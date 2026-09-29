"""On-demand, segment-cached translation; no whole-archive cloud jobs."""
import hashlib,json,os,re,threading
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.db import connect
from services import llm
_lock=threading.Lock();_inflight={}

def provider():return os.getenv('TRANSLATION_PROVIDER','local')

def segments(text,limit=1800):
    remaining=text.strip();result=[]
    while remaining:
        if len(remaining)<=limit:result.append(remaining);break
        boundaries=[m.end() for m in re.finditer(r'[.!?।]\s+|\n\n',remaining[:limit]) if m.end()>limit//3]
        cut=boundaries[-1] if boundaries else remaining.rfind(' ',0,limit)
        if cut<=0:cut=limit
        result.append(remaining[:cut].strip());remaining=remaining[cut:].strip()
    return result

def translate_segment(text,source,target,speaker=''):
    from services.narration import known_gender
    gender=known_gender(speaker)
    backend=provider();key=hashlib.sha256(f'segment-v2:{backend}:{source}:{target}:{gender}:{text}'.encode()).hexdigest()
    with _lock:guard=_inflight.setdefault(key,threading.Lock())
    with guard:
        with connect() as c:cached=c.execute('SELECT text FROM translations WHERE cache_key=?',(key,)).fetchone()
        if cached:return cached[0]
        if backend=='sarvam':
            with httpx.Client(timeout=25) as client:
                payload={'input':text,'source_language_code':source+'-IN','target_language_code':target+'-IN','model':'sarvam-translate:v1'}
                if gender:payload['speaker_gender']=gender
                response=client.post('https://api.sarvam.ai/translate',headers={'api-subscription-key':os.environ['SARVAM_API_KEY']},json=payload)
                response.raise_for_status();translated=response.json()['translated_text']
        else:translated=llm.translate(text,target)
        if not translated.strip():raise ValueError('Empty translation')
        with connect() as c:c.execute('INSERT OR REPLACE INTO translations VALUES(?,?,?,?,CURRENT_TIMESTAMP)',(key,target,translated,backend))
        return translated

def translate_many(texts,source,target,speakers=None):
    if source==target:return texts
    if source not in llm.LANGUAGES or target not in llm.LANGUAGES:raise ValueError('Unsupported translation language')
    speakers=speakers or ['']*len(texts)
    if len(speakers)!=len(texts):raise ValueError('Each translation needs its corresponding speaker')
    groups=[segments(text) for text in texts];flat=[(chunk,speaker) for group,speaker in zip(groups,speakers) for chunk in group]
    # Three bounded requests keep page latency down without bulk spending.
    with ThreadPoolExecutor(max_workers=3 if provider()=='sarvam' else 1) as pool:
        translated=list(pool.map(lambda pair:translate_segment(pair[0],source,target,pair[1]),flat))
    result=[];offset=0
    for group in groups:result.append('\n\n'.join(translated[offset:offset+len(group)]));offset+=len(group)
    return result
