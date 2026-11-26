"""The case set of runs B to D, from the two readers' labels and the author's decisions.

    python claims/case_set.py

Reads claims.jsonl, labels-reader1.jsonl, labels-reader2.jsonl and decisions.jsonl. Writes case-set.jsonl and
prints the counts. A claim is in the set if it is of runs B to D, is not in a special case, and
  - both readers gave the same type and label, and neither marked it "inferred" (source "agreed"), or
  - the author decided for one reader, and that reader did not mark it "inferred" (source "author").
"""

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str) -> dict[str, dict]:
    return {r["id"]: r for r in map(json.loads, (HERE / name).read_text().splitlines())}


def main() -> None:
    claims, r1, r2, decisions = (
        load("claims.jsonl"),
        load("labels-reader1.jsonl"),
        load("labels-reader2.jsonl"),
        load("decisions.jsonl"),
    )
    rows = []
    for cid, claim in claims.items():
        if claim["run"] == "A" or claim["excluded"]:
            continue
        a, b = r1[cid], r2[cid]
        if (a["type"], a["label"]) == (b["type"], b["label"]):
            chosen, source = (None if a["inferred"] or b["inferred"] else a), "agreed"
        else:
            reader = decisions.get(cid, {}).get("decision")
            chosen = {"reader1": a, "reader2": b}.get(reader)
            chosen, source = (None if chosen is None or chosen["inferred"] else chosen), "author"
        if chosen is not None:
            rows.append(
                {
                    "id": cid,
                    "run": claim["run"],
                    "sample": claim["sample"],
                    "step": claim["step"],
                    "source": claim["source"],
                    "text": claim["text"],
                    "type": chosen["type"],
                    "label": chosen["label"],
                    "steps": chosen["steps"],
                    "set": source,
                }
            )
    (HERE / "case-set.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    for source in ("agreed", "author"):
        count = Counter((r["type"], r["label"]) for r in rows if r["set"] == source)
        print(source, sum(count.values()), dict(sorted(count.items())))


if __name__ == "__main__":
    main()
