import json

import pytest

from nucleus.dictionary import Meaning
from nucleus.gate import FIRST_LINE, check, compose
from nucleus.graph import Graph, parse_graph

TTL = '''<https://understood.app/ontology/connection/conn-obs-a> a understood:Connection ;
  understood:label "Momentum is Adam's compass: what gives a feeling of momentum is worthwhile" ;
  understood:connectionType "stated_relationship" ;
  understood:strength "0.90"^^xsd:decimal ;
  understood:acceptedAt "2026-07-10T22:57:35Z"^^xsd:dateTime ;
  .

<https://understood.app/ontology/connection/conn-obs-r> a understood:Connection ;
  understood:label "A rejected claim" ;
  understood:connectionType "observed_pattern" ;
  understood:strength "0.50"^^xsd:decimal ;
  understood:acceptedAt "2026-07-10T00:00:00Z"^^xsd:dateTime ;
  .
'''
LEDGER = [
    {"claim": "Momentum is Adam's compass: what gives a feeling of momentum is worthwhile", "decision": "accepted", "at": "2026-07-10T22:57:35+00:00"},
    {"claim": "A rejected claim", "decision": "rejected", "at": "2026-07-11T00:00:00+00:00"},
]
MEANINGS = [
    Meaning(word="PULLED", identifier="16, 21, 12, 12, 5, 4", index=1, text="It is important to feel pulled…interested without an obsessive desire to feel interested."),
    Meaning(word="KILL SWITCH", identifier="11, 9, 12, 12, 37, 19, 23, 9, 20, 3, 8", index=1, text="that's my Killswitch not feeling momentum"),
    Meaning(word="KILL SWITCH", identifier="11, 9, 12, 12, 37, 19, 23, 9, 20, 3, 8", index=1, text="The lack of momentum.  It means to stop what I am doing. Pause, and think BIGGER!"),
]
A = "conn-obs-a"
QUOTE = "Momentum is Adam's compass"


@pytest.fixture
def graph():
    return Graph(records=parse_graph(TTL), ledger=LEDGER, raw_graph=TTL, raw_ledger=json.dumps(LEDGER))


def aligned(**overrides):
    reply = {"answer": "aligned",
             "words": [{"word": "PULLED", "why": "Your word draws the line between pull and obsession."}],
             "records": [{"id": A, "quote": QUOTE, "why": "Rising is the feeling your compass points at."}]}
    reply.update(overrides)
    return reply


def test_aligned_passes_and_code_composes_the_text(graph):
    verdict = check(aligned(), graph, MEANINGS)
    assert verdict.ok, verdict.reason
    assert verdict.answer == "aligned"
    lines = verdict.text.split("\n")
    assert lines[0] == "aligned and why"
    assert "PULLED — “It is important to feel pulled…interested without an obsessive desire to feel interested.”" in lines
    assert "0.90 · 2026-07-10 — “Momentum is Adam's compass”" in lines
    assert verdict.text.endswith("Rising is the feeling your compass points at.")
    assert "possibility" not in verdict.text


def test_dont_know_is_exactly_adams_sentence(graph):
    verdict = check({"answer": "dont_know", "words": [], "records": []}, graph, MEANINGS)
    assert verdict.ok
    assert verdict.text == "I don't know. There is nothing in your records that points to a conclusion."


def test_not_sure_carries_the_possibility_box(graph):
    reply = aligned(answer="not_sure", possibility=[{
        "links": [A, "KILL SWITCH"],
        "proposed": "Your compass and your kill switch may be the same feeling read from two ends.",
        "would_show": "A week where momentum was logged next to a kill-switch moment.",
    }])
    verdict = check(reply, graph, MEANINGS)
    assert verdict.ok, verdict.reason
    lines = verdict.text.split("\n")
    assert lines[0] == FIRST_LINE["not_sure"]
    assert "possibility" in lines
    assert "Momentum is Adam's compass: what gives a feeling of momentum is worthwhile ↔ KILL SWITCH" in lines
    assert lines[-1].startswith("would show: ")


@pytest.mark.parametrize("reply, reason", [
    ({"answer": "advice", "words": [], "records": []}, "not one of Adam's three answers"),
    ({"answer": "aligned", "words": [], "records": []}, "must match at least one"),
    ({"answer": "dont_know", "records": [{"id": A, "quote": QUOTE, "why": "Why."}]}, "cannot cite"),
    (aligned(records=[{"id": "conn-obs-missing", "quote": "x", "why": "Why."}]), "does not exist"),
    (aligned(records=[{"id": A, "quote": "Momentum is Adam's map", "why": "Why."}]), "character for character"),
    (aligned(records=[{"id": "conn-obs-r", "quote": "A rejected claim", "why": "Why."}]), "no accepted decision"),
    (aligned(records=[{"id": A, "quote": QUOTE, "why": "First sentence. Second sentence with advice."}]), "more than one sentence"),
    (aligned(records=[{"id": A, "quote": QUOTE, "why": "Line one\nLine two"}]), "line break"),
    (aligned(words=[{"word": "HUSTLE", "why": "Why."}]), "not in Adam's dictionary"),
    (aligned(possibility=[{"links": [A, "PULLED"], "proposed": "P.", "would_show": "W."}]), "only allowed under not_sure"),
    (aligned(answer="not_sure", possibility=[{"links": [A], "proposed": "P.", "would_show": "W."}]), "exactly two things"),
    (aligned(answer="not_sure", possibility=[{"links": [A, "conn-obs-missing"], "proposed": "P.", "would_show": "W."}]), "neither a record nor"),
    (aligned(summary="A summary paragraph."), "not in the contract"),
    ("this is not json", "not JSON"),
])
def test_anything_outside_the_three_answers_is_refused(graph, reply, reason):
    verdict = check(reply, graph, MEANINGS)
    assert not verdict.ok
    assert reason in verdict.reason, verdict.reason


def test_compose_never_adds_words_of_its_own():
    text = compose("aligned", [], [{"id": "u", "leaf": "l", "quote": "Q", "why": "W.", "strength": "", "accepted_at": "", "connection_type": ""}], [])
    assert text == "aligned and why\n\n“Q”\nW."
