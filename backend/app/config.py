import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "Cheeku AI Assistant"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = True
    
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
    WHISPER_MODEL: str = "base.en"  # "tiny.en", "base.en", "small.en"
    STT_DEVICE: str = "cpu"  # or "cuda"
    AUDIO_SAMPLE_RATE: int = 16000
    TTS_ENGINE: str = "web"  # "web" (synthesized for client browser playback)
    KOKORO_VOICE: str = "af_heart"  # 'af_heart', 'af_bella', 'af_sky'
    TTS_SPEED: float = 1.05
    FRONTEND_ONLY: bool = True  # Terminal assistant execution disabled
    
    # VAD Settings
    VAD_AGGRESSIVENESS: int = 2
    SILENCE_THRESHOLD_SECONDS: float = 1.2
    
    # Logging
    LOG_LEVEL: str = "INFO"

settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
