# Erasmus DocFlow — Web QA checklist

Manual and automated checks for the deployed Streamlit app.
Priority: **P0** must pass before the demo, **P1** important, **P2** if time allows.

Legend: `[ ]` not run · `[x]` passed · `[!]` failed (add a note).

## 1. Deployment and secrets (P0)

- [ ] 1.1 Open the app URL; check **Manage app → logs**: no build errors, dependencies installed.
- [ ] 1.2 Sidebar shows `Gemini key loaded`; no `No GOOGLE_API_KEY detected` warning.
- [ ] 1.3 **Settings → Secrets** contains `GOOGLE_API_KEY = "..."` (TOML, double quotes, top level).
- [ ] 1.4 **Settings → Python version** is 3.12.
- [ ] 1.5 Reboot the app and reload: behaviour identical after a cold start.

## 2. Inbox listing (P0)

- [ ] 2.1 After a fresh reboot, Inbox shows `Emails in inbox: 10` (committed samples).
- [ ] 2.2 Table lists 10 rows with subject, sender and attachment count.
- [ ] 2.3 Counters show `Documents saved: 0` and `Needs a human: 0` (ephemeral filesystem).

## 3. Email upload (P0)

- [ ] 3.1 Upload one valid `.eml` with a PDF: success message, counter 11, file listed.
- [ ] 3.2 Upload the same file again: "Already in inbox", no duplicate row.
- [ ] 3.3 Upload 5 files at once: 5 added, counter 15.
- [ ] 3.4 Rename to `MAIL.EML` (uppercase) and upload: accepted and listed.
- [ ] 3.5 Upload a 0-byte `.eml`: stored, later skipped, no crash.
- [ ] 3.6 Upload garbage bytes named `.eml`: no crash, error or skip reported.
- [ ] 3.7 Upload an `.eml` named `../../evil.eml`: sanitized, no path escape.
- [ ] 3.8 Upload a 25 MB `.eml`: `Too large (max 20 MB)` warning.
- [ ] 3.9 Upload an `.eml` with a unicode attachment filename: listed and processed.

## 4. Run pipeline (P0)

- [ ] 4.1 Press **Run agent on inbox** with the 10 samples:
      `10 emails · 8 documents saved · 2 sent to review · 0 errors · 1 without attachments`.
- [ ] 4.2 Saved files match `Surname_Name_DocType_YYYY-YY.ext`.
- [ ] 4.3 Review folder gets 2 documents plus 2 `.reason.txt` files with confidence/notes.
- [ ] 4.4 `foto_borrosa.jpg` is in review, not saved.
- [ ] 4.5 `dokument_ohne_titel.pdf` is in review.
- [ ] 4.6 Press Run twice: no duplicated rows or files (idempotent).
- [ ] 4.7 Set confidence threshold to 0.1 and run: more files saved, fewer in review.
- [ ] 4.8 Set "Max emails per run" to 3: only 3 emails processed.
- [ ] 4.9 Runtime under ~90 s for 10 emails; spinner visible.

## 5. Student form (P0)

- [ ] 5.1 Submit with empty name/surname: validation error.
- [ ] 5.2 Name filled, no file and no message: "attach a document or write a question".
- [ ] 5.3 Full data plus PDF: saved as `Surname_Name_DocType_2026-27.pdf`.
- [ ] 5.4 Submit the same document again: deduplicated, no duplicate row.
- [ ] 5.5 No attachment, question "When is the deadline?": FAQ answer shown.
- [ ] 5.6 No attachment, question "Can I bring my dog?": escalated to staff.
- [ ] 5.7 PDF over 15 MB: too-large error.
- [ ] 5.8 Empty optional dates: submission still succeeds.
- [ ] 5.9 After a document submission: Students tab shows the new row with updated Missing.

## 6. Ask tab (P0)

- [ ] 6.1 "When is the deadline to submit the Learning Agreement?" → 15 October 2026.
- [ ] 6.2 "Did you get my insurance? I am Maria Rossi" → references her saved file.
- [ ] 6.3 "Who signs my Learning Agreement?" → correct FAQ answer.
- [ ] 6.4 Unknown question: `ESCALATE:` warning and escalation row created.
- [ ] 6.5 Repeat the unknown question: a second escalation row is appended.
- [ ] 6.6 "FAQ context used" expander shows the matched block or full FAQ.

## 7. Students tab (P0)

- [ ] 7.1 After a run: 9 rows, one per student, no duplicates.
- [ ] 7.2 Columns: Student, Surname, Semester, HostUniversity, StartDate, EndDate, Deadline,
      Documents, Missing, Status, Expired.
