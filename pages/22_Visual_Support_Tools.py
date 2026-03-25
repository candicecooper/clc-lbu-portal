# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# Build, customise and print visual supports: lanyard cards, desk mats,
# First-Then boards, visual schedules, communication boards, regulation tools
# =============================================================================

import streamlit as st
import json
from datetime import datetime

st.set_page_config(
    page_title="Visual Support Tools - CLC",
    page_icon="🎨",
    layout="wide",
)

# -- Brand colours ------------------------------------------------------------
TEAL   = "#1A5C78"
TEAL_L = "#2A8AAF"
TEAL_B = "#EBF5FA"
AMBER  = "#D4860A"
AMB_B  = "#FEF7EA"
GREEN  = "#2D7D4F"
GRN_B  = "#E8F5EE"
NAVY   = "#1A2E44"
CREAM  = "#F7F9FB"

# -- CSS ----------------------------------------------------------------------
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:{CREAM}; }}

.vst-header {{
    background:linear-gradient(135deg,{TEAL} 0%,#0F3D54 100%);
    color:#fff; padding:1rem 1.5rem; border-radius:12px;
    margin-bottom:1.5rem; display:flex; align-items:center; gap:1rem;
}}
.vst-header .icon {{ font-size:2.2rem; }}
.vst-header h1 {{ margin:0; font-size:1.35rem; font-weight:800; }}
.vst-header p  {{ margin:.1rem 0 0; opacity:.8; font-size:.82rem; }}

.section-card {{
    background:#fff; border-radius:12px; border:1px solid #dde6ee;
    padding:1.1rem 1.3rem; margin-bottom:1rem;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
}}
.section-card h3 {{
    margin:0 0 .75rem; font-size:1rem; font-weight:800; color:{TEAL};
}}

.vc {{
    background:#fff; border-radius:10px; border:2px solid #dde6ee;
    padding:.85rem .6rem; text-align:center; min-height:120px;
    display:flex; flex-direction:column; justify-content:center;
}}
.vc .em {{ font-size:2.4rem; line-height:1; margin-bottom:.45rem; }}
.vc .ti {{ font-size:.88rem; font-weight:700; color:{NAVY}; line-height:1.25; }}
.vc .su {{ font-size:.73rem; color:#718096; margin-top:.25rem; }}

.fw {{
    display:inline-block; padding:.1rem .42rem; border-radius:20px;
    font-size:.62rem; font-weight:700; margin:.1rem .1rem 0 0;
}}

.slot {{
    border:2px dashed #cbd5e0; border-radius:10px;
    min-height:130px; display:flex; flex-direction:column;
    align-items:center; justify-content:center; padding:1rem;
    text-align:center; background:#f8fafc;
}}
.slot.filled {{
    border-style:solid; border-color:{TEAL}; background:{TEAL_B};
}}
.slot .slot-lbl {{
    font-size:.65rem; font-weight:800; text-transform:uppercase;
    letter-spacing:.1em; color:#718096; margin-bottom:.4rem;
}}
.slot.filled .slot-lbl {{ color:{TEAL}; }}
.slot .slot-em {{ font-size:2.5rem; line-height:1; margin-bottom:.3rem; }}
.slot .slot-tx {{ font-size:.88rem; font-weight:700; }}

.zone {{ border-radius:10px; padding:.85rem; border:2px solid transparent; margin-bottom:.5rem; }}
.zone-blue   {{ background:#DBEAFE; border-color:#93C5FD; }}
.zone-green  {{ background:#DCFCE7; border-color:#86EFAC; }}
.zone-yellow {{ background:#FEF9C3; border-color:#FDE047; }}
.zone-red    {{ background:#FEE2E2; border-color:#FCA5A5; }}
.zone h4     {{ margin:0 0 .4rem; font-size:.9rem; font-weight:800; }}
.zone .feels {{ font-size:.75rem; color:#4a5568; line-height:1.7; }}

.research-note {{
    background:{TEAL_B}; border:1px solid {TEAL}; border-radius:8px;
    padding:.6rem .9rem; font-size:.8rem; color:{TEAL}; margin-top:.75rem;
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA
# =============================================================================

CARDS = [
    # Regulation
    dict(id="feelings",   cat="regulation",    color=AMBER,     em="😊😐😢😠", ti="How am I feeling?",        sub="Point to show your feeling",      fw=["BSEM","ZOR","TI"]),
    dict(id="calmdown",   cat="regulation",    color=AMBER,     em="🧘",        ti="Lets calm down",           sub="Breathe - Move - Squeeze",        fw=["BSEM","TI","OT"]),
    dict(id="break",      cat="regulation",    color=AMBER,     em="⏸️",        ti="I need a break",           sub="I will come back soon",           fw=["TI","PBS","BSEM"]),
    dict(id="bodycheck",  cat="regulation",    color=AMBER,     em="🫁",        ti="Body check",               sub="What does my body feel?",         fw=["OT","BSEM"]),
    dict(id="zones",      cat="regulation",    color=AMBER,     em="🟢",        ti="What zone am I in?",       sub="Blue/Green/Yellow/Red",           fw=["ZOR","BSEM"]),
    dict(id="volume",     cat="regulation",    color=AMBER,     em="🔊",        ti="Volume check 1-5",         sub="What level is my voice?",         fw=["OT","PBS"]),
    dict(id="welldone",   cat="regulation",    color=AMBER,     em="🌟",        ti="Well done!",               sub="You are doing great",             fw=["PBS","BSEM"]),
    dict(id="voicein",    cat="regulation",    color=AMBER,     em="🏠",        ti="Inside voice",             sub="Quiet, calm voice inside",        fw=["OT","EALD"]),
    # Communication
    dict(id="ineed",      cat="communication", color=TEAL,      em="🙋",        ti="I need...",                sub="Toilet / Water / Food / Help",    fw=["AAC","EALD"]),
    dict(id="corewords",  cat="communication", color=TEAL,      em="💬",        ti="Core words",               sub="Yes / No / Want / Stop / More",   fw=["AAC","EALD","UDL"]),
    dict(id="waiting",    cat="communication", color=TEAL,      em="⏳",        ti="I'm waiting",              sub="Someone is coming",               fw=["TEACCH","AAC"]),
    dict(id="help",       cat="communication", color=TEAL,      em="🤝",        ti="I need help",              sub="Please help me",                  fw=["AAC","PBS"]),
    dict(id="goodtrying", cat="communication", color=TEAL,      em="👍",        ti="Good trying!",             sub="That was hard. You tried.",       fw=["PBS","BSEM"]),
    dict(id="talktome",   cat="communication", color=TEAL,      em="🗣️",       ti="I want to talk",           sub="I have something to say",         fw=["AAC","BSEM"]),
    dict(id="question",   cat="communication", color=TEAL,      em="❓",        ti="I have a question",        sub="Please listen to me",             fw=["AAC","EALD"]),
    dict(id="play",       cat="communication", color=TEAL,      em="🎮",        ti="Can I play?",              sub="Can I join in?",                  fw=["CG","BSEM"]),
    dict(id="quiet",      cat="communication", color=TEAL,      em="🤫",        ti="Quiet time",               sub="This is a calm space",            fw=["OT","BSEM"]),
    # Routine
    dict(id="firstthencard", cat="routine",   color=GREEN,     em="1️⃣➡️2️⃣",  ti="First then Then",          sub="First work, then reward",         fw=["TEACCH","PBS"]),
    dict(id="nownext",    cat="routine",       color=GREEN,     em="▶️⏭️",      ti="Now then Next",            sub="Here's what's coming next",       fw=["TEACCH","PBS"]),
    dict(id="finished",   cat="routine",       color=GREEN,     em="✅",        ti="Finished!",                sub="I am done with this task",        fw=["TEACCH","PBS"]),
    dict(id="transition", cat="routine",       color=GREEN,     em="🔔",        ti="Time to change",           sub="We are finishing soon",           fw=["TEACCH","TI"]),
    dict(id="fivemins",   cat="routine",       color=GREEN,     em="⏱️",       ti="5 more minutes",           sub="Almost time to stop",             fw=["TEACCH","PBS"]),
    dict(id="packup",     cat="routine",       color=GREEN,     em="📦",        ti="Pack up time",             sub="Lets pack away",                  fw=["TEACCH","PBS"]),
    dict(id="steps",      cat="routine",       color=GREEN,     em="1️⃣2️⃣3️⃣", ti="Task steps 1-2-3",        sub="Step by step",                    fw=["TEACCH","UDL"]),
    # Attention
    dict(id="choice",     cat="attention",     color="#C97B1A", em="🤔",        ti="My choices",               sub="Choose one",                      fw=["UDL","PBS"]),
    dict(id="tokens",     cat="attention",     color="#C97B1A", em="⭐⭐⭐",   ti="Token board",              sub="Earn your reward",                fw=["PBS","BSEM"]),
    dict(id="listen",     cat="attention",     color="#C97B1A", em="👂",        ti="Listening body",           sub="Eyes / Ears / Still body",        fw=["BSEM","PBS"]),
    dict(id="seat",       cat="attention",     color="#C97B1A", em="💺",        ti="Stay in your seat",        sub="Stay here to learn",              fw=["PBS","TEACCH"]),
    dict(id="hands",      cat="attention",     color="#C97B1A", em="🙌",        ti="Safe hands",               sub="Hands to yourself",               fw=["BSEM","TI","PBS"]),
    dict(id="sensory",    cat="attention",     color="#C97B1A", em="🎯",        ti="My sensory tools",         sub="Fidget / Squeeze / Stretch",      fw=["OT","BSEM"]),
    dict(id="bubble",     cat="attention",     color="#C97B1A", em="🫧",        ti="Body bubble",              sub="My space / Your space",           fw=["BSEM","CG"]),
    # Places
    dict(id="myspace",    cat="places",        color="#5A3B8C", em="🏷️",       ti="My learning space",        sub="This is my place",                fw=["TEACCH","ABLES"]),
    dict(id="playground", cat="places",        color="#5A3B8C", em="🛝",       ti="Playground",               sub="Outside play time",               fw=["TEACCH"]),
    dict(id="classroom",  cat="places",        color="#5A3B8C", em="🏫",       ti="Classroom",                sub="Learning room",                   fw=["TEACCH"]),
    dict(id="kitchen",    cat="places",        color="#5A3B8C", em="🍽️",      ti="Kitchen / dining",         sub="Food and eating area",            fw=["TEACCH"]),
    dict(id="toilet",     cat="places",        color="#5A3B8C", em="🚽",       ti="Toilet",                   sub="Bathroom break",                  fw=["TEACCH"]),
    dict(id="outside",    cat="places",        color="#5A3B8C", em="🌳",       ti="Outside / Yard",           sub="Outdoor learning space",          fw=["TEACCH"]),
]

ACTIVITIES = [
    dict(cat="school",  em="✏️",  lb="Writing"),
    dict(cat="school",  em="📚",  lb="Reading"),
    dict(cat="school",  em="🔢",  lb="Maths"),
    dict(cat="school",  em="🎨",  lb="Art"),
    dict(cat="school",  em="🎵",  lb="Music"),
    dict(cat="school",  em="🖥️", lb="iPad / ICT"),
    dict(cat="school",  em="🏃",  lb="P.E."),
    dict(cat="school",  em="🔬",  lb="Science"),
    dict(cat="routine", em="🍎",  lb="Lunch"),
    dict(cat="routine", em="🥐",  lb="Morning snack"),
    dict(cat="routine", em="🎒",  lb="Bag time"),
    dict(cat="routine", em="🚌",  lb="Bus"),
    dict(cat="routine", em="🧘",  lb="Calm break"),
    dict(cat="routine", em="📦",  lb="Pack up"),
    dict(cat="routine", em="🚶",  lb="Move to next"),
    dict(cat="social",  em="🎮",  lb="Free play"),
    dict(cat="social",  em="🧩",  lb="Puzzle / game"),
    dict(cat="social",  em="👥",  lb="Group work"),
    dict(cat="social",  em="💬",  lb="Chat time"),
    dict(cat="social",  em="🎲",  lb="Board game"),
    dict(cat="reward",  em="⭐",  lb="Star reward"),
    dict(cat="reward",  em="🎉",  lb="Celebration"),
    dict(cat="reward",  em="📺",  lb="Video time"),
    dict(cat="reward",  em="🍫",  lb="Treat"),
    dict(cat="reward",  em="🎧",  lb="Music time"),
    dict(cat="reward",  em="🎨",  lb="Free draw"),
    dict(cat="places",  em="🏫",  lb="Classroom"),
    dict(cat="places",  em="🛝",  lb="Playground"),
    dict(cat="places",  em="🍽️", lb="Kitchen"),
    dict(cat="places",  em="🚽",  lb="Toilet"),
    dict(cat="places",  em="🌳",  lb="Outside"),
    dict(cat="places",  em="📚",  lb="Library"),
]

FW_DETAILS = {
    "BSEM":  dict(label="BSEM",           color=TEAL,      bg=TEAL_B),
    "TI":    dict(label="Trauma-Informed", color="#5A3B8C", bg="#F2EEF8"),
    "TEACCH":dict(label="TEACCH",          color=GREEN,     bg=GRN_B),
    "PBS":   dict(label="PBS",             color="#C97B1A", bg=AMB_B),
    "OT":    dict(label="OT/Sensory",      color="#1A4D8C", bg="#EBF2FC"),
    "AAC":   dict(label="AAC/PECS",        color="#8C2D5A", bg="#F8EDF3"),
    "ZOR":   dict(label="Zones of Reg",    color="#1E6F75", bg="#E8F5F6"),
    "PODD":  dict(label="PODD",            color="#7B3B8C", bg="#F4EEF8"),
    "CG":    dict(label="Social Stories",  color="#3730A3", bg="#EEEEF9"),
    "EALD":  dict(label="EAL/D",           color="#2D5A8C", bg="#EBF2FC"),
    "UDL":   dict(label="UDL",             color="#B83232", bg="#FDF0EF"),
    "ABLES": dict(label="ABLES",           color=TEAL,      bg=TEAL_B),
}

COMM_PRESETS = {
    "Feelings":    [("😊","Happy"),("😢","Sad"),("😠","Angry"),("😰","Worried"),("😴","Tired"),("😐","Okay"),("🤢","Sick"),("🤩","Excited"),("😮","Surprised"),("🥱","Bored"),("😤","Frustrated"),("🥰","Loved")],
    "Food & Drink":[("🍎","Apple"),("🥪","Sandwich"),("🍌","Banana"),("💧","Water"),("🥛","Milk"),("🥕","Carrot"),("🍞","Bread"),("🍫","Chocolate"),("🥜","Nuts"),("🍊","Orange"),("🧃","Juice"),("🍇","Grapes")],
    "Places":      [("🏫","School"),("🏠","Home"),("🛝","Playground"),("🍽️","Kitchen"),("🚽","Toilet"),("📚","Library"),("🏋️","Gym"),("🌳","Outside")],
    "Activities":  [("🎨","Art"),("✏️","Writing"),("📚","Reading"),("🎮","Play"),("🎵","Music"),("🏃","Exercise"),("🧩","Puzzle"),("🖥️","Computer")],
    "Requests":    [("🙋","Help me"),("💧","Water"),("🚽","Toilet"),("⏸️","Break"),("❓","Question"),("👍","Yes"),("👎","No"),("🔄","Again"),("✅","Done"),("😊","OK"),("😢","Not OK"),("⏳","Wait")],
    "People":      [("👩‍🏫","Teacher"),("👦","Me"),("👥","Friends"),("👩","Mum"),("👨","Dad"),("👴","Grandpa"),("👵","Grandma"),("🧑‍⚕️","Doctor")],
    "Core words":  [("✅","Yes"),("❌","No"),("🙋","Want"),("🛑","Stop"),("➕","More"),("✅","Done"),("🤝","Help"),("🔄","Go"),("❤️","Like"),("💔","Don't like"),("👀","Look"),("👂","Listen")],
}

CALM_STRATS = [
    ("🌬️","Deep breaths"),("🧘","Mindful pause"),("🚶","Walk it out"),("💦","Cold water"),
    ("🎧","Music"),("🤲","Squeeze ball"),("🏃","Jump / move"),("🎨","Draw / colour"),
    ("📖","Quiet reading"),("🌟","Think happy"),("🫂","Ask for hug"),("🏋️","Heavy work"),
    ("🧩","Fidget toy"),("💺","Sit quietly"),("🌳","Go outside"),("🐾","Animal breathing"),
    ("🫶","Self-hug"),("⏱️","Count to 10"),
]

ZONE_DATA = {
    "blue":   dict(name="Blue Zone - Low/Slow",       color="#1D4ED8", bg="#DBEAFE", feels=["Tired","Sad","Bored","Sick","Moving slowly"],          strats=["Do some movement","Splash cold water on face","Listen to upbeat music","Have a snack","Do jumping jacks"]),
    "green":  dict(name="Green Zone - Ready to Learn", color="#15803D", bg="#DCFCE7", feels=["Happy","Calm","Focused","Ready","Content"],             strats=["Keep going!","Use your tools if needed","Check in with teacher","You're in the best zone"]),
    "yellow": dict(name="Yellow Zone - Wobbly/Busy",   color="#B45309", bg="#FEF9C3", feels=["Worried","Frustrated","Silly","Excited","Overwhelmed"],  strats=["Take 3 deep breaths","Squeeze a fidget tool","Ask for a movement break","Get a drink of water"]),
    "red":    dict(name="Red Zone - Out of Control",   color="#B91C1C", bg="#FEE2E2", feels=["Furious","Terrified","Panicking","Explosive"],           strats=["Move to your safe space","Take slow breaths","Use your sensory tool","Ask for help"]),
}

SCRIPT_SITUS = [
    dict(em="🏫", ti="Arriving at school",     steps=["I come to school in the morning","I put my bag away","I say hello to my teacher","I find my seat","I am ready to learn"]),
    dict(em="🙋", ti="Asking for help",         steps=["I notice I need help","I raise my hand or use my card","I wait for my teacher","I ask my question","My teacher helps me"]),
    dict(em="🎮", ti="Joining in play",         steps=["I watch what my friends are doing","I say Can I play?","I wait for the answer","If they say yes I join in","I share and take turns"]),
    dict(em="😞", ti="Feeling disappointed",    steps=["Sometimes things don't go my way","I might feel upset or sad","That is okay","I take a breath","I can try again later"]),
    dict(em="🍽️",ti="Lunchtime",              steps=["It is time for lunch","I find my lunchbox","I sit in my spot","I eat my food","When I'm done I pack up"]),
    dict(em="🔔", ti="Moving to next activity", steps=["I hear the signal for change","I finish what I am doing","I pack up my things","I move to the next activity","I am ready to start"]),
    dict(em="😠", ti="When I feel angry",       steps=["I notice my body feels hot or tight","I am in the red zone","I stop and breathe","I use a strategy from my toolkit","I feel better when I'm calm"]),
    dict(em="🤝", ti="Making an apology",       steps=["I did something that hurt someone","I notice how they feel","I say I'm sorry","I listen to their answer","We both feel better"]),
]

FIVE_COLORS = ["#DBEAFE","#DCFCE7","#FEF9C3","#FED7AA","#FEE2E2"]
FIVE_EMOJIS = ["😌","😊","😬","😤","🤯"]

# =============================================================================
# SESSION STATE
# =============================================================================
def ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

ss("vst_tab", "Cards")
ss("vst_selected_cards", [])
ss("vst_custom_cards", [])
ss("vst_ft_slots", [None, None, None])
ss("vst_sched_slots", [])
ss("vst_grid_size", "2x2")
ss("vst_board_cells", [{"em":"","tx":""} for _ in range(4)])
ss("vst_zone_custom", {"blue":[],"green":[],"yellow":[],"red":[]})
ss("vst_five_labels", ["Calm & Still","Happy & Ready","A bit wobbly","Really upset","Cannot stop"])
ss("vst_calm_selected", [])
ss("vst_script_steps", [])
ss("vst_print_queue", [])
ss("vst_print_format", "A4 Lanyard cards")

# =============================================================================
# HELPERS
# =============================================================================
def fw_badge(key):
    f = FW_DETAILS.get(key, {})
    if not f:
        return ""
    return f'<span class="fw" style="background:{f["bg"]};color:{f["color"]}">{f["label"]}</span>'

def cat_color(cat):
    return {"regulation": AMBER, "communication": TEAL,
            "routine": GREEN, "attention": "#C97B1A", "places": "#5A3B8C"}.get(cat, TEAL)

def add_to_queue(item):
    st.session_state.vst_print_queue.append(item)

def queue_count():
    return len(st.session_state.vst_print_queue)

# =============================================================================
# HEADER
# =============================================================================
st.markdown(f"""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools</h1>
        <p>Create, customise and print visual supports - lanyard cards, desk mats, First-Then boards, schedules, communication boards and more</p>
    </div>
    <div style="margin-left:auto;background:rgba(255,255,255,.15);border-radius:20px;padding:.35rem .9rem;font-size:.82rem;font-weight:700">
        🖨️ Queue: {queue_count()}
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# TAB NAVIGATION
# =============================================================================
TABS = ["Cards", "First-Then", "Schedule", "Comm Board", "Regulation", "Social Scripts", "Print Queue"]
TAB_ICONS = ["🃏","🔄","📅","💬","🧘","📖","🖨️"]

tab_cols = st.columns(len(TABS))
for i, (col, label, icon) in enumerate(zip(tab_cols, TABS, TAB_ICONS)):
    with col:
        is_active = st.session_state.vst_tab == label
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon} {label}", key=f"tab_{i}", use_container_width=True, type=btn_type):
            st.session_state.vst_tab = label
            st.rerun()

st.markdown("<hr style='margin:.5rem 0 1.25rem;border-color:#e2e8f0'>", unsafe_allow_html=True)
active = st.session_state.vst_tab

# =============================================================================
# TAB 1 - CARD BUILDER
# =============================================================================
if active == "Cards":
    st.markdown("""
    <div class="section-card">
      <h3>🃏 Lanyard and Desk Card Builder</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Select cards to add to your print queue. Filter by category or search. Add custom cards with your own text and emoji.</p>
    </div>
    """, unsafe_allow_html=True)

    col_cat, col_search = st.columns([2, 1])
    with col_cat:
        cat_filter = st.selectbox("Category", ["All","Regulation","Communication","Routine","Attention","Places"], label_visibility="collapsed")
    with col_search:
        search = st.text_input("Search", placeholder="Search cards...", label_visibility="collapsed")

    all_cards = CARDS + st.session_state.vst_custom_cards
    filtered = all_cards
    if cat_filter != "All":
        filtered = [c for c in filtered if c["cat"].lower() == cat_filter.lower()]
    if search:
        filtered = [c for c in filtered if search.lower() in c["ti"].lower() or search.lower() in c["sub"].lower()]

    selected_ids = set(st.session_state.vst_selected_cards)
    cols_per_row = 4
    rows = [filtered[i:i+cols_per_row] for i in range(0, len(filtered), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for col, card in zip(cols, row):
            with col:
                is_sel = card["id"] in selected_ids
                border = TEAL if is_sel else "#dde6ee"
                bg = TEAL_B if is_sel else "#fff"
                check = "✅ " if is_sel else ""
                fws = "".join(fw_badge(f) for f in card.get("fw", []))
                st.markdown(f"""
                <div class="vc" style="border-color:{border};background:{bg};border-top:3px solid {card['color']}">
                    <div class="em">{card['em']}</div>
                    <div class="ti">{check}{card['ti']}</div>
                    <div class="su">{card['sub']}</div>
                    <div style="margin-top:.3rem">{fws}</div>
                </div>
                """, unsafe_allow_html=True)
                btn_label = "Deselect" if is_sel else "Select"
                if st.button(btn_label, key=f"sel_{card['id']}", use_container_width=True):
                    if is_sel:
                        st.session_state.vst_selected_cards.remove(card["id"])
                    else:
                        st.session_state.vst_selected_cards.append(card["id"])
                    st.rerun()

    st.markdown("---")
    ca, cb, cc = st.columns([2, 2, 3])
    with ca:
        st.write(f"**{len(selected_ids)} card(s) selected**")
    with cb:
        if st.button("Clear selection"):
            st.session_state.vst_selected_cards = []
            st.rerun()
    with cc:
        if st.button("🖨️ Add selected to print queue", type="primary", use_container_width=True):
            if not selected_ids:
                st.warning("Select at least one card first.")
            else:
                sel = [c for c in all_cards if c["id"] in selected_ids]
                add_to_queue({"type":"cards","label":f"{len(sel)} lanyard card(s)","icon":"🃏","data":sel})
                st.success(f"Added {len(sel)} card(s) to print queue!")
                st.rerun()

    with st.expander("➕ Add custom card"):
        cc1, cc2 = st.columns(2)
        with cc1:
            cc_em = st.text_input("Emoji", placeholder="e.g. 🚿", key="cc_em")
            cc_ti = st.text_input("Card title", placeholder="e.g. Shower time", key="cc_ti")
        with cc2:
            cc_sub = st.text_input("Subtitle", placeholder="e.g. Wash hair and body", key="cc_sub")
            cc_cat = st.selectbox("Category", ["Regulation","Communication","Routine","Attention","Places"], key="cc_cat")
        if st.button("Add custom card", type="primary"):
            if cc_em and cc_ti:
                new_id = f"custom_{datetime.utcnow().timestamp()}"
                st.session_state.vst_custom_cards.append(dict(
                    id=new_id, cat=cc_cat.lower(), color=cat_color(cc_cat.lower()),
                    em=cc_em, ti=cc_ti, sub=cc_sub or "", fw=[]
                ))
                st.success("Custom card added!")
                st.rerun()
            else:
                st.warning("Emoji and title are required.")

    st.markdown("""<div class="research-note">
    📚 <strong>Research base:</strong> Visual support cards draw on AAC core vocabulary principles (Beukelman & Mirenda), TEACCH structured teaching, BSEM body-brain connection, and UDL multiple means of representation (CAST, 2018). Framework badges on each card indicate the supporting evidence base.
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 2 - FIRST-THEN / NOW-NEXT
# =============================================================================
elif active == "First-Then":
    st.markdown("""
    <div class="section-card">
      <h3>🔄 First-Then / Now-Next Boards</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Build visual sequence boards. Choose activities from the library or enter custom ones.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        ft_student = st.text_input("Student name (optional)", placeholder="e.g. Alex", key="ft_student")
    with c2:
        ft_title = st.text_input("Board title (optional)", placeholder="e.g. Morning routine", key="ft_title")

    ft_type = st.radio("Board type", ["First-Then (2 panels)","Now-Next-Then (3 panels)"], horizontal=True)
    is_three = "3" in ft_type
    panels = 3 if is_three else 2
    labels = ["NOW","NEXT","THEN"] if is_three else ["FIRST","THEN"]
    slots = st.session_state.vst_ft_slots

    # Preview
    st.markdown("#### Board preview")
    board_cols = st.columns(panels)
    for i in range(panels):
        with board_cols[i]:
            slot = slots[i]
            if slot:
                st.markdown(f"""
                <div class="slot filled">
                    <div class="slot-lbl">{labels[i]}</div>
                    <div class="slot-em">{slot['em']}</div>
                    <div class="slot-tx">{slot['lb']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Clear {labels[i]}", key=f"clr_{i}"):
                    st.session_state.vst_ft_slots[i] = None
                    st.rerun()
            else:
                st.markdown(f"""
                <div class="slot">
                    <div class="slot-lbl">{labels[i]}</div>
                    <div class="slot-em">➕</div>
                    <div style="font-size:.82rem;color:#718096">Choose activity below</div>
                </div>
                """, unsafe_allow_html=True)

    # Activity picker
    st.markdown("#### Choose activities")
    act_cat = st.selectbox("Filter", ["All","School","Routine","Social","Reward","Places"], key="act_cat_sel", label_visibility="collapsed")
    act_pool = ACTIVITIES if act_cat == "All" else [a for a in ACTIVITIES if a["cat"].lower() == act_cat.lower()]

    act_cols_per_row = 8
    act_rows = [act_pool[i:i+act_cols_per_row] for i in range(0, len(act_pool), act_cols_per_row)]
    for act_row in act_rows:
        acols = st.columns(act_cols_per_row)
        for j, act in enumerate(act_row):
            with acols[j]:
                st.markdown(f"<div style='text-align:center;font-size:1.2rem'>{act['em']}</div><div style='font-size:.62rem;text-align:center;font-weight:600;color:#4a5568'>{act['lb']}</div>", unsafe_allow_html=True)
                slot_choice = st.selectbox("Slot", ["--"] + labels[:panels], key=f"act_s_{act['id']}_{j}", label_visibility="collapsed")
                if slot_choice != "--":
                    idx = labels.index(slot_choice)
                    st.session_state.vst_ft_slots[idx] = act
                    st.rerun()

    with st.expander("Custom activity"):
        ca1, ca2, ca3 = st.columns([1,2,2])
        with ca1:
            cust_em = st.text_input("Emoji", value="📌", key="cust_em")
        with ca2:
            cust_lb = st.text_input("Name", key="cust_lb")
        with ca3:
            cust_slot = st.selectbox("Slot", labels[:panels], key="cust_slot")
        if st.button("Add"):
            if cust_lb.strip():
                idx = labels.index(cust_slot)
                st.session_state.vst_ft_slots[idx] = {"em": cust_em, "lb": cust_lb, "cat":"custom", "id":"cust"}
                st.rerun()

    if st.button("🖨️ Add board to print queue", type="primary"):
        filled = [s for s in slots[:panels] if s]
        if not filled:
            st.warning("Fill at least one slot.")
        else:
            add_to_queue({"type":"firstthen","label":ft_type.split(" (")[0],"icon":"🔄",
                          "data":{"type":ft_type,"slots":list(slots[:panels]),"labels":labels,"student":ft_student,"title":ft_title}})
            st.success("Board added to print queue!")
            st.rerun()

    st.markdown("""<div class="research-note">
    📚 <strong>TEACCH Structured Teaching</strong> (Mesibov, Shea & Schopler): First-Then and Now-Next boards provide visual predictability that reduces transition anxiety and task avoidance. Consistently supported by PBS research for students with ASD and ID.
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 3 - VISUAL SCHEDULE
# =============================================================================
elif active == "Schedule":
    st.markdown("""
    <div class="section-card">
      <h3>📅 Visual Schedule Builder</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Build daily, half-day or strip schedules. Add, reorder and remove time slots.</p>
    </div>
    """, unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    with sc1:
        sched_title = st.text_input("Schedule title", placeholder="e.g. Monday Schedule", key="sched_title_in")
    with sc2:
        sched_student = st.text_input("Student name (optional)", placeholder="e.g. Abdulaziz", key="sched_student_in")

    sched_type = st.radio("Type", ["Full day","Morning only","Afternoon only","Now-Next-Later strip"], horizontal=True)

    st.markdown("#### Schedule slots")
    if st.session_state.vst_sched_slots:
        to_delete = None
        to_swap = None
        for i, slot in enumerate(st.session_state.vst_sched_slots):
            sc, se, sa, sm, sd = st.columns([1.2, 0.6, 3.5, 0.8, 0.4])
            with sc:
                new_time = st.text_input("Time", value=slot.get("time",""), key=f"slt_{i}", label_visibility="collapsed", placeholder="9:00am")
                st.session_state.vst_sched_slots[i]["time"] = new_time
            with se:
                new_em = st.text_input("Em", value=slot.get("em","📌"), key=f"slem_{i}", label_visibility="collapsed")
                st.session_state.vst_sched_slots[i]["em"] = new_em
            with sa:
                new_act = st.text_input("Activity", value=slot.get("act",""), key=f"slac_{i}", label_visibility="collapsed", placeholder="Activity name")
                st.session_state.vst_sched_slots[i]["act"] = new_act
            with sm:
                mc1, mc2 = st.columns(2)
                with mc1:
                    if st.button("▲", key=f"sup_{i}") and i > 0:
                        to_swap = (i, i-1)
                with mc2:
                    if st.button("▼", key=f"sdn_{i}") and i < len(st.session_state.vst_sched_slots)-1:
                        to_swap = (i, i+1)
            with sd:
                if st.button("✕", key=f"sdel_{i}"):
                    to_delete = i
        if to_swap:
            a, b = to_swap
            st.session_state.vst_sched_slots[a], st.session_state.vst_sched_slots[b] = st.session_state.vst_sched_slots[b], st.session_state.vst_sched_slots[a]
            st.rerun()
        if to_delete is not None:
            st.session_state.vst_sched_slots.pop(to_delete)
            st.rerun()
    else:
        st.info("No slots yet. Click '+ Add slot' below.")

    col_add, col_q = st.columns([1, 2])
    with col_add:
        if st.button("+ Add time slot", use_container_width=True):
            st.session_state.vst_sched_slots.append({"time":"","em":"📌","act":""})
            st.rerun()
    with col_q:
        if st.button("🖨️ Add schedule to print queue", type="primary", use_container_width=True):
            if not st.session_state.vst_sched_slots:
                st.warning("Add at least one slot.")
            else:
                add_to_queue({"type":"schedule","label":sched_title or "Visual Schedule","icon":"📅",
                              "data":{"title":sched_title,"student":sched_student,"type":sched_type,
                                      "slots":list(st.session_state.vst_sched_slots)}})
                st.success("Schedule added to print queue!")
                st.rerun()

    st.markdown("""<div class="research-note">
    📚 <strong>TEACCH temporal organisation:</strong> Visual schedules reduce anxiety around unpredictability, support executive function, and build independence in transitioning. Particularly effective for students with ASD, ID, ADHD and complex trauma backgrounds (BSEM predictability principle).
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 4 - COMMUNICATION BOARD
# =============================================================================
elif active == "Comm Board":
    st.markdown("""
    <div class="section-card">
      <h3>💬 Communication Choice Board</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">AAC-informed choice boards using core vocabulary principles, PODD framework and UDL multiple means of expression.</p>
    </div>
    """, unsafe_allow_html=True)

    cb1, cb2 = st.columns(2)
    with cb1:
        board_title = st.text_input("Board title", placeholder="e.g. I want...  /  How am I feeling?", key="board_title_in")
    with cb2:
        board_student = st.text_input("Student name (optional)", placeholder="e.g. Priya", key="board_student_in")

    grid_size = st.radio("Grid size", ["2x2","2x3","3x3","3x4","4x4"], horizontal=True, key="grid_sz")
    if grid_size != st.session_state.vst_grid_size:
        cols_n, rows_n = [int(x) for x in grid_size.split("x")]
        total = cols_n * rows_n
        cur = st.session_state.vst_board_cells
        while len(cur) < total:
            cur.append({"em":"","tx":""})
        st.session_state.vst_board_cells = cur[:total]
        st.session_state.vst_grid_size = grid_size
        st.rerun()

    preset_choice = st.selectbox("Load preset", ["-- choose --"] + list(COMM_PRESETS.keys()), key="preset_sel")
    if preset_choice != "-- choose --":
        if st.button(f"Load '{preset_choice}'"):
            cols_n, rows_n = [int(x) for x in st.session_state.vst_grid_size.split("x")]
            total = cols_n * rows_n
            items = COMM_PRESETS[preset_choice][:total]
            cells = [{"em":em,"tx":tx} for em, tx in items]
            while len(cells) < total:
                cells.append({"em":"","tx":""})
            st.session_state.vst_board_cells = cells
            st.rerun()

    st.markdown("#### Edit cells")
    cols_n, rows_n = [int(x) for x in st.session_state.vst_grid_size.split("x")]
    cell_idx = 0
    for row in range(rows_n):
        row_cols = st.columns(cols_n)
        for col_i in range(cols_n):
            if cell_idx < len(st.session_state.vst_board_cells):
                cell = st.session_state.vst_board_cells[cell_idx]
                with row_cols[col_i]:
                    new_em = st.text_input("Emoji", value=cell["em"], key=f"ce_{cell_idx}", label_visibility="collapsed", placeholder="😊")
                    new_tx = st.text_input("Word",  value=cell["tx"], key=f"ct_{cell_idx}", label_visibility="collapsed", placeholder="Label")
                    st.session_state.vst_board_cells[cell_idx] = {"em":new_em,"tx":new_tx}
            cell_idx += 1

    if st.button("🖨️ Add board to print queue", type="primary"):
        filled = [c for c in st.session_state.vst_board_cells if c["em"] or c["tx"]]
        if not filled:
            st.warning("Fill in some cells first.")
        else:
            add_to_queue({"type":"board","label":board_title or "Communication Board","icon":"💬",
                          "data":{"title":board_title,"student":board_student,
                                  "gridSize":st.session_state.vst_grid_size,
                                  "cells":list(st.session_state.vst_board_cells)}})
            st.success("Board added to print queue!")
            st.rerun()

    st.markdown("""<div class="research-note">
    📚 <strong>AAC/Core vocabulary</strong> (Beukelman & Mirenda, 2013): Core words account for up to 80% of daily communication. PODD (Gayle Porter, RCH Melbourne) and PECS provide frameworks for symbol-based communication. For EALD learners, symbol + word format reduces English processing demands.
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 5 - REGULATION TOOLS
# =============================================================================
elif active == "Regulation":
    st.markdown("""
    <div class="section-card">
      <h3>🧘 Regulation and Wellbeing Tools</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Zones of Regulation, 5-Point Scale, Calm-Down menus and Feelings Check-In. Grounded in BSEM, Trauma-Informed and OT/Sensory frameworks.</p>
    </div>
    """, unsafe_allow_html=True)

    reg_type = st.radio("Tool type", ["Zones of Regulation","5-Point Scale","Calm-Down Menu","Feelings Check-In"], horizontal=True)

    # ZONES
    if reg_type == "Zones of Regulation":
        st.markdown("#### Customise strategies per zone")
        zone_cols = st.columns(2)
        for i, (z, zd) in enumerate(ZONE_DATA.items()):
            with zone_cols[i % 2]:
                st.markdown(f"""
                <div class="zone zone-{z}">
                    <h4>{zd['name']}</h4>
                    <div class="feels">{' / '.join(zd['feels'])}</div>
                    <div style="margin-top:.35rem;font-size:.75rem"><strong>Default strategies:</strong> {', '.join(zd['strats'][:3])}</div>
                </div>
                """, unsafe_allow_html=True)
                custom_in = st.text_input(f"Add student strategy for {z}", key=f"zin_{z}", label_visibility="collapsed", placeholder=f"Add a strategy for {z} zone...")
                if st.button(f"Add to {z.capitalize()}", key=f"zbtn_{z}"):
                    if custom_in.strip():
                        st.session_state.vst_zone_custom[z].append(custom_in.strip())
                        st.rerun()
                if st.session_state.vst_zone_custom[z]:
                    st.caption("Added: " + " / ".join(st.session_state.vst_zone_custom[z]))

        if st.button("🖨️ Add Zones chart to print queue", type="primary"):
            add_to_queue({"type":"regulation","label":"Zones of Regulation","icon":"🟢",
                          "data":{"tool":"zones","custom":dict(st.session_state.vst_zone_custom)}})
            st.success("Added to print queue!")
            st.rerun()

    # 5-POINT SCALE
    elif reg_type == "5-Point Scale":
        fps_student = st.text_input("Student name", placeholder="e.g. Jordan", key="fps_s")
        st.markdown("#### Edit scale labels")
        scale_cols = st.columns(5)
        new_labels = []
        for i in range(5):
            with scale_cols[i]:
                st.markdown(f"""
                <div style="background:{FIVE_COLORS[i]};border-radius:8px;padding:.6rem .4rem;text-align:center;margin-bottom:.4rem">
                    <div style="font-size:1.4rem">{FIVE_EMOJIS[i]}</div>
                    <div style="font-size:1rem;font-weight:900">{i+1}</div>
                </div>
                """, unsafe_allow_html=True)
                lbl = st.text_input(f"L{i+1}", value=st.session_state.vst_five_labels[i], key=f"fp5_{i}", label_visibility="collapsed")
                new_labels.append(lbl)
        st.session_state.vst_five_labels = new_labels

        if st.button("🖨️ Add 5-Point Scale to print queue", type="primary"):
            add_to_queue({"type":"regulation","label":"5-Point Scale","icon":"5️⃣",
                          "data":{"tool":"fivepoint","student":fps_student,"labels":list(new_labels)}})
            st.success("Added to print queue!")
            st.rerun()

    # CALM-DOWN MENU
    elif reg_type == "Calm-Down Menu":
        cd1, cd2 = st.columns(2)
        with cd1:
            cd_student = st.text_input("Student name", placeholder="e.g. Mia", key="cd_s")
        with cd2:
            cd_title = st.text_input("Card title", value="My calm-down toolkit", key="cd_t")

        st.markdown("#### Select strategies to include")
        selected_strats = list(st.session_state.vst_calm_selected)
        strat_cols = st.columns(6)
        for j, (em, lb) in enumerate(CALM_STRATS):
            with strat_cols[j % 6]:
                is_on = j in selected_strats
                bg = TEAL if is_on else "#f8fafc"
                col_txt = "#fff" if is_on else NAVY
                border = TEAL if is_on else "#dde6ee"
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {border};border-radius:8px;padding:.5rem .3rem;text-align:center;margin-bottom:.3rem">
                    <div style="font-size:1.3rem">{em}</div>
                    <div style="font-size:.65rem;font-weight:700;color:{col_txt}">{lb}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Remove" if is_on else "Add", key=f"strat_{j}", use_container_width=True):
                    if is_on:
                        selected_strats.remove(j)
                    else:
                        selected_strats.append(j)
                    st.session_state.vst_calm_selected = selected_strats
                    st.rerun()

        if st.button("🖨️ Add Calm-Down Menu to print queue", type="primary"):
            chosen = [{"em":CALM_STRATS[i][0],"lb":CALM_STRATS[i][1]} for i in selected_strats]
            if not chosen:
                st.warning("Select at least one strategy.")
            else:
                add_to_queue({"type":"regulation","label":cd_title or "Calm-Down Menu","icon":"🌬️",
                              "data":{"tool":"calmdown","student":cd_student,"title":cd_title,"strats":chosen}})
                st.success("Added to print queue!")
                st.rerun()

    # FEELINGS CHECK-IN
    elif reg_type == "Feelings Check-In":
        fc1, fc2 = st.columns(2)
        with fc1:
            fc_student = st.text_input("Student name", placeholder="e.g. Sam", key="fc_s")
        with fc2:
            fc_style = st.selectbox("Style", ["Simple faces","Words + faces","Zones colours"], key="fc_sty")

        feels_map = {
            "Simple faces":  [("😊","Happy"),("😐","Okay"),("😢","Sad"),("😠","Angry"),("😰","Worried"),("😴","Tired")],
            "Words + faces": [("😊","Happy"),("😐","Okay"),("😢","Sad"),("😠","Angry"),("😰","Worried"),("😴","Tired"),("🤩","Excited"),("😮","Surprised")],
            "Zones colours": [("🔵","Blue Zone"),("🟢","Green Zone"),("🟡","Yellow Zone"),("🔴","Red Zone")],
        }
        preview = feels_map[fc_style]
        f_cols = st.columns(len(preview))
        for k, (em, tx) in enumerate(preview):
            with f_cols[k]:
                st.markdown(f"""
                <div style="background:#fff;border:2px solid #dde6ee;border-radius:8px;padding:.75rem .3rem;text-align:center">
                    <div style="font-size:1.8rem">{em}</div>
                    <div style="font-size:.77rem;font-weight:700;margin-top:.3rem">{tx}</div>
                </div>
                """, unsafe_allow_html=True)

        if st.button("🖨️ Add Feelings Check-In to print queue", type="primary"):
            add_to_queue({"type":"regulation","label":"Feelings Check-In","icon":"😊",
                          "data":{"tool":"feelings","student":fc_student,"style":fc_style,"feels":preview}})
            st.success("Added to print queue!")
            st.rerun()

    st.markdown("""<div class="research-note">
    📚 <strong>Zones of Regulation</strong> (Kuypers, 2011) - aligns with BSEM body-brain connection and Polyvagal Theory (Porges). <strong>5-Point Scale</strong> (Buron & Curtis, 2003) - concrete anchors for abstract emotional states. <strong>Sensory strategies</strong> draw on Ayres Sensory Integration and Winnie Dunn's Sensory Profile.
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 6 - SOCIAL SCRIPTS
# =============================================================================
elif active == "Social Scripts":
    st.markdown("""
    <div class="section-card">
      <h3>📖 Social Scripts and Situation Guides</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Step-by-step visual guides for navigating social situations. Based on Carol Gray Social Stories framework.</p>
    </div>
    """, unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    with sc1:
        ss_student = st.text_input("Student name", placeholder="e.g. Nico", key="ss_s")
    with sc2:
        ss_title = st.text_input("Script title", placeholder="e.g. What happens at lunch", key="ss_t")

    st.markdown("#### Choose a situation template")
    situ_cols = st.columns(4)
    for k, situ in enumerate(SCRIPT_SITUS):
        with situ_cols[k % 4]:
            if st.button(f"{situ['em']} {situ['ti']}", key=f"situ_{k}", use_container_width=True):
                st.session_state.vst_script_steps = [{"em":"📌","tx":s} for s in situ["steps"]]
                st.rerun()

    st.markdown("#### Script steps")
    if st.session_state.vst_script_steps:
        to_del = None
        to_swap = None
        new_steps = []
        for i, step in enumerate(st.session_state.vst_script_steps):
            s1, s2, s3, s4, s5 = st.columns([0.4, 0.5, 4.5, 0.8, 0.4])
            with s1:
                st.markdown(f"<div style='width:24px;height:24px;border-radius:50%;background:{TEAL};color:#fff;font-size:.75rem;font-weight:800;display:flex;align-items:center;justify-content:center;margin-top:.5rem'>{i+1}</div>", unsafe_allow_html=True)
            with s2:
                new_em = st.text_input("Em", value=step["em"], key=f"sem_{i}", label_visibility="collapsed")
            with s3:
                new_tx = st.text_input("Step", value=step["tx"], key=f"stx_{i}", label_visibility="collapsed")
            with s4:
                mc1, mc2 = st.columns(2)
                with mc1:
                    if st.button("▲", key=f"su_{i}") and i > 0:
                        to_swap = (i, i-1)
                with mc2:
                    if st.button("▼", key=f"sd_{i}") and i < len(st.session_state.vst_script_steps)-1:
                        to_swap = (i, i+1)
            with s5:
                if st.button("✕", key=f"sdl_{i}"):
                    to_del = i
            new_steps.append({"em":new_em,"tx":new_tx})
        st.session_state.vst_script_steps = new_steps
        if to_swap:
            a, b = to_swap
            st.session_state.vst_script_steps[a], st.session_state.vst_script_steps[b] = st.session_state.vst_script_steps[b], st.session_state.vst_script_steps[a]
            st.rerun()
        if to_del is not None:
            st.session_state.vst_script_steps.pop(to_del)
            st.rerun()
    else:
        st.info("Choose a situation above or click '+ Add step'.")

    ca, cq = st.columns([1, 2])
    with ca:
        if st.button("+ Add step", use_container_width=True):
            st.session_state.vst_script_steps.append({"em":"📌","tx":""})
            st.rerun()
    with cq:
        if st.button("🖨️ Add script to print queue", type="primary", use_container_width=True):
            if not st.session_state.vst_script_steps:
                st.warning("Add steps first.")
            else:
                add_to_queue({"type":"script","label":ss_title or "Social Script","icon":"📖",
                              "data":{"title":ss_title,"student":ss_student,"steps":list(st.session_state.vst_script_steps)}})
                st.success("Script added to print queue!")
                st.rerun()

    st.markdown("""<div class="research-note">
    📚 <strong>Social Stories (Carol Gray, 1991):</strong> Descriptive, perspective, directive and affirmative sentence types. Meta-analysis (Sansosti et al., 2004) supports effectiveness for ASD. For EALD learners, visual step format significantly reduces language processing demands (ACARA EAL/D).
    </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 7 - PRINT QUEUE
# =============================================================================
elif active == "Print Queue":
    st.markdown("""
    <div class="section-card">
      <h3>🖨️ Print Queue</h3>
      <p style="margin:0;font-size:.82rem;color:#718096">Select your print format, review queued items, then download a print-ready HTML file.</p>
    </div>
    """, unsafe_allow_html=True)

    # Format selector
    pf_cols = st.columns(3)
    fmt_opts = ["A4 Lanyard cards","A4 Desk mat","A3 Desk mat"]
    fmt_icons = ["🏷️","📄","📋"]
    fmt_descs = ["Credit card size - laminate & punch","Larger format - laminate for desk","Full A3 - personal space mat"]
    for i, (col, fmt) in enumerate(zip(pf_cols, fmt_opts)):
        with col:
            is_sel = st.session_state.vst_print_format == fmt
            border = TEAL if is_sel else "#dde6ee"
            bg = TEAL_B if is_sel else "#fff"
            st.markdown(f"""
            <div style="background:{bg};border:2px solid {border};border-radius:10px;padding:1rem;text-align:center;margin-bottom:.5rem">
                <div style="font-size:1.8rem;margin-bottom:.3rem">{fmt_icons[i]}</div>
                <div style="font-weight:700;font-size:.87rem">{fmt}</div>
                <div style="font-size:.7rem;color:#718096;margin-top:.2rem">{fmt_descs[i]}</div>
            </div>
            """, unsafe_allow_html=True)
            btn_type = "primary" if is_sel else "secondary"
            if st.button("Selected" if is_sel else "Select", key=f"fmt_{i}", use_container_width=True, type=btn_type):
                st.session_state.vst_print_format = fmt
                st.rerun()

    st.markdown(f"#### Queued items ({queue_count()})")
    if not st.session_state.vst_print_queue:
        st.markdown("""
        <div style="text-align:center;padding:2rem;background:#fff;border:2px dashed #dde6ee;border-radius:12px;color:#718096">
            🗂️<br><br>Nothing in the queue yet.<br>
            Build a card set, schedule, board or script then click <strong>Add to queue</strong>.
        </div>
        """, unsafe_allow_html=True)
    else:
        to_remove = None
        for i, item in enumerate(st.session_state.vst_print_queue):
            qi1, qi2, qi3 = st.columns([0.4, 6, 1.5])
            with qi1:
                st.markdown(f"<div style='font-size:1.3rem'>{item['icon']}</div>", unsafe_allow_html=True)
            with qi2:
                st.markdown(f"**{item['label']}**")
                st.caption(item["type"])
            with qi3:
                if st.button("Remove", key=f"qr_{i}"):
                    to_remove = i
        if to_remove is not None:
            st.session_state.vst_print_queue.pop(to_remove)
            st.rerun()

        st.markdown("---")
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Clear queue", use_container_width=True):
                st.session_state.vst_print_queue = []
                st.rerun()
        with pc2:
            gen_print = st.button("🖨️ Generate print page", type="primary", use_container_width=True)

        if gen_print:
            fmt = st.session_state.vst_print_format
            is_lanyard = "Lanyard" in fmt
            is_a3 = "A3" in fmt
            page_size = "297mm 420mm" if is_a3 else "210mm 297mm"
            card_h = "54mm" if is_lanyard else ("90mm" if is_a3 else "75mm")
            em_sz = "22px" if is_lanyard else "32px"
            ti_sz = "9px" if is_lanyard else "13px"
            su_sz = "7px" if is_lanyard else "10px"
            fw_sz = "5.5px" if is_lanyard else "7px"

            def card_html(c):
                fws = "".join(
                    f'<span style="background:{FW_DETAILS.get(f,{}).get("bg","#eee")};color:{FW_DETAILS.get(f,{}).get("color","#333")};padding:1px 5px;border-radius:10px;font-size:{fw_sz};font-weight:700;margin-right:2px">{FW_DETAILS.get(f,{}).get("label",f)}</span>'
                    for f in c.get("fw",[])
                )
                return f"""<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column;position:relative">
                  <div style="height:5px;background:{c.get('color',TEAL)}"></div>
                  <div style="height:8px;width:8px;border-radius:50%;border:1.5px solid #dde;position:absolute;top:3px;left:50%;transform:translateX(-50%);background:#fff"></div>
                  <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:6px 5px;text-align:center">
                    <div style="font-size:{em_sz};line-height:1;margin-bottom:4px">{c.get('em','📌')}</div>
                    <div style="font-size:{ti_sz};font-weight:800;color:#1a2e44;line-height:1.2">{c.get('ti','')}</div>
                    <div style="font-size:{su_sz};color:#718096;margin-top:2px">{c.get('sub','')}</div>
                    <div style="margin-top:3px">{fws}</div>
                  </div>
                </div>"""

            all_cards_html = []

            for item in st.session_state.vst_print_queue:
                t = item["type"]
                d = item["data"]

                if t == "cards":
                    for c in d:
                        all_cards_html.append(card_html(c))

                elif t == "firstthen":
                    slots_html = ""
                    for si, (lbl, slot) in enumerate(zip(d["labels"], d["slots"])):
                        if si > 0:
                            slots_html += '<div style="font-size:16px;color:#718096;display:flex;align-items:center">&#8594;</div>'
                        slots_html += f'<div style="flex:1;border:1px solid #eee;border-radius:4px;background:#f8f9fa;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:4px 3px;text-align:center"><div style="font-size:6px;font-weight:800;text-transform:uppercase;color:#718096;margin-bottom:2px">{lbl}</div><div style="font-size:{em_sz}">{slot["em"] if slot else "?"}</div><div style="font-size:8px;font-weight:700;margin-top:1px">{slot["lb"] if slot else ""}</div></div>'
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{GREEN}"></div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5px"><div style="font-size:8px;font-weight:800;color:#1a2e44;margin-bottom:4px">{(name + "\'s ") if name else ""}{d.get("title","")}</div><div style="display:flex;gap:3px;align-items:center;width:100%">{slots_html}</div></div></div>')

                elif t == "schedule":
                    slots_rows = "".join(
                        f'<div style="display:flex;align-items:center;gap:3px;padding:2px 5px;border-bottom:1px solid #f0f0f0"><span style="font-size:{"6px" if is_lanyard else "8px"};font-weight:700;color:#718096;min-width:28px">{s.get("time","")}</span><span style="font-size:{"11px" if is_lanyard else "16px"}">{s.get("em","")}</span><span style="font-size:{"7px" if is_lanyard else "10px"};font-weight:700">{s.get("act","")}</span></div>'
                        for s in d.get("slots",[])[:7]
                    )
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{TEAL}"></div><div style="flex:1;display:flex;flex-direction:column;padding:3px 0"><div style="text-align:center;font-size:8px;font-weight:800;color:#1a2e44;padding:2px 5px 3px">{(name + "\'s ") if name else ""}{d.get("title","Schedule")}</div>{slots_rows}</div></div>')

                elif t == "board":
                    cols_n = int(d["gridSize"].split("x")[0])
                    cells_html = "".join(
                        f'<div style="border:1px solid #dde;border-radius:3px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2px;text-align:center"><span style="font-size:{"13px" if is_lanyard else "18px"}">{c.get("em","")}</span><span style="font-size:{"5.5px" if is_lanyard else "8px"};font-weight:700">{c.get("tx","")}</span></div>'
                        for c in d.get("cells",[])
                    )
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:#8C2D5A"></div><div style="flex:1;display:flex;flex-direction:column;padding:3px"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">{d.get("title","Comm Board")}</div><div style="display:grid;grid-template-columns:repeat({cols_n},1fr);gap:2px;flex:1">{cells_html}</div></div></div>')

                elif t == "regulation":
                    tool = d.get("tool","")
                    if tool == "zones":
                        zboxes = "".join(
                            f'<div style="background:{zd["bg"]};border-radius:3px;padding:2px 3px"><div style="font-size:7px;font-weight:800;color:{zd["color"]}">{zd["name"].split(" - ")[0]}</div><div style="font-size:5.5px;line-height:1.4">{" / ".join(zd["feels"][:2])}</div></div>'
                            for z, zd in ZONE_DATA.items()
                        )
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:linear-gradient(to right,#3B82F6,#22C55E,#EAB308,#EF4444)"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:3px">Zones of Regulation</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;flex:1">{zboxes}</div></div></div>')
                    elif tool == "fivepoint":
                        pts = "".join(f'<div style="flex:1;background:{FIVE_COLORS[i]};border-radius:4px;text-align:center;padding:2px"><div style="font-size:11px">{FIVE_EMOJIS[i]}</div><div style="font-size:8px;font-weight:900">{i+1}</div><div style="font-size:5px;font-weight:600">{d.get("labels",[])[i] if i < len(d.get("labels",[])) else ""}</div></div>' for i in range(5))
                        name = d.get("student","")
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{TEAL}"></div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5px"><div style="font-size:8px;font-weight:800;margin-bottom:4px">{(name + "\'s ") if name else ""}5-Point Scale</div><div style="display:flex;gap:2px;width:100%">{pts}</div></div></div>')
                    elif tool == "calmdown":
                        sh = "".join(f'<div style="text-align:center;padding:1px"><div style="font-size:12px">{s["em"]}</div><div style="font-size:5.5px;font-weight:700">{s["lb"]}</div></div>' for s in d.get("strats",[])[:9])
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{GREEN}"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">{d.get("title","Calm-Down Toolkit")}</div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;flex:1">{sh}</div></div></div>')
                    elif tool == "feelings":
                        n_c = len(d.get("feels",[])) or 4
                        fh = "".join(f'<div style="text-align:center;padding:2px;border:1px solid #dde;border-radius:3px"><div style="font-size:{"11px" if is_lanyard else "16px"}">{em}</div><div style="font-size:{"5.5px" if is_lanyard else "7px"};font-weight:700">{tx}</div></div>' for em, tx in d.get("feels",[]))
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{AMBER}"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">How am I feeling?</div><div style="display:grid;grid-template-columns:repeat({min(n_c,4)},1fr);gap:2px;flex:1">{fh}</div></div></div>')

                elif t == "script":
                    steps_html = "".join(
                        f'<div style="display:flex;align-items:flex-start;gap:2px;margin-bottom:1px"><div style="min-width:12px;height:12px;border-radius:50%;background:{TEAL};color:#fff;font-size:6px;font-weight:800;display:flex;align-items:center;justify-content:center">{i+1}</div><div style="font-size:{"6px" if is_lanyard else "8px"};font-weight:600;line-height:1.3">{s["em"]} {s["tx"]}</div></div>'
                        for i, s in enumerate(d.get("steps",[])[:5])
                    )
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:#3730A3"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:3px">{(name + "\'s ") if name else ""}{d.get("title","Social Script")}</div>{steps_html}</div></div>')

            per_row = 2
            per_page = 8 if is_lanyard else 4
            pages = [all_cards_html[i:i+per_page] for i in range(0, len(all_cards_html), per_page)]

            def make_page(cards):
                rows_h = ""
                for ri in range(0, len(cards), per_row):
                    row_cards = cards[ri:ri+per_row]
                    cols_html = "".join(f'<td style="width:50%;padding:2mm;vertical-align:top">{c}</td>' for c in row_cards)
                    rows_h += f"<tr>{cols_html}</tr>"
                return f'<table style="width:100%;border-collapse:collapse;page-break-after:always">{rows_h}</table>'

            print_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>*{{box-sizing:border-box;margin:0;padding:0;font-family:'Nunito',sans-serif}}@page{{size:{page_size};margin:6mm}}body{{background:#fff}}</style>
</head><body>{"".join(make_page(p) for p in pages)}</body></html>"""

            st.download_button(
                label="⬇️ Download print HTML",
                data=print_html,
                file_name=f"visual_supports_{fmt.replace(' ','_').lower()}.html",
                mime="text/html",
            )
            st.info("Open the downloaded file in Chrome then use File > Print (Ctrl+P). Set margins to None and enable Background graphics.")
