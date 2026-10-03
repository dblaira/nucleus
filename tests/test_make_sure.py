"""What the second chat checked after Adam wrote, 2026-10-02: "These are the steps being taken.  make sure."

Three things found while checking the engine his Cowboyai app talks to:
1. his phone, the page and the answer being written all reach one record at once; under load a request was dropped
2. the answer was saved a moment before its paragraph; a phone that looked in that moment stopped with no paragraph
3. on the page, the thumb under the paragraph posted to the row thumbs and was refused: his thumb at 20:04 was not saved
"""

import threading
import time
from pathlib import Path

from nucleus import ask as ask_module
from nucleus import serve
from nucleus.store import Store

COMPASS = "conn-obs-fable5-2026-07-10-affect-work-momentum-compass"
SLOW = "Sometimes I get mad at how slow things feel.  Like now.  Fuck! Things feel slow."
DOCTOR = "What are reasons I would avoid going to the doctor?"


def reading(unknown=()):
    return {"said": "q", "numbers": "", "outcome": "no", "heSaidTheWordItself": [], "hisRoutesSentItHere": [],
            "anotherRouteWasPossible": [], "noMeaningAddedYet": list(unknown), "mustAskFirst": None, "stopped": None}


def never(prompt):
    raise AssertionError("the model was asked")


def test_his_phone_and_the_answer_being_written_reach_the_record_at_once(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    earlier = []
    for i in range(30):
        question_id = store.new_question(f"an earlier entry {i % 3}", "web")
        store.save_answer(question_id, "answered", "not_sure", "Not sure.", "{}", True, None)
        earlier.append(question_id)
    errors: list[str] = []
    until = time.time() + 1.5

    def the_answer_being_written():
        try:
            while time.time() < until:
                question_id = store.new_question(DOCTOR, "web")
                for name in ("1 question in", "2 dictionary reads it", "3 your phrases found"):
                    store.start_step(question_id, name)
                    store.finish_step(question_id, name)
                store.save_explanation(question_id, "You said doctor.", None, "code", "narrative", time.time())
                store.save_answer(question_id, "answered", "not_sure", "Not sure.", "{}", True, None)
        except Exception as error:      # noqa: BLE001 - every error is the failure this test is about
            errors.append(repr(error))

    def his_phone_looking():
        try:
            while time.time() < until:
                for question_id in earlier[:6]:
                    store.question(question_id)
                    store.answer(question_id)
                    store.steps(question_id)
                    store.times_asked("an earlier entry 1", question_id)
                    store.explanation(question_id)
                store.recent(5)
        except Exception as error:      # noqa: BLE001
            errors.append(repr(error))

    threads = [threading.Thread(target=the_answer_being_written)] + [threading.Thread(target=his_phone_looking) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []


def paragraph_when_the_answer_is_saved(store: Store) -> list:
    """Each time an answer is saved: was its paragraph already there?"""
    seen = []
    save_answer = store.save_answer

    def watching(question_id, *args, **kwargs):
        seen.append(store.explanation(question_id))
        return save_answer(question_id, *args, **kwargs)

    store.save_answer = watching
    return seen


def test_the_paragraph_is_there_before_the_answer_his_phone_waits_for(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    store = Store(tmp_path / "n.sqlite3")
    store.add_link("MOMENTUM", COMPASS, "Momentum is Adam's compass", "why.", "links:MOMENTUM", "fake", "fake", kind="serves the purpose of")
    seen = paragraph_when_the_answer_is_saved(store)

    # his dictionary reached a word of his
    result = ask_module.ask(SLOW, store=store, model_call=never, brief=lambda q: reading(unknown=["MAD", "SLOW"]), explain_call=never)
    assert result.status == "answered" and seen[-1] is not None and seen[-1]["status"] == "shown"

    # no word of his: judged by his ontology and his knowledge graph
    result = ask_module.ask(DOCTOR, store=store, model_call=never, brief=lambda q: reading(unknown=["REASONS", "AVOID", "DOCTOR"]), explain_call=never)
    assert result.answer == "not_sure" and seen[-1] is not None and "Health" in seen[-1]["text"]

    # nothing of his holds it
    result = ask_module.ask("What is the capital of France?", store=store, model_call=never,
                            brief=lambda q: reading(unknown=["CAPITAL", "FRANCE"]), explain_call=never)
    assert result.answer == "dont_know" and seen[-1] is not None and seen[-1]["text"].startswith("Nothing in your dictionary")
    assert len(seen) == 3


def test_on_the_page_the_thumb_under_the_paragraph_keeps_its_own_door():
    assert "answerEl.querySelectorAll('.thumbs:not(#exthumbs) button')" in serve.PAGE
    assert "answerEl.querySelectorAll('.thumbs button')" not in serve.PAGE
