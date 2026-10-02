"""Pattern, meaning, and reading-level vetoes for the night pass."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from nucleus import forms, forms_patterns as patterns, forms_night as night
from nucleus.model import ModelReply
from test_forms_night import KINDS, candidate, copy, history, miss, model_reply, painted, picture, run


def checked_form(**changes):
    return {'number': 'F-1', 'author': 'test', 'date': '2026-10-01', 'status': 'proposed', **candidate(**changes)}


@pytest.mark.parametrize('when', [
    {'answer': 'aligned'}, {'record_count': {'min': 2}}, {'word_count': 2},
    {'kinds_present': ['supports']}, {'kinds_absent': ['rejects']},
    {'kinds_present': ['supports'], 'kinds_absent': ['rejects']},
    {'missing_links': False},
])
def test_counts_single_positive_kind_absences_and_false_missing_are_not_patterns(when):
    assert patterns.check(checked_form(when=when), KINDS) == patterns.NO_PATTERN


@pytest.mark.parametrize('kind', sorted(patterns.PUSHING_KINDS))
def test_each_user_named_opposing_kind_establishes_pattern_eligibility(kind):
    assert patterns.pattern_reason({'kinds_present': [kind]}) is None


def test_two_distinct_present_kinds_or_missing_links_establish_eligibility():
    assert patterns.pattern_reason({'kinds_present': ['supports', 'requires']}) is None
    assert patterns.pattern_reason({'missing_links': True}) is None
    assert patterns.check(checked_form(when={'kinds_present': ['supports', 'supports']}), KINDS) == patterns.NO_PATTERN


@pytest.mark.parametrize('sentence', [
    'Your rows list {count} {kind} relationships for {word}.',
    'For {word}, {count} rows use the relationship {kind}.',
    'Your screen connects {word} with {count} rejects rows.',
    'The rows for {word} include both supports and requires relationships.',
    'For {word}, the most frequent displayed relationship is {strongest_kind}.',
    'These rows span {word_count} displayed words, beginning with {word}.',
    '{word} rejects 3 things.',
])
def test_count_and_middle_word_inventory_is_refused_even_with_eligible_conditions(sentence):
    assert patterns.check(checked_form(sentence=sentence), KINDS) == patterns.RESTATEMENT


def test_all_twelve_actual_slice3_sentences_are_now_refused():
    report = json.loads((Path(__file__).parents[1] / 'docs/forms-slice-3-first-night.json').read_text())
    kinds = sorted({k for r in report['results'] for k in r['form']['when'].get('kinds_present', [])} | set(KINDS))
    reasons = [patterns.check(r['form'], kinds) for r in report['results']]
    assert reasons.count(patterns.NO_PATTERN) == 11
    assert reasons.count(patterns.RESTATEMENT) == 1


def test_obvious_restatement_never_reaches_meaning_reviewer(copy):
    miss(copy)
    def writer(prompt, *, schema):
        assert schema == night.SCHEMA
        return ModelReply('test', 'writer', json.dumps({'forms': [candidate(when={'kinds_present': ['rejects']}, sentence='For {word}, {count} rows use {kind}.')]}))
    result = night.night(copy.path, practice=False, model_call=writer)
    assert result['refused'] == 1
    assert result['results'][0]['reason'] == patterns.RESTATEMENT
    assert result['meaning_reviews'] == []


def reviewing(verdict, reason, *, value=None, reading_grade=3, one_sentence=True):
    value = value or candidate()
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return ModelReply('test', 'writer', json.dumps({'forms': [value]}))
        assert schema == patterns.REVIEW_SCHEMA
        batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
        assert batch[0]['form']['sentence'] == value['sentence']
        return ModelReply('test', 'reviewer', json.dumps({'reviews': [
            {'number': batch[0]['form']['number'], 'verdict': verdict, 'reason': reason, 'reading_grade': reading_grade, 'one_sentence': one_sentence}]}))
    return call


@pytest.mark.parametrize('sentence', [
    'This means {word} has a trio of rejects links.',
    'For {word}, rejecting things is meaningful because it is a pattern.',
    'The total of {kind} relations for {word} is {count}; this is important.',
])
def test_reworded_counts_and_vague_filler_need_real_row_quotes(copy, sentence):
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('restates_rows', 'Only rephrases labels.',
        value=candidate(when={'kinds_present': ['rejects']}, sentence=sentence)))
    assert (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['reason'] == patterns.NEEDS_QUOTES
    assert copy.form_proposals()[0]['status'] == 'rejected'
    assert result['results'][0]['form']['status'] == 'rejected'
    assert result['results'][0]['payload']['status'] == 'proposed'
    assert result['meaning_reviews'] == []


def test_explanation_is_not_approved_by_a_favorable_review(copy):
    history(copy)
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('explains_pattern', 'Joins two real row contents in simple words.'))
    assert result['proposed'] == 1
    form = copy.form_proposals()[0]['form']
    assert form['status'] == 'proposed'
    assert forms.fill(form, night.screen_from_picture(picture(), KINDS), kinds=KINDS) is None
    assert forms.load(forms.FORMS_PATH) == []


def test_direction_reversal_is_refused_and_explanation_retained(copy):
    history(copy)
    miss(copy)
    reason = 'The row means FLOW rejects a record, not that FLOW is rejected.'
    result = night.night(copy.path, practice=False, model_call=reviewing('unsupported_meaning', reason,
        value=candidate(sentence='“{quote:depends on}” depends on {word} and “{quote:rejects}” rejects it.')))
    assert result['refused'] == 1
    assert result['results'][0]['reason'] == 'unsupported pattern meaning: ' + reason


def test_missing_links_form_fires_only_for_real_missing_snapshot(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        qid = painted(copy, word)
        value = picture(word); value['missing'] = ['MOMENTUM']; value['words'].append({'word': 'MOMENTUM'})
        copy.save_form_miss(qid, value, 'missing links')
    proposal = candidate(when={'missing_links': True, 'kinds_present': ['depends on', 'rejects']})
    result = run(copy, [proposal])
    assert result['proposed'] == 1
    form = result['results'][0]['form']
    assert forms.preview(form, night.screen_from_picture(value, KINDS), kinds=KINDS)
    value['missing'] = []
    assert forms.preview(form, night.screen_from_picture(value, KINDS), kinds=KINDS) is None


def test_two_kinds_form_needs_both_and_preserves_all_part_origins(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        qid = painted(copy, word)
        value = picture(word); value['records'][0]['kind'] = 'supports'; value['records'][1]['kind'] = 'requires'
        copy.save_form_miss(qid, value, 'no form fits')
    proposal = candidate(when={'kinds_present': ['supports', 'requires'], 'word_count': {'min': 1}},
        sentence='{word} supports “{quote:supports}” and requires “{quote:requires}”.')
    result = run(copy, [proposal])
    assert result['proposed'] == 1
    example = result['results'][0]['examples'][0]
    assert ''.join(p['text'] for p in example['parts']) == example['text']
    value['records'].pop()
    assert forms.preview(result['results'][0]['form'], night.screen_from_picture(value, KINDS), kinds=KINDS) is None


@pytest.mark.parametrize('reviews', [None, [], [
    {'number': 'F-1', 'verdict': 'approved', 'reason': 'yes'}], [
    {'number': 'F-99', 'verdict': 'explains_pattern', 'reason': 'wrong number'}], [
    {'number': 'F-1', 'verdict': 'explains_pattern', 'reason': ''}], [
    {'number': 'F-1', 'verdict': 'explains_pattern', 'reason': 'ok'},
    {'number': 'F-1', 'verdict': 'explains_pattern', 'reason': 'duplicate'}], 'timeout', 'malformed JSON'])
def test_incomplete_invalid_or_failed_review_fails_closed_and_retries(copy, reviews):
    history(copy)
    miss(copy)
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return model_reply([candidate()])(prompt, schema=schema)
        if reviews == 'timeout':
            raise TimeoutError('test review timeout')
        value = ([{'reading_grade': 3, 'one_sentence': True, **item} for item in reviews]
                 if isinstance(reviews, list) else reviews)
        text = 'not JSON' if reviews == 'malformed JSON' else json.dumps({'reviews': value})
        return ModelReply('test', 'reviewer', text)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['status'] == 'failed'
    assert copy.form_proposals() == []
    assert not result['meaning_reviews'][0]['ok']
    assert copy.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 2
    assert run(copy)['proposed'] == 1


def test_old_inventory_proposal_rejected_once_without_erasing_original(copy):
    old = checked_form(when={'kinds_present': ['supports']}, sentence='{word} supports {count} things.')
    pid = copy.save_form_proposal(old)
    before = copy.form_proposals()[0]['payload']
    result = run(copy, [])
    assert result['prior_proposals_refused'] == [{'proposal_id': pid, 'number': 'F-1', 'reason': patterns.NO_PATTERN}]
    after = copy.form_proposals()[0]
    assert after['payload'] == before
    assert after['status'] == 'rejected'
    assert run(copy, [])['prior_proposals_refused'] == []


def test_failed_review_does_not_partially_reject_previous_proposals(copy):
    history(copy)
    miss(copy)
    pid = copy.save_form_proposal(checked_form(when={'kinds_present': ['supports']}, sentence='{word} supports {count} things.'))
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return model_reply([candidate()])(prompt, schema=schema)
        raise TimeoutError('test failure')
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['status'] == 'failed'
    assert copy.form_proposals()[0]['status'] == 'proposed'
    assert copy.connection.execute('SELECT count(*) FROM form_night_rechecks').fetchone()[0] == 0
    result = run(copy)
    assert result['prior_proposals_refused'][0]['proposal_id'] == pid


def test_old_successful_inputs_are_revisited_once_for_new_policy(copy):
    miss(copy)
    inputs = night.collect(copy, KINDS, False)
    old_inputs = deepcopy(inputs)
    for item in old_inputs:
        item['key'] = item['key'].removeprefix(patterns.POLICY + ':')
    old_bytes = json.dumps(old_inputs)
    copy.connection.execute("INSERT INTO form_night_runs(id,started,status,inputs_json) VALUES ('old',1,'completed',?)", (old_bytes,))
    copy.connection.commit()
    assert run(copy)['inputs'] == 1
    assert run(copy)['inputs'] == 0
    assert copy.connection.execute("SELECT inputs_json FROM form_night_runs WHERE id='old'").fetchone()[0] == old_bytes


@pytest.mark.parametrize('grade,one_sentence,reason', [
    (6, True, 'reading level above fifth grade: 6'),
    (5, False, 'not one plain sentence'),
])
def test_reading_level_and_one_sentence_veto_favorable_meaning(copy, grade, one_sentence, reason):
    history(copy)
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('explains_pattern', 'Review result.',
        reading_grade=grade, one_sentence=one_sentence))
    assert (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['reason'].startswith(reason)
    assert result['results'][0]['examples']


def test_fifth_grade_is_allowed_but_never_approved(copy):
    history(copy)
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('explains_pattern', 'Plain words.', reading_grade=5))
    assert result['proposed'] == 1
    assert result['results'][0]['form']['status'] == 'proposed'


@pytest.mark.parametrize('grade', [True, '5', 0, 13, None])
def test_invalid_reading_grade_fails_closed(copy, grade):
    history(copy)
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('explains_pattern', 'Plain words.', reading_grade=grade))
    assert result['status'] == 'failed'
    assert copy.form_proposals() == []


def test_reviewer_sees_every_distinct_fill_while_saved_examples_stay_at_three(copy):
    for word in ['FLOW', 'LIFT', 'MOMENTUM', 'VALUE']:
        miss(copy, word)
    def call(prompt, *, schema):
        if schema == patterns.REVIEW_SCHEMA:
            batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
            assert len(batch[0]['examples']) == 4
            assert any(e['text'].startswith('VALUE ') for e in batch[0]['examples'])
        return model_reply([candidate()])(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['proposed'] == 1
    assert len(result['results'][0]['examples']) == 3


@pytest.mark.parametrize('one_sentence', ['true', 1, None])
def test_invalid_sentence_verdict_fails_closed(copy, one_sentence):
    history(copy)
    miss(copy)
    result = night.night(copy.path, practice=False, model_call=reviewing('explains_pattern', 'Plain words.', one_sentence=one_sentence))
    assert result['status'] == 'failed'
    assert copy.form_proposals() == []
