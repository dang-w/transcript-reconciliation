"""The checks before an upload. No network: the upload itself is not called."""

import hashlib

import pytest

from reconcile import publish


def log(tmp_path, name: str, data: bytes):
    (tmp_path / name).write_bytes(data)
    return {"file": name, "sha256": hashlib.sha256(data).hexdigest()}


def test_plan_names_the_dataset_path_of_each_log(tmp_path):
    manifest = {"logs": [log(tmp_path, "a.eval", b"one")]}
    [(path, target, digest)] = publish.plan("run-x", manifest, tmp_path)
    assert path.name == "a.eval" and target == "runs/run-x/a.eval" and digest == manifest["logs"][0]["sha256"]


def test_a_changed_log_is_refused(tmp_path):
    manifest = {"logs": [log(tmp_path, "a.eval", b"one")]}
    (tmp_path / "a.eval").write_bytes(b"two")
    with pytest.raises(publish.Refused, match="differs"):
        publish.plan("run-x", manifest, tmp_path)


def test_a_log_that_the_manifest_does_not_name_is_refused(tmp_path):
    manifest = {"logs": [log(tmp_path, "a.eval", b"one")]}
    (tmp_path / "b.eval").write_bytes(b"extra")
    with pytest.raises(publish.Refused, match="not the ones"):
        publish.plan("run-x", manifest, tmp_path)


def test_no_log_is_refused(tmp_path):
    with pytest.raises(publish.Refused, match="no log"):
        publish.plan("run-x", {"logs": []}, tmp_path)


def test_a_run_without_a_manifest_is_refused():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "reconcile.publish", "no-such-run", "--upload"],
        cwd=publish.REPO, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.returncode == 1 and "no manifest" in result.stderr
