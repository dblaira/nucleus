import hashlib
import json
from pathlib import Path

from nucleus import NUCLEUS_FILES, ask, middle
from nucleus.contextual_sources import later_reports
from nucleus.graph import Graph, Record, load_graph
from nucleus.store import Store

QUESTION = 'why I can’t seem to feel happy'
WORDS = "I am satisfied with the response.  I have already escaped my earlier malaise and find myself feeling lighter. More awake and aware.\n"


def fixture(tmp_path, monkeypatch, *, session='one', role='input', decision='accepted', created='2026-10-11T05:00:00+00:00'):
    root = tmp_path / 'Ontology'
    monkeypatch.setitem(NUCLEUS_FILES, 'graph', root / 'accepted' / 'g.ttl')
    path = root / 'sources' / 'automatic-exact-words' / 'batch' / 'sources.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    def entry(identity, text, at, session):
        return {'identity': identity, 'adapter': 'codex', 'text': text, 'source_text': text,
                'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'source_sha256': hashlib.sha256(text.encode()).hexdigest(), 'char_start': 0, 'char_end': len(text),
                'created_at': at, 'context': {'session_id': session}}
    anchor = entry('codex:one:1:0:user_prompt:span:0', QUESTION, '2026-10-11T04:00:00+00:00', 'one')
    report = entry(f'codex:{session}:2:0:user_prompt:span:0', WORDS, created, session)
    path.write_text(json.dumps({'entries': [anchor, report]}))
    record = Record('https://understood.app/ontology/connection/report', 'report', 'report', 'stated_source_entry', '', created,
                    f'understood:sourceSnapshot "{path}" ;', record_class='SourceEntry', exact_words=WORDS,
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
        assert later_reports(graph, QUESTION) == []


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
    assert records[0]['context'] == 'later report in the same conversation'
    assert result.answer == 'not_sure' and saved['gate_ok'] == 1
    assert 'malaise' in middle.form(saved['text'], saved['reply_json'], [])['sections'][0]['lines'][0]
