import json
import httpx
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.models.schemas import ChatMessage, MessageRole
from backend.brain.personality import get_system_prompt
from backend.brain.memory import memory
from backend.tools.registry import registry
from backend.utils.logger import logger


class GroqBrainClient:
    """
    Ultra-fast Cloud Neural Brain powered by Groq LPU (qwen/qwen3.8-27b).
    Provides sub-second conversational latency, sweet personality, and autonomous tool calling.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def is_online(self) -> bool:
        """Verifies Groq API connectivity and authentication."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self.headers)
                return res.status_code == 200
        except Exception as e:
            logger.warning(f"Groq API health check failed: {e}")
            return False

    async def generate_response(
        self,
        messages: List[ChatMessage]
    ) -> Dict[str, Any]:
        """
        Sends dialogue history and tool definitions to Groq chat completions.
        Returns generated content and any requested tool calls.
        """
        user_name = memory.get_pref("user_name")
        context_notes = memory.get_context_summary()
        sys_prompt = get_system_prompt(user_name, context_notes)

        # Build message history for OpenAI-compatible endpoint
        api_messages = [{"role": "system", "content": sys_prompt}]
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role.value, "content": m.content or ""}
            if m.tool_calls:
                msg_dict["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            api_messages.append(msg_dict)

        tools = registry.get_all_schemas()

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "temperature": settings.TEMPERATURE,
            "max_tokens": 512
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=18.0) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )

                if res.status_code == 200:
                    data = res.json()
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content", "") or ""
                    tool_calls = message.get("tool_calls", []) or []

                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "success": True
                    }
                else:
                    logger.error(f"Groq API returned error status {res.status_code}: {res.text}")
                    return {
                        "content": f"Groq API error ({res.status_code}). Please check API settings.",
                        "tool_calls": [],
                        "success": False
                    }

        except httpx.TimeoutException:
            logger.error("Groq API request timed out.")
            return {
                "content": "My thoughts took a moment too long! I am still right here with you.",
                "tool_calls": [],
                "success": False
            }
        except Exception as e:
            logger.error(f"Groq chat execution error: {e}", exc_info=True)
            return {
                "content": f"I had a slight neural hiccup: {str(e)}",
                "tool_calls": [],
                "success": False
            }


groq_client = GroqBrainClient()
