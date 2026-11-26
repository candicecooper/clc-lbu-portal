"""
CLC-LBU Leadership Planning Calendar 2027
-----------------------------------------
Confidential tile (shared confidential_auth.py password).

Leadership can log meetings, PD, SDDs and other commitments as
Proposed / Scheduled / Confirmed / Cancelled, with where they will occur,
then view each 2027 term week-by-week to plan ahead (starting with Term 1).

Supabase tables: leadership_planning_events, leadership_planning_drafts,
leadership_day_plans, leadership_plans, leadership_planning_files
(see leadership_planning_schema.sql, day_planner_table.sql, plans_and_documents.sql)
Storage bucket: leadership-planning (private) for uploaded documents.
Uses the main portal Supabase project (SUPABASE_URL / SUPABASE_KEY).
"""
from __future__ import annotations

import os
import io
import html
import uuid
from datetime import date, datetime, timedelta

import streamlit as st
from supabase import create_client, Client

from theme import apply_clc_theme
from confidential_auth import require_confidential_auth

try:
    from confidential_auth import confidential_logout_button
except Exception:  # keep the page working if the helper is renamed
    confidential_logout_button = None

st.set_page_config(
    page_title="Leadership Planning Calendar",
    page_icon="🗓️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_clc_theme()
require_confidential_auth("Leadership Planning Calendar", "🗓️")

PORTAL_URL = "https://clc-portal.pages.dev/"
st.sidebar.markdown(
    f'<a href="{PORTAL_URL}" target="_self" style="display:block;text-align:center;'
    f'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    f'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    f'🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True,
)
if confidential_logout_button:
    try:
        with st.sidebar:
            confidential_logout_button()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
TABLE = "leadership_planning_events"
YEAR = 2027

# SA Department for Education government school term dates 2027
TERMS = {
    1: (date(2027, 1, 27), date(2027, 4, 9)),
    2: (date(2027, 4, 26), date(2027, 7, 2)),
    3: (date(2027, 7, 19), date(2027, 9, 24)),
    4: (date(2027, 10, 11), date(2027, 12, 10)),
}

# SA public holidays 2027 that fall on weekdays (check/extend as needed)
PUBLIC_HOLIDAYS = {
    date(2027, 1, 1): "New Year's Day",
    date(2027, 1, 26): "Australia Day",
    date(2027, 3, 8): "Adelaide Cup Day",
    date(2027, 3, 26): "Good Friday",
    date(2027, 3, 29): "Easter Monday",
    date(2027, 6, 14): "King's Birthday",
    date(2027, 10, 4): "Labour Day",
}

EVENT_TYPES = [
    "Leadership meeting",
    "Staff meeting",
    "Professional development",
    "School development day",
    "Network / partner meeting",
    "External meeting",
    "Planning / admin",
    "Other",
]
TYPE_ICON = {
    "Leadership meeting": "👔",
    "Staff meeting": "👥",
    "Professional development": "🎓",
    "School development day": "🏫",
    "Network / partner meeting": "🤝",
    "External meeting": "🏢",
    "Planning / admin": "📋",
    "Other": "📌",
}

STATUSES = ["Proposed", "Scheduled", "Confirmed", "Cancelled"]
# background, text, border
STATUS_STYLE = {
    "Proposed": ("#FEF3C7", "#92400E", "#F59E0B"),
    "Scheduled": ("#DBEAFE", "#1E3A8A", "#3B82F6"),
    "Confirmed": ("#D1FAE5", "#065F46", "#10B981"),
    "Cancelled": ("#F1F5F9", "#64748B", "#94A3B8"),
}

LOCATION_MODES = ["On site – CLC", "Off site", "Online / Teams", "Hybrid", "TBC"]
LOCATION_ICON = {
    "On site – CLC": "🏠",
    "Off site": "📍",
    "Online / Teams": "💻",
    "Hybrid": "🔀",
    "TBC": "❔",
}

AUDIENCES = [
    "Leadership", "All staff", "Teachers", "SSOs",
    "JP team", "PY team", "SY team", "Admin", "External partners",
]

NO_TIME = "—"
TIME_SLOTS = [NO_TIME] + [
    f"{h:02d}:{m:02d}" for h in range(7, 19) for m in (0, 15, 30, 45)
]

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]

VIEW_CAL, VIEW_PLANS, VIEW_DAY = "📅 Term calendar", "📂 Plans", "🗒️ Day Planner"
VIEW_ADD, VIEW_LIST, VIEW_EXPORT = "➕ Add item", "📝 Review & edit", "⬇️ Export"
VIEWS = [VIEW_CAL, VIEW_PLANS, VIEW_DAY, VIEW_ADD, VIEW_LIST, VIEW_EXPORT]

