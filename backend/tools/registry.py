import inspect
from typing import Callable, Dict, Any, List
from backend.models.schemas import ToolDefinition
from backend.utils.logger import logger

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Decorator to register a tool function with its JSON schema."""
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
            logger.info(f"Registered tool: [{name}] - {description}")
            return func
        return decorator

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

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
        try:
            logger.info(f"Executing tool '{name}' with args: {args}")
            if inspect.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = func(**args)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return f"Error executing {name}: {str(e)}"

registry = ToolRegistry()
register_tool = registry.register
