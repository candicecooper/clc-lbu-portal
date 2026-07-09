"""
43_communication_log.py  —  CLC-LBU Portal
============================================
Student Communication Register / Log.

Privacy model:
  * student_communications stores INITIALS ONLY + the communication details.
  * Full names are merged in at export from an uploaded roster.
  * Attachments (images / PDFs) live in a PRIVATE Supabase Storage bucket and
    are inherently identifying — a deliberate, optional step beyond the
    initials-only rule. Viewed via short-lived signed URLs, never public.

Features
--------
1. Student dropdown pulled live from the SMARTAR Goal Builder (separate Supabase
   project; stored by name, stored here as initials only).
2. Archive tab — archive a student after confirming the record was downloaded,
   printed, and digitally archived.
3. Attachments — attach & label image(s)/PDF(s) to any entry.

Setup in the OPERATIONAL Supabase project (SQL at bottom of this file):
  * student_communications   (already created)
  * student_comm_archive     (created earlier)
  * comm_attachments         (NEW)
  * a PRIVATE Storage bucket named 'comm-attachments' + the storage policies.

Requirements: streamlit, supabase, pandas, openpyxl, reportlab
"""

import io
import re
import uuid
from datetime import datetime, date, time, timezone

import streamlit as st

# ── Document Archive integration (fails silently if unavailable) ──────────
try:
    from archive_utils import archive_once, initials_from_name
