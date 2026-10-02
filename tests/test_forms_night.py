from copy import deepcopy
import fcntl
import json
from pathlib import Path
import plistlib
import sqlite3

import pytest

from nucleus import forms, forms_night as night, forms_patterns as patterns
from nucleus.model import ModelReply
from nucleus.store import Store

KINDS = ['depends on', 'supports', 'requires', 'should not', *sorted(patterns.PUSHING_KINDS)]


def candidate(**changes):
    value = {'when': {'answer': 'aligned', 'kinds_present': ['depends on', 'rejects']},
             'sentence': '{word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.'}
    value.update(changes)
    return value


def picture(word='FLOW', kind='depends on'):
    return {'answer': 'aligned', 'words': [{'word': word}], 'records': [
        {'link_word': word, 'leaf': 'r1', 'kind': kind, 'quote': 'First quote'},
        {'link_word': word, 'leaf': 'r2', 'kind': 'rejects', 'quote': 'Second quote'}], 'missing': []}


def model_reply(candidates):
    def call(prompt, *, schema):
        if schema == patterns.REVIEW_SCHEMA:
            batch = json.loads(prompt.split('\nCandidates:\n', 1)[1])
            return ModelReply('test', 'review-fixture', json.dumps({'reviews': [
                {'number': c['form']['number'], 'verdict': 'explains_pattern',
                 'reading_grade': 3, 'one_sentence': True, 'reason': 'Test reviewer: two exact rows joined in simple words.'} for c in batch]}))
        assert schema == night.SCHEMA
        return ModelReply('test', 'fixture', json.dumps({'forms': candidates}))
    return call


@pytest.fixture
def copy(tmp_path, monkeypatch):
    monkeypatch.setattr(night, 'load_kinds', lambda: KINDS)
    monkeypatch.setattr(forms, 'load_kinds', lambda: KINDS)
    monkeypatch.delenv('NUCLEUS_FORMS_ONLY', raising=False)
    catalog = tmp_path / 'forms.txt'
    catalog.write_text('forms = []\n')
    monkeypatch.setattr(forms, 'FORMS_PATH', catalog)
    store = Store(tmp_path / 'copy.sqlite3')
    yield store
    store.connection.close()


def miss(store, word='FLOW', kind='depends on'):
    qid = painted(store, word, kind)
    store.save_form_miss(qid, picture(word, kind), 'no approved forms')
    return qid


def painted(store, word='FLOW', kind='depends on', printed_kind=None):
    qid = store.new_question(f'What is {word}?', 'web')
    payload = {'answer': 'aligned', 'words': [{'word': word}],
               'records': [{'id': 'r1', 'quote': 'First quote'}, {'id': 'r2', 'quote': 'Second quote'}]}
    store.save_answer(qid, 'answered', 'aligned',
                      f'aligned and why\n\n0.90 · 2026-10-01 — {word} {printed_kind or kind} “First quote”\n\n0.80 — {word} rejects “Second quote”',
                      json.dumps(payload), True, None)
    store.start_step(qid, '5 model')
    store.finish_step(qid, '5 model', 'painted from your links, no model')
    return qid


def history(store):
    """Three actual painted answers for two words; no new night trigger events."""
    qids = [painted(store, word) for word in ['FLOW', 'LIFT', 'FLOW']]
    store.connection.execute('UPDATE questions SET question=? WHERE id=?', ('Why does FLOW matter?', qids[-1]))
    store.connection.commit()
    return qids


def run(store, candidates=None, **kwargs):
    return night.night(store.path, practice=False, model_call=model_reply([candidate()] if candidates is None else candidates), **kwargs)


def test_preview_does_not_approve_or_change_day_selection(copy):
    proposal = {'number': 'F-1', 'status': 'proposed', 'author': 'test', 'date': '2026-10-01', **candidate()}
    original = deepcopy(proposal)
    screen = night.screen_from_picture(picture(), KINDS)
    assert forms.preview(proposal, screen).text == 'FLOW depends on “First quote” and rejects “Second quote”.'
    assert forms.fill(proposal, screen) is None
    assert forms.pick(screen)[0] is None
    assert proposal == original
    assert forms.preview({**proposal, 'status': 'rejected'}, screen) is None


