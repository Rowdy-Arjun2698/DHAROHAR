# Internal API contract

One FastAPI application serves React at localhost:8010. Use hash routes in the UI. UTF-8 JSON. All errors have `detail`. The development Python executable is C:/Users/Administrator/Documents/Codex/2026-09-25/hey-x20/work/.venv/Scripts/python.exe.

GET /api/status -> {documents,pages,indexed_chunks,by_category:{debates,writings,audio},ingestion:{state,message},ai:{ready,model,provider},voice:{stt,tts,sarvam},languages:[{code,name}],source_notes:[]}
GET /api/catalog?category=debates|writings|audio&q=&language=&offset=0&limit=18 -> {items:[Document],total,offset,limit}
GET /api/documents/{id}?language=en -> Document plus summary, key_points, summary_kind, related_versions
Document: {id,title,category,language,date,year,page_count,summary,summary_kind,key_points:[],source_label,source_url,has_file,format,authors,description,processing_status,group_key}
POST /api/documents/{id}/summary {language} -> {summary,key_points,summary_kind,citations:[],notice?}. This may take time; show the available overview while preparing an AI summary.
GET /api/documents/{id}/read?page=1&language=en -> {document_id,page,page_count,page_label,text,turns:[{id,speaker,initials,color,text,page}],original_language,language,translation_status,notice?}. Read source text quickly; translation can be requested explicitly with POST /api/documents/{id}/translate {page,language}; returns the same reading shape. Translations are machine-labelled.
GET /api/documents/{id}/file -> original PDF or audio, inline, supports range. Never navigate users to external source pages to read.
GET /api/documents/{id}/image?page=1 -> PNG page scan. Can be used as fallback to iframe PDF.
POST /api/chat {message,language,history:[{role,content}],document_id?:string} -> {answer,language,citations:[{id,document_id,title,page,quote}],grounding:{status,checks:[],notice?},provider,elapsed_ms}. Render answer as text, citations open in-app reader. AbortController for cancel. Never claim model ready if not.
POST /api/voice/transcribe multipart file (browser audio/wav),language -> {text,language,elapsed_ms}
POST /api/voice/synthesize {text,language} -> audio/wav or MP3. Browser speechSynthesis may fallback with explicit matching language voice.
WS /api/voice/live: client sends {type:'audio',audio:'base64 PCM16 WAV',language,history} or {type:'cancel'}; server events {type:'state',state:'transcribing|thinking|speaking|ready'}, {type:'transcript',text}, {type:'answer',...chatresponse}, {type:'audio',audio:base64,mime}, {type:'error',message}. Initial message {type:'ready',...capabilities}. Browser VAD should capture utterances, send after silence, restart listening after playback, and cancel via explicit interrupt/stop. Do not claim full-duplex barge-in unless implemented/tested.

## Data ownership

Root owns app/db.py, app/main.py, app/retrieval.py and integrations. Corpus agent owns ingestion/, sources/, scripts/recover_sources.py, scripts/import_archive.py and acquisition reports. UI agent owns frontend/. AI agent owns services/ and model/voice setup scripts/runtime assets. Avoid editing another owner's files.

SQLite data/archive.sqlite3. Root provides app.db.connect and init_db; DATA/ROOT constants. documents table fields: id,title,category,language,date,year,authors,description,source_label,source_url,file_path,checksum,format,page_count,summary,summary_kind,key_points,processing_status,group_key,created_at. file_path is absolute local validated path. pages(document_id,number,text,method,quality,label). turns(id,document_id,page,ordinal,speaker,text). chunks(id,document_id,page,text). chunks_fts text using chunks rowid. embeddings(chunk_id,model_id,vector,text_hash). Documents included only if actual local source valid; saved webpage records stay in recovery manifest, not reader catalogue. processing_status ready|ocr_pending|extracting|error; scanned PDF may remain readable even if OCR pending. Source language derived carefully; original EN/HI versions grouped by session/date. Audio optional with provenance, never substitute narration as an authentic recording.

Services AI interface requested: services.llm.health()->dict; generate(messages:list, max_tokens:int=600, json_schema:dict|None=None)->str; translate(text,target_language)->str; services.voice.transcribe(path,language='auto')->dict; synthesize(text,language)->(bytes,mime); capabilities()->dict. Root handles source selection, grounding and endpoint schema.
