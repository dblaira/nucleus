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
