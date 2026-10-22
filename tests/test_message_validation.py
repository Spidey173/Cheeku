import json
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings


@contextmanager
def connect_ws(client):
    with client.websocket_connect(f"/ws?token={settings.AUTH_TOKEN}") as ws:
        # Drain initial state_change, session_init command, and memory_update
        ws.receive_json()
        ws.receive_json()
        ws.receive_json()
        yield ws


def test_oversized_payload_rejected(monkeypatch):
    monkeypatch.setattr(settings, "MAX_PAYLOAD_BYTES", 2048)

    with TestClient(app) as client:
        with connect_ws(client) as ws:
            oversized_text = "A" * 3000
            ws.send_text(oversized_text)

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "exceeds maximum allowed limit" in res["payload"]["message"]


def test_malformed_json_rejected():
    with TestClient(app) as client:
        with connect_ws(client) as ws:
            ws.send_text("THIS IS NOT JSON {{{{{")

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Malformed JSON" in res["payload"]["message"]


def test_unsupported_message_type_rejected():
    with TestClient(app) as client:
        with connect_ws(client) as ws:
            ws.send_json({
                "type": "malicious_unsupported_type",
                "payload": {"data": "exploit"}
            })

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Invalid message format" in res["payload"]["message"]


def test_invalid_chat_payload():
    with TestClient(app) as client:
        with connect_ws(client) as ws:
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
        with connect_ws(client) as ws:
            # Audio payload missing audio_base64
            ws.send_json({
                "type": "audio",
                "payload": {"mime_type": "audio/wav"}
            })

            res = ws.receive_json()
            assert res["type"] == "error"
            assert "Invalid audio payload" in res["payload"]["message"]
