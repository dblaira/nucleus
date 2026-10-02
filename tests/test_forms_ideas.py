"""The most useful measured version of one idea waits; human decisions stay exact."""
from copy import deepcopy
import json

from nucleus import forms, forms_night as night
from test_forms_night import copy, candidate, history, miss, model_reply, run, painted, KINDS


def test_same_middle_words_one_form(copy):
    history(copy)
    miss(copy)
    narrow = candidate(when={**candidate()['when'], 'record_count': {'min': 2, 'max': 3}})
    wide = candidate(when={**candidate()['when'], 'record_count': {'min': 2}})
    result = run(copy, [narrow, wide])
    assert result['proposed'] == 1
    assert result['results'][1]['reason'] == 'same form'  # Equal coverage keeps the earlier number.
    assert night.idea(result['results'][0]['form']) == night.idea(result['results'][1]['form'])
    assert night.signature(result['results'][0]['form']) != night.signature(result['results'][1]['form'])


def test_best_coverage_wins_even_when_newer(copy):
    history(copy)
    miss(copy)
    qid = painted(copy, 'MOMENTUM')
    # This fourth screen has three rows, still using the same quoted middle words.
    reply = json.loads(copy.connection.execute('SELECT reply_json FROM answers WHERE question_id=?',(qid,)).fetchone()[0])
    reply['records'].append({'id':'r3','quote':'Third quote'})
    copy.connection.execute("UPDATE answers SET text=text || ?,reply_json=? WHERE question_id=?",
        ('\n\n0.70 — MOMENTUM supports “Third quote”', json.dumps(reply), qid))
    copy.connection.commit()
    narrow = candidate(when={**candidate()['when'], 'record_count': {'min': 2, 'max': 3}})
    # A wider form later gets another four-row screen.
    assert run(copy, [narrow])['proposed'] == 1
    qid = painted(copy, 'VALUE')
    reply = json.loads(copy.connection.execute('SELECT reply_json FROM answers WHERE question_id=?',(qid,)).fetchone()[0])
    reply['records'] += [{'id':'r3','quote':'Third quote'},{'id':'r4','quote':'Fourth quote'}]
    copy.connection.execute("UPDATE answers SET text=text || ?,reply_json=? WHERE question_id=?",
        ('\n\n0.70 — VALUE supports “Third quote”\n\n0.60 — VALUE requires “Fourth quote”', json.dumps(reply),qid))
    copy.connection.commit()
    miss(copy, 'LIFT')
    second = run(copy, [candidate(when={**candidate()['when'], 'record_count': {'min': 2}})])
    proposals = copy.form_proposals()
    assert second['proposed'] == 1
    assert proposals[0]['status'] == 'rejected' and proposals[0]['reason'] == 'same form'
    assert proposals[1]['status'] == 'proposed'
    assert second['prior_proposals_refused'][0]['reason'] == 'same form'


def test_human_yes_and_no_are_preserved(copy):
    history(copy)
    miss(copy)
    first = run(copy)
    pid = first['results'][0]['proposal_id']
    copy.reject_form_proposal(pid, 'Adam said no on /forms.')
    before = deepcopy(copy.form_proposals()[0])
    miss(copy, 'LIFT')
    wider = candidate(when={**candidate()['when'], 'record_count': {'min': 0}})
    result = run(copy, [wider])
    assert result['results'][0]['reason'] == 'same form'
    assert copy.form_proposals()[0] == before


def test_approved_idea_kept_even_if_new_form_fits_more(copy):
    history(copy)
    miss(copy)
    from nucleus.forms_review import append_text
    approved = {'number':'F-1','status':'approved','author':'Adam','date':'2026-10-02',
                **candidate(when={**candidate()['when'], 'record_count':{'min':2,'max':3}})}
    forms.FORMS_PATH.write_text(append_text(forms.FORMS_PATH.read_text(), approved, []))
    original = forms.FORMS_PATH.read_bytes()
    result = run(copy,[candidate()])
    assert result['results'][0]['reason'] == 'same form'
    assert forms.FORMS_PATH.read_bytes() == original


def test_answer_and_quoted_kinds_both_define_idea():
    base = candidate()
    assert night.idea(base) == night.idea(candidate(sentence='{word} rejects “{quote:rejects}” and depends on “{quote:depends on}”.'))
    assert night.idea(base) != night.idea(candidate(when={**base['when'],'answer':'not_sure'}))
    assert night.idea(base) != night.idea(candidate(sentence='{word} supports “{quote:supports}” and rejects “{quote:rejects}”.'))


def test_different_quoted_middle_words_can_share_conditions(copy):
    history(copy)
    miss(copy)
    for qid, reply, text in copy.connection.execute('SELECT question_id,reply_json,text FROM answers').fetchall():
        payload=json.loads(reply)
        word=payload['words'][0]['word']
        payload['records'].append({'id':'r3','quote':'Third quote'})
        copy.connection.execute('UPDATE answers SET text=?,reply_json=? WHERE question_id=?',
            (text+'\n\n0.70 — '+word+' supports “Third quote”',json.dumps(payload),qid))
    # Remove the old row-only miss so every source snapshot contains all three rows.
    copy.connection.execute('DELETE FROM form_misses')
    copy.connection.commit()
    when={'answer':'aligned','kinds_present':['depends on','rejects','supports']}
    first=candidate(when=when)
    other=candidate(when=when,sentence='{word} supports “{quote:supports}” and rejects “{quote:rejects}”.')
    result=run(copy,[first,other],bootstrap=True)
    assert result['proposed']==2 and result['refused']==0


