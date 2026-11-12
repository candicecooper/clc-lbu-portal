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
    response_source  text default '',              -- suggested | worked_before | other
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

-- If you ran the setup before the suggested-response update (Nov 2026), also run:
alter table micro_incidents add column if not exists response_source text default '';
-------------------------------------------------------------------
The code list seeds itself the first time a Leader/ADM opens
"Manage micro behaviour codes" (or you can press "Load the starter list").
Until then the built-in list below is used, so logging works straight away.
"""

from __future__ import annotations

import html as _html
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
# Colours match the site's Window of Tolerance Creator / Behaviour Support WoT zones
DIR_COLOURS = {"Hyper": "#B9761A", "Hypo": "#2A6693", "Either": "#7C3AED"}

# Micro behaviours sit in the WoT "Coping Mechanisms" bands: the student is still
# coping (still in their window) but showing they are moving toward its edge.
WOT_BANDS = [
    ("hyper", "Mobilisation — Hyperarousal", "Outside the window: fight / flight. This is an incident.", "#AF3A2C"),
    ("copingup", "Coping — moving toward Hyperarousal", "Still coping, but arousal is rising.", "#B9761A"),
    ("window", "Window of Tolerance", "Regulated, ready to learn and connect.", "#2E7D32"),
    ("copingdown", "Coping — moving toward Hypoarousal", "Still coping, but starting to shut down.", "#2A6693"),
    ("hypo", "Immobilisation — Hypoarousal", "Outside the window: freeze / shut down. This is an incident.", "#3C4C6B"),
]
WOT_FOR_DIRECTION = {"Hyper": "copingup", "Hypo": "copingdown"}
WOT_SHORT = {"Hyper": "Coping ↑ toward Hyperarousal", "Hypo": "Coping ↓ toward Hypoarousal",
             "Either": "Coping (either way)"}
WOT_EXPLAINER = ("Micro behaviours are **coping** signs. The student is still inside their Window "
                 "of Tolerance and still coping, but is showing us they are moving toward the edge. "
                 "Responding now helps them stay in the window, before it becomes an incident.")


def wot_strip_html(directions: list[str] | None = None, compact: bool = False) -> str:
    """Five-band Window of Tolerance strip (same zones and colours as the WoT
    Creator). Highlights the coping band(s) the given directions point to."""
    directions = directions or []
    active = {WOT_FOR_DIRECTION[d] for d in directions if d in WOT_FOR_DIRECTION}
    if "Either" in directions and not active:
        active = {"copingup", "copingdown"}
    rows = []
    for zid, label, desc, col in WOT_BANDS:
        on = zid in active
        is_window = zid == "window"
        bg = col if on else ("#E8F5E9" if is_window else "#F1F5F9")
        fg = "#FFFFFF" if on else (col if is_window else "#64748B")
        border = f"2px solid {col}" if (on or is_window) else "1px solid #E2E8F0"
        marker = " ◀ the signs you picked" if on else ""
        sub = "" if compact else f"<div style='font-size:.72rem;opacity:.9;'>{desc}</div>"
        rows.append(
            f"<div style='background:{bg};color:{fg};border:{border};border-radius:6px;"
            f"padding:{'.18rem' if compact else '.3rem'} .6rem;margin:2px 0;'>"
            f"<div style='font-weight:{700 if (on or is_window) else 500};font-size:.82rem;'>"
            f"{label}{marker}</div>{sub}</div>")
    return "<div style='max-width:520px;margin:.2rem 0 .6rem;'>" + "".join(rows) + "</div>"


def wot_position_sentence(directions: list[str]) -> str:
    h, l = directions.count("Hyper"), directions.count("Hypo")
    if h and l:
        return ("These signs point both ways. Some students go quiet before they escalate, so "
                "watch for a swing from Hypo to Hyper.")
    if h:
        return "The student is still coping, but their arousal is rising toward Mobilisation (hyperarousal)."
    if l:
        return "The student is still coping, but is starting to move toward Immobilisation (hypoarousal)."
    return "The student is still coping. Check their profile for which way these signs usually go."

CATEGORIES = {
    "BM": "Body and movement", "VC": "Voice and words", "FA": "Face and eyes",
    "TE": "Task engagement", "AR": "With adults", "PR": "With peers",
    "SE": "Sensory", "RT": "Routine, transitions and arrival",
    "PH": "Physical and self-care", "OB": "Objects and belongings", "OT": "Other",
}

# (code, description, direction) — matches the "CLC-LBU Micro Behaviours:
# Early Indicators Reference" doc. Category comes from the 2-letter prefix.
_STARTER = [
    ('BM12', "Tapping more than usual", 'Hyper'),
    ('BM13', "Leg jiggling", 'Hyper'),
    ('BM14', "Rocking on chair", 'Hyper'),
    ('BM02', "Getting up or wandering without a purpose", 'Hyper'),
    ('BM15', "Pacing", 'Hyper'),
    ('BM16', "Moving to the edge of the room or the doorway", 'Hyper'),
    ('BM17', "Clenched fists", 'Hyper'),
    ('BM18', "Clenched jaw", 'Hyper'),
    ('BM19', "Tense or raised shoulders", 'Hyper'),
    ('BM20', "Fast or shallow breathing", 'Hyper'),
    ('BM21', "Flushed face", 'Hyper'),
    ('BM22', "Slumping in chair", 'Hypo'),
    ('BM23', "Head down on desk", 'Hypo'),
    ('BM24', "Body going floppy", 'Hypo'),
    ('BM25', "Hood up", 'Hypo'),
    ('BM26', "Hiding face in arms or clothing", 'Hypo'),
    ('BM08', "Freezing mid-action or moving very slowly", 'Hypo'),
    ('BM09', "Getting under a table or into a small space", 'Either'),
    ('BM27', "Rocking to self-soothe", 'Either'),
    ('BM28', "Rubbing hands or body", 'Either'),
    ('BM29', "Hand flapping", 'Either'),
    ('BM11', "Turning body away from the adult or group", 'Either'),
    ('VC01', "Volume rising", 'Hyper'),
    ('VC13', "Talking faster", 'Hyper'),
    ('VC14', "Harder to interrupt or redirect", 'Hyper'),
    ('VC15', "Sharp or abrupt tone", 'Hyper'),
    ('VC16', "One-word answers (\"what\" or \"whatever\")", 'Hyper'),
    ('VC04', "Muttering or comments under the breath", 'Hyper'),
    ('VC17', "Increased silliness", 'Hyper'),
    ('VC18', "Making noises", 'Hyper'),
    ('VC19', "Putting on voices", 'Hyper'),
    ('VC20', "Repeating phrases", 'Hyper'),
    ('VC21', "More negotiating", 'Hyper'),
    ('VC22', "More questioning (\"why do I have to?\")", 'Hyper'),
    ('VC07', "Swearing said to no one in particular", 'Hyper'),
    ('VC08', "Goes quiet or stops talking", 'Hypo'),
    ('VC23', "Says \"I don't know\"", 'Hypo'),
    ('VC24', "Says \"I can't\"", 'Hypo'),
    ('VC25', "Shrugs instead of answering", 'Hypo'),
    ('VC10', "Flat or monotone voice", 'Hypo'),
    ('VC11', "Putting self down (e.g. \"I'm dumb\")", 'Either'),
    ('VC12', "Talking about going home or leaving", 'Either'),
    ('FA01', "Staring or a fixed glare", 'Hyper'),
    ('FA08', "Scanning the room", 'Hyper'),
    ('FA09', "Watching the door or the adults", 'Hyper'),
    ('FA10', "Frowning", 'Hyper'),
    ('FA11', "Grimacing", 'Hyper'),
    ('FA12', "Eye-rolling", 'Hyper'),
    ('FA13', "Glazed or far-away look", 'Hypo'),
    ('FA14', "Slow to respond to name", 'Hypo'),
    ('FA05', "Avoiding eye contact more than usual", 'Either'),
    ('FA15', "Teary or watery eyes", 'Either'),
    ('FA16', "Chin wobbling", 'Either'),
    ('FA07', "Smiling or laughing that doesn't fit the moment", 'Either'),
    ('TE11', "Rushing through work", 'Hyper'),
    ('TE12', "More careless errors than usual", 'Hyper'),
    ('TE13', "Rubbing out again and again", 'Hyper'),
    ('TE14', "Scribbling over own work", 'Hyper'),
    ('TE15', "Screwing up or ripping own work", 'Hyper'),
    ('TE03', "Refusing help that is usually accepted", 'Hyper'),
    ('TE16', "Changing the rules of the task", 'Hyper'),
    ('TE17', "Insisting on doing it their own way", 'Hyper'),
    ('TE05', "Stopping mid-task and staring", 'Hypo'),
    ('TE18', "Sharpening pencils to delay starting", 'Either'),
    ('TE19', "Rearranging things to delay starting", 'Either'),
    ('TE20', "Asking for the toilet at the start of a task", 'Either'),
    ('TE07', "Off task sooner than usual", 'Either'),
    ('TE08', "Asking for help again and again on things they can do", 'Either'),
    ('TE09', "Choosing the easiest option or avoiding a usual favourite", 'Either'),
    ('TE10', "Asking for screen or preferred item early or repeatedly", 'Either'),
    ('AR01', "Pushing the adult away (\"leave me alone\")", 'Hyper'),
    ('AR02', "Testing a small boundary while watching the adult's reaction", 'Hyper'),
    ('AR03', "Arguing about small things or correcting the adult", 'Hyper'),
    ('AR08', "Over-compliant", 'Hypo'),
    ('AR09', "Apologising a lot", 'Hypo'),
    ('AR10', "People-pleasing", 'Hypo'),
    ('AR05', "Not responding to name or first instruction (when they usually do)", 'Either'),
    ('AR11', "Shadowing an adult", 'Either'),
    ('AR12', "Seeking closeness more than usual", 'Either'),
    ('AR13', "Rejecting a usually preferred adult", 'Either'),
    ('AR14', "Accepting only one adult", 'Either'),
    ('PR01', "Commenting on or correcting peers", 'Hyper'),
    ('PR08', "Moving into a peer's space", 'Hyper'),
    ('PR09', "Nudging or poking a peer", 'Hyper'),
    ('PR03', "Strong reaction to a peer's noise or look (\"stop looking at me\")", 'Hyper'),
    ('PR04', "Over-excited play that escalates quickly", 'Hyper'),
    ('PR05', "Choosing to be alone when usually social", 'Hypo'),
    ('PR06', "Telling on peers again and again", 'Either'),
    ('PR10', "Bringing up conflict from home", 'Either'),
    ('PR11', "Bringing up conflict from the bus or taxi", 'Either'),
    ('PR12', "Bringing up conflict from the yard", 'Either'),
    ('SE01', "More sensitive to touch or being bumped", 'Hyper'),
    ('SE08', "Covering ears", 'Either'),
    ('SE09', "Flinching at sounds", 'Either'),
    ('SE10', "Shielding eyes", 'Either'),
    ('SE11', "Asking for lights off", 'Either'),
    ('SE12', "Squeezing people or objects (deep pressure)", 'Either'),
    ('SE13', "Leaning hard on people or furniture", 'Either'),
    ('SE14', "Crashing into things or the floor", 'Either'),
    ('SE05', "Chewing or mouthing clothing or objects more than usual", 'Either'),
    ('SE15', "Taking off shoes or jumper", 'Either'),
    ('SE16', "Saying they're hot or itchy", 'Either'),
    ('SE07', "Using or avoiding the calm space more than usual", 'Either'),
    ('RT08', "Hovering near exits", 'Hyper'),
    ('RT09', "Checking gates or doors", 'Hyper'),
    ('RT10', "Asking again and again what's next", 'Either'),
    ('RT11', "Checking the visual timetable again and again", 'Either'),
    ('RT12', "Hard to leave an activity", 'Either'),
    ('RT13', "Slow to transition", 'Either'),
    ('RT14', "Unsettled by a change of staff", 'Either'),
    ('RT15', "Unsettled by a change of room", 'Either'),
    ('RT16', "Unsettled by a change of plan", 'Either'),
    ('RT17', "Lingering at the car on arrival", 'Either'),
    ('RT18', "Lingering at the gate on arrival", 'Either'),
    ('RT19', "Lingering at their bag on arrival", 'Either'),
    ('RT20', "Arriving late", 'Either'),
    ('RT21', "Arriving without their usual item", 'Either'),
    ('RT22', "Arriving in a different mood from usual", 'Either'),
    ('RT23', "Asking for the toilet again and again", 'Either'),
    ('RT24', "Asking to go to the office again and again", 'Either'),
    ('RT25', "Asking for a drink again and again", 'Either'),
    ('PH07', "Saying they're tired", 'Hypo'),
    ('PH08', "Yawning a lot early in the day", 'Hypo'),
    ('PH09', "Says they have a headache", 'Either'),
    ('PH10', "Says they have a tummy ache", 'Either'),
    ('PH11', "Says they feel sick", 'Either'),
    ('PH12', "Not eating", 'Either'),
    ('PH13', "Eating far more than usual", 'Either'),
    ('PH04', "Says they're hungry or haven't had breakfast", 'Either'),
    ('PH14', "Picking at skin", 'Either'),
    ('PH15', "Picking or biting nails", 'Either'),
    ('PH16', "Pulling or twisting hair", 'Either'),
    ('PH17', "Going to the toilet more often", 'Either'),
    ('PH18', "Toileting accidents", 'Either'),
    ('PH19', "Avoiding the toilet", 'Either'),
    ('OB05', "Clicking pens or objects", 'Hyper'),
    ('OB06', "Tapping objects", 'Hyper'),
    ('OB07', "Fiddling with objects", 'Hyper'),
    ('OB08', "Pushing items around or off the desk", 'Hyper'),
    ('OB09', "Dropping things", 'Hyper'),
    ('OB03', "Gripping or hoarding a comfort object", 'Either'),
    ('OB10', "Packing up early", 'Either'),
    ('OB11', "Putting their bag on early", 'Either'),
    ('OT00', "Other (describe)", 'Either'),
]

# Combined codes from the first version (Nov 2026), retired when each was split into
# single behaviours. Kept so entries already logged with them keep their label.
LEGACY_CODES = {
    'BM01': ("Fidgeting more than usual (tapping, leg jiggling, rocking on chair)", 'Hyper'),
    'BM03': ("Pacing, or moving to the edge of the room or the doorway", 'Hyper'),
    'BM04': ("Clenched fists or jaw, tense shoulders", 'Hyper'),
    'BM05': ("Fast or shallow breathing, flushed face", 'Hyper'),
    'BM06': ("Slumping, head on desk, body going floppy", 'Hypo'),
    'BM07': ("Hood up, hiding face in arms or clothing", 'Hypo'),
    'BM10': ("Self-soothing movement increasing (rocking, rubbing, flapping)", 'Either'),
    'VC02': ("Talking faster, harder to interrupt", 'Hyper'),
    'VC03': ("Sharp or abrupt tone, one-word answers (\"what\", \"whatever\")", 'Hyper'),
    'VC05': ("Increased silliness, noises, voices or repeated phrases", 'Hyper'),
    'VC06': ("More negotiating or questioning (\"why do I have to\", \"how long\")", 'Hyper'),
    'VC09': ("\"I don't know\", \"I can't\", or a shrug instead of an answer", 'Hypo'),
    'FA02': ("Scanning the room, watching the door or the adults", 'Hyper'),
    'FA03': ("Frowning, grimacing or eye-rolling", 'Hyper'),
    'FA04': ("Glazed, far-away look, slow to respond to name", 'Hypo'),
    'FA06': ("Teary, watery eyes, chin wobbling", 'Either'),
    'TE01': ("Rushing through work, more careless errors", 'Hyper'),
    'TE02': ("Rubbing out or scribbling over again and again, screwing up own work", 'Hyper'),
    'TE04': ("Trying to take control of the task (changing rules, insisting on own way)", 'Hyper'),
    'TE06': ("Delaying the start (sharpening, rearranging, toilet request)", 'Either'),
    'AR04': ("Over-compliant, apologising a lot, people-pleasing", 'Hypo'),
    'AR06': ("Shadowing an adult, seeking closeness more than usual", 'Either'),
    'AR07': ("Rejecting a usually preferred adult, or accepting only one adult", 'Either'),
    'PR02': ("Moving into a peer's space, nudging or poking", 'Hyper'),
    'PR07': ("Bringing up conflict from home, the bus or the yard", 'Either'),
    'SE02': ("Covering ears, flinching at sounds", 'Either'),
    'SE03': ("Shielding eyes, asking for lights off", 'Either'),
    'SE04': ("Seeking deep pressure (squeezing, leaning hard, crashing)", 'Either'),
    'SE06': ("Taking off shoes or jumper, saying they're hot or itchy", 'Either'),
    'RT01': ("Hovering near exits, checking gates or doors", 'Hyper'),
    'RT02': ("Asking again and again what's next, checking the visual timetable", 'Either'),
    'RT03': ("Hard to leave an activity, slow to transition", 'Either'),
    'RT04': ("Unsettled by a change of staff, room or plan", 'Either'),
    'RT05': ("Lingering at the car, gate or bag on arrival", 'Either'),
    'RT06': ("Arriving different from usual (late, without usual item, different mood)", 'Either'),
    'RT07': ("Repeated requests to leave the room (toilet, office, drink)", 'Either'),
    'PH01': ("Saying they're tired, yawning a lot early in the day", 'Hypo'),
    'PH02': ("Headache, tummy ache or feeling sick", 'Either'),
    'PH03': ("Not eating, or eating far more than usual", 'Either'),
    'PH05': ("Picking at skin, nails or hair, nail biting", 'Either'),
    'PH06': ("Toileting changes (more often, accidents, avoiding)", 'Either'),
    'OB01': ("Clicking, tapping or fiddling with objects", 'Hyper'),
    'OB02': ("Pushing items around or off the desk, dropping things", 'Hyper'),
    'OB04': ("Packing up early, putting bag on, getting ready to leave", 'Either'),
}
SPLIT_INTO = {
    'BM01': ['BM12', 'BM13', 'BM14'],
    'BM03': ['BM15', 'BM16'],
    'BM04': ['BM17', 'BM18', 'BM19'],
    'BM05': ['BM20', 'BM21'],
    'BM06': ['BM22', 'BM23', 'BM24'],
    'BM07': ['BM25', 'BM26'],
    'BM10': ['BM27', 'BM28', 'BM29'],
    'VC02': ['VC13', 'VC14'],
    'VC03': ['VC15', 'VC16'],
    'VC05': ['VC17', 'VC18', 'VC19', 'VC20'],
    'VC06': ['VC21', 'VC22'],
    'VC09': ['VC23', 'VC24', 'VC25'],
    'FA02': ['FA08', 'FA09'],
    'FA03': ['FA10', 'FA11', 'FA12'],
    'FA04': ['FA13', 'FA14'],
    'FA06': ['FA15', 'FA16'],
    'TE01': ['TE11', 'TE12'],
    'TE02': ['TE13', 'TE14', 'TE15'],
    'TE04': ['TE16', 'TE17'],
    'TE06': ['TE18', 'TE19', 'TE20'],
    'AR04': ['AR08', 'AR09', 'AR10'],
    'AR06': ['AR11', 'AR12'],
    'AR07': ['AR13', 'AR14'],
    'PR02': ['PR08', 'PR09'],
    'PR07': ['PR10', 'PR11', 'PR12'],
    'SE02': ['SE08', 'SE09'],
    'SE03': ['SE10', 'SE11'],
    'SE04': ['SE12', 'SE13', 'SE14'],
    'SE06': ['SE15', 'SE16'],
    'RT01': ['RT08', 'RT09'],
    'RT02': ['RT10', 'RT11'],
    'RT03': ['RT12', 'RT13'],
    'RT04': ['RT14', 'RT15', 'RT16'],
    'RT05': ['RT17', 'RT18', 'RT19'],
    'RT06': ['RT20', 'RT21', 'RT22'],
    'RT07': ['RT23', 'RT24', 'RT25'],
    'PH01': ['PH07', 'PH08'],
    'PH02': ['PH09', 'PH10', 'PH11'],
    'PH03': ['PH12', 'PH13'],
    'PH05': ['PH14', 'PH15', 'PH16'],
    'PH06': ['PH17', 'PH18', 'PH19'],
    'OB01': ['OB05', 'OB06', 'OB07'],
    'OB02': ['OB08', 'OB09'],
    'OB04': ['OB10', 'OB11'],
}
# Codes kept but reworded to one behaviour: {code: (old wording, new wording)}
RENAMED = {
    'VC08': ("Stops talking, goes quiet", "Goes quiet or stops talking"),
    'VC11': ("Putting self down (\"I'm dumb\", \"I'm bad at this\")", "Putting self down (e.g. \"I'm dumb\")"),
    'VC12': ("Talking about going home, leaving or being somewhere else", "Talking about going home or leaving"),
    'AR01': ("Pushing the adult away (\"leave me alone\", \"don't talk to me\")", "Pushing the adult away (\"leave me alone\")"),
}


def starter_codes() -> list[dict]:
    return [{"code": c, "category": CATEGORIES.get(c[:2], "Other"), "description": d,
             "direction": dr, "active": True, "sort_order": i}
            for i, (c, d, dr) in enumerate(_STARTER)]


def legacy_codes() -> list[dict]:
    """Retired combined codes (inactive) — labels for entries logged before the split."""
    return [{"code": c, "category": CATEGORIES.get(c[:2], "Other"), "description": d,
             "direction": dr, "active": False, "sort_order": 9000 + i}
            for i, (c, (d, dr)) in enumerate(LEGACY_CODES.items())]


def expand_codes(codes) -> set:
    """A code plus, for a retired combined code, the single codes it was split into."""
    out = set()
    for c in codes or []:
        out.add(c)
        out.update(SPLIT_INTO.get(c, []))
    return out


_SYNCED_DB = False


def _sync_db_codes(sb, rows: list[dict]) -> bool:
    """One-off upgrade of a code table seeded before the split: add the new
    single-behaviour codes, retire the combined ones, reword renamed ones.
    Never touches codes Leadership has added or reworded themselves."""
    have = {r["code"]: r for r in rows}
    changes = []
    for r in starter_codes():
        if r["code"] not in have:
            changes.append(r)
    for code in SPLIT_INTO:
        r = have.get(code)
        if r and r.get("active", True):
            changes.append({**{k: r.get(k) for k in ("code", "category", "description",
                                                      "direction", "sort_order")},
                            "active": False})
    for code, (old, new) in RENAMED.items():
        r = have.get(code)
        if r and (r.get("description") or "").strip() == old:
            changes.append({**{k: r.get(k) for k in ("code", "category", "direction",
                                                      "active", "sort_order")},
                            "description": new})
    if not changes:
        return False
    # Upgrading: put every built-in code into the new order (split codes sit
    # where the combined code used to be). Leadership-added codes keep theirs.
    order = {r["code"]: r["sort_order"] for r in starter_codes()}
    order.update({r["code"]: r["sort_order"] for r in legacy_codes()})
    touched = {ch["code"] for ch in changes}
    for code, r in have.items():
        if code in order and code not in touched and r.get("sort_order") != order[code]:
            changes.append({k: r.get(k) for k in ("code", "category", "description",
                                                   "direction", "active")})
    for ch in changes:
        if ch["code"] in order:
            ch["sort_order"] = order[ch["code"]]
    if changes:
        sb.table("micro_behaviour_codes").upsert(changes, on_conflict="code").execute()
    return bool(changes)


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
            global _SYNCED_DB
            if rows and not _SYNCED_DB:
                _SYNCED_DB = True
                try:
                    if _sync_db_codes(sb, rows):
                        rows = (sb.table("micro_behaviour_codes").select("*")
                                .order("sort_order").order("code").execute().data or rows)
                except Exception:
                    pass
            if rows:
                if not include_inactive:
                    rows = [r for r in rows if r.get("active", True)]
                return rows, True
        except Exception:
            pass
    return starter_codes(), False


def seed_codes(sb) -> int:
    rows = starter_codes() + legacy_codes()
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
            "category", "outcome", "outcome_short", "staff_response", "response_source", "setting",
            "just_before", "other_text", "reported_by_name"]
    if not rows:
        return pd.DataFrame(columns=cols)
    lookup = {c["code"]: c for c in codes}
    for c in starter_codes() + legacy_codes():   # retired codes still label old entries
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
                "response_source": {"suggested": "Suggested", "worked_before": "Worked before",
                                    "other": "Own choice"}.get(r.get("response_source") or "", ""),
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
# SUGGESTED RESPONSES — trauma-informed, CPI-aligned
# ──────────────────────────────────────────────────────────────────────────
# CPI Crisis Development Model: Anxiety -> Supportive, Defensive -> Directive.
# Micro behaviours sit at the Anxiety level unless they are already pushing
# back at an adult/peer, which is the Defensive level. Risk behaviour is an
# incident, not a micro behaviour, so the Safety Intervention level is not used.
_DEFENSIVE_BASE = {"BM03", "BM04", "VC03", "VC07", "FA01", "TE03", "TE04",
                   "AR01", "AR02", "AR03", "PR02", "PR03", "RT01", "OB02"}
DEFENSIVE_CODES = expand_codes(_DEFENSIVE_BASE)

CPI_STANCE = {
    "Anxiety": ("Anxiety → Supportive",
                "Empathic, non-judgemental. Connect before you direct: calm voice, fewer words, "
                "respectful space, and help them regulate (co-regulation first, learning later)."),
    "Defensive": ("Defensive → Directive",
                  "Stay calm and take charge kindly. Give a clear, simple, reasonable limit with "
                  "choices, then allow time to decide. Remove the audience; avoid power struggles."),
}

_DIR_SUGGESTIONS = {
    "Hyper": [
        "Lower your voice and slow down; stand side-on at a respectful distance",
        "Offer a movement or sensory break as a choice (\"a job for me, or 2 minutes on the bike?\")",
        "Reduce the demand for now: shorten, chunk or pause the task",
    ],
    "Hypo": [
        "Connect without pressure: sit alongside and name what you notice gently (\"You seem tired today\")",
        "Offer a low-demand activating job (hand out sheets, take a message, water the plants)",
        "Bring arousal up gently: drink of water, rhythm, walk-and-talk",
    ],
    "Either": [
        "Quiet check-in using their name, warm tone, no audience",
        "Offer a choice of two regulation options from their plan",
    ],
}

_DEFENSIVE_SUGGESTIONS = [
    "Give a clear, simple limit with a choice, positive option first (\"You can take a break in the calm corner or sit with me, your choice\")",
    "Give take-up time and step back; don't repeat the instruction or argue the point",
    "Reduce the audience: redirect other students or move to a quieter spot",
]

_CAT_SUGGESTIONS = {
    "TE": ["Do the first part together, then step back", "Offer a choice of how or where to do the work",
           "Acknowledge effort out loud, not accuracy"],
    "VC": ["Respond to the tone with calm and fewer words; don't match the volume",
           "Validate the feeling (\"It sounds like this is hard\") before redirecting",
           "Tactically ignore low-level words and redirect to the task"],
    "AR": ["Use PACE: curious, not cross (\"I'm wondering if something's bothering you\")",
           "Offer a preferred adult if one is free", "Respond to the need, not the words"],
    "PR": ["Create space between students discreetly (a job, a seat change)",
           "Acknowledge the feeling (\"That sounded annoying\") and redirect to a shared task",
           "Increase active supervision nearby"],
    "SE": ["Reduce sensory load: lights down, headphones, quieter space",
           "Offer the supports in their Sensory Overview", "Offer heavy work or deep pressure"],
    "RT": ["Use the visual timetable and \"first… then…\"", "Give a countdown warning before the change",
           "Give a transition job or object to carry"],
    "PH": ["Check basic needs first: food, water, toilet, rest", "Offer a snack or drink per site procedure",
           "Let leadership know if this keeps happening"],
    "BM": ["Offer a movement break or fidget as a choice", "Give space; don't block their exit"],
    "FA": ["Check in privately with a soft, open face", "Reassure and name the plan for the next few minutes"],
    "OB": ["Swap the object for a fidget or regulation tool", "Move items out of reach quietly, without comment"],
}

_CONTEXT_RULES = [
    (("transition", "change", "pack", "finish", "end of", "line up", "moving"),
     "Preview the change privately and give a countdown"),
    (("asked", "instruction", "demand", "fix", "correct", "work", "task", "write", "read", "maths"),
     "Lower the demand: offer a smaller first step or perceived choice"),
    (("peer", "student", "friend", "teased", "said", "looked", "laughed"),
     "Separate the students discreetly and check in privately"),
    (("noise", "loud", "busy", "crowd", "bell", "siren"),
     "Move to a quieter space or offer headphones"),
    (("told no", "said no", "denied", "wait", "turn", "lost", "game"),
     "Acknowledge the disappointment and use \"when… then…\""),
    (("home", "weekend", "bus", "taxi", "morning", "arrival", "arrived"),
     "Private, low-key check-in about what happened before school"),
    (("relief", "trt", "new staff", "different teacher", "absent"),
     "Introduce the adult and explain the plan for the day; keep routines the same"),
]
_SETTING_RULES = [
    (("yard", "recess", "lunch", "outside", "oval", "playground"),
     "Increase active supervision and offer a structured game or job"),
    (("literacy", "maths", "writing", "reading", "spelling", "numeracy"),
     "Chunk the task and do the first one together"),
]


# Category tips that suit rising (Hyper) arousal but not a student who is shutting down
_HYPER_ONLY = {
    "Respond to the tone with calm and fewer words; don't match the volume",
    "Tactically ignore low-level words and redirect to the task",
    "Offer a movement break or fidget as a choice",
    "Give space; don't block their exit",
}


def cpi_stage(codes: list[str]) -> str:
    return "Defensive" if any(c in DEFENSIVE_CODES for c in codes) else "Anxiety"


def suggest_responses(codes: list[str], code_meta: dict, setting: str = "",
                      just_before: str = "", worked_before: list[str] | None = None,
                      max_n: int = 5) -> dict:
    """Rule-based suggestions. Returns
    {stage, stage_label, stage_note, items: [{text, source}]}  source in
    worked_before | suggested."""
    stage = cpi_stage(codes)
    items: list[dict] = []

    def add(t, src="suggested"):
        if t and all(t.lower() != i["text"].lower() for i in items):
            items.append({"text": t, "source": src})

    dirs = [code_meta.get(c, {}).get("direction", "Either") for c in codes]
    hyper, hypo = dirs.count("Hyper"), dirs.count("Hypo")
    main_dir = "Hyper" if hyper > hypo else "Hypo" if hypo > hyper else (
        "Either" if not (hyper or hypo) else "Hyper" if stage == "Defensive" else "Hypo")

    for t in (worked_before or [])[:2]:
        add(t, "worked_before")
    ctx = f" {just_before} ".lower()
    ctx_hits = [t for keys, t in _CONTEXT_RULES if any(k in ctx for k in keys)]
    for t in ctx_hits[:2]:
        add(t)
    if stage == "Defensive":
        for t in _DEFENSIVE_SUGGESTIONS[:2]:
            add(t)
    for t in _DIR_SUGGESTIONS.get(main_dir, [])[:2]:
        add(t)
    st_ = f" {setting} ".lower()
    for keys, t in _SETTING_RULES:
        if any(k in st_ for k in keys):
            add(t)
    for c in codes:
        for t in _CAT_SUGGESTIONS.get(c[:2], []):
            if main_dir == "Hypo" and t in _HYPER_ONLY:
                continue
            add(t)
            break
    for t in _DIR_SUGGESTIONS.get(main_dir, [])[2:] + _DIR_SUGGESTIONS["Either"]:
        add(t)
    label, note = CPI_STANCE[stage]
    return {"stage": stage, "stage_label": label, "stage_note": note,
            "direction": main_dir, "items": items[:max_n]}


def worked_before_for(rows: list[dict], codes: list[str], n: int = 2) -> list[str]:
    """Responses that led to 'Settled' for this student, preferring entries
    that shared a code with the current one."""
    if not rows:
        return []
    scored: dict[str, list] = {}
    for r in rows:
        if OUTCOME_SHORT.get(r.get("outcome", "")) != "Settled":
            continue
        resp = (r.get("staff_response") or "").strip()
        if not resp:
            continue
        overlap = len(expand_codes(r.get("codes")) & expand_codes(codes))
        sc = scored.setdefault(resp, [0, 0])
        sc[0] += overlap
        sc[1] += 1
    ranked = sorted(scored.items(), key=lambda kv: (kv[1][0], kv[1][1]), reverse=True)
    return [k for k, v in ranked if v[0] > 0 or not codes][:n] or [k for k, _ in ranked[:n]]


# ──────────────────────────────────────────────────────────────────────────
# STREAMLIT UI
# ──────────────────────────────────────────────────────────────────────────
_DIR_ARROW = {"Hyper": " ↑", "Hypo": " ↓", "Either": ""}


def _code_label(c: dict) -> str:
    return f"{c['code']} · {c['description']}{_DIR_ARROW.get(c.get('direction'), '')}"


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

    mine = []
    for c in sig_codes:
        for cc in ([c] if c in by_code else SPLIT_INTO.get(c, [])):
            if cc in by_code and cc not in mine:
                mine.append(cc)
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

    st.markdown(
        "<div style='background:#E8F5E9;border-left:5px solid #2E7D32;border-radius:0 8px 8px 0;"
        "padding:.55rem .9rem;margin:.2rem 0 .6rem;font-size:.88rem;color:#1B3A1F;'>"
        "🪟 <b>Window of Tolerance:</b> micro behaviours are <b>coping</b> signs. The student is "
        "still in their window and still coping, but is showing us they are moving toward the "
        "edge. Responding now helps them stay in the window.</div>", unsafe_allow_html=True)
    st.markdown("**👀 What did you see or hear?** (tap one or more · ↑ toward hyperarousal · "
                "↓ toward hypoarousal)")
    sig = load_signature(sb, sid)
    picked = _pick_codes(codes, signature_codes(sig), f"{k}_codes")
    other_text = ""
    if "OT00" in picked:
        other_text = st.text_input("Describe the 'Other' behaviour *", key=f"{k}_other")
    if picked:
        st.caption("Selected: " + ", ".join(picked))
        _meta = {c["code"]: c for c in codes}
        _dirs = [_meta.get(c, {}).get("direction", "Either") for c in picked if c != "OT00"]
        if _dirs:
            st.markdown("**Where this sits in the Window of Tolerance**")
            st.markdown(wot_strip_html(_dirs, compact=True), unsafe_allow_html=True)
            st.caption(wot_position_sentence(_dirs))

    s1, s2 = st.columns(2)
    with s1:
        setting = st.text_input("📍 Setting / activity", placeholder="Literacy, independent writing",
                                key=f"{k}_setting")
    with s2:
        just_before = st.text_input("⏪ Just before", placeholder="Asked to fix a spelling error",
                                    key=f"{k}_before")
    # ── Suggested response (appears once behaviour + setting + just before are in) ──
    st.markdown("**🤝 Response**")
    OTHER = "Something else (describe)"
    sugg_items = []
    if picked and setting.strip() and just_before.strip():
        meta = {c["code"]: c for c in codes}
        past = load_micro(sb, sid)
        sg = suggest_responses(picked, meta, setting, just_before,
                               worked_before=worked_before_for(past, picked))
        sugg_items = sg["items"]
        colour = "#DC2626" if sg["stage"] == "Defensive" else "#1A7A7A"
        tip_parts = []
        for i in sugg_items:
            if i["source"] == "worked_before":
                tip_parts.append("<li>⭐ " + _html.escape(i["text"]) + " <i style='color:#64748b'>"
                                 "(worked before for this student)</i></li>")
            else:
                tip_parts.append("<li>" + _html.escape(i["text"]) + "</li>")
        tips = "".join(tip_parts)
        st.markdown(
            f"<div style='border-left:5px solid {colour};background:#f8fafc;border-radius:0 8px 8px 0;"
            f"padding:.7rem 1rem;margin:.3rem 0 .6rem;'>"
            f"<div style='font-weight:700;color:{colour};'>💡 Suggested response · CPI stage: {sg['stage_label']}</div>"
            f"<div style='font-size:.8rem;color:#475569;'>🪟 {WOT_SHORT.get(sg['direction'], '')}: "
            f"the aim is to help the student stay in their window.</div>"
            f"<div style='font-size:.85rem;color:#334155;margin:.25rem 0 .4rem;'>{sg['stage_note']}</div>"
            f"<ul style='margin:0 0 0 1.1rem;font-size:.9rem;color:#0f172a;'>{tips}</ul>"
            f"<div style='font-size:.75rem;color:#64748b;margin-top:.4rem;'>Suggestions only. Use your "
            f"judgement and the student's Safety &amp; Risk Plan. If behaviour becomes a risk to anyone, "
            f"follow the plan and CPI safety procedures.</div></div>",
            unsafe_allow_html=True)
    else:
        st.caption("Pick the behaviour and fill in **Setting** and **Just before** to see a suggested "
                   "trauma-informed, CPI-aligned response.")
    resp_opts = [i["text"] for i in sugg_items] + [OTHER]
    used = st.radio("What did you do? *", resp_opts, index=None, key=f"{k}_used",
                    format_func=lambda x: ("✅ Used: " + x) if x != OTHER else "✏️ " + x)
    response, response_source = "", ""
    if used == OTHER:
        response = st.text_input("Describe what you did *", placeholder="Offered a 2-minute movement break",
                                 key=f"{k}_resp")
        response_source = "other"
    elif used:
        response = used
        response_source = next((i["source"] for i in sugg_items if i["text"] == used), "suggested")
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
        if not used:
            errs.append("Choose what you did (a suggestion or something else).")
        elif used == OTHER and not response.strip():
            errs.append("Describe what you did.")
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
        row = {
            "student_id": str(sid), "occurred_at": occurred, "codes": picked,
            "other_text": other_text.strip(), "setting": setting.strip(),
            "just_before": just_before.strip(), "staff_response": response.strip(),
            "response_source": response_source,
            "outcome": outcome, "reported_by": str(staff_id),
            "reported_by_name": staff_opts.get(staff_id, ""),
        }
        try:
            saved = save_micro(sb, row)
        except Exception as e:
            if "response_source" in str(e):
                # Table created before this update and the ALTER hasn't been run yet:
                # save without the new column rather than losing the entry.
                row.pop("response_source", None)
                try:
                    saved = save_micro(sb, row)
                except Exception as e2:
                    saved = None
                    st.error(f"Could not save: {e2}")
            else:
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
                f"starter list ({len(_STARTER) - 1} codes + Other) is being used.")
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
    st.markdown(
        "<div style='background:#E8F5E9;border-left:5px solid #2E7D32;border-radius:0 8px 8px 0;"
        "padding:.5rem .9rem;margin:.2rem 0 .6rem;font-size:.86rem;color:#1B3A1F;'>"
        "🪟 <b>Window of Tolerance link:</b> every entry here is a <b>coping</b> sign. The student "
        "was still in their window, but showing they were moving toward the edge (Coping ↑ toward "
        "hyperarousal, or Coping ↓ toward hypoarousal). Incidents are when they've left the window.</div>",
        unsafe_allow_html=True)

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
            st.caption("Bar colour = Window of Tolerance coping zone: amber Coping ↑ toward "
                       "hyperarousal, blue Coping ↓ toward hypoarousal, purple either way.")
        with cB:
            st.markdown("**Which coping zone**")
            tot = sum(ds.values()) or 1
            for dname, label in [("Hyper", "Coping ↑ toward hyper"), ("Hypo", "Coping ↓ toward hypo"),
                                 ("Either", "Either way")]:
                st.markdown(
                    f"<div style='border-left:4px solid {DIR_COLOURS[dname]};padding:.3rem .6rem;"
                    f"margin-bottom:.4rem;background:#f8fafc;border-radius:0 6px 6px 0;'>"
                    f"<b>{label}</b><br><span style='font-size:1.3rem;font-weight:700;'>"
                    f"{round(ds[dname] / tot * 100)}%</span> <span style='color:#64748b;"
                    f"font-size:.8rem;'>({ds[dname]})</span></div>", unsafe_allow_html=True)
            main = max(ds, key=ds.get)
            if ds["Hyper"] and ds["Hypo"] and min(ds["Hyper"], ds["Hypo"]) / max(ds["Hyper"], ds["Hypo"]) >= 0.5:
                st.caption("Signs in both coping zones — check whether this student goes quiet "
                           "(toward hypoarousal) before they escalate (toward hyperarousal).")
            elif main == "Hypo":
                st.caption("Mostly Coping ↓ toward hypoarousal — quiet signs that are easy to miss "
                           "in a busy room.")
            elif main == "Hyper":
                st.caption("Mostly Coping ↑ toward hyperarousal.")

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
        _e1 = mdf.drop_duplicates("id")
        _sug = _e1[_e1["response_source"].isin(["Suggested", "Worked before"])]
        if len(_sug):
            _sug_set = int((_sug["outcome_short"] == "Settled").sum())
            st.caption(f"Suggested responses were used {len(_sug)} time(s); the student settled after "
                       f"{_sug_set} of them ({round(_sug_set / len(_sug) * 100)}%).")
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
                                      rtype=("response_source", "first"),
                                      setting=("setting", "first"), before=("just_before", "first"),
                                      by=("reported_by_name", "first")).reset_index()
            e = e.sort_values("dt", ascending=False)
            show = e.assign(When=e["dt"].dt.strftime("%a %d/%m/%Y %I:%M %p"))[
                ["When", "codes", "setting", "before", "response", "rtype", "outcome", "by"]].rename(columns={
                    "rtype": "Response type",
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
    st.caption("The student's own short, ordered list of coping signs as they move toward the edge "
               "of their Window of Tolerance, and what helps them stay in it at each stage. Stages "
               "1–3 are still in the window; stage 4 is outside it. It feeds the Early Warning Signs "
               "section of their Safety & Risk Plan. Review it each term.")
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
