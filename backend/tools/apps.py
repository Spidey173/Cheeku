import sys
import re
import asyncio
import urllib.parse
import webbrowser
from backend.tools.registry import register_tool
from backend.app.config import settings
from backend.utils.logger import logger

# Strict regex for application names: alphanumeric, spaces, dots, hyphens
SAFE_APP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9\.\- ]{1,100}$")


@register_tool(
    name="launch_application",
    description="Launch or open an authorized desktop application on macOS (e.g. Chrome, Spotify, Visual Studio Code, Terminal, Slack, Notes, Calculator).",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Name of the application to open, e.g. 'Spotify', 'Google Chrome', 'Notes', 'Visual Studio Code'"
            }
        },
        "required": ["app_name"]
    },
    requires_system_action=True
)
async def launch_application(app_name: str) -> str:
    if sys.platform != "darwin":
        return "Error: Launching desktop applications is only supported on macOS."

    if not isinstance(app_name, str):
        return "Error: Application name must be a string."

    clean_name = app_name.strip()
    if not clean_name or not SAFE_APP_NAME_PATTERN.match(clean_name) or clean_name.startswith("-"):
        return f"Error: Invalid application name '{app_name}'. Application names must be alphanumeric and cannot contain path separators or flags."

    # Whitelist enforcement
    allowed_map = {app.lower(): app for app in settings.ALLOWED_SYSTEM_APPS}
    target_app = allowed_map.get(clean_name.lower())
    if not target_app:
        allowed_list_str = ", ".join(settings.ALLOWED_SYSTEM_APPS)
        return f"Error: '{clean_name}' is not in the authorized applications whitelist. Authorized apps: {allowed_list_str}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "open", "-a", target_app,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode == 0:
                return f"Successfully opened {target_app} for you!"
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            return f"Could not open {target_app}: {err_msg or 'exit code ' + str(proc.returncode)}"
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"Error: Timed out trying to launch {target_app}."
        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            raise
    except Exception as e:
        logger.error(f"Failed to launch application '{target_app}': {e}")
        return f"Error launching {target_app}: {str(e)}"


@register_tool(
    name="open_website",
    description="Open a validated web URL in the default web browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open, e.g. 'https://youtube.com' or 'https://github.com'"
            }
        },
        "required": ["url"]
    },
    requires_system_action=True
)
async def open_website(url: str) -> str:
    if not isinstance(url, str):
        return "Error: URL must be a string."

    clean_url = url.strip()
    if len(clean_url) > 2048:
        return "Error: URL exceeds maximum supported length."

    # Prevent control characters or command injection in URL
    if any(c in clean_url for c in ("\n", "\r", "\x00")):
        return "Error: URL contains illegal characters."

    parsed = urllib.parse.urlparse(clean_url)
    if parsed.scheme:
        if parsed.scheme.lower() not in ("http", "https"):
            return f"Error: Unsupported URL scheme '{parsed.scheme}'. Only http and https URLs are allowed."
    else:
        clean_url = "https://" + clean_url
        parsed = urllib.parse.urlparse(clean_url)

    if not parsed.netloc:
        return f"Error: Invalid web address '{url}'. Missing valid host domain."

    try:
        if sys.platform == "darwin":
            proc = await asyncio.create_subprocess_exec(
                "open", clean_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                if proc.returncode == 0:
                    return f"Opened {clean_url} in your browser!"
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                return f"Could not open {clean_url}: {err_msg}"
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return f"Error: Timed out opening {clean_url}."
            except asyncio.CancelledError:
                proc.kill()
                await proc.wait()
                raise
        else:
            # Cross-platform fallback using webbrowser in worker thread
            await asyncio.to_thread(webbrowser.open, clean_url)
            return f"Opened {clean_url} in your browser!"
    except Exception as e:
        logger.error(f"Failed to open URL '{clean_url}': {e}")
        return f"Error opening URL: {str(e)}"
