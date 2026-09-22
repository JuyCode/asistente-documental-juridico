# -*- coding: utf-8 -*-
"""
Prompts y plantillas de contexto del asistente.

El diseño es deliberadamente estricto:
  - El LLM solo recibe los fragmentos recuperados como "CONTEXTO".
  - Se le ordena explícitamente no usar conocimiento previo.
  - Debe citar cada fuente con [n] y, si falta el dato, responder con
    la frase exacta de rechazo (sin inventar nada).
"""
from __future__ import annotations

from typing import Sequence

from core.constants import REFUSAL_RESPONSE

# Prompt de sistema: define el rol y las reglas inquebrantables.
SYSTEM_PROMPT = (
    "Eres un asistente jurídico-contable senior, especializado en responder "
    "exclusivamente sobre los documentos que el usuario ha cargado.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. SOLO puedes basarte en el bloque <CONTEXTO> del mensaje del usuario. "
    "NUNCA uses conocimiento memorizado del modelo ni inventes datos.\n"
    "2. Cada afirmación o dato debe terminar citando su fuente con [n], donde "
    "n es el número de la fuente dentro del CONTEXTO. Si una respuesta usa "
    "varias fuentes, cita todas las que apliquen.\n"
    "3. Si el CONTEXTO no contiene la información preguntada, debes responder "
    f"ÚNICAMENTE con esta frase exacta: \"{REFUSAL_RESPONSE}\".\n"
    "4. No agregues interpretaciones, deducciones ni información que no tenga "
    "soporte textual en el CONTEXTO.\n"
    "5. Si el usuario pregunta por números, fechas, partes firmantes, montos o "
    "cláusulas, transcríbelos EXACTAMENTE como están en el CONTEXTO, sin recalcular.\n"
    "6. No digas que consultarás o que buscarás: si el dato no está, aplica la regla 3.\n"
    "7. Responde siempre en español, con tono formal y técnico.\n"
)


def build_context(nodes: Sequence) -> str:
    """Construye el bloque <CONTEXTO> numerado con sus fuentes.

    Cada fragmento se presenta como:
      [n] Archivo: <nombre> | Página: <página>
      <texto>
    para que el LLM pueda referenciarlo con [n].
    """
    parts = []
    for i, node in enumerate(nodes, start=1):
        file_name = node.metadata.get("file_name", "documento_desconocido")
        page = node.metadata.get("page_number", "—")
        text = (node.text or "").strip()
        parts.append(f"[{i}] Archivo: {file_name} | Página: {page}\n{text}")
    return "\n\n".join(parts)


def user_prompt(question: str, context: str) -> str:
    """Compone el prompt del usuario: pregunta + contexto numerado."""
    return (
        f"Pregunta del usuario:\n{question}\n\n"
        f"### COMIENZO DEL CONTEXTO (únicos datos permitidos) ###\n{context}\n"
        f"### FIN DEL CONTEXTO ###\n\n"
        f"Responde SOLO con el CONTEXTO y cita tus fuentes con [n]. "
        f"Si el dato no está en el CONTEXTO, responde exactamente: "
        f"\"{REFUSAL_RESPONSE}\"."
    )