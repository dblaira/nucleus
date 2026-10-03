from pathlib import Path

import pytest

from nucleus import NUCLEUS_FILES, ask as ask_module, dictionary, narrative
from nucleus.graph import load_graph
from nucleus.person import same_words
from nucleus.store import Store

COMPASS = "conn-obs-fable5-2026-07-10-affect-work-momentum-compass"
SLOW = "Sometimes I get mad at how slow things feel.  Like now.  Fuck! Things feel slow."


def reading(said=(), routed=(), unknown=()):
    def entry(word, by):
        return {"word": word, "identifier": "", "triggeredBy": by, "adamsWords": []}
    return {"said": "q", "numbers": "", "outcome": "yes" if said or routed else "no",
            "heSaidTheWordItself": [entry(w, w) for w in said], "hisRoutesSentItHere": [entry(w, by) for w, by in routed],
            "anotherRouteWasPossible": [], "noMeaningAddedYet": list(unknown), "mustAskFirst": None, "stopped": None}


@pytest.fixture(scope="module")
def narrator():
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    return narrative.Narrator(dictionary.load_meanings(NUCLEUS_FILES["meanings"]), graph)


@pytest.fixture
def store(tmp_path: Path):
    store = Store(tmp_path / "n.sqlite3")
    store.add_link("MOMENTUM", COMPASS, "Momentum is Adam's compass", "why.", "links:MOMENTUM", "fake", "fake", kind="serves the purpose of")
    return store


def test_no_model_is_reachable_from_the_narrative():
    source = Path(narrative.__file__).read_text(encoding="utf-8")
    assert "from . import model" not in source and "model_module" not in source and "import explain" not in source


def test_the_statement_he_was_satisfied_with_gets_more_with_no_model(narrator, store):
    told = narrator.tell(SLOW, reading(unknown=["MAD", "SLOW"]), store.links_for)
    sources = [part.source for part in told.parts]
    # what he had: his dictionary, MOMENTUM
    assert told.parts[0].source == "meaning" and told.parts[0].word == "MOMENTUM"
    assert "The lack of momentum would be trying to make a decision but finding that you can’t." in told.text
    # the walk through his own sentence to KILL SWITCH
    assert "walk" in sources and "KILL SWITCH: The lack of momentum." in told.text and "Pause, and think BIGGER!" in told.text
    # his knowledge graph and his ontology: the record, its two life domains, his tracked weeks
    assert "Momentum is your compass" in told.text
    assert "Your records place this in Affect and Work." in told.text
    assert "Affect and Work rise together in the same week: 53% of 92 tracked weeks" in told.text
    assert told.no_meaning_yet == ["MAD", "SLOW"]


def test_every_sentence_told_is_his_with_only_the_person_changed(narrator, store):
    told = narrator.tell(SLOW, reading(), store.links_for)
    checked = 0
    for part in told.parts:
        if part.source in ("meaning", "walk", "record"):
            assert same_words(part.exact, part.text), part.text
            checked += 1
    assert checked >= 3


def test_his_route_is_told_with_his_own_rule(narrator, store):
    told = narrator.tell("This project has become a burden and I am losing FLOW. What should I do?",
                         reading(said=["FLOW"], routed=[("KILL SWITCH", "burden")]), store.links_for)
    assert "When you say burden, you are talking about KILL SWITCH:" in told.text
    assert "It means to stop what you are doing." in told.text
    assert "FLOW: If a process becomes a worry or burden kill it, and think BIGGER!" in told.text


def test_what_is_starts_at_his_defining_sentence(narrator, store):
    told = narrator.tell("What does Adam mean by momentum?", reading(said=["MOMENTUM"]), store.links_for)
    assert told.text.startswith("Momentum is the feeling of being pulled along")


def test_a_shared_phrase_of_three_words_names_where_it_lives(narrator, store):
    question = ("I just built 50 social media post ideas so I could use my pattern recognition skills to understand where my "
                "interest lies for making content.  It succeeded but now I am lingering before taking more action and I don’t know why.")
    told = narrator.tell(question, reading(said=["ACTION"]), store.links_for)
    assert "“pattern recognition skills” is in your CLOSE THE GAP: Processing an action after it has been taken." in told.text
    assert "In the Adam Pattern it is step 3 of 8, after CIRCLE and before CHOOSE SUCCESS." in told.text


