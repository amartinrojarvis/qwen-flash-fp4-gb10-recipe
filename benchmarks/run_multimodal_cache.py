#!/usr/bin/env python3
"""Live, bounded multimodal-cache probe. It never changes the server."""
import argparse, base64, hashlib, json, os, re, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

P=argparse.ArgumentParser(); P.add_argument('--base-url',default='http://localhost:8000'); P.add_argument('--model',default='vllmcritic'); P.add_argument('--output-dir',required=True); P.add_argument('--long-tokens',type=int,default=32000); A=P.parse_args()
OUT=Path(A.output_dir); OUT.mkdir(parents=True,exist_ok=False); AS=OUT/'assets'; AS.mkdir()

def png(name,color,code):
 im=Image.new('RGB',(900,540),color); d=ImageDraw.Draw(im); f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',96)
 d.rectangle((35,35,865,505),outline='white',width=10); d.text((90,200),code,font=f,fill='white',stroke_width=2,stroke_fill='black'); im.save(AS/name)
 return (AS/name).read_bytes()
red=png('red.png',(190,25,30),'RIVERA 73'); blue=png('blue.png',(20,65,190),'AZUL 41'); green=png('green.png',(20,150,80),'VERDE 92')
# Existing legal asset is deliberately recorded as photographic coverage only if it is usable.
photo=Path(__file__).with_name('fixtures')/'coco_cats_couch.jpg'

