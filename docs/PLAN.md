# Erasmus DocFlow — team plan (English)

Hackathon plan for 4 people in a shared repo. Hard deadline: submission 19:00,
live demo 19:10. Times below are relative (`H0` = start). Compress/expand to the
real clock, keep the ordering.

## Goal

Agent reads a folder of messy `.eml` emails, works out student + document type +
semester, saves files as `Surname_Name_DocType_2026-27.pdf`, fills one row per
student in `students.xlsx`, answers common questions from `faq.md`, escalates
anything uncertain to a human.

## Stack

- Python 3.11+ (Streamlit Cloud uses 3.12; tested locally on 3.14)
- Google ADK (`google-adk`) + Gemini API key from AI Studio
- `email` stdlib for `.eml`, `openpyxl` for `.xlsx`
- Streamlit UI, deployed to **Streamlit Community Cloud** (public URL, free)
- `adk web` for local agent debugging
- Git + GitHub public repo

## Repo contract (freeze at H1, do not change without telling the team)

- Document types: `LearningAgreement`, `Transcript`, `Insurance`,
  `CertificateOfArrival`, `Other`
- Structured fields: `student_first_name`, `student_surname`, `doc_type`,
  `semester`, `host_university`, `start_date`, `end_date`, `deadline`,
  `confidence`, `notes`
- Naming: `Surname_Name_DocType_YYYY-YY.ext` (`erasmus_agent/schemas.py`)
- Escalation: `confidence < 0.7`, `doc_type == Other`, or missing surname goes
  to `data/review/` and gets `status=needs_review` in the sheet
- Tool signatures live in `erasmus_agent/tools/` and `erasmus_agent/pipeline.py`

## Roles

| Person | Owns | Files |
|---|---|---|
| A — Agent/LLM | prompts, structured output, ADK agent, FAQ grounding | `llm.py`, `agent.py`, `faq.md` |
| B — Email/files | `.eml` parsing, attachments, naming, review folder | `tools/email_reader.py`, `tools/file_saver.py` |
| C — Data | spreadsheet rows, missing/expired flags, draft replies | `tools/excel_writer.py`, `pipeline.py` |
| D — UI/demo/repo | Streamlit UI, sample data, deploy, README, submission, slides | `app.py`, `scripts/`, `.github/` |

Everyone can touch shared files, but announce it in the group chat first.

## Timeline

| Phase | Slot | Work |
|---|---|---|
| 0. Setup | H0–H0:30 | Repo pushed, `.env` created per person, key works, contract frozen |
| 1. Skeleton | H0:30–H1 | Sample emails generated, each owner fills their module |
| 2. Parallel MVP | H1–H3 | B: read+save one email. C: write one xlsx row. A: classify one PDF with Gemini. D: UI shell + Streamlit deploy |
| 3. Integration | H3–H4:30 | `run_inbox()` end to end on 10 emails; uncertain docs to review |
| 4. Answers + extras | H4:30–H5:45 | FAQ chat, missing-document flags, draft reply, download buttons |
| 5. Freeze + demo | H5:45–H6:30 | No new features. README, deploy public URL, record backup video |
| 6. Submit | H6:30–H7 | Title, pitch, challenge, description, public repo link — before 19:00 |
| 7. Present | 19:10 | 30s problem, 3.5 min live demo, 1 min impact/roadmap |

Nice-to-haves only after phase 4: Gmail test mailbox, web document download.

## Git workflow

- `main` protected; short branches `feat/email-reader`, `fix/xlsx-dates`
- PR into `main`, one teammate reviews in 2 minutes; squash merge
- Commits: `feat:`, `fix:`, `chore:`, `docs:`
- D resolves conflicts and keeps `main` deployable at all times
- Never commit `.env`, `data/out`, `data/review`, `students.xlsx`

## Interface + deployment

Streamlit (`app.py`) because it is pretty, fast to build and one-click deploy.

1. Push repo to GitHub (public).
2. share.streamlit.io → New app → select repo, branch `main`, file `app.py`.
3. App settings → Secrets: `GOOGLE_API_KEY = "..."`
4. Deploy; public URL looks like `https://<name>.streamlit.app`.
5. Keep `adk web` as the local debugging interface for the agent.

Fallback if Streamlit Cloud misbehaves: Hugging Face Spaces (Streamlit SDK) or
Render. Demo always has the local Streamlit app plus a recorded video.

## Demo script (5 min)

1. 30s: staff manually opening `scan_0042.pdf` and typing dates into Excel.
2. 3.5 min: drop 10 messy emails → press Run → show renamed files, review
   folder, spreadsheet rows, download buttons, public URL.
3. 1 min: live question “Did you get my insurance?” → answer from FAQ + student
   data; unknown question → escalate.

## Risks

- Gemini rate limits: one call per attachment, small emails, retry once.
- Blurry scan: Gemini reads it; if confidence is low, review folder instead of
  blocking the batch.
- Live demo fails: pre-generated output + recorded video, show public URL first.
- Integration late: phase 3 starts at H3 even if the modules are imperfect.

## Definition of done (must-have)

- 10 emails processed without crashing
- files renamed with the agreed pattern
- `students.xlsx` with one row per student and key dates
- FAQ answer through the UI
- uncertain documents visibly sent to review
- public repo + deployed URL + submission text saved
