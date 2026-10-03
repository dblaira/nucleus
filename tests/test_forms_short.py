"""Adam's review of 2026-10-02: one short line, his words only, question shown with the answer."""
from nucleus import forms, forms_middle as middle, forms_short, serve

KINDS = ['supports', 'depends on', 'rejects', 'enables', 'explains']


def word_form(status='approved'):
    return dict(number='F-90', when={'answer': 'aligned'}, sentence=middle.WORD_FRAME,
                status=status, author='test only', date='2026-10-02')


def screen(meaning, answer='aligned'):
    return forms.Screen(answer, ('FLOW',), (forms.Row('FLOW', 'r1', 'depends on', 'a row quote'),),
                        False, (forms.Meaning('FLOW', meaning),), (), (), True, ())


def test_word_frame_fills_from_his_shortest_meaning_only():
    filled = forms.fill(word_form(), screen('If a process becomes a worry or burden kill it, and think BIGGER!'), kinds=KINDS)
    assert filled.text == 'That’s FLOW: “If a process becomes a worry or burden kill it, and think BIGGER!”.'
    assert [p.source for p in filled.parts if not p.source.startswith('form')] == ['screen.words[0]', 'screen.meanings[0].quote']


def test_a_long_meaning_never_fires():
    long = ' '.join(['word'] * 21)
    assert forms.fill(word_form(), screen(long), kinds=KINDS) is None


def test_no_filled_line_is_longer_than_the_day_limit():
    long_form = dict(word_form(), sentence='{word} depends on “{quote:depends on}”.',
                     when={'answer': 'aligned', 'kinds_present': ['depends on']})
    row = forms.Row('FLOW', 'r1', 'depends on', ' '.join(['long'] * 30))
    long_screen = forms.Screen('aligned', ('FLOW',), (row,), False, (), (), (), True, ())
    assert forms.fill(long_form, long_screen, kinds=KINDS) is None
    assert forms.MAX_WORDS == 25


def test_word_frame_fires_only_on_aligned_and_only_when_approved():
    assert forms.fill(word_form(), screen('short meaning', answer='not_sure'), kinds=KINDS) is None
    assert forms.fill(word_form(status='proposed'), screen('short meaning'), kinds=KINDS) is None
    assert forms.preview(word_form(status='proposed'), screen('short meaning'), kinds=KINDS) is not None


def test_review_refuses_lines_built_from_record_quotes_and_the_long_frame():
    quote_join = dict(word_form(), when={'answer': 'aligned', 'kinds_present': ['depends on', 'rejects']},
                      sentence='{word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.')
    assert forms_short.his_words_reason(quote_join) == middle.NOT_HIS_WORDS
    old_middle = dict(word_form(), when={'answer': 'not_sure', 'graph_parts': True}, sentence=middle.PART_FRAME)
    assert forms_short.his_words_reason(old_middle) == middle.TOO_LONG
    assert forms_short.his_words_reason(word_form()) is None


def test_short_part_frame_names_his_word_without_pasting_the_meaning():
    form = dict(word_form(), when={'answer': 'not_sure', 'graph_parts': True}, sentence=middle.SHORT_PART_FRAME)
    parts = (forms.GraphPart('I feel pulled toward the idea', ('PULLED',), ('PULLED',), (), {'PULLED': ('r1',)}),
             forms.GraphPart('my sleep is bad', (), (), (), {}))
    s = forms.Screen('not_sure', ('PULLED',), (), False, (forms.Meaning('PULLED', ' '.join(['long'] * 60)),), (), (), True, parts)
    filled = forms.fill(form, s, kinds=KINDS)
    assert filled.text == '“I feel pulled toward the idea” — that’s PULLED. “my sleep is bad” is still open.'


def test_page_shows_the_question_before_the_answer():
    proposal = {'id': 'p1', 'number': 'F-90', 'form': word_form('proposed'), 'error': None, 'version': 'v',
                'real_fit_count': 1, 'practice_fit_count': 0,
                'examples': [{'question': 'Why do I lose interest?', 'text': 'That’s FLOW: “kill it”.', 'surface': 'web'}]}
    page = serve.forms_page([proposal], 'token')
    assert page.index('You asked') < page.index('Why do I lose interest?') < page.index('Cowboy AI says') < page.index('That’s FLOW')
