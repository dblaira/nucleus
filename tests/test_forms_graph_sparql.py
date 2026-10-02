"""Graph-part form conditions run real isolated SPARQL over checked sources."""
from dataclasses import replace

import pytest
from rdflib import Dataset, Literal, URIRef

from nucleus import forms, forms_sparql
from nucleus.graph import CONNECTION_PREFIX


KINDS = ['supports']


def screen():
    return forms.Screen('not_sure', ('ALPHA',), (), meanings=(forms.Meaning('ALPHA', 'His exact meaning.'),),
                        parts=(forms.GraphPart('ALPHA feels right', ('ALPHA',), ('ALPHA',), (),
                                               {'ALPHA': (CONNECTION_PREFIX + 'r',)}),
                               forms.GraphPart('the app is a mystery?', (), (), (), {})))


def test_graph_parts_asks_for_both_graph_connected_and_open_parts():
    value = screen()
    when = {'answer': 'not_sure', 'graph_parts': True}
    query = forms_sparql.compile_when(when, kinds=KINDS)
    assert 'ASK WHERE' in query and 'GRAPH ?screen' in query
    assert 'screen:graphConnected true' in query and 'screen:graphConnected false' in query
    assert forms_sparql.matches(when, value, kinds=KINDS)
    assert not forms_sparql.matches(when, replace(value, parts=()), kinds=KINDS)
    assert not forms_sparql.matches(when, replace(value, parts=(value.parts[0],)), kinds=KINDS)
    assert not forms_sparql.matches(when, replace(value, parts=(value.parts[1],)), kinds=KINDS)
    assert not forms_sparql.matches(when, replace(value, answer='aligned'), kinds=KINDS)


def test_graph_part_literals_and_paths_are_projected_exactly_and_cleaned(monkeypatch):
    loaded = Dataset(default_union=True)
    source = (URIRef('urn:source'), URIRef('urn:predicate'), Literal('unchanged'))
    loaded.default_graph.add(source)
    before = set(loaded.quads())
    value = screen()
    exact = 'I cannot claim “this”. } SERVICE <https://example.invalid/> { ?a ?b ?c } # {word}'
    value = replace(value, parts=(value.parts[0], replace(value.parts[1], text=exact)))
    original = loaded.query
    snapshots = []
    def query(statement, **kwargs):
        context = kwargs['initBindings']['screen']
        graph = loaded.graph(context)
        snapshots.append(set(graph))
        assert (URIRef(str(context) + '/part/1'), forms_sparql.SCREEN.text, Literal(exact)) in graph
        assert (URIRef(str(context) + '/part/0'), forms_sparql.SCREEN.record, URIRef(CONNECTION_PREFIX + 'r')) in graph
        assert (URIRef(str(context) + '/part/0'), forms_sparql.SCREEN.source, Literal('screen.parts[0].text')) in graph
        return original(statement, **kwargs)
    monkeypatch.setattr(loaded, 'query', query)
    assert forms_sparql.matches({'graph_parts': True}, value, kinds=KINDS, graph=loaded)
    assert snapshots and set(loaded.quads()) == before


def test_hidden_graph_part_flags_never_supply_a_screen_part():
    loaded = Dataset(default_union=True)
    hidden = loaded.graph(URIRef('urn:hidden:screen'))
    node, lined, opened = (URIRef('urn:hidden:' + name) for name in ('screen', 'lined', 'open'))
    hidden.add((node, forms_sparql.SCREEN.graphParts, Literal(True)))
    hidden.add((node, forms_sparql.SCREEN.part, lined))
    hidden.add((node, forms_sparql.SCREEN.part, opened))
    hidden.add((lined, forms_sparql.SCREEN.graphConnected, Literal(True)))
    hidden.add((opened, forms_sparql.SCREEN.graphConnected, Literal(False)))
    before = set(loaded.quads())
    value = replace(screen(), parts=())
    assert not forms_sparql.matches({'graph_parts': True}, value, kinds=KINDS, graph=loaded)
    assert set(loaded.quads()) == before


@pytest.mark.parametrize('value', ['true', 1, None])
def test_graph_part_condition_requires_a_boolean(value):
    with pytest.raises(forms.Refused, match='graph_parts must be boolean'):
        forms_sparql.compile_when({'graph_parts': value}, kinds=KINDS)


def test_graph_part_ask_budget_callback_runs_after_projection_cleanup():
    loaded = Dataset(default_union=True)
    class BudgetMiss(Exception):
        pass
    def stop(_milliseconds):
        raise BudgetMiss('budget exceeded')
    with pytest.raises(BudgetMiss):
        forms_sparql.matches({'graph_parts': True}, screen(), kinds=KINDS, graph=loaded, query_trace=stop)
    assert len(loaded) == 0
