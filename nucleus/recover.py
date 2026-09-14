"""Bring the questions Adam asked in the CowboyAI iPhone app into nucleus, each with its saved answer.

Adam, 2026-09-14: "recover all of the questions that I had asked before and add them back to the app"

The CowboyAI service on 8765 keeps one row per exact iPhone question (GET /v1/hub/answers: the answered attempt
wins, else the newest saved attempt). Each becomes a nucleus question with surface "cowboyai-iphone", its own
request id, its original time, and the complete CowboyAI turn kept in reply_json. Nothing is rewritten; running
it again adds nothing that is already there.

    python -m nucleus.recover                # from http://127.0.0.1:8765
    python -m nucleus.recover answers.json   # from a saved copy of /v1/hub/answers
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from .gate import FIRST_LINE
from .store import Store

SURFACE = "cowboyai-iphone"
COWBOYAI = "http://127.0.0.1:8765/v1/hub/answers"


def _epoch(stamp: str | None) -> float | None:
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def _answer_word(text: str) -> str | None:
    first = text.split("\n", 1)[0].strip()
    for word, line in FIRST_LINE.items():
        if first == line.strip():
            return word
    return None


def recover_turn(store: Store, turn: dict) -> bool:
    """One CowboyAI iPhone turn into the store. Returns False when it is already there."""
    question_id = str(turn["request_id"])
    if store.question(question_id) is not None:
        return False
    asked_at = _epoch(turn.get("created_at"))
    store.connection.execute(
        "INSERT INTO questions (id, question, asked_at, surface) VALUES (?, ?, ?, ?)",
        (question_id, str(turn.get("raw_words") or ""), asked_at, SURFACE),
    )
    response = turn.get("response") or {}
    text = str(response.get("final_answer") or "")
    status = str(turn.get("status") or "")
    if status == "answered":
        stored_status, reason = "answered", None
    elif status == "saved without answer":
        stored_status, reason = "saved", None
    else:
        stored_status, reason = "stopped", turn.get("error_message") or status
    finished = _epoch(response.get("completed_at")) or asked_at
    store.connection.execute(
        "INSERT INTO answers (question_id, status, answer, text, reply_json, gate_ok, gate_reason, finished)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (question_id, stored_status, _answer_word(text) if stored_status == "answered" else None,
         text if stored_status != "stopped" else str(reason), json.dumps(turn, ensure_ascii=False), None, reason, finished),
    )
    store.connection.commit()
    return True


def recover(store: Store, turns: list[dict]) -> tuple[int, int]:
    """(brought in, already there)."""
    added = 0
    for turn in turns:
        if recover_turn(store, turn):
            added += 1
    return added, len(turns) - added


def load_turns(source: str | None) -> list[dict]:
    if source:
        return json.loads(Path(source).read_text())
    with urllib.request.urlopen(COWBOYAI, timeout=30) as reply:
        return json.load(reply)


def main(argv: list[str]) -> int:
    turns = load_turns(argv[0] if argv else None)
    added, there = recover(Store(), turns)
    print(f"{len(turns)} CowboyAI iPhone questions: {added} brought in, {there} already there")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
