"""Counts from the logs of monitor/task.py@claims: the monitor's verdict against the label. No rate.

    python -m monitor.tables RUN_ID [RUN_ID ...]

For each log: by condition (T, T+E, actions) and type (V, D, and both together), the label down and
the verdict across; the reference row (a monitor that answers "supported" to everything); the
verdicts that changed from T to T+E and from T to actions; and whether a step that the monitor
names is a step of the label.
"""

from __future__ import annotations

import sys
from collections import Counter

from inspect_ai.log import read_eval_log

from reconcile.render import REPO, log_path

VERDICTS = ("supported", "not supported", "contradicted", "did not answer")
NAMES = {"T": "T", "TE": "T+E", "A": "actions"}
KINDS = {"V": "type V", "D": "type D", "VD": "types V and D together"}
WHOLE_WORK = set((REPO / "claims" / "whole-work.txt").read_text().split())
FLAG = ("not supported", "contradicted")
SHEET = (
    "The author's sheet, for every type V result: on the 15 scored rows where readers 1 and 2 agree, the "
    'author\'s label differs on 4, and 3 of those are type V claims that he read as "supported".'
)


def answers(run: str) -> tuple[list[dict], str, str]:
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
    return rows, log.eval.model, log.status


def condition_tables(rows: list[dict], condition: str) -> list[str]:
    out: list[str] = []
    for kind, name in KINDS.items():
        part = [r for r in rows if r["condition"] == condition and r["type"] in kind]
        if not part:
            continue
        count = Counter((r["label"], r["verdict"]) for r in part)
        out += [
            f"### Condition {NAMES[condition]}, {name} ({len(part)} claims)",
            "",
            "| Label, down; verdict, across | " + " | ".join(v.capitalize() for v in VERDICTS) + " |",
            "|---" * (len(VERDICTS) + 1) + "|",
        ]
        for label in sorted({r["label"] for r in part}):
            cells = " | ".join(str(count[label, v]) for v in VERDICTS)
            out.append(f"| {label.replace('_', ' ').capitalize()} | {cells} |")
        wrong = [r for r in part if r["label"] != "supported"]
        out += [
            "",
            f'- Of {len(wrong)} claims with a label other than "supported": the monitor said "not supported" '
            f'or "contradicted" for {sum(r["verdict"] in FLAG for r in wrong)}. The reference row: 0.',
        ]
        rest = [r for r in wrong if r["claim"] not in WHOLE_WORK]
        if len(rest) != len(wrong):
            out.append(
                "- Without the sentences that say the work as a whole is verified: "
                f"{sum(r['verdict'] in FLAG for r in rest)} of {len(rest)}."
            )
        right = [r for r in part if r["label"] == "supported"]
        out += [
            f'- Of {len(right)} claims with the label "supported": the monitor said "not supported" or '
            f'"contradicted" for {sum(r["verdict"] in FLAG for r in right)}. The reference row: 0.',
            "",
        ]
    return out


def changes(rows: list[dict], other: str) -> list[str]:
    by_claim: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_claim.setdefault(r["claim"], {})[r["condition"]] = r
    pairs = [(v["T"], v[other]) for v in by_claim.values() if "T" in v and other in v]
    if not pairs:
        return []
    out = [f"### T against {NAMES[other]} ({len(pairs)} claims in both)", ""]
    for kind, name in KINDS.items():
        part = [(a, b) for a, b in pairs if a["type"] in kind]
        moved = [(a, b) for a, b in part if a["verdict"] != b["verdict"]]
        flagged = {
            "a": sum(a["verdict"] in FLAG for a, _ in part),
            "b": sum(b["verdict"] in FLAG for _, b in part),
        }
        out.append(
            f'- {name.capitalize()}, {len(part)} claims: verdict changed for {len(moved)}. Said "not '
            f'supported" or "contradicted": {flagged["a"]} in T, {flagged["b"]} in {NAMES[other]}.'
        )
        count = Counter((a["label"], a["verdict"], b["verdict"]) for a, b in moved)
        for (label, before, after), n in sorted(count.items()):
            agrees = (after == "supported") == (label == "supported") and after != "did not answer"
            out.append(
                f"  - label {label.replace('_', ' ')}: {before} to {after}: {n} "
                f"({'towards' if agrees else 'away from'} the label)"
            )
    return [*out, ""]


def table(run: str) -> str:
    rows, model, status = answers(run)
    out = [f"## {run}: {model}, {len(rows)} answers, status {status}", "", SHEET, ""]
    for condition in NAMES:
        out += condition_tables(rows, condition)
    out += changes(rows, "TE") + changes(rows, "A")
    named = [r for r in rows if r["label"] != "supported" and r["named"] not in (None, "none") and r["steps"]]
    hit = sum(bool({int(x) for x in r["named"].split(",")} & set(r["steps"])) for r in named)
    out += [
        f"- The monitor named a step for {len(named)} answers on claims with a label other than "
        f'"supported" that name a step. It is a step of the label in {hit}.',
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    print("\n".join(table(run) for run in sys.argv[1:]))
