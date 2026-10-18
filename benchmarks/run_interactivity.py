#!/usr/bin/env python3
"""Event-driven mixed long-history fluency probe for an already-running vLLM.

It never changes server configuration.  Raw SSE is retained outside the portable
report; published evidence contains hashes, counts, timings, and metric samples.
"""
import argparse, concurrent.futures, hashlib, json, os, re, statistics, threading, time, urllib.error, urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:8000'
MODEL = 'vllmcritic'
LIMIT = 200000
FLOOR_MEM = 8 * 1024**3
FLOOR_SWAP = 4 * 1024**3


def percentile(values, p):
    if not values: return None
    values = sorted(values)
    return values[round((len(values) - 1) * p)]


def read_mem():
    d = {k: int(v.split()[0]) * 1024 for k, v in
         (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    return {'mem_available_bytes': d['MemAvailable'], 'swap_free_bytes': d['SwapFree']}


def json_http(base, path, body=None, timeout=90):
    req = urllib.request.Request(base + path,
        data=None if body is None else json.dumps(body, separators=(',', ':')).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'fp4-interactivity-e2e/1'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode()), response.status


def metrics(base):
    try:
        req = urllib.request.Request(base + '/metrics', headers={'User-Agent': 'fp4-interactivity-e2e/1'})
        with urllib.request.urlopen(req, timeout=8) as response: raw = response.read().decode()
    except Exception as exc:
        return {'metrics_error': repr(exc)}
    names = ('num_requests_running', 'num_requests_waiting', 'num_preemptions_total',
             'kv_cache_usage_perc', 'prefix_cache_hits_total', 'prefix_cache_queries_total',
             'spec_decode_num_draft_tokens_total', 'spec_decode_num_accepted_tokens_total')
    out = {}
    for line in raw.splitlines():
        m = re.match(r'^(vllm:[A-Za-z0-9_:]+)(?:\{[^}]*\})?\s+([+\-0-9.eE]+)$', line)
        if m and any(name in m.group(1) for name in names):
            out[m.group(1)] = out.get(m.group(1), 0.0) + float(m.group(2))
    return out


def counter_delta(before, after):
    return {k: after[k] - before[k] for k in after if isinstance(after[k], (int, float)) and isinstance(before.get(k), (int, float))}


def parse_sse(lines):
    content, events = [], []
    usage = finish = None
    done = False
    for stamp_ns, raw in lines:
        if not raw.startswith('data:'): continue
        data = raw[5:].strip()
        if data == '[DONE]': done = True; continue
        try: obj = json.loads(data)
        except json.JSONDecodeError: continue
        if obj.get('usage') is not None: usage = obj['usage']
        for choice in obj.get('choices', []):
            delta = choice.get('delta') or {}
            visible = delta.get('content')
            if visible:
                content.append(visible); events.append(stamp_ns)
            if choice.get('finish_reason') is not None: finish = choice['finish_reason']
    return {'visible_event_ns': events, 'visible_chars': sum(map(len, content)),
            'visible_sha256': hashlib.sha256(''.join(content).encode()).hexdigest(),
            'usage': usage, 'finish_reason': finish, 'done': done}


def gaps(events):
    return [(b - a) / 1e9 for a, b in zip(events, events[1:])]


def crossing_gap(events, begin_ns, end_ns):
    pairs = [(a, b) for a, b in zip(events, events[1:]) if a <= begin_ns and b >= end_ns]
    return max(((b - a) / 1e9 for a, b in pairs), default=None)


def tokenize(base, messages):
    value, status = json_http(base, '/tokenize', {'model': MODEL, 'messages': messages,
        'chat_template_kwargs': {'enable_thinking': False}}, timeout=300)
    if status != 200: raise RuntimeError('tokenize status %s' % status)
    if isinstance(value.get('count'), int): return value['count']
    if isinstance(value.get('tokens'), list) and all(isinstance(x, int) for x in value['tokens']): return len(value['tokens'])
    raise RuntimeError('unknown tokenizer schema')


def calibrated_user(base, target, lane, phase):
    nonce = 'interactivity-%s-lane-%s-%s' % (phase, lane, time.time_ns())
    fill = max(1, target - 120)
    for _ in range(12):
        # ` alpha` calibrates as a stable single-token filler on this tokenizer;
        # lane separation comes from the salted nonce rather than token shape.
        text = nonce + '\n' + (' alpha' * fill) + '\nRespond with a sustained stream of the word pulse until the output limit.'
        messages = [{'role': 'user', 'content': text}]
        got = tokenize(base, messages)
        if got == target: return messages, hashlib.sha256(text.encode()).hexdigest(), got
        fill += target - got
        if fill < 1: raise RuntimeError('fixture calibration underflow')
    raise RuntimeError('fixture calibration failed target=%d got=%d' % (target, got))


def request_stream(base, name, messages, budget, root, started=None, cancel_after_visible=False):
    payload = {'model': MODEL, 'messages': messages, 'temperature': 0, 'seed': 42,
        'max_tokens': budget, 'ignore_eos': True, 'stream': True,
        'stream_options': {'include_usage': True}, 'chat_template_kwargs': {'enable_thinking': False}}
    start_ns = started or time.monotonic_ns()
    before = metrics(base); lines = []; cancelled = False; error = None
    try:
        req = urllib.request.Request(base + '/v1/chat/completions', data=json.dumps(payload, separators=(',', ':')).encode(),
              headers={'Content-Type': 'application/json', 'User-Agent': 'fp4-interactivity-e2e/1'})
        with urllib.request.urlopen(req, timeout=2400) as response:
            for raw in response:
                now = time.monotonic_ns(); value = raw.decode('utf-8', errors='replace').strip()
                if value: lines.append((now, value))
                if cancel_after_visible and '"content"' in value:
                    parsed = parse_sse(lines)
                    if parsed['visible_event_ns']:
                        cancelled = True; break
    except Exception as exc: error = repr(exc)
    end_ns = time.monotonic_ns(); parsed = parse_sse(lines); usage = parsed['usage'] or {}
    raw = '\n'.join(value for _, value in lines)
    (root / 'raw-sse' / (name + '.sse')).write_text(raw)
    events = parsed['visible_event_ns']; all_gaps = gaps(events)
    result = {'name': name, 'start_monotonic_ns': start_ns, 'end_monotonic_ns': end_ns,
        'first_visible_monotonic_ns': events[0] if events else None,
        'last_visible_monotonic_ns': events[-1] if events else None,
        'visible_event_monotonic_ns': events, 'visible_gap_s': all_gaps,
        'visible_gap_p50_s': percentile(all_gaps, .5), 'visible_gap_p95_s': percentile(all_gaps, .95),
        'visible_gap_max_s': max(all_gaps, default=None), 'visible_chunks': len(events),
        'visible_chars': parsed['visible_chars'], 'visible_sha256': parsed['visible_sha256'],
        'done': parsed['done'], 'finish_reason': parsed['finish_reason'], 'cancelled_by_harness': cancelled,
        'http_error': error, 'input_tokens': usage.get('prompt_tokens'),
        'output_tokens': usage.get('completion_tokens'),
        'cached_tokens': (usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
        'metric_before': before, 'metric_after': metrics(base), 'raw_sse_sha256': hashlib.sha256(raw.encode()).hexdigest()}
    result['ttft_visible_s'] = ((result['first_visible_monotonic_ns'] - start_ns) / 1e9) if events else None
    result['elapsed_s'] = (end_ns - start_ns) / 1e9
    result['e2e_output_tps'] = usage.get('completion_tokens', 0) / result['elapsed_s'] if result['elapsed_s'] else None
    return result


def monitor(base, root, stop, samples):
    while not stop.is_set():
        row = {'monotonic_ns': time.monotonic_ns(), **read_mem(), 'metrics': metrics(base)}
        samples.append(row)
        with (root / 'telemetry.jsonl').open('a') as f: f.write(json.dumps(row, separators=(',', ':')) + '\n')
        stop.wait(.15)


def wait_visible(futures, timeout_s=1800):
    deadline = time.monotonic() + timeout_s
    # Futures write result only on completion; event watcher is supplied separately by request threads.
    while time.monotonic() < deadline:
        time.sleep(.05)
    raise RuntimeError('internal wait_visible misuse')


def prepare_history(base, lane, prompt_tokens, setup_output, root):
    seed, prompt_hash, count = calibrated_user(base, prompt_tokens, lane, 'setup')
    setup = request_stream(base, 'setup-%s' % lane, seed, setup_output, root)
    if not (setup['done'] and setup['input_tokens'] == count and setup['output_tokens'] and setup['visible_chars']):
        raise RuntimeError('history setup failed lane=%s' % lane)
    # Real assistant response becomes history, but stays private: recover it only from raw SSE.
    text = ''
    for line in (root / 'raw-sse' / ('setup-%s.sse' % lane)).read_text().splitlines():
        if line.startswith('data:'):
            try:
                obj = json.loads(line[5:].strip())
                for choice in obj.get('choices', []): text += (choice.get('delta') or {}).get('content') or ''
            except Exception: pass
    follow = seed + [{'role': 'assistant', 'content': text}, {'role': 'user', 'content': 'Continue the pulse stream until the output limit.'}]
    actual = tokenize(base, follow)
    return {'lane': lane, 'seed_prompt_sha256': prompt_hash, 'setup': setup, 'history_prompt_tokens': actual, 'messages': follow}


def run_event_wave(base, label, histories, cold_tokens, output_tokens, root, samples):
    # Calibration happens before peer decode begins.  The injection timestamp
    # therefore describes the real cold POST, not tokenizer preparation.
    cold_msg, cold_hash, cold_count = calibrated_user(base, cold_tokens, 'cold', label)
    starts, visible = {}, {}; lock = threading.Lock()
    def peer(lane, messages):
        # Inline variant exposes first visible instantly without waiting for completion.
        payload = {'model': MODEL, 'messages': messages, 'temperature': 0, 'seed': 42, 'max_tokens': output_tokens,
          'ignore_eos': True, 'stream': True, 'stream_options': {'include_usage': True}, 'chat_template_kwargs': {'enable_thinking': False}}
        start = time.monotonic_ns(); starts[lane] = start; before = metrics(base); lines=[]; error=None
        try:
            req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload,separators=(',',':')).encode(),headers={'Content-Type':'application/json','User-Agent':'fp4-interactivity-e2e/1'})
            with urllib.request.urlopen(req,timeout=2400) as response:
                for raw in response:
                    now=time.monotonic_ns(); value=raw.decode(errors='replace').strip()
                    if value: lines.append((now,value))
                    parsed=parse_sse(lines)
                    if parsed['visible_event_ns']:
                        with lock: visible.setdefault(lane, parsed['visible_event_ns'][0])
        except Exception as exc: error=repr(exc)
        end=time.monotonic_ns(); p=parse_sse(lines); raw='\n'.join(x for _,x in lines)
        (root/'raw-sse'/(label+'-peer-'+str(lane)+'.sse')).write_text(raw)
        ev=p['visible_event_ns']; gs=gaps(ev);u=p['usage'] or {}
        return {'name':label+'-peer-'+str(lane),'start_monotonic_ns':start,'end_monotonic_ns':end,'first_visible_monotonic_ns':ev[0] if ev else None,'last_visible_monotonic_ns':ev[-1] if ev else None,'visible_event_monotonic_ns':ev,'visible_gap_s':gs,'visible_gap_max_s':max(gs,default=None),'visible_gap_p50_s':percentile(gs,.5),'visible_gap_p95_s':percentile(gs,.95),'visible_chunks':len(ev),'visible_sha256':p['visible_sha256'],'done':p['done'],'finish_reason':p['finish_reason'],'http_error':error,'input_tokens':u.get('prompt_tokens'),'output_tokens':u.get('completion_tokens'),'cached_tokens':(u.get('prompt_tokens_details') or {}).get('cached_tokens'),'metric_before':before,'metric_after':metrics(base),'raw_sse_sha256':hashlib.sha256(raw.encode()).hexdigest(),'ttft_visible_s':(ev[0]-start)/1e9 if ev else None,'elapsed_s':(end-start)/1e9}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(peer, h['lane'], h['messages']) for h in histories]
        deadline=time.monotonic()+1800
        while len(visible)<3 and time.monotonic()<deadline: time.sleep(.02)
        if len(visible)<3: raise RuntimeError('three peers did not produce visible content')
        injection_start=time.monotonic_ns()
        cold=request_stream(base,label+'-cold',cold_msg,output_tokens,root,started=injection_start)
        injection_end=cold['first_visible_monotonic_ns'] or cold['end_monotonic_ns']
        peers=[f.result() for f in fs]
    conditions={'first_visible_all_three':len(visible)==3,
      'injection_after_first_visible':all(v < injection_start for v in visible.values()),
      'injection_before_finish_all_three':all(injection_start < p['end_monotonic_ns'] for p in peers)}
    for p in peers:
        p['gap_crossing_cold_prefill_s']=crossing_gap(p['visible_event_monotonic_ns'], injection_start, injection_end)
        p['wall_until_next_content_after_injection_s']=next(((e-injection_start)/1e9 for e in p['visible_event_monotonic_ns'] if e>injection_start),None)
    interval_samples=[s for s in samples if injection_start<=s['monotonic_ns']<=injection_end]
    running3_wait0=sum(1 for s in interval_samples if s['metrics'].get('vllm:num_requests_running')==3 and s['metrics'].get('vllm:num_requests_waiting')==0)
    return {'label':label,'injection_start_monotonic_ns':injection_start,'injection_first_visible_monotonic_ns':cold['first_visible_monotonic_ns'],'injection_end_monotonic_ns':injection_end,'conditions':conditions,'cold_prompt_sha256':cold_hash,'cold_prompt_tokens':cold_count,'peers':peers,'cold':cold,'interval_native_samples':interval_samples,'running3_wait0_samples_during_cold_prefill':running3_wait0}


