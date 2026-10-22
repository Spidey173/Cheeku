import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.brain.groq import GroqBrainClient
from backend.models.schemas import ChatMessage, MessageRole, AssistantState
from backend.audio.tts import NeuralVoiceEngine
from backend.audio.stt import SpeechToText
from backend.tools.registry import registry
from backend.app.assistant import AssistantOrchestrator


def test_groq_api_timeout():
    async def _test():
        client = GroqBrainClient(api_key="mock_key")

        with patch("httpx.AsyncClient.post", side_effect=asyncio.TimeoutError()):
            messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
            res = await client.generate_response(messages)
            assert res["success"] is False
            assert "took a moment too long" in res["content"]

    asyncio.run(_test())


def test_groq_api_http_error():
    async def _test():
        client = GroqBrainClient(api_key="mock_key")

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post", return_value=mock_resp):
            messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
            res = await client.generate_response(messages)
            assert res["success"] is False
            assert "Groq API error" in res["content"]

    asyncio.run(_test())


def test_tts_synthesis_failure_fallback():
    async def _test():
        tts_engine = NeuralVoiceEngine()

        # Mock all TTS providers to return None (failure)
        with patch.object(tts_engine, "_synthesize_azure", new_callable=AsyncMock, return_value=None), \
             patch.object(tts_engine, "_synthesize_openai", new_callable=AsyncMock, return_value=None), \
             patch.object(tts_engine, "_synthesize_elevenlabs", new_callable=AsyncMock, return_value=None), \
             patch.object(tts_engine, "_synthesize_edge_tts", new_callable=AsyncMock, return_value=None), \
             patch.object(tts_engine, "_synthesize_macos_say", new_callable=AsyncMock, return_value=None):

            res = await tts_engine.synthesize_to_base64("Hello world")
            assert res is None

    asyncio.run(_test())


def test_tool_execution_exception_handled():
    async def _test():
        @registry.register(
            name="faulty_test_tool",
            description="Tool that raises an unexpected exception",
            parameters={"type": "object", "properties": {}}
        )
        def faulty_tool():
            raise RuntimeError("Database connection crashed!")

        res = await registry.execute("faulty_test_tool", {})
        assert "Error executing faulty_test_tool" in res
        assert "Database connection crashed!" in res

    asyncio.run(_test())


def test_stt_whisper_unavailable_fallback():
    stt_engine = SpeechToText()
    stt_engine._is_loaded = True
    stt_engine._model = None  # Model unavailable

    res = stt_engine.transcribe_bytes(b"dummy audio bytes")
    assert res == ""
