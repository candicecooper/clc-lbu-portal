from theme import apply_clc_theme
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import uuid
import random
import json
import re
import difflib
import requests
import urllib.parse
from io import BytesIO
import base64
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SUPABASE CONNECTION
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase not installed. Run: pip install supabase")

@st.cache_resource(ttl=60)
def init_supabase() -> Client:
    if not SUPABASE_AVAILABLE:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Supabase connection failed: {e}")
        return None

supabase: Client = init_supabase()

try:
    from archive_utils import archive_once, initials_from_name
    _ARCHIVE_AVAILABLE = True
except Exception:
    _ARCHIVE_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════
# SHARED GROQ HELPER
# Model fallback chain (openai/gpt-oss-120b -> qwen/qwen3.6-27b ->
# llama-3.3-70b-versatile), self-healing on 413 "request too large" by
# halving max_tokens, and a fallback client construction for the
# httpx "proxies" TypeError seen on some cached wheel combinations.
# Consolidates the three separate hardcoded llama-3.3-70b-versatile call
# sites in this file (that model was deprecated for free/dev-tier Groq
# accounts on 16 Aug 2026).
# ══════════════════════════════════════════════════════════════════════════
_GROQ_MODEL_CHAIN = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]

def _make_groq_client(api_key: str):
    from groq import Groq as _GroqClient
    try:
        return _GroqClient(api_key=api_key)
    except TypeError:
        # Cached groq wheel + newer httpx: Client.__init__() got an
        # unexpected keyword argument 'proxies' — build httpx.Client()
        # explicitly and pass it through.
        import httpx
        return _GroqClient(api_key=api_key, http_client=httpx.Client())

def groq_ai_call(prompt: str, max_tokens: int = 1500, temperature: float = 0.1) -> str:
    """Call Groq's chat completions with model fallback and self-healing
    on oversized requests. Returns the raw text content, or raises the
    last exception if every model in the chain fails."""
    GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
    if not GROQ_KEY:
        raise RuntimeError("Groq API key not configured.")
    client = _make_groq_client(GROQ_KEY)
    last_err = None
    for model in _GROQ_MODEL_CHAIN:
        _tokens = max_tokens
        for _attempt in range(3):
            try:
                kwargs = dict(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=_tokens,
                    temperature=temperature,
                )
                if model.startswith("qwen/"):
                    # Disable hybrid-thinking chain-of-thought output so
                    # Qwen returns the requested content directly instead
                    # of a <think>...</think> block.
                    kwargs["reasoning_effort"] = "none"
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                if "413" in str(e) or "too large" in str(e).lower():
                    _tokens = max(500, _tokens // 2)
                    continue
                break  # non-413 error: try the next model in the chain
    raise last_err if last_err else RuntimeError("Groq call failed for an unknown reason.")


st.set_page_config(page_title="CLC Behaviour Support", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

with st.sidebar:
    st.markdown(
        '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
        'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
        'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
        '🏠 Back to Staff Portal</a>',
        unsafe_allow_html=True
    )

MOCK_STAFF = [
    {"id": "s1", "name": "Emily Jones", "role": "JP", "email": "emily.jones@example.com", "password": "demo123"},
    {"id": "s2", "name": "Daniel Lee", "role": "PY", "email": "daniel.lee@example.com", "password": "demo123"},
    {"id": "s3", "name": "Sarah Chen", "role": "SY", "email": "sarah.chen@example.com", "password": "demo123"},
    {"id": "s4", "name": "Admin User", "role": "ADM", "email": "admin@example.com", "password": "admin123"},
]

MOCK_STUDENTS = [
    {"id": "stu_jp1", "name": "Emma T.", "grade": "R", "dob": "2018-05-30", "program": "JP",
     "edid": "ED123456", "placement_start": "2024-02-01", "placement_end": None},
    {"id": "stu_jp2", "name": "Oliver S.", "grade": "Y1", "dob": "2017-09-12", "program": "JP",
     "edid": "ED234567", "placement_start": "2024-03-15", "placement_end": None},
    {"id": "stu_jp3", "name": "Sophie M.", "grade": "Y2", "dob": "2016-03-20", "program": "JP",
     "edid": "ED345678", "placement_start": "2024-01-29", "placement_end": None},
    {"id": "stu_py1", "name": "Liam C.", "grade": "Y3", "dob": "2015-06-15", "program": "PY",
     "edid": "ED456789", "placement_start": "2024-02-12", "placement_end": None},
    {"id": "stu_py2", "name": "Ava R.", "grade": "Y4", "dob": "2014-11-08", "program": "PY",
     "edid": "ED567890", "placement_start": "2024-01-08", "placement_end": None},
    {"id": "stu_py3", "name": "Noah B.", "grade": "Y6", "dob": "2012-02-28", "program": "PY",
     "edid": "ED678901", "placement_start": "2024-04-03", "placement_end": None},
    {"id": "stu_sy1", "name": "Isabella G.", "grade": "Y7", "dob": "2011-04-17", "program": "SY",
     "edid": "ED789012", "placement_start": "2024-01-29", "placement_end": None},
    {"id": "stu_sy2", "name": "Ethan D.", "grade": "Y9", "dob": "2009-12-03", "program": "SY",
     "edid": "ED890123", "placement_start": "2024-02-26", "placement_end": None},
    {"id": "stu_sy3", "name": "Mia A.", "grade": "Y11", "dob": "2007-08-20", "program": "SY",
     "edid": "ED901234", "placement_start": "2024-03-11", "placement_end": None},
]

PROGRAM_NAMES = {"JP": "Junior Primary", "PY": "Primary Years", "SY": "Senior Years"}
BEHAVIOUR_TYPES = [
    "--- REFUSAL / WITHDRAWAL ---",
    "Verbal refusal of instruction",
    "Task refusal / passive non-compliance",
    "Shutdown / complete withdrawal",
    "Selective mutism / non-responsiveness",
    "--- ESCAPE / EVASION ---",
    "Unsanctioned departure (elopement)",
    "Absconding from school grounds",
    "Hiding or avoiding adult proximity",
    "--- DISRUPTIVE BEHAVIOUR ---",
    "Inappropriate vocalisation / noises",
    "Disruptive verbal commentary",
    "Interrupting / calling out",
    "Property misuse or interference",
    "--- AGGRESSION ---",
    "Verbal aggression toward peer",
    "Verbal aggression toward adult",
    "Physical aggression toward peer",
    "Physical aggression toward adult",
    "Threatening behaviour",
    "--- PROPERTY ---",
    "Property destruction",
    "Throwing objects",
    "--- SELF-REGULATION ---",
    "Self-injurious behaviour",
    "Dysregulated emotional expression",
    "--- OTHER ---",
    "Other (specify in description)",
]
ANTECEDENTS = [
    "--- PEER ---",
    "Peer - negative peer feedback",
    "Peer - peer conflict/interaction",
    "Peer - participating in competition",
    "Peer - losing against a peer/s",
    "Peer - another student escalating",
    "--- TRANSITION ---",
    "Transition - to a non-preferred activity",
    "Transition - from one activity to another",
    "Transition - from one environment to another",
    "Transition - another teacher coming into the program",
    "Transition - from play/yard to classroom",
    "Transition - from home to the program",
    "Transition - off a device",
    "--- INSTRUCTIONS ---",
    "Instructions - following instructions given by an adult",
    "Instructions - following task demands",
    "--- ENGAGEMENT ---",
    "Engagement - engaging in a non-preferred learning area (Maths/Literacy)",
    "Engagement - having to wait",
    "Engagement - change in routine",
    "Engagement - learning task too difficult or perceived as difficult",
    "Engagement - having to work with a peer",
    "Engagement - working independently",
    "Engagement - interrupted activity",
    "Engagement - not being able to finish an activity",
    "--- SENSORY ---",
    "Sensory - crowded area",
    "Sensory - noise",
    "Sensory - environment too bright",
    "Sensory - no medication",
    "Sensory - hungry/thirsty",
    "Sensory - unable to take a movement break",
    "--- OTHER ---",
    "Other - perceived injustice",
    "Other - TRT (Temporary Relief Teacher)",
    "Other - NIT teacher (New Initiatives Teacher)",
    "Other - incident before coming to program",
    "Other - verbalising not wanting to be at the program",
    "Other - staff attention shifted",
    "Other - unstructured time",
    "Other - access denied"
]

# ══════════════════════════════════════════════════════════════════════════
# ANTECEDENT CATEGORISATION (shared)
# Groups a raw antecedent string into one of the six categories used
# throughout the dashboard/analysis charts and by the BSEM recommendation
# engine below. Matches the "Category - description" structure of
# ANTECEDENTS first; falls back to keyword matching for free-text
# antecedents (e.g. AI-extracted historical incidents).
# ══════════════════════════════════════════════════════════════════════════
def categorize_antecedent(ant) -> str | None:
    a = str(ant).strip()
    if not a or a.startswith("---"):
        return None
    _KNOWN = {"peer": "Peer", "transition": "Transition", "instructions": "Instructions",
              "engagement": "Engagement", "sensory": "Sensory", "other": "Other"}
    prefix = a.split(" - ")[0].strip().lower()
    if prefix in _KNOWN:
        return _KNOWN[prefix]
    a_low = a.lower()
    if "peer" in a_low: return "Peer"
    if "transition" in a_low: return "Transition"
    if "instruction" in a_low or "demand" in a_low or "following" in a_low: return "Instructions"
    if any(w in a_low for w in ["engagement", "task", "wait", "routine", "interrupt", "finish",
                                 "literacy", "maths", "learning", "work independently", "difficult"]):
        return "Engagement"
    if any(w in a_low for w in ["sensory", "noise", "loud", "bright", "crowded", "medication",
                                 "hungry", "thirsty", "movement break"]):
        return "Sensory"
    return "Other"


# ══════════════════════════════════════════════════════════════════════════
# BSEM STRATEGY LIBRARY
# Curated, trauma-informed strategies organised by antecedent category and
# BSEM domain (Body / Relationship / Stamina / Engagement / Character —
# the Berry Street Education Model's five real domains).
# This is the fixed, reviewable source of truth for "what could be
# trialled" — the AI layer (build_bsem_recommendations, below) only ever
# selects and explains items from this list; it never invents strategies.
# ══════════════════════════════════════════════════════════════════════════
BSEM_STRATEGY_LIBRARY = {
    "Peer": [
        {"domain": "Body", "strategy": "A consistent seating position / work partner away from known peer-conflict pairings, reducing the physical stress response of tracking a threat."},
        {"domain": "Relationship", "strategy": "A pre-taught, low-key 'I need space' cue (card, gesture, or phrase) agreed with the student in advance, so the relationship can hold the need for distance before dysregulation, not during."},
        {"domain": "Character", "strategy": "Once regulated, a brief comic-strip-conversation or social-story debrief of the incident, building the student's own account of what happened, their values, and a better next step."},
        {"domain": "Stamina", "strategy": "Notice and name small wins in staying engaged after a peer conflict, building resilience for next time."},
    ],
    "Transition": [
        {"domain": "Body", "strategy": "A visual first-then schedule with a consistent early warning (5-minute, then 2-minute) before the transition, reducing the stress response to surprise."},
        {"domain": "Relationship", "strategy": "A brief regulation check-in with a trusted adult immediately before the transition begins, not only offered after dysregulation appears."},
        {"domain": "Engagement", "strategy": "Involve the student in choosing part of their own transition routine (order of steps, which door, which adult walks with them) to build willingness to engage with the routine."},
        {"domain": "Stamina", "strategy": "A visible 'transition streak' tracker, celebrating consecutive successful transitions to build persistence through a known hard moment."},
    ],
    "Instructions": [
        {"domain": "Body", "strategy": "Offer instructions as a choice of order rather than a single directive ('finish the maths or start it — you choose') to reduce the perceived threat of direct demand."},
        {"domain": "Relationship", "strategy": "PACE-aligned delivery (Playful, Accepting, Curious, Empathic tone) rather than a directive tone, particularly for the first instruction attempt."},
        {"domain": "Engagement", "strategy": "Build in visible processing/wait time before expecting compliance, using 'when-then' framing so the student can see the endpoint and stays willing to engage."},
        {"domain": "Character", "strategy": "Frame following instructions as a values-based choice the student is making ('this is what taking responsibility looks like'), building their own self-knowledge of capability."},
    ],
    "Engagement": [
        {"domain": "Body", "strategy": "Chunk tasks into short, visibly-bounded segments with a built-in movement break before fatigue sets in, rather than after."},
        {"domain": "Relationship", "strategy": "Lead with specific, genuine connection/praise before task difficulty increases, so engagement is scaffolded by relationship rather than demand alone."},
        {"domain": "Engagement", "strategy": "Offer choice in task order or format, and link the task to a known interest area where possible, to build willingness to learn."},
        {"domain": "Stamina", "strategy": "A visible progress tracker or goal-setting approach so the student can see persistence paying off across the task."},
    ],
    "Sensory": [
        {"domain": "Body", "strategy": "A quiet, low-stimulation space to enter before joining the group; trial reducing ambient volume on entry, and noise-cancelling headphones/earphones if auditory input seems to be the driver."},
        {"domain": "Body", "strategy": "Reduce ambient unpredictability where identifiable (flickering lights, sudden bells/alarms, echoing spaces)."},
        {"domain": "Relationship", "strategy": "Offer the sensory strategy discreetly rather than in front of peers, protecting the relationship and the student's dignity."},
        {"domain": "Character", "strategy": "Once regulated, collaboratively ask the student which specific inputs feel hardest — building their own self-knowledge and language for it over time."},
    ],
    "Other": [
        {"domain": "Body", "strategy": "Check whether an unidentified sensory or physiological factor (hunger, tiredness, medication timing) coincides with these incidents."},
        {"domain": "Relationship", "strategy": "Prioritise co-regulation and connection with a trusted adult before any expectation of cognitive engagement or compliance."},
        {"domain": "Stamina", "strategy": "Look for a predictability gap around this trigger (change of adult, change of routine, time of day) and consider what advance notice could be built in, building resilience to change over time."},
        {"domain": "Character", "strategy": "Because this antecedent doesn't fit a clear category yet, a closer look at the incident narratives — including what they say about the student's needs and values — may surface a more specific pattern to target."},
    ],
}


# ══════════════════════════════════════════════════════════════════════════
# BEHAVIOUR REFRAME — trauma-informed / neurodivergent-affirming lens
# Reframes a canonical behaviour label away from "the student is choosing
# to be difficult" toward what's more likely actually happening
# neurologically/developmentally. Draws on SMART (Strategies for Managing
# Abuse-Related Trauma), Australian Childhood Foundation, and general
# well-established neurodiversity-affirming concepts — not a diagnosis
# for any individual student, a starting lens for staff to be read
# alongside clinical judgement, not instead of it.
# ══════════════════════════════════════════════════════════════════════════
BEHAVIOUR_REFRAME = {
    "Verbal refusal of instruction": "Often reflects a felt loss of control, or a demand that feels unsafe or overwhelming in the moment — not a wish to be defiant.",
    "Task refusal / passive non-compliance": "May reflect executive-function load, perceived risk of failure, or sensory overwhelm rather than unwillingness to comply.",
    "Physical aggression toward peer": "A fight response from a nervous system that has moved into survival mode — the priority is safety and de-escalation, not the 'why' in the moment.",
    "Physical aggression toward adult": "Same as above — a fight-stage survival response, not a considered choice made with full access to reasoning.",
    "Threatening behaviour": "Often a warning sign the nervous system is close to its threshold, an attempt to create distance or safety — though it must still be taken seriously and responded to safely.",
    "Property destruction": "A release of overwhelming internal arousal directed at an object rather than a person — often safer than it looks.",
    "Throwing objects": "A physical release of energy the body can't otherwise discharge in the moment.",
    "Unsanctioned departure (elopement)": "A flight response — moving away from an overwhelming environment, often the only escape route available to a dysregulated nervous system.",
    "Absconding from school grounds": "An extension of the same flight response, at higher intensity.",
    "Self-injurious behaviour": "Can be a way of regulating overwhelming internal sensation, or a communication of distress when other channels feel unavailable.",
    "Shutdown / complete withdrawal": "A freeze response — the nervous system going into shutdown as a protective strategy, not disengagement by choice.",
    "Selective mutism / non-responsiveness": "Consistent with a freeze response, or for some neurodivergent students a genuine, situational loss of verbal access under stress.",
    "Hiding or avoiding adult proximity": "May reflect a freeze/avoid response, or sensory and social avoidance common in autism.",
    "Verbal aggression toward peer": "Often a release of built-up frustration or dysregulation rather than a considered social choice.",
    "Verbal aggression toward adult": "Usually reflects dysregulation in the moment, not a stable judgement about the adult.",
    "Property misuse or interference": "Can reflect sensory-seeking or a need for control/predictability rather than deliberate disruption.",
    "Disruptive verbal commentary": "Can reflect impulsivity (common in ADHD) or an attempt to self-regulate out loud, rather than intentional disruption.",
    "Interrupting / calling out": "Often impulsivity-driven — reduced inhibitory control rather than rudeness, common in ADHD presentations.",
    "Inappropriate vocalisation / noises": "May be a self-regulatory or stimming behaviour common in neurodivergence rather than attention-seeking.",
    "Dysregulated emotional expression": "A visible sign the student's regulatory capacity has been exceeded in that moment.",
}

# ══════════════════════════════════════════════════════════════════════════
# CPI VERBAL ESCALATION CONTINUUM
# CPI's continuum tracks rising verbal defiance through five stages. It
# describes verbal/behavioural escalation specifically — physical
# aggression, elopement, and shutdown/freeze presentations sit outside
# it (physical aggression belongs to CPI's broader Crisis Development
# Model rather than the verbal continuum; shutdown/freeze is the opposite
# pole entirely). Mapped here in general terms — always apply CPI training
# and in-the-moment clinical judgement over an automatic label.
# ══════════════════════════════════════════════════════════════════════════
CPI_STAGE_MAP = {
    "Verbal refusal of instruction": "Refusal",
    "Task refusal / passive non-compliance": "Refusal",
    "Disruptive verbal commentary": "Release",
    "Interrupting / calling out": "Release",
    "Inappropriate vocalisation / noises": "Release",
    "Verbal aggression toward peer": "Release",
    "Verbal aggression toward adult": "Release",
    "Property misuse or interference": "Release",
    "Dysregulated emotional expression": "Release",
    "Property destruction": "Release",
    "Throwing objects": "Release",
    "Threatening behaviour": "Intimidation",
}

CPI_STAGES = {
    "Questioning": {
        "desc": "Asking questions that challenge authority or purpose — sometimes a genuine information request, sometimes a challenge disguised as one.",
        "response": "Answer a genuine information question directly and matter-of-factly. If it's a challenging question aimed at your authority rather than real information, redirect calmly back to the original request rather than getting drawn into a debate.",
        "smart_stage": "Relate — the student is still verbally reachable here, but a defensive/testing question is often an early sign the nervous system is starting to feel unsafe. Stay connected before pushing for compliance.",
    },
    "Refusal": {
        "desc": "Non-compliance — saying no, or passively refusing to follow an instruction.",
        "response": "Set a clear, simple limit and offer a genuine choice within it. Avoid repeating the same instruction on a loop, and avoid a power struggle — state it once, calmly, and allow processing time.",
        "smart_stage": "Relate — offering choice and a calm, connected tone keeps the relationship (not the demand) in charge. Reasoning or negotiating the 'why' of the rule can wait.",
    },
    "Release": {
        "desc": "Releasing built-up energy through venting — raised voice, swearing, crying, or object-directed release not aimed at hurting anyone.",
        "response": "Allow the release to happen safely and remove the audience if possible. Don't try to reason, problem-solve, or debrief while they're venting — wait for the energy to visibly drop first.",
        "smart_stage": "Regulate — the brainstem/survival part of the brain is driving this, not the thinking part. Words and logic can't reach it yet; the only job right now is safety and letting the energy discharge.",
    },
    "Intimidation": {
        "desc": "Verbal or nonverbal threats aimed at a specific person, or general intimidation.",
        "response": "Take the threat seriously and seek additional staff support. Stay calm and neutral — don't respond in kind, argue, or make counter-threats.",
        "smart_stage": "Regulate — the student's threat response has taken over. Your own calm, regulated nervous system is the intervention here, not an argument or a consequence delivered in the moment.",
    },
    "Tension Reduction": {
        "desc": "The point after the peak where energy visibly starts dropping.",
        "response": "This is the window for reconnection and repair — not before. Debrief once the student is genuinely calm, not immediately after the peak.",
        "smart_stage": "Relate, then Reason — this is the only point in the sequence where a debrief or a consequence conversation will actually land. Reconnect first (Relate); once that's solid, then reflect together (Reason).",
    },
}


# ── Demand-avoidant presentations (ODD / PDA-type profiles, diagnosed or not) ──
# Framed around the presentation, never a label: the strategies are the same
# whether or not a diagnosis exists. Core idea: the *perceived* loss of control
# is what triggers the threat response, so demands are lowered, shared and
# reframed (declarative language, perceived choice) rather than pushed harder.
DEMAND_AVOIDANCE_STRATEGIES = [
    {"domain": "Relationship", "strategy": "Lead with connection and a calm, low-arousal tone. Treat refusal as anxiety-driven avoidance of a perceived loss of control, not defiance — so avoid power struggles, ultimatums and public correction."},
    {"domain": "Body", "strategy": "Lower the overall demand load, especially during dysregulation or the known peak session. Drop non-essential demands, prioritise 2–3 'must-do' expectations, and let everything else flow from choice."},
    {"domain": "Engagement", "strategy": "Use declarative, indirect language ('I wonder if...', 'I notice the pencils are out') and invitations rather than direct commands. Present tasks as problems to solve together or as roles ('Can you be the timekeeper?')."},
    {"domain": "Engagement", "strategy": "Build in perceived choice: offer two acceptable options where both meet your goal, with the student choosing 'what', 'where', 'with whom' or 'in what order' — never whether."},
    {"domain": "Stamina", "strategy": "Hand control back in small, safe ways: let the student set the timer, pick the starting point, or negotiate a 'my turn / your turn' split of the task, and acknowledge the effort made rather than the compliance."},
    {"domain": "Character", "strategy": "Use shared-expert and interest-led framing (a favourite topic, a role of responsibility) so the student can say yes on their own terms. Build their own language for 'I'm feeling pressured' with a pre-agreed, no-questions-asked pause signal."},
    {"domain": "Relationship", "strategy": "Keep adults consistent and predictable about what stays non-negotiable (safety) while staying flexible about everything else. Plan the repair conversation for when the student is regulated and keep it brief, non-blaming and forward-looking."},
]

PERCEIVED_CHOICE_PHRASES = [
    ("Get your book out now.",
     "Would you like to start with the reading or the writing? / Do you want your book on the desk or the floor?"),
    ("It's time to line up.",
     "I wonder who is going to lead us to the door today — you or your buddy?"),
    ("You need to finish this before break.",
     "We have 10 minutes before break. Do you want to do the first half now, or the part you like best first?"),
    ("Stop doing that.",
     "I'm noticing it's getting loud in here. Would a walk to the water bottle or a quiet corner help?"),
    ("Sit down and start.",
     "Where would be the best spot for you to work today — the beanbag or the back table?"),
    ("You must say sorry.",
     "When you're ready, how would you like to fix it — a note, a chat, or help tidy up?"),
    ("Do the worksheet.",
     "I've got a worksheet and a hands-on version of the same task. Which would you like to take on?"),
]


def demand_avoidance_signal(full_df) -> dict:
    """How strongly does this student's data point to a demand-avoidant
    presentation? Looks at the share of incidents triggered by instructions,
    engagement/task demands or transitions, or presenting as refusal. A
    prompt for staff judgement only, never a label or diagnosis."""
    if full_df is None or full_df.empty:
        return {"n": 0, "total": 0, "pct": 0.0, "flag": False}
    total = len(full_df)
    _cats = full_df["antecedent"].apply(categorize_antecedent) if "antecedent" in full_df.columns else pd.Series([None] * total, index=full_df.index)
    _demand_cat = _cats.isin(["Instructions", "Engagement", "Transition"])
    _refusal = pd.Series(False, index=full_df.index)
    if "behaviour_type" in full_df.columns:
        _refusal = full_df["behaviour_type"].astype(str).str.contains("refus|non-compl|noncompl|elope|depart|abscond|shutdown|withdraw", case=False, regex=True)
    _flagged = _demand_cat | _refusal
    n = int(_flagged.sum())
    pct = n / total if total else 0.0
    return {"n": n, "total": total, "pct": pct, "flag": (n >= 3 and pct >= 0.4)}


def _top_categories(full_df, n: int = 2) -> list[str]:
    """Return the n most frequent antecedent categories present in
    full_df, computing the category column if it isn't already there."""
    if full_df is None or full_df.empty or "antecedent" not in full_df.columns:
        return []
    if "_ant_cat" in full_df.columns:
        cats = full_df["_ant_cat"].dropna()
    else:
        cats = full_df["antecedent"].apply(categorize_antecedent).dropna()
    if cats.empty:
        return []
    return list(cats.value_counts().head(n).index)


def build_bsem_recommendations(
    full_df, top_beh, top_ant, top_loc, top_session, student_name: str,
    context: str = "dashboard",
) -> list[dict]:
    """Curated-library + AI-framing recommendations, returned as structured
    items so the UI can render them as clickable cards with a short "why
    this fits" and "how to implement" — rather than one static paragraph.

    The curated BSEM_STRATEGY_LIBRARY supplies the domain + strategy
    (fixed, never AI-invented); the AI layer only writes the "why" and
    "how" for each, grounded in the student's actual pattern.

    context="dashboard": short, practical, "things to trial this week"
      framing for CLC-LBU's small, highly structured setting.
    context="analysis": framing oriented toward what should travel with
      the student into a mainstream school placement — what a receiving
      school would need to know and put in place.

    Returns a list of dicts: {"category","domain","strategy","why","how"}.
    """
    cats = _top_categories(full_df, n=2)
    if not cats:
        return []

    picked = []
    for cat in cats:
        for item in BSEM_STRATEGY_LIBRARY.get(cat, []):
            picked.append({"category": cat, **item})

    _library_json = "\n".join(
        f'{i}. [{p["domain"]}] {p["strategy"]}' for i, p in enumerate(picked)
    )

    if context == "analysis":
        _framing = (
            "Write for a transition/handover audience: staff preparing to support this "
            "student's move into a mainstream school setting. Frame 'how' in terms of what "
            "the receiving school would need to know and put in place, since a mainstream "
            "classroom won't have CLC-LBU's small, highly structured environment by default."
        )
    else:
        _framing = (
            "Write for CLC-LBU staff to use directly, day to day, in our small, highly "
            "structured setting. Frame 'how' as something concrete to trial this week."
        )

    prompt = (
        "You are a trauma-informed behaviour support specialist, using the Berry Street Education "
        "Model (BSEM), whose five domains are Body, Relationship, Stamina, Engagement, and Character.\n"
        f"Student pattern — primary behaviour: {top_beh}; primary trigger: {top_ant}; "
        f"location hotspot: {top_loc}; peak time: {top_session}.\n\n"
        "Here is a numbered, fixed, pre-approved list of strategies. Do NOT invent new "
        "strategies or add anything not in this list:\n"
        f"{_library_json}\n\n"
        f"{_framing}\n"
        "Select the 4-6 most relevant items given the student's pattern. For each, write:\n"
        '"why" — one short sentence connecting it to this student\'s specific hotspot/time '
        "pattern (not generic).\n"
        '"how" — 2-3 concrete, practical implementation steps a staff member could follow.\n\n'
        "Return ONLY a JSON array, no markdown fences, no preamble, in this exact form: "
        '[{"id": <number from the list above>, "why": "...", "how": "..."}]'
    )

    try:
        raw = groq_ai_call(prompt, max_tokens=2200, temperature=0.3)
        raw = raw.strip()
        raw = re.sub(r'^```(?:json)?\s*|\s*```\s*$', '', raw, flags=re.IGNORECASE).strip()
        try:
            ai_items = json.loads(raw)
        except json.JSONDecodeError:
            # Response likely got truncated by the token limit before the
            # JSON could close properly — salvage whatever complete
            # {"id":...,"why":...,"how":...} objects we can from the
            # partial array instead of discarding the whole response.
            ai_items = []
            for _om in re.findall(r'\{[^{}]*\}', raw):
                try:
                    ai_items.append(json.loads(_om))
                except json.JSONDecodeError:
                    continue
            if not ai_items:
                raise
        if isinstance(ai_items, dict):
            # Model may have wrapped the array in an object, e.g. {"recommendations": [...]}
            for _v in ai_items.values():
                if isinstance(_v, list):
                    ai_items = _v
                    break
        result = []
        for a in ai_items:
            if not isinstance(a, dict):
                continue
            try:
                idx = int(a.get("id"))
            except (TypeError, ValueError):
                continue
            if not (0 <= idx < len(picked)):
                continue
            result.append({**picked[idx], "why": a.get("why", ""), "how": a.get("how", "")})
        if result:
            return result
        # TEMP DIAGNOSTIC: the call succeeded and returned valid JSON, but no
        # item matched a known strategy id — surface why instead of a silent
        # generic fallback, so the actual cause is visible in the app.
        _debug = (f"[DEBUG] AI returned {len(ai_items) if isinstance(ai_items, list) else 'non-list'} "
                  f"item(s), none matched. Raw response (first 400 chars): {raw[:400]}")
        return [{**p, "why": "", "how": _debug if i == 0 else ""} for i, p in enumerate(picked[:6])]
    except Exception as _e:
        # TEMP DIAGNOSTIC: surface the actual exception instead of swallowing it.
        _debug = f"[DEBUG] AI call/parsing failed: {type(_e).__name__}: {_e}"
        return [{**p, "why": "", "how": _debug if i == 0 else ""} for i, p in enumerate(picked[:6])]


def plotly_chart_with_selection(fig, key: str, **kwargs):
    """st.plotly_chart with click-to-select (a clicked bar/point is
    returned so the caller can drill into it), falling back to a plain,
    non-interactive chart if the installed Streamlit version doesn't
    support on_select yet — so this can never silently break the chart
    itself, only the click feature."""
    try:
        event = st.plotly_chart(fig, key=key, on_select="rerun", selection_mode="points", **kwargs)
        return (event.get("selection", {}) or {}).get("points", []) if isinstance(event, dict) else []
    except TypeError:
        st.plotly_chart(fig, **kwargs)
        return []


def _render_bsem_recommendations_ui(items: list[dict], key_prefix: str):
    """Render structured BSEM recommendations as clickable, colour-coded
    cards — click a strategy to reveal why it fits and how to trial it.
    Uses only button + session_state toggling (not st.expander's `key=`
    argument, which isn't supported on all Streamlit versions) so the
    click-to-expand behaviour is guaranteed to work regardless of the
    exact Streamlit version deployed."""
    if not items:
        return
    _domain_style = {
        "Body":         {"icon": "🧘", "color": "#10b981", "bg": "#f0fdf4"},
        "Relationship": {"icon": "🤝", "color": "#3b82f6", "bg": "#eff6ff"},
        "Stamina":      {"icon": "💪", "color": "#f97316", "bg": "#fff7ed"},
        "Engagement":   {"icon": "🎯", "color": "#8b5cf6", "bg": "#faf5ff"},
        "Character":    {"icon": "⭐", "color": "#eab308", "bg": "#fefce8"},
    }
    for i, item in enumerate(items):
        style = _domain_style.get(item["domain"], {"icon": "•", "color": "#64748b", "bg": "#f8fafc"})
        _open_key = f"{key_prefix}_open_{i}"
        if _open_key not in st.session_state:
            st.session_state[_open_key] = False
        with st.container(border=True):
            st.markdown(
                f"<span style='background:{style['bg']};color:{style['color']};"
                f"padding:0.2rem 0.75rem;border-radius:999px;font-size:0.72rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:.03em;'>{style['icon']} {item['domain']}</span>",
                unsafe_allow_html=True,
            )
            _arrow = "🔽" if st.session_state[_open_key] else "▶️"
            if st.button(f"{_arrow}  {item['strategy']}", key=f"{key_prefix}_btn_{i}", use_container_width=True):
                st.session_state[_open_key] = not st.session_state[_open_key]
                # No explicit st.rerun() — Streamlit already reruns the script
                # automatically after any button click, and the state check
                # below runs immediately in that same pass. A manual rerun()
                # here was redundant and could interrupt the click before the
                # updated state was rendered.
            if st.session_state[_open_key]:
                if item.get("why"):
                    st.markdown(f"**Why this fits:** {item['why']}")
                if item.get("how"):
                    st.markdown(f"**How to trial it:** {item['how']}")
                if not item.get("why") and not item.get("how"):
                    st.caption("Implementation detail unavailable right now — the strategy above is still valid to trial.")


# ══════════════════════════════════════════════════════════════════════════
# WINDOW OF TOLERANCE — DRAFT TABLE FROM INCIDENT DATA
# Maps this tool's incident records into the same 5-zone structure used by
# the standalone Window of Tolerance Creator, so staff get a data-informed
# starting draft to review and copy across, rather than starting blank.
# ══════════════════════════════════════════════════════════════════════════
WOT_ZONES = [
    {"id": "hyper",      "label": "Mobilisation — Hyperarousal",                    "color": "#AF3A2C"},
    {"id": "copingup",   "label": "Coping Mechanisms — moving toward Hyperarousal", "color": "#B9761A"},
    {"id": "copingdown", "label": "Coping Mechanisms — moving toward Hypoarousal",  "color": "#2A6693"},
    {"id": "hypo",       "label": "Immobilisation — Hypoarousal",                   "color": "#3C4C6B"},
]

# Behaviour type -> arousal direction ("up" toward hyperarousal/fight-flight,
# "down" toward hypoarousal/shutdown-freeze). Severity then decides which of
# the two bands on that side a given incident sits in. Types not listed here
# (e.g. "Other") are left unclassified and excluded from the draft table —
# this is a starting point for staff judgement, not a final answer.
WOT_DIRECTION_MAP = {
    "Physical aggression toward peer": "up", "Physical aggression toward adult": "up",
    "Threatening behaviour": "up", "Property destruction": "up", "Throwing objects": "up",
    "Unsanctioned departure (elopement)": "up", "Absconding from school grounds": "up",
    "Self-injurious behaviour": "up", "Verbal aggression toward peer": "up",
    "Verbal aggression toward adult": "up", "Property misuse or interference": "up",
    "Disruptive verbal commentary": "up", "Interrupting / calling out": "up",
    "Inappropriate vocalisation / noises": "up", "Verbal refusal of instruction": "up",
    "Dysregulated emotional expression": "up",
    "Task refusal / passive non-compliance": "down", "Shutdown / complete withdrawal": "down",
    "Selective mutism / non-responsiveness": "down", "Hiding or avoiding adult proximity": "down",
}


def deidentify_context(text: str, subject_student_id=None) -> str:
    """Replace known staff/peer first names in free text with a generic
    role label, so the Context column reads as a general situation
    rather than naming specific people. Uses the app's own known staff
    and student names — matches whole words only, case-insensitive."""
    if not text or not isinstance(text, str):
        return text
    result = text
    for s in st.session_state.get("staff", []):
        _first = (s.get("name") or "").split()[0] if s.get("name") else ""
        if _first and len(_first) > 2:
            result = re.sub(rf'\b{re.escape(_first)}\b', "a staff member", result, flags=re.IGNORECASE)
    for stu in st.session_state.get("students", []):
        if stu.get("id") == subject_student_id:
            continue  # don't scrub the subject student's own name from their own record
        _first = (stu.get("name") or "").split()[0] if stu.get("name") else ""
        if _first and len(_first) > 2:
            result = re.sub(rf'\b{re.escape(_first)}\b', "a peer", result, flags=re.IGNORECASE)
    return result


def generate_single_incident_docx(print_data: dict, incident_type: str, student_name: str):
    """Simple one-page printable/downloadable summary of a single incident
    — for staff who need to print one record's details or hand it to
    someone outside the portal."""
    from docx import Document
    from docx.shared import Pt, Cm
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2)
    doc.add_heading(f"Incident Summary — {student_name}", level=1)
    _type_label = "Critical Incident (ABCH)" if incident_type == "critical" else "Regular Incident"
    p = doc.add_paragraph()
    p.add_run("Record type: ").bold = True
    p.add_run(_type_label)
    doc.add_paragraph("")
    for label, value in print_data.items():
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(str(value) if value not in (None, "") else "—")
    p_footer = doc.add_paragraph()
    p_footer.add_run(f"\nPrinted from CLC-LBU Behaviour Support Tool — {datetime.now().strftime('%d/%m/%Y %H:%M')}").italic = True
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _strip_category_prefix(text: str) -> str:
    """Antecedents in this tool are stored as 'Category - description'
    (e.g. 'Engagement - having to work with a peer'). The Window of
    Tolerance Creator's own context entries read as plain situational
    phrases with no category prefix — strip it and capitalise, so
    drafted lines match that register."""
    if not text or not isinstance(text, str):
        return text
    _parts = text.split(" - ", 1)
    _clean = (_parts[1] if len(_parts) == 2 else text).strip()
    return (_clean[:1].upper() + _clean[1:]) if _clean else _clean


# INTERVENTIONS (the fixed multi-select list staff choose from when logging
# an incident) expanded into a fuller standard description of what each
# technique actually means/looks like in practice. These describe the
# technique itself, not any specific incident — so expanding a known,
# fixed strategy name this way doesn't invent per-incident detail nobody
# wrote; it's the same kind of description a policy or training document
# would already give that strategy.
INTERVENTION_DETAIL = {
    "CPI Supportive stance":  "Used a supportive, non-threatening body stance (CPI) — angled rather than square-on, at a safe distance",
    "Offered break":          "Offered a short break before returning to the task",
    "Reduced demand":         "Reduced the task demand — fewer steps or a lower-effort version of the task",
    "Provided choices":       "Offered a choice between two options rather than a single imposed demand",
    "Removed audience":       "Removed the audience — moved nearby peers/onlookers away as a de-escalation measure",
    "Visual supports":        "Used a visual support (schedule, cue card, or written prompt) to reduce reliance on verbal instruction",
    "Co-regulation":          "Stayed alongside the student and modelled calm breathing/tone to support co-regulation",
    "Prompted coping skill":  "Prompted use of a previously taught coping strategy (e.g. breathing, movement, quiet space)",
    "Redirection":            "Redirected attention to a different activity or focus to interrupt the escalation",
}


def _polish_intervention_list(text: str) -> str:
    """Intervention is a multi-select of short strategy names (e.g.
    'CPI Supportive stance, Removed audience'). Where an item matches
    one of the fixed, known strategies, expand it to its full standard
    description (INTERVENTION_DETAIL) to match the Creator's fuller
    register. Anything that doesn't match a known strategy (free text,
    a renamed option) is just capitalised rather than guessed at."""
    if not text or not isinstance(text, str):
        return text
    _items = [s.strip() for s in text.split(",") if s.strip()]
    _items = [INTERVENTION_DETAIL.get(s, s[:1].upper() + s[1:]) for s in _items]
    return "; ".join(_items)


def build_window_of_tolerance_table(full_df, student_id=None) -> dict:
    """Group this student's incident data into the WoT Creator's 4
    dysregulation zones (the 'Window of Tolerance' zone itself is by
    definition regulated behaviour, which incident logs don't capture,
    so it's intentionally left for staff to complete directly in the
    Creator). Returns {zone_id: {"n", "context", "behaviour",
    "interventions"}} — each a short list of this student's most
    frequent entries for that zone, styled to match the Creator's own
    short, concrete, observable-phrase entries as closely as the
    underlying data allows.

    Context is de-identified (named peers/staff replaced with a generic
    role) since it describes the surrounding situation, not this
    student's own presentation. Behaviour keeps — and where a free-text
    description exists, adds — the specific detail, since that's exactly
    what should stay sharp and individual to this student."""
    if full_df is None or full_df.empty or "behaviour_type" not in full_df.columns:
        return {}
    _df = full_df.copy()
    _df["severity"] = pd.to_numeric(_df.get("severity", 3), errors="coerce").fillna(3)

    def _flatten(v):
        # "intervention" is a multi-select field stored as a Postgres array —
        # supabase-py returns it as a Python list, not a plain string, which
        # breaks a straight "\n".join() downstream. Flatten to one string.
        if isinstance(v, list):
            return ", ".join(str(x) for x in v if x)
        return v

    for _col in ("antecedent", "behaviour_type", "intervention", "description"):
        if _col in _df.columns:
            _df[_col] = _df[_col].apply(_flatten)

    if "antecedent" in _df.columns:
        _df["antecedent"] = _df["antecedent"].apply(_strip_category_prefix)
        _df["antecedent"] = _df["antecedent"].apply(lambda t: deidentify_context(t, student_id))

    if "intervention" in _df.columns:
        _df["intervention"] = _df["intervention"].apply(_polish_intervention_list)

    # Combine the canonical behaviour label with any free-text description
    # for specificity — the label alone is a category, the description is
    # what this student's presentation actually looks like. Capped to a
    # short phrase, matching the Creator's concrete, observable style
    # rather than a full narrative sentence.
    if "description" in _df.columns:
        def _combine_behaviour(row):
            _lbl = row.get("behaviour_type") or ""
            _desc_raw = row.get("description")
            # pd.isna() correctly catches NaN/None; a plain "or ''" check
            # doesn't, because NaN is truthy in Python — that produced the
            # literal text "nan" appearing whenever description was blank.
            _desc = "" if pd.isna(_desc_raw) else str(_desc_raw).strip()
            if len(_desc) > 70:
                _desc = _desc[:67].rstrip() + "…"
            if _desc:
                return f"{_lbl} — {_desc}" if _lbl else _desc
            return _lbl
        _df["_behaviour_detail"] = _df.apply(_combine_behaviour, axis=1)
    else:
        _df["_behaviour_detail"] = _df["behaviour_type"]

    def _zone(row):
        direction = WOT_DIRECTION_MAP.get(row.get("behaviour_type"))
        if direction is None:
            return None
        if direction == "up":
            return "hyper" if row["severity"] >= 4 else "copingup"
        return "hypo" if row["severity"] >= 4 else "copingdown"

    _df["_wot_zone"] = _df.apply(_zone, axis=1)
    _df = _df.dropna(subset=["_wot_zone"])
    if _df.empty:
        return {}
    result = {}
    for z in WOT_ZONES:
        _zdf = _df[_df["_wot_zone"] == z["id"]]
        if _zdf.empty:
            continue
        _contexts = (_zdf["antecedent"].dropna().value_counts().head(5).index.tolist()
                     if "antecedent" in _zdf.columns else [])
        _behaviours = _zdf["_behaviour_detail"].dropna().value_counts().head(5).index.tolist()
        _interventions = []
        if "intervention" in _zdf.columns:
            _iv = _zdf["intervention"].dropna()
            _iv = _iv[_iv.astype(str).str.strip() != ""]
            _interventions = _iv.value_counts().head(5).index.tolist()
        result[z["id"]] = {"n": len(_zdf), "context": _contexts,
                            "behaviour": _behaviours, "interventions": _interventions}
    return result


def _render_window_of_tolerance_table_ui(full_df, student_id=None):
    """Streamlit UI for build_window_of_tolerance_table — one block per
    zone, each field in its own st.code() box so staff can use
    Streamlit's built-in copy-icon to paste straight into the Creator."""
    wot_data = build_window_of_tolerance_table(full_df, student_id=student_id)
    if not wot_data:
        st.info("Not enough classifiable incidents yet to draft a Window of Tolerance table. "
                "This needs behaviour types that clearly indicate arousal direction (e.g. aggression, "
                "elopement, shutdown, withdrawal) — 'Other' or ambiguous entries are left out on purpose.")
        return
    st.caption("Draft only — built from this student's logged behaviour types and severity. "
               "Context is de-identified (peers/staff shown by role, not name); Behaviour and "
               "Interventions stay specific to this student. The Window of Tolerance concept itself "
               "is part of SMART's brain-based framework — regulation must be restored before any "
               "reasoning or correction can land. Review before use; copy any line across into the "
               "Window of Tolerance Creator.")
    for z in WOT_ZONES:
        if z["id"] not in wot_data:
            continue
        zd = wot_data[z["id"]]
        st.markdown(
            f"<div style='border-left:5px solid {z['color']};padding:0.3rem 0.9rem;margin:0.6rem 0 0.2rem;'>"
            f"<b style='color:{z['color']};'>{z['label']}</b> — {zd['n']} incident(s)</div>",
            unsafe_allow_html=True,
        )
        _wcol1, _wcol2, _wcol3 = st.columns(3)

        def _safe_join(items):
            # Defensive: coerce anything unexpected (e.g. a stray list) to a
            # plain string rather than letting "\n".join() crash the page.
            return "\n".join(x if isinstance(x, str) else str(x) for x in items)

        with _wcol1:
            st.caption("Context")
            st.code(_safe_join(zd["context"]) or "—", language=None)
        with _wcol2:
            st.caption("Behaviour")
            st.code(_safe_join(zd["behaviour"]) or "—", language=None)
        with _wcol3:
            st.caption("Interventions")
            st.code(_safe_join(zd["interventions"]) or "— none logged for this zone —", language=None)



def render_bsem_recommendations(items: list[dict], key_prefix: str):
    """Draws the clickable cards; the print capture records every strategy
    with its why/how in full (not just the cards that happen to be open)."""
    if items:
        _scr_add("bsem", items)
    _prev = _SCREEN["paused"]; _SCREEN["paused"] = True
    try:
        _render_bsem_recommendations_ui(items, key_prefix)
    finally:
        _SCREEN["paused"] = _prev


def render_window_of_tolerance_table(full_df, student_id=None):
    _wd = build_window_of_tolerance_table(full_df, student_id=student_id)
    if _wd:
        _scr_add("caption", "Draft only, built from this student's logged behaviour types and severity. Context is de-identified; "
                            "Behaviour and Interventions stay specific to this student. Review before use.")
        _scr_add("wot", _wd)
    _prev = _SCREEN["paused"]; _SCREEN["paused"] = True
    try:
        _render_window_of_tolerance_table_ui(full_df, student_id=student_id)
    finally:
        _SCREEN["paused"] = _prev


def build_considerations(full_df, top_ant, top_loc, top_session) -> list[str]:
    """Deterministic 'things to consider' prompts — alternative or
    structural explanations to weigh before treating a data pattern as
    purely behavioural (e.g. a morning cluster that's actually a modified
    timetable, or a yard cluster that's actually where the student goes
    to self-regulate). Rule-based rather than AI-generated, since this is
    a fixed checklist of things worth ruling out, not a personalised
    narrative."""
    considerations = []
    if full_df is None or full_df.empty:
        return considerations
    total = len(full_df)

    if total < 6:
        considerations.append(
            f"Only {total} incident(s) recorded so far — the pattern below is an early "
            "signal, not yet a robust trend. Treat any hypothesis as provisional."
        )

    if "session" in full_df.columns and total > 0:
        _sess_counts = full_df["session"].value_counts()
        if not _sess_counts.empty:
            _pct = _sess_counts.iloc[0] / total
            if _pct >= 0.5:
                considerations.append(
                    f"Incidents cluster heavily in the {_sess_counts.index[0]} session "
                    f"({int(_pct*100)}%). Before treating this as purely behavioural, check for a "
                    "structural explanation — a modified timetable, a specific specialist/NIT "
                    "session, medication timing, or an arrival/transport routine that only "
                    "happens at that time."
                )

    if "location" in full_df.columns and total > 0:
        _loc_counts = full_df["location"].value_counts()
        if not _loc_counts.empty:
            _pct = _loc_counts.iloc[0] / total
            if _pct >= 0.5:
                considerations.append(
                    f"Incidents cluster heavily in {_loc_counts.index[0]} ({int(_pct*100)}%). This "
                    "may be what's triggering there — or it may be where the student moves to when "
                    "seeking regulation (a destination, not a trigger), or simply the space they "
                    "spend the most time in. Check where the student was immediately beforehand, "
                    "not only where the incident occurred."
                )

    if "date_parsed" in full_df.columns and total >= 4:
        _dow = full_df["date_parsed"].dt.day_name().value_counts()
        if not _dow.empty:
            _pct = _dow.iloc[0] / total
            if _pct >= 0.4:
                considerations.append(
                    f"A notable share of incidents fall on {_dow.index[0]}s ({int(_pct*100)}%). "
                    "Check the roster and timetable for that day — a TRT, a changed specialist, a "
                    "different transport arrangement, or a weekend-transition effect (e.g. Mondays) "
                    "can produce a day-of-week pattern that looks behavioural but is structural."
                )

    if "behaviour_type" in full_df.columns and total > 0:
        _beh = full_df["behaviour_type"].dropna()
        _beh = _beh[_beh.str.strip() != ""].value_counts()
        if not _beh.empty:
            _pct = _beh.iloc[0] / total
            if _pct >= 0.6:
                considerations.append(
                    f"One behaviour ('{_beh.index[0]}') accounts for {int(_pct*100)}% of records. "
                    "Consider whether this is genuinely the dominant presentation, or whether it's "
                    "simply the most visible behaviour for staff to notice and log — quieter "
                    "presentations (withdrawal, shutdown) can be under-recorded by comparison."
                )

    if not considerations:
        considerations.append(
            "No single pattern in the data is dominant enough to flag a specific structural "
            "explanation — the hypothesis is reasonably well-supported by the spread of "
            "recorded incidents."
        )
    return considerations


def find_combined_patterns(full_df, min_count: int = 3, min_pct: float = 0.2) -> list[dict]:
    """Find where antecedent category, location, and session genuinely
    intersect — a combination that concentrates a disproportionate share
    of incidents is a far stronger, more actionable signal than any single
    axis viewed alone (e.g. 'Peer-triggered incidents in the Yard during
    Middle session' vs three separate top-3 lists that happen to share a
    student in common).

    Returns up to 2 combinations, each accounting for at least min_count
    incidents and at least min_pct of the total, sorted by count desc.
    """
    if full_df is None or full_df.empty:
        return []
    required = {"location", "session"}
    if not required.issubset(full_df.columns):
        return []
    _df = full_df.copy()
    if "_ant_cat" not in _df.columns:
        if "antecedent" not in _df.columns:
            return []
        _df["_ant_cat"] = _df["antecedent"].apply(categorize_antecedent)
    _df = _df.dropna(subset=["_ant_cat"])
    if _df.empty:
        return []
    total = len(full_df)
    _grp = _df.groupby(["_ant_cat", "location", "session"]).size().sort_values(ascending=False)
    combos = []
    for (cat, loc, sess), count in _grp.items():
        pct = count / total
        if count >= min_count and pct >= min_pct:
            combos.append({"category": cat, "location": loc, "session": sess,
                            "count": int(count), "pct": pct})
        if len(combos) >= 2:
            break
    return combos


def render_analysis_snapshot(student, full_df, student_id):
    """A condensed, one-screen view of the key findings for this student —
    an alternative to the full detailed Analysis page for anyone who just
    wants the headline picture without the full set of charts. Reuses
    the same underlying logic as the full page (hypothesis, combined
    patterns, BSEM strategies) so the two views can never disagree with
    each other."""
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1A7A7A 0%,#134e4e 100%);"
        "border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:0.9rem;"
        "box-shadow:0 4px 14px rgba(19,78,78,0.25);'>"
        f"<span style='color:white;font-size:1.3rem;font-weight:700;'>🔎 Snapshot — {student['name']}</span><br>"
        "<span style='color:#d1fae5;font-size:0.85rem;'>The headline findings only — switch to Full "
        "Analysis for every chart and detail behind these.</span></div>",
        unsafe_allow_html=True,
    )

    if full_df.empty:
        st.info("No incidents logged yet for this student.")
        return

    top_beh     = full_df["behaviour_type"].mode()[0] if len(full_df) else "Unknown"
    top_ant     = full_df["antecedent"].mode()[0] if len(full_df) else "Unknown"
    top_loc     = full_df["location"].mode()[0] if len(full_df) else "Unknown"
    top_session = full_df["session"].mode()[0] if len(full_df) else "Unknown"

    def _snap_card(color_hex, bg_hex, icon, heading, body_lines, footnote=None):
        _body = "".join(f"<div style='margin:.25rem 0;'>{line}</div>" for line in body_lines)
        _foot = f"<div style='margin-top:.5rem;font-size:.75rem;color:#64748b;font-style:italic;'>{footnote}</div>" if footnote else ""
        st.markdown(
            f"<div style='background:{bg_hex};border-left:5px solid {color_hex};border-radius:10px;"
            f"padding:.9rem 1.2rem;margin-bottom:.8rem;'>"
            f"<div style='font-weight:700;color:{color_hex};font-size:1.05rem;margin-bottom:.4rem;'>"
            f"{icon}  {heading}</div>"
            f"<div style='font-size:.92rem;color:#1e293b;line-height:1.6;'>{_body}</div>{_foot}</div>",
            unsafe_allow_html=True,
        )

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Incidents", len(full_df))
    with m2: st.metric("Critical", len(full_df[full_df.get("incident_type", "Quick") == "Critical"]))
    with m3: st.metric("Avg Severity", f"{full_df['severity'].mean():.1f}" if "severity" in full_df.columns else "—")
    with m4:
        _direction = "—"
        if len(full_df) >= 5:
            _r_avg = full_df.tail(5)["severity"].mean()
            _e_avg = full_df.head(5)["severity"].mean()
            _direction = "🟢 Reducing" if _r_avg < _e_avg else "🔴 Increasing" if _r_avg > _e_avg else "🟡 Stable"
        st.metric("Severity Trend", _direction)
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    _patterns = [
        f"<b>Most frequent behaviour:</b> {top_beh}",
        f"<b>Most frequent trigger:</b> {top_ant}",
        f"<b>Location hotspot:</b> {normalise_location(top_loc)}",
        f"<b>Peak time:</b> {top_session}",
    ]
    _combos = find_combined_patterns(full_df)
    if _combos:
        c = _combos[0]
        _patterns.append(
            f"<b>Combined pattern:</b> {int(c['pct']*100)}% of incidents are "
            f"{c['category']}-triggered, in {normalise_location(c['location'])}, during {c['session']}"
        )
    _snap_card("#3B82F6", "#EFF6FF", "📌", "Top Patterns", _patterns)

    _reframe_body = []
    _reframe = BEHAVIOUR_REFRAME.get(top_beh)
    if _reframe:
        _reframe_body.append(f"<b>{top_beh}:</b> {_reframe}")
    else:
        _reframe_body.append(f"No reframe on file yet for '{top_beh}'.")
    _cpi_stage = CPI_STAGE_MAP.get(top_beh)
    if _cpi_stage:
        _stage_info = CPI_STAGES[_cpi_stage]
        _reframe_body.append(f"<b>CPI stage:</b> {_cpi_stage} — {_stage_info['desc']}")
        _reframe_body.append(f"<b>Appropriate response:</b> {_stage_info['response']}")
        _reframe_body.append(f"<b>Regulate → Relate → Reason:</b> {_stage_info['smart_stage']}")
    else:
        _reframe_body.append(
            f"<b>CPI Verbal Escalation Continuum:</b> '{top_beh}' sits outside the verbal continuum — "
            "it tracks rising verbal defiance; physical aggression, flight, and freeze/shutdown "
            "presentations belong elsewhere in CPI's broader crisis framework."
        )
    _cats_for_reframe = _top_categories(full_df, n=1)
    if _cats_for_reframe:
        _mgmt = BSEM_STRATEGY_LIBRARY.get(_cats_for_reframe[0], [])[:2]
        if _mgmt:
            _reframe_body.append("<b>Suggested classroom management:</b> " +
                                  "; ".join(f"[{s['domain']}] {s['strategy']}" for s in _mgmt))
    _snap_card("#8B5CF6", "#FAF5FF", "🧠", "Behaviour Reframe", _reframe_body,
               footnote="A starting lens, not a diagnosis — read alongside clinical judgement and what's known about this individual student. Trauma reframing draws on SMART (Strategies for Managing Abuse-Related Trauma), Australian Childhood Foundation; escalation staging draws on CPI's Verbal Escalation Continuum.")

    try:
        _hyp = generate_strong_clinical_hypothesis(full_df, top_ant, top_beh, top_loc, top_session, student["name"])
        _hyp_text = _hyp.get("summary", "Not enough data yet.")
    except Exception:
        _hyp_text = "Not enough data yet."
    _snap_card("#1A7A7A", "#F0FDFA", "🔬", "Hypothesis", [_hyp_text])

    _cats = _top_categories(full_df, n=1)
    _strat_body = []
    if _cats:
        for s in BSEM_STRATEGY_LIBRARY.get(_cats[0], [])[:3]:
            _strat_body.append(f"<b>[{s['domain']}]</b> {s['strategy']}")
    if not _strat_body:
        _strat_body = ["Not enough data yet."]
    _snap_card("#D97706", "#FFFBEB", "💡", "Top Strategies to Trial", _strat_body,
               footnote="Based on the Berry Street Education Model (BSEM) — domains: Body, Relationship, Stamina, Engagement, Character.")

    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("📄 Switch to Full Analysis", type="primary", use_container_width=True, key="snap_to_full"):
            st.session_state[f"analysis_view_mode_{student_id}"] = "📄 Full Analysis"
            st.rerun()
    with sc2:
        if st.button("📋 Support Plan", use_container_width=True, key="snap_to_plan"):
            go_to("support_plan", selected_student_id=student_id)


def render_combined_patterns(full_df):
    """Streamlit UI for find_combined_patterns — a callout box on the
    Analysis page."""
    combos = find_combined_patterns(full_df)
    if not combos:
        return
    st.markdown(
        "<div style='background:#f0f9ff;border-left:4px solid #0284c7;border-radius:8px;"
        "padding:.75rem 1.1rem;margin:.5rem 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown("**🔗 Combined Pattern** — stronger than any single chart above on its own:")
    for c in combos:
        st.markdown(
            f"- **{int(c['pct']*100)}% of all incidents** ({c['count']} of {len(full_df)}) share "
            f"all three conditions: **{c['category']}**-triggered, in **{normalise_location(c['location'])}**, "
            f"during the **{c['session']}** session."
        )
    st.caption("This is the intersection of trigger, location, and time — worth checking as a single, "
               "specific scenario rather than three separate factors.")
    st.markdown("</div>", unsafe_allow_html=True)


def compute_before_after(full_df, trial_date) -> dict | None:
    """Compare incident rate and severity before vs after a given date —
    when a support/strategy was noted as trialled — to check whether it
    actually appears to have made a difference, rather than just
    recording that it was tried. Returns None if trial_date isn't set;
    returns {"insufficient": True} if there isn't enough data on both
    sides to compare yet."""
    if full_df is None or full_df.empty or trial_date is None or "date_parsed" not in full_df.columns:
        return None
    _df = full_df.dropna(subset=["date_parsed"])
    if _df.empty:
        return None
    _trial_ts = pd.Timestamp(trial_date)
    before = _df[_df["date_parsed"] < _trial_ts]
    after  = _df[_df["date_parsed"] >= _trial_ts]
    if len(before) == 0 or len(after) == 0:
        return {"insufficient": True}
    _min_date, _max_date = _df["date_parsed"].min(), _df["date_parsed"].max()
    weeks_before = max((_trial_ts - _min_date).days / 7, 0.1)
    weeks_after  = max((_max_date - _trial_ts).days / 7, 0.1)
    rate_before, rate_after = len(before) / weeks_before, len(after) / weeks_after
    sev_before = float(before["severity"].mean()) if "severity" in before.columns else None
    sev_after  = float(after["severity"].mean())  if "severity" in after.columns  else None
    pct_rate_change = ((rate_after - rate_before) / rate_before * 100) if rate_before > 0 else None
    return {
        "insufficient": False,
        "n_before": len(before), "n_after": len(after),
        "weeks_before": round(weeks_before, 1), "weeks_after": round(weeks_after, 1),
        "rate_before": rate_before, "rate_after": rate_after,
        "sev_before": sev_before, "sev_after": sev_after,
        "pct_rate_change": pct_rate_change,
    }


def render_before_after(ba: dict):
    """Streamlit UI for compute_before_after."""
    if not ba:
        return
    if ba.get("insufficient"):
        st.info("Not enough incidents logged on both sides of the trial date yet to compare — "
                "check back once more data has been recorded.")
        return
    _rate_dir = "fewer" if ba["pct_rate_change"] is not None and ba["pct_rate_change"] < 0 else "more"
    st.markdown(
        f"**Before ({ba['weeks_before']:.1f} wks, {ba['n_before']} incidents):** "
        f"{ba['rate_before']:.1f}/week"
        + (f", avg severity {ba['sev_before']:.1f}" if ba['sev_before'] is not None else "")
    )
    st.markdown(
        f"**After ({ba['weeks_after']:.1f} wks, {ba['n_after']} incidents):** "
        f"{ba['rate_after']:.1f}/week"
        + (f", avg severity {ba['sev_after']:.1f}" if ba['sev_after'] is not None else "")
    )
    if ba["pct_rate_change"] is not None:
        _icon = "🟢" if ba["pct_rate_change"] < -10 else "🔴" if ba["pct_rate_change"] > 10 else "🟡"
        st.markdown(f"{_icon} **{abs(ba['pct_rate_change']):.0f}% {_rate_dir} incidents per week** since the trial date.")
    st.caption("A short 'after' window is a preliminary read, not a conclusion — treat it as an early signal.")


# ── Location normalisation ────────────────────────────────────────────────────
LOCATION_ALIASES = {
    "JP Classroom": "JP Room", "JP classroom": "JP Room", "Junior Primary": "JP Room",
    "JP class room": "JP Room", "JP Class Room": "JP Room", "Jnr Primary": "JP Room",
    "Jnr Primary Room": "JP Room", "Jnr Primary Classroom": "JP Room",
    "PY Classroom": "PY Room", "PY classroom": "PY Room", "Primary Years": "PY Room",
    "PY class room": "PY Room", "PY Class Room": "PY Room", "PY class": "PY Room",
    "SY Classroom": "SY Room", "SY classroom": "SY Room", "Senior Years": "SY Room",
    "SY class room": "SY Room", "SY Class Room": "SY Room",
    "Playground": "Yard", "playground": "Yard",
    "Front Office": "Office", "front office": "Office", "Reception": "Office",
    "Kitchen area": "Kitchen", "kitchen area": "Kitchen",
    "Toilet": "Toilets", "toilet": "Toilets", "Bathroom": "Toilets", "bathroom": "Toilets",
}

def normalise_location(loc: str) -> str:
    """Map free-text location entries to a canonical label. Critical
    incidents record location as free text (staff type it), while the
    Quick Incident Log uses a fixed dropdown (LOCATIONS) — so the same
    physical place easily ends up logged two different ways (e.g. 'JP
    classroom' vs 'JP Room'), and without normalisation they'd show as
    separate bars on every location chart.

    Checks the exact-alias dict first (LOCATION_ALIASES, fast and
    predictable), then falls back to fuzzy matching against the
    canonical LOCATIONS list for close-but-not-identical wording a
    fixed alias list can't fully anticipate. Falls back to the original
    text unchanged if nothing matches closely enough — this only ever
    merges genuinely similar wording, never guesses at something new."""
    if not loc:
        return ""
    _clean = str(loc).strip()
    if _clean in LOCATION_ALIASES:
        return LOCATION_ALIASES[_clean]
    _canonical_lower = {c.lower(): c for c in LOCATIONS}
    if _clean.lower() in _canonical_lower:
        return _canonical_lower[_clean.lower()]
    _matches = difflib.get_close_matches(_clean.lower(), list(_canonical_lower.keys()), n=1, cutoff=0.75)
    if _matches:
        return _canonical_lower[_matches[0]]
    return _clean


# ── Clinical behaviour terminology ───────────────────────────────────────────
CLINICAL_BEHAVIOUR_MAP = {
    "Verbal Refusal":       "Non-compliance with adult directives",
    "Elopement":            "Unsanctioned departure from a supervised area (elopement)",
    "Property Destruction": "Deliberate destruction or damage of property",
    "Aggression (Peer)":    "Physical aggression directed toward a peer",
    "Aggression (Adult)":   "Physical aggression directed toward an adult",
    "Self-Harm":            "Self-injurious behaviour",
    "Verbal Aggression":    "Antisocial verbal outbursts directed toward others",
    "Other":                "Unclassified behaviour of concern",
}

def get_clinical_behaviour(raw: str) -> str:
    """Return professional terminology for a behaviour label."""
    if not raw:
        return raw
    mapped = CLINICAL_BEHAVIOUR_MAP.get(raw)
    if mapped:
        return mapped
    lower = raw.lower()
    if any(w in lower for w in ["hit","kick","punch","push","threw","throw","attack","physical"]):
        return "Physical aggression"
    if any(w in lower for w in ["yell","scream","shout","growl","swear","curse","verbal","shout"]):
        return "Antisocial verbal outburst directed toward others"
    if any(w in lower for w in ["run","elope","left","fled","exit","bolt","absconding"]):
        return "Unsanctioned departure from a supervised area"
    if any(w in lower for w in ["destroy","damage","broke","smash","threw object"]):
        return "Deliberate destruction or damage of property"
    if any(w in lower for w in ["refuse","refus","non-compli","defian","wouldn't","won't"]):
        return "Non-compliance with adult directives"
    if any(w in lower for w in ["self","harm","bite self","scratch self","hit self","head bang"]):
        return "Self-injurious behaviour"
    return raw

INTERVENTIONS = ["CPI Supportive stance", "Offered break", "Reduced demand", "Provided choices",
                "Removed audience", "Visual supports", "Co-regulation", "Prompted coping skill", "Redirection"]
LOCATIONS = ["JP Room", "PY Room", "SY Room", "Yard", "Playground", "Library", "Kitchen", "Office", "Student Gate", "Toilets", "Transition area", "Other"]
VALID_PAGES = ["login", "landing", "program_students", "incident_log", "critical_incident", "review_critical", "leader_approve_critical", "student_analysis", "student_dashboard", "admin_portal", "support_plan"]

HYPOTHESIS_FUNCTIONS = ["To get", "To avoid"]
HYPOTHESIS_ITEMS = ["Tangible", "Activity", "Sensory", "Attention"]

def format_time_12hr(time_str):
    try:
        if isinstance(time_str, str):
            dt = datetime.strptime(time_str, "%H:%M:%S")
        else:
            dt = datetime.combine(date.today(), time_str)
        return dt.strftime("%I:%M %p")
    except:
        return time_str

def generate_hypothesis(antecedent, behaviour, consequence):
    hypotheses = []
    antecedent_lower = antecedent.lower()
    behaviour_lower = behaviour.lower()
    if any(word in antecedent_lower for word in [
        "instruction", "demand", "task", "transition", "work", "non-preferred",
        "literacy", "maths", "wait", "routine", "independently", "difficult"
    ]):
        hypotheses.append("To avoid or escape the demand/task")
    if any(word in antecedent_lower for word in [
        "attention", "shifted", "ignored", "alone", "feedback", "conflict",
        "interaction", "escalating", "injustice"
    ]):
        hypotheses.append("To gain staff/peer attention")
    if any(word in antecedent_lower for word in [
        "sensory", "loud", "noise", "bright", "touch", "crowded", "medication",
        "hungry", "thirsty", "movement"
    ]):
        hypotheses.append("To escape sensory discomfort or seek sensory input")
    if any(word in antecedent_lower for word in [
        "denied", "can't have", "no", "wait", "device", "finish", "preferred"
    ]):
        hypotheses.append("To gain access to preferred item/activity")
    if any(word in behaviour_lower for word in ["refusal", "defiance", "left", "ran", "elopement"]):
        hypotheses.append("To assert control or autonomy")
    if not hypotheses:
        hypotheses.append("Function requires further analysis")
    return " / ".join(hypotheses[:2])

def generate_admin_summary(incident_data, student, staff_name):
    abch_primary = incident_data.get("ABCH_primary", {})
    intended = incident_data.get("intended_outcomes", [])
    date_time = incident_data.get("created_at", datetime.now().isoformat())
    dt = datetime.fromisoformat(date_time)
    location = abch_primary.get("location", "Unknown location")
    time_str = abch_primary.get("time", "Unknown time")
    behaviour = abch_primary.get("behaviour", "Behaviour not specified")
    context = abch_primary.get("context", "")
    consequence = abch_primary.get("consequence", "")
    hypothesis = abch_primary.get("hypothesis", "")
    summary = f"""CRITICAL INCIDENT SUMMARY - FOR ADMIN USE ONLY

Student: {student['name']} (Grade {student['grade']})
Date/Time: {dt.strftime('%d/%m/%Y')} at {time_str}
Location: {location}

INCIDENT DESCRIPTION:
{behaviour[:200]}{'...' if len(behaviour) > 200 else ''}

CONTEXT/ANTECEDENT:
{context[:200]}{'...' if len(context) > 200 else ''}

IMMEDIATE STAFF RESPONSE:
{consequence[:200]}{'...' if len(consequence) > 200 else ''}

BEHAVIOURAL FUNCTION:
{hypothesis}

OUTCOMES IMPLEMENTED:
{', '.join(intended[:5]) if intended else 'See full form for details'}

REPORTED BY: {staff_name}
FORM COMPLETED: {dt.strftime('%d/%m/%Y %H:%M')}

** This summary is for external departmental incident log entry purposes only **
** Full critical incident form has been saved and distributed to relevant parties **
"""
    return summary

def generate_hypothesis_ai(antecedent, behaviour, consequence=""):
    ant_lower = (antecedent or "").lower()
    beh_lower = (behaviour or "").lower()
    cons_lower = (consequence or "").lower()
    avoid_keywords = ["instruction","demand","task","transition","work","difficult","challenging",
        "non-preferred","literacy","maths","wait","routine","peer","independently","interrupted","finish","teacher coming"]
    get_keywords = ["attention","item","toy","want","access","denied","device","finish","preferred","competition","feedback"]
    sensory_keywords = ["sensory","loud","noise","touch","bright","crowded","medication","hungry","thirsty","movement break"]
    attention_keywords = ["attention","staff","peer","ignored","escalating","feedback","conflict","interaction","injustice"]
    function = "To avoid"
    if any(word in ant_lower for word in get_keywords):
        function = "To get"
    elif any(word in cons_lower for word in ["given","received","got","obtained"]):
        function = "To get"
    elif "denied" in ant_lower or "can't" in ant_lower or "wait" in ant_lower:
        function = "To get"
    elif "off a device" in ant_lower or "finish" in ant_lower:
        function = "To get"
    item = "Activity"
    if any(word in ant_lower + beh_lower for word in attention_keywords):
        item = "Attention"
    elif any(word in ant_lower + beh_lower for word in sensory_keywords):
        item = "Sensory"
    elif any(word in ant_lower + beh_lower for word in ["toy","item","object","food","device","tangible"]):
        item = "Tangible"
    elif any(word in ant_lower for word in ["instruction","demand","task","work","learning","maths","literacy"]):
        item = "Activity"
    elif "transition" in ant_lower or "environment" in ant_lower or "classroom" in ant_lower:
        item = "Activity"
    return {"function": function, "item": item}

def format_hypothesis(hyp):
    if isinstance(hyp, dict):
        return f"{hyp.get('function', 'Unknown')} {hyp.get('item', 'Unknown')}"
    elif isinstance(hyp, str):
        return hyp
    else:
        return "Unknown"

def generate_strong_clinical_hypothesis(full_df, top_ant, top_beh, top_loc, top_session, student_name):
    """Return a dict with a detailed evidence-based functional hypothesis."""
    import pandas as _pd
    total = len(full_df)
    if total == 0:
        return {"summary": "Insufficient data to generate hypothesis.", "detail": {}}

    ant_lower = str(top_ant).lower()
    beh_clinical = get_clinical_behaviour(top_beh)

    escape_kw  = ["instruction","demand","task","transition","work","difficult","non-preferred",
                  "literacy","maths","wait","routine","independently","interrupted","finish","teacher coming"]
    access_kw  = ["attention","denied","device","preferred","competition","feedback","tangible",
                  "item","toy","food","want","access"]
    sensory_kw = ["sensory","noise","loud","bright","crowded","medication","hungry","thirsty",
                  "movement","no medication"]

    escape_score  = sum(1 for w in escape_kw  if w in ant_lower)
    access_score  = sum(1 for w in access_kw  if w in ant_lower)
    sensory_score = sum(1 for w in sensory_kw if w in ant_lower)

    if sensory_score > 0 and sensory_score >= escape_score and sensory_score >= access_score:
        function_verb = "escape or reduce"
        function_item = "sensory discomfort or physiological dysregulation"
        bsem_domain   = "Body domain (regulation)"
        hyp_function  = "To escape / sensory"
    elif escape_score >= access_score:
        function_verb = "escape or avoid"
        function_item = "the instructional demand, task, or transition"
        bsem_domain   = "Stamina domain (task persistence)"
        hyp_function  = "To avoid / activity"
    else:
        function_verb = "gain access to"
        function_item = "a preferred item, activity, or adult/peer attention"
        bsem_domain   = "Relationship domain (connection)"
        hyp_function  = "To get / attention or tangible"

    if "peer"       in ant_lower: ant_category = "peer-related interactions"
    elif "transition" in ant_lower: ant_category = "transitional demands"
    elif "instruction" in ant_lower or "demand" in ant_lower: ant_category = "instructional demands"
    elif "sensory"  in ant_lower or "noise" in ant_lower: ant_category = "sensory-environmental factors"
    elif "engagement" in ant_lower or "task" in ant_lower: ant_category = "academic engagement demands"
    else: ant_category = "contextual antecedent triggers"

    has_type = "incident_type" in full_df.columns
    crit_cnt = int(len(full_df[full_df["incident_type"] == "Critical"])) if has_type else 0
    crit_pct = int(crit_cnt / total * 100) if total else 0
    avg_sev  = round(float(full_df["severity"].mean()), 1) if "severity" in full_df.columns else 0

    summary = (
        f"Based on analysis of {total} recorded incidents, it is hypothesised that "
        f"{student_name}'s {beh_clinical.lower()} functions primarily to {function_verb} "
        f"{function_item}. The behaviour is most consistently preceded by {ant_category}, "
        f"occurring predominantly during the {top_session.lower()} session "
        f"in {top_loc}. From a trauma-informed and Berry Street Education Model perspective, "
        f"this behaviour constitutes a stress response — a communicative act signalling an unmet "
        f"need within the {bsem_domain} — rather than wilful non-compliance. "
        f"A mean incident severity of {avg_sev}/5 with a {crit_pct}% critical escalation rate "
        f"indicates that antecedent-stage intervention is the highest priority. "
        f"Proactive, function-based supports targeted at {ant_category} are recommended."
    )

    detail = {
        "Behavioural Function":     hyp_function,
        "Primary Antecedent":       ant_category.capitalize(),
        "BSEM Domain Priority":     bsem_domain.capitalize(),
        "Behaviour Label": beh_clinical,
        "Peak Context":             f"{top_session} session · {top_loc}",
        "Risk Indicator":           f"Mean severity {avg_sev}/5 · {crit_pct}% critical escalation",
    }
    return {"summary": summary, "detail": detail}


def show_severity_guide():
    with st.expander("📊 Behaviour Severity Continuum Guide", expanded=False):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown("### 🟢 Level 1")
            st.caption("**Low Level / Engaged**")
            st.markdown("**Examples:**")
            st.markdown("- Following instructions\n- Minor defiance\n- Answering back\n- Mumbling\n- Attention seeking")
        with col2:
            st.markdown("### 🟡 Level 2")
            st.caption("**Escalating**")
            st.markdown("**Examples:**")
            st.markdown("- Raised voice\n- Arguing\n- Frustration\n- Crying\n- Pacing")
        with col3:
            st.markdown("### 🟠 Level 3")
            st.caption("**High Risk**")
            st.markdown("**Examples:**")
            st.markdown("- Yelling, swearing\n- Throwing items\n- Property damage\n- Attempting to run")
        with col4:
            st.markdown("### 🔴 Level 4")
            st.caption("**Dangerous**")
            st.markdown("**Examples:**")
            st.markdown("- Attempts to hit/kick\n- Dangerous objects\n- Threats of violence\n- Absconding")
        with col5:
            st.markdown("### ⚫ Crisis")
            st.caption("**Crisis Situation**")
            st.markdown("**Examples:**")
            st.markdown("- Physical violence\n- Severe self-harm\n- Use of weapons\n- Loss of control")
        st.warning("⚠️ **Level 3 or above requires a Critical Incident ABCH Form**")

def send_critical_incident_email(incident_data, student, staff_email, leader_email, admin_email):
    st.info(f"""📧 **Email Notification Sent**

**To:** {leader_email}, {admin_email}, {staff_email}
**Subject:** CRITICAL INCIDENT - {student['name']}

Critical Incident Form completed and saved.
*(In production, this sends via SMTP)*
    """)


def generate_behaviour_analysis_plan_docx(student, full_df, top_ant, top_beh, top_loc, top_session, risk_score, risk_level,
                                           supports_trialled: str = "", supports_success: str = "", before_after: dict = None,
                                           full_pack: bool = False, bsem_items: list = None, trials: list = None):
    """Generate professional BAP — fixed chart sizing and page layout.

    full_pack=True produces the printable "Full Analysis" version: everything in the
    standard summary PLUS the on-screen-only sections (Window of Tolerance table,
    combined patterns, considerations, BSEM recommendations, antecedent categories),
    a complete incident register and a blank meetings-notes/actions page."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import matplotlib.dates as mdates
        import numpy as np
        import textwrap

        TEAL_HEX   = "1A7A6E"
        TEAL_LIGHT = "D6EEEB"
        AMBER_HEX  = "D97706"
        AMBER_LIGHT= "FEF3C7"
        GREY_DARK  = "2E4057"
        WHITE      = "FFFFFF"
        LIGHT_GREY = "F2F6F6"

        FIG_W    = 14.0   # wide, but a saner aspect ratio once scaled to page width
        FIG_H    = 6.5    # taller — was 4.2, which read as a thin illegible strip once shrunk to fit the page
        FIG_DPI  = 170    # sharper for printing
        DOC_W    = Cm(17.0)  # stays inside the printable area (21cm page − 1.8cm margins each side = 17.4cm)
        MAX_LABEL_CHARS = 42

        def wrap_labels(labels, width=MAX_LABEL_CHARS):
            out = []
            for lbl in labels:
                if len(lbl) > width:
                    out.append(lbl[:width-1] + "…")
                else:
                    out.append(lbl)
            return out

        def rgb(h):
            h = h.lstrip("#")
            return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

        def set_bg(cell, hex_color):
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto')
            shd.set(qn('w:fill'), hex_color.lstrip("#")); tcPr.append(shd)

        def set_borders(cell, color="1A7A6E", size="4"):
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            tcB = OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                b = OxmlElement(f'w:{side}')
                b.set(qn('w:val'),'single'); b.set(qn('w:sz'),size)
                b.set(qn('w:space'),'0'); b.set(qn('w:color'), color.lstrip("#"))
                tcB.append(b)
            tcPr.append(tcB)

        def arun(para, text, bold=False, italic=False, size=18, color="000000"):
            run = para.add_run(text)
            run.bold = bold; run.italic = italic
            run.font.size = Pt(size/2)
            run.font.color.rgb = rgb(color)
            run.font.name = "Arial"
            return run

        def cpara(cell, text, bold=False, italic=False, size=18, color="000000",
                  align=WD_ALIGN_PARAGRAPH.LEFT, sb=40, sa=40):
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(sb/20)
            p.paragraph_format.space_after  = Pt(sa/20)
            p.alignment = align
            if text: arun(p, text, bold=bold, italic=italic, size=size, color=color)
            return p

        def section_header(doc, text):
            tbl = doc.add_table(rows=1, cols=1)
            tbl.style = 'Table Grid'
            cell = tbl.rows[0].cells[0]
            set_bg(cell, GREY_DARK); set_borders(cell, TEAL_HEX)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after  = Pt(2)
            arun(p, text, bold=True, size=17, color=WHITE)

        def add_chart(doc, fig, caption_text):
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=FIG_DPI,
                        bbox_inches='tight', facecolor='white', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            doc.add_picture(buf, width=DOC_W)
            pic_para = doc.paragraphs[-1]
            pic_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pic_para.paragraph_format.space_before = Pt(2)
            pic_para.paragraph_format.space_after  = Pt(0)
            # Keep the image glued to its caption — never split across a page break
            pic_para.paragraph_format.keep_together = True
            pic_para.paragraph_format.keep_with_next = True
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_before = Pt(1)
            cap.paragraph_format.space_after  = Pt(6)
            cap.paragraph_format.keep_together = True
            run = cap.add_run(caption_text)
            run.font.size = Pt(10)   # increased for print readability
            run.font.italic = True
            run.font.color.rgb = rgb("333333")
            run.font.name = "Arial"

        def base_ax_style(ax):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#cbd5e1')
            ax.spines['bottom'].set_color('#cbd5e1')
            ax.tick_params(colors='#334155', labelsize=10)
            ax.grid(True, alpha=0.25, linestyle='--', color='#94a3b8')

        doc = Document()
        sec = doc.sections[0]
        sec.page_width  = Cm(21)
        sec.page_height = Cm(29.7)
        for attr in ('left_margin','right_margin','top_margin','bottom_margin'):
            setattr(sec, attr, Cm(1.8))

        t = doc.add_table(rows=1, cols=1); t.style='Table Grid'
        tc = t.rows[0].cells[0]
        set_bg(tc, TEAL_HEX); set_borders(tc, TEAL_HEX)
        p1 = tc.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        arun(p1, "FULL ANALYSIS — PRINT PACK" if full_pack else "BEHAVIOUR SUMMARY", bold=True, size=28 if not full_pack else 24, color=WHITE)
        cpara(tc, f"{student['name']}  |  Cowandilla Learning Centre  |  LBU {student.get('program','')} Program",
              size=17, color="FEF3C7", align=WD_ALIGN_PARAGRAPH.CENTER, sb=10, sa=30)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        det = doc.add_table(rows=3, cols=2); det.style='Table Grid'
        hdr = det.rows[0].cells[0].merge(det.rows[0].cells[1])
        set_bg(hdr, GREY_DARK); set_borders(hdr, TEAL_HEX)
        hdr.paragraphs[0].paragraph_format.space_before = Pt(2)
        hdr.paragraphs[0].paragraph_format.space_after  = Pt(2)
        arun(hdr.paragraphs[0], "STUDENT DETAILS", bold=True, size=16, color=WHITE)

        PROGRAM_NAMES_LOCAL = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years"}
        for ci, items in enumerate([
            [("Student", student['name']),
             ("Program", PROGRAM_NAMES_LOCAL.get(student.get('program',''), student.get('program',''))),
             ("Grade",   student.get('grade','—'))],
            [("Analysis Date", datetime.now().strftime('%d %B %Y')),
             ("Data Period",   f"{full_df['date_parsed'].min().strftime('%d/%m/%Y')} – {full_df['date_parsed'].max().strftime('%d/%m/%Y')}"),
             ("Total incidents", str(len(full_df)))]
        ]):
            c = det.rows[1].cells[ci]
            set_bg(c, LIGHT_GREY); set_borders(c, TEAL_HEX)
            c.paragraphs[0].clear()
            for label, val in items:
                p = c.add_paragraph()
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after  = Pt(1)
                arun(p, f"{label}: ", bold=True, size=16, color=GREY_DARK)
                arun(p, val, size=18)

        sum_cell = det.rows[2].cells[0].merge(det.rows[2].cells[1])
        set_bg(sum_cell, AMBER_LIGHT); set_borders(sum_cell, AMBER_HEX)
        p_s = sum_cell.paragraphs[0]
        p_s.paragraph_format.space_before = Pt(3)
        p_s.paragraph_format.space_after  = Pt(3)
        arun(p_s, "Summary:  ", bold=True, size=16, color=AMBER_HEX)
        arun(p_s, f"Total incidents: {len(full_df)}   |   "
                  f"Critical: {len(full_df[full_df['incident_type']=='Critical'])}", size=16)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        kf = doc.add_table(rows=1, cols=1); kf.style='Table Grid'
        kf_c = kf.rows[0].cells[0]
        set_bg(kf_c, TEAL_LIGHT); set_borders(kf_c, TEAL_HEX)
        kf_c.paragraphs[0].clear()
        p_kf = kf_c.paragraphs[0]
        p_kf.paragraph_format.space_before = Pt(3)
        arun(p_kf, "KEY FINDINGS", bold=True, size=16, color=TEAL_HEX)
        for label, val in [
            ("Primary behaviour of concern",     get_clinical_behaviour(top_beh)),
            ("Most common trigger / antecedent", top_ant[top_ant.find(" - ")+3:] if " - " in top_ant else top_ant),
            ("Hotspot location",                 normalise_location(top_loc)),
            ("Peak time of day",                 f"{top_session} (before 11am / 11am–13:30 / after 13:31)"),
        ]:
            p = kf_c.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after  = Pt(2)
            arun(p, f"{label}:  ", bold=True, size=15, color=GREY_DARK)
            arun(p, val, size=15)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── AT A GLANCE: hypothesis summary + top strategies ──
        # (front-page condensed view — full detail follows after the page break)
        hyp_data_front = generate_strong_clinical_hypothesis(
            full_df, top_ant, top_beh, top_loc, top_session, student["name"])

        if hyp_data_front.get("summary"):
            fh = doc.add_table(rows=1, cols=1); fh.style = 'Table Grid'
            fh_c = fh.rows[0].cells[0]
            set_bg(fh_c, TEAL_LIGHT); set_borders(fh_c, TEAL_HEX)
            fh_c.paragraphs[0].clear()
            p_fh = fh_c.paragraphs[0]
            p_fh.paragraph_format.space_before = Pt(3); p_fh.paragraph_format.space_after = Pt(3)
            arun(p_fh, "FUNCTIONAL HYPOTHESIS (Summary):  ", bold=True, size=15, color=TEAL_HEX)
            arun(p_fh, hyp_data_front["summary"], size=15)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        _front_cats = _top_categories(full_df, n=1)
        if _front_cats:
            _front_strats = BSEM_STRATEGY_LIBRARY.get(_front_cats[0], [])[:3]
            if _front_strats:
                ts = doc.add_table(rows=1, cols=1); ts.style = 'Table Grid'
                ts_c = ts.rows[0].cells[0]
                set_bg(ts_c, AMBER_LIGHT); set_borders(ts_c, AMBER_HEX)
                ts_c.paragraphs[0].clear()
                p_ts = ts_c.paragraphs[0]
                p_ts.paragraph_format.space_before = Pt(3)
                arun(p_ts, "TOP STRATEGIES TO TRIAL", bold=True, size=15, color=AMBER_HEX)
                for _s in _front_strats:
                    p = ts_c.add_paragraph()
                    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
                    arun(p, f"[{_s['domain']}] ", bold=True, size=14, color=GREY_DARK)
                    arun(p, _s["strategy"], size=14)
                p_more = ts_c.add_paragraph()
                p_more.paragraph_format.space_before = Pt(4)
                arun(p_more, "See Support Lens and Teaching Lens sections (below) for the full set.",
                     italic=True, size=13, color=GREY_DARK)

        if (supports_trialled or "").strip() or (supports_success or "").strip() or (before_after and not before_after.get("insufficient")):
            doc.add_paragraph().paragraph_format.space_after = Pt(3)
            tr = doc.add_table(rows=1, cols=1); tr.style = 'Table Grid'
            tr_c = tr.rows[0].cells[0]
            set_bg(tr_c, LIGHT_GREY); set_borders(tr_c, GREY_DARK)
            tr_c.paragraphs[0].clear()
            p_tr = tr_c.paragraphs[0]
            p_tr.paragraph_format.space_before = Pt(3)
            arun(p_tr, "SUPPORTS TRIALLED & OUTCOMES", bold=True, size=15, color=GREY_DARK)
            if (supports_trialled or "").strip():
                p1 = tr_c.add_paragraph()
                p1.paragraph_format.space_before = Pt(3); p1.paragraph_format.space_after = Pt(2)
                arun(p1, "Trialled:  ", bold=True, size=14, color=GREY_DARK)
                arun(p1, supports_trialled.strip(), size=14)
            if (supports_success or "").strip():
                p2 = tr_c.add_paragraph()
                p2.paragraph_format.space_before = Pt(2); p2.paragraph_format.space_after = Pt(3)
                arun(p2, "Outcome:  ", bold=True, size=14, color=GREY_DARK)
                arun(p2, supports_success.strip(), size=14)
            if before_after and not before_after.get("insufficient"):
                p3 = tr_c.add_paragraph()
                p3.paragraph_format.space_before = Pt(3); p3.paragraph_format.space_after = Pt(2)
                arun(p3, "Before/After:  ", bold=True, size=14, color=GREY_DARK)
                _rate_dir = "fewer" if before_after["pct_rate_change"] is not None and before_after["pct_rate_change"] < 0 else "more"
                _txt = (f"Before ({before_after['weeks_before']:.1f} wks): {before_after['rate_before']:.1f}/week. "
                        f"After ({before_after['weeks_after']:.1f} wks): {before_after['rate_after']:.1f}/week.")
                if before_after["pct_rate_change"] is not None:
                    _txt += f" ({abs(before_after['pct_rate_change']):.0f}% {_rate_dir} incidents per week since the trial date — preliminary read.)"
                arun(p3, _txt, size=14)

        doc.add_page_break()

        p_detail_note = doc.add_paragraph()
        p_detail_note.paragraph_format.space_after = Pt(6)
        arun(p_detail_note, "The pages below expand on the summary above with full charts, "
             "the complete functional hypothesis, and the full recommendation set.",
             italic=True, size=14, color=GREY_DARK)

        section_header(doc, "VISUAL ANALYTICS — FREQUENCY PATTERNS")
        p_sp = doc.add_paragraph(); p_sp.paragraph_format.space_after = Pt(4)

        # Show all SCHOOL days in range (weekends excluded) so gaps reflect
        # actual attendance days, not calendar days
        import datetime as _bdt
        _b_start = full_df["date_parsed"].min().date()
        _b_end   = full_df["date_parsed"].max().date()
        _b_all_days = []
        _b_d = _b_start
        while _b_d <= _b_end:
            if _b_d.weekday() < 5:
                _b_all_days.append(_b_d)
            _b_d += _bdt.timedelta(days=1)
        _b_counts_map = full_df.groupby(full_df["date_parsed"].dt.date).size().to_dict()
        daily_all = [(_b_d, _b_counts_map.get(_b_d, 0)) for _b_d in _b_all_days]
        daily = type("obj", (object,), {
            "date_parsed": [x[0] for x in daily_all],
            "count":       [x[1] for x in daily_all]
        })()
        # Compute summary stats for chart 1 caption
        _fi_total_days_bap    = len(_b_all_days)
        _fi_incident_days_bap = sum(1 for v in daily.count if v > 0)
        _fi_max_day_bap       = max(daily.count) if daily.count else 0
        _fi_avg_per_day_bap   = sum(daily.count) / max(_fi_incident_days_bap, 1)
        _fi_high_days_bap     = sum(1 for v in daily.count if v >= 3)
        # Count consecutive incident days
        _fi_consec_bap = 0
        _prev_had = False
        for _cv in daily.count:
            if _cv > 0 and _prev_had:
                _fi_consec_bap += 1
            _prev_had = _cv > 0
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        bar_colours = ['#94a3b8' if v == 0 else '#C0392B' if v >= 3 else '#1A7A6E' for v in daily.count]
        bars = ax.bar(range(len(daily.count)), daily.count,
                      color=bar_colours, width=0.7, edgecolor='white', linewidth=0.6)
        ax.set_xticks(range(len(daily.count)))
        ax.set_xticklabels([d.strftime("%a %d/%m") for d in daily.date_parsed],
                           fontsize=7, rotation=35, ha='right')
        ax.set_ylabel("Incidents", fontsize=10, fontweight='bold', color='#334155')
        ax.set_title("1.  Daily Incident Frequency",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, daily.count):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        str(int(v)), ha='center', va='bottom', fontsize=9, fontweight='bold', color='#0f172a')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        add_chart(doc, fig,
            f"{_fi_incident_days_bap} of {_fi_total_days_bap} school days had at least one incident "
            f"(weekends excluded), averaging {_fi_avg_per_day_bap:.1f} per active day (peak: {_fi_max_day_bap}). "
            + (f"{_fi_high_days_bap} spike day(s) had 3 or more incidents — worth reviewing what was "
               "different about staffing, timetable, or demands that day. "
               if _fi_high_days_bap > 0 else "") +
            (f"{_fi_consec_bap} instance(s) of consecutive high-incident days — may point to insufficient "
             "recovery time between episodes, or a sustained stressor across multiple days."
             if _fi_consec_bap >= 2 else ""))

        beh_counts = full_df["behaviour_type"].value_counts().head(6)
        # Use clinical terminology and filter out raw ABCH narratives (>80 chars)
        _bap_beh_clean = [(get_clinical_behaviour(b) if len(str(b)) <= 80 else b[:55]+"…", v)
                          for b, v in zip(beh_counts.index, beh_counts.values)]
        _bap_beh_labels = [x[0] for x in _bap_beh_clean]
        _bap_beh_vals   = [x[1] for x in _bap_beh_clean]
        beh_counts_vals = _bap_beh_vals
        labels_beh = wrap_labels(_bap_beh_labels[::-1])
        chart_colours = ['#C0392B','#E67E22','#1A7A6E','#2E4057','#D97706','#5D6D7E']
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        y_pos = range(len(labels_beh))
        bars = ax.barh(y_pos, _bap_beh_vals[::-1],
                       color=chart_colours[:len(_bap_beh_vals)], edgecolor='white', height=0.6)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels_beh, fontsize=8)
        ax.set_xlabel("Number of incidents", fontsize=10, fontweight='bold', color='#334155')
        ax.set_title("2.  Behaviours of Concern — Frequency",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, _bap_beh_vals[::-1]):
            ax.text(v + 0.08, bar.get_y() + bar.get_height()/2,
                    str(int(v)), va='center', fontsize=9, fontweight='bold', color='#0f172a')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        add_chart(doc, fig,
            f"Most frequent: {_bap_beh_labels[0] if _bap_beh_labels else 'Unknown'} "
            f"({_bap_beh_vals[0] if _bap_beh_vals else 0} of {len(full_df)} incidents, "
            f"{int((_bap_beh_vals[0] if _bap_beh_vals else 0)/max(len(full_df),1)*100)}% of total).")

        ant_counts = full_df["antecedent"].value_counts().head(6)
        # Strip category prefix (e.g. "Peer - " → "peer conflict/interaction")
        def _strip_ant(a):
            a = str(a)
            if " - " in a: a = a[a.find(" - ")+3:]
            return a[:60] + ("…" if len(a) > 60 else "")
        labels_ant = wrap_labels([_strip_ant(a) for a in list(ant_counts.index[::-1])])
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        y_pos = range(len(labels_ant))
        bars = ax.barh(y_pos, ant_counts.values[::-1],
                       color='#2E4057', edgecolor='white', height=0.6)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels_ant, fontsize=7.5)
        ax.set_xlabel("Number of incidents preceded by this trigger",
                      fontsize=10, fontweight='bold', color='#334155')
        ax.set_title("3.  Most Common Triggers / Antecedents",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, ant_counts.values[::-1]):
            ax.text(v + 0.08, bar.get_y() + bar.get_height()/2,
                    f"{int(v)}×", va='center', fontsize=8, fontweight='bold', color='#2E4057')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        add_chart(doc, fig,
            f"Most frequent trigger: '{wrap_labels([top_ant], width=60)[0]}' "
            f"({int(ant_counts.values[0])} of {len(full_df)} incidents, "
            f"{int(ant_counts.values[0]/max(len(full_df),1)*100)}% of total).")

        doc.add_page_break()

        section_header(doc, "VISUAL ANALYTICS — TIME, LOCATION & SEVERITY")
        p_sp2 = doc.add_paragraph(); p_sp2.paragraph_format.space_after = Pt(4)

        SESSION_LABELS = {
            'Morning':   'Morning\nBefore 11:00am',
            'Middle':    'Middle of day\n11:00am – 1:30pm',
            'Afternoon': 'Afternoon\n1:31pm – 2:45pm',
        }
        session_order = ['Morning', 'Middle', 'Afternoon']
        session_counts = full_df["session"].value_counts().reindex(session_order, fill_value=0)
        peak_idx = int(session_counts.values.argmax())
        bar_colours_s = ['#E67E22' if i == peak_idx else '#1A7A6E'
                         for i in range(len(session_order))]
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        x_pos = [0, 1, 2]
        bars = ax.bar(x_pos, session_counts.values,
                      color=bar_colours_s, edgecolor='white', linewidth=1, width=0.45)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([SESSION_LABELS[s] for s in session_order],
                           fontsize=8.5, linespacing=1.3)
        ax.set_ylabel("Number of incidents", fontsize=10, fontweight='bold', color='#334155')
        ax.set_title("4.  Incidents by Time of Day  —  orange = peak session",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, session_counts.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    str(int(v)), ha='center', va='bottom', fontsize=11, fontweight='bold', color='#0f172a')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        peak_name = session_order[peak_idx]
        add_chart(doc, fig,
            f"Peak session: {SESSION_LABELS[peak_name].replace(chr(10),' ')} — "
            f"{int(session_counts[peak_name])} of {len(full_df)} incidents "
            f"({int(session_counts[peak_name]/max(len(full_df),1)*100)}%).")

        loc_counts = full_df["location"].value_counts().head(6)
        labels_loc = wrap_labels(list(loc_counts.index[::-1]))
        loc_colours = ['#C0392B' if i == len(loc_counts)-1 else '#1A7A6E'
                       for i in range(len(loc_counts))]
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        y_pos = range(len(labels_loc))
        bars = ax.barh(y_pos, loc_counts.values[::-1],
                       color=loc_colours, edgecolor='white', height=0.6)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels_loc, fontsize=8.5)
        ax.set_xlabel("Number of incidents in this location",
                      fontsize=10, fontweight='bold', color='#334155')
        ax.set_title("5.  Location Hotspots  —  red = highest frequency",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, loc_counts.values[::-1]):
            ax.text(v + 0.08, bar.get_y() + bar.get_height()/2,
                    f"{int(v)} incidents", va='center', fontsize=9, fontweight='bold', color='#0f172a')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        add_chart(doc, fig,
            f"Highest-frequency location: {normalise_location(top_loc)} "
            f"({int(loc_counts.values[-1])} of {len(full_df)} incidents, "
            f"{int(loc_counts.values[-1]/max(len(full_df),1)*100)}% of total).")

        # WoT for incidents: yellow/orange=coping (severity 1–3), red=outside window (severity 4–5)
        sev_colours = {1:'#eab308',2:'#eab308',3:'#f97316',4:'#ef4444',5:'#7f1d1d'}
        sev_level_names = {1:'Severity 1 (Minor)',2:'Severity 2 (Low)',3:'Severity 3 (Moderate)',
                           4:'Severity 4 (Serious)',5:'Severity 5 (Critical)'}
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        ax.axhspan(0.5, 3.5,  color='#fef9c3', alpha=0.35, zorder=0)  # yellow — coping zone severity 1–3
        ax.axhspan(3.5, 5.5,  color='#fee2e2', alpha=0.30, zorder=0)  # red — outside window severity 4–5
        for y, lbl, col in [(1.5,'Within window (regulated)','#16a34a'),
                            (3.0,'Coping','#f97316'),
                            (4.5,'Outside window','#ef4444')]:
            ax.text(full_df['date_parsed'].min(), y, lbl,
                    fontsize=6.5, color=col, alpha=0.6, va='center', style='italic')
        for sev in [1,2,3,4,5]:
            mask = full_df['severity'] == sev
            if mask.any():
                ax.scatter(full_df.loc[mask,'date_parsed'], full_df.loc[mask,'severity'],
                           s=45, color=sev_colours[sev], alpha=0.85,
                           label=sev_level_names[sev], edgecolors='white', linewidth=0.6, zorder=5)
        if len(full_df) >= 4:
            x_num = np.arange(len(full_df))
            z = np.polyfit(x_num, full_df['severity'], 1)
            p_poly = np.poly1d(z)
            trend_col = '#22c55e' if z[0] < 0 else '#ef4444'
            ax.plot(full_df['date_parsed'], p_poly(x_num),
                    color=trend_col, linewidth=2, linestyle='--',
                    label='Trend ↓ improving' if z[0]<0 else 'Trend ↑ worsening', zorder=4)
        ax.set_xlabel("Date", fontsize=10, fontweight='bold', color='#334155')
        ax.set_yticks([1,2,3,4,5])
        ax.set_yticklabels(['1\nMinor','2\nLow','3\nModerate','4\nSerious','5\nCritical'], fontsize=7)
        ax.set_ylim(0.3, 5.7)
        ax.set_title("6.  Severity Trajectory — Window of Tolerance",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.legend(loc='upper right', frameon=True, fontsize=6.5,
                  framealpha=0.85, ncol=3, borderpad=0.4, handlelength=1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        plt.xticks(rotation=25, ha='right', fontsize=7.5)
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        r_avg = e_avg = full_df["severity"].mean() if len(full_df) > 0 else 0  # defaults
        direction = "stable"
        if len(full_df) >= 5:
            r_avg = full_df.tail(5)['severity'].mean()
            e_avg = full_df.head(5)['severity'].mean()
            direction = "reducing" if r_avg < e_avg else "increasing" if r_avg > e_avg else "stable"
        elif len(full_df) > 0:
            direction = "insufficient data for trend"
        add_chart(doc, fig,
            f"Severity trend: {direction} (early average {e_avg:.1f} → recent average {r_avg:.1f})."
            + ({
               "reducing": f" Reduced by {abs(round(r_avg-e_avg,1))} points — a positive indicator worth sustaining.",
               "increasing": f" Increased by {abs(round(r_avg-e_avg,1))} points — the most significant finding here; a case review is warranted.",
               "stable": " Holding steady — current supports are maintaining functioning without a clear recovery trend.",
              }.get(direction, "")))

        doc.add_page_break()

        # ── Chart 7: Day of Week ─────────────────────────────────────────
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        _school_days_bap = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        _dow_bap = full_df["day"].value_counts().reindex(_school_days_bap, fill_value=0) \
            if "day" in full_df.columns \
            else full_df["date_parsed"].dt.day_name().value_counts().reindex(_school_days_bap, fill_value=0)
        if _dow_bap.sum() >= 3:
            _dow_avg_bap = _dow_bap.mean()
            _dow_cols_bap = ["#ef4444" if v >= _dow_avg_bap * 1.5 else "#1A7A7A" if v >= _dow_avg_bap * 0.8 else "#94a3b8"
                             for v in _dow_bap.values]
            fig, ax = plt.subplots(figsize=(FIG_W, FIG_H * 0.8), dpi=FIG_DPI)
            bars = ax.bar(_school_days_bap, _dow_bap.values,
                          color=_dow_cols_bap, edgecolor="white", linewidth=0.6)
            ax.axhline(_dow_avg_bap, color="#94a3b8", linestyle="--", linewidth=1,
                       label=f"Daily avg: {_dow_avg_bap:.1f}")
            for bar, v in zip(bars, _dow_bap.values):
                if v > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                            str(int(v)), ha="center", va="bottom", fontsize=8,
                            fontweight="bold", color="#0f172a")
            ax.set_ylabel("Total incidents", fontsize=8.5, fontweight="bold", color="#334155")
            ax.set_title("7.  Incident Frequency by Day of Week  —  red = significantly above average",
                         fontsize=9.5, fontweight="bold", color="#0f172a", pad=6, loc="left")
            ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            base_ax_style(ax)
            plt.tight_layout(pad=0.4)
            _dow_peak_bap = _dow_bap.idxmax()
            _dow_peak_n_bap = int(_dow_bap.max())
            _dow_low_bap = _dow_bap[_dow_bap > 0].idxmin() if (_dow_bap > 0).any() else ""
            add_chart(doc, fig,
                f"Peak incident day: {_dow_peak_bap} ({_dow_peak_n_bap} incidents). "
                "Worth checking what's specific to the timetable, staffing, or subjects on that day."
                + (f" Lowest: {_dow_low_bap} — a useful comparison point for what's working."
                   if _dow_low_bap and _dow_low_bap != _dow_peak_bap else ""))

        # ── Chart 8: Escalation Rate by Behaviour ────────────────────────
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        _beh_esc = full_df["behaviour_type"].value_counts().head(6).index.tolist()
        _beh_esc = [b for b in _beh_esc if b and len(str(b)) <= 80
                    and not str(b).startswith("---")]
        if len(_beh_esc) >= 2:
            _esc_data = []
            for b in _beh_esc:
                _tot = len(full_df[full_df["behaviour_type"] == b])
                _crit = len(full_df[(full_df["behaviour_type"] == b) &
                                   (full_df["incident_type"] == "Critical")])
                _pct = (_crit / _tot * 100) if _tot >= 4 else -1
                _esc_data.append((get_clinical_behaviour(b), _tot, _crit, _pct))
            fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
            _esc_labels = [x[0][:40] + ("…" if len(x[0]) > 40 else "") for x in _esc_data]
            _esc_pcts   = [max(x[3], 0) for x in _esc_data]
            _esc_cols   = ["#ef4444" if x[3] > 50 else "#f97316" if x[3] > 25
                           else "#eab308" if x[3] >= 0 else "#94a3b8"
                           for x in _esc_data]
            bars = ax.barh(range(len(_esc_labels)), _esc_pcts,
                           color=_esc_cols, edgecolor="white", height=0.55)
            ax.set_yticks(range(len(_esc_labels)))
            ax.set_yticklabels(_esc_labels[::-1] if False else _esc_labels,
                               fontsize=8)
            ax.set_xlabel("Escalation rate (%)", fontsize=8.5, fontweight="bold", color="#334155")
            ax.axvline(50, color="#ef4444", linestyle="--", linewidth=1, alpha=0.5)
            for bar, d in zip(bars, _esc_data):
                if d[3] >= 0:
                    ax.text(d[3] + 1, bar.get_y() + bar.get_height()/2,
                            f"{d[3]:.0f}% (n={d[1]})", va="center", fontsize=8, color="#0f172a")
                else:
                    ax.text(1, bar.get_y() + bar.get_height()/2,
                            f"n={d[1]} — insufficient data", va="center", fontsize=8, color="#94a3b8")
            ax.set_title("8.  Escalation Rate by Behaviour  —  red dashed = 50% threshold",
                         fontsize=9.5, fontweight="bold", color="#0f172a", pad=6, loc="left")
            ax.set_xlim(0, max(105, max(_esc_pcts) + 15) if _esc_pcts else 110)
            base_ax_style(ax)
            plt.tight_layout(pad=0.4)
            _high_esc = [x for x in _esc_data if x[3] > 50]
            add_chart(doc, fig,
                "Escalation rate = the proportion of each behaviour's incidents that reached "
                "Critical Incident status rather than staying in the Coping zone. Grey bars = fewer than 4 "
                "incidents, not yet a reliable rate. "
                + (f"HIGH ESCALATION: {", ".join(x[0][:35] for x in _high_esc)} — proactive strategies "
                   "need to be in place before these behaviours emerge, not after."
                   if _high_esc else
                   "No behaviours currently show high escalation risk — a positive indicator."))

        # ── Chart 9: Severity distribution by Behaviour (WoT coloured) ──
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        _sv_behs = [b for b in full_df["behaviour_type"].value_counts().head(5).index
                    if b and len(str(b)) <= 80 and not str(b).startswith("---")]
        if _sv_behs and len(full_df) >= 4:
            _WOT_COLS_BAP = {1:"#eab308",2:"#eab308",3:"#f97316",4:"#ef4444",5:"#7f1d1d"}
            _WOT_LBLS_BAP = {1:"severity 1 Coping",2:"severity 2 Coping",3:"severity 3 Approaching edge",
                             4:"severity 4 Outside window",5:"severity 5 Crisis"}
            fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
            _bar_bottom = [0] * len(_sv_behs)
            _sv_labels_bap = [get_clinical_behaviour(b)[:40] + ("…" if len(get_clinical_behaviour(b)) > 40 else "")
                              for b in _sv_behs]
            for sv in [1,2,3,4,5]:
                _sv_vals = [int((full_df[full_df["behaviour_type"]==b]["severity"]==sv).sum())
                            for b in _sv_behs]
                if any(v > 0 for v in _sv_vals):
                    bars = ax.barh(range(len(_sv_behs)), _sv_vals,
                                   left=_bar_bottom, color=_WOT_COLS_BAP[sv],
                                   edgecolor="white", linewidth=0.6, height=0.55,
                                   label=_WOT_LBLS_BAP[sv])
                    for bar, v in zip(bars, _sv_vals):
                        if v > 0:
                            ax.text(bar.get_x() + bar.get_width()/2,
                                    bar.get_y() + bar.get_height()/2,
                                    str(v), ha="center", va="center",
                                    fontsize=8, color="white", fontweight="bold")
                    _bar_bottom = [b + v for b, v in zip(_bar_bottom, _sv_vals)]
            ax.set_yticks(range(len(_sv_labels_bap)))
            ax.set_yticklabels(_sv_labels_bap, fontsize=8)
            ax.set_xlabel("Number of incidents", fontsize=8.5, fontweight="bold", color="#334155")
            ax.set_title("9.  Severity Distribution by Behaviour  —  Window of Tolerance zones",
                         fontsize=9.5, fontweight="bold", color="#0f172a", pad=6, loc="left")
            ax.axvline(0, color="#cbd5e1", linewidth=1)
            ax.legend(fontsize=7, loc="lower right")
            base_ax_style(ax)
            plt.tight_layout(pad=0.4)
            _coping_n = int((full_df["severity"] <= 3).sum())
            _outside_n = int((full_df["severity"] > 3).sum())
            _c_pct = int(_coping_n / len(full_df) * 100) if len(full_df) else 0
            add_chart(doc, fig,
                f"{_c_pct}% of all incidents ({_coping_n} of {len(full_df)}) stayed within the Coping zone "
                f"(severity 1–3); {100-_c_pct}% ({_outside_n}) reached the outside-window zone (severity 4–5)."
                + (" Every outside-window episode needs relational repair before re-engaging with learning."
                   if _outside_n > 0 else " A strong positive indicator — document and sustain current strategies."))

        # ── Chart 10: Antecedent Category Breakdown (also shown in-app) ──
        full_df["_ant_cat"] = full_df["antecedent"].apply(categorize_antecedent)
        _cat_counts = full_df["_ant_cat"].dropna().value_counts()
        if not _cat_counts.empty:
            _cat_order  = ["Peer", "Transition", "Instructions", "Engagement", "Sensory", "Other"]
            _cat_colors = {"Peer": "#3b82f6", "Transition": "#f59e0b", "Instructions": "#ef4444",
                           "Engagement": "#8b5cf6", "Sensory": "#10b981", "Other": "#64748b"}
            _cat_present = [c for c in _cat_order if c in _cat_counts.index]
            _cat_vals = [int(_cat_counts[c]) for c in _cat_present]
            fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
            bars = ax.bar(_cat_present, _cat_vals,
                          color=[_cat_colors[c] for c in _cat_present],
                          edgecolor='white', linewidth=0.6, width=0.6)
            ax.set_ylabel("Number of incidents", fontsize=10, fontweight='bold', color='#334155')
            ax.set_title("10.  Antecedent Category Breakdown",
                         fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
            ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            for bar, v in zip(bars, _cat_vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        str(v), ha='center', va='bottom', fontsize=9, fontweight='bold', color='#0f172a')
            base_ax_style(ax)
            plt.tight_layout(pad=0.4)
            _top_cat = _cat_present[_cat_vals.index(max(_cat_vals))]
            _top_cat_pct = int(max(_cat_vals) / sum(_cat_vals) * 100) if sum(_cat_vals) else 0
            add_chart(doc, fig,
                f"Incidents grouped by trigger domain. '{_top_cat}' is the primary domain "
                f"({_top_cat_pct}% of categorised incidents) — this is where preventive "
                f"effort is likely to have the most impact.")

        _combos = find_combined_patterns(full_df)
        if _combos:
            cb = doc.add_table(rows=1, cols=1); cb.style = 'Table Grid'
            cb_c = cb.rows[0].cells[0]
            set_bg(cb_c, "EFF6FF"); set_borders(cb_c, "0284C7")
            cb_c.paragraphs[0].clear()
            p_cb = cb_c.paragraphs[0]
            p_cb.paragraph_format.space_before = Pt(3)
            arun(p_cb, "COMBINED PATTERN", bold=True, size=15, color="0284C7")
            for _c in _combos:
                p = cb_c.add_paragraph()
                p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
                arun(p, f"{int(_c['pct']*100)}% of all incidents ", bold=True, size=14)
                arun(p, f"({_c['count']} of {len(full_df)}) share all three conditions: "
                        f"{_c['category']}-triggered, in {normalise_location(_c['location'])}, "
                        f"during the {_c['session']} session.", size=14)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        section_header(doc, "FUNCTIONAL HYPOTHESIS")
        p_sp3 = doc.add_paragraph(); p_sp3.paragraph_format.space_after = Pt(4)

        interp_tbl = doc.add_table(rows=1, cols=1); interp_tbl.style='Table Grid'
        interp_c = interp_tbl.rows[0].cells[0]
        set_bg(interp_c, TEAL_LIGHT); set_borders(interp_c, TEAL_HEX)
        interp_c.paragraphs[0].clear()
        total = len(full_df)
        m_pct = int(len(full_df[full_df['session']=='Morning'])  / total * 100) if total else 0
        d_pct = int(len(full_df[full_df['session']=='Middle'])   / total * 100) if total else 0
        a_pct = int(len(full_df[full_df['session']=='Afternoon'])/ total * 100) if total else 0
        for line in [
            f"Based on {total} recorded incidents, {student['name']} experiences the most difficulty "
            f"when '{wrap_labels([top_ant], 70)[0]}' occurs. This happens most frequently in {top_loc}, "
            f"particularly during the {top_session} session "
            f"(Morning {m_pct}% / Middle of day {d_pct}% / Afternoon {a_pct}%).",
            f"The behaviour '{top_beh}' is the primary concern. From a trauma-informed perspective, "
            f"this is {student['name']}'s way of communicating an unmet need or responding to feeling "
            f"unsafe or overwhelmed — a stress response, not deliberate defiance.",
            f"All recommendations below are informed by the functional hypothesis and prioritise the "
            "Berry Street Body and Relationship domains first.",
        ]:
            p = interp_c.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after  = Pt(3)
            arun(p, line, size=16)

        doc.add_paragraph().paragraph_format.space_after = Pt(5)

        section_header(doc, "EVIDENCE-BASED RECOMMENDATIONS")
        p_sp4 = doc.add_paragraph(); p_sp4.paragraph_format.space_after = Pt(4)

        rec_tbl = doc.add_table(rows=5, cols=2); rec_tbl.style='Table Grid'
        for row in rec_tbl.rows:
            row.cells[0].width = Cm(4.8)
            row.cells[1].width = Cm(12.6)

        rec_headers = [
            ("1. Body Domain\nRegulation",            TEAL_HEX),
            ("2. Relationship Domain\nConnection",     GREY_DARK),
            ("3. Stamina Domain\nPersistence",         AMBER_HEX),
            ("4. CPI Principles\nDe-escalation",       "C0392B"),
            ("5. SMART Goal",                          "2E7D32"),
        ]
        rec_content = [
            [f"Regulated start before {top_session} (breathing, movement break)",
             f"Visual schedule check-in before '{wrap_labels([top_ant],45)[0]}'",
             f"Environmental modification in {top_loc}",
             "Sensory regulation built into schedule",
             "Proactive breaks before dysregulation — widen the window"],
            ["CPI Supportive Stance — low, slow voice; body at an angle",
             "One key adult maintains consistent connection",
             "Acknowledge feelings: 'I can see that feels really hard'",
             "Offer choices to maintain sense of control",
             "Never correct publicly — maintain dignity always"],
            ["Teach help-seeking using a visual cue card",
             "Practice requesting breaks in low-stakes moments",
             "Emotional literacy: name the feeling, not just the behaviour",
             "Celebrate effort and regulation, not just outcomes",
             "Break tasks into small, achievable steps"],
            [f"Intervene at first signs — before '{wrap_labels([top_beh],40)[0]}' occurs",
             "Co-regulation: your calm becomes their calm",
             "Remove audience; offer a face-saving exit",
             "Reduce demands when dysregulated — this is not rewarding behaviour",
             "Post-incident: repair relationship before re-engaging with learning"],
            [f"Over 5 weeks, {student['name']} will use a help-seeking strategy in 4/5 observed opportunities.",
             f"Review date: {(datetime.now() + timedelta(weeks=5)).strftime('%d %B %Y')}",
             "Measure: staff tally sheet, incident frequency trend",
             "Success indicator: reduction in severity and frequency of peak-session incidents"],
        ]
        for row_idx, ((hdr_text, hdr_colour), content_lines) in enumerate(zip(rec_headers, rec_content)):
            row = rec_tbl.rows[row_idx]
            hdr_cell = row.cells[0]
            set_bg(hdr_cell, hdr_colour); set_borders(hdr_cell, TEAL_HEX)
            hdr_cell.paragraphs[0].clear()
            p = hdr_cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after  = Pt(4)
            arun(p, hdr_text, bold=True, size=15, color=WHITE)
            content_cell = row.cells[1]
            set_bg(content_cell, LIGHT_GREY if row_idx % 2 == 0 else WHITE)
            set_borders(content_cell, TEAL_HEX)
            content_cell.paragraphs[0].clear()
            for line in content_lines:
                p = content_cell.add_paragraph()
                p.paragraph_format.space_before = Pt(1.5)
                p.paragraph_format.space_after  = Pt(1.5)
                arun(p, f"• {line}", size=15)

        doc.add_paragraph().paragraph_format.space_after = Pt(5)

        section_header(doc, "THEORETICAL FRAMEWORKS APPLIED")
        p_sp5 = doc.add_paragraph(); p_sp5.paragraph_format.space_after = Pt(4)

        fw_tbl = doc.add_table(rows=1, cols=4); fw_tbl.style='Table Grid'
        for ci, (fw_name, fw_desc) in enumerate([
            ("Applied Behaviour Analysis",
             "Triggers, behaviour and consequences — understand function, reduce harmful patterns."),
            ("Trauma-Informed Practice",
             "Behaviour is communication. Safety and relationships must come before learning."),
            ("Berry Street Education Model",
             "Body → Relationship → Stamina → Engagement → Character. Sequential domains."),
            ("Crisis Prevention Institute",
             "De-escalation, supportive stance, dignity, early intervention, co-regulation."),
        ]):
            c = fw_tbl.rows[0].cells[ci]
            set_bg(c, TEAL_LIGHT if ci % 2 == 0 else AMBER_LIGHT)
            set_borders(c, TEAL_HEX)
            c.paragraphs[0].clear()
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after  = Pt(2)
            arun(p, fw_name + "\n", bold=True, size=14, color=GREY_DARK)
            arun(p, fw_desc, size=13, color="444444")

        doc.add_paragraph().paragraph_format.space_after = Pt(5)

        section_header(doc, "TEACHING LENS — RECOMMENDATIONS")
        p_tl = doc.add_paragraph(); p_tl.paragraph_format.space_after = Pt(4)
        arun(p_tl, "Framed on SMART's core principle: a dysregulated (Regulate-stage) brain can't yet learn or "
                   "reason — these strategies work by keeping the student regulated before demand increases, "
                   "not after.", italic=True, size=13, color=GREY_DARK)

        tl_tbl = doc.add_table(rows=2, cols=2); tl_tbl.style = 'Table Grid'
        tl_data = [
            ("📚 Curriculum & Pedagogy", [
                f"Deliver clear, single-step instructions with visual supports — avoid multi-part directives during the {top_session} session.",
                f"Scaffold tasks into small, achievable components with explicit success criteria before engaging in '{wrap_labels([top_ant],50)[0]}'-type activities.",
                "Embed student choice within the curriculum (topic, modality, sequence) to maintain agency and reduce escape-motivated behaviour.",
                "Apply strength-based entry points — begin all tasks at a mastery level before incrementally increasing demand.",
                "Use pre-teaching and content priming before transitions or cognitively demanding tasks.",
                "Implement flexible, low-stakes assessment to reduce evaluation-related anxiety as a trigger.",
            ]),
            ("🗂️ Structure & Routines", [
                f"Display a visual daily schedule and review it collaboratively at the start of the {top_session} session.",
                "Provide 2-minute transition warnings using both verbal and visual cues before all activity changes.",
                f"Strategic seating in {top_loc} — close to support adult, away from high-traffic and peer-conflict areas.",
                "Explicitly teach and practise a Help Card or Break Card system during calm, low-demand times.",
                "Use errorless learning techniques — engineer early task success before fading prompts.",
                "Deliver all corrections privately to preserve dignity and avoid public escalation.",
            ]),
            ("📈 SMART Teaching Goal", [
                f"Over 5 school weeks, {student['name']} will independently use a help-seeking strategy in 4/5 observed opportunities during the {top_session} session.",
                "Measurement: daily staff tally sheet. Baseline data collected in Week 1 before intervention commences in Week 2.",
                f"Mid-point review at Week 3; end-point review at Week 5 against baseline frequency of {get_clinical_behaviour(top_beh).lower()}.",
            ]),
            ("🎯 Implementation Notes", [
                "All strategies should be implemented consistently by all staff across all settings.",
                "Data collection must be maintained to evaluate effectiveness and adjust strategies as needed.",
                "Strategies are grounded in Applied Behaviour Analysis (ABA) and Berry Street Education Model frameworks.",
                "Review Teaching Goal progress at the next scheduled case review meeting.",
            ]),
        ]
        for row_idx, (hdr_text, items) in enumerate(tl_data):
            row = tl_tbl.rows[row_idx // 2].cells[row_idx % 2] if row_idx < 4 else None
            if row_idx < 4:
                set_bg(row, TEAL_LIGHT if row_idx % 2 == 0 else AMBER_LIGHT)
                set_borders(row, TEAL_HEX)
                row.paragraphs[0].clear()
                p = row.paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                arun(p, hdr_text + "\n", bold=True, size=15, color=GREY_DARK)
                for item in items:
                    pi = row.add_paragraph()
                    pi.paragraph_format.space_before = Pt(1)
                    pi.paragraph_format.space_after  = Pt(1)
                    arun(pi, f"• {item}", size=13)

        doc.add_paragraph().paragraph_format.space_after = Pt(5)

        section_header(doc, "SUPPORT LENS — RECOMMENDATIONS")
        p_sl = doc.add_paragraph(); p_sl.paragraph_format.space_after = Pt(4)
        arun(p_sl, "Sequenced on SMART's Regulate → Relate → Reason principle — co-regulation and safety come "
                   "first; debrief, repair, and skill-teaching only once the student is genuinely calm.",
             italic=True, size=13, color=GREY_DARK)

        sl_tbl = doc.add_table(rows=2, cols=2); sl_tbl.style = 'Table Grid'
        sl_data = [
            ("🧠 Regulation & Sensory", [
                f"Incorporate a sensory diet before the {top_session} session — movement break, heavy work, or proprioceptive input to prepare the nervous system.",
                "Co-regulate with a key adult using CPI Supportive Stance (low, slow, sideways) as the default interaction posture.",
                f"Develop a personalised Window of Tolerance profile for {student['name']} — document early warning signs, escalation cues, and effective de-escalation strategies.",
                "Teach and embed regulation tools during calm states; cue their use proactively at early warning signs, before escalation occurs.",
                "Monitor medication timing and note correlations with incident frequency in the peak session.",
            ]),
            ("🛡️ Antecedent Prevention", [
                f"Conduct an environmental audit of {top_loc} — review and modify sensory load, spatial arrangement, and proximity to triggers.",
                "Implement pre-correction immediately before high-risk contexts — calm reminder of expectations and available supports.",
                f"Conduct Functional Communication Training (FCT) — teach a socially appropriate replacement behaviour serving the same function as {get_clinical_behaviour(top_beh).lower()}.",
                "Apply structured peer interaction protocols — pre-assign groupings and roles; avoid unstructured proximity where peer triggers are present.",
                "Develop a Crisis Safety Plan with Critical Incident protocols, staff roles, and a post-incident restorative repair sequence.",
            ]),
            ("🔄 Post-Incident Repair", [
                "Restore the relationship before re-engaging with academic demands — never return to tasks while the student remains dysregulated.",
                "Conduct a brief, non-punitive restorative conversation once regulated — focus on impact and repair.",
                "Complete a structured staff debrief after every Critical Incident.",
                "Maintain proactive, strengths-focused communication with parent/carer — not solely incident-driven contact.",
            ]),
            ("📅 Case Management", [
                f"Schedule a formal case review within {'2 weeks' if risk_score >= 60 else '4 weeks' if risk_score >= 30 else '6 weeks'} — review BAP, update strategies, and set new SMART goals.",
                "Consult with allied health professionals (OT, Speech, Psych) if sensory, communication, or mental health factors are contributing.",
                f"Ensure all staff working with {student['name']} are briefed on the current BAP and implementing strategies consistently.",
                "Formally update the Behaviour Support Plan each term, or after any critical incident.",
            ]),
        ]
        for row_idx, (hdr_text, items) in enumerate(sl_data):
            if row_idx < 4:
                row = sl_tbl.rows[row_idx // 2].cells[row_idx % 2]
                set_bg(row, LIGHT_GREY if row_idx % 2 == 0 else WHITE)
                set_borders(row, TEAL_HEX)
                row.paragraphs[0].clear()
                p = row.paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                arun(p, hdr_text + "\n", bold=True, size=15, color=GREY_DARK)
                for item in items:
                    pi = row.add_paragraph()
                    pi.paragraph_format.space_before = Pt(1)
                    pi.paragraph_format.space_after  = Pt(1)
                    arun(pi, f"• {item}", size=13)

        doc.add_paragraph().paragraph_format.space_after = Pt(5)

        if full_pack:
            from docx.enum.section import WD_SECTION, WD_ORIENT

            def _clean(v, default="—"):
                if isinstance(v, (list, tuple)):
                    v = ", ".join(str(x) for x in v if x)
                if v is None:
                    return default
                try:
                    if pd.isna(v):
                        return default
                except (TypeError, ValueError):
                    pass
                v = str(v).strip()
                return v if v and v.lower() not in ("nan", "none", "nat") else default

            def _set_col_widths(tbl, widths_cm):
                tbl.autofit = False
                for idx, w in enumerate(widths_cm):
                    if idx < len(tbl.columns):
                        tbl.columns[idx].width = Cm(w)
                for row in tbl.rows:
                    for idx, w in enumerate(widths_cm):
                        if idx < len(row.cells):
                            row.cells[idx].width = Cm(w)

            def _repeat_header(row):
                trPr = row._tr.get_or_add_trPr()
                el = OxmlElement('w:tblHeader'); el.set(qn('w:val'), 'true'); trPr.append(el)

            def grid_table(headers, rows, widths_cm, font=17):
                tbl = doc.add_table(rows=1, cols=len(headers)); tbl.style = 'Table Grid'
                for i, h in enumerate(headers):
                    c = tbl.rows[0].cells[i]
                    set_bg(c, GREY_DARK); set_borders(c, TEAL_HEX)
                    c.paragraphs[0].clear()
                    arun(c.paragraphs[0], h, bold=True, size=font, color=WHITE)
                _repeat_header(tbl.rows[0])
                for r_i, r in enumerate(rows):
                    cells = tbl.add_row().cells
                    for i, val in enumerate(r):
                        set_bg(cells[i], LIGHT_GREY if r_i % 2 == 0 else WHITE)
                        set_borders(cells[i], "CBD5E1")
                        cells[i].paragraphs[0].clear()
                        arun(cells[i].paragraphs[0], str(val), size=font)
                _set_col_widths(tbl, widths_cm)
                return tbl

            def note(text, size=17):
                pn = doc.add_paragraph(); pn.paragraph_format.space_after = Pt(4)
                arun(pn, text, italic=True, size=size, color=GREY_DARK)

            # ── page numbers + confidentiality footer ──
            _fp = doc.sections[0].footer.paragraphs[0]
            _fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(_fp, f"CONFIDENTIAL — {student['name']} — Full Analysis, printed "
                      f"{datetime.now().strftime('%d/%m/%Y')} — Page ", size=18, color="666666")
            _r = _fp.add_run(); _r.font.size = Pt(7); _r.font.name = "Arial"
            for _t, _txt in (("begin", None), (None, "PAGE"), ("end", None)):
                if _t:
                    _e = OxmlElement('w:fldChar'); _e.set(qn('w:fldCharType'), _t)
                else:
                    _e = OxmlElement('w:instrText'); _e.set(qn('xml:space'), 'preserve'); _e.text = _txt
                _r._r.append(_e)

            # ── Strategy trials ──
            if trials:
                doc.add_page_break()
                section_header(doc, "STRATEGY TRIALS — WHAT WE HAVE TRIED AND LEARNED")
                note("Each trial tests a hypothesis about this student. Effects are a preliminary read from logged incidents.")
                for _t in trials:
                    _st_, _en_ = _trial_date(_t.get("start_date")), _trial_date(_t.get("end_date"))
                    _eff = compute_trial_effect(full_df, _st_, _en_ if _t.get("status") != "Running" else None, _t.get("focus_session") or "")
                    _tt = doc.add_table(rows=1, cols=1); _tt.style = 'Table Grid'
                    _tc = _tt.rows[0].cells[0]; set_borders(_tc, TEAL_HEX, size="10"); _tc.paragraphs[0].clear()
                    arun(_tc.paragraphs[0], _tr_text(_t.get("title")), bold=True, size=19, color=GREY_DARK)
                    _status = "Running" if _t.get("status") == "Running" else f"Concluded: {_t.get('outcome') or ''}"
                    arun(_tc.paragraphs[0], f"   [{_status}]  from {_st_.strftime('%d/%m/%Y') if _st_ else '—'}", size=15, color=TEAL_HEX)
                    for _lab, _val in (("Hypothesis: ", _t.get("hypothesis")), ("Strategy: ", _t.get("strategy")), ("Tracking: ", _t.get("measure"))):
                        _pp = _tc.add_paragraph(); _pp.paragraph_format.space_before = Pt(2)
                        arun(_pp, _lab, bold=True, size=16, color=GREY_DARK); arun(_pp, _tr_text(_val, "—"), size=16)
                    if _eff and not _eff.get("insufficient"):
                        for _ln in (_fmt_effect(_eff.get("focus"), f"{_t.get('focus_session')} session"), _fmt_effect(_eff.get("all"), "Whole day")):
                            if _ln:
                                _pp = _tc.add_paragraph(); arun(_pp, _ln, size=16, color="1A7A6E")
                    _al = trial_attendance_line(student.get("id"), _st_, _en_ if _t.get("status") != "Running" else None, full_df)
                    if _al:
                        _pp = _tc.add_paragraph(); arun(_pp, _al, size=16, color="1A7A6E")
                    for _o in (_t.get("observations") or []):
                        _pp = _tc.add_paragraph(); arun(_pp, f"• {_o.get('date','')} — {_o.get('text','')}", size=15)
                    if _t.get("conclusion"):
                        _pp = _tc.add_paragraph(); _pp.paragraph_format.space_before = Pt(2)
                        arun(_pp, "What we learned: ", bold=True, size=16, color=GREY_DARK); arun(_pp, _tr_text(_t.get("conclusion")), size=16)
                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

            # ── Antecedent categories ──
            doc.add_page_break()
            section_header(doc, "WHAT TENDS TO COME BEFORE THE BEHAVIOUR — BY CATEGORY")
            note("Each incident's trigger grouped into a category. Count, share of all incidents, and average severity.")
            _cdf = full_df.copy()
            if "antecedent" in _cdf.columns:
                _cdf["_cat"] = _cdf["antecedent"].apply(categorize_antecedent)
                _cdf["_sev"] = pd.to_numeric(_cdf.get("severity"), errors="coerce")
                _rows = []
                for cat, g in _cdf.groupby("_cat"):
                    _sv = g["_sev"].mean()
                    _rows.append([cat, len(g), f"{len(g)/len(_cdf)*100:.0f}%",
                                  f"{_sv:.1f}" if pd.notna(_sv) else "—"])
                _rows.sort(key=lambda r: -r[1])
                if _rows:
                    grid_table(["Category", "Incidents", "Share", "Avg severity"], _rows, [7.4, 3.2, 3.2, 3.6], font=18)
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # ── Where / when crosstab ──
            if {"location", "session"}.issubset(full_df.columns):
                section_header(doc, "WHERE AND WHEN — LOCATION × SESSION")
                note("Number of incidents in each location, by session (Morning before 11:00; Middle 11:00–13:30; Afternoon after 13:30).")
                _ct = pd.crosstab(full_df["location"].fillna("Unknown"), full_df["session"])
                for _s in ("Morning", "Middle", "Afternoon"):
                    if _s not in _ct.columns:
                        _ct[_s] = 0
                _ct = _ct[["Morning", "Middle", "Afternoon"]]
                _ct["Total"] = _ct.sum(axis=1)
                _ct = _ct.sort_values("Total", ascending=False)
                grid_table(["Location", "Morning", "Middle", "Afternoon", "Total"],
                           [[idx, *[int(v) for v in row]] for idx, row in _ct.iterrows()],
                           [6.0, 2.8, 2.8, 2.9, 2.9], font=18)
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # ── Combined patterns ──
            _combos = find_combined_patterns(full_df)
            if _combos:
                section_header(doc, "COMBINED PATTERNS")
                note("Where trigger, place and time of day overlap — a stronger signal than any one on its own.")
                grid_table(["Trigger category", "Location", "Session", "Incidents", "Share"],
                           [[c["category"], c["location"], c["session"], c["count"], f"{c['pct']*100:.0f}%"] for c in _combos],
                           [4.4, 4.4, 3.2, 2.7, 2.7], font=18)
                doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # ── Considerations ──
            _cons = build_considerations(full_df, top_ant, top_loc, top_session)
            if _cons:
                section_header(doc, "THINGS TO CONSIDER BEFORE ACTING ON THIS DATA")
                note("Other explanations worth ruling out before treating a pattern as purely behavioural.")
                for _c in _cons:
                    _pc = doc.add_paragraph(); _pc.paragraph_format.space_after = Pt(3)
                    _pc.paragraph_format.left_indent = Cm(0.4)
                    arun(_pc, "☐  ", size=20, color=TEAL_HEX); arun(_pc, _c, size=18)
                doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # ── Demand-avoidant presentations ──
            doc.add_page_break()
            section_header(doc, "DEMAND-AVOIDANT PRESENTATIONS — PERCEIVED CHOICE APPROACH")
            _sig = demand_avoidance_signal(full_df)
            note((f"{_sig['n']} of {_sig['total']} incidents ({_sig['pct']*100:.0f}%) were linked to demands, instructions, "
                  "transitions or refusal/avoidance. " if _sig["flag"] else "")
                 + "Useful whether or not a diagnosis (e.g. ODD or PDA profile) exists. This is a prompt for team discussion, not a label.")
            for _d in DEMAND_AVOIDANCE_STRATEGIES:
                _pd = doc.add_paragraph(); _pd.paragraph_format.space_after = Pt(3)
                _pd.paragraph_format.left_indent = Cm(0.4)
                arun(_pd, f"[{_d['domain']}]  ", bold=True, size=17, color=TEAL_HEX); arun(_pd, _d["strategy"], size=17)
            doc.add_paragraph().paragraph_format.space_after = Pt(3)
            note("Perceived choice: reframing the language. Both options must be acceptable; the choice is in how, when, where or with whom, not whether.")
            grid_table(["Instead of...", "Try..."], [[a, b] for a, b in PERCEIVED_CHOICE_PHRASES], [6.0, 11.4], font=17)

            # ── Window of Tolerance ──
            doc.add_page_break()
            section_header(doc, "WINDOW OF TOLERANCE — DRAFT FROM THIS STUDENT'S DATA")
            note("Draft only, built from logged behaviour types and severity. Context is de-identified (people shown by role). "
                 "Review with the team and complete the regulated 'Window of Tolerance' zone directly in the Creator.")
            _wot = build_window_of_tolerance_table(full_df, student_id=student.get("id"))
            if not _wot:
                note("Not enough classifiable incidents yet to draft this table.")
            for _z in WOT_ZONES:
                if _z["id"] not in _wot:
                    continue
                _zd = _wot[_z["id"]]
                _zt = doc.add_table(rows=2, cols=3); _zt.style = 'Table Grid'
                _hc = _zt.rows[0].cells[0].merge(_zt.rows[0].cells[2])
                set_bg(_hc, _z["color"].lstrip("#")); set_borders(_hc, _z["color"].lstrip("#"))
                _hc.paragraphs[0].clear()
                arun(_hc.paragraphs[0], f"{_z['label']}  —  {_zd['n']} incident(s)", bold=True, size=20, color=WHITE)
                for _ci, (_h, _items) in enumerate((("Context", _zd["context"]), ("Behaviour", _zd["behaviour"]),
                                                    ("Interventions", _zd["interventions"] or ["— none logged for this zone —"]))):
                    _cell = _zt.rows[1].cells[_ci]
                    set_borders(_cell, _z["color"].lstrip("#"))
                    _cell.paragraphs[0].clear()
                    arun(_cell.paragraphs[0], _h, bold=True, size=17, color=GREY_DARK)
                    for _it in _items:
                        _pi = _cell.add_paragraph(); _pi.paragraph_format.space_after = Pt(1)
                        arun(_pi, f"• {_clean(_it)}", size=17)
                _set_col_widths(_zt, [5.8, 5.8, 5.8])
                doc.add_paragraph().paragraph_format.space_after = Pt(4)

            # ── BSEM recommendations (fully expanded for print) ──
            if bsem_items:
                doc.add_page_break()
                section_header(doc, "BERRY STREET EDUCATION MODEL — RECOMMENDED STRATEGIES")
                note("Strategies matched to this student's pattern, framed for handover to a receiving school. "
                     "SMART reminder: regulate before you reason.")
                _dom_col = {"Body": "10B981", "Relationship": "3B82F6", "Stamina": "F97316",
                            "Engagement": "8B5CF6", "Character": "EAB308"}
                for _it in bsem_items:
                    _bt = doc.add_table(rows=1, cols=1); _bt.style = 'Table Grid'
                    _bc = _bt.rows[0].cells[0]
                    _col = _dom_col.get(_it.get("domain"), "64748B")
                    set_borders(_bc, _col, size="12"); _bc.paragraphs[0].clear()
                    arun(_bc.paragraphs[0], f"{str(_it.get('domain','')).upper()}   ", bold=True, size=17, color=_col)
                    arun(_bc.paragraphs[0], _clean(_it.get("strategy")), bold=True, size=20, color=GREY_DARK)
                    for _lab, _key in (("Why it fits: ", "why"), ("How to put it in place: ", "how")):
                        _txt = _clean(_it.get(_key), default="")
                        if _txt and not _txt.startswith("[DEBUG]"):
                            _pw = _bc.add_paragraph(); _pw.paragraph_format.space_before = Pt(2)
                            arun(_pw, _lab, bold=True, size=17, color=GREY_DARK); arun(_pw, _txt, size=17)
                    doc.add_paragraph().paragraph_format.space_after = Pt(3)

            # ── Incident register (landscape) ──
            _land = doc.add_section(WD_SECTION.NEW_PAGE)
            _land.orientation = WD_ORIENT.LANDSCAPE
            _land.page_width, _land.page_height = Cm(29.7), Cm(21)
            for _a in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
                setattr(_land, _a, Cm(1.5))
            section_header(doc, f"INCIDENT REGISTER — ALL {len(full_df)} DATED INCIDENTS")
            note("Every incident on file, oldest first. Q = Quick log, C = Critical (ABCH).")
            _reg_rows = []
            for _, r in full_df.sort_values("date_parsed").iterrows():
                _desc = _clean(r.get("description"), default="")
                if not _desc and isinstance(r.get("ABCH_primary"), dict):
                    _desc = _clean(r["ABCH_primary"].get("behaviour"), default="")
                if len(_desc) > 150:
                    _desc = _desc[:147].rstrip() + "…"
                _sev = pd.to_numeric(r.get("severity"), errors="coerce")
                _reg_rows.append([
                    r["date_parsed"].strftime("%d/%m/%y"),
                    _clean(r.get("time"), default="")[:5],
                    "C" if r.get("incident_type") == "Critical" else "Q",
                    _clean(r.get("location")),
                    _clean(r.get("behaviour_type")),
                    _clean(r.get("antecedent")),
                    "—" if pd.isna(_sev) else int(_sev),
                    _clean(r.get("intervention")),
                    _desc or "—",
                ])
            grid_table(["Date", "Time", "Type", "Location", "Behaviour", "Antecedent (trigger)", "Sev", "Interventions", "Notes"],
                       _reg_rows, [1.8, 1.3, 1.4, 2.6, 4.1, 4.1, 1.1, 4.2, 6.0], font=16)

            # ── Meeting notes & actions (portrait, blank for handwriting) ──
            _port = doc.add_section(WD_SECTION.NEW_PAGE)
            _port.orientation = WD_ORIENT.PORTRAIT
            _port.page_width, _port.page_height = Cm(21), Cm(29.7)
            for _a in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
                setattr(_port, _a, Cm(1.8))
            section_header(doc, "MEETING NOTES & AGREED ACTIONS")
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            _hdr = doc.add_table(rows=1, cols=2); _hdr.style = 'Table Grid'
            for _i, _t in enumerate(("Date of meeting:", "Present:")):
                set_borders(_hdr.rows[0].cells[_i], TEAL_HEX); _hdr.rows[0].cells[_i].paragraphs[0].clear()
                arun(_hdr.rows[0].cells[_i].paragraphs[0], _t, bold=True, size=20, color=GREY_DARK)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            _nt = doc.add_table(rows=2, cols=1); _nt.style = 'Table Grid'
            set_borders(_nt.rows[0].cells[0], TEAL_HEX); _nt.rows[0].cells[0].paragraphs[0].clear()
            arun(_nt.rows[0].cells[0].paragraphs[0], "Notes", bold=True, size=20, color=GREY_DARK)
            set_borders(_nt.rows[1].cells[0], TEAL_HEX)
            _nt.rows[1].height = Cm(9.5)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            _act = grid_table(["Agreed action", "Who", "By when"], [["", "", ""] for _ in range(6)], [10.0, 3.8, 3.6], font=18)
            for _row in _act.rows[1:]:
                _row.height = Cm(1.5)

        # Sign-off section removed — BAP approved via portal workflow

        # Prevent any table row (Student Details, Key Findings, Risk banner,
        # recommendation tables, etc.) from splitting across a page break
        for _tbl in doc.tables:
            for _row in _tbl.rows:
                _trPr = _row._tr.get_or_add_trPr()
                _cant_split = OxmlElement('w:cantSplit')
                _trPr.append(_cant_split)

        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream

    except Exception as e:
        import traceback
        st.error(f"BAP Error: {e}")
        st.error(traceback.format_exc())
        return None


# ============================================
# SUPABASE DATABASE FUNCTIONS
# ============================================

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# ── Attendance / absence persistence ─────────────────────────────────────────
def load_attendance_from_db(student_id):
    """Load saved attendance record for a student from Supabase."""
    if not supabase or not student_id:
        return {}
    try:
        res = _db_retry(lambda: supabase.table("student_attendance")
                        .select("*").eq("student_id", student_id).limit(1).execute())
        if res.data:
            row = res.data[0]
            return {
                "absent_dates": row.get("absent_dates") or [],
                "pt_days":      row.get("pt_days") or ["Monday","Tuesday","Wednesday","Thursday","Friday"],
                "pt_sessions":  row.get("pt_sessions") or ["Full day"],
                "pt_notes":     row.get("pt_notes") or "",
                "schedule":     row.get("schedule") or [],
                "exceptions":   row.get("exceptions") or [],
            }
    except Exception:
        pass
    return {}


ATTENDANCE_SQL = """alter table student_attendance add column if not exists schedule jsonb default '[]'::jsonb;
alter table student_attendance add column if not exists exceptions jsonb default '[]'::jsonb;"""


def save_attendance_to_db(student_id, absent_dates, pt_days, pt_sessions, pt_notes, schedule=None, exceptions=None):
    """Upsert attendance record for a student in Supabase. If the newer schedule /
    exceptions columns don't exist yet, the older fields are still saved and a flag is set
    so the page can show the one-line SQL needed."""
    if not supabase or not student_id:
        return False
    base = {
        "student_id":   student_id,
        "absent_dates": absent_dates or [],
        "pt_days":      pt_days or [],
        "pt_sessions":  pt_sessions or [],
        "pt_notes":     pt_notes or "",
    }
    full = dict(base)
    if schedule is not None: full["schedule"] = schedule
    if exceptions is not None: full["exceptions"] = exceptions

    def _write(data):
        res = _db_retry(lambda: supabase.table("student_attendance").update(data).eq("student_id", student_id).execute())
        if not res.data:
            _db_retry(lambda: supabase.table("student_attendance").insert(data).execute())

    try:
        _write(full)
        st.session_state.pop("_att_new_cols_missing", None)
        return True
    except Exception as e:
        st.session_state["_last_save_error"] = str(e)
        if len(full) > len(base):
            try:
                _write(base)
                st.session_state["_att_new_cols_missing"] = True
                return True
            except Exception as e2:
                st.session_state["_last_save_error"] = str(e2)
        return False


# ── Attendance model: weekly schedule (versioned) + dated exceptions ─────────
# Staff set the usual weekly pattern once and only touch it when the pattern changes
# ("applies from" a given Monday). Day-to-day variation is recorded as an exception
# only when it happens, so no one needs to enter attendance daily.
ATT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
ATT_DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
ATT_SESSIONS = ["Morning", "Middle", "Afternoon"]
ATT_SESSION_LABEL = {"Morning": "AM", "Middle": "Mid", "Afternoon": "PM"}
ATT_TYPES = ["Absent", "Finished early", "Arrived late", "Different sessions", "Extra day", "No school"]
ATT_TYPE_HELP = {
    "Absent": "Did not attend at all",
    "Finished early": "Went home before the end of the day (e.g. a day end to avoid potential escalation, to reset, or negotiated with the student)",
    "Arrived late": "Missed the start of the day",
    "Different sessions": "Attended a different mix of sessions to usual",
    "Extra day": "Attended on a day they don't usually",
    "No school": "Holiday, closure or student-free day (not counted as expected attendance)",
}
ATT_ESCALATION_REASON = "Day end: avoid potential escalation"
ATT_RESET_REASON = "Day end: needs reset"
ATT_NEGOTIATED_REASON = "Day end: negotiated"
ATT_CI_REASON = "C.I. (critical incident)"
ATT_REASONS = [ATT_ESCALATION_REASON, ATT_RESET_REASON, ATT_NEGOTIATED_REASON, ATT_CI_REASON, "Illness", "Appointment",
               "Family / personal", "Other"]
ATT_DAYEND_REASONS = (ATT_ESCALATION_REASON, ATT_RESET_REASON, ATT_NEGOTIATED_REASON)
# Earlier wording, converted automatically when a record is loaded
ATT_LEGACY_REASONS = {"Day end to avoid escalation": ATT_ESCALATION_REASON,
                      "Day end: needs reset, negotiated time": ATT_RESET_REASON}


def _att_monday(d):
    return d - timedelta(days=d.weekday())


def _att_sess_text(sessions) -> str:
    sessions = [x for x in ATT_SESSIONS if x in (sessions or [])]
    if len(sessions) == len(ATT_SESSIONS): return "Full day"
    if not sessions: return "—"
    return " + ".join(sessions)


def attendance_state(student_id) -> dict:
    """The student's attendance model, cached per session. Legacy fields (regular days,
    sessions, absent dates) are converted the first time so nothing already entered is lost."""
    ck = f"att2_{student_id}"
    if ck in st.session_state:
        return st.session_state[ck]
    state = {"schedule": [], "exceptions": [], "notes": ""}
    leg = load_attendance_from_db(student_id)
    if leg:
        state["notes"] = leg.get("pt_notes", "") or ""
        state["schedule"] = list(leg.get("schedule") or [])
        state["exceptions"] = list(leg.get("exceptions") or [])
        if not state["schedule"]:
            pt_days = leg.get("pt_days") or ATT_DAYS_FULL
            sess_opts = leg.get("pt_sessions") or ["Full day"]
            sess = set()
            for o in sess_opts:
                if o == "Full day": sess |= set(ATT_SESSIONS)
                elif o == "Morning only": sess.add("Morning")
                elif o == "Middle of day only": sess.add("Middle")
                elif o == "Afternoon only": sess.add("Afternoon")
                elif o == "Morning + Middle": sess |= {"Morning", "Middle"}
                elif o == "Middle + Afternoon": sess |= {"Middle", "Afternoon"}
            sess = [x for x in ATT_SESSIONS if x in sess] or list(ATT_SESSIONS)
            days_map = {ATT_DAYS[i]: (sess if ATT_DAYS_FULL[i] in pt_days else []) for i in range(5)}
            if any(v != list(ATT_SESSIONS) for v in days_map.values()):
                state["schedule"] = [{"from": "2000-01-01", "days": days_map, "note": ""}]
        have = {e.get("date") for e in state["exceptions"]}
        for d in leg.get("absent_dates") or []:
            if d not in have:
                state["exceptions"].append({"date": d, "type": "Absent", "sessions": [], "reason": "", "note": ""})
    for e in state["exceptions"]:
        if e.get("reason") in ATT_LEGACY_REASONS:
            e["reason"] = ATT_LEGACY_REASONS[e["reason"]]
    st.session_state[ck] = state
    return state


def attendance_persist(student_id, state) -> bool:
    """Save the model and refresh the older session keys other parts of the page still read."""
    state["schedule"] = sorted(state.get("schedule", []), key=lambda v: v["from"])
    state["exceptions"] = sorted(state.get("exceptions", []), key=lambda e: e["date"])
    st.session_state[f"att2_{student_id}"] = state
    absent = sorted({e["date"] for e in state["exceptions"] if e.get("type") == "Absent"})
    st.session_state[f"absent_dates_{student_id}"] = absent
    cur = attendance_current_days(state)
    days_on = [ATT_DAYS_FULL[i] for i, dname in enumerate(ATT_DAYS) if cur.get(dname)]
    full_week = all(set(cur.get(d, [])) == set(ATT_SESSIONS) for d in ATT_DAYS)
    return save_attendance_to_db(student_id, absent, days_on, ["Full day"] if full_week else ["See weekly schedule"],
                                 state.get("notes", ""), schedule=state["schedule"], exceptions=state["exceptions"])


def attendance_current_days(state, on=None) -> dict:
    """Sessions per weekday in force on a given date (default today)."""
    on = on or date.today()
    vers = sorted(state.get("schedule", []), key=lambda v: v["from"])
    if not vers:
        return {d: list(ATT_SESSIONS) for d in ATT_DAYS}
    chosen = vers[0]
    for v in vers:
        if v["from"] <= on.isoformat():
            chosen = v
    return {d: list(chosen["days"].get(d, [])) for d in ATT_DAYS}


def attendance_day(state, d) -> dict:
    """Planned vs actual sessions for one date, after any exception."""
    exc = next((e for e in state.get("exceptions", []) if e.get("date") == d.isoformat()), None)
    planned = attendance_current_days(state, d).get(ATT_DAYS[d.weekday()], []) if d.weekday() < 5 else []
    if exc and exc.get("type") == "No school":
        return {"planned": [], "actual": [], "exc": exc, "no_school": True}
    actual = planned
    if exc:
        actual = [] if exc.get("type") == "Absent" else [x for x in ATT_SESSIONS if x in (exc.get("sessions") or [])]
    return {"planned": planned, "actual": actual, "exc": exc, "no_school": False}


def attendance_summary(state, start, end) -> dict:
    exp = act = 0
    days_on = early = esc = absent = 0
    esc_dates, early_dates = [], []
    d = start
    while d <= end:
        day = attendance_day(state, d)
        if not day["no_school"]:
            exp += len(day["planned"]); act += len(day["actual"])
            if day["actual"]: days_on += 1
            exc = day["exc"]
            if exc:
                if exc["type"] == "Absent": absent += 1
                if exc["type"] == "Finished early":
                    early += 1; early_dates.append(d)
                    if exc.get("reason") in ATT_DAYEND_REASONS:
                        esc += 1; esc_dates.append(d)
        d += timedelta(days=1)
    return {"expected": exp, "attended": act, "lost": max(exp - act, 0), "days_attended": days_on,
            "absent_days": absent, "early_days": early, "escalation_day_ends": esc,
            "early_dates": early_dates, "esc_dates": esc_dates}


def render_attendance_tracking(student_id):
    """Weekly schedule + exceptions + week view. Edits save immediately."""
    state = attendance_state(student_id)
    if st.session_state.get("_att_new_cols_missing"):
        st.warning("⚠️ Saved, but the newer schedule details can't be stored permanently until two columns are added. "
                   "Copy this into the Supabase SQL Editor and run it once:")
        st.code(ATTENDANCE_SQL, language="sql")
    st.caption("Set the usual week once. Only change it when the pattern changes, and add an exception only on days that "
               "differ. Nothing needs entering on days that go to plan.")

    # ── week view ──
    wk = st.date_input("Week to view", value=date.today(), key=f"att_wk_{student_id}")
    mon = _att_monday(wk)
    rows = {"Planned": [], "Actual": [], "Note": []}
    heads = []
    for i in range(5):
        d = mon + timedelta(days=i)
        day = attendance_day(state, d)
        heads.append(f"{ATT_DAYS[i]} {d.strftime('%-d/%-m')}")
        # Show only the sessions that apply (e.g. "AM  Mid"), not a tick/dot for every session
        fmt = lambda lst: "  ".join(ATT_SESSION_LABEL[x] for x in ATT_SESSIONS if x in lst) or "—"
        rows["Planned"].append("No school" if day["no_school"] else fmt(day["planned"]))
        rows["Actual"].append("—" if day["no_school"] else fmt(day["actual"]))
        e = day["exc"]
        rows["Note"].append("" if not e else (e["type"] + (f": {e['reason']}" if e.get("reason") else "")))
    st.table(pd.DataFrame(rows, index=None).T.rename(columns=dict(enumerate(heads))))

    t1, t2 = st.tabs(["📅 Usual weekly schedule", "✏️ Add an exception for a day"])

    # ── usual weekly schedule ──
    with t1:
        cur = attendance_current_days(state)
        for dname in ATT_DAYS:
            if f"att_sched_{student_id}_{dname}" not in st.session_state:
                st.session_state[f"att_sched_{student_id}_{dname}"] = cur[dname]
        presets = {
            "Choose a quick start…": None,
            "Full time (all sessions, Mon–Fri)": {d: list(ATT_SESSIONS) for d in ATT_DAYS},
            "Mornings only, Mon–Fri": {d: ["Morning"] for d in ATT_DAYS},
            "Mon–Wed full days": {d: (list(ATT_SESSIONS) if d in ("Mon", "Tue", "Wed") else []) for d in ATT_DAYS},
            "Tue–Thu full days": {d: (list(ATT_SESSIONS) if d in ("Tue", "Wed", "Thu") else []) for d in ATT_DAYS},
        }
        pc1, pc2 = st.columns([3, 1])
        pick = pc1.selectbox("Quick start", list(presets), key=f"att_preset_{student_id}", label_visibility="collapsed")
        if pc2.button("Apply", key=f"att_preset_go_{student_id}", use_container_width=True) and presets[pick]:
            for dname in ATT_DAYS:
                st.session_state[f"att_sched_{student_id}_{dname}"] = presets[pick][dname]
        cols = st.columns(5)
        new_days = {}
        for i, dname in enumerate(ATT_DAYS):
            new_days[dname] = cols[i].multiselect(ATT_DAYS_FULL[i], ATT_SESSIONS, key=f"att_sched_{student_id}_{dname}")
        frm = st.date_input("Applies from (the Monday this pattern starts)", value=_att_monday(date.today()),
                            key=f"att_from_{student_id}")
        notes = st.text_input("Schedule notes (optional)", value=state.get("notes", ""), key=f"att_notes_{student_id}",
                              placeholder="e.g. Building up to full days over Term 4")
        if st.button("💾 Save weekly schedule", type="primary", key=f"att_save_sched_{student_id}", use_container_width=True):
            ver = {"from": frm.isoformat(), "days": {d: [x for x in ATT_SESSIONS if x in new_days[d]] for d in ATT_DAYS}, "note": notes}
            state["schedule"] = [v for v in state["schedule"] if v["from"] != ver["from"]] + [ver]
            state["notes"] = notes
            attendance_persist(student_id, state)
            st.success("✅ Schedule saved.")
            st.rerun()
        if state["schedule"]:
            st.markdown("**Schedule history** (the pattern in force on each date is used for the analysis)")
            for v in sorted(state["schedule"], key=lambda v: v["from"], reverse=True):
                txt = " · ".join(f"{d} {_att_sess_text(v['days'].get(d, []))}" for d in ATT_DAYS)
                c1, c2 = st.columns([6, 1])
                c1.markdown(f"From **{v['from'] if v['from'] != '2000-01-01' else 'the start'}**: {txt}")
                if c2.button("Remove", key=f"att_rmv_{student_id}_{v['from']}"):
                    state["schedule"] = [x for x in state["schedule"] if x["from"] != v["from"]]
                    attendance_persist(student_id, state); st.rerun()

    # ── exceptions ──
    with t2:
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Date", value=date.today(), key=f"att_ex_date_{student_id}")
        typ = c2.selectbox("What happened", ATT_TYPES, key=f"att_ex_type_{student_id}")
        st.caption(ATT_TYPE_HELP[typ])
        d2 = d1
        if typ in ("Absent", "No school"):
            if st.checkbox("Several days in a row", key=f"att_ex_multi_{student_id}_{typ}"):
                d2 = st.date_input("Last day", value=d1, min_value=d1, key=f"att_ex_end_{student_id}_{typ}")
        sessions = []
        if typ not in ("Absent", "No school"):
            default = {"Finished early": ["Morning", "Middle"], "Arrived late": ["Middle", "Afternoon"],
                       "Extra day": list(ATT_SESSIONS)}.get(typ) or attendance_day(state, d1)["planned"]
            sessions = st.multiselect("Sessions attended", ATT_SESSIONS, default=default,
                                      key=f"att_ex_sess_{student_id}_{typ}_{d1.isoformat()}")
        rdef = {"Finished early": 0, "Absent": 3, "Arrived late": 3}.get(typ, 6)
        reason = st.selectbox("Reason", ATT_REASONS, index=rdef, key=f"att_ex_reason_{student_id}_{typ}")
        left_t = ""
        if typ == "Finished early":
            left_t = st.text_input("Time they left (optional, e.g. 11:30)", key=f"att_ex_left_{student_id}",
                                   help="For a negotiated day end, the time agreed with the student.").strip()
            if left_t and not re.match(r"^\d{1,2}:\d{2}$", left_t):
                st.caption("Use the form 11:30 so it can be charted. It will be saved as text otherwise.")
        note = st.text_input("Note (optional)", key=f"att_ex_note_{student_id}",
                             placeholder="e.g. Left after recess when the first signs of escalation appeared")
        if st.button("➕ Add exception", type="primary", key=f"att_ex_add_{student_id}", use_container_width=True):
            added, d = 0, d1
            while d <= d2:
                if d.weekday() < 5 or typ in ("Extra day", "Different sessions"):
                    state["exceptions"] = [e for e in state["exceptions"] if e["date"] != d.isoformat()] + [
                        {"date": d.isoformat(), "type": typ, "sessions": sessions,
                         "reason": ("" if typ == "No school" else reason), "note": note, "left": left_t}]
                    added += 1
                d += timedelta(days=1)
            if added:
                attendance_persist(student_id, state)
                st.rerun()
            else:
                st.warning("That range only covers weekend days.")
        excs = sorted(state["exceptions"], key=lambda e: e["date"], reverse=True)
        if excs:
            st.markdown(f"**Recorded exceptions ({len(excs)})**, most recent first")
            for e in excs[:12]:
                c1, c2 = st.columns([6, 1])
                extra = (f" ({_att_sess_text(e.get('sessions'))})" if e["type"] in ("Finished early", "Arrived late", "Different sessions", "Extra day") else "")
                c1.markdown(f"**{e['date']}** · {e['type']}{extra}" + (f" · {e['reason']}" if e.get("reason") else "")
                            + (f" · left {e['left']}" if e.get("left") else "")
                            + (f" · *{e['note']}*" if e.get("note") else ""))
                if c2.button("Remove", key=f"att_ex_rm_{student_id}_{e['date']}"):
                    state["exceptions"] = [x for x in state["exceptions"] if x["date"] != e["date"]]
                    attendance_persist(student_id, state); st.rerun()
            if len(excs) > 12:
                st.caption(f"{len(excs) - 12} older exception(s) not shown.")
        else:
            st.info("No exceptions recorded. Days are assumed to go to plan.")


ATT_CAT_COLORS = {
    "Attended": "#99d5cf",
    "Day end: avoid potential escalation": "#d97706",
    "Day end: needs reset": "#3b82f6",
    "Day end: negotiated": "#7c3aed",
    "C.I. (critical incident)": "#be123c",
    "Left early (other reason)": "#94a3b8",
    "Absent": "#cbd5e1",
    "Arrived late": "#c4b5a5",
    "Different sessions": "#e9d5ff",
}


def _att_loss_category(exc) -> str:
    if not exc:
        return "Different sessions"
    t, r = exc.get("type"), exc.get("reason")
    if t == "Absent": return "Absent"
    if t == "Arrived late": return "Arrived late"
    if t == "Finished early":
        if r == ATT_ESCALATION_REASON: return "Day end: avoid potential escalation"
        if r == ATT_RESET_REASON: return "Day end: needs reset"
        if r == ATT_NEGOTIATED_REASON: return "Day end: negotiated"
        if r == ATT_CI_REASON: return "C.I. (critical incident)"
        return "Left early (other reason)"
    return "Different sessions"


def _att_insight(text: str) -> None:
    st.markdown(
        "<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;padding:.75rem 1.1rem;margin:.5rem 0;"
        "font-size:.84rem;color:#1e293b;line-height:1.65;'><b>📊 Understanding this chart:</b><br>" + text + "</div>",
        unsafe_allow_html=True)


def attendance_analysis(state, full_df, start, end) -> dict:
    """Everything the attendance charts and conclusions are built from."""
    inc_dates = full_df["date_parsed"].dt.date
    weeks, d = [], _att_monday(start)
    while d <= end:
        row = {"week": d, "attended": 0, "lost": {}, "incidents": int(((inc_dates >= d) & (inc_dates <= d + timedelta(days=6))).sum())}
        for i in range(7):
            day = attendance_day(state, d + timedelta(days=i))
            if day["no_school"]:
                continue
            row["attended"] += len(day["actual"])
            gap = len([x for x in day["planned"] if x not in day["actual"]])
            if gap:
                c = _att_loss_category(day["exc"])
                row["lost"][c] = row["lost"].get(c, 0) + gap
        weeks.append(row); d += timedelta(days=7)
    by_dow = {n: {"attended": 0, "dayends": 0, "absent": 0, "inc": 0} for n in ATT_DAYS}
    ended = {x: {"Day end: avoid potential escalation": 0, "Day end: needs reset": 0, "Day end: negotiated": 0, "Left early (other reason)": 0} for x in ATT_SESSIONS}
    dayend_dates, d = [], start
    while d <= end:
        if d.weekday() < 5:
            day = attendance_day(state, d); n = ATT_DAYS[d.weekday()]
            if not day["no_school"]:
                by_dow[n]["attended"] += len(day["actual"])
                e = day["exc"]
                if e and e["type"] == "Absent": by_dow[n]["absent"] += 1
                if e and e["type"] == "Finished early":
                    by_dow[n]["dayends"] += 1
                    cat = _att_loss_category(e)
                    last = [x for x in ATT_SESSIONS if x in day["actual"]]
                    ended[last[-1] if last else "Morning"][cat] += 1
                    dayend_dates.append(d)
        d += timedelta(days=1)
    for dt, n in zip(inc_dates, full_df["date_parsed"].dt.weekday):
        if n < 5: by_dow[ATT_DAYS[n]]["inc"] += 1
    # what follows a day end: the next day the student attended
    follow_inc = follow_att = 0
    followed = 0
    for de in dayend_dates:
        nd = de + timedelta(days=1)
        while nd <= end and not attendance_day(state, nd)["actual"]:
            nd += timedelta(days=1)
        if nd <= end:
            followed += 1
            follow_att += len(attendance_day(state, nd)["actual"])
            follow_inc += int((inc_dates == nd).sum())
    total_att = sum(w["attended"] for w in weeks)
    other_att = max(total_att - follow_att, 0)
    other_inc = max(len(full_df) - follow_inc - int(inc_dates.isin(set(dayend_dates)).sum()), 0)
    half = start + (end - start) / 2
    first_half = sum(1 for x in dayend_dates if x <= half); second_half = len(dayend_dates) - first_half
    return {"weeks": weeks, "by_dow": by_dow, "ended": ended, "dayend_dates": dayend_dates,
            "follow": {"n": followed, "inc": follow_inc, "att": follow_att, "other_inc": other_inc, "other_att": other_att},
            "halves": (first_half, second_half), "total_att": total_att}


def render_attendance_context(student, full_df):
    """Attendance in the analysis: how much school the student actually attended, incidents
    relative to that, and what early finishes and day ends show about what helps."""
    sid = student["id"]
    state = attendance_state(sid)
    if not state["schedule"] and not state["exceptions"]:
        return
    if full_df is None or full_df.empty or "date_parsed" not in full_df.columns:
        return
    start, end = full_df["date_parsed"].min().date(), full_df["date_parsed"].max().date()
    sm = attendance_summary(state, start, end)
    if sm["expected"] == 0:
        return
    an = attendance_analysis(state, full_df, start, end)
    n = len(full_df)
    st.markdown("### 🗓️ Attendance Context")
    st.caption("Incident counts mean more when set against how much school the student actually attended, and day ends show "
               "where the day becomes too much and whether the reset works.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions expected", sm["expected"])
    c2.metric("Sessions attended", sm["attended"], f"{sm['attended'] / sm['expected'] * 100:.0f}% of expected")
    c3.metric("Incidents per 10 sessions", f"{(n / sm['attended'] * 10) if sm['attended'] else 0:.1f}")
    c4.metric("Day ends / early finishes", sm["early_days"], f"{sm['escalation_day_ends']} day ends" if sm["escalation_day_ends"] else None)

    # ── 1. weekly picture ──
    weeks = an["weeks"]
    if len(weeks) >= 2:
        xs = [w["week"].strftime("%-d %b") for w in weeks]
        fig = go.Figure()
        fig.add_bar(x=xs, y=[w["attended"] for w in weeks], name="Attended", marker_color=ATT_CAT_COLORS["Attended"], yaxis="y")
        for cat in [c for c in ATT_CAT_COLORS if c != "Attended"]:
            vals = [w["lost"].get(cat, 0) for w in weeks]
            if any(vals):
                fig.add_bar(x=xs, y=vals, name=cat, marker_color=ATT_CAT_COLORS[cat], yaxis="y")
        fig.add_scatter(x=xs, y=[(w["incidents"] / w["attended"] * 10) if w["attended"] else None for w in weeks],
                        name="Incidents per 10 sessions attended", mode="lines+markers", line=dict(color="#be123c", width=3), yaxis="y2")
        fig.update_layout(barmode="stack", height=380, margin=dict(t=30, b=40, l=50, r=50), legend=dict(orientation="h", y=1.18),
                          yaxis=dict(title="Sessions"), yaxis2=dict(title="Incidents per 10 sessions", overlaying="y", side="right", rangemode="tozero"),
                          xaxis=dict(title="Week starting"))
        st.plotly_chart(fig, use_container_width=True)
        busiest = max((w for w in weeks if w["attended"]), key=lambda w: w["incidents"] / w["attended"], default=None)
        _att_insight("Each bar is one week of school. The teal part is the sessions the student attended; the coloured parts are sessions "
                     "planned but not attended, by reason (amber, blue and purple are the three kinds of day end). The red line is incidents for every 10 sessions "
                     "attended, so a short week isn't mistaken for improvement. Look for weeks where coloured blocks grow and the line "
                     "rises or falls with them. "
                     + (f"The highest rate was the week starting {busiest['week'].strftime('%-d %b')} ({busiest['incidents']} incident(s) in "
                        f"{busiest['attended']} sessions)." if busiest else ""))

    # ── 2. which day of the week ──
    dow = an["by_dow"]
    if any(v["attended"] or v["dayends"] or v["absent"] for v in dow.values()):
        fig2 = go.Figure()
        fig2.add_bar(x=ATT_DAYS, y=[dow[x]["dayends"] for x in ATT_DAYS], name="Day ends / early finishes", marker_color="#d97706")
        fig2.add_bar(x=ATT_DAYS, y=[dow[x]["absent"] for x in ATT_DAYS], name="Absent days", marker_color="#cbd5e1")
        fig2.add_scatter(x=ATT_DAYS, y=[(dow[x]["inc"] / dow[x]["attended"] * 10) if dow[x]["attended"] else None for x in ATT_DAYS],
                         name="Incidents per 10 sessions attended", mode="lines+markers", line=dict(color="#be123c", width=3), yaxis="y2")
        fig2.update_layout(barmode="group", height=320, margin=dict(t=30, b=40, l=50, r=50), legend=dict(orientation="h", y=1.18),
                           yaxis=dict(title="Number of days"), yaxis2=dict(title="Incidents per 10 sessions", overlaying="y", side="right", rangemode="tozero"))
        st.plotly_chart(fig2, use_container_width=True)
        top_de = max(ATT_DAYS, key=lambda x: dow[x]["dayends"])
        _att_insight("Which weekdays carry the day ends, absences and incidents. A weekday where all three rise together points to something about "
                     "that day (the timetable, the staffing, what came before it) rather than the student alone."
                     + (f" Day ends are most frequent on {ATT_DAYS_FULL[ATT_DAYS.index(top_de)]}s ({dow[top_de]['dayends']})." if dow[top_de]["dayends"] else ""))

    # ── 3. when the day ends ──
    if an["dayend_dates"]:
        fig3 = go.Figure()
        for cat in ("Day end: avoid potential escalation", "Day end: needs reset", "Day end: negotiated", "Left early (other reason)"):
            vals = [an["ended"][x][cat] for x in ATT_SESSIONS]
            if any(vals):
                fig3.add_bar(x=[f"After {x}" for x in ATT_SESSIONS], y=vals, name=cat, marker_color=ATT_CAT_COLORS[cat])
        fig3.update_layout(barmode="stack", height=300, margin=dict(t=30, b=40, l=50, r=30), legend=dict(orientation="h", y=1.2),
                           yaxis=dict(title="Number of day ends", dtick=1))
        st.plotly_chart(fig3, use_container_width=True)
        tot = {x: sum(an["ended"][x].values()) for x in ATT_SESSIONS}
        topk = max(tot, key=tot.get)
        _att_insight("The last session the student attended on days that finished early. Day ends bunched after one session show where "
                     "the day starts to become too much, which is the place to try a planned break, lower demand or a negotiated "
                     f"alternative earlier. Most often the day ended after {topk} ({tot[topk]} of {len(an['dayend_dates'])}).")

        # ── 4. what the data suggests ──
        st.markdown("**What the day ends suggest**")
        pts = []
        f = an["follow"]
        if f["n"] >= 3 and f["att"] and f["other_att"]:
            r1, r2 = f["inc"] / f["att"] * 10, f["other_inc"] / f["other_att"] * 10
            if r1 < r2 * 0.8:
                pts.append(f"On the next day attended after a day end, incidents were lower ({r1:.1f} per 10 sessions) than on other days ({r2:.1f}). "
                           "The reset appears to be helping the student return settled.")
            elif r1 > r2 * 1.2:
                pts.append(f"On the next day attended after a day end, incidents were higher ({r1:.1f} per 10 sessions) than on other days ({r2:.1f}). "
                           "The day end may be postponing the difficulty rather than resolving it, so consider acting earlier in the day or planning the return.")
            else:
                pts.append(f"Incidents on the day after a day end ({r1:.1f} per 10 sessions) were similar to other days ({r2:.1f}), so there is no clear sign yet "
                           "of the day end helping or hurting the next day.")
        elif f["n"]:
            pts.append(f"Only {f['n']} day end(s) have a following day to compare, which is too few to draw a conclusion yet.")
        a1, a2 = an["halves"]
        if len(an["dayend_dates"]) >= 4:
            if a2 < a1:
                pts.append(f"Day ends are reducing: {a1} in the first half of the period and {a2} in the second half.")
            elif a2 > a1:
                pts.append(f"Day ends are increasing: {a1} in the first half of the period and {a2} in the second half. This is worth raising at the next case meeting.")
            else:
                pts.append(f"Day ends are steady at {a1} in each half of the period.")
        neg = sum(1 for dd in an["dayend_dates"] if next((e for e in state["exceptions"] if e["date"] == dd.isoformat()), {}).get("reason") == ATT_NEGOTIATED_REASON)
        if neg:
            pts.append(f"{neg} day end(s) were negotiated with the student, which builds their say in the plan. Note whether these become earlier, later or shorter over time.")
        for ptxt in pts:
            st.markdown(f"- {ptxt}")
        st.caption("Early patterns with few days are signals to discuss, not conclusions. Absences are not counted as day ends.")
    st.markdown("---")


def trial_attendance_line(student_id, start, end=None, full_df=None) -> str:
    """Attendance before vs during a strategy trial: how much school the student attended,
    how often the day ended early, and incidents per attended session."""
    state = attendance_state(student_id)
    if not start or (not state["schedule"] and not state["exceptions"]):
        return ""
    end = end or date.today()
    if end < start:
        return ""
    b_start, b_end = start - timedelta(days=28), start - timedelta(days=1)

    def _win(a, b):
        sm = attendance_summary(state, a, b)
        days = sum(1 for i in range((b - a).days + 1) if (a + timedelta(days=i)).weekday() < 5
                   and not attendance_day(state, a + timedelta(days=i))["no_school"])
        weeks = max(days, 1) / 5.0
        rate = None
        if full_df is not None and not full_df.empty and sm["attended"]:
            d = full_df["date_parsed"].dt.date
            rate = int(((d >= a) & (d <= b)).sum()) / sm["attended"] * 10
        return sm, weeks, rate
    sb, wb, rb = _win(b_start, b_end)
    sd, wd, rd = _win(start, end)
    if not sb["expected"] or not sd["expected"]:
        return ""
    bits = [f"{sb['attended'] / sb['expected'] * 100:.0f}% of expected sessions attended before, {sd['attended'] / sd['expected'] * 100:.0f}% during",
            f"day ends/early finishes {sb['early_days'] / wb:.1f}/wk before, {sd['early_days'] / wd:.1f}/wk during"]
    if rb is not None and rd is not None:
        bits.append(f"incidents per 10 attended sessions {rb:.1f} before, {rd:.1f} during")
    return "Attendance: " + "; ".join(bits) + "."


def load_placement_extensions_from_db(student_id):
    """Load all recorded placement extensions for a student from Supabase,
    oldest first."""
    if not supabase or not student_id:
        return []
    try:
        res = supabase.table("placement_extensions") \
            .select("*").eq("student_id", student_id).order("from_date").execute()
        return [
            {"id": row.get("id"), "from": row.get("from_date"), "to": row.get("to_date"), "reason": row.get("reason", "")}
            for row in (res.data or [])
        ]
    except Exception:
        return []


def save_placement_extension_to_db(student_id, from_date, to_date, reason):
    """Insert a new placement extension record in Supabase."""
    if not supabase or not student_id:
        return False
    try:
        supabase.table("placement_extensions").insert({
            "student_id": student_id,
            "from_date": from_date,
            "to_date": to_date,
            "reason": reason,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving extension: {e}")
        return False


def delete_placement_extension_from_db(extension_id):
    """Permanently delete a placement extension record from Supabase."""
    if not supabase or not extension_id:
        return False
    try:
        supabase.table("placement_extensions").delete().eq("id", extension_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting extension: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# BEHAVIOUR SUPPORT PLAN (student-lens, living document)
# Data-derived sections (Target Behaviours, Possible Function, Known
# Triggers) are deliberately NOT stored — they're computed live from
# incident data every time the plan is opened, so they always reflect the
# latest data with no separate "refresh" step and no risk of ever being
# overwritten by (or overwriting) staff/student writing. Only the
# staff/student-authored sections below are persisted.
# ══════════════════════════════════════════════════════════════════════════
SUPPORT_PLAN_FIELDS = [
    "class_teacher", "support_staff", "date_commenced", "review_date",
    "strengths", "interests", "purpose", "early_warning_signs",
    "proactive_strategies_additional", "teaching_strategies",
    "response_early_signs", "response_escalation", "safety_risk_management",
    "post_incident_repair", "reinforcement", "adjustments_supports",
    "short_term_goals", "student_voice", "recovery_time",
]


def load_support_plan_from_db(student_id):
    """Load the staff/student-authored sections of a student's Behaviour
    Support Plan."""
    if not supabase or not student_id:
        return {}
    try:
        res = supabase.table("support_plans").select("*").eq("student_id", student_id).limit(1).execute()
        return res.data[0] if res.data else {}
    except Exception:
        return {}


def save_support_plan_to_db(student_id, data: dict, updated_by: str = ""):
    """Upsert the staff/student-authored sections of a Behaviour Support
    Plan. Only ever touches fields staff explicitly edited."""
    if not supabase or not student_id:
        return False
    try:
        payload = {k: v for k, v in data.items() if k in SUPPORT_PLAN_FIELDS}
        payload["student_id"] = student_id
        payload["last_updated_by"] = updated_by
        payload["last_updated_at"] = datetime.utcnow().isoformat()
        existing = supabase.table("support_plans").select("id").eq("student_id", student_id).limit(1).execute()
        if existing.data:
            supabase.table("support_plans").update(payload).eq("student_id", student_id).execute()
        else:
            supabase.table("support_plans").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Error saving support plan: {e}")
        return False


# ============================================
# STRATEGY TRIALS — suggest, run, measure, report back
# ============================================
# CLC-LBU's small, structured setting is where new strategies can actually be
# trialled and compared (a mainstream class of 30+ rarely can). Each trial is a
# hypothesis -> strategy -> measure -> outcome record per student, so what is
# learned here can travel with the student and inform receiving schools.
#
# Table (create once in Supabase):
#   create table strategy_trials (
#     id uuid primary key default gen_random_uuid(),
#     student_id text not null, title text, hypothesis text, strategy text,
#     measure text, focus_session text, start_date date, review_date date,
#     end_date date, status text default 'Running', outcome text, conclusion text,
#     observations jsonb default '[]'::jsonb, created_by text,
#     created_at timestamptz default now());
# If the table doesn't exist the tool still works for the current session only.

TRIAL_OUTCOMES = ["Worked well", "Partly helped", "No clear change", "Made things harder", "Adapted — new version to trial"]


def _tr_text(v, default=""):
    try:
        if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
            return default
    except (TypeError, ValueError):
        pass
    return str(v).strip() or default


def build_trial_suggestions(full_df, max_n: int = 3) -> list[dict]:
    """Turn this student's data pattern into specific, trialable strategies.
    Each carries the evidence it is based on, a provisional hypothesis (never
    a conclusion), a strategy offering genuinely acceptable choices, and what
    to measure. Rule-based so it is predictable and always grounded in data."""
    if full_df is None or full_df.empty:
        return []
    df = full_df.copy()
    total = len(df)
    sugg = []

    def _pct(n): return f"{n} of {total} incidents ({n/total*100:.0f}%)"

    # --- patterns ---
    sess = df["session"].value_counts() if "session" in df.columns else pd.Series(dtype=int)
    locs = df["location"].fillna("").astype(str).value_counts() if "location" in df.columns else pd.Series(dtype=int)
    cats = (df["antecedent"].apply(categorize_antecedent) if "antecedent" in df.columns else pd.Series([None] * total)).value_counts()
    beh = df["behaviour_type"].fillna("").astype(str) if "behaviour_type" in df.columns else pd.Series([""] * total, index=df.index)
    verbal = int(beh.str.contains("verbal|swear|vocal|calling out|commentary|abuse", case=False, regex=True).sum())

    def _mins(t):
        try:
            h, m = str(t).split(":")[:2]; return int(h) * 60 + int(m)
        except Exception:
            return None
    arrival = 0
    if "time" in df.columns:
        _m = df["time"].apply(_mins)
        arrival = int(((_m >= 8 * 60) & (_m <= 9 * 60 + 45)).sum())

    # 1. Arrival / entry anxiety
    morning = int(sess.get("Morning", 0))
    if arrival >= 3 and arrival / total >= 0.3 or (morning / total >= 0.5 and verbal >= 2):
        n_ev = arrival if arrival >= 3 else morning
        sugg.append({
            "key": "arrival_entry", "score": n_ev / total + 0.15,
            "title": "Arrival: perceived-choice entry to the morning",
            "evidence": f"{_pct(n_ev)} happen {'around arrival (8:00–9:45)' if arrival >= 3 else 'in the morning session'}"
                        + (f", with {verbal} verbal outburst(s)." if verbal else "."),
            "hypothesis": "Entering the room and being seen by peers may feel anxious or exposing, and the outburst may be masking that "
                          "anxiety rather than being aimed at anyone. (Provisional: the trial will help test this.)",
            "strategy": "At arrival, greet calmly and offer a perceived choice of how to start the morning. Both options are fine: "
                        "(a) begin in the aligned room, away from other students, and join the group at an agreed later time; or "
                        "(b) take a short moment outside the room first, then enter. Say nothing about earlier outbursts at the door and "
                        "keep demands minimal for the first few minutes.",
            "measure": "Daily: outbursts or incidents in the first 30 minutes, which option was chosen, and how long before joining the group.",
            "focus_session": "Morning"})

    # 2. Demand / instruction
    sig = demand_avoidance_signal(df)
    n_ins = int(cats.get("Instructions", 0))
    if n_ins / total >= 0.3 or sig["flag"]:
        n_ev = max(n_ins, sig["n"]) if sig["flag"] else n_ins
        sugg.append({
            "key": "instruction_choice", "score": n_ev / total,
            "title": "Instructions: declarative language and perceived choice",
            "evidence": f"{_pct(n_ev)} linked to instructions, demands or refusal/avoidance.",
            "hypothesis": "Direct demands may be felt as a loss of control, prompting refusal as a way to regain it.",
            "strategy": "Swap direct commands for invitations and two acceptable options (what, where, with whom or in what order, never whether). "
                        "e.g. 'Do you want to start with the reading or the writing?' Drop non-essential demands during the peak session.",
            "measure": "Tally per day: first instructions followed within 2 minutes, refusals, and how often a choice was offered.",
            "focus_session": ""})

    # 3. Transition
    n_tr = int(cats.get("Transition", 0))
    if n_tr / total >= 0.3:
        sugg.append({
            "key": "transition_choice", "score": n_tr / total,
            "title": "Transitions: shared control of the routine",
            "evidence": f"{_pct(n_tr)} follow a transition.",
            "hypothesis": "Sudden change may feel unpredictable; sharing control of how the change happens may reduce threat.",
            "strategy": "Give a 5-then-2-minute warning with a visual, then offer a choice within the transition (which route, which job, "
                        "who walks with them, what they carry). Both options meet the same goal.",
            "measure": "Per transition: smooth, needed support, or incident. Note which choice was picked.",
            "focus_session": ""})

    # 4. Peer
    n_pe = int(cats.get("Peer", 0))
    if n_pe / total >= 0.3:
        sugg.append({
            "key": "peer_choice", "score": n_pe / total,
            "title": "Peers: choice of when and with whom",
            "evidence": f"{_pct(n_pe)} are peer-related.",
            "hypothesis": "Unstructured peer proximity may be the trigger, and having a say in the social load may help.",
            "strategy": "Offer a structured choice for high-risk times: join a supported small group, or take a parallel activity near a "
                        "trusted adult, with a planned time to rejoin. Both are positive options, not a consequence.",
            "measure": "Peer-related incidents per week; which option chosen; whether the student rejoined.",
            "focus_session": ""})

    # 5. Sensory
    n_se = int(cats.get("Sensory", 0))
    if n_se / total >= 0.25:
        sugg.append({
            "key": "sensory_choice", "score": n_se / total,
            "title": "Sensory: prepare the body before the busy moment",
            "evidence": f"{_pct(n_se)} are sensory-linked.",
            "hypothesis": "Noise, light or crowding may be overloading the nervous system before any demand is placed.",
            "strategy": "Before the known busy session, offer a choice of sensory preparation: a quiet 5 minutes in a low-stimulation space, "
                        "or a movement or heavy-work task, then join.",
            "measure": "Incidents in the following session versus days without the prep; which option was chosen.",
            "focus_session": ""})

    # 6. Engagement
    n_en = int(cats.get("Engagement", 0))
    if n_en / total >= 0.3:
        sugg.append({
            "key": "engagement_start", "score": n_en / total,
            "title": "Task start: a strength-first, chosen starting point",
            "evidence": f"{_pct(n_en)} are linked to task engagement.",
            "hypothesis": "The start of a task may feel risky; a guaranteed early success and some control may lower that threshold.",
            "strategy": "Offer a choice of two starting tasks, one always at mastery level or linked to an interest. Chunk the task with a "
                        "visible endpoint and a planned movement break before fatigue.",
            "measure": "Time to begin the task; tasks completed; incidents during independent work.",
            "focus_session": ""})

    # 7. Afternoon
    aft = int(sess.get("Afternoon", 0))
    if aft / total >= 0.45:
        sugg.append({
            "key": "afternoon_reset", "score": aft / total,
            "title": "Afternoon: a planned reset after lunch",
            "evidence": f"{_pct(aft)} happen in the afternoon.",
            "hypothesis": "Fatigue, hunger or the unstructured lunch break may be carrying over into the afternoon.",
            "strategy": "Check food, water and tiredness, then offer a choice of reset: movement break or quiet time with a preferred activity, "
                        "before the first afternoon demand.",
            "measure": "Afternoon incidents per week; which reset was chosen.",
            "focus_session": "Afternoon"})

    # 8. Unstructured space
    _yard = int(sum(c for l, c in locs.items() if re.search(r"yard|playground|oval|outside", l, re.I)))
    if _yard / total >= 0.4:
        sugg.append({
            "key": "yard_choice", "score": _yard / total,
            "title": "Break times: a choice of structured options",
            "evidence": f"{_pct(_yard)} happen outside or in the yard.",
            "hypothesis": "Unstructured time may be the pressure point, and a ready choice of activity may reduce it.",
            "strategy": "Offer two ready options before break: a supported game or activity, or a quiet space with a trusted adult. "
                        "Both are valued choices, with a check-in at the end.",
            "measure": "Yard incidents per week; option chosen; ease of returning to class.",
            "focus_session": ""})

    sugg.sort(key=lambda d: -d["score"])
    if not sugg:
        sugg.append({
            "key": "baseline_choice", "score": 0.1,
            "title": "Start with choice at the start of the day",
            "evidence": "No single pattern stands out yet.",
            "hypothesis": "A small, predictable sense of control at the start of the day may help settle the student.",
            "strategy": "Offer a choice of how to begin the day (two acceptable options) and keep demands low for the first few minutes.",
            "measure": "Daily: how the first 30 minutes went (settled, needed support, incident).",
            "focus_session": "Morning"})
    return sugg[:max_n]


def load_trials(student_id) -> list[dict]:
    """Trials from Supabase (cached for the session, refreshed after any save), merged
    with any held only in this session (used if the table hasn't been created yet)."""
    ck = f"_trials_cache_{student_id}"
    if ck in st.session_state:
        rows = st.session_state[ck]
    else:
        rows = []
        if supabase and student_id:
            try:
                res = _db_retry(lambda: supabase.table("strategy_trials").select("*").eq("student_id", student_id).order("start_date", desc=True).execute())
                rows = res.data or []
                st.session_state["_trials_db_ok"] = True
                st.session_state[ck] = rows
            except Exception as e:
                # Only a missing table means "not saved permanently"; a network blip just retries next time.
                if not _is_transient_db_error(e):
                    st.session_state["_trials_db_ok"] = False
    local = st.session_state.get(f"trials_local_{student_id}", [])
    return rows + [t for t in local if t.get("id") not in {r.get("id") for r in rows}]


def save_trial(student_id, trial: dict) -> bool:
    """Insert or update a trial. Falls back to session storage (returning False, with the
    reason in session_state['_last_save_error']) if the database save fails."""
    trial = dict(trial)
    trial["student_id"] = student_id
    st.session_state.pop(f"_trials_cache_{student_id}", None)
    st.session_state.pop("_last_save_error", None)
    if supabase:
        try:
            if trial.get("id") and not str(trial["id"]).startswith("local-"):
                tid = trial.pop("id")
                _db_retry(lambda: supabase.table("strategy_trials").update(trial).eq("id", tid).execute())
            else:
                trial.pop("id", None)
                _db_retry(lambda: supabase.table("strategy_trials").insert(trial).execute())
            st.session_state.pop("_trials_save_problem", None)
            st.session_state["_trials_db_ok"] = True
            return True
        except Exception as e:
            st.session_state["_last_save_error"] = str(e)
    else:
        st.session_state["_last_save_error"] = "No database connection."
    loc_key = f"trials_local_{student_id}"
    lst = st.session_state.get(loc_key, [])
    if trial.get("id"):
        lst = [trial if t.get("id") == trial["id"] else t for t in lst]
    else:
        trial["id"] = f"local-{uuid.uuid4()}"
        lst.append(trial)
    st.session_state[loc_key] = lst
    st.session_state["_trials_save_problem"] = True
    return False


def compute_trial_effect(full_df, start, end=None, focus_session: str = "") -> dict | None:
    """Compare incidents per school week in the (up to) 4 weeks before the
    trial with the trial period itself, overall and in the targeted session.
    Preliminary by design: it does not account for absences."""
    if full_df is None or full_df.empty or "date_parsed" not in full_df.columns or not start:
        return None
    try:
        s_ts = pd.Timestamp(start).normalize()
        e_ts = pd.Timestamp(end).normalize() if end else pd.Timestamp(date.today())
    except Exception:
        return None
    df = full_df.dropna(subset=["date_parsed"])
    if df.empty or e_ts < s_ts:
        return None
    b_start = max(df["date_parsed"].min().normalize(), s_ts - pd.Timedelta(days=28))
    if b_start >= s_ts:
        return {"insufficient": True}
    def _wk(a, b): return max(int(np.busday_count(a.date(), b.date())), 1) / 5.0
    wk_b, wk_d = _wk(b_start, s_ts), _wk(s_ts, e_ts + pd.Timedelta(days=1))
    out = {"insufficient": False, "weeks_before": wk_b, "weeks_during": wk_d}
    def _slice(d):
        before = d[(d["date_parsed"] >= b_start) & (d["date_parsed"] < s_ts)]
        during = d[(d["date_parsed"] >= s_ts) & (d["date_parsed"] <= e_ts + pd.Timedelta(days=1))]
        return before, during
    for tag, d in (("all", df), ("focus", df[df["session"] == focus_session] if focus_session and "session" in df.columns else None)):
        if d is None:
            out[tag] = None; continue
        b, du = _slice(d)
        rb, rd = len(b) / wk_b, len(du) / wk_d
        sb = pd.to_numeric(b.get("severity"), errors="coerce").mean() if "severity" in b.columns else np.nan
        sd = pd.to_numeric(du.get("severity"), errors="coerce").mean() if "severity" in du.columns else np.nan
        out[tag] = {"n_before": len(b), "n_during": len(du), "rate_before": rb, "rate_during": rd,
                    "sev_before": None if pd.isna(sb) else float(sb), "sev_during": None if pd.isna(sd) else float(sd),
                    "pct": ((rd - rb) / rb * 100) if rb > 0 else None}
    return out


def _fmt_effect(block: dict | None, label: str) -> str:
    if not block:
        return ""
    pct = block["pct"]
    arrow = "no baseline to compare" if pct is None else f"{abs(pct):.0f}% {'fewer' if pct < 0 else 'more'} per week"
    return (f"{label}: {block['rate_before']:.1f}/wk before ({block['n_before']}) → {block['rate_during']:.1f}/wk during "
            f"({block['n_during']}), {arrow}.")


def _trial_date(v):
    try:
        return pd.Timestamp(v).date() if v else None
    except Exception:
        return None


def render_strategy_trials(student, full_df):
    student_id = student["id"]
    st.markdown("### 🧪 Strategies to Trial")
    st.caption("Suggestions are drawn from this student's own pattern. Each is a hypothesis to test, not a conclusion. "
               "Run it for a few weeks, note what you see, then record what you learned. That evidence can travel "
               "with the student to a receiving school.")
    if st.session_state.get("_trials_db_ok") is False or st.session_state.get("_trials_save_problem"):
        show_save_problem("Strategy trials", STRATEGY_TRIALS_SQL)
    me = (st.session_state.get("current_user") or {}).get("name", "") or ""
    trials = load_trials(student_id)
    running_titles = {t.get("title") for t in trials if t.get("status") == "Running"}

    _data_sugg = build_trial_suggestions(full_df, max_n=8)
    _profile = load_starting_profile(student_id)
    _psugg = build_profile_trial_suggestions(_profile, _data_sugg)
    _covered = {STARTING_PROFILE_TAGS[t["tag"]].get("equiv") for t in (_profile or {}).get("tags", []) if t.get("include", True) and t.get("tag") in STARTING_PROFILE_TAGS}
    sugg = _psugg + [d for d in _data_sugg if d["key"] not in _covered][:3]
    if not sugg:
        st.info("Add a Starting Profile above, or log some incidents, to get trial suggestions.")
    for i, sg in enumerate(sugg):
        with st.container(border=True):
            st.markdown(f"**💡 {sg['title']}**" + ("  \n*📄 From the starting profile*" if sg.get("source") == "profile" else "  \n*📊 From incident data*"))
            st.markdown(f"*{'Where this comes from' if sg.get('source') == 'profile' else 'What the data shows'}:* {sg['evidence']}")
            if sg.get('data_note'):
                st.markdown(f"*{sg['data_note']}*")
            st.markdown(f"*Hypothesis to test:* {sg['hypothesis']}")
            st.markdown(f"*Strategy to trial:* {sg['strategy']}")
            st.markdown(f"*What to track:* {sg['measure']}")
            if sg["title"] in running_titles:
                st.success("This trial is already running (see below).")
                continue
            if st.button("▶️ Start this trial", key=f"trial_start_{student_id}_{sg['key']}"):
                st.session_state[f"trial_form_{student_id}"] = i
    open_i = st.session_state.get(f"trial_form_{student_id}")
    if open_i is not None and 0 <= open_i < len(sugg):
        sg = sugg[open_i]
        with st.form(f"trial_new_{student_id}"):
            st.markdown(f"**Start trial: {sg['title']}**")
            c1, c2 = st.columns(2)
            _start = c1.date_input("Start date", value=date.today())
            _review = c2.date_input("Review date", value=date.today() + timedelta(days=21))
            _strat = st.text_area("Strategy (edit to fit this student)", value=sg["strategy"], height=130)
            _meas = st.text_area("What staff will track", value=sg["measure"], height=70)
            _sess = st.selectbox("Session this should affect most", ["", "Morning", "Middle", "Afternoon"],
                                 index=["", "Morning", "Middle", "Afternoon"].index(sg["focus_session"]),
                                 format_func=lambda x: x or "Whole day")
            ok = st.form_submit_button("✅ Start trial", type="primary")
        if ok:
            saved = save_trial(student_id, {
                "title": sg["title"], "hypothesis": sg["hypothesis"], "strategy": _strat, "measure": _meas,
                "focus_session": _sess, "start_date": _start.isoformat(), "review_date": _review.isoformat(),
                "status": "Running", "observations": [], "created_by": me})
            st.session_state.pop(f"trial_form_{student_id}", None)
            st.rerun()

    with st.expander("➕ Plan your own trial"):
        with st.form(f"trial_custom_{student_id}"):
            _t = st.text_input("Title", placeholder="e.g. Choice of first activity after lunch")
            _h = st.text_area("Hypothesis (what do you think is going on?)", height=70)
            _s = st.text_area("Strategy to trial", height=90)
            _m = st.text_area("What will staff track?", height=60)
            c1, c2, c3 = st.columns(3)
            _sd = c1.date_input("Start date", value=date.today(), key=f"cust_sd_{student_id}")
            _rd = c2.date_input("Review date", value=date.today() + timedelta(days=21), key=f"cust_rd_{student_id}")
            _fs = c3.selectbox("Session affected", ["", "Morning", "Middle", "Afternoon"], format_func=lambda x: x or "Whole day",
                               key=f"cust_fs_{student_id}")
            if st.form_submit_button("✅ Start trial", type="primary"):
                if not _t.strip() or not _s.strip():
                    st.error("Add at least a title and a strategy.")
                else:
                    save_trial(student_id, {"title": _t.strip(), "hypothesis": _h, "strategy": _s, "measure": _m,
                                            "focus_session": _fs, "start_date": _sd.isoformat(),
                                            "review_date": _rd.isoformat(), "status": "Running",
                                            "observations": [], "created_by": me})
                    st.rerun()

    if not trials:
        return
    st.markdown("#### 📋 Trials for this student")
    for t in trials:
        tid = str(t.get("id"))
        running = t.get("status") == "Running"
        start, review, end = _trial_date(t.get("start_date")), _trial_date(t.get("review_date")), _trial_date(t.get("end_date"))
        due = running and review and review <= date.today()
        badge = "🟢 Running" if running else f"✅ {t.get('outcome') or 'Concluded'}"
        with st.expander(f"{badge} — {t.get('title','')}" + (" — ⏰ review due" if due else ""), expanded=due):
            st.markdown(f"**Hypothesis:** {_tr_text(t.get('hypothesis'), '—')}")
            st.markdown(f"**Strategy:** {_tr_text(t.get('strategy'), '—')}")
            st.markdown(f"**Tracking:** {_tr_text(t.get('measure'), '—')}")
            st.caption(f"Started {start.strftime('%d/%m/%Y') if start else '—'} · review {review.strftime('%d/%m/%Y') if review else '—'}"
                       + (f" · ended {end.strftime('%d/%m/%Y')}" if end else "") + (f" · by {t.get('created_by')}" if t.get("created_by") else ""))
            eff = compute_trial_effect(full_df, start, end if not running else None, t.get("focus_session") or "")
            if eff and eff.get("insufficient"):
                st.info("Not enough earlier data to compare against yet.")
            elif eff:
                for line in (_fmt_effect(eff.get("focus"), f"{t.get('focus_session')} session"), _fmt_effect(eff.get("all"), "Whole day")):
                    if line:
                        st.markdown(f"📈 {line}")
                _al = trial_attendance_line(student_id, start, end if not running else None, full_df)
                if _al:
                    st.markdown(f"🗓️ {_al}")
                st.caption("Preliminary read from logged incidents. Fewer logged incidents is only one measure, and the attendance line shows whether "
                           "the student was at school more or less, so weigh both with the staff observations below.")
            obs = t.get("observations") or []
            if obs:
                st.markdown("**Staff observations**")
                for o in obs:
                    st.markdown(f"- {o.get('date','')} — {o.get('text','')}" + (f" *({o.get('by')})*" if o.get("by") else ""))
            if running:
                with st.form(f"trial_obs_{tid}"):
                    _o = st.text_input("Add an observation", placeholder="e.g. Chose to start in the quiet room 4/5 days; joined group by 9:20")
                    if st.form_submit_button("➕ Add"):
                        if _o.strip():
                            upd = dict(t); upd["observations"] = obs + [{"date": date.today().strftime("%d/%m"), "text": _o.strip(), "by": me}]
                            save_trial(student_id, upd); st.rerun()
                with st.form(f"trial_end_{tid}"):
                    st.markdown("**Conclude this trial**")
                    _out = st.selectbox("How did it go?", TRIAL_OUTCOMES, key=f"out_{tid}")
                    _con = st.text_area("What did you learn? What would you keep, change or pass on to a receiving school?", height=90, key=f"con_{tid}")
                    if st.form_submit_button("✅ Conclude trial"):
                        upd = dict(t); upd.update({"status": "Concluded", "outcome": _out, "conclusion": _con, "end_date": date.today().isoformat()})
                        save_trial(student_id, upd); st.rerun()
            else:
                st.markdown(f"**What we learned:** {_tr_text(t.get('conclusion'), '—')}")
                if st.button("↩️ Reopen", key=f"reopen_{tid}"):
                    upd = dict(t); upd.update({"status": "Running", "end_date": None}); save_trial(student_id, upd); st.rerun()


# ============================================
# STARTING PROFILE — suggestions from day one
# ============================================
# By the time incident data reveals a pattern, much of a placement may be gone.
# Staff can upload (or paste) the referral, transition report or earlier school
# information; themes are extracted and matched to trial-ready strategies so
# something useful can be tried in the first weeks. Only the extracted themes
# are kept, never the document itself, and the student's name is removed from
# the text before it goes to the AI. Staff confirm each theme before it is used.
#
# Table (create once in Supabase):
#   create table starting_profiles (
#     student_id text primary key, profile jsonb, updated_by text,
#     updated_at timestamptz default now());

STARTING_PROFILE_TAGS = {
    "difficult_start": {
        "label": "Finds the start of the day hard",
        "title": "Soft landing at the start of the day",
        "hypothesis": "Arriving and joining the group may feel unpredictable or exposing, and a calm, low-demand start may settle the student before anything is expected.",
        "strategy": "Greet calmly and offer a choice of how to begin. Both options are fine: settle in a quieter space and join the group at an agreed later time, or take a short moment outside first. Keep demands low and skip questions about the morning for the first few minutes. Follow with a predictable first task the student can succeed at.",
        "measure": "Daily: how the first 30 minutes went (settled, needed support, incident), which option was chosen, and time to join the group.",
        "focus_session": "Morning", "equiv": "arrival_entry"},
    "demand_avoidance": {
        "label": "Strong need for control, resists direct demands",
        "title": "Low-demand, perceived-choice approach",
        "hypothesis": "Direct demands may feel like a loss of control, prompting refusal or escalation to regain it. This fits a demand-avoidant presentation, whether or not it is diagnosed.",
        "strategy": "Swap commands for invitations and declarative language ('I wonder if...'). Offer two acceptable options about what, where, with whom or in what order, never whether. Keep a few non-negotiables (safety) and drop the rest. Avoid ultimatums and public correction, and hand control back in small safe ways (setting the timer, choosing the start point).",
        "measure": "Tally per day: first instructions followed within 2 minutes, refusals or escalations, and how often a choice was offered.",
        "focus_session": "", "equiv": "instruction_choice"},
    "subject_difficulty": {
        "label": "Finds a particular subject very hard",
        "title": "{subject}: prepare, support closely, lower the demand",
        "hypothesis": "{subject} may feel overwhelming or exposing, and leaving the room or escalating may be a way to escape that feeling.",
        "strategy": "Before {subject}, prepare the student: preview what is coming, agree the first step and when the lesson will finish, and offer a choice of how to start. During the lesson, stay close, lower the demand (shorter chunked tasks, fewer items, a familiar entry point) and set up early chances to succeed. Notice and name effort, not only correct answers. Agree a way to pause (break card) before the student reaches the point of leaving.",
        "measure": "Per {subject} lesson: stayed in the room, needed a break, or left; time to first task; success moments noted.",
        "focus_session": "", "equiv": None},
    "transitions": {
        "label": "Finds changes and transitions hard",
        "title": "Transitions: shared control of the routine",
        "hypothesis": "Sudden change may feel unpredictable, and sharing control of how the change happens may reduce the threat.",
        "strategy": "Give a 5-then-2-minute warning with a visual, then offer a choice within the transition (which route, which job, who walks with them, what they carry). Both options reach the same goal.",
        "measure": "Per transition: smooth, needed support, or incident. Note which choice was picked.",
        "focus_session": "", "equiv": "transition_choice"},
    "peer_difficulty": {
        "label": "Finds peer relationships hard",
        "title": "Peers: choice of when and with whom",
        "hypothesis": "Unstructured peer proximity may be the pressure point, and having a say in the social load may help.",
        "strategy": "Offer a structured choice at higher-risk times: join a supported small group, or work on a parallel activity near a trusted adult with a planned time to rejoin. Both are positive options, not a consequence.",
        "measure": "Peer-related incidents per week, which option was chosen, and whether the student rejoined.",
        "focus_session": "", "equiv": "peer_choice"},
    "sensory": {
        "label": "Sensory sensitivities or needs",
        "title": "Sensory: prepare the body before the busy moment",
        "hypothesis": "Noise, light or crowding may overload the nervous system before any demand is placed.",
        "strategy": "Before the known busy session, offer a choice of sensory preparation: a quiet 5 minutes in a low-stimulation space, or a movement or heavy-work task, then join. Offer it discreetly.",
        "measure": "Incidents in the following session on days with and without the prep; which option was chosen.",
        "focus_session": "", "equiv": "sensory_choice"},
    "emotional_regulation": {
        "label": "Escalates quickly, big emotional responses",
        "title": "Regulate first: early signs and a choice of reset",
        "hypothesis": "Big reactions may come when the student's stress response takes over before they have a way to settle.",
        "strategy": "Identify the early warning signs with the student, and agree a short menu of two reset options (movement, quiet space, trusted adult). Offer the menu at the first signs, using few words and a calm tone, and keep any talking about it until the student is regulated.",
        "measure": "Per day: early signs noticed, reset option used, and whether escalation was avoided.",
        "focus_session": "", "equiv": None},
    "low_confidence": {
        "label": "Fear of failure, low confidence or perfectionism",
        "title": "Success first: a guaranteed early win",
        "hypothesis": "Starting a task may feel risky, and a guaranteed early success may lower the threshold for trying.",
        "strategy": "Offer a choice of two starting tasks, one always at mastery level or linked to an interest. Model that mistakes are normal, praise effort and strategy rather than the answer, and keep a visible record of successes.",
        "measure": "Time to begin the task; tasks attempted; incidents during independent work.",
        "focus_session": "", "equiv": None},
    "attention_executive": {
        "label": "Difficulty starting, focusing or organising work",
        "title": "Chunk it, show it, check in",
        "hypothesis": "Large or vague tasks may be hard to start and sustain, and visible structure may help.",
        "strategy": "Break work into short, visible chunks with a checklist and a clear endpoint. Check in at the start of each chunk, build in movement before fatigue, and let the student choose the order of chunks.",
        "measure": "Chunks completed per session; time to start; prompts needed.",
        "focus_session": "", "equiv": None},
    "communication": {
        "label": "Difficulty expressing needs or understanding language",
        "title": "Make asking for help easy",
        "hypothesis": "Behaviour may be communicating a need the student cannot yet put into words.",
        "strategy": "Pre-teach key routines with visuals, allow extra processing time and use fewer words. Give the student an easy way to ask for a break or help without speaking (card, gesture, symbol) and respond to it every time.",
        "measure": "Times the student used the break or help signal, and what happened after.",
        "focus_session": "", "equiv": None},
    "unstructured_time": {
        "label": "Finds unstructured time hard (breaks, yard)",
        "title": "Break times: a choice of structured options",
        "hypothesis": "Unstructured time may be the pressure point, and a ready choice of activity may reduce it.",
        "strategy": "Before break, offer two ready options: a supported game or activity, or a quiet space with a trusted adult. Both are valued choices, with a check-in at the end.",
        "measure": "Incidents at break per week; option chosen; ease of returning to class.",
        "focus_session": "", "equiv": "yard_choice"},
    "adult_trust": {
        "label": "Finds it hard to trust or connect with adults",
        "title": "Connection before correction",
        "hypothesis": "Trust in adults may be fragile, so relationship safety needs to come before expectations.",
        "strategy": "Give the student a consistent key adult and a predictable greeting. Spend a few minutes of low-demand connection daily, repair quickly after any rupture, and keep correction private and brief.",
        "measure": "Weekly: quality of greetings and connection (1 to 5), and how quickly the student recovered after difficult moments.",
        "focus_session": "", "equiv": None},
    "anxiety": {
        "label": "Anxious presentation",
        "title": "Predictability and a named safe adult",
        "hypothesis": "Uncertainty may be driving some behaviour, and more predictability and a trusted person may settle it.",
        "strategy": "Preview the day and any changes on a visual schedule, name a safe adult the student can go to, and offer a choice of calming option at the first signs of worry.",
        "measure": "Daily: worry signs noticed, safe adult or calming option used, how the student settled.",
        "focus_session": "", "equiv": None},
}


def _extract_upload_text(f) -> str:
    """Plain text from an uploaded .docx / .pdf / .odt / .txt file."""
    name = f.name.lower()
    # getvalue() not read(): read() continues from where the last read stopped, so a second
    # click (or any rerun) returned empty bytes and the file looked blank.
    raw = f.getvalue()
    try:
        if name.endswith(".pdf"):
            try:
                import fitz
                d = fitz.open(stream=raw, filetype="pdf")
                txt = " ".join(pg.get_text() for pg in d); d.close()
                return txt
            except Exception:
                from pypdf import PdfReader
                return " ".join((pg.extract_text() or "") for pg in PdfReader(BytesIO(raw)).pages)
        if name.endswith(".odt"):
            import zipfile, xml.etree.ElementTree as _ET
            return " ".join(_ET.fromstring(zipfile.ZipFile(BytesIO(raw)).read("content.xml")).itertext())
        if name.endswith(".txt"):
            return raw.decode("utf-8", errors="ignore")
        from docx import Document as _D
        d = _D(BytesIO(raw))
        return " ".join([p.text for p in d.paragraphs if p.text.strip()] +
                        [c.text for t in d.tables for r in t.rows for c in r.cells if c.text.strip()])
    except Exception as e:
        return f"[Could not read {f.name}: {e}]"


def _strip_student_name(text: str, name: str) -> str:
    for tok in {t for t in re.split(r"\W+", name or "") if len(t) >= 3}:
        text = re.sub(rf"\b{re.escape(tok)}(?:'s)?\b", "the student", text, flags=re.I)
    return text


def extract_starting_profile(text: str, student_name: str) -> dict:
    """AI reads referral / transition information and returns confirmed-able themes
    tagged against the fixed STARTING_PROFILE_TAGS list."""
    tag_lines = "; ".join(f'"{k}" = {v["label"]}' for k, v in STARTING_PROFILE_TAGS.items())
    prompt = (
        "You support teachers at an alternative education setting. Read this information about a new student and "
        "identify which themes it describes. Use ONLY the tags provided, only where the document gives clear evidence, "
        "and do not diagnose. Return ONLY valid JSON, no markdown. Structure: "
        '{"summary":"2 sentence plain summary","strengths":["..."],"interests":["..."],'
        '"what_helps":["..."],"what_doesnt_help":["..."],'
        '"tags":[{"tag":"one of the tags","evidence":"short paraphrase from the document","detail":"for subject_difficulty give the subject name, else empty"}]}. '
        f"Allowed tags: {tag_lines}. "
        "Document: " + _strip_student_name(text, student_name)[:7000]
    )
    raw = groq_ai_call(prompt, max_tokens=2000, temperature=0.1)
    raw = raw.replace("```json", "").replace("```", "").strip()
    a, b = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[a:b + 1])
    tags, seen = [], set()
    for t in data.get("tags", []):
        k = str(t.get("tag", "")).strip()
        if k in STARTING_PROFILE_TAGS and (k, str(t.get("detail", ""))) not in seen:
            seen.add((k, str(t.get("detail", ""))))
            tags.append({"tag": k, "evidence": str(t.get("evidence", ""))[:300],
                         "detail": str(t.get("detail", ""))[:60], "include": True})
    return {"summary": str(data.get("summary", "")), "strengths": [str(x) for x in data.get("strengths", [])][:8],
            "interests": [str(x) for x in data.get("interests", [])][:8],
            "what_helps": [str(x) for x in data.get("what_helps", [])][:8],
            "what_doesnt_help": [str(x) for x in data.get("what_doesnt_help", [])][:8], "tags": tags}


def load_starting_profile(student_id) -> dict:
    ck = f"_profile_cache_{student_id}"
    if ck in st.session_state:
        return st.session_state[ck]
    if supabase and student_id:
        try:
            res = _db_retry(lambda: supabase.table("starting_profiles").select("*").eq("student_id", student_id).limit(1).execute())
            st.session_state["_profile_db_ok"] = True
            prof = (res.data[0].get("profile") if res.data else None) or st.session_state.get(f"starting_profile_{student_id}", {})
            st.session_state[ck] = prof
            return prof
        except Exception as e:
            if not _is_transient_db_error(e):
                st.session_state["_profile_db_ok"] = False
    return st.session_state.get(f"starting_profile_{student_id}", {})


def save_starting_profile(student_id, profile: dict, by: str = "") -> bool:
    """Save to the database. Always keeps a session copy; returns False (and records
    why in session_state['_last_save_error']) if the database save did not go through."""
    st.session_state[f"starting_profile_{student_id}"] = profile
    st.session_state[f"_profile_cache_{student_id}"] = profile
    st.session_state.pop("_last_save_error", None)
    if not supabase:
        st.session_state["_last_save_error"] = "No database connection."
        return False
    try:
        payload = {"student_id": str(student_id), "profile": profile, "updated_by": by,
                   "updated_at": datetime.utcnow().isoformat()}
        try:
            _db_retry(lambda: supabase.table("starting_profiles").upsert(payload, on_conflict="student_id").execute())
        except TypeError:
            _db_retry(lambda: supabase.table("starting_profiles").upsert(payload).execute())
        st.session_state["_profile_db_ok"] = True
        return True
    except Exception as e:
        st.session_state["_last_save_error"] = str(e)
        return False


STARTING_PROFILES_SQL = """create table if not exists starting_profiles (
  student_id text primary key,
  profile jsonb,
  updated_by text,
  updated_at timestamptz default now()
);
alter table starting_profiles disable row level security;"""

STRATEGY_TRIALS_SQL = """create table if not exists strategy_trials (
  id uuid primary key default gen_random_uuid(),
  student_id text not null,
  title text, hypothesis text, strategy text, measure text,
  focus_session text, start_date date, review_date date, end_date date,
  status text default 'Running', outcome text, conclusion text,
  observations jsonb default '[]'::jsonb, created_by text,
  created_at timestamptz default now()
);
alter table strategy_trials disable row level security;"""


def show_save_problem(what: str, sql: str):
    """Tell staff plainly when something only saved for this session, and why."""
    err = st.session_state.get("_last_save_error", "")
    st.warning(f"⚠️ {what} was kept for this session only, because it couldn't be saved to the database.")
    if err:
        st.caption(f"Reason given: {err}")
    st.caption("This usually means the table hasn't been created yet. Copy this into the Supabase SQL Editor and run it once:")
    st.code(sql, language="sql")


def build_profile_trial_suggestions(profile: dict, data_suggestions: list | None = None) -> list[dict]:
    """Trial suggestions for every confirmed theme in the starting profile, each
    noting what the incident data says so far (once there is any)."""
    out = []
    data_by_key = {d["key"]: d for d in (data_suggestions or [])}
    for t in (profile or {}).get("tags", []):
        if not t.get("include", True):
            continue
        meta = STARTING_PROFILE_TAGS.get(t.get("tag"))
        if not meta:
            continue
        subj = (t.get("detail") or "").strip() or "this subject"
        fmt = lambda x: x.replace("{subject}", subj)
        eq = data_by_key.get(meta.get("equiv"))
        out.append({
            "key": f"profile_{t['tag']}_{re.sub(r'[^a-z0-9]', '', subj.lower())}",
            "score": 1.0, "source": "profile",
            "title": fmt(meta["title"]),
            "evidence": "From the starting information: " + (t.get("evidence") or meta["label"]),
            "data_note": ("Incident data so far supports this: " + eq["evidence"]) if eq else "",
            "hypothesis": fmt(meta["hypothesis"]) + " (Provisional: the trial will help test this.)",
            "strategy": fmt(meta["strategy"]), "measure": fmt(meta["measure"]),
            "focus_session": meta["focus_session"]})
    return out


def render_starting_profile(student):
    """Upload / paste referral information, confirm the themes found, and save them."""
    sid = student["id"]
    me = (st.session_state.get("current_user") or {}).get("name", "") or ""
    profile = load_starting_profile(sid)
    n_tags = len([t for t in profile.get("tags", []) if t.get("include", True)]) if profile else 0
    label = "🌱 Starting Profile — get suggestions from day one" + (f" ({n_tags} themes saved)" if n_tags else "")
    with st.expander(label, expanded=not profile):
        st.caption("Upload or paste the referral, transition report or earlier school information. Themes (for example finding the "
                   "start of the day hard, resisting direct demands, or struggling with a subject) are matched to strategies you "
                   "can trial in the first weeks. The student's name is removed before the AI reads it, only the themes you "
                   "confirm are kept, and the document itself is not stored.")
        if st.session_state.get("_profile_db_ok") is False:
            show_save_problem("The starting profile", STARTING_PROFILES_SQL)
        files = st.file_uploader("Upload one or more documents", type=["docx", "pdf", "odt", "txt"],
                                 accept_multiple_files=True, key=f"sp_files_{sid}")
        pasted = st.text_area("…or paste text here", height=120, key=f"sp_paste_{sid}",
                              placeholder="Paste referral notes, a transition summary or previous school report…")
        if st.button("🤖 Find themes and suggestions", type="primary", key=f"sp_run_{sid}", use_container_width=True):
            _parts = [(f.name, _extract_upload_text(f).strip()) for f in (files or [])]
            text = "\n\n".join([t for _, t in _parts if t] + ([pasted] if pasted.strip() else [])).strip()
            if not text:
                if files:
                    st.warning("The file uploaded, but no readable text was found in it ("
                               + ", ".join(f"{n}: {len(t)} characters" for n, t in _parts)
                               + "). This usually means a scanned or image-only PDF. Try a Word version, or copy the text and paste it into the box below.")
                else:
                    st.warning("Upload a document or paste some text first.")
            elif not st.secrets.get("GROQ_API_KEY", ""):
                st.error("AI key not configured, so extraction isn't available.")
            else:
                with st.spinner("Reading and matching to strategies..."):
                    try:
                        prof = extract_starting_profile(text, student["name"])
                        if not save_starting_profile(sid, prof, me):
                            st.session_state[f"sp_save_problem_{sid}"] = True
                        for k in [k for k in st.session_state if str(k).startswith(f"sp_inc_") and str(k).endswith(sid)]:
                            del st.session_state[k]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not extract themes: {e}")
        if not profile:
            return
        st.markdown("---")
        if profile.get("summary"):
            st.info(profile["summary"])
        cs, ci = st.columns(2)
        with cs:
            if profile.get("strengths"):
                st.markdown("**Strengths**")
                for x in profile["strengths"]: st.markdown(f"- {x}")
            if profile.get("what_helps"):
                st.markdown("**What helps**")
                for x in profile["what_helps"]: st.markdown(f"- {x}")
        with ci:
            if profile.get("interests"):
                st.markdown("**Interests**")
                for x in profile["interests"]: st.markdown(f"- {x}")
            if profile.get("what_doesnt_help"):
                st.markdown("**What doesn't help**")
                for x in profile["what_doesnt_help"]: st.markdown(f"- {x}")
        st.markdown("**Confirm the themes to use.** Untick anything that doesn't fit, and edit the wording if needed.")
        tags = profile.get("tags", [])
        edited = []
        for i, t in enumerate(tags):
            meta = STARTING_PROFILE_TAGS.get(t["tag"], {})
            c1, c2 = st.columns([1, 4])
            inc = c1.checkbox(meta.get("label", t["tag"]), value=t.get("include", True), key=f"sp_inc_{i}_{sid}")
            ev = c2.text_input("Evidence" if not t.get("detail") else f"Evidence (subject: {t['detail']})", value=t.get("evidence", ""),
                               key=f"sp_ev_{i}_{sid}", label_visibility="collapsed")
            edited.append({**t, "include": inc, "evidence": ev})
        if st.button("💾 Save confirmed themes", key=f"sp_save_{sid}"):
            if save_starting_profile(sid, {**profile, "tags": edited}, me):
                st.session_state.pop(f"sp_save_problem_{sid}", None)
                st.success("Saved. See the suggested trials under 🧪 Strategies to Trial.")
                st.rerun()
            else:
                st.session_state[f"sp_save_problem_{sid}"] = True
        if st.session_state.get(f"sp_save_problem_{sid}"):
            show_save_problem("The starting profile", STARTING_PROFILES_SQL)


import time as _time_mod


def _is_transient_db_error(e) -> bool:
    msg = str(e).lower()
    return (isinstance(e, (BlockingIOError, ConnectionError, TimeoutError, OSError))
            or any(x in msg for x in ("temporarily unavailable", "timed out", "timeout", "connection", "reset by peer",
                                      "eof", "disconnected", "errno 11", "502", "503", "504")))


def _db_retry(fn, tries: int = 4, base: float = 0.5):
    """Run a database call, retrying brief network hiccups (e.g. [Errno 11]
    'Resource temporarily unavailable') with a short back-off before giving up."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if i == tries - 1 or not _is_transient_db_error(e):
                raise
            _time_mod.sleep(base * (2 ** i))


def _reload_into_session(key: str, loader):
    """Refresh a cached list from the database, but never replace good data
    with an empty list when the database could not be reached."""
    st.session_state.pop("_load_failed", None)
    data = loader()
    if st.session_state.pop("_load_failed", False):
        st.warning("Couldn't refresh from the database just now, so the previous data is still showing. Please try again in a moment.")
        return
    st.session_state[key] = data


def load_students_from_db():
    if not supabase:
        return MOCK_STUDENTS
    try:
        response = _db_retry(lambda: supabase.table('students').select('*').execute())
        students = []
        for row in response.data:
            students.append({
                "id": str(row['id']),
                "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() if row.get('first_name') else row.get('name', 'Unknown'),
                "first_name": row.get('first_name', ''),
                "last_name": row.get('last_name', ''),
                "edid": row.get('edid', ''),
                "grade": row.get('grade', '') or str(row.get('year_level', '')),
                "dob": row.get('dob', ''),
                "program": row.get('program', ''),
                "placement_start": row.get('placement_start'),
                "placement_end": row.get('placement_end'),
                "archived": row.get('archived', False)
            })
        return students
    except Exception as e:
        st.session_state["_load_failed"] = True
        st.error(f"Error loading students: {e}")
        return []

def save_student_to_db(student):
    if not supabase:
        return False
    try:
        data = {
            "first_name": (student.get('first_name') or student.get('name', '').split(' ')[0]).strip(),
            "last_name": (student.get('last_name') or ' '.join(student.get('name', '').split(' ')[1:])).strip() or '-',
            "edid": student.get('edid', ''),
            "name": f"{student.get('first_name', '')} {student.get('last_name', '')}".strip() or student.get('name', ''),
            "year_level": (lambda g: int(g.replace('Y','').replace('R','0').replace('r','0')) if g and str(g).upper() not in ['','NONE'] else 0)(str(student.get('grade', '') or '')),
            "dob": student.get('dob', ''),
            "program": student.get('program', ''),
            "placement_start": student.get('placement_start'),
            "placement_end": student.get('placement_end'),
            "archived": student.get('archived', False)
        }
        if 'id' in student and student['id'].startswith('stu_'):
            supabase.table('students').insert(data).execute()
        else:
            supabase.table('students').update(data).eq('id', student['id']).execute()
        return True
    except Exception as e:
        st.error(f"Error saving student: {e}")
        return False

def delete_student_from_db(student_id):
    if not supabase:
        return False
    try:
        supabase.table('students').delete().eq('id', student_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting student: {e}")
        return False

def load_staff_from_db():
    if not supabase:
        return MOCK_STAFF
    try:
        response = _db_retry(lambda: supabase.table('staff').select('*').execute())
        staff = []
        for row in response.data:
            staff.append({
                "id": str(row['id']),
                "name": row['name'],
                "email": row['email'],
                "password": row.get('password'),
                "password_hash": row.get('password_hash') or "",
                "role": row['role'],
                "program": row.get('program'),
                "phone": row.get('phone'),
                "notes": row.get('notes'),
                "receive_critical_emails": row.get('receive_critical_emails', True),
                "created_date": row.get('created_at', '')[:10] if row.get('created_at') else None
            })
        return staff
    except Exception as e:
        print(f"[load_staff_from_db error]: {e}")  # log to Render logs, not UI
        st.session_state["_load_failed"] = True
        return []

def save_staff_to_db(staff_member):
    if not supabase:
        return False
    try:
        sid   = str(staff_member.get("id", ""))
        email = staff_member.get("email", "").strip()
        data  = {
            "name":                    staff_member.get("name", ""),
            "email":                   email,
            "password":                staff_member.get("password"),
            "password_hash":           staff_member.get("password_hash") or None,
            "role":                    staff_member.get("role", ""),
            "program":                 staff_member.get("program"),
            "phone":                   staff_member.get("phone"),
            "notes":                   staff_member.get("notes"),
            "receive_critical_emails": staff_member.get("receive_critical_emails", True),
        }
        if sid and not sid.startswith("staff_"):
            # Real Supabase UUID — always UPDATE
            supabase.table("staff").update(data).eq("id", sid).execute()
        else:
            # New staff — check if email already exists first
            _existing = supabase.table("staff").select("id").eq(
                "email", email).limit(1).execute()
            if _existing.data:
                # Email exists — UPDATE that record instead of inserting
                _existing_id = _existing.data[0]["id"]
                supabase.table("staff").update(data).eq("id", _existing_id).execute()
            else:
                # Genuinely new — INSERT
                supabase.table("staff").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving staff: {e}")
        return False

def delete_staff_from_db(staff_id):
    if not supabase:
        return False
    try:
        supabase.table('staff').delete().eq('id', staff_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting staff: {e}")
        return False

def load_incidents_from_db(student_id=None):
    if not supabase:
        return []
    try:
        query = supabase.table('incidents').select('*')
        if student_id:
            query = query.eq('student_id', student_id)
        response = _db_retry(lambda: query.execute())
        incidents = []
        for row in response.data:
            incidents.append({
                "id": str(row['id']),
                "student_id": str(row['student_id']),
                "date": row['date'],
                "time": row['time'],
                "day": row['day_of_week'],
                "session": row['session'],
                "location": normalise_location(row.get("location", "")),
                "behaviour_type": row['behaviour_type'],
                "antecedent": row['antecedent'],
                "intervention": row['intervention'],
                "severity": row['severity'],
                "reported_by": str(row['reported_by']) if row.get('reported_by') else None,
                "description": row.get('description', ''),
                "duration_minutes": row.get('duration_minutes'),
                "hypothesis_function": row.get('hypothesis_function'),
                "hypothesis_item": row.get('hypothesis_item'),
                "is_critical": row.get('is_critical', False)
            })
        return incidents
    except Exception as e:
        st.session_state["_load_failed"] = True
        st.error(f"Error loading incidents: {e}")
        return []

def save_incident_to_db(incident):
    if not supabase:
        return False
    try:
        data = {
            "student_id": incident['student_id'],
            "date": incident['date'],
            "time": incident['time'],
            "day_of_week": incident['day'],
            "session": incident['session'],
            "location": incident['location'],
            "behaviour_type": incident['behaviour_type'],
            "antecedent": incident['antecedent'],
            "intervention": incident['intervention'],
            "severity": incident['severity'],
            "reported_by": incident.get('reported_by'),
            "description": incident.get('description', ''),
            "duration_minutes": incident.get('duration_minutes'),
            "hypothesis_function": incident.get('hypothesis_function'),
            "hypothesis_item": incident.get('hypothesis_item'),
            "is_critical": incident.get('is_critical', False)
        }
        if incident.get('db_exists'):
            # Editing an existing DB row — UPDATE
            supabase.table('incidents').update(data).eq('id', incident['id']).execute()
        else:
            # New incident — INSERT with client-generated UUID
            if incident.get('id'):
                data['id'] = incident['id']
            supabase.table('incidents').insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving incident: {e}")
        return False

def load_critical_incidents_from_db(student_id=None):
    if not supabase:
        return []
    try:
        query = supabase.table('critical_incidents').select('*')
        if student_id:
            query = query.eq('student_id', student_id)
        response = _db_retry(lambda: query.execute())
        critical = []
        for row in response.data:
            critical.append({
                "id": str(row['id']),
                "student_id": str(row['student_id']),
                "severity": row['severity'],
                "reported_by": str(row['reported_by']) if row.get('reported_by') else None,
                "ABCH_primary": {
                    "location": row['primary_location'],
                    "context": row['primary_context'],
                    "time": row['primary_time'],
                    "behaviour": row['primary_behaviour'],
                    "consequence": row['primary_consequence'],
                    "hypothesis_function": row.get('primary_hypothesis_function'),
                    "hypothesis_item": row.get('primary_hypothesis_item')
                },
                "ABCH_additional": row.get('additional_entries', []),
                "outcomes": row['outcomes'],
                "sapol_reference": row.get('sapol_reference'),
                "admin_summary": row.get('admin_summary'),
                "created_at": row.get('created_at')
            })
        return critical
    except Exception as e:
        st.session_state["_load_failed"] = True
        st.error(f"Error loading critical incidents: {e}")
        return []

def save_critical_incident_to_db(critical):
    if not supabase:
        return False
    try:
        primary = critical.get('ABCH_primary', {})
        audit_trail_json = critical.get('audit_trail', [])
        if isinstance(audit_trail_json, list):
            audit_trail_json = json.dumps(audit_trail_json)
        data = {
            "student_id": critical['student_id'],
            "severity": critical.get('severity', 5),
            "reported_by": critical.get('reported_by'),
            "primary_location": primary.get('location', ''),
            "primary_context": primary.get('context', ''),
            "primary_time": primary.get('time', ''),
            "primary_behaviour": primary.get('behaviour', ''),
            "primary_consequence": primary.get('consequence', ''),
            "primary_hypothesis_function": primary.get('hypothesis_function'),
            "primary_hypothesis_item": primary.get('hypothesis_item'),
            "additional_entries": critical.get('ABCH_additional', []),
            "outcomes": critical.get('intended_outcomes', []),
            "sapol_reference": critical.get('sapol_reference'),
            "admin_summary": critical.get('admin_summary'),
            "status": critical.get('status', 'draft'),
            "completed_by_id": critical.get('completed_by_id'),
            "reviewed_by_id": critical.get('reviewed_by_id'),
            "leader_approved_by_id": critical.get('leader_approved_by_id'),
            "assigned_to_id": critical.get('assigned_to_id'),
            "review_notes": critical.get('review_notes'),
            "leader_notes": critical.get('leader_notes'),
            "audit_trail": audit_trail_json,
            "completed_at": critical.get('completed_at'),
            "reviewed_at": critical.get('reviewed_at'),
            "leader_approved_at": critical.get('leader_approved_at'),
            "submitted_at": critical.get('submitted_at'),
            "include_audit_in_report": critical.get('include_audit_in_report', False)
        }
        if 'id' not in critical or not critical['id']:
            response = supabase.table('critical_incidents').insert(data).execute()
            if response.data:
                critical['id'] = response.data[0]['id']
        else:
            supabase.table('critical_incidents').update(data).eq('id', critical['id']).execute()
        return True
    except Exception as e:
        st.error(f"Error saving critical incident: {e}")
        return False


# ===================================================================
# CRITICAL INCIDENT WORKFLOW FUNCTIONS
# ===================================================================

def get_pending_reviews_for_user(user_id):
    if not supabase:
        return [c for c in st.session_state.critical_incidents
                if c.get('status') == 'pending_review' and c.get('assigned_to_id') == user_id]
    try:
        response = supabase.table('critical_incidents').select('*')\
            .eq('status', 'pending_review').eq('assigned_to_id', user_id).execute()
        return response.data
    except:
        return []

def get_pending_leader_approvals(leader_id):
    if not supabase:
        return [c for c in st.session_state.critical_incidents
                if c.get('status') == 'pending_leader' and c.get('assigned_to_id') == leader_id]
    try:
        response = supabase.table('critical_incidents').select('*')\
            .eq('status', 'pending_leader').eq('assigned_to_id', leader_id).execute()
        return response.data
    except:
        return []

def get_manager_staff_id():
    if not supabase:
        manager = next((s for s in st.session_state.staff if s.get('role') == 'Leader'), None)
        return manager['id'] if manager else None
    try:
        response = supabase.table('staff').select('id').eq('role', 'Leader').limit(1).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except:
        return None

def add_audit_trail_entry(critical_incident, action, staff_name, notes=""):
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "staff": staff_name,
        "notes": notes
    }
    if 'audit_trail' not in critical_incident:
        critical_incident['audit_trail'] = []
    if isinstance(critical_incident['audit_trail'], str):
        try:
            critical_incident['audit_trail'] = json.loads(critical_incident['audit_trail'])
        except:
            critical_incident['audit_trail'] = []
    critical_incident['audit_trail'].append(audit_entry)
    return critical_incident

def format_audit_trail(audit_trail):
    if not audit_trail:
        return "No audit trail"
    if isinstance(audit_trail, str):
        try:
            audit_trail = json.loads(audit_trail)
        except:
            return "Error parsing audit trail"
    formatted = []
    for entry in audit_trail:
        timestamp = entry.get('timestamp', 'Unknown time')
        action = entry.get('action', 'Unknown action')
        staff = entry.get('staff', 'Unknown staff')
        notes = entry.get('notes', '')
        formatted.append(f"**{action}** by {staff} at {timestamp}")
        if notes:
            formatted.append(f"  Notes: {notes}")
    return "\n\n".join(formatted)

def generate_critical_incident_email_content(critical, student, include_audit=False):
    primary = critical.get('ABCH_primary', {})
    email_body = f"""
CRITICAL INCIDENT REPORT - {student['name']}

Date: {critical.get('created_at', 'N/A')}
Student: {student['name']} (Grade {student['grade']})
Program: {PROGRAM_NAMES.get(student['program'], student['program'])}

INCIDENT SUMMARY:
Location: {primary.get('location', 'N/A')}
Time: {primary.get('time', 'N/A')}
Behaviour: {primary.get('behaviour', 'N/A')}

FUNCTIONAL HYPOTHESIS:
{primary.get('hypothesis', 'N/A')}

INTENDED OUTCOMES:
{', '.join(critical.get('intended_outcomes', []))}

SAPOL REFERENCE:
{critical.get('sapol_reference', 'N/A')}

WORKFLOW STATUS:
Status: {critical.get('status', 'draft').replace('_', ' ').title()}
Completed by: {critical.get('completed_by_name', 'N/A')}
Reviewed by: {critical.get('reviewed_by_name', 'N/A')}
Approved by: {critical.get('leader_approved_by_name', 'N/A')}
"""
    if include_audit and critical.get('audit_trail'):
        email_body += "\n\nAUDIT TRAIL:\n"
        email_body += format_audit_trail(critical['audit_trail'])
    email_body += "\n\n---\nThis is an automated notification from the Behaviour Support Tool."
    return email_body


# ===================================================================
# EMAIL NOTIFICATION FUNCTIONS
# ===================================================================

def get_email_config():
    try:
        return {
            'smtp_server': st.secrets.get("email", {}).get("smtp_server", "smtp.gmail.com"),
            'smtp_port': st.secrets.get("email", {}).get("smtp_port", 587),
            'sender_email': st.secrets.get("email", {}).get("sender_email", ""),
            'sender_password': st.secrets.get("email", {}).get("sender_password", ""),
            'enabled': st.secrets.get("email", {}).get("enabled", False)
        }
    except:
        return {'smtp_server': 'smtp.gmail.com', 'smtp_port': 587, 'sender_email': '', 'sender_password': '', 'enabled': False}

def send_email(to_email, subject, body):
    config = get_email_config()
    if not config['enabled'] or not config['sender_email'] or not config['sender_password']:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = config['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['sender_email'], config['sender_password'])
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"⚠️ Email notification failed: {str(e)}")
        return False

def send_assignment_notification(assigned_staff, assigner_name, student_name, critical_id):
    if not assigned_staff.get('email'):
        return False
    subject = f"Critical Incident Review Assigned - {student_name}"
    body = f"""Hi {assigned_staff['name']},

A critical incident has been assigned to you for review.

STUDENT: {student_name}
ASSIGNED BY: {assigner_name}
ACTION REQUIRED: Review and approve the ABCH form

Please log in to the Behaviour Support Tool to review this incident.

---
This is an automated notification from the Behaviour Support Tool.
"""
    return send_email(assigned_staff['email'], subject, body)

def send_leader_notification(leader_staff, reviewer_name, student_name, critical_id):
    if not leader_staff.get('email'):
        return False
    subject = f"Critical Incident Awaiting Leader Approval - {student_name}"
    body = f"""Hi {leader_staff['name']},

A critical incident has been reviewed and is now awaiting your approval.

STUDENT: {student_name}
REVIEWED BY: {reviewer_name}
ACTION REQUIRED: Final review and approval

---
This is an automated notification from the Behaviour Support Tool.
"""
    return send_email(leader_staff['email'], subject, body)

def send_completion_notifications(critical, student, completed_by, reviewed_by, leader):
    emails_sent = []
    subject = f"Critical Incident Report Completed - {student['name']}"
    body = f"""The critical incident report for {student['name']} has been completed and submitted.

WORKFLOW SUMMARY:
- Completed by: {completed_by.get('name', 'Unknown')}
- Reviewed by: {reviewed_by.get('name', 'Unknown')}
- Approved by: {leader.get('name', 'Unknown')}
- Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

STUDENT: {student['name']} (Grade {student.get('grade', 'Unknown')})
PROGRAM: {PROGRAM_NAMES.get(student.get('program', ''), 'Unknown')}

---
This is an automated notification from the Behaviour Support Tool.
"""
    admin_email = "clc.admin281@schools.sa.edu.au"
    if send_email(admin_email, subject, body):
        emails_sent.append(f"Admin ({admin_email})")
    if completed_by.get('email'):
        if send_email(completed_by['email'], subject, body):
            emails_sent.append(f"{completed_by['name']}")
    if reviewed_by.get('email'):
        if send_email(reviewed_by['email'], subject, body):
            emails_sent.append(f"{reviewed_by['name']}")
    if leader.get('email'):
        if send_email(leader['email'], subject, body):
            emails_sent.append(f"{leader['name']}")
    return emails_sent


def init_state():
    ss = st.session_state
    if "logged_in" not in ss: ss.logged_in = False
    if "current_user" not in ss: ss.current_user = None
    if "current_page" not in ss: ss.current_page = "login"
    def _init_load(key, loader, fallback):
        # A failed load must NOT be cached as "no data": that made incidents look
        # lost until the session was restarted. Stop with a retry button instead.
        if key in ss:
            return
        if not supabase:
            ss[key] = fallback() if callable(fallback) else fallback
            return
        ss.pop("_load_failed", None)
        data = loader()
        if ss.pop("_load_failed", False):
            st.error("The database couldn't be reached just now (this is usually a brief network hiccup). "
                     "Nothing has been lost. Please try again.")
            if st.button("🔄 Try again", key=f"retry_load_{key}"):
                st.rerun()
            st.stop()
        ss[key] = data
    _init_load("students", load_students_from_db, MOCK_STUDENTS)
    _init_load("staff", load_staff_from_db, MOCK_STAFF)
    _init_load("incidents", load_incidents_from_db, lambda: generate_mock_incidents(70))
    _init_load("critical_incidents", load_critical_incidents_from_db, [])
    if "selected_program" not in ss: ss.selected_program = "JP"
    if "selected_student_id" not in ss: ss.selected_student_id = None
    if "current_incident_id" not in ss: ss.current_incident_id = None
    if "abch_rows" not in ss: ss.abch_rows = []
    if "ci_draft_id" not in ss: ss.ci_draft_id = None
    if "ci_last_saved" not in ss: ss.ci_last_saved = None
    if "show_critical_prompt" not in ss: ss.show_critical_prompt = False
    if "incident_prefill" not in ss: ss.incident_prefill = None
    if "last_saved_incident" not in ss: ss.last_saved_incident = None

def login_user(email: str, password: str) -> bool:
    email = (email or "").strip().lower()
    password = (password or "").strip()
    if not email or not password:
        return False
    import os
    try:
        ADMIN_EMAIL    = st.secrets.get("admin", {}).get("email", "") or os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        ADMIN_PASSWORD = st.secrets.get("admin", {}).get("password", "") or os.environ.get("BEHAVIOUR_ADMIN_PASSWORD", "")
    except Exception:
        ADMIN_EMAIL    = os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        ADMIN_PASSWORD = os.environ.get("BEHAVIOUR_ADMIN_PASSWORD", "")
    if ADMIN_EMAIL and email == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.current_user = {"id": "admin_bypass", "name": "Admin", "email": ADMIN_EMAIL, "role": "ADM"}
        st.session_state.current_page = "landing"
        return True
    for staff in st.session_state.staff:
        if staff.get("email", "").lower() == email and staff.get("role") == "ADM":
            if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.current_user = staff
                st.session_state.current_page = "landing"
                return True
    for staff in st.session_state.staff:
        # Match by email OR by name (case-insensitive)
        _staff_email = staff.get("email", "").lower()
        _staff_name  = staff.get("name", "").lower()
        if _staff_email != email and _staff_name != email:
            continue
        # Try bcrypt hash first
        stored_hash = staff.get("password_hash", "")
        if stored_hash:
            try:
                hash_bytes = stored_hash.encode('utf-8') if isinstance(stored_hash, str) else stored_hash
                if bcrypt.checkpw(password.encode('utf-8'), hash_bytes):
                    st.session_state.logged_in = True
                    st.session_state.current_user = staff
                    st.session_state.current_page = "landing"
                    return True
            except Exception:
                pass
        # Try plaintext password
        if staff.get("password") and staff.get("password") == password:
            st.session_state.logged_in = True
            st.session_state.current_user = staff
            st.session_state.current_page = "landing"
            return True
    return False

# ── Persistent sign-in ────────────────────────────────────────────────────
# Streamlit drops st.session_state whenever the browser connection drops
# (laptop sleep, idle tab, wifi change, refresh). To stop that logging staff out
# and losing their place, a signed, expiring token is kept in the page URL
# (?s=...) together with the current page (?p=) and student (?sid=). On a fresh
# session the token is verified and the user is put straight back where they were.
AUTH_TTL_SECONDS = 10 * 60 * 60      # stay signed in for 10 hours of the same browser tab
AUTH_REFRESH_SECONDS = 15 * 60       # re-issue the token when this much time has passed


def _auth_secret() -> bytes:
    import os, hashlib
    sec = ""
    try:
        sec = st.secrets.get("auth_secret", "") or ""
    except Exception:
        sec = ""
    sec = sec or os.environ.get("BEHAVIOUR_AUTH_SECRET", "")
    if not sec:
        # Fallback: derived from existing private settings so no new setup is required.
        parts = []
        try:
            parts.append(str(st.secrets.get("admin", {}).get("password", "")))
            parts.append(str(st.secrets.get("supabase", {}).get("key", "")))
        except Exception:
            pass
        parts.append(os.environ.get("BEHAVIOUR_ADMIN_PASSWORD", ""))
        sec = "clc-lbu|" + "|".join(parts)
    return hashlib.sha256(sec.encode("utf-8")).digest()


def make_auth_token(user: dict) -> str:
    import base64, hmac, hashlib, json, time
    payload = {"id": str(user.get("id", "")), "role": user.get("role", ""),
               "exp": int(time.time()) + AUTH_TTL_SECONDS, "iat": int(time.time())}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(_auth_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def read_auth_token(token: str):
    import base64, hmac, hashlib, json, time
    try:
        body, sig = (token or "").split(".", 1)
        good = hmac.new(_auth_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode())
        if int(data.get("exp", 0)) < time.time():
            return None
        return data
    except Exception:
        return None


def _qp_get(key: str) -> str:
    try:
        v = st.query_params.get(key, "")
        return v[0] if isinstance(v, list) else (v or "")
    except Exception:
        try:
            return st.experimental_get_query_params().get(key, [""])[0]
        except Exception:
            return ""


def _qp_set(**items):
    """Set/clear URL params (empty/None clears) without touching others, only when changed."""
    try:
        qp = st.query_params
        for k, v in items.items():
            if v:
                if qp.get(k, "") != str(v):
                    qp[k] = str(v)
            elif k in qp:
                del qp[k]
    except Exception:
        pass


def restore_login_from_url() -> bool:
    ss = st.session_state
    data = read_auth_token(_qp_get("s"))
    if not data:
        return False
    uid = data.get("id")
    user = None
    if uid == "admin_bypass":
        import os
        try:
            em = st.secrets.get("admin", {}).get("email", "") or os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        except Exception:
            em = os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        if em:
            user = {"id": "admin_bypass", "name": "Admin", "email": em, "role": "ADM"}
    else:
        user = next((s for s in ss.get("staff", []) if str(s.get("id")) == str(uid)), None)
    if not user:
        return False
    ss.logged_in = True
    ss.current_user = user
    p = _qp_get("p")
    ss.current_page = p if (p in VALID_PAGES and p != "login") else "landing"
    sid = _qp_get("sid")
    if sid and any(str(s.get("id")) == sid for s in ss.get("students", [])):
        match = next(s for s in ss.students if str(s.get("id")) == sid)
        ss.selected_student_id = match["id"]
    ss["_auth_issued"] = float(data.get("iat", 0))
    return True


def persist_login_to_url():
    import time
    ss = st.session_state
    if not ss.get("logged_in") or not ss.get("current_user"):
        return
    issued = ss.get("_auth_issued", 0) or 0
    if not _qp_get("s") or time.time() - issued > AUTH_REFRESH_SECONDS:
        _qp_set(s=make_auth_token(ss.current_user))
        ss["_auth_issued"] = time.time()
    _qp_set(p=ss.get("current_page") if ss.get("current_page") != "landing" else "",
            sid=str(ss.get("selected_student_id") or ""))


def do_logout():
    ss = st.session_state
    ss.logged_in = False
    ss.current_user = None
    ss.current_page = "login"
    ss.pop("_auth_issued", None)
    _qp_set(s="", p="", sid="")


def go_to(page: str, **kwargs):
    if page not in VALID_PAGES: return
    st.session_state.current_page = page
    for k, v in kwargs.items():
        setattr(st.session_state, k, v)
    st.rerun()

def get_student(sid):
    return next((s for s in st.session_state.students if s["id"] == sid), None)

def get_session_from_time(t):
    """Morning = before 11:00 | Middle = 11:00–13:30 | Afternoon = 13:31+"""
    total_mins = t.hour * 60 + t.minute
    if total_mins < 11 * 60:
        return "Morning"
    elif total_mins <= 13 * 60 + 30:
        return "Middle"
    else:
        return "Afternoon"

def generate_mock_incidents(n=70):
    incidents = []
    weights = {"stu_sy1": 12, "stu_py1": 10, "stu_sy2": 9, "stu_jp1": 8, "stu_py2": 7}
    pool = []
    for stu in MOCK_STUDENTS:
        pool.extend([stu] * weights.get(stu["id"], 5))
    for _ in range(n):
        stu = random.choice(pool)
        sev = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
        dt = datetime.now() - timedelta(days=random.randint(0, 90))
        dt = dt.replace(hour=random.choices([9,10,11,12,13,14,15], weights=[10,15,12,8,12,18,10])[0],
                       minute=random.randint(0,59), second=0)
        incidents.append({
            "id": str(uuid.uuid4()), "student_id": stu["id"], "student_name": stu["name"],
            "date": dt.date().isoformat(), "time": dt.time().strftime("%H:%M:%S"),
            "day": dt.strftime("%A"), "session": get_session_from_time(dt.time()),
            "location": random.choice(LOCATIONS), "behaviour_type": random.choice(BEHAVIOUR_TYPES),
            "antecedent": random.choice(ANTECEDENTS),
            "intervention": [random.choice(INTERVENTIONS)],
            "severity": sev, "reported_by": random.choice(MOCK_STAFF)["name"],
            "description": "Mock incident", "is_critical": sev >= 3, "duration_minutes": random.randint(2, 25)
        })
    return incidents


# ===================================================================
# PAGES
# ===================================================================

def render_login_page():
    st.markdown("""
    <div style="text-align:center; padding: 2.5rem 0 1.5rem 0;">
        <div style="display:inline-block; background:#1A7A7A; color:white; border-radius:16px;
                    padding: 1rem 2rem; margin-bottom: 1rem;">
            <span style="font-size:2rem;">📊</span>
        </div>
        <h1 style="color:#1A7A7A !important; font-size:1.8rem; margin:0.5rem 0 0.25rem;">
            Behaviour Support Tool
        </h1>
        <p style="color:#5a8a8a; font-size:0.95rem; margin:0;">
            Cowandilla Learning Centre — Learning & Behaviour Unit
        </p>
    </div>
    """, unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.container(border=True):
            st.markdown("<p style='color:#1A7A7A; font-weight:700; font-size:1.1rem; margin-bottom:1rem;'>Staff Sign In</p>", unsafe_allow_html=True)
            email = st.text_input("Email Address", placeholder="your.email@schools.sa.edu.au", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Sign In", type="primary", use_container_width=True):
                if login_user(email, password):
                    st.success(f"Welcome {st.session_state.current_user['name']}!")
                    st.rerun()
                else:
                    _staff_count = len(st.session_state.get("staff", []))
                    if _staff_count == 0:
                        st.error(
                            "⚠️ Could not load staff records from the database. "
                            "Check your Supabase connection on Render. "
                            "If Supabase is connected, try the admin bypass: "
                            "use the admin email and password from your Render environment variables."
                        )
                    else:
                        st.error(
                            f"Incorrect email or password ({_staff_count} staff records loaded). "
                            "Check your email address and password, or contact your admin to reset."
                        )
        st.markdown("<p style='text-align:center; color:#8aabab; font-size:0.8rem; margin-top:1rem;'>For access issues contact your program administrator</p>", unsafe_allow_html=True)


def render_landing_page():
    user = st.session_state.current_user or {}
    col_head, col_logout = st.columns([7, 1])
    with col_head:
        st.markdown(f"""
        <div style="border-left: 4px solid #1A7A7A; padding: 0.4rem 0 0.4rem 1rem; margin-bottom:0.5rem;">
            <p style="margin:0; color:#5a8a8a; font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.06em;">Behaviour Support Tool</p>
            <h2 style="margin:0; color:#1A7A7A !important; font-size:1.6rem;">Welcome, {user.get('name', 'User').split()[0]} 👋</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_logout:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key="logout_btn_landing"):
            do_logout()
            st.rerun()
    if st.session_state.current_user.get("role") == "ADM":
        st.markdown("---")
        if st.button("🔧 Admin Portal", use_container_width=True, key="goto_admin"):
            go_to("admin_portal")
    current_user_id = st.session_state.current_user.get("id")
    pending_reviews = get_pending_reviews_for_user(current_user_id)
    pending_leader = get_pending_leader_approvals(current_user_id)
    if pending_reviews or pending_leader:
        st.markdown("---")
        st.markdown("### 📋 Pending Actions")
        if pending_reviews:
            col_alert1, col_alert2 = st.columns([4, 1])
            with col_alert1:
                st.warning(f"🔴 **{len(pending_reviews)} Critical Incident{'' if len(pending_reviews) == 1 else 's'} Pending Your Review**")
            with col_alert2:
                if st.button("Review Now", key="goto_review", use_container_width=True):
                    go_to("review_critical")
        if pending_leader:
            col_alert3, col_alert4 = st.columns([4, 1])
            with col_alert3:
                st.warning(f"🟡 **{len(pending_leader)} Critical Incident{'' if len(pending_leader) == 1 else 's'} Awaiting Leader Approval**")
            with col_alert4:
                if st.button("Approve Now", key="goto_leader_approve", use_container_width=True):
                    go_to("leader_approve_critical")

    st.markdown("---")

    # ── PATCH 1: Whole-of-site totals (incidents + critical_incidents) ────────
    _all_incidents  = st.session_state.incidents
    _all_critical   = st.session_state.critical_incidents
    _total_q        = len(_all_incidents)
    _total_c        = len(_all_critical)
    _total_combined = _total_q + _total_c
    _active_students = len([s for s in st.session_state.students if not s.get("archived", False)])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Students", _active_students)
    with col2:
        st.metric("Total Incidents", _total_combined,
                  help="Quick/regular incidents + critical incident ABCH forms")
    with col3:
        st.metric("Critical Incidents", _total_c,
                  help="Completed ABCH critical incident forms")
    with col4:
        _escalation = f"{int(_total_c/_total_combined*100)}%" if _total_combined else "—"
        st.metric("Escalation Rate", _escalation,
                  help="% of all incidents that are critical")

    # ── Per-program breakdown ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Program Overview")
    prog_col1, prog_col2, prog_col3 = st.columns(3)
    for _prog, _pcol, _color in [
        ("JP", prog_col1, "#1A7A7A"),
        ("PY", prog_col2, "#D97706"),
        ("SY", prog_col3, "#2E4057"),
    ]:
        _prog_students  = [s for s in st.session_state.students
                           if s.get("program") == _prog and not s.get("archived", False)]
        _prog_stu_ids   = {s["id"] for s in _prog_students}
        _prog_incidents = [i for i in _all_incidents if i.get("student_id") in _prog_stu_ids]
        _prog_critical  = [c for c in _all_critical  if c.get("student_id") in _prog_stu_ids]
        _prog_total     = len(_prog_incidents) + len(_prog_critical)
        with _pcol:
            st.markdown(
                f"<div style='border-left:4px solid {_color};padding:.4rem .75rem;"
                f"background:#f8fafc;border-radius:0 6px 6px 0;margin-bottom:.4rem;'>"
                f"<div style='font-weight:700;color:{_color};font-size:.95rem;'>{_prog} — {PROGRAM_NAMES.get(_prog, _prog)}</div>"
                f"<div style='font-size:.82rem;color:#475569;'>👥 {len(_prog_students)} students</div>"
                f"<div style='font-size:.82rem;color:#475569;'>📋 {_prog_total} incidents total</div>"
                f"<div style='font-size:.82rem;color:#ef4444;'>🚨 {len(_prog_critical)} critical</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("### Select Program")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Junior Primary**")
        if st.button("Enter JP", use_container_width=True, type="primary", key="btn_jp"):
            go_to("program_students", selected_program="JP")
    with col2:
        st.markdown("**Primary Years**")
        if st.button("Enter PY", use_container_width=True, type="primary", key="btn_py"):
            go_to("program_students", selected_program="PY")
    with col3:
        st.markdown("**Senior Years**")
        if st.button("Enter SY", use_container_width=True, type="primary", key="btn_sy"):
            go_to("program_students", selected_program="SY")


def render_program_students_page():
    program = st.session_state.get("selected_program", "JP")
    st.markdown(f"## {PROGRAM_NAMES.get(program)} — Students")
    col1, col2 = st.columns([6, 1])
    with col1:
        if st.button("⬅ Back to Landing", key="back_students"):
            go_to("landing")
    students = [s for s in st.session_state.students if s["program"] == program and not s.get("archived", False)]
    for stu in students:
        stu_incidents = [i for i in st.session_state.incidents if i["student_id"] == stu["id"]]
        stu_critical = [c for c in st.session_state.critical_incidents if c["student_id"] == stu["id"]]
        stu_total = len(stu_incidents) + len(stu_critical)
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.markdown(f"**{stu['name']}**")
                st.caption(f"Grade {stu['grade']}")
            with col2:
                st.metric("Incidents", stu_total)
            with col3:
                if st.button("📊 Dashboard", key=f"dash_{stu['id']}", use_container_width=True):
                    go_to("student_dashboard", selected_student_id=stu["id"])
                if st.button("📝 Log", key=f"log_{stu['id']}", use_container_width=True):
                    go_to("incident_log", selected_student_id=stu["id"])
                if st.button("📈 Analysis", key=f"ana_{stu['id']}", use_container_width=True):
                    go_to("student_analysis", selected_student_id=stu["id"])
                if st.button("📋 Plan", key=f"plan_{stu['id']}", use_container_width=True):
                    go_to("support_plan", selected_student_id=stu["id"])
                if st.session_state.get("is_admin") or (st.session_state.get("current_user") or {}).get("role") == "ADM":
                    if st.button("📦 Archive", key=f"archive_prog_{stu['id']}", use_container_width=True):
                        stu['archived'] = True
                        if supabase:
                            try:
                                supabase.table('students').update({'archived': True}).eq('id', stu['id']).execute()
                            except Exception as e:
                                st.error(f"Archive failed: {e}")
                        st.rerun()


def render_incident_log_page():
    student_id = st.session_state.get("selected_student_id")
    student = get_student(student_id)
    if not student:
        st.error("No student selected")
        return
    st.markdown(f"## 📝 Incident Log — {student['name']}")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_log_top"):
            # Clear prefill state when navigating away
            st.session_state.incident_prefill = None
            st.session_state.last_saved_incident = None
            go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("🏠 Program Landing", key="home_log"):
            st.session_state.incident_prefill = None
            st.session_state.last_saved_incident = None
            go_to("landing")
    with col3:
        if st.button("📋 Support Plan", key="sp_from_log"):
            go_to("support_plan", selected_student_id=student_id)
    show_severity_guide()
    if st.session_state.show_critical_prompt:
        inc_info = st.session_state.get("last_incident_info", {})
        if inc_info.get("severity", 0) >= 3:
            st.error(f"⚠️ **Severity {inc_info['severity']} Detected** - Critical Incident ABCH Form Required")
        else:
            st.error("⚠️ **Critical Incident Flagged** - Critical Incident ABCH Form Required")
        st.info("Please complete the Critical Incident ABCH form to document this event fully.")
        if st.button("📋 Complete Critical Form Now", type="primary", key="crit_now", use_container_width=True):
            st.session_state.show_critical_prompt = False
            go_to("critical_incident", current_incident_id=st.session_state.current_incident_id)
        st.markdown("---")
        st.stop()

    # ── "Log Another" success banner (shown above the form after a non-critical save) ──
    _last = st.session_state.get("last_saved_incident")
    if _last:
        _prev_time = _last.get("time","")[:5]
        _prev_beh  = _last.get("behaviour_type","")
        _prev_sev  = _last.get("severity", 1)
        st.markdown(
            f"<div style='background:#f0fdf4;border:1.5px solid #22c55e;border-radius:8px;"
            f"padding:.65rem 1rem;margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem;'>"
            f"<span style='font-size:1.1rem;'>✅</span>"
            f"<span style='font-size:.88rem;color:#166534;'>"
            f"<strong>Incident saved</strong> — {_prev_beh}, Severity {_prev_sev}, at {_prev_time}. "
            f"Use <strong>Log Another</strong> to repeat with the same details, or edit any field below."
            f"</span></div>",
            unsafe_allow_html=True
        )
        btn_col1, btn_col2 = st.columns([2, 1])
        with btn_col2:
            if st.button("🗑️ Clear prefill", key="clear_prefill_btn", use_container_width=True,
                         help="Reset all form fields to blank defaults"):
                st.session_state.incident_prefill = None
                st.session_state.last_saved_incident = None
                st.rerun()

    # ── Pre-populate defaults from prefill (set by "Log Another") ─────────────
    _pf = st.session_state.get("incident_prefill") or {}

    def _loc_idx():
        v = _pf.get("location", "")
        opts = [""] + LOCATIONS
        return opts.index(v) if v in opts else 0

    def _beh_idx():
        v = _pf.get("behaviour_type", "")
        opts = [""] + BEHAVIOUR_TYPES
        return opts.index(v) if v in opts else 0

    def _ant_idx():
        v = _pf.get("antecedent", "")
        opts = [""] + ANTECEDENTS
        return opts.index(v) if v in opts else 0

    def _int_defaults():
        stored = _pf.get("intervention", [])
        return [i for i in (stored if isinstance(stored, list) else []) if i in INTERVENTIONS]

    # ── Form ──────────────────────────────────────────────────────────────────
    # Label changes to show "Repeat Log" mode when prefill is active
    _form_label = "📋 Repeat Incident (editing pre-filled details)" if _pf else "📋 New Incident"
    if _pf:
        st.markdown(
            "<div style='background:#fef9c3;border:1px solid #fde68a;border-radius:6px;"
            "padding:.4rem .8rem;margin-bottom:.4rem;font-size:.82rem;color:#92400e;'>"
            "🔁 <strong>Pre-filled from previous incident.</strong> "
            "Adjust the time and any other details that have changed, then submit.</div>",
            unsafe_allow_html=True
        )

    with st.form("incident_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            inc_date = st.date_input("Date *", value=date.today(), key="inc_date")
            inc_time = st.time_input(
                "Time * ← update this",
                value=datetime.now().time(),
                key="inc_time",
                help="Time defaults to now — adjust if the incident was earlier"
            )
            location = st.selectbox("Location *", [""] + LOCATIONS, index=_loc_idx(), key="inc_loc")
        with col2:
            behaviour = st.selectbox("Behaviour Type *", [""] + BEHAVIOUR_TYPES, index=_beh_idx(), key="inc_beh")
            antecedent = st.selectbox("Antecedent/Trigger *", [""] + ANTECEDENTS, index=_ant_idx(), key="inc_ant")
            interventions = st.multiselect("Interventions Used *", INTERVENTIONS, default=_int_defaults(), key="inc_ints")
        duration = st.number_input("Duration (minutes) *", min_value=1,
                                   value=int(_pf.get("duration_minutes", 1)), key="inc_dur")
        severity = st.slider("Severity Level *", 1, 5,
                             value=int(_pf.get("severity", 1)), key="inc_sev")
        description = st.text_area("Brief Description (Optional)",
                                   value="",
                                   placeholder="Factual, objective description...", key="inc_desc")
        manual_critical = st.checkbox(
            "This incident requires a Critical Incident ABCH Form (regardless of severity)", key="manual_crit"
        )
        _submit_label = "🔁 Submit Repeat Incident" if _pf else "Submit Incident"
        submitted = st.form_submit_button(_submit_label, type="primary", use_container_width=True)

    # ── Submit handler ────────────────────────────────────────────────────────
    if submitted:
        if not location or not behaviour or not antecedent or not interventions:
            st.error("Please complete all required fields marked with *")
        else:
            new_id = str(uuid.uuid4())
            is_critical = (severity >= 3) or manual_critical
            hyp_ai = generate_hypothesis_ai(antecedent, behaviour, "")
            rec = {
                "id": new_id, "student_id": student_id, "student_name": student["name"],
                "date": inc_date.isoformat(), "time": inc_time.strftime("%H:%M:%S"),
                "day": inc_date.strftime("%A"), "session": get_session_from_time(inc_time),
                "location": location, "behaviour_type": behaviour, "antecedent": antecedent,
                "intervention": interventions, "severity": severity,
                "reported_by": st.session_state.current_user.get("id", "unknown"),
                "duration_minutes": duration, "description": description or "", "is_critical": is_critical,
                "hypothesis_function": hyp_ai['function'], "hypothesis_item": hyp_ai['item']
            }
            if save_incident_to_db(rec):
                st.session_state.incidents.append(rec)
                if is_critical:
                    # Critical path — clear prefill state, go to ABCH form
                    st.session_state.incident_prefill    = None
                    st.session_state.last_saved_incident = None
                    st.session_state.current_incident_id = new_id
                    st.session_state.show_critical_prompt = True
                    st.session_state.last_incident_info  = {"severity": severity, "manual": manual_critical}
                    st.rerun()
                else:
                    # Non-critical — store for "Log Another" banner and offer repeat
                    st.session_state.last_saved_incident = rec
                    # Pre-populate NEXT form with this incident's repeatable fields
                    st.session_state.incident_prefill = {
                        "location":         location,
                        "behaviour_type":   behaviour,
                        "antecedent":       antecedent,
                        "intervention":     interventions,
                        "duration_minutes": duration,
                        "severity":         severity,
                    }
                    st.rerun()
            else:
                st.error("❌ Failed to save incident to database. Please try again.")


def render_critical_incident_page():
    inc_id = st.session_state.get("current_incident_id")
    quick_inc = next((i for i in st.session_state.incidents if i["id"] == inc_id), None)
    if not quick_inc:
        st.error("No incident found")
        return
    student = get_student(quick_inc["student_id"])
    st.markdown(f"## 🚨 Critical Incident ABCH Form")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_crit_top"):
            go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("🏠 Program Landing", key="home_crit"):
            go_to("landing")
    st.markdown("### Incident Details (from Quick Log)")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"**Student:** {student['name']}")
            st.markdown(f"**Grade:** {student['grade']}")
        with col2:
            st.markdown(f"**Date:** {quick_inc['date']}")
            st.markdown(f"**Time:** {format_time_12hr(quick_inc['time'])}")
        with col3:
            st.markdown(f"**Location:** {quick_inc['location']}")
            st.markdown(f"**Session:** {quick_inc['session']}")
        with col4:
            st.markdown(f"**Severity:** {quick_inc['severity']}")
        st.markdown(f"**Hypothesis:** {quick_inc.get('hypothesis', 'N/A')}")
    st.markdown("---")
    st.markdown("### ABCH Chronology")
    st.caption("Document the sequence of events. Add continuation entries if incident was prolonged.")
    if "abch_rows" not in st.session_state:
        st.session_state.abch_rows = []
    st.markdown("#### Initial Incident")
    col_header = st.columns([2, 2, 2, 2, 2])
    with col_header[0]: st.markdown("**ANTECEDENT (Triggers)**")
    with col_header[2]: st.markdown("**BEHAVIOUR**")
    with col_header[4]: st.markdown("**CONSEQUENCES**")
    col_subheader = st.columns([1, 1, 1, 1, 2, 2])
    with col_subheader[0]: st.caption("Location")
    with col_subheader[1]: st.caption("Context (what was happening?)")
    with col_subheader[2]: st.caption("Time")
    with col_subheader[3]: st.caption("Observed Behaviour")
    with col_subheader[4]: st.caption("What happened after?")
    with col_subheader[5]: st.caption("HYPOTHESIS (Function)")
    col_inputs1 = st.columns([1, 1, 1, 1, 2, 2])
    with col_inputs1[0]:
        location_1 = st.text_input("", value=quick_inc['location'], key="loc_1", label_visibility="collapsed")
    with col_inputs1[1]:
        context_1 = st.text_area("", placeholder="What was going on before?", key="context_1", height=100, label_visibility="collapsed")
    with col_inputs1[2]:
        time_1 = st.text_input("", value=format_time_12hr(quick_inc['time']), key="time_1", label_visibility="collapsed")
    with col_inputs1[3]:
        behaviour_1 = st.text_area("", placeholder="What did student do?", key="behaviour_1", height=100, label_visibility="collapsed")
    with col_inputs1[4]:
        consequence_1 = st.text_area("", placeholder="Staff response? Student reaction?", key="consequence_1", height=100, label_visibility="collapsed")
    with col_inputs1[5]:
        if "hyp_1_generated" not in st.session_state:
            st.session_state.hyp_1_generated = False
        if not st.session_state.hyp_1_generated and context_1 and behaviour_1:
            auto_hyp = generate_hypothesis(context_1, behaviour_1, consequence_1)
            st.session_state.hyp_1_auto = auto_hyp
            st.session_state.hyp_1_generated = True
        hypothesis_1 = st.text_area("", value=st.session_state.get("hyp_1_auto", ""),
                                    placeholder="Auto-generated (editable)", key="hypothesis_1", height=100, label_visibility="collapsed")
    st.markdown("---")
    for idx, row in enumerate(st.session_state.abch_rows):
        st.markdown(f"#### Continuation Entry {idx + 1}")
        col_add = st.columns([1, 1, 1, 1, 2, 2])
        with col_add[0]: row["location"] = st.text_input("", key=f"loc_{idx+2}", label_visibility="collapsed")
        with col_add[1]: row["context"] = st.text_area("", key=f"context_{idx+2}", height=100, label_visibility="collapsed")
        with col_add[2]: row["time"] = st.text_input("", key=f"time_{idx+2}", label_visibility="collapsed")
        with col_add[3]: row["behaviour"] = st.text_area("", key=f"behaviour_{idx+2}", height=100, label_visibility="collapsed")
        with col_add[4]: row["consequence"] = st.text_area("", key=f"consequence_{idx+2}", height=100, label_visibility="collapsed")
        with col_add[5]:
            if row.get("context") and row.get("behaviour"):
                auto_hyp_add = generate_hypothesis(row["context"], row["behaviour"], row.get("consequence", ""))
                row["hypothesis"] = st.text_area("", value=auto_hyp_add, key=f"hypothesis_{idx+2}", height=100, label_visibility="collapsed")
            else:
                row["hypothesis"] = st.text_area("", key=f"hypothesis_{idx+2}", height=100, label_visibility="collapsed")
        st.markdown("---")

    def _save_ci_draft():
        draft_id = st.session_state.get("ci_draft_id") or str(uuid.uuid4())
        st.session_state.ci_draft_id = draft_id
        draft = {
            "id": draft_id, "created_at": datetime.now().isoformat(),
            "student_id": quick_inc["student_id"], "severity": quick_inc.get("severity", 5),
            "reported_by": st.session_state.current_user.get("id"),
            "primary_location": st.session_state.get("loc_1", ""),
            "primary_context": st.session_state.get("context_1", ""),
            "primary_time": st.session_state.get("time_1", ""),
            "primary_behaviour": st.session_state.get("behaviour_1", ""),
            "primary_consequence": st.session_state.get("consequence_1", ""),
            "additional_entries": st.session_state.abch_rows.copy(),
            "outcomes": [], "status": "draft", "audit_trail": "[]", "include_audit_in_report": False,
        }
        try:
            existing = supabase.table("critical_incidents").select("id").eq("id", draft_id).execute()
            if existing.data:
                supabase.table("critical_incidents").update(draft).eq("id", draft_id).execute()
            else:
                supabase.table("critical_incidents").insert(draft).execute()
            st.session_state.ci_last_saved = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.warning(f"⚠️ Draft save failed: {e}")

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        if st.button("➕ Add Continuation Entry", key="add_abch_row"):
            st.session_state.abch_rows.append({})
            _save_ci_draft()
            st.rerun()
    with btn_col2:
        if st.button("💾 Save Draft", key="save_draft_btn"):
            _save_ci_draft()
            st.rerun()
    if st.session_state.get("ci_last_saved"):
        st.caption(f"✅ Draft auto-saved at {st.session_state.ci_last_saved}")

    st.markdown("### Intended Outcomes")
    outcomes_options = [
        "Send Home", "Parent/Caregiver notified via Phone Call",
        "Student Leaving supervised areas/leaving school grounds",
        "Sexualised behaviour", "Incident – student to student",
        "Complaint by co-located school/member of public",
        "Property damage", "Stealing", "Toileting issue",
        "ED155: Staff Injury", "ED155: Student injury",
        "Emergency services - SAPOL", "Emergency services - SA Ambulance",
        "Incident Internally Managed - Restorative Session",
        "Incident Internally Managed - Community Service",
        "Incident Internally Managed - Re-Entry",
        "Incident Internally Managed - Case Review",
        "Incident Internally Managed - Make-up Time"
    ]
    selected_outcomes = st.multiselect("Select all intended outcomes:", outcomes_options, key="intended_outcomes")
    sapol_reference = ""
    if "Emergency services - SAPOL" in selected_outcomes:
        st.warning("⚠️ SAPOL involvement detected - Police Reference Number required")
        sapol_reference = st.text_input("SAPOL Police Reference Number *", placeholder="Enter police reference number", key="sapol_ref")
    tac_notes = st.text_area("Additional Outcome Notes:", placeholder="A TAC meeting will be held...", key="tac_notes", height=100)
    st.markdown("---")
    st.markdown("### Notifications & Administration")
    col_notif1, col_notif2 = st.columns(2)
    with col_notif1:
        notified_line_manager = st.checkbox("Notified Line Manager", key="notif_manager", value=True)
        notified_parent = st.checkbox("Notified Parent/Caregiver", key="notif_parent")
    with col_notif2:
        copy_in_file = st.checkbox("Copy in student file", key="copy_file", value=True)
        safety_plan_review = st.checkbox("Safety plan review required", key="safety_review")
    st.markdown("---")
    st.markdown("### Staff Agreement")
    staff_name = st.session_state.current_user.get("name", "Staff Member")
    st.markdown(f"**Completing Staff Member:** {staff_name}")
    staff_agrees = st.checkbox(f"✓ I, {staff_name}, confirm this information is accurate and complete.", key="staff_agrees")
    st.markdown("---")
    st.markdown("### Email Distribution")
    col_email1, col_email2 = st.columns(2)
    with col_email1:
        leader_email = st.text_input("Line Manager Email *", value="manager@clc.sa.edu.au", key="leader_email")
    with col_email2:
        admin_email = st.text_input("Admin Email *", value="admin@clc.sa.edu.au", key="admin_email")
    st.markdown("---")
    other_staff = [s for s in st.session_state.staff if s['id'] != st.session_state.current_user['id']]
    st.markdown("### Assign for Review")
    st.caption("Select another staff member to review this critical incident report")
    assigned_staff_id = st.selectbox(
        "Assign to staff member *",
        options=[s['id'] for s in other_staff],
        format_func=lambda x: next((s['name'] for s in other_staff if s['id'] == x), "Unknown"),
        key="assigned_review_staff"
    )
    st.markdown("---")
    if st.button("📧 Complete & Assign for Review", type="primary", use_container_width=True, key="save_crit"):
        errors = []
        if not context_1 or not behaviour_1 or not consequence_1 or not hypothesis_1:
            errors.append("Please complete all ABCH fields for initial incident")
        if not staff_agrees:
            errors.append("Please confirm your agreement")
        if not assigned_staff_id:
            errors.append("Please assign a staff member for review")
        if "Emergency services - SAPOL" in selected_outcomes and not sapol_reference:
            errors.append("SAPOL Reference Number is required when SAPOL is involved")
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            current_user_id = st.session_state.current_user['id']
            current_user_name = st.session_state.current_user['name']
            record_id = st.session_state.get("ci_draft_id") or str(uuid.uuid4())
            record = {
                "id": record_id, "created_at": datetime.now().isoformat(),
                "quick_incident_id": inc_id, "student_id": quick_inc["student_id"],
                "student_name": student["name"], "incident_type": "Critical",
                "severity": quick_inc.get('severity', 5),
                "ABCH_primary": {
                    "location": location_1, "context": context_1, "time": time_1,
                    "behaviour": behaviour_1, "consequence": consequence_1, "hypothesis": hypothesis_1
                },
                "ABCH_additional": st.session_state.abch_rows.copy(),
                "intended_outcomes": selected_outcomes,
                "sapol_reference": sapol_reference if sapol_reference else None,
                "tac_notes": tac_notes,
                "notifications": {"line_manager": notified_line_manager, "parent": notified_parent,
                                  "copy_in_file": copy_in_file, "safety_plan_review": safety_plan_review},
                "staff_agreement": {"staff_name": staff_name, "agreed": staff_agrees, "timestamp": datetime.now().isoformat()},
                "leader_email": leader_email, "admin_email": "clc.admin281@schools.sa.edu.au",
                "status": "pending_review", "completed_by_id": current_user_id,
                "completed_by_name": current_user_name, "assigned_to_id": assigned_staff_id,
                "assigned_to_name": next((s['name'] for s in other_staff if s['id'] == assigned_staff_id), "Unknown"),
                "completed_at": datetime.now().isoformat(), "audit_trail": [], "include_audit_in_report": False
            }
            record = add_audit_trail_entry(record, "ABCH Form Completed", current_user_name,
                                           f"Assigned to {record['assigned_to_name']} for review")
            if save_critical_incident_to_db(record):
                for _key in ["critical_incidents", "incidents"]:
                    if _key in st.session_state:
                        del st.session_state[_key]
                st.session_state.abch_rows = []
                st.session_state.hyp_1_generated = False
                st.session_state.ci_draft_id = None
                st.session_state.ci_last_saved = None
                st.success("✅ Critical incident form completed and assigned for review")
                st.info(f"📤 Assigned to **{record['assigned_to_name']}** for review")
                admin_summary = generate_admin_summary(record, student, staff_name)
                with st.expander("📋 ADMIN SUMMARY (For External Incident Log)", expanded=False):
                    st.text_area("Copy this summary for departmental log:", admin_summary, height=400, key="admin_summary_display")
                    st.download_button("📥 Download Admin Summary", admin_summary,
                        file_name=f"Admin_Summary_{student['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt", mime="text/plain")
                assigned_staff = next((s for s in st.session_state.staff if s['id'] == assigned_staff_id), None)
                if assigned_staff:
                    email_sent = send_assignment_notification(assigned_staff, current_user_name, student['name'], record['id'])
                    if email_sent:
                        st.success(f"📧 Email notification sent to {record['assigned_to_name']}")
                if sapol_reference:
                    st.info(f"🚔 SAPOL Reference: {sapol_reference}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📊 View Analysis", type="primary", use_container_width=True, key="view_analysis"):
                        go_to("student_analysis", selected_student_id=quick_inc["student_id"])
                with col2:
                    if st.button("↩️ Back to Students", use_container_width=True, key="back_crit_after"):
                        go_to("program_students", selected_program=student["program"])
                with col3:
                    if st.button("🏠 Program Landing", use_container_width=True, key="home_crit_after"):
                        go_to("landing")
            else:
                st.error("❌ Failed to save critical incident to database")


def render_review_critical_page():
    current_user_id = st.session_state.current_user.get("id")
    current_user_name = st.session_state.current_user.get("name")
    pending = get_pending_reviews_for_user(current_user_id)
    st.markdown("## 📋 Critical Incidents Pending Your Review")
    if st.button("⬅ Back to Landing", key="back_review"):
        go_to("landing")
    if not pending:
        st.info("✅ No critical incidents pending your review")
        return
    st.markdown("---")
    st.markdown(f"### You have {len(pending)} critical incident{'' if len(pending) == 1 else 's'} to review")
    if len(pending) > 1:
        incident_options = {str(inc.get('id')): f"{inc.get('student_name', 'Unknown')} - {inc.get('created_at', 'No date')}"
                           for inc in pending}
        selected_id = st.selectbox("Select incident to review:", list(incident_options.keys()),
                                   format_func=lambda x: incident_options[x])
        critical = next((inc for inc in pending if str(inc.get('id')) == selected_id), None)
    else:
        critical = pending[0]
    if not critical:
        st.error("Critical incident not found"); return
    student = get_student(critical['student_id'])
    if not student:
        st.error("Student not found"); return
    st.markdown("---")
    st.markdown(f"### Critical Incident - {student['name']}")
    primary = critical.get('ABCH_primary', {})
    with st.container(border=True):
        st.markdown("**Incident Overview**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Student:** {student['name']}")
            st.markdown(f"**Grade:** {student['grade']}")
        with col2:
            st.markdown(f"**Date:** {critical.get('created_at', 'N/A')[:10]}")
            st.markdown(f"**Severity:** {critical.get('severity', 'N/A')}")
        with col3:
            st.markdown(f"**Completed by:** {critical.get('completed_by_name', 'N/A')}")
            st.markdown(f"**Status:** {critical.get('status', 'draft').replace('_', ' ').title()}")
    st.markdown("---")
    with st.expander("📍 ANTECEDENT", expanded=True):
        st.markdown(f"**Location:** {primary.get('location', 'N/A')}")
        st.markdown(f"**Time:** {primary.get('time', 'N/A')}")
        st.markdown(f"**Context:** {primary.get('context', 'N/A')}")
    with st.expander("🎯 BEHAVIOUR", expanded=True):
        st.markdown(primary.get('behaviour', 'N/A'))
    with st.expander("📊 CONSEQUENCE", expanded=True):
        st.markdown(primary.get('consequence', 'N/A'))
    with st.expander("💡 HYPOTHESIS", expanded=True):
        st.markdown(primary.get('hypothesis', 'N/A'))
    additional = critical.get('ABCH_additional', [])
    if additional:
        st.markdown("---")
        for idx, entry in enumerate(additional):
            with st.expander(f"Continuation Entry {idx + 1}"):
                st.markdown(f"**Location:** {entry.get('location', 'N/A')}")
                st.markdown(f"**Time:** {entry.get('time', 'N/A')}")
                st.markdown(f"**Context:** {entry.get('context', 'N/A')}")
                st.markdown(f"**Behaviour:** {entry.get('behaviour', 'N/A')}")
                st.markdown(f"**Consequence:** {entry.get('consequence', 'N/A')}")
                st.markdown(f"**Hypothesis:** {entry.get('hypothesis', 'N/A')}")
    st.markdown("---")
    outcomes = critical.get('intended_outcomes', [])
    if outcomes:
        st.markdown("**Intended Outcomes**")
        for outcome in outcomes:
            st.markdown(f"- {outcome}")
    if critical.get('sapol_reference'):
        st.warning(f"🚔 **SAPOL Reference:** {critical['sapol_reference']}")
    st.markdown("---")
    st.markdown("### Your Review")
    review_notes = st.text_area("Review Notes (Optional)", placeholder="Add any observations or additional context...", height=150, key="review_notes_input")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve & Forward to Leader", type="primary", use_container_width=True, key="approve_review"):
            manager_id = get_manager_staff_id()
            if not manager_id:
                st.error("❌ No Leader/Manager found. Please contact admin.")
            else:
                critical['status'] = 'pending_leader'
                critical['reviewed_by_id'] = current_user_id
                critical['reviewed_by_name'] = current_user_name
                critical['review_notes'] = review_notes
                critical['reviewed_at'] = datetime.now().isoformat()
                critical['assigned_to_id'] = manager_id
                critical = add_audit_trail_entry(critical, "Reviewed by Staff Member", current_user_name,
                                                 review_notes if review_notes else "No additional notes")
                if save_critical_incident_to_db(critical):
                    for idx, inc in enumerate(st.session_state.critical_incidents):
                        if inc.get('id') == critical['id']:
                            st.session_state.critical_incidents[idx] = critical
                            break
                    leader_staff = next((s for s in st.session_state.staff if s['id'] == manager_id), None)
                    if leader_staff:
                        send_leader_notification(leader_staff, current_user_name, student['name'], critical['id'])
                    st.success("✅ Review completed and forwarded to Leader for approval")
                    st.balloons()
                    go_to("landing")
                else:
                    st.error("❌ Failed to save review")
    with col2:
        if st.button("🔙 Back to Landing", use_container_width=True, key="back_review_later"):
            go_to("landing")


def render_leader_approve_critical_page():
    current_user_id = st.session_state.current_user.get("id")
    current_user_name = st.session_state.current_user.get("name")
    pending = get_pending_leader_approvals(current_user_id)
    st.markdown("## 🎯 Critical Incidents Awaiting Leader Approval")
    if st.button("⬅ Back to Landing", key="back_leader"):
        go_to("landing")
    if not pending:
        st.info("✅ No critical incidents awaiting your approval")
        return
    st.markdown("---")
    if len(pending) > 1:
        incident_options = {str(inc.get('id')): f"{inc.get('student_name', 'Unknown')} - {inc.get('created_at', 'No date')}"
                           for inc in pending}
        selected_id = st.selectbox("Select incident to approve:", list(incident_options.keys()),
                                   format_func=lambda x: incident_options[x])
        critical = next((inc for inc in pending if str(inc.get('id')) == selected_id), None)
    else:
        critical = pending[0]
    if not critical:
        st.error("Critical incident not found"); return
    student = get_student(critical['student_id'])
    if not student:
        st.error("Student not found"); return
    st.markdown(f"### Critical Incident - {student['name']}")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown(f"✅ **Completed by:** {critical.get('completed_by_name', 'N/A')}")
        with col2: st.markdown(f"✅ **Reviewed by:** {critical.get('reviewed_by_name', 'N/A')}")
        with col3: st.markdown(f"⏳ **Awaiting:** Leader Approval")
    if critical.get('review_notes'):
        with st.expander("📝 Review Notes from Staff", expanded=True):
            st.info(critical['review_notes'])
    primary = critical.get('ABCH_primary', {})
    with st.expander("📋 View Complete ABCH Form"):
        st.markdown(f"**Severity:** {critical.get('severity', 'N/A')}")
        st.markdown(f"**Location:** {primary.get('location', 'N/A')}")
        st.markdown(f"**Behaviour:** {primary.get('behaviour', 'N/A')}")
        st.markdown(f"**Hypothesis:** {primary.get('hypothesis', 'N/A')}")
        for outcome in critical.get('intended_outcomes', []):
            st.markdown(f"- {outcome}")
        if critical.get('sapol_reference'):
            st.warning(f"🚔 **SAPOL Reference:** {critical['sapol_reference']}")
    st.markdown("---")
    leader_notes = st.text_area("Leader Notes / Amendments", placeholder="Add any corrections or amendments...", height=150, key="leader_notes_input")
    include_audit = st.checkbox("Include full audit trail in final report", value=False, key="include_audit_toggle")
    st.markdown("---")
    if st.button("✅ Final Approval & Submit Report", type="primary", use_container_width=True, key="final_approve"):
        critical['status'] = 'completed'
        critical['leader_approved_by_id'] = current_user_id
        critical['leader_approved_by_name'] = current_user_name
        critical['leader_notes'] = leader_notes
        critical['leader_approved_at'] = datetime.now().isoformat()
        critical['submitted_at'] = datetime.now().isoformat()
        critical['include_audit_in_report'] = include_audit
        critical['assigned_to_id'] = None
        critical = add_audit_trail_entry(critical, "Approved by Leader", current_user_name,
                                         leader_notes if leader_notes else "Final approval granted")
        if save_critical_incident_to_db(critical):
            for idx, inc in enumerate(st.session_state.critical_incidents):
                if inc.get('id') == critical['id']:
                    st.session_state.critical_incidents[idx] = critical
                    break
            st.success("✅ Critical incident approved and submitted")
            completed_by_staff = next((s for s in st.session_state.staff if s['id'] == critical.get('completed_by_id')), None)
            reviewed_by_staff = next((s for s in st.session_state.staff if s['id'] == critical.get('reviewed_by_id')), None)
            leader_staff = next((s for s in st.session_state.staff if s['id'] == current_user_id), None)
            emails_sent = send_completion_notifications(critical, student,
                completed_by_staff or {}, reviewed_by_staff or {}, leader_staff or {})
            if emails_sent:
                st.success(f"📧 Emails sent to: {', '.join(emails_sent)}")
            else:
                st.info("📧 Email notifications not configured")
            st.balloons()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 View Student Analysis", use_container_width=True, key="goto_analysis"):
                    go_to("student_analysis", selected_student_id=critical['student_id'])
            with col2:
                if st.button("🏠 Return to Landing", use_container_width=True, key="back_landing"):
                    go_to("landing")
        else:
            st.error("❌ Failed to save approval to database")


def _parse_dates(series):
    """Robust date parsing for mixed formats (e.g. '2026-09-10', '2026-09-10T09:15:00',
    '...+00:00', with/without microseconds). pandas otherwise infers ONE format from the
    first row and silently turns every row in a different format into NaT, which made
    valid incidents disappear from the analysis."""
    try:
        out = pd.to_datetime(series, utc=True, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        out = pd.to_datetime(series, utc=True, errors="coerce")
    return out.dt.tz_localize(None)


def render_demand_avoidance_section(full_df):
    sig = demand_avoidance_signal(full_df)
    if sig["flag"]:
        st.info(f"{sig['n']} of {sig['total']} incidents ({sig['pct']*100:.0f}%) were linked to demands, "
                "instructions, transitions or refusal/avoidance. That pattern fits a demand-avoidant "
                "presentation. This is a prompt for team discussion, not a diagnosis, and the approach "
                "below helps whether or not a diagnosis (e.g. ODD or PDA profile) exists.")
    else:
        st.caption("Not strongly indicated by this student's data, but these approaches are useful for any "
                   "student who reacts to being told what to do.")
    with st.expander("Demand-avoidant presentations — low-demand, perceived-choice approach", expanded=sig["flag"]):
        st.markdown("**Core idea:** for these students, direct demands can feel like a loss of control, which "
                    "triggers the threat response. Lower the demand, share control, and let the student say yes "
                    "on their own terms. This is Regulate-before-Reason in practice.")
        for item in DEMAND_AVOIDANCE_STRATEGIES:
            st.markdown(f"- **{item['domain']}:** {item['strategy']}")
        st.markdown("**Perceived choice: reframing the language**")
        st.caption("Both options must be acceptable to you. The choice is in the how, when, where or with whom, not whether.")
        for _instead, _try in PERCEIVED_CHOICE_PHRASES:
            st.markdown(f"- Instead of *\"{_instead}\"* try *\"{_try}\"*")



# ============================================
# SCREEN CAPTURE -> PRINTABLE HTML
# ============================================
# The Analysis page is built from Streamlit calls (markdown, charts, metrics,
# info boxes...). While it renders, these thin wrappers record each call, in
# order, in addition to drawing it. The recording is then turned into a single
# print-ready page (A4, charts included, "Understanding this chart" notes and
# all) so the printed version is literally what is on screen. Interactive
# controls (buttons, forms, inputs) are not recorded.
import html as _html_mod

_SCREEN = {"on": False, "paused": False, "rec": []}


def _scr_add(kind, *payload):
    if _SCREEN["on"] and not _SCREEN["paused"]:
        _SCREEN["rec"].append((kind, *payload))


def screen_capture_start():
    _SCREEN.update(on=True, paused=False, rec=[])
    _orig = {n: getattr(st, n) for n in ("markdown", "caption", "write", "info", "warning", "success", "error",
                                         "metric", "plotly_chart", "dataframe", "table", "code", "subheader",
                                         "header", "divider", "expander")}
    _SCREEN["orig"] = _orig

    def _mk(name, fn):
        def wrapper(*a, **k):
            try:
                fn(*a, **k)
            except Exception:
                pass
            return _orig[name](*a, **k)
        return wrapper

    def _markdown(body="", *a, **k):
        t = str(body)
        if "<style" in t or "<script" in t:
            return
        if t.lstrip().startswith("### 👁️ View, Edit"):
            _SCREEN["paused"] = True
        _scr_add("md", t, bool(k.get("unsafe_allow_html", False)))

    st.markdown = _mk("markdown", _markdown)
    st.caption = _mk("caption", lambda body="", *a, **k: _scr_add("caption", str(body)))
    st.write = _mk("write", lambda *a, **k: [_scr_add("md", x, False) for x in a if isinstance(x, str)])
    for _n in ("info", "warning", "success", "error"):
        st.__dict__[_n] = _mk(_n, (lambda nn: (lambda body="", *a, **k: _scr_add("alert", nn, str(body))))(_n))
    st.metric = _mk("metric", lambda label="", value="", delta=None, *a, **k: _scr_add("metric", str(label), str(value), None if delta is None else str(delta)))
    st.plotly_chart = _mk("plotly_chart", lambda fig=None, *a, **k: _scr_add("fig", fig))
    st.dataframe = _mk("dataframe", lambda data=None, *a, **k: _scr_add("df", data))
    st.table = _mk("table", lambda data=None, *a, **k: _scr_add("df", data))
    st.code = _mk("code", lambda body="", *a, **k: _scr_add("code", str(body)))
    st.subheader = _mk("subheader", lambda body="", *a, **k: _scr_add("md", f"### {body}", False))
    st.header = _mk("header", lambda body="", *a, **k: _scr_add("md", f"## {body}", False))
    st.divider = _mk("divider", lambda *a, **k: _scr_add("md", "---", False))
    st.expander = _mk("expander", lambda label="", *a, **k: _scr_add("md", f"#### {label}", False))


def screen_capture_stop():
    _orig = _SCREEN.get("orig") or {}
    for n, f in _orig.items():
        try:
            if n in st.__dict__:
                del st.__dict__[n]
            setattr(st, n, f)
        except Exception:
            pass
    _SCREEN["on"] = False


def _inline_md(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def _md_to_html(text: str, allow_html: bool) -> str:
    """Small markdown subset: headings, bullets, numbered lists, tables, rules, bold/italic/code."""
    if not allow_html:
        text = _html_mod.escape(text, quote=False)
    out, para, in_ul, in_ol, tbl = [], [], False, False, []

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + "<br>".join(_inline_md(x) for x in para) + "</p>")
            para = []

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False

    def flush_tbl():
        nonlocal tbl
        if tbl:
            rows = [r for r in tbl if not re.match(r"^\s*\|?\s*:?-{2,}", r)]
            html_rows = []
            for i, r in enumerate(rows):
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                tag = "th" if i == 0 else "td"
                html_rows.append("<tr>" + "".join(f"<{tag}>{_inline_md(c)}</{tag}>" for c in cells) + "</tr>")
            out.append("<table class='md'>" + "".join(html_rows) + "</table>")
            tbl = []

    for line in text.split("\n"):
        st_ = line.strip()
        if st_.startswith("|") and st_.endswith("|"):
            flush_para(); close_lists(); tbl.append(st_); continue
        flush_tbl()
        if not st_:
            flush_para(); close_lists(); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st_)
        if m:
            flush_para(); close_lists()
            lvl = max(len(m.group(1)), 2)
            out.append(f"<h{lvl}>{_inline_md(m.group(2))}</h{lvl}>"); continue
        if re.match(r"^-{3,}$|^\*{3,}$", st_):
            flush_para(); close_lists(); out.append("<hr>"); continue
        m = re.match(r"^[-*•]\s+(.*)$", st_)
        if m:
            flush_para()
            if in_ol: out.append("</ol>"); in_ol = False
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline_md(m.group(1))}</li>"); continue
        m = re.match(r"^\d+[.)]\s+(.*)$", st_)
        if m:
            flush_para()
            if in_ul: out.append("</ul>"); in_ul = False
            if not in_ol: out.append("<ol>"); in_ol = True
            out.append(f"<li>{_inline_md(m.group(1))}</li>"); continue
        if st_.startswith("<") and allow_html:
            flush_para(); close_lists(); out.append(line); continue
        close_lists(); para.append(st_)
    flush_para(); close_lists(); flush_tbl()
    return "\n".join(out)


def build_print_html(student, full_df, records, supports_trialled="", supports_success="",
                     before_after=None, trials=None, bsem_items=None) -> bytes:
    """Assemble the recorded screen into one printable HTML document."""
    import plotly.graph_objects as _go
    from plotly.offline import get_plotlyjs
    esc = lambda v: _html_mod.escape(_tr_text(v, "—"))
    body, metrics = [], []

    def flush_metrics():
        if metrics:
            body.append("<div class='metrics'>" + "".join(
                f"<div class='metric'><div class='ml'>{_html_mod.escape(l)}</div><div class='mv'>{_html_mod.escape(v)}</div>"
                + (f"<div class='md_'>{_html_mod.escape(d)}</div>" if d else "") + "</div>" for l, v, d in metrics) + "</div>")
            metrics.clear()

    fig_n = 0
    for rec in records:
        kind = rec[0]
        if kind == "metric":
            metrics.append((rec[1], rec[2], rec[3])); continue
        flush_metrics()
        if kind == "md":
            body.append(f"<div class='blk'>{_md_to_html(rec[1], rec[2])}</div>")
        elif kind == "caption":
            body.append(f"<p class='cap'>{_inline_md(_html_mod.escape(rec[1], quote=False))}</p>")
        elif kind == "alert":
            body.append(f"<div class='alert {rec[1]}'>{_md_to_html(rec[2], False)}</div>")
        elif kind == "code":
            body.append(f"<pre>{_html_mod.escape(rec[1])}</pre>")
        elif kind == "df":
            try:
                d = rec[1]
                d = d.data if hasattr(d, "data") and hasattr(d, "to_html") else d
                body.append("<div class='tbl'>" + pd.DataFrame(d).to_html(index=False, border=0, classes="data", na_rep="—") + "</div>")
            except Exception:
                pass
        elif kind == "fig":
            try:
                f = _go.Figure(rec[1])
                f.update_layout(template="plotly_white", paper_bgcolor="white", width=None, autosize=True)
                fig_n += 1
                body.append("<div class='fig'>" + f.to_html(full_html=False, include_plotlyjs=False,
                            config={"displayModeBar": False, "responsive": True}, div_id=f"fig{fig_n}") + "</div>")
            except Exception:
                pass
        elif kind == "bsem":
            for it in rec[1]:
                why = _tr_text(it.get("why")); how = _tr_text(it.get("how"))
                body.append(f"<div class='card'><b>{esc(it.get('domain'))}</b> — {esc(it.get('strategy'))}"
                            + (f"<p><b>Why it fits:</b> {esc(why)}</p>" if why and not why.startswith("[DEBUG]") else "")
                            + (f"<p><b>How to put it in place:</b> {esc(how)}</p>" if how and not how.startswith("[DEBUG]") else "")
                            + "</div>")
        elif kind == "wot":
            for z in WOT_ZONES:
                zd = rec[1].get(z["id"])
                if not zd:
                    continue
                cols = "".join(f"<td><b>{h}</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in (items or ["— none logged —"])) + "</ul></td>"
                               for h, items in (("Context", zd["context"]), ("Behaviour", zd["behaviour"]), ("Interventions", zd["interventions"])))
                body.append(f"<table class='wot' style='border-color:{z['color']}'><tr><th colspan='3' style='background:{z['color']}'>"
                            f"{esc(z['label'])} — {zd['n']} incident(s)</th></tr><tr>{cols}</tr></table>")
    flush_metrics()

    # ── appended: supports trialled, register, meeting notes ──
    if (supports_trialled or "").strip() or (supports_success or "").strip():
        body.append("<h3 class='pb'>Supports Trialled</h3><table class='md'><tr><th>Supports / strategies trialled</th><th>How successful?</th></tr>"
                    f"<tr><td>{esc(supports_trialled)}</td><td>{esc(supports_success)}</td></tr></table>")
        if before_after and not before_after.get("insufficient"):
            b = before_after
            chg = "" if b.get("pct_rate_change") is None else (
                f" ({abs(b['pct_rate_change']):.0f}% {'fewer' if b['pct_rate_change'] < 0 else 'more'} incidents per week since the trial date)")
            body.append(f"<p>Before ({b['weeks_before']:.1f} wks): {b['rate_before']:.1f}/week. After ({b['weeks_after']:.1f} wks): "
                        f"{b['rate_after']:.1f}/week{chg}. Preliminary read.</p>")
    rows = []
    for _, r in full_df.sort_values("date_parsed").iterrows():
        desc = _tr_text(r.get("description"))
        if not desc and isinstance(r.get("ABCH_primary"), dict):
            desc = _tr_text(r["ABCH_primary"].get("behaviour"))
        sev = pd.to_numeric(r.get("severity"), errors="coerce")
        iv = r.get("intervention")
        iv = ", ".join(str(x) for x in iv if x) if isinstance(iv, (list, tuple)) else _tr_text(iv)
        rows.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in [
            r["date_parsed"].strftime("%d/%m/%y"), _tr_text(r.get("time"))[:5], "C" if r.get("incident_type") == "Critical" else "Q",
            _tr_text(r.get("location")), _tr_text(r.get("behaviour_type")), _tr_text(r.get("antecedent")),
            "—" if pd.isna(sev) else int(sev), iv or "—", desc or "—"]) + "</tr>")
    body.append(f"<h3 class='pb'>Incident Register — all {len(full_df)} dated incidents</h3><p class='cap'>Oldest first. Q = Quick log, C = Critical (ABCH).</p>"
                "<table class='data reg'><tr><th>Date</th><th>Time</th><th>Type</th><th>Location</th><th>Behaviour</th><th>Antecedent</th><th>Sev</th>"
                "<th>Interventions</th><th>Notes</th></tr>" + "".join(rows) + "</table>")
    body.append("<h3 class='pb'>Meeting Notes & Agreed Actions</h3><div class='lines'>Date of meeting: ____________   Present: ______________________________</div>"
                "<div class='notes'>Notes</div><table class='data act'><tr><th>Agreed action</th><th>Who</th><th>By when</th></tr>"
                + "<tr><td></td><td></td><td></td></tr>" * 6 + "</table>")

    dp = full_df["date_parsed"]
    cover = (f"<div class='cover'><h1>Full Analysis — {_html_mod.escape(student['name'])}</h1>"
             f"<p>Cowandilla Learning Centre · LBU {_html_mod.escape(str(student.get('program','')))} Program · printed {datetime.now().strftime('%d %B %Y')}<br>"
             f"Data period {dp.min().strftime('%d/%m/%Y')} – {dp.max().strftime('%d/%m/%Y')} · {len(full_df)} dated incidents</p></div>")
    css = """
    @page { size: A4; margin: 14mm 13mm 16mm; @bottom-center { content: "CONFIDENTIAL — Page " counter(page); font: 8pt Arial; color:#666 } }
    * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { font: 10.5pt/1.45 Arial, Helvetica, sans-serif; color:#1f2937; margin:0 auto; max-width:190mm; padding:10px; }
    .bar { position: sticky; top:0; background:#134e4a; color:#fff; padding:8px 12px; margin-bottom:12px; border-radius:6px; display:flex; justify-content:space-between; align-items:center; }
    .bar button { background:#fff; color:#134e4a; border:0; padding:6px 14px; border-radius:6px; font-weight:700; cursor:pointer; }
    .cover { background:#1A7A6E; color:#fff; padding:14px 18px; border-radius:8px; margin-bottom:10px; } .cover h1 { margin:0 0 4px; font-size:20pt; } .cover p { margin:0; color:#fef3c7; }
    h2 { font-size:15pt; color:#134e4a; margin:14px 0 4px; break-after: avoid; } h3 { background:#2E4057; color:#fff; padding:5px 9px; border-radius:4px; font-size:12pt; margin:16px 0 6px; break-after: avoid; }
    h4 { font-size:11pt; color:#2E4057; margin:10px 0 3px; break-after: avoid; border-bottom:1px solid #cbd5e1; } h5,h6 { margin:8px 0 2px; break-after: avoid; }
    p { margin:4px 0; orphans:3; widows:3; } .cap { color:#475569; font-style:italic; font-size:9.5pt; }
    .blk, .fig, .card, .alert, table, pre, .metrics, .lines, .notes { break-inside: avoid; } .pb { break-before: page; }
    .blk > div { break-inside: avoid; }
    .fig { margin:6px 0; border:1px solid #e2e8f0; border-radius:6px; padding:4px; overflow:hidden; } .fig .plotly-graph-div { width:100% !important; }
    .alert { border-left:4px solid #3b82f6; background:#eff6ff; padding:6px 10px; margin:6px 0; border-radius:4px; } .alert.warning { border-color:#f59e0b; background:#fffbeb; }
    .alert.success { border-color:#10b981; background:#ecfdf5; } .alert.error { border-color:#ef4444; background:#fef2f2; }
    .metrics { display:flex; flex-wrap:wrap; gap:8px; margin:6px 0; } .metric { flex:1 1 90px; border:1px solid #cbd5e1; border-radius:6px; padding:6px 8px; background:#f8fafc; }
    .ml { font-size:8.5pt; color:#64748b; } .mv { font-size:15pt; font-weight:700; } .md_ { font-size:8.5pt; color:#047857; }
    .card { border:1px solid #cbd5e1; border-left:4px solid #1A7A6E; padding:6px 10px; margin:6px 0; border-radius:4px; background:#fafafa; }
    pre { background:#f1f5f9; padding:6px 8px; border-radius:4px; white-space:pre-wrap; font-size:9.5pt; }
    table { width:100%; border-collapse:collapse; margin:6px 0; font-size:9.5pt; } th, td { border:1px solid #cbd5e1; padding:4px 6px; vertical-align:top; text-align:left; }
    th { background:#2E4057; color:#fff; } tr:nth-child(even) td { background:#f8fafc; } table.wot { border:2px solid; margin:8px 0; } table.wot td { background:#fff !important; } table.wot ul { margin:2px 0; padding-left:16px; }
    table.reg { font-size:8pt; } table.reg th, table.reg td { padding:3px 4px; } thead { display: table-header-group; } tr { break-inside: avoid; }
    .lines { margin:10px 0; } .notes { border:1px solid #94a3b8; min-height:90mm; padding:6px; margin:8px 0; font-weight:700; } .act td { height:14mm; } ul { margin:3px 0; padding-left:20px; }
    @media print { .bar { display:none; } body { padding:0; max-width:none; } }
    """
    js = ("""<script>
    function _rs(w){document.querySelectorAll('.js-plotly-plot').forEach(function(d){try{Plotly.relayout(d,{width:w})}catch(e){}})}
    window.addEventListener('beforeprint',function(){_rs(690)});
    window.addEventListener('afterprint',function(){document.querySelectorAll('.js-plotly-plot').forEach(function(d){try{Plotly.relayout(d,{autosize:true,width:null});Plotly.Plots.resize(d)}catch(e){}})});
    </script>""")
    doc = ("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>Full Analysis — {_html_mod.escape(student['name'])}</title><style>{css}</style>"
           f"<script>{get_plotlyjs()}</script></head><body>"
           "<div class='bar'><span>Print-ready analysis. Press Print, then choose your printer or Save as PDF.</span>"
           "<button onclick='window.print()'>🖨️ Print</button></div>"
           + cover + "\n".join(body) + js + "</body></html>")
    return doc.encode("utf-8")


def render_student_analysis_page():
    """Draws the Analysis page, recording what is shown so a printable copy can be built."""
    screen_capture_start()
    try:
        _render_student_analysis_page_inner()
    finally:
        screen_capture_stop()


def _render_student_analysis_page_inner():
    student_id = st.session_state.get("selected_student_id")
    student = get_student(student_id)
    if not student:
        st.error("No student selected"); return

    st.markdown(f"## 📊 Behaviour Summary — {student['name']}")
    st.caption("Evidence-based analysis prepared by Learning and Behaviour Unit")

    if student.get('placement_start'):
        try:
            start_dt = datetime.fromisoformat(student['placement_start'])
            has_end = bool(student.get('placement_end'))
            end_dt = datetime.fromisoformat(student['placement_end']) if has_end else None
            # Extensions push the true end date later — use the latest of the
            # original end date and any extension's "to" date.
            _exts_for_metrics = load_placement_extensions_from_db(student_id)
            _extended = False
            if _exts_for_metrics:
                try:
                    _latest_ext = max(datetime.fromisoformat(e["to"]) for e in _exts_for_metrics if e.get("to"))
                    if not end_dt or _latest_ext > end_dt:
                        end_dt = _latest_ext
                        has_end = True
                        _extended = True
                except Exception:
                    pass
            today = datetime.utcnow()
            # Days enrolled so far — today, capped at the placement end date
            # once it's passed (so this doesn't keep climbing after the
            # placement has actually finished).
            _reference_end = min(today, end_dt) if end_dt else today
            days_enrolled = max((_reference_end.date() - start_dt.date()).days, 0)

            st.markdown("---")
            pcol1, pcol2, pcol3 = st.columns(3)
            with pcol1: st.metric("Placement Start", start_dt.strftime('%d/%m/%Y'))
            with pcol2:
                if has_end:
                    st.metric("Extended End" if _extended else "Placement End", end_dt.strftime('%d/%m/%Y'))
                else:
                    st.metric("Status", "Ongoing")
            with pcol3: st.metric("Days Enrolled", days_enrolled)

            if has_end:
                total_placement_days = max((end_dt.date() - start_dt.date()).days, 0)
                days_remaining = max((end_dt.date() - today.date()).days, 0)
                pcol4, pcol5 = st.columns(2)
                with pcol4:
                    st.metric("Days Remaining", days_remaining)
                with pcol5:
                    st.metric("Total Placement (days)", total_placement_days)
            st.markdown("---")
        except: pass

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_analysis_top"):
            if student.get("archived", False):
                go_to("admin_portal")
            else:
                go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("🏠 Program Landing", key="home_analysis"):
            go_to("landing")
    with col3:
        if st.button("📋 Support Plan", key="sp_from_analysis"):
            go_to("support_plan", selected_student_id=student_id)

    # ── Attendance: weekly schedule + exceptions (legacy fields derived for older code) ──
    _att_state = attendance_state(student_id)
    _abs_key = f"absent_dates_{student_id}"
    _abs_stored = sorted({e["date"] for e in _att_state["exceptions"] if e.get("type") == "Absent"})
    st.session_state[_abs_key] = _abs_stored
    _att_cur = attendance_current_days(_att_state)
    _pt_days = [ATT_DAYS_FULL[i] for i, dn in enumerate(ATT_DAYS) if _att_cur.get(dn)]
    _pt_sessions = ["Full day"] if all(set(_att_cur.get(dn, [])) == set(ATT_SESSIONS) for dn in ATT_DAYS) else ["See weekly schedule"]
    _pt_notes = _att_state.get("notes", "")

    # ══ Placement Timeline ═══════════════════════════════════════════════════
    with st.expander("📌 Placement Timeline & Extensions", expanded=False):
        st.caption(
            "Record and view this student's placement start date, agreed end date, and any extensions. "
            "Placement timeline provides important context for incident pattern analysis — "
            "incidents in the first weeks of placement may reflect adjustment, "
            "while incidents near the end of an agreed period may reflect transition anxiety."
        )
        _pl_start_raw = student.get("placement_start")
        _pl_end_raw   = student.get("placement_end")
        _pl_exts      = load_placement_extensions_from_db(student_id)

        _pl_c1, _pl_c2, _pl_c3 = st.columns(3)
        with _pl_c1:
            st.metric("Placement Start",
                      datetime.fromisoformat(_pl_start_raw).strftime("%-d %b %Y") if _pl_start_raw else "Not set")
        with _pl_c2:
            st.metric("Original End Date",
                      datetime.fromisoformat(_pl_end_raw).strftime("%-d %b %Y") if _pl_end_raw else "Ongoing")
        with _pl_c3:
            if _pl_exts:
                try:
                    _last_ext = max(datetime.fromisoformat(e["to"]) for e in _pl_exts)
                    st.metric("Extended Until", _last_ext.strftime("%-d %b %Y"))
                except: st.metric("Extensions", f"{len(_pl_exts)} recorded")
            elif _pl_start_raw:
                import datetime as _pdt
                _days_en = (_pdt.date.today() - datetime.fromisoformat(_pl_start_raw).date()).days
                st.metric("Days enrolled", _days_en)

        if _pl_exts:
            st.markdown("**Extensions:**")
            for _ex in _pl_exts:
                try:
                    _ef = datetime.fromisoformat(_ex["from"]).strftime("%-d %b %Y")
                    _et = datetime.fromisoformat(_ex["to"]).strftime("%-d %b %Y")
                    st.markdown(
                        f"<div style='background:#eff6ff;border-left:3px solid #3b82f6;"
                        f"border-radius:5px;padding:.4rem .75rem;margin:.2rem 0;font-size:.83rem;'>"
                        f"📌 <b>{_ef} – {_et}</b> — {_ex['reason']}</div>",
                        unsafe_allow_html=True
                    )
                except: pass

        st.markdown("---")
        with st.expander("✏️ Edit placement dates or add extension", expanded=False):
            _pfc1, _pfc2 = st.columns(2)
            with _pfc1:
                _new_pl_start = st.date_input(
                    "Placement start *",
                    value=datetime.fromisoformat(_pl_start_raw).date() if _pl_start_raw else date.today(),
                    key=f"an_pl_start_{student_id}"
                )
            with _pfc2:
                _new_pl_end = st.date_input(
                    "Original end date (blank = ongoing)",
                    value=datetime.fromisoformat(_pl_end_raw).date() if _pl_end_raw else None,
                    key=f"an_pl_end_{student_id}"
                )
            if st.button("💾 Save placement dates", key=f"an_pl_save_{student_id}", use_container_width=True):
                student["placement_start"] = _new_pl_start.isoformat()
                student["placement_end"]   = _new_pl_end.isoformat() if _new_pl_end else None
                if save_student_to_db(student):
                    if "students" in st.session_state: del st.session_state["students"]
                    st.success("✅ Placement dates saved.")
                    st.rerun()

            st.markdown("**Add extension:**")
            _exc1, _exc2, _exc3 = st.columns([2, 2, 3])
            with _exc1:
                _an_ef = st.date_input("From *", value=None, key=f"an_ext_f_{student_id}")
            with _exc2:
                _an_et = st.date_input("To *",   value=None, key=f"an_ext_t_{student_id}")
            with _exc3:
                _an_er = st.text_input(
                    "Reason / context *",
                    placeholder="e.g. Extended — transition support, positive progress",
                    key=f"an_ext_r_{student_id}"
                )
            if st.button("➕ Add extension", key=f"an_ext_add_{student_id}", use_container_width=True):
                if _an_ef and _an_et and _an_er.strip():
                    if save_placement_extension_to_db(student_id, _an_ef.isoformat(), _an_et.isoformat(), _an_er.strip()):
                        st.success(f"✅ Extension added: {_an_ef.strftime('%-d %b')} – {_an_et.strftime('%-d %b %Y')}")
                        st.rerun()
                else:
                    st.error("Please complete all three fields.")

        st.session_state[f"pl_start_an_{student_id}"] = _pl_start_raw
        st.session_state[f"pl_end_an_{student_id}"]   = _pl_end_raw


    render_starting_profile(student)

    # ══ Sensory Overview Upload ════════════════════════════════════════════════
    with st.expander("🧠 Sensory Overview — upload to enrich analysis (optional)", expanded=False):
        st.caption(
            "Upload a completed Sensory Overview or Sensory Profile document "
            "(e.g. OT assessment, sensory checklist, or sensory processing summary). "
            "The AI will extract key themes and cross-reference them with the behaviour "
            "and trigger data already identified for this student. "
            "Accepts .docx, .pdf, or paste text directly."
        )

        _so_key  = f"sensory_overview_{student_id}"
        _so_data = st.session_state.get(_so_key, {})

        _so_tab1, _so_tab2 = st.tabs(["📄 Upload File (.docx / .pdf)", "📋 Paste Text"])

        with _so_tab1:
            _so_file = st.file_uploader(
                "Upload Sensory Overview",
                type=["docx", "pdf", "odt"],
                key=f"so_upload_{student_id}"
            )
            if _so_file:
                if st.button("🤖 Extract Sensory Information", type="primary",
                             key=f"so_extract_file_{student_id}", use_container_width=True):
                    with st.spinner("Reading document..."):
                        try:
                            _fname = _so_file.name.lower()
                            if _fname.endswith(".pdf"):
                                try:
                                    import fitz
                                    _raw  = _so_file.read()
                                    _pdoc = fitz.open(stream=_raw, filetype="pdf")
                                    _so_text = " ".join(page.get_text() for page in _pdoc)
                                    _pdoc.close()
                                except Exception:
                                    _so_text = "[PDF extraction failed — use the Paste Text tab instead]"
                            elif _fname.endswith(".odt"):
                                import zipfile, xml.etree.ElementTree as _ET
                                _zf      = zipfile.ZipFile(_so_file)
                                _content = _ET.fromstring(_zf.read("content.xml"))
                                _so_text = " ".join(_content.itertext())
                            else:
                                from docx import Document as _DocxDoc
                                _d      = _DocxDoc(_so_file)
                                _paras  = [p.text for p in _d.paragraphs if p.text.strip()]
                                _cells  = [c.text for t in _d.tables
                                           for r in t.rows for c in r.cells if c.text.strip()]
                                _so_text = " ".join(_paras + _cells)
                            st.session_state[f"so_raw_{student_id}"] = _so_text
                            st.success(f"✅ Extracted {len(_so_text):,} characters from {_so_file.name}")
                        except Exception as _e:
                            st.error(f"Extraction error: {_e}")

        with _so_tab2:
            _so_pasted = st.text_area(
                "Paste sensory overview content here",
                height=200,
                placeholder="Paste the full text of the sensory overview or OT report here...",
                key=f"so_paste_{student_id}"
            )
            if st.button("✅ Use this text", key=f"so_use_paste_{student_id}", use_container_width=True):
                if _so_pasted.strip():
                    st.session_state[f"so_raw_{student_id}"] = _so_pasted.strip()
                    st.success("Text saved — click 'Run AI Extraction' below.")
                else:
                    st.warning("Please paste some content first.")

        # Run AI extraction when raw text is available
        _so_raw = st.session_state.get(f"so_raw_{student_id}", "")
        if _so_raw:
            st.markdown(
                f"<div style='background:#f0fdf4;border-left:3px solid #22c55e;border-radius:6px;"
                f"padding:.4rem .75rem;font-size:.82rem;margin:.3rem 0;'>"
                f"✅ {len(_so_raw):,} characters of sensory overview text ready for extraction.</div>",
                unsafe_allow_html=True
            )
            if not _so_data:
                if st.button("🤖 Run AI Extraction", type="primary",
                             key=f"so_run_ai_{student_id}", use_container_width=True):
                    GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
                    if GROQ_KEY:
                        with st.spinner("AI extracting sensory themes — this takes a few seconds..."):
                            try:
                                import json as _sjs
                                _so_prompt = (
                                    "You are an occupational therapist and behaviour support specialist. "
                                    f"Extract a structured sensory profile from this document for student: {student['name']}. "
                                    "Return ONLY valid JSON — no markdown, no preamble. "
                                    'Use this exact structure: '
                                    '{"sensory_seeking":["list of sensory-seeking needs"],'
                                    '"sensory_avoiding":["list of sensory sensitivities"],'
                                    '"regulation_strategies":["effective strategies noted"],'
                                    '"triggers":["sensory triggers that precede behaviour"],'
                                    '"recommendations":["classroom recommendations"],'
                                    '"summary":"2-3 sentence clinical summary"}'
                                    f" Document: {_so_raw[:4000]}"
                                )
                                _so_json = groq_ai_call(_so_prompt, max_tokens=1500, temperature=0.1)
                                _so_json = _so_json.replace("```json", "").replace("```", "").strip()
                                _so_parsed = _sjs.loads(_so_json)
                                st.session_state[_so_key] = _so_parsed
                                _so_data = _so_parsed
                                st.success("✅ Sensory overview processed.")
                                st.rerun()
                            except Exception as _se:
                                st.error(f"AI extraction failed: {_se}")
                    else:
                        st.error("Groq API key not configured — AI extraction unavailable.")

        # Re-read _so_data after possible update
        _so_data = st.session_state.get(_so_key, {})

        # Display extracted sensory profile
        if _so_data:
            st.markdown("---")
            st.markdown("#### 🧠 Sensory Profile — Extracted Themes")
            if _so_data.get("summary"):
                st.markdown(
                    f"<div style='background:#f0f9ff;border-left:4px solid #0284c7;"
                    f"border-radius:6px;padding:.75rem 1rem;font-size:.88rem;"
                    f"color:#0c4a6e;margin-bottom:.6rem;'>"
                    f"{_so_data['summary']}</div>",
                    unsafe_allow_html=True
                )
            _sc1, _sc2 = st.columns(2)
            with _sc1:
                if _so_data.get("sensory_seeking"):
                    st.markdown("**🔍 Sensory seeking / high need:**")
                    for item in _so_data["sensory_seeking"][:6]:
                        st.markdown(f"• {item}")
                if _so_data.get("triggers"):
                    st.markdown("**⚡ Sensory triggers:**")
                    for item in _so_data["triggers"][:6]:
                        st.markdown(f"• {item}")
            with _sc2:
                if _so_data.get("sensory_avoiding"):
                    st.markdown("**🛡️ Sensory sensitivities:**")
                    for item in _so_data["sensory_avoiding"][:6]:
                        st.markdown(f"• {item}")
                if _so_data.get("regulation_strategies"):
                    st.markdown("**✅ Effective regulation strategies:**")
                    for item in _so_data["regulation_strategies"][:6]:
                        st.markdown(f"• {item}")
            if _so_data.get("recommendations"):
                st.markdown("**📚 Classroom recommendations:**")
                for item in _so_data["recommendations"][:8]:
                    st.markdown(f"• {item}")

            # Cross-reference with incident trigger data
            if "full_df" in dir() and not full_df.empty:
                st.markdown("---")
                st.markdown("#### 🔗 Sensory–Behaviour Cross-Reference")
                _sens_kw = ["noise","sound","crowd","touch","bright","light","texture",
                            "smell","movement","propriocep","vestibular","tactile",
                            "auditory","visual","sensory","hungry","food","thirsty"]
                _ant_lower = full_df["antecedent"].dropna().str.lower()
                _sens_mask = _ant_lower.apply(lambda a: any(kw in a for kw in _sens_kw))
                _n_sens = int(_sens_mask.sum())
                if _n_sens > 0:
                    _pct_sens = int(_n_sens / len(full_df) * 100)
                    st.markdown(
                        f"<div style='background:#fefce8;border-left:3px solid #eab308;"
                        f"border-radius:6px;padding:.55rem .85rem;font-size:.84rem;margin:.3rem 0;'>"
                        f"<b>{_pct_sens}% of incidents ({_n_sens}/{len(full_df)})</b> were preceded by "
                        f"antecedents with a sensory dimension. "
                        "This aligns with the uploaded sensory profile and supports prioritising "
                        "sensory regulation strategies as antecedent interventions.</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.caption(
                        "No direct sensory antecedent overlap detected in current incident logs. "
                        "Consider whether sensory factors are being captured consistently "
                        "when logging antecedents."
                    )

            if st.button("🗑️ Clear sensory overview", key=f"so_clear_{student_id}"):
                for _k in [_so_key, f"so_raw_{student_id}"]:
                    if _k in st.session_state:
                        del st.session_state[_k]
                st.rerun()

    with st.expander("⏱️ Attendance — weekly schedule & day-to-day changes (saved automatically)", expanded=False):
        render_attendance_tracking(student_id)

    # ── Active attendance summary (always visible below expander) ─────────
    _has_sched = bool(_att_state["schedule"])
    _n_early = sum(1 for e in _att_state["exceptions"] if e.get("type") == "Finished early")
    if _has_sched or _att_state["exceptions"]:
        _att_html = (
            "<div style='background:#eff6ff;border-left:4px solid #3b82f6;border-radius:8px;"
            "padding:.65rem 1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;'>"
            "<b>⏱️ Attendance context active</b><br>"
        )
        if _has_sched:
            _att_html += ("<b>This week's pattern:</b> " + " · ".join(f"{dn} {_att_sess_text(_att_cur.get(dn, []))}" for dn in ATT_DAYS)
                          + ". Zero-incident days may reflect days not attended.<br>")
        if _abs_stored:
            _att_html += f"<b>Absent days recorded: {len(_abs_stored)}</b>, marked on the frequency chart below.<br>"
        if _n_early:
            _att_html += f"<b>Days finished early: {_n_early}</b>, shown in the Attendance Context section below.<br>"
        if _pt_notes:
            _att_html += f"<i>Note: {_pt_notes}</i>"
        _att_html += "</div>"
        st.markdown(_att_html, unsafe_allow_html=True)

    quick = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    crit = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]

    if not quick and not crit:
        st.info("No incident data available yet. Suggestions from the Starting Profile can still be trialled from day one.")
        render_strategy_trials(student, pd.DataFrame())
        if st.button("↩️ Back", key="back_no_data"):
            go_to("program_students", selected_program=student["program"])
        return

    quick_df = pd.DataFrame(quick) if quick else pd.DataFrame()
    crit_df = pd.DataFrame(crit) if crit else pd.DataFrame()

    if not quick_df.empty:
        quick_df["incident_type"] = "Quick"
        quick_df["date_parsed"] = _parse_dates(quick_df["date"])
        if "location" in quick_df.columns:
            quick_df["location"] = quick_df["location"].apply(normalise_location)
        if "intervention" in quick_df.columns:
            quick_df["intervention_str"] = quick_df["intervention"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))

    if not crit_df.empty:
        crit_df["incident_type"] = "Critical"
        _crit_dates_a = crit_df["created_at"] if "created_at" in crit_df.columns else pd.Series(
            [datetime.now().isoformat()] * len(crit_df), index=crit_df.index
        )
        crit_df["date_parsed"] = _parse_dates(_crit_dates_a)
        crit_df["severity"] = crit_df["severity"].fillna(5).astype(int) if "severity" in crit_df.columns else 5
        crit_df["antecedent"] = crit_df["ABCH_primary"].apply(lambda d: d.get("context","") if isinstance(d, dict) else "")
        # Keyword map: ABCH free-text → canonical clinical behaviour label
        _CRIT_BEH_KEYWORDS = [
            # (keyword list, canonical label) — checked in order; first match wins
            (["self-harm","self harm","hurt himself","hurt herself","scratch","bite himself",
              "bite herself","bang head","banged head","hit himself","hit herself"],
             "Self-injurious behaviour"),
            (["threw","throw","thrown","hurled","launched","flung","pushed chair",
              "knocked over","flipped","tipped","toppled","pushed desk","flipped table",
              "knocked chair"],
             "Throwing objects"),
            (["destroyed","broke","smashed","kicked wall","punched wall","ripped","torn",
              "property damage","damaged"],
             "Property destruction"),
            (["hit peer","hit a peer","hit student","punch peer","punched peer",
              "kicked peer","kicked a student","shoved peer","pushed peer","bit peer",
              "grabbed peer","scratched peer","attacked peer","spat at peer"],
             "Physical aggression toward peer"),
            (["hit staff","hit teacher","hit adult","punch staff","punched teacher",
              "kicked staff","kicked teacher","kicked adult","shoved staff","pushed staff",
              "bit staff","grabbed staff","scratched staff","spat at staff","spat at teacher",
              "hit the teacher","struck","swung at"],
             "Physical aggression toward adult"),
            (["growl","growled","snarl","snarled","scream at","screamed at","yell at",
              "yelled at","swore at","sworn at","sworn towards","sworn toward",
              "verbal abuse","verbally abused","name call","called names","insulted",
              "threatened","said he would","said she would","told them he would",
              "told them she would"],
             "Verbal aggression toward peer"),
            (["swore at teacher","swore at staff","swore at adult","yelled at teacher",
              "yelled at staff","yelled at adult","screamed at teacher","screamed at staff",
              "verbal abuse toward staff","abused staff","abused teacher","abused adult",
              "threatened staff","threatened teacher","threatened adult"],
             "Verbal aggression toward adult"),
            (["ran from","ran out","left the room","left class","left the class",
              "walked out","walked away","fled","ran away","elopement","eloped",
              "absconded","left the building","left the school","left school grounds"],
             "Unsanctioned departure (elopement)"),
            (["refus","refused","refusing","won't","will not","not going to",
              "declined to","passive","non-complian","non complian","wouldn't"],
             "Task refusal / passive non-compliance"),
            (["shut down","shutdown","withdrew","withdrawal","stopped responding",
              "stopped talking","silent","mute","unresponsive","disengaged",
              "curled up","head down","under desk"],
             "Shutdown / complete withdrawal"),
            (["noise","noises","sound","sounds","humming","clicking","tapping",
              "inappropriate sound","disruptive sound","loud noise"],
             "Inappropriate vocalisation / noises"),
            (["verbal refus","said no","said 'no'","stated he would not",
              "stated she would not","verbally refus"],
             "Verbal refusal of instruction"),
        ]

        def _clean_crit_beh(d):
            """Map ABCH free-text behaviour to a canonical clinical label."""
            raw = d.get("behaviour","") if isinstance(d, dict) else ""
            if not raw or not raw.strip():
                return "Behaviour (see ABCH form)"
            raw_lower = raw.lower()
            # 1. Direct match against known BEHAVIOUR_TYPES
            for known in BEHAVIOUR_TYPES:
                if not known.startswith("---") and known.lower() == raw_lower.strip():
                    return known
            # 2. Keyword map — first match wins
            for keywords, label in _CRIT_BEH_KEYWORDS:
                if any(kw in raw_lower for kw in keywords):
                    return label
            # 3. Partial known-type match
            for known in BEHAVIOUR_TYPES:
                if not known.startswith("---") and known.lower() in raw_lower:
                    return known
            # 4. Fallback — use truncated description tagged as narrative
            short = raw.strip()[:50].replace("\n"," ")
            return f"{short}…" if len(raw.strip()) > 50 else short
        crit_df["behaviour_type"] = crit_df["ABCH_primary"].apply(_clean_crit_beh)
        crit_df["time"] = crit_df["ABCH_primary"].apply(lambda d: d.get("time", "09:00:00") if isinstance(d, dict) else "09:00:00")
        for _col in ["location", "session"]:
            if _col not in crit_df.columns:
                crit_df[_col] = crit_df["ABCH_primary"].apply(lambda d: d.get(_col, "") if isinstance(d, dict) else "")
        if "location" in crit_df.columns:
            crit_df["location"] = crit_df["location"].apply(normalise_location)

    full_df = pd.concat([quick_df, crit_df], ignore_index=True).sort_values("date_parsed")
    # Drop any record with an unparseable/missing date — a handful of charts
    # below call .strftime() on date_parsed directly, which crashes on NaT
    # (pandas' null timestamp). A record with no valid date can't be
    # meaningfully plotted by date anyway.
    _dropped_nat = int(full_df["date_parsed"].isna().sum()) if "date_parsed" in full_df.columns else 0
    if _dropped_nat > 0:
        full_df = full_df.dropna(subset=["date_parsed"])
    if "time" not in full_df.columns:
        full_df["time"] = "09:00:00"
    else:
        full_df["time"] = full_df["time"].fillna("09:00:00")
    full_df["hour"] = pd.to_datetime(full_df["time"], format="%H:%M:%S", errors="coerce").dt.hour.fillna(9).astype(int)
    full_df["day_of_week"] = full_df["date_parsed"].dt.day_name()
    # Always recompute session using precise time boundaries
    def _session_precise(t_str):
        try:
            parts = str(t_str).split(":")
            tm = int(parts[0]) * 60 + int(parts[1])
            if tm < 11 * 60: return "Morning"
            elif tm <= 13 * 60 + 30: return "Middle"
            else: return "Afternoon"
        except:
            return "Morning"
    full_df["session"] = full_df["time"].apply(_session_precise)

    quick_only_df = full_df[full_df['incident_type'] == 'Quick'].copy() if 'Quick' in full_df['incident_type'].values else pd.DataFrame()
    crit_only_df = full_df[full_df['incident_type'] == 'Critical'].copy() if 'Critical' in full_df['incident_type'].values else pd.DataFrame()

    _view_mode = st.radio(
        "View", ["🔎 Snapshot", "📄 Full Analysis"], horizontal=True, index=1,
        key=f"analysis_view_mode_{student_id}",
    )
    if _view_mode == "🔎 Snapshot":
        render_analysis_snapshot(student, full_df, student_id)
        return

    st.markdown("### 📈 Executive Summary")
    if _dropped_nat > 0:
        _raw_total = len(full_df) + _dropped_nat
        st.warning(
            f"⚠️ **This student has {_raw_total} incident(s) on file in total, but {_dropped_nat} "
            f"have no valid date recorded**, so they're excluded from every chart and metric below "
            f"(all of it is organised by date). That's why this page may show a lower number than "
            f"other screens — it's not a missing/deleted record, it's a missing date. "
            f"To fix: scroll down to **👁️ View, Edit & Print an Incident** on this page. Undated "
            f"records are flagged **⚠️ NO DATE**. Pick one, set the correct date, and press "
            f"**Save Changes** to bring it into this analysis (or use **🗑️ Delete an Incident** "
            f"if it's a duplicate)."
        )
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total (dated)" if _dropped_nat > 0 else "Total", len(full_df))
    with col2: st.metric("Critical", len(full_df[full_df["incident_type"] == "Critical"]))
    with col3: st.metric("Avg Severity", f"{full_df['severity'].mean():.1f}")
    with col4:
        days = max((full_df["date_parsed"].max() - full_df["date_parsed"].min()).days, 1)
        st.metric("Days Span", days)
    with col5: st.metric("Per Day", f"{len(full_df) / days:.1f}")
    st.markdown("---")

    st.markdown("### 📅 Daily Incident Frequency")
    st.caption("All school days in the data period are shown. Zero bars = no incidents that day. Non-incident days are important context.")

    # Build a combined daily frame with string labels so Plotly uses category axis
    # (avoids date interpolation that would show weekend gaps / empty days)
    _all_daily = pd.concat([
        quick_only_df.assign(_type="Regular") if not quick_only_df.empty else pd.DataFrame(),
        crit_only_df.assign(_type="Critical") if not crit_only_df.empty else pd.DataFrame(),
    ], ignore_index=True)
    if not _all_daily.empty:
        _all_daily = _all_daily.dropna(subset=["date_parsed"])

    fig1 = go.Figure()
    if not _all_daily.empty:
        _all_daily["_date"] = _all_daily["date_parsed"].dt.date
        # Day label: "Mon 03 Mar" — unambiguous, no year clutter
        _all_daily["_label"] = _all_daily["date_parsed"].apply(
            lambda d: d.strftime("%a %-d %b")
        )
        # Span ALL calendar days (not just incident days) so zero-incident days show
        import datetime as _dt
        _first_date = _all_daily["_date"].min()
        _last_date  = _all_daily["_date"].max()
        _all_days   = []
        _d = _first_date
        while _d <= _last_date:
            _all_days.append(_d)
            _d += _dt.timedelta(days=1)
        _date_label_map = {d: d.strftime("%a %-d %b") for d in _all_days}
        label_order = [_date_label_map[d] for d in _all_days]
        _all_daily["_label"] = _all_daily["_date"].map(_date_label_map)
        _day_regular = (
            _all_daily[_all_daily["_type"] == "Regular"]
            .groupby("_label").size().reindex(label_order, fill_value=0)
        ) if "Regular" in _all_daily["_type"].values else pd.Series(0, index=label_order)
        _day_critical = (
            _all_daily[_all_daily["_type"] == "Critical"]
            .groupby("_label").size().reindex(label_order, fill_value=0)
        ) if "Critical" in _all_daily["_type"].values else pd.Series(0, index=label_order)

        # Weekend shading: flag labels that are Sat/Sun
        _is_weekend = {_date_label_map[d]: d.weekday() >= 5 for d in _all_days}

        fig1.add_trace(go.Bar(
            x=label_order, y=list(_day_regular),
            name="Regular",
            marker=dict(color=[
                "#94a3b8" if _is_weekend.get(l) else "#3b82f6" for l in label_order
            ], line=dict(color="white", width=1)),
            text=[str(v) if v else "" for v in _day_regular],
            textposition="inside",
            textfont=dict(color="white", size=11, family="Arial Black"),
            hovertemplate="<b>%{x}</b><br>Regular: %{y}<extra></extra>"
        ))
        fig1.add_trace(go.Bar(
            x=label_order, y=list(_day_critical),
            name="Critical",
            marker=dict(color=[
                "#cbd5e1" if _is_weekend.get(l) else "#ef4444" for l in label_order
            ], line=dict(color="white", width=1)),
            text=[str(v) if v else "" for v in _day_critical],
            textposition="inside",
            textfont=dict(color="white", size=11, family="Arial Black"),
            hovertemplate="<b>%{x}</b><br>Critical: %{y}<extra></extra>"
        ))

        # Annotate any weekend bars so it's obvious
        for lbl in label_order:
            if _is_weekend.get(lbl):
                fig1.add_annotation(
                    x=lbl, y=0, text="weekend", showarrow=False,
                    yanchor="bottom", font=dict(size=8, color="#94a3b8"),
                    yshift=4
                )

    # Overlay day-end markers (planned early finishes) on the daily chart
    try:
        _de_state = attendance_state(student_id)
        for _de in [e for e in _de_state["exceptions"] if e.get("type") == "Finished early"]:
            _de_lbl = date.fromisoformat(_de["date"]).strftime("%a %-d %b")
            if _de_lbl in label_order:
                fig1.add_annotation(x=_de_lbl, y=0.6, text="day end", showarrow=False, yanchor="bottom",
                                    font=dict(size=9, color="#b45309"), bgcolor="#fef3c7")
    except Exception:
        pass

    # Overlay absent day markers on the chart
    _absent_dates_chart = st.session_state.get(f"absent_dates_{student_id}", [])
    if _absent_dates_chart and not _all_daily.empty:
        import datetime as _acdt
        for _abs_d in _absent_dates_chart:
            try:
                _abs_date_obj = _acdt.date.fromisoformat(_abs_d)
                _abs_lbl = _abs_date_obj.strftime("%a %-d %b")
                if _abs_lbl in label_order:
                    fig1.add_annotation(
                        x=_abs_lbl, y=0.3,
                        text="absent",
                        showarrow=False,
                        font=dict(size=9, color="#94a3b8"),
                        textangle=-90,
                        yanchor="bottom",
                    )
                    fig1.add_vline(
                        x=label_order.index(_abs_lbl),
                        line_dash="dot", line_color="#cbd5e1",
                        line_width=1.5, opacity=0.7
                    )
            except Exception:
                pass

    fig1.update_layout(
        height=380, barmode="stack",
        xaxis_title="<b>Date (school days only)</b>", yaxis_title="<b>Incident Count</b>",
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        font=dict(color="#0f172a", size=12, family="Arial"),
        yaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                   showline=True, linewidth=2, linecolor="#cbd5e1"),
        xaxis=dict(
            type="category",
            tickangle=-40 if len(label_order) > 10 else -25,
            tickfont=dict(size=10 if len(label_order) > 15 else 11, color="#334155"),
            showline=True, linewidth=2, linecolor="#cbd5e1",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.25,
        margin=dict(b=60),
    )
    st.plotly_chart(fig1, use_container_width=True)
    # ── Daily frequency insight ───────────────────────────────────────────
    if not full_df.empty:
        _fi_start_d = full_df["date_parsed"].min().date()
        _fi_end_d   = full_df["date_parsed"].max().date()
        _fi_total_days = sum(
            1 for _n in range((_fi_end_d - _fi_start_d).days + 1)
            if (_fi_start_d + timedelta(days=_n)).weekday() < 5
        )  # school days only — weekends excluded
        _fi_incident_days = full_df["date_parsed"].dt.date.nunique()
        _fi_day_counts  = full_df.groupby(full_df["date_parsed"].dt.date).size()
        _fi_max_day     = int(_fi_day_counts.max())
        _fi_avg_per_day = len(full_df) / max(_fi_incident_days, 1)
        _fi_high_days   = int((_fi_day_counts >= 3).sum())
        # Identify any consecutive runs of 2+ incident days
        _fi_dates_sorted = sorted(_fi_day_counts.index)
        _fi_consec = 0
        if len(_fi_dates_sorted) >= 2:
            for _dx in range(1, len(_fi_dates_sorted)):
                if (_fi_dates_sorted[_dx] - _fi_dates_sorted[_dx-1]).days == 1:
                    _fi_consec += 1
        _fi_insight = (
            f"<b>{_fi_incident_days} of {_fi_total_days} school days</b> had at least one incident, "
            f"averaging <b>{_fi_avg_per_day:.1f} per active day</b> (highest single day: {_fi_max_day}). "
        )
        if _fi_high_days >= 1:
            _fi_insight += (
                f"<b>{_fi_high_days} spike day(s)</b> had 3 or more incidents — worth reviewing what was "
                "different about staffing, timetable, or demands that day. "
            )
        if _fi_consec >= 2:
            _fi_insight += (
                f"<b>{_fi_consec} instance(s) of consecutive high-incident days</b> — may point to "
                "insufficient recovery time between events, or a sustained stressor (transition, "
                "staffing change, curriculum demand) across multiple days."
            )
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
            f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
            f"<b>📊 Understanding this chart:</b><br>{_fi_insight}</div>",
            unsafe_allow_html=True
        )
    render_attendance_context(student, full_df)
    # ══ Absence–Incident Pattern Analysis ═══════════════════════════════════
    _absent_dates_analysis = st.session_state.get(f"absent_dates_{student_id}", [])
    if _absent_dates_analysis and not full_df.empty:
        import datetime as _aadt
        _abs_date_objs = set()
        for _d in _absent_dates_analysis:
            try: _abs_date_objs.add(_aadt.date.fromisoformat(_d))
            except: pass

        _inc_dates_sorted = sorted(full_df["date_parsed"].dt.date.tolist())
        _all_dates_sorted = sorted(set(_inc_dates_sorted) | _abs_date_objs)

        # ── Pattern 1: Incidents on return-to-school day after absence ──────
        _return_incidents = []  # (return_date, n_incidents, prev_abs_dates)
        for _dt in sorted(set(_inc_dates_sorted)):
            # Check if yesterday or recent prior school days were absences
            _prev = _dt - _aadt.timedelta(days=1)
            _prev2 = _dt - _aadt.timedelta(days=2)
            _prev3 = _dt - _aadt.timedelta(days=3)
            _prior_abs = [d for d in [_prev, _prev2, _prev3] if d in _abs_date_objs]
            if _prior_abs:
                _n = len([d for d in _inc_dates_sorted if d == _dt])
                _return_incidents.append((_dt, _n, _prior_abs))

        # ── Pattern 2: Absence immediately after a high-severity incident ───
        _post_escalation_abs = []  # (incident_date, severity, abs_dates_after)
        _high_sev_dates = full_df[full_df["severity"] >= 4]["date_parsed"].dt.date.tolist()
        for _hd in _high_sev_dates:
            _day_after = _hd + _aadt.timedelta(days=1)
            _two_after = _hd + _aadt.timedelta(days=2)
            _abs_after = [d for d in [_day_after, _two_after] if d in _abs_date_objs]
            if _abs_after:
                _sev = int(full_df[full_df["date_parsed"].dt.date == _hd]["severity"].max())
                _post_escalation_abs.append((_hd, _sev, _abs_after))

        # ── Pattern 3: Build-up after absence (escalation within 3 days of return) ─
        _buildup_after_abs = []  # (abs_end_date, first_incident_after, days_gap)
        _abs_sorted = sorted(_abs_date_objs)
        for _abs_d in _abs_sorted:
            # Find first incident within 4 school days of this absence
            for _gap in range(1, 5):
                _candidate = _abs_d + _aadt.timedelta(days=_gap)
                if _candidate in set(_inc_dates_sorted):
                    _n_on_return = len([d for d in _inc_dates_sorted if d == _candidate])
                    _buildup_after_abs.append((_abs_d, _candidate, _gap, _n_on_return))
                    break

        # ── Display analysis if any patterns found ───────────────────────────
        if _return_incidents or _post_escalation_abs or _buildup_after_abs:
            st.markdown("### 📅 Absence & Return-to-School Pattern Analysis")
            st.caption(
                "This section cross-references recorded absence dates with incident data to identify "
                "patterns that are clinically important: incidents on return-to-school days, "
                "absences after escalations, and incident build-up following time away."
            )

            if _return_incidents:
                _ri_total = sum(r[1] for r in _return_incidents)
                _ri_pct = int(_ri_total / len(full_df) * 100) if len(full_df) else 0
                st.markdown(
                    f"<div style='background:#fff7ed;border-left:4px solid #f97316;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"<b>🔄 Return-to-school incidents:</b> "
                    f"<b>{len(_return_incidents)} return day(s)</b> had incidents within 1–3 days of an absence. "
                    f"These account for <b>{_ri_total} incidents ({_ri_pct}% of total)</b>. "
                    "<br><br>"
                    "Return-to-school days are high-risk for students with disrupted regulatory systems. "
                    "After any period away — even a single day — the student must re-establish "
                    "familiarity with the environment, reconnect with staff, and rebuild tolerance for "
                    "the demands of the school day. This re-regulation period is a significant vulnerability window. "
                    "<br><br>"
                    "<b>Recommended proactive strategies for return days:</b> "
                    "Greet the student at the gate with a known, trusted adult. "
                    "Begin with a low-demand, highly predictable activity. "
                    "Delay any assessment, group work, or non-preferred task for at least the first hour. "
                    "Build in an explicit check-in before each session and provide a visual overview of the day."
                    "</div>",
                    unsafe_allow_html=True
                )
                with st.expander("See return-day details", expanded=False):
                    for _rt, _rn, _ra in _return_incidents:
                        st.markdown(f"• **{_rt.strftime('%a %-d %b')}** — {_rn} incident(s) "
                                    f"(absent on: {", ".join(d.strftime('%-d %b') for d in sorted(_ra))})")

            if _post_escalation_abs:
                st.markdown(
                    f"<div style='background:#fef2f2;border-left:4px solid #ef4444;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"<b>⚠️ Absences following escalation:</b> "
                    f"<b>{len(_post_escalation_abs)} instance(s)</b> where a recorded absence followed "
                    "a high-severity incident (severity 4–5) within 1–2 days. "
                    "<br><br>"
                    "Post-escalation absences are a significant clinical indicator. They may reflect: "
                    "the student being too dysregulated to return, a family decision to keep the student home "
                    "while the situation settles, or a planned withdrawal as part of a crisis response. "
                    "While protective in the short term, post-escalation absence also resets the student's "
                    "routine and regulatory baseline — making the return-to-school day a compounded risk event. "
                    "<br><br>"
                    "<b>Recommended approach:</b> When a student is absent following a significant episode, "
                    "the team should plan the return proactively — not reactively. "
                    "A re-entry plan should be agreed before the student arrives: "
                    "who will meet them, what the first hour looks like, and what supports are in place. "
                    "A brief family or carer contact before return can reduce anxiety on both sides."
                    "</div>",
                    unsafe_allow_html=True
                )
                with st.expander("See post-escalation absence details", expanded=False):
                    for _hd, _hs, _ha in _post_escalation_abs:
                        st.markdown(f"• Severity {_hs} incident on **{_hd.strftime('%a %-d %b')}** "
                                    f"→ absent on: {", ".join(d.strftime('%-d %b') for d in sorted(_ha))}")

            if _buildup_after_abs:
                _multi_inc_returns = [x for x in _buildup_after_abs if x[3] >= 2]
                _short_gap = [x for x in _buildup_after_abs if x[2] <= 2]
                st.markdown(
                    f"<div style='background:#fefce8;border-left:4px solid #eab308;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"<b>📈 Incident build-up after absence:</b> "
                    f"<b>{len(_buildup_after_abs)} of {len(_abs_date_objs)} recorded absence(s)</b> "
                    "were followed by an incident within 4 school days. "
                    + (f"{len(_short_gap)} of these occurred within 1–2 days of return — "
                       "indicating rapid build-up once back in the environment. "
                       if _short_gap else "") +
                    "<br><br>"
                    "This pattern is consistent with the theory of cumulative stress and regulatory capacity depletion: "
                    "when the student returns to a structured, demand-based environment after time away, "
                    "they must immediately begin managing the cognitive and sensory load of school. "
                    "Without a proactive re-regulation window at the start of each return day, "
                    "the student's window of tolerance narrows quickly and behaviours emerge sooner. "
                    "<br><br>"
                    "<b>Key question for the team:</b> Is there a pattern in the <i>type</i> of incidents "
                    "that follow absences? Do they match the primary behaviour identified above, "
                    "or are different behaviours emerging on return days? "
                    "If different, this may point to a specific return-to-school trigger "
                    "rather than a general regulatory vulnerability."
                    "</div>",
                    unsafe_allow_html=True
                )
                with st.expander("See absence-to-incident timeline", expanded=False):
                    for _ad, _id, _gap, _nin in _buildup_after_abs:
                        st.markdown(f"• Absent **{_ad.strftime('%a %-d %b')}** "
                                    f"→ {_nin} incident(s) on **{_id.strftime('%a %-d %b')}** "
                                    f"({_gap} day(s) after)")

        elif _absent_dates_analysis:
            st.info(
                f"✅ {len(_absent_dates_analysis)} absence(s) recorded — "
                "no significant absence–incident patterns detected in the current data. "
                "Continue logging to build a more complete picture."
            )

    # ── Placement phase analysis ──────────────────────────────────────────────
    _pl_start_str = st.session_state.get(f"pl_start_an_{student_id}") or student.get("placement_start")
    _pl_end_str   = st.session_state.get(f"pl_end_an_{student_id}")   or student.get("placement_end")
    _pl_exts_an   = load_placement_extensions_from_db(student_id)
    if _pl_start_str and not full_df.empty:
        import datetime as _pldt
        _pl_s = datetime.fromisoformat(_pl_start_str).date()
        _pl_e = datetime.fromisoformat(_pl_end_str).date() if _pl_end_str else _pldt.date.today()
        _total_pl_days = (_pl_e - _pl_s).days or 1

        # Settling-in period — first 4 weeks
        _setl_end  = _pl_s + _pldt.timedelta(weeks=4)
        _setl_incs = full_df[full_df["date_parsed"].dt.date <= _setl_end]
        _n_setl    = len(_setl_incs)
        _setl_pct  = int(_n_setl / len(full_df) * 100) if len(full_df) else 0

        # Pre-transition — last 4 weeks before end
        _pret_start = _pl_e - _pldt.timedelta(weeks=4)
        _pret_incs  = full_df[full_df["date_parsed"].dt.date >= _pret_start]
        _n_pret     = len(_pret_incs)
        _pret_pct   = int(_n_pret / len(full_df) * 100) if len(full_df) else 0

        # Extension period incidents
        _ext_rows = []
        for _ex in _pl_exts_an:
            try:
                _ef = datetime.fromisoformat(_ex["from"]).date()
                _et = datetime.fromisoformat(_ex["to"]).date()
                _en = len(full_df[(full_df["date_parsed"].dt.date >= _ef) &
                                   (full_df["date_parsed"].dt.date <= _et)])
                _ext_rows.append((_ex, _ef, _et, _en))
            except: pass

        if _total_pl_days > 14:  # Only show if placement long enough to be meaningful
            st.markdown("### 📌 Placement Phase Analysis")
            _phase_parts = []

            if _n_setl > 0:
                _phase_parts.append(
                    f"<b>🌱 Settling-in period (first 4 weeks — up to {_setl_end.strftime('%-d %b %Y')}):</b> "
                    f"<b>{_n_setl} of {len(full_df)} incidents ({_setl_pct}%)</b> occurred in this phase. "
                    + ("This is a high proportion during the adjustment phase. "
                       "Early placement incidents typically reflect the student testing relational safety, "
                       "adjusting to new routines and expectations, and beginning to build "
                       "regulatory capacity in an unfamiliar environment. "
                       "These incidents are expected and should not be over-interpreted — "
                       "compare week 1 to week 4 to assess whether adjustment was occurring. "
                       if _setl_pct >= 40 else
                       "The student settled into the placement with relatively few early incidents — "
                       "a positive indicator of early relational capacity and readiness to engage. ") +
                    "If incidents reduced after the first 4 weeks, this is evidence that the student "
                    "was successfully building regulatory capacity and relational safety through the placement."
                )
            elif _pl_s <= _pldt.date.today():
                _phase_parts.append(
                    f"<b>🌱 Settling-in period (first 4 weeks):</b> "
                    "No incidents recorded in the first 4 weeks of placement — "
                    "a strong positive start. Document what conditions supported this and sustain them."
                )

            if _pl_end_str and _n_pret > 0:
                _phase_parts.append(
                    f"<b>🔚 Pre-transition period (last 4 weeks — from {_pret_start.strftime('%-d %b %Y')}):</b> "
                    f"<b>{_n_pret} incident(s) ({_pret_pct}%)</b> occurred in this phase. "
                    + ("This elevated rate is consistent with anticipatory transition anxiety. "
                       "Students with disrupted attachment histories often escalate as a significant "
                       "relationship or routine approaches an end — testing whether the placement "
                       "and the relationship will hold. "
                       "A clear, predictable, communicated-in-advance transition plan — "
                       "with the student actively involved in co-designing next steps — "
                       "is the most effective intervention at this stage. "
                       "Avoid reducing structure or staff presence in the pre-transition period. "
                       if _pret_pct >= 30 else
                       "No significant pre-transition escalation — "
                       "the student appears to be managing the approaching transition well. "
                       "Continue providing clear transition information and predictable routines. ") +
                    "Compare the pre-transition rate to the overall rate to determine whether "
                    "transition anxiety is a significant factor in the incident profile."
                )

            for _ex, _ef, _et, _en in _ext_rows:
                _ext_days = (_et - _ef).days or 1
                _phase_parts.append(
                    f"<b>📌 Extension period {_ef.strftime('%-d %b')} – {_et.strftime('%-d %b %Y')}:</b> "
                    f"<b>{_en} incident(s)</b> during this extension "
                    f"(context: {_ex['reason']}). "
                    "Extensions reflect a decision to continue building on progress. "
                    "The incident rate during an extension should be compared to the rate in the original placement "
                    "period — if lower, the extension is supporting consolidation of gains. "
                    "If higher, consider whether increased demands or expectations are contributing."
                )

            for part in _phase_parts:
                st.markdown(
                    f"<div style='background:#f8fafc;border-left:4px solid #3b82f6;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"{part}</div>",
                    unsafe_allow_html=True
                )

    if not quick_only_df.empty and not crit_only_df.empty:
        escalation_rate = (len(crit_only_df) / len(quick_only_df)) * 100 if len(quick_only_df) > 0 else 0
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Regular Incidents", len(quick_only_df))
        with col2: st.metric("Critical Incidents", len(crit_only_df))
        with col3: st.metric("Escalation Rate", f"{escalation_rate:.1f}%")
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # BEHAVIOUR PROFILE — comprehensive multi-panel analysis
    # ══════════════════════════════════════════════════════════════════
    st.markdown("### 🎯 Behaviour Profile")

    _MIN_N      = 4
    _MIN_TREND  = 3
    _CRIT_SEV   = 3.0
    _SEV_LABELS = ["severity 1 Minor", "severity 2 Low", "severity 3 Moderate", "severity 4 Serious", "severity 5 Critical"]

    all_behaviours = full_df["behaviour_type"].value_counts().head(8).index.tolist()
    all_behaviours = [
        b for b in all_behaviours
        if b
        and not str(b).startswith("---")
        and len(str(b)) <= 80  # exclude raw ABCH narrative text
    ]

    if not all_behaviours:
        st.info("No behaviour data recorded yet.")
    else:
        _n_total = len(full_df)
        quick_beh_counts = [len(quick_only_df[quick_only_df["behaviour_type"] == b]) if not quick_only_df.empty else 0 for b in all_behaviours]
        crit_beh_counts  = [len(crit_only_df[crit_only_df["behaviour_type"] == b]) if not crit_only_df.empty else 0 for b in all_behaviours]
        total_beh_counts = [quick_beh_counts[i] + crit_beh_counts[i] for i in range(len(all_behaviours))]

        beh_sev_means, beh_sev_stds = [], []
        for b in all_behaviours:
            b_rows = full_df[full_df["behaviour_type"] == b]["severity"]
            beh_sev_means.append(round(float(b_rows.mean()), 2) if len(b_rows) > 0 else 0)
            beh_sev_stds.append(round(float(b_rows.std()), 2) if len(b_rows) > 1 else 0)

        # ── DATA SUFFICIENCY BANNER ────────────────────────────────────
        _reliable_behs = [b for i, b in enumerate(all_behaviours) if total_beh_counts[i] >= _MIN_N]
        _limited_behs  = [b for i, b in enumerate(all_behaviours) if 0 < total_beh_counts[i] < _MIN_N]
        if _limited_behs and not _reliable_behs:
            st.warning(
                f"⚠️ **Limited data** — fewer than {_MIN_N} incidents per behaviour recorded. "
                "Percentages and escalation rates are suppressed to avoid misleading conclusions. "
                "Continue logging to build a reliable picture."
            )
        elif _limited_behs:
            _lim_names = ", ".join(f"*{b}*" for b in _limited_behs[:3])
            _more = f" and {len(_limited_behs)-3} more" if len(_limited_behs) > 3 else ""
            st.info(
                f"ℹ️ **Note:** {len(_limited_behs)} behaviour(s) have fewer than {_MIN_N} incidents: "
                f"{_lim_names}{_more}. Escalation rates are suppressed for these until more data is recorded."
            )

        # ═══════════════════════════════════════════════════════════════
        # PANEL A — Frequency Overview
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### A — Frequency Overview")
        _pa1, _pa2 = st.columns([3, 2])
        with _pa1:
            fig_a1 = go.Figure()
            fig_a1.add_trace(go.Bar(
                y=all_behaviours, x=quick_beh_counts, name="Regular", orientation="h",
                marker=dict(color="#3b82f6", opacity=0.85, line=dict(color="white", width=1)),
                text=[str(v) if v else "" for v in quick_beh_counts], textposition="inside",
                textfont=dict(color="white", size=11, family="Arial Black"),
                hovertemplate="<b>%{y}</b><br>Regular: %{x}<extra></extra>"
            ))
            fig_a1.add_trace(go.Bar(
                y=all_behaviours, x=crit_beh_counts, name="Critical (ABCH)", orientation="h",
                marker=dict(color="#ef4444", opacity=0.9, line=dict(color="white", width=1)),
                text=[str(v) if v else "" for v in crit_beh_counts], textposition="inside",
                textfont=dict(color="white", size=11, family="Arial Black"),
                hovertemplate="<b>%{y}</b><br>Critical: %{x}<extra></extra>"
            ))
            fig_a1.update_layout(
                height=max(260, len(all_behaviours)*50+80), barmode="stack",
                title=dict(text="Frequency — Regular vs Critical", font=dict(size=12)),
                xaxis_title="<b>Number of incidents</b>",
                plot_bgcolor="#f8fafc", paper_bgcolor="white",
                font=dict(color="#0f172a", size=11, family="Arial"),
                xaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                           showline=True, linewidth=2, linecolor="#cbd5e1"),
                yaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1", automargin=True),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=40, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_a1, use_container_width=True)
            if all_behaviours:
                _pa_top     = all_behaviours[0]
                _pa_top_n   = total_beh_counts[0]
                _pa_top_pct = int(_pa_top_n / _n_total * 100) if _n_total else 0
                _pa_crit_n  = crit_beh_counts[0]
                _pa_crit_pct = int(_pa_crit_n / _pa_top_n * 100) if _pa_top_n else 0
                _pa_n_types = len(all_behaviours)
                _pa_insight = (
                    f"The primary behaviour is <b>{get_clinical_behaviour(_pa_top)}</b>, "
                    f"accounting for <b>{_pa_top_n} of {_n_total} incidents ({_pa_top_pct}%)</b>. "
                )
                if _pa_crit_n > 0:
                    _pa_insight += (
                        f"Of these, <b>{_pa_crit_n} ({_pa_crit_pct}%) escalated to a critical incident (ABCH form). </b>"
                        "Escalation from this behaviour warrants careful review of the antecedent chain — "
                        "what specific conditions or sequences led to the most severe episodes? "
                    )
                else:
                    _pa_insight += (
                        "No incidents involving this behaviour have escalated to critical level — "
                        "current responses appear to be containing escalation effectively. "
                    )
                if _pa_n_types >= 4:
                    _pa_insight += (
                        f"<b>{_pa_n_types} distinct behaviour types</b> are present across the data. "
                        "A wide range of behaviour types typically indicates a broad, pervasive stress response — "
                        "the student is communicating distress through multiple channels rather than a single "
                        "specific function. This suggests that foundational Body domain regulation supports "
                        "(sensory regulation, movement breaks, predictable routines) should be the primary focus, "
                        "rather than behaviour-by-behaviour intervention. "
                    )
                elif _pa_n_types <= 2:
                    _pa_insight += (
                        "A <b>narrow behaviour profile</b> (1–2 types) suggests a specific, consistent function — "
                        "the student is using a predictable response to communicate a particular unmet need. "
                        "This is a positive indicator for targeted functional intervention: "
                        "identify the function, teach an alternative, and pre-empt the trigger. "
                    )
                _pa_insight += (
                    "The proportion of blue (regular) to red (critical) bars shows how often each behaviour "
                    "remains in the Coping zone versus escalating to a more significant episode. "
                    "Behaviours with a high red proportion should be the focus of immediate antecedent intervention."
                )
                st.markdown(
                    f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"<b>📊 Understanding this chart:</b><br>{_pa_insight}</div>",
                    unsafe_allow_html=True
                )
        with _pa2:
            if _n_total >= 5:
                _donut_cols = ["#3b82f6","#ef4444","#f59e0b","#10b981","#8b5cf6","#f97316","#64748b","#06b6d4"]
                fig_donut = go.Figure(go.Pie(
                    labels=all_behaviours, values=total_beh_counts, hole=0.5,
                    marker=dict(colors=_donut_cols[:len(all_behaviours)], line=dict(color="white", width=2)),
                    textinfo="percent+label", textfont=dict(size=9), sort=False,
                    hovertemplate="<b>%{label}</b><br>%{value} incidents (%{percent})<extra></extra>",
                ))
                fig_donut.add_annotation(
                    text=f"<b>{_n_total}</b><br>total", x=0.5, y=0.5, showarrow=False,
                    font=dict(size=13, color="#1e293b")
                )
                fig_donut.update_layout(
                    title=dict(text="Proportion of behaviour types", font=dict(size=12)),
                    height=max(260, len(all_behaviours)*50+80), showlegend=False,
                    paper_bgcolor="white", margin=dict(t=40, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.caption(f"Proportion chart requires 5+ total incidents ({_n_total} recorded so far).")

        # ═══════════════════════════════════════════════════════════════
        # PANEL B — Severity Profile
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### B — Severity Profile")
        st.caption(
            "Incident distribution by severity. All logged behaviours occur in the Coping zone or beyond — "
            "if a student is within their Window of Tolerance (green), no incidents are being logged. "
            "🟡 Yellow (severity 1–2) = Coping — behaviour present but student managing  ·  "
            "🟠 Orange (severity 3) = Coping, approaching edge  ·  "
            "🔴 Red (severity 4–5) = Outside window — significant dysregulation. "
            "Critical incident status alone does not place a student outside their window."
        )
        # WoT zone colour map
        # Clinical framework: if incident logged, student NOT in green.
        # Yellow = Coping (severity 1–3), Red = Outside window (severity 4–5)
        _WOT_COLS = {
            1: "#eab308",   # yellow — coping (low level behaviour)
            2: "#eab308",   # yellow — coping
            3: "#f97316",   # orange — coping, approaching edge
            4: "#ef4444",   # red    — outside window
            5: "#7f1d1d",   # dark red — crisis
        }
        _WOT_NAMES = {
            1: "severity 1 — Coping",
            2: "severity 2 — Coping",
            3: "severity 3 — Coping, approaching edge",
            4: "severity 4 — Outside window",
            5: "severity 5 — Crisis",
        }
        # Build count matrix: behaviour × severity level
        _sev_matrix = {}  # {beh: {sv: count}}
        for b in all_behaviours:
            b_rows = full_df[full_df["behaviour_type"] == b]["severity"]
            _sev_matrix[b] = {sv: int((b_rows == sv).sum()) for sv in [1,2,3,4,5]}

        fig_b = go.Figure()
        # Add WoT background zones (shapes behind bars)
        _chart_h = max(300, len(all_behaviours)*55+120)
        # Add one trace per severity level
        for sv in [1, 2, 3, 4, 5]:
            _counts = [_sev_matrix[b][sv] for b in all_behaviours]
            _texts  = [str(v) if v > 0 else "" for v in _counts]
            if any(v > 0 for v in _counts):
                fig_b.add_trace(go.Bar(
                    y=all_behaviours, x=_counts,
                    name=_WOT_NAMES[sv],
                    orientation="h",
                    marker=dict(
                        color=_WOT_COLS[sv],
                        line=dict(color="white", width=1.5),
                        opacity=0.88
                    ),
                    text=_texts, textposition="inside",
                    textfont=dict(color="white", size=11, family="Arial Black"),
                    hovertemplate=f"<b>%{{y}}</b><br>{_WOT_NAMES[sv]}: %{{x}} incident(s)<extra></extra>"
                ))

        # Mean severity markers (diamond) overlaid
        _reliable = [b for i, b in enumerate(all_behaviours) if total_beh_counts[i] >= _MIN_N]
        if _reliable:
            _means_x = [beh_sev_means[all_behaviours.index(b)] for b in _reliable]
            fig_b.add_trace(go.Scatter(
                y=_reliable, x=_means_x,
                mode="markers+text",
                name="Mean severity",
                marker=dict(symbol="diamond", size=14, color="#1e293b",
                            line=dict(color="white", width=1.5)),
                text=[f"{v:.1f}" for v in _means_x],
                textposition="middle right",
                textfont=dict(size=9, color="#1e293b"),
                hovertemplate="<b>%{y}</b><br>Mean severity: %{x:.2f}<extra></extra>"
            ))

        # Outside window threshold vline removed — WoT zone shown via bar colour instead
        fig_b.update_layout(
            barmode="stack",
            height=_chart_h,
            title=dict(
                text="Incident count per severity level — coloured by Window of Tolerance zone"
                     " · ◆ = mean severity (requires 4+ incidents)",
                font=dict(size=11)
            ),
            xaxis=dict(
                title="<b>Number of incidents</b>",
                tickmode="linear", tick0=0, dtick=1,
                gridcolor="#e2e8f0", showline=True,
                linewidth=2, linecolor="#cbd5e1"
            ),
            yaxis=dict(showline=True, linewidth=2,
                       linecolor="#cbd5e1", automargin=True),
            plot_bgcolor="#f8fafc", paper_bgcolor="white",
            font=dict(color="#0f172a", size=11, family="Arial"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.04,
                xanchor="left", x=0, font=dict(size=9)
            ),
            margin=dict(t=70, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_b, use_container_width=True)
        if all_behaviours:
            _pb_coping_n  = sum(sum(_sev_matrix[b][sv] for sv in [1,2,3]) for b in all_behaviours)
            _pb_outside_n = sum(sum(_sev_matrix[b][sv] for sv in [4,5]) for b in all_behaviours)
            _pb_coping_pct = int(_pb_coping_n / _n_total * 100) if _n_total else 0
            _pb_l1_n = sum(_sev_matrix[b][1] for b in all_behaviours)
            _pb_l2_n = sum(_sev_matrix[b][2] for b in all_behaviours)
            _pb_l3_n = sum(_sev_matrix[b][3] for b in all_behaviours)
            _pb_l4_n = sum(_sev_matrix[b][4] for b in all_behaviours)
            _pb_l5_n = sum(_sev_matrix[b][5] for b in all_behaviours)
            _pb_insight = (
                f"<b>{_pb_coping_pct}% of all incidents ({_pb_coping_n}/{_n_total}) occurred within the Coping zone</b> "
                f"(severity 1–3: low-level {_pb_l1_n}, escalating {_pb_l2_n}, approaching edge {_pb_l3_n}). "
                "This is clinically significant — it means the student is exhibiting behaviour as a way of "
                "managing or communicating distress, rather than being fully dysregulated. "
                "The Coping zone is where staff intervention is most effective: "
                "offering choices, reducing demand, co-regulating, and providing predictable structure "
                "can prevent further escalation. "
            )
            if _pb_outside_n > 0:
                _pb_insight += (
                    f"<b>{_pb_outside_n} incident(s) ({100-_pb_coping_pct}%) reached the outside-window zone</b> "
                    f"(serious {_pb_l4_n}, crisis {_pb_l5_n}). "
                    "These episodes indicate the student moved beyond coping into significant dysregulation. "
                    "Post-incident repair — re-establishing relational safety before returning to learning — "
                    "is essential after every outside-window episode. "
                    "Review what proactive conditions were absent on those days and what de-escalation "
                    "strategies were applied — this informs both the safety plan and the hypothesis. "
                )
            else:
                _pb_insight += (
                    "<b>No incidents reached the outside-window zone</b> — a significant positive indicator. "
                    "All logged behaviour remained within the Coping zone, meaning the student "
                    "was always attempting to manage, and current staff responses are successfully "
                    "preventing escalation to full dysregulation. "
                )
            _pb_insight += (
                "The mean severity diamond markers show the average level for each behaviour type. "
                "Where the mean approaches severity 3 or above, consider whether current antecedent strategies "
                "are sufficiently proactive — the student may need wider-window supports before that behaviour emerges."
            )
            st.markdown(
                f"<div style='background:#f8fafc;border-left:4px solid #eab308;border-radius:8px;"
                f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                f"<b>📊 Understanding this chart:</b><br>{_pb_insight}</div>",
                unsafe_allow_html=True
            )

        if not _reliable:
            st.caption("⚠️ Mean severity markers require 4+ incidents per behaviour — not shown yet.")

        # Data sufficiency note for behaviours with < 2 incidents
        _too_few = [b for i, b in enumerate(all_behaviours) if total_beh_counts[i] < 2]
        if _too_few:
            st.caption(
                f"⚠️ Behaviours with fewer than 2 incidents not shown in severity spread: "
                + ", ".join(f"*{b}*" for b in _too_few)
            )
        _pb2 = None  # _pb2 no longer used — single chart replaces two columns
        if _pb2:
            _beh_heat = [b for i, b in enumerate(all_behaviours) if total_beh_counts[i] >= 2]
            if _beh_heat:
                _heat_z, _heat_text = [], []
                for b in _beh_heat:
                    b_rows = full_df[full_df["behaviour_type"] == b]["severity"]
                    rz = [int((b_rows == sv).sum()) for sv in [1,2,3,4,5]]
                    rt = [str(n) if n > 0 else "" for n in rz]
                    _heat_z.append(rz); _heat_text.append(rt)
                # Severity spread — grouped bar chart, coloured by WoT zone
                # Green (severity 1–2) = coping/within window, Amber (severity 3) = elevated,
                # Red (severity 4–5) = outside window. Count drives bar length, not colour.
                # WoT colour scheme (per CLC-LBU framework):
                # Green  = Within window (severity 1–2) — student regulated and engaged
                # Yellow = Coping (severity 3)          — managing but approaching edge
                # Red    = Outside window (severity 4–5) — dysregulated / crisis
                _SEV_COLOURS_WOT = {
                    1: "#22c55e",  # green  — within window
                    2: "#22c55e",  # green  — within window
                    3: "#eab308",  # yellow — coping / approaching edge
                    4: "#ef4444",  # red    — outside window / serious
                    5: "#7f1d1d",  # dark red — crisis zone
                }
                _sev_names_wot = {
                    1: "severity 1 Within window (regulated)",
                    2: "severity 2 Within window (low concern)",
                    3: "severity 3 Coping (approaching edge)",
                    4: "severity 4 Outside window (serious)",
                    5: "severity 5 Outside window (crisis)",
                }
                fig_b2 = go.Figure()
                for sv in [1, 2, 3, 4, 5]:
                    _sv_counts = [rz[sv-1] for rz in _heat_z]
                    if any(v > 0 for v in _sv_counts):
                        fig_b2.add_trace(go.Bar(
                            y=_beh_heat, x=_sv_counts,
                            name=_sev_names_wot[sv],
                            orientation="h",
                            marker=dict(color=_SEV_COLOURS_WOT[sv],
                                        line=dict(color="white", width=1)),
                            text=[str(v) if v > 0 else "" for v in _sv_counts],
                            textposition="inside",
                            textfont=dict(color="white", size=10, family="Arial Black"),
                            hovertemplate=f"<b>%{{y}}</b><br>{_sev_names_wot[sv]}: %{{x}}<extra></extra>"
                        ))
                fig_b2.update_layout(
                    title=dict(text="Severity spread — colour shows Window of Tolerance zone", font=dict(size=11)),
                    height=max(260, len(_beh_heat)*55+120),
                    barmode="stack",
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    font=dict(color="#0f172a", size=10, family="Arial"),
                    xaxis=dict(title="<b>Number of incidents</b>",
                               tickmode="linear", tick0=0, dtick=1,
                               gridcolor="#e2e8f0", showline=True,
                               linewidth=2, linecolor="#cbd5e1"),
                    yaxis=dict(showline=True, linewidth=2,
                               linecolor="#cbd5e1", automargin=True),
                    legend=dict(orientation="h", yanchor="bottom",
                                y=1.02, xanchor="left", x=0,
                                font=dict(size=9)),
                    margin=dict(t=60, b=10, l=10, r=20)
                )
                st.plotly_chart(fig_b2, use_container_width=True)
                st.caption(
                    "🟢 Green (severity 1–2) = Within window — student is regulated and engaged effectively  ·  "
                    "🟡 Yellow (severity 3) = Coping — managing, but approaching the edge of the window  ·  "
                    "🔴 Red (severity 4–5) = Outside window — dysregulated / crisis zone. "
                    "Green bars are a positive indicator: the student is within their Window of Tolerance."
                )


        # ═══════════════════════════════════════════════════════════════
        # PANEL C — Escalation Risk Table
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### C — Escalation Risk Summary")
        _risk_rows = []
        for i, beh in enumerate(all_behaviours):
            total = total_beh_counts[i]; crit = crit_beh_counts[i]
            sev_m = beh_sev_means[i]; std = beh_sev_stds[i]
            if total >= _MIN_N:
                pct = crit / total * 100
                risk_icon = "🔴" if pct > 50 else "🟡" if pct > 25 else "🟢"
                risk_lbl  = "High" if pct > 50 else "Medium" if pct > 25 else "Low"
                _risk_rows.append({
                    "Behaviour": beh, "Total (n)": total, "Regular": total-crit, "Critical": crit,
                    "Escalation %": f"{pct:.0f}%", "Mean Sev": f"{sev_m:.1f}",
                    "Sev StDev": f"{std:.1f}" if std > 0 else "—",
                    "Escalation Tier": f"{risk_icon} {risk_lbl}",
                })
            else:
                _risk_rows.append({
                    "Behaviour": beh, "Total (n)": total, "Regular": total-crit, "Critical": crit,
                    "Escalation %": "⚠️ Insufficient", "Mean Sev": f"{sev_m:.1f}" if total > 0 else "—",
                    "Sev StDev": "—", "Escalation Tier": "⚪ Limited data",
                })
        if _risk_rows:
            st.dataframe(
                pd.DataFrame(_risk_rows), use_container_width=True, hide_index=True,
                column_config={
                    "Behaviour":    st.column_config.TextColumn("Behaviour", width="large"),
                    "Total (n)":    st.column_config.NumberColumn("Total (n)", width="small"),
                    "Regular":      st.column_config.NumberColumn("Regular", width="small"),
                    "Critical":     st.column_config.NumberColumn("Critical", width="small"),
                    "Escalation %": st.column_config.TextColumn("Escalation %", width="medium"),
                    "Mean Sev":     st.column_config.TextColumn("Mean Sev", width="small"),
                    "Sev StDev":    st.column_config.TextColumn("Sev StDev", help="Higher = more variable severity; lower = more consistent", width="small"),
                    "Escalation Tier": st.column_config.TextColumn("Escalation Tier", width="medium"),
                }
            )
            st.caption(
                "🔴 High = 51%+ escalate  ·  🟡 Medium = 26–50%  ·  🟢 Low = 0–25%  ·  "
                "⚪ Insufficient = fewer than 4 incidents logged for this behaviour — "
                "not a data error, just means more observations are needed before a reliable rate can be calculated  ·  "
                "Sev StDev: spread of severity scores (higher = more variable)"
            )
            _pch = [r for r in _risk_rows if r.get("Escalation Tier","").startswith("🔴")]
            _pcm = [r for r in _risk_rows if r.get("Escalation Tier","").startswith("🟡")]
            _pcp = []
            if _pch: _pcp.append(f"{len(_pch)} behaviour(s) carry high escalation risk "
                f"({", ".join(get_clinical_behaviour(r['Behaviour']) for r in _pch[:2])}). "
                "Intervene early in the Coping zone for these behaviours.")
            if _pcm: _pcp.append(f"{len(_pcm)} behaviour(s) have medium risk — apply co-regulation consistently.")
            if not _pch and not _pcm: _pcp.append(
                "No behaviours currently showing elevated escalation risk — "
                "all behaviours are remaining within the Coping zone rather than escalating to critical. "
                "This is a positive indicator that current staff responses are containing escalation. "
                "Maintain and document current strategies explicitly so they survive staff changes."
            )
            _pcp_preamble = (
                "Escalation rate is the proportion of incidents involving a given behaviour that progressed "
                "from regular (coping) to critical (ABCH-documented). A high rate for a specific behaviour "
                "signals that something about how that behaviour unfolds — the environment, staff response, "
                "or the student's internal state — is not being interrupted effectively in the Coping zone. "
                "Sev StDev (standard deviation) tells you how variable the severity is: "
                "a low StDev means episodes are consistently similar in intensity; "
                "a high StDev means the student oscillates between mild and severe episodes, "
                "which may suggest unpredictable triggers or inconsistent staff response. "
            )
            st.markdown(
                "<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                "padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                "<b>📊 Understanding this chart:</b><br>"
                + _pcp_preamble + "<br>"
                + " ".join(_pcp) + "</div>",
                unsafe_allow_html=True
            )

        # ═══════════════════════════════════════════════════════════════
        # PANEL D — Behaviour by Time of Day
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### D — Behaviour by Time of Day")
        st.caption("Which behaviours peak in which session. Darker = more incidents.")
        if "session" in full_df.columns:
            _session_order = ["Morning", "Middle", "Afternoon"]
            _bsdf_rows = []
            for b in all_behaviours:
                bdf = full_df[full_df["behaviour_type"] == b]
                row = {"Behaviour": b}
                for s in _session_order: row[s] = int((bdf["session"] == s).sum())
                _bsdf_rows.append(row)
            _bsdf = pd.DataFrame(_bsdf_rows)
            _sess_z    = [[row[s] for s in _session_order] for _, row in _bsdf.iterrows()]
            _sess_text = [[str(v) if v > 0 else "" for v in r] for r in _sess_z]
            _sess_xlbl = ["Morning (before 11am)", "Middle of day (11am-1:30pm)", "Afternoon (1:31-2:45pm)"]
            fig_d = go.Figure(go.Heatmap(
                z=_sess_z, x=_sess_xlbl, y=_bsdf["Behaviour"].tolist(),
                text=_sess_text, texttemplate="%{text}",
                colorscale=[[0,"#f8fafc"],[0.3,"#bae6fd"],[0.65,"#f59e0b"],[1,"#ef4444"]],
                showscale=True, colorbar=dict(title="n", thickness=12, len=0.7),
                hovertemplate="<b>%{y}</b><br>%{x}: %{z} incidents<extra></extra>"
            ))
            fig_d.update_layout(
                height=max(200, len(all_behaviours)*48+100),
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(color="#0f172a", size=11, family="Arial"),
                xaxis=dict(side="top", tickfont=dict(size=10)),
                yaxis=dict(automargin=True, tickfont=dict(size=10)),
                margin=dict(t=60, b=10, l=10, r=80)
            )
            st.plotly_chart(fig_d, use_container_width=True)
            # D insight
            if _bsdf_rows:
                _pd_counts = {s: sum(r[s] for r in _bsdf_rows) for s in ["Morning","Middle","Afternoon"]}
                _pd_peak   = max(_pd_counts, key=_pd_counts.get)
                _pd_low    = min(_pd_counts, key=_pd_counts.get)
                _pd_peak_n = _pd_counts[_pd_peak]
                _pd_low_n  = _pd_counts[_pd_low]
                _pd_peak_pct = int(_pd_peak_n / _n_total * 100) if _n_total else 0
                _pd_low_pct  = int(_pd_low_n  / _n_total * 100) if _n_total else 0
                _pd_labels = {
                    "Morning":   "morning session (before 11am)",
                    "Middle":    "middle of the day (11am–1:30pm)",
                    "Afternoon": "afternoon session (after 1:30pm)"
                }
                _pd_context = {
                    "Morning":   "Morning peaks may reflect difficulty with the transition from home, "
                                 "low readiness to engage, or unmet overnight/morning needs (hunger, sleep, "
                                 "sensory dysregulation on arrival). A structured, low-demand arrival routine "
                                 "with a trusted adult check-in is the most effective morning intervention.",
                    "Middle":    "Middle-of-day peaks frequently reflect cumulative fatigue — the student "
                                 "has been managing demands since arrival and their regulatory capacity is depleted. "
                                 "Lunch and transition periods also introduce unstructured time, which can be "
                                 "particularly challenging. A mid-day sensory break, a quiet space option, "
                                 "or reduced demand before/after the lunch break are high-priority strategies.",
                    "Afternoon": "Afternoon peaks often reflect end-of-day fatigue, anticipatory anxiety about "
                                 "the transition home, or the accumulation of the day's regulatory demands. "
                                 "A structured, predictable end-of-day routine — including a debrief, "
                                 "a positive closure activity, and advance notice of tomorrow's schedule — "
                                 "is recommended."
                }
                _pd_insight = (
                    f"Incidents peak in the <b>{_pd_labels[_pd_peak]}</b>, "
                    f"accounting for <b>{_pd_peak_n} of {_n_total} incidents ({_pd_peak_pct}%)</b>. "
                    f"{_pd_context[_pd_peak]} "
                )
                if _pd_low_n < _pd_peak_n and _pd_low != _pd_peak:
                    _pd_insight += (
                        f"The lowest-frequency session is the <b>{_pd_labels[_pd_low]}</b> "
                        f"({_pd_low_n} incidents, {_pd_low_pct}%). "
                        "Identifying what is structurally different about this session — "
                        "staffing, activity type, demand level, or environmental factors — "
                        "and replicating those conditions in the peak session is one of the most effective "
                        "preventive strategies available."
                    )
                st.markdown(
                    f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                    f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    f"<b>📊 Understanding this chart:</b><br>{_pd_insight}</div>",
                    unsafe_allow_html=True
                )
            if _n_total < 5:
                st.caption("⚠️ Session patterns are preliminary with limited data — treat as directional only.")

        # ═══════════════════════════════════════════════════════════════
        # PANEL E — Behaviour by Location
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### E — Behaviour by Location")
        st.caption("Where each behaviour occurs most frequently.")
        if "location" in full_df.columns:
            _top_locs = [l for l in full_df["location"].value_counts().head(6).index.tolist()
                         if l and str(l).strip()]
            if _top_locs:
                _bloc_z, _bloc_text, _bloc_y = [], [], []
                for b in all_behaviours:
                    bdf = full_df[full_df["behaviour_type"] == b]
                    rz = [int((bdf["location"] == loc).sum()) for loc in _top_locs]
                    rt = [str(n) if n > 0 else "" for n in rz]
                    if any(v > 0 for v in rz):
                        _bloc_z.append(rz); _bloc_text.append(rt); _bloc_y.append(b)
                if _bloc_y:
                    fig_e = go.Figure(go.Heatmap(
                        z=_bloc_z, x=_top_locs, y=_bloc_y,
                        text=_bloc_text, texttemplate="%{text}",
                        colorscale=[[0,"#f8fafc"],[0.3,"#a5b4fc"],[0.7,"#7c3aed"],[1,"#3b0764"]],
                        showscale=True, colorbar=dict(title="n", thickness=12, len=0.7),
                        hovertemplate="<b>%{y}</b><br>%{x}: %{z} incidents<extra></extra>"
                    ))
                    fig_e.update_layout(
                        height=max(200, len(_bloc_y)*48+100),
                        plot_bgcolor="white", paper_bgcolor="white",
                        font=dict(color="#0f172a", size=10, family="Arial"),
                        xaxis=dict(side="top", tickangle=-30, tickfont=dict(size=10)),
                        yaxis=dict(automargin=True, tickfont=dict(size=10)),
                        margin=dict(t=70, b=10, l=10, r=80)
                    )
                    st.plotly_chart(fig_e, use_container_width=True)
                    if _bloc_y:
                        _pe_top_loc = _top_locs[0] if _top_locs else ""
                        _pe_top_n = max(sum(r) for r in _bloc_z) if _bloc_z else 0
                        _pe_name = normalise_location(_pe_top_loc)
                        _pe_advice_map = {
                            "jp room": "Classroom environments can trigger behaviour due to academic demand, "
                                       "seating arrangements, noise from peers, or the presence of "
                                       "non-preferred tasks. Consider the physical layout, sensory conditions, "
                                       "and the demand level of activities occurring when incidents happen.",
                            "py room": "Classroom environments can trigger behaviour due to academic demand, "
                                       "seating arrangements, noise from peers, or the presence of "
                                       "non-preferred tasks. Consider the physical layout, sensory conditions, "
                                       "and the demand level of activities occurring when incidents happen.",
                            "sy room": "Classroom environments can trigger behaviour due to academic demand, "
                                       "seating arrangements, noise from peers, or the presence of "
                                       "non-preferred tasks. Consider the physical layout, sensory conditions, "
                                       "and the demand level of activities occurring when incidents happen.",
                            "yard":    "Yard and playground incidents often reflect unstructured time, "
                                       "peer conflict, sensory overload from noise and activity, "
                                       "and reduced adult proximity. Increased supervision ratios, "
                                       "structured yard activities, and a clear opt-out space are recommended.",
                            "kitchen": "Kitchen incidents may reflect access to food as a motivator, "
                                       "transitions in and out of the space, or sensory factors. "
                                       "Review routines around meal/snack times and ensure clear, "
                                       "consistent expectations are in place.",
                            "toilets": "Incidents in or near toilets may indicate the student uses "
                                       "this space as an escape route, or that transitions to/from "
                                       "the toilets are a trigger. Review supervision and transition routines.",
                        }
                        _pe_advice = next(
                            (v for k, v in _pe_advice_map.items() if k in _pe_name.lower()),
                            "Review the specific environmental conditions in this location — "
                            "consider noise, crowding, demand level, supervision, and transition patterns."
                        )
                        st.markdown(
                            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                            f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                            f"<b>📊 Understanding this chart:</b><br>"
                            f"The highest-frequency incident location is <b>{_pe_name}</b>. "
                            "Location clustering is an important signal — it tells you where environmental "
                            "modification will have the most direct preventive impact. "
                            f"{_pe_advice} "
                            "Also consider: does this location coincide with the peak time of day? "
                            "If so, the combination of place and time creates a compounding risk window "
                            "that warrants an immediate, targeted proactive plan.</div>",
                            unsafe_allow_html=True
                        )
                    if _n_total < 5:
                        st.caption("⚠️ Location patterns are preliminary with limited data.")

        # ═══════════════════════════════════════════════════════════════
        # PANEL F — Behaviour × Antecedent Crosswalk
        # ═══════════════════════════════════════════════════════════════
        st.markdown("#### F — Behaviour x Antecedent Crosswalk")
        st.caption(
            "Which triggers precede which behaviours. "
            "Identifies specific antecedent-behaviour pairs for targeted intervention. "
            "Blank = zero incidents with that combination."
        )
        if "antecedent" in full_df.columns:
            _top_ants = [
                a for a in full_df[~full_df["antecedent"].str.startswith("---", na=True)]
                ["antecedent"].value_counts().head(8).index.tolist()
                if a and str(a).strip()
            ]
            def _shorten_ant(s, n=32):
                return s[s.find(" - ")+3:] if " - " in s else s[:n]
            _ant_labels = [_shorten_ant(a) for a in _top_ants]
            if _top_ants:
                _cross_z, _cross_text, _cross_y = [], [], []
                for b in all_behaviours:
                    bdf = full_df[full_df["behaviour_type"] == b]
                    rz = [int((bdf["antecedent"] == ant).sum()) for ant in _top_ants]
                    rt = [str(n) if n > 0 else "" for n in rz]
                    if any(v > 0 for v in rz):
                        _cross_z.append(rz); _cross_text.append(rt); _cross_y.append(b)
                if _cross_y:
                    fig_f = go.Figure(go.Heatmap(
                        z=_cross_z, x=_ant_labels, y=_cross_y,
                        text=_cross_text, texttemplate="%{text}",
                        colorscale=[[0,"#f0fdf4"],[0.3,"#6ee7b7"],[0.65,"#0284c7"],[1,"#1e3a5f"]],
                        showscale=True, colorbar=dict(title="n", thickness=12, len=0.7),
                        hovertemplate="<b>Behaviour:</b> %{y}<br><b>Trigger:</b> %{x}<br>%{z} incidents<extra></extra>"
                    ))
                    fig_f.update_layout(
                        height=max(240, len(_cross_y)*48+120),
                        plot_bgcolor="white", paper_bgcolor="white",
                        font=dict(color="#0f172a", size=10, family="Arial"),
                        xaxis=dict(side="top", tickangle=-40, tickfont=dict(size=9), automargin=True),
                        yaxis=dict(automargin=True, tickfont=dict(size=10)),
                        margin=dict(t=110, b=10, l=10, r=80)
                    )
                    st.plotly_chart(fig_f, use_container_width=True)
                    if _cross_y and _cross_z:
                        _pf_flat = [(ri, ci, v) for ri, row in enumerate(_cross_z) for ci, v in enumerate(row) if v > 0]
                        if _pf_flat:
                            _pf_max_ri, _pf_max_ci, _pf_max_v = max(_pf_flat, key=lambda x: x[2])
                            _pf_beh = get_clinical_behaviour(_cross_y[_pf_max_ri]) if _pf_max_ri < len(_cross_y) else ""
                            _pf_ant = _ant_labels[_pf_max_ci] if _pf_max_ci < len(_ant_labels) else ""
                            st.markdown(
                                f"<div style='background:#f8fafc;border-left:4px solid #0284c7;"
                                f"border-radius:6px;padding:.55rem .9rem;font-size:.82rem;color:#1e293b;'>"
                                f"<b>📊 What this shows:</b> "
                                "The darkest cells identify the most predictable trigger–behaviour sequences. "
                                + (f"The strongest pairing: <b>{_pf_ant}</b> → <b>{_pf_beh}</b> ({_pf_max_v} times). "
                                   if _pf_beh else "") +
                                "Intervening before this trigger occurs is more effective than "
                                "responding after the behaviour has started.</div>",
                                unsafe_allow_html=True
                            )
                    if _n_total < 8:
                        st.caption("⚠️ Crosswalk is preliminary with limited data — treat each cell as directional only.")

        # ═══════════════════════════════════════════════════════════════
        # PANEL G — Behaviour Over Time
        # ═══════════════════════════════════════════════════════════════
        _beh_for_trend = [b for i, b in enumerate(all_behaviours) if total_beh_counts[i] >= _MIN_TREND]
        if _beh_for_trend and len(full_df) >= 6:
            st.markdown("#### G — Behaviour Frequency Over Time")
            st.caption(
                "Weekly incident count per behaviour. Only behaviours with 3+ incidents shown. "
                "Diamond = single week of data, no trend line possible."
            )
            full_df["_week"] = full_df["date_parsed"].dt.to_period("W").apply(lambda p: p.start_time)
            fig_g = go.Figure()
            _line_cols = ["#3b82f6","#ef4444","#f59e0b","#10b981","#8b5cf6","#f97316"]
            _any_g = False
            for ci, b in enumerate(_beh_for_trend):
                b_weekly = full_df[full_df["behaviour_type"] == b].groupby("_week").size().reset_index(name="n")
                _col = _line_cols[ci % len(_line_cols)]
                if len(b_weekly) >= 2:
                    fig_g.add_trace(go.Scatter(
                        x=b_weekly["_week"], y=b_weekly["n"], mode="lines+markers", name=b[:40],
                        line=dict(color=_col, width=2),
                        marker=dict(size=8, color=_col, line=dict(color="white", width=1.5)),
                        hovertemplate=f"<b>{b[:35]}</b><br>Week of %{{x|%-d %b}}<br>%{{y}} incidents<extra></extra>"
                    )); _any_g = True
                else:
                    fig_g.add_trace(go.Scatter(
                        x=b_weekly["_week"], y=b_weekly["n"], mode="markers",
                        name=b[:40] + " (1 week)",
                        marker=dict(size=12, color=_col, symbol="diamond", line=dict(color="white", width=1.5)),
                        hovertemplate=f"<b>{b[:35]}</b><br>%{{y}} incidents<extra></extra>"
                    )); _any_g = True
            if _any_g:
                fig_g.update_layout(
                    height=320, xaxis_title="<b>Week</b>", yaxis_title="<b>Incidents per week</b>",
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    font=dict(color="#0f172a", size=11, family="Arial"),
                    yaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                               showline=True, linewidth=2, linecolor="#cbd5e1", rangemode="tozero"),
                    xaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1",
                               tickformat="%-d %b", tickangle=-30),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    margin=dict(t=10, b=40, l=10, r=10)
                )
                st.plotly_chart(fig_g, use_container_width=True)
                st.markdown(
                    "<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                    "padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                    "<b>📊 Understanding this chart:</b><br>"
                    "This chart shows whether each behaviour is <b>increasing, stable, or reducing</b> over time. "
                    "An <b>upward trend</b> is the most important finding — it means a behaviour is becoming more frequent, "
                    "signalling that current supports are insufficient and an urgent review is warranted. "
                    "Ask: have there been any changes in staffing, timetable, or environmental conditions "
                    "that coincide with the increase? "
                    "A <b>downward trend</b> is a positive indicator — current strategies are having effect. "
                    "Document what has changed and ensure those conditions are sustained. "
                    "A <b>flat trend</b> suggests the current level of support is maintaining but not reducing the behaviour — "
                    "consider whether a strategy intensification or a new approach is needed. "
                    "Diamond markers indicate only a single week of data — treat these as preliminary observations, "
                    "not conclusions. Continue logging to build a trend line.</div>",
                    unsafe_allow_html=True
                )
            full_df.drop(columns=["_week"], errors="ignore", inplace=True)

        # ═══════════════════════════════════════════════════════════════
        # PANEL H — Duration per behaviour
        # ═══════════════════════════════════════════════════════════════
        if "duration_minutes" in full_df.columns:
            _dur_df = full_df[
                full_df["duration_minutes"].notna() &
                full_df["behaviour_type"].isin(all_behaviours)
            ].copy()
            _dur_df["duration_minutes"] = pd.to_numeric(_dur_df["duration_minutes"], errors="coerce")
            _dur_df = _dur_df[_dur_df["duration_minutes"] > 0]
            if len(_dur_df) >= 3:
                st.markdown("#### H — Incident Duration by Behaviour")
                st.caption("Average incident duration. Grey = fewer than 2 records — treat as indicative only.")
                _dur_agg = (_dur_df.groupby("behaviour_type")["duration_minutes"]
                            .agg(["mean","count"]).reset_index()
                            .rename(columns={"mean":"avg","count":"n"})
                            .sort_values("avg", ascending=True))
                _dur_cols, _dur_text = [], []
                for _, r in _dur_agg.iterrows():
                    if r["n"] < 2:
                        _dur_cols.append("#cbd5e1"); _dur_text.append(f"{r['avg']:.1f} min (n={int(r['n'])} — limited)")
                    elif r["avg"] >= 15:
                        _dur_cols.append("#ef4444"); _dur_text.append(f"{r['avg']:.1f} min (n={int(r['n'])})")
                    elif r["avg"] >= 8:
                        _dur_cols.append("#f59e0b"); _dur_text.append(f"{r['avg']:.1f} min (n={int(r['n'])})")
                    else:
                        _dur_cols.append("#3b82f6"); _dur_text.append(f"{r['avg']:.1f} min (n={int(r['n'])})")
                fig_h = go.Figure(go.Bar(
                    y=_dur_agg["behaviour_type"], x=_dur_agg["avg"].round(1), orientation="h",
                    marker=dict(color=_dur_cols, line=dict(color="white", width=1)),
                    text=_dur_text, textposition="outside",
                    textfont=dict(size=9, color="#1e293b"),
                    hovertemplate="<b>%{y}</b><br>Avg: %{x:.1f} min<extra></extra>"
                ))
                fig_h.update_layout(
                    height=max(200, len(_dur_agg)*50+80),
                    xaxis_title="<b>Average duration (minutes)</b>",
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    font=dict(color="#0f172a", size=11, family="Arial"),
                    xaxis=dict(gridcolor="#e2e8f0", showline=True, linewidth=2, linecolor="#cbd5e1"),
                    yaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1", automargin=True),
                    showlegend=False, margin=dict(t=10, b=10, l=10, r=180)
                )
                st.plotly_chart(fig_h, use_container_width=True)
                st.caption("🔴 Red = 15+ min  ·  🟡 Amber = 8–14 min  ·  🔵 Blue = under 8 min  ·  ⬜ Grey = insufficient records")
                if not _dur_agg.empty:
                    _ph_longest = _dur_agg.iloc[-1]
                    _ph_beh_name = get_clinical_behaviour(_ph_longest["behaviour_type"])
                    _ph_avg      = _ph_longest["avg"]
                    _ph_tier     = "long" if _ph_avg >= 15 else "medium" if _ph_avg >= 8 else "short"
                    _ph_tier_text = {
                        "long":   f"An average of {_ph_avg:.1f} minutes is a <b>long-duration episode</b>. "
                                  "Long-duration incidents indicate the student has moved significantly "
                                  "outside their window and requires substantial time to return to a state "
                                  "where they can re-engage. Post-incident, do not rush back to learning — "
                                  "prioritise relational repair, offer a low-demand transition activity, "
                                  "and allow recovery time proportionate to the episode length. "
                                  "For episodes over 15 minutes, a structured re-entry protocol is recommended.",
                        "medium": f"An average of {_ph_avg:.1f} minutes is a <b>medium-duration episode</b>. "
                                  "The student is taking a moderate amount of time to return to the Coping zone. "
                                  "De-escalation strategies should be applied early and consistently — "
                                  "the goal is to shorten this window through earlier intervention, "
                                  "not to wait out the episode.",
                        "short":  f"An average of {_ph_avg:.1f} minutes is a <b>short-duration episode</b>. "
                                  "Brief episodes suggest the student recovers relatively quickly once triggered. "
                                  "This is a protective factor — focus on preventing the trigger rather than "
                                  "managing the episode itself.",
                    }
                    st.markdown(
                        f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
                        f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
                        f"<b>📊 Understanding this chart:</b><br>"
                        "Incident duration shows how long the student remains in an escalated state — "
                        "this directly informs recovery time planning and post-incident protocols. "
                        "Longer durations mean the student's nervous system takes longer to return to baseline, "
                        "which means re-engagement with learning must be delayed accordingly. "
                        f"The longest-duration behaviour is <b>{_ph_beh_name}</b>. "
                        + _ph_tier_text[_ph_tier] + "</div>",
                        unsafe_allow_html=True
                    )

        # ═══════════════════════════════════════════════════════════════
        # PANEL I — Interventions by Behaviour
        # ═══════════════════════════════════════════════════════════════
        if "intervention" in full_df.columns:
            _int_rows = []
            for _, row in full_df.iterrows():
                ints = row.get("intervention", [])
                if isinstance(ints, str):
                    try: ints = json.loads(ints)
                    except: ints = [ints] if ints else []
                beh = row.get("behaviour_type", "")
                if beh and beh in all_behaviours:
                    for iv in (ints if isinstance(ints, list) else [ints]):
                        _iv_str = str(iv).strip()
                        if _iv_str and _iv_str.lower() not in ("nan", "none", "", "null"):
                            _int_rows.append({"behaviour": beh, "intervention": _iv_str})
            if len(_int_rows) >= 3:
                st.markdown("#### I — Interventions by Behaviour Type")
                st.caption("Which strategies were used for each behaviour. Helps assess whether responses are matched to the behaviour function.")
                _int_df    = pd.DataFrame(_int_rows)
                _int_pivot = _int_df.groupby(["behaviour","intervention"]).size().reset_index(name="n")
                _top_ints  = _int_pivot.groupby("intervention")["n"].sum().nlargest(8).index.tolist()
                _int_filt  = _int_pivot[_int_pivot["intervention"].isin(_top_ints)]
                _int_behs  = [b for b in all_behaviours if b in _int_filt["behaviour"].values]
                if _int_behs:
                    _iz, _it = [], []
                    for b in _int_behs:
                        rz = [int(_int_filt[(_int_filt["behaviour"]==b) &
                                             (_int_filt["intervention"]==iv)]["n"].sum()) for iv in _top_ints]
                        rt = [str(n) if n > 0 else "" for n in rz]
                        _iz.append(rz); _it.append(rt)
                    fig_i = go.Figure(go.Heatmap(
                        z=_iz, x=_top_ints, y=_int_behs,
                        text=_it, texttemplate="%{text}",
                        colorscale=[[0,"#f8fafc"],[0.4,"#bfdbfe"],[1,"#1d4ed8"]],
                        showscale=True, colorbar=dict(title="Uses", thickness=12, len=0.7),
                        hovertemplate="<b>%{y}</b><br>%{x}: %{z} times<extra></extra>"
                    ))
                    fig_i.update_layout(
                        height=max(220, len(_int_behs)*48+120),
                        plot_bgcolor="white", paper_bgcolor="white",
                        font=dict(color="#0f172a", size=10, family="Arial"),
                        xaxis=dict(side="top", tickangle=-35, automargin=True),
                        margin=dict(t=90, b=10, l=10, r=80)
                    )
                    st.plotly_chart(fig_i, use_container_width=True)
                    st.caption("Blank = intervention not used for that behaviour. Review whether high-frequency interventions match the identified behaviour function.")
                    st.markdown(
                        "<div style='background:#f8fafc;border-left:4px solid #1A7A7A;"
                        "border-radius:6px;padding:.55rem .9rem;font-size:.82rem;color:#1e293b;'>"
                        "<b>📊 What this shows:</b> "
                        "This chart reveals whether staff responses are matched to the behaviour function. "
                        "For escape-motivated behaviours, demand reduction and offered breaks are appropriate — "
                        "attention-seeking responses (e.g. removing audience) may inadvertently reinforce the behaviour. "
                        "Consistent use of 2–3 well-matched strategies is more effective than "
                        "applying many strategies inconsistently.</div>",
                        unsafe_allow_html=True
                    )

    st.markdown("---")

    st.markdown("### 🔍 Trigger Analysis")
    # (insight summary rendered below after chart data is populated)
    if False:  # placeholder removed
        _ta_top_raw = ""
        _ta_cat_advice = {
            "peer":       "Peer-related triggers indicate the student struggles to regulate in social contexts. "
                          "Structured, supervised peer interactions with explicit social scripts, "
                          "reduced competition, and immediate adult support are recommended. "
                          "Avoid unstructured peer time during high-risk periods.",
            "transition": "Transition triggers indicate difficulty managing changes in activity, "
                          "environment, or expectation. Predictive warnings (5-minute, 2-minute), "
                          "visual schedules, transition objects, and a consistent transition routine "
                          "reduce the cognitive load of change.",
            "instruction":"Instruction/demand triggers suggest the behaviour serves an escape function — "
                          "the student is communicating that the demand feels unmanageable. "
                          "Pre-teaching content, offering choice within the task, and starting at "
                          "mastery level before increasing demand are high-priority strategies.",
            "sensory":    "Sensory triggers indicate the student's nervous system is being overloaded "
                          "before the behaviour occurs. A sensory audit of the environment — "
                          "noise, lighting, crowding, temperature — and proactive sensory breaks "
                          "are the most direct preventive intervention.",
            "engagement": "Engagement triggers (waiting, non-preferred tasks, interrupted activities) "
                          "suggest the student has difficulty with delayed gratification or task demand. "
                          "Break tasks into smaller steps, build in frequent success moments, "
                          "and use visual timers to reduce the ambiguity of waiting.",
            "other":      "Investigate the specific context of this trigger type to identify "
                          "the most appropriate antecedent strategy."
        }
        _ta_insight = (
            f"The most frequent trigger is <b>{_ta_top_lbl}</b>, "
            f"preceding <b>{_ta_top_n} of {len(full_df)} incidents ({_ta_top_pct}%)</b>. "
            + (f"Of these, <b>{_ta_crit_n} resulted in a critical incident</b> — "
               "this trigger–critical pairing requires immediate proactive planning. "
               if _ta_crit_n > 0 else "") +
            "<br><br><b>Intervention principle:</b> "
            "Antecedent-stage intervention — modifying what happens <i>before</i> the trigger — "
            "is consistently more effective than any consequence-based response. "
            "The goal is to reduce or modify the trigger itself, or build the student's capacity "
            "to tolerate it. <br><br>"
            f"<b>Specific guidance for this trigger type:</b> {_ta_cat_advice.get(_ta_cat, _ta_cat_advice["other"])}"
        )
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
            f"padding:.75rem 1.1rem;margin-bottom:.6rem;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
            f"<b>📊 Understanding this chart:</b><br>{_ta_insight}</div>",
            unsafe_allow_html=True
        )
    all_triggers = full_df["antecedent"].value_counts().head(6).index.tolist()
    # Strip section headers and truncate to clinical label only (remove free-text names)
    # Keyword map: free-text ABCH antecedents → canonical clinical trigger labels
    _TRIGGER_KW_MAP = [
        (["noise","loud","sound","auditory","noisy","making noise"],
         "Sensory — noise / auditory input"),
        (["crowd","crowded","too many","busy"],
         "Sensory — crowded environment"),
        (["hungry","food","thirsty","meal","snack","refused food","wouldn't eat"],
         "Sensory — hunger / food refusal"),
        (["medication","no med","without med"],
         "Sensory — medication not taken"),
        (["movement break","couldn't move","unable to move","no break"],
         "Sensory — unable to take movement break"),
        (["bright","light","glare"],
         "Sensory — bright/visual environment"),
        (["peer conflict","peer interaction","conflict with peer","argument with",
           "disagreement with","another student"],
         "Peer — conflict / interaction"),
        (["losing","competition","lost the game","didn't win"],
         "Peer — competition / losing"),
        (["instruction","demand","told to","asked to","required to","refused to clean",
           "refused to help","refused to do","wouldn't follow"],
         "Instructions — following adult direction"),
        (["transition","change","moved to","from one","different activity"],
         "Transition — activity or environment change"),
        (["non-preferred","didn't want to","not wanting to","off device","device"],
         "Transition — from preferred to non-preferred activity"),
        (["wait","waiting","had to wait","queue"],
         "Engagement — having to wait"),
        (["difficult task","hard task","too hard","can't do","maths","literacy","reading"],
         "Engagement — difficult or non-preferred task"),
        (["independent","alone","working by himself","working by herself"],
         "Engagement — working independently"),
        (["injustice","unfair","not fair","perceived"],
         "Other — perceived injustice"),
        (["unstructured","free time","no structure","playground"],
         "Other — unstructured time"),
        (["attention","ignored","staff not attending","shifted attention"],
         "Other — staff attention shifted"),
        (["trt","relief teacher","new teacher","substitute"],
         "Other — relief / unfamiliar teacher"),
    ]

    def _clean_trigger_label(t):
        """Map an antecedent to a clinical label — never show student names or raw narrative."""
        if not t or str(t).startswith("---"): return None
        t = str(t).strip()
        # Structured antecedent (e.g. "Peer - peer conflict/interaction") — strip category prefix
        if " - " in t:
            clean = t[t.find(" - ")+3:]
            # Still check length — some structured ones are fine
            if len(clean) <= 70:
                return clean
            t = clean  # fall through to keyword map for long ones
        # Free-text (ABCH narrative) — map via keywords, never show raw text
        t_low = t.lower()
        for keywords, label in _TRIGGER_KW_MAP:
            if any(kw in t_low for kw in keywords):
                return label
        # Last resort: if > 40 chars it almost certainly contains names or narrative
        if len(t) > 40:
            return "Other — context recorded in incident notes"
        return t
    _trig_labels = [_clean_trigger_label(a) for a in all_triggers]
    _trig_pairs  = [(a, lbl) for a, lbl in zip(all_triggers, _trig_labels) if lbl]
    all_triggers       = [p[0] for p in _trig_pairs]
    _trig_display      = [p[1] for p in _trig_pairs]
    quick_ant_counts = [len(quick_only_df[quick_only_df["antecedent"] == a]) if not quick_only_df.empty else 0 for a in all_triggers]
    crit_ant_counts  = [len(crit_only_df[crit_only_df["antecedent"] == a]) if not crit_only_df.empty else 0 for a in all_triggers]
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(y=_trig_display, x=quick_ant_counts, name='Regular', orientation='h',
        marker=dict(color='#3b82f6'), text=quick_ant_counts, textposition='inside',
        textfont=dict(color='white', size=11, family='Arial Black'),
        hovertemplate='<b>%{y}</b><br>Regular: %{x}<extra></extra>'))
    fig3.add_trace(go.Bar(y=_trig_display, x=crit_ant_counts, name='Critical', orientation='h',
        marker=dict(color='#ef4444'), text=crit_ant_counts, textposition='inside',
        textfont=dict(color='white', size=11, family='Arial Black'),
        hovertemplate='<b>%{y}</b><br>Critical: %{x}<extra></extra>'))
    fig3.update_layout(height=350, barmode='stack', xaxis_title="<b>Incident Count</b>",
        plot_bgcolor='#f8fafc', paper_bgcolor='white', font=dict(color='#0f172a', size=12, family='Arial'),
        xaxis=dict(tickmode='linear', tick0=0, dtick=1, gridcolor='#e2e8f0', showline=True, linewidth=2, linecolor='#cbd5e1'),
        yaxis=dict(showline=True, linewidth=2, linecolor='#cbd5e1'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig3, use_container_width=True)
    # ── Trigger insight (rendered here where all_triggers is defined) ─────
    if all_triggers:
        _ta_top_raw = all_triggers[0]
        _ta_top_lbl = _trig_display[0] if _trig_display else _ta_top_raw
        _ta_top_n   = (quick_ant_counts[0] if quick_ant_counts else 0) + (crit_ant_counts[0] if crit_ant_counts else 0)
        _ta_top_pct = int(_ta_top_n / len(full_df) * 100) if len(full_df) else 0
        _ta_crit_n  = crit_ant_counts[0] if crit_ant_counts else 0
        _ta_cat = ("peer" if "peer" in _ta_top_lbl.lower() else
                   "transition" if "transition" in _ta_top_lbl.lower() else
                   "instruction" if any(kw in _ta_top_lbl.lower() for kw in ["instruction","demand","direction"]) else
                   "sensory" if any(kw in _ta_top_lbl.lower() for kw in ["sensory","noise","hungry","food","auditory"]) else
                   "engagement" if any(kw in _ta_top_lbl.lower() for kw in ["engagement","wait","task"]) else "other")
        _ta_advice = {
            "peer": "Peer-related triggers indicate the student struggles to regulate in social contexts. Structured, supervised peer interactions with explicit social scripts, reduced competition, and immediate adult support are recommended. Avoid unstructured peer time during high-risk periods.",
            "transition": "Transition triggers indicate difficulty managing changes in activity, environment, or expectation. Predictive warnings (5-minute, 2-minute), visual schedules, transition objects, and a consistent transition routine reduce the cognitive load of change.",
            "instruction": "Instruction/demand triggers suggest the behaviour serves an escape function — the student is communicating that the demand feels unmanageable. Pre-teaching content, offering choice within the task, and starting at mastery level before increasing demand are high-priority strategies.",
            "sensory": "Sensory triggers indicate the student's nervous system is being overloaded before the behaviour occurs. A sensory audit of the environment and proactive sensory breaks are the most direct preventive intervention.",
            "engagement": "Engagement triggers (waiting, non-preferred tasks, interrupted activities) suggest difficulty with delayed gratification or task demand. Break tasks into smaller steps, build in frequent success moments, and use visual timers to reduce ambiguity.",
            "other": "Investigate the specific context of this trigger type to identify the most appropriate antecedent strategy.",
        }
        _ta_insight = (
            f"The most frequent trigger is <b>{_ta_top_lbl}</b>, "
            f"preceding <b>{_ta_top_n} of {len(full_df)} incidents ({_ta_top_pct}%)</b>. "
            + (f"Of these, <b>{_ta_crit_n} resulted in a critical incident</b> — "
               "this trigger–critical pairing requires immediate proactive planning. "
               if _ta_crit_n > 0 else "") +
            "<br><br><b>Intervention principle:</b> Antecedent-stage intervention — "
            "modifying what happens <i>before</i> the trigger — is consistently more effective "
            "than any consequence-based response. "
            f"<br><br><b>Specific guidance:</b> {_ta_advice.get(_ta_cat, _ta_advice['other'])}"
        )
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
            f"padding:.75rem 1.1rem;margin-bottom:.6rem;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
            f"<b>📊 Understanding this chart:</b><br>{_ta_insight}</div>",
            unsafe_allow_html=True
        )
    _any_reliable_ant = any((quick_ant_counts[i] + crit_ant_counts[i]) >= 4
                              for i in range(len(all_triggers)))
    if _any_reliable_ant:
        st.markdown("**Escalation Risk by Trigger** *(minimum 4 incidents required for % to display)*")
        for i, (ant, lbl) in enumerate(zip(all_triggers, _trig_display)):
            total = quick_ant_counts[i] + crit_ant_counts[i]
            if total >= 4:
                risk_pct = (crit_ant_counts[i] / total) * 100
                color = "🔴" if risk_pct > 60 else "🟡" if risk_pct > 30 else "🟢"
                st.markdown(f"{color} **{ant}** (n={total}): {risk_pct:.0f}% lead to critical incidents")
            elif total > 0:
                st.markdown(f"• **{ant}** (n={total}): ⚠️ *Insufficient data for reliable rate*")
    else:
        st.caption("⚠️ Trigger escalation rates not shown — minimum 4 incidents per trigger required.")
    st.markdown("---")

    st.markdown("### 📊 Severity Trajectory — Window of Tolerance Analysis")
    st.caption(
        "The Window of Tolerance is the zone of optimal regulation in which a student can engage, "
        "learn, and respond to support. "
        "If a behaviour is being logged, the student is not currently within their window — "
        "behaviours occur in the Coping zone or beyond. "
        "🟡 Levels 1–3 = Coping — behaviour is the student's way of communicating or managing distress. "
        "🔴 Levels 4–5 = Outside window — significant dysregulation. "
        "A critical incident does not automatically mean the student is outside their window."
    )
    fig4 = go.Figure()
    # WoT zones for behaviour incidents:
    # Logged incidents = student is not in green. All start from Coping (yellow).
    # Critical incident alone does NOT mean outside window.
    fig4.add_hrect(y0=0, y1=3.5, fillcolor="#fef9c3", opacity=0.25,
                   annotation_text="Coping zone (severity 1–3) — behaviour present, student managing", annotation_position="top left", line_width=0)
    fig4.add_hrect(y0=3.5, y1=5.5, fillcolor="#fee2e2", opacity=0.25,
                   annotation_text="Outside window (severity 4–5) — significant dysregulation", annotation_position="top left", line_width=0)
    # WoT for incidents: yellow=coping (severity 1–3), red=outside window (severity 4–5)
    sev_colours = {1: '#eab308', 2: '#eab308', 3: '#f97316', 4: '#ef4444', 5: '#7f1d1d'}
    for sev_level in [1, 2, 3, 4, 5]:
        sev_data = full_df[full_df['severity'] == sev_level]
        if len(sev_data) > 0:
            fig4.add_trace(go.Scatter(x=sev_data["date_parsed"], y=sev_data["severity"],
                mode='markers', name=f'Level {sev_level}',
                marker=dict(size=12, color=sev_colours[sev_level], opacity=0.7,
                            line=dict(color='white', width=1.5)),
                hovertemplate='<b>%{x|%a %d/%m}</b><br>Severity: %{y}<extra></extra>'))
    if len(full_df) >= 8:
        z = np.polyfit(range(len(full_df)), full_df["severity"], 1)
        p = np.poly1d(z)
        trend_color = '#22c55e' if z[0] < 0 else '#ef4444'
        fig4.add_trace(go.Scatter(x=full_df["date_parsed"], y=p(range(len(full_df))),
            mode='lines', name=f'Trend (n={len(full_df)})',
            line=dict(color=trend_color, width=2, dash='dash')))
    fig4.update_layout(
        height=420, xaxis_title="<b>Date</b>", yaxis_title="<b>Severity Level</b>",
        yaxis=dict(
            range=[0, 5.5], tickmode='array',
            tickvals=[1, 2, 3, 4, 5],
            ticktext=['severity 1<br>Coping', 'severity 2<br>Coping', 'severity 3<br>Approaching<br>edge',
                      'severity 4<br>Outside<br>window', 'severity 5<br>Crisis'],
            gridcolor='#e2e8f0', showline=True, linewidth=2, linecolor='#cbd5e1'
        ),
        xaxis=dict(showline=True, linewidth=2, linecolor='#cbd5e1', gridcolor='#e2e8f0', tickformat='%a %d/%m'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(color='#0f172a', size=12, family='Arial'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='closest')
    st.plotly_chart(fig4, use_container_width=True)
    if len(full_df) >= 5:
        recent_avg = full_df.tail(5)["severity"].mean()
        early_avg = full_df.head(5)["severity"].mean()
        trend_dir = "improving" if recent_avg < early_avg else "worsening" if recent_avg > early_avg else "stable"
        col1, col2 = st.columns(2)
        with col1: st.metric("Early period average", f"{early_avg:.1f}")
        with col2: st.metric("Recent period average", f"{recent_avg:.1f}")
        _traj_dir    = "reducing" if recent_avg < early_avg else "stable" if recent_avg == early_avg else "increasing"
        _traj_colour = "#16a34a" if _traj_dir == "reducing" else "#64748b" if _traj_dir == "stable" else "#dc2626"
        _traj_diff   = abs(round(recent_avg - early_avg, 1))
        _traj_advice = {
            "reducing": (
                f"Average severity has <b>reduced by {_traj_diff} levels</b> across the data period. "
                "This is a meaningful positive indicator — the student is experiencing less intense "
                "dysregulation episodes over time. "
                "This may reflect improved regulatory capacity, more effective proactive supports, "
                "a stronger relational foundation with key staff, or environmental improvements. "
                "Document specifically what has changed and ensure those conditions are deliberately "
                "maintained — gains in regulation can reverse quickly if supports are reduced or "
                "staff relationships change. "
                "If severity has reduced but frequency remains the same, the student is still "
                "struggling but managing better — sustain current supports and continue monitoring."
            ),
            "stable": (
                f"Average severity has remained <b>stable</b> across the data period ({early_avg:.1f}). "
                "Stability indicates current supports are maintaining the student within a consistent "
                "level of functioning — this is not a deterioration, but it is also not a recovery. "
                "Consider whether the current support intensity matches the student's needs, "
                "or whether a targeted strategy shift is required to move the trajectory downward. "
                "A case review, updated hypothesis, or consultation with an external specialist "
                "may be appropriate if the pattern has been stable across multiple terms."
            ),
            "increasing": (
                f"Average severity has <b>increased by {_traj_diff} levels</b> across the data period. "
                "This is the most significant finding in this analysis — it indicates the student's "
                "episodes are becoming more intense over time, which signals that current supports "
                "are insufficient and escalation pathways need urgent review. "
                "Recommended immediate actions: schedule a case conference with all key staff, "
                "update the safety plan, conduct a sensory and environmental audit, "
                "review staffing consistency and relational supports, "
                "and consider referral for additional specialist assessment. "
                "Also check whether any external life stressors (family changes, transitions, "
                "health factors) are contributing to the increase."
            )
        }
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid {_traj_colour};border-radius:8px;"
            f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
            f"<b>📊 Understanding this chart:</b><br>"
            f"{_traj_advice[_traj_dir]}<br><br>"
            "<b>Reading the chart:</b> Each dot represents one incident, positioned on the date it occurred "
            "and the severity level recorded. The dashed trend line shows the overall direction. "
            "Yellow zone = Coping (severity 1–3, behaviour present but student managing). "
            "Red zone = Outside window (severity 4–5, significant dysregulation). "
            "Any dot in the red zone marks an episode that required intensive de-escalation "
            "and post-incident relational repair before the student could re-engage with learning.</div>",
            unsafe_allow_html=True
        )
        if recent_avg < early_avg:
            st.caption("📉 Severity reducing over time — positive indicator.")
        elif recent_avg == early_avg:
            st.caption("➡️ Severity stable over the observed period.")
        else:
            st.caption("📊 Severity has increased in recent incidents — review proactive supports.")
    st.markdown("---")

    st.markdown("### 📍 Location Hotspots")
    all_locations = full_df["location"].value_counts().head(6).index.tolist()
    quick_loc_counts = [len(quick_only_df[quick_only_df["location"] == loc]) if not quick_only_df.empty else 0 for loc in all_locations]
    crit_loc_counts  = [len(crit_only_df[crit_only_df["location"] == loc]) if not crit_only_df.empty else 0 for loc in all_locations]
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(y=all_locations, x=quick_loc_counts, name='Regular', orientation='h',
        marker=dict(color='#3b82f6'), text=quick_loc_counts, textposition='inside',
        textfont=dict(color='white', size=11, family='Arial Black')))
    fig5.add_trace(go.Bar(y=all_locations, x=crit_loc_counts, name='Critical', orientation='h',
        marker=dict(color='#ef4444'), text=crit_loc_counts, textposition='inside',
        textfont=dict(color='white', size=11, family='Arial Black')))
    fig5.update_layout(height=350, barmode='stack', xaxis_title="<b>Incident Count</b>",
        plot_bgcolor='#f8fafc', paper_bgcolor='white', font=dict(color='#0f172a', size=12, family='Arial'),
        xaxis=dict(tickmode='linear', tick0=0, dtick=1, gridcolor='#e2e8f0', showline=True, linewidth=2, linecolor='#cbd5e1'),
        yaxis=dict(showline=True, linewidth=2, linecolor='#cbd5e1'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig5, use_container_width=True)
    if all_locations:
        _lh_top = normalise_location(all_locations[0])
        _lh_top_n = quick_loc_counts[0] + crit_loc_counts[0]
        _lh_pct = int(_lh_top_n / len(full_df) * 100) if len(full_df) else 0
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;"
            f"border-radius:6px;padding:.55rem .9rem;font-size:.82rem;color:#1e293b;'>"
            f"<b>📊 What this shows:</b> "
            f"<b>{_lh_top}</b> is the highest-frequency incident location ({_lh_pct}% of all incidents). "
            "This may reflect specific environmental conditions — crowding, noise levels, "
            "supervision ratios, or transition demands — that warrant targeted modification. "
            "Where a single location dominates, environmental audit and proactive supervision "
            "strategies for that space should be the first priority.</div>",
            unsafe_allow_html=True
        )
    st.markdown("---")

    st.markdown("### ⏰ Time of Day Patterns")
    SESSION_DISPLAY = {
        'Morning':   'Morning<br>(Before 11:00am)',
        'Middle':    'Middle of day<br>(11:00am – 1:30pm)',
        'Afternoon': 'Afternoon<br>(1:31pm – 2:45pm)',
    }
    session_order = ['Morning', 'Middle', 'Afternoon']
    quick_session_counts = [len(quick_only_df[quick_only_df["session"] == s]) if not quick_only_df.empty and 'session' in quick_only_df.columns else 0 for s in session_order]
    crit_session_counts  = [len(crit_only_df[crit_only_df["session"] == s]) if not crit_only_df.empty and 'session' in crit_only_df.columns else 0 for s in session_order]
    display_labels = [SESSION_DISPLAY[s] for s in session_order]
    fig6 = go.Figure()
    fig6.add_trace(go.Bar(x=display_labels, y=quick_session_counts, name='Regular',
        marker=dict(color='#3b82f6'), text=quick_session_counts, textposition='inside',
        textfont=dict(color='white', size=12, family='Arial Black')))
    fig6.add_trace(go.Bar(x=display_labels, y=crit_session_counts, name='Critical',
        marker=dict(color='#ef4444'), text=crit_session_counts, textposition='inside',
        textfont=dict(color='white', size=12, family='Arial Black')))
    fig6.update_layout(height=380, barmode='stack',
        xaxis_title="<b>Time of Day</b>", yaxis_title="<b>Number of incidents</b>",
        plot_bgcolor='#f8fafc', paper_bgcolor='white',
        font=dict(color='#0f172a', size=12, family='Arial'),
        yaxis=dict(tickmode='linear', tick0=0, dtick=1, gridcolor='#e2e8f0', showline=True, linewidth=2, linecolor='#cbd5e1'),
        xaxis=dict(showline=True, linewidth=2, linecolor='#cbd5e1', tickfont=dict(size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig6, use_container_width=True)
    _tot_ses = {s: (quick_session_counts[i] + crit_session_counts[i]) for i, s in enumerate(session_order)}
    _peak_ses = max(_tot_ses, key=_tot_ses.get)
    _peak_ses_n = _tot_ses[_peak_ses]
    _peak_ses_pct = int(_peak_ses_n / len(full_df) * 100) if len(full_df) else 0
    _ses_display_map = {"Morning":"morning","Middle":"middle of day","Afternoon":"afternoon"}
    st.markdown(
        f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;"
        f"border-radius:6px;padding:.55rem .9rem;font-size:.82rem;color:#1e293b;'>"
        f"<b>📊 What this shows:</b> "
        f"Incidents peak in the <b>{_ses_display_map[_peak_ses]}</b> "
        f"({_peak_ses_pct}% of all incidents). "
        "Scheduling structured regulation activities, check-ins, and predictable routines "
        "just before this window opens is the single highest-leverage proactive strategy. "
        "If the student is on a part-time schedule, note that absences during certain sessions "
        "will affect these counts.</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.markdown("### 📆 Day of Week Patterns")
    _school_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_counts = full_df["day_of_week"].value_counts().reindex(_school_days, fill_value=0)
    _total_school = int(day_counts.sum())
    if _total_school >= 3:
        _day_avg = _total_school / 5
        _day_colours = ["#ef4444" if v >= _day_avg * 1.5 else "#3b82f6" if v >= _day_avg * 0.8 else "#94a3b8"
                        for v in day_counts.values]
        fig7 = go.Figure()
        fig7.add_trace(go.Bar(
            x=day_counts.index, y=day_counts.values,
            marker=dict(color=_day_colours, line=dict(color="white", width=1)),
            text=day_counts.values, textposition="outside",
            textfont=dict(size=12, color="#1e293b"),
            hovertemplate="<b>%{x}</b><br>%{y} incident(s)<extra></extra>"
        ))
        fig7.add_hline(y=_day_avg, line_dash="dot", line_color="#94a3b8", line_width=1.5,
                       annotation_text=f"Daily avg: {_day_avg:.1f}",
                       annotation_position="right", annotation_font_size=10)
        fig7.update_layout(
            height=300, showlegend=False,
            yaxis_title="<b>Total incidents</b>",
            plot_bgcolor="#f8fafc", paper_bgcolor="white",
            font=dict(color="#334155", size=11),
            yaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                       showline=True, linewidth=2, linecolor="#cbd5e1"),
            xaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1"),
            margin=dict(t=20, b=10)
        )
        st.plotly_chart(fig7, use_container_width=True)
        st.caption("🔴 Red = significantly above average  ·  🔵 Blue = near average  ·  ⚫ Grey = below average  ·  Dashed line = daily mean")
        _dow_peak = day_counts.idxmax()
        _dow_peak_n = int(day_counts.max())
        _dow_has_data = day_counts[day_counts > 0]
        _dow_low = _dow_has_data.idxmin() if len(_dow_has_data) > 1 else None
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;"
            f"border-radius:6px;padding:.55rem .9rem;font-size:.82rem;color:#1e293b;'>"
            f"<b>📊 What this shows:</b> "
            f"<b>{_dow_peak}</b> has the highest incident count ({_dow_peak_n}). "
            + (f"<b>{_dow_low}</b> has the fewest — consider what differs about that day's "
               "structure, staffing, or routine and replicate those conditions on other days. "
               if _dow_low and _dow_low != _dow_peak else "") +
            "Day-of-week patterns often point to timetable-specific triggers — "
            "a particular subject, a staff change, a scheduled transition, or a specific peer group "
            "on that day. The recommended action is to review the timetable for the high-incident day: "
            "what subjects, staff, peers, or transitions are unique to that day? "
            "Conversely, if one day consistently has no or few incidents, identify what is different "
            "about that day's structure and replicate it.</div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Day of week chart requires at least 3 recorded incidents across school days.")
    st.markdown("---")

    # ── Derived metrics (used in multiple sections below) ─────────────────────
    top_beh     = full_df["behaviour_type"].mode()[0] if len(full_df) > 0 else "Unknown"
    top_ant     = full_df["antecedent"].mode()[0] if len(full_df) > 0 else "Unknown"
    top_loc     = full_df["location"].mode()[0] if len(full_df) > 0 else "Unknown"
    top_session = full_df["session"].mode()[0] if len(full_df) > 0 else "Unknown"
    top_beh_clinical = get_clinical_behaviour(top_beh)

    recent = full_df.tail(7)
    risk_score = min(100, int(
        (len(recent) / 7 * 10) +
        (recent["severity"].mean() * 8) +
        (len(full_df[full_df["incident_type"] == "Critical"]) / len(full_df) * 50)
    ))
    risk_level = "LOW" if risk_score < 30 else "MODERATE" if risk_score < 60 else "HIGH"
    risk_color = "#10b981" if risk_level == "LOW" else "#f59e0b" if risk_level == "MODERATE" else "#ef4444"

    # ══════════════════════════════════════════════════════════════════════════
    # CLINICAL HYPOTHESIS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Window of Tolerance reference note (diagram removed) ────────────────
    st.info(
        "🪟 **Window of Tolerance:** All logged incidents occur in the Coping zone (yellow/orange) or Outside window (red). Green = within window — on task and engaged, no incidents. When a behaviour is logged, the student is managing distress (Coping) or dysregulated (Outside window). A critical incident does not automatically mean outside the window."
    )
    st.markdown("---")
    st.markdown("### 🔬 Behaviour Analysis & Functional Hypothesis")
    hyp_data = generate_strong_clinical_hypothesis(
        full_df, top_ant, top_beh, top_loc, top_session, student["name"]
    )
    st.markdown(
        "<div style='background:#f0fdf4;border:1.5px solid #16a34a;border-radius:10px;"
        "padding:1rem 1.25rem;margin-bottom:1rem;'>"
        "<div style='font-weight:700;color:#15803d;font-size:1rem;margin-bottom:.5rem;'>"
        "📋 Functional Hypothesis Statement</div>"
        f"<p style='color:#1e293b;font-size:.88rem;line-height:1.65;margin:0;'>{hyp_data['summary']}</p>"
        "</div>",
        unsafe_allow_html=True
    )

    detail = hyp_data["detail"]
    dc1, dc2, dc3 = st.columns(3)
    def _card(col, title, val, bg, border, tc):
        col.markdown(
            f"<div style='background:{bg};border-left:3px solid {border};"
            f"padding:.55rem .75rem;border-radius:0 6px 6px 0;height:100%;'>"
            f"<div style='font-size:.7rem;font-weight:700;color:{tc};text-transform:uppercase;"
            f"letter-spacing:.04em;'>{title}</div>"
            f"<div style='font-size:.84rem;color:#1e293b;margin-top:.2rem;line-height:1.4;'>{val}</div></div>",
            unsafe_allow_html=True
        )
    _card(dc1, "Behavioural Function",    detail.get("Behavioural Function","—"),    "#eff6ff","#3b82f6","#1d4ed8")
    _card(dc2, "BSEM Domain Priority",    detail.get("BSEM Domain Priority","—"),    "#fef9c3","#eab308","#a16207")
    _card(dc3, "Incidents Logged",        f"{len(full_df)} total",                    "#f1f5f9","#64748b","#475569")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    dc4, dc5, dc6 = st.columns(3)
    _card(dc4, "Behaviour Label",  top_beh_clinical,                          "#f0fdf4","#22c55e","#15803d")
    _card(dc5, "Primary Antecedent",        detail.get("Primary Antecedent","—"),       "#fdf4ff","#8b5cf6","#7c3aed")
    _card(dc6, "Risk Indicator",            detail.get("Risk Indicator","—"),           "#fff7ed","#f97316","#c2410c")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    _considerations = build_considerations(full_df, top_ant, top_loc, top_session)
    with st.expander("🤔 Considerations — before settling on this hypothesis"):
        st.caption(
            "Alternative or structural explanations worth ruling out before treating the "
            "pattern above as purely behavioural. Worth reading with SMART's core reminder in "
            "mind: behaviour is communication from the nervous system, not a considered choice "
            "in the moment — regulate and relate before reasoning about it."
        )
        for _c in _considerations:
            st.markdown(f"- {_c}")

    st.markdown("---")
    st.markdown("### 🪟 Window of Tolerance — Draft from This Student's Data")
    render_window_of_tolerance_table(full_df, student_id=student_id)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # ANTECEDENT CATEGORY BREAKDOWN CHART
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📂 Antecedent Category Analysis")
    st.caption("Incidents grouped by antecedent category to identify the primary trigger domain.")

    full_df["_ant_cat"] = full_df["antecedent"].apply(categorize_antecedent)
    quick_cat  = full_df[full_df.get("incident_type", "Quick") == "Quick"]["_ant_cat"].dropna() if "incident_type" in full_df.columns else full_df["_ant_cat"].dropna()
    crit_cat   = full_df[full_df.get("incident_type", "Quick") == "Critical"]["_ant_cat"].dropna() if "incident_type" in full_df.columns else pd.Series(dtype=str)

    cat_order  = ["Peer","Transition","Instructions","Engagement","Sensory","Other"]
    cat_colors = {"Peer":"#3b82f6","Transition":"#f59e0b","Instructions":"#ef4444",
                  "Engagement":"#8b5cf6","Sensory":"#10b981","Other":"#64748b"}

    fig_cat = go.Figure()
    q_counts = quick_cat.value_counts() if len(quick_cat) else pd.Series(dtype=int)
    c_counts = crit_cat.value_counts()  if len(crit_cat)  else pd.Series(dtype=int)
    for cat in cat_order:
        qv = int(q_counts.get(cat, 0))
        cv = int(c_counts.get(cat, 0))
        if qv + cv == 0: continue
        fig_cat.add_trace(go.Bar(x=[cat], y=[qv], name="Regular",
            marker=dict(color=cat_colors[cat], opacity=0.7),
            text=[qv] if qv else [""], textposition="inside",
            textfont=dict(color="white", size=10), showlegend=(cat == cat_order[0])))
        fig_cat.add_trace(go.Bar(x=[cat], y=[cv], name="Critical",
            marker=dict(color=cat_colors[cat]),
            text=[cv] if cv else [""], textposition="inside",
            textfont=dict(color="white", size=10, family="Arial Black"),
            showlegend=(cat == cat_order[0])))
    fig_cat.update_layout(
        height=340, barmode="stack",
        xaxis_title="<b>Antecedent Category</b>", yaxis_title="<b>Incidents</b>",
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        font=dict(color="#0f172a", size=12, family="Arial"),
        yaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                   showline=True, linewidth=2, linecolor="#cbd5e1"),
        xaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=20, b=10)
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    all_cats = pd.concat([quick_cat, crit_cat]) if len(crit_cat) else quick_cat
    if len(all_cats):
        top_cat     = all_cats.value_counts().index[0]
        top_cat_pct = int(all_cats.value_counts().iloc[0] / len(all_cats) * 100)
        st.caption(f"📌 **{top_cat}** is the dominant antecedent category ({top_cat_pct}% of all incidents) — "
                   f"this is the highest-priority domain for proactive, antecedent-stage intervention.")

    render_combined_patterns(full_df)

    # Hypothesis function bar
    st.markdown("#### 🎯 Behavioural Function Distribution")
    if "hypothesis_function" in full_df.columns:
        fn_counts = full_df["hypothesis_function"].dropna().value_counts()
        if not fn_counts.empty:
            fig_fn = go.Figure()
            fig_fn.add_trace(go.Bar(
                y=list(fn_counts.index), x=list(fn_counts.values), orientation="h",
                marker=dict(color=["#3b82f6","#ef4444","#10b981","#f59e0b","#8b5cf6"][:len(fn_counts)]),
                text=list(fn_counts.values), textposition="outside",
                textfont=dict(size=11, family="Arial Black", color="#1e293b")
            ))
            fig_fn.update_layout(
                height=max(180, len(fn_counts)*55), showlegend=False,
                xaxis_title="<b>Incidents</b>",
                plot_bgcolor="#f8fafc", paper_bgcolor="white",
                font=dict(color="#0f172a", size=11, family="Arial"),
                xaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor="#e2e8f0",
                           showline=True, linewidth=2, linecolor="#cbd5e1"),
                yaxis=dict(showline=True, linewidth=2, linecolor="#cbd5e1", automargin=True),
                margin=dict(t=10, b=10, l=10, r=30)
            )
            st.plotly_chart(fig_fn, use_container_width=True)

    st.markdown("---")

    # ── Derive sensory-overview flags used by the Teaching Lens section below ──
    # (fixes NameError: these were referenced but never computed)
    _n_sensory_ants   = int((full_df["_ant_cat"] == "Sensory").sum()) if "_ant_cat" in full_df.columns else 0
    _sensory_prominent = len(full_df) > 0 and (_n_sensory_ants / len(full_df)) >= 0.2
    _has_sensory  = bool(_so_data)
    _so_recs       = _so_data.get("recommendations", []) if _so_data else []
    _so_seeking    = _so_data.get("sensory_seeking", []) if _so_data else []
    _so_avoiding   = _so_data.get("sensory_avoiding", []) if _so_data else []
    _so_strategies = _so_data.get("regulation_strategies", []) if _so_data else []
    _so_triggers   = _so_data.get("triggers", []) if _so_data else []

    # ══════════════════════════════════════════════════════════════════════════
    # SUPPORTS FOR TRANSITION TO A MAINSTREAM SETTING
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1A7A7A 0%,#134e4e 100%);"
        "border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:0.7rem;"
        "box-shadow:0 4px 14px rgba(19,78,78,0.25);'>"
        "<span style='color:white;font-size:1.15rem;font-weight:700;'>🎒 Supports for Transition to a Mainstream Setting</span><br>"
        "<span style='color:#d1fae5;font-size:0.85rem;'>BSEM-informed strategies (Body · Relationship · Stamina · Engagement · Character), "
        "matched to this student's actual pattern, framed for handover to a receiving school. "
        "Click a strategy for why it fits and how to implement it.</span></div>",
        unsafe_allow_html=True,
    )
    st.caption("SMART's core reminder: regulate before you reason — these strategies work by supporting "
               "regulation ahead of demand, not by correcting after the fact.")
    _bsem_key = f"bsem_analysis_{student_id}"
    _bsem_sig = f"{top_beh}|{top_ant}|{top_loc}|{top_session}"
    if (st.session_state.get(f"{_bsem_key}_sig") != _bsem_sig
            or st.button("🔄 Regenerate", key=f"{_bsem_key}_regen")):
        with st.spinner("Drawing up BSEM-aligned recommendations..."):
            st.session_state[_bsem_key] = build_bsem_recommendations(
                full_df, top_beh, top_ant, top_loc, top_session,
                student["name"], context="analysis")
            st.session_state[f"{_bsem_key}_sig"] = _bsem_sig
    _bsem_items = st.session_state.get(_bsem_key, [])
    if _bsem_items:
        render_bsem_recommendations(_bsem_items, key_prefix=_bsem_key)
    else:
        st.info("Not enough antecedent data yet to generate recommendations.")
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # TEACHING LENS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎓 Teaching Lens — Recommendations")
    st.caption("Strategies for educators to embed within the learning environment and curriculum delivery. "
               "Framed on SMART's core principle: a dysregulated (Regulate-stage) brain can't yet learn or reason — "
               "these strategies work by keeping the student regulated before demand increases, not after.")

    tc1, tc2 = st.columns(2)
    with tc1:
        _tc1_sensory = "".join(
            f"<li><strong>Sensory recommendation:</strong> {r}</li>"
            for r in _so_recs[:3]
        ) if _has_sensory and _so_recs else ""
        st.markdown(
            "<div style='background:#eff6ff;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #bfdbfe;height:100%;'><div style='font-weight:700;color:#1d4ed8;"
            "font-size:.93rem;margin-bottom:.6rem;'>📚 Curriculum & Pedagogy</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            f"<li>Deliver <strong>clear, single-step instructions</strong> supported by visual cues — avoid multi-part verbal directives, particularly during the {top_session} session</li>"
            f"<li><strong>Scaffold tasks</strong> into small, achievable components with explicit success criteria before activities preceded by <em>{top_ant[:55]}...</em>-type triggers</li>"
            "<li>Embed <strong>student choice</strong> within the curriculum (topic, modality, sequence) to maintain agency and reduce escape-motivated responding</li>"
            "<li>Apply <strong>strength-based entry points</strong> — begin all tasks at mastery level before incrementally increasing demand</li>"
            "<li>Use <strong>pre-teaching and content priming</strong> before transitions or cognitively demanding activities</li>"
            "<li>Implement <strong>flexible, low-stakes assessment</strong> to reduce evaluation-related anxiety as a trigger</li>"
            + _tc1_sensory +
            "</ul></div>",
            unsafe_allow_html=True
        )
    with tc2:
        st.markdown(
            "<div style='background:#f0fdf4;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #bbf7d0;height:100%;'>"
            "<div style='font-weight:700;color:#15803d;font-size:.93rem;margin-bottom:.6rem;'>"
            "🗂️ Classroom Structure & Routines</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            f"<li>Display a <strong>visual daily schedule</strong> with explicit markers for session changes — review it collaboratively at the start of the {top_session} session</li>"
            "<li>Provide <strong>2-minute transition warnings</strong> before every activity change, using both verbal and visual cues</li>"
            f"<li><strong>Strategic seating in {top_loc}</strong> — proximity to the support adult, away from high-traffic zones and peer conflict areas</li>"
            "<li>Explicitly teach and practise a <strong>Help Card / Break Card system</strong> during calm, low-demand moments</li>"
            "<li>Use <strong>errorless learning techniques</strong> — engineer early task success before fading support</li>"
            "<li>Deliver all corrections <strong>privately and with dignity</strong> — provide face-saving exit options to avoid public escalation</li>"
            "</ul></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#fef9c3;border-radius:10px;padding:.85rem 1.1rem;"
        "border:1px solid #fde68a;margin-top:.35rem;'>"
        "<div style='font-weight:700;color:#92400e;font-size:.93rem;margin-bottom:.4rem;'>📈 SMART Teaching Goal</div>"
        f"<p style='margin:0;font-size:.84rem;color:#1e293b;line-height:1.6;'>"
        f"Over the next <strong>5 school weeks</strong>, {student['name']} will independently use a help-seeking "
        f"strategy (Help Card or calm verbal request) in <strong>4 out of 5 observed opportunities</strong> "
        f"during the {top_session} session, as measured by a daily staff tally sheet. "
        f"Baseline data will be collected in Week 1 before intervention commences in Week 2. "
        f"Review at Week 3 (mid-point) and Week 5 (end-point) against the baseline frequency of {top_beh_clinical.lower()}."
        f"</p></div>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # SUPPORT LENS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🤝 Support Lens — Recommendations")
    st.caption("Therapeutic and behavioural support strategies for the care team, allied health, and leadership. "
               "Sequenced on SMART's Regulate → Relate → Reason principle — co-regulation and safety come first; "
               "debrief, repair, and skill-teaching only once the student is genuinely calm.")

    sc1, sc2 = st.columns(2)
    with sc1:
        _sc1_seeking_items = "".join(
            f"<li><strong>Sensory need (profile):</strong> {s} — provide proactively before high-risk periods</li>"
            for s in _so_seeking[:2]
        ) if _has_sensory and _so_seeking else ""
        _sc1_strat_items = "".join(
            f"<li><strong>Regulation strategy (profile):</strong> {s}</li>"
            for s in _so_strategies[:2]
        ) if _has_sensory and _so_strategies else ""
        st.markdown(
            "<div style='background:#fdf4ff;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #e9d5ff;height:100%;'><div style='font-weight:700;color:#7c3aed;"
            "font-size:.93rem;margin-bottom:.6rem;'>🧠 Regulation & Sensory Strategies</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            f"<li><strong>Sensory diet</strong> incorporated before the {top_session} session — movement break, heavy work activity, or proprioceptive input to prepare the nervous system</li>"
            "<li><strong>Co-regulation with a key adult</strong> — calm, attuned, predictable adult presence; CPI Supportive Stance (low, slow, sideways) as the default posture</li>"
            f"<li>Develop a personalised <strong>Window of Tolerance profile</strong> for {student['name']} — document early warning signs, escalation cues, and effective de-escalation strategies</li>"
            "<li><strong>Teach and embed regulation tools</strong> during calm states; cue their use proactively at early warning signs — before escalation occurs</li>"
            "<li>Monitor <strong>medication timing</strong> if relevant and note correlations with incident frequency</li>"
            + _sc1_seeking_items + _sc1_strat_items +
            "</ul></div>",
            unsafe_allow_html=True
        )
    with sc2:
        st.markdown(
            "<div style='background:#fff7ed;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #fed7aa;height:100%;'>"
            "<div style='font-weight:700;color:#c2410c;font-size:.93rem;margin-bottom:.6rem;'>"
            "🛡️ Antecedent Prevention & Environment</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            f"<li><strong>Environmental audit of {top_loc}</strong> — assess and modify sensory load (noise, lighting, crowding) and spatial arrangement to reduce ambient triggers</li>"
            "<li><strong>Pre-correction</strong> immediately before known high-risk contexts — brief, calm reminder of expectations and available supports prior to entering the trigger environment</li>"
            f"<li><strong>Functional Communication Training (FCT)</strong> — teach an efficient, socially appropriate replacement behaviour that serves the same function as {top_beh_clinical.lower()}, explicitly and systematically</li>"
            "<li><strong>Structured peer interaction protocols</strong> — pre-assign groupings and roles where peer triggers are identified; avoid unstructured proximity</li>"
            "<li>Develop a <strong>Crisis Safety Plan</strong> with Critical Incident protocols, designated staff roles, de-escalation sequence, and post-incident restorative repair procedure</li>"
            "</ul></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    sc3, sc4 = st.columns(2)
    with sc3:
        st.markdown(
            "<div style='background:#fef2f2;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #fecaca;height:100%;'>"
            "<div style='font-weight:700;color:#dc2626;font-size:.93rem;margin-bottom:.6rem;'>"
            "🔄 Post-Incident Repair & Restoration</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            "<li><strong>Restore the relationship before re-engaging</strong> with academic demands — never return to learning tasks while the student remains dysregulated</li>"
            "<li>Conduct a <strong>brief, non-punitive restorative conversation</strong> once fully regulated — focus on what happened, who was affected, and how to repair</li>"
            "<li>Complete a structured <strong>staff debrief</strong> after every Critical Incident — review antecedents, early warning signs, and response effectiveness</li>"
            "<li>Maintain <strong>proactive, strengths-focused communication</strong> with parent/carer — not solely incident-driven contact</li>"
            "</ul></div>",
            unsafe_allow_html=True
        )
    with sc4:
        review_window = "2 weeks" if risk_level == "HIGH" else "4 weeks" if risk_level == "MODERATE" else "6 weeks"
        st.markdown(
            "<div style='background:#f0fdf4;border-radius:10px;padding:1rem 1.1rem;"
            "border:1px solid #bbf7d0;height:100%;'>"
            "<div style='font-weight:700;color:#15803d;font-size:.93rem;margin-bottom:.6rem;'>"
            "📅 Case Management</div>"
            "<ul style='margin:0;padding-left:1.2rem;font-size:.84rem;color:#1e293b;line-height:1.85;'>"
            f"<li>Schedule a <strong>formal case review within {review_window}</strong> — review BAP, update function-based strategies, and set new SMART goals based on current data trends</li>"
            "<li>Consult with relevant <strong>allied health professionals</strong> (OT, Speech Pathologist, Psychologist) if sensory, communication, or mental health factors are contributing</li>"
            f"<li>Ensure <strong>all staff working with {student['name']}</strong> are fully briefed on the current BAP and implementing strategies consistently across all settings</li>"
            "<li>Review and formally update the <strong>Behaviour Support Plan</strong> at minimum each term, or following any critical incident</li>"
            "</ul></div>",
            unsafe_allow_html=True
        )

    # ── Sensory recommendations panel ─────────────────────────────────────
    if _has_sensory:
        st.markdown(
            "<div style='background:#f0f9ff;border:2px solid #0284c7;border-radius:12px;"
            "padding:1rem 1.25rem;margin:.5rem 0;'>"
            "<div style='font-weight:700;color:#0369a1;font-size:1rem;margin-bottom:.6rem;'>"
            "🧠 Sensory Profile — Integrated Recommendations</div>"
            f"<p style='font-size:.84rem;color:#1e293b;margin-bottom:.5rem;line-height:1.6;'>{_so_summary}</p>"
            "</div>",
            unsafe_allow_html=True
        )
        _sp1, _sp2 = st.columns(2)
        with _sp1:
            _avoiding_li = "".join(
                f"<li>Minimise/modify <strong>{a}</strong> in the learning environment</li>" for a in _so_avoiding[:4]
            ) if _so_avoiding else "<li>No specific avoidances recorded in profile</li>"
            st.markdown(
                "<div style='background:#fef9c3;border-radius:8px;padding:.85rem 1rem;"
                "border:1px solid #fde68a;height:100%;'><div style='font-weight:700;color:#92400e;"
                "font-size:.88rem;margin-bottom:.5rem;'>🛡️ Sensory Sensitivities — Reduce/Modify</div>"
                "<ul style='margin:0;padding-left:1.1rem;font-size:.83rem;color:#1e293b;line-height:1.8;'>" + _avoiding_li + "</ul></div>",
                unsafe_allow_html=True
            )
        with _sp2:
            _seeking_li = "".join(
                f"<li>Provide <strong>{s}</strong> proactively — schedule before high-risk periods</li>" for s in _so_seeking[:4]
            ) if _so_seeking else "<li>No specific seeking needs recorded in profile</li>"
            st.markdown(
                "<div style='background:#f0fdf4;border-radius:8px;padding:.85rem 1rem;"
                "border:1px solid #bbf7d0;height:100%;'><div style='font-weight:700;color:#15803d;"
                "font-size:.88rem;margin-bottom:.5rem;'>✅ Sensory Needs — Provide Proactively</div>"
                "<ul style='margin:0;padding-left:1.1rem;font-size:.83rem;color:#1e293b;line-height:1.8;'>" + _seeking_li + "</ul></div>",
                unsafe_allow_html=True
            )
        if _so_triggers:
            st.markdown(
                "<div style='background:#fff7ed;border-radius:8px;padding:.85rem 1rem;"
                "border:1px solid #fed7aa;margin-top:.5rem;'><div style='font-weight:700;color:#c2410c;"
                "font-size:.88rem;margin-bottom:.5rem;'>⚡ Sensory Triggers — Antecedent Priorities</div>"
                "<ul style='margin:0;padding-left:1.1rem;font-size:.83rem;color:#1e293b;line-height:1.8;'>" +
                "".join(f"<li><strong>{t}</strong> — pre-empt or modify before high-risk periods</li>" for t in _so_triggers[:5]) +
                "</ul></div>",
                unsafe_allow_html=True
            )
        if _so_recs:
            st.markdown(
                "<div style='background:#f8fafc;border-radius:8px;padding:.85rem 1rem;"
                "border:1px solid #e2e8f0;margin-top:.5rem;'><div style='font-weight:700;color:#1A7A7A;"
                "font-size:.88rem;margin-bottom:.5rem;'>📚 All Classroom Recommendations (from Sensory Profile)</div>"
                "<ul style='margin:0;padding-left:1.1rem;font-size:.83rem;color:#1e293b;line-height:1.8;'>" +
                "".join(f"<li>{r}</li>" for r in _so_recs) + "</ul></div>",
                unsafe_allow_html=True
            )
    elif _sensory_prominent and not _has_sensory:
        st.markdown(
            "<div style='background:#fff7ed;border:2px solid #f97316;border-radius:12px;"
            "padding:1rem 1.25rem;margin:.5rem 0;'>"
            "<div style='font-weight:700;color:#c2410c;font-size:1rem;margin-bottom:.5rem;'>"
            "⚡ Recommendation: Complete a Sensory Overview</div>"
            f"<p style='font-size:.84rem;color:#1e293b;line-height:1.65;margin:0;'>"
            f"<b>{_n_sensory_ants} of {len(full_df)} incidents ({int(_n_sensory_ants/max(len(full_df),1)*100)}%)</b> "
            "were preceded by antecedents with a sensory dimension (noise, hunger, crowding, movement, sensory input). "
            "Sensory processing is likely playing a significant role in this student's behaviour pattern. "
            "<br><br><strong>Recommended action:</strong> Request a formal Sensory Overview or Sensory Profile "
            "from an Occupational Therapist. This will identify specific sensory needs, sensitivities, and "
            "regulation strategies that can be embedded directly into the teaching and support approach. "
            "Once completed, upload the document using the <strong>🧠 Sensory Overview</strong> expander "
            "at the top of this analysis page — the recommendations here will automatically update.</p></div>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    render_strategy_trials(student, full_df)
    st.markdown("---")

    st.markdown("### 🧭 Demand-Avoidant Presentations — Perceived Choice Approach")
    render_demand_avoidance_section(full_df)
    st.markdown("---")

    st.markdown("### 👁️ View, Edit & Print an Incident")
    st.caption("Look up any single incident for this student, correct details (e.g. a wrong date), and print or download a summary.")

    _ve_reg  = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    _ve_crit = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]
    _ve_combined = []
    for i in _ve_reg:
        _rdate = i.get("date", "")
        _flag = "⚠️ NO DATE  " if not _rdate else ""
        _ve_combined.append({
            "id": i["id"], "type": "regular", "date": _rdate,
            "label": f"{_flag}[REGULAR]  {_rdate or '(none)'}  {i.get('time','')[:5]}  |  "
                     f"{i.get('behaviour_type','—')}  |  Severity {i.get('severity','?')}",
        })
    for c in _ve_crit:
        _primary_lbl = c.get("ABCH_primary", {}) if isinstance(c.get("ABCH_primary"), dict) else {}
        _created = (c.get("created_at", "") or "")[:10]
        _flag = "⚠️ NO DATE  " if not _created else ""
        _ve_combined.append({
            "id": c["id"], "type": "critical", "date": _created,
            "label": f"{_flag}[CRITICAL]  {_created or '(none)'}  {_primary_lbl.get('time','')[:5]}  |  "
                     f"{_primary_lbl.get('behaviour','Behaviour not recorded')[:50]}",
        })

    if not _ve_combined:
        st.info("No incidents on record for this student yet.")
    else:
        _ve_sorted = sorted(_ve_combined, key=lambda x: x["date"], reverse=True)
        _ve_options = {item["label"]: item for item in _ve_sorted}
        _ve_selected_label = st.selectbox(
            f"Select incident to view/edit ({len(_ve_combined)} total)",
            list(_ve_options.keys()), key="view_edit_incident_select",
        )
        _ve_item = _ve_options[_ve_selected_label]
        _ve_id, _ve_type = _ve_item["id"], _ve_item["type"]
        _ve_record = next((i for i in _ve_reg if i["id"] == _ve_id), None) if _ve_type == "regular" \
            else next((c for c in _ve_crit if c["id"] == _ve_id), None)

        _ve_print_data = {}

        if _ve_record and _ve_type == "regular":
            _beh_opts = [b for b in BEHAVIOUR_TYPES if not b.startswith("---")]
            _ant_opts = [a for a in ANTECEDENTS if not a.startswith("---")]
            with st.form(f"edit_reg_{_ve_id}"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    _ve_date_val = None
                    if _ve_record.get("date"):
                        try: _ve_date_val = datetime.fromisoformat(_ve_record["date"]).date()
                        except Exception: pass
                    _e_date = st.date_input("Date", value=_ve_date_val, key=f"e_date_{_ve_id}")
                    _e_time = st.text_input("Time (HH:MM:SS)", value=_ve_record.get("time","") or "", key=f"e_time_{_ve_id}")
                with ec2:
                    _e_loc = st.text_input("Location", value=_ve_record.get("location","") or "", key=f"e_loc_{_ve_id}")
                    _sess_opts = ["Morning", "Middle", "Afternoon"]
                    _e_sess = st.selectbox("Session", _sess_opts,
                        index=_sess_opts.index(_ve_record.get("session")) if _ve_record.get("session") in _sess_opts else 0,
                        key=f"e_sess_{_ve_id}")
                with ec3:
                    _e_sev = st.slider("Severity", 1, 5, int(_ve_record.get("severity") or 3), key=f"e_sev_{_ve_id}")
                    _e_beh = st.selectbox("Behaviour Type", _beh_opts,
                        index=_beh_opts.index(_ve_record.get("behaviour_type")) if _ve_record.get("behaviour_type") in _beh_opts else 0,
                        key=f"e_beh_{_ve_id}")
                _e_ant = st.selectbox("Antecedent", _ant_opts,
                    index=_ant_opts.index(_ve_record.get("antecedent")) if _ve_record.get("antecedent") in _ant_opts else 0,
                    key=f"e_ant_{_ve_id}")
                _e_desc = st.text_area("Description / Notes", value=_ve_record.get("description","") or "", key=f"e_desc_{_ve_id}")
                _ve_interv_current = _ve_record.get("intervention")
                _e_interv = st.text_input(
                    "Intervention(s) — comma separated",
                    value=", ".join(_ve_interv_current) if isinstance(_ve_interv_current, list) else (_ve_interv_current or ""),
                    key=f"e_interv_{_ve_id}",
                )
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    _updated = dict(_ve_record)
                    _updated.update({
                        "date": _e_date.isoformat() if _e_date else None,
                        "time": _e_time, "location": _e_loc, "session": _e_sess,
                        "severity": _e_sev, "behaviour_type": _e_beh, "antecedent": _e_ant,
                        "description": _e_desc,
                        "intervention": [s.strip() for s in _e_interv.split(",") if s.strip()],
                        "db_exists": True,
                    })
                    if save_incident_to_db(_updated):
                        _reload_into_session("incidents", load_incidents_from_db)
                        _reload_into_session("critical_incidents", load_critical_incidents_from_db)
                        st.success("✅ Incident updated.")
                        st.rerun()
            _ve_print_data = {
                "Date": _ve_record.get("date") or "—", "Time": _ve_record.get("time") or "—",
                "Location": _ve_record.get("location") or "—", "Session": _ve_record.get("session") or "—",
                "Behaviour Type": _ve_record.get("behaviour_type") or "—",
                "Antecedent": _ve_record.get("antecedent") or "—",
                "Severity": _ve_record.get("severity") or "—",
                "Intervention": ", ".join(_ve_interv_current) if isinstance(_ve_interv_current, list) else (_ve_interv_current or "—"),
                "Description": _ve_record.get("description") or "—",
            }

        elif _ve_record and _ve_type == "critical":
            _primary = _ve_record.get("ABCH_primary", {}) if isinstance(_ve_record.get("ABCH_primary"), dict) else {}
            with st.form(f"edit_crit_{_ve_id}"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    _ve_cdate_val = None
                    if _ve_record.get("created_at"):
                        try: _ve_cdate_val = datetime.fromisoformat(_ve_record["created_at"][:10]).date()
                        except Exception: pass
                    _e_cdate = st.date_input("Date", value=_ve_cdate_val, key=f"e_cdate_{_ve_id}")
                    _e_ctime = st.text_input("Time", value=_primary.get("time","") or "", key=f"e_ctime_{_ve_id}")
                with ec2:
                    _e_cloc = st.text_input("Location", value=_primary.get("location","") or "", key=f"e_cloc_{_ve_id}")
                    _e_csev = st.slider("Severity", 1, 5, int(_ve_record.get("severity") or 3), key=f"e_csev_{_ve_id}")
                with ec3:
                    _e_sapol = st.text_input("SAPOL Reference", value=_ve_record.get("sapol_reference") or "", key=f"e_sapol_{_ve_id}")
                _e_ctx = st.text_area("Antecedent / Context", value=_primary.get("context","") or "", key=f"e_cctx_{_ve_id}")
                _e_cbeh = st.text_area("Behaviour", value=_primary.get("behaviour","") or "", key=f"e_cbeh_{_ve_id}")
                _e_ccons = st.text_area("Consequence / Response", value=_primary.get("consequence","") or "", key=f"e_ccons_{_ve_id}")
                _e_notes = st.text_area("Admin Summary / Notes", value=_ve_record.get("admin_summary","") or "", key=f"e_cnotes_{_ve_id}")
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    _update_payload = {
                        "created_at": f"{_e_cdate.isoformat()}T00:00:00" if _e_cdate else None,
                        "primary_time": _e_ctime, "primary_location": _e_cloc,
                        "primary_context": _e_ctx, "primary_behaviour": _e_cbeh,
                        "primary_consequence": _e_ccons, "severity": _e_csev,
                        "sapol_reference": _e_sapol or None, "admin_summary": _e_notes,
                    }
                    try:
                        supabase.table("critical_incidents").update(_update_payload).eq("id", _ve_id).execute()
                        _reload_into_session("incidents", load_incidents_from_db)
                        _reload_into_session("critical_incidents", load_critical_incidents_from_db)
                        st.success("✅ Critical incident updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
            _ve_print_data = {
                "Date": (_ve_record.get("created_at","") or "")[:10] or "—",
                "Time": _primary.get("time") or "—", "Location": _primary.get("location") or "—",
                "Antecedent / Context": _primary.get("context") or "—",
                "Behaviour": _primary.get("behaviour") or "—",
                "Consequence": _primary.get("consequence") or "—",
                "Severity": _ve_record.get("severity") or "—",
                "SAPOL Reference": _ve_record.get("sapol_reference") or "—",
                "Notes": _ve_record.get("admin_summary") or "—",
            }

        if _ve_print_data:
            st.markdown("")
            _print_buf = generate_single_incident_docx(_ve_print_data, _ve_type, student["name"])
            st.download_button(
                "🖨️ Download Printable Summary (Word)", _print_buf,
                file_name=f"Incident_{student['name'].replace(' ', '_')}_{_ve_item.get('date') or 'nodate'}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"print_dl_{_ve_id}",
            )

    st.markdown("---")
    st.markdown("### 🗑️ Delete an Incident")
    st.caption("Remove an incorrectly logged or duplicate incident from this student's full data set. This includes regular incidents AND critical incidents. Deletions are permanent and will affect all charts and analysis.")

    reg_incidents = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    crit_incidents = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]

    combined = []
    for i in reg_incidents:
        _rdate = i.get("date", "")
        _no_date_flag = "⚠️ NO DATE  " if not _rdate else ""
        combined.append({
            "id": i["id"],
            "type": "regular",
            "label": f"{_no_date_flag}[REGULAR]  {_rdate or '(none)'}  {i.get('time','')[:5]}  |  {i.get('behaviour_type','—')}  |  Severity {i.get('severity','?')}  |  {i.get('location','—')}",
            "date": _rdate,
        })
    for c in crit_incidents:
        primary = c.get("ABCH_primary", {}) if isinstance(c.get("ABCH_primary"), dict) else {}
        created = (c.get("created_at","") or "")[:10]
        _no_date_flag = "⚠️ NO DATE  " if not created else ""
        combined.append({
            "id": c["id"],
            "type": "critical",
            "label": f"{_no_date_flag}[CRITICAL]  {created or '(none)'}  {primary.get('time','')[:5]}  |  {primary.get('behaviour','Behaviour not recorded')[:50]}  |  {primary.get('location','—')}",
            "date": created,
        })

    if not combined:
        st.info("No incidents on record for this student yet.")
    else:
        combined_sorted = sorted(combined, key=lambda x: x["date"], reverse=True)
        delete_options = {item["label"]: item for item in combined_sorted}

        selected_label = st.selectbox(
            f"Select incident to delete ({len(combined)} total — {len(reg_incidents)} regular, {len(crit_incidents)} critical)",
            list(delete_options.keys()),
            key="delete_incident_select"
        )
        selected_item = delete_options[selected_label]
        selected_id   = selected_item["id"]
        selected_type = selected_item["type"]

        type_badge = "🔴 CRITICAL INCIDENT FORM" if selected_type == "critical" else "🟡 Regular Incident"
        st.markdown(
            f'<div style="background:#fff5f5;border:1.5px solid #fca5a5;border-radius:8px;padding:.65rem 1rem;margin:.5rem 0;">'
            f'<strong>Selected:</strong> {type_badge}<br>'
            f'<span style="font-size:.82rem;color:#374151;">{selected_label}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        confirm_key  = f"confirm_del_inc_{selected_id}"
        confirm2_key = f"confirm2_del_inc_{selected_id}"

        if not st.session_state.get(confirm_key):
            if selected_type == "critical":
                st.warning("⚠️ This is a **Critical Incident ABCH form**. Deleting it will permanently remove the full incident record, all ABCH entries, workflow history, and audit trail from the dataset.")
            else:
                st.warning("⚠️ Deleting this incident will permanently remove it from all charts, analysis, and exports.")
            if st.button("🗑️ I want to delete this — proceed to confirmation", key="del_inc_btn", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()

        elif not st.session_state.get(confirm2_key):
            st.error(
                f"**Step 1 of 2 — Are you sure?**\n\n"
                f"You are about to permanently delete:\n\n"
                f"> {selected_label}\n\n"
                f"This will be **removed from the data set immediately** and cannot be recovered."
            )
            confirm_check = st.checkbox(
                f"I understand this will permanently remove this {'critical incident form' if selected_type == 'critical' else 'incident'} from {student['name']}'s record.",
                key=f"confirm_chk_{selected_id}"
            )
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("⚠️ Confirm — proceed to final step", type="primary",
                             key=f"confirm2_btn_{selected_id}", use_container_width=True,
                             disabled=not confirm_check):
                    st.session_state[confirm2_key] = True
                    st.rerun()
            with col_no:
                if st.button("❌ Cancel — keep this incident", key=f"cancel1_{selected_id}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()

        else:
            st.error(
                f"**Step 2 of 2 — FINAL CONFIRMATION**\n\n"
                f"Click the red button below to permanently delete this record from the database. "
                f"There is no undo."
            )
            col_final, col_back = st.columns(2)
            with col_final:
                if st.button("🔴 YES — permanently delete this incident", type="primary",
                             key=f"final_del_{selected_id}", use_container_width=True):
                    deleted = False
                    if supabase:
                        try:
                            table = "critical_incidents" if selected_type == "critical" else "incidents"
                            supabase.table(table).delete().eq("id", selected_id).execute()
                            deleted = True
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
                    else:
                        deleted = True
                    if deleted:
                        # Explicitly reload fresh from the database rather than
                        # filtering the in-memory list — guarantees the removed
                        # incident is actually gone everywhere it's counted
                        # (program roster, dashboard, analysis), with no
                        # dependency on an in-memory id-match succeeding.
                        _reload_into_session("incidents", load_incidents_from_db)
                        _reload_into_session("critical_incidents", load_critical_incidents_from_db)
                        for k in [confirm_key, confirm2_key, f"confirm_chk_{selected_id}"]:
                            st.session_state.pop(k, None)
                        st.success("✅ Incident permanently deleted and removed from the data set.")
                        st.rerun()
            with col_back:
                if st.button("❌ Cancel — keep this incident", key=f"cancel2_{selected_id}", use_container_width=True):
                    for k in [confirm_key, confirm2_key]:
                        st.session_state.pop(k, None)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🔁 Re-log as New Incident")
    st.caption(
        "Quickly re-log a previously recorded behaviour as a new incident. "
        "Pre-fills with the existing record so you only need to update the date, time, "
        "severity, or description. Useful when the same behaviour occurs regularly."
    )

    # ── Build selectable list of regular incidents only (re-log doesn't apply to critical forms) ──
    _relog_incidents = sorted(
        [i for i in st.session_state.incidents if i["student_id"] == student_id],
        key=lambda x: x.get("date", ""), reverse=True
    )

    if not _relog_incidents:
        st.info("No regular incidents on record yet — log the first one above.")
    else:
        # Selectbox label: date · time · behaviour · severity
        def _relog_label(inc):
            t = (inc.get("time") or "")[:5]
            return (
                f"{inc.get('date','?')}  {t}  |  "
                f"{inc.get('behaviour_type','—')}  |  "
                f"Sev {inc.get('severity','?')}  |  "
                f"{inc.get('location','—')}"
            )

        _relog_options = {_relog_label(i): i for i in _relog_incidents}
        _selected_label = st.selectbox(
            f"Select incident to use as template ({len(_relog_incidents)} regular incidents)",
            list(_relog_options.keys()),
            key="relog_select"
        )
        _src_inc = _relog_options[_selected_label]

        # Preview card
        st.markdown(
            f"<div style='background:#eff6ff;border:1.5px solid #93c5fd;border-radius:8px;"
            f"padding:.6rem 1rem;margin:.35rem 0 .7rem;font-size:.83rem;color:#1e3a5f;'>"
            f"<strong>Template:</strong> {_src_inc.get('behaviour_type','—')} on "
            f"{_src_inc.get('date','?')} at {(_src_inc.get('time') or '')[:5]}  ·  "
            f"Severity {_src_inc.get('severity','?')}  ·  {_src_inc.get('location','—')}<br>"
            f"<span style='color:#64748b;'>Antecedent: {_src_inc.get('antecedent','—')}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        with st.expander("✏️ Adjust & Submit New Incident", expanded=False):
            st.caption("All fields are pre-filled from the template. Change only what is different this time.")

            # ── Parse existing time for the time_input default ──
            try:
                _default_time = datetime.strptime(
                    (_src_inc.get("time") or "09:00:00")[:8], "%H:%M:%S"
                ).time()
            except Exception:
                _default_time = datetime.now().time()

            rl_col1, rl_col2 = st.columns(2)
            with rl_col1:
                rl_date = st.date_input(
                    "Date *", value=date.today(), key="rl_date"
                )
                rl_time = st.time_input(
                    "Time *", value=_default_time, key="rl_time"
                )
                rl_location = st.selectbox(
                    "Location *",
                    LOCATIONS,
                    index=LOCATIONS.index(_src_inc["location"]) if _src_inc.get("location") in LOCATIONS else 0,
                    key="rl_location"
                )
            with rl_col2:
                rl_behaviour = st.selectbox(
                    "Behaviour Type *",
                    BEHAVIOUR_TYPES,
                    index=BEHAVIOUR_TYPES.index(_src_inc["behaviour_type"]) if _src_inc.get("behaviour_type") in BEHAVIOUR_TYPES else 0,
                    key="rl_behaviour"
                )
                # Filter section headers out of antecedents for selectbox
                _valid_ants = [a for a in ANTECEDENTS if not a.startswith("---")]
                _ant_default = _src_inc.get("antecedent", _valid_ants[0])
                if _ant_default not in _valid_ants:
                    _ant_default = _valid_ants[0]
                rl_antecedent = st.selectbox(
                    "Antecedent/Trigger *",
                    _valid_ants,
                    index=_valid_ants.index(_ant_default),
                    key="rl_antecedent"
                )
                # Pre-select existing interventions
                _existing_ints = _src_inc.get("intervention", [])
                if isinstance(_existing_ints, str):
                    _existing_ints = [_existing_ints]
                _valid_existing_ints = [v for v in _existing_ints if v in INTERVENTIONS]
                rl_interventions = st.multiselect(
                    "Interventions Used *",
                    INTERVENTIONS,
                    default=_valid_existing_ints,
                    key="rl_interventions"
                )

            rl_duration = st.number_input(
                "Duration (minutes) *",
                min_value=1,
                value=int(_src_inc.get("duration_minutes") or 1),
                key="rl_duration"
            )
            rl_severity = st.slider(
                "Severity Level *", 1, 5,
                value=int(_src_inc.get("severity") or 1),
                key="rl_severity"
            )
            rl_description = st.text_area(
                "Notes / Description (Optional)",
                value="",
                placeholder="Add any notes specific to this occurrence...",
                height=80,
                key="rl_description"
            )

            # Warn if severity ≥ 3 — needs a critical form after
            if rl_severity >= 3:
                st.warning(
                    f"⚠️ Severity {rl_severity} — if this incident reaches Level 3+, "
                    "a Critical Incident ABCH Form will be required after saving."
                )

            rl_submit = st.button(
                "✅ Save as New Incident", type="primary",
                key="rl_submit_btn", use_container_width=True
            )

            if rl_submit:
                if not rl_interventions:
                    st.error("Please select at least one intervention.")
                else:
                    _new_id  = str(uuid.uuid4())
                    _is_crit = rl_severity >= 3
                    _hyp     = generate_hypothesis_ai(rl_antecedent, rl_behaviour, "")
                    _new_rec = {
                        "id":               _new_id,
                        "student_id":       student_id,
                        "student_name":     student["name"],
                        "date":             rl_date.isoformat(),
                        "time":             rl_time.strftime("%H:%M:%S"),
                        "day":              rl_date.strftime("%A"),
                        "session":          get_session_from_time(rl_time),
                        "location":         rl_location,
                        "behaviour_type":   rl_behaviour,
                        "antecedent":       rl_antecedent,
                        "intervention":     rl_interventions,
                        "severity":         rl_severity,
                        "reported_by":      st.session_state.current_user.get("id", "unknown"),
                        "duration_minutes": rl_duration,
                        "description":      rl_description or f"Re-logged from incident on {_src_inc.get('date','?')}",
                        "is_critical":      _is_crit,
                        "hypothesis_function": _hyp["function"],
                        "hypothesis_item":     _hyp["item"],
                    }
                    if save_incident_to_db(_new_rec):
                        st.session_state.incidents.append(_new_rec)
                        st.success(
                            f"✅ New incident saved for {student['name']} on {rl_date.strftime('%d/%m/%Y')}."
                        )
                        if _is_crit:
                            st.warning(
                                "⚠️ Severity 3+ — please complete a Critical Incident ABCH Form "
                                "for this event. Use the '📝 Log Incident' button and select "
                                "'Complete Critical Form' after submitting."
                            )
                        st.rerun()
                    else:
                        st.error("❌ Failed to save — please try again.")

    st.markdown("---")
    st.markdown("#### 📝 Supports Trialled (optional — included in the report below)")
    st.caption("Answers here are included in the Behaviour Summary report automatically.")
    _st_col1, _st_col2 = st.columns(2)
    with _st_col1:
        st.text_area(
            "What supports/strategies have been trialled with this student?",
            key=f"supports_trialled_{student_id}", height=90,
            placeholder="e.g. Quiet entry space before joining the group, movement break before Maths, "
                        "visual transition schedule...",
        )
    with _st_col2:
        st.text_area(
            "How successful were they? What worked, what didn't?",
            key=f"supports_success_{student_id}", height=90,
            placeholder="e.g. Quiet entry space reduced morning incidents significantly; movement "
                        "breaks had mixed results...",
        )
    st.date_input(
        "When did this trial start? (optional — enables a before/after comparison below)",
        value=None, key=f"supports_trial_date_{student_id}",
    )
    _supports_trialled = st.session_state.get(f"supports_trialled_{student_id}", "")
    _supports_success  = st.session_state.get(f"supports_success_{student_id}", "")
    _trial_date = st.session_state.get(f"supports_trial_date_{student_id}")
    _before_after = compute_before_after(full_df, _trial_date) if _trial_date else None
    if _before_after:
        st.markdown("**📈 Before / After Comparison**")
        render_before_after(_before_after)

    st.markdown("---")
    st.markdown("### 📄 Export Data & Reports")
    col1, col2 = st.columns(2)
    with col1:
        csv = full_df.to_csv(index=False)
        st.download_button("📥 Download Raw Data (CSV)", csv,
            file_name=f"{student['name'].replace(' ', '_')}_Incident_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv", use_container_width=True)
    with col2:
        with st.spinner("Generating Behaviour Summary..."):
            docx_file = generate_behaviour_analysis_plan_docx(
                student, full_df, top_ant, top_beh, top_loc, top_session, risk_score, risk_level,
                supports_trialled=_supports_trialled, supports_success=_supports_success,
                before_after=_before_after)
        if docx_file:
            _bs_date = datetime.now().strftime("%Y%m%d")
            _bs_local_name = f"BehaviourSummary_{student['name'].replace(' ', '_')}_{_bs_date}.docx"
            _dl_kwargs = {}
            if _ARCHIVE_AVAILABLE:
                _bs_initials = initials_from_name(student["name"])
                _bs_creator = (
                    st.session_state.current_user.get("email")
                    or st.session_state.current_user.get("name", "unknown")
                ) if st.session_state.get("current_user") else "unknown"
                _dl_kwargs = dict(
                    on_click=archive_once,
                    kwargs=dict(
                        guard_key=f"behreport_{student_id}_{_bs_date}",
                        source_tool="Behaviour Support Tool",
                        doc_type="Behaviour Report",
                        title=f"Behaviour Summary — {_bs_initials}",
                        file_bytes=docx_file.getvalue(),
                        # Archive filename uses initials only — the archive
                        # never stores full student names (privacy policy
                        # in archive_utils.py) — separate from the
                        # full-name filename used for the local download.
                        filename=f"BehaviourSummary_{_bs_initials}_{_bs_date}.docx",
                        student_initials=_bs_initials,
                        created_by=_bs_creator,
                        notes="Auto-archived on download.",
                    ),
                )
            st.download_button("📄 Behaviour Summary (Word)", docx_file,
                file_name=_bs_local_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                **_dl_kwargs)

    _prep_print = st.checkbox("🖨️ Prepare print versions (Full Screen + Full Analysis Word)", key=f"prep_print_{student_id}",
                              help="Built only when ticked, so the page stays quick for everyday use.")
    st.markdown("#### 🖨️ Print the Whole Screen")
    st.caption("Prints everything on this page exactly as shown: every chart with its 'Understanding this chart' note, "
               "tables, recommendations and trials, plus the incident register and a notes page. Open the file, press Print, "
               "then pick your printer or Save as PDF.")
    if not _prep_print:
        st.caption("Tick the box above to prepare the print versions.")
    try:
        if not _prep_print:
            raise StopIteration
        _screen_html = build_print_html(
            student, full_df, list(_SCREEN["rec"]), supports_trialled=_supports_trialled,
            supports_success=_supports_success, before_after=_before_after, trials=None)
        st.download_button(
            "🖨️ Print-ready Full Screen (HTML)", _screen_html,
            file_name=f"FullScreen_{student['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html", use_container_width=True, key=f"dl_fullscreen_{student_id}")
    except StopIteration:
        pass
    except Exception as _e:
        st.warning(f"Could not prepare the print-ready version: {_e}")
    st.markdown("#### 📄 Full Analysis — Word version")
    st.caption("Everything on this page in one printable Word document for meetings: all charts and tables, "
               "Window of Tolerance, patterns, considerations, Berry Street strategies, a full incident "
               "register, and a blank page for notes and agreed actions.")
    with st.spinner("Preparing print pack..."):
        _pack_file = None if not _prep_print else generate_behaviour_analysis_plan_docx(
            student, full_df, top_ant, top_beh, top_loc, top_session, risk_score, risk_level,
            supports_trialled=_supports_trialled, supports_success=_supports_success,
            before_after=_before_after, full_pack=True,
            bsem_items=st.session_state.get(f"bsem_analysis_{student_id}", []),
            trials=load_trials(student_id))
    if _pack_file:
        st.download_button(
            "🖨️ Full Analysis for Printing (Word)", _pack_file,
            file_name=f"FullAnalysis_{student['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True, key=f"dl_fullpack_{student_id}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back to Students", type="primary", key="back_analysis_bottom", use_container_width=True):
            if student.get("archived", False):
                go_to("admin_portal")
            else:
                go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("🏠 Program Landing", key="home_analysis_bottom", use_container_width=True):
            go_to("landing")


def render_student_dashboard():
    student_id = st.session_state.get("selected_student_id")
    student = get_student(student_id)
    if not student:
        st.error("No student selected"); return
    st.markdown(f"## 📊 Dashboard — {student['name']}")
    if st.session_state.get("hist_incident_just_saved"):
        _saved_total = st.session_state.pop("hist_incident_just_saved")
        st.success(f"✅ Historical incident saved — {student['name']} now has **{_saved_total}** incident(s) on record.")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_dash"):
            if student.get("archived", False):
                go_to("admin_portal")
            else:
                go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("📝 Log Incident", key="log_dash"):
            go_to("incident_log", selected_student_id=student_id)
    with col3:
        if st.button("📈 Full Analysis", key="analysis_dash"):
            go_to("student_analysis", selected_student_id=student_id)
    with col4:
        if st.button("📋 Support Plan", key="sp_dash"):
            go_to("support_plan", selected_student_id=student_id)
    st.markdown("---")
    incidents = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    critical = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]
    if not incidents and not critical:
        st.info("📋 No incident data yet. Click 'Log Incident' to start tracking.")
    quick_df = pd.DataFrame(incidents) if incidents else pd.DataFrame()
    crit_df = pd.DataFrame(critical) if critical else pd.DataFrame()
    if not quick_df.empty:
        quick_df["incident_type"] = "Quick"
        quick_df["date_parsed"] = _parse_dates(quick_df["date"])
    if not crit_df.empty:
        crit_df["incident_type"] = "Critical"
        _crit_dates = crit_df["created_at"] if "created_at" in crit_df.columns else pd.Series(
            [datetime.now().isoformat()] * len(crit_df), index=crit_df.index
        )
        crit_df["date_parsed"] = _parse_dates(_crit_dates)
        crit_df["severity"] = crit_df["severity"].fillna(5).astype(int) if "severity" in crit_df.columns else 5
        crit_df["time"] = crit_df["ABCH_primary"].apply(
            lambda d: d.get("time", "09:00:00") if isinstance(d, dict) else "09:00:00"
        ) if "ABCH_primary" in crit_df.columns else "09:00:00"
        for _col in ["location", "session", "antecedent", "behaviour_type"]:
            if _col not in crit_df.columns:
                crit_df[_col] = crit_df["ABCH_primary"].apply(
                    lambda d: d.get(_col, "") if isinstance(d, dict) else ""
                ) if "ABCH_primary" in crit_df.columns else ""
        if "location" in crit_df.columns:
            crit_df["location"] = crit_df["location"].apply(normalise_location)
    full_df = (
        pd.concat([quick_df, crit_df], ignore_index=True)
        .sort_values("date_parsed", na_position="last")
        if not quick_df.empty or not crit_df.empty
        else pd.DataFrame()
    )

    # ── Filters: applied to everything below (metrics, charts, patterns, recommendations) ──
    if not full_df.empty:
        with st.expander("🔎 Filters", expanded=False):
            _fcol1, _fcol2, _fcol3 = st.columns(3)
            _min_d = full_df["date_parsed"].min()
            _max_d = full_df["date_parsed"].max()
            with _fcol1:
                _date_range = st.date_input(
                    "Date range", value=(_min_d.date(), _max_d.date()),
                    min_value=_min_d.date(), max_value=_max_d.date(),
                    key=f"dash_filter_dates_{student_id}",
                )
            with _fcol2:
                _beh_opts = sorted(full_df["behaviour_type"].dropna().unique().tolist()) if "behaviour_type" in full_df.columns else []
                _beh_filter = st.multiselect("Behaviour type", _beh_opts, key=f"dash_filter_beh_{student_id}")
            with _fcol3:
                _loc_opts = sorted(full_df["location"].dropna().unique().tolist()) if "location" in full_df.columns else []
                _loc_filter = st.multiselect("Location", _loc_opts, key=f"dash_filter_loc_{student_id}")
            if st.button("Clear filters", key=f"dash_filter_clear_{student_id}"):
                for _k in [f"dash_filter_dates_{student_id}", f"dash_filter_beh_{student_id}", f"dash_filter_loc_{student_id}"]:
                    st.session_state.pop(_k, None)
                st.rerun()

        if isinstance(_date_range, tuple) and len(_date_range) == 2:
            _d_start, _d_end = _date_range
            full_df = full_df[
                (full_df["date_parsed"].dt.date >= _d_start) & (full_df["date_parsed"].dt.date <= _d_end)
            ]
        if _beh_filter:
            full_df = full_df[full_df["behaviour_type"].isin(_beh_filter)]
        if _loc_filter:
            full_df = full_df[full_df["location"].isin(_loc_filter)]
        _filters_active = bool(_beh_filter or _loc_filter or (isinstance(_date_range, tuple) and _date_range != (_min_d.date(), _max_d.date())))
        if _filters_active:
            st.caption(f"🔎 Filters applied — showing {len(full_df)} incident(s). Everything below reflects this filtered view.")

    total_incidents = len(full_df)
    critical_count = len(full_df[full_df.get("incident_type", pd.Series(dtype=str)) == "Critical"]) if "incident_type" in full_df.columns else len(crit_df)
    avg_severity = full_df["severity"].mean() if "severity" in full_df.columns else 0
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_incidents = len(full_df[full_df["date_parsed"] >= week_ago]) if not full_df.empty else 0
    risk_score = min(100, int((recent_incidents / 7 * 15) + (avg_severity * 10) + (critical_count / max(total_incidents, 1) * 40)))
    if risk_score < 30:
        risk_level = "LOW"; risk_color = "#10b981"; risk_emoji = "🟢"
    elif risk_score < 60:
        risk_level = "MODERATE"; risk_color = "#f59e0b"; risk_emoji = "🟡"
    else:
        risk_level = "HIGH"; risk_color = "#ef4444"; risk_emoji = "🔴"
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Total Incidents", total_incidents)
    with col2: st.metric("Critical", critical_count, delta=f"{(critical_count/total_incidents*100):.0f}%" if total_incidents > 0 else "0%")
    with col3: st.metric("Avg Severity", f"{avg_severity:.1f}/5")
    with col4: st.metric("Last 7 Days", recent_incidents)
    with col5:
        st.markdown(f"<div style='text-align:center;padding:1rem;background:white;border-radius:8px;border:2px solid {risk_color};'>"
                   f"<div style='font-size:2rem;'>{risk_emoji}</div>"
                   f"<div style='font-size:0.875rem;color:#64748b;font-weight:600;'>RISK LEVEL</div>"
                   f"<div style='font-size:1.5rem;font-weight:700;color:{risk_color};'>{risk_level}</div>"
                   f"<div style='font-size:0.75rem;color:#64748b;'>{risk_score}/100</div>"
                   f"</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📊 Visual Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📅 Daily Incident Count (Last 30 Days)")
        if not full_df.empty:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_df = full_df[full_df["date_parsed"] >= thirty_days_ago]
            if recent_df.empty:
                st.info("No incidents in the last 30 days.")
            else:
                daily = (
                    recent_df
                    .assign(_d=recent_df["date_parsed"].dt.date)
                    .groupby("_d")
                    .size()
                    .reset_index(name="count")
                )
                daily["label"] = daily["_d"].apply(lambda d: d.strftime("%a %-d %b"))
                max_count = int(daily["count"].max())
                colours = ["#ef4444" if v >= 3 else "#1A7A7A" for v in daily["count"]]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=daily["label"], y=daily["count"],
                    marker=dict(color=colours, line=dict(color="white", width=1)),
                    text=daily["count"], textposition="outside",
                    textfont=dict(size=11, family="Arial", color="#1a2e44"),
                    hovertemplate="<b>%{x}</b><br>%{y} incident(s)<extra></extra>"
                ))
                fig.update_layout(
                    height=270, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(
                        type="category",
                        tickfont=dict(size=10, color="#334155"),
                        showline=True, linecolor="#cbd5e1",
                        tickangle=-35 if len(daily) > 8 else 0,
                    ),
                    yaxis=dict(
                        tickmode="linear", tick0=0, dtick=1,
                        range=[0, max_count + 1],
                        gridcolor="#e2e8f0", showline=True, linecolor="#cbd5e1",
                        tickfont=dict(size=10, color="#334155"),
                        title=dict(text="Incidents", font=dict(size=11, color="#334155")),
                    ),
                )
                _daily_pts = plotly_chart_with_selection(fig, key=f"dash_daily_chart_{student_id}", use_container_width=True)
                st.caption("🟥 Red = 3+ incidents that day  ·  🟦 Teal = 1–2 incidents  ·  Click a bar to see that day's incidents.")
                if _daily_pts:
                    _sel_idx = _daily_pts[0].get("point_index")
                    if _sel_idx is not None and 0 <= _sel_idx < len(daily):
                        _sel_date = daily.iloc[_sel_idx]["_d"]
                        _day_incidents = full_df[full_df["date_parsed"].dt.date == _sel_date]
                        with st.expander(f"📋 Incidents on {_sel_date.strftime('%A %d %B')} ({len(_day_incidents)})", expanded=True):
                            _show_cols = [c for c in ["date_parsed", "time", "behaviour_type", "antecedent", "location", "session", "severity"] if c in _day_incidents.columns]
                            st.dataframe(_day_incidents[_show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No incident data to display.")
    with col2:
        st.markdown("#### 🎯 Top Behaviours")
        if not full_df.empty and "behaviour_type" in full_df.columns:
            beh_series = full_df["behaviour_type"].dropna()
            beh_series = beh_series[beh_series.str.strip() != ""]
            beh_counts = beh_series.value_counts().head(5)
            if beh_counts.empty:
                st.info("No behaviour data recorded yet.")
            else:
                max_beh = int(beh_counts.max())
                beh_colours = ["#1A7A7A" if i == 0 else "#64748b" for i in range(len(beh_counts))]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=list(beh_counts.index[::-1]),
                    x=list(beh_counts.values[::-1]),
                    orientation="h",
                    marker=dict(color=beh_colours[::-1], line=dict(color="white", width=1)),
                    text=[str(v) for v in beh_counts.values[::-1]],
                    textposition="outside",
                    textfont=dict(size=11, family="Arial", color="#1a2e44"),
                    hovertemplate="<b>%{y}</b><br>%{x} incident(s)<extra></extra>"
                ))
                fig.update_layout(
                    height=270, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10, r=30, t=10, b=10),
                    xaxis=dict(
                        tickmode="linear", tick0=0, dtick=1,
                        range=[0, max_beh + 1],
                        gridcolor="#e2e8f0", showline=True, linecolor="#cbd5e1",
                        tickfont=dict(size=10, color="#334155"),
                        title=dict(text="Number of incidents", font=dict(size=11, color="#334155")),
                    ),
                    yaxis=dict(
                        tickfont=dict(size=10, color="#334155"),
                        showline=True, linecolor="#cbd5e1",
                        automargin=True,
                    ),
                )
                _beh_pts = plotly_chart_with_selection(fig, key=f"dash_beh_chart_{student_id}", use_container_width=True)
                st.caption("Click a bar to see incidents of that behaviour.")
                if _beh_pts:
                    _sel_idx = _beh_pts[0].get("point_index")
                    _beh_labels_rev = list(beh_counts.index[::-1])
                    if _sel_idx is not None and 0 <= _sel_idx < len(_beh_labels_rev):
                        _sel_beh = _beh_labels_rev[_sel_idx]
                        _beh_incidents = full_df[full_df["behaviour_type"] == _sel_beh]
                        with st.expander(f"📋 Incidents — {_sel_beh} ({len(_beh_incidents)})", expanded=True):
                            _show_cols = [c for c in ["date_parsed", "time", "antecedent", "location", "session", "severity"] if c in _beh_incidents.columns]
                            st.dataframe(_beh_incidents[_show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No behaviour data recorded yet.")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🎯 Key Patterns")
        if not full_df.empty:
            top_beh = full_df["behaviour_type"].mode()[0] if "behaviour_type" in full_df.columns else "Unknown"
            top_ant = full_df["antecedent"].mode()[0] if "antecedent" in full_df.columns else "Unknown"
            top_loc = full_df["location"].mode()[0] if "location" in full_df.columns else "Unknown"
            top_session = full_df["session"].mode()[0] if "session" in full_df.columns else "Unknown"
            st.markdown(f"- **Primary Behaviour:** {top_beh}\n- **Main Trigger:** {top_ant}\n- **Hotspot:** {top_loc}\n- **Peak Time:** {top_session}")
    with col2:
        st.markdown("### 📋 Recent Activity")
        if not full_df.empty:
            recent_5 = full_df.tail(5).sort_values("date_parsed", ascending=False)
            for _, inc in recent_5.iterrows():
                date_str = inc["date_parsed"].strftime("%d/%m")
                sev = inc.get("severity", "?")
                emoji = "🔴" if inc.get("incident_type") == "Critical" else "🟡" if sev >= 3 else "🟢"
                st.markdown(f"{emoji} **{date_str}** - Sev {sev}")
    st.markdown("---")
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1A7A7A 0%,#134e4e 100%);"
        "border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:0.7rem;"
        "box-shadow:0 4px 14px rgba(19,78,78,0.25);'>"
        "<span style='color:white;font-size:1.15rem;font-weight:700;'>💡 Recommendations to Trial</span><br>"
        "<span style='color:#d1fae5;font-size:0.85rem;'>BSEM-informed strategies matched to this "
        "student's actual pattern. Click a strategy for why it fits and how to trial it.</span></div>",
        unsafe_allow_html=True,
    )
    st.caption("SMART's core reminder: regulate before you reason — these strategies work by supporting "
               "regulation ahead of demand, not by correcting after the fact.")
    _risk_line = {"HIGH": "🔴 **HIGH RISK** — daily check-ins recommended alongside the strategies below.",
                  "MODERATE": "🟡 **MODERATE RISK** — weekly review alongside the strategies below.",
                  "LOW": "🟢 **LOW RISK** — maintain current supports."}[risk_level]
    st.caption(_risk_line)
    if not full_df.empty:
        _bsem_key_d = f"bsem_dash_{student_id}"
        _bsem_sig_d = f"{top_beh}|{top_ant}|{top_loc}|{top_session}"
        if (st.session_state.get(f"{_bsem_key_d}_sig") != _bsem_sig_d
                or st.button("🔄 Regenerate", key=f"{_bsem_key_d}_regen")):
            with st.spinner("Drawing up BSEM-aligned recommendations..."):
                st.session_state[_bsem_key_d] = build_bsem_recommendations(
                    full_df, top_beh, top_ant, top_loc, top_session,
                    student["name"], context="dashboard")
                st.session_state[f"{_bsem_key_d}_sig"] = _bsem_sig_d
        _bsem_items_d = st.session_state.get(_bsem_key_d, [])
        if _bsem_items_d:
            render_bsem_recommendations(_bsem_items_d, key_prefix=_bsem_key_d)
        else:
            st.info("Not enough antecedent data yet to generate recommendations.")
    else:
        st.info("Log some incidents to generate BSEM-aligned recommendations.")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Log New Incident", type="primary", use_container_width=True, key="dash_log_btn"):
            go_to("incident_log", selected_student_id=student_id)
    with col2:
        if st.button("📈 Full Analysis", use_container_width=True, key="dash_analysis_btn"):
            go_to("student_analysis", selected_student_id=student_id)
    with col3:
        if st.button("⬅ Back", use_container_width=True, key="dash_back_btn"):
            if student.get("archived", False):
                go_to("admin_portal")
            else:
                go_to("program_students", selected_program=student["program"])

    # ══════════════════════════════════════════════════════════════════════════
    # PATCH 2: HISTORICAL CRITICAL INCIDENTS — tabbed: Paste / Upload
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📋 Historical Critical Incidents")
    st.caption("Upload or paste an existing Word/PDF critical incident document. AI will extract and structure the incident automatically.")

    _hist_tab_paste, _hist_tab_upload = st.tabs(["📋 Paste Text", "📤 Upload File (.docx / .pdf)"])

    # ── shared AI extraction helper ───────────────────────────────────────────
    def _run_ai_extraction(doc_text: str, student_name: str):
        GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
        if not GROQ_KEY:
            st.error("Groq API key not configured.")
            return
        with st.spinner("AI is reading your document..."):
            try:
                import json as _json
                prompt = (
                    "You are a behaviour support data analyst for Cowandilla Learning Centre, Learning & Behaviour Unit.\n"
                    f"The following document describes ONE critical incident involving student: {student_name}.\n"
                    "Extract the incident as a single JSON object with this exact structure:\n"
                    '{"date":"YYYY-MM-DD","severity":3,"sapol_reference":"reference number or null",'
                    '"outcomes":["list","of","outcomes"],'
                    '"primary":{"time":"time","location":"location","context":"antecedent context",'
                    '"behaviour":"narrative description of what happened",'
                    '"behaviour_type":"CANONICAL LABEL — see list below","consequence":"staff response"},'
                    '"additional_entries":[{"time":"time","location":"location","context":"antecedent",'
                    '"behaviour":"behaviour narrative","behaviour_type":"canonical label",'
                    '"consequence":"consequence","hypothesis":""}],'
                    '"notes":"any other relevant context"}\n\n'
                    "CANONICAL BEHAVIOUR TYPES — behaviour_type MUST be one of these exact strings:\n"
                    "Verbal refusal of instruction | Task refusal / passive non-compliance | Shutdown / complete withdrawal | Selective mutism / non-responsiveness | Unsanctioned departure (elopement) | Absconding from school grounds | Hiding or avoiding adult proximity | Inappropriate vocalisation / noises | Disruptive verbal commentary | Interrupting / calling out | Property misuse or interference | Verbal aggression toward peer | Verbal aggression toward adult | Physical aggression toward peer | Physical aggression toward adult | Threatening behaviour | Property destruction | Throwing objects | Self-injurious behaviour | Dysregulated emotional expression | Other (specify in description)\n\n"
                    "Rules:\n"
                    "- severity 1-5 (1=minor/coping, 2=low, 3=elevated, 4=serious, 5=crisis); if SAPOL called then at least 4.\n"
                    "- behaviour_type must exactly match one of the canonical labels above.\n"
                    "- behaviour is the narrative/description; behaviour_type is the clinical classification.\n"
                    "- Return ONLY valid JSON, no markdown fences, no extra text.\n"
                    f"Document: {doc_text}"
                )
                raw = groq_ai_call(prompt, max_tokens=3000, temperature=0.1)
                raw = raw.replace("```json","").replace("```","").strip()
                extracted = _json.loads(raw)
                if isinstance(extracted, list):
                    extracted = extracted[0] if extracted else {}
                if extracted:
                    n_additional = len(extracted.get("additional_entries", []))
                    st.success(f"✅ Extracted — {1 + n_additional} timeline entries found.")
                    st.session_state["ai_extracted_incident"] = extracted
            except Exception as e:
                st.error(f"AI extraction failed: {e}")

    # ── Tab 1: Paste ──────────────────────────────────────────────────────────
    with _hist_tab_paste:
        st.caption("Copy all text from your Word document (Ctrl+A → Ctrl+C) and paste it below.")
        ai_notes = st.text_area(
            "Paste Word document content here",
            placeholder="Paste the full text of your ABCH Word document here...",
            height=300, key="ai_hist_notes")
        if st.button("🤖 Extract Incident with AI", type="primary",
                     key="ai_extract_btn_paste", use_container_width=True):
            if not ai_notes.strip():
                st.warning("Please paste your document content first.")
            else:
                _run_ai_extraction(ai_notes, student['name'])

    # ── Tab 2: Upload ─────────────────────────────────────────────────────────
    with _hist_tab_upload:
        st.caption("Upload the original Word, LibreOffice or PDF critical incident document. Text will be extracted automatically.")
        uploaded_doc = st.file_uploader(
            "Choose a .docx, .odt or .pdf file",
            type=["docx", "odt", "pdf"],
            key="ai_hist_upload",
            help="Accepts .docx (Word), .odt (LibreOffice) and .pdf files"
        )
        if uploaded_doc is not None:
            st.success(f"📄 **{uploaded_doc.name}** ready — click Extract below.")
            if st.button("🤖 Extract Incident with AI", type="primary",
                         key="ai_extract_btn_upload", use_container_width=True):
                extracted_text = ""
                try:
                    fname = uploaded_doc.name.lower()
                    if fname.endswith(".pdf"):
                        try:
                            import fitz  # PyMuPDF
                            raw_bytes = uploaded_doc.read()
                            pdf_doc = fitz.open(stream=raw_bytes, filetype="pdf")
                            pages = [page.get_text() for page in pdf_doc]
                            pdf_doc.close()
                            extracted_text = "\n".join(pages)
                        except ImportError:
                            st.error("PDF support requires PyMuPDF. Ask your admin to run: pip install pymupdf")
                        except Exception as pdf_err:
                            st.error(f"PDF read error: {pdf_err}")
                    elif fname.endswith(".odt"):
                        # .odt — OpenDocument Text (LibreOffice)
                        try:
                            import zipfile, xml.etree.ElementTree as _ET, io as _io
                            raw_bytes = uploaded_doc.read()
                            with zipfile.ZipFile(_io.BytesIO(raw_bytes)) as zf:
                                with zf.open("content.xml") as cx:
                                    tree = _ET.parse(cx)
                            ns = {
                                "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
                                "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
                            }
                            lines = []
                            for elem in tree.iter():
                                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                if tag in ("p", "h", "span") and elem.text and elem.text.strip():
                                    lines.append(elem.text.strip())
                                if elem.tail and elem.tail.strip():
                                    lines.append(elem.tail.strip())
                            extracted_text = "\n".join(lines)
                        except Exception as odt_err:
                            st.error(f"ODT read error: {odt_err}")
                    else:
                        # .docx
                        from docx import Document as DocxDocument
                        import io as _io
                        doc_obj = DocxDocument(_io.BytesIO(uploaded_doc.read()))
                        lines = [p.text.strip() for p in doc_obj.paragraphs if p.text.strip()]
                        for tbl in doc_obj.tables:
                            for row in tbl.rows:
                                for cell in row.cells:
                                    cell_txt = " ".join(
                                        p.text.strip() for p in cell.paragraphs if p.text.strip()
                                    )
                                    if cell_txt:
                                        lines.append(cell_txt)
                        extracted_text = "\n".join(lines)
                except Exception as ext_err:
                    st.error(f"File extraction error: {ext_err}")

                if extracted_text.strip():
                    with st.expander("🔍 View extracted text (optional)", expanded=False):
                        st.text_area("Extracted content",
                                     extracted_text[:3000] + ("\n…[truncated for display]" if len(extracted_text) > 3000 else ""),
                                     height=200, disabled=True, key="extracted_preview")
                    _run_ai_extraction(extracted_text, student['name'])
                elif not extracted_text:
                    st.warning("Could not extract any text from the file. Try pasting the text manually using the Paste tab.")

    # ── Review & save extracted incident ─────────────────────────────────────
    if st.session_state.get("ai_extracted_incident"):
        inc = st.session_state["ai_extracted_incident"]
        st.markdown("---")
        st.markdown("#### Review Extracted Incident")
        meta_col1, meta_col2, meta_col3 = st.columns(3)
        with meta_col1: inc["date"] = st.text_input("Incident Date (YYYY-MM-DD)", value=inc.get("date", ""), key="ai_inc_date")
        with meta_col2: inc["severity"] = st.slider("Severity", 1, 5, int(inc.get("severity", 3)), key="ai_inc_sev")
        with meta_col3: inc["sapol_reference"] = st.text_input("SAPOL Reference", value=inc.get("sapol_reference") or "", key="ai_inc_sapol")
        inc["outcomes"] = st.text_area("Outcomes", value=", ".join(inc.get("outcomes", [])) if isinstance(inc.get("outcomes"), list) else inc.get("outcomes", ""), key="ai_inc_outcomes", height=60)
        inc["notes"] = st.text_area("Additional Notes", value=inc.get("notes", ""), key="ai_inc_notes", height=60)
        st.markdown("##### Initial Entry")
        primary = inc.get("primary", {})
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            primary["time"] = st.text_input("Time", value=primary.get("time", ""), key="ai_p_time")
            primary["location"] = st.text_input("Location", value=primary.get("location", ""), key="ai_p_loc")
            primary["context"] = st.text_area("Antecedent", value=primary.get("context", ""), key="ai_p_ctx", height=100)
        with p_col2:
            primary["behaviour"] = st.text_area("Behaviour", value=primary.get("behaviour", ""), key="ai_p_beh", height=100)
            primary["consequence"] = st.text_area("Consequence", value=primary.get("consequence", ""), key="ai_p_con", height=100)
        inc["primary"] = primary
        additional = inc.get("additional_entries", [])
        if additional:
            for idx, entry in enumerate(additional):
                with st.expander(f"Entry {idx + 1} — {entry.get('time', '')}"):
                    a_col1, a_col2 = st.columns(2)
                    with a_col1:
                        entry["time"] = st.text_input("Time", value=entry.get("time", ""), key=f"ai_a_time_{idx}")
                        entry["location"] = st.text_input("Location", value=entry.get("location", ""), key=f"ai_a_loc_{idx}")
                        entry["context"] = st.text_area("Antecedent", value=entry.get("context", ""), key=f"ai_a_ctx_{idx}", height=80)
                    with a_col2:
                        entry["behaviour"] = st.text_area("Behaviour", value=entry.get("behaviour", ""), key=f"ai_a_beh_{idx}", height=80)
                        entry["consequence"] = st.text_area("Consequence", value=entry.get("consequence", ""), key=f"ai_a_con_{idx}", height=80)
            inc["additional_entries"] = additional
        st.markdown("---")
        save_col, clear_col = st.columns(2)
        with save_col:
            if st.button("💾 Save as Critical Incident", type="primary", key="save_ai_extracted", use_container_width=True):
                try:
                    outcomes_raw = inc.get("outcomes", "")
                    outcomes_list = [o.strip() for o in outcomes_raw.split(",") if o.strip()] if isinstance(outcomes_raw, str) else outcomes_raw
                    primary_data = inc.get("primary", {})
                    additional_data = inc.get("additional_entries", [])
                    sapol_ref = inc.get("sapol_reference", "") or None
                    if sapol_ref == "": sapol_ref = None
                    record = {
                        "student_id": student_id, "severity": int(inc.get("severity", 3)),
                        "reported_by": st.session_state.current_user.get("id"),
                        "created_at": f"{inc.get('date', str(date.today()))}T00:00:00",
                        "primary_location": primary_data.get("location", ""),
                        "primary_context": primary_data.get("context", ""),
                        "primary_time": primary_data.get("time", ""),
                        "primary_behaviour": (primary_data.get("behaviour_type") or primary_data.get("behaviour", "")).strip(),
                        "primary_consequence": primary_data.get("consequence", ""),
                        "additional_entries": additional_data, "outcomes": outcomes_list,
                        "sapol_reference": sapol_ref, "admin_summary": inc.get("notes", ""),
                        "status": "historical", "audit_trail": "[]", "include_audit_in_report": False,
                    }
                    supabase.table("critical_incidents").insert(record).execute()
                    st.session_state["ai_extracted_incident"] = None
                    # Explicitly refetch fresh data now, rather than deleting
                    # the cache and relying on init_state()'s lazy-load guard
                    # to correctly repopulate it on the next run — this
                    # guarantees the dashboard reflects the new incident
                    # immediately, with no dependency on rerun ordering.
                    _reload_into_session("incidents", load_incidents_from_db)
                    _reload_into_session("critical_incidents", load_critical_incidents_from_db)
                    _new_total = (
                        len([i for i in st.session_state.incidents if i["student_id"] == student_id])
                        + len([c for c in st.session_state.critical_incidents if c["student_id"] == student_id])
                    )
                    st.session_state["hist_incident_just_saved"] = _new_total
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
        with clear_col:
            if st.button("🗑️ Clear & Start Over", key="clear_ai", use_container_width=True):
                st.session_state["ai_extracted_incident"] = None
                st.rerun()


def render_admin_portal():
    if st.session_state.current_user.get("role") != "ADM":
        st.error("⛔ Access Denied: Admin privileges required")
        if st.button("⬅ Back to Landing", key="back_admin_denied"):
            go_to("landing")
        return
    st.markdown("## 🔧 Admin Portal")
    col1, col2 = st.columns([6, 1])
    with col1:
        if st.button("⬅ Back to Landing", key="back_admin"):
            go_to("landing")
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Active Students", "📦 Archived Students", "📊 System Overview", "👨‍💼 Staff Management", "🔑 Password Reset"])

    with tab1:
        st.markdown("### Student Management")
        active_students = [s for s in st.session_state.students if not s.get("archived", False)]
        st.markdown(f"**{len(active_students)} active students**")
        if active_students:
            for prog in ["JP", "PY", "SY"]:
                prog_students = [s for s in active_students if s.get("program") == prog]
                if prog_students:
                    st.markdown(f"**{prog}** ({len(prog_students)})")
                    for s in sorted(prog_students, key=lambda x: x.get("name","")):
                        sc1, sc2, sc3, sc4 = st.columns([3, 2, 2, 1])
                        with sc1: st.markdown(f"**{s.get('name','Unknown')}**")
                        with sc2: st.caption(f"EDID: {s.get('edid','—')}")
                        with sc3: st.caption(f"Grade: {s.get('grade','—')} · DOB: {s.get('dob','—')}")
                        with sc4:
                            if st.button("Archive", key=f"arch_{s['id']}", help="Archive student"):
                                s["archived"] = True
                                try:
                                    supabase.table("students").update({"archived": True}).eq("id", s["id"]).execute()
                                    st.session_state.students = load_students_from_db()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Could not archive: {e}")
                    st.markdown("---")
        else:
            st.info("No active students. Add students below.")

        with st.expander("➕ Add New Student", expanded=False):
            with st.form("add_student_form"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_first_name = st.text_input("First Name *", placeholder="Boston")
                    new_last_name  = st.text_input("Last Name *", placeholder="Murphy")
                    new_grade      = st.selectbox("Grade *", ["R","Y1","Y2","Y3","Y4","Y5","Y6","Y7","Y8","Y9","Y10","Y11","Y12"])
                with col2:
                    new_edid = st.text_input("EDID *", placeholder="ED123456")
                    new_dob  = st.date_input("Date of Birth *", value=date(2015, 1, 1))
                with col3:
                    new_program         = st.selectbox("Program *", ["JP", "PY", "SY"])
                    new_placement_start = st.date_input("Placement Start Date *", value=date.today())
                with col4:
                    st.write("")
                    new_placement_end = st.date_input("Placement End Date (Optional)", value=None)
                student_submitted = st.form_submit_button("Add Student", type="primary")
            if student_submitted:
                if not new_first_name or not new_last_name or not new_edid or not new_grade or not new_program:
                    st.error("Please complete all required fields marked with *")
                else:
                    new_student = {
                        "id": f"stu_{uuid.uuid4().hex[:8]}",
                        "first_name": new_first_name.strip(), "last_name": new_last_name.strip(),
                        "name": f"{new_first_name.strip()} {new_last_name.strip()}",
                        "edid": new_edid.strip(), "grade": new_grade, "dob": new_dob.isoformat(),
                        "program": new_program, "placement_start": new_placement_start.isoformat(),
                        "placement_end": new_placement_end.isoformat() if new_placement_end else None,
                        "archived": False
                    }
                    if save_student_to_db(new_student):
                        st.session_state.students = load_students_from_db()
                        st.success(f"✅ Added {new_student['name']} to {new_program}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save student to database")

        st.markdown("### Current Students")
        for program in ["JP", "PY", "SY"]:
            st.markdown(f"#### {PROGRAM_NAMES[program]}")
            program_students = [s for s in st.session_state.students if s["program"] == program and not s.get("archived", False)]
            if not program_students:
                st.caption("No students in this program"); continue
            for student in program_students:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{student['name']}**")
                        st.caption(f"Grade {student['grade']}")
                        if student.get('edid'): st.caption(f"🆔 EDID: {student['edid']}")
                    with col2:
                        if student.get('placement_start'):
                            start_date = datetime.fromisoformat(student['placement_start']).strftime('%d/%m/%Y')
                            st.caption(f"📅 Start: {start_date}")
                            start = datetime.fromisoformat(student['placement_start']).date()
                            end   = datetime.fromisoformat(student['placement_end']).date() if student.get('placement_end') else date.today()
                            st.caption(f"📊 {(end - start).days} days enrolled")
                        else:
                            st.caption("📅 Start: Not set")
                    with col3:
                        if student.get('placement_end'):
                            end_date = datetime.fromisoformat(student['placement_end']).strftime('%d/%m/%Y')
                            st.caption(f"📅 End: {end_date}")
                            st.caption("🔴 Inactive")
                        else:
                            st.caption("📅 End: Ongoing")
                            st.caption("🟢 Active")
                    with col4:
                        if st.button("✏️", key=f"edit_{student['id']}", help="Edit student"):
                            st.session_state.editing_student = student['id']
                            st.rerun()
                        if st.button("📦 Archive", key=f"archive_{student['id']}"):
                            student['archived'] = True
                            if supabase:
                                try:
                                    supabase.table('students').update({'archived': True}).eq('id', student['id']).execute()
                                    st.success(f"✅ {student['name']} archived")
                                except Exception as e:
                                    st.error(f"Archive failed: {e}")
                            st.rerun()
                if st.session_state.get("editing_student") == student['id']:
                    with st.expander("✏️ Edit Student Details", expanded=True):
                        with st.form(f"edit_form_{student['id']}"):
                            edit_col1, edit_col2 = st.columns(2)
                            with edit_col1:
                                default_start = datetime.fromisoformat(student['placement_start']).date() if student.get('placement_start') else date.today()
                                edit_start = st.date_input("Placement Start", value=default_start, key=f"edit_start_{student['id']}")
                            with edit_col2:
                                current_end = datetime.fromisoformat(student['placement_end']).date() if student.get('placement_end') else None
                                edit_end = st.date_input("Placement End (None = Ongoing)", value=current_end, key=f"edit_end_{student['id']}")
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.form_submit_button("💾 Save Placement Dates", type="primary"):
                                    student['placement_start'] = edit_start.isoformat()
                                    student['placement_end']   = edit_end.isoformat() if edit_end else None
                                    save_student_to_db(student)
                                    if "students" in st.session_state: del st.session_state["students"]
                                    st.session_state.editing_student = None
                                    st.success("✅ Placement dates saved.")
                                    st.rerun()
                            with col_cancel:
                                if st.form_submit_button("Cancel"):
                                    st.session_state.editing_student = None
                                    st.rerun()

                        st.markdown("---")
                        st.markdown("**📌 Placement Extensions**")
                        st.caption(
                            "Record any extensions to the original placement. "
                            "Extensions appear in the student's analysis alongside incident patterns."
                        )
                        _adm_exts = load_placement_extensions_from_db(student['id'])

                        with st.form(f"ext_form_{student['id']}"):
                            _ae1, _ae2, _ae3 = st.columns([2, 2, 3])
                            with _ae1: _adm_ef = st.date_input("From *", value=None, key=f"adm_ef_{student['id']}")
                            with _ae2: _adm_et = st.date_input("To *",   value=None, key=f"adm_et_{student['id']}")
                            with _ae3: _adm_er = st.text_input("Reason / context *", placeholder="e.g. Extended — positive progress", key=f"adm_er_{student['id']}")
                            if st.form_submit_button("➕ Add Extension"):
                                if _adm_ef and _adm_et and _adm_er.strip():
                                    if save_placement_extension_to_db(student['id'], _adm_ef.isoformat(), _adm_et.isoformat(), _adm_er.strip()):
                                        st.success(f"✅ Extension added")
                                        st.rerun()
                                else: st.error("Complete all three fields.")

                        if _adm_exts:
                            for _ex in _adm_exts:
                                try:
                                    _c1, _c2 = st.columns([5, 1])
                                    with _c1:
                                        st.markdown(f"📌 **{datetime.fromisoformat(_ex['from']).strftime('%-d %b %Y')} – {datetime.fromisoformat(_ex['to']).strftime('%-d %b %Y')}** — {_ex['reason']}")
                                    with _c2:
                                        if st.button("❌", key=f"rm_ext_{student['id']}_{_ex['id']}"):
                                            if delete_placement_extension_from_db(_ex['id']):
                                                st.rerun()
                                except: pass

    with tab2:
        st.markdown("### 📦 Archived Students")
        archived_students = [s for s in st.session_state.students if s.get('archived', False)]
        if not archived_students:
            st.info("No archived students.")
        else:
            for program in ["JP", "PY", "SY"]:
                prog_archived = [s for s in archived_students if s['program'] == program]
                if not prog_archived: continue
                st.markdown(f"#### {PROGRAM_NAMES[program]}")
                for student in prog_archived:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([4, 3, 2])
                        with col1:
                            st.markdown(f"**{student['name']}**")
                            st.caption(f"Grade {student['grade']} | EDID: {student.get('edid', 'N/A')}")
                        with col2:
                            if student.get('placement_start'):
                                st.caption(f"📅 Placement: {datetime.fromisoformat(student['placement_start']).strftime('%d/%m/%Y')} – {datetime.fromisoformat(student['placement_end']).strftime('%d/%m/%Y') if student.get('placement_end') else 'ongoing'}")
                            incident_count = (
                                len([i for i in st.session_state.incidents if i['student_id'] == student['id']])
                                + len([c for c in st.session_state.critical_incidents if c['student_id'] == student['id']])
                            )
                            st.caption(f"📋 {incident_count} incidents on record")
                        with col3:
                            if st.button("👁️ View Details", key=f"view_archived_{student['id']}", use_container_width=True):
                                go_to("student_dashboard", selected_student_id=student['id'])
                            if st.button("♻️ Restore", key=f"restore_{student['id']}"):
                                student['archived'] = False
                                if supabase:
                                    try:
                                        supabase.table('students').update({'archived': False}).eq('id', student['id']).execute()
                                        st.success(f"✅ {student['name']} restored")
                                    except Exception as e:
                                        st.error(f"Restore failed: {e}")
                                st.rerun()
                            if st.button("🗑️ Delete", key=f"permdelete_{student['id']}"):
                                st.session_state[f"confirm_delete_{student['id']}"] = True
                                st.rerun()
                            if st.session_state.get(f"confirm_delete_{student['id']}"):
                                st.warning(f"⚠️ Permanently delete {student['name']} and ALL their incident data?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("Yes, delete", key=f"yes_delete_{student['id']}", type="primary"):
                                        if supabase:
                                            try:
                                                supabase.table('incidents').delete().eq('student_id', student['id']).execute()
                                                supabase.table('critical_incidents').delete().eq('student_id', student['id']).execute()
                                                supabase.table('students').delete().eq('id', student['id']).execute()
                                            except Exception as e:
                                                st.error(f"Delete failed: {e}")
                                        st.session_state.students = [s for s in st.session_state.students if s['id'] != student['id']]
                                        # Also refresh incidents/critical_incidents — otherwise this
                                        # student's now-deleted records linger in the cached lists
                                        # and inflate site-wide totals elsewhere in the portal.
                                        if supabase:
                                            _reload_into_session("incidents", load_incidents_from_db)
                                            _reload_into_session("critical_incidents", load_critical_incidents_from_db)
                                        st.session_state[f"confirm_delete_{student['id']}"] = False
                                        st.rerun()
                                with col_no:
                                    if st.button("Cancel", key=f"no_delete_{student['id']}"):
                                        st.session_state[f"confirm_delete_{student['id']}"] = False
                                        st.rerun()

    with tab3:
        st.markdown("### System Overview")
        # ── PATCH 1 (admin): corrected whole-of-site totals ───────────────────
        _all_inc  = st.session_state.incidents
        _all_crit = st.session_state.critical_incidents
        _all_stu  = st.session_state.students
        _active_stu = len([s for s in _all_stu if not s.get('placement_end')])
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", len(_all_stu))
            st.caption(f"{_active_stu} active (no end date)")
        with col2:
            st.metric("Total Incidents", len(_all_inc) + len(_all_crit),
                      help="Regular incidents + critical incident ABCH forms")
        with col3:
            st.metric("Critical Incidents", len(_all_crit),
                      help="Completed ABCH critical incident forms")
        with col4:
            st.metric("Staff Members", len(st.session_state.staff))
        st.markdown("---")
        st.markdown("#### Students by Program")
        for prog in ["JP", "PY", "SY"]:
            _p_stu     = [s for s in _all_stu if s["program"] == prog]
            _p_active  = [s for s in _p_stu if not s.get('placement_end')]
            _p_ids     = {s["id"] for s in _p_stu}
            _p_inc     = len([i for i in _all_inc  if i.get("student_id") in _p_ids])
            _p_crit    = len([c for c in _all_crit if c.get("student_id") in _p_ids])
            st.write(f"**{PROGRAM_NAMES[prog]}:** {len(_p_stu)} students ({len(_p_active)} active) · {_p_inc + _p_crit} incidents ({_p_crit} critical)")

    with tab4:
        st.markdown("### Staff Management")
        with st.expander("➕ Add New Staff Member", expanded=False):
            with st.form("add_staff_form"):
                col1, col2 = st.columns(2)
                with col1:
                    staff_name     = st.text_input("Full Name *", placeholder="Jane Smith")
                    staff_email    = st.text_input("Email Address *", placeholder="jane.smith@school.edu.au")
                    staff_password = st.text_input("Initial Password *", type="password", value="demo123")
                with col2:
                    staff_role    = st.selectbox("Role *", ["TSS","Teacher","Leader","ADM"])
                    staff_program = st.selectbox("Program *", ["JP","PY","SY","All Programs"])
                    staff_phone   = st.text_input("Phone Number", placeholder="0412 345 678")
                staff_notes  = st.text_area("Notes (Optional)")
                submit_staff = st.form_submit_button("Add Staff Member", type="primary")
                if submit_staff:
                    if staff_name and staff_email and staff_password and staff_role:
                        if any(s.get("email","").lower() == staff_email.lower() for s in st.session_state.staff):
                            st.error(f"❌ Email {staff_email} already exists")
                        else:
                            new_staff = {
                                "id": f"staff_{uuid.uuid4().hex[:8]}",
                                "name": staff_name, "email": staff_email.lower().strip(),
                                "password": staff_password, "role": staff_role,
                                "program": staff_program if staff_program != "All Programs" else None,
                                "phone": staff_phone if staff_phone else None,
                                "notes": staff_notes if staff_notes else None,
                                "receive_critical_emails": True,
                                "created_date": date.today().isoformat()
                            }
                            if save_staff_to_db(new_staff):
                                # Force clean reload so DB-generated UUID is used
                                if "staff" in st.session_state:
                                    del st.session_state["staff"]
                                st.success(f"✅ Added {staff_name} to database")
                                st.rerun()
                            else:
                                st.error("❌ Failed to save staff member to database")

        st.markdown("---")
        st.markdown("### Current Staff")
        for role in ["ADM","Leader","Teacher","TSS"]:
            role_names = {"ADM":"Administrators","Leader":"Program Leaders","Teacher":"Teachers","TSS":"Support Staff"}
            role_staff = [s for s in st.session_state.staff if s.get("role") == role]
            if role_staff:
                st.markdown(f"#### {role_names[role]}")
                for staff in role_staff:
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.markdown(f"**{staff['name']}**")
                            st.caption(f"📧 {staff['email']}")
                            if staff.get('phone'): st.caption(f"📱 {staff['phone']}")
                        with col2:
                            st.caption(f"**Role:** {staff['role']}")
                            if staff.get('program'):
                                st.caption(f"**Program:** {PROGRAM_NAMES[staff['program']]}")
                            else:
                                st.caption("**Program:** All Programs")
                        with col3:
                            receives_emails = staff.get('receive_critical_emails', True)
                            st.caption("📬 Receives critical alerts" if receives_emails else "📪 No critical alerts")
                            if staff.get('created_date'): st.caption(f"Added: {staff['created_date']}")
                        with col4:
                            if st.button("✏️", key=f"edit_staff_{staff['id']}", help="Edit staff"):
                                st.session_state.editing_staff = staff['id']
                                st.rerun()
                    if st.session_state.get("editing_staff") == staff['id']:
                        with st.expander("✏️ Edit Staff Details", expanded=True):
                            with st.form(f"edit_staff_form_{staff['id']}"):
                                edit_col1, edit_col2 = st.columns(2)
                                with edit_col1:
                                    edit_name  = st.text_input("Name", value=staff['name'], key=f"edit_staff_name_{staff['id']}")
                                    edit_email = st.text_input("Email", value=staff['email'], key=f"edit_staff_email_{staff['id']}")
                                    edit_phone = st.text_input("Phone", value=staff.get('phone',''), key=f"edit_staff_phone_{staff['id']}")
                                with edit_col2:
                                    edit_role = st.selectbox("Role", ["TSS","Teacher","Leader","ADM"],
                                        index=["TSS","Teacher","Leader","ADM"].index(staff['role']),
                                        key=f"edit_staff_role_{staff['id']}")
                                    _prog_options = ["JP","PY","SY","All Programs"]
                                    _prog_val = staff.get('program') if staff.get('program') in ["JP","PY","SY"] else "All Programs"
                                    edit_program = st.selectbox("Program", _prog_options,
                                        index=_prog_options.index(_prog_val),
                                        key=f"edit_staff_program_{staff['id']}")
                                    edit_receive_emails = st.checkbox("Receive critical incident emails",
                                        value=staff.get('receive_critical_emails', True),
                                        key=f"edit_staff_emails_{staff['id']}")
                                edit_notes   = st.text_area("Notes", value=staff.get('notes',''), key=f"edit_staff_notes_{staff['id']}")
                                new_password = st.text_input("New Password (leave blank to keep current)",
                                    type="password", key=f"new_pass_{staff['id']}")
                                col_save, col_cancel, col_delete = st.columns([1,1,1])
                                with col_save:
                                    if st.form_submit_button("💾 Save Changes", type="primary"):
                                        staff['name']                    = edit_name
                                        staff['email']                   = edit_email.lower().strip()
                                        staff['phone']                   = edit_phone if edit_phone else None
                                        staff['role']                    = edit_role
                                        staff['program']                 = edit_program if edit_program != "All Programs" else None
                                        staff['receive_critical_emails'] = edit_receive_emails
                                        staff['notes']                   = edit_notes if edit_notes else None
                                        _pw_msg = ""
                                        if new_password:
                                            staff['password']      = new_password
                                            staff['password_hash'] = None
                                            if supabase:
                                                try:
                                                    supabase.table('staff').update({
                                                        'password':      new_password,
                                                        'password_hash': None,
                                                    }).eq('id', staff['id']).execute()
                                                    _pw_msg = " — password reset"
                                                except Exception as _pw_e:
                                                    st.error(f"❌ Password update failed: {_pw_e}")
                                        save_staff_to_db(staff)
                                        if "staff" in st.session_state:
                                            del st.session_state["staff"]
                                        st.session_state.editing_staff = None
                                        st.success(f"✅ Saved{_pw_msg}")
                                        st.rerun()
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancel"):
                                        st.session_state.editing_staff = None
                                        st.rerun()
                                with col_delete:
                                    if st.form_submit_button("🗑️ Delete"):
                                        if staff['role'] != 'ADM' or len([s for s in st.session_state.staff if s.get('role') == 'ADM']) > 1:
                                            st.session_state.staff.remove(staff)
                                            st.session_state.editing_staff = None
                                            st.success("✅ Staff member removed")
                                            st.rerun()
                                        else:
                                            st.error("❌ Cannot delete the last administrator")

        st.markdown("---")
        st.markdown("### 📧 Email Notification Recipients")
        email_recipients = [s for s in st.session_state.staff if s.get('receive_critical_emails', True)]
        if email_recipients:
            for recipient in email_recipients:
                st.write(f"• **{recipient['name']}** ({recipient['email']}) - {recipient['role']}")
        else:
            st.warning("⚠️ No staff members set to receive critical incident emails!")

    with tab5:
        st.markdown("### 🔑 Staff Password Reset")
        st.caption(
            "Use this to directly reset any staff member\'s password. "
            "The new password is saved immediately and the bcrypt hash is cleared — "
            "staff can log in straight away with the new password."
        )
        _pw_all = {s["id"]: f"{s['name']} ({s['email']})" for s in st.session_state.staff}
        if not _pw_all:
            st.info("No staff loaded — reload the page.")
        else:
            _pw_sel = st.selectbox("Staff member *", list(_pw_all.keys()),
                                   format_func=lambda x: _pw_all[x], key="pw_reset_sel")
            _pw_c1, _pw_c2 = st.columns(2)
            with _pw_c1:
                _pw_new  = st.text_input("New password *", type="password",
                                          placeholder="Min 6 characters", key="pw_reset_new")
            with _pw_c2:
                _pw_conf = st.text_input("Confirm password *", type="password",
                                          placeholder="Re-enter", key="pw_reset_conf")
            if st.button("🔑 Reset Password Now", type="primary", use_container_width=True, key="pw_reset_btn"):
                _target = next((s for s in st.session_state.staff if s["id"] == _pw_sel), None)
                if not _pw_new:
                    st.error("Enter a new password.")
                elif len(_pw_new) < 6:
                    st.error("Password must be at least 6 characters.")
                elif _pw_new != _pw_conf:
                    st.error("Passwords do not match.")
                elif not _target:
                    st.error("Staff member not found — reload the page.")
                elif not supabase:
                    st.error("Supabase not connected.")
                else:
                    try:
                        _res = supabase.table("staff").update({
                            "password":      _pw_new,
                            "password_hash": None,
                        }).eq("id", _target["id"]).execute()
                        if _res.data:
                            _target["password"]      = _pw_new
                            _target["password_hash"] = None
                            if "staff" in st.session_state:
                                del st.session_state["staff"]
                            st.success(f"✅ Password reset for **{_target['name']}** ({_target['email']})")
                            st.info(f"Email: `{_target['email']}` \u00b7 Password: `{_pw_new}`")
                        else:
                            st.error("Supabase returned no confirmation. Check the staff ID exists in the database.")
                    except Exception as _e:
                        st.error(f"❌ Reset failed: {_e}")

        st.markdown("---")
        st.markdown("### 🔧 Data Correction Tool")
        st.caption(
            "Fix behaviour labels directly in Supabase for any student. "
            "Queries the database live — no session state required. "
            "Use this to bulk-correct 'Other' or any mislabelled behaviour."
        )
        _dc_students = {s["id"]: s["name"] for s in st.session_state.students}
        if not _dc_students:
            st.info("No students loaded — reload the page.")
        else:
            _dc_stu = st.selectbox(
                "Select student *",
                list(_dc_students.keys()),
                format_func=lambda x: _dc_students[x],
                key="dc_stu"
            )

            # Load this student's current behaviour values LIVE from Supabase
            _dc_live_vals = []
            if st.button("🔍 Load current behaviour values from DB", key="dc_load", use_container_width=True):
                if supabase:
                    try:
                        _dc_r = supabase.table("incidents").select(
                            "id,behaviour_type,date,time"
                        ).eq("student_id", _dc_stu).execute()
                        st.session_state["dc_live_rows"] = _dc_r.data or []
                    except Exception as _le:
                        st.error(f"Load failed: {_le}")

            _dc_rows = st.session_state.get("dc_live_rows", [])
            if _dc_rows:
                # Show unique behaviour values found
                _dc_vals = sorted(set(
                    r.get("behaviour_type","").strip()
                    for r in _dc_rows
                    if r.get("behaviour_type","").strip()
                ))
                st.info(
                    f"Found **{len(_dc_rows)} incident(s)** for {_dc_students.get(_dc_stu,'this student')}. "
                    f"Behaviour values in DB: {', '.join(f'**{v}**' for v in _dc_vals)}"
                )

                _dc_col1, _dc_col2 = st.columns(2)
                with _dc_col1:
                    _dc_old = st.selectbox(
                        "Current behaviour to replace *",
                        _dc_vals,
                        key="dc_old_sel"
                    )
                with _dc_col2:
                    _dc_new = st.selectbox(
                        "Replace with *",
                        [b for b in BEHAVIOUR_TYPES if not b.startswith("---")],
                        key="dc_new_sel"
                    )

                # Show matching rows
                _dc_matching = [r for r in _dc_rows
                                if r.get("behaviour_type","").strip() == _dc_old]
                if _dc_matching:
                    st.markdown(
                        f"<div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;"
                        f"padding:.5rem .85rem;margin:.4rem 0;font-size:.82rem;'>"
                        f"<b>{len(_dc_matching)} incident(s)</b> will be changed from "
                        f"<code>{_dc_old}</code> → <code>{_dc_new}</code>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    for r in _dc_matching[:8]:
                        st.caption(f"  • {r.get('date','?')}  {str(r.get('time',''))[:5]}  — {r.get('behaviour_type','')}")
                    if len(_dc_matching) > 8:
                        st.caption(f"  … and {len(_dc_matching)-8} more")

                    _dc_col3, _dc_col4 = st.columns(2)
                    with _dc_col3:
                        if st.button(
                            f"✅ Apply — update {len(_dc_matching)} record(s)",
                            type="primary", key="dc_apply", use_container_width=True
                        ):
                            if not supabase:
                                st.error("Supabase not connected.")
                            else:
                                _updated = 0
                                _errors  = 0
                                for r in _dc_matching:
                                    try:
                                        supabase.table("incidents").update(
                                            {"behaviour_type": _dc_new}
                                        ).eq("id", r["id"]).execute()
                                        _updated += 1
                                    except Exception as _ue:
                                        _errors += 1
                                        st.error(f"Failed on {r['id']}: {_ue}")
                                # Clear both session caches so fresh data loads
                                for _k in ["incidents", "dc_live_rows"]:
                                    if _k in st.session_state:
                                        del st.session_state[_k]
                                if _updated:
                                    st.success(
                                        f"✅ Updated {_updated} incident(s): "
                                        f"'{_dc_old}' → '{_dc_new}'"
                                        + (f" ({_errors} errors)" if _errors else "")
                                    )
                                    st.info("Reload the student's Analysis page to see the updated charts.")
                    with _dc_col4:
                        if st.button("🔄 Reload from DB", key="dc_reload", use_container_width=True):
                            if "dc_live_rows" in st.session_state:
                                del st.session_state["dc_live_rows"]
                            st.rerun()
                else:
                    st.info(f"No incidents found with behaviour_type = '{_dc_old}'.")

        st.markdown("---")
        st.markdown("### 🎚️ Correct Critical Incident Severity")
        st.caption(
            "Fix the severity level on a specific critical incident. "
            "Remember: a critical incident does not automatically mean severity 4/severity 5 — "
            "most incidents sit in the Coping zone (severity 1–3)."
        )
        _sv_students = {s["id"]: s["name"] for s in st.session_state.students}
        _sv_stu = st.selectbox(
            "Student *", list(_sv_students.keys()),
            format_func=lambda x: _sv_students[x], key="sv_stu"
        )
        if st.button("🔍 Load critical incidents from DB", key="sv_load", use_container_width=True):
            if supabase:
                try:
                    _sv_r = supabase.table("critical_incidents").select(
                        "id,severity,created_at,primary_behaviour"
                    ).eq("student_id", _sv_stu).execute()
                    st.session_state["sv_live_rows"] = _sv_r.data or []
                except Exception as _sve:
                    st.error(f"Load failed: {_sve}")

        _sv_rows = st.session_state.get("sv_live_rows", [])
        if _sv_rows:
            _sv_opts = {
                r["id"]: (
                    f"{(r.get('created_at') or '')[:10]}  "
                    f"Sev {r.get('severity','?')}  ·  "
                    f"{str(r.get('primary_behaviour',''))[:50]}"
                )
                for r in _sv_rows
            }
            _sv_sel = st.selectbox(
                "Select incident *",
                list(_sv_opts.keys()),
                format_func=lambda x: _sv_opts[x],
                key="sv_sel"
            )
            _sv_new = st.select_slider(
                "New severity level *",
                options=[1, 2, 3, 4, 5],
                value=3,
                key="sv_new"
            )
            _sv_zone = ("Coping zone" if _sv_new <= 3 else "Outside window")
            _sv_zone_col = "#92400e" if _sv_new <= 3 else "#dc2626"
            st.markdown(
                f"<div style='background:#fef9c3;border-left:4px solid #eab308;"
                f"border-radius:6px;padding:.5rem .9rem;font-size:.83rem;'>"  
                f"Setting to <b>Level {_sv_new}</b> — "
                f"<span style='color:{_sv_zone_col};font-weight:700;'>{_sv_zone}</span>"  
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button(
                f"✅ Update severity to Level {_sv_new}",
                type="primary", key="sv_apply", use_container_width=True
            ):
                if supabase:
                    try:
                        supabase.table("critical_incidents").update(
                            {"severity": _sv_new}
                        ).eq("id", _sv_sel).execute()
                        for _k in ["sv_live_rows","critical_incidents"]:
                            if _k in st.session_state: del st.session_state[_k]
                        st.success(f"✅ Severity updated to Level {_sv_new}.")
                        st.info("Reload the student's Analysis page to see the updated trajectory chart.")
                    except Exception as _sve2:
                        st.error(f"Update failed: {_sve2}")

        st.markdown("---")
        st.markdown("### 🤖 Reclassify Historical Incident Behaviour Types")
        st.caption(
            "For historical critical incidents where the behaviour was saved as free text, "
            "this tool reads the narrative and maps it to the correct clinical label. "
            "Works on the critical_incidents table (primary_behaviour field). "
            "Preview first, then apply."
        )
        _rc_students = {s["id"]: s["name"] for s in st.session_state.students}
        _rc_stu = st.selectbox("Student", list(_rc_students.keys()),
                               format_func=lambda x: _rc_students[x], key="rc_stu")
        _rc_preview = st.checkbox("Preview only (do not save)", value=True, key="rc_preview_chk")
        _use_ai = st.checkbox(
            "Use AI (Groq) for ambiguous cases",
            value=True, key="rc_use_ai",
            help="Falls back to keyword matching if AI is unavailable"
        )
        if st.button("🔍 Scan & Reclassify", type="primary", key="rc_apply", use_container_width=True):
            if not supabase:
                st.error("Supabase not connected.")
            else:
                try:
                    _rc_res = supabase.table("critical_incidents").select(
                        "id,primary_behaviour,severity"
                    ).eq("student_id", _rc_stu).execute()
                    _rc_rows = _rc_res.data or []
                except Exception as _rce:
                    st.error(f"Load failed: {_rce}")
                    _rc_rows = []

                if not _rc_rows:
                    st.info("No critical incidents found for this student.")
                else:
                    # Keyword map (same as _CRIT_BEH_KEYWORDS in analysis)
                    _RC_KW = [
                        (["self-harm","self harm","hurt himself","hurt herself","scratch","bite himself",
                          "bite herself","bang head","banged head","hit himself","hit herself"],
                         "Self-injurious behaviour"),
                        (["threw","throw","thrown","hurled","launched","flung","pushed chair",
                          "knocked over","flipped","tipped","toppled","pushed desk","flipped table",
                          "knocked chair","tipped chair"],
                         "Throwing objects"),
                        (["destroyed","broke","smashed","kicked wall","punched wall","ripped","torn",
                          "property damage","damaged"],
                         "Property destruction"),
                        (["hit peer","hit a peer","hit student","punch peer","punched peer",
                          "kicked peer","kicked a student","shoved peer","pushed peer","bit peer",
                          "grabbed peer","scratched peer","attacked peer","spat at peer"],
                         "Physical aggression toward peer"),
                        (["hit staff","hit teacher","hit adult","punch staff","punched teacher",
                          "kicked staff","kicked teacher","kicked adult","shoved staff","pushed staff",
                          "bit staff","grabbed staff","scratched staff","spat at staff","spat at teacher",
                          "hit the teacher","struck","swung at"],
                         "Physical aggression toward adult"),
                        (["growl","growled","snarl","snarled","scream at","screamed at","yell at",
                          "yelled at","swore at","sworn at","name call","called names","insulted",
                          "threatened","verbal abuse","verbally abused"],
                         "Verbal aggression toward peer"),
                        (["swore at teacher","swore at staff","yelled at teacher","yelled at staff",
                          "screamed at teacher","screamed at staff","abused staff","abused teacher",
                          "threatened staff","threatened teacher"],
                         "Verbal aggression toward adult"),
                        (["ran from","ran out","left the room","left class","walked out","walked away",
                          "fled","ran away","elopement","eloped","absconded","left the building",
                          "left the school","left school grounds"],
                         "Unsanctioned departure (elopement)"),
                        (["refus","refused","refusing","won't","will not","not going to",
                          "declined to","passive","non-complian","non complian","wouldn't"],
                         "Task refusal / passive non-compliance"),
                        (["shut down","shutdown","withdrew","withdrawal","stopped responding",
                          "stopped talking","silent","mute","unresponsive","disengaged",
                          "curled up","head down","under desk"],
                         "Shutdown / complete withdrawal"),
                        (["noise","noises","humming","clicking","tapping","inappropriate sound"],
                         "Inappropriate vocalisation / noises"),
                        (["verbal refus","said no","verbally refus","stated he would not",
                          "stated she would not"],
                         "Verbal refusal of instruction"),
                    ]

                    def _kw_classify(text):
                        t = (text or "").lower()
                        for kws, label in _RC_KW:
                            if any(kw in t for kw in kws):
                                return label
                        return None

                    _pending, _already_clean = [], []
                    _known_types = set(b for b in BEHAVIOUR_TYPES if not b.startswith("---"))
                    for row in _rc_rows:
                        pb = (row.get("primary_behaviour") or "").strip()
                        if pb in _known_types:
                            _already_clean.append(pb)
                        else:
                            # Try keyword map
                            _kw = _kw_classify(pb)
                            _pending.append({"id": row["id"], "raw": pb, "suggested": _kw})

                    st.markdown(f"**Scan results:** {len(_already_clean)} already use canonical labels · {len(_pending)} need reclassification")

                    if _pending:
                        # Use Groq AI for any that keyword-map couldn't resolve
                        _ambiguous = [p for p in _pending if p["suggested"] is None]
                        if _ambiguous and _use_ai:
                            GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
                            if GROQ_KEY:
                                with st.spinner(f"AI classifying {len(_ambiguous)} ambiguous record(s)..."):
                                    try:
                                        _canonical_list = [b for b in BEHAVIOUR_TYPES if not b.startswith("---")]
                                        for _amb in _ambiguous:
                                            _ai_prompt = (
                                                "You are classifying a school behaviour incident. "
                                                "Map this behaviour description to the closest label from the list below. "
                                                "Reply with ONLY the exact label text, nothing else.\n\n"
                                                f"Behaviour description: {_amb['raw'][:300]}\n\n"
                                                "Labels:\n" + "\n".join(f"- {l}" for l in _canonical_list)
                                            )
                                            _ai_label = groq_ai_call(_ai_prompt, max_tokens=60, temperature=0)
                                            _ai_label = _ai_label.strip().strip("-").strip()
                                            if _ai_label in _known_types:
                                                _amb["suggested"] = _ai_label
                                                _amb["ai"] = True
                                    except Exception as _ai_e:
                                        st.warning(f"AI classification unavailable: {_ai_e}")

                        st.markdown("**Proposed reclassifications:**")
                        for p in _pending:
                            _src_label = p.get("raw","")[:80]
                            _tgt_label = p.get("suggested")
                            _via = " (AI)" if p.get("ai") else " (keyword)" if _tgt_label else ""
                            if _tgt_label:
                                st.markdown(
                                    f"<div style='background:#f0fdf4;border-left:3px solid #22c55e;"
                                    f"border-radius:6px;padding:.35rem .75rem;margin:.2rem 0;font-size:.8rem;'>"  
                                    f"<b>→ {_tgt_label}</b>{_via}<br>"
                                    f"<span style='color:#64748b;'>{_src_label}</span></div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f"<div style='background:#fff7ed;border-left:3px solid #f59e0b;"
                                    f"border-radius:6px;padding:.35rem .75rem;margin:.2rem 0;font-size:.8rem;'>"  
                                    f"⚠️ <b>Could not classify</b> — manual fix needed<br>"
                                    f"<span style='color:#64748b;'>{_src_label}</span></div>",
                                    unsafe_allow_html=True
                                )

                        if not _rc_preview:
                            _applied = 0
                            for p in _pending:
                                if p.get("suggested"):
                                    try:
                                        supabase.table("critical_incidents").update(
                                            {"primary_behaviour": p["suggested"]}
                                        ).eq("id", p["id"]).execute()
                                        _applied += 1
                                    except Exception as _ue:
                                        st.error(f"Update failed for {p['id']}: {_ue}")
                            if "critical_incidents" in st.session_state:
                                del st.session_state["critical_incidents"]
                            st.success(f"✅ Applied {_applied} reclassification(s) to critical_incidents table.")
                        else:
                            st.info("Preview mode — tick off 'Preview only' and run again to apply.")

        st.markdown("---")
        st.markdown("### 🧪 Test a Login")
        st.caption("Verify credentials work before notifying a staff member.")
        _t_email = st.text_input("Email", placeholder="staff@schools.sa.edu.au", key="tl_email")
        _t_pw    = st.text_input("Password", type="password", key="tl_pw")
        if st.button("Test", key="tl_btn", use_container_width=True):
            if _t_email and _t_pw:
                _fresh = load_staff_from_db() if supabase else st.session_state.staff
                _m = next((s for s in _fresh if s.get("email","").lower() == _t_email.lower().strip()), None)
                if not _m:
                    st.error(f"No staff record found for: {_t_email}")
                else:
                    _ok, _method = False, ""
                    _h = (_m.get("password_hash") or "")
                    _p = (_m.get("password") or "")
                    if _h:
                        try:
                            _ok = bcrypt.checkpw(_t_pw.encode(), _h.encode() if isinstance(_h, str) else _h)
                            _method = "bcrypt hash"
                        except Exception:
                            pass
                    if not _ok and _p:
                        _ok = (_p == _t_pw)
                        _method = "plaintext password"
                    if _ok:
                        st.success(f"✅ Login would succeed for **{_m['name']}** (matched via {_method})")
                    else:
                        st.error(
                            f"Login would FAIL for **{_m['name']}**. "
                            f"password_hash: {'set' if _h else 'empty/null'}. "
                            f"password: {'set' if _p else 'empty/null'}. "
                            "Run the Password Reset above if both are empty."
                        )
            else:
                st.warning("Enter both email and password to test.")


def render_support_plan_page():
    """Student-lens Behaviour Support Plan — a living document per student.
    Data-derived sections (Target Behaviours, Possible Function, Known
    Triggers, Data/Monitoring) are computed live from current incident data
    every time this page loads. Staff/student-authored sections are saved
    to the database and are never touched by that live computation."""
    student_id = st.session_state.get("selected_student_id")
    student = get_student(student_id)
    if not student:
        st.error("No student selected"); return

    st.markdown(f"## 📋 Behaviour Support Plan — {student['name']}")
    st.caption("Target Behaviours, Possible Function, Known Triggers, and Data/Monitoring update "
               "automatically from incident data every time this page is opened. Everything else is "
               "written by staff and/or the student, and is saved separately — it's never overwritten.")

    col_back1, col_back2 = st.columns(2)
    with col_back1:
        if st.button("⬅ Back", key="sp_back"):
            go_to("student_dashboard", selected_student_id=student_id)
    with col_back2:
        if st.button("📈 Full Analysis", key="sp_to_analysis"):
            go_to("student_analysis", selected_student_id=student_id)

    # ── Assemble this student's incident data (same pattern as Dashboard) ──
    incidents = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    critical  = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]
    quick_df = pd.DataFrame(incidents) if incidents else pd.DataFrame()
    crit_df  = pd.DataFrame(critical) if critical else pd.DataFrame()
    if not quick_df.empty:
        quick_df["incident_type"] = "Quick"
        quick_df["date_parsed"] = _parse_dates(quick_df["date"])
    if not crit_df.empty:
        crit_df["incident_type"] = "Critical"
        _crit_dates = crit_df["created_at"] if "created_at" in crit_df.columns else pd.Series([None]*len(crit_df))
        crit_df["date_parsed"] = _parse_dates(_crit_dates)
        crit_df["severity"] = crit_df["severity"].fillna(5).astype(int) if "severity" in crit_df.columns else 5
        crit_df["behaviour_type"] = crit_df["ABCH_primary"].apply(
            lambda d: d.get("behaviour", "") if isinstance(d, dict) else "") if "ABCH_primary" in crit_df.columns else ""
        crit_df["antecedent"] = crit_df["ABCH_primary"].apply(
            lambda d: d.get("context", "") if isinstance(d, dict) else "") if "ABCH_primary" in crit_df.columns else ""
        crit_df["location"] = crit_df["ABCH_primary"].apply(
            lambda d: d.get("location", "") if isinstance(d, dict) else "") if "ABCH_primary" in crit_df.columns else ""
        if "location" in crit_df.columns:
            crit_df["location"] = crit_df["location"].apply(normalise_location)
    full_df = pd.concat([quick_df, crit_df], ignore_index=True) if not quick_df.empty or not crit_df.empty else pd.DataFrame()
    if not full_df.empty and "date_parsed" in full_df.columns:
        full_df = full_df.dropna(subset=["date_parsed"])

    # ── Live, auto-computed sections ────────────────────────────────────
    _sp_target_behaviours, _sp_function, _sp_triggers, _sp_monitoring, _sp_strategies = [], "", [], "", []
    if not full_df.empty and "behaviour_type" in full_df.columns:
        _bcounts = full_df["behaviour_type"].dropna()
        _bcounts = _bcounts[_bcounts.astype(str).str.strip() != ""].value_counts()
        _sp_target_behaviours = _bcounts.head(4).index.tolist()

        top_beh     = full_df["behaviour_type"].mode()[0] if len(full_df) else "Unknown"
        top_ant     = full_df["antecedent"].mode()[0] if "antecedent" in full_df.columns and len(full_df) else "Unknown"
        top_loc     = full_df["location"].mode()[0] if "location" in full_df.columns and len(full_df) else "Unknown"
        top_session = full_df["session"].mode()[0] if "session" in full_df.columns and len(full_df) else "Unknown"
        try:
            _hyp = generate_strong_clinical_hypothesis(full_df, top_ant, top_beh, top_loc, top_session, student["name"])
            _sp_function = _hyp.get("detail", {}).get("Behavioural Function") or _hyp.get("summary", "")
        except Exception:
            _sp_function = ""

        _cats = _top_categories(full_df, n=3)
        _sp_triggers = _cats

        _total = len(full_df)
        _crit_n = len(full_df[full_df.get("incident_type", "Quick") == "Critical"]) if "incident_type" in full_df.columns else 0
        _sp_monitoring = (
            f"{_total} incident(s) on record. Most frequent behaviour: {_bcounts.index[0] if len(_bcounts) else '—'} "
            f"({int(_bcounts.iloc[0])} occurrence(s)). Peak time: {top_session}. Hotspot location: {normalise_location(top_loc)}. "
            f"{_crit_n} critical incident(s)."
        )
        if _cats:
            _picked = []
            for cat in _cats[:2]:
                _picked.extend(BSEM_STRATEGY_LIBRARY.get(cat, [])[:2])
            _sp_strategies = _picked

    st.markdown("---")
    st.markdown("#### 🎯 Target Behaviours  *(auto, from incident data)*")
    if _sp_target_behaviours:
        for b in _sp_target_behaviours: st.markdown(f"- {b}")
    else:
        st.caption("Not enough data yet — log some incidents to populate this section.")

    st.markdown("#### 🔍 Possible Function of the Behaviour  *(auto, from incident data)*")
    st.markdown(_sp_function or "_Not enough data yet._")

    st.markdown("#### ⚡ Known Triggers / Precipitating Factors  *(auto, from incident data)*")
    if _sp_triggers:
        for t in _sp_triggers: st.markdown(f"- {t}")
    else:
        st.caption("Not enough data yet.")

    st.markdown("#### 🛡️ Proactive Strategies — suggested starting point  *(auto, from BSEM library)*")
    if _sp_strategies:
        for s in _sp_strategies:
            st.markdown(f"- **[{s['domain']}]** {s['strategy']}")
    else:
        st.caption("Not enough data yet to suggest strategies.")

    st.markdown("#### 📊 Data / Monitoring  *(auto, from incident data)*")
    st.markdown(_sp_monitoring or "_Not enough data yet._")

    st.markdown("---")
    st.markdown("### ✏️ Staff & Student Sections — written and saved here")

    _plan = load_support_plan_from_db(student_id)

    with st.form("support_plan_form"):
        st.markdown("**Plan details**")
        pc1, pc2 = st.columns(2)
        with pc1:
            _f_teacher = st.text_input("Class teacher", value=_plan.get("class_teacher","") or "")
            _f_start = st.date_input("Date commenced", value=(
                datetime.fromisoformat(_plan["date_commenced"]).date() if _plan.get("date_commenced") else date.today()))
        with pc2:
            _f_support = st.text_input("Support staff", value=_plan.get("support_staff","") or "")
            _f_review = st.date_input("Review date", value=(
                datetime.fromisoformat(_plan["review_date"]).date() if _plan.get("review_date") else date.today()))

        st.markdown("**Student Profile**")
        _f_strengths = st.text_area("Strengths", value=_plan.get("strengths","") or "", height=80)
        _f_interests = st.text_area("Interests", value=_plan.get("interests","") or "", height=80)
        _f_purpose = st.text_area("Purpose of this plan", value=_plan.get("purpose","") or "", height=80)

        st.markdown("**Early Warning Signs**")
        _f_ews = st.text_area("What does this look like for this student?", value=_plan.get("early_warning_signs","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Additional Proactive Strategies** *(beyond the suggestions above)*")
        _f_proactive_add = st.text_area("Additional proactive strategies", value=_plan.get("proactive_strategies_additional","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Teaching Strategies**")
        _f_teaching = st.text_area("What will be explicitly taught?", value=_plan.get("teaching_strategies","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Response to Early Signs**")
        st.caption("Regulate first — at this stage the goal is co-regulation, not correction or reasoning.")
        _f_resp_early = st.text_area("Staff response to early signs", value=_plan.get("response_early_signs","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Response to Escalation**")
        st.caption("The nervous system is in survival mode here — safety and calm presence, not words or logic, are the intervention.")
        _f_resp_esc = st.text_area("Staff response to escalation", value=_plan.get("response_escalation","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Safety / Risk Management**")
        _f_safety = st.text_area("Safety and risk management", value=_plan.get("safety_risk_management","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Post-Incident / Repair**")
        st.caption("Relate, then reason — reconnect with the student first; a debrief or consequence conversation only lands once they're genuinely calm.")
        _f_repair = st.text_area("Post-incident and repair process", value=_plan.get("post_incident_repair","") or "", height=90, label_visibility="collapsed")

        st.markdown("**Recovery Time**")
        st.caption("Roughly how long this student typically needs to regulate/recover — appears in the student-friendly version as 'How long I need.'")
        _f_recovery = st.text_input("Recovery time", value=_plan.get("recovery_time","") or "", placeholder="e.g. Usually 10-15 minutes in the quiet space", label_visibility="collapsed")

        st.markdown("**Reinforcement**")
        _f_reinforce = st.text_area("How positive behaviour is reinforced", value=_plan.get("reinforcement","") or "", height=80, label_visibility="collapsed")

        st.markdown("**Adjustments / Supports**")
        _f_adjustments = st.text_area("Adjustments and supports in place", value=_plan.get("adjustments_supports","") or "", height=80, label_visibility="collapsed")

        st.markdown("**Short-Term Goals**")
        _f_goals = st.text_area("Short-term goals", value=_plan.get("short_term_goals","") or "", height=80, label_visibility="collapsed")

        st.markdown("**🗣️ Student Voice** — in the student's own words")
        _f_voice = st.text_area("What the student says about this themselves", value=_plan.get("student_voice","") or "", height=100, label_visibility="collapsed")

        if st.form_submit_button("💾 Save Plan", type="primary", use_container_width=True):
            _updated_by = (
                st.session_state.current_user.get("name", "unknown")
                if st.session_state.get("current_user") else "unknown"
            )
            _plan_data = {
                "class_teacher": _f_teacher, "support_staff": _f_support,
                "date_commenced": _f_start.isoformat() if _f_start else None,
                "review_date": _f_review.isoformat() if _f_review else None,
                "strengths": _f_strengths, "interests": _f_interests, "purpose": _f_purpose,
                "early_warning_signs": _f_ews, "proactive_strategies_additional": _f_proactive_add,
                "teaching_strategies": _f_teaching, "response_early_signs": _f_resp_early,
                "response_escalation": _f_resp_esc, "safety_risk_management": _f_safety,
                "post_incident_repair": _f_repair, "recovery_time": _f_recovery, "reinforcement": _f_reinforce,
                "adjustments_supports": _f_adjustments, "short_term_goals": _f_goals,
                "student_voice": _f_voice,
            }
            if save_support_plan_to_db(student_id, _plan_data, updated_by=_updated_by):
                st.success("✅ Plan saved.")
                st.rerun()

    if _plan.get("last_updated_by"):
        st.caption(f"Last updated by {_plan['last_updated_by']}"
                   + (f" on {_plan['last_updated_at'][:16].replace('T',' ')}" if _plan.get("last_updated_at") else ""))

    st.markdown("---")
    _dl_col1, _dl_col2 = st.columns(2)
    with _dl_col1:
        if st.button("📥 Generate Full Plan (Word)", key="sp_download_btn", use_container_width=True):
            _sp_docx = generate_support_plan_docx(
                student, _plan, _sp_target_behaviours, _sp_function, _sp_triggers, _sp_strategies, _sp_monitoring)
            st.download_button(
                "📄 Download Behaviour Support Plan (Word)", _sp_docx,
                file_name=f"BSP_{student['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="sp_download_dl",
            )
    with _dl_col2:
        if st.button("🧒 Generate Student-Friendly Version (Word)", key="sp_kid_btn", use_container_width=True):
            _sp_kid_docx = generate_student_friendly_plan_docx(student, _plan, _sp_strategies, _sp_triggers)
            st.download_button(
                "📄 Download My Plan (Word)", _sp_kid_docx,
                file_name=f"MyPlan_{student['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="sp_kid_dl",
            )
    st.caption("The student-friendly version pulls from the same saved plan, kept short and in plain "
               "language, and leaves out anything clinical (hypothesis, triggers, escalation/safety "
               "protocols) that belongs in the staff version only.")


def generate_support_plan_docx(student, plan, target_behaviours, function_text, triggers, strategies, monitoring_text):
    """Word export of the Behaviour Support Plan — combines the live
    auto-computed sections with whatever staff/student have written and
    saved, in the DfE-style template structure."""
    from docx import Document
    from docx.shared import Pt, Cm
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2)

    doc.add_heading(f"Behaviour Support Plan — {student['name']}", level=1)
    p = doc.add_paragraph()
    p.add_run(f"Class teacher: {plan.get('class_teacher','—')}    Support staff: {plan.get('support_staff','—')}")
    p2 = doc.add_paragraph()
    p2.add_run(f"Date commenced: {plan.get('date_commenced','—')}    Review date: {plan.get('review_date','—')}")

    def _section(title, body):
        doc.add_heading(title, level=2)
        if isinstance(body, list):
            for item in body:
                doc.add_paragraph(f"• {item}", style=None)
        else:
            doc.add_paragraph(body or "—")

    _section("Strengths", plan.get("strengths"))
    _section("Interests", plan.get("interests"))
    _section("Purpose of This Plan", plan.get("purpose"))
    _section("Target Behaviours (auto — from incident data)", target_behaviours or "Not enough data yet.")
    _section("Possible Function of the Behaviour (auto — from incident data)", function_text or "Not enough data yet.")
    _section("Known Triggers / Precipitating Factors (auto — from incident data)", triggers or "Not enough data yet.")
    _section("Early Warning Signs", plan.get("early_warning_signs"))
    _section("Proactive Strategies — suggested (auto — from BSEM library)",
              [f"[{s['domain']}] {s['strategy']}" for s in strategies] if strategies else "Not enough data yet.")
    _section("Additional Proactive Strategies", plan.get("proactive_strategies_additional"))
    _section("Teaching Strategies", plan.get("teaching_strategies"))
    _section("Response to Early Signs", plan.get("response_early_signs"))
    _section("Response to Escalation", plan.get("response_escalation"))
    _section("Safety / Risk Management", plan.get("safety_risk_management"))
    _section("Post-Incident / Repair", plan.get("post_incident_repair"))
    _section("Reinforcement", plan.get("reinforcement"))
    _section("Adjustments / Supports", plan.get("adjustments_supports"))
    _section("Data / Monitoring (auto — from incident data)", monitoring_text or "Not enough data yet.")
    _section("Short-Term Goals", plan.get("short_term_goals"))
    _section("Student Voice", plan.get("student_voice"))

    p_footer = doc.add_paragraph()
    p_footer.add_run(f"\nGenerated from CLC-LBU Behaviour Support Tool — {datetime.now().strftime('%d/%m/%Y %H:%M')}").italic = True
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _first_lines(text: str, max_items: int = 3) -> list[str]:
    """Break staff-written text into a few short standalone lines,
    splitting on newlines/semicolons/sentence breaks and capping the
    count — a deterministic way to keep the student-facing version
    brief without rewriting anyone's actual words."""
    if not text or not isinstance(text, str):
        return []
    _raw = text.replace("•", "\n").replace(";", "\n")
    _lines = [l.strip(" -\n\t") for l in re.split(r'\n|(?<=[.!?])\s+', _raw) if l.strip(" -\n\t")]
    return _lines[:max_items]


@st.cache_data(ttl=86400)
def get_arasaac_symbol_bytes(keyword: str):
    """Fetch a real ARASAAC pictogram — a free, open-license symbol set
    built for AAC/visual supports, already used in this portal's Visual
    Support Tools — for a fixed, well-defined keyword. Returns PNG bytes,
    or None if the lookup/download fails for any reason. Never raises:
    a network hiccup just means the plan falls back to its emoji-only
    look rather than breaking the document. Only used for fixed section
    concepts (me/help/goal/talk) this code controls — not for arbitrary
    free text, since a mismatched auto-picked symbol could pair the
    wrong picture with someone's actual words."""
    try:
        search_url = f"https://api.arasaac.org/api/pictograms/en/search/{urllib.parse.quote(keyword)}"
        resp = requests.get(search_url, timeout=5)
        if resp.status_code != 200:
            return None
        results = resp.json()
        if not results:
            return None
        symbol_id = results[0]["_id"]
        img_url = f"https://static.arasaac.org/pictograms/{symbol_id}/{symbol_id}_500.png"
        img_resp = requests.get(img_url, timeout=5)
        if img_resp.status_code == 200:
            return img_resp.content
    except Exception:
        pass
    return None


CHALLENGE_SIMPLE = {
    "Peer": "Getting along with other kids",
    "Transition": "Changing from one thing to another",
    "Instructions": "Being told what to do",
    "Engagement": "Schoolwork that feels hard",
    "Sensory": "Loud noises, bright lights, or busy spaces",
    "Other": "Unexpected changes",
}


def generate_student_friendly_plan_docx(student, plan, strategies, triggers=None):
    """A short, plain-language version of the same saved plan, for the
    student themselves. Deliberately leaves out anything clinical
    (possible function, escalation/safety protocols) — those stay in the
    staff version. Content is the same words staff wrote, just trimmed to
    a few short lines per section rather than rewritten, so nothing
    appears here that a real person didn't actually say. The one
    exception is "Things I Find Really Challenging," which translates
    the auto-detected trigger categories into plain child-friendly words.

    Formatted along Easy Read principles (a widely-used accessible-document
    standard in the disability sector): one idea per line, a picture
    anchoring every idea, large plain text, and generous white space.
    Cards use a light background with a coloured border rather than solid
    colour blocks, for a gentler look. Uses emoji as the visual anchor
    since licensed symbol sets (Widgit, Makaton, Boardmaker) aren't
    something this tool has access to — staff can swap in real symbols
    afterward since it's an editable Word file."""
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    def _set_bg(cell, hex_color):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), hex_color)
        tcPr.append(shd)

    def _set_border(cell, hex_color, sz=28):
        # A visible coloured border on all four sides — the "gentler" look
        # (light background, colour on the frame) instead of a solid block.
        tcPr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement('w:tcBorders')
        for side in ('top', 'left', 'bottom', 'right'):
            b = OxmlElement(f'w:{side}')
            b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), str(sz))
            b.set(qn('w:space'), '4'); b.set(qn('w:color'), hex_color)
            borders.append(b)
        tcPr.append(borders)

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(1.8)

    # ── Title band — this one stays a solid colour, as the one "banner" moment ──
    tt = doc.add_table(rows=1, cols=1); tt.autofit = True
    tt_c = tt.rows[0].cells[0]
    _set_bg(tt_c, "1A7A6E")
    _no_border_tcPr = tt_c._tc.get_or_add_tcPr()
    _nb = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        b = OxmlElement(f'w:{side}'); b.set(qn('w:val'), 'nil'); _nb.append(b)
    _no_border_tcPr.append(_nb)
    tt_c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = tt_c.paragraphs[0].add_run("⭐ My Plan ⭐")
    r1.font.size = Pt(32); r1.font.bold = True; r1.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p_name = tt_c.add_paragraph(); p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p_name.add_run(student["name"])
    r2.font.size = Pt(20); r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    doc.add_paragraph("")

    # ── One bordered, light-background card per section ─────────────────
    _CARD_SYMBOLS = {"about": "me", "challenging": "difficult", "want": "choose",
                      "need": "help", "long": "time", "voice": "talk"}

    def _hex_to_rgb(hex_color):
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))

    def _card(hex_color, icon, heading, lines, italic=False, symbol_keyword=None):
        if not lines:
            return
        tbl = doc.add_table(rows=1, cols=1); tbl.autofit = True
        cell = tbl.rows[0].cells[0]
        _set_border(cell, hex_color)
        _rgb = _hex_to_rgb(hex_color)
        p_h = cell.paragraphs[0]
        if symbol_keyword:
            _sym_bytes = get_arasaac_symbol_bytes(symbol_keyword)
            if _sym_bytes:
                p_img = cell.paragraphs[0]
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(BytesIO(_sym_bytes), width=Cm(2.2))
                p_h = cell.add_paragraph()
        rh = p_h.add_run(f"{icon}  {heading}")
        rh.font.size = Pt(22); rh.font.bold = True; rh.font.color.rgb = _rgb
        p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_h.paragraph_format.space_after = Pt(6)
        for line in lines:
            p = cell.add_paragraph()
            _bullet_icon = "💬" if italic else "⭐"
            r = p.add_run(line if italic else f"{_bullet_icon}  {line}")
            r.font.size = Pt(17)
            r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            if italic:
                r.font.italic = True
            p.paragraph_format.space_after = Pt(8)
        doc.add_paragraph("")

    # 1. A little bit about me
    _about_me = _first_lines(plan.get("strengths"), 3) + _first_lines(plan.get("interests"), 2)
    _card("3B82F6", "🖐️", "A Little Bit About Me", _about_me, symbol_keyword=_CARD_SYMBOLS["about"])

    # 2. Things I find really challenging — auto, translated into plain words
    _challenges = []
    for cat in (triggers or [])[:2]:
        _plain = CHALLENGE_SIMPLE.get(cat)
        if _plain:
            _challenges.append(_plain)
    _challenges += _first_lines(plan.get("early_warning_signs"), 2)
    _card("EF4444", "⚡", "Things I Find Really Challenging", _challenges[:4], symbol_keyword=_CARD_SYMBOLS["challenging"])

    # 3. Things I want to do when things are challenging
    _want_to_do = _first_lines(plan.get("teaching_strategies"), 4)
    _card("22C55E", "🙋", "Things I Want To Do When Things Are Hard", _want_to_do, symbol_keyword=_CARD_SYMBOLS["want"])

    # 4. Things I need others to do
    _need_others = (
        _first_lines(plan.get("proactive_strategies_additional"), 2)
        + _first_lines(plan.get("adjustments_supports"), 2)
        + [s["strategy"] for s in (strategies or [])[:2]]
    )
    _card("8B5CF6", "🤝", "Things I Need Others To Do", _need_others[:4], symbol_keyword=_CARD_SYMBOLS["need"])

    # 5. How long I need
    _recovery = _first_lines(plan.get("recovery_time"), 2)
    _card("F59E0B", "⏳", "How Long I Need", _recovery, symbol_keyword=_CARD_SYMBOLS["long"])

    # 6. In my own words
    _card("EC4899", "💬", "In My Own Words", _first_lines(plan.get("student_voice"), 4), italic=True, symbol_keyword=_CARD_SYMBOLS["voice"])

    doc.add_paragraph("")
    p_note = doc.add_paragraph(
        f"This is a simple version of a bigger plan that {student['name']}'s teachers and support "
        "staff keep. Ask a trusted adult if you want to know more or talk about anything in it."
    )
    p_note.runs[0].font.size = Pt(11)
    p_note.runs[0].font.italic = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def render_quick_incident_log():
    """Standalone quick incident log — no login required."""
    import uuid as _uuid

    st.markdown(
        "<div style='background:#1A7A7A;border-radius:12px;padding:1rem 1.5rem;"
        "margin-bottom:1.25rem;'>"
        "<div style='color:white;font-size:1.5rem;font-weight:700;'>⚡ Quick Incident Log</div>"
        "<div style='color:#fef3c7;font-size:.88rem;margin-top:.2rem;'>"
        "Cowandilla Learning Centre — Learning & Behaviour Unit</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Log a regular (non-critical) incident quickly. "
        "All entries appear immediately in the student's analysis. "
        "For critical incidents requiring an ABCH form, use the full Behaviour Support Tool."
    )

    if not supabase:
        st.error("Database not connected — unable to save. Contact the portal administrator.")
        return

    # After a successful save, show a summary + explicit "log another?"
    # prompt instead of silently resetting straight back to a blank form.
    _ql_saved = st.session_state.get("ql_just_saved")
    if _ql_saved:
        st.markdown(
            f"<div style='background:#f0fdf4;border:2px solid #22c55e;border-radius:12px;"
            f"padding:1.1rem 1.5rem;margin-top:.5rem;'>"
            f"<div style='font-weight:700;color:#15803d;font-size:1rem;margin-bottom:.4rem;'>"
            f"✅ Incident logged successfully</div>"
            f"<div style='font-size:.85rem;color:#1e293b;line-height:1.7;'>"
            f"<b>Student:</b> {_ql_saved['student']}<br>"
            f"<b>Date/Time:</b> {_ql_saved['datetime']} — {_ql_saved['session']}<br>"
            f"<b>Location:</b> {_ql_saved['location']}<br>"
            f"<b>Behaviour:</b> {_ql_saved['behaviour']}<br>"
            f"<b>Antecedent:</b> {_ql_saved['antecedent']}<br>"
            f"<b>Severity:</b> <span style='background:{_ql_saved['sev_color']};color:white;"
            f"padding:.1rem .4rem;border-radius:4px;font-size:.82rem;'>"
            f"{_ql_saved['sev_label']}</span><br>"
            f"<b>Logged by:</b> {_ql_saved['logged_by']}"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        st.caption("Visible immediately in the student's analysis in the Behaviour Support Tool.")
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Log Another Incident", type="primary", use_container_width=True, key="ql_log_another"):
            st.session_state["ql_just_saved"] = None
            st.rerun()
        st.markdown("---")
        st.caption("CLC-LBU Portal · Quick Incident Log · For critical incidents use the full Behaviour Support Tool")
        return

    # Load students live
    try:
        _stu_resp = supabase.table("students").select("id,first_name,last_name,name,program") \
            .eq("archived", False).execute()
        _students = []
        for _r in _stu_resp.data:
            _nm = (
                f"{_r.get('first_name','')} {_r.get('last_name','')}".strip()
                if _r.get("first_name") else _r.get("name", "Unknown")
            )
            _students.append({"id": str(_r["id"]), "name": _nm, "program": _r.get("program","")})
        _students = sorted(_students, key=lambda s: s["name"])
    except Exception as _e:
        st.error(f"Could not load students: {_e}")
        return

    if not _students:
        st.warning("No students found in the database.")
        return

    # Load staff live (avoids free-text name matching, which can silently
    # fail to resolve an id and violate the NOT NULL constraint on
    # incidents.reported_by)
    try:
        _staff_resp = supabase.table("staff").select("id,name") \
            .order("name").execute()
        _staff_opts = {str(_r["id"]): _r["name"] for _r in _staff_resp.data}
    except Exception as _e:
        st.error(f"Could not load staff list: {_e}")
        return

    if not _staff_opts:
        st.warning("No staff found in the database.")
        return

    _SESSIONS_QL = {
        "Morning (before 11:00am)": "Morning",
        "Middle of day (11:00am – 1:30pm)": "Middle",
        "Afternoon (1:31pm – 2:45pm)": "Afternoon",
    }
    _SEV_LABELS_QL = {
        1: "1 — Low level, student coping",
        2: "2 — Escalating, still coping",
        3: "3 — Elevated, approaching edge of window",
        4: "4 — Outside window, significant dysregulation",
        5: "5 — Crisis, immediate safety concern",
    }
    _SEV_COLS_QL = {1:"#22c55e", 2:"#eab308", 3:"#f97316", 4:"#ef4444", 5:"#7f1d1d"}

    try:
        _ql_form = st.form("ql_form", clear_on_submit=True, enter_to_submit=False)
    except TypeError:
        # Older Streamlit without the enter_to_submit param — falls back to
        # default behaviour rather than crashing the page.
        _ql_form = st.form("ql_form", clear_on_submit=True)
    with _ql_form:
        _ql_c1, _ql_c2 = st.columns([3, 2])
        with _ql_c1:
            _stu_opts = {s["id"]: f"{s['name']}  ({s['program']})" for s in _students}
            _sel_id = st.selectbox("👤 Student *", list(_stu_opts.keys()),
                                   format_func=lambda x: _stu_opts[x])
        with _ql_c2:
            _rep_by_id = st.selectbox("🙋 Your name *", list(_staff_opts.keys()),
                                       format_func=lambda x: _staff_opts[x])

        st.markdown("<hr style='margin:.5rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

        _dc1, _dc2, _dc3 = st.columns(3)
        with _dc1:
            _inc_date = st.date_input("📅 Date *", value=date.today())
        with _dc2:
            _inc_time = st.time_input("🕐 Time *",
                value=datetime.now().replace(second=0, microsecond=0).time())
        with _dc3:
            _sess_lbl = st.selectbox("⏰ Session *", list(_SESSIONS_QL.keys()))

        _location = st.selectbox("📍 Location *", LOCATIONS)

        st.markdown("<hr style='margin:.5rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

        st.markdown("**⚡ What happened just before? (Trigger / Antecedent)**")
        _antecedent = st.selectbox("Antecedent", ANTECEDENTS, label_visibility="collapsed")

        st.markdown("**🎯 Behaviour observed**")
        _behaviour = st.selectbox("Behaviour", BEHAVIOUR_TYPES, label_visibility="collapsed")

        st.markdown("<hr style='margin:.5rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

        st.markdown("**📊 Severity**")
        _sev_c1, _sev_c2 = st.columns([2, 3])
        with _sev_c1:
            _severity = st.select_slider("Severity", options=[1,2,3,4,5],
                                          value=2, label_visibility="collapsed")
        with _sev_c2:
            _sc = _SEV_COLS_QL[_severity]
            st.markdown(
                f"<div style='background:{_sc}20;border-left:4px solid {_sc};"
                f"border-radius:6px;padding:.35rem .7rem;font-size:.84rem;color:#1e293b;"
                f"margin-top:.1rem;'><b>{_SEV_LABELS_QL[_severity]}</b></div>",
                unsafe_allow_html=True
            )
        st.caption("🟡 1–2 = Coping zone  ·  🟠 3 = Approaching edge  ·  🔴 4–5 = Outside window")

        st.markdown("<hr style='margin:.5rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

        st.markdown("**🤝 Staff response / intervention**")
        _interventions = st.multiselect("Interventions", INTERVENTIONS,
                                         label_visibility="collapsed")

        _opt1, _opt2 = st.columns([1, 2])
        with _opt1:
            _duration = st.number_input("⏱️ Duration (min)", min_value=0, max_value=120,
                                         value=0, step=1, help="Leave 0 if unknown")
        with _opt2:
            _desc = st.text_area("📝 Brief notes (optional)", height=75,
                                  placeholder="Any additional context not captured above...")

        _submitted = st.form_submit_button("✅ Log Incident", type="primary",
                                            use_container_width=True)

    if _submitted:
        _errs = []
        if not _rep_by_id:
            _errs.append("Please select your name.")
        if _antecedent.startswith("---"):
            _errs.append("Please select an antecedent (not a section header).")
        if _behaviour.startswith("---"):
            _errs.append("Please select a behaviour (not a section header).")
        if not _interventions:
            _errs.append("Please select at least one staff response.")
        if _errs:
            for _e in _errs:
                st.error(_e)
        else:
            try:
                _staff_id = _rep_by_id

                _data = {
                    "id":               str(_uuid.uuid4()),
                    "student_id":       _sel_id,
                    "date":             _inc_date.isoformat(),
                    "time":             _inc_time.strftime("%H:%M:%S"),
                    "day_of_week":      _inc_date.strftime("%A"),
                    "session":          _SESSIONS_QL[_sess_lbl],
                    "location":         _location,
                    "behaviour_type":   _behaviour,
                    "antecedent":       _antecedent,
                    "intervention":     _interventions,
                    "severity":         _severity,
                    "reported_by":      _staff_id,
                    "description":      _desc.strip(),
                    "duration_minutes": _duration if _duration > 0 else None,
                    "hypothesis_function": None,
                    "hypothesis_item":  None,
                    "is_critical":      False,
                }
                supabase.table("incidents").insert(_data).execute()
                _stu_name = _stu_opts[_sel_id].split("  (")[0]
                _sc2 = _SEV_COLS_QL[_severity]
                st.session_state["ql_just_saved"] = {
                    "student": _stu_name,
                    "datetime": f"{_inc_date.strftime('%-d %b %Y')} at {_inc_time.strftime('%H:%M')}",
                    "session": _SESSIONS_QL[_sess_lbl],
                    "location": _location,
                    "behaviour": _behaviour,
                    "antecedent": _antecedent,
                    "sev_color": _sc2,
                    "sev_label": _SEV_LABELS_QL[_severity],
                    "logged_by": _staff_opts[_rep_by_id],
                }
                st.rerun()
            except Exception as _e:
                st.error(f"❌ Save failed: {_e}")

    st.markdown("---")
    st.caption("CLC-LBU Portal · Quick Incident Log · For critical incidents use the full Behaviour Support Tool")


def _inject_modern_css():
    """One shared, modern visual layer for the whole Behaviour Support
    tool — rounded cards, soft shadows, smoother buttons/expanders/tabs,
    tighter typography. Pure CSS targeting Streamlit's own component
    selectors, so if a selector doesn't match on a given Streamlit
    version it simply has no effect — it can't break functionality the
    way a Python API mismatch would."""
    st.markdown("""
    <style>
    /* Typography */
    h1, h2, h3, h4 {
        letter-spacing: -0.01em;
        font-weight: 700 !important;
    }
    p, li, .stMarkdown { line-height: 1.55; }

    /* Buttons */
    div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
        border-radius: 10px !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        transition: transform 0.08s ease, box-shadow 0.15s ease !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    }

    /* Bordered containers (BSEM recommendation cards, etc.) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: box-shadow 0.15s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        border-radius: 10px !important;
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        border: 1px solid #e2e8f0;
    }
    div[data-testid="stMetricValue"] {
        font-weight: 700 !important;
    }

    /* Tabs */
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 600 !important;
    }

    /* Dataframes / tables */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }

    /* Text inputs / text areas / selects */
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-baseweb="select"] > div {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    _inject_modern_css()
    # ── Quick Incident Log — no login required ────────────────────────────
    # Accessible at ?mode=quicklog (tile URL: /Behaviour_Support?mode=quicklog)
    try:
        _ql_mode = st.query_params.get("mode", "")
    except Exception:
        try:
            _ql_mode = st.experimental_get_query_params().get("mode", [""])[0]
        except Exception:
            _ql_mode = ""
    if _ql_mode == "quicklog":
        render_quick_incident_log()
        return

    init_state()
    if not st.session_state.logged_in:
        restore_login_from_url()
    page = st.session_state.current_page
    if not st.session_state.logged_in:
        render_login_page()
        return
    persist_login_to_url()
    if page == "landing":                  render_landing_page()
    elif page == "program_students":        render_program_students_page()
    elif page == "incident_log":            render_incident_log_page()
    elif page == "critical_incident":       render_critical_incident_page()
    elif page == "review_critical":         render_review_critical_page()
    elif page == "leader_approve_critical": render_leader_approve_critical_page()
    elif page == "student_analysis":        render_student_analysis_page()
    elif page == "student_dashboard":       render_student_dashboard()
    elif page == "support_plan":             render_support_plan_page()
    elif page == "admin_portal":            render_admin_portal()
    else:                                   render_landing_page()


if __name__ == "__main__":
    main()