def test_one_pass_retains_exact_trace_and_three_real_distinct_examples(copy):
    qids = {miss(copy, word) for word in ['FLOW', 'LIFT', 'MOMENTUM', 'VALUE']}
    result = run(copy)
    assert (result['status'], result['proposed'], result['refused']) == ('completed', 1, 0)
    saved = copy.form_proposals()[0]
    assert saved['status'] == saved['payload']['status'] == 'proposed'
    assert saved['payload']['author'] == 'test/fixture'
    examples = result['results'][0]['examples']
    assert len(examples) == 3
    assert {e['question_id'] for e in examples} <= qids
    for e in examples:
        assert ''.join(p['text'] for p in e['parts']) == e['text']
        assert forms.preview(saved['form'], night.restore_screen(e['screen'])).text == e['text']
    trace = copy.connection.execute('SELECT prompt,reply FROM model_calls').fetchone()
    assert 'Saved screens:' in trace[0]
    assert json.loads(trace[1]) == {'forms': [candidate()]}
    assert copy.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 2
    assert result['meaning_reviews'][0]['ok']
    assert forms.load(forms.FORMS_PATH) == []
    assert not forms.forms_only()


@pytest.mark.parametrize('value,reason', [
    (candidate(sentence='{quote}'), 'unknown or malformed blank'),
    (candidate(when={'kinds_present': ['invents']}), 'unknown middle word'),
    (candidate(when={'secret': True}), 'unknown or missing conditions'),
    (candidate(when={'answer': 'aligned', 'secret': None}), 'unknown or missing conditions'),
    (candidate(sentence='You should follow {word}.'), 'advice'),
    (candidate(sentence='{word}. Two. Three. Four. Five. Six.'), 'more than 4 sentences'),
    (candidate(sentence='pre{word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.'), 'kill switch'),
    (candidate(when={'answer': 'dont_know', 'kinds_present': ['depends on', 'rejects']}), 'fits too few answers'),
    ({**candidate(), 'status': 'approved'}, 'unknown or missing proposal fields'),
    ('malformed', 'unknown or missing proposal fields'),
])
def test_every_refused_form_and_original_payload_are_retained(copy, value, reason):
    miss(copy)
    result = run(copy, [value])
    assert (result['proposed'], result['refused']) == (0, 1)
    assert reason in result['results'][0]['reason']
    assert result['results'][0]['raw'] == value
    assert copy.form_proposals()[0]['status'] == 'rejected'
    assert result['results'][0]['examples'] == []


def test_null_conditions_are_wire_format_only(copy):
    history(copy)
    miss(copy)
    result = run(copy, [candidate(when={'answer': 'aligned', 'kinds_present': ['depends on', 'rejects'],
        'kinds_absent': None, 'record_count': None, 'word_count': None, 'missing_links': None})])
    assert result['proposed'] == 1
    assert result['results'][0]['form']['when'] == candidate()['when']
    assert 'kinds_absent' in result['results'][0]['raw']['when']


def test_explicit_recheck_keeps_original_and_reproposes_once(copy):
    history(copy)
    miss(copy)
    form = {'number': 'F-43', 'status': 'proposed', 'author': 'old writer',
            'date': '2026-10-02', **candidate()}
    pid = copy.save_form_proposal(form, 'negative or caveat: not')
    original = copy.form_proposals()[0]
    result = run(copy, [candidate()], recheck=('F-43',))
    assert result['status'] == 'completed'
    assert (result['proposed'], result['refused']) == (1, 1)
    proposals = {p['id']: p for p in copy.form_proposals()}
    assert proposals[pid] == original
    replacement = next(p for p in proposals.values() if p['number'] == 'F-44')
    assert replacement['status'] == 'proposed'
    assert replacement['form']['when'] == original['form']['when']
    assert replacement['form']['sentence'] == original['form']['sentence']
    assert replacement['form']['author'] == 'program/recheck-own-words'
    assert result['results'][1]['reason'] == 'same form'
    assert forms.pick(night.screen_from_picture(picture(), KINDS))[0] is None


