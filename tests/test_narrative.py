from pathlib import Path

import pytest

from nucleus import NUCLEUS_FILES, ask as ask_module, dictionary, english, narrative
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
    told = narrator.tell("The more I work on Cowboyai the more my ambition seem to grow.", reading(said=["WORK"]), store.links_for)
    # his dictionary meaning of WORK ("Work happens when you have a job.") is not told for a word used in passing
    assert not any(part.source == "meaning" for part in told.parts) and "Work happens when you have a job" not in told.text
    # his knowledge graph still answers: the statement names two life domains, and his tracked weeks measured them
    assert "Ambition and Work rise together in the same week: 53% of 92 tracked weeks" in told.text


def test_an_ending_is_folded_for_his_word_names(narrator, store):
    told = narrator.tell("Why do I tend to push sometimes when I know it isn’t what I need?", reading(), store.links_for)
    assert [reach.word for reach in told.reaches] == ["PUSHED"]
    assert told.text.startswith("Pushed is signal to flip the kill switch.")


def test_nothing_of_his_holds_it_so_it_says_plainly_what_is_missing(narrator, store):
    told = narrator.tell("What is the capital of France?", reading(unknown=["CAPITAL", "FRANCE"]), store.links_for)
    assert told.judged == "dont_know" and told.no_meaning_yet == ["CAPITAL", "FRANCE"]
    assert told.text == "Nothing in your dictionary or your records says capital, France."


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


def test_nothing_reached_is_his_third_answer_at_once_and_no_model_is_asked(monkeypatch, store):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.delenv("NUCLEUS_NO_MODEL", raising=False)

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask("What is the capital of France?", store=store, model_call=never,
                            brief=lambda q: reading(unknown=["CAPITAL", "FRANCE"]), explain_call=never)
    assert result.answer == "dont_know" and result.text.startswith("I don't know.")
    assert store.explanation(result.question_id)["text"] == "Nothing in your dictionary or your records says capital, France."
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
    assert result.answer == "not_sure" and result.text.startswith("There is some relationship, but not enough to justify causation.")
    saved = store.explanation(result.question_id)
    assert saved["provider"] == "code" and "Exercise and Sleep rise together in the same week: 57% of 92 tracked weeks" in saved["text"]


def test_a_record_that_is_his_own_words_is_checked_against_his_quote(narrator, store):
    told = narrator.tell("Why do I sleep badly after a late meeting?", reading(unknown=["BADLY", "LATE", "MEETING"]), store.links_for)
    records = [part for part in told.parts if part.source == "record"]
    assert records and all(same_words(part.exact, part.text) for part in records)
    assert any(part.exact.startswith("Better sleep, and concentration is the outcome I'm going for") for part in records)
    assert store.connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0] == 0


