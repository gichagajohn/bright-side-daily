"""Multi-scene 1080p Reel compositor with measured phrase captions and QC."""
import json
import math
import re
from pathlib import Path
from PIL import ImageFont
from bsd.common import config, run, probe, duration, file_hash, write_json
from bsd.narration import validate_marks

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
LEAD=0.35

def stamp(t):
    cs=round(t*100); return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'

def escape(s):
    return s.replace('\\','').replace('{','').replace('}','').replace('\n',' ')

def captions(marks, folder, total):
    font=ImageFont.truetype(FONT,54)
    groups=[]
    for mark in marks:
        if not groups or len(groups[-1])>=5 or mark['end']-groups[-1][0]['start']>2.5:
            groups.append([])
        groups[-1].append(mark)
    lines=['[Script Info]','ScriptType: v4.00+','PlayResX: 1080','PlayResY: 1920',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Caption,DejaVu Sans,54,&H00FFFFFF,&H0000D7FF,&H00202020,&H90000000,-1,0,0,0,100,100,0,0,1,4,1,2,140,180,480,1',
        'Style: Brand,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00303030,&H80000000,0,0,0,0,100,100,1,0,1,2,0,8,140,180,220,1',
        '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
        f'Dialogue: 0,0:00:00.00,{stamp(total)},Brand,,0,0,0,,BRIGHT SIDE DAILY']
    bounds=[]
    for i,g in enumerate(groups):
        words=[escape(m['text']) for m in g]; rows=[[]]
        for word in words:
            if font.getlength(word)>760: raise ValueError('Unbreakable caption word exceeds safe width')
            if font.getlength(' '.join(rows[-1]+[word]))>760: rows.append([])
            rows[-1].append(word)
        if len(rows)>2: raise ValueError('Caption exceeds two safe lines')
        plain=[' '.join(row) for row in rows]
        # Small accent on the last word, without flashing or word-by-word jumps.
        rows[-1][-1]='{\\c&H66D9FF&}'+rows[-1][-1]+'{\\c&HFFFFFF&}'
        text='\\N'.join(' '.join(row) for row in rows)
        start=g[0]['start']+LEAD
        next_start=groups[i+1][0]['start']+LEAD if i+1<len(groups) else total-0.4
        end=min(max(g[-1]['end']+LEAD,next_start),total-0.25)
        if end<=start: raise ValueError('Caption interval invalid')
        lines.append(f'Dialogue: 1,{stamp(start)},{stamp(end)},Caption,,0,0,0,,{text}')
        bounds.append({'start':start,'end':end,'text':' '.join(words),'lines':plain,
                       'max_width':max(font.getlength(s) for s in plain),'bottom':1440})
    path=Path(folder)/'captions.ass';path.write_text('\n'.join(lines))
    return path,bounds


