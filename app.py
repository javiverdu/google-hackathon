"""Streamlit front-end. Deployable to Streamlit Community Cloud (public URL)."""

from __future__ import annotations

import io
import os
import zipfile

import streamlit as st

from erasmus_agent import config, llm
from erasmus_agent.pipeline import run_inbox
from erasmus_agent.tools.email_reader import iter_inbox
from erasmus_agent.tools.excel_writer import read_students
from erasmus_agent.tools.faq import load_faq, search_faq

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
    st.caption(f"Data folder: `{config.DATA_DIR}`")
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        st.warning("No GOOGLE_API_KEY detected. Add it in .env or Streamlit secrets.")

inbox_tab, students_tab, ask_tab = st.tabs(["📥 Inbox", "📊 Students", "💬 Ask"])

with inbox_tab:
    emails = list(iter_inbox(config.INBOX_DIR))
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Emails in inbox", len(emails))
    col_b.metric("Documents saved", len(list(config.OUT_DIR.glob("*.*"))))
    col_c.metric("Needs a human", len(list(config.REVIEW_DIR.glob("*.*"))))

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
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No .eml files yet. Drop sample emails into `data/inbox/`.")

    if st.button("▶ Run agent on inbox", type="primary", use_container_width=True):
        with st.spinner("Reading emails, classifying documents, filling the spreadsheet..."):
            try:
                report = run_inbox(limit=int(limit), threshold=threshold)
                st.session_state["report"] = report
                st.success(
                    f"{report['emails']} emails · {report['saved']} documents saved · "
                    f"{report['review']} sent to review · {report['errors']} errors"
                )
            except Exception as exc:
                st.error(f"Run failed: {exc}")

    report = st.session_state.get("report")
    if report:
        for item in report["results"]:
            with st.expander(f"{item['email']} — {item['subject'] or 'no subject'}"):
                st.write("Saved:", ", ".join(item["saved"]) or "none")
                st.write("Review:", ", ".join(item["review"]) or "none")
                if item["errors"]:
                    st.warning("; ".join(item["errors"]))

with students_tab:
    rows = read_students(config.SPREADSHEET)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
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

    files = list(config.OUT_DIR.glob("*.*"))
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
                st.warning(answer)
            else:
                st.write(answer)
            with st.expander("FAQ context used"):
                st.text(search_faq(question, faq_text) or faq_text[:1500])
