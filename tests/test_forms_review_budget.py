"""Every whole semantic-review example is checked within bounded prompt packets."""
from copy import deepcopy
import json

import pytest

from nucleus import forms, forms_middle, forms_patterns as patterns
from nucleus.model import ModelReply


class Audit:
    def __init__(self):
        self.calls = []

    def save_model_call(self, *args):
        self.calls.append(args)


def candidate(number='F-100', count=3, size=1000):
    form = dict(number=number, when={'answer': 'aligned', 'kinds_present': ['depends on', 'rejects']},
                sentence='{word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.',
                status='proposed', author='test only', date='2026-10-02')
    return {'form': form, 'examples': [
        {'id': number + ':' + str(i), 'text': 'Adam’s whole words “α” ' + str(i) + ':' + ('z' * size),
         'screen': {'rows': [{'word': 'FLOW', 'kind': 'depends on', 'record': 'r1', 'quote': 'No claim. You should not change this.'}]}}
        for i in range(count)]}


def batch(prompt):
    return json.loads(prompt.split('\nCandidates:\n', 1)[1])


def reply(prompt, *, verdict='explains_pattern', grade=3, one_sentence=True, reason='Exact sources joined.'):
    return ModelReply('test', 'packet-review', json.dumps({'reviews': [
        {'number': c['form']['number'], 'verdict': verdict, 'reason': reason,
         'reading_grade': grade, 'one_sentence': one_sentence} for c in batch(prompt)]}))


def one_example_packets(monkeypatch, value):
    one = {**value, 'examples': value['examples'][:1]}
    prompt = patterns.review_packets([one])[0][0]
    monkeypatch.setattr(patterns, 'REVIEW_PROMPT_LIMIT', len(prompt) + patterns.REVIEW_PROMPT_OVERHEAD)


def test_every_whole_example_is_reviewed_once_within_real_750k_cap():
    values = [candidate('F-100', count=3, size=200_000), candidate('F-101', count=3, size=200_000)]
    original = deepcopy(values)
    visited, prompts, audit = [], [], Audit()
    def call(prompt, *, schema):
        assert schema == patterns.REVIEW_SCHEMA
        assert len(prompt) + patterns.REVIEW_PROMPT_OVERHEAD <= 750_000
        prompts.append(prompt)
        packet = batch(prompt)
        assert len({c['form']['number'] for c in packet}) == len(packet)
        for current in packet:
            source = next(c for c in original if c['form']['number'] == current['form']['number'])
            assert current['form'] == source['form']
            assert current['literal_words'] == forms.literal_words(source['form']['sentence'])
            for example in current['examples']:
                assert example == next(e for e in source['examples'] if e['id'] == example['id'])
                visited.append(example['id'])
        return reply(prompt)
    decisions = patterns.review(audit, 'same-phase', values, model_call=call)
    assert len(prompts) > 1 and len(prompts) == len(audit.calls)
    assert visited == [e['id'] for c in original for e in c['examples']]
    assert len(set(visited)) == len(visited) and values == original
    assert set(decisions) == {'F-100', 'F-101'}
    assert all(receipt[0] == 'forms-night:same-phase:review' and receipt[-2:] == (True, None) for receipt in audit.calls)
    assert [receipt[3] for receipt in audit.calls] == prompts


def test_small_review_stays_one_complete_call_and_one_unchanged_decision():
    value, audit = candidate(count=2, size=10), Audit()
    expected = {'number': 'F-100', 'verdict': 'explains_pattern', 'reason': 'Exact sources joined.',
                'reading_grade': 3, 'one_sentence': True}
    result = patterns.review(audit, 'small', [value], model_call=lambda p, **_: reply(p))
    assert result == {'F-100': expected} and len(audit.calls) == 1
    assert batch(audit.calls[0][3])[0]['examples'] == value['examples']


