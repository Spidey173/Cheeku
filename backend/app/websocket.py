import asyncio
import json
from typing import Set
from fastapi import WebSocket
from backend.models.schemas import WSMessage, WSMessageType, AssistantState
from backend.utils.logger import logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Any):
        if not self.active_connections:
            return
        if isinstance(message, dict):
            data = json.dumps(message)
        elif hasattr(message, "model_dump_json"):
            data = message.model_dump_json()
        else:
            data = str(message)

        disconnected = set()
        for conn in self.active_connections:
            try:
                await conn.send_text(data)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket client: {e}")
                disconnected.add(conn)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_audio_failed(self, text: str):
        msg = WSMessage(
            type=WSMessageType.AUDIO_FAILED,
            payload={"text": text}
        )
        await self.broadcast(msg)

    async def send_state(self, state: AssistantState, details: str = ""):
        msg = WSMessage(
            type=WSMessageType.STATE_CHANGE,
            payload={"state": state.value, "details": details}
        )
        await self.broadcast(msg)

    async def send_chat(self, role: str, content: str):
        msg = WSMessage(
            type=WSMessageType.CHAT,
            payload={"role": role, "content": content}
        )
        await self.broadcast(msg)

    async def send_tool_call(self, tool_name: str, args: dict):
        msg = WSMessage(
            type=WSMessageType.TOOL_CALL,
            payload={"tool": tool_name, "args": args}
        )
        await self.broadcast(msg)

    async def send_tool_result(self, tool_name: str, result: str):
        msg = WSMessage(
            type=WSMessageType.TOOL_RESULT,
            payload={"tool": tool_name, "result": result}
        )
        await self.broadcast(msg)

    async def send_audio(self, b64_audio: str, mime_type: str = "audio/mp3"):
        msg = WSMessage(
            type=WSMessageType.AUDIO_CHUNK,
            payload={"audio_base64": b64_audio, "mime_type": mime_type}
        )
        await self.broadcast(msg)

    async def send_interrupt(self, reason: str = "Interrupted"):
        msg = WSMessage(
            type=WSMessageType.STATE_CHANGE,
            payload={"state": AssistantState.READY.value, "details": reason, "interrupted": True}
        )
        await self.broadcast(msg)

ws_manager = ConnectionManager()
