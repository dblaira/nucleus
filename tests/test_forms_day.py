"""Slice 2: real painted answers, isolated stores and approved test fixtures only."""

import json
import threading

import pytest

from nucleus import NUCLEUS_FILES, ask, explain, forms
from nucleus.graph import load_graph
from nucleus.model import ModelReply
from nucleus.store import Store

IDS = [
    "conn-obs-fable5-2026-07-10-affect-work-momentum-compass",
    "conn-obs-mined-2026-07-10-external-scaffolding-by-design",
    "conn-obs-mined-2026-07-10-affect-is-his-blind-spot",
]
OLD_STEPS = [ask.STEP_QUESTION, ask.STEP_DICTIONARY, ask.STEP_PHRASES,
             ask.STEP_NUCLEUS, ask.STEP_MODEL, ask.STEP_GATE, ask.STEP_ANSWER]


def forbidden(*args, **kwargs):
    raise AssertionError("this path must not call a model or start a thread")


def reading(question):
    return {"said": question, "outcome": "yes", "heSaidTheWordItself": [{"word": "FLOW"}]}


def fixture_form(number="F-7", **changes):
    value = {"number": number, "when": {"answer": "aligned", "kinds_present": ["depends on"]},
             "sentence": "Your rows say {word} depends on {count} things you have written down.",
             "status": "approved", "author": "isolated test fixture; not Adam's approval", "date": "2026-10-01"}
    value.update(changes)
    return value


def toml_value(value):
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{key} = {toml_value(item)}" for key, item in value.items()) + " }"
    return json.dumps(value, ensure_ascii=False)


def write_forms(path, *values):
    blocks = []
    for value in values:
        lines = ["[[forms]]"]
        lines += [f"{key} = {toml_value(item)}" for key, item in value.items() if key != "when"]
        lines += ["[forms.when]"] + [f"{key} = {toml_value(item)}" for key, item in value["when"].items()]
        blocks.append("\n".join(lines))
    path.write_text("\n\n".join(blocks) + "\n" if blocks else "forms = []\n")


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_FORMS_ONLY", raising=False)
    monkeypatch.setattr(ask.model_module, "call", forbidden)
    path = tmp_path / "forms.txt"
    write_forms(path)
    monkeypatch.setattr(forms, "FORMS_PATH", path)
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    for record_id in IDS:
        record = graph.find(record_id)
        assert record is not None and graph.is_accepted(record)
        store.add_link("FLOW", record_id, record.label, "", "links:FLOW", "fixture", "fixture", kind="depends on")
    yield store, path
    store.connection.close()


def run(store, **kwargs):
    return ask.ask("What is FLOW?", store=store, model_call=forbidden, brief=reading, **kwargs)


def model_rows(store, question_id):
    return store.connection.execute("SELECT * FROM model_calls WHERE question_id = ?", (question_id,)).fetchall()


def misses(store):
    return store.connection.execute("SELECT question_id, picture_json, reason FROM form_misses ORDER BY created").fetchall()


def test_approved_form_has_zero_model_rows_and_no_thread(setup, monkeypatch):
    store, path = setup
    write_forms(path, fixture_form())
    monkeypatch.setattr(explain, "start", forbidden)
    monkeypatch.setattr(threading, "Thread", forbidden)
    result = run(store, explain_call=forbidden)
    assert result.status == "answered" and result.answer == "aligned" and result.provider == "links"
    assert model_rows(store, result.question_id) == []
    paragraph = store.explanation(result.question_id)
    assert paragraph["status"] == "shown" and paragraph["provider"] == "form" and paragraph["model"] == "F-7"
    assert paragraph["text"] == "F-7 · Your rows say FLOW depends on 3 things you have written down."
    steps = [step["name"] for step in result.steps]
    assert steps == OLD_STEPS[:4] + ["5 form F-7 chosen"] + OLD_STEPS[5:]
    assert all(step["finished"] is not None for step in result.steps)
    parts = json.loads(result.steps[4]["note"])["parts"]
    assert "".join(part["text"] for part in parts) == paragraph["text"].split(" · ", 1)[1]
    assert store.answer(result.question_id)["text"] == result.text
    assert misses(store) == []
    # Repeat questions still paint, retaining both saved answers and neither calling a model.
    repeated = run(store, explain_call=forbidden)
    assert repeated.times_asked_before == 1 and repeated.text == result.text
    assert model_rows(store, repeated.question_id) == []
    assert store.explanation(repeated.question_id)["provider"] == "form"


