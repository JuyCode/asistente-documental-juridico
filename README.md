# ⚖️ Asistente Documental Jurídico/Contable (RAG estricto sobre PDFs)

Aplicación web lista para producción, desplegable gratis en **Streamlit Community Cloud**,
que responde preguntas **exclusivamente** a partir de documentos PDF (contratos, escrituras,
informes contables, expedientes…).

Garantías de comportamiento:

- ✅ **Cero alucinación**: si un dato no está en los documentos, responde literalmente
  `No dispongo de esa información en los documentos cargados.`
- ✅ **Siempre cita la fuente**: nombre del archivo + número de página.
- ✅ **Modelo B2B**: el estudio carga los documentos **una sola vez** y el cliente
  entra por el link público y **solo pregunta** (nunca ve la subida de archivos).

---

## 1. Cómo la ven el estudio y el cliente

| | Estudio (admin) | Cliente (visitante) |
|---|---|---|
| Entra | Link público + clave de admin en el panel lateral | Link público, sin login |
| Sube PDFs | ✅ (solo con `ADMIN_KEY`) | ❌ nunca |
| Borra/regenera el índice | ✅ | ❌ |
| Chat sobre los documentos | ✅ | ✅ |
| Firma "No dispongo de esa información…" | ✅ | ✅ |

---

## 1. Arquitectura

```
Usuario / Cliente
     │  HTTPS (URL pública)
     ▼
┌────────────────────────────────────────────┐
│   Streamlit Community Cloud (gratis)       │
│   - app.py (UI: chat + carga de PDFs)      │
│   - core/ (pipeline RAG estricto)          │
└──────────────┬─────────────────────────────┘
               │  API vía variables de entorno (secretas)
               ▼
        ┌──────────────┐        ┌──────────────────┐
        │  LLM +       │        │  Vector DB       │
        │  Embeddings  │        │  (embeddings)    │
        │  Gemini  │   │        │  Qdrant Cloud o  │
        │  OpenAI      │        │  persistencia local
        └──────────────┘        └──────────────────┘
```

Opciones de despliegue de la base vectorial:

| Modo | Cuándo usarlo | Persistencia |
|---|---|---|
| **Qdrant Cloud** (gratis, 1 GB) | Producción real, múltiples clientes | Permanente, en la nube |
| **Local persistente** (`data/`) | Pruebas, demo rápida | Efímera en el plan free de Cloud |

---

## 2. Estructura del proyecto

```
prueba1/
├── app.py                        # Interfaz Streamlit (chat + carga + fuentes)
├── requirements.txt              # Dependencias
├── .env.example                  # Plantilla de variables de entorno (local)
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example      # Plantilla de secretos (local / Cloud)
├── core/                         # Lógica de negocio (sin dependencias de UI)
│   ├── __init__.py
│   ├── config.py                 # Configuración: st.secrets / .env
│   ├── constants.py              # Constantes (frase de rechazo, umbrales)
│   ├── prompts.py                # Prompts estrictos con citas [n]
│   ├── ingest.py                 # PDF -> documentos por página (pypdf)
│   ├── indexer.py                # Índice vectorial (Qdrant o local)
│   └── pipeline.py               # Recuperación + filtrado + generación
└── data/                         # Índice local (generado, no se sube a GitHub)
```

---

## 3. Configuración de claves API

### Gemini (recomendado: gratis y generoso)
1. Entra a <https://aistudio.google.com/apikey>.
2. Crea una API Key (gratuita) y cópiala.
3. ⚠️ **Ojo regional**: Google puede restringir Gemini en algunos países.
   Si la API falla, usa **OpenAI** (punto siguiente).

### OpenAI (alternativa)
1. <https://platform.openai.com/api-keys> → crea una key con saldo.
2. Modelos usados: `gpt-4o-mini` + `text-embedding-3-small`.

> Con OpenAI el umbral recomendado es mayor (0.70) que con Gemini (0.50),
> porque las métricas de similitud difieren entre modelos de embeddings.

---

## 4. Despliegue paso a paso (GitHub + Streamlit Cloud)

### Paso 1 — Repositorio en GitHub
Crea un repo y sube el código:

