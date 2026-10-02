"""Checked sentences filled only from their literal text and a snapshot of the screen.

The day path selects approved forms without a model. Human decisions live in forms_review.
See docs/forms-slice-1.md for the file format and docs/forms-slice-3c.md for quotes.
"""

from __future__ import annotations

import os
import re
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import explain, forms_style
from .kinds import load_kinds

FORMS_PATH = Path(__file__).resolve().parent.parent / "forms.txt"
FIELDS = {"number", "when", "sentence", "status", "author", "date"}
CONDITIONS = {"answer", "kinds_present", "kinds_absent", "record_count", "word_count", "missing_links"}
BLANKS = {"word", "other_word", "kind", "count", "word_count", "strongest_kind"}
ANSWERS = {"aligned", "not_sure", "dont_know"}
_BLANK = re.compile(r"\{([^{}]*)\}")
_TOKEN = re.compile(r"\w+(?:[’'\-]\w+)*", re.UNICODE)


class Refused(ValueError):
    """A malformed form or unsafe filled sentence. Never return partial text."""


@dataclass(frozen=True)
class Row:
    word: str
    record: str
    kind: str | None
    quote: str | None = None


@dataclass(frozen=True)
class Screen:
    answer: str
    words: tuple[str, ...]
    rows: tuple[Row, ...]
    missing_links: bool = False


@dataclass(frozen=True)
class Part:
    text: str
    source: str


@dataclass(frozen=True)
class Filled:
    number: str
    text: str
    parts: tuple[Part, ...]


def _parts(sentence: str) -> list[tuple[str, str | None]]:
    """No formatting language, attribute access, conversions, or recursive expansion."""
    parts = []
    position = 0
    for match in _BLANK.finditer(sentence):
        literal, name = sentence[position:match.start()], match[1]
        if "{" in literal or "}" in literal or (name not in BLANKS and not name.startswith("quote:")):
            raise Refused("unknown or malformed blank")
        parts.append((literal, name))
        position = match.end()
    tail = sentence[position:]
    if "{" in tail or "}" in tail:
        raise Refused("unknown or malformed blank")
    parts.append((tail, None))
    return parts


def _paragraph_reason(text: str, words: list[str]) -> str | None:
    reason = explain.check(text, words)
    if reason:
        return reason
    reason = forms_style.check(text)
    if reason:
        return reason
    if "\n" in text or "\r" in text:
        return "not one paragraph"
    # Conservative: punctuation can overcount abbreviations, never excuse a fifth sentence.
    sentences = [piece for piece in re.split(r"[.!?]+[\"'”’)]*", text) if piece.strip()]
    if len(sentences) > 4:
        return "more than 4 sentences"
    return None


def _valid_count(value: object) -> bool:
    if type(value) is int:
        return value >= 0
    if not isinstance(value, dict) or not value or set(value) - {"min", "max"}:
        return False
    if any(type(n) is not int or n < 0 for n in value.values()):
        return False
    return value.get("min", 0) <= value.get("max", float("inf"))


def check(form: object, *, kinds: list[str] | None = None) -> str | None:
    """Return a refusal reason, or None. Validation never confers approval."""
    if not isinstance(form, dict) or set(form) != FIELDS:
        return "unknown or missing form fields"
    if not isinstance(form["number"], str) or not re.fullmatch(r"F-[1-9][0-9]*", form["number"]):
        return "invalid form number"
    if form["status"] not in ("proposed", "approved", "rejected"):
        return "unknown status"
    if not isinstance(form["author"], str) or not form["author"].strip():
        return "missing author"
    try:
        if not isinstance(form["date"], str) or date.fromisoformat(form["date"]).isoformat() != form["date"]:
            return "invalid date"
    except ValueError:
        return "invalid date"
    when = form["when"]
    if not isinstance(when, dict) or not when or set(when) - CONDITIONS:
        return "unknown or missing conditions"
    kinds = load_kinds() if kinds is None else kinds
    for name, value in when.items():
        if name == "answer" and (not isinstance(value, str) or value not in ANSWERS):
            return "unknown answer label"
        if name in ("kinds_present", "kinds_absent"):
            if not isinstance(value, list) or not value or any(not isinstance(k, str) or k not in kinds for k in value):
                return "unknown middle word"
            if len(set(value)) != len(value):
                return "repeated middle word"
        if name in ("record_count", "word_count") and not _valid_count(value):
            return "invalid count condition"
        if name == "missing_links" and type(value) is not bool:
            return "missing_links must be boolean"
    if set(when.get("kinds_present", [])) & set(when.get("kinds_absent", [])):
        return "middle word both present and absent"
    sentence = form["sentence"]
    if not isinstance(sentence, str):
        return "empty"
    try:
        parts = _parts(sentence)
    except Refused as error:
        return str(error)
    blanks = {blank for _, blank in parts if blank is not None}
    for blank in blanks:
        if blank.startswith("quote:"):
            kind = blank[len("quote:"):]
            if kind not in kinds:
                return "unknown middle word in quote blank"
            if kind not in when.get("kinds_present", []):
                return "quote blank needs its named middle word in kinds_present"
    if blanks & {"kind", "count"} and len(when.get("kinds_present", [])) != 1:
        return "kind and count need exactly one middle word to fire on"
    return _paragraph_reason(sentence, [])