# ══════════════════════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  .lp-header { background:linear-gradient(135deg,#1A7A7A,#0f5f5f);color:white;
    border-radius:12px;padding:1rem 1.4rem;margin-bottom:1rem; }
  .lp-header h1 { color:white;font-size:1.5rem;margin:0; }
  .lp-header p { margin:0.25rem 0 0 0;opacity:0.9;font-size:0.9rem; }
  .lp-legend { display:flex;flex-wrap:wrap;gap:0.5rem;margin:0.25rem 0 0.75rem 0; }
  .lp-pill { font-size:0.75rem;padding:2px 10px;border-radius:999px;border:1px solid;font-weight:600; }
  .lp-wrap { overflow-x:auto;width:100%; }
  table.lp-grid { border-collapse:collapse;width:100%;min-width:820px;table-layout:fixed; }
  table.lp-grid th { background:#0f5f5f;color:white;font-size:0.8rem;padding:6px;text-align:left; }
  table.lp-grid td { border:1px solid #e2e8f0;vertical-align:top;padding:4px 5px;
    min-height:70px;height:78px;font-size:0.78rem;background:white; }
  td.lp-week { background:#f0f7f7 !important;font-weight:700;color:#0f5f5f;width:92px; }
  td.lp-week span { display:block;font-weight:400;font-size:0.72rem;color:#475569; }
  td.lp-out { background:#f8fafc !important;color:#94a3b8; }
  td.lp-hol { background:#FDF2F8 !important; }
  .lp-daynum { font-size:0.72rem;color:#64748b;font-weight:600; }
  .lp-holname { font-size:0.7rem;color:#9D174D;font-weight:600; }
  .lp-chip { display:block;border-left:4px solid;border-radius:5px;padding:3px 5px;
    margin-top:3px;line-height:1.25;word-wrap:break-word; }
  .lp-chip b { font-weight:600; }
  .lp-chip .lp-meta { display:block;font-size:0.68rem;opacity:0.85; }
  .lp-cancel { text-decoration:line-through;opacity:0.7; }
  .lp-dayplan { display:block;margin-top:3px;font-size:0.68rem;color:#0f5f5f;
    background:#f0f7f7;border:1px dashed #1A7A7A;border-radius:5px;padding:2px 5px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase() -> Client | None:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not (url and key):
        try:
            url = st.secrets.get("SUPABASE_URL", "") or url
            key = st.secrets.get("SUPABASE_KEY", "") or key
        except Exception:
            pass
    if not (url and key):
        return None
    return create_client(url, key)


def _to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def load_events() -> tuple[list[dict], str | None]:
    sb = get_supabase()
    if sb is None:
        return [], "no_credentials"
    try:
        res = sb.table(TABLE).select("*").order("start_date").execute()
    except Exception as e:
        return [], str(e)
    rows = []
    for r in res.data or []:
        r["start_date"] = _to_date(r.get("start_date"))
        r["end_date"] = _to_date(r.get("end_date")) or r["start_date"]
        if r["start_date"] is None:
            continue
        rows.append(r)
    return rows, None


def save_event(data: dict, event_id: str | None = None) -> bool:
    sb = get_supabase()
    if sb is None:
        st.error("Supabase credentials not found.")
        return False
    payload = dict(data)
    payload["updated_at"] = _utcnow_iso()
    try:
        if event_id:
            sb.table(TABLE).update(payload).eq("id", event_id).execute()
        else:
            payload["id"] = str(uuid.uuid4())
            payload["created_at"] = payload["updated_at"]
            sb.table(TABLE).insert(payload).execute()
    except Exception as e:
        st.error(f"Could not save: {e}")
        return False
    load_events.clear()
    return True


def delete_event(event_id: str) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(TABLE).delete().eq("id", event_id).execute()
    except Exception as e:
        st.error(f"Could not delete: {e}")
        return False
    load_events.clear()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def term_weeks(term: int, include_pre_term: bool) -> list[tuple[str, date]]:
    """Return [(label, monday), ...] for a term."""
    start, end = TERMS[term]
    monday = start - timedelta(days=start.weekday())
    last_monday = end - timedelta(days=end.weekday())
    weeks = []
    if include_pre_term:
        weeks.append(("Pre-term", monday - timedelta(days=7)))
    n = 1
    while monday <= last_monday:
        weeks.append((f"Week {n}", monday))
        monday += timedelta(days=7)
        n += 1
    return weeks


def term_and_week_for(d: date) -> str:
    for t, (start, end) in TERMS.items():
        first_monday = start - timedelta(days=start.weekday())
        if first_monday - timedelta(days=7) <= d <= end:
            if d < first_monday:
                return f"T{t} pre-term"
            wk = (d - first_monday).days // 7 + 1
            return f"T{t} Wk {wk}"
    return "Holidays"


def fmt_date_range(r: dict) -> str:
    s, e = r["start_date"], r["end_date"]
    if e and e != s:
        return f"{s.strftime('%a %d %b')} – {e.strftime('%a %d %b')}"
    return s.strftime("%a %d %b %Y")


def fmt_time(r: dict) -> str:
    st_, en = r.get("start_time") or "", r.get("end_time") or ""
    if st_ and en:
        return f"{st_}–{en}"
    return st_ or ""


def fmt_location(r: dict) -> str:
    mode = r.get("location_mode") or ""
    loc = r.get("location") or ""
    if mode and loc:
        return f"{mode}: {loc}"
    return mode or loc or "TBC"


def chip_html(r: dict) -> str:
    bg, fg, border = STATUS_STYLE.get(r.get("status"), STATUS_STYLE["Proposed"])
    icon = TYPE_ICON.get(r.get("event_type"), "📌")
    loc_icon = LOCATION_ICON.get(r.get("location_mode"), "📍")
    cancel = " lp-cancel" if r.get("status") == "Cancelled" else ""
    time_txt = fmt_time(r)
    meta_bits = []
    if time_txt:
        meta_bits.append(html.escape(time_txt))
    meta_bits.append(f"{loc_icon} {html.escape(r.get('location') or r.get('location_mode') or 'TBC')}")
    title_attr = html.escape(
        f"{r.get('status')} · {r.get('event_type')}\n{fmt_location(r)}\n{r.get('summary') or ''}"
    )
    return (
        f'<span class="lp-chip{cancel}" title="{title_attr}" '
        f'style="background:{bg};color:{fg};border-color:{border};">'
        f'{icon} <b>{html.escape(r.get("title") or "")}</b>'
        f'<span class="lp-meta">{" · ".join(meta_bits)}</span></span>'
    )


def events_on(events: list[dict], d: date) -> list[dict]:
    hits = [r for r in events if r["start_date"] <= d <= r["end_date"]]
    return sorted(hits, key=lambda r: (r.get("start_time") or "99", r.get("title") or ""))


def render_term_grid(term: int, events: list[dict], include_pre_term: bool,
                     plan_days: dict | None = None) -> set[date]:
    start, end = TERMS[term]
    weeks = term_weeks(term, include_pre_term)
    shown: set[date] = set()
    rows = []
    for label, monday in weeks:
        cells = [
            f'<td class="lp-week">{label}<span>{monday.strftime("%d %b")}</span></td>'
        ]
        for i in range(5):
            d = monday + timedelta(days=i)
            shown.add(d)
            classes = []
            in_term = start <= d <= end
            if not in_term:
                classes.append("lp-out")
            hol = PUBLIC_HOLIDAYS.get(d)
            if hol:
                classes.append("lp-hol")
            inner = f'<div class="lp-daynum">{d.day} {d.strftime("%b")}'
            if not in_term and label != "Pre-term":
                inner += " · outside term"
            inner += "</div>"
            if hol:
                inner += f'<div class="lp-holname">🎌 {html.escape(hol)}</div>'
            inner += "".join(chip_html(r) for r in events_on(events, d))
            if plan_days and d in plan_days:
                tip = html.escape(plan_days[d] or "Day plan")
                inner += (f'<span class="lp-dayplan" title="{tip}">🗒️ Day plan'
                          + (f": {tip}" if plan_days[d] else "") + "</span>")
            cls = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{cls}>{inner}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    head = "<tr><th style='width:92px'>Week</th>" + "".join(
        f"<th>{n}</th>" for n in WEEKDAY_NAMES
    ) + "</tr>"
    st.markdown(
        f'<div class="lp-wrap"><table class="lp-grid">{head}{"".join(rows)}</table></div>',
        unsafe_allow_html=True,
    )
    return shown


def legend():
    pills = "".join(
        f'<span class="lp-pill" style="background:{bg};color:{fg};border-color:{bd};">{s}</span>'
        for s, (bg, fg, bd) in STATUS_STYLE.items()
    )
    pills += ('<span class="lp-pill" style="background:#FDF2F8;color:#9D174D;'
              'border-color:#F9A8D4;">Public holiday</span>')
    st.markdown(f'<div class="lp-legend">{pills}</div>', unsafe_allow_html=True)


def build_docx(term: int, events: list[dict]) -> bytes | None:
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.enum.section import WD_ORIENT
    except Exception:
        return None

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.5))

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9.5)

    start, end = TERMS[term]
    h = doc.add_heading(f"CLC-LBU Leadership Planning — Term {term} {YEAR}", level=1)
    h.runs[0].font.color.rgb = RGBColor(0x1A, 0x7A, 0x7A)
    doc.add_paragraph(
        f"Term dates: {start.strftime('%a %d %b')} – {end.strftime('%a %d %b %Y')}   ·   "
        f"CONFIDENTIAL — leadership only   ·   Exported {date.today().strftime('%d %b %Y')}"
    )

    if not events:
        doc.add_paragraph("No items entered for this term yet.")
    else:
        cols = ["When", "Time", "Item", "Type", "Status", "Where", "Audience", "Lead", "Summary / next action"]
        table = doc.add_table(rows=1, cols=len(cols))
        table.style = "Light Grid Accent 1"
        for i, c in enumerate(cols):
            table.rows[0].cells[i].text = c
            for p in table.rows[0].cells[i].paragraphs:
                for run in p.runs:
                    run.font.bold = True
        for r in events:
            summary = r.get("summary") or ""
            if r.get("next_action"):
                owner = f" ({r['action_owner']})" if r.get("action_owner") else ""
                summary = (summary + "\n" if summary else "") + f"Next: {r['next_action']}{owner}"
            vals = [
                f"{term_and_week_for(r['start_date'])}\n{fmt_date_range(r)}",
                fmt_time(r),
                r.get("title") or "",
                r.get("event_type") or "",
                r.get("status") or "",
                fmt_location(r),
                r.get("audience") or "",
                r.get("lead") or "",
                summary,
            ]
            cells = table.add_row().cells
            for i, v in enumerate(vals):
                cells[i].text = v

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_csv(events: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Term/Week", "Start date", "End date", "Start time", "End time", "Title", "Type",
                "Status", "Location type", "Location", "Audience", "Lead", "Summary",
                "Next action", "Action owner", "Entered by"])
    for r in events:
        w.writerow([
            term_and_week_for(r["start_date"]), r["start_date"], r["end_date"],
            r.get("start_time") or "", r.get("end_time") or "", r.get("title") or "",
            r.get("event_type") or "", r.get("status") or "", r.get("location_mode") or "",
            r.get("location") or "", r.get("audience") or "", r.get("lead") or "",
            r.get("summary") or "", r.get("next_action") or "", r.get("action_owner") or "",
            r.get("created_by") or "",
        ])
    return buf.getvalue().encode("utf-8-sig")


# ══════════════════════════════════════════════════════════════════════════════
# FORM (used for both new entries and edits)
#
# Why it's built this way (so details are never lost):
#  • Each form runs as a Streamlit *fragment*: typing/choosing in it only
#    refreshes that form, never the whole page or calendar.
#  • Values live in session_state under stable keys, so filters, tab changes
#    or other reruns never wipe what's been typed.
#  • Every field change auto-saves a draft to Supabase
#    (leadership_planning_drafts). If the session drops (laptop sleeps,
#    Render reconnects, password re-prompt), the draft is restored.
#  • A failed save or missing title keeps everything on screen.
#  • The draft is only cleared after a successful save, or on "Discard".
# ══════════════════════════════════════════════════════════════════════════════
DRAFT_TABLE = "leadership_planning_drafts"
FIELDS = ["title", "etype", "status", "sdate", "edate", "stime", "etime", "lmode",
          "loc", "aud", "lead", "summary", "next", "owner", "by"]

try:
    from zoneinfo import ZoneInfo
    _ADL = ZoneInfo("Australia/Adelaide")
except Exception:
    _ADL = None

_fragment = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None)
if _fragment is None:
    def _fragment(func):  # older Streamlit: run as normal
        return func


def _utcnow_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat()


def _now_hm() -> str:
    return (datetime.now(_ADL) if _ADL else datetime.now()).strftime("%I:%M %p").lstrip("0")


def _fmt_ts(value) -> str:
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (ts.astimezone(_ADL) if _ADL else ts).strftime("%a %d %b, %I:%M %p")
    except Exception:
        return ""


def load_drafts() -> dict:
    """All saved drafts keyed by draft_key. Missing table → feature quietly off."""
    if st.session_state.get("lp_drafts_unavailable"):
        return {}
    sb = get_supabase()
    if sb is None:
        return {}
    try:
        res = sb.table(DRAFT_TABLE).select("*").execute()
        return {r["draft_key"]: r for r in (res.data or [])}
    except Exception:
        st.session_state["lp_drafts_unavailable"] = True
        return {}


def _collect(prefix: str) -> dict:
    out = {}
    for f in FIELDS:
        v = st.session_state.get(f"{prefix}_{f}")
        if isinstance(v, date):
            v = v.isoformat()
        out[f] = v
    return out


def _autosave(prefix: str, draft_key: str):
    if st.session_state.get("lp_drafts_unavailable"):
        return
    sb = get_supabase()
    if sb is None:
        return
    try:
        sb.table(DRAFT_TABLE).upsert({
            "draft_key": draft_key,
            "data": _collect(prefix),
            "saved_by": (st.session_state.get(f"{prefix}_by")
                         or st.session_state.get("lp_entered_by") or None),
            "updated_at": _utcnow_iso(),
        }).execute()
        st.session_state[f"{prefix}_saved_at"] = _now_hm()
    except Exception:
        st.session_state["lp_drafts_unavailable"] = True


def _delete_draft(draft_key: str):
    sb = get_supabase()
    if sb is None or st.session_state.get("lp_drafts_unavailable"):
        return
    try:
        sb.table(DRAFT_TABLE).delete().eq("draft_key", draft_key).execute()
    except Exception:
        pass


def _defaults(ex: dict) -> dict:
    s = ex.get("start_date") or st.session_state.get("lp_prefill_date") or TERMS[1][0]
    return {
        "title": ex.get("title") or "",
        "etype": ex.get("event_type") if ex.get("event_type") in EVENT_TYPES else EVENT_TYPES[0],
        "status": ex.get("status") if ex.get("status") in STATUSES else STATUSES[0],
        "sdate": s,
        "edate": ex.get("end_date") or s,
        "stime": ex.get("start_time") if ex.get("start_time") in TIME_SLOTS else NO_TIME,
        "etime": ex.get("end_time") if ex.get("end_time") in TIME_SLOTS else NO_TIME,
        "lmode": ex.get("location_mode") if ex.get("location_mode") in LOCATION_MODES else LOCATION_MODES[0],
        "loc": ex.get("location") or "",
        "aud": [a.strip() for a in (ex.get("audience") or "").split(",") if a.strip() in AUDIENCES],
        "lead": ex.get("lead") or "",
        "summary": ex.get("summary") or "",
        "next": ex.get("next_action") or "",
        "owner": ex.get("action_owner") or "",
        "by": ex.get("created_by") or st.session_state.get("lp_entered_by", ""),
    }


def _clean_draft_values(data: dict, base: dict) -> dict:
    vals = dict(base)
    for k, v in (data or {}).items():
        if k not in vals or v is None:
            continue
        if k in ("sdate", "edate"):
            v = _to_date(v) or vals[k]
        elif k == "etype" and v not in EVENT_TYPES:
            continue
        elif k == "status" and v not in STATUSES:
            continue
        elif k in ("stime", "etime") and v not in TIME_SLOTS:
            continue
        elif k == "lmode" and v not in LOCATION_MODES:
            continue
        elif k == "aud":
            v = [a for a in (v or []) if a in AUDIENCES]
        vals[k] = v
    return vals


def _init_form(prefix: str, ex: dict, draft: dict | None):
    # A pending reset (after a successful save / discard) clears keys
    # before any widget is created on this run.
    if st.session_state.pop(f"{prefix}_reset", False):
        for f in FIELDS:
            st.session_state.pop(f"{prefix}_{f}", None)
        for extra in ("init", "restored", "saved_at"):
            st.session_state.pop(f"{prefix}_{extra}", None)
        draft = None
    if st.session_state.get(f"{prefix}_init"):
        return
    vals = _defaults(ex)
    if draft and draft.get("data"):
        vals = _clean_draft_values(draft["data"], vals)
    if draft and draft.get("data") and not st.session_state.get("lp_quiet_restore"):
        who = f" by {draft['saved_by']}" if draft.get("saved_by") else ""
        st.session_state[f"{prefix}_restored"] = f"{_fmt_ts(draft.get('updated_at'))}{who}".strip()
    for k, v in vals.items():
        st.session_state[f"{prefix}_{k}"] = v
    st.session_state[f"{prefix}_init"] = True


@_fragment
def render_event_form(prefix: str, existing: dict | None = None, draft: dict | None = None):
    ex = existing or {}
    is_edit = existing is not None
    draft_key = f"edit:{ex['id']}" if is_edit else "new"
    _init_form(prefix, ex, draft)

    def autosave():
        _autosave(prefix, draft_key)

    restored = st.session_state.get(f"{prefix}_restored")
    if restored:
        st.info(f"↩️ Restored unsaved {'changes' if is_edit else 'draft'} from {restored}. "
                "Check the details, then save.")

    st.text_input("Title *", key=f"{prefix}_title", on_change=autosave,
                  placeholder="e.g. Term 1 leadership planning day")
    c1, c2 = st.columns(2)
    c1.selectbox("Type", EVENT_TYPES, key=f"{prefix}_etype", on_change=autosave)
    c2.selectbox("Status", STATUSES, key=f"{prefix}_status", on_change=autosave)

    c1, c2, c3, c4 = st.columns(4)
    c1.date_input("Start date *", key=f"{prefix}_sdate", format="DD/MM/YYYY", on_change=autosave)
    c2.date_input("End date (multi-day)", key=f"{prefix}_edate", format="DD/MM/YYYY",
                  on_change=autosave, help="Leave the same as the start date for a one-day item.")
    c3.selectbox("Start time", TIME_SLOTS, key=f"{prefix}_stime", on_change=autosave)
    c4.selectbox("End time", TIME_SLOTS, key=f"{prefix}_etime", on_change=autosave)

    c1, c2 = st.columns([1, 2])
    c1.selectbox("Where", LOCATION_MODES, key=f"{prefix}_lmode", on_change=autosave)
    c2.text_input("Venue / room / link details", key=f"{prefix}_loc", on_change=autosave,
                  placeholder="e.g. Staff room, LBU head office, Teams link to follow")

    c1, c2 = st.columns([2, 1])
    c1.multiselect("Who's involved", AUDIENCES, key=f"{prefix}_aud", on_change=autosave)
    c2.text_input("Lead / facilitator", key=f"{prefix}_lead", on_change=autosave)

    st.text_area("Summary details", key=f"{prefix}_summary", height=110, on_change=autosave,
                 placeholder="Purpose, focus, key details, bookings or costs to note…")
    c1, c2 = st.columns([2, 1])
    c1.text_input("Next action to progress this", key=f"{prefix}_next", on_change=autosave,
                  placeholder="e.g. Confirm venue with presenter")
    c2.text_input("Action owner", key=f"{prefix}_owner", on_change=autosave)

    if not is_edit:
        st.text_input("Entered by", key=f"{prefix}_by", on_change=autosave)

    b1, b2, b3 = st.columns([1.3, 1, 2.2])
    save_clicked = b1.button("💾 Save changes" if is_edit else "➕ Add to calendar",
                             type="primary", key=f"{prefix}_save", use_container_width=True)
    discard_clicked = b2.button("↺ Discard changes" if is_edit else "🧹 Clear form",
                                key=f"{prefix}_discard", use_container_width=True)
    if st.session_state.get("lp_drafts_unavailable"):
        b3.caption("⚠️ Draft auto-save is off — run the updated schema SQL to turn it on.")
    elif st.session_state.get(f"{prefix}_saved_at"):
        b3.caption(f"✓ Draft auto-saved {st.session_state[f'{prefix}_saved_at']}")
    else:
        b3.caption("Drafts auto-save as you move between fields.")

    if discard_clicked:
        _delete_draft(draft_key)
        st.session_state[f"{prefix}_reset"] = True
        st.rerun()

    if save_clicked:
        v = _collect(prefix)
        sdate, edate = _to_date(v["sdate"]), _to_date(v["edate"])
        if not (v["title"] or "").strip():
            st.warning("Please give the item a title — everything else you've typed is still here.")
            return
        if sdate and edate and edate < sdate:
            st.warning("End date can't be before the start date.")
            return
        if v.get("by"):
            st.session_state["lp_entered_by"] = v["by"].strip()
        data = {
            "title": v["title"].strip(),
            "event_type": v["etype"],
            "status": v["status"],
            "start_date": sdate.isoformat(),
            "end_date": (edate or sdate).isoformat(),
            "start_time": None if v["stime"] == NO_TIME else v["stime"],
            "end_time": None if v["etime"] == NO_TIME else v["etime"],
            "location_mode": v["lmode"],
            "location": (v["loc"] or "").strip() or None,
            "audience": ", ".join(v["aud"] or []) or None,
            "lead": (v["lead"] or "").strip() or None,
            "summary": (v["summary"] or "").strip() or None,
            "next_action": (v["next"] or "").strip() or None,
            "action_owner": (v["owner"] or "").strip() or None,
        }
        if not is_edit:
            data["created_by"] = (v.get("by") or "").strip() or None
        if save_event(data, ex.get("id")):  # on failure the error shows and fields stay
            _delete_draft(draft_key)
            st.session_state[f"{prefix}_reset"] = True
            st.session_state["lp_flash"] = ("Changes saved." if is_edit
                                            else f"Added “{data['title']}” to the calendar.")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DAY PLANNER (sandbox) — pick any date, build up the day freely
#
#  • Everything for a date lives in one row of leadership_day_plans.
#  • Runs as a fragment and auto-saves to Supabase whenever anything changes
#    (on leaving a text box, or after each table edit) — no Save button to forget.
#  • Calendar items already booked on that date are shown alongside.
# ══════════════════════════════════════════════════════════════════════════════
DAY_TABLE = "leadership_day_plans"
TT_COLS = ["start", "end", "activity", "who", "where", "notes"]
LINK_COLS = ["label", "url", "note"]
TASK_COLS = ["done", "task", "owner"]


@st.cache_data(ttl=60, show_spinner=False)
def load_day_plan_index() -> dict:
    """{date: focus} for every saved day plan — used to flag days on the grid."""
    sb = get_supabase()
    if sb is None:
        return {}
    try:
        res = sb.table(DAY_TABLE).select("plan_date,focus").execute()
    except Exception:
        return {}
    out = {}
    for r in res.data or []:
        d = _to_date(r.get("plan_date"))
        if d:
            out[d] = r.get("focus") or ""
    return out


def load_day_plan(d: date) -> tuple[dict | None, str | None]:
    sb = get_supabase()
    if sb is None:
        return None, "no_credentials"
    try:
        res = sb.table(DAY_TABLE).select("*").eq("plan_date", d.isoformat()).execute()
    except Exception as e:
        return None, str(e)
    rows = res.data or []
    return (rows[0] if rows else None), None


def save_day_plan(d: date, payload: dict) -> str | None:
    sb = get_supabase()
    if sb is None:
        return "Supabase credentials not found."
    row = dict(payload)
    row["plan_date"] = d.isoformat()
    row["updated_at"] = _utcnow_iso()
    try:
        sb.table(DAY_TABLE).upsert(row).execute()
    except Exception as e:
        return str(e)
    load_day_plan_index.clear()
    return None


def delete_day_plan(d: date) -> str | None:
    sb = get_supabase()
    if sb is None:
        return "Supabase credentials not found."
    try:
        sb.table(DAY_TABLE).delete().eq("plan_date", d.isoformat()).execute()
    except Exception as e:
        return str(e)
    load_day_plan_index.clear()
    return None


def _rows(df_or_list, cols: list[str]) -> list[dict]:
    """Clean editor output → list of dicts, dropping fully blank rows."""
    try:
        records = df_or_list.to_dict("records")
    except AttributeError:
        records = list(df_or_list or [])
    out = []
    for r in records:
        row = {}
        for c in cols:
            v = r.get(c)
            if c == "done":
                v = bool(v) if v == v and v is not None else False  # NaN-safe
            else:
                v = "" if v is None or v != v else str(v).strip()
                if c in ("start", "end") and v == NO_TIME:
                    v = ""
            row[c] = v
        if any(row[c] for c in cols if c != "done"):
            out.append(row)
    return out


def _df(rows: list[dict], cols: list[str]):
    import pandas as pd
    clean = []
    for r in rows or []:
        clean.append({c: (bool(r.get(c)) if c == "done" else (r.get(c) or "")) for c in cols})
    if not clean:
        return pd.DataFrame({c: pd.Series(dtype="bool" if c == "done" else "object") for c in cols})
    return pd.DataFrame(clean, columns=cols)


def _sort_tt(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r.get("start") or "99:99", r.get("end") or ""))


def _template_rows() -> list[dict]:
    return [{"start": f"{h:02d}:00", "end": f"{h + 1:02d}:00", "activity": "",
             "who": "", "where": "", "notes": ""} for h in range(8, 16)]


def build_day_docx(d: date, plan: dict, day_events: list[dict]) -> bytes | None:
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
    except Exception:
        return None
    doc = Document()
    sec = doc.sections[0]
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.8))
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    h = doc.add_heading(f"Day Plan — {d.strftime('%A %d %B %Y')}", level=1)
    h.runs[0].font.color.rgb = RGBColor(0x1A, 0x7A, 0x7A)
    doc.add_paragraph(f"{term_and_week_for(d)}   ·   CONFIDENTIAL — leadership only")
    if plan.get("focus"):
        p = doc.add_paragraph()
        p.add_run("Focus: ").bold = True
        p.add_run(plan["focus"])
    if plan.get("location"):
        p = doc.add_paragraph()
        p.add_run("Where: ").bold = True
        p.add_run(plan["location"])

    if day_events:
        doc.add_heading("Calendar items", level=2)
        for r in day_events:
            doc.add_paragraph(f"{fmt_time(r) or 'All day'} — {r.get('title')} "
                              f"({r.get('status')}, {fmt_location(r)})", style="List Bullet")

    tt = _sort_tt(plan.get("timetable") or [])
    if tt:
        doc.add_heading("Timetable", level=2)
        t = doc.add_table(rows=1, cols=5)
        t.style = "Light Grid Accent 1"
        for i, c in enumerate(["Time", "Activity", "Who", "Where", "Notes"]):
            t.rows[0].cells[i].text = c
        for r in tt:
            cells = t.add_row().cells
            time_txt = "–".join(x for x in (r.get("start"), r.get("end")) if x)
            for i, v in enumerate([time_txt, r.get("activity"), r.get("who"), r.get("where"), r.get("notes")]):
                cells[i].text = v or ""

    if plan.get("notes"):
        doc.add_heading("Notes", level=2)
        for line in plan["notes"].splitlines():
            doc.add_paragraph(line)

    tasks = plan.get("tasks") or []
    if tasks:
        doc.add_heading("To do", level=2)
        for r in tasks:
            owner = f" ({r['owner']})" if r.get("owner") else ""
            doc.add_paragraph(f"{'☑' if r.get('done') else '☐'} {r.get('task')}{owner}")

    links = plan.get("links") or []
    if links:
        doc.add_heading("Links", level=2)
        for r in links:
            note = f" — {r['note']}" if r.get("note") else ""
            doc.add_paragraph(f"{r.get('label') or r.get('url')}: {r.get('url')}{note}", style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _dp_load_into_state(d: date):
    """Load a date's plan into session_state once (re-load only when asked)."""
    k = d.isoformat()
    if st.session_state.get("dp_loaded_date") == k:
        return
    plan, err = load_day_plan(d)
    st.session_state["dp_load_error"] = err
    if err:
        # Don't mark this date as loaded, so it retries on the next interaction
        st.session_state.pop("dp_loaded_date", None)
        return
    plan = plan or {}
    st.session_state["dp_loaded_date"] = k
    st.session_state["dp_focus"] = plan.get("focus") or ""
    st.session_state["dp_location"] = plan.get("location") or ""
    st.session_state["dp_notes"] = plan.get("notes") or ""
    st.session_state["dp_tt_base"] = _sort_tt(plan.get("timetable") or [])
    st.session_state["dp_links_base"] = plan.get("links") or []
    st.session_state["dp_tasks_base"] = plan.get("tasks") or []
    st.session_state["dp_ver"] = st.session_state.get("dp_ver", 0) + 1  # fresh editor keys
    st.session_state["dp_last_saved"] = _dp_payload_from(plan) if plan else None
    st.session_state["dp_saved_note"] = (
        f"Last saved {_fmt_ts(plan.get('updated_at'))}"
        + (f" by {plan['updated_by']}" if plan.get("updated_by") else "")
    ) if plan else ""


def _dp_payload_from(plan: dict) -> dict:
    return {
        "focus": (plan.get("focus") or "").strip(),
        "location": (plan.get("location") or "").strip(),
        "notes": plan.get("notes") or "",
        "timetable": _rows(plan.get("timetable") or [], TT_COLS),
        "links": _rows(plan.get("links") or [], LINK_COLS),
        "tasks": _rows(plan.get("tasks") or [], TASK_COLS),
    }


def _dp_reset_editors(tt=None, links=None, tasks=None):
    if tt is not None:
        st.session_state["dp_tt_base"] = tt
    if links is not None:
        st.session_state["dp_links_base"] = links
    if tasks is not None:
        st.session_state["dp_tasks_base"] = tasks
    st.session_state["dp_ver"] = st.session_state.get("dp_ver", 0) + 1


def _dp_rerun():
    try:
        st.rerun(scope="fragment")
    except Exception:
        st.rerun()


@_fragment
def render_day_planner(events: list[dict]):
    c1, c2, c3 = st.columns([1.2, 1.6, 1.2])
    with c1:
        d = st.date_input("Pick a date", key="dp_date", format="DD/MM/YYYY")
    st.session_state["dp_date_keep"] = d
    plan_index = load_day_plan_index()
    with c2:
        upcoming = sorted(x for x in plan_index if x >= date.today())
        if upcoming:
            st.markdown("**Days with a plan**")
            st.caption(" · ".join(x.strftime("%a %d %b") for x in upcoming[:8])
                       + (" …" if len(upcoming) > 8 else ""))
    with c3:
        st.markdown(f"**{d.strftime('%A %d %B %Y')}**")
        hol = PUBLIC_HOLIDAYS.get(d)
        st.caption(term_and_week_for(d) + (f" · 🎌 {hol}" if hol else "")
                   + (" · weekend" if d.weekday() >= 5 else ""))

    _dp_load_into_state(d)
    if st.session_state.get("dp_load_error"):
        e = st.session_state["dp_load_error"]
        if "does not exist" in e or "PGRST205" in e or "schema cache" in e:
            st.error(f"The `{DAY_TABLE}` table hasn't been found yet — run the Day Planner SQL "
                     "in Supabase (same project as the calendar), then press Retry.")
        else:
            st.error(f"Could not load this day: {e}")
        if st.button("🔄 Retry", key="dp_retry"):
            _dp_rerun()
        return

    day_events = events_on(events, d)
    if day_events:
        st.markdown("**Already on the calendar this day**")
        st.markdown("".join(chip_html(r) for r in day_events), unsafe_allow_html=True)
    all_plans, _perr = load_plans()
    linked_plans = plans_for_date(all_plans, d) if not _perr else []
    if linked_plans:
        st.markdown("**Part of plan:**")
        cols = st.columns(min(len(linked_plans), 4))
        for i, p in enumerate(linked_plans):
            if cols[i % len(cols)].button(f"📂 {p.get('title') or 'Untitled'}", key=f"dp_goplan_{p['id']}",
                                          help="Open this plan's overview"):
                go_to(VIEW_PLANS, p["id"])

    b1, b2, b3 = st.columns([1.3, 1.6, 1])
    if b1.button("➕ Add a calendar item on this date", key="dp_add_item"):
        st.session_state["lp_prefill_date"] = d
        st.session_state["lp_new_reset"] = True
        go_to(VIEW_ADD)
    unlinked = [p for p in all_plans if p not in linked_plans] if not _perr else []
    if unlinked:
        names = {p["id"]: p.get("title") or "Untitled" for p in unlinked}
        pick = b2.selectbox("Link this day to a plan", [""] + list(names), key=f"dp_linkpick_{d.isoformat()}",
                            format_func=lambda x: names.get(x, "Link this day to a plan…"),
                            label_visibility="collapsed")
        if b3.button("🔗 Link", key="dp_link_btn", disabled=not pick):
            p = next(x for x in unlinked if x["id"] == pick)
            e = update_plan(pick, {"linked_dates": sorted(set((p.get("linked_dates") or []) + [d.isoformat()]))})
            if e:
                st.error(f"Could not link: {e}")
            else:
                st.session_state.pop("pl_loaded_id", None)
                _dp_rerun()

    st.divider()
    c1, c2 = st.columns([2, 1])
    c1.text_input("Focus / title for the day", key="dp_focus",
                  placeholder="e.g. Pupil-free day — Reflection Loops + Term 1 planning")
    c2.text_input("Where", key="dp_location", placeholder="e.g. CLC staff room / Teams")

    ver = st.session_state.get("dp_ver", 0)

    # ── Timetable ──
    st.markdown("#### 🕘 Timetable")
    t1, t2, t3 = st.columns([1.3, 1.3, 3])
    if t1.button("Add hourly slots 8–4", key="dp_tpl",
                 help="Adds blank hour slots you can fill in, rename or delete."):
        current = _rows(st.session_state.get(f"dp_tt_out_{ver}", st.session_state["dp_tt_base"]), TT_COLS)
        have = {r["start"] for r in current}
        _dp_reset_editors(tt=_sort_tt(current + [r for r in _template_rows() if r["start"] not in have]))
        _dp_rerun()
    if t2.button("Sort by time", key="dp_sort"):
        current = _rows(st.session_state.get(f"dp_tt_out_{ver}", st.session_state["dp_tt_base"]), TT_COLS)
        _dp_reset_editors(tt=_sort_tt(current))
        _dp_rerun()
    t3.caption("Click a cell to type. Use the + row at the bottom to add; tick a row's box and press 🗑 to remove.")

    tt_df = st.data_editor(
        _df(st.session_state["dp_tt_base"], TT_COLS),
        key=f"dp_tt_{ver}", num_rows="dynamic", use_container_width=True, hide_index=True,
        column_config={
            "start": st.column_config.SelectboxColumn("Start", options=TIME_SLOTS[1:], width="small"),
            "end": st.column_config.SelectboxColumn("End", options=TIME_SLOTS[1:], width="small"),
            "activity": st.column_config.TextColumn("Activity", width="large"),
            "who": st.column_config.TextColumn("Who"),
            "where": st.column_config.TextColumn("Where"),
            "notes": st.column_config.TextColumn("Notes", width="medium"),
        },
    )
    st.session_state[f"dp_tt_out_{ver}"] = tt_df

    # ── Notes ──
    st.markdown("#### 📝 Notes & information")
    n1, n2 = st.tabs(["✏️ Write", "👁 Preview"])
    with n1:
        st.text_area("Notes", key="dp_notes", height=220, label_visibility="collapsed",
                     placeholder="Anything for the day — agenda, reminders, who's covering, room set-up…\n"
                                 "Tip: start lines with - for bullets, **bold** for emphasis, "
                                 "and paste links straight in.")
    with n2:
        if st.session_state.get("dp_notes"):
            st.markdown(st.session_state["dp_notes"])
        else:
            st.caption("Nothing written yet.")

    c1, c2 = st.columns(2)
    # ── Links ──
    with c1:
        st.markdown("#### 🔗 Links & documents")
        links_df = st.data_editor(
            _df(st.session_state["dp_links_base"], LINK_COLS),
            key=f"dp_links_{ver}", num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "label": st.column_config.TextColumn("Name"),
                "url": st.column_config.LinkColumn("Link (paste URL)", width="medium",
                                                   validate=r"^https?://.+"),
                "note": st.column_config.TextColumn("Note"),
            },
        )
        clickable = [r for r in _rows(links_df, LINK_COLS) if r["url"].startswith("http")]
        if clickable:
            st.markdown("  \n".join(f"🔗 [{r['label'] or r['url']}]({r['url']})" for r in clickable))
    # ── To-do ──
    with c2:
        st.markdown("#### ✅ To do for this day")
        tasks_df = st.data_editor(
            _df(st.session_state["dp_tasks_base"], TASK_COLS),
            key=f"dp_tasks_{ver}", num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "done": st.column_config.CheckboxColumn("✓", width="small", default=False),
                "task": st.column_config.TextColumn("Task", width="large"),
                "owner": st.column_config.TextColumn("Who"),
            },
        )

    # ── Auto-save ──
    payload = {
        "focus": (st.session_state.get("dp_focus") or "").strip(),
        "location": (st.session_state.get("dp_location") or "").strip(),
        "notes": st.session_state.get("dp_notes") or "",
        "timetable": _rows(tt_df, TT_COLS),
        "links": _rows(links_df, LINK_COLS),
        "tasks": _rows(tasks_df, TASK_COLS),
    }
    is_blank = not any([payload["focus"], payload["location"], payload["notes"].strip(),
                        payload["timetable"], payload["links"], payload["tasks"]])
    last = st.session_state.get("dp_last_saved")
    if payload != last and not (is_blank and last is None):
        who = st.session_state.get("lp_entered_by") or None
        err = save_day_plan(d, {**payload, "updated_by": who})
        if err:
            if "does not exist" in err or "PGRST205" in err or "schema cache" in err:
                st.error(f"Not saved — the `{DAY_TABLE}` table hasn't been created yet. "
                         "Run the updated schema SQL; what you've typed stays on screen.")
            else:
                st.error(f"Not saved yet ({err}). What you've typed stays on screen — "
                         "it will retry on your next change.")
        else:
            st.session_state["dp_last_saved"] = payload
            st.session_state["dp_saved_note"] = f"✓ Auto-saved {_now_hm()}"

    st.markdown("#### 📎 Documents for this day")
    render_documents("day", d.isoformat(), f"dpdoc_{d.isoformat()}", _dp_rerun)

    st.divider()
    f1, f2, f3 = st.columns([2, 1.4, 1.4])
    f1.caption(st.session_state.get("dp_saved_note") or "Auto-saves as you go — nothing to press.")
    with f2:
        docx_bytes = build_day_docx(d, payload, day_events)
        if docx_bytes:
            st.download_button("📄 Day plan (Word)", data=docx_bytes,
                               file_name=f"CLC_Day_Plan_{d.isoformat()}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True, key="dp_dl")
    with f3:
        with st.popover("More…", use_container_width=True):
            copy_to = st.date_input("Copy this plan to", key=f"dp_copy_to_{d.isoformat()}",
                                    format="DD/MM/YYYY", value=d + timedelta(days=7))
            if st.button("📋 Copy", key="dp_copy_btn", disabled=is_blank):
                existing, _ = load_day_plan(copy_to)
                if existing and not st.session_state.get("dp_copy_ok"):
                    st.session_state["dp_copy_ok"] = True
                    st.warning(f"{copy_to.strftime('%a %d %b')} already has a plan — press Copy again to replace it.")
                else:
                    st.session_state.pop("dp_copy_ok", None)
                    err = save_day_plan(copy_to, {**payload, "updated_by": st.session_state.get("lp_entered_by")})
                    if err:
                        st.error(f"Could not copy: {err}")
                    else:
                        st.success(f"Copied to {copy_to.strftime('%a %d %b %Y')}.")
            st.divider()
            if not st.session_state.get("dp_del_confirm"):
                if st.button("🗑️ Clear this day's plan", key="dp_del", disabled=last is None):
                    st.session_state["dp_del_confirm"] = True
                    _dp_rerun()
            else:
                st.warning("Delete everything planned for this day, including its documents?")
                if st.button("Yes, clear it", key="dp_del_yes", type="primary"):
                    st.session_state.pop("dp_del_confirm", None)
                    delete_all_files("day", d.isoformat())
                    err = delete_day_plan(d)
                    if err:
                        st.error(f"Could not delete: {err}")
                    else:
                        st.session_state.pop("dp_loaded_date", None)
                        _dp_rerun()
                if st.button("Keep it", key="dp_del_no"):
                    st.session_state.pop("dp_del_confirm", None)
                    _dp_rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS — shared upload/list component (Plans + Day Planner)
#
#  • Files go to the private Supabase Storage bucket `leadership-planning`.
#  • A row per file in leadership_planning_files records what it belongs to
#    (parent_type = 'plan' | 'day', parent_key = plan id | ISO date).
#  • Links are short-lived signed URLs, so nothing is publicly reachable.
# ══════════════════════════════════════════════════════════════════════════════
BUCKET = "leadership-planning"
FILES_TABLE = "leadership_planning_files"
MAX_UPLOAD_MB = 50  # Supabase Storage default per-file limit

FILE_ICONS = {
    "pdf": "📕", "doc": "📘", "docx": "📘", "xls": "📗", "xlsx": "📗", "csv": "📗",
    "ppt": "📙", "pptx": "📙", "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️", "gif": "🖼️",
    "txt": "📄", "zip": "🗜️", "mp4": "🎞️", "mov": "🎞️", "mp3": "🎧", "m4a": "🎧",
}


def _is_missing(err: str | None) -> bool:
    e = (err or "").lower()
    return any(s in e for s in ("does not exist", "pgrst205", "schema cache", "bucket not found",
                                "not found"))


def _human_size(n) -> str:
    try:
        n = float(n or 0)
    except Exception:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def list_files(parent_type: str, parent_key: str) -> tuple[list[dict], str | None]:
    sb = get_supabase()
    if sb is None:
        return [], "Supabase credentials not found."
    try:
        res = (sb.table(FILES_TABLE).select("*")
               .eq("parent_type", parent_type).eq("parent_key", parent_key).execute())
    except Exception as e:
        return [], str(e)
    rows = res.data or []
    return sorted(rows, key=lambda r: str(r.get("uploaded_at") or "")), None


@st.cache_data(ttl=60, show_spinner=False)
def file_counts(parent_type: str) -> dict:
    """{parent_key: number of files} for one parent type."""
    sb = get_supabase()
    if sb is None:
        return {}
    try:
        res = sb.table(FILES_TABLE).select("parent_key").eq("parent_type", parent_type).execute()
    except Exception:
        return {}
    out: dict = {}
    for r in res.data or []:
        out[r["parent_key"]] = out.get(r["parent_key"], 0) + 1
    return out


@st.cache_data(ttl=3000, show_spinner=False)
def signed_url(path: str) -> str | None:
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = sb.storage.from_(BUCKET).create_signed_url(path, 3600)
    except Exception:
        return None
    if isinstance(res, dict):
        return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
    return getattr(res, "signed_url", None) or getattr(res, "signedURL", None)


def upload_files(parent_type: str, parent_key: str, files: list) -> list[str]:
    """Upload each file; returns a list of error messages (empty = all good)."""
    import re
    sb = get_supabase()
    if sb is None:
        return ["Supabase credentials not found."]
    errors = []
    who = st.session_state.get("lp_entered_by") or None
    for f in files:
        size = getattr(f, "size", None) or len(f.getvalue())
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            errors.append(f"{f.name}: larger than {MAX_UPLOAD_MB} MB — save it to OneDrive/SharePoint "
                          "and add it as a link instead.")
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f.name).strip("_")[:120] or "file"
        path = f"{parent_type}/{parent_key}/{uuid.uuid4().hex[:8]}_{safe}"
        mime = f.type or "application/octet-stream"
        try:
            sb.storage.from_(BUCKET).upload(path, f.getvalue(),
                                            {"content-type": mime, "upsert": "false"})
        except Exception as e:
            errors.append(f"{f.name}: {e}")
            continue
        try:
            sb.table(FILES_TABLE).insert({
                "id": str(uuid.uuid4()),
                "parent_type": parent_type,
                "parent_key": parent_key,
                "file_name": f.name,
                "storage_path": path,
                "mime_type": mime,
                "size_bytes": size,
                "uploaded_by": who,
                "uploaded_at": _utcnow_iso(),
            }).execute()
        except Exception as e:
            errors.append(f"{f.name}: uploaded but not recorded ({e})")
            try:
                sb.storage.from_(BUCKET).remove([path])
            except Exception:
                pass
    file_counts.clear()
    return errors


