import {useEffect,useRef,useState} from 'react';
import {Play,Pause,RotateCcw,Volume2,Square,ChevronRight,LoaderCircle} from 'lucide-react';

type Turn={id:number|string,speaker:string,initials:string,color:string,text:string};
export function readingBlocks(text:string){const blocks:string[]=[];let paragraph='';const flush=()=>{if(paragraph){blocks.push(paragraph);paragraph=''}};for(const raw of text.split('\n')){const line=raw.trim();if(!line){flush();continue}const heading=line.length<110&&/[A-Z]{4}/.test(line)&&line===line.toUpperCase();if(heading){flush();blocks.push(line)}else paragraph+=(paragraph?' ':'')+line}flush();return blocks}
export function speechChunks(text:string,limit=1000){const out:string[]=[];let remaining=text;while(remaining.length){if(remaining.length<=limit){out.push(remaining);break}const head=remaining.slice(0,limit),matches=[...head.matchAll(/[.!?।]\s+/g)];let cut=matches.length?matches[matches.length-1].index!+matches[matches.length-1][0].length:head.lastIndexOf(' ');if(cut<1)cut=limit;out.push(remaining.slice(0,cut));remaining=remaining.slice(cut).trim()}return out}

export default function ReadingExperience({turns,text,language,page,font,documentId}:{turns:Turn[],text:string,language:string,page:number,font:number,documentId:string}){
 const [mode,setMode]=useState<'read'|'watch'>('read'),[visible,setVisible]=useState(0),[running,setRunning]=useState(false),[narrate,setNarrate]=useState(false),[interval,setIntervalSeconds]=useState(2.5),[active,setActive]=useState(-1),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const generation=useRef(0),timer=useRef<ReturnType<typeof setTimeout>|null>(null),context=useRef<AudioContext|null>(null),source=useRef<AudioBufferSourceNode|null>(null),abort=useRef<AbortController|null>(null),activeElement=useRef<HTMLElement|null>(null),next=useRef(0),paused=useRef(false),audioActive=useRef(false);
 const blocks=readingBlocks(text),contextTurns=turns.filter(t=>t.speaker==='Session text'),spokenTurns=turns.filter(t=>t.speaker!=='Session text');
 const items:Turn[]=turns.length?(mode==='watch'&&spokenTurns.length?spokenTurns.flatMap(t=>speechChunks(t.text,500).map((piece,i)=>({...t,id:t.id+'-'+i,text:piece}))):turns):blocks.map((t,i)=>({id:i,speaker:'',initials:'',color:'',text:t}));
 const currentKey=documentId+':'+page+':'+language+':'+text;
 function cancel(){generation.current++;paused.current=false;audioActive.current=false;if(timer.current)clearTimeout(timer.current);timer.current=null;abort.current?.abort();source.current?.stop();source.current=null;setRunning(false);setLoading(false);if(context.current){void context.current.close();context.current=null}}
 function pause(){paused.current=true;if(timer.current){clearTimeout(timer.current);timer.current=null}if(context.current)void context.current.suspend();setRunning(false)}
 useEffect(()=>{cancel();setVisible(0);setActive(-1);next.current=0;setError('')},[currentKey]);
 useEffect(()=>()=>cancel(),[]);
 useEffect(()=>{if(mode==='watch'&&active>=0)activeElement.current?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'nearest'})},[active,mode]);
 async function audio(text:string,speaker:string,token:number){
   for(const piece of speechChunks(text)){
     if(token!==generation.current)return;
     setLoading(true);const controller=new AbortController();abort.current=controller;
     const response=await fetch('/api/voice/synthesize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:piece,language,speaker,profile:'warm'}),signal:controller.signal});
     if(!response.ok){const body=await response.json();throw new Error(body.detail||'Narration is unavailable.')}
     const data=await response.arrayBuffer();if(token!==generation.current)return;
     const ctx=context.current;if(!ctx)return;const buffer=await ctx.decodeAudioData(data);if(token!==generation.current)return;
     setLoading(false);await new Promise<void>((resolve)=>{const node=ctx.createBufferSource();node.buffer=buffer;node.connect(ctx.destination);node.onended=()=>{source.current=null;resolve()};source.current=node;node.start()});
   }
 }
 async function step(index:number,token:number,spoken:boolean){
   if(token!==generation.current)return;
   if(index>=items.length){setRunning(false);setLoading(false);next.current=0;if(context.current){void context.current.close();context.current=null}return}
   next.current=index;setActive(index);setVisible(index+1);
   try{audioActive.current=spoken;if(spoken)await audio(items[index].text,items[index].speaker,token);if(token!==generation.current)return;audioActive.current=false;next.current=index+1;if(!paused.current)timer.current=setTimeout(()=>void step(index+1,token,spoken),spoken?350:interval*1000)}
   catch(e:any){if(token!==generation.current)return;setError(e.message);cancel()}
 }
 function start(spoken=narrate){if(!items.length)return;setError('');setRunning(true);if(paused.current){paused.current=false;if(context.current)void context.current.resume();if(audioActive.current)return;void step(next.current,generation.current,spoken);return}const token=++generation.current;if(spoken){context.current=new AudioContext();void context.current.resume()}void step(next.current,token,spoken)}
 function replay(){cancel();next.current=0;setVisible(0);setActive(-1)}
 const shown=mode==='watch'?items.slice(0,visible):items;
 return <section className="reading-experience">
  <div className="experience-controls"><div className="segmented"><button className={mode==='read'?'selected':''} onClick={()=>{replay();setMode('read')}}>Read at your pace</button>{turns.length>0&&<button className={mode==='watch'?'selected':''} onClick={()=>{replay();setMode('watch')}}>Watch the debate</button>}</div>
   <div className="playback-controls">{running?<button className="button secondary small" onClick={pause}><Pause size={16}/>Pause</button>:<button className="button primary small" onClick={()=>start(mode==='read'||narrate)}><Play size={16}/>{paused.current?'Resume':mode==='read'?'Read aloud':visible===items.length?'Replay debate':visible?'Continue':'Play debate'}</button>}
   <button className="icon-button" aria-label="Replay from beginning" onClick={replay}><RotateCcw size={17}/></button>
   {mode==='watch'&&<><label className="check-label"><input type="checkbox" checked={narrate} onChange={e=>{cancel();setNarrate(e.target.checked)}}/>Narration</label><label>Reveal every <select aria-label="Dialogue reveal interval" value={interval} onChange={e=>{cancel();setIntervalSeconds(Number(e.target.value))}}><option value={2}>2 seconds</option><option value={2.5}>2.5 seconds</option><option value={3}>3 seconds</option><option value={5}>5 seconds</option></select></label><button className="icon-button" aria-label="Next dialogue" disabled={visible>=items.length} onClick={()=>{cancel();setActive(visible);setVisible(visible+1);next.current=visible+1}}><ChevronRight size={18}/></button></>}
   {active>=0&&<button className="icon-button" aria-label="Stop narration" onClick={replay}><Square size={16}/></button>}</div></div>
  <p className="narration-note"><Volume2 size={14}/>Synthetic narration, not an original recording or a recreation of anyone’s actual voice. Speaker names stay as printed in the source.</p>
  {loading&&<p className="small-note" role="status"><LoaderCircle size={15} className="spin"/>Preparing the next spoken passage…</p>}{error&&<p className="error" role="alert">{error}</p>}
  {mode==='watch'&&contextTurns.length>0&&<details className="session-context"><summary>Session context and stage directions</summary>{contextTurns.map(t=><div key={t.id}>{readingBlocks(t.text).map((p,i)=><p key={i}>{p}</p>)}</div>)}</details>}
  {mode==='watch'&&<div className="debate-progress"><span>{visible} of {items.length} passages on this page</span><progress value={visible} max={Math.max(1,items.length)}/></div>}
  <div className={'reading-surface '+(mode==='watch'?'debate-theatre':'')} style={{fontSize:font}}>
   {!shown.length&&<div className="debate-curtain"><div className="eyebrow">THE ASSEMBLY, ONE VOICE AT A TIME</div><h2>Follow the exchange.</h2><p>Press Play to reveal each dialogue. Pause whenever you want to read more closely.</p></div>}
   {shown.map((turn,index)=>turn.speaker?<article ref={el=>{if(index===active)activeElement.current=el}} className={'debate-turn '+(index===active?'speaking-turn':'')} key={turn.id}><div className={'avatar '+turn.color}>{turn.initials}</div><div><div className="speaker"><strong>{turn.speaker}</strong><span>{index===active&&running?'Now reading · ':''}PDF page {page}</span></div>{readingBlocks(turn.text).map((p,i)=><p key={i}>{p}</p>)}</div></article>:<article ref={el=>{if(index===active)activeElement.current=el}} className={'prose narrated-paragraph '+(index===active?'speaking-turn':'')} key={turn.id}><p>{turn.text}</p></article>)}
  </div>
 </section>
}
