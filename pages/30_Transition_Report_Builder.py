"""
Transition Report Builder — CLC Learning and Behaviour Unit

Students are chosen from the Student Register by INITIALS only (the same code
every portal tool uses). Two sections pull live data:

  • Regulation Profile  ← Window of Tolerance Builder (wot_builder_reports,
                           students/register Supabase project)
  • SMARTAR Goals       ← SMARTAR Goal Builder (smartar_students / smartar_goals /
                           smartar_tracking, behaviour Supabase project) —
                           active AND archived goals, with the Builder's own
                           "Distribution" pie chart for each goal

A full name can be typed for the printout only; it is never saved. The copy
filed to the Document Archive always uses initials.
"""
import os
import re
import json
import statistics
from io import BytesIO
from datetime import date, datetime

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from supabase import create_client

# ── Document Archive integration (fails soft if unavailable) ─────────────────
try:
    from archive_utils import archive_document
    ARCHIVE_AVAILABLE = True
except Exception:
    ARCHIVE_AVAILABLE = False

    def archive_document(**_k):
        return None

st.set_page_config(page_title="Transition Report Builder", layout="wide", page_icon="📄")


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _secret(*paths, default=None):
    """First secret found. Each path is 'KEY' or 'section.key'. Render env vars
    are checked first, then Streamlit secrets (same order as other portal tools)."""
    for p in paths:
        if "." not in p and os.environ.get(p):
            return os.environ[p]
    for p in paths:
        try:
            node = st.secrets
            for part in p.split("."):
                node = node[part]
            if node:
                return node
        except Exception:
            continue
    return default


def _students_client():
    """Supabase project holding the Student Register, Window of Tolerance
    reports and the Document Archive. Uses archive_utils' own connection when
    available (so it always lands on the same project as the archive), then
    falls back to the *_STUDENTS env vars, then the unsuffixed ones."""
    if "_tr_students_client" in st.session_state:
        return st.session_state["_tr_students_client"]
    client = None
    try:
        from archive_utils import _get_client as _au_client
        client = _au_client()
    except Exception:
        client = None
    if client is None:
        candidates = [
            (("SUPABASE_URL_STUDENTS", "supabase_students.url"),
             ("SUPABASE_KEY_STUDENTS", "SUPABASE_ANON_KEY_STUDENTS", "supabase_students.key")),
            (("SUPABASE_URL",), ("SUPABASE_KEY", "SUPABASE_ANON_KEY")),
        ]
        for url_names, key_names in candidates:
            url, key = _secret(*url_names), _secret(*key_names)
            if not (url and key):
                continue
            try:
                c = create_client(url, key)
                c.table("student_directory").select("id").limit(1).execute()
                client = c
                break
            except Exception:
                continue
    st.session_state["_tr_students_client"] = client
    return client


def _smartar_client():
    """Same project/credentials the SMARTAR Goal Builder uses."""
    if "_tr_smartar_client" in st.session_state:
        return st.session_state["_tr_smartar_client"]
    url = _secret("supabase.url", "BEHAVIOUR_SUPABASE_URL")
    key = _secret("supabase.key", "BEHAVIOUR_SUPABASE_KEY")
    client = None
    if url and key:
        try:
            client = create_client(url, key)
        except Exception:
            client = None
    st.session_state["_tr_smartar_client"] = client
    return client


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
# ── SMARTAR / GAS — identical to 25_SMARTAR_Goal_Builder.py ──────────────────
LEVEL_ORDER  = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
TRACK_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]   # BELOW isn't tracked daily
LEVEL_EMOJI  = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "BELOW": "⚠️", "NOT YET": "❌"}
LEVEL_COLOR  = {"EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e", "EXPECTED": "#1d6fa4",
                "BELOW": "#d97706", "NOT YET": "#c0392b"}   # Builder's text colours
MPL_COLOR    = {"EXCEEDING": "#27ae60", "ABOVE": "#2ecc71", "EXPECTED": "#2980b9",
                "BELOW": "#e67e22", "NOT YET": "#c0392b"}
SCORE_MAP    = {"EXCEEDING": 5, "ABOVE": 4, "EXPECTED": 3, "BELOW": 2, "NOT YET": 1}
SCORE_TO_LVL = {v: k for k, v in SCORE_MAP.items()}
GAS_COLUMN   = {"EXCEEDING": "gas_exceeding", "ABOVE": "gas_above", "EXPECTED": "gas_expected",
                "BELOW": "gas_below", "NOT YET": "gas_not_yet"}
SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}
ALL_SESSIONS = ["Morning", "Middle", "Afternoon"]

# ── Window of Tolerance — same zones/columns/colours as the WoT Builder's Regulation Map ──
WOT_ZONES = [
    {"id": "hyper",      "name": "Mobilisation",        "tag": "Hyperarousal",     "color": "#C1543A", "tint": "#F3E2DC"},
    {"id": "copingup",   "name": "Coping — rising",     "tag": "Early warning",    "color": "#C98A2E", "tint": "#F3E7D3"},
    {"id": "wot",        "name": "Window of Tolerance", "tag": "Regulated",        "color": "#4C7A5A", "tint": "#E1EBE3"},
    {"id": "copingdown", "name": "Coping — falling",    "tag": "Early withdrawal", "color": "#3E6E8E", "tint": "#DEE7ED"},
    {"id": "hypo",       "name": "Immobilisation",      "tag": "Hypoarousal",      "color": "#38456B", "tint": "#DFE2EA"},
]
WOT_COLS = [("context", "Context"), ("behaviour", "Behaviour descriptors"), ("interventions", "What helps")]

# ── Report sections ──────────────────────────────────────────────────────────
SOUNDS_WRITE = [
    ("Blending (building words)", 14),
    ("Segmenting (identifying sounds)", 69),
    ("Phoneme Manipulation", 10),
    ("Alphabet Code Knowledge", 50),
    ("Non-Word Reading", 30),
]
# Big Ideas in Number — the 4 big ideas / 19 elements on the CLC report's assessment grid
BIIN = [
    ("Trusting the count", [("1.1", "Subitising"), ("1.2", "Mental objects")]),
    ("Place value", [("2.1", "Number naming"), ("2.2", "Efficient counting"), ("2.3", "Sequencing"),
                     ("2.4", "Renaming and counting")]),
    ("Multiplicative thinking", [("3.1", "Countable units"), ("3.2", "Additive strategies"), ("3.3", "Sharing"),
                                 ("3.4", "Arrays and regions"), ("3.5", "Cartesian product"),
                                 ("3.6", "Propositional reasoning")]),
    ("Partitioning", [("4.1", "Equal parts"), ("4.2", "Fraction naming"), ("4.3", "Fraction making"),
                      ("4.4", "Fraction recording"), ("4.5", "Decimal fraction naming and recording"),
                      ("4.6", "Comparing and ordering"), ("4.7", "Rational number sequencing")]),
]
BIIN_RESULTS = ["", "Mastered", "Developing", "Needs improvement"]
BIIN_RANK = {"Needs improvement": 1, "Developing": 2, "Mastered": 3}
BIIN_FILL = {"Mastered": "B7DE9B", "Developing": "FFE38A", "Needs improvement": "F4A9A3"}   # green / yellow / red
BIIN_LEGEND = "Green = Mastered (90–100%) · Yellow = Developing (70–80%) · Red = Needs improvement (< 70%)"

# High Impact Teaching Strategies and their key elements — the same matrix as the CLC report template
HITS_ELEMENTS = {
    "Goal setting": [
        "Goals are developed from outcomes of student assessments",
        "Goals are presented clearly to students, so they know what they need to learn",
        "Goals focus on surface and/or deep learning",
        "Challenges student relevant to their current mastery of the topic",
        "Goals are linked to explicit assessment criteria"],
    "Structuring lessons": [
        "Clear expectations", "Sequencing and linking learning", "Clear instructions", "Clear transitions",
        "Scaffolding", "Questioning / feedback", "Formative assessment", "Exit cards"],
    "Explicit teaching": [
        "Shared learning intentions", "Relevant content and activities",
        "New content is explicitly introduced and explored",
        "Teacher models application of knowledge and skills",
        "Worked examples support independent practice",
        "Practice and feedback loops uncover and address misunderstanding"],
    "Worked examples": [
        "Clarify learning objective / demonstrate what students need to do to acquire new knowledge & skills",
        "Present the steps required to arrive at a solution, reducing cognitive load so students can focus on process",
        "Students practise independently using the worked example as a model"],
    "Collaborative learning": [
        "Students work together to apply previously acquired knowledge",
        "Cooperatively solve problems using previously acquired knowledge & skills",
        "Work in groups that foster peer learning", "Groups of students compete against each other"],
    "Multiple exposures": [
        "Time to practise what they have learned",
        "Timely feedback provides opportunities for immediate correction and improvement"],
    "Questioning": [
        "Plan in advance for probing, extending, revising & reflecting", "Use open questions",
        "Questions as an immediate source of feedback to track progress/understanding",
        "Cold call and strategic sampling"],
    "Feedback": [
        "Precise, timely, specific, accurate and actionable",
        "Questioning and assessment is feedback on teaching practice",
        "Use student voice to enable student feedback about teaching"],
    "Metacognitive strategies": [
        "Teaching problem solving", "Teaching study skills", "Promotes self-questioning",
        "Classroom discussion an essential feature", "Uses concept mapping"],
    "Differentiated teaching": [
        "High quality, evidence-based group instruction", "Regular supplemental instruction",
        "Individualised interventions"],
}
HITS_OPTIONS = list(HITS_ELEMENTS.keys())
RP_OPTIONS = ["Comic Strip Conversations", "Circles (Nurture/Restorative/Community)",
              "Restorative Meetings", "Relational Mapping", "Restorative Conversations",
              "Affective Questioning/Statements"]

