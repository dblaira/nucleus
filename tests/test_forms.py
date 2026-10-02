from copy import deepcopy
from dataclasses import replace
import random
import re
import sqlite3

import pytest

from nucleus import forms
from nucleus.store import Store


KINDS = ["depends on", "supports", "requires", "rejects", "should not"]
SCREEN = forms.Screen("aligned", ("FLOW", "LIFT"), (
    forms.Row("FLOW", "r1", "depends on"),
    forms.Row("FLOW", "r2", "depends on"),
    forms.Row("FLOW", "r3", "depends on"),
    forms.Row("LIFT", "r4", "supports"),
))


def form(**changes):
    result = {
        "number": "F-7", "when": {"answer": "aligned", "kinds_present": ["depends on"]},
        "sentence": "Your rows say {word} depends on {count} things you have written down.",
        "status": "approved", "author": "test fixture; not an approved product form", "date": "2026-10-01",
    }
    result.update(changes)
    return result


def fill(value=None, screen=SCREEN):
    return forms.fill(form() if value is None else value, screen, kinds=KINDS)


def test_legal_form_fills_exactly_and_keeps_number_and_origins():
    result = fill()
    assert result.number == "F-7"
    assert result.text == "Your rows say FLOW depends on 3 things you have written down."
    assert "".join(p.text for p in result.parts) == result.text
    assert [(p.text, p.source) for p in result.parts if p.source != "form.sentence"] == [
        ("FLOW", "screen.words[0]"), ("3", "count(screen.rows.kind == 'depends on')"),
    ]


@pytest.mark.parametrize("sentence", [
    "{quote}", "{word.upper}", "{word[0]}", "{word!r}", "{word:>20}",
    "{{word}}", "{", "}", "{}", "{word}{", "{word:{other_word}}",
])
def test_unknown_blanks_and_python_formatting_are_refused(sentence):
    with pytest.raises(forms.Refused, match="blank"):
        fill(form(sentence=sentence))


@pytest.mark.parametrize("sentence", [
    "You should follow {word}.", "Try to follow {word}.", "Consider {word}.",
    "The next step is {word}.", "You could follow {word}.", "Make sure {word}.",
])
def test_existing_advice_pattern_is_reused(sentence):
    assert forms.check(form(sentence=sentence), kinds=KINDS) == "advice"


def test_existing_explanation_check_runs_on_filled_text(monkeypatch):
    calls = []
    original = forms.explain.check

    def capture(text, words):
        calls.append((text, words))
        return original(text, words)

    monkeypatch.setattr(forms.explain, "check", capture)
    assert fill().text
    assert calls[-1] == ("Your rows say FLOW depends on 3 things you have written down.", ["FLOW", "LIFT"])


@pytest.mark.parametrize("status", ["proposed", "rejected"])
def test_a_nonapproved_form_cannot_produce_text(status):
    assert fill(form(status=status)) is None


@pytest.mark.parametrize("when", [
    {"weather": "sunny"}, {}, {"answer": "maybe"}, {"answer": []},
    {"kinds_present": ["vibes with"]}, {"kinds_absent": ["vibes with"]},
    {"kinds_present": ["supports", "supports"]}, {"kinds_present": "supports"},
    {"kinds_present": []}, {"kinds_present": ["supports"], "kinds_absent": ["supports"]},
    {"record_count": -1}, {"record_count": True}, {"record_count": {"min": 5, "max": 2}},
    {"word_count": {"more_than": 3}}, {"word_count": {}}, {"word_count": 1.5},
    {"missing_links": 1},
])
def test_unknown_or_malformed_conditions_are_refused(when):
    with pytest.raises(forms.Refused):
        fill(form(when=when))


@pytest.mark.parametrize("change", [
    {"number": "FLOW"}, {"number": "F-07"}, {"date": "2026-02-30"}, {"date": "20261001"},
    {"status": "yes"}, {"author": ""}, {"sentence": ""}, {"sentence": None}, {"extra": "field"},
])
def test_malformed_form_metadata_is_refused(change):
    with pytest.raises(forms.Refused):
        fill(form(**change))


def test_all_six_conditions_must_hold():
    when = {"answer": "aligned", "kinds_present": ["depends on"], "kinds_absent": ["requires"],
            "record_count": {"min": 4, "max": 4}, "word_count": 2, "missing_links": False}
    assert fill(form(when=when))
    for name, bad in (("answer", "not_sure"), ("kinds_present", ["rejects"]),
                      ("kinds_absent", ["supports"]), ("record_count", {"max": 3}),
                      ("word_count", {"min": 3}), ("missing_links", True)):
        assert fill(form(when={**when, name: bad})) is None
    assert fill(form(when={**when, "missing_links": True}), replace(SCREEN, missing_links=True))


