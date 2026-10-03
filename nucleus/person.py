"""Only the person changes: I → you, Adam → you. Every other word stays his.

Adam, 2026-10-02: "the output is put in a reasonable state to where I can read it like a normal
fucking sentence or statement or narrative".

His dictionary speaks as "I". His records speak about "Adam". A sentence handed back to him reads
as "you". Code changes the person and nothing else; `same_words` proves it. A sentence that cannot
be turned cleanly comes back as None, and the caller hands it back in his exact words, in quotes.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------- sentences

_HOLD = [("A.I.", "A\u0001I\u0001"), ("a.i.", "a\u0001i\u0001"), ("e.g.", "e\u0001g\u0001"), ("i.e.", "i\u0001e\u0001"),
         ("vs.", "vs\u0001"), ("etc.", "etc\u0001")]
_NUMBERED = re.compile(r"(^|\s)(\d{1,2})\.(?=\s)")
_END = re.compile(r"[.!?…]+[\"”’')\]]*(?=\s+\S)")


def split_sentences(text: str) -> list[str]:
    """His text, cut where he ended a sentence. Nothing inside a sentence is touched."""
    held = text
    for mark, hold in _HOLD:
        held = held.replace(mark, hold)
    held = re.sub(r"\.\.\.", "\u0002", held)                     # his three dots stay inside the sentence
    held = _NUMBERED.sub(lambda m: m.group(1) + m.group(2) + "\u0003", held)   # "1." opens a line, it does not end one
    parts, start = [], 0
    for match in _END.finditer(held):
        parts.append(held[start:match.end()])
        start = match.end()
    parts.append(held[start:])
    out = []
    for part in parts:
        part = part.strip().replace("\u0002", "...").replace("\u0003", ".")
        for mark, hold in _HOLD:
            part = part.replace(hold, mark)
        if part:
            out.append(part)
    return out


# ---------------------------------------------------------------- I → you

_SECOND = re.compile(r"\b(you|your|yours|yourself|you['’]re|you['’]ve|you['’]d|you['’]ll)\b", re.I)
_FIRST = re.compile(r"(?<![A-Za-z]\.)\b(I|I['’]m|I['’]ve|I['’]d|I['’]ll|my|me|mine|myself)\b(?!\.[A-Za-z])")
_FIRST_ANY = re.compile(r"(?<![A-Za-z]\.)\b(I|I['’]m|I['’]ve|I['’]d|I['’]ll|[Mm]y|me|mine|myself)\b(?!\.[A-Za-z])")

_I_RULES = [
    (re.compile(r"\bI(['’])m\b"), r"you\1re"),
    (re.compile(r"\bI(['’])ve\b"), r"you\1ve"),
    (re.compile(r"\bI(['’])d\b"), r"you\1d"),
    (re.compile(r"\bI(['’])ll\b"), r"you\1ll"),
    (re.compile(r"\b[Aa]m I\b"), lambda m: "Are you" if m.group(0)[0] == "A" else "are you"),
    (re.compile(r"\b[Ww]as I\b"), lambda m: "Were you" if m.group(0)[0] == "W" else "were you"),
    (re.compile(r"\bI am\b"), "you are"),
    (re.compile(r"\bI was\b"), "you were"),
    (re.compile(r"(?<![A-Za-z]\.)\bI\b(?!\.[A-Za-z])"), "you"),
    (re.compile(r"\bmyself\b"), "yourself"),
    (re.compile(r"\bMy\b"), "Your"),
    (re.compile(r"\bmy\b"), "your"),
    (re.compile(r"\bmine\b"), "yours"),
    (re.compile(r"\bme\b"), "you"),
]


def speaks_as_i(text: str) -> bool:
    return bool(_FIRST_ANY.search(text))


def speaks_to_someone(text: str) -> bool:
    return bool(_SECOND.search(text))


def _capital(sentence: str) -> str:
    """A sentence that now opens with "you" opens with "You". Nothing else is recapitalized."""
    return re.sub(r"^([\"“'‘(]*)y(ou\w*)", lambda m: m.group(1) + "Y" + m.group(2), sentence)


def i_to_you(text: str) -> str | None:
    """His own sentence, said back to him. None when it already speaks to someone as "you" and
    also as "I": turning it would mix the two people."""
    if speaks_as_i(text) and speaks_to_someone(text):
        return None
    out = []
    for sentence in split_sentences(text) or [text]:
        for pattern, replacement in _I_RULES:
            sentence = pattern.sub(replacement, sentence)
        out.append(_capital(sentence))
    return " ".join(out)


# ---------------------------------------------------------------- Adam → you

# verbs as they appear after "Adam" or "he" in his accepted records; anything else is left as written
_IRREGULAR = {"is": "are", "was": "were", "has": "have", "does": "do", "goes": "go",
              "isn't": "aren't", "isn’t": "aren’t", "wasn't": "weren't", "wasn’t": "weren’t",
              "doesn't": "don't", "doesn’t": "don’t", "hasn't": "haven't", "hasn’t": "haven’t",
              "studies": "study", "tries": "try", "carries": "carry", "relies": "rely", "applies": "apply"}
_VERBS = set("""thinks picks plans turns captures shops studies puts buys sets works feeds builds researches holds
maintains tags favors wants learns runs prepares moves starts knows experiences returns hunts feels prefers asks
pulls analyzes journals investigates pauses kills keeps uses needs makes takes gives finds sees gets says tells
acts tests watches reads writes ships tracks trains treats trusts values views wins loses lets leaves looks
lives means notices opens plays reaches saves seeks sends shares shows spends stays stops tends responds
delegates designs draws drops follows grows handles helps hears describes decides creates collects chooses
checks changes calls brings begins believes avoids adds accepts filters commits casts narrows engineers
compensates thrives combines pursues challenges narrates talks organizes listens collects""".split()) | set(_IRREGULAR)
_ADVERBS_OK = re.compile(r"^(\w+ly|never|always|often|also|still|just|only|first)$")


def _base(verb: str) -> str:
    low = verb.lower()
    if low in _IRREGULAR:
        return _IRREGULAR[low]
    if low.endswith("ies"):
        return low[:-3] + "y"
    if low.endswith(("sses", "shes", "ches", "xes", "zzes", "oes")):
        return low[:-2]
    if low.endswith("s") and not low.endswith("ss"):
        return low[:-1]
    return low


def _after_subject(rest: str) -> str:
    """The words right after "you": the verb agrees with "you". One adverb may stand between them."""
    tokens = rest.split(" ")
    for index in (0, 1):
        if index >= len(tokens):
            break
        token = tokens[index]
        core = re.sub(r"[,;:.!?]+$", "", token)
        if core.lower() in _VERBS:
            tokens[index] = _base(core) + token[len(core):]
            break
        if not (index == 0 and _ADVERBS_OK.match(core)):
            break
    return " ".join(tokens)


_QUOTED = re.compile(r"(“[^”]*”|\"[^\"]*\")")
_JOINERS = {"and", "then", "but", "or"}
_NEW_CLAUSE = {"that", "which", "who", "what", "because", "unless", "if", "while", "so"}
# records where the verb sits too far from "Adam" for the rule above; checked by `same_words` like the rest
_BY_HAND = {
    "Adam is energized by go-between roles — coordinator, facilitator, liaison — feels boxed in by narrow scope, and prefers to delegate details":
        "You are energized by go-between roles — coordinator, facilitator, liaison — feel boxed in by narrow scope, and prefer to delegate details",
}
_ENDS_CLAUSE = re.compile(r"[.!?;]$")
_SIMPLE = {"his": "your", "His": "Your", "him": "you", "himself": "yourself",
           "Adam's": "your", "Adam’s": "your", "he'd": "you'd", "he’d": "you’d", "He'd": "You'd", "He’d": "You’d",
           "he's": "you're", "he’s": "you’re", "He's": "You're", "He’s": "You’re"}
_EDGES = re.compile(r"^([\"“'‘(\[]*)(.*?)([.,;:!?\"”’')\]]*)$")


def _turn_about_him(text: str) -> str:
    """One stretch of a record with no quotation in it: Adam and he become you, the verb agrees."""
    pieces = re.findall(r"\s+|\S+", text)
    out: list[str] = []
    agree = 0            # how many of the next words may be the verb that goes with "you"
    active = False       # "you" is the subject of this clause, so a joined verb agrees too
    previous = ""
    for piece in pieces:
        if piece.isspace():
            out.append(piece)
            continue
        lead, core, tail = _EDGES.match(piece).groups()
        low = core.lower()
        if core in ("Adam", "he", "He"):
            core, agree, active = ("You" if core == "He" else "you"), 2, True
        elif core in _SIMPLE:
            core, agree = _SIMPLE[core], 0
        elif agree and low in _VERBS:
            core, agree = _base(core), 0
        elif agree == 2 and _ADVERBS_OK.match(low):
            agree = 1
        elif active and previous in _JOINERS and low in _VERBS:
            core, agree = _base(core), 0
        else:
            agree = 0
        if _ENDS_CLAUSE.search(tail) or core in ("—", "–") or low in _NEW_CLAUSE:
            active = False
        if not _ADVERBS_OK.match(low):
            previous = low
        out.append(lead + core + tail)
    return "".join(out)


def adam_to_you(text: str) -> str | None:
    """A record written about him, said to him. His quoted words inside it are left exactly as
    they are. None when a word about him is left that code cannot turn; the caller then keeps the
    record in its exact words."""
    if "AGENT PROPOSAL" in text:
        return None
    if text in _BY_HAND:
        return _BY_HAND[text]
    parts = _QUOTED.split(text)
    turned = []
    for index, part in enumerate(parts):
        if index % 2 == 1:                       # his quotation: untouched
            turned.append(part)
            continue
        if speaks_as_i(part) or speaks_to_someone(part):
            return None
        part = re.sub(r"\bFor Adam,", "For you,", part)
        turned.append(_turn_about_him(part))
    out = "".join(turned)
    outside = "".join(p for i, p in enumerate(_QUOTED.split(out)) if i % 2 == 0)
    if re.search(r"\b(he|He|his|His|him|himself|Adam)\b", outside):
        return None
    return " ".join(_capital(sentence) for sentence in (split_sentences(out) or [out]))


# ---------------------------------------------------------------- the proof

_PERSON = set("""i i'm i've i'd i'll my me mine myself am was you you're you've you'd you'll your yours yourself
are were adam adam's he he'd he's his him himself is has have does do doesn't don't isn't aren't wasn't weren't
hasn't haven't for""".split())


def _content(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9'’\-]+", text.lower().replace("’", "'"))
    kept = []
    for word in words:
        word = word.strip("'-")
        if not word or word in _PERSON:
            continue
        kept.append(_base(word) if word in _VERBS or word.endswith("s") else word)
    return sorted(kept)


def same_words(original: str, turned: str) -> bool:
    """True when nothing but the person changed: every other word of his is still there, none added."""
    return _content(original) == _content(turned)
