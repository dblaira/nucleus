"""Both halves come from the visible answer, with a narrow missing-evidence scope."""
from dataclasses import asdict, replace
import json

import pytest

from nucleus import forms, forms_middle as middle, forms_night as night, gate


@pytest.fixture(autouse=True)
def legacy_long_lines(monkeypatch):
    """These fixtures test the exact mechanics of frames Adam retired on 2026-10-02 as
    too long and not his words. The 25-word day limit is tested in test_forms_short.py."""
    monkeypatch.setattr(forms, 'MAX_WORDS', None)


KINDS = ['supports', 'depends on', 'rejects']


def form(**changes):
    value = dict(number='F-50', status='approved', author='test only', date='2026-10-02',
                 when={'answer': 'not_sure', 'missing_why': True},
                 sentence=middle.HEADS[0]+middle.TAILS['missing_why'])
    value.update(changes)
    return value


def screen():
    words = [{'word': 'FLOW', 'meanings': ['Work feels like a pull.'], 'why': 'This matches the pull in your question.'}]
    records = [{'id': 'record-1', 'leaf': 'record-1', 'quote': 'Work feels like a pull and holds my whole focus.',
                'why': 'This shows what holds focus, but the records do not show how the app behaved.',
                'strength': '', 'accepted_at': ''}]
    text = gate.compose('not_sure', words, records, [])
    return middle.from_visible('not_sure', words, records, text, KINDS), text


def test_middle_both_halves_keep_whole_exact_screen_quotes_and_gap():
    saved, text = screen()
    filled = forms.fill(form(), saved, kinds=KINDS)
    assert filled.text == ('FLOW — “Work feels like a pull.” — and “Work feels like a pull and holds my whole focus.” '
                           'line up here, while the records do not show how the app behaved.')
    assert '..' not in filled.text
    assert middle.is_filled(filled)
    for part in filled.parts:
        if part.source != 'form.sentence':
            assert part.text in text
    assert saved.rows[0].kind is None
    assert night.restore_screen(asdict(saved)) == saved


@pytest.mark.parametrize('answer', ['aligned', 'dont_know'])
def test_not_sure_forms_fire_only_on_not_sure(answer):
    saved, _ = screen()
    assert forms.fill(form(), replace(saved, answer=answer), kinds=KINDS) is None
    assert forms.check(form(when={'answer': answer, 'missing_why': True}), kinds=KINDS) == 'middle-option forms fire only on not_sure'


def test_proposed_middle_form_is_never_chosen(tmp_path):
    saved, _ = screen()
    p = tmp_path/'forms.txt'
    from nucleus.forms_review import append_text
    proposed = form(status='proposed')
    p.write_text(append_text('forms = []\n', proposed, []))
    assert forms.preview(proposed, saved, kinds=KINDS)
    assert forms.fill(proposed, saved, kinds=KINDS) is None
    assert forms.pick(saved, p) == (None, 'no approved forms')


@pytest.mark.parametrize('why', ['The app is not good.', 'This may fit your question.', 'Your word has no link in the model list.',
                                'The question does not give enough detail.', 'This record shows a gap.'])
def test_negative_or_uncertain_why_is_not_missing_record_evidence(why):
    assert middle.gap_span(why) is None
    saved, _ = screen()
    assert forms.fill(form(), replace(saved, whys=(forms.Why(why),)), kinds=KINDS) is None


def test_quote_slots_do_not_invent_missing_record_or_word_names():
    saved, _ = screen()
    no_rows = replace(saved, rows=())
    no_meanings = replace(saved, meanings=())
    assert forms.fill(form(), no_rows, kinds=KINDS) is None
    assert forms.fill(form(), no_meanings, kinds=KINDS) is None
    unknown = form(sentence='FLOW lines up but the app failed.')
    assert forms.check(unknown, kinds=KINDS)


