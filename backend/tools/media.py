import subprocess
import urllib.parse
from backend.tools.registry import register_tool
from backend.utils.logger import logger

def run_applescript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return res.stdout.strip()

@register_tool(
    name="play_youtube_video",
    description="Find and immediately play the top video/song on YouTube in the web browser (e.g. 'Dheere Dheere', 'lofi beats', 'popular songs').",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Song name or video title to play directly"
            }
        },
        "required": ["query"]
    }
)
def play_youtube_video(query: str):
    """
    Uses yt-dlp to resolve the exact top video URL and opens it directly so it starts playing immediately!
    """
    logger.info(f"Resolving direct YouTube video for: {query}")
    try:
        # Search yt-dlp for top 1 result ID
        cmd = ["yt-dlp", f"ytsearch1:{query}", "--get-id", "--get-title"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        lines = res.stdout.strip().split("\n")
        
        if len(lines) >= 2:
            title = lines[0].split("|")[0].split("(")[0].strip()
            video_id = lines[1]
            direct_url = f"https://www.youtube.com/watch?v={video_id}"
            subprocess.run(["open", direct_url])
            return f"Playing {title} on YouTube 🎶"
        elif len(lines) == 1 and lines[0]:
            video_id = lines[0]
            direct_url = f"https://www.youtube.com/watch?v={video_id}"
            subprocess.run(["open", direct_url])
            return f"Playing {query} on YouTube 🎶"
    except Exception as e:
        logger.warning(f"yt-dlp quick resolve timed out or failed: {e}. Falling back to search redirect.")

    # Fallback: direct query URL
    encoded = urllib.parse.quote_plus(query)
    direct_url = f"https://www.youtube.com/results?search_query={encoded}"
    subprocess.run(["open", direct_url])
    return f"Opening YouTube for {query} 🎶"

@register_tool(
    name="control_media_player",
    description="Control audio and music playback on Spotify or Apple Music (play, pause, next track, previous track).",
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
    }
)
def control_media_player(action: str):
    spotify_script = f'tell application "Spotify" to {action}'
    res = subprocess.run(["osascript", "-e", spotify_script], capture_output=True, text=True)
    if res.returncode == 0:
        return f"Spotify: executed {action}!"
    
    music_script = f'tell application "Music" to {action}'
    res2 = subprocess.run(["osascript", "-e", music_script], capture_output=True, text=True)
    if res2.returncode == 0:
        return f"Music: executed {action}!"
    return f"Triggered media action {action}."

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
    }
)
def set_system_volume(volume_percent: int):
    script = f"set volume output volume {volume_percent}"
    run_applescript(script)
    return f"Master volume set to {volume_percent}%."