def delete_file(row: dict) -> str | None:
    sb = get_supabase()
    if sb is None:
        return "Supabase credentials not found."
    try:
        sb.storage.from_(BUCKET).remove([row["storage_path"]])
    except Exception:
        pass  # still remove the record so it doesn't linger
    try:
        sb.table(FILES_TABLE).delete().eq("id", row["id"]).execute()
    except Exception as e:
        return str(e)
    file_counts.clear()
    return None


def delete_all_files(parent_type: str, parent_key: str):
    rows, err = list_files(parent_type, parent_key)
    if not err:
        for r in rows:
            delete_file(r)


def render_documents(parent_type: str, parent_key: str, key_prefix: str, rerun):
    rows, err = list_files(parent_type, parent_key)
    if err:
        if _is_missing(err):
            st.warning("📎 Document uploads aren't set up yet — run `plans_and_documents.sql` in Supabase "
                       "(it creates the `leadership_planning_files` table and the storage bucket).")
        else:
            st.error(f"Could not load documents: {err}")
        return

    if not rows:
        st.caption("No documents yet.")
    for r in rows:
        ext = (r.get("file_name") or "").rsplit(".", 1)[-1].lower()
        icon = FILE_ICONS.get(ext, "📎")
        url = signed_url(r["storage_path"])
        name = html.escape(r.get("file_name") or "file")
        meta = " · ".join(x for x in (_human_size(r.get("size_bytes")),
                                      r.get("uploaded_by") or "",
                                      _fmt_ts(r.get("uploaded_at"))) if x)
        c1, c2 = st.columns([6, 1])
        link = f'<a href="{url}" target="_blank">{name}</a>' if url else name
        c1.markdown(f"{icon} {link}<br><span style='font-size:0.75rem;color:#64748b'>{html.escape(meta)}</span>",
                    unsafe_allow_html=True)
        ck = f"{key_prefix}_del_{r['id']}"
        if not st.session_state.get(ck):
            if c2.button("🗑", key=f"{ck}_btn", help="Remove this document"):
                st.session_state[ck] = True
                rerun()
        else:
            if c2.button("Confirm", key=f"{ck}_yes", type="primary"):
                st.session_state.pop(ck, None)
                e = delete_file(r)
                if e:
                    st.error(f"Could not remove: {e}")
                else:
                    rerun()
            if c2.button("Keep", key=f"{ck}_no"):
                st.session_state.pop(ck, None)
                rerun()

    ver_key = f"{key_prefix}_upver"
    ver = st.session_state.get(ver_key, 0)
    picked = st.file_uploader("Add documents (Word, PDF, Excel, PowerPoint, images…)",
                              accept_multiple_files=True, key=f"{key_prefix}_up_{ver}",
                              help=f"Up to {MAX_UPLOAD_MB} MB each. Files are private to the confidential area.")
    if picked:
        if st.button(f"⬆️ Upload {len(picked)} file{'s' if len(picked) != 1 else ''}",
                     key=f"{key_prefix}_upbtn_{ver}", type="primary"):
            with st.spinner("Uploading…"):
                errors = upload_files(parent_type, parent_key, picked)
            st.session_state[ver_key] = ver + 1  # clears the picker
            if errors:
                st.session_state[f"{key_prefix}_uperr"] = errors
            rerun()
    for e in st.session_state.pop(f"{key_prefix}_uperr", []) or []:
        st.error(e)


