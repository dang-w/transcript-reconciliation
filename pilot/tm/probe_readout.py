"""Readout of a tool-use capability probe (control/bash/task.py): what the agent did in the sandbox.

    python -m tm.probe_readout RUN_ID            one row per sample, then the four probe answers
    python -m tm.probe_readout RUN_ID --json

`tm.report` already counts tool calls, parse errors and times. This adds what the probe is for:
the sandbox events Inspect recorded (`exec`, `read_file`, `write_file`), the number of model calls,
and whether a sample stopped at a limit. No statistics: five samples are a probe, not a result.

The four answers (results/bash-probe-preregistration.md fixes how they are read):

1. tool calls that parsed, of all tool calls;
2. samples with a `submit` call that parsed, of all samples;
3. samples whose main task passed, of all samples;
4. samples with at least one sandbox tool call that parsed (so it ran), of all samples.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any

from inspect_ai.log import EvalSample, read_eval_log

from tm.manifest import REPO
from tm.report import sample_record

SUBMIT = "submit"
# The tools of the Bash setting that run in the sandbox. A name list, not "every call except submit":
# Inspect has tools of its own that do not touch the sandbox (`read_tool_output`, seen in an APPS log).
SANDBOX_TOOLS = frozenset({"bash", "python", "text_editor", "run_tests"})


def executed_calls(sample: EvalSample) -> list[str]:
    """The names of the tool calls that parsed, in order.

    A call that fails to parse never runs, so it is no evidence of sandbox use or of a submission.
    The failure shows in two places: on the call in the assistant message (`parse_error`) and on the
    tool event (an error of type `parsing`). Either one excludes the call.
    """
    unparsed = {e.id for e in sample.events if e.event == "tool" and e.error and e.error.type == "parsing"}
    return [
        call.function
        for m in sample.messages
        if m.role == "assistant"
        for call in (m.tool_calls or [])
        if not call.parse_error and call.id not in unparsed
    ]


def probe_record(sample: EvalSample) -> dict[str, Any]:
    record = sample_record(sample)
    executed = executed_calls(sample)
    sandbox = collections.Counter(e.action for e in sample.events if e.event == "sandbox")
    limit = getattr(sample, "limit", None)
    return {
        "id": record["id"],
        "error": record["error"],
        "main_task_success": record["main_task_success"],
        "model_calls": sum(1 for e in sample.events if e.event == "model"),
        "tool_calls": len(record["tool_calls"]),
        "tool_calls_by_name": dict(collections.Counter(record["tool_calls"])),
        "tool_calls_parsed": len(executed),
        "tool_call_parse_errors": record["tool_call_parse_errors"],
        "tool_call_other_errors": record["tool_call_other_errors"],
        "submitted": SUBMIT in executed,
        # All sandbox events of the sample: the setup and the scorer use the sandbox too, so this
        # count is context, not answer 4. Answer 4 uses the agent's calls to the sandbox tools that
        # parsed: such a call runs in the sandbox, also when it then fails there.
        "sandbox_events": dict(sandbox),
        "agent_sandbox_tool_calls": sum(1 for name in executed if name in SANDBOX_TOOLS),
        # `custom` is ControlArena's step limit (max_steps); `time`, `message` are Inspect's own.
        "stopped_at_limit": getattr(limit, "type", None),
        "total_seconds": record["total_seconds"],
    }


def answers(records: list[dict[str, Any]]) -> dict[str, str]:
    n = len(records)
    calls = sum(r["tool_calls"] for r in records)
    parsed = sum(r["tool_calls_parsed"] for r in records)
    limits = collections.Counter(r["stopped_at_limit"] for r in records if r["stopped_at_limit"] is not None)
    by_type = f" ({', '.join(f'{k}: {v}' for k, v in sorted(limits.items()))})" if limits else ""
    active = sum(r["agent_sandbox_tool_calls"] > 0 for r in records)
    return {
        "1 tool calls that parsed": f"{parsed} of {calls}",
        "2 samples that submitted": f"{sum(r['submitted'] for r in records)} of {n}",
        "3 main task passed": f"{sum(r['main_task_success'] == 'C' for r in records)} of {n}",
        "4 samples with agent sandbox activity": f"{active} of {n}",
        "samples stopped at a limit": f"{sum(limits.values())} of {n}{by_type}",
        "samples with an error": f"{sum(r['error'] is not None for r in records)} of {n}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths = sorted((REPO / "logs" / args.run_id).glob("*.eval"))
    if not paths:
        print(f"no .eval file in logs/{args.run_id}/", file=sys.stderr)
        return 1
    # The newest file: an `eval-retry` log holds every sample of its run.
    log = read_eval_log(str(paths[-1]))
    records = [probe_record(sample) for sample in log.samples or []]
    summary = answers(records)

    if args.json:
        print(json.dumps({"run_id": args.run_id, "samples": records, "answers": summary}, indent=2))
        return 0
    for r in records:
        print(
            f"{r['id']!s:>8}  main={r['main_task_success']!s:<4}  model_calls={r['model_calls']:<3} "
            f"tools={r['tool_calls_by_name']}  parsed={r['tool_calls_parsed']}  "
            f"sandbox={r['sandbox_events']}  limit={r['stopped_at_limit']}  {r['total_seconds']} s"
            + (f"  ERROR {r['error']}" if r["error"] else "")
        )
    print()
    for question, answer in summary.items():
        print(f"{question}: {answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
