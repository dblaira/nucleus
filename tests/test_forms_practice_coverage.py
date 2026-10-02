"""Real screens anchor practice coverage; the same rule is one form."""
from copy import deepcopy
import json

from nucleus import forms, forms_night as night, forms_review as review, serve
from test_forms_night import KINDS, candidate, copy, miss, picture, run


def origin(store, word, surface):
    qid = miss(store, word)
    store.connection.execute('UPDATE questions SET surface=? WHERE id=?', (surface, qid))
    store.connection.commit()
    return qid


def test_a_form_needs_one_real_question(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        origin(copy, word, 'practice')
    result = run(copy)
    row = result['results'][0]
    assert (row['fit_count'], row['fit_word_count']) == (3, 3)
    assert (row['real_fit_count'], row['practice_fit_count']) == (0, 3)
    assert row['reason'] == 'needs one real question'
    assert result['proposed'] == 0 and result['meaning_reviews'] == []


def test_real_and_practice_together_can_pass_and_show_both_counts(copy):
    origin(copy, 'FLOW', 'cowboyai-iphone')
    for word in ['LIFT', 'VALUE']:
        origin(copy, word, 'practice')
    result = run(copy)
    assert result['proposed'] == 1
    row = result['results'][0]
    assert (row['fit_count'], row['fit_word_count']) == (3, 3)
    assert (row['real_fit_count'], row['practice_fit_count']) == (1, 2)
    queue = review.pending(copy, forms.FORMS_PATH)
    assert queue[0]['error'] is None
    page = serve.forms_page(queue, 'fixture')
    assert 'fits 1 of your questions · 2 practice questions' in page
    assert page.count('Practice question') == 2 and page.count('Your question') == 1
    assert page.count('>Yes</button>') == page.count('>No</button>') == 1
    assert forms.pick(night.screen_from_picture(picture(), KINDS))[0] is None


def test_grade_cli_and_unknown_surfaces_cannot_supply_a_real_anchor(copy):
    for word, surface in [('FLOW', 'grade'), ('LIFT', 'cli'), ('VALUE', 'other')]:
        origin(copy, word, surface)
    for word in ['WORK', 'MOMENTUM', 'PULLED']:
        origin(copy, word, 'practice')
    row = run(copy)['results'][0]
    assert row['real_fit_count'] == 0 and row['practice_fit_count'] == 3
    assert row['reason'] == 'needs one real question'


def test_repeated_question_counts_once_across_both_sources_preferring_real(copy):
    origin(copy, 'FLOW', 'practice')
    origin(copy, 'FLOW', 'web')
    origin(copy, 'LIFT', 'practice')
    row = run(copy)['results'][0]
    assert (row['real_fit_count'], row['practice_fit_count'], row['fit_word_count']) == (1, 1, 2)
    assert row['reason'] == 'fits too few answers'
    examples = night.coverage_for(copy, row['proposal_id'])
    assert len(examples) == 3


def test_same_form_refused_even_when_wording_kind_order_and_nulls_differ(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        origin(copy, word, 'web')
    first = candidate()
    second = candidate(when={'answer': 'aligned', 'kinds_present': ['rejects', 'depends on'],
                             'missing_links': None},
                       sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.')
    result = run(copy, [first, second])
    assert (result['proposed'], result['refused']) == (1, 1)
    assert result['results'][1]['reason'] == 'same form'
    assert result['results'][1]['raw'] == second
    assert len(copy.form_proposals()) == 2


def test_saved_coverage_origin_comes_from_durable_question(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        origin(copy, word, 'web')
    result = run(copy)
    pid = result['results'][0]['proposal_id']
    matches = night.coverage_for(copy, pid)
    changed = deepcopy(matches)
    for example in changed:
        example['surface'] = 'practice'
    copy.connection.execute('UPDATE form_night_coverage SET matches_json=? WHERE proposal_id=?',
                            (json.dumps(changed), pid))
    copy.connection.commit()
    assert night.source_counts(night.coverage_for(copy, pid)) == (3, 0)


def test_practice_answer_id_is_not_a_history_endpoint(copy):
    from test_forms_review import serving, request
    qid = origin(copy, 'FLOW', 'practice')
    with serving((copy, forms.FORMS_PATH, [])) as server:
        assert request(server, path='/ask/' + qid)[0] == 404
        assert request(server, path='/recent')[2] == '[]'


def test_default_night_creates_practice_screens_before_measuring_forms(copy, monkeypatch):
    from nucleus import ask, dictionary, forms_practice as practice
    from nucleus.model import ModelReply
    from test_forms_night import model_reply
    from test_forms_practice import reading

    origin(copy, 'VALUE', 'web')
    monkeypatch.setattr(dictionary, 'brief', lambda q: reading('FLOW' if 'FLOW' in q else 'LIFT'))
    calls = []
    def call(prompt, *, schema):
        calls.append(schema)
        if schema == practice.SCHEMA:
            return ModelReply('test', 'writer', json.dumps({'questions': [
                {'question': 'Where does FLOW fit at work?', 'target_word': 'FLOW'},
                {'question': 'Where does LIFT fit at work?', 'target_word': 'LIFT'}]}))
        return model_reply([candidate()])(prompt, schema=schema)

    def checked_screen(question, *, store, surface, brief, question_id, model_call):
        assert surface == 'practice'
        word = brief(question)['heSaidTheWordItself'][0]['word']
        payload = {'answer': 'aligned', 'words': [{'word': word}],
                   'records': [{'id': 'r1', 'quote': 'First quote'}, {'id': 'r2', 'quote': 'Second quote'}]}
        text = f'aligned and why\n\n{word} depends on “First quote”\n\n{word} rejects “Second quote”'
        store.save_answer(question_id, 'answered', 'aligned', text, json.dumps(payload), True, None)
        store.start_step(question_id, '5 model')
        store.finish_step(question_id, '5 model', 'painted from your links, no model')
        store.save_form_miss(question_id, picture(word), 'no form fits')
        return ask.Result(question_id, question, 'answered', answer='aligned', text=text)

    result = night.night(copy.path, model_call=call, practice_ask=checked_screen)
    assert result['status'] == 'completed' and result['practice']['asked'] == 2
    assert result['proposed'] == 1
    assert (result['results'][0]['real_fit_count'], result['results'][0]['practice_fit_count']) == (1, 2)
    assert calls[0] == practice.SCHEMA and calls[1] == night.SCHEMA
    assert len(copy.recent()) == 1


def test_failed_practice_writer_stops_night_before_form_writer(copy):
    from nucleus import forms_practice as practice
    from nucleus.model import ModelReply
    origin(copy, 'FLOW', 'web')
    def bad_writer(prompt, *, schema):
        assert schema == practice.SCHEMA
        return ModelReply('test', 'bad-writer', 'bad JSON')
    result = night.night(copy.path, model_call=bad_writer)
    assert result['status'] == result['practice']['status'] == 'failed'
    assert result['practice']['asked'] == result['proposed'] == 0
    assert copy.form_proposals() == []


def test_pending_form_counts_and_examples_refresh_together_without_overwriting(copy):
    for word in ['FLOW', 'LIFT', 'VALUE']:
        origin(copy, word, 'web')
    result = run(copy)
    proposal = review.pending(copy, forms.FORMS_PATH)[0]
    pid = proposal['id']
    original = copy.connection.execute('SELECT matches_json FROM form_night_coverage WHERE proposal_id=?', (pid,)).fetchone()[0]
    origin(copy, 'WORK', 'practice')
    updated = run(copy, [])
    assert updated['status'] == 'completed' and updated['prior_proposals_refused'] == []
    fresh = review.pending(copy, forms.FORMS_PATH)[0]
    assert (fresh['real_fit_count'], fresh['practice_fit_count']) == (3, 1)
    assert fresh['error'] is None and fresh['version'] != proposal['version']
    assert copy.connection.execute('SELECT matches_json FROM form_night_coverage WHERE proposal_id=?', (pid,)).fetchone()[0] == original
    assert copy.connection.execute('SELECT count(*) FROM form_coverage_checks WHERE proposal_id=?', (pid,)).fetchone()[0] == 1


def test_failed_night_cannot_publish_refreshed_coverage(copy):
    from nucleus.model import ModelReply
    for word in ['FLOW', 'LIFT', 'VALUE']:
        origin(copy, word, 'web')
    run(copy)
    before = review.pending(copy, forms.FORMS_PATH)[0]
    origin(copy, 'WORK', 'practice')
    result = night.night(copy.path, practice=False,
                        model_call=lambda *a, **k: ModelReply('test', 'bad-writer', 'bad JSON'))
    assert result['status'] == 'failed'
    assert review.pending(copy, forms.FORMS_PATH)[0]['version'] == before['version']
    assert copy.connection.execute('SELECT count(*) FROM form_coverage_checks').fetchone()[0] == 0
