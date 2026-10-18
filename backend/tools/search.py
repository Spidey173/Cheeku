from duckduckgo_search import DDGS
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
                "description": "Number of snippets to retrieve (default 3)",
                "default": 3
            }
        },
        "required": ["query"]
    }
)
def web_search(query: str, max_results: int = 3):
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No search results found for '{query}'."
        
        snippets = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            snippets.append(f"• {title}: {body}")
        return "\n".join(snippets)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error conducting web search: {str(e)}"
