"""
excursion_utils.py  —  shared helpers for the CLC-LBU Excursion Planner.

Used by:  pages/74_Excursion_Planner.py

Put this file at the ROOT of the repo (next to confidential_auth.py).

Staff plan, save, find and download excursions here. The documents are printed and signed by hand
(teacher-in-charge, then Leadership) – the tool does not send anything to Leadership.

What lives here
  * DfE Camps and Excursions Procedure (March 2025) rules the tool checks against
    (ratios, exclusions, bushfire season, aquatic, buses, private vehicles …)
  * The risk matrix from the CLC risk assessment (Likelihood x Consequence)
  * The starter Activity Library (staff can add to it from the tool)
  * Supabase + email helpers (same secrets / Apps Script mailer as the Hazard Report)
  * Word builders: ED169 Application to Conduct a Camp or Excursion, and the
    CLC Risk Management Plan and Approval to Transport
"""

from __future__ import annotations

import copy
import io
import math
import os
from datetime import date, datetime, time

import streamlit as st

try:
    from zoneinfo import ZoneInfo
    ADL_TZ = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover
    ADL_TZ = None

# =====================================================================
# Tables
# =====================================================================
T_EXCURSIONS = "excursions"
T_ACTIVITIES = "excursion_activities"
T_STAFF = "excursion_staff"
T_VEHICLES = "excursion_vehicles"
# CLC site vehicles – used until the vehicles table has rows (edit in ⚙️ Settings → Vehicles)
DEFAULT_VEHICLES = [
    {"id": None, "name": "Kia (site car)", "rego": "S104BQL", "seats": None, "active": True},
    {"id": None, "name": "Van", "rego": "S996BQL", "seats": None, "active": True},
]

VEHICLES_SQL = """-- Excursion Planner: site vehicles list (run once if you ran the earlier setup SQL)
create table if not exists excursion_vehicles (
  id uuid primary key default gen_random_uuid(),
  name text not null,                            -- e.g. Kia Carnival (site car)
  rego text,                                     -- registration number
  seats int,                                     -- seats incl. driver (optional – used for a seating check)
  notes text,
  active boolean default true
);
alter table excursion_vehicles disable row level security;
insert into excursion_vehicles (name, rego)
select v.name, v.rego from (values ('Kia (site car)', 'S104BQL'), ('Van', 'S996BQL')) as v(name, rego)
where not exists (select 1 from excursion_vehicles e where upper(e.rego) = v.rego);
"""

SETUP_SQL = """-- CLC Excursion Planner — run once in the Supabase SQL editor
-- (same Supabase project as the Hazard Report: SUPABASE_URL / SUPABASE_KEY)

create table if not exists excursions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  status text not null default 'Saved',          -- Saved | Archived
  name text,
  destination text,
  program text,
  excursion_date date,
  teacher_in_charge text,
  prepared_by text,
  data jsonb not null default '{}'::jsonb       -- every field of the form
);

create table if not exists excursion_activities (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  name text not null,
  category text default 'Activity',
  flags jsonb not null default '{}'::jsonb,     -- aquatic / bushfire / national_park / food / public_transport ...
  risks jsonb not null default '[]'::jsonb,     -- list of {hazard, likelihood, consequence, controls, procedure}
  created_by text,
  reviewed boolean default true,                 -- false = added by staff, Leadership to check
  active boolean default true
);

create table if not exists excursion_staff (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  gender text,                                   -- M / F / X
  status text default 'Teacher',                 -- Teacher / SSO / Leader / Specialist / Other
  email text,
  is_leader boolean default false,               -- Leadership (used as the default site contact)
  first_aid_expiry date,
  active boolean default true
);

create table if not exists excursion_vehicles (
  id uuid primary key default gen_random_uuid(),
  name text not null,                            -- e.g. Kia Carnival (site car)
  rego text,                                     -- registration number
  seats int,                                     -- seats incl. driver (optional – used for a seating check)
  notes text,
  active boolean default true
);

alter table excursions           disable row level security;
alter table excursion_activities disable row level security;
alter table excursion_staff      disable row level security;
alter table excursion_vehicles   disable row level security;

insert into excursion_vehicles (name, rego)
select v.name, v.rego from (values ('Kia (site car)', 'S104BQL'), ('Van', 'S996BQL')) as v(name, rego)
where not exists (select 1 from excursion_vehicles e where upper(e.rego) = v.rego);
"""