def test_form_is_saved_before_answer_is_published_to_polling_clients(setup, monkeypatch):
    store, path = setup
    write_forms(path, fixture_form())
    original = store.save_answer
    inspected = []

    def publish(question_id, *args, **kwargs):
        assert store.answer(question_id) is None
        assert store.explanation(question_id)["status"] == "shown"
        assert store.explanation(question_id)["provider"] == "form"
        inspected.append(question_id)
        return original(question_id, *args, **kwargs)

    monkeypatch.setattr(store, "save_answer", publish)
    result = run(store, explain_call=forbidden)
    assert inspected == [result.question_id]


@pytest.mark.parametrize("status", [None, "proposed", "rejected"])
def test_zero_approved_forms_keeps_the_real_pending_then_shown_path(setup, monkeypatch, status):
    store, path = setup
    if status is not None:
        write_forms(path, fixture_form(status=status))
    entered, release = threading.Event(), threading.Event()
    threads = []
    real_thread = threading.Thread

    def track_thread(*args, **kwargs):
        thread = real_thread(*args, **kwargs)
        threads.append(thread)
        return thread

    monkeypatch.setattr(threading, "Thread", track_thread)
    prompts = []

    def live_paragraph(prompt):
        prompts.append(prompt)
        entered.set()
        assert release.wait(5)
        return ModelReply("fixture-live", "fixture-model", json.dumps({"explanation": "Your FLOW rows describe what carries you."}))

    try:
        result = run(store, explain_call=live_paragraph)
        assert entered.wait(2)
        assert len(threads) == 1
        assert store.explanation(result.question_id)["status"] == "pending"
        assert [s["name"] for s in result.steps] == OLD_STEPS
        assert result.text in prompts[0] and result.question in prompts[0]
    finally:
        release.set()
        for thread in threads:
            thread.join(5)
            assert not thread.is_alive()
    paragraph = store.explanation(result.question_id)
    assert paragraph["status"] == "shown" and paragraph["provider"] == "fixture-live"
    assert paragraph["model"] == "fixture-model" and paragraph["text"] == "Your FLOW rows describe what carries you."
    assert len(model_rows(store, result.question_id)) == 1
    saved_misses = misses(store)
    assert len(saved_misses) == 1 and saved_misses[0][0] == result.question_id
    picture = json.loads(saved_misses[0][1])
    assert picture["text"] == result.text and picture["records"] == result.records and picture["words"] == result.words
    assert saved_misses[0][2] == "no approved forms"


def test_most_conditions_win_then_lowest_numeric_number(setup, monkeypatch):
    store, path = setup
    write_forms(path,
                fixture_form("F-1"),
                fixture_form("F-10", when={**fixture_form()["when"], "word_count": 1}),
                fixture_form("F-2", when={**fixture_form()["when"], "record_count": 3}),
                fixture_form("F-3", when={**fixture_form()["when"], "record_count": 4, "word_count": 1}),
                fixture_form("F-4", status="proposed", when={**fixture_form()["when"], "record_count": 3, "word_count": 1}))
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store)
    assert store.explanation(result.question_id)["model"] == "F-2"


def test_unsafe_filling_is_skipped_for_the_next_safe_form(setup, monkeypatch):
    store, path = setup
    write_forms(path, fixture_form("F-1", sentence="prefix{word}."), fixture_form("F-7"))
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store)
    assert store.explanation(result.question_id)["model"] == "F-7"