def test_only_explicitly_printed_missing_words_can_fill():
    saved, _ = screen()
    f = form(when={'answer':'not_sure','missing_links':True},sentence=middle.HEADS[0]+middle.TAILS['missing_word'])
    assert forms.fill(f, replace(saved, missing_links=True), kinds=KINDS) is None
    assert forms.fill(f, replace(saved, missing_links=True, missing_words=('FLOW',)), kinds=KINDS).text.endswith('FLOW has no links.')


def test_incomplete_model_middle_word_display_cannot_prove_absent_kind():
    saved, _ = screen()
    f = form(when={'answer':'not_sure','kinds_absent':['rejects']},sentence=middle.HEADS[0]+middle.TAILS['absent_kind'])
    assert forms.fill(f, saved, kinds=KINDS) is None
    complete = replace(saved, rows=(replace(saved.rows[0], kind='supports'),), middle_words_complete=True)
    assert forms.fill(f, complete, kinds=KINDS).text.endswith('rows leave out “rejects”.')
    rejected = replace(saved, rows=(replace(saved.rows[0],kind='rejects'),))
    assert forms.fill(f, rejected, kinds=KINDS) is None


def test_exact_negative_and_advice_source_quotes_are_preserved_with_their_binding():
    saved, _ = screen()
    negative = replace(saved, meanings=(forms.Meaning('FLOW', 'thinking momentum is not feeling momentum'),), rows=(forms.Row('FLOW','r1',None,'Interest lasts when there is feeling momentum.'),))
    assert 'thinking momentum is not feeling momentum' in forms.fill(form(), negative, kinds=KINDS).text
    advice = replace(saved, meanings=(forms.Meaning('FLOW', 'You should build it.'),),
                     rows=(forms.Row('FLOW','r1','supports','You should build it.'),))
    assert 'You should build it.' in forms.fill(form(), advice, kinds=KINDS).text
    # Author-written negative words still fail.
    old = form(when={'answer':'not_sure'},sentence='{word} does not fit.')
    assert 'negative or caveat' in forms.check(old,kinds=KINDS)


def test_exact_counts_refused_in_middle_approved_file():
    assert forms.check(form(when={'answer':'not_sure','missing_why':True,'record_count':1}), kinds=KINDS) == 'exact counts refused'


def test_saved_screen_does_not_enrich_quotes_from_todays_dictionary():
    saved, text = screen()
    raw={'text':text,'reply_json':json.dumps({'answer':'not_sure','words':[{'word':'FLOW','why':'This matches the pull in your question.'}],
         'records':[{'id':'record-1','quote':'Work feels like a pull and holds my whole focus.','why':saved.whys[1].text}]})}
    assert middle.saved_screen(raw,KINDS) == saved
    raw['text']=text.replace('FLOW — “Work feels like a pull.”\n','')
    assert middle.saved_screen(raw,KINDS).meanings == ()


def test_a_record_with_only_missing_why_does_not_become_an_aligned_part():
    saved, text = screen()
    why='The records do not show how the app behaved.'
    words=[{'word':'FLOW','why':'This matches the pull in your question.'}]
    records=[{'id':'record-1','quote':'Work feels like a pull and holds my whole focus.','why':why}]
    text=text.replace(saved.whys[1].text,why)
    assert middle.from_visible('not_sure',words,records,text,KINDS).rows == ()


@pytest.mark.parametrize('why', ["FLOW cannot match this question.", "FLOW can't fit this question.",
                                "FLOW fails to match this question.", "FLOW might fit this question."])
def test_positive_half_refuses_negative_or_uncertain_alignment(why):
    assert not middle.positive_half(why)


def test_missing_why_cannot_add_a_guess_or_a_narrower_no_links_claim():
    assert middle.gap_span('Your records do not show how the app behaved, but it probably broke.') is None
    saved, text = screen()
    words=[{'word':'FLOW','why':'FLOW has no links to this one record.'}]
    recovered=middle.from_visible('not_sure',words,[],text.replace('This matches the pull in your question.',words[0]['why']),KINDS)
    assert recovered.missing_words == ()


