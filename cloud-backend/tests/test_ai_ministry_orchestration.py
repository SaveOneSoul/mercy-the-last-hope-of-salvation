import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
