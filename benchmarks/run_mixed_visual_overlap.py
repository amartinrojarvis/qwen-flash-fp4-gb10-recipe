#!/usr/bin/env python3
"""Real 3-stream + fourth visual injection; no server mutation."""
import argparse,base64,json,queue,threading,time,urllib.request
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://localhost:8000');p.add_argument('--output-dir',required=True);p.add_argument('--tokens',type=int,default=32000);a=p.parse_args(); out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=False)
fixture=Path(__file__).with_name('fixtures')/'ocr.png'; im=Image.open(fixture); b=fixture.read_bytes(); url='data:image/png;base64,'+base64.b64encode(b).decode()
startgate=threading.Event(); first=[threading.Event() for _ in range(3)]; rec=[{'name':f'peer{i}','events_ns':[],'error':None} for i in range(3)]; fourth={'name':'visual4','events_ns':[],'error':None}; q=queue.Queue()
def payload(i,visual=False):
 filler=' '.join(['historia']*(a.tokens-300)); content=[{'type':'text','text':f'Contexto largo independiente lane={i} {filler}\nEscribe una explicación extensa de ingeniería de software sin terminar pronto.'}]
 if visual: content.extend([{'type':'text','text':' Además lee el código de la imagen y menciónalo.'},{'type':'image_url','image_url':{'url':url}}])
 return {'model':'vllmcritic','messages':[{'role':'user','content':content}],'temperature':0,'seed':100+i,'max_tokens':512,'ignore_eos':True,'chat_template_kwargs':{'enable_thinking':False},'stream':True,'stream_options':{'include_usage':True}}
def run(i,target):
 try:
  startgate.wait(); target['start_ns']=time.monotonic_ns(); req=urllib.request.Request(a.base_url.rstrip('/')+'/v1/chat/completions',data=json.dumps(payload(i,target['name']=='visual4')).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=300) as r:
   for line in r:
    line=line.decode().strip()
    if not line.startswith('data: ') or line=='data: [DONE]':continue
    x=json.loads(line[6:]); target['usage']=x.get('usage') or target.get('usage')
    for c in x.get('choices',[]):
     if c.get('delta',{}).get('content'):
      t=time.monotonic_ns();target['events_ns'].append(t)
      if i<3:first[i].set()
     target['finish_reason']=c.get('finish_reason') or target.get('finish_reason')
  target['end_ns']=time.monotonic_ns()
 except Exception as e: target['error']=str(e);target['end_ns']=time.monotonic_ns()
ths=[threading.Thread(target=run,args=(i,rec[i])) for i in range(3)]
for t in ths:t.start()
startgate.set()
if not all(x.wait(180) for x in first): raise SystemExit('peer first-visible timeout')
inject=time.monotonic_ns(); t4=threading.Thread(target=run,args=(3,fourth));t4.start();t4.join();[t.join() for t in ths]
for r in rec:
 ev=r['events_ns']; r['max_gap_ms']=max([(ev[i]-ev[i-1])/1e6 for i in range(1,len(ev))],default=None);r['first_ns']=ev[0] if ev else None;r['last_ns']=ev[-1] if ev else None
summary={'schema':1,'fixture':'three real 32K streaming text histories; fourth visual request injected after first visible from all peers','tokens_requested':a.tokens,'injection_mono_ns':inject,'peers':rec,'visual':fourth,'overlap_assertion':all(r.get('first_ns') and r['first_ns']<inject<r.get('end_ns',0) for r in rec),'encoder_preprocess':'UNAVAILABLE: pinned API did not expose image-encoder timing','native_running_waiting':'UNAVAILABLE: no pinned metrics observation implemented in this bounded probe'}
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'out':str(out),'overlap':summary['overlap_assertion'],'peer_gaps':[x['max_gap_ms'] for x in rec]}))
