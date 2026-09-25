"""
NIT & Staff Absence Tracker — CLC-LBU Portal
=============================================
Replaces the "NIT Term X.xlsx" weekly-sheet workbook. Fresh start:
records begin Term 4 2026 and continue term by term through 2027
(add later years in Setup → Term dates). No workbook data is imported.

THE BIG CHANGE: EXCEPTION-BASED RECORDING
  Each teacher has a rostered NIT schedule (minutes per weekday). The tool
  ASSUMES rostered NIT was received unless admin logs an exception:
     - Missed NIT       (NIT not given — covering, no relief, incident, etc.)
     - Additional NIT   (extra / make-up NIT given)
     - Staff absence    (full/part day, by leave type; can remove that day's
                         NIT from entitlement so it isn't counted as "owed")
     - Cancel NIT for a whole day (e.g. NIT specialist away) — one click
       logs missed NIT for everyone rostered that day.
  So admin only records what went differently — not every session.

  Balance  = Additional − Missed (+ opening balance carried forward)
     negative  →  NIT OWED to the teacher
     positive  →  teacher received MORE than entitlement
  Displayed as "-1h 40m" / "+30m" — no more Excel negative-time ####.

TABS
  This Week   — week grid: who had NIT, missed, absent, extra; week balances
  Log         — record missed / additional / absence / whole-day cancel
  Leadership  — term balances, owed/over status, trend, reasons, absences
  History     — view / filter / delete entries (corrections)
  Setup       — staff, FTE, rostered NIT per day, entitlement, term dates,
                closure days, opening balances (carry forward)
  Export      — Excel term report

SETUP BEFORE FIRST RUN
  1. Run nit_tracker_schema.sql once in the Supabase SQL editor.
  2. Put this file in pages/ (rename number if it clashes with your sidebar).
  3. Uses the same Supabase secrets as other tools (env vars on Render or
     st.secrets): SUPABASE_URL + SUPABASE_SERVICE_KEY / SUPABASE_KEY, or a
     [supabase] section with url / key.
  4. Gated by the shared confidential_auth.py (admin/leadership tier).
  5. Go to Setup → set each staff member's FTE and rostered NIT minutes per
     day, and confirm the weekly entitlement per 1.0 FTE.
"""

import streamlit as st

try:
    st.set_page_config(page_title="NIT & Absence Tracker | CLC-LBU", page_icon="⏱️", layout="wide")
except Exception:
    pass

import io
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.dirname(os.path.abspath(__file__))):
    if p not in sys.path:
        sys.path.insert(0, p)


