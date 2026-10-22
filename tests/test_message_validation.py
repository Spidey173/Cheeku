import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings


def test_oversized_payload_rejected(monkeypatch):
    monkeypatch.setattr(settings, "MAX_PAYLOAD_BYTES", 2048)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Drain initial state & memory messages
            ws.receive_json()
            ws.receive_json()

            oversized_text = "A" * 3000
            ws.send_text(oversized_text)

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "exceeds maximum allowed limit" in res["payload"]["message"]


def test_malformed_json_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_text("THIS IS NOT JSON {{{{{")

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Malformed JSON" in res["payload"]["message"]


def test_unsupported_message_type_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({
                "type": "malicious_unsupported_type",
                "payload": {"data": "exploit"}
            })

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Invalid message format" in res["payload"]["message"]


def test_invalid_chat_payload():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.receive_json()

            # Chat payload with text exceeding max limit
            ws.send_json({
                "type": "chat",
                "payload": {"text": "A" * 15000}
            })

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Invalid chat payload" in res["payload"]["message"]


def test_invalid_audio_payload():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.receive_json()

            # Audio payload missing audio_base64
            ws.send_json({
                "type": "audio",
                "payload": {"mime_type": "audio/wav"}
            })

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Invalid audio payload" in res["payload"]["message"]
