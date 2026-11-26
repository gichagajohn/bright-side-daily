"""Conservative transcript timing reconciliation and readable caption grouping."""
import re
from difflib import SequenceMatcher

NUMBERS=dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'.split(),map(str,range(21))))
WEAK=set('a an the and or but to of for with at by in on is are was were be have has had can could would should will do does did you your it its this that make feel not rough whole'.split())
KEYWORDS=set('kindness courage hope rest breathe breath control gratitude practice beginning progress support help listen learn small steps missed bus'.split())

def norm(word):
    word=re.sub(r'[^a-z0-9]','',word.lower())
    return NUMBERS.get(word,word)

def script_marks(script, marks):
    """Use recognition only for timing. Reject missing/extra or materially different words.

    One small spelling/inflection discrepancy per >=40 words is tolerated as ASR
    uncertainty; it is reported, not proof that the spoken audio is verbatim.
    Multiword number/contraction mappings are withheld rather than guessed.
    """
    words=script.split()
    if len(words)!=len(marks): raise ValueError('Word count differs; exact script alignment unavailable')
    corrected=[];changes=[];fuzzy=0
    for word,mark in zip(words,marks):
        expected,heard=norm(word),norm(mark['text'])
        if expected!=heard:
            if min(len(expected),len(heard))<5 or SequenceMatcher(None,expected,heard).ratio()<0.8:
                raise ValueError('Material narration/script mismatch; manual review required')
            fuzzy+=1
        if word!=mark['text']:
            changes.append({'script':word,'recognized':mark['text'],'start':mark['start'],
                            'kind':'minor_asr_difference' if expected!=heard else 'formatting'})
        corrected.append({**mark,'text':word})
    if fuzzy>len(words)//40: raise ValueError('Too many ASR differences; narration withheld')
    return corrected,changes

def phrase_groups(marks):
    # Hard boundaries at sentence punctuation, commas/semicolons and audible pauses.
    phrases=[];current=[]
    for m in marks:
        if current and m['start']-current[-1]['end']>=0.28:
            phrases.append(current);current=[]
        current.append(m)
        if re.search(r'[.!?,;:]\s*$',m['text']):
            phrases.append(current);current=[]
    if current:phrases.append(current)
    output=[]
    for phrase in phrases:
        n=len(phrase);best={n:(0,[])}
        for i in range(n-1,-1,-1):
            choices=[]
            for j in range(i+1,min(n,i+7)+1):
                span=phrase[j-1]['end']-phrase[i]['start']
                if span>3.2 and j>i+1:break
                cost=3+(6 if j-i==1 else 2 if j-i==2 else 0)+(3 if span<0.8 else 0)
                if j<n and norm(phrase[j-1]['text']) in WEAK:cost+=12
                if j<n and norm(phrase[j]['text']) in {'a','an','the'}:cost-=1
                tail,groups=best[j]
                choices.append((cost+tail,[phrase[i:j]]+groups))
            best[i]=min(choices,key=lambda x:x[0])
        output.extend(best[0][1])
    return output

def wrap_balanced(words,font,max_width=760):
    if any(font.getlength(w)>max_width for w in words):raise ValueError('Caption word too wide')
    if font.getlength(' '.join(words))<=max_width:return [list(words)]
    choices=[]
    for i in range(1,len(words)):
        widths=[font.getlength(' '.join(words[:i])),font.getlength(' '.join(words[i:]))]
        if max(widths)<=max_width:
            penalty=abs(widths[0]-widths[1])+(300 if min(i,len(words)-i)==1 else 0)
            choices.append((penalty,[words[:i],words[i:]]))
    if not choices:raise ValueError('Caption cannot fit two safe lines')
    return min(choices,key=lambda x:x[0])[1]

def emphasized(words, phrases=()):
    normalized=[norm(w) for w in words];indices=set()
    for phrase in phrases:
        needle=[norm(w) for w in phrase.split()]
        if not needle:continue
        for i in range(len(words)-len(needle)+1):
            if normalized[i:i+len(needle)]==needle:indices.update(range(i,i+len(needle)))
    if not indices:
        indices={i for i,w in enumerate(normalized) if w in KEYWORDS}
    return indices


def footage_score(clip,query,rule=None):
    """Metadata-only relevance filter, NOT visual understanding/legal clearance."""
    from urllib.parse import urlparse,unquote
    title=unquote(urlparse(clip.get('url','')).path).replace('-',' ').lower()
    words=set(re.findall(r'[a-z]+',title));query_words=set(re.findall(r'[a-z]+',query.lower()))
    rule=rule or {}
    if query_words & {'sunrise','morning','dawn'} and words & {'sunset','night','nighttime','dusk'}:return None
    if query_words & {'sunset','evening','dusk'} and words & {'sunrise','morning','dawn'}:return None
    if words & set(rule.get('exclude',[])):return None
    required=set(rule.get('required_any',[]))
    if required and not words & required:return None
    matches=(query_words-WEAK-{'person','beautiful','video'}) & words
    if not matches:return None
    return len(matches)*3+len(required & words)*4
