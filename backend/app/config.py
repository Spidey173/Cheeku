import os
import secrets
from pathlib import Path
from typing import Any, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=False)


def _parse_bool(val: Any, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "t", "yes", "y", "on")


def _parse_list(val: Any, default: List[str]) -> List[str]:
    if val is None:
        return default
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        parts = [p.strip() for p in val.split(",") if p.strip()]
        return parts if parts else default
    return default


def _resolve_default_auth_token() -> Optional[str]:
    """
    Resolves or generates a secure auth token.
    Ensures safe-by-default posture: authentication is never absent unless explicitly opted out.
    """
    configured_token = os.getenv("AUTH_TOKEN", "").strip()
    if configured_token:
        return configured_token

    if _parse_bool(os.getenv("ALLOW_UNAUTHENTICATED", "false"), default=False):
        return None

    # Auto-generate a secure token for local server lifecycle
    token_file = BASE_DIR / ".cheeku_token"
    if token_file.exists():
        try:
            stored = token_file.read_text().strip()
            if stored:
                return stored
        except Exception:
            pass

    new_token = secrets.token_urlsafe(24)
    try:
        token_file.write_text(new_token)
        os.chmod(token_file, 0o600)
    except Exception:
        pass
    return new_token


class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "Cheeku AI Assistant"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = _parse_bool(os.getenv("DEBUG", "false"), default=False)

    # Security & WebSocket (Secure by Default)
    AUTH_TOKEN: Optional[str] = Field(default_factory=_resolve_default_auth_token)
    WS_AUTH_REQUIRED: bool = _parse_bool(os.getenv("WS_AUTH_REQUIRED", "true"), default=True)
    ALLOW_UNAUTHENTICATED: bool = _parse_bool(os.getenv("ALLOW_UNAUTHENTICATED", "false"), default=False)
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: _parse_list(
            os.getenv("ALLOWED_ORIGINS"),
            ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000"]
        )
    )
    ALLOW_ALL_ORIGINS: bool = _parse_bool(os.getenv("ALLOW_ALL_ORIGINS", "false"), default=False)
    MAX_PAYLOAD_BYTES: int = int(os.getenv("MAX_PAYLOAD_BYTES", 1_048_576))  # 1 MB default frame limit

    # Tool Execution Security & Authorization (Disabled by Default for safety)
    ENABLE_SYSTEM_ACTIONS: bool = _parse_bool(os.getenv("ENABLE_SYSTEM_ACTIONS", "false"), default=False)
    ALLOWED_SYSTEM_APPS: List[str] = Field(
        default_factory=lambda: _parse_list(
            os.getenv("ALLOWED_SYSTEM_APPS"),
            [
                "Safari", "Google Chrome", "Spotify", "Terminal", "Notes",
                "Calculator", "Visual Studio Code", "Slack", "Music", "System Settings"
            ]
        )
    )
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))

    # Paths
    BASE_DIR: Path = BASE_DIR
    LOG_DIR: str = str(BASE_DIR / "logs")
    DATA_DIR: str = str(BASE_DIR / "data")
    STATIC_DIR: str = str(BASE_DIR.parent / "frontend")

    # Brain / Groq Cloud LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    MAX_HISTORY_TURNS: int = 15
    TEMPERATURE: float = 0.7

    # Audio / STT & TTS
    WHISPER_MODEL: str = "base.en"
    STT_DEVICE: str = "cpu"
    AUDIO_SAMPLE_RATE: int = 16000
    TTS_ENGINE: str = "web"
    KOKORO_VOICE: str = "af_heart"
    TTS_SPEED: float = 1.05
    FRONTEND_ONLY: bool = True

    # VAD Settings
    VAD_AGGRESSIVENESS: int = 2
    SILENCE_THRESHOLD_SECONDS: float = 1.2

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"PORT must be between 1 and 65535, got {v}")
        return v

    @field_validator("MAX_PAYLOAD_BYTES")
    @classmethod
    def validate_max_payload(cls, v: int) -> int:
        if v < 1024:
            raise ValueError(f"MAX_PAYLOAD_BYTES must be at least 1024 bytes, got {v}")
        return v


settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
