"""The comparisons of layer 1 and the pairing of events with tool calls. No log, no model."""

import datetime as dt
import json
import shlex
from types import SimpleNamespace as NS

from reconcile import layer1
from reconcile.layer1 import DIFFERENT, KNOWN, NO_TEXT, SAME


def test_output_that_is_the_same():
    assert layer1.relate_output("a\nb\n", "a\nb\n").kind == SAME


def test_output_with_the_stream_separator():
    # the event: error stream, empty line, output stream; the tool result: error stream, line end, output
    relation = layer1.relate_output("warn\nout\n", "warn\n\nout\n")
    assert (relation.kind, relation.changes) == (KNOWN, ("stream separator",))


def test_output_cut_to_twenty_lines():
    full = "".join(f"line {i}\n" for i in range(30))
    event = "\n".join(full.splitlines()[:20]) + "\n\nOutput truncated (10 additional lines)"
    relation = layer1.relate_output(full, event)
    assert (relation.kind, relation.changes) == (KNOWN, ("cut",))
    changed = full.replace("line 3\n", "line three\n")
    assert layer1.relate_output(changed, event).kind == DIFFERENT


def test_output_cut_and_stream_separator():
    out = "".join(f"line {i}\n" for i in range(30))
    result = "warn\n" + out
    event = "\n".join(("warn\n\n" + out).splitlines()[:20]) + "\n\nOutput truncated (12 additional lines)"
    assert layer1.relate_output(result, event).changes == ("cut", "stream separator")


def test_output_that_differs_and_output_that_is_missing():
    assert layer1.relate_output("exit 0\n", "exit 1\n").kind == DIFFERENT
    assert layer1.relate_output("x", None).kind == NO_TEXT


def test_bash_command_wrapper():
    command = "cd / && echo 'it''s' | wc -l"
    wrapped = shlex.join(["bash", "--login", "-c", command])
    assert layer1.relate_bash_command(command, wrapped).changes == ("wrapper",)
    assert layer1.relate_bash_command(command, wrapped.replace("wc -l", "wc -c")).kind == DIFFERENT


def test_envelope_of_arguments_and_result():
    arguments = {"command": "create", "path": "/a.sh", "file_text": "echo hi\n"}
    sent = json.dumps(
        {"jsonrpc": "2.0", "method": "text_editor", "params": arguments | {"_run_as": {"uid": 0}}}
    )
    assert layer1.relate_envelope(arguments, sent, "params").changes == ("envelope",)
    assert layer1.relate_envelope(arguments | {"path": "/b.sh"}, sent, "params").kind == DIFFERENT
    received = json.dumps({"jsonrpc": "2.0", "result": "File created", "id": 1}) + "\n"
    assert layer1.relate_envelope("File created", received, "result").changes == ("envelope",)
    assert layer1.relate_envelope("x", "not json", "result").kind == DIFFERENT


def test_layout_of_run_tests():
    event = "collected 2 items\n\ntest_task.py ..\nAll tests succeeded for real!\n"
    pad = " " * 8
    result = f"STDOUT:\n{pad}collected 2 items\n\n{pad}test_task.py ..\n{pad}All tests succeeded for real!\n"
    assert layer1.relate_layout(result, event).changes == ("layout",)
    assert layer1.relate_layout(result.replace("..", ".F"), event).kind == DIFFERENT


T0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def at(seconds: float) -> dt.datetime:
    return T0 + dt.timedelta(seconds=seconds)


def sandbox(span: str, start: float, end: float, cmd: str = "x", output: str = "", result: int = 0):
    return NS(event="sandbox", span_id=span, timestamp=at(start), completed=at(end), cmd=cmd, input="",
              output=output, result=result, action="exec")  # fmt: skip


def span(id_: str, parent: str | None, type_: str, name: str):
    return NS(event="span_begin", id=id_, parent_id=parent, type=type_, name=name, span_id=id_)


def tool(id_: str, function: str, arguments: dict, result: str):
    return NS(event="tool", id=id_, function=function, arguments=arguments, result=result, error=None,
              span_id="solver")  # fmt: skip


def sample():
    one, two = (
        shlex.join(["bash", "--login", "-c", "echo 1"]),
        shlex.join(["bash", "--login", "-c", "echo 2"]),
    )
    events = [
        span("init", None, "init", "init"), sandbox("init", 0, 1),
        span("solvers", None, "solvers", "solvers"),
        span("setup", "solvers", "solver", "control_arena/add_test_file"), sandbox("setup", 1, 2),
        span("solver", "solvers", "solver", "control_arena/control_solver"),
        NS(event="model", span_id="solver"),
        # two calls of one step: Inspect writes each span's begin event just before its tool event
        span("t1", "solver", "tool", "bash"), tool("c1", "bash", {"command": "echo 1"}, "1\n"),
        span("t2", "solver", "tool", "bash"), tool("c2", "bash", {"command": "echo 2"}, "2\n"),
        sandbox("t2", 10, 12, two, "2\n"), sandbox("t1", 10.5, 11, one, "1\n", result=1),
        NS(event="model", span_id="solver"),
        span("t3", "solver", "tool", "submit"), tool("c3", "submit", {}, ""),
        span("scorers", None, "scorers", "scorers"), span("score", "scorers", "scorer", "bash_scorer"),
        sandbox("score", 20, 21),
    ]  # fmt: skip
    messages = [
        NS(role="tool", tool_call_id=i, text=t) for i, t in (("c1", "1\n"), ("c2", "2\n"), ("c3", ""))
    ]
    return NS(id=1, events=events, messages=messages)


def test_events_pair_with_the_call_whose_span_holds_them():
    calls, outside, not_placed = layer1.pair(sample())
    assert [(c.function, c.step, len(c.events)) for c in calls] == [
        ("bash", 1, 1),
        ("bash", 1, 1),
        ("submit", 2, 0),
    ]
    assert calls[0].main.cmd.endswith("'echo 1'") and calls[1].main.cmd.endswith("'echo 2'")
    assert {where: len(events) for where, events in outside.items()} == {
        "init": 1, "setup (add_test_file)": 1, "scorer": 1,
    }  # fmt: skip
    assert not_placed == 0 and layer1.overlaps(calls) == 1


def test_a_call_is_compared_with_its_own_event():
    rows = [layer1.compare(call) for call in layer1.pair(sample())[0]]
    assert [row.command.changes for row in rows[:2]] == [("wrapper",), ("wrapper",)]
    assert [row.output.kind for row in rows] == [SAME, SAME, NO_TEXT]
    assert [row.exit_code for row in rows] == [1, 0, None]


def test_report_counts():
    text = layer1.report(NS(samples=[sample()]))
    assert "| `bash` | 2 | 2 | 0 | 0 |" in text and "| `submit` | 1 | 0 | 1 | 0 |" in text
    assert "| exit code not 0 and no error in the tool result | 1 |" in text
