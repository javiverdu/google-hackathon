"""Streamlit front-end. Deployable to Streamlit Community Cloud (public URL)."""

from __future__ import annotations

import io
import zipfile

import streamlit as st

from erasmus_agent import config, llm
from erasmus_agent.pipeline import process_email, process_url, run_inbox
from erasmus_agent.tools.email_reader import iter_inbox, read_email
from erasmus_agent.tools.escalation import log_escalation, read_escalations
from erasmus_agent.tools.excel_writer import read_students
from erasmus_agent.tools.faq import load_faq, search_faq
from erasmus_agent.tools.inbox_store import (
    compose_email,
    store_email_bytes,
    student_submission_email,
)

st.set_page_config(page_title="Erasmus DocFlow", page_icon="🎓", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      .hero {
        background: linear-gradient(120deg, #1f3c88 0%, #2e86ab 55%, #48c9b0 100%);
        border-radius: 18px; padding: 26px 30px; color: white; margin-bottom: 20px;
      }
      .hero h1 {margin: 0; font-size: 2rem;}
      .hero p {margin: 6px 0 0; opacity: .92;}
      div[data-testid="stMetric"] {
        background: #f7f9fc; border: 1px solid #e3e9f2; border-radius: 14px; padding: 12px 16px;
      }
      .pill {display:inline-block; background:#eef6ff; color:#1f3c88; border-radius:999px;
             padding:2px 10px; margin:2px; font-size:.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Erasmus DocFlow</h1>
      <p>Messy inbox in. Renamed documents, clean spreadsheet and ready replies out.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Settings")
    threshold = st.slider("Confidence threshold", 0.0, 1.0, config.CONFIDENCE_THRESHOLD, 0.05)
    limit = st.number_input("Max emails per run", 1, 50, 10)
    st.caption(f"Model: `{config.GEMINI_MODEL}`")
    st.caption("Fallbacks: " + ", ".join(f"`{m}`" for m in config.GEMINI_FALLBACK_MODELS))
    st.caption(f"Data folder: `{config.DATA_DIR}`")
    if config.has_api_key():
        st.caption("Gemini key loaded")
    else:
        st.warning(
            'No GOOGLE_API_KEY detected. Add GOOGLE_API_KEY = "..." to Streamlit secrets, '
            "or to .env for local runs."
        )
def _visible_files(folder) -> list:
    """Real documents only: no .gitkeep, no review reason sidecars."""
    if not folder.exists():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".reason.txt")
    ]


inbox_tab, form_tab, students_tab, ask_tab = st.tabs(
    ["📥 Inbox", "📨 Student form", "📊 Students", "💬 Ask"]
)

with inbox_tab:
    with st.expander("📤 Send emails to the agent", expanded=True):
        st.caption(
            "Upload one or more `.eml` files. Gmail: open the message → ⋮ → **Show original** → "
            "**Download Original**. Outlook: drag the message to the desktop. "
            "Apple Mail: **Save As** → `.eml`."
        )
        uploads = st.file_uploader(
            "Drop .eml files here",
            type=["eml"],
            accept_multiple_files=True,
            key="eml_uploader",
        )
        if uploads:
            added: list[str] = []
            duplicates: list[str] = []
            too_big: list[str] = []
            for upload in uploads:
                data = upload.getvalue()
                if len(data) > 20 * 1024 * 1024:
                    too_big.append(upload.name)
                    continue
                name, created = store_email_bytes(upload.name, data, config.INBOX_DIR)
                (added if created else duplicates).append(name)
            if added:
                st.success(f"Added {len(added)} email(s): {', '.join(added)}. Press Run below.")
            if duplicates:
                st.caption(f"Already in inbox: {', '.join(duplicates)}")
            if too_big:
                st.warning(f"Too large (max 20 MB): {', '.join(too_big)}")

    with st.expander("✍ Or write a test email"):
        with st.form("compose_email"):
            subject = st.text_input("Subject", "My Learning Agreement")
            sender = st.text_input("From", "student@example.com")
            body = st.text_area("Body", "Hello, attached is my document.")
            files = st.file_uploader(
                "Attachments (PDF, JPG, PNG)",
                type=["pdf", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="compose_files",
            )
            submitted = st.form_submit_button("Add to inbox")

        if submitted:
            attachments = []
            oversized = []
            for file in files or []:
                if file.size > 15 * 1024 * 1024:
                    oversized.append(file.name)
                    continue
                attachments.append(
                    {
                        "filename": file.name,
                        "data": file.getvalue(),
                        "content_type": file.type,
                    }
                )
            data = compose_email(subject, sender, body, attachments)
            filename, created = store_email_bytes(
                f"web_{subject.lower().replace(' ', '_')}.eml", data, config.INBOX_DIR
            )
            if created:
                st.success(f"Email added as {filename}. Press Run below.")
            else:
                st.caption(f"Identical email already in inbox as {filename}.")
            if oversized:
                st.warning(f"Attachments over 15 MB were skipped: {', '.join(oversized)}")

    emails = list(iter_inbox(config.INBOX_DIR))
    saved_files = _visible_files(config.OUT_DIR)
    review_files = _visible_files(config.REVIEW_DIR)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Emails in inbox", len(emails))
    col_b.metric("Documents saved", len(saved_files))
    col_c.metric("Needs a human", len(review_files))

    if emails:
        st.dataframe(
            [
                {
                    "Email": meta["filename"],
                    "Subject": meta["subject"],
                    "From": meta["sender"],
                    "Attachments": len(meta["attachments"]),
                }
                for meta in emails
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No .eml files yet. Drop sample emails into `data/inbox/`.")

    if st.button("▶ Run agent on inbox", type="primary", width="stretch"):
        with st.spinner("Reading emails, classifying documents, filling the spreadsheet..."):
            try:
                report = run_inbox(limit=int(limit), threshold=threshold)
                st.session_state["report"] = report
                st.success(
                    f"{report['emails']} emails · {report['saved']} documents saved · "
                    f"{report['review']} sent to review · {report['errors']} errors · "
                    f"{report['skipped']} without attachments"
                )
            except Exception as exc:
                st.error(f"Run failed: {exc}")

    report = st.session_state.get("report")
    if report:
        for item in report["results"]:
            with st.expander(f"{item['email']} — {item['subject'] or 'no subject'}"):
                st.write("Saved:", ", ".join(item["saved"]) or "none")
                st.write("Review:", ", ".join(item["review"]) or "none")
                if item.get("documents"):
                    st.dataframe(item["documents"], width="stretch", hide_index=True)
                if item["skipped"]:
                    st.info("; ".join(item["skipped"]))
                if item["errors"]:
                    st.warning("; ".join(item["errors"]))

                saved = [doc for doc in item.get("documents", []) if doc["status"] == "saved"]
                if saved:
                    key = f"draft_{item['email']}"
                    if st.button("✉ Draft reply for staff review", key=f"btn_{item['email']}"):
                        summary = "Documents received: " + ", ".join(
                            f"{doc['doc_type']} ({doc['filename']})" for doc in saved
                        )
                        try:
                            st.session_state[key] = llm.draft_reply(
                                saved[0]["student"], item["subject"], summary, load_faq()
                            )
                        except Exception as exc:
                            st.warning(f"Draft failed: {exc}")
                    draft = st.session_state.get(key)
                    if draft:
                        st.text_area("Draft — staff checks and sends", draft, height=180, key=f"area_{key}")
                        st.download_button(
                            "⬇ Download draft (.txt)",
                            data=draft.encode("utf-8"),
                            file_name=f"reply_{item['email']}.txt",
                            mime="text/plain",
                            key=f"dl_{key}",
                        )

    with st.expander("🌐 Download a document from a web page"):
        url = st.text_input("Document URL (http/https)", key="web_url")
        if st.button("Download and file", key="web_button") and url:
            with st.spinner("Downloading and classifying..."):
                try:
                    result = process_url(url, threshold=threshold)
                    st.session_state["report"] = {
                        "emails": 1,
                        "saved": len(result["saved"]),
                        "review": len(result["review"]),
                        "errors": len(result["errors"]),
                        "skipped": len(result["skipped"]),
                        "results": [result],
                    }
                    st.success(
                        f"Saved: {', '.join(result['saved']) or 'none'} · "
                        f"review: {len(result['review'])}"
                    )
                except Exception as exc:
                    st.error(f"Download failed: {exc}")

with form_tab:
    st.subheader("Student document submission")
    st.caption(
        "Same as a student emailing the office: the form generates a normal `.eml` "
        "and the agent processes it immediately."
    )
    with st.form("student_submission"):
        col1, col2 = st.columns(2)
        first = col1.text_input("First name", key="sf_first")
        surname = col2.text_input("Surname", key="sf_surname")
        email_addr = col1.text_input("Email", "student@example.com", key="sf_email")
        semester = col2.selectbox("Semester", ["2026-27", "2027-28"], key="sf_semester")
        host = st.text_input("Host university", key="sf_host")
        doc_type = st.selectbox(
            "Document type",
            ["LearningAgreement", "Transcript", "Insurance", "CertificateOfArrival", "Other"],
            key="sf_doc_type",
        )
        date1, date2, date3 = st.columns(3)
        start = date1.date_input("Stay start", value=None, key="sf_start")
        end = date2.date_input("Stay end", value=None, key="sf_end")
        deadline = date3.date_input("Deadline", value=None, key="sf_deadline")
        message = st.text_area("Message (optional)", key="sf_message")
        submission = st.file_uploader(
            "Document (PDF, JPG, PNG)",
            type=["pdf", "jpg", "jpeg", "png"],
            key="sf_file",
        )
        sent = st.form_submit_button("Send to agent", type="primary")

    if sent:
        if not first.strip() or not surname.strip():
            st.error("First name and surname are required.")
        elif submission is None and not message.strip():
            st.error("Attach a document or write a question.")
        elif submission is not None and submission.size > 15 * 1024 * 1024:
            st.error("Document too large (max 15 MB).")
        else:
            attachment = (
                {
                    "filename": submission.name,
                    "data": submission.getvalue(),
                    "content_type": submission.type,
                }
                if submission is not None
                else None
            )
            data = student_submission_email(
                first_name=first.strip(),
                surname=surname.strip(),
                email=email_addr.strip(),
                semester=semester,
                host_university=host.strip(),
                doc_type=doc_type,
                start_date=start.isoformat() if start else "",
                end_date=end.isoformat() if end else "",
                deadline=deadline.isoformat() if deadline else "",
                message=message.strip(),
                attachment=attachment,
            )
            filename, _ = store_email_bytes(
                f"form_{first}_{surname}.eml", data, config.INBOX_DIR
            )
            meta = read_email(config.INBOX_DIR / filename)

            if meta["attachments"]:
                with st.spinner("Classifying the document and updating the spreadsheet..."):
                    result = process_email(meta, threshold=threshold)
                if result["saved"]:
                    st.success(f"Saved as {', '.join(result['saved'])}")
                else:
                    st.warning(
                        "Sent to review, a staff member will check it. "
                        + "; ".join(result["review"] + result["errors"])
                    )
            else:
                context = "\n".join(str(row) for row in read_students(config.SPREADSHEET))
                with st.spinner("Answering from the FAQ..."):
                    try:
                        answer = llm.answer_question(message, load_faq(), context)
                    except Exception as exc:
                        answer = f"ESCALATE: model unavailable ({exc})"
                if answer.startswith("ESCALATE"):
                    reason = answer.removeprefix("ESCALATE:").strip()
                    log_escalation(message, reason, student=f"{first} {surname}")
                    st.warning("Question handed to a staff member.")
                else:
                    st.success(answer)
            st.caption(f"Stored as `{filename}`. Staff can see it in the Inbox tab.")

with students_tab:
    rows = read_students(config.SPREADSHEET)
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        buffer = io.BytesIO()
        buffer.write(config.SPREADSHEET.read_bytes())
        st.download_button(
            "⬇ Download students.xlsx",
            data=buffer.getvalue(),
            file_name="students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Spreadsheet empty. Run the agent first.")

    escalations = read_escalations()
    if escalations:
        st.subheader("Handed to a person")
        st.dataframe(escalations, width="stretch", hide_index=True)
        st.download_button(
            "⬇ Download escalations.csv",
            data=config.ESCALATIONS.read_bytes(),
            file_name="escalations.csv",
            mime="text/csv",
        )

    files = _visible_files(config.OUT_DIR)
    if files:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in files:
                bundle.write(path, arcname=path.name)
        st.download_button(
            "⬇ Download renamed documents (.zip)",
            data=archive.getvalue(),
            file_name="erasmus_documents.zip",
            mime="application/zip",
        )

with ask_tab:
    st.caption("Answers come only from faq.md and the current student table. Unknown = escalate.")
    question = st.chat_input("Ask about deadlines, signatures, insurance...")
    if question:
        faq_text = load_faq()
        context = "\n".join(str(row) for row in read_students(config.SPREADSHEET))
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            try:
                answer = llm.answer_question(question, faq_text, context)
            except Exception as exc:
                answer = f"ESCALATE: model unavailable ({exc})"
            if answer.startswith("ESCALATE"):
                reason = answer.removeprefix("ESCALATE:").strip() or "not covered by the FAQ"
                log_escalation(question, reason)
                st.warning(answer)
                st.info("Handed to a staff member. It now appears under Students → Handed to a person.")
            else:
                st.write(answer)
            with st.expander("FAQ context used"):
                st.text(search_faq(question, faq_text) or faq_text[:1500])
