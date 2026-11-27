"""Read-only speech diagnostic. Never logs exception strings or request URLs."""
import asyncio
import importlib.metadata
import json
import tempfile
from pathlib import Path
import edge_tts

VOICE = 'en-KE-ChilembaNeural'

def error_summary(exc):
    result = {'error_type':type(exc).__name__}
    status = getattr(exc, 'status', None)
    if isinstance(status, int): result['http_status'] = status
    return result

async def check():
    report = {'voice':VOICE, 'edge_tts_version':importlib.metadata.version('edge-tts')}
    try:
        voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=30)
        matches = [v for v in voices if v.get('ShortName') == VOICE]
        report['voice_list'] = {'available':bool(matches), 'gender':matches[0].get('Gender') if matches else None}
    except Exception as exc:
        report['voice_list'] = error_summary(exc)
    audio_bytes = 0
    boundaries = 0
    async def synthesize():
        nonlocal audio_bytes, boundaries
        stream = edge_tts.Communicate('Take your time. One steady step today is enough to begin.', VOICE, rate='+0%', boundary='WordBoundary')
        with tempfile.TemporaryDirectory(prefix='bsd-voice-check-') as folder:
            with (Path(folder)/'voice.mp3').open('wb') as output:
                async for chunk in stream.stream():
                    if chunk['type']=='audio':
                        output.write(chunk['data']); audio_bytes += len(chunk['data'])
                    elif chunk['type']=='WordBoundary': boundaries += 1
    try:
        await asyncio.wait_for(synthesize(), timeout=45)
        report['synthesis'] = {'audio_bytes':audio_bytes,'word_boundaries':boundaries,'passed':audio_bytes>1000 and boundaries>0}
    except Exception as exc:
        report['synthesis'] = dict(error_summary(exc), passed=False)
    path = Path('artifacts/voice-diagnostic/report.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if report['synthesis']['passed'] else 1

if __name__=='__main__':
    raise SystemExit(asyncio.run(check()))
