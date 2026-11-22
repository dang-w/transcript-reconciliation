"""Repeatability: the tool calls of two runs of the same samples, compared in order.

    python -m reconcile.repeat FIRST.eval SECOND.eval

For each sample: whether every tool call (tool name and arguments) is the same in the same order,
or the step (model call) of the first tool call that differs. Also whether the text and the
reasoning of the first model call are the same. A sample that is only in one log is skipped.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


def steps(sample: Any) -> list[list[tuple[str, Any]]]:
    """For each model call that the sample kept: its tool calls as (tool name, arguments)."""
    return [
        [(call.function, call.arguments) for call in (message.tool_calls or [])]
        for message in sample.messages
        if message.role == "assistant"
    ]


def first_difference(first: list[list[Any]], second: list[list[Any]]) -> int | None:
    """The 1-based step of the first difference in tool calls, or None when all are the same."""
    for index in range(max(len(first), len(second))):
        if index >= len(first) or index >= len(second) or first[index] != second[index]:
            return index + 1
    return None


def first_message(sample: Any) -> tuple[str, str]:
    for message in sample.messages:
        if message.role == "assistant":
            content = message.content if isinstance(message.content, list) else []
            reasoning = "".join(getattr(part, "reasoning", "") or "" for part in content)
            return message.text, reasoning
    return "", ""


def common_prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("first")
    parser.add_argument("second")
    args = parser.parse_args()
    from inspect_ai.log import read_eval_log

    logs = [read_eval_log(path, resolve_attachments=True) for path in (args.first, args.second)]
    second = {sample.id: sample for sample in logs[1].samples}
    print("| Sample | Tool calls | Steps, first and second | Text of step 1 | Reasoning of step 1 |")
    print("|---|---|---|---|---|")
    for a in logs[0].samples:
        if (b := second.get(a.id)) is None:
            continue
        sa, sb = steps(a), steps(b)
        step = first_difference(sa, sb)
        (ta, ra), (tb, rb) = first_message(a), first_message(b)
        reasoning = (
            "the same" if ra == rb else f"the same for {common_prefix(ra, rb)} of {len(ra)} characters"
        )
        print(
            f"| {a.id} | {'the same' if step is None else f'first difference at step {step}'} "
            f"| {len(sa)} and {len(sb)} | {'the same' if ta == tb else 'different'} | {reasoning} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
