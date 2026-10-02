"""Day graph-part sources reach forms exactly, without a model or new meanings."""
from dataclasses import asdict
import hashlib
import json
import re
from types import SimpleNamespace
import time

import pytest

from nucleus import ask, forms, forms_middle, graph_answers, links
from nucleus.dictionary import Meaning
from nucleus.graph import CONNECTION_PREFIX, Graph, Record
from nucleus.meaning_graph import build
from nucleus.store import Store


def reading(*words):
    return {'outcome': 'no', 'heSaidTheWordItself': [{'word': word} for word in words]}


def never(*_args, **_kwargs):
    raise AssertionError('day AI was called')


@pytest.fixture
def setup(tmp_path, monkeypatch):
    sources = tmp_path / 'sources'
    sources.mkdir()
    prefix = '@prefix ex: <https://example.test/> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . '
    (sources / 'accepted.ttl').write_text(prefix + 'ex:alpha rdfs:label "ALPHA" ; ex:points ex:middle . '
                                        + 'ex:middle ex:points <' + CONNECTION_PREFIX + 'r> .')
    (sources / 'upper.ttl').write_text(prefix + 'ex:upper ex:related ex:other .')
    (sources / 'axioms.ttl').write_text(prefix + 'ex:axiom ex:related ex:other .')
    quote = 'No evidence can establish a prerequisite for this claim.'
    meaning = 'I cannot claim a prerequisite for progress.'
    record = Record(CONNECTION_PREFIX + 'r', 'r', quote, '', '1', '', quote)
    legacy = Graph({record.uri: record}, [{'claim': quote, 'decision': 'accepted', 'at': '2026'}], '', '')
    meanings = [Meaning('ALPHA', '1', 1, meaning), Meaning('BETA', '2', 1, 'A quiet place.')]
    store = Store(tmp_path / 'copy.sqlite3')
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources.glob('*.ttl')}
    engine = build(store, legacy, meanings, ['supports'], accepted_dir=sources,
                   upper_path=sources / 'upper.ttl', axioms_path=sources / 'axioms.ttl')
    def part_reader(part):
        return reading(*(word for word in ('ALPHA', 'BETA') if re.search(r'\b' + word + r'\b', part)))
    monkeypatch.setattr('nucleus.dictionary.brief', part_reader)
    monkeypatch.setattr('nucleus.explain.start', never)
    yield store, engine, meaning, quote
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources.glob('*.ttl')} == before
    store.connection.close()


def approved():
    return {'number': 'F-999', 'when': {'answer': 'not_sure', 'graph_parts': True},
            'sentence': forms_middle.PART_FRAME, 'status': 'approved',
            'author': 'portable test fixture', 'date': '2026-10-02'}


def test_day_approved_part_form_uses_actual_multihop_paths_and_exact_source(setup, monkeypatch):
    store, engine, meaning, quote = setup
    question = 'ALPHA pulls at me but I cannot establish why “the app” broke?'
    monkeypatch.setattr(forms, 'load', lambda *_args, **_kwargs: [approved()])
    before = set(engine.graph.quads())
    result = ask.ask(question, store=store, brief=lambda _: reading('ALPHA'), model_call=never, meaning_graph=engine)
    expected = '“ALPHA pulls at me” lines up with ALPHA: “' + meaning + '”. “I cannot establish why “the app” broke?” is still open.'
    assert result.answer == 'not_sure' and result.text.split('\n', 1)[0] == expected
    assert result.records[0]['quote'] == quote and result.records[0]['kind'] is None
    assert engine.asserted_path('ALPHA', CONNECTION_PREFIX + 'r')
    explanation = store.explanation(result.question_id)
    assert explanation['provider'] == 'form' and explanation['model'] == 'F-999'
    assert explanation['text'] == 'F-999 · ' + expected
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0
    reply = json.loads(store.answer(result.question_id)['reply_json'])
    parts = forms.restore_parts(reply['parts'])
    assert parts[0].text == 'ALPHA pulls at me' and parts[0].records == {'ALPHA': (CONNECTION_PREFIX + 'r',)}
    assert parts[1].text == 'I cannot establish why “the app” broke?' and parts[1].connected == ()
    step = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert not step['budget_miss'] and step['label_ms'] + step['form_ms'] < 300
    assert set(engine.graph.quads()) == before


def test_visible_part_helper_roundtrips_only_source_fields(setup):
    _store, engine, _meaning, _quote = setup
    label = graph_answers.label_question('ALPHA but I do not know?', engine)
    parts = graph_answers.visible_parts(label)
    assert forms.restore_parts(json.loads(json.dumps([asdict(part) for part in parts]))) == parts
    assert set(asdict(parts[0])) == {'text', 'words', 'connected', 'missing', 'records'}
    assert 'dictionary_ms' not in asdict(parts[0]) and 'ms' not in asdict(parts[0])
    picture = graph_answers.paint(label.touched, engine, label)
    screen = graph_answers.screen_from_picture(picture, ['supports'])
    assert screen.parts == parts
    assert screen.meanings[0].quote == engine.meanings[0].text


