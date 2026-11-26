"""The parser of a monitor's answer, and the prompt. No model."""

from pathlib import Path

from monitor.task import DID_NOT_ANSWER, parse

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
