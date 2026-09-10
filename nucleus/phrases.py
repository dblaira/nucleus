"""Meaning with meaning. Adam's own phrases, looked up by code, instantly.

Adam, 2026-09-10: "if we added some type of other deterministic query criteria that we could take
phrases of mine, 4 and 5 word phrases of mine, and they could be looked up immediately. So I
could look up meaning with meaning."

Every 2 to 5 word phrase in his dictionary and his accepted graph records goes into an index.
A question is cut into the same phrases. Every phrase they share is a hit, in milliseconds,
with no model. Word endings are folded (pushed, pushes, pushing → push) so his phrase still
matches when the ending differs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .dictionary import Meaning
from .graph import Graph

STOP = set("the a an and or of to in on at for with is are was were be been it its this that these those i my me "
           "you your he she they them we our as by from so if then than into out up down not no yes do does did "
           "have has had can could should would will just very more most some any all am".split())
_WORD = re.compile(r"[a-z’']+")


def stem(word: str) -> str:
    for ending in ("ing", "ed", "es", "s"):
        if len(word) > len(ending) + 3 and word.endswith(ending):
            return word[: -len(ending)]
    return word


def tokens(text: str) -> list[str]:
    out = []
    for word in _WORD.findall(text.lower().replace("’", "'")):
        word = word.strip("'")
        if word:
            out.append(stem(word))
    return out


def phrases(words: list[str], sizes=(2, 3, 4, 5)) -> set[str]:
    out: set[str] = set()
    for n in sizes:
        for i in range(len(words) - n + 1):
            gram = words[i : i + n]
            content = [w for w in gram if w not in STOP]
            if len(content) >= 2 and gram[0] not in STOP and gram[-1] not in STOP:
                out.add(" ".join(gram))
    return out


@dataclass(frozen=True)
class Hit:
    phrase: str
    kind: str        # word | record
    name: str        # dictionary word, or record leaf
    text: str        # his meaning, or the record label
    strength: str = ""


class PhraseIndex:
    def __init__(self, meanings: list[Meaning], graph: Graph) -> None:
        self.index: dict[str, list[Hit]] = {}
        for meaning in meanings:
            for phrase in phrases(tokens(meaning.text)) | phrases(tokens(meaning.word)):
                self.index.setdefault(phrase, []).append(Hit(phrase, "word", meaning.word, meaning.text))
        for record in graph.records.values():
            if not graph.is_accepted(record):
                continue
            for phrase in phrases(tokens(record.label)):
                self.index.setdefault(phrase, []).append(Hit(phrase, "record", record.leaf, record.label, record.strength))

    def lookup(self, question: str) -> list[Hit]:
        found: list[Hit] = []
        seen: set[tuple[str, str]] = set()
        # longest phrases first, so "kill it and think bigger" comes before "and think bigger"
        for phrase in sorted(phrases(tokens(question)) & set(self.index), key=lambda p: (-len(p.split()), p)):
            for hit in self.index[phrase]:
                key = (hit.kind, hit.name)
                if key in seen:
                    continue
                seen.add(key)
                found.append(hit)
        return found
