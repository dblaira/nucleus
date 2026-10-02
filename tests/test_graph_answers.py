import json
from pathlib import Path
import re

import pytest

from nucleus import ask, forms_night, graph_answers, serve
from nucleus.dictionary import Meaning
from nucleus.graph import Graph, Record, CONNECTION_PREFIX
from nucleus.meaning_graph import build, Label
from nucleus.store import Store
from nucleus import STORE_PATH


@pytest.fixture
def setup(tmp_path):
    accepted = tmp_path / 'sources'
    accepted.mkdir()
    for name in ('accepted.ttl', 'upper.ttl', 'axioms.ttl'):
        (accepted / name).write_text('@prefix ex: <urn:test:> . ex:a ex:related ex:b .')
    record = Record(CONNECTION_PREFIX + 'r', 'r', 'A clear sign.', '', '1', '', 'A clear sign.')
    legacy = Graph({record.uri: record}, [{'claim': record.label, 'decision': 'accepted', 'at': '2026'}], '', '')
    meanings = [Meaning('ALPHA', '1', 1, 'A clear sign.'), Meaning('BETA', '2', 1, 'A quiet place.')]
    store = Store(tmp_path / 'copy.sqlite3')
    store.add_link('ALPHA', 'r', record.label, '', 'links:ALPHA', 'night', 'night', kind='supports')
    engine = build(store, legacy, meanings, ['supports'], accepted_dir=accepted,
                   upper_path=accepted / 'upper.ttl', axioms_path=accepted / 'axioms.ttl')
    yield store, engine
    store.connection.close()


def reading(*words):
    return {'outcome': 'no', 'heSaidTheWordItself': [{'word': w} for w in words]}


def never(*args, **kwargs):
    raise AssertionError('day AI was called')


@pytest.mark.parametrize('words,label', [(('ALPHA',), 'aligned'), (('ALPHA', 'BETA'), 'not_sure'),
                                        (('BETA',), 'dont_know'), ((), 'dont_know')])
def test_the_label_comes_from_the_graph(setup, words, label, monkeypatch):
    store, engine = setup
    monkeypatch.setattr('nucleus.explain.start', never)
    result = ask.ask('A situation?', store=store, brief=lambda _: reading(*words),
                     model_call=never, meaning_graph=engine)
    assert result.answer == label
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0
    step = next(s for s in result.steps if s['name'] == graph_answers.QUERY_STEP)
    trace = json.loads(step['note'])
    assert trace['rule'] == 'graph paths' and trace['label']['answer'] == label
    assert trace['total_ms'] < 300 and not trace['budget_miss']
    if label == 'not_sure':
        assert 'BETA has no links.' in result.text
        screen = forms_night.past_answers(store, ['supports'])
        # CLI is not counted as Adam's history.
        assert screen == []


def test_budget_miss_uses_named_count_rule_and_logs_miss(setup, monkeypatch):
    store, engine = setup
    monkeypatch.setattr(engine, 'label', lambda _: Label(None, (), ('ALPHA',), {}, 301, True))
    result = ask.ask('A situation?', store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine)
    trace = json.loads(next(s for s in result.steps if s['name'] == graph_answers.QUERY_STEP)['note'])
    assert trace['rule'] == 'count rule' and trace['budget_miss']
    assert store.connection.execute('SELECT reason FROM form_misses').fetchone()[0] == 'graph budget miss'
    assert result.answer == 'not_sure'  # Old one-record fallback.


def test_form_asks_share_the_label_budget(setup, monkeypatch):
    store, engine = setup
    def over_budget(screen, *, graph, query_trace):
        query_trace(301)
        pytest.fail('The form check must stop when the shared budget is exceeded')
    monkeypatch.setattr('nucleus.forms.pick', over_budget)
    result = ask.ask('A situation?', store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine)
    trace = json.loads(next(s for s in result.steps if s['name'] == graph_answers.QUERY_STEP)['note'])
    assert trace['label']['answer'] == 'aligned' and trace['form_ms'] == 301
    assert trace['rule'] == 'count rule' and trace['budget_miss']
    assert result.answer == 'not_sure'
    assert store.connection.execute('SELECT reason FROM form_misses').fetchone()[0] == 'graph budget miss'


