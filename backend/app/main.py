import asyncio
import os
import json
import psutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.assistant import orchestrator
from backend.app.websocket import ws_manager
from backend.models.schemas import WSMessage, WSMessageType, TelemetryData, AssistantState
import backend.tools  # Ensure all tool decorators are registered on startup
from backend.brain.memory import memory
from backend.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Cheeku AI Voice OS...")
    asyncio.create_task(orchestrator.initialize())
    telemetry_task = asyncio.create_task(broadcast_telemetry_loop())
    yield
    # Shutdown
    telemetry_task.cancel()
    logger.info("Cheeku AI shutting down. Goodbye!")

async def broadcast_telemetry_loop():
    """Periodically broadcast host system metrics to HUD."""
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            
            telemetry = TelemetryData(
                cpu_percent=cpu,
                ram_percent=ram.percent,
                ram_used_gb=round(ram.used / (1024 ** 3), 2),
                ram_total_gb=round(ram.total / (1024 ** 3), 2),
                battery_percent=round(battery.percent, 1) if battery else None,
                battery_plugged=battery.power_plugged if battery else None
            )
            
            msg = WSMessage(
                type=WSMessageType.TELEMETRY,
                payload=telemetry.model_dump()
            )
            await ws_manager.broadcast(msg)
        except Exception as e:
            logger.debug(f"Telemetry loop exception: {e}")
        await asyncio.sleep(2.0)

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial state and memories
        await websocket.send_text(
            WSMessage(
                type=WSMessageType.STATE_CHANGE,
                payload={"state": orchestrator.state.value, "details": "Connected to Cheeku Core."}
            ).model_dump_json()
        )
        
        # Send current user profile memory
        prefs = memory.get_all_prefs()
        await websocket.send_text(
            WSMessage(
                type=WSMessageType.MEMORY_UPDATE,
                payload={"preferences": prefs}
            ).model_dump_json()
        )

        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type")
                payload = data.get("payload", {})

                if msg_type in ["chat", "transcript"]:
                    user_text = payload.get("text", "") or payload.get("content", "")
                    asyncio.create_task(orchestrator.handle_user_input(user_text))

                elif msg_type == "audio":
                    # Audio chunk in base64
                    import base64
                    audio_b64 = payload.get("audio_base64", "")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        asyncio.create_task(orchestrator.handle_audio_stream(audio_bytes))

                elif msg_type == "state_change":
                    new_state = payload.get("state")
                    logger.info(f"Frontend requested state change: {new_state}")
                    if new_state == "READY":
                        # Only accept READY from frontend if currently speaking/generating, preventing stale audio events
                        if orchestrator.state in [AssistantState.SPEAKING, AssistantState.GENERATING]:
                            await orchestrator.set_state(AssistantState.READY, "Cheeku is ready!")
                        else:
                            logger.debug(f"Ignoring frontend READY: orchestrator is in [{orchestrator.state.value}]")

                elif msg_type == "interrupt":
                    logger.info("Frontend requested immediate interrupt.")
                    await orchestrator.interrupt("Client interrupt command")
                    await orchestrator.set_state(AssistantState.READY, "Cheeku is ready!")

            except json.JSONDecodeError:
                logger.warning(f"Received malformed WebSocket frame: {raw_text}")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        ws_manager.disconnect(websocket)

# Mount Frontend static files
if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(settings.STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Cheeku AI Backend Running. Static index.html not found yet."}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "state": orchestrator.state.value,
        "active_connections": len(ws_manager.active_connections)
    }
