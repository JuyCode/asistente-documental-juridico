# -*- coding: utf-8 -*-
"""
Indexer: crea, carga y actualiza el índice vectorial.

Dos modos de almacenamiento (100% en la nube o local):

  A) QDRANT CLOUD (recomendado para producción):
     - Se configura QDRANT_URL + QDRANT_API_KEY (capa gratuita de Qdrant).
     - Los embeddings viven en la nube, persistidos entre sesiones.
     - Ideal para Streamlit Community Cloud (donde el disco es efímero).

  B) LOCAL PERSISTENTE (default si no hay Qdrant):
     - El índice se guarda en ./data/index (SimpleVectorStore).
     - Perfecto para pruebas locales y demos; en Community Cloud los
       archivos se conservan mientras la app esté activa en el plan free.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core import load_index_from_storage
from qdrant_client import QdrantClient

from core.config import AppConfig
from llama_index.vector_stores.qdrant import QdrantVectorStore

_MANIFEST = ".manifest.json"


def configure(embed_model, llm) -> None:
    """Configura los modelos globales de LlamaIndex (Settings)."""
    Settings.embed_model = embed_model
    Settings.llm = llm


# ----------------------------------------------------------------------
# Creación de índices
# ----------------------------------------------------------------------
def build_qdrant_index(config: AppConfig) -> VectorStoreIndex:
    """Conecta (o crea) una colección Qdrant en la nube."""
    client = QdrantClient(url=config.qdrant_url, api_key=config.qdrant_api_key)
    vector_store = QdrantVectorStore(
        client=client, collection_name=config.qdrant_collection
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )


def load_local_index(config: AppConfig) -> VectorStoreIndex:
    """Carga el índice local si existe; si no, crea uno vacío.

    Nota: en LlamaIndex, `StorageContext.from_defaults(persist_dir=...)`
    es SOLO para cargar persistencia existente (llama los archivos en disco).
    Para crear uno nuevo hay que usar `StorageContext()` sin persist_dir y
    persistir después de forma explícita.
    """
    persist_dir = Path(config.persist_dir)
    docstore_file = persist_dir / "docstore.json"

    if docstore_file.exists():
        storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
        # load_index_from_storage reconstruye el índice completo (docstore +
        # vector store + index store). from_vector_store solo aplica a
        # stores que guardan el texto en sí mismas (p. ej. Qdrant).
        return load_index_from_storage(storage_context)

    # Índice vacío inicial.
    persist_dir.mkdir(parents=True, exist_ok=True)
    storage_context = StorageContext.from_defaults()
    index = VectorStoreIndex.from_documents([], storage_context=storage_context)
    storage_context.persist(persist_dir=str(persist_dir))
    return index


def get_or_create_index(config: AppConfig) -> VectorStoreIndex:
    """Devuelve un índice listo para consultar/insertar según la config."""
    if config.uses_qdrant:
        return build_qdrant_index(config)
    return load_local_index(config)


# ----------------------------------------------------------------------
# Inserción
# ----------------------------------------------------------------------
def insert_documents(index: VectorStoreIndex, config: AppConfig, nodes: List) -> None:
    """Inserta nodos en el índice y persiste los cambios."""
    if nodes:
        index.insert_nodes(nodes)
    if not config.uses_qdrant:
        Path(config.persist_dir).mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=config.persist_dir)


# ----------------------------------------------------------------------
# Manifest: lista de archivos indexados (para mostrar en la UI)
# ----------------------------------------------------------------------
def get_manifest(config: AppConfig) -> List[str]:
    """Lee los nombres de archivo ya indexados."""
    manifest_path = Path(config.persist_dir) / _MANIFEST
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_manifest(config: AppConfig, names: List[str]) -> None:
    """Persiste la lista de archivos indexados."""
    manifest_path = Path(config.persist_dir)
    manifest_path.mkdir(parents=True, exist_ok=True)
    (manifest_path / _MANIFEST).write_text(
        json.dumps(sorted(set(names)), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_local_index(config: AppConfig) -> None:
    """Borra el índice local (modo de prueba / reset)."""
    if config.uses_qdrant:
        return
    persist_dir = Path(config.persist_dir)
    if persist_dir.exists():
        for f in persist_dir.rglob("*"):
            if f.is_file():
                f.unlink()