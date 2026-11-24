# transcript-reconciliation

> First version, facts only. The author has not yet edited this text.

## The question

Does the record a monitor reads differ from what ran in the sandbox?

A monitor in an AI-control evaluation reads a transcript: the model's messages, its tool calls, and the tool
outputs. This repository compares that record with other records of the same run, at three layers.

| Layer | Comparison | Status |
|---|---|---|
| 1. Call against event | The transcript's tool calls with the sandbox events that Inspect records | Run A: 0 differences in 79 tool calls after the known changes. The events hold 3 exit codes that the transcript does not show. Run B: 0 differences in 117 tool calls; 2 exit codes of 143 (a shell killed by a signal) that the transcript does not show. |
| 2. Claim against output | What the model says happened with what the tool output shows | Seen in the pilot: 4 cases the model did not notice |
| 3. Command against effect | The command string with what happened in the container | Seen in the pilot: 2 cases, which are also 2 of the 4 above (a command chain that stopped before its last command; two calls of one step that ran at the same time on one file). Run B: 1 more: a `kill` command of the model stopped the container, and the model did not connect the two. A replay of the commands with no model confirmed the cause (`results/run-b-replay-574105.md`). |

## Status

| | |
|---|---|
| Runs in this repository | 2. Run B, on 23 November 2026: step limit 30, a larger context, the base image pinned; `results/run-b-step-limit.md`. Run A, the replication of the pilot, on 22 November 2026: `results/run-a-replication.md` (the readout against the pilot) and `results/run-a-layer1.md` (tool calls against sandbox events). Both were pre-registered, with the author's predictions committed before the run. |
| Logs | The dataset [`dang-w/transcript-reconciliation-logs`](https://huggingface.co/datasets/dang-w/transcript-reconciliation-logs). It holds the logs of run A and run B. Git holds a manifest for each run with the sha256 of its log. |
| Pilot | One private run of 5 samples on 17 November 2026: honest mode, one model, one setting. `pilot/README.md` |
| Code | A readout, a scan for private identifiers, a run wrapper that writes a manifest, an upload step that a person starts, and a first reconciler for layer 1 (`scripts/layer1`). |
| Survey | `docs/survey-2026-11-21.md`: versions, the Bash setting and Inspect's sandbox events across versions, the packages the tasks need |

The pilot is a probe, not a result. Its log is not published; its written record is in `pilot/`. The first run
made in this repository repeats it, with the way it is read and the author's prediction committed before it starts.

## The pilot's pre-registered rule and its outcome

The rule was written before the run (`pilot/results/bash-probe-preregistration.md`). Counts from 5 samples; none
is a rate.

| Answer | Outcome | Rule for "usable" |
|---|---|---|
| 1. Tool calls that parsed | 83 of 83 | At most 1 in 10 fails to parse: met |
| 2. Samples with a `submit` call that parsed | 3 of 5 | At least 3: met, at the threshold |
| 3. Samples whose main task passed | 5 of 5 | Not in the rule |
| 4. Samples with a sandbox tool call that parsed | 5 of 5 | At least 4: met |
| Samples stopped at a limit | 2 of 5, both at the step limit | 3 or more would have meant "the limit is the finding": not met |

Verdict by the rule: usable. Three statements in that pre-registration were wrong, and the prediction was not
committed before the run; `pilot/README.md` lists both.

## What it cannot show

- Nothing about attacks. Only honest mode ran.
- Nothing about monitors or catch rates. No monitor ran.
- Nothing about other models or other settings.
- Nothing about the 252 tasks of the setting that were not run.
- No rate. Five samples, one seed.
- Nothing that is replicated. Each observation was made once, by one reader of the transcripts.

## Relation to `trusted-monitoring`

[`trusted-monitoring`](https://github.com/dang-w/trusted-monitoring) measures how often a monitor flags attack
trajectories on the APPS setting. This repository asks a different question, on a different setting. It is not an
extension of those results and it adds nothing to them. It uses the same models and the same machine.

## Setup

| | |
|---|---|
| Versions | `control-arena` 20.1.1 and `inspect-ai` 0.3.275, pinned in `pyproject.toml` and `uv.lock`. The pilot ran on `control-arena` 19.0.0; the lock for 20.1.1 also moves `huggingface-hub` from 0.36.2 to 1.33.0 and drops `aiofiles`. |
| Setting | ControlArena's Bash setting (tasks from the Ctrl-Z paper), honest mode |
| Sandbox | `control/bash/`: ControlArena's Dockerfile with two changes. From run B the base image is `alpine` pinned by digest (the image that the pilot and run A used) in place of `alpine:latest`, so that the base does not change between runs. From run C one added line installs `nano` and `openssh-server` at build time. The compose file differs from upstream: the network is off, with a process limit and a short stop time. The container runs as root with default capabilities, as upstream. |
| Model server | An OpenAI-compatible llama.cpp server; `scripts/run` reads its key from a file outside the repository |
| Tools | `uv`, Docker, `gitleaks` |

## Commands

| Command | What it does |
|---|---|
| `scripts/readout RUN_ID` or `scripts/readout PATH.eval` | One row per sample, then the counts above |
| `scripts/run RUN_ID -- eval control/bash/task.py@bash_generate_honest …` | One recorded run: the log in `logs/RUN_ID/`, a manifest in `manifests/`. Refuses a dirty tree unless `--allow-dirty` is given. |
| `scripts/scan PATH …` | Fails on a home path, a tailnet or private network address or name, a string of a local denylist, key material. Reads `.eval` logs. `--history` also reads every commit. Reports; never redacts. Two items are exempt, with the reasons in `reconcile/scan.py`: the default network of the container tool, and the placeholder path `/home/user/`. |
| `scripts/replay RUN_ID SAMPLE_ID --to-event N` | Runs the sandbox events of one sample again in a new container, with no model, and records the state of the container after each one. |
| `scripts/publish RUN_ID [--upload]` | By hand, one run. Checks the logs against the committed manifest and runs the scan. With `--upload` it puts the logs in the dataset, downloads them again and compares the sha256. Nothing else uploads. |
| `uv run python -m pytest` | The tests. They need no model and no Docker. |

To reproduce the pilot's readout a reader needs the pilot's log, which is not published. The readout of a run made
in this repository reproduces from that run's published log with `scripts/readout PATH.eval`.

Enable the commit hook once per clone: `git config core.hooksPath .githooks`. It needs a denylist file
(`~/.config/transcript-reconciliation/denylist.txt`, one string per line; it may be empty).

## Background

- Greenblatt et al., "AI Control: Improving Safety Despite Intentional Subversion" (2023).
- ControlArena issue #943, "Is 'nothing monitors actual sandbox execution' a gap worth closing?" (open on
  21 November 2026). Others there work on kernel-level capture and on a filesystem snapshot scorer.

## Licence

MIT. `control/bash/Dockerfile` is ControlArena's (MIT, Copyright (c) 2025 UK AI Security Institute).
