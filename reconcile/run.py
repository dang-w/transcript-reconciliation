"""Run one Inspect command as a recorded run: the log in logs/<run-id>/, a manifest in manifests/.

    python -m reconcile.run --run-id ID [--allow-dirty] [--note TEXT] -- eval control/bash/task.py@... [flags]

What it adds to a plain `inspect` call:

- it refuses to start on a dirty working tree, unless `--allow-dirty` is given; the manifest records
  the commit and the dirty flag either way;
- the logs go to `logs/<run-id>/`; a run id is used once;
- `docker ps` is sampled during the run, because Inspect removes the image it built when the run ends;
- `manifests/<run-id>.json` is written also when the run fails or is interrupted: the command, the
  commit, the package versions, the container images, the name, size and sha256 of each log with
  the settings in its header, and what served the model (reconcile/inference.py): the llama.cpp
  build, the model files with their sha256, and the server's settings, read while a model is loaded.

No queue, no retry, no upload. The model server's key and address come from the environment
(scripts/run sets them). The manifest holds no path of the machine and no secret: it is not written
if it contains the home directory or the server's key.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
from importlib import metadata
from pathlib import Path
from typing import Any

from reconcile import inference

REPO = Path(__file__).resolve().parent.parent
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
POLL_SECONDS = 3
SCHEMA = 1


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output(*argv: str) -> str | None:
    """Output of a command run in the repository, or None if it is missing or fails."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30, cwd=REPO, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def git_state() -> dict[str, Any]:
    status = output("git", "status", "--porcelain")
    return {
        "commit": (output("git", "rev-parse", "HEAD") or "").strip() or None,
        "dirty": bool(status.strip()) if status is not None else None,
        "dirty_files": sorted(line[3:] for line in (status or "").splitlines()),
    }


def versions() -> dict[str, Any]:
    def package(name: str) -> str | None:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return None

    lock = REPO / "uv.lock"
    return {
        "python": platform.python_version(),
        "inspect_ai": package("inspect-ai"),
        "control_arena": package("control-arena"),
        "uv_lock_sha256": sha256_file(lock) if lock.exists() else None,
    }


def image_record(name: str) -> dict[str, Any]:
    """Identity of one container image. Needs the Docker daemon, and the image must still exist."""
    out = output("docker", "image", "inspect", name, "--format", "{{json .}}")
    if out is None:
        return {"name": name, "id": None, "note": "docker image inspect failed"}
    info = json.loads(out)
    return {
        "name": name,
        "id": info.get("Id"),
        "repo_digests": info.get("RepoDigests") or [],
        "architecture": info.get("Architecture"),
    }


def watch(
    images: dict[str, dict[str, Any]], servers: dict[str, dict[str, Any]], stop: threading.Event
) -> None:
    """During the run: the images of the running containers, and the settings of each loaded model."""
    base_url, key = os.environ.get("LLAMA_CPP_BASE_URL"), os.environ.get("LLAMA_CPP_API_KEY")
    while not stop.wait(POLL_SECONDS):
        for name in (output("docker", "ps", "--format", "{{.Image}}") or "").split():
            if name not in images:
                images[name] = image_record(name)
        if base_url:
            for model_id in inference.loaded_models(base_url, key):
                if model_id not in servers and (
                    settings := inference.server_settings(base_url, key, model_id)
                ):
                    servers[model_id] = settings


