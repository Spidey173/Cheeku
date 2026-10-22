import os
import tempfile
import asyncio
from typing import Optional
from backend.app.config import settings
from backend.utils.logger import logger


class SpeechToText:
    def __init__(self, model_size: str = settings.WHISPER_MODEL, device: str = settings.STT_DEVICE):
        self.model_size = model_size
        self.device = device
        self._model = None
        self._is_loaded = False
        self._load_lock = asyncio.Lock()

    def load_model(self):
        if not self._is_loaded:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper model ({self.model_size}) on {self.device}...")
                self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
                self._is_loaded = True
                logger.info("Speech-to-Text model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load faster-whisper ({e}). Web Speech API will be used as primary.")

    def transcribe_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Transcribe raw audio bytes to text synchronously."""
        if not audio_bytes or len(audio_bytes) > 10 * 1024 * 1024:
            return ""

        if not self._is_loaded:
            self.load_model()

        if not self._model:
            return ""

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            segments, _ = self._model.transcribe(tmp_path, beam_size=2)
            transcription = " ".join([segment.text for segment in segments]).strip()
            return transcription
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    async def transcribe_bytes_async(self, audio_bytes: bytes, format: str = "wav", timeout: float = 12.0) -> str:
        """Transcribe audio bytes in background worker thread with timeout."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.transcribe_bytes, audio_bytes, format),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Whisper transcription timed out.")
            return ""
        except Exception as e:
            logger.error(f"Async transcription error: {e}")
            return ""


stt = SpeechToText()
