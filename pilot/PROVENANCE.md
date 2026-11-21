# Provenance of the pilot's files

## Source

The files come from a private git clone with no remote (the "pilot clone"). Two commits matter:

| Commit | Time (UTC) | What it holds |
|---|---|---|
| `a5d12ed` | 2026-11-17 17:47:45 | The task, the sandbox files, the readout script, the run script, the pre-registration without a prediction. The run used this commit, with a dirty tree. |
| `e1b7acd` | 2026-11-21 18:46:23 | Adds the prediction to the pre-registration, the manifest and the readout. Nothing else. |

The files here were taken from `e1b7acd` with `git show e1b7acd:<path>`, one by one, and not edited.

## Hashes (sha256 of each file as taken)

| File | sha256 |
|---|---|
| `control/bash/Dockerfile` | `c793b354c2fcc023dc71e09a4ee290ac9d8e76118a80ebb3dec7fde2416a08e1` |
| `control/bash/compose.yaml` | `e823095eed923356a31f69dc132b860429bcd9ac75b7b452b7b962e3db478f2b` |
| `control/bash/task.py` | `c77047b82127dc3dc2c2cf3df2adabe8995402f60d716083e8c7b1811b11364a` |
| `manifests/f1-gen-bash-honest-probe.json` | `958175fbb0adb4c57e0ec35373cf7420a20e761738202b203af62eb87c9991a3` |
| `results/bash-probe-2026-11-17.md` | `93698761c20f0a3135b6be7e1ecd103921b21cd5d455f1a12c99da0ae1d7334a` |
| `results/bash-probe-preregistration.md` | `42194487acaf6a5790072db629fe20854bf67568b34f9ddaaaa1aa319a11e2a9` |
| `scripts/run-probe` | `e55ea54a0ec4aefd76072a9df283109034be17c453ecc2d1f33938d03eef0024` |
| `tm/probe_readout.py` | `4e843acef3e6b6ddcce5be88831e08434e344234c1047c033d798c95ea0898c7` |

Check: `cd pilot && find . -type f ! -name README.md ! -name PROVENANCE.md | sort | xargs shasum -a 256`.

The log (not in this repository): sha256 `459d7206887bcc70c826041c5ad704ec4b490494f48ef93f447a2271f02acb01`,
checked again on 21 November against the file on disk and against the manifest.

## The code did not change between the two commits

`git diff --stat a5d12ed e1b7acd -- control/bash tm/probe_readout.py scripts/run-probe` prints nothing: the
task, the sandbox files, the readout script and the run script are the same in both commits.

`git diff --stat a5d12ed e1b7acd` lists three files: the manifest (new), the readout (new), and the
pre-registration (one line: the placeholder comment under "Prediction" replaced by the prediction).

## What was uncommitted when the run started

- **The prediction.** It was in the working tree's pre-registration file and not in a commit. File modification
  time 17:53:36 UTC; the run started at 17:56:09 UTC. The file was not modified again before it was committed on
  21 November (its time was read on 21 November before that commit and was still 17:53:36).
- **Nothing else that is known.** The modification times of the task, the sandbox files, the run script and the
  readout script are 17:46:58 to 17:47:32 UTC, before the commit `a5d12ed`.
- **The Dockerfile's header comment** was corrected before the commit: the corrected text is in `a5d12ed`. It was
  not a working-tree change at run time.

## What cannot now be established

- That the working tree at 17:56 held no other change. The manifest records only a dirty flag, not the list of
  dirty files. The file times above are consistent with "only the prediction"; they do not prove it.
- The text of the prediction at 17:56 by any means other than the file time.
- The base image's digest by name. `alpine:latest` was not pinned; the manifest lists the image ids that
  `docker ps` showed during the run.

## The Dockerfile against ControlArena 19.0.0

