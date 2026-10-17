#!/usr/bin/env python3
"""Bounded OpenAI SSE serving benchmark. Does not modify/restart the server."""
import argparse,base64,concurrent.futures,fcntl,hashlib,json,math,os,re,statistics,threading,time,urllib.request
from pathlib import Path
BASE='http://127.0.0.1:8000';MODEL='vllmcritic';ROOT=Path('benchmark-output');SERVICE_READY=None;ROUTER_BASE=None
samples=[];stop_event=threading.Event();origin=time.monotonic()
def request(path,body=None,timeout=120,base=None):
 req=urllib.request.Request((base or BASE)+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','User-Agent':'reproducible-local-serving-benchmark/1.0'})
 return urllib.request.urlopen(req,timeout=timeout)
def json_request(path,body=None,**kw):
 with request(path,body,**kw) as r:return json.load(r)
def counters():
 with request('/metrics',timeout=5) as r:text=r.read().decode()
 result={}
 for line in text.splitlines():
  if line.startswith('#'):continue
  m=re.match(r'^(vllm:[a-zA-Z0-9_:]+)(?:\{.*\})?\s+([+\-\d.eE]+)$',line)
  if m and any(s in m[1] for s in ['num_requests_running','num_requests_waiting','prefix_cache','spec_decode','num_preemptions','time_to_first_token_seconds_sum','time_to_first_token_seconds_count']):result[m[1]]=result.get(m[1],0)+float(m[2])
 return result
def memory():
 d={k:int(v.split()[0])*1024 for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())}
 return {'available_bytes':d['MemAvailable'],'swap_free_bytes':d['SwapFree']}
def monitor():
 while not stop_event.is_set():
  try:
   s={'t':time.monotonic()-origin,**memory(),**counters()}
   try:s['router_active']=json_request('/internal/activity',base=ROUTER_BASE,timeout=3)['activeRequests'] if ROUTER_BASE else None
   except Exception:s['router_active']=None
   samples.append(s)
   with (ROOT/'telemetry.jsonl').open('a') as out:out.write(json.dumps(s)+'\n')
  except Exception as e:
   with (ROOT/'monitor-errors.log').open('a') as out:out.write(str(e)+'\n')
  stop_event.wait(.15)
def healthy():
 models=json_request('/v1/models',timeout=10);assert any(x['id']==MODEL and x['max_model_len']==200000 for x in models['data'])
 mem=memory();assert mem['available_bytes']>8*1024**3 and mem['swap_free_bytes']>4*1024**3
 return models
COUNT_SCHEMA=None
def token_count(messages):
 global COUNT_SCHEMA
 r=json_request('/tokenize',{'model':MODEL,'messages':messages,'chat_template_kwargs':{'enable_thinking':False}},timeout=20)
 n=r.get('count')
 if not isinstance(n,int):
  ids=r.get('tokens');assert isinstance(ids,list) and all(isinstance(i,int) for i in ids);n=len(ids)
 COUNT_SCHEMA=list(r);return n
def fixture(target,nonce):
 n=max(1,target-100)
 for _ in range(8):
  text=nonce+'\n'+(' alpha'*n)+'\nWrite at least 1500 words of continuous English prose about reliable software engineering. Do not summarize or end early.'
  msg=[{'role':'user','content':text}];count=token_count(msg)
  if count==target:return msg
  n+=target-count
  if n<0:raise ValueError('fixture budget too small')
 raise RuntimeError('exact tokenizer calibration did not converge')
def parse_sse(lines):
 content=[];reason=[];usage=None;finish=None;done=False;first=None;last=None;chunks=0
 for timestamp,raw in lines:
  if not raw.startswith('data:'):continue
  data=raw[5:].strip()
  if data=='[DONE]':done=True;break
  obj=json.loads(data)
  if obj.get('error'):raise RuntimeError(str(obj['error']))
  if obj.get('usage') is not None:usage=obj['usage']
  for choice in obj.get('choices',[]):
   delta=choice.get('delta',{});v=delta.get('content')
   if v:
    first=timestamp if first is None else first;last=timestamp;content.append(v);chunks+=1
   if delta.get('reasoning_content'):reason.append(delta['reasoning_content'])
   if choice.get('finish_reason') is not None:finish=choice['finish_reason']
 if not done or usage is None or finish is None:raise RuntimeError('incomplete SSE contract: DONE, usage or finish absent')
 return {'usage':usage,'finish_reason':finish,'first_visible_s':first,'last_visible_s':last,'visible_text':''.join(content),'reasoning_chars':sum(map(len,reason)),'visible_chunks':chunks,'done':done}
