import re
from backend.tools.registry import register_tool
from backend.brain.memory import memory

SAFE_KEY_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{1,50}$")


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
    },
    requires_system_action=False
)
def save_quick_note(content: str, category: str = "note", session_id: str = "default") -> str:
    if not isinstance(content, str) or not content.strip():
        return "Error: Note content must be a non-empty string."

    clean_content = content.strip()[:5000]
    clean_cat = str(category).strip()[:50] or "note"
    clean_cat = re.sub(r"[^a-zA-Z0-9_\-]", "", clean_cat) or "note"

    note_id = memory.add_note(clean_content, session_id=session_id, category=clean_cat)
    return f"I saved your note: '{clean_content}' (Note #{note_id})!"


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
    },
    requires_system_action=False
)
def remember_user_preference(key: str, value: str, session_id: str = "default") -> str:
    if not isinstance(key, str) or not key.strip():
        return "Error: Preference key must be a non-empty string."

    clean_key = key.strip().lower()
    if not SAFE_KEY_REGEX.match(clean_key):
        return f"Error: Invalid preference key '{key}'. Must be alphanumeric with underscores."

    if not isinstance(value, str):
        val_str = str(value)
    else:
        val_str = value.strip()

    clean_val = val_str[:1000]
    memory.set_pref(clean_key, clean_val, session_id=session_id)
    return f"Got it! I will remember that your {clean_key.replace('_', ' ')} is '{clean_val}'! 💖"
