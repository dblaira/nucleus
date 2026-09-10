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
from pathlib import Path

CONNECTION_PREFIX = "https://understood.app/ontology/connection/"
_RECORD_START = re.compile(r"^<(" + re.escape(CONNECTION_PREFIX) + r"[^>]+)> a understood:Connection ;", re.M)
_LABEL = re.compile(r'understood:label "((?:[^"\\]|\\.)*)" ;', re.S)
_TYPE = re.compile(r'understood:connectionType "((?:[^"\\]|\\.)*)"')
_STRENGTH = re.compile(r'understood:strength "([^"]*)"')
_ACCEPTED_AT = re.compile(r'understood:acceptedAt "([^"]*)"')


def normalize_claim(value: str) -> str:
    return value.strip().rstrip(".").lower()


def unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


@dataclass(frozen=True)
class Record:
    uri: str
    leaf: str
    label: str
    connection_type: str
    strength: str
    accepted_at: str
    block: str


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
        records[uri] = Record(
            uri=uri,
            leaf=uri[len(CONNECTION_PREFIX) :],
            label=label.group(1) if label else "",
            connection_type=kind.group(1) if kind else "",
            strength=strength.group(1) if strength else "",
            accepted_at=accepted_at.group(1) if accepted_at else "",
            block=block,
        )
    return records


def load_graph(graph_path: Path, ledger_path: Path) -> Graph:
    raw_graph = graph_path.read_text(encoding="utf-8")
    raw_ledger = ledger_path.read_text(encoding="utf-8")
    ledger = json.loads(raw_ledger)
    if not isinstance(ledger, list):
        raise ValueError("The ledger is not a list of decisions.")
    return Graph(records=parse_graph(raw_graph), ledger=ledger, raw_graph=raw_graph, raw_ledger=raw_ledger)
