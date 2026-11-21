"""Run one Inspect command as a recorded run: the log in logs/<run-id>/, a manifest in manifests/.

    python -m reconcile.run --run-id ID [--allow-dirty] [--note TEXT] -- eval control/bash/task.py@... [flags]

What it adds to a plain `inspect` call:

- it refuses to start on a dirty working tree, unless `--allow-dirty` is given; the manifest records
  the commit and the dirty flag either way;
- the logs go to `logs/<run-id>/`; a run id is used once;
- `docker ps` is sampled during the run, because Inspect removes the image it built when the run ends;
- `manifests/<run-id>.json` is written also when the run fails or is interrupted: the command, the
  commit, the package versions, the container images, and the name, size and sha256 of each log.

No queue, no retry, no upload. The model server's key and address come from the environment
(scripts/run sets them). The manifest holds no path of the machine and no secret.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import signal
import subprocess
import sys
import threading
from importlib import metadata
from pathlib import Path
from typing import Any

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


def watch_images(images: dict[str, dict[str, Any]], stop: threading.Event) -> None:
    while not stop.wait(POLL_SECONDS):
        for name in (output("docker", "ps", "--format", "{{.Image}}") or "").split():
            if name not in images:
                images[name] = image_record(name)


def log_records(log_dir: Path) -> list[dict[str, Any]]:
    return [
        {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(log_dir.glob("*.eval"))
    ]


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
    stop = threading.Event()
    watcher = threading.Thread(target=watch_images, args=(images, stop), daemon=True)
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
        logs=log_records(REPO / log_dir),
    )
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"reconcile.run: {status}; manifest {manifest_path.relative_to(REPO)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
