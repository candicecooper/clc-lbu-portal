import streamlit as st
from supabase import create_client
import json
from datetime import date

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sensory Overview",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAL  = "#1A7A7A"
AMBER = "#C8760A"

st.markdown(f"""
<style>
    .stApp {{ background-color: #f5f7f7; }}
    h1 {{ color: {TEAL}; }}
    .section-header {{
        background: {TEAL}; color: white;
        padding: 8px 14px; border-radius: 6px;
        font-weight: 700; font-size: 1rem; margin-bottom: 6px;
    }}
    .priority-card {{
        padding: 10px 14px; border-radius: 6px; margin: 4px 0;
        background: white; border-left: 5px solid #ccc;
    }}
    .priority-card.high {{ border-left-color: #c62828; }}
    .priority-card.med  {{ border-left-color: #e65100; }}
    .priority-card.low  {{ border-left-color: #2e7d32; }}
    .priority-card .label {{ font-size: 0.75rem; font-weight: 700; color: #444; }}
    .priority-card .pval  {{ font-size: 1.1rem; font-weight: 800; }}
    .priority-card.high .pval {{ color: #c62828; }}
    .priority-card.med  .pval {{ color: #e65100; }}
    .priority-card.low  .pval {{ color: #2e7d32; }}
    .priority-card .sub {{ font-size: 0.75rem; color: #666; }}
    .student-badge {{
        background: {TEAL}; color: white;
        padding: 6px 14px; border-radius: 20px;
        font-weight: 700; display: inline-block; margin-bottom: 8px;
    }}
    div[data-testid="stCheckbox"] label {{ font-size: 0.9rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background: #e0ecec; border-radius: 6px 6px 0 0;
        color: {TEAL}; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ background: {TEAL} !important; color: white !important; }}
    .new-student-box {{
        background: #fff8e1; border: 2px dashed {AMBER};
        border-radius: 8px; padding: 14px; margin-top: 8px;
    }}
    /* ── Persistent section toggle ── */
    .sec-header {{
        display: flex; align-items: center; justify-content: space-between;
        background: white; border: 1px solid #d0e0e0;
        border-radius: 8px; padding: 10px 16px; margin: 6px 0;
        cursor: pointer; user-select: none;
    }}
    .sec-header:hover {{ background: #f0f8f8; }}
    .sec-left {{ display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 0.95rem; color: #1a1a1a; }}
    .sec-right {{ display: flex; align-items: center; gap: 10px; }}
    .sec-pill {{
        padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;
    }}
    .sec-pill.high {{ background: #fde8e8; color: #c62828; }}
    .sec-pill.med  {{ background: #fff3e0; color: #e65100; }}
    .sec-pill.low  {{ background: #e8f5e9; color: #2e7d32; }}
    .sec-body {{
        background: white; border: 1px solid #d0e0e0; border-top: none;
        border-radius: 0 0 8px 8px; padding: 14px 16px; margin-top: -8px; margin-bottom: 6px;
    }}
    div[data-testid="stButton"] button[kind="secondary"] {{
        background: transparent; border: none; padding: 0;
        font-size: 0.9rem; color: #555; text-align: left; width: 100%;
    }}
</style>
""", unsafe_allow_html=True)

# ── Supabase ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = "https://lvzaebjrxrgguypqvdcq.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx2emFlYmpyeHJnZ3V5cHF2ZGNxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDAzNDU2MSwiZXhwIjoyMDc5NjEwNTYxfQ.vw8nYDA-tnQVr-mAEAGFsxUkcYbB5J8ilv4ATCBnlOY"
    return create_client(url, key)

supabase = get_supabase()

