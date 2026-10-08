import logging
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from app import gemini_ministry


@pytest.mark.parametrize("upstream_status", [400, 404, 429, 500, 503])
def test_gemini_upstream_status_logged_without_sensitive_data(
    upstream_status, caplog
):
    secret = "test-secret-must-not-appear"
    private_text = "private-ministry-content-must-not-appear"

    response = httpx.Response(
        upstream_status,
        json={"error": {"message": secret}},
        request=httpx.Request("POST", "https://example.invalid"),
    )

    # The production logger deliberately has propagation disabled.
    # Enable it only within this test to let pytest capture records.
    with patch.object(gemini_ministry.logger, "propagate", True):
        with caplog.at_level(logging.INFO, logger="mercy.gemini_ministry"):
            with patch.object(gemini_ministry, "GEMINI_API_KEY", secret):
                with patch.object(httpx.Client, "post", return_value=response):
                    with pytest.raises(HTTPException) as exc:
                        gemini_ministry.refine_ministry_text(
                            private_text,
                            kind="preaching",
                            title="Test",
                            request_text=private_text,
                        )

    assert exc.value.status_code == 502
    assert exc.value.detail == "gemini_upstream_error"

    output = caplog.text
    assert f"gemini_upstream_http_error status_code={upstream_status}" in output
    assert secret not in output
    assert private_text not in output


@pytest.mark.parametrize("upstream_status", [401, 403])
def test_gemini_authentication_errors_keep_existing_contract(upstream_status):
    response = httpx.Response(
        upstream_status,
        request=httpx.Request("POST", "https://example.invalid"),
    )

    with patch.object(gemini_ministry, "GEMINI_API_KEY", "test-key"):
        with patch.object(httpx.Client, "post", return_value=response):
            with pytest.raises(HTTPException) as exc:
                gemini_ministry.refine_ministry_text(
                    "Grounded content",
                    kind="preaching",
                    title="Test",
                )

    assert exc.value.status_code == 503
    assert exc.value.detail == "gemini_authentication_failed"