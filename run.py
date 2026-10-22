import sys
import os

# Auto-switch to project virtual environment if running with system python
current_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(current_dir, "venv", "bin", "python3")
if sys.prefix == sys.base_prefix and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

import uvicorn
import threading
import time
import webbrowser

# Ensure backend is in python path
sys.path.insert(0, current_dir)

from backend.app.config import settings

def open_browser():
    time.sleep(1.2)
    display_host = "localhost" if settings.HOST in ("0.0.0.0", "127.0.0.1") else settings.HOST
    url = f"http://{display_host}:{settings.PORT}"
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    display_host = "localhost" if settings.HOST in ("0.0.0.0", "127.0.0.1") else settings.HOST
    url = f"http://{display_host}:{settings.PORT}"
    print(f"""
    =================================================================
    🌸 CHEEKU AI // NEURAL VOICE OS CORE (HEADLESS BACKEND SERVER) 🌸
    =================================================================
    • Mode: Headless Server (Assistant running ONLY on Frontend)
    • Host: {settings.HOST}:{settings.PORT} (Debug: {settings.DEBUG})
    • Web Client & Interactive HUD: {url}
    • Voice, Speech & 3D Visuals: Active exclusively in browser
    
    🚀 Assistant is live! Opening in your browser now...
    =================================================================
    """)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        reload_dirs=[os.path.join(current_dir, "backend")] if settings.DEBUG else None
    )
