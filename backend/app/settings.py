from __future__ import annotations
import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Mercy Catholic AI API")
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Gemini credentials remain server-side only.
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    gemini_classifier_model: str = os.getenv(
        "GEMINI_CLASSIFIER_MODEL", "gemini-3.5-flash-lite"
    )

    allowed_origins: list[str] = None

    # reCAPTCHA Enterprise. The site key is public; assessment auth uses ADC/service-account IAM.
    recaptcha_enforce: bool = _bool("RECAPTCHA_ENFORCE", False)
    recaptcha_project_id: str = os.getenv("RECAPTCHA_PROJECT_ID", "")
    recaptcha_site_key: str = os.getenv("RECAPTCHA_SITE_KEY", "")
    recaptcha_min_score: float = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.5"))
    recaptcha_allowed_hostnames: list[str] = None

    # Cloud Run filesystems are ephemeral. Keep persistence disabled until a durable DB is configured.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////tmp/mercy.db")
    persist_contact_messages: bool = _bool("PERSIST_CONTACT_MESSAGES", False)

    # Owner delivery. At least one configured delivery route or durable DB is required
    # before /api/contact reports success.
    owner_email: str = os.getenv("OWNER_EMAIL", "")
    owner_whatsapp: str = os.getenv("OWNER_WHATSAPP", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_use_tls: bool = _bool("SMTP_USE_TLS", True)
    whatsapp_api_url: str = os.getenv("WHATSAPP_API_URL", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

    auto_reply_faith_questions: bool = _bool("AUTO_REPLY_FAITH_QUESTIONS", True)
    max_chat_chars: int = int(os.getenv("MAX_CHAT_CHARS", "2000"))
    max_contact_chars: int = int(os.getenv("MAX_CONTACT_CHARS", "5000"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

    def __post_init__(self):
        object.__setattr__(
            self,
            "allowed_origins",
            _csv(
                "ALLOWED_ORIGINS",
                "http://localhost:5500,http://127.0.0.1:5500",
            ),
        )
        object.__setattr__(
            self,
            "recaptcha_allowed_hostnames",
            _csv("RECAPTCHA_ALLOWED_HOSTNAMES", ""),
        )


settings = Settings()