@pytest.mark.parametrize('verdicts, expected', [
    (['explains_pattern', 'restates_rows', 'explains_pattern'], 'restates_rows'),
    (['restates_rows', 'unsupported_meaning', 'explains_pattern'], 'unsupported_meaning'),
    (['unsupported_meaning', 'explains_pattern', 'restates_rows'], 'unsupported_meaning'),
])
def test_strictest_verdict_highest_grade_and_all_sentence_checks_survive_chunks(monkeypatch, verdicts, expected):
    value = candidate()
    one_example_packets(monkeypatch, value)
    calls, audit = [], Audit()
    def call(prompt, *, schema):
        index = len(calls)
        calls.append(prompt)
        assert len(batch(prompt)[0]['examples']) == 1
        return reply(prompt, verdict=verdicts[index], grade=[3, 7, 4][index],
                     one_sentence=[True, False, True][index], reason='Whole example ' + str(index))
    result = patterns.review(audit, 'strict', [value], model_call=call)['F-100']
    assert len(calls) == 3
    assert (result['verdict'], result['reading_grade'], result['one_sentence']) == (expected, 7, False)
    assert all('Whole example ' + str(i) in result['reason'] for i in range(3))


@pytest.mark.parametrize('failure', ['transport', 'malformed', 'missing', 'duplicate'])
def test_later_packet_failure_preserves_earlier_successful_call_receipts(monkeypatch, failure):
    value, audit = candidate(count=2), Audit()
    one_example_packets(monkeypatch, value)
    def call(prompt, *, schema):
        if not audit.calls:
            return reply(prompt)
        if failure == 'transport':
            raise RuntimeError('packet connection failed')
        if failure == 'malformed':
            text = 'complete malformed response'
        elif failure == 'missing':
            text = json.dumps({'reviews': []})
        else:
            payload = json.loads(reply(prompt).text)
            payload['reviews'].append(payload['reviews'][0])
            text = json.dumps(payload)
        return ModelReply('test', 'second-packet', text)
    with pytest.raises(ValueError, match='meaning review failed'):
        patterns.review(audit, 'failure', [value], model_call=call)
    assert len(audit.calls) == 2
    first, last = audit.calls
    assert first[0] == last[0] == 'forms-night:failure:review'
    assert first[-2:] == (True, None) and last[-2] is False and last[-1]
    assert first[5] == reply(first[3]).text
    assert last[5] is None if failure == 'transport' else last[5] is not None
    assert first[3] != last[3]


def test_an_individually_oversized_whole_example_fails_before_any_model_call():
    value, audit = candidate(count=1, size=750_000), Audit()
    def forbidden(*args, **kwargs):
        pytest.fail('an oversized whole source must fail before the model door')
    with pytest.raises(ValueError, match='whole review example exceeds prompt limit: F-100'):
        patterns.review(audit, 'oversized', [value], model_call=forbidden)
    assert not audit.calls and len(value['examples'][0]['text']) > 750_000


def test_empty_example_candidate_is_not_dropped_between_large_candidates(monkeypatch):
    first, empty, last = candidate('F-100', count=1), candidate('F-101', count=0), candidate('F-102', count=1)
    one_example_packets(monkeypatch, first)
    packets = patterns.review_packets([first, empty, last])
    assert [c['form']['number'] for _prompt, values in packets for c in values] == ['F-100', 'F-101', 'F-102']
    assert [c for _prompt, values in packets for c in values if c['form']['number'] == 'F-101'][0]['examples'] == []


def test_duplicate_form_numbers_fail_closed_before_model_call():
    with pytest.raises(ValueError, match='duplicate review candidate number'):
        patterns.review(Audit(), 'duplicate', [candidate(), candidate()], model_call=lambda *_: pytest.fail('model called'))


def test_graph_part_packets_keep_exact_frame_exception_and_source_text(monkeypatch):
    value = candidate()
    value['form'].update(when={'answer': 'not_sure', 'graph_parts': True}, sentence=forms_middle.PART_FRAME)
    one_example_packets(monkeypatch, value)
    audit = Audit()
    def call(prompt, *, schema):
        assert 'two-sentence exception' in prompt
        assert batch(prompt)[0]['form']['sentence'] == forms_middle.PART_FRAME
        return reply(prompt, one_sentence=False)
    result = patterns.review(audit, 'graph-parts', [value], model_call=call)['F-100']
    assert len(audit.calls) == 3 and result['one_sentence'] is False
    assert result['verdict'] == 'explains_pattern' and result['reading_grade'] == 3
