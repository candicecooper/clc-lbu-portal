"""
micro_behaviour_utils.py — Micro Behaviours (early-warning signs) for CLC-LBU
==========================================================================

Used by:
  * pages/5_Behaviour_Support.py      — Micro log (in-app + ?mode=microlog),
                                        analysis-page section, signature table
  * pages/16_Safety_risk_plan_builder.py — pulls the student's early-warning
                                        signature into the plan

What a micro behaviour is: a small, observable change from a student's own
baseline that signals they are starting to move outside their Window of
Tolerance, well before anything that would be called an incident.

Decisions (Candice, Nov 2026):
  1. Micro entries appear on the student ANALYSIS page only. They are not in
     the Behaviour Summary report and never count towards incident totals or
     the risk score.
  2. The run-up window is the 60 minutes before each Minor/Critical incident.
  3. A student's early-warning signature feeds the Safety & Risk Plan.

-------------------------------------------------------------------
SUPABASE SETUP — run once in the SQL editor of the BEHAVIOUR SUPPORT project
(the same project as the `incidents` table):

create table if not exists micro_behaviour_codes (
    code        text primary key,
    category    text not null,
    description text not null,
    direction   text not null default 'Either',   -- Hyper | Hypo | Either
    active      boolean not null default true,
    sort_order  int default 0,
    updated_at  timestamptz default now()
);

create table if not exists micro_incidents (
    id               uuid primary key default gen_random_uuid(),
    student_id       text not null,
    occurred_at      timestamptz not null,
    codes            text[] not null,
    other_text       text default '',
    setting          text default '',
    just_before      text default '',
    staff_response   text default '',
    outcome          text not null,                -- Settled | Partly settled | Escalated
    linked_incident  text,
    reported_by      text,
    reported_by_name text default '',
    created_at       timestamptz default now()
);
create index if not exists micro_incidents_student_idx
    on micro_incidents (student_id, occurred_at);

create table if not exists micro_signatures (
    student_id       text primary key,
    student_initials text default '',
    stages           jsonb not null default '[]'::jsonb,
    updated_by       text default '',
    updated_at       timestamptz default now()
);

alter table micro_behaviour_codes enable row level security;
alter table micro_incidents       enable row level security;
alter table micro_signatures      enable row level security;
create policy "micro_codes_all" on micro_behaviour_codes for all using (true) with check (true);
create policy "micro_inc_all"   on micro_incidents       for all using (true) with check (true);
create policy "micro_sig_all"   on micro_signatures      for all using (true) with check (true);
-------------------------------------------------------------------
The code list seeds itself the first time a Leader/ADM opens
"Manage micro behaviour codes" (or you can press "Load the starter list").
Until then the built-in list below is used, so logging works straight away.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

import pandas as pd

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Australia/Adelaide")
except Exception:          # pragma: no cover
    _TZ = None

RUN_UP_MINUTES = 60
OUTCOMES = ["Settled / returned to task", "Partly settled", "Escalated to incident"]
OUTCOME_SHORT = {"Settled / returned to task": "Settled", "Partly settled": "Partly settled",
                 "Escalated to incident": "Escalated"}
DIRECTIONS = ["Hyper", "Hypo", "Either"]
DIR_COLOURS = {"Hyper": "#DC2626", "Hypo": "#2563EB", "Either": "#7C3AED"}

CATEGORIES = {
    "BM": "Body and movement", "VC": "Voice and words", "FA": "Face and eyes",
    "TE": "Task engagement", "AR": "With adults", "PR": "With peers",
    "SE": "Sensory", "RT": "Routine, transitions and arrival",
    "PH": "Physical and self-care", "OB": "Objects and belongings", "OT": "Other",
}

# (code, description, direction) — matches the "CLC-LBU Micro Behaviours:
# Early Indicators Reference" doc. Category comes from the 2-letter prefix.
_STARTER = [
    ("BM01", "Fidgeting more than usual (tapping, leg jiggling, rocking on chair)", "Hyper"),
    ("BM02", "Getting up or wandering without a purpose", "Hyper"),
    ("BM03", "Pacing, or moving to the edge of the room or the doorway", "Hyper"),
    ("BM04", "Clenched fists or jaw, tense shoulders", "Hyper"),
    ("BM05", "Fast or shallow breathing, flushed face", "Hyper"),
    ("BM06", "Slumping, head on desk, body going floppy", "Hypo"),
    ("BM07", "Hood up, hiding face in arms or clothing", "Hypo"),
    ("BM08", "Freezing mid-action or moving very slowly", "Hypo"),
    ("BM09", "Getting under a table or into a small space", "Either"),
    ("BM10", "Self-soothing movement increasing (rocking, rubbing, flapping)", "Either"),
    ("BM11", "Turning body away from the adult or group", "Either"),
    ("VC01", "Volume rising", "Hyper"),
    ("VC02", "Talking faster, harder to interrupt", "Hyper"),
    ("VC03", "Sharp or abrupt tone, one-word answers (\"what\", \"whatever\")", "Hyper"),
    ("VC04", "Muttering or comments under the breath", "Hyper"),
    ("VC05", "Increased silliness, noises, voices or repeated phrases", "Hyper"),
    ("VC06", "More negotiating or questioning (\"why do I have to\", \"how long\")", "Hyper"),
    ("VC07", "Swearing said to no one in particular", "Hyper"),
    ("VC08", "Stops talking, goes quiet", "Hypo"),
    ("VC09", "\"I don't know\", \"I can't\", or a shrug instead of an answer", "Hypo"),
    ("VC10", "Flat or monotone voice", "Hypo"),
    ("VC11", "Putting self down (\"I'm dumb\", \"I'm bad at this\")", "Either"),
    ("VC12", "Talking about going home, leaving or being somewhere else", "Either"),
    ("FA01", "Staring or a fixed glare", "Hyper"),
    ("FA02", "Scanning the room, watching the door or the adults", "Hyper"),
    ("FA03", "Frowning, grimacing or eye-rolling", "Hyper"),
    ("FA04", "Glazed, far-away look, slow to respond to name", "Hypo"),
    ("FA05", "Avoiding eye contact more than usual", "Either"),
    ("FA06", "Teary, watery eyes, chin wobbling", "Either"),
    ("FA07", "Smiling or laughing that doesn't fit the moment", "Either"),
    ("TE01", "Rushing through work, more careless errors", "Hyper"),
    ("TE02", "Rubbing out or scribbling over again and again, screwing up own work", "Hyper"),
    ("TE03", "Refusing help that is usually accepted", "Hyper"),
    ("TE04", "Trying to take control of the task (changing rules, insisting on own way)", "Hyper"),
    ("TE05", "Stopping mid-task and staring", "Hypo"),
    ("TE06", "Delaying the start (sharpening, rearranging, toilet request)", "Either"),
    ("TE07", "Off task sooner than usual", "Either"),
    ("TE08", "Asking for help again and again on things they can do", "Either"),
    ("TE09", "Choosing the easiest option or avoiding a usual favourite", "Either"),
    ("TE10", "Asking for screen or preferred item early or repeatedly", "Either"),
    ("AR01", "Pushing the adult away (\"leave me alone\", \"don't talk to me\")", "Hyper"),
    ("AR02", "Testing a small boundary while watching the adult's reaction", "Hyper"),
    ("AR03", "Arguing about small things or correcting the adult", "Hyper"),
    ("AR04", "Over-compliant, apologising a lot, people-pleasing", "Hypo"),
    ("AR05", "Not responding to name or first instruction (when they usually do)", "Either"),
    ("AR06", "Shadowing an adult, seeking closeness more than usual", "Either"),
    ("AR07", "Rejecting a usually preferred adult, or accepting only one adult", "Either"),
    ("PR01", "Commenting on or correcting peers", "Hyper"),
    ("PR02", "Moving into a peer's space, nudging or poking", "Hyper"),
    ("PR03", "Strong reaction to a peer's noise or look (\"stop looking at me\")", "Hyper"),
    ("PR04", "Over-excited play that escalates quickly", "Hyper"),
    ("PR05", "Choosing to be alone when usually social", "Hypo"),
    ("PR06", "Telling on peers again and again", "Either"),
    ("PR07", "Bringing up conflict from home, the bus or the yard", "Either"),
    ("SE01", "More sensitive to touch or being bumped", "Hyper"),
    ("SE02", "Covering ears, flinching at sounds", "Either"),
    ("SE03", "Shielding eyes, asking for lights off", "Either"),
    ("SE04", "Seeking deep pressure (squeezing, leaning hard, crashing)", "Either"),
    ("SE05", "Chewing or mouthing clothing or objects more than usual", "Either"),
    ("SE06", "Taking off shoes or jumper, saying they're hot or itchy", "Either"),
    ("SE07", "Using or avoiding the calm space more than usual", "Either"),
    ("RT01", "Hovering near exits, checking gates or doors", "Hyper"),
    ("RT02", "Asking again and again what's next, checking the visual timetable", "Either"),
    ("RT03", "Hard to leave an activity, slow to transition", "Either"),
    ("RT04", "Unsettled by a change of staff, room or plan", "Either"),
    ("RT05", "Lingering at the car, gate or bag on arrival", "Either"),
    ("RT06", "Arriving different from usual (late, without usual item, different mood)", "Either"),
    ("RT07", "Repeated requests to leave the room (toilet, office, drink)", "Either"),
    ("PH01", "Saying they're tired, yawning a lot early in the day", "Hypo"),
    ("PH02", "Headache, tummy ache or feeling sick", "Either"),
    ("PH03", "Not eating, or eating far more than usual", "Either"),
    ("PH04", "Says they're hungry or haven't had breakfast", "Either"),
    ("PH05", "Picking at skin, nails or hair, nail biting", "Either"),
    ("PH06", "Toileting changes (more often, accidents, avoiding)", "Either"),
    ("OB01", "Clicking, tapping or fiddling with objects", "Hyper"),
    ("OB02", "Pushing items around or off the desk, dropping things", "Hyper"),
    ("OB03", "Gripping or hoarding a comfort object", "Either"),
    ("OB04", "Packing up early, putting bag on, getting ready to leave", "Either"),
    ("OT00", "Other (describe)", "Either"),
]


def starter_codes() -> list[dict]:
    return [{"code": c, "category": CATEGORIES.get(c[:2], "Other"), "description": d,
             "direction": dr, "active": True, "sort_order": i}
            for i, (c, d, dr) in enumerate(_STARTER)]


def now_local() -> datetime:
    return datetime.now(_TZ) if _TZ else datetime.now()


def session_of(t: time) -> str:
    """Same boundaries as the Behaviour Support analysis page."""
    m = t.hour * 60 + t.minute
    if m < 11 * 60:
        return "Morning"
    if m <= 13 * 60 + 30:
        return "Middle"
    return "Afternoon"


# ──────────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────────
def load_codes(sb, include_inactive: bool = False) -> tuple[list[dict], bool]:
    """Returns (codes, from_db). Falls back to the starter list if the table
    is missing or empty, so the log works before anyone has seeded it."""
    if sb is not None:
        try:
            q = sb.table("micro_behaviour_codes").select("*")
            rows = q.order("sort_order").order("code").execute().data or []
            if rows:
                if not include_inactive:
                    rows = [r for r in rows if r.get("active", True)]
                return rows, True
        except Exception:
            pass
    return starter_codes(), False


def seed_codes(sb) -> int:
    rows = starter_codes()
    sb.table("micro_behaviour_codes").upsert(rows, on_conflict="code").execute()
    return len(rows)


def upsert_code(sb, row: dict) -> None:
    row = dict(row)
    row["updated_at"] = now_local().isoformat()
    sb.table("micro_behaviour_codes").upsert(row, on_conflict="code").execute()


def load_micro(sb, student_id: str) -> list[dict]:
    if sb is None or not student_id:
        return []
    try:
        return (sb.table("micro_incidents").select("*")
                .eq("student_id", str(student_id)).order("occurred_at").execute().data or [])
    except Exception:
        return []


def save_micro(sb, row: dict) -> dict | None:
    """Insert one micro incident. Returns the inserted row or None."""
    data = dict(row)
    data.setdefault("id", str(uuid.uuid4()))
    if isinstance(data.get("occurred_at"), datetime):
        data["occurred_at"] = data["occurred_at"].isoformat()
    res = sb.table("micro_incidents").insert(data).execute()
    return (res.data or [None])[0]


def delete_micro(sb, micro_id: str) -> None:
    sb.table("micro_incidents").delete().eq("id", micro_id).execute()


def load_signature(sb, student_id: str) -> dict | None:
    if sb is None or not student_id:
        return None
    try:
        rows = (sb.table("micro_signatures").select("*")
                .eq("student_id", str(student_id)).limit(1).execute().data or [])
        return rows[0] if rows else None
    except Exception:
        return None


def load_signature_by_initials(sb, initials: str) -> dict | None:
    ini = (initials or "").strip().upper()
    if sb is None or not ini:
        return None
    try:
        rows = (sb.table("micro_signatures").select("*")
                .eq("student_initials", ini).order("updated_at", desc=True)
                .limit(1).execute().data or [])
        return rows[0] if rows else None
    except Exception:
        return None


def save_signature(sb, student_id: str, student_initials: str, stages: list[dict],
                   updated_by: str) -> None:
    sb.table("micro_signatures").upsert({
        "student_id": str(student_id),
        "student_initials": (student_initials or "").strip().upper(),
        "stages": stages,
        "updated_by": updated_by or "",
        "updated_at": now_local().isoformat(),
    }, on_conflict="student_id").execute()


# ──────────────────────────────────────────────────────────────────────────
# ANALYSIS (pure pandas — no Streamlit)
# ──────────────────────────────────────────────────────────────────────────
def _to_local_naive(ts) -> pd.Timestamp | None:
    t = pd.to_datetime(ts, errors="coerce", utc=True)
    if pd.isna(t):
        return None
    if _TZ:
        t = t.tz_convert(_TZ)
    return t.tz_localize(None)


def micro_frame(rows: list[dict], codes: list[dict]) -> pd.DataFrame:
    """One row per (entry, code). Columns: id, dt, date, session, weekday,
    code, description, direction, category, outcome, staff_response, ..."""
    cols = ["id", "dt", "date", "session", "weekday", "code", "description", "direction",
            "category", "outcome", "outcome_short", "staff_response", "setting",
            "just_before", "other_text", "reported_by_name"]
    if not rows:
        return pd.DataFrame(columns=cols)
    lookup = {c["code"]: c for c in codes}
    for c in starter_codes():          # retired codes still label old entries
        lookup.setdefault(c["code"], c)
    out = []
    for r in rows:
        dt = _to_local_naive(r.get("occurred_at"))
        if dt is None:
            continue
        for code in (r.get("codes") or []):
            meta = lookup.get(code, {})
            out.append({
                "id": str(r.get("id")), "dt": dt, "date": dt.date(),
                "session": session_of(dt.time()), "weekday": dt.day_name(),
                "code": code,
                "description": (r.get("other_text") or meta.get("description", code))
                               if code == "OT00" else meta.get("description", code),
                "direction": meta.get("direction", "Either"),
                "category": meta.get("category", CATEGORIES.get(code[:2], "Other")),
                "outcome": r.get("outcome", ""),
                "outcome_short": OUTCOME_SHORT.get(r.get("outcome", ""), r.get("outcome", "")),
                "staff_response": (r.get("staff_response") or "").strip(),
                "setting": r.get("setting", ""), "just_before": r.get("just_before", ""),
                "other_text": r.get("other_text", ""),
                "reported_by_name": r.get("reported_by_name", ""),
            })
    return pd.DataFrame(out, columns=cols).sort_values("dt").reset_index(drop=True)


def code_frequency(mdf: pd.DataFrame) -> pd.DataFrame:
    if mdf.empty:
        return pd.DataFrame(columns=["code", "description", "direction", "count"])
    return (mdf.groupby(["code", "description", "direction"]).size()
            .reset_index(name="count").sort_values(["count", "code"], ascending=[False, True]))


def direction_split(mdf: pd.DataFrame) -> dict:
    counts = mdf["direction"].value_counts().to_dict() if not mdf.empty else {}
    return {d: int(counts.get(d, 0)) for d in DIRECTIONS}


def incident_datetimes(full_df: pd.DataFrame) -> pd.DataFrame:
    """Incident list with a combined local datetime, from the Behaviour
    Support full_df (columns date_parsed, time, incident_type, behaviour_type)."""
    if full_df is None or full_df.empty or "date_parsed" not in full_df.columns:
        return pd.DataFrame(columns=["inc_dt", "incident_type", "behaviour_type"])
    d = pd.to_datetime(full_df["date_parsed"], errors="coerce")
    try:
        if getattr(d.dt, "tz", None) is not None:
            d = d.dt.tz_localize(None)
    except Exception:
        pass
    d = d.dt.normalize()
    raw_t = (full_df["time"] if "time" in full_df.columns
             else pd.Series(["09:00:00"] * len(full_df), index=full_df.index))
    raw_t = raw_t.fillna("09:00:00").astype(str).str.strip().str.slice(0, 8)
    raw_t = raw_t.where(raw_t.str.count(":") >= 2, raw_t + ":00")
    t = pd.to_timedelta(raw_t, errors="coerce").fillna(pd.Timedelta(hours=9))
    out = pd.DataFrame({
        "inc_dt": d + t,
        "incident_type": full_df["incident_type"] if "incident_type" in full_df.columns else "Quick",
        "behaviour_type": full_df["behaviour_type"] if "behaviour_type" in full_df.columns else "",
    }).dropna(subset=["inc_dt"])
    # A Critical (ABCH) record is usually raised from a Quick incident that is
    # already in the list, so drop a Critical row when a Quick row sits within
    # 2 hours of it on the same day — otherwise one incident would count twice.
    quick = out[out["incident_type"] != "Critical"]
    keep = []
    for i, r in out.iterrows():
        if r["incident_type"] == "Critical" and not quick.empty:
            near = quick[(quick["inc_dt"].dt.date == r["inc_dt"].date())
                         & ((quick["inc_dt"] - r["inc_dt"]).abs() <= pd.Timedelta(hours=2))]
            if not near.empty:
                continue
        keep.append(i)
    out = out.loc[keep]
    return out.sort_values("inc_dt").reset_index(drop=True)


def run_up(mdf: pd.DataFrame, incs: pd.DataFrame, window_min: int = RUN_UP_MINUTES) -> dict:
    """For each incident, the micro behaviours logged in the `window_min`
    minutes before it. Returns:
      per_incident: list of {inc_dt, incident_type, behaviour_type, codes, first_lead_min}
      code_counts:  DataFrame code/description/direction/incidents/median_lead_min
      n_incidents, n_with_runup
    """
    res = {"per_incident": [], "code_counts": pd.DataFrame(), "n_incidents": len(incs),
           "n_with_runup": 0}
    if mdf.empty or incs.empty:
        return res
    hits = []
    for _, inc in incs.iterrows():
        start = inc["inc_dt"] - pd.Timedelta(minutes=window_min)
        w = mdf[(mdf["dt"] >= start) & (mdf["dt"] < inc["inc_dt"])]
        if w.empty:
            continue
        lead = (inc["inc_dt"] - w["dt"]).dt.total_seconds() / 60
        res["per_incident"].append({
            "inc_dt": inc["inc_dt"], "incident_type": inc["incident_type"],
            "behaviour_type": inc["behaviour_type"],
            "codes": list(dict.fromkeys(w.sort_values("dt")["code"])),
            "first_lead_min": int(round(lead.max())),
        })
        for code, grp in w.assign(lead=lead).groupby("code"):
            hits.append({"code": code, "description": grp["description"].iloc[0],
                         "direction": grp["direction"].iloc[0],
                         "lead": float(grp["lead"].max())})
    res["n_with_runup"] = len(res["per_incident"])
    if hits:
        h = pd.DataFrame(hits)
        res["code_counts"] = (h.groupby(["code", "description", "direction"])
                              .agg(incidents=("lead", "size"), median_lead_min=("lead", "median"))
                              .reset_index()
                              .sort_values(["incidents", "median_lead_min"], ascending=[False, False]))
        res["code_counts"]["median_lead_min"] = res["code_counts"]["median_lead_min"].round().astype(int)
    return res


def time_pattern(mdf: pd.DataFrame) -> pd.DataFrame:
    """Entries (not codes) by weekday x session."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    sess = ["Morning", "Middle", "Afternoon"]
    if mdf.empty:
        return pd.DataFrame(0, index=sess, columns=days)
    e = mdf.drop_duplicates("id")
    tab = pd.crosstab(e["session"], e["weekday"]).reindex(index=sess, columns=days, fill_value=0)
    return tab


