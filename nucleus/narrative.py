"""The meaning, in normal sentences, with no model.

Adam, 2026-10-02: "after adding the ontology and the knowledge graph to the dictionary and everything I have, I
should have more meaning that doesn't require a fucking large language model to help me with, and and it's just
the output is put in a reasonable state to where I can read it like a normal fucking sentence or statement or
narrative"

Adam, 2026-10-01: "choose from (I don't know) 400 responses that use if/then statements or some other type of
decision tree to respond."

The responses are his own sentences: his dictionary, cut where he ended each sentence, and his accepted records.
Code reaches his words from the question, walks from one of his words to the next through his own sentences,
picks the sentences that fit, and says them back to him as "you". No sentence is written here. No model is called.

Every number below that decides something is a PROPOSAL, not a rule of record (adams-authority).
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from .dictionary import Meaning
from .gate import unescape_label
from .graph import Graph, load_graph
from .person import adam_to_you, i_to_you, same_words, split_sentences
from .phrases import STOP, PhraseIndex, stem, tokens

PATTERN_FILE = NUCLEUS_FILES["graph"].parent / "adam_pattern.ttl"
ONTOLOGY_ROOT = NUCLEUS_FILES["graph"].parent.parent          # Main/Ontology: one folder per life domain, each with his one-line definition
LIFE_DOMAINS = ("affect", "ambition", "belief", "entertainment", "exercise", "health", "insight", "learning",
                "nutrition", "purchase", "sleep", "social", "work")
# words in his domain definitions that name no domain by themselves
PLAIN = {stem(w) for w in """decision decisions state quality personal core target targets activity activities performance
maintenance care science body long term and""".split()}
# his middle words that answer "why": FUNCTION and CAUSAL STRUCTURE in his note, plus "explains"
WHY_KINDS = {"requires", "depends on", "enables", "supports", "constrains", "limits", "prevents", "inhibits", "causes",
             "contributes to", "mediates", "moderates", "feeds back into", "explains"}

MAX_WORDS_TOLD = 2          # PROPOSAL: how many of his words one paragraph speaks about; the rest stay as rows
MAX_SENTENCES = 4           # PROPOSAL: sentences taken from one meaning
MAX_WINDOW_WORDS = 46       # PROPOSAL
MAX_TOLD_WORDS = 125        # PROPOSAL: the whole answer. His words, 2026-10-02: "I don't speak that way or read long rows of text."
SHORT_PHRASE_NEEDS = 3.0    # PROPOSAL: a word reached by a two-word phrase is told only when its sentences fit this well
SECOND_NEEDS = 0.4          # PROPOSAL: a second word is told only when it fits at least this share as well as the first
WALK_NEEDS = 3.0            # PROPOSAL: the walk to a neighboring word of his is told only when its sentences fit this well
RECORD_NEEDS = 2.0          # PROPOSAL: a record joins the answer only when it fits the question this well
PHRASE_WORDS = 3            # PROPOSAL: a shared phrase counts from this many words. His words, 2026-09-10: "4 and 5 word phrases of mine"
# PROPOSAL: words of his that are also everyday English. Typed in capitals they are his word. Typed small, in
# passing ("the more I work on it"), they are told only when his sentences share more than the word itself.
IN_PASSING = set("""WORK DONE LEARNING ACTION CONTEXT VALUE SIMPLE NOTES IMAGES NUMBERS BUSINESS SOFTWARE RESEARCH UNIQUE
COMPLEX ENVIRONMENT FRAMEWORK HOMES MENU MAYBE USEFUL GUIDED SHELL ARCHIVE HURRY IMPORTANCE MEANINGFUL CIRCLE""".split())

# words that carry a question but no meaning of his
ASKING = set("""what why how when where who which whom whose does did doing should would could can cannot may might
must shall will know think feel get got like thing things sometimes now really seem seems tend usually also about there
here because while right even though still ever never much many less each every other another same way lot been being
going want need make made take use used one two keep keeps kept come comes came say said tell mean means meant
something anything everything nothing someone time times today day days week weeks into onto over under again just
only actually maybe well good new old big small long short back before after during actual let lets put too but don
isn doesn didn won wouldn couldn shouldn yes very""".split())
ASKING = {stem(w) for w in ASKING} | ASKING

# the question says something is missing, lost, stuck, or hurting
TROUBLE = {stem(w) for w in """lose lost losing loss cannot can't slow slower slowly mad angry burden worry worried stuck
drag drags dragging discouraged anxious anxiety tired drop drops dropped ruin ruins fail failed failure bad hard
don't doesn't won't stop stopped stops frustrated frustrating hate afraid fear stress stressed bored boring apathetic
apathy overwhelmed confused confusing trouble problem struggle struggling wrong weird lack lacking without unable
linger lingering odd unfounded""".split()}
# his sentence speaks about the missing, the lost, the stuck
ANSWERS_TROUBLE = {stem(w) for w in """lack lose lost can't cannot stress kill pause worry burden opposite stop avoid
distract distraction frustrated apathy boredom mistake obsession obsessive narrow vanish unfamiliar regret lies
without never disrupted stagnation friction slowing objective drop block""".split()}
BECAUSE = {"because", "when", "mean", "signal", "come", "so", "therefore", "lead", "create", "reason", "which"}
STARTS_MID_THOUGHT = re.compile(r"^(this|that|it|they|and|so|when this|from this|otherwise|then|these|those)\b", re.I)
WHAT_IS = re.compile(r"^\s*(what\s+is|what['’]s|what\s+are|what\s+does|what\s+do\s+i\s+mean|define)\b", re.I)
DOMAIN = re.compile(r"understood:inLifeDomain <https://understood.app/ontology/domain/([^>]+)>")
NOTE = re.compile(r'understood:evidenceNote "((?:[^"\\]|\\.)*)"', re.S)
MEASURED = re.compile(r"(\d+)% (?:of tracked weeks \((\d+) weeks, ([^)]+)\)|across (\d+) tracked weeks \(([^)]+)\))")
HIS_WORDS_RECORD = re.compile(r"^“(.+)”\s+—\s+his words\b.*$", re.S)
LOGGED = "(his logged data, not anyone's words)"


@dataclass(frozen=True)
class Reach:
    """How the question reached one of his words."""
    word: str
    how: str          # said | route | phrase
    by: str           # his own words in the question that led there


@dataclass
class Part:
    """One piece of the paragraph and exactly where it came from."""
    text: str         # as told, to "you"
    exact: str        # his exact words, untouched
    source: str       # meaning | walk | record | weeks | pattern | tie | domain
    word: str = ""
    record: str = ""


@dataclass
class Told:
    text: str = ""
    reaches: list[Reach] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    no_meaning_yet: list[str] = field(default_factory=list)
    ms: float = 0.0


def content(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOP and t not in ASKING and len(t) > 2]


class Narrator:
    """Built once from his files. Each question after that is a lookup."""

    def __init__(self, meanings: list[Meaning], graph: Graph, pattern_file: Path = PATTERN_FILE,
                 routes_file: Path | None = None, ontology_root: Path = ONTOLOGY_ROOT) -> None:
        self.meanings = meanings
        self.graph = graph
        self.words: list[str] = []
        self.sentences: dict[str, list[list[str]]] = {}      # word -> one list of sentences per meaning, his order
        for meaning in meanings:
            if meaning.word not in self.sentences:
                self.words.append(meaning.word)
                self.sentences[meaning.word] = []
            self.sentences[meaning.word].append(split_sentences(meaning.text) or [meaning.text])
        # how many of his words hold each single word: a word held by few counts for more when sentences are chosen
        self.holders: dict[str, set[str]] = {}
        for meaning in meanings:
            for token in set(content(meaning.text)) | set(content(meaning.word)):
                self.holders.setdefault(token, set()).add(meaning.word)
        self.record_spread: dict[str, int] = {}
        for record in graph.records.values():
            if graph.is_accepted(record):
                for token in set(content(unescape_label(record.label))):
                    self.record_spread[token] = self.record_spread.get(token, 0) + 1
        # the graph on his dictionary: a word of his named inside another word's meaning is a neighbor
        self.neighbors: dict[str, list[str]] = {}
        texts = {w: " ".join(" ".join(run) for run in self.sentences[w]).lower() for w in self.words}
        for word in self.words:
            near = [other for other in self.words if other != word and len(other) > 3
                    and re.search(r"\b" + re.escape(other.lower()) + r"\b", texts[word])]
            self.neighbors[word] = near
        # his knowledge graph: the accepted measurement between each pair of life domains
        self.weeks: dict[frozenset, tuple[float, str, str, str]] = {}
        for record in graph.records.values():
            if record.connection_type != "observed_correlation" or not graph.is_accepted(record):
                continue
            pair = frozenset(DOMAIN.findall(record.block))
            note = NOTE.search(record.block)
            strength = float(record.strength or 0)
            if len(pair) == 2 and (pair not in self.weeks or strength > self.weeks[pair][0]):
                self.weeks[pair] = (strength, unescape_label(record.label), unescape_label(note.group(1)) if note else "", record.leaf)
        self.domain_cues, self.domain_lines = load_domain_cues(ontology_root)
        # every pair of life domains his tracked weeks measured, strongest first, by domain
        self.weeks_by_domain: dict[str, list[tuple[float, frozenset]]] = {}
        for pair, found in self.weeks.items():
            for domain in pair:
                self.weeks_by_domain.setdefault(domain, []).append((found[0], pair))
        for found in self.weeks_by_domain.values():
            found.sort(key=lambda f: (-f[0], sorted(f[1])))
        self.phrase_index = PhraseIndex(meanings, graph)
        self.steps = load_pattern(pattern_file)
        self.routes = load_routes(routes_file, set(self.words))

    # ------------------------------------------------------------ 1. reach his words from the question

    def reach(self, question: str, reading: dict, extra_routes: dict[str, str] | None = None) -> list[Reach]:
        found: dict[str, Reach] = {}
        asked = tokens(question)

        def add(word: object, how: str, by: object) -> None:
            if isinstance(word, str) and word in self.sentences and word not in found:
                found[word] = Reach(word, how, str(by or word))

        def said_in_question(folded: list[str]) -> bool:
            return bool(folded) and any(asked[i:i + len(folded)] == folded for i in range(len(asked) - len(folded) + 1))

        for item in reading.get("heSaidTheWordItself") or []:
            if isinstance(item, dict):
                add(item.get("word"), "said", item.get("triggeredBy"))
        for item in reading.get("hisRoutesSentItHere") or []:
            if isinstance(item, dict):
                add(item.get("word"), "route", item.get("triggeredBy"))
        # the same word with a different ending: "habit" is HABITS, "pushing" is PUSHED. The phrase lookup
        # already folds endings; this folds them for his word names and his routes too.
        for word in self.words:
            folded = tokens(word)
            if len(folded) == 1 and said_in_question(folded):
                add(word, "said", as_he_said_it(question, folded[0]))
        for word, said_as in self.routes:
            folded = tokens(said_as)
            if said_in_question(folded):
                add(word, "route", as_he_said_it(question, " ".join(folded)))
        for said_as, word in (extra_routes or {}).items():          # routes waiting for his yes; never used unless handed in
            if said_in_question(tokens(said_as)):
                add(word, "route", said_as)
        for hit in self.phrase_index.lookup(question):                # what he had before: every phrase of his, two words and up
            if hit.kind == "word":
                add(hit.name, "phrase", hit.phrase if len(hit.phrase.split()) < PHRASE_WORDS else as_he_said_it(question, hit.phrase))
        return list(found.values())

    # ------------------------------------------------------------ 2. choose his sentences

    def window(self, word: str, question: str, others: set[str], reached_by: str = "") -> tuple[float, list[str]]:
        """The run of his own sentences, in his order, that fits the question best, and how well it fits.
        The words that reached this word do not count as a fit by themselves."""
        mine = set(content(question)) - set(tokens(reached_by))
        trouble = any(stem(t) in TROUBLE or t in TROUBLE for t in tokens(question))
        why = bool(re.search(r"\bwhy\b", question, re.I))
        what_is = bool(WHAT_IS.search(question)) or tokens(question) == tokens(word)
        best: tuple[float, float, list[str]] | None = None
        for sentences in self.sentences[word]:
            scores = [self._fit(s, mine, word, others, trouble, why) for s in sentences]
            for i in range(len(sentences)):
                for j in range(i, min(len(sentences), i + MAX_SENTENCES)):
                    run = sentences[i:j + 1]
                    if j > i and sum(len(s.split()) for s in run) > MAX_WINDOW_WORDS:
                        break
                    fit = sum(scores[i:j + 1])
                    score = fit - 0.35 * (j - i)
                    if i > 0 and len(sentences[i].split()) <= 3:
                        continue                                      # "Regret." and "Confidence is high." lean on the line before
                    if i == 0:
                        score += 1.5 if what_is else 0.25
                    if what_is:
                        score += 0.6 * (j - i)                        # "What is FLOW?" wants the meaning from its start
                        if re.match(re.escape(word) + r"\s*(is|means|:)", sentences[i], re.I):
                            score += 2.5                              # his own defining sentence: "Momentum is the feeling of ..."
                    if i > 0 and STARTS_MID_THOUGHT.match(sentences[i]):
                        score -= 1.5                                  # it leans on the sentence before it
                    if j + 1 == len(sentences) and j > i and len(sentences[j].split()) <= 6:
                        score += 0.4                                  # his short closing line stays with the run
                    if best is None or score > best[0]:
                        best = (score, fit, run)
        return (best[1], best[2]) if best else (0.0, [])

    def _fit(self, sentence: str, mine: set[str], word: str, others: set[str], trouble: bool, why: bool) -> float:
        held = set(content(sentence)) - set(tokens(word))
        score = 0.0
        for token in held & mine:
            spread = len(self.holders.get(token, ()))
            score += 2.0 if spread <= 3 else 1.2 if spread <= 10 else 0.6
        low = sentence.lower()
        for other in others:
            if other != word and re.search(r"\b" + re.escape(other.lower()) + r"\b", low):
                score += 1.5                                         # his sentence joins two of the words he touched
        if trouble:
            score += 0.8 * min(2, sum(1 for t in tokens(sentence) if t in ANSWERS_TROUBLE))
        if why and any(t in BECAUSE for t in tokens(sentence)):
            score += 0.4
        return score

    def record_for(self, word: str, question: str, links: list[dict], used: set[str], spoken: str = ""):
        """One accepted record linked to this word that fits the question and what was just told:
        (told, exact, record). Nothing is added when no record fits."""
        mine = set(content(question))
        told_already = set(content(spoken))
        trouble = any(stem(t) in TROUBLE or t in TROUBLE for t in tokens(question))
        why = bool(re.search(r"\bwhy\b", question, re.I))
        domains = self.domains_in(question)
        ranked = []
        for link in links:
            if link.get("thumb") == 0 or link["record"] in used:
                continue
            record = self.graph.find(link["record"])
            if record is None or not self.graph.is_accepted(record):
                continue
            label = unescape_label(record.label)
            if record.connection_type in ("observed_pattern", "observed_correlation") or LOGGED in label:
                continue
            held = set(content(label))
            if held and len(held & told_already) / len(held) >= 0.6:
                continue                                              # it would repeat what was just told
            fit = 0.0
            shared = held & (mine | told_already)
            for token in shared:
                spread = self.record_spread.get(token, 1)
                weight = 1.5 if spread <= 2 else 1.0 if spread <= 5 else 0.4 if spread <= 15 else 0.1
                fit += weight if token in mine else 0.6 * weight
            in_domain = bool(domains & set(DOMAIN.findall(record.block)))    # it sits in a life domain his statement names
            answers = len({t for t in tokens(label) if t in ANSWERS_TROUBLE})
            reason = why and link.get("kind") in WHY_KINDS and in_domain      # his middle word says this record is a reason
            strong = float(record.strength or 0) >= 0.75
            continues = len(shared) >= 2 and bool(shared & told_already)      # it carries on from the sentences just told
            if not (continues or reason or (trouble and answers and in_domain and strong)):
                continue                                              # it does not belong to this moment
            if in_domain:
                fit += 1.0
            if reason:
                fit += 2.0
            if trouble:
                fit += 0.8 * min(2, answers)
            if fit < RECORD_NEEDS:
                continue
            ranked.append((round(fit, 2), 1 if link.get("thumb") == 1 else 0, float(record.strength or 0), record.leaf, label, record))
        for _fit, _thumb, _strength, _leaf, label, record in sorted(ranked, key=lambda r: r[:4], reverse=True):
            told = tell_record(label)
            if told:
                return told, label, record
        return None

    def domains_in(self, question: str) -> set[str]:
        """The life domains his statement names, by the words of his own ontology's definitions."""
        asked = set(tokens(question))
        return {domain for domain, cues in self.domain_cues.items() if asked & cues}

    def measured(self, pair: frozenset) -> tuple[str, str, str] | None:
        """What his tracked weeks measured between two life domains, in the record's own words."""
        found = self.weeks.get(pair)
        if not found:
            return None
        _strength, label, note, leaf = found
        measured = MEASURED.search(note)
        if not measured:
            return None                                              # a seed record with no measurement behind it is not told
        count = measured.group(2) or measured.group(4)
        span = measured.group(3) or measured.group(5)
        return f"{label}: {measured.group(1)}% of {count} tracked weeks, {span}.", (label + " — " + note).strip(" —"), leaf

    def domain_road(self, question: str, told: "Told") -> list[str]:
        """None of his dictionary words were reached, but his statement names a life domain of his ontology.
        His knowledge graph still holds something: the accepted records in that domain, and what his tracked
        weeks measured between that domain and the others."""
        asked = tokens(re.sub(r"\bsocial media\b", " ", question, flags=re.I))   # "social media" names neither Social nor Entertainment
        named = [(min(asked.index(c) for c in cues if c in asked), domain)
                 for domain, cues in self.domain_cues.items() if set(asked) & cues]
        named = [domain for _at, domain in sorted(named)][:2]
        if not named:
            return []
        mine = set(content(question))
        trouble = any(stem(t) in TROUBLE or t in TROUBLE for t in asked)
        blocks = []
        for domain in named:
            said = next((question[m.start():m.end()] for m in re.finditer(r"[A-Za-z’']+", question)
                         if stem(m.group(0).lower().replace("’", "'").strip("'")) in self.domain_cues[domain]), domain)
            line = f"You said {said}. Your ontology files that under {domain.capitalize()}"
            line += f": {self.domain_lines[domain]}" if self.domain_lines.get(domain) else "."
            told.parts.append(Part(line, self.domain_lines.get(domain, domain), "domain", domain))
            blocks.append(line)
        ranked = []
        for record in self.graph.records.values():
            if not self.graph.is_accepted(record) or record.connection_type in ("observed_pattern", "observed_correlation"):
                continue
            label = unescape_label(record.label)
            domains = set(DOMAIN.findall(record.block))
            if LOGGED in label or not (domains & set(named)):
                continue
            held = set(content(label))
            shared = sum(1.5 if self.record_spread.get(t, 1) <= 2 else 1.0 if self.record_spread.get(t, 1) <= 5 else 0.4
                         for t in held & mine)
            plain = set(re.findall(r"[a-z]+", label.lower()))
            if any(domain in plain for domain in named if domain != "work"):
                shared = max(shared, 1.5)                            # the record names the domain itself: "sleep"
            answers = len({t for t in tokens(label) if t in ANSWERS_TROUBLE}) if trouble and "affect" in named else 0
            both = len(domains & set(named)) == 2
            if len(named) == 2 and not both:
                continue                                              # two domains named: only a record that sits in both
            if len(named) == 1 and not (shared >= 1.5 or answers):
                continue
            fit = (shared if shared >= 1.0 else 0.0) + 0.8 * min(2, answers)    # a faint overlap does not outrank strength
            ranked.append((both, round(fit, 2), float(record.strength or 0), record.leaf, label, record))
        count = sum(len(b.split()) for b in blocks)
        for _both, _fit, _strength, _leaf, label, record in sorted(ranked, key=lambda r: r[:4], reverse=True)[:1 if len(named) == 2 else 2]:
            line = tell_record(label)
            if line and count + len(line.split()) <= MAX_TOLD_WORDS - 30:
                told.parts.append(Part(line, label, "record", "", record.leaf))
                blocks.append(line)
                count += len(line.split())
        pairs = [frozenset(named)] if len(named) == 2 and frozenset(named) in self.weeks else []
        if not pairs:                                                 # one domain, or two his weeks never measured together
            for domain in named:
                pairs += [pair for _strength, pair in self.weeks_by_domain.get(domain, [])[:2] if pair not in pairs]
        lines = []
        for pair in pairs[:3]:
            found = self.measured(pair)
            if found and count + len(found[0].split()) <= MAX_TOLD_WORDS:
                told.parts.append(Part(found[0], found[1], "weeks", "", found[2]))
                lines.append(found[0])
                count += len(found[0].split())
        if lines:
            blocks.append(" ".join(lines))
        return blocks if len(blocks) > len(named) else []

    def weeks_line(self, record, question: str) -> tuple[str, str, str] | None:
        """From a record, through its two life domains, to what his tracked weeks measured between them.
        Told only when his statement names one of the two domains."""
        pair = frozenset(DOMAIN.findall(record.block))
        found = self.weeks.get(pair)
        if not found or not (pair & self.domains_in(question)):
            return None
        _strength, label, note, leaf = found
        measured = MEASURED.search(note)
        first, second = [name.strip() for name in label.split(" and ", 1)[0:1]] + [label.split(" and ", 1)[1].split(" ")[0]] if " and " in label else ("", "")
        place = f"Your records place this in {first} and {second}. " if first and second else ""
        if measured:
            percent = measured.group(1)
            count = measured.group(2) or measured.group(4)
            span = measured.group(3) or measured.group(5)
            line = f"{place}{label}: {percent}% of {count} tracked weeks, {span}."
        else:
            line = place + finished(label) + (" " + finished(note) if note else "")
        return line, (label + " — " + note).strip(" —"), leaf

    def walk(self, word: str, question: str, touched: set[str]) -> tuple[str, list[str]] | None:
        """From one of his words to a neighbor named inside its meaning, when the neighbor's own sentences fit."""
        best = None
        for other in self.neighbors.get(word, []):
            if other in touched:
                continue
            fit, run = self.window(other, question, touched | {word})
            if not run or fit < WALK_NEEDS:
                continue
            if word in self.neighbors.get(other, []):
                fit += 2.0                                           # each names the other: MOMENTUM and KILL SWITCH
            if best is None or fit > best[0]:
                best = (fit, other, run)
        return (best[1], best[2]) if best else None

    # ------------------------------------------------------------ 3. say them back, in order

    def tell(self, question: str, reading: dict, links_for=None, extra_routes: dict[str, str] | None = None) -> Told:
        started = time.perf_counter()
        told = Told(reaches=self.reach(question, reading, extra_routes))
        told.no_meaning_yet = [w for w in (reading.get("noMeaningAddedYet") or []) if isinstance(w, str) and len(w) > 2
                               and w.lower() not in STOP and w.lower() not in ASKING and stem(w.lower()) not in ASKING]
        touched = {r.word for r in told.reaches}
        chosen = []
        what_is = bool(WHAT_IS.search(question))
        mine = set(content(question))
        for position, reach in enumerate(told.reaches):
            fit, run = self.window(reach.word, question, touched, reach.by if reach.how == "phrase" else "")
            if not run:
                continue
            in_passing = reach.how == "said" and reach.word in IN_PASSING and reach.word not in question and not what_is
            if in_passing:
                own = set(tokens(reach.word))
                shared = sum(1 for t in set(content(" ".join(run))) - own if t in mine)
                if not shared:
                    continue                                          # typed small, in passing, and his sentences share nothing else
            short = reach.how == "phrase" and len(reach.by.split()) < PHRASE_WORDS
            if short and fit < SHORT_PHRASE_NEEDS:
                continue
            rank = fit + {"said": 1.0, "route": 1.0, "phrase": 0.8}[reach.how]
            chosen.append((0 if short else 1, rank, -position, reach, run))
        if any(c[0] for c in chosen):
            chosen = [c for c in chosen if c[0]]                     # a two-word phrase speaks only when nothing stronger was reached
        chosen = [c[1:] for c in sorted(chosen, reverse=True)]
        chosen = [c for c in chosen[:MAX_WORDS_TOLD] if c[0] >= SECOND_NEEDS * chosen[0][0]]
        chosen.sort(key=lambda c: place_in(question, c[2].by))        # then in the order he said them
        blocks: list[str] = []
        spoken: set[str] = set()
        count = 0

        def room(text: str) -> bool:
            return count + len(text.split()) <= MAX_TOLD_WORDS

        def say(word: str, run: list[str], lead: str, source: str) -> bool:
            nonlocal count
            exact = " ".join(run)
            if exact in spoken:
                return False
            turned = i_to_you(exact)
            body = finished(turned) if turned is not None else f"You wrote: “{exact}”"
            if source == "meaning" and lead == f"{word}:" and word.lower() in body.lower():
                lead = ""                                             # his sentence already names the word
            block = (lead + " " if lead else "") + body
            if blocks and not room(block):
                return False
            spoken.add(exact)
            if lead:
                told.parts.append(Part(lead, lead, "tie", word))
            told.parts.append(Part(body, exact, source, word))
            blocks.append(block)
            count += len(block.split())
            return True

        # 1. his own words for what he touched, in the order he said them
        for _rank, _position, reach, run in chosen:
            if say(reach.word, run, tie(reach), "meaning"):
                step = self.step_line(reach.word, question)
                if step and room(step):
                    told.parts.append(Part(step, step, "pattern", reach.word))
                    blocks[-1] += " " + step
                    count += len(step.split())
        # 2. the walk: from his first word to the neighbor his own sentences name
        trouble = any(stem(t) in TROUBLE or t in TROUBLE for t in tokens(question))
        if len(chosen) == 1 and trouble and not what_is and not any(part.source == "pattern" for part in told.parts):
            reach = chosen[0][2]
            step = self.walk(reach.word, question, touched)
            if step and sum(len(sentence.split()) for sentence in step[1]) <= MAX_WINDOW_WORDS:
                fresh = set(content(" ".join(step[1])))
                if fresh and len(fresh & set(content(" ".join(spoken)))) / len(fresh) < 0.5:   # it adds something not yet said
                    say(step[0], step[1], f"{step[0]}:", "walk")
        # 3. his knowledge graph: one record that fits, then what his tracked weeks measured between its two life domains
        if links_for is not None and not what_is:
            for _rank, _position, reach, _run in chosen:
                found = self.record_for(reach.word, question, links_for(reach.word), set(), " ".join(spoken))
                if not found or not room(found[0]):
                    continue
                line, exact, record = found
                told.parts.append(Part(line, exact, "record", reach.word, record.leaf))
                weeks = self.weeks_line(record, question)
                if weeks and room(line + " " + weeks[0]):
                    told.parts.append(Part(weeks[0], weeks[1], "weeks", reach.word, weeks[2]))
                    line += " " + weeks[0]
                blocks.append(line)
                count += len(line.split())
                break
        if not blocks:
            blocks = self.domain_road(question, told)                # no word of his reached: his ontology and graph alone
        told.text = "\n\n".join(blocks)
        told.ms = round((time.perf_counter() - started) * 1000, 2)
        return told

    def step_line(self, word: str, question: str) -> str:
        """His ontology: where this word sits in the Adam Pattern, what is before it and after it."""
        names = [name for _n, name, _d in self.steps]
        if word not in names:
            return ""
        if word in ("CONTEXT", "KILL SWITCH") and not re.search(r"\b(pattern|step)\b", question, re.I):
            return ""                                                # these two words live outside the pattern too
        at = names.index(word)
        around = []
        if at > 0:
            around.append(f"after {names[at - 1]}")
        if at + 1 < len(names):
            around.append(f"before {names[at + 1]}")
        return f"In the Adam Pattern it is step {at + 1} of {len(names)}, " + " and ".join(around) + "."


