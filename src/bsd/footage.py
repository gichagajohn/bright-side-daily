"""Pexels video assets with source metadata, cache and atomic reuse claims."""
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bsd.common import config, file_hash, probe

class Footage:
    def __init__(self, cache, ledger=None, job_key=None):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.ledger=ledger;self.key=job_key
        self.session=requests.Session()
        self.session.mount('https://',HTTPAdapter(max_retries=Retry(total=2,backoff_factor=1,
            status_forcelist=[429,500,502,503],allowed_methods=['GET'])))
        self.used=ledger.recent_clips(config()['reels']['clip_cooldown_days']) if ledger else set()

    def choose(self, query, min_seconds=9):
        key=os.environ.get('PEXELS_API_KEY')
        if not key: raise RuntimeError('PEXELS_API_KEY required for footage')
        for page in random.sample(range(1,6),5):
            r=self.session.get('https://api.pexels.com/videos/search',headers={'Authorization':key},
                params={'query':query,'orientation':'portrait','per_page':30,'page':page},timeout=30)
            if not r.ok: raise RuntimeError('Pexels HTTP '+str(r.status_code))
            clips=r.json().get('videos',[]);random.shuffle(clips)
            for clip in clips:
                cid=str(clip['id'])
                if cid in self.used or clip.get('duration',0)<min_seconds: continue
                options=[f for f in clip.get('video_files',[]) if f.get('file_type')=='video/mp4'
                         and (f.get('width') or 0)>=1080 and (f.get('height') or 0)>=1920]
                if not options: continue
                variant=min(options,key=lambda f:f['width']*f['height'])
                url=variant['link'];parsed=urlparse(url)
                if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.pexels.com'): continue
                provenance={'id':cid,'source_url':clip['url'],'creator':clip.get('user',{}).get('name'),
                    'license_url':'https://www.pexels.com/license/','provider':'pexels','query':query,
                    'retrieved_at':datetime.now(timezone.utc).isoformat(),
                    'rights_note':'Pexels licence; no endorsement implied. Review identifiable people/brands.'}
                path=self.cache/(cid+'.mp4')
                if not path.exists():
                    temp=path.with_suffix('.part');size=0
                    try:
                        with self.session.get(url,stream=True,timeout=(10,60)) as response:
                            if not response.ok: raise RuntimeError('Footage download failed')
                            with open(temp,'wb') as f:
                                for chunk in response.iter_content(1048576):
                                    size+=len(chunk)
                                    if size>150_000_000: raise ValueError('Source clip too large')
                                    f.write(chunk)
                        probe(temp);temp.replace(path)
                    finally: temp.unlink(missing_ok=True)
                try: probe(path)
                except Exception:
                    path.unlink(missing_ok=True);continue
                provenance['sha256']=file_hash(path)
                if self.ledger and not self.ledger.reserve_clip(provenance,self.key,config()['reels']['clip_cooldown_days']):
                    continue
                self.used.add(cid)
                return path,provenance
        raise RuntimeError('No fresh suitable licensed footage; skip rather than repeat')

    def prune(self, max_bytes=800_000_000):
        files=sorted(self.cache.glob('*.mp4'),key=lambda p:p.stat().st_mtime,reverse=True)
        total=0
        for path in files:
            total+=path.stat().st_size
            if total>max_bytes: path.unlink()