def test_recheck_cannot_override_another_existing_form(copy):
    history(copy)
    miss(copy)
    for number in ('F-43', 'F-44'):
        copy.save_form_proposal({'number': number, 'status': 'proposed', 'author': 'test',
                                'date': '2026-10-02', **candidate()}, 'old refusal')
    result = run(copy, [], recheck=('F-43',))
    assert result['proposed'] == 0 and result['results'][0]['reason'] == 'same form'


def test_recheck_cannot_override_same_number_in_approved_catalog(copy):
    history(copy)
    miss(copy)
    form = {'number': 'F-43', 'status': 'proposed', 'author': 'test',
            'date': '2026-10-02', **candidate()}
    copy.save_form_proposal(form, 'old refusal')
    from nucleus.forms_review import append_text
    forms.FORMS_PATH.write_text(append_text(forms.FORMS_PATH.read_text(), {**form, 'status': 'approved'}, []))
    result = run(copy, [], recheck=('F-43',))
    assert result['proposed'] == 0 and result['results'][0]['reason'] == 'same form'


def test_recheck_requires_unique_explicit_rejected_forms(copy):
    copy.save_form_proposal({'number': 'F-43', 'status': 'proposed', 'author': 'test',
                            'date': '2026-10-02', **candidate()}, None)
    with pytest.raises(ValueError, match='one rejected proposal'):
        night.rechecked_candidates(copy.form_proposals(), ('F-43',))
    with pytest.raises(ValueError, match='distinct'):
        night.rechecked_candidates(copy.form_proposals(), ('F-43', 'F-43'))


def test_no_input_recheck_failure_records_only_the_attempted_review(copy):
    history(copy)
    miss(copy)
    assert run(copy, [])['status'] == 'completed'  # Consume all current triggers.
    copy.save_form_proposal({'number': 'F-43', 'status': 'proposed', 'author': 'test',
                            'date': '2026-10-02', **candidate()}, 'old refusal')
    original = copy.form_proposals()[0]
    def call(prompt, *, schema):
        assert schema == patterns.REVIEW_SCHEMA
        raise TimeoutError('review timeout')
    result = night.night(copy.path, practice=False, recheck=('F-43',), model_call=call)
    assert result['status'] == 'failed' and 'review timeout' in result['error']
    calls = copy.connection.execute('SELECT question_id FROM model_calls WHERE question_id LIKE ?',
                                   ('forms-night:' + result['run_id'] + '%',)).fetchall()
    assert calls == [('forms-night:' + result['run_id'] + ':review',)]
    assert copy.form_proposals()[0] == original


def test_fill_checks_all_matching_answers_not_just_first_three(copy):
    for word in ['FLOW', 'LIFT', 'MOMENTUM', 'you should']:
        miss(copy, word)
    result = run(copy)
    assert result['proposed'] == 1
    pid = result['results'][0]['proposal_id']
    assert len(night.coverage_for(copy, pid)) == 4
    review_prompt = copy.connection.execute("SELECT prompt FROM model_calls WHERE question_id LIKE 'forms-night:%:review'").fetchone()[0]
    reviewed = json.loads(review_prompt.split('\nCandidates:\n', 1)[1])[0]['examples']
    assert len(reviewed) == 4
    assert any('you should' in e['text'] for e in reviewed)


def test_limit_never_writes_more_than_twelve_proposal_rows_but_keeps_overflow(copy):
    history(copy)
    miss(copy)
    values = [candidate(when={**candidate()['when'], 'record_count': {'min': 0, 'max': i+3}}) for i in range(14)]
    result = run(copy, values)
    assert len(copy.form_proposals()) == 12
    assert (result['proposed'], result['refused']) == (12, 2)
    assert [r['raw'] for r in result['results']] == values
    assert result['results'][12]['reason'] == 'night limit: more than 12 forms'


