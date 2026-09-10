import json
from pathlib import Path

import pytest

from nucleus import ask as ask_module
from nucleus.model import ModelReply
from nucleus.store import Store

FLOW_ID = "conn-obs-fable5-2026-07-10-affect-work-momentum-compass"
FLOW_QUOTE = "Momentum is Adam's compass"


def reading(outcome="no", **extra):
    base = {"said": "q", "numbers": "", "outcome": outcome, "heSaidTheWordItself": [], "hisRoutesSentItHere": [],
            "anotherRouteWasPossible": [], "noMeaningAddedYet": [], "mustAskFirst": None, "stopped": None}
    base.update(extra)
    return base


def fake_model(payload):
    def call(prompt: str) -> ModelReply:
        assert "===== graph:" in prompt and "===== meanings:" in prompt and "===== the contract =====" in prompt
        return ModelReply(provider="fake", model="fake", text=json.dumps(payload))
    return call


@pytest.fixture
def store(tmp_path: Path):
    return Store(tmp_path / "nucleus.sqlite3")


def test_aligned_end_to_end(store):
    payload = {"answer": "aligned", "words": [{"word": "FLOW", "why": "Your word names the state the question asks about."}],
               "records": [{"id": FLOW_ID, "quote": FLOW_QUOTE, "why": "Your compass points at this."}], "possibility": []}
    result = ask_module.ask("What is FLOW?", store=store, model_call=fake_model(payload), brief=lambda q: reading())
    assert result.status == "answered" and result.answer == "aligned"
    assert result.text.startswith("aligned and why")
    assert "FLOW — “" in result.text and "Your compass points at this." in result.text
    names = [s["name"] for s in result.steps]
    assert names == ["1 question in", "2 dictionary reads it", "3 nucleus read whole", "4 one model call", "5 the gate", "6 answer out"]
    assert all(s["finished"] for s in result.steps)
    assert result.bytes_sent > 300_000
    saved = store.answer(result.question_id)
    assert saved["status"] == "answered" and saved["text"] == result.text


def test_not_sure_saves_possibility_as_candidates(store):
    payload = {"answer": "not_sure", "words": [], "records": [{"id": FLOW_ID, "quote": FLOW_QUOTE, "why": "It touches the theme without deciding it."}],
               "possibility": [{"links": [FLOW_ID, "PULLED"], "proposed": "The compass and the pull may be one feeling.", "would_show": "A week with both logged."}]}
    result = ask_module.ask("Peptides or social media?", store=store, model_call=fake_model(payload), brief=lambda q: reading())
    assert result.status == "answered" and result.answer == "not_sure"
    assert "possibility" in result.text
    rows = store.connection.execute("SELECT proposed FROM candidates WHERE question_id = ?", (result.question_id,)).fetchall()
    assert rows == [("The compass and the pull may be one feeling.",)]


def test_dont_know_end_to_end(store):
    payload = {"answer": "dont_know", "words": [], "records": [], "possibility": []}
    result = ask_module.ask("How early should I be at the airport?", store=store, model_call=fake_model(payload), brief=lambda q: reading())
    assert result.status == "answered"
    assert result.text == "I don't know. There is nothing in your records that points to a conclusion."


def test_advice_or_a_fourth_answer_is_refused_and_kept(store):
    payload = {"answer": "advice", "words": [], "records": [], "possibility": [], "text": "Take a break and come back."}
    result = ask_module.ask("Should I rest?", store=store, model_call=fake_model(payload), brief=lambda q: reading())
    assert result.status == "refused"
    assert "not in the contract" in result.reason or "three answers" in result.reason
    saved = store.answer(result.question_id)
    assert saved["status"] == "refused" and json.loads(saved["reply_json"])["answer"] == "advice"


def test_invented_quote_is_refused(store):
    payload = {"answer": "aligned", "words": [], "records": [{"id": FLOW_ID, "quote": "Momentum is Adam's map", "why": "Why."}], "possibility": []}
    result = ask_module.ask("What is FLOW?", store=store, model_call=fake_model(payload), brief=lambda q: reading())
    assert result.status == "refused" and "character for character" in result.reason


def test_a_mark_with_no_number_stops_before_any_model_call(store):
    calls = []
    def never(prompt):
        calls.append(prompt)
        raise AssertionError("the model must not be called")
    result = ask_module.ask("💥", store=store, model_call=never, brief=lambda q: reading("stopped", stopped="💥 is on the screen and has no number."))
    assert result.status == "stopped" and result.text == "💥 is on the screen and has no number."
    assert calls == []
    assert [s["name"] for s in result.steps] == ["1 question in", "2 dictionary reads it"]


def test_two_meanings_none_named_asks_before_any_model_call(store):
    result = ask_module.ask("SHELL", store=store, model_call=lambda p: (_ for _ in ()).throw(AssertionError()), brief=lambda q: reading("ask", mustAskFirst="SHELL is two meanings. Which one."))
    assert result.status == "stopped" and result.text == "SHELL is two meanings. Which one."


def test_model_failure_is_saved_and_reported(store):
    def broken(prompt):
        raise RuntimeError("no network")
    result = ask_module.ask("What is FLOW?", store=store, model_call=broken, brief=lambda q: reading())
    assert result.status == "failed" and "no network" in result.reason
    row = store.connection.execute("SELECT ok, error FROM model_calls").fetchone()
    assert row == (0, "no network")
