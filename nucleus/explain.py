"""The explanation under the rows: what the rows on the screen say about the question he asked.

Adam, 2026-09-12: "It just regurgitates my words. The meaning is there, but no explanation to help to use it."
and, on rows first with the explanation arriving under them: "This is what I was gunning for".

The rows paint in a blink. This paragraph arrives under them when the model is done. It may speak only
about the rows on the screen and the question. No advice. No next steps. Code checks it before it shows.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from . import model as model_module
from .store import Store

SCHEMA = Path(__file__).with_name("explanation.schema.json")
TITLE = "what this says about your question"

CONTRACT = """Above are Adam Blair's question and the rows his records painted for it: his own words, his own records,
and the middle word that names how each connects. Write one paragraph, four sentences at most, that says what
these rows say about his question. Speak to Adam as "you", never "he" or "Adam". Speak only about the rows above. Do not add facts, records, or words that are
not above. Adam's rule, verbatim: "No advice is given.  No next steps are suggested." Do not tell him what to do.
Do not quote his sentences back; the rows already show them. Plain words.
One plain paragraph. No headings, no chapters, no bullets, no labels in parentheses.
Return exactly one JSON object and nothing else: {"explanation": "<the paragraph>"}
"""

# words that turn a description into advice; refused by code
ADVICE = re.compile(r"\b(you should|should|try to|consider|next step|recommend|it would help|make sure|you need to|you must|you could)\b", re.I)
MAX_CHARS = 900


def check(text: object, touched_words: list[str]) -> str | None:
    """The paragraph, or None with the reason it is refused."""
    if not isinstance(text, str) or not text.strip():
        return "empty"
    text = " ".join(text.split())
    if len(text) > MAX_CHARS:
        return "longer than a paragraph"
    if ADVICE.search(text):
        return "advice"
    if "#" in text or re.search(r"\((Executive Conclusion|Consequence|Recommendation|Supporting Evidence)", text):
        return "chapters, not a paragraph"
    if touched_words and not any(w.lower() in text.lower() for w in touched_words):
        return "does not speak about his words on the screen"
    return None


def explain(question: str, painted_text: str, touched_words: list[str], model_call=None) -> tuple[str | None, str | None, model_module.ModelReply | None]:
    model_call = model_call or (lambda p: model_module.call(p, schema=SCHEMA))
    prompt = (
        "===== Adam's question =====\n" + question
        + "\n\n===== the rows on his screen =====\n" + painted_text
        + "\n\n===== the contract =====\n" + CONTRACT
    )
    reply = model_call(prompt)
    try:
        payload = json.loads(model_module._extract_json(reply.text))
    except json.JSONDecodeError:
        return None, "not JSON", reply
    text = payload.get("explanation") if isinstance(payload, dict) else None
    reason = check(text, touched_words)
    if reason:
        return None, reason, reply
    return " ".join(text.split()), None, reply


def start(question_id: str, question: str, painted_text: str, touched_words: list[str], store: Store, model_call=None) -> None:
    """Runs in the background so the rows are on the screen first."""
    store.explanation_pending(question_id)

    def run() -> None:
        started = time.time()
        try:
            text, reason, reply = explain(question, painted_text, touched_words, model_call)
        except Exception as error:
            store.save_explanation(question_id, None, f"failed: {error}", "?", "?", started)
            return
        provider = reply.provider if reply else "?"
        model = reply.model if reply else "?"
        if reply:
            store.save_model_call(question_id, provider, model, "(explanation)", started, reply.text, text is not None, reason)
        store.save_explanation(question_id, text, reason, provider, model, started)

    threading.Thread(target=run, daemon=True).start()
