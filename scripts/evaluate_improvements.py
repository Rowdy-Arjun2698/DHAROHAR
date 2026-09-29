"""Small live acceptance set. Explicitly consumes configured provider credits."""
import asyncio,base64,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,websockets
from app.db import ROOT,connect
from services import narration

async def run():
    results={'checked_at':time.strftime('%Y-%m-%d %H:%M:%S'),'chat':[]}
    with httpx.Client(base_url='http://127.0.0.1:8010',timeout=90) as client:
        for question,language,expected in [('Hello','en','social'),('How are you?','en','social'),('What are you?','en','social'),('What is constitutional morality?','en','source_checked'),('Explain social democracy simply.','hi','source_checked'),('Did Ambedkar invent the internet in 1922?','en','insufficient'),('Give me a pizza recipe','en','off_topic')]:
            result=client.post('/api/chat',json={'message':question,'language':language}).raise_for_status().json()
            quotes_match=True
            for citation in result['citations']:
                page=client.get(f"/api/documents/{citation['document_id']}/read",params={'page':citation['page']}).raise_for_status().json()
                quotes_match=quotes_match and ' '.join(citation['quote'].split()).casefold() in ' '.join(page['text'].split()).casefold()
            results['chat'].append({'question':question,'expected':expected,'pass':result['grounding']['status']==expected and quotes_match,'quotes_match':quotes_match,'result':result})
            print(json.dumps({'question':question,'status':result['grounding']['status'],'ms':result['elapsed_ms'],'pass':results['chat'][-1]['pass']}),flush=True)
        start=time.perf_counter();page=client.post('/api/documents/writing-volume_13/translate',json={'page':93,'language':'hi'}).raise_for_status().json()
        first=round(time.perf_counter()-start,3);start=time.perf_counter();client.post('/api/documents/writing-volume_13/translate',json={'page':93,'language':'hi'}).raise_for_status()
        results['translation']={'first_seconds':first,'cached_seconds':round(time.perf_counter()-start,3),'page':page}
        print(json.dumps({'translation_seconds':first,'cached_seconds':results['translation']['cached_seconds']}),flush=True)
        story=client.get('/api/story').raise_for_status().json();sources=[]
        for event in story['events']:
            for source in event['sources']:
                if source.get('document_id'):
                    p=client.get(f"/api/documents/{source['document_id']}/read",params={'page':source['page']})
                    sources.append({'event':event['id'],'page_status':p.status_code})
        results['story_sources']=sources
    # Synthetic microphone substitute; explicitly not a physical microphone quality test.
    wav,_=narration.synthesize('What is constitutional morality?','en',profile='clear')
    start=time.perf_counter();events=[]
    async with websockets.connect('ws://127.0.0.1:8010/api/voice/live',origin='http://127.0.0.1:8010',max_size=8*1024**2) as ws:
        await ws.recv();await ws.send(json.dumps({'type':'audio','request_id':1,'language':'en','profile':'warm','audio':base64.b64encode(wav).decode(),'history':[]}))
        while True:
            event=json.loads(await asyncio.wait_for(ws.recv(),90))
            if event['type']=='audio':
                data=base64.b64decode(event.pop('audio'));event['audio_bytes']=len(data);event['valid_wav']=data[:4]==b'RIFF'
            events.append(event)
            if event['type'] in ('audio','error'):break
    results['voice']={'seconds':round(time.perf_counter()-start,3),'input':'Synthetic English speech, no physical microphone','events':events}
    (ROOT/'docs/improvements-live-evaluation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'voice_seconds':results['voice']['seconds'],'last_event':events[-1]['type']}),flush=True)
    return all(x['pass'] for x in results['chat']) and events[-1]['type']=='audio' and any(e.get('type')=='answer' and e.get('grounding',{}).get('status')=='source_checked' for e in events)

if __name__=='__main__':sys.exit(0 if asyncio.run(run()) else 1)
