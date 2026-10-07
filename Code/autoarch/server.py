"""Loopback-only application server; same engine as evaluation."""
import argparse,json,mimetypes,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from .engine import Engine

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,engine):
        super().__init__(address,Handler);self.engine=engine;self.lock=threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,data,kind='application/json'):
        raw=json.dumps(data).encode() if kind=='application/json' else data
        self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");self.end_headers();self.wfile.write(raw)
    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.valid_host():return self.send(403,{'error':'Invalid Host'})
        p=urlparse(self.path);q=parse_qs(p.query);v=q.get('version',['v2'])[0];e=self.server.engine
        try:
            if p.path=='/api/status':return self.send(200,{'app':'AutoArch AI','backend':e.cfg['backend'],'documents':e.documents,'chunks':len(e.chunks),'index_sha256':e.index_digest,'config':e.cfg})
            if p.path=='/api/entities':return self.send(200,e.entities(v))
            if p.path=='/api/graph':return self.send(200,e.graph(v))
            if p.path=='/api/consistency':return self.send(200,e.consistency(v))
            if p.path=='/api/compare':return self.send(200,e.compare())
            if p.path=='/api/impact':return self.send(200,e.impact(q.get('component',[''])[0],v))
            if p.path=='/api/source':
                cid=q.get('id',[''])[0];c=next((c for c in e.chunks if c['id']==cid),None)
                return self.send(200,c) if c else self.send(404,{'error':'Unknown citation'})
            if p.path=='/api/evaluation':
                f=e.root/'Evaluation_Results/metrics.json';return self.send(200,json.loads(f.read_text()) if f.exists() else {'status':'Not yet evaluated'})
            if p.path=='/api/data':return self.send(200,{'documents':e.documents,'chunks':e.chunks})
            if p.path=='/api/export':return self.send(200,{'entities':e.entities(v),'graph':e.graph(v),'consistency':e.consistency(v),'comparison':e.compare()})
            if p.path=='/api/architecture':return self.send(200,{'steps':['Manifest and approved or synthetic inputs','Page and section aware ingestion','TF-IDF sparse vectors or local pretrained embeddings','Exact cosine top-k retrieval within one version','Extracted source lines or local model response','Citation validation and human review'],'backend':e.cfg['backend']})
            allowed={'/':'index.html','/style.css':'style.css','/app.js':'app.js'}
            if p.path in allowed:
                f=Path(__file__).parent/'web'/allowed[p.path];return self.send(200,f.read_bytes(),mimetypes.guess_type(f.name)[0])
            return self.send(404,{'error':'Not found'})
        except (ValueError,KeyError) as exc:self.send(400,{'error':str(exc)})
    def do_POST(self):
        if not self.valid_host():return self.send(403,{'error':'Invalid Host'})
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):return self.send(403,{'error':'Cross-origin request refused'})
        if urlparse(self.path).path!='/api/ask':return self.send(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>8192:return self.send(413,{'error':'Request size must be 1–8192 bytes'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'JSON required'})
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise ValueError('Request must be a JSON object')
            result=self.server.engine.ask(body.get('question'),body.get('version','v2'))
            # Logs are local and exclude secrets; safe on simultaneous writes.
            with self.server.lock:
                with (self.server.engine.root/'Evaluation_Results/interaction_log.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
            self.send(200,result)
        except (ValueError,TypeError,json.JSONDecodeError) as exc:self.send(400,{'error':str(exc)})
        except RuntimeError as exc:self.send(503,{'error':str(exc)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);args=p.parse_args()
    e=Engine(args.root);e.export_index();server=Server(('127.0.0.1',args.port),e)
    print(f'AutoArch AI [{e.cfg["backend"]}] at http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
if __name__=='__main__':main()