TEAL = "#1A7A6E"

# ── Report types ─────────────────────────────────────────────────────────────
# Review Report      — written about halfway through a normal placement
# Transition Report  — the completed report at the end; built on the Review
# Modified Report    — short placements: only the sections chosen are included
REPORT_TYPES = ["Review Report", "Transition Report", "Modified Report"]
REPORT_TYPE_HELP = {
    "Review Report": "Halfway through a normal placement. Saved, then built on through the placement.",
    "Transition Report": "The completed report at the end of placement — usually started from the Review Report.",
    "Modified Report": "Shorter placements. Has the cover page; choose only the sections to include.",
}
SECTIONS = [
    ("literacy", "Literacy Progress"),
    ("numeracy", "Numeracy Progress"),
    ("hits", "Pedagogical Strategies (HITS)"),
    ("restorative", "Restorative Practice & Relational Safety"),
    ("regulation", "Regulation Profile (Window of Tolerance)"),
    ("smartar", "Behaviour Progress: SMARTAR Goals"),
    ("attendance", "Attendance"),
    ("summary", "Overall Progress Summary"),
    ("recommendations", "Transition Recommendations"),
]
SECTION_LABEL = dict(SECTIONS)
# Review Report = everything except the end-of-placement recommendations
REVIEW_SECTIONS = [k for k, _ in SECTIONS if k != "recommendations"]

# Saved reports live in the students/register project, next to wot_builder_reports
REPORTS_TABLE = "student_reports"
REPORTS_TABLE_SQL = """create table if not exists student_reports (
    id                  uuid primary key default gen_random_uuid(),
    student_register_id text,
    student_initials    text not null,
    report_type         text not null,
    sections            jsonb,
    data                jsonb not null default '{}'::jsonb,
    created_by          text,
    updated_by          text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists student_reports_student_idx on student_reports (student_register_id);
alter table student_reports disable row level security;"""

# Session keys (without the tr_ prefix) that make up a saved report. Never the
# printout name, never caches.
SAVED_KEY_RE = re.compile(
    r"^(report_type|sections|report_date|pstart|pend|teacher|school|vocab_(type|pre|post|summary)|numeracy|"
    r"biin_c_\d+|hits|hits_el_\d+|hits_c_\d+|rp|rp_comments|wot|wotz_\w+|regulation|goal_sel|goal_known|"
    r"g_current_.+|days_att|days_tot|summary|recs|sm_override)$")
DATE_KEYS = ("report_date", "pstart", "pend")
EDITORS = ["sw", "biin0", "biin1", "biin2", "biin3"]


# ══════════════════════════════════════════════════════════════════════════════
# DATA — STUDENT REGISTER
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def load_register():
    """Current students from the register (same list the WoT Builder reads).
    Students who've left (status 'archived') are hidden; a missing status is
    kept, so a data gap never hides an enrolled student. Returns None if the
    register can't be reached."""
    c = _students_client()
    if c is None:
        return None
    try:
        rows = c.table("student_directory").select("*").execute().data or []
    except Exception:
        return None
    out = []
    for r in rows:
        ini = str(r.get("initials") or "").strip()
        if not ini:
            continue
        if str(r.get("status") or "").strip().lower() == "archived":
            continue
        out.append({"id": r.get("id"), "initials": ini, "program": r.get("program") or ""})
    return sorted(out, key=lambda r: (r["initials"].upper()))


# ══════════════════════════════════════════════════════════════════════════════
# DATA — WINDOW OF TOLERANCE
# ══════════════════════════════════════════════════════════════════════════════
def _normalise_wot(data):
    out = {}
    data = data if isinstance(data, dict) else {}
    for z in WOT_ZONES:
        zd = data.get(z["id"]) or {}
        out[z["id"]] = {}
        for col, _ in WOT_COLS:
            items = zd.get(col) or []
            texts = []
            for it in items:
                t = it.get("text") if isinstance(it, dict) else it
                t = str(t or "").strip()
                if t:
                    texts.append(t)
            out[z["id"]][col] = texts
    return out


def load_wot_report(student):
    """Latest WoT Builder report for this student — by register id, then by
    initials as a fallback. Returns dict or None."""
    c = _students_client()
    if c is None:
        return None
    rows = []
    try:
        rows = (c.table("wot_builder_reports").select("*")
                .eq("student_register_id", student["id"])
                .order("updated_at", desc=True).limit(1).execute().data or [])
    except Exception:
        rows = []
    if not rows:
        try:
            rows = (c.table("wot_builder_reports").select("*")
                    .eq("student_initials", student["initials"])
                    .order("updated_at", desc=True).limit(1).execute().data or [])
        except Exception:
            rows = []
    if not rows:
        return None
    r = rows[0]
    return {
        "status": r.get("status") or "draft",
        "updated_at": r.get("updated_at"),
        "updated_by": r.get("updated_by") or "",
        "data": _normalise_wot(r.get("data")),
    }


def wot_has_content(wot, zone_id):
    return any(wot["data"][zone_id][c] for c, _ in WOT_COLS)


def _lc(s):
    return s[:1].lower() + s[1:] if s else s


def _join(items):
    items = [_lc(i) for i in items]
    if len(items) < 2:
        return "".join(items)
    return "; ".join(items[:-1]) + " and " + items[-1]


def draft_wot_summary(wot, zones_on, who):
    """Starting paragraph built from the pulled WoT phrases — staff edit it after."""
    d = wot["data"]
    on = lambda z: zones_on.get(z, False)
    get = lambda z, c: d[z][c] if on(z) else []
    p = []
    if get("wot", "context"):
        p.append(f"{who} is most settled and ready to learn during {_join(get('wot', 'context')[:2])}.")
    if get("wot", "interventions"):
        p.append(f"What keeps {who} in their window: {_join(get('wot', 'interventions'))}.")
    trig = (get("copingup", "context") + get("hyper", "context"))[:3]
    if trig:
        p.append(f"Common triggers include {_join(trig)}.")
    warn = (get("copingup", "behaviour") + get("copingdown", "behaviour"))[:4]
    if warn:
        p.append(f"Early warning signs to watch for are {_join(warn)}.")
    early = (get("copingup", "interventions") + get("copingdown", "interventions"))[:3]
    if early:
        p.append(f"Stepping in early works best: {_join(early)}.")
    if get("hyper", "interventions"):
        p.append(f"If {who} becomes highly dysregulated, staff should {_join(get('hyper', 'interventions'))}.")
    if get("hypo", "interventions"):
        p.append(f"When shut down, {_join(get('hypo', 'interventions'))}.")
    return " ".join(p).replace("..", ".")


# ══════════════════════════════════════════════════════════════════════════════
# DATA — SMARTAR GOAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def load_smartar_students():
    c = _smartar_client()
    if c is None:
        return None
    try:
        return c.table("smartar_students").select("*").order("student_name").execute().data or []
    except Exception:
        return None


def match_smartar_student(initials, smartar_students):
    """Register initials → SMARTAR student_name (the register writes its code
    into SMARTAR verbatim). Exact, case-insensitive."""
    key = initials.strip().upper()
    hits = [s for s in (smartar_students or []) if str(s.get("student_name") or "").strip().upper() == key]
    return hits[0] if len(hits) == 1 else None


def load_goals(smartar_name):
    """Active + archived goals, newest first (as the Builder's Progress Report)."""
    c = _smartar_client()
    if c is None:
        return []
    try:
        return (c.table("smartar_goals").select("*").eq("student_name", smartar_name)
                .order("created_at", desc=True).execute().data or [])
    except Exception:
        return []


def goal_date_range(goal):
    """Same rule as the Builder: start → archived_at for archived goals, start → today otherwise."""
    start = goal.get("start_date") or (goal.get("created_at") or "")[:10] or date.today().isoformat()
    if not goal.get("active", True) and goal.get("archived_at"):
        end = goal["archived_at"][:10]
    else:
        end = date.today().isoformat()
    return str(start)[:10], end


def load_goal_tracking(goal):
    """Tracking rows for the goal's own date range, limited to the sessions in
    its tracking period — exactly what the Builder's Progress Report charts."""
    c = _smartar_client()
    if c is None:
        return []
    from_d, to_d = goal_date_range(goal)
    sessions = SESSIONS_FOR_PERIOD.get(goal.get("tracking_period", "All Day"), ALL_SESSIONS)
    try:
        rows = (c.table("smartar_tracking").select("*").eq("goal_id", goal["id"])
                .gte("session_date", from_d).lte("session_date", to_d)
                .order("session_date").execute().data or [])
    except Exception:
        return []
    rows = [r for r in rows if r.get("session_time") in sessions]
    rows.sort(key=lambda r: (str(r.get("session_date")), str(r.get("recorded_at") or "")))
    return rows


def goal_stats(tracking):
    counts = {l: 0 for l in LEVEL_ORDER}
    for r in tracking:
        lvl = r.get("performance_level")
        if lvl in counts:
            counts[lvl] += 1
    total = sum(counts.values())
    pct = {l: (counts[l] / total * 100 if total else 0) for l in LEVEL_ORDER}
    at_or_above = round(sum(counts[l] for l in ("EXCEEDING", "ABOVE", "EXPECTED")) / total * 100) if total else 0
    # analyze_trend() from the Builder: first half vs second half average
    trend = "insufficient_data"
    if len(tracking) >= 4:
        mid = len(tracking) // 2
        a = sum(SCORE_MAP.get(r.get("performance_level", ""), 0) for r in tracking[:mid]) / mid
        b = sum(SCORE_MAP.get(r.get("performance_level", ""), 0) for r in tracking[mid:]) / (len(tracking) - mid)
        trend = "improving" if b - a > 0.5 else "declining" if b - a < -0.5 else "stable"
    # suggested current level = typical (median) level over the last 10 observations
    recent = [SCORE_MAP[r["performance_level"]] for r in tracking[-10:] if r.get("performance_level") in SCORE_MAP]
    suggested = SCORE_TO_LVL[int(statistics.median_low(recent))] if recent else "EXPECTED"
    dates = [str(r.get("session_date"))[:10] for r in tracking]
    return {"counts": counts, "total": total, "pct": pct, "at_or_above": at_or_above,
            "trend": trend, "suggested": suggested,
            "first": min(dates) if dates else None, "last": max(dates) if dates else None}


