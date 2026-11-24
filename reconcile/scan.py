"""Scan: a file that is published must hold no private identifier.

    python -m reconcile.scan PATH [PATH ...]      files, directories, Inspect .eval logs
    python -m reconcile.scan --history            every commit of this repository: author, committer,
                                                  message and every line that a commit adds or removes

An Inspect `.eval` file is a zip archive with zstd-compressed members; each member is unpacked and
checked. The scan fails on any of:

- a home-directory path (/Users/..., /home/...), with one exemption: the placeholder path in
  `PLACEHOLDER_HOME` below, which names no account of a machine;
- a tailnet address (100.64/10) or a tailnet name (`*.ts.net`);
- a private network address (10/8, 172.16/12, 192.168/16), with one exemption: the subnet in
  `TOOL_DEFAULT_NETWORKS` below, which a container tool creates with the same numbers on every machine;
- an mDNS host name (a name that ends in `.local`; a cgroup v2 file name with that ending is a file,
  not a host);
- a string of the local denylist file: host names, user names, service hosts, one per line, matched
  as whole words. The file is outside the repository, so the repository does not hold the strings;
- the contents of the local key files;
- key material, found by gitleaks with the repository's .gitleaks.toml.

A missing denylist file is itself a finding: without it the scan cannot check names.

Exit 0: clean. Exit 1: at least one finding, listed with file, member and count. Nothing is changed:
a finding is reported, never redacted.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

# zstd (method 93) support for zipfile; without it a member cannot be unpacked, which is a finding
with contextlib.suppress(ImportError):
    import zipfile_zstd  # noqa: F401

REPO = Path(__file__).resolve().parent.parent
OCTET = rb"(?:25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])"
PATTERNS: dict[str, re.Pattern[bytes]] = {
    "home-directory path": re.compile(rb"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "tailnet address": re.compile(
        rb"\b100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.[0-9]{1,3}\.[0-9]{1,3}\b"
    ),
    "tailnet name": re.compile(rb"\b[A-Za-z0-9-]+\.ts\.net\b"),
    "private network address": re.compile(
        rb"(?<![0-9.])(?:10\."
        + OCTET
        + rb"|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\."
        + OCTET
        + rb"\."
        + OCTET
        + rb"(?![0-9]|\.[0-9])"
    ),
    "local host name": re.compile(rb"\b[A-Za-z0-9-]+\.local\b"),
}
# Private subnets that are a tool's default, not a network of the machine's owner. An address here is
# the same on every machine that runs the tool, so it identifies nobody.
#   192.168.5.0/24: the user-mode network of Lima, which Colima uses for its VM. Colima's template
#   configuration gives 192.168.5.2 as the default gateway address. A container's /etc/resolv.conf
#   can name an address of this subnet, and a task can print that file.
# Only this subnet is exempt. Every other private address stays a finding.
TOOL_DEFAULT_NETWORKS = re.compile(rb"192\.168\.5\." + OCTET)
# A home path that is a placeholder, not a directory of a person. `/home/user/` is the example path of
# manuals and of model text: in run B a model wrote it in its reasoning, as an example of a directory
# that a person can give to a script. The container of the runs has no such directory.
# Only this one path is exempt, and only under /home. Every other home path stays a finding. The
# account names of the author's machines are in the denylist, which is checked apart from this rule,
# so a real path under one of those names is still a finding.
# Added 24 November 2026, after the scan of the run B log, by the author's decision.
PLACEHOLDER_HOME = re.compile(rb"/home/user/")
# cgroup v2 files whose names end in `.local` (the `events` and `stat` files of a controller), only
# as the last component of a path under /sys/fs/cgroup/
CGROUP_FILE = re.compile(
    rb"/sys/fs/cgroup(?:/[A-Za-z0-9_.-]+)*/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.(?:events|stat)\.local\b"
)
DENYLIST_FILE = Path(
    os.environ.get("TR_DENYLIST", "~/.config/transcript-reconciliation/denylist.txt")
).expanduser()
KEY_FILES = [
    Path(p).expanduser()
    for p in os.environ.get(
        "TR_KEY_FILES",
        "~/.config/llama/research.key:~/.config/huggingface/transcript-reconciliation.token",
    ).split(":")
    if p
]
SUFFIXES_SKIPPED = {".png", ".jpg", ".gif", ".pdf", ".gguf", ".pyc"}
DIRECTORIES_SKIPPED = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}


def denylist() -> list[bytes] | None:
    """The strings of the denylist file, or None when the file is missing."""
    try:
        lines = DENYLIST_FILE.read_text().splitlines()
    except OSError:
        return None
    return [line.strip().encode() for line in lines if line.strip() and not line.startswith("#")]


def key_contents() -> list[bytes]:
    values = []
    for path in KEY_FILES:
        with contextlib.suppress(OSError):
            if value := path.read_bytes().strip():
                values.append(value)
    return values


def check_bytes(data: bytes, *, denied: list[bytes], keys: list[bytes]) -> Counter[tuple[str, str]]:
    """Pure check of one file's bytes: a count for each (rule, detail). No secret appears in a detail."""
    found: Counter[tuple[str, str]] = Counter()
    cgroup_ends = {m.end() for m in CGROUP_FILE.finditer(data)}
    for rule, pattern in PATTERNS.items():
        for match in pattern.finditer(data):
            if rule == "local host name" and match.end() in cgroup_ends:
                continue
            if rule == "home-directory path" and PLACEHOLDER_HOME.fullmatch(match.group()):
                continue
            if rule == "private network address" and TOOL_DEFAULT_NETWORKS.fullmatch(match.group()):
                continue
            found[(rule, match.group().decode(errors="replace"))] += 1
    for word in denied:
        hits = len(re.findall(rb"(?<![A-Za-z0-9_])" + re.escape(word) + rb"(?![A-Za-z0-9_])", data))
        if hits:
            found[("denylist", word.decode(errors="replace"))] += hits
    for key in keys:
        if key in data:
            found[("contents of a local key file", "(not shown)")] += data.count(key)
    return found