# =====================================================================
# DfE procedure rules (Camps and excursions procedure, March 2025)
# =====================================================================
PROGRAMS = ["JP", "PY", "SY", "Whole site", "Other"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
EXCURSION_TYPES = [
    "Excursion (one-off, off site)",
    "Local walk or regular outing",
]
STAFF_STATUSES = ["Teacher", "SSO", "Leader", "Specialist", "Volunteer", "Instructor", "Other"]

TRANSPORT_MODES = [
    "Site car / government vehicle",
    "Walking only",
    "Public transport (bus / train / tram)",
    "Chartered bus",
    "Private vehicle",
]

# Minimum ratios — procedure p.17 ("Ratios")
RATIO_EXCURSION = [((0, 2), 6, "Reception to Year 2"), ((3, 6), 10, "Years 3 to 6"), ((7, 12), 15, "Years 7 to 12")]
RATIO_LOCAL_WALK = 15
CLC_MIN_ADULTS = 2          # CLC practice: never fewer than 2 adults off site

EXCLUDED_ACTIVITIES = [
    "parachuting", "boxing", "quad bik", "rock fishing", "rodeo", "gliding",
    "paraglid", "formula car", "go kart racing", "bungy", "bungee", "shooting",
]
BUSHFIRE_MONTHS = {11, 12, 1, 2, 3, 4}   # "particularly between November and April"

# =====================================================================
# Risk matrix (from the CLC risk assessment "Notes on analysing risks")
# =====================================================================
LIKELIHOOD = ["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"]
CONSEQUENCE = ["Insignificant", "Minor", "Moderate", "Major", "Critical"]
LIKELIHOOD_HELP = {
    "Almost Certain": "Almost certain to occur in most circumstances",
    "Likely": "Likely to occur frequently",
    "Possible": "Possible and likely to occur at some time",
    "Unlikely": "Unlikely to occur but could happen",
    "Rare": "May occur but only in rare and exceptional circumstances",
}
CONSEQUENCE_HELP = {
    "Critical": ["Critical incident. (e.g. Death or permanent disability of adult or child; high level of "
                 "distress to other parties)",
                 "Sustained negative publicity or damage to reputation from a national perspective or from "
                 "the community welfare perspective."],
    "Major": ["Multiple injuries requiring specialist medical treatment or hospitalisation; and/or major "
              "occupational health safety & welfare liability incident / issue.",
              "Major incident which damages public or parent confidence.",
              "One or more children are lost from the main group."],
    "Moderate": ["Serious injuries and/or illness.", "Complex welfare and/or health care issue.",
                 "Serious disruption or incident, resulting in distress to children and adults."],
    "Minor": ["Minor first aid or minor occupational health safety & welfare liability incident / issue "
              "(e.g. minor cuts, bruises, bumps).", "Minor behavioural issues."],
    "Insignificant": ["No treatment required."],
}
MATRIX = {  # consequence -> levels by likelihood (Rare … Almost Certain)
    "Critical":      ["Moderate", "High", "High", "Extreme", "Extreme"],
    "Major":         ["Moderate", "Moderate", "High", "High", "Extreme"],
    "Moderate":      ["Low", "Moderate", "Moderate", "High", "High"],
    "Minor":         ["Low", "Low", "Moderate", "Moderate", "Moderate"],
    "Insignificant": ["Low", "Low", "Low", "Moderate", "Moderate"],
}
LEVEL_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Extreme": 3}
LEVEL_COLOUR = {"Low": "#2e7d32", "Moderate": "#c8760a", "High": "#c62828", "Extreme": "#6a1b9a"}
LEVEL_FILL = {"Low": "E8F5E9", "Moderate": "FFF3E0", "High": "FFEBEE", "Extreme": "F3E5F5"}


def risk_level(likelihood: str, consequence: str) -> str:
    try:
        return MATRIX[consequence][LIKELIHOOD.index(likelihood)]
    except Exception:
        return "Moderate"


# =====================================================================
# Starter Activity Library
# =====================================================================
def _r(hazard, like, cons, controls, procedure):
    return {"hazard": hazard, "likelihood": like, "consequence": cons,
            "controls": controls.strip(), "procedure": procedure.strip()}


UNSIGHTED = ("If a student becomes unsighted: contact CLC Leadership/site contact immediately, "
             "then SAPOL (131 444, or 000 if there is immediate danger) and the student's parent/carer. "
             "Leadership to report via IRMS.")

GENERAL_ACTIVITY = {
    "name": "General – supervision and student wellbeing (every excursion)",
    "category": "General",
    "flags": {"always": True},
    "risks": [
        _r("Student leaves the group or the supervised area without permission.", "Unlikely", "Major", """
- Staff-to-student ratios meet DfE minimums and CLC practice (minimum 2 adults).
- Each student allocated to a named adult for the whole excursion.
- Headcounts before leaving CLC, on arrival, at regular intervals, before leaving the venue and on return.
- Meeting point agreed and shown to students on arrival.
- Safety & Risk Plans checked for students with a history of leaving; staff know each plan.
- Expectations pre-taught (visuals / social story) before the day.""",
           f"""
- Allocated adult keeps the student in sight and follows their Safety & Risk Plan; other staff keep the group together.
- {UNSIGHTED}"""),
        _r("Student becomes dysregulated (outside their Window of Tolerance) or behaves unsafely.", "Possible", "Minor", """
- Each student's Safety & Risk Plan and Window of Tolerance reviewed by attending staff.
- Visual schedule / social story of the excursion shared beforehand; changes flagged early.
- Regulation and sensory items carried; a quieter space identified at the venue.
- Staff watch for early warning signs and reduce demands early.""",
           """
- Follow the student's Safety & Risk Plan (tiered responses).
- Move the student (or the group) to a calmer space; one adult leads, others support the group.
- If unsafe or not settling: contact the site contact for support or pick-up; contact parent/carer.
- Record as a minor incident or ABCH critical incident on return."""),
        _r("Student or staff member becomes ill, injured or has an allergic / medical event.", "Unlikely", "Moderate", """
- Health care plans checked; plans shared with attending staff on a need-to-know basis.
- Required medication (e.g. EpiPen, Ventolin) carried and kept close to the student.
- First aid kit and a current first aider on the excursion.
- Mobile phone charged and carried; site contact and parent numbers on hand.""",
           """
- First aider provides first aid; follow the student's health care plan.
- Call 000 for any serious injury or illness.
- Contact the site contact and the parent/carer. Leadership to report via IRMS."""),
    ],
}

DEFAULT_ACTIVITIES = [
    {"name": "Travel – site car / government vehicle", "category": "Transport", "flags": {"vehicle": True}, "risks": [
        _r("Involved in a traffic accident.", "Rare", "Moderate", """
- Authorised driver with a current licence; DfE motor vehicle procedure followed.
- Every student seated with a seat belt / appropriate restraint fastened.
- Vehicle checked before departure; route planned; no phone use while driving.""",
           """
- Ensure the immediate safety of all students (all accompanying staff); call 000 if needed.
- Contact the site contact and parents/carers.
- Report via IRMS and follow the motor vehicle procedure."""),
        _r("Unsafe behaviour in the vehicle (e.g. fighting, unbuckling, distracting the driver).", "Unlikely", "Minor", """
- Seating plan set in advance; second adult travels as a passenger where possible.
- Expectations and the consequences of unsafe behaviour reinforced before boarding.""",
           """
- Pull over safely and stop the vehicle; manage the situation.
- Contact the site contact for support if needed."""),
        _r("Student left in the vehicle, or not accounted for when getting in or out.", "Rare", "Major", """
- Roll check and headcount when getting in and out of the vehicle.
- Driver physically checks the vehicle is empty before locking it.""",
           f"""
- Stop and recount immediately; check the vehicle.
- {UNSIGHTED}"""),
    ]},
    {"name": "Travel – public transport (bus / train / tram)", "category": "Transport", "flags": {"public_transport": True}, "risks": [
        _r("Group is split when boarding or getting off (a student or adult left behind).", "Unlikely", "Major", """
- At least one staff member travels in each carriage/vehicle with students.
- Headcount before boarding and straight after getting off.
- Plan taught in advance: anyone separated gets off at the next stop and waits with an adult.""",
           f"""
- Separated adult keeps the student(s) with them and phones the teacher-in-charge.
- {UNSIGHTED}"""),
        _r("Injury on platforms, stops or moving vehicles (falls, platform edge, crowding).", "Unlikely", "Moderate", """
- Students wait behind the yellow line / back from the kerb and board when told.
- Seated or holding on while moving; avoid peak times where possible.""",
           """
- First aid as needed; call 000 if serious; contact the site contact and parent/carer."""),
        _r("Behaviour affects members of the public.", "Possible", "Minor", """
- Public-transport expectations pre-taught; staff positioned among students.""",
           """
- Calmly redirect; if needed get off at the next stop and regroup; follow Safety & Risk Plans."""),
    ]},
    {"name": "Travel – chartered bus", "category": "Transport", "flags": {"bus": True}, "risks": [
        _r("Bus is unsafe, unaccredited or breaks down.", "Rare", "Major", """
- Operator and driver accreditation details recorded on the ED169.
- Current safety label of inspection on the windscreen; operator has back-up services.
- Every student has their own seat; seat belts worn where fitted.""",
           """
- Keep students seated or move them to a safe area away from traffic.
- Contact the operator and the site contact; arrange alternative transport."""),
        _r("Student not accounted for when getting on or off the bus.", "Rare", "Major", """
- Roll check and headcount when getting on and off; staff member checks the bus is empty.
- An adult guides the driver when reversing or parking in tight areas.""",
           f"""
- Stop and recount immediately.
- {UNSIGHTED}"""),
    ]},
    {"name": "Walking – footpaths and crossing roads", "category": "Transport", "flags": {"walking": True}, "risks": [
        _r("Struck by a vehicle or bike while walking or crossing.", "Rare", "Major", """
- Route planned and walked or checked in advance; use pedestrian lights and crossings.
- Adult at the front and back of the group; students walk on the inside of the footpath.
- Road safety expectations practised before the day.""",
           """
- Ensure the group is safe; first aid; call 000 if needed.
- Contact the site contact and parent/carer; report via IRMS."""),
        _r("Trips and falls on uneven paths.", "Unlikely", "Minor", """
- Appropriate footwear; walking pace set to the slowest student.""",
           """
- First aid as needed; contact parent/carer if more than minor."""),
    ]},
    {"name": "Park, reserve or playground", "category": "Venue", "flags": {"outdoor": True}, "risks": [
        _r("Injury from play equipment or running games.", "Unlikely", "Minor", """
- Staff check equipment and the area on arrival; age-appropriate equipment only.
- Staff positioned to see all students; clear play boundaries shown.""",
           """
- First aid as needed; follow emergency health plans; call 000 if serious."""),
        _r("Hazards on the ground (broken glass, syringes, dog faeces) or off-leash dogs.", "Unlikely", "Minor", """
- Staff sweep the area on arrival; students told not to touch items found and to tell an adult.
- Group moves away from unfamiliar or off-leash dogs.""",
           """
- Staff remove students from the area; sharps are not handled by students.
- First aid for any bite or needlestick, then seek medical advice; contact parent/carer."""),
        _r("Bites and stings (bees, wasps, ants, spiders, snakes).", "Unlikely", "Moderate", """
- Students with known allergies identified; EpiPen carried where prescribed.
- Avoid long grass and garden beds; staff check seating areas.""",
           """
- Follow the health care plan / anaphylaxis plan; call 000 for anaphylaxis or snake bite.
- Pressure immobilisation for snake bite; keep the student still."""),
    ]},
    {"name": "Beach, coast or jetty", "category": "Venue", "flags": {"aquatic": True, "outdoor": True}, "risks": [
        _r("Student falls into or enters the water (drowning).", "Rare", "Critical", """
- Water entry is NOT part of the program unless it has been planned and approved separately.
- Staff positioned between students and the water; students stay above the high-tide line and away from jetty edges.
- Tide, surf and weather checked (BOM) the day before and on the morning.
- Students who cannot swim, or who are drawn to water, identified in advance.""",
           """
- Do not enter the water unless trained and it is safe to do so; throw a floating object.
- Call 000 and alert lifeguards/bystanders; keep the rest of the group together.
- Contact the site contact and parent/carer; report via IRMS."""),
        _r("Cuts from shells/rocks, marine stings (jellyfish, blue-ringed octopus).", "Unlikely", "Minor", """
- Footwear worn on rocks; students told not to touch marine creatures.""",
           """
- First aid; vinegar/cold pack as appropriate; call 000 for a blue-ringed octopus bite."""),
    ]},
    {"name": "Lake, river, creek or wetlands", "category": "Venue", "flags": {"aquatic": True, "outdoor": True}, "risks": [
        _r("Student falls into or enters the water.", "Rare", "Critical", """
- Students stay on paths and away from banks; staff positioned on the water side.
- Water entry is not part of the program.""",
           """
- Do not enter the water unless trained and safe; throw a floating object; call 000.
- Contact the site contact and parent/carer; report via IRMS."""),
        _r("Slippery or uneven banks; snakes in reeds and long grass.", "Unlikely", "Moderate", """
- Stay on formed paths; closed footwear; avoid long grass.""",
           """
- First aid; pressure immobilisation and 000 for snake bite."""),
    ]},
    {"name": "Swimming pool / aquatic centre", "category": "Venue", "flags": {"aquatic": True}, "risks": [
        _r("Drowning or near drowning.", "Rare", "Critical", """
- Centre lifeguards on duty; qualified instructors confirmed for any lessons.
- Students' swimming ability known; non-swimmers stay in shallow, designated areas.
- CLC staff actively supervise from poolside at all times (supervision is not handed to centre staff).
- Relevant health care plans and behaviour information shared with instructors.""",
           """
- Alert lifeguards immediately; call 000; keep the group out of the water and together.
- Contact the site contact and parent/carer; report via IRMS."""),
        _r("Slips and falls on wet surfaces; change room supervision.", "Unlikely", "Minor", """
- Walk on pool decks; change room arrangements planned (same-gender staff, students change in groups).""",
           """
- First aid as needed."""),
    ]},
    {"name": "BBQ / cooking food", "category": "Activity", "flags": {"food": True}, "risks": [
        _r("Burns from the BBQ or hot food.", "Unlikely", "Moderate", """
- Staff operate the BBQ; students stay behind a marked line unless 1:1 with an adult.
- Tongs and gloves used; hot plates never left unattended.""",
           """
- Cool running water for 20 minutes; first aid; call 000 for serious burns."""),
        _r("Allergic reaction or food-borne illness.", "Unlikely", "Moderate", """
- Dietary needs and allergies checked against health care plans before shopping.
- Food kept cold in an esky; hands washed or sanitised; separate utensils for raw and cooked food.""",
           """
- Follow the anaphylaxis / health care plan; call 000 for anaphylaxis; contact parent/carer."""),
        _r("Cuts from knives during food preparation.", "Unlikely", "Minor", """
- Food prepared at CLC where possible; knife use supervised 1:1 and taught.""",
           """
- First aid."""),
    ]},
    {"name": "Café or restaurant", "category": "Venue", "flags": {"food": True, "public": True}, "risks": [
        _r("Allergic reaction to food or drink.", "Unlikely", "Moderate", """
- Allergies checked against health care plans; staff check orders with café staff.""",
           """
- Follow the anaphylaxis / health care plan; call 000; contact parent/carer."""),
        _r("Burns from hot drinks; breakages.", "Unlikely", "Minor", """
- Hot drinks placed away from table edges; students seated with staff.""",
           """
- Cool running water; first aid."""),
        _r("Behaviour in a public setting affects others.", "Possible", "Minor", """
- Expectations pre-taught; quieter seating requested; visit at a quieter time.""",
           """
- Calmly redirect; step outside with the student if needed; follow Safety & Risk Plans."""),
    ]},
    {"name": "Library", "category": "Venue", "flags": {"public": True}, "risks": [
        _r("Student separated from the group inside the building.", "Unlikely", "Major", """
- Meeting point inside the library agreed and shown to students; students stay with their allocated adult.
- Library staff told the group is visiting.""",
           f"""
- Go to the meeting point; ask library staff to help search and watch the exits.
- {UNSIGHTED}"""),
        _r("Behaviour affects other library users.", "Possible", "Minor", """
- Library expectations pre-taught; visit planned for a quieter time.""",
           """
- Calmly redirect; take a break outside with an adult if needed."""),
    ]},
    {"name": "Shopping centre", "category": "Venue", "flags": {"public": True}, "risks": [
        _r("Student lost in crowds.", "Unlikely", "Major", """
- Students stay with their allocated adult; meeting point agreed (e.g. information desk).
- Visit at quieter times; identifiable clothing worn where possible.""",
           f"""
- Go to the meeting point; ask centre security to help and watch the exits.
- {UNSIGHTED}"""),
        _r("Injury on escalators or travelators.", "Unlikely", "Minor", """
- Use lifts or stairs where possible; students hold the rail and stand still.""",
           """
- First aid; contact parent/carer if more than minor."""),
        _r("Student takes items without paying.", "Unlikely", "Minor", """
- Expectations taught; staff stay close in shops.""",
           """
- Calmly return the item and apologise to the shop with the student; inform parent/carer."""),
    ]},
    {"name": "Museum, gallery or public venue / event", "category": "Venue", "flags": {"public": True}, "risks": [
        _r("Student separated from the group in a crowded venue.", "Unlikely", "Major", """
- Program booked in advance; meeting point set on arrival.
- Identifiable clothing (e.g. CLC shirts); bags kept to a minimum.
- Audience / venue behaviour taught before the visit.""",
           f"""
- Go to the meeting point; ask venue staff to help and watch the exits.
- {UNSIGHTED}"""),
        _r("Damage to exhibits or property.", "Unlikely", "Minor", """
- Hands-off expectations taught; staff positioned near students.""",
           """
- Remove the student from the area; report to venue staff and Leadership."""),
    ]},
    {"name": "Bushwalk / conservation or national park", "category": "Venue",
     "flags": {"bushfire": True, "national_park": True, "outdoor": True}, "risks": [
        _r("Bushfire.", "Rare", "Critical", """
- CFS 4-day fire danger rating and BOM warnings checked; cancelled on a total fire ban day or if a fire is nearby.
- Avoid bushfire-prone areas between November and April where possible.
- Ranger / National Parks SA office notified; safe refuge locations identified.""",
           """
- Leave the area by the planned route immediately; follow emergency services advice.
- Contact the site contact and parents/carers."""),
        _r("Getting lost or separated on trails.", "Unlikely", "Major", """
- Trail planned and checked; adults at the front and back; regular headcounts at trail markers.""",
           f"""
- Stop the group and stay together; search back along the trail with one adult.
- {UNSIGHTED}"""),
        _r("Snake bite, falls on uneven terrain, heat.", "Unlikely", "Moderate", """
- Closed shoes, stay on tracks; water, hats and sunscreen; walk early in the day.""",
           """
- Pressure immobilisation and 000 for snake bite; first aid; contact parent/carer."""),
    ]},
    {"name": "Zoo or wildlife park", "category": "Venue", "flags": {"public": True, "outdoor": True}, "risks": [
        _r("Bites, scratches or illness from animal contact.", "Unlikely", "Minor", """
- Animal contact only in supervised keeper sessions; hands washed afterwards.
- Students with allergies to animals identified.""",
           """
- First aid; seek medical advice for bites; contact parent/carer."""),
        _r("Student separated from the group.", "Unlikely", "Major", """
- Meeting point set at the entrance; students stay with their allocated adult.""",
           f"""
- Go to the meeting point; ask park staff to help and watch the exits.
- {UNSIGHTED}"""),
    ]},
    {"name": "Ten-pin bowling / indoor entertainment venue", "category": "Venue", "flags": {"public": True}, "risks": [
        _r("Injury from bowling balls (dropped on feet or fingers caught) or slipping on the lanes.", "Unlikely", "Minor", """
- Staff model how to pick up, carry and release the ball; students choose a ball they can manage (light balls / ramps).
- Only the bowler on the approach; others wait seated; bowling shoes worn; no crossing the foul line.""",
           """
- First aid; ice for bumps; contact parent/carer if more than minor."""),
        _r("Student separated from the group in a busy venue (arcade / food areas).", "Unlikely", "Major", """
- Group stays in its booked lanes; meeting point set at the lanes; arcade only with an adult.""",
           f"""
- Go to the meeting point; ask venue staff to help and watch the exits.
- {UNSIGHTED}"""),
        _r("Frustration or conflict over turn-taking, scores or losing.", "Possible", "Minor", """
- Turn-taking, fair play and good sportsmanship pre-taught; visual turn order; bumpers if helpful.
- Staff watch for early warning signs and offer breaks.""",
           """
- Follow the student's Safety & Risk Plan; take a calm break away from the lanes."""),
    ]},
    {"name": "Weather – sun, heat, rain and storms", "category": "General", "flags": {"outdoor": True}, "risks": [
        _r("Sunburn, heat exhaustion or dehydration.", "Possible", "Minor", """
- DfE inclement weather and sun protection procedure followed; BOM forecast checked.
- Hats, sunscreen and water for every student; shade identified; activities shortened in heat.
- Excursion postponed if extreme heat is forecast.""",
           """
- Move to shade, cool down and give water; first aid; call 000 for signs of heat stroke.
- Contact the site contact for early pick-up if needed."""),
        _r("Storm, strong wind or heavy rain.", "Unlikely", "Minor", """
- Forecast checked on the morning; wet-weather shelter identified at the venue.""",
           """
- Move to shelter; return to CLC early if conditions worsen."""),
    ]},
]


def new_risk() -> dict:
    return _r("", "Unlikely", "Minor", "", "")


def blank_activity(name: str = "") -> dict:
    return {"name": name, "category": "Activity", "flags": {}, "risks": [new_risk()],
            "library_id": None, "save_to_library": True, "is_new": True}


def activity_for_excursion(lib_row: dict) -> dict:
    a = copy.deepcopy({k: lib_row.get(k) for k in ("name", "category", "flags", "risks")})
    a["flags"] = a.get("flags") or {}
    a["risks"] = a.get("risks") or []
    a["library_id"] = lib_row.get("id")
    a["save_to_library"] = False
    a["is_new"] = False
    return a


# =====================================================================
# Secrets / Supabase / email  (same pattern + secrets as the Hazard Report)
# =====================================================================
def _secret(*paths, default=None):
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


@st.cache_resource(show_spinner=False)
def get_supabase():
    from supabase import create_client

    url = _secret("SUPABASE_URL", "supabase.url", "supabase.SUPABASE_URL", "connections.supabase.url")
    key = _secret("SUPABASE_KEY", "SUPABASE_ANON_KEY", "supabase.key", "supabase.anon_key",
                  "supabase.SUPABASE_KEY", "connections.supabase.key")
    if not url or not key:
        raise RuntimeError("Supabase URL/key not found in Streamlit secrets / Render environment.")
    return create_client(url, key)


def today_adl() -> date:
    return datetime.now(ADL_TZ).date() if ADL_TZ else date.today()


def now_iso() -> str:
    return (datetime.now(ADL_TZ) if ADL_TZ else datetime.now()).isoformat()


# =====================================================================
# Excursion data model
# =====================================================================
def blank_excursion() -> dict:
    return {
        "excursion_type": EXCURSION_TYPES[0],
        "name": "", "destination": "", "address": "", "program": "PY",
        "outline": "", "curriculum": "",
        "date_from": None, "date_to": None,
        "depart_time": "10:00", "return_time": "14:30",
        "students": [{"year": "3", "male": 0, "female": 0, "other": 0}],
        "student_considerations": "",
        "staff": [],
        "teacher_in_charge": "",
        "min_at_once": 2,
        "site_contact": "", "site_contact_phone": "",
        "call_in": "Text/phone the site contact on arrival, if plans change, and when leaving to return to CLC.",
        "emergency_extra": "",
        "transport_mode": TRANSPORT_MODES[0],
        "vehicle_desc": "",
        "vehicles": [],                  # site vehicles chosen: [{"name", "rego", "seats"}]
        "bus_company": "", "bus_phone": "", "bus_accreditation": "", "driver_accreditation": "",
        "driver_name": "", "driver_licence": "", "hvnl_aware": None, "last_heavy_vehicle": "",
        "freeway_aware": None,
        "private_vehicles": [],
        "costs": {"food": 0.0, "transport": 0.0, "accommodation": 0.0, "entrance": 0.0},
        "predominantly_educational": True,
        "activities": [],
        "bushfire_area": False, "national_park": False,
        "checks": {},
        "venue_reviewed": False,
        "prepared_by": "",
    }


PRE_CHECKS = [
    ("health_plans", "Health care plans checked for every student going; medication packed where needed"),
    ("safety_plans", "Safety & Risk Plans / Windows of Tolerance reviewed by all attending staff"),
    ("consent", "Parent/carer consent obtained (or requested) and costs explained"),
    ("bookings", "Bookings confirmed (at least one week before for paid venues/transport)"),
    ("briefed", "All attending adults briefed on the program, their role and emergency procedures"),
    ("kit", "First aid kit, charged mobile phone, emergency contacts and student list packed"),
    ("prep", "Students prepared (visual schedule / social story / expectations taught)"),
    ("cultural", "Cultural and environmental considerations thought about (e.g. Traditional Owners of the area)"),
]


def year_num(y: str) -> int:
    return 0 if str(y).upper() in ("R", "REC", "RECEPTION") else int(y)


def student_total(d: dict) -> int:
    return sum(int(s.get("male") or 0) + int(s.get("female") or 0) + int(s.get("other") or 0)
               for s in d.get("students", []))


def required_adults(d: dict) -> tuple[int, str]:
    """Minimum adults under the procedure's ratios (+ CLC minimum of 2)."""
    total = student_total(d)
    if total == 0:
        return CLC_MIN_ADULTS, "No students entered yet."
    if d.get("excursion_type", "").startswith("Local walk"):
        need = math.ceil(total / RATIO_LOCAL_WALK)
        why = f"Local walk/regular outing ratio 1:{RATIO_LOCAL_WALK}"
    else:
        frac, parts = 0.0, []
        for (lo, hi), ratio, label in RATIO_EXCURSION:
            n = sum(int(s.get("male") or 0) + int(s.get("female") or 0) + int(s.get("other") or 0)
                    for s in d.get("students", []) if lo <= year_num(s.get("year", "3")) <= hi)
            if n:
                frac += n / ratio
                parts.append(f"{n} × {label} (1:{ratio})")
        need = math.ceil(frac - 1e-9)
        why = "DfE minimum: " + ", ".join(parts)
    final = max(need, CLC_MIN_ADULTS)
    if final > need:
        why += f" → raised to the CLC minimum of {CLC_MIN_ADULTS} adults"
    return final, why


def cost_breakdown(d: dict) -> dict:
    """GST rule from the ED169: predominantly educational → GST on food only; otherwise on everything."""
    edu = bool(d.get("predominantly_educational", True))
    out, total = {}, 0.0
    for key, label in (("food", "Food"), ("transport", "Transport"),
                       ("accommodation", "Accommodation"), ("entrance", "Entrance Fee(s)")):
        ex = float((d.get("costs") or {}).get(key) or 0)
        gst = round(ex * 0.10, 2) if (key == "food" or not edu) else 0.0
        out[key] = {"label": label, "ex": ex, "gst": gst, "charge": round(ex + gst, 2)}
        total += ex + gst
    out["total"] = round(total, 2)
    return out


def _parse_date(v):
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _parse_time(v):
    if isinstance(v, time):
        return v
    try:
        h, m = str(v).split(":")[:2]
        return time(int(h), int(m))
    except Exception:
        return None


def all_activities(d: dict) -> list[dict]:
    return [GENERAL_ACTIVITY] + list(d.get("activities") or [])


def check_excursion(d: dict, staff_directory: list[dict] | None = None) -> list[tuple[str, str]]:
    """Return [(level, message)] where level is 'block', 'warn' or 'ok'.
    'block' = missing or not allowed – fix before printing for signature."""
    res: list[tuple[str, str]] = []
    add = lambda lvl, msg: res.append((lvl, msg))  # noqa: E731
    staff_directory = staff_directory or []

    # --- Required details ------------------------------------------------
    for key, label in (("name", "Name of excursion"), ("destination", "Destination"),
                       ("outline", "Outline of the excursion"), ("curriculum", "Curriculum links / outcomes"),
                       ("teacher_in_charge", "Teacher in charge"), ("site_contact", "Site-based contact person"),
                       ("site_contact_phone", "Site contact phone number")):
        if not str(d.get(key) or "").strip():
            add("block", f"{label} is missing.")

    d_from, d_to = _parse_date(d.get("date_from")), _parse_date(d.get("date_to") or d.get("date_from"))
    if not d_from:
        add("block", "Excursion date is missing.")
    else:
        if d_to and d_to < d_from:
            add("block", "The end date is before the start date.")
        if d_from < today_adl():
            add("warn", "The excursion date is in the past — check the date is correct.")
        if d_to and d_to > d_from:
            add("warn", "This runs over more than one day — overnight camps need extra planning "
                        "(sleeping arrangements, gender balance, camp site checks). Talk to Leadership.")
    t_dep, t_ret = _parse_time(d.get("depart_time")), _parse_time(d.get("return_time"))
    if t_dep and t_ret and (not d_to or d_to == d_from) and t_ret <= t_dep:
        add("block", "Return time is not after the departure time.")

    # --- Excluded activities --------------------------------------------
    text = " ".join([d.get("name", ""), d.get("outline", "")] + [a.get("name", "") for a in d.get("activities", [])]).lower()
    hits = [x for x in EXCLUDED_ACTIVITIES if x in text]
    if hits:
        add("block", "The DfE procedure does not permit some high-risk activities on excursions "
                     f"(matched: {', '.join(hits)}). Remove them or check with Leadership.")

    # --- Students and ratios ---------------------------------------------
    total = student_total(d)
    if total == 0:
        add("block", "No students entered.")
    staff = [s for s in d.get("staff", []) if str(s.get("name") or "").strip()]
    need, why = required_adults(d)
    if len(staff) < need:
        add("block", f"{len(staff)} adult(s) listed but at least {need} are needed. {why}.")
    elif total:
        add("ok", f"Ratio OK — {len(staff)} adults for {total} students (need {need}). {why}.")
    if int(d.get("min_at_once") or 0) < min(need, len(staff) or need):
        add("warn", "'Minimum number of adults at any one time' is lower than the ratio requires.")

    tic = (d.get("teacher_in_charge") or "").strip()
    if tic and tic not in [s.get("name") for s in staff]:
        add("block", "The teacher in charge must also be listed in the staff attending.")
    if tic:
        rec = next((s for s in staff if s.get("name") == tic), {})
        if rec and rec.get("status") not in ("Teacher", "Leader"):
            add("warn", "The procedure expects the teacher-in-charge to be a teacher.")

    if staff and not any(s.get("first_aid") for s in staff):
        add("block", "No attending adult has a current first aid qualification.")
    elif staff:
        add("ok", "At least one current first aider attending.")
    if d_from:
        for s in staff:
            rec = next((r for r in staff_directory if r.get("name") == s.get("name")), None)
            exp = _parse_date((rec or {}).get("first_aid_expiry"))
            if s.get("first_aid") and exp and exp < d_from:
                add("warn", f"{s['name']}'s first aid certificate on file expires {exp:%d/%m/%Y}, "
                            "before the excursion.")

    g_students = {("M" if int(x.get("male") or 0) else None) for x in d.get("students", [])} | \
                 {("F" if int(x.get("female") or 0) else None) for x in d.get("students", [])}
    g_students.discard(None)
    g_staff = {s.get("gender") for s in staff if s.get("gender") in ("M", "F")}
    if len(g_students) > 1 and len(g_staff) < 2:
        add("warn", "Mixed-gender student group without mixed-gender staff — the procedure requires mixed "
                    "gender supervisors unless parents have approved an alternative.")

    # --- Transport --------------------------------------------------------
    mode = d.get("transport_mode", "")
    if mode == "Chartered bus":
        if not (d.get("bus_company") and d.get("bus_accreditation")):
            add("block", "Chartered bus: the company name and accreditation number are required on the ED169.")
        if d.get("hvnl_aware") is False:
            add("block", "Chartered bus: the driver must be aware of the Heavy Vehicle National Law requirements.")
        if not d.get("driver_accreditation"):
            add("warn", "Chartered bus: add the driver accreditation, or collect it from the driver on arrival "
                        "and file it with the excursion.")
    if mode == "Private vehicle":
        pv = d.get("private_vehicles") or []
        if not pv or not all(v.get("owner") and v.get("rego") and v.get("insurance_category") for v in pv):
            add("block", "Private vehicle: owner, registration and insurance category are required for each vehicle.")
        add("warn", "Private vehicle: parental consent is needed for every passenger, and a staff member must "
                    "not transport a single student 1:1.")
    if mode == "Site car / government vehicle":
        vs = d.get("vehicles") or []
        if not vs and not d.get("vehicle_desc"):
            add("warn", "Choose which site vehicle(s) are being used.")
        for v in vs:
            if not (v.get("rego") or "").strip():
                add("warn", f"No rego recorded for {v.get('name')} – add it in ⚙️ Settings → Vehicles.")
        seats = [int(v.get("seats") or 0) for v in vs]
        if vs and all(seats):
            people = student_total(d) + len([x for x in d.get("staff", []) if x.get("name")])
            if people > sum(seats):
                add("warn", f"{people} people (students + adults) but only {sum(seats)} seats in the vehicle(s) chosen – "
                            "plan more than one trip or another vehicle.")
    if mode == "Public transport (bus / train / tram)":
        add("ok", "Public transport: a CLC staff member must travel in each vehicle with students.")

    # --- Activities & risk -----------------------------------------------
    acts = d.get("activities") or []
    if not acts:
        add("block", "Add at least one activity (e.g. the transport and the venue) to the risk assessment.")
    transport_acts = [a for a in acts if (a.get("category") == "Transport")]
    if mode != "Walking only" and acts and not transport_acts:
        add("warn", "No travel activity in the risk assessment — add the transport you are using.")
    flags = {}
    for a in acts:
        for k, v in (a.get("flags") or {}).items():
            flags[k] = flags.get(k) or v
        if not str(a.get("name") or "").strip():
            add("block", "An activity has no name.")
        if not a.get("risks"):
            add("block", f"'{a.get('name') or 'New activity'}' has no risks listed.")
        for r in a.get("risks", []):
            lbl = f"'{a.get('name') or 'New activity'}': {(r.get('hazard') or 'a risk')[:50]}"
            if not str(r.get("hazard") or "").strip():
                add("block", f"'{a.get('name') or 'New activity'}' has a risk with no description.")
                continue
            if not str(r.get("controls") or "").strip() or not str(r.get("procedure") or "").strip():
                add("block", f"{lbl} — needs both prevention strategies and a procedure if it occurs.")
            lvl = risk_level(r.get("likelihood"), r.get("consequence"))
            if lvl == "Extreme":
                add("block", f"{lbl} is rated EXTREME. Add controls to lower the likelihood, or change the plan.")
            elif lvl == "High":
                add("warn", f"{lbl} is rated HIGH — talk this through with Leadership when the forms are signed.")

    if flags.get("aquatic"):
        add("warn", "Water is involved — plans must cover a student falling into the water, and the ratio must "
                    "come from the risk assessment (consider extra staff).")
    if d_from and d_from.month in BUSHFIRE_MONTHS and (flags.get("bushfire") or d.get("bushfire_area")):
        add("warn", "Bushfire season (Nov–Apr): check the CFS 4-day fire danger rating; cancel on a total fire "
                    "ban day or if a fire threatens the area. Tell parents the emergency plan.")
    if flags.get("national_park") or d.get("national_park"):
        add("warn", "State/national park: liaise with the ranger and notify the National Parks SA office.")

    # --- Pre-departure checks -------------------------------------------
    missing = [label for key, label in PRE_CHECKS if not (d.get("checks") or {}).get(key)]
    if missing:
        add("warn", f"{len(missing)} preparation check(s) not ticked yet: " + "; ".join(missing))
    else:
        add("ok", "All preparation checks ticked.")
    if not d.get("venue_reviewed"):
        add("warn", "Venue and safety information not marked as reviewed.")
    if (d.get("student_considerations") or "").strip():
        words = [w for w in d["student_considerations"].replace(",", " ").split() if w.istitle() and len(w) > 3]
        if words:
            add("warn", "Individual student notes may contain full names — use initials only.")
    return res


def is_complete(checks: list[tuple[str, str]]) -> bool:
    return not any(lvl == "block" for lvl, _ in checks)


def highest_level(d: dict) -> str:
    lv = "Low"
    for a in all_activities(d):
        for r in a.get("risks", []):
            x = risk_level(r.get("likelihood"), r.get("consequence"))
            if LEVEL_ORDER[x] > LEVEL_ORDER[lv]:
                lv = x
    return lv


def fmt_date(v) -> str:
    dd = _parse_date(v)
    return dd.strftime("%d/%m/%Y") if dd else ""


def fmt_time(v) -> str:
    t = _parse_time(v)
    return t.strftime("%I:%M %p").lstrip("0") if t else ""


def transport_text(d: dict) -> str:
    mode = d.get("transport_mode", "")
    if mode == "Site car / government vehicle":
        vs = d.get("vehicles") or []
        if vs:
            return f"{mode} – " + "; ".join(v.get("name", "") + (f" (rego {v['rego']})" if v.get("rego") else "")
                                             for v in vs)
        if d.get("vehicle_desc"):
            return f"{mode} – {d['vehicle_desc']}"
    if mode == "Chartered bus" and d.get("bus_company"):
        return f"{mode} – {d['bus_company']}"
    return mode


def emergency_text(d: dict) -> list[str]:
    lines = [
        f"Site-based contact: {d.get('site_contact', '')} – {d.get('site_contact_phone', '')}. "
        "Contacted immediately for support or pick-up.",
        f"Call-in procedure: {d.get('call_in', '')}",
        "Mobile phone(s) carried at all times; first aid kit and required medication carried.",
        "Serious injury/illness: first aid and call 000; then contact the site contact.",
        "Missing student: follow the attached risk assessment – contact CLC Leadership, SAPOL and parent/carer.",
        "Parents/carers contacted and pick-up arranged if required. Outside agency support if required.",
        "All incidents reported to Leadership on return (IRMS / ABCH as required).",
    ]
    if (d.get("emergency_extra") or "").strip():
        lines.append(d["emergency_extra"].strip())
    lines.append("All adults on the excursion have this information. See attached Risk Management Plan.")
    return lines


# =====================================================================
# Word documents
# =====================================================================
def _docx():
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    return Document, WD_ORIENT, WD_TABLE_ALIGNMENT, WD_ALIGN_PARAGRAPH, OxmlElement, qn, Cm, Pt, RGBColor


def _shade(cell, hex_fill):
    _, _, _, _, OxmlElement, qn, *_ = _docx()
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _repeat_header(row):
    _, _, _, _, OxmlElement, qn, *_ = _docx()
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _cell(cell, text, bold=False, size=9.5, fill=None, colour=None, italic=False):
    *_, Pt, RGBColor = _docx()
    cell.text = ""
    lines = str(text if text is not None else "").split("\n")
    p = cell.paragraphs[0]
    for i, line in enumerate(lines):
        if i:
            p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(0)
        run = p.add_run(line)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size)
        if colour:
            run.font.color.rgb = RGBColor.from_string(colour)
    if fill:
        _shade(cell, fill)
    return cell


