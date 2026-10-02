import json
from pathlib import Path

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
