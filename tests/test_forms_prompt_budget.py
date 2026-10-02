"""Sampling may omit whole writer inputs; it never clips a source or lowers coverage."""
from copy import deepcopy
import json

from nucleus import forms_night as night


def sample(word, question, surface='web', answer='not_sure', quote='Whole exact source.'):
    return {'question_id':question,'question':question,'surface':surface,
            'screen':{'answer':answer,'words':[word], 'rows':[{'word':word,'record':'r','kind':'supports','quote':quote}],
                      'parts':[], 'missing_links':False}}


def test_writer_packet_stays_bounded_without_clipping_quotes(monkeypatch):
    monkeypatch.setattr(night,'PROMPT_LIMIT',20000)
    raw=[sample('FLOW',f'Question {i}',quote='Exact whole quote. '+('x'*5000)+str(i)) for i in range(20)]
    inputs=[{'source':'past_answer',**s} for s in raw]
    original=deepcopy(inputs)
    prompt=night.make_prompt(inputs,[],['supports'])
    selected=json.loads(prompt.split('\nSaved screens:\n')[1])
    assert 0<len(selected)<len(inputs) and len(prompt)<=night.PROMPT_LIMIT
    for s in selected:
        assert s in raw
        assert s['screen']['rows'][0]['quote'].startswith('Exact whole quote. ')
        assert len(s['screen']['rows'][0]['quote'])>5000
    assert inputs==original


def test_round_robin_includes_real_practice_and_different_words():
    real=[sample('FLOW',f'FLOW {i}') for i in range(20)]
    more=[sample('LIFT','LIFT one'),sample('FLOW','Practice one','practice')]
    selected=night.bounded_screens(real+more,1500)
    assert any(s['surface']=='practice' for s in selected)
    assert {s['screen']['words'][0] for s in selected}=={'FLOW','LIFT'}
    assert any(s['surface']=='web' for s in selected)


def test_oversized_screen_is_omitted_whole():
    big=sample('FLOW','Big',quote='x'*100000)
    small=sample('LIFT','Small')
    assert night.bounded_screens([big,small],1000)==[small]