def _base_doc(landscape=False, draft=False):  # draft kept for compatibility – no longer used
    Document, WD_ORIENT, _, WD_ALIGN_PARAGRAPH, _, _, Cm, Pt, RGBColor = _docx()
    doc = Document()
    st_ = doc.styles["Normal"]
    st_.font.name = "Arial"
    st_.font.size = Pt(10)
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(1.5))
    sec.top_margin = sec.bottom_margin = Cm(1.4)
    if draft:
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = hp.add_run("DRAFT – NOT YET APPROVED BY LEADERSHIP")
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(0xC6, 0x28, 0x28)
    return doc


def _heading(doc, text, size=12, colour="1A7A7A", space_before=8):
    *_, Pt, RGBColor = _docx()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(colour)
    return p


def _para(doc, text, bold=False, size=10, italic=False, after=3):
    *_, Pt, RGBColor = _docx()
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size = Pt(size)
    return p


def _kv_table(doc, rows, widths=(5.5, 12.5)):
    *_, Cm, Pt, RGBColor = _docx()
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in rows:
        c = t.add_row().cells
        _cell(c[0], k, bold=True, fill="E8F2F2")
        _cell(c[1], v)
    for row in t.rows:
        row.cells[0].width, row.cells[1].width = Cm(widths[0]), Cm(widths[1])
    return t


