# Bash tool-use probe: how it is read (written before the run)

Run: `f1-gen-bash-honest-probe`. Task: `control/bash/task.py@bash_generate_honest`, the first 5 tasks of
ControlArena's Bash setting, honest mode, network off. Untrusted model: Qwen3.8-27B at the research preset
(thinking budget 12288), 16384 output tokens, temperature 0, seed 1, at most 15 steps and 5,400 s per sample.

A private probe (Dan, 2026-11-17): started by hand with `scripts/run-probe` in a second clone that has no
remote, not through the queue. The log is not published and the manifest is not in the public ledger. If the
probe later supports a public statement, that statement says so.

## The question

Can the untrusted model drive tools in a sandbox well enough for a setting with shell access to be usable on
this machine? APPS gives the agent no tools except `submit`, so it cannot answer this.

This is a probe, not a result. Five samples give no rate worth an interval, and none is reported as one.

## What is read, from `python -m tm.probe_readout f1-gen-bash-honest-probe`

1. Tool calls that parsed, of all tool calls.
2. Samples with a `submit` call that parsed, of 5.
3. Samples whose main task passed, of 5.
4. Samples with at least one sandbox tool call (`bash`, `python`, `text_editor`, `run_tests`) that parsed, of 5.

A call that does not parse never runs, so it counts for answer 1 only.

Also recorded: samples stopped at a limit, by type (`custom` is the step limit, `time`, `message`), samples
with an error, seconds per sample and model calls per sample.

## The rule, fixed now

- **The limit is the finding:** 3 or more of 5 samples stop at the time limit or at the step limit. No
  verdict on the model follows. The next step is the same probe with a different limit or a smaller thinking
  budget. This clause is read first.
- **Usable:** answer 4 is at least 4 of 5, answer 2 is at least 3 of 5, and at most 1 in 10 tool calls fails
  to parse. A larger run in this setting is then worth queuing.
- **Not usable as configured:** answer 2 is 0 or 1 of 5, or more than 3 in 10 tool calls fail to parse. The
  next step is then a different model or scaffold, not more samples.
- **Between the two:** read the transcripts before deciding; say so in the record.

Answer 3 does not enter the rule. With the network off, a task that needs to install a package fails whatever
the model does, so the main-task rate here mixes the model with the sandbox policy.

## Known limits

- The container runs as root with default capabilities (`control/bash/compose.yaml` says why). This is not the
  hardened policy of the APPS runs.
- `alpine:latest` is not pinned upstream, so the image can differ between builds.
- The step limit of 15 is a guess.
- The time limit will probably stop a sample before the step limit does. A call that uses all 16384 output
  tokens takes about 1,260 s (`control/apps/task.py`), so 5,400 s holds about 4 such calls. Short calls are
  possible; no timing for a multi-step tool task exists on this machine.
- Time per sample is unknown in advance; the measured times set the estimate for any later run.
- Answer 4 shows that a sandbox tool call parsed and ran. It does not show that the call did something useful.

## Prediction

- I think we'll likely find a few small differences that aren't captured - some truncation of tool calls, or small differences in tool call output vs. the description of the calls.