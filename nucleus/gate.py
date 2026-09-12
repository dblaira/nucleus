"""The gate. Code decides whether a model reply is one of Adam's three answers.

Adam's three answers, in his words (2026-09-10):
  1. "aligned and why"
  2. "Not sure.  some correlation, but not enough for causation, more data may help."
  3. "I don't know" there is nothing in your records that points to a conclusion.

The model returns JSON only. The gate checks it. Code composes the text Adam sees.
The model never writes a paragraph. Its only free text is one sentence per entry,
plus the possibility box under "Not sure", which is the one place it may propose.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .dictionary import Meaning, meanings_for
from .graph import Graph, Record

ANSWERS = ("aligned", "not_sure", "dont_know")

FIRST_LINE = {
    "aligned": "aligned and why",
    "not_sure": "Not sure.  some correlation, but not enough for causation, more data may help.",
    "dont_know": "I don't know. There is nothing in your records that points to a conclusion.",
}

POSSIBILITY_TITLE = "possibility"

_SENTENCE_BREAK = re.compile(r"[.!?]\s+[A-Z“\"(]")
MAX_SENTENCE_CHARS = 320


@dataclass
class Verdict:
    ok: bool
    reason: str = ""
    answer: str | None = None
    text: str = ""
    words: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    possibility: list[dict] = field(default_factory=list)


class Refused(ValueError):
    pass


def one_sentence(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Refused(f"{what} is empty.")
    text = value.strip()
    if "\n" in text:
        raise Refused(f"{what} has a line break; it must be one sentence.")
    if len(text) > MAX_SENTENCE_CHARS:
        raise Refused(f"{what} is longer than one sentence.")
    if _SENTENCE_BREAK.search(text):
        raise Refused(f"{what} is more than one sentence.")
    return text


def _require_list(value: object, what: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise Refused(f"{what} is not a list.")
    return value


def check(reply: object, graph: Graph, meanings: list[Meaning]) -> Verdict:
    try:
        return _check(reply, graph, meanings)
    except Refused as error:
        return Verdict(ok=False, reason=str(error))


def _check(reply: object, graph: Graph, meanings: list[Meaning]) -> Verdict:
    if isinstance(reply, str):
        try:
            reply = json.loads(reply)
        except json.JSONDecodeError as error:
            raise Refused("The reply is not JSON.") from error
    if not isinstance(reply, dict):
        raise Refused("The reply is not an object.")
    allowed_keys = {"answer", "words", "records", "possibility"}
    extra = set(reply) - allowed_keys
    if extra:
        raise Refused(f"The reply has keys that are not in the contract: {sorted(extra)}.")

    answer = reply.get("answer")
    if answer not in ANSWERS:
        raise Refused("The answer is not one of Adam's three answers: aligned, not_sure, or dont_know.")

    words_in = _require_list(reply.get("words"), "words")
    records_in = _require_list(reply.get("records"), "records")
    possibility_in = _require_list(reply.get("possibility"), "possibility")

    known = {m.word for m in meanings}
    words: list[dict] = []
    seen_words: set[str] = set()
    for item in words_in:
        if not isinstance(item, dict):
            raise Refused("A words entry is not an object.")
        word = item.get("word")
        if not isinstance(word, str) or word not in known:
            raise Refused(f"The word {word!r} is not in Adam's dictionary.")
        if word in seen_words:
            raise Refused(f"The word {word} is listed twice.")
        seen_words.add(word)
        why = one_sentence(item.get("why"), f"why for {word}")
        words.append({"word": word, "why": why, "meanings": [m.text for m in meanings_for(meanings, word)]})

    records: list[dict] = []
    seen_records: set[str] = set()
    for item in records_in:
        if not isinstance(item, dict):
            raise Refused("A records entry is not an object.")
        record_id = item.get("id")
        record = graph.find(record_id) if isinstance(record_id, str) else None
        if record is None:
            raise Refused(f"The record {record_id!r} does not exist in the accepted graph.")
        if record.uri in seen_records:
            raise Refused(f"The record {record.leaf} is cited twice.")
        seen_records.add(record.uri)
        quote = item.get("quote")
        if not isinstance(quote, str) or not graph.quote_is_in(record, quote):
            raise Refused(f"The quote for {record.leaf} is not in that record, character for character.")
        if not graph.is_accepted(record):
            raise Refused(f"The record {record.leaf} has no accepted decision in the ledger.")
        why = one_sentence(item.get("why"), f"why for {record.leaf}")
        records.append({
            "id": record.uri,
            "leaf": record.leaf,
            "quote": quote,
            "why": why,
            "strength": record.strength,
            "accepted_at": record.accepted_at,
            "connection_type": record.connection_type,
        })

    if answer == "dont_know":
        if words or records:
            raise Refused("An I-don't-know answer cannot cite words or records.")
        if possibility_in:
            raise Refused("Possibility is only allowed under not_sure.")
    else:
        if not words and not records:
            raise Refused(f"A {answer} answer must match at least one word or record.")
        if answer == "aligned" and possibility_in:
            raise Refused("Possibility is only allowed under not_sure.")

    possibility: list[dict] = []
    for item in possibility_in:
        if not isinstance(item, dict):
            raise Refused("A possibility entry is not an object.")
        links = item.get("links")
        if not isinstance(links, list) or len(links) != 2:
            raise Refused("A possibility entry must link exactly two things.")
        shown: list[str] = []
        for link in links:
            if not isinstance(link, str):
                raise Refused("A possibility link is not text.")
            if link in known:
                shown.append(link)
                continue
            record = graph.find(link)
            if record is None:
                raise Refused(f"The possibility link {link!r} is neither a record nor one of Adam's words.")
            shown.append(unescape_label(record.label))
        proposed = one_sentence(item.get("proposed"), "a possibility's proposed relationship")
        would_show = one_sentence(item.get("would_show"), "a possibility's would_show")
        possibility.append({"links": links, "shown": shown, "proposed": proposed, "would_show": would_show})

    text = compose(answer, words, records, possibility)
    return Verdict(ok=True, answer=answer, text=text, words=words, records=records, possibility=possibility)


def unescape_label(label: str) -> str:
    return label.replace('\\"', '"').replace("\\\\", "\\")


def compose(answer: str, words: list[dict], records: list[dict], possibility: list[dict]) -> str:
    """The text Adam sees. First line fixed. Then his words, then his records, each with one why."""
    lines = [FIRST_LINE[answer]]
    if answer == "dont_know":
        return lines[0]
    for entry in words:
        lines.append("")
        for meaning in entry["meanings"]:
            lines.append(f"{entry['word']} — “{meaning}”")
        lines.append(entry["why"])
    for entry in records:
        lines.append("")
        stamp = " · ".join(part for part in (entry["strength"], entry["accepted_at"][:10]) if part)
        quote = f"“{unescape_label(entry['quote'])}”"
        if entry.get("kind") and entry.get("link_word"):
            quote = f"{entry['link_word']} {entry['kind']} {quote}"      # Adam: "Thing A → exact relationship → Thing B"
        lines.append(f"{stamp} — {quote}" if stamp else quote)
        if entry["why"]:
            lines.append(entry["why"])
    if answer == "not_sure" and possibility:
        lines.append("")
        lines.append(POSSIBILITY_TITLE)
        for entry in possibility:
            lines.append("")
            lines.append(f"{entry['shown'][0]} ↔ {entry['shown'][1]}")
            lines.append(entry["proposed"])
            lines.append(f"would show: {entry['would_show']}")
    return "\n".join(lines)
