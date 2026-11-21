"""The run wrapper's refusals and its manifest fields. No Inspect run, no Docker."""

import subprocess
import sys
from pathlib import Path

from reconcile import run

REPO = Path(__file__).resolve().parent.parent


def cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "reconcile.run", *argv], cwd=REPO, capture_output=True, text=True, check=False
    )


def test_a_log_dir_argument_is_refused():
    result = cli("--run-id", "x", "--", "eval", "t.py", "--log-dir", "elsewhere")
    assert result.returncode == 2 and "--log-dir" in result.stderr


def test_a_bad_run_id_is_refused():
    result = cli("--run-id", "../x", "--", "eval", "t.py")
    assert result.returncode == 2 and "run id" in result.stderr


def test_manifest_fields():
    manifest = run.build_manifest("x", status="completed", repo={"commit": "abc", "dirty": False})
    assert manifest["schema"] == run.SCHEMA and manifest["run_id"] == "x"
    assert manifest["repo"] == {"commit": "abc", "dirty": False}
    assert manifest["versions"]["control_arena"] == "19.0.0"
    assert set(manifest["versions"]) == {"python", "inspect_ai", "control_arena", "uv_lock_sha256"}


def test_git_state_lists_dirty_files(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "new.txt").write_text("x")
    monkeypatch.setattr(run, "REPO", tmp_path)
    state = run.git_state()
    assert state["dirty"] is True and state["dirty_files"] == ["new.txt"] and state["commit"] is None
