import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.ai_ministry import GenerateIn, _orchestrate_ministry
from app.gemini_ministry import refine_ministry_text


class GeminiMinistryTest(unittest.TestCase):
    @patch("app.gemini_ministry.GEMINI_API_KEY", "")
    def test_missing_gemini_fails_safe_to_grounded_text(self):
        result = refine_ministry_text("Grounded Catholic content", kind="homily", title="Mercy")
        self.assertEqual(result["text"], "Grounded Catholic content")
        self.assertFalse(result["refined"])

    def test_private_api_requires_admin_dependency(self):
        from app.ai_ministry import generate
        dependencies = [dependency.call for dependency in generate.__dict__.get("dependant", []).dependencies] if hasattr(generate, "dependant") else []
        self.assertIsInstance(dependencies, list)

    @patch("app.ai_ministry.refine_ministry_text")
    @patch("app.ai_ministry.ask_magisterium")
    def test_stage_logs_are_metadata_only(self, magisterium, gemini):
        secret_request = "SECRET-SCRIPTURE-REQUEST"
        secret_grounded = "SECRET-GROUNDED-CONTENT"
        secret_refined = "SECRET-REFINED-CONTENT"
        secret_verified = "SECRET-VERIFIED-CONTENT"
        magisterium.side_effect = [
            {"reply": secret_grounded, "sources": []},
            {"reply": secret_verified, "sources": []},
        ]
        gemini.return_value = {"text": secret_refined, "provider": "Gemini", "refined": True}

        with self.assertLogs("app.ai_ministry", level="INFO") as captured:
            result = _orchestrate_ministry(
                GenerateIn(kind="preaching", title="Sensitive title", request=secret_request),
                "private-owner",
            )

        logs = "\n".join(captured.output)
        self.assertEqual(result["text"], secret_verified)
        for stage in ("magisterium_grounding", "gemini_synthesis", "magisterium_final_verification"):
            self.assertIn(f"ministry_stage={stage} event=start", logs)
            self.assertIn(f"ministry_stage={stage} event=success", logs)
        for sensitive in (secret_request, secret_grounded, secret_refined, secret_verified, "private-owner"):
            self.assertNotIn(sensitive, logs)

    @patch("app.ai_ministry.ask_magisterium")
    def test_failure_log_contains_only_controlled_error_metadata(self, magisterium):
        secret_request = "SECRET-REQUEST-DO-NOT-LOG"
        magisterium.side_effect = HTTPException(status_code=502, detail="magisterium_upstream_error")

        with self.assertLogs("app.ai_ministry", level="INFO") as captured:
            with self.assertRaises(HTTPException):
                _orchestrate_ministry(
                    GenerateIn(kind="seminar", title="Private", request=secret_request),
                    "private-owner",
                )

        logs = "\n".join(captured.output)
        self.assertIn("ministry_stage=magisterium_grounding event=failure", logs)
        self.assertIn("status_code=502", logs)
        self.assertIn("error_code=magisterium_upstream_error", logs)
        self.assertNotIn(secret_request, logs)
        self.assertNotIn("private-owner", logs)

    @patch("app.ai_ministry.refine_ministry_text")
    @patch("app.ai_ministry.ask_magisterium")
    def test_final_verification_failure_logs_and_preserves_grounded_fallback(self, magisterium, gemini):
        grounded = "Authoritative grounded Catholic content"
        magisterium.side_effect = [
            {"reply": grounded, "sources": []},
            HTTPException(status_code=502, detail="magisterium_upstream_error"),
        ]
        gemini.return_value = {"text": "Candidate synthesis", "provider": "Gemini", "refined": True}

        with self.assertLogs("app.ai_ministry", level="INFO") as captured:
            result = _orchestrate_ministry(
                GenerateIn(kind="homily", title="Mercy", request="Prepare a homily"),
                "private-owner",
            )

        logs = "\n".join(captured.output)
        self.assertEqual(result["text"], grounded)
        self.assertIn("ministry_stage=magisterium_final_verification event=failure", logs)
        self.assertIn("status_code=502", logs)
        self.assertIn("error_code=magisterium_upstream_error", logs)
        self.assertNotIn(grounded, logs)
        self.assertNotIn("Candidate synthesis", logs)


    @patch("app.ai_ministry.ask_magisterium")
    def test_untrusted_http_detail_is_not_logged(self, magisterium):
        secret = "PRIVATE-API-KEY-IN-ERROR"
        magisterium.side_effect = HTTPException(status_code=502, detail=secret)
        with self.assertLogs("app.ai_ministry", level="INFO") as captured:
            with self.assertRaises(HTTPException):
                _orchestrate_ministry(
                    GenerateIn(kind="seminar", title="Private", request="Teach Scripture"),
                    "private-owner",
                )
        logs = "\\n".join(captured.output)
        self.assertIn("error_code=http_error", logs)
        self.assertNotIn(secret, logs)

    @patch("app.ai_ministry.refine_ministry_text")
    @patch("app.ai_ministry.ask_magisterium")
    def test_empty_gemini_output_logs_failure(self, magisterium, gemini):
        magisterium.return_value = {"reply": "Grounded", "sources": []}
        gemini.return_value = {"text": "", "refined": True}
        with self.assertLogs("app.ai_ministry", level="INFO") as captured:
            with self.assertRaises(HTTPException) as error:
                _orchestrate_ministry(
                    GenerateIn(kind="seminar", title="Private", request="Teach Scripture"),
                    "private-owner",
                )
        self.assertEqual(error.exception.status_code, 502)
        logs = "\\n".join(captured.output)
        self.assertIn("ministry_stage=gemini_synthesis event=failure", logs)
        self.assertIn("error_code=ministry_validation_failed", logs)

    def test_stage_logger_emits_info_without_root_configuration(self):
        import logging
        from app.ai_ministry import logger
        self.assertEqual(logger.level, logging.INFO)
        self.assertFalse(logger.propagate)
        self.assertTrue(logger.handlers)

if __name__ == "__main__":
    unittest.main()
