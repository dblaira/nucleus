"""Day answers from asserted graph paths; exact screen data still binds forms."""
from __future__ import annotations

from dataclasses import asdict
import json
import time
import uuid

from . import dictionary, forms, forms_middle, gate, links

BUILD_STEP = '4 graph built at start'
QUERY_STEP = '4 graph questions'
BUDGET_MS = 300.0


class GraphBudgetExceeded(RuntimeError):
    pass


def record_build(store, engine):
    finished = time.time()
    qid = 'graph:start:' + str(uuid.uuid4())
    store.connection.execute('INSERT INTO steps(question_id,name,started,finished,note) VALUES (?,?,?,?,?)',
        (qid, BUILD_STEP, finished - engine.stats['build_ms'] / 1000, finished,
         json.dumps(engine.stats, ensure_ascii=False, sort_keys=True)))
    store.connection.commit()
    return qid


def paint(touched, engine, label):
    """Only asserted reachable records and their complete, validated source quotes."""
    if label.answer == 'dont_know':
        # That screen prints only its fixed line. Hidden dictionary hits are not blanks.
        return links.Picture('dont_know', gate.compose('dont_know', [], [], []),
                             touched=list(touched), missing=list(label.missing))
    graph, meanings = engine.legacy_graph, engine.meanings
    words, records, seen = [], [], set()
    for word in touched:
        words.append({'word': word, 'why': word + ' has no links.' if word in label.missing else 'you said ' + word,
                      'meanings': [m.text for m in dictionary.meanings_for(meanings, word)]})
        direct = {link['record']: link for link in engine.links_for(word)}
        for uri in label.records.get(word, ()):
            record = graph.find(uri)
            if record is None or record.leaf in seen or not graph.is_accepted(record):
                continue
            link = direct.get(record.leaf)
            quote = link['quote'] if link else gate.unescape_label(record.label)
            if not graph.quote_is_in(record, quote):
                continue
            seen.add(record.leaf)
            records.append({'id': record.uri, 'leaf': record.leaf, 'quote': quote,
                'why': link['why'] if link and str(link['source']).startswith('links:') else '',
                'strength': record.strength, 'accepted_at': record.accepted_at,
                'connection_type': record.connection_type, 'link_word': word,
                'kind': link['kind'] if link else None})
    records.sort(key=lambda r: -float(r['strength'] or 0))
    text = gate.compose(label.answer, words, records, [])
    return links.Picture(label.answer, text, words, records, list(touched), list(label.missing))


def answer(question_id, question, reading, hits, store, engine, explain_call):
    """No model door exists here, even with the forms-only switch off."""
    touched = links.touched_words(reading, hits, {m.word for m in engine.meanings})
    store.start_step(question_id, QUERY_STEP)
    label, error, filled, reason = None, None, None, None
    form_times = []
    label_started = time.perf_counter()
    try:
        label = engine.label(touched)
        if label.budget_miss:
            raise ValueError('graph budget miss')
        picture = paint(touched, engine, label)
    except Exception as failure:
        error = str(failure)
        # The old note count is a named fallback only. It never invokes AI.
        picture = links.paint(question, reading, hits, store, engine.legacy_graph, engine.meanings)
        if picture is None:
            picture = links.Picture('dont_know', gate.compose('dont_know', [], [], []), touched=touched)
    label_ms = label.ms if label is not None else (time.perf_counter() - label_started) * 1000

    def trace_form(milliseconds):
        form_times.append(milliseconds)
        if label_ms + sum(form_times) > BUDGET_MS:
            raise GraphBudgetExceeded('graph budget miss')

    if explain_call is not False:
        try:
            screen = forms_middle.from_visible(picture.answer, picture.words, picture.records, picture.text)
            filled, reason = forms.pick(screen, graph=engine.graph, query_trace=trace_form)
        except forms.Refused as failure:
            reason = str(failure)
        except GraphBudgetExceeded:
            reason = 'graph budget miss'
    graph_ms = label_ms + sum(form_times)
    miss = graph_ms > BUDGET_MS or error == 'graph budget miss'
    if miss:
        filled, reason = None, 'graph budget miss'
        error = 'graph budget miss'
        picture = links.paint(question, reading, hits, store, engine.legacy_graph, engine.meanings)
        if picture is None:
            picture = links.Picture('dont_know', gate.compose('dont_know', [], [], []), touched=touched)
    diagnostic = {'rule': 'count rule' if error else 'graph paths', 'error': error,
                  'label': label.to_dict() if label is not None else None,
                  'label_ms': label_ms, 'form_ms': sum(form_times), 'total_ms': graph_ms,
                  'budget_ms': BUDGET_MS, 'budget_miss': miss}
    store.finish_step(question_id, QUERY_STEP, note=json.dumps(diagnostic, ensure_ascii=False, sort_keys=True))
    form_step = '5 form ' + filled.number + ' chosen' if filled else '5 graph answer, no model'
    for step in (form_step, '6 the gate'):
        store.start_step(question_id, step)
        store.finish_step(question_id, step, note=json.dumps({'parts': [asdict(p) for p in filled.parts]})
                          if filled and step == form_step else 'graph paths, source quotes checked')
    if filled:
        store.save_explanation(question_id, filled.number + ' · ' + filled.text, None, 'form', filled.number, time.time())
    else:
        store.save_form_miss(question_id, asdict(picture), reason or error or 'no approved forms')
    text = picture.text
    if filled and picture.answer == 'not_sure' and forms_middle.is_filled(filled):
        _first, separator, body = text.partition('\n')
        text = filled.text + separator + body
    reply = {'answer': picture.answer, 'words': picture.words, 'records': picture.records, 'possibility': []}
    store.start_step(question_id, '7 answer out')
    store.save_answer(question_id, 'answered', picture.answer, text, json.dumps(reply, ensure_ascii=False), True, None)
    store.finish_step(question_id, '7 answer out')
    return picture, text
