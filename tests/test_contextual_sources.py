import hashlib
import json
import pytest
from pathlib import Path

from nucleus import NUCLEUS_FILES, ask, middle
from nucleus.contextual_sources import later_reports, review_later_words, SourceContextUnavailable
from nucleus.graph import Graph, Record, load_graph
from nucleus.store import Store

QUESTION = 'why I can’t seem to feel happy'
WORDS = "I am satisfied with the response.  I have already escaped my earlier malaise and find myself feeling lighter. More awake and aware.\n"


def fixture(tmp_path, monkeypatch, *, session='one', role='input', decision='accepted', created='2026-10-11T05:00:00+00:00', question=QUESTION, words=WORDS):
    root = tmp_path / 'Ontology'
    monkeypatch.setitem(NUCLEUS_FILES, 'graph', root / 'accepted' / 'g.ttl')
    path = root / 'sources' / 'automatic-exact-words' / 'batch' / 'sources.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    def entry(identity, text, at, session):
        return {'identity': identity, 'adapter': 'codex', 'text': text, 'source_text': text,
                'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'source_sha256': hashlib.sha256(text.encode()).hexdigest(), 'char_start': 0, 'char_end': len(text),
                'created_at': at, 'context': {'session_id': session}}
    anchor = entry('codex:one:1:0:user_prompt:span:0', question, '2026-10-11T04:00:00+00:00', 'one')
    report = entry(f'codex:{session}:2:0:user_prompt:span:0', words, created, session)
    path.write_text(json.dumps({'entries': [anchor, report]}))
    record = Record('https://understood.app/ontology/connection/report', 'report', 'report', 'stated_source_entry', '', created,
                    f'understood:sourceSnapshot "{path}" ;', record_class='SourceEntry', exact_words=words,
                    source_role=role, source_created_at=created, source_identity=report['identity'])
    graph = Graph({record.uri: record}, [{'claim': 'report', 'decision': decision, 'at': created}], '', '')
    return graph, path


def test_later_report_with_no_question_word_overlap_preserves_every_character(tmp_path, monkeypatch):
    graph, _ = fixture(tmp_path, monkeypatch)
    rows = later_reports(graph, QUESTION)
    assert len(rows) == 1 and rows[0]['quote'] == WORDS
    assert rows[0]['source_date'] == '2026-10-10'  # user's Pacific date
    assert 'causes' not in rows[0] and not rows[0]['why']
    assert graph.raw_graph == '' and len(graph.ledger) == 1


def test_never_borrows_other_conversations(tmp_path, monkeypatch):
    graph, _ = fixture(tmp_path, monkeypatch, session='other')
    assert later_reports(graph, QUESTION) == []


def test_rejected_and_question_records_never_become_reports(tmp_path, monkeypatch):
    for opts in ({'decision': 'rejected'}, {'role': 'question'}):
        graph, _ = fixture(tmp_path, monkeypatch, **opts)
        assert later_reports(graph, QUESTION) == []


def test_earlier_report_is_not_a_later_update(tmp_path, monkeypatch):
    graph, _ = fixture(tmp_path, monkeypatch, created='2026-10-11T03:00:00+00:00')
    assert later_reports(graph, QUESTION) == []


def test_modified_snapshot_or_offsets_are_not_trusted(tmp_path, monkeypatch):
    graph, path = fixture(tmp_path, monkeypatch)
    original = json.loads(path.read_text())
    for field, value in [('char_start', 1), ('text_sha256', 'bad'), ('source_text', 'invented words')]:
        data = json.loads(json.dumps(original))
        data['entries'][1][field] = value
        path.write_text(json.dumps(data))
        with pytest.raises(SourceContextUnavailable):
            later_reports(graph, QUESTION)


def test_damaged_anchor_and_unrelated_questions_do_not_link_context(tmp_path, monkeypatch):
    graph, path = fixture(tmp_path, monkeypatch)
    assert later_reports(graph, 'why I cannot seem to sleep') == []
    assert later_reports(graph, 'response') == []
    data = json.loads(path.read_text()); data['entries'][0]['source_sha256'] = 'bad'
    path.write_text(json.dumps(data))
    assert later_reports(graph, QUESTION) == []


def test_phone_form_preserves_context_quote_spaces_and_date():
    row = {'id': 'report', 'quote': WORDS, 'why': '', 'context': 'later report in the same conversation',
           'exact_words': True, 'source_date': '2026-10-10'}
    form = middle.form('There is some relationship, but not enough to justify causation.', json.dumps({'records': [row]}), [])
    assert form['sections'][0]['lines'] == [f'2026-10-10 — “{WORDS}”']
    assert form['sections'][0]['head'] == 'Later in the same conversation'
    assert 'Reasons' not in [section['head'] for section in form['sections']]


def test_actual_happiness_answer_includes_exact_later_words_without_model(tmp_path, monkeypatch):
    monkeypatch.setenv('NUCLEUS_NARRATIVE', '1')
    def forbidden(*args):
        raise AssertionError('model called')
    store = Store(tmp_path / 'n.sqlite3')
    result = ask.ask(QUESTION, store=store, model_call=forbidden, explain_call=forbidden)
    saved = store.answer(result.question_id)
    records = json.loads(saved['reply_json'])['records']
    expected = load_graph(NUCLEUS_FILES['graph'], NUCLEUS_FILES['ledger']).find('source-0fee3e8cc85bc970ee8acae95837fb03')
    from nucleus.graph import unescape
    assert records[0]['quote'] == unescape(expected.exact_words)
    assert records[0]['context'] == 'later words in the same recorded source context'
    assert result.answer == 'not_sure' and saved['gate_ok'] == 1
    assert 'malaise' in middle.form(saved['text'], saved['reply_json'], [])['sections'][0]['lines'][0]


