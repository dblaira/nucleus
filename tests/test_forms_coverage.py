"""Measure different fitting questions, not repeat answers or sampled examples."""
from copy import deepcopy
import json

import pytest

from nucleus import forms, forms_night as night, forms_patterns as patterns, forms_review as review, serve
from nucleus.model import ModelReply
from test_forms_night import KINDS, candidate, copy, history, miss, model_reply, painted, picture, run


@pytest.mark.parametrize('field', ['record_count', 'word_count'])
@pytest.mark.parametrize('count', [1, 15, {'min': 1, 'max': 1}, {'min': 15, 'max': 15}])
def test_exact_counts_refused(copy, field, count):
    history(copy); miss(copy)
    value = candidate(when={**candidate()['when'], field: count})
    result = run(copy, [value])
    assert (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['reason'] == 'exact counts refused'
    assert result['results'][0]['raw'] == value
    assert result['meaning_reviews'] == []


@pytest.mark.parametrize('count', [{'max': 15}, {'max': 1}])
def test_maximum_only_is_not_a_minimum_or_range(copy, count):
    miss(copy)
    result = run(copy, [candidate(when={**candidate()['when'], 'record_count': count})])
    assert result['results'][0]['reason'] == 'counts must be minimums or ranges'


@pytest.mark.parametrize('counts', [
    {'record_count': {'min': 2}, 'word_count': {'min': 1}},
    {'record_count': {'min': 2, 'max': 8}, 'word_count': {'min': 1, 'max': 3}},
])
def test_minimums_and_ranges_fit_three_answers_for_two_words(copy, counts):
    qids = [miss(copy, word) for word in ['FLOW', 'FLOW', 'LIFT']]
    copy.connection.execute('UPDATE questions SET question=? WHERE id=?', ('Why does FLOW matter?', qids[1]))
    copy.connection.commit()
    result = run(copy, [candidate(when={**candidate()['when'], **counts})])
    saved = result['results'][0]
    assert (result['proposed'], saved['fit_count'], saved['fit_word_count']) == (1, 3, 2)
    assert {m['question_id'] for m in night.coverage_for(copy, saved['proposal_id'])} == set(qids)
    assert [e['screen']['words'][0] for e in saved['examples']] == ['FLOW', 'LIFT']
    screen = night.screen_from_picture(picture(), KINDS)
    grown = forms.Screen(screen.answer, screen.words, screen.rows + (forms.Row('FLOW', 'r3', 'supports', 'Third quote'),))
    assert forms.preview(saved['form'], grown, kinds=KINDS) is not None
    assert forms.fill(saved['form'], grown, kinds=KINDS) is None


@pytest.mark.parametrize('words', [[], ['FLOW'], ['FLOW', 'LIFT'], ['FLOW', 'FLOW', 'FLOW']])
def test_too_few_answers_refused(copy, words):
    for word in words:
        miss(copy, word)
    # An unfinished miss triggers the writer but is never counted as a past painted answer.
    qid = copy.new_question('An unfinished question', 'web')
    copy.save_form_miss(qid, picture('VALUE'), 'pending')
    result = run(copy)
    row = result['results'][0]
    assert result['proposed'] == 0
    assert row['reason'] == 'fits too few answers'
    assert row['fit_count'] == len(set(words))
    assert row['fit_word_count'] == len(set(words))
    assert result['meaning_reviews'] == []
    assert copy.form_proposals()[0]['status'] == 'rejected'


def test_multiple_sources_and_extra_screen_words_cannot_inflate_coverage(copy):
    qid = miss(copy)
    value = picture(); value['words'].extend([{'word': 'LIFT'}, {'word': 'VALUE'}])
    for _ in range(3):
        copy.save_form_miss(qid, value, 'another miss for the same answer')
    copy.save_explanation(qid, 'Old text', None, 'test', 'fixture', 1)
    copy.thumb_explanation(qid, False)
    result = run(copy, bootstrap=True)
    assert result['inputs'] == 6  # Four misses, one thumb-down, one historical answer.
    row = result['results'][0]
    assert (row['fit_count'], row['fit_word_count']) == (1, 1)
    assert row['reason'] == 'fits too few answers'


def test_model_answers_and_failed_answers_are_not_painted_history(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        qid = miss(copy, word)
        copy.connection.execute('DELETE FROM steps WHERE question_id=?', (qid,))
    qid = painted(copy, 'WORK')
    copy.connection.execute("UPDATE answers SET status='stopped' WHERE question_id=?", (qid,))
    copy.connection.commit()
    result = run(copy)
    assert result['results'][0]['fit_count'] == 0
    assert result['results'][0]['reason'] == 'fits too few answers'


def test_coverage_uses_consumed_history_and_review_checks_every_distinct_fill(copy):
    for word in ['FLOW', 'FLOW', 'LIFT', 'VALUE', 'WORK']:
        miss(copy, word)
    first = run(copy)
    assert first['results'][0]['fit_count'] == 4
    assert len(first['results'][0]['examples']) == 3
    miss(copy, 'MOMENTUM')
    reverse = candidate(when={**candidate()['when'], 'record_count': {'min': 2}})
    def call(prompt, *, schema):
        if schema == patterns.REVIEW_SCHEMA:
            batch = json.loads(prompt.split('\nCandidates:\n')[1])
            assert len(batch[0]['examples']) == 5  # All five words, one fill each.
        return model_reply([reverse])(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['inputs'] == 1
    assert result['results'][0]['fit_count'] == 5
    assert result['results'][0]['fit_word_count'] == 5


def narrow(copy, number='F-25'):
    form = {'number': number, 'status': 'proposed', 'author': 'test', 'date': '2026-10-02',
            **candidate(when={**candidate()['when'], 'record_count': 2, 'word_count': 1})}
    return copy.save_form_proposal(form), form


def test_widening_keeps_sentence_uses_new_number_and_is_not_a_repeat(copy):
    history(copy)
    pid, original = narrow(copy)
    seen_schemas = []
    def reviewer(prompt, *, schema):
        seen_schemas.append(schema)
        assert schema == patterns.REVIEW_SCHEMA  # No fabricated model writer call.
        return model_reply([])(prompt, schema=schema)
    result = night.night(copy.path, practice=False, widen=('F-25',), model_call=reviewer)
    row = result['results'][0]
    assert (result['proposed'], result['refused']) == (1, 0)
    assert row['form']['number'] == 'F-26'
    assert row['form']['sentence'] == original['sentence']
    assert row['form']['when'] == {**original['when'], 'record_count': {'min': 2}, 'word_count': {'min': 1}}
    assert row['form']['status'] == 'proposed'
    assert row['form']['author'] == 'program/widen-counts'
    assert night.signature(row['form']) != night.signature(original)
    assert seen_schemas == [patterns.REVIEW_SCHEMA]
    old = next(p for p in copy.form_proposals() if p['id'] == pid)
    assert old['payload'] == original and old['status'] == 'rejected'
    assert old['reason'] == 'fit one screen only'
    assert forms.load(forms.FORMS_PATH) == []


def test_widened_form_still_refused_when_only_one_word_fits(copy):
    for _ in range(5): painted(copy)
    _, original = narrow(copy)
    result = night.night(copy.path, practice=False, widen=('F-25',), model_call=lambda *a, **kw: pytest.fail('too few words never reaches reviewer'))
    row = result['results'][0]
    assert (row['fit_count'], row['fit_word_count']) == (1, 1)
    assert row['reason'] == 'fits too few answers'
    assert row['reason'] != 'same form'
    assert result['prior_proposals_refused'][0]['reason'] == 'fit one screen only'
    assert copy.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0


def test_failed_widen_review_preserves_original_until_success(copy):
    history(copy)
    pid, original = narrow(copy)
    def fail(*a, **kw): raise TimeoutError('test failure')
    result = night.night(copy.path, practice=False, widen=('F-25',), model_call=fail)
    assert result['status'] == 'failed'
    assert len(copy.form_proposals()) == 1
    assert copy.form_proposals()[0]['payload'] == original
    assert copy.form_proposals()[0]['status'] == 'proposed'
    assert copy.connection.execute('SELECT count(*) FROM form_night_coverage').fetchone()[0] == 0


def test_review_lists_largest_fit_first_with_different_words_and_keeps_yes_no(copy):
    for index, word in enumerate(['FLOW', 'LIFT', 'FLOW']):
        qid = miss(copy, word)
        if index == 2:
            copy.connection.execute('UPDATE questions SET question=? WHERE id=?', ('Why does FLOW matter?', qid))
        value = picture(word); value['records'].append({'link_word': word, 'leaf': 'r3', 'kind': 'supports', 'quote': 'Third quote'})
        copy.save_form_miss(qid, value, 'snapshot')
    for word in ['VALUE', 'WORK']: miss(copy, word)
    limited = candidate(when={**candidate()['when'], 'kinds_present': ['depends on', 'rejects', 'supports']})
    result = run(copy, [limited, candidate()])
    assert result['proposed'] == 2
    queue = review.pending(copy, forms.FORMS_PATH)
    assert [(p['number'], p['fit_count']) for p in queue] == [('F-2', 5), ('F-1', 3)]
    assert [e['screen']['words'][0] for e in queue[0]['examples']] == ['FLOW', 'LIFT', 'VALUE']
    assert len(queue[1]['examples']) == 2
    page = serve.forms_page(queue, 'test')
    assert page.index('form-F-2') < page.index('form-F-1')
    assert 'fits 5 of your questions · 0 practice questions' in page and 'fits 3 of your questions · 0 practice questions' in page
    assert page.count('>Yes</button>') == page.count('>No</button>') == 2
    assert forms.load(forms.FORMS_PATH) == []


def test_changed_coverage_cannot_be_approved_from_an_old_page(copy):
    history(copy); miss(copy)
    result = run(copy)
    p = review.pending(copy, forms.FORMS_PATH)[0]
    matches = night.coverage_for(copy, p['id'])
    copy.connection.execute('UPDATE form_night_coverage SET matches_json=? WHERE proposal_id=?',
                            (json.dumps(matches[:1]), p['id']))
    copy.connection.commit()
    with pytest.raises(review.Conflict, match='changed'):
        review.decide(copy.path, forms.FORMS_PATH, p['id'], 'yes', p['version'])
    fresh = review.pending(copy, forms.FORMS_PATH)[0]
    assert fresh['error'] == 'fits too few answers'
    with pytest.raises(forms.Refused, match='fits too few answers'):
        review.decide(copy.path, forms.FORMS_PATH, fresh['id'], 'yes', fresh['version'])
    assert forms.load(forms.FORMS_PATH) == []


def test_writer_schema_offers_only_minimum_or_range_counts():
    schema = json.loads(night.SCHEMA.read_text())
    props = schema['properties']['forms']['items']['properties']['when']['properties']
    for name in ['record_count', 'word_count']:
        alternatives = props[name]['anyOf']
        assert {v['type'] for v in alternatives} == {'null', 'object'}
        assert [v['required'] for v in alternatives if v['type'] == 'object'] == [['min'], ['min', 'max']]


def test_a_repeated_question_counts_once_even_with_new_answer_ids(copy):
    for _ in range(43):
        miss(copy, 'FLOW')
    miss(copy, 'LIFT')
    result = run(copy)
    row = result['results'][0]
    assert row['fit_count'] == 2 and row['fit_word_count'] == 2
    assert row['reason'] == 'fits too few answers'
    assert len(night.coverage_for(copy, row['proposal_id'])) == 44


def test_question_normalization_and_different_fills_keep_semantic_audit(copy):
    qids = [miss(copy, word) for word in ['FLOW', 'LIFT', 'VALUE', 'WORK']]
    for qid, text in zip(qids[:2], ['  My question? ', 'MY\nQUESTION?']):
        copy.connection.execute('UPDATE questions SET question=? WHERE id=?', (text, qid))
    copy.connection.commit()
    def call(prompt, *, schema):
        if schema == patterns.REVIEW_SCHEMA:
            batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
            assert len(batch[0]['examples']) == 4  # Different fills survive question dedup.
        return model_reply([candidate()])(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    row = result['results'][0]
    assert row['fit_count'] == 3 and row['fit_word_count'] == 3
    assert result['proposed'] == 1
    examples = row['examples']
    assert len({night.question_key(e) for e in examples}) == len(examples) == 3


def test_only_fitting_answers_participate_in_question_dedup(copy):
    qid = miss(copy, 'FLOW')
    copy.connection.execute('UPDATE answers SET status=? WHERE question_id=?', ('stopped', qid))
    history(copy); miss(copy, 'LIFT')
    result = run(copy)
    assert result['results'][0]['fit_count'] == 3
    assert result['proposed'] == 1


def test_bound_word_coverage_comes_from_the_filled_source():
    examples = [
        {'surface': 'web', 'question_id': str(i), 'question': f'Different question {i}',
         'screen': {'words': ['FIRST', word]},
         'parts': [{'source': 'screen.words[1]', 'text': word}]}
        for i, word in enumerate(['FLOW', 'LIFT', 'FLOW'])
    ]
    assert night.fit_counts(examples) == (3, 2)
    assert [night.bound_word(e) for e in night.diverse_examples(examples)] == ['FLOW', 'LIFT']


def test_repeat_of_same_question_with_new_word_cannot_inflate_word_coverage():
    examples = [
        {'surface': 'web', 'question_id': str(i), 'question': question, 'screen': {'words': [word]},
         'parts': [{'source': 'screen.words[0]', 'text': word}]}
        for i, (question, word) in enumerate([
            ('Why don’t I trust this app?', 'FLOW'),
            (" WHY DON'T I TRUST THIS APP? ", 'LIFT'),
            ('Different question two', 'FLOW'),
            ('Different question three', 'FLOW'),
        ])
    ]
    assert night.fit_counts(examples) == (3, 1)
    assert night.coverage_reason(examples) == 'fits too few answers'
    assert len(night.distinct_fills([{**e, 'text': e['parts'][0]['text']} for e in examples])) == 2
