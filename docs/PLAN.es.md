# Erasmus DocFlow — planning del equipo (Español)

Plan hackathon para 4 personas en repo compartido. Límite duro: entrega 19:00,
demo 19:10. Tiempos relativos (`H0` = inicio). Comprimir o estirar según reloj
real, mantener el orden.

## Objetivo

El agente lee una carpeta de `.eml` desordenados, deduce alumno + tipo de
documento + semestre, guarda ficheros como
`Apellido_Nombre_TipoDocumento_2026-27.pdf`, rellena una fila por alumno en
`students.xlsx`, responde preguntas frecuentes desde `faq.md` y manda lo dudoso
a una persona.

## Stack

- Python 3.11+ (Streamlit Cloud usa 3.12; probado en local con 3.14)
- Google ADK (`google-adk`) + API key de Gemini desde AI Studio
- `email` de la stdlib para `.eml`, `openpyxl` para `.xlsx`
- UI Streamlit desplegada en **Streamlit Community Cloud** (URL pública, gratis)
- `adk web` para depurar el agente en local
- Git + repo público en GitHub

## Contrato del repo (congelar en H1, avisar antes de cambiarlo)

- Tipos de documento: `LearningAgreement`, `Transcript`, `Insurance`,
  `CertificateOfArrival`, `Other`
- Campos estructurados: `student_first_name`, `student_surname`, `doc_type`,
  `semester`, `host_university`, `start_date`, `end_date`, `deadline`,
  `confidence`, `notes`
- Nombres: `Apellido_Nombre_TipoDocumento_YYYY-YY.ext` (`erasmus_agent/schemas.py`)
- Escalado: `confidence < 0.7`, `doc_type == Other` o falta apellido va a
  `data/review/` y marca `status=needs_review` en el Excel
- Firmas de tools en `erasmus_agent/tools/` y `erasmus_agent/pipeline.py`

## Roles

| Persona | Responsable de | Ficheros |
|---|---|---|
| A — Agente/LLM | prompts, structured output, agente ADK, FAQ | `llm.py`, `agent.py`, `faq.md` |
| B — Email/ficheros | parseo `.eml`, adjuntos, naming, carpeta review | `tools/email_reader.py`, `tools/file_saver.py` |
| C — Datos | filas Excel, flags de faltantes/caducados, borradores | `tools/excel_writer.py`, `pipeline.py` |
| D — UI/demo/repo | UI Streamlit, datos de prueba, deploy, README, entrega, slides | `app.py`, `scripts/`, `.github/` |

Todos pueden tocar ficheros compartidos, pero avisar antes en el chat del grupo.

## Cronograma

| Fase | Franja | Trabajo |
|---|---|---|
| 0. Setup | H0–H0:30 | Repo subido, `.env` por persona, key funcionando, contrato congelado |
| 1. Esqueleto | H0:30–H1 | Emails de prueba generados, cada dueño rellena su módulo |
| 2. MVP paralelo | H1–H3 | B: lee y guarda un email. C: escribe una fila. A: clasifica un PDF. D: shell UI + deploy |
| 3. Integración | H3–H4:30 | `run_inbox()` completo con 10 emails; dudosos a review |
| 4. Respuestas + extras | H4:30–H5:45 | chat FAQ, flags de faltantes, borrador de respuesta, botones de descarga |
| 5. Freeze + demo | H5:45–H6:30 | Sin features nuevas. README, URL pública, vídeo de respaldo |
| 6. Entrega | H6:30–H7 | Título, pitch, reto, descripción, link repo público — antes de 19:00 |
| 7. Presentar | 19:10 | 30s problema, 3.5 min demo en vivo, 1 min impacto |

Nice-to-have solo después de fase 4: bandeja Gmail real, descarga desde web.

## Git

- `main` protegida; ramas cortas `feat/email-reader`, `fix/xlsx-dates`
- PR a `main`, otra persona revisa en 2 minutos; squash merge
- Commits: `feat:`, `fix:`, `chore:`, `docs:`
- D resuelve conflictos y mantiene `main` desplegable siempre
- Nunca commitear `.env`, `data/out`, `data/review`, `students.xlsx`

## Interfaz + despliegue

Streamlit (`app.py`): bonito, rápido y deploy en un clic.

1. Subir repo a GitHub (público).
2. share.streamlit.io → New app → repo, rama `main`, fichero `app.py`.
3. App settings → Secrets: `GOOGLE_API_KEY = "..."`
4. Deploy; URL pública tipo `https://<nombre>.streamlit.app`.
5. `adk web` queda como interfaz local para depurar el agente.

Plan B si Streamlit Cloud falla: Hugging Face Spaces (SDK Streamlit) o Render.
La demo siempre tenga app local + vídeo grabado.

## Guion demo (5 min)

1. 30s: personal abriendo `scan_0042.pdf` y tecleando fechas a mano.
2. 3.5 min: soltar 10 emails → pulsar Run → mostrar ficheros renombrados,
   carpeta review, filas del Excel, botones de descarga, URL pública.
3. 1 min: pregunta en vivo “Did you get my insurance?” → respuesta desde FAQ +
   datos del alumno; pregunta desconocida → escalado.

## Riesgos

- Rate limit Gemini: una llamada por adjunto, emails pequeños, un reintento.
- Scan borroso: Gemini lo lee; si baja confianza, a review sin bloquear el lote.
- Demo en vivo falla: salida pregenerada + vídeo, enseñar URL pública primero.
- Integración tarde: fase 3 empieza en H3 aunque los módulos estén verdes.

## Criterio de hecho (must-have)

- 10 emails procesados sin caerse
- ficheros renombrados con el patrón acordado
- `students.xlsx` con una fila por alumno y fechas clave
- respuesta FAQ en la UI
- dudosos visibles en review
- repo público + URL desplegada + texto de entrega guardado
