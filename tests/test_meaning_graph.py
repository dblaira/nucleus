"""Forward RDF paths stay grounded in source triples and valid copied links."""
import hashlib
from pathlib import Path
import time

import pytest
from rdflib import Graph as RDFGraph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from nucleus import meaning_graph as engine, store as store_module
from nucleus.dictionary import Meaning
from nucleus.graph import CONNECTION_PREFIX, Graph, Record
from nucleus.store import Store

EX = 'https://example.test/'
KINDS = ['depends on', 'supports', 'rejects']


def legacy():
    records = {}
    ledger = []
    for name, label, accepted in [('r1', 'The work feels clear', True), ('r2', 'The next step feels light', True),
                                   ('r3', 'An unapproved record', False)]:
        uri = CONNECTION_PREFIX + name
        records[uri] = Record(uri, name, label, 'observation', '0.9', '2026-10-02', f'understood:label "{label}" ;')
        ledger.append({'claim': label, 'decision': 'accepted' if accepted else 'rejected', 'at': '2026-10-02'})
    return Graph(records, ledger, '', '')


def meanings(*words):
    return [Meaning(word, str(i), i, 'His exact meaning ' + word) for i, word in enumerate(words, 1)]


@pytest.fixture
def fixture(tmp_path):
    accepted = tmp_path / 'sources' / 'accepted'
    accepted.mkdir(parents=True)
    prefix = f'@prefix ex: <{EX}> .\n@prefix rdfs: <{RDFS}> .\n@prefix rdf: <{RDF}> .\n@prefix owl: <{OWL}> .\n'
    text = prefix + f'''
ex:flow rdfs:label "FLOW" ; ex:leadsTo ex:middle .
ex:middle ex:reaches <{CONNECTION_PREFIX}r1> .
ex:lift rdfs:label "LIFT" .
ex:value1 rdfs:label "VALUE" ; ex:reaches <{CONNECTION_PREFIX}r1> .
ex:value2 rdfs:label "VALUE" .
ex:unknown rdfs:label "UNKNOWN" ; ex:reaches <{CONNECTION_PREFIX}r1> .
ex:back rdfs:label "BACK" .
<{CONNECTION_PREFIX}r1> ex:leadsTo ex:back .
ex:typed rdfs:label "TYPE" ; rdf:type <{CONNECTION_PREFIX}r1> .
ex:schema rdfs:label "SCHEMA" ; rdfs:subClassOf <{CONNECTION_PREFIX}r1> .
ex:metadata rdfs:label "META" ; rdfs:seeAlso <{CONNECTION_PREFIX}r1> .
ex:rejected rdfs:label "REJECTED" ; ex:reaches <{CONNECTION_PREFIX}r3> .
ex:ontology a owl:Ontology ; owl:imports <https://never-fetch.example/missing.ttl> .
ex:backwards a owl:ObjectProperty ; owl:inverseOf ex:leadsTo .
'''
    (accepted / 'connections.ttl').write_text(text)
    upper = tmp_path / 'sources' / 'upper.ttl'
    upper.write_text(prefix + 'ex:Thing a owl:Class .')
    axioms = tmp_path / 'sources' / 'axioms.ttl'
    axioms.write_text(prefix + 'ex:axiom ex:antecedent ex:flow ; ex:consequent ex:lift .')
    copy_area = tmp_path / 'review'
    store = Store(copy_area / 'copy.sqlite3')
    words = meanings('FLOW', 'LIFT', 'VALUE', 'BACK', 'TYPE', 'SCHEMA', 'META', 'REJECTED')
    yield store, legacy(), words, {'accepted_dir': accepted, 'upper_path': upper, 'axioms_path': axioms}
    store.connection.close()


def build(fixture, **kwargs):
    store, graph, words, paths = fixture
    return engine.build(store, graph, words, KINDS, **paths, **kwargs)


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_forward_multihop_paths_label_all_some_and_none(fixture):
    graph = build(fixture)
    result = graph.label(['FLOW', 'FLOW'])
    assert result.answer == 'aligned' and result.connected == ('FLOW',) and result.missing == ()
    assert result.records == {'FLOW': (CONNECTION_PREFIX + 'r1',)}
    assert graph.label(['FLOW', 'LIFT']).answer == 'not_sure'
    assert graph.label(['LIFT']).answer == 'dont_know'
    assert graph.label([]).answer == 'dont_know'
    assert not result.budget_miss and result.ms < 300
    assert '+ ?record' in graph.path_query
    assert graph.legacy_graph is fixture[1] and graph.meanings == tuple(fixture[2])


