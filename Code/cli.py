"""Run the same submitted engine from a terminal, without a browser."""
import argparse,json
from pathlib import Path
from autoarch.engine import Engine
p=argparse.ArgumentParser(description='AutoArch AI local HLD analysis');p.add_argument('action',choices=['status','ask','entities','graph','impact','compare','consistency']);p.add_argument('--version',default='v2');p.add_argument('--question');p.add_argument('--component',default='VehicleStateProvider');a=p.parse_args();e=Engine(Path(__file__).resolve().parents[1])
if a.action=='status':r={'application':'AutoArch AI','backend':e.cfg['backend'],'documents':e.documents,'chunk_count':len(e.chunks),'index_sha256':e.index_digest,'configuration':e.cfg}
elif a.action=='ask':r=e.ask(a.question,a.version)
elif a.action=='impact':r=e.impact(a.component,a.version)
elif a.action=='compare':r=e.compare()
else:r=getattr(e,a.action)(a.version)
print(json.dumps(r,indent=2))