# ══════════════════════════════════════════════════════════════════════════════
# PLANS — overviews that don't need a date, with dated days linked to them
#
#  • One row per plan in leadership_plans. `linked_dates` lists the ISO dates
#    of its Day Planner pages, so each day keeps its own timetable/notes/docs.
#  • Auto-saves like the Day Planner; documents attach to the plan itself.
# ══════════════════════════════════════════════════════════════════════════════
PLANS_TABLE = "leadership_plans"
PLAN_STATUSES = ["Idea", "Drafting", "Proposed", "Confirmed", "In progress", "Complete", "On hold"]
PLAN_STATUS_STYLE = {
    "Idea": ("#F1F5F9", "#334155", "#94A3B8"),
    "Drafting": ("#FEF3C7", "#92400E", "#F59E0B"),
    "Proposed": ("#FFEDD5", "#9A3412", "#FB923C"),
    "Confirmed": ("#D1FAE5", "#065F46", "#10B981"),
    "In progress": ("#DBEAFE", "#1E3A8A", "#3B82F6"),
    "Complete": ("#E0E7FF", "#3730A3", "#6366F1"),
    "On hold": ("#F1F5F9", "#64748B", "#CBD5E1"),
}
PLAN_CATEGORIES = [
    "Professional development", "Meeting series", "School development day", "Project / initiative",
    "Event", "Network / partner", "Planning / admin", "Other",
]
PLAN_TERMS = ["Term 1", "Term 2", "Term 3", "Term 4", "Whole year", "Not yet decided"]
PLAN_TASK_COLS = ["done", "task", "owner", "due"]