@pytest.mark.parametrize("failure", ["missing", "invalid", "no_match", "unsafe"])
def test_unavailable_or_nonmatching_forms_record_miss_and_use_original_start(setup, monkeypatch, failure):
    store, path = setup
    if failure == "missing":
        path.unlink()
    elif failure == "invalid":
        path.write_text("not TOML")
    elif failure == "unsafe":
        write_forms(path, fixture_form(sentence="prefix{word}."))
    else:
        write_forms(path, fixture_form(when={**fixture_form()["when"], "record_count": 4}))
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    result = run(store, explain_call=forbidden)
    assert calls == [(result.question_id, result.question, result.text, ["FLOW"], store, forbidden)]
    assert model_rows(store, result.question_id) == []
    saved = misses(store)
    assert len(saved) == 1
    assert ("forms unavailable" in saved[0][2]) if failure in ("missing", "invalid") else bool(saved[0][2])


def test_counts_use_only_painted_rows_not_hidden_links(setup, monkeypatch):
    store, path = setup
    hidden = "conn-obs-fable5-2026-07-10-belief-work-distraction-rule"
    store.add_link("FLOW", hidden, "hidden", "", "links:FLOW", "fixture", "fixture", kind="depends on")
    store.thumb("FLOW", hidden, up=False)
    write_forms(path, fixture_form(when={**fixture_form()["when"], "record_count": 3}))
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store)
    assert len(store.links_for("FLOW")) == 4 and len(result.records) == 3
    assert "depends on 3" in store.explanation(result.question_id)["text"]


def test_existing_explanation_opt_out_still_means_no_paragraph(setup, monkeypatch):
    store, path = setup
    write_forms(path, fixture_form())
    monkeypatch.setattr(forms, "pick", forbidden)
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store, explain_call=False)
    assert store.explanation(result.question_id) is None and misses(store) == []
    assert [s["name"] for s in result.steps] == OLD_STEPS


@pytest.mark.parametrize("value", [None, "", "0", "false", "off"])
def test_forms_only_is_off_by_default_and_for_false_values(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("NUCLEUS_FORMS_ONLY", raising=False)
    else:
        monkeypatch.setenv("NUCLEUS_FORMS_ONLY", value)
    assert forms.forms_only() is False


def test_forms_only_switch_is_tested_in_isolation_and_never_starts_a_live_paragraph(setup, monkeypatch):
    store, path = setup
    monkeypatch.setenv("NUCLEUS_FORMS_ONLY", "1")  # restored by pytest; no service/config change
    monkeypatch.setattr(explain, "start", forbidden)
    result = run(store)
    assert model_rows(store, result.question_id) == [] and store.explanation(result.question_id) is None
    assert len(misses(store)) == 1
    write_forms(path, fixture_form())
    fitted = run(store)
    assert store.explanation(fitted.question_id)["provider"] == "form"
    assert model_rows(store, fitted.question_id) == []


@pytest.mark.parametrize("forms_only", [False, True])
def test_nonpainted_answer_stays_on_existing_model_path(setup, monkeypatch, forms_only):
    store, path = setup
    write_forms(path, fixture_form())
    monkeypatch.setattr(ask.links_module, "paint", lambda *args: None)
    monkeypatch.setattr(forms, "pick", forbidden)
    monkeypatch.setenv("NUCLEUS_FORMS_ONLY", "1" if forms_only else "0")
    calls = []
    monkeypatch.setattr(explain, "start", lambda *args: calls.append(args))
    payload = {"answer": "aligned", "words": [{"word": "FLOW", "why": "Your word names the state."}], "records": [], "possibility": []}
    result = ask.ask("What is FLOW?", store=store, brief=reading,
                     model_call=lambda p: ModelReply("fixture", "fixture", json.dumps(payload)))
    assert result.status == "answered" and len(model_rows(store, result.question_id)) == 1
    assert len(calls) == (0 if forms_only else 1) and misses(store) == []


def test_misses_are_append_only_and_survive_reopening(setup):
    store, _ = setup
    picture = {"answer": "aligned", "text": "exact  spacing", "words": [{"word": "FLOW"}], "records": []}
    first = store.save_form_miss("q1", picture, "no form fits")
    second = store.save_form_miss("q1", picture, "no approved forms")
    assert first != second
    reopened = Store(store.path)
    try:
        saved = misses(reopened)
        assert len(saved) == 2 and all(json.loads(row[1]) == picture for row in saved)
        assert reopened.connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        reopened.connection.close()
