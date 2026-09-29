"""Independent local NLI check; scores are model signals, not correctness guarantees."""
import json,re,threading
import numpy as np
from app.db import DATA
_session=None;_tokenizer=None;_lock=threading.RLock()

def evidence_score(source,claim):
    global _session,_tokenizer
    with _lock:
        if _session is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            folder=DATA/'models/nli'
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            options.add_session_config_entry('session.intra_op.allow_spinning','0')
            _session=ort.InferenceSession(str(folder/'model_quantized.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
            _tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'));_tokenizer.enable_truncation(max_length=512,strategy='only_first')
        words=re.sub(r'\s+',' ',source).strip().split(' ')
        windows=[source] if len(words)<=110 else [' '.join(words[i:i+110]) for i in range(0,max(1,len(words)-55),55)]
        best={'score':0.,'quote':source,'contradiction':0.}
        for window in windows:
            token=_tokenizer.encode(window,claim)
            inputs={'input_ids':np.array([token.ids],dtype=np.int64),'attention_mask':np.array([token.attention_mask],dtype=np.int64)}
            logits=_session.run(None,inputs)[0][0];prob=np.exp(logits-logits.max());prob=prob/prob.sum()
            best['contradiction']=max(best['contradiction'],float(prob[2]))
            if float(prob[0])>best['score']:best.update(score=float(prob[0]),quote=window)
        return best