```bash
cd C:\Users\user\Desktop\prueba1
git init
git add .
git commit -m "Asistente documental RAG estricto sobre PDFs"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

> Nunca subas `.env`, `secrets.toml` ni `data/`: ya están en `.gitignore`.

### Paso 2 — Crear cuenta en Streamlit Community Cloud
1. Entra a <https://streamlit.io/cloud> y **inicia sesión con tu cuenta de GitHub**.
2. Pulsa **"New app"**.

### Paso 3 — Conectar el repositorio
1. Selecciona el repo que acabas de crear.
2. **Branch**: `main`.
3. **Main file path**: `app.py`.
4. Pulsa **Deploy**. La primera compilación instala `requirements.txt`
   (tarda 2–4 minutos).

### Paso 4 — Añadir secretos (¡clave! el asistente no funciona sin ellos)
En el dashboard de tu app: **Settings → Secrets** y pega:

```toml
PROVIDER = "gemini"
GEMINI_API_KEY = "AIza..."
ADMIN_KEY = "elige_una_clave_larga_y_secreta"

# Si usas OpenAI en vez de Gemini:
# PROVIDER = "openai"
# OPENAI_API_KEY = "sk-..."
```

Guardas con **Save** y la app se reinicia sola.

> `ADMIN_KEY` es la única forma de cargar documentos. Compártela solo con tu equipo.

### Paso 5 — (Recomendado) Añadir Qdrant Cloud para persistencia real
Para que los documentos cargados **persistan en la nube** para todos los clientes
(aunque la app se duerma por inactividad), activa Qdrant:

1. Crea una cuenta gratis en <https://cloud.qdrant.io/>.
2. Crea un cluster **free** y copia su URL y API key.
3. Añade a los secretos:

```toml
QDRANT_URL = "https://tu-cluster.us-east-1-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "tu_clave"
QDRANT_COLLECTION = "legal_contable_docs"
```

4. Sin Qdrant, la app usa el disco local del contenedor de Streamlit (efímero):
   los documentos se pierden cuando la app duerme en el plan free.

### Paso 6 — Compartir el link con tus clientes
Tu app queda disponible en:
```
https://TU_USUARIO-TU_REPO.streamlit.app
```
Ajustes útiles (derecho de la app → **⋮ → Settings → Share**):
- **Make this app public** si quieres que cualquiera la use sin "invitación".
- Si se duerme por inactividad (plan free), se despierta solo con la primera visita.

---

## 5. Pruebas locales

```bash
# 1) Python 3.11+
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate        # Linux/macOS

# 2) Dependencias
pip install -r requirements.txt

# 3) Claves: crea tu .env copiando .env.example  (o .streamlit/secrets.toml)
copy .env.example .env             # Windows
# cp .env.example .env              # Linux/macOS
# luego edita .env y pega tus claves

# 4) Ejecutar
streamlit run app.py
```

---

## 6. Ajustar la "estrictez" (umbral de similitud)

El filtro anti-alucinación está en `MIN_SIMILARITY_SCORE`:

- **Sube el valor** (0.55–0.60) → respuestas más conservadoras, más
  probabilidad del mensaje de rechazo. Útil para datos legales exactos.
- **Bájalo** (0.45) → más recalls, permite respuestas con matices.
- Ajusta por proveedor: Gemini (gemini-embedding-2) ≈ `0.50`, OpenAI ≈ `0.70`.
- Puedes medirlo con `calibrate_test.py` y tus propios PDFs.

---

## 7. Seguridad y buenas prácticas

- Los PDFs subidos **se indexan en la memoria interna de la app**; los datos
  se envían únicamente al proveedor LLM/embeddings que elijas.
- Recomendación para estudio jurídico: firma un **DPA/DTA (acuerdo de
  tratamiento de datos)** con Google/OpenAI antes de procesar datos sensibles,
  o usa una instancia con retención de datos regional.
- No commits secretos: revisa siempre con `git status` antes de `git push`.

---

## 8. FAQ

**¿Por qué responde la frase de rechazo a veces?**
Porque ningún fragmento del PDF superó el umbral de similitud, o el dato
realmente no figura en los documentos. Es el comportamiento deseado.

**Mi Gemini falla en esta región.**
Usa `PROVIDER="openai"` o despliega la app en una región soportada.

**¿Puedo indexar PDFs escaneados (imágenes)?**
Necesitarías OCR adicional (p. ej. `pypdf` no extrae imágenes por sí solo).
Puedes añadir `pytesseract` o un lector OCR si tus expedientes son escaneados.