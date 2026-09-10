from theme import apply_clc_theme
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import uuid
import random
import json
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
# ── Location normalisation ────────────────────────────────────────────────────
LOCATION_ALIASES = {
    "JP Classroom": "JP Room", "JP classroom": "JP Room", "Junior Primary": "JP Room",
    "PY Classroom": "PY Room", "PY classroom": "PY Room", "Primary Years": "PY Room",
    "SY Classroom": "SY Room", "SY classroom": "SY Room", "Senior Years": "SY Room",
    "Playground": "Yard", "playground": "Yard",
}

def normalise_location(loc: str) -> str:
    """Map historical location aliases to canonical labels."""
    return LOCATION_ALIASES.get(str(loc).strip(), str(loc).strip()) if loc else ""


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
VALID_PAGES = ["login", "landing", "program_students", "incident_log", "critical_incident", "review_critical", "leader_approve_critical", "student_analysis", "student_dashboard", "admin_portal"]

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


def generate_behaviour_analysis_plan_docx(student, full_df, top_ant, top_beh, top_loc, top_session, risk_score, risk_level):
    """Generate professional BAP — fixed chart sizing and page layout."""
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

        FIG_W    = 16.5   # wider — fills the page
        FIG_H    = 4.2    # taller — more readable when printed
        FIG_DPI  = 150    # sharper for printing
        DOC_W    = Cm(18.5)  # stretch to near full page width
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
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_before = Pt(1)
            cap.paragraph_format.space_after  = Pt(6)
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
            ax.tick_params(colors='#334155', labelsize=9)
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
        arun(p1, "BEHAVIOUR SUMMARY", bold=True, size=28, color=WHITE)
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

        doc.add_page_break()

        section_header(doc, "VISUAL ANALYTICS — FREQUENCY PATTERNS")
        p_sp = doc.add_paragraph(); p_sp.paragraph_format.space_after = Pt(4)

        # Show ALL days in range (not just incident days) so zero-incident days are visible
        import datetime as _bdt
        _b_start = full_df["date_parsed"].min().date()
        _b_end   = full_df["date_parsed"].max().date()
        _b_all_days = []
        _b_d = _b_start
        while _b_d <= _b_end:
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
        _fi_zero_days_bap     = sum(1 for v in daily.count if v == 0)
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
        ax.set_title("1.  Daily Incident Frequency  —  teal = 1–2 incidents,  red = 3+",
                     fontsize=11.5, fontweight='bold', color='#0f172a', pad=8, loc='left')
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        for bar, v in zip(bars, daily.count):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        str(int(v)), ha='center', va='bottom', fontsize=9, fontweight='bold', color='#0f172a')
        base_ax_style(ax)
        plt.tight_layout(pad=0.4)
        add_chart(doc, fig,
            f"Daily totals across {_fi_total_days_bap} school days. "
            f"Incidents occurred on {_fi_incident_days_bap} days ({_fi_zero_days_bap} incident-free). "
            f"On days with incidents, average was {_fi_avg_per_day_bap:.1f} per day "
            f"(peak: {_fi_max_day_bap}). "
            + (f"{_fi_high_days_bap} day(s) had 3 or more incidents — "
               "these are high-demand days requiring retrospective review: what was different about "
               "the environment, staffing, timetable, or demands on those days? "
               if _fi_high_days_bap > 0 else "") +
            (f"There are {_fi_consec_bap} instance(s) of consecutive incident days — "
             "consecutive high-incident days indicate the student did not have sufficient recovery time "
             "between episodes, or a systemic stressor was sustained across multiple days. "
             "Proactive regulation support at the start of each day is strongly indicated. "
             if _fi_consec_bap >= 2 else "") +
            f"Incident-free days ({_fi_zero_days_bap}) are equally important — "
            "what proactive conditions were in place on those days? Replicating them on high-risk days "
            "is one of the most effective preventive strategies available.")

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
            f"The most frequently occurring behaviour is {_bap_beh_labels[0] if _bap_beh_labels else 'Unknown'} "
            f"({_bap_beh_vals[0] if _bap_beh_vals else 0} of {len(full_df)} incidents, "
            f"{int((_bap_beh_vals[0] if _bap_beh_vals else 0)/max(len(full_df),1)*100)}% of total). "
            + (f"A wide range of behaviour types ({len(_bap_beh_labels)} types shown) indicates a broad stress response — "
               "the student is communicating distress through multiple channels. "
               "Foundational Body domain regulation supports (sensory regulation, movement breaks, "
               "predictable routines) should be the primary focus rather than behaviour-by-behaviour intervention. "
               if len(_bap_beh_labels) >= 4 else
               "A narrow behaviour profile (1-2 types) suggests a specific, consistent function — "
               "the student is using a predictable response to communicate a particular unmet need. "
               "This supports targeted functional intervention: identify the function, "
               "teach an alternative, and pre-empt the trigger. ") +
            "Behaviours are described using consistent, observable language to support shared understanding across the team.")

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
            f"The most frequent trigger is '{wrap_labels([top_ant], width=60)[0]}' "
            f"({int(ant_counts.values[0])} of {len(full_df)} incidents, "
            f"{int(ant_counts.values[0]/max(len(full_df),1)*100)}% of total). "
            "Antecedent-stage intervention — modifying what happens before the trigger occurs — "
            "is consistently more effective than any consequence-based response. "
            "The goal is either to reduce or modify the trigger itself, or to build the student's "
            "capacity to tolerate it through graduated exposure and skill-building. "
            "Triggers that cluster around peer interaction, instruction, or transitions point to "
            "specific environmental conditions that can be directly modified by staff. "
            "Sensory triggers indicate the nervous system is overloaded before behaviour emerges — "
            "a sensory audit and proactive sensory breaks are the most direct preventive intervention.")

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
            f"({int(session_counts[peak_name]/max(len(full_df),1)*100)}%). "
            + ({"Morning":
                "Morning peaks frequently reflect difficulty with the transition from home, "
                "low readiness to engage, or unmet overnight and morning needs (hunger, sleep disruption, "
                "sensory dysregulation on arrival). A structured, low-demand arrival routine with a "
                "trusted adult check-in is the most effective morning intervention. "
                "Consider: has the student eaten? Have there been any household stressors? "
                "A predictable, warm, unhurried start to the day reduces cortisol and builds regulatory capacity "
                "before academic demands are introduced.",
                "Middle":
                "Middle-of-day peaks reflect cumulative fatigue — the student has been managing demands "
                "since arrival and regulatory capacity is depleted. Lunch and transition periods introduce "
                "unstructured time which can be particularly challenging. "
                "A mid-day sensory or movement break, a quiet opt-out space, and reduced demand "
                "before and after the lunch break are high-priority strategies. "
                "Pre-teach the transition into and out of lunch with explicit expectations and a visual schedule.",
                "Afternoon":
                "Afternoon peaks often reflect end-of-day fatigue, anticipatory anxiety about the transition "
                "home, or the accumulation of the day's regulatory demands. "
                "A structured, predictable end-of-day routine — including a debrief, a positive closure "
                "activity, and advance notice of tomorrow's schedule — reduces afternoon escalation. "
                "Consider the student's home situation: if the transition home is anxiety-provoking, "
                "this may manifest as afternoon behaviour at school.",
               }.get(peak_name,
                "Review the specific conditions of this session and schedule targeted proactive support. "
                "Identify what is different about the lowest-incident session and replicate those conditions.")) +
            f" Lowest-frequency session provides a template: identify what differs structurally and replicate.")

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
            f"{int(loc_counts.values[-1]/max(len(full_df),1)*100)}% of total). "
            "Location clustering signals that specific environmental conditions are contributing to behaviour. "
            + ({"jp room": "Classroom behaviour often reflects academic demand, seating arrangements, "
                "peer noise, or non-preferred task presentation. Review the physical layout, "
                "sensory conditions, and demand level of activities occurring at the time of incidents.",
                "py room": "Classroom behaviour often reflects academic demand, seating arrangements, "
                "peer noise, or non-preferred task presentation. Review the physical layout, "
                "sensory conditions, and demand level of activities occurring at the time of incidents.",
                "sy room": "Classroom behaviour often reflects academic demand, seating arrangements, "
                "peer noise, or non-preferred task presentation. Review the physical layout, "
                "sensory conditions, and demand level of activities occurring at the time of incidents.",
                "yard":    "Yard incidents reflect unstructured time, peer conflict, sensory overload, "
                "and reduced adult proximity. Increased supervision ratios, structured yard activities, "
                "and a clear opt-out space are recommended.",
                "kitchen": "Kitchen incidents may reflect access to food as a motivator, transitions "
                "in/out of the space, or sensory factors around meal/snack time. "
                "Ensure clear, consistent expectations and supervised, predictable kitchen routines.",
                "toilets": "Incidents in or near toilets may indicate the student uses this space as an "
                "escape route, or that transitions to/from the toilets are a trigger. "
                "Review supervision and transition routines.",
               }.get(normalise_location(top_loc).lower(),
               "Conduct an environmental audit of this location — review noise level, crowding, "
               "supervision ratio, demand level, and transition patterns in and out of the space. ")) +
            "An environmental audit of this location is the most direct preventive action. "
            "Also note whether this hotspot coincides with the peak time of day — "
            "if so, the combination creates a compounding risk window requiring an immediate targeted plan.")

        # WoT for incidents: yellow/orange=coping (L1-3), red=outside window (L4-5)
        sev_colours = {1:'#eab308',2:'#eab308',3:'#f97316',4:'#ef4444',5:'#7f1d1d'}
        sev_level_names = {1:'Level 1 (Minor)',2:'Level 2 (Low)',3:'Level 3 (Moderate)',
                           4:'Level 4 (Serious)',5:'Level 5 (Critical)'}
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)
        ax.axhspan(0.5, 3.5,  color='#fef9c3', alpha=0.35, zorder=0)  # yellow — coping zone L1-3
        ax.axhspan(3.5, 5.5,  color='#fee2e2', alpha=0.30, zorder=0)  # red — outside window L4-5
        for y, lbl, col in [(1.5,'Within window (regulated)','#16a34a'),
                            (3.0,'Coping','#ca8a04'),
                            (4.5,'Outside window','#dc2626')]:
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
            f"Severity trajectory: {direction} (early average {e_avg:.1f} → recent average {r_avg:.1f}). "
            + ({
               "reducing": (
                   f"Average severity has reduced by {abs(round(r_avg-e_avg,1))} levels across the data period. "
                   "This is a meaningful positive indicator — the student is experiencing less intense episodes over time. "
                   "This may reflect improved regulatory capacity, more effective proactive supports, or a stronger "
                   "relational foundation with key staff. Document specifically what has changed and ensure those "
                   "conditions are deliberately sustained — gains in regulation can reverse quickly if supports "
                   "are reduced or key staff change."
               ),
               "stable": (
                   "Severity has remained stable across the data period. "
                   "Current supports are maintaining a consistent level of functioning — not a deterioration, "
                   "but not a recovery. Consider whether support intensity matches the student's needs, "
                   "or whether a targeted strategy shift is needed to move the trajectory downward. "
                   "A case review or consultation with an external specialist may be appropriate "
                   "if this pattern has held across multiple terms."
               ),
               "increasing": (
                   f"Average severity has increased by {abs(round(r_avg-e_avg,1))} levels — "
                   "the most significant finding in this analysis. Current supports are insufficient. "
                   "Recommended immediate actions: case conference, updated safety plan, "
                   "sensory and environmental audit, review of staffing consistency and relational supports, "
                   "and consideration of specialist referral. Also check whether external stressors "
                   "(family changes, transitions, health factors) are contributing."
               ),
              }.get(direction, "")) +
            " Yellow zone (L1–L3) = Coping. Red zone (L4–L5) = Outside window. "
            "A critical incident does not automatically mean outside the window. "
            "All episodes in the red zone require post-incident relational repair before re-engaging with learning.")

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
                "Day-of-week patterns point to timetable-specific triggers. "
                "The recommended action is to review the full timetable for the peak day: "
                "which subjects, staff members, peer groupings, or transitions are unique to that day? "
                "Is there a particular subject that is cognitively demanding or non-preferred? "
                "Is there a staffing change (e.g. a relief teacher, a different support worker)? "
                "Is there an unstructured or transition-heavy period that does not appear on other days? "
                + (f"The lowest-incident day is {_dow_low_bap} — "
                   "this day provides a template for what effective conditions look like. "
                   "Identify what is structurally different and deliberately replicate those conditions "
                   "on high-risk days. This is one of the highest-leverage preventive strategies available. "
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
                "Escalation rate is the proportion of incidents for each behaviour that progressed "
                "from a regular (Coping zone) episode to a critical incident (ABCH-documented). "
                "A high rate for a specific behaviour signals that something about how that behaviour unfolds "
                "— the environment, the staff response, or the student's internal state — "
                "is not being interrupted effectively while the student is still in the Coping zone. "
                "Grey bars indicate fewer than 4 incidents — rate is not yet reliable, continue logging. "
                "The Sev StDev (if shown) tells you how variable the severity is: a low value means "
                "episodes are consistently similar in intensity; a high value means the student "
                "oscillates between mild and severe episodes, which may indicate inconsistent triggers "
                "or inconsistent staff responses across different contexts. "
                + (f"HIGH ESCALATION RISK IDENTIFIED: {", ".join(x[0][:35] for x in _high_esc)}. "
                   "For these behaviours, proactive strategies must be in place BEFORE the behaviour emerges. "
                   "The Coping zone (yellow/orange) is the window for effective intervention — "
                   "once the student moves to the outside-window zone (red), de-escalation is the only "
                   "available strategy and learning re-engagement must wait until full recovery. "
                   "Review the antecedent chain for these specific behaviours: what conditions reliably "
                   "precede escalation, and how can those conditions be modified or removed? "
                   if _high_esc else
                   "No behaviours are currently showing high escalation risk — "
                   "all incidents are remaining within the Coping zone rather than escalating to critical. "
                   "This is a significant positive indicator: document and sustain current staff responses. "))

        # ── Chart 9: Severity distribution by Behaviour (WoT coloured) ──
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        _sv_behs = [b for b in full_df["behaviour_type"].value_counts().head(5).index
                    if b and len(str(b)) <= 80 and not str(b).startswith("---")]
        if _sv_behs and len(full_df) >= 4:
            _WOT_COLS_BAP = {1:"#eab308",2:"#eab308",3:"#f97316",4:"#ef4444",5:"#7f1d1d"}
            _WOT_LBLS_BAP = {1:"L1 Coping",2:"L2 Coping",3:"L3 Approaching edge",
                             4:"L4 Outside window",5:"L5 Crisis"}
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
                f"{_c_pct}% of all incidents ({_coping_n} of {len(full_df)}) occurred within the Coping zone (L1–L3). "
                "This chart shows how each behaviour type is distributed across Window of Tolerance zones. "
                "Colour key: yellow = L1-2 Coping (low-level behaviour, student managing); "
                "orange = L3 Coping, approaching edge; red = L4-5 Outside window (significant dysregulation). "
                "Behaviours with a high proportion of yellow/orange are being managed within the Coping zone — "
                "these are responsive to proactive supports and de-escalation strategies. "
                "Behaviours with a high proportion of red indicate the student is regularly moving "
                "outside their window with this specific behaviour — these require urgent antecedent intervention, "
                "a robust safety plan, and a clear post-incident relational repair protocol. "
                "Important: a critical incident classification does not automatically mean outside the window — "
                "many critical incidents are logged at L3 (Coping, approaching edge). "
                + (f"The remaining {100-_c_pct}% ({_outside_n} incidents) reached the outside-window zone (L4-5). "
                   "Post-incident repair — re-establishing relational safety before returning to learning — "
                   "is essential after every outside-window episode. "
                   "Review what proactive conditions were absent on those days. "
                   if _outside_n > 0 else
                   "All logged incidents remained within the Coping zone — a strong positive indicator. "
                   "Current staff responses are successfully preventing escalation to full dysregulation. "
                   "Document and sustain current proactive strategies explicitly. "))

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

        sl_tbl = doc.add_table(rows=2, cols=2); sl_tbl.style = 'Table Grid'
        sl_data = [
            ("🧠 Regulation & Sensory", [
                f"Incorporate a sensory diet before the {top_session} session — movement break, heavy work, or proprioceptive input to prepare the nervous system.",
                "Co-regulate with a key adult using CPI Supportive Stance (low, slow, sideways) as the default interaction posture.",
                f"Develop a personalised Window of Tolerance profile for {student['name']} — document early warning signs, escalation cues, and effective de-escalation strategies.",
                "Teach and embed regulation tools during calm states; cue their use proactively at Level 2 before escalation occurs.",
                "Monitor medication timing and note correlations with incident frequency in the peak session.",
            ]),
            ("🛡️ Antecedent Prevention", [
                f"Conduct an environmental audit of {top_loc} — review and modify sensory load, spatial arrangement, and proximity to triggers.",
                "Implement pre-correction immediately before high-risk contexts — calm reminder of expectations and available supports.",
                f"Conduct Functional Communication Training (FCT) — teach a socially appropriate replacement behaviour serving the same function as {get_clinical_behaviour(top_beh).lower()}.",
                "Apply structured peer interaction protocols — pre-assign groupings and roles; avoid unstructured proximity where peer triggers are present.",
                "Develop a Crisis Safety Plan with Level 3+ protocols, staff roles, and a post-incident restorative repair sequence.",
            ]),
            ("🔄 Post-Incident Repair", [
                "Restore the relationship before re-engaging with academic demands — never return to tasks while the student remains dysregulated.",
                "Conduct a brief, non-punitive restorative conversation once regulated — focus on impact and repair.",
                "Complete a structured staff debrief after every Level 3+ incident.",
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

        # Sign-off section removed — BAP approved via portal workflow

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
        res = supabase.table("student_attendance") \
            .select("*").eq("student_id", student_id).limit(1).execute()
        if res.data:
            row = res.data[0]
            return {
                "absent_dates": row.get("absent_dates") or [],
                "pt_days":      row.get("pt_days") or ["Monday","Tuesday","Wednesday","Thursday","Friday"],
                "pt_sessions":  row.get("pt_sessions") or ["Full day"],
                "pt_notes":     row.get("pt_notes") or "",
            }
    except Exception:
        pass
    return {}


def save_attendance_to_db(student_id, absent_dates, pt_days, pt_sessions, pt_notes):
    """Upsert attendance record for a student in Supabase."""
    if not supabase or not student_id:
        return False
    try:
        data = {
            "student_id":   student_id,
            "absent_dates": absent_dates or [],
            "pt_days":      pt_days or [],
            "pt_sessions":  pt_sessions or [],
            "pt_notes":     pt_notes or "",
        }
        # Try update first
        res = supabase.table("student_attendance") \
            .update(data).eq("student_id", student_id).execute()
        if not res.data:
            # No existing row — insert
            supabase.table("student_attendance").insert(data).execute()
        return True
    except Exception as e:
        return False


def load_students_from_db():
    if not supabase:
        return MOCK_STUDENTS
    try:
        response = supabase.table('students').select('*').execute()
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
        response = supabase.table('staff').select('*').execute()
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
        response = query.execute()
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
        response = query.execute()
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
    if "students" not in ss:
        ss.students = load_students_from_db() if supabase else MOCK_STUDENTS
    if "staff" not in ss:
        ss.staff = load_staff_from_db() if supabase else MOCK_STAFF
    if "incidents" not in ss:
        ss.incidents = load_incidents_from_db() if supabase else generate_mock_incidents(70)
    if "critical_incidents" not in ss:
        ss.critical_incidents = load_critical_incidents_from_db() if supabase else []
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
            st.session_state.logged_in = False
            st.session_state.current_page = "login"
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
    col1, col2 = st.columns([3, 1])
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


def render_student_analysis_page():
    student_id = st.session_state.get("selected_student_id")
    student = get_student(student_id)
    if not student:
        st.error("No student selected"); return

    st.markdown(f"## 📊 Behaviour Summary — {student['name']}")
    st.caption("Evidence-based analysis prepared by Learning and Behaviour Unit")

    if student.get('placement_start'):
        try:
            start_dt = datetime.fromisoformat(student['placement_start'])
            end_dt = datetime.fromisoformat(student['placement_end']) if student.get('placement_end') else datetime.utcnow()
            days_enrolled = (end_dt.date() - start_dt.date()).days
            st.markdown("---")
            pcol1, pcol2, pcol3 = st.columns(3)
            with pcol1: st.metric("Placement Start", start_dt.strftime('%d/%m/%Y'))
            with pcol2:
                if student.get('placement_end'):
                    st.metric("Placement End", datetime.fromisoformat(student['placement_end']).strftime('%d/%m/%Y'))
                else:
                    st.metric("Status", "Ongoing")
            with pcol3: st.metric("Days Enrolled", days_enrolled)
            st.markdown("---")
        except: pass

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_analysis_top"):
            go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("🏠 Program Landing", key="home_analysis"):
            go_to("landing")

    # ── Part-time schedule context ───────────────────────────────────────────
    # ── Load saved attendance from Supabase on first render ─────────────────
    _att_cache_key = f"att_loaded_{student_id}"
    if _att_cache_key not in st.session_state:
        _att_from_db = load_attendance_from_db(student_id)
        if _att_from_db:
            st.session_state[f"absent_dates_{student_id}"]  = _att_from_db.get("absent_dates", [])
            st.session_state[f"pt_days_{student_id}"]       = _att_from_db.get("pt_days", ["Monday","Tuesday","Wednesday","Thursday","Friday"])
            st.session_state[f"pt_sess_{student_id}"]       = _att_from_db.get("pt_sessions", ["Full day"])
            st.session_state[f"pt_notes_{student_id}"]      = _att_from_db.get("pt_notes", "")
        st.session_state[_att_cache_key] = True

    _abs_key   = f"absent_dates_{student_id}"
    _abs_stored = st.session_state.get(_abs_key, [])
    _pt_days    = st.session_state.get(f"pt_days_{student_id}", ["Monday","Tuesday","Wednesday","Thursday","Friday"])
    _pt_sessions = st.session_state.get(f"pt_sess_{student_id}", ["Full day"])
    _pt_notes   = st.session_state.get(f"pt_notes_{student_id}", "")

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
        _ext_key_an   = f"placement_extensions_{student_id}"
        _pl_exts      = st.session_state.get(_ext_key_an, [])

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
                    _pl_exts = _pl_exts + [{"from": _an_ef.isoformat(), "to": _an_et.isoformat(), "reason": _an_er.strip()}]
                    st.session_state[_ext_key_an] = _pl_exts
                    st.success(f"✅ Extension added: {_an_ef.strftime('%-d %b')} – {_an_et.strftime('%-d %b %Y')}")
                    st.rerun()
                else:
                    st.error("Please complete all three fields.")

        st.session_state[f"pl_start_an_{student_id}"] = _pl_start_raw
        st.session_state[f"pl_end_an_{student_id}"]   = _pl_end_raw


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
                                from groq import Groq as _GQ
                                import json as _sjs
                                _gc = _GQ(api_key=GROQ_KEY)
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
                                _so_resp = _gc.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": _so_prompt}],
                                    max_tokens=1500, temperature=0.1
                                )
                                _so_json = _so_resp.choices[0].message.content.strip()
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

    with st.expander("⏱️ Attendance & Absence Tracking — saved automatically", expanded=False):
        st.caption(
            "Record attendance pattern and specific absent dates. "
            "Data is saved automatically to the database. "
            "Absent days appear on the frequency chart and are used in the pattern analysis below."
        )

        _att_tab1, _att_tab2 = st.tabs(["📅 Regular Schedule", "🗓️ Absent Dates"])

        with _att_tab1:
            _pt_days_new = st.multiselect(
                "Days the student regularly attends",
                ["Monday","Tuesday","Wednesday","Thursday","Friday"],
                default=_pt_days,
                key=f"pt_days_w_{student_id}"
            )
            _pt_sess_new = st.multiselect(
                "Sessions attended",
                ["Full day","Morning only","Middle of day only","Afternoon only","Morning + Middle","Middle + Afternoon"],
                default=_pt_sessions,
                key=f"pt_sess_w_{student_id}"
            )
            _pt_notes_new = st.text_area(
                "Schedule notes",
                value=_pt_notes,
                placeholder="e.g. Attends Tue–Thu, mornings only. Transition to full days planned Term 2.",
                height=65, key=f"pt_notes_w_{student_id}"
            )
            if st.button("💾 Save schedule", key=f"pt_save_{student_id}", type="primary", use_container_width=True):
                st.session_state[f"pt_days_{student_id}"]  = _pt_days_new
                st.session_state[f"pt_sess_{student_id}"]  = _pt_sess_new
                st.session_state[f"pt_notes_{student_id}"] = _pt_notes_new
                _pt_days = _pt_days_new; _pt_sessions = _pt_sess_new; _pt_notes = _pt_notes_new
                save_attendance_to_db(student_id, _abs_stored, _pt_days_new, _pt_sess_new, _pt_notes_new)
                st.success("✅ Schedule saved.")

        with _att_tab2:
            st.caption(
                "Add dates when the student was absent. "
                "Each date is saved immediately. Saved dates appear on the frequency chart."
            )
            _abs_col1, _abs_col2 = st.columns([2, 1])
            with _abs_col1:
                _abs_new = st.date_input(
                    "Date to add",
                    value=None, key=f"abs_date_input_{student_id}"
                )
            with _abs_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ Add & save", key=f"abs_add_{student_id}",
                             type="primary", use_container_width=True):
                    if _abs_new and str(_abs_new) not in _abs_stored:
                        _abs_stored = sorted(_abs_stored + [str(_abs_new)])
                        st.session_state[_abs_key] = _abs_stored
                        save_attendance_to_db(student_id, _abs_stored, _pt_days, _pt_sessions, _pt_notes)
                        st.rerun()

            if _abs_stored:
                st.markdown(f"**{len(_abs_stored)} absent date(s) recorded:**")
                _abs_display_cols = st.columns(4)
                for _i, _d in enumerate(sorted(_abs_stored)):
                    with _abs_display_cols[_i % 4]:
                        if st.button(f"❌ {_d}", key=f"abs_rm_{student_id}_{_i}", use_container_width=True):
                            _abs_stored = [x for x in _abs_stored if x != _d]
                            st.session_state[_abs_key] = _abs_stored
                            save_attendance_to_db(student_id, _abs_stored, _pt_days, _pt_sessions, _pt_notes)
                            st.rerun()
            else:
                st.info("No absent dates recorded yet — add dates above.")

    # ── Active attendance summary (always visible below expander) ─────────
    _parttime_active = len(_pt_days) < 5 or (len(_pt_sessions) > 0 and "Full day" not in _pt_sessions)
    _absent_dates    = _abs_stored
    if _parttime_active or _absent_dates:
        _att_html = (
            "<div style='background:#eff6ff;border-left:4px solid #3b82f6;border-radius:8px;"
            "padding:.65rem 1rem;margin:.4rem 0;font-size:.84rem;color:#1e293b;'>"
            "<b>⏱️ Attendance context active</b><br>"
        )
        if _parttime_active:
            _att_html += (
                f"<b>Part-time schedule:</b> attends {len(_pt_days)}/5 days "
                f"({", ".join(_pt_days[:3])}{"..." if len(_pt_days) > 3 else ""}). "
                "Sessions: " + (", ".join(_pt_sessions) if _pt_sessions else "not specified") + ". "
                "Zero-incident days may reflect absence. Time-of-day analysis reflects attended sessions only.<br>"
            )
        if _absent_dates:
            _att_html += (
                f"<b>Absent dates recorded: {len(_absent_dates)}</b> — "
                "marked on the frequency chart below. "
                "Zero-incident days on these dates reflect absence, not regulation.<br>"
            )
        if _pt_notes:
            _att_html += f"<i>Note: {_pt_notes}</i>"
        _att_html += "</div>"
        st.markdown(_att_html, unsafe_allow_html=True)

    quick = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    crit = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]

    if not quick and not crit:
        st.info("No incident data available yet.")
        if st.button("↩️ Back", key="back_no_data"):
            go_to("program_students", selected_program=student["program"])
        return

    quick_df = pd.DataFrame(quick) if quick else pd.DataFrame()
    crit_df = pd.DataFrame(crit) if crit else pd.DataFrame()

    if not quick_df.empty:
        quick_df["incident_type"] = "Quick"
        quick_df["date_parsed"] = pd.to_datetime(
            quick_df["date"], utc=True, errors="coerce"
        ).dt.tz_localize(None)
        if "location" in quick_df.columns:
            quick_df["location"] = quick_df["location"].apply(normalise_location)
        if "intervention" in quick_df.columns:
            quick_df["intervention_str"] = quick_df["intervention"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))

    if not crit_df.empty:
        crit_df["incident_type"] = "Critical"
        _crit_dates_a = crit_df["created_at"] if "created_at" in crit_df.columns else pd.Series(
            [datetime.now().isoformat()] * len(crit_df), index=crit_df.index
        )
        crit_df["date_parsed"] = pd.to_datetime(
            _crit_dates_a, utc=True, errors="coerce"
        ).dt.tz_localize(None)
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

    full_df = pd.concat([quick_df, crit_df], ignore_index=True).sort_values("date_parsed")
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

    st.markdown("### 📈 Executive Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Total", len(full_df))
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
        _fi_total_days  = (full_df["date_parsed"].max() - full_df["date_parsed"].min()).days + 1
        _fi_incident_days = full_df["date_parsed"].dt.date.nunique()
        _fi_zero_days   = _fi_total_days - _fi_incident_days
        _fi_day_counts  = full_df.groupby(full_df["date_parsed"].dt.date).size()
        _fi_max_day     = int(_fi_day_counts.max())
        _fi_avg_per_day = len(full_df) / max(_fi_incident_days, 1)
        _fi_high_days   = int((_fi_day_counts >= 3).sum())
        # Identify any consecutive runs of 2+ incident days
        _fi_dates_sorted = sorted(_fi_day_counts.index)
        _fi_consec = 0
        if len(_fi_dates_sorted) >= 2:
            import datetime as _fdt
            for _dx in range(1, len(_fi_dates_sorted)):
                if (_fi_dates_sorted[_dx] - _fi_dates_sorted[_dx-1]).days == 1:
                    _fi_consec += 1
        _fi_insight = (
            f"<b>{_fi_incident_days} of {_fi_total_days} school days</b> had at least one incident "
            f"({_fi_zero_days} day(s) incident-free). "
            f"When incidents occurred, the average was <b>{_fi_avg_per_day:.1f} per day</b> "
            f"(highest single day: {_fi_max_day}). "
        )
        if _fi_high_days >= 2:
            _fi_insight += (
                f"<b>{_fi_high_days} day(s) had 3 or more incidents</b> — these are high-demand days "
                "that warrant retrospective review: what was different about the environment, "
                "staffing, timetable, or demands on those days? "
            )
        if _fi_consec >= 2:
            _fi_insight += (
                f"There are <b>{_fi_consec} instance(s) of consecutive incident days</b>. "
                "Consecutive high-incident days are a significant indicator — they suggest the student "
                "did not have sufficient recovery time between events, or that a systemic stressor "
                "(e.g. a transition, staffing change, or curriculum demand) was sustained across multiple days. "
                "Proactive regulation support at the start of each day is strongly indicated. "
            )
        _fi_insight += (
            f"Incident-free days ({_fi_zero_days}) are equally important data — "
            "what proactive conditions, routines, or environmental factors were in place on those days? "
            "Replicating those conditions on high-risk days is one of the most effective preventive strategies."
        )
        st.markdown(
            f"<div style='background:#f8fafc;border-left:4px solid #1A7A7A;border-radius:8px;"
            f"padding:.75rem 1.1rem;margin:.5rem 0;font-size:.84rem;color:#1e293b;line-height:1.65;'>"
            f"<b>📊 Understanding this chart:</b><br>{_fi_insight}</div>",
            unsafe_allow_html=True
        )
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
                    "a high-severity incident (Level 4–5) within 1–2 days. "
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
    _pl_exts_an   = st.session_state.get(f"placement_extensions_{student_id}", [])
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
    _SEV_LABELS = ["L1 Minor", "L2 Low", "L3 Moderate", "L4 Serious", "L5 Critical"]

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
            "🟡 Yellow (L1–2) = Coping — behaviour present but student managing  ·  "
            "🟠 Orange (L3) = Coping, approaching edge  ·  "
            "🔴 Red (L4–5) = Outside window — significant dysregulation. "
            "Critical incident status alone does not place a student outside their window."
        )
        # WoT zone colour map
        # Clinical framework: if incident logged, student NOT in green.
        # Yellow = Coping (L1-L3), Red = Outside window (L4-L5)
        _WOT_COLS = {
            1: "#eab308",   # yellow — coping (low level behaviour)
            2: "#eab308",   # yellow — coping
            3: "#f97316",   # orange — coping, approaching edge
            4: "#ef4444",   # red    — outside window
            5: "#7f1d1d",   # dark red — crisis
        }
        _WOT_NAMES = {
            1: "L1 — Coping",
            2: "L2 — Coping",
            3: "L3 — Coping, approaching edge",
            4: "L4 — Outside window",
            5: "L5 — Crisis",
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
                f"(L1–L3: low-level {_pb_l1_n}, escalating {_pb_l2_n}, approaching edge {_pb_l3_n}). "
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
                "Where the mean approaches L3 or above, consider whether current antecedent strategies "
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
                # Green (L1-2) = coping/within window, Amber (L3) = elevated,
                # Red (L4-5) = outside window. Count drives bar length, not colour.
                # WoT colour scheme (per CLC-LBU framework):
                # Green  = Within window (L1-2) — student regulated and engaged
                # Yellow = Coping (L3)          — managing but approaching edge
                # Red    = Outside window (L4-5) — dysregulated / crisis
                _SEV_COLOURS_WOT = {
                    1: "#22c55e",  # green  — within window
                    2: "#22c55e",  # green  — within window
                    3: "#eab308",  # yellow — coping / approaching edge
                    4: "#ef4444",  # red    — outside window / serious
                    5: "#7f1d1d",  # dark red — crisis zone
                }
                _sev_names_wot = {
                    1: "L1 Within window (regulated)",
                    2: "L2 Within window (low concern)",
                    3: "L3 Coping (approaching edge)",
                    4: "L4 Outside window (serious)",
                    5: "L5 Outside window (crisis)",
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
                    "🟢 Green (L1–2) = Within window — student is regulated and engaged effectively  ·  "
                    "🟡 Yellow (L3) = Coping — managing, but approaching the edge of the window  ·  "
                    "🔴 Red (L4–5) = Outside window — dysregulated / crisis zone. "
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
                    "Risk Level": f"{risk_icon} {risk_lbl}",
                })
            else:
                _risk_rows.append({
                    "Behaviour": beh, "Total (n)": total, "Regular": total-crit, "Critical": crit,
                    "Escalation %": "⚠️ Insufficient", "Mean Sev": f"{sev_m:.1f}" if total > 0 else "—",
                    "Sev StDev": "—", "Risk Level": "⚪ Limited data",
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
                    "Risk Level":   st.column_config.TextColumn("Risk Level", width="medium"),
                }
            )
            st.caption(
                "🔴 High = 51%+ escalate  ·  🟡 Medium = 26–50%  ·  🟢 Low = 0–25%  ·  "
                "⚪ Insufficient = fewer than 4 incidents logged for this behaviour — "
                "not a data error, just means more observations are needed before a reliable rate can be calculated  ·  "
                "Sev StDev: spread of severity scores (higher = more variable)"
            )
            _pch = [r for r in _risk_rows if r.get("Risk Level","").startswith("🔴")]
            _pcm = [r for r in _risk_rows if r.get("Risk Level","").startswith("🟡")]
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
                   annotation_text="Coping zone (L1–L3) — behaviour present, student managing", annotation_position="top left", line_width=0)
    fig4.add_hrect(y0=3.5, y1=5.5, fillcolor="#fee2e2", opacity=0.25,
                   annotation_text="Outside window (L4–L5) — significant dysregulation", annotation_position="top left", line_width=0)
    # WoT for incidents: yellow=coping (L1-3), red=outside window (L4-5)
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
            ticktext=['L1<br>Coping', 'L2<br>Coping', 'L3<br>Approaching<br>edge',
                      'L4<br>Outside<br>window', 'L5<br>Crisis'],
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
            "Yellow zone = Coping (L1–L3, behaviour present but student managing). "
            "Red zone = Outside window (L4–L5, significant dysregulation). "
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
    _card(dc3, "Risk Level",              f"{risk_level} ({risk_score}/100)",         f"{risk_color}22",risk_color,risk_color)

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    dc4, dc5, dc6 = st.columns(3)
    _card(dc4, "Behaviour Label",  top_beh_clinical,                          "#f0fdf4","#22c55e","#15803d")
    _card(dc5, "Primary Antecedent",        detail.get("Primary Antecedent","—"),       "#fdf4ff","#8b5cf6","#7c3aed")
    _card(dc6, "Risk Indicator",            detail.get("Risk Indicator","—"),           "#fff7ed","#f97316","#c2410c")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # ANTECEDENT CATEGORY BREAKDOWN CHART
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📂 Antecedent Category Analysis")
    st.caption("Incidents grouped by antecedent category to identify the primary trigger domain.")

    def _cat(ant):
        a = str(ant).lower()
        if a.startswith("---"): return None
        if "peer" in a: return "Peer"
        if "transition" in a: return "Transition"
        if "instruction" in a or "demand" in a or "following" in a: return "Instructions"
        if any(w in a for w in ["engagement","task","wait","routine","interrupt","finish",
                                  "literacy","maths","learning","work independently","difficult"]): return "Engagement"
        if any(w in a for w in ["sensory","noise","loud","bright","crowded","medication",
                                  "hungry","thirsty","movement break"]): return "Sensory"
        return "Other"

    full_df["_ant_cat"] = full_df["antecedent"].apply(_cat)
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
    # TEACHING LENS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎓 Teaching Lens — Recommendations")
    st.caption("Strategies for educators to embed within the learning environment and curriculum delivery.")

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
    st.caption("Therapeutic and behavioural support strategies for the care team, allied health, and leadership.")

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
            "<li><strong>Teach and embed regulation tools</strong> during calm states; cue their use proactively at Yellow/Level 2 — before escalation to Level 3+</li>"
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
            "<li>Develop a <strong>Crisis Safety Plan</strong> with Level 3+ protocols, designated staff roles, de-escalation sequence, and post-incident restorative repair procedure</li>"
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
            "<li>Complete a structured <strong>staff debrief</strong> after every Level 3+ incident — review antecedents, early warning signs, and response effectiveness</li>"
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
    st.markdown("### 🗑️ Delete an Incident")
    st.caption("Remove an incorrectly logged or duplicate incident from this student's full data set. This includes regular incidents AND critical incidents. Deletions are permanent and will affect all charts and analysis.")

    reg_incidents = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    crit_incidents = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]

    combined = []
    for i in reg_incidents:
        combined.append({
            "id": i["id"],
            "type": "regular",
            "label": f"[REGULAR]  {i.get('date','?')}  {i.get('time','')[:5]}  |  {i.get('behaviour_type','—')}  |  Severity {i.get('severity','?')}  |  {i.get('location','—')}",
            "date": i.get("date",""),
        })
    for c in crit_incidents:
        primary = c.get("ABCH_primary", {}) if isinstance(c.get("ABCH_primary"), dict) else {}
        created = (c.get("created_at","") or "")[:10]
        combined.append({
            "id": c["id"],
            "type": "critical",
            "label": f"[CRITICAL]  {created}  {primary.get('time','')[:5]}  |  {primary.get('behaviour','Behaviour not recorded')[:50]}  |  {primary.get('location','—')}",
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
                        if selected_type == "regular":
                            st.session_state.incidents = [i for i in st.session_state.incidents if i["id"] != selected_id]
                        else:
                            st.session_state.critical_incidents = [c for c in st.session_state.critical_incidents if c["id"] != selected_id]
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
                student, full_df, top_ant, top_beh, top_loc, top_session, risk_score, risk_level)
        if docx_file:
            st.download_button("📄 Behaviour Summary (Word)", docx_file,
                file_name=f"BehaviourSummary_{student['name'].replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back to Students", type="primary", key="back_analysis_bottom", use_container_width=True):
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
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("⬅ Back to Students", key="back_dash"):
            go_to("program_students", selected_program=student["program"])
    with col2:
        if st.button("📝 Log Incident", key="log_dash"):
            go_to("incident_log", selected_student_id=student_id)
    with col3:
        if st.button("📈 Full Analysis", key="analysis_dash"):
            go_to("student_analysis", selected_student_id=student_id)
    st.markdown("---")
    incidents = [i for i in st.session_state.incidents if i["student_id"] == student_id]
    critical = [c for c in st.session_state.critical_incidents if c["student_id"] == student_id]
    if not incidents and not critical:
        st.info("📋 No incident data yet. Click 'Log Incident' to start tracking.")
    quick_df = pd.DataFrame(incidents) if incidents else pd.DataFrame()
    crit_df = pd.DataFrame(critical) if critical else pd.DataFrame()
    if not quick_df.empty:
        quick_df["incident_type"] = "Quick"
        quick_df["date_parsed"] = pd.to_datetime(
            quick_df["date"], utc=True, errors="coerce"
        ).dt.tz_localize(None)
    if not crit_df.empty:
        crit_df["incident_type"] = "Critical"
        _crit_dates = crit_df["created_at"] if "created_at" in crit_df.columns else pd.Series(
            [datetime.now().isoformat()] * len(crit_df), index=crit_df.index
        )
        crit_df["date_parsed"] = pd.to_datetime(
            _crit_dates, utc=True, errors="coerce"
        ).dt.tz_localize(None)
        crit_df["severity"] = crit_df["severity"].fillna(5).astype(int) if "severity" in crit_df.columns else 5
        crit_df["time"] = crit_df["ABCH_primary"].apply(
            lambda d: d.get("time", "09:00:00") if isinstance(d, dict) else "09:00:00"
        ) if "ABCH_primary" in crit_df.columns else "09:00:00"
        for _col in ["location", "session", "antecedent", "behaviour_type"]:
            if _col not in crit_df.columns:
                crit_df[_col] = crit_df["ABCH_primary"].apply(
                    lambda d: d.get(_col, "") if isinstance(d, dict) else ""
                ) if "ABCH_primary" in crit_df.columns else ""
    full_df = (
        pd.concat([quick_df, crit_df], ignore_index=True)
        .sort_values("date_parsed", na_position="last")
        if not quick_df.empty or not crit_df.empty
        else pd.DataFrame()
    )
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
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🟥 Red = 3+ incidents that day  ·  🟦 Teal = 1–2 incidents")
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
                st.plotly_chart(fig, use_container_width=True)
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
    st.markdown("### 💡 Quick Recommendations")
    if risk_level == "HIGH":
        st.error("**⚠️ HIGH RISK**\n- Schedule urgent case review\n- Update safety plan\n- Daily check-ins")
    elif risk_level == "MODERATE":
        st.warning("**⚠️ MODERATE RISK**\n- Weekly review\n- Enhanced monitoring\n- Proactive strategies")
    else:
        st.success("**✅ LOW RISK**\n- Maintain supports\n- Continue monitoring\n- Celebrate progress")
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
                from groq import Groq as GroqClient
                import json as _json
                client = GroqClient(api_key=GROQ_KEY)
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
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000, temperature=0.1)
                raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
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
                    st.success(f"✅ Saved to {student['name']}'s record!")
                    st.session_state["ai_extracted_incident"] = None
                    for _key in ["critical_incidents", "incidents"]:
                        if _key in st.session_state:
                            del st.session_state[_key]
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
                        _adm_ext_key = f"placement_extensions_{student['id']}"
                        _adm_exts    = st.session_state.get(_adm_ext_key, [])

                        with st.form(f"ext_form_{student['id']}"):
                            _ae1, _ae2, _ae3 = st.columns([2, 2, 3])
                            with _ae1: _adm_ef = st.date_input("From *", value=None, key=f"adm_ef_{student['id']}")
                            with _ae2: _adm_et = st.date_input("To *",   value=None, key=f"adm_et_{student['id']}")
                            with _ae3: _adm_er = st.text_input("Reason / context *", placeholder="e.g. Extended — positive progress", key=f"adm_er_{student['id']}")
                            if st.form_submit_button("➕ Add Extension"):
                                if _adm_ef and _adm_et and _adm_er.strip():
                                    _adm_exts = _adm_exts + [{"from": _adm_ef.isoformat(), "to": _adm_et.isoformat(), "reason": _adm_er.strip()}]
                                    st.session_state[_adm_ext_key] = _adm_exts
                                    st.success(f"✅ Extension added")
                                    st.rerun()
                                else: st.error("Complete all three fields.")

                        if _adm_exts:
                            for _ei, _ex in enumerate(_adm_exts):
                                try:
                                    _c1, _c2 = st.columns([5, 1])
                                    with _c1:
                                        st.markdown(f"📌 **{datetime.fromisoformat(_ex['from']).strftime('%-d %b %Y')} – {datetime.fromisoformat(_ex['to']).strftime('%-d %b %Y')}** — {_ex['reason']}")
                                    with _c2:
                                        if st.button("❌", key=f"rm_ext_{student['id']}_{_ei}"):
                                            st.session_state[_adm_ext_key] = [e for i, e in enumerate(_adm_exts) if i != _ei]
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
                            incident_count = len([i for i in st.session_state.incidents if i['student_id'] == student['id']])
                            st.caption(f"📋 {incident_count} incidents on record")
                        with col3:
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
            "Remember: a critical incident does not automatically mean L4/L5 — "
            "most incidents sit in the Coping zone (L1–L3)."
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
                                        from groq import Groq as _GC
                                        import json as _jmod
                                        _gc = _GC(api_key=GROQ_KEY)
                                        _canonical_list = [b for b in BEHAVIOUR_TYPES if not b.startswith("---")]
                                        for _amb in _ambiguous:
                                            _ai_prompt = (
                                                "You are classifying a school behaviour incident. "
                                                "Map this behaviour description to the closest label from the list below. "
                                                "Reply with ONLY the exact label text, nothing else.\n\n"
                                                f"Behaviour description: {_amb['raw'][:300]}\n\n"
                                                "Labels:\n" + "\n".join(f"- {l}" for l in _canonical_list)
                                            )
                                            _ai_r = _gc.chat.completions.create(
                                                model="llama-3.3-70b-versatile",
                                                messages=[{"role":"user","content":_ai_prompt}],
                                                max_tokens=60, temperature=0
                                            )
                                            _ai_label = _ai_r.choices[0].message.content.strip().strip("-").strip()
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

    with st.form("ql_form", clear_on_submit=True):
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
                st.markdown(
                    f"<div style='background:#f0fdf4;border:2px solid #22c55e;border-radius:12px;"
                    f"padding:1.1rem 1.5rem;margin-top:.5rem;'>"
                    f"<div style='font-weight:700;color:#15803d;font-size:1rem;margin-bottom:.4rem;'>"
                    f"✅ Incident logged successfully</div>"
                    f"<div style='font-size:.85rem;color:#1e293b;line-height:1.7;'>"
                    f"<b>Student:</b> {_stu_name}<br>"
                    f"<b>Date/Time:</b> {_inc_date.strftime('%-d %b %Y')} at {_inc_time.strftime('%H:%M')}"
                    f" — {_SESSIONS_QL[_sess_lbl]}<br>"
                    f"<b>Location:</b> {_location}<br>"
                    f"<b>Behaviour:</b> {_behaviour}<br>"
                    f"<b>Antecedent:</b> {_antecedent}<br>"
                    f"<b>Severity:</b> <span style='background:{_sc2};color:white;"
                    f"padding:.1rem .4rem;border-radius:4px;font-size:.82rem;'>"
                    f"{_SEV_LABELS_QL[_severity]}</span><br>"
                    f"<b>Logged by:</b> {_staff_opts[_rep_by_id]}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                st.caption("Visible immediately in the student's analysis in the Behaviour Support Tool.")
            except Exception as _e:
                st.error(f"❌ Save failed: {_e}")

    st.markdown("---")
    st.caption("CLC-LBU Portal · Quick Incident Log · For critical incidents use the full Behaviour Support Tool")


def main():
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
    page = st.session_state.current_page
    if not st.session_state.logged_in:
        render_login_page()
        return
    if page == "landing":                   render_landing_page()
    elif page == "program_students":        render_program_students_page()
    elif page == "incident_log":            render_incident_log_page()
    elif page == "critical_incident":       render_critical_incident_page()
    elif page == "review_critical":         render_review_critical_page()
    elif page == "leader_approve_critical": render_leader_approve_critical_page()
    elif page == "student_analysis":        render_student_analysis_page()
    elif page == "student_dashboard":       render_student_dashboard()
    elif page == "admin_portal":            render_admin_portal()
    else:                                   render_landing_page()


if __name__ == "__main__":
    main()