- [ ] 7.3 Review rows have empty HostUniversity/StartDate and `needs_review` status.
- [ ] 7.4 Download `students.xlsx`: opens in Excel/LibreOffice, has Students and Documents sheets.
- [ ] 7.5 Download `.zip`: only renamed documents, no `.gitkeep`, no `.reason.txt`.
- [ ] 7.6 "Handed to a person" table shows question, reason, timestamp; CSV downloads.

## 8. Web download (P1) — optional nice-to-have

- [ ] 8.1 Public PDF URL: downloaded, classified and saved with the naming pattern.
- [ ] 8.2 URL returning `Content-Disposition`: that filename is used.
- [ ] 8.3 `file:///etc/passwd`: rejected, only http(s) allowed.
- [ ] 8.4 404 URL: clear error, no crash.
- [ ] 8.5 HTML page URL: warning "That URL is a web page, not a document", never saved.
- [ ] 8.6 `http://localhost/...` or `http://192.168.x.x/...`: rejected with "not reachable".
- [ ] 8.7 Login-protected URL (403): warning that the link needs a login.

## 9. Failure injection (P1)

- [ ] 9.1 Remove the secret and reboot: sidebar warning, page still loads; Run shows a clear error.
- [ ] 9.2 Wrong API key: per-attachment errors, documents to review, no crash.
- [ ] 9.3 Model overloaded: fallback chain completes the run.
- [ ] 9.4 Empty inbox: `0 emails`, no crash.
- [ ] 9.5 Ask tab with no spreadsheet: answers from FAQ, empty student context.

## 10. UI counters and empty states (P1)

- [ ] 10.1 After a run: `Documents saved: 8`, `Needs a human: 2` (ignores `.reason.txt` and `.gitkeep`).
- [ ] 10.2 Fresh app, Students tab: "Spreadsheet empty. Run the agent first."
- [ ] 10.3 Fresh app, Ask tab: questions still work.
- [ ] 10.4 Every email expander opens/closes without layout break.

## 11. Ephemeral filesystem and concurrency (P1)

- [ ] 11.1 Run, then Reboot: outputs cleared, 10 sample emails remain.
- [ ] 11.2 Two browser tabs press Run together: no crash, consistent final state.
- [ ] 11.3 Idle 20+ minutes, reload: app wakes, data reset, still functional.
- [ ] 11.4 Sidebar shows "Public demo. No login..." and "Generated files: N documents".
- [ ] 11.5 **Prepare state bundle → Download state (.zip)**: bundle downloads, size shown.
- [ ] 11.6 Reboot, upload the bundle, **Restore state**: spreadsheet and documents return.
- [ ] 11.7 Upload a random `.zip`: `Unexpected file in bundle` or `not a valid .zip`, nothing changes.
- [ ] 11.8 **Reset demo data** disabled until the checkbox; after reset, inbox keeps 10 emails.

## 12. Cross-browser and responsive (P2)

- [ ] 12.1 Chrome, Firefox, Edge: same layout, no console errors.
- [ ] 12.2 Mobile width: tabs and tables usable.
- [ ] 12.3 Throttled connection: spinner during run, no UI glitch.

## 13. Security (P1)

- [ ] 13.1 API key never visible in page source or network responses.
- [ ] 13.2 Crafted filenames (`..`, `\`, NUL, 300 chars): sanitized or rejected.
- [ ] 13.3 Public URL: users cannot read secrets or the server filesystem.

## 14. Automated regression (run before the demo)

```bash
pytest -q                                                   # 111 offline tests
python scripts/check_inbox.py                               # inbox doctor
python scripts/check_requirements.py                        # 15 must-have checks
RUN_LLM_TESTS=1 pytest tests/test_llm_integration.py -v     # 4 live Gemini tests
```

## 15. Pre-demo smoke run (5 minutes, P0)

1. Reboot app; sidebar shows key loaded.
2. Inbox counters: 10 / 0 / 0.
3. Run: `10 · 8 · 2 · 0 · 1`.
4. Students: 9 rows, download and open the xlsx.
5. Ask the deadline question: answered.
6. Ask an unknown question: escalation row appears.
7. Student form: quick PDF submission, filename shown.

## Coverage notes

- Automated: sections 3, 4 (partly), 5 (backend), 6 (backend), 9.2–9.4.
- Manual on the deployed URL: sections 1, 2, 7, 8, 10–13, 15.
- Known limitation: no real Gmail mailbox; `.eml` upload and the student form are the intake paths.
