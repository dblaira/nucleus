"""Review every accepted original; retrieve later context without RDF inference."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import NUCLEUS_FILES
from .graph import unescape

SNAPSHOT = re.compile(r'understood:sourceSnapshot "((?:[^"\\]|\\.)*)" ;')
SELF_REPORT = re.compile(r"\bI (?:am|feel|felt|have|find myself)\b", re.I)
REPLY_REFERENCE = re.compile(r"\b(?:answer|response|replied|reflections)\b", re.I)
REQUEST = re.compile(r"^\s*(?:(?:now|then|okay|ok)[, ]+)?(?:fix|open|show|use|try|keep|make sure|verify|check|set up|put|ask|approve|do it|then fix|now show)\b", re.I)


class SourceContextUnavailable(ValueError):
    pass


def _scope(entry):
    context = entry.get("context") or {}
    adapter = entry.get("adapter")
    for key in ("session_id", "question_id", "reminder_id", "intake_id"):
        if context.get(key):
            return (adapter, key, str(context[key]))
    # Native question entries carry the question's ID as their source_id.
    if adapter == "cowboyai" and entry.get("role") == "question" and entry.get("source_id"):
        return ("cowboyai", "question_id", str(entry["source_id"]))
    return None


def _valid(entry, record=None):
    source, text = entry.get("source_text"), entry.get("text")
    start, end = entry.get("char_start"), entry.get("char_end")
    if not isinstance(source, str) or not isinstance(text, str):
        return False
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(source):
        return False
    if source[start:end] != text or hashlib.sha256(source.encode()).hexdigest() != entry.get("source_sha256"):
        return False
    if hashlib.sha256(text.encode()).hexdigest() != entry.get("text_sha256"):
        return False
    if record and (text != unescape(record.exact_words) or entry.get("created_at") != record.source_created_at):
        return False
    return True


def _terms(text):
    from .narrative import content, WHEN
    return set(content(text)) - WHEN


def review_later_words(graph, question: str) -> tuple[list[dict], dict]:
    """Every question reviews all accepted current originals before answer selection.

    Exact question occurrence or literal topic overlap establishes retrieval
    context. Later messages are scoped by recorded conversation/question IDs.
    Their words need not overlap, use first person, or mention an answer.
    These are provenance/context checks, never new semantic relationships.
    """
    root = (NUCLEUS_FILES["graph"].parent.parent / "sources" / "automatic-exact-words").resolve()
    snapshots = {}
    admitted = [r for r in graph.records.values() if r.record_class == "SourceEntry" and graph.is_accepted(r)]
    superseded = {r.previous_record for r in admitted if r.previous_record}
    current = [r for r in admitted if r.leaf not in superseded]
    for record in current:
        match = SNAPSHOT.search(record.block)
        if not match:
            continue
        path = Path(unescape(match.group(1))).resolve()
        if not path.is_relative_to(root):
            raise SourceContextUnavailable(f"Original source snapshot is outside its recorded source directory: {path}")
        if path not in snapshots:
            try:
                entries = json.loads(path.read_text())["entries"]
                if not isinstance(entries, list):
                    raise ValueError("entries are not a list")
                snapshots[path] = entries
            except (OSError, ValueError, KeyError) as error:
                raise SourceContextUnavailable(f"Later words could not be checked: {path}: {error}") from error
    entries = {e.get("identity"): e for batch in snapshots.values() for e in batch if isinstance(e, dict)}
    verified, invalid = [], []
    for record in current:
        entry = entries.get(record.source_identity)
        if entry and _valid(entry, record):
            verified.append((record, entry))
        else:
            invalid.append(record.leaf)
    if invalid:
        raise SourceContextUnavailable("Original words could not be verified for: " + ", ".join(invalid))
    audit = {"question": question, "graph_sha256": hashlib.sha256(graph.raw_graph.encode()).hexdigest(),
             "checked_originals": [r.leaf for r, _ in verified], "checked_count": len(verified),
             "later_candidates": [], "selected": [], "relationships_created": 0}
    anchors = {}
    wanted = _terms(question)
    # Exact occurrences in original source envelopes remain context only, even
    # when a quoted question or copied answer is not accepted as Adam's words.
    for entry in entries.values():
        scope = _scope(entry)
        if not scope or not _valid(entry):
            continue
        source = entry["source_text"]
        exact = bool(question.strip()) and question.casefold().strip() in source.casefold()
        # Topic anchors must be accepted original words, not quoted/copied envelopes.
        accepted_text = next((unescape(r.exact_words) for r, e in verified if e["identity"] == entry["identity"]), "")
        shared = wanted & _terms(accepted_text)
        topic = bool(wanted) and len(shared) >= min(2, len(wanted))
        if not exact and not topic:
            continue
        created = entry.get("created_at", "")
        priority = 2 if exact else 1
        prior = anchors.get(scope)
        if prior is None or priority > prior[2] or (priority == prior[2] and created < prior[0]):
            anchors[scope] = (created, entry["identity"], priority)
    rows = []
    for record, entry in verified:
        scope = _scope(entry)
        if scope not in anchors or record.source_created_at <= anchors[scope][0]:
            continue
        audit["later_candidates"].append(record.leaf)
        text = unescape(record.exact_words)
        # Questions and operational requests are considered in the audit but
        # never presented as personal facts or answers to another question.
        if record.source_role not in ("input", "reflection") or REQUEST.search(text) or REQUEST.search(entry["source_text"]):
            continue
        date = datetime.fromisoformat(record.source_created_at.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        row = {"id": record.uri, "leaf": record.leaf, "quote": text, "why": "", "strength": "",
               "accepted_at": record.source_created_at, "source_created_at": record.source_created_at,
               "source_date": date, "context": "later words in the same recorded source context",
               "conversation_id": scope[2], "anchor_identity": anchors[scope][1], "exact_words": True}
        # Explicit reports about an answer rank first, but are no longer a gate.
        priority = int(bool(SELF_REPORT.search(text) and REPLY_REFERENCE.search(text)))
        rows.append((priority, record.source_created_at, row))
    rows.sort(key=lambda item: (item[0], item[1], item[2]["leaf"]), reverse=True)
    # Always retain the newest eligible later words, including a subsequent
    # update that has none of the old report vocabulary. An explicit earlier
    # report may also remain, with its own date; neither silently replaces the other.
    selected = []
    groups = {}
    for priority, created, row in rows:
        groups.setdefault(row["conversation_id"], []).append((priority, created, row))
    for group in groups.values():
        newest = max(group, key=lambda item: (item[1], item[2]["leaf"]))[2]
        reference = group[0][2]
        if group[0][0] and reference["leaf"] != newest["leaf"]:
            selected.append(reference)
        selected.append(newest)
    audit["selected"] = [row["leaf"] for row in selected]
    return selected, audit


def later_reports(graph, question: str) -> list[dict]:
    return review_later_words(graph, question)[0]