def data(b): return 'data:image/png;base64,'+base64.b64encode(b).decode()
def ih(b): return {'type':'image_url','image_url':{'url':data(b)}}
def tx(s): return {'type':'text','text':s}
def call(case,msgs,max_tokens=128,stream=False):
 body={'model':A.model,'messages':msgs,'temperature':0,'seed':17,'max_tokens':max_tokens,'chat_template_kwargs':{'enable_thinking':False}}
 started=time.monotonic_ns(); raw=[]; first=None; usage=None; finish=None; text=[]
 if stream:
  body.update(stream=True,stream_options={'include_usage':True})
  req=urllib.request.Request(A.base_url+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=180) as r:
   for line in r:
    line=line.decode().strip(); raw.append(line)
    if not line.startswith('data: '):continue
    x=line[6:]
    if x=='[DONE]':continue
    x=json.loads(x); usage=x.get('usage') or usage
    for c in x.get('choices',[]):
     v=c.get('delta',{}).get('content')
     if v:
      first=first or time.monotonic_ns(); text.append(v)
     finish=c.get('finish_reason') or finish
 else:
  req=urllib.request.Request(A.base_url+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=180) as r:
   x=json.load(r); usage=x.get('usage'); finish=x['choices'][0]['finish_reason']; text=[x['choices'][0]['message'].get('content','')]
 end=time.monotonic_ns(); answer=''.join(text).strip()
 rec={'case':case,'request_sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),'ordered_media_sha256':[hashlib.sha256(base64.b64decode(p['image_url']['url'].split(',',1)[1])).hexdigest() for m in msgs for p in (m.get('content') if isinstance(m.get('content'),list) else []) if p.get('type')=='image_url'],'answer':answer,'finish_reason':finish,'usage':usage,'start_mono_ns':started,'first_visible_mono_ns':first,'end_mono_ns':end,'ttft_ms':None if first is None else (first-started)/1e6,'e2e_ms':(end-started)/1e6,'raw_sse':raw if stream else None}
 (OUT/(case+'.json')).write_text(json.dumps(rec,indent=2)); return rec

def judge(r,need):
 ans=r['answer'].lower(); return {'finish_ok':r['finish_reason']=='stop','contains':{n:n.lower() in ans for n in need},'answer_sha256':hashlib.sha256(r['answer'].encode()).hexdigest()}

results=[]
def one(name,msgs,need,max_tokens=128,stream=False):
 r=call(name,msgs,max_tokens,stream); r['grade']=judge(r,need); results.append(r); return r
question='Indica exactamente el color y el código visibles, sin inventar datos.'
r1=one('01_exact_first',[{'role':'user','content':[tx(question),ih(red)]}],['rojo','73'])
r2=one('01_exact_repeat',[{'role':'user','content':[tx(question),ih(red)]}],['rojo','73'])
# Actual assistant reply is retained on the wire; final user turn does not resend the image.
h=[{'role':'user','content':[tx(question),ih(red)]},{'role':'assistant','content':r1['answer']},{'role':'user','content':'Ahora responde solamente el código de la misma foto.'}]
r3=one('02_followup_history',h,['73'])
r4=one('03_text_history_control',[{'role':'user','content':'Historia: el cartel anterior fue descrito como '+r1['answer']},{'role':'assistant','content':r1['answer']},{'role':'user','content':'Ahora responde solamente el código citado en la historia.'}],['73'])
r5=one('04_replace_same_text',[{'role':'user','content':[tx(question),ih(blue)]}],['azul','41'])
r6=one('06_order_red_blue',[{'role':'user','content':[tx('Da una lista en orden, una entrada por foto, con color y código.'),ih(red),ih(blue)]}],['rojo','73','azul','41'])
r7=one('06_order_blue_red',[{'role':'user','content':[tx('Da una lista en orden, una entrada por foto, con color y código.'),ih(blue),ih(red)]}],['azul','41','rojo','73'])
r8=one('06_replace_position',[{'role':'user','content':[tx('Da una lista en orden, una entrada por foto, con color y código.'),ih(red),ih(green)]}],['rojo','73','verde','92'])
# Same URL, changed served bytes: valid only if the engine reaches the local host server.
class H(BaseHTTPRequestHandler):
 blob=red
 def do_GET(self): self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Length',str(len(self.blob))); self.end_headers(); self.wfile.write(self.blob)
 def log_message(self,*x): pass
srv=ThreadingHTTPServer(('localhost',18081),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
def urlmsg(): return [{'role':'user','content':[tx(question),{'type':'image_url','image_url':{'url':'http://localhost:18081/same.png'}}]}]
try:
 u1=one('05_same_url_red',urlmsg(),['rojo','73']); H.blob=blue; u2=one('05_same_url_blue',urlmsg(),['azul','41'])
except Exception as e: results.append({'case':'05_same_url_changed_bytes','status':'INCONCLUSIVE_BACKEND_CANNOT_REACH_HOST_LOCAL_URL','error':str(e)})
finally: srv.shutdown()
# Representative text+image history. Exact 32K is calibrated through the live endpoint only when supported.
try:
 filler=' '.join(['contexto']*(A.long_tokens-300)); long=[{'role':'user','content':f'Sesión extensa {filler}'},{'role':'assistant','content':'Recibido.'},{'role':'user','content':[tx('Conserva el contexto y lee la foto: responde color y código.'),ih(green)]}]
 rlong=one('07_long_history_visual',long,['verde','92'],256,True); rlong['long_requested_tokens']=A.long_tokens
except Exception as e: results.append({'case':'07_long_history_visual','status':'NOT_EVALUATED','error':str(e)})
summary={'schema':1,'scope':'direct backend multimodal cache/integrity probe; synthetic deterministic OCR/color assets; no broad natural-scene quality claim','identity':{'model':A.model,'base_url':A.base_url},'asset_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in AS.iterdir()},'photo_asset_present':photo.exists(),'results':results,'assertions':{'exact_reply_equal':r1['answer']==r2['answer'],'replacement_changed_answer':r1['answer']!=r5['answer'],'media_cache_proven':False,'reason':'API cached_tokens/native media/encoder counters are recorded per response when exposed; a text-prefix cache hit alone is not media-cache proof'}}
for r in results:
 u=r.get('usage') or {}; summary.setdefault('usage_observations',[]).append({'case':r.get('case'),'cached_tokens':(u.get('prompt_tokens_details') or {}).get('cached_tokens'),'prompt_tokens':u.get('prompt_tokens'),'completion_tokens':u.get('completion_tokens')})
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps({'output':str(OUT),'cases':len(results),'assertions':summary['assertions']}))
