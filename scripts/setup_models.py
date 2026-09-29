"""Explicit local model/runtime installation. No downloads occur inside a chat request."""
import sys,json,hashlib,zipfile,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'runtime';MODELS=ROOT/'data/models'
MODELS.mkdir(parents=True,exist_ok=True)

def download(url,path,limit):
    if path.exists() and path.stat().st_size>1000:return path
    partial=path.with_suffix(path.suffix+'.part')
    for attempt in range(4):
        try:
            offset=partial.stat().st_size if partial.exists() else 0
            with httpx.Client(timeout=90,follow_redirects=True) as c,c.stream('GET',url,headers={'Range':f'bytes={offset}-'} if offset else {}) as r:
                r.raise_for_status();append=offset and r.status_code==206
                size=offset if append else 0
                with partial.open('ab' if append else 'wb') as out:
                    for block in r.iter_bytes(1024*1024):
                        size+=len(block)
                        if size>limit:raise ValueError('Download exceeds configured limit')
                        out.write(block)
            partial.replace(path)
            print(path.name,path.stat().st_size,'bytes',flush=True);return path
        except Exception as e:
            print('Retry',path.name,str(e),flush=True)
            if attempt==3:raise
            time.sleep(2)

def install_asset(asset):
    target=ROOT/asset['path'];target.parent.mkdir(parents=True,exist_ok=True)
    def verified():
        if not target.exists() or target.stat().st_size!=asset['bytes']:return False
        with target.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==asset['sha256']
    if verified():return target
    if target.exists():
        # Keep a failed/corrupted previous file for investigation; never silently reuse it.
        target.replace(target.with_name(target.name+'.invalid-'+str(int(time.time()))))
    download(asset['url'],target,asset['bytes']+1024)
    if not verified():raise ValueError('Checksum mismatch: '+asset['path'])
    return target

if __name__=='__main__':
    manifest=json.loads((ROOT/'sources/models.json').read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(install_asset,manifest['assets']))
    archive=ROOT/manifest['llama_archive'];target=RUNTIME/'llama';target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (target/item.filename).resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe runtime archive path')
        z.extractall(target)
    print('Pinned local AI models and Windows runtime verified. Docker supplies speech output and OCR.',flush=True)
