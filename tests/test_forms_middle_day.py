"""Middle-option route checks use isolated stores and explicitly fake approved choices."""

import json
import threading

import pytest

from nucleus import NUCLEUS_FILES, ask, dictionary, explain, forms, forms_middle, gate
from nucleus.graph import load_graph
from nucleus.model import ModelReply
from nucleus.store import Store
from test_forms_day import IDS, reading, setup, run, write_forms, forbidden, model_rows, fixture_form


@pytest.fixture(autouse=True)
def legacy_long_lines(monkeypatch):
    """These fixtures test the exact mechanics of frames Adam retired on 2026-10-02 as
    too long and not his words. The 25-word day limit is tested in test_forms_short.py."""
    monkeypatch.setattr(forms, 'MAX_WORDS', None)



MISSING_WHY = "Your records do not show how the app behaved."


def payload(answer="not_sure"):
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    record = graph.find(IDS[0])
    return {"answer": answer, "words": [{"word": "FLOW", "why": "FLOW fits part of this question; " + MISSING_WHY}],
            "records": [{"id": record.leaf, "quote": record.label, "why": "FLOW names what carries you."}],
            "possibility": []}


def original_text(reply):
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    verdict = gate.check(reply, graph, meanings)
    assert verdict.ok
    return verdict.text


def selected():
    # The source markers distinguish a middle-option choice from older quote forms.
    text = "FLOW lines up; Your records do not show how the app behaved."
    return forms.Filled("F-51", text, (
        forms.Part("FLOW", "screen.words[0]"),
        forms.Part(" lines up; ", "form.sentence"),
        forms.Part(MISSING_WHY, "screen.whys[0].text"),
    ))


