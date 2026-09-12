import json
from pathlib import Path

from nucleus import NUCLEUS_FILES, dictionary, links
from nucleus.graph import load_graph
from nucleus.model import ModelReply
from nucleus.phrases import PhraseIndex
from nucleus.store import Store

FLOW_ID = "conn-obs-fable5-2026-07-10-affect-work-momentum-compass"
FLOW_QUOTE = "Momentum is Adam's compass"


def reading(word=None):
    said = [{"word": word, "identifier": "", "triggeredBy": word, "adamsWords": []}] if word else []
    return {"said": "q", "numbers": "", "outcome": "yes" if word else "no", "heSaidTheWordItself": said,
            "hisRoutesSentItHere": [], "anotherRouteWasPossible": [], "noMeaningAddedYet": [], "mustAskFirst": None, "stopped": None}


def test_background_pass_keeps_only_links_the_graph_confirms(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    reply = {"word": "FLOW", "records": [
        {"id": FLOW_ID, "quote": FLOW_QUOTE, "why": "Momentum is the felt side of FLOW."},
        {"id": "made-up-record", "quote": "x", "why": "y."},
        {"id": FLOW_ID + "", "quote": "not in the record", "why": "y."},
    ]}
    added = links.find_links("FLOW", store, graph, meanings, model_call=lambda p: ModelReply("fake", "fake", json.dumps(reply)))
    assert added == 1
    assert [l["record"] for l in store.links_for("FLOW")] == [FLOW_ID]
    assert store.searched_words() == {"FLOW"}


def test_picture_is_painted_from_links_without_a_model(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    assert links.paint("What is FLOW?", reading("FLOW"), [], store, graph, meanings) is None
    store.add_link("FLOW", FLOW_ID, FLOW_QUOTE, "Momentum is the felt side of FLOW.", "links:FLOW", "fake", "fake")
    picture = links.paint("What is FLOW?", reading("FLOW"), [], store, graph, meanings)
    assert picture is not None and picture.answer == "not_sure" and picture.missing == []
    assert picture.text.startswith("Not sure.") and FLOW_QUOTE in picture.text and "Momentum is the felt side of FLOW." in picture.text
    store.thumb("FLOW", FLOW_ID, up=False)
    assert links.paint("What is FLOW?", reading("FLOW"), [], store, graph, meanings) is None


def test_a_why_from_an_old_answer_is_not_shown_under_a_painted_picture(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    store.add_link("FLOW", FLOW_ID, FLOW_QUOTE, "This answers your question about diet.", "some-question-id", "fake", "fake")
    picture = links.paint("What is FLOW?", reading("FLOW"), [], store, graph, meanings)
    assert picture is not None and "diet" not in picture.text and FLOW_QUOTE in picture.text


def test_a_change_to_his_records_sends_words_back_through_the_pass(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    store.mark_word_searched("FLOW", "hash-of-yesterdays-records")
    assert store.searched_words() == {"FLOW"}
    assert store.searched_words("hash-of-yesterdays-records") == {"FLOW"}
    assert store.searched_words("hash-of-todays-records") == set()


def test_the_middle_words_come_from_his_note():
    from nucleus.kinds import load_kinds, is_kind
    kinds = load_kinds()
    assert len(kinds) >= 30
    for word in ("requires", "correlates with", "causes", "happens before", "should not", "is part of"):
        assert word in kinds
    assert "MEANING" not in kinds and "RELATIONSHIP" not in kinds
    assert is_kind("requires", kinds) and not is_kind("is caused by the vibes", kinds)


def test_a_middle_word_off_his_list_is_refused_and_a_good_one_is_painted(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    reply = {"word": "FLOW", "records": [
        {"id": FLOW_ID, "quote": FLOW_QUOTE, "kind": "requires", "why": "Momentum is the felt side of FLOW."},
    ]}
    links.find_links("FLOW", store, graph, meanings, model_call=lambda p: ModelReply("fake", "fake", json.dumps(reply)))
    assert store.links_for("FLOW")[0]["kind"] == "requires"
    picture = links.paint("What is FLOW?", reading("FLOW"), [], store, graph, meanings)
    assert f"FLOW requires “{FLOW_QUOTE}”" in picture.text

    store2 = Store(tmp_path / "n2.sqlite3")
    bad = {"word": "FLOW", "records": [{"id": FLOW_ID, "quote": FLOW_QUOTE, "kind": "vibes with", "why": "x."}]}
    links.find_links("FLOW", store2, graph, meanings, model_call=lambda p: ModelReply("fake", "fake", json.dumps(bad)))
    assert store2.links_for("FLOW")[0]["kind"] is None


def test_kinds_pass_fills_the_middle_word_on_old_links(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    meanings = dictionary.load_meanings(NUCLEUS_FILES["meanings"])
    store.add_link("FLOW", FLOW_ID, FLOW_QUOTE, "old why.", "some-question", "fake", "fake")
    assert store.words_with_unkinded_links() == ["FLOW"]
    reply = {"word": "FLOW", "kinds": [{"id": FLOW_ID, "kind": "depends on"}, {"id": "not-linked", "kind": "causes"}]}
    done = links.find_kinds("FLOW", store, graph, meanings, model_call=lambda p: ModelReply("fake", "fake", json.dumps(reply)))
    assert done == 1 and store.links_for("FLOW")[0]["kind"] == "depends on"
    assert store.words_with_unkinded_links() == []