def _box(b: bool) -> str:
    return "☒" if b else "☐"


def _build_ed169_recreated(row: dict) -> bytes:
    """Fallback only (template file missing): ED169 rebuilt with the DfE wording."""
    d = row.get("data") or {}
    Document, _, _, WD_ALIGN_PARAGRAPH, _, _, Cm, Pt, RGBColor = _docx()
    doc = _base_doc()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("APPLICATION TO CONDUCT A CAMP OR EXCURSION")
    r.bold = True
    r.font.size = Pt(14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("(Requirements in this document must not be altered. Please use block letters when filling out this form)")
    r.italic = True
    r.font.size = Pt(8.5)

    _heading(doc, "APPLICATION FOR EDUCATION EXCURSIONS:", size=10, colour="000000")
    for line in [
        "INTRASTATE TRAVEL (Approved by PRINCIPAL/PRESCHOOL DIRECTOR)",
        "INTERSTATE TRAVEL/INTERSTATE USE OF DEPARTMENTAL VEHICLES (Approved by EDUCATION DIRECTOR) "
        "(excluding departmentally owned yellow school buses, specific approval requirements from Minister's "
        "delegate - contact Transport Services Unit)",
        "OVERSEAS TRAVEL (Approved by CHIEF EXECUTIVE through EXECUTIVE DIRECTOR, PARTNERSHIPS, SCHOOLS AND "
        "PRESCHOOLS). Refer to overseas travel policy and procedures",
    ]:
        _para(doc, f"{_box(line.startswith('INTRASTATE'))}  {line}", size=8.5, after=1)

    _kv_table(doc, [
        ("SCHOOL/PRESCHOOL NAME:", "COWANDILLA LEARNING CENTRE"),
        ("NAME OF EXCURSION:", (d.get("name") or "").upper()),
        ("DESTINATION:", ((d.get("destination") or "") + (f" – {d['address']}" if d.get("address") else "")).upper()),
    ])

    _heading(doc, "NATURE OF EXCURSION", size=10, colour="000000")
    _kv_table(doc, [
        ("(a) Provide an outline of the excursion, including places to be visited and a program of proposed "
         "activities.", d.get("outline") or ""),
        ("(b) Curriculum Links/Outcomes\nMust show specifically how it links with or obtains outcomes of the "
         "curriculum for this year level eg: stating from Curriculum Statements, syllabus etc.", d.get("curriculum") or ""),
    ], widths=(7, 11))
    df, dt = fmt_date(d.get("date_from")), fmt_date(d.get("date_to") or d.get("date_from"))
    _kv_table(doc, [("(c) Dates (Inclusive)", f"On: {df}" if df == dt else f"From: {df}   to: {dt}")])

    # --- Costs + students ---------------------------------------------
    _heading(doc, "BREAKDOWN OF COSTS AND CHARGES", size=10, colour="000000")
    _para(doc, "If the camp/excursion is:\n- predominantly educational, GST must be added to the food charge, but "
               "all other charges to students are GST-free\n- not predominantly educational, eg predominantly "
               "recreational, GST must be added to all student charges.", size=8.5)
    cb = cost_breakdown(d)
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["", "GST exclusive cost per student", "10% GST (only where applicable)", "Charge to student"]):
        _cell(c, h, bold=True, fill="E8F2F2", size=8.5)
    for key in ("food", "transport", "accommodation", "entrance"):
        x = cb[key]
        c = t.add_row().cells
        _cell(c[0], x["label"], bold=True)
        _cell(c[1], f"${x['ex']:.2f}")
        _cell(c[2], f"${x['gst']:.2f}")
        _cell(c[3], f"${x['charge']:.2f}")
    c = t.add_row().cells
    _cell(c[0], "Total charge to student", bold=True)
    c[1].merge(c[3])
    _cell(c[1], f"${cb['total']:.2f}", bold=True)

    _heading(doc, "NUMBER AND YEAR LEVEL(S) OF STUDENTS INVOLVED", size=10, colour="000000")
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["Year Level", "Male", "Female", "Total"]):
        _cell(c, h, bold=True, fill="E8F2F2")
    for s in d.get("students", []):
        m, f, o = int(s.get("male") or 0), int(s.get("female") or 0), int(s.get("other") or 0)
        if not (m or f or o):
            continue
        c = t.add_row().cells
        _cell(c[0], s.get("year"))
        _cell(c[1], m or "")
        _cell(c[2], f or "")
        _cell(c[3], m + f + o)
    c = t.add_row().cells
    _cell(c[0], "Total number of students", bold=True)
    c[1].merge(c[3])
    _cell(c[1], student_total(d), bold=True)

    # --- Staff ---------------------------------------------------------
    _heading(doc, "TEACHERS AND OTHER LEADERS' QUALIFICATIONS AND RELEVANT EXPERIENCE", size=10, colour="000000")
    _kv_table(doc, [("Teacher in Charge", d.get("teacher_in_charge") or "")])
    _para(doc, "Other Teachers and Leaders", bold=True, size=9, after=1)
    t = doc.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["Name(s)", "Male/ Female",
                                      "Status: teacher, SSO, student, instructor, parent, volunteer, etc",
                                      "Qualifications and experiences in proposed activities",
                                      "Current first aid qualification (in past 3 years)"]):
        _cell(c, h, bold=True, fill="E8F2F2", size=8.5)
    staff = [s for s in d.get("staff", []) if s.get("name")]
    for s in staff:
        c = t.add_row().cells
        _cell(c[0], s.get("name"))
        _cell(c[1], s.get("gender") or "")
        _cell(c[2], s.get("status") or "")
        _cell(c[3], s.get("experience") or "Y")
        _cell(c[4], "Y" if s.get("first_aid") else "N")
    _kv_table(doc, [("Total number of teachers and leaders", str(len(staff))),
                    ("Minimum number at any one time", str(d.get("min_at_once") or ""))])

    _heading(doc, "SCHOOL/PRESCHOOL-BASED CONTACT PERSON DURING CAMP/EXCURSION", size=10, colour="000000")
    _para(doc, f"{d.get('site_contact', '')}    Ph: {d.get('site_contact_phone', '')}")

    _heading(doc, "EMERGENCY ACTION", size=10, colour="000000")
    _para(doc, "Detail the plan for emergency action should the need arise. All teachers and leaders involved in "
               "the program should have this information. (Attach Risk Management Form)", size=8.5, italic=True)
    for line in emergency_text(d):
        _para(doc, f"• {line}", size=9.5, after=1)

    # --- Travel --------------------------------------------------------
    _heading(doc, "TRAVEL ARRANGEMENTS", size=10, colour="000000")
    mode = d.get("transport_mode", "")
    mode_txt = transport_text(d)
    _kv_table(doc, [
        ("(a) Intrastate/Interstate Travel – Mode of travel to be used", mode_txt),
        ("Departure time / return time", f"{fmt_time(d.get('depart_time'))}  and return time  {fmt_time(d.get('return_time'))}"),
        ("Name of bus company/tour operator/airline", d.get("bus_company") if mode == "Chartered bus" else "N/A"),
        ("Phone No", d.get("bus_phone") if mode == "Chartered bus" else ""),
        ("Company / driver accreditation", (f"Company: {d.get('bus_accreditation', '')}   Driver: {d.get('driver_accreditation', '')}"
                                            if mode == "Chartered bus" else "N/A")),
    ], widths=(7, 11))
    _para(doc, "Private vehicle/name of owner/registration number (Insurance category: Third party property or comprehensive)",
          size=8.5, after=1)
    t = doc.add_table(rows=1, cols=6)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["Name of Owner", "Accreditation No", "Registration No",
                                      "Safety label certificate expiry date", "Insurance Category",
                                      "Name of Insuring Company"]):
        _cell(c, h, bold=True, fill="E8F2F2", size=8)
    pvs = (d.get("private_vehicles") or []) if mode == "Private vehicle" else []
    for v in pvs or [{}]:
        c = t.add_row().cells
        for i, k in enumerate(["owner", "accreditation", "rego", "safety_label_expiry", "insurance_category", "insurer"]):
            _cell(c[i], v.get(k, "") if pvs else ("N/A" if i == 0 else ""))
    _para(doc, "(b) Overseas Travel – provide a detailed itinerary of all travel arrangements for excursion. "
               "Attach separate sheets including overseas travel proposals (FORM NP11) completed by each "
               "departmental employee.    N/A", size=8.5)
    _para(doc, "(c) Charter air travel – indicate why charter air travel is required.    N/A", size=8.5)

    _kv_table(doc, [("Signature – Teacher-in-charge", ""), ("Date", "")])

    # --- Approvals -----------------------------------------------------
    _heading(doc, "APPROVALS", size=11, colour="000000")
    _para(doc, "PRINCIPAL/DIRECTOR APPROVAL FOR CAMP/EXCURSION", bold=True, size=9.5)
    _para(doc, "Based on the stated curriculum links/outcomes, I certify that this camp/excursion is predominantly "
               f"educational     {_box(False)} Yes   {_box(False)} No", size=9.5)
    _kv_table(doc, [("Signature – Principal/Director", ""), ("Date", "")])
    _para(doc, "FOR INTERSTATE TRAVEL/USE OF DEPARTMENTAL VEHICLES/BUSES INTERSTATE", bold=True, size=9.5)
    _kv_table(doc, [("Approved/not approved – Education Director", "Not applicable – intrastate excursion")])
    _para(doc, "FOR OVERSEAS TRAVEL REFER TO OVERSEAS TRAVEL POLICY & PROCEDURES", bold=True, size=9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_risk_assessment(row: dict) -> bytes:
    """CLC Risk Management Plan and Approval to Transport (layout of the current CLC template)."""
    d = row.get("data") or {}
    Document, _, WD_TABLE_ALIGNMENT, WD_ALIGN_PARAGRAPH, _, _, Cm, Pt, RGBColor = _docx()
    doc = _base_doc(landscape=True)

    prog = d.get("program") or ""
    _heading(doc, f"Risk Management Plan and Approval to Transport – CLC {prog if prog in ('JP', 'PY', 'SY') else ''}".strip(),
             size=15, space_before=0)
    _para(doc, f"Excursion Destination: {d.get('destination', '')}" + (f" – {d['address']}" if d.get("address") else ""),
          bold=True, size=11)

    _heading(doc, "Excursion Details", size=11)
    staff = [s for s in d.get("staff", []) if s.get("name")]
    fa = [s["name"] for s in staff if s.get("first_aid")]
    yrs = ", ".join(sorted({str(s.get('year')) for s in d.get('students', [])
                            if int(s.get('male') or 0) + int(s.get('female') or 0) + int(s.get('other') or 0)},
                           key=lambda y: year_num(y)))
    need, why = required_adults(d)
    det = [
        ("Excursion", d.get("name", "")),
        ("Date and times", f"{fmt_date(d.get('date_from'))}  •  depart CLC {fmt_time(d.get('depart_time'))}  •  "
                           f"return {fmt_time(d.get('return_time'))}"),
        ("Program / students", f"{prog}  •  {student_total(d)} students (Year {yrs})"),
        ("Staff attending", ", ".join(f"{s['name']} ({s.get('status', '')})" for s in staff)),
        ("Teacher in charge", d.get("teacher_in_charge", "")),
        ("Ratio", f"{len(staff)} adults : {student_total(d)} students (minimum required {need}; {why})"),
        ("First aiders", ", ".join(fa) or "—"),
        ("Transport", transport_text(d)),
        ("Site contact", f"{d.get('site_contact', '')} – {d.get('site_contact_phone', '')}"),
        ("Call-in procedure", d.get("call_in", "")),
    ]
    if (d.get("student_considerations") or "").strip():
        det.append(("Individual student considerations (initials only)", d["student_considerations"]))
    _kv_table(doc, det, widths=(6, 20.7))

    _heading(doc, "Risk Assessment:", size=11)
    t = doc.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    heads = ["Activity", "Potential Risk", "Level of Risk**\n(Likelihood x Consequence)",
             "Proactive Strategies to prevent / reduce\n(including whom is responsible)",
             "Procedure to Follow if occurs\n(including whom is responsible)"]
    for c, h in zip(t.rows[0].cells, heads):
        _cell(c, h, bold=True, fill="1A7A7A", colour="FFFFFF", size=9)
    _repeat_header(t.rows[0])
    widths = [Cm(4.0), Cm(4.6), Cm(3.4), Cm(7.6), Cm(7.1)]
    for a in all_activities(d):
        risks = a.get("risks") or []
        first_row_idx = len(t.rows)
        for i, r in enumerate(risks):
            lvl = risk_level(r.get("likelihood"), r.get("consequence"))
            c = t.add_row().cells
            _cell(c[0], a.get("name", "") if i == 0 else "", bold=True)
            _cell(c[1], r.get("hazard", ""))
            _cell(c[2], f"{lvl}\n({r.get('likelihood')} x {r.get('consequence')})", bold=False,
                  fill=LEVEL_FILL.get(lvl))
            c[2].paragraphs[0].runs[0].bold = True
            _cell(c[3], (r.get("controls") or "").replace("- ", "• "))
            _cell(c[4], (r.get("procedure") or "").replace("- ", "• "))
        if len(risks) > 1:
            top = t.rows[first_row_idx].cells[0]
            bottom = t.rows[len(t.rows) - 1].cells[0]
            txt = top.text
            merged = top.merge(bottom)
            _cell(merged, txt, bold=True)
    for row_ in t.rows:
        for i, w in enumerate(widths):
            row_.cells[i].width = w

    _para(doc, "", after=2)
    _para(doc, "Note: To assess degree of risk use the notes on the matrix on next page. Level of risk is rated with "
               "the proactive strategies in place.", size=8.5, italic=True)
    sign = [
        ("Venue and safety information reviewed and attached.", "Yes" if d.get("venue_reviewed") else "No"),
        ("Prepared By:", d.get("prepared_by") or d.get("teacher_in_charge", "")),
        ("Consultation with Manager/ Line Manager (if relevant):", ""),
        ("Manager / Line Manager signature and date:", ""),
        ("Developed / Reviewed:", fmt_date(row.get("updated_at")) or fmt_date(today_adl())),
    ]
    _kv_table(doc, sign, widths=(9, 17.7))

    # --- Matrix page ------------------------------------------------------
    doc.add_page_break()
    _heading(doc, "Notes on analysing risks for excursions", size=12, space_before=0)
    _para(doc, "Assess the likelihood that the event will occur, and the seriousness of the consequences if it "
               "does, using the table below. Then use the grid on the previous page to identify level of risk.", size=9)
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ["Likelihood", "", "Consequence", ""]):
        _cell(c, h, bold=True, fill="E8F2F2")
    for like, cons in zip(reversed(LIKELIHOOD), reversed(CONSEQUENCE)):
        c = t.add_row().cells
        _cell(c[0], like, bold=True)
        _cell(c[1], LIKELIHOOD_HELP[like], size=8.5)
        _cell(c[2], cons, bold=True)
        _cell(c[3], "\n".join(f"• {x}" for x in CONSEQUENCE_HELP[cons]), size=8.5)
    for row_ in t.rows:
        for i, w in enumerate([Cm(3), Cm(6.5), Cm(3), Cm(14.2)]):
            row_.cells[i].width = w

    _heading(doc, "Level of Risk", size=11)
    t = doc.add_table(rows=1, cols=6)
    t.style = "Table Grid"
    _cell(t.rows[0].cells[0], "Consequence \\ Likelihood", bold=True, fill="E8F2F2", size=8.5)
    for i, like in enumerate(LIKELIHOOD):
        _cell(t.rows[0].cells[i + 1], like, bold=True, fill="E8F2F2")
    for cons in reversed(CONSEQUENCE):
        c = t.add_row().cells
        _cell(c[0], cons, bold=True)
        for i, lvl in enumerate(MATRIX[cons]):
            _cell(c[i + 1], lvl, fill=LEVEL_FILL[lvl])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def doc_filename(row: dict, kind: str) -> str:
    d = row.get("data") or {}
    dd = _parse_date(d.get("date_from"))
    stamp = dd.strftime("%d-%m-%y") if dd else "undated"
    dest = "".join(ch for ch in (d.get("destination") or d.get("name") or "Excursion") if ch.isalnum() or ch in " -")
    dest = "_".join(dest.split())[:40]
    return f"{stamp}_{dest}_{kind}.docx"


