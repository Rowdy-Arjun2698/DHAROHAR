import os,shutil,subprocess,tempfile,threading,time,base64,hashlib
from pathlib import Path
import httpx
from app.db import ROOT,DATA
_model=None;_lock=threading.Lock();_speech_check=(0.,False)

def espeak_path():
    configured=os.getenv('ESPEAK_BIN');local=ROOT/'runtime/espeak/eSpeak NG/espeak-ng.exe'
    return configured or (str(local) if local.exists() else shutil.which('espeak-ng'))

def capabilities():
    global _speech_check
    if os.getenv('VOICE_PROVIDER')=='sarvam':
        ready=bool(os.getenv('SARVAM_API_KEY'));return {'stt':ready,'tts':ready,'sarvam':ready,'mode':'sarvam','languages':['en','hi','mr','gu','bn','ta','te','kn','ml','pa'],'notice':'Sarvam neural voices · synthetic narration'}
    if os.getenv('TTS_ENGINE','piper')=='piper':
        from services.narration import available_languages
        languages=available_languages()
        return {'stt':(DATA/'models/whisper-small/model.bin').exists(),'tts':bool(languages),'sarvam':bool(os.getenv('SARVAM_API_KEY')),'mode':'local','languages':languages,'notice':'Local Whisper + neural narration · synthetic voices'}
    if os.name=='nt' and os.getenv('TTS_ENGINE','docker')=='docker':
        if time.monotonic()-_speech_check[0]>30:
            try:
                r=subprocess.run(['docker','inspect','-f','{{.State.Running}}','dharohar-ocr'],capture_output=True,timeout=4)
                _speech_check=(time.monotonic(),r.returncode==0 and r.stdout.strip()==b'true')
            except (OSError,subprocess.TimeoutExpired):_speech_check=(time.monotonic(),False)
        tts=_speech_check[1]
    else:tts=bool(espeak_path())
    return {'stt':(DATA/'models/whisper-small/model.bin').exists(),'tts':tts,'sarvam':bool(os.getenv('SARVAM_API_KEY')),'mode':'local','notice':'Local Whisper + eSpeak. Naturalness and latency differ from cloud voice systems.'}

def transcribe(path,language='auto'):
    global _model
    start=time.perf_counter()
    if language not in ('auto','en','hi','mr','gu','bn','ta','te','kn','ml','pa'):raise ValueError('Unsupported speech language')
    if os.getenv('VOICE_PROVIDER')=='sarvam':
        with open(path,'rb') as f:
            r=httpx.post('https://api.sarvam.ai/speech-to-text',headers={'api-subscription-key':os.environ['SARVAM_API_KEY']},files={'file':('speech.wav',f,'audio/wav')},data={'model':'saaras:v3','language_code':language+'-IN' if language!='auto' else 'unknown'},timeout=80)
        r.raise_for_status();data=r.json();return {'text':data.get('transcript',''),'language':data.get('language_code',language),'elapsed_ms':round((time.perf_counter()-start)*1000)}
    model_path=DATA/'models/whisper-small'
    if not (model_path/'model.bin').exists():raise RuntimeError('Whisper model is not installed.')
    with _lock:
        from faster_whisper import WhisperModel
        if _model is None:_model=WhisperModel(str(model_path),device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,local_files_only=True)
        segments,info=_model.transcribe(str(path),language=None if language=='auto' else language,beam_size=1,vad_filter=True,condition_on_previous_text=False)
        text=' '.join(s.text.strip() for s in segments if s.no_speech_prob<.75)
    return {'text':text,'language':info.language,'elapsed_ms':round((time.perf_counter()-start)*1000)}

def synthesize(text,language='en',speaker='',profile='warm',pace=1.):
    from services.narration import clean_speech,cast
    text=clean_speech(text)
    if not text:raise ValueError('There is no text to read.')
    if len(text)>2500:raise ValueError('Split narration into passages of at most 2500 characters.')
    identity='neural-v2:'+str((os.getenv('VOICE_PROVIDER','local'),os.getenv('TTS_ENGINE','piper'),text,language,speaker,profile,pace))
    cache=DATA/'cache'/('speech-'+hashlib.sha256(identity.encode()).hexdigest()+'.wav')
    if cache.exists():return cache.read_bytes(),'audio/wav'
    if os.getenv('VOICE_PROVIDER')!='sarvam' and os.getenv('TTS_ENGINE','piper')=='piper':
        from services.narration import synthesize as neural
        data,mime=neural(text,language,speaker,profile,pace)
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
        return data,mime
    if os.getenv('VOICE_PROVIDER')=='sarvam':
        role=cast(speaker,profile)
        pool={'female':['ritu','priya','neha'],'male':['shubh','rahul','rohan'],'strong':['aditya']}[role]
        voice_id=pool[int(hashlib.sha256(speaker.casefold().encode()).hexdigest()[:4],16)%len(pool)] if speaker else pool[0]
        r=httpx.post('https://api.sarvam.ai/text-to-speech',headers={'api-subscription-key':os.environ['SARVAM_API_KEY']},json={'text':text,'language_code':language+'-IN','model':'bulbul:v3','speaker':voice_id,'pace':pace,'speech_sample_rate':24000},timeout=35);r.raise_for_status()
        data=base64.b64decode(r.json()['audios'][0]);cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
        return data,'audio/wav'
    if os.name=='nt' and os.getenv('TTS_ENGINE','docker')=='docker':
        result=subprocess.run(['docker','exec','-i','dharohar-ocr','espeak-ng','-v',language,'-s','155','--stdout'],input=text[:4000].encode('utf-8'),capture_output=True,timeout=40)
        if result.returncode or result.stdout[:4]!=b'RIFF':raise RuntimeError('Speech output is unavailable. Start the local speech/OCR container.')
        return result.stdout,'audio/wav'
    executable=espeak_path()
    if not executable:raise RuntimeError('Local speech output is not installed.')
    with tempfile.TemporaryDirectory() as folder:
        output=Path(folder)/'voice.wav'
        result=subprocess.run([executable,'-v',language,'-s','155','-w',str(output),'--stdin'],input=text[:4000].encode('utf-8'),capture_output=True,timeout=35)
        if result.returncode or not output.exists():
            fallback=subprocess.run(['docker','exec','-i','dharohar-ocr','espeak-ng','-v',language,'-s','155','--stdout'],input=text[:4000].encode('utf-8'),capture_output=True,timeout=40)
            if fallback.returncode or fallback.stdout[:4]!=b'RIFF':raise RuntimeError('Speech output is unavailable. Start the local speech/OCR container.')
            return fallback.stdout,'audio/wav'
        return output.read_bytes(),'audio/wav'