@st.cache_data(ttl=60, show_spinner=False)
def load_plans() -> tuple[list[dict], str | None]:
    sb = get_supabase()
    if sb is None:
        return [], "no_credentials"
    try:
        res = sb.table(PLANS_TABLE).select("*").order("updated_at", desc=True).execute()
    except Exception as e:
        return [], str(e)
    return res.data or [], None


def create_plan(title: str) -> tuple[str | None, str | None]:
    sb = get_supabase()
    if sb is None:
        return None, "Supabase credentials not found."
    pid = str(uuid.uuid4())
    now = _utcnow_iso()
    who = st.session_state.get("lp_entered_by") or None
    try:
        sb.table(PLANS_TABLE).insert({
            "id": pid, "title": title, "status": "Idea", "category": PLAN_CATEGORIES[0],
            "terms": [], "overview": "", "links": [], "tasks": [], "linked_dates": [],
            "created_by": who, "updated_by": who, "created_at": now, "updated_at": now,
        }).execute()
    except Exception as e:
        return None, str(e)
    load_plans.clear()
    return pid, None


def update_plan(pid: str, payload: dict) -> str | None:
    sb = get_supabase()
    if sb is None:
        return "Supabase credentials not found."
    row = dict(payload)
    row["updated_at"] = _utcnow_iso()
    row["updated_by"] = st.session_state.get("lp_entered_by") or None
    try:
        sb.table(PLANS_TABLE).update(row).eq("id", pid).execute()
    except Exception as e:
        return str(e)
    load_plans.clear()
    return None