@pytest.fixture
def model_route(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_FORMS_ONLY", raising=False)
    monkeypatch.setattr(ask.links_module, "paint", lambda *args: None)
    path = tmp_path / "forms.txt"
    write_forms(path)
    monkeypatch.setattr(forms, "FORMS_PATH", path)
    store = Store(tmp_path / "n.sqlite3")
    yield store, path
    store.connection.close()


def model_answer(store, reply=None, **options):
    reply = payload() if reply is None else reply
    return ask.ask("Why do I circle this app?", store=store, brief=reading,
                   model_call=lambda prompt: ModelReply("fixture", "fixture", json.dumps(reply)), **options)


def test_approved_middle_form_replaces_only_painted_opening_without_model_or_thread(setup, monkeypatch):
    store, _path = setup
    for record_id in IDS[1:]:
        store.thumb("FLOW", record_id, False)
    picture = ask.links_module.paint("What is FLOW?", reading("What is FLOW?"), [], store,
                                    load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"]),
                                    dictionary.load_meanings(NUCLEUS_FILES["meanings"]))
    assert picture.answer == "not_sure"
    monkeypatch.setattr(forms, "pick", lambda screen: (selected(), None))
    monkeypatch.setattr(explain, "start", forbidden)
    monkeypatch.setattr(threading, "Thread", forbidden)
    result = run(store, explain_call=forbidden)
    assert result.answer == "not_sure" and result.text.split("\n", 1)[0] == selected().text
    assert result.text.partition("\n")[1:] == picture.text.partition("\n")[1:]
    assert model_rows(store, result.question_id) == []
    assert store.explanation(result.question_id)["provider"] == "form"
    assert store.answer(result.question_id)["text"] == result.text


def test_approved_middle_form_after_gate_uses_visible_screen_and_no_explanation_model(model_route, monkeypatch):
    store, _path = model_route
    seen = []

    def choose(screen):
        seen.append(screen)
        assert screen.answer == "not_sure" and screen.words == ("FLOW",)
        return selected(), None

    monkeypatch.setattr(forms, "pick", choose)
    monkeypatch.setattr(explain, "start", forbidden)
    monkeypatch.setattr(threading, "Thread", forbidden)
    monkeypatch.setattr(store, "rows_for_answer", forbidden)
    saved = store.save_answer

    def publish(question_id, *args, **kwargs):
        assert store.explanation(question_id)["provider"] == "form"
        return saved(question_id, *args, **kwargs)

    monkeypatch.setattr(store, "save_answer", publish)
    result = model_answer(store)
    assert len(seen) == 1
    assert result.text.partition("\n")[1:] == original_text(payload()).partition("\n")[1:]
    assert result.text.split("\n", 1)[0] == selected().text
    assert len(model_rows(store, result.question_id)) == 1  # the answer call, never a form choice call
    assert store.explanation(result.question_id)["text"] == "F-51 · " + selected().text


def test_saved_middle_answer_is_chosen_again_by_code_without_model(model_route, monkeypatch):
    store, _path = model_route
    choices = []
    monkeypatch.setattr(forms, "pick", lambda screen: (choices.append(screen) or selected(), None))
    monkeypatch.setattr(explain, "start", forbidden)
    first = model_answer(store)
    repeated = ask.ask("Why do I circle this app?", store=store, brief=reading,
                       model_call=forbidden, explain_call=forbidden)
    assert len(choices) == 2 and repeated.provider == "saved"
    assert repeated.text == first.text and repeated.times_asked_before == 1
    assert model_rows(store, repeated.question_id) == []
    assert store.explanation(repeated.question_id)["provider"] == "form"


@pytest.mark.parametrize("answer", ["aligned", "dont_know"])
def test_middle_day_picker_runs_only_for_not_sure(model_route, monkeypatch, answer):
    store, _path = model_route
    monkeypatch.setattr(forms, "pick", forbidden)
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    reply = payload(answer)
    if answer == "dont_know":
        reply["words"], reply["records"] = [], []
    result = model_answer(store, reply)
    assert result.text == original_text(reply)
    assert len(calls) == (1 if answer == "aligned" else 0)


def test_zero_approved_forms_keeps_model_middle_answer_and_original_explanation_path(model_route, monkeypatch):
    store, _path = model_route
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    result = model_answer(store)
    assert result.text == original_text(payload())
    assert result.text.startswith(gate.FIRST_LINE["not_sure"])
    assert calls == [(result.question_id, result.question, result.text, ["FLOW"], store, None)]
    assert store.explanation(result.question_id) is None


def test_uncheckable_middle_screen_keeps_original_fallback(model_route, monkeypatch):
    store, _path = model_route

    def refused(*args, **kwargs):
        raise forms.Refused("fixture screen lacks a printed quote")

    monkeypatch.setattr(ask.forms_middle, "from_visible", refused)
    monkeypatch.setattr(forms, "pick", forbidden)
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    result = model_answer(store)
    assert result.text == original_text(payload()) and len(calls) == 1


def test_middle_explanation_opt_out_keeps_fixed_opening(model_route, monkeypatch):
    store, _path = model_route
    monkeypatch.setattr(forms, "pick", forbidden)
    monkeypatch.setattr(explain, "start", forbidden)
    result = model_answer(store, explain_call=False)
    assert result.text == original_text(payload())
    assert store.explanation(result.question_id) is None


def middle_form(status="approved"):
    return {"number": "F-52", "when": {"answer": "not_sure", "missing_why": True},
            "sentence": forms_middle.HEADS[0] + forms_middle.TAILS["missing_why"],
            "status": status, "author": "isolated fixture; not Adam's approval", "date": "2026-10-02"}


def test_real_approved_middle_form_is_filled_from_printed_sources_after_gate(model_route, monkeypatch):
    store, path = model_route
    write_forms(path, middle_form())
    monkeypatch.setattr(explain, "start", forbidden)
    reply = payload()
    reply['words'][0]['word'] = 'FEELING MOMENTUM'
    reply['words'][0]['why'] = 'FEELING MOMENTUM fits part of this question; ' + MISSING_WHY
    reply['records'][0]['why'] = 'FEELING MOMENTUM names what carries you.'
    result = model_answer(store, reply)
    paragraph = store.explanation(result.question_id)
    assert paragraph["provider"] == "form" and paragraph["model"] == "F-52"
    assert result.text.split("\n", 1)[0] == paragraph["text"].split(" · ", 1)[1]
    assert result.text.partition("\n")[1:] == original_text(reply).partition("\n")[1:]
    step = next(s for s in result.steps if s["name"] == "5 form F-52 chosen")
    parts = json.loads(step["note"])["parts"]
    assert any(p["source"].startswith("screen.meanings[") for p in parts)
    assert any(p["source"].startswith("screen.rows[") and p["source"].endswith(".quote") for p in parts)
    assert next(p["text"] for p in parts if p["source"].startswith("screen.whys[")) == MISSING_WHY
    assert len(model_rows(store, result.question_id)) == 1


def test_real_approved_absent_kind_middle_form_uses_painted_rows_without_model(setup, monkeypatch):
    store, path = setup
    for record_id in IDS[1:]:
        store.thumb("FLOW", record_id, False)
    value = middle_form()
    value["when"] = {"answer": "not_sure", "kinds_absent": ["rejects"]}
    value["sentence"] = forms_middle.HEADS[0] + forms_middle.TAILS["absent_kind"]
    write_forms(path, value)
    monkeypatch.setattr(explain, "start", forbidden)
    monkeypatch.setattr(threading, "Thread", forbidden)
    result = run(store, explain_call=forbidden)
    assert result.answer == "not_sure" and model_rows(store, result.question_id) == []
    paragraph = store.explanation(result.question_id)
    assert paragraph["provider"] == "form" and paragraph["model"] == "F-52"
    assert result.text.split("\n", 1)[0] == paragraph["text"].split(" · ", 1)[1]
    assert result.text.split("\n", 1)[0].endswith('the rows leave out “rejects”.')


def test_existing_approved_row_form_keeps_not_sure_opening(setup, monkeypatch):
    store, path = setup
    for record_id in IDS[1:]:
        store.thumb("FLOW", record_id, False)
    write_forms(path, fixture_form(when={"answer": "not_sure", "kinds_present": ["depends on"]}))
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store, explain_call=forbidden)
    assert result.text.startswith(gate.FIRST_LINE["not_sure"])
    assert store.explanation(result.question_id)["provider"] == "form"
    assert model_rows(store, result.question_id) == []


@pytest.mark.parametrize("answer", ["aligned", "dont_know"])
def test_not_sure_form_fires_only_on_not_sure(model_route, answer):
    _store, path = model_route
    write_forms(path, middle_form())
    reply = payload(answer)
    if answer == "dont_know":
        reply["words"], reply["records"] = [], []
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    verdict = gate.check(reply, graph, meanings)
    assert verdict.ok
    screen = forms_middle.from_visible(answer, verdict.words, verdict.records, verdict.text)
    assert forms.pick(screen, path)[0] is None


@pytest.mark.parametrize("status", ["proposed", "rejected"])
def test_unapproved_middle_form_keeps_fixed_opening_and_existing_fallback(model_route, monkeypatch, status):
    store, path = model_route
    write_forms(path, middle_form(status))
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    result = model_answer(store)
    assert result.text == original_text(payload()) and len(calls) == 1
    assert store.explanation(result.question_id) is None