def test_unknown_ambiguous_reverse_schema_and_rejected_endpoints_stay_missing(fixture):
    graph = build(fixture)
    words = ['UNKNOWN', 'VALUE', 'BACK', 'TYPE', 'SCHEMA', 'META', 'REJECTED']
    result = graph.label(words)
    assert result.answer == 'dont_know' and result.missing == tuple(words)
    assert graph.word_node('FLOW') == URIRef(EX + 'flow')
    assert graph.word_node('VALUE') == engine.word_node('VALUE')
    assert graph.word_node('UNKNOWN') == engine.word_node('UNKNOWN')
    assert (URIRef(EX + 'back'), URIRef(EX + 'leadsTo'), URIRef(CONNECTION_PREFIX + 'r1')) not in graph.graph
    assert all(p not in (RDF.type, RDFS.subClassOf, RDFS.seeAlso, OWL.imports, OWL.inverseOf) for p in graph.predicates)
    assert (URIRef(CONNECTION_PREFIX + 'r3'), engine.ACCEPTED_RECORD, Literal(True)) not in graph.graph


def test_copied_links_require_exact_word_kind_accepted_record_and_quote(fixture):
    store = fixture[0]
    examples = [('LIFT', 'r1', 'The work feels clear', 'depends on', None),
                ('VALUE', 'r1', 'The work feels clear', 'supports', 0),
                ('FLOW ', 'r1', 'The work feels clear', 'supports', None),
                ('META', 'r1', 'The work feels clear', 'made up', None),
                ('TYPE', 'r3', 'An unapproved record', 'supports', None),
                ('SCHEMA', 'r1', 'The work felt clear', 'supports', None),
                ('BACK', 'missing', 'The work feels clear', 'supports', None)]
    for word, record, text, kind, thumb in examples:
        store.add_link(word, record, text, 'Exact stored why', 'links:fixture', 'fixture', 'fixture', kind=kind)
        if thumb == 0:
            store.thumb(word, record, False)
    before = store.connection.execute('SELECT * FROM links ORDER BY word,record').fetchall()
    graph = build(fixture)
    assert graph.label(['LIFT']).answer == 'aligned'
    assert graph.stats['link_triples'] == 1
    assert graph.stats['link_refusal_reasons'] == {'thumbed down': 1, 'unknown dictionary word': 1,
        'unknown middle word': 1, 'record is not accepted': 2, 'quote is not exact': 1}
    assert graph.links_for('LIFT')[0]['quote'] == 'The work feels clear'
    assert graph.links_for('LIFT')[0]['why'] == 'Exact stored why'
    assert (graph.word_node('LIFT'), engine.kind_node('depends on'), URIRef(CONNECTION_PREFIX + 'r1')) in graph.graph
    assert store.connection.execute('SELECT * FROM links ORDER BY word,record').fetchall() == before


def test_thumb_refresh_removes_only_derived_links(fixture):
    store = fixture[0]
    store.add_link('LIFT', 'r1', 'The work feels clear', 'Why exact', 'links:fixture', '?', '?', kind='depends on')
    graph = build(fixture)
    source = set(graph._source_triples)
    assert graph.label(['LIFT']).answer == 'aligned'
    store.thumb('LIFT', 'r1', False)
    graph.refresh_links(store)
    assert graph.label(['LIFT']).answer == 'dont_know'
    assert graph.links_for('LIFT') == []
    assert source <= set(graph.graph.triples((None, None, None)))
    assert graph.label(['FLOW']).answer == 'aligned'


def test_refresh_rechecks_export_aliases_before_any_source_write(fixture):
    store, _, _, paths = fixture
    output = store.path.parent / 'derived.ttl'
    graph = build(fixture, output_path=output)
    source_before = paths['upper_path'].read_bytes()
    temporary = output.with_name(output.name + '.tmp')
    temporary.hardlink_to(paths['upper_path'])
    with pytest.raises(ValueError, match='read only'):
        graph.refresh_links(store)
    assert paths['upper_path'].read_bytes() == source_before


