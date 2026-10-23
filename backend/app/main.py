import asyncio
import os
import json
import base64
import uuid
import secrets
try:
    import psutil
except ImportError:
    psutil = None
from urllib.parse import urlparse
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from backend.app.config import settings
from backend.app.assistant import orchestrator, session_registry
from backend.app.websocket import ws_manager
from backend.models.schemas import (
    WSMessage,
    WSMessageType,
    TelemetryData,
    AssistantState,
    InboundMessage,
    InboundChatPayload,
    InboundAudioPayload,
    InboundStateChangePayload
)
import backend.tools  # Ensure all tool decorators are registered on startup
from backend.brain.memory import memory
from backend.utils.logger import logger


# Background task handles for graceful shutdown
background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Cheeku AI Voice OS Core...")
    init_task = asyncio.create_task(orchestrator.initialize())
    background_tasks.add(init_task)
    init_task.add_done_callback(background_tasks.discard)

    telemetry_task = asyncio.create_task(broadcast_telemetry_loop())
    background_tasks.add(telemetry_task)

    yield

    # Graceful Shutdown
    logger.info("Cheeku AI shutting down. Cleaning up background tasks...")
    telemetry_task.cancel()
    try:
        await telemetry_task
    except (asyncio.CancelledError, Exception):
        pass

    # Cancel and await all active sessions
    await session_registry.shutdown_all()
    await orchestrator.shutdown()

    # Cancel any remaining background tasks
    for task in list(background_tasks):
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
    background_tasks.clear()
    logger.info("Cheeku AI shutdown complete. Goodbye!")


async def broadcast_telemetry_loop():
    """Periodically broadcast host system metrics to HUD."""
    while True:
        try:
            if psutil is None:
                await asyncio.sleep(5.0)
                continue

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
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Telemetry loop exception: {e}")
        await asyncio.sleep(2.0)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ALLOW_ALL_ORIGINS else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add defensive security headers to all HTTP responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def is_origin_allowed(origin: Optional[str], client_host: Optional[str] = None) -> bool:
    """Verifies whether the WebSocket Origin header is permitted."""
    if settings.ALLOW_ALL_ORIGINS:
        return True

    # If Origin header is not sent (e.g. curl, test client, local script)
    if not origin:
        if client_host in ("127.0.0.1", "localhost", "testclient", "::1", None):
            return True
        return False

    normalized_origin = origin.rstrip("/").lower()
    allowed_set = {o.rstrip("/").lower() for o in settings.ALLOWED_ORIGINS}
    if normalized_origin in allowed_set:
        return True

    # Check origin netloc (host:port match)
    parsed = urlparse(normalized_origin)
    origin_netloc = parsed.netloc
    for allowed in allowed_set:
        if urlparse(allowed).netloc == origin_netloc:
            return True

    return False


def is_authenticated(websocket: WebSocket) -> bool:
    """Validates WebSocket authentication credentials."""
    expected_token = settings.AUTH_TOKEN

    # If auth token is not set and auth not strictly required, allow safe local dev
    if not expected_token and not settings.WS_AUTH_REQUIRED:
        return True

    if not expected_token:
        # Auth is required but no token is configured in environment
        logger.error("WS_AUTH_REQUIRED is true but AUTH_TOKEN is not configured in settings.")
        return False

    # Check query param ?token=...
    token = websocket.query_params.get("token")

    # Check Authorization header: Bearer <token>
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        return False

    return secrets.compare_digest(token, expected_token)


# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    client_host = websocket.client.host if websocket.client else None

    # 1. Validate Origin to prevent Cross-Site WebSocket Hijacking
    if not is_origin_allowed(origin, client_host):
        logger.warning(f"Rejected WebSocket connection from unauthorized origin: {origin}")
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    # 2. Validate Authentication
    if not is_authenticated(websocket):
        logger.warning(f"Rejected unauthenticated WebSocket connection from {client_host}")
        await websocket.close(code=1008, reason="Authentication required")
        return

    # 3. Establish connection
    await ws_manager.connect(websocket)

    # 4. Bind to session orchestrator (supports initial generation or legacy query params)
    req_session_id = websocket.query_params.get("session_id")
    req_session_token = websocket.query_params.get("session_token")
    session_id, session_token, session_orch, was_resumed = session_registry.get_or_resume(
        req_session_id, req_session_token, websocket
    )

    try:
        # Send initial state and memories to this specific client
        await ws_manager.send_state_to(
            websocket,
            session_orch.state,
            "Connected to Cheeku Core."
        )

        # Notify client of its authenticated session credentials
        await ws_manager.send_to_socket(
            websocket,
            WSMessage(
                type=WSMessageType.COMMAND,
                payload={
                    "command": "session_init",
                    "session_id": session_id,
                    "session_token": session_token,
                    "resumed": was_resumed
                }
            )
        )

        # Send session-isolated preferences
        prefs = memory.get_all_prefs(session_id=session_id)
        await ws_manager.send_to_socket(
            websocket,
            WSMessage(
                type=WSMessageType.MEMORY_UPDATE,
                payload={"preferences": prefs}
            )
        )

        while True:
            raw_text = await websocket.receive_text()

            # Enforce max payload frame size
            if len(raw_text) > settings.MAX_PAYLOAD_BYTES:
                logger.warning(f"[{session_id}] Rejected oversized WebSocket frame: {len(raw_text)} bytes")
                await ws_manager.send_error_to(websocket, "Payload size exceeds maximum allowed limit.")
                continue

            # Parse JSON frame safely
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning(f"[{session_id}] Received malformed JSON WebSocket frame.")
                await ws_manager.send_error_to(websocket, "Malformed JSON frame received.")
                continue

            # Validate message structure with Pydantic
            try:
                inbound = InboundMessage.model_validate(data)
            except ValidationError as ve:
                logger.warning(f"[{session_id}] Invalid inbound message schema: {ve}")
                await ws_manager.send_error_to(websocket, "Invalid message format.")
                continue

            msg_type = inbound.type
            payload = inbound.payload

            # In-band session resumption (avoids exposing session tokens in URL query params or access logs)
            if msg_type in ["session_resume", "authenticate"]:
                res_id = payload.get("session_id")
                res_tok = payload.get("session_token")
                user_id = payload.get("user_id")
                if res_id and res_tok:
                    new_id, new_tok, new_orch, resumed_ok = session_registry.get_or_resume(
                        res_id, res_tok, websocket, user_id=user_id
                    )
                    if resumed_ok:
                        old_temp_id = session_id
                        session_id = new_id
                        session_token = new_tok
                        session_orch = new_orch
                        if old_temp_id != new_id:
                            await session_registry.remove_session(old_temp_id)
                        logger.info(f"Session '{session_id}' successfully resumed in-band.")
                        await ws_manager.send_to_socket(
                            websocket,
                            WSMessage(
                                type=WSMessageType.COMMAND,
                                payload={
                                    "command": "session_init",
                                    "session_id": session_id,
                                    "session_token": session_token,
                                    "resumed": True
                                }
                            )
                        )
                        prefs = memory.get_all_prefs(session_id=session_id)
                        await ws_manager.send_to_socket(
                            websocket,
                            WSMessage(
                                type=WSMessageType.MEMORY_UPDATE,
                                payload={"preferences": prefs}
                            )
                        )
                    else:
                        logger.warning(f"In-band session resumption rejected for session '{res_id}'.")
                continue

            if msg_type in ["chat", "transcript"]:
                try:
                    chat_data = InboundChatPayload.model_validate(payload)
                    user_text = chat_data.clean_text
                    if user_text:
                        asyncio.create_task(session_orch.handle_user_input(user_text))
                except ValidationError:
                    await ws_manager.send_error_to(websocket, "Invalid chat payload.")

            elif msg_type == "audio":
                try:
                    audio_data = InboundAudioPayload.model_validate(payload)
                    audio_bytes = base64.b64decode(audio_data.audio_base64)
                    asyncio.create_task(session_orch.handle_audio_stream(audio_bytes))
                except Exception as audio_err:
                    logger.warning(f"[{session_id}] Audio decoding error: {audio_err}")
                    await ws_manager.send_error_to(websocket, "Invalid audio payload.")

            elif msg_type == "state_change":
                try:
                    state_data = InboundStateChangePayload.model_validate(payload)
                    new_state = state_data.state
                    logger.info(f"[{session_id}] Client reported state: {new_state}")
                    if new_state == "READY":
                        # Only accept READY transition from client if currently speaking/generating
                        if session_orch.state in [AssistantState.SPEAKING, AssistantState.GENERATING]:
                            await session_orch.set_state(AssistantState.READY, "Cheeku is ready!")
                        else:
                            logger.debug(f"[{session_id}] Ignoring client READY: state is [{session_orch.state.value}]")
                except ValidationError:
                    await ws_manager.send_error_to(websocket, "Invalid state_change payload.")

            elif msg_type == "interrupt":
                logger.info(f"[{session_id}] Client requested immediate interrupt.")
                await session_orch.interrupt("Client interrupt command")
                await session_orch.set_state(AssistantState.READY, "Cheeku is ready!", force=True)

            elif msg_type == "authenticate":
                # Already authenticated; frame ignored gracefully
                logger.debug(f"[{session_id}] Received redundant in-band authenticate message on active session.")
                continue

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        await session_registry.on_disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"[{session_id}] WebSocket connection error: {e}")
        ws_manager.disconnect(websocket)
        await session_registry.on_disconnect(session_id, websocket)


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
    """Health check endpoint without leaking sensitive environment or server details."""
    return {
        "status": "healthy",
        "active_sessions": session_registry.count(),
        "active_connections": len(ws_manager.active_connections)
    }
