import json
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock
import pytest
import yaml
from bsd import schedule,stories,narration,pipeline,facebook
from bsd.common import ROOT,digest
from bsd.ledger import Ledger
from bsd.analytics import measure,summary


def test_story_categories_and_original_seeds():
    items=json.loads((ROOT/'content/reel_stories.json').read_text())['stories']
    assert len(items)==20
    assert set(s['category'] for s in items)==set(stories.CATEGORIES)
    for item in items: assert stories.validate(item,[])
    assert len({digest(stories.text(s)) for s in items})==20


def test_repeated_story_rejected():
    item=json.loads((ROOT/'content/reel_stories.json').read_text())['stories'][0]
    with pytest.raises(ValueError): stories.validate(item,[{'content':stories.text(item)}])


def test_scripture_not_invented():
    item=json.loads((ROOT/'content/reel_stories.json').read_text())['stories'][8]
    item['hook']='John 99:99 says something invented.'
    with pytest.raises(ValueError): stories.validate(item,[])


def test_nairobi_requested_reels():
    for hour,name in [(5,'morning_motivation'),(10,'midday_encouragement'),(16,'evening_reflection')]:
        selected=schedule.due(datetime(2026,11,26,hour,7,tzinfo=timezone.utc))
        assert any(s['name']==name and s['format']=='REELS' and d=='2026-11-26' for s,d in selected)


def test_delayed_slot_and_late_skip():
    selected=schedule.due(datetime(2026,11,26,6,7,tzinfo=timezone.utc))
    assert selected[0][0]['name']=='morning_motivation'
    assert not schedule.due(datetime(2026,11,26,6,45,tzinfo=timezone.utc))


def test_dst_rule_not_fixed_offset(monkeypatch):
    monkeypatch.setattr(schedule,'config',lambda:{'timezone':'America/New_York','max_lateness_minutes':30,
        'slots':[{'name':'morning','time':'08:00','format':'REELS'}]})
    assert schedule.due(datetime(2026,7,1,12,7,tzinfo=timezone.utc))
    assert schedule.due(datetime(2026,12,1,13,7,tzinfo=timezone.utc))
    assert not schedule.due(datetime(2026,12,1,12,7,tzinfo=timezone.utc))


def test_marks_partial_or_out_of_order_rejected():
    with pytest.raises(ValueError): narration.validate_marks('one two three four',[{'text':'one','start':0,'end':1}],4)
    with pytest.raises(ValueError): narration.validate_marks('one two',[
        {'text':'one','start':2,'end':3},{'text':'two','start':1,'end':2}],4)


def test_valid_marks():
    narration.validate_marks('One, two.',[{'text':'one','start':0,'end':1},{'text':'two','start':1,'end':2}],3)


def test_legacy_multiplatform_blocked():
    from agents.social_publisher import SocialPublisher
    with pytest.raises(RuntimeError): SocialPublisher('facebook,instagram')


def test_all_workflows_no_instagram_execution_or_secrets():
    for path in (ROOT/'.github/workflows').glob('*.yml'):
        text=path.read_text(); doc=yaml.load(text,Loader=yaml.BaseLoader)
        assert 'on' in doc
        assert 'secrets.IG_' not in text
        for job in doc['jobs'].values():
            for step in job.get('steps',[]):
                cmd=step.get('run','')
                assert 'instagram_' not in cmd and 'comment_agent.py' not in cmd
                assert '--retry-failed' not in cmd


def test_main_workflow_no_git_state_commit_and_dry_default():
    text=(ROOT/'.github/workflows/post_scheduler.yml').read_text()
    d=yaml.load(text,Loader=yaml.BaseLoader)
    assert d['on']['workflow_dispatch']['inputs']['dry_run']['default']=='true'
    assert 'git push' not in text and 'contents: write' not in text
    assert 'github.event.inputs' not in text


def test_live_disabled_before_ledger(monkeypatch,tmp_path):
    monkeypatch.setattr(pipeline,'ROOT',tmp_path);monkeypatch.delenv('BSD_ENABLE_PUBLISH',raising=False)
    monkeypatch.setattr(pipeline,'Ledger',Mock(side_effect=AssertionError('must not instantiate')))
    with pytest.raises(RuntimeError): pipeline.run_slot({'name':'positive_quote','format':'IMAGE'},'2026-11-26',False)


