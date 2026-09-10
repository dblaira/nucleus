"""One SQLite file. Everything is saved. Nothing is ever deleted."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from . import STORE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, question TEXT NOT NULL, asked_at REAL NOT NULL, surface TEXT
);
CREATE TABLE IF NOT EXISTS steps (
  question_id TEXT NOT NULL, name TEXT NOT NULL, started REAL NOT NULL, finished REAL, note TEXT
);
CREATE TABLE IF NOT EXISTS model_calls (
  question_id TEXT NOT NULL, provider TEXT, model TEXT, prompt TEXT NOT NULL, reply TEXT,
  started REAL NOT NULL, finished REAL, ok INTEGER, error TEXT
);
CREATE TABLE IF NOT EXISTS answers (
  question_id TEXT PRIMARY KEY, status TEXT NOT NULL, answer TEXT, text TEXT, reply_json TEXT,
  gate_ok INTEGER, gate_reason TEXT, finished REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY, question_id TEXT NOT NULL, links TEXT NOT NULL, proposed TEXT NOT NULL,
  would_show TEXT NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS phrase_hits (
  question_id TEXT NOT NULL, phrase TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
  text TEXT NOT NULL, strength TEXT, position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS grades (
  run_id TEXT NOT NULL, question_id TEXT, question TEXT NOT NULL, expected TEXT, got TEXT,
  status TEXT, gate_ok INTEGER, seconds REAL, at REAL NOT NULL
);
"""


class Store:
    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def new_question(self, question: str, surface: str) -> str:
        question_id = str(uuid.uuid4())
        self.connection.execute(
            "INSERT INTO questions (id, question, asked_at, surface) VALUES (?, ?, ?, ?)",
            (question_id, question, time.time(), surface),
        )
        self.connection.commit()
        return question_id

    def start_step(self, question_id: str, name: str) -> float:
        started = time.time()
        self.connection.execute(
            "INSERT INTO steps (question_id, name, started) VALUES (?, ?, ?)", (question_id, name, started)
        )
        self.connection.commit()
        return started

    def finish_step(self, question_id: str, name: str, note: str | None = None) -> float:
        finished = time.time()
        self.connection.execute(
            "UPDATE steps SET finished = ?, note = ? WHERE question_id = ? AND name = ? AND finished IS NULL",
            (finished, note, question_id, name),
        )
        self.connection.commit()
        return finished

    def steps(self, question_id: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT name, started, finished, note FROM steps WHERE question_id = ? ORDER BY started", (question_id,)
        ).fetchall()
        return [{"name": n, "started": s, "finished": f, "note": note} for n, s, f, note in rows]

    def save_model_call(self, question_id: str, provider: str, model: str, prompt: str, started: float,
                        reply: str | None, ok: bool, error: str | None) -> None:
        self.connection.execute(
            "INSERT INTO model_calls (question_id, provider, model, prompt, reply, started, finished, ok, error)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (question_id, provider, model, prompt, reply, started, time.time(), int(ok), error),
        )
        self.connection.commit()

    def save_answer(self, question_id: str, status: str, answer: str | None, text: str, reply_json: str | None,
                    gate_ok: bool | None, gate_reason: str | None) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO answers (question_id, status, answer, text, reply_json, gate_ok, gate_reason, finished)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (question_id, status, answer, text, reply_json, None if gate_ok is None else int(gate_ok), gate_reason, time.time()),
        )
        self.connection.commit()

    def save_candidates(self, question_id: str, possibility: list[dict]) -> None:
        for entry in possibility:
            self.connection.execute(
                "INSERT INTO candidates (id, question_id, links, proposed, would_show, created) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), question_id, json.dumps(entry["links"], ensure_ascii=False), entry["proposed"],
                 entry["would_show"], time.time()),
            )
        self.connection.commit()

    def save_phrase_hits(self, question_id: str, hits: list) -> None:
        for position, hit in enumerate(hits):
            self.connection.execute(
                "INSERT INTO phrase_hits (question_id, phrase, kind, name, text, strength, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (question_id, hit.phrase, hit.kind, hit.name, hit.text, hit.strength, position),
            )
        self.connection.commit()

    def phrase_hits(self, question_id: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT phrase, kind, name, text, strength FROM phrase_hits WHERE question_id = ? ORDER BY position", (question_id,)
        ).fetchall()
        return [{"phrase": p, "kind": k, "name": n, "text": t, "strength": s} for p, k, n, t, s in rows]

    def answer(self, question_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT status, answer, text, reply_json, gate_ok, gate_reason, finished FROM answers WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        if row is None:
            return None
        status, answer, text, reply_json, gate_ok, gate_reason, finished = row
        return {"status": status, "answer": answer, "text": text, "reply_json": reply_json,
                "gate_ok": gate_ok, "gate_reason": gate_reason, "finished": finished}

    def question(self, question_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT id, question, asked_at, surface FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            return None
        return {"id": row[0], "question": row[1], "asked_at": row[2], "surface": row[3]}

    def save_grade(self, run_id: str, question_id: str | None, question: str, expected: str | None, got: str | None,
                   status: str, gate_ok: bool | None, seconds: float) -> None:
        self.connection.execute(
            "INSERT INTO grades (run_id, question_id, question, expected, got, status, gate_ok, seconds, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, question_id, question, expected, got, status, None if gate_ok is None else int(gate_ok), seconds, time.time()),
        )
        self.connection.commit()