def gitleaks(directory: Path) -> list[str]:
    """Rule ids and file names that gitleaks flags in the directory, with the repository's config."""
    try:
        result = subprocess.run(
            ["gitleaks", "dir", str(directory), "--config", str(REPO / ".gitleaks.toml"), "--no-banner",
             "--redact", "--exit-code", "1", "--report-format", "json", "--report-path", "-"],
            capture_output=True, text=True, check=False,
        )  # fmt: skip
    except OSError as e:
        return [f"gitleaks did not run: {e}"]
    if result.returncode == 0:
        return []
    if result.returncode != 1:
        return [f"gitleaks did not run: {result.stderr.strip()[-200:]}"]
    try:
        leaks = json.loads(result.stdout or "[]")
    except ValueError:
        return ["gitleaks reported leaks but its report could not be read"]
    return [f"{leak.get('RuleID')} in {Path(leak.get('File', '?')).name}" for leak in leaks]


def members(path: Path) -> list[tuple[str, bytes | Exception]]:
    """(member name, bytes) for each part of a file: the members of an .eval archive, or the file itself."""
    if path.suffix != ".eval":
        return [("", path.read_bytes())]
    parts: list[tuple[str, bytes | Exception]] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        return [("", e)]
    for member in archive.infolist():
        try:
            parts.append((member.filename, archive.read(member)))
        except (NotImplementedError, zipfile.BadZipFile, RuntimeError) as e:
            parts.append((member.filename, e))
    return parts


def files_of(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found += sorted(
                p
                for p in path.rglob("*")
                if p.is_file() and not DIRECTORIES_SKIPPED & set(p.parts) and p.suffix not in SUFFIXES_SKIPPED
            )
        else:
            found.append(path)
    return found


def history() -> bytes:
    """Every commit of the repository as text: names, addresses, dates, message, and the full patch."""
    result = subprocess.run(
        ["git", "log", "--all", "--format=fuller", "--patch", "--no-color", "--no-ext-diff"],
        cwd=REPO, capture_output=True, check=True,
    )  # fmt: skip
    return result.stdout


def scan(paths: list[Path], *, with_history: bool = False) -> list[tuple[str, str, str, str, int]]:
    """(file, member, rule, detail, count) for every finding in the given files."""
    findings: list[tuple[str, str, str, str, int]] = []
    denied = denylist()
    if denied is None:
        findings.append((str(DENYLIST_FILE.name), "", "denylist file missing", "names are not checked", 1))
    keys = key_contents()
    with tempfile.TemporaryDirectory(prefix="scan-") as tmp:
        if with_history:
            data = history()
            for (rule, detail), count in check_bytes(data, denied=denied or [], keys=keys).items():
                findings.append(("(git history)", "", rule, detail, count))
            (Path(tmp) / "git-history.txt").write_bytes(data)
        for index, path in enumerate(files_of(paths)):
            for member, data in members(path):
                if isinstance(data, Exception):
                    findings.append((str(path), member, "could not be unpacked", str(data), 1))
                    continue
                for (rule, detail), count in check_bytes(data, denied=denied or [], keys=keys).items():
                    findings.append((str(path), member, rule, detail, count))
                name = f"{index}__{path.name}__{member.replace('/', '__')}"
                (Path(tmp) / name).write_bytes(data)
        for leak, count in Counter(gitleaks(Path(tmp))).items():
            findings.append(("", "", "gitleaks", leak, count))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--history", action="store_true", help="also scan every commit of this repository")
    args = parser.parse_args()
    if not args.paths and not args.history:
        parser.error("give at least one path, or --history")
    findings = scan(args.paths, with_history=args.history)
    count = len(files_of(args.paths))
    if not findings:
        commits = subprocess.run(
            ["git", "rev-list", "--all", "--count"], cwd=REPO, capture_output=True, text=True, check=False
        ).stdout.strip()
        print(f"scan: {count} file(s) clean" + (f", {commits} commit(s) clean" if args.history else ""))
        return 0
    for file, member, rule, detail, n in findings:
        where = f"{file}{' :: ' + member if member else ''}"
        print(f"scan: {rule}: {detail} ({n}x) in {where}", file=sys.stderr)
    print(f"scan: FAILED, {len(findings)} finding(s) in {count} file(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