def test_sources_are_read_only_exact_duplicate_filename_excluded_and_derived_export_stays_in_copy(fixture):
    store, old, words, paths = fixture
    excluded = paths['accepted_dir'] / engine.EXCLUDED_FILE
    excluded.write_text('invalid Turtle that must never be read')
    files = engine.source_paths(**paths)
    before = hashes(files)
    store.add_link('LIFT', 'r1', 'The work feels clear', 'Why', 'links:fixture', '?', '?', kind='supports')
    output = store.path.parent / 'meaning-links.ttl'
    graph = build(fixture, output_path=output)
    assert graph.stats['source_hashes'] == before and hashes(files) == before
    assert len(files) == graph.stats['source_files'] == 3
    assert str(excluded) not in graph.stats['source_hashes']
    exported = RDFGraph().parse(output, format='turtle')
    assert (graph.word_node('LIFT'), engine.kind_node('supports'), URIRef(CONNECTION_PREFIX + 'r1')) in exported
    assert (URIRef(EX + 'flow'), URIRef(EX + 'leadsTo'), URIRef(EX + 'middle')) not in exported
    assert len(exported) < graph.stats['triples']
    assert graph.stats['build_ms'] > 0
    with pytest.raises(ValueError, match='copy area'):
        build(fixture, output_path=paths['upper_path'])
    with pytest.raises(ValueError, match='requires a database copy'):
        engine.build(None, old, words, KINDS, **paths, output_path=output)
    # Source-only load is explicit and needs no copy connection or exported file.
    source_only = engine.build(None, old, words, KINDS, **paths)
    assert source_only.stats['link_triples'] == 0 and hashes(files) == before


def test_export_refuses_source_aliases_live_aliases_database_and_escaped_temporary_path(fixture, monkeypatch):
    store, _, _, paths = fixture
    source_alias = store.path.parent / 'alias.ttl'
    source_alias.hardlink_to(paths['upper_path'])
    with pytest.raises(ValueError, match='read only'):
        build(fixture, output_path=source_alias)
    with pytest.raises(ValueError, match='copy area'):
        build(fixture, output_path=store.path)
    output = store.path.parent / 'output.ttl'
    temporary = output.with_name(output.name + '.tmp')
    temporary.symlink_to(paths['upper_path'])
    with pytest.raises(ValueError, match='copy area'):
        build(fixture, output_path=output)
    temporary.unlink()
    isolated_live = store.path.parent.parent / 'isolated-live.sqlite3'
    isolated_live.write_bytes(b'untouched stand-in')
    monkeypatch.setattr(store_module, 'STORE_PATH', isolated_live)
    live_alias = store.path.parent / 'live-alias.ttl'
    live_alias.hardlink_to(isolated_live)
    with pytest.raises(ValueError, match='never the live'):
        build(fixture, output_path=live_alias)


def test_malformed_source_and_missing_file_refused_without_changing_output(fixture):
    store, _, _, paths = fixture
    output = store.path.parent / 'existing.ttl'
    output.write_text('kept output')
    bad = paths['accepted_dir'] / 'new-source.ttl'
    bad.write_text('not Turtle')
    with pytest.raises(ValueError, match='source refused'):
        build(fixture, output_path=output)
    assert output.read_text() == 'kept output'
    bad.unlink()
    paths['upper_path'].unlink()
    with pytest.raises(ValueError, match='missing meaning graph source'):
        build(fixture, output_path=output)
    assert output.read_text() == 'kept output'


def test_excluded_turtle_and_all_ontology_locations_remain_read_only(fixture):
    store, old, words, paths = fixture
    excluded = paths['accepted_dir'] / engine.EXCLUDED_FILE
    excluded.write_text('exact excluded historical text')
    before = excluded.read_bytes()
    alias = store.path.parent / 'excluded-alias.ttl'
    alias.hardlink_to(excluded)
    with pytest.raises(ValueError, match='read only'):
        build(fixture, output_path=alias)
    output = store.path.parent / 'derived.ttl'
    output.with_name(output.name + '.tmp').hardlink_to(excluded)
    with pytest.raises(ValueError, match='read only'):
        build(fixture, output_path=output)
    assert excluded.read_bytes() == before
    # Even a deliberately misplaced test copy grants no write access to Ontology.
    misplaced = Store(paths['accepted_dir'] / 'copy.sqlite3')
    try:
        with pytest.raises(ValueError, match='read only'):
            engine.build(misplaced, old, words, KINDS, **paths,
                         output_path=paths['accepted_dir'] / 'new-derived.ttl')
    finally:
        misplaced.connection.close()


