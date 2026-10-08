"""His SAVY themes in Cowboy AI. Adam, 2026-10-07: "All the themes that I have on the SAVY app, I want added on
cowboy AI. That way there can be choices of the questions that I have." The engine keeps the form he picked and
what he filled in, exactly as sent, beside the question."""

from pathlib import Path

from nucleus.store import Store


def test_the_theme_he_picked_is_kept_with_the_question(tmp_path: Path):
    store = Store(tmp_path / "t.sqlite3")
    theme = {"id": "story-arc", "name": "Story Arc", "question": "",
             "fields": [{"prompt": "Where does it start?", "symbol": "location", "answer": "At the gym."}]}
    qid = store.new_question("Where does it start?\nAt the gym.", "web", theme=theme)
    assert store.question(qid)["theme"] == theme
    plain = store.new_question("What is FLOW?", "web")
    assert store.question(plain)["theme"] is None


def test_a_blank_box_is_filled_only_with_his_own_words(tmp_path: Path):
    from nucleus import boxes
    from nucleus.dictionary import Meaning

    class Record:
        label = "Done is a confident, clear internal framework of what matters vs what doesn't"
        note = ""
        block = ""
        leaf = "r-done"

    class G:
        def find(self, key): return Record() if key == "r-done" else None
        def is_accepted(self, record): return True

    meanings = [Meaning("FLOW", "6, 12, 15, 23", 1, "FLOW is the act of using all of my awareness and energy into one activity.")]
    theme = {"id": "how-to", "name": "How-To", "question": "I want a plan.",
             "fields": [{"prompt": "What's the outcome?", "symbol": "flag", "answer": ""},
                        {"prompt": "What are the steps?", "symbol": "list", "answer": "Open the app."}]}
    payload = {"boxes": [
        {"prompt": "What's the outcome?", "brings_in": "r-done", "quote": "a confident, clear internal framework of what matters",
         "answer": "Your record names the outcome: a clear frame of what matters."},
        {"prompt": "What are the steps?", "brings_in": "FLOW", "quote": "one activity", "answer": "Already filled by him; ignored."},
        {"prompt": "What's the outcome?", "brings_in": "FLOW", "quote": "words he never wrote", "answer": "Dropped."}]}
    fills, reason = boxes.check(payload, theme, G(), meanings)
    assert reason is None and list(fills) == ["What's the outcome?"]
    assert fills["What's the outcome?"]["brings_in"] == "r-done"
    advice = {"boxes": [{"prompt": "What's the outcome?", "brings_in": "r-done", "quote": "what matters", "answer": "You should decide what matters."}]}
    assert boxes.check(advice, theme, G(), meanings) == ({}, "every box failed the checks")


def test_the_night_run_fills_only_forms_with_a_blank_box_and_never_touches_his_answers(tmp_path: Path, monkeypatch):
    from nucleus import boxes
    store = Store(tmp_path / "t.sqlite3")
    blank = {"id": "how-to", "name": "How-To", "question": "I want a plan.",
             "fields": [{"prompt": "What's the outcome?", "symbol": "flag", "answer": ""},
                        {"prompt": "What are the steps?", "symbol": "list", "answer": "Open the app."}]}
    full = {"id": "story-arc", "name": "Story Arc", "question": "", "fields": [{"prompt": "Where does it start?", "symbol": "location", "answer": "At the gym."}]}
    a = store.new_question("I want a plan.", "web", theme=blank)
    store.new_question("Where does it start?\nAt the gym.", "web", theme=full)
    store.new_question("What is FLOW?", "web")
    calls = []

    class Reply:
        provider, model = "test", "test"
        text = '{"boxes": [{"prompt": "What\'s the outcome?", "brings_in": "FLOW", "quote": "all of my awareness", "answer": "The outcome is all of your awareness on one thing."}]}'

    def fake(prompt):
        calls.append(prompt)
        return Reply()

    class Record:
        label = "x"; note = ""; block = ""; leaf = "x"

    class G:
        records = {}
        def find(self, key): return None
        def is_accepted(self, record): return True

    from nucleus.dictionary import Meaning
    meanings = [Meaning("FLOW", "6, 12, 15, 23", 1, "FLOW is the act of using all of my awareness and energy into one activity.")]
    monkeypatch.setattr(boxes, "load_graph", lambda *a, **k: G())
    monkeypatch.setattr(boxes.dictionary_module, "load_meanings", lambda *a, **k: meanings)
    done = boxes.run(store, model_call=fake)
    assert [(q, n) for q, n, _ in done] == [("I want a plan.", 1)] and len(calls) == 1      # the full form and the plain question are left alone
    theme = store.question(a)["theme"]
    assert theme["fields"][0]["night"]["brings_in"] == "FLOW" and theme["fields"][1]["answer"] == "Open the app." and "night" not in theme["fields"][1]
    assert boxes.run(store, model_call=fake) == [] and len(calls) == 1                     # filled once; not asked again
