"""Two passes over the records, then one small judging call. For a model whose window is too small.

Apple's server model holds 32,768 tokens. The compact nucleus is 41,083 (measured 2026-09-10 with
Apple's own tokenizer). So the records are split in two, each half travels with the whole dictionary,
both passes run at the same time, and a third, small call reads only what the two passes found and
gives one of Adam's three answers. The gate then checks that answer exactly as it checks a single call.

What the user feels: one wait. The two passes overlap, so the wait is the slower pass plus the judge.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from . import NUCLEUS_FILES
from . import dictionary as dictionary_module
from . import gate as gate_module
from . import model as model_module
from . import phrases as phrases_module
from .ask import Result, STEP_DICTIONARY, STEP_GATE, STEP_PHRASES, STEP_QUESTION
from .compact import compact_records
from .graph import Graph, load_graph
from .prompt import CONTRACT, phrase_block
from .store import Store

STEP_SPLIT = "4 records split in two"
STEP_PASS_1 = "5a pass one, first half"
STEP_PASS_2 = "5b pass two, second half"
STEP_JUDGE = "5c the judge reads both"
STEP_ANSWER = "7 answer out"

PASS_NOTE = """
===== this is one of two passes =====
You are seeing HALF of Adam's accepted records with his whole dictionary. Another pass sees the other
half. A third call will read what both passes found and give the final answer. So: report every word
and every record in front of you that matches his question, with one-sentence whys. Choose "answer"
from what you can see; the judge decides the final one. If nothing in front of you matches, return
"dont_know" with empty lists.
"""

JUDGE_CONTRACT = """You are the judge. Two passes each read half of Adam Blair's accepted records with his whole
dictionary and reported what matched his question. Their reports are above, and under them the full
lines of every record and every dictionary entry they cited, so you can copy quotes character for
character. You have not seen the other records; the passes have. Merge the two reports into one final
answer.

