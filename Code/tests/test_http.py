import json,threading,unittest,urllib.request,urllib.error,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoarch.engine import Engine
from autoarch.server import Server
class HTTPTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=Server(('127.0.0.1',0),Engine(Path(__file__).resolve().parents[2]));cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def test_live_question_cites_current_version(self):
  req=urllib.request.Request(self.url+'/api/ask',data=json.dumps({'question':'What is the period of VehicleSpeed?','version':'v1'}).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req) as res:d=json.load(res);self.assertEqual(res.status,200)
  self.assertTrue(all(':v1:' in c['citation'] for c in d['claims']))
 def test_cross_origin_post_rejected(self):
  req=urllib.request.Request(self.url+'/api/ask',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://untrusted.example'})
  with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
  self.assertEqual(caught.exception.code,403)
 def test_host_validation(self):
  req=urllib.request.Request(self.url+'/api/status',headers={'Host':'untrusted.example'})
  with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
  self.assertEqual(caught.exception.code,403)
 def test_json_export(self):
  with urllib.request.urlopen(self.url+'/api/export?version=v2') as res:d=json.load(res)
  self.assertEqual(len(d['entities']),16);self.assertEqual(len(d['consistency']['findings']),1)
 def test_unknown_citation_not_found(self):
  with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(self.url+'/api/source?id=invented')
  self.assertEqual(caught.exception.code,404)
 def test_bad_payload_is_client_error(self):
  req=urllib.request.Request(self.url+'/api/ask',data=b'{"question":null}',headers={'Content-Type':'application/json'})
  with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
  self.assertEqual(caught.exception.code,400)
if __name__=='__main__':unittest.main(verbosity=2)
