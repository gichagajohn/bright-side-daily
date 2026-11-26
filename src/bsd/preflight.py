"""Authenticated READ-ONLY checks. Does not start an upload or publish anything."""
import json
from bsd.ledger import Ledger
from bsd.facebook import Facebook

def main():
    ledger=Ledger()
    # Access to all three tables must work before a publishing claim is attempted.
    for table in ('bsd_jobs','bsd_assets','bsd_metrics'):
        ledger.request('GET',table,params={'select':'*','limit':1})
        print(table+': readable')
    api=Facebook(lambda *_:None)
    page=api.request('GET',api.page,params={'fields':'id,name'})
    print(json.dumps({'page_id':page.get('id'),'page_name':page.get('name'),
        'note':'Read access only. Does NOT prove publish permissions or Reel eligibility.'}))

if __name__=='__main__': main()