except Exception:
    def archive_once(*_a, **_k):
        pass
    def initials_from_name(name):
        parts = [p for p in str(name or "").replace("_", " ").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or None

import pandas as pd
from supabase import create_client

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
TABLE_NAME = "student_communications"
ARCHIVE_TABLE = "student_comm_archive"
ATTACH_TABLE = "comm_attachments"
BUCKET = "comm-attachments"
ALLOWED_EXT = ["png", "jpg", "jpeg", "gif", "webp", "pdf"]

ATTACH_WARNING = (
    "⚠️ **Don't attach anything containing personal information or photos of students** "
    "(signed forms showing names, medical details, images of children). Upload those to "
    "**EMS** and reference them in the log summary instead — e.g. *“Signed consent uploaded "
    "to EMS”*. Attachments here are for non-identifying material only."
)
ATTACH_ACK = ("I confirm this file contains no student personal information or photos — "
              "anything identifying has gone to EMS.")

SMARTAR_TABLE = "smartar_students"
SMARTAR_NAME_COLS = ["student_name", "name", "full_name", "student"]

COMM_TYPES = ["Phone call", "Text message", "Email", "Letter / mail",
              "Face-to-face", "Meeting", "Other"]
DIRECTIONS = ["Received", "Given"]
CONTACT_ROLES = ["", "Parent / Carer", "Family member", "Agency / DCP",
                 "Health", "School / Education", "Legal", "Other"]

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False


# ----------------------------------------------------------------------------
# SECRETS / CLIENTS
# ----------------------------------------------------------------------------
def _get_secret(*names):
    for n in names:
        try:
            if n in st.secrets:
                return st.secrets[n]
        except Exception:
            pass
    return None


@st.cache_resource(show_spinner=False)
def get_client():
    url = _get_secret("SUPABASE_URL", "supabase_url")
    key = _get_secret("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY",
                      "supabase_key", "supabase_anon_key")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Could not connect to Supabase: {e}")
        return None


def get_smartar_client():
    url = key = None
    try:
        sec = st.secrets
        if "supabase" in sec:
            sub = sec["supabase"]
            try:
                url = sub.get("url")
                key = sub.get("key")
            except Exception:
                pass
    except Exception:
        pass
    if not url:
        url = _get_secret("BEHAVIOUR_SUPABASE_URL", "SMARTAR_SUPABASE_URL")
    if not key:
        key = _get_secret("BEHAVIOUR_SUPABASE_KEY", "SMARTAR_SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


# ----------------------------------------------------------------------------
# COMM-LOG DATA
# ----------------------------------------------------------------------------
def fetch_records(client, code=None, date_from=None, date_to=None):
    try:
        q = client.table(TABLE_NAME).select("*")
        if code:
            q = q.eq("student_initials", code)
        if date_from:
            q = q.gte("comm_date", date_from.isoformat())
        if date_to:
            q = q.lte("comm_date", date_to.isoformat())
        q = q.order("comm_date", desc=True).order("created_at", desc=True)
        return q.execute().data or []
    except Exception as e:
        st.error(f"Could not load records: {e}")
        return []


def get_codes(client):
    try:
        res = client.table(TABLE_NAME).select("student_initials").execute()
        return sorted({(r.get("student_initials") or "").strip()
                       for r in (res.data or []) if r.get("student_initials")})
    except Exception:
        return []


def insert_record(client, payload):
    return client.table(TABLE_NAME).insert(payload).execute()


def update_record(client, rec_id, payload):
    return client.table(TABLE_NAME).update(payload).eq("id", rec_id).execute()


def delete_record(client, rec_id):
    # remove any attached files from storage first (rows cascade-delete)
    try:
        paths = [a["storage_path"] for a in get_attachments(client, rec_id)]
        if paths:
            try:
                client.storage.from_(BUCKET).remove(paths)
            except Exception:
                pass
    except Exception:
        pass
    return client.table(TABLE_NAME).delete().eq("id", rec_id).execute()


# ----------------------------------------------------------------------------
# ATTACHMENTS
# ----------------------------------------------------------------------------
def _safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "file")


def get_attachments(client, comm_id):
    try:
        res = (client.table(ATTACH_TABLE).select("*").eq("comm_id", comm_id)
               .order("uploaded_at").execute())
        return res.data or []
    except Exception:
        return []


def get_attachment_counts(client, comm_ids):
    if not comm_ids:
        return {}
    try:
        res = client.table(ATTACH_TABLE).select("comm_id").in_("comm_id", comm_ids).execute()
        d = {}
        for r in (res.data or []):
            d[r["comm_id"]] = d.get(r["comm_id"], 0) + 1
        return d
    except Exception:
        return {}


def get_attachment_labels(client, comm_ids):
    if not comm_ids:
        return {}
    try:
        res = (client.table(ATTACH_TABLE).select("comm_id,label,file_name")
               .in_("comm_id", comm_ids).execute())
        d = {}
        for a in (res.data or []):
            lab = a.get("label") or a.get("file_name") or "attachment"
            d.setdefault(a["comm_id"], []).append(lab)
        return {k: "; ".join(v) for k, v in d.items()}
    except Exception:
        return {}


def upload_attachment(client, comm_id, uploaded_file, label):
    try:
        data = uploaded_file.getvalue()
        path = f"{comm_id}/{uuid.uuid4().hex}_{_safe_name(uploaded_file.name)}"
        mime = uploaded_file.type or "application/octet-stream"
        client.storage.from_(BUCKET).upload(path, data, {"content-type": mime})
        client.table(ATTACH_TABLE).insert({
            "comm_id": comm_id, "storage_path": path,
            "file_name": uploaded_file.name, "label": label or None, "mime_type": mime,
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def signed_url(client, path, expires=3600):
    try:
        res = client.storage.from_(BUCKET).create_signed_url(path, expires)
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
        return None
    except Exception:
        return None


def delete_attachment(client, att):
    try:
        client.storage.from_(BUCKET).remove([att["storage_path"]])
    except Exception:
        pass
    try:
        client.table(ATTACH_TABLE).delete().eq("id", att["id"]).execute()
    except Exception:
        pass


def render_attachments(client, comm_id, key_prefix):
    """Show existing attachments + an uploader to add more, for one record."""
    atts = get_attachments(client, comm_id)
    if atts:
        st.markdown("**Attachments**")
        for a in atts:
            url = signed_url(client, a["storage_path"])
            label = a.get("label") or a.get("file_name") or "attachment"
            is_img = (a.get("mime_type") or "").startswith("image/")
            col1, col2 = st.columns([4, 1])
            with col1:
                if is_img and url:
                    st.image(url, caption=label, width=240)
                elif url:
                    st.markdown(f"📄 **{label}** — [{a.get('file_name')}]({url})")
                else:
                    st.write(f"📎 {label} (preview unavailable)")
            with col2:
                if st.button("Remove", key=f"{key_prefix}_del_{a['id']}"):
                    delete_attachment(client, a)
                    st.rerun()

    st.warning(ATTACH_WARNING)
    add_files = st.file_uploader("Add image(s) / PDF(s) to this record",
                                 type=ALLOWED_EXT, accept_multiple_files=True,
                                 key=f"{key_prefix}_add")
    add_label = st.text_input("Label for the above (optional)", key=f"{key_prefix}_lbl",
                              placeholder="e.g. Newsletter or info sheet")
    add_ack = st.checkbox(ATTACH_ACK, key=f"{key_prefix}_ack") if add_files else False
    if st.button("Upload", key=f"{key_prefix}_up", disabled=not (add_files and add_ack)):
        errs = []
        for f in add_files:
            ok, err = upload_attachment(client, comm_id, f, add_label)
            if not ok:
                errs.append(f"{f.name}: {err}")
        if errs:
            st.error("Some uploads failed:\n" + "\n".join(errs))
        else:
            st.success("Uploaded.")
            st.rerun()


# ----------------------------------------------------------------------------
# ARCHIVE DATA
# ----------------------------------------------------------------------------
def get_archived_codes(client):
    try:
        res = client.table(ARCHIVE_TABLE).select("student_initials").eq("archived", True).execute()
        return [r["student_initials"] for r in (res.data or [])]
    except Exception:
        return []


def get_archive_rows(client):
    try:
        res = (client.table(ARCHIVE_TABLE).select("*").eq("archived", True)
               .order("archived_at", desc=True).execute())
        return res.data or []
    except Exception:
        return []


def archive_student(client, code, by):
    now = datetime.now(timezone.utc).isoformat()
    return client.table(ARCHIVE_TABLE).upsert({
        "student_initials": code, "archived": True, "record_downloaded": True,
        "record_printed": True, "record_digitally_archived": True,
        "archived_at": now, "archived_by": by or None, "updated_at": now,
    }, on_conflict="student_initials").execute()


def unarchive_student(client, code):
    return (client.table(ARCHIVE_TABLE)
            .update({"archived": False, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("student_initials", code).execute())


# ----------------------------------------------------------------------------
# SMARTAR STUDENTS
# ----------------------------------------------------------------------------
def initials_from_name(name):
    parts = re.findall(r"[A-Za-z]+", name or "")
    return "".join(p[0] for p in parts[:3]).upper()


def fetch_smartar_names(sb):
    if sb is None:
        return [], "not connected"
    try:
        rows = sb.table(SMARTAR_TABLE).select("*").execute().data or []
    except Exception as e:
        return [], str(e)
    if not rows:
        return [], None
    sample = rows[0]
    name_col = next((c for c in SMARTAR_NAME_COLS if c in sample), None)
    if name_col is None:
        return [], f"no name column found (columns: {list(sample.keys())})"
    names = []
    for r in rows:
        if r.get("placement_ended") is True or r.get("archived") is True:
            continue
        nm = (r.get(name_col) or "").strip()
        if nm:
            names.append(nm)
    return sorted(set(names)), None


def build_active_students(op_client, smartar_client):
    archived = set(get_archived_codes(op_client))
    comm_codes = set(get_codes(op_client))
    smartar_names, err = fetch_smartar_names(smartar_client)
    status = {"connected": smartar_client is not None and err is None,
              "count": len(smartar_names), "error": err}

    options, seen_codes, base_seen = [], set(), {}
    for nm in smartar_names:
        base = initials_from_name(nm)
        if not base:
            continue
        base_seen[base] = base_seen.get(base, 0) + 1
        code = base if base_seen[base] == 1 else f"{base}{base_seen[base]}"
        if code in archived:
            continue
        options.append((f"{nm} — {code}", code))
        seen_codes.add(code)
    for c in sorted(comm_codes):
        if c in archived or c in seen_codes:
            continue
        options.append((c, c))
        seen_codes.add(c)
    options.sort(key=lambda x: x[0].lower())
    return options, status


def suggest_code(base, existing):
    base = (base or "").strip().upper()
    existing_up = {c.upper() for c in existing}
    if not base or base not in existing_up:
        return base
    i = 2
    while f"{base}{i}" in existing_up:
        i += 1
    return f"{base}{i}"


# ----------------------------------------------------------------------------
# EXPORT / ROSTER
# ----------------------------------------------------------------------------
def parse_roster(uploaded_file):
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        return None, f"Could not read the roster file: {e}"
    if df.empty:
        return None, "The roster file is empty."
    cols = {str(c).strip().lower(): c for c in df.columns}
    code_col = next((o for k, o in cols.items()
                     if "initial" in k or k == "code" or "student code" in k or k == "id"), None)
    name_col = next((o for k, o in cols.items() if "name" in k), None)
    if code_col is None or name_col is None:
        return None, ("Roster needs a code/initials column (header containing 'Initials' "
                      "or 'Code') and a full name column (header containing 'Name').")
    mapping = {}
    for _, row in df.iterrows():
        code = str(row[code_col]).strip().upper()
        name = str(row[name_col]).strip()
        if code and code.lower() != "nan":
            mapping[code] = name if name.lower() != "nan" else ""
    return mapping, None


def resolve_name(code, roster):
    return roster.get((code or "").strip().upper()) if roster else None


def records_to_rows(records, roster=None, att_map=None):
    rows = []
    for r in records:
        code = r.get("student_initials", "")
        full = resolve_name(code, roster)
        row = {
            "id": r.get("id"),
            "Full name": full if full else ("" if roster else None),
            "Code": code,
            "Date": r.get("comm_date", ""),
            "Time": r.get("comm_time") or "",
            "Direction": r.get("direction", ""),
            "Type": r.get("comm_type", ""),
            "Who": r.get("contact_name") or "",
            "Role": r.get("contact_role") or "",
            "Summary": r.get("summary", ""),
            "Recorded by": r.get("recorded_by") or "",
        }
        if att_map is not None:
            row["Attachments"] = att_map.get(r.get("id"), "")
        rows.append(row)
    return rows


def build_excel(rows, roster_used, with_attachments=False):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Communication Log"
    headers = (["Full name", "Code"] if roster_used else ["Code"]) + \
              ["Date", "Time", "Direction", "Type", "Who", "Role", "Summary", "Recorded by"]
    if with_attachments:
        headers.append("Attachments")
    header_fill = PatternFill("solid", fgColor="1F4E5F")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center", horizontal="left")
        cell.border = border
    for i, row in enumerate(rows, start=2):
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=i, column=c, value=row.get(h, ""))
            cell.alignment = Alignment(vertical="top", wrap_text=(h in ("Summary", "Attachments")))
            cell.border = border
    widths = {"Full name": 26, "Code": 8, "Date": 12, "Time": 8, "Direction": 11,
              "Type": 14, "Who": 22, "Role": 16, "Summary": 60, "Recorded by": 14,
              "Attachments": 30}
    for c, h in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(h, 14)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows)+1)}"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_pdf(rows, roster_used, scope_label):
    if not HAS_REPORTLAB:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12*mm,
                            rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    head_style = ParagraphStyle("head", parent=styles["Normal"], fontSize=8, leading=10,
                                textColor=colors.white, fontName="Helvetica-Bold")
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=15)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    story = [Paragraph("Communication Log", title_style),
             Paragraph(f"{scope_label} &nbsp;&nbsp;|&nbsp;&nbsp; Generated "
                       f"{datetime.now().strftime('%d %b %Y, %H:%M')}", sub_style),
             Spacer(1, 6*mm)]
    if roster_used:
        headers = ["Student", "Date", "Time", "Dir.", "Type", "Who", "Summary"]
        col_widths = [42, 20, 13, 16, 24, 34, 124]
    else:
        headers = ["Code", "Date", "Time", "Dir.", "Type", "Who", "Summary"]
        col_widths = [18, 20, 13, 16, 24, 46, 136]
    data = [[Paragraph(h, head_style) for h in headers]]
    for r in rows:
        student = (r.get("Full name") or r.get("Code")) if roster_used else r.get("Code")
        data.append([Paragraph(str(student or ""), cell_style),
                     Paragraph(str(r.get("Date", "")), cell_style),
                     Paragraph(str(r.get("Time", "")), cell_style),
                     Paragraph(str(r.get("Direction", "")), cell_style),
                     Paragraph(str(r.get("Type", "")), cell_style),
                     Paragraph(str(r.get("Who", "")), cell_style),
                     Paragraph(str(r.get("Summary", "")).replace("\n", "<br/>"), cell_style)])
    table = Table(data, colWidths=[w*mm for w in col_widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E5F")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9C9C9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    doc.build(story)
    buf.seek(0)
    return buf


def build_print_html(rows, roster_used, scope_label, with_attachments=False):
    head_cells = (["Student"] if roster_used else ["Code"]) + \
                 ["Date", "Time", "Direction", "Type", "Who", "Summary"]
    if with_attachments:
        head_cells.append("Attachments")
    thead = "".join(f"<th>{h}</th>" for h in head_cells)
    body = ""
    for r in rows:
        student = (r.get("Full name") or r.get("Code")) if roster_used else r.get("Code")
        cells = [student, r.get("Date", ""), r.get("Time", ""), r.get("Direction", ""),
                 r.get("Type", ""), r.get("Who", ""), r.get("Summary", "")]
        if with_attachments:
            cells.append(r.get("Attachments", ""))
        body += "<tr>" + "".join(
            f"<td>{(str(c) if c is not None else '').replace(chr(10),'<br>')}</td>"
            for c in cells) + "</tr>"
    return f"""
    <style>
      .clc-print{{font-family:Arial,sans-serif;color:#222;}}
      .clc-print h3{{margin:0 0 2px 0;}}
      .clc-print .meta{{color:#666;font-size:12px;margin-bottom:10px;}}
      .clc-print table{{border-collapse:collapse;width:100%;font-size:12px;}}
      .clc-print th{{background:#1F4E5F;color:#fff;text-align:left;padding:6px 8px;}}
      .clc-print td{{border:1px solid #d4d4d4;padding:6px 8px;vertical-align:top;}}
      .clc-print tr:nth-child(even) td{{background:#f4f7f8;}}
    </style>
    <div class="clc-print"><h3>Communication Log</h3>
      <div class="meta">{scope_label} &nbsp;|&nbsp; Generated {datetime.now().strftime('%d %b %Y, %H:%M')}</div>
      <table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table></div>"""


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Communication Log", page_icon="📞", layout="wide")
st.title("📞 Communication Log")
st.caption("A chronicle of every communication and document — in or out — for each student. "
           "Supabase holds **initials only**; full names are merged in at export.")

client = get_client()
if client is None:
    st.error("No Supabase connection. Check SUPABASE_URL / SUPABASE_KEY in the app secrets.")
    st.stop()

smartar = get_smartar_client()
active_options, smartar_status = build_active_students(client, smartar)
code_to_label = {}
for lbl, code in active_options:
    code_to_label.setdefault(code, lbl)

if "up_seed" not in st.session_state:
    st.session_state.up_seed = 0

tab_log, tab_view, tab_export, tab_archive = st.tabs(
    ["➕ Log a communication", "📋 View / edit", "⬇️ Export & print", "🗄️ Archive"])

# ---- TAB 1: LOG ------------------------------------------------------------
with tab_log:
    st.subheader("Log a communication")
    _ok = st.session_state.pop("flash_ok", None)
    if _ok:
        st.success(_ok)
    _wn = st.session_state.pop("flash_warn", None)
    if _wn:
        st.warning(_wn)
    with st.expander("SMARTAR connection status", expanded=False):
        if not smartar_status["connected"]:
            st.write("⚠️ Not reading from SMARTAR — using existing students + manual add. "
                     f"Detail: `{smartar_status['error'] or 'no SMARTAR secrets found'}`")
        else:
            st.write(f"✅ Pulled **{smartar_status['count']}** student(s) from `{SMARTAR_TABLE}`.")

    mode = st.radio("Student", ["Choose existing", "Add new"], horizontal=True, key="student_mode")
    student_code = None
    if mode == "Choose existing":
        if active_options:
            idx = st.selectbox("Student", range(len(active_options)),
                               format_func=lambda i: active_options[i][0], key="log_pick")
            student_code = active_options[idx][1]
            st.caption(f"Will be stored as initials: **{student_code}**")
        else:
            st.info("No students available yet — switch to **Add new**.")
    else:
        existing = [c for (_, c) in active_options] + get_codes(client)
        raw = st.text_input("New student initials / code",
                            help="e.g. JS. If two students share initials, use JS2.").strip().upper()
        student_code = raw or None
        if raw and raw in {c.upper() for c in existing}:
            st.warning(f"⚠️ **{raw}** already exists. If this is a *different* student, "
                       f"use a distinct code like **{suggest_code(raw, existing)}**.")

    c1, c2, c3 = st.columns(3)
    with c1:
        comm_date = st.date_input("Date", value=date.today())
    with c2:
        include_time = st.checkbox("Record a time")
        comm_time = st.time_input("Time", value=time(9, 0)) if include_time else None
    with c3:
        direction = st.radio("Direction", DIRECTIONS, horizontal=True)

    c4, c5 = st.columns(2)
    with c4:
        comm_type = st.selectbox("Type", COMM_TYPES)
    with c5:
        contact_role = st.selectbox("Contact category (optional)", CONTACT_ROLES)

    contact_name = st.text_input("Who (e.g. Mum, DCP caseworker, Dr Smith)")
    summary = st.text_area("Summary", height=110,
                           placeholder="e.g. Permission given over the phone for the Adelaide Zoo excursion on 14 Aug.")
    recorded_by = st.text_input("Recorded by (optional)", placeholder="Your initials")

    st.markdown("**Attachments (optional)**")
    st.warning(ATTACH_WARNING)
    new_files = st.file_uploader("Attach image(s) / PDF(s)", type=ALLOWED_EXT,
                                 accept_multiple_files=True,
                                 key=f"log_files_{st.session_state.up_seed}")
    new_label = st.text_input("Label for the attachment(s) (optional)",
                              key=f"log_label_{st.session_state.up_seed}",
                              placeholder="e.g. Newsletter or info sheet")
    new_ack = st.checkbox(ATTACH_ACK, key=f"log_ack_{st.session_state.up_seed}") if new_files else False

    if st.button("💾 Save communication", type="primary"):
        if not student_code:
            st.error("Please choose or add a student.")
        elif not summary.strip():
            st.error("Please add a summary.")
        elif new_files and not new_ack:
            st.error("Tick the confirmation under Attachments to upload these file(s) — "
                     "or remove them to save without attachments.")
        else:
            try:
                res = insert_record(client, {
                    "student_initials": student_code.strip().upper(),
                    "comm_date": comm_date.isoformat(),
                    "comm_time": comm_time.strftime("%H:%M") if include_time and comm_time else None,
                    "direction": direction, "comm_type": comm_type,
                    "contact_name": contact_name.strip() or None,
                    "contact_role": contact_role or None,
                    "summary": summary.strip(),
                    "recorded_by": recorded_by.strip() or None,
                })
                new_id = res.data[0]["id"] if res.data else None
                att_errors = []
                if new_id and new_files:
                    for f in new_files:
                        ok, err = upload_attachment(client, new_id, f, new_label)
                        if not ok:
                            att_errors.append(f"{f.name}: {err}")
                # read the record back to confirm it truly persisted
                code_up = student_code.strip().upper()
                saved_count = len(fetch_records(client, code=code_up))
                st.session_state["flash_ok"] = (
                    f"✅ Saved & verified — **{code_up}** now has **{saved_count}** logged "
                    f"communication(s). Open the **📋 View / edit** tab to see them."
                )
                if att_errors:
                    st.session_state["flash_warn"] = (
                        "Record saved, but attachment(s) failed (is the 'comm-attachments' "
                        "bucket + table set up?):\n" + "\n".join(att_errors)
                    )
                st.session_state.up_seed += 1
                st.cache_resource.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")

# ---- TAB 2: VIEW / EDIT ----------------------------------------------------
with tab_view:
    st.subheader("View / edit log")
    try:
        _total = len(fetch_records(client))
        st.caption(f"📁 {_total} communication(s) saved in total. This is the live record — "
                   "every saved entry is stored in Supabase and listed below.")
    except Exception:
        pass
    archived = set(get_archived_codes(client))
    record_codes = get_codes(client)
    fc1, fc2, fc3 = st.columns([1.2, 1, 1])
    with fc1:
        inc_arch = st.checkbox("Include archived students", key="view_inc_arch")
        pool = record_codes if inc_arch else [c for c in record_codes if c not in archived]
        view_code = st.selectbox("Filter by student", ["All students"] + pool, key="view_code")
    with fc2:
        use_dates = st.checkbox("Filter by date range", key="view_use_dates")
    with fc3:
        if use_dates:
            dr = st.date_input("From / to", value=(date.today(), date.today()), key="view_dr")
            d_from, d_to = (dr if isinstance(dr, (list, tuple)) and len(dr) == 2 else (None, None))
        else:
            d_from = d_to = None

    code_filter = None if view_code == "All students" else view_code
    records = fetch_records(client, code=code_filter, date_from=d_from, date_to=d_to)
    if code_filter is None and not inc_arch:
        records = [r for r in records if r.get("student_initials") not in archived]

    if not records:
        st.info("No communications match this filter yet.")
    else:
        counts = get_attachment_counts(client, [r["id"] for r in records])
        df = pd.DataFrame(records_to_rows(records)).drop(columns=["Full name"], errors="ignore")
        df["📎"] = [counts.get(r["id"], 0) for r in records]
        df = df.drop(columns=["id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(records)} record(s). 📎 = attachments. Full names appear only in Export.")

        st.markdown("##### Edit a record / manage its attachments")
        def _label(r):
            return f"{r.get('comm_date','')} · {r.get('student_initials','')} · " \
                   f"{r.get('comm_type','')} · {(r.get('summary','') or '')[:50]}"
        idx = st.selectbox("Select a record", list(range(len(records))),
                           format_func=lambda i: _label(records[i]), key="edit_pick")
        rec = records[idx]
        with st.expander("Open record", expanded=True):
            render_attachments(client, rec["id"], key_prefix=f"att_{rec['id']}")
            st.divider()
            e1, e2, e3 = st.columns(3)
            with e1:
                e_date = st.date_input("Date", value=date.fromisoformat(rec["comm_date"]), key="e_date")
            with e2:
                e_inc_time = st.checkbox("Time", value=bool(rec.get("comm_time")), key="e_inc_time")
                default_t = time(9, 0)
                if rec.get("comm_time"):
                    try:
                        hh, mm = rec["comm_time"].split(":")
                        default_t = time(int(hh), int(mm))
                    except Exception:
                        pass
                e_time = st.time_input("Time", value=default_t, key="e_time") if e_inc_time else None
            with e3:
                e_dir = st.radio("Direction", DIRECTIONS,
                                 index=DIRECTIONS.index(rec["direction"]) if rec.get("direction") in DIRECTIONS else 0,
                                 horizontal=True, key="e_dir")
            e_type = st.selectbox("Type", COMM_TYPES,
                                  index=COMM_TYPES.index(rec["comm_type"]) if rec.get("comm_type") in COMM_TYPES else 0,
                                  key="e_type")
            e_role = st.selectbox("Contact category", CONTACT_ROLES,
                                  index=CONTACT_ROLES.index(rec.get("contact_role")) if rec.get("contact_role") in CONTACT_ROLES else 0,
                                  key="e_role")
            e_who = st.text_input("Who", value=rec.get("contact_name") or "", key="e_who")
            e_sum = st.text_area("Summary", value=rec.get("summary") or "", key="e_sum")
            e_by = st.text_input("Recorded by", value=rec.get("recorded_by") or "", key="e_by")
            if st.button("Update record", key="do_update"):
                try:
                    update_record(client, rec["id"], {
                        "comm_date": e_date.isoformat(),
                        "comm_time": e_time.strftime("%H:%M") if e_inc_time and e_time else None,
                        "direction": e_dir, "comm_type": e_type, "contact_role": e_role or None,
                        "contact_name": e_who.strip() or None, "summary": e_sum.strip(),
                        "recorded_by": e_by.strip() or None,
                    })
                    st.success("Updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update: {e}")
            st.divider()
            confirm = st.checkbox("Confirm I want to delete this record (and its attachments)", key="del_confirm")
            if st.button("🗑️ Delete record", key="do_delete", disabled=not confirm):
                try:
                    delete_record(client, rec["id"])
                    st.success("Deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete: {e}")

# ---- TAB 3: EXPORT & PRINT -------------------------------------------------
with tab_export:
    st.subheader("Export & print")
    st.markdown("Upload your **master roster** to merge full names in. Names are used in "
                "memory only and never saved.")
    roster_file = st.file_uploader("Master roster (.xlsx or .csv)", type=["xlsx", "csv"])
    roster = None
    if roster_file is not None:
        roster, err = parse_roster(roster_file)
        if err:
            st.error(err)
        else:
            st.success(f"Roster loaded — {len(roster)} student name(s) available for merging.")

    archived = set(get_archived_codes(client))
    record_codes = get_codes(client)
    xc1, xc2, xc3 = st.columns([1.2, 1, 1])
    with xc1:
        inc_arch_x = st.checkbox("Include archived students", key="x_inc_arch")
        pool = record_codes if inc_arch_x else [c for c in record_codes if c not in archived]
        x_code = st.selectbox("Scope", ["All students"] + pool, key="x_code")
    with xc2:
        x_use_dates = st.checkbox("Limit by date range", key="x_use_dates")
    with xc3:
        if x_use_dates:
            xdr = st.date_input("From / to", value=(date.today(), date.today()), key="x_dr")
            x_from, x_to = (xdr if isinstance(xdr, (list, tuple)) and len(xdr) == 2 else (None, None))
        else:
            x_from = x_to = None

    code_filter = None if x_code == "All students" else x_code
    records = fetch_records(client, code=code_filter, date_from=x_from, date_to=x_to)
    if code_filter is None and not inc_arch_x:
        records = [r for r in records if r.get("student_initials") not in archived]

    att_labels = get_attachment_labels(client, [r["id"] for r in records]) if records else {}
    has_att = bool(att_labels)
    rows = records_to_rows(records, roster=roster, att_map=att_labels if has_att else None)
    roster_used = roster is not None

    scope_label = "All students" if code_filter is None else f"Student: {code_filter}"
    if roster_used and code_filter and roster.get(code_filter.upper()):
        scope_label = f"Student: {roster[code_filter.upper()]} ({code_filter})"

    st.caption(f"{len(records)} record(s) in scope." +
               ("" if roster_used else "  ⚠️ No roster uploaded — output shows initials only."))

    if records:
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("⬇️ Excel (.xlsx)", data=build_excel(rows, roster_used, has_att),
                               file_name=f"communication_log_{datetime.now():%Y%m%d_%H%M}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        with d2:
            if HAS_REPORTLAB:
                st.download_button("⬇️ PDF list", data=build_pdf(rows, roster_used, scope_label),
                                   file_name=f"communication_log_{datetime.now():%Y%m%d_%H%M}.pdf",
                                   mime="application/pdf", use_container_width=True)
            else:
                st.button("PDF unavailable", disabled=True, use_container_width=True,
                          help="Add 'reportlab' to requirements.txt to enable PDF export.")
        with d3:
            st.toggle("Show printable list", key="show_print")
        if st.button("🗄️ Archive this export (initials-only)", key="arch_export"):
            _rows_priv = records_to_rows(records, roster=None,
                                         att_map=att_labels if has_att else None)
            _xls = build_excel(_rows_priv, False, has_att)
            archive_once(
                f"commlog_{code_filter or 'all'}_{datetime.now():%Y%m%d%H%M}",
                source_tool="Communication Log",
                doc_type="Communication Log Export",
                title=f"Communication Log Export — {code_filter or 'All students'} — {datetime.now():%d %b %Y}",
                file_bytes=_xls.getvalue() if hasattr(_xls, "getvalue") else _xls,
                filename=f"communication_log_{(code_filter or 'all').lower()}_{datetime.now():%Y%m%d_%H%M}.xlsx",
                student_initials=code_filter or None,
                created_by=st.session_state.get("user_email", "unknown"),
            )
        if has_att:
            st.caption("Attachment labels are listed in the Excel and the printable list "
                       "(the PDF stays a compact summary). The files themselves stay in the secure bucket.")
        if st.session_state.get("show_print"):
            st.markdown(build_print_html(rows, roster_used, scope_label, has_att), unsafe_allow_html=True)
            st.caption("Use your browser's Print (Ctrl/Cmd + P) to print or save as PDF.")
    else:
        st.info("Nothing to export for this scope yet.")

# ---- TAB 4: ARCHIVE --------------------------------------------------------
with tab_archive:
    st.subheader("Archive a student")
    st.markdown("Archive a student once their placement has ended **and** their full record "
                "has been downloaded, printed, and saved to their secure digital file. "
                "Archiving hides them from active lists but keeps all records and attachments.")
    archived = set(get_archived_codes(client))
    candidates = [c for c in get_codes(client) if c not in archived]
    if not candidates:
        st.info("No active students with records to archive.")
    else:
        pick = st.selectbox("Student to archive", candidates,
                            format_func=lambda c: code_to_label.get(c, c), key="arch_pick")
        n = len(fetch_records(client, code=pick))
        st.caption(f"**{n}** record(s) for {pick}. Download & print them from the Export tab first.")
        st.markdown("**Confirm the record lifecycle is complete:**")
        a1 = st.checkbox("✅ Record downloaded (Excel / PDF)", key="arch_dl")
        a2 = st.checkbox("✅ Record printed", key="arch_pr")
        a3 = st.checkbox("✅ Record digitally archived (saved to the student's secure file)", key="arch_da")
        by = st.text_input("Archived by (your initials)", key="arch_by")
        ready = a1 and a2 and a3
        if not ready:
            st.caption("Tick all three confirmations to enable archiving.")
        if st.button("🗄️ Archive student", type="primary", disabled=not ready, key="do_archive"):
            try:
                archive_student(client, pick, by)
                st.success(f"{pick} archived — confirmations recorded.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not archive (has student_comm_archive been created?): {e}")

    st.divider()
    st.markdown("##### Archived students")
    rows = get_archive_rows(client)
    if not rows:
        st.caption("None yet.")
    else:
        for r in rows:
            code = r["student_initials"]
            ts = (r.get("archived_at") or "")[:10]
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{code}** — archived {ts} by {r.get('archived_by') or '—'}  ·  "
                            "✓ downloaded ✓ printed ✓ digitally archived")
            with col2:
                if st.button("Unarchive", key=f"un_{code}"):
                    try:
                        unarchive_student(client, code)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not unarchive: {e}")


# ============================================================================
# SETUP SQL  — run in the SQL editor of your OPERATIONAL project
# ============================================================================
# -- Attachments table
# create table if not exists comm_attachments (
#     id           uuid primary key default gen_random_uuid(),
#     comm_id      uuid not null references student_communications(id) on delete cascade,
#     storage_path text not null,
#     file_name    text,
#     label        text,
#     mime_type    text,
#     uploaded_at  timestamptz not null default now()
# );
# create index if not exists idx_comm_attachments_comm on comm_attachments(comm_id);
#
# -- Storage bucket: create a PRIVATE bucket named  comm-attachments
# --   (Dashboard -> Storage -> New bucket -> name: comm-attachments, Public: OFF)
# -- Then allow the anon role to use just that bucket:
# create policy "comm_attach_read"  on storage.objects for select to anon using (bucket_id = 'comm-attachments');
# create policy "comm_attach_write" on storage.objects for insert to anon with check (bucket_id = 'comm-attachments');
# create policy "comm_attach_del"   on storage.objects for delete to anon using (bucket_id = 'comm-attachments');
