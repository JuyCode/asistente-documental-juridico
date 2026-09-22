# -*- coding: utf-8 -*-
"""
=====================================================================
 Asistente Documental Jurídico/Contable  (RAG estricto sobre PDFs)
=====================================================================
 Aplicación Streamlit lista para desplegar en Streamlit Community Cloud.

 Comportamiento garantizado:
   * Responde SOLO con datos textuales presentes en los PDFs cargados.
   * Si el dato no está, responde exactamente:
     "No dispongo de esa información en los documentos cargados."
   * Siempre cita la fuente: nombre del archivo + número de página.

 Cómo correrlo en local:
   streamlit run app.py

 Módulos:
   core/config.py   -> configuración (secrets / .env)
   core/prompts.py  -> prompts estrictos con citas [n]
   core/ingest.py   -> PDF -> documentos por página
   core/indexer.py  -> índice vectorial (Qdrant Cloud o local)
   core/pipeline.py -> recuperación + filtrado + generación
=====================================================================
"""
import os
import tempfile
from pathlib import Path

import streamlit as st

from core import indexer, ingest
from core.config import AppConfig, from_env
from core.constants import REFUSAL_RESPONSE
from core.pipeline import RAGPipeline

# -------------------------------------------------------------------
# Configuración de página (DEBE ser la primera orden de Streamlit)
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Asistente Documental Jurídico",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------
# Utilidades
# -------------------------------------------------------------------
def merge_secrets_into_env() -> None:
    """Copia los secretos de Streamlit a variables de entorno."""
    try:
        for key, value in st.secrets.items():
            os.environ.setdefault(key, str(value))
    except Exception:
        pass  # sin secretos definidos (modo local con .env)


def get_config() -> AppConfig:
    """Configuración única: st.secrets tiene prioridad sobre .env."""
    merge_secrets_into_env()
    return from_env()


def build_models(config: AppConfig):
    """Instancia el LLM y el modelo de embeddings del proveedor elegido."""
    if config.provider == "openai":
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI

        llm = OpenAI(
            model=config.llama_model, api_key=config.openai_api_key, temperature=0.0
        )
        embed = OpenAIEmbedding(
            model=config.embedding_model, api_key=config.openai_api_key
        )
    else:
        # SDK unificado de Google (google-genai). Reemplaza al antiguo
        # llama-index-llms-gemini / llama-index-embeddings-gemini (EOL).
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        from llama_index.llms.google_genai import GoogleGenAI

        llm = GoogleGenAI(
            model=config.llama_model, api_key=config.gemini_api_key, temperature=0.0
        )
        embed = GoogleGenAIEmbedding(
            model_name=config.embedding_model, api_key=config.gemini_api_key
        )
    return llm, embed


def render_source_expander(sources: list) -> None:
    """Dibuja las fuentes citadas con su fragmento textual."""
    with st.expander("📎 Fuentes citadas", expanded=False):
        for src in sources:
            st.markdown(
                f"**[{src['marker']}]** `{src['file']}` — Página {src['page']}"
            )
            with st.expander("Ver fragmento del documento"):
                st.caption(src["text"])


def load_existing_index(config: AppConfig) -> None:
    """Al iniciar, si hay un índice previo (local), lo restaura."""
    if st.session_state.index is not None:
        return
    try:
        idx = indexer.get_or_create_index(config)
        st.session_state.index = idx
        st.session_state.docs = indexer.get_manifest(config)
        st.session_state.pipeline = RAGPipeline(idx, config, st.session_state.llm)
    except Exception as exc:  # pragma: no cover
        st.sidebar.warning(f"No se pudo cargar el índice previo: {exc}")


# -------------------------------------------------------------------
# Estado de sesión (sobrevive a cada re-ejecución de Streamlit)
# -------------------------------------------------------------------
if "index" not in st.session_state:
    st.session_state.index = None
if "pipeline" not in st.session_state:
    st.session_state.pipeline = None
if "docs" not in st.session_state:
    st.session_state.docs = []
if "llm" not in st.session_state:
    st.session_state.llm = None
if "embed" not in st.session_state:
    st.session_state.embed = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------------------------------------------
# Configuración + modelos
# -------------------------------------------------------------------
config = get_config()
config_problem = config.problem()

# Instanciamos modelos una sola vez por sesión.
if st.session_state.llm is None and config_problem is None:
    st.session_state.llm, st.session_state.embed = build_models(config)
    indexer.configure(st.session_state.embed, st.session_state.llm)

if st.session_state.llm is not None:
    indexer.configure(st.session_state.embed, st.session_state.llm)

if config_problem is None:
    load_existing_index(config)