def test_duplicate_previous_rejected_proposed_approved_and_same_batch(copy):
    history(copy)
    miss(copy)
    first = run(copy)
    copy.reject_form_proposal(first['results'][0]['proposal_id'], 'Adam said no')
    miss(copy, 'LIFT')
    result = run(copy, [candidate(), candidate(sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.'), candidate(sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.')])
    assert (result['proposed'], result['refused']) == (0, 3)
    assert all(r['reason'] == 'same form' for r in result['results'])
    miss(copy, 'MOMENTUM')
    result = run(copy, [candidate(sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.')])
    assert result['refused'] == 1
    forms.FORMS_PATH.write_text('''[[forms]]
number = "F-80"
status = "approved"
author = "test fixture only"
date = "2026-10-01"
sentence = "{word} has printed links."
[forms.when]
answer = "aligned"
''')
    miss(copy, 'VALUE')
    result = run(copy, [candidate(when={'answer': 'aligned'}, sentence='{word} has printed links.')])
    assert result['results'][0]['form']['number'] == 'F-81'
    assert result['results'][0]['reason'] == 'same form'


def test_success_consumes_only_inputs_present_before_the_call(copy):
    history(copy)
    miss(copy)
    def call(prompt, *, schema):
        miss(copy, 'LIFT')
        return ModelReply('test', 'fixture', '{"forms":[]}')
    first = night.night(copy.path, practice=False, model_call=call)
    assert first['inputs'] == 1
    second = run(copy)
    assert second['inputs'] == second['proposed'] == 1
    third = night.night(copy.path, practice=False, model_call=lambda *a, **k: pytest.fail('no new input must not call model'))
    assert third['inputs'] == third['proposed'] == 0


@pytest.mark.parametrize('response', ['timeout', 'not JSON', '[]', '{"forms": {}}'])
def test_failed_model_or_shape_retains_trace_and_retries_inputs(copy, response):
    history(copy)
    miss(copy)
    def call(prompt, **kwargs):
        if response == 'timeout':
            raise TimeoutError('test timeout')
        return ModelReply('test', 'fixture', response)
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['status'] == 'failed'
    assert len(copy.form_proposals()) == 0
    assert copy.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 1
    if response != 'timeout':
        assert copy.connection.execute('SELECT reply FROM form_night_runs').fetchone()[0] == response
    assert run(copy)['proposed'] == 1


def test_atomic_write_failure_keeps_no_half_proposals_and_does_not_consume(copy, monkeypatch):
    history(copy)
    miss(copy)
    original = Store.save_form_proposal
    def fail(self, payload, reason=None, **kwargs):
        if payload['number'] == 'F-2':
            raise OSError('test disk failure')
        return original(self, payload, reason, **kwargs)
    monkeypatch.setattr(Store, 'save_form_proposal', fail)
    result = run(copy, [candidate(), candidate(when={**candidate()['when'], 'record_count': {'min': 2}})])
    assert result['status'] == 'failed'
    assert copy.form_proposals() == []
    assert copy.connection.execute('SELECT count(*) FROM form_night_results').fetchone()[0] == 0
    monkeypatch.setattr(Store, 'save_form_proposal', original)
    assert run(copy)['proposed'] == 1


def test_bootstrap_uses_historical_printed_kind_never_current_links(copy):
    qid = painted(copy)
    painted(copy, 'LIFT')
    other = painted(copy, 'FLOW')
    copy.connection.execute('UPDATE questions SET question=? WHERE id=?', ('Why does FLOW matter?', other))
    copy.connection.commit()
    copy.connection.execute("INSERT INTO links(word,record,quote,why,source,found_at,kind) VALUES ('FLOW','r1','Quote','','test',1,'supports')")
    copy.connection.commit()
    assert run(copy)['inputs'] == 0
    first = run(copy, bootstrap=True)
    assert first['proposed'] == 1
    example = first['results'][0]['examples'][0]
    assert example['question_id'] == qid
    assert example['screen']['rows'][0]['kind'] == 'depends on'
    assert example['text'] == 'FLOW depends on “First quote” and rejects “Second quote”.'
    assert run(copy, bootstrap=True)['inputs'] == 0


def test_unrecoverable_historical_rows_are_audited_not_guessed(copy):
    painted(copy, printed_kind='unknown kind')
    result = run(copy, bootstrap=True)
    assert (result['inputs'], result['usable_inputs'], result['proposed']) == (1, 0, 0)
    assert 'no unambiguous printed middle word' in result['skipped_inputs'][0]['reason']
    assert copy.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 0


def test_downvote_after_old_answer_is_consumed_once_and_sent_with_explanation(copy):
    qid = painted(copy)
    run(copy, bootstrap=True)
    copy.save_explanation(qid, 'FLOW old paragraph', None, 'test', 'fixture', 1)
    copy.thumb_explanation(qid, False)
    def call(prompt, **kwargs):
        assert 'FLOW old paragraph' in prompt
        assert 'thumbed_down_explanation' in prompt
        return ModelReply('test', 'fixture', '{"forms":[]}')
    result = night.night(copy.path, practice=False, model_call=call)
    assert result['inputs'] == 1
    assert run(copy)['inputs'] == 0


def test_downvote_uses_miss_snapshot_when_historical_text_has_no_middle(copy):
    history(copy)
    qid = painted(copy, printed_kind='unknown')
    copy.save_form_miss(qid, picture(), 'no form fits')
    run(copy)
    copy.save_explanation(qid, 'FLOW old paragraph', None, 'test', 'fixture', 1)
    copy.thumb_explanation(qid, False)
    result = run(copy, [candidate(when={**candidate()['when'], 'record_count': {'min': 2}})])
    assert result['usable_inputs'] == result['proposed'] == 1


def test_live_file_and_aliases_refused_before_any_schema_write(tmp_path, monkeypatch):
    live = tmp_path / 'live.sqlite3'
    sqlite3.connect(live).close()
    monkeypatch.setattr(night, 'STORE_PATH', live)
    symlink = tmp_path / 'alias.sqlite3'
    symlink.symlink_to(live)
    hardlink = tmp_path / 'hard.sqlite3'
    hardlink.hardlink_to(live)
    before = live.read_bytes()
    for path in [live, symlink, hardlink]:
        with pytest.raises(ValueError, match='never the live'):
            night.night(path)
    assert live.read_bytes() == before
    with pytest.raises(ValueError, match='must already exist'):
        night.night(tmp_path / 'absent.sqlite3')


def test_switch_is_never_enabled_or_ignored(copy, monkeypatch):
    monkeypatch.setenv('NUCLEUS_FORMS_ONLY', '1')
    with pytest.raises(ValueError, match='requires NUCLEUS_FORMS_ONLY off'):
        night.night(copy.path)
    assert copy.connection.execute('SELECT count(*) FROM form_night_runs').fetchone()[0] == 0


def test_second_pass_cannot_overlap(copy):
    with copy.path.with_suffix('.sqlite3.forms.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match='already running'):
            run(copy)


def test_schedule_and_schema_are_bounded_repo_files():
    root = Path(__file__).resolve().parents[1]
    plist = plistlib.loads((root / 'launchd/com.nucleus.forms.plist').read_bytes())
    assert plist['Label'] == 'com.nucleus.forms'
    assert plist['StartCalendarInterval'] == {'Hour': 3, 'Minute': 0}
    assert plist['StandardOutPath'] == plist['StandardErrorPath'] == '/Users/adamblair/Library/Logs/nucleus-forms.log'
    assert plist['ProgramArguments'][2:4] == ['nucleus.forms', 'night']
    assert plist['ProgramArguments'][-1] == str(night.REVIEW_PATH)
    assert 'NUCLEUS_FORMS_ONLY' not in plist['EnvironmentVariables']
    assert 'RunAtLoad' not in plist and 'KeepAlive' not in plist
    schema = json.loads(night.SCHEMA.read_text())
    assert schema['properties']['forms']['maxItems'] == 12