def records_told(told: Told, graph: Graph) -> list[dict]:
    """The accepted records a telling used, in the shape the rows on the screen take."""
    rows, seen = [], set()
    for part in told.parts:
        record = graph.find(part.record) if part.record else None
        if record is None or record.leaf in seen or not graph.is_accepted(record):
            continue
        seen.add(record.leaf)
        rows.append({"id": record.uri, "leaf": record.leaf, "quote": unescape_label(record.label), "why": "",
                     "strength": record.strength, "accepted_at": record.accepted_at,
                     "connection_type": record.connection_type})
    return rows


def tie(reach: Reach) -> str:
    """One plain line for how his statement led to his word. Routes use his own rule from routes.txt:
    "A route says: when Adam says any of these, he is talking about this word." """
    if reach.how == "route":
        return f"When you say {reach.by}, you are talking about {reach.word}:"
    if reach.how == "phrase" and len(reach.by.split()) >= PHRASE_WORDS:
        return f"“{reach.by}” is in your {reach.word}:"
    return f"{reach.word}:"


def place_in(question: str, said: str) -> int:
    at = question.lower().find(said.lower())
    return at if at >= 0 else len(question)


def load_routes(path: Path | None, known: set[str]) -> list[tuple[str, str]]:
    """His routes.txt: (his word, one way he says it). "A route says: when Adam says any of these, he is
    talking about this word." The first name on each line is the word itself."""
    path = path or NUCLEUS_FILES["routes"]
    if not path.exists():
        return []
    routes = []
    for line in dictionary_module.load_meanings(path):
        if line.word not in known:
            continue
        for said_as in [part.strip() for part in line.text.split(",")][1:]:
            if said_as:
                routes.append((line.word, said_as))
    return routes


