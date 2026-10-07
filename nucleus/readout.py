"""The middle answer's feedback as a readout: a question and its answer, one row each, the way his Decide card in SAVY
lays out a theme. Adam, 2026-10-07: "I am think a feedback readout like I have built in the Themes section of SAVY app
will work." "The only difference is that the question and the answer would be filled in by the feedback." "The word
"Your" and "You" will be removed."

The rows are drawn from the parts the paragraph was told from. Each answer is his exact words wherever the part holds
them; each heading is the word itself. Adam, 2026-10-07, on "What is doctor?": "This should read, "Reasons"." and
"They don't all need to be questions and answers. We will work on the forms. But this is the path." The icons are taken from SAVY's own theme catalog.
The last row is his own question of 2026-09-09, asked by the middle answer.
"""

from __future__ import annotations

import re

from .gate import MIDDLE_ASKS

BOOK = "book"                                   # SAVY: "What does each term mean in plain language?"
LINK = "link"                                   # SAVY: "How do the principles work together?"
EVIDENCE = "doc.text.magnifyingglass"           # SAVY: "What evidence establishes the difference?"
NOT_HELD = "nosign"                             # SAVY: "Where does each principle stop applying?"
FOLLOW_UP = "arrow.turn.down.right"             # SAVY: "What follow-up question naturally comes after each answer?"

_BOTH = re.compile(r"This accepted record of yours sits in both (.+):$")
_HOLDS = re.compile(r"Your graph holds (.+?)\.(?: (None sits in both\.|None says .+?\.))?(?: (Closest to what you said|The strongest stated):)?$")
_MISSING = "Nothing in your dictionary or your records says "


def _unquote(text: str) -> str:
    return text.strip().strip("“”\"")


def _row(symbol: str, question: str, answer: str) -> dict:
    return {"symbol": symbol, "question": question, "answer": answer.strip()}


def rows(parts: list[dict] | None) -> list[dict]:
    """The readout for one paragraph, in the order it was told. Empty when there are no parts."""
    out: list[dict] = []
    waiting: list[str] = []                     # records told before the line that introduces them
    for part in parts or []:
        source, text, exact, word = part.get("source"), part.get("text", ""), part.get("exact", ""), part.get("word", "")
        if source == "domain":
            said, domain = part.get("said") or word, word.capitalize()
            answer = (_unquote(part["english"]) + "\n" if part.get("english") else "") + f"{domain}: {exact}"
            if _MISSING in text:
                answer += f"\nNot in the dictionary or the records."
            out.append(_row(BOOK, said[:1].upper() + said[1:], answer))
        elif source in ("meaning", "walk"):
            out.append(_row(BOOK, word, exact))
        elif source == "pattern" and out:
            out[-1]["answer"] += "\n" + exact
        elif source == "record":
            waiting.append(exact)
        elif source == "weeks":
            if waiting:
                out.append(_row(LINK, word or "Record", "\n\n".join(waiting)))
                waiting = []
            out.append(_row(EVIDENCE, "Tracked weeks", text))
        elif source == "graph":
            both, holds = _BOTH.match(text), _HOLDS.match(text)
            if both and waiting:
                out.append(_row(LINK, both.group(1), "\n\n".join(waiting)))
                waiting = []
            elif holds:
                held = holds.group(1)
                note = holds.group(2) or ""
                if waiting:
                    question = "Closest" if holds.group(3) == "Closest to what you said" else "Strongest"
                    out.append(_row(LINK, question, "\n\n".join(waiting)))
                    waiting = []
                out.append(_row(EVIDENCE, "Graph", (held[0].upper() + held[1:] + ". " + note).strip()))
            else:
                out.append(_row(EVIDENCE, "Graph", text.replace("Your graph holds", "The graph holds")))
        elif source == "missing":
            out.append(_row(NOT_HELD, "Not in the records", _unquote(text[len(_MISSING):].rstrip(".")) if text.startswith(_MISSING) else text))
    if waiting:
        out.append(_row(LINK, "Record", "\n\n".join(waiting)))
    return out


def middle(parts: list[dict] | None) -> list[dict]:
    """The readout under a middle answer: the feedback's rows, then his own question of September 9."""
    return rows(parts) + [_row(FOLLOW_UP, MIDDLE_ASKS, "")]