The earlier statement "an unchanged copy" was wrong. The body, from `FROM` to the end, is the same as
`control_arena/settings/bash/Dockerfile` in the 19.0.0 wheel from PyPI (`diff` of the two prints nothing). The
difference is a header of six comment lines added above `FROM`:

```
# Copied unchanged from ControlArena 19.0.0 (control_arena/settings/bash/Dockerfile, MIT licence,
# Copyright (c) 2025 UK AI Security Institute), so that the build context is inside this repository.
# One path of the installed package still goes into the log: ControlArena loads `bash_tasks.json` by
# its absolute path and Inspect records that as the dataset location. The image is built with the
# host's network; the running container has none (compose.yaml next to this file). `alpine:latest` is
# not pinned upstream: the manifest records the image the run used.
```

## The compose file against ControlArena 19.0.0

Not a copy. Against `control_arena/settings/bash/compose.yml`: `network_mode: none`, `pids_limit: 256` and
`stop_grace_period: 1s` are added; the upstream `networks:` block (for podman) is left out; the comments differ.
The build, `init`, the command, the CPU and memory limits are the same. No `user:` in either.

## No queue spec

The run was started by hand with `scripts/run-probe`. A queue spec was drafted before the run and dropped; it was
never in the pilot clone and it is not here.

## References in these files that do not resolve here

The files are left as they ran. These names point into the repository they came from:

| File | Reference |
|---|---|
| `control/bash/task.py` | `control/apps/task.py` (docstring, twice); `python -m tm.run`; `python -m tm.probe_readout`; the comment "The honest APPS runs needed one or two calls" |
| `control/bash/compose.yaml` | `control/apps/compose.yaml` ("this repository's hardened policy"); "the hardened policy of the APPS runs" |
| `scripts/run-probe` | `scripts/env.sh`, `python -m tm.run`, `mini-mode` (the mode switch of the machine) |
| `tm/probe_readout.py` | `from tm.manifest import REPO`, `from tm.report import sample_record`; the docstring names `tm.report` |
| `results/*.md` | `python -m tm.probe_readout`, `scripts/run-probe`, `control/apps/task.py`, "the APPS runs" |
| `manifests/…json` | `dataset` and `dataset_path` name a place the log was never uploaded to |

## Changes made so that the code stands alone

The pilot's files are not changed. The code that runs is new files at the top of the repository:

| New file | From | What changed | Why |
|---|---|---|---|
| `reconcile/readout.py` | `tm/probe_readout.py` | The two imports from `tm` are gone. `REPO` is computed in the file. The seven fields that came from `tm.report.sample_record` (id, error, main-task value, tool-call names, parse errors, other errors, seconds) are computed in the file by the same expressions. It takes a path to an `.eval` file as well as a run id. | The `tm` package is not in this repository. |
| `control/bash/task.py` | `control/bash/task.py` | Docstring and comments only. The code lines are the same (`diff` of the two files without comment lines, from the first import on, prints nothing). | The comments named files of the other repository. |
| `control/bash/compose.yaml` | `control/bash/compose.yaml` | The header comment only. | The same. |
| `control/bash/Dockerfile` | `control/bash/Dockerfile` | The header comment only. | The same; the old header's first words were wrong. |
| `scripts/run`, `reconcile/run.py` | `scripts/run-probe`, and the manifest writer of the other repository | New code. It writes a smaller manifest: command, commit, dirty flag and dirty files, package versions, container images, log hashes. It refuses a dirty tree unless told. | The queue and manifest machinery of the other repository are not carried over. |

**The readout's numbers are the same.** On the pilot's log, the pilot's script in the pilot clone and
`reconcile/readout.py` here print the same 12 lines (`diff` of the two outputs prints nothing):

```
1 tool calls that parsed: 83 of 83
2 samples that submitted: 3 of 5
3 main task passed: 5 of 5
4 samples with agent sandbox activity: 5 of 5
samples stopped at a limit: 2 of 5 (custom: 2)
samples with an error: 0 of 5
```

Only someone with the private log can repeat this check.
