"""Safe orchestrator for the existing project's new Facebook-only active path."""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from bsd.common import ROOT,config,digest,enabled,safe_error,write_json,duration
from bsd.schedule import due,job_key
from bsd.ledger import Ledger
from bsd.stories import choose
from bsd.narration import narrate
from bsd.footage import Footage
from bsd.cinematic import render,quality
from bsd.facebook import Facebook


def image_post(slot, history, folder):
    from agents.content_agent import ContentAgent, SLOT_CATEGORY
    category=SLOT_CATEGORY[slot]
    agent=ContentAgent()
    # Reuse existing libraries/theme helpers without consuming the old state.
    if category=='bible_quotes':
        from agents import world_bible_agent as bible
        source=ROOT/'data/state/bible_used.json'
        state=folder/'bible_used.json'
        used=json.loads(source.read_text()) if source.exists() else []
        used+= [h['bible_reference'] for h in history if h.get('bible_reference')]
        state.write_text(json.dumps(sorted(set(used))))
        with patch.object(bible,'STATE_FILE',state):
            result=bible.build_bible_post({'slot':slot,'content_index':0})
        result['reference']=result['bible_reference']
        return result
    items=agent._load_category(category)
    previous=set(agent.state.get('posted',{}).get(category,[]))
    seen={digest(h.get('content','')) for h in history}
    indices=[i for i in range(len(items)) if i not in previous and digest(items[i]) not in seen]
    if not indices: raise RuntimeError('Image library exhausted; no automatic reset')
    i=random.choice(indices)
    return {'slot':slot,'category':category,'content':items[i],'content_index':i,
            'visual_theme':agent._pick_visual_theme(category,items[i])}


def run_slot(slot, day, dry_run=True):
    started=time.monotonic();key=job_key(slot,day)
    folder=ROOT/'artifacts'/day/slot['name'];folder.mkdir(parents=True,exist_ok=True)
    ledger=None; payload={}; live_started=False
    if not dry_run:
        if not enabled('BSD_ENABLE_PUBLISH'): raise RuntimeError('Live publishing is disabled')
        if slot['format']=='REELS' and not enabled('BSD_ENABLE_REELS'):
            return {'skipped':True,'reason':'Reels await approved visual/live validation'}
        ledger=Ledger()
        if not ledger.claim(key):
            existing=ledger.get(key)
            # Retry ONLY a known pre-publication failure. Claim is compare-and-set.
            attempts=existing.get('payload',{}).get('attempts',1) if existing else 1
            if not existing or existing['status']!='failed_preflight' or attempts>=2:
                return {'skipped':True,'reason':'Existing job; reconcile if uncertain','job_key':key}
            rows=ledger.request('PATCH','bsd_jobs',params={'job_key':'eq.'+key,'status':'eq.failed_preflight'},
                                json={'status':'claimed'})
            if not rows: return {'skipped':True,'reason':'Another worker claimed retry'}
            payload=existing['payload'];payload['attempts']=attempts+1
        else: payload={'attempts':1}
    try:
        history=[j['payload'].get('post',{}) for j in ledger.jobs(days=3650)] if ledger else []
        # Dry preview never writes a production history, ledger, asset reservation or Facebook API.
        post=payload.get('post') or (choose(slot['name'],history) if slot['format']=='REELS'
                                        else image_post(slot['name'],history,folder))
        post['date']=day;post['posting_time']=slot['time'];post['timezone']=config()['timezone']
        payload.update({'post':post,'format':slot['format'],'job_key':key})
        if ledger: ledger.update(key,'rendering',payload,content_hash=digest(post['content']))
        if slot['format']=='REELS':
            voice,marks,voice_meta=narrate(post['content'],folder,post.get('style','warm'))
            source=Footage(ROOT/'.cache/bsd-footage',ledger,key)
            clips=[];provenance=[]
            for query in post['queries']:
                path,metadata=source.choose(query,min_seconds=max(9,(duration(voice)+2.15)/3))
                clips.append(path);provenance.append(metadata)
            asset,manifest=render(post,clips,voice,marks,folder,voice_meta,provenance)
            payload['qc']=quality(asset,manifest)
            payload['duration']=manifest['duration'];payload['voice']=voice_meta
            payload['footage']=provenance
            source.prune()
        else:
            from generators.pexels_photo_generator import PexelsPhotoGenerator
            from PIL import Image
            asset=Path(PexelsPhotoGenerator().generate(post,folder/'image.jpg'))
            with Image.open(asset) as image:
                image.verify()
            with Image.open(asset) as image:
                if image.size!=(1080,1080): raise ValueError('Invalid image resolution')
        write_json(folder/'preview.json',payload)
        if dry_run: return {'success':True,'dry_run':True,'artifact':str(asset)}
        ledger.update(key,'ready',payload)
        def checkpoint(stage, update):
            nonlocal live_started
            # Set before attempting durable update; failed checkpoint means no remote mutation.
            # Hold on any ambiguity rather than risking a second submission.
            live_started=True
            payload.update(update);payload['stage']=stage
            ledger.update(key,stage,payload)
        caption=post['content']+'\n\n#BrightSideDaily #'+post['category'].replace('_','').title()
        publisher=Facebook(checkpoint)
        media_id=publisher.reel(asset,caption) if slot['format']=='REELS' else publisher.photo(asset,caption)
        return {'success':True,'media_id':media_id,'job_key':key}
    except Exception as exc:
        payload['error']=safe_error(exc)
        payload['stage_at_failure']=payload.get('stage','preflight')
        if ledger:
            try: ledger.update(key,'uncertain' if live_started else 'failed_preflight',payload)
            except Exception: pass # existing durable checkpoint stays reserved
        write_json(folder/'failure.json',payload)
        raise RuntimeError(payload['error']) from None
    finally:
        write_json(folder/'execution.json',{'elapsed_seconds':round(time.monotonic()-started,2),
            'artifact_bytes':sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),'dry_run':dry_run})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--slot',choices=[s['name'] for s in config()['slots']])
    parser.add_argument('--due',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--schedule',action='store_true')
    args=parser.parse_args()
    if args.schedule:
        print(json.dumps(config()['slots'],indent=2));return 0
    dry=args.dry_run or not enabled('BSD_ENABLE_PUBLISH') or enabled('DRY_RUN')
    if args.slot:
        from zoneinfo import ZoneInfo
        day=datetime.now(ZoneInfo(config()['timezone'])).date().isoformat()
        selected=[(next(s for s in config()['slots'] if s['name']==args.slot),day)]
    elif args.due: selected=due()
    else: parser.error('Choose --slot, --due or --schedule')
    failed=False
    for slot,day in selected:
        try: print(json.dumps(run_slot(slot,day,dry)))
        except Exception as exc:
            print(json.dumps({'success':False,'slot':slot['name'],'error':safe_error(exc)}));failed=True
    return 1 if failed else 0
