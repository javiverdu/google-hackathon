# Erasmus DocFlow

- Project made using Deepsek v4 flash (we didn't won)

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
| Model | Gemini (`gemini-3.5-flash`, automatic fallbacks if overloaded) |
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
python scripts/make_sample_data.py   # optional: 15 fake emails
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
    excel_writer.py         one row per student + Documents detail sheet
    faq.py                  FAQ lookup
    escalation.py           questions handed to a person
    web_download.py         download a document from an http(s) page
    state.py                export, restore and reset the demo data bundle
    signature.py            typed signature PNG stamped onto a PDF
    status_log.py           per-email New / Review / Processed status
scripts/make_sample_data.py 15 fake emails + PDFs/JPGs
scripts/check_inbox.py      validate a folder without calling Gemini
scripts/check_requirements.py  audit must-have requirements on generated data
tests/                      offline tests + optional live Gemini tests
data/inbox/                 input .eml files (samples committed)
data/out/                   renamed documents (gitignored)
data/review/                uncertain documents (gitignored)
data/students.xlsx          generated spreadsheet (gitignored)
docs/PLAN.md | docs/PLAN.es.md  team plan (English / Spanish)
docs/IMPLEMENTATION.md      architecture and data flow with Mermaid diagrams
docs/QA_CHECKLIST.md        web QA checklist for the deployed app
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

Streamlit Community Cloud redeploys on every push to the connected branch. If a
change does not show up, use **Manage app → Reboot app**. The filesystem is
ephemeral: `data/out`, `students.xlsx` and `escalations.csv` reset when the app
reboots or sleeps, so press **Run agent** once before the demo. The sample inbox
is committed, so there is always data to process.

Alternative hosts: Hugging Face Spaces (Streamlit SDK) or Render. `adk web` stays
local; the deployed app calls the same pipeline functions.

## Send emails to the web app

There is no mailbox address connected. The app reads `.eml` files, so you export
the messages from your mail client and upload them in **Inbox → Send emails to
the agent**.

- **Gmail:** open the message → ⋮ → **Show original** → **Download Original** (`.eml`).
  For several messages, use Google Takeout or save them one by one.
- **Outlook (Windows):** drag the message to the desktop, or **File → Save As → .eml**.
- **Apple Mail:** select the messages → **File → Save As → .eml**.
- **No .eml?** Use **Student form**: name, surname, email, semester, host
  university, document type, dates and a PDF/JPG. The form builds a real `.eml`
  and processes it immediately, exactly like an emailed document. If no file is
  attached, the message is treated as a question and answered from the FAQ.

Uploads are deduplicated by content, so pressing the button twice is safe. On
Streamlit Community Cloud the filesystem is ephemeral: uploaded emails and
generated files disappear when the app reboots or sleeps. The 15 sample emails
under `data/inbox/` are committed, so the demo always has data.

A real Gmail mailbox (IMAP with an app password) is not implemented.

## Review, signatures and the spreadsheet

- **Review tab:** every uncertain document waits here with a preview, the model
  guess and the reason it was flagged. Staff fix the fields and **Approve & save**
  (renamed, filed, row updated) or **Discard** it.
- **Signatures:** for a PDF in review, type a name or upload a signature image and
  stamp it bottom-left, bottom-center or bottom-right. Images cannot be signed.
- **Students tab:** an editable grid. Change any cell and press **Save changes**;
  `students.xlsx` is rewritten (the `Documents` detail sheet is kept).
- **Inbox status:** each email is grouped as New, Student questions, Needs review
  or Processed, using `data/processing_log.json`.

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
                          |
          Missing / Expired columns + Documents detail sheet
```

Unknown questions go to `data/escalations.csv` and appear in the UI under
Students → "Handed to a person".

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

125 offline tests, no key needed. They cover the ugly cases:

- empty, garbage and truncated `.eml` files
- HTML-only emails, missing subject/sender, unicode and missing filenames
- attachments with unsupported types, empty or oversized payloads
- low-confidence scans, missing student name, path-traversal filenames
- duplicate names, long names, disk errors, one broken email in a batch
- idempotent spreadsheet rows, missing-document recalculation
- expired documents (valid future date, invalid date, renewal clears the flag)
- escalations persisted to CSV with flattened questions
- web downloads: Content-Disposition names, MIME fallback, size limits, http-only
- FAQ retrieval and escalation for unknown questions
- Gemini fallback chain when the primary model is overloaded

Check the generated artifacts against the must-have list:

```bash
python scripts/check_requirements.py
```

Inspect a folder of emails without calling Gemini:

```bash
python scripts/check_inbox.py
```

Real-Gemini checks (classification, blurry scan, FAQ answer, escalation). Run
these before the demo and whenever prompts change:

```bash
RUN_LLM_TESTS=1 pytest tests/test_llm_integration.py -v
# Windows PowerShell: $env:RUN_LLM_TESTS=1; pytest tests/test_llm_integration.py -v
```

The integration tests are skipped by default, so CI and teammates without a
key stay green.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named google.adk` | Activate the venv, reinstall requirements |
| `GOOGLE_API_KEY missing` | `.env` in repo root, or Streamlit secrets |
| 429 from Gemini | Lower "Max emails per run", one retry is built in |
| 503 from Gemini | Model overloaded: fallback list in `.env` handles it, or change `GEMINI_MODEL` |
| Blurry scan rejected | Expected: it lands in `data/review/`, demo the human step |
| Windows activation blocked | `Set-ExecutionPolicy -Scope Process Bypass` |

## Nice-to-haves (implemented)

- Draft reply emails for staff approval (Inbox → expander → **Draft reply**)
- Flag missing and expired documents (`Missing` and `Expired` columns)
- Download documents from a web page with the same naming rules (Inbox → URL box)
- Public Streamlit deployment (see above); `adk web` for the ADK agent locally
- Save/restore the demo state as a `.zip` and reset generated files (sidebar → **Demo data**)
- Human review queue with approve/discard, PDF signature stamping and an editable student grid

Not implemented: real Gmail mailbox, login, persistent database.

## Demo data on Streamlit Cloud

The container filesystem is ephemeral. Before the demo:

1. Sidebar → **Demo data → Prepare state bundle** → **Download state (.zip)**.
2. After a reboot, upload the same bundle and press **Restore state**.
3. **Reset demo data** clears the spreadsheet, documents, review files and
   escalations but keeps the fifteen sample emails in `data/inbox/`.

The public URL has no login: every visitor shares the same files. Do not upload
real student data.
