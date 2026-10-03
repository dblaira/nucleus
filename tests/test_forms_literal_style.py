"""Author words are judged; Adam's exact source text is never rewritten or graded."""
import json
from dataclasses import replace

import pytest

from nucleus import forms, forms_middle as middle, forms_patterns as patterns, forms_style
from nucleus.model import ModelReply


@pytest.fixture(autouse=True)
def legacy_long_lines(monkeypatch):
    """These fixtures test the exact mechanics of frames Adam retired on 2026-10-02 as
    too long and not his words. The 25-word day limit is tested in test_forms_short.py."""
    monkeypatch.setattr(forms, 'MAX_WORDS', None)


KINDS = ['depends on', 'rejects', 'supports', 'should not']


def row_form(**changes):
    value = {'number': 'F-71', 'when': {'kinds_present': ['depends on', 'rejects']},
             'sentence': '{word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.',
             'status': 'approved', 'author': 'isolated fixture', 'date': '2026-10-02'}
    value.update(changes)
    return value


def screen(quote):
    return forms.Screen('aligned', ('FLOW',), (
        forms.Row('FLOW', 'r1', 'depends on', quote), forms.Row('FLOW', 'r2', 'rejects', 'Room to grow')))


@pytest.mark.parametrize('quote', [
    'thinking momentum is not feeling momentum',
    'You should establish a prerequisite claim for coexistence.',
    'No evidence. Cannot. Maybe. Probably. However, act.',
    'One. Two. Three. Four. Five. Six.',
    'A physiological multidimensional interrelationship.',
    'First exact line.\nSecond exact line.',
    'x' * 1100,
])
def test_quoted_sources_keep_every_character_without_vocabulary_or_style_vetoes(quote):
    filled = forms.fill(row_form(), screen(quote), kinds=KINDS)
    assert filled.text == f'FLOW depends on “{quote}” and rejects “Room to grow”.'
    assert next(p for p in filled.parts if p.source == 'screen.rows[0].quote').text == quote


def test_only_author_literals_reach_advice_and_style_detectors(monkeypatch):
    checked = []
    advice, style = forms.explain.check, forms_style.check
    def advice_check(text, words):
        checked.append(text)
        return advice(text, words)
    def style_check(text):
        checked.append(text)
        return style(text)
    monkeypatch.setattr(forms.explain, 'check', advice_check)
    monkeypatch.setattr(forms_style, 'check', style_check)
    quote = 'You should not establish a claim or prerequisite.'
    assert forms.fill(row_form(), screen(quote), kinds=KINDS)
    assert checked and all(text == '  depends on “ ” and rejects “ ”.' for text in checked)


def test_blank_names_and_filled_middle_words_are_not_author_vocabulary():
    value = row_form(when={'kinds_present': ['should not', 'supports']},
                     sentence='{word} joins “{quote:should not}” and “{quote:supports}”.')
    saved = forms.Screen('aligned', ('FLOW',), (
        forms.Row('FLOW', 'r1', 'should not', 'Exact first quote'),
        forms.Row('FLOW', 'r2', 'supports', 'Exact second quote')))
    assert forms.check(value, kinds=KINDS) is None
    assert forms.fill(value, saved, kinds=KINDS).text == 'FLOW joins “Exact first quote” and “Exact second quote”.'


@pytest.mark.parametrize('literal, reason', [
    ('You should follow', 'advice'), ('does not fit', 'negative or caveat'),
    ('might help', 'negative or caveat'), ('needs a prerequisite', 'blocked word'),
])
def test_author_advice_negative_caveat_and_abstract_words_remain_refused(literal, reason):
    value = row_form(sentence='{word} ' + literal + ' “{quote:depends on}” and “{quote:rejects}”.')
    assert reason in forms.check(value, kinds=KINDS)
    with pytest.raises(forms.Refused, match=reason):
        forms.fill(value, screen('His exact source'), kinds=KINDS)


def test_middle_sources_are_exact_without_source_style_judgments():
    quote = 'You should establish a prerequisite. Not a claim. No evidence of coexistence.'
    value = row_form(when={'answer': 'not_sure', 'missing_why': True},
                     sentence=middle.HEADS[0] + middle.TAILS['missing_why'])
    saved = forms.Screen('not_sure', ('FLOW',), (forms.Row('FLOW', 'r1', 'supports', quote),),
                         meanings=(forms.Meaning('FLOW', quote),),
                         whys=(forms.Why('Your records do not show how that prerequisite claim worked.'),))
    filled = forms.fill(value, saved, kinds=KINDS)
    assert filled.text.count(quote) == 2
    assert filled.text.endswith(saved.whys[0].text)
    assert forms.fill(value, replace(saved, meanings=()), kinds=KINDS) is None
    assert forms.fill({**value, 'status': 'proposed'}, saved, kinds=KINDS) is None


def test_graph_authored_missing_question_part_keeps_source_words_and_punctuation():
    part = 'Why might a prerequisite claim fail, but not for me?'
    why = 'you said FLOW. Your records do not show “' + part + '”.'
    span = middle.gap_span(why)
    assert span is not None and why[slice(*span)] == 'Your records do not show “' + part + '”.'
    assert middle.gap_span(why + ' It probably broke.') is None
    assert middle.gap_span('Your records do not show how it worked, but it probably broke.') is None


def test_graph_gap_keeps_nested_quotes_and_multiple_exact_missing_parts():
    missing = 'Your records do not show “Why does “maybe” mean no?”. Your records do not show “What should I claim?”.'
    why = 'you said FLOW. ' + missing
    assert why[slice(*middle.gap_span(why))] == missing
    assert middle.gap_span('Your records do not show “what happened”. It probably broke “the app”.') is None


def test_reviewer_receives_literal_words_for_style_and_full_sources_for_binding():
    class Audit:
        def __init__(self):
            self.calls = []
        def save_model_call(self, *args):
            self.calls.append(args)
    audit = Audit()
    quote = 'You should not establish a prerequisite claim.'
    value = row_form(status='proposed')
    filled = forms.preview(value, screen(quote), kinds=KINDS)
    original = {'form': value, 'examples': [{'text': filled.text}]}
    def call(prompt, *, schema):
        assert 'ONLY in\nliteral_words' in prompt
        assert 'source wording never raises it' in prompt
        candidate = json.loads(prompt.split('\nCandidates:\n')[1])[0]
        assert candidate['literal_words'] == '  depends on “ ” and rejects “ ”.'
        assert quote in candidate['examples'][0]['text']
        return ModelReply('test', 'literal-review', json.dumps({'reviews': [
            {'number': 'F-71', 'verdict': 'explains_pattern', 'reason': 'The literal frame is plain.',
             'reading_grade': 3, 'one_sentence': True}]}))
    result = patterns.review(audit, 'isolated', [original], model_call=call)
    assert result['F-71']['reading_grade'] == 3
    assert 'literal_words' not in original and len(audit.calls) == 1
    assert patterns.POLICY == 'graph-parts-text-v3'