DOCTOR = "What are reasons I would avoid going to the doctor?"


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_a_word_his_dictionary_does_not_hold_is_carried_by_english_to_his_ontology_and_judged_by_his_graph(narrator, store):
    # Adam, 2026-10-02: "It did not use the ontology and knowledge graph. ... make sure my entry is judged
    # according the knowledge graph and dictionary."
    told = narrator.tell(DOCTOR, reading(unknown=["REASONS", "AVOID", "DOCTOR"]), store.links_for)
    assert [(n.domain, n.said) for n in narrator.domains_named(DOCTOR)] == [("belief", "reasons"), ("health", "doctor")]
    assert "You said doctor. In English that is “a licensed medical practitioner”. Your ontology files that under Health: " \
           "Medical, wellness, body maintenance, and preventive care. Nothing in your dictionary or your records says doctor." in told.text
    assert "You said reasons. In English that is “a rational motive for a belief or action”. Your ontology files that under Belief: " \
           "Core beliefs, values, worldview, and personal philosophy." in told.text
    assert "This accepted record of yours sits in both Belief and Health: Changes only stick for you when they feel innocent " \
           "and easy — any change that feels effortful will not be adopted." in told.text
    assert told.judged == "not_sure" and told.ms < 200
    record = [part for part in told.parts if part.source == "record"]
    assert len(record) == 1 and same_words(record[0].exact, record[0].text)


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_the_doctor_entry_is_his_middle_answer_with_the_record_as_a_row_and_no_model(monkeypatch, store):
    monkeypatch.setenv("NUCLEUS_NARRATIVE", "1")
    monkeypatch.delenv("NUCLEUS_NO_MODEL", raising=False)

    def never(prompt):
        raise AssertionError("the model was asked")

    result = ask_module.ask(DOCTOR, store=store, model_call=never, brief=lambda q: reading(unknown=["REASONS", "AVOID", "DOCTOR"]),
                            explain_call=never)
    assert result.answer == "not_sure" and result.text.startswith("There is some relationship, but not enough to justify causation.\n")
    assert [row["leaf"] for row in result.records] == ["conn-obs-mined-2026-07-10-easy-innocent-changes-stick"]
    saved = store.explanation(result.question_id)
    assert saved["provider"] == "code" and "“a licensed medical practitioner”" in saved["text"]
    assert store.connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0] == 0


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_what_english_does_not_carry(narrator):
    named = lambda entry: [(n.domain, n.said) for n in narrator.domains_named(entry)]
    assert named("Fuck! Things feel slow.") == [("affect", "feel")]                    # said for force: never Sleep
    assert named("What did I decide about Notion last Tuesday?") == []                 # a name, not "a vague idea"
    assert named("What is the capital of France?") == []
    assert named("I keep getting stuck on the content.") == []                         # "getting" is "get"; content is not a feeling
    assert named("I am in control of my focus.") == []                                 # "exercise control" is not Exercise
    assert named("Why am I so mad?") == [("affect", "mad")]                            # the dictionary shelves it with feelings


@pytest.mark.skipif(not english.installed(), reason="the English dictionary is not installed")
def test_a_domain_his_graph_holds_records_in_but_none_about_his_word_says_so(narrator, store):
    told = narrator.tell("Why am I so tired after I eat?", reading(unknown=["TIRED", "EAT"]), store.links_for)
    assert "You said eat. In English that is “take in solid food”. Your ontology files that under Nutrition: " \
           "Diet, food, supplements, and nutritional science. Nothing in your dictionary or your records says eat." in told.text
    assert "accepted Nutrition records. The strongest stated: " in told.text and told.judged == "not_sure"
    for part in told.parts:
        if part.source == "record":
            assert same_words(part.exact, part.text), part.text


def test_without_the_english_dictionary_nothing_else_changes(narrator, store, monkeypatch):
    monkeypatch.setattr(english, "_wordnet", None)
    english.sense.cache_clear()
    english.bases.cache_clear()
    try:
        assert narrator.domains_named(DOCTOR) == []
        told = narrator.tell(SLOW, reading(unknown=["MAD", "SLOW"]), store.links_for)
        assert "KILL SWITCH: The lack of momentum." in told.text and "Affect and Work rise together in the same week" in told.text
    finally:
        english.sense.cache_clear()
        english.bases.cache_clear()


def test_the_middle_answer_begins_with_his_words_of_october_2():
    # Adam, 2026-10-02: "I will need to define the logic for the middle response.  We will begin with this response.
    # "There is some relationship, but not enough to justify causation.""
    from nucleus import gate
    assert gate.FIRST_LINE["not_sure"] == "There is some relationship, but not enough to justify causation."
    assert gate.compose("not_sure", [], [], []).split("\n")[0] == "There is some relationship, but not enough to justify causation."


def test_the_middle_answer_asks_with_his_own_question_of_october_7():
    # Adam wrote the middle answer himself on 2026-10-07; his last question replaces the September 9 sentence
    from nucleus import gate
    assert gate.MIDDLE_ASKS == "What would you like AI to revisit? Anything come to mind?"
    assert gate.compose("not_sure", [], [], []) == gate.FIRST_LINE["not_sure"] + "\n\n" + gate.MIDDLE_ASKS
    assert gate.MIDDLE_ASKS not in gate.compose("aligned", [], [], [])
    assert gate.compose("dont_know", [], [], []) == gate.FIRST_LINE["dont_know"]