def test_all_six_blanks_use_only_screen_text_or_screen_counts():
    value = form(sentence="{word} / {other_word}: {kind}; {count}; {word_count}; {strongest_kind}.")
    assert fill(value).text == "FLOW / LIFT: depends on; 3; 2; depends on."
    # Strongest-kind ties preserve screen order, not alphabetical order or an invented label.
    screen = replace(SCREEN, rows=(forms.Row("FLOW", "r1", "supports"), forms.Row("FLOW", "r2", "depends on")))
    assert fill(value, screen).text.endswith("supports.")


def test_word_binds_to_the_firing_rows_not_the_first_word():
    screen = replace(SCREEN, words=("LIFT", "FLOW"))
    assert fill(screen=screen).text == "Your rows say FLOW depends on 3 things you have written down."


def test_missing_blank_values_and_ambiguous_per_word_counts_do_not_fill():
    assert fill(form(sentence="{word} and {other_word}."), replace(SCREEN, words=("FLOW",), rows=SCREEN.rows[:3])) is None
    mixed = replace(SCREEN, rows=SCREEN.rows[:2] + (forms.Row("LIFT", "r4", "depends on"),))
    assert fill(screen=mixed) is None
    assert fill(form(when={"answer": "aligned"}, sentence="{word}: {strongest_kind}."), replace(SCREEN, rows=())) is None
    assert fill(form(when={"answer": "aligned"}, sentence="{word}."), replace(SCREEN, words=(), rows=())) is None


@pytest.mark.parametrize("present", [[], ["depends on", "supports"]])
def test_kind_and_count_have_no_guessed_binding(present):
    when = {"answer": "aligned"}
    if present:
        when["kinds_present"] = present
    assert forms.check(form(when=when), kinds=KINDS) == "kind and count need exactly one middle word to fire on"


def test_more_than_four_sentences_refused_before_and_after_filling():
    assert fill(form(sentence="{word}. Two. Three! Four?"))
    with pytest.raises(forms.Refused, match="more than 4"):
        fill(form(sentence="{word}. Two. Three! Four? Five."))
    word = "One. Two. Three. Four. Five."
    with pytest.raises(forms.Refused, match="more than 4"):
        fill(form(when={"answer": "aligned"}, sentence="{word}"), forms.Screen("aligned", (word,), ()))


def test_advice_and_oversize_text_from_screen_are_also_refused():
    for word, reason in (("you should", "advice"), ("x" * 901, "longer")):
        with pytest.raises(forms.Refused, match=reason):
            fill(form(when={"answer": "aligned"}, sentence="{word}"), forms.Screen("aligned", (word,), ()))
    with pytest.raises(forms.Refused, match="advice"):
        fill(form(when={"kinds_present": ["should not"]}, sentence="{word} {kind}."),
             forms.Screen("aligned", ("FLOW",), (forms.Row("FLOW", "r1", "should not"),)))


@pytest.mark.parametrize("sentence", ["prefix{word}.", "{word}suffix.", "{word}{other_word}.", "{word}-suffix."])
def test_kill_switch_refuses_words_created_by_joining_pieces(sentence):
    with pytest.raises(forms.Refused, match="kill switch"):
        fill(form(sentence=sentence))


def test_filling_preserves_case_unicode_and_does_not_expand_screen_braces():
    word = "Élan {other_word}"
    screen = forms.Screen("aligned", (word,), ())
    result = fill(form(when={"answer": "aligned"}, sentence="Your rows say {word}."), screen)
    assert result.text == "Your rows say Élan {other_word}."
    assert result.parts[1].text == word


@pytest.mark.parametrize("screen", [
    replace(SCREEN, answer="invented"), replace(SCREEN, answer=[]),
    replace(SCREEN, words=("FLOW", "FLOW")), replace(SCREEN, missing_links="yes"),
    replace(SCREEN, rows=(forms.Row("SECRET", "r1", "supports"),)),
    replace(SCREEN, rows=(forms.Row("FLOW", "r1", "vibes with"),)),
    replace(SCREEN, rows=(SCREEN.rows[0], SCREEN.rows[0])),
])
def test_malformed_screen_is_refused(screen):
    with pytest.raises(forms.Refused):
        fill(screen=screen)


