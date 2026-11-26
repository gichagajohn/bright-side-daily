"""Read remote status of held jobs. Never upload, finish, or recreate media.
Only marks a Reel published when Meta confirms its publishing phase complete.
Photo submissions without an acknowledged ID require manual Page inspection.
"""
import argparse
import json
from bsd.ledger import Ledger
from bsd.facebook import Facebook

def main():
    p=argparse.ArgumentParser();p.add_argument('--job-key',required=True)
    p.add_argument('--record-confirmed',action='store_true',help='Record a confirmed remote Reel; no Facebook writes')
    args=p.parse_args();ledger=Ledger();job=ledger.get(args.job_key)
    if not job: raise RuntimeError('Job not found')
    payload=job['payload'];mid=payload.get('media_id')
    if not mid:
        print('No acknowledged media ID. Inspect Page manually. Do NOT clear or replay this job.');return
    if payload.get('format')!='REELS':
        print('Image job: inspect the recorded media ID on Facebook before any manual ledger changes.');return
    api=Facebook(lambda *_:None)
    status=api.request('GET',str(mid),params={'fields':'status'}).get('status',{})
    complete=status.get('publishing_phase',{}).get('status')=='complete'
    print(json.dumps({'media_id':mid,'confirmed_published':complete,'status':status}))
    if complete and args.record_confirmed:
        payload['stage']='published';payload['reconciled']=True
        ledger.update(args.job_key,'published',payload)

if __name__=='__main__':main()
