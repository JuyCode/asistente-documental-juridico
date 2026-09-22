# -*- coding: utf-8 -*-
"""Constantes globales del proyecto."""

# Respuesta exacta que debe devolver el asistente cuando el dato
# no está en los documentos. Se usa tanto en el prompt como en el
# filtro de recuperación (evitando que el LLM "invente" la respuesta).
REFUSAL_RESPONSE = "No dispongo de esa información en los documentos cargados."

# Mínimo de caracteres para considerar que una página tiene contenido
# real (las páginas escaneadas o vacías suelen extraer texto vacío).
EMPTY_CHARS_MIN = 40