def test_a_meaning_quote_is_not_a_displayed_record_quote():
    words=[{'word':'FLOW','why':'FLOW fits this question.'}]
    records=[{'id':'r1','quote':'A clear path','why':'This shows a path.'}]
    text='Not sure.\n\nFLOW — “A clear path”\nFLOW fits this question.\n\n“No exact quote row here”\nThis shows a path.'
    assert middle.from_visible('not_sure',words,records,text,KINDS).rows == ()


def test_a_quoted_word_why_is_not_a_meaning():
    why='FLOW — “Fake fits here”'
    words=[{'word':'FLOW','why':why}]
    records=[{'id':'r1','quote':'Work feels like a pull and holds my whole focus.','why':'This shows a pull, but the records do not show how the app behaved.'}]
    text='Not sure.\n\nFLOW — “Work feels like a pull.”\n'+why+'\n\n“Work feels like a pull and holds my whole focus.”\n'+records[0]['why']
    saved=middle.from_visible('not_sure',words,records,text,KINDS)
    assert saved.meanings == (forms.Meaning('FLOW','Work feels like a pull.'),)
    assert 'Fake fits here' not in forms.fill(form(),saved,kinds=KINDS).text


def test_a_chosen_opening_never_becomes_a_new_screen_source():
    saved, text=screen()
    filled=forms.fill(form(),saved,kinds=KINDS)
    changed=filled.text+text[text.find('\n'):]
    words=[{'word':'FLOW','why':saved.whys[0].text}]
    records=[{'id':'record-1','quote':saved.rows[0].quote,'why':saved.whys[1].text}]
    assert middle.from_visible('not_sure',words,records,changed,KINDS) == saved


def test_a_word_why_cannot_supply_a_record_middle_word():
    why='FLOW supports “A clear path”'
    words=[{'word':'FLOW','why':why}]
    records=[{'id':'r1','quote':'A clear path','why':'This shows a path.'}]
    text='Not sure.\n\nFLOW — “Work feels like a pull.”\n'+why+'\n\n“A clear path”\nThis shows a path.'
    saved=middle.from_visible('not_sure',words,records,text,KINDS)
    assert saved.rows[0].kind is None


def test_two_unrelated_positive_sources_never_get_paired():
    saved,_=screen()
    unrelated=replace(saved,meanings=(forms.Meaning('FLOW','thinking momentum is not feeling momentum'),))
    assert forms.fill(form(),unrelated,kinds=KINDS) is None
    matching=replace(saved,meanings=(forms.Meaning('FLOW','thinking momentum is not feeling momentum'),),
                     rows=(forms.Row('FLOW','r1',None,'Interest lasts when there is feeling momentum.'),))
    assert forms.fill(form(),matching,kinds=KINDS)


def test_shared_names_and_possessive_suffix_do_not_tie_unrelated_quotes():
    assert middle.shared_words("Adam's FLOW", "Adam's LIFT") == set()


def test_skipping_an_unbound_row_cannot_prove_an_absent_middle_word():
    words=[{'word':'FLOW','why':'FLOW fits this question.'}]
    records=[{'id':'r1','quote':'Work feels clear','why':'This shows a path.'},
             {'id':'r2','quote':'Other words','why':'The records do not show what happened.'}]
    text='Not sure.\n\nFLOW — “Work feels clear”\nFLOW fits this question.\n\nFLOW supports “Work feels clear”\nThis shows a path.\n\n“Other words”\nThe records do not show what happened.'
    saved=middle.from_visible('not_sure',words,records,text,KINDS)
    assert not saved.middle_words_complete
    f=form(when={'answer':'not_sure','kinds_absent':['rejects']},sentence=middle.HEADS[0]+middle.TAILS['absent_kind'])
    assert forms.fill(f,saved,kinds=KINDS) is None
