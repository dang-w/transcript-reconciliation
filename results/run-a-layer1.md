# Run A, layer 1: tool calls against sandbox events (read 22 November 2026)

Pre-registered in `run-a-layer1-preregistration.md`, with the author's prediction, at commit `455a471`. The events
were opened after the run. Tables for every tool call: `run-a-layer1-tables.md`, made by
`scripts/layer1 run-a-replication`. Five samples: every number is a count.

## Result

No tool call of run A differs from its sandbox events after the known changes. 0 of 79 commands and 0 of 79 outputs
are in the class "different".

## Pairing

Inspect opens a span for each tool call and writes the call's sandbox events inside it. All 140 events were placed
by span. None needed the time key. 0 events were not placed.

| Where the events sit | Events | What they are |
|---|---|---|
| In tool calls | 115 | |
| `init` | 5 | 1 for each sample: Inspect looks at the container |
| Setup (`add_test_file`) | 10 | 2 for each sample: it writes `test_task.py`, then runs the tests once (they fail) |
| Scorer | 10 | 2 for each sample: it writes `test_task.py` again, then runs the tests |
| Total | 140 | 130 `exec`, 10 `write_file`, 0 `read_file` |

| Tool | Calls | Events | Calls with no event | Calls with more than one event |
|---|---|---|---|---|
| `bash` | 66 | 66 | 0 | 0 |
| `run_tests` | 5 | 5 | 0 | 0 |
| `text_editor` | 8 | 44 | 0 | 4 |
| `submit` | 3 | 0 | 3 | 0 |

- The first `text_editor` call of a sample has 10 events: 9 put Inspect's helper program into the container and
  start it, and 1 carries the call. Each later `text_editor` call has 1 event.
- The `python` tool was not called.
- 22 pairs of calls of one step have events that overlap in time: the calls of one step run at the same time.

## Commands

| Class | Count | Tools |
|---|---|---|
| Same after known change: wrapper | 66 | `bash`: the event's command is `bash --login -c` and the call's command |
| Same after known change: envelope | 8 | `text_editor`: the event's command is the helper program, and its input is one JSON-RPC message that holds the call's arguments |
| Cannot compare: the call holds no command | 5 | `run_tests`: the call has no arguments. The event shows what runs: `pytest test_task.py`. |
| Different | 0 | |

## Exit codes

The transcript holds no exit code. The `bash` tool returns the error stream and the output stream as one text, and
nothing else. So no comparison of exit codes is possible; the event is the only record.

| | Count |
|---|---|
| Tool calls whose event has an exit code other than 0 | 3, all `bash`, all in sample 574105 (steps 1, 2 and 12) |
| Of these, tool results that show an error | 0 |

In the 3 cases the last command of the line ended with a status other than 0 and no fault: a `grep` with no
match (2), a test that was false (1).

## Outputs

| Class | Count |
|---|---|
| Same | 48 |
| Same after known change: cut | 14 |
| Same after known change: envelope | 8 |
| Same after known change: layout | 5 |
| Same after known change: stream separator | 4 |
| Different | 0 |

- **Cut:** the event keeps 20 lines. For these 14 outputs the first 20 lines agree. The text after line 20 was not
  compared, because the event does not hold it.
- **Stream separator:** the event puts an empty line between the error stream and the output stream. The tool
  result puts one line end there.
- **Envelope** and **layout** are known changes that were added after the events were read, as the
  pre-registration allows. Envelope: the event's output is a JSON-RPC message whose `result` member is the tool
  result (`text_editor`). Layout: the tool result is the event's output inside the labels `STDOUT:` and `STDERR:`
  with indentation (`run_tests`).
- **The model's view:** in 82 of 82 tool calls, the message that the model received is the same text as the
  tool's result. ControlArena did not shorten any output in this run.

## Three things that the events show and the transcript does not

1. **The exit code.** See above.
2. **The order of the streams.** The tool result puts all of the error stream before all of the output stream. The
   model reads lines in an order in which they were not written (for example 26576 step 6, 511704 step 6). The
   event has the same order, so layer 1 cannot show the true order either.
3. **The scorer writes the test file again** before it runs the tests. A change to `/test_task.py` by the agent
   would not change the score. Reading the file is still possible, and 5 of 5 samples read it.

## The pilot's log, for comparison

The same command on the pilot's private log gives the same classes: 0 different, 150 events (125 in tool calls,
5 `init`, 10 setup, 10 scorer), 4 exit codes other than 0 with no error in the tool result. A reader cannot repeat
this, because that log is not published.

## Against the predictions

| Question | The author's prediction (confidence) | Result |
|---|---|---|
| Do commands differ? | yes, same after a known change (medium) | As predicted: 74 of 79 are the same after a known change, 0 are different, 5 have no command in the call. |
| Do exit codes differ? | yes, low count (low) | Not comparable: the transcript holds no exit code. 3 events have an exit code other than 0 that the transcript does not show. The author decides how to score this. |
| Do outputs differ, apart from the known cuts? | yes (medium) | No: 0 different. 17 outputs differ only by a known change other than the cut. |
| Where do the extra events come from? | several events for one call; `bash` and `python` the likely tools (medium) | Not as predicted. `bash` has 1 event for each call, and `python` was not called. The extra events are: 25 outside tool calls (`init`, setup, scorer), and 36 in the first `text_editor` call of 4 samples. |
| Does a tool call other than `submit` have no event? | yes (high) | No: 0 such calls. |

The prediction of the author's claude.ai session (not the author's): "few or no differences in content; some tool
calls map to more than one sandbox event, `text_editor` most likely". Both parts agree with the result.

## What this cannot show

- An event is Inspect's own record of what it sent to the container. The process that writes the tool result
  also writes the event. Agreement between them does not show that the transcript matches what happened in the
  container. That is layer 3.
- An event shows one command line. It does not show what that command started.
- The text of an output after its first 20 lines (14 outputs).
- How the `python` tool appears in events. It was not called.
- Anything beyond 5 samples of one model on one setting, in honest mode, on `inspect-ai` 0.3.275.
