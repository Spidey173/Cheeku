from backend.tools.registry import registry
# Import tool modules to trigger decorators
import backend.tools.system
import backend.tools.apps
import backend.tools.media
import backend.tools.search
import backend.tools.notes

__all__ = ["registry"]