""" + CONTRACT + """
- Keep the whys the passes wrote when they are one sentence; you may shorten, never lengthen.
- Cite only records and words that appear in the cited lines above. Nothing else exists to you.
"""


def split_records(graph: Graph) -> tuple[str, str]:
    header, *lines = compact_records(graph).rstrip("\n").split("\n")
    middle = (len(lines) + 1) // 2
    return (header + "\n" + "\n".join(lines[:middle]) + "\n",
            header + "\n" + "\n".join(lines[middle:]) + "\n")


def pass_prompt(question: str, reading: dict, half: str, which: str, hits) -> str:
    meanings = NUCLEUS_FILES["meanings"].read_text(encoding="utf-8")
    return (
        f"===== accepted records, {which} =====\n{half}\n"
        f"===== meanings.txt (Adam's dictionary, verbatim) =====\n{meanings}\n"
        + "\n===== the dictionary's reading of the question =====\n"
        + json.dumps(reading, ensure_ascii=False, indent=1) + "\n"
        + phrase_block(hits)
        + "\n\n===== Adam's question, character for character =====\n" + question
        + "\n\n===== the contract =====\n" + CONTRACT + PASS_NOTE
    )


def judge_prompt(question: str, replies: list[str], graph: Graph, meanings) -> str:
    cited_records: list[str] = []
    cited_words: list[str] = []
    for text in replies:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        for item in payload.get("records") or []:
            record = graph.find(str(item.get("id"))) if isinstance(item, dict) else None
            if record is not None and graph.is_accepted(record):
                line = [l for l in compact_records(graph).split("\n") if l.startswith(record.leaf + " |")]
                cited_records.extend(l for l in line if l not in cited_records)
        for item in payload.get("words") or []:
            word = item.get("word") if isinstance(item, dict) else None
            for meaning in dictionary_module.meanings_for(meanings, word) if isinstance(word, str) else []:
                line = f"{word} = {meaning.text}"
                if line not in cited_words:
                    cited_words.append(line)
    return (
        "===== pass one found =====\n" + replies[0] + "\n\n===== pass two found =====\n" + replies[1]
        + "\n\n===== the cited records, full lines (id | type | strength | accepted | label | note) =====\n"
        + ("\n".join(cited_records) or "none") + "\n"
        + "\n===== the cited dictionary entries =====\n" + ("\n".join(cited_words) or "none") + "\n"
        + "\n\n===== Adam's question, character for character =====\n" + question
        + "\n\n===== the contract =====\n" + JUDGE_CONTRACT
    )


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

    store.start_step(question_id, STEP_DICTIONARY)
    reading = brief(question)
    outcome = reading.get("outcome")
    store.finish_step(question_id, STEP_DICTIONARY, note=f"outcome {outcome}")
    if outcome in ("stopped", "ask"):
        text = str(reading.get("stopped") or reading.get("mustAskFirst") or outcome)
        store.save_answer(question_id, "stopped", None, text, json.dumps(reading, ensure_ascii=False), None, None)
        return finish(Result(question_id, question, "stopped", text=text, reason=text, reading=reading))

    store.start_step(question_id, STEP_PHRASES)
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary_module.load_meanings(NUCLEUS_FILES["meanings"])
    hits = phrases_module.PhraseIndex(meanings, graph).lookup(question)
    store.save_phrase_hits(question_id, hits)
    phrase_dicts = [{"phrase": h.phrase, "kind": h.kind, "name": h.name, "text": h.text, "strength": h.strength} for h in hits]
    store.finish_step(question_id, STEP_PHRASES, note=f"{len(hits)} of his phrases found")

    store.start_step(question_id, STEP_SPLIT)
    first, second = split_records(graph)
    prompts = [pass_prompt(question, reading, first, "first half", hits), pass_prompt(question, reading, second, "second half", hits)]
    sizes = [len(p.encode("utf-8")) for p in prompts]
    store.finish_step(question_id, STEP_SPLIT, note=f"{sizes[0]} and {sizes[1]} bytes")

    def run(step: str, prompt: str) -> model_module.ModelReply:
        """The model call only. The store is written from the main thread; one connection, one thread."""
        started = time.time()
        try:
            reply = model_call(prompt)
        except Exception as error:
            raise RuntimeError(f"{step}: {error}") from error
        return model_module.ModelReply(reply.provider, reply.model, reply.text), started

    def record(step: str, prompt: str, outcome) -> model_module.ModelReply:
        reply, started = outcome
        store.save_model_call(question_id, reply.provider, reply.model, prompt, started, reply.text, True, None)
        store.finish_step(question_id, step, note=f"{reply.provider} {reply.model}")
        return reply

    try:
        store.start_step(question_id, STEP_PASS_1)
        store.start_step(question_id, STEP_PASS_2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, STEP_PASS_1, prompts[0]), pool.submit(run, STEP_PASS_2, prompts[1])]
            outcomes = [f.result() for f in futures]
        passes = [record(STEP_PASS_1, prompts[0], outcomes[0]), record(STEP_PASS_2, prompts[1], outcomes[1])]
        judge_text = judge_prompt(question, [p.text for p in passes], graph, meanings)
        store.start_step(question_id, STEP_JUDGE)
        judged = record(STEP_JUDGE, judge_text, run(STEP_JUDGE, judge_text))
    except Exception as error:
        for step in (STEP_PASS_1, STEP_PASS_2, STEP_JUDGE):
            store.finish_step(question_id, step, note=f"failed: {error}")
        store.save_answer(question_id, "failed", None, "", None, None, str(error))
        return finish(Result(question_id, question, "failed", reason=f"A model call failed: {error}", reading=reading, phrases=phrase_dicts, bytes_sent=sum(sizes)))

    store.start_step(question_id, STEP_GATE)
    verdict = gate_module.check(judged.text, graph, meanings)
    store.finish_step(question_id, STEP_GATE, note="pass" if verdict.ok else f"refused: {verdict.reason}")
    if not verdict.ok:
        store.save_answer(question_id, "refused", None, "", judged.text, False, verdict.reason)
        return finish(Result(question_id, question, "refused", reason=verdict.reason, reading=reading, phrases=phrase_dicts,
                             provider=judged.provider, model=judged.model, bytes_sent=sum(sizes)))

    store.start_step(question_id, STEP_ANSWER)
    store.save_answer(question_id, "answered", verdict.answer, verdict.text, judged.text, True, None)
    if verdict.possibility:
        store.save_candidates(question_id, verdict.possibility)
    store.finish_step(question_id, STEP_ANSWER)
    return finish(Result(question_id, question, "answered", answer=verdict.answer, text=verdict.text,
                         words=verdict.words, records=verdict.records, possibility=verdict.possibility,
                         reading=reading, phrases=phrase_dicts, provider=judged.provider, model=judged.model, bytes_sent=sum(sizes)))


def main(argv: list[str]) -> int:
    from .ask import print_result
    question = " ".join(argv).strip()
    if not question:
        print("Write a question after twopass.", file=sys.stderr)
        return 2
    result = ask(question, surface="cli-twopass")
    print_result(result)
    return 0 if result.status == "answered" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
