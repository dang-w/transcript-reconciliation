"""Render the transcript of each sample of a run as plain text, in one of three forms.

    python -m reconcile.render RUN_ID --out DIR [--form visible] [--events]

Forms:

    full      the task, then for each step: reasoning, visible text, tool calls, tool results
    visible   the same without reasoning
    calls     tool calls and tool results only, then the visible text of the last message
    actions   tool calls and tool results only, with no text of the agent at all

With --events, each tool result gets one more line, taken from the sandbox events of that call and
not from the transcript: the exit code, and a mark if the call ran at the same time as another call
of the same step. The file name is then SAMPLE_ID.FORM.events.txt.

A step is one assistant message. The text is taken from the messages of the sample, in order, with
nothing cut. An argument of a tool call that holds more than one line (the content of a file) is
printed on real lines, each with the mark `    | `. One file per sample:
DIR/RUN_ID/SAMPLE_ID.FORM.txt. The output is derived from the log
and is not committed; it can hold whatever the log holds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalSample, read_eval_log

from reconcile.layer1 import overlap_pairs, pair

REPO = Path(__file__).resolve().parent.parent
FORMS = ("full", "visible", "calls", "actions")


def log_path(run: str) -> Path:
    path = Path(run)
    if path.suffix == ".eval":
        return path
    logs = sorted((REPO / "logs" / run).glob("*.eval"))
    if not logs:
        raise SystemExit(f"render: no .eval file in logs/{run}/")
    return logs[-1]


def parts(message: Any) -> tuple[str, str]:
    """The reasoning and the visible text of one message."""
    content = message.content
    if isinstance(content, str):
        return "", content
    reasoning = "\n".join(c.reasoning for c in content if c.type == "reasoning")
    text = "\n".join(c.text for c in content if c.type == "text")
    return reasoning, text


def call_text(call: Any) -> str:
    arguments = call.arguments or {}
    if call.function == "bash" and set(arguments) == {"command"}:
        return str(arguments["command"])
    if not arguments:
        return "(no arguments)"
    out: list[str] = []
    for key, value in arguments.items():
        if isinstance(value, str) and "\n" in value:
            out.append(f"{key}:\n" + "\n".join("    | " + line for line in value.split("\n")))
        elif isinstance(value, str):
            out.append(f"{key}: {value}")
        else:
            out.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(out)


def event_lines(sample: EvalSample) -> dict[str, str]:
    """For each tool call id: the line that --events adds to its result."""
    calls, _, _ = pair(sample)
    together = {id(c) for both in overlap_pairs(calls) for c in both}
    lines: dict[str, str] = {}
    for call in calls:
        if call.call_id is None:
            continue
        main = call.main
        code = "no sandbox event for this call" if main is None else f"exit code {main.result}"
        mark = "; ran at the same time as another call of this step" if id(call) in together else ""
        lines[call.call_id] = f"[SANDBOX EVENTS] {code}{mark}"
    return lines


def render(sample: EvalSample, form: str, events: bool = False) -> str:
    if form not in FORMS:
        raise ValueError(form)
    added = event_lines(sample) if events else {}
    out: list[str] = []
    task = [parts(m)[1] for m in sample.messages if m.role == "user"]
    out.append("=== TASK ===\n" + "\n".join(task).strip())
    assistants = [m for m in sample.messages if m.role == "assistant"]
    step = 0
    for message in sample.messages:
        if message.role == "assistant":
            step += 1
            reasoning, text = parts(message)
            out.append(f"\n=== STEP {step} ===")
            if form == "full" and reasoning.strip():
                out.append("[AGENT REASONING]\n" + reasoning.strip())
            last = message is assistants[-1]
            if text.strip() and form != "actions" and (form != "calls" or last):
                out.append("[AGENT]\n" + text.strip())
            for call in message.tool_calls or []:
                out.append(f"[TOOL CALL {call.function}]\n" + call_text(call))
        elif message.role == "tool":
            body = parts(message)[1]
            if message.error:
                body = (body + "\n" if body.strip() else "") + f"(tool error: {message.error.message})"
            out.append(f"[TOOL RESULT {message.function}]\n" + body.rstrip())
            if events:
                out.append(added.get(message.tool_call_id, "[SANDBOX EVENTS] no sandbox event for this call"))
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", help="a run id, or the path of an .eval file")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--form", choices=FORMS, action="append")
    parser.add_argument("--events", action="store_true")
    args = parser.parse_args(argv)
    path = log_path(args.run)
    name = args.run if Path(args.run).suffix != ".eval" else path.parent.name
    log = read_eval_log(str(path), resolve_attachments=True)
    target = args.out / name
    target.mkdir(parents=True, exist_ok=True)
    for sample in log.samples or []:
        for form in args.form or FORMS:
            text = render(sample, form, args.events)
            kind = f"{form}.events" if args.events else form
            (target / f"{sample.id}.{kind}.txt").write_text(text)
            print(f"{name} {sample.id} {kind} {len(text)} characters", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
