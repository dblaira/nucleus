"""Night relevance vetoes bind to exact question/source contexts, never approval."""
from copy import deepcopy
from dataclasses import asdict
import json

import pytest

from nucleus import forms, forms_night as night, forms_patterns as patterns, forms_review
from nucleus.model import ModelReply
from test_forms_night import KINDS, candidate, copy, history, miss, picture, run


def form(number='F-80'):
    return {'number': number, 'status': 'proposed', 'author': 'portable fixture',
            'date': '2026-10-02', **candidate()}


def example(question='What is FLOW?', word='FLOW'):
    screen = night.screen_from_picture(picture(word), KINDS)
    filled = forms.preview(form(), screen, kinds=KINDS)
    return {'question_id': 'fixture-' + word, 'question': question, 'surface': 'web',
            'screen': asdict(screen), 'text': filled.text, 'parts': [asdict(part) for part in filled.parts]}


def reviewer(verdict='explains_pattern', reason='Exact sources apply to each actual question.', *, fail=False):
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return ModelReply('test', 'writer', json.dumps({'forms': []}))
        assert schema == patterns.REVIEW_SCHEMA
        if fail:
            raise TimeoutError('fixture question review failed')
        batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
        return ModelReply('test', 'relevance reviewer', json.dumps({'reviews': [
            {'number': entry['form']['number'], 'verdict': verdict, 'reason': reason,
             'reading_grade': 3, 'one_sentence': True} for entry in batch]}))
    return call


def test_same_filled_sentence_keeps_every_distinct_question_and_source_context():
    first = example()
    second = example('Why is the water flow low?')
    changed = deepcopy(first)
    changed['screen']['rows'][0]['quote'] = 'Another exact displayed quote'
    repeated = deepcopy(first)
    repeated['question_id'] = 'a second ask of the same context'
    patterns.mark_context_review(form(), repeated)
    assert first['text'] == second['text'] == changed['text']
    contexts = night.distinct_fills([first, second, changed, repeated])
    assert len(contexts) == 3
    assert [value['question'] for value in contexts] == [first['question'], second['question'], changed['question']]
    assert contexts[2]['screen']['rows'][0]['quote'] == 'Another exact displayed quote'


def test_question_fit_prompt_requires_relevance_but_never_source_style():
    value = example('I cannot claim why FLOW is a prerequisite?')
    value['screen']['rows'][0]['quote'] = 'You should not establish necessity.'
    prompt, batch = patterns.review_packets([{'form': form(), 'examples': [value]}])[0]
    assert value['question'] in prompt and value['screen']['rows'][0]['quote'] in prompt
    assert 'actual question' in prompt and 'different sense' in prompt
    assert 'Exact copying' in prompt and 'never sufficient' in prompt
    assert 'Never judge vocabulary or style in filled' in prompt
    assert batch[0]['literal_words'] == forms.literal_words(form()['sentence'])


def test_source_bound_receipt_never_changes_form_or_approves_it():
    proposed, value = form(), example()
    original = deepcopy(proposed)
    assert patterns.context_reason(proposed, value) == 'The question and answer need checking before Yes.'
    assert patterns.mark_context_review(proposed, value) is value
    assert patterns.context_reason(proposed, value) is None
    assert proposed == original and proposed['status'] == 'proposed'
    assert set(value[patterns.CONTEXT_FIELD]) == {'policy', 'digest'}
    assert len(value[patterns.CONTEXT_FIELD]['digest']) == 64


@pytest.mark.parametrize('field', ['question', 'form', 'screen', 'text', 'parts', 'policy', 'digest', 'extra_proof_field'])
def test_question_form_or_source_mutation_invalidates_the_receipt(field):
    proposed, value = form(), example()
    patterns.mark_context_review(proposed, value)
    if field == 'question':
        value['question'] += ' '
    elif field == 'form':
        proposed['when']['word_count'] = {'min': 1}
    elif field == 'screen':
        value['screen']['rows'][0]['quote'] = 'A different quote'
    elif field == 'text':
        value['text'] += ' '
    elif field == 'parts':
        value['parts'][0]['text'] += ' '
    else:
        value[patterns.CONTEXT_FIELD][field] = 'changed'
    assert patterns.context_reason(proposed, value) is not None


