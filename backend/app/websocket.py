import asyncio
import json
from typing import Any, Dict, Optional, Set
from fastapi import WebSocket
from backend.models.schemas import WSMessage, WSMessageType, AssistantState
from backend.utils.logger import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    def _serialize_message(self, message: Any) -> str:
        if isinstance(message, dict):
            return json.dumps(message)
        elif hasattr(message, "model_dump_json"):
            return message.model_dump_json()
        return str(message)

    async def send_to_socket(self, websocket: WebSocket, message: Any) -> bool:
        """Send a message directly to a specific client WebSocket."""
        try:
            data = self._serialize_message(message)
            await websocket.send_text(data)
            return True
        except Exception as e:
            logger.warning(f"Error sending message to client: {e}")
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: Any):
        """Broadcast message to all connected clients (used for system telemetry)."""
        if not self.active_connections:
            return

        data = self._serialize_message(message)
        disconnected = set()
        for conn in list(self.active_connections):
            try:
                await conn.send_text(data)
            except Exception as e:
                logger.warning(f"Error broadcasting to client: {e}")
                disconnected.add(conn)

        for conn in disconnected:
            self.disconnect(conn)

    # Targeted / Per-Client Senders
    async def send_state_to(self, websocket: Optional[WebSocket], state: AssistantState, details: str = ""):
        msg = WSMessage(
            type=WSMessageType.STATE_CHANGE,
            payload={"state": state.value, "details": details}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_chat_to(self, websocket: Optional[WebSocket], role: str, content: str):
        msg = WSMessage(
            type=WSMessageType.CHAT,
            payload={"role": role, "content": content}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_tool_call_to(self, websocket: Optional[WebSocket], tool_name: str, args: dict):
        msg = WSMessage(
            type=WSMessageType.TOOL_CALL,
            payload={"tool": tool_name, "args": args}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_tool_result_to(self, websocket: Optional[WebSocket], tool_name: str, result: str):
        msg = WSMessage(
            type=WSMessageType.TOOL_RESULT,
            payload={"tool": tool_name, "result": result}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_audio_to(self, websocket: Optional[WebSocket], b64_audio: str, mime_type: str = "audio/mp3"):
        msg = WSMessage(
            type=WSMessageType.AUDIO_CHUNK,
            payload={"audio_base64": b64_audio, "mime_type": mime_type}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_audio_failed_to(self, websocket: Optional[WebSocket], text: str):
        msg = WSMessage(
            type=WSMessageType.AUDIO_FAILED,
            payload={"text": text}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_interrupt_to(self, websocket: Optional[WebSocket], reason: str = "Interrupted"):
        msg = WSMessage(
            type=WSMessageType.STATE_CHANGE,
            payload={"state": AssistantState.READY.value, "details": reason, "interrupted": True}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    async def send_error_to(self, websocket: Optional[WebSocket], error_text: str):
        msg = WSMessage(
            type=WSMessageType.ERROR,
            payload={"message": error_text}
        )
        if websocket:
            await self.send_to_socket(websocket, msg)
        else:
            await self.broadcast(msg)

    # Legacy broadcast methods for backwards-compatibility
    async def send_audio_failed(self, text: str):
        await self.send_audio_failed_to(None, text)

    async def send_state(self, state: AssistantState, details: str = ""):
        await self.send_state_to(None, state, details)

    async def send_chat(self, role: str, content: str):
        await self.send_chat_to(None, role, content)

    async def send_tool_call(self, tool_name: str, args: dict):
        await self.send_tool_call_to(None, tool_name, args)

    async def send_tool_result(self, tool_name: str, result: str):
        await self.send_tool_result_to(None, tool_name, result)

    async def send_audio(self, b64_audio: str, mime_type: str = "audio/mp3"):
        await self.send_audio_to(None, b64_audio, mime_type)

    async def send_interrupt(self, reason: str = "Interrupted"):
        await self.send_interrupt_to(None, reason)


ws_manager = ConnectionManager()