# ══════════════════════════════════════════════════════════════════════════════
# SECRETS
# ══════════════════════════════════════════════════════════════════════════════
def _secret(*names, section=None, section_keys=()):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    try:
        for n in names:
            if n in st.secrets:
                return st.secrets[n]
        if section and section in st.secrets:
            for k in section_keys:
                if k in st.secrets[section]:
                    return st.secrets[section][k]
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# CONFIDENTIAL GATE (shared confidential_auth.py, with a local fallback)
# ══════════════════════════════════════════════════════════════════════════════
def _gate():
    try:
        import confidential_auth as ca  # repo root module
    except Exception:
        ca = None
    if ca is not None:
        for fn in ("require_confidential_auth", "require_confidential", "require_auth",
                   "check_confidential_password", "check_password"):
            f = getattr(ca, fn, None)
            if callable(f):
                if f() is False:
                    st.stop()
                return
    # Fallback: local gate sharing the same session flag as confidential_auth
    if st.session_state.get("clc_confidential_ok"):
        return
    pw_expected = _secret("CONFIDENTIAL_PASSWORD", "ADMIN_PASSWORD")
    st.markdown("### 🔒 NIT & Absence Tracker")
    st.caption("Admin and leadership only.")
    pw = st.text_input("Confidential password", type="password")
    if st.button("Unlock"):
        if pw_expected and pw == pw_expected:
            st.session_state["clc_confidential_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


_gate()


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def sb():
    from supabase import create_client
    url = _secret("SUPABASE_URL", section="supabase", section_keys=("url", "SUPABASE_URL"))
    key = _secret("SUPABASE_SERVICE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY",
                  section="supabase", section_keys=("key", "service_key", "SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError("Supabase URL/key not found in environment or secrets.")
    return create_client(url, key)


try:
    sb()
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.stop()

T_STAFF = "nit_staff"
T_ENTRIES = "nit_entries"
T_OPEN = "nit_opening_balances"
T_SETTINGS = "nit_settings"

DAYS = ["mon_min", "tue_min", "wed_min", "thu_min", "fri_min"]
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

DEFAULT_CONFIG = {
    "base_minutes_fte1": 250,
    "absence_forfeits_nit": True,
    "terms": [
        {"year": 2026, "term": 4, "start": "2026-10-12", "end": "2026-12-11"},
        {"year": 2027, "term": 1, "start": "2027-01-27", "end": "2027-04-09"},
        {"year": 2027, "term": 2, "start": "2027-04-26", "end": "2027-07-02"},
        {"year": 2027, "term": 3, "start": "2027-07-19", "end": "2027-09-24"},
        {"year": 2027, "term": 4, "start": "2027-10-11", "end": "2027-12-10"},
    ],
    "closures": [
        {"date": "2027-03-08", "label": "Adelaide Cup Day"},
        {"date": "2027-03-26", "label": "Good Friday"},
        {"date": "2027-03-29", "label": "Easter Monday"},
        {"date": "2027-06-14", "label": "King's Birthday"},
    ],
    "missed_reasons": [
        "Covering a class (staff shortage)",
        "No relief teacher available",
        "Student behaviour / critical incident",
        "Meeting scheduled over NIT",
        "Excursion / event / whole-site activity",
        "NIT provider absent",
        "Other",
    ],
    "additional_reasons": [
        "Make-up for missed NIT",
        "Extra release (leadership approved)",
        "Reporting / assessment time",
        "Other",
    ],
    "absence_types": [
        "Sick leave",
        "Carer's leave",
        "Personal / annual leave",
        "Professional development (off site)",
        "School business (off site)",
        "Other",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(m, signed=False):
    """Minutes → '1h 05m' / '-40m' / '+2h 00m'."""
    try:
        m = int(round(float(m or 0)))
    except Exception:
        m = 0
    sign = "-" if m < 0 else ("+" if signed and m > 0 else "")
    h, mm = divmod(abs(m), 60)
    return f"{sign}{h}h {mm:02d}m" if h else f"{sign}{mm}m"


def to_date(v):
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, pd.Timestamp):
        return v.date()
    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def monday_of(d):
    return d - timedelta(days=d.weekday())


def _stretch():
    """width='stretch' on newer Streamlit, use_container_width on older."""
    try:
        major, minor = (int(x) for x in st.__version__.split(".")[:2])
        return {"width": "stretch"} if (major, minor) >= (1, 46) else {"use_container_width": True}
    except Exception:
        return {"use_container_width": True}


WIDE = _stretch()


def rerun():
    (getattr(st, "rerun", None) or st.experimental_rerun)()


def refresh():
    st.cache_data.clear()


def who():
    return st.session_state.get("nit_entered_by", "").strip()


# ══════════════════════════════════════════════════════════════════════════════
# DATA ACCESS
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_all(build):
    out, start, step = [], 0, 1000
    while True:
        rows = build().range(start, start + step - 1).execute().data or []
        out += rows
        if len(rows) < step:
            return out
        start += step


@st.cache_data(ttl=60, show_spinner=False)
def load_config():
    cfg = {k: (v.copy() if isinstance(v, list) else v) for k, v in DEFAULT_CONFIG.items()}
    try:
        res = sb().table(T_SETTINGS).select("*").eq("key", "config").execute()
        if res.data:
            stored = res.data[0].get("value") or {}
            cfg.update({k: v for k, v in stored.items() if v is not None})
    except Exception:
        pass
    return cfg


def save_config(cfg):
    sb().table(T_SETTINGS).upsert({"key": "config", "value": cfg,
                                   "updated_at": datetime.now().isoformat()}).execute()
    refresh()


@st.cache_data(ttl=60, show_spinner=False)
def load_staff():
    return _fetch_all(lambda: sb().table(T_STAFF).select("*").order("display_order").order("name"))


@st.cache_data(ttl=60, show_spinner=False)
def load_entries(start_iso, end_iso):
    return _fetch_all(lambda: sb().table(T_ENTRIES).select("*")
                      .gte("entry_date", start_iso).lte("entry_date", end_iso)
                      .order("entry_date"))


@st.cache_data(ttl=60, show_spinner=False)
def load_opening(year, term):
    return _fetch_all(lambda: sb().table(T_OPEN).select("*").eq("year", year).eq("term", term))


def insert_entries(rows):
    if rows:
        sb().table(T_ENTRIES).insert(rows).execute()
        refresh()


def delete_entries(ids):
    for i in ids:
        sb().table(T_ENTRIES).delete().eq("id", int(i)).execute()
    refresh()


# ══════════════════════════════════════════════════════════════════════════════
# TERM / CALCULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def term_list(cfg):
    out = []
    for t in cfg.get("terms", []):
        try:
            out.append({"year": int(t["year"]), "term": int(t["term"]),
                        "start": to_date(t["start"]), "end": to_date(t["end"])})
        except Exception:
            continue
    return sorted(out, key=lambda x: (x["year"], x["term"]))


def term_label(t):
    return f"{t['year']} Term {t['term']}"


def current_term(terms, today=None):
    today = today or date.today()
    for t in terms:
        if t["start"] <= today <= t["end"]:
            return t
    past = [t for t in terms if t["end"] < today]
    upcoming = [t for t in terms if t["start"] > today]
    if past:
        return past[-1]          # holidays: stay on the term just finished
    return upcoming[0] if upcoming else (terms[0] if terms else None)


def term_week_count(t):
    return ((monday_of(t["end"]) - monday_of(t["start"])).days // 7) + 1


def week_no(t, d):
    return ((monday_of(d) - monday_of(t["start"])).days // 7) + 1


def week_dates(t, wk):
    mon = monday_of(t["start"]) + timedelta(weeks=wk - 1)
    return [mon + timedelta(days=i) for i in range(5)]


def closure_set(cfg):
    out = {}
    for c in cfg.get("closures", []):
        try:
            out[to_date(c["date"])] = c.get("label", "Closed")
        except Exception:
            pass
    return out


def rostered(s, d):
    return int(s.get(DAYS[d.weekday()]) or 0) if d.weekday() < 5 else 0


def build_daily(staff, entries, t, cfg, upto=None):
    """One row per staff member per school day in the term (optionally up to a date)."""
    closures = closure_set(cfg)
    forfeits = bool(cfg.get("absence_forfeits_nit", True))
    end = min(t["end"], upto) if upto else t["end"]
    days = [d for d in daterange(t["start"], end) if d.weekday() < 5 and d not in closures]

    agg = {}
    for e in entries:
        k = (e["staff_id"], to_date(e["entry_date"]))
        a = agg.setdefault(k, {"missed": 0, "additional": 0, "absence": 0, "absent_days": 0.0})
        et = e["entry_type"]
        a[et] += int(e.get("minutes") or 0)
        if et == "absence":
            a["absent_days"] += float(e.get("day_fraction") or 0)

    rows = []
    for s in staff:
        for d in days:
            a = agg.get((s["id"], d), {})
            sched = rostered(s, d)
            forf = min(a.get("absence", 0), sched) if forfeits else 0
            ent = sched - forf
            missed = min(a.get("missed", 0), ent)
            add = a.get("additional", 0)
            rows.append({
                "staff_id": s["id"], "Staff": s["name"], "date": d, "week": week_no(t, d),
                "rostered": sched, "forfeited": forf, "entitlement": ent,
                "missed": missed, "additional": add,
                "received": ent - missed + add, "balance": add - missed,
                "absent_days": a.get("absent_days", 0.0),
            })
    cols = ["staff_id", "Staff", "date", "week", "rostered", "forfeited", "entitlement",
            "missed", "additional", "received", "balance", "absent_days"]
    return pd.DataFrame(rows, columns=cols)


def staff_summary(staff, daily, opening, cfg):
    base = float(cfg.get("base_minutes_fte1", 250) or 0)
    ob = {o["staff_id"]: int(o.get("minutes") or 0) for o in opening}
    rows = []
    for s in staff:
        d = daily[daily["staff_id"] == s["id"]]
        weekly_roster = sum(int(s.get(k) or 0) for k in DAYS)
        fte_ent = round(base * float(s.get("fte") or 0))
        open_bal = ob.get(s["id"], 0)
        bal = open_bal + int(d["balance"].sum())
        rows.append({
            "staff_id": s["id"], "Staff": s["name"], "FTE": float(s.get("fte") or 0),
            "Rostered / wk": weekly_roster, "FTE entitlement / wk": fte_ent,
            "Opening": open_bal, "Entitled": int(d["entitlement"].sum()),
            "Missed": int(d["missed"].sum()), "Additional": int(d["additional"].sum()),
            "Received": int(d["received"].sum()), "Balance": bal,
            "Absent days": float(d["absent_days"].sum()),
            "Roster check": ("⚠️ Rostered below entitlement" if weekly_roster < fte_ent
                             else ("Rostered above entitlement" if weekly_roster > fte_ent else "✓")),
            "Status": "🔴 Owed" if bal < 0 else ("🔵 Over" if bal > 0 else "🟢 Square"),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
cfg = load_config()
TERMS = term_list(cfg)
all_staff = load_staff()
staff = [s for s in all_staff if s.get("active", True)]
staff_by_id = {s["id"]: s for s in all_staff}
CLOSURES = closure_set(cfg)
TODAY = date.today()

st.markdown("""
<style>
.nit-head {border-left: 6px solid #1f6f78; padding: 0.2rem 0 0.2rem 0.9rem; margin-bottom: 0.6rem;}
.nit-head h1 {font-size: 1.7rem; margin: 0; color: #1f3b4d;}
.nit-head p {margin: 0.15rem 0 0; color: #5a6b75;}
</style>
<div class="nit-head"><h1>⏱️ NIT & Staff Absence Tracker</h1>
<p>Log only what differs from the roster. Balances calculate themselves.</p></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.text_input("Your initials (recorded on entries)", key="nit_entered_by", max_chars=10)

if not TERMS:
    st.error("No term dates configured — add them in Setup.")
if not staff:
    st.warning("No active staff yet. Go to **Setup** to add staff and their rostered NIT.")

with st.expander("How this works"):
    st.markdown(f"""
- Each teacher has **rostered NIT** (minutes per weekday) set in Setup. Rostered NIT is **assumed received** unless you log an exception.
- **Missed NIT** reduces the balance. **Additional NIT** increases it. **Balance = Additional − Missed** (plus any opening balance carried from last term).
- **Negative balance = NIT owed to the teacher.** Positive = they've had more than entitlement.
- **Staff absence** on a NIT day {'removes that NIT from their entitlement (not owed)' if cfg.get('absence_forfeits_nit', True) else 'does NOT change entitlement (setting is off)'} — change this rule in Setup.
- Public holidays / closure days in Setup are excluded from entitlement.
- Weekly entitlement per 1.0 FTE is currently **{fmt(cfg.get('base_minutes_fte1', 250))}** — used for the roster check on the Leadership tab.
""")


def term_picker(key, default=None):
    if not TERMS:
        return None
    default = default or current_term(TERMS, TODAY)
    labels = [term_label(t) for t in TERMS]
    idx = labels.index(term_label(default)) if default else 0
    choice = st.selectbox("Term", labels, index=idx, key=key)
    return TERMS[labels.index(choice)]


tabs = st.tabs(["📅 This Week", "✍️ Log", "📊 Leadership", "🗂️ History", "⚙️ Setup", "⬇️ Export"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — THIS WEEK
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    if TERMS and staff:
        c1, c2 = st.columns([2, 1])
        with c1:
            t = term_picker("wk_term")
        nweeks = term_week_count(t)
        default_wk = week_no(t, TODAY) if t["start"] <= TODAY <= t["end"] else 1
        with c2:
            wk = st.number_input("Week", 1, nweeks, min(max(default_wk, 1), nweeks), key="wk_no")
        wdates = week_dates(t, wk)
        st.caption(f"{wdates[0]:%a %d %b} – {wdates[-1]:%a %d %b %Y}")

        ents = load_entries(wdates[0].isoformat(), wdates[-1].isoformat())
        by_key = {}
        for e in ents:
            by_key.setdefault((e["staff_id"], to_date(e["entry_date"])), []).append(e)
        daily = build_daily(staff, ents, t, cfg)
        wdf = daily[daily["week"] == wk]

        rows = []
        for s in staff:
            row = {"Staff": s["name"]}
            for d, lab in zip(wdates, DAY_LABELS):
                col = f"{lab} {d:%d/%m}"
                if d < t["start"] or d > t["end"]:
                    row[col] = "—"
                    continue
                if d in CLOSURES:
                    row[col] = f"Closed ({CLOSURES[d]})"
                    continue
                es = by_key.get((s["id"], d), [])
                sched = rostered(s, d)
                parts = []
                absent = [e for e in es if e["entry_type"] == "absence"]
                missed = sum(int(e["minutes"] or 0) for e in es if e["entry_type"] == "missed")
                extra = sum(int(e["minutes"] or 0) for e in es if e["entry_type"] == "additional")
                if absent:
                    parts.append("🏠 Absent" + ("" if absent[0].get("portion") in ("Full day", None, "")
                                               else f" ({absent[0]['portion'].lower()})"))
                if sched:
                    forf = sum(int(e["minutes"] or 0) for e in absent)
                    if absent and forf >= sched and cfg.get("absence_forfeits_nit", True):
                        parts.append(f"NIT {fmt(sched)} n/a")
                    elif missed:
                        parts.append(f"❌ NIT missed {fmt(missed)}")
                    elif d <= TODAY:
                        parts.append(f"✅ NIT {fmt(sched)}")
                    else:
                        parts.append(f"NIT {fmt(sched)}")
                if extra:
                    parts.append(f"➕ {fmt(extra)} extra")
                row[col] = " · ".join(parts)
            sd = wdf[wdf["staff_id"] == s["id"]]
            row["Entitled"] = fmt(sd["entitlement"].sum())
            row["Received"] = fmt(sd["received"].sum())
            row["Week balance"] = fmt(sd["balance"].sum(), signed=True)
            rows.append(row)

        st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)
        st.caption("✅ received as rostered (assumed) · ❌ missed · ➕ additional · 🏠 absent · "
                   "future days show rostered NIT only.")

        wk_bal = int(wdf["balance"].sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("NIT missed this week", fmt(wdf["missed"].sum()))
        m2.metric("Additional NIT this week", fmt(wdf["additional"].sum()))
        m3.metric("Net for the site", fmt(wk_bal, signed=True))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LOG
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    if staff:
        kind = st.radio("What are you recording?",
                        ["❌ Missed NIT", "➕ Additional NIT", "🏠 Staff absence",
                         "📅 NIT cancelled for a whole day"],
                        horizontal=True, key="log_kind")
        names = [s["name"] for s in staff]
        name_to = {s["name"]: s for s in staff}

        def _existing(staff_id, d):
            return [e for e in load_entries(d.isoformat(), d.isoformat()) if e["staff_id"] == staff_id]

        def _not_school_day(d):
            if d.weekday() >= 5:
                return "That date is a weekend."
            if d in CLOSURES:
                return f"That date is a closure day ({CLOSURES[d]})."
            if not any(t["start"] <= d <= t["end"] for t in TERMS):
                return "That date is outside the configured term dates."
            return None

        if kind == "❌ Missed NIT":
            c1, c2 = st.columns(2)
            d = c1.date_input("Date", TODAY, format="DD/MM/YYYY", key="m_date")
            who_s = c2.selectbox("Staff member", names, key="m_staff")
            s = name_to[who_s]
            sched = rostered(s, d)
            if msg := _not_school_day(d):
                st.warning(msg)
            if sched == 0:
                st.info(f"{who_s} has no NIT rostered on {d:%A}. You can still log minutes if NIT was moved to this day.")
            c3, c4 = st.columns(2)
            mins = c3.number_input("Minutes missed", 0, 600, sched, step=5, key=f"m_min_{s['id']}_{d}")
            reason = c4.selectbox("Reason", cfg["missed_reasons"], key="m_reason")
            notes = st.text_input("Notes (optional)", key="m_notes")
            ex = _existing(s["id"], d) or []
            if any(e["entry_type"] == "absence" for e in ex):
                st.warning(f"{who_s} is logged as absent that day — missed NIT may double-count. "
                           "(Missed minutes are capped at that day's remaining entitlement.)")
            if any(e["entry_type"] == "missed" for e in ex):
                st.warning("Missed NIT is already logged for this person on this date.")
            if st.button("Save missed NIT", type="primary", disabled=mins <= 0):
                insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "missed",
                                 "minutes": int(mins), "category": reason, "notes": notes,
                                 "entered_by": who()}])
                st.success(f"Logged {fmt(mins)} missed NIT for {who_s} on {d:%a %d %b}.")
                rerun()

        elif kind == "➕ Additional NIT":
            c1, c2 = st.columns(2)
            d = c1.date_input("Date", TODAY, format="DD/MM/YYYY", key="a_date")
            who_s = c2.selectbox("Staff member", names, key="a_staff")
            s = name_to[who_s]
            if msg := _not_school_day(d):
                st.warning(msg)
            c3, c4 = st.columns(2)
            mins = c3.number_input("Additional minutes given", 0, 600, 0, step=5, key="a_min")
            reason = c4.selectbox("Reason", cfg["additional_reasons"], key="a_reason")
            notes = st.text_input("Notes (optional)", key="a_notes")
            if st.button("Save additional NIT", type="primary", disabled=mins <= 0):
                insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "additional",
                                 "minutes": int(mins), "category": reason, "notes": notes,
                                 "entered_by": who()}])
                st.success(f"Logged {fmt(mins)} additional NIT for {who_s}.")
                rerun()

        elif kind == "🏠 Staff absence":
            c1, c2, c3 = st.columns(3)
            who_s = c1.selectbox("Staff member", names, key="ab_staff")
            d1 = c2.date_input("From", TODAY, format="DD/MM/YYYY", key="ab_from")
            d2 = c3.date_input("To", d1, format="DD/MM/YYYY", key=f"ab_to_{d1}")
            s = name_to[who_s]
            c4, c5 = st.columns(2)
            portion = c4.selectbox("Portion of each day", ["Full day", "Morning", "Afternoon", "Part day"],
                                   key="ab_portion")
            ltype = c5.selectbox("Leave type", cfg["absence_types"], key="ab_type")
            covers = st.checkbox("Absence covered their rostered NIT time",
                                 value=(portion == "Full day"), key=f"ab_cov_{portion}",
                                 help="If ticked, that day's rostered NIT is recorded as not applicable "
                                      "(not owed), per the absence rule in Setup.")
            notes = st.text_input("Notes (optional — avoid personal/medical detail)", key="ab_notes")
            frac = {"Full day": 1.0, "Morning": 0.5, "Afternoon": 0.5, "Part day": 0.25}[portion]
            plan = []
            if d2 < d1:
                st.error("'To' date is before 'From' date.")
            else:
                for d in daterange(d1, d2):
                    if d.weekday() >= 5 or d in CLOSURES:
                        continue
                    if not any(t["start"] <= d <= t["end"] for t in TERMS):
                        continue
                    plan.append({"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "absence",
                                 "minutes": rostered(s, d) if covers else 0, "day_fraction": frac,
                                 "portion": portion, "category": ltype, "notes": notes,
                                 "entered_by": who()})
            if plan:
                st.dataframe(pd.DataFrame([{"Date": to_date(p["entry_date"]).strftime("%a %d %b"),
                                            "Portion": portion,
                                            "NIT not applicable": fmt(p["minutes"])} for p in plan]),
                             hide_index=True)
            elif d2 >= d1:
                st.info("No school days in that range.")
            if st.button(f"Save absence ({len(plan)} day{'s' if len(plan) != 1 else ''})",
                         type="primary", disabled=not plan):
                insert_entries(plan)
                st.success(f"Logged absence for {who_s}.")
                rerun()

        else:  # whole-day cancel
            st.caption("Use when NIT couldn't run for several staff on a day — e.g. NIT provider away, "
                       "whole-site event. Logs missed NIT for each ticked person at their rostered minutes.")
            c1, c2 = st.columns(2)
            d = c1.date_input("Date", TODAY, format="DD/MM/YYYY", key="c_date")
            reason = c2.selectbox("Reason", cfg["missed_reasons"],
                                  index=cfg["missed_reasons"].index("NIT provider absent")
                                  if "NIT provider absent" in cfg["missed_reasons"] else 0, key="c_reason")
            if msg := _not_school_day(d):
                st.warning(msg)
            day_ents = load_entries(d.isoformat(), d.isoformat())
            absent_ids = {e["staff_id"] for e in day_ents if e["entry_type"] == "absence"}
            missed_ids = {e["staff_id"] for e in day_ents if e["entry_type"] == "missed"}
            cands = [s for s in staff if rostered(s, d) > 0]
            if not cands:
                st.info(f"No one has NIT rostered on {d:%A}.")
            else:
                pick = []
                for s in cands:
                    note = " — absent that day" if s["id"] in absent_ids else (
                        " — missed NIT already logged" if s["id"] in missed_ids else "")
                    if st.checkbox(f"{s['name']} ({fmt(rostered(s, d))}){note}",
                                   value=not note, key=f"c_{s['id']}_{d}"):
                        pick.append(s)
                notes = st.text_input("Notes (optional)", key="c_notes")
                if st.button(f"Log missed NIT for {len(pick)} staff", type="primary", disabled=not pick):
                    insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "missed",
                                     "minutes": rostered(s, d), "category": reason, "notes": notes,
                                     "entered_by": who()} for s in pick])
                    st.success(f"Logged missed NIT for {len(pick)} staff on {d:%a %d %b}.")
                    rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LEADERSHIP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    if TERMS and staff:
        c1, c2 = st.columns([2, 1])
        with c1:
            t = term_picker("ld_term")
        with c2:
            to_date_only = (getattr(st, "toggle", None) or st.checkbox)("Term to date only", value=True,
                                     help="Off = include the whole term's rostered entitlement.")
        upto = TODAY if to_date_only else None
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat())
        daily = build_daily(staff, ents, t, cfg, upto=upto)
        opening = load_opening(t["year"], t["term"])
        summ = staff_summary(staff, daily, opening, cfg)

        owed = summ[summ["Balance"] < 0]
        over = summ[summ["Balance"] > 0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Staff owed NIT", f"{len(owed)} of {len(summ)}")
        m2.metric("Total NIT owed", fmt(-owed["Balance"].sum()) if len(owed) else "0m")
        m3.metric("Total over entitlement", fmt(over["Balance"].sum()) if len(over) else "0m")
        m4.metric("Staff absence (days)", f"{summ['Absent days'].sum():g}")

        show = summ.copy()
        for c in ["Rostered / wk", "FTE entitlement / wk", "Opening", "Entitled", "Missed",
                  "Additional", "Received"]:
            show[c] = show[c].apply(fmt)
        show["Balance"] = summ["Balance"].apply(lambda v: fmt(v, signed=True))
        show["Absent days"] = show["Absent days"].apply(lambda v: f"{v:g}")
        st.dataframe(show[["Staff", "Status", "Balance", "FTE", "Rostered / wk", "FTE entitlement / wk",
                           "Roster check", "Opening", "Entitled", "Missed", "Additional", "Received",
                           "Absent days"]],
                     hide_index=True, **WIDE)
        st.caption("Balance = Opening + Additional − Missed. Negative = owed to the teacher. "
                   "Roster check compares rostered NIT per week with FTE × base entitlement (Setup).")

        if not daily.empty:
            st.markdown("#### Balance over the term")
            wk = daily.groupby(["week", "Staff"])["balance"].sum().unstack(fill_value=0).sort_index()
            ob = {staff_by_id[o["staff_id"]]["name"]: int(o["minutes"] or 0)
                  for o in opening if o["staff_id"] in staff_by_id}
            cum = wk.cumsum()
            for name in cum.columns:
                cum[name] = (cum[name] + ob.get(name, 0)) / 60.0
            cum.index = [f"Wk {i}" for i in cum.index]
            try:
                st.line_chart(cum, y_label="Balance (hours, negative = owed)")
            except TypeError:
                st.line_chart(cum)

        cA, cB = st.columns(2)
        with cA:
            st.markdown("#### Why NIT was missed")
            mdf = pd.DataFrame([e for e in ents if e["entry_type"] == "missed"
                                and (upto is None or to_date(e["entry_date"]) <= upto)])
            if mdf.empty:
                st.caption("No missed NIT logged.")
            else:
                r = mdf.groupby("category")["minutes"].sum().sort_values(ascending=False)
                try:
                    st.bar_chart((r / 60.0).rename("Hours"), horizontal=True)
                except TypeError:
                    st.bar_chart((r / 60.0).rename("Hours"))
        with cB:
            st.markdown("#### Absence by leave type (days)")
            adf = pd.DataFrame([e for e in ents if e["entry_type"] == "absence"
                                and (upto is None or to_date(e["entry_date"]) <= upto)])
            if adf.empty:
                st.caption("No absences logged.")
            else:
                adf["Staff"] = adf["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
                pv = adf.pivot_table(index="Staff", columns="category", values="day_fraction",
                                     aggfunc="sum", fill_value=0)
                pv["Total"] = pv.sum(axis=1)
                st.dataframe(pv.apply(lambda c: c.map(lambda v: f"{v:g}")), **WIDE)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
TYPE_LABEL = {"missed": "❌ Missed", "additional": "➕ Additional", "absence": "🏠 Absence"}

with tabs[3]:
    if TERMS:
        c1, c2, c3 = st.columns(3)
        with c1:
            t = term_picker("h_term")
        f_staff = c2.multiselect("Staff", [s["name"] for s in all_staff], key="h_staff")
        f_type = c3.multiselect("Type", list(TYPE_LABEL.values()), key="h_type")
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat())
        if not ents:
            st.info("No entries this term.")
        else:
            df = pd.DataFrame(ents)
            df["Date"] = df["entry_date"].map(to_date)
            df["Staff"] = df["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
            df["Type"] = df["entry_type"].map(TYPE_LABEL)
            df["Time"] = df["minutes"].map(fmt)
            if f_staff:
                df = df[df["Staff"].isin(f_staff)]
            if f_type:
                df = df[df["Type"].isin(f_type)]
            df = df.sort_values(["Date", "Staff"], ascending=[False, True])
            df.insert(0, "Delete", False)
            cols = ["Delete", "Date", "Staff", "Type", "Time", "portion", "category", "notes",
                    "entered_by", "id"]
            ed = st.data_editor(
                df[cols], hide_index=True, **WIDE,
                disabled=[c for c in cols if c != "Delete"],
                column_config={
                    "Date": st.column_config.DateColumn(format="ddd DD/MM/YYYY"),
                    "portion": "Portion", "category": "Reason / leave type", "notes": "Notes",
                    "entered_by": "By", "id": st.column_config.NumberColumn("ID", width="small"),
                    "Time": "Minutes (NIT)",
                }, key=f"h_editor_{t['year']}_{t['term']}")
            to_del = ed.loc[ed["Delete"], "id"].tolist()
            if to_del:
                st.warning(f"{len(to_del)} entr{'y' if len(to_del) == 1 else 'ies'} selected for deletion.")
                if st.button("Delete selected", type="primary"):
                    delete_entries(to_del)
                    st.success("Deleted.")
                    rerun()
            st.caption("To correct an entry: delete it and log it again.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SETUP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("#### Staff and rostered NIT")
    st.caption("Minutes of NIT rostered on each weekday. Untick Active for staff who leave — "
               "their history is kept. Removing a row here also just deactivates them.")
    base_df = pd.DataFrame(all_staff) if all_staff else pd.DataFrame(
        columns=["id", "name", "fte", *DAYS, "active", "display_order", "notes"])
    for c, dflt in [("fte", 1.0), ("active", True), ("display_order", 0), ("notes", "")] + [(k, 0) for k in DAYS]:
        if c not in base_df:
            base_df[c] = dflt
    base_df = base_df[["id", "name", "fte", *DAYS, "active", "display_order", "notes"]]
    ed_staff = st.data_editor(
        base_df, num_rows="dynamic", hide_index=True, **WIDE, key="staff_editor",
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("Name", required=True),
            "fte": st.column_config.NumberColumn("FTE", min_value=0.0, max_value=1.0, step=0.1, format="%.1f"),
            **{k: st.column_config.NumberColumn(f"{lab} (min)", min_value=0, max_value=600, step=5)
               for k, lab in zip(DAYS, DAY_LABELS)},
            "active": st.column_config.CheckboxColumn("Active", default=True),
            "display_order": st.column_config.NumberColumn("Order", step=1),
            "notes": st.column_config.TextColumn("Notes"),
        })
    if st.button("Save staff", type="primary"):
        kept_ids = set()
        for _, r in ed_staff.iterrows():
            if not str(r.get("name") or "").strip():
                continue
            rec = {"name": str(r["name"]).strip(),
                   "fte": float(r["fte"]) if pd.notna(r["fte"]) else 1.0,
                   "active": bool(r["active"]) if pd.notna(r["active"]) else True,
                   "display_order": int(r["display_order"]) if pd.notna(r["display_order"]) else 0,
                   "notes": "" if pd.isna(r["notes"]) else str(r["notes"])}
            for k in DAYS:
                rec[k] = int(r[k]) if pd.notna(r[k]) else 0
            if pd.notna(r.get("id")):
                sb().table(T_STAFF).update(rec).eq("id", int(r["id"])).execute()
                kept_ids.add(int(r["id"]))
            else:
                sb().table(T_STAFF).insert(rec).execute()
        for s in all_staff:
            if s["id"] not in kept_ids and s.get("active", True):
                sb().table(T_STAFF).update({"active": False}).eq("id", s["id"]).execute()
        refresh()
        st.success("Staff saved.")
        rerun()

    st.divider()
    st.markdown("#### Entitlement rules")
    c1, c2 = st.columns(2)
    base_min = c1.number_input("Weekly NIT entitlement at 1.0 FTE (minutes)", 0, 1000,
                               int(cfg.get("base_minutes_fte1", 250)), step=5,
                               help="Pro-rated by FTE for the Roster check. Confirm against the current "
                                    "enterprise agreement / DfE guidance.")
    c1.caption(f"= {fmt(base_min)} per week · 0.8 FTE → {fmt(base_min * 0.8)} · "
               f"0.6 → {fmt(base_min * 0.6)} · 0.4 → {fmt(base_min * 0.4)} · 0.2 → {fmt(base_min * 0.2)}")
    forfeits = (getattr(c2, "toggle", None) or c2.checkbox)("Absence on a NIT day removes that NIT from entitlement (not owed)",
                         value=bool(cfg.get("absence_forfeits_nit", True)))

    st.markdown("#### Term dates")
    tdf = pd.DataFrame([{"year": t["year"], "term": t["term"], "start": t["start"], "end": t["end"]}
                        for t in TERMS])
    ed_terms = st.data_editor(tdf, num_rows="dynamic", hide_index=True, key="terms_editor",
                              column_config={
                                  "year": st.column_config.NumberColumn("Year", step=1, format="%d"),
                                  "term": st.column_config.NumberColumn("Term", min_value=1, max_value=4, step=1),
                                  "start": st.column_config.DateColumn("First day", format="DD/MM/YYYY"),
                                  "end": st.column_config.DateColumn("Last day", format="DD/MM/YYYY")})

    st.markdown("#### Closure days (public holidays, pupil-free days with no NIT)")
    cdf = pd.DataFrame([{"date": d, "label": l} for d, l in sorted(CLOSURES.items())],
                       columns=["date", "label"])
    ed_clos = st.data_editor(cdf, num_rows="dynamic", hide_index=True, key="clos_editor",
                             column_config={"date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                                            "label": "Label"})

    with st.expander("Reason and leave-type lists"):
        mr = st.text_area("Missed NIT reasons (one per line)", "\n".join(cfg["missed_reasons"]))
        ar = st.text_area("Additional NIT reasons (one per line)", "\n".join(cfg["additional_reasons"]))
        at = st.text_area("Leave types (one per line)", "\n".join(cfg["absence_types"]))

    if st.button("Save rules, terms and closures", type="primary"):
        new = dict(cfg)
        new["base_minutes_fte1"] = int(base_min)
        new["absence_forfeits_nit"] = bool(forfeits)
        new["terms"] = [{"year": int(r["year"]), "term": int(r["term"]),
                         "start": to_date(r["start"]).isoformat(), "end": to_date(r["end"]).isoformat()}
                        for _, r in ed_terms.iterrows()
                        if pd.notna(r["year"]) and pd.notna(r["term"]) and pd.notna(r["start"]) and pd.notna(r["end"])]
        new["closures"] = [{"date": to_date(r["date"]).isoformat(), "label": str(r["label"] or "Closed")}
                           for _, r in ed_clos.iterrows() if pd.notna(r["date"])]
        for key, txt in [("missed_reasons", mr), ("additional_reasons", ar), ("absence_types", at)]:
            items = [x.strip() for x in txt.splitlines() if x.strip()]
            if items:
                new[key] = items
        save_config(new)
        st.success("Saved.")
        rerun()

    st.divider()
    st.markdown("#### Opening balances (carried from previous term)")
    if TERMS and staff:
        t = term_picker("ob_term")
        opening = load_opening(t["year"], t["term"])
        ob = {o["staff_id"]: int(o["minutes"] or 0) for o in opening}
        idx = TERMS.index(t)
        prev = TERMS[idx - 1] if idx > 0 else None
        if prev and st.button(f"Carry forward closing balances from {term_label(prev)}"):
            p_ents = load_entries(prev["start"].isoformat(), prev["end"].isoformat())
            p_daily = build_daily(staff, p_ents, prev, cfg)
            p_summ = staff_summary(staff, p_daily, load_opening(prev["year"], prev["term"]), cfg)
            recs = [{"year": t["year"], "term": t["term"], "staff_id": int(r["staff_id"]),
                     "minutes": int(r["Balance"]), "note": f"Carried from {term_label(prev)}"}
                    for _, r in p_summ.iterrows()]
            sb().table(T_OPEN).upsert(recs, on_conflict="year,term,staff_id").execute()
            refresh()
            st.success("Carried forward.")
            rerun()
        odf = pd.DataFrame([{"staff_id": s["id"], "Staff": s["name"], "Minutes": ob.get(s["id"], 0)}
                            for s in staff])
        ed_ob = st.data_editor(odf, hide_index=True, key=f"ob_editor_{t['year']}_{t['term']}",
                               disabled=["Staff"],
                               column_config={"staff_id": None,
                                              "Minutes": st.column_config.NumberColumn(
                                                  "Opening balance (minutes, negative = owed)", step=5)})
        if st.button("Save opening balances"):
            recs = [{"year": t["year"], "term": t["term"], "staff_id": int(r["staff_id"]),
                     "minutes": int(r["Minutes"] or 0), "note": "Manual"} for _, r in ed_ob.iterrows()]
            sb().table(T_OPEN).upsert(recs, on_conflict="year,term,staff_id").execute()
            refresh()
            st.success("Saved.")
            rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def build_workbook(t, staff, ents, daily, summ):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    s_out = summ.copy()
    for c in ["Rostered / wk", "FTE entitlement / wk", "Opening", "Entitled", "Missed", "Additional", "Received"]:
        s_out[c + " (h:m)"] = s_out[c].apply(fmt)
    s_out["Balance (h:m)"] = s_out["Balance"].apply(lambda v: fmt(v, signed=True))
    s_out = s_out[["Staff", "Status", "Balance (h:m)", "FTE", "Rostered / wk (h:m)",
                   "FTE entitlement / wk (h:m)", "Roster check", "Opening (h:m)", "Entitled (h:m)",
                   "Missed (h:m)", "Additional (h:m)", "Received (h:m)", "Absent days",
                   "Balance", "Entitled", "Missed", "Additional"]].rename(
        columns={"Balance": "Balance (min)", "Entitled": "Entitled (min)",
                 "Missed": "Missed (min)", "Additional": "Additional (min)"})

    weekly = daily.groupby(["Staff", "week"])[["entitlement", "missed", "additional", "balance"]].sum().reset_index()
    wk_bal = weekly.pivot(index="Staff", columns="week", values="balance").fillna(0)
    wk_bal = wk_bal.apply(lambda col: col.map(lambda v: fmt(v, signed=True)))
    wk_bal.columns = [f"Week {c}" for c in wk_bal.columns]

    e_df = pd.DataFrame(ents)
    if not e_df.empty:
        e_df["Staff"] = e_df["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
        e_df["Type"] = e_df["entry_type"].map({"missed": "Missed NIT", "additional": "Additional NIT",
                                               "absence": "Absence"})
        e_df["Time (h:m)"] = e_df["minutes"].map(fmt)
        e_df = e_df.rename(columns={"entry_date": "Date", "minutes": "Minutes", "portion": "Portion",
                                    "category": "Reason / leave type", "notes": "Notes",
                                    "entered_by": "Entered by", "day_fraction": "Days"})
        e_df = e_df[["Date", "Staff", "Type", "Minutes", "Time (h:m)", "Portion", "Days",
                     "Reason / leave type", "Notes", "Entered by"]].sort_values(["Date", "Staff"])
    else:
        e_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Minutes"])

    d_out = daily.drop(columns=["staff_id"]).rename(columns={
        "date": "Date", "week": "Week", "rostered": "Rostered (min)", "forfeited": "N/A - absent (min)",
        "entitlement": "Entitled (min)", "missed": "Missed (min)", "additional": "Additional (min)",
        "received": "Received (min)", "balance": "Balance (min)", "absent_days": "Absent days"})

    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        s_out.to_excel(xw, sheet_name="Term Summary", index=False, startrow=2)
        wk_bal.to_excel(xw, sheet_name="Weekly Balances", startrow=2)
        e_df.to_excel(xw, sheet_name="Log Entries", index=False, startrow=2)
        d_out.to_excel(xw, sheet_name="Daily Detail", index=False, startrow=2)
        wb = xw.book
        head_fill = PatternFill("solid", start_color="1F6F78")
        for ws in wb.worksheets:
            ws["A1"] = f"CLC-LBU NIT & Absence — {term_label(t)} — {ws.title}"
            ws["A1"].font = Font(name="Arial", bold=True, size=13)
            ws["A2"] = (f"Generated {datetime.now():%d/%m/%Y %H:%M}. Balance = Opening + Additional − Missed; "
                        f"negative = NIT owed to the teacher.")
            ws["A2"].font = Font(name="Arial", italic=True, size=9, color="555555")
            for row in ws.iter_rows(min_row=3):
                for c in row:
                    c.font = Font(name="Arial", size=10, bold=(c.row == 3), color=("FFFFFF" if c.row == 3 else "000000"))
                    if c.row == 3:
                        c.fill = head_fill
                        c.alignment = Alignment(wrap_text=True, vertical="center")
            for i, col in enumerate(ws.iter_cols(min_row=3), start=1):
                width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 9), 38)
            ws.freeze_panes = "B4"
    return buf.getvalue()


with tabs[5]:
    if TERMS and staff:
        t = term_picker("ex_term")
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat())
        upto = TODAY if t["start"] <= TODAY <= t["end"] else None
        daily = build_daily(staff, ents, t, cfg, upto=upto)
        summ = staff_summary(staff, daily, load_opening(t["year"], t["term"]), cfg)
        st.caption("Term Summary, Weekly Balances, Log Entries and Daily Detail sheets. "
                   + ("Current term: figures are term to date." if upto else ""))
        if st.button("Build Excel report"):
            st.session_state["nit_xlsx"] = build_workbook(t, staff, ents, daily, summ)
            st.session_state["nit_xlsx_name"] = f"NIT_Absence_{t['year']}_Term{t['term']}.xlsx"
        if st.session_state.get("nit_xlsx"):
            st.download_button("⬇️ Download", st.session_state["nit_xlsx"],
                               file_name=st.session_state["nit_xlsx_name"],
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
