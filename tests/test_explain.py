import json
from pathlib import Path

from nucleus import explain
from nucleus.model import ModelReply
from nucleus.store import Store


def test_the_paragraph_is_checked_by_code():
    assert explain.check("Your rows on FLOW point one way.", ["FLOW"]) is None
    assert explain.check("You should take a break.", ["FLOW"]) == "advice"
    assert explain.check("Nothing here mentions the word.", ["FLOW"]) == "does not speak about his words on the screen"
    assert explain.check("", ["FLOW"]) == "empty"
    assert explain.check("x " * 600, ["FLOW"]) == "longer than a paragraph"


def test_explain_returns_the_paragraph_or_the_reason():
    good = lambda p: ModelReply("fake", "fake", json.dumps({"explanation": "The FLOW rows all describe momentum as the thing that carries you."}))
    text, reason, _ = explain.explain("Why no flow?", "FLOW — “...”", ["FLOW"], good)
    assert text and reason is None
    bad = lambda p: ModelReply("fake", "fake", json.dumps({"explanation": "You should rest, then FLOW returns."}))
    text, reason, _ = explain.explain("Why no flow?", "FLOW — “...”", ["FLOW"], bad)
    assert text is None and reason == "advice"


def test_the_store_keeps_pending_then_shown(tmp_path: Path):
    s = Store(tmp_path / "n.sqlite3")
    s.explanation_pending("q1")
    assert s.explanation("q1")["status"] == "pending"
    s.save_explanation("q1", "The FLOW rows say one thing.", None, "fake", "fake", 0.0)
    assert s.explanation("q1")["status"] == "shown"
    s.thumb_explanation("q1", up=False)
    assert s.explanation("q1")["thumb"] == 0
    s.save_explanation("q2", None, "advice", "fake", "fake", 0.0)
    assert s.explanation("q2")["status"] == "refused"


def test_chapters_are_refused():
    assert explain.check("# The rows say FLOW (Executive Conclusion) - one", ["FLOW"]) == "chapters, not a paragraph"
