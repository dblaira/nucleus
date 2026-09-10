import json
from pathlib import Path

from nucleus.graph import load_graph, normalize_claim, parse_graph

TTL = '''@prefix understood: <https://understood.app/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://understood.app/ontology/connection/conn-obs-a> a understood:Connection ;
  understood:label "Focus and Sleep rise together in the same week" ;
  understood:connectionType "observed_correlation" ;
  understood:inLifeDomain <https://understood.app/ontology/domain/focus> ;
  understood:strength "0.42"^^xsd:decimal ;
  understood:frequency "sometimes" ;
  understood:acceptedAt "2026-07-02T00:30:11Z"^^xsd:dateTime ;
  .

<https://understood.app/ontology/connection/conn-obs-b> a understood:Connection ;
  understood:label "Adam builds external rules like \\"if I can't say I can't play\\" to hold himself to plans" ;
  understood:connectionType "stated_relationship" ;
  understood:inLifeDomain <https://understood.app/ontology/domain/work> ;
  understood:strength "0.70"^^xsd:decimal ;
  understood:acceptedAt "2026-07-10T00:00:00Z"^^xsd:dateTime ;
  .

<https://understood.app/ontology/connection/conn-obs-c> a understood:Connection ;
  understood:label "A claim Adam rejected" ;
  understood:connectionType "observed_pattern" ;
  understood:inLifeDomain <https://understood.app/ontology/domain/work> ;
  understood:strength "0.50"^^xsd:decimal ;
  understood:acceptedAt "2026-07-10T00:00:00Z"^^xsd:dateTime ;
  .
'''

LEDGER = [
    {"ledger_id": "A1", "claim": "Focus and Sleep rise together in the same week.", "decision": "accepted", "at": "2026-07-02T00:30:11+00:00"},
    {"ledger_id": "B1", "claim": 'Adam builds external rules like "if I can\'t say I can\'t play" to hold himself to plans', "decision": "accepted", "at": "2026-07-10T00:00:00+00:00"},
    {"ledger_id": "C1", "claim": "A claim Adam rejected", "decision": "accepted", "at": "2026-07-09T00:00:00+00:00"},
    {"ledger_id": "C2", "claim": "A claim Adam rejected", "decision": "rejected", "at": "2026-07-11T00:00:00+00:00"},
]


def graph(tmp_path: Path):
    ttl = tmp_path / "g.ttl"
    ttl.write_text(TTL, encoding="utf-8")
    ledger = tmp_path / "l.json"
    ledger.write_text(json.dumps(LEDGER), encoding="utf-8")
    return load_graph(ttl, ledger)


def test_records_are_split_by_uri_and_carry_their_fields(tmp_path):
    g = graph(tmp_path)
    assert len(g.records) == 3
    a = g.find("conn-obs-a")
    assert a.uri.endswith("/conn-obs-a") and a.leaf == "conn-obs-a"
    assert a.label == "Focus and Sleep rise together in the same week"
    assert a.connection_type == "observed_correlation" and a.strength == "0.42"
    assert a.accepted_at.startswith("2026-07-02")
    assert g.find("https://understood.app/ontology/connection/conn-obs-a") is a
    assert g.find("conn-obs-missing") is None


def test_join_rule_matches_the_promotion_code():
    assert normalize_claim("  Focus and Sleep rise together in the same week. ") == "focus and sleep rise together in the same week"


def test_latest_decision_wins_so_a_rejected_claim_is_not_accepted(tmp_path):
    g = graph(tmp_path)
    assert g.is_accepted(g.find("conn-obs-a"))
    assert g.is_accepted(g.find("conn-obs-b"))
    assert not g.is_accepted(g.find("conn-obs-c"))


def test_quotes_are_character_for_character_but_escaped_quotes_read_both_ways(tmp_path):
    g = graph(tmp_path)
    a = g.find("conn-obs-a")
    assert g.quote_is_in(a, "Focus and Sleep rise together")
    assert not g.quote_is_in(a, "Focus and sleep rise together")
    assert not g.quote_is_in(a, "   ")
    b = g.find("conn-obs-b")
    assert g.quote_is_in(b, 'external rules like "if I can\'t say I can\'t play"')
    assert g.quote_is_in(b, 'external rules like \\"if I can\'t say I can\'t play\\"')


def test_parse_ignores_text_outside_connection_records():
    records = parse_graph("@prefix x: <y> .\n<https://understood.app/ontology/other/thing> a x:Thing ;\n  .\n")
    assert records == {}