def load(path: Path = FORMS_PATH, *, kinds: list[str] | None = None) -> list[dict]:
    """Read one [[forms]] TOML block per form; fail closed on missing/invalid files."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise Refused(f"invalid forms file: {error}") from error
    if set(document) != {"forms"} or not isinstance(document["forms"], list):
        raise Refused("forms file must contain only forms blocks")
    kinds = load_kinds() if kinds is None else kinds
    seen = set()
    for form in document["forms"]:
        reason = check(form, kinds=kinds)
        if reason:
            raise Refused(reason)
        if form["number"] in seen:
            raise Refused(f"duplicate form number: {form['number']}")
        seen.add(form["number"])
    return document["forms"]


def forms_only() -> bool:
    """Off unless Adam explicitly enables it; reading this never changes the environment."""
    return os.environ.get("NUCLEUS_FORMS_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}


def pick(screen: Screen, path: Path | None = None) -> tuple[Filled | None, str | None]:
    """Most conditions first, then lowest numeric form number. Return a miss reason.

    File/validation failures refuse forms and leave the existing live paragraph available.
    Proposed/rejected forms and forms that cannot safely fill are never selected.
    """
    try:
        kinds = load_kinds()
        available = load(FORMS_PATH if path is None else path, kinds=kinds)
    except (OSError, UnicodeError, Refused) as error:
        return None, f"forms unavailable: {error}"
    approved = [form for form in available if form["status"] == "approved"]
    if not approved:
        return None, "no approved forms"
    approved.sort(key=lambda form: (-len(form["when"]), int(form["number"][2:])))
    refused = []
    for form in approved:
        try:
            filled = fill(form, screen, kinds=kinds)
        except Refused as error:
            refused.append(f"{form['number']}: {error}")
            continue
        if filled is not None:
            return filled, None
    return None, "; ".join(refused) if refused else "no form fits"


def _check_screen(screen: Screen, kinds: list[str]) -> None:
    if (not isinstance(screen, Screen) or not isinstance(screen.answer, str)
            or screen.answer not in ANSWERS or type(screen.missing_links) is not bool):
        raise Refused("invalid screen")
    if not isinstance(screen.words, tuple) or any(not isinstance(w, str) or not w.strip() for w in screen.words):
        raise Refused("invalid screen words")
    if len(set(screen.words)) != len(screen.words):
        raise Refused("duplicate screen word")
    if not isinstance(screen.rows, tuple):
        raise Refused("invalid screen rows")
    records = set()
    for row in screen.rows:
        if not isinstance(row, Row) or row.word not in screen.words or not isinstance(row.record, str) or not row.record:
            raise Refused("invalid screen row")
        if row.kind is not None and (not isinstance(row.kind, str) or row.kind not in kinds):
            raise Refused("unknown middle word on screen")
        if row.quote is not None and (not isinstance(row.quote, str) or not row.quote.strip()):
            raise Refused("invalid screen quote")
        if row.record in records:
            raise Refused("duplicate screen record")
        records.add(row.record)


def _count_matches(actual: int, wanted: int | dict) -> bool:
    if type(wanted) is int:
        return actual == wanted
    return wanted.get("min", 0) <= actual <= wanted.get("max", float("inf"))


def fill(form: dict, screen: Screen, *, kinds: list[str] | None = None) -> Filled | None:
    """An approved matching form, or None; unsafe input raises Refused.

    Nonapproved forms cannot produce text. Every part retains its origin. Counts are
    derived only from this snapshot; no dictionary, question, database, or model is read.
    """
    return _fill(form, screen, kinds=kinds, statuses={"approved"})


def preview(form: dict, screen: Screen, *, kinds: list[str] | None = None) -> Filled | None:
    """Night-only example for review. Never changes status or enters the day picker."""
    return _fill(form, screen, kinds=kinds, statuses={"proposed", "approved"})


def _fill(form: dict, screen: Screen, *, kinds: list[str] | None, statuses: set[str]) -> Filled | None:
    kinds = load_kinds() if kinds is None else kinds
    reason = check(form, kinds=kinds)
    if reason:
        raise Refused(reason)
    if form["status"] not in statuses:
        return None
    _check_screen(screen, kinds)
    when = form["when"]
    counts = Counter(row.kind for row in screen.rows if row.kind is not None)
    for name, wanted in when.items():
        if name == "answer" and screen.answer != wanted:
            return None
        if name == "kinds_present" and not all(k in counts for k in wanted):
            return None
        if name == "kinds_absent" and any(k in counts for k in wanted):
            return None
        if name == "record_count" and not _count_matches(len(screen.rows), wanted):
            return None
        if name == "word_count" and not _count_matches(len(screen.words), wanted):
            return None
        if name == "missing_links" and screen.missing_links != wanted:
            return None

    template_parts = _parts(form["sentence"])
    blanks = {blank for _, blank in template_parts if blank is not None}
    present = when.get("kinds_present", [])
    bound_rows = [i for i, row in enumerate(screen.rows) if len(present) == 1 and row.kind == present[0]]
    focus = screen.rows[bound_rows[0]].word if bound_rows else next(iter(screen.words), None)
    # A total over several words must not be described as one word's count.
    if {"word", "count"} <= blanks and len({screen.rows[i].word for i in bound_rows}) != 1:
        return None
    values: dict[str, Part] = {
        "word_count": Part(str(len(screen.words)), "count(screen.words)"),
    }
    if focus is not None:
        values["word"] = Part(focus, f"screen.words[{screen.words.index(focus)}]")
        for i, word in enumerate(screen.words):
            if word != focus:
                values["other_word"] = Part(word, f"screen.words[{i}]")
                break
    # Exact, complete displayed quotes only. Choose the shortest safe whole quote
    # for this word/kind (word count, then length, then screen order). Never edit it.
    for blank in sorted(b for b in blanks if b.startswith("quote:")):
        kind = blank[len("quote:"):]
        eligible = [i for i, row in enumerate(screen.rows)
                    if row.word == focus and row.kind == kind and row.quote is not None
                    and _paragraph_reason(row.quote, []) is None]
        if eligible:
            i = min(eligible, key=lambda i: (len(_TOKEN.findall(screen.rows[i].quote)), len(screen.rows[i].quote), i))
            values[blank] = Part(screen.rows[i].quote, f"screen.rows[{i}].quote")
    if bound_rows:
        index = bound_rows[0]
        values["kind"] = Part(screen.rows[index].kind, f"screen.rows[{index}].kind")
        values["count"] = Part(str(len(bound_rows)), f"count(screen.rows.kind == {screen.rows[index].kind!r})")
    if counts:
        strongest = max(counts, key=counts.get)  # ties keep first occurrence on screen
        index = next(i for i, row in enumerate(screen.rows) if row.kind == strongest)
        values["strongest_kind"] = Part(screen.rows[index].kind, f"screen.rows[{index}].kind")
    if blanks - values.keys():
        return None

    parts = []
    for literal, blank in template_parts:
        if literal:
            parts.append(Part(literal, "form.sentence"))
        if blank is not None:
            parts.append(values[blank])
    text = "".join(part.text for part in parts)
    # Prevent joining separate pieces into a word that occurred in neither source.
    allowed_tokens = {token for part in parts for token in _TOKEN.findall(part.text)}
    if set(_TOKEN.findall(text)) - allowed_tokens:
        raise Refused("kill switch: filling joined pieces into a new word")
    reason = _paragraph_reason(text, list(screen.words))
    if reason:
        raise Refused(reason)
    return Filled(form["number"], text, tuple(parts))


if __name__ == "__main__":
    from .forms_night import main
    main()