TREND_TEXT = {"improving": "📈 Improving", "declining": "📉 Declining", "stable": "➡️ Stable",
              "insufficient_data": "Not enough data for a trend"}


def pie_png(tracking, size_in=3.0):
    """The Builder's 'Distribution' pie (make_goal_chart_mpl, bottom-left panel),
    drawn on its own: same levels, colours, start angle and labels."""
    if not tracking:
        return None
    s = pd.Series([r.get("performance_level") for r in tracking])
    counts_d = s.value_counts().reindex(TRACK_LEVELS).dropna()
    counts_d = counts_d[counts_d > 0]
    if counts_d.empty:
        return None
    fig, ax = plt.subplots(figsize=(size_in, size_in), facecolor="white")
    _, _, autotexts = ax.pie(
        counts_d.values, labels=counts_d.index, colors=[MPL_COLOR[l] for l in counts_d.index],
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8},
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Distribution", fontsize=10, color=TEAL, fontweight="bold", loc="left", pad=6)
    ax.axis("equal")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def fmt_date(iso_str, long=True):
    if not iso_str:
        return ""
    try:
        d = date.fromisoformat(str(iso_str)[:10])
        return d.strftime("%d %B %Y" if long else "%d %b").lstrip("0")
    except Exception:
        return str(iso_str)[:10]


# ══════════════════════════════════════════════════════════════════════════════
# STATE — everything this page stores lives under "tr_" keys, so switching
# student can wipe it in one go (one student's details never carry over)
# ══════════════════════════════════════════════════════════════════════════════
def reset_report_state():
    for k in list(st.session_state.keys()):
        if k.startswith("tr_"):
            del st.session_state[k]


def S(key, default=None):
    return st.session_state.get(f"tr_{key}", default)


def inc(section):
    """Is this section part of the current report type?"""
    rt = S("report_type", "Review Report")
    if rt == "Modified Report":
        return section in (S("sections") or [])
    if rt == "Review Report":
        return section in REVIEW_SECTIONS
    return True


# ── saved reports (student_reports table) ────────────────────────────────────
def load_saved_reports(student):
    c = _students_client()
    if c is None:
        return None
    try:
        return (c.table(REPORTS_TABLE).select("*").eq("student_register_id", student["id"])
                .order("updated_at", desc=True).execute().data or [])
    except Exception:
        return None          # table not created yet (or unreachable)


def _editor_state_rows(name):
    return S(f"{name}_latest") or S(f"{name}_base")


def snapshot():
    data = {}
    for k in list(st.session_state.keys()):
        if not k.startswith("tr_"):
            continue
        short = k[3:]
        if not SAVED_KEY_RE.match(short):
            continue
        v = st.session_state[k]
        if short in DATE_KEYS and isinstance(v, date):
            v = v.isoformat()
        data[short] = v
    data["editors"] = {name: _editor_state_rows(name) for name in EDITORS if _editor_state_rows(name)}
    return json.loads(json.dumps(data, default=str))


def apply_record(rec, note=None):
    """Load a saved report into the page (used as a button callback and on student pick)."""
    reset_report_state()
    st.session_state["_tr_ver"] = st.session_state.get("_tr_ver", 0) + 1
    data = rec.get("data") or {}
    for short, v in data.items():
        if short == "editors":
            continue
        if short in DATE_KEYS and v:
            try:
                v = date.fromisoformat(str(v)[:10])
            except Exception:
                continue
        st.session_state[f"tr_{short}"] = v
    for name, rows in (data.get("editors") or {}).items():
        st.session_state[f"tr_{name}_base"] = rows
        st.session_state[f"tr_{name}_latest"] = rows
    st.session_state["tr_report_type"] = rec.get("report_type") or data.get("report_type") or "Review Report"
    st.session_state["tr_record_id"] = rec.get("id")
    st.session_state["tr_record_type"] = st.session_state["tr_report_type"]
    st.session_state["tr_record_saved"] = rec.get("updated_at")
    st.session_state["tr_loaded_note"] = note or (
        f"Opened the {st.session_state['tr_report_type']} saved {fmt_date(rec.get('updated_at'))}"
        + (f" by {rec['updated_by']}" if rec.get("updated_by") else "") + ".")


def start_transition_from_review():
    """Carry everything forward into a NEW Transition Report record; the Review stays as saved."""
    st.session_state["tr_report_type"] = "Transition Report"
    st.session_state["tr_record_id"] = None
    st.session_state["tr_record_type"] = None
    st.session_state["tr_loaded_note"] = ("Started a Transition Report from the Review Report — everything has been "
                                          "carried over. Save it to keep it; the Review Report stays as it was.")


def save_report(student, teacher):
    c = _students_client()
    if c is None:
        return False, "Can't reach the database right now."
    now = datetime.utcnow().isoformat()
    payload = {
        "student_register_id": student["id"], "student_initials": student["initials"],
        "report_type": S("report_type"), "sections": [k for k, _ in SECTIONS if inc(k)],
        "data": snapshot(), "updated_by": teacher or "unknown", "updated_at": now,
    }
    same_record = S("record_id") and S("record_type") == S("report_type")
    try:
        if same_record:
            res = c.table(REPORTS_TABLE).update(payload).eq("id", S("record_id")).execute()
        else:
            payload["created_by"] = teacher or "unknown"
            res = c.table(REPORTS_TABLE).insert(payload).execute()
        row = (res.data or [None])[0]
    except Exception as e:
        return False, f"Couldn't save ({e}). Has the `{REPORTS_TABLE}` table been created?"
    if row:
        st.session_state["tr_record_id"] = row.get("id")
    st.session_state["tr_record_type"] = S("report_type")
    st.session_state["tr_record_saved"] = now
    st.session_state.pop("tr_records", None)      # refresh the list
    return True, ("Saved." if same_record else f"Saved as a new {S('report_type')}.")


def editor(name, default_rows):
    """Data-editor rows that survive being hidden (Modified Report sections) and loading a saved report."""
    if S(f"{name}_hidden"):
        st.session_state[f"tr_{name}_base"] = S(f"{name}_latest")
        st.session_state[f"tr_{name}_v"] = S(f"{name}_v", 0) + 1
        st.session_state[f"tr_{name}_hidden"] = False
    base = S(f"{name}_base") or default_rows
    if len(base) != len(default_rows):
        base = default_rows
    key = f"tr_{name}_ed_{st.session_state.get('_tr_ver', 0)}_{S(f'{name}_v', 0)}"
    RENDERED_EDITORS.add(name)
    return base, key


RENDERED_EDITORS = set()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — student by register initials
# ══════════════════════════════════════════════════════════════════════════════
st.title("📄 Transition Report Builder")
st.markdown("Generate comprehensive transition reports")

register = load_register()