# =====================================================================
# ED169 — fill the official DfE form (data/excursions/ED169_template.docx)
# =====================================================================
ED169_TEMPLATE_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "excursions", "ED169_template.docx"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "excursions", "ED169_template.docx"),
]

# Cost + year-level grid: one tuple per row of the form → (ex GST, GST, charge, year, male, female, total)
_COST_ROWS = [
    ("Text22", "Text1", "Text2", "Text23", "Text3", "Text4", "Text12"),       # Food
    ("Text13", "Text14", "Text15", "Text16", "Text17", "Text18", "Text21"),   # Transport
    ("Text24", "Text36", "Text37", "Text38", "Text39", "Text40", "Text41"),   # Accommodation
    ("Text42", "Text43", "Text44", "Text45", "Text46", "Text47", "Text48"),   # Entrance fee(s)
    ("Text50", "Text51", "Text52", "Text53", "Text54", "Text55", "Text56"),   # blank row
    ("Text58", "Text59", "Text60", "Text61", "Text62", "Text63", "Text64"),   # blank row
]
_STAFF_ROWS = [("Text6", "Text7", "Text8", "Text9", "Text10"), ("Text67", "Text68", "Text69", "Text70", "Text71"),
               ("Text72", "Text73", "Text74", "Text75", "Text76"), ("Text77", "Text78", "Text79", "Text80", "Text81")]
