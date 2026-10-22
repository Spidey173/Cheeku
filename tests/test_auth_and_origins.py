import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app.main import app
from backend.app.config import settings


def test_allowed_origin_connects():
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={settings.AUTH_TOKEN}", headers={"origin": "http://localhost:8000"}) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "state_change"


def test_disallowed_origin_rejected():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws?token={settings.AUTH_TOKEN}", headers={"origin": "http://evil-attacker.com"}):
                pass
        assert exc_info.value.code == 1008


def test_missing_origin_on_localhost_allowed():
    # Local development tools connecting directly to loopback without Origin header
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={settings.AUTH_TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "state_change"


def test_auth_token_enforcement(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TOKEN", "super-secret-token")
    monkeypatch.setattr(settings, "WS_AUTH_REQUIRED", True)

    with TestClient(app) as client:
        # 1. Connection without token should be rejected
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws", headers={"origin": "http://localhost:8000"}):
                pass
        assert exc_info.value.code == 1008

        # 2. Connection with wrong token should be rejected
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws?token=wrong-token", headers={"origin": "http://localhost:8000"}):
                pass
        assert exc_info.value.code == 1008

        # 3. Connection with valid token in query param should succeed
        with client.websocket_connect("/ws?token=super-secret-token", headers={"origin": "http://localhost:8000"}) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "state_change"

        # 4. Connection with valid Bearer token in header should succeed
        with client.websocket_connect(
            "/ws",
            headers={"origin": "http://localhost:8000", "authorization": "Bearer super-secret-token"}
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "state_change"


def test_secure_by_default_posture():
    # In secure-by-default configuration, auth is required and token is resolved
    assert settings.WS_AUTH_REQUIRED is True
    assert bool(settings.AUTH_TOKEN) is True

    # Connecting without a token is rejected by default
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws", headers={"origin": "http://127.0.0.1:8000"}):
                pass
        assert exc_info.value.code == 1008


def test_opt_in_unauthenticated_mode(monkeypatch):
    # When explicitly configured with unauthenticated mode, connections succeed without token
    monkeypatch.setattr(settings, "WS_AUTH_REQUIRED", False)
    monkeypatch.setattr(settings, "AUTH_TOKEN", None)

    with TestClient(app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://127.0.0.1:8000"}) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "state_change"
