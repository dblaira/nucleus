"""Practice uses the normal checked ask path without entering the real record."""
import json
from pathlib import Path
import sqlite3

import pytest

from nucleus import NUCLEUS_FILES, ask, dictionary, forms_practice as practice, links, store as store_module
from nucleus.graph import load_graph
from nucleus.model import ModelReply
from nucleus.store import Store

FLOW_RECORD = 'conn-obs-fable5-2026-07-10-affect-work-momentum-compass'
FLOW_QUOTE = "Momentum is Adam's compass"


def reading(word='FLOW'):
    return {'outcome': 'yes', 'heSaidTheWordItself': [{'word': word}], 'hisRoutesSentItHere': [],
            'anotherRouteWasPossible': [], 'noMeaningAddedYet': [], 'stopped': None, 'mustAskFirst': None}


@pytest.fixture
def copy(tmp_path, monkeypatch):
    monkeypatch.delenv('NUCLEUS_FORMS_ONLY', raising=False)
    store = Store(tmp_path / 'review.sqlite3')
    store.connection.execute("INSERT INTO form_night_runs(id,started,status,inputs_json) VALUES ('night',1,'running','[]')")
    store.connection.commit()
    yield store
    store.connection.close()


def writer(values):
    return lambda prompt, **kwargs: ModelReply('test', 'practice-writer', json.dumps({'questions': values}))


def scenario(question='Why does FLOW feel clear here?', word='FLOW'):
    return {'question': question, 'target_word': word}


def fake_ask(question, *, store, surface, brief, question_id, model_call=None):
    assert surface == 'practice' and brief(question)['outcome'] == 'yes'
    store.save_answer(question_id, 'answered', 'not_sure', 'Not sure.', '{}', True, None)
    return ask.Result(question_id, question, 'answered', answer='not_sure', text='Not sure.')


def test_practice_uses_normal_ask_and_keeps_checked_screen_and_full_trace(copy, monkeypatch):
    monkeypatch.setattr(dictionary, 'brief', lambda q: reading())
    payload = {'answer': 'not_sure', 'words': [{'word': 'FLOW', 'why': 'Momentum lines up here, but the records do not show what happened.'}],
               'records': [{'id': FLOW_RECORD, 'quote': FLOW_QUOTE,
                            'why': 'Momentum lines up here, but the records do not show what happened.'}], 'possibility': []}
    calls = []
    def call(prompt, *, schema=None):
        calls.append((prompt, schema))
        if schema == practice.SCHEMA:
            return writer([scenario()])(prompt)
        return ModelReply('test', 'checked-ask', json.dumps(payload))
    monkeypatch.setattr(ask.explain_module, 'start', lambda *a, **k: pytest.fail('practice must not start a background paragraph'))
    outcome = practice.run(copy, 'night', model_call=call)
    assert (outcome['status'], outcome['generated'], outcome['asked'], outcome['answered'], outcome['refused']) == ('completed', 1, 1, 1, 0)
    assert outcome['model_calls'] == 2 and len(calls) == 2
    result = outcome['results'][0]
    qid = result['question_id']
    assert copy.question(qid)['surface'] == 'practice'
    assert result['reading'] == reading()
    assert result['result']['answer'] == 'not_sure' and FLOW_QUOTE in result['result']['text']
    assert copy.answer(qid)['gate_ok'] == 1
    assert copy.connection.execute('SELECT count(*) FROM form_misses WHERE question_id=?', (qid,)).fetchone()[0] == 1
    assert copy.recent() == []
    assert outcome == practice.report(copy, 'night')
    generator = copy.connection.execute('SELECT prompt,reply FROM form_practice_runs').fetchone()
    assert generator == (calls[0][0], json.dumps({'questions': [scenario()]}))
    assert copy.connection.execute('SELECT count(*) FROM links').fetchone()[0] == 0


def test_generator_style_uses_only_exact_real_surface_questions(copy):
    for question, surface in [('Why do I trust this app?', 'web'), ('What pulls me?', 'cowboyai-iphone'),
                              ('GRADE QUESTION', 'grade'), ('OLD PRACTICE', 'practice')]:
        copy.new_question(question, surface)
    prompt = practice.make_prompt(copy, dictionary.load_meanings(NUCLEUS_FILES['meanings']))
    samples = json.loads(prompt.split('His real questions, exact:\n')[1].split('\nQuestions already present')[0])
    assert samples == [{'question': 'Why do I trust this app?', 'surface': 'web'},
                       {'question': 'What pulls me?', 'surface': 'cowboyai-iphone'}]
    assert 'never facts about Adam' in prompt and 'settled meanings' in prompt