def delete_plan(pid: str) -> str | None:
    sb = get_supabase()
    if sb is None:
        return "Supabase credentials not found."
    delete_all_files("plan", pid)
    try:
        sb.table(PLANS_TABLE).delete().eq("id", pid).execute()
    except Exception as e:
        return str(e)
    load_plans.clear()
    return None


def load_day_plans_for(dates: list[str]) -> dict:
    """{iso date: day plan row} for the given dates."""
    if not dates:
        return {}
    sb = get_supabase()
    if sb is None:
        return {}
    try:
        res = sb.table(DAY_TABLE).select("*").in_("plan_date", dates).execute()
    except Exception:
        return {}
    return {str(r["plan_date"])[:10]: r for r in res.data or []}


def plans_for_date(plans: list[dict], d: date) -> list[dict]:
    iso = d.isoformat()
    return [p for p in plans if iso in (p.get("linked_dates") or [])]


def status_pill(status: str, styles: dict) -> str:
    bg, fg, bd = styles.get(status, ("#F1F5F9", "#334155", "#94A3B8"))
    return (f'<span class="lp-pill" style="background:{bg};color:{fg};border-color:{bd};">'
            f'{html.escape(status or "")}</span>')


def go_to(view: str, arg=None):
    """Switch the page view on the next run (e.g. open a day or a plan)."""
    st.session_state["lp_goto"] = (view, arg)
    st.rerun()


