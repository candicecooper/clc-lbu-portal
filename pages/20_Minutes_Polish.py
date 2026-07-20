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

# Authentication removed - open access

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
        client = Groq(api_key=st.secrets["GROQ_API_KEY"], timeout=120.0)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        last_err = None
        for attempt in range(2):  # one automatic retry on transient failure
            try:
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=max_tokens,
                    temperature=0.1,  # low temperature — factual fidelity over creativity
                    messages=messages
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
        return f"[AI error: {last_err}]"
    except Exception as e:
        return f"[AI error: {e}]"

# ── ROBUST JSON PARSING ───────────────────────────────────────
def parse_ai_json(raw: str) -> dict:
    """Parse JSON from an AI response, tolerating common LLM quirks:
    - markdown code fences
    - text before/after the JSON object
    - literal newlines/tabs inside string values (invalid control chars)
    - trailing commas
    """
    import re
    raw = raw.replace("```json", "").replace("```", "").strip()
    # Trim to outermost { ... }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in AI response")
    raw = raw[start:end+1]
    # 1) Straight parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 2) strict=False allows literal control characters inside strings
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        pass
    # 3) Escape raw control characters that appear inside string values,
    #    then remove trailing commas, and retry
    def _escape_ctrl(match):
        s = match.group(0)
        return (s.replace("\n", "\\n").replace("\r", "\\r")
                 .replace("\t", "\\t"))
    # Match JSON string literals (handles escaped quotes) incl. any raw ctrl chars inside
    fixed = re.sub(r'"(?:[^"\\]|\\.)*"', _escape_ctrl, raw, flags=re.DOTALL)
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)  # trailing commas
    return json.loads(fixed, strict=False)

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
            "subject": "",
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

# ── DRAFT SAVE / RESTORE (protects against timeouts & disconnects) ──
def export_draft_bytes() -> bytes:
    draft = {
        "mp_meeting":  st.session_state.mp_meeting,
        "mp_raw_text": st.session_state.mp_raw_text,
        "mp_style":    st.session_state.mp_style,
        "mp_sections": st.session_state.mp_sections,
        "mp_actions":  st.session_state.mp_actions,
        "mp_opening":  st.session_state.get("mp_opening",""),
        "mp_closing":  st.session_state.get("mp_closing",""),
        "mp_step":     st.session_state.mp_step,
        "saved":       str(date.today()),
    }
    return json.dumps(draft, indent=2, ensure_ascii=False).encode("utf-8")

def restore_draft(uploaded_file) -> bool:
    try:
        draft = json.loads(uploaded_file.read().decode("utf-8"))
        for k in ["mp_meeting","mp_raw_text","mp_style","mp_sections","mp_actions"]:
            if k in draft:
                st.session_state[k] = draft[k]
        st.session_state["mp_opening"] = draft.get("mp_opening","")
        st.session_state["mp_closing"] = draft.get("mp_closing","")
        try:
            st.session_state.mp_step = max(1, min(int(draft.get("mp_step", 2)), 4))
        except (TypeError, ValueError):
            st.session_state.mp_step = 2
        return True
    except Exception as e:
        st.error(f"Could not restore draft: {e}")
        return False

def draft_toolbar():
    with st.expander("💾 Save / restore progress — protects your work if the app times out"):
        st.caption(
            "Download a draft at any point (especially before polishing and after reviewing). "
            "If the app disconnects or times out, upload the draft here and you'll be back exactly where you left off."
        )
        dc1, dc2 = st.columns([1, 2])
        with dc1:
            st.download_button(
                "⬇️ Download draft",
                data=export_draft_bytes(),
                file_name=f"minutes_draft_{m.get('type','meeting').replace(' ','_')}_{date.today()}.json",
                mime="application/json",
                use_container_width=True,
                key="draft_dl",
            )
        with dc2:
            up = st.file_uploader("Restore a saved draft (.json)", type=["json"], key="draft_up")
            if up is not None:
                if st.button("♻️ Restore this draft", type="primary", use_container_width=True, key="draft_rs"):
                    if restore_draft(up):
                        st.success("Draft restored.")
                        st.rerun()

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

