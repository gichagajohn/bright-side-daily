"""Legacy quote-card appearance with fail-closed media validation."""
from pathlib import Path
from unittest.mock import patch
from bsd.common import probe, run, write_json


def render_legacy(post, folder):
    from generators import reel_generator as legacy
    original_speak = legacy._speak

    def require_speech(*args, **kwargs):
        kwargs.update(voice='en-KE-ChilembaNeural', rate='+0%', strict=True)
        spoken = original_speak(*args, **kwargs)
        if not spoken:
            raise RuntimeError('Legacy narration unavailable; publication withheld')
        return spoken

    def reject_static(*args, **kwargs):
        raise RuntimeError('Legacy animated rendering failed; no silent/static fallback')

    # Use the original generated pad, not unverified files from assets/audio.
    with patch.object(legacy, '_speak', require_speech), \
         patch.object(legacy, '_static_reel', reject_static), \
         patch.object(legacy, '_own_track', return_value=None), \
         patch.object(legacy, 'ANIM_MODE', 'words'), \
         patch.object(legacy, 'TTS_MODE', 'auto'):
        result = legacy.generate(post, output_path=folder/'reel.mp4')
    if not result:
        raise RuntimeError('Legacy renderer returned no video')
    asset = Path(result)
    info = probe(asset)
    video = next((s for s in info['streams'] if s['codec_type']=='video'), {})
    audio = next((s for s in info['streams'] if s['codec_type']=='audio'), {})
    seconds = float(info['format']['duration'])
    if (video.get('width'),video.get('height'),video.get('codec_name')) != (1080,1920,'h264'):
        raise ValueError('Invalid legacy video format')
    if audio.get('codec_name') != 'aac' or not 3 <= seconds <= 90:
        raise ValueError('Invalid legacy audio or duration')
    if asset.stat().st_size > 50_000_000:
        raise ValueError('Legacy Reel exceeds size limit')
    run(['ffmpeg','-v','error','-xerror','-i',asset,'-f','null','-'])
    qc = {'passed':True,'duration':seconds,'renderer':'legacy_quote_card',
          'note':'Legacy technical checks, not cinematic caption/loudness checks'}
    write_json(folder/'manifest.json',{'post':post,'qc':qc})
    return asset, qc
