"""Layer 1: the tool calls of a transcript against the sandbox events that Inspect records.

    python -m reconcile.layer1 RUN_ID | PATH.eval        tables in Markdown: one per sample, then counts

A monitor reads tool calls and tool results. Inspect also writes one sandbox event for each action it
sends to the container. This command pairs the two records and compares them.

Pairing. Inspect opens a span of type `tool` for each tool call and writes the call's sandbox events
inside that span. An event belongs to the call whose span holds it. Events in other spans are listed
by the span they sit in: `init`, the setup solver, the scorer.

Each comparison of text gets one class:

    same                      the same text
    same after known change   the texts agree after named changes (below); each change is counted
    different                 the texts do not agree after the known changes
    cannot compare            one side holds no text for this comparison

Known changes, each with the reason it exists. The pre-registration of the first run named `wrapper`,
`cut` and the order of the streams. `envelope` and `layout` were added after the events of that run
were read (results/run-a-layer1.md):

    wrapper           the tool wraps the command: `bash --login -c <command>`
    envelope          a tool that runs through Inspect's in-container helper sends its arguments, and
                      gets its result, as one JSON-RPC message
    cut               Inspect cuts the text of an event to 10,000 characters and then to 20 lines
    stream separator  an event holds the error stream, an empty line, then the output stream; the bash
                      tool's result holds the error stream, a line end, then the output stream
    layout            `run_tests` puts labels and indentation around the output of the tests

What this cannot show: an event is Inspect's own record of what it sent to the container, written by
the process that also writes the tool result. Agreement here does not show what happened in the
container. An event shows one command line, not what that command started.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from reconcile.readout import log_path

SAME, KNOWN, DIFFERENT, NO_TEXT = "same", "same after known change", "different", "cannot compare"
CUT_MARKER = re.compile(r"\n\nOutput truncated \((\d+) additional lines\)\Z")
CHARACTER_CUT = 10_000
HELPER = "inspect-sandbox-tools exec"


@dataclass
class Relation:
    """The result of one comparison: a class, and the known changes that were needed."""

    kind: str
    changes: tuple[str, ...] = ()
    note: str = ""

    def __str__(self) -> str:
        text = self.kind + (f" ({', '.join(self.changes)})" if self.changes else "")
        return text + (f": {self.note}" if self.note else "")


# ---------------------------------------------------------------- pure comparisons


def split_cut(text: str) -> tuple[str, bool]:
    """An event's text without the line that reports a cut, and whether the text was cut."""
    match = CUT_MARKER.search(text)
    if match:
        return text[: match.start()], True
    return text, len(text) >= CHARACTER_CUT


def without_one_line_end(text: str, other: str, *, prefix: bool) -> bool:
    """True when deleting one line end from an empty line of `text` gives `other` (or a prefix of it)."""
    start = 0
    while (index := text.find("\n\n", start)) != -1:
        candidate = text[:index] + text[index + 1 :]
        if other.startswith(candidate) if prefix else candidate == other:
            return True
        start = index + 1
    return False


def relate_output(result: str, event_output: str | None) -> Relation:
    """The bash tool's result against the output of its event."""
    if event_output is None:
        return Relation(NO_TEXT, note="the event holds no output")
    if event_output == result:
        return Relation(SAME)
    body, cut = split_cut(event_output)
    if not cut:
        if without_one_line_end(body, result, prefix=False):
            return Relation(KNOWN, ("stream separator",))
        return Relation(DIFFERENT)
    body = body[: CHARACTER_CUT - 20] if len(body) >= CHARACTER_CUT else body
    if result.startswith(body):
        return Relation(KNOWN, ("cut",))
    if without_one_line_end(body, result, prefix=True):
        return Relation(KNOWN, ("cut", "stream separator"))
    return Relation(DIFFERENT)