# Draft save/restore available on every step
draft_toolbar()

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
        m["subject"] = st.text_input("Subject / reason for meeting", value=m.get("subject",""),
            placeholder="e.g. Xavier Shilton Sumner — TAC Review  ·  Term 1 Staff Meeting",
            help="Who or what the meeting is about — appears prominently on the minutes")
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

        # ── Auto-extract meeting details from transcript ──────
        if st.button("🔍 Auto-detect meeting details from transcript", use_container_width=True, key="auto_detect"):
            with st.spinner("Reading transcript for meeting details…"):
                detect_prompt = f"""Read this transcript carefully and extract meeting metadata.

TRANSCRIPT:
{st.session_state.mp_raw_text[:8000]}

Return as JSON only (no markdown):
{{
  "date": "full date mentioned e.g. Monday 23 March 2026 — extract exactly as stated",
  "start_time": "time meeting started e.g. 3:30 PM",
  "end_time": "time meeting closed if mentioned",
  "location": "where the meeting was held or platform used e.g. Teams, CLC Staff Room",
  "chair": "name of person who chaired or opened the meeting",
  "minutes_by": "name of person taking minutes if mentioned",
  "subject": "what the meeting is about — student name, topic, or meeting purpose e.g. 'Xavier Shilton Sumner — TAC Review' or 'Term 1 Staff Meeting'",
  "present": [
    {{"name": "full name", "role": "their role or organisation e.g. Principal, BSE, Kinship Carer, DCP Worker"}}
  ],
  "apologies": [
    {{"name": "full name", "role": "role if mentioned"}}
  ],
  "next_meeting": "next meeting details if mentioned"
}}

Extract only what is explicitly stated. For present/apologies, include EVERY person introduced or mentioned as attending — including external attendees like DCP workers, parents, specialists.
If a field is not mentioned, return an empty string or empty array."""

                raw = groq_call(detect_prompt, 1500)
                try:
                    detected = parse_ai_json(raw)
                    changed = []
                    if detected.get("date","").strip() and not m.get("date","").strip():
                        m["date"] = detected["date"]; changed.append("date")
                    elif detected.get("date","").strip():
                        m["date"] = detected["date"]; changed.append("date")
                    if detected.get("start_time","").strip():
                        m["start_time"] = detected["start_time"]; changed.append("start time")
                    if detected.get("end_time","").strip():
                        m["end_time"] = detected["end_time"]; changed.append("end time")
                    if detected.get("location","").strip():
                        m["location"] = detected["location"]; changed.append("location")
                    if detected.get("chair","").strip():
                        m["chair"] = detected["chair"]; changed.append("chair")
                    if detected.get("minutes_by","").strip():
                        m["minutes_by"] = detected["minutes_by"]; changed.append("minutes by")
                    if detected.get("subject","").strip():
                        m["subject"] = detected["subject"]; changed.append("subject/reason")
                    if detected.get("next_meeting","").strip():
                        m["next_meeting"] = detected["next_meeting"]; changed.append("next meeting")
                    # Build present list with roles
                    present_list = detected.get("present",[])
                    if present_list:
                        m["present"] = "\n".join(
                            f"{p['name']}{' (' + p['role'] + ')' if p.get('role') else ''}"
                            for p in present_list if p.get("name")
                        )
                        changed.append(f"attendees ({len(present_list)} people)")
                    # Build apologies list
                    apo_list = detected.get("apologies",[])
                    if apo_list:
                        m["apologies"] = "\n".join(
                            f"{p['name']}{' (' + p['role'] + ')' if p.get('role') else ''}"
                            for p in apo_list if p.get("name")
                        )
                        changed.append("apologies")
                    if changed:
                        st.success(f"✅ Auto-detected: {', '.join(changed)} — scroll up to Meeting Details (Step 1) to review")
                    else:
                        st.info("Could not detect meeting details from transcript. Fill in manually.")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Could not parse detection result. Fill in details manually ({e}).")

    st.markdown('</div></div>', unsafe_allow_html=True)

    # Show current detected details as a summary
    if any([m.get("date"), m.get("present"), m.get("subject")]):
        st.markdown('<div class="card"><div class="card-header slate"><h3>📋 Current Meeting Details</h3></div><div class="card-body">', unsafe_allow_html=True)
        det1, det2 = st.columns(2)
        with det1:
            m["date"]      = st.text_input("Date", value=m.get("date",""), key="s2_date", placeholder="e.g. Monday 23 March 2026")
            m["start_time"]= st.text_input("Start time", value=m.get("start_time",""), key="s2_st", placeholder="e.g. 3:30 PM")
            m["end_time"]  = st.text_input("End time", value=m.get("end_time",""), key="s2_et", placeholder="e.g. 4:45 PM")
            m["location"]  = st.text_input("Location / platform", value=m.get("location",""), key="s2_loc", placeholder="e.g. CLC Staff Room / Teams")
        with det2:
            m["subject"]   = st.text_input("Subject / reason for meeting", value=m.get("subject",""), key="s2_subj",
                                placeholder="e.g. Xavier Shilton Sumner — TAC Review · Term 1 Staff Meeting")
            m["chair"]     = st.text_input("Chaired by", value=m.get("chair",""), key="s2_chair")
            m["minutes_by"]= st.text_input("Minutes by", value=m.get("minutes_by",""), key="s2_minby")
        m["present"]   = st.text_area("Present (name + role)", value=m.get("present",""), height=110, key="s2_pres",
                            placeholder="e.g.\nAnnette Smith (Principal, CLC)\nSarah Cromer (BSE)\nJane Doe (Kinship Carer)")
        m["apologies"] = st.text_area("Apologies", value=m.get("apologies",""), height=70, key="s2_apo")
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

    SYSTEM_PROMPT = """You are a professional minute-taker producing formal meeting minutes for Cowandilla Learning Centre (CLC) LBU, Adelaide SA.

These minutes are the OFFICIAL RECORD of the meeting, distributed to ALL attendees including external parties — DCP workers, parents/carers, BSE, allied health professionals, and other agencies. Because they are an official record, ACCURACY OVERRIDES EVERYTHING ELSE. A vague but accurate record is acceptable; a detailed but invented one is not.

FIDELITY — the absolute rule:
- Every statement in the minutes must be directly traceable to the transcript
- NEVER invent, guess, or infer who said something. NEVER assign a statement to a named person unless the transcript clearly identifies them as the speaker (a speaker label like "Annette:", or wording like "Sarah said/asked/raised…", or an unmistakable first-person context)
- NEVER invent names, roles, quotes, figures, dates, locations, or events that are not in the transcript
- NEVER embellish or extrapolate — do not add plausible-sounding detail the transcript does not contain
- If the transcript is ambiguous about a detail, either omit it or record it at the level of certainty the transcript supports

ATTRIBUTION — use it only when it is genuinely in the transcript:
- When the speaker IS clearly identified: attribute precisely — "Ms Smith advised that…", "The Principal, Ms Jones, reported that…"
- When the speaker is NOT clearly identified: use neutral minute-taking language — "It was noted that…", "Discussion was held regarding…", "The group agreed that…", "A concern was raised that…". This is CORRECT professional practice, not a failure
- When multiple people contributed and each is identifiable, record each contribution separately with its speaker
- If someone asked a question and the transcript shows who asked and who answered, record both; if not, record the question and response neutrally

THOROUGHNESS — within the bounds of fidelity:
- Capture everything of substance from the transcript — do not summarise away important detail
- Record specific figures, dates, names, and details exactly as stated in the transcript
- Capture concerns raised, questions asked, and responses given
- Note where there was agreement, disagreement, or uncertainty — as the transcript shows it

STRUCTURE:
- One section per distinct topic — never merge two topics
- Within each section: (1) context/background as given in the transcript, (2) discussion, (3) resolution or outcome
- A Resolution must be labelled "Resolution:" ONLY where the transcript shows a decision was actually made; otherwise state "Discussion only — no resolution reached at this meeting"
- Every action must record the responsible person, task, and due date as stated; if the transcript does not name a responsible person or date, write "Not specified" rather than guessing
- Write for an external reader who was not present"""

    def build_prompt():
        style_instruction = {
            "formal": "Write in complete formal sentences. Within each section write full paragraphs — one for context/background, one or more for the discussion (attributing points to speakers by name only where the transcript identifies them; otherwise using neutral formal wording), and a clearly labelled Resolution or Outcome where one was actually reached. Do not use dot points as the primary format.",
            "concise": "Use bullet points. Each bullet must be a complete statement — attributed by name where the transcript identifies the speaker (e.g. '• Ms Smith (BSE) advised that the current ISP funding allocation is unclear.'), or neutrally worded where it does not (e.g. '• It was agreed the timetable requires updating.'). Never invent an attribution to avoid neutral wording.",
            "narrative": "Write in flowing formal prose. Narrate the discussion as it unfolded, attributing contributions to speakers only where the transcript identifies them, and otherwise describing the discussion neutrally. The reader should be able to follow what was discussed and decided — with every detail traceable to the transcript.",
        }.get(st.session_state.mp_style, "")

        present_list = m.get("present","").strip()
        apology_list = m.get("apologies","").strip()
        next_mtg     = m.get("next_meeting","").strip()
        subject      = m.get("subject","").strip()

        return f"""Produce THOROUGH, ACCURATE, formal meeting minutes from the transcript below.

CRITICAL: These minutes must capture everything of substance from the transcript — and NOTHING that is not in it.
Do not summarise away detail. Do not omit concerns, questions, or explanations.
Attribute statements by name ONLY where the transcript clearly identifies the speaker.
Where the speaker is not clearly identified, use neutral wording ("It was noted that…", "Discussion was held regarding…") — do NOT guess or assign a name.

MEETING DETAILS:
- Meeting type: {m['type']}
- Subject / reason: {subject if subject else '(extract from transcript)'}
- Date: {m['date'] if m.get('date') else '(extract from transcript)'}
- Time: {m.get('start_time','')} – {m.get('end_time','')}
- Location: {m.get('location','')}
- Organisation: {m.get('organisation','')}
- Chaired by: {m.get('chair','')}
- Minutes recorded by: {m.get('minutes_by','')}
- Present: {present_list if present_list else '(extract ALL names and roles from transcript)'}
- Apologies: {apology_list if apology_list else '(extract from transcript if mentioned)'}
- Next meeting: {next_mtg}

OUTPUT STYLE: {style_instruction}

TRANSCRIPT:
{st.session_state.mp_raw_text[:14000]}

Return as JSON only (no markdown fences):
{{
  "date": "full meeting date extracted from transcript if not already provided",
  "start_time": "meeting start time",
  "end_time": "meeting end time if mentioned",
  "location": "meeting location or platform",
  "chair": "name of chair",
  "minutes_by": "name of minute-taker if mentioned",
  "subject": "subject or reason for meeting",
  "present": [
    {{"name": "full name", "role": "role and organisation e.g. Principal, CLC; BSE, DfE; Kinship Carer; DCP Caseworker"}}
  ],
  "apologies": [
    {{"name": "full name", "role": "role if mentioned"}}
  ],
  "opening": "Formal opening: name of chair, date, time, location, who was present. 2-3 sentences.",
  "sections": [
    {{
      "heading": "Specific topic heading — be descriptive e.g. 'Safety & Risk Plan Review' not just 'Safety'",
      "content": "THOROUGH content for this section, drawn ONLY from the transcript. Include: (1) How the topic arose. (2) Contributions attributed by name ONLY where the transcript clearly identifies the speaker — e.g. 'Ms Cromer (BSE) stated that...'; where the speaker is unclear, use neutral wording — 'It was noted that...', 'Discussion was held regarding...'. (3) Concerns raised (with the person's name only if the transcript identifies them). (4) Evidence or information presented. (5) The outcome — labelled Resolution: [what was agreed] ONLY if the transcript shows a decision was made, otherwise 'Discussion only — no resolution reached at this meeting'. Use \\n for new paragraphs. Use \\n• for bullet points within a section.",
      "is_actions": false
    }}
  ],
  "actions": [
    {{
      "who": "Full name of person responsible AS STATED in the transcript, or 'Not specified'",
      "action": "Specific action as stated in the transcript — written so someone not at the meeting understands what is required. Do not add detail the transcript does not contain.",
      "due": "Due date as stated in the transcript, or 'Not specified'"
    }}
  ],
  "closing": "Formal closing: time meeting closed, who closed it, thanks if given, next meeting date/time — only details actually in the transcript.",
  "next_meeting": "Full next meeting details if mentioned"
}}

MANDATORY RULES — failure to follow these is not acceptable:
1. FIDELITY FIRST: never attribute a statement to a named person unless the transcript clearly identifies them as the speaker. Where the speaker is unclear, neutral wording ("It was noted that…") is REQUIRED — this is correct minute-taking practice, not a shortcoming
2. Never invent names, roles, quotes, figures, dates, or events. Every sentence must be traceable to the transcript
3. Each section must be long enough to fully capture the discussion — but depth comes from the transcript, never from invention
4. Capture specific details: dates, names, figures, locations, document names — exactly as stated in the transcript
5. If someone raised a question or concern, record the question AND the response as the transcript gives them
6. One section per topic — create as many sections as needed, never merge unrelated topics
7. "Resolution:" appears ONLY where the transcript shows a decision was actually made
8. Actions: every action mentioned in the transcript must appear in the actions array — with "Not specified" for any missing person or due date, never a guess
9. Do NOT omit content because it seems minor — if it was discussed, it belongs in the minutes
10. Write for an external reader (e.g. a DCP worker reading these 6 months later) — which is exactly why nothing can be invented"""

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
            with st.spinner("Reading transcript and writing detailed minutes — this may take 30–60 seconds…"):
                raw = groq_call(build_prompt(), 6000, SYSTEM_PROMPT)
                try:
                    parsed = parse_ai_json(raw)
                    st.session_state.mp_sections  = parsed.get("sections", [])
                    st.session_state.mp_actions    = parsed.get("actions", [])
                    st.session_state["mp_opening"] = parsed.get("opening", "")
                    st.session_state["mp_closing"] = parsed.get("closing", "")
                    # Auto-fill meeting details from AI extraction if not already set
                    if parsed.get("date","").strip() and not m.get("date","").strip():
                        m["date"] = parsed["date"]
                    if parsed.get("start_time","").strip() and not m.get("start_time","").strip():
                        m["start_time"] = parsed["start_time"]
                    if parsed.get("end_time","").strip() and not m.get("end_time","").strip():
                        m["end_time"] = parsed["end_time"]
                    if parsed.get("location","").strip() and not m.get("location","").strip():
                        m["location"] = parsed["location"]
                    if parsed.get("chair","").strip() and not m.get("chair","").strip():
                        m["chair"] = parsed["chair"]
                    if parsed.get("minutes_by","").strip() and not m.get("minutes_by","").strip():
                        m["minutes_by"] = parsed["minutes_by"]
                    if parsed.get("subject","").strip():
                        m["subject"] = parsed["subject"]
                    if parsed.get("next_meeting","").strip() and not m.get("next_meeting","").strip():
                        m["next_meeting"] = parsed["next_meeting"]
                    # Build present/apologies from extracted lists if not already set
                    if parsed.get("present") and not m.get("present","").strip():
                        m["present"] = "\n".join(
                            f"{p['name']}{' (' + p['role'] + ')' if p.get('role') else ''}"
                            for p in parsed["present"] if p.get("name")
                        )
                    if parsed.get("apologies") and not m.get("apologies","").strip():
                        m["apologies"] = "\n".join(
                            f"{p['name']}{' (' + p['role'] + ')' if p.get('role') else ''}"
                            for p in parsed["apologies"] if p.get("name")
                        )
                    st.session_state.mp_step = 4
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not parse AI response ({e}). Please try again.")
                    with st.expander("Show raw AI response (for troubleshooting)"):
                        st.code(raw)


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
            m["subject"]   = st.text_input("Subject / reason", value=m.get("subject",""), key="rv_subj")
            m["start_time"]= st.text_input("Start time", value=m.get("start_time",""), key="rv_st")
            m["end_time"]  = st.text_input("End time", value=m.get("end_time",""), key="rv_et")
            m["location"]  = st.text_input("Location", value=m.get("location",""), key="rv_loc")
        with c2:
            m["chair"]       = st.text_input("Chaired by", value=m.get("chair",""), key="rv_chair")
            m["minutes_by"]  = st.text_input("Minutes by", value=m.get("minutes_by",""), key="rv_minby")
            m["organisation"]= st.text_input("Organisation", value=m.get("organisation",""), key="rv_org")
        m["present"]   = st.text_area("Present", value=m.get("present",""), height=100, key="rv_present")
        m["apologies"] = st.text_area("Apologies", value=m.get("apologies",""), height=80, key="rv_apo")

    # ── AI REFINEMENT CHAT ────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="card"><div class="card-header teal"><h3>🤖 Ask AI to Refine the Minutes</h3></div><div class="card-body">', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    Tell the AI what to change — it will update the minutes and you can keep asking until it's right.
    <br><strong>Examples:</strong> "Make section 2 more formal" · "Add an action for Mike to fix the fence by Friday" ·
    "Expand the timetable discussion" · "Remove the part about the photocopier" · "Rewrite the opening in third person"
    </div>
    """, unsafe_allow_html=True)

    # Show chat history
    if "mp_chat" not in st.session_state:
        st.session_state.mp_chat = []

    for msg in st.session_state.mp_chat:
        role_icon = "🧑‍💼" if msg["role"] == "user" else "🤖"
        bg = "#f0f7ff" if msg["role"] == "user" else "#f0faf8"
        border = "#4a7fb5" if msg["role"] == "user" else "#1a7a6e"
        st.markdown(
            f'<div style="background:{bg};border-left:3px solid {border};border-radius:0 8px 8px 0;'
            f'padding:.6rem .9rem;margin-bottom:.4rem;font-size:.85rem;color:#1a2e44;">'
            f'<span style="font-weight:700;">{role_icon} {"You" if msg["role"]=="user" else "AI"}</span>'
            f'<br>{msg["content"]}'
            f'</div>',
            unsafe_allow_html=True
        )

    # Input
    with st.form("mp_ai_chat_form", clear_on_submit=True):
        chat_cols = st.columns([5, 1])
        with chat_cols[0]:
            user_instruction = st.text_input(
                "Your instruction",
                placeholder="e.g. Make the opening more concise · Add action for Sarah to send agenda by Monday · Expand the discussion about the new timetable",
                label_visibility="collapsed"
            )
        with chat_cols[1]:
            send = st.form_submit_button("✨ Apply", type="primary", use_container_width=True)

        if send and user_instruction.strip():
            # Build current minutes as text for the AI to work with
            current_minutes = f"OPENING:\n{st.session_state.get('mp_opening','')}\n\n"
            for sec in st.session_state.mp_sections:
                current_minutes += f"SECTION: {sec.get('heading','')}\n{sec.get('content','')}\n\n"
            current_minutes += f"CLOSING:\n{st.session_state.get('mp_closing','')}\n\n"
            if st.session_state.mp_actions:
                current_minutes += "ACTIONS:\n"
                for a in st.session_state.mp_actions:
                    current_minutes += f"- {a.get('who','')}: {a.get('action','')} (due: {a.get('due','')})\n"

            refine_prompt = f"""You are refining formal meeting minutes for Cowandilla Learning Centre (CLC) LBU.
