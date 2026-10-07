"""Execute held-out reference questions. No answers are injected into the engine."""
import argparse,csv,json,platform,statistics,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoarch.engine import Engine
root=Path(__file__).resolve().parents[2];ref=root/'Evaluation_Results';p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ref);args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);engine=Engine(root)
gold=json.loads((ref/'ground_truth.json').read_text());known={c['id']:c for c in engine.chunks};rows=[];outputs=[];citation_checks=0;valid_citations=0;exact_claims=0;total_claims=0;retrieval_hits=0;answerable=0;refusal_pass=0;refusal_total=0
for test in gold:
 result=engine.ask(test['question'],test['version']);outputs.append(dict(test_id=test['id'],**result));released='\n'.join(c['text'] for c in result['claims']);retrieved={c['id'] for c in result['evidence']}
 hit=bool(retrieved.intersection(test['reference_evidence_ids'])) if test['expected_behaviour']=='answer' else None
 citation_ok=True
 for claim in result['claims']:
  citation_checks+=1;total_claims+=1;source=known.get(claim['citation']);valid=source is not None and source['version']==test['version'] and claim['citation'] in retrieved
  valid_citations+=int(valid);citation_ok&=valid
  exact_claims+=int(valid and claim['text'] in source['text'])
 if test['expected_behaviour']=='answer':
  answerable+=1;retrieval_hits+=int(hit);fragments=all(f.lower() in released.lower() for f in test['expected_fragments']);passed=result['status']=='answered' and fragments and hit and citation_ok
 else:
  refusal_total+=1;passed=result['status']=='abstained' and not result['claims'];refusal_pass+=int(passed);fragments=None
 rows.append({'id':test['id'],'question':test['question'],'version':test['version'],'expected_behaviour':test['expected_behaviour'],'actual_status':result['status'],'reference_hit':hit,'expected_fragments_present':fragments,'citations_valid':citation_ok,'passed':bool(passed),'latency_ms':result['latency_ms'],'reason':result['reason'] or '', 'actual_answer':released})
entity_gold=json.loads((ref/'entity_ground_truth.json').read_text());entity_metrics={}
for version,ref in entity_gold.items():
 expected={(k,n) for k,ns in ref.items() for n in ns};predicted={(x['kind'],x['name']) for x in engine.entities(version)};tp=len(expected&predicted)
 entity_metrics[version]={'true_positive':tp,'predicted':len(predicted),'reference':len(expected),'precision':tp/len(predicted) if predicted else 0,'recall':tp/len(expected) if expected else 0,'false_positive':sorted(predicted-expected),'false_negative':sorted(expected-predicted)}
rule_results={v:engine.consistency(v) for v in ('v1','v2')}
rule_pass=not rule_results['v1']['findings'] and [(f['rule'],f['entity']) for f in rule_results['v2']['findings']]==[('unit_mismatch','SteeringAngle')]
impact=engine.impact('VehicleStateProvider','v2');impact_pass={a['component'] for a in impact['affected']}=={'SteeringController','SafetyMonitor','DiagnosticManager'}
comparison=engine.compare();compare_pass=any(c['entity']=='VehicleSpeed' and c['kind']=='modified' for c in comparison['changes']) and any(c['entity']=='SteeringAngle' and c['kind']=='modified' for c in comparison['changes']) and any(c['entity']=='DiagnosticManager' and c['kind']=='added' for c in comparison['changes'])
latencies=[x['latency_ms'] for x in rows]
metrics={'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),'application_version':'1.0.0','backend':engine.cfg['backend'],'pretrained_model_run_verified':engine.cfg['backend']=='ollama','python_version':platform.python_version(),'platform':platform.platform(),'index_sha256':engine.index_digest,'dataset':'AUTOARCH-SYN-001; two synthetic versions, seven sections each','qa':{'total':len(rows),'passed':sum(x['passed'] for x in rows),'pass_rate':sum(x['passed'] for x in rows)/len(rows),'failed_ids':[x['id'] for x in rows if not x['passed']]},'retrieval':{'k':engine.cfg['top_k'],'answerable_questions':answerable,'reference_hits':retrieval_hits,'hit_rate_at_k':retrieval_hits/answerable},'citations':{'checked':citation_checks,'valid_source_ids_and_versions':valid_citations,'source_id_accuracy':valid_citations/citation_checks if citation_checks else None,'exact_source_line_claims':exact_claims,'total_claims':total_claims,'exact_copy_rate':exact_claims/total_claims if total_claims else None,'meaning':'Exact copied-source containment in extractive mode; not an independent semantic faithfulness score'},'abstention':{'expected':refusal_total,'correct':refusal_pass,'success_rate':refusal_pass/refusal_total},'extraction':entity_metrics,'deterministic_checks':{'unit_mismatch_seed_pass':rule_pass,'dependency_reachability_pass':impact_pass,'revision_change_checks_pass':compare_pass},'latency':{'median_ms':round(statistics.median(latencies),3),'max_ms':max(latencies),'min_ms':min(latencies),'scope':'engine query only; excludes startup, browser/network and ingestion; one run per question'},'limitations':['Small synthetic self-authored reference set; no independent automotive expert validation','Lexical baseline is not a pretrained model or an LLM','Conservative unknown-term guard can refuse valid paraphrases','Source copying proves traceability, not usefulness or full answer completeness','OCR, ARXML conformance, authentication/RBAC and production safety validation are not implemented','Local pretrained-model mode must be installed and evaluated separately']}
(out/'metrics.json').write_text(json.dumps(metrics,indent=2));(out/'sample_outputs.json').write_text(json.dumps(outputs,indent=2));(out/'deterministic_results.json').write_text(json.dumps({'consistency':rule_results,'impact':impact,'comparison':comparison},indent=2))
with (out/'evaluation_results.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (out/'retrieval_log.jsonl').open('w') as f:
 for r in outputs:f.write(json.dumps({'test_id':r['test_id'],'question':r['question'],'version':r['version'],'evidence':[{'id':c['id'],'score':c['score'],'section':c['section']} for c in r['evidence']]})+'\n')
(out/'evaluation_method.md').write_text('''# Evaluation procedure
The ground_truth.json question set and entity_ground_truth.json records were prepared before running this script. Application source never reads them. Scoring is deterministic and transparent: an answerable scenario passes if the released claims contain all expected fragments, retrieval includes at least one listed reference evidence chunk, the response is answered, and every citation is a retrieved source from the selected version. Unsupported/override scenarios pass if status is abstained and no claims are released. Citation ID validity and exact-copy source containment are distinct from semantic correctness. Extraction precision/recall compare (kind,name) pairs, not every attribute. Rule tests check a known seeded mismatch and reachability expectations. Results include failures. These are small educational synthetic checks, not a production benchmark. Re-run after any code, data, configuration or model change.\n''')
print(json.dumps(metrics,indent=2))
