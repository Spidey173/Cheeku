import asyncio
import inspect
from typing import Callable, Dict, Any, List
from backend.models.schemas import ToolDefinition
from backend.app.config import settings
from backend.utils.logger import logger


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolDefinition] = {}
        self._requires_system_action: Dict[str, bool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        requires_system_action: bool = False
    ):
        """Decorator to register a tool function with its JSON schema and authorization requirements."""
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
            self._requires_system_action[name] = requires_system_action
            logger.info(f"Registered tool: [{name}] (system_action={requires_system_action}) - {description}")
            return func
        return decorator

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

    def is_system_action(self, name: str) -> bool:
        return self._requires_system_action.get(name, False)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns schemas formatted for Groq/OpenAI tool calling."""
        formatted = []
        for name, tool_def in self._schemas.items():
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.parameters
                }
            })
        return formatted

    async def execute(self, name: str, args: Dict[str, Any]) -> Any:
        func = self.get_tool(name)
        if not func:
            return f"Error: Tool '{name}' not found."

        # Check authorization for system-action tools
        if self.is_system_action(name) and not settings.ENABLE_SYSTEM_ACTIONS:
            msg = f"System action '{name}' is disabled by policy. Set ENABLE_SYSTEM_ACTIONS=true to enable."
            logger.warning(msg)
            return msg

        try:
            logger.info(f"Executing tool '{name}' (keys: {list(args.keys())})")
            if inspect.iscoroutinefunction(func):
                coro = func(**args)
            else:
                coro = asyncio.to_thread(func, **args)

            result = await asyncio.wait_for(coro, timeout=settings.REQUEST_TIMEOUT_SECONDS)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Tool '{name}' execution timed out after {settings.REQUEST_TIMEOUT_SECONDS}s.")
            return f"Error: Tool '{name}' timed out."
        except asyncio.CancelledError:
            logger.info(f"Tool '{name}' execution was cancelled.")
            raise
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return f"Error executing {name}: {str(e)}"


registry = ToolRegistry()
register_tool = registry.register