def test_old_answers_are_replayed_without_rewriting_the_screen(setup):
    store, engine = setup
    original = {'words': ['ALPHA'], 'answer': 'not_sure', 'rows': [], 'missing_links': False}
    item = {'screen': dict(original), 'reason': None, 'raw': {'text': 'old exact text'}}
    forms_night.replay_graph_labels([item], engine)
    assert item['screen']['answer'] == 'aligned'
    assert item['raw']['text'] == 'old exact text'
    assert item['screen']['rows'] == original['rows']
    assert item['graph_label']['answer'] == 'aligned'


def test_multipart_historical_replay_keeps_every_source_field_exact(setup, monkeypatch):
    from copy import deepcopy
    store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', lambda q: reading('ALPHA') if 'ALPHA' in q else reading())
    original = {'words': ['ALPHA'], 'answer': 'aligned',
                'rows': [{'word': 'ALPHA', 'kind': 'supports', 'quote': 'I cannot tell the coordinator.'}],
                'meanings': [{'word': 'ALPHA', 'quote': 'Facilitator, liaison, engineering.'}],
                'whys': [{'word': 'ALPHA', 'text': 'Exact old why.'}],
                'missing_words': [], 'missing_links': False, 'kinds_complete': True}
    raw = {'text': 'Exact old screen, unchanged.', 'reply_json': '{"exact":"not"}'}
    item = {'question': 'ALPHA feels clear, but how did the app behave?',
            'screen': deepcopy(original), 'reason': None, 'raw': deepcopy(raw)}
    forms_night.replay_graph_labels([item], engine)
    assert item['screen'] == {**original, 'answer': 'not_sure'}
    assert item['raw'] == raw
    assert item['graph_label']['rule'] == 'question parts'
    assert len(item['graph_label']['parts']) == 2
    assert item['graph_label']['parts'][1]['connected'] == ()


def test_service_build_is_saved_in_steps(setup):
    store, engine = setup
    qid = graph_answers.record_build(store, engine)
    step = store.steps(qid)[0]
    assert step['name'] == graph_answers.BUILD_STEP
    assert json.loads(step['note'])['build_ms'] == engine.stats['build_ms']
    assert abs((step['finished'] - step['started']) * 1000 - engine.stats['build_ms']) < .01


def test_graph_service_refuses_live_before_sqlite_open(monkeypatch):
    monkeypatch.setattr(serve, 'Store', never)
    with pytest.raises(ValueError, match='never the live'):
        serve.make_server(0, STORE_PATH, graph_mode=True)


def test_copy_graph_cannot_open_default_live_store(setup, monkeypatch):
    store, engine = setup
    monkeypatch.setattr(ask, 'Store', never)
    with pytest.raises(ValueError, match='explicit copy store'):
        ask.ask('ALPHA', meaning_graph=engine)


def test_dont_know_cannot_fill_a_hidden_dictionary_word(setup, monkeypatch):
    store, engine = setup
    screens = []
    monkeypatch.setattr('nucleus.forms.pick', lambda screen, **_: (screens.append(screen) or None, 'no approved forms'))
    result = ask.ask('A situation?', store=store, brief=lambda _: reading('BETA'),
                     model_call=never, meaning_graph=engine)
    assert result.answer == 'dont_know' and result.words == []
    assert screens[0].words == () and screens[0].missing_words == ()


def read_part(text):
    return reading(*(word for word in ('ALPHA', 'BETA') if re.search(r'\b' + word + r'\b', text)))


def test_one_connected_part_and_one_unconnected_part_gets_the_middle(setup, monkeypatch):
    _store, engine = setup
    seen = []
    monkeypatch.setattr('nucleus.dictionary.brief', lambda part: (seen.append(part) or read_part(part)))
    question = 'ALPHA feels right but I cannot tell how the app behaved?'
    label = graph_answers.label_question(question, engine, reading('ALPHA'), [])
    assert label.answer == 'not_sure'
    assert label.rule == 'question parts'
    assert label.touched == ('ALPHA',)
    assert label.connected == ('ALPHA',) and label.missing == ()
    assert seen == ['ALPHA feels right', 'I cannot tell how the app behaved?']
    assert label.parts[0].connected == ('ALPHA',)
    assert label.parts[1].words == () and label.parts[1].connected == ()
    assert label.ms < 300 and not label.budget_miss
    assert label.to_dict()['parts'][1]['text'] == 'I cannot tell how the app behaved?'


