"""Night-only middle proposals read exact saved screens and count different questions."""
import json
import sys

import pytest

from nucleus import forms, forms_middle, forms_night as night, forms_patterns as patterns
from test_forms_night import KINDS, candidate, copy, model_reply


def middle_candidate(**changes):
    value = {'when': {'answer': 'not_sure', 'missing_why': True,
                      'record_count': {'min': 1}, 'word_count': {'min': 1}},
             'sentence': forms_middle.HEADS[0] + forms_middle.TAILS['missing_why']}
    value.update(changes)
    return value


def saved_middle(store, word, question=None, *, answer='not_sure'):
    question = question or f'What does {word} show here?'
    qid = store.new_question(question, 'test')
    word_why = f'{word} matches this question, but the records do not show what happened.'
    record_why = f'This record supports {word} here, but the records do not show what happened.'
    payload = {'answer': answer, 'words': [{'word': word, 'why': word_why}],
               'records': [{'id': 'saved-r1', 'quote': 'The work feels clear', 'why': record_why}]}
    text = (f'Not sure.\n\n{word} — “Work feels clear”\n{word_why}'
            f'\n\n0.90 — “The work feels clear”\n{record_why}')
    store.save_answer(qid, 'answered', answer, text, json.dumps(payload), True, None)
    return qid


def run_middle(store, values=None):
    return night.night(store.path, bootstrap=True, middle_only=True,
                       model_call=model_reply(values or [middle_candidate()]))


def test_bootstrap_reads_saved_not_sure_screen_without_adding_links(copy):
    qids = {saved_middle(copy, word) for word in ['FLOW', 'LIFT', 'VALUE']}
    result = run_middle(copy)
    assert (result['status'], result['proposed'], result['refused']) == ('completed', 1, 0)
    assert result['usable_inputs'] == result['inputs'] == 3
    row = result['results'][0]
    assert (row['fit_count'], row['fit_word_count']) == (3, 3)
    assert {e['question_id'] for e in row['examples']} == qids
    assert len(row['examples']) == 3
    for example in row['examples']:
        assert example['screen']['answer'] == 'not_sure'
        assert all(r['kind'] is None for r in example['screen']['rows'])
        assert forms.preview(row['form'], night.restore_screen(example['screen']), kinds=KINDS).text == example['text']
        assert 'the records do not show what happened.' in example['text']
    assert copy.connection.execute('SELECT count(*) FROM links').fetchone()[0] == 0
    assert forms.load(forms.FORMS_PATH) == []
    assert all(p['status'] == 'proposed' for p in copy.form_proposals())
    assert forms.fill(row['form'], night.restore_screen(row['examples'][0]['screen']), kinds=KINDS) is None


@pytest.mark.parametrize('answer', ['aligned', 'dont_know', None])
def test_not_sure_forms_fire_only_on_not_sure(copy, answer):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        saved_middle(copy, word)
    when = {**middle_candidate()['when']}
    if answer is None:
        when.pop('answer')
    else:
        when['answer'] = answer
    result = run_middle(copy, [middle_candidate(when=when)])
    assert result['proposed'] == 0
    assert result['results'][0]['reason'] == 'middle-option forms fire only on not_sure'
    assert result['meaning_reviews'] == []


def test_middle_only_pass_retains_and_refuses_an_old_row_form(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        saved_middle(copy, word)
    result = run_middle(copy, [candidate()])
    assert result['proposed'] == 0
    assert result['results'][0]['raw'] == candidate()
    assert result['results'][0]['reason'] == 'middle-only pass requires a not_sure form with both halves'
    assert copy.form_proposals()[0]['status'] == 'rejected'


@pytest.mark.parametrize('sentence', [None, '{unknown_slot}', '{meaning'])
def test_malformed_middle_batch_is_refused_and_retained(copy, sentence):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        saved_middle(copy, word)
    raw = middle_candidate(sentence=sentence)
    result = run_middle(copy, [raw])
    assert result['status'] == 'completed'
    assert (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['raw'] == raw
    assert copy.form_proposals()[0]['status'] == 'rejected'


def test_repeated_question_cannot_qualify_a_middle_proposal(copy):
    for _ in range(43):
        saved_middle(copy, 'FLOW', 'What is FLOW?')
    saved_middle(copy, 'LIFT', 'What is LIFT?')
    result = run_middle(copy)
    row = result['results'][0]
    assert row['fit_count'] == 2 and row['fit_word_count'] == 2
    assert row['reason'] == 'fits too few answers'
    assert result['meaning_reviews'] == []
    assert len(night.coverage_for(copy, row['proposal_id'])) == 44


def test_middle_writer_and_reviewer_describe_scoped_exact_source_exception(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        saved_middle(copy, word)
    prompts = []
    def call(prompt, *, schema):
        prompts.append((schema, prompt))
        return model_reply([middle_candidate()])(prompt, schema=schema)
    result = night.night(copy.path, bootstrap=True, middle_only=True, model_call=call)
    assert result['proposed'] == 1
    writer = next(p for s, p in prompts if s == night.SCHEMA)
    reviewer = next(p for s, p in prompts if s == patterns.REVIEW_SCHEMA)
    assert 'ONLY forms requiring answer=not_sure' in writer
    assert 'Repeated questions count once' in writer
    assert 'whole safe source' in writer and 'never clips' in writer
    assert 'narrowly scoped middle-option rule' in reviewer
    assert 'No invented cause' in reviewer and 'joining frame' in reviewer
    assert patterns.POLICY == 'middle-question-v2'


def test_middle_schema_requires_nullable_missing_why():
    schema = json.loads(night.SCHEMA.read_text())
    when = schema['properties']['forms']['items']['properties']['when']
    assert 'missing_why' in when['required']
    assert when['properties']['missing_why'] == {'type': ['boolean', 'null']}


def test_cli_passes_middle_only_option(monkeypatch, capsys):
    seen = {}
    def capture(path, **options):
        seen.update(options)
        return {'status': 'completed'}
    monkeypatch.setattr(night, 'night', capture)
    monkeypatch.setattr(sys, 'argv', ['forms', 'night', '--bootstrap', '--middle-only', '--store', 'copy.sqlite3'])
    night.main()
    assert seen == {'bootstrap': True, 'widen': (), 'middle_only': True}
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'


def test_middle_only_cannot_widen_old_forms(copy):
    with pytest.raises(ValueError, match='cannot widen'):
        night.night(copy.path, middle_only=True, widen=('F-25',))


def test_unrelated_quotes_are_refused_even_when_three_questions_exist(copy):
    for word in ['FLOW','LIFT','VALUE']:
        qid=saved_middle(copy,word)
        copy.connection.execute('UPDATE answers SET text=replace(text,?,?) WHERE question_id=?',
                                ('Work feels clear','thinking momentum is not feeling momentum',qid))
    copy.connection.commit()
    result=run_middle(copy)
    assert result['proposed']==0
    assert result['results'][0]['reason']=='fits too few answers'
    assert result['results'][0]['fit_count']==0
    assert result['meaning_reviews']==[]
