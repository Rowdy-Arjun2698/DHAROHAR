"""Explicitly install pinned neural narrators for the local research prototype."""
import hashlib,json,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.setup_models import download,install_asset
ROOT=Path(__file__).resolve().parents[1]
REV='c10ece1aade47bb51c153c893d14e5bf8e5b7117'
VOICES=['en_US-ryan-medium','en_US-ljspeech-medium','en_GB-alan-medium','hi_IN-pratham-medium','hi_IN-priyamvada-medium']

def install(name):
    locale,speaker,quality=name.split('-');lang=locale.split('_')[0]
    base=f'https://huggingface.co/rhasspy/piper-voices/resolve/{REV}/{lang}/{locale}/{speaker}/{quality}/'
    folder=ROOT/'data/models/piper';folder.mkdir(parents=True,exist_ok=True)
    assets=[]
    for suffix in ['.onnx','.onnx.json','-MODEL_CARD.md']:
        filename=name+suffix;remote='MODEL_CARD' if suffix=='-MODEL_CARD.md' else filename
        path=download(base+remote,folder/filename,100_000_000)
        assets.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'url':base+remote,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return assets

if __name__=='__main__':
    manifest=ROOT/'sources/neural-voices.json'
    if manifest.exists():
        for asset in json.loads(manifest.read_text(encoding='utf-8'))['assets']:install_asset(asset)
        print('Pinned neural narrators verified.');sys.exit(0)
    assets=[]
    with ThreadPoolExecutor(3) as pool:
        for group in pool.map(install,VOICES):assets.extend(group)
    (ROOT/'sources/neural-voices.json').write_text(json.dumps({'revision':REV,'notice':'Synthetic narrators, not replicas of historical speakers. Voice-specific dataset licences are included; Ryan and Hindi models have noncommercial conditions. Review rights before a commercial release. Piper runtime is GPL-3.0.','assets':assets},indent=2),encoding='utf-8')
