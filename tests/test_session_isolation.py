import secrets
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings
from backend.app.assistant import session_registry
from backend.brain.memory import memory
from backend.models.schemas import AssistantState


@contextmanager
def connect_ws_session(client, extra_params=""):
    url = f"/ws?token={settings.AUTH_TOKEN}"
    if extra_params:
        url += f"&{extra_params}"
    with client.websocket_connect(url) as ws:
        state_msg = ws.receive_json()
        init_msg = ws.receive_json()
        mem_msg = ws.receive_json()
        session_id = init_msg["payload"]["session_id"]
        session_token = init_msg["payload"]["session_token"]
        resumed = init_msg["payload"].get("resumed", False)
        yield ws, session_id, session_token, resumed


def test_concurrent_sessions_isolated():
    mock_response_a = {
        "content": "Cheeku response for Client A",
        "tool_calls": [],
        "success": True
    }
    mock_response_b = {
        "content": "Cheeku response for Client B",
        "tool_calls": [],
        "success": True
    }

    with patch("backend.brain.groq.groq_client.generate_response", new_callable=AsyncMock) as mock_groq, \
         patch("backend.audio.tts.tts.synthesize_to_base64", new_callable=AsyncMock) as mock_tts:

        mock_tts.return_value = {"data": "bW9ja19hdWRpb19kYXRh", "mime": "audio/mp3"}

        with TestClient(app) as client:
            with connect_ws_session(client) as (ws_alice, session_alice_id, token_alice, _), \
                 connect_ws_session(client) as (ws_bob, session_bob_id, token_bob, _):

                assert session_alice_id != session_bob_id

                # Alice sends chat
                mock_groq.return_value = mock_response_a
                ws_alice.send_json({
                    "type": "chat",
                    "payload": {"text": "Hello, this is Alice"}
                })

                # Alice should receive user echo, state changes, assistant reply, audio
                alice_messages = []
                while True:
                    msg = ws_alice.receive_json()
                    alice_messages.append(msg)
                    if msg["type"] == "chat" and msg["payload"].get("role") == "assistant":
                        break

                assert any("Cheeku response for Client A" in str(m) for m in alice_messages)

                # Bob sends chat
                mock_groq.return_value = mock_response_b
                ws_bob.send_json({
                    "type": "chat",
                    "payload": {"text": "Hello, this is Bob"}
                })

                bob_messages = []
                while True:
                    msg = ws_bob.receive_json()
                    bob_messages.append(msg)
                    if msg["type"] == "chat" and msg["payload"].get("role") == "assistant":
                        break

                assert any("Cheeku response for Client B" in str(m) for m in bob_messages)

                # Verify Session State and History Isolation in backend registry
                orch_alice = session_registry.get_or_create(session_alice_id)
                orch_bob = session_registry.get_or_create(session_bob_id)

                alice_history_texts = [m.content for m in orch_alice.short_term_history]
                bob_history_texts = [m.content for m in orch_bob.short_term_history]

                assert "Hello, this is Alice" in alice_history_texts
                assert "Hello, this is Bob" not in alice_history_texts

                assert "Hello, this is Bob" in bob_history_texts
                assert "Hello, this is Alice" not in bob_history_texts

                # Verify memory manager isolation per session
                alice_mem = memory.get_short_term(session_alice_id)
                bob_mem = memory.get_short_term(session_bob_id)
                assert any("Hello, this is Alice" in m.content for m in alice_mem)
                assert not any("Hello, this is Bob" in m.content for m in alice_mem)
                assert any("Hello, this is Bob" in m.content for m in bob_mem)
                assert not any("Hello, this is Alice" in m.content for m in bob_mem)


def test_independent_session_states():
    with TestClient(app) as client:
        with connect_ws_session(client) as (ws1, s1_id, _, _), \
             connect_ws_session(client) as (ws2, s2_id, _, _):

            orch1 = session_registry.get_or_create(s1_id)
            orch2 = session_registry.get_or_create(s2_id)

            assert orch1.state == AssistantState.READY
            assert orch2.state == AssistantState.READY

            # Interrupt session 1
            ws1.send_json({"type": "interrupt", "payload": {}})
            msg1 = ws1.receive_json()
            assert msg1["type"] == "state_change"

            # Session 2 should remain unaffected and ready
            assert orch2.state == AssistantState.READY


def test_session_hijacking_prevention_and_disconnect_isolation():
    """
    Verifies:
    1. A client cannot hijack another connection's session_id without the session_token.
    2. An attacker's disconnect does NOT destroy or disconnect the victim's session.
    3. Valid session_token allows legitimate session resumption.
    """
    with TestClient(app) as client:
        # 1. Alice connects legitimately
        with connect_ws_session(client) as (ws_alice, session_alice_id, token_alice, _):
            orch_alice = session_registry.get_or_create(session_alice_id)
            initial_alice_ws = orch_alice.websocket
            assert initial_alice_ws is not None

            # 2. Attacker attempts to hijack Alice's session with a guessed/wrong token
            with connect_ws_session(
                client,
                extra_params=f"session_id={session_alice_id}&session_token=attacker_guessing_tokens"
            ) as (ws_eve, session_eve_id, token_eve, resumed_eve):
                # Hijack must be blocked: Eve must NOT get Alice's session ID
                assert session_eve_id != session_alice_id
                assert resumed_eve is False

                # Alice's WebSocket binding remains completely unperturbed
                assert orch_alice.websocket is initial_alice_ws

            # 3. Eve disconnected (exited Eve's context block).
            # Alice's session must NOT be removed or disturbed by Eve's disconnect.
            assert session_alice_id in session_registry._sessions
            assert orch_alice.websocket is initial_alice_ws

        # 4. Legitimate resumption with matching session_token succeeds
        with connect_ws_session(
            client,
            extra_params=f"session_id={session_alice_id}&session_token={token_alice}"
        ) as (ws_resumed, resumed_id, _, was_resumed):
            assert resumed_id == session_alice_id
            assert was_resumed is True
