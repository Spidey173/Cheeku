from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

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
