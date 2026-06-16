from theme import apply_clc_theme
from auth import require_auth, logout_button, get_staff_name
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
import json
import os

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="CLC PDP Builder", page_icon="🎯", layout="wide",
                   initial_sidebar_state="collapsed")
apply_clc_theme()
require_auth("PDP Builder", "🎯")
logout_button("sidebar")

TEAL = "#1A7A7A"
AMBER = "#C8760A"
PORTAL_URL = "https://16cefb77.clc-portal.pages.dev/"

# Back to portal link
st.sidebar.markdown(
    f'<a href="{PORTAL_URL}" target="_self" style="display:block;text-align:center;'
    f'background:{TEAL};color:white;font-weight:600;font-size:0.85rem;'
    f'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    f'🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Admin gate (matches auth.py is_portal_admin pattern) ──────────────────────
def require_portal_admin(message="The PDP Builder is in the leadership area."):
    try:
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "")
    except Exception:
        admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if st.session_state.get("is_portal_admin"):
        return True
    st.warning(f"🔒 {message}")
    entered = st.text_input("Admin password", type="password", key="pdp_admin_pw")
    if st.button("Unlock", type="primary", key="pdp_admin_btn"):
        if entered and entered == admin_pw:
            st.session_state.is_portal_admin = True
            st.rerun()
        else:
            st.error("Incorrect admin password.")
    st.stop()
    return False

require_portal_admin()

# ── Supabase ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_client()

# ── Groq ──────────────────────────────────────────────────────────────────────
try:
    GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

DEFAULT_PRINCIPLES = (
    "Collective responsibility\nLearning system\nEvaluate for impact\n"
    "Tight and flexible\nTrust and verify\nImprovement and responsibility"
)
AREAS_OF_IMPACT = "Wellbeing, Equity and excellence, Learner agency, Effective learners"

# ── Field definitions ─────────────────────────────────────────────────────────
# (widget_key, default) — all start blank, seeded into session_state once
FIELD_KEYS = [
    "w_emp", "w_ldr", "w_date",
    "w_goal1_goal", "w_goal1_strengths", "w_goal1_learn", "w_goal1_support",
    "w_goal1_monitor", "w_goal1_evaluate", "w_goal1_r6", "w_goal1_r12",
    "w_goal2_goal", "w_goal2_strengths", "w_goal2_learn", "w_goal2_support",
    "w_goal2_monitor", "w_goal2_evaluate", "w_goal2_r6", "w_goal2_r12",
    "w_career_goal", "w_career_actions", "w_career_r6", "w_career_r12",
    "w_wb_goal", "w_wb_actions", "w_wb_r6", "w_wb_r12",
    "w_cultural_commitment",
    "w_ref_emp6", "w_ref_ldr6", "w_ref_emp12", "w_ref_ldr12",
]

def seed_state():
    for k in FIELD_KEYS:
        if k not in st.session_state:
            st.session_state[k] = ""
    if "w_cultural_focus" not in st.session_state:
        st.session_state["w_cultural_focus"] = "Knowing"
    if "w_emp" in st.session_state and not st.session_state["w_emp"]:
        st.session_state["w_emp"] = get_staff_name() or ""
    if "w_date" in st.session_state and not st.session_state["w_date"]:
        st.session_state["w_date"] = date.today().strftime("%d/%m/%Y")
    if "transcript" not in st.session_state:
        st.session_state["transcript"] = ""
    if "principles" not in st.session_state:
        st.session_state["principles"] = DEFAULT_PRINCIPLES

seed_state()

# ── AI alignment ──────────────────────────────────────────────────────────────
def align_transcript(transcript: str, principles: str) -> dict:
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    system = (
        "You are helping a South Australian Department for Education staff member draft a "
        "Performance and Development Plan (PDP) from a transcript of a development conversation. "
        "Use only what is grounded in the transcript — never invent achievements, goals or quotes. "
        "Where a section is not covered, return a short honest prompt for the person to complete it "
        "(e.g. 'Not discussed — consider what success looks like here'). "
        "Write in Australian English, first person, in a warm, practical, coaching-aligned voice. "
        "Frame goals to be specific and measurable with a timeframe (SMARTAR-friendly) where the transcript supports it. "
        f"Where natural, connect goals to the 4 areas of impact ({AREAS_OF_IMPACT}) and these guiding principles: {principles}. "
        "Keep each field concise — roughly 1 to 4 sentences. "
        "Return ONLY a JSON object, no preamble, no markdown fences, with exactly this shape: "
        '{"employee_name":"","leader_name":"",'
        '"goal1":{"goal":"","strengths":"","learn_change":"","support":"","monitor":"","evaluate":""},'
        '"goal2":{"goal":"","strengths":"","learn_change":"","support":"","monitor":"","evaluate":""},'
        '"career":{"goal":"","actions":""},'
        '"wellbeing":{"goal":"","actions":""},'
        '"cultural":{"focus":"Knowing|Doing|Being","commitment":""}}'
    )
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=4000,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",
             "content": "Here is the development conversation transcript:\n\n" + transcript},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1])

