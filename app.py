"""Streamlit front-end. Deployable to Streamlit Community Cloud (public URL)."""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import streamlit as st

from erasmus_agent import config, llm
from erasmus_agent.pipeline import process_email, process_url, run_inbox
from erasmus_agent.schemas import DocType, DocumentInfo
from erasmus_agent.tools.email_reader import iter_inbox, read_email
from erasmus_agent.tools.escalation import log_escalation, read_escalations
from erasmus_agent.tools.excel_writer import read_students, upsert_student, write_students
from erasmus_agent.tools.faq import load_faq, search_faq
from erasmus_agent.tools.file_saver import (
    approve_review_item,
    discard_review_item,
    list_review_items,
    read_review_sidecar,
)
from erasmus_agent.tools.inbox_store import compose_email, store_email_bytes, student_submission_email
from erasmus_agent.tools.signature import render_typed_signature, stamp_signature_on_pdf
from erasmus_agent.tools.state import export_state, reset_demo_data, restore_state, state_summary
from erasmus_agent.tools.status_log import read_log, resolve_review_item, status_for
from erasmus_agent.tools.web_download import DownloadError

st.set_page_config(page_title="Erasmus DocFlow", page_icon="🎓", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Roboto+Slab:wght@400;700;900&display=swap');

      :root {
        --cream: #faf5e8;
        --white: #ffffff;
        --frost: #f8fafc;
        --onyx: #181d26;
        --charcoal: #333840;
        --graphite: #525965;
        --steel: #9297a0;
        --border: #e0e2e6;
        --indigo: #040e20;
        --cobalt: #1b61c9;
        --sapphire: #254fad;
        --terracotta: #aa2d00;
        --forest: #0a2e0e;
        --moss: #214224;
        --peach: #fcab79;
        --pink: #fa91e0;
        --marigold: #fcb42a;
        --sky: #c7e5f2;
        --shadow-subtle: rgba(0,0,0,.32) 0 0 1px 0, rgba(0,0,0,.08) 0 0 2px 0,
          rgba(45,127,249,.28) 0 1px 3px 0, rgba(0,0,0,.06) 0 0 0 .5px inset;
        --shadow-lg: rgba(15,48,106,.05) 0 0 20px 0;
      }

      html, body, .stApp { background: var(--cream); }
      [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--cream); }
      [data-testid="stHeader"] { background: transparent; }
      .block-container {padding-top: 2.5rem; padding-bottom: 4rem; max-width: 1200px;}

      .stApp, .stApp p, .stApp li, .stApp label, .stApp span,
      [data-testid="stMarkdownContainer"] {
        font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
        color: var(--charcoal);
      }
      .stApp p {line-height: 1.5;}

      h1, h2, h3, h4, h5,
      [data-testid="stMarkdownContainer"] h1,
      [data-testid="stMarkdownContainer"] h2,
      [data-testid="stMarkdownContainer"] h3 {
        font-family: 'Roboto Slab', 'GT Sectra Display', Tiempos, Georgia, serif;
        color: var(--indigo);
        letter-spacing: 0;
      }
      h1 {font-weight: 900; font-size: 3rem; line-height: 1.1;}
      h2 {font-weight: 900; font-size: 2rem; line-height: 1.2;}
      h3 {font-weight: 700; font-size: 1.4rem; line-height: 1.25;}

      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        color: var(--graphite);
        font-size: .875rem;
      }

      /* Hero: warm editorial block, no gradient, display slab type */
      .hero {
        background: var(--cream);
        border-bottom: 1px solid var(--border);
        padding: 8px 0 32px;
        margin-bottom: 32px;
      }
      .hero .eyebrow {
        display: inline-block;
        background: var(--marigold);
        color: var(--onyx);
        border-radius: 32px;
        padding: 4px 14px;
        font-size: .75rem;
        font-weight: 600;
        letter-spacing: .08em;
        text-transform: uppercase;
        margin-bottom: 16px;
      }
      .hero h1 {
        font-family: 'Roboto Slab', Georgia, serif;
        font-weight: 900;
        font-size: 3rem;
        line-height: 1.1;
        color: var(--indigo);
        margin: 0 0 12px;
      }
      .hero p {
        color: var(--charcoal);
        font-size: 1.125rem;
        line-height: 1.4;
        max-width: 720px;
        margin: 0 0 20px;
      }
      .hero .chips {display: flex; flex-wrap: wrap; gap: 8px;}
      .chip {
        display: inline-block;
        border-radius: 32px;
        padding: 4px 14px;
        font-size: .8125rem;
        font-weight: 500;
        color: var(--onyx);
      }
      .chip-sapphire {background: var(--sky);}
      .chip-forest {background: #d8e6d9; color: var(--moss);}
      .chip-terracotta {background: #f6d9cd; color: var(--terracotta);}
      .chip-marigold {background: var(--marigold); color: var(--onyx);}

      /* Sidebar: clean white panel */
      [data-testid="stSidebar"] {
        background: var(--white);
        border-right: 1px solid var(--border);
      }
      [data-testid="stSidebar"] > div:first-child {padding-top: 1.5rem;}
      [data-testid="stSidebar"] h2 {font-size: 1.5rem;}

      /* Buttons: onyx primary, ghost secondary, 12px radius */
      .stButton > button, .stDownloadButton > button,
      [data-testid="stFormSubmitButton"] > button {
        border-radius: 12px;
        font-weight: 600;
        font-size: .9375rem;
        padding: .55rem 1.25rem;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
      }
      .stButton > button[kind="primary"],
      [data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: var(--onyx);
        color: var(--white);
        border: 1px solid var(--onyx);
        box-shadow: var(--shadow-subtle);
      }
      .stButton > button[kind="primary"]:hover,
      [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
        background: var(--charcoal);
        border-color: var(--charcoal);
        color: var(--white);
      }
      .stButton > button[kind="secondary"],
      .stDownloadButton > button,
      [data-testid="stFormSubmitButton"] > button[kind="secondary"] {
        background: var(--white);
        color: var(--onyx);
        border: 1px solid var(--onyx);
        box-shadow: none;
      }
      .stButton > button[kind="secondary"]:hover,
      .stDownloadButton > button:hover,
      [data-testid="stFormSubmitButton"] > button[kind="secondary"]:hover {
        background: var(--frost);
        color: var(--onyx);
        border-color: var(--onyx);
      }
      .stButton > button:disabled {opacity: .45;}

      /* Tabs as a rounded editorial nav bar */
      [data-baseweb="tab-list"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 6px;
        gap: 4px;
        box-shadow: var(--shadow-lg);
      }
      [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 8px 16px;
        font-weight: 500;
        color: var(--graphite);
        background: transparent;
      }
      [data-baseweb="tab"]:hover {background: var(--frost); color: var(--onyx);}
      [aria-selected="true"][data-baseweb="tab"] {
        background: var(--onyx) !important;
        color: var(--white) !important;
      }
      [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display: none;}

      /* Metrics: white cards with a colour-coded top edge */
      div[data-testid="stMetric"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: var(--shadow-lg);
      }
      div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="stMetric"] {
        border-top: 4px solid var(--sapphire);
      }
      div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stMetric"] {
        border-top: 4px solid var(--moss);
      }
      div[data-testid="stHorizontalBlock"] > div:nth-child(3) div[data-testid="stMetric"] {
        border-top: 4px solid var(--terracotta);
      }
      div[data-testid="stHorizontalBlock"] > div:nth-child(4) div[data-testid="stMetric"] {
        border-top: 4px solid var(--marigold);
      }
      div[data-testid="stMetricLabel"] p {
        color: var(--graphite);
        font-weight: 500;
        font-size: .875rem;
      }
      div[data-testid="stMetricValue"] {
        font-family: 'Roboto Slab', Georgia, serif;
        color: var(--indigo);
      }

      /* Cards, expanders, forms */
      [data-testid="stExpander"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        box-shadow: var(--shadow-lg);
        overflow: hidden;
      }
      [data-testid="stExpander"] summary {
        font-weight: 600;
        color: var(--onyx);
      }
      [data-testid="stExpander"] summary:hover {color: var(--cobalt);}
      [data-testid="stForm"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: var(--shadow-lg);
      }

      /* Inputs */
      [data-testid="stTextInput"] input,
      [data-testid="stNumberInput"] input,
      [data-testid="stTextArea"] textarea,
      [data-testid="stDateInput"] input,
      [data-baseweb="select"] > div {
        background: var(--white) !important;
        border-radius: 12px !important;
        border-color: var(--border) !important;
        color: var(--charcoal) !important;
      }
      [data-testid="stTextInput"] input:focus,
      [data-testid="stTextArea"] textarea:focus {
        border-color: var(--cobalt) !important;
        box-shadow: 0 0 0 3px rgba(27, 97, 201, .12) !important;
      }
      [data-testid="stFileUploaderDropzone"] {
        background: var(--frost);
        border: 1px dashed var(--steel);
        border-radius: 16px;
      }
      [data-testid="stFileUploaderDropzone"]:hover {
        background: var(--white);
        border-color: var(--onyx);
      }

      /* Alerts: paper cards with a colour spine */
      [data-testid="stAlert"] {
        border-radius: 16px;
        border: 1px solid var(--border);
        background: var(--white);
        box-shadow: var(--shadow-lg);
      }

      /* Tables and chat */
      [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 4px;
        box-shadow: var(--shadow-lg);
      }
      [data-testid="stChatInput"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 32px;
      }
      [data-testid="stChatMessage"] {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 12px 16px;
      }

      hr, [data-testid="stDivider"] {border-color: var(--border);}
      a {color: var(--cobalt);}
      code {background: var(--frost); border-radius: 6px; padding: 1px 5px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <span class="eyebrow">Erasmus office agent</span>
      <h1>Erasmus DocFlow</h1>
      <p>Messy inbox in. Renamed documents, a clean spreadsheet and ready replies out.</p>
      <div class="chips">
        <span class="chip chip-sapphire">Classify</span>
        <span class="chip chip-forest">Rename &amp; file</span>
        <span class="chip chip-terracotta">Human review</span>
        <span class="chip chip-marigold">FAQ &amp; drafts</span>
      </div>
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

    st.divider()
    st.caption(
        "**Public demo.** No login: everyone who opens this URL shares the same "
        "files and spreadsheet. Do not upload real student data."
    )
    summary = state_summary()
    st.caption(
        f"Generated files: {summary['documents']} documents · "
        f"{summary['review']} in review · spreadsheet "
        f"{'ready' if summary['spreadsheet'] else 'empty'}."
    )
    with st.expander("💾 Demo data: save, restore, reset"):
        st.caption(
            "Streamlit Cloud deletes generated files when the app sleeps. "
            "Save the bundle before the demo and restore it after a reboot."
        )
        if st.button("📦 Prepare state bundle", key="prepare_state"):
            st.session_state["state_bundle"] = export_state()
        bundle = st.session_state.get("state_bundle")
        if bundle:
            st.download_button(
                "⬇ Download state (.zip)",
                data=bundle,
                file_name="erasmus_state.zip",
                mime="application/zip",
                key="download_state",
            )
            st.caption(f"{len(bundle) / 1024:.0f} KB. Prepare again after a new run.")

        restore_upload = st.file_uploader(
            "Restore a state bundle", type=["zip"], key="state_upload"
        )
        if restore_upload is not None and st.button("Restore state", key="restore_state"):
            try:
                restored = restore_state(restore_upload.getvalue())
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop("report", None)
                st.session_state.pop("state_bundle", None)
                st.session_state["state_flash"] = f"Restored {restored['files']} files."
                st.rerun()

        st.divider()
        confirm_reset = st.checkbox(
            "I understand this deletes the spreadsheet, documents, review files "
            "and escalations (inbox is kept).",
            key="reset_confirm",
        )
        if st.button(
            "Reset demo data",
            key="reset_button",
            disabled=not confirm_reset,
        ):
            removed = reset_demo_data()
            st.session_state.pop("report", None)
            st.session_state.pop("state_bundle", None)
            st.session_state["state_flash"] = f"Removed {removed['removed']} files. Inbox kept."
            st.rerun()

    flash = st.session_state.pop("state_flash", None)
    if flash:
        st.success(flash)


def _visible_files(folder) -> list:
    """Real documents only: no dotfiles, no review sidecars."""
    if not folder.exists():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and not path.name.endswith(".reason.txt")
        and path.suffix != ".json"
    ]


