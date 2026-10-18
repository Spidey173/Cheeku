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

def open_browser():
    time.sleep(1.2)
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

if __name__ == "__main__":
    print("""
    =================================================================
    🌸 CHEEKU AI // NEURAL VOICE OS CORE (HEADLESS BACKEND SERVER) 🌸
    =================================================================
    • Mode: Headless Server (Assistant running ONLY on Frontend)
    • Terminal assistant execution: DISABLED (No host terminal audio)
    • Web Client & Interactive HUD: http://localhost:8000
    • Voice, Speech & 3D Visuals: Active exclusively in browser
    
    🚀 Assistant is live! Opening in your browser now...
    =================================================================
    """)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[os.path.join(current_dir, "backend")])
