"""What the night run does for the middle answer.

Adam, 2026-10-03: "The response, "There is some relationship, but not enough to justify causation," will be followed by
requesting more information, which will be logged and then analyzed by the LLM during the night run.  During the
overnight run, all middle responses will use AI to generate options that might move the situation further down the
spectrum from correlation to causation.   Three options are a good starting point.  I will set the criteria for the
three options later, but they will all align in attitude and speed. But they offer different ways to broaden my
perspective and create better opportunities for causation. What this means is that thinking bigger is also thinking
broader because it brings in other relationships that are probably affecting the predictability of a situation."

One model call for each middle answer of his that has no options yet, or has more information logged since its last
options. The model reads his accepted records and his dictionary, his entry, what the engine told him, and what he
logged. It returns three options. Code checks each one: what it brings in is a real accepted record or a real
dictionary word of his, shown in his own words; one sentence for what it may be doing; one sentence for the
information that would show it. Anything else is refused and nothing is saved for that answer that night.

The criteria for the three are his to set. Nothing here sets them. Every number and list that decides something
below is a PROPOSAL, not a rule of record (adams-authority).
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from . import gate as gate_module
from . import model as model_module
from .compact import compact_records
from .explain import ADVICE

# ADVICE catches the word "consider" anywhere. On 2026-10-07 it threw away all three options for one answer
# because one sentence said "when you consider going to the doctor", which tells him nothing to do. Here the
# word counts as advice only when it is told to him: at the start of a sentence, or after "you should".
TOLD_TO = re.compile(r"(?:^|[.!?]\s+)(consider|try)\b|\b(you should|try to|next step|recommend|it would help|make sure|you need to|you must|you could)\b", re.I)
from .gate import one_sentence, unescape_label
from .graph import Graph, load_graph
from .narrative import finished, tell_record
from .person import i_to_you, same_words, split_sentences
from .store import Store

OPTIONS_SCHEMA = Path(__file__).with_name("options.schema.json")
HOW_MANY = 3                                    # his words: "Three options are a good starting point."
# PROPOSAL: whose middle answers the night run works on. His own entries, from the day he defined this.
SINCE = datetime(2026, 10, 2).timestamp()
NOT_FROM = ("grade", "cli", "cli-twopass")      # the daily grade and the command line are not his entries
TIMEOUT_SECONDS = 240.0
TITLE = gate_module.POSSIBILITY_TITLE           # the box under the middle answer, in his word of September

CONTRACT = """Above are Adam Blair's accepted records (one per line: id | type | strength | accepted | label | note), his
dictionary (one per line: WORD = his meaning, verbatim), one entry of his, what his engine answered, and any more
information he gave afterwards. The engine gave his middle answer: "There is some relationship, but not enough to
justify causation."

Adam's own words for what happens now, verbatim: "During the overnight run, all middle responses will use AI to
generate options that might move the situation further down the spectrum from correlation to causation.   Three
options are a good starting point.  I will set the criteria for the three options later, but they will all align in
attitude and speed. But they offer different ways to broaden my perspective and create better opportunities for
causation. What this means is that thinking bigger is also thinking broader because it brings in other
relationships that are probably affecting the predictability of a situation. I'm confused and talking about
something that doesn't quite align with my beliefs because I've narrowed my focus too much and haven't considered
enough variables that could be causing odd results from different behaviors."

Return exactly three options. Each option brings in one other relationship of his, from the records or the
dictionary above, that the answer did not use and that is probably affecting the situation in his entry. A
different one each time, so the three broaden his view in three different ways. If he gave more information, the
three take it into account.

Return exactly one JSON object and nothing else:
{"options": [{"brings_in": "<a record id from the list above, or one of his dictionary words exactly as written>",
              "proposed": "<one sentence, to Adam as you: how this relationship may be affecting the situation in his entry>",
              "would_show": "<one sentence that names the information from him that would show whether it does, and nothing else>"}]}

Rules, checked by code after you answer:
- brings_in is copied exactly. It is not a record or a word the answer already used. The three are different.
- proposed and would_show are each exactly one sentence, in plain words, with no quotation inside and no line break.
- would_show starts with the information itself. It does not contain the words "would show".
- Adam's rule, verbatim: "No advice is given.  No next steps are suggested." Do not tell him what to do. An option is
  another relationship to look at, not an instruction.
