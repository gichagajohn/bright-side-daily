"""Capability-aware Facebook metrics. Unsupported is null, never zero.
Metric candidates: Meta /video/video_insights documentation (checked 2026-11-26).
Runtime probes still required: a documented name does not establish Page access.
"""
import json
import statistics
from datetime import datetime, timezone
from bsd.common import ROOT,write_json
from bsd.facebook import Facebook
from bsd.ledger import Ledger

REEL_METRICS=['blue_reels_play_count','fb_reels_total_plays','post_impressions_unique',
 'post_video_avg_time_watched','post_video_view_time','post_video_followers',
 'post_video_likes_by_reaction_type','post_video_retention_graph','post_video_social_actions']
IMAGE_METRICS=['post_media_view','post_total_media_view_unique']

def measure(api, media_id, media_type):
    values={};availability={}
    names=REEL_METRICS if media_type=='REELS' else IMAGE_METRICS
    edge='/video_insights' if media_type=='REELS' else '/insights'
    for name in names:
        try:
            data=api.request('GET',media_id+edge,params={'metric':name,'period':'lifetime'})
            records=data.get('data',[])
            item=next((r for r in records if r.get('name')==name),None)
            samples=item.get('values',[]) if item else []
            value=samples[-1].get('value') if samples else None
            values[name]=value;availability[name]='available' if value is not None else 'not_returned'
        except RuntimeError as exc:
            values[name]=None;availability[name]=str(exc) # transport emits codes only
    if media_type=='IMAGE':
        try:
            values['social']=api.request('GET',media_id,params={
                'fields':'reactions.summary(true),comments.summary(true),shares'})
        except RuntimeError: values['social']=None
    return values,availability

def summary(rows):
    lines=['# Bright Side Daily — Facebook weekly report','',
        'Snapshots are lifetime totals collected now, not weekly increments. Missing metrics are not zero.',
        'Watch ratio includes replays and is NOT completion rate. Retention is preserved separately.',
        'Only new-ledger confirmed publications are included; legacy video IDs are not assumed to be Reels.','']
    for fmt in ('REELS','IMAGE'):
        selected=[r for r in rows if r['format']==fmt]
        lines += [f'## {fmt}: {len(selected)} unique media IDs','']
        for field in ('category','hook','duration_band','posting_time','voice_style','footage_style'):
            groups={}
            for row in selected:
                # Compare only 7–30 day cohorts; young posts are not mistaken for poor performers.
                if not 7<=row['age_days']<=30: continue
                label=str(row.get(field,'unknown'));groups.setdefault(label,[]).append(row)
            for label,items in groups.items():
                if len(items)<5: continue
                ratios=[r['watch_ratio'] for r in items if r.get('watch_ratio') is not None]
                shares=[r['share_rate'] for r in items if r.get('share_rate') is not None]
                followers=[r['follow_rate'] for r in items if r.get('follow_rate') is not None]
                def med(xs): return f'{statistics.median(xs):.3f}' if xs else 'unavailable'
                lines.append(f'- {field}: {label} — n={len(items)}; median watch ratio {med(ratios)}; '
                             f'shares/play {med(shares)}; follows/play {med(followers)}')
        lines.append('')
    lines+=['## Recommendation',
        'Keep three daily Reels. Do not increase frequency or change posting times from sparse observations.',
        'Compare watch time, shares and follows together once at least five age-matched posts exist per group.',
        'Investigate unavailable metrics and permissions before interpreting a missing value as performance.',
        'Cover frames and caption timing still require human visual review before production enablement.']
    return '\n'.join(lines)

def main():
    ledger=Ledger();api=Facebook(lambda *_:None);now=datetime.now(timezone.utc);rows=[]
    jobs=ledger.jobs(days=90)
    for job in jobs:
        p=job['payload'];mid=p.get('media_id')
        if job['status']!='published' or not mid: continue
        fmt=p['format'];metrics,available=measure(api,str(mid),fmt)
        post=p['post'];seconds=p.get('duration',0)
        plays=metrics.get('blue_reels_play_count');avg=metrics.get('post_video_avg_time_watched')
        social=metrics.get('post_video_social_actions') or {}
        shares=social.get('share') if isinstance(social,dict) else None
        follows=metrics.get('post_video_followers')
        row={'media_id':str(mid),'format':fmt,'collected_at':now.isoformat(),
             'published_at':job['updated_at'],'category':post.get('category'),'hook':post.get('hook'),
             'duration_band':f'{int(seconds)//5*5}-{int(seconds)//5*5+5}s',
             'posting_time':post.get('posting_time'),'voice_style':post.get('style'),
             'footage_style':', '.join(a.get('query','') for a in p.get('footage',[])),
             'age_days':(now-datetime.fromisoformat(job['updated_at'].replace('Z','+00:00'))).total_seconds()/86400,
             'metrics':metrics,'availability':available,
             'watch_ratio':avg/1000/seconds if isinstance(avg,(float,int)) and seconds else None,
             'share_rate':shares/plays if isinstance(shares,(int,float)) and plays else None,
             'follow_rate':follows/plays if isinstance(follows,(int,float)) and plays else None}
        ledger.metrics(f'{mid}:{now.date()}',row);rows.append(row)
    try: followers=api.request('GET',api.page,params={'fields':'followers_count'}).get('followers_count')
    except RuntimeError: followers=None
    ledger.metrics('page:'+str(now.date()),{'followers_count':followers,'collected_at':now.isoformat(),
        'note':'Page snapshot; use dated differences for growth, not per-Reel attribution'})
    folder=ROOT/'artifacts/analytics';write_json(folder/'observations.json',rows)
    (folder/'weekly-report.md').write_text(summary(rows))
    print(f'Collected {len(rows)} unique posts. Page followers: '+str(followers))

if __name__=='__main__': main()