_PV_ROWS = [("Text88", "Text89", "Text90", "Text91", "Text92", "Text93"),
            ("Text94", "Text95", "Text96", "Text97", "Text98", "Text99"),
            ("Text100", "Text101", "Text102", "Text103", "Text104", "Text105")]
_DRIVER_ROWS = [("Text106", "Text107", "Text108"), ("Text109", "Text110", "Text111"), ("Text112", "Text113", "Text114")]


def _data_file(name: str) -> str | None:
    for base in (os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        p = os.path.join(base, "data", "excursions", name)
        if os.path.exists(p):
            return p
    return None


LOGO_HEIGHT_CM = 2.1


def _insert_site_logo(doc) -> None:
    """Put the CLC logo into the form's 'INSERT SITE LOGO' text box (and drop the box outline)."""
    logo = _data_file("clc_logo.png")
    if not logo:
        return
    from docx.oxml.ns import qn
    from docx.shared import Cm
    from docx.text.paragraph import Paragraph
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    for txbx in doc.element.body.iter(qn("w:txbxContent")):
        text = "".join(t.text or "" for t in txbx.iter(qn("w:t")))
        if "INSERT SITE LOGO" not in text.upper():
            continue
        ps = txbx.findall(qn("w:p"))
        for extra in ps[1:]:
            txbx.remove(extra)
        p_el = ps[0]
        for r in p_el.findall(qn("w:r")):
            p_el.remove(r)
        para = Paragraph(p_el, doc._body)
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = para.paragraph_format
        pf.space_before = pf.space_after = 0
        para.add_run().add_picture(logo, height=Cm(LOGO_HEIGHT_CM))
        # remove the text box outline
        wsp = txbx
        while wsp is not None and not wsp.tag.endswith("}wsp"):
            wsp = wsp.getparent()
        # make the text box tall enough for the logo
        anchor = txbx
        while anchor is not None and not anchor.tag.endswith("}anchor") and not anchor.tag.endswith("}inline"):
            anchor = anchor.getparent()
        if anchor is not None:
            new_cy = str(int(Cm(LOGO_HEIGHT_CM + 0.35)))
            new_cx = str(int(Cm(LOGO_HEIGHT_CM * 0.76 + 0.5)))      # logo is ~0.76 wide:tall
            targets = [c for c in anchor if c.tag.endswith("}extent")]          # the box's own size
            if wsp is not None:
                A_ = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
                for sp in wsp.findall("{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}spPr"):
                    targets += [e for xf in sp.findall(A_ + "xfrm") for e in xf.findall(A_ + "ext")]
            for ext in targets:
                ext.set("cy", new_cy)
                ext.set("cx", new_cx)
            for bp in anchor.iter("{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}bodyPr"):
                for k in ("tIns", "bIns", "lIns", "rIns"):
                    bp.set(k, "0")
        if wsp is not None:
            A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
            for sp in wsp.iter("{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}spPr"):
                for fill in [c for c in sp if c.tag in (A + "solidFill", A + "noFill", A + "gradFill")]:
                    sp.remove(fill)
                from docx.oxml import OxmlElement as _OE
                nf = _OE("a:noFill")
                geom = sp.find(A + "prstGeom")
                (geom.addnext(nf) if geom is not None else sp.append(nf))
            for ln in wsp.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}ln"):
                for ch in list(ln):
                    ln.remove(ch)
                from docx.oxml import OxmlElement
                ln.append(OxmlElement("a:noFill"))
        break