def test_dry_image_no_publish_or_ledger(monkeypatch,tmp_path):
    from PIL import Image
    from generators.pexels_photo_generator import PexelsPhotoGenerator
    monkeypatch.setattr(pipeline,'ROOT',tmp_path)
    monkeypatch.setattr(pipeline,'Ledger',Mock(side_effect=AssertionError('must not instantiate')))
    monkeypatch.setattr(pipeline,'Facebook',Mock(side_effect=AssertionError('must not instantiate')))
    monkeypatch.setattr(pipeline,'image_post',lambda *a:{'content':'Test only','category':'test'})
    def generate(self,post,path): Image.new('RGB',(1080,1080)).save(path);return str(path)
    monkeypatch.setattr(PexelsPhotoGenerator,'generate',generate)
    monkeypatch.setenv('PEXELS_API_KEY','fixture-only')
    assert pipeline.run_slot({'name':'positive_quote','time':'10:00','format':'IMAGE'},'2026-11-26',True)['dry_run']


def test_unknown_existing_job_not_replayed(monkeypatch,tmp_path):
    monkeypatch.setattr(pipeline,'ROOT',tmp_path);monkeypatch.setenv('BSD_ENABLE_PUBLISH','true')
    ledger=Mock();ledger.claim.return_value=False
    ledger.get.return_value={'status':'uncertain','payload':{}}
    monkeypatch.setattr(pipeline,'Ledger',lambda:ledger)
    monkeypatch.setattr(pipeline,'Facebook',Mock(side_effect=AssertionError('must not publish')))
    assert pipeline.run_slot({'name':'positive_quote','format':'IMAGE'},'2026-11-26',False)['skipped']


def test_read_metrics_missing_not_zero():
    api=Mock();api.request.side_effect=RuntimeError('Meta HTTP 400; code 100')
    metrics,availability=measure(api,'123','REELS')
    assert all(v is None for v in metrics.values())
    assert all('400' in a for a in availability.values())
    assert all('/video_insights' in c.args[1] for c in api.request.call_args_list)


def test_report_no_fake_optimisation():
    report=summary([])
    assert 'Keep three daily Reels' in report and 'NOT completion rate' in report


def api_fixture(monkeypatch):
    monkeypatch.setenv('FB_PAGE_ID','test-page');monkeypatch.setenv('FB_PAGE_ACCESS_TOKEN','test-secret')
    checkpoint=Mock();api=facebook.Facebook(checkpoint);return api,checkpoint


def test_photo_stages_and_no_text_fallback(monkeypatch,tmp_path):
    api,cb=api_fixture(monkeypatch);p=tmp_path/'image.jpg';p.write_bytes(b'fixture')
    api.request=Mock(return_value={'post_id':'123'})
    assert api.photo(p,'caption')=='123'
    assert [c.args[0] for c in cb.call_args_list]==['photo_submitting','published']
    assert api.request.call_count==1


def test_photo_ambiguous_never_retried(monkeypatch,tmp_path):
    api,cb=api_fixture(monkeypatch);p=tmp_path/'image.jpg';p.write_bytes(b'fixture')
    api.request=Mock(side_effect=RuntimeError('timeout'))
    with pytest.raises(RuntimeError): api.photo(p,'caption')
    assert api.request.call_count==1


def test_reel_lifecycle(monkeypatch,tmp_path):
    api,cb=api_fixture(monkeypatch);p=tmp_path/'reel.mp4';p.write_bytes(b'fixture')
    api.request=Mock(side_effect=[{'video_id':'123','upload_url':'https://rupload.facebook.com/test'},
        {'success':True},{'status':{'publishing_phase':{'status':'complete'}}}])
    response=Mock(ok=True);response.json.return_value={'success':True}
    upload=Mock(return_value=response);monkeypatch.setattr(facebook.requests,'post',upload)
    assert api.reel(p,'caption')=='123'
    assert [c.args[0] for c in cb.call_args_list]==['reel_starting','reel_uploading','reel_finishing','reel_processing','published']
    assert api.request.call_args_list[1].kwargs['data']['video_state']=='PUBLISHED'
    assert upload.call_count==1


def test_reel_untrusted_upload_url_rejected(monkeypatch,tmp_path):
    api,cb=api_fixture(monkeypatch)
    api.request=Mock(return_value={'video_id':'123','upload_url':'https://attacker.invalid/upload'})
    with pytest.raises(RuntimeError): api.reel(tmp_path/'x','caption')


