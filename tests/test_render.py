"""The three forms of a rendered transcript, on a hand-made sample. No log file, no model."""

from types import SimpleNamespace as NS

from reconcile.render import render


def content(text: str, reasoning: str = "") -> list[NS]:
    out = [NS(type="reasoning", reasoning=reasoning)] if reasoning else []
    return [*out, NS(type="text", text=text)]


def sample() -> NS:
    call = NS(function="bash", arguments={"command": "ls /tmp"})
    submit = NS(function="submit", arguments={})
    return NS(
        messages=[
            NS(role="system", content="system text", tool_calls=None),
            NS(role="user", content="the task", tool_calls=None),
            NS(role="assistant", content=content("I look.", "secret thought"), tool_calls=[call]),
            NS(role="tool", content="a.txt", function="bash", error=None),
            NS(role="assistant", content=content("All done."), tool_calls=[submit]),
            NS(role="tool", content="", function="submit", error=NS(message="refused")),
        ]
    )


def test_full_holds_reasoning_and_visible_does_not():
    assert "secret thought" in render(sample(), "full")
    assert "secret thought" not in render(sample(), "visible")
    assert "I look." in render(sample(), "visible")


def test_calls_keeps_only_the_last_visible_text():
    text = render(sample(), "calls")
    assert "I look." not in text
    assert "All done." in text
    assert "ls /tmp" in text and "a.txt" in text


def test_steps_task_and_tool_errors():
    text = render(sample(), "visible")
    assert text.startswith("=== TASK ===\nthe task")
    assert "system text" not in text
    assert "=== STEP 1 ===" in text and "=== STEP 2 ===" in text
    assert "(tool error: refused)" in text
    assert "[TOOL CALL submit]\n(no arguments)" in text
