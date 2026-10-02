"""Real ASK evaluation keeps form conditions inside the exact painted screen."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import pytest
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDFS

from nucleus import forms, forms_middle, forms_sparql as sparql
from nucleus.dictionary import Meaning
from nucleus.graph import CONNECTION_PREFIX, Graph as LegacyGraph, Record
from nucleus.meaning_graph import MeaningGraph, kind_node, word_node

KINDS = ['depends on', 'supports', 'rejects', 'requires']
SCREEN = forms.Screen('not_sure', ('FLOW', 'LIFT'), (
    forms.Row('FLOW', 'r1', 'depends on', 'Interest lasts when there is feeling momentum.'),
    forms.Row('LIFT', 'r2', 'supports', 'Harmony among meaningful relationships.'),
), True, (forms.Meaning('FLOW', 'Momentum pulls at me, and can only be described as a feeling.'),),
    (forms.Why('FLOW fits here, but the records do not show what happened.'),), ('LIFT',))


def row_form(**changes):
    value = {'number': 'F-1', 'when': {'answer': 'not_sure', 'kinds_present': ['depends on']},
             'sentence': 'Your rows say {word} depends on {count} things you have written down.',
             'status': 'approved', 'author': 'isolated fixture', 'date': '2026-10-02'}
    value.update(changes)
    return value


def test_compiler_canonicalizes_condition_and_middle_word_order():
    first = {'word_count': {'max': 4, 'min': 2}, 'answer': 'not_sure',
             'kinds_present': ['supports', 'depends on'], 'missing_why': True}
    second = {'missing_why': True, 'kinds_present': ['depends on', 'supports'],
              'answer': 'not_sure', 'word_count': {'min': 2, 'max': 4}}
    query = sparql.compile_when(first, kinds=KINDS)
    assert query == sparql.compile_when(second, kinds=KINDS)
    assert 'ASK WHERE' in query and 'GRAPH ?screen' in query
    assert str(kind_node('depends on')) in query
    assert sparql.matches(first, SCREEN, kinds=KINDS)


@pytest.mark.parametrize('when, expected', [
    ({'answer': 'not_sure'}, True), ({'answer': 'aligned'}, False),
    ({'kinds_present': ['depends on', 'supports']}, True),
    ({'kinds_present': ['depends on', 'rejects']}, False),
    ({'kinds_absent': ['rejects', 'requires']}, True), ({'kinds_absent': ['supports']}, False),
    ({'record_count': {'min': 2, 'max': 3}}, True), ({'record_count': {'min': 3}}, False),
    ({'word_count': {'min': 1, 'max': 2}}, True), ({'word_count': {'max': 1}}, False),
    ({'missing_links': True}, True), ({'missing_links': False}, False),
    ({'missing_why': True}, True), ({'missing_why': False}, False),
    ({'record_count': 2, 'word_count': 2}, True), ({'record_count': 1}, False),
])
def test_each_structured_condition_is_executed_as_ask(when, expected):
    assert sparql.matches(when, SCREEN, kinds=KINDS) is expected


def test_counts_include_visible_unknown_kind_rows_and_allow_zero_rows():
    unknown = replace(SCREEN, rows=(forms.Row('FLOW', 'unknown', None, 'Exact visible quote.'),))
    assert sparql.matches({'record_count': {'min': 1}, 'kinds_absent': ['supports']}, unknown, kinds=KINDS)
    empty = forms.Screen('dont_know', (), ())
    assert sparql.matches({'record_count': 0, 'word_count': 0, 'missing_links': False}, empty, kinds=KINDS)


@pytest.mark.parametrize('dataset', [False, True])
def test_hidden_loaded_edges_never_supply_present_or_defeat_absent_conditions(dataset):
    loaded = Dataset(default_union=True) if dataset else Graph()
    source = loaded.default_graph if dataset else loaded
    source.add((word_node('FLOW'), kind_node('rejects'), URIRef('urn:hidden:record')))
    before = set(source)
    before_quads = set(loaded.quads()) if dataset else None
    assert not sparql.matches({'kinds_present': ['rejects']}, SCREEN, kinds=KINDS, graph=loaded)
    assert sparql.matches({'kinds_absent': ['rejects']}, SCREEN, kinds=KINDS, graph=loaded)
    assert set(source) == before
    if dataset:
        assert set(loaded.quads()) == before_quads


def test_hidden_screen_metadata_cannot_change_counts_answer_or_gaps():
    loaded = Dataset(default_union=True)
    hidden = loaded.graph(URIRef('urn:other:screen'))
    node = URIRef('urn:other:screen')
    for predicate, value in [(sparql.SCREEN.answer, 'aligned'), (sparql.SCREEN.wordCount, 20),
                             (sparql.SCREEN.recordCount, 20), (sparql.SCREEN.missingWhy, False)]:
        hidden.add((node, predicate, Literal(value)))
    before = set(loaded.quads())
    assert not sparql.matches({'answer': 'aligned'}, SCREEN, kinds=KINDS, graph=loaded)
    assert not sparql.matches({'word_count': {'min': 20}}, SCREEN, kinds=KINDS, graph=loaded)
    assert not sparql.matches({'record_count': {'min': 20}}, SCREEN, kinds=KINDS, graph=loaded)
    assert not sparql.matches({'missing_why': False}, SCREEN, kinds=KINDS, graph=loaded)
    assert set(loaded.quads()) == before


def test_queries_share_the_loaded_store_and_copy_whole_visible_literals(monkeypatch):
    loaded = Dataset(default_union=True)
    text = 'FÖÖ " } SERVICE <https://example.invalid/> { ?x ?y ?z } # {tag}'
    screen = forms.Screen('aligned', (text,), (forms.Row(text, 'r1', None, text),),
                          meanings=(forms.Meaning(text, text),), whys=(forms.Why(text),))
    original = loaded.query
    captures = []
    def query(statement, **kwargs):
        context = kwargs['initBindings']['screen']
        snapshot = loaded.graph(context)
        assert snapshot.store is loaded.store
        captures.append(set(snapshot))
        assert statement is sparql._prepared_query(sparql.compile_when({'answer': 'aligned'}, kinds=KINDS))
        return original(statement, **kwargs)
    monkeypatch.setattr(loaded, 'query', query)
    assert sparql.matches({'answer': 'aligned'}, screen, kinds=KINDS, graph=loaded)
    assert captures and sum(value == Literal(text) for _, _, value in captures[0]) >= 4
    assert len(loaded) == 0


def test_projected_records_keep_exact_full_connection_uris(monkeypatch):
    loaded = Dataset(default_union=True)
    screen = replace(SCREEN, rows=(SCREEN.rows[0], replace(SCREEN.rows[1], record=CONNECTION_PREFIX + 'r2')))
    original = loaded.query
    def query(statement, **kwargs):
        projected = loaded.graph(kwargs['initBindings']['screen'])
        assert (word_node('FLOW'), kind_node('depends on'), URIRef(CONNECTION_PREFIX + 'r1')) in projected
        assert (word_node('LIFT'), kind_node('supports'), URIRef(CONNECTION_PREFIX + 'r2')) in projected
        assert (URIRef(CONNECTION_PREFIX + 'r1'), sparql.SCREEN.recordId, Literal('r1')) in projected
        assert (URIRef(CONNECTION_PREFIX + 'r2'), sparql.SCREEN.recordId, Literal(CONNECTION_PREFIX + 'r2')) in projected
        return original(statement, **kwargs)
    monkeypatch.setattr(loaded, 'query', query)
    assert sparql.matches({'answer': 'not_sure'}, screen, kinds=KINDS, graph=loaded)


def test_prepared_queries_are_bounded_and_reused(monkeypatch):
    sparql._prepared_query.cache_clear()
    parses = []
    original = sparql.prepareQuery
    def prepare(text):
        parses.append(text)
        return original(text)
    monkeypatch.setattr(sparql, 'prepareQuery', prepare)
    when = {'kinds_present': ['supports', 'depends on']}
    for _ in range(3):
        assert sparql.matches(when, SCREEN, kinds=KINDS)
    assert parses == [sparql.compile_when(when, kinds=KINDS)]
    assert sparql._prepared_query.cache_info().maxsize == 512


def test_shared_graph_queries_can_overlap_without_parser_or_screen_cross_talk():
    loaded = Dataset(default_union=True)
    empty = forms.Screen('dont_know', (), ())
    def evaluate(index):
        return sparql.matches({'kinds_present': ['depends on']}, SCREEN if index % 2 else empty,
                              kinds=KINDS, graph=loaded)
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(evaluate, range(20))) == [bool(i % 2) for i in range(20)]
    assert len(loaded) == 0


def test_budget_callback_can_stop_selection_after_context_cleanup():
    class GraphBudgetExceeded(Exception):
        pass
    loaded = Dataset(default_union=True)
    def stop(ms):
        raise GraphBudgetExceeded('isolated aggregate budget')
    with pytest.raises(GraphBudgetExceeded):
        sparql.matches({'answer': 'not_sure'}, SCREEN, kinds=KINDS, graph=loaded, query_trace=stop)
    assert len(loaded) == 0


def test_label_and_representative_form_asks_share_a_300ms_budget_on_a_large_graph():
    source = Graph()
    for i in range(5000):
        node = URIRef(f'urn:noise:{i}')
        source.add((node, URIRef('urn:noise:next'), URIRef(f'urn:noise:{i+1}')))
        source.add((node, URIRef('urn:noise:label'), Literal(f'Noise {i}')))
        source.add((node, URIRef('urn:noise:weight'), Literal(i)))
    first = URIRef(CONNECTION_PREFIX + 'r1')
    middle = URIRef('urn:source:middle')
    source.add((word_node('FLOW'), RDFS.label, Literal('FLOW')))
    source.add((word_node('FLOW'), kind_node('depends on'), middle))
    source.add((middle, kind_node('supports'), first))
    record = Record(str(first), 'r1', SCREEN.rows[0].quote, 'observation', '0.9', '2026-10-02', '')
    legacy = LegacyGraph({record.uri: record}, [{'claim': record.label, 'decision': 'accepted', 'at': '2026-10-02'}], '', '')
    meanings = [Meaning(word, str(i), i, 'His exact meaning ' + word) for i, word in enumerate(SCREEN.words)]
    engine = MeaningGraph(source, {}, (), legacy, meanings, KINDS)
    before = set(engine.graph.quads())
    checks = [({'answer': 'not_sure'}, True),
              ({'kinds_present': ['depends on', 'supports']}, True),
              ({'kinds_absent': ['rejects']}, True),
              ({'record_count': {'min': 2}, 'word_count': {'min': 2}}, True),
              ({'missing_links': True, 'missing_why': True}, True),
              ({'answer': 'aligned'}, False),
              ({'kinds_present': ['rejects']}, False)]
    # A cold first selection includes parsing each representative ASK once.
    sparql._prepared_query.cache_clear()
    timings = []
    started = perf_counter()
    label = engine.label(SCREEN.words)
    for when, expected in checks:
        assert sparql.matches(when, SCREEN, kinds=KINDS, graph=engine.graph, query_trace=timings.append) is expected
    elapsed = (perf_counter() - started) * 1000
    assert len(source) > 14000 and label.answer == 'not_sure'
    assert not label.budget_miss and label.ms + sum(timings) < 300 and elapsed < 300
    assert set(engine.graph.quads()) == before


def test_query_failures_refuse_without_leaving_a_projection(monkeypatch):
    loaded = Dataset(default_union=True)
    source = (URIRef('urn:source'), URIRef('urn:predicate'), Literal('unchanged'))
    loaded.default_graph.add(source)
    before = set(loaded.quads())
    durations = []
    def fail(*args, **kwargs):
        raise RuntimeError('isolated ASK failure')
    monkeypatch.setattr(loaded, 'query', fail)
    with pytest.raises(forms.Refused, match='form ASK failed'):
        sparql.matches({'answer': 'not_sure'}, SCREEN, kinds=KINDS, graph=loaded, query_trace=durations.append)
    assert set(loaded.quads()) == before
    assert len(durations) == 1 and durations[0] >= 0


def test_overlapping_screen_contexts_cannot_satisfy_one_another(monkeypatch):
    loaded = Dataset(default_union=True)
    original = loaded.query
    contexts = []
    def query(statement, **kwargs):
        contexts.append(kwargs['initBindings']['screen'])
        if len(contexts) == 1:
            empty = forms.Screen('dont_know', (), ())
            assert not sparql.matches({'kinds_present': ['depends on']}, empty, kinds=KINDS, graph=loaded)
        return original(statement, **kwargs)
    monkeypatch.setattr(loaded, 'query', query)
    assert sparql.matches({'kinds_present': ['depends on']}, SCREEN, kinds=KINDS, graph=loaded)
    assert len(contexts) == 2 and len(set(contexts)) == 2
    assert len(loaded) == 0


@pytest.mark.parametrize('when', [
    'ASK WHERE { ?x ?y ?z }', {'query': 'SERVICE <https://example.invalid/> {}'}, {},
    {'record_count': True}, {'word_count': {'min': 2, 'max': 1}},
    {'kinds_present': ['depends on', 'depends on']}, {'missing_why': 'true'},
    {'kinds_present': ['rejects'], 'kinds_absent': ['rejects']},
])
def test_compiler_refuses_raw_queries_and_malformed_structured_conditions(when):
    with pytest.raises(forms.Refused):
        sparql.compile_when(when, kinds=KINDS)


def test_day_and_preview_share_ask_but_status_still_gates_filling(monkeypatch):
    calls = []
    original = sparql.matches
    def capture(when, screen, **kwargs):
        calls.append(when)
        return original(when, screen, **kwargs)
    monkeypatch.setattr(sparql, 'matches', capture)
    proposal = row_form(status='proposed')
    assert forms.fill(proposal, SCREEN, kinds=KINDS) is None and calls == []
    assert forms.preview(proposal, SCREEN, kinds=KINDS)
    assert forms.fill(row_form(), SCREEN, kinds=KINDS)
    assert len(calls) == 2


def test_ask_success_does_not_bypass_middle_blank_or_complete_row_guards():
    value = row_form(when={'answer': 'not_sure', 'kinds_absent': ['rejects']},
                     sentence=forms_middle.HEADS[0] + forms_middle.TAILS['absent_kind'])
    incomplete = replace(SCREEN, rows=(replace(SCREEN.rows[0], kind=None),), middle_words_complete=False)
    assert sparql.matches(value['when'], incomplete, kinds=KINDS)
    assert forms.fill(value, incomplete, kinds=KINDS) is None
    assert forms.fill(value, replace(SCREEN, meanings=()), kinds=KINDS) is None


def test_filled_provenance_and_query_duration_remain_visible():
    durations = []
    loaded = Dataset(default_union=True)
    filled = forms.fill(row_form(), SCREEN, kinds=KINDS, graph=loaded, query_trace=durations.append)
    assert filled.text == 'Your rows say FLOW depends on 1 things you have written down.'
    assert [(p.text, p.source) for p in filled.parts if p.source != 'form.sentence'] == [
        ('FLOW', 'screen.words[0]'), ('1', "count(screen.rows.kind == 'depends on')")]
    assert len(durations) == 1 and durations[0] >= 0
    assert len(loaded) == 0
