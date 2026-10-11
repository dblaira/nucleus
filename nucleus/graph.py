"""Adam's accepted graph and ledger, read as they are on disk.

The graph is a Turtle file of understood:Connection records. The ledger is a JSON
list of his decisions. A record counts as accepted when the latest ledger decision
for its label is "accepted". The join is by claim text, normalized exactly the way
the promotion code already does it: strip, drop the trailing period, lowercase.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CONNECTION_PREFIX = "https://understood.app/ontology/connection/"
_RECORD_START = re.compile(r"^<(" + re.escape(CONNECTION_PREFIX) + r"[^>]+)> a understood:(Connection|SourceEntry) ;", re.M)
_LABEL = re.compile(r'understood:label "((?:[^"\\]|\\.)*)" ;', re.S)
_TYPE = re.compile(r'understood:connectionType "((?:[^"\\]|\\.)*)"')
_STRENGTH = re.compile(r'understood:strength "([^"]*)"')
_ACCEPTED_AT = re.compile(r'understood:acceptedAt "([^"]*)"')
_EXACT_WORDS = re.compile(r'understood:exactWords "((?:[^"\\]|\\.)*)" ;', re.S)
_SOURCE_ROLE = re.compile(r'understood:sourceRole "([^"]*)"')
_SOURCE_CREATED = re.compile(r'<http://purl.org/dc/terms/created> "([^"]*)"')
_SOURCE_MODIFIED = re.compile(r'<http://purl.org/dc/terms/modified> "([^"]*)"')
_SOURCE_IDENTITY = re.compile(r'understood:sourceIdentity "((?:[^"\\]|\\.)*)" ;', re.S)
_REVISION_OF = re.compile(r'<http://www.w3.org/ns/prov#wasRevisionOf> <' + re.escape(CONNECTION_PREFIX) + r'([^>]+)>')


def normalize_claim(value: str) -> str:
    return value.strip().rstrip(".").lower()


def unescape(value: str) -> str:
    """Decode Turtle escapes once, preserving Unicode and literal backslashes."""
    escapes = {'t': '\t', 'n': '\n', 'r': '\r', 'b': '\b', 'f': '\f', '"': '"', "'": "'", '\\': '\\'}
    def replace(match):
        token = match.group(1)
        return chr(int(token[1:], 16)) if token.startswith(('u', 'U')) else escapes[token]
    return re.sub(r"\\(u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|[tnrbf\"'\\])", replace, value)


@dataclass(frozen=True)
class Record:
    uri: str
    leaf: str
    label: str
    connection_type: str
    strength: str
    accepted_at: str
    block: str
    record_class: str = "Connection"
    exact_words: str = ""
    source_role: str = ""
    source_created_at: str = ""
    previous_record: str = ""
    source_identity: str = ""
    source_modified_at: str = ""


@dataclass
class Graph:
    records: dict[str, Record]
    ledger: list[dict]
    raw_graph: str
    raw_ledger: str

    def find(self, record_id: str) -> Record | None:
        """Accept a full URI or its leaf."""
        if record_id in self.records:
            return self.records[record_id]
        return self.records.get(CONNECTION_PREFIX + record_id)

    def latest_decision(self, label: str) -> str | None:
        wanted = normalize_claim(unescape(label))
        latest = None
        latest_at = ""
        for entry in self.ledger:
            claim = entry.get("claim")
            if not isinstance(claim, str) or normalize_claim(claim) != wanted:
                continue
            at = str(entry.get("at", ""))
            if at >= latest_at:
                latest_at = at
                latest = str(entry.get("decision", ""))
        return latest

    def is_accepted(self, record: Record) -> bool:
        return self.latest_decision(record.label) == "accepted"

    def quote_is_in(self, record: Record, quote: str) -> bool:
        """Character for character inside the record's block, before or after unescaping."""
        if not quote.strip():
            return False
        return quote in record.block or quote in unescape(record.block)

    def source_entries(self, query: str = "", include_questions: bool = True) -> list[dict]:
        """Literal retrieval of accepted originals. No domain or relationship inference."""
        admitted = [r for r in self.records.values() if r.record_class == "SourceEntry" and self.is_accepted(r)]
        superseded = {r.previous_record for r in admitted if r.previous_record}
        current = {}
        for record in admitted:
            key = record.source_identity or record.leaf
            before = current.get(key)
            if before is None or (record.source_modified_at, record.accepted_at, record.leaf) > (before.source_modified_at, before.accepted_at, before.leaf):
                current[key] = record
        terms = set(re.findall(r"[\w’']+", query.casefold()))
        rows = []
        for r in current.values():
            if r.leaf in superseded or (not include_questions and r.source_role == "question"):
                continue
            text = unescape(r.exact_words)
            shared = terms & set(re.findall(r"[\w’']+", text.casefold()))
            if query and not shared:
                continue
            rows.append({"id": r.uri, "leaf": r.leaf, "text": text, "role": r.source_role,
                         "source_created_at": r.source_created_at, "accepted_at": r.accepted_at,
                         "source_date": datetime.fromisoformat(r.source_created_at.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat(),
                         "shared_terms": sorted(shared), "literal_matches": len(shared)})
        ordered = sorted(rows, key=lambda r: (r["literal_matches"], r["source_created_at"], r["leaf"]), reverse=True)
        result, seen = [], set()
        for row in ordered:
            if row["text"] not in seen:
                seen.add(row["text"])
                result.append(row)
        return result


def parse_graph(text: str) -> dict[str, Record]:
    records: dict[str, Record] = {}
    starts = list(_RECORD_START.finditer(text))
    for index, start in enumerate(starts):
        end = text.find("\n  .", start.end())
        if end == -1:
            end = len(text)
        block = text[start.start() : end + len("\n  .")]
        uri = start.group(1)
        label = _LABEL.search(block)
        kind = _TYPE.search(block)
        strength = _STRENGTH.search(block)
        accepted_at = _ACCEPTED_AT.search(block)
        exact_words = _EXACT_WORDS.search(block)
        source_role = _SOURCE_ROLE.search(block)
        source_created = _SOURCE_CREATED.search(block)
        previous = _REVISION_OF.search(block)
        source_identity = _SOURCE_IDENTITY.search(block)
        source_modified = _SOURCE_MODIFIED.search(block)
        records[uri] = Record(
            uri=uri,
            leaf=uri[len(CONNECTION_PREFIX) :],
            label=label.group(1) if label else "",
            connection_type=kind.group(1) if kind else "",
            strength=strength.group(1) if strength else "",
            accepted_at=accepted_at.group(1) if accepted_at else "",
            block=block,
            record_class=start.group(2),
            exact_words=exact_words.group(1) if exact_words else "",
            source_role=source_role.group(1) if source_role else "",
            source_created_at=source_created.group(1) if source_created else "",
            previous_record=previous.group(1) if previous else "",
            source_identity=source_identity.group(1) if source_identity else "",
            source_modified_at=source_modified.group(1) if source_modified else "",
        )
    return records


def load_graph(graph_path: Path, ledger_path: Path) -> Graph:
    raw_graph = graph_path.read_text(encoding="utf-8")
    raw_ledger = ledger_path.read_text(encoding="utf-8")
    ledger = json.loads(raw_ledger)
    if not isinstance(ledger, list):
        raise ValueError("The ledger is not a list of decisions.")
    return Graph(records=parse_graph(raw_graph), ledger=ledger, raw_graph=raw_graph, raw_ledger=raw_ledger)
