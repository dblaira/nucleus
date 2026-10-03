"""An English dictionary between his entry and his ontology.

His ontology defines each life domain in his own words. Health is "Medical, wellness, body maintenance, and
preventive care." His entry says "doctor". Neither his dictionary nor his records hold that word, so nothing of his
was reached and the answer was "I don't know". Adam, 2026-10-02: "It did not use the ontology and knowledge graph."

WordNet is a public English dictionary made by hand at Princeton. It says a doctor is "a licensed medical
practitioner". That is the bridge: doctor -> medical -> Health. No model reads the entry. Every bridge keeps the
exact definition it used, so the screen can show it.

Read only. When the dictionary is not installed, there are no bridges and nothing else changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

try:
    from nltk.corpus import wordnet as _wordnet
    _wordnet.ensure_loaded()
except Exception:                                   # not installed: no bridges
    _wordnet = None

PARTS = ("n", "v", "a")                             # a thing, a doing, a describing word
KIND_LEVELS = 2                                     # PROPOSAL: how far up "is a kind of" is followed: madness -> anger -> emotion
FEELING = ("noun.feeling", "verb.emotion")          # the dictionary's own shelf for words of feeling
_QUOTED_FROM = re.compile(r";\s*-\s*[A-Z][\w. ]*$")  # "roused to anger; - Mark Twain"


@dataclass(frozen=True)
class Sense:
    word: str                 # the word as he typed it
    part: str                 # n | v | a
    definition: str           # the English definition, exact
    described: tuple[str, ...]  # for a describing word: the definitions of the thing it describes ("madness" for "mad")
    also: tuple[str, ...]     # the same thing by other names: "physician" for "doctor"
    kinds: tuple[str, ...]    # what it is a kind of, nearest first: "medical practitioner", then "health professional"
    related: tuple[str, ...]  # the same word in another form: "madness" for "mad"
    feeling: bool             # the dictionary shelves it with feelings


def installed() -> bool:
    return _wordnet is not None


@lru_cache(maxsize=65536)
def bases(word: str) -> frozenset[str]:
    """The word with its ending taken off the way the dictionary does it: "getting" is "get", "buys" is "buy"."""
    low = word.lower().strip("'’")
    if _wordnet is None:
        return frozenset({low})
    return frozenset({low} | {base for part in PARTS if (base := _wordnet.morphy(low, part))})


@lru_cache(maxsize=4096)
def sense(word: str) -> Sense | None:
    """The first sense of the word, in the part of speech English uses it most. Nothing beyond that:
    the common meaning only."""
    if _wordnet is None:
        return None
    low = word.lower().strip("'’")
    best = None
    for order, part in enumerate(PARTS):
        base = _wordnet.morphy(low, part) or low
        synsets = _wordnet.synsets(base, pos=part)
        if not synsets:
            continue
        used = sum(lemma.count() for synset in synsets for lemma in synset.lemmas() if lemma.name().lower() == base)
        if best is None or (used, -order) > best[0]:
            best = ((used, -order), part, base, synsets[0])
    if best is None:
        return None
    _used, part, base, first = best
    also = [name.replace("_", " ") for name in first.lemma_names() if name.lower() != base]
    described, related = [], []
    things = [first] if part == "n" else []
    feeling = first.lexname() in FEELING
    if part == "a":
        for near in (first.similar_tos()[:1] + first.attributes()[:1]):
            described.append(_clean(near.definition()))
    for lemma in first.lemmas():
        if lemma.name().lower() != base:
            continue
        for form in lemma.derivationally_related_forms()[:3]:
            related.append(form.name().replace("_", " "))
            # a doing drifts when followed to its nouns, and a thing drifts when followed to a person: drug -> druggist
            if part != "v" and form.synset().pos() == "n" and not (part == "n" and form.synset().lexname() == "noun.person"):
                things.append(form.synset())
                if part == "a":
                    described.append(_clean(form.synset().definition()))
                    feeling = feeling or form.synset().lexname() in FEELING
    kinds = []
    for thing in things:                                              # what it is a kind of, nearest first
        level = thing.hypernyms()[:2]
        for _ in range(KIND_LEVELS):
            kinds += [name.replace("_", " ") for parent in level for name in parent.lemma_names()]
            level = [above for parent in level for above in parent.hypernyms()[:2]]
    return Sense(word, part, _clean(first.definition()), tuple(dict.fromkeys(described)), tuple(dict.fromkeys(also)),
                 tuple(dict.fromkeys(kinds)), tuple(dict.fromkeys(related)), feeling)


def _clean(definition: str) -> str:
    return _QUOTED_FROM.sub("", definition).strip()