def test_no_model_or_hidden_record_lookups_during_fill(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("a form must not look up a model or hidden record")

    monkeypatch.setattr(forms.explain.model_module, "call", forbidden)
    monkeypatch.setattr(Store, "link", forbidden)
    monkeypatch.setattr(Store, "links_for", forbidden)
    assert fill()


def test_provenance_for_varied_screen_words_and_counts():
    rng = random.Random(7)
    # Independent token check includes the numeric counts explicitly allowed by the plan.
    tokens = re.compile(r"\w+(?:[’'\-]\w+)*")
    value = form(sentence="{word} / {other_word}: {kind}; {count}; {word_count}; {strongest_kind}.")
    literals = set(tokens.findall(re.sub(r"\{[^}]+\}", "", value["sentence"])))
    for _ in range(200):
        words = tuple(rng.sample(["FLOW", "LIFT", "ÉLAN", "A VISION", "don't", "山", "1:4", "a-b"], 2))
        count = rng.randint(1, 30)
        rows = tuple(forms.Row(words[0], f"r{i}", "depends on") for i in range(count))
        screen = forms.Screen("aligned", words, rows)
        result = fill(value, screen)
        allowed = literals | set(tokens.findall(" ".join(words) + " depends on")) | {str(count), "2"}
        assert set(tokens.findall(result.text)) <= allowed
        assert "".join(p.text for p in result.parts) == result.text


def test_loader_reads_blocks_without_approving_proposals(tmp_path):
    path = tmp_path / "forms.txt"
    block = '''[[forms]]
number = "F-7"
sentence = "Your rows say {word} depends on {count} things you have written down."
status = "proposed"
author = "test fixture"
date = "2026-10-01"
[forms.when]
answer = "aligned"
kinds_present = ["depends on"]
'''
    path.write_text(block)
    loaded = forms.load(path, kinds=KINDS)
    assert len(loaded) == 1 and fill(loaded[0]) is None
    path.write_text(block + "\n" + block)
    with pytest.raises(forms.Refused, match="duplicate"):
        forms.load(path, kinds=KINDS)
    path.write_text("forms = []\nunknown = 1\n")
    with pytest.raises(forms.Refused):
        forms.load(path, kinds=KINDS)
    path.write_text("this is not TOML")
    with pytest.raises(forms.Refused):
        forms.load(path, kinds=KINDS)
    with pytest.raises(FileNotFoundError):
        forms.load(tmp_path / "absent", kinds=KINDS)


def test_product_starts_with_zero_approved_forms():
    assert forms.load() == []


def test_proposals_are_kept_and_never_overwrite_each_other(tmp_path):
    path = tmp_path / "n.sqlite3"
    store = Store(path)
    payload = form(status="proposed")
    original = deepcopy(payload)
    first = store.save_form_proposal(payload)
    bad = {**payload, "sentence": "You should follow {word}."}
    second = store.save_form_proposal(bad, forms.check(bad, kinds=KINDS))
    assert first != second
    store.reject_form_proposal(first, "Adam said no")
    with pytest.raises(ValueError):
        store.reject_form_proposal(first, "rewriting the decision")
    with pytest.raises(ValueError):
        store.reject_form_proposal("missing", "no")
    store.connection.close()
    reopened = Store(path)
    saved = reopened.form_proposals()
    assert len(saved) == 2
    by_id = {p["id"]: p for p in saved}
    assert by_id[first]["payload"] == original
    assert by_id[first]["status"] == "rejected" and by_id[first]["reason"] == "Adam said no"
    assert by_id[second]["payload"] == bad and by_id[second]["reason"] == "advice"
    assert fill(by_id[first]["payload"]) is None
    assert payload == original
    assert reopened.connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_schema_addition_preserves_existing_question_and_answer(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript('''
        CREATE TABLE questions (id TEXT PRIMARY KEY, question TEXT NOT NULL, asked_at REAL NOT NULL, surface TEXT);
        INSERT INTO questions VALUES ('q1', 'My exact words', 123, 'web');
        CREATE TABLE answers (question_id TEXT PRIMARY KEY, status TEXT NOT NULL, answer TEXT, text TEXT,
            reply_json TEXT, gate_ok INTEGER, gate_reason TEXT, finished REAL NOT NULL, nucleus_hash TEXT);
        INSERT INTO answers VALUES ('q1', 'answered', 'aligned', 'Exact answer', '{}', 1, NULL, 124, 'hash');
    ''')
    before = {table: db.execute(f"SELECT * FROM {table}").fetchall() for table in ("questions", "answers")}
    db.close()
    store = Store(path)
    for table, rows in before.items():
        assert store.connection.execute(f"SELECT * FROM {table}").fetchall() == rows
    assert store.form_proposals() == []
    assert store.connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_proposal_payload_cannot_approve_itself(tmp_path):
    store = Store(tmp_path / "n.sqlite3")
    raw = form(status="approved")
    store.save_form_proposal(raw)
    saved = store.form_proposals()[0]
    assert saved["payload"] == raw  # retain the attempted approval as evidence
    assert saved["status"] == saved["form"]["status"] == "proposed"
    assert fill(saved["form"]) is None
