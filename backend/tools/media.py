import sys
import re
import asyncio
import urllib.parse
import webbrowser
from typing import Optional
from backend.tools.registry import register_tool
from backend.app.config import settings
from backend.utils.logger import logger

ALLOWED_MEDIA_ACTIONS = {"play", "pause", "playpause", "next", "previous"}
YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")


async def run_applescript_async(script: str, timeout: float = 5.0) -> Optional[str]:
    """Execute AppleScript safely without blocking the event loop."""
    if sys.platform != "darwin":
        return None

    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace").strip()
        logger.warning(f"AppleScript error (code {proc.returncode}): {stderr.decode('utf-8', errors='replace').strip()}")
        return None
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("AppleScript execution timed out.")
        return None
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        raise


@register_tool(
    name="play_youtube_video",
    description="Find and play a video or music query on YouTube in the web browser.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Song name or video title to play directly"
            }
        },
        "required": ["query"]
    },
    requires_system_action=True
)
async def play_youtube_video(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        return "Error: YouTube search query must be a non-empty string."

    clean_query = query.strip()[:200]
    # Remove control characters
    clean_query = re.sub(r"[\x00-\x1f\x7f]", "", clean_query)
    logger.info(f"Resolving YouTube video for query: '{clean_query}'")

    target_url = None
    title = clean_query

    # Try resolving exact top video ID with yt-dlp
    try:
        cmd = ["yt-dlp", f"ytsearch1:{clean_query}", "--get-id", "--get-title"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
            if proc.returncode == 0:
                lines = stdout.decode("utf-8", errors="replace").strip().split("\n")
                if len(lines) >= 2:
                    raw_title = lines[0].split("|")[0].split("(")[0].strip()
                    raw_id = lines[1].strip()
                    if YOUTUBE_VIDEO_ID_REGEX.match(raw_id):
                        target_url = f"https://www.youtube.com/watch?v={raw_id}"
                        title = raw_title
                elif len(lines) == 1 and YOUTUBE_VIDEO_ID_REGEX.match(lines[0].strip()):
                    target_url = f"https://www.youtube.com/watch?v={lines[0].strip()}"
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            if isinstance(sys.exc_info()[1], asyncio.CancelledError):
                raise
    except FileNotFoundError:
        logger.info("yt-dlp executable not found, falling back to direct search URL.")
    except Exception as e:
        logger.warning(f"yt-dlp query failed: {e}")

    # Fallback to direct search query URL if video ID could not be resolved
    if not target_url:
        encoded = urllib.parse.quote_plus(clean_query)
        target_url = f"https://www.youtube.com/results?search_query={encoded}"

    # Open in browser safely
    try:
        if sys.platform == "darwin":
            proc = await asyncio.create_subprocess_exec("open", target_url)
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        else:
            await asyncio.to_thread(webbrowser.open, target_url)
        return f"Playing {title} on YouTube 🎶"
    except Exception as e:
        logger.error(f"Error opening YouTube URL: {e}")
        return f"Error playing YouTube video: {str(e)}"


@register_tool(
    name="control_media_player",
    description="Control audio and music playback on Spotify or Apple Music (play, pause, playpause, next, previous).",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["play", "pause", "playpause", "next", "previous"],
                "description": "Playback command to trigger"
            }
        },
        "required": ["action"]
    },
    requires_system_action=True
)
async def control_media_player(action: str) -> str:
    if sys.platform != "darwin":
        return "Media player control is only supported on macOS."

    clean_action = str(action).strip().lower()
    if clean_action not in ALLOWED_MEDIA_ACTIONS:
        return f"Error: Unsupported media action '{action}'. Allowed: {', '.join(sorted(ALLOWED_MEDIA_ACTIONS))}."

    # First attempt Spotify
    spotify_script = f'tell application "Spotify" to {clean_action}'
    res = await run_applescript_async(spotify_script, timeout=4.0)
    if res is not None:
        return f"Spotify: executed {clean_action}!"

    # Fallback to Apple Music
    music_script = f'tell application "Music" to {clean_action}'
    res2 = await run_applescript_async(music_script, timeout=4.0)
    if res2 is not None:
        return f"Music: executed {clean_action}!"

    return f"Triggered media action '{clean_action}'."


@register_tool(
    name="set_system_volume",
    description="Set computer master audio volume level from 0 to 100 percent.",
    parameters={
        "type": "object",
        "properties": {
            "volume_percent": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Desired volume percentage (0-100)"
            }
        },
        "required": ["volume_percent"]
    },
    requires_system_action=True
)
async def set_system_volume(volume_percent: int) -> str:
    if sys.platform != "darwin":
        return "Volume adjustment is only supported on macOS."

    try:
        val = int(volume_percent)
    except (ValueError, TypeError):
        return "Error: volume_percent must be an integer."

    clamped = max(0, min(100, val))
    script = f"set volume output volume {clamped}"
    await run_applescript_async(script, timeout=4.0)
    return f"Master volume set to {clamped}%."
