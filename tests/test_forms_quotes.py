"""Slice 3c: exact screen quotes, strict wording, and no approval side effects."""
from dataclasses import replace
import json

import pytest

from nucleus import forms, forms_night as night, forms_patterns as patterns
from test_forms_night import KINDS, candidate, copy, miss, run
from test_forms_patterns import checked_form


def screen(first='Keep  “my words” — as written', second='Room to grow'):
    return forms.Screen('aligned', ('FLOW',), (
        forms.Row('FLOW', 'r1', 'depends on', first),
        forms.Row('FLOW', 'r2', 'rejects', second)))


def test_exact_whole_quotes_and_origins_with_punctuation_spaces_and_braces():
    source = screen('Keep  “my words” — {word} and \\ paths', 'Room to grow')
    filled = forms.preview(checked_form(), source, kinds=KINDS)
    assert filled.text == 'FLOW depends on “Keep  “my words” — {word} and \\ paths” and rejects “Room to grow”.'
    assert [(p.text, p.source) for p in filled.parts if p.source.endswith('.quote')] == [
        (source.rows[0].quote, 'screen.rows[0].quote'), (source.rows[1].quote, 'screen.rows[1].quote')]
    assert forms.fill(checked_form(), source, kinds=KINDS) is None


def test_quotes_cannot_come_from_another_word_or_a_missing_snapshot_field():
    for source in [
        replace(screen(), words=('FLOW', 'LIFT'), rows=(screen().rows[0], forms.Row('LIFT', 'r2', 'rejects', 'Wrong word'))),
        replace(screen(), rows=(screen().rows[0], forms.Row('FLOW', 'r2', 'rejects'))),
    ]:
        assert forms.preview(checked_form(), source, kinds=KINDS) is None


def test_shortest_safe_quote_is_whole_and_ties_keep_screen_order():
    source = replace(screen(), rows=(
        forms.Row('FLOW', 'a', 'depends on', 'not'),
        forms.Row('FLOW', 'b', 'depends on', 'A longer safe source quote'),
        forms.Row('FLOW', 'c', 'depends on', 'My words'),
        forms.Row('FLOW', 'd', 'depends on', 'My voice'), screen().rows[1]))
    filled = forms.preview(checked_form(), source, kinds=KINDS)
    quote = next(p for p in filled.parts if p.source.endswith('.quote'))
    assert (quote.text, quote.source) == ('My words', 'screen.rows[2].quote')


@pytest.mark.parametrize('word', [
    'not', 'does not', 'cannot', 'no evidence', "can't", 'doesn’t', 'without',
    'unless', 'however', 'might', 'maybe', 'but', 'never', 'NOT',
    'establish', 'establishes', 'established', 'claim', 'claims', 'prerequisite',
    'prerequisites', 'containment', 'necessity', 'coexistence',
])
def test_banned_words_are_refused_in_template_and_unavailable_in_exact_quote(word):
    proposal = checked_form(sentence=candidate()['sentence'][:-1] + ' ' + word + '.')
    assert forms.check(proposal, kinds=KINDS) is not None
    assert forms.preview(checked_form(), screen(first=word), kinds=KINDS) is None


def test_advice_inside_a_quote_is_never_shown():
    assert forms.preview(checked_form(), screen(first='You should act'), kinds=KINDS) is None


@pytest.mark.parametrize('blank,reason', [
    ('quote:', 'unknown middle word in quote blank'),
    ('quote:depends on.extra', 'unknown middle word in quote blank'),
    ('quote:supports', 'quote blank needs its named middle word in kinds_present'),
])
def test_quote_blank_requires_exact_known_kind_and_condition(blank, reason):
    assert forms.check(checked_form(sentence='{word} {' + blank + '}.'), kinds=KINDS) == reason


def test_repeating_one_quote_does_not_join_two_rows():
    proposal = checked_form(sentence='{word} rejects {quote:rejects} and rejects {quote:rejects}.')
    assert patterns.check(proposal, KINDS) == patterns.NEEDS_QUOTES


def test_two_frame_sentences_are_refused():
    proposal = checked_form(sentence='{word} depends on {quote:depends on}. It rejects {quote:rejects}.')
    assert patterns.check(proposal, KINDS) == patterns.ONE_SENTENCE


def test_historical_quote_uses_the_displayed_unescape_and_never_current_record():
    quote = 'His \\"exact\\" words with  spaces'
    displayed = 'His "exact" words with  spaces'
    raw = {'painted': True, 'reply_json': json.dumps({'answer': 'aligned', 'words': [{'word': 'FLOW'}],
        'records': [{'id': 'r1', 'quote': quote}]}), 'text': 'aligned and why\n\nFLOW depends on “' + displayed + '”'}
    restored = night.saved_screen(raw, KINDS)
    assert restored.rows[0].quote == displayed
    raw['text'] = raw['text'].replace('  spaces', ' spaces')
    with pytest.raises(forms.Refused, match='no unambiguous printed middle word'):
        night.saved_screen(raw, KINDS)


def test_every_actual_3b_form_is_refused_and_rejection_preserves_payload(copy):
    from pathlib import Path
    old = json.loads((Path(__file__).parents[1] / 'docs/forms-slice-3b-night.json').read_text())
    before = {}
    for result in old['results']:
        value = result['payload']
        pid = copy.save_form_proposal(value, result['reason'])
        before[pid] = value
    # Real middle words are needed to exercise each original form's actual wording.
    real_kinds = sorted(set(KINDS) | {k for r in old['results'] for k in r['payload']['when'].get('kinds_present', [])})
    for value in before.values():
        assert forms.check(value, kinds=real_kinds) or patterns.check(value, real_kinds)
    result = run(copy, [])
    assert len(result['prior_proposals_refused']) == 11
    assert len(copy.form_proposals()) == 12
    assert all(p['status'] == 'rejected' and p['payload'] == before[p['id']] for p in copy.form_proposals())