@pytest.mark.parametrize('question,expected', [
    ('ALPHA with BETA but ALPHA?', 'aligned'),
    ('ALPHA but BETA?', 'not_sure'),
    ('BETA but an unknown thing?', 'dont_know'),
    ('ALPHA. An unknown thing? ALPHA!', 'not_sure'),
])
def test_each_part_needs_a_path_from_at_least_one_word(setup, monkeypatch, question, expected):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', read_part)
    label = graph_answers.label_question(question, engine)
    assert label.answer == expected
    assert all(part.text in question for part in label.parts)
    assert not label.budget_miss and label.ms < 300


def test_single_part_keeps_the_existing_word_verdict_and_supplied_reading(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', never)
    label = graph_answers.label_question('One situation?', engine, reading('ALPHA', 'BETA'), [])
    assert label.answer == 'not_sure' and label.rule == 'word paths'
    assert label.parts[0].words == ('ALPHA', 'BETA')
    assert label.parts[0].missing == ('BETA',)


def test_all_part_paths_share_one_graph_query_and_one_budget(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', read_part)
    original = engine.label
    calls = []
    def measured(words):
        calls.append(tuple(words))
        return original(words)
    monkeypatch.setattr(engine, 'label', measured)
    label = graph_answers.label_question('ALPHA but BETA. ALPHA?', engine)
    assert calls == [('ALPHA', 'BETA')]
    assert label.ms < 300
    assert all(part.ms == label.ms and part.query_is_shared for part in label.parts)


def test_a_whole_question_phrase_never_connects_across_parts(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', lambda _: reading())
    # ALPHA's meaning contains "A clear sign."; neither part has that phrase.
    label = graph_answers.label_question('A clear but sign.', engine)
    assert label.answer == 'dont_know' and label.touched == ()


def test_part_budget_miss_has_no_guessed_answer(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', read_part)
    monkeypatch.setattr(engine, 'label', lambda _: Label(None, (), ('ALPHA',), {}, 301, True))
    label = graph_answers.label_question('ALPHA but unknown?', engine)
    assert label.answer is None and label.budget_miss and label.ms == 301


def test_the_exact_missing_part_is_visible_source_for_a_form(setup, monkeypatch):
    store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', read_part)
    screens = []
    monkeypatch.setattr('nucleus.forms.pick', lambda screen, **_: (screens.append(screen) or None, 'no approved forms'))
    question = 'ALPHA but I cannot establish how “the app” behaved?'
    result = ask.ask(question, store=store, brief=lambda _: reading('ALPHA'),
                     model_call=never, meaning_graph=engine)
    why = 'you said ALPHA. Your records do not show “I cannot establish how “the app” behaved?”.'
    assert result.answer == 'not_sure'
    assert result.words[0]['why'] == why and why in result.text
    assert result.records[0]['quote'] == 'A clear sign.'
    assert result.records[0]['kind'] == 'supports'
    assert len(result.records) == 1
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0
    trace = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert trace['label']['parts'][1]['text'] == 'I cannot establish how “the app” behaved?'
    assert trace['label']['parts'][1]['connected'] == []
    assert trace['total_ms'] < 300 and not trace['budget_miss']
    from nucleus.forms_middle import gap_span
    span = gap_span(screens[0].whys[0].text)
    assert span is not None
    assert screens[0].whys[0].text[slice(*span)] == 'Your records do not show “I cannot establish how “the app” behaved?”.'


def test_multiple_missing_parts_stay_exact_and_visible(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', read_part)
    question = 'ALPHA but I do not know? Yet “Nothing changed.”'
    label = graph_answers.label_question(question, engine)
    picture = graph_answers.paint(label.touched, engine, label)
    why = 'you said ALPHA. Your records do not show “I do not know?”. Your records do not show ““Nothing changed.””.'
    assert label.answer == 'not_sure'
    assert [part.text for part in label.parts] == ['ALPHA', 'I do not know?', '“Nothing changed.”']
    assert picture.words[0]['why'] == why and why in picture.text
    assert len(picture.records) == 1


def test_real_sized_graph_checks_sixteen_parts_in_one_300ms_budget(setup, monkeypatch):
    store, original = setup
    old = original.legacy_graph
    words = [Meaning('WORD ' + str(i), str(i), i, 'Exact meaning ' + str(i)) for i in range(140)]
    kinds = ['kind ' + str(i) for i in range(43)]
    for i in range(191):
        uri, text = CONNECTION_PREFIX + 'dense-' + str(i), 'Exact record ' + str(i)
        old.records[uri] = Record(uri, 'dense-' + str(i), text, '', '1', '', text)
        old.ledger.append({'claim': text, 'decision': 'accepted', 'at': '2026'})
    rows = [(word.word, 'dense-' + str((i * 10 + j) % 191), 'Exact record ' + str((i * 10 + j) % 191),
             '', 'links:fixture', 'fixture', 'fixture', 1, None, kinds[(i + j) % 43])
            for i, word in enumerate(words) for j in range(10)]
    store.connection.executemany('INSERT INTO links(word,record,quote,why,source,provider,model,found_at,thumb,kind) VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
    store.connection.commit()
    sources = store.path.parent / 'sources'
    (sources / 'dense.ttl').write_text('@prefix ex: <https://example.test/> .\n' + '\n'.join(
        f'ex:noise{i} ex:next{i % 14} ex:noise{i+1} ; ex:label "Noise {i}" ; ex:weight {i} .'
        for i in range(4300)))
    engine = build(store, old, words, kinds, accepted_dir=sources,
                   upper_path=sources / 'upper.ttl', axioms_path=sources / 'axioms.ttl')
    assert engine.stats['triples'] > 14000 and engine.stats['link_triples'] == 1400
    monkeypatch.setattr('nucleus.dictionary.brief', lambda part: reading(part))
    question = ' but '.join(word.word for word in words[:16])
    label = graph_answers.label_question(question, engine)
    assert label.answer == 'aligned' and len(label.parts) == 16
    assert all(len(part.records[part.words[0]]) == 10 for part in label.parts)
    assert not label.budget_miss and label.ms < 300
    # Part timings describe the same query; they must not create sixteen budgets.
    assert label.ms == label.parts[0].ms


@pytest.mark.parametrize('outcome', ['stopped', 'ask'])
def test_a_stopped_part_never_connects_from_its_returned_word_or_phrase_hits(setup, monkeypatch, outcome):
    _store, engine = setup
    stopped = dict(reading('ALPHA'), outcome=outcome)
    monkeypatch.setattr('nucleus.dictionary.brief', lambda _: stopped)
    monkeypatch.setattr('nucleus.phrases.PhraseIndex.lookup', never)
    monkeypatch.setattr(engine, 'label', never)
    with pytest.raises(ValueError, match='^dictionary stopped question part$'):
        graph_answers.label_question('A clear sign but another part?', engine)


@pytest.mark.parametrize('outcome', ['stopped', 'ask'])
def test_a_stopped_part_uses_the_named_count_fallback_with_the_original_question(setup, monkeypatch, outcome):
    store, engine = setup
    question = 'ALPHA but I cannot tell what happened?'
    whole_reading = reading('ALPHA')
    def part_reader(part):
        return dict(reading('ALPHA'), outcome=outcome) if part == 'ALPHA' else reading()
    monkeypatch.setattr('nucleus.dictionary.brief', part_reader)
    result = ask.ask(question, store=store, brief=lambda _: whole_reading,
                     model_call=never, meaning_graph=engine)
    trace = json.loads(next(step for step in result.steps if step['name'] == graph_answers.QUERY_STEP)['note'])
    assert result.question == question and result.reading == whole_reading
    assert store.question(result.question_id)['question'] == question
    assert result.answer == 'not_sure'  # Existing one-record count fallback.
    assert trace['rule'] == 'count rule'
    assert trace['error'] == 'dictionary stopped question part'
    assert trace['label'] is None and not trace['budget_miss']
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0


def test_an_invalid_part_reading_never_becomes_an_unconnected_guess(setup, monkeypatch):
    _store, engine = setup
    monkeypatch.setattr('nucleus.dictionary.brief', lambda _: None)
    monkeypatch.setattr(engine, 'label', never)
    with pytest.raises(ValueError, match='^dictionary returned invalid question part$'):
        graph_answers.label_question('ALPHA but another part?', engine)
