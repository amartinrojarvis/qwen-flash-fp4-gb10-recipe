"""CPU checks of actual producer helpers; no CLI, HTTP or GPU is executed."""
import ast,base64,hashlib,json,re,unittest
from pathlib import Path
PATH=Path(__file__).resolve().parents[1]/'benchmarks/run_multimodal_cache.py'
def helpers():
 names={'media_bytes','ordered_media_hashes','canonical_color','judge_order','judge'}
 tree=ast.parse(PATH.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert {n.name for n in nodes}==names
 ns={'base64':base64,'hashlib':hashlib,'json':json,'re':re}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(PATH),'exec'),ns);return ns
class MultimodalContract(unittest.TestCase):
 def setUp(self):self.h=helpers()
 def test_real_hash_helpers_accept_data_and_captured_url(self):
  a,b=b'original image fixture',b'replacement image fixture';url='http://fixture.invalid/same.png';data='data:image/png;base64,'+base64.b64encode(a).decode()
  msgs=[{'role':'user','content':[{'type':'image_url','image_url':{'url':data}},{'type':'image_url','image_url':{'url':url}}]}]
  self.assertEqual(self.h['ordered_media_hashes'](msgs,{url:b}),[hashlib.sha256(a).hexdigest(),hashlib.sha256(b).hexdigest()])
  with self.assertRaises(ValueError):self.h['media_bytes'](url)
 def test_real_order_grader_positive_and_poison(self):
  expected=[('red','RIVERA73'),('blue','AZUL41')];good=[{'color':'#b31b1b','text':'RIVERA 73'},{'color':'azul','text':'AZUL 41'}]
  def grade(x,finish='stop'):return self.h['judge_order']({'answer':json.dumps(x),'finish_reason':finish},expected)
  self.assertTrue(grade(good)['exact_positions']);self.assertFalse(grade(good[::-1])['exact_positions'])
  self.assertFalse(grade([{'color':'blue','text':'RIVERA 73'},good[1]])['exact_positions'])
  self.assertFalse(grade([good[0],{'color':'blue','text':'OTHER 99'}])['exact_positions']);self.assertFalse(grade(good,'length')['finish_ok'])
 def test_real_ocr_grader_rejects_color_only_answer(self):
  a=self.h['judge']({'answer':'RIVERA 73','finish_reason':'stop'},['rivera','73']);b=self.h['judge']({'answer':'#B31217','finish_reason':'stop'},['rivera','73'])
  self.assertTrue(a['finish_ok'] and all(a['contains'].values()));self.assertFalse(all(b['contains'].values()))
if __name__=='__main__':unittest.main()