def test_receipt_annotation_and_ask_identity_do_not_change_exact_context_digest():
    proposed, value = form(), example()
    patterns.mark_context_review(proposed, value)
    before = deepcopy(value[patterns.CONTEXT_FIELD])
    value['question_id'] = 'same complete exact question/source asked again'
    patterns.mark_context_review(proposed, value)
    assert value[patterns.CONTEXT_FIELD] == before
    assert patterns.context_reason(proposed, value) is None


@pytest.mark.parametrize('question', [None, '', ' \n ', 3])
def test_missing_question_cannot_receive_a_source_receipt(question):
    value = example()
    value['question'] = question
    assert 'question' in patterns.context_reason(form(), value).lower()
    with pytest.raises(ValueError, match='question'):
        patterns.mark_context_review(form(), value)
    assert patterns.CONTEXT_FIELD not in value


def test_off_topic_verdict_is_an_explicit_refusal_before_any_stamp(copy):
    history(copy)
    miss(copy)
    def call(prompt, *, schema):
        if schema == night.SCHEMA:
            return ModelReply('test', 'writer', json.dumps({'forms': [candidate()]}))
        return reviewer('off_topic', 'The selected personal records do not describe the situation.')(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['status'] == 'completed' and (result['proposed'], result['refused']) == (0, 1)
    assert result['results'][0]['reason'] == 'does not answer the question: The selected personal records do not describe the situation.'
    proposed = copy.form_proposals()[0]
    assert proposed['status'] == 'rejected' and proposed['payload']['status'] == 'proposed'
    matches = night.coverage_for(copy, proposed['id'])
    assert matches and all(patterns.CONTEXT_FIELD not in value for value in matches)
    assert forms.load(forms.FORMS_PATH) == []


def test_old_pending_form_without_receipts_is_reviewed_and_payload_preserved(copy):
    history(copy)
    pid = copy.save_form_proposal(form())
    original = deepcopy(copy.form_proposals()[0])
    prompts = []
    def call(prompt, *, schema):
        prompts.append((prompt, schema))
        return reviewer()(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['status'] == 'completed'
    assert len(prompts) == 1 and prompts[0][1] == patterns.REVIEW_SCHEMA
    assert form()['number'] in prompts[0][0]
    after = copy.form_proposals()[0]
    assert after == original and after['id'] == pid and after['status'] == 'proposed'
    matches = night.coverage_for(copy, pid)
    assert len(matches) == 3 and all(patterns.context_reason(after['form'], value) is None for value in matches)
    assert forms_review.pending(copy, forms.FORMS_PATH)[0]['error'] is None


def test_current_old_receipts_are_reused_but_a_changed_question_is_reviewed(copy):
    qids = history(copy)
    pid = copy.save_form_proposal(form())
    result = night.night(copy.path, practice=False, model_call=reviewer())
    assert result['status'] == 'completed'
    def no_call(*_args, **_kwargs):
        raise AssertionError('current exact receipts must be reused')
    result = night.night(copy.path, practice=False, model_call=no_call)
    assert result['status'] == 'completed' and result['meaning_reviews'] == []
    copy.connection.execute('UPDATE questions SET question=? WHERE id=?', ('Where does FLOW apply now?', qids[0]))
    copy.connection.commit()
    result = night.night(copy.path, practice=False, model_call=reviewer())
    assert result['status'] == 'completed' and len(result['meaning_reviews']) == 1
    assert all(patterns.context_reason(form(), value) is None for value in night.coverage_for(copy, pid))


def test_failed_old_review_preserves_pending_payload_and_no_partial_receipts(copy):
    history(copy)
    pid = copy.save_form_proposal(form())
    before = deepcopy(copy.form_proposals()[0])
    result = night.night(copy.path, practice=False, model_call=reviewer(fail=True))
    assert result['status'] == 'failed' and copy.form_proposals()[0] == before
    assert night.coverage_for(copy, pid) == []
    assert copy.connection.execute('SELECT count(*) FROM form_coverage_checks').fetchone()[0] == 0
    assert forms_review.pending(copy, forms.FORMS_PATH)[0]['error'] is not None


def test_old_off_topic_review_keeps_original_payload_and_reports_reason(copy):
    history(copy)
    pid = copy.save_form_proposal(form())
    original = deepcopy(copy.form_proposals()[0]['payload'])
    result = night.night(copy.path, practice=False, model_call=reviewer('off_topic', 'Wrong dictionary sense for a question.'))
    assert result['status'] == 'completed'
    assert result['prior_proposals_refused'] == [{'proposal_id': pid, 'number': 'F-80',
        'reason': 'does not answer the question: Wrong dictionary sense for a question.'}]
    assert copy.form_proposals()[0]['payload'] == original
    assert copy.form_proposals()[0]['status'] == 'rejected'
    assert all(patterns.CONTEXT_FIELD not in value for value in night.coverage_for(copy, pid))


@pytest.mark.parametrize('verdict', ['approved', 'unknown', None])
def test_unknown_review_verdict_never_passes_or_stamps_pending_context(copy, verdict):
    history(copy)
    pid = copy.save_form_proposal(form())
    before = deepcopy(copy.form_proposals()[0])
    result = night.night(copy.path, practice=False, model_call=reviewer(verdict))
    assert result['status'] == 'failed' and copy.form_proposals()[0] == before
    assert night.coverage_for(copy, pid) == []


def test_more_than_twelve_pending_forms_are_bounded_into_complete_review_packets():
    candidates = [{'form': form('F-' + str(number)), 'examples': [example()]} for number in range(1, 15)]
    packets = patterns.review_packets(candidates)
    assert [len(batch) for _prompt, batch in packets] == [12, 2]
    assert [entry['form']['number'] for _prompt, batch in packets for entry in batch] == [c['form']['number'] for c in candidates]
    assert all(len(prompt) <= patterns.REVIEW_PROMPT_LIMIT - patterns.REVIEW_PROMPT_OVERHEAD for prompt, _batch in packets)


@pytest.mark.parametrize('second_result', ['failure', 'off_topic'])
def test_a_later_semantic_packet_cannot_leave_partial_source_receipts(copy, monkeypatch, second_result):
    history(copy)
    pid = copy.save_form_proposal(form())
    matches = night.matching_answers(form(), night.past_answers(copy, KINDS), KINDS)
    candidate_value = {'form': form(), 'examples': night.distinct_fills(matches)}
    single_limits = [len(patterns.review_packets([{'form': form(), 'examples': [value]}])[0][0])
                     for value in candidate_value['examples']]
    monkeypatch.setattr(patterns, 'REVIEW_PROMPT_LIMIT', max(single_limits) + patterns.REVIEW_PROMPT_OVERHEAD)
    assert len(patterns.review_packets([candidate_value])) == 3
    calls = []
    def call(prompt, *, schema):
        assert schema == patterns.REVIEW_SCHEMA
        calls.append(prompt)
        if len(calls) == 2 and second_result == 'failure':
            raise TimeoutError('fixture second packet failed')
        verdict = 'off_topic' if len(calls) == 2 else 'explains_pattern'
        return reviewer(verdict, 'The second question uses an unrelated meaning.')(prompt, schema=schema)
    result = night.night(copy.path, practice=False, model_call=call)
    if second_result == 'failure':
        assert result['status'] == 'failed'
        assert [value['ok'] for value in result['meaning_reviews']] == [True, False]
        assert copy.form_proposals()[0]['status'] == 'proposed'
    else:
        assert result['status'] == 'completed' and len(result['meaning_reviews']) == 3
        assert result['prior_proposals_refused'][0]['reason'].startswith('does not answer the question:')
        assert copy.form_proposals()[0]['status'] == 'rejected'
    assert all(patterns.CONTEXT_FIELD not in value for value in night.coverage_for(copy, pid))


def test_human_yes_and_no_remain_authoritative_during_pending_rechecks(copy):
    history(copy)
    miss(copy)
    result = run(copy)
    assert result['proposed'] == 1
    waiting = forms_review.pending(copy, forms.FORMS_PATH)[0]
    forms_review.decide(copy.path, forms.FORMS_PATH, waiting['id'], 'yes', waiting['version'])
    approved_before = deepcopy(copy.form_proposals()[0])
    declined = copy.save_form_proposal(form('F-90'), 'Adam said no on /forms.')
    declined_before = next(p for p in copy.form_proposals() if p['id'] == declined)
    result = night.night(copy.path, practice=False, model_call=reviewer())
    assert result['status'] == 'completed' and result['meaning_reviews'] == []
    by_id = {p['id']: p for p in copy.form_proposals()}
    assert by_id[waiting['id']] == approved_before
    assert by_id[declined] == declined_before
    assert forms.load(forms.FORMS_PATH)[0]['status'] == 'approved'
