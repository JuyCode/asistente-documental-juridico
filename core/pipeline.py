# -*- coding: utf-8 -*-
"""
Pipeline RAG: recuperación + generación estricta con citas.

Flujo de una pregunta:
  1) Se recuperan los fragmentos más similares (top_k).
  2) Filtro por umbral de similitud (min_similarity): los fragmentos
     poco relevantes se descartan. Si no queda ninguno -> rechazo.
  3) Se arma el contexto numerado [1], [2], ... y el prompt estricto.
  4) El LLM genera la respuesta citando cada fuente con [n].
"""
from __future__ import annotations

from typing import Dict, Generator, List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.llms import ChatMessage, MessageRole

from core import prompts
from core.config import AppConfig
from core.constants import REFUSAL_RESPONSE

# Historial máximo de turnos que se incluye como contexto conversacional.
MAX_HISTORY_TURNS = 6


class RAGPipeline:
    """Encapsula recuperación + generación para una sesión dada."""

    def __init__(self, index: VectorStoreIndex, config: AppConfig, llm):
        self.index = index
        self.config = config
        self.llm = llm
        # Retriever configurado con el top_k deseado.
        self.retriever = index.as_retriever(similarity_top_k=config.top_k)

    # ------------------------------------------------------------------
    def retrieve(self, question: str) -> List:
        """Recupera y filtra fragmentos por umbral de similitud.

        - Se descartan duplicados (el vector store puede devolver el mismo
          fragmento más de una vez cuando hay pocos documentos).
        - Si un fragmento no tiene score (None) se conserva; de lo contrario
          debe superar o igualar `min_similarity`.
        """
        nodes = self.retriever.retrieve(question)

        seen_ids = set()
        unique = []
        for node in nodes:
            if node.node_id in seen_ids:
                continue
            seen_ids.add(node.node_id)
            unique.append(node)

        filtered = [
            n
            for n in unique
            if n.score is None or n.score >= self.config.min_similarity
        ]
        return filtered[: self.config.top_k]

    @staticmethod
    def sources_from(nodes: List) -> List[Dict]:
        """Exporta las fuentes para mostrarlas en la interfaz."""
        sources = []
        for i, node in enumerate(nodes, start=1):
            sources.append(
                {
                    "marker": i,
                    "file": node.metadata.get("file_name", "documento"),
                    "page": node.metadata.get("page_number", "—"),
                    "text": (node.text or "")[:600],
                }
            )
        return sources

    # ------------------------------------------------------------------
    def build_messages(
        self, question: str, history: List[Dict], nodes: List
    ) -> List[ChatMessage]:
        """Construye el historial de mensajes para el LLM.

        Se incluyen los últimos turnos de la conversación para dar contexto,
        pero el CONTEXTO (fragmentos) corresponde siempre a la pregunta actual.
        """
        messages = [ChatMessage(role=MessageRole.SYSTEM, content=prompts.SYSTEM_PROMPT)]

        for turn in history[-MAX_HISTORY_TURNS:]:
            role = MessageRole.USER if turn.get("role") == "user" else MessageRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        context = prompts.build_context(nodes)
        messages.append(
            ChatMessage(role=MessageRole.USER, content=prompts.user_prompt(question, context))
        )
        return messages

    # ------------------------------------------------------------------
    def run(
        self, question: str, history: List[Dict]
    ) -> (Generator[str, None, None], Dict):
        """Ejecuta el pipeline completo.

        Returns:
            - Generador de tokens de la respuesta (para streaming).
            - Metadata con:
                * refused: True si no había fuentes suficientes.
                * sources: lista de fuentes usadas (vacía si refused).
        """
        nodes = self.retrieve(question)
        sources = self.sources_from(nodes)

        if not nodes:
            # No hay información relevante -> respuesta exacta de rechazo.
            def _refusal():
                yield REFUSAL_RESPONSE

            return _refusal(), {"refused": True, "sources": []}

        messages = self.build_messages(question, history, nodes)
        stream = self.llm.stream_chat(messages)

        def _gen():
            for token in stream:
                yield token.delta

        return _gen(), {"refused": False, "sources": sources}