from backend.tools.registry import register_tool
from backend.brain.memory import memory

@register_tool(
    name="save_quick_note",
    description="Save a quick note, reminder, or idea to Cheeku's memory.",
    parameters={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The note or task content to save"
            },
            "category": {
                "type": "string",
                "description": "Category for the note, e.g. 'work', 'todo', 'idea'",
                "default": "note"
            }
        },
        "required": ["content"]
    }
)
def save_quick_note(content: str, category: str = "note"):
    note_id = memory.add_note(content, category)
    return f"I saved your note: '{content}' (Note #{note_id})!"

@register_tool(
    name="remember_user_preference",
    description="Remember a permanent fact, preference, or detail about the user (e.g. user's name, favorite music genre, favorite IDE, coffee preference).",
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "The key or aspect to remember, e.g. 'user_name', 'favorite_song', 'favorite_drink'"
            },
            "value": {
                "type": "string",
                "description": "The value or information to store"
            }
        },
        "required": ["key", "value"]
    }
)
def remember_user_preference(key: str, value: str):
    memory.set_pref(key, value)
    return f"Got it! I will always remember that your {key.replace('_', ' ')} is '{value}'! 💖"
