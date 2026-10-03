"""Adam's review of the forms page, applied to the review copy. No model is called.

Adam, 2026-10-02:
  "why is f-66 so damn long? I am not reviewing ridiculously long answers.
   I don't speak that way or read long rows of text."
  "F-53 makes no sense either.  Don't tell me this is how it is going to go."
  "the way the questions and answers are set up don't make sense."

Every waiting form is rechecked under the short-line and his-words rules. Two fixed
short frames are proposed with measured examples. Nothing is approved; every form
still waits for his yes. Run on the copy only:

    .venv/bin/python -m nucleus.forms_short
"""
from __future__ import annotations

from datetime import date
import json
import time
import uuid

from . import NUCLEUS_FILES, dictionary, forms, forms_middle, forms_night, forms_patterns
from .graph import load_graph
from .kinds import load_kinds
from .meaning_graph import build
from .store import Store

AUTHOR = 'claude/short-lines'
FRAMES = (
    {'when': {'answer': 'aligned'}, 'sentence': forms_middle.WORD_FRAME},
    {'when': {'answer': 'not_sure', 'graph_parts': True}, 'sentence': forms_middle.SHORT_PART_FRAME},
)


def his_words_reason(form) -> str | None:
    """Adam's review: no line built from record quotes, which are written about him."""
    blanks = {b for _, b in forms._parts(form['sentence']) if b}
    if 'record_quote' in blanks or any(b.startswith('quote:') for b in blanks):
        return forms_middle.NOT_HIS_WORDS
    if form['sentence'] == forms_middle.OLD_PART_FRAME:
        return forms_middle.TOO_LONG
    return None


def _measure(form, history, kinds, graph):
    reason = his_words_reason(form) or forms.check(form, kinds=kinds) or forms_patterns.check(form, kinds)
    if reason:
        return [], reason
    try:
        matches = forms_night.matching_answers(form, history, kinds, graph=graph)
    except forms.Refused as error:
        return [], str(error)
    return matches, forms_night.coverage_reason(matches)


def apply(path=forms_night.REVIEW_PATH) -> dict:
    path = forms_night.check_copy(path)
    if forms.forms_only():
        raise ValueError('requires NUCLEUS_FORMS_ONLY off')
    kinds = load_kinds()
    store = Store(path)
    try:
        engine = build(store, load_graph(NUCLEUS_FILES['graph'], NUCLEUS_FILES['ledger']),
                       dictionary.load_meanings(NUCLEUS_FILES['meanings']), kinds,
                       output_path=path.parent / 'forms-links.ttl')
        store.meaning_graph = engine
        history = forms_night.past_answers(store, kinds)
        forms_night.replay_graph_labels(history, engine)
        run_id, started = str(uuid.uuid4()), time.time()
        proposals = store.form_proposals()
        numbers = [int(p['number'][2:]) for p in proposals if (p['number'] or '').startswith('F-')]
        next_number = max(numbers, default=0) + 1
        rechecks, new = [], []
        for p in proposals:
            if p['status'] != 'proposed':
                continue
            matches, reason = _measure(p['form'], history, kinds, engine.graph)
            rechecks.append((p, matches, reason))
        standing = {(forms_night.encoded(p['form']['when']), p['form']['sentence'])
                    for p in proposals if p['status'] in ('proposed', 'approved')}
        fresh = [raw for raw in FRAMES if (forms_night.encoded(raw['when']), raw['sentence']) not in standing]
        for position, raw in enumerate(fresh, 1):
            form = {'number': f'F-{next_number + position - 1}', 'when': raw['when'], 'sentence': raw['sentence'],
                    'status': 'proposed', 'author': AUTHOR, 'date': date.today().isoformat()}
            matches, reason = _measure(form, history, kinds, engine.graph)
            new.append((position, raw, form, matches, reason))
        with store.connection:
            store.connection.execute(
                "INSERT INTO form_night_runs (id,started,status,inputs_json,prompt,reply,provider,model) "
                "VALUES (?,?,'running','[]',?,?,'program','short-lines')",
                (run_id, started, 'program: Adam review 2026-10-02, short lines and his words',
                 forms_night.encoded({'forms': list(FRAMES)})))
            for p, matches, reason in rechecks:
                forms_night.save_graph_condition(store, p['id'], run_id, p['form'], kinds)
                store.connection.execute(
                    'INSERT INTO form_coverage_checks(proposal_id,run_id,matches_json,examples_json,reason) VALUES (?,?,?,?,?)',
                    (p['id'], run_id, forms_night.encoded(matches),
                     forms_night.encoded(forms_night.diverse_examples(matches)), reason))
                if reason:
                    store.reject_form_proposal(p['id'], reason, commit=False)
                    store.connection.execute(
                        'INSERT INTO form_night_rechecks (run_id,proposal_id,reason) VALUES (?,?,?)',
                        (run_id, p['id'], reason))
            for position, raw, form, matches, reason in new:
                pid = store.save_form_proposal(form, reason, commit=False)
                forms_night.save_graph_condition(store, pid, run_id, form, kinds)
                store.connection.execute(
                    'INSERT INTO form_night_coverage (proposal_id,run_id,matches_json) VALUES (?,?,?)',
                    (pid, run_id, forms_night.encoded(matches)))
                store.connection.execute(
                    'INSERT INTO form_night_results (run_id,position,proposal_id,raw_json,reason,examples_json) '
                    'VALUES (?,?,?,?,?,?)',
                    (run_id, position, pid, forms_night.encoded(raw), reason,
                     forms_night.encoded(forms_night.diverse_examples(matches))))
            store.connection.execute("UPDATE form_night_runs SET status='completed',finished=? WHERE id=?",
                                     (time.time(), run_id))
        summary = {'run_id': run_id,
                   'rechecked': [{'number': p['number'], 'refused': reason} for p, _, reason in rechecks],
                   'new': []}
        for position, raw, form, matches, reason in new:
            real, practice = forms_night.source_counts(matches)
            summary['new'].append({
                'number': form['number'], 'sentence': form['sentence'], 'refused': reason,
                'real_fit_count': real, 'practice_fit_count': practice,
                'examples': [{'question': e['question'], 'says': e['text']}
                             for e in forms_night.diverse_examples(matches)]})
        return summary
    finally:
        store.connection.close()


def main() -> None:
    print(json.dumps(apply(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
