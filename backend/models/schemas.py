from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AssistantState(str, Enum):
    BOOTING = "BOOTING"
    READY = "READY"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    CALLING_TOOL = "CALLING_TOOL"
    GENERATING = "GENERATING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: Optional[str] = ""
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None
    timestamp: Optional[float] = None


class WSMessageType(str, Enum):
    STATE_CHANGE = "state_change"
    CHAT = "chat"
    TRANSCRIPT = "transcript"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AUDIO_CHUNK = "audio_chunk"
    TELEMETRY = "telemetry"
    MEMORY_UPDATE = "memory_update"
    ERROR = "error"
    COMMAND = "command"
    AUDIO_FAILED = "audio_failed"


class WSMessage(BaseModel):
    type: WSMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class TelemetryData(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None
    status: str = "nominal"


# --- Inbound Client Message Validation Models ---

class InboundChatPayload(BaseModel):
    text: Optional[str] = Field(default="", max_length=10000)
    content: Optional[str] = Field(default="", max_length=10000)

    @property
    def clean_text(self) -> str:
        return (self.text or self.content or "").strip()


class InboundAudioPayload(BaseModel):
    audio_base64: str = Field(..., max_length=5_000_000)
    mime_type: Optional[str] = Field(default="audio/wav", max_length=100)


class InboundStateChangePayload(BaseModel):
    state: str = Field(..., max_length=50)


class InboundMessage(BaseModel):
    type: str = Field(..., max_length=50)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"chat", "transcript", "audio", "state_change", "interrupt"}
        if v not in allowed:
            raise ValueError(f"Unsupported message type '{v}'. Allowed: {', '.join(sorted(allowed))}")
        return v