# ── Section definitions ────────────────────────────────────────────────────────
SECTIONS = {
    "Body Awareness (Interoception)": {
        "icon": "🫀",
        "items": [
            "Able to name own emotions",
            "Able to recognise own emotions",
            "Knows when thirsty",
            "Knows when hungry",
            "Knows when they need to go to the toilet",
            "Able to say where hurts (accurately) when injured",
            "Knows when they feel unwell",
            "Knows when getting upset",
            "Gets distressed easily or frequently",
            "Knows when becoming anxious",
            "Gets anxious easily or frequently",
            "Knows when getting frustrated",
            "Knows when becoming angry",
            "Gets frustrated/angry easily",
            "Seems to react to the emotions of others/places",
        ],
    },
    "Visual": {
        "icon": "👁️",
        "items": [
            "Does not recognise familiar people in unfamiliar clothes or contexts",
            "Dislikes bright lights",
            "Dislikes fluorescent lights",
            "Avoids bright light",
            "Attracted to lights",
            "Attracted to shiny objects and bright colours",
            "Attracted to patterns and visual textures",
            "Attracted to darkness",
        ],
    },
    "Sense of Body in Space": {
        "icon": "🗺️",
        "items": [
            "Does not seem to know where body is in space",
            "Gets lost in familiar places/routes",
            "Remembers familiar places and routes",
            "Avoids escalators/travellators",
            "Dislikes crowds or being close to others",
            "Difficulties catching a ball",
            "Difficulties kicking a ball",
            "Appears to not see certain colours",
            "Walks into doors/people/objects",
            "Prefers to sit at the front of a group",
            "Prefers to sit at back of group",
        ],
    },
    "Auditory": {
        "icon": "👂",
        "items": [
            "Aversion to certain sounds",
            "Seeks or creates certain sounds",
            "Can hear sounds which others do not hear",
            "Bangs objects and doors",
            "Mumbles/talks/makes vocalisations to self constantly",
            "Changes vocalisations in reaction to environmental noises",
            "Changes vocalisations in reaction to emotional state",
        ],
    },
    "Auditory Processing": {
        "icon": "🔊",
        "items": [
            "Only seems to hear the first words of a sentence",
            "Can follow complex or multi-step instructions",
            "Can follow simple one step instructions",
            "Finds it easier to listen when not looking at person",
            "Echolalic (repeats phrases)",
        ],
    },
    "Smell": {
        "icon": "👃",
        "items": [
            "Avoids/dislikes certain everyday smells",
            "Attracted to certain smells",
        ],
    },
    "Touch and Textures": {
        "icon": "🤚",
        "items": [
            "Does not like shaking hands or being hugged",
            "Seeks/uses light touch",
            "Seeks/uses firm touch/deep pressure (incl. hitting)",
            "Aversion to certain fabrics/textures",
            "Attracted to certain fabrics/textures",
            "Very sensitive to pain and temperature",
            "Does not indicate sensitivity to pain or temperature",
            "Attracted to mouthing/chewing certain textures/things",
            "Avoids particular textures of food & drink",
            "Avoids particular colours/smells of food & drink",
            "Preference for food to not touch other food on plate",
        ],
    },
    "Kinaesthetic": {
        "icon": "🏃",
        "items": [
            "Tries to avoid using fine motor skills",
            "Enjoys using fine motor skills",
            "Difficulties with fine motor skills",
            "Tries to avoid running and/or climbing",
            "Enjoys running and/or climbing",
            "Difficulty running and/or climbing",
            "Tries to avoid riding a bike",
            "Enjoys riding a bike",
            "Poor balance",
            "Has extremely good balance",
            "Enjoys/seeks out swings",
            "Enjoys/seeks out trampolines",
            "Enjoys/seeks out slides",
            "Flaps hands when happy",
            "Flaps hands when anxious",
        ],
    },
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def priority_info(pct):
    if pct >= 60:
        return "HIGH PRIORITY", "high", "🔴"
    elif pct >= 30:
        return "MEDIUM PRIORITY", "med", "🟡"
    return "LOW PRIORITY", "low", "🟢"

def calc_priorities(responses):
    results = {}
    for sec, meta in SECTIONS.items():
        items = meta["items"]
        sec_resp = responses.get(sec, {})
        checked = sum(1 for it in items if sec_resp.get(it, False))
        pct = round((checked / len(items)) * 100, 1) if items else 0
        label, css, emoji = priority_info(pct)
        results[sec] = {"priority": label, "css": css, "emoji": emoji,
                        "checked": checked, "total": len(items), "pct": pct}
    return results

def priority_card(section_name, info, icon=""):
    return f"""
    <div class="priority-card {info['css']}">
        <div class="label">{icon} {section_name}</div>
        <div class="pval">{info['emoji']} {info['priority']}</div>
        <div class="sub">{info['checked']} / {info['total']} items ({info['pct']}%)</div>
    </div>"""

def load_all_overviews():
    try:
        res = supabase.table("sensory_overviews") \
            .select("*") \
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load overviews: {e}")
        return []

def generate_hypothesis(pr: dict) -> str:
    """
    Generate a functional hypothesis paragraph from priority results.
    Maps high/medium sensory areas to likely functional implications.
    """
    IMPLICATIONS = {
        "Body Awareness (Interoception)": (
            "difficulty recognising and regulating internal body signals, which may contribute to "
            "emotional dysregulation, delayed awareness of distress, and challenges in self-monitoring "
            "behaviour and physiological states"
        ),
        "Visual": (
            "heightened or reduced sensitivity to visual stimuli, which may affect attention, "
            "comfort in bright or busy environments, and ability to process visual information "
            "in classroom settings"
        ),
        "Sense of Body in Space": (
            "reduced proprioceptive or vestibular awareness, which may impact spatial orientation, "
            "gross motor coordination, and comfort in group or crowded environments"
        ),
        "Auditory": (
            "atypical auditory sensitivity, which may cause distress in noisy environments, "
            "difficulty filtering background noise, and use of self-generated sound as a "
            "regulatory strategy"
        ),
        "Auditory Processing": (
            "challenges processing verbal instructions, which may affect the ability to follow "
            "multi-step directions, retain spoken information, and engage in verbal learning tasks"
        ),
        "Smell": (
            "sensitivity to olfactory input, which may result in avoidance of certain environments, "
            "foods, or social situations due to smell-related discomfort"
        ),
        "Touch and Textures": (
            "tactile sensitivity or seeking behaviour, which may influence responses to physical "
            "contact, food textures, clothing, and the use of touch as a self-regulatory strategy"
        ),
        "Kinaesthetic": (
            "differences in movement processing and motor planning, which may affect participation "
            "in physical activities, use of movement as regulation, and fine motor task engagement"
        ),
    }

    STRATEGIES = {
        "Body Awareness (Interoception)": [
            "explicit interoception teaching (e.g. Zones of Regulation, body scan activities)",
            "regular check-in routines using visual emotion scales",
            "co-regulation support to build awareness of physiological cues",
        ],
        "Visual": [
            "reducing visual clutter in the learning environment",
            "offering tinted overlays, sunglasses, or alternative lighting options",
            "providing advance notice before entering visually stimulating spaces",
        ],
        "Sense of Body in Space": [
            "regular proprioceptive input (e.g. heavy work, wall push-ups, weighted items)",
            "clear spatial boundaries using visual markers or designated seating",
            "structured movement breaks throughout the day",
        ],
        "Auditory": [
            "use of noise-cancelling headphones or ear defenders in loud environments",
            "pre-warning before transitions to noisy settings",
            "providing a quiet withdrawal space for regulation",
        ],
        "Auditory Processing": [
            "breaking instructions into single steps with visual supports",
            "allowing processing time before expecting a response",
            "using written or visual instructions alongside verbal communication",
        ],
        "Smell": [
            "identifying and minimising exposure to trigger smells where possible",
            "offering scent-neutral toiletries and food options",
            "providing advance warning before entering areas with strong smells",
        ],
        "Touch and Textures": [
            "offering deep pressure input (e.g. weighted lap pad, compression clothing)",
            "providing advance warning before physical contact",
            "allowing flexibility around uniform, food textures, and tactile materials",
        ],
        "Kinaesthetic": [
            "embedding regular movement breaks and sensory circuits",
            "offering alternative seating (e.g. wobble cushion, standing desk)",
            "using movement-based learning activities where possible",
        ],
    }

    high = [(s, i) for s, i in pr.items() if i.get("priority") == "HIGH PRIORITY"]
    med  = [(s, i) for s, i in pr.items() if i.get("priority") == "MEDIUM PRIORITY"]

    if not high and not med:
        return ("Based on the completed overview, no sensory areas were identified as high or "
                "medium priority at this time. Continued monitoring is recommended.")

    # Build hypothesis
    priority_areas = [s for s, _ in high] + [s for s, _ in med]
    implications   = [IMPLICATIONS[s] for s in priority_areas if s in IMPLICATIONS]

    if len(implications) == 1:
        impl_text = implications[0]
    elif len(implications) == 2:
        impl_text = f"{implications[0]}, and {implications[1]}"
    else:
        impl_text = "; ".join(implications[:-1]) + f"; and {implications[-1]}"

    area_names = []
    for s, _ in high:
        area_names.append(f"{s} (HIGH)")
    for s, _ in med:
        area_names.append(f"{s} (MEDIUM)")

    hypothesis = (
        f"Based on the completed sensory overview, {', '.join(area_names[:3])}"
        f"{'and other areas ' if len(area_names) > 3 else ''}"
        f" {'were' if len(area_names) > 1 else 'was'} identified as priority areas. "
        f"From what has been observed, it is suggested that this student may experience {impl_text}. "
        f"These observed sensory differences may be contributing to behaviours including "
        f"emotional dysregulation, avoidance, sensory-seeking, or difficulty sustaining "
        f"engagement in the learning environment. This is based on staff observation only "
        f"and does not constitute a clinical assessment."
    )

    # Strategies
    all_strategies = []
    for s in priority_areas[:4]:
        if s in STRATEGIES:
            all_strategies.extend(STRATEGIES[s][:2])

    return hypothesis, all_strategies[:6]


def generate_word_report(rec: dict) -> bytes:
    """Generate a clean, editable Word document sensory overview report."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from io import BytesIO

    sname    = rec.get("student_name", "Unknown")
    ov_date  = rec.get("overview_date", "—")
    rev_date = rec.get("review_date",   "—")
    by       = rec.get("completed_by",  "—")

    try:
        pr = rec.get("priority_results") or {}
        if isinstance(pr, str):
            pr = json.loads(pr)
    except Exception:
        pr = {}

    try:
        resp = rec.get("responses") or {}
        if isinstance(resp, str):
            resp = json.loads(resp)
    except Exception:
        resp = {}

    hyp_result = generate_hypothesis(pr)
    if isinstance(hyp_result, tuple):
        hyp_text, strategies = hyp_result
    else:
        hyp_text, strategies = hyp_result, []

    # Colours
    TEAL_RGB  = RGBColor(0x1A, 0x7A, 0x7A)
    AMBER_RGB = RGBColor(0xC8, 0x76, 0x0A)
    HIGH_RGB  = RGBColor(0xC6, 0x28, 0x28)
    MED_RGB   = RGBColor(0xE6, 0x51, 0x00)
    LOW_RGB   = RGBColor(0x2E, 0x7D, 0x32)
    WHITE     = RGBColor(0xFF, 0xFF, 0xFF)

    def hex_to_rgb_str(r, g, b):
        return f"{r:02X}{g:02X}{b:02X}"

    TEAL_HEX  = "1A7A7A"
    AMBER_HEX = "C8760A"
    HIGH_HEX  = "C62828"
    MED_HEX   = "E65100"
    LOW_HEX   = "2E7D32"
    HIGH_BG   = "FFF8F8"
    MED_BG    = "FFFAF5"
    LOW_BG    = "F6FFF6"

    def set_cell_bg(cell, hex_colour):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  hex_colour)
        tcPr.append(shd)

    def set_cell_borders(cell, colour_hex="DDDDDD"):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement("w:tcBorders")
        for side in ["top","left","bottom","right"]:
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"),   "single")
            el.set(qn("w:sz"),    "4")
            el.set(qn("w:color"), colour_hex)
            tcBorders.append(el)
        tcPr.append(tcBorders)

    def add_heading(doc, text, colour_hex=TEAL_HEX, size=13):
        p   = doc.add_paragraph()
        run = p.add_run(text)
        run.bold      = True
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(
            int(colour_hex[0:2],16),
            int(colour_hex[2:4],16),
            int(colour_hex[4:6],16),
        )
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after  = Pt(2)
        # Bottom border
        pPr  = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bot  = OxmlElement("w:bottom")
        bot.set(qn("w:val"),   "single")
        bot.set(qn("w:sz"),    "6")
        bot.set(qn("w:color"), colour_hex)
        pBdr.append(bot)
        pPr.append(pBdr)
        return p

    def pri_colours(pct):
        if pct >= 60:   return "HIGH PRIORITY 🔴",   HIGH_HEX, HIGH_BG
        elif pct >= 30: return "MEDIUM PRIORITY 🟡", MED_HEX,  MED_BG
        return "LOW PRIORITY 🟢",    LOW_HEX,  LOW_BG

    doc = Document()

    # ── Page margins ───────────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin   = Cm(2.0)
        section.right_margin  = Cm(2.0)

    # ── Header banner ──────────────────────────────────────────────────────────
    banner = doc.add_table(rows=1, cols=1)
    banner.style = "Table Grid"
    cell = banner.cell(0, 0)
    set_cell_bg(cell, TEAL_HEX)
    cell.paragraphs[0].clear()
    r1 = cell.paragraphs[0].add_run("🧠  Sensory Overview Report")
    r1.bold = True
    r1.font.size  = Pt(16)
    r1.font.color.rgb = WHITE
    cell.paragraphs[0].paragraph_format.space_before = Pt(6)
    cell.paragraphs[0].paragraph_format.space_after  = Pt(2)

    p2 = cell.add_paragraph()
    p2.add_run(f"Cowandilla Learning Centre · Learning & Behaviour Unit")
    p2.runs[0].font.size      = Pt(9)
    p2.runs[0].font.color.rgb = WHITE
    p2.paragraph_format.space_after = Pt(6)

    doc.add_paragraph()  # spacer

    # ── Student details table ──────────────────────────────────────────────────
    dtbl = doc.add_table(rows=2, cols=4)
    dtbl.style = "Table Grid"
    labels = ["Student", "Overview Date", "Review Date", "Completed by"]
    values = [sname, ov_date, rev_date, by]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        hcell = dtbl.rows[0].cells[i]
        vcell = dtbl.rows[1].cells[i]
        set_cell_bg(hcell, TEAL_HEX)
        set_cell_bg(vcell, "E8F4F4")
        hp = hcell.paragraphs[0]
        hp.clear()
        hr = hp.add_run(lbl)
        hr.bold = True
        hr.font.size      = Pt(8)
        hr.font.color.rgb = WHITE
        vp = vcell.paragraphs[0]
        vp.clear()
        vr = vp.add_run(val)
        vr.font.size = Pt(9)

    doc.add_paragraph()

    # ── Priority Summary ───────────────────────────────────────────────────────
    add_heading(doc, "Priority Summary")

    pr_items = list(pr.items())
    # 4 columns
    for i in range(0, len(pr_items), 4):
        chunk = pr_items[i:i+4]
        tbl   = doc.add_table(rows=3, cols=len(chunk))
        tbl.style = "Table Grid"
        for ci, (sec, info) in enumerate(chunk):
            pct         = info.get("pct", 0)
            lbl, col_hex, bg_hex = pri_colours(pct)
            icon        = SECTIONS.get(sec, {}).get("icon", "")

            # Row 0 — section name
            c0 = tbl.rows[0].cells[ci]
            set_cell_bg(c0, "F0F8F8")
            p0 = c0.paragraphs[0]
            p0.clear()
            r0 = p0.add_run(f"{icon} {sec}")
            r0.bold      = True
            r0.font.size = Pt(8)

            # Row 1 — priority label
            c1 = tbl.rows[1].cells[ci]
            set_cell_bg(c1, bg_hex)
            p1 = c1.paragraphs[0]
            p1.clear()
            r1 = p1.add_run(lbl)
            r1.bold = True
            r1.font.size = Pt(9)
            r1.font.color.rgb = RGBColor(
                int(col_hex[0:2],16), int(col_hex[2:4],16), int(col_hex[4:6],16)
            )

            # Row 2 — count
            c2 = tbl.rows[2].cells[ci]
            set_cell_bg(c2, bg_hex)
            p2 = c2.paragraphs[0]
            p2.clear()
            r2 = p2.add_run(f"{info.get('checked',0)}/{info.get('total',0)} items ({pct}%)")
            r2.font.size = Pt(7.5)
            r2.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

        doc.add_paragraph()

    # ── Hypothesis ─────────────────────────────────────────────────────────────
    add_heading(doc, "Hypothesis from Observed Sensory Profile", AMBER_HEX)
    p = doc.add_paragraph(hyp_text)
    p.paragraph_format.space_after = Pt(6)
    p.runs[0].font.size = Pt(10)

    if strategies:
        add_heading(doc, "Suggested Supports to Explore", TEAL_HEX, size=11)
        for strat in strategies:
            bp = doc.add_paragraph(style="List Bullet")
            bp.add_run(strat.capitalize()).font.size = Pt(10)

    # ── Page break ─────────────────────────────────────────────────────────────
    doc.add_page_break()

    # ── Page 2 header ──────────────────────────────────────────────────────────
    p2h = doc.add_paragraph()
    r   = p2h.add_run(f"Sensory Overview — {sname}  ·  Checked Items Detail")
    r.bold            = True
    r.font.size       = Pt(13)
    r.font.color.rgb  = TEAL_RGB
    p2h.paragraph_format.space_after = Pt(6)

    # ── Checked items ──────────────────────────────────────────────────────────
    any_checked = False
    for sec_name, items_dict in resp.items():
        checked = [it for it, val in items_dict.items() if val]
        if not checked:
            continue
        any_checked = True
        icon    = SECTIONS.get(sec_name, {}).get("icon", "")
        pct     = round(len(checked) / max(len(items_dict), 1) * 100, 1)
        lbl, col_hex, bg_hex = pri_colours(pct)

        # Section header row
        shdr = doc.add_table(rows=1, cols=1)
        shdr.style = "Table Grid"
        sc = shdr.cell(0, 0)
        set_cell_bg(sc, col_hex)
        sp = sc.paragraphs[0]
        sp.clear()
        sr = sp.add_run(f"{icon}  {sec_name}  ·  {lbl}  ({len(checked)}/{len(items_dict)} items)")
        sr.bold           = True
        sr.font.size      = Pt(9)
        sr.font.color.rgb = WHITE

        # Items in two columns
        left_items  = checked[::2]
        right_items = checked[1::2]
        rows        = max(len(left_items), len(right_items))
        itbl        = doc.add_table(rows=rows, cols=2)
        itbl.style  = "Table Grid"
        for ri in range(rows):
            lc = itbl.rows[ri].cells[0]
            rc = itbl.rows[ri].cells[1]
            set_cell_bg(lc, bg_hex)
            set_cell_bg(rc, bg_hex)
            if ri < len(left_items):
                lp = lc.paragraphs[0]
                lp.clear()
                lp.add_run(f"✅  {left_items[ri]}").font.size = Pt(9)
            if ri < len(right_items):
                rp = rc.paragraphs[0]
                rp.clear()
                rp.add_run(f"✅  {right_items[ri]}").font.size = Pt(9)

        doc.add_paragraph()

    if not any_checked:
        doc.add_paragraph("No items were checked in this overview.").runs[0].font.size = Pt(10)

    # ── Footer note ────────────────────────────────────────────────────────────
    doc.add_paragraph()
    fp = doc.add_paragraph(
        f"Cowandilla Learning Centre · Learning & Behaviour Unit · "
        f"Generated {date.today().strftime('%d %B %Y')} · "
        f"Based on staff observation only — not a clinical assessment."
    )
    fp.runs[0].font.size      = Pt(7.5)
    fp.runs[0].font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
    fp.paragraph_format.space_before = Pt(12)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Session state ──────────────────────────────────────────────────────────────
if "responses" not in st.session_state:
    st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
if "saved_ok" not in st.session_state:
    st.session_state.saved_ok = False
if "section_open" not in st.session_state:
    st.session_state.section_open = {sec: False for sec in SECTIONS}
if "editing_mode" not in st.session_state:
    st.session_state.editing_mode = False
if "edit_record_id" not in st.session_state:
    st.session_state.edit_record_id = None

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("<h1>🧠 Sensory Overview</h1>", unsafe_allow_html=True)

# Check for ?student_id= query param (deep-link from behaviour app)
params = st.query_params
deep_link_id   = params.get("student_id", None)
deep_link_name = params.get("student_name", None)

tab_new, tab_past = st.tabs(["📝  New Overview", "📋  Past Overviews"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NEW OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_new:

    if st.session_state.saved_ok:
        st.success("✅ Overview saved successfully!")
        if st.button("Start another overview"):
            st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
            st.session_state.saved_ok        = False
            st.session_state.editing_mode    = False
            st.session_state.edit_record_id  = None
            st.rerun()

    # Editing mode banner
    if st.session_state.editing_mode:
        st.info(f"✏️ **Editing overview** for **{st.session_state.get('edit_student','')}** "
                f"· Originally completed {st.session_state.get('edit_ov_date','—')} "
                f"by {st.session_state.get('edit_by','—')}. "
                f"Make changes and save to update.")
        if st.button("✖ Cancel edit — start fresh instead"):
            st.session_state.responses       = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
            st.session_state.editing_mode    = False
            st.session_state.edit_record_id  = None
            st.rerun()

    # ── Student details ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 👤 Student")

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            student_name = st.text_input(
                "Student name *",
                value=st.session_state.get("edit_student", deep_link_name or ""),
                placeholder="Full name",
            )
        with sc2:
            program = st.selectbox("Program *", ["— Select —", "JP", "PY", "SY"])
        with sc3:
            completed_by = st.text_input(
                "Completed by *",
                value=st.session_state.get("edit_by", "") if st.session_state.editing_mode else "",
                placeholder="Staff name",
            )

        selected_student_id = deep_link_id

        oc1, oc2 = st.columns(2)
        with oc1:
            overview_date = st.date_input("Overview Date", value=date.today())
        with oc2:
            review_date = st.date_input("Review Date")

    # ── Existing overviews for this student (by name match) ────────────────────
    if student_name.strip():
        try:
            existing = supabase.table("sensory_overviews") \
                .select("overview_date,completed_by,priority_results") \
                .ilike("student_name", student_name.strip()) \
                .order("overview_date", desc=True).limit(1).execute()
            if existing.data:
                prev = existing.data[0]
                with st.expander(
                    f"ℹ️ Previous overview exists — {prev['overview_date']} (by {prev['completed_by']})",
                    expanded=False,
                ):
                    try:
                        pr = prev["priority_results"]
                        if isinstance(pr, str):
                            pr = json.loads(pr)
                        cols = st.columns(4)
                        for idx, (sec, info) in enumerate(pr.items()):
                            icon = SECTIONS.get(sec, {}).get("icon", "")
                            _, css, emoji = priority_info(info.get("pct", 0))
                            info["css"] = css
                            info["emoji"] = emoji
                            with cols[idx % 4]:
                                st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)
                    except Exception:
                        pass
        except Exception:
            pass

    st.markdown("---")

    # ── Checklist sections ─────────────────────────────────────────────────────
    st.markdown("#### Checklist — tick all items that apply")

    # Expand / collapse all controls
    ctrl1, ctrl2 = st.columns([1, 1])
    with ctrl1:
        if st.button("⬇️  Expand all sections", use_container_width=True):
            for sec in SECTIONS:
                st.session_state.section_open[sec] = True
            st.rerun()
    with ctrl2:
        if st.button("⬆️  Collapse all sections", use_container_width=True):
            for sec in SECTIONS:
                st.session_state.section_open[sec] = False
            st.rerun()

    for sec_name, meta in SECTIONS.items():
        icon  = meta["icon"]
        items = meta["items"]
        sec_resp      = st.session_state.responses.get(sec_name, {})
        checked_count = sum(1 for it in items if sec_resp.get(it, False))
        pct           = round((checked_count / len(items)) * 100) if items else 0
        _, css, emoji = priority_info(pct)
        is_open       = st.session_state.section_open.get(sec_name, False)
        chevron       = "🔽" if is_open else "▶️"

        # Header row — clicking the button toggles open/closed
        hdr_col, btn_col = st.columns([8, 1])
        with hdr_col:
            st.markdown(
                f"""<div class="sec-header">
                    <div class="sec-left">{icon} <span>{sec_name}</span></div>
                    <div class="sec-right">
                        <span class="sec-pill {css}">{emoji} {checked_count}/{len(items)}</span>
                        <span style="color:#888;font-size:0.85rem;">{chevron}</span>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with btn_col:
            # Invisible toggle button aligned over the header
            if st.button(
                chevron,
                key=f"toggle_{sec_name}",
                help=f"{'Collapse' if is_open else 'Expand'} {sec_name}",
                use_container_width=True,
            ):
                st.session_state.section_open[sec_name] = not is_open
                st.rerun()

        # Body — only rendered when open, state persists through checkbox reruns
        if is_open:
            with st.container(border=True):
                cols = st.columns(2)
                for i, item in enumerate(items):
                    with cols[i % 2]:
                        val = st.checkbox(
                            item,
                            value=st.session_state.responses[sec_name].get(item, False),
                            key=f"chk_{sec_name}_{item}",
                        )
                        st.session_state.responses[sec_name][item] = val

    st.markdown("---")

    # ── Results summary ────────────────────────────────────────────────────────
    st.markdown("#### Results Summary")
    priorities = calc_priorities(st.session_state.responses)
    cols = st.columns(4)
    for idx, (sec, info) in enumerate(priorities.items()):
        icon = SECTIONS[sec]["icon"]
        with cols[idx % 4]:
            st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)

    st.markdown("---")

    # ── Save ───────────────────────────────────────────────────────────────────
    btn_col, clr_col = st.columns([3, 1])
    with btn_col:
        if st.button("💾  Save Overview", type="primary", use_container_width=True):
            if not student_name.strip():
                st.error("Please enter a student name before saving.")
            elif program == "— Select —":
                st.error("Please select a program.")
            else:
                store_priorities = {
                    sec: {"priority": v["priority"], "checked": v["checked"],
                          "total": v["total"], "pct": v["pct"]}
                    for sec, v in priorities.items()
                }
                payload = {
                    "student_id":       selected_student_id,
                    "student_name":     student_name.strip(),
                    "overview_date":    str(overview_date),
                    "review_date":      str(review_date),
                    "completed_by":     completed_by.strip(),
                    "responses":        json.dumps(st.session_state.responses),
                    "priority_results": json.dumps(store_priorities),
                }
                try:
                    if st.session_state.editing_mode and st.session_state.edit_record_id:
                        # Update existing record
                        supabase.table("sensory_overviews") \
                            .update(payload) \
                            .eq("id", st.session_state.edit_record_id) \
                            .execute()
                    else:
                        # Insert new record
                        supabase.table("sensory_overviews").insert(payload).execute()
                    st.session_state.saved_ok       = True
                    st.session_state.editing_mode   = False
                    st.session_state.edit_record_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with clr_col:
        if st.button("🗑️  Clear", use_container_width=True):
            st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PAST OVERVIEWS
