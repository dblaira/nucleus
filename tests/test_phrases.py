from nucleus.dictionary import Meaning
from nucleus.graph import Graph, parse_graph
from nucleus.phrases import PhraseIndex, phrases, stem, tokens

TTL = '''<https://understood.app/ontology/connection/conn-obs-a> a understood:Connection ;
  understood:label "'Borrowed motivation' is a warning sign Adam acts on: when the drive behind a project isn't his own, he pauses or kills it" ;
  understood:strength "0.75"^^xsd:decimal ;
  understood:acceptedAt "2026-07-02T00:00:00Z"^^xsd:dateTime ;
  .
'''
LEDGER = [{"claim": "'Borrowed motivation' is a warning sign Adam acts on: when the drive behind a project isn't his own, he pauses or kills it", "decision": "accepted", "at": "2026-07-02T00:00:00+00:00"}]
MEANINGS = [
    Meaning("KILL SWITCH", "11", 1, "that's my Killswitch not feeling momentum"),
    Meaning("EYE FOR EXCELLENCE", "5", 1, "What pulls instead of pushes"),
    Meaning("FLOW", "6", 1, "If a process becomes a worry or burden kill it, and think BIGGER!"),
]


def index():
    return PhraseIndex(MEANINGS, Graph(parse_graph(TTL), LEDGER, TTL, "[]"))


def test_word_endings_fold_so_his_phrase_matches_a_different_ending():
    assert stem("pushed") == stem("pushes") == stem("push")
    assert tokens("pulled instead of pushed") == ["pull", "instead", "of", "push"]


def test_phrases_need_two_content_words_and_no_stop_word_at_the_edges():
    assert "kill it and think bigger" in phrases(tokens("kill it and think bigger"))
    assert "and think" not in phrases(tokens("kill it and think bigger"))


def test_his_phrases_are_found_in_a_question_instantly_with_no_model():
    hits = index().lookup("I am not feeling momentum, is this borrowed motivation or being pulled instead of pushed?")
    names = [h.name for h in hits]
    assert "KILL SWITCH" in names
    assert "EYE FOR EXCELLENCE" in names
    assert "conn-obs-a" in names
    kill = next(h for h in hits if h.name == "KILL SWITCH")
    assert kill.phrase == "feel momentum"


def test_everyday_words_find_nothing():
    assert index().lookup("How long before my flight should I arrive at the airport?") == []


def test_longest_phrase_comes_first_and_each_source_once():
    hits = index().lookup("kill it and think bigger, then kill it and think bigger again")
    assert [h.name for h in hits] == ["FLOW"]
    assert hits[0].phrase == "kill it and think bigger"
