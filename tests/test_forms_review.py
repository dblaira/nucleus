"""Slice 4 uses isolated stores/files. No test decides any real proposal."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from html.parser import HTMLParser
import http.client
import json
from pathlib import Path
import threading
from urllib.parse import urlencode

import pytest

from nucleus import forms, forms_review as review, serve, STORE_PATH
from nucleus.store import Store
from test_forms_night import candidate, copy, history, miss, run, picture, KINDS
from nucleus.forms_night import screen_from_picture


@pytest.fixture
def ready(copy):
    history(copy)
    miss(copy)
    result = run(copy, [candidate(), candidate(sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.')])
    assert result['proposed'] == 2
    return copy, forms.FORMS_PATH, review.pending(copy, forms.FORMS_PATH)


def decide(ready, choice='yes', index=0):
    store, path, proposals = ready
    p = proposals[index]
    return review.decide(store.path, path, p['id'], choice, p['version'])


def test_yes_saves_exact_approved_form_preserves_proposal_and_enables_day_pick(ready):
    store, path, proposals = ready
    before = store.form_proposals()[0]['payload']
    assert forms.pick(screen_from_picture(picture(), KINDS), path)[0] is None
    assert decide(ready) == 'F-1'
    assert forms.load(path) == [{**before, 'status': 'approved'}]
    filled, reason = forms.pick(screen_from_picture(picture(), KINDS), path)
    assert reason is None and filled.number == 'F-1'
    saved = store.form_proposals()[0]
    assert saved['status'] == 'approved' and saved['payload'] == before
    assert [p['number'] for p in review.pending(store, path)] == ['F-2']
    assert store.connection.execute('SELECT count(*) FROM form_night_results').fetchone()[0] == 2
    assert store.connection.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 2  # only the fixture night


def test_no_marks_rejected_and_keeps_payload_examples_and_file(ready):
    store, path, proposals = ready
    payload = store.form_proposals()[0]['payload']
    text = path.read_bytes()
    examples = review.examples_for(store, proposals[0]['id'])
    assert decide(ready, 'no') == 'F-1'
    saved = store.form_proposals()[0]
    assert saved['status'] == 'rejected' and saved['reason'] == 'Adam said no on /forms.'
    assert saved['payload'] == payload and review.examples_for(store, proposals[0]['id']) == examples
    assert path.read_bytes() == text
    assert forms.pick(screen_from_picture(picture(), KINDS), path)[0] is None


def test_a_proposed_form_is_never_chosen_or_approved_by_reading_the_page(ready):
    store, path, proposals = ready
    before = path.read_bytes()
    for p in proposals:
        assert forms.fill(p['form'], screen_from_picture(picture(), KINDS), kinds=KINDS) is None
    assert forms.pick(screen_from_picture(picture(), KINDS), path)[0] is None
    serve.forms_page(review.pending(store, path), 'test-token')
    assert path.read_bytes() == before
    assert all(p['status'] == 'proposed' for p in store.form_proposals())


def test_two_yeses_preserve_existing_blocks_and_comments(ready):
    store, path, _ = ready
    path.write_text('# Adam comment stays\nforms = []\n')
    decide(ready)
    first = path.read_text()
    decide(ready, index=1)
    assert path.read_text().startswith(first)
    assert path.read_text().startswith('# Adam comment stays\n')
    assert [f['number'] for f in forms.load(path)] == ['F-1', 'F-2']


@pytest.mark.parametrize('choice', ['yes', 'no'])
def test_retry_same_decision_is_idempotent_but_opposite_choice_conflicts(ready, choice):
    store, path, _ = ready
    decide(ready, choice)
    before = (path.read_bytes(), store.form_proposals())
    decide(ready, choice)
    assert (path.read_bytes(), store.form_proposals()) == before
    with pytest.raises(review.Conflict, match='already'):
        decide(ready, 'no' if choice == 'yes' else 'yes')
    assert (path.read_bytes(), store.form_proposals()) == before


def test_changed_payload_or_examples_require_reloading(ready):
    store, path, proposals = ready
    row = store.connection.execute('SELECT examples_json FROM form_night_results WHERE proposal_id=?', (proposals[0]['id'],)).fetchone()
    examples=json.loads(row[0]);examples[0]['text'] += ' changed'
    store.connection.execute('UPDATE form_night_results SET examples_json=? WHERE proposal_id=?', (json.dumps(examples), proposals[0]['id']))
    store.connection.commit()
    with pytest.raises(review.Conflict, match='changed'):
        decide(ready)
    fresh=review.pending(store,path)[0]
    assert fresh['error']
    with pytest.raises(forms.Refused, match='Saved example'):
        review.decide(store.path,path,fresh['id'],'yes',fresh['version'])
    assert forms.load(path) == []


def test_missing_examples_cannot_be_approved(ready):
    store,path,_=ready
    pid=store.save_form_proposal({'number':'F-3','status':'proposed','author':'test','date':'2026-10-02',**candidate()})
    proposal=next(p for p in review.pending(store,path) if p['id']==pid)
    with pytest.raises(forms.Refused,match='missing'):
        review.decide(store.path,path,pid,'yes',proposal['version'])


def test_unknown_or_editing_choice_does_not_change_anything(ready):
    store,path,p=ready
    with pytest.raises(review.Conflict):
        review.decide(store.path,path,'unknown','yes',p[0]['version'])
    with pytest.raises(ValueError):
        decide(ready,'edit')
    assert forms.load(path)==[] and len(review.pending(store,path))==2


def test_duplicate_number_does_not_overwrite_file(ready):
    store,path,proposals=ready
    value={**proposals[0]['payload'],'status':'approved','author':'existing different author'}
    path.write_text(review.append_text('forms = []\n',value,[]))
    before=path.read_bytes()
    with pytest.raises(review.Conflict,match='number'):
        decide(ready)
    assert path.read_bytes()==before and store.form_proposals()[0]['status']=='proposed'


def test_write_failure_leaves_proposal_and_file_unchanged(ready,monkeypatch):
    store,path,_=ready;before=path.read_bytes()
    def fail(*args): raise OSError('fixture disk full')
    monkeypatch.setattr(review.os,'replace',fail)
    with pytest.raises(OSError): decide(ready)
    assert path.read_bytes()==before and store.form_proposals()[0]['status']=='proposed'
    assert list(path.parent.glob('.forms-*.tmp'))==[]


def test_file_changed_outside_the_lock_is_preserved(ready,monkeypatch):
    store,path,_=ready
    original=review.forms.load
    def change(candidate_path,*args,**kwargs):
        result=original(candidate_path,*args,**kwargs)
        if candidate_path.name.startswith('.forms-'):
            path.write_text('# external edit\nforms = []\n')
        return result
    monkeypatch.setattr(review.forms,'load',change)
    with pytest.raises(review.Conflict,match='changed'):
        decide(ready)
    assert path.read_text()=='# external edit\nforms = []\n'
    assert store.form_proposals()[0]['status']=='proposed'


def test_file_published_before_interrupted_receipt_recovers_without_duplicate(ready):
    store,path,proposals=ready
    # Reproduce the crash boundary: human Yes was published, receipt has not committed.
    path.write_text(review.append_text(path.read_text(),review.approved_form(proposals[0]),[]))
    assert [p['number'] for p in review.pending(store,path)]==['F-2']
    with pytest.raises(review.Conflict,match='approved'): decide(ready,'no')
    before=path.read_bytes();decide(ready)
    assert path.read_bytes()==before
    assert store.form_proposals()[0]['status']=='approved'


def test_simultaneous_yes_and_no_keep_one_decision(ready):
    def choose(choice):
        try: return decide(ready,choice)
        except review.Conflict: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(choose,['yes','no']))
    assert sorted(results)==['F-1','conflict']
    store,path,_=ready
    status=store.form_proposals()[0]['status']
    assert (status=='approved')==bool(forms.load(path))


@contextmanager
def serving(ready):
    store,path,_=ready
    server=serve.make_server(0,store.path,host='127.0.0.1',forms_path=path)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield server
    finally:
        server.shutdown();thread.join(5);server.server_close();server.RequestHandlerClass.store.connection.close()


def request(server,method='GET',path='/forms',data=None,headers=None):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    c.request(method,path,body=urlencode(data) if data is not None else None,headers=headers or {})
    r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read().decode())
    c.close();return result


def fields(server,proposal,choice='yes'):
    return {'proposal_id':proposal['id'],'choice':choice,'version':proposal['version'],'token':server.RequestHandlerClass.forms_token}


@pytest.mark.parametrize('choice,expected', [('yes','approved'),('no','rejected')])
def test_browser_post_decision_redirects_and_removes_only_decided_form(ready,choice,expected):
    store,path,p=ready
    with serving(ready) as server:
        status,headers,page=request(server)
        assert status==200 and headers['cache-control']=='no-store'
        assert page.count('>Yes</button>')==page.count('>No</button>')==2
        assert '<textarea' not in page and 'contenteditable' not in page
        assert 'The rows include “depends on” and “rejects”' in page
        status,headers,_=request(server,'POST','/forms/decision',fields(server,p[0],choice),{'Content-Type':'application/x-www-form-urlencoded'})
        assert status==303 and headers['location']=='/forms'
        assert store.form_proposals()[0]['status']==expected
        _,_,page=request(server)
        assert '<h2 id="form-F-1">' not in page and '<h2 id="form-F-2">' in page


@pytest.mark.parametrize('change,expected', [('token',403),('origin',403),('edit',400),('stale',409),('choice',400),('json',400)])
def test_http_rejects_forged_stale_and_editing_requests(ready,change,expected):
    store,path,p=ready
    with serving(ready) as server:
        data=fields(server,p[0]);headers={'Content-Type':'application/x-www-form-urlencoded'}
        if change=='token':data['token']='wrong'
        elif change=='origin':headers['Origin']='http://another-site.example'
        elif change=='edit':data['sentence']='edited'
        elif change=='stale':data['version']='old'
        elif change=='choice':data['choice']='maybe'
        elif change=='json':headers['Content-Type']='application/json'
        assert request(server,'POST','/forms/decision',data,headers)[0]==expected
        assert forms.load(path)==[] and len(review.pending(store,path))==2


def test_html_escapes_quotes_and_conditions_and_has_only_two_visible_buttons_per_form(ready):
    p=ready[2][0]
    p['examples'][0]['text']='<script>alert("bad")</script>'
    page=serve.forms_page([p],'test-token')
    assert '<script>' not in page and '&lt;script&gt;' in page
    assert page.count('<button ')==2
    assert page.index('class="example"')<page.index('class="fires"')


def test_empty_page_and_original_home_page(ready):
    decide(ready,'no');decide(ready,'no',1)
    with serving(ready) as server:
        _,_,page=request(server)
        assert 'No forms waiting for your yes.' in page and '<button' not in page
        _,_,page=request(server,path='/')
        assert page==serve.PAGE.replace('__NAMES__',json.dumps(serve.STEP_NAMES)).replace('__TITLE__',serve.explain_module.TITLE)


def test_startup_defaults_and_explicit_copy_configuration(tmp_path):
    defaults=serve.parse_args([])
    assert defaults.port==8766 and defaults.store==STORE_PATH
    custom=serve.parse_args(['--port','8767','--store',str(tmp_path/'copy.sqlite3')])
    assert custom.port==8767 and custom.store==tmp_path/'copy.sqlite3'
    for port in ['0','-1','65536']:
        with pytest.raises(SystemExit):serve.parse_args(['--port',port])


def test_two_servers_are_isolated_and_occupied_port_does_not_open_a_database(ready,tmp_path,monkeypatch):
    with serving(ready) as first:
        second=serve.make_server(0,tmp_path/'other.sqlite3',host='127.0.0.1',forms_path=tmp_path/'other-forms.txt')
        try:
            assert first.RequestHandlerClass.store.path!=second.RequestHandlerClass.store.path
            assert first.RequestHandlerClass.forms_path!=second.RequestHandlerClass.forms_path
            monkeypatch.setattr(serve,'Store',lambda *a,**k:pytest.fail('must bind port before opening a store'))
            with pytest.raises(OSError):serve.make_server(first.server_port,STORE_PATH,host='127.0.0.1')
        finally:
            second.server_close();second.RequestHandlerClass.store.connection.close()


@pytest.mark.parametrize('condition,wording', [
    ({'record_count':{'min':2,'max':5}},'2 to 5 rows'),
    ({'word_count':{'min':2}},'At least 2 words'),
    ({'record_count':{'max':8}},'At most 8 rows'),
    ({'kinds_absent':['rejects']},'The rows leave out “rejects”'),
    ({'missing_links':True},'A word has missing links'),
    ({'missing_links':False},'Every word has links'),
    ({'missing_why':True},'A why line says what the records do not show'),
    ({'missing_why':False},'No why line says the records are missing something'),
])
def test_conditions_in_plain_words(condition,wording):
    assert review.fires_when(condition)==wording


def test_night_reads_yes_as_approved_and_preserves_the_original_payload(ready):
    from nucleus.forms_night import report
    store,path,p=ready
    run_id=store.connection.execute('SELECT run_id FROM form_night_results WHERE proposal_id=?',(p[0]['id'],)).fetchone()[0]
    decide(ready)
    result=report(store,run_id)
    saved=next(r for r in result['results'] if r['proposal_id']==p[0]['id'])
    assert saved['form']['status']=='approved' and saved['payload']['status']=='proposed'
    assert run(store,[])['prior_proposals_refused']==[]


def test_database_receipt_failure_reports_an_error_and_retry_recovers(ready,monkeypatch):
    store,path,p=ready
    original=review.Store
    class FailReceipt(Store):
        def __init__(self,path):
            super().__init__(path)
            self.connection.execute("CREATE TRIGGER fail_approval BEFORE INSERT ON form_approvals BEGIN SELECT RAISE(ABORT, 'test receipt failure'); END")
    monkeypatch.setattr(review,'Store',FailReceipt)
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):decide(ready)
    assert len(forms.load(path))==1
    assert store.form_proposals()[0]['status']=='proposed'
    store.connection.execute('DROP TRIGGER fail_approval');store.connection.commit()
    monkeypatch.setattr(review,'Store',original)
    decide(ready)
    assert len(forms.load(path))==1 and store.form_proposals()[0]['status']=='approved'
