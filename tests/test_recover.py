import json
from datetime import datetime

from nucleus.recover import recover
from nucleus.store import Store


def turn(request_id, words, status="answered", final_answer="aligned and why\n\nFLOW — “x”\nyou said FLOW",
         created="2026-09-13T05:44:27.411586+00:00", error=None):
    return {"request_id": request_id, "conversation_id": "c", "turn_index": 1, "raw_words": words, "source": "iPhone",
            "created_at": created, "status": status, "attachments": [], "error_message": error,
            "response": None if status != "answered" else {"final_answer": final_answer, "completed_at": created,
                                                             "route": "cloud_worker_without_personal_model"}}


def test_recover_keeps_his_words_time_source_and_the_whole_turn(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    turns = [turn("A", "What is FLOW?"),
             turn("B", "I know the UI is wrong but not why.", status="saved without answer", created="2026-07-18T19:19:00+00:00"),
             turn("C", "What happens when I feel confident?", status="Cowboy AI stopped because x.", error="Cowboy AI stopped because x.")]
    assert recover(store, turns) == (3, 0)
    assert recover(store, turns) == (0, 3)                      # running it again adds nothing
    q = store.question("A")
    assert q["question"] == "What is FLOW?" and q["surface"] == "cowboyai-iphone"
    assert q["asked_at"] == datetime.fromisoformat("2026-09-13T05:44:27.411586+00:00").timestamp()
    a = store.answer("A")
    assert a["status"] == "answered" and a["answer"] == "aligned" and a["text"].startswith("aligned and why")
    assert json.loads(a["reply_json"])["source"] == "iPhone"      # the complete CowboyAI turn, kept
    assert store.answer("B")["status"] == "saved" and store.answer("B")["text"] == ""
    c = store.answer("C")
    assert c["status"] == "stopped" and c["gate_reason"] == "Cowboy AI stopped because x."
    assert store.rows_for_answer(a["reply_json"]) == []


def test_recent_shows_each_of_his_questions_once_from_his_surfaces_only(tmp_path):
    store = Store(tmp_path / "s.sqlite3")
    older = store.new_question("What is FLOW?", "web")
    store.save_answer(older, "answered", "aligned", "aligned and why", None, True, None)
    newer = store.new_question("what is flow?", "web")
    store.save_answer(newer, "answered", "aligned", "aligned and why", None, True, None)
    machine = store.new_question("What is the capital of France?", "cli")
    store.save_answer(machine, "stopped", None, "stopped", None, False, "no")
    recover(store, [turn("A", "What does DONE mean to me?")])
    ids = [r["id"] for r in store.recent()]
    assert ids == [newer, "A"]                                   # once each, newest first, no cli asks
    assert store.recent(limit=1) == store.recent()[:1]
