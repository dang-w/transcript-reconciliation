"""Two more outputs of the stage 2 runs. No model is called.

    python -m monitor.extra suspicion RUN_ID [RUN_ID ...]
    python -m monitor.extra special RUN_ID [RUN_ID ...]

suspicion: one table for each run, the 20 samples in the order of the score, highest first. Samples
with the same score share one rank and are shown as a tie; no order is made inside a tie.

special: the answer of the monitor for each special-case transcript and condition, in full, for
the readers who score it against `claims/special-cases.md`. Nothing is scored here.
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from inspect_ai.log import read_eval_log

from reconcile.render import log_path


def score_of(sample: Any) -> Any:
    return next(iter(sample.scores.values()))


def suspicion(run: str) -> str:
    log = read_eval_log(str(log_path(run)))
    rows = []
    for sample in log.samples or []:
        score = score_of(sample)
        rows.append(
            (
                score.value,
                sample.metadata["run"],
                sample.metadata["sample"],
                (score.metadata or {}).get("step"),
            )
        )
    scored = sorted((r for r in rows if isinstance(r[0], int | float)), key=lambda r: (-r[0], r[1], r[2]))
    silent = sorted(r for r in rows if not isinstance(r[0], int | float))
    sizes = Counter(r[0] for r in scored)
    out = [f"## {run}: {log.eval.model}, {len(rows)} samples, status {log.status}", ""]
    out += [
        "| Rank | Score | Run | Sample | Step that the monitor names | Tie |",
        "|---|---|---|---|---|---|",
    ]
    rank = 0
    for i, (value, run_letter, sample_id, step) in enumerate(scored):
        if i == 0 or value != scored[i - 1][0]:
            rank = i + 1
        tie = f"tie of {sizes[value]}" if sizes[value] > 1 else ""
        out.append(f"| {rank} | {int(value)} | {run_letter} | {sample_id} | {step or ''} | {tie} |")
    for _, run_letter, sample_id, _ in silent:
        out.append(f"| none | did not answer | {run_letter} | {sample_id} | | |")
    top = [r for r in scored if r[0] == scored[0][0]] if scored else []
    names = ", ".join(f"{r[1]} {r[2]}" for r in top)
    out += [
        "",
        f"- Highest score: {int(top[0][0]) if top else 'none'}, held by {len(top)} sample(s): {names}.",
    ]
    out.append(
        "- Scores: " + ", ".join(f"{int(v)} for {n}" for v, n in sorted(sizes.items(), reverse=True)) + "."
    )
    return "\n".join(out) + "\n"


def special(run: str) -> str:
    log = read_eval_log(str(log_path(run)))
    out = [f"## {run}: {log.eval.model}, status {log.status}", ""]
    for sample in sorted(log.samples or [], key=lambda s: (s.metadata["run"], s.metadata["condition"])):
        meta = sample.metadata
        condition = "T+E" if meta["condition"] == "TE" else meta["condition"]
        out += [f"### Run {meta['run']}, sample {meta['sample']}, condition {condition}", ""]
        out += ["```text", (sample.output.completion or "(no answer)").strip(), "```", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] not in ("suspicion", "special"):
        print(__doc__, file=sys.stderr)
        return 2
    make = suspicion if args[0] == "suspicion" else special
    print("\n".join(make(run) for run in args[1:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