def build_plan_docx(plan: dict, days: dict, events: list[dict], doc_names: list[str]) -> bytes | None:
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
    except Exception:
        return None
    doc = Document()
    sec = doc.sections[0]
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.8))
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    h = doc.add_heading(plan.get("title") or "Plan", level=1)
    h.runs[0].font.color.rgb = RGBColor(0x1A, 0x7A, 0x7A)
    meta = [plan.get("status"), plan.get("category"), ", ".join(plan.get("terms") or [])]
    if plan.get("lead"):
        meta.append(f"Lead: {plan['lead']}")
    doc.add_paragraph("   ·   ".join(x for x in meta if x) + "   ·   CONFIDENTIAL — leadership only")

    if plan.get("overview"):
        doc.add_heading("Overview", level=2)
        for line in plan["overview"].splitlines():
            doc.add_paragraph(line)

    tasks = plan.get("tasks") or []
    if tasks:
        doc.add_heading("Actions", level=2)
        for r in tasks:
            extra = ", ".join(x for x in (r.get("owner"), r.get("due")) if x)
            doc.add_paragraph(f"{'☑' if r.get('done') else '☐'} {r.get('task')}"
                              + (f" ({extra})" if extra else ""))

    linked = sorted(plan.get("linked_dates") or [])
    if linked:
        doc.add_heading("Days", level=2)
        for iso in linked:
            d = _to_date(iso)
            dp = days.get(iso) or {}
            doc.add_heading(f"{d.strftime('%A %d %B %Y')} — {term_and_week_for(d)}", level=3)
            if dp.get("focus"):
                doc.add_paragraph(dp["focus"])
            if dp.get("location"):
                doc.add_paragraph(f"Where: {dp['location']}")
            for r in events_on(events, d):
                doc.add_paragraph(f"Calendar: {fmt_time(r) or 'All day'} — {r.get('title')} "
                                  f"({r.get('status')})", style="List Bullet")
            for r in _sort_tt(dp.get("timetable") or []):
                t = "–".join(x for x in (r.get("start"), r.get("end")) if x)
                bits = " · ".join(x for x in (r.get("who"), r.get("where")) if x)
                doc.add_paragraph(f"{t}  {r.get('activity') or ''}" + (f"  ({bits})" if bits else ""),
                                  style="List Bullet")
            if dp.get("notes"):
                doc.add_paragraph(dp["notes"])

    links = plan.get("links") or []
    if links:
        doc.add_heading("Links", level=2)
        for r in links:
            doc.add_paragraph(f"{r.get('label') or r.get('url')}: {r.get('url')}", style="List Bullet")
    if doc_names:
        doc.add_heading("Attached documents (in the portal)", level=2)
        for n in doc_names:
            doc.add_paragraph(n, style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pl_payload(plan: dict) -> dict:
    return {
        "title": (plan.get("title") or "").strip(),
        "category": plan.get("category") or PLAN_CATEGORIES[0],
        "status": plan.get("status") or PLAN_STATUSES[0],
        "terms": list(plan.get("terms") or []),
        "lead": (plan.get("lead") or "").strip(),
        "overview": plan.get("overview") or "",
        "links": _rows(plan.get("links") or [], LINK_COLS),
        "tasks": _rows(plan.get("tasks") or [], PLAN_TASK_COLS),
        "linked_dates": sorted(set(plan.get("linked_dates") or [])),
    }


def _pl_load_into_state(plan: dict):
    if st.session_state.get("pl_loaded_id") == plan["id"]:
        return
    p = _pl_payload(plan)
    st.session_state["pl_loaded_id"] = plan["id"]
    st.session_state["pl_title"] = p["title"]
    st.session_state["pl_category"] = p["category"] if p["category"] in PLAN_CATEGORIES else PLAN_CATEGORIES[-1]
    st.session_state["pl_status"] = p["status"] if p["status"] in PLAN_STATUSES else PLAN_STATUSES[0]
    st.session_state["pl_terms"] = [t for t in p["terms"] if t in PLAN_TERMS]
    st.session_state["pl_lead"] = p["lead"]
    st.session_state["pl_overview"] = p["overview"]
    st.session_state["pl_links_base"] = p["links"]
    st.session_state["pl_tasks_base"] = p["tasks"]
    st.session_state["pl_dates"] = p["linked_dates"]
    st.session_state["pl_ver"] = st.session_state.get("pl_ver", 0) + 1
    st.session_state["pl_last_saved"] = p
    st.session_state["pl_saved_note"] = (f"Last saved {_fmt_ts(plan.get('updated_at'))}"
                                         + (f" by {plan['updated_by']}" if plan.get("updated_by") else ""))


def _pl_rerun():
    try:
        st.rerun(scope="fragment")
    except Exception:
        st.rerun()


@_fragment
def render_plans(events: list[dict]):
    plans, err = load_plans()
    if err:
        if _is_missing(err):
            st.error(f"The `{PLANS_TABLE}` table hasn't been found yet — run `plans_and_documents.sql` "
                     "in Supabase (same project as the calendar), then press Retry.")
        else:
            st.error(f"Could not load plans: {err}")
        if st.button("🔄 Retry", key="pl_retry"):
            load_plans.clear()
            _pl_rerun()
        return

    open_id = st.session_state.get("pl_open_id")
    current = next((p for p in plans if p["id"] == open_id), None)

    # ── List of plans ─────────────────────────────────────────────────────────
    if current is None:
        c1, c2 = st.columns([3, 1])
        new_title = c1.text_input("New plan", key="pl_new_title", label_visibility="collapsed",
                                  placeholder="Name a new plan, e.g. 2027 Team Commitment PD series")
        if c2.button("➕ Create plan", key="pl_create", type="primary", use_container_width=True):
            pid, e = create_plan((new_title or "").strip() or "Untitled plan")
            if e:
                st.error(f"Could not create the plan: {e}")
            else:
                st.session_state["pl_open_id"] = pid
                st.session_state.pop("pl_new_title", None)
                _pl_rerun()

        f1, f2, f3 = st.columns([1.4, 1.4, 2])
        sf = f1.multiselect("Status", PLAN_STATUSES, key="pl_f_status",
                            default=[s for s in PLAN_STATUSES if s not in ("Complete",)])
        tf = f2.multiselect("Term", PLAN_TERMS, key="pl_f_terms", placeholder="Any term")
        q = f3.text_input("Search plans", key="pl_f_q", placeholder="Title, lead, overview…").strip().lower()
        shown = [p for p in plans
                 if p.get("status") in sf
                 and (not tf or set(tf) & set(p.get("terms") or []))
                 and (not q or q in " ".join(str(p.get(k) or "") for k in ("title", "lead", "overview")).lower())]
        if not plans:
            st.info("No plans yet. Name one above and press ➕ Create plan — you can add the overview now "
                    "and dates later.")
        elif not shown:
            st.caption("No plans match these filters.")

        counts = file_counts("plan")
        for p in shown:
            dates = sorted(p.get("linked_dates") or [])
            future = [x for x in dates if x >= date.today().isoformat()]
            next_txt = (f"Next day: {_to_date(future[0]).strftime('%a %d %b')}" if future
                        else ("No days added yet" if not dates else "All days past"))
            open_tasks = sum(1 for t in (p.get("tasks") or []) if not t.get("done") and t.get("task"))
            preview = (p.get("overview") or "").strip().replace("\n", " ")
            preview = preview[:160] + ("…" if len(preview) > 160 else "")
            with st.container(border=True):
                a, b = st.columns([5, 1])
                a.markdown(
                    f"{status_pill(p.get('status'), PLAN_STATUS_STYLE)} &nbsp;**{html.escape(p.get('title') or 'Untitled')}**"
                    f"<br><span style='font-size:0.8rem;color:#475569'>"
                    f"{html.escape(p.get('category') or '')}"
                    f"{' · ' + html.escape(', '.join(p.get('terms') or [])) if p.get('terms') else ''}"
                    f"{' · Lead: ' + html.escape(p['lead']) if p.get('lead') else ''}"
                    f" · 📅 {len(dates)} day{'s' if len(dates) != 1 else ''} ({next_txt})"
                    f" · 📎 {counts.get(p['id'], 0)} · ✅ {open_tasks} open</span>"
                    + (f"<br><span style='font-size:0.8rem'>{html.escape(preview)}</span>" if preview else ""),
                    unsafe_allow_html=True,
                )
                if b.button("Open", key=f"pl_open_{p['id']}", use_container_width=True):
                    st.session_state["pl_open_id"] = p["id"]
                    _pl_rerun()
        return

    # ── One plan ──────────────────────────────────────────────────────────────
    _pl_load_into_state(current)
    pid = current["id"]
    ver = st.session_state.get("pl_ver", 0)

    if st.button("← All plans", key="pl_back"):
        st.session_state.pop("pl_open_id", None)
        st.session_state.pop("pl_loaded_id", None)
        _pl_rerun()

    st.text_input("Plan title", key="pl_title")
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.6, 1.2])
    c1.selectbox("Status", PLAN_STATUSES, key="pl_status")
    c2.selectbox("Type", PLAN_CATEGORIES, key="pl_category")
    c3.multiselect("When", PLAN_TERMS, key="pl_terms", placeholder="Term(s)")
    c4.text_input("Lead", key="pl_lead")

    st.markdown("#### 🧭 Overview")
    o1, o2 = st.tabs(["✏️ Write", "👁 Preview"])
    with o1:
        st.text_area("Overview", key="pl_overview", height=240, label_visibility="collapsed",
                     placeholder="The big picture — purpose, outcomes, who it's for, sequence of sessions, "
                                 "budget, presenters, open questions…\nNo dates needed here; add them below "
                                 "when you know them.")
    with o2:
        if st.session_state.get("pl_overview"):
            st.markdown(st.session_state["pl_overview"])
        else:
            st.caption("Nothing written yet.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ✅ Actions")
        tasks_df = st.data_editor(
            _df(st.session_state["pl_tasks_base"], PLAN_TASK_COLS),
            key=f"pl_tasks_{ver}", num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "done": st.column_config.CheckboxColumn("✓", width="small", default=False),
                "task": st.column_config.TextColumn("Action", width="large"),
                "owner": st.column_config.TextColumn("Who"),
                "due": st.column_config.TextColumn("By when", help="e.g. Wk 9 T4, end of Jan"),
            },
        )
    with c2:
        st.markdown("#### 🔗 Links")
        links_df = st.data_editor(
            _df(st.session_state["pl_links_base"], LINK_COLS),
            key=f"pl_links_{ver}", num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "label": st.column_config.TextColumn("Name"),
                "url": st.column_config.LinkColumn("Link (paste URL)", width="medium",
                                                   validate=r"^https?://.+"),
                "note": st.column_config.TextColumn("Note"),
            },
        )
        clickable = [r for r in _rows(links_df, LINK_COLS) if r["url"].startswith("http")]
        if clickable:
            st.markdown("  \n".join(f"🔗 [{r['label'] or r['url']}]({r['url']})" for r in clickable))

    # ── Auto-save (before the day/document actions so nothing typed is lost) ──
    payload = {
        "title": (st.session_state.get("pl_title") or "").strip() or "Untitled plan",
        "category": st.session_state.get("pl_category"),
        "status": st.session_state.get("pl_status"),
        "terms": list(st.session_state.get("pl_terms") or []),
        "lead": (st.session_state.get("pl_lead") or "").strip(),
        "overview": st.session_state.get("pl_overview") or "",
        "links": _rows(links_df, LINK_COLS),
        "tasks": _rows(tasks_df, PLAN_TASK_COLS),
        "linked_dates": sorted(set(st.session_state.get("pl_dates") or [])),
    }

    def save_now() -> bool:
        if payload == st.session_state.get("pl_last_saved"):
            return True
        e = update_plan(pid, payload)
        if e:
            st.error(f"Not saved yet ({e}). What you've typed stays on screen — it retries on your next change.")
            return False
        st.session_state["pl_last_saved"] = dict(payload)
        st.session_state["pl_saved_note"] = f"✓ Auto-saved {_now_hm()}"
        return True

    save_now()

    # ── Days ──────────────────────────────────────────────────────────────────
    st.markdown("#### 📅 Days in this plan")
    st.caption("Each day opens as its own Day Planner page (timetable, notes, links, documents).")
    dates = payload["linked_dates"]
    day_rows = load_day_plans_for(dates)
    day_files = file_counts("day")
    if not dates:
        st.caption("No days yet — add one below when a date is known or pencilled in.")
    for iso in dates:
        d = _to_date(iso)
        dp = day_rows.get(iso) or {}
        tt = _sort_tt(dp.get("timetable") or [])
        evs = events_on(events, d)
        with st.container(border=True):
            a, b, c = st.columns([4, 1, 1])
            summary = []
            if dp.get("location"):
                summary.append(f"📍 {dp['location']}")
            if tt:
                first = ", ".join(
                    f"{r.get('start') or ''} {r.get('activity') or ''}".strip() for r in tt[:3] if r.get("activity"))
                summary.append(f"🕘 {len(tt)} slot{'s' if len(tt) != 1 else ''}" + (f": {first}" if first else ""))
            if day_files.get(iso):
                summary.append(f"📎 {day_files[iso]}")
            if evs:
                summary.append("📅 " + ", ".join(r.get("title") or "" for r in evs))
            a.markdown(
                f"**{d.strftime('%a %d %b %Y')}** · {term_and_week_for(d)}"
                + (f" — {html.escape(dp['focus'])}" if dp.get("focus") else "")
                + (f"<br><span style='font-size:0.8rem;color:#475569'>{html.escape(' · '.join(summary))}</span>"
                   if summary else ""),
                unsafe_allow_html=True,
            )
            if b.button("✏️ Open day", key=f"pl_day_open_{iso}", use_container_width=True):
                go_to(VIEW_DAY, d)
            if c.button("Unlink", key=f"pl_day_unlink_{iso}", use_container_width=True,
                        help="Removes the date from this plan. The day's own page is kept."):
                st.session_state["pl_dates"] = [x for x in dates if x != iso]
                _pl_rerun()

    with st.expander("➕ Add a day to this plan", expanded=not dates):
        a, b = st.columns([1, 2])
        new_d = a.date_input("Date", key=f"pl_newday_{pid}", format="DD/MM/YYYY",
                             value=TERMS[1][0] if date.today() < TERMS[1][0] else date.today())
        new_focus = b.text_input("What's happening this day (optional)", key=f"pl_newfocus_{pid}",
                                 placeholder=f"e.g. {payload['title']} — session 1")
        open_after = st.checkbox("Open it in the Day Planner straight away", value=True, key=f"pl_openafter_{pid}")
        if st.button("➕ Add day", key=f"pl_addday_{pid}", type="primary"):
            iso = new_d.isoformat()
            existing, e = load_day_plan(new_d)
            if e:
                st.error(f"Could not check that date: {e}")
            else:
                if not existing:
                    e = save_day_plan(new_d, {
                        "focus": (new_focus or "").strip() or payload["title"], "location": "", "notes": "",
                        "timetable": [], "links": [], "tasks": [],
                        "updated_by": st.session_state.get("lp_entered_by") or None})
                if e:
                    st.error(f"Could not create the day: {e}")
                else:
                    st.session_state["pl_dates"] = sorted(set(dates + [iso]))
                    payload["linked_dates"] = st.session_state["pl_dates"]
                    if save_now():
                        if existing:
                            st.session_state["lp_flash"] = (f"{new_d.strftime('%a %d %b')} already had a Day "
                                                            "Planner page — it's now linked to this plan.")
                        if open_after:
                            go_to(VIEW_DAY, new_d)
                        _pl_rerun()

    # ── Documents ─────────────────────────────────────────────────────────────
    st.markdown("#### 📎 Documents for this plan")
    render_documents("plan", pid, f"pldoc_{pid}", _pl_rerun)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    f1, f2, f3 = st.columns([2, 1.4, 1.4])
    f1.caption(st.session_state.get("pl_saved_note") or "Auto-saves as you go — nothing to press.")
    with f2:
        docs, _ = list_files("plan", pid)
        docx_bytes = build_plan_docx(payload, day_rows, events, [r.get("file_name") for r in docs])
        if docx_bytes:
            safe_title = "".join(ch if ch.isalnum() else "_" for ch in payload["title"])[:50]
            st.download_button("📄 Plan overview (Word)", data=docx_bytes,
                               file_name=f"CLC_Plan_{safe_title}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True, key="pl_dl")
    with f3:
        with st.popover("More…", use_container_width=True):
            if not st.session_state.get("pl_del_confirm"):
                if st.button("🗑️ Delete this plan", key="pl_del"):
                    st.session_state["pl_del_confirm"] = True
                    _pl_rerun()
            else:
                st.warning("Delete this plan and its documents? Its Day Planner pages are kept.")
                if st.button("Yes, delete", key="pl_del_yes", type="primary"):
                    st.session_state.pop("pl_del_confirm", None)
                    e = delete_plan(pid)
                    if e:
                        st.error(f"Could not delete: {e}")
                    else:
                        st.session_state.pop("pl_open_id", None)
                        st.session_state.pop("pl_loaded_id", None)
                        _pl_rerun()
                if st.button("Keep it", key="pl_del_no"):
                    st.session_state.pop("pl_del_confirm", None)
                    _pl_rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="lp-header"><h1>🗓️ Leadership Planning Calendar {YEAR}</h1>'
    f'<p>Confidential — meetings, PD and key dates being proposed, scheduled or confirmed, '
    f'and where they will happen.</p></div>',
    unsafe_allow_html=True,
)