def apply_alignment(parsed: dict):
    if parsed.get("employee_name") and not st.session_state["w_emp"]:
        st.session_state["w_emp"] = parsed["employee_name"]
    if parsed.get("leader_name") and not st.session_state["w_ldr"]:
        st.session_state["w_ldr"] = parsed["leader_name"]
    m = {
        "goal1": {"goal": "w_goal1_goal", "strengths": "w_goal1_strengths", "learn_change": "w_goal1_learn",
                  "support": "w_goal1_support", "monitor": "w_goal1_monitor", "evaluate": "w_goal1_evaluate"},
        "goal2": {"goal": "w_goal2_goal", "strengths": "w_goal2_strengths", "learn_change": "w_goal2_learn",
                  "support": "w_goal2_support", "monitor": "w_goal2_monitor", "evaluate": "w_goal2_evaluate"},
        "career": {"goal": "w_career_goal", "actions": "w_career_actions"},
        "wellbeing": {"goal": "w_wb_goal", "actions": "w_wb_actions"},
    }
    for sect, mapping in m.items():
        obj = parsed.get(sect, {}) or {}
        for src, key in mapping.items():
            if obj.get(src):
                st.session_state[key] = obj[src]
    cult = parsed.get("cultural", {}) or {}
    if cult.get("focus") in ("Knowing", "Doing", "Being"):
        st.session_state["w_cultural_focus"] = cult["focus"]
    if cult.get("commitment"):
        st.session_state["w_cultural_commitment"] = cult["commitment"]

# ── Supabase save / load ──────────────────────────────────────────────────────
def collect_plan() -> dict:
    return {k: st.session_state.get(k, "") for k in FIELD_KEYS + ["w_cultural_focus"]}

