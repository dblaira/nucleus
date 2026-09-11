"""The path of one question. Six steps. One model call. The gate decides."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from . import gate as gate_module
from . import model as model_module
from . import phrases as phrases_module
from . import prompt as prompt_module
from .graph import load_graph
from .store import Store

STEP_QUESTION = "1 question in"
STEP_DICTIONARY = "2 dictionary reads it"
STEP_PHRASES = "3 your phrases found"
STEP_NUCLEUS = "4 nucleus read whole"
STEP_MODEL = "5 one model call"
STEP_GATE = "6 the gate"
STEP_ANSWER = "7 answer out"


@dataclass
class Result:
    question_id: str
    question: str
    status: str            # answered | stopped | refused | failed
    answer: str | None = None
    text: str = ""
    reason: str = ""
    words: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    possibility: list[dict] = field(default_factory=list)
    reading: dict | None = None
    phrases: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    seconds: float = 0.0
    provider: str | None = None
    model: str | None = None
    bytes_sent: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def ask(question: str, store: Store | None = None, surface: str = "cli",
        model_call: Callable[[str], model_module.ModelReply] | None = None,
        brief: Callable[[str], dict] | None = None, question_id: str | None = None) -> Result:
    store = store or Store()
    model_call = model_call or model_module.call
    brief = brief or dictionary_module.brief
    started_all = time.time()

    question_id = question_id or store.new_question(question, surface)
    store.start_step(question_id, STEP_QUESTION)
    store.finish_step(question_id, STEP_QUESTION)

    def finish(result: Result) -> Result:
        result.steps = store.steps(question_id)
        result.seconds = round(time.time() - started_all, 3)
        return result

    # 2. the dictionary reads the question with its own program
    store.start_step(question_id, STEP_DICTIONARY)
    try:
        reading = brief(question)
    except Exception as error:
        store.finish_step(question_id, STEP_DICTIONARY, note=f"failed: {error}")
        store.save_answer(question_id, "failed", None, "", None, None, str(error))
        return finish(Result(question_id, question, "failed", reason=f"The dictionary could not read the question: {error}"))
    outcome = reading.get("outcome")
    store.finish_step(question_id, STEP_DICTIONARY, note=f"outcome {outcome}")
    if outcome == "stopped":
        text = str(reading.get("stopped") or "stopped")
        store.save_answer(question_id, "stopped", None, text, json.dumps(reading, ensure_ascii=False), None, None)
        return finish(Result(question_id, question, "stopped", text=text, reason=text, reading=reading))
    if outcome == "ask":
        text = str(reading.get("mustAskFirst") or "ask")
        store.save_answer(question_id, "stopped", None, text, json.dumps(reading, ensure_ascii=False), None, None)
        return finish(Result(question_id, question, "stopped", text=text, reason=text, reading=reading))

    # 3. his phrases, looked up by code. Meaning with meaning.
    store.start_step(question_id, STEP_PHRASES)
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    hits = phrases_module.PhraseIndex(meanings, graph).lookup(question)
    store.save_phrase_hits(question_id, hits)
    phrase_dicts = [{"phrase": h.phrase, "kind": h.kind, "name": h.name, "text": h.text, "strength": h.strength} for h in hits]
    store.finish_step(question_id, STEP_PHRASES, note=f"{len(hits)} of his phrases found")

    # 4. the nucleus, whole
    store.start_step(question_id, STEP_NUCLEUS)
    nucleus, sizes = prompt_module.nucleus_text()
    prompt = prompt_module.build(question, reading, nucleus, graph, hits)
    bytes_sent = len(prompt.encode("utf-8"))
    store.finish_step(question_id, STEP_NUCLEUS, note=f"{bytes_sent} bytes; " + ", ".join(f"{k} {v}" for k, v in sizes.items()))

    # 4. one model call
    store.start_step(question_id, STEP_MODEL)
    call_started = time.time()
    try:
        reply = model_call(prompt)
    except Exception as error:
        store.save_model_call(question_id, "?", "?", prompt, call_started, None, False, str(error))
        store.finish_step(question_id, STEP_MODEL, note=f"failed: {error}")
        store.save_answer(question_id, "failed", None, "", None, None, str(error))
        return finish(Result(question_id, question, "failed", reason=f"The model call failed: {error}", reading=reading, phrases=phrase_dicts, bytes_sent=bytes_sent))
    store.save_model_call(question_id, reply.provider, reply.model, prompt, call_started, reply.text, True, None)
    store.finish_step(question_id, STEP_MODEL, note=f"{reply.provider} {reply.model}")

    # 5. the gate
    store.start_step(question_id, STEP_GATE)
    verdict = gate_module.check(reply.text, graph, meanings)
    store.finish_step(question_id, STEP_GATE, note="pass" if verdict.ok else f"refused: {verdict.reason}")
    if not verdict.ok:
        store.save_answer(question_id, "refused", None, "", reply.text, False, verdict.reason)
        return finish(Result(question_id, question, "refused", reason=verdict.reason, reading=reading, phrases=phrase_dicts,
                             provider=reply.provider, model=reply.model, bytes_sent=bytes_sent))

    # 6. the answer, out and saved
    store.start_step(question_id, STEP_ANSWER)
    store.save_answer(question_id, "answered", verdict.answer, verdict.text, reply.text, True, None)
    if verdict.possibility:
        store.save_candidates(question_id, verdict.possibility)
    store.finish_step(question_id, STEP_ANSWER)
    return finish(Result(question_id, question, "answered", answer=verdict.answer, text=verdict.text,
                         words=verdict.words, records=verdict.records, possibility=verdict.possibility,
                         reading=reading, phrases=phrase_dicts, provider=reply.provider, model=reply.model, bytes_sent=bytes_sent))


def print_result(result: Result) -> None:
    if result.phrases:
        print("meaning with meaning")
        for hit in result.phrases:
            print(f"  “{hit['phrase']}” → {hit['name']}: {hit['text'][:110]}")
        print()
    print(result.text if result.status == "answered" else f"{result.status}: {result.reason}")
    print()
    for step in result.steps:
        took = (step["finished"] or time.time()) - step["started"]
        note = f"  ({step['note']})" if step.get("note") else ""
        print(f"{step['name']:<24} {took:7.2f} s{note}")
    print(f"{'total':<24} {result.seconds:7.2f} s")
    if result.provider:
        print(f"model: {result.provider} {result.model}, {result.bytes_sent} bytes sent")


def main(argv: list[str]) -> int:
    question = " ".join(argv).strip()
    if not question:
        print("Write a question after ask.", file=sys.stderr)
        return 2
    result = ask(question)
    print_result(result)
    return 0 if result.status == "answered" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