def load_domain_cues(root: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    """His ontology's own definition of each life domain, as the words that name it.
    Affect/Affect.md: "Emotions, mood, emotional regulation, and psychological state."
    upper/bfo-bridge.ttl: "Affect ... records felt qualities or states" - so felt, feel, feeling name Affect."""
    cues: dict[str, set[str]] = {}
    lines: dict[str, str] = {}
    for domain in LIFE_DOMAINS:
        words = {domain}
        note = root / domain.capitalize() / f"{domain.capitalize()}.md"
        if note.exists():
            lines_ = note.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines_):
                if line.startswith("# "):
                    definition = next((l for l in lines_[index + 1:] if l.strip()), "")
                    lines[domain] = definition.strip()
                    words |= {t for t in tokens(definition) if t not in STOP and t not in PLAIN and len(t) > 2}
                    break
        cues[domain] = words
    cues["affect"] |= {"felt", "feel", "feeling"}
    seen: dict[str, int] = {}
    for words in cues.values():
        for word in words:
            seen[word] = seen.get(word, 0) + 1
    return {domain: {w for w in words if seen[w] == 1} for domain, words in cues.items()}, lines


def tell_record(label: str) -> str | None:
    """A record, said to him. A record that is his own quoted words is turned from "I"; a record about
    him is turned from "Adam". None when it cannot be turned with nothing changed but the person."""
    own = HIS_WORDS_RECORD.match(label)
    if own:
        said = i_to_you(own.group(1))
        return finished(said) if said and same_words(own.group(1), said) else None
    said = adam_to_you(label)
    return finished(said) if said and same_words(label, said) else None


