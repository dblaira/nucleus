"""The middle answer, as Adam defined it on 2026-10-03: "will be followed by requesting more information, which will
be logged and then analyzed by the LLM during the night run.  During the overnight run, all middle responses will
use AI to generate options ... Three options are a good starting point." """

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from nucleus import NUCLEUS_FILES, dictionary, gate, model, night, serve
from nucleus.graph import load_graph
from nucleus.store import Store

BLIND_SPOT = "conn-obs-mined-2026-07-10-affect-is-his-blind-spot"
EASY = "conn-obs-mined-2026-07-10-easy-innocent-changes-stick"
DOCTOR = "What are reasons I would avoid going to the doctor?"
MIDDLE = gate.FIRST_LINE["not_sure"]


@pytest.fixture(scope="module")
def nucleus():
    return load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"]), dictionary.load_meanings(NUCLEUS_FILES["meanings"])


def three(first="ANTICIPATORY ANXIETY", second="PUSHED", third=BLIND_SPOT, **change):
    options = [{"brings_in": name, "proposed": f"This may be affecting what you asked about in way {i}.",
                "would_show": f"The times it happened and what came before them, set {i}."}
               for i, name in enumerate((first, second, third), 1)]
    options[0].update(change)
    return {"options": options}


def middle_answer(store: Store, surface="web", question=DOCTOR) -> str:
    question_id = store.new_question(question, surface)
    reply = {"answer": "not_sure", "words": [], "records": [{"id": EASY, "quote": "", "why": ""}], "possibility": []}
    store.save_answer(question_id, "answered", "not_sure", MIDDLE + "\n\n0.65 · 2026-07-10 — “Changes only stick”", json.dumps(reply), True, None)
    return question_id


