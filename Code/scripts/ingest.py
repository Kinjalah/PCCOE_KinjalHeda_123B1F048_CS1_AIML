"""Validate one local file and export citation-aware chunks; does not silently add data."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoarch.engine import ingest_file
p=argparse.ArgumentParser();p.add_argument('file',type=Path);p.add_argument('--document-id',required=True);p.add_argument('--version',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.write_text(json.dumps(ingest_file(a.file,a.document_id,a.version),indent=2))
print(a.output)