# -------------------------------------------------------------------
# BARRA LATERAL
# -------------------------------------------------------------------
with st.sidebar:
    st.title("⚖️ Asistente Documental")
    st.caption("Estudio Jurídico / Contable · RAG estricto")

    # Estado del proveedor -------------------------------------------------
    st.subheader("🔌 Motor")
    if config_problem:
        st.error(f"Configuración incompleta: {config_problem}")
        st.info(
            "Configura tus claves en `.streamlit/secrets.toml` (local) o en "
            "**Settings → Secrets** (Streamlit Cloud)."
        )
    else:
        st.success(f"Proveedor: **{config.provider}**")
        st.caption(
            f"LLM: `{config.llama_model}`\n\n"
            f"Embeddings: `{config.embedding_model}`\n\n"
            f"Vector DB: {'Qdrant Cloud' if config.uses_qdrant else 'Local (./data)'}"
        )
        st.caption(f"Umbral de similitud: **{config.min_similarity}** · top_k: **{config.top_k}**")

    # Carga de PDFs --------------------------------------------------------
    st.subheader("📄 Documentos")
    pdfs = st.file_uploader(
        "Sube tus PDFs (contratos, escrituras, informes…)",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdfs",
    )

    if st.button("🔄 Indexar documentos", type="primary", use_container_width=True):
        if config_problem:
            st.error("Primero configura las claves de API.")
        elif not pdfs:
            st.warning("No hay archivos PDF para procesar.")
        else:
            with st.spinner("Extrayendo texto y generando embeddings…"):
                existing = set(indexer.get_manifest(config))
                new_nodes = []
                new_names = []
                skipped = 0

                for f in pdfs:
                    if f.name in existing:
                        skipped += 1
                        continue
                    # Escribimos el archivo subido a un temporal para pypdf.
                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as tmp:
                        tmp.write(f.getbuffer())
                        tmp_path = tmp.name
                    try:
                        docs = ingest.read_pdf(Path(tmp_path))
                        new_nodes.extend(ingest.chunk_documents(docs))
                        new_names.append(f.name)
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)

                # Obtenemos/creamos el índice y lo actualizamos.
                idx = st.session_state.index or indexer.get_or_create_index(config)
                indexer.insert_documents(idx, config, new_nodes)
                indexer.save_manifest(config, existing | set(new_names))

                st.session_state.index = idx
                st.session_state.pipeline = RAGPipeline(idx, config, st.session_state.llm)
                st.session_state.docs = indexer.get_manifest(config)
                # Al cambiar los documentos, reiniciamos el chat.
                st.session_state.messages = []

                if new_names:
                    st.success(f"✅ Indexados: {', '.join(new_names)}")
                if skipped:
                    st.info(f"⏭️ Ya estaban indexados: {skipped} archivo(s).")

    # Documentos actualmente indexados -------------------------------------
    if st.session_state.docs:
        st.caption(f"**{len(st.session_state.docs)} documento(s) indexado(s):**")
        for name in st.session_state.docs:
            st.markdown(f"- `{name}`")

    st.divider()

    # Acciones de sesión ----------------------------------------------------
    if st.button("🧹 Limpiar chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🗑️ Borrar índice local", use_container_width=True):
        indexer.clear_local_index(config)
        st.session_state.index = None
        st.session_state.pipeline = None
        st.session_state.docs = []
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "🔒 El asistente responde **solo** con el contenido de tus documentos. "
        "No usa conocimiento previo y cita cada fuente."
    )

# -------------------------------------------------------------------
# ÁREA PRINCIPAL: CABECERA
# -------------------------------------------------------------------
st.title("📚 Consultas sobre tus documentos")
st.markdown(
    "Haz preguntas sobre los PDFs cargados. Cada respuesta cita su **fuente** "
    "(archivo y página). Si el dato no está en los documentos, te lo indicará."
)

# -------------------------------------------------------------------
# ÁREA PRINCIPAL: CHAT
# -------------------------------------------------------------------
# Render histórico de mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            render_source_expander(msg["sources"])

# Determinamos si el chat debe estar habilitado -------------------------
no_docs = st.session_state.index is None
chat_disabled = config_problem is not None

placeholder = "Escribe tu consulta sobre los documentos…"
if no_docs:
    placeholder = "Sube y indexa documentos primero (panel izquierdo)."
if chat_disabled:
    placeholder = "Configura las claves de API para comenzar."

prompt = st.chat_input(placeholder, disabled=chat_disabled or no_docs)

if prompt:
    # Turno del usuario ----------------------------------------------------
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta del asistente ----------------------------------------------
    with st.chat_message("assistant"):
        try:
            gen, meta = st.session_state.pipeline.run(
                prompt, st.session_state.messages[:-1]
            )
            answer = st.write_stream(gen)

            # Salvaguarda doble contra alucinación:
            # 1) Si el LLM respondió vacío -> rechazo.
            # 2) Si el LLM se "auto-rechazó" (variante de la frase canónica),
            #    normalizamos a la frase exacta y descartamos las fuentes.
            refusal_key = REFUSAL_RESPONSE.lower().split(" información")[0]
            if not (answer or "").strip():
                answer = REFUSAL_RESPONSE
                st.markdown(answer)
            elif refusal_key in answer.lower():
                answer = REFUSAL_RESPONSE
                meta["sources"] = []
                st.markdown(answer)

            if meta["sources"]:
                render_source_expander(meta["sources"])
        except Exception as exc:  # pragma: no cover
            answer = (
                "Ocurrió un error al consultar los documentos. "
                f"Detalle: {exc}"
            )
            st.error(answer)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": meta.get("sources", []) if "meta" in locals() else [],
            }
        )