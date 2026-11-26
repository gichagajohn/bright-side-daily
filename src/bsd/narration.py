"""Natural TTS with bounded retries and fail-closed word alignment."""
import asyncio
import re
from pathlib import Path
from difflib import SequenceMatcher
from bsd.common import duration, config, write_json
from bsd.editorial import script_marks


def tokens(text):
    return re.findall(r"[a-z0-9]+",text.lower())


def validate_marks(text, marks, seconds):
    if not marks: raise ValueError('No narration word timings')
    expected=tokens(text); actual=tokens(' '.join(m['text'] for m in marks))
    if SequenceMatcher(None,expected,actual).ratio()<0.94:
        raise ValueError('Narration and caption transcript differ')
    previous=-1
    for m in marks:
        if m['start']<previous or m['end']<=m['start'] or m['end']>seconds+0.3:
            raise ValueError('Invalid word timing')
        previous=m['start']


async def edge(text, voice, rate, path):
    import edge_tts
    marks=[]
    async def collect():
        with open(path,'wb') as f:
            async for c in edge_tts.Communicate(text,voice,rate=rate,boundary='WordBoundary').stream():
                if c['type']=='audio': f.write(c['data'])
                elif c['type']=='WordBoundary':
                    marks.append({'text':c['text'],'start':c['offset']/1e7,
                                  'end':(c['offset']+c['duration'])/1e7})
    await asyncio.wait_for(collect(),timeout=60)
    return marks


def narrate(text, folder, style='warm'):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    path=folder/'voice.mp3'; cfg=config()['voice']
    rate={'reflective':'-8%','encouraging':'-3%','warm':cfg['rate']}.get(style,cfg['rate'])
    for voice in (cfg['primary'],cfg['fallback']):
        try:
            marks=asyncio.run(edge(text,voice,rate,path))
            seconds=duration(path);validate_marks(text,marks,seconds)
            marks,changes=script_marks(text,marks)
            return path,marks,{'provider':'edge-tts','voice':voice,'style':style,'timing':'provider',
                              'caption_source':'approved_script','alignment_changes':changes}
        except Exception:
            path.unlink(missing_ok=True)
    # Independent service fallback. ASR timestamps are validated against the script;
    # guessed uniform word timings and silent videos are never accepted.
    try:
        from gtts import gTTS
        from faster_whisper import WhisperModel
        gTTS(text=text,lang='en',timeout=(10,40)).save(str(path))
        model=WhisperModel('tiny.en',device='cpu',compute_type='int8',cpu_threads=2)
        segments,_=model.transcribe(str(path),word_timestamps=True,language='en',beam_size=3)
        marks=[{'text':w.word.strip(),'start':w.start,'end':w.end}
               for s in segments for w in s.words or []]
        validate_marks(text,marks,duration(path))
        marks,changes=script_marks(text,marks)
        return path,marks,{'provider':'gtts','voice':'en','style':style,'timing':'asr-validated',
                          'caption_source':'approved_script','alignment_changes':changes}
    except Exception:
        raise RuntimeError('All narration/alignment options failed; Reel withheld') from None
