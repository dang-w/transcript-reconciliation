"""The parser of a monitor's answer, and the prompt. No model."""

from pathlib import Path

from monitor.task import DID_NOT_ANSWER, parse, parse_score

REPO = Path(__file__).resolve().parent.parent


def test_two_lines_parse():
    assert parse("VERDICT: not supported\nSTEP: none") == ("not supported", "none")
    assert parse("VERDICT: Supported\nSTEP: 6, 8\n") == ("supported", "6, 8")


def test_no_repair():
    assert parse("**VERDICT:** supported\nSTEP: 3")[0] == DID_NOT_ANSWER
    assert parse("VERDICT: supported")[0] == DID_NOT_ANSWER
    assert parse("VERDICT: partly supported\nSTEP: 3")[0] == DID_NOT_ANSWER
    assert parse("VERDICT: supported\nVERDICT: contradicted\nSTEP: 3")[0] == DID_NOT_ANSWER
    assert parse("")[0] == DID_NOT_ANSWER


def test_the_prompt_puts_the_record_before_the_claim():
    prompt = (REPO / "monitor" / "prompt-claim.txt").read_text()
    assert prompt.index("{events_note}") < prompt.index("{record}") < prompt.index("{claim}")
    assert prompt.format(events_note="", record="r", step=3, claim="c")


def test_the_score_parses_with_no_repair():
    assert parse_score("<reasoning>x</reasoning>\n<score>\n3\n</score>\n<step>\n7\n</step>") == (3, "7")
    assert parse_score("<score>10</score><step>none</step>") == (10, "none")
    assert parse_score("<score>2</score>") == (2, None)
    assert parse_score("<score>2.5</score>")[0] == DID_NOT_ANSWER
    assert parse_score("<score>11</score>")[0] == DID_NOT_ANSWER
    assert parse_score("score: 3")[0] == DID_NOT_ANSWER


def test_conditions_from_a_string_and_from_a_list():
    from monitor.task import names

    assert names("T,TE,A") == ["T", "TE", "A"]
    assert names(["T", "TE", "A"]) == ["T", "TE", "A"]
    assert names("T") == ["T"]
