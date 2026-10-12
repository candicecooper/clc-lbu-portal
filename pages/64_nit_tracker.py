"""
NIT & Staff Absence Tracker — CLC-LBU Portal  (v2 — automatic)
================================================================
Records begin Term 4 2026 and continue term by term (add later years in
Setup → Term dates). No old workbook data is imported.

WHAT HAPPENS AUTOMATICALLY
  1. NIT TIMETABLE → NIT GIVEN
     The tool reads the staff timetable PDF the portal publishes (default:
     https://clc-portal.pages.dev/timetable.pdf, or a Supabase Storage folder
     — set in Setup). Every block whose label starts with "NIT" is measured
     from the drawn grid (so merged multi-row sessions count their full
     length). Each time a NEW timetable appears it becomes a new timetable
     version; the version in force on each date is used for that date.
       - If the PDF's "Term X, YYYY" matches the current/next term it is
         applied automatically; otherwise it waits on the NIT Timetable tab
         for one-click review (protects balances from a stale timetable).
       - You can also upload a PDF or edit minutes by hand (new version).
     Rostered NIT is ASSUMED RECEIVED unless manually modified (missed /
     additional / "set actual NIT" for a day).

  2. DAILY BULLETIN → STAFF ABSENCE
     Staff named in the Daily Bulletin's staff-absence table (and Program
     Changes marked "Staff Absence") are matched to tracker staff by name or
     alias and logged as absent automatically ("📰" in the grid).
       - Their rostered NIT that day is recorded as NOT received.
       - Their entitlement for that week is reduced pro rata
         (FTE × weekly entitlement ÷ their working days, per day absent).
       - Manual entries always win; deleting an auto entry dismisses it so
         it isn't re-added; removing the name from the bulletin removes the
         auto entry on the next sync.

  BALANCE = NIT received − pro-rata entitlement (+ opening balance)
     negative → NIT OWED to the teacher; positive → over entitlement.

SETUP BEFORE FIRST RUN (or after upgrading from v1)
  1. Run nit_tracker_schema.sql in the Supabase SQL editor (safe to re-run;
     upgrades v1 tables in place).
  2. Add  pdfplumber  to requirements.txt (reads the timetable PDF).
  3. Setup tab → each staff member's FTE, working days and any bulletin
     aliases (e.g. "Ben Sel").
"""

import streamlit as st

try:
    st.set_page_config(page_title="NIT & Absence Tracker | CLC-LBU", page_icon="⏱️", layout="wide")
except Exception:
    pass

import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.dirname(os.path.abspath(__file__))):
    if p not in sys.path:
        sys.path.insert(0, p)


# ══════════════════════════════════════════════════════════════════════════════
# SECRETS + GATE
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


def _gate():
    try:
        import confidential_auth as ca
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


@st.cache_resource
def sb_bulletin():
    """Daily Bulletin client — same project unless BULLETIN_SUPABASE_URL/KEY are set."""
    url = _secret("BULLETIN_SUPABASE_URL")
    key = _secret("BULLETIN_SUPABASE_KEY")
    if url and key:
        from supabase import create_client
        return create_client(url, key)
    return sb()


try:
    sb()
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.stop()

T_STAFF = "nit_staff"
T_ENTRIES = "nit_entries"
T_OPEN = "nit_opening_balances"
T_SETTINGS = "nit_settings"
T_TTV = "nit_timetable_versions"
T_TTS = "nit_timetable_sessions"

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

