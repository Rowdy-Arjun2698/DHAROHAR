"""Resume OCR page by page. Native Tesseract or isolated local Docker engine."""
import sys,subprocess,time,json,threading,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf
from app.db import connect,job,init_db
from ingestion.pipeline import clean,paragraph_chunks,split_turns,readable_quality
render_lock=threading.Lock()

def process(row):
    with render_lock,pymupdf.open(row['file_path']) as doc:
        pix=doc[row['number']-1].get_pixmap(dpi=150);data=pix.tobytes('png')
    lang='hin+eng' if row['language']=='hi' else 'eng'
    result=subprocess.run(['docker','exec','-i','dharohar-ocr','tesseract','stdin','stdout','-l',lang,'--psm','3'],input=data,capture_output=True,timeout=100)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[:150])
    text=clean(result.stdout.decode('utf-8'));quality=readable_quality(text,row['language'])
    with connect() as c:
        c.execute('UPDATE pages SET text=?,quality=?,method=? WHERE document_id=? AND number=?',(text,quality,'Tesseract OCR — unreviewed',row['document_id'],row['number']))
        c.execute('DELETE FROM chunks WHERE document_id=? AND page=?',(row['document_id'],row['number']))
        c.execute('DELETE FROM turns WHERE document_id=? AND page=?',(row['document_id'],row['number']))
        if quality>=.4:
            c.executemany('INSERT INTO chunks(document_id,page,text) VALUES(?,?,?)',[(row['document_id'],row['number'],t) for t in paragraph_chunks(text)])
            if row['category']=='debates':c.executemany('INSERT INTO turns(document_id,page,ordinal,speaker,text) VALUES(?,?,?,?,?)',[(row['document_id'],row['number'],i,s,t) for i,(s,t) in enumerate(split_turns(text))])
    return row['document_id'],row['number'],len(text)

if __name__=='__main__':
    init_db();done=0;errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        while True:
            with connect() as c:rows=[dict(r) for r in c.execute("SELECT p.*,d.file_path,d.language,d.category FROM pages p JOIN documents d ON d.id=p.document_id WHERE p.quality<.4 AND p.method NOT LIKE 'Tesseract%' AND p.method!='OCR failed' ORDER BY CASE WHEN d.category='debates' THEN 0 ELSE 1 END,p.number LIMIT 10")]
            if not rows:break
            for future,row in [(pool.submit(process,r),r) for r in rows]:
                try:result=future.result();done+=1
                except Exception as e:
                    errors.append(str(e));result=(row['document_id'],row['number'],'failed')
                    with connect() as c:c.execute("UPDATE pages SET method='OCR failed' WHERE document_id=? AND number=?",(row['document_id'],row['number']))
                print(result,flush=True);job('ocr','running',f'{done} pages OCR processed in this run; {len(errors)} errors. OCR text needs review.')
    with connect() as c:
        c.execute("UPDATE documents SET processing_status='ready' WHERE NOT EXISTS(SELECT 1 FROM pages p WHERE p.document_id=documents.id AND p.quality<.4 AND p.method NOT LIKE 'Tesseract%')")
    job('ocr','complete' if not errors else 'needs_attention',f'{done} pages OCR processed; {len(errors)} errors. Text remains unreviewed.')
