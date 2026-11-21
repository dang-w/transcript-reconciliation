"""The readout's counting rules, on hand-made samples. No log file, no model."""

from types import SimpleNamespace as NS

from reconcile.readout import answers, executed_calls, sample_record


def call(name: str, id_: str, parse_error: str | None = None) -> NS:
    return NS(function=name, id=id_, parse_error=parse_error)


def sample(
    calls: list[NS], *, unparsed_events: tuple[str, ...] = (), limit: str | None = None, main="C"
) -> NS:
    events = [NS(event="model") for _ in calls]
    for c in calls:
        error = NS(type="parsing") if c.id in unparsed_events else None
        events.append(NS(event="tool", id=c.id, function=c.function, error=error))
    events += [NS(event="sandbox", action="exec"), NS(event="sandbox", action="write_file")]
    return NS(
        id=1,
        error=None,
        messages=[NS(role="user", tool_calls=None), *[NS(role="assistant", tool_calls=[c]) for c in calls]],
        events=events,
        scores={"bash_scorer": NS(value={"main_task_success": main})},
        limit=NS(type=limit) if limit else None,
        total_time=12.34,
    )


def test_a_call_that_did_not_parse_is_not_executed():
    s = sample(
        [call("bash", "a"), call("bash", "b", parse_error="bad json"), call("submit", "c")],
        unparsed_events=("c",),
    )
    assert executed_calls(s) == ["bash"]
    record = sample_record(s)
    assert record["tool_calls"] == 3 and record["tool_calls_parsed"] == 1
    assert record["submitted"] is False
    assert record["agent_sandbox_tool_calls"] == 1


def test_only_the_sandbox_tools_count_as_sandbox_activity():
    record = sample_record(sample([call("read_tool_output", "a"), call("submit", "b")]))
    assert record["agent_sandbox_tool_calls"] == 0
    assert record["submitted"] is True
    assert record["sandbox_events"] == {"exec": 1, "write_file": 1}


def test_answers_count_samples_and_limits_by_type():
    records = [
        sample_record(sample([call("bash", "a"), call("submit", "b")])),
        sample_record(sample([call("text_editor", "a")], limit="custom", main="I")),
        sample_record(sample([call("submit", "a", parse_error="x")], limit="time")),
    ]
    assert answers(records) == {
        "1 tool calls that parsed": "3 of 4",
        "2 samples that submitted": "1 of 3",
        "3 main task passed": "2 of 3",
        "4 samples with agent sandbox activity": "2 of 3",
        "samples stopped at a limit": "2 of 3 (custom: 1, time: 1)",
        "samples with an error": "0 of 3",
    }