def test_practice_budget_caps_asks_and_retains_overflow(copy, monkeypatch):
    monkeypatch.setattr(dictionary, 'brief', lambda q: reading())
    values = [scenario(f'What does FLOW mean in practice {i}?') for i in range(23)]
    result = practice.run(copy, 'night', model_call=writer(values), ask_call=fake_ask)
    assert (result['generated'], result['asked'], result['refused']) == (23, 20, 3)
    assert result['refusal_reasons'] == {'practice limit: more than 20 questions': 3}
    assert result['results'][-1]['raw'] == values[-1]
    assert copy.connection.execute("SELECT count(*) FROM questions WHERE surface='practice'").fetchone()[0] == 20
    assert json.loads(practice.SCHEMA.read_text())['properties']['questions']['maxItems'] == 20


def test_practice_rejects_old_duplicate_unknown_and_unreadable_targets(copy, monkeypatch):
    copy.new_question("Why don't I trust this app?", 'web')
    monkeypatch.setattr(dictionary, 'brief', lambda q: reading('LIFT' if q == 'A new question?' else 'FLOW'))
    values = [scenario(' WHY DON’T I TRUST THIS APP? '), scenario(), scenario('  why does FLOW feel clear here?  '),
              scenario('New made-up word?', 'IMAGINED'), scenario('A new question?')]
    result = practice.run(copy, 'night', model_call=writer(values), ask_call=fake_ask)
    assert (result['asked'], result['refused']) == (1, 4)
    assert [r['reason'] for r in result['results']] == ['question already present', None,
        'question already present', 'unknown dictionary target', 'dictionary did not find target word']


def test_exact_meaning_phrase_can_target_without_word_itself(copy, monkeypatch):
    meaning = dictionary.Meaning('FLOW', '6,12,15,23', 1, 'curious pulling sensation')
    monkeypatch.setattr(dictionary, 'load_meanings', lambda path: [meaning])
    monkeypatch.setattr(dictionary, 'brief', lambda q: {**reading(), 'heSaidTheWordItself': []})
    result = practice.run(copy, 'night', model_call=writer([scenario('What is this curious pulling sensation?')]), ask_call=fake_ask)
    assert result['asked'] == result['answered'] == 1


@pytest.mark.parametrize('payload', ['not JSON', '[]', '{"questions": {}}'])
def test_generator_failure_preserves_reply_and_failure_without_questions(copy, payload):
    result = practice.run(copy, 'night', model_call=lambda *a, **k: ModelReply('test', 'bad-shape', payload))
    assert result['status'] == 'failed' and result['asked'] == 0
    assert copy.connection.execute('SELECT reply FROM form_practice_runs').fetchone()[0] == payload
    assert copy.connection.execute('SELECT ok FROM model_calls').fetchone()[0] == 0
    assert copy.connection.execute('SELECT count(*) FROM questions').fetchone()[0] == 0


def test_generator_timeout_and_ask_exception_are_audited(copy, monkeypatch):
    monkeypatch.setattr(dictionary, 'brief', lambda q: reading())
    def fail_ask(*a, **k):
        raise RuntimeError('test ask failure')
    result = practice.run(copy, 'night', model_call=writer([scenario()]), ask_call=fail_ask)
    assert result['status'] == 'completed' and result['asked'] == result['refused'] == 1
    assert result['results'][0]['reason'] == 'practice ask failed: test ask failure'
    assert copy.question(result['results'][0]['question_id'])['surface'] == 'practice'
    copy.connection.execute("INSERT INTO form_night_runs(id,started,status,inputs_json) VALUES ('later',2,'running','[]')")
    copy.connection.commit()
    def timeout(*a, **k):
        raise TimeoutError('test writer timeout')
    failed = practice.run(copy, 'later', model_call=timeout)
    assert failed['status'] == 'failed' and failed['error'] == 'test writer timeout'
    assert failed['model_calls'] == 1


def test_practice_requires_running_night_and_runs_once(copy):
    with pytest.raises(ValueError, match='inside a running'):
        practice.run(copy, 'not-a-night', model_call=lambda *a, **k: pytest.fail('must not call'))
    practice.run(copy, 'night', model_call=writer([]))
    with pytest.raises(ValueError, match='already ran'):
        practice.run(copy, 'night', model_call=lambda *a, **k: pytest.fail('must not repeat writer'))


def test_practice_newness_uses_the_same_unicode_question_key():
    assert practice.question_key(' Ｗｈｙ  ＤＯＮ’Ｔ I? ') == practice.question_key("why don't i?")


def test_practice_switch_must_stay_off_before_generator(copy, monkeypatch):
    monkeypatch.setenv('NUCLEUS_FORMS_ONLY', '1')
    with pytest.raises(ValueError, match='requires NUCLEUS_FORMS_ONLY off'):
        practice.run(copy, 'night', model_call=lambda *a, **k: pytest.fail('must not call'))
    assert copy.connection.execute('SELECT count(*) FROM form_practice_runs').fetchone()[0] == 0


