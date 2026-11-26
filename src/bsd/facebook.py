"""Facebook-only transport. Every remote mutation has a durable checkpoint.
Docs: developers.facebook.com/docs/graph-api/reference/page/video_reels/
Do not treat accepted uploads as published. Never replay ambiguous mutations.
"""
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

class Facebook:
    def __init__(self, checkpoint):
        self.page=os.environ['FB_PAGE_ID'].strip()
        version=os.environ.get('FB_API_VERSION','v26.0')
        if not re.fullmatch(r'v\d+\.0',version): raise ValueError('Invalid Graph version')
        self.base='https://graph.facebook.com/'+version
        self.token=os.environ['FB_PAGE_ACCESS_TOKEN'].strip()
        self.session=requests.Session()
        self.session.headers['Authorization']='Bearer '+self.token
        self.checkpoint=checkpoint

    def request(self, method, endpoint, **kw):
        url=self.base+'/'+endpoint
        for attempt in range(3 if method=='GET' else 1):
            try:
                r=self.session.request(method,url,timeout=120,**kw)
            except requests.RequestException:
                if method=='GET' and attempt<2:
                    time.sleep(2**attempt);continue
                raise RuntimeError('Meta connection failure; mutation status may be unknown') from None
            if method=='GET' and r.status_code in (429,500,502,503) and attempt<2:
                time.sleep(2**attempt);continue
            try: body=r.json()
            except ValueError: raise RuntimeError('Meta returned invalid JSON') from None
            if not r.ok or 'error' in body:
                code=body.get('error',{}).get('code','unknown')
                raise RuntimeError(f'Meta HTTP {r.status_code}; code {code}')
            return body

    def photo(self, path, caption):
        self.checkpoint('photo_submitting',{})
        with open(path,'rb') as f:
            data=self.request('POST',self.page+'/photos',data={'caption':caption},files={'source':f})
        post_id=data.get('post_id') or data.get('id')
        if not post_id: raise RuntimeError('Photo response has no ID')
        self.checkpoint('published',{'media_id':str(post_id),'media_type':'IMAGE'})
        return str(post_id)

    def reel(self, path, caption):
        self.checkpoint('reel_starting',{})
        data=self.request('POST',self.page+'/video_reels',data={'upload_phase':'start'})
        vid=str(data['video_id']); url=data['upload_url']
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='rupload.facebook.com':
            raise RuntimeError('Untrusted upload URL')
        self.checkpoint('reel_uploading',{'media_id':vid,'media_type':'REELS'})
        # Direct binary upload removes temporary public storage and early-deletion races.
        with open(path,'rb') as f:
            try:
                r=requests.post(url,headers={'Authorization':'OAuth '+self.token,'offset':'0',
                    'file_size':str(Path(path).stat().st_size),'Content-Type':'application/octet-stream'},
                    data=f,timeout=240)
            except requests.RequestException:
                raise RuntimeError('Reel upload uncertain; inspect recorded video ID') from None
        if not r.ok or not r.json().get('success'): raise RuntimeError('Reel upload rejected')
        self.checkpoint('reel_finishing',{'media_id':vid,'media_type':'REELS'})
        self.request('POST',self.page+'/video_reels',data={'upload_phase':'finish','video_id':vid,
                      'video_state':'PUBLISHED','description':caption})
        self.checkpoint('reel_processing',{'media_id':vid,'media_type':'REELS'})
        for _ in range(36):
            status=self.request('GET',vid,params={'fields':'status'}).get('status',{})
            phase=status.get('publishing_phase',{}).get('status')
            if phase=='complete':
                self.checkpoint('published',{'media_id':vid,'media_type':'REELS'})
                return vid
            if phase=='error' or status.get('video_status')=='error':
                raise RuntimeError('Remote Reel processing failed; inspect recorded ID')
            time.sleep(5)
        raise RuntimeError('Remote Reel not confirmed before polling deadline; reconcile recorded ID')