with st.sidebar:
    st.header("Report Configuration")

    if register is None:
        st.error("Can't reach the Student Register right now — check your connection and reload.")
        st.stop()
    if not register:
        st.info("No current students on the register.")
        st.stop()

    reg_by_id = {str(r["id"]): r for r in register}
    picked = st.selectbox(
        "Student (register initials) *",
        options=[""] + list(reg_by_id.keys()),
        format_func=lambda sid: "Choose student…" if not sid else
        f"{reg_by_id[sid]['initials']} · {reg_by_id[sid]['program']}".rstrip(" ·"),
        key="picker_sid",
    )
    if st.session_state.get("_tr_current_sid") != picked:
        reset_report_state()
        st.session_state["_tr_current_sid"] = picked
        if picked:
            _recs = load_saved_reports(reg_by_id[picked])
            st.session_state["tr_records"] = _recs
            if _recs:
                apply_record(_recs[0])          # open this student's most recent saved report
                st.session_state["tr_records"] = _recs
    if not picked:
        st.warning("Choose a student to continue")
        st.stop()
    student = reg_by_id[picked]
    INITIALS = student["initials"]

    # keep entered values even while a section is hidden (Modified Report) — Streamlit
    # otherwise drops a widget's value when the widget isn't shown
    for _k in list(st.session_state.keys()):
        if _k.startswith("tr_") and (SAVED_KEY_RE.match(_k[3:]) or _k == "tr_print_name"):
            st.session_state[_k] = st.session_state[_k]
    st.session_state.setdefault("tr_report_type", "Review Report")
    st.session_state.setdefault("tr_report_date", date.today())
    st.session_state.setdefault("tr_pstart", date.today())
    st.session_state.setdefault("tr_pend", date.today())
    st.session_state.setdefault("tr_days_att", 0)
    st.session_state.setdefault("tr_days_tot", 1)

    st.markdown("---")
    st.radio("Report type", REPORT_TYPES, key="tr_report_type",
             captions=[REPORT_TYPE_HELP[t] for t in REPORT_TYPES])
    REPORT_TYPE = S("report_type")
    if REPORT_TYPE == "Modified Report":
        st.multiselect("Sections to include (the cover page is always included)", [k for k, _ in SECTIONS],
                       key="tr_sections", format_func=lambda k: SECTION_LABEL[k])
        if not S("sections"):
            st.warning("Choose the sections this Modified Report will include.")

    # ── saved reports for this student ──
    if "tr_records" not in st.session_state:
        st.session_state["tr_records"] = load_saved_reports(student)
    records = st.session_state["tr_records"]
    with st.expander(f"💾 Saved reports for {INITIALS}", expanded=True):
        if records is None:
            st.caption(f"Saved reports aren't set up yet — run this once in the Supabase SQL editor "
                       f"(the project with the Student Register):")
            st.code(REPORTS_TABLE_SQL, language="sql")
        elif not records:
            st.caption("Nothing saved yet for this student.")
        else:
            for rec in records:
                is_open = rec.get("id") == S("record_id")
                rc1, rc2 = st.columns([3, 1])
                rc1.markdown(f"{'**▶ ' if is_open else ''}{rec.get('report_type')}{'**' if is_open else ''}  \n"
                             f"<span style='font-size:0.75rem;color:#777'>saved {fmt_date(rec.get('updated_at'))}"
                             f"{' · ' + rec['updated_by'] if rec.get('updated_by') else ''}</span>",
                             unsafe_allow_html=True)
                rc2.button("Open", key=f"tr_open_{rec.get('id')}", disabled=is_open,
                           on_click=apply_record, args=(rec,), use_container_width=True)
        if S("record_id") and S("record_type") == "Review Report" and REPORT_TYPE == "Review Report":
            st.button("➡️ Start the Transition Report from this Review", key="tr_to_transition",
                      on_click=start_transition_from_review, use_container_width=True)
        if S("record_id") and S("record_type") and S("record_type") != REPORT_TYPE:
            st.caption(f"Saving will create a new {REPORT_TYPE} — the {S('record_type')} stays as it was.")
        SAVE_SLOT = st.container()

    print_name = st.text_input(
        "Name for this printout (optional)", key="tr_print_name",
        placeholder="Shows on the downloaded report only",
    )
    st.caption("Never saved — the report and the Document Archive copy only use initials.")
    DISPLAY_NAME = print_name.strip() or INITIALS
    WHO = (print_name.strip().split()[0] if print_name.strip() else INITIALS)

    st.markdown("---")
    report_date = st.date_input("Report Date", key="tr_report_date")
    placement_start = st.date_input("Placement Start Date", key="tr_pstart")
    placement_end = st.date_input("Placement End Date", key="tr_pend")
    st.markdown("---")
    lc_teacher = st.text_input("LC Teacher Name", key="tr_teacher")
    enrolled_school = st.text_input("Enrolled School", key="tr_school")