These minutes are an official record distributed to all attendees including external parties.

STANDARDS TO MAINTAIN:
- NEVER invent who said something. Attribute a statement to a named person only if the current minutes or the user's instruction already identify that person as the speaker — otherwise keep or use neutral wording ("It was noted that…")
- NEVER add names, figures, dates, or events that are not in the current minutes or the user's instruction
- Sections must remain thorough — never delete substance the user did not ask you to remove
- "Resolution:" labels stay only where a decision was actually recorded
- Write in formal third person throughout

CURRENT MINUTES:
{current_minutes}

USER INSTRUCTION:
{user_instruction}

Apply the instruction precisely and return the complete updated minutes as JSON only (no markdown):
{{
  "opening": "updated opening text",
  "sections": [
    {{"heading": "section title", "content": "section content with \\n• for bullets"}}
  ],
  "actions": [
    {{"who": "person", "action": "action description", "due": "due date"}}
  ],
  "closing": "updated closing text",
  "change_summary": "One sentence describing what you changed"
}}

RULES:
- Only make the change the user asked for — preserve everything else exactly as written
- New content may only come from the user's instruction — do not fabricate supporting detail
- If the instruction adds a new action, add it to the actions array
- Maintain {st.session_state.mp_style} style throughout
- Return ALL sections, even unchanged ones"""

            with st.spinner("Applying changes…"):
                raw = groq_call(refine_prompt, 3000,
                    "You are a professional minute-taker refining meeting minutes. Apply changes precisely as instructed. Preserve all other content exactly. Never invent attribution — never assign a statement to a named person unless the current minutes or the instruction identify them as the speaker. Never fabricate names, figures, dates, or events.")
                try:
                    updated = parse_ai_json(raw)
                    # Apply updates
                    if updated.get("opening","").strip():
                        st.session_state["mp_opening"] = updated["opening"]
                    if updated.get("sections"):
                        st.session_state.mp_sections = updated["sections"]
                    if updated.get("actions") is not None:
                        st.session_state.mp_actions = updated["actions"]
                    if updated.get("closing","").strip():
                        st.session_state["mp_closing"] = updated["closing"]
                    # Log to chat
                    summary = updated.get("change_summary", "Changes applied.")
                    st.session_state.mp_chat.append({"role": "user", "content": user_instruction})
                    st.session_state.mp_chat.append({"role": "assistant", "content": f"✅ Done — {summary}"})
                    st.rerun()
                except Exception as e:
                    st.session_state.mp_chat.append({"role": "user", "content": user_instruction})
                    st.session_state.mp_chat.append({"role": "assistant", "content": f"⚠️ Could not apply that change ({e}). Try rephrasing your instruction."})
                    st.rerun()

    # Quick-action buttons
    st.markdown("**Quick actions:**")
    qa_cols = st.columns(4)
    quick_actions = [
        ("📏 More concise",        "Make all sections more concise — remove unnecessary words but keep all existing attributions and specific details exactly as they are. Do not add or change any attribution."),
        ("🎩 More formal",         "Rewrite all sections in a more formal professional tone. Keep every attribution exactly as it currently stands — do not add names to statements that are currently unattributed."),
        ("✅ Extract all actions", "Find any action items mentioned in the minutes text that are not yet in the action register and add them. Use the responsible person's name only if the minutes state it; otherwise use 'Not specified'."),
        ("🔍 Check thoroughness",  "Review every section and expand any that are too brief — using ONLY content already present in the minutes. Do not add new attributions, names, or details that are not already there. Ensure every genuine decision is labelled Resolution:. Do not remove any existing content."),
    ]
    for i, (label, instruction) in enumerate(quick_actions):
        with qa_cols[i]:
            if st.button(label, key=f"qa_{i}", use_container_width=True):
                st.session_state.mp_chat.append({"role": "user", "content": instruction})
                # Build current state
                current = f"OPENING:\n{st.session_state.get('mp_opening','')}\n\n"
                for sec in st.session_state.mp_sections:
                    current += f"SECTION: {sec.get('heading','')}\n{sec.get('content','')}\n\n"
                current += f"CLOSING:\n{st.session_state.get('mp_closing','')}\n"
                refine_p = f"""Current minutes:\n{current}\n\nInstruction: {instruction}\n\nReturn updated JSON only:\n{{"opening":"...","sections":[{{"heading":"...","content":"..."}}],"actions":[{{"who":"...","action":"...","due":"..."}}],"closing":"...","change_summary":"one sentence"}}"""
                with st.spinner("Applying…"):
                    raw = groq_call(refine_p, 3000, "You are a professional minute-taker. Apply changes precisely. Never invent attribution or fabricate details — only use content already in the minutes or the instruction.")
                    try:
                        upd = parse_ai_json(raw)
                        if upd.get("opening","").strip(): st.session_state["mp_opening"] = upd["opening"]
                        if upd.get("sections"): st.session_state.mp_sections = upd["sections"]
                        if upd.get("actions") is not None: st.session_state.mp_actions = upd["actions"]
                        if upd.get("closing","").strip(): st.session_state["mp_closing"] = upd["closing"]
                        st.session_state.mp_chat.append({"role":"assistant","content":f"✅ {upd.get('change_summary','Done.')}"})
                    except:
                        st.session_state.mp_chat.append({"role":"assistant","content":"⚠️ Could not apply — try the manual instruction box above."})
                st.rerun()

    if st.session_state.mp_chat:
        if st.button("🗑️ Clear chat history", key="clear_chat"):
            st.session_state.mp_chat = []; st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

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
        # Subject line prominently
        subject = m.get("subject","").strip()
        p_subj = hc.add_paragraph()
        p_subj.paragraph_format.space_before = Pt(0); p_subj.paragraph_format.space_after = Pt(3)
        if subject:
            add_run(p_subj, subject, bold=True, size=10.5, color=CREAM)
        p_org = hc.add_paragraph()
        p_org.paragraph_format.space_before = Pt(0); p_org.paragraph_format.space_after = Pt(0)
        add_run(p_org, f"{m.get('organisation','')}  ·  {m.get('type','')}  ·  {m.get('date','')}", size=9, color=CREAM)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── MEETING INFO TABLE ───────────────────────────────
        info_fields = [
            ("Date", m.get("date","")),
            ("Time", f"{m.get('start_time','')} – {m.get('end_time','')}".strip(" –")),
            ("Location", m.get("location","")),
            ("Subject / Reason", subject),
            ("Chaired by", m.get("chair","")),
            ("Minutes prepared by", m.get("minutes_by","")),
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
                      "mp_actions","mp_opening","mp_closing","mp_docx_bytes","mp_chat"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