def ed169_template_path() -> str | None:
    return next((p for p in ED169_TEMPLATE_PATHS if os.path.exists(p)), None)


class _FormFiller:
    """Fills legacy Word form fields (FORMTEXT / FORMCHECKBOX / FORMDROPDOWN) in place, keeping them live."""

    def __init__(self, doc):
        from docx.oxml.ns import qn
        self.qn = qn
        self.doc = doc
        self.fields = {}
        for fc in doc.element.body.iter(qn("w:fldChar")):
            if fc.get(qn("w:fldCharType")) != "begin":
                continue
            ff = fc.find(qn("w:ffData"))
            nm = ff.find(qn("w:name")) if ff is not None else None
            if nm is not None:
                self.fields.setdefault(nm.get(qn("w:val")), fc)

    def text(self, name: str, value, upper: bool = False):
        import copy as _copy
        from docx.oxml import OxmlElement
        qn = self.qn
        fc = self.fields.get(name)
        if fc is None or value is None:
            return
        value = str(value)
        if upper:
            value = value.upper()
        run = fc.getparent()                       # w:r holding fldChar begin
        sib = run.getnext()
        sep_run, result = None, []
        while sib is not None:                     # find separate, collect result runs until end
            fcs = sib.findall(qn("w:fldChar")) if sib.tag == qn("w:r") else []
            kind = fcs[0].get(qn("w:fldCharType")) if fcs else None
            if sep_run is None:
                if kind == "separate":
                    sep_run = sib
            else:
                if kind == "end":
                    break
                result.append(sib)
            sib = sib.getnext()
        if sep_run is None:
            return
        rpr = None
        for r in result + [sep_run]:
            x = r.find(qn("w:rPr")) if r.tag == qn("w:r") else None
            if x is not None:
                rpr = _copy.deepcopy(x)
                break
        for r in result:
            r.getparent().remove(r)
        new = OxmlElement("w:r")
        if rpr is not None:
            for tag in ("w:vanish", "w:color"):
                for v in rpr.findall(qn(tag)):
                    rpr.remove(v)
            new.append(rpr)
        for i, line in enumerate(value.split("\n")):
            if i:
                new.append(OxmlElement("w:br"))
            t = OxmlElement("w:t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = line
            new.append(t)
        sep_run.addnext(new)

    def check(self, name: str, on: bool):
        from docx.oxml import OxmlElement
        qn = self.qn
        fc = self.fields.get(name)
        if fc is None:
            return
        cb = fc.find(qn("w:ffData")).find(qn("w:checkBox"))
        if cb is None:
            return
        for tag in ("w:checked",):
            for x in cb.findall(qn(tag)):
                cb.remove(x)
        el = OxmlElement("w:checked")
        el.set(qn("w:val"), "1" if on else "0")
        cb.append(el)

    def dropdown(self, name: str, option: str):
        from docx.oxml import OxmlElement
        qn = self.qn
        fc = self.fields.get(name)
        if fc is None:
            return
        dd = fc.find(qn("w:ffData")).find(qn("w:ddList"))
        if dd is None:
            return
        opts = [e.get(qn("w:val")) for e in dd.findall(qn("w:listEntry"))]
        if option not in opts:
            return
        for x in dd.findall(qn("w:result")):
            dd.remove(x)
        res = OxmlElement("w:result")
        res.set(qn("w:val"), str(opts.index(option)))
        dd.insert(0, res)


def _grid(table):
    """Single-line borders without relying on the 'Table Grid' style (the DfE template doesn't have it)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)


def _write_cell(cell, text: str, size: float = 9, bold: bool = False, italic: bool = False):
    from docx.shared import Pt
    lines = str(text).split("\n")
    p = cell.paragraphs[0]
    for i, line in enumerate(lines):
        if i:
            p = cell.add_paragraph()
        r = p.add_run(line)
        r.font.size = Pt(size)
        r.font.name = "Arial"
        r.bold, r.italic = bold, italic


def _row_grow(row):
    """Let a fixed-height row grow to fit its text."""
    from docx.oxml.ns import qn
    trPr = row._tr.get_or_add_trPr()
    for h in trPr.findall(qn("w:trHeight")):
        h.set(qn("w:hRule"), "atLeast")


def build_ed169(row: dict) -> bytes:
    """Fill the official DfE ED169 (Updated 08/20). Falls back to the rebuilt version if the template is missing."""
    path = ed169_template_path()
    if not path:
        return _build_ed169_recreated(row)
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    d = row.get("data") or {}
    doc = Document(path)
    try:
        _insert_site_logo(doc)
    except Exception:
        pass
    f = _FormFiller(doc)

    # ---- header details --------------------------------------------------
    f.text("Text35", "Cowandilla Learning Centre", upper=True)
    f.text("Text25", d.get("name", ""), upper=True)
    f.text("Text26", (d.get("destination") or "") + (f", {d['address']}" if d.get("address") else ""), upper=True)
    f.text("Text27", d.get("outline", ""))
    f.text("Text28", d.get("curriculum", ""))

    d_from = _parse_date(d.get("date_from"))
    d_to = _parse_date(d.get("date_to")) or d_from
    if d_from and d_to and d_to != d_from:
        for (dn, mn, yn), dd in ((("Unnamed", "Unnamed Copy 1", "Unnamed Copy 2"), d_from),
                                 (("Unnamed Copy 3", "Unnamed Copy 4", "Unnamed Copy 5"), d_to)):
            f.text(dn, f"{dd:%d}"); f.text(mn, f"{dd:%m}"); f.text(yn, f"{dd:%y}")
    elif d_from:
        f.text("Text29", f"{d_from:%d}"); f.text("Text30", f"{d_from:%m}"); f.text("Text31", f"{d_from:%Y}")

    # ---- costs + students -----------------------------------------------
    cb = cost_breakdown(d)
    for i, key in enumerate(("food", "transport", "accommodation", "entrance")):
        x = cb[key]
        if x["ex"] or x["charge"]:
            f.text(_COST_ROWS[i][0], f"${x['ex']:.2f}")
            f.text(_COST_ROWS[i][1], f"${x['gst']:.2f}")
            f.text(_COST_ROWS[i][2], f"${x['charge']:.2f}")
    f.text("Text65", f"{cb['total']:.2f}")
    students = [s for s in d.get("students", [])
                if int(s.get("male") or 0) + int(s.get("female") or 0) + int(s.get("other") or 0)]
    students.sort(key=lambda s: year_num(s.get("year", "0")))
    extra_students = students[len(_COST_ROWS):]
    for i, s in enumerate(students[:len(_COST_ROWS)]):
        m, fe, o = int(s.get("male") or 0), int(s.get("female") or 0), int(s.get("other") or 0)
        f.text(_COST_ROWS[i][3], s.get("year"))
        f.text(_COST_ROWS[i][4], m or "")
        f.text(_COST_ROWS[i][5], fe or "")
        f.text(_COST_ROWS[i][6], m + fe + o)
    f.text("Text66", student_total(d))

    # ---- staff -------------------------------------------------------------
    f.text("Text5", d.get("teacher_in_charge", ""), upper=True)
    staff = [s for s in d.get("staff", []) if s.get("name")]
    for i, s in enumerate(staff[:len(_STAFF_ROWS)]):
        nm, g, stt, q, fa = _STAFF_ROWS[i]
        f.text(nm, s.get("name", ""), upper=True)
        f.text(g, s.get("gender", ""))
        f.text(stt, s.get("status", ""))
        f.text(q, s.get("experience") or "Y")
        f.text(fa, "Y" if s.get("first_aid") else "N")
    extra_staff = staff[len(_STAFF_ROWS):]
    f.text("Text3 Copy 1", len(staff))
    f.text("Text3 Copy 2", d.get("min_at_once") or "")

    f.text("Text82", f"{d.get('site_contact', '')}  Ph: {d.get('site_contact_phone', '')}", upper=True)

    # ---- travel ------------------------------------------------------------
    mode = d.get("transport_mode", "")
    f.text("Text11", transport_text(d), upper=True)
    for (hn, mn, dn), tv in ((("Unnamed Copy 6", "Unnamed Copy 7", "Dropdown1"), d.get("depart_time")),
                             (("Unnamed Copy 8", "Unnamed Copy 9", "Dropdown83"), d.get("return_time"))):
        t = _parse_time(tv)
        if t:
            h12 = t.hour % 12 or 12
            f.text(hn, f"{h12:02d}"); f.text(mn, f"{t.minute:02d}")
            f.dropdown(dn, "am" if t.hour < 12 else "pm")
    if mode == "Chartered bus":
        f.text("Text12 Copy 1", d.get("bus_company", ""), upper=True)
        if d.get("bus_accreditation"):
            f.text("Text12 Copy 2", f"Company accreditation no: {d['bus_accreditation']}")
        f.text("Text20", d.get("bus_phone", ""))
        if d.get("hvnl_aware") is not None:
            f.check("Check84", d["hvnl_aware"] is True); f.check("Check85", d["hvnl_aware"] is False)
        if d.get("freeway_aware") is not None:
            f.check("Check86", d["freeway_aware"] is True); f.check("Check87", d["freeway_aware"] is False)
        f.text("Text12 Copy 3", d.get("last_heavy_vehicle", ""))
        if d.get("driver_name") or d.get("driver_accreditation") or d.get("driver_licence"):
            f.text("Text106", d.get("driver_name", ""), upper=True)
            f.text("Text107", d.get("driver_accreditation", ""))
            f.text("Text108", d.get("driver_licence", ""))
    if mode == "Private vehicle":
        for i, v in enumerate((d.get("private_vehicles") or [])[:len(_PV_ROWS)]):
            for fld, k in zip(_PV_ROWS[i], ("owner", "accreditation", "rego", "safety_label_expiry",
                                            "insurance_category", "insurer")):
                f.text(fld, v.get(k, ""), upper=(k == "owner"))

    # ---- emergency action (cell under the instruction – no form field there) ----
    try:
        _row_grow(doc.tables[7].rows[1])
        _write_cell(doc.tables[7].rows[1].cells[0], "\n".join(f"• {x}" for x in emergency_text(d)), size=9)
    except Exception:
        pass

    # ---- signatures + approval: left blank – the form is printed and signed by hand ----

    # ---- attachment sheet if more staff / year levels than the form has rows -------
    if extra_staff or extra_students:
        doc.add_page_break()
        p = doc.add_paragraph()
        r = p.add_run("ED169 ATTACHMENT – " + (d.get("name") or "").upper())
        r.bold = True
        r.font.size = Pt(12)
        if extra_staff:
            doc.add_paragraph().add_run("Other Teachers and Leaders (continued)").bold = True
            t = doc.add_table(rows=1, cols=5)
            _grid(t)
            for c, h in zip(t.rows[0].cells, ["Name(s)", "Male/ Female", "Status", "Qualifications and experiences "
                                              "in proposed activities", "Current first aid qualification"]):
                _write_cell(c, h, bold=True)
            for s in extra_staff:
                c = t.add_row().cells
                for i, v in enumerate([s.get("name", "").upper(), s.get("gender", ""), s.get("status", ""),
                                       s.get("experience") or "Y", "Y" if s.get("first_aid") else "N"]):
                    _write_cell(c[i], v)
        if extra_students:
            doc.add_paragraph().add_run("Number and year level(s) of students involved (continued)").bold = True
            t = doc.add_table(rows=1, cols=4)
            _grid(t)
            for c, h in zip(t.rows[0].cells, ["Year Level", "Male", "Female", "Total"]):
                _write_cell(c, h, bold=True)
            for s in extra_students:
                m, fe, o = int(s.get("male") or 0), int(s.get("female") or 0), int(s.get("other") or 0)
                c = t.add_row().cells
                for i, v in enumerate([s.get("year"), m or "", fe or "", m + fe + o]):
                    _write_cell(c[i], v)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# =====================================================================
# Excursion bank – CLC's previous excursions, ready to pre-fill a new plan
# (built from past ED169s; students, date, costs and checks are left blank to fill in each time)
# =====================================================================
CANDICE_MOBILE = "0476 037 050"
_CAITIE = {"name": "Caitie Hook", "gender": "F", "status": "Teacher", "experience": "Y", "first_aid": True}
_BEN_SE = {"name": "Ben Selga", "gender": "M", "status": "Teacher", "experience": "Y", "first_aid": True}
_VINNIE = {"name": "Vinnie Don", "gender": "M", "status": "SSO", "experience": "Y", "first_aid": True}
_BEN_SU = {"name": "Ben Sutton", "gender": "M", "status": "Teacher", "experience": "Y", "first_aid": True}
_MEGHAN = {"name": "Meghan Strydom", "gender": "F", "status": "Teacher", "experience": "Y", "first_aid": True}
_ROISIN = {"name": "Roisin Mcilduff", "gender": "F", "status": "Teacher", "experience": "Y", "first_aid": True}
_KIA = [{"name": "Kia (site car)", "rego": "S104BQL", "seats": None}]
_VAN = [{"name": "Van", "rego": "S996BQL", "seats": None}]
_PUBLIC = ("Opportunity to demonstrate and practise appropriate public behaviour and engage socially with others, "
           "and practise following instructions.")
_CAFE = ("Students practise appropriate behaviour in public spaces: selecting and ordering their own meal from the menu "
         "within the provided budget, and practising table etiquette and socially acceptable behaviours.\n"
         "Students observe how baristas work and how cafés run – supporting teaching for transfer in the Junior "
         "Barista Programme.")
_CAR = "Travel – site car / government vehicle"
_WEATHER = "Weather – sun, heat, rain and storms"

EXCURSION_BANK = [
    {"bank_name": "Beach & Adventure Park – Point Malcolm Reserve (BBQ lunch)",
     "data": {"name": "Beach & Adventure Park", "destination": "Point Malcolm Reserve", "address": "Semaphore Park",
              "program": "PY", "outline": _PUBLIC + "\nWalking and exploring Point Malcolm Reserve. Cooking lunch on the BBQ.",
              "curriculum": "English, Social Skills, Protective Practices.",
              "depart_time": "12:00", "return_time": "14:30", "vehicles": _KIA,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Beach, coast or jetty", "Park, reserve or playground", "BBQ / cooking food", _WEATHER]},
    {"bank_name": "Semaphore – walk and explore",
     "data": {"name": "Semaphore", "destination": "Semaphore", "address": "Semaphore foreshore and jetty",
              "program": "PY", "outline": _PUBLIC + "\nWalking and exploring Semaphore.",
              "curriculum": "English, Social Skills, Protective Practices.",
              "depart_time": "11:00", "return_time": "14:30", "vehicles": _KIA,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Walking – footpaths and crossing roads", "Beach, coast or jetty", _WEATHER]},
    {"bank_name": "Roy Marten Reserve (BBQ lunch)",
     "data": {"name": "Roy Marten Reserve", "destination": "Roy Marten Reserve", "address": "",
              "program": "PY", "outline": _PUBLIC + "\nWalking and exploring Roy Marten Reserve. Cooking lunch on the BBQ.",
              "curriculum": "English, Social Skills, Protective Practices.",
              "depart_time": "11:30", "return_time": "14:30", "vehicles": _KIA,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Park, reserve or playground", "BBQ / cooking food", _WEATHER]},
    {"bank_name": "Polonia Reserve – Croydon Park",
     "data": {"name": "Primary Program – Polonia Reserve", "destination": "Polonia Reserve", "address": "Croydon Park",
              "program": "PY", "outline": "Walk and explore Polonia Reserve. Practise appropriate behaviours and social "
                                          "skills in public places.",
              "curriculum": "Health, PE & Social Skills.",
              "depart_time": "12:00", "return_time": "14:20", "vehicles": _VAN,
              "staff": [_BEN_SE, _CAITIE, _VINNIE], "teacher_in_charge": "Ben Selga", "min_at_once": 3},
     "activities": [_CAR, "Park, reserve or playground", _WEATHER]},
    {"bank_name": "Gorge Wildlife Park",
     "data": {"name": "Wildlife Park", "destination": "Gorge Wildlife Park", "address": "Cudlee Creek",
              "program": "PY",
              "outline": "Students will visit Gorge Wildlife Park to observe and interact with a variety of native "
                         "Australian and exotic animals. Activities include exploring animal exhibits, supervised animal "
                         "feeding and interactions, and lunch in designated picnic areas.\nThe excursion provides "
                         "opportunities for students to practise social skills, emotional regulation, following "
                         "instructions and respectful interactions with peers, adults and animals in a community setting.",
              "curriculum": "Science: Explore living things, their habitats, characteristics and basic needs, while "
                            "developing an understanding of animal care and conservation.\nHASS: Develop an understanding "
                            "of the importance of caring for animals and protecting natural environments.\nHealth and "
                            "Physical Education: Practise emotional regulation, respectful communication, cooperation and "
                            "safe decision-making in a community setting.\nPersonal and Social Capability: Develop "
                            "self-management, social awareness, relationship skills and responsible decision-making.",
              "depart_time": "11:00", "return_time": "14:30", "vehicles": _KIA, "bushfire_area": True,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Zoo or wildlife park", _WEATHER]},
    {"bank_name": "Ten-pin bowling – Zone Bowling Cross Road",
     "data": {"name": "10 Pin Bowling", "destination": "Zone Bowling", "address": "Cross Road",
              "program": "PY",
              "outline": _PUBLIC + "\nPlaying 10 pin bowling: practising turn taking, fair play, good sportsmanship and "
                                   "following instructions.",
              "curriculum": "English, Social Skills, PE.",
              "depart_time": "11:30", "return_time": "14:30", "vehicles": _VAN,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Ten-pin bowling / indoor entertainment venue"]},
    {"bank_name": "Café lunch – Café Pellegrini",
     "data": {"name": "Café Lunch", "destination": "Café Pellegrini", "address": "Adelaide CBD",
              "program": "PY", "outline": _CAFE,
              "curriculum": "Social skills, Health, Protective Behaviours, Literacy, Numeracy.",
              "depart_time": "11:45", "return_time": "14:30", "vehicles": _VAN,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Walking – footpaths and crossing roads", "Café or restaurant"]},
    {"bank_name": "Café lunch – Burgerstronomy",
     "data": {"name": "Café Lunch", "destination": "Burgerstronomy", "address": "",
              "program": "PY", "outline": _CAFE,
              "curriculum": "Social skills, Health, Protective Behaviours, Literacy, Numeracy.",
              "depart_time": "11:30", "return_time": "14:00", "vehicles": _VAN,
              "staff": [_CAITIE, _BEN_SE], "teacher_in_charge": "Caitie Hook"},
     "activities": [_CAR, "Café or restaurant"]},
    {"bank_name": "Hamra Library and park next door (walk)",
     "data": {"name": "HAMRA Library", "destination": "Hamra Library and park next door", "address": "",
              "program": "JP", "outline": "Walking to Hamra Library. Borrowing library books and playing on the play "
                                          "equipment in the park next door.",
              "curriculum": "PE, Health, Social Skills programmes and Literacy.",
              "depart_time": "13:00", "return_time": "14:00", "transport_mode": "Walking only",
              "emergency_extra": "Van is available for immediate return to site if required.",
              "staff": [_BEN_SU, _MEGHAN], "teacher_in_charge": "Ben Sutton"},
     "activities": ["Walking – footpaths and crossing roads", "Library", "Park, reserve or playground", _WEATHER]},
    {"bank_name": "Salvation Army store (walk)",
     "data": {"name": "Salvation Army store", "destination": "Salvation Army store", "address": "",
              "program": "PY", "outline": "Walking to the Salvation Army store for a student to choose clothes for "
                                          "swimming.",
              "curriculum": "PE, Health, Social Skills programmes and Literacy.",
              "depart_time": "09:50", "return_time": "10:30", "transport_mode": "Walking only",
              "emergency_extra": "Van is available for immediate return to site if required.",
              "staff": [_CAITIE, _VINNIE], "teacher_in_charge": "Caitie Hook"},
     "activities": ["Walking – footpaths and crossing roads", "Shopping centre"]},
    {"bank_name": "Swimming lessons – The Parks Recreation & Sports Centre (YMCA)",
     "data": {"name": "Swimming", "destination": "The Parks Recreation and Sports Centre – YMCA", "address": "",
              "program": "JP", "outline": "Swimming lessons at The Parks Recreation and Sports Centre.",
              "curriculum": "PE, Health and Social Skills programmes.",
              "depart_time": "09:00", "return_time": "11:00", "vehicles": _VAN,
              "staff": [_BEN_SU, _ROISIN], "teacher_in_charge": "Ben Sutton"},
     "activities": [_CAR, "Swimming pool / aquatic centre"]},
]


def bank_excursion(entry: dict, library: list[dict] | None = None) -> dict:
    """Build a full new excursion from a bank entry (date, students, costs and checks left blank)."""
    d = blank_excursion()
    d.update(copy.deepcopy(entry["data"]))
    d["transport_mode"] = d.get("transport_mode") or TRANSPORT_MODES[0]
    d["site_contact"] = d.get("site_contact") or "Candice Cooper"
    if d["site_contact"] == "Candice Cooper" and not d.get("site_contact_phone"):
        d["site_contact_phone"] = CANDICE_MOBILE
    d["prepared_by"] = d.get("teacher_in_charge", "")
    by_name = {a["name"]: a for a in DEFAULT_ACTIVITIES}
    for a in library or []:
        by_name[a["name"]] = a
    d["activities"] = [activity_for_excursion(by_name[n]) for n in entry.get("activities", []) if n in by_name]
    d["students"] = [{"year": "3", "male": 0, "female": 0, "other": 0}]
    d["date_from"] = d["date_to"] = None
    return d


def fold(text: str) -> str:
    """Lower-case and strip accents so 'cafe' finds 'Café'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(c)).lower()


def search_bank(query: str) -> list[dict]:
    terms = [t for t in fold(query).split() if t]
    out = []
    for e in EXCURSION_BANK:
        hay = " ".join([e["bank_name"], e["data"].get("name", ""), e["data"].get("destination", ""),
                        e["data"].get("address", ""), e["data"].get("outline", "")] + e.get("activities", []))
        hay = fold(hay)
        if all(t in hay for t in terms):
            out.append(e)
    return out