tab1, tab2, tab3 = st.tabs(["📝 Report Sections", "👁️ Preview", "💾 Generate"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REPORT SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
# values used later even when a section isn't part of this report type
report_goals = []
days_attended, total_days, attendance_pct = S("days_att", 0) or 0, S("days_tot", 1) or 1, 0.0

with tab1:
    st.header(f"{REPORT_TYPE}: {DISPLAY_NAME}")
    if S("loaded_note"):
        st.info(st.session_state.pop("tr_loaded_note"))
    if REPORT_TYPE == "Modified Report" and not S("sections"):
        st.info("Choose the sections to include in the sidebar — only the cover page is included so far.")

    if inc("literacy"):
        # ── LITERACY ─────────────────────────────────────────────────────────────
        st.subheader("📖 Literacy Progress")
        st.markdown("**Word Aware (Vocabulary)**")
        lc1, lc2, lc3 = st.columns(3)
        lc1.text_input("Pre-Assessment Type", key="tr_vocab_type")
        lc2.text_input("Pre Score", key="tr_vocab_pre", placeholder="/5")
        lc3.text_input("Post Score", key="tr_vocab_post", placeholder="/5")
        st.text_area("Summary", key="tr_vocab_summary", height=80)

        st.markdown("**Sounds-Write Assessments**")
        st.caption("Leave blank if not assessed")
        _sw_base, _sw_key = editor("sw", [{"Pre": "", "Post": "", "Summary": ""} for _ in SOUNDS_WRITE])
        sw_df = pd.DataFrame({
            "Skill": [s for s, _ in SOUNDS_WRITE],
            "Max Score": [m for _, m in SOUNDS_WRITE],
            "Pre": [str(r.get("Pre") or "") for r in _sw_base],
            "Post": [str(r.get("Post") or "") for r in _sw_base],
            "Summary": [str(r.get("Summary") or "") for r in _sw_base],
        })
        edited_sw = st.data_editor(
            sw_df, hide_index=True, use_container_width=True, key=_sw_key,
            disabled=["Skill", "Max Score"],
            column_config={"Pre": st.column_config.TextColumn(), "Post": st.column_config.TextColumn(),
                           "Summary": st.column_config.TextColumn(width="large")},
        )
        st.session_state["tr_sw_latest"] = edited_sw[["Pre", "Post", "Summary"]].fillna("").to_dict("records")
        st.markdown("---")

    if inc("numeracy"):
        # ── NUMERACY ─────────────────────────────────────────────────────────────
        st.subheader("🔢 Numeracy Progress")
        st.markdown("**Big Ideas in Number (BIiN)**")
        st.caption(BIIN_LEGEND + ". Set Pre and/or Post for each element that was assessed — "
                   "only assessed elements appear on the report.")
        for bi, (big_idea, elements) in enumerate(BIIN):
            with st.expander(f"{big_idea} ({len(elements)} elements)", expanded=(bi < 2)):
                _b_base, _b_key = editor(f"biin{bi}", [{"Pre": "", "Post": ""} for _ in elements])
                ed = st.data_editor(
                    pd.DataFrame({"Element": [f"{c} {n}" for c, n in elements],
                                  "Pre": [str(r.get("Pre") or "") for r in _b_base],
                                  "Post": [str(r.get("Post") or "") for r in _b_base]}),
                    hide_index=True, use_container_width=True, key=_b_key, disabled=["Element"],
                    column_config={
                        "Element": st.column_config.TextColumn(width="medium"),
                        "Pre": st.column_config.SelectboxColumn(options=BIIN_RESULTS, width="small"),
                        "Post": st.column_config.SelectboxColumn(options=BIIN_RESULTS, width="small"),
                    },
                )
                st.session_state[f"tr_biin{bi}_latest"] = ed[["Pre", "Post"]].fillna("").to_dict("records")
                st.text_area(f"Comments — {big_idea}", key=f"tr_biin_c_{bi}", height=90,
                             placeholder=f"What the student can do in {big_idea.lower()}, and what's next…")
        st.text_area("Overall numeracy comments", key="tr_numeracy", height=110,
                     placeholder="Overall progress, engagement, and the approaches that supported numeracy learning…")
        st.markdown("---")

    if inc("hits"):
        # ── HITS ─────────────────────────────────────────────────────────────────
        st.subheader("🎯 Pedagogical Strategies (HITS)")
        st.caption("Choose the High Impact Teaching Strategies that promoted positive engagement. For each one, "
                   "tick the key elements you used and say how it worked for this student.")
        st.multiselect("Strategies that promoted positive engagement", HITS_OPTIONS, key="tr_hits")
        for strat in (S("hits", []) or []):
            hi = HITS_OPTIONS.index(strat)
            with st.container(border=True):
                st.markdown(f"**{strat}**")
                st.multiselect("Key elements used", HITS_ELEMENTS[strat], key=f"tr_hits_el_{hi}")
                st.text_area("How it supported the student", key=f"tr_hits_c_{hi}", height=90,
                             placeholder=f"e.g. what {strat.lower()} looked like for this student and the difference it made…")
        st.markdown("---")

    if inc("restorative"):
        # ── RESTORATIVE ──────────────────────────────────────────────────────────
        st.subheader("🤝 Restorative Practice & Relational Safety")
        st.multiselect("Restorative strategies used", RP_OPTIONS, key="tr_rp")
        st.text_area("Comments on restorative practice", key="tr_rp_comments", height=100,
                     placeholder="Describe relational safety strategies and their effectiveness...")
        st.markdown("---")

    if inc("regulation"):
        # ── REGULATION PROFILE — pulled from the Window of Tolerance Builder ─────
        st.subheader("🌡️ Regulation Profile (Window of Tolerance)")
        if "tr_wot_lookup" not in st.session_state:
            st.session_state["tr_wot_lookup"] = load_wot_report(student)
        wot_found = st.session_state["tr_wot_lookup"]
        wot = S("wot")

        if wot:
            wc1, wc2, wc3 = st.columns([6, 1, 1])
            wc1.success(
                f"✓ Pulled from the Window of Tolerance Builder — **{INITIALS}** "
                f"({wot['status']}, updated {fmt_date(wot['updated_at'])}"
                f"{' by ' + wot['updated_by'] if wot['updated_by'] else ''}). "
                "Untick a zone to leave it out of this report."
            )
            if wc2.button("🔄 Refresh", key="tr_wot_refresh", use_container_width=True):
                fresh = load_wot_report(student)
                st.session_state["tr_wot_lookup"] = fresh
                st.session_state["tr_wot"] = fresh
                for z in WOT_ZONES:
                    st.session_state[f"tr_wotz_{z['id']}"] = bool(fresh and wot_has_content(fresh, z["id"]))
                st.rerun()
            if wc3.button("✖ Remove", key="tr_wot_remove", use_container_width=True):
                st.session_state.pop("tr_wot", None)
                st.rerun()

            for z in WOT_ZONES:
                zc = st.columns([1.3, 2, 2, 2])
                with zc[0]:
                    st.markdown(
                        f"<div style='background:{z['color']};color:#fff;border-radius:8px;padding:8px 10px;'>"
                        f"<b>{z['name']}</b><br><i style='font-size:0.8rem;opacity:.9'>{z['tag']}</i></div>",
                        unsafe_allow_html=True,
                    )
                    st.checkbox("Include", key=f"tr_wotz_{z['id']}")
                for i, (col, label) in enumerate(WOT_COLS, start=1):
                    items = wot["data"][z["id"]][col]
                    body = "".join(f"<li>{t}</li>" for t in items) if items else "<span style='color:#999'>—</span>"
                    zc[i].markdown(
                        f"<div style='background:{z['tint']};border-radius:8px;padding:8px 10px;font-size:0.85rem;min-height:70px;'>"
                        f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;color:#555;'>{label}</div>"
                        f"<ul style='margin:4px 0 0;padding-left:16px'>{body}</ul></div>",
                        unsafe_allow_html=True,
                    )

            if st.button("✍️ Draft summary from this profile", key="tr_wot_draft"):
                zones_on = {z["id"]: S(f"wotz_{z['id']}", False) for z in WOT_ZONES}
                st.session_state["tr_regulation"] = draft_wot_summary(wot, zones_on, WHO)
                st.rerun()
            st.caption("Writes a starting paragraph into the summary box below, replacing what's there — edit it as you like.")
        elif wot_found:
            wc1, wc2 = st.columns([5, 2])
            wc1.info(
                f"**Window of Tolerance report found** for {INITIALS} — {wot_found['status']}, "
                f"last updated {fmt_date(wot_found['updated_at'])}"
                f"{' by ' + wot_found['updated_by'] if wot_found['updated_by'] else ''}."
            )
            if wc2.button("Pull from Window of Tolerance Builder", type="primary",
                          key="tr_wot_pull", use_container_width=True):
                st.session_state["tr_wot"] = wot_found
                for z in WOT_ZONES:
                    st.session_state[f"tr_wotz_{z['id']}"] = wot_has_content(wot_found, z["id"])
                st.rerun()
        else:
            st.info(f"No Window of Tolerance report yet for {INITIALS}. Build one in the "
                    "Window of Tolerance Builder, or type the profile below.")

        st.text_area("Regulation Profile Summary", key="tr_regulation", height=130,
                     placeholder="Describe typical arousal patterns, triggers, and effective co-regulation strategies...")
        st.markdown("---")

    if inc("smartar"):
        # ── SMARTAR GOALS — pulled from the SMARTAR Goal Builder ─────────────────
        st.subheader("📊 Behaviour Progress: SMARTAR Goals")
        smartar_students = load_smartar_students()
        sm_student = None
        all_goals = []
        if smartar_students is None:
            st.warning("Can't reach the SMARTAR Goal Builder right now — goals can't be added to the report until it's reachable. Try reloading the page.")
        else:
            sm_student = match_smartar_student(INITIALS, smartar_students)
            if sm_student is None:
                same_prog = [s for s in smartar_students if s.get("program") and student["program"]
                             and str(student["program"]).upper().startswith(str(s["program"]).upper())]
                pool = same_prog or smartar_students
                st.warning(f"No SMARTAR Goal Builder student is filed as **{INITIALS}**. "
                           "If they're filed under a different code, choose them here:")
                names = [""] + sorted({str(s["student_name"]) for s in pool})
                if S("sm_override") not in names:
                    st.session_state["tr_sm_override"] = ""
                chosen = st.selectbox("SMARTAR student", names, key="tr_sm_override",
                                      format_func=lambda n: "Choose…" if not n else n)
                if chosen:
                    sm_student = next(s for s in pool if str(s["student_name"]) == chosen)
            if sm_student:
                if "tr_goals_cache" not in st.session_state or S("goals_cache_for") != sm_student["student_name"]:
                    st.session_state["tr_goals_cache"] = load_goals(sm_student["student_name"])
                    st.session_state["tr_goals_cache_for"] = sm_student["student_name"]
                all_goals = st.session_state["tr_goals_cache"]

        goal_by_id = {str(g["id"]): g for g in all_goals}
        if sm_student and all_goals:
            n_act = sum(1 for g in all_goals if g.get("active", True))
            gc1, gc2 = st.columns([5, 1])
            gc1.caption(f"SMARTAR Goal Builder student **{sm_student['student_name']}** · "
                        f"{n_act} active, {len(all_goals) - n_act} archived goal(s). "
                        "All are included — remove any you don't want on this report.")
            if gc2.button("🔄 Refresh goals", key="tr_goals_refresh", use_container_width=True):
                for k in ("tr_goals_cache", "tr_goals_cache_for", "tr_tracking_cache", "tr_goal_sel"):
                    st.session_state.pop(k, None)
                st.rerun()

            def _goal_label(gid):
                g = goal_by_id[gid]
                if g.get("active", True):
                    tag = "🟢 Active"
                else:
                    tag = f"🟠 Archived {fmt_date(g.get('archived_at'), long=False)}"
                txt = g.get("smartar_goal") or "No goal text"
                return f"{tag} — {txt[:90]}{'…' if len(txt) > 90 else ''}"

            # active goals first, then archived — newest first within each
            ordered = ([gid for gid, g in goal_by_id.items() if g.get("active", True)] +
                       [gid for gid, g in goal_by_id.items() if not g.get("active", True)])
            if "tr_goal_sel" not in st.session_state:
                st.session_state["tr_goal_sel"] = ordered
            else:
                known = set(S("goal_known") or [])
                new_ids = [gid for gid in ordered if known and gid not in known]
                kept = [gid for gid in S("goal_sel") if gid in goal_by_id]
                st.session_state["tr_goal_sel"] = kept + [gid for gid in new_ids if gid not in kept]
                if new_ids:
                    st.caption(f"✨ {len(new_ids)} goal(s) added in the SMARTAR Goal Builder since this report was saved "
                               "— included automatically.")
            st.session_state["tr_goal_known"] = ordered
            st.multiselect("Goals included in this report (active and archived)", ordered,
                           key="tr_goal_sel", format_func=_goal_label)
        elif sm_student:
            st.info(f"No SMARTAR goals in the SMARTAR Goal Builder for {sm_student['student_name']} yet. "
                    "Add them in the SMARTAR Goal Builder, then reload this page.")

        _sel = set(S("goal_sel") or [])
        selected_ids = ([gid for gid, g in goal_by_id.items() if g.get("active", True) and gid in _sel] +
                        [gid for gid, g in goal_by_id.items() if not g.get("active", True) and gid in _sel]) if all_goals else []

        # tracking + stats are fetched once per goal and kept for this student
        tr_cache = st.session_state.setdefault("tr_tracking_cache", {})
        for gid in selected_ids:
            if gid not in tr_cache:
                tr_cache[gid] = load_goal_tracking(goal_by_id[gid])

        pulled_goals = []
        for n, gid in enumerate(selected_ids, start=1):
            g = goal_by_id[gid]
            tracking = tr_cache.get(gid, [])
            stats = goal_stats(tracking)
            active = g.get("active", True)
            with st.expander(f"Goal {n} {'🟢' if active else '🟠'} — {(g.get('smartar_goal') or '')[:80]}",
                             expanded=(n <= 3)):
                pc1, pc2 = st.columns([1, 2])
                png = pie_png(tracking)
                with pc1:
                    if png:
                        st.image(png, use_container_width=True)
                    else:
                        st.caption("No tracking recorded for this goal yet.")
                with pc2:
                    status_line = ("🟢 **Active goal**" if active else
                                   f"🟠 **Archived** {fmt_date(g.get('archived_at'))}"
                                   + (f" — {g['archive_reason']}" if g.get("archive_reason") else ""))
                    st.markdown(status_line)
                    if stats["total"]:
                        st.markdown(
                            f"{stats['total']} observations · {fmt_date(stats['first'], False)} → "
                            f"{fmt_date(stats['last'], False)} · tracking period: {g.get('tracking_period', 'All Day')}  \n"
                            f"{TREND_TEXT[stats['trend']]} · **{stats['at_or_above']}%** at Expected or better"
                        )
                    if g.get("exclusion_goal"):
                        st.markdown(f"**🏫 Exclusion goal:** {g['exclusion_goal']}")
                    st.markdown(f"**🎯 SMARTAR goal:** {g.get('smartar_goal') or '—'}")
                    st.caption("Goal wording comes from the SMARTAR Goal Builder — edit it there if it needs changing.")

                st.markdown("**Goal Attainment Scale** (from the SMARTAR Goal Builder)")
                for lvl in LEVEL_ORDER:
                    desc = g.get(GAS_COLUMN[lvl]) or ""
                    if desc:
                        st.markdown(f"<span style='color:{LEVEL_COLOR[lvl]};font-weight:600'>{LEVEL_EMOJI[lvl]} {lvl}</span> — {desc}",
                                    unsafe_allow_html=True)
                cur_key = f"tr_g_current_{gid}"
                if cur_key not in st.session_state:
                    st.session_state[cur_key] = stats["suggested"]
                st.selectbox("Current achievement level", LEVEL_ORDER, key=cur_key,
                             format_func=lambda l: f"{LEVEL_EMOJI[l]} {l}")
                if stats["total"]:
                    st.caption(f"Suggested from the last 10 observations: {LEVEL_EMOJI[stats['suggested']]} {stats['suggested']}")

            pulled_goals.append({
                "source": "builder", "id": gid, "active": active,
                "archived_at": g.get("archived_at"), "archive_reason": g.get("archive_reason") or "",
                "tracking_period": g.get("tracking_period", "All Day"),
                "excl": g.get("exclusion_goal") or "", "smartar": g.get("smartar_goal") or "",
                "gas": {lvl: g.get(GAS_COLUMN[lvl]) or "" for lvl in LEVEL_ORDER},
                "current": S(f"g_current_{gid}", "EXPECTED"),
                "stats": stats, "pie": png,
            })

        report_goals = pulled_goals
        st.markdown("---")

    # ── ATTENDANCE & SUMMARY ─────────────────────────────────────────────────
    if inc("attendance"):
        st.subheader("📅 Attendance")
        ac1, ac2 = st.columns(2)
        with ac1:
            days_attended = st.number_input("Days Attended", min_value=0, key="tr_days_att")
            total_days = st.number_input("Total Days", min_value=1, key="tr_days_tot")
        ac2.metric("Attendance Rate", f"{(days_attended / total_days * 100 if total_days else 0):.1f}%")
    if inc("summary"):
        st.subheader("📝 Overall Progress Summary")
        st.text_area("Overall Progress Summary", key="tr_summary", height=150, label_visibility="collapsed",
                     placeholder="Summarise key achievements, challenges, and demonstrated growth...")
    if inc("recommendations"):
        st.subheader("➡️ Transition Recommendations")
        st.text_area("Transition Recommendations", key="tr_recs", height=150, label_visibility="collapsed",
                     placeholder="Specific strategies, accommodations, or supports recommended for successful transition...")
attendance_pct = days_attended / total_days * 100 if total_days else 0


# ══════════════════════════════════════════════════════════════════════════════
# GATHER EVERYTHING FOR PREVIEW / WORD
# ══════════════════════════════════════════════════════════════════════════════
def sounds_write_rows():
    rows = []
    saved = _editor_state_rows("sw") or []
    for (skill, mx), r in zip(SOUNDS_WRITE, saved):
        pre, post, summ = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip(), str(r.get("Summary") or "").strip()
        if not (pre or post or summ):
            continue
        change = ""
        try:
            change = f"{float(post) - float(pre):+g}"
        except Exception:
            pass
        rows.append({"skill": skill, "max": mx, "pre": pre, "post": post,
                     "change": change, "summary": summ})
    return rows


def biin_rows():
    """Assessed BIiN elements only (Pre and/or Post set), in framework order."""
    out = []
    for bi, (big_idea, elements) in enumerate(BIIN):
        for (code, name), r in zip(elements, _editor_state_rows(f"biin{bi}") or []):
            pre, post = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip()
            if not (pre or post):
                continue
            prog = ""
            if pre in BIIN_RANK and post in BIIN_RANK:
                d = BIIN_RANK[post] - BIIN_RANK[pre]
                prog = "Improved" if d > 0 else "Maintained" if d == 0 else "Declined"
            out.append({"big_idea": big_idea, "element": f"{code} {name}", "pre": pre, "post": post, "progress": prog})
    return out


def collect_report(name_on_report):
    wot_on = None
    if S("wot"):
        wot_on = [z for z in WOT_ZONES if S(f"wotz_{z['id']}", False)]
    return {
        "type": REPORT_TYPE, "sections": {k for k, _ in SECTIONS if inc(k)},
        "name": name_on_report, "initials": INITIALS, "program": student["program"],
        "report_date": report_date, "pstart": placement_start, "pend": placement_end,
        "teacher": (lc_teacher or "").strip(), "school": (enrolled_school or "").strip(),
        "vocab": {"type": S("vocab_type", ""), "pre": S("vocab_pre", ""), "post": S("vocab_post", ""),
                  "summary": S("vocab_summary", "")},
        "sounds_write": sounds_write_rows(),
        "biin": biin_rows(), "biin_comments": [(bi_name, S(f"biin_c_{bi}", "") or "") for bi, (bi_name, _) in enumerate(BIIN)],
        "numeracy": S("numeracy", ""),
        "hits": [{"name": h, "elements": S(f"hits_el_{HITS_OPTIONS.index(h)}", []) or [],
                  "comment": S(f"hits_c_{HITS_OPTIONS.index(h)}", "") or ""} for h in (S("hits", []) or [])],
        "rp": S("rp", []) or [], "rp_comments": S("rp_comments", ""),
        "wot": S("wot"), "wot_zones": wot_on, "regulation": S("regulation", ""),
        "goals": report_goals,
        "attendance": (days_attended, total_days, attendance_pct),
        "summary": S("summary", ""), "recs": S("recs", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
# WORD DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════
def build_docx(rep):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def shade(cell, hex_colour):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_colour.lstrip("#"))
        tcPr.append(shd)

    def hex_rgb(h):
        h = h.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(1.8))
    sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.6)
    base = doc.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10.5)

    def heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = hex_rgb(TEAL)
        return p

    def sub(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text.upper())
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    def para(text, empty="Not entered."):
        p = doc.add_paragraph()
        if text and str(text).strip():
            p.add_run(str(text).strip())
        else:
            r = p.add_run(empty)
            r.italic = True
            r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        return p

    def table(rows, header=True, widths=None, size=9.5):
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j)
                cell.text = ""
                run = cell.paragraphs[0].add_run(str(val))
                run.font.size = Pt(size)
                if header and i == 0:
                    run.bold = True
                    shade(cell, "EEF2EC")
                if widths:
                    cell.width = widths[j]
        return t

    # ── cover page (every report type) ──
    for _ in range(6):
        doc.add_paragraph()
    cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ct = cp.add_run(rep["type"].upper()); ct.bold = True; ct.font.size = Pt(36); ct.font.color.rgb = hex_rgb(TEAL)
    cp2 = doc.add_paragraph(); cp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c2 = cp2.add_run("LEARNING AND BEHAVIOUR UNIT"); c2.bold = True; c2.font.size = Pt(14)
    c2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    cp3 = doc.add_paragraph(); cp3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c3 = cp3.add_run("Cowandilla Learning Centre"); c3.font.size = Pt(12); c3.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    for _ in range(3):
        doc.add_paragraph()
    fmt = lambda d: d.strftime("%d %B %Y").lstrip("0")
    cover_rows = [("Student name", rep["name"] + (f" ({rep['program']})" if rep["program"] else "")),
                  ("Date", fmt(rep["report_date"])),
                  ("Enrolled site", rep["school"] or "—"),
                  ("LC teacher", rep["teacher"] or "—"),
                  ("Placement", f"{fmt(rep['pstart'])} to {fmt(rep['pend'])}")]
    ctab = doc.add_table(rows=len(cover_rows), cols=2)
    ctab.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i_, (k_, v_) in enumerate(cover_rows):
        kr = ctab.cell(i_, 0).paragraphs[0]; kr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        kk = kr.add_run(k_ + ":"); kk.bold = True; kk.font.size = Pt(13)
        vv = ctab.cell(i_, 1).paragraphs[0].add_run(v_); vv.font.size = Pt(13)
        ctab.cell(i_, 0).width, ctab.cell(i_, 1).width = Cm(5.5), Cm(9.5)
    if rep["type"] == "Modified Report":
        for _ in range(2):
            doc.add_paragraph()
        mp = doc.add_paragraph(); mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        mr = mp.add_run("This modified report includes: " +
                        (", ".join(SECTION_LABEL[k] for k, _ in SECTIONS if k in rep["sections"]) or "cover page only"))
        mr.italic = True; mr.font.size = Pt(10.5); mr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    doc.add_page_break()

    if "literacy" in rep["sections"]:
        # ── literacy ──
        heading("Literacy Progress")
        sub("Word Aware (Vocabulary)")
        v = rep["vocab"]
        if v["type"] or v["pre"] or v["post"]:
            table([["Assessment", "Pre", "Post"], [v["type"] or "—", v["pre"] or "—", v["post"] or "—"]])
        para(v["summary"])
        sub("Sounds-Write")
        if rep["sounds_write"]:
            rows = [["Skill", "Pre", "Post", "Change", "Summary"]]
            for s_ in rep["sounds_write"]:
                rows.append([s_["skill"], f"{s_['pre']} / {s_['max']}" if s_["pre"] else "—",
                             f"{s_['post']} / {s_['max']}" if s_["post"] else "—", s_["change"] or "—", s_["summary"]])
            table(rows)
        else:
            para("", empty="Not assessed.")

    if "numeracy" in rep["sections"]:
        heading("Numeracy Progress")
        sub("Big Ideas in Number")
        intro = doc.add_paragraph()
        ir = intro.add_run("The Big Ideas in Number is a framework of numeracy concepts providing the foundation for "
                           "developing number sense. Number sense is fundamental to mathematical learning.")
        ir.font.size = Pt(9.5)
        if rep["biin"]:
            lg = doc.add_paragraph()
            for label, fill in [("Mastered (90–100%)", "B7DE9B"), ("Developing (70–80%)", "FFE38A"), ("Needs improvement (< 70%)", "F4A9A3")]:
                r_ = lg.add_run(f"  {label}  ")
                r_.font.size = Pt(8.5)
                rPr = r_._element.get_or_add_rPr()
                shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
                rPr.append(shd)
                lg.add_run("  ")
            bt = doc.add_table(rows=1 + len(rep["biin"]), cols=5)
            bt.style = "Table Grid"
            for j, h in enumerate(["Big idea", "Element", "Pre", "Post", "Progress"]):
                c = bt.cell(0, j)
                run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
                shade(c, "EEF2EC")
            prev = None
            for i, row in enumerate(rep["biin"], start=1):
                vals = [row["big_idea"] if row["big_idea"] != prev else "", row["element"], row["pre"] or "—",
                        row["post"] or "—", row["progress"]]
                prev = row["big_idea"]
                for j, val in enumerate(vals):
                    c = bt.cell(i, j)
                    run = c.paragraphs[0].add_run(val); run.font.size = Pt(9)
                    if j == 0 and val:
                        run.bold = True
                    if j in (2, 3) and val in BIIN_FILL:
                        shade(c, BIIN_FILL[val])
            for row_ in bt.rows:
                for j, w in enumerate([Cm(3.6), Cm(5.4), Cm(2.9), Cm(2.9), Cm(2.6)]):
                    row_.cells[j].width = w
        else:
            para("", empty="Not assessed.")
        any_comment = False
        for bi_name, comment in rep["biin_comments"]:
            if comment.strip():
                any_comment = True
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.add_run(f"{bi_name} — ").bold = True
                p.add_run(comment.strip())
        if rep["numeracy"].strip():
            para(rep["numeracy"])
        elif not any_comment and rep["biin"]:
            pass

    if "hits" in rep["sections"]:
        heading("Pedagogical Strategies (HITS)")
        if rep["hits"]:
            intro = doc.add_paragraph()
            ir = intro.add_run("The following High Impact Teaching Strategies, and the key elements listed, "
                               "promoted positive student engagement in learning.")
            ir.font.size = Pt(9.5)
            ht = doc.add_table(rows=1 + len(rep["hits"]), cols=3)
            ht.style = "Table Grid"
            for j, h in enumerate(["Strategy", "Key elements used", "How it supported the student"]):
                c = ht.cell(0, j)
                run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
                shade(c, "EEF2EC")
            for i, h in enumerate(rep["hits"], start=1):
                sc = ht.cell(i, 0)
                sr = sc.paragraphs[0].add_run(h["name"]); sr.bold = True; sr.font.size = Pt(9.5)
                shade(sc, "FBE7A1")
                ec = ht.cell(i, 1)
                if h["elements"]:
                    for k, el in enumerate(h["elements"]):
                        par_ = ec.paragraphs[0] if k == 0 else ec.add_paragraph()
                        par_.add_run("• " + el).font.size = Pt(8.5)
                else:
                    ec.paragraphs[0].add_run("—").font.size = Pt(9)
                cc_ = ht.cell(i, 2)
                cr = cc_.paragraphs[0].add_run(h["comment"].strip() or "—"); cr.font.size = Pt(9)
            for row_ in ht.rows:
                for j, w in enumerate([Cm(3.3), Cm(5.6), Cm(8.5)]):
                    row_.cells[j].width = w
        else:
            para("", empty="Not entered.")

    if "restorative" in rep["sections"]:
        heading("Restorative Practice & Relational Safety")
        if rep["rp"]:
            doc.add_paragraph(" · ".join(rep["rp"])).runs[0].bold = True
        para(rep["rp_comments"], empty="No comments entered." if rep["rp"] else "Not entered.")

    if "regulation" in rep["sections"]:
        # ── regulation profile ──
        heading("Regulation Profile (Window of Tolerance)")
        zones = rep["wot_zones"] or []
        if rep["wot"] and zones:
            t = doc.add_table(rows=1 + len(zones), cols=4)
            t.style = "Table Grid"
            hdr = ["Zone"] + [lbl for _, lbl in WOT_COLS]
            for j, h in enumerate(hdr):
                c = t.cell(0, j)
                run = c.paragraphs[0].add_run(h)
                run.bold = True
                run.font.size = Pt(9)
                shade(c, "EEF2EC")
            for i, z in enumerate(zones, start=1):
                zc = t.cell(i, 0)
                zr = zc.paragraphs[0].add_run(z["name"])
                zr.bold = True
                zr.font.size = Pt(9.5)
                zr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                tg = zc.add_paragraph().add_run(z["tag"])
                tg.italic = True
                tg.font.size = Pt(8)
                tg.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                shade(zc, z["color"])
                for j, (col, _) in enumerate(WOT_COLS, start=1):
                    c = t.cell(i, j)
                    shade(c, z["tint"])
                    items = rep["wot"]["data"][z["id"]][col]
                    if not items:
                        c.paragraphs[0].add_run("—").font.size = Pt(9)
                    for k, it in enumerate(items):
                        p = c.paragraphs[0] if k == 0 else c.add_paragraph()
                        run = p.add_run("• " + it)
                        run.font.size = Pt(8.5)
            for row in t.rows:
                row.cells[0].width = Cm(3.3)
            note = doc.add_paragraph()
            nr = note.add_run(f"From the Window of Tolerance Builder ({rep['initials']}), "
                              f"updated {fmt_date(rep['wot']['updated_at'])}.")
            nr.italic = True
            nr.font.size = Pt(8)
            nr.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
            if rep["regulation"].strip():
                para(rep["regulation"])
        else:
            para(rep["regulation"])

    if "smartar" in rep["sections"]:
        # ── SMARTAR goals ──
        heading("Behaviour Progress: SMARTAR Goals")
        if not rep["goals"]:
            para("", empty="No SMARTAR goals recorded in the SMARTAR Goal Builder.")
        else:
            ov = doc.add_table(rows=1 + len(rep["goals"]), cols=4)
            ov.style = "Table Grid"
            for j, h in enumerate(["#", "Exclusion goal", "SMARTAR goal", "Status"]):
                c = ov.cell(0, j)
                run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
                shade(c, "EEF2EC")
            for i, g in enumerate(rep["goals"], start=1):
                vals = [str(i), g["excl"] or "—", g["smartar"] or "—",
                        "Active" if g["active"] else f"Archived {fmt_date(g['archived_at'], long=False)}"]
                for j, val in enumerate(vals):
                    ov.cell(i, j).paragraphs[0].add_run(val).font.size = Pt(8.5)
            for row_ in ov.rows:
                for j, w in enumerate([Cm(0.8), Cm(5.2), Cm(9.0), Cm(2.4)]):
                    row_.cells[j].width = w
        for n, g in enumerate(rep["goals"], start=1):
            sub(f"Goal {n}")
            if g["excl"].strip():
                p = doc.add_paragraph()
                p.add_run("Exclusion goal: ").bold = True
                p.add_run(g["excl"].strip())
            p = doc.add_paragraph()
            p.add_run("SMARTAR goal: ").bold = True
            p.add_run(g["smartar"].strip() or "—")

            if g["source"] == "builder":
                st_ = g["stats"]
                box = doc.add_table(rows=1, cols=2)
                box.style = "Table Grid"
                pic_cell, txt_cell = box.cell(0, 0), box.cell(0, 1)
                pic_cell.width, txt_cell.width = Cm(5.6), Cm(11.8)
                if g["pie"]:
                    pic_cell.paragraphs[0].add_run().add_picture(BytesIO(g["pie"]), width=Cm(5.2))
                else:
                    pic_cell.paragraphs[0].add_run("No tracking recorded.").italic = True
                tp = txt_cell.paragraphs[0]
                if g["active"]:
                    tp.add_run("Active goal.").bold = True
                else:
                    tp.add_run("Archived goal").bold = True
                    tp.add_run(f" — archived {fmt_date(g['archived_at'])}"
                               + (f" ({g['archive_reason']})" if g["archive_reason"] else "") + ".")
                if st_["total"]:
                    lines = [
                        f"{st_['total']} observations recorded from {fmt_date(st_['first'])} to {fmt_date(st_['last'])} "
                        f"(tracking period: {g['tracking_period']}).",
                        f"{st_['at_or_above']}% were at Expected or better.",
                    ]
                    lines.append(" · ".join(f"{lvl} {st_['pct'][lvl]:.0f}%" for lvl in TRACK_LEVELS))
                    trend_line = {"improving": "Performance improved over the goal (second half of observations compared with the first half).",
                                  "declining": "Performance declined over the goal (second half of observations compared with the first half).",
                                  "stable": "Performance stayed stable across the goal."}.get(st_["trend"])
                    if trend_line:
                        lines.append(trend_line)
                    for line in lines:
                        run = txt_cell.add_paragraph().add_run(line)
                        run.font.size = Pt(9.5)
                for par in pic_cell.paragraphs + txt_cell.paragraphs:
                    par.paragraph_format.space_after = Pt(2)
                doc.add_paragraph().paragraph_format.space_after = Pt(0)

            gt = doc.add_table(rows=1 + len(LEVEL_ORDER), cols=2)
            gt.style = "Table Grid"
            for j, h in enumerate(["Level", "Descriptor"]):
                c = gt.cell(0, j)
                run = c.paragraphs[0].add_run(h)
                run.bold = True
                run.font.size = Pt(9)
                shade(c, "EEF2EC")
            for i, lvl in enumerate(LEVEL_ORDER, start=1):
                is_cur = g["current"] == lvl
                lc_, dc = gt.cell(i, 0), gt.cell(i, 1)
                r1 = lc_.paragraphs[0].add_run(lvl + ("  ✓ current" if is_cur else ""))
                r1.font.size = Pt(9)
                r1.bold = is_cur
                r1.font.color.rgb = hex_rgb(LEVEL_COLOR[lvl])
                r2 = dc.paragraphs[0].add_run(g["gas"].get(lvl, "") or "—")
                r2.font.size = Pt(9)
                r2.bold = is_cur
                if is_cur:
                    shade(lc_, "E3EFE8")
                    shade(dc, "E3EFE8")
                lc_.width, dc.width = Cm(4.0), Cm(13.4)

    # ── attendance + summaries ──
    if "attendance" in rep["sections"]:
        heading("Attendance")
        a, t_, pct = rep["attendance"]
        para(f"{a} of {t_} days ({pct:.1f}%)")
    if "summary" in rep["sections"]:
        heading("Overall Progress Summary")
        para(rep["summary"])
    if "recommendations" in rep["sections"]:
        heading("Transition Recommendations")
        para(rep["recs"])

    foot = sec.footer.paragraphs[0]
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = foot.add_run(f"{rep['type']} | Cowandilla Learning Centre LBU | {rep['initials']} | "
                      f"Generated {datetime.now().strftime('%d %b %Y')}")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    rep = collect_report(DISPLAY_NAME)
    st.header(f"{rep['type']}: {rep['name']}")
    st.markdown(
        f"**Report date:** {rep['report_date'].strftime('%d %B %Y').lstrip('0')} · "
        f"**Placement:** {rep['pstart'].strftime('%d %b %Y')} to {rep['pend'].strftime('%d %b %Y')}  \n"
        f"**LC teacher:** {rep['teacher'] or '—'} · **Enrolled school:** {rep['school'] or '—'}"
    )
    st.markdown("---")

    if "literacy" in rep["sections"]:
        st.markdown("#### Literacy Progress")
        v = rep["vocab"]
        if v["pre"] or v["post"]:
            st.write(f"Word Aware ({v['type'] or 'assessment'}): pre {v['pre'] or '—'}, post {v['post'] or '—'}")
        if v["summary"]:
            st.write(v["summary"])
        if rep["sounds_write"]:
            st.dataframe(pd.DataFrame(rep["sounds_write"]).rename(columns={
                "skill": "Skill", "max": "Max", "pre": "Pre", "post": "Post", "change": "Change", "summary": "Summary"}),
                hide_index=True, use_container_width=True)
    if "numeracy" in rep["sections"]:
        st.markdown("#### Numeracy Progress")
        if rep["biin"]:
            _fill = {k: "#" + v for k, v in BIIN_FILL.items()}
            bdf = pd.DataFrame(rep["biin"]).rename(columns={"big_idea": "Big idea", "element": "Element", "pre": "Pre",
                                                             "post": "Post", "progress": "Progress"})
            st.dataframe(bdf.style.map(lambda v: f"background-color:{_fill[v]}" if v in _fill else "", subset=["Pre", "Post"]),
                         hide_index=True, use_container_width=True)
        else:
            st.write("_BIiN not assessed._")
        for bi_name, comment in rep["biin_comments"]:
            if comment.strip():
                st.write(f"**{bi_name}** — {comment}")
        if rep["numeracy"]:
            st.write(rep["numeracy"])
    if "hits" in rep["sections"]:
        st.markdown("#### Pedagogical Strategies (HITS)")
        if not rep["hits"]:
            st.write("_None selected_")
        for h in rep["hits"]:
            st.markdown(f"**{h['name']}**" + ("" if not h["elements"] else "  \n" + "  \n".join("• " + e for e in h["elements"])))
            if h["comment"]:
                st.write(h["comment"])
    if "restorative" in rep["sections"]:
        st.markdown("#### Restorative Practice & Relational Safety")
        st.write(", ".join(rep["rp"]) or "_None selected_")
        if rep["rp_comments"]:
            st.write(rep["rp_comments"])

    if "regulation" in rep["sections"]:
        st.markdown("#### Regulation Profile (Window of Tolerance)")
        if rep["wot"] and rep["wot_zones"]:
            html = ("<table style='width:100%;border-collapse:collapse;font-size:0.82rem'><tr>"
                    + "".join(f"<th style='border:1px solid #cfd6cc;background:#EEF2EC;padding:5px;text-align:left'>{h}</th>"
                              for h in ["Zone"] + [l for _, l in WOT_COLS]) + "</tr>")
            for z in rep["wot_zones"]:
                html += (f"<tr><td style='border:1px solid #cfd6cc;background:{z['color']};color:#fff;padding:6px;width:18%'>"
                         f"<b>{z['name']}</b><br><i style='font-size:0.75rem'>{z['tag']}</i></td>")
                for col, _ in WOT_COLS:
                    items = rep["wot"]["data"][z["id"]][col]
                    body = "<ul style='margin:0;padding-left:16px'>" + "".join(f"<li>{t}</li>" for t in items) + "</ul>" if items else "—"
                    html += f"<td style='border:1px solid #cfd6cc;background:{z['tint']};padding:6px;vertical-align:top'>{body}</td>"
                html += "</tr>"
            st.markdown(html + "</table>", unsafe_allow_html=True)
        st.write(rep["regulation"] or ("" if rep["wot_zones"] else "_Not entered._"))

    if "smartar" in rep["sections"]:
        st.markdown("#### Behaviour Progress: SMARTAR Goals")
        if not rep["goals"]:
            st.write("_No goals entered._")
        for n, g in enumerate(rep["goals"], start=1):
            st.markdown(f"**Goal {n}**" + (" — 🟢 Active" if g["active"] else f" — 🟠 Archived {fmt_date(g['archived_at'])}"))
            if g["excl"].strip():
                st.write(f"**Exclusion goal:** {g['excl']}")
            st.write(f"**SMARTAR goal:** {g['smartar']}")
            if g["source"] == "builder":
                c1, c2 = st.columns([1, 2])
                if g["pie"]:
                    c1.image(g["pie"], use_container_width=True)
                s_ = g["stats"]
                if s_["total"]:
                    c2.write(f"{s_['total']} observations, {fmt_date(s_['first'])} to {fmt_date(s_['last'])}. "
                             f"{s_['at_or_above']}% at Expected or better. {TREND_TEXT[s_['trend']]}")
            st.write("**Current level:** " + LEVEL_EMOJI[g["current"]] + " " + g["current"]
                     + (f" — {g['gas'][g['current']]}" if g["gas"].get(g["current"]) else ""))

    if "attendance" in rep["sections"]:
        st.markdown("#### Attendance")
        a, t_, pct = rep["attendance"]
        st.write(f"{a} of {t_} days ({pct:.1f}%)")
    if "summary" in rep["sections"]:
        st.markdown("#### Overall Progress Summary")
        st.write(rep["summary"] or "_Not entered._")
    if "recommendations" in rep["sections"]:
        st.markdown("#### Transition Recommendations")
        st.write(rep["recs"] or "_Not entered._")
    if not rep["sections"]:
        st.info("Only the cover page is included so far — choose sections in the sidebar.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GENERATE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header(f"Generate {REPORT_TYPE}")
    rep = collect_report(DISPLAY_NAME)
    filled = {
        "literacy": bool(rep["vocab"]["summary"] or rep["vocab"]["pre"] or rep["sounds_write"]),
        "numeracy": bool(rep["biin"] or rep["numeracy"]), "hits": bool(rep["hits"]),
        "restorative": bool(rep["rp"] or rep["rp_comments"]),
        "regulation": bool(rep["regulation"] or rep["wot_zones"]), "smartar": bool(rep["goals"]),
        "attendance": rep["attendance"][0] > 0, "summary": bool(rep["summary"]), "recommendations": bool(rep["recs"]),
    }
    checks = [("Cover page — LC Teacher", bool(rep["teacher"])), ("Cover page — Enrolled School", bool(rep["school"]))]
    checks += [(SECTION_LABEL[k], filled[k]) for k, _ in SECTIONS if k in rep["sections"]]
    cc = st.columns(2)
    for i, (label, ok) in enumerate(checks):
        cc[i % 2].markdown(("✅ " if ok else "⬜ ") + label)

    if not rep["teacher"] or not rep["school"]:
        st.error("Please enter LC Teacher name and Enrolled School in the sidebar.")
    else:
        today_tag = datetime.now().strftime("%Y%m%d")
        type_tag = REPORT_TYPE.replace(" ", "_")
        docx_bytes = build_docx(rep)
        st.download_button(
            f"📄 Download {REPORT_TYPE} (Word)", data=docx_bytes, type="primary", use_container_width=True,
            file_name=f"{INITIALS}_{type_tag}_{today_tag}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        if print_name.strip():
            st.caption(f"This download shows the name “{print_name.strip()}”. The Document Archive copy uses initials only.")

        st.markdown("---")
        st.markdown("**🗄️ File to the Document Archive**")
        if not ARCHIVE_AVAILABLE:
            st.caption("The Document Archive isn't available on this deployment.")
        else:
            st.caption(f"Files an initials-only copy into {INITIALS}'s Document Archive folder.")
            if st.button("Save to Document Archive", key="tr_archive_btn"):
                archive_bytes = docx_bytes if not print_name.strip() else build_docx(collect_report(INITIALS))
                saved = archive_document(
                    source_tool="Transition Report Builder",
                    doc_type=REPORT_TYPE,
                    title=f"{REPORT_TYPE} — {INITIALS} — {datetime.now():%d %b %Y}",
                    file_bytes=archive_bytes,
                    filename=f"{INITIALS}_{type_tag}_{today_tag}.docx",
                    student_initials=INITIALS,
                    created_by=rep["teacher"] or "unknown",
                )
                if saved:
                    st.success(f"🗄️ Saved to {INITIALS}'s Document Archive folder.")
                else:
                    st.error("⚠️ Could NOT save to the Document Archive — the report was NOT filed. "
                             "You can still download it above.")

# editors not shown this run (Modified Report sections switched off) keep their rows for next time
for _name in EDITORS:
    if _name not in RENDERED_EDITORS and S(f"{_name}_latest") is not None:
        st.session_state[f"tr_{_name}_hidden"] = True

with SAVE_SLOT:
    _same = S("record_id") and S("record_type") == REPORT_TYPE
    if st.button(f"💾 Save {REPORT_TYPE}" if _same or not S("record_id") else f"💾 Save as new {REPORT_TYPE}",
                 key="tr_save_btn", type="primary", use_container_width=True, disabled=records is None):
        ok, msg = save_report(student, (lc_teacher or "").strip())
        (st.success if ok else st.error)(msg)
        if ok:
            st.toast(f"{REPORT_TYPE} saved for {INITIALS}")
    if S("record_saved"):
        st.caption(f"Last saved {fmt_date(S('record_saved'))}. Save regularly — the report is built up over the placement.")

st.markdown("---")
st.caption("Transition Report Builder · Review, Transition and Modified reports | Cowandilla Learning Centre LBU")
