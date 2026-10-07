"""Adam's own form for the middle answer, filled with no typing from him. Adam, 2026-10-07: "My middle answer
adjustments are completed." and "I will not be there to type this shit every time." """

import pytest

from nucleus import ask as ask_module, english, gate, middle

from test_narrative import DOCTOR, reading, store  # noqa: F401  (fixtures)


def test_every_fixed_word_is_his_verbatim():
    assert middle.EXPLANATION == ("Some relationships, but not enough to justify is an opportunity for growth.  This is a "
                                  "chance to transform potential into a new skill that can compound into something more "
                                  "and more valuable.")
    assert middle.SUGGESTIONS == "Suggestions to move the relationships into a more predictable category"
    assert middle.BELIEF_TEXT == ("Speed. Discernment. Curiosity.  Confidence.  These are important to you.  Do any of them "
                                  "apply more or less when moving this issue further towards a predictable outcome?")
    assert middle.ASK == "What would you like AI to revisit? Anything come to mind?"


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_the_doctor_entry_fills_his_form(monkeypatch, store):  # noqa: F811
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.delenv("NUCLEUS_NO_MODEL", raising=False)

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask(DOCTOR, store=store, model_call=never, brief=lambda q: reading(unknown=["REASONS", "AVOID", "DOCTOR"]),
                            explain_call=never)
    saved = store.answer(result.question_id)
    filled = middle.form(saved["text"], saved["reply_json"], [])
    assert filled["explanation"] == middle.EXPLANATION and filled["answer"] == gate.FIRST_LINE["not_sure"]
    assert [section["head"] for section in filled["sections"]] == ["Reasons", "Belief"]      # no options before the night run
    assert filled["sections"][0]["lines"][0].startswith("“Changes only stick for Adam when they feel innocent and easy")
    assert filled["ask"] == middle.ASK


def test_the_night_runs_options_fill_the_suggestions():
    options = [{"brings_in": "ANTICIPATORY ANXIETY", "shown": "Anticipatory anxiety lies.",
                "proposed": "Stress that builds before acting may be affecting why you avoid going to the doctor.",
                "would_show": "The feelings that arise between considering a doctor visit and attending it indicate whether anticipatory stress is involved."}]
    filled = middle.form("There is some relationship, but not enough to justify causation.", None, options)
    assert [section["head"] for section in filled["sections"]] == [middle.SUGGESTIONS, "Belief"]
    assert filled["sections"][0]["lines"][0].startswith("ANTICIPATORY ANXIETY — “Anticipatory anxiety lies.”\nStress that builds")
