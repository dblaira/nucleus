"""Links between his words and his records. Found once in the background, kept, his to thumb.

Adam, 2026-09-11: "we're not trying to answer questions. Trying to paint accurate pictures from the
information given." The picture at question time is painted by code from saved links: his words, his
records, their strengths and dates. The model's only job is to find links in the background.

Word matching alone paints wrong pictures (measured 2026-09-11): the momentum records never contain
the word FLOW. The link FLOW <-> momentum is meaning, and it lives here.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from . import gate as gate_module
from . import model as model_module
from .compact import compact_records
from .gate import FIRST_LINE, one_sentence, unescape_label
from .graph import Graph, load_graph
from .kinds import is_kind, load_kinds
from .store import Store

LINKS_SCHEMA = Path(__file__).with_name("links.schema.json")
KINDS_SCHEMA = Path(__file__).with_name("kinds.schema.json")

LINK_CONTRACT = """You are reading Adam Blair's accepted records (one per line: id | type | strength | accepted | label | note)
and one word from his dictionary with his own meaning of it. Find every record that connects to this word's
meaning. Return exactly one JSON object and nothing else:
{"word": "<the word>", "records": [{"id": "<record id>", "quote": "<a verbatim excerpt of that record's label>", "kind": "<the middle word>", "why": "<one sentence: how this record connects to the word's meaning>"}]}
The middle word completes the sentence "<the word> <middle word> <the record>". Adam's words, his note:
"The two things are not enough. The middle must say what kind of connection exists." Choose it from this
list only, copied exactly; code refuses anything else:
__KINDS__
A quote is copied character for character. Each why is one sentence, no quotation inside it, no line break.
If no record connects, return {"word": "<the word>", "records": []}.
"""

KIND_CONTRACT = """Below are one word from Adam Blair's dictionary, his own meaning of it, and records of his that are already
linked to that word. For each record give the middle word that completes the sentence
"<the word> <middle word> <the record>". Adam's words, his note: "The two things are not enough. The middle
must say what kind of connection exists." Choose from this list only, copied exactly; code refuses anything else:
__KINDS__
Return exactly one JSON object and nothing else:
{"word": "<the word>", "kinds": [{"id": "<record id>", "kind": "<the middle word>"}]}
"""


def _with_kinds(contract: str, kinds: list[str]) -> str:
    return contract.replace("__KINDS__", "\n".join(f"- {k}" for k in kinds))

# PROPOSAL, not a rule of record (adams-authority): how a painted picture picks one of Adam's three lines.
# aligned:   every touched word has links, and together they reach at least 3 records
# not_sure:  some links, fewer than that, or a touched word with no links yet
# dont_know: no touched words, or no links for any of them
ALIGNED_RECORDS = 3


@dataclass
class Picture:
    answer: str
    text: str
    words: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    touched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def touched_words(reading: dict, hits, known: set[str]) -> list[str]:
    words: list[str] = []
    for item in reading.get("heSaidTheWordItself") or []:
        word = item.get("word") if isinstance(item, dict) else None
        if isinstance(word, str) and word in known and word not in words:
            words.append(word)
    for hit in hits or []:
        if hit.kind == "word" and hit.name in known and hit.name not in words:
            words.append(hit.name)
    return words


def paint(question: str, reading: dict, hits, store: Store, graph: Graph, meanings) -> Picture | None:
    """The picture from saved links. None when no word of his in the question has links yet."""
    known = {m.word for m in meanings}
    touched = touched_words(reading, hits, known)
    if not touched:
        return None
    words: list[dict] = []
    records: list[dict] = []
    seen: set[str] = set()
    missing: list[str] = []
    for word in touched:
        links = [l for l in store.links_for(word) if l["thumb"] != 0]
        if not links:
            missing.append(word)
            continue
        words.append({"word": word, "why": f"you said {word}", "meanings": [m.text for m in dictionary_module.meanings_for(meanings, word)]})
        for link in links:
            record = graph.find(link["record"])
            if record is None or not graph.is_accepted(record) or record.leaf in seen:
                continue
            seen.add(record.leaf)
            # a why written while answering an earlier question is about that question, not this one; only a
            # why from the background pass (about the word itself) is shown under a painted picture
            why = link["why"] if str(link["source"]).startswith("links:") else ""
            records.append({"id": record.uri, "leaf": record.leaf, "quote": link["quote"], "why": why,
                            "strength": record.strength, "accepted_at": record.accepted_at, "connection_type": record.connection_type,
                            "link_word": word, "kind": link.get("kind")})
    if not words:
        return None
    records.sort(key=lambda r: -float(r["strength"] or 0))
    if not missing and len(records) >= ALIGNED_RECORDS:
        answer = "aligned"
    else:
        answer = "not_sure"
    text = gate_module.compose(answer, words, records, [])
    return Picture(answer=answer, text=text, words=words, records=records, touched=touched, missing=missing)


def seed_from_answers(store: Store, graph: Graph) -> int:
    """Every word-to-record pair the model already found while answering, kept as a link."""
    added = 0
    rows = store.connection.execute(
        "SELECT a.question_id, a.reply_json, m.provider, m.model FROM answers a LEFT JOIN model_calls m ON m.question_id = a.question_id"
        " WHERE a.status = 'answered' AND a.reply_json IS NOT NULL GROUP BY a.question_id"
    ).fetchall()
    for question_id, reply_json, provider, model in rows:
        try:
            payload = json.loads(reply_json)
        except json.JSONDecodeError:
            continue
        words = [w.get("word") for w in payload.get("words") or [] if isinstance(w, dict)]
        for item in payload.get("records") or []:
            record = graph.find(str(item.get("id"))) if isinstance(item, dict) else None
            if record is None:
                continue
            for word in words:
                if isinstance(word, str) and store.add_link(word, record.leaf, item.get("quote", ""), item.get("why", ""),
                                                          question_id, provider or "?", model or "?"):
                    added += 1
    return added


def find_links(word: str, store: Store, graph: Graph, meanings, model_call=None) -> int:
    """One background call for one word. Saves what the graph confirms. Returns links added."""
    model_call = model_call or (lambda p: model_module.call(p, schema=LINKS_SCHEMA))
    texts = [m.text for m in dictionary_module.meanings_for(meanings, word)]
    kinds = load_kinds()
    prompt = (
        "===== accepted records =====\n" + compact_records(graph)
        + f"\n===== the word =====\n{word}\n" + "\n".join(f"Adam's meaning: {t}" for t in texts)
        + "\n\n===== the contract =====\n" + _with_kinds(LINK_CONTRACT, kinds)
    )
    started = time.time()
    reply = model_call(prompt)
    store.save_model_call(f"links:{word}", reply.provider, reply.model, prompt, started, reply.text, True, None)
    payload = json.loads(model_module._extract_json(reply.text))
    added = 0
    for item in payload.get("records") or []:
        record = graph.find(str(item.get("id"))) if isinstance(item, dict) else None
        quote = item.get("quote") if isinstance(item, dict) else None
        if record is None or not graph.is_accepted(record) or not isinstance(quote, str) or not graph.quote_is_in(record, quote):
            continue
        try:
            why = one_sentence(item.get("why"), f"why for {record.leaf}")
        except gate_module.Refused:
            continue
        kind = item.get("kind").strip() if is_kind(item.get("kind"), kinds) else None   # code refuses any word not on his list
        if store.add_link(word, record.leaf, quote, why, f"links:{word}", reply.provider, reply.model, kind=kind):
            added += 1
    store.mark_word_searched(word, model_module.nucleus_hash(compact_records(graph)))
    return added


def find_kinds(word: str, store: Store, graph: Graph, meanings, model_call=None) -> int:
    """One background call for one word: the middle word for each of its links that has none. Returns kinds set."""
    model_call = model_call or (lambda p: model_module.call(p, schema=KINDS_SCHEMA))
    kinds = load_kinds()
    links = [l for l in store.links_for(word) if l["kind"] is None and l["thumb"] != 0]
    if not links:
        return 0
    lines = []
    for l in links:
        r = graph.find(l["record"])
        if r is not None:
            lines.append(f"{r.leaf} | {r.connection_type} | {r.strength} | {unescape_label(r.label)}")
    texts = [m.text for m in dictionary_module.meanings_for(meanings, word)]
    prompt = (
        f"===== the word =====\n{word}\n" + "\n".join(f"Adam's meaning: {t}" for t in texts)
        + "\n\n===== his records linked to it (id | type | strength | label) =====\n" + "\n".join(lines)
        + "\n\n===== the contract =====\n" + _with_kinds(KIND_CONTRACT, kinds)
    )
    started = time.time()
    reply = model_call(prompt)
    store.save_model_call(f"kinds:{word}", reply.provider, reply.model, prompt, started, reply.text, True, None)
    payload = json.loads(model_module._extract_json(reply.text))
    wanted = {l["record"] for l in links}
    done = 0
    for item in payload.get("kinds") or []:
        if not isinstance(item, dict):
            continue
        record = graph.find(str(item.get("id")))
        if record is None or record.leaf not in wanted or not is_kind(item.get("kind"), kinds):
            continue
        store.set_kind(word, record.leaf, item.get("kind").strip())
        done += 1
    return done


def kinds_pass(limit: int | None = None, model_call=None, shard: tuple[int, int] = (0, 1)) -> list[tuple[str, int, float]]:
    """Every word with links that have no middle word yet, one call each. shard=(i, n) takes every n-th word."""
    store = Store()
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    todo = [w for i, w in enumerate(store.words_with_unkinded_links()) if i % shard[1] == shard[0]]
    results = []
    for word in todo[:limit] if limit else todo:
        t = time.time()
        try:
            done = find_kinds(word, store, graph, meanings, model_call)
        except Exception as error:
            store.save_model_call(f"kinds:{word}", "?", "?", "", t, None, False, str(error))
            done = -1
        results.append((word, done, round(time.time() - t, 1)))
        print(f"{word:<28} {done:3d} kinds  {time.time()-t:5.1f} s", flush=True)
    return results


def background_pass(limit: int | None = None, model_call=None) -> list[tuple[str, int, float]]:
    """Every word of his that has not been searched yet, one call each, in the background."""
    store = Store()
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    searched = store.searched_words(model_module.nucleus_hash(compact_records(graph)))
    todo = []
    for m in meanings:
        if m.word not in searched and m.word not in todo:
            todo.append(m.word)
    results = []
    for word in todo[:limit] if limit else todo:
        t = time.time()
        try:
            added = find_links(word, store, graph, meanings, model_call)
        except Exception as error:
            store.save_model_call(f"links:{word}", "?", "?", "", t, None, False, str(error))
            added = -1
        results.append((word, added, round(time.time() - t, 1)))
        print(f"{word:<28} {added:3d} links  {time.time()-t:5.1f} s", flush=True)
    return results


def main(argv: list[str]) -> int:
    if argv and argv[0] == "seed":
        store = Store()
        graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
        print("links kept from saved answers:", seed_from_answers(store, graph))
        return 0
    limit = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else None
    if argv and argv[0] == "pass":
        results = background_pass(limit)
        print(f"words searched: {len(results)}, links added: {sum(a for _, a, _ in results if a > 0)}")
        results = kinds_pass(limit)
        print(f"words kinded: {len(results)}, kinds set: {sum(a for _, a, _ in results if a > 0)}")
        return 0
    if argv and argv[0] == "kinds":
        shard = (0, 1)
        if len(argv) > 1 and "/" in argv[1]:
            i, n = argv[1].split("/")
            shard, limit = (int(i), int(n)), None
        results = kinds_pass(limit, shard=shard)
        print(f"words kinded: {len(results)}, kinds set: {sum(a for _, a, _ in results if a > 0)}")
        return 0
    print("usage: python -m nucleus.links seed | pass [N] | kinds [N]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
