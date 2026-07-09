"""
CLC Safety & Risk Management Plan Builder  v3 - EXCEL SAVE VERSION
Cowandilla Learning Centre – LBU Portal Tool

PRIVACY-FIRST DESIGN:
✓ Saves to Excel files (YOUR computer/network drive)
✓ No sensitive student data in cloud databases
✓ Upload Excel to resume work
✓ Generates final Word document
✓ Compliant with data governance policies

Steps:
1. Student details
2. Source documents  — school safety plan AND/OR supporting docs (reports, BAP, incident data)
3. AI synthesis     — extracts / generates CLC-contextualised risk rows
4. Risk builder     — staff review, edit, add risks with AI prompts
5. Review           — priority actions, review date
6. Generate         — formatted .docx plan
"""

import streamlit as st

# ── Document Archive integration (fails silently if unavailable) ──────────
try:
    from archive_utils import archive_once, initials_from_name
except Exception:
    def archive_once(*_a, **_k):
        pass
    def initials_from_name(name):
        parts = [p for p in str(name or "").replace("_", " ").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or None

from groq import Groq
import json, os, io, time
from datetime import date, datetime
from copy import deepcopy
import pandas as pd

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Brand colours ──────────────────────────────────────────────────────────────
TEAL        = "#1A7A6E"
TEAL_LIGHT  = "#D6EEEB"
AMBER       = "#D97706"
AMBER_LIGHT = "#FEF3C7"
GREY_DARK   = "#2E4057"
GREY_LIGHT  = "#F2F6F6"
RED_RISK    = "#C0392B"
ORANGE_RISK = "#E67E22"
YELLOW_RISK = "#F1C40F"

# ── Risk matrix ────────────────────────────────────────────────────────────────
LIKELIHOOD_OPTIONS  = ["A – Rare","B – Unlikely","C – Likely sometimes",
                       "D – Likely/frequently","E – Almost certain"]
CONSEQUENCE_OPTIONS = ["1 – Insignificant","2 – Minor","3 – Moderate",
                       "4 – Major","5 – Catastrophic"]

RISK_MATRIX = {
    ("E","5"):"EXTREME",("E","4"):"EXTREME",("E","3"):"EXTREME",("E","2"):"HIGH",("E","1"):"HIGH",
    ("D","5"):"EXTREME",("D","4"):"EXTREME",("D","3"):"HIGH",  ("D","2"):"HIGH",("D","1"):"MODERATE",
    ("C","5"):"EXTREME",("C","4"):"EXTREME",("C","3"):"HIGH",  ("C","2"):"MODERATE",("C","1"):"LOW",
    ("B","5"):"HIGH",   ("B","4"):"HIGH",   ("B","3"):"MODERATE",("B","2"):"LOW",("B","1"):"LOW",
    ("A","5"):"HIGH",   ("A","4"):"HIGH",   ("A","3"):"MODERATE",("A","2"):"LOW",("A","1"):"LOW",
}
RISK_COLOURS = {"EXTREME":RED_RISK,"HIGH":ORANGE_RISK,"MODERATE":YELLOW_RISK,"LOW":"#27AE60"}

# ── CLC standard risk categories (from revised plan) ──────────────────────────
CLC_RISK_TEMPLATES = [
    "Absconding from CLC grounds",
    "Fence / boundary climbing following peer rejection or negative feedback",
    "High-risk behaviour in the community during absconding (road safety)",
    "Verbal aggression toward staff, peers, and/or family",
    "Rapid behavioural escalation resulting in flight following peer interaction",
    "Staff safety during community follow",
    "Physical aggression toward staff or peers",
    "Property damage",
    "Parent / carer handover escalation",
    "Self-harm or self-injurious behaviour",
    "Elopement within CLC grounds",
    "Tree / structure climbing at height",
    "Other (describe)",
]

BLANK_RISK = {
    "issue_title": "", "issue_detail": "", "behaviour_descriptors": "",
    "function": "", "likelihood": "D – Likely/frequently",
    "consequence": "3 – Moderate", "proactive": "", "procedure": "",
    "clc_notes": "", "from_school": False, "from_docs": False,
}

def normalize_risk(risk: dict) -> dict:
    """Convert all risk fields to proper types (lists→strings, etc)."""
    r = {**risk}
    # Convert list fields to newline-separated strings
    for field in ["behaviour_descriptors", "proactive", "procedure"]:
        if isinstance(r.get(field), list):
            r[field] = "\n".join(str(x) for x in r[field] if x)
        else:
            r[field] = str(r.get(field, "")).strip()
    # Ensure string fields are strings
    for field in ["issue_title", "issue_detail", "function", "clc_notes"]:
        r[field] = str(r.get(field, "")).strip()
    return r

STEPS = ["1 · Student","2 · Documents","3 · AI Synthesis",
         "4 · Build Risks","5 · Review","6 · Polish & Enhance","7 · Generate"]

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_client():
    key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY",""))
    if not key:
        st.error("⚠️  GROQ_API_KEY not found in Render environment variables.")
        st.stop()
    return Groq(api_key=key)

def extract_docx_text(uploaded_file) -> str:
    """Extract plain text from an uploaded .docx or .pdf file."""
    name = getattr(uploaded_file, "name", "").lower()
    try:
        if name.endswith(".pdf"):
            try:
                import fitz  # PyMuPDF — already installed for timetable
                raw = uploaded_file.read()
                doc = fitz.open(stream=raw, filetype="pdf")
                lines = [page.get_text() for page in doc]
                doc.close()
                return "\n".join(lines)
            except Exception as e:
                return f"[PDF extraction error: {e}]"
        else:
            doc = DocxDocument(io.BytesIO(uploaded_file.read()))
            lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        cell_text = " ".join(
                            p.text.strip() for p in cell.paragraphs if p.text.strip()
                        )
                        if cell_text:
                            lines.append(cell_text)
            return "\n".join(lines)
    except Exception as e:
        return f"[Extraction error: {e}]"

def groq_call(prompt: str, max_tokens: int = 2000, timeout_seconds: int = 60) -> str:
    """Call Groq API with timeout protection."""
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            messages=[{"role":"user","content":prompt}],
            timeout=timeout_seconds
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        if "timeout" in str(e).lower():
            raise Exception(f"AI request timed out after {timeout_seconds}s")
        raise

def check_language_objectivity(text: str) -> list:
    """
    Scan text for subjective / non-observable language.
    Returns list of (flagged_phrase, suggestion) tuples.
    """
    import re
    flags = [
        # Speed/pace
        (r'\bat speed\b',          '"at speed" — describe what was observed instead, e.g. "running out of the supervised area"'),
        (r'\bhigh.?speed\b',       '"high speed" — subjective. Describe the observable action'),
        (r'\bquickly\b',           '"quickly" — subjective. Name the trigger for action instead'),
        (r'\brapidly\b',           '"rapidly" — subjective. Describe the specific observable behaviour'),
        (r'\bswiftly\b',           '"swiftly" — subjective. Use an observable anchor instead'),
        # Distance/proximity
        (r"\barm'?s\s+reach\b",    '"arm\'s reach" — ambiguous. Use positional language: "positioned between student and fence"'),
        (r'\bclose proximity\b',   '"close proximity" — vague. Define position: "within 1 metre of student at all times"'),
        (r'\bnearby\b',            '"nearby" — vague distance. Specify: "within line-of-sight" or name the location'),
        # Behaviour descriptors
        (r'\bchallenging behaviour\b', '"challenging behaviour" — not observable. Name the specific behaviour'),
        (r'\bdysregulated\b',      '"dysregulated" — clinical inference. Describe what is observed: "shouting, throwing objects, moving toward fence"'),
        (r'\bescalating\b',        '"escalating" — subjective judgement. Describe the observable signs instead'),
        (r'\baggressively\b',      '"aggressively" — subjective. Describe the act: "struck with open hand", "threw chair"'),
        (r'\bviolently\b',         '"violently" — subjective intensity. Describe the observable action'),
        # Time qualifiers
        (r'\bstraight away\b',     '"straight away" — ambiguous timing. Name the trigger: "as soon as student moves toward fence"'),
        (r'\bimmediately\b',       '"immediately" — ambiguous. Specify the trigger for the action'),
        # Intervention language
        (r'\bde-?escalat',         '"de-escalation" — vague strategy. Name the specific technique: "reduce verbal demands", "offer choice", "move to quieter space"'),
        (r'\bappropriate(ly)?\b',  '"appropriate" — subjective. State what the appropriate action actually is'),
        (r'\badequate\b',          '"adequate" — subjective. Define the specific standard required'),
        (r'\blow.?arousal\b',      '"low arousal" — professional shorthand. Define for all staff: "calm tone, no raised voice, no direct commands, offer choice"'),
        (r'\bmanage the situation\b', '"manage the situation" — vague. List the specific steps'),
        (r'\brespond appropriately\b', '"respond appropriately" — vague. State the specific response'),
    ]
    found = []
    text_lower = text.lower()
    for pattern, suggestion in flags:
        if re.search(pattern, text_lower):
            found.append(suggestion)
    return found


def compute_risk_level(likelihood: str, consequence: str) -> str:
    """
    Compute risk level from likelihood and consequence.
    Handles various input formats (full strings, partial strings, or integers from Excel).
    """
    # Convert to string if integer
    likelihood = str(likelihood) if not isinstance(likelihood, str) else likelihood
    consequence = str(consequence) if not isinstance(consequence, str) else consequence
    
    # Extract just the letter/number code
    # Handles "D – Likely/frequently", "D", or just "D "
    if "–" in likelihood:
        l = likelihood.split("–")[0].strip().split(" ")[0]
    else:
        l = likelihood.strip().split(" ")[0]
    
    if "–" in consequence:
        c = consequence.split("–")[0].strip().split(" ")[0]
    else:
        c = consequence.strip().split(" ")[0]
    
    return RISK_MATRIX.get((l, c), "HIGH")

def risk_colour(level): return RISK_COLOURS.get(level,"#888")

def normalize_risk_rating(value: str, options: list) -> str:
    """
    Normalize a risk rating value that may have been truncated by Excel.
    E.g., "3" or "3.0" → "3 – Moderate"
    """
    value = str(value).strip()
    
    # If it's already a full option, return it
    if value in options:
        return value
    
    # Try to match by the first character/number
    for option in options:
        if option.startswith(value.split()[0]):
            return option
    
    # If no match, return the value as-is
    return value

# ══════════════════════════════════════════════════════════════════════════════
# EXCEL SAVE/LOAD FUNCTIONS - Privacy-first data handling
# ══════════════════════════════════════════════════════════════════════════════

def create_excel_save():
    """
    Create Excel file with all current data.
    Returns BytesIO buffer ready for download.
    """
    # Sheet 1: Student Details
    student = st.session_state.student
    student_df = pd.DataFrame([{
        'Field': k,
        'Value': v
    } for k, v in student.items()])
    
    # Sheet 2: Risks
    risks = st.session_state.risks
    if risks:
        risks_df = pd.DataFrame(risks)
    else:
        risks_df = pd.DataFrame(columns=[
            'issue_title', 'issue_detail', 'behaviour_descriptors',
            'function', 'likelihood', 'consequence',
            'proactive', 'procedure', 'clc_notes', 'from_school', 'from_docs'
        ])
    
    # Sheet 3: Final Details
    final_df = pd.DataFrame([{
        'Field': 'priority_actions',
        'Value': st.session_state.get('priority_actions', '')
    }, {
        'Field': 'review_date',
        'Value': st.session_state.get('review_date', '')
    }, {
        'Field': 'mode',
        'Value': st.session_state.get('mode', 'wizard')
    }, {
        'Field': 'step',
        'Value': st.session_state.get('step', 1)
    }, {
        'Field': 'synthesis_done',
        'Value': st.session_state.get('synthesis_done', False)
    }])
    
    # Sheet 4: Uploaded Documents (truncated for size)
    school_plan_text = st.session_state.get('school_plan_text', '')
    docs_data = [{
        'Document': 'School Safety Plan',
        'Text': school_plan_text[:5000] + ('...' if len(school_plan_text) > 5000 else '')
    }]
    
    for i, doc in enumerate(st.session_state.get('support_docs', [])):
        docs_data.append({
            'Document': f"{doc.get('doc_type', 'Unknown')}: {doc.get('name', 'Unnamed')}",
            'Text': doc.get('text', '')[:5000] + ('...' if len(doc.get('text', '')) > 5000 else '')
        })
    
    docs_df = pd.DataFrame(docs_data)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        student_df.to_excel(writer, sheet_name='Student Details', index=False)
        risks_df.to_excel(writer, sheet_name='Risks', index=False)
        final_df.to_excel(writer, sheet_name='Final Details', index=False)
        docs_df.to_excel(writer, sheet_name='Uploaded Documents', index=False)
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output

def load_excel_save(excel_file):
    """
    Load data from Excel file back into session state.
    Returns (success: bool, message: str)
    """
    try:
        # Read all sheets
        excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
        
        # Sheet 1: Student Details
        if 'Student Details' in excel_data:
            try:
                student_df = excel_data['Student Details']
                student_dict = dict(zip(student_df['Field'], student_df['Value']))
                
                # Handle NaN values and convert to strings
                for k in student_dict:
                    if pd.isna(student_dict[k]):
                        student_dict[k] = ''
                    else:
                        student_dict[k] = str(student_dict[k])
                
                st.session_state.student = student_dict
            except Exception as e:
                return False, f"Error loading student details: {str(e)}"
        
        # Sheet 2: Risks
        if 'Risks' in excel_data:
            try:
                risks_df = excel_data['Risks']
                
                # Convert DataFrame to list of dicts
                risks = []
                for _, row in risks_df.iterrows():
                    risk_dict = row.to_dict()
                    # Handle NaN values
                    for k in risk_dict:
                        if k in ['from_school', 'from_docs']:
                            risk_dict[k] = bool(risk_dict[k]) if not pd.isna(risk_dict[k]) else False
                        else:
                            risk_dict[k] = str(risk_dict[k]) if not pd.isna(risk_dict[k]) else ''
                    
                    # Normalize likelihood and consequence (Excel may have truncated them)
                    if 'likelihood' in risk_dict and risk_dict['likelihood']:
                        risk_dict['likelihood'] = normalize_risk_rating(risk_dict['likelihood'], LIKELIHOOD_OPTIONS)
                    if 'consequence' in risk_dict and risk_dict['consequence']:
                        risk_dict['consequence'] = normalize_risk_rating(risk_dict['consequence'], CONSEQUENCE_OPTIONS)
                    
                    risks.append(risk_dict)
                
                st.session_state.risks = risks
            except Exception as e:
                return False, f"Error loading risks: {str(e)}"
        
        # Sheet 3: Final Details
        if 'Final Details' in excel_data:
            try:
                final_df = excel_data['Final Details']
                final_dict = dict(zip(final_df['Field'], final_df['Value']))
                
                st.session_state.priority_actions = str(final_dict.get('priority_actions', '')) if not pd.isna(final_dict.get('priority_actions')) else ''
                st.session_state.review_date = str(final_dict.get('review_date', '')) if not pd.isna(final_dict.get('review_date')) else ''
                st.session_state.mode = str(final_dict.get('mode', 'wizard')) if not pd.isna(final_dict.get('mode')) else 'wizard'
                
                # Safely convert step to int
                try:
                    step_val = final_dict.get('step', 1)
                    st.session_state.step = int(float(step_val)) if not pd.isna(step_val) else 1
                except:
                    st.session_state.step = 1
                
                # Safely convert synthesis_done to bool
                try:
                    synth_val = final_dict.get('synthesis_done', False)
                    st.session_state.synthesis_done = bool(synth_val) if not pd.isna(synth_val) else False
                except:
                    st.session_state.synthesis_done = False
            except Exception as e:
                return False, f"Error loading final details: {str(e)}"
        
        # Sheet 4: Uploaded Documents
        if 'Uploaded Documents' in excel_data:
            try:
                docs_df = excel_data['Uploaded Documents']
                
                # First row is usually school plan
                if len(docs_df) > 0:
                    school_row = docs_df.iloc[0]
                    st.session_state.school_plan_text = str(school_row['Text']) if not pd.isna(school_row['Text']) else ''
                
                # Rest are support docs
                support_docs = []
                for i in range(1, len(docs_df)):
                    doc_row = docs_df.iloc[i]
                    doc_name = str(doc_row['Document']) if not pd.isna(doc_row['Document']) else 'Unknown'
                    
                    # Parse doc type from "Type: Name" format
                    if ':' in doc_name:
                        parts = doc_name.split(':', 1)
                        doc_type = parts[0].strip()
                        name = parts[1].strip()
                    else:
                        doc_type = 'Other'
                        name = doc_name
                    
                    support_docs.append({
                        'name': name,
                        'doc_type': doc_type,
                        'text': str(doc_row['Text']) if not pd.isna(doc_row['Text']) else ''
                    })
                
                st.session_state.support_docs = support_docs
            except Exception as e:
                # Don't fail if uploaded docs fail to load
                st.session_state.support_docs = []
        
        student_name = st.session_state.student.get('name', 'Unknown')
        risk_count = len(st.session_state.risks)
        return True, f"✅ Successfully loaded: {student_name} with {risk_count} risk(s)"
        
    except Exception as e:
        return False, f"❌ Failed to read Excel file: {str(e)[:200]}"

# ══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "step": 1,
        "mode": "wizard",            # "wizard" or "express"
        "student": {
            "name":"","dob":"","age":"","edsas":"","program":"JP",
            "home_school":"","key_staff":"","clc_context":"",
            "plan_date": str(date.today()),"medical_notes":"",
        },
        "school_plan_text": "",
        "support_docs": [],          # list of {name, text, doc_type}
        "risks": [],
        "current_risk": 0,
        "ai_context_cache": {},
        "synthesis_done": False,
        "priority_actions": "",
        "review_date": "",
        "file_loaded": False,        # Flag to prevent reload loop
        "last_loaded_file": None,    # Track which file was loaded
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# AI FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def ai_extract_from_school_plan(plan_text: str, student_name: str) -> list:
    """Extract risk rows from a school safety plan."""
    prompt = f"""You are analysing a Safety and Risk Management Plan from a mainstream school for {student_name}.

CRITICAL RULES for CLC adaptation:
- Identify what the student DOES that is risky — describe observable behaviours only
- Do NOT describe triggers or function in the risk description — those belong in proactive strategies
- Use language: "program option for students with educational exclusion" not "specialist setting"
- Describe behaviour specifically: fence climbing, running onto roads, darting across traffic, verbal aggression — not vague terms like "challenging behaviour"
LANGUAGE OBJECTIVITY — MANDATORY:
Every word in this plan must be observable and measurable. A different staff member reading this plan must interpret it identically.
NEVER USE subjective terms — replace with observable descriptions:
  ✗ "high speed / at speed / quickly / rapidly / fast" → ✓ describe what is observed: "running out of the supervised area", "ran onto the road"
  ✗ "arm's reach / close proximity / nearby" → ✓ "within arm's length" is still vague — use positional descriptions: "positioned between student and fence boundary", "physically proximate during all peer interactions"
  ✗ "aggressively / violently / severely" → ✓ describe the observable act: "struck staff with open hand", "threw chair across room"
  ✗ "immediately / straight away / quickly respond" → ✓ specify the trigger for action: "as soon as student moves toward fence", "once verbal engagement ceases"
  ✗ "challenging behaviour / dysregulated / escalating" → ✓ name the specific behaviour: "climbing fence", "running toward road", "throwing objects"
  ✗ "de-escalation strategies" → ✓ name the specific strategy: "offer sensory break", "reduce verbal demands", "move to quieter space"
  ✗ "appropriate supervision / adequate support" → ✓ "staff positioned between student and fence at all times", "one staff member maintains line-of-sight to student"
  ✗ "respond appropriately / manage the situation" → ✓ "radio leadership immediately", "retrieve vehicle keys from program office"
  ✗ "low arousal approach" → ✓ "calm tone, no raised voice, no direct commands, offer choice"
If you use a measurement, define it: not "close proximity" but "within arm's length (approx. 60cm)"
Every procedure step must be a specific, named action — not a category of action.

Extract each risk row and return as a JSON array. Each object must have:
- issue_title: specific behaviour name (e.g. "Absconding from school grounds")
- issue_detail: 2-3 sentences describing what the student does — observable behaviour only
- behaviour_descriptors: dot-point list of specific observable behaviours (as string, one per line starting with •)
- function: function of behaviour if stated (e.g. "Avoidance – adult and peer")
- likelihood: code A/B/C/D/E (default "D")
- consequence: code 1/2/3/4/5 (default "3")
- proactive: proactive strategies as string, one per line starting with •
- procedure: reactive procedures as string with ### Subheadings and • bullets

Return ONLY valid JSON array. No markdown fences, no preamble.

PLAN TEXT:
{plan_text[:8000]}"""
    try:
        raw = groq_call(prompt, 3000)
        raw = raw.replace("```json","").replace("```","").strip()
        
        # Clean up control characters
        import re
        raw = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', raw)
        
        risks = json.loads(raw)
        for r in risks:
            r["from_school"] = True
            r["from_docs"]   = False
            r["clc_notes"]   = ""
            if "behaviour_descriptors" not in r:
                r["behaviour_descriptors"] = ""
        return risks
    except Exception as e:
        st.warning(f"School plan extraction issue ({e}). You can enter risks manually.")
        return []


def ai_synthesise_from_docs(support_docs: list, student: dict) -> list:
    """Generate risk rows from a collection of uploaded support documents."""
    combined = "\n\n".join(
        f"=== {d['doc_type'].upper()}: {d['name']} ===\n{d['text'][:3000]}"
        for d in support_docs
    )
    student_ctx = f"Student: {student['name']}, Age {student.get('age','')}, Program {student.get('program','')}"
    prompt = f"""You are a behaviour support specialist analysing documents about {student['name']} to identify specific safety risks for a CLC Safety & Risk Management Plan.

MOST IMPORTANT RULE: Only identify risks that are directly evidenced in the documents provided below.
Do NOT include risks because they are common or because they appeared in another student's plan.
Do NOT invent behaviours. Every risk must trace to specific content in the documents.
LANGUAGE OBJECTIVITY — MANDATORY:
Every word in this plan must be observable and measurable. A different staff member reading this plan must interpret it identically.
NEVER USE subjective terms — replace with observable descriptions:
  ✗ "high speed / at speed / quickly / rapidly / fast" → ✓ describe what is observed: "running out of the supervised area", "ran onto the road"
  ✗ "arm's reach / close proximity / nearby" → ✓ "within arm's length" is still vague — use positional descriptions: "positioned between student and fence boundary", "physically proximate during all peer interactions"
  ✗ "aggressively / violently / severely" → ✓ describe the observable act: "struck staff with open hand", "threw chair across room"
  ✗ "immediately / straight away / quickly respond" → ✓ specify the trigger for action: "as soon as student moves toward fence", "once verbal engagement ceases"
  ✗ "challenging behaviour / dysregulated / escalating" → ✓ name the specific behaviour: "climbing fence", "running toward road", "throwing objects"
  ✗ "de-escalation strategies" → ✓ name the specific strategy: "offer sensory break", "reduce verbal demands", "move to quieter space"
  ✗ "appropriate supervision / adequate support" → ✓ "staff positioned between student and fence at all times", "one staff member maintains line-of-sight to student"
  ✗ "respond appropriately / manage the situation" → ✓ "radio leadership immediately", "retrieve vehicle keys from program office"
  ✗ "low arousal approach" → ✓ "calm tone, no raised voice, no direct commands, offer choice"
If you use a measurement, define it: not "close proximity" but "within arm's length (approx. 60cm)"
Every procedure step must be a specific, named action — not a category of action.

CLC CONTEXT (apply only where relevant to evidenced risks):
- CLC is a program option for students with educational exclusion in Adelaide SA
- Small group setting; playground adjacent to carpark via climbable fence; busy roads nearby
- TAC, CARL, DCP, IRMS processes apply; trauma-informed relational practice

{student_ctx}
Medical/context: {student.get('medical_notes','')}
Staff notes: {student.get('clc_context','')}

DOCUMENTS:
{combined}

Based ONLY on the above documents, identify the specific safety risks for {student['name']}.
If the documents do not describe absconding — do not include it.
If the documents do not describe aggression — do not include it.
Only include what is actually described about this student.

Return a JSON array. Each object:
- issue_title: behaviour-focused title derived from documents
- issue_detail: 2-3 sentences of what THIS student does — sourced from documents only
- behaviour_descriptors: specific observable behaviours from documents, one per line starting with •
- function: function of behaviour as evidenced
- likelihood: A/B/C/D/E based on frequency described in documents
- consequence: 1/2/3/4/5 based on severity described in documents
- proactive: CLC-specific proactive strategies with ### subheadings and • bullets
- procedure: reactive procedures with ### subheadings and • bullets

Return ONLY valid JSON array. No markdown, no preamble."""
    try:
        raw = groq_call(prompt, 4000)
        raw = raw.replace("```json","").replace("```","").strip()
        
        # Clean up control characters
        import re
        raw = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', raw)
        
        risks = json.loads(raw)
        for r in risks:
            r["from_school"] = False
            r["from_docs"]   = True
            r["clc_notes"]   = ""
            if "behaviour_descriptors" not in r:
                r["behaviour_descriptors"] = ""
        return risks
    except Exception as e:
        st.warning(f"Document synthesis issue. You can review and add risks manually.")
        return []


def ai_contextualise(risk: dict, student: dict) -> str:
    """Generate CLC contextualisation advisory for a school-plan risk."""
    prompt = f"""You are a behaviour support specialist helping CLC (Cowandilla Learning Centre) staff adapt a school safety plan risk for their specialist setting.
LANGUAGE OBJECTIVITY — MANDATORY:
Every word in this plan must be observable and measurable. A different staff member reading this plan must interpret it identically.
NEVER USE subjective terms — replace with observable descriptions:
  ✗ "high speed / at speed / quickly / rapidly / fast" → ✓ describe what is observed: "running out of the supervised area", "ran onto the road"
  ✗ "arm's reach / close proximity / nearby" → ✓ "within arm's length" is still vague — use positional descriptions: "positioned between student and fence boundary", "physically proximate during all peer interactions"
  ✗ "aggressively / violently / severely" → ✓ describe the observable act: "struck staff with open hand", "threw chair across room"
  ✗ "immediately / straight away / quickly respond" → ✓ specify the trigger for action: "as soon as student moves toward fence", "once verbal engagement ceases"
  ✗ "challenging behaviour / dysregulated / escalating" → ✓ name the specific behaviour: "climbing fence", "running toward road", "throwing objects"
  ✗ "de-escalation strategies" → ✓ name the specific strategy: "offer sensory break", "reduce verbal demands", "move to quieter space"
  ✗ "appropriate supervision / adequate support" → ✓ "staff positioned between student and fence at all times", "one staff member maintains line-of-sight to student"
  ✗ "respond appropriately / manage the situation" → ✓ "radio leadership immediately", "retrieve vehicle keys from program office"
  ✗ "low arousal approach" → ✓ "calm tone, no raised voice, no direct commands, offer choice"
If you use a measurement, define it: not "close proximity" but "within arm's length (approx. 60cm)"
Every procedure step must be a specific, named action — not a category of action.

CLC context:
- Program option for students with educational exclusion (not "specialist centre")
- Small group setting with frequent externalising behaviour from other students
- Playground adjacent to carpark via climbable fence; Jenkins Rd, Marion Rd, Sir Donald Bradman Drive within 100m; South Road ~15 min on foot
- All staff carry walkie talkies; program vehicle available; school mobile for SAPOL contact
- TAC, CARL, DCP, IRMS processes apply
- Trauma-informed, relational practice; movement-based interventions valued
- Risk descriptions must focus on what the student DOES — not why (triggers go in proactive strategies)

Student: {student.get('name','')}, Age {student.get('age','')}, Program {student.get('program','')}
Key staff: {student.get('key_staff','')}
CLC context: {student.get('clc_context','')}
Medical notes: {student.get('medical_notes','')}

SCHOOL RISK TO ADAPT:
Title: {risk.get('issue_title','')}
Detail: {risk.get('issue_detail','')}
School proactive: {risk.get('proactive','')[:500]}
School procedure: {risk.get('procedure','')[:500]}

Write a SHORT advisory note (150-250 words) for the staff member that:
1. Highlights what is DIFFERENT about this risk at CLC vs the school (environment, roads, peer cohort, staffing, processes)
2. Asks 3 specific CLC-contextualising questions (e.g. "Has this been observed at CLC?", "Does the fence/carpark create additional risk?")
3. Flags 2 CLC-specific additions the school plan likely missed

Keep it practical and direct. Do not repeat school plan content verbatim."""
    try:
        return groq_call(prompt, 500)
    except Exception as e:
        return f"[AI unavailable: {e}]"


def ai_generate_strategies(risk: dict, student: dict) -> dict:
    """Generate CLC-specific proactive strategies and reactive procedures."""
    
    # Simpler, more reliable prompt
    prompt = f"""You are writing a Safety & Risk Management Plan for Cowandilla Learning Centre (CLC LBU).

Student: {student.get('name','')}, Age {student.get('age','')}, Program {student.get('program','')}
Risk: {risk.get('issue_title','')}
Behaviour: {risk.get('issue_detail','')}

Generate TWO sections:

1. Proactive strategies (what we do BEFORE the behaviour happens):
Write 4-6 strategies with ### subheadings. Use specific, observable actions.
Format: ### Heading
• strategy
• strategy

2. Reactive procedures (what we do IF the behaviour happens):
Write 3-4 scenarios with ### subheadings. Use specific, observable steps.
Format: ### If [scenario]
• step
• step

Return ONLY valid JSON (no markdown fences):
{{"proactive": "### Heading\\n• strategy\\n• strategy", "procedure": "### If scenario\\n• step\\n• step"}}"""
    
    try:
        raw = groq_call(prompt, 1000, timeout_seconds=25)
        raw = raw.replace("```json","").replace("```","").strip()
        
        # Clean up control characters
        import re
        raw = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', raw)
        
        # Try to extract JSON if wrapped in text
        if not raw.startswith("{"):
            json_start = raw.find("{")
            if json_start != -1:
                raw = raw[json_start:]
        
        result = json.loads(raw)
        
        # Validate we got the expected fields
        if "proactive" in result and "procedure" in result:
            return result
        else:
            st.warning("⚠️ AI response incomplete. You can enter strategies manually.")
            return {"proactive": "", "procedure": ""}
            
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ AI formatting issue. You can enter strategies manually or try again.")
        return {"proactive": "", "procedure": ""}
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            st.error("⚠️ AI took too long to respond. You can enter strategies manually.")
        else:
            st.warning("⚠️ AI generation failed. Please enter strategies manually or try again in a moment.")
        return {"proactive": "", "procedure": ""}
        return {"proactive":"","procedure":""}


def ai_generate_priority_actions(risks: list, student: dict) -> str:
    """Generate a priority actions list from the complete risk set."""
    risk_summary = "\n".join(f"- {r['issue_title']} ({compute_risk_level(r['likelihood'],r['consequence'])})"
                             for r in risks if r.get('issue_title'))
    prompt = f"""You are completing a CLC Safety & Risk Management Plan for {student.get('name','')}.

Risks identified:
{risk_summary}

CLC context: {student.get('clc_context','')}
Medical notes: {student.get('medical_notes','')}

Generate a concise priority actions list (8-12 items) for what must happen after this plan is signed.
Format: one action per line starting with •
Include: TAC meeting, fence/environment audit, staff sign-off, BAP update, CARL/DCP notifications, medication considerations if relevant, review date.
Order by urgency (URGENT items first).
Return plain text only — no JSON, no headers."""
    try:
        return groq_call(prompt, 500)
    except Exception:
        return "• Schedule TAC meeting\n• Conduct fence/gate safety audit\n• Ensure all staff sign this plan"


def ai_enhance_text(text: str, mode: str = "both") -> str:
    """
    Enhance text using AI.
    mode: "language" (just improve language), "expand" (add detail), "both" (improve + expand)
    """
    if not text or not text.strip():
        return text
    
    mode_instruction = {
        "language": "Improve the language and clarity while keeping it brief and professional. Fix any grammatical issues.",
        "expand": "Expand this with more detail, examples, and professional language. Make it comprehensive but concise.",
        "both": "Improve the professional language AND expand with relevant detail and examples. Make it polished and comprehensive."
    }.get(mode, "Improve the language and clarity.")
    
    prompt = f"""You are helping refine a Safety & Risk Management Plan section for CLC LBU.

Original text:
{text}

Task: {mode_instruction}

Return ONLY the improved text. No explanations, no markdown, no quotes. Just the improved text ready to use in a professional document."""

    try:
        result = groq_call(prompt, max_tokens=1500, timeout_seconds=25)
        return result.strip()
    except Exception as e:
        st.warning(f"⚠️ Enhancement failed: {str(e)[:50]}. Keeping original text.")
        return text


def ai_generate_full_plan(student: dict, school_plan_text: str, support_docs: list) -> dict:
    """
    Express path — generate a complete, ready-to-use plan directly from all documents.
    Returns {"risks": [...], "priority_actions": "...", "review_date": "..."}.
    """
    combined_docs = ""
    if school_plan_text:
        combined_docs += f"=== SCHOOL SAFETY & RISK PLAN ===\n{school_plan_text[:5000]}\n\n"
    for d in support_docs:
        combined_docs += f"=== {d['doc_type'].upper()}: {d['name']} ===\n{d['text'][:2500]}\n\n"

    # Warn if documents are very thin
    if len(combined_docs.strip()) < 200:
        return {"error": "Documents provided contain very little text. Please check the files uploaded and try again.", "risks": [], "priority_actions": "", "review_date": ""}

    prompt = f"""You are an expert behaviour support specialist writing a Safety & Risk Management Plan for Cowandilla Learning Centre (CLC) LBU, Adelaide SA.

IMPORTANT — SITE NAME: This plan is for COWANDILLA LEARNING CENTRE (CLC), the Learning and Behaviour Unit.
This is NOT Cowandilla Primary School. These are two separate schools in the same suburb.
Some students at CLC have Cowandilla Primary School as their home school — this is normal and correct.
The plan must always read "Cowandilla Learning Centre" as the placement site regardless of home school.

STUDENT DETAILS PROVIDED BY STAFF:
Name: {student['name']}
Age: {student.get('age','—')}  DOB: {student.get('dob','—')}  EDSAS: {student.get('edsas','—')}
Program: {student.get('program','—')}  Home school: {student.get('home_school','—')}
Key staff: {student.get('key_staff','—')}
Additional context: {student.get('clc_context','')}
Medical/background: {student.get('medical_notes','')}

STUDENT DETAIL EXTRACTION TASK:
If any of the above are blank or "—", search the documents and extract:
- Full name (confirm or correct spelling)
- Date of birth (DD/MM/YYYY format)
- Age
- EDSAS ID (numeric student ID, may be labelled EDSAS, student ID, or similar)
- Home school (the school they normally attend — this will NOT be Cowandilla Learning Centre)
Include extracted values in the student_details section of your response.

═══════════════════════════════════════════════
MOST IMPORTANT RULE:
ONLY identify risks that are directly evidenced in the documents provided.
DO NOT include risks because they are common or appeared in another student's plan.
DO NOT invent behaviours. Every risk must trace to the provided documents.
═══════════════════════════════════════════════

CLC CONTEXT (apply only where relevant to evidenced risks):
- Program option for students with educational exclusion — NOT a specialist centre
- Small group setting with frequent externalising behaviour from other students
- Playground adjacent to carpark via climbable fence; Marion Rd/Sir Donald Bradman Dr within 100m
- All staff carry walkie talkies; program vehicle available; school mobile for SAPOL contact
- TAC, CARL, DCP, IRMS, ED155/ED165 apply; trauma-informed relational practice

RISK DESCRIPTION RULES:
- Describe what THIS student DOES — observable behaviour only from the documents
- Do NOT include triggers or function in the risk description
- Use specific language from the documents (e.g. "threw chairs", "bit staff", "ran into traffic")
- Rate based on actual severity and frequency described in the documents
LANGUAGE OBJECTIVITY — MANDATORY:
Every word in this plan must be observable and measurable. A different staff member reading this plan must interpret it identically.
NEVER USE subjective terms — replace with observable descriptions:
  ✗ "high speed / at speed / quickly / rapidly / fast" → ✓ describe what is observed: "running out of the supervised area", "ran onto the road"
  ✗ "arm's reach / close proximity / nearby" → ✓ "within arm's length" is still vague — use positional descriptions: "positioned between student and fence boundary", "physically proximate during all peer interactions"
  ✗ "aggressively / violently / severely" → ✓ describe the observable act: "struck staff with open hand", "threw chair across room"
  ✗ "immediately / straight away / quickly respond" → ✓ specify the trigger for action: "as soon as student moves toward fence", "once verbal engagement ceases"
  ✗ "challenging behaviour / dysregulated / escalating" → ✓ name the specific behaviour: "climbing fence", "running toward road", "throwing objects"
  ✗ "de-escalation strategies" → ✓ name the specific strategy: "offer sensory break", "reduce verbal demands", "move to quieter space"
  ✗ "appropriate supervision / adequate support" → ✓ "staff positioned between student and fence at all times", "one staff member maintains line-of-sight to student"
  ✗ "respond appropriately / manage the situation" → ✓ "radio leadership immediately", "retrieve vehicle keys from program office"
  ✗ "low arousal approach" → ✓ "calm tone, no raised voice, no direct commands, offer choice"
If you use a measurement, define it: not "close proximity" but "within arm's length (approx. 60cm)"
Every procedure step must be a specific, named action — not a category of action.

DOCUMENTS:
{combined_docs[:14000]}

Based ONLY on the above documents, generate a complete plan for {student['name']}.
Include only risks clearly evidenced. Typically 3–6 risks.

Return JSON only (no markdown fences):
{{
  "student_details": {{
    "name": "confirmed full name from documents",
    "dob": "date of birth DD/MM/YYYY from documents, or blank if not found",
    "age": "age from documents, or blank",
    "edsas": "EDSAS ID from documents, or blank",
    "home_school": "home school from documents — NOT Cowandilla Learning Centre"
  }},
  "risks": [
    {{
      "issue_title": "specific behaviour-focused title",
      "issue_detail": "2-3 sentences of what {student['name']} does — from documents only",
      "behaviour_descriptors": "• specific descriptor\n• descriptor\n• descriptor",
      "function": "function of behaviour from documents",
      "likelihood": "A – Rare / B – Unlikely / C – Likely sometimes / D – Likely/frequently / E – Almost certain",
      "consequence": "1 – Insignificant / 2 – Minor / 3 – Moderate / 4 – Major / 5 – Catastrophic",
      "proactive": "### Category\n• strategy\n• strategy\n\n### Category\n• strategy",
      "procedure": "### If early warning signs:\n• step\n\n### If [scenario]:\n• step\n\n### Post-incident:\n• step",
      "clc_notes": "CLC-specific context if relevant to evidenced risks",
      "from_school": false,
      "from_docs": true
    }}
  ],
  "priority_actions": "• action\n• action\n• action\n• action\n• action",
  "review_date": "approx 8 weeks from today"
}}

Each risk: 6-8 proactive strategies across 2-3 subheadings; procedures in 3-5 scenario sections."""

    try:
        # Simpler, shorter prompt to avoid timeouts
        simple_prompt = f"""You are writing a Safety & Risk Management Plan for CLC LBU.

STUDENT: {student['name']} (Age {student.get('age','—')}, EDSAS {student.get('edsas','—')})

DOCUMENTS PROVIDED:
{combined_docs[:12000]}

TASK: Extract risks directly mentioned in the documents. Do NOT invent risks.

For each risk found, provide:
- Title (what the student does)
- Detail (2-3 sentences from documents)
- Descriptors (bullet list of specific behaviours)
- Likelihood (A-E: Rare to Almost certain)
- Consequence (1-5: Insignificant to Catastrophic)
- Proactive strategies (4-6 specific actions)
- Reactive procedures (3-4 specific steps)

Return JSON only (no markdown):
{{"student_details": {{"name": "{student['name']}", "dob": "", "age": "", "edsas": "", "home_school": ""}}, "risks": [{{"issue_title": "Title", "issue_detail": "Detail", "behaviour_descriptors": "• descriptor", "function": "", "likelihood": "D – Likely/frequently", "consequence": "3 – Moderate", "proactive": "### Heading\\n• strategy", "procedure": "### If scenario\\n• step", "clc_notes": "", "from_school": false, "from_docs": true}}], "priority_actions": "• action", "review_date": "8 weeks"}}"""
        
        raw = groq_call(simple_prompt, 3000, timeout_seconds=30)
        raw = raw.replace("```json","").replace("```","").strip()
        
        # Handle case where model wraps in extra text
        if not raw.startswith("{"):
            start = raw.find("{")
            if start != -1:
                raw = raw[start:]
        
        # Clean up control characters
        import re
        raw = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', raw)
        
        result = json.loads(raw)
        
        # Ensure all risk fields present
        for r in result.get("risks", []):
            for k, v in BLANK_RISK.items():
                if k not in r:
                    r[k] = v
        
        # Back-fill any blank student details with what the AI found in the documents
        extracted = result.get("student_details", {})
        for field, key in [("dob","dob"),("age","age"),("edsas","edsas"),("home_school","home_school"),("name","name")]:
            val = extracted.get(field,"").strip()
            if val and val.lower() not in ("blank","not found","—","unknown","") and not student.get(key,"").strip():
                student[key] = val
        
        return result
        
    except json.JSONDecodeError as e:
        st.warning("⚠️ AI response format issue. Try uploading clearer documents or use step-by-step builder.")
        return {"error": "JSON parsing failed", "risks": [], "priority_actions": "", "review_date": ""}
    except Exception as e:
        error_str = str(e).lower()
        if "timeout" in error_str:
            st.error("⚠️ AI took too long. Use the step-by-step builder instead.")
        elif "rate" in error_str:
            st.warning("⚠️ AI service busy. Please try again in a moment.")
        else:
            st.warning("⚠️ AI generation failed. Use the step-by-step builder instead (add risks manually).")
        return {"error": f"Generation failed", "risks": [], "priority_actions": "", "review_date": ""}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Safety & Risk Plan Builder | CLC LBU",
    page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed"
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}

  .clc-header {{ background:{TEAL}; color:white; padding:18px 28px 14px; border-radius:10px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; }}
  .clc-header h1 {{ margin:0; font-size:1.3rem; font-weight:700; }}
  .clc-header p  {{ margin:0; font-size:0.82rem; opacity:0.8; }}
  .clc-badge {{ background:{AMBER}; color:white; font-size:0.72rem; font-weight:700; padding:4px 10px; border-radius:20px; }}

  .step-bar {{ display:flex; gap:6px; margin-bottom:24px; }}
  .step-item {{ flex:1; padding:7px 4px; text-align:center; font-size:11px; font-weight:600; border-radius:6px; background:#E8F5F3; color:#888; border:1.5px solid transparent; }}
  .step-item.active {{ background:{TEAL}; color:white; border-color:{TEAL}; }}
  .step-item.done   {{ background:{TEAL_LIGHT}; color:{TEAL}; border-color:{TEAL}; }}

  .sec-head {{ font-size:11px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:{TEAL}; margin:18px 0 8px; border-bottom:2px solid {TEAL_LIGHT}; padding-bottom:4px; }}
  .card-amber {{ background:{AMBER_LIGHT}; border-left:4px solid {AMBER}; border-radius:6px; padding:12px 16px; margin-bottom:14px; font-size:13px; color:#5C3D00; }}
  .card-teal  {{ background:{TEAL_LIGHT}; border:1px solid {TEAL}; border-radius:8px; padding:14px 16px; margin-bottom:14px; }}
  .card-red   {{ background:#FDECEA; border-left:4px solid {RED_RISK}; border-radius:6px; padding:12px 16px; margin-bottom:14px; font-size:13px; }}
  .ai-bubble  {{ background:#f0faf8; border:1.5px solid {TEAL}; border-radius:10px 10px 10px 2px; padding:12px 14px; margin:8px 0 14px; font-size:12.5px; line-height:1.7; color:#1A3530; }}
  .ai-label   {{ font-size:10px; font-weight:700; color:{TEAL}; letter-spacing:.08em; margin-bottom:5px; }}
  .risk-item  {{ padding:9px 12px; border-radius:6px; border:0.5px solid #ddd; background:white; cursor:pointer; margin-bottom:6px; }}
  .risk-item.active {{ border-color:{TEAL}; background:{TEAL_LIGHT}; }}
  .risk-title {{ font-size:13px; font-weight:600; color:{GREY_DARK}; }}
  .risk-meta  {{ font-size:11px; color:#888; margin-top:2px; }}
  .rbadge     {{ display:inline-block; font-size:10px; font-weight:700; padding:2px 7px; border-radius:3px; color:white; margin-left:6px; vertical-align:middle; }}
  .doc-chip   {{ display:inline-block; background:{TEAL_LIGHT}; color:{TEAL}; font-size:11px; padding:3px 9px; border-radius:4px; margin:3px 3px 3px 0; }}
  .doc-chip.amber {{ background:{AMBER_LIGHT}; color:#92400e; }}

  div[data-testid="stExpander"] {{ border:1.5px solid {TEAL_LIGHT} !important; border-radius:8px !important; }}
  .stButton > button {{ font-family:'DM Sans',sans-serif !important; font-weight:600 !important; border-radius:8px !important; }}
</style>
""", unsafe_allow_html=True)

# ── Init & Header ─────────────────────────────────────────────────────────────
init_state()

st.markdown(f"""
<div class="clc-header">
  <div><h1>🛡️ Safety &amp; Risk Management Plan Builder</h1>
  <p>Cowandilla Learning Centre — Learning &amp; Behaviour Unit</p></div>
  <span class="clc-badge">v3 · EXCEL SAVE</span>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SAVE/LOAD SECTION - Always visible at top
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div style="background:#d1fae5;border:2px solid #10b981;border-radius:10px;padding:16px;margin:16px 0;">', unsafe_allow_html=True)
st.markdown("### 💾 Save & Load Your Work")

col_save, col_load = st.columns(2)

with col_save:
    st.markdown("**Save Progress to Excel:**")
    if st.session_state.student.get('name') and st.session_state.student.get('edsas'):
        excel_buffer = create_excel_save()
        student_name = st.session_state.student.get('name', 'draft').replace(' ', '_').replace('/', '_')
        filename = f"SafetyPlan_SAVE_{student_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            "💾 Download Save File (Excel)",
            data=excel_buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download your progress as Excel. Upload this file later to resume.",
            use_container_width=True,
            key="save_excel_btn"
        )
        st.caption(f"📁 File: Student details + {len(st.session_state.risks)} risk(s)")
    else:
        st.info("⬅️ Enter student name and EDSAS in Step 1 to enable save")

with col_load:
    st.markdown("**Load Previous Save:**")
    uploaded_save = st.file_uploader(
        "Upload Excel save file",
        type=['xlsx'],
        help="Upload a previously saved Excel file to resume work",
        key="load_excel_upload"
    )
    
    if uploaded_save:
        # Create unique ID for this file to prevent re-loading same file
        file_id = f"{uploaded_save.name}_{uploaded_save.size}"
        
        # Only load if this is a new file (not already loaded)
        if st.session_state.last_loaded_file != file_id:
            with st.spinner("Loading Excel file... Please wait..."):
                try:
                    success, message = load_excel_save(uploaded_save)
                    if success:
                        st.session_state.last_loaded_file = file_id  # Mark as loaded
                        st.session_state.step = 2  # Jump to Step 2 (documents)
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"Failed to load file: {str(e)}")
        else:
            # File already loaded, show confirmation
            student_name = st.session_state.student.get('name', 'Unknown')
            st.success(f"✅ Loaded: {student_name}")
            if st.button("Upload Different File", key="clear_upload"):
                st.session_state.last_loaded_file = None
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Privacy & Save Reminder
st.markdown("""
<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px;margin:12px 0;border-radius:6px;">
⚠️ <strong>Save Regularly:</strong> Click "Download Save File" every 10-15 minutes. 
This app does NOT auto-save. Save the Excel file to your computer or network drive (e.g., S:\CLC_LBU\Safety_Plans_DRAFTS\).
<br><br>
🔒 <strong>Privacy:</strong> Your save files stay on YOUR computer/network. No sensitive student data is stored in cloud databases.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Show current progress
if st.session_state.student.get('name'):
    progress_text = f"**Current:** {st.session_state.student.get('name')} | {len(st.session_state.risks)} risk(s) | Step {st.session_state.step}"
    st.markdown(progress_text)
    st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────

# ── Step bar ──────────────────────────────────────────────────────────────────
if st.session_state.mode == "express":
    express_steps = ["1 · Student","⚡ Upload & Generate"]
    bar = '<div class="step-bar">'
    for i, label in enumerate([1, 7], 0):
        real_step = [1, 7][i]
        cls = "active" if st.session_state.step == real_step else ("done" if st.session_state.step > real_step else "step-item")
        tick = "✓ " if st.session_state.step > real_step else ""
        bar += f'<div class="step-item {cls}">{tick}{express_steps[i]}</div>'
    bar += "</div>"
else:
    bar = '<div class="step-bar">'
    for i, label in enumerate(STEPS, 1):
        cls = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "step-item")
        tick = "✓ " if i < st.session_state.step else ""
        bar += f'<div class="step-item {cls}">{tick}{label}</div>'
    bar += "</div>"
st.markdown(bar, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STEP NAVIGATION - SIMPLE RADIO SELECTOR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📍 Navigate Using Buttons Below")

col_steps = st.columns(len(STEPS))
for i, step_label in enumerate(STEPS, 1):
    with col_steps[i-1]:
        btn_type = "primary" if st.session_state.step == i else "secondary"
        if st.button(step_label, key=f"step_btn_{i}", use_container_width=True, type=btn_type):
            st.session_state.step = i
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Student Details
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    s = st.session_state.student

    st.markdown('<div class="sec-head">Student Details</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        s["name"]  = st.text_input("Full name *", value=s["name"])
        s["dob"]   = st.text_input("Date of birth * (DD/MM/YYYY)", value=s["dob"],
                        help="Required — will appear on the generated plan")
        s["age"]   = st.text_input("Age *", value=s["age"])
        s["edsas"] = st.text_input("EDSAS ID *", value=s["edsas"],
                        help="Required — enter the student's EDSAS number e.g. 10981999M")
    with c2:
        s["program"] = st.selectbox("CLC Program *", ["JP","PY","SY"],
                            index=["JP","PY","SY"].index(s["program"]) if s["program"] in ["JP","PY","SY"] else 0)
        s["home_school"] = st.text_input(
            "Home school (student's mainstream school) *",
            value=s["home_school"],
            placeholder="e.g. Cowandilla Primary School, Mount Barker Primary",
            help="Enter the student's HOME school — the school they are excluded from. "
                 "This plan is always for CLC LBU regardless of which school is entered here.")
        # Warning if they accidentally enter CLC itself
        if s["home_school"].strip().lower() in ("cowandilla learning centre","clc","clc lbu"):
            st.warning("⚠️ The home school should be the student's mainstream school, not CLC. "
                       "This plan is automatically for Cowandilla Learning Centre LBU.")
        s["key_staff"]  = st.text_input("Key CLC staff", value=s["key_staff"],
                            help="e.g. Annette, Vinnie, Naomi")
        s["plan_date"]  = st.text_input("Plan date", value=s["plan_date"])

    st.markdown('<div class="sec-head">CLC Context</div>', unsafe_allow_html=True)
    s["clc_context"] = st.text_area(
        "Brief context — what has been observed at CLC so far, known triggers, current concerns",
        value=s["clc_context"], height=90,
        help="This informs all AI-generated content throughout the builder.")

    st.markdown('<div class="sec-head">Medical & Background Notes</div>', unsafe_allow_html=True)
    s["medical_notes"] = st.text_area(
        "Medical, disability, DCP, medication, or family context relevant to risk planning",
        value=s["medical_notes"], height=90,
        placeholder="e.g. ADHD — medication transition in progress. Possible ABI under investigation (MRI pending). Kinship care. DCP involved — Candice Blamey.")

    # ── Mode selector ─────────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">How would you like to build this plan?</div>', unsafe_allow_html=True)

    col_w, col_e = st.columns(2)
    with col_w:
        wizard_selected = st.session_state.mode == "wizard"
        st.markdown(f"""
        <div style="border:2px solid {'#1A7A6E'};border-radius:10px;
        padding:16px 18px;background:{'#D6EEEB'};cursor:pointer;height:130px;">
        <div style="font-size:1.3rem;margin-bottom:6px;">🧱</div>
        <div style="font-weight:700;font-size:14px;color:#2E4057;">Build step-by-step (Recommended)</div>
        <div style="font-size:12px;color:#666;margin-top:4px;line-height:1.5;">
        Upload documents, add risks one at a time, generate strategies for each risk. 
        <strong style="color:#1A7A6E;">Most reliable method.</strong></div>
        </div>""", unsafe_allow_html=True)
        if st.button("Select: Build step-by-step", use_container_width=True, type="primary"):
            st.session_state.mode = "wizard"; st.rerun()

    with col_e:
        express_selected = st.session_state.mode == "express"
        st.markdown(f"""
        <div style="border:2px solid #ddd;border-radius:10px;
        padding:16px 18px;background:white;cursor:not-allowed;height:130px;opacity:0.6;">
        <div style="font-size:1.3rem;margin-bottom:6px;">⚡</div>
        <div style="font-weight:700;font-size:14px;color:#999;">Generate directly from documents</div>
        <div style="font-size:12px;color:#999;margin-top:4px;line-height:1.5;">
        ⛔ This feature is temporarily disabled. Use the step-by-step builder below instead (more reliable).</div>
        </div>""", unsafe_allow_html=True)
        # Express mode disabled - forced to use wizard
        # if st.button("Select: Generate from documents", use_container_width=True,
        #              type="primary" if express_selected else "secondary"):
        #     st.session_state.mode = "express"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Continue →", type="primary"):
        errors = []
        if not s["name"].strip():      errors.append("Student name is required.")
        if not s["dob"].strip():       errors.append("Date of birth is required.")
        if not s["edsas"].strip():     errors.append("EDSAS ID is required.")
        if not s["home_school"].strip(): errors.append("Home school is required.")
        if errors:
            for e in errors: st.error(e)
        else:
            st.session_state.step = 5 if st.session_state.mode == "express" else 2
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Documents
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    student_name = st.session_state.student["name"]

    st.markdown('<div class="sec-head">Existing School Safety Plan</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="card-amber">
    <strong>Does {student_name}'s home school have an existing Safety &amp; Risk Management Plan?</strong><br>
    Upload it below and the AI will extract and adapt all risk rows for CLC's context.
    </div>""", unsafe_allow_html=True)

    school_plan = st.file_uploader("Upload school safety plan (.docx or .pdf)", type=["docx","pdf"],
                                    key="school_upload")
    if school_plan:
        text = extract_docx_text(school_plan)
        st.session_state.school_plan_text = text
        st.markdown(f'<div class="card-teal">✅ <strong>{school_plan.name}</strong> ready for extraction.</div>',
                    unsafe_allow_html=True)
        with st.expander("Preview extracted text"):
            st.text(text[:1500] + ("…" if len(text) > 1500 else ""))

    st.markdown('<div class="sec-head">Supporting Documents</div>', unsafe_allow_html=True)
    st.markdown("""<div class="card-teal">
    <strong>Upload any supporting documents for this student.</strong><br>
    The AI will read all of them together and generate CLC-appropriate risk rows.<br>
    <em>Accepted: behaviour support plans (BAP), psychological reports, ABCH incident reports,
    team meeting notes, OT reports, SSS notes, paediatrician letters, school reports.</em>
    </div>""", unsafe_allow_html=True)

    doc_type_options = [
        "Behaviour Summary",
        "ABCH / Incident Report",
        "Psychological Report",
        "OT / Sensory Report",
        "SSS / BSE Notes",
        "Paediatrician / Medical Report",
        "School Report / Academic Summary",
        "LC Referral",
        "Exclusion Documentation",
        "Exclusion Paperwork",
        "Entry Meeting Notes",
        "Entry Meeting Minutes",
        "Team Meeting Notes",
        "TAC Meeting Notes",
        "Other",
    ]

    uploaded_docs = st.file_uploader(
        "Upload supporting documents (.docx or .pdf)", type=["docx","pdf"],
        accept_multiple_files=True, key="support_upload"
    )

    if uploaded_docs:
        st.markdown("**Classify each document:**")
        new_docs = []
        for fi, f in enumerate(uploaded_docs):
            col_name, col_type = st.columns([2,2])
            with col_name:
                st.markdown(f"📄 `{f.name}`")
            with col_type:
                dtype = st.selectbox("Document type", doc_type_options,
                                     key=f"dtype_{fi}_{f.name[:20]}")
            text = extract_docx_text(f)
            new_docs.append({"name": f.name, "text": text, "doc_type": dtype})
        st.session_state.support_docs = new_docs

        chips = " ".join(f'<span class="doc-chip amber">{d["doc_type"]}</span>' for d in new_docs)
        st.markdown(f"<div style='margin-top:8px;'>{chips}</div>", unsafe_allow_html=True)

    # Summary of what we have
    has_school = bool(st.session_state.school_plan_text)
    has_docs   = bool(st.session_state.support_docs)
    st.markdown("<br>", unsafe_allow_html=True)

    if has_school or has_docs:
        summary = []
        if has_school: summary.append("📋 School safety plan")
        if has_docs:   summary.append(f"📄 {len(st.session_state.support_docs)} supporting document(s)")
        chips = " ".join(f'<span class="doc-chip">{s}</span>' for s in summary)
        st.markdown(f"**Ready to synthesise:** {chips}", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1,1,2])
    with col_a:
        if st.button("← Back"):
            st.session_state.step = 1; st.rerun()
    with col_b:
        if st.button("Skip to manual →"):
            st.session_state.step = 4; st.rerun()
    with col_c:
        if st.button("Extract with AI →", type="primary", use_container_width=True):
            st.session_state.step = 3; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — AI Synthesis
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:
    st.markdown('<div class="sec-head">AI Synthesis</div>', unsafe_allow_html=True)

    if st.session_state.synthesis_done:
        n = len(st.session_state.risks)
        st.success(f"✅ Synthesis complete — {n} risk(s) extracted and ready for review.")
        col_a, col_b = st.columns([1,2])
        with col_a:
            if st.button("← Back to documents"):
                st.session_state.synthesis_done = False
                st.session_state.step = 2; st.rerun()
        with col_b:
            if st.button("Continue to Risk Builder →", type="primary"):
                st.session_state.step = 6; st.rerun()
    else:
        has_school = bool(st.session_state.school_plan_text)
        has_docs   = bool(st.session_state.support_docs)
        student    = st.session_state.student

        progress = st.progress(0)
        status   = st.empty()

        all_risks = []

        if has_school:
            status.info("📋 Extracting risks from school safety plan…")
            progress.progress(15)
            school_risks = ai_extract_from_school_plan(
                st.session_state.school_plan_text, student["name"]
            )
            all_risks.extend(school_risks)
            progress.progress(40)

        if has_docs:
            status.info(f"📄 Synthesising {len(st.session_state.support_docs)} supporting document(s)…")
            doc_risks = ai_synthesise_from_docs(
                st.session_state.support_docs, student
            )
            # Deduplicate by title similarity
            existing_titles = {r["issue_title"].lower()[:30] for r in all_risks}
            for r in doc_risks:
                if r["issue_title"].lower()[:30] not in existing_titles:
                    all_risks.append(r)
                    existing_titles.add(r["issue_title"].lower()[:30])
            progress.progress(75)

        # Ensure BLANK_RISK keys present on all
        status.info("✨ Finalising and formatting risk rows…")
        clean = []
        for r in all_risks:
            merged = {**BLANK_RISK, **r}
            clean.append(merged)
        st.session_state.risks = clean
        progress.progress(100)

        status.success(f"✅ Done — {len(clean)} risk row(s) ready. Click Continue to review each one.")
        st.session_state.synthesis_done = True
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Risk Builder
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 4:
    student = st.session_state.student
    risks   = st.session_state.risks

    left, right = st.columns([1,2], gap="large")

    with left:
        st.markdown('<div class="sec-head">Risk areas</div>', unsafe_allow_html=True)

        for i, r in enumerate(risks):
            level  = compute_risk_level(r["likelihood"], r["consequence"])
            colour = risk_colour(level)
            title  = r["issue_title"] or f"Risk {i+1} (unnamed)"
            origin = "📋" if r.get("from_school") else ("📄" if r.get("from_docs") else "✏️")
            active = i == st.session_state.current_risk
            if st.button(f"{'▶ ' if active else ''}{origin} {title}", key=f"sel_{i}",
                         use_container_width=True):
                st.session_state.current_risk = i; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick-add from CLC standard templates
        with st.expander("＋ Add from CLC risk library"):
            template = st.selectbox("Select a common CLC risk", ["— choose —"] + CLC_RISK_TEMPLATES,
                                    key="tpl_select")
            if st.button("Add this risk", key="tpl_add") and template != "— choose —":
                new_r = {**BLANK_RISK, "issue_title": template}
                risks.append(new_r)
                st.session_state.current_risk = len(risks) - 1
                st.rerun()

        if st.button("＋ Add blank risk", use_container_width=True):
            risks.append(deepcopy(BLANK_RISK))
            st.session_state.current_risk = len(risks) - 1; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Back to documents", use_container_width=True):
            st.session_state.step = 2; st.rerun()
        if risks and st.button("Continue to Review →", type="primary", use_container_width=True):
            if all(r["issue_title"].strip() == "" for r in risks):
                st.error("Please complete at least one risk.")
            else:
                st.session_state.step = 6; st.rerun()

    with right:
        if not risks:
            st.markdown('<div class="card-teal"><strong>No risks yet.</strong> Add one from the library or click <em>＋ Add blank risk</em>.</div>', unsafe_allow_html=True)
        else:
            idx = min(st.session_state.current_risk, len(risks)-1)
            r   = risks[idx]
            level  = compute_risk_level(r["likelihood"], r["consequence"])
            colour = risk_colour(level)
            origin = "📋 from school plan" if r.get("from_school") else ("📄 from documents" if r.get("from_docs") else "✏️ manual entry")

            st.markdown(f'<div class="sec-head">Risk {idx+1} of {len(risks)} &nbsp;·&nbsp; <span style="color:{colour};font-weight:700">{level}</span> &nbsp;·&nbsp; <span style="color:#888;font-weight:400;font-size:10px;">{origin}</span></div>', unsafe_allow_html=True)

            # AI contextualisation advisory (school plan risks only)
            if r.get("from_school") and r["issue_title"]:
                cache_key = f"ctx_{idx}_{r['issue_title'][:20]}"
                if cache_key not in st.session_state.ai_context_cache:
                    with st.spinner("Generating CLC contextualisation prompts…"):
                        st.session_state.ai_context_cache[cache_key] = ai_contextualise(r, student)
                advice = st.session_state.ai_context_cache.get(cache_key,"")
                if advice:
                    st.markdown(f"""<div class="ai-bubble">
                    <div class="ai-label">🤖 AI · CLC CONTEXTUALISATION PROMPTS</div>
                    {advice.replace(chr(10),'<br>')}
                    </div>""", unsafe_allow_html=True)

            # ── Issue details ─────────────────────────────────────────────
            st.markdown('<div class="sec-head">Issue / Behaviour</div>', unsafe_allow_html=True)
            r["issue_title"] = st.text_input("Short title *", value=r["issue_title"], key=f"t_{idx}",
                placeholder="e.g. Absconding from CLC grounds")

            st.caption("⚠️  Describe what the student DOES — observable behaviour only. Triggers belong in proactive strategies.")
            r["issue_detail"] = st.text_area("Behaviour description",
                value=r["issue_detail"], key=f"d_{idx}", height=90,
                placeholder="Describe the observable behaviour and what it looks like at CLC…")

            r["behaviour_descriptors"] = st.text_area(
                "Specific behaviour descriptors (one per line, start with •, -, or *)",
                value="\n".join(r["behaviour_descriptors"]) if isinstance(r["behaviour_descriptors"], list) else r["behaviour_descriptors"],
                key=f"bd_{idx}", height=90,
                placeholder="• Running at speed away from supervised areas\n• Climbing boundary fence into carpark\n• Darting across Marion Road without checking for traffic")

            r["function"] = st.text_input("Function of behaviour",
                value=r["function"], key=f"fn_{idx}",
                placeholder="e.g. Avoidance – peer and adult")

            st.markdown('<div class="sec-head">CLC-Specific Context for this Risk</div>', unsafe_allow_html=True)
            r["clc_notes"] = st.text_area(
                "Staff notes — what has been observed at CLC, environmental factors, relevant incidents",
                value=r["clc_notes"], key=f"cn_{idx}", height=80,
                placeholder="e.g. Confirmed fence climb and absconding 19/03/2026. Jenkins Rd, Marion Rd, Sir Donald Bradman Drive all within 100m. SAPOL ref 0732.")

            # ── Risk rating ───────────────────────────────────────────────
            st.markdown('<div class="sec-head">Risk Rating</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                r["likelihood"] = st.selectbox("Likelihood", LIKELIHOOD_OPTIONS,
                    index=LIKELIHOOD_OPTIONS.index(r["likelihood"]) if r["likelihood"] in LIKELIHOOD_OPTIONS else 3,
                    key=f"lk_{idx}")
            with c2:
                r["consequence"] = st.selectbox("Consequence", CONSEQUENCE_OPTIONS,
                    index=CONSEQUENCE_OPTIONS.index(r["consequence"]) if r["consequence"] in CONSEQUENCE_OPTIONS else 2,
                    key=f"cq_{idx}")
            with c3:
                lv = compute_risk_level(r["likelihood"], r["consequence"])
                col = risk_colour(lv)
                st.markdown(f"""<div style="background:{col};color:white;border-radius:8px;padding:18px 10px 12px;text-align:center;margin-top:4px;">
                <div style="font-size:10px;font-weight:700;opacity:.9;letter-spacing:.08em;">RISK LEVEL</div>
                <div style="font-size:1.6rem;font-weight:700;margin-top:2px;">{lv}</div>
                </div>""", unsafe_allow_html=True)

            # ── Strategies ────────────────────────────────────────────────
            st.markdown('<div class="sec-head">Proactive Strategies</div>', unsafe_allow_html=True)
            if st.button("✨ Generate CLC strategies with AI", key=f"gen_{idx}",
                         disabled=not r["issue_title"].strip()):
                with st.spinner("Generating…"):
                    gen = ai_generate_strategies(r, student)
                    if gen.get("proactive"): r["proactive"] = gen["proactive"]
                    if gen.get("procedure"): r["procedure"] = gen["procedure"]
                st.rerun()

            r["proactive"] = st.text_area(
                "Proactive strategies (use ### Subheading and • bullets)",
                value="\n".join(r["proactive"]) if isinstance(r["proactive"], list) else r["proactive"],
                key=f"pr_{idx}", height=180,
                placeholder="### Environment & supervision\n• Ensure gate is latched at all times\n• Staff maintain line-of-sight\n\n### Relational strategies\n• Daily co-regulation check-in…")

            st.markdown('<div class="sec-head">Reactive Procedures</div>', unsafe_allow_html=True)
            st.caption("Use ### Subheadings to structure by scenario (e.g. ### If early warning signs: / ### If left grounds:)")
            r["procedure"] = st.text_area(
                "Step-by-step reactive procedures",
                value="\n".join(r["procedure"]) if isinstance(r["procedure"], list) else r["procedure"],
                key=f"pc_{idx}", height=220,
                placeholder="### If early signs of dysregulation:\n• Offer co-regulation…\n\n### If Xavier has left grounds:\n• Staff 1 follow on foot…")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 Remove this risk", key=f"del_{idx}"):
                risks.pop(idx)
                st.session_state.current_risk = max(0, idx-1)
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Review
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    student = st.session_state.student
    risks   = st.session_state.risks

    st.markdown('<div class="sec-head">Plan Summary</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="card-teal">
    <strong>{student['name']}</strong> &nbsp;|&nbsp; DOB: {student['dob']} &nbsp;|&nbsp;
    Age: {student['age']} &nbsp;|&nbsp; EDSAS: {student['edsas']} &nbsp;|&nbsp;
    Program: {student['program']} &nbsp;|&nbsp; Home school: {student['home_school']}<br>
    <span style="font-size:0.85rem;color:#1A3530;">Key staff: {student['key_staff']} &nbsp;·&nbsp; Plan date: {student['plan_date']}</span>
    </div>""", unsafe_allow_html=True)

    if student.get("medical_notes"):
        st.markdown(f'<div class="card-amber">⚕ <strong>Medical/context:</strong> {student["medical_notes"]}</div>',
                    unsafe_allow_html=True)

    st.markdown(f"**{len(risks)} risk(s) identified:**")
    for i, r in enumerate(risks):
        level = compute_risk_level(r["likelihood"], r["consequence"])
        col   = risk_colour(level)
        title = r["issue_title"] or f"Unnamed risk {i+1}"
        with st.expander(f"Risk {i+1}: {title}  [{level}]"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Likelihood:** {r['likelihood']}")
                st.markdown(f"**Consequence:** {r['consequence']}")
                st.markdown(f"**Function:** {r['function'] or '—'}")
            with c2:
                st.markdown(f"**Risk level:** <span style='color:{col};font-weight:700'>{level}</span>", unsafe_allow_html=True)
                st.markdown(f"**CLC notes:** {r['clc_notes'] or '—'}")
            if r.get("behaviour_descriptors"):
                st.markdown("**Behaviour descriptors:**")
                st.text(r["behaviour_descriptors"])
            st.markdown("**Proactive:**")
            st.text(r["proactive"] or "(none)")
            st.markdown("**Procedure:**")
            st.text(r["procedure"] or "(none)")

    st.markdown('<div class="sec-head">Priority Actions</div>', unsafe_allow_html=True)
    gen_col, _ = st.columns([1,2])
    with gen_col:
        if st.button("✨ Generate priority actions with AI"):
            with st.spinner("Generating…"):
                st.session_state.priority_actions = ai_generate_priority_actions(risks, student)
            st.rerun()

    st.session_state.priority_actions = st.text_area(
        "Priority actions arising from this plan (one per line, start with •, -, or *)",
        value=st.session_state.priority_actions, height=140,
        placeholder="• Schedule TAC meeting within 5 school days\n• Conduct fence/gate risk audit…")

    st.session_state.review_date = st.text_input("Review date",
        value=st.session_state.review_date, placeholder="e.g. 19/05/2026")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1,1,2])
    with col_a:
        if st.button("← Back to risks"):
            st.session_state.step = 6; st.rerun()
    with col_c:
        if st.button("✅ Generate Safety Plan (.docx)", type="primary", use_container_width=True):
            if not risks or all(r["issue_title"].strip() == "" for r in risks):
                st.error("Please complete at least one risk row.")
            else:
                st.session_state.step = 6; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Polish & Enhance (Optional)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 6:
    student = st.session_state.student
    risks   = st.session_state.risks
    
    st.markdown('<div class="sec-head">Polish & Enhance Your Plan</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#e0f7fa;border-left:4px solid #0097a7;padding:12px;margin:12px 0;border-radius:4px;">
    📝 <strong>Optional step:</strong> Edit your content and use AI to enhance language or expand sections. 
    Click "Generate Document" when ready to create the final Word doc.
    </div>
    """, unsafe_allow_html=True)
    
    # Enhancement mode selector
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        enhance_mode = st.radio(
            "AI Enhancement mode:",
            options=["language", "expand", "both"],
            format_func=lambda x: {"language": "Improve language", "expand": "Expand detail", "both": "Improve + Expand"}[x],
            horizontal=True
        )
    
    st.markdown("---")
    st.markdown("### Priority Actions")
    
    col_pa1, col_pa2 = st.columns([4, 1])
    with col_pa1:
        st.session_state.priority_actions = st.text_area(
            "Priority actions (one per line, start with •, -, or *)",
            value=st.session_state.priority_actions,
            height=120,
            key="pa_edit"
        )
    with col_pa2:
        if st.button("✨ AI Enhance", key="pa_enhance"):
            with st.spinner("Enhancing..."):
                enhanced = ai_enhance_text(st.session_state.priority_actions, enhance_mode)
                st.session_state.priority_actions = enhanced
                st.rerun()
    
    st.markdown("---")
    st.markdown("### Individual Risks")
    
    # Edit each risk
    for idx, r in enumerate(st.session_state.risks):
        with st.expander(f"📋 {idx+1}. {r['issue_title'] or '(Untitled)'}", expanded=(idx == st.session_state.current_risk)):
            
            # Title
            r["issue_title"] = st.text_input(
                "Risk title",
                value=r["issue_title"],
                key=f"enh_title_{idx}"
            )
            
            # Behaviour descriptors
            st.markdown("**Behaviour Descriptors**")
            col_bd1, col_bd2 = st.columns([4, 1])
            with col_bd1:
                r["behaviour_descriptors"] = st.text_area(
                    "What the student does (one per line, start with •, -, or *)",
                    value="\n".join(r["behaviour_descriptors"]) if isinstance(r["behaviour_descriptors"], list) else r["behaviour_descriptors"],
                    height=80,
                    key=f"enh_bd_{idx}"
                )
            with col_bd2:
                if st.button("✨", key=f"enh_bd_btn_{idx}", help="Enhance descriptors"):
                    with st.spinner("Enhancing..."):
                        enhanced = ai_enhance_text(r["behaviour_descriptors"], enhance_mode)
                        r["behaviour_descriptors"] = enhanced
                        st.rerun()
            
            # Proactive
            st.markdown("**Proactive Strategies**")
            col_pro1, col_pro2 = st.columns([4, 1])
            with col_pro1:
                r["proactive"] = st.text_area(
                    "What you do before (### Subheading + • bullets)",
                    value="\n".join(r["proactive"]) if isinstance(r["proactive"], list) else r["proactive"],
                    height=120,
                    key=f"enh_pro_{idx}"
                )
            with col_pro2:
                if st.button("✨", key=f"enh_pro_btn_{idx}", help="Enhance proactive"):
                    with st.spinner("Enhancing..."):
                        enhanced = ai_enhance_text(r["proactive"], enhance_mode)
                        r["proactive"] = enhanced
                        st.rerun()
            
            # Procedures
            st.markdown("**Reactive Procedures**")
            col_proc1, col_proc2 = st.columns([4, 1])
            with col_proc1:
                r["procedure"] = st.text_area(
                    "What you do if it happens (### Subheading + • bullets)",
                    value="\n".join(r["procedure"]) if isinstance(r["procedure"], list) else r["procedure"],
                    height=140,
                    key=f"enh_proc_{idx}"
                )
            with col_proc2:
                if st.button("✨", key=f"enh_proc_btn_{idx}", help="Enhance procedures"):
                    with st.spinner("Enhancing..."):
                        enhanced = ai_enhance_text(r["procedure"], enhance_mode)
                        r["procedure"] = enhanced
                        st.rerun()
            
            # CLC notes
            r["clc_notes"] = st.text_area(
                "CLC-specific notes",
                value=r["clc_notes"],
                height=70,
                key=f"enh_notes_{idx}"
            )
    
    st.markdown("---")
    
    # Navigation buttons
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Review"):
            st.session_state.step = 5; st.rerun()
    with col_nav2:
        if st.button("Generate Document →", type="primary", use_container_width=True):
            st.session_state.step = 7; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Generate .docx
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 7:
    student          = st.session_state.student
    risks            = st.session_state.risks
    priority_actions = st.session_state.priority_actions
    review_date      = st.session_state.review_date

    st.markdown('<div class="sec-head">Generating Document</div>', unsafe_allow_html=True)

    # ── docx helpers ──────────────────────────────────────────────────────────
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

    def cbullet(cell, text, size=17, color="333333"):
        p = cell.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        arun(p, text, size=size, color=color)

    def render_content(cell, text):
        """Parse ### subheadings and • bullets into formatted cell content."""
        # Handle both string and list formats
        if isinstance(text, list):
            text = "\n".join(str(t) for t in text)
        else:
            text = str(text) if text else ""
        
        if not text.strip():
            cpara(cell, "(Not completed)", italic=True, color="888888")
            return
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            if line.startswith("###"):
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(5)
                p.paragraph_format.space_after  = Pt(2)
                arun(p, line.lstrip("# "), bold=True, color=TEAL.lstrip("#"), size=16)
            elif line.startswith("•") or line.startswith("-") or line.startswith("*"):
                cbullet(cell, line.lstrip("•-* "))
            else:
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after  = Pt(2)
                arun(p, line, size=17)

    # ── Build document ────────────────────────────────────────────────────────
    with st.spinner("Building your Safety & Risk Management Plan…"):
        doc = DocxDocument()
        sec = doc.sections[0]
        sec.page_width  = Cm(21)
        sec.page_height = Cm(29.7)
        for attr in ('left_margin','right_margin','top_margin','bottom_margin'):
            setattr(sec, attr, Cm(1.5))

        # Title
        t = doc.add_table(rows=1, cols=1); t.style='Table Grid'
        tc = t.rows[0].cells[0]; set_bg(tc, TEAL.lstrip("#")); set_borders(tc, TEAL.lstrip("#"))
        p1 = tc.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        arun(p1, "SAFETY & RISK MANAGEMENT PLAN", bold=True, size=28, color="FFFFFF")
        cpara(tc, f"{student['name']}  |  Cowandilla Learning Centre  |  LBU {student['program']} Program",
              size=18, color="FEF3C7", align=WD_ALIGN_PARAGRAPH.CENTER, sb=20, sa=40)

        doc.add_paragraph()

        # Student details
        det = doc.add_table(rows=3, cols=2); det.style='Table Grid'
        hdr = det.rows[0].cells[0].merge(det.rows[0].cells[1])
        set_bg(hdr, GREY_DARK.lstrip("#")); set_borders(hdr, TEAL.lstrip("#"))
        arun(hdr.paragraphs[0], "STUDENT DETAILS", bold=True, size=18, color="FFFFFF")

        details_l = [("Full Name", student['name']), ("Date of Birth", student['dob'] or "—"),
                     ("Age", student['age'] or "—"), ("EDSAS ID", student['edsas'] or "—")]
        details_r = [("Home School", student['home_school'] or "—"),
                     ("CLC Program", student['program']), ("Plan Date", student['plan_date'])]

        for ci, items in enumerate([details_l, details_r]):
            c = det.rows[1].cells[ci]; set_bg(c,"F2F6F6"); set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].clear()
            for label, val in items:
                p = c.add_paragraph()
                arun(p, f"{label}: ", bold=True, size=17, color=GREY_DARK.lstrip("#"))
                arun(p, val, size=17)

        status_cell = det.rows[2].cells[0].merge(det.rows[2].cells[1])
        set_bg(status_cell, AMBER_LIGHT.lstrip("#")); set_borders(status_cell, AMBER.lstrip("#"))
        p = status_cell.paragraphs[0]
        arun(p, "Key staff: ", bold=True, size=17, color=AMBER.lstrip("#"))
        arun(p, student['key_staff'] or "—", size=17)
        if student.get('medical_notes'):
            p2 = status_cell.add_paragraph()
            arun(p2, "Medical/context: ", bold=True, size=16, color="666666")
            arun(p2, student['medical_notes'], size=16, italic=True)
        if student.get('clc_context'):
            p3 = status_cell.add_paragraph()
            arun(p3, "CLC context: ", bold=True, size=16, color="666666")
            arun(p3, student['clc_context'], size=16, italic=True)

        doc.add_paragraph()

        # Risk table heading
        h = doc.add_paragraph()
        arun(h, "IDENTIFIED RISKS AND MANAGEMENT STRATEGIES", bold=True, size=20, color=GREY_DARK.lstrip("#"))
        n = doc.add_paragraph()
        arun(n, "* Risk ratings use the Likelihood/Consequence matrix on page 2. Ratings reflect probability and severity without proactive strategies in place.",
             italic=True, size=14, color="666666")

        # Main risk table — 4 columns
        main = doc.add_table(rows=1, cols=4); main.style='Table Grid'
        col_widths = [Cm(5.2), Cm(2.0), Cm(7.2), Cm(8.6)]
        for i, w in enumerate(col_widths):
            for c in main.columns[i].cells: c.width = w

        for i, h in enumerate(["Concerning Issue","Risk Level *","Proactive Strategies","Procedure to Follow"]):
            c = main.rows[0].cells[i]; set_bg(c, TEAL.lstrip("#")); set_borders(c, TEAL.lstrip("#"))
            p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p, h, bold=True, size=17, color="FFFFFF")

        for r in risks:
            if not r["issue_title"].strip(): continue
            level   = compute_risk_level(r["likelihood"], r["consequence"])
            lhex    = RISK_COLOURS.get(level,"#888").lstrip("#")
            l_code  = r["likelihood"].split("–")[0].strip().split(" ")[0]
            c_code  = r["consequence"].split("–")[0].strip().split(" ")[0]
            row = main.add_row()

            # Col 0: Issue
            c0 = row.cells[0]; set_bg(c0,"D6EEEB"); set_borders(c0, TEAL.lstrip("#"))
            c0.paragraphs[0].clear()
            p = c0.paragraphs[0]; arun(p, r["issue_title"], bold=True, size=17, color=GREY_DARK.lstrip("#"))
            if r["issue_detail"]:
                p2 = c0.add_paragraph(); p2.paragraph_format.space_before = Pt(4)
                arun(p2, r["issue_detail"], size=16)
            if r["behaviour_descriptors"]:
                ph = c0.add_paragraph(); ph.paragraph_format.space_before = Pt(5)
                arun(ph, "Characterised by:", bold=True, size=15, color=TEAL.lstrip("#"))
                
                # Handle both string (with newlines) and list formats
                if isinstance(r["behaviour_descriptors"], list):
                    bd_lines = r["behaviour_descriptors"]
                else:
                    bd_lines = r["behaviour_descriptors"].splitlines()
                
                for bd_line in bd_lines:
                    bl = str(bd_line).strip()
                    if bl:
                        bp = c0.add_paragraph(style='List Bullet')
                        bp.paragraph_format.space_before = Pt(1)
                        bp.paragraph_format.space_after  = Pt(1)
                        arun(bp, bl.lstrip("•- "), size=15)
            if r["function"]:
                pf = c0.add_paragraph(); pf.paragraph_format.space_before = Pt(5)
                arun(pf, "Function: ", bold=True, size=15, color="555555")
                arun(pf, r["function"], size=15, italic=True)
            if r["clc_notes"]:
                pn = c0.add_paragraph(); pn.paragraph_format.space_before = Pt(5)
                arun(pn, "CLC: ", bold=True, size=14, color=AMBER.lstrip("#"))
                arun(pn, r["clc_notes"], size=14, italic=True)

            # Col 1: Risk level
            c1 = row.cells[1]; set_bg(c1, lhex); set_borders(c1, lhex)
            p1 = c1.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p1, f"{l_code}{c_code}", bold=True, size=26, color="FFFFFF")
            p2 = c1.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p2, level, bold=True, size=14, color="FFFFFF")

            # Col 2: Proactive
            c2 = row.cells[2]; set_borders(c2, TEAL.lstrip("#"))
            c2.paragraphs[0].clear(); render_content(c2, r["proactive"])

            # Col 3: Procedure
            c3 = row.cells[3]; set_borders(c3, TEAL.lstrip("#"))
            c3.paragraphs[0].clear(); render_content(c3, r["procedure"])

        # Footer note
        fn_row = main.add_row()
        fn_cell = fn_row.cells[0].merge(fn_row.cells[1]).merge(fn_row.cells[2]).merge(fn_row.cells[3])
        set_bg(fn_cell,"F2F6F6"); set_borders(fn_cell, TEAL.lstrip("#"))
        p = fn_cell.paragraphs[0]
        arun(p, "* Risk ratings use the Likelihood/Consequence matrix on the following page.",
             italic=True, size=13, color="666666")

        doc.add_paragraph()

        # Priority actions
        if priority_actions.strip():
            pa_tbl = doc.add_table(rows=1, cols=1); pa_tbl.style='Table Grid'
            pa = pa_tbl.rows[0].cells[0]
            set_bg(pa, AMBER_LIGHT.lstrip("#")); set_borders(pa, AMBER.lstrip("#"))
            pa.paragraphs[0].clear()
            cpara(pa, "PRIORITY ACTIONS", bold=True, size=19, color=AMBER.lstrip("#"), sb=40, sa=60)
            for line in priority_actions.splitlines():
                line = line.strip()
                if not line: continue
                if line.startswith("•") or line.startswith("-"):
                    cbullet(pa, line.lstrip("•- "))
                else:
                    cpara(pa, line, size=17)
            doc.add_paragraph()


        # ── Staff Acknowledgement sign-off ─────────────────────────────────
        doc.add_paragraph()
        sh = doc.add_paragraph()
        arun(sh, "STAFF ACKNOWLEDGEMENT", bold=True, size=19, color=GREY_DARK.lstrip("#"))
        sn = doc.add_paragraph()
        arun(sn, "All staff working with this student must read this plan and sign below to confirm they understand the identified risks and their responsibilities.",
             size=15, italic=True)
        doc.add_paragraph()

        # Sign-off table — header + 8 blank rows
        SIGN_COLS = ["Staff Member Name", "Role", "Signature", "Date"]
        SIGN_WIDTHS_CM = [5.5, 4.0, 5.5, 2.5]
        stbl = doc.add_table(rows=9, cols=4); stbl.style='Table Grid'
        from docx.shared import Cm as _Cm
        for ci, w in enumerate(SIGN_WIDTHS_CM):
            for cell in stbl.columns[ci].cells:
                cell.width = _Cm(w)
        # Header row
        for ci, lbl in enumerate(SIGN_COLS):
            c = stbl.rows[0].cells[ci]
            set_bg(c, GREY_DARK.lstrip("#")); set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], lbl, bold=True, size=16, color="FFFFFF")
        # 8 blank signing rows
        for ri in range(1, 9):
            row = stbl.rows[ri]
            bg = "F2F6F6" if ri % 2 == 0 else "FFFFFF"
            for ci in range(4):
                c = row.cells[ci]
                set_bg(c, bg); set_borders(c, "CCCCCC")
                cpara(c, "", size=16, sb=60, sa=60)
        doc.add_paragraph()

        # Endorsement / review
        eh = doc.add_paragraph()
        arun(eh, "PLAN ENDORSEMENT", bold=True, size=19, color=GREY_DARK.lstrip("#"))
        doc.add_paragraph()
        sign_tbl = doc.add_table(rows=2, cols=3); sign_tbl.style='Table Grid'
        for ci, lbl in enumerate(["Prepared by (CLC staff)","Endorsed by (Principal/Leader)","Next Review Date"]):
            c = sign_tbl.rows[0].cells[ci]; set_bg(c, GREY_DARK.lstrip("#"))
            set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], lbl, bold=True, size=16, color="FFFFFF")
        for ci, val in enumerate(["Name: ___________________________\nSignature: ______________________\nDate: _______________",
                                   "Name: ___________________________\nSignature: ______________________\nDate: _______________",
                                   review_date or "TBC"]):
            c = sign_tbl.rows[1].cells[ci]; set_bg(c,"F2F6F6"); set_borders(c, TEAL.lstrip("#"))
            for line in val.split('\n'):
                cpara(c, line, size=16, sb=20, sa=20)


        doc.add_page_break()

        # Risk matrix page
        mh = doc.add_paragraph(); arun(mh, "LEVEL OF RISK — REFERENCE MATRIX", bold=True, size=22, color=GREY_DARK.lstrip("#"))

        likelihoods = ["E – Almost Certain","D – Likely/Frequently","C – Likely Sometimes","B – Unlikely","A – Rare"]
        cons_labels = ["1 Insignificant","2 Minor","3 Moderate","4 Major","5 Catastrophic"]
        matrix_data = [["High","High","Extreme","Extreme","Extreme"],
                       ["Moderate","High","High","Extreme","Extreme"],
                       ["Low","Moderate","High","Extreme","Extreme"],
                       ["Low","Low","Moderate","High","Extreme"],
                       ["Low","Low","Moderate","High","High"]]
        fill_m = {"Extreme":"C0392B","High":"E67E22","Moderate":"F1C40F","Low":"27AE60"}
        text_m = {"Extreme":"FFFFFF","High":"FFFFFF","Moderate":"333333","Low":"FFFFFF"}

        mx = doc.add_table(rows=len(likelihoods)+1, cols=len(cons_labels)+1); mx.style='Table Grid'
        mx.rows[0].cells[0].paragraphs[0].clear()
        set_bg(mx.rows[0].cells[0], GREY_DARK.lstrip("#"))
        arun(mx.rows[0].cells[0].paragraphs[0], "Likelihood \\ Consequences", bold=True, size=13, color="FFFFFF")
        for ci, cl in enumerate(cons_labels):
            c = mx.rows[0].cells[ci+1]; set_bg(c, GREY_DARK.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], cl, bold=True, size=13, color="FFFFFF")

        for ri, (lh, row_data) in enumerate(zip(likelihoods, matrix_data)):
            row = mx.rows[ri+1]
            set_bg(row.cells[0],"F2F6F6")
            arun(row.cells[0].paragraphs[0], lh, bold=True, size=13, color=GREY_DARK.lstrip("#"))
            for ci, val in enumerate(row_data):
                c = row.cells[ci+1]; fh = fill_m.get(val,"888888"); set_bg(c, fh)
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                arun(c.paragraphs[0], val, bold=True, size=13, color=text_m.get(val,"FFFFFF"))

        doc.add_paragraph()
        lh = doc.add_paragraph(); arun(lh, "NOTES ON ANALYSING RISKS", bold=True, size=18, color=GREY_DARK.lstrip("#"))
        note = doc.add_paragraph()
        arun(note, "Assess the likelihood and consequence using the definitions below, then read the level from the matrix above.", size=16)
        doc.add_paragraph()

        legend = [
            ("E – Almost Certain","5 – Catastrophic: Serious injury or near-miss; severe incident (traffic collision, weapon, suicidal behaviour); major level over significant period."),
            ("D – Likely/Frequently","4 – Major: Injury or near-miss; distress to others; violence; critical incident report; repeated incidents."),
            ("C – Likely Sometimes","3 – Moderate: Cross-agency involvement; incident reports; repeated suspension/take-home; complex welfare or health issues."),
            ("B – Unlikely","2 – Minor: Impact on learning; team approach required; referral suggested; frequent repeats and take-home suspensions."),
            ("A – Rare","1 – Insignificant: Managed within program; discussion with line manager; review at team meeting."),
        ]
        leg_tbl = doc.add_table(rows=len(legend)+1, cols=2); leg_tbl.style='Table Grid'
        for ci, lbl in enumerate(["Likelihood","Consequences"]):
            c = leg_tbl.rows[0].cells[ci]; set_bg(c, GREY_DARK.lstrip("#")); set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], lbl, bold=True, size=15, color="FFFFFF")
        for ri, (lk, cs) in enumerate(legend):
            r0 = leg_tbl.rows[ri+1].cells[0]; r1 = leg_tbl.rows[ri+1].cells[1]
            set_bg(r0,"F2F6F6"); arun(r0.paragraphs[0], lk, bold=True, size=14, color=GREY_DARK.lstrip("#"))
            arun(r1.paragraphs[0], cs, size=14)

        buf = io.BytesIO()
        doc.save(buf); buf.seek(0)

    # ── Normalize all risks before final checks ────────────────────────────────
    risks_final = [normalize_risk(r) for r in st.session_state.risks]
    
    # ── Language objectivity check ────────────────────────────────────────────
    all_text = " ".join([
        " ".join([
            str(r.get("issue_title","")).strip(),
            str(r.get("issue_detail","")).strip(),
            "\n".join(r.get("behaviour_descriptors",[])) if isinstance(r.get("behaviour_descriptors"), list) else str(r.get("behaviour_descriptors","")),
            "\n".join(r.get("proactive",[])) if isinstance(r.get("proactive"), list) else str(r.get("proactive","")),
            "\n".join(r.get("procedure",[])) if isinstance(r.get("procedure"), list) else str(r.get("procedure",""))
        ])
        for r in risks_final
    ])
    lang_flags = check_language_objectivity(all_text)
    if lang_flags:
        st.markdown("""
        <div style="background:#fff8e6;border:2px solid #e8a125;border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem;">
        <div style="font-weight:700;color:#92400e;font-size:.9rem;margin-bottom:.5rem;">
        ⚠️ Language Review — Possible Subjective Terms Detected
        </div>
        <div style="font-size:.8rem;color:#78350f;margin-bottom:.5rem;">
        The plan may contain language that is open to individual interpretation.
        Review the flagged items below and edit the relevant risk rows before downloading.
        Objective language ensures all staff understand and apply the plan consistently.
        </div>
        </div>""", unsafe_allow_html=True)
        for flag in lang_flags:
            st.markdown(f'<div style="background:#fef9ee;border-left:3px solid #e8a125;border-radius:0 6px 6px 0;padding:.4rem .8rem;margin-bottom:.35rem;font-size:.8rem;color:#78350f;">⚠️ {flag}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#f0faf8;border:1.5px solid #1a7a6e;border-radius:10px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.85rem;color:#1a2e44;">
        ✅ <strong>Language check passed</strong> — no obvious subjective terms detected. Review the plan content before downloading.
        </div>""", unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown(f"""<div class="card-teal">
    ✅ <strong>Plan generated!</strong> {student['name']}'s Safety &amp; Risk Management Plan is ready —
    {len([r for r in risks if r['issue_title'].strip()])} risk row(s), priority actions, risk matrix.
    </div>""", unsafe_allow_html=True)

    safe = student['name'].replace(" ","_").replace("/","")
    fname = f"Safety_Risk_Plan_{safe}_CLC_{student['plan_date'].replace('/','')}.docx"
    _ini = initials_from_name(student['name'])
    st.download_button("⬇️  Download Safety & Risk Plan (.docx)",
                       data=buf, file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       type="primary", use_container_width=True,
                       on_click=archive_once,
                       args=(f"srp_{_ini}_{student['plan_date']}",),
                       kwargs=dict(
                           source_tool="Safety & Risk Plan Builder",
                           doc_type="Safety & Risk Plan",
                           title=f"Safety & Risk Plan — {_ini} — {student['plan_date']}",
                           file_bytes=buf.getvalue() if hasattr(buf, "getvalue") else buf,
                           filename=f"Safety_Risk_Plan_{_ini}_CLC_{student['plan_date'].replace('/','')}.docx",
                           student_initials=_ini,
                           created_by=st.session_state.get("user_email", "unknown"),
                       ))

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Back to Review"):
            st.session_state.step = 6; st.rerun()
    with col_b:
        if st.button("🔄 Start a new plan"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Express: Upload & Generate directly
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    student = st.session_state.student

    st.markdown(f"""<div class="card-amber">
    ⚡ <strong>Express mode</strong> — Upload documents for <strong>{student['name']}</strong> and
    the AI will write the complete, formatted Safety &amp; Risk Management Plan in one step.
    No step-by-step review needed.
    </div>""", unsafe_allow_html=True)

    # ── Document uploads ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">School Safety Plan (optional)</div>', unsafe_allow_html=True)
    school_upload = st.file_uploader("Upload existing school safety plan (.docx or .pdf)",
                                     type=["docx","pdf"], key="express_school")
    if school_upload:
        text = extract_docx_text(school_upload)
        st.session_state.school_plan_text = text
        st.markdown(f'<div class="card-teal">✅ <strong>{school_upload.name}</strong> ready.</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="sec-head">Supporting Documents</div>', unsafe_allow_html=True)
    st.caption("BAPs, incident reports, psych reports, OT reports, SSS/BSE notes, paediatrician letters, school reports, TAC notes — upload as many as you have.")

    doc_type_options = [
        "Behaviour Summary",
        "ABCH / Incident Report",
        "Psychological Report",
        "OT / Sensory Report",
        "SSS / BSE Notes",
        "Paediatrician / Medical Report",
        "School Report / Academic Summary",
        "LC Referral",
        "Exclusion Documentation",
        "Exclusion Paperwork",
        "Entry Meeting Notes",
        "Entry Meeting Minutes",
        "Team Meeting Notes",
        "TAC Meeting Notes",
        "Other",
    ]

    uploaded_docs = st.file_uploader("Upload supporting documents (.docx or .pdf)",
                                     type=["docx","pdf"], accept_multiple_files=True,
                                     key="express_docs")
    if uploaded_docs:
        new_docs = []
        for fi, f in enumerate(uploaded_docs):
            col_n, col_t = st.columns([2,2])
            with col_n:
                st.markdown(f"📄 `{f.name}`")
            with col_t:
                dtype = st.selectbox("Type", doc_type_options, key=f"etype_{fi}_{f.name[:20]}")
            new_docs.append({"name": f.name, "text": extract_docx_text(f), "doc_type": dtype})
        st.session_state.support_docs = new_docs

    # ── Summary of what's loaded ──────────────────────────────────────────────
    has_school = bool(st.session_state.school_plan_text)
    has_docs   = bool(st.session_state.support_docs)

    if not has_school and not has_docs:
        st.markdown('<div class="card-red">⚠️ Please upload at least one document before generating.</div>',
                    unsafe_allow_html=True)

    # ── Additional context ────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">Any additional context for the AI?</div>', unsafe_allow_html=True)
    extra_context = st.text_area(
        "Anything not in the documents that the AI should know about",
        height=80,
        placeholder="e.g. Xavier absconded from CLC grounds on 19/03/2026 — SAPOL ref 0732. Fence climb confirmed. Medication transition in progress from same date.",
        key="express_extra")

    if extra_context.strip():
        student = {**st.session_state.student, "clc_context":
                   st.session_state.student.get("clc_context","") + "\n" + extra_context}
    else:
        student = st.session_state.student

    st.markdown('<div class="sec-head">Review date</div>', unsafe_allow_html=True)
    st.session_state.review_date = st.text_input("Review date",
        value=st.session_state.review_date, placeholder="e.g. 19/05/2026",
        key="express_review_date")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,2])
    with col_a:
        if st.button("← Back"):
            st.session_state.step = 1; st.rerun()
    with col_b:
        ready = has_school or has_docs
        if st.button("⚡ Generate complete plan now", type="primary",
                     use_container_width=True, disabled=not ready):
            st.session_state.step = 6; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Express: AI generation + docx build + download
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 7:
    student = st.session_state.student

    st.markdown('<div class="sec-head">⚡ Generating your plan…</div>', unsafe_allow_html=True)

    # Only run generation once — cache result in session state
    if "express_result" not in st.session_state:
        prog = st.progress(0)
        status = st.empty()

        status.info("📄 Reading all documents and planning risk rows…")
        prog.progress(20)

        result = ai_generate_full_plan(
            student,
            st.session_state.school_plan_text,
            st.session_state.support_docs,
        )
        prog.progress(70)

        if result.get("error"):
            st.error(f"AI generation failed: {result['error']}")
            if st.button("← Try again"):
                st.session_state.step = 5; st.rerun()
            st.stop()

        st.session_state.risks            = result.get("risks", [])
        st.session_state.priority_actions = result.get("priority_actions", "")
        if not st.session_state.review_date:
            st.session_state.review_date  = result.get("review_date", "")
        st.session_state.express_result   = True

        status.info("🏗️ Building formatted document…")
        prog.progress(85)

    risks            = st.session_state.risks
    priority_actions = st.session_state.priority_actions
    review_date      = st.session_state.review_date

    # ── Show what was generated ───────────────────────────────────────────────
    n_risks = len([r for r in risks if r.get("issue_title","").strip()])
    st.markdown(f"""<div class="card-teal">
    ✅ <strong>AI generated {n_risks} risk rows</strong> from your documents.
    The complete plan is ready to download below.<br>
    <span style="font-size:0.85rem;color:#1A3530;">
    If anything looks off, switch to <em>Build step-by-step</em> mode to review and edit each risk.
    </span>
    </div>""", unsafe_allow_html=True)

    # Quick summary of risks
    with st.expander(f"Preview: {n_risks} risks identified"):
        for i, r in enumerate(risks):
            if not r.get("issue_title","").strip(): continue
            level = compute_risk_level(r.get("likelihood","D – Likely/frequently"),
                                       r.get("consequence","3 – Moderate"))
            col = risk_colour(level)
            st.markdown(
                f"**{i+1}. {r['issue_title']}** "
                f"<span style='color:{col};font-weight:700;font-size:0.85rem;'>[{level}]</span>",
                unsafe_allow_html=True)
            if r.get("issue_detail"):
                st.caption(r["issue_detail"][:120] + "…")

    # Quality warning — if risks seem generic/template-derived
    all_risk_text = " ".join(r.get("issue_detail","") + r.get("proactive","") for r in risks)
    if "Xavier" in all_risk_text or (n_risks >= 6 and all(
        any(t in r.get("issue_title","").lower() for t in ["abscond","fence","road","verbal","peer","staff safety","handover"])
        for r in risks if r.get("issue_title")
    )):
        st.markdown(f"""<div class="card-red">
        ⚠️ <strong>Quality check:</strong> The generated risks may be based on a template rather than
        {student['name']}'s specific documents. Before downloading, review each risk in the preview above
        and confirm it matches the documents you uploaded. If the content looks generic,
        click <em>Switch to step-by-step</em> below to review and correct individual risks.
        </div>""", unsafe_allow_html=True)

    # ── Build docx (reuse Step 6 helpers inline) ──────────────────────────────
    with st.spinner("Building document…"):

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

        def cbullet(cell, text, size=17, color="333333"):
            p = cell.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after  = Pt(1)
            arun(p, text, size=size, color=color)

        def render_content(cell, text):
            # Handle both string and list formats
            if isinstance(text, list):
                text = "\n".join(str(t) for t in text)
            else:
                text = str(text) if text else ""
            
            if not text.strip():
                cpara(cell, "(Not completed)", italic=True, color="888888"); return
            for line in text.splitlines():
                line = line.strip()
                if not line: continue
                if line.startswith("###"):
                    p = cell.add_paragraph()
                    p.paragraph_format.space_before = Pt(5)
                    p.paragraph_format.space_after  = Pt(2)
                    arun(p, line.lstrip("# "), bold=True, color=TEAL.lstrip("#"), size=16)
                elif line.startswith("•") or line.startswith("-") or line.startswith("*"):
                    cbullet(cell, line.lstrip("•-* "))
                else:
                    p = cell.add_paragraph()
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after  = Pt(2)
                    arun(p, line, size=17)

        doc = DocxDocument()
        sec = doc.sections[0]
        sec.page_width  = Cm(21); sec.page_height = Cm(29.7)
        for attr in ('left_margin','right_margin','top_margin','bottom_margin'):
            setattr(sec, attr, Cm(1.5))

        # Title
        t = doc.add_table(rows=1, cols=1); t.style='Table Grid'
        tc = t.rows[0].cells[0]; set_bg(tc, TEAL.lstrip("#")); set_borders(tc, TEAL.lstrip("#"))
        p1 = tc.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        arun(p1, "SAFETY & RISK MANAGEMENT PLAN", bold=True, size=28, color="FFFFFF")
        cpara(tc, f"{student['name']}  |  Cowandilla Learning Centre  |  LBU {student['program']} Program",
              size=18, color="FEF3C7", align=WD_ALIGN_PARAGRAPH.CENTER, sb=20, sa=40)
        doc.add_paragraph()

        # Student details
        det = doc.add_table(rows=3, cols=2); det.style='Table Grid'
        hdr = det.rows[0].cells[0].merge(det.rows[0].cells[1])
        set_bg(hdr, GREY_DARK.lstrip("#")); set_borders(hdr, TEAL.lstrip("#"))
        arun(hdr.paragraphs[0], "STUDENT DETAILS", bold=True, size=18, color="FFFFFF")
        details_l = [("Full Name", student['name']), ("Date of Birth", student['dob'] or "—"),
                     ("Age", student['age'] or "—"), ("EDSAS ID", student['edsas'] or "—")]
        details_r = [("Home School", student['home_school'] or "—"),
                     ("CLC Program", student['program']), ("Plan Date", student['plan_date'])]
        for ci, items in enumerate([details_l, details_r]):
            c = det.rows[1].cells[ci]; set_bg(c,"F2F6F6"); set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].clear()
            for label, val in items:
                p = c.add_paragraph()
                arun(p, f"{label}: ", bold=True, size=17, color=GREY_DARK.lstrip("#"))
                arun(p, val or "—", size=17)
        status_cell = det.rows[2].cells[0].merge(det.rows[2].cells[1])
        set_bg(status_cell, AMBER_LIGHT.lstrip("#")); set_borders(status_cell, AMBER.lstrip("#"))
        p = status_cell.paragraphs[0]
        arun(p, "Key staff: ", bold=True, size=17, color=AMBER.lstrip("#"))
        arun(p, student['key_staff'] or "—", size=17)
        if student.get('medical_notes'):
            p2 = status_cell.add_paragraph()
            arun(p2, "Medical/context: ", bold=True, size=16, color="666666")
            arun(p2, student['medical_notes'], size=16, italic=True)
        if student.get('clc_context'):
            p3 = status_cell.add_paragraph()
            arun(p3, "CLC context: ", bold=True, size=16, color="666666")
            arun(p3, student['clc_context'], size=16, italic=True)
        doc.add_paragraph()

        # Risk table
        h = doc.add_paragraph()
        arun(h, "IDENTIFIED RISKS AND MANAGEMENT STRATEGIES", bold=True, size=20, color=GREY_DARK.lstrip("#"))
        n = doc.add_paragraph()
        arun(n, "* Risk ratings use the Likelihood/Consequence matrix on page 2.",
             italic=True, size=14, color="666666")

        main = doc.add_table(rows=1, cols=4); main.style='Table Grid'
        for i, w in enumerate([Cm(5.2), Cm(2.0), Cm(7.2), Cm(8.6)]):
            for c in main.columns[i].cells: c.width = w
        for i, h in enumerate(["Concerning Issue","Risk Level *","Proactive Strategies","Procedure to Follow"]):
            c = main.rows[0].cells[i]; set_bg(c, TEAL.lstrip("#")); set_borders(c, TEAL.lstrip("#"))
            p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p, h, bold=True, size=17, color="FFFFFF")

        for r in risks:
            if not r.get("issue_title","").strip(): continue
            lk = r.get("likelihood","D – Likely/frequently")
            cq = r.get("consequence","3 – Moderate")
            level  = compute_risk_level(lk, cq)
            lhex   = RISK_COLOURS.get(level,"#888").lstrip("#")
            l_code = lk.split("–")[0].strip().split(" ")[0]
            c_code = cq.split("–")[0].strip().split(" ")[0]
            row = main.add_row()

            c0 = row.cells[0]; set_bg(c0,"D6EEEB"); set_borders(c0, TEAL.lstrip("#"))
            c0.paragraphs[0].clear()
            p = c0.paragraphs[0]; arun(p, r["issue_title"], bold=True, size=17, color=GREY_DARK.lstrip("#"))
            if r.get("issue_detail"):
                p2 = c0.add_paragraph(); p2.paragraph_format.space_before = Pt(4)
                arun(p2, r["issue_detail"], size=16)
            if r.get("behaviour_descriptors","").strip():
                ph = c0.add_paragraph(); ph.paragraph_format.space_before = Pt(5)
                arun(ph, "Characterised by:", bold=True, size=15, color=TEAL.lstrip("#"))
                
                # Handle both string (with newlines) and list formats
                bd_data = r["behaviour_descriptors"]
                if isinstance(bd_data, list):
                    bd_lines = bd_data
                else:
                    bd_lines = str(bd_data).splitlines()
                
                for bd in bd_lines:
                    bd = str(bd).strip()
                    if bd:
                        bp = c0.add_paragraph(style='List Bullet')
                        bp.paragraph_format.space_before = Pt(1); bp.paragraph_format.space_after = Pt(1)
                        arun(bp, bd.lstrip("•- "), size=15)
            if r.get("function","").strip():
                pf = c0.add_paragraph(); pf.paragraph_format.space_before = Pt(5)
                arun(pf, "Function: ", bold=True, size=15, color="555555")
                arun(pf, r["function"], size=15, italic=True)
            if r.get("clc_notes","").strip():
                pn = c0.add_paragraph(); pn.paragraph_format.space_before = Pt(5)
                arun(pn, "CLC: ", bold=True, size=14, color=AMBER.lstrip("#"))
                arun(pn, r["clc_notes"], size=14, italic=True)

            c1 = row.cells[1]; set_bg(c1, lhex); set_borders(c1, lhex)
            p1 = c1.paragraphs[0]; p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p1, f"{l_code}{c_code}", bold=True, size=26, color="FFFFFF")
            p2 = c1.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(p2, level, bold=True, size=14, color="FFFFFF")

            c2 = row.cells[2]; set_borders(c2, TEAL.lstrip("#"))
            c2.paragraphs[0].clear(); render_content(c2, r.get("proactive",""))

            c3 = row.cells[3]; set_borders(c3, TEAL.lstrip("#"))
            c3.paragraphs[0].clear(); render_content(c3, r.get("procedure",""))

        fn_row  = main.add_row()
        fn_cell = fn_row.cells[0].merge(fn_row.cells[1]).merge(fn_row.cells[2]).merge(fn_row.cells[3])
        set_bg(fn_cell,"F2F6F6"); set_borders(fn_cell, TEAL.lstrip("#"))
        arun(fn_cell.paragraphs[0], "* Refer to risk matrix on page 2.",
             italic=True, size=13, color="666666")
        doc.add_paragraph()

        # Priority actions
        if priority_actions.strip():
            pa_tbl = doc.add_table(rows=1, cols=1); pa_tbl.style='Table Grid'
            pa = pa_tbl.rows[0].cells[0]
            set_bg(pa, AMBER_LIGHT.lstrip("#")); set_borders(pa, AMBER.lstrip("#"))
            pa.paragraphs[0].clear()
            cpara(pa, "PRIORITY ACTIONS", bold=True, size=19, color=AMBER.lstrip("#"), sb=40, sa=60)
            for line in priority_actions.splitlines():
                line = line.strip()
                if not line: continue
                if line.startswith("•") or line.startswith("-"):
                    cbullet(pa, line.lstrip("•- "))
                else:
                    cpara(pa, line, size=17)
            doc.add_paragraph()


        # ── Staff Acknowledgement sign-off ─────────────────────────────────
        doc.add_paragraph()
        sh = doc.add_paragraph()
        arun(sh, "STAFF ACKNOWLEDGEMENT", bold=True, size=19, color=GREY_DARK.lstrip("#"))
        sn = doc.add_paragraph()
        arun(sn, "All staff working with this student must read this plan and sign below to confirm they understand the identified risks and their responsibilities.",
             size=15, italic=True)
        doc.add_paragraph()

        # Sign-off table — header + 8 blank rows
        SIGN_COLS = ["Staff Member Name", "Role", "Signature", "Date"]
        SIGN_WIDTHS_CM = [5.5, 4.0, 5.5, 2.5]
        stbl = doc.add_table(rows=9, cols=4); stbl.style='Table Grid'
        from docx.shared import Cm as _Cm
        for ci, w in enumerate(SIGN_WIDTHS_CM):
            for cell in stbl.columns[ci].cells:
                cell.width = _Cm(w)
        # Header row
        for ci, lbl in enumerate(SIGN_COLS):
            c = stbl.rows[0].cells[ci]
            set_bg(c, GREY_DARK.lstrip("#")); set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], lbl, bold=True, size=16, color="FFFFFF")
        # 8 blank signing rows
        for ri in range(1, 9):
            row = stbl.rows[ri]
            bg = "F2F6F6" if ri % 2 == 0 else "FFFFFF"
            for ci in range(4):
                c = row.cells[ci]
                set_bg(c, bg); set_borders(c, "CCCCCC")
                cpara(c, "", size=16, sb=60, sa=60)
        doc.add_paragraph()

        # Endorsement / review
        eh = doc.add_paragraph()
        arun(eh, "PLAN ENDORSEMENT", bold=True, size=19, color=GREY_DARK.lstrip("#"))
        doc.add_paragraph()
        sign_tbl = doc.add_table(rows=2, cols=3); sign_tbl.style='Table Grid'
        for ci, lbl in enumerate(["Prepared by (CLC staff)","Endorsed by (Principal/Leader)","Next Review Date"]):
            c = sign_tbl.rows[0].cells[ci]; set_bg(c, GREY_DARK.lstrip("#"))
            set_borders(c, TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], lbl, bold=True, size=16, color="FFFFFF")
        for ci, val in enumerate(["Name: ___________________________\nSignature: ______________________\nDate: _______________",
                                   "Name: ___________________________\nSignature: ______________________\nDate: _______________",
                                   review_date or "TBC"]):
            c = sign_tbl.rows[1].cells[ci]; set_bg(c,"F2F6F6"); set_borders(c, TEAL.lstrip("#"))
            for line in val.split('\n'):
                cpara(c, line, size=16, sb=20, sa=20)


        doc.add_page_break()

        # Risk matrix
        mh = doc.add_paragraph()
        arun(mh, "LEVEL OF RISK — REFERENCE MATRIX", bold=True, size=22, color=GREY_DARK.lstrip("#"))
        likelihoods = ["E – Almost Certain","D – Likely/Frequently","C – Likely Sometimes","B – Unlikely","A – Rare"]
        cons_labels = ["1 Insignificant","2 Minor","3 Moderate","4 Major","5 Catastrophic"]
        matrix_data = [["High","High","Extreme","Extreme","Extreme"],
                       ["Moderate","High","High","Extreme","Extreme"],
                       ["Low","Moderate","High","Extreme","Extreme"],
                       ["Low","Low","Moderate","High","Extreme"],
                       ["Low","Low","Moderate","High","High"]]
        fill_m = {"Extreme":"C0392B","High":"E67E22","Moderate":"F1C40F","Low":"27AE60"}
        text_m = {"Extreme":"FFFFFF","High":"FFFFFF","Moderate":"333333","Low":"FFFFFF"}
        mx = doc.add_table(rows=6, cols=6); mx.style='Table Grid'
        set_bg(mx.rows[0].cells[0], GREY_DARK.lstrip("#"))
        arun(mx.rows[0].cells[0].paragraphs[0], "Likelihood \\ Consequences",
             bold=True, size=13, color="FFFFFF")
        for ci, cl in enumerate(cons_labels):
            c = mx.rows[0].cells[ci+1]; set_bg(c, GREY_DARK.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            arun(c.paragraphs[0], cl, bold=True, size=13, color="FFFFFF")
        for ri, (lh, row_data) in enumerate(zip(likelihoods, matrix_data)):
            row = mx.rows[ri+1]
            set_bg(row.cells[0],"F2F6F6")
            arun(row.cells[0].paragraphs[0], lh, bold=True, size=13, color=GREY_DARK.lstrip("#"))
            for ci, val in enumerate(row_data):
                c = row.cells[ci+1]; set_bg(c, fill_m.get(val,"888888"))
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                arun(c.paragraphs[0], val, bold=True, size=13, color=text_m.get(val,"FFFFFF"))

        buf = io.BytesIO()
        doc.save(buf); buf.seek(0)

    # ── Language objectivity check ────────────────────────────────────────────
    exp_all_text = " ".join([
        r.get("issue_title","") + " " + r.get("issue_detail","") + " " +
        r.get("behaviour_descriptors","") + " " + r.get("proactive","") + " " + r.get("procedure","")
        for r in risks
    ])
    exp_lang_flags = check_language_objectivity(exp_all_text)
    if exp_lang_flags:
        st.markdown("""
        <div style="background:#fff8e6;border:2px solid #e8a125;border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem;">
        <div style="font-weight:700;color:#92400e;font-size:.9rem;margin-bottom:.5rem;">
        ⚠️ Language Review — Possible Subjective Terms Detected
        </div>
        <div style="font-size:.8rem;color:#78350f;margin-bottom:.5rem;">
        The plan may contain language that is open to individual interpretation.
        Use <strong>Switch to step-by-step to edit risks</strong> below to review and correct flagged items before downloading.
        </div>
        </div>""", unsafe_allow_html=True)
        for flag in exp_lang_flags:
            st.markdown(f'<div style="background:#fef9ee;border-left:3px solid #e8a125;border-radius:0 6px 6px 0;padding:.4rem .8rem;margin-bottom:.35rem;font-size:.8rem;color:#78350f;">⚠️ {flag}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#f0faf8;border:1.5px solid #1a7a6e;border-radius:10px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.85rem;color:#1a2e44;">
        ✅ <strong>Language check passed</strong> — no obvious subjective terms detected.
        </div>""", unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────────────────────────────
    safe  = student['name'].replace(" ","_").replace("/","")
    fname = f"Safety_Risk_Plan_{safe}_CLC_{student['plan_date'].replace('/','')}.docx"
    _ini = initials_from_name(student['name'])
    st.download_button("⬇️  Download Safety & Risk Plan (.docx)",
                       data=buf, file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       type="primary", use_container_width=True,
                       on_click=archive_once,
                       args=(f"srp_{_ini}_{student['plan_date']}",),
                       kwargs=dict(
                           source_tool="Safety & Risk Plan Builder",
                           doc_type="Safety & Risk Plan",
                           title=f"Safety & Risk Plan — {_ini} — {student['plan_date']}",
                           file_bytes=buf.getvalue() if hasattr(buf, "getvalue") else buf,
                           filename=f"Safety_Risk_Plan_{_ini}_CLC_{student['plan_date'].replace('/','')}.docx",
                           student_initials=_ini,
                           created_by=st.session_state.get("user_email", "unknown"),
                       ))

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("← Upload different documents"):
            del st.session_state["express_result"]
            st.session_state.step = 5; st.rerun()
    with col_b:
        if st.button("🧱 Switch to step-by-step to edit risks"):
            del st.session_state["express_result"]
            st.session_state.mode = "wizard"
            st.session_state.synthesis_done = True
            st.session_state.step = 6; st.rerun()
    with col_c:
        if st.button("🔄 Start a new plan"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