- Speak only from the records, the dictionary, his entry and his more information. Add no facts about him.
"""


def used_by(reply_json: str | None) -> set[str]:
    """The records and words the answer already showed him."""
    try:
        payload = json.loads(reply_json or "{}")
    except json.JSONDecodeError:
        return set()
    used = {str(w.get("word")) for w in payload.get("words") or [] if isinstance(w, dict)}
    return used | {str(r.get("id")) for r in payload.get("records") or [] if isinstance(r, dict)}


def build_prompt(question: str, answer_text: str, paragraph: str, more: list[dict], graph: Graph, meanings) -> str:
    dictionary = "\n".join(f"{m.word} = {m.text}" for m in meanings)
    given = "\n".join(f"- {entry['text']}" for entry in more) or "(none yet)"
    return (
        "===== accepted records =====\n" + compact_records(graph)
        + "\n===== his dictionary =====\n" + dictionary
        + "\n\n===== his entry =====\n" + question
        + "\n\n===== what his engine answered =====\n" + answer_text + ("\n\n" + paragraph if paragraph else "")
        + "\n\n===== more information he gave afterwards =====\n" + given
        + "\n\n===== the contract =====\n" + CONTRACT
    )


def shown(brings_in: str, graph: Graph, meanings) -> str | None:
    """What an option brings in, in his own words, said to him. None when it is not his."""
    known = {m.word for m in meanings}
    if brings_in in known:
        first = split_sentences(dictionary_module.meanings_for(meanings, brings_in)[0].text)[:1]
        turned = i_to_you(first[0]) if first else None
        if turned and same_words(first[0], turned):
            return turned if brings_in.lower() in turned.lower() else f"{brings_in}: {finished(turned)}"
        return brings_in
    record = graph.find(brings_in)
    if record is None or not graph.is_accepted(record):
        return None
    label = unescape_label(record.label)
    return tell_record(label) or f"“{label}”"


def check(payload: object, graph: Graph, meanings, used: set[str]) -> tuple[list[dict], str | None]:
    """The three options, or none and the reason they are refused."""
    items = payload.get("options") if isinstance(payload, dict) else None
    if not isinstance(items, list) or len(items) != HOW_MANY:
        return [], f"not exactly {HOW_MANY} options"
    options, seen = [], set()
    for item in items:
        brings_in = item.get("brings_in") if isinstance(item, dict) else None
        if not isinstance(brings_in, str):
            return [], "an option brings in nothing"
        record = graph.find(brings_in)
        key = record.leaf if record is not None else brings_in
        if key in seen:
            return [], f"{key} is brought in twice"
        if key in used or brings_in in used:
            return [], f"{key} is already in the answer"
        told = shown(brings_in, graph, meanings)
        if told is None:
            return [], f"{brings_in!r} is neither an accepted record nor one of his words"
        try:
            proposed = one_sentence(item.get("proposed"), "an option's proposed sentence")
            would_show = one_sentence(item.get("would_show"), "an option's would_show sentence")
        except gate_module.Refused as error:
            return [], str(error)
        if TOLD_TO.search(proposed) or TOLD_TO.search(would_show):
            return [], "advice"
        if "would show" in would_show.lower():
            return [], "would_show repeats its own label"
        seen.add(key)
        options.append({"brings_in": key, "shown": told, "proposed": proposed, "would_show": would_show})
    return options, None


def options_for(waiting: dict, store: Store, graph: Graph, meanings, model_call=None) -> tuple[list[dict], str | None]:
    """One model call for one middle answer. Saves the three when code accepts them."""
    model_call = model_call or (lambda p: model_module.call_codex_fresh(p, timeout=TIMEOUT_SECONDS, schema=OPTIONS_SCHEMA))
    explanation = store.explanation(waiting["id"]) or {}
    prompt = build_prompt(waiting["question"], waiting["text"] or "", explanation.get("text") or "",
                          store.more_information(waiting["id"]), graph, meanings)
    started = time.time()
    try:
        reply = model_call(prompt)
    except Exception as error:                                         # the door is shut tonight; tried again tomorrow night
        store.save_model_call(f"night:{waiting['id']}", "?", "?", prompt, started, None, False, str(error))
        return [], f"the model call failed: {error}"
    try:
        payload = json.loads(model_module._extract_json(reply.text))
    except json.JSONDecodeError:
        payload = None
    options, reason = check(payload, graph, meanings, used_by(waiting.get("reply_json")))
    store.save_model_call(f"night:{waiting['id']}", reply.provider, reply.model, prompt, started, reply.text, reason is None, reason)
    if reason is None:
        store.save_options(waiting["id"], options, reply.provider, reply.model)
    return options, reason


def run(store: Store | None = None, model_call=None, only: str | None = None) -> list[tuple[str, int, str | None]]:
    store = store or Store()
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    done = []
    for waiting in store.middle_answers_waiting(SINCE, NOT_FROM):
        if only and waiting["id"] != only:
            continue
        options, reason = options_for(waiting, store, graph, meanings, model_call)
        done.append((waiting["question"], len(options), reason))
    return done


def block(option: dict) -> str:
    """One option as his screen shows it: what it brings in, what it may be doing, the information that would show it."""
    return "\n".join([option["shown"], option["proposed"], f"would show: {option['would_show']}"])


def with_options(text: str, options: list[dict]) -> str:
    """The middle answer with the night's options under it, in the box his app already draws."""
    if not options:
        return text
    blocks = "\n\n".join(block(option) for option in options)
    if f"\n{TITLE}\n" in text + "\n":
        return text + "\n\n" + blocks
    return text + f"\n\n{TITLE}\n\n" + blocks


def main(argv: list[str]) -> int:
    only = argv[argv.index("--question") + 1] if "--question" in argv else None
    store = Store(Path(argv[argv.index("--store") + 1])) if "--store" in argv else Store()
    started = time.time()
    done = run(store, only=only)
    for question, count, reason in done:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {count} options | {reason or 'saved'} | {question[:90]}")
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} middle answers worked on: {len(done)}, in {round(time.time() - started, 1)} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
