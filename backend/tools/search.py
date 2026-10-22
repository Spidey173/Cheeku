import asyncio
import re
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
from backend.tools.registry import register_tool
from backend.utils.logger import logger


@register_tool(
    name="web_search",
    description="Search the web for real-time information, current news, answers to questions, or research topics.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query keywords to find"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of snippets to retrieve (default 3, max 10)",
                "default": 3
            }
        },
        "required": ["query"]
    },
    requires_system_action=False
)
async def web_search(query: str, max_results: int = 3) -> str:
    if not isinstance(query, str) or not query.strip():
        return "Error: Search query must be a non-empty string."

    if DDGS is None:
        return "Web search is unavailable (duckduckgo-search package is not installed)."

    clean_query = query.strip()[:300]
    clean_query = re.sub(r"[\x00-\x1f\x7f]", "", clean_query)

    try:
        limit = max(1, min(10, int(max_results)))
    except (ValueError, TypeError):
        limit = 3

    def _sync_search():
        ddgs = DDGS(timeout=6.0)
        return list(ddgs.text(clean_query, max_results=limit))

    try:
        results = await asyncio.wait_for(asyncio.to_thread(_sync_search), timeout=8.0)
        if not results:
            return f"No search results found for '{clean_query}'."

        snippets = []
        for r in results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            if title or body:
                snippets.append(f"• {title}: {body}")
        return "\n".join(snippets) if snippets else f"No descriptive results found for '{clean_query}'."
    except asyncio.TimeoutError:
        logger.warning(f"Web search for '{clean_query}' timed out.")
        return "Error: Web search request timed out."
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error conducting web search: {str(e)}"