def run_one(name,messages,out_tokens,barrier=None):
 payload={'model':MODEL,'messages':messages,'temperature':0,'seed':42,'max_tokens':out_tokens,'ignore_eos':True,'chat_template_kwargs':{'enable_thinking':False},'stream':True,'stream_options':{'include_usage':True}}
 if barrier:barrier.wait(timeout=20)
 start=time.monotonic();before=counters();wire=[];rawlines=[]
 try:
  with request('/v1/chat/completions',payload,timeout=120) as response:
   for raw in response:
    line=raw.decode('utf8').strip();elapsed=time.monotonic()-start
    if line:wire.append((elapsed,line));rawlines.append(line)
  total=time.monotonic()-start;p=parse_sse(wire);after=counters();u=p['usage'];assert u['completion_tokens']==out_tokens and p['visible_text']
  reason_tokens=(u.get('completion_tokens_details') or {}).get('reasoning_tokens');cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens')
  p.update({'name':name,'start_s':start-origin,'end_s':time.monotonic()-origin,'elapsed_s':total,'output_budget':out_tokens,'input_tokens':u['prompt_tokens'],'output_tokens':u['completion_tokens'],'cached_tokens':cached,'reasoning_tokens':reason_tokens,'output_tps_end_to_end':u['completion_tokens']/total,'decode_tps_approx':(u['completion_tokens']-1)/(p['last_visible_s']-p['first_visible_s']) if p['visible_chunks']>1 else None,'prefill_tps_effective':u['prompt_tokens']/p['first_visible_s'] if p['first_visible_s'] else None,'counter_delta':{k:after[k]-before.get(k,after[k]) for k in after},'prompt_sha256':hashlib.sha256(json.dumps(messages).encode()).hexdigest(),'settings':{'temperature':0,'seed':42,'thinking':False,'ignore_eos':True},'status':'PASS'})
 except Exception as e:
  p={'name':name,'start_s':start-origin,'end_s':time.monotonic()-origin,'status':'ERROR','error':str(e)}
 finally:(ROOT/(name+'.sse')).write_text('\n'.join(rawlines))
 (ROOT/(name+'.json')).write_text(json.dumps(p,indent=2));print(json.dumps({k:v for k,v in p.items() if k in ['name','status','input_tokens','output_tokens','elapsed_s','first_visible_s','output_tps_end_to_end','decode_tps_approx','error']}),flush=True)
 return p
def functional():
 rows=[]
 cases=[('json',{'messages':[{'role':'user','content':'Return exactly a JSON object with status equal to ok and count equal to integer 3.'}],'response_format':{'type':'json_object'}},lambda r:json.loads(r['choices'][0]['message']['content'])=={'status':'ok','count':3}),('grounding',{'messages':[{'role':'user','content':'Source: Project Cedar uses code K-47. No launch date has been set. Return JSON with code and launch_date, null if unavailable. Use only this source.'}],'response_format':{'type':'json_object'}},lambda r:json.loads(r['choices'][0]['message']['content'])=={'code':'K-47','launch_date':None}),('tool',{'messages':[{'role':'user','content':'Use record_measurement exactly once with label sample and value 7. Do not answer in text.'}],'tools':[{'type':'function','function':{'name':'record_measurement','description':'Record a measurement','parameters':{'type':'object','properties':{'label':{'type':'string'},'value':{'type':'integer'}},'required':['label','value'],'additionalProperties':False}}}],'tool_choice':'auto'},lambda r:len(r['choices'][0]['message'].get('tool_calls',[]))==1 and r['choices'][0]['message']['tool_calls'][0]['function']['name']=='record_measurement' and json.loads(r['choices'][0]['message']['tool_calls'][0]['function']['arguments'])=={'label':'sample','value':7})]
 for name,extra,grade in cases:
  healthy();payload={'model':MODEL,'max_tokens':256,'temperature':0,'chat_template_kwargs':{'enable_thinking':False},**extra};r=json_request('/v1/chat/completions',payload,timeout=45);row={'name':name,'passed':False,'response':r};rows.append(row);(ROOT/'functional.json').write_text(json.dumps(rows,indent=2))
  try:row['passed']=bool(grade(r)) and r['choices'][0]['finish_reason']==('tool_calls' if name=='tool' else 'stop')
  except Exception as error:row['grader_error']=str(error)
  (ROOT/'functional.json').write_text(json.dumps(rows,indent=2));print('FUNCTIONAL',name,row['passed'],flush=True)
 return rows
