"""The boxes he left blank in a form, filled at night from his records. Every night at 02:20, as part of the night
run (nucleus/night.py), on every form he left a box blank in. Adam, 2026-10-07, asked "Run this every night on every
form you leave blank: yes or no?": "yes".

Adam, 2026-10-07: "they could also be used to answer the questions for me and to come up with better solutions to
fill in the gaps when needed." Adam, 2026-10-01: "allow AI to be used on a nightly basis, rather than in the actual
moment of use for the user."

One model call for one entry: his records, his dictionary, his entry, the form, the questions he left blank. For each
blank box the model names one record or dictionary word of his, quotes it word for word, and says in one or two
sentences what it says about the box's question. Code checks every piece; a box that fails is left blank.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from . import model as model_module
from .compact import compact_records
from .gate import unescape_label
from .graph import Graph, load_graph
from .night import TIMEOUT_SECONDS, TOLD_TO
from .store import Store

SCHEMA = Path(__file__).with_name("boxes.schema.json")
MAX_SENTENCES = 2

CONTRACT = """Above are Adam Blair's accepted records (one per line: id | type | strength | accepted | label | note), his
dictionary (one per line: WORD = his meaning, verbatim), one entry of his, and the form he picked with the questions
he left blank.

Adam's own words, verbatim: "they could also be used to answer the questions for me and to come up with better
solutions to fill in the gaps when needed."

For each blank question, return one box. Return exactly one JSON object and nothing else:
{"boxes": [{"prompt": "<the blank question, copied exactly>",
            "brings_in": "<a record id from the list above, or one of his dictionary words exactly as written>",
            "quote": "<words copied exactly from that record's label or note, or from that dictionary meaning>",
            "answer": "<one or two sentences to Adam as you: what the quote says about this question, for his entry>"}]}

Rules, checked by code after you answer:
- prompt is one of the blank questions, exactly. One box per blank question, in order.
- brings_in is copied exactly. quote is inside that record or that meaning, character for character.
- answer is at most two sentences, in plain words, built only from the quote and his entry. Add no facts about him.
- Adam's rule, verbatim: "No advice is given.  No next steps are suggested." Do not tell him what to do.
"""

_SENTENCE = re.compile(r"[.!?](?:\s|$)")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", unescape_label(text or "")).strip()


def blank_boxes(theme: dict | None) -> list[dict]:
    if not theme or not isinstance(theme.get("fields"), list):
        return []
    return [f for f in theme["fields"] if isinstance(f, dict) and not (f.get("answer") or "").strip() and not f.get("night")]


def build_prompt(entry: str, theme: dict, graph: Graph, meanings) -> str:
    dictionary = "\n".join(f"{m.word} = {m.text}" for m in meanings)
    filled = "\n".join(f"- {f['prompt']}\n  {f['answer']}" for f in theme["fields"] if (f.get("answer") or "").strip()) or "(none)"
    blank = "\n".join(f"- {f['prompt']}" for f in blank_boxes(theme))
    return ("===== accepted records =====\n" + compact_records(graph)
            + "\n===== his dictionary =====\n" + dictionary
            + "\n\n===== his entry =====\n" + (entry or "(only the form)")
            + "\n\n===== the form he picked =====\n" + theme["name"]
            + "\n\n===== boxes he filled =====\n" + filled
            + "\n\n===== boxes he left blank =====\n" + blank
            + "\n\n===== the contract =====\n" + CONTRACT)


def _his_text(brings_in: str, graph: Graph, meanings) -> str | None:
    """Everything of his that a quote may be copied from, or None when brings_in is not his."""
    if brings_in in {m.word for m in meanings}:
        return " \n ".join(m.text for m in dictionary_module.meanings_for(meanings, brings_in))
    record = graph.find(brings_in)
    if record is None or not graph.is_accepted(record):
        return None
    return unescape_label(record.label) + " \n " + (getattr(record, "note", "") or "") + " \n " + (record.block or "")


def check(payload: object, theme: dict, graph: Graph, meanings) -> tuple[dict[str, dict], str | None]:
    """The fills that pass, by prompt. A box the model got wrong is left blank; nothing else is refused for it."""
    items = payload.get("boxes") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}, "no boxes"
    blank = {f["prompt"] for f in blank_boxes(theme)}
    fills: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict) or item.get("prompt") not in blank or item["prompt"] in fills:
            continue
        brings_in, quote, answer = str(item.get("brings_in", "")), _plain(str(item.get("quote", ""))), str(item.get("answer", "")).strip()
        source = _his_text(brings_in, graph, meanings)
        if source is None or not quote or _plain(quote.lower()) not in _plain(source.lower()):
            continue                                                      # not his, or not his words as written
        if not answer or "\n" in answer or len(_SENTENCE.findall(answer)) > MAX_SENTENCES or TOLD_TO.search(answer):
            continue
        fills[item["prompt"]] = {"brings_in": brings_in, "quote": quote, "answer": answer}
    return fills, None if fills else "every box failed the checks"


def fill(question_id: str, store: Store, graph: Graph | None = None, meanings=None, model_call=None) -> tuple[int, str | None]:
    """Fill the blank boxes of one entry. Returns how many boxes were filled and, if none, why."""
    graph = graph or load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = meanings or dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    question = store.question(question_id)
    theme = (question or {}).get("theme")
    if not blank_boxes(theme):
        return 0, "no blank boxes"
    model_call = model_call or (lambda p: model_module.call_codex_fresh(p, timeout=TIMEOUT_SECONDS, schema=SCHEMA))
    prompt = build_prompt(theme.get("question") or "", theme, graph, meanings)
    started = time.time()
    try:
        reply = model_call(prompt)
    except Exception as error:
        store.save_model_call(f"boxes:{question_id}", "?", "?", prompt, started, None, False, str(error))
        return 0, f"the model call failed: {error}"
    try:
        payload = json.loads(model_module._extract_json(reply.text))
    except json.JSONDecodeError:
        payload = None
    fills, reason = check(payload, theme, graph, meanings)
    store.save_model_call(f"boxes:{question_id}", reply.provider, reply.model, prompt, started, reply.text, reason is None, reason)
    for field in theme["fields"]:
        if field.get("prompt") in fills:
            field["night"] = {**fills[field["prompt"]], "run_at": time.time(), "provider": reply.provider, "model": reply.model}
    if fills:
        store.set_theme(question_id, theme)
    return len(fills), reason


SINCE = time.mktime((2026, 10, 7, 0, 0, 0, 0, 0, -1))      # the forms reached his app on 2026-10-07


def run(store: Store | None = None, model_call=None, only: str | None = None) -> list[tuple[str, int, str | None]]:
    """Every entry of his with a form and a blank box: one call each. A box already filled is never touched."""
    store = store or Store()
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    done = []
    for entry in store.entries_with_forms(SINCE):
        if only and entry["id"] != only:
            continue
        if not blank_boxes(entry["theme"]):
            continue
        count, reason = fill(entry["id"], store, graph, meanings, model_call)
        done.append((entry["question"], count, reason))
    return done


def main(argv: list[str]) -> int:
    store = Store(Path(argv[argv.index("--store") + 1])) if "--store" in argv else Store()
    only = argv[argv.index("--question") + 1] if "--question" in argv else None
    for question, count, reason in run(store, only=only):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {count} boxes filled | {reason or 'saved'} | {question[:90]}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
