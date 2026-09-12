"""The middle words. Adam's own list, read from his note, never from a model.

Adam's note, Narrative vs Relational: "The two things are not enough. The middle must say what kind of
connection exists." "Thing A → exact relationship → Thing B"

The words come from the tree under "The usable hierarchy" in that note. A line like
"├── requires / depends on" gives two words; text after " — " is his gloss and is dropped.
"""

from __future__ import annotations

import re
from pathlib import Path

NOTE = Path("/Users/adamblair/Documents/Main/🗯 Narrative vs 🔥 Relational.md")
_LEAF = re.compile(r"[├└]──\s+(.+)$")
_GROUP = re.compile(r"^[A-Z][A-Z ]+(?:—|$)")


def load_kinds(path: Path = NOTE) -> list[str]:
    text = path.read_text(encoding="utf-8")
    start = text.find("The usable hierarchy")
    block = text[start:] if start != -1 else text
    end = block.find("```", block.find("```") + 3)
    block = block[:end] if end != -1 else block
    kinds: list[str] = []
    for line in block.splitlines():
        found = _LEAF.search(line)
        if not found:
            continue
        leaf = found.group(1).strip()
        if _GROUP.match(leaf):          # a group name like "MEANING — What is this thing..." is not a middle word
            continue
        leaf = leaf.split(" — ")[0]
        for word in leaf.split(" / "):
            word = word.strip()
            if word and word not in kinds:
                kinds.append(word)
    return kinds


def is_kind(value: object, kinds: list[str]) -> bool:
    return isinstance(value, str) and value.strip() in kinds
