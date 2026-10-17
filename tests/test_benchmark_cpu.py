"""CPU-only protocol test. Fake SSE exercises the runner, never produces published benchmarks."""
import contextlib,importlib.util,io,json,tempfile,unittest
from pathlib import Path
class Response:
 def __init__(self,data):self.data=data
 def __enter__(self):return self
 def __exit__(self,*a):return False
 def read(self):return self.data
 def __iter__(self):return iter(self.data.splitlines(keepends=True))
class BenchmarkContract(unittest.TestCase):
 def test_full_producer_uses_usage_done_and_keeps_unknown_evidence_unknown(self):
  path=Path(__file__).resolve().parents[1]/'benchmarks/run_benchmark.py';spec=importlib.util.spec_from_file_location('bench_fixture',path);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  def response(path,body=None,**kw):
   if path=='/metrics':return Response(b'vllm:num_requests_running 0\nvllm:num_requests_waiting 0\n')
   if path=='/v1/models':return Response(json.dumps({'data':[{'id':m.MODEL,'max_model_len':200000}]}).encode())
   if path=='/tokenize':return Response(json.dumps({'count':body['messages'][0]['content'].count(' alpha')+20}).encode())
   if body.get('stream'):
    data=[{'choices':[{'delta':{'content':'fixture '},'finish_reason':None}]},{'choices':[{'delta':{'content':'answer'},'finish_reason':'length'}]},{'choices':[],'usage':{'prompt_tokens':body['messages'][0]['content'].count(' alpha')+20,'completion_tokens':body['max_tokens']}}]
    return Response(('\n'.join('data: '+json.dumps(x)+'\n' for x in data)+'\ndata: [DONE]\n').encode())
   text=body['messages'][0]['content']
   if body.get('tools'):message={'tool_calls':[{'function':{'name':'record_measurement','arguments':'{"label":"sample","value":7}'}}]};finish='tool_calls'
   else:message={'content':json.dumps({'code':'K-47','launch_date':None} if 'Source:' in text else {'status':'ok','count':3})};finish='stop'
   return Response(json.dumps({'choices':[{'message':message,'finish_reason':finish}]}).encode())
  m.request=response;m.memory=lambda:{'available_bytes':16*1024**3,'swap_free_bytes':8*1024**3}
  with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
   m.ROOT=Path(folder);m.main();r=json.loads((m.ROOT/'report.json').read_text());self.assertEqual(sum(len(w['requests']) for w in r['waves']),17);self.assertIsNone(r['same_service_ready_record']);self.assertTrue(all(x['passed'] for x in r['functional']));self.assertTrue(all(w.get('external_router_traffic') is None for w in r['waves']))
if __name__=='__main__':unittest.main()
