"""nucleus — an independent system around Adam's graph, ontology, and dictionary.

Adam, 2026-09-10: "That is the nucleus." "The RDF, Ontology, Dictionary all stay."
Only his three answers can come out.
"""

from pathlib import Path

NUCLEUS_FILES = {
    "graph": Path("/Users/adamblair/Documents/Main/Ontology/accepted/accepted-graph.ttl"),
    "ledger": Path("/Users/adamblair/Documents/Main/Ontology/accepted/decision-ledger.json"),
    "shape": Path("/Users/adamblair/Documents/Main/Ontology/shapes/connection-shape.ttl"),
    "upper": Path("/Users/adamblair/Documents/Main/Ontology/upper/bfo-bridge.ttl"),
    "meanings": Path("/Users/adamblair/Documents/adams-language/meanings.txt"),
    "routes": Path("/Users/adamblair/Documents/adams-language/routes.txt"),
}

DICTIONARY_ROOT = Path("/Users/adamblair/Documents/adams-language")
STORE_PATH = Path.home() / "Library" / "Application Support" / "nucleus" / "nucleus.sqlite3"