def test_an_everyday_word_typed_small_in_passing_is_not_told(narrator, store):
    told = narrator.tell("The more I work on Cowboyai the more I see it.", reading(said=["WORK"]), store.links_for)
    assert told.text == "" and not any(part.source == "meaning" for part in told.parts)


def test_an_ending_is_folded_for_his_word_names(narrator, store):
    told = narrator.tell("Why do I tend to push sometimes when I know it isn’t what I need?", reading(), store.links_for)
    assert [reach.word for reach in told.reaches] == ["PUSHED"]
    assert told.text.startswith("Pushed is signal to flip the kill switch.")


def test_nothing_reached_says_nothing(narrator, store):
    told = narrator.tell("What is the capital of France?", reading(unknown=["CAPITAL", "FRANCE"]), store.links_for)
    assert told.text == "" and told.no_meaning_yet == ["CAPITAL", "FRANCE"]


def test_it_takes_milliseconds(narrator, store):
    told = narrator.tell(SLOW, reading(), store.links_for)
    assert told.ms < 100


def test_the_switches_are_off_unless_he_turns_them_on(monkeypatch):
    monkeypatch.delenv("NUCLEUS_NARRATIVE", raising=False)
    monkeypatch.delenv("NUCLEUS_NO_MODEL", raising=False)
    assert not ask_module.narrative_on() and not ask_module.no_model()


def test_with_the_switch_on_the_paragraph_is_code_and_no_model_is_called(monkeypatch, store):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    for record in ("conn-obs-claude-2026-07-02-affect-work-stated-relationship", "conn-obs-mined-2026-07-10-easy-innocent-changes-stick"):
        store.add_link("MOMENTUM", record, "", "why.", "links:MOMENTUM", "fake", "fake", kind="correlates with")

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask(SLOW, store=store, model_call=never, brief=lambda q: reading(unknown=["MAD", "SLOW"]), explain_call=never)
    assert result.status == "answered" and result.provider == "links"
    saved = store.explanation(result.question_id)
    assert saved["status"] == "shown" and saved["provider"] == "code" and saved["model"] == "narrative"
    assert "KILL SWITCH: The lack of momentum." in saved["text"]
    assert store.connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0] == 0


def test_with_no_model_on_nothing_reached_is_his_third_answer_at_once(monkeypatch, store):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.setenv("NUCLEUS_NO_MODEL", "1")

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask("What is the capital of France?", store=store, model_call=never,
                            brief=lambda q: reading(unknown=["CAPITAL", "FRANCE"]), explain_call=never)
    assert result.answer == "dont_know" and result.text.startswith("I don't know.")
    assert store.explanation(result.question_id)["text"] == "No meaning added yet: CAPITAL, FRANCE."
    assert store.connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0] == 0


def test_no_dictionary_word_but_a_life_domain_is_named_so_his_graph_answers(narrator, store):
    told = narrator.tell("I cannot get happy.  I am preoccupied with getting out of a feeling I can’t describe any other way than anxious.",
                         reading(unknown=["HAPPY", "ANXIOUS"]), store.links_for)
    assert not any(part.source == "meaning" for part in told.parts)
    assert told.text.startswith("You said feeling. Your ontology files that under Affect: Emotions, mood, emotional regulation, and psychological state.")
    assert "Your mood drops hardest when tooling or setup blocks building, and lifts when something ships." in told.text
    assert "Affect and Learning rise together in the same week: 67% of 92 tracked weeks" in told.text


def test_social_media_names_no_life_domain(narrator, store):
    told = narrator.tell("Peptides are important to me and yet so is social media.", reading(), store.links_for)
    assert told.text == ""


def test_the_domain_road_paints_his_middle_line_with_the_records_as_rows(monkeypatch, store):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.setenv("NUCLEUS_NO_MODEL", "1")

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask("Why do I sleep badly after a late meeting?", store=store, model_call=never,
                            brief=lambda q: reading(unknown=["SLEEP", "BADLY", "LATE", "MEETING"]), explain_call=never)
    assert result.answer == "not_sure" and result.text.startswith("Not sure.")
    saved = store.explanation(result.question_id)
    assert saved["provider"] == "code" and "Exercise and Sleep rise together in the same week: 57% of 92 tracked weeks" in saved["text"]
    assert store.connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0] == 0
