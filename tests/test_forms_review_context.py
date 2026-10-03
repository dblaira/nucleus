"""The review shows each exact question before its proposed future answer."""
from copy import deepcopy
from dataclasses import dataclass, field
from html.parser import HTMLParser

import pytest

from nucleus import forms, forms_night, forms_review, serve
from test_forms_night import copy
from test_forms_review import ready


@dataclass
class Element:
    tag: str
    attrs: dict
    order: int
    children: list = field(default_factory=list)

    @property
    def text(self):
        return ''.join(child.text if isinstance(child, Element) else child for child in self.children)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element('root', {}, -1)
        self.stack, self.nodes = [self.root], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), len(self.nodes))
        self.nodes.append(node)
        self.stack[-1].children.append(node)
        if tag not in {'img', 'meta', 'link', 'input', 'br', 'hr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def find(self, *, tag=None, cls=None):
        return [node for node in self.nodes if (tag is None or node.tag == tag)
                and (cls is None or cls in node.attrs.get('class', '').split())]


def proposal(number='F-90', *, examples=None):
    return {'number': number, 'id': 'proposal-' + number, 'version': 'test-snapshot', 'error': None,
            'real_fit_count': 5, 'practice_fit_count': 2,
            'form': {'when': {'answer': 'aligned', 'kinds_present': ['depends on', 'rejects']}},
            'examples': examples if examples is not None else [
                {'surface': 'web', 'question': 'What makes ALPHA fit this choice?',
                 'text': 'ALPHA depends on “A clear sign.” and rejects “A burden.”'},
                {'surface': 'practice', 'question': 'Where does BETA fit, but what happened with the app?',
                 'text': 'BETA depends on “A quiet place.” and rejects “Noise.”'},
                {'surface': 'web', 'question': 'Does GAMMA fit my work?',
                 'text': 'GAMMA depends on “Time to work.” and rejects “Lost time.”'}]}


def test_each_complete_question_precedes_its_corresponding_proposed_answer():
    value = proposal()
    original = deepcopy(value)
    page = serve.forms_page([value], 'test-token')
    document = Document(page)
    pairs = document.find(cls='example-pair')
    questions = document.find(cls='example-question')
    answers = document.find(cls='example')
    assert len(pairs) == len(questions) == len(answers) == 3
    assert [node.text for node in questions] == [e['question'] for e in value['examples']]
    assert [node.text for node in answers] == [e['text'] for e in value['examples']]
    for index, (question, answer) in enumerate(zip(questions, answers)):
        assert question.order < answer.order
        if index < 2:
            assert answer.order < questions[index + 1].order
    labels = document.find(tag='h3', cls='example-source')
    assert [node.text for node in labels] == ['Your question', 'Proposed answer', 'Practice question',
                                            'Proposed answer', 'Your question', 'Proposed answer']
    assert value == original


def test_exact_source_whitespace_quotes_and_markup_are_preserved_and_escaped():
    question = '  Why “ALPHA”?\n</p><script>alert("question")</script> & <img src=x onerror="bad">  '
    answer = 'ALPHA — “An exact quote.”\n<script>alert("answer")</script> & {unexpanded_source}'
    value = proposal(examples=[{'surface': 'web', 'question': question, 'text': answer}])
    page = serve.forms_page([value], 'test-token')
    document = Document(page)
    assert document.find(cls='example-question')[0].text == question
    assert document.find(cls='example')[0].text == answer
    assert not document.find(tag='script')
    assert all('onerror' not in node.attrs for node in document.nodes)
    assert '&lt;script&gt;' in page and '&amp;' in page
    assert '.example-question' in page and 'white-space:pre-wrap' in page


def test_question_answer_and_approval_scope_have_resolvable_accessible_labels():
    document = Document(serve.forms_page([proposal()], 'test-token'))
    ids = [node.attrs['id'] for node in document.nodes if 'id' in node.attrs]
    assert len(ids) == len(set(ids))
    by_id = {node.attrs['id']: node for node in document.nodes if 'id' in node.attrs}
    for node in document.find(cls='example-question') + document.find(cls='example'):
        label = by_id[node.attrs['aria-labelledby']]
        assert label.tag == 'h3'
        assert label.text in {'Your question', 'Practice question', 'Proposed answer'}
    for node in document.find(tag='button'):
        scope = by_id[node.attrs['aria-describedby']]
        assert scope.text == ('Yes allows this way of answering future questions that match this form. '
                              'No rejects this form and keeps it.')
    assert document.find(tag='article')[0].attrs['aria-labelledby'] == 'form-F-90'
    assert by_id['form-F-90'].text == 'F-90'


def test_supporting_conditions_follow_examples_and_choices_inside_closed_details():
    value = proposal()
    value['examples'][0]['graph_label'] = {'answer': 'aligned'}
    document = Document(serve.forms_page([value], 'test-token'))
    details = document.find(tag='details')
    assert len(details) == 1 and 'open' not in details[0].attrs
    assert details[0].children[0].tag == 'summary'
    assert details[0].children[0].text == 'When this answer would be used'
    assert document.find(cls='example')[-1].order < document.find(cls='choices')[0].order < details[0].order
    assert document.find(cls='fit-count')[0].order > details[0].order
    assert 'fits 5 of your questions · 2 practice questions' in details[0].text
    assert 'Fires when' in details[0].text and 'The rows include “depends on” and “rejects”' in details[0].text
    assert 'These fits are checked with your graph.' in details[0].text


@pytest.mark.parametrize('question', [None, '', ' \n\t ', 42])
def test_missing_question_disables_yes_keeps_no_and_never_mislabels_an_answer(question):
    value = proposal(examples=[{'surface': 'web', 'question': question, 'text': 'A proposed answer without its question.'}])
    document = Document(serve.forms_page([value], 'test-token'))
    assert not document.find(cls='example-pair') and not document.find(cls='example-question')
    buttons = document.find(tag='button')
    yes, no = buttons
    assert yes.text == 'Yes' and 'disabled' in yes.attrs
    assert no.text == 'No' and 'disabled' not in no.attrs
    alerts = [node for node in document.nodes if node.attrs.get('role') == 'alert']
    assert len(alerts) == 1 and 'missing its question or answer' in alerts[0].text
    assert alerts[0].attrs['id'] in yes.attrs['aria-describedby'].split()
    assert 'A proposed answer without its question.' not in document.root.text


def test_one_missing_question_blocks_approval_of_the_whole_form_without_hiding_good_pairs():
    value = proposal()
    del value['examples'][1]['question']
    document = Document(serve.forms_page([value], 'test-token'))
    assert [node.text for node in document.find(cls='example-question')] == [value['examples'][i]['question'] for i in (0, 2)]
    assert 'disabled' in document.find(tag='button')[0].attrs


def test_review_error_is_shown_plainly_before_the_choices_and_labels_disabled_yes():
    value = proposal()
    value['error'] = 'Question-based review is missing for “this <example>”.'
    page = serve.forms_page([value], 'test-token')
    document = Document(page)
    alert = next(node for node in document.nodes if node.attrs.get('role') == 'alert')
    yes, no = document.find(tag='button')
    assert alert.text == value['error']
    assert alert.order < yes.order < document.find(tag='details')[0].order
    assert alert.attrs['id'] in yes.attrs['aria-describedby'].split()
    assert 'disabled' in yes.attrs and 'disabled' not in no.attrs
    assert '&lt;example&gt;' in page and not document.find(tag='example')


def test_missing_answer_or_empty_examples_also_cannot_be_approved():
    for examples in ([], [{'question': 'An exact question?', 'surface': 'web'}]):
        document = Document(serve.forms_page([proposal(examples=examples)], 'test-token'))
        assert 'disabled' in document.find(tag='button')[0].attrs
        assert 'disabled' not in document.find(tag='button')[1].attrs


def test_missing_question_fails_the_semantic_approval_gate_even_when_rendering_is_bypassed(ready):
    store, _path, waiting = ready
    value = waiting[0]
    matches = deepcopy(forms_night.coverage_for(store, value['id']))
    examples = deepcopy(forms_review.examples_for(store, value['id']))
    for example in [*matches, *examples]:
        example.pop('question', None)
    with pytest.raises(forms.Refused, match='question'):
        forms_review.check_examples(value, examples, matches)


def test_palette_hat_numbers_card_order_and_only_yes_no_choices_stay():
    first, second = proposal('F-92'), proposal('F-90')
    page = serve.forms_page([first, second], 'test-token')
    document = Document(page)
    assert [node.attrs['aria-labelledby'] for node in document.find(tag='article')] == ['form-F-92', 'form-F-90']
    assert [node.text for node in document.find(tag='button')] == ['Yes', 'No', 'Yes', 'No']
    assert not document.find(tag='textarea') and not any('contenteditable' in node.attrs for node in document.nodes)
    assert all(node.attrs.get('type') == 'hidden' for node in document.find(tag='input'))
    assert document.find(tag='img', cls='hat') and '--lapis:#243F86' in page and '--sand:#CDB38B' in page
    assert 'approved answer' not in page.lower()
