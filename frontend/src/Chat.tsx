import {useEffect,useRef,useState} from 'react';
import {Sparkles,Send,X,BookOpen,ArrowUpRight,LoaderCircle,Globe2} from 'lucide-react';
import Voice from './Voice';
import {langs} from './api';

export default function Chat({voice=false,params,status}:{voice?:boolean,params:URLSearchParams,status:any}){
 const storage=voice?'dharohar-voice-language':'dharohar-chat-language';
 const [language,setLanguage]=useState(localStorage.getItem(storage)||'en'),[messages,setMessages]=useState<any[]>([]),[q,setQ]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[stage,setStage]=useState('Preparing an answer');
 const controller=useRef<AbortController|null>(null),generation=useRef(0),end=useRef<HTMLDivElement>(null);
 useEffect(()=>{localStorage.setItem(storage,language)},[language,storage]);
 useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth',block:'nearest'})},[messages.length]);
 useEffect(()=>()=>{generation.current++;controller.current?.abort()},[]);
 function stop(){generation.current++;controller.current?.abort();setBusy(false)}
 async function send(text=q){
   if(!text.trim()||busy)return;const token=++generation.current;setError('');setQ('');const history=messages.map(m=>({role:m.role,content:m.content}));setMessages(m=>[...m,{role:'user',content:text}]);setBusy(true);setStage('Understanding your question');controller.current=new AbortController();
   try{
     const response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,language,history:history.slice(-6),document_id:params.get('document')||null}),signal:controller.current.signal});
     if(!response.ok)throw new Error('The assistant could not be reached. Please try again.');
     const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer='',complete=false;
     while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let split;while((split=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,split);buffer=buffer.slice(split+2);if(!block.startsWith('data: '))continue;const event=JSON.parse(block.slice(6));if(token!==generation.current)return;if(event.type==='progress')setStage(event.stage);if(event.type==='answer'){complete=true;setMessages(m=>[...m,{role:'assistant',content:event.answer,...event}])}}}
     if(!complete&&token===generation.current)throw new Error('The connection ended before the answer was ready. Please try again.');
   }catch(e:any){if(e.name!=='AbortError'&&token===generation.current)setError(e.message)}finally{if(token===generation.current)setBusy(false)}
 }
 return <div className="chat-page"><div className="chat-intro"><div className="eyebrow">YOUR GUIDE TO AMBEDKAR’S WORLD</div><h1>{voice?'Let’s talk about Ambedkar.':'A question can open a whole new world.'}</h1><p>Say hello, follow your curiosity, and explore ideas through clear explanations.</p><div className="conversation-preferences"><label><Globe2 size={17}/>{voice?'Spoken conversation language':'Chat language'}<select value={language} aria-label={voice?'Voice conversation language':'Chat conversation language'} onChange={e=>{stop();setLanguage(e.target.value)}}>{langs.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><span>Changes this conversation only.</span></div><span className="ai-status"><span className={status?.ai?.ready?'ready-dot':'pending-dot'}/>{status?.ai?.ready?(status.ai.provider==='sarvam'?'Online assistant ready':'Local assistant ready'):'Assistant is starting or unavailable'}</span></div>
  {voice&&<Voice key={language} language={language} history={messages} onTranscript={text=>setMessages(m=>[...m,{role:'user',content:text}])} onAnswer={r=>setMessages(m=>[...m,{role:'assistant',content:r.answer,...r}])}/>}
  <div className="conversation">{!messages.length&&!voice&&<div className="suggestions">{['Hello! What can you help me explore?','Why did Ambedkar argue for the abolition of caste?','Explain constitutional morality in simple words.'].map(s=><button key={s} onClick={()=>void send(s)}><Sparkles size={17}/><span>{s}</span><ArrowUpRight size={17}/></button>)}</div>}
   {messages.map((m,i)=><article key={i} className={'message '+m.role}>{m.role==='assistant'&&<div className="assistant-avatar"><Sparkles size={18}/></div>}<div className="message-body"><span className="message-name">{m.role==='user'?'YOU':'DHAROHAR'}</span><div className="answer-text">{m.content}</div>{m.citations?.length>0&&<details className="citations"><summary><BookOpen size={15}/>{m.citations.length} sources behind this explanation</summary>{m.citations.map((c:any)=><a key={c.id} href={'#/read/'+c.document_id+'?page='+c.page}><strong>[{c.id}] {c.title} · page {c.page}</strong><blockquote>{c.quote}</blockquote><span>Read in context<ArrowUpRight size={14}/></span></a>)}</details>}{m.grounding?.notice&&<p className="grounding-note">{m.grounding.notice}</p>}</div></article>)}
   {busy&&<div className="thinking" role="status"><LoaderCircle className="spin" size={18}/>{stage}…</div>}<div ref={end}/></div>
  {error&&<p className="error" role="alert">{error}</p>}<form className="composer" onSubmit={e=>{e.preventDefault();void send()}}><textarea aria-label="Your question" value={q} onChange={e=>setQ(e.target.value)} placeholder="Ask a question, say hello, or follow up…" maxLength={1500} rows={2} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send()}}}/>{busy?<button className="send-button" type="button" aria-label="Stop generating" onClick={stop}><X size={21}/></button>:<button className="send-button" aria-label="Send question" disabled={!q.trim()}><Send size={20}/></button>}</form><div className="chat-foot"><span>AI can make mistakes. Open the sources to check.</span><button className="text-link" onClick={()=>{stop();setMessages([]);setError('')}}>New conversation</button></div>
 </div>
}
