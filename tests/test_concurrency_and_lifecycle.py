import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.assistant import AssistantOrchestrator, session_registry
from backend.models.schemas import AssistantState


def test_session_overlapping_requests_barge_in():
    async def _test():
        orch = AssistantOrchestrator(session_id="barge_in_test")
        await orch.set_state(AssistantState.READY, "Ready for test", force=True)

        task_1_cancelled = False
        task_2_completed = False

        async def slow_turn_1():
            nonlocal task_1_cancelled
            try:
                orch.is_processing = True
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                task_1_cancelled = True
                raise
            finally:
                orch.is_processing = False

        async def fast_turn_2():
            nonlocal task_2_completed
            orch.is_processing = True
            await asyncio.sleep(0.05)
            task_2_completed = True
            orch.is_processing = False

        orch._current_task = asyncio.create_task(slow_turn_1())
        await asyncio.sleep(0.02)
        assert orch.is_processing is True

        # Now incoming second turn triggers barge-in
        await orch.handle_user_input("Second user turn")
        assert task_1_cancelled is True
        assert orch.is_processing is False

    asyncio.run(_test())


def test_disconnect_cancels_in_flight_tasks():
    async def _test():
        task_cancelled = False

        orch = session_registry.get_or_create("disconnect_test")

        async def long_task():
            nonlocal task_cancelled
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        orch._current_task = asyncio.create_task(long_task())
        await asyncio.sleep(0.02)
        assert not orch._current_task.done()

        # Simulate client disconnect
        await session_registry.remove_session("disconnect_test")
        assert task_cancelled is True
        assert "disconnect_test" not in session_registry._sessions

    asyncio.run(_test())


def test_shutdown_all_sessions_cleanly():
    async def _test():
        orch1 = session_registry.get_or_create("sess_shutdown_1")
        orch2 = session_registry.get_or_create("sess_shutdown_2")

        task1_cancelled = False
        task2_cancelled = False

        async def task_fn_1():
            nonlocal task1_cancelled
            try:
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                task1_cancelled = True
                raise

        async def task_fn_2():
            nonlocal task2_cancelled
            try:
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                task2_cancelled = True
                raise

        orch1._current_task = asyncio.create_task(task_fn_1())
        orch2._current_task = asyncio.create_task(task_fn_2())
        await asyncio.sleep(0.02)

        # Trigger bulk shutdown
        await session_registry.shutdown_all()

        assert task1_cancelled is True
        assert task2_cancelled is True
        assert len(session_registry._sessions) == 0

    asyncio.run(_test())
