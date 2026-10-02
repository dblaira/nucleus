"""Day answers from asserted graph paths; exact screen data still binds forms."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
import uuid

from . import dictionary, forms, forms_middle, gate, links
from .phrases import PhraseIndex
from .question_parts import split_question

BUILD_STEP = '4 graph built at start'
QUERY_STEP = '4 graph questions'
BUDGET_MS = 300.0


class GraphBudgetExceeded(RuntimeError):
    pass


class GraphLabelFailure(ValueError):
    """Carry query time separately when no completed label can do so."""
    def __init__(self, message, *, graph_ms=0.0, dictionary_ms=0.0):
        super().__init__(message)
        self.graph_ms = graph_ms
        self.dictionary_ms = dictionary_ms


@dataclass(frozen=True)
class PartLabel:
    text: str
    words: tuple[str, ...]
    connected: tuple[str, ...]
    missing: tuple[str, ...]
    records: dict[str, tuple[str, ...]]
    dictionary_ms: float
    ms: float
    query_is_shared: bool = True


@dataclass(frozen=True)
class QuestionLabel:
    answer: str | None
    connected: tuple[str, ...]
    missing: tuple[str, ...]
    records: dict[str, tuple[str, ...]]
    ms: float
    budget_miss: bool
    touched: tuple[str, ...]
    parts: tuple[PartLabel, ...]
    rule: str
    dictionary_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


def label_question(question, engine, reading=None, hits=None):
    """Ask one graph query, then check which exact question parts it connects.

    A single part keeps the existing dictionary-word verdict. Multiple parts
    are read separately by the dictionary's own deterministic reader. One
    reached word connects that part; only all connected parts yield aligned.
    No question part becomes a new word, edge, or governing meaning.
    """
    texts = split_question(question) or (question.strip(),)
    known = {meaning.word for meaning in engine.meanings}
    readings = []
    dictionary_ms = 0.0
    # A whole-question phrase can cross a separator, so multipart questions
    # use only phrase hits looked up inside each part.
    index = PhraseIndex(engine.meanings, engine.legacy_graph) if len(texts) > 1 or hits is None else None
    for text in texts:
        started = time.perf_counter()
        try:
            part_reading = reading if len(texts) == 1 and reading is not None else dictionary.brief(text)
            if len(texts) > 1:
                if not isinstance(part_reading, dict):
                    raise ValueError('dictionary returned invalid question part')
                if part_reading.get('outcome') in ('stopped', 'ask'):
                    raise ValueError('dictionary stopped question part')
            part_hits = hits if len(texts) == 1 and hits is not None else index.lookup(text)
            words = tuple(links.touched_words(part_reading, part_hits, known))
        except Exception as error:
            elapsed = (time.perf_counter() - started) * 1000
            raise GraphLabelFailure(str(error), dictionary_ms=dictionary_ms + elapsed) from error
        elapsed = (time.perf_counter() - started) * 1000
        dictionary_ms += elapsed
        readings.append((text, words, elapsed))
    touched = tuple(dict.fromkeys(word for _text, words, _elapsed in readings for word in words))
    query_started = time.perf_counter()
    try:
        label = engine.label(touched)
    except Exception as error:
        raise GraphLabelFailure(str(error), graph_ms=(time.perf_counter() - query_started) * 1000,
                                dictionary_ms=dictionary_ms) from error
    reached = set(label.connected)
    parts = tuple(PartLabel(text, words, tuple(word for word in words if word in reached),
                            tuple(word for word in words if word not in reached),
                            {word: label.records.get(word, ()) for word in words}, elapsed,
                            label.ms)
                  for text, words, elapsed in readings)
    answer = label.answer
    if len(parts) > 1 and not label.budget_miss:
        count = sum(bool(part.connected) for part in parts)
        answer = 'aligned' if count == len(parts) else 'not_sure' if count else 'dont_know'
    return QuestionLabel(answer, label.connected, label.missing, label.records,
                         label.ms, label.budget_miss, touched, parts,
                         'question parts' if len(parts) > 1 else 'word paths', dictionary_ms)


def visible_parts(label):
    """Exact successful multipart sources, without lookup or historical repaint."""
    if (getattr(label, 'budget_miss', True) or getattr(label, 'rule', '') != 'question parts'
            or label.answer == 'dont_know'):
        return ()
    return tuple(forms.GraphPart(part.text, part.words, part.connected, part.missing,
                                 dict(part.records)) for part in label.parts)


def question_part_whys(parts, words=None):
    """Print the exact parts beside the dictionary word whose graph path fits.

    A replay can append these new graph-part lines to its saved source text;
    the helper never replaces a record, meaning, or original why.
    """
    return forms_middle.graph_part_whys(parts, words)


def render_question_parts(parts, words=None):
    """Visible graph-part proof only; old source lines stay untouched."""
    return '\n\n'.join(question_part_whys(parts, words).values())


def screen_from_picture(picture, kinds=None):
    """Use only the current painted source and its explicit graph-part proof."""
    return forms_middle.from_visible(picture.answer, picture.words, picture.records,
                                     picture.text, kinds, parts=tuple(picture.parts))


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
    parts = visible_parts(label)
    part_whys = question_part_whys(parts, touched)
    for word in touched:
        why = word + ' has no links.' if word in label.missing else 'you said ' + word
        if word in part_whys:
            why = part_whys[word]
        words.append({'word': word, 'why': why,
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
    return links.Picture(label.answer, text, words, records, list(touched), list(label.missing), list(parts))


def answer(question_id, question, reading, hits, store, engine, explain_call):
    """No model door exists here, even with the forms-only switch off."""
    touched = links.touched_words(reading, hits, {m.word for m in engine.meanings})
    store.start_step(question_id, QUERY_STEP)
    label, error, filled, reason = None, None, None, None
    form_times = []
    failed_graph_ms = failed_dictionary_ms = 0.0
    try:
        label = label_question(question, engine, reading=reading, hits=hits)
        touched = list(label.touched)
        if label.budget_miss:
            raise ValueError('graph budget miss')
        picture = paint(touched, engine, label)
    except Exception as failure:
        error = str(failure)
        failed_graph_ms = getattr(failure, 'graph_ms', 0.0)
        failed_dictionary_ms = getattr(failure, 'dictionary_ms', 0.0)
        # The old note count is a named fallback only. It never invokes AI.
        picture = links.paint(question, reading, hits, store, engine.legacy_graph, engine.meanings)
        if picture is None:
            picture = links.Picture('dont_know', gate.compose('dont_know', [], [], []), touched=touched)
    label_ms = label.ms if label is not None else failed_graph_ms

    def trace_form(milliseconds):
        form_times.append(milliseconds)
        if label_ms + sum(form_times) > BUDGET_MS:
            raise GraphBudgetExceeded('graph budget miss')

    if explain_call is not False:
        try:
            screen = screen_from_picture(picture)
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
                  'dictionary_ms': label.dictionary_ms if label is not None else failed_dictionary_ms,
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
    reply = {'answer': picture.answer, 'words': picture.words, 'records': picture.records, 'possibility': [],
             'parts': [asdict(part) for part in picture.parts]}
    store.start_step(question_id, '7 answer out')
    store.save_answer(question_id, 'answered', picture.answer, text, json.dumps(reply, ensure_ascii=False), True, None)
    store.finish_step(question_id, '7 answer out')
    return picture, text
