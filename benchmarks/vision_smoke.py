#!/usr/bin/env python3
"""One objective OCR smoke; no claim of broad vision quality."""
import argparse,base64,hashlib,json,re,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8000');p.add_argument('--model',default='vllmcritic');a=p.parse_args()
image=Path(__file__).parent/'fixtures/ocr.png'
body={'model':a.model,'messages':[{'role':'user','content':[{'type':'text','text':'Read the code in this image. Reply only the code.'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode()}}]}],'temperature':0,'max_tokens':48,'chat_template_kwargs':{'enable_thinking':False}}
with urllib.request.urlopen(urllib.request.Request(a.base_url.rstrip('/')+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=45) as response:r=json.load(response)
c=r['choices'][0];text=c['message'].get('content','').strip();answer=re.sub(r'^```(?:text)?\s*|\s*```$','',text).strip();passed=answer=='K7M4' and c['finish_reason']=='stop';print(json.dumps({'passed':passed,'answer':answer,'finish_reason':c['finish_reason'],'fixture_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'scope':'single OCR fixture, not a general vision benchmark'}));raise SystemExit(0 if passed else 1)
