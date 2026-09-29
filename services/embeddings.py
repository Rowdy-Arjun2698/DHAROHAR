import threading,hashlib,json,time
import numpy as np
from app.db import DATA,connect
_session=None;_tokenizer=None;_lock=threading.RLock();_matrix=None;_ids=[];_stamp=0
MODEL=DATA/'models/multilingual-minilm'

def encode(texts):
    global _session,_tokenizer
    with _lock:
        if _session is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            options.add_session_config_entry('session.intra_op.allow_spinning','0')
            _session=ort.InferenceSession(str(MODEL/'model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
            _tokenizer=Tokenizer.from_file(str(MODEL/'tokenizer.json'));_tokenizer.enable_truncation(max_length=128);_tokenizer.enable_padding(pad_id=0,pad_token='[PAD]')
        tokens=_tokenizer.encode_batch(texts)
        arrays={key:np.array([getattr(t,attr) for t in tokens],dtype=np.int64) for key,attr in [('input_ids','ids'),('attention_mask','attention_mask'),('token_type_ids','type_ids')]}
        out=_session.run(None,{i.name:arrays[i.name] for i in _session.get_inputs()})[0]
        mask=arrays['attention_mask'][...,None];v=(out*mask).sum(1)/np.maximum(mask.sum(1),1)
        return (v/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-9)).astype(np.float32)

def semantic(query,limit=35):
    global _matrix,_ids,_stamp
    if not (MODEL/'model.onnx').exists():return []
    with _lock:
        if _matrix is None or time.monotonic()-_stamp>40:
            with connect() as c:rows=c.execute('SELECT chunk_id,vector FROM embeddings').fetchall()
            if not rows:return []
            _ids=[r['chunk_id'] for r in rows];_matrix=np.stack([np.frombuffer(r['vector'],dtype=np.float32) for r in rows]);_stamp=time.monotonic()
        scores=_matrix@encode([query])[0]
        indices=np.argsort(scores)[-limit:][::-1]
        return [(_ids[i],float(scores[i])) for i in indices if scores[i]>=.46]

def index_missing(batch_size=24):
    while True:
        with connect() as c:rows=c.execute('SELECT ch.id,ch.text FROM chunks ch LEFT JOIN embeddings e ON e.chunk_id=ch.id WHERE e.chunk_id IS NULL LIMIT ?',(batch_size,)).fetchall()
        if not rows:break
        vectors=encode([r['text'] for r in rows])
        with connect() as c:
            for row,v in zip(rows,vectors):
                current=c.execute('SELECT text FROM chunks WHERE id=?',(row['id'],)).fetchone()
                if current and current['text']==row['text']:c.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?)',(row['id'],'minilm-qint8-e8f8c211',v.tobytes(),hashlib.sha256(row['text'].encode()).hexdigest()))
        yield len(rows)
