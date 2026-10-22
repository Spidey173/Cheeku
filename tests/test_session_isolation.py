from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.assistant import session_registry
from backend.models.schemas import AssistantState


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
            with client.websocket_connect("/ws?session_id=session_alice") as ws_alice, \
                 client.websocket_connect("/ws?session_id=session_bob") as ws_bob:

                # Drain initial state & memory messages for both
                ws_alice.receive_json()
                ws_alice.receive_json()

                ws_bob.receive_json()
                ws_bob.receive_json()

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
                orch_alice = session_registry.get_or_create("session_alice")
                orch_bob = session_registry.get_or_create("session_bob")

                alice_history_texts = [m.content for m in orch_alice.short_term_history]
                bob_history_texts = [m.content for m in orch_bob.short_term_history]

                assert "Hello, this is Alice" in alice_history_texts
                assert "Hello, this is Bob" not in alice_history_texts

                assert "Hello, this is Bob" in bob_history_texts
                assert "Hello, this is Alice" not in bob_history_texts


def test_independent_session_states():
    with TestClient(app) as client:
        with client.websocket_connect("/ws?session_id=session_1") as ws1, \
             client.websocket_connect("/ws?session_id=session_2") as ws2:

            ws1.receive_json()
            ws1.receive_json()
            ws2.receive_json()
            ws2.receive_json()

            orch1 = session_registry.get_or_create("session_1")
            orch2 = session_registry.get_or_create("session_2")

            assert orch1.state == AssistantState.READY
            assert orch2.state == AssistantState.READY

            # Interrupt session 1
            ws1.send_json({"type": "interrupt", "payload": {}})
            msg1 = ws1.receive_json()
            assert msg1["type"] == "state_change"

            # Session 2 should remain unaffected and ready
            assert orch2.state == AssistantState.READY
