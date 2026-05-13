import streamlit as st
from datetime import datetime, date, time
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import streamlit.components.v1 as components
import io
import json
import os
from supabase import create_client

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Program Changes Manager", layout="wide")

st.markdown("""
<style>
    .main {background-color: #f0f2f6;}
    .stButton>button {
        background-color: #1A7A6E; color: white;
        border-radius: 5px; padding: 0.5rem 1rem; font-weight: 600;
    }
    .stButton>button:hover { background-color: #156359; }
    .change-card {
        background-color: white; padding: 1.5rem;
        border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem;
    }
    .edit-mode-banner {
        background-color: #fff3cd; border-left: 4px solid #C8760A;
        padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Supabase
# ─────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
STAFF_LIST = [
    "Candice", "Annette", "Ben Selga", "Ben Sutton", "Caitie",
    "Jacqui", "Brenton", "Tom", "Naomi", "Vinnie", "Cheryl"
]

PROGRAM_OPTIONS = [
    "JP", "PY", "SY", "NIT", "PRT",
    "Meeting", "Own Lunch", "Lunch Release", "Other"
]

# ─────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────
for _k, _v in {
    'editing_change_id': None,
    'editing_change_data': None,
    'num_blocks': 1,
    'show_mobile_view': False,
    'pending_edit_preload': False,
    '_save_success': None,   # set to staff name after successful save, cleared after display
    '_save_updated': False,  # True when an edit was saved (vs new entry)
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────
# Edit pre-population — runs BEFORE any widget is instantiated.
# When an edit button fires it sets pending_edit_preload=True and reruns.
# This block then writes all widget keys on the very next run before they render.
# ─────────────────────────────────────────────
if st.session_state.pending_edit_preload and st.session_state.editing_change_data:
    _ed = st.session_state.editing_change_data

    def _pt(ts):
        try:
            if isinstance(ts, time):
                return ts
            p = str(ts).split(':')
            return time(int(p[0]), int(p[1]))
        except Exception:
            return time(9, 0)

    _edit_staff = _ed.get('staff_name', '')
    if _edit_staff in STAFF_LIST:
        st.session_state['staff_type_selector'] = "Regular Staff"
        st.session_state['staff_select_main'] = _edit_staff
    else:
        st.session_state['staff_type_selector'] = "TRT/Relief"
        st.session_state['trt_name_main'] = _edit_staff

    st.session_state['form_reason'] = _ed.get('reason', '')
    st.session_state['form_covered_by'] = _ed.get('covered_by') or ''
    st.session_state['form_notes'] = _ed.get('notes') or ''

    _edit_blocks = _ed.get('time_blocks', [])
    if isinstance(_edit_blocks, str):
        _edit_blocks = json.loads(_edit_blocks)
    st.session_state.num_blocks = max(1, len(_edit_blocks))

    for _i, _blk in enumerate(_edit_blocks):
        _prog = _blk.get('program_type', 'JP')
        _rb = _blk.get('released_by', '')
        st.session_state[f'start_{_i}'] = _pt(_blk.get('start_time', '09:00:00'))
        st.session_state[f'end_{_i}'] = _pt(_blk.get('end_time', '10:00:00'))
        st.session_state[f'program_type_{_i}'] = _prog if _prog in PROGRAM_OPTIONS else PROGRAM_OPTIONS[0]
        if _rb in STAFF_LIST:
            st.session_state[f'released_by_{_i}'] = _rb
            st.session_state[f'released_by_manual_{_i}'] = ''
        else:
            st.session_state[f'released_by_{_i}'] = 'N/A'
            st.session_state[f'released_by_manual_{_i}'] = _rb

    st.session_state.pending_edit_preload = False

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def parse_time(time_str):
    try:
        if isinstance(time_str, time):
            return time_str
        parts = str(time_str).split(':')
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return time(9, 0)


def format_time(t):
    if isinstance(t, time):
        return t.strftime("%I:%M %p").lstrip('0')
    elif isinstance(t, str):
        try:
            return datetime.strptime(t, "%H:%M:%S").strftime("%I:%M %p").lstrip('0')
        except Exception:
            return t
    return str(t)


def _parse_blocks(raw):
    """Normalise time_blocks — may arrive as list or JSON string from Supabase."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return raw or []


# ─────────────────────────────────────────────
# Supabase CRUD
# ─────────────────────────────────────────────

def get_changes_for_date(target_date_str):
    try:
        sb = get_supabase()
        result = (
            sb.table("program_changes")
            .select("*")
            .eq("change_date", target_date_str)
            .order("created_at")
            .execute()
        )
        rows = result.data or []
        for row in rows:
            row['time_blocks'] = _parse_blocks(row.get('time_blocks'))
        return rows
    except Exception as e:
        st.error(f"Could not load program changes: {e}")
        return []


def save_program_change(change_data):
    try:
        sb = get_supabase()
        payload = {k: v for k, v in change_data.items()
                   if k not in ('id', 'created_at', 'updated_at')}
        sb.table("program_changes").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Could not save: {e}")
        return False


def update_program_change(change_id, new_data):
    try:
        sb = get_supabase()
        payload = {k: v for k, v in new_data.items()
                   if k not in ('id', 'created_at')}
        payload['updated_at'] = datetime.now().isoformat()
        sb.table("program_changes").update(payload).eq("id", change_id).execute()
        return True
    except Exception as e:
        st.error(f"Could not update: {e}")
        return False


def delete_program_change(change_id):
    try:
        sb = get_supabase()
        sb.table("program_changes").delete().eq("id", change_id).execute()
        return True
    except Exception as e:
        st.error(f"Could not delete: {e}")
        return False


def export_all_data():
    try:
        sb = get_supabase()
        result = sb.table("program_changes").select("*").order("change_date").execute()
        return json.dumps(result.data or [], indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def import_data(json_str):
    try:
        records = json.loads(json_str)
        sb = get_supabase()
        clean = [{k: v for k, v in r.items()
                  if k not in ('id', 'created_at', 'updated_at')} for r in records]
        if clean:
            sb.table("program_changes").insert(clean).execute()
        return True
    except Exception as e:
        st.error(f"Import failed: {e}")
        return False


# ─────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────

def generate_pdf(changes, target_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            topMargin=1*cm, bottomMargin=1*cm,
                            leftMargin=1*cm, rightMargin=1*cm)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CT', parent=styles['Heading1'], fontSize=16,
        textColor=colors.HexColor('#1A7A6E'), alignment=TA_CENTER, spaceAfter=12
    )
    story.append(Paragraph(
        f"Program Changes — {datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')}",
        title_style
    ))
    story.append(Spacer(1, 0.3*cm))

    if not changes:
        story.append(Paragraph("No program changes scheduled for this day",
                               ParagraphStyle('NC', parent=styles['Normal'],
                                              fontSize=12, alignment=TA_CENTER,
                                              textColor=colors.grey)))
    else:
        for idx, change in enumerate(changes):
            header_text = f"<b>{change.get('staff_name','N/A')}: {change.get('reason','Program Change')}</b>"
            if change.get('covered_by'):
                header_text += f"<br/><font size=9>Covered by: {change['covered_by']}</font>"
            ht = Table([[Paragraph(header_text, ParagraphStyle(
                'CH', parent=styles['Normal'], fontSize=11,
                textColor=colors.HexColor('#1A7A6E')))]], colWidths=[25*cm])
            ht.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#E8F4F2')),
                ('PADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(ht)
            story.append(Spacer(1, 0.2*cm))
            for block in _parse_blocks(change.get('time_blocks')):
                block_text = (f"{format_time(block.get('start_time',''))} → "
                              f"{format_time(block.get('end_time',''))}: "
                              f"{block.get('modified_program','N/A')}")
                if block.get('released_by'):
                    block_text += f" (Release: {block['released_by']})"
                dt = Table([[block_text]], colWidths=[25*cm])
                dt.setStyle(TableStyle([
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('PADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ]))
                story.append(dt)
            if idx < len(changes) - 1:
                story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# Mobile HTML
# ─────────────────────────────────────────────

def render_mobile_view(changes, target_date):
    date_str = datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')
    body = ""
    if not changes:
        body = '<p style="text-align:center;color:#666;padding:2rem;">No program changes scheduled</p>'
    else:
        for change in changes:
            covered_html = (f'<div class="mobile-covered">Covered by: {change["covered_by"]}</div>'
                            if change.get('covered_by') else "")
            rows = ""
            for block in _parse_blocks(change.get('time_blocks')):
                rb_html = (f' <span class="released-by">(Release: {block["released_by"]})</span>'
                           if block.get('released_by') else '')
                rows += (f'<div class="block-item">'
                         f'<span class="mobile-time">'
                         f'{format_time(block.get("start_time",""))} → '
                         f'{format_time(block.get("end_time",""))}</span>: '
                         f'{block.get("modified_program","N/A")}{rb_html}</div>')
            blocks_section = f'<div class="mobile-blocks">{rows}</div>' if rows else ''
            notes_html = (f'<div class="mobile-notes">{change["notes"]}</div>'
                          if change.get('notes') else '')
            body += f"""
            <div class="mobile-change">
                <div class="mobile-staff">{change.get('staff_name','N/A')}</div>
                <div class="mobile-reason">{change.get('reason','Program Change')}</div>
                {covered_html}{blocks_section}{notes_html}
            </div>"""

    return f"""<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
    <style>
        *{{box-sizing:border-box;margin:0;padding:0;}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f6;padding:12px;}}
        .mobile-view{{background:white;border-radius:10px;overflow:hidden;
            box-shadow:0 2px 8px rgba(0,0,0,0.15);width:100%;max-width:420px;margin:0 auto;}}
        .mobile-header{{background:#1A7A6E;color:white;padding:14px 16px;text-align:center;
            font-weight:bold;font-size:1.1rem;line-height:1.4;}}
        .mobile-header span{{font-size:0.88rem;font-weight:normal;display:block;opacity:0.9;}}
        .mobile-body{{padding:12px 14px;}}
        .mobile-change{{border-left:4px solid #C8760A;padding:8px 10px;
            margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #eee;}}
        .mobile-change:last-child{{border-bottom:none;margin-bottom:0;}}
        .mobile-staff{{font-weight:bold;color:#1A7A6E;font-size:1rem;margin-bottom:2px;}}
        .mobile-reason{{color:#555;font-size:0.85rem;margin-bottom:6px;}}
        .mobile-covered{{font-size:0.82rem;color:#1A7A6E;font-weight:600;margin-bottom:6px;}}
        .mobile-blocks{{background:#f8f9fa;padding:8px 10px;border-radius:5px;font-size:0.82rem;}}
        .block-item{{margin:4px 0;line-height:1.4;}}
        .mobile-time{{color:#C8760A;font-weight:600;}}
        .released-by{{color:#888;font-size:0.78rem;}}
        .mobile-notes{{font-size:0.8rem;color:#666;font-style:italic;margin-top:6px;}}
        .mobile-footer{{padding:10px 14px;border-top:1px solid #eee;text-align:center;}}
        .print-btn{{background:#C8760A;color:white;padding:8px 20px;border-radius:6px;
            font-size:0.85rem;font-weight:600;cursor:pointer;border:none;margin:4px;}}
        @media print{{.mobile-footer{{display:none;}}body{{padding:0;background:white;}}
            .mobile-view{{box-shadow:none;border-radius:0;max-width:100%;}}}}
    </style>
</head><body>
    <div class="mobile-view">
        <div class="mobile-header">Program Changes<span>{date_str}</span></div>
        <div class="mobile-body">{body}</div>
        <div class="mobile-footer">
            <button class="print-btn" onclick="window.print()">🖨️ Print / Save PDF</button>
        </div>
    </div>
</body></html>"""


# ═══════════════════════════════════════════════════════════
# MAIN INTERFACE
# ═══════════════════════════════════════════════════════════

st.title("📋 Program Changes Manager")
st.caption("Changes are saved to the database and appear automatically in the Daily Bulletin.")

# Date selector + data controls
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    target_date = st.date_input("Select Date", value=date.today(), key="target_date")
with col2:
    st.write(""); st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with col3:
    st.write(""); st.write("")
    with st.popover("💾 Data"):
        st.markdown("**Export all changes (JSON backup)**")
        st.download_button(
            "📥 Download JSON",
            data=export_all_data(),
            file_name=f"program_changes_backup_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True
        )
        st.markdown("**Import from JSON backup**")
        uploaded_file = st.file_uploader("Upload JSON", type=['json'], key="import_json")
        if uploaded_file:
            if import_data(uploaded_file.read().decode()):
                st.success("✅ Imported!")
                st.rerun()

target_date_str = target_date.isoformat()
changes = get_changes_for_date(target_date_str)

# ── Post-save success banner (shown after rerun so it persists) ──────
if st.session_state._save_success:
    _name = st.session_state._save_success
    _verb = "updated" if st.session_state._save_updated else "saved"
    st.success(f"✅ Timetable {_verb} for **{_name}**!")
    st.session_state._save_success = None
    st.session_state._save_updated = False

st.markdown("---")

# ── Editing state ────────────────────────────────────────────
is_editing = st.session_state.editing_change_id is not None
edit_data = st.session_state.editing_change_data or {}

# ── Add / Edit expander ──────────────────────────────────────
form_title = "✏️ Edit Timetable Entry" if is_editing else "➕ Add Timetable Change"
with st.expander(form_title, expanded=is_editing or len(changes) == 0):

    if is_editing:
        st.markdown(
            f'<div class="edit-mode-banner">✏️ <b>Edit mode</b> — editing entry for '
            f'<b>{edit_data.get("staff_name","")}</b>. '
            f'Make changes then click <b>Update Timetable</b>.</div>',
            unsafe_allow_html=True
        )
        if st.button("❌ Cancel Edit", type="secondary"):
            st.session_state.editing_change_id = None
            st.session_state.editing_change_data = None
            st.session_state.num_blocks = 1
            st.rerun()
    else:
        st.info("""
**Important:** Only create entries for people WHO ARE ONSITE.

- **Ben Sutton absent?** → Entry for the TRT covering him
- **Caitie released for a meeting?** → Entry for Caitie AND one for whoever covers her
- **Someone picking up extra lunch duty?** → Entry for that person

Each entry = one person's view of what THEY are doing today.
""")

    # Staff type (outside form — refreshes immediately)
    st.subheader("Staff Member (must be onsite)")
    col1, col2 = st.columns([1, 3])
    with col1:
        staff_type = st.radio("Type", options=["Regular Staff", "TRT/Relief"],
                              key="staff_type_selector")
    with col2:
        if staff_type == "Regular Staff":
            staff_member = st.selectbox("Select Staff Member *",
                                        options=STAFF_LIST, key="staff_select_main")
        else:
            staff_member = st.text_input("TRT/Relief Name *",
                                         placeholder="e.g., Gary, Sarah Relief",
                                         key="trt_name_main")

    if not staff_member:
        st.warning("⬆️ Please select or enter a staff member name above")
        st.stop()

    with st.form("new_change_form"):
        st.info(f"📝 {'Editing' if is_editing else 'Creating'} timetable for: **{staff_member}**")
        st.markdown("---")
        st.subheader(f"Why is {staff_member}'s timetable different today?")

        reason = st.text_input(
            "Reason *", key="form_reason",
            placeholder="e.g., Covering absent Ben Sutton, Released for PAC Meeting"
        )

        if staff_type == "Regular Staff":
            col1, col2 = st.columns(2)
            with col1:
                covered_by = st.text_input(
                    "If THEY are being covered (optional)", key="form_covered_by",
                    placeholder="e.g., Candice, Tom"
                )
            with col2:
                notes = st.text_area("Additional Notes", key="form_notes",
                                     placeholder="Optional notes...")
        else:
            covered_by = None
            notes = st.text_area("Additional Notes", key="form_notes",
                                 placeholder="Optional notes...")

        st.markdown("---")
        st.subheader(f"{staff_member}'s Timetable for Today")
        st.caption("Program/Role includes Own Lunch and Lunch Release — no separate lunch column needed.")

        edit_blocks = _parse_blocks(edit_data.get('time_blocks', [])) if is_editing else []
        time_blocks = []

        for i in range(st.session_state.num_blocks):
            st.markdown(f"**Block {i + 1}**")
            bcol1, bcol2, bcol3, bcol4 = st.columns([2, 2, 3, 3])
            with bcol1:
                start_time = st.time_input("Start", value=time(9, 0), key=f"start_{i}")
            with bcol2:
                end_time = st.time_input("End", value=time(10, 0), key=f"end_{i}")
            with bcol3:
                program_type = st.selectbox("Program/Role", options=PROGRAM_OPTIONS,
                                            key=f"program_type_{i}")
            with bcol4:
                release_options = ["N/A"] + [s for s in STAFF_LIST if s != staff_member]
                released_by_sel = st.selectbox(
                    "Release", options=release_options, key=f"released_by_{i}",
                    help="Who releases this person for lunch/NIT/break?"
                )
                released_by_manual = st.text_input(
                    "or type name", placeholder="e.g., TRT name...",
                    key=f"released_by_manual_{i}", label_visibility="collapsed"
                )

            if released_by_manual.strip():
                released_by = released_by_manual.strip()
            elif released_by_sel != "N/A":
                released_by = released_by_sel
            else:
                released_by = ""

            time_blocks.append({
                'start_time': start_time.strftime("%H:%M:%S"),
                'end_time': end_time.strftime("%H:%M:%S"),
                'modified_program': program_type,
                'program_type': program_type,
                'released_by': released_by
            })

        col_add, _ = st.columns([1, 4])
        with col_add:
            if st.form_submit_button("➕ Add Block"):
                st.session_state.num_blocks += 1
                st.rerun()

        st.markdown("---")
        submitted = st.form_submit_button(
            "💾 Update Timetable" if is_editing else "💾 Save Timetable Change",
            type="primary", use_container_width=True
        )

        if submitted:
            _form_error = None
            if not staff_member or not reason:
                _form_error = "Please fill in Staff Member and Reason."
            else:
                valid_blocks = [b for b in time_blocks if b.get('program_type')]
                if not valid_blocks:
                    _form_error = "Please add at least one time block."

            if _form_error:
                st.error(_form_error)
            else:
                change_data = {
                    'change_date': target_date_str,
                    'staff_name': staff_member,
                    'reason': reason,
                    'covered_by': covered_by if covered_by else None,
                    'notes': st.session_state.get('form_notes') or None,
                    'time_blocks': valid_blocks
                }

                if is_editing:
                    _ok = update_program_change(st.session_state.editing_change_id, change_data)
                    if _ok:
                        st.session_state._save_success = staff_member
                        st.session_state._save_updated = True
                        st.session_state.editing_change_id = None
                        st.session_state.editing_change_data = None
                        st.session_state.num_blocks = 1
                        for _k in ['form_reason', 'form_covered_by', 'form_notes']:
                            st.session_state.pop(_k, None)
                        st.rerun()
                    # if _ok is False, save_program_change already called st.error()
                    # — don't rerun so the error stays visible
                else:
                    _ok = save_program_change(change_data)
                    if _ok:
                        st.session_state._save_success = staff_member
                        st.session_state._save_updated = False
                        st.session_state.num_blocks = 1
                        for _k in ['form_reason', 'form_covered_by', 'form_notes']:
                            st.session_state.pop(_k, None)
                        st.rerun()
                    # if _ok is False, save_program_change already called st.error()


# ─────────────────────────────────────────────
# Display saved changes
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader(f"Program Changes for {target_date.strftime('%A, %d %B %Y')}")
st.caption("Each entry = one person's view of their timetable changes")

if not changes:
    st.info("No program changes scheduled for this day")
else:
    for change in changes:
        with st.container():
            st.markdown('<div class="change-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                updated_tag = " *(edited)*" if change.get('updated_at') else ""
                st.markdown(
                    f"### {change.get('staff_name','N/A')}: "
                    f"{change.get('reason','Program Change')}{updated_tag}"
                )
                if change.get('covered_by'):
                    st.markdown(f"**Covered by:** {change['covered_by']}")
            with col2:
                if st.button("✏️ Edit", key=f"edit_{change['id']}", use_container_width=True):
                    st.session_state.editing_change_id = change['id']
                    st.session_state.editing_change_data = change
                    st.session_state.pending_edit_preload = True
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{change['id']}", use_container_width=True):
                    if delete_program_change(change['id']):
                        st.rerun()

            if change.get('notes'):
                st.markdown(f"*{change['notes']}*")

            blocks = _parse_blocks(change.get('time_blocks'))
            if blocks:
                st.markdown("**Timetable:**")
                for block in blocks:
                    time_display = (
                        f"{format_time(block.get('start_time',''))} → "
                        f"{format_time(block.get('end_time',''))}"
                    )
                    rb = block.get('released_by', '')
                    suffix = f" *(Release: {rb})*" if rb else ""
                    st.markdown(f"- **{time_display}**: {block.get('modified_program','N/A')}{suffix}")

            st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PDF + Mobile view
# ─────────────────────────────────────────────

st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("📱 Mobile View / Screenshot", use_container_width=True, type="secondary"):
        st.session_state.show_mobile_view = not st.session_state.show_mobile_view
with col2:
    pdf_buffer = generate_pdf(changes, target_date_str)
    st.download_button(
        "📄 Download PDF", data=pdf_buffer,
        file_name=f"program_changes_{target_date_str}.pdf",
        mime="application/pdf", use_container_width=True, type="primary"
    )

if st.session_state.show_mobile_view:
    st.markdown("---")
    st.markdown("### 📱 Mobile View")
    st.caption("Full-height panel — screenshot directly or download HTML to open on your phone.")
    mobile_html = render_mobile_view(changes, target_date_str)

    estimated_height = 260
    for c in changes:
        estimated_height += 120 + len(_parse_blocks(c.get('time_blocks'))) * 45
        if c.get('notes'):
            estimated_height += 30
    estimated_height = max(500, estimated_height)

    components.html(mobile_html, height=estimated_height, scrolling=False)
    st.markdown(" ")
    st.download_button(
        "📲 Download Mobile HTML",
        data=mobile_html.encode('utf-8'),
        file_name=f"program_changes_{target_date_str}.html",
        mime="text/html", use_container_width=True, type="secondary"
    )
    st.caption(
        "💡 Open in any mobile browser — clean display, no scrolling. "
        "Print button inside saves as PDF."
    )
