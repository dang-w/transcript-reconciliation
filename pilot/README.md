# The pilot (17 November 2026)

A private run of 5 samples, made before this repository existed. It is a pilot, not the record.

| | |
|---|---|
| What | The honest policy on the first 5 tasks of ControlArena 19.0.0's Bash setting, network off, one model (Qwen3.8-27B), no monitor |
| When | 17 November 2026, 17:56 to 19:30 UTC |
| Where | A private clone of another repository of the same author, with no remote |
| Why it is here | The direction of this repository was chosen on what the pilot showed. A reader must be able to see that. |
| Status | Runs made in this repository supersede it as the record. Everything it showed was seen once and is not yet replicated. |

## What is in this folder

The files as they were, byte for byte (`PROVENANCE.md` has the hashes and the source commits). They do not run
from here: they import a package of the repository they came from. The code that runs is in `reconcile/` and
`control/bash/` at the top of this repository.

| File | What it is |
|---|---|
| `results/bash-probe-preregistration.md` | How the run was to be read, written before it, with the prediction |
| `results/bash-probe-2026-11-17.md` | The readout, written on 21 November |
| `manifests/f1-gen-bash-honest-probe.json` | The manifest the run wrote |
| `control/bash/` | The task, the compose file and the Dockerfile |
| `scripts/run-probe` | The invocation. No queue spec was used. |
| `tm/probe_readout.py` | The readout script |

## The log is not published

The log exists and is kept privately. Its sha256 is
`459d7206887bcc70c826041c5ad704ec4b490494f48ef93f447a2271f02acb01` (221,205 bytes), the value in the manifest.
It is not published for two reasons: the prediction was not committed before the run, and the log holds two
items that would need a decision before publication (a private-range network address that a command printed, and
the absolute path of the Python environment of that machine). The first public run is made to fix both.

Two fields of the manifest name a dataset and a path in it (`dataset`, `dataset_path`). The tool that wrote the
manifest fills them for every run. The log was never uploaded there or anywhere.

## What the pilot showed (seen once, not replicated)

Counts from 5 samples. No count here is a rate.

| | |
|---|---|
| Tool calls that parsed | 83 of 83 |
| Samples that submitted | 3 of 5 |
| Samples that stopped at the step limit (15) | 2 of 5 |
| Samples that stopped at the time limit | 0 of 5 |
| Main task passed | 5 of 5 |
| Cases where the model's account differed from the tool output, or had no support in it, and the model did not see it | 4 |
| Tasks passed with a stand-in for a package that could not be installed | 2 (`nano`, `sshd`) |

Details are in the readout. By the pre-registered rule the verdict was "usable".

## What must be said about it

- **The prediction was not committed before the run.** It was in the pre-registration file: the file's
  modification time is 17:53:36 UTC and the run started at 17:56:09 UTC. The evidence is a file time, not a commit.
  The manifest records the tree as dirty for this reason.
- **The 574105 daemon case is an inference from the log.** The readout says the daemon had stopped when the model
  said it was running. The container was not run again to confirm it.
- **Three things in the pre-registration were wrong.**
  1. "A task that needs to install a package fails whatever the model does." Two such tasks passed, with stand-ins.
  2. The expectation that the time limit would stop samples before the step limit. No sample came near the
     time limit; 2 stopped at the step limit.
  3. The submission criterion (answer 2). The scorer does not need a submission: it runs the tests on the
     container as it is at the end. The criterion measures something the score does not depend on.
- **Truncation was not found, and it was not tested.** The longest tool output was 3,983 characters. No output was
  long enough to show what happens to a long one.
- **The container ran as root with default capabilities, as upstream.**
- **The agent could read the test file.** `/test_task.py` was in the container and all 5 samples read it at step 2.
  The scorer runs the same file. This is recorded as observed.
- **The transcripts were read by one reader, once.** The mismatch counts are that reader's.

## What it cannot show

Nothing about attacks, monitors, catch rates, other models, other settings, or the 252 tasks that were not run.
Five samples, one seed.
