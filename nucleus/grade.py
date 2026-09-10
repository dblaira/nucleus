"""The morning grade. Adam's real questions through the whole path, graded, into Apple Notes.

questions.txt: one question per line, then a tab, then the answer Adam expects:
aligned, not_sure, or dont_know. Lines starting with # are skipped.
"""

from __future__ import annotations

import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import ask as ask_module
from .store import Store

QUESTIONS = Path(__file__).resolve().parent.parent / "questions.txt"
NOTE_TITLE = "nucleus grade"


def load_questions(path: Path = QUESTIONS) -> list[tuple[str, str | None]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        question, _, expected = line.partition("\t")
        out.append((question.strip(), expected.strip() or None))
    return out


def run(store: Store | None = None, questions: list[tuple[str, str | None]] | None = None, ask=ask_module.ask) -> list[dict]:
    store = store or Store()
    run_id = str(uuid.uuid4())
    rows = []
    for question, expected in (questions or load_questions()):
        started = time.time()
        result = ask(question, store=store, surface="grade")
        seconds = round(time.time() - started, 1)
        got = result.answer if result.status == "answered" else result.status
        right = expected is None or got == expected
        rows.append({"question": question, "expected": expected, "got": got, "status": result.status,
                     "right": right, "seconds": seconds, "reason": result.reason})
        store.save_grade(run_id, result.question_id, question, expected, got, result.status,
                         None if result.status in ("stopped", "failed") else result.status != "refused", seconds)
    return rows


def report(rows: list[dict]) -> str:
    wrong = [r for r in rows if not r["right"]]
    right = [r for r in rows if r["right"]]
    lines = [time.strftime("%Y-%m-%d %H:%M"), f"{len(wrong)} wrong, {len(right)} right", ""]
    if wrong:
        lines.append("WRONG")
        for r in wrong:
            lines.append(f"{r['question']}")
            lines.append(f"  expected {r['expected']}, got {r['got']}, {r['seconds']} s" + (f", {r['reason']}" if r['reason'] else ""))
        lines.append("")
    if right:
        lines.append("RIGHT")
        for r in right:
            lines.append(f"{r['question']}")
            lines.append(f"  {r['got']}, {r['seconds']} s")
    return "\n".join(lines)


def write_note(text: str, title: str = NOTE_TITLE) -> None:
    """Create a note in Apple Notes. Notes syncs it to his phone."""
    body = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "<br>")
    script = f'''tell application "Notes"
  make new note at folder "Notes" with properties {{name:"{title}", body:"<div>{body}</div>"}}
end tell'''
    subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True, timeout=60)


def main(argv: list[str]) -> int:
    rows = run()
    text = report(rows)
    print(text)
    if "--no-note" not in argv:
        write_note(text)
        print("\nwritten to Apple Notes")
    return 0 if all(r["right"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
