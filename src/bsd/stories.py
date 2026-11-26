"""Story-first scripts: vetted seeds + optional free local Ollama generation.
No paid APIs. Seed exhaustion fails closed, never silently recycles narratives.
"""
import json
import os
import random
import re
from difflib import SequenceMatcher
from bsd.common import ROOT, digest

CATEGORIES=['life_lessons','motivational_storytelling','personal_growth','discipline_consistency',
            'overcoming_challenges','emotional_intelligence','relationships_kindness','gratitude',
            'faith_encouragement','everyday_experiences']
BANNED=['unlock your potential','in a world where','embrace the journey','unleash your','game changer']

def text(story): return ' '.join(story[k].strip() for k in ('hook','body','conclusion'))

def validate(story, history):
    if story.get('category') not in CATEGORIES: raise ValueError('Unknown narrative category')
    script=text(story)
    if not 45<=len(script.split())<=90: raise ValueError('Script length outside narrative budget')
    if any(s in script.lower() for s in BANNED): raise ValueError('Generic script expression')
    if len(story.get('queries',[]))!=3 or any(not isinstance(q,str) or len(q)>120 for q in story['queries']):
        raise ValueError('Three safe visual queries required')
    # Generated devotional prose may not introduce quotations or verse references.
    if story['category']=='faith_encouragement' and re.search(r'\d+:\d+|[“”"]',script):
        raise ValueError('Scripture quotations require a separately vetted source')
    for old in history:
        prior=old.get('content','')
        if digest(script)==digest(prior) or SequenceMatcher(None,script.lower(),prior.lower()).ratio()>0.72:
            raise ValueError('Repeated narrative')
        if old.get('hook','').lower()==story['hook'].lower(): raise ValueError('Repeated hook')
    return script

def choose(slot, history):
    seeds=json.loads((ROOT/'content/reel_stories.json').read_text())['stories']
    random.shuffle(seeds)
    # Prefer underrepresented categories; do not change daily frequency.
    counts={c:sum(h.get('category')==c for h in history) for c in CATEGORIES}
    seeds.sort(key=lambda s:counts[s['category']])
    candidates=seeds
    if os.environ.get('BSD_LOCAL_MODEL'):
        # Explicit opt-in for a local open-source model. No arbitrary remote API URLs.
        import requests
        category=min(counts,key=counts.get)
        prompt=('Write one original warm motivational micro-story, 55 to 70 English words total. '
                'Use a concrete everyday situation, a hook, a meaningful middle, and a gentle conclusion. '
                'No invented true events, Bible quotations, medical promises or generic motivational slogans. '
                'Return JSON only with category, title, hook, body, conclusion, queries (three Pexels visual '
                'search phrases), style (warm, reflective or encouraging). Category: '+category+
                '. Avoid these recent hooks: '+json.dumps([h.get('hook') for h in history[-20:]]))
        try:
            r=requests.post('http://127.0.0.1:11434/api/generate',json={'model':os.environ['BSD_LOCAL_MODEL'],
                'prompt':prompt,'stream':False,'format':'json'},timeout=180)
            r.raise_for_status(); candidate=json.loads(r.json()['response'])
            candidate['source']='local model draft';candidates=[candidate]+seeds
        except Exception: pass  # vetted unseen seeds remain the only fallback
    for story in candidates:
        try: script=validate(story,history)
        except (ValueError,KeyError,TypeError): continue
        return {**story,'slot':slot,'content':script,'content_hash':digest(script)}
    raise RuntimeError('No original unused story available; replenish reviewed seeds or enable a local model')
