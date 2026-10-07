import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autoarch.engine import Engine
print(Engine(Path(__file__).resolve().parents[2]).export_index())