def saves(mdf: pd.DataFrame) -> dict:
    """Saves = entries where the student settled after an early response."""
    if mdf.empty:
        return {"n_entries": 0, "n_saves": 0, "n_escalated": 0, "responses": pd.DataFrame()}
    e = mdf.drop_duplicates("id")
    s = e[e["outcome_short"] == "Settled"]
    resp = (s[s["staff_response"] != ""].groupby("staff_response").size()
            .reset_index(name="times").sort_values("times", ascending=False))
    return {"n_entries": len(e), "n_saves": len(s),
            "n_escalated": int((e["outcome_short"] == "Escalated").sum()), "responses": resp}


def suggest_signature(mdf: pd.DataFrame, ru: dict, max_codes: int = 6) -> list[dict]:
    """Draft a 3-stage signature: pick the student's most frequent codes
    (prefer ones seen in incident run-ups) and order them by how early they
    tend to appear before incidents. Staff then edit it."""
    freq = code_frequency(mdf)
    if freq.empty:
        return []
    lead = {}
    cc = ru.get("code_counts")
    if isinstance(cc, pd.DataFrame) and not cc.empty:
        lead = dict(zip(cc["code"], cc["median_lead_min"]))
    freq = freq[freq["code"] != "OT00"]
    if freq.empty:
        return []
    seen_before = freq[freq["code"].isin(list(lead))]
    if not seen_before.empty:
        # Signs that actually showed up before incidents, earliest first
        top = seen_before.head(max_codes).copy()
        top["lead"] = top["code"].map(lead)
        top = top.sort_values(["lead", "count"], ascending=[False, False])
    else:
        top = freq.head(max_codes).copy()
    stages_n = 3
    rows = top.to_dict("records")
    per = max(1, -(-len(rows) // stages_n))
    names = ["1. First sign", "2. Building", "3. Close to the edge"]
    out = []
    for i in range(stages_n):
        part = rows[i * per:(i + 1) * per]
        if not part:
            continue
        out.append({"stage": names[i],
                    "what_staff_see": "; ".join(r["description"] for r in part),
                    "codes": ", ".join(r["code"] for r in part),
                    "what_works": ""})
    out.append({"stage": "4. Outside the window", "what_staff_see": "Minor or Critical incident",
                "codes": "Incident log", "what_works": "Follow the Safety and Risk Plan"})
    return out


def signature_codes(sig: dict | None) -> list[str]:
    if not sig:
        return []
    out = []
    for st_ in sig.get("stages") or []:
        for c in str(st_.get("codes", "")).replace(";", ",").split(","):
            c = c.strip().upper()
            if len(c) == 4 and c[:2].isalpha() and c[2:].isdigit() and c not in out:
                out.append(c)
    return out


def signature_plan_text(sig: dict | None) -> str:
    """Bullet text for the Safety & Risk Plan's Early Warning Signs section."""
    if not sig or not sig.get("stages"):
        return ""
    lines = []
    for s in sig["stages"]:
        stage = str(s.get("stage", "")).strip()
        see = str(s.get("what_staff_see", "")).strip()
        works = str(s.get("what_works", "")).strip()
        if not (see or works):
            continue
        lines.append(f"### {stage}" if stage else "###")
        if see:
            lines.append(f"• What staff see: {see}")
        if works:
            lines.append(f"• What works: {works}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# STREAMLIT UI
# ──────────────────────────────────────────────────────────────────────────
def _code_label(c: dict) -> str:
    return f"{c['code']} · {c['description']}"


def _pick_codes(codes: list[dict], sig_codes: list[str], key: str) -> list[str]:
    """Tap-chips per category (st.pills where available, else multiselect).
    The student's own signature codes are offered first."""
    import streamlit as st
    by_code = {c["code"]: c for c in codes}
    chosen: list[str] = []
    has_pills = hasattr(st, "pills")

    def _chips(label, opts, k):
        if not opts:
            return []
        if has_pills:
            return st.pills(label, opts, selection_mode="multi", key=k,
                            format_func=lambda x: _code_label(by_code[x])) or []
        return st.multiselect(label, opts, key=k,
                              format_func=lambda x: _code_label(by_code[x]))

    mine = [c for c in sig_codes if c in by_code]
    if mine:
        st.markdown("**⭐ This student's usual signs**")
        chosen += _chips("This student's usual signs", mine, f"{key}_sig")
    cats = [k for k in CATEGORIES if any(c["code"].startswith(k) for c in codes)]
    tabs = st.tabs([CATEGORIES[k] for k in cats])
    for tab, k in zip(tabs, cats):
        with tab:
            opts = [c["code"] for c in codes if c["code"].startswith(k) and c["code"] not in mine]
            chosen += _chips(CATEGORIES[k], opts, f"{key}_{k}")
    return list(dict.fromkeys(chosen))


def render_micro_log(sb, students: list[dict], staff_opts: dict, *, key: str = "ml",
                     preselect_student_id: str | None = None,
                     current_staff_id: str | None = None,
                     write_blocked=None, on_saved=None) -> None:
    """The quick micro-incident form.
    students:   [{"id","name","program"}]
    staff_opts: {staff_id: name}; if current_staff_id is given the picker is hidden.
    write_blocked: optional callable() -> bool (Behaviour Support's view-only guard).
    """
    import streamlit as st

    just = st.session_state.get(f"{key}_saved")
    if just:
        st.success(f"✅ Micro behaviour logged for **{just['student']}** at {just['time']}: "
                   f"{just['codes']} · {just['outcome']}")
        if st.button("➕ Log another micro behaviour", type="primary", key=f"{key}_again",
                     use_container_width=True):
            st.session_state[f"{key}_saved"] = None
            st.session_state[f"{key}_nonce"] = st.session_state.get(f"{key}_nonce", 0) + 1
            st.rerun()
        return

    if not students:
        st.warning("No active students found.")
        return
    nonce = st.session_state.get(f"{key}_nonce", 0)
    k = f"{key}_{nonce}"
    codes, _ = load_codes(sb)

    stu_opts = {s["id"]: f"{s['name']}  ({s.get('program', '')})" for s in students}
    ids = list(stu_opts)
    c1, c2 = st.columns(2)
    with c1:
        idx = ids.index(preselect_student_id) if preselect_student_id in ids else 0
        sid = st.selectbox("👤 Student *", ids, index=idx, format_func=lambda x: stu_opts[x],
                           key=f"{k}_stu")
    with c2:
        if current_staff_id and current_staff_id in staff_opts:
            staff_id = current_staff_id
            st.text_input("🙋 Logged by", value=staff_opts[staff_id], disabled=True, key=f"{k}_by_ro")
        elif staff_opts:
            staff_id = st.selectbox("🙋 Your name *", list(staff_opts),
                                    format_func=lambda x: staff_opts[x], key=f"{k}_by")
        else:
            staff_id = None
            st.warning("No staff list available.")

    nowl = now_local()
    d1, d2 = st.columns(2)
    with d1:
        d = st.date_input("📅 Date *", value=nowl.date(), key=f"{k}_date", format="DD/MM/YYYY")
    with d2:
        t = st.time_input("🕐 Time it started *", value=nowl.time().replace(second=0, microsecond=0),
                          step=60, key=f"{k}_time")

    st.markdown("**👀 What did you see or hear?** (tap one or more)")
    sig = load_signature(sb, sid)
    picked = _pick_codes(codes, signature_codes(sig), f"{k}_codes")
    other_text = ""
    if "OT00" in picked:
        other_text = st.text_input("Describe the 'Other' behaviour *", key=f"{k}_other")
    if picked:
        st.caption("Selected: " + ", ".join(picked))

    s1, s2 = st.columns(2)
    with s1:
        setting = st.text_input("📍 Setting / activity", placeholder="Literacy, independent writing",
                                key=f"{k}_setting")
    with s2:
        just_before = st.text_input("⏪ Just before", placeholder="Asked to fix a spelling error",
                                    key=f"{k}_before")
    response = st.text_input("🤝 What you did", placeholder="Offered a 2-minute movement break",
                             key=f"{k}_resp")
    outcome = st.radio("➡️ What happened next *", OUTCOMES, horizontal=True, index=None,
                       key=f"{k}_outcome")
    if outcome == "Escalated to incident":
        st.info("Remember to log the incident itself (Quick Incident Log or ABCH form) — "
                "this micro entry will then show in that incident's run-up.")

    if st.button("💾 Save micro behaviour", type="primary", use_container_width=True,
                 key=f"{k}_save"):
        errs = []
        if not picked:
            errs.append("Pick at least one behaviour.")
        if "OT00" in picked and not other_text.strip():
            errs.append("Describe the 'Other' behaviour.")
        if not outcome:
            errs.append("Choose what happened next.")
        if not staff_id:
            errs.append("Choose your name.")
        if errs:
            for e in errs:
                st.error(e)
            return
        if write_blocked and write_blocked():
            return
        occurred = datetime.combine(d, t)
        if _TZ:
            occurred = occurred.replace(tzinfo=_TZ)
        try:
            saved = save_micro(sb, {
                "student_id": str(sid), "occurred_at": occurred, "codes": picked,
                "other_text": other_text.strip(), "setting": setting.strip(),
                "just_before": just_before.strip(), "staff_response": response.strip(),
                "outcome": outcome, "reported_by": str(staff_id),
                "reported_by_name": staff_opts.get(staff_id, ""),
            })
        except Exception as e:
            saved = None
            st.error(f"Could not save: {e}")
        if saved:
            st.session_state[f"{key}_saved"] = {
                "student": stu_opts[sid].split("  (")[0], "time": t.strftime("%I:%M %p").lstrip("0"),
                "codes": ", ".join(picked), "outcome": OUTCOME_SHORT[outcome]}
            if on_saved:
                on_saved()
            st.rerun()
        elif saved is None:
            st.error("The save didn't go through — nothing was stored. Please try again.")


def render_code_manager(sb, key: str = "mcm") -> None:
    """Leader/ADM: add, edit, retire codes."""
    import streamlit as st
    rows, from_db = load_codes(sb, include_inactive=True)
    if not from_db:
        st.info("The code list hasn't been loaded into the database yet, so the built-in "
                "starter list (78 codes + Other) is being used.")
        if st.button("📥 Load the starter list into the database", key=f"{key}_seed"):
            try:
                n = seed_codes(sb)
                st.success(f"Loaded {n} codes.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't load the list (has the SQL setup been run?): {e}")
        return
    df = pd.DataFrame(rows)[["code", "category", "description", "direction", "active", "sort_order"]]
    st.caption("Edit descriptions or directions, untick **active** to retire a code (old entries "
               "keep their label), or add a row for a new code. New codes: 2-letter category + "
               "2 digits, e.g. BM12.")
    edited = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"{key}_ed",
        column_config={
            "code": st.column_config.TextColumn("Code", max_chars=4, required=True),
            "category": st.column_config.SelectboxColumn("Category",
                                                         options=list(CATEGORIES.values()), required=True),
            "description": st.column_config.TextColumn("What you see / hear", required=True, width="large"),
            "direction": st.column_config.SelectboxColumn("Direction", options=DIRECTIONS, required=True),
            "active": st.column_config.CheckboxColumn("Active"),
            "sort_order": st.column_config.NumberColumn("Order", step=1),
        })
    if st.button("💾 Save code list", type="primary", key=f"{key}_save"):
        n, bad = 0, []
        for r in edited.to_dict("records"):
            code = str(r.get("code") or "").strip().upper()
            if not (len(code) == 4 and code[:2].isalpha() and code[2:].isdigit()):
                if code:
                    bad.append(code)
                continue
            try:
                upsert_code(sb, {"code": code, "category": r.get("category") or CATEGORIES.get(code[:2], "Other"),
                                 "description": str(r.get("description") or "").strip() or code,
                                 "direction": r.get("direction") or "Either",
                                 "active": bool(r.get("active", True)),
                                 "sort_order": int(r.get("sort_order") or 999)})
                n += 1
            except Exception as e:
                st.error(f"{code}: {e}")
        if bad:
            st.warning("Skipped (codes must be 2 letters + 2 digits): " + ", ".join(bad))
        st.success(f"Saved {n} codes.")


def render_micro_analysis_section(sb, student: dict, full_df: pd.DataFrame, *,
                                  student_initials: str = "", can_edit: bool = False,
                                  can_delete: bool = False, editor_name: str = "",
                                  write_blocked=None, key: str = "mas") -> None:
    """The Micro Behaviours section of the student analysis page.
    Never touches incident totals or the risk score."""
    import streamlit as st
    import plotly.graph_objects as go

    sid = str(student.get("id"))
    st.markdown("### 🌡️ Micro Behaviours — Early Warning Signs")
    st.caption(f"Small changes logged before anything became an incident. Shown here only — not in "
               f"the Behaviour Summary report, incident totals or the risk score. Run-up window: "
               f"{RUN_UP_MINUTES} minutes before each incident.")

    codes, _ = load_codes(sb, include_inactive=True)
    rows = load_micro(sb, sid)
    mdf = micro_frame(rows, codes)
    sig = load_signature(sb, sid)

    if mdf.empty:
        st.info("No micro behaviours logged for this student yet. Use **🌡️ Micro** on the students "
                "list (or the Micro Log tile) to start building their early-warning picture.")
    else:
        sv = saves(mdf)
        incs = incident_datetimes(full_df)
        ru = run_up(mdf, incs)
        ds = direction_split(mdf)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Micro entries", sv["n_entries"])
        m2.metric("Saves (settled)", sv["n_saves"],
                  help="Entries where the student settled after an early staff response")
        m3.metric("Escalated", sv["n_escalated"])
        pct = f"{round(ru['n_with_runup'] / ru['n_incidents'] * 100)}%" if ru["n_incidents"] else "—"
        m4.metric("Incidents with a logged run-up", pct,
                  help=f"Incidents with at least one micro behaviour logged in the "
                       f"{RUN_UP_MINUTES} minutes before")

        # Most frequent + direction
        freq = code_frequency(mdf).head(10)
        cA, cB = st.columns([3, 1])
        with cA:
            st.markdown("**Most frequent micro behaviours**")
            fig = go.Figure(go.Bar(
                x=freq["count"][::-1], y=(freq["code"] + " · " + freq["description"].str.slice(0, 48))[::-1],
                orientation="h", marker_color=[DIR_COLOURS.get(d, "#64748B") for d in freq["direction"][::-1]],
                hovertemplate="%{y}<br>%{x} times<extra></extra>"))
            fig.update_layout(height=max(220, 34 * len(freq) + 60), margin=dict(l=10, r=10, t=10, b=30),
                              xaxis_title="Times logged", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True, key=f"{key}_freq")
            st.caption("Bar colour = direction: red Hyper (heading up), blue Hypo (heading down), "
                       "purple Either.")
        with cB:
            st.markdown("**Direction of drift**")
            tot = sum(ds.values()) or 1
            for dname, label in [("Hyper", "Hyper ↑"), ("Hypo", "Hypo ↓"), ("Either", "Either")]:
                st.markdown(
                    f"<div style='border-left:4px solid {DIR_COLOURS[dname]};padding:.3rem .6rem;"
                    f"margin-bottom:.4rem;background:#f8fafc;border-radius:0 6px 6px 0;'>"
                    f"<b>{label}</b><br><span style='font-size:1.3rem;font-weight:700;'>"
                    f"{round(ds[dname] / tot * 100)}%</span> <span style='color:#64748b;"
                    f"font-size:.8rem;'>({ds[dname]})</span></div>", unsafe_allow_html=True)
            main = max(ds, key=ds.get)
            if ds["Hyper"] and ds["Hypo"] and min(ds["Hyper"], ds["Hypo"]) / max(ds["Hyper"], ds["Hypo"]) >= 0.5:
                st.caption("Mix of Hyper and Hypo signs — check whether this student goes quiet "
                           "before they escalate.")
            elif main == "Hypo":
                st.caption("Mostly Hypo — quiet signs that are easy to miss in a busy room.")

        # Run-up
        st.markdown(f"**The run-up: micro behaviours in the {RUN_UP_MINUTES} minutes before incidents**")
        if not ru["n_incidents"]:
            st.caption("No incidents on file yet, so there's no run-up to compare.")
        elif not ru["n_with_runup"]:
            st.caption(f"None of this student's {ru['n_incidents']} incident(s) had a micro behaviour "
                       f"logged in the {RUN_UP_MINUTES} minutes before.")
        else:
            cc = ru["code_counts"].rename(columns={
                "code": "Code", "description": "Micro behaviour", "direction": "Direction",
                "incidents": "Incidents it came before", "median_lead_min": "Typical minutes before"})
            st.dataframe(cc, hide_index=True, use_container_width=True)
            with st.expander(f"Each incident's run-up ({ru['n_with_runup']})"):
                per = pd.DataFrame([{
                    "Incident": p["inc_dt"].strftime("%a %d/%m/%Y %I:%M %p"),
                    "Type": p["incident_type"], "Behaviour": p["behaviour_type"],
                    "Micro behaviours (in order)": " → ".join(p["codes"]),
                    "First sign (min before)": p["first_lead_min"],
                } for p in sorted(ru["per_incident"], key=lambda x: x["inc_dt"], reverse=True)])
                st.dataframe(per, hide_index=True, use_container_width=True)

        # When
        st.markdown("**When micro behaviours are logged**")
        tp = time_pattern(mdf)
        hfig = go.Figure(go.Heatmap(z=tp.values, x=[c[:3] for c in tp.columns], y=list(tp.index),
                                    colorscale=[[0, "#F1F5F9"], [1, "#1A7A7A"]], showscale=False,
                                    text=tp.values, texttemplate="%{text}",
                                    hovertemplate="%{y}, %{x}: %{z} entries<extra></extra>"))
        hfig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10),
                           yaxis=dict(autorange="reversed"))
        st.plotly_chart(hfig, use_container_width=True, key=f"{key}_heat")
        st.caption("Morning before 11:00 · Middle 11:00–1:30 · Afternoon after 1:30. "
                   "Compare with the Scatter Plot Tracker.")

        # Saves
        st.markdown("**Saves — what staff did when the student settled**")
        if sv["responses"].empty:
            st.caption("No settled entries with a staff response recorded yet.")
        else:
            st.dataframe(sv["responses"].rename(columns={"staff_response": "Staff response",
                                                         "times": "Times it worked"}).head(10),
                         hide_index=True, use_container_width=True)

        with st.expander(f"All micro entries ({sv['n_entries']})"):
            e = mdf.groupby("id").agg(dt=("dt", "first"), codes=("code", lambda s: ", ".join(s)),
                                      outcome=("outcome_short", "first"),
                                      response=("staff_response", "first"),
                                      setting=("setting", "first"), before=("just_before", "first"),
                                      by=("reported_by_name", "first")).reset_index()
            e = e.sort_values("dt", ascending=False)
            show = e.assign(When=e["dt"].dt.strftime("%a %d/%m/%Y %I:%M %p"))[
                ["When", "codes", "setting", "before", "response", "outcome", "by"]].rename(columns={
                    "codes": "Codes", "setting": "Setting", "before": "Just before",
                    "response": "Staff response", "outcome": "Next", "by": "Logged by"})
            st.dataframe(show, hide_index=True, use_container_width=True)
            if can_delete:
                opts = {r["id"]: f"{r['dt'].strftime('%d/%m %I:%M %p')} · {r['codes']}"
                        for r in e.to_dict("records")}
                dsel = st.selectbox("Delete an entry logged in error", [""] + list(opts),
                                    format_func=lambda x: opts.get(x, "—"), key=f"{key}_del")
                if dsel and st.button("🗑️ Delete this entry", key=f"{key}_delbtn"):
                    if not (write_blocked and write_blocked("delete a micro entry")):
                        try:
                            delete_micro(sb, dsel)
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Couldn't delete: {ex}")

    # Signature
    st.markdown("#### 🧭 Early-warning signature")
    st.caption("The student's own short, ordered list of signs and what works at each stage. "
               "It feeds the Early Warning Signs section of their Safety & Risk Plan. "
               "Review it each term.")
    if sig and sig.get("updated_at"):
        when = _to_local_naive(sig["updated_at"])
        st.caption(f"Last updated {when.strftime('%d/%m/%Y') if when is not None else ''}"
                   f"{' by ' + sig['updated_by'] if sig.get('updated_by') else ''}.")
    stages = (sig or {}).get("stages") or []
    sig_cols = ["stage", "what_staff_see", "codes", "what_works"]
    if not stages and not mdf.empty:
        draft = suggest_signature(mdf, run_up(mdf, incident_datetimes(full_df)))
        if draft:
            st.info("Draft below is built from the logged data (most frequent signs, ordered by how "
                    "early they show up before incidents). Check it with the team, fill in "
                    "**What works**, then save.")
            stages = draft
    if not stages:
        stages = [{"stage": n, "what_staff_see": "", "codes": "", "what_works": ""}
                  for n in ["1. First sign", "2. Building", "3. Close to the edge"]] + [
                  {"stage": "4. Outside the window", "what_staff_see": "Minor or Critical incident",
                   "codes": "Incident log", "what_works": "Follow the Safety and Risk Plan"}]
    sdf = pd.DataFrame(stages).reindex(columns=sig_cols).fillna("")
    if can_edit:
        ed = st.data_editor(sdf, num_rows="dynamic", hide_index=True, use_container_width=True,
                            key=f"{key}_sig_{sid}", column_config={
                                "stage": st.column_config.TextColumn("Stage"),
                                "what_staff_see": st.column_config.TextColumn("What staff see", width="large"),
                                "codes": st.column_config.TextColumn("Codes"),
                                "what_works": st.column_config.TextColumn("What works", width="large")})
        if st.button("💾 Save signature", type="primary", key=f"{key}_sigsave"):
            if not (write_blocked and write_blocked("save the signature")):
                clean = [{k2: str(v or "").strip() for k2, v in r.items()}
                         for r in ed.to_dict("records")
                         if any(str(v or "").strip() for v in r.values())]
                try:
                    save_signature(sb, sid, student_initials, clean, editor_name)
                    st.success("Signature saved — it will appear in this student's next Safety & Risk Plan.")
                except Exception as ex:
                    st.error(f"Couldn't save the signature (has the SQL setup been run?): {ex}")
    else:
        st.dataframe(sdf.rename(columns={"stage": "Stage", "what_staff_see": "What staff see",
                                         "codes": "Codes", "what_works": "What works"}),
                     hide_index=True, use_container_width=True)
        st.caption("🔒 Log in with your own account to edit the signature.")