def sanitize(obj):
    # Keep timing/metrics but never publish response text or filesystem/network identity.
    if isinstance(obj, dict): return {k: sanitize(v) for k,v in obj.items() if k not in ('messages','raw_sse','error_body','base_url','output_dir')}
    if isinstance(obj, list): return [sanitize(v) for v in obj]
    return obj


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base-url',default=BASE); ap.add_argument('--output-dir',required=True)
    ap.add_argument('--medium-tokens',type=int,default=128000); ap.add_argument('--near-limit-tokens',type=int,default=197800)
    ap.add_argument('--output-tokens',type=int,default=1024); ap.add_argument('--skip-near-limit',action='store_true')
    args=ap.parse_args(); base=args.base_url.rstrip('/'); root=Path(args.output_dir); root.mkdir(parents=True,exist_ok=False); (root/'raw-sse').mkdir()
    model,_=json_http(base,'/v1/models'); assert any(x.get('id')==MODEL and x.get('max_model_len')==LIMIT for x in model['data'])
    assert read_mem()['mem_available_bytes']>=FLOOR_MEM and read_mem()['swap_free_bytes']>=FLOOR_SWAP
    for size in (args.medium_tokens,args.near_limit_tokens):
        if size+args.output_tokens>=LIMIT: raise ValueError('prompt + output must fit total context')
    initial={'monotonic_ns':time.monotonic_ns(),'memory':read_mem(),'metrics':metrics(base),'model_limit':LIMIT,'settings':vars(args)}
    stop=threading.Event(); samples=[]; thread=threading.Thread(target=monitor,args=(base,root,stop,samples),daemon=True);thread.start()
    report={'schema':1,'benchmark':'event-driven long-history mixed-load fluency','clock':'all *_monotonic_ns fields share time.monotonic_ns clock','thresholds':{'warm_ttft_visible_s_max':2.0,'visible_pause_max_s':2.0},'initial':initial,'waves':[],'cancellation':None}
    try:
        for name,size in [('medium128k',args.medium_tokens),('near198k',args.near_limit_tokens)]:
            if name=='near198k' and args.skip_near_limit: continue
            histories=[prepare_history(base,lane,size,args.output_tokens,root) for lane in range(3)]
            if any(h['history_prompt_tokens']+args.output_tokens>LIMIT for h in histories): raise RuntimeError('history continuation exceeds context')
            wave=run_event_wave(base,name,histories,32000,args.output_tokens,root,samples)
            report['waves'].append(wave); (root/'progress.json').write_text(json.dumps(sanitize(report),indent=2))
            if not all(wave['conditions'].values()): break
        # Bounded cancellation of a harness-owned request after visible output, then wait for idle.
        msg,_,_=calibrated_user(base,32000,'cancel','cancel')
        before=metrics(base); cancelled=request_stream(base,'owned-cancel',msg,1024,root,cancel_after_visible=True)
        deadline=time.monotonic()+90; idle=False
        while time.monotonic()<deadline:
            m=metrics(base)
            if m.get('vllm:num_requests_running')==0 and m.get('vllm:num_requests_waiting')==0: idle=True; break
            time.sleep(.2)
        probe=request_stream(base,'recovery-probe',[{'role':'user','content':'Reply exactly RECOVERED.'}],32,root)
        report['cancellation']={'before_metrics':before,'cancelled_request':cancelled,'capacity_idle_after_cancel':idle,'recovery_probe':probe,'after_metrics':metrics(base)}
    finally:
        stop.set();thread.join(5)
        report['final']={'monotonic_ns':time.monotonic_ns(),'memory':read_mem(),'metrics':metrics(base),'telemetry_samples':len(samples)}
        report['safety']={'mem_floor_pass':min((x['mem_available_bytes'] for x in samples),default=0)>=FLOOR_MEM,'swap_floor_pass':min((x['swap_free_bytes'] for x in samples),default=0)>=FLOOR_SWAP}
        (root/'report-private.json').write_text(json.dumps(report,indent=2))
        (root/'report-sanitized.json').write_text(json.dumps(sanitize(report),indent=2))

if __name__=='__main__': main()
