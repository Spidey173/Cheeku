import os
import re
import tempfile
import base64
import asyncio
import httpx
import edge_tts
from typing import Optional, Dict, Any
from backend.utils.logger import logger


class NeuralVoiceEngine:
    """
    Studio-quality neural voice engine delivering warm, natural, expressive speech
    directly to the frontend web browser.
    
    Automatic Provider Hierarchy:
    1. OpenAI TTS (if OPENAI_API_KEY is configured) - Lowest latency, high naturalness
    2. ElevenLabs (if ELEVENLABS_API_KEY is configured) - Ultra-realistic human voice
    3. Microsoft Edge TTS (edge-tts) - High-quality neural cloud voices (100% free)
    4. macOS 'say' system speech - Offline fallback
    """
    def __init__(self):
        # Default to Ava Multilingual Neural (Microsoft Ava Latest HD, expressive female ~20+)
        self.edge_voice = os.getenv("EDGE_VOICE", "en-US-AvaMultilingualNeural")
        # Natural conversational pitch and cadence (zero roughness)
        self.edge_rate = os.getenv("TTS_RATE", "+0%")
        self.edge_pitch = os.getenv("TTS_PITCH", "+0Hz")

        # Microsoft Azure AI Speech (Ava Dragon HD Latest)
        self.azure_speech_key = os.getenv("AZURE_SPEECH_KEY", "") or os.getenv("SPEECH_KEY", "")
        self.azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus") or os.getenv("SPEECH_REGION", "eastus")
        self.azure_voice = os.getenv("AZURE_VOICE", "en-US-Ava:DragonHDLatestNeural")

        # OpenAI TTS Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_voice = os.getenv("OPENAI_VOICE", "nova")  # 'nova' is warm, cute, friendly female

        # ElevenLabs Configuration
        self.eleven_api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_API_KEY", "")
        # Rachel: 21m00Tcm4TlvDq8ikWAM, Bella: EXAVITQu4vr4xnSDxMaL
        self.eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

        # Local macOS offline fallback
        self.local_fallback_voice = "Samantha"

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Removes markdown, code snippets, emojis, URLs, and noisy symbols
        to prevent audio crackling and synthesis artifacts.
        """
        if not text:
            return ""

        clean = text

        # Remove code blocks and inline code
        clean = re.sub(r"```[\s\S]*?```", "", clean)
        clean = re.sub(r"`.*?`", "", clean)

        # Remove markdown URLs: [anchor](url) -> anchor
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)

        # Remove bare URLs
        clean = re.sub(r"https?://\S+", "", clean)

        # Remove decorative emojis and special characters
        emojis_and_symbols = [
            '🌸', '💖', '✨', '🎶', '💕', '😊', '🥰', '☀️', '⚡', '⚙️', '🌐', '🎵',
            '•', '*', '#', '_', '~', '>', '<', '[', ']', '(', ')', '{', '}', '|', '\\'
        ]
        for char in emojis_and_symbols:
            clean = clean.replace(char, ' ')

        # Normalize whitespace
        clean = " ".join(clean.split()).strip()
        return clean

    async def _synthesize_azure(self, text: str) -> Optional[Dict[str, str]]:
        """Synthesizes high-definition speech using Microsoft Azure AI Speech (Ava Dragon HD)."""
        if not self.azure_speech_key or not self.azure_speech_region:
            return None

        url = f"https://{self.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "CheekuAI"
        }
        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
    <voice name="{self.azure_voice}">
        {text}
    </voice>
</speak>"""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
                if res.status_code == 200:
                    b64_audio = base64.b64encode(res.content).decode("utf-8")
                    logger.info(f"Azure AI Speech [{self.azure_voice}] succeeded ({len(res.content)} bytes).")
                    return {"data": b64_audio, "mime": "audio/mp3"}
                else:
                    logger.warning(f"Azure Speech API notice ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"Azure Speech synthesis failed: {e}")

        return None

    async def _synthesize_openai(self, text: str) -> Optional[Dict[str, str]]:
        """Synthesizes speech using OpenAI TTS API (tts-1 with 'nova' voice)."""
        if not self.openai_api_key:
            return None

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": self.openai_voice,
            "response_format": "mp3"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    b64_audio = base64.b64encode(res.content).decode("utf-8")
                    logger.info(f"OpenAI TTS synthesis succeeded ({len(res.content)} bytes).")
                    return {"data": b64_audio, "mime": "audio/mp3"}
                else:
                    logger.warning(f"OpenAI TTS error ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"OpenAI TTS synthesis failed: {e}")

        return None

    async def _synthesize_elevenlabs(self, text: str) -> Optional[Dict[str, str]]:
        """Synthesizes speech using ElevenLabs API (eleven_turbo_v2_5)."""
        if not self.eleven_api_key:
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.eleven_voice_id}"
        headers = {
            "xi-api-key": self.eleven_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75,
                "style": 0.15,
                "use_speaker_boost": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    b64_audio = base64.b64encode(res.content).decode("utf-8")
                    logger.info(f"ElevenLabs TTS synthesis succeeded ({len(res.content)} bytes).")
                    return {"data": b64_audio, "mime": "audio/mp3"}
                else:
                    logger.warning(f"ElevenLabs TTS error ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"ElevenLabs TTS synthesis failed: {e}")

        return None

    async def _synthesize_edge_tts(self, text: str) -> Optional[Dict[str, str]]:
        """Synthesizes high-fidelity neural speech via Microsoft Edge TTS."""
        voice = self.edge_voice
        # Map Azure Speech Studio Ava Dragon HD identifier to Edge TTS counterpart
        if "DragonHDLatest" in voice or "Dragon" in voice or voice == "en-US-Ava:DragonHDLatestNeural":
            voice = "en-US-AvaMultilingualNeural"

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=self.edge_rate,
                pitch=self.edge_pitch
            )
            chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

            if chunks:
                audio_bytes = b"".join(chunks)
                if len(audio_bytes) > 0:
                    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                    logger.info(
                        f"Edge Neural TTS [{self.edge_voice}] succeeded ({len(audio_bytes)} bytes)."
                    )
                    return {"data": b64_audio, "mime": "audio/mp3"}
        except Exception as e:
            logger.warning(f"Edge TTS synthesis error: {e}")

        return None

    async def _synthesize_macos_say(self, text: str) -> Optional[Dict[str, str]]:
        """Offline fallback using macOS speech synthesis converted to clean 16-bit PCM WAV."""
        aiff_path = None
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_tmp:
                aiff_path = aiff_tmp.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
                wav_path = wav_tmp.name

            # Synthesize
            proc = await asyncio.create_subprocess_exec(
                "say", "-v", self.local_fallback_voice, "-o", aiff_path, text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()

            if not os.path.exists(aiff_path) or os.path.getsize(aiff_path) == 0:
                proc_def = await asyncio.create_subprocess_exec(
                    "say", "-o", aiff_path, text,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc_def.wait()

            # Convert to standard 16-bit PCM WAVE
            proc_conv = await asyncio.create_subprocess_exec(
                "afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc_conv.wait()

            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                with open(wav_path, "rb") as f:
                    b64_wav = base64.b64encode(f.read()).decode("utf-8")
                logger.info(f"macOS offline speech fallback used ({os.path.getsize(wav_path)} bytes).")
                return {"data": b64_wav, "mime": "audio/wav"}

        except Exception as err:
            logger.error(f"macOS say synthesis error: {err}")
        finally:
            for p in [aiff_path, wav_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        return None

    async def synthesize_to_base64(self, text: str) -> Optional[Dict[str, str]]:
        """
        Synthesizes text into high-fidelity neural audio.
        Automatically cascades down provider priority:
        OpenAI TTS -> ElevenLabs -> Edge Neural TTS -> macOS say fallback.
        """
        clean_text = self._clean_text_for_speech(text)
        if not clean_text:
            return None

        # 1. Try Microsoft Azure AI Speech (Ava Dragon HD Latest) if configured
        res = await self._synthesize_azure(clean_text)
        if res:
            return res

        # 2. Try OpenAI TTS (if API key available)
        res = await self._synthesize_openai(clean_text)
        if res:
            return res

        # 2. Try ElevenLabs (if API key available)
        res = await self._synthesize_elevenlabs(clean_text)
        if res:
            return res

        # 3. Try Microsoft Edge Neural TTS (High-quality, free, expressive female voice)
        res = await self._synthesize_edge_tts(clean_text)
        if res:
            return res

        # 4. Fallback to macOS system synthesis if all cloud options are unavailable
        res = await self._synthesize_macos_say(clean_text)
        return res

    async def speak_locally(self, text: str):
        """Deprecated: Assistant audio runs exclusively in the browser."""
        return


tts = NeuralVoiceEngine()