def selftest():
 x=parse_sse([(0.1,'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}'),(.2,'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}'),(.3,'data: {"choices":[],"usage":{"completion_tokens":1,"prompt_tokens":2}}'),(.4,'data: [DONE]')]);assert x['first_visible_s']==.2 and x['usage']['completion_tokens']==1
 try:parse_sse([])
 except RuntimeError:pass
 else:raise AssertionError('truncated SSE accepted')
 print('CPU_SSE_CONTRACT_PASS')
def main():
 selftest();healthy();baseline=counters();unit_pid=SERVICE_READY.read_text() if SERVICE_READY and SERVICE_READY.exists() else None
 for _ in range(2):
  assert ROUTER_BASE is None or json_request('/internal/activity',base=ROUTER_BASE)['activeRequests']==0;time.sleep(.5)
 thread=threading.Thread(target=monitor,daemon=True);thread.start();results=[]
 try:
  f=functional()
  plans=[('pp512_tg128',512,128,1),('c1_1024',1024,256,1),('c1_8192',8192,256,1),('c2_8192',8192,256,2),('c4_8192',8192,256,4),('c1_32768',32768,128,1)]
  for group,prompt_size,budget,c in plans:
   healthy();messages=[fixture(prompt_size,f'Run-{time.time_ns()}-lane-{lane}') for lane in range(c)]
   repeats=3 if group=='c1_1024' else 1
   for rep in range(repeats):
    if rep:messages=[fixture(prompt_size,f'Run-{time.time_ns()}-lane-{lane}') for lane in range(c)]
    start=time.monotonic();barrier=threading.Barrier(c) if c>1 else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=c) as pool:
     cold=list(pool.map(lambda pair:run_one(f'{group}_r{rep}_cold_l{pair[0]}',pair[1],budget,barrier),enumerate(messages)))
    duration=time.monotonic()-start;selected=[s for s in samples if start-origin<=s['t']<=time.monotonic()-origin];resident=[s for s in selected if s.get('vllm:num_requests_running')==c and s.get('vllm:num_requests_waiting')==0];external=any((s.get('router_active') or 0)>0 for s in selected) if ROUTER_BASE else None
    wave={'group':group,'repeat':rep,'concurrency':c,'client_wall_s':duration,'aggregate_output_tps':sum(x.get('output_tokens',0) for x in cold)/duration,'resident_samples':len(resident),'residency_status':'PASS' if c==1 or len(resident)>=2 else 'INCONCLUSIVE','external_router_traffic':external,'requests':cold};results.append(wave);(ROOT/'waves.json').write_text(json.dumps(results,indent=2));assert all(x['status']=='PASS' for x in cold)
    if c==1 and prompt_size<=8192:
     warm=run_one(f'{group}_r{rep}_warm_l0',messages[0],budget);results.append({'group':group+'_warm','repeat':rep,'concurrency':1,'requests':[warm]});assert warm['status']=='PASS'
  after=counters();report={'schema':1,'benchmark':'bounded synthetic OpenAI serving benchmark','endpoint':'localhost physical backend','model':MODEL,'context_limit':200000,'configured_slots':4,'thinking':False,'functional':f,'waves':results,'metrics_delta':{k:after[k]-baseline.get(k,after[k]) for k in after},'min_mem_available_bytes':min(s['available_bytes'] for s in samples),'min_swap_free_bytes':min(s['swap_free_bytes'] for s in samples),'same_service_ready_record':(unit_pid==SERVICE_READY.read_text()) if SERVICE_READY and unit_pid else None,'limitations':['Not four full 200K windows','Not MMLU or model quality certification','Synthetic alpha-filler prompts; forced output length','Decode TPS approximate because SSE may coalesce speculative tokens','Cache-hit count unknown unless API/native counters provide evidence']};(ROOT/'report.json').write_text(json.dumps(report,indent=2));print('BENCHMARK_COMPLETE',flush=True)
 finally:stop_event.set();thread.join(timeout=7)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--selftest',action='store_true');parser.add_argument('--base-url',default=BASE);parser.add_argument('--model',default=MODEL);parser.add_argument('--output-dir',default='benchmark-output');parser.add_argument('--service-ready-file');parser.add_argument('--router-base-url');args=parser.parse_args()
 BASE=args.base_url.rstrip('/');MODEL=args.model;ROOT=Path(args.output_dir)
 if not args.selftest and ROOT.exists() and any(ROOT.iterdir()):parser.error('Use a new/empty output directory to preserve prior evidence')
 ROOT.mkdir(parents=True,exist_ok=True);SERVICE_READY=Path(args.service_ready_file) if args.service_ready_file else None;ROUTER_BASE=args.router_base_url.rstrip('/') if args.router_base_url else None
 selftest() if args.selftest else main()