def test_what_he_gives_is_logged_and_the_newest_three_options_are_the_ones_shown(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    question_id = middle_answer(store)
    assert [w["id"] for w in store.middle_answers_waiting(0)] == [question_id]          # no options yet
    store.save_options(question_id, [{"brings_in": "PUSHED", "shown": "one", "proposed": "p", "would_show": "w"}], "fake", "fake")
    assert store.middle_answers_waiting(0) == []                                           # it has its options
    store.save_more_information(question_id, "It is strongest the night before.")
    assert [m["text"] for m in store.more_information(question_id)] == ["It is strongest the night before."]
    assert [w["id"] for w in store.middle_answers_waiting(0)] == [question_id]          # he said more: tonight again
    store.save_options(question_id, [{"brings_in": "COMPLEX", "shown": "two", "proposed": "p", "would_show": "w"}], "fake", "fake")
    assert [o["shown"] for o in store.options(question_id)] == ["two"]                    # the newest night; the older one is kept
    assert store.connection.execute("SELECT COUNT(*) FROM options").fetchone()[0] == 2


def test_the_daily_grade_and_the_command_line_are_not_his_entries(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    middle_answer(store, surface="grade")
    mine = middle_answer(store, surface="web")
    assert [w["id"] for w in store.middle_answers_waiting(0, night.NOT_FROM)] == [mine]


def test_code_accepts_three_options_that_bring_in_his_own_words_and_records(nucleus):
    graph, meanings = nucleus
    options, reason = night.check(three(), graph, meanings, used={EASY})
    assert reason is None and [o["brings_in"] for o in options] == ["ANTICIPATORY ANXIETY", "PUSHED", BLIND_SPOT]
    assert options[0]["shown"] == "Anticipatory anxiety lies."                            # his dictionary, said to him
    assert options[2]["shown"].startswith("Your feelings are the data you are least likely to volunteer")   # his record, said to him


@pytest.mark.parametrize("payload, why", [
    ({"options": three()["options"][:2]}, "not exactly 3 options"),
    (three(first="DOCTOR"), "neither an accepted record nor one of his words"),
    (three(first=EASY), "already in the answer"),
    (three(first="PUSHED"), "brought in twice"),
    (three(proposed="You should book the visit this week."), "advice"),
    (three(proposed="It may be one thing. It may be another."), "more than one sentence"),
    (three(would_show="It would show itself in your notes."), "repeats its own label"),
    ("not json", "not exactly 3 options"),
])
def test_code_refuses_anything_else(nucleus, payload, why):
    graph, meanings = nucleus
    options, reason = night.check(payload, graph, meanings, used={EASY})
    assert options == [] and why in reason


def test_the_night_run_makes_one_call_for_each_middle_answer_and_saves_three(tmp_path: Path, monkeypatch):
    store = Store(tmp_path / "n.sqlite3")
    question_id = middle_answer(store)
    store.save_more_information(question_id, "It is strongest the night before.")
    middle_answer(store, surface="grade")
    seen = []

    def fake(prompt):
        seen.append(prompt)
        return model.ModelReply(provider="fake", model="fake", text=json.dumps(three()))

    monkeypatch.setattr(night, "SINCE", 0)
    done = night.run(store, model_call=fake)
    assert [(q, n, r) for q, n, r in done] == [(DOCTOR, 3, None)] and len(seen) == 1
    # the model was handed his words, his entry, what he was told, and what he logged
    assert "Three\noptions are a good starting point." in seen[0] and DOCTOR in seen[0] and MIDDLE in seen[0]
    assert "- It is strongest the night before." in seen[0] and "ANTICIPATORY ANXIETY = " in seen[0]
    assert len(store.options(question_id)) == 3
    assert night.run(store, model_call=fake) == [] and len(seen) == 1                      # nothing new: no second call


def test_a_refused_reply_saves_nothing_and_is_tried_again_the_next_night(tmp_path: Path, monkeypatch):
    store = Store(tmp_path / "n.sqlite3")
    question_id = middle_answer(store)
    monkeypatch.setattr(night, "SINCE", 0)
    bad = lambda prompt: model.ModelReply(provider="fake", model="fake", text=json.dumps(three(proposed="You should go.")))
    assert night.run(store, model_call=bad) == [(DOCTOR, 0, "advice")]
    assert store.options(question_id) == [] and [w["id"] for w in store.middle_answers_waiting(0)] == [question_id]


def test_the_options_sit_in_the_box_his_app_already_draws():
    option = {"shown": "Anticipatory anxiety lies.", "proposed": "It may build before you act.", "would_show": "When it is strongest."}
    text = night.with_options(MIDDLE + "\n\n0.65 — “a record”", [option, option])
    blocks = text.split("\n\n")
    assert blocks[0] == MIDDLE and blocks[2] == "possibility"
    assert blocks[3] == "Anticipatory anxiety lies.\nIt may build before you act.\nwould show: When it is strongest." and len(blocks) == 5
    assert night.with_options(MIDDLE, []) == MIDDLE


def test_his_app_can_log_more_information_and_reads_the_options_back(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    question_id = middle_answer(store)
    other = store.new_question("What is FLOW?", "web")
    store.save_answer(other, "answered", "aligned", "aligned and why", "{}", True, None)
    handler = type("Handler", (serve.Handler,), {"store": store, "log_message": lambda *a: None})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def post(path, body):
        request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
        return json.load(urllib.request.urlopen(request))

    try:
        logged = post("/more", {"question_id": question_id, "text": "  It is strongest the night before.  "})
        assert [m["text"] for m in logged["more"]] == ["It is strongest the night before."]
        with pytest.raises(urllib.error.HTTPError):                                        # only after the middle answer
            post("/more", {"question_id": other, "text": "more"})
        store.save_options(question_id, [{"brings_in": "PUSHED", "shown": "Pushed is signal to flip the kill switch.",
                                          "proposed": "It may feel pushed.", "would_show": "Whose idea the visit was."}], "fake", "fake")
        seen = json.load(urllib.request.urlopen(f"{base}/ask/{question_id}"))
        assert seen["more"][0]["text"] == "It is strongest the night before." and seen["options"][0]["brings_in"] == "PUSHED"
        assert seen["answer"]["text"].endswith("possibility\n\nPushed is signal to flip the kill switch.\nIt may feel pushed.\nwould show: Whose idea the visit was.")
        assert store.answer(question_id)["text"].endswith("“Changes only stick”")          # the saved answer itself is untouched
    finally:
        server.shutdown()


def test_the_page_asks_for_more_information_under_the_middle_answer_only():
    assert "if (a.answer === 'not_sure'){" in serve.PAGE and "fetch('/more'" in serve.PAGE
