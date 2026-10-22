import asyncio
import json
import time
import secrets
from typing import Optional, Dict, Set, Any, List, Tuple
from fastapi import WebSocket
from backend.models.schemas import AssistantState, ChatMessage, MessageRole
from backend.brain.groq import groq_client
from backend.brain.memory import memory
import backend.tools  # Ensure all tool decorators are registered on import
from backend.tools.registry import registry
from backend.audio.stt import stt
from backend.audio.tts import tts
from backend.app.websocket import ws_manager
from backend.app.config import settings
from backend.utils.logger import logger

# Deterministic Finite State Machine Transition Matrix
ALLOWED_TRANSITIONS: Dict[AssistantState, Set[AssistantState]] = {
    AssistantState.BOOTING: {
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.READY: {
        AssistantState.LISTENING,
        AssistantState.TRANSCRIBING,
        AssistantState.THINKING,
        AssistantState.BOOTING,
        AssistantState.ERROR,
    },
    AssistantState.LISTENING: {
        AssistantState.TRANSCRIBING,
        AssistantState.THINKING,
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.TRANSCRIBING: {
        AssistantState.THINKING,
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.THINKING: {
        AssistantState.CALLING_TOOL,
        AssistantState.GENERATING,
        AssistantState.SPEAKING,
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.CALLING_TOOL: {
        AssistantState.GENERATING,
        AssistantState.THINKING,
        AssistantState.SPEAKING,
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.GENERATING: {
        AssistantState.SPEAKING,
        AssistantState.READY,
        AssistantState.ERROR,
    },
    AssistantState.SPEAKING: {
        AssistantState.READY,
        AssistantState.LISTENING,
        AssistantState.THINKING,
        AssistantState.ERROR,
    },
    AssistantState.ERROR: {
        AssistantState.READY,
        AssistantState.BOOTING,
    },
}


class AssistantOrchestrator:
    """
    Controller for Cheeku AI Voice OS Assistant session.
    Coordinates Deterministic State Machine, Task Cancellation, Groq Brain, Tools, and Audio per session.
    """
    def __init__(self, session_id: str = "default", websocket: Optional[WebSocket] = None):
        self.session_id: str = session_id
        self.websocket: Optional[WebSocket] = websocket
        self.state: AssistantState = AssistantState.BOOTING
        self.is_processing: bool = False
        self._current_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None
        self._last_state_time: float = time.time()
        self._state_lock: asyncio.Lock = asyncio.Lock()
        self.short_term_history: List[ChatMessage] = []

    def can_transition(self, target: AssistantState) -> bool:
        """Checks if moving from current state to target state is legally permitted by FSM."""
        return target in ALLOWED_TRANSITIONS.get(self.state, set())

    async def initialize(self):
        """Bootstraps subsystems, checks Groq brain, and transitions to READY."""
        logger.info(f"Orchestrator [{self.session_id}] booting up...")
        await self.set_state(AssistantState.BOOTING, "Connecting to Groq Neural Brain...", force=True)

        groq_ok = await groq_client.is_online()
        if groq_ok:
            logger.info("Groq Cloud Brain is ONLINE.")
        else:
            logger.warning("Groq API connection check failed. Verify GROQ_API_KEY in .env.")

        await asyncio.sleep(0.1)
        await self.set_state(AssistantState.READY, "Cheeku is ready and listening! 💖")

    def add_history(
        self,
        role: MessageRole,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None
    ):
        """Adds a message to this session's isolated short-term memory."""
        msg = ChatMessage(
            role=role,
            content=content or "",
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            name=name,
            timestamp=time.time()
        )
        self.short_term_history.append(msg)
        if len(self.short_term_history) > settings.MAX_HISTORY_TURNS * 2:
            self.short_term_history = self.short_term_history[-settings.MAX_HISTORY_TURNS * 2:]

        # Also persist to session-isolated database log
        memory.add_short_term(
            role=role,
            content=content,
            session_id=self.session_id,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            name=name
        )

    async def set_state(self, new_state: AssistantState, details: str = "", force: bool = False) -> bool:
        """
        Enforces deterministic state transitions with audit logging and targeted telemetry.
        Returns True if transition occurred, False if rejected by FSM.
        """
        async with self._state_lock:
            if self.state == new_state:
                await ws_manager.send_state_to(self.websocket, new_state, details)
                return True

            if not force and not self.can_transition(new_state):
                logger.warning(
                    f"[{self.session_id}] Blocked invalid FSM transition: [{self.state.value}] -> [{new_state.value}] | details: '{details}'"
                )
                return False

            now = time.time()
            duration = now - self._last_state_time
            old_state = self.state

            self.state = new_state
            self._last_state_time = now

            logger.info(
                f"[{self.session_id}] FSM Transition: [{old_state.value}] -> [{new_state.value}] (stayed {duration:.2f}s) | details: {details}"
            )
            await ws_manager.send_state_to(self.websocket, new_state, details)
            return True

    async def interrupt(self, reason: str = "User interruption"):
        """
        Cancels any in-flight LLM request, tool execution, or audio synthesis task cleanly.
        Enables instantaneous voice barge-in without orphaned tasks or state drift.
        """
        logger.info(f"[{self.session_id}] Interrupting active pipeline: reason='{reason}'")

        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            self._timeout_task = None

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._current_task), timeout=0.3)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
            self._current_task = None

        self.is_processing = False
        await ws_manager.send_interrupt_to(self.websocket, reason)

    async def shutdown(self):
        """Awaits and cleans up all active tasks for this session during shutdown or disconnect."""
        logger.info(f"[{self.session_id}] Shutting down session orchestrator...")
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except (asyncio.CancelledError, Exception):
                pass
            self._timeout_task = None

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except (asyncio.CancelledError, Exception):
                pass
            self._current_task = None

        self.is_processing = False

    async def handle_user_input(self, user_text: str):
        """
        Entry point for user input (voice transcript or chat).
        If already processing, cancels previous turn immediately to service the new input.
        """
        clean_text = user_text.strip() if user_text else ""
        if not clean_text:
            return

        # Barge-in: If a turn is already executing, cancel it cleanly
        if self.is_processing or (self._current_task and not self._current_task.done()):
            logger.info(f"[{self.session_id}] Barge-in detected: interrupting in-flight turn for incoming user input.")
            await self.interrupt("Barge-in on new user input")

        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            self._timeout_task = None

        # Execute turn as tracked asyncio task
        self._current_task = asyncio.create_task(self._process_turn(clean_text))
        try:
            await self._current_task
        except asyncio.CancelledError:
            logger.info(f"[{self.session_id}] Active turn task cancelled cleanly during execution.")
        finally:
            if self._current_task and self._current_task.done():
                self._current_task = None

    async def _process_turn(self, user_text: str):
        """
        Internal turn pipeline:
        User Text -> Thinking -> Tool Execution -> Generation -> Speech Synthesis -> Ready.
        """
        self.is_processing = True
        try:
            # 1. Register User Message in session history
            self.add_history(MessageRole.USER, user_text)
            await ws_manager.send_chat_to(self.websocket, "user", user_text)

            # 2. State: THINKING
            await self.set_state(AssistantState.THINKING, "Consulting Groq Neural Brain...")

            # 3. Call Brain (Groq qwen/qwen3.8-27b) using session history
            response = await groq_client.generate_response(self.short_term_history)

            tool_calls = response.get("tool_calls", [])
            reply_text = response.get("content", "")

            # 4. Handle Tool Calls
            if tool_calls:
                self.add_history(
                    MessageRole.ASSISTANT,
                    reply_text or "",
                    tool_calls=tool_calls
                )

                await self.set_state(AssistantState.CALLING_TOOL, "Executing system directive...")
                for call in tool_calls:
                    call_id = call.get("id", "")
                    fn = call.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}

                    label = {
                        "play_youtube_video": "Searching & Streaming YouTube",
                        "control_media_player": "Media Playback Control",
                        "set_system_volume": "Adjusting Master Volume",
                        "get_system_telemetry": "Scanning Hardware Vitals",
                        "get_current_time_and_date": "Checking Chronometer",
                        "web_search": "Querying Neural Web",
                        "save_quick_note": "Writing to Neural Memory",
                        "launch_application": "Launching Application",
                        "open_website": "Opening Web Target"
                    }.get(fn_name, (fn_name or "Tool").replace("_", " ").title())

                    detail = (
                        fn_args.get("query")
                        or fn_args.get("action")
                        or fn_args.get("app_name")
                        or fn_args.get("note")
                        or ""
                    )

                    await ws_manager.send_tool_call_to(
                        self.websocket,
                        fn_name,
                        {"args": fn_args, "title": label, "detail": detail, "status": "active"}
                    )

                    # Execute tool safely
                    tool_output = await registry.execute(fn_name, fn_args)
                    await ws_manager.send_tool_result_to(
                        self.websocket,
                        fn_name,
                        json.dumps({"output": str(tool_output), "title": label, "detail": detail, "status": "done"})
                    )

                    # Feed tool result back to session history
                    self.add_history(
                        MessageRole.TOOL,
                        str(tool_output),
                        tool_call_id=call_id,
                        name=fn_name
                    )

                # Formulate natural conversational reply from tool results
                await self.set_state(AssistantState.GENERATING, "Formulating voice reply...")
                followup = await groq_client.generate_response(self.short_term_history)
                reply_text = followup.get("content", reply_text)

            # Clean reply if it's empty
            if not reply_text.strip() and tool_calls:
                reply_text = "All done! I took care of that for you!"
            elif not reply_text.strip():
                reply_text = "I'm right here listening!"

            # 5. Save assistant reply and broadcast to client
            self.add_history(MessageRole.ASSISTANT, reply_text)
            await ws_manager.send_chat_to(self.websocket, "assistant", reply_text)

            # 6. State: GENERATING (during TTS synthesis)
            await self.set_state(AssistantState.GENERATING, "Synthesizing voice reply...")

            audio_res = None
            try:
                audio_res = await tts.synthesize_to_base64(reply_text)
            except Exception as tts_err:
                logger.error(f"TTS synthesis error: {tts_err}")

            # 7. State: SPEAKING (only active when audio is transmitted to browser)
            if audio_res:
                await self.set_state(AssistantState.SPEAKING, "Cheeku is speaking...")
                await ws_manager.send_audio_to(
                    self.websocket,
                    audio_res["data"],
                    mime_type=audio_res.get("mime", "audio/mp3")
                )
            else:
                logger.warning("Neural TTS synthesis produced no audio. Broadcasting fallback signal.")
                await self.set_state(AssistantState.SPEAKING, "Cheeku is speaking...")
                await ws_manager.send_audio_failed_to(self.websocket, reply_text)

            # Watchdog timeout: primary READY transition is triggered by browser onended event
            word_count = len(reply_text.split())
            speech_duration = max(6.0, min(30.0, (word_count / 2.0) + 6.0))
            if self._timeout_task and not self._timeout_task.done():
                self._timeout_task.cancel()
            self._timeout_task = asyncio.create_task(self._auto_ready_timeout(speech_duration))

        except asyncio.CancelledError:
            logger.info(f"[{self.session_id}] Pipeline processing turn was cancelled.")
            raise
        except Exception as e:
            logger.error(f"[{self.session_id}] Error in orchestrator loop: {e}", exc_info=True)
            await self.set_state(AssistantState.ERROR, str(e))
            await ws_manager.send_chat_to(self.websocket, "assistant", "Oh dear, I had a little hiccup! But I'm still here for you!")
            await asyncio.sleep(1.0)
            await self.set_state(AssistantState.READY, "Cheeku is ready!", force=True)
        finally:
            self.is_processing = False

    async def _auto_ready_timeout(self, delay: float):
        """Auto-resets state to READY after estimated speech duration if client didn't send READY."""
        try:
            await asyncio.sleep(delay)
            if self.state == AssistantState.SPEAKING:
                await self.set_state(AssistantState.READY, "Cheeku is ready!")
        except asyncio.CancelledError:
            pass

    async def handle_audio_stream(self, audio_bytes: bytes):
        """Processes recorded audio buffer from frontend or microphone."""
        if self.is_processing or (self._current_task and not self._current_task.done()):
            await self.interrupt("Barge-in on audio stream")

        await self.set_state(AssistantState.TRANSCRIBING, "Transcribing speech with Whisper...")
        text = await stt.transcribe_bytes_async(audio_bytes)
        if text:
            logger.info(f"[{self.session_id}] Transcribed audio: '{text}'")
            await self.handle_user_input(text)
        else:
            logger.info(f"[{self.session_id}] No audible speech detected in audio stream.")
            await self.set_state(AssistantState.READY, "Cheeku is ready!")


class SessionRegistry:
    """
    Manages active assistant orchestrator sessions with cryptographic tokens.
    Prevents unauthorized session reuse, session hijacking, and cross-client disconnect interference.
    """
    def __init__(self):
        self._sessions: Dict[str, AssistantOrchestrator] = {}
        self._session_tokens: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    def create_session(self, websocket: Optional[WebSocket] = None) -> Tuple[str, str, AssistantOrchestrator]:
        """Generates a new secure session with an unguessable secret token."""
        session_id = f"sess_{secrets.token_hex(12)}"
        session_token = secrets.token_hex(32)
        orch = AssistantOrchestrator(session_id=session_id, websocket=websocket)
        orch.state = AssistantState.READY
        self._sessions[session_id] = orch
        self._session_tokens[session_id] = session_token
        return session_id, session_token, orch

    def get_or_resume(
        self,
        requested_session_id: Optional[str],
        provided_session_token: Optional[str],
        websocket: Optional[WebSocket] = None
    ) -> Tuple[str, str, AssistantOrchestrator, bool]:
        """
        Resumes an existing session only when the valid session_token is provided.
        Rejects client attempts to specify/claim a session_id without the secret token,
        and generates a new isolated session instead.
        """
        if requested_session_id and provided_session_token:
            if requested_session_id in self._sessions:
                stored_token = self._session_tokens.get(requested_session_id, "")
                if stored_token and secrets.compare_digest(stored_token, provided_session_token):
                    orch = self._sessions[requested_session_id]
                    orch.websocket = websocket
                    return requested_session_id, stored_token, orch, True
                else:
                    logger.warning(f"Rejected attempt to attach to session '{requested_session_id}': invalid session token.")

        session_id, session_token, orch = self.create_session(websocket=websocket)
        return session_id, session_token, orch, False

    def get_or_create(self, session_id: str, websocket: Optional[WebSocket] = None) -> AssistantOrchestrator:
        """Compatibility helper for direct test instantiation."""
        if session_id not in self._sessions:
            orch = AssistantOrchestrator(session_id=session_id, websocket=websocket)
            orch.state = AssistantState.READY
            self._sessions[session_id] = orch
            self._session_tokens[session_id] = secrets.token_hex(32)
        else:
            if websocket is not None:
                self._sessions[session_id].websocket = websocket
        return self._sessions[session_id]

    async def on_disconnect(self, session_id: str, websocket: WebSocket):
        """
        Disconnect cleanup: unbinds the websocket and interrupts in-flight processing
        only if the disconnecting socket is the active WebSocket for this session.
        Preserves session context for legitimate token-authenticated reconnection.
        """
        orch = self._sessions.get(session_id)
        if orch and orch.websocket == websocket:
            orch.websocket = None
            await orch.interrupt("Client disconnected")
            logger.info(f"Session '{session_id}' unlinked from disconnected websocket.")

    async def remove_session(self, session_id: str):
        self._session_tokens.pop(session_id, None)
        orch = self._sessions.pop(session_id, None)
        if orch:
            await orch.shutdown()

    async def shutdown_all(self):
        tasks = [orch.shutdown() for orch in list(self._sessions.values())]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._sessions.clear()
        self._session_tokens.clear()

    def count(self) -> int:
        return len(self._sessions)


session_registry = SessionRegistry()
orchestrator = AssistantOrchestrator()