@pytest.mark.parametrize('question,words', [
    ('Sleep?', 'Eight hours last night.  Rested.\n'),
    ('Did I ship?', 'The build is on the phone.\n'),
    ('Where are my keys?', 'Found them in the kitchen drawer.\n'),
    ('Have my knees improved?', 'No pain during the walk today.\n'),
    ('What is working now?', 'That worked.\n'),
])
def test_every_topic_and_short_question_considers_later_words(tmp_path, monkeypatch, question, words):
    graph, _ = fixture(tmp_path, monkeypatch, question=question, words=words)
    rows, audit = review_later_words(graph, question)
    assert rows[0]['quote'] == words  # no first-person or response vocabulary
    assert audit['checked_originals'] == ['report'] and audit['selected'] == ['report']
    assert audit['relationships_created'] == 0


def test_native_iphone_question_and_followup_share_recorded_question_identity(tmp_path, monkeypatch):
    graph, path = fixture(tmp_path, monkeypatch, question='Did I ship?', words='The build shipped.  It works.\n')
    data = json.loads(path.read_text())
    data['entries'][0].update(adapter='cowboyai', source_id='phone-question', role='question', context={})
    data['entries'][1].update(adapter='cowboyai', context={'question_id':'phone-question'})
    path.write_text(json.dumps(data))
    rows, audit = review_later_words(graph, 'Did I ship?')
    assert rows[0]['quote'] == 'The build shipped.  It works.\n'
    assert audit['selected'] == ['report']


def test_missing_source_blocks_answer_instead_of_silently_using_old_words(tmp_path, monkeypatch):
    graph, path = fixture(tmp_path, monkeypatch)
    path.unlink()
    with pytest.raises(SourceContextUnavailable):
        review_later_words(graph, QUESTION)


def test_shared_path_records_review_even_when_dictionary_stops(tmp_path, monkeypatch):
    def forbidden(*args):
        raise AssertionError('model called')
    store = Store(tmp_path / 'stopped.sqlite3')
    result = ask.ask('FLOW?', store=store, model_call=forbidden,
                     brief=lambda q: {'outcome':'stopped','stopped':'choose a meaning'})
    assert result.status == 'stopped'
    audit = json.loads(result.steps[0]['note'])['later_words_review']
    assert audit['checked_count'] > 0 and len(audit['checked_originals']) == audit['checked_count']


def test_model_path_receives_later_original_words_without_rewriting(tmp_path, monkeypatch):
    from nucleus.model import ModelReply
    graph, _ = fixture(tmp_path, monkeypatch, question='Sleep?', words='Eight hours last night.  Rested.\n')
    NUCLEUS_FILES['graph'].parent.mkdir(parents=True, exist_ok=True)
    NUCLEUS_FILES['graph'].write_text(graph.raw_graph)
    monkeypatch.delenv('NUCLEUS_NARRATIVE', raising=False)
    monkeypatch.delenv('NUCLEUS_NO_MODEL', raising=False)
    monkeypatch.setattr(ask, 'load_graph', lambda *args: graph)
    def model(prompt):
        marker = '===== Later original words: recorded source context, not causal relationships =====\n'
        rows = json.loads(prompt.split(marker)[1])
        assert rows[0]['quote'] == 'Eight hours last night.  Rested.\n'
        return ModelReply(provider='test', model='test', text=json.dumps({'answer':'dont_know','words':[],'records':[],'possibility':[]}))
    result = ask.ask('Sleep?', store=Store(tmp_path/'model.sqlite3'), model_call=model,
                     brief=lambda q: {'outcome':'no','heSaidTheWordItself':[], 'hisRoutesSentItHere':[]})
    assert result.status == 'answered'
    audit = json.loads(result.steps[0]['note'])['later_words_review']
    assert audit['selected'] == ['report']


@pytest.mark.parametrize('kind', ['aligned','not_sure','dont_know'])
def test_later_words_remain_inspectable_on_every_answer_form(kind):
    row = {'id':'report','quote':WORDS,'context':'recorded source context','exact_words':True,'source_date':'2026-10-10'}
    filled = middle.form_for({'status':'answered','answer':kind,'text':'answer','reply_json':json.dumps({'records':[row]})}, [], None, [])
    assert filled['sections'][0]['lines'] == [f'2026-10-10 — “{WORDS}”']


def test_newer_update_without_report_vocabulary_is_not_hidden_by_older_response(tmp_path, monkeypatch):
    from dataclasses import replace
    graph, path = fixture(tmp_path, monkeypatch)
    data = json.loads(path.read_text())
    words = 'The ache is gone.  Back to normal.\n'
    latest = dict(data['entries'][1], identity='codex:one:3:0:user_prompt:span:0', text=words, source_text=words,
                  text_sha256=hashlib.sha256(words.encode()).hexdigest(), source_sha256=hashlib.sha256(words.encode()).hexdigest(),
                  char_start=0,char_end=len(words),created_at='2026-10-11T06:00:00+00:00')
    data['entries'].append(latest);path.write_text(json.dumps(data))
    before = next(iter(graph.records.values()))
    newest = replace(before,uri=before.uri+'-new',leaf='report-new',label='report-new',exact_words=words,
                     source_identity=latest['identity'],source_created_at=latest['created_at'])
    graph.records[newest.uri] = newest
    graph.ledger.append({'claim':'report-new','decision':'accepted','at':latest['created_at']})
    rows, audit = review_later_words(graph, QUESTION)
    assert words in [row['quote'] for row in rows]
    assert WORDS in [row['quote'] for row in rows]
    assert audit['selected'] == ['report', 'report-new']