def save_plan():
    payload = {
        "staff_name": get_staff_name() or "",
        "employee_name": st.session_state.get("w_emp", ""),
        "leader_name": st.session_state.get("w_ldr", ""),
        "plan_date": st.session_state.get("w_date", ""),
        "data": collect_plan(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    supabase.table("pdp_plans").insert(payload).execute()

def load_my_plans() -> list:
    name = get_staff_name() or ""
    res = (supabase.table("pdp_plans")
           .select("id, employee_name, plan_date, updated_at")
           .eq("staff_name", name)
           .order("updated_at", desc=True).execute())
    return res.data or []

def load_plan(plan_id: str):
    res = supabase.table("pdp_plans").select("data").eq("id", plan_id).single().execute()
    data = (res.data or {}).get("data", {}) or {}
    for k, v in data.items():
        st.session_state[k] = v

def delete_plan(plan_id: str):
    supabase.table("pdp_plans").delete().eq("id", plan_id).execute()

def plan_to_markdown() -> str:
    g = st.session_state.get
    md = []
    md.append(f"# Performance and Development Plan\n")
    md.append(f"**Employee:** {g('w_emp','')}  ")
    md.append(f"**Leader:** {g('w_ldr','')}  ")
    md.append(f"**Date:** {g('w_date','')}\n")
    for n in ("1", "2"):
        md.append(f"\n## Goal {n}\n")
        md.append(f"**Goal & purpose:** {g(f'w_goal{n}_goal','')}\n")
        md.append(f"- **Strengths to leverage:** {g(f'w_goal{n}_strengths','')}")
        md.append(f"- **Learn / change:** {g(f'w_goal{n}_learn','')}")
        md.append(f"- **Support needed:** {g(f'w_goal{n}_support','')}")
        md.append(f"- **Monitor change:** {g(f'w_goal{n}_monitor','')}")
        md.append(f"- **Evaluate impact:** {g(f'w_goal{n}_evaluate','')}")
        md.append(f"\n*6 months:* {g(f'w_goal{n}_r6','')}")
        md.append(f"\n*12 months:* {g(f'w_goal{n}_r12','')}")
    md.append(f"\n## Career fulfilment\n{g('w_career_goal','')}\n")
    md.append(f"**Actions:** {g('w_career_actions','')}")
    md.append(f"\n*6 months:* {g('w_career_r6','')}  *12 months:* {g('w_career_r12','')}")
    md.append(f"\n## My wellbeing\n{g('w_wb_goal','')}\n")
    md.append(f"**Actions:** {g('w_wb_actions','')}")
    md.append(f"\n*6 months:* {g('w_wb_r6','')}  *12 months:* {g('w_wb_r12','')}")
    md.append(f"\n## Cultural responsiveness journey\n")
    md.append(f"**Focus:** {g('w_cultural_focus','')}\n\n{g('w_cultural_commitment','')}")
    md.append(f"\n## Reflection overview\n")
    md.append(f"**Employee — 6 months:** {g('w_ref_emp6','')}")
    md.append(f"**Leader — 6 months:** {g('w_ref_ldr6','')}")
    md.append(f"**Employee — 12 months:** {g('w_ref_emp12','')}")
    md.append(f"**Leader — 12 months:** {g('w_ref_ldr12','')}")
    return "\n".join(md)

SAMPLE = (
    "Leader: Thanks for making time. Let's start with what's been going well this term.\n"
    "Staff: The interval support tracking has helped me see patterns earlier. I've gotten better at "
    "noticing when a student is moving out of their window of tolerance and stepping in before things escalate.\n"
    "Leader: That's a real strength. Where do you want to grow?\n"
    "Staff: I'd like to build confidence leading restorative conversations after incidents. I tend to hand "
    "those to others. I'd like to be running structured restorative debriefs with students myself by the end "
    "of term 3, and supporting one colleague to do the same.\n"
    "Leader: What would help?\n"
    "Staff: Coaching from you, observing a couple of debriefs, and time carved out in the week. I'd know it's "
    "working if incident re-escalation drops and students re-engage faster afterwards.\n"
    "Leader: And wellbeing?\n"
    "Staff: The back-to-back days wear me down. I'm at my best when I get a proper reset at lunch and I've "
    "prepped the morning before. I want to protect that more deliberately.\n"
    "Leader: Career-wise?\n"
    "Staff: Longer term I'm interested in a coordinator role — leading practice across the centre, not just my "
    "own room. I'd like to start shadowing some of the operational side.\n"
    "Leader: Cultural responsiveness?\n"
    "Staff: I want to deepen how I respond to our Aboriginal students specifically — not just knowledge, but "
    "the doing. Embedding more responsive practice into how I plan and run sessions."
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,{TEAL},#0f5f5f);color:white;border-radius:12px;
            padding:1.25rem 1.5rem;margin-bottom:1rem;">
  <div style="font-size:1.5rem;font-weight:800;">🎯 PDP Builder</div>
  <div style="opacity:0.85;font-size:0.9rem;margin-top:0.2rem;">
    Draft your Performance and Development Plan from a development conversation —
    aligned to each element, every field editable.</div>
</div>
""", unsafe_allow_html=True)

st.info(
    "This drafts **your own** PDP from a conversation you were part of. It's a personal reflection aid — "
    "not a way to write or assess someone else's plan, which is a separate, consent-based process.",
    icon="💬",
)

# ── Identity ──────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 1])
c1.text_input("Employee name", key="w_emp")
c2.text_input("Leader name", key="w_ldr")
c3.text_input("Date", key="w_date")

# ── Engine ────────────────────────────────────────────────────────────────────
st.markdown("### Align from a conversation")
st.caption("Paste a transcript or notes from a development conversation. The builder drafts each section in "
           "your words and flags anything not covered.")

st.text_area("Transcript or notes", key="transcript", height=180,
             placeholder="Paste your development conversation transcript or notes here…")

bc1, bc2, bc3 = st.columns([1, 1, 3])
align_clicked = bc1.button("✨ Align to PDP", type="primary", use_container_width=True)
if bc2.button("Load sample", use_container_width=True):
    st.session_state["transcript"] = SAMPLE
    st.rerun()

if align_clicked:
    if not st.session_state["transcript"].strip():
        st.warning("Paste a transcript first, then align.")
    elif not GROQ_KEY:
        st.error("No Groq API key found in secrets — add GROQ_API_KEY to enable alignment. "
                 "You can still complete the plan manually.")
    else:
        with st.spinner("Reading the conversation and drafting each section…"):
            try:
                parsed = align_transcript(st.session_state["transcript"], st.session_state["principles"])
                apply_alignment(parsed)
                st.success("Drafted. Review and edit every field — it's your plan.")
                st.rerun()
            except Exception as ex:
                st.error(f"Couldn't draft from that transcript: {ex}. Try again or shorten it.")

with st.expander("Strategy hooks (used by the alignment)"):
    st.markdown(f"**4 areas of impact:** {AREAS_OF_IMPACT}")
    st.text_area("Guiding principles — confirm wording against EDi", key="principles", height=120)

st.divider()

# ── GOALS ─────────────────────────────────────────────────────────────────────
def goal_block(n: str):
    st.subheader(f"Goal {n}")
    st.text_area("Goal & purpose — what I'll deliver, by when and how",
                 key=f"w_goal{n}_goal", height=90)
    with st.expander("Coaching scaffold"):
        st.text_area("My strengths to leverage", key=f"w_goal{n}_strengths", height=70)
        st.text_area("What I need to learn / change", key=f"w_goal{n}_learn", height=70)
        st.text_area("Support I need (people, processes, resources, tools)",
                     key=f"w_goal{n}_support", height=70)
        st.text_area("How I'll monitor change (feedback I'll seek)",
                     key=f"w_goal{n}_monitor", height=70)
        st.text_area("How I'll evaluate impact (how I'll know it worked)",
                     key=f"w_goal{n}_evaluate", height=70)
    rc1, rc2 = st.columns(2)
    rc1.text_area("At 6 months", key=f"w_goal{n}_r6", height=90)
    rc2.text_area("At 12 months", key=f"w_goal{n}_r12", height=90)

st.markdown("## 🎯 Goals")
st.caption("Achievable within 6–12 months · tied to practice, standards or site priorities")
goal_block("1")
st.markdown("---")
goal_block("2")

# ── CAREER FULFILMENT ─────────────────────────────────────────────────────────
st.markdown("## 🏅 Career fulfilment")
st.caption("An area of focus or future aspiration · may take up to 2 years")
st.text_area("My career fulfilment goal", key="w_career_goal", height=90)
st.text_area("Actions — what I'll do, by when and how", key="w_career_actions", height=70)
cc1, cc2 = st.columns(2)
cc1.text_area("At 6 months", key="w_career_r6", height=80)
cc2.text_area("At 12 months", key="w_career_r12", height=80)

# ── WELLBEING ─────────────────────────────────────────────────────────────────
st.markdown("## 🌱 My wellbeing")
st.caption("What helps me learn and thrive at work")
st.text_area("My wellbeing goal", key="w_wb_goal", height=90)
st.text_area("Actions", key="w_wb_actions", height=70)
wc1, wc2 = st.columns(2)
wc1.text_area("At 6 months", key="w_wb_r6", height=80)
wc2.text_area("At 12 months", key="w_wb_r12", height=80)

# ── CULTURAL RESPONSIVENESS ───────────────────────────────────────────────────
st.markdown("## 🧭 My cultural responsiveness journey")
st.caption("Choose one way to build your commitment over 12 months")
st.radio("Focus", ["Knowing", "Doing", "Being"], key="w_cultural_focus", horizontal=True,
         help="Knowing: broaden knowledge of histories, cultures and languages. "
              "Doing: respond to diverse needs and knowledge. "
              "Being: strengthen self-awareness of cultural and linguistic needs.")
st.text_area("My commitment — what I'll learn or do over the next 12 months",
             key="w_cultural_commitment", height=90)

# ── REFLECTION OVERVIEW ───────────────────────────────────────────────────────
st.markdown("## 📝 Reflection overview")
st.caption("Completed together at the 6 and 12 month review")
r1, r2 = st.columns(2)
r1.text_area("Employee summary — 6 months", key="w_ref_emp6", height=90)
r2.text_area("Leader summary — 6 months", key="w_ref_ldr6", height=90)
r3, r4 = st.columns(2)
r3.text_area("Employee summary — 12 months", key="w_ref_emp12", height=90)
r4.text_area("Leader summary — 12 months", key="w_ref_ldr12", height=90)

st.divider()

# ── Save / load / export ──────────────────────────────────────────────────────
st.markdown("### Save & export")
sc1, sc2, sc3 = st.columns([1, 2, 1])

if sc1.button("💾 Save to my plans", type="primary", use_container_width=True):
    try:
        save_plan()
        st.success("Saved.")
    except Exception as ex:
        st.error(f"Save failed: {ex}")

try:
    plans = load_my_plans()
except Exception:
    plans = []

if plans:
    opts = {f"{p.get('employee_name','(no name)')} · {p.get('plan_date','')} "
            f"· saved {str(p.get('updated_at',''))[:16]}": p["id"] for p in plans}
    chosen = sc2.selectbox("My saved plans", list(opts.keys()), index=None,
                           placeholder="Choose a saved plan…")
    lc1, lc2 = sc2.columns(2)
    if lc1.button("Load", use_container_width=True, disabled=chosen is None):
        load_plan(opts[chosen]); st.rerun()
    if lc2.button("Delete", use_container_width=True, disabled=chosen is None):
        delete_plan(opts[chosen]); st.rerun()
else:
    sc2.caption("No saved plans yet.")

sc3.download_button("⬇️ Download (.md)", data=plan_to_markdown(),
                    file_name="pdp.md", mime="text/markdown", use_container_width=True)

st.caption("Plans are stored privately against your staff name. Nothing is shared until you choose to print "
           "or send it.")
