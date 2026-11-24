"""Replay: run the sandbox events of one sample again in a new container, with no model.

    python -m reconcile.replay RUN_ID SAMPLE_ID --to-event N [--out FILE]

The events of the sample are read from the run's log, in order, from event 0 to event N. Each `exec`
event is run again with `docker compose exec -T` in a new container of `control/bash/compose.yaml`;
each `write_file` event is written with `cat`. After each event the state of the container is read
with `docker inspect`. After the last event one more command (`true`) is sent, and its error text is
recorded.

Written for one question (24 November 2026, before the replay was run): in run B, sample 574105,
did the model's command of step 10 (`kill -TERM -1`) stop the container?

- Confirmed: the container is `running` after every event before the last, and is not `running`
  after the last; the next command gets an error.
- Not confirmed: the container is still `running` after the last event.
- Not this command: the container stopped at an earlier event.

What a replay is not: Inspect did not send the commands (the call is the same in form: the command of
the event, the user and the environment of its options, no terminal); the times between commands
differ; the dates in the outputs differ; the log holds the first 20 lines of a written file, so a longer
file is written incomplete (the last item was found in the first replay). No model runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import read_eval_log

REPO = Path(__file__).resolve().parent.parent
COMPOSE = REPO / "control" / "bash" / "compose.yaml"
SERVICE = "default"


def compose(
    project: str, *args: str, stdin: str | None = None, timeout: float = 600
) -> tuple[int | None, str]:
    """Exit code (None on a timeout) and stderr + stdout of one `docker compose` command."""
    argv = ["docker", "compose", "-p", project, "-f", str(COMPOSE), *args]
    try:
        r = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, "(timeout)"
    return r.returncode, r.stderr + r.stdout


def state(project: str) -> dict[str, Any]:
    """The state of the service's container: status, exit code, OOM flag, times."""
    code, ident = compose(project, "ps", "-a", "-q", SERVICE)
    ident = ident.strip().splitlines()[-1] if ident.strip() else ""
    if code != 0 or not ident:
        return {"status": "no container"}
    r = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State}}", ident],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        s = json.loads(r.stdout)
    except ValueError:
        return {"status": "inspect failed"}
    return {k.lower(): s.get(k) for k in ("Status", "ExitCode", "OOMKilled", "StartedAt", "FinishedAt")}


def replay(run_id: str, sample_id: str, to_event: int) -> dict[str, Any]:
    paths = sorted((REPO / "logs" / run_id).glob("*.eval"))
    if len(paths) != 1:
        raise SystemExit(f"replay: expected one log in logs/{run_id}, found {len(paths)}")
    log = read_eval_log(paths[0], resolve_attachments=True)
    sample = next(s for s in log.samples or [] if str(s.id) == sample_id)
    events = [e for e in sample.events if e.event == "sandbox"][: to_event + 1]
    project = f"replay-{sample_id}-{dt.datetime.now(dt.UTC):%H%M%S}"
    record: dict[str, Any] = {
        "run_id": run_id,
        "sample_id": sample_id,
        "to_event": to_event,
        "started": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "events": [],
    }
    code, text = compose(project, "up", "-d", "--build", "--wait", timeout=1800)
    record["up"] = {"exit_code": code, "state": state(project)}
    if code != 0:
        record["up"]["output_tail"] = text[-2000:]
        return record
    try:
        for index, event in enumerate(events):
            options = event.options or {}
            flags = ["-T"]
            if options.get("user"):
                flags += ["--user", str(options["user"])]
            for key, value in (options.get("env") or {}).items():
                flags += ["--env", f"{key}={value}"]
            timeout = float(options.get("timeout") or 120)
            if event.action == "exec":
                argv = shlex.split(event.cmd or "")
                code, text = compose(
                    project, "exec", *flags, SERVICE, *argv, stdin=event.input, timeout=timeout + 30
                )
            elif event.action == "write_file":
                target = shlex.quote(event.file or "")
                code, text = compose(
                    project, "exec", "-T", SERVICE, "sh", "-c", f"cat > {target}", stdin=event.input or ""
                )
            else:
                code, text = None, f"(action {event.action} is not replayed)"
            record["events"].append(
                {
                    "index": index,
                    "action": event.action,
                    "command": event.cmd if event.action == "exec" else event.file,
                    "logged_exit_code": event.result,
                    "replay_exit_code": code,
                    "logged_output": event.output,
                    "replay_output": text,
                    "state_after": state(project),
                }
            )
        code, text = compose(project, "exec", "-T", SERVICE, "true", timeout=60)
        record["command_after"] = {
            "command": "true",
            "exit_code": code,
            "output": text,
            "state": state(project),
        }
    finally:
        compose(project, "down", "--rmi", "local", "--volumes", timeout=300)
    record["ended"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument("sample_id")
    parser.add_argument("--to-event", type=int, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    record = replay(args.run_id, args.sample_id, args.to_event)
    text = json.dumps(record, indent=1) + "\n"
    if str(Path.home()) in text:
        print("replay: the record holds the home directory; not written", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text)
    for e in record["events"]:
        print(
            f"{e['index']:>2} {e['action']:<10} logged {e['logged_exit_code']!s:>4}"
            f"  replay {e['replay_exit_code']!s:>4}  container {e['state_after'].get('status')}"
        )
    if after := record.get("command_after"):
        print(
            f"then `true`: exit {after['exit_code']}, container {after['state'].get('status')}:"
            f" {after['output'].strip()[:200]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
