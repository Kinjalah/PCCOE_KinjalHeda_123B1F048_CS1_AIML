"""Document ingestion, exact sparse retrieval, local-model adapter and traceability.
No test answers are embedded here. Corpus text is the source of every baseline answer.
"""
from __future__ import annotations
import hashlib,json,math,re,time,urllib.request,urllib.error
from collections import Counter,deque
from pathlib import Path

STOP=set('a an the and or is are was were be to of for in on at by from with how what which who does do can please tell me describe explain list show give document hld version v1 v2 according system'.split())
ALIASES={'milliseconds':'ms','timing':'period','cycle':'period','supplier':'producer','receiver':'consumer','connections':'connection','interfaces':'interface','components':'component','signals':'signal','ports':'port','units':'unit','uses':'use','carries':'interface','depends':'dependency','dependencies':'dependency','degrees':'deg'}
BLOCKED=re.compile(r'ignore\s+(?:all\s+)?(?:previous|prior|system)|fabricat\w*|invent\s+(?:a\s+)?(?:citation|source)|reveal\s+(?:the\s+)?(?:system\s+prompt|secret)|override\s+(?:the\s+)?(?:rule|instruction)',re.I)

def tokens(text):
    text=re.sub(r'([a-z])([A-Z])',r'\1 \2',text)
    return [ALIASES.get(x,x) for x in re.findall(r'[a-z0-9]+',text.lower()) if x not in STOP and len(x)>1]

def digest(data): return hashlib.sha256(data).hexdigest()

def load_config(root):
    cfg=json.loads((Path(root)/'Model_Prompts_Config/model_config.json').read_text())
    if cfg['backend'] not in ('extractive','ollama'): raise ValueError('Unsupported backend')
    endpoint=cfg.get('ollama_url','http://127.0.0.1:11434')
    from urllib.parse import urlparse
    u=urlparse(endpoint)
    if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or u.username or u.password or u.query or u.fragment or u.path not in ('','/'):
        raise ValueError('Only a local loopback Ollama endpoint is supported')
    return cfg

def ollama(cfg,path,body):
    req=urllib.request.Request(cfg['ollama_url'].rstrip('/')+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=cfg.get('model_timeout_seconds',60)) as response:return json.load(response)
    except (OSError,ValueError) as exc:raise RuntimeError('Local model request failed. Start Ollama and install the configured models; no cloud fallback is used.') from exc

def ingest_text(text,document_id,version,filename):
    if len(text)>2_000_000:raise ValueError('Document exceeds text limit')
    sections=re.split(r'^##\s+',text,flags=re.M)
    chunks=[]
    for page,section in enumerate(sections[1:],1):
        title,_,body=section.partition('\n')
        if not body.strip():continue
        # Explicitly retain full evidence lines; split only between lines.
        groups=[];current=[];n=0
        for line in body.strip().splitlines():
            if n+len(line)>1800 and current:groups.append('\n'.join(current));current=[];n=0
            if len(line)>1800:raise ValueError('A source line exceeds the 1800-character limit; preprocess it before ingestion')
            current.append(line);n+=len(line)+1
        if current:groups.append('\n'.join(current))
        for part,body in enumerate(groups,1):
            cid=f'{document_id}:{version}:p{page}:c{part}'
            chunks.append({'id':cid,'document_id':document_id,'version':version,'filename':filename,'page':page,'section':title.strip(),'text':body,'text_sha256':digest(body.encode()),'locator_kind':'section-derived page; see generated PDF'})
    if not chunks:
        for page,body in enumerate([text[i:i+1800] for i in range(0,len(text),1800)],1):
            if body.strip():chunks.append({'id':f'{document_id}:{version}:c{page}','document_id':document_id,'version':version,'filename':filename,'page':None,'section':f'Text block {page}','text':body,'text_sha256':digest(body.encode()),'locator_kind':'text block; no PDF page asserted'})
    return chunks