def lines_of(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def relate_layout(result: str, event_output: str | None) -> Relation:
    """A result that holds the event's output inside labels and indentation (`run_tests`)."""
    if event_output is None:
        return Relation(NO_TEXT, note="the event holds no output")
    if event_output == result:
        return Relation(SAME)
    body, cut = split_cut(event_output)
    wanted, have = lines_of(body), lines_of(result)
    for start in range(len(have) - len(wanted) + 1):
        if have[start : start + len(wanted)] == wanted:
            return Relation(KNOWN, ("layout", "cut") if cut else ("layout",))
    return Relation(DIFFERENT)


def relate_bash_command(command: str, event_cmd: str | None) -> Relation:
    if event_cmd is None:
        return Relation(NO_TEXT, note="the event holds no command")
    if event_cmd == command:
        return Relation(SAME)
    if event_cmd == shlex.join(["bash", "--login", "-c", command]):
        return Relation(KNOWN, ("wrapper",))
    return Relation(DIFFERENT)


def relate_envelope(value: Any, event_text: str | None, key: str) -> Relation:
    """A value against the `params` or `result` member of the JSON-RPC message in an event's text."""
    if not event_text:
        return Relation(NO_TEXT, note="the event holds no text")
    try:
        message = json.loads(event_text)
    except ValueError:
        body, cut = split_cut(event_text)
        if not cut:
            return Relation(DIFFERENT, note="the event's text is not one JSON message")
        # A cut message cannot be parsed. Compare the text of the value with what is left of it.
        if key == "params":
            match = re.search(r'"params": \{(.*)', body, re.S)
            expected = json.dumps(value)[1:-1]
        else:
            match = re.search(r'"result": (.*)', body, re.S)
            expected = json.dumps(value)
        left = match.group(1)[:-20] if match else ""
        if left and expected.startswith(left[: len(expected)]):
            return Relation(KNOWN, ("envelope", "cut"))
        return Relation(DIFFERENT, note="the text before the cut does not agree")
    member = message.get(key)
    if key == "params" and isinstance(member, dict):
        member = {k: v for k, v in member.items() if not k.startswith("_")}  # `_run_as`: the user
    return Relation(KNOWN, ("envelope",)) if member == value else Relation(DIFFERENT)


# ---------------------------------------------------------------- pairing


@dataclass
class Call:
    step: int
    function: str
    arguments: dict[str, Any]
    result: str
    message: str | None
    error: bool
    events: list[Any] = field(default_factory=list)

    @property
    def main(self) -> Any | None:
        """The event that carries the call itself: the last one. Earlier ones prepare the tool."""
        return self.events[-1] if self.events else None


def text_of(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str)


def pair(sample: Any) -> tuple[list[Call], dict[str, list[Any]], int]:
    """(tool calls with their events, events outside tool calls by place, events that could not be placed)."""
    spans: dict[str, Any] = {}
    in_span: dict[str, list[Any]] = {}
    for event in sample.events:
        if event.event == "span_begin":
            spans[event.id] = event
        elif event.event == "sandbox":
            in_span.setdefault(event.span_id, []).append(event)

    def place(span_id: str | None) -> str:
        seen = set()
        while span_id in spans and span_id not in seen:
            seen.add(span_id)
            span = spans[span_id]
            if span.type == "tool":
                return "tool"
            if span.type in ("init", "scorer", "scorers"):
                return {"scorers": "scorer"}.get(span.type, span.type)
            if span.type == "solver" and not span.name.endswith("control_solver"):
                return f"setup ({span.name.split('/')[-1]})"
            span_id = span.parent_id
        return "not placed"

    messages = {m.tool_call_id: m for m in sample.messages if m.role == "tool"}
    calls: list[Call] = []
    step, last_tool_span, used = 0, None, set()
    for event in sample.events:
        if event.event == "model":
            step += 1
        elif event.event == "span_begin" and event.type == "tool":
            last_tool_span = event
        elif event.event == "tool":
            message = messages.get(event.id)
            call = Call(
                step=step,
                function=event.function,
                arguments=event.arguments or {},
                result=text_of(event.result),
                message=message.text if message else None,
                error=event.error is not None,
            )
            # Inspect writes the span's begin event just before the tool event of the same call.
            span = last_tool_span
            if span is not None and span.name == event.function and span.id not in used:
                call.events = in_span.get(span.id, [])
                used.add(span.id)
            calls.append(call)

    outside: dict[str, list[Any]] = {}
    not_placed = 0
    for span_id, events in in_span.items():
        if span_id in used:
            continue
        where = place(span_id)
        if where in ("tool", "not placed"):
            not_placed += len(events)
            where = "not placed"
        outside.setdefault(where, []).extend(events)
    return calls, outside, not_placed


def overlaps(calls: list[Call]) -> int:
    """Pairs of calls of one step whose events overlap in time."""
    count = 0
    by_step: dict[int, list[Call]] = {}
    for call in calls:
        if call.events:
            by_step.setdefault(call.step, []).append(call)
    for group in by_step.values():
        spans = [(c.events[0].timestamp, c.events[-1].completed or c.events[-1].timestamp) for c in group]
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                if spans[i][0] < spans[j][1] and spans[j][0] < spans[i][1]:
                    count += 1
    return count


# ---------------------------------------------------------------- one call


@dataclass
class Row:
    call: Call
    command: Relation
    output: Relation
    model_view: Relation
    exit_code: int | None


def compare(call: Call) -> Row:
    main = call.main
    model_view = (
        Relation(NO_TEXT, note="no tool message")
        if call.message is None
        else Relation(SAME)
        if call.message == call.result
        else Relation(DIFFERENT, note="the message is not the tool's result")
    )
    if main is None:
        nothing = Relation(NO_TEXT, note="no event")
        return Row(call, nothing, nothing, model_view, None)
    if call.function == "bash":
        command = relate_bash_command(call.arguments.get("command", ""), main.cmd)
        output = relate_output(call.result, main.output)
    elif main.cmd and main.cmd.endswith(HELPER):
        command = relate_envelope(call.arguments, main.input, "params")
        output = relate_envelope(call.result, main.output, "result")
    elif not call.arguments:
        command = Relation(NO_TEXT, note="the call holds no command")
        output = relate_layout(call.result, main.output)
    else:
        command = Relation(DIFFERENT, note="no rule for this tool")
        output = relate_output(call.result, main.output)
    return Row(call, command, output, model_view, main.result)


# ---------------------------------------------------------------- report


def short(text: str, width: int = 48) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= width else text[: width - 1] + "…"


def describe(call: Call) -> str:
    if call.function == "bash":
        return short(call.arguments.get("command", ""))
    if call.function == "text_editor":
        return short(f"{call.arguments.get('command')} {call.arguments.get('path')}")
    return ""


def report(log: Any) -> str:
    out: list[str] = []
    total: Counter[str] = Counter()
    by_tool: dict[str, Counter[str]] = {}
    places: Counter[str] = Counter()
    for sample in log.samples:
        calls, outside, not_placed = pair(sample)
        rows = [compare(call) for call in calls]
        out += [
            f"## Sample {sample.id}",
            "",
            "| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            call = row.call
            code = "" if row.exit_code is None else str(row.exit_code)
            out.append(
                f"| {call.step} | `{call.function}` | {describe(call)} | {len(call.events)} | {code} "
                f"| {row.command} | {row.output} | {row.model_view} |"
            )
            tool = by_tool.setdefault(call.function, Counter())
            tool["calls"] += 1
            tool["events"] += len(call.events)
            tool["calls with no event"] += not call.events
            tool["calls with more than one event"] += len(call.events) > 1
            if call.events:
                total[f"command: {row.command}"] += 1
                total[f"output: {row.output}"] += 1
                total["exit code not 0"] += bool(row.exit_code)
                total["exit code not 0 and no error in the tool result"] += (
                    bool(row.exit_code) and not call.error
                )
            total[f"model's view: {row.model_view}"] += 1
        out += [
            "",
            "Events outside tool calls: "
            + (", ".join(f"{k} {len(v)}" for k, v in outside.items()) or "none"),
        ]
        out += [f"Pairs of calls of one step with events that overlap in time: {overlaps(calls)}", ""]
        for where, events in outside.items():
            places[where] += len(events)
        places["in tool calls"] += sum(len(c.events) for c in calls)
        total["events not placed"] += not_placed
        total["pairs of calls that overlap in time"] += overlaps(calls)

    out += [
        "## Counts, all samples",
        "",
        "| Tool | Calls | Events | Calls with no event | Calls with more than one event |",
        "|---|---|---|---|---|",
    ]
    for tool, c in sorted(by_tool.items()):
        out.append(
            f"| `{tool}` | {c['calls']} | {c['events']} | {c['calls with no event']} "
            f"| {c['calls with more than one event']} |"
        )
    out += ["", "| Where the events sit | Events |", "|---|---|"]
    out += [f"| {where} | {n} |" for where, n in sorted(places.items())]
    out += ["", "| Comparison | Count |", "|---|---|"]
    out += [f"| {name} | {n} |" for name, n in sorted(total.items())]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", help="a run id (logs/<run-id>/) or the path of an .eval file")
    args = parser.parse_args()
    from inspect_ai.log import read_eval_log  # imported here so that the comparisons need no Inspect

    print(report(read_eval_log(str(log_path(args.run)), resolve_attachments=True)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