def render(post, clips, voice, marks, folder, voice_meta, provenance):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    speech=duration(voice);total=speech+LEAD+0.8
    cfg=config()['reels']
    if not cfg['min_seconds']<=total<=cfg['max_seconds']:
        raise ValueError(f'Narration duration {total:.1f}s outside 20–35s; revise script')
    validate_marks(post['content'],marks,speech)
    if len(clips)!=3: raise ValueError('Exactly three scenes required')
    ass,bounds=captions(marks,folder,total)
    segment=(total+1.0)/3; overlap=0.5
    normalized=[]
    # Sequential normalisation bounds RAM; libass overlays captions after transitions.
    for i,clip in enumerate(clips):
        p=folder/f'scene-{i}.mp4'
        run(['ffmpeg','-y','-v','error','-threads','2','-stream_loop','-1','-i',clip,
             '-t',f'{segment:.3f}','-an','-vf',
             'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,eq=contrast=1.025:saturation=0.94:brightness=-0.015,format=yuv420p',
             '-c:v','libx264','-preset','veryfast','-crf','21','-threads','2',p],timeout=360)
        normalized.append(p)
    # Subtitle path is generated locally, not supplied by content.
    ass_path=str(ass.resolve()).replace('\\','/').replace(':','\\:').replace("'", "\\'")
    graph=(f'[0:v]setpts=PTS-STARTPTS,fps=30[v0];[1:v]setpts=PTS-STARTPTS,fps=30[v1];'
           f'[2:v]setpts=PTS-STARTPTS,fps=30[v2];'
           f'[v0][v1]xfade=transition=fade:duration={overlap}:offset={segment-overlap:.3f},fps=30[x];'
           f'[x][v2]xfade=transition=fade:duration={overlap}:offset={2*(segment-overlap):.3f},'
           f"subtitles=filename='{ass_path}',fade=t=out:st={total-0.35:.3f}:d=0.35,format=yuv420p[v];"
           f'[3:a]adelay=350|350,apad,loudnorm=I=-16:TP=-1.5:LRA=9[a]')
    out=folder/'reel.mp4'
    args=['ffmpeg','-y','-v','error','-filter_complex_threads','1']
    for p in normalized: args+=['-i',p]
    args+=['-i',voice,'-filter_complex',graph,'-map','[v]','-map','[a]',
           '-t',f'{total:.3f}','-c:v','libx264','-preset','fast','-crf','21',
           '-threads','2','-c:a','aac','-b:a','160k','-ar','48000','-ac','2','-movflags','+faststart',out]
    run(args,timeout=600)
    # Cover is an actual rendered scene frame, not unrelated stock.
    run(['ffmpeg','-y','-v','error','-ss','1.0','-i',out,'-frames:v','1',folder/'cover.jpg'])
    manifest={'schema':1,'brand':'BRIGHT SIDE DAILY','post':post,'voice':voice_meta,
              'narration_sha256':file_hash(voice),'captions':bounds,'marks':marks,
              'footage':provenance,'duration':total,'video_sha256':file_hash(out),
              'music':None,'music_note':'No external music: avoids unverified licensing.'}
    write_json(folder/'manifest.json',manifest)
    quality(out,manifest)
    for p in normalized: p.unlink(missing_ok=True)
    return out,manifest


def quality(path, manifest):
    p=Path(path);cfg=config()['reels']
    if not p.is_file() or not 1000<p.stat().st_size<=cfg['max_bytes']: raise ValueError('Invalid video size')
    info=probe(p);video=[s for s in info['streams'] if s['codec_type']=='video']
    audio=[s for s in info['streams'] if s['codec_type']=='audio']
    if len(video)!=1 or (video[0]['width'],video[0]['height'])!=(1080,1920): raise ValueError('Invalid resolution')
    if video[0]['codec_name']!='h264' or video[0].get('pix_fmt')!='yuv420p': raise ValueError('Invalid video codec')
    if not audio or audio[0]['codec_name']!='aac': raise ValueError('AAC narration missing')
    seconds=float(info['format']['duration'])
    if not cfg['min_seconds']<=seconds<=cfg['max_seconds']: raise ValueError('Invalid duration')
    if manifest.get('brand')!='BRIGHT SIDE DAILY' or not manifest.get('narration_sha256'): raise ValueError('Missing brand/narration')
    if file_hash(p)!=manifest.get('video_sha256'): raise ValueError('Video modified after rendering')
    if not manifest.get('captions') or any(c['max_width']>760 or c['bottom']>1440 or c['end']>seconds+0.1
                                          for c in manifest['captions']): raise ValueError('Unsafe captions')
    assets=manifest.get('footage',[])
    if len(assets)!=3 or len({a.get('id') for a in assets})!=3 or len({a.get('sha256') for a in assets})!=3:
        raise ValueError('Duplicate or missing footage')
    if any(not a.get('license_url') or not a.get('source_url') for a in assets): raise ValueError('Missing asset provenance')
    run(['ffmpeg','-v','error','-xerror','-i',p,'-f','null','-'],timeout=180)
    import subprocess
    result=subprocess.run(['ffmpeg','-v','info','-i',str(p),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json',
                           '-f','null','-'],capture_output=True,text=True,timeout=180)
    if result.returncode: raise ValueError('Audio analysis failed')
    match=re.search(r'\{\s*"input_i".*?\}',result.stderr,re.S)
    if not match: raise ValueError('Audio measurement unavailable')
    levels=json.loads(match.group())
    loudness=float(levels['input_i']);peak=float(levels['input_tp'])
    if not math.isfinite(loudness) or not -21<=loudness<=-12 or peak>0:
        raise ValueError('Narration too quiet, loud or clipped')
    return {'passed':True,'duration':seconds,'lufs':loudness,'true_peak_db':peak}