# ══════════════════════════════════════════════════════════════════════════════
with tab_past:
    st.markdown("#### Past Sensory Overviews")
    records = load_all_overviews()

    if not records:
        st.info("No overviews saved yet.")
    else:
        f1, f2 = st.columns([2, 2])
        with f1:
            student_names = sorted(set(
                (r.get("students") or {}).get("name") or r.get("student_name", "Unknown")
                for r in records
            ))
            sel_student = st.selectbox("Filter by student", ["— All —"] + student_names)
        with f2:
            search = st.text_input("Search by staff / date", placeholder="e.g. Candice or 2026-03")

        filtered = records
        if sel_student != "— All —":
            filtered = [r for r in filtered if
                        ((r.get("students") or {}).get("name") or r.get("student_name")) == sel_student]
        if search:
            s = search.lower()
            filtered = [r for r in filtered if
                        s in (r.get("completed_by") or "").lower()
                        or s in (r.get("overview_date") or "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(records)} records")

        for rec in filtered:
            sname    = rec.get("student_name", "Unknown")
            ov_date  = rec.get("overview_date", "—")
            by       = rec.get("completed_by", "—")
            rev_date = rec.get("review_date", "—")

            with st.expander(
                f"**{sname}** · {ov_date} · {by}",
                expanded=False
            ):
                st.markdown(f"**Review date:** {rev_date}")

                try:
                    pr = rec["priority_results"]
                    if isinstance(pr, str):
                        pr = json.loads(pr)
                except Exception:
                    pr = {}

                if pr:
                    p_cols = st.columns(4)
                    for idx, (sec, info) in enumerate(pr.items()):
                        icon = SECTIONS.get(sec, {}).get("icon", "")
                        _, css, emoji = priority_info(info.get("pct", 0))
                        info["css"] = css
                        info["emoji"] = emoji
                        with p_cols[idx % 4]:
                            st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)

                if st.toggle("Show checked items", key=f"detail_{rec['id']}"):
                    try:
                        resp = rec["responses"]
                        if isinstance(resp, str):
                            resp = json.loads(resp)
                    except Exception:
                        resp = {}
                    for sec_name, items_dict in resp.items():
                        icon = SECTIONS.get(sec_name, {}).get("icon", "")
                        checked_items = [it for it, val in items_dict.items() if val]
                        if checked_items:
                            st.markdown(f"**{icon} {sec_name}**")
                            for it in checked_items:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;✅ {it}")

                st.markdown("---")

                # ── Action buttons ─────────────────────────────────────────────
                ac1, ac2, ac3 = st.columns(3)

                # Download report
                with ac1:
                    try:
                        doc_bytes = generate_word_report(rec)
                        fname = f"sensory_{sname.replace(' ','_')}_{ov_date}.docx"
                        st.download_button(
                            "📄 Download Word Report",
                            data=doc_bytes,
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"dl_{rec['id']}",
                        )
                    except Exception as e:
                        st.error(f"Report generation failed: {e}")

                # Edit / add to overview
                with ac2:
                    if st.button("✏️ Edit / Add to Overview", key=f"edit_{rec['id']}", use_container_width=True):
                        # Load this record into session state for editing
                        try:
                            resp = rec["responses"]
                            if isinstance(resp, str):
                                resp = json.loads(resp)
                            st.session_state.responses = resp
                        except Exception:
                            st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
                        st.session_state.edit_record_id  = rec["id"]
                        st.session_state.edit_student    = sname
                        st.session_state.edit_ov_date    = ov_date
                        st.session_state.edit_rev_date   = rev_date
                        st.session_state.edit_by         = by
                        st.session_state.editing_mode    = True
                        st.session_state.saved_ok        = False
                        st.rerun()

                # Delete
                with ac3:
                    if st.button("🗑️ Delete", key=f"del_{rec['id']}", use_container_width=True):
                        try:
                            supabase.table("sensory_overviews").delete().eq("id", rec["id"]).execute()
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