def render_attachment_preview(name: str, data: bytes) -> None:
    """Reusable inline preview for a PDF/image, used by Inbox and Review tabs."""
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        b64 = base64.b64encode(data).decode()
        st.markdown(
            f'<embed src="data:application/pdf;base64,{b64}" '
            'width="100%" height="500" type="application/pdf">',
            unsafe_allow_html=True,
        )
    elif suffix in (".jpg", ".jpeg", ".png", ".webp"):
        st.image(data, width="stretch")
    else:
        st.info(f"No preview available for {suffix or 'this'} files.")
        st.download_button("⬇ Download to view", data=data, file_name=name, key=f"dl_{name}")


STATUS_LABELS = {
    "needs_review": "⚠️ Needs review",
    "question": "❓ Student questions",
    "new": "🆕 New / not processed yet",
    "processed": "✅ Processed",
}

inbox_tab, review_tab, form_tab, students_tab, ask_tab = st.tabs(
    ["📥 Inbox", "🔍 Review", "📨 Student form", "📊 Students", "💬 Ask"]
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
    review_items = list_review_items(config.REVIEW_DIR)
    log = read_log()
    students = read_students(config.SPREADSHEET)
    flagged = sum(
        1 for row in students if str(row.get("Status", "")).strip() == "needs_review"
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Emails in inbox", len(emails))
    col_b.metric("Documents saved", len(_visible_files(config.OUT_DIR)))
    col_c.metric("Documents in review", len(review_items))
    col_d.metric("Students flagged", flagged)
    if review_items:
        st.caption(
            "Review counts files, not students: the spreadsheet keeps one row per "
            "student, so several review files can belong to the same person."
        )

    if st.button("▶ Run agent on inbox", type="primary", width="stretch"):
        with st.spinner("Reading emails, classifying documents, filling the spreadsheet..."):
            try:
                report = run_inbox(limit=int(limit), threshold=threshold)
                st.success(
                    f"{report['emails']} emails · {report['saved']} documents saved · "
                    f"{report['review']} sent to review · {report['errors']} errors · "
                    f"{report['skipped']} without attachments"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Run failed: {exc}")

    if not emails:
        st.info("No .eml files yet. Drop sample emails into `data/inbox/`.")
    else:
        groups: dict[str, list[dict]] = {key: [] for key in STATUS_LABELS}
        for meta in emails:
            entry = log.get(meta["filename"])
            status = status_for(entry, has_attachments=bool(meta["attachments"]))
            groups[status].append({"meta": meta, "entry": entry})

        for status, label in STATUS_LABELS.items():
            items = groups[status]
            if not items:
                continue
            st.subheader(f"{label} ({len(items)})")
            for item in items:
                meta, entry = item["meta"], item["entry"]
                header = f"{meta['subject'] or '(no subject)'} — {meta['sender']}"
                with st.expander(header):
                    st.write(meta["body"] or "_(no text in the email)_")

                    if entry and entry.get("errors"):
                        for err in entry["errors"]:
                            st.warning(err)

                    if not meta["attachments"]:
                        st.caption("No attachments on this email.")
                    for attachment in meta["attachments"]:
                        att_name = attachment.get("name", "document")
                        tag = ""
                        if entry:
                            if att_name in (entry.get("review") or []):
                                tag = " · ⚠️ needs review"
                            elif any(att_name.split(".")[0] in s for s in entry.get("saved") or []):
                                tag = " · ✅ saved"
                        with st.expander(f"📎 {att_name}{tag}"):
                            render_attachment_preview(att_name, attachment["data"])
                            if tag.endswith("needs review"):
                                st.caption("Fix this in the 🔍 Review tab to approve or discard it.")

                    saved_docs = (
                        [doc for doc in entry.get("documents", []) if doc.get("status") == "saved"]
                        if entry
                        else []
                    )
                    if saved_docs:
                        draft_key = f"draft_{meta['filename']}"
                        if st.button("✉ Draft reply for staff review", key=f"btn_{meta['filename']}"):
                            doc_summary = "Documents received: " + ", ".join(
                                f"{doc['doc_type']} ({doc['filename']})" for doc in saved_docs
                            )
                            try:
                                st.session_state[draft_key] = llm.draft_reply(
                                    saved_docs[0]["student"], meta["subject"], doc_summary, load_faq()
                                )
                            except Exception as exc:
                                st.warning(f"Draft failed: {exc}")
                        draft = st.session_state.get(draft_key)
                        if draft:
                            st.text_area(
                                "Draft — staff checks and sends", draft, height=180, key=f"area_{draft_key}"
                            )
                            st.download_button(
                                "⬇ Download draft (.txt)",
                                data=draft.encode("utf-8"),
                                file_name=f"reply_{meta['filename']}.txt",
                                mime="text/plain",
                                key=f"dl_{draft_key}",
                            )

    with st.expander("🌐 Download a document from a web page (optional)"):
        st.caption(
            "Only direct links to a file work: the URL must end in `.pdf`, `.jpg`, `.png` or "
            "similar, or return the file itself. Login pages, Google Drive folders, Moodle "
            "links and pages where you must click a button are **not** supported. "
            "Prefer the Student form or upload the `.eml` instead."
        )
        url = st.text_input(
            "Direct file URL (http/https)",
            key="web_url",
            placeholder="https://example.edu/files/learning_agreement.pdf",
        )
        if st.button("Download and file", key="web_button") and url:
            with st.spinner("Downloading and classifying..."):
                try:
                    result = process_url(url, threshold=threshold)
                    st.success(
                        f"Saved: {', '.join(result['saved']) or 'none'} · "
                        f"review: {len(result['review'])}"
                    )
                    st.rerun()
                except DownloadError as exc:
                    if exc.kind in {"html", "scheme", "not_found", "auth"}:
                        st.warning(str(exc))
                    else:
                        st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - last resort, keep the UI alive
                    st.error(f"Download failed: {exc}")

with review_tab:
    st.caption(
        "Documents the agent was not sure about. Check the preview, fix the fields, "
        "then approve — it gets renamed, filed and added to the spreadsheet."
    )
    items = list_review_items(config.REVIEW_DIR)

    if not items:
        st.success("Nothing waiting for review. 🎉")
    else:
        names = [path.name for path in items]
        choice = st.selectbox(f"{len(items)} document(s) need a human", names)
        selected = items[names.index(choice)]
        sidecar = read_review_sidecar(selected)
        extracted = sidecar.get("extracted") or {}

        preview_col, form_col = st.columns([3, 2])

        with preview_col:
            if sidecar.get("reason"):
                st.warning(f"Why it was flagged: {sidecar['reason']}")
            if sidecar.get("source_email"):
                st.caption(f"From email: {sidecar['source_email']}")

            render_attachment_preview(selected.name, selected.read_bytes())

            if selected.suffix.lower() == ".pdf":
                with st.expander("✍️ Add a signature"):
                    position = st.selectbox(
                        "Position on the page",
                        ["Bottom-right", "Bottom-left", "Bottom-center"],
                        key=f"sig_pos_{selected.name}",
                    )
                    mode = st.radio(
                        "Signature source",
                        ["Type a name", "Upload an image"],
                        horizontal=True,
                        key=f"sig_mode_{selected.name}",
                    )

                    signature_png = None
                    if mode == "Type a name":
                        typed = st.text_input(
                            "Full name to render as a signature",
                            value=(
                                f"{extracted.get('student_first_name', '')} "
                                f"{extracted.get('student_surname', '')}"
                            ).strip(),
                            key=f"sig_name_{selected.name}",
                        )
                        if typed.strip():
                            signature_png = render_typed_signature(typed)
                            st.image(signature_png, caption="Preview")
                    else:
                        uploaded = st.file_uploader(
                            "Signature image (PNG with transparent background works best)",
                            type=["png", "jpg", "jpeg"],
                            key=f"sig_upload_{selected.name}",
                        )
                        if uploaded is not None:
                            signature_png = uploaded.getvalue()
                            st.image(signature_png, caption="Preview")

                    if st.button(
                        "Stamp signature onto this document",
                        disabled=signature_png is None,
                        key=f"sig_stamp_{selected.name}",
                    ):
                        signed_bytes = stamp_signature_on_pdf(
                            selected.read_bytes(),
                            signature_png,
                            position=position.lower().replace(" ", "-"),
                        )
                        selected.write_bytes(signed_bytes)
                        st.success("Signed. The preview above now shows the signed copy.")
                        st.rerun()

        with form_col:
            with st.form(key=f"review_form_{selected.name}"):
                first_name = st.text_input("First name", extracted.get("student_first_name", ""))
                surname = st.text_input("Surname", extracted.get("student_surname", ""))
                doc_type = st.selectbox(
                    "Document type",
                    [d.value for d in DocType],
                    index=[d.value for d in DocType].index(
                        extracted.get("doc_type", DocType.other.value)
                    )
                    if extracted.get("doc_type") in [d.value for d in DocType]
                    else len(DocType) - 1,
                )
                semester = st.text_input("Semester", extracted.get("semester", config.SEMESTER))
                host_university = st.text_input("Host university", extracted.get("host_university", ""))
                start_date = st.text_input("Start date (YYYY-MM-DD)", extracted.get("start_date", ""))
                end_date = st.text_input("End date (YYYY-MM-DD)", extracted.get("end_date", ""))
                deadline = st.text_input("Deadline (YYYY-MM-DD)", extracted.get("deadline", ""))

                approve = st.form_submit_button("✅ Approve & save", type="primary", width="stretch")
                discard = st.form_submit_button("🗑 Discard (not a real document)", width="stretch")

            if approve:
                if not surname.strip():
                    st.error("Surname is required before approving.")
                else:
                    info = DocumentInfo(
                        student_first_name=first_name.strip(),
                        student_surname=surname.strip(),
                        doc_type=DocType(doc_type),
                        semester=semester.strip(),
                        host_university=host_university.strip(),
                        start_date=start_date.strip(),
                        end_date=end_date.strip(),
                        deadline=deadline.strip(),
                        confidence=1.0,
                        notes="Confirmed by staff",
                    )
                    target = approve_review_item(selected, info, config.OUT_DIR)
                    upsert_student(
                        config.SPREADSHEET,
                        info,
                        saved_filename=target.name,
                        status="ok",
                        force_status=True,
                    )
                    if sidecar.get("source_email"):
                        resolve_review_item(sidecar["source_email"], selected.name, target.name)
                    st.success(f"Saved as {target.name} and added to students.xlsx")
                    st.rerun()

            if discard:
                if sidecar.get("source_email"):
                    resolve_review_item(sidecar["source_email"], selected.name, None)
                discard_review_item(selected)
                st.info(f"Discarded {selected.name}")
                st.rerun()

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
        st.caption("Edit any cell directly, then save. Changes go straight into students.xlsx.")
        edited = st.data_editor(
            rows,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            key="students_editor",
        )

        save_col, download_col = st.columns([1, 1])
        with save_col:
            if st.button("💾 Save changes", type="primary", width="stretch"):
                write_students(config.SPREADSHEET, edited)
                st.success("students.xlsx updated.")
                st.rerun()
        with download_col:
            buffer = io.BytesIO()
            buffer.write(config.SPREADSHEET.read_bytes())
            st.download_button(
                "⬇ Download students.xlsx",
                data=buffer.getvalue(),
                file_name="students.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
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
