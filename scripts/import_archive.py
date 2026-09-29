"""Resumable import of corrected user PDFs and downloaded official debate PDFs."""
import sys,csv,re,json,hashlib,shutil,time,argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.db import DATA,ROOT,init_db,job
from ingestion.pipeline import import_pdf

SOURCE=Path(r'C:\Users\Administrator\Desktop\Dharohar Data')
MANIFEST=ROOT/'sources/debates.json'

def csv_records():
    records={}
    for f in SOURCE.rglob('*.csv'):
        for row in csv.DictReader(f.open(encoding='utf-8-sig',newline='')):
            match=re.search(r'https://elibrary\.sansad\.in/items/([\w-]+)',row.get('View',''))
            if not match:continue
            item=match[1];date=datetime.strptime(row['Date'],'%d-%b-%Y').date().isoformat() if row.get('Date','').strip() else ''
            records[item]={'item_id':item,'id':'debate-'+item,'title':row['Title']+' · '+row['Date'],'category':'debates','language':'hi' if 'Hindi' in row['Title'] else 'en','date':date,'year':int(date[:4]) if date else None,'authors':'Constituent Assembly members','description':row['Title'],'source_label':'Parliament Digital Library','source_url':match[0],'group_key':('legislative-' if 'Legislative' in row['Title'] else 'drafting-')+(date or item),'csv_source':str(f.relative_to(SOURCE))}
    return list(records.values())

def resolve(record,cached):
    known=cached.get(record['item_id'])
    if known:
        originals=[f for f in known.get('files',[]) if f['bundle']=='ORIGINAL' and f['name'].lower().endswith('.pdf')]
        if originals:return {**record,'download_url':originals[0]['url'],'expected_bytes':originals[0]['bytes']}
    with httpx.Client(follow_redirects=True,timeout=60) as c:
        r=c.get('https://elibrary.sansad.in/server/api/core/items/'+record['item_id']+'/bundles?size=100');r.raise_for_status()
        for bundle in r.json().get('_embedded',{}).get('bundles',[]):
            if bundle['name']!='ORIGINAL':continue
            r=c.get('https://elibrary.sansad.in/server/api/core/bundles/'+bundle['uuid']+'/bitstreams?size=100');r.raise_for_status()
            for bit in r.json().get('_embedded',{}).get('bitstreams',[]):
                if bit['name'].lower().endswith('.pdf'):
                    return {**record,'download_url':'https://elibrary.sansad.in/server/api/core/bitstreams/'+bit['uuid']+'/content','expected_bytes':bit.get('sizeBytes',0)}
    raise ValueError('No public PDF bitstream found')

def fetch_import(record):
    path=DATA/'originals'/(record['id']+'.pdf')
    if not path.exists():
        if shutil.disk_usage(DATA).free<10*1024**3:raise ValueError('10 GB storage reserve reached')
        temp=path.with_suffix('.part')
        for attempt in range(3):
            try:
                with httpx.Client(timeout=90,follow_redirects=True) as c,c.stream('GET',record['download_url']) as r:
                    r.raise_for_status();size=0
                    with temp.open('wb') as out:
                        for block in r.iter_bytes(1024*1024):
                            if size==0 and not block.startswith(b'%PDF-'):raise ValueError('Source response is not a PDF')
                            size+=len(block)
                            if size>800*1024**2:raise ValueError('PDF exceeds 800 MB bound')
                            out.write(block)
                if record.get('expected_bytes') and size!=record['expected_bytes']:raise ValueError('Incomplete PDF download')
                temp.replace(path);break
            except Exception:
                if attempt==2:raise
                time.sleep(attempt+1)
    return import_pdf(path,record)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cached-manifest',type=Path);parser.add_argument('--limit',type=int);parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    init_db();reports=[];job('import','running','Importing supplied writings')
    for file in sorted((SOURCE/'Writings and Speeches').glob('*.pdf')):
        if file.name.startswith('._'):continue
        parts=file.stem.split('_')[1:];vol=int(parts[0]);part=(' · Part '+str(int(parts[1]))) if len(parts)>1 else ''
        meta={'id':'writing-'+file.stem.lower(),'title':f'Writings & Speeches · Volume {vol}'+part,'category':'writings','language':'en','authors':'Dr. B. R. Ambedkar','source_label':'User-supplied Dr. Ambedkar Foundation edition','source_url':'','group_key':file.stem,'description':'Collected writings and speeches, supplied by the user.'}
        target=DATA/'originals'/file.name
        with file.open('rb') as original:source_hash=hashlib.file_digest(original,'sha256').hexdigest()
        target_hash=None
        if target.exists():
            with target.open('rb') as previous:target_hash=hashlib.file_digest(previous,'sha256').hexdigest()
        if source_hash!=target_hash:
            if target.exists():
                revisions=DATA/'originals/revisions';revisions.mkdir(exist_ok=True)
                backup=revisions/(target.stem+'-'+target_hash[:12]+'.pdf')
                if not backup.exists():shutil.copyfile(target,backup)
            incoming=target.with_suffix('.incoming');shutil.copyfile(file,incoming);incoming.replace(target)
        try:r=import_pdf(target,meta);reports.append(r);print(r,flush=True)
        except Exception as e:
            reports.append({'id':meta['id'],'error':str(e)});print(reports[-1],flush=True)
    records=csv_records();cached={}
    if args.cached_manifest and args.cached_manifest.exists():
        for d in json.loads(args.cached_manifest.read_text(encoding='utf-8')):
            for item in d.get('items',[]):cached[item['id']]=d
    if MANIFEST.exists():
        old={r['item_id']:r for r in json.loads(MANIFEST.read_text(encoding='utf-8'))}
        records=[{**r,**{k:old[r['item_id']][k] for k in ('download_url','expected_bytes') if k in old[r['item_id']]}} if r['item_id'] in old else r for r in records]
    resolved=[];errors=[]
    for r in records:
        try:resolved.append(r if r.get('download_url') else resolve(r,cached))
        except Exception as e:errors.append({'id':r['id'],'error':str(e)})
    MANIFEST.write_text(json.dumps(resolved,ensure_ascii=False,indent=2),encoding='utf-8')
    # Small files first gets the reader useful quickly while larger scans follow.
    selected=sorted(resolved,key=lambda x:(x.get('expected_bytes',10**9),x['language']!='en'))
    if args.limit:selected=selected[:args.limit]
    completed=0;job('import','running',f'Downloading {len(selected)} debate PDFs; 20 writing volumes imported')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(fetch_import,r):r for r in selected}
        for f in as_completed(pending):
            r=pending[f];completed+=1
            try:result=f.result();reports.append(result)
            except Exception as e:result={'id':r['id'],'error':str(e)};errors.append(result)
            if completed%10==0 or 'error' in result:
                print(completed,'/',len(selected),result,flush=True)
                job('import','running',f'{completed}/{len(selected)} debate download/import attempts completed; {len(errors)} errors')
                (ROOT/'docs/import-report.json').write_text(json.dumps({'completed':completed,'total':len(selected),'results':reports,'errors':errors},indent=2))
    job('import','complete' if not errors else 'needs_attention',f'{completed} debate attempts finished; {len(errors)} errors. OCR assessment recorded per document.')
    (ROOT/'docs/import-report.json').write_text(json.dumps({'completed':completed,'total':len(selected),'results':reports,'errors':errors},indent=2))
    print('Import pass complete.',flush=True)

if __name__=='__main__':main()
