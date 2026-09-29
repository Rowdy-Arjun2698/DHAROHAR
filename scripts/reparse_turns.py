"""Rebuild only debate speaker turns, with atomic batches and resumable hashes.

OCR may keep running. Each page is read again under the write transaction before
its turns change, so an OCR update cannot be overwritten by a stale parse.
Run again after an older OCR worker has been restarted to pick up its later pages.
"""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db import DATA,connect
from ingestion.pipeline import split_turns

VERSION='balanced-speakers-v3'

def fingerprint(text,quality):
    return hashlib.sha256((str(quality)+'\0'+text).encode()).hexdigest()

def main():
    checkpoint=DATA/'cache'/'speaker-reparse.json'
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    state=json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
    completed=state.get('pages',{}) if state.get('version')==VERSION else {}
    cursor=('',0);scanned=changed=turn_count=0;started=time.monotonic()
    while True:
        with connect() as c:
            rows=c.execute('''SELECT p.document_id,p.number,p.text,p.quality
                FROM pages p JOIN documents d ON d.id=p.document_id
                WHERE d.category='debates' AND (p.document_id,p.number)>(?,?)
                ORDER BY p.document_id,p.number LIMIT 50''',cursor).fetchall()
        if not rows:break
        pending=[]
        for row in rows:
            key=f'{row["document_id"]}:{row["number"]}'
            digest=fingerprint(row['text'],row['quality'])
            if completed.get(key)!=digest:pending.append((row['document_id'],row['number'],key))
        updates={}
        if pending:
            with connect() as c:
                c.execute('BEGIN IMMEDIATE')
                for doc_id,page,key in pending:
                    fresh=c.execute('SELECT text,quality FROM pages WHERE document_id=? AND number=?',(doc_id,page)).fetchone()
                    if fresh is None:continue
                    turns=split_turns(fresh['text']) if fresh['quality']>=.4 else []
                    c.execute('DELETE FROM turns WHERE document_id=? AND page=?',(doc_id,page))
                    c.executemany('INSERT INTO turns(document_id,page,ordinal,speaker,text) VALUES(?,?,?,?,?)',[(doc_id,page,i,s,t) for i,(s,t) in enumerate(turns)])
                    updates[key]=fingerprint(fresh['text'],fresh['quality']);changed+=1;turn_count+=len(turns)
            completed.update(updates)
        scanned+=len(rows);cursor=(rows[-1]['document_id'],rows[-1]['number'])
        # Replaying a committed batch after a crash is harmless. The checkpoint
        # is replaced only after the matching SQLite transaction has committed.
        temporary=checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':VERSION,'pages':completed}),encoding='utf-8')
        temporary.replace(checkpoint)
        if scanned%1000==0:print(f'Scanned {scanned}; reparsed {changed} pages; {turn_count} turns',flush=True)
    result={'scanned_pages':scanned,'reparsed_pages':changed,'written_turns':turn_count,'seconds':round(time.monotonic()-started,1)}
    print(json.dumps(result),flush=True)
    return result

if __name__=='__main__':main()
