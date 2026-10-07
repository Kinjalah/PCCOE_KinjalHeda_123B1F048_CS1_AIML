"""Activate explicitly installed local models; preserve baseline and record provenance."""
import json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoarch.engine import ollama
root=Path(__file__).resolve().parents[2];folder=root/'Model_Prompts_Config';cfg=json.loads((folder/'model_config_ollama_example.json').read_text())
# POST to /api/show verifies the installed model; it does not download or approve it.
models={}
for key in ['generation_model','embedding_model']:
 response=ollama(cfg,'/api/show',{'model':cfg[key]});models[key]={'requested_name':cfg[key],'details':response.get('details',{}),'model_info':response.get('model_info',{}),'parameters':response.get('parameters',''),'license':response.get('license',''),'capabilities':response.get('capabilities',[])}
import urllib.request
with urllib.request.urlopen(cfg['ollama_url']+'/api/tags',timeout=10) as res:tags=json.load(res)
with urllib.request.urlopen(cfg['ollama_url']+'/api/version',timeout=10) as res:version=json.load(res)
provenance={'ollama':version,'installed_tags_and_digests':tags,'models':models,'execution_quality_verified':False}
backup=folder/'model_config_extractive_backup.json'
if not backup.exists():shutil.copyfile(folder/'model_config.json',backup)
(folder/'local_model_provenance.json').write_text(json.dumps(provenance,indent=2));(folder/'model_config.json').write_text(json.dumps(cfg,indent=2));print('Local candidate configuration activated. Restart and evaluate separately; execution quality remains unverified.')
