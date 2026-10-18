import os
import subprocess
from backend.tools.registry import register_tool

@register_tool(
    name="launch_application",
    description="Launch or open any installed desktop application on macOS (e.g. Chrome, Spotify, Visual Studio Code, Terminal, Slack, Notes, Calculator).",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Name of the application to open, e.g. 'Spotify', 'Google Chrome', 'Notes', 'Visual Studio Code'"
            }
        },
        "required": ["app_name"]
    }
)
def launch_application(app_name: str):
    cmd = ["open", "-a", app_name]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return f"Successfully opened {app_name} for you!"
    else:
        # Try generic open in case of file or URL
        res2 = subprocess.run(["open", app_name], capture_output=True, text=True)
        if res2.returncode == 0:
            return f"Opened {app_name}!"
        return f"Could not open {app_name}: {res.stderr.strip()}"

@register_tool(
    name="open_website",
    description="Open any website URL in the default web browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open, e.g. 'https://youtube.com' or 'https://github.com'"
            }
        },
        "required": ["url"]
    }
)
def open_website(url: str):
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    subprocess.run(["open", url])
    return f"Opened {url} in your browser!"
