import os,sqlite3,json
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
DATA=Path(os.getenv('DHAROHAR_DATA',str(ROOT/'data'))).resolve()

@contextmanager
def connect():
    DATA.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DATA/'archive.sqlite3',timeout=60)
    c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=60000')
    try:yield c;c.commit()
    except: c.rollback();raise
    finally:c.close()

def init_db():
    for folder in ['originals','cache','models','logs']: (DATA/folder).mkdir(parents=True,exist_ok=True)
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,language TEXT NOT NULL DEFAULT 'en',date TEXT,year INTEGER,authors TEXT DEFAULT '',description TEXT DEFAULT '',source_label TEXT DEFAULT '',source_url TEXT DEFAULT '',file_path TEXT NOT NULL,checksum TEXT NOT NULL,format TEXT DEFAULT 'pdf',page_count INTEGER DEFAULT 0,summary TEXT DEFAULT '',summary_kind TEXT DEFAULT 'overview',key_points TEXT DEFAULT '[]',processing_status TEXT DEFAULT 'extracting',group_key TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS docs_category ON documents(category,date);
        CREATE TABLE IF NOT EXISTS pages(document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,number INTEGER,text TEXT NOT NULL,method TEXT,quality REAL,label TEXT,PRIMARY KEY(document_id,number));
        CREATE TABLE IF NOT EXISTS turns(id INTEGER PRIMARY KEY,document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,page INTEGER,ordinal INTEGER,speaker TEXT,text TEXT);
        CREATE INDEX IF NOT EXISTS turns_page ON turns(document_id,page);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,page INTEGER,text TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(document_id,page);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text,content=chunks,content_rowid=id,tokenize='unicode61');
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN INSERT INTO chunks_fts(rowid,text) VALUES(new.id,new.text); END;
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts,rowid,text) VALUES('delete',old.id,old.text); END;
        CREATE TABLE IF NOT EXISTS embeddings(chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,model_id TEXT,vector BLOB,text_hash TEXT);
        CREATE TABLE IF NOT EXISTS translations(cache_key TEXT PRIMARY KEY,language TEXT,text TEXT,provider TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS summaries(document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,language TEXT,summary TEXT,key_points TEXT,kind TEXT,citations TEXT,PRIMARY KEY(document_id,language));
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,state TEXT,message TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY,kind TEXT,payload TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        ''')

def job(key,state,message):
    with connect() as c:c.execute('INSERT OR REPLACE INTO jobs(id,state,message) VALUES(?,?,?)',(key,state,message))
