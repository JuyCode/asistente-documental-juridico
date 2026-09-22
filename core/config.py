# -*- coding: utf-8 -*-
"""
Configuración central de la aplicación.

Las claves pueden venir de dos fuentes, en este orden de prioridad:
  1) secrets de Streamlit (st.secrets  ->  .streamlit/secrets.toml)
  2) variables de entorno  (archivo .env en la raíz del proyecto)

En Streamlit Cloud las secrets se cargan desde el panel
"Settings -> Secrets" y se inyectan aquí automáticamente.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _as_float(name: str, default: float) -> float:
    """Lee una variable como float tolerando valores inválidos."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = float(raw)
        return default if math.isnan(value) else value
    except (TypeError, ValueError):
        return default


def _as_int(name: str, default: int) -> int:
    """Lee una variable como int tolerando valores inválidos."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class AppConfig:
    """Configuración completa de la aplicación (inmutable por convención)."""

    # Proveedor de LLM + embeddings: "gemini" (por defecto) o "openai".
    provider: str = "gemini"
    # Claves de API (nunca deben committearse).
    gemini_api_key: str = ""
    openai_api_key: str = ""
    # Modelos (se puede sobrescribir con variables de entorno).
    llm_model: str = ""          # ej: "models/gemini-3.6-flash" o "gpt-4o-mini"
    embed_model: str = ""        # ej: "models/gemini-embedding-2" o "text-embedding-3-small"
    # Vector DB Qdrant Cloud (opcional). Si QDRANT_URL y QDRANT_API_KEY
    # están vacías, la app usa el modo "local persistente" (./data).
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "legal_contable_docs"
    # Umbral de similitud mínima (0..1): si ningún fragmento supera este
    # valor, el asistente responde la frase de rechazo (cero alucinación).
    # El default depende del proveedor (rango de scores distinto):
    #   gemini-embedding-2 ≈ 0.50 · openai text-embedding-3 ≈ 0.70
    min_similarity: float = 0.50
    # Cantidad de fragmentos recuperados por consulta.
    top_k: int = 4
    # Carpeta de persistencia local del índice.
    persist_dir: str = "data/index"
    # Cachea variables no usadas oficialmente (tolerante a ampliaciones).
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    @property
    def llama_model(self) -> str:
        """Nombre final del modelo de chat."""
        if self.llm_model:
            return self.llm_model
        return "models/gemini-3.6-flash" if self.provider == "gemini" else "gpt-4o-mini"

    @property
    def embedding_model(self) -> str:
        """Nombre final del modelo de embeddings."""
        if self.embed_model:
            return self.embed_model
        return "models/gemini-embedding-2" if self.provider == "gemini" else "text-embedding-3-small"

    @property
    def uses_qdrant(self) -> bool:
        """True si configuramos una base vectorial en la nube."""
        return bool(self.qdrant_url and self.qdrant_api_key)

    def problem(self) -> Optional[str]:
        """Devuelve un string describiendo el problema de configuración,
        o None si la configuración está lista para usar."""
        if self.provider not in ("gemini", "openai"):
            return f"PROVIDER inválido: '{self.provider}'. Usar 'gemini' u 'openai'."
        if self.provider == "gemini" and not self.gemini_api_key:
            return "Falta GEMINI_API_KEY."
        if self.provider == "openai" and not self.openai_api_key:
            return "Falta OPENAI_API_KEY."
        if self.uses_qdrant and not self.qdrant_collection:
            return "Falta QDRANT_COLLECTION."
        return None


def from_env() -> AppConfig:
    """Construye la configuración desde variables de entorno.

    Si existe un archivo .env en la raíz, se carga automáticamente
    (sin sobrescribir variables que ya estén definidas en el sistema).
    """
    if load_dotenv is not None:
        load_dotenv(override=False)

    provider = (os.getenv("PROVIDER") or "gemini").strip().lower()
    return AppConfig(
        provider=provider,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        embed_model=os.getenv("EMBEDDING_MODEL", "").strip(),
        qdrant_url=os.getenv("QDRANT_URL", "").strip(),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
        qdrant_collection=(os.getenv("QDRANT_COLLECTION") or "legal_contable_docs").strip(),
        # Umbral por defecto dependiente del proveedor (rango de scores distintos).
        min_similarity=_as_float(
            "MIN_SIMILARITY_SCORE", 0.50 if provider == "gemini" else 0.70
        ),
        top_k=_as_int("TOP_K", 4),
        persist_dir=(os.getenv("LOCAL_PERSIST_DIR") or "data/index").strip(),
    )