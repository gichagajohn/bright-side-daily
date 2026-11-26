"""Real FFmpeg offline integration; synthetic media, NOT a live voice/footage test."""
import shutil
from pathlib import Path
import pytest
from bsd.common import run,file_hash
from bsd.cinematic import render,quality

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg not installed')
def test_real_ffmpeg_render_and_qc(tmp_path):
    clips=[];assets=[]
    for i,color in enumerate(['darkblue','darkgreen','darkred']):
        p=tmp_path/f'input{i}.mp4'
        run(['ffmpeg','-y','-v','error','-f','lavfi','-i',f'color=c={color}:s=360x640:r=30:d=2',
             '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',p])
        clips.append(p);assets.append({'id':str(i),'sha256':file_hash(p),
                                      'license_url':'fixture://generated','source_url':'fixture://generated'})
    voice=tmp_path/'test.wav'
    run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=20',voice])
    words=('This is a synthetic engineering fixture and not a finished motivational story. '
           'Its purpose is to check video dimensions captions audio codecs transitions and safe margins.').split()
    step=19/len(words)
    marks=[{'text':w,'start':i*step,'end':(i+1)*step} for i,w in enumerate(words)]
    output,manifest=render({'content':' '.join(words)},clips,voice,marks,tmp_path/'render',
                          {'provider':'synthetic-test-only'},assets)
    result=quality(output,manifest)
    assert result['passed'] and 20<=result['duration']<=35
    assert (tmp_path/'render/cover.jpg').exists()
    # Mutation and duplicate-asset detection must fail closed.
    manifest['footage'][1]=manifest['footage'][0]
    with pytest.raises(ValueError): quality(output,manifest)
