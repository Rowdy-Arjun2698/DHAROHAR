import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db import init_db,job,connect
from services.embeddings import index_missing
init_db();count=0
while True:
    job('embeddings','running','Building local multilingual search index')
    for n in index_missing():
        count+=n
        if count%480==0:print('Encoded',count,flush=True);job('embeddings','running',f'{count} new passages encoded in this run')
    with connect() as c:active=c.execute("SELECT 1 FROM jobs WHERE id IN ('import','ocr') AND state='running'").fetchone()
    if not active:break
    time.sleep(10)
job('embeddings','complete',f'{count} new passages encoded');print('Embedding index complete',count,flush=True)
