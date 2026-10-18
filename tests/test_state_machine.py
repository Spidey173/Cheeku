import asyncio
import os
import sys

# Ensure repository root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.models.schemas import AssistantState
from backend.app.assistant import AssistantOrchestrator, ALLOWED_TRANSITIONS


async def run_state_machine_tests():
    print("==================================================")
    print("🧪 Running Cheeku AI: State Machine Unit Tests")
    print("==================================================")

    orchestrator = AssistantOrchestrator()

    # Test 1: Initial state
    assert orchestrator.state == AssistantState.BOOTING, f"Expected BOOTING, got {orchestrator.state}"
    print("✅ Test 1: Initial state is BOOTING.")

    # Test 2: Legal transition BOOTING -> READY
    ok = await orchestrator.set_state(AssistantState.READY, "System booted")
    assert ok is True, "Failed legal transition BOOTING -> READY"
    assert orchestrator.state == AssistantState.READY
    print("✅ Test 2: Transition BOOTING -> READY succeeded.")

    # Test 3: Illegal transition READY -> GENERATING (should be rejected)
    ok = await orchestrator.set_state(AssistantState.GENERATING, "Illegal jump")
    assert ok is False, "Illegal transition READY -> GENERATING was incorrectly accepted"
    assert orchestrator.state == AssistantState.READY, "State changed after illegal transition"
    print("✅ Test 3: Blocked illegal transition READY -> GENERATING.")

    # Test 4: Legal sequence: READY -> THINKING -> CALLING_TOOL -> GENERATING -> SPEAKING -> READY
    sequence = [
        (AssistantState.THINKING, "Consulting Groq"),
        (AssistantState.CALLING_TOOL, "Executing tool"),
        (AssistantState.GENERATING, "Generating response"),
        (AssistantState.SPEAKING, "Synthesizing audio"),
        (AssistantState.READY, "Finished speaking"),
    ]
    for target_state, detail in sequence:
        ok = await orchestrator.set_state(target_state, detail)
        assert ok is True, f"Failed legal transition to {target_state.value}"
        assert orchestrator.state == target_state
    print("✅ Test 4: Standard turn sequence completed successfully.")

    # Test 5: Voice barge-in transition: SPEAKING -> THINKING
    await orchestrator.set_state(AssistantState.SPEAKING, "Cheeku speaking")
    ok = await orchestrator.set_state(AssistantState.THINKING, "User barge-in speaking")
    assert ok is True, "Failed voice barge-in transition SPEAKING -> THINKING"
    assert orchestrator.state == AssistantState.THINKING
    print("✅ Test 5: Voice barge-in transition SPEAKING -> THINKING succeeded.")

    # Test 6: Voice barge-in transition: SPEAKING -> LISTENING
    await orchestrator.set_state(AssistantState.SPEAKING, "Cheeku speaking", force=True)
    ok = await orchestrator.set_state(AssistantState.LISTENING, "User tapped mic")
    assert ok is True, "Failed voice barge-in transition SPEAKING -> LISTENING"
    assert orchestrator.state == AssistantState.LISTENING
    print("✅ Test 6: Voice barge-in transition SPEAKING -> LISTENING succeeded.")

    # Test 7: Force transition allows recovery
    ok = await orchestrator.set_state(AssistantState.READY, "Forced recovery", force=True)
    assert ok is True, "Failed forced transition"
    assert orchestrator.state == AssistantState.READY
    print("✅ Test 7: Forced recovery to READY succeeded.")

    print("\n🎉 ALL STATE MACHINE TESTS PASSED!\n")


def test_state_machine():
    asyncio.run(run_state_machine_tests())


if __name__ == "__main__":
    asyncio.run(run_state_machine_tests())
