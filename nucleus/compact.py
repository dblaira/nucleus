"""The nucleus in compact form: his words untouched, the file wrapping removed.

Apple's server model has a 32,000 token window. The files as they sit on disk are about
93,000 tokens because of the RDF and JSON wrapping. One line per accepted record, plus the
dictionary and routes as they are, is about 29,000. Labels, notes, and meanings are verbatim.
"""

from __future__ import annotations

import re

from . import NUCLEUS_FILES
from .graph import Graph, unescape

_NOTE = re.compile(r'understood:evidenceNote "((?:[^"\\]|\\.)*)"', re.S)


def compact_records(graph: Graph) -> str:
    lines = ["# Adam's accepted records. One per line: id | type | strength | accepted | label | note. Labels and notes are his words, verbatim."]
    for record in graph.records.values():
        if not graph.is_accepted(record):
            continue
        note = _NOTE.search(record.block)
        line = f"{record.leaf} | {record.connection_type} | {record.strength} | {record.accepted_at[:10]} | {unescape(record.label)}"
        if note:
            line += f" | note: {unescape(note.group(1))}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def compact_nucleus(graph: Graph) -> tuple[str, dict[str, int]]:
    meanings = NUCLEUS_FILES["meanings"].read_text(encoding="utf-8")
    routes = NUCLEUS_FILES["routes"].read_text(encoding="utf-8")
    records = compact_records(graph)
    parts = {
        "records": f"===== accepted records ({sum(1 for r in graph.records.values() if graph.is_accepted(r))}) =====\n{records}",
        "meanings": f"===== meanings.txt (Adam's dictionary, verbatim) =====\n{meanings}\n",
        "routes": f"===== routes.txt (verbatim) =====\n{routes}\n",
    }
    sizes = {k: len(v.encode("utf-8")) for k, v in parts.items()}
    return "\n".join(parts.values()), sizes
