"""
18_Minutes_Polish.py
CLC LBU — Meeting Minutes Polisher
Drop in a rough transcript or draft — AI produces professional meeting minutes.
"""

import streamlit as st
import json
from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Minutes Polisher | CLC LBU",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import require_auth, logout_button
require_auth("Minutes Polisher", "📝")
logout_button("sidebar")

# ── DESIGN ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"]{background:#f0f4f0!important;font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{display:none}[data-testid="stSidebar"]{display:none}
#MainMenu,footer,.stDeployButton{display:none}
.main .block-container{padding:0!important;max-width:100%!important}
.top-nav{background:#1a2e44;padding:0 2rem;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000;box-shadow:0 2px 12px rgba(0,0,0,0.2)}
.content-area{padding:1.5rem 2rem 4rem;max-width:1200px;margin:0 auto}
.hero{background:linear-gradient(135deg,#1a2e44 0%,#4a7fb5 100%);padding:1.5rem 2rem;border-radius:14px;margin-bottom:1.5rem;color:white}
.hero-title{font-size:1.4rem;font-weight:700;margin-bottom:.2rem}
.hero-sub{font-size:.85rem;opacity:.8}
.step-bar{display:flex;gap:0;margin-bottom:1.5rem;border-radius:10px;overflow:hidden;border:1.5px solid #d8e8d4}
.step-item{flex:1;padding:.55rem .5rem;text-align:center;font-size:.72rem;font-weight:600;color:#7a9a7a;background:white;transition:.15s}
.step-item.active{background:#1a2e44;color:white}
.step-item.done{background:#e8f5e1;color:#2d6b1a}
.card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);overflow:hidden;margin-bottom:1.25rem}
.card-header{padding:.65rem 1rem}
.card-header.navy{background:#1a2e44}
.card-header.blue{background:#4a7fb5}
.card-header.amber{background:#e8a125}
.card-header.green{background:#4a8f33}
.card-header.slate{background:#6a7f8a}
.card-header.teal{background:#1a7a6e}
.card-header h3{font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.1em;margin:0}
.card-header.amber h3{color:#1a2e44}
.card-body{padding:1rem 1.25rem}
.info-box{background:#dbeafe;border-left:3px solid #4a7fb5;border-radius:0 8px 8px 0;padding:.75rem 1rem;font-size:.82rem;color:#1a2e44;margin-bottom:1rem}
.minutes-preview{background:white;border:1.5px solid #d8e8d4;border-radius:10px;padding:1.5rem 2rem;font-family:'DM Sans',sans-serif;line-height:1.8;font-size:.88rem;color:#2a3a2a}
.minutes-preview h2{font-size:1rem;font-weight:700;color:#1a2e44;border-bottom:2px solid #6BBF4E;padding-bottom:.3rem;margin:1.2rem 0 .5rem}
.minutes-preview h3{font-size:.9rem;font-weight:700;color:#4a7fb5;margin:.8rem 0 .3rem}
.minutes-preview .action-row{background:#fff8e6;border-left:3px solid #e8a125;padding:.3rem .7rem;border-radius:0 6px 6px 0;margin:.2rem 0;font-size:.82rem}
.minutes-preview .apology-row{color:#7a907a;font-style:italic;font-size:.82rem}
.section-label{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#4a7fb5;margin:1rem 0 .3rem}
.stTextInput input,.stTextArea textarea{border:1.5px solid #d8e8d4!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:#4a7fb5!important;box-shadow:0 0 0 3px rgba(74,127,181,0.12)!important}
.stButton button{border-radius:8px!important;font-weight:600!important;font-size:.85rem!important}
.stButton button[kind="primary"]{background:#1a2e44!important;border:none!important}
.stButton button[kind="primary"]:hover{background:#2d4f72!important}
label[data-testid="stWidgetLabel"] p{font-size:.72rem!important;font-weight:600!important;color:#4a6a8a!important;text-transform:uppercase!important;letter-spacing:.06em!important}
[data-baseweb="tab-list"]{background:transparent!important;gap:.25rem!important;border-bottom:2px solid #e0e8dc!important;padding:0!important}
[data-baseweb="tab"]{background:transparent!important;border-radius:8px 8px 0 0!important;padding:.5rem 1rem!important;font-size:.82rem!important;font-weight:600!important;color:#7a907a!important;border:none!important}
[aria-selected="true"][data-baseweb="tab"]{background:white!important;color:#1a2e44!important;border-bottom:2px solid #1a2e44!important}
</style>
""", unsafe_allow_html=True)

# ── GROQ ──────────────────────────────────────────────────────
def groq_call(prompt: str, max_tokens: int = 3000, system: str = "") -> str:
    try:
        from groq import Groq
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            messages=messages
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[AI error: {e}]"

# ── FILE TEXT EXTRACTION ──────────────────────────────────────
def extract_text(uploaded_file) -> str:
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".docx"):
            from docx import Document
            doc = Document(uploaded_file)
            parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        if cell.text.strip(): parts.append(cell.text.strip())
            return "\n".join(parts)
        elif name.endswith(".pdf"):
            import fitz
            data = uploaded_file.read()
            pdf = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in pdf)
        elif name.endswith(".txt"):
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.warning(f"Could not read {uploaded_file.name}: {e}")
    return ""

# ── SESSION STATE ─────────────────────────────────────────────
def init():
    defaults = {
        "mp_step": 1,
        "mp_meeting": {
            "type": "Staff Meeting",
            "date": str(date.today()),
            "start_time": "",
            "end_time": "",
            "location": "",
            "chair": "",
            "minutes_by": "",
            "present": "",
            "apologies": "",
            "organisation": "Cowandilla Learning Centre — LBU",
        },
        "mp_raw_text": "",
        "mp_style": "formal",
        "mp_sections": [],   # [{heading, content, is_action_table}]
        "mp_actions": [],    # [{who, action, due}]
        "mp_next_meeting": "",
        "mp_docx_bytes": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()
m  = st.session_state.mp_meeting

MEETING_TYPES = [
    "Staff Meeting",
    "Team Meeting — JP",
    "Team Meeting — PY",
    "Team Meeting — SY",
    "TAC Meeting",
    "PAC Meeting",
    "Committee Meeting",
    "Leadership Meeting",
    "Professional Development",
    "Other",
]

# ── TOP NAV ───────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
  <div style="display:flex;align-items:center;gap:.75rem;">
    <div style="width:32px;height:32px;background:linear-gradient(135deg,#1a2e44,#4a7fb5);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:.85rem;">📝</div>
    <div>
      <div style="font-weight:700;font-size:.95rem;color:white;">Minutes Polisher</div>
      <div style="font-size:.72rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.06em;">CLC LBU — Meeting Minutes</div>
    </div>
  </div>
  <div style="font-size:.75rem;color:rgba(255,255,255,.5);">📋 Cowandilla Learning Centre</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="content-area">', unsafe_allow_html=True)

# ── STEP BAR ─────────────────────────────────────────────────
STEPS = ["1 · Meeting Details", "2 · Input", "3 · Polish", "4 · Review & Edit", "5 · Download"]
bar = '<div class="step-bar">'
for i, label in enumerate(STEPS, 1):
    cls = "active" if i == st.session_state.mp_step else ("done" if i < st.session_state.mp_step else "")
    bar += f'<div class="step-item {cls}">{label}</div>'
bar += "</div>"
st.markdown(bar, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 1 — MEETING DETAILS
# ══════════════════════════════════════════════════════════════
if st.session_state.mp_step == 1:
    st.markdown("""
    <div class="hero">
      <div class="hero-title">📝 Meeting Minutes Polisher</div>
      <div class="hero-sub">Drop in a rough transcript, voice memo text, or draft notes — the AI produces polished, professional meeting minutes ready to share.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-header navy"><h3>📋 Meeting Details</h3></div><div class="card-body">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        m["type"] = st.selectbox("Meeting type", MEETING_TYPES,
            index=MEETING_TYPES.index(m["type"]) if m["type"] in MEETING_TYPES else 0)
        m["date"] = st.text_input("Date", value=m["date"], placeholder="e.g. Monday 23 March 2026")
        m["organisation"] = st.text_input("Organisation / team", value=m["organisation"])
    with c2:
        m["start_time"]  = st.text_input("Start time", value=m["start_time"], placeholder="e.g. 3:30 PM")
        m["end_time"]    = st.text_input("End time", value=m["end_time"],   placeholder="e.g. 4:45 PM")
        m["location"]    = st.text_input("Location / platform", value=m["location"], placeholder="e.g. Staff room / Teams")
    with c3:
        m["chair"]       = st.text_input("Chaired by", value=m["chair"], placeholder="e.g. Annette")
        m["minutes_by"]  = st.text_input("Minutes recorded by", value=m["minutes_by"], placeholder="e.g. Sarah")
        m["next_meeting"] = st.text_input("Next meeting date / time (optional)", value=m.get("next_meeting",""), placeholder="e.g. Monday 7 April 2026, 3:30 PM")

    st.markdown("---", unsafe_allow_html=True)
    ac1, ac2 = st.columns(2)
    with ac1:
        m["present"]   = st.text_area("Present (one per line)", value=m["present"], height=120,
            placeholder="e.g.\nAnnette Smith (Principal)\nSarah Jones (JP Teacher)\nMike Brown (SSO)")
    with ac2:
        m["apologies"] = st.text_area("Apologies (one per line)", value=m["apologies"], height=120,
            placeholder="e.g.\nTom Wilson (SSO)\nRachel Green (PY Teacher)")

    st.markdown('</div></div>', unsafe_allow_html=True)

    # Style selector
    st.markdown('<div class="card"><div class="card-header blue"><h3>✨ Output Style</h3></div><div class="card-body">', unsafe_allow_html=True)
    s1c, s2c, s3c = st.columns(3)
    with s1c:
        sel = st.session_state.mp_style == "formal"
        st.markdown(f'<div style="border:2px solid {"#1a2e44" if sel else "#e0e8dc"};border-radius:10px;padding:.85rem;background:{"#eef2f7" if sel else "white"};">'
            f'<div style="font-weight:700;font-size:.9rem;color:#1a2e44;margin-bottom:.25rem;">📄 Formal</div>'
            f'<div style="font-size:.78rem;color:#7a907a;">Full sentences, professional tone. Suitable for official records, PAC, TAC, governance.</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("Select Formal", type="primary" if sel else "secondary", use_container_width=True, key="sel_formal"):
            st.session_state.mp_style = "formal"; st.rerun()
    with s2c:
        sel = st.session_state.mp_style == "concise"
        st.markdown(f'<div style="border:2px solid {"#1a2e44" if sel else "#e0e8dc"};border-radius:10px;padding:.85rem;background:{"#eef2f7" if sel else "white"};">'
            f'<div style="font-weight:700;font-size:.9rem;color:#1a2e44;margin-bottom:.25rem;">⚡ Concise</div>'
            f'<div style="font-size:.78rem;color:#7a907a;">Dot points and brief summaries. Fast to read. Great for team meetings and weekly staff catch-ups.</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("Select Concise", type="primary" if sel else "secondary", use_container_width=True, key="sel_concise"):
            st.session_state.mp_style = "concise"; st.rerun()
    with s3c:
        sel = st.session_state.mp_style == "narrative"
        st.markdown(f'<div style="border:2px solid {"#1a2e44" if sel else "#e0e8dc"};border-radius:10px;padding:.85rem;background:{"#eef2f7" if sel else "white"};">'
            f'<div style="font-weight:700;font-size:.9rem;color:#1a2e44;margin-bottom:.25rem;">📖 Narrative</div>'
            f'<div style="font-size:.78rem;color:#7a907a;">Flowing prose that tells the story of the meeting. Good for complex discussions or sensitive topics.</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("Select Narrative", type="primary" if sel else "secondary", use_container_width=True, key="sel_narrative"):
            st.session_state.mp_style = "narrative"; st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

    if st.button("Continue →", type="primary", use_container_width=True):
        if not m["type"] or not m["date"]:
            st.error("Please enter the meeting type and date.")
        else:
            st.session_state.mp_step = 2; st.rerun()


# ══════════════════════════════════════════════════════════════
# STEP 2 — INPUT (TRANSCRIPT / DRAFT)
# ══════════════════════════════════════════════════════════════
elif st.session_state.mp_step == 2:

    st.markdown('<div class="card"><div class="card-header navy"><h3>📥 Paste or Upload Your Transcript / Draft</h3></div><div class="card-body">', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    This can be anything — a Teams or Zoom auto-transcript, rough handwritten notes typed up,
    a voice memo transcription, bullet points jotted during the meeting, or a previous draft
    that needs cleaning up. The messier the better — that's what this tool is for.
    </div>
    """, unsafe_allow_html=True)

    # Upload option
    uploaded = st.file_uploader(
        "Upload file (.docx, .pdf, or .txt)",
        type=["docx","pdf","txt"],
        key="mp_upload"
    )
    if uploaded:
        text = extract_text(uploaded)
        if text:
            st.session_state.mp_raw_text = text
            st.success(f"✅ {uploaded.name} loaded — {len(text.split())} words")

    st.markdown("**Or paste directly:**")
    st.session_state.mp_raw_text = st.text_area(
        "Transcript / rough notes",
        value=st.session_state.mp_raw_text,
        height=380,
        label_visibility="collapsed",
        placeholder=(
            "Paste anything here — Teams transcript, voice memo, rough notes…\n\n"
            "Examples of what works:\n"
            "• 'Annette opened the meeting at 3.30. Sarah said we need to sort out the timetable. "
            "Mike brought up the issue with the fence. Everyone agreed we need to fix it by Friday.'\n\n"
            "• Speaker-labelled transcript: '00:00 Annette: Welcome everyone…'\n\n"
            "• Rough bullet points: '- discussed X - agreed Y - action: Z by person'"
        )
    )

    if st.session_state.mp_raw_text.strip():
        word_count = len(st.session_state.mp_raw_text.split())
        st.markdown(f'<div style="font-size:.78rem;color:#4a7fb5;margin-top:.25rem;">📊 {word_count} words ready to polish</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Back", use_container_width=True):
            st.session_state.mp_step = 1; st.rerun()
    with n2:
        if st.button("Continue →", type="primary", use_container_width=True):
            if not st.session_state.mp_raw_text.strip():
                st.error("Please paste or upload some content to polish.")
            else:
                st.session_state.mp_step = 3; st.rerun()


# ══════════════════════════════════════════════════════════════
# STEP 3 — AI POLISH
# ══════════════════════════════════════════════════════════════
elif st.session_state.mp_step == 3:

    SYSTEM_PROMPT = """You are an expert minute-taker for Cowandilla Learning Centre (CLC) LBU, Adelaide SA.
You produce clear, accurate, professional meeting minutes.
You preserve all factual content, decisions, and action items — never omit anything important.
You remove filler words, repetition, and off-topic tangents.
You write in third person (e.g. 'Annette advised that…', 'The group agreed to…').
Actions must be clearly attributed to a named person with a due date where mentioned.
Do not add information that was not in the original transcript."""

    def build_prompt():
        style_instruction = {
            "formal": "Use full sentences and a formal professional tone throughout. Each agenda item should have a paragraph-style summary of discussion and any resolution reached.",
            "concise": "Use clear dot points under each heading. Keep each point to one or two lines. Prioritise decisions and actions over discussion.",
            "narrative": "Write in flowing prose that captures the tone and substance of the discussion. This should read like a professional narrative account of the meeting.",
        }.get(st.session_state.mp_style, "")

        present_list  = m.get("present","").strip()
        apology_list  = m.get("apologies","").strip()
        next_mtg      = m.get("next_meeting","").strip()

        return f"""Transform the following rough transcript/notes into polished, professional meeting minutes.

MEETING DETAILS:
- Type: {m['type']}
- Date: {m['date']}
- Time: {m.get('start_time','')} – {m.get('end_time','')}
- Location: {m.get('location','')}
- Organisation: {m.get('organisation','')}
- Chair: {m.get('chair','')}
- Minutes recorded by: {m.get('minutes_by','')}
- Present: {present_list}
- Apologies: {apology_list}
- Next meeting: {next_mtg}

STYLE: {style_instruction}

TRANSCRIPT / ROUGH NOTES:
{st.session_state.mp_raw_text[:12000]}

Return as JSON only (no markdown fences):
{{
  "opening": "One sentence: who opened the meeting, time, quorum noted if relevant",
  "sections": [
    {{
      "heading": "Section heading (e.g. agenda item, topic discussed)",
      "content": "Polished content for this section as a string. Use \\n• for bullet points within. Use \\n\\n for paragraph breaks.",
      "is_actions": false
    }}
  ],
  "actions": [
    {{
      "who": "Person responsible",
      "action": "Specific action to be taken",
      "due": "Due date or 'Next meeting' if not specified"
    }}
  ],
  "closing": "One or two sentences: time meeting closed, next meeting date/time if known",
  "next_meeting": "Next meeting details if mentioned in transcript (or empty string)"
}}

RULES:
- Create a section for each distinct topic discussed — do not clump multiple topics together
- Every decision made must be explicitly stated as a resolution/agreed outcome
- Every action mentioned must appear in the actions array, attributed to a named person
- If a topic was discussed but no decision was reached, note 'Discussion only — no resolution reached'
- Remove all filler words, cross-talk, and off-topic conversation
- Do not fabricate content — only include what was in the transcript"""

    st.markdown("""
    <div class="hero" style="text-align:center;padding:2rem;">
      <div style="font-size:2.5rem;margin-bottom:.5rem;">✨</div>
      <div class="hero-title">Ready to Polish</div>
      <div class="hero-sub">{words} words · {style} style · {meeting_type}</div>
    </div>
    """.replace("{words}", str(len(st.session_state.mp_raw_text.split())))
       .replace("{style}", st.session_state.mp_style.title())
       .replace("{meeting_type}", m["type"]),
       unsafe_allow_html=True)

    # Summary of what's going in
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="card"><div class="card-body" style="text-align:center;"><div style="font-size:1.5rem;">📅</div><div style="font-weight:700;color:#1a2e44;">{m["date"]}</div><div style="font-size:.75rem;color:#7a907a;">{m["type"]}</div></div></div>', unsafe_allow_html=True)
    with col2:
        present_count = len([p for p in m.get("present","").splitlines() if p.strip()])
        st.markdown(f'<div class="card"><div class="card-body" style="text-align:center;"><div style="font-size:1.5rem;">👥</div><div style="font-weight:700;color:#1a2e44;">{present_count} attendees</div><div style="font-size:.75rem;color:#7a907a;">recorded</div></div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="card"><div class="card-body" style="text-align:center;"><div style="font-size:1.5rem;">📊</div><div style="font-weight:700;color:#1a2e44;">{st.session_state.mp_style.title()}</div><div style="font-size:.75rem;color:#7a907a;">output style</div></div></div>', unsafe_allow_html=True)

    p1, p2 = st.columns(2)
    with p1:
        if st.button("← Back to Input", use_container_width=True):
            st.session_state.mp_step = 2; st.rerun()
    with p2:
        if st.button("✨ Polish Minutes Now", type="primary", use_container_width=True):
            with st.spinner("Reading transcript and writing polished minutes — this may take 20–40 seconds…"):
                raw = groq_call(build_prompt(), 4000, SYSTEM_PROMPT)
                raw = raw.replace("```json","").replace("```","").strip()
                if not raw.startswith("{"):
                    idx = raw.find("{")
                    if idx != -1: raw = raw[idx:]
                try:
                    parsed = json.loads(raw)
                    st.session_state.mp_sections  = parsed.get("sections", [])
                    st.session_state.mp_actions    = parsed.get("actions", [])
                    st.session_state["mp_opening"] = parsed.get("opening", "")
                    st.session_state["mp_closing"] = parsed.get("closing", "")
                    if parsed.get("next_meeting","").strip() and not m.get("next_meeting","").strip():
                        m["next_meeting"] = parsed["next_meeting"]
                    st.session_state.mp_step = 4
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not parse AI response ({e}). Please try again.")


# ══════════════════════════════════════════════════════════════
# STEP 4 — REVIEW & EDIT
# ══════════════════════════════════════════════════════════════
elif st.session_state.mp_step == 4:

    st.markdown("""
    <div class="info-box">
    Review the polished minutes below. Edit any section, reorder content, add missing items, or adjust wording.
    The action register at the bottom captures every action mentioned — check it's complete before downloading.
    </div>
    """, unsafe_allow_html=True)

    rev_tabs = st.tabs(["📋 Minutes Content", "✅ Action Register", "📄 Meeting Details"])

    # ── TAB 1: Minutes content ────────────────────────────────
    with rev_tabs[0]:
        st.markdown('<div class="section-label">Opening</div>', unsafe_allow_html=True)
        st.session_state["mp_opening"] = st.text_area(
            "Opening", value=st.session_state.get("mp_opening",""),
            height=70, label_visibility="collapsed", key="rev_opening"
        )

        st.markdown('<div class="section-label">Sections</div>', unsafe_allow_html=True)
        sections = st.session_state.mp_sections
        for si, sec in enumerate(sections):
            with st.expander(f"**{si+1}. {sec.get('heading','Section')}**", expanded=(si < 3)):
                sc1, sc2 = st.columns([4,1])
                with sc1:
                    sec["heading"] = st.text_input(
                        "Section heading", value=sec.get("heading",""),
                        key=f"sec_h_{si}"
                    )
                with sc2:
                    st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
                    if si > 0 and st.button("🗑️ Remove", key=f"sec_del_{si}", use_container_width=True):
                        sections.pop(si); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                sec["content"] = st.text_area(
                    "Content", value=sec.get("content",""),
                    height=160, key=f"sec_c_{si}", label_visibility="collapsed"
                )

        if st.button("➕ Add Section", use_container_width=True):
            sections.append({"heading":"New Section","content":"","is_actions":False}); st.rerun()

        st.markdown('<div class="section-label">Closing</div>', unsafe_allow_html=True)
        st.session_state["mp_closing"] = st.text_area(
            "Closing", value=st.session_state.get("mp_closing",""),
            height=70, label_visibility="collapsed", key="rev_closing"
        )

        st.markdown('<div class="section-label">Next Meeting</div>', unsafe_allow_html=True)
        m["next_meeting"] = st.text_input(
            "Next meeting", value=m.get("next_meeting",""),
            placeholder="e.g. Monday 7 April 2026, 3:30 PM — Staff Room",
            key="rev_next_mtg"
        )

    # ── TAB 2: Action register ────────────────────────────────
    with rev_tabs[1]:
        st.markdown("""
        <div class="info-box">
        Every action item pulled from the minutes. Edit, add, or remove as needed.
        Actions highlighted in amber will appear in a dedicated Action Register table in the document.
        </div>
        """, unsafe_allow_html=True)

        actions = st.session_state.mp_actions
        if not actions:
            st.info("No actions were identified — add them manually below if needed.")
            actions = []

        for ai_idx, action in enumerate(actions):
            ac1, ac2, ac3, ac4 = st.columns([2, 5, 2, 0.6])
            with ac1:
                action["who"] = st.text_input("Person", value=action.get("who",""),
                    key=f"ac_who_{ai_idx}", placeholder="e.g. Annette")
            with ac2:
                action["action"] = st.text_input("Action", value=action.get("action",""),
                    key=f"ac_act_{ai_idx}", placeholder="e.g. Update timetable by Friday")
            with ac3:
                action["due"] = st.text_input("Due", value=action.get("due",""),
                    key=f"ac_due_{ai_idx}", placeholder="e.g. 28 March 2026")
            with ac4:
                st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                if st.button("✕", key=f"ac_del_{ai_idx}"):
                    actions.pop(ai_idx); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if st.button("➕ Add Action Item", use_container_width=True):
            actions.append({"who":"","action":"","due":"Next meeting"}); st.rerun()
        st.session_state.mp_actions = actions

    # ── TAB 3: Meeting details ────────────────────────────────
    with rev_tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            m["type"]      = st.text_input("Meeting type", value=m["type"], key="rv_type")
            m["date"]      = st.text_input("Date", value=m["date"], key="rv_date")
            m["start_time"]= st.text_input("Start time", value=m.get("start_time",""), key="rv_st")
            m["end_time"]  = st.text_input("End time", value=m.get("end_time",""), key="rv_et")
            m["location"]  = st.text_input("Location", value=m.get("location",""), key="rv_loc")
        with c2:
            m["chair"]       = st.text_input("Chaired by", value=m.get("chair",""), key="rv_chair")
            m["minutes_by"]  = st.text_input("Minutes by", value=m.get("minutes_by",""), key="rv_minby")
            m["organisation"]= st.text_input("Organisation", value=m.get("organisation",""), key="rv_org")
        m["present"]   = st.text_area("Present", value=m.get("present",""), height=100, key="rv_present")
        m["apologies"] = st.text_area("Apologies", value=m.get("apologies",""), height=80, key="rv_apo")

    st.markdown("<br>", unsafe_allow_html=True)
    rv1, rv2, rv3 = st.columns([1,1,1])
    with rv1:
        if st.button("← Back", use_container_width=True):
            st.session_state.mp_step = 3; st.rerun()
    with rv2:
        if st.button("🔄 Re-Polish", use_container_width=True, help="Run the AI again on the original transcript"):
            st.session_state.mp_step = 3; st.rerun()
    with rv3:
        if st.button("📄 Generate Document →", type="primary", use_container_width=True):
            st.session_state.mp_step = 5; st.rerun()


# ══════════════════════════════════════════════════════════════
# STEP 5 — GENERATE & DOWNLOAD
# ══════════════════════════════════════════════════════════════
elif st.session_state.mp_step == 5:

    def build_docx():
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        for sec in doc.sections:
            sec.page_width   = Cm(21.0)
            sec.page_height  = Cm(29.7)
            sec.left_margin  = sec.right_margin = Cm(2.0)
            sec.top_margin   = sec.bottom_margin = Cm(2.0)

        NAVY   = RGBColor(0x1a, 0x2e, 0x44)
        BLUE   = RGBColor(0x4a, 0x7f, 0xb5)
        BODY   = RGBColor(0x2a, 0x3a, 0x4a)
        GREY   = RGBColor(0x6a, 0x7f, 0x8a)
        WHITE  = RGBColor(0xff, 0xff, 0xff)
        AMBER  = RGBColor(0xe8, 0xa1, 0x25)
        CREAM  = RGBColor(0xfe, 0xf3, 0xc7)

        def no_border(cell):
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            tcB = OxmlElement("w:tcBorders")
            for side in ["top","left","bottom","right"]:
                b = OxmlElement(f"w:{side}")
                b.set(qn("w:val"), "none"); b.set(qn("w:sz"), "0"); b.set(qn("w:color"), "FFFFFF")
                tcB.append(b)
            tcPr.append(tcB)

        def hex_fill(cell, hx):
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hx)
            tcPr.append(shd)

        def cell_margin(cell, v=80, h=120):
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            mar = OxmlElement("w:tcMar")
            for side, val in [("top",str(v)),("bottom",str(v)),("left",str(h)),("right",str(h))]:
                m2 = OxmlElement(f"w:{side}"); m2.set(qn("w:w"), val); m2.set(qn("w:type"), "dxa"); mar.append(m2)
            tcPr.append(mar)

        def add_run(para, text, bold=False, size=10, color=BODY, italic=False):
            run = para.add_run(text)
            run.bold = bold; run.italic = italic
            run.font.name = "Arial"; run.font.size = Pt(size); run.font.color.rgb = color
            return run

        def add_para(doc_or_cell, text="", bold=False, size=10, color=BODY,
                     space_before=3, space_after=3, align=None, italic=False):
            p = doc_or_cell.add_paragraph()
            p.paragraph_format.space_before = Pt(space_before)
            p.paragraph_format.space_after  = Pt(space_after)
            if align: p.alignment = align
            if text: add_run(p, text, bold, size, color, italic)
            return p

        def add_bullet(doc_or_cell, text, size=9.5, color=BODY, indent=Cm(0.6)):
            p = doc_or_cell.add_paragraph()
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after  = Pt(1.5)
            p.paragraph_format.left_indent  = indent
            p.paragraph_format.first_line_indent = Cm(-0.3)
            add_run(p, "•  " + text.lstrip("•").strip(), size=size, color=color)

        # ── HEADER ──────────────────────────────────────────
        hdr_tbl = doc.add_table(rows=1, cols=1)
        hc = hdr_tbl.rows[0].cells[0]
        hex_fill(hc, "1A2E44"); no_border(hc); cell_margin(hc, 150, 200)
        p_title = hc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0); p_title.paragraph_format.space_after = Pt(4)
        add_run(p_title, "MEETING MINUTES", bold=True, size=14, color=WHITE)
        p_org = hc.add_paragraph()
        p_org.paragraph_format.space_before = Pt(0); p_org.paragraph_format.space_after = Pt(0)
        add_run(p_org, f"{m.get('organisation','')}  ·  {m.get('type','')}  ·  {m.get('date','')}", size=9, color=CREAM)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── MEETING INFO TABLE ───────────────────────────────
        info_fields = [
            ("Date", m.get("date","")),
            ("Time", f"{m.get('start_time','')} – {m.get('end_time','')}".strip(" –")),
            ("Location", m.get("location","")),
            ("Chaired by", m.get("chair","")),
            ("Minutes by", m.get("minutes_by","")),
        ]
        info_fields = [(k,v) for k,v in info_fields if v.strip()]
        if info_fields:
            info_tbl = doc.add_table(rows=len(info_fields), cols=2)
            info_tbl.autofit = True
            for ri, (label, val) in enumerate(info_fields):
                lc = info_tbl.rows[ri].cells[0]
                vc = info_tbl.rows[ri].cells[1]
                for cell in [lc, vc]:
                    no_border(cell); cell_margin(cell, 50, 100)
                    hex_fill(cell, "F4F8FC" if ri % 2 == 0 else "FFFFFF")
                lp = lc.add_paragraph()
                lp.paragraph_format.space_before = Pt(2); lp.paragraph_format.space_after = Pt(2)
                add_run(lp, label, bold=True, size=9, color=BLUE)
                vp = vc.add_paragraph()
                vp.paragraph_format.space_before = Pt(2); vp.paragraph_format.space_after = Pt(2)
                add_run(vp, val, size=9, color=BODY)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── PRESENT & APOLOGIES ──────────────────────────────
        att_tbl = doc.add_table(rows=1, cols=2)
        att_tbl.autofit = True
        for ci, (label, key, hx) in enumerate([("Present","present","F0F9FF"),("Apologies","apologies","FFFBEB")]):
            cell = att_tbl.rows[0].cells[ci]
            no_border(cell); hex_fill(cell, hx); cell_margin(cell, 80, 120)
            hp = cell.add_paragraph()
            hp.paragraph_format.space_before = Pt(0); hp.paragraph_format.space_after = Pt(4)
            add_run(hp, label.upper(), bold=True, size=8.5, color=NAVY if ci==0 else RGBColor(0x78,0x35,0x0f))
            names = [n.strip() for n in m.get(key,"").splitlines() if n.strip()]
            for name in names:
                np2 = cell.add_paragraph()
                np2.paragraph_format.space_before = Pt(1); np2.paragraph_format.space_after = Pt(1)
                add_run(np2, name, size=9, color=BODY, italic=(ci==1))
            if not names:
                ep = cell.add_paragraph()
                ep.paragraph_format.space_before = Pt(1); ep.paragraph_format.space_after = Pt(1)
                add_run(ep, "None", size=9, color=GREY, italic=True)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── OPENING ──────────────────────────────────────────
        opening = st.session_state.get("mp_opening","").strip()
        if opening:
            p_op = doc.add_paragraph()
            p_op.paragraph_format.space_before = Pt(2); p_op.paragraph_format.space_after = Pt(6)
            add_run(p_op, opening, size=9.5, color=BODY, italic=True)

        # ── SECTIONS ─────────────────────────────────────────
        def section_heading(doc, text):
            p_h = doc.add_paragraph()
            p_h.paragraph_format.space_before = Pt(8)
            p_h.paragraph_format.space_after  = Pt(3)
            run_h = add_run(p_h, text, bold=True, size=10.5, color=NAVY)
            # Underline via bottom border on paragraph
            pPr = p_h._p.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            bot = OxmlElement("w:bottom")
            bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "4")
            bot.set(qn("w:space"), "1"); bot.set(qn("w:color"), "4A7FB5")
            pBdr.append(bot); pPr.append(pBdr)

        def render_content(doc, content):
            """Render content string — bullet lines and regular paragraphs."""
            lines = content.split("\n")
            para_buffer = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if para_buffer:
                        p = doc.add_paragraph()
                        p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
                        add_run(p, " ".join(para_buffer), size=9.5, color=BODY)
                        para_buffer = []
                    continue
                if stripped.startswith("•") or stripped.startswith("-"):
                    if para_buffer:
                        p = doc.add_paragraph()
                        p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
                        add_run(p, " ".join(para_buffer), size=9.5, color=BODY)
                        para_buffer = []
                    add_bullet(doc, stripped.lstrip("•-").strip())
                else:
                    para_buffer.append(stripped)
            if para_buffer:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(4)
                add_run(p, " ".join(para_buffer), size=9.5, color=BODY)

        for sec in st.session_state.mp_sections:
            heading = sec.get("heading","").strip()
            content = sec.get("content","").strip()
            if not heading and not content: continue
            if heading: section_heading(doc, heading)
            if content: render_content(doc, content)

        # ── CLOSING ──────────────────────────────────────────
        closing = st.session_state.get("mp_closing","").strip()
        if closing:
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
            p_cl = doc.add_paragraph()
            p_cl.paragraph_format.space_before = Pt(2); p_cl.paragraph_format.space_after = Pt(4)
            add_run(p_cl, closing, size=9.5, color=BODY, italic=True)

        # ── ACTION REGISTER ───────────────────────────────────
        actions = [a for a in st.session_state.mp_actions if a.get("action","").strip()]
        if actions:
            section_heading(doc, "Action Register")
            act_tbl = doc.add_table(rows=len(actions)+1, cols=3)
            act_tbl.autofit = True
            # Header row
            for ci, htext in enumerate(["Person Responsible","Action","Due Date"]):
                hcell = act_tbl.rows[0].cells[ci]
                hex_fill(hcell, "1A2E44"); no_border(hcell); cell_margin(hcell, 60, 120)
                hp = hcell.add_paragraph()
                hp.paragraph_format.space_before = Pt(2); hp.paragraph_format.space_after = Pt(2)
                add_run(hp, htext, bold=True, size=8.5, color=WHITE)
            # Action rows
            for ai, action in enumerate(actions):
                row = act_tbl.rows[ai+1]
                for ci, text in enumerate([action.get("who",""), action.get("action",""), action.get("due","")]):
                    cell = row.cells[ci]
                    no_border(cell)
                    hex_fill(cell, "FFF8E6" if ai % 2 == 0 else "FFFBF0")
                    cell_margin(cell, 50, 120)
                    cp = cell.add_paragraph()
                    cp.paragraph_format.space_before = Pt(2); cp.paragraph_format.space_after = Pt(2)
                    add_run(cp, text, size=9, color=BODY)

        # ── NEXT MEETING ──────────────────────────────────────
        next_mtg = m.get("next_meeting","").strip()
        if next_mtg:
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
            nm_tbl = doc.add_table(rows=1, cols=1)
            nmc = nm_tbl.rows[0].cells[0]
            hex_fill(nmc, "EFF6FF"); no_border(nmc); cell_margin(nmc, 100, 150)
            nmp = nmc.add_paragraph()
            nmp.paragraph_format.space_before = Pt(0); nmp.paragraph_format.space_after = Pt(0)
            add_run(nmp, "Next meeting:  ", bold=True, size=9.5, color=BLUE)
            add_run(nmp, next_mtg, size=9.5, color=BODY)

        # ── FOOTER ───────────────────────────────────────────
        doc.add_paragraph().paragraph_format.space_after = Pt(10)
        p_foot = doc.add_paragraph()
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run(p_foot,
            f"{m.get('organisation','')}  ·  {m.get('type','')}  ·  {m.get('date','')}  ·  Minutes prepared by {m.get('minutes_by','')}",
            size=7.5, color=GREY, italic=True)

        buf = BytesIO(); doc.save(buf); buf.seek(0)
        return buf

    # Generate
    with st.spinner("Generating polished minutes document…"):
        try:
            buf = build_docx()
            st.session_state.mp_docx_bytes = buf.getvalue()
        except Exception as e:
            st.error(f"Document generation error: {e}")
            import traceback; st.code(traceback.format_exc())
            st.stop()

    # Success
    st.markdown("""
    <div class="hero" style="text-align:center;">
      <div style="font-size:2.5rem;margin-bottom:.5rem;">✅</div>
      <div class="hero-title">Minutes Ready</div>
      <div class="hero-sub">Your polished meeting minutes are ready to download, share, and distribute.</div>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    sc1, sc2, sc3, sc4 = st.columns(4)
    present_count = len([p for p in m.get("present","").splitlines() if p.strip()])
    action_count  = len([a for a in st.session_state.mp_actions if a.get("action","").strip()])
    section_count = len([s for s in st.session_state.mp_sections if s.get("heading","").strip()])
    with sc1: st.metric("Meeting type", m.get("type","").split(" — ")[0])
    with sc2: st.metric("Sections", section_count)
    with sc3: st.metric("Attendees", present_count)
    with sc4: st.metric("Actions", action_count)

    # Download
    fname = f"Minutes_{m.get('type','Meeting').replace(' ','_')}_{m.get('date','').replace(' ','_')}.docx".replace("/","")
    st.download_button(
        "📥 Download Minutes (.docx)",
        data=st.session_state.mp_docx_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1:
        if st.button("← Back to Review & Edit", use_container_width=True):
            st.session_state.mp_step = 4; st.rerun()
    with d2:
        if st.button("📝 Polish New Minutes", use_container_width=True):
            for k in ["mp_step","mp_meeting","mp_raw_text","mp_style","mp_sections",
                      "mp_actions","mp_opening","mp_closing","mp_docx_bytes"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
