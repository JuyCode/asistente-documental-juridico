# Inspección de scores de retrieval para calibrar MIN_SIMILARITY_SCORE
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\user\Desktop\prueba1")

from core.config import from_env
from core import indexer
from core.pipeline import RAGPipeline

cfg = from_env()
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
llm = GoogleGenAI(model=cfg.llama_model, api_key=cfg.gemini_api_key, temperature=0.0)
embed = GoogleGenAIEmbedding(model_name=cfg.embedding_model, api_key=cfg.gemini_api_key)
indexer.configure(embed, llm)

idx = indexer.get_or_create_index(cfg)
pipe = RAGPipeline(idx, cfg, llm)

questions = [
    "¿Cuál es el canon mensual del contrato?",
    "¿Cuál es el precio de compra del inmueble?",
    "¿Quién es el arrendatario?",
    "¿Qué color tiene el coche del arrendador?",
]
for q in questions:
    nodes = pipe.retriever.retrieve(q)
    print(f"\nQ: {q}")
    for n in nodes:
        print(f"  score={n.score:.4f} | {n.metadata.get('file_name')} p.{n.metadata.get('page_number')}")