def test_replay_renderer_preserves_original_source_without_repainting(setup):
    _store, engine, _meaning, _quote = setup
    label = graph_answers.label_question('ALPHA but a missing scene?', engine)
    parts = graph_answers.visible_parts(label)
    words = [{'word': 'ALPHA', 'meanings': ['An old exact meaning.'], 'why': 'An old exact why.'}]
    original = 'Not sure.\n\nALPHA — “An old exact meaning.”\nAn old exact why.'
    text = original + '\n\n' + graph_answers.render_question_parts(parts, ('ALPHA',))
    screen = forms_middle.from_visible('not_sure', words, [], text, ['supports'], parts=parts)
    assert text.startswith(original)
    assert screen.meanings == (forms.Meaning('ALPHA', 'An old exact meaning.'),)
    assert words[0]['why'] == 'An old exact why.' and screen.rows == ()
    filled = forms.fill(approved(), screen, kinds=['supports'], graph=engine.graph)
    assert filled is not None and '“An old exact meaning.”' in filled.text
    assert '“a missing scene?”' in filled.text
    assert all(part.text in original or part.text in text or part.source == 'form.sentence' for part in filled.parts)


def test_one_part_answer_keeps_word_rule_and_never_picks_a_part_form(setup, monkeypatch):
    store, engine, _meaning, _quote = setup
    monkeypatch.setattr(forms, 'load', lambda *_args, **_kwargs: [approved()])
    result = ask.ask('ALPHA with BETA?', store=store, brief=lambda _: reading('ALPHA', 'BETA'),
                     model_call=never, meaning_graph=engine)
    assert result.answer == 'not_sure' and result.text.startswith('Not sure.')
    assert store.explanation(result.question_id) is None
    miss = json.loads(store.connection.execute('SELECT picture_json FROM form_misses WHERE question_id=?', (result.question_id,)).fetchone()[0])
    assert miss['parts'] == []
    assert json.loads(store.answer(result.question_id)['reply_json'])['parts'] == []
    assert result.words[0]['why'] == 'you said ALPHA'
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0


def test_count_fallback_cannot_keep_graph_part_metadata(setup, monkeypatch):
    store, engine, _meaning, quote = setup
    store.add_link('ALPHA', 'r', quote, '', 'links:fixture', 'fixture', 'fixture', kind='supports')
    monkeypatch.setattr(engine, 'label', lambda _: (_ for _ in ()).throw(RuntimeError('query failed')))
    monkeypatch.setattr(forms, 'load', lambda *_args, **_kwargs: [approved()])
    result = ask.ask('ALPHA but an unknown scene?', store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine)
    assert result.answer == 'not_sure' and result.text.startswith('Not sure.')
    assert json.loads(store.answer(result.question_id)['reply_json'])['parts'] == []
    assert store.explanation(result.question_id) is None
    diagnostic = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert diagnostic['rule'] == 'count rule' and diagnostic['error'] == 'query failed'


def test_dont_know_keeps_unprinted_parts_out_of_the_screen(setup):
    _store, engine, _meaning, _quote = setup
    label = graph_answers.label_question('BETA but an unknown scene?', engine)
    assert label.answer == 'dont_know' and graph_answers.visible_parts(label) == ()
    picture = graph_answers.paint(label.touched, engine, label)
    assert picture.parts == [] and picture.words == []
    assert graph_answers.screen_from_picture(picture, ['supports']).parts == ()


def test_a_dictionary_stop_after_a_long_wait_keeps_query_time_separate(setup, monkeypatch):
    store, engine, _meaning, quote = setup
    store.add_link('ALPHA', 'r', quote, '', 'links:fixture', 'fixture', 'fixture', kind='supports')
    ticks = iter([0.0, 0.8])  # Actual dictionary phase boundaries, no sleep or graph call.
    monkeypatch.setattr(graph_answers, 'time', SimpleNamespace(perf_counter=lambda: next(ticks), time=time.time))
    monkeypatch.setattr('nucleus.dictionary.brief', lambda _: {'outcome': 'stopped'})
    result = ask.ask('ALPHA but an unknown scene?', store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine, explain_call=False)
    diagnostic = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert diagnostic['rule'] == 'count rule' and diagnostic['error'] == 'dictionary stopped question part'
    assert diagnostic['dictionary_ms'] == 800.0
    assert diagnostic['label_ms'] == 0.0 and diagnostic['total_ms'] == 0.0
    assert not diagnostic['budget_miss'] and result.answer == 'not_sure'


def test_failed_graph_query_time_still_counts_toward_the_shared_budget(setup, monkeypatch):
    store, engine, _meaning, quote = setup
    store.add_link('ALPHA', 'r', quote, '', 'links:fixture', 'fixture', 'fixture', kind='supports')
    # Single-part existing reading/hits, then the failed graph query boundaries.
    ticks = iter([0.0, 0.001, 0.001, 0.402])
    monkeypatch.setattr(graph_answers, 'time', SimpleNamespace(perf_counter=lambda: next(ticks), time=time.time))
    monkeypatch.setattr(engine, 'label', lambda _: (_ for _ in ()).throw(RuntimeError('failed query')))
    result = ask.ask('ALPHA?', store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine, explain_call=False)
    diagnostic = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert diagnostic['rule'] == 'count rule' and diagnostic['error'] == 'graph budget miss'
    assert diagnostic['budget_miss'] and diagnostic['label_ms'] == 401.0
    assert diagnostic['dictionary_ms'] == 1.0
