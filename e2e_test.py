# E2E test: índice + embeddings + LLM + citas (requiere GEMINI_API_KEY en .env)
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\user\Desktop\prueba1")

from core.config import from_env
from core import ingest, indexer
from core.pipeline import RAGPipeline

cfg = from_env()
problem = cfg.problem()
print(f"Proveedor: {cfg.provider} | Modelo: {cfg.llama_model} | Embedding: {cfg.embedding_model}")
if problem:
    print(f"ERROR config: {problem}")
    sys.exit(1)

# 1) Modelos
if cfg.provider == "gemini":
    from llama_index.llms.google_genai import GoogleGenAI
    from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
    llm = GoogleGenAI(model=cfg.llama_model, api_key=cfg.gemini_api_key, temperature=0.0)
    embed = GoogleGenAIEmbedding(model_name=cfg.embedding_model, api_key=cfg.gemini_api_key)
else:
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding
    llm = OpenAI(model=cfg.llama_model, api_key=cfg.openai_api_key, temperature=0.0)
    embed = OpenAIEmbedding(model=cfg.embedding_model, api_key=cfg.openai_api_key)

indexer.configure(embed, llm)
print("Modelos configurados OK")

# 2) Índice local + inserción del PDF de prueba
idx = indexer.get_or_create_index(cfg)
docs = ingest.read_pdf(Path(r"C:\Users\user\Desktop\prueba1\test_contrato.pdf"))
nodes = ingest.chunk_documents(docs)
indexer.insert_documents(idx, cfg, nodes)
indexer.save_manifest(cfg, ["test_contrato.pdf"])
print(f"Indexados {len(nodes)} nodos | persist: {cfg.persist_dir}")

# 3) Pipeline real
pipe = RAGPipeline(idx, cfg, llm)

print("\n--- Pregunta 1: dato presente ---")
gen, meta = pipe.run("¿Cuál es el canon mensual del contrato?", [])
answer = "".join(gen)
print(answer)
print("FUENTES:", meta["sources"])

print("\n--- Pregunta 2: dato NO presente ---")
gen2, meta2 = pipe.run("¿Cuál es el precio de compra del inmueble?", [])
answer2 = "".join(gen2)
print(answer2)
print("refused:", meta2["refused"], "| sources:", meta2["sources"])
print("E2E OK")