def test_copy_links_cannot_be_read_from_a_live_alias(fixture, monkeypatch):
    store = fixture[0]
    monkeypatch.setattr(store_module, 'STORE_PATH', store.path)
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match='never the live'):
        build(fixture)
    assert store.path.read_bytes() == before


def test_budget_miss_returns_no_graph_verdict(fixture, monkeypatch):
    graph = build(fixture)
    readings = iter([0.0, 0.301])
    monkeypatch.setattr(engine.time, 'perf_counter', lambda: next(readings))
    result = graph.label(['FLOW'])
    assert result.budget_miss and result.answer is None and result.ms == 301
    assert result.connected == ('FLOW',) and result.records['FLOW']


def test_adjacency_projection_preserves_original_path_predicates_and_direction(fixture):
    graph = build(fixture)
    path = graph.asserted_path('FLOW', CONNECTION_PREFIX + 'r1')
    assert path == ((URIRef(EX + 'flow'), URIRef(EX + 'leadsTo'), URIRef(EX + 'middle')),
                    (URIRef(EX + 'middle'), URIRef(EX + 'reaches'), URIRef(CONNECTION_PREFIX + 'r1')))
    assert graph.asserted_path('BACK', CONNECTION_PREFIX + 'r1') == ()
    for start, _, end in graph.forward.triples((None, engine.FORWARD_EDGE, None)):
        assert graph.forward_sources[(start, end)]
        assert all(triple in graph.relations for triple in graph.forward_sources[(start, end)])
    assert not list(graph.graph.triples((None, engine.FORWARD_EDGE, None)))


def test_dense_real_sized_graph_and_16_touched_words_fit_one_300ms_budget(fixture):
    store, old, _, paths = fixture
    kinds = [f'kind {i}' for i in range(43)]
    words = meanings(*(f'WORD {i}' for i in range(140)))
    for i in range(191):
        uri, text = CONNECTION_PREFIX + f'dense-{i}', f'Exact record {i}'
        old.records[uri] = Record(uri, f'dense-{i}', text, 'observation', '0.9', '2026-10-02', text)
        old.ledger.append({'claim': text, 'decision': 'accepted', 'at': '2026-10-02'})
    rows = [(word.word, f'dense-{(i * 10 + j) % 191}', f'Exact record {(i * 10 + j) % 191}',
             'Exact why', 'links:fixture', '?', '?', 1, None, kinds[(i + j) % 43])
            for i, word in enumerate(words) for j in range(10)]
    store.connection.executemany('INSERT INTO links(word,record,quote,why,source,provider,model,found_at,thumb,kind) VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
    store.connection.commit()
    source = paths['accepted_dir'] / 'dense.ttl'
    source.write_text('@prefix ex: <https://example.test/> .\n' + '\n'.join(
        f'ex:noise{i} ex:next{i % 14} ex:noise{i+1} ; ex:label "Noise {i}" ; ex:weight {i} .'
        for i in range(4300)))
    graph = engine.build(store, old, words, kinds, **paths)
    assert graph.stats['triples'] > 14000 and graph.stats['link_triples'] == 1400
    started = time.perf_counter()
    result = graph.label([word.word for word in words[:16]])
    wall_ms = (time.perf_counter() - started) * 1000
    assert result.answer == 'aligned' and len(result.connected) == 16 and result.missing == ()
    assert all(len(records) == 10 for records in result.records.values())
    assert not result.budget_miss and result.ms < 300 and wall_ms < 300


def test_real_sized_document_sparql_multihop_path_stays_under_300ms(fixture):
    store, old, words, paths = fixture
    # Larger than the current 12,815-triple source union; unrelated metadata cannot
    # turn into paths. These are portable records, not Adam's runtime database.
    large = paths['accepted_dir'] / 'large.ttl'
    lines = ['@prefix ex: <https://example.test/> .']
    for i in range(5500):
        lines.append(f'ex:noise{i} ex:next ex:noise{i+1} ; ex:label "Noise {i}" ; ex:weight {i} .')
    large.write_text('\n'.join(lines))
    graph = build(fixture)
    assert graph.stats['source_triples'] > 16000
    started = time.perf_counter()
    result = graph.label(['FLOW', 'LIFT', 'VALUE', 'UNKNOWN'])
    wall_ms = (time.perf_counter() - started) * 1000
    assert result.answer == 'not_sure'
    assert result.connected == ('FLOW',) and result.missing == ('LIFT', 'VALUE', 'UNKNOWN')
    assert not result.budget_miss and result.ms < 300 and wall_ms < 300