def finished(sentence: str) -> str:
    return sentence if re.search(r"[.!?…]['\"”’)]*$", sentence) else sentence + "."


def as_he_said_it(question: str, stemmed: str) -> str:
    """The words as he typed them in the question, for a phrase the lookup holds in folded form."""
    wanted = stemmed.split()
    spans = [(m.start(), m.end()) for m in re.finditer(r"[A-Za-z’']+", question)]
    folded = [stem(question[a:b].lower().replace("’", "'").strip("'")) for a, b in spans]
    for i in range(len(folded) - len(wanted) + 1):
        if folded[i:i + len(wanted)] == wanted:
            return question[spans[i][0]:spans[i + len(wanted) - 1][1]]
    return stemmed


def load_pattern(path: Path) -> list[tuple[int, str, str]]:
    """The steps of The Adam Pattern from his ontology file, in order: (number, his dictionary word, description)."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    steps = []
    for block in re.findall(r":Step\d+ a :Step ;(.*?)\n\n", text, re.S):
        label = re.search(r'rdfs:label "([^"]+)"', block)
        order = re.search(r":order (\d+)", block)
        description = re.search(r':description "([^"]+)"', block)
        if label and order:
            name = label.group(1).upper().replace("CREATE KILL SWITCH", "KILL SWITCH")
            steps.append((int(order.group(1)), name, description.group(1) if description else ""))
    return sorted(steps)


def build() -> Narrator:
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    return Narrator(meanings, graph)


def main(argv: list[str]) -> int:
    question = " ".join(argv).strip()
    if not question:
        print("Write a question after narrative.", file=sys.stderr)
        return 2
    from .store import Store
    narrator = build()
    reading = dictionary_module.brief(question)
    store = Store()
    told = narrator.tell(question, reading, store.links_for)
    for reach in told.reaches:
        print(f"[{reach.how}] {reach.by} -> {reach.word}")
    print()
    print(told.text or "(none of his words reached)")
    print(f"\n{told.ms} ms, no model. no meaning added yet: {', '.join(told.no_meaning_yet)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