def test_rejected_different_quoted_middle_words_do_not_block(copy):
    history(copy)
    miss(copy)
    when={**candidate()['when'],'kinds_present':['depends on','supports','rejects']}
    old={'number':'F-1','status':'proposed','author':'old','date':'2026-10-02',
         **candidate(when=when,sentence='{word} supports “{quote:supports}” and rejects “{quote:rejects}”.')}
    copy.save_form_proposal(old,'old refusal')
    # Direct checker isolates the repeat key; missing supports means a clean miss,
    # never a false same-form refusal for a different idea.
    form,reason,matches=night.checked(candidate(when=when),'F-2','new',night.past_answers(copy,KINDS),KINDS,{night.repeat_key(old)})
    assert reason=='fits too few answers'


def test_real_label_census_counts_a_repeated_question_once(copy,monkeypatch):
    from types import SimpleNamespace
    from nucleus import dictionary, graph_answers, phrases
    copy.new_question(' What is FLOW? ', 'web')
    copy.new_question('what is flow?', 'cowboyai-iphone')
    copy.new_question('What is LIFT?', 'web')
    copy.new_question('What is FLOW? but unknown?', 'practice')
    monkeypatch.setattr(dictionary,'brief',lambda q:{'outcome':'ready'})
    monkeypatch.setattr(phrases.PhraseIndex,'lookup',lambda *a:[])
    monkeypatch.setattr(graph_answers,'label_question',lambda q,e,**kw:SimpleNamespace(
        budget_miss=False,to_dict=lambda:{'answer':'aligned'}))
    engine=SimpleNamespace(meanings=[],legacy_graph=SimpleNamespace(records={}))
    census=night.real_graph_labels(copy,engine)
    assert census['different_questions']==2
    assert census['labels']=={'aligned':2,'middle':0,'dont_know':0}


def test_real_label_census_preserves_dictionary_stop(copy,monkeypatch):
    from types import SimpleNamespace
    from nucleus import dictionary, graph_answers
    copy.new_question('What is FLOW?', 'web')
    monkeypatch.setattr(dictionary,'brief',lambda q:{'outcome':'ask'})
    monkeypatch.setattr(graph_answers,'label_question',lambda *a,**k:__import__('pytest').fail('must not label a stopped question'))
    census=night.real_graph_labels(copy,SimpleNamespace(meanings=[],legacy_graph=SimpleNamespace(records={})))
    assert census['refused']==1
    assert census['labels']=={'aligned':0,'middle':0,'dont_know':0}


def test_invalid_first_frame_cannot_suppress_a_valid_same_idea(copy):
    history(copy)
    miss(copy)
    bad = candidate(sentence='You should use {word} depends on “{quote:depends on}” and rejects “{quote:rejects}”.')
    result = run(copy,[bad,candidate()])
    assert result['proposed']==1
    assert 'advice' in result['results'][0]['reason']
    assert result['results'][1]['reason'] is None


def test_semantic_refusal_cannot_win_against_valid_same_idea(copy):
    from nucleus.model import ModelReply
    from nucleus import forms_patterns
    history(copy)
    miss(copy)
    def call(prompt, *, schema):
        if schema != forms_patterns.REVIEW_SCHEMA:
            return model_reply([candidate(),candidate(when={**candidate()['when'],'record_count':{'min':0}})])(prompt,schema=schema)
        batch=json.loads(prompt.split('\nCandidates:\n')[1])
        return ModelReply('test','review',json.dumps({'reviews':[
            {'number':c['form']['number'],'verdict':'unsupported_meaning' if i==0 else 'explains_pattern',
             'reading_grade':3,'one_sentence':True,'reason':'fixture verdict'} for i,c in enumerate(batch)]}))
    result=night.night(copy.path,practice=False,model_call=call)
    assert result['proposed']==1
    assert result['results'][0]['reason'].startswith('unsupported pattern meaning')
    assert result['results'][1]['reason'] is None


def test_resumed_writer_failure_cannot_rewrite_earlier_attempt(copy):
    import time
    from nucleus import forms_patterns
    history(copy)
    miss(copy)
    def failed(*a,**k):raise TimeoutError('original writer timeout')
    first=night.night(copy.path,practice=False,model_call=failed)
    run_id=first['run_id']
    previous=copy.connection.execute('SELECT rowid,ok,error,prompt FROM model_calls WHERE question_id=?',('forms-night:'+run_id,)).fetchone()
    copy.connection.execute("UPDATE form_night_runs SET status='running' WHERE id=?",(run_id,));copy.connection.commit()
    def failed_review(prompt,*,schema):
        if schema==forms_patterns.REVIEW_SCHEMA:raise TimeoutError('later review timeout')
        return model_reply([candidate()])(prompt,schema=schema)
    result=night._propose(copy,run_id,time.time(),False,forms.FORMS_PATH,failed_review,(),False)
    assert result['status']=='failed' and 'later review timeout' in result['error']
    assert copy.connection.execute('SELECT rowid,ok,error,prompt FROM model_calls WHERE rowid=?',(previous[0],)).fetchone()==previous