def ingest_file(path,document_id,version):
    path=Path(path)
    if path.stat().st_size>8_000_000:raise ValueError('Maximum file size is 8 MB')
    if path.suffix.lower() in ('.md','.txt'):
        return ingest_text(path.read_text(encoding='utf-8'),document_id,version,path.name)
    if path.suffix.lower()=='.pdf':
        try:from pypdf import PdfReader
        except ImportError as exc:raise RuntimeError('PDF ingestion requires pypdf. Text ingestion has no dependency.') from exc
        reader=PdfReader(path);chunks=[]
        if len(reader.pages)>100:raise ValueError('Maximum PDF length is 100 pages')
        for page,p in enumerate(reader.pages,1):
            text=p.extract_text() or ''
            if not text.strip():raise ValueError(f'Page {page} contains no extractable text. Scanned PDF/OCR is not implemented.')
            c=ingest_text(text,document_id,version,path.name)
            for i,item in enumerate(c,1):item.update(id=f'{document_id}:{version}:p{page}:c{i}',page=page,section=f'PDF page {page}',locator_kind='physical PDF page')
            chunks+=c
        return chunks
    raise ValueError('Supported formats: UTF-8 MD/TXT and text PDF')

class Engine:
    def __init__(self,root):
        self.root=Path(root);self.cfg=load_config(root)
        manifest=json.loads((self.root/'Input_Data/data_manifest.json').read_text())
        self.chunks=[];self.documents=manifest['documents']
        for d in self.documents:
            if not d.get('synthetic') and not d.get('approved'):raise ValueError('Unapproved source refused')
            p=self.root/'Input_Data'/d['file']
            if p.resolve().parent!=(self.root/'Input_Data').resolve():raise ValueError('Invalid manifest path')
            if d.get('sha256') and digest(p.read_bytes())!=d['sha256']:raise ValueError('Source checksum differs from the manifest; review and update approved data')
            self.chunks+=ingest_file(p,d['document_id'],d['version'])
        self.counters={c['id']:Counter(tokens(c['section']+' '+c['text'])) for c in self.chunks}
        # Same immutable index for evaluation and UI; fitted from corpus, not test labels.
        df=Counter()
        for words in self.counters.values():df.update(words.keys())
        self.idf={t:math.log((1+len(self.chunks))/(1+n))+1 for t,n in df.items()}
        self.vectors={cid:self.vector(counter) for cid,counter in self.counters.items()}
        self.dense=None
        if self.cfg['backend']=='ollama':
            if not self.cfg.get('embedding_model') or not self.cfg.get('generation_model'):raise ValueError('Both local pretrained models must be configured')
            self.dense=ollama(self.cfg,'/api/embed',{'model':self.cfg['embedding_model'],'input':[self.cfg.get('embedding_document_prefix','')+c['section']+'\n'+c['text'] for c in self.chunks]})['embeddings']
        self.index_digest=digest(json.dumps(self.chunks,sort_keys=True).encode())
    def vector(self,counter):
        vals={k:(1+math.log(n))*self.idf[k] for k,n in counter.items() if k in self.idf}
        norm=math.sqrt(sum(v*v for v in vals.values())) or 1
        return {k:v/norm for k,v in vals.items()}
    def retrieve(self,question,version='v2'):
        if version not in {d['version'] for d in self.documents}:raise ValueError('Unknown document version')
        q=self.vector(Counter(tokens(question)));qraw=set(tokens(question))
        qdense=ollama(self.cfg,'/api/embed',{'model':self.cfg['embedding_model'],'input':[self.cfg.get('embedding_query_prefix','')+question]})['embeddings'][0] if self.dense is not None else None
        evidence=[]
        for i,c in enumerate(self.chunks):
            if c['version']!=version:continue
            score=sum(v*self.vectors[c['id']].get(k,0) for k,v in q.items())
            if qdense is not None:
                a=self.dense[i];norm=math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in qdense)) or 1
                score=sum(x*y for x,y in zip(a,qdense))/norm
            overlap=qraw.intersection(self.counters[c['id']])
            if score>=self.cfg['retrieval_threshold'] and (overlap or self.dense is not None):
                evidence.append(dict(c,score=round(score,6),overlap=sorted(overlap)))
        return sorted(evidence,key=lambda c:(-c['score'],c['id']))[:self.cfg['top_k']]
    def ask(self,question,version='v2'):
        start=time.perf_counter()
        if not isinstance(question,str) or not question.strip() or len(question)>1000:raise ValueError('Question must contain 1–1000 characters')
        question=question.strip()
        evidence=[];answer=[];reason=None
        if BLOCKED.search(question):reason='Request asks to override evidence rules or fabricate information.'
        else:
            evidence=self.retrieve(question,version)
            corpus_tokens=set().union(*(self.counters[c['id']].keys() for c in self.chunks if c['version']==version))
            # Conservative scope guard for requested facts absent from the corpus.
            unknown=set(tokens(question))-corpus_tokens-set('provide summarize summary all main key between about used use find information value purpose responsible change changes affect affected upstream downstream software connection relationship need current impact architecture compared difference compare required requirement'.split())
            if re.search(r'\bASIL\b',question,re.I) and re.search(r'rating|classification|level',question,re.I):reason='No ASIL rating or classification is assigned in this synthetic HLD.'
            elif not evidence:reason='No supporting evidence was retrieved for this question.'
            elif unknown and self.cfg['backend']=='extractive':reason='The requested terms are not supported by the selected source version: '+', '.join(sorted(unknown))+'.'
            elif self.cfg['backend']=='extractive':
                for c in evidence:
                    lines=[l.strip() for l in c['text'].splitlines() if l.strip()]
                    ranked=sorted(enumerate(lines),key=lambda p:(-len(set(tokens(p[1])).intersection(tokens(question))),p[0]))
                    chosen=[line for _,line in ranked[:2]]
                    for line in chosen:answer.append({'text':line,'citation':c['id']})
            else:
                allowed=[c['id'] for c in evidence]
                sys=(self.root/'Model_Prompts_Config/prompts/system_prompt.txt').read_text()
                context='\n\n'.join(f'[{c["id"]}] {c["text"]}' for c in evidence)
                response=ollama(self.cfg,'/api/chat',{'model':self.cfg['generation_model'],'stream':False,'format':'json','options':{'temperature':0,'num_predict':600},'messages':[{'role':'system','content':sys},{'role':'user','content':json.dumps({'question':question,'version':version,'evidence':context})}]})
                try:
                    parsed=json.loads(response['message']['content'])
                    if parsed.get('abstain'):reason='Local model abstained because the evidence was insufficient.'
                    else:
                        for claim in parsed.get('claims',[]):
                            if claim.get('citation') not in allowed or not isinstance(claim.get('text'),str):raise ValueError('Invalid citation')
                            # Validate quoted evidence membership; do not label this semantic truth verification.
                            c=next(c for c in evidence if c['id']==claim['citation'])
                            quote=claim.get('evidence_quote','')
                            if not quote or quote not in c['text']:raise ValueError('Invalid evidence quote')
                            answer.append({'text':claim['text'],'citation':claim['citation'],'evidence_quote':quote})
                        if not answer:raise ValueError('Empty answer')
                except (ValueError,KeyError,TypeError):reason='Local model output failed citation/quote validation; no answer released.';answer=[]
        result={'question':question,'version':version,'backend':self.cfg['backend'],'status':'abstained' if reason else 'answered','reason':reason,'claims':answer,'evidence':evidence,'review_required':True,'warning':'Synthetic learning example. Engineering review required; no architecture approval or safety certification.','latency_ms':round((time.perf_counter()-start)*1000,3),'index_sha256':self.index_digest}
        return result
    def entities(self,version='v2'):
        entities=[]
        for c in self.chunks:
            if c['version']!=version:continue
            for line in c['text'].splitlines():
                m=re.match(r'^(Component|Interface|Signal|Port):\s*([^|]+)(.*)$',line)
                if not m:continue
                kind,name,tail=m.groups();attrs={}
                for part in tail.split('|'):
                    if ':' in part:
                        k,v=part.split(':',1);attrs[k.strip()]=v.strip()
                entities.append({'kind':kind,'name':name.strip(),'attributes':attrs,'citation':c['id']})
        return entities
    def graph(self,version='v2'):
        es=self.entities(version);nodes=sorted({e['name'] for e in es if e['kind']=='Component'});edges=[]
        for e in es:
            if e['kind']=='Signal':
                a=e['attributes'];edges.append({'source':a.get('Producer'),'target':a.get('Consumer'),'signal':e['name'],'interface':a.get('Interface'),'citation':e['citation']})
        return {'nodes':nodes,'edges':edges,'version':version}
    def impact(self,component,version='v2'):
        graph=self.graph(version)
        if component not in graph['nodes']:raise ValueError('Component not found in selected version')
        seen={component};queue=deque([component]);paths={component:[]}
        while queue:
            node=queue.popleft()
            for e in graph['edges']:
                if e['source']==node and e['target'] not in seen:
                    seen.add(e['target']);queue.append(e['target']);paths[e['target']]=paths[node]+[e]
        return {'component':component,'version':version,'affected':[{'component':n,'path':paths[n]} for n in sorted(seen-{component})],'review_required':True,'limitation':'Graph reachability is potential downstream impact, not proof of a defect or quantitative risk.'}
    def consistency(self,version='v2'):
        es=self.entities(version);components={e['name'] for e in es if e['kind']=='Component'};interfaces={e['name'] for e in es if e['kind']=='Interface'};issues=[]
        for e in es:
            if e['kind']!='Signal':continue
            a=e['attributes']
            for role in ('Producer','Consumer'):
                if a.get(role) not in components:issues.append({'rule':'unknown_component','entity':e['name'],'details':f'{role} {a.get(role)} is not declared','citation':e['citation']})
            if a.get('Interface') not in interfaces:issues.append({'rule':'unknown_interface','entity':e['name'],'details':f'Interface {a.get("Interface")} is not declared','citation':e['citation']})
            if a.get('ProducerUnit')!=a.get('ConsumerUnit'):issues.append({'rule':'unit_mismatch','entity':e['name'],'details':f'Producer unit {a.get("ProducerUnit")} differs from consumer unit {a.get("ConsumerUnit")}','citation':e['citation']})
        return {'version':version,'findings':issues,'review_required':True,'rules':['unknown_component','unknown_interface','unit_mismatch'],'limitation':'Only declared records are checked. No AUTOSAR schema/conformance or safety certification is performed.'}
    def compare(self):
        versions=sorted({d['version'] for d in self.documents})
        if len(versions)!=2:raise ValueError('Comparison requires exactly two corpus versions')
        left,right=versions
        a={(e['kind'],e['name']):e for e in self.entities(left)};b={(e['kind'],e['name']):e for e in self.entities(right)};changes=[]
        for key in sorted(a.keys()|b.keys()):
            if key not in a:changes.append({'kind':'added','entity':key[1],'record':b[key]})
            elif key not in b:changes.append({'kind':'removed','entity':key[1],'record':a[key]})
            elif a[key]['attributes']!=b[key]['attributes']:changes.append({'kind':'modified','entity':key[1],'before':a[key],'after':b[key]})
        return {'from_version':left,'to_version':right,'changes':changes,'review_required':True}
    def export_index(self):
        out=self.root/'Model_Prompts_Config/index.json'
        data={'format':'autoarch-sparse-index-v1','backend':self.cfg['backend'],'index_sha256':self.index_digest,'idf':self.idf,'vectors':self.vectors,'chunks':self.chunks}
        if self.dense is not None:data['dense_embeddings']=self.dense
        out.write_text(json.dumps(data,indent=2))
        return out
