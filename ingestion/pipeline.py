import hashlib,re,json,threading
from pathlib import Path
import pymupdf
from app.db import connect

# The delimiter must be outside a complete constituency/portfolio suffix. A colon
# inside "(United Provinces:\nGeneral)" is not the start of the member's speech.
SPEAKER_PREFIX=r"(?:An Honourable Member|Several Honourable Members|Honourable Members|Dr\.|Mr\.|Mrs\.|Miss|Shrimati|Shri|Sri|Smt\.|Prof\.|Pandit|Seth|Maulana|Sardar|Sir|The Honourable|The Hon\.?['’]?ble|Vice-President|President|Chairman|Speaker|श्रीमती|श्री|डॉ\.?|डा\.?|अध्यक्ष)"
SPEAKER=re.compile(
    r'^[ \t]*(?P<speaker>'+SPEAKER_PREFIX+r'[^\n:：()]{0,145}?)'
    r'(?:[ \t]*\([^()]{0,200}\))*[ \t]*[:：][ \t]*',
    re.MULTILINE|re.IGNORECASE,
)
_OFFICE=re.compile(r'(?:The )?(?:Mr\. )?(?:Deputy[- ]|Vice[- ])?(?:President|Chairman|Speaker)',re.IGNORECASE)
_PROSE_WORDS={'said','says','speaks','spoke','writes','wrote','declares','declare','shall','should','would','will','memorandum'}

def _speaker_label(raw):
    label=re.sub(r'\s+',' ',raw).strip()
    if not label or any(ch in label for ch in ',;!?\ufffd') or len(label.split())>14:return None
    if _OFFICE.fullmatch(label):return label
    # Bare office prefixes can also begin quoted constitutional provisions.
    if re.match(r'^(?:Vice-President|President|Chairman|Speaker)\b',label,re.IGNORECASE):return None
    if re.search(r'[\u0900-\u097f]',label):
        return label if re.fullmatch(r'[\u0900-\u097fA-Za-z.\-\s]+',label) else None
    words=label.split()
    if any(word.casefold().strip('.') in _PROSE_WORDS for word in words):return None
    # English printed names/initials have capitals; prose after an honorific is
    # deliberately left in the source text rather than assigned a false speaker.
    for word in words:
        if word.casefold() in {'de','of','the','von','van'}:continue
        if not re.fullmatch(r"[A-Za-z.'’\-]+",word) or not word[0].isupper():return None
    return label if len(words)>1 else None

def clean(text):
    text=text.replace('\x00','').replace('\u00ad','')
    return re.sub(r'[ \t]+',' ',text).strip()

def split_turns(text):
    # Front-matter office directories use colons too, but contain no speeches.
    offices=re.findall(r'(?mi)^[ \t]*(?:Constitutional Adviser|Joint Secretary|Deputy Secretary|Under Secretary|Marshal)[ \t]*:',text)
    if len(offices)>=3:return []
    matches=[(m,label) for m in SPEAKER.finditer(text) if (label:=_speaker_label(m.group('speaker')))];turns=[]
    if not matches:return []
    if text[:matches[0][0].start()].strip():turns.append(('Session text',text[:matches[0][0].start()].strip()))
    for i,(m,label) in enumerate(matches):
        body=text[m.end():matches[i+1][0].start() if i+1<len(matches) else len(text)].strip()
        if body:turns.append((label,body))
    return turns

def readable_quality(text,language):
    if len(text.strip())<50:return 0.
    bad=text.count('\ufffd')/max(len(text),1)
    if language=='hi' and len(re.findall('[\u0900-\u097f]',text))<len(text)*.04:return .2
    return max(0.,1.-bad*15)

def paragraph_chunks(text,size=1400,overlap=220):
    # Keep page provenance; choose sentence boundaries where possible.
    pos=0
    while pos<len(text):
        end=min(pos+size,len(text))
        if end<len(text):
            cut=max(text.rfind('. ',pos+size//2,end),text.rfind('।',pos+size//2,end),text.rfind('\n',pos+size//2,end))
            if cut>pos:end=cut+1
        chunk=text[pos:end].strip()
        if len(chunk)>70:yield chunk
        if end==len(text):break
        pos=max(pos+1,end-overlap)

_pdf_lock=threading.RLock()

def import_pdf(path,meta):
    with _pdf_lock:return _import_pdf(path,meta)

def _import_pdf(path,meta):
    path=Path(path).resolve()
    with path.open('rb') as f:
        if f.read(5)!=b'%PDF-':raise ValueError('Not a PDF')
    with path.open('rb') as original:digest=hashlib.file_digest(original,'sha256').hexdigest()
    doc_id=meta['id']
    with connect() as c:
        existing=c.execute('SELECT checksum,processing_status FROM documents WHERE id=?',(doc_id,)).fetchone()
        if existing and existing['checksum']==digest and existing['processing_status'] in ('ready','ocr_pending'):return {'id':doc_id,'skipped':True}
    pages=[];turns=[];chunks=[];low=0
    with pymupdf.open(path) as pdf:
        if pdf.needs_pass:raise ValueError('Password-protected PDF')
        for i,p in enumerate(pdf):
            raw=clean(p.get_text(sort=False));quality=readable_quality(raw,meta['language'])
            method='embedded text'
            if quality<.4:low+=1;method='needs OCR' if len(raw)<50 or meta['language']=='hi' else 'text quality review'
            pages.append((doc_id,i+1,raw,method,quality,f'PDF page {i+1}'))
            if quality>=.4:
                if meta['category']=='debates':turns.extend((doc_id,i+1,n,s,t) for n,(s,t) in enumerate(split_turns(raw)))
                chunks.extend((doc_id,i+1,t) for t in paragraph_chunks(raw))
    status='ocr_pending' if low>max(3,len(pages)*.15) else 'ready'
    summary=(f"Read the {meta.get('date','')} sitting of the {'Constituent Assembly (Legislative)' if 'legislative' in meta.get('group_key','') else 'Constituent Assembly'}. This local edition contains {len(pages)} PDF pages. Open the reader for the proceedings and speaker-labelled exchanges." if meta['category']=='debates' else f"Explore {meta['title']}, a collected volume of Dr. B. R. Ambedkar’s writings and speeches. This edition has {len(pages)} pages, available to read on this device.")
    columns=['id','title','category','language','date','year','authors','description','source_label','source_url','file_path','checksum','format','page_count','summary','summary_kind','processing_status','group_key']
    values={**meta,'file_path':str(path),'checksum':digest,'format':'pdf','page_count':len(pages),'summary':summary,'summary_kind':'catalogue overview','processing_status':status}
    with connect() as c:
        c.execute('DELETE FROM documents WHERE id=?',(doc_id,))
        c.execute('INSERT INTO documents('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[values.get(k,'') for k in columns])
        c.executemany('INSERT INTO pages VALUES(?,?,?,?,?,?)',pages)
        c.executemany('INSERT INTO turns(document_id,page,ordinal,speaker,text) VALUES(?,?,?,?,?)',turns)
        c.executemany('INSERT INTO chunks(document_id,page,text) VALUES(?,?,?)',chunks)
    return {'id':doc_id,'pages':len(pages),'chunks':len(chunks),'turns':len(turns),'low_text_pages':low,'status':status}
