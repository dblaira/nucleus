"""The middle answer's feedback as question-and-answer rows. Adam, 2026-10-07: "I am think a feedback readout like I
have built in the Themes section of SAVY app will work." "The word "Your" and "You" will be removed." """

import re

import pytest

from nucleus import ask as ask_module, english, gate, readout

from test_narrative import DOCTOR, reading, store  # noqa: F401  (fixtures)


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_the_doctor_entry_reads_as_questions_and_answers(monkeypatch, store):  # noqa: F811
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.delenv("NUCLEUS_NO_MODEL", raising=False)

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask(DOCTOR, store=store, model_call=never, brief=lambda q: reading(unknown=["REASONS", "AVOID", "DOCTOR"]),
                            explain_call=never)
    assert result.answer == "not_sure"
    rows = readout.middle(store.explanation(result.question_id)["parts"])
    assert [row["question"] for row in rows] == [
        "What is reasons?", "What is doctor?", "What sits in both Belief and Health?", gate.MIDDLE_ASKS]
    assert rows[0]["answer"] == "a rational motive for a belief or action\n" \
                                "Belief: Core beliefs, values, worldview, and personal philosophy."
    assert rows[1]["answer"].endswith("Not in the dictionary or the records.")
    assert rows[2]["answer"].startswith("Changes only stick for Adam when they feel innocent and easy")   # his record, verbatim
    assert rows[3]["answer"] == ""
    for row in rows[:-1]:                    # the last question is his own sentence of September 9, kept as he wrote it
        assert not re.search(r"\b[Yy]our?\b", row["question"] + " " + row["answer"]), row


def test_no_parts_no_rows():
    assert readout.rows(None) == [] and readout.middle(None) == [
        {"symbol": readout.FOLLOW_UP, "question": gate.MIDDLE_ASKS, "answer": ""}]