events, err = load_events()
if err == "no_credentials":
    st.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) were not found in Render environment variables.")
    st.stop()
elif err:
    if "does not exist" in err or "PGRST205" in err or "schema cache" in err:
        st.error(f"The `{TABLE}` table hasn't been created yet. Run `leadership_planning_schema.sql` "
                 "in the Supabase SQL editor (main portal project), then refresh this page.")
    else:
        st.error(f"Could not load the planning calendar: {err}")
    st.stop()

drafts = load_drafts()
_flash = st.session_state.pop("lp_flash", None)
if _flash:
    st.success(_flash)

# ── Term + filters ────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 2, 2])
with c1:
    term = st.selectbox("Term", [1, 2, 3, 4], format_func=lambda t: f"Term {t} {YEAR}", key="lp_term")
with c2:
    status_filter = st.multiselect("Show status", STATUSES, default=["Proposed", "Scheduled", "Confirmed"],
                                   key="lp_status_filter")
with c3:
    type_filter = st.multiselect("Show types", EVENT_TYPES, default=EVENT_TYPES, key="lp_type_filter")

filtered = [r for r in events
            if r.get("status") in status_filter and r.get("event_type") in type_filter]

t_start, t_end = TERMS[term]
pre_term_start = t_start - timedelta(days=t_start.weekday() + 7)
term_events = [r for r in filtered if r["end_date"] >= pre_term_start and r["start_date"] <= t_end]
all_term_events = [r for r in events if r["end_date"] >= pre_term_start and r["start_date"] <= t_end]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Confirmed", sum(r.get("status") == "Confirmed" for r in all_term_events))
m2.metric("Scheduled", sum(r.get("status") == "Scheduled" for r in all_term_events))
m3.metric("Proposed", sum(r.get("status") == "Proposed" for r in all_term_events))
m4.metric("Location TBC", sum(
    (r.get("location_mode") == "TBC") and r.get("status") != "Cancelled" for r in all_term_events))

# ── Navigation ────────────────────────────────────────────────────────────────
# A view switcher (rather than st.tabs) so buttons like "Open day" / "Open plan"
# can jump straight to the right place. Only the chosen view is built each run.
_goto = st.session_state.pop("lp_goto", None)
if _goto:
    _view, _arg = _goto
    st.session_state["lp_view"] = _view
    if _view == VIEW_DAY and _arg:
        st.session_state["dp_date"] = _arg
        st.session_state["dp_date_keep"] = _arg
    if _view == VIEW_PLANS and _arg:
        st.session_state["pl_open_id"] = _arg

view = st.radio("View", VIEWS, horizontal=True, key="lp_view", label_visibility="collapsed")
if st.session_state.get("lp_prev_view") != view:
    # Entering a view: reload it fresh from the database (auto-saves are already there)
    st.session_state["lp_prev_view"] = view
    st.session_state.pop("dp_loaded_date", None)
    st.session_state.pop("pl_loaded_id", None)
    for _k in [k for k in st.session_state.keys() if k.startswith("lp_") and k.endswith("_init")]:
        st.session_state.pop(_k, None)
    st.session_state["lp_quiet_restore"] = True
else:
    st.session_state["lp_quiet_restore"] = False

# ── Calendar ──────────────────────────────────────────────────────────────────
if view == VIEW_CAL:
    st.caption(f"Term {term}: {t_start.strftime('%a %d %b')} – {t_end.strftime('%a %d %b %Y')}. "
               "Hover an item for its summary.")
    include_pre = st.toggle("Show the week before term starts", value=True, key="lp_pre",
                            help="Useful for planning leadership days and SDDs before students return.")
    legend()
    shown_days = render_term_grid(term, term_events, include_pre, load_day_plan_index())
    st.caption("🗒️ marks days that have a Day Planner page — open 🗒️ Day Planner to view or edit it.")

    hidden = [r for r in term_events
              if not any(r["start_date"] <= d <= r["end_date"] for d in shown_days)]
    if hidden:
        st.markdown("**Also in this period (weekend or outside the grid)**")
        for r in hidden:
            st.markdown(f"- {fmt_date_range(r)} — {r.get('title')} ({r.get('status')}, {fmt_location(r)})")

    holiday_events = [r for r in filtered
                      if term_and_week_for(r["start_date"]) == "Holidays"]
    if holiday_events:
        with st.expander(f"School holiday items ({len(holiday_events)})"):
            for r in holiday_events:
                st.markdown(f"- {fmt_date_range(r)} — {r.get('title')} ({r.get('status')}, {fmt_location(r)})")

# ── Plans ─────────────────────────────────────────────────────────────────────
elif view == VIEW_PLANS:
    st.caption("Overviews that don't need a date yet — purpose, actions, links and documents. "
               "Add dated days to a plan when you know them; each day opens in the Day Planner.")
    render_plans(events)

# ── Day Planner ───────────────────────────────────────────────────────────────
elif view == VIEW_DAY:
    st.caption("Your sandbox for any single day — pick a date and build it up: timetable, notes, "
               "links, to-dos and documents. Everything auto-saves to that date.")
    if "dp_date" not in st.session_state:
        st.session_state["dp_date"] = st.session_state.get("dp_date_keep", TERMS[1][0])
    render_day_planner(events)

# ── Add ───────────────────────────────────────────────────────────────────────
elif view == VIEW_ADD:
    st.caption("Start with what you know — an item can be Proposed with the location TBC and updated later.")
    render_event_form("lp_new", draft=drafts.get("new"))

# ── Review & edit ─────────────────────────────────────────────────────────────
elif view == VIEW_LIST:
    scope = st.radio("Show", [f"Term {term} (incl. pre-term week)", "All of 2027"], horizontal=True,
                     key="lp_scope")
    source = [r for r in events if r.get("event_type") in type_filter and r.get("status") in STATUSES]
    if scope.startswith("Term"):
        source = [r for r in source if r["end_date"] >= pre_term_start and r["start_date"] <= t_end]
    search = st.text_input("Search", placeholder="Title, venue, lead, notes…", key="lp_search").strip().lower()
    if search:
        source = [r for r in source if search in " ".join(
            str(r.get(k) or "") for k in ("title", "location", "lead", "summary", "next_action", "audience")
        ).lower()]

    if not source:
        st.info("Nothing here yet — add the first item in the ➕ Add item tab.")
    for r in source:
        bg, fg, bd = STATUS_STYLE.get(r.get("status"), STATUS_STYLE["Proposed"])
        icon = TYPE_ICON.get(r.get("event_type"), "📌")
        label = (f"{icon} {r['start_date'].strftime('%d %b')} · {r.get('title')} "
                 f"— {r.get('status')} · {term_and_week_for(r['start_date'])}")
        with st.expander(label):
            st.markdown(
                f'<span class="lp-pill" style="background:{bg};color:{fg};border-color:{bd};">'
                f'{r.get("status")}</span> &nbsp; **{fmt_date_range(r)}** {fmt_time(r)} · '
                f'{LOCATION_ICON.get(r.get("location_mode"), "📍")} {html.escape(fmt_location(r))}',
                unsafe_allow_html=True,
            )
            if r.get("next_action"):
                owner = f" — {r['action_owner']}" if r.get("action_owner") else ""
                st.markdown(f"➡️ **Next:** {r['next_action']}{owner}")
            if r.get("created_by"):
                st.caption(f"Entered by {r['created_by']}")

            render_event_form(f"lp_edit_{r['id']}", existing=r, draft=drafts.get(f"edit:{r['id']}"))

            confirm_key = f"lp_del_confirm_{r['id']}"
            if not st.session_state.get(confirm_key):
                if st.button("🗑️ Delete", key=f"lp_del_{r['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning("Delete this item permanently? (Use status ‘Cancelled’ to keep a record instead.)")
                d1, d2 = st.columns(2)
                if d1.button("Yes, delete", key=f"lp_del_yes_{r['id']}", type="primary"):
                    st.session_state.pop(confirm_key, None)
                    if delete_event(r["id"]):
                        st.rerun()
                if d2.button("Keep it", key=f"lp_del_no_{r['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

# ── Export ────────────────────────────────────────────────────────────────────
elif view == VIEW_EXPORT:
    st.caption("Exports use the current status/type filters. Marked confidential — share with leadership only.")
    export_events = sorted(term_events, key=lambda r: (r["start_date"], r.get("start_time") or "99"))
    docx_bytes = build_docx(term, export_events)
    c1, c2 = st.columns(2)
    with c1:
        if docx_bytes:
            st.download_button(
                f"📄 Term {term} planning overview (Word)",
                data=docx_bytes,
                file_name=f"CLC_Leadership_Planning_T{term}_{YEAR}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        else:
            st.info("Word export needs python-docx in requirements.txt.")
    with c2:
        st.download_button(
            f"📊 Term {term} items (CSV / Excel)",
            data=build_csv(export_events),
            file_name=f"CLC_Leadership_Planning_T{term}_{YEAR}.csv",
            mime="text/csv",
            use_container_width=True,
        )
