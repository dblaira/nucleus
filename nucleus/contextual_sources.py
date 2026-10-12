"""Read later human reports through recorded conversation provenance, never RDF inference."""
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


def later_reports(graph, question: str) -> list[dict]:
    """Context is same conversation + later timestamp + a report about an answer.

    A quoted question in original source context is a retrieval anchor only;
    neither it nor any copied answer becomes accepted words or a relationship.
    Only accepted originals with verified offsets and hashes can be returned.
    """
    if len(question.split()) < 4:
        return []
    root = (NUCLEUS_FILES["graph"].parent.parent / "sources" / "automatic-exact-words").resolve()
    snapshots = {}
    for record in graph.records.values():
        match = SNAPSHOT.search(record.block)
        if record.record_class != "SourceEntry" or not match:
            continue
        path = Path(unescape(match.group(1))).resolve()
        if not path.is_relative_to(root):
            continue
        if path not in snapshots:
            try:
                snapshots[path] = json.loads(path.read_text()).get("entries", [])
            except (OSError, ValueError, AttributeError):
                snapshots[path] = []
    entries = {e.get("identity"): e for batch in snapshots.values() for e in batch if isinstance(e, dict)}
    anchors = {}
    for entry in entries.values():
        context = entry.get("context") or {}
        session = context.get("session_id")
        source = entry.get("source_text", "")
        if entry.get("adapter") != "codex" or not session or question.casefold() not in source.casefold():
            continue
        # Original root-human source identity is the scope; copied content is never an answer.
        if hashlib.sha256(source.encode()).hexdigest() != entry.get("source_sha256"):
            continue
        if not entry.get("identity", "").startswith(f"codex:{session}:"):
            continue
        created = entry.get("created_at", "")
        if session not in anchors or created < anchors[session][0]:
            anchors[session] = (created, entry["identity"])
    result = []
    admitted = [r for r in graph.records.values() if r.record_class == "SourceEntry" and graph.is_accepted(r)]
    superseded = {r.previous_record for r in admitted if r.previous_record}
    for record in graph.records.values():
        if record.leaf in superseded or record.record_class != "SourceEntry" or record.source_role not in ("input", "reflection") or not graph.is_accepted(record):
            continue
        entry = entries.get(record.source_identity)
        if not entry:
            continue
        session = (entry.get("context") or {}).get("session_id")
        if session not in anchors or entry.get("adapter") != "codex":
            continue
        if record.source_created_at <= anchors[session][0]:
            continue
        text = unescape(record.exact_words)
        if not (SELF_REPORT.search(text) and REPLY_REFERENCE.search(text)):
            continue
        source = entry.get("source_text", "")
        start, end = entry.get("char_start"), entry.get("char_end")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(source):
            continue
        if source[start:end] != text or entry.get("text") != text:
            continue
        if hashlib.sha256(source.encode()).hexdigest() != entry.get("source_sha256") or hashlib.sha256(text.encode()).hexdigest() != entry.get("text_sha256"):
            continue
        if entry.get("created_at") != record.source_created_at:
            continue
        date = datetime.fromisoformat(record.source_created_at.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        result.append({"id": record.uri, "leaf": record.leaf, "quote": text, "why": "",
                       "strength": "", "accepted_at": record.source_created_at,
                       "source_created_at": record.source_created_at, "source_date": date,
                       "context": "later report in the same conversation", "conversation_id": session,
                       "anchor_identity": anchors[session][1], "exact_words": True})
    # Retain the newest explicit report per conversation; do not declare a cause or supersede history.
    result.sort(key=lambda row: (row["source_created_at"], row["leaf"]), reverse=True)
    seen, unique = set(), []
    for row in result:
        if row["conversation_id"] not in seen:
            unique.append(row)
            seen.add(row["conversation_id"])
    return unique[:2]
