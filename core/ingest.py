# -*- coding: utf-8 -*-
"""
Ingesta de PDFs: convierte cada archivo en "Documentos" de LlamaIndex.

Estrategia anti-alucinación clave:
  - Se procesa página a página con pypdf.
  - Cada página genera un Document que guarda en metadatos el nombre
    del archivo y el número de página, para poder citar la fuente.
  - Las páginas muy largas se dividen en fragmentos (chunks) que
    conservan el mismo número de página (atribución precisa).
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from pypdf import PdfReader

from core.constants import EMPTY_CHARS_MIN

# Tamaño de fragmento en "tokens aproximados" (tamaño moderado para que
# el embedding sea preciso y quepa en el contexto del LLM).
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 120


def read_pdf(path: Path) -> List[Document]:
    """Extrae el texto de un PDF creando un Documento por página.

    Args:
        path: ruta al archivo PDF.

    Returns:
        Lista de Document de LlamaIndex con metadatos:
          - file_name:   nombre del archivo (para la cita)
          - page_number: número de página 1-based (para la cita)
          - total_pages: páginas totales del PDF
    """
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    documents: List[Document] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        # Saltamos páginas sin contenido útil (escaneos, portadas en blanco).
        if len(text) < EMPTY_CHARS_MIN:
            continue
        documents.append(
            Document(
                text=text,
                metadata={
                    "file_name": path.name,
                    "page_number": page_number,
                    "total_pages": total_pages,
                },
            )
        )
    return documents


def chunk_documents(documents: List[Document]) -> List:
    """Divide las páginas largas en fragmentos, conservando metadatos.

    SentenceSplitter crea "Nodes" que heredan los metadatos del Document
    fuente, por lo que cada fragmento sigue sabiendo a qué archivo y a
    qué página pertenece.
    """
    parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    nodes = []
    for doc in documents:
        parsed = parser.get_nodes_from_documents([doc])
        nodes.extend(parsed or [doc])  # si no fragmenta, usamos la página tal cual
    return nodes