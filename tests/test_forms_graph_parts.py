"""Graph-part forms copy checked question slices, with no day model or new meaning."""
from dataclasses import asdict, replace
import json

import pytest

from nucleus import forms, forms_middle as middle, forms_patterns as patterns, gate
from nucleus.model import ModelReply


@pytest.fixture(autouse=True)
def legacy_long_lines(monkeypatch):
    """The long frame here was retired on 2026-10-02; its mechanics stay tested without the
    25-word day limit, which test_forms_short.py covers."""
    monkeypatch.setattr(forms, 'MAX_WORDS', None)


KINDS = ['supports', 'rejects', 'depends on']


def proposal(**changes):
    value = dict(number='F-90', when={'answer': 'not_sure', 'graph_parts': True},
                 sentence=middle.PART_FRAME, status='approved', author='test only', date='2026-10-02')
    value.update(changes)
    return value


def parts(open_text='I do not know how the app behaved.', connected_text='The work feels like a pull.'):
    return (forms.GraphPart(connected_text, ('FLOW',), ('FLOW',), (), {'FLOW': ('https://example.test/r1',)}),
            forms.GraphPart(open_text, (), (), (), {}))


def screen(**changes):
    value = forms.Screen('not_sure', ('FLOW',), (), meanings=(forms.Meaning('FLOW', 'If a process becomes a worry or burden kill it, and think BIGGER!'),), parts=parts())
    return replace(value, **changes)


def visible(part_values=None, *, appendix=False):
    part_values = parts() if part_values is None else part_values
    proof = middle.graph_part_whys(part_values)['FLOW']
    words = [{'word': 'FLOW', 'meanings': [screen().meanings[0].quote],
              'why': 'you said FLOW' if appendix else proof}]
    text = gate.compose('not_sure', words, [], [])
    if appendix:
        text += '\n\n' + proof
    return words, text


def test_graph_part_frame_joins_both_exact_parts_and_bound_meaning():
    saved = screen()
    assert forms.check(proposal(), kinds=KINDS) is None
    assert patterns.check(proposal(), KINDS) is None
    filled = forms.fill(proposal(), saved, kinds=KINDS)
    assert filled.text == ('“The work feels like a pull.” lines up with FLOW: '
                           '“If a process becomes a worry or burden kill it, and think BIGGER!”. '
                           '“I do not know how the app behaved.” is still open.')
    assert middle.is_graph_parts(proposal()) and middle.is_graph_part(proposal())
    assert middle.is_filled(filled)
    assert [(p.text, p.source) for p in filled.parts if p.source.startswith('screen.parts[')] == [
        (saved.parts[0].text, 'screen.parts[0].text'), (saved.parts[1].text, 'screen.parts[1].text')]
    assert next(p for p in filled.parts if p.source == 'screen.meanings[0].quote').text == saved.meanings[0].quote


@pytest.mark.parametrize('source', [
    'You should establish a prerequisite, but no evidence shows coexistence.',
    'Why might “maybe” mean no? I cannot claim this.',
    '{not_a_blank} is Adam’s exact text.\nAnother whole line.',
])
def test_question_part_source_words_and_punctuation_are_never_style_judged(source):
    saved = screen(parts=parts(source, source))
    filled = forms.fill(proposal(), saved, kinds=KINDS)
    assert filled.text.count(source) == 2
    assert filled.parts[0].text == '“'
    assert [p.text for p in filled.parts if p.source.startswith('screen.parts[')] == [source, source]


@pytest.mark.parametrize('answer', ['aligned', 'dont_know'])
def test_graph_part_forms_fire_only_on_not_sure(answer):
    assert forms.fill(proposal(), screen(answer=answer), kinds=KINDS) is None
    assert forms.check(proposal(when={'answer': answer, 'graph_parts': True}), kinds=KINDS) == 'middle-option forms fire only on not_sure'


@pytest.mark.parametrize('when,reason', [
    ({'answer': 'not_sure'}, 'graph-part blanks need graph_parts=true'),
    ({'answer': 'not_sure', 'graph_parts': False}, 'graph-part blanks need graph_parts=true'),
    ({'answer': 'not_sure', 'graph_parts': 'true'}, 'graph_parts must be boolean'),
    ({'answer': 'not_sure', 'graph_parts': True, 'word_count': 1}, 'exact counts refused'),
])
def test_graph_part_conditions_are_required_and_counts_stay_minimums(when, reason):
    assert forms.check(proposal(when=when), kinds=KINDS) == reason
    assert forms.check(proposal(when={'answer': 'not_sure', 'graph_parts': True, 'word_count': {'min': 1}}), kinds=KINDS) is None


@pytest.mark.parametrize('sentence', [
    middle.PART_FRAME + ' You should act.',
    middle.PART_FRAME.replace('is still open', 'cannot be settled'),
    middle.PART_FRAME.replace('{meaning}', '{record_quote}'),
    '“{lined_up_part}” fits. “{open_part}” is open.',
])
def test_two_sentence_and_caveat_exception_is_only_the_exact_authorized_frame(sentence):
    value = proposal(sentence=sentence)
    assert not middle.is_graph_parts(value)
    assert forms.check(value, kinds=KINDS) == 'graph-part sentence must use the exact lined-up and open frame'


def test_missing_metadata_or_one_connected_part_cannot_fill():
    for value in ((), parts()[:1], parts()[1:], (parts()[0], parts()[0])):
        assert forms.fill(proposal(), screen(parts=value), kinds=KINDS) is None
    assert forms.fill(proposal(), screen(meanings=()), kinds=KINDS) is None


def test_connected_part_cannot_use_another_words_meaning_or_an_unprinted_word():
    saved = screen(words=('FLOW', 'LIFT'), meanings=(forms.Meaning('LIFT', 'Harmony among meaningful relationships.'),))
    assert forms.fill(proposal(), saved, kinds=KINDS) is None
    other = replace(parts()[0], words=('LIFT',), connected=('LIFT',), records={'LIFT': ('https://example.test/r1',)})
    assert forms.fill(proposal(), screen(parts=(other, parts()[1])), kinds=KINDS) is None


def test_second_connected_part_is_never_called_open():
    other = replace(parts()[0], text='The app feels like a pull too.')
    assert forms.fill(proposal(), screen(parts=(parts()[0], other)), kinds=KINDS) is None


@pytest.mark.parametrize('bad', [
    replace(parts()[0], connected=(), missing=('FLOW',)),
    replace(parts()[0], records={'FLOW': ()}),
    replace(parts()[0], connected=('LIFT',)),
    replace(parts()[1], records={'FLOW': ('https://example.test/r1',)}),
])
def test_inconsistent_graph_metadata_is_refused_before_filling(bad):
    with pytest.raises(forms.Refused):
        forms.fill(proposal(), screen(parts=(bad, parts()[1])), kinds=KINDS)


@pytest.mark.parametrize('appendix', [False, True])
def test_graph_parts_bind_only_to_exact_printed_scaffolds_and_meanings(appendix):
    words, text = visible(appendix=appendix)
    saved = middle.from_visible('not_sure', words, [], text, KINDS, parts=parts())
    assert saved.parts == parts() and saved.meanings == screen().meanings
    filled = forms.fill(proposal(), saved, kinds=KINDS)
    assert all(p.text in text for p in filled.parts if p.source != 'form.sentence')
    forged = (replace(parts()[0], text='A different part never printed'), parts()[1])
    with pytest.raises(forms.Refused, match='not printed'):
        middle.from_visible('not_sure', words, [], text, KINDS, parts=forged)
    without_meaning = text.replace('FLOW — “' + screen().meanings[0].quote + '”\n', '')
    assert forms.fill(proposal(), middle.from_visible('not_sure', words, [], without_meaning, KINDS, parts=parts()), kinds=KINDS) is None


def test_graph_scaffold_keeps_multiple_connected_parts_and_nested_source_quotes():
    more = replace(parts()[0], text='Could “FLOW” mean pull?')
    saved_parts = (parts()[0], more, replace(parts()[1], text='Why should “maybe” mean no?'))
    proof = middle.graph_part_whys(saved_parts)['FLOW']
    gap = 'Your records do not show “Why should “maybe” mean no?”.'
    assert proof.endswith(gap)
    assert proof[slice(*middle.gap_span(proof))] == gap
    assert middle.gap_span(proof + ' It probably broke.') is None
    words, text = visible(saved_parts)
    assert middle.from_visible('not_sure', words, [], text, KINDS, parts=saved_parts).parts == saved_parts


def test_graph_parts_roundtrip_exactly_and_unknown_metadata_is_refused():
    serialized = json.loads(json.dumps([asdict(p) for p in parts()]))
    assert forms.restore_parts(serialized) == parts()
    with pytest.raises(forms.Refused, match='unknown or missing'):
        forms.restore_parts([{**serialized[0], 'model_guess': True}])
    words, text = visible()
    raw = {'text': text, 'reply_json': json.dumps({'answer': 'not_sure', 'words': words, 'records': [], 'parts': serialized})}
    assert middle.saved_screen(raw, KINDS).parts == parts()


def test_proposed_or_rejected_graph_part_form_never_produces_day_text(tmp_path):
    from nucleus.forms_review import append_text
    value = proposal(status='proposed')
    assert forms.preview(value, screen(), kinds=KINDS)
    assert forms.fill(value, screen(), kinds=KINDS) is None
    assert forms.preview(proposal(status='rejected'), screen(), kinds=KINDS) is None
    path = tmp_path / 'forms.txt'
    path.write_text(append_text('forms = []\n', value, []))
    assert forms.pick(screen(), path) == (None, 'no approved forms')


def test_graph_part_reviewer_gets_literal_style_and_scoped_two_sentence_exception():
    class Audit:
        def save_model_call(self, *args):
            pass
    def call(prompt, *, schema):
        assert 'These two short sentences' not in prompt  # writer instructions are separate
        assert 'Its two short sentences are explicitly\nallowed' in prompt
        assert 'ONLY in literal_words' in prompt
        candidate = json.loads(prompt.split('\nCandidates:\n')[1])[0]
        assert candidate['literal_words'] == '“ ” lines up with  : “ ”. “ ” is still open.'
        assert candidate['examples'][0]['screen']['parts'][1]['text'] == parts()[1].text
        return ModelReply('test', 'frame-review', json.dumps({'reviews': [
            {'number': 'F-90', 'verdict': 'explains_pattern', 'reason': 'Both checked question parts remain exact.',
             'reading_grade': 3, 'one_sentence': False}]}))
    value = proposal(status='proposed')
    result = patterns.review(Audit(), 'test', [{'form': value, 'examples': [{'screen': asdict(screen())}]}], model_call=call)
    assert result['F-90']['reading_grade'] == 3 and result['F-90']['one_sentence'] is False
