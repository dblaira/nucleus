"""Behavior tests for the slice 3b rules, separate from earlier filler/day contracts."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from nucleus import forms, forms_patterns as patterns, forms_night as night
from nucleus.model import ModelReply
from test_forms_night import KINDS, candidate, copy, miss, model_reply, picture, run


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
    assert patterns.check(checked_form(when={'kinds_present': [kind]}), KINDS) is None


def test_two_distinct_present_kinds_or_missing_links_establish_eligibility():
    assert patterns.check(checked_form(when={'kinds_present': ['supports', 'requires']}), KINDS) is None
    assert patterns.check(checked_form(when={'missing_links': True}), KINDS) is None
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
        return ModelReply('test', 'writer', json.dumps({'forms': [candidate(sentence='For {word}, {count} rows use {kind}.')]}))
    result = night.night(copy.path, model_call=writer)
    assert result['refused'] == 1
    assert result['results'][0]['reason'] == patterns.RESTATEMENT
    assert result['meaning_reviews'] == []


def reviewing(verdict, reason, *, value=None):
    value = value or candidate()
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return ModelReply('test', 'writer', json.dumps({'forms': [value]}))
        assert schema == patterns.REVIEW_SCHEMA
        batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
        assert batch[0]['form']['sentence'] == value['sentence']
        return ModelReply('test', 'reviewer', json.dumps({'reviews': [
            {'number': batch[0]['form']['number'], 'verdict': verdict, 'reason': reason}]}))
    return call


@pytest.mark.parametrize('sentence', [
    'This means {word} has a trio of rejects links.',
    'For {word}, rejecting things is meaningful because it is a pattern.',
    'The total of {kind} relations for {word} is {count}; this is important.',
])
def test_reworded_counts_and_vague_filler_are_refused_by_separate_review(copy, sentence):
    miss(copy)
    reason = 'Only rephrases the labels or amount; no implication of the pattern.'
    result = night.night(copy.path, model_call=reviewing('restates_rows', reason, value=candidate(sentence=sentence)))
    assert (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['reason'] == patterns.RESTATEMENT + ': ' + reason
    assert copy.form_proposals()[0]['status'] == 'rejected'
    assert result['results'][0]['form']['status'] == 'rejected'
    assert result['results'][0]['payload']['status'] == 'proposed'
    assert result['results'][0]['examples']  # Retain evidence for this semantic refusal.
    assert 'restates_rows' in result['meaning_reviews'][0]['reply']


def test_explanation_is_not_approved_by_a_favorable_review(copy):
    miss(copy)
    result = night.night(copy.path, model_call=reviewing('explains_pattern', 'Exclusion bounds the scope of the picture.'))
    assert result['proposed'] == 1
    form = copy.form_proposals()[0]['form']
    assert form['status'] == 'proposed'
    assert forms.fill(form, night.screen_from_picture(picture(), KINDS), kinds=KINDS) is None
    assert forms.load(forms.FORMS_PATH) == []


def test_direction_reversal_is_refused_and_explanation_retained(copy):
    miss(copy)
    reason = 'The row means FLOW rejects a record, not that FLOW is rejected.'
    result = night.night(copy.path, model_call=reviewing('unsupported_meaning', reason,
        value=candidate(sentence='{word} faces rejection here, so its acceptance is in doubt.')))
    assert result['refused'] == 1
    assert result['results'][0]['reason'] == 'unsupported pattern meaning: ' + reason


def test_missing_links_form_fires_only_for_real_missing_snapshot(copy):
    qid = copy.new_question('What is FLOW?', 'test')
    value = picture(); value['missing'] = ['FLOW']; value['records'] = []
    copy.save_form_miss(qid, value, 'missing links')
    proposal = candidate(when={'missing_links': True}, sentence='The picture involving {word} is incomplete: a gap in evidence cannot establish a negative conclusion.')
    result = run(copy, [proposal])
    assert result['proposed'] == 1
    form = result['results'][0]['form']
    assert forms.preview(form, night.screen_from_picture(value, KINDS), kinds=KINDS)
    value['missing'] = []
    assert forms.preview(form, night.screen_from_picture(value, KINDS), kinds=KINDS) is None


def test_two_kinds_form_needs_both_and_preserves_all_part_origins(copy):
    qid = copy.new_question('What is FLOW?', 'test')
    value = picture(); value['records'][0]['kind'] = 'supports'; value['records'][1]['kind'] = 'requires'
    copy.save_form_miss(qid, value, 'no form fits')
    proposal = candidate(when={'kinds_present': ['supports', 'requires'], 'word_count': 1},
        sentence='For {word}, backing does not establish that its prerequisites are in place.')
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
    miss(copy)
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return model_reply([candidate()])(prompt, schema=schema)
        if reviews == 'timeout':
            raise TimeoutError('test review timeout')
        text = 'not JSON' if reviews == 'malformed JSON' else json.dumps({'reviews': reviews})
        return ModelReply('test', 'reviewer', text)
    result = night.night(copy.path, model_call=call)
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
    miss(copy)
    pid = copy.save_form_proposal(checked_form(when={'kinds_present': ['supports']}, sentence='{word} supports {count} things.'))
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return model_reply([candidate()])(prompt, schema=schema)
        raise TimeoutError('test failure')
    result = night.night(copy.path, model_call=call)
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


def test_review_contract_checks_condition_scope_and_preserves_direction():
    # The reviewer must reason about all matching screens, not rubber-stamp three examples.
    assert 'EVERY matching screen' in night.CONTRACT
    assert 'GUARANTEE for any matching screen' in patterns.REVIEW_CONTRACT
    assert "does not mean FLOW is rejected" in patterns.REVIEW_CONTRACT
    assert 'not that {word} specifically lacks them' in patterns.REVIEW_CONTRACT
    assert 'not instructions' in patterns.REVIEW_CONTRACT
