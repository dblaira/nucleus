"""Adam's own form for the middle answer. He wrote it himself on 2026-10-07 in the artifact "The Middle Answer"
(https://claude.ai/artifact/MWFiR9Je6jCibrhcsMNK12) and said: "My middle answer adjustments are completed." Then: "I will
not be there to type this shit every time. What are we going to do to automate this?"

So nothing here is typed by him per question. Every word of the form is his, verbatim (HANDOFF.md, 2026-10-07):
- the Explanation, the Answer, the Belief section and the last question are the same on every middle answer;
- Reasons is filled by code with his own quotes the answer found: "This should contain quotes of mine that have some
  relationship.  Not a bland fucking explanation of nothing.";
- Suggestions is filled by the night run's options (nucleus/night.py), shown once that run has made them.
"""

from __future__ import annotations

import json
import re

from .gate import FIRST_LINE, MIDDLE_ASKS, unescape_label

EXPLANATION = ("Some relationships, but not enough to justify is an opportunity for growth.  This is a chance to "
               "transform potential into a new skill that can compound into something more and more valuable.")
REASONS = "Reasons"
SUGGESTIONS = "Suggestions to move the relationships into a more predictable category"
BELIEF = "Belief"
BELIEF_TEXT = ("Speed. Discernment. Curiosity.  Confidence.  These are important to you.  Do any of them apply more or "
               "less when moving this issue further towards a predictable outcome?")
ASK = MIDDLE_ASKS      # "What would you like AI to revisit? Anything come to mind?"

MOST_QUOTES = 5        # PROPOSAL: the strongest few, so the section stays short. His to change.

_MEANING = re.compile(r"^[A-Z][A-Z0-9 '’&-]* — “(.+)”$")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", unescape_label(text)).strip().strip("“”\"").strip()


def quotes(answer_text: str, reply_json: str | None) -> list[str]:
    """His own words the answer reached: his dictionary meanings first, then his records, each once, as written."""
    found: list[str] = []
    for line in (answer_text or "").split("\n"):
        meaning = _MEANING.match(line.strip())
        if meaning:
            found.append(_plain(meaning.group(1)))
    try:
        records = json.loads(reply_json or "{}").get("records") or []
    except (json.JSONDecodeError, AttributeError):
        records = []
    found += [_plain(record.get("quote") or "") for record in records if isinstance(record, dict)]
    out, seen = [], set()
    for quote in found:
        key = quote.lower()
        if quote and key not in seen:
            seen.add(key)
            out.append(quote)
    return out[:MOST_QUOTES]


def suggestions(options: list[dict]) -> list[str]:
    """The night run's options: the pattern of his it brings in, in his words, then what it may be doing and the
    information that would show it."""
    out = []
    for option in options or []:
        word = option.get("brings_in") or ""
        shown = _plain(option.get("shown") or "")
        head = f"{word} — “{shown}”" if word.isupper() and shown else (f"“{shown}”" if shown else word)
        out.append(head + "\n" + " ".join(part for part in (option.get("proposed"), option.get("would_show")) if part))
    return out


def form(answer_text: str, reply_json: str | None, options: list[dict]) -> dict:
    """Everything his app draws for one middle answer, in the order he laid it out."""
    sections = []
    reasons = quotes(answer_text, reply_json)
    if reasons:
        sections.append({"head": REASONS, "symbol": "book", "lines": [f"“{quote}”" for quote in reasons]})
    suggested = suggestions(options)
    if suggested:
        sections.append({"head": SUGGESTIONS, "symbol": "book", "lines": suggested})
    sections.append({"head": BELIEF, "symbol": "link", "lines": [BELIEF_TEXT]})
    return {"explanation": EXPLANATION, "answer": FIRST_LINE["not_sure"], "sections": sections, "ask": ASK}
