# Erasmus DocFlow

Messy Erasmus inbox in. Renamed documents, a clean spreadsheet and FAQ answers out.

An agent for a university international office: it reads a folder of `.eml`
emails, identifies the student, document type and semester, saves each file as
`Surname_Name_DocType_2026-27.pdf`, adds one row per student to `students.xlsx`,
answers common questions from `faq.md`, and sends anything uncertain to
`data/review/` for a human.

## Stack

| Layer | Tool |
|---|---|
| Agent | Google ADK (`google-adk`) |
| Model | Gemini via AI Studio key |
| Emails | Python `email` stdlib |
| Spreadsheet | `openpyxl` |
| UI | Streamlit, deployable to Streamlit Community Cloud |
| Local agent UI | `adk web` |

## Quickstart (Windows and Linux)

Requires **Python 3.11+**. Tested locally on 3.14; Streamlit Community Cloud
uses 3.12, which is the recommended version for the team.

### Linux / macOS

```bash
git clone <your-repo-url> erasmus-agent
cd erasmus-agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then paste your AI Studio key
python scripts/make_sample_data.py   # optional: 10 fake emails
streamlit run app.py
```

### Windows (PowerShell)

```powershell
git clone <your-repo-url> erasmus-agent
cd erasmus-agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then paste your key
python scripts\make_sample_data.py
streamlit run app.py
```

Open http://localhost:8501. Everything uses `pathlib`, so no slash fixes needed
between Windows and Linux. Git line endings are normalised via `.gitattributes`.

Key: https://aistudio.google.com/apikey — put it in `.env` as
`GOOGLE_API_KEY=...`. Never commit `.env`.

## Repo layout

```
app.py                      Streamlit UI (deployed)
erasmus_agent/
  agent.py                  ADK agent (adk web)
  pipeline.py               inbox -> files -> spreadsheet
  llm.py                    Gemini classification + FAQ answers
  schemas.py                shared data contract (freeze this)
  config.py                 paths, env, key loading
  tools/
    email_reader.py         .eml parsing
    file_saver.py           rename + review folder
    excel_writer.py         one row per student
    faq.py                  FAQ lookup
scripts/make_sample_data.py 10 fake emails + PDFs/JPGs
data/inbox/                 input .eml files (samples committed)
data/out/                   renamed documents (gitignored)
data/review/                uncertain documents (gitignored)
data/students.xlsx          generated spreadsheet (gitignored)
docs/PLAN.md | docs/PLAN.es.md  team plan (English / Spanish)
faq.md                      demo FAQ
```

## Run the agent locally with ADK

```bash
adk web
```

Choose `erasmus_agent` in the dropdown. The agent exposes tools for listing and
processing the inbox, reading students, file naming and FAQ answers.

## Deploy the public UI (Streamlit Community Cloud)

1. Push this repo to a public GitHub repo.
2. Go to https://share.streamlit.io → **New app**.
3. Repo: your repo, branch `main`, main file `app.py`.
4. **Advanced settings → Secrets**:
   ```toml
   GOOGLE_API_KEY = "your-key"
   ```
5. Deploy. You get a public `https://<name>.streamlit.app` URL.

Alternative hosts: Hugging Face Spaces (Streamlit SDK) or Render. `adk web` stays
local; the deployed app calls the same pipeline functions.

## Data flow

```
.eml  ->  email_reader  ->  Gemini (structured output)
                                   |
                    confidence >= 0.7 and known type
                          /                     \
                    data/out/                data/review/
                 renamed file              original + reason
                          \                     /
                      students.xlsx (one row per student)
```

Uncertain cases: `confidence < 0.7`, `doc_type == Other`, or missing surname.
They never block the rest of the batch.

## Team workflow

- Read `docs/PLAN.md` (English) or `docs/PLAN.es.md` (Spanish).
- Contract in `erasmus_agent/schemas.py` is frozen after the first hour.
- Branches: `feat/...`, `fix/...`; PR into `main`, one quick review.
- Commits: `feat:`, `fix:`, `chore:`, `docs:`.
- CI runs ruff + pytest on Ubuntu and Windows.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

Tests never call Gemini, so they run without an API key.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named google.adk` | Activate the venv, reinstall requirements |
| `GOOGLE_API_KEY missing` | `.env` in repo root, or Streamlit secrets |
| 429 from Gemini | Lower "Max emails per run", one retry is built in |
| Blurry scan rejected | Expected: it lands in `data/review/`, demo the human step |
| Windows activation blocked | `Set-ExecutionPolicy -Scope Process Bypass` |

## Nice-to-haves (only after must-haves work)

- Draft reply emails for staff approval (`llm.draft_reply`)
- Flag expired documents using dates already extracted
- Download documents from a web page with the same naming tool
- Gmail test mailbox (`imaplib` + app password)