def test_practice_stays_out_of_the_live_record_and_aliases(tmp_path, monkeypatch):
    # This is an isolated stand-in for live; the actual live file is never opened.
    live = tmp_path / 'live.sqlite3'
    sqlite3.connect(live).close()
    monkeypatch.setattr(store_module, 'STORE_PATH', live)
    monkeypatch.setattr(ask, 'STORE_PATH', live)
    symlink, hardlink = tmp_path / 'symlink.sqlite3', tmp_path / 'hardlink.sqlite3'
    symlink.symlink_to(live)
    hardlink.hardlink_to(live)
    before = live.read_bytes()
    with pytest.raises(ValueError, match='never the live'):
        ask.ask('FLOW?', surface='practice')
    for path in [live, symlink, hardlink]:
        with pytest.raises(ValueError, match='never the live'):
            store_module.require_practice_copy(path)
    assert live.read_bytes() == before
    store = Store(live)
    after_schema = live.read_bytes()
    with pytest.raises(ValueError, match='never the live'):
        store.new_question('FLOW?', 'practice')
    # Even a misleading path cannot conceal the actual connected live file.
    separate = tmp_path / 'copy.sqlite3'
    sqlite3.connect(separate).close()
    store.path = separate
    with pytest.raises(ValueError, match='never the live'):
        ask.ask('FLOW?', store=store, surface='practice')
    assert live.read_bytes() == after_schema
    store.connection.close()


def test_supplied_question_ids_cannot_spoof_practice_or_real_surface(copy):
    real = copy.new_question('FLOW?', 'web')
    practice_id = copy.new_question('FLOW?', 'practice')
    for qid, surface, question in [(real, 'practice', 'FLOW?'), (practice_id, 'web', 'FLOW?'),
                                   (practice_id, 'practice', 'LIFT?'), ('missing', 'practice', 'FLOW?')]:
        with pytest.raises(ValueError, match='question id and surface'):
            ask.ask(question, store=copy, surface=surface, question_id=qid,
                    brief=lambda q: pytest.fail('must stop before dictionary'))
    assert copy.connection.execute('SELECT count(*) FROM steps').fetchone()[0] == 0


def test_practice_history_repeats_counts_and_grades_are_isolated(copy):
    practice_id = copy.new_question('What is FLOW?', 'practice')
    copy.save_answer(practice_id, 'answered', 'not_sure', 'practice', '{"practice":true}', True, None, 'same-hash')
    real = copy.new_question('What is FLOW?', 'web')
    assert copy.find_repeat('What is FLOW?', 'same-hash', real) is None
    assert copy.times_asked('What is FLOW?', real) == 0
    assert copy.times_asked('What is FLOW?', practice_id) == 0
    assert copy.recent() == []
    with pytest.raises(ValueError, match='never count in the grade'):
        copy.save_grade('grade', practice_id, 'What is FLOW?', None, 'not_sure', 'answered', True, 1)
    assert copy.connection.execute('SELECT count(*) FROM grades').fetchone()[0] == 0
    copy.save_answer(real, 'answered', 'aligned', 'real', '{"real":true}', True, None, 'same-hash')
    later = copy.new_question('What is FLOW?', 'web')
    assert copy.find_repeat('What is FLOW?', 'same-hash', later)['question_id'] == real
    assert copy.times_asked('What is FLOW?', later) == 1
    assert [r['id'] for r in copy.recent()] == [real]
    practice_again = copy.new_question('What is FLOW?', 'practice')
    assert copy.find_repeat('What is FLOW?', 'same-hash', practice_again)['question_id'] == practice_id


def test_practice_cannot_seed_new_links_but_real_and_legacy_answers_can(copy):
    graph = load_graph(NUCLEUS_FILES['graph'], NUCLEUS_FILES['ledger'])
    for word, surface in [('FLOW', 'practice'), ('LIFT', 'web'), ('VALUE', 'legacy')]:
        qid = 'orphan' if surface == 'legacy' else copy.new_question(f'{word}?', surface)
        payload = {'words': [{'word': word}], 'records': [{'id': FLOW_RECORD, 'quote': FLOW_QUOTE, 'why': 'Momentum matters.'}]}
        copy.save_answer(qid, 'answered', 'not_sure', 'text', json.dumps(payload), True, None)
    assert links.seed_from_answers(copy, graph) == 2
    assert copy.links_for('FLOW') == []
    assert len(copy.links_for('LIFT')) == len(copy.links_for('VALUE')) == 1
