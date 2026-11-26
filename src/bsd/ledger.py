"""Durable, unique job claims. Ambiguous publishing is NEVER retried blindly."""
import os
import time
from datetime import datetime, timezone, timedelta
import requests

class Ledger:
    def __init__(self):
        self.url = os.environ['SUPABASE_URL'].strip().rstrip('/') + '/rest/v1/'
        key = os.environ['SUPABASE_SERVICE_KEY'].strip()
        self.session = requests.Session()
        self.session.headers.update({'apikey':key, 'Authorization':'Bearer '+key,
                                     'Prefer':'return=representation'})

    def request(self, method, table, **kw):
        # Retry reads only. A failed write acknowledgement requires inspection.
        for attempt in range(3 if method == 'GET' else 1):
            try:
                r = self.session.request(method, self.url+table, timeout=30, **kw)
            except requests.RequestException:
                if method == 'GET' and attempt < 2:
                    time.sleep(2**attempt); continue
                raise RuntimeError('Ledger connection failed') from None
            if r.status_code == 409: return None
            if r.status_code >= 500 and method == 'GET' and attempt < 2:
                time.sleep(2**attempt); continue
            if not r.ok: raise RuntimeError('Ledger HTTP '+str(r.status_code))
            return r.json() if r.content else []

    def claim(self, key):
        return self.request('POST','bsd_jobs',json={'job_key':key}) is not None

    def get(self, key):
        rows = self.request('GET','bsd_jobs',params={'job_key':'eq.'+key,'select':'*'})
        return rows[0] if rows else None

    def update(self, key, status, payload, content_hash=None):
        data={'status':status,'payload':payload,'updated_at':datetime.now(timezone.utc).isoformat()}
        if content_hash: data['content_hash']=content_hash
        rows=self.request('PATCH','bsd_jobs',params={'job_key':'eq.'+key},json=data)
        if not rows: raise RuntimeError('Job update refused (duplicate content or missing job)')

    def jobs(self, days=90):
        since=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        rows=[]; offset=0
        while True:
            page=self.request('GET','bsd_jobs',params={'created_at':'gte.'+since,'select':'*',
                              'order':'created_at.asc,job_key.asc','limit':500,'offset':offset})
            rows.extend(page)
            if len(page)<500: return rows
            offset+=500

    def recent_clips(self, days=30):
        since=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        rows=self.request('GET','bsd_assets',params={'used_at':'gte.'+since,'select':'clip_id','limit':1000})
        return {r['clip_id'] for r in rows}

    def reserve_clip(self, clip, key, days=30):
        # Atomic claim or conditional expiry update, never an unconditional upsert.
        data={'clip_id':str(clip['id']),'job_key':key,'provenance':clip,
              'used_at':datetime.now(timezone.utc).isoformat()}
        if self.request('POST','bsd_assets',json=data) is not None: return True
        since=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        rows=self.request('PATCH','bsd_assets',params={'clip_id':'eq.'+str(clip['id']),
                     'used_at':'lt.'+since},json=data)
        return bool(rows)

    def metrics(self, key, payload):
        # Safe to repeat the same daily observation; never aggregate repeated snapshots as posts.
        self.request('POST','bsd_metrics',params={'on_conflict':'observation_key'},
            headers={'Prefer':'resolution=merge-duplicates,return=representation'},
            json={'observation_key':key,'payload':payload})
