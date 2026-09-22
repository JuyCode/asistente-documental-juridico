# Smoke test de ingesta y chunking (sin API key).
from pathlib import Path
import sys

sys.path.insert(0, r"C:\Users\user\Desktop\prueba1")

from core.config import from_env
from core import ingest

path = Path(r"C:\Users\user\Desktop\prueba1\test_contrato.pdf")
docs = ingest.read_pdf(path)
print(f"Documentos generados: {len(docs)}")
for d in docs:
    print(f"  - file={d.metadata['file_name']} | page={d.metadata['page_number']} | chars={len(d.text)}")
    print(f"    texto: {d.text[:100]!r}")

nodes = ingest.chunk_documents(docs)
print(f"Nodos tras chunking: {len(nodes)}")
if nodes:
    print(f"  - primer nodo conserva metadata: {nodes[0].metadata}")
    print(f"  - contenido: {nodes[0].text[:80]!r}")

cfg = from_env()
print(f"Config cargada: provider={cfg.provider}, umbral={cfg.min_similarity}, persist={cfg.persist_dir}")
print(f"Problema de config: {cfg.problem()}")
print("SMOKE OK")