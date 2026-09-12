"""One SQLite file. Everything is saved. Nothing is ever deleted."""

from __future__ import annotations

import json
import re
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
CREATE TABLE IF NOT EXISTS links (
  word TEXT NOT NULL, record TEXT NOT NULL, quote TEXT NOT NULL, why TEXT NOT NULL, source TEXT NOT NULL,
  provider TEXT, model TEXT, found_at REAL NOT NULL, thumb INTEGER, kind TEXT, PRIMARY KEY (word, record)
);
CREATE TABLE IF NOT EXISTS searched_words (
  word TEXT PRIMARY KEY, searched_at REAL NOT NULL, records_hash TEXT
);
CREATE TABLE IF NOT EXISTS grades (
  run_id TEXT NOT NULL, question_id TEXT, question TEXT NOT NULL, expected TEXT, got TEXT,
  status TEXT, gate_ok INTEGER, seconds REAL, at REAL NOT NULL
);
"""


def normalize_question(question: str) -> str:
    """The same question, typed again: spaces and capitals do not make it a different question."""
    return re.sub(r"\s+", " ", question).strip().lower()


class Store:
    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self.connection.executescript(SCHEMA)
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(answers)")}
        if "nucleus_hash" not in columns:
            self.connection.execute("ALTER TABLE answers ADD COLUMN nucleus_hash TEXT")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(searched_words)")}
        if columns and "records_hash" not in columns:
            self.connection.execute("ALTER TABLE searched_words ADD COLUMN records_hash TEXT")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(links)")}
        if columns and "kind" not in columns:
            self.connection.execute("ALTER TABLE links ADD COLUMN kind TEXT")
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
                    gate_ok: bool | None, gate_reason: str | None, nucleus_hash: str | None = None) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO answers (question_id, status, answer, text, reply_json, gate_ok, gate_reason, finished, nucleus_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (question_id, status, answer, text, reply_json, None if gate_ok is None else int(gate_ok), gate_reason, time.time(), nucleus_hash),
        )
        self.connection.commit()

    def find_repeat(self, question: str, nucleus_hash: str, before_id: str) -> dict | None:
        """The same question, answered before, against the same records: the saved reply, no model."""
        wanted = normalize_question(question)
        rows = self.connection.execute(
            "SELECT q.id, q.question, a.reply_json, a.finished FROM questions q JOIN answers a ON a.question_id = q.id"
            " WHERE a.status = 'answered' AND a.nucleus_hash = ? AND q.id != ? ORDER BY a.finished DESC",
            (nucleus_hash, before_id),
        ).fetchall()
        for question_id, text, reply_json, finished in rows:
            if normalize_question(text) == wanted and reply_json:
                return {"question_id": question_id, "reply_json": reply_json, "finished": finished}
        return None

    def times_asked(self, question: str, before_id: str) -> int:
        """How many times he asked this same question before this one. Adam: circling."""
        wanted = normalize_question(question)
        asked_at = self.connection.execute("SELECT asked_at FROM questions WHERE id = ?", (before_id,)).fetchone()
        limit = asked_at[0] if asked_at else time.time()
        rows = self.connection.execute("SELECT question FROM questions WHERE id != ? AND asked_at < ?", (before_id, limit)).fetchall()
        return sum(1 for (text,) in rows if normalize_question(text) == wanted)

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

    def recent(self, limit: int = 12) -> list[dict]:
        rows = self.connection.execute(
            "SELECT q.id, q.question, a.status, a.answer, a.finished FROM questions q JOIN answers a ON a.question_id = q.id"
            " ORDER BY a.finished DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"id": i, "question": q, "status": s, "answer": a, "finished": f} for i, q, s, a, f in rows]

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

    def add_link(self, word: str, record: str, quote: str, why: str, source: str, provider: str, model: str,
                 kind: str | None = None) -> bool:
        """A link between one of his words and one of his records. Kept once; a second find does not overwrite."""
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO links (word, record, quote, why, source, provider, model, found_at, thumb, kind)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
            (word, record, quote, why, source, provider, model, time.time(), kind),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def set_kind(self, word: str, record: str, kind: str) -> None:
        """The middle word, from Adam's list only. The caller checks the list."""
        self.connection.execute("UPDATE links SET kind = ? WHERE word = ? AND record = ?", (kind, word, record))
        self.connection.commit()

    def links_for(self, word: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT record, quote, why, source, provider, model, found_at, thumb, kind FROM links WHERE word = ? ORDER BY found_at", (word,)
        ).fetchall()
        return [{"record": r, "quote": q, "why": w, "source": s, "provider": p, "model": m, "found_at": f, "thumb": t, "kind": k}
                for r, q, w, s, p, m, f, t, k in rows]

    def link(self, word: str, record: str) -> dict | None:
        row = self.connection.execute(
            "SELECT quote, why, kind, thumb FROM links WHERE word = ? AND record = ?", (word, record)).fetchone()
        if row is None:
            return None
        return {"word": word, "record": record, "quote": row[0], "why": row[1], "kind": row[2], "thumb": row[3]}

    def rows_for_answer(self, reply_json: str | None) -> list[dict]:
        """One row per record in an answer: the word it is linked from, the middle word, his thumb.
        A record with no saved link yet gets the answer's first word, so a thumb can make the link."""
        if not reply_json:
            return []
        try:
            payload = json.loads(reply_json)
        except json.JSONDecodeError:
            return []
        words = [w.get("word") for w in payload.get("words") or [] if isinstance(w, dict) and isinstance(w.get("word"), str)]
        rows: list[dict] = []
        for item in payload.get("records") or []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            leaf = item["id"].rsplit("/", 1)[-1]
            found = None
            for word in words:
                found = self.link(word, leaf)
                if found:
                    break
            if found:
                rows.append({"word": found["word"], "record": leaf, "quote": item.get("quote", ""), "kind": found["kind"], "thumb": found["thumb"], "saved": True})
            elif words:
                rows.append({"word": words[0], "record": leaf, "quote": item.get("quote", ""), "kind": None, "thumb": None, "saved": False})
        return rows

    def words_with_unkinded_links(self) -> list[str]:
        return [w for (w,) in self.connection.execute(
            "SELECT DISTINCT word FROM links WHERE kind IS NULL AND (thumb IS NULL OR thumb = 1) ORDER BY word")]

    def thumb(self, word: str, record: str, up: bool) -> None:
        self.connection.execute("UPDATE links SET thumb = ? WHERE word = ? AND record = ?", (1 if up else 0, word, record))
        self.connection.commit()

    def mark_word_searched(self, word: str, records_hash: str | None = None) -> None:
        self.connection.execute("INSERT OR REPLACE INTO searched_words (word, searched_at, records_hash) VALUES (?, ?, ?)",
                                (word, time.time(), records_hash))
        self.connection.commit()

    def searched_words(self, records_hash: str | None = None) -> set[str]:
        """Words already searched. With a hash: only those searched against these same records, so a
        change to his records sends every word back through the background pass."""
        if records_hash is None:
            return {w for (w,) in self.connection.execute("SELECT word FROM searched_words")}
        return {w for (w,) in self.connection.execute("SELECT word FROM searched_words WHERE records_hash = ?", (records_hash,))}

    def link_counts(self) -> dict:
        words, links, kinded = self.connection.execute(
            "SELECT COUNT(DISTINCT word), COUNT(*), SUM(CASE WHEN kind IS NOT NULL THEN 1 ELSE 0 END) FROM links").fetchone()
        return {"words": words, "links": links, "kinded": kinded or 0, "searched": len(self.searched_words())}
