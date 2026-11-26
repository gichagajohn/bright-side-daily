import json
import pytest
from PIL import ImageFont
from bsd.common import ROOT
from bsd.editorial import script_marks,phrase_groups,wrap_balanced,emphasized,footage_score
from bsd.cinematic import FONT,captions
from bsd.stories import choose

SCRIPT=('A missed bus can make the whole morning feel ruined. You check the time again. '
        'You replay the minute you spent searching for your keys. But the next ten minutes '
        'do not have to become another argument with yourself. Let someone know you are delayed. '
        'Take a breath. Decide what is still within your control. '
        'A rough beginning does not have to write the rest of your day.')

def recognized():
    return [{'text':w.replace('spent','spend').replace('ten','10'),'start':i*.3,'end':i*.3+.25}
            for i,w in enumerate(SCRIPT.split())]

def test_corrects_reported_asr_error_without_changing_timing():
    original=recognized();fixed,changes=script_marks(SCRIPT,original)
    assert ' '.join(m['text'] for m in fixed)==SCRIPT
    assert [(m['start'],m['end']) for m in fixed]==[(m['start'],m['end']) for m in original]
    assert any(c['script']=='spent' and c['recognized']=='spend' for c in changes)
    assert any(c['script']=='ten' and c['recognized']=='10' for c in changes)
    assert original[20]['text']=='spend'

def test_missing_word_withheld():
    with pytest.raises(ValueError):script_marks(SCRIPT,recognized()[:-1])

def test_meaning_change_withheld():
    marks=recognized();marks[0]['text']='Never'
    with pytest.raises(ValueError):script_marks(SCRIPT,marks)

def test_sentence_boundaries_and_exact_caption_text(tmp_path):
    marks,_=script_marks(SCRIPT,recognized())
    groups=phrase_groups(marks)
    assert all(not any(m['text'].endswith('.') for m in g[:-1]) for g in groups)
    assert all(g[-1]['text'].lower() not in {'the','you','are'} for g in groups)
    ass,bounds=captions(marks,tmp_path,25,['missed bus'])
    assert ' '.join(b['text'] for b in bounds)==SCRIPT
    assert 'make' not in [w for b in bounds for w in b['highlighted_words']]
    assert all(len(b['lines'])<=2 for b in bounds)

def test_pause_starts_new_group():
    marks=[{'text':'Keep','start':0,'end':.4},{'text':'going','start':1,'end':1.4}]
    assert len(phrase_groups(marks))==2

def test_balanced_lines_avoid_single_word_tail():
    rows=wrap_balanced('You replay the minute you'.split(),ImageFont.truetype(FONT,54))
    assert len(rows)==2 and all(len(r)>1 for r in rows)

def test_meaningful_emphasis():
    assert emphasized('A missed bus can make'.split(),['missed bus'])=={1,2}
    assert emphasized(['make'])==set()

def test_title_filter_rejects_reported_mismatch():
    assert footage_score({'url':'https://www.pexels.com/video/vibrant-city-street-at-sunset-35301986/'},'sunrise street') is None
    assert footage_score({'url':'https://www.pexels.com/video/morning-walk-near-istanbul-s-new-mosque-40450802/'},
                         'commuter waiting bus stop',{'required_any':['bus','commuter']}) is None
    assert footage_score({'url':'https://www.pexels.com/video/commuter-waiting-at-bus-stop-123/'},
                         'commuter waiting bus stop',{'required_any':['bus','commuter']})>0

def test_select_same_preview_story(monkeypatch):
    monkeypatch.delenv('BSD_LOCAL_MODEL',raising=False)
    post=choose('morning_motivation',[],'bsd-story-010')
    assert post['id']=='bsd-story-010' and post['queries'][0]=='commuter waiting bus stop'
    with pytest.raises(ValueError):choose('morning_motivation',[],'unknown-id')