def log_records(log_dir: Path) -> list[dict[str, Any]]:
    """One record per .eval file: identity, outcome and the request-side settings of its header."""
    from inspect_ai.log import read_eval_log  # imported here so that the refusals need no Inspect

    records = []
    for path in sorted(log_dir.glob("*.eval")):
        record: dict[str, Any] = {
            "file": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        try:
            log = read_eval_log(str(path), header_only=True)
        except Exception as e:  # a log cut off by a kill is still a log of this run
            records.append(record | {"status": "unreadable", "error": type(e).__name__, "model": None})
            continue
        roles = log.eval.model_roles or {}
        records.append(
            record
            | {
                "status": log.status,
                "task": log.eval.task,
                "model": log.eval.model,
                # request-side sampling settings of each role (temperature, seed, max_tokens, ...)
                "model_roles": {
                    role: {"model": config.model, "config": config.config.model_dump(exclude_none=True)}
                    for role, config in roles.items()
                },
                "samples": log.eval.dataset.samples,
                "completed_samples": log.results.completed_samples if log.results else None,
                "generate_config": log.eval.model_generate_config.model_dump(exclude_none=True),
                "eval_config": log.eval.config.model_dump(exclude_none=True),
                "sandbox": log.eval.sandbox.model_dump(exclude_none=True) if log.eval.sandbox else None,
                "inspect_run_id": log.eval.run_id,
                "started": log.stats.started_at or None,
                "completed": log.stats.completed_at or None,
            }
        )
    return records


def manifest_text(manifest: dict[str, Any]) -> str:
    """The manifest as JSON. Refused when it holds the home directory or the model server's key."""
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if str(Path.home()) in text:
        raise ValueError("the manifest contains the home directory path; it must hold no path of the machine")
    if (key := os.environ.get("LLAMA_CPP_API_KEY")) and key in text:
        raise ValueError("the manifest contains the model server's key")
    return text


def build_manifest(run_id: str, **fields: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "run_id": run_id, **fields, "versions": versions()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--note", help="free text for the manifest")
    parser.add_argument(
        "--allow-dirty", action="store_true", help="run on a dirty tree; the manifest says so"
    )
    parser.add_argument("inspect_args", nargs=argparse.REMAINDER, help="-- followed by the inspect arguments")
    args = parser.parse_args()
    inspect_args = args.inspect_args[1:] if args.inspect_args[:1] == ["--"] else args.inspect_args

    if not RUN_ID.fullmatch(args.run_id):
        parser.error("the run id may hold letters, digits, '.', '_' and '-'")
    if not inspect_args:
        parser.error("give the inspect arguments after --")
    if "--log-dir" in inspect_args:
        parser.error("do not give --log-dir: the logs of a run go to logs/<run-id>/")
    manifest_path = REPO / "manifests" / f"{args.run_id}.json"
    if manifest_path.exists():
        parser.error(f"run id {args.run_id} already has a manifest; a run id is used once")
    repo = git_state()  # before the run: the run itself adds files
    if repo["dirty"] is not False and not args.allow_dirty:
        print(
            "reconcile.run: the working tree is dirty (or is not a git repository); commit first, "
            "or give --allow-dirty and the manifest records it:\n  " + "\n  ".join(repo["dirty_files"]),
            file=sys.stderr,
        )
        return 2

    log_dir = Path("logs") / args.run_id
    (REPO / log_dir).mkdir(parents=True, exist_ok=True)
    command = ["inspect", *inspect_args, "--log-dir", log_dir.as_posix()]
    images: dict[str, dict[str, Any]] = {}
    servers: dict[str, dict[str, Any]] = {}
    stop = threading.Event()
    watcher = threading.Thread(target=watch, args=(images, servers, stop), daemon=True)
    interrupted = False
    started = utc_now()
    child = subprocess.Popen([str(Path(sys.executable).parent / "inspect"), *command[1:]], cwd=REPO)

    def forward(signum: int, frame: object) -> None:
        nonlocal interrupted
        interrupted = True
        child.send_signal(signal.SIGINT)  # Inspect stops gracefully on SIGINT and closes its log

    signal.signal(signal.SIGINT, forward)
    signal.signal(signal.SIGTERM, forward)
    watcher.start()
    try:
        exit_code = child.wait()
    finally:
        stop.set()
        watcher.join(timeout=POLL_SECONDS + 30)

    status = "interrupted" if interrupted else "completed" if exit_code == 0 else "failed"
    logs = log_records(REPO / log_dir)
    manifest = build_manifest(
        args.run_id,
        started=started,
        ended=utc_now(),
        status=status,
        exit_code=exit_code,
        command=command,
        note=args.note,
        repo=repo,
        allow_dirty=args.allow_dirty,
        container_images=[images[name] for name in sorted(images)],
        logs=logs,
        **inference.record(logs, servers),
    )
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(manifest_text(manifest))
    print(f"reconcile.run: {status}; manifest {manifest_path.relative_to(REPO)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