def test_ledger_conflict_is_not_claim():
    ledger=Ledger.__new__(Ledger);ledger.request=Mock(return_value=None)
    assert not ledger.claim('same-job')


def test_asset_claim_uses_conditional_expiry():
    ledger=Ledger.__new__(Ledger);ledger.request=Mock(side_effect=[None,[]])
    assert not ledger.reserve_clip({'id':'123'},'job')
    call=ledger.request.call_args_list[1]
    assert call.args[0]=='PATCH' and call.kwargs['params']['used_at'].startswith('lt.')


def test_quality_rejects_empty_file(tmp_path):
    from bsd.cinematic import quality
    p=tmp_path/'bad.mp4';p.write_bytes(b'')
    with pytest.raises(ValueError): quality(p,{})


def test_secret_redaction(monkeypatch):
    from bsd.common import safe_error
    monkeypatch.setenv('FB_PAGE_ACCESS_TOKEN','private-example-token')
    message=safe_error(RuntimeError('failed private-example-token https://api.example/?access_token=hidden'))
    assert 'private-example-token' not in message and 'access_token' not in message
    assert '[REDACTED]' in message


def test_actual_image_layout_with_local_photo(monkeypatch,tmp_path):
    import io
    from PIL import Image
    from generators import pexels_photo_generator as photo
    data=io.BytesIO();Image.new('RGB',(1200,1600),'darkgreen').save(data,format='JPEG')
    response=Mock(content=data.getvalue());response.raise_for_status.return_value=None
    monkeypatch.setenv('PEXELS_API_KEY','fixture-only')
    monkeypatch.setattr(photo.PexelsPhotoGenerator,'_download_url',lambda *a:'fixture://photo')
    monkeypatch.setattr(photo.requests,'get',lambda *a,**k:response)
    path=photo.PexelsPhotoGenerator().generate({'content':'Small steps matter. Keep going with kindness.',
        'category':'motivational_quotes'},tmp_path/'image.jpg')
    with Image.open(path) as image: assert image.size==(1080,1080)
    with pytest.raises(ValueError):
        photo.PexelsPhotoGenerator().generate({'content':'word '*3000,'category':'bible_quotes'},tmp_path/'overflow.jpg')


def test_image_selection_preserves_existing_state(tmp_path):
    source=ROOT/'data/state/posted_content.json';before=source.read_bytes()
    post=pipeline.image_post('positive_quote',[],tmp_path)
    assert post['content'] and source.read_bytes()==before


def test_subtitles_measure_width_and_brand(tmp_path):
    from bsd.cinematic import captions
    marks=[{'text':w,'start':i,'end':i+.8} for i,w in enumerate('One small act of kindness matters'.split())]
    ass,bounds=captions(marks,tmp_path,22)
    assert 'BRIGHT SIDE DAILY' in ass.read_text()
    assert all(b['max_width']<=760 and b['bottom']<=1440 for b in bounds)


def test_reel_failure_does_not_fall_back_to_image(monkeypatch,tmp_path):
    monkeypatch.setattr(pipeline,'ROOT',tmp_path)
    monkeypatch.setattr(pipeline,'choose',lambda *a:{'content':'A complete test story','category':'test'})
    monkeypatch.setattr(pipeline,'narrate',Mock(side_effect=RuntimeError('No narration')))
    publish=Mock();monkeypatch.setattr(pipeline,'Facebook',publish)
    with pytest.raises(RuntimeError):
        pipeline.run_slot({'name':'morning_motivation','time':'08:00','format':'REELS'},'2026-11-26',True)
    publish.assert_not_called()
    assert (tmp_path/'artifacts/2026-11-26/morning_motivation/failure.json').exists()


def test_meta_write_transport_no_retry(monkeypatch):
    import requests
    api,cb=api_fixture(monkeypatch)
    api.session.request=Mock(side_effect=requests.Timeout('secret URL not logged'))
    with pytest.raises(RuntimeError): api.request('POST','test/photos',data={})
    assert api.session.request.call_count==1


def test_checkpoint_failure_prevents_photo_request(monkeypatch,tmp_path):
    api,cb=api_fixture(monkeypatch);cb.side_effect=RuntimeError('Ledger unavailable')
    api.request=Mock()
    with pytest.raises(RuntimeError):api.photo(tmp_path/'image.jpg','test')
    api.request.assert_not_called()
