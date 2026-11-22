"""Publish the logs of one run to the Hugging Face dataset, by hand, after the scan.

    python -m reconcile.publish RUN_ID              check only: nothing leaves the machine
    python -m reconcile.publish RUN_ID --upload     check, upload, download again, compare

Nothing calls this: not the run wrapper, not a hook, not a timer. A person starts it for one run.

The checks, in order. A failure stops everything and nothing is uploaded:

1. the run has a manifest, and the manifest is committed (a log is published only against a
   manifest that git already holds);
2. the logs in logs/<run-id>/ are the ones in the manifest, by name and sha256;
3. the scan (reconcile/scan.py) finds nothing in them. A finding is reported and never redacted.

With `--upload`, the logs go up in one dataset commit at `runs/<run-id>/<file>`. Each file is then
downloaded at that commit and its sha256 compared with the manifest. Only then does the manifest get
the dataset commit and the time of the check; commit the manifest afterwards.

The token is read from a file outside the repository and is never printed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from reconcile.run import REPO, manifest_text, sha256_file
from reconcile.scan import scan

DATASET = "dang-w/transcript-reconciliation-logs"
TOKEN_FILE = Path(
    os.environ.get("TR_HF_TOKEN_FILE", "~/.config/huggingface/transcript-reconciliation.token")
).expanduser()


class Refused(Exception):
    """A check failed: nothing is uploaded."""


def dataset_path(run_id: str, file: str) -> str:
    return f"runs/{run_id}/{file}"


def plan(run_id: str, manifest: dict[str, Any], log_dir: Path) -> list[tuple[Path, str, str]]:
    """(local file, dataset path, sha256) for each log, after the files match the manifest."""
    recorded = {record["file"]: record["sha256"] for record in manifest.get("logs", [])}
    files = sorted(log_dir.glob("*.eval"))
    if not files:
        raise Refused(f"no log in {log_dir.name}/")
    if {f.name for f in files} != set(recorded):
        raise Refused("the logs on disk are not the ones in the manifest")
    batch = []
    for path in files:
        digest = sha256_file(path)
        if digest != recorded[path.name]:
            raise Refused(f"{path.name} differs from its sha256 in the manifest")
        batch.append((path, dataset_path(run_id, path.name), digest))
    return batch


def manifest_is_committed(path: Path) -> bool:
    """True when git holds this exact manifest: tracked, and no change against HEAD."""
    relative = path.relative_to(REPO).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative], cwd=REPO, capture_output=True, check=False
    )
    changed = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=REPO, check=False)
    return tracked.returncode == 0 and changed.returncode == 0


def upload_and_verify(run_id: str, batch: list[tuple[Path, str, str]]) -> dict[str, Any]:
    """One dataset commit, then each file downloaded at that commit and compared. Returns the record."""
    from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

    token = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else ""
    if not token:
        raise Refused("the token file is missing or empty")
    api = HfApi(token=token)
    commit = api.create_commit(
        repo_id=DATASET,
        repo_type="dataset",
        operations=[
            CommitOperationAdd(path_in_repo=target, path_or_fileobj=str(path)) for path, target, _ in batch
        ],
        commit_message=f"Logs of run {run_id}",
    )
    print(f"publish: uploaded {len(batch)} file(s) in dataset commit {commit.oid}")
    with tempfile.TemporaryDirectory(prefix="publish-") as tmp:
        for _, target, digest in batch:
            local = hf_hub_download(
                DATASET, target, repo_type="dataset", revision=commit.oid, cache_dir=tmp, token=token
            )
            if sha256_file(Path(local)) != digest:
                raise Refused(f"VERIFY FAILED for {target} at dataset commit {commit.oid}")
            print(f"publish: verified {target} ({digest[:12]})")
    return {
        "dataset": DATASET,
        "dataset_commit": commit.oid,
        "verified": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument(
        "--upload", action="store_true", help="upload after the checks; without it, check only"
    )
    args = parser.parse_args()
    manifest_path = REPO / "manifests" / f"{args.run_id}.json"
    log_dir = REPO / "logs" / args.run_id
    try:
        if not manifest_path.exists():
            raise Refused("the run has no manifest; a run without a manifest is never published")
        manifest = json.loads(manifest_path.read_text())
        if all(record.get("published") for record in manifest.get("logs", [])) and manifest.get("logs"):
            print("publish: already published; nothing to do")
            return 0
        if not manifest_is_committed(manifest_path):
            raise Refused("commit the manifest first: a log is published only against a committed manifest")
        batch = plan(args.run_id, manifest, log_dir)
        findings = scan([path for path, _, _ in batch])
        for file, member, rule, detail, n in findings:
            print(f"publish: scan: {rule}: {detail} ({n}x) in {Path(file).name} :: {member}", file=sys.stderr)
        if findings:
            raise Refused(f"the scan has {len(findings)} finding(s); report them, do not redact")
        for _, target, digest in batch:
            print(f"publish: checked {target} ({digest[:12]}): matches the manifest, scan clean")
        if not args.upload:
            print(f"publish: check only; nothing was uploaded. Give --upload to publish to {DATASET}")
            return 0
        published = upload_and_verify(args.run_id, batch)
        for record in manifest["logs"]:
            record["published"] = published | {
                "url": f"https://huggingface.co/datasets/{DATASET}/blob/{published['dataset_commit']}/"
                + dataset_path(args.run_id, record["file"])
            }
        manifest_path.write_text(manifest_text(manifest))
    except Refused as refusal:
        print(f"publish: REFUSED: {refusal}", file=sys.stderr)
        return 1
    print("publish: done; the manifest is updated, commit it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
