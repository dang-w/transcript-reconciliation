"""Counts from the logs of monitor/task.py: the monitor's verdict against the label. No rate is written.

    python -m monitor.tables RUN_ID [RUN_ID ...]

For each log: by condition and type, the label down and the verdict across; the reference row (a
monitor that answers "supported" to everything); the verdicts that changed from T to T+E; and
whether the step that the monitor names is a step of the label.
"""

from __future__ import annotations

import sys
from collections import Counter

from inspect_ai.log import read_eval_log

from reconcile.render import log_path

VERDICTS = ("supported", "not supported", "contradicted", "did not answer")
NAMES = {"T": "T", "TE": "T+E"}


def table(run: str) -> str:
    log = read_eval_log(str(log_path(run)))
    rows = []
    for sample in log.samples or []:
        score = next(iter((sample.scores or {}).values()), None)
        rows.append(
            {
                **sample.metadata,
                "verdict": score.value if score else "did not answer",
                "named": (score.metadata or {}).get("step") if score else None,
            }
        )
    out = [f"## {run}: {log.eval.model}, {len(rows)} answers, status {log.status}", ""]
    for condition in ("T", "TE"):
        for kind in ("V", "D"):
            part = [r for r in rows if r["condition"] == condition and r["type"] == kind]
            if not part:
                continue
            count = Counter((r["label"], r["verdict"]) for r in part)
            out += [
                f"### Condition {NAMES[condition]}, type {kind} ({len(part)} claims)",
                "",
                "| Label, down; verdict, across | " + " | ".join(v.capitalize() for v in VERDICTS) + " |",
                "|---" * (len(VERDICTS) + 1) + "|",
            ]
            for label in sorted({r["label"] for r in part}):
                cells = " | ".join(str(count[label, v]) for v in VERDICTS)
                out.append(f"| {label.replace('_', ' ').capitalize()} | {cells} |")
            wrong = [r for r in part if r["label"] != "supported"]
            noticed = sum(r["verdict"] in ("not supported", "contradicted") for r in wrong)
            out += [
                "",
                f'- Of {len(wrong)} claims with a label other than "supported": the monitor said '
                f'"not supported" or "contradicted" for {noticed}. The reference row: 0.',
                "",
            ]
    by_claim: dict[str, dict[str, str]] = {}
    for r in rows:
        by_claim.setdefault(r["claim"], {})[r["condition"]] = r["verdict"]
    changed = Counter((v["T"], v["TE"]) for v in by_claim.values() if len(v) == 2 and v["T"] != v["TE"])
    both = sum(1 for v in by_claim.values() if len(v) == 2)
    out += [f"### T against T+E ({both} claims in both)", "", f"- Verdict changed: {sum(changed.values())}."]
    out += [f"  - {a} to {b}: {n}" for (a, b), n in sorted(changed.items())]
    named = [r for r in rows if r["label"] != "supported" and r["named"] not in (None, "none") and r["steps"]]
    hit = sum(bool({int(x) for x in r["named"].split(",")} & set(r["steps"])) for r in named)
    out += [
        "",
        f"- The monitor named a step for {len(named)} answers on claims with a label other than "
        f'"supported" that name a step. It is a step of the label in {hit}.',
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    print("\n".join(table(run) for run in sys.argv[1:]))
