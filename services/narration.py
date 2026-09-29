"""Stable synthetic narrator casting. No historical voice cloning."""
import hashlib,io,json,re,threading,wave
from collections import OrderedDict
from app.db import DATA

_voices=OrderedDict();_lock=threading.RLock()
PROFILES={'warm':'Warm guide','clear':'Clear storyteller','strong':'Resonant narrator'}
# Explicit titles and a limited historical roster; never infer gender from an arbitrary name.
FEMALE=re.compile(r'\b(mrs\.?|miss|shrimati|srimati|smt\.?|begum|hansa mehta|durgabai|dakshayani|sucheta|renuka ray|purnima|sarojini)\b|श्रीमती|बेगम|दुर्गाबाई',re.I)
MALE=re.compile(r'\b(mr\.?|shri|sri|pandit|ambedkar|rajendra prasad|jawaharlal nehru|vallabhbhai patel)\b|अंबेडकर|आंबेडकर|अम्बेडकर|श्री\s|पंडित',re.I)
AMBEDKAR=re.compile(r'ambedkar|अंबेडकर|आंबेडकर|अम्बेडकर',re.I)

def known_gender(speaker=''):
    if speaker and FEMALE.search(speaker):return 'Female'
    if speaker and MALE.search(speaker):return 'Male'
    return None

def cast(speaker='',profile='warm'):
    if speaker and FEMALE.search(speaker):return 'female'
    if speaker and AMBEDKAR.search(speaker):return 'strong'
    if speaker and MALE.search(speaker):return 'male'
    return {'warm':'female','clear':'male','strong':'strong'}.get(profile,'female')

def voice_name(language,speaker='',profile='warm'):
    role=cast(speaker,profile)
    if language=='hi':return 'hi_IN-priyamvada-medium' if role=='female' else 'hi_IN-pratham-medium'
    if language=='en':
        if role=='female':return 'en_US-ljspeech-medium'
        if role=='strong':return 'en_US-ryan-medium'
        return ['en_GB-alan-medium','en_US-ryan-medium'][int(hashlib.sha256(speaker.encode()).hexdigest()[:2],16)%2] if speaker else 'en_GB-alan-medium'
    raise ValueError('Neural narration for this language needs Sarvam. Local neural voices currently cover English and Hindi.')

def available_languages():
    folder=DATA/'models/piper'
    return [lang for lang,name in [('en','en_US-ljspeech-medium'),('hi','hi_IN-priyamvada-medium')] if (folder/(name+'.onnx')).is_file()]

def clean_speech(text):
    return re.sub(r'\s+',' ',re.sub(r'\[\d+\]|[*#_`]', '',text)).strip()

def synthesize(text,language='en',speaker='',profile='warm',pace=1.):
    from piper import PiperVoice,SynthesisConfig
    from piper.config import PiperConfig
    import onnxruntime as ort
    name=voice_name(language,speaker,profile);folder=DATA/'models/piper';path=folder/(name+'.onnx')
    if not path.exists():raise RuntimeError('Neural voice is missing. Run scripts/setup_neural_voices.py.')
    with _lock:
        if name not in _voices:
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            options.add_session_config_entry('session.intra_op.allow_spinning','0')
            _voices[name]=PiperVoice(session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider']),config=PiperConfig.from_dict(json.loads(path.with_suffix('.onnx.json').read_text(encoding='utf-8'))))
            if len(_voices)>3:_voices.popitem(last=False)
        model=_voices[name];_voices.move_to_end(name)
        # A small stable cadence variation helps separate speakers without claiming an authentic voice.
        cadence=(.98+(int(hashlib.md5(speaker.encode()).hexdigest()[:2],16)%5)*.018) if speaker else 1.
        config=SynthesisConfig(length_scale=cadence/max(.75,min(1.4,pace)),noise_scale=.65,noise_w_scale=.8,normalize_audio=True)
        output=io.BytesIO()
        with wave.open(output,'wb') as wav:model.synthesize_wav(clean_speech(text),wav,syn_config=config)
        return output.getvalue(),'audio/wav'