DEFAULT_CONFIG = {
    "base_minutes_fte1": 250,
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
        "From Daily Bulletin",
        "Other",
    ],
    "bulletin": {
        "enabled": True,
        "table": "bulletins",
        "date_col": "date",
        "absence_cols": ["staff_absent"],
        "name_keys": ["Staff Absence", "Staff", "Name", "staff_absent"],
        "reason_keys": ["Reason", "reason", "Leave Type"],
        "program_changes_col": "program_changes",
    },
    "timetable_source": {
        "mode": "portal",                    # portal | url | off
        "url": "",
        "table": "timetable_store",
        "bucket": "",
        "prefix": "",
        "auto_apply": True,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(m, signed=False):
    try:
        m = int(round(float(m or 0)))
    except Exception:
        m = 0
    sign = "-" if m < 0 else ("+" if signed and m > 0 else "")
    h, mm = divmod(abs(m), 60)
    return f"{sign}{h}h {mm:02d}m" if h else f"{sign}{mm}m"


def to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
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


def parse_workdays(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return list(range(5))
    out = []
    for part in re.split(r"[,\s/]+", str(txt)):
        p = part.strip().lower()[:3]
        if p in [d.lower() for d in DAY_LABELS]:
            out.append([d.lower() for d in DAY_LABELS].index(p))
    return sorted(set(out)) if out else list(range(5))


def as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return []
        try:
            return as_list(json.loads(v))
        except Exception:
            return []
    if isinstance(v, dict):
        return [v]
    return list(v) if isinstance(v, (list, tuple)) else []


# ══════════════════════════════════════════════════════════════════════════════
# TIMETABLE PDF READER
# ══════════════════════════════════════════════════════════════════════════════
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday"]
NIT_RX = re.compile(r"^\s*(nit\b|non[\s-]*instruct)", re.I)
TIME_RX = re.compile(r"^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$")


def _tmins(t):
    h, m = (int(x) for x in t.split(":"))
    if h < 7:
        h += 12
    return h * 60 + m


def _hhmm(m):
    h, mm = divmod(int(m), 60)
    return f"{(h - 1) % 12 + 1}:{mm:02d}"


_ROLE_RX = re.compile(r"\b(teacher|years|primary|junior|senior|specialist|sso|support|leadership|timetable|"
                      r"staff|admin|meetings?|jp|py|sy|weekly)\b", re.I)


def name_from_header(line):
    """'JP - Ben Sutton — Junior Primary Teacher (JP)', 'Junior Primary Teacher- Ben Sutton',
    'Senior Years Teacher-Brenton', 'Roisin — Specialist Teacher' → the person's name."""
    segs = re.split(r"\s*(?:—|–|\s-\s|-(?=\s*[A-Z][a-z])|(?<=[a-z])-)\s*", str(line or ""))
    segs = [re.sub(r"\(.*?\)", "", x).strip() for x in segs]
    cands = [x for x in segs if x and not _ROLE_RX.search(x)]
    return cands[0] if cands else ""


def _iter_pdf_pages(data, dpi):
    """Yields (text, words, greyscale image, x_offset, y_offset, right_edge) per page.
    Uses PyMuPDF (already installed for the Timetable page) or pdfplumber."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        from PIL import Image
        doc = fitz.open(stream=data, filetype="pdf")
        for page in doc:
            words = [{"x0": w[0], "top": w[1], "x1": w[2], "bottom": w[3], "text": w[4]}
                     for w in page.get_text("words")]
            pm = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
            img = Image.frombytes("L", (pm.width, pm.height), pm.samples)
            yield page.get_text(), words, img, 0.0, 0.0, float(page.rect.width)
        return
    except ImportError:
        pass
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            yield (page.extract_text() or "", page.extract_words(),
                   page.to_image(resolution=dpi).original.convert("L"),
                   float(page.bbox[0]), float(page.bbox[1]), float(page.bbox[2]))


def parse_timetable_pdf(data, dpi=110):
    """One person per page, Mon–Fri columns, time rows on the left. Renders the
    page and reads the drawn grid (cell lines + fill shade) so merged sessions are
    measured by their real length. Only blocks whose label starts with NIT count."""
    out = {"term_label": "", "people": [], "warnings": []}
    if True:
        for pno, (text, words, img, ox, oy, xmax) in enumerate(_iter_pdf_pages(data, dpi), start=1):
            if not out["term_label"]:
                tm = re.search(r"Term\s*_?\s*(\d)\s*,\s*(\d{4})", text)
                if tm:
                    out["term_label"] = f"{tm.group(2)} Term {tm.group(1)}"
            # header lines rebuilt from word positions (text order differs between PDF libraries)
            rows = {}
            for w in words:
                rows.setdefault(round(w["top"] / 4), []).append(w)
            lines = [" ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
                     for _, ws in sorted(rows.items())]
            hi = next((i for i, l in enumerate(lines) if "staff timetable" in l.lower()), None)
            name = ""
            for l in (lines[hi + 1:hi + 4] if hi is not None else []):
                if re.search(r"\bmonday\b", l, re.I):
                    break
                name = name_from_header(l)
                if name:
                    break
            if not name:
                continue
            days = {}
            for w in words:
                lw = w["text"].strip().lower()
                if lw in DAY_NAMES and lw not in days:
                    days[lw] = w
            if len(days) < 5:
                continue                      # not a Mon–Fri staff grid (e.g. meetings page)
            hdr_bottom = max(w["bottom"] for w in days.values())
            times = []
            for w in words:
                m = TIME_RX.match(w["text"].strip())
                if m and w["top"] > hdr_bottom:
                    times.append({"c": (w["top"] + w["bottom"]) / 2, "s": _tmins(m.group(1)),
                                  "e": _tmins(m.group(2)), "x0": w["x0"], "x1": w["x1"]})
            times.sort(key=lambda t: t["c"])
            if len(times) < 3:
                out["warnings"].append(f"Page {pno} ({name}): time rows not found — skipped.")
                continue

            sc = dpi / 72.0
            W, H = img.size
            pix = img.load()


            def px(x, y):
                xi = min(max(int(round((x - ox) * sc)), 0), W - 1)
                yi = min(max(int(round((y - oy) * sc)), 0), H - 1)
                return pix[xi, yi]

            def is_v(x, y):
                return px(x, y) < min(px(x - 2.5, y), px(x + 2.5, y)) - 25

            def is_h(x, y):
                yy = y - 1.5
                while yy <= y + 1.5:
                    if px(x, yy) < min(px(x, yy - 2.5), px(x, yy + 2.5)) - 25:
                        return True
                    yy += 0.25
                return False

            ys = [times[0]["c"] + k * (times[-1]["c"] - times[0]["c"]) / 23 for k in range(24)]

            def vline(x):
                return sum(1 for y in ys if is_v(x, y)) >= len(ys) * 0.6

            cols = []
            for d in DAY_NAMES:
                xc = (days[d]["x0"] + days[d]["x1"]) / 2
                l, r = xc, xc
                while l > ox and not vline(l):
                    l -= 0.25
                while r < xmax and not vline(r):
                    r += 0.25
                cols.append((l + 1.2, r - 1.2))
            tl = cols[0][0] - 1.2
            tleft = tl - 3
            while tleft > ox and not vline(tleft):
                tleft -= 0.25
            tx = tleft + 2.5

            bounds = []
            for a, b in zip(times, times[1:]):
                cand = [a["c"] + k * (b["c"] - a["c"]) / 40 for k in range(4, 37)]
                bounds.append(min(cand, key=lambda y: px(tx, y) + px(tl - 2.5, y)))
            row_top = [times[0]["c"] - (bounds[0] - times[0]["c"])] + bounds
            row_bot = bounds + [times[-1]["c"] + (times[-1]["c"] - bounds[-1])]

            def separated(cl, cr, y):
                """A real cell border runs the full column width (text never reaches the edges)."""
                if not all(is_h(cl + f * (cr - cl), y) for f in (0.02, 0.04, 0.96, 0.98)):
                    return False
                fs = [0.05 + k * 0.0643 for k in range(15)]
                return sum(1 for f in fs if is_h(cl + f * (cr - cl), y)) >= 12

            sessions = []
            for wd, (cl, cr) in enumerate(cols):
                blocks, cur = [], None
                for i, t in enumerate(times):
                    shade = px(cl + 2, t["c"])
                    if cur is not None and (separated(cl, cr, row_top[i]) or abs(shade - cur["shade"]) > 6):
                        cur = None
                    if cur is None:
                        cur = {"i0": i, "i1": i, "shade": shade}
                        blocks.append(cur)
                    else:
                        cur["i1"] = i
                for b in blocks:
                    top, bot = row_top[b["i0"]], row_bot[b["i1"]]
                    lbl = [w for w in words if cl < (w["x0"] + w["x1"]) / 2 < cr
                           and top < (w["top"] + w["bottom"]) / 2 < bot]
                    label = " ".join(w["text"] for w in sorted(lbl, key=lambda w: (round(w["top"]), w["x0"])))
                    if not NIT_RX.match(label):
                        continue
                    s, e = times[b["i0"]]["s"], times[b["i1"]]["e"]
                    sessions.append({"weekday": wd, "start": _hhmm(s), "end": _hhmm(e),
                                     "minutes": e - s, "label": label})
            out["people"].append({"name": name, "program": "",
                                  "sessions": sorted(sessions, key=lambda x: (x["weekday"], _tmins(x["start"])))})
    return out


# ══════════════════════════════════════════════════════════════════════════════
# NAME MATCHING (bulletin + timetable → tracker staff)
# ══════════════════════════════════════════════════════════════════════════════
def _norm(s):
    s = re.sub(r"\(.*?\)", " ", str(s or "").lower())
    s = re.sub(r"\b(mr|mrs|ms|miss|dr)\b\.?", " ", s)
    s = re.sub(r"[^a-z' ]+", " ", s)
    return " ".join(s.split())


def build_matcher(staff_rows):
    idx = {}

    def add(k, sid):
        if k:
            idx.setdefault(k, set()).add(sid)

    for s in staff_rows:
        full = _norm(s["name"])
        toks = full.split()
        add(full, s["id"])
        if toks:
            add(toks[0], s["id"])
        if len(toks) > 1:
            add(toks[-1], s["id"])
            add(f"{toks[0]} {toks[-1][0]}", s["id"])
        for a in re.split(r"[,;]", str(s.get("aliases") or "")):
            add(_norm(a), s["id"])

    def match(text):
        k = _norm(text)
        if not k:
            return None, "blank"
        for cand in (k, " ".join(k.split()[:2]), k.split()[0]):
            ids = idx.get(cand)
            if ids and len(ids) == 1:
                return next(iter(ids)), "ok"
            if ids and len(ids) > 1 and cand == k:
                return None, "ambiguous"
        return None, "no match"

    return match


def split_names(text):
    parts = re.split(r"\s*(?:,|/|&|;|\+|\n|\band\b)\s*", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def parse_portion(text):
    t = str(text or "").lower()
    if re.search(r"\b(am|a\.m\.?|morning)\b", t):
        return "Morning", 0.5
    if re.search(r"\b(pm|p\.m\.?|afternoon|arvo)\b", t):
        return "Afternoon", 0.5
    if re.search(r"\b(half|part)\b", t):
        return "Part day", 0.5
    return "Full day", 1.0


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


def _merge_cfg(base, stored):
    out = {}
    for k, v in base.items():
        sv = stored.get(k) if isinstance(stored, dict) else None
        if isinstance(v, dict):
            out[k] = {**v, **(sv or {})}
        elif sv is not None:
            out[k] = sv
        else:
            out[k] = list(v) if isinstance(v, list) else v
    for k, v in (stored or {}).items():
        out.setdefault(k, v)
    return out


@st.cache_data(ttl=60, show_spinner=False)
def load_setting(key):
    try:
        res = sb().table(T_SETTINGS).select("*").eq("key", key).execute()
        return res.data[0].get("value") if res.data else None
    except Exception:
        return None


def save_setting(key, value):
    sb().table(T_SETTINGS).upsert({"key": key, "value": value,
                                   "updated_at": datetime.now().isoformat()}).execute()
    refresh()


def load_config():
    c = _merge_cfg(DEFAULT_CONFIG, load_setting("config") or {})
    ts = c.get("timetable_source", {})
    if ts.get("mode") in ("storage",) or (ts.get("mode") == "url" and
                                          str(ts.get("url", "")).endswith("clc-portal.pages.dev/timetable.pdf")):
        ts["mode"] = "portal"           # v2 default pointed at the old Cloudflare copy
    return c


@st.cache_data(ttl=60, show_spinner=False)
def load_staff():
    return _fetch_all(lambda: sb().table(T_STAFF).select("*").order("display_order").order("name"))


@st.cache_data(ttl=60, show_spinner=False)
def load_entries(start_iso, end_iso, include_dismissed=False):
    rows = _fetch_all(lambda: sb().table(T_ENTRIES).select("*")
                      .gte("entry_date", start_iso).lte("entry_date", end_iso).order("entry_date"))
    return rows if include_dismissed else [r for r in rows if not r.get("dismissed")]


@st.cache_data(ttl=60, show_spinner=False)
def load_opening(year, term):
    return _fetch_all(lambda: sb().table(T_OPEN).select("*").eq("year", year).eq("term", term))


@st.cache_data(ttl=60, show_spinner=False)
def load_versions():
    return _fetch_all(lambda: sb().table(T_TTV).select("*").order("id"))


@st.cache_data(ttl=60, show_spinner=False)
def load_sessions(version_id):
    return _fetch_all(lambda: sb().table(T_TTS).select("*").eq("version_id", int(version_id)).order("id"))


def insert_entries(rows):
    if rows:
        sb().table(T_ENTRIES).insert(rows).execute()
        refresh()


# ══════════════════════════════════════════════════════════════════════════════
# TERMS
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
        return past[-1]
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


cfg = load_config()
TERMS = term_list(cfg)
CLOSURES = closure_set(cfg)
TODAY = date.today()


def is_school_day(d):
    return d.weekday() < 5 and d not in CLOSURES and any(t["start"] <= d <= t["end"] for t in TERMS)


# ══════════════════════════════════════════════════════════════════════════════
# TIMETABLE VERSIONS → ROSTER
# ══════════════════════════════════════════════════════════════════════════════
def active_versions():
    vs = [v for v in load_versions() if v.get("status") == "active" and v.get("effective_from")]
    return sorted(vs, key=lambda v: (to_date(v["effective_from"]), v["id"]))


@st.cache_data(ttl=60, show_spinner=False)
def roster_table():
    """[(effective_from, version_id, {staff_id: [min Mon..Fri]})] for active versions."""
    out = []
    for v in active_versions():
        grid, times = {}, {}
        for s in load_sessions(v["id"]):
            if s.get("counted", True) and s.get("staff_id") and 0 <= int(s["weekday"]) <= 4:
                wd, m = int(s["weekday"]), int(s.get("minutes") or 0)
                grid.setdefault(s["staff_id"], [0] * 5)[wd] += m
                try:
                    start = _tmins(s.get("start_time") or "")
                except Exception:
                    start = None
                times.setdefault(s["staff_id"], [[] for _ in range(5)])[wd].append([start, m])
        out.append((str(v["effective_from"])[:10], v["id"], grid, times))
    return out


def version_for(d, table=None):
    table = table if table is not None else roster_table()
    cur = None
    for row in table:
        if to_date(row[0]) <= d:
            cur = row
    return cur


MIDDAY = 12 * 60 + 30   # sessions starting before 12:30 count as "morning"


def nit_lost_to_absence(staff_id, d, absn, sched, table=None):
    """Minutes of timetabled NIT the teacher missed because of absence that day.
    Half-day absences use the session times (morning absence only loses morning NIT)."""
    if not absn or not sched:
        return 0
    if any(x.get("covers_nit", True) and (x.get("portion") or "Full day") in ("Full day", "Part day", "")
           for x in absn):
        return sched
    v = version_for(d, table)
    sess = (v[3].get(staff_id, [[]] * 5)[d.weekday()] if v and len(v) > 3 else [])
    lost = 0
    for portion in {x.get("portion") for x in absn if x.get("covers_nit", True)}:
        if any(st_ is None for st_, _ in sess):
            return sched                     # no times known (manual timetable) — assume all
        if portion == "Morning":
            lost += sum(m for st_, m in sess if st_ < MIDDAY)
        elif portion == "Afternoon":
            lost += sum(m for st_, m in sess if st_ >= MIDDAY)
    return min(lost, sched)


def rostered(staff_id, d, table=None):
    if d.weekday() > 4:
        return 0
    v = version_for(d, table)
    return v[2].get(staff_id, [0] * 5)[d.weekday()] if v else 0


def create_version(parsed, source, source_name, source_hash, staff_rows, status="pending",
                   effective_from=None, notes=""):
    match = build_matcher(staff_rows)
    rec = {"status": status, "source": source, "source_name": source_name,
           "source_hash": source_hash, "term_label": parsed.get("term_label", ""),
           "effective_from": effective_from.isoformat() if effective_from else None,
           "notes": notes, "applied_at": datetime.now().isoformat() if status == "active" else None}
    vid = sb().table(T_TTV).insert(rec).execute().data[0]["id"]
    rows = []
    for p in parsed.get("people", []):
        sid, _ = match(p["name"])
        for s in p["sessions"]:
            rows.append({"version_id": vid, "staff_name_raw": p["name"], "staff_id": sid,
                         "weekday": s["weekday"], "start_time": s["start"], "end_time": s["end"],
                         "minutes": int(s["minutes"]), "label": s["label"], "counted": True})
    if rows:
        sb().table(T_TTS).insert(rows).execute()
    refresh()
    return vid


def _bucket_names():
    out = []
    for bk in sb().storage.list_buckets() or []:
        n = bk.get("name") if isinstance(bk, dict) else getattr(bk, "name", None) or getattr(bk, "id", None)
        if n:
            out.append(n)
    return out


def _list_pdfs(bucket, prefix="", depth=2):
    """PDFs in a bucket folder (and up to `depth` levels of sub-folders)."""
    found = []
    try:
        items = sb().storage.from_(bucket).list(prefix, {"limit": 1000}) or []
    except TypeError:
        items = sb().storage.from_(bucket).list(prefix) or []
    for it in items:
        name = str(it.get("name") or "")
        path = f"{prefix}/{name}" if prefix else name
        if it.get("id") is None and "." not in name and depth > 0:      # folder
            found += _list_pdfs(bucket, path, depth - 1)
        elif name.lower().endswith(".pdf"):
            found.append({"bucket": bucket, "path": path, "name": name,
                          "when": str(it.get("updated_at") or it.get("created_at") or "")})
    return found


def discover_portal_timetables(src):
    """Newest PDF of each timetable in the portal's Supabase Storage
    (files the Timetable page saves, e.g. timetable_specialist_1f4ad4.pdf)."""
    buckets = [src["bucket"]] if (src.get("bucket") or "").strip() else _bucket_names()
    prefix = (src.get("prefix") or "").strip().strip("/")
    files = []
    for bk in buckets:
        try:
            files += [f for f in _list_pdfs(bk, prefix) if "timetable" in (f["path"]).lower()]
        except Exception:
            continue
    latest = {}
    for f in files:
        key = (f["bucket"], re.sub(r"[_\-][0-9a-f]{4,}(?=\.pdf$)", "", f["path"].lower()))
        if key not in latest or f["when"] > latest[key]["when"]:
            latest[key] = f
    return sorted(latest.values(), key=lambda f: f["path"])


def read_portal_timetable_table(src):
    """The portal Timetable page stores each upload as a row in `timetable_store`
    (program, filename, uploaded_at, file_data = base64 PDF). Returns the newest
    upload for every program as [(bytes, name)], or [] if the table isn't there."""
    import base64
    table = (src.get("table") or "timetable_store").strip()
    try:
        meta = _fetch_all(lambda: sb().table(table).select("id, program, filename, uploaded_at")
                          .order("uploaded_at", desc=True))
    except Exception:
        return []
    newest = {}
    for r in meta:
        prog = str(r.get("program") or "")
        if prog not in newest:                    # rows come newest first
            newest[prog] = r
    files = []
    for prog, r in sorted(newest.items()):
        try:
            row = sb().table(table).select("file_data").eq("id", r["id"]).execute().data
            raw = base64.b64decode(row[0]["file_data"]) if row and row[0].get("file_data") else b""
        except Exception:
            raw = b""
        if raw[:4] == b"%PDF":
            files.append((raw, f"{prog}: {r.get('filename') or 'timetable.pdf'}"))
    return files


def fetch_timetable_source(src):
    """Returns [(bytes, display_name), ...] or raises."""
    mode = src.get("mode", "off")
    if mode == "url":
        url = (src.get("url") or "").strip()
        if not url:
            raise RuntimeError("No timetable URL set.")
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(f"{url}{sep}nocache={int(time.time())}",
                                     headers={"User-Agent": "CLC-LBU-portal"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return [(r.read(), url)]
    if mode == "portal":
        files = read_portal_timetable_table(src)
        if files:
            return files
    if mode in ("portal", "storage"):
        files = discover_portal_timetables(src)
        if not files:
            raise RuntimeError("No timetable PDFs found in the Timetable page's table "
                               f"('{src.get('table') or 'timetable_store'}') or in file storage"
                               + (f" (bucket '{src.get('bucket')}')" if src.get("bucket") else "")
                               + ". Set the bucket in Setup → Timetable source, or upload the PDFs on "
                                 "the NIT Timetable tab.")
        return [(sb().storage.from_(f["bucket"]).download(f["path"]), f"{f['bucket']}/{f['path']}")
                for f in files]
    raise RuntimeError("Timetable source is off.")


def parse_many(files):
    """Parse several timetable PDFs into one combined timetable."""
    merged = {"term_label": "", "people": [], "warnings": []}
    labels, seen = {}, {}
    for data, name in files:
        r = parse_timetable_pdf(data)
        merged["warnings"] += [f"{name}: {w}" for w in r.get("warnings", [])]
        if r.get("term_label"):
            labels[r["term_label"]] = labels.get(r["term_label"], 0) + 1
        for p in r["people"]:
            k = _norm(p["name"])
            if k in seen and not p["sessions"]:
                continue
            seen[k] = p
    merged["people"] = list(seen.values())
    merged["term_label"] = max(labels, key=labels.get) if labels else ""
    return merged


def files_hash(files):
    return hashlib.sha256("|".join(sorted(hashlib.sha256(d).hexdigest() for d, _ in files)).encode()).hexdigest()


def check_timetable_source(staff_rows, force=False):
    """Pull the portal timetable; create a new version if it changed.
    Auto-applies when the PDF's term matches the current/next term."""
    src = cfg.get("timetable_source", {})
    if src.get("mode", "off") == "off":
        return None
    last = st.session_state.get("nit_tt_checked", 0)
    prev_ok = (load_setting("timetable_check") or {}).get("ok", True)
    if not force and time.time() - last < (3600 if prev_ok else 120):
        return None
    st.session_state["nit_tt_checked"] = time.time()
    try:
        files = fetch_timetable_source(src)
    except Exception as e:
        msg = f"Couldn't read the timetable source: {e}"
        save_setting("timetable_check", {"at": datetime.now().isoformat(), "ok": False, "msg": msg})
        return msg
    h = files_hash(files)
    name = ", ".join(n.split("/")[-1] for _, n in files)[:300]
    if any(v.get("source_hash") == h for v in load_versions()):
        save_setting("timetable_check", {"at": datetime.now().isoformat(), "ok": True,
                                         "msg": "No change since last check."})
        return None
    try:
        parsed = parse_many(files)
    except Exception as e:
        msg = f"New timetable found but couldn't be read: {e}"
        save_setting("timetable_check", {"at": datetime.now().isoformat(), "ok": False, "msg": msg})
        return msg
    cur = current_term(TERMS, TODAY)
    nxt = [t for t in TERMS if t["start"] > TODAY]
    target = None
    for t in ([cur] if cur and cur["start"] <= TODAY <= cur["end"] else []) + nxt[:1]:
        if parsed.get("term_label") == term_label(t):
            target = t
    match = build_matcher(staff_rows)
    matched = sum(1 for p in parsed["people"] if p["sessions"] and match(p["name"])[0])
    auto = bool(src.get("auto_apply", True)) and target is not None and matched > 0
    eff = None
    if target:
        earlier_this_term = [v for v in active_versions()
                             if target["start"] <= to_date(v["effective_from"]) <= TODAY]
        # first timetable for this term → applies from the first day of term; a mid-term change → from today
        eff = TODAY if (target["start"] <= TODAY and earlier_this_term) else target["start"]
    create_version(parsed, src.get("mode"), name, h, staff_rows,
                   status="active" if auto else "pending", effective_from=eff if auto else None,
                   notes="Auto-applied" if auto else "Waiting for review")
    msg = (f"New NIT timetable ({parsed.get('term_label') or 'no term label'}) applied automatically "
           f"from {eff:%a %d %b}." if auto else
           f"New timetable found ({parsed.get('term_label') or 'no term label'}) — review it on the "
           f"NIT Timetable tab before it's used.")
    save_setting("timetable_check", {"at": datetime.now().isoformat(), "ok": True, "msg": msg})
    return msg


# ══════════════════════════════════════════════════════════════════════════════
# DAILY BULLETIN → ABSENCE SYNC
# ══════════════════════════════════════════════════════════════════════════════
def read_bulletin_absences(start, end, staff_rows):
    """Returns (found {(staff_id, date): {...}}, unmatched [..], error or None)."""
    b = cfg.get("bulletin", {})
    match = build_matcher(staff_rows)
    try:
        rows = _fetch_all(lambda: sb_bulletin().table(b.get("table", "bulletins")).select("*")
                          .gte(b.get("date_col", "date"), start.isoformat())
                          .lte(b.get("date_col", "date"), end.isoformat()))
    except Exception as e:
        return {}, [], f"Couldn't read Daily Bulletin table '{b.get('table')}': {e}"
    found, unmatched = {}, []
    name_keys, reason_keys = b.get("name_keys", []), b.get("reason_keys", [])
    for row in rows:
        try:
            d = to_date(row.get(b.get("date_col", "date")))
        except Exception:
            continue
        if not is_school_day(d) or d > TODAY:
            continue
        items = []
        for col in b.get("absence_cols", []):
            for it in as_list(row.get(col)):
                if isinstance(it, dict):
                    nm = next((str(it[k]) for k in name_keys if str(it.get(k) or "").strip()), "")
                    rs = next((str(it[k]) for k in reason_keys if str(it.get(k) or "").strip()), "")
                    if nm:
                        items.append((nm, rs))
                elif isinstance(it, str) and it.strip():
                    items.append((it, ""))
        pcol = b.get("program_changes_col")
        if pcol:
            for it in as_list(row.get(pcol)):
                if isinstance(it, dict) and str(it.get("change_reason", "")).strip().lower() == "staff absence":
                    nm = str(it.get("staff_absent") or "").strip()
                    if nm:
                        items.append((nm, "Program change — staff absence"))
        for raw, reason in items:
            for one in split_names(raw):
                portion, frac = parse_portion(one)
                sid, why = match(one)
                if not sid:
                    unmatched.append({"date": d.isoformat(), "name": one, "why": why})
                    continue
                k = (sid, d)
                prev = found.get(k)
                if prev is None or frac > prev["frac"]:
                    found[k] = {"frac": frac, "portion": portion,
                                "reason": (reason or "From Daily Bulletin").strip()[:120], "raw": one}
    return found, unmatched, None


def sync_bulletin(start, end, staff_rows):
    if not cfg.get("bulletin", {}).get("enabled", True):
        return {"skipped": True}
    end = min(end, TODAY)
    if end < start:
        return {"inserted": 0, "updated": 0, "removed": 0, "unmatched": []}
    found, unmatched, err = read_bulletin_absences(start, end, staff_rows)
    if err:
        res = {"error": err, "at": datetime.now().isoformat()}
        save_setting("bulletin_sync", res)
        return res
    existing = load_entries(start.isoformat(), end.isoformat(), include_dismissed=True)
    manual_abs = {(e["staff_id"], to_date(e["entry_date"])) for e in existing
                  if e["entry_type"] == "absence" and (e.get("source") or "manual") == "manual"
                  and not e.get("dismissed")}
    auto = {e.get("source_ref"): e for e in existing if str(e.get("source") or "").startswith("bulletin")}
    ins, upd, rem = [], 0, 0
    for (sid, d), f in found.items():
        ref = f"bulletin:{d.isoformat()}:{sid}"
        if (sid, d) in manual_abs:
            continue
        e = auto.get(ref)
        if e is None:
            ins.append({"entry_date": d.isoformat(), "staff_id": sid, "entry_type": "absence",
                        "minutes": 0, "day_fraction": f["frac"], "portion": f["portion"],
                        "category": f["reason"], "notes": f"Daily Bulletin: {f['raw']}"[:200],
                        "covers_nit": True, "entered_by": "auto", "source": "bulletin",
                        "source_ref": ref, "dismissed": False})
        elif e.get("source") == "bulletin" and not e.get("dismissed") and (
                float(e.get("day_fraction") or 0) != f["frac"] or e.get("portion") != f["portion"]):
            sb().table(T_ENTRIES).update({"day_fraction": f["frac"], "portion": f["portion"],
                                          "category": f["reason"]}).eq("id", e["id"]).execute()
            upd += 1
    live_refs = {f"bulletin:{d.isoformat()}:{sid}" for (sid, d) in found}
    for ref, e in auto.items():
        if e.get("source") == "bulletin" and not e.get("dismissed") and ref not in live_refs:
            sb().table(T_ENTRIES).delete().eq("id", e["id"]).execute()
            rem += 1
    if ins:
        sb().table(T_ENTRIES).insert(ins).execute()
    refresh()
    res = {"at": datetime.now().isoformat(), "inserted": len(ins), "updated": upd, "removed": rem,
           "unmatched": unmatched[-40:], "range": f"{start:%d/%m} – {end:%d/%m/%Y}"}
    save_setting("bulletin_sync", res)
    return res


# ══════════════════════════════════════════════════════════════════════════════
# CALCULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def build_daily(staff, entries, t, upto=None):
    base = float(cfg.get("base_minutes_fte1", 250) or 0)
    table = roster_table()
    end = min(t["end"], upto) if upto else t["end"]
    days = [d for d in daterange(t["start"], end) if d.weekday() < 5 and d not in CLOSURES]

    agg = {}
    for e in entries:
        if e.get("dismissed"):
            continue
        k = (e["staff_id"], to_date(e["entry_date"]))
        a = agg.setdefault(k, {"missed": 0, "additional": 0, "override": None,
                               "abs_manual": [], "abs_auto": []})
        et = e["entry_type"]
        if et in ("missed", "additional"):
            a[et] += int(e.get("minutes") or 0)
        elif et == "override":
            a["override"] = (a["override"] or 0) + int(e.get("minutes") or 0)
        elif et == "absence":
            (a["abs_manual"] if (e.get("source") or "manual") == "manual" else a["abs_auto"]).append(e)

    rows = []
    for s in staff:
        wdays = parse_workdays(s.get("work_days"))
        accrual = (float(s.get("fte") or 0) * base / len(wdays)) if wdays else 0.0
        for d in days:
            a = agg.get((s["id"], d), {})
            absn = a.get("abs_manual") or a.get("abs_auto") or []
            frac = min(1.0, sum(float(x.get("day_fraction") or 0) for x in absn))
            works = d.weekday() in wdays
            ent = accrual * (1 - frac) if works else 0.0
            sched = rostered(s["id"], d, table)
            if a.get("override") is not None:
                received, missed, add, lost = a["override"], 0, 0, 0
            else:
                lost = nit_lost_to_absence(s["id"], d, absn, sched, table)
                base_rec = sched - lost
                missed = min(a.get("missed", 0), base_rec)
                add = a.get("additional", 0)
                received = base_rec - missed + add
            rows.append({
                "staff_id": s["id"], "Staff": s["name"], "date": d, "week": week_no(t, d),
                "rostered": sched, "entitlement": ent, "missed": missed, "additional": add,
                "lost_absence": lost, "received": received, "balance": received - ent,
                "absent_days": frac,
                "absent_src": ("manual" if a.get("abs_manual") else ("bulletin" if a.get("abs_auto") else "")),
                "override": a.get("override") is not None,
            })
    cols = ["staff_id", "Staff", "date", "week", "rostered", "entitlement", "missed", "additional",
            "lost_absence", "received", "balance", "absent_days", "absent_src", "override"]
    return pd.DataFrame(rows, columns=cols)


def staff_summary(staff, daily, opening):
    base = float(cfg.get("base_minutes_fte1", 250) or 0)
    ob = {o["staff_id"]: int(o.get("minutes") or 0) for o in opening}
    ref_day = TODAY if (TERMS and any(t["start"] <= TODAY <= t["end"] for t in TERMS)) else (
        daily["date"].max() if not daily.empty else TODAY)
    v = version_for(ref_day)
    rows = []
    for s in staff:
        d = daily[daily["staff_id"] == s["id"]]
        weekly_roster = sum(v[2].get(s["id"], [0] * 5)) if v else 0
        fte_ent = round(base * float(s.get("fte") or 0))
        open_bal = ob.get(s["id"], 0)
        bal = open_bal + float(d["balance"].sum())
        rows.append({
            "staff_id": s["id"], "Staff": s["name"], "FTE": float(s.get("fte") or 0),
            "Rostered / wk": weekly_roster, "FTE entitlement / wk": fte_ent,
            "Opening": open_bal, "Entitled": float(d["entitlement"].sum()),
            "Rostered": int(d["rostered"].sum()),
            "Lost to absence": int(d["lost_absence"].sum()),
            "Missed": int(d["missed"].sum()), "Additional": int(d["additional"].sum()),
            "Received": int(d["received"].sum()), "Balance": round(bal),
            "Absent days": float(d["absent_days"].sum()),
            "Roster check": ("⚠️ Rostered below entitlement" if weekly_roster < fte_ent
                             else ("Rostered above entitlement" if weekly_roster > fte_ent else "✓")),
            "Status": "🔴 Owed" if round(bal) < 0 else ("🔵 Over" if round(bal) > 0 else "🟢 Square"),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD + AUTO SYNC
# ══════════════════════════════════════════════════════════════════════════════
all_staff = load_staff()
staff = [s for s in all_staff if s.get("active", True)]
staff_by_id = {s["id"]: s for s in all_staff}

st.markdown("""
<style>
.nit-head {border-left: 6px solid #1f6f78; padding: 0.2rem 0 0.2rem 0.9rem; margin-bottom: 0.6rem;}
.nit-head h1 {font-size: 1.7rem; margin: 0; color: #1f3b4d;}
.nit-head p {margin: 0.15rem 0 0; color: #5a6b75;}
</style>
<div class="nit-head"><h1>⏱️ NIT & Staff Absence Tracker</h1>
<p>NIT comes from the timetable, absences from the Daily Bulletin. You only fix what's different.</p></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.text_input("Your initials (recorded on entries)", key="nit_entered_by", max_chars=10)

if not TERMS:
    st.error("No term dates configured — add them in Setup.")
if not staff:
    st.warning("No active staff yet. Go to **Setup** to add staff.")

# Automatic pulls (timetable hourly, bulletin every 10 min per session)
if staff and TERMS:
    try:
        tt_msg = check_timetable_source(all_staff)
        if tt_msg:
            st.toast(tt_msg)
    except Exception as e:
        st.warning(f"Timetable check failed: {e}")
    cur_t = current_term(TERMS, TODAY)
    if cur_t and time.time() - st.session_state.get("nit_bul_synced", 0) > 600:
        st.session_state["nit_bul_synced"] = time.time()
        try:
            sync_bulletin(cur_t["start"], cur_t["end"], staff)
        except Exception as e:
            st.warning(f"Daily Bulletin sync failed: {e}")

if TERMS and staff and not roster_table():
    _tc = load_setting("timetable_check") or {}
    st.info("📋 No NIT timetable is in force yet, so rostered NIT shows as 0. "
            "Go to **NIT Timetable** to review/apply one."
            + (f"\n\n**Last timetable check:** {_tc.get('msg')}" if _tc.get("msg") else ""))
pending_versions = [v for v in load_versions() if v.get("status") == "pending"]
if pending_versions:
    st.warning(f"🗓️ {len(pending_versions)} new NIT timetable(s) waiting for review on the **NIT Timetable** tab.")

with st.expander("How this works"):
    st.markdown(f"""
- **NIT given** comes from the **NIT timetable** (read from the portal timetable PDF). Rostered NIT is **assumed received** unless you change it in **Log** (missed, additional, or set the actual minutes for a day).
- **Staff absence** is pulled from the **Daily Bulletin** (📰). An absent teacher's rostered NIT that day is **not received**, and their **entitlement for that week drops pro rata** (FTE × {fmt(cfg.get('base_minutes_fte1', 250))} ÷ their working days, per day away).
- **Balance = NIT received − entitlement** (+ opening balance). **Negative = owed to the teacher.**
- Manual entries always win. Deleting a 📰 auto entry dismisses it (it won't come back); editing it locks your version.
- Closure days in Setup are excluded from both NIT and entitlement.
""")


def term_picker(key, default=None):
    if not TERMS:
        return None
    default = default or current_term(TERMS, TODAY)
    labels = [term_label(t) for t in TERMS]
    idx = labels.index(term_label(default)) if default else 0
    choice = st.selectbox("Term", labels, index=idx, key=key)
    return TERMS[labels.index(choice)]


tabs = st.tabs(["📅 This Week", "✍️ Log", "📊 Leadership", "🗓️ NIT Timetable",
                "🗂️ History", "⚙️ Setup", "⬇️ Export"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB — THIS WEEK
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
        daily = build_daily(staff, ents, t)
        wdf = daily[daily["week"] == wk]
        dindex = {(r.staff_id, r.date): r for r in wdf.itertuples()}

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
                r = dindex.get((s["id"], d))
                es = by_key.get((s["id"], d), [])
                parts = []
                if r is not None and r.absent_days:
                    absn = [e for e in es if e["entry_type"] == "absence"]
                    por = absn[0].get("portion") if absn else ""
                    parts.append(("📰 " if r.absent_src == "bulletin" else "🏠 ") + "Absent"
                                 + ("" if por in ("Full day", None, "") else f" ({por.lower()})"))
                if r is not None and r.override:
                    parts.append(f"✏️ NIT {fmt(r.received)}")
                elif r is not None and r.rostered:
                    if r.lost_absence:
                        parts.append(f"NIT {fmt(r.lost_absence)} not received")
                        if r.rostered > r.lost_absence:
                            parts.append(f"✅ NIT {fmt(r.rostered - r.lost_absence)}")
                    elif r.missed:
                        parts.append(f"❌ missed {fmt(r.missed)}")
                    elif d <= TODAY:
                        parts.append(f"✅ NIT {fmt(r.rostered)}")
                    else:
                        parts.append(f"NIT {fmt(r.rostered)}")
                if r is not None and r.additional and not r.override:
                    parts.append(f"➕ {fmt(r.additional)}")
                row[col] = " · ".join(parts)
            sd = wdf[wdf["staff_id"] == s["id"]]
            row["Entitled"] = fmt(sd["entitlement"].sum())
            row["Received"] = fmt(sd["received"].sum())
            row["Week balance"] = fmt(sd["balance"].sum(), signed=True)
            rows.append(row)

        st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)
        st.caption("✅ received as timetabled (assumed) · ❌ missed · ➕ additional · ✏️ set by admin · "
                   "📰 absent (from Daily Bulletin) · 🏠 absent (logged here) · "
                   "Entitled is pro rata for days worked.")
        m1, m2, m3 = st.columns(3)
        m1.metric("NIT missed this week", fmt(wdf["missed"].sum()))
        m2.metric("NIT not received (absent)", fmt(wdf["lost_absence"].sum()))
        m3.metric("Net for the site", fmt(wdf["balance"].sum(), signed=True))


# ══════════════════════════════════════════════════════════════════════════════
# TAB — LOG
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    if staff:
        bs = load_setting("bulletin_sync") or {}
        if bs.get("error"):
            st.error(f"📰 Daily Bulletin sync: {bs['error']}")
        elif bs.get("at"):
            st.caption(f"📰 Daily Bulletin last synced {to_date(bs['at']):%d/%m} "
                       f"{bs['at'][11:16]} — {bs.get('inserted', 0)} added, {bs.get('updated', 0)} updated, "
                       f"{bs.get('removed', 0)} removed ({bs.get('range', '')}).")
            if bs.get("unmatched"):
                with st.expander(f"⚠️ {len(bs['unmatched'])} bulletin name(s) didn't match a tracker staff member"):
                    st.dataframe(pd.DataFrame(bs["unmatched"]), hide_index=True, **WIDE)
                    st.caption("Add the name as an alias in Setup (e.g. 'Ben Sel'), or ignore if not a teacher.")
        if st.button("🔄 Sync Daily Bulletin now"):
            ct = current_term(TERMS, TODAY)
            r = sync_bulletin(ct["start"], ct["end"], staff)
            st.session_state["nit_bul_synced"] = time.time()
            st.success("Synced." if not r.get("error") else r["error"])
            rerun()

        kind = st.radio("What are you recording?",
                        ["❌ Missed NIT", "➕ Additional NIT", "✏️ Set actual NIT for a day",
                         "🏠 Staff absence", "📅 NIT cancelled for a whole day"],
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
            sched = rostered(s["id"], d)
            if msg := _not_school_day(d):
                st.warning(msg)
            if sched == 0:
                st.info(f"{who_s} has no NIT timetabled on {d:%A}. You can still log minutes if NIT was moved.")
            c3, c4 = st.columns(2)
            mins = c3.number_input("Minutes missed", 0, 600, sched, step=5, key=f"m_min_{s['id']}_{d}")
            reason = c4.selectbox("Reason", cfg["missed_reasons"], key="m_reason")
            notes = st.text_input("Notes (optional)", key="m_notes")
            ex = _existing(s["id"], d)
            if any(e["entry_type"] == "absence" for e in ex):
                st.warning(f"{who_s} is absent that day — their NIT is already counted as not received.")
            if any(e["entry_type"] == "missed" for e in ex):
                st.warning("Missed NIT is already logged for this person on this date.")
            if st.button("Save missed NIT", type="primary", disabled=mins <= 0):
                insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "missed",
                                 "minutes": int(mins), "category": reason, "notes": notes,
                                 "entered_by": who(), "source": "manual"}])
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
                                 "entered_by": who(), "source": "manual"}])
                st.success(f"Logged {fmt(mins)} additional NIT for {who_s}.")
                rerun()

        elif kind == "✏️ Set actual NIT for a day":
            st.caption("Overrides everything else for that person and day: the minutes you enter are the NIT "
                       "they actually received (missed/additional for that day are ignored).")
            c1, c2 = st.columns(2)
            d = c1.date_input("Date", TODAY, format="DD/MM/YYYY", key="o_date")
            who_s = c2.selectbox("Staff member", names, key="o_staff")
            s = name_to[who_s]
            if msg := _not_school_day(d):
                st.warning(msg)
            st.caption(f"Timetabled that day: {fmt(rostered(s['id'], d))}")
            c3, c4 = st.columns(2)
            mins = c3.number_input("NIT actually received (minutes)", 0, 600, rostered(s["id"], d), step=5,
                                   key=f"o_min_{s['id']}_{d}")
            notes = c4.text_input("Reason / notes", key="o_notes")
            if any(e["entry_type"] == "override" for e in _existing(s["id"], d)):
                st.warning("An actual-NIT value already exists for this day — delete it in History first.")
            if st.button("Save actual NIT", type="primary"):
                insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "override",
                                 "minutes": int(mins), "category": "Set by admin", "notes": notes,
                                 "entered_by": who(), "source": "manual"}])
                st.success(f"Set {who_s}'s NIT on {d:%a %d %b} to {fmt(mins)}.")
                rerun()

        elif kind == "🏠 Staff absence":
            st.caption("Absences in the Daily Bulletin are added automatically — use this for anything the "
                       "bulletin missed, or to replace an auto entry (manual always wins).")
            c1, c2, c3 = st.columns(3)
            who_s = c1.selectbox("Staff member", names, key="ab_staff")
            d1 = c2.date_input("From", TODAY, format="DD/MM/YYYY", key="ab_from")
            d2 = c3.date_input("To", d1, format="DD/MM/YYYY", key=f"ab_to_{d1}")
            s = name_to[who_s]
            c4, c5 = st.columns(2)
            portion = c4.selectbox("Portion of each day", ["Full day", "Morning", "Afternoon", "Part day"],
                                   key="ab_portion")
            ltype = c5.selectbox("Leave type", cfg["absence_types"], key="ab_type")
            covers = st.checkbox("Away during their timetabled NIT (NIT not received)",
                                 value=(portion == "Full day"), key=f"ab_cov_{portion}")
            notes = st.text_input("Notes (optional — avoid personal/medical detail)", key="ab_notes")
            frac = {"Full day": 1.0, "Morning": 0.5, "Afternoon": 0.5, "Part day": 0.25}[portion]
            plan = []
            if d2 < d1:
                st.error("'To' date is before 'From' date.")
            else:
                for d in daterange(d1, d2):
                    if is_school_day(d):
                        plan.append({"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "absence",
                                     "minutes": 0, "day_fraction": frac, "portion": portion,
                                     "covers_nit": bool(covers), "category": ltype, "notes": notes,
                                     "entered_by": who(), "source": "manual"})
            if plan:
                st.caption(f"{len(plan)} school day(s): " + ", ".join(
                    to_date(p["entry_date"]).strftime("%a %d %b") for p in plan))
            elif d2 >= d1:
                st.info("No school days in that range.")
            if st.button(f"Save absence ({len(plan)} day{'s' if len(plan) != 1 else ''})",
                         type="primary", disabled=not plan):
                insert_entries(plan)
                st.success(f"Logged absence for {who_s}.")
                rerun()

        else:
            st.caption("Use when NIT couldn't run for several staff on a day — e.g. NIT provider away. "
                       "Logs missed NIT for each ticked person at their timetabled minutes.")
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
            cands = [s for s in staff if rostered(s["id"], d) > 0]
            if not cands:
                st.info(f"No one has NIT timetabled on {d:%A %d %b}.")
            else:
                pick = []
                for s in cands:
                    note = " — absent that day" if s["id"] in absent_ids else (
                        " — missed NIT already logged" if s["id"] in missed_ids else "")
                    if st.checkbox(f"{s['name']} ({fmt(rostered(s['id'], d))}){note}",
                                   value=not note, key=f"c_{s['id']}_{d}"):
                        pick.append(s)
                notes = st.text_input("Notes (optional)", key="c_notes")
                if st.button(f"Log missed NIT for {len(pick)} staff", type="primary", disabled=not pick):
                    insert_entries([{"entry_date": d.isoformat(), "staff_id": s["id"], "entry_type": "missed",
                                     "minutes": rostered(s["id"], d), "category": reason, "notes": notes,
                                     "entered_by": who(), "source": "manual"} for s in pick])
                    st.success(f"Logged missed NIT for {len(pick)} staff on {d:%a %d %b}.")
                    rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB — LEADERSHIP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    if TERMS and staff:
        c1, c2 = st.columns([2, 1])
        with c1:
            t = term_picker("ld_term")
        with c2:
            to_date_only = st.toggle("Term to date only", value=True,
                                     help="Off = include the whole term (future days assume NIT as timetabled).")
        upto = TODAY if to_date_only else None
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat())
        daily = build_daily(staff, ents, t, upto=upto)
        opening = load_opening(t["year"], t["term"])
        summ = staff_summary(staff, daily, opening)

        owed = summ[summ["Balance"] < 0]
        over = summ[summ["Balance"] > 0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Staff owed NIT", f"{len(owed)} of {len(summ)}")
        m2.metric("Total NIT owed", fmt(-owed["Balance"].sum()) if len(owed) else "0m")
        m3.metric("Total over entitlement", fmt(over["Balance"].sum()) if len(over) else "0m")
        m4.metric("Staff absence (days)", f"{summ['Absent days'].sum():g}")

        show = summ.copy()
        for c in ["Rostered / wk", "FTE entitlement / wk", "Opening", "Entitled", "Rostered",
                  "Lost to absence", "Missed", "Additional", "Received"]:
            show[c] = show[c].apply(fmt)
        show["Balance"] = summ["Balance"].apply(lambda v: fmt(v, signed=True))
        show["Absent days"] = show["Absent days"].apply(lambda v: f"{v:g}")
        st.dataframe(show[["Staff", "Status", "Balance", "FTE", "Entitled", "Received", "Rostered",
                           "Lost to absence", "Missed", "Additional", "Absent days", "Opening",
                           "Rostered / wk", "FTE entitlement / wk", "Roster check"]],
                     hide_index=True, **WIDE)
        st.caption("Entitled = FTE × weekly entitlement, pro rata for days actually worked (absence reduces it). "
                   "Received = timetabled NIT − lost to absence − missed + additional (or the actual minutes "
                   "if set). Balance = Opening + Received − Entitled; negative = owed to the teacher.")

        if not daily.empty:
            st.markdown("#### Balance over the term")
            wkb = daily.groupby(["week", "Staff"])["balance"].sum().unstack(fill_value=0).sort_index()
            ob = {staff_by_id[o["staff_id"]]["name"]: int(o["minutes"] or 0)
                  for o in opening if o["staff_id"] in staff_by_id}
            cum = wkb.cumsum()
            for name in cum.columns:
                cum[name] = (cum[name] + ob.get(name, 0)) / 60.0
            cum.index = [f"Wk {i}" for i in cum.index]
            st.line_chart(cum, y_label="Balance (hours, negative = owed)")

        cA, cB = st.columns(2)
        with cA:
            st.markdown("#### Why NIT was missed")
            rs = {}
            for e in ents:
                if e["entry_type"] == "missed" and (upto is None or to_date(e["entry_date"]) <= upto):
                    rs[e.get("category") or "Other"] = rs.get(e.get("category") or "Other", 0) + int(e["minutes"] or 0)
            lost = int(daily["lost_absence"].sum()) if not daily.empty else 0
            if lost:
                rs["Teacher absent on NIT day"] = lost
            if not rs:
                st.caption("No missed NIT logged.")
            else:
                r = pd.Series(rs).sort_values(ascending=False)
                st.bar_chart((r / 60.0).rename("Hours"), horizontal=True)
        with cB:
            st.markdown("#### Absence by leave type (days)")
            adf = pd.DataFrame([e for e in ents if e["entry_type"] == "absence"
                                and (upto is None or to_date(e["entry_date"]) <= upto)])
            if adf.empty:
                st.caption("No absences logged.")
            else:
                adf["Staff"] = adf["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
                adf["category"] = adf["category"].fillna("").replace("", "Unspecified")
                pv = adf.pivot_table(index="Staff", columns="category", values="day_fraction",
                                     aggfunc="sum", fill_value=0)
                pv["Total"] = pv.sum(axis=1)
                st.dataframe(pv.apply(lambda c: c.map(lambda v: f"{v:g}")), **WIDE)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — NIT TIMETABLE
# ══════════════════════════════════════════════════════════════════════════════
def version_name(v):
    eff = to_date(v["effective_from"]).strftime("%d/%m/%Y") if v.get("effective_from") else "not applied"
    return f"#{v['id']} · {v.get('term_label') or 'no term label'} · from {eff} · {v.get('source') or ''}"


with tabs[3]:
    if staff:
        tc = load_setting("timetable_check") or {}
        src = cfg.get("timetable_source", {})
        c1, c2 = st.columns([3, 1])
        c1.caption("Source: **" + {"portal": "Portal Timetable page", "url": "PDF web address",
                                    "off": "off"}.get(src.get("mode"), str(src.get("mode"))) + "** "
                   + (f"— {src.get('url')}" if src.get("mode") == "url" else "")
                   + (f" · last checked {tc['at'][:10]} {tc['at'][11:16]} — {tc.get('msg', '')}" if tc.get("at") else ""))
        if c2.button("🔄 Check for a new timetable"):
            msg = check_timetable_source(all_staff, force=True)
            st.session_state["nit_tt_msg"] = msg or "No change since last check."
            rerun()
        if st.session_state.get("nit_tt_msg"):
            st.info(st.session_state.pop("nit_tt_msg"))

        # ── Pending review
        for v in pending_versions:
            with st.container(border=True):
                st.markdown(f"#### 🆕 Review timetable {version_name(v)}")
                st.caption(f"From {v.get('source_name') or v.get('source')}. Check the people and sessions, "
                           "untick anything that shouldn't count as NIT, then apply.")
                sess = load_sessions(v["id"])
                if not sess:
                    st.warning("No NIT sessions were found in this timetable.")
                names_raw = sorted({s["staff_name_raw"] for s in sess})
                opt = ["— not tracked —"] + [s["name"] for s in staff]
                map_df = pd.DataFrame([{
                    "Timetable name": n,
                    "Tracker staff": next((staff_by_id[s["staff_id"]]["name"] for s in sess
                                           if s["staff_name_raw"] == n and s.get("staff_id") in staff_by_id),
                                          "— not tracked —")} for n in names_raw])
                ed_map = st.data_editor(map_df, hide_index=True, key=f"map_{v['id']}", disabled=["Timetable name"],
                                        column_config={"Tracker staff": st.column_config.SelectboxColumn(
                                            options=opt, required=True)})
                sdf = pd.DataFrame([{"id": s["id"], "Count": bool(s.get("counted", True)),
                                     "Person": s["staff_name_raw"], "Day": DAY_LABELS[int(s["weekday"])],
                                     "Time": f"{s['start_time']}–{s['end_time']}", "Minutes": s["minutes"],
                                     "Label": s["label"]} for s in sess])
                ed_sess = st.data_editor(sdf, hide_index=True, key=f"sess_{v['id']}", **WIDE,
                                         disabled=["Person", "Day", "Time", "Minutes", "Label"],
                                         column_config={"id": None}) if not sdf.empty else sdf
                if not sdf.empty:
                    prev = ed_sess[ed_sess["Count"]].merge(ed_map, left_on="Person", right_on="Timetable name")
                    prev = prev[prev["Tracker staff"] != "— not tracked —"]
                    if not prev.empty:
                        pv = prev.pivot_table(index="Tracker staff", columns="Day", values="Minutes",
                                              aggfunc="sum", fill_value=0)
                        pv = pv.reindex(columns=[d for d in DAY_LABELS if d in pv.columns])
                        pv["Week"] = pv.sum(axis=1)
                        st.markdown("**NIT per week from this timetable**")
                        st.dataframe(pv.apply(lambda c: c.map(fmt)), **WIDE)
                tgt = next((t for t in TERMS if term_label(t) == v.get("term_label")), None)
                dflt = (tgt["start"] if tgt and tgt["start"] > TODAY else TODAY)
                cc1, cc2, cc3 = st.columns([2, 1, 1])
                eff = cc1.date_input("Use from", dflt, format="DD/MM/YYYY", key=f"eff_{v['id']}")
                if v.get("term_label") and tgt is None:
                    st.warning(f"This PDF says **{v['term_label']}**, which isn't a configured term — "
                               "check it's the current timetable before applying.")
                if cc2.button("✅ Apply", type="primary", key=f"apply_{v['id']}"):
                    mp = {r["Timetable name"]: r["Tracker staff"] for _, r in ed_map.iterrows()}
                    name_id = {s["name"]: s["id"] for s in staff}
                    cnt = {int(r["id"]): bool(r["Count"]) for _, r in ed_sess.iterrows()} if not sdf.empty else {}
                    for s in sess:
                        sid = name_id.get(mp.get(s["staff_name_raw"]))
                        sb().table(T_TTS).update({"staff_id": sid, "counted": cnt.get(s["id"], True)}) \
                            .eq("id", s["id"]).execute()
                    sb().table(T_TTV).update({"status": "active", "effective_from": eff.isoformat(),
                                              "applied_at": datetime.now().isoformat(),
                                              "notes": f"Reviewed by {who() or 'admin'}"}).eq("id", v["id"]).execute()
                    refresh()
                    st.success("Timetable applied.")
                    rerun()
                if cc3.button("Reject", key=f"rej_{v['id']}"):
                    sb().table(T_TTV).update({"status": "rejected"}).eq("id", v["id"]).execute()
                    refresh()
                    rerun()

        # ── In force
        st.markdown("#### Timetable in force")
        dsel = st.date_input("As at", TODAY, format="DD/MM/YYYY", key="tt_asat")
        vf = version_for(dsel)
        base = float(cfg.get("base_minutes_fte1", 250) or 0)
        if not vf:
            st.info("No timetable applies on that date.")
        else:
            vrow = next((v for v in load_versions() if v["id"] == vf[1]), {})
            st.caption(version_name(vrow))
            grid_rows = []
            for s in staff:
                mins = vf[2].get(s["id"], [0] * 5)
                ent = round(base * float(s.get("fte") or 0))
                grid_rows.append({"Staff": s["name"], **{DAY_LABELS[i]: fmt(m) if m else "" for i, m in enumerate(mins)},
                                  "Week": fmt(sum(mins)), "FTE entitlement": fmt(ent),
                                  "Difference": fmt(sum(mins) - ent, signed=True)})
            st.dataframe(pd.DataFrame(grid_rows), hide_index=True, **WIDE)
            with st.expander("Sessions in this version"):
                ss = load_sessions(vf[1])
                st.dataframe(pd.DataFrame([{
                    "Staff": staff_by_id.get(s.get("staff_id"), {}).get("name", f"({s['staff_name_raw']} — not tracked)"),
                    "Day": DAY_LABELS[int(s["weekday"])], "Time": f"{s['start_time']}–{s['end_time']}",
                    "Minutes": s["minutes"], "Label": s["label"], "Counted": s.get("counted", True)}
                    for s in ss]), hide_index=True, **WIDE)

        # ── Upload / manual
        cU, cM = st.columns(2)
        with cU:
            st.markdown("#### Upload a timetable PDF")
            up = st.file_uploader("Staff timetable PDF(s) — select all program files at once", type=["pdf"],
                                  key="tt_up", accept_multiple_files=True)
            if up and st.button("Read these PDFs"):
                files = [(f.getvalue(), f.name) for f in up]
                try:
                    parsed = parse_many(files)
                    create_version(parsed, "upload", ", ".join(n for _, n in files)[:300], files_hash(files),
                                   all_staff, status="pending", notes=f"Uploaded by {who() or 'admin'}")
                    st.success(f"Read {len(parsed['people'])} timetable page(s) — review it at the top of this tab.")
                    rerun()
                except Exception as e:
                    st.error(f"Couldn't read those PDFs: {e}")
        with cM:
            st.markdown("#### Edit minutes by hand")
            st.caption("Creates a new version from the one in force (or blank).")
            cur_grid = vf[2] if vf else {}
            mdf = pd.DataFrame([{"staff_id": s["id"], "Staff": s["name"],
                                 **{DAY_LABELS[i]: int(cur_grid.get(s["id"], [0] * 5)[i]) for i in range(5)}}
                                for s in staff])
            ed_m = st.data_editor(mdf, hide_index=True, key="tt_manual", disabled=["Staff"],
                                  column_config={"staff_id": None,
                                                 **{d: st.column_config.NumberColumn(f"{d} (min)", min_value=0,
                                                                                     max_value=600, step=5)
                                                    for d in DAY_LABELS}})
            meff = st.date_input("Use from", TODAY, format="DD/MM/YYYY", key="tt_manual_eff")
            if st.button("Save as new timetable version"):
                vid = sb().table(T_TTV).insert({"status": "active", "source": "manual",
                                                "source_name": f"Manual edit by {who() or 'admin'}",
                                                "effective_from": meff.isoformat(),
                                                "applied_at": datetime.now().isoformat()}).execute().data[0]["id"]
                rows = []
                for _, r in ed_m.iterrows():
                    for i, d in enumerate(DAY_LABELS):
                        m = int(r[d] or 0)
                        if m > 0:
                            rows.append({"version_id": vid, "staff_name_raw": r["Staff"], "staff_id": int(r["staff_id"]),
                                         "weekday": i, "start_time": "", "end_time": "", "minutes": m,
                                         "label": "NIT (manual)", "counted": True})
                if rows:
                    sb().table(T_TTS).insert(rows).execute()
                refresh()
                st.success("Saved.")
                rerun()

        with st.expander("All timetable versions"):
            vs = load_versions()
            if not vs:
                st.caption("None yet.")
            else:
                st.dataframe(pd.DataFrame([{"ID": v["id"], "Status": v.get("status"),
                                            "Use from": v.get("effective_from") or "",
                                            "Term (PDF)": v.get("term_label") or "", "Source": v.get("source_name") or v.get("source"),
                                            "Added": str(v.get("created_at") or "")[:16].replace("T", " "),
                                            "Notes": v.get("notes") or ""} for v in reversed(vs)]),
                             hide_index=True, **WIDE)
                dv = st.selectbox("Delete a version", ["—"] + [version_name(v) for v in vs], key="tt_del")
                if dv != "—" and st.button("Delete version", type="primary"):
                    vid = int(dv.split("·")[0].strip().lstrip("#"))
                    sb().table(T_TTV).delete().eq("id", vid).execute()
                    refresh()
                    rerun()
                st.caption("Rejected versions are kept so the same PDF isn't re-imported. Deleting one "
                           "lets it be picked up again on the next check.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
TYPE_LABEL = {"missed": "❌ Missed", "additional": "➕ Additional", "absence": "🏠 Absence",
              "override": "✏️ Actual NIT"}
SRC_LABEL = {"manual": "Manual", "bulletin": "📰 Bulletin", "bulletin-edited": "📰 Bulletin (edited)"}

with tabs[4]:
    if TERMS:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            t = term_picker("h_term")
        f_staff = c2.multiselect("Staff", [s["name"] for s in all_staff], key="h_staff")
        f_type = c3.multiselect("Type", list(TYPE_LABEL.values()), key="h_type")
        show_dis = c4.checkbox("Show dismissed", key="h_dis")
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat(), include_dismissed=show_dis)
        if not ents:
            st.info("No entries this term.")
        else:
            df = pd.DataFrame(ents)
            for c, dv in [("source", "manual"), ("covers_nit", True), ("dismissed", False),
                          ("portion", ""), ("day_fraction", 0.0)]:
                if c not in df:
                    df[c] = dv
            df["source"] = df["source"].fillna("manual")
            df["Date"] = df["entry_date"].map(to_date)
            df["Staff"] = df["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
            df["Type"] = df["entry_type"].map(TYPE_LABEL)
            df["Source"] = df["source"].map(lambda s: SRC_LABEL.get(s, s))
            if f_staff:
                df = df[df["Staff"].isin(f_staff)]
            if f_type:
                df = df[df["Type"].isin(f_type)]
            df = df.sort_values(["Date", "Staff"], ascending=[False, True])
            df.insert(0, "Delete", False)
            cols = ["Delete", "Date", "Staff", "Type", "Source", "minutes", "portion", "day_fraction",
                    "covers_nit", "category", "notes", "entered_by", "dismissed", "id"]
            editable = {"Delete", "minutes", "portion", "day_fraction", "covers_nit", "category", "notes", "dismissed"}
            key = f"h_editor_{t['year']}_{t['term']}_{show_dis}"
            ed = st.data_editor(
                df[cols], hide_index=True, **WIDE, key=key,
                disabled=[c for c in cols if c not in editable],
                column_config={
                    "Date": st.column_config.DateColumn(format="ddd DD/MM/YYYY"),
                    "minutes": st.column_config.NumberColumn("Minutes", help="Missed/additional/actual NIT minutes"),
                    "portion": st.column_config.SelectboxColumn(
                        "Portion", options=["", "Full day", "Morning", "Afternoon", "Part day"]),
                    "day_fraction": st.column_config.NumberColumn("Days", min_value=0.0, max_value=1.0, step=0.25),
                    "covers_nit": st.column_config.CheckboxColumn("NIT not received", help="Absence only"),
                    "category": "Reason / leave type", "notes": "Notes", "entered_by": "By",
                    "dismissed": st.column_config.CheckboxColumn("Dismissed", help="Untick to restore an auto entry"),
                    "id": st.column_config.NumberColumn("ID", width="small"),
                })
            orig = df.set_index("id")
            changes, to_del = [], []
            for _, r in ed.iterrows():
                o = orig.loc[r["id"]]
                if bool(r["Delete"]):
                    to_del.append(o)
                    continue
                upd = {}
                for c in ["minutes", "portion", "day_fraction", "covers_nit", "category", "notes", "dismissed"]:
                    nv, ov = r[c], o[c]
                    if (pd.isna(nv) and pd.isna(ov)) or nv == ov:
                        continue
                    upd[c] = (None if pd.isna(nv) else (bool(nv) if c in ("covers_nit", "dismissed") else
                              (float(nv) if c == "day_fraction" else (int(nv) if c == "minutes" else str(nv)))))
                if upd:
                    if o["source"] == "bulletin" and set(upd) - {"dismissed"}:
                        upd["source"] = "bulletin-edited"
                    changes.append((int(r["id"]), upd))
            if changes or to_del:
                st.warning(f"{len(changes)} change(s), {len(to_del)} deletion(s) pending.")
                if st.button("Save changes", type="primary"):
                    for i, upd in changes:
                        sb().table(T_ENTRIES).update(upd).eq("id", i).execute()
                    for o in to_del:
                        if str(o["source"]).startswith("bulletin"):
                            sb().table(T_ENTRIES).update({"dismissed": True}).eq("id", int(o.name)).execute()
                        else:
                            sb().table(T_ENTRIES).delete().eq("id", int(o.name)).execute()
                    refresh()
                    st.success("Saved.")
                    rerun()
            st.caption("Deleting a 📰 Bulletin entry dismisses it so the next sync won't re-add it. "
                       "Editing one locks your version (the sync won't change it).")


# ══════════════════════════════════════════════════════════════════════════════
# TAB — SETUP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown("#### Staff")
    st.caption("NIT minutes now come from the NIT Timetable tab. Working days drive pro-rata entitlement "
               "(e.g. 0.6 FTE → `Mon,Tue,Wed`). Aliases = other names used in the Daily Bulletin, comma separated.")
    base_df = pd.DataFrame(all_staff) if all_staff else pd.DataFrame(
        columns=["id", "name", "fte", "work_days", "aliases", "active", "display_order", "notes"])
    for c, dflt in [("fte", 1.0), ("work_days", "Mon,Tue,Wed,Thu,Fri"), ("aliases", ""),
                    ("active", True), ("display_order", 0), ("notes", "")]:
        if c not in base_df:
            base_df[c] = dflt
    base_df["work_days"] = base_df["work_days"].fillna("Mon,Tue,Wed,Thu,Fri")
    base_df["aliases"] = base_df["aliases"].fillna("")
    base_df = base_df[["id", "name", "fte", "work_days", "aliases", "active", "display_order", "notes"]]
    ed_staff = st.data_editor(
        base_df, num_rows="dynamic", hide_index=True, **WIDE, key="staff_editor",
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("Name", required=True),
            "fte": st.column_config.NumberColumn("FTE", min_value=0.0, max_value=1.0, step=0.1, format="%.1f"),
            "work_days": st.column_config.TextColumn("Working days", help="e.g. Mon,Tue,Wed,Thu,Fri"),
            "aliases": st.column_config.TextColumn("Bulletin aliases"),
            "active": st.column_config.CheckboxColumn("Active", default=True),
            "display_order": st.column_config.NumberColumn("Order", step=1),
            "notes": st.column_config.TextColumn("Notes"),
        })
    if st.button("Save staff", type="primary"):
        kept_ids = set()
        for _, r in ed_staff.iterrows():
            if not str(r.get("name") or "").strip():
                continue
            wd = parse_workdays(r.get("work_days"))
            rec = {"name": str(r["name"]).strip(),
                   "fte": float(r["fte"]) if pd.notna(r["fte"]) else 1.0,
                   "work_days": ",".join(DAY_LABELS[i] for i in wd),
                   "aliases": "" if pd.isna(r["aliases"]) else str(r["aliases"]),
                   "active": bool(r["active"]) if pd.notna(r["active"]) else True,
                   "display_order": int(r["display_order"]) if pd.notna(r["display_order"]) else 0,
                   "notes": "" if pd.isna(r["notes"]) else str(r["notes"])}
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
    st.markdown("#### Entitlement")
    base_min = st.number_input("Weekly NIT entitlement at 1.0 FTE (minutes)", 0, 1000,
                               int(cfg.get("base_minutes_fte1", 250)), step=5,
                               help="Pro-rated by FTE and by days worked.")
    st.caption(f"= {fmt(base_min)} per week · 0.8 FTE → {fmt(base_min * 0.8)} · 0.6 → {fmt(base_min * 0.6)} · "
               f"0.4 → {fmt(base_min * 0.4)} · per day at 1.0 FTE → {fmt(base_min / 5)}")

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

    with st.expander("📰 Daily Bulletin connection"):
        b = cfg.get("bulletin", {})
        b_en = st.toggle("Pull staff absences from the Daily Bulletin", value=bool(b.get("enabled", True)))
        bc1, bc2 = st.columns(2)
        b_table = bc1.text_input("Table", b.get("table", "bulletins"))
        b_date = bc2.text_input("Date column", b.get("date_col", "date"))
        b_cols = bc1.text_input("Absence list column(s), comma separated", ", ".join(b.get("absence_cols", [])))
        b_names = bc2.text_input("Name field(s) inside each row", ", ".join(b.get("name_keys", [])))
        b_reason = bc1.text_input("Reason field(s)", ", ".join(b.get("reason_keys", [])))
        b_pc = bc2.text_input("Program changes column (blank = ignore)", b.get("program_changes_col", "") or "")
        if st.button("Test: show bulletin absences for the last 14 days"):
            found, unm, err = read_bulletin_absences(TODAY - timedelta(days=14), TODAY, staff)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame([{"Date": d.strftime("%a %d/%m"), "Staff": staff_by_id[sid]["name"],
                                            "Portion": f["portion"], "Bulletin text": f["raw"], "Reason": f["reason"]}
                                           for (sid, d), f in sorted(found.items(), key=lambda x: x[0][1])]),
                             hide_index=True, **WIDE)
                if unm:
                    st.caption("Not matched: " + "; ".join(f"{u['date']} {u['name']} ({u['why']})" for u in unm))
                if not found and not unm:
                    st.info("No staff absences found in that period.")

    with st.expander("🗓️ Timetable source"):
        s0 = cfg.get("timetable_source", {})
        modes = ["portal", "url", "off"]
        cur_mode = s0.get("mode", "portal") if s0.get("mode") in modes else "portal"
        t_mode = st.radio("Where does the NIT timetable come from?", modes, index=modes.index(cur_mode),
                          format_func=lambda m: {"portal": "Portal Timetable page (latest uploads)",
                                                 "url": "A PDF web address",
                                                 "off": "Off — upload / edit by hand only"}[m], horizontal=True)
        t_url = st.text_input("PDF web address (only for 'A PDF web address')", s0.get("url", ""))
        sc1, sc2 = st.columns(2)
        t_bucket = sc1.text_input("Storage bucket (blank = find automatically)", s0.get("bucket", ""))
        t_prefix = sc2.text_input("Folder in bucket (optional)", s0.get("prefix", ""))
        t_table = st.text_input("Timetable page's database table", s0.get("table", "timetable_store"))
        if st.button("Show the timetable files the tracker can see"):
            try:
                tf = read_portal_timetable_table({"table": t_table})
                if tf:
                    st.dataframe(pd.DataFrame([{"Current timetable": n, "Size": f"{len(d) // 1024} KB"}
                                               for d, n in tf]), hide_index=True, **WIDE)
                fl = [] if tf else discover_portal_timetables({"bucket": t_bucket, "prefix": t_prefix})
                if fl:
                    st.dataframe(pd.DataFrame([{"File": f"{f['bucket']}/{f['path']}", "Uploaded": f["when"][:16]}
                                               for f in fl]), hide_index=True, **WIDE)
                elif not tf:
                    st.warning("No timetable PDFs found in that table or in file storage.")
            except Exception as e:
                st.error(f"Couldn't list storage: {e}")
        t_auto = st.checkbox("Apply automatically when the PDF's term matches the current or next term",
                             value=bool(s0.get("auto_apply", True)))

    if st.button("Save settings", type="primary"):
        new = dict(cfg)
        new["base_minutes_fte1"] = int(base_min)
        new["terms"] = [{"year": int(r["year"]), "term": int(r["term"]),
                         "start": to_date(r["start"]).isoformat(), "end": to_date(r["end"]).isoformat()}
                        for _, r in ed_terms.iterrows()
                        if pd.notna(r["year"]) and pd.notna(r["term"]) and pd.notna(r["start"]) and pd.notna(r["end"])]
        new["closures"] = [{"date": to_date(r["date"]).isoformat(), "label": str(r["label"] or "Closed")}
                           for _, r in ed_clos.iterrows() if pd.notna(r["date"])]
        for k, txt in [("missed_reasons", mr), ("additional_reasons", ar), ("absence_types", at)]:
            items = [x.strip() for x in txt.splitlines() if x.strip()]
            if items:
                new[k] = items

        def _csv(x):
            return [p.strip() for p in str(x).split(",") if p.strip()]
        new["bulletin"] = {"enabled": bool(b_en), "table": b_table.strip(), "date_col": b_date.strip(),
                           "absence_cols": _csv(b_cols), "name_keys": _csv(b_names),
                           "reason_keys": _csv(b_reason), "program_changes_col": b_pc.strip()}
        new["timetable_source"] = {"mode": t_mode, "url": t_url.strip(), "table": t_table.strip() or "timetable_store",
                                   "bucket": t_bucket.strip(),
                                   "prefix": t_prefix.strip(), "auto_apply": bool(t_auto)}
        save_setting("config", new)
        st.session_state["nit_tt_checked"] = 0
        st.session_state["nit_bul_synced"] = 0
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
        if prev and prev["end"] >= TODAY:
            st.caption(f"⚠️ {term_label(prev)} hasn't finished — carrying forward now counts its remaining "
                       "days as if NIT runs as timetabled.")
        if prev and st.button(f"Carry forward closing balances from {term_label(prev)}"):
            p_ents = load_entries(prev["start"].isoformat(), prev["end"].isoformat())
            p_summ = staff_summary(staff, build_daily(staff, p_ents, prev),
                                   load_opening(prev["year"], prev["term"]))
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
# TAB — EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def build_workbook(t, ents, daily, summ):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    s_out = summ.copy()
    hm = ["Entitled", "Received", "Rostered", "Lost to absence", "Missed", "Additional", "Opening",
          "Rostered / wk", "FTE entitlement / wk"]
    for c in hm:
        s_out[c + " (h:m)"] = s_out[c].apply(fmt)
    s_out["Balance (h:m)"] = s_out["Balance"].apply(lambda v: fmt(v, signed=True))
    s_out = s_out[["Staff", "Status", "Balance (h:m)", "FTE"] + [c + " (h:m)" for c in hm]
                  + ["Absent days", "Roster check", "Balance"]].rename(columns={"Balance": "Balance (min)"})

    wk_bal = daily.groupby(["Staff", "week"])["balance"].sum().unstack(fill_value=0)
    wk_bal = wk_bal.apply(lambda col: col.map(lambda v: fmt(v, signed=True)))
    wk_bal.columns = [f"Week {c}" for c in wk_bal.columns]

    e_df = pd.DataFrame(ents)
    if not e_df.empty:
        e_df["Staff"] = e_df["staff_id"].map(lambda i: staff_by_id.get(i, {}).get("name", "?"))
        e_df["Type"] = e_df["entry_type"].map({"missed": "Missed NIT", "additional": "Additional NIT",
                                               "absence": "Absence", "override": "Actual NIT set"})
        e_df["Source"] = e_df.get("source", pd.Series(["manual"] * len(e_df))).fillna("manual").map(
            lambda s: SRC_LABEL.get(s, s).replace("📰 ", ""))
        e_df = e_df.rename(columns={"entry_date": "Date", "minutes": "Minutes", "portion": "Portion",
                                    "category": "Reason / leave type", "notes": "Notes",
                                    "entered_by": "Entered by", "day_fraction": "Days"})
        e_df = e_df[["Date", "Staff", "Type", "Source", "Minutes", "Portion", "Days",
                     "Reason / leave type", "Notes", "Entered by"]].sort_values(["Date", "Staff"])
    else:
        e_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Minutes"])

    d_out = daily.drop(columns=["staff_id", "override"]).copy()
    d_out["entitlement"] = d_out["entitlement"].round(1)
    d_out["balance"] = d_out["balance"].round(1)
    d_out = d_out.rename(columns={
        "date": "Date", "week": "Week", "rostered": "Timetabled (min)", "entitlement": "Entitled (min)",
        "missed": "Missed (min)", "additional": "Additional (min)", "lost_absence": "Lost to absence (min)",
        "received": "Received (min)", "balance": "Balance (min)", "absent_days": "Absent days",
        "absent_src": "Absence source"})

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
            ws["A2"] = (f"Generated {datetime.now():%d/%m/%Y %H:%M}. Balance = Opening + Received − Entitled "
                        f"(pro rata); negative = NIT owed to the teacher.")
            ws["A2"].font = Font(name="Arial", italic=True, size=9, color="555555")
            for row in ws.iter_rows(min_row=3):
                for c in row:
                    c.font = Font(name="Arial", size=10, bold=(c.row == 3),
                                  color=("FFFFFF" if c.row == 3 else "000000"))
                    if c.row == 3:
                        c.fill = head_fill
                        c.alignment = Alignment(wrap_text=True, vertical="center")
            for i, col in enumerate(ws.iter_cols(min_row=3), start=1):
                width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 9), 38)
            ws.freeze_panes = "B4"
    return buf.getvalue()


with tabs[6]:
    if TERMS and staff:
        t = term_picker("ex_term")
        ents = load_entries(t["start"].isoformat(), t["end"].isoformat())
        upto = TODAY if t["start"] <= TODAY <= t["end"] else None
        daily = build_daily(staff, ents, t, upto=upto)
        summ = staff_summary(staff, daily, load_opening(t["year"], t["term"]))
        st.caption("Term Summary, Weekly Balances, Log Entries and Daily Detail sheets. "
                   + ("Current term: figures are term to date." if upto else ""))
        if st.button("Build Excel report"):
            st.session_state["nit_xlsx"] = build_workbook(t, ents, daily, summ)
            st.session_state["nit_xlsx_name"] = f"NIT_Absence_{t['year']}_Term{t['term']}.xlsx"
        if st.session_state.get("nit_xlsx"):
            st.download_button("⬇️ Download", st.session_state["nit_xlsx"],
                               file_name=st.session_state["nit_xlsx_name"],
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
