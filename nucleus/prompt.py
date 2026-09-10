"""The one prompt. Adam's five files verbatim, the dictionary's reading, his question, the contract."""

from __future__ import annotations

import json
from pathlib import Path

from . import NUCLEUS_FILES

CONTRACT = """You are reading Adam Blair's records. Everything above this line is his: his accepted graph
(RDF Turtle), his ledger of decisions, his ontology (the rulebook for the graph), his dictionary
(meanings.txt: each line is numbers, an index, " = ", then his meaning in his own words), and his
routes. Below is the dictionary's own reading of his question, then his question character for
character.

Adam, 2026-09-10: "The reason for it is so it can be grounded in my meaning." Go through all of it.

You return exactly one JSON object and nothing else. No prose before or after it.

Adam's three answers, in his words:
1. "aligned and why"
2. "Not sure.  some correlation, but not enough for causation, more data may help."
3. "I don't know" there is nothing in your records that points to a conclusion.

The object:
{
  "answer": "aligned" | "not_sure" | "dont_know",
  "words":   [{"word": "<one of his dictionary words, exactly as decoded, e.g. PULLED>", "why": "<one sentence>"}],
  "records": [{"id": "<a record id from the graph, the part after connection/>", "quote": "<a verbatim excerpt of that record's label>", "why": "<one sentence>"}],
  "possibility": [{"links": ["<record id or WORD>", "<record id or WORD>"], "proposed": "<one sentence>", "would_show": "<one sentence>"}]
}

Rules, checked by code after you answer:
- "aligned": his records match the theme of his question and point the same way. Give every matching word and record. Each why is one sentence saying why it matches his question. No advice. No next steps.
- "not_sure": his records touch the question but do not connect to it, or are weak, or pull two ways. Give the matching words and records with one-sentence whys that say what is missing. Then, and only then, fill "possibility": connections not yet in his records that his records make plausible. Each links exactly two things, each a real record id or a real dictionary word; "proposed" is one sentence stating the relationship; "would_show" is one sentence naming the data that would show whether it is real. This is the only place you may propose anything.
- "dont_know": nothing in his records points to a conclusion. words and records are empty. No possibility.
- A quote must be copied character for character from the record's label. Do not paraphrase his words anywhere.
- Every why is exactly one sentence. No line breaks.
- Never include a key that is not in the object above.
"""


def nucleus_text() -> tuple[str, dict[str, int]]:
    parts = []
    sizes: dict[str, int] = {}
    for name, path in NUCLEUS_FILES.items():
        text = path.read_text(encoding="utf-8")
        sizes[name] = len(text.encode("utf-8"))
        parts.append(f"===== {name}: {path} =====\n{text}\n")
    return "\n".join(parts), sizes


def not_accepted_block(graph) -> str:
    """Derived by code from his own ledger: graph records with no accepted decision. Never cite them."""
    leaves = sorted(record.leaf for record in graph.records.values() if not graph.is_accepted(record))
    if not leaves:
        return ""
    return (
        f"\n===== {len(leaves)} records in the graph have no accepted decision in the ledger. Do not cite them. =====\n"
        + "\n".join(leaves)
        + "\n"
    )


def build(question: str, brief: dict, nucleus: str, graph=None) -> str:
    reading = json.dumps(brief, ensure_ascii=False, indent=1)
    return (
        nucleus
        + (not_accepted_block(graph) if graph is not None else "")
        + "\n===== the dictionary's reading of the question =====\n"
        + reading
        + "\n\n===== Adam's question, character for character =====\n"
        + question
        + "\n\n===== the contract =====\n"
        + CONTRACT
    )


SCHEMA_PATH = Path(__file__).with_name("contract.schema.json")
