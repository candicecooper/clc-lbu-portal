import streamlit as st
import os as _os
from datetime import date, timedelta, datetime
import database as db
import json
import time as _time

st.set_page_config(
    page_title="CLC Daily Bulletin",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

try:
    from auth import logout_button
except ImportError:
    # auth.py doesn't provide logout_button in this deployment —
    # the page has its own logout controls, so fall back to a no-op.
    def logout_button(*_args, **_kwargs):
        return None
logout_button("sidebar")

# ── DESIGN SYSTEM ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"]{background:#f0f4f0!important;font-family:'DM Sans',sans-serif}
[data-testid="stAppViewContainer"]{padding:0}
[data-testid="stHeader"]{display:none}
[data-testid="stSidebar"]{display:none}
#MainMenu,footer,.stDeployButton{display:none}
/* Was `.main .block-container` — this Streamlit version has no `.main`
   ancestor class any more, so that selector matched nothing and the
   page has been carrying Streamlit's default ~6rem/5rem/10rem block
   padding this whole time (confirmed by measuring the live preview).
   Target the real testid instead, with the class kept as a fallback. */
[data-testid="stMainBlockContainer"],.block-container{padding:0 1.5rem 2rem!important;max-width:1600px!important;margin:0 auto!important}
/* The bars below want to run edge-to-edge despite that new side padding —
   same bleed trick as the header-bar's own vertical margin below. */
.top-nav,.quicknav,.bulletin-hero,.st-key-header_bar{margin-left:-1.5rem;margin-right:-1.5rem}
.top-nav{background:#1a2e44;padding:0 2rem;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000;box-shadow:0 2px 12px rgba(0,0,0,0.2)}
.top-nav-left{display:flex;align-items:center;gap:.75rem}
.top-nav-logo{width:32px;height:32px;background:linear-gradient(135deg,#6BBF4E,#4a8f33);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:.85rem}
.top-nav-title{font-family:'DM Sans',sans-serif;font-weight:700;font-size:.95rem;color:white;letter-spacing:.02em}
.top-nav-sub{font-size:.72rem;color:rgba(255,255,255,0.5);letter-spacing:.06em;text-transform:uppercase}
.nav-badge{background:rgba(107,191,78,0.2);border:1px solid rgba(107,191,78,0.4);color:#6BBF4E;font-size:.72rem;font-weight:600;padding:.2rem .6rem;border-radius:20px;letter-spacing:.05em}
.nav-badge.edit{background:rgba(232,161,37,0.2);border-color:rgba(232,161,37,0.4);color:#e8a125}
.bulletin-hero{background:linear-gradient(135deg,#3d7a28 0%,#6BBF4E 60%,#8fd468 100%);padding:1.75rem 2rem 1.5rem;position:relative;overflow:hidden}
.bulletin-hero::before{content:'';position:absolute;top:-40px;right:-40px;width:200px;height:200px;background:rgba(255,255,255,0.06);border-radius:50%}
.bulletin-hero-inner{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;position:relative;z-index:1}
.bulletin-date-label{font-family:'DM Mono',monospace;font-size:.7rem;color:rgba(255,255,255,0.7);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.3rem}
.bulletin-date-main{font-family:'Playfair Display',serif;font-size:2rem;color:white;font-weight:700;line-height:1.1}
.bulletin-date-sub{font-size:.85rem;color:rgba(255,255,255,0.75);margin-top:.25rem;font-weight:400}
/* .content-area itself carries no layout CSS any more — it's a div
   opened by one st.markdown() call and never closed by a matching one,
   so (like every other st.markdown-only "wrapper" in the old code) it
   renders as an empty, self-closing fragment that never actually wraps
   the real content after it. Real padding/max-width/centering now live
   on [data-testid="stMainBlockContainer"] above, which is a genuine
   ancestor of everything on the page. The class stays in the markup
   only as a hook for the .editing variant below, applied via a
   conditional <style> block injected right where `edit` is known
   (see EDIT_MODE_CSS) rather than a descendant selector — the same
   phantom-div problem means `.content-area.editing sometyzhing` can
   never match a real descendant either, no matter what selector is
   used to try to reach through it. ────────────────────────────── */
.hero-edit-badge{position:absolute;top:16px;right:22px;z-index:2;background:#e8a125;color:#1a2e44;font-size:.68rem;font-weight:800;letter-spacing:.06em;padding:.3rem .8rem;border-radius:20px;box-shadow:0 2px 6px rgba(0,0,0,0.15)}
/* ── Unified header control bar ───────────────────────────────
   Replaces three separately-boxed banners (week nav / jump-to-date /
   button row) stacked on top of each other with one calmer container,
   so the page reads as "hero, then one control strip" rather than a
   pile of cards before you even reach content. */
.st-key-header_bar{background:white;border-radius:0 0 14px 14px;padding:.65rem 1.5rem .85rem;margin-bottom:-2rem;box-shadow:0 2px 10px rgba(0,0,0,0.05);border:none;position:relative;z-index:2}
.st-key-header_bar .week-label{text-align:center;padding:.45rem 0;font-size:.78rem;font-weight:600}
/* ── Palette refresh ──────────────────────────────────────────
   Previously 7 near-random header colors (green/navy/brown/blue/
   purple/slate/red) with no shared meaning — busy without being
   informative. Down to 4 colors that each mean something:
   green = people/presence on site, navy = general information
   (the default), amber = a highlighted/responsibility item, red =
   a change or alert that needs a second look. Applied via
   .card-header (see the `card()` helper) rather than the old
   .section-card-header, which no longer has any markup using it.
/* ── Real card container (st.container(border=True)-based) ──────
   .card-header bleeds out to the edges of Streamlit's own bordered
   container using a negative margin equal to its default padding, so
   the colored strip reaches edge-to-edge while the body content below
   keeps that same padding naturally (no extra wrapper div needed).
   Targeted by the container's own st-key-card_* class rather than
   [data-testid="stVerticalBlockBorderWrapper"] — this Streamlit
   version applies border/radius directly to the stVerticalBlock
   element itself and never renders that wrapper div, so a selector
   built around it silently matches nothing. */
div.stVerticalBlock[class*="st-key-card_"]{
    border-radius:12px!important;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);border-color:#e9eee7!important;
}
.card-header{margin:-1rem -1rem .75rem;padding:.5rem 1rem;display:flex;align-items:center;gap:.5rem;
    height:2.15rem;overflow:hidden;line-height:1.15;font-size:.72rem;font-weight:700;color:white;
    text-transform:uppercase;letter-spacing:.1em;white-space:nowrap}
.card-header.green{background:#6BBF4E}
.card-header.navy,.card-header.brown,.card-header.blue,.card-header.purple,.card-header.slate{background:#1a2e44}
.card-header.amber{background:#e8a125;color:#1a2e44}
.card-header.red{background:#c0392b}
.data-table{width:100%;border-collapse:collapse;font-size:.78rem}
.data-table th{background:#f4f8f2;color:#4a6640;font-weight:600;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;padding:.4rem .6rem;text-align:left;border-bottom:2px solid #d8ead2}
.data-table td{padding:.4rem .6rem;border-bottom:1px solid #f0f4ee;color:#2a3a2a;vertical-align:top}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:hover td{background:#fafcf9}
.change-badge{background:#fee2e2;color:#b91c1c;padding:.1rem .45rem;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.kitchen-row td{background:#fff8e6!important;font-weight:600}
.kitchen-badge{background:#e8a125;color:#1a2e44;padding:.15rem .5rem;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.vehicle-time{font-family:'DM Mono',monospace;font-size:.72rem;color:#888}
.vehicle-booking{background:#e8f5e1;color:#2d6b1a;padding:.1rem .4rem;border-radius:4px;font-size:.75rem;font-weight:500}
[data-baseweb="tab-list"]{background:transparent!important;gap:.25rem!important;border-bottom:2px solid #e0e8dc!important;padding:0!important}
[data-baseweb="tab"]{background:transparent!important;border-radius:8px 8px 0 0!important;padding:.5rem 1rem!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important;font-weight:600!important;color:#7a907a!important;border:none!important}
[aria-selected="true"][data-baseweb="tab"]{background:white!important;color:#4a8f33!important;border-bottom:2px solid #6BBF4E!important}
[data-baseweb="tab-panel"]{padding:1rem 0 0!important}
.stTextInput input,.stTextArea textarea,.stSelectbox select{border:1.5px solid #d8e8d4!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important;background:white!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:#6BBF4E!important;box-shadow:0 0 0 3px rgba(107,191,78,0.15)!important}
label[data-testid="stWidgetLabel"] p{font-size:.72rem!important;font-weight:600!important;color:#5a7a5a!important;text-transform:uppercase!important;letter-spacing:.06em!important}
.stButton button{border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-weight:600!important;font-size:.85rem!important}
.stButton button[kind="primary"]{background:#4a8f33!important;border:none!important}
.stButton button[kind="primary"]:hover{background:#3d7a28!important}
[data-testid="stDataEditor"]{border:1.5px solid #d8e8d4!important;border-radius:10px!important;overflow:hidden}
.arch-card{background:white;border:1.5px solid #e0e8dc;border-left:4px solid #6BBF4E;border-radius:10px;padding:.85rem 1rem;margin-bottom:.6rem}
.arch-card-date{font-weight:700;font-size:.9rem;color:#1a2e44}
.arch-card-fact{font-size:.78rem;color:#7a907a;margin-top:.2rem}
/* Compact single-line empty state — the old version (2rem padding, a 2rem
   icon on its own line) cost a full card's worth of height just to say
   "nothing here", which barely mattered when tabs hid most sections at
   once but adds up fast now that every section is visible on one page. */
.empty-state{text-align:center;padding:.5rem;color:#9ab09a;font-size:.8rem;display:flex;align-items:center;justify-content:center;gap:.4rem}
.empty-state .icon{font-size:1rem;margin-bottom:0}
.auth-gate{max-width:400px;margin:4rem auto;background:white;border-radius:16px;padding:2.5rem;box-shadow:0 8px 32px rgba(0,0,0,0.1);text-align:center}
/* ── Quick-jump section nav (replaces nested tabs) ─────────── */
.quicknav{position:sticky;top:56px;z-index:900;background:white;border-bottom:2px solid #e8f0e3;padding:.55rem 2rem;display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.05)}
.quicknav.editing{background:#fff8e6;border-bottom-color:#e8a125}
.quicknav a{background:#f4f8f2;color:#4a6640;font-size:.78rem;font-weight:600;padding:.4rem .8rem;border-radius:20px;text-decoration:none;border:1.5px solid #e0e8dc;white-space:nowrap}
.quicknav a:hover{background:#6BBF4E;color:white;border-color:#6BBF4E}
.quicknav.editing a{background:white;border-color:#e8c090}
.quicknav-tag{font-size:.72rem;font-weight:800;color:#92400e;background:#fde68a;padding:.35rem .7rem;border-radius:20px;letter-spacing:.03em;white-space:nowrap;margin-left:auto}
.section-anchor{position:relative;top:-116px;visibility:hidden}
/* ── Today at a glance ──────────────────────────────────────── */
.glance-strip{display:flex;gap:.6rem;flex-wrap:wrap;margin:0 0 1rem}
.glance-chip{background:white;border:1.5px solid #e0e8dc;border-radius:12px;padding:.55rem 1rem;display:flex;align-items:center;gap:.6rem;text-decoration:none;box-shadow:0 1px 4px rgba(0,0,0,0.05)}
.glance-chip .num{font-size:1.25rem;font-weight:800;color:#1a2e44;line-height:1}
.glance-chip .lbl{font-size:.7rem;font-weight:700;color:#7a907a;text-transform:uppercase;letter-spacing:.04em}
.glance-chip.zero{opacity:.55}
.glance-chip.zero .num{color:#4a8f33}
.glance-chip.alert{border-color:#c0392b;background:#fdecea}
.glance-chip.alert .num{color:#c0392b}
/* ── Section dividers (replace the old nested tab bar) ─────── */
.section-divider{display:flex;align-items:center;gap:.65rem;margin:2rem 0 1rem}
.section-divider .num-badge{background:#1a2e44;color:white;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:800;flex-shrink:0}
.section-divider h2{font-size:1.1rem;font-weight:700;color:#1a2e44;margin:0}
.section-divider .rule{flex:1;height:2px;background:#e0e8dc}
/* ── Mobile responsiveness ──────────────────────────────────── */
@media(max-width:768px){
  .bulletin-date-main{font-size:1.4rem}
  [data-testid="stMainBlockContainer"],.block-container{padding:0 .75rem 1.5rem!important}
  .top-nav,.quicknav,.bulletin-hero,.st-key-header_bar{margin-left:-.75rem;margin-right:-.75rem}
  .top-nav{padding:0 1rem}
  .quicknav{padding:.5rem 1rem;top:56px}
  .section-anchor{top:-150px}
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}
  [data-testid="stHorizontalBlock"]>div[data-testid="column"]{width:100%!important;flex:1 1 100%!important;min-width:100%!important}
  .stButton button{font-size:.92rem!important;padding:.65rem .5rem!important;min-height:2.6rem}
  .glance-chip{flex:1 1 calc(50% - .6rem)}
  .st-key-header_bar{padding:.5rem 1rem .65rem;border-radius:0 0 10px 10px}
  .hero-edit-badge{position:static;display:inline-block;margin-bottom:.5rem}
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────
def _default_date():
    d = date.today()
    if d.weekday() == 5: return d - timedelta(days=1)
    if d.weekday() == 6: return d + timedelta(days=1)
    return d

def init_state():
    defaults = {
        "authenticated": False, "edit_mode": False,
        "selected_date": _default_date(), "page": "bulletin",
        "show_login": False, "show_inline_login": False,
        "_pc_form_id": 0, "_last_seen_day": date.today(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# If this browser tab has been left open since an earlier calendar day -
# which is exactly how staff actually use this, opening it once in the
# morning and leaving it up - Streamlit's session state just keeps
# whatever date was last viewed instead of knowing a new day has
# started. Only the very first rerun after midnight sees a mismatch
# here, so deliberately browsing to a past or future date during the
# same day is untouched; this only forces things back to today when the
# day has actually rolled over underneath an idle tab.
if st.session_state._last_seen_day != date.today():
    st.session_state.selected_date = _default_date()
    st.session_state._last_seen_day = date.today()

# Staff-tier password for editing the bulletin (viewing needs no password).
# Reads STAFF_PASSWORD from secrets/env — do NOT use ADMIN_PASSWORD here:
# that secret belongs to the confidential/admin tier (confidential_auth.py).
def _get_staff_password():
    val = ""
    try:
        val = st.secrets.get("STAFF_PASSWORD", "")
    except Exception:
        val = ""
    if not val:
        val = _os.environ.get("STAFF_PASSWORD", "")
    return val or "clcstaff2026"

ADMIN_PASSWORD = _get_staff_password()

TRANSPORT_OPTIONS = ["Taxi","Parent/Carer","Other"]
CHANGE_TYPE_OPTIONS = ["Early Departure","Late Arrival","No Show","Alternative Pickup","Alternative Drop-off","Absent - not attending","Other"]
VISITOR_REASON_OPTIONS = ["Student Observation","Meeting with Leadership","Meeting with Teacher","TAC","Review/Transition Meeting","Support","Other"]

def _migrate_travel_rows(rows):
    migrated = []
    for r in rows:
        if "Transport To" in r or "Transport From" in r or "Times" in r:
            migrated.append({
                "Student": r.get("Student",""),
                "Arrival Time": r.get("Times",""),
                "Departure Time": "",
                "Transport": r.get("Transport To","") or r.get("Transport From",""),
            })
        else:
            migrated.append(r)
    return migrated

# ── HELPERS ───────────────────────────────────────────────────
def week_dates(d):
    monday = d - timedelta(days=d.weekday())
    return [monday + timedelta(days=i) for i in range(5)]

def term_label(d):
    y = d.year
    terms = {1:(date(y,1,28),date(y,4,11)), 2:(date(y,4,28),date(y,7,4)),
              3:(date(y,7,21),date(y,9,26)), 4:(date(y,10,13),date(y,12,12))}
    for t,(s,e) in terms.items():
        if s <= d <= e: return f"Term {t} \u00b7 {y}"
    return str(y)

# \u2500\u2500 TRANSITION STUDENTS (Student Absent \u2192 Travel & Vehicles) \u2500\u2500\u2500
# Any Student Absent row whose Reason mentions "transition" gets copied onto
# the matching JP/PY/SY travel card, so staff planning transport / pickups
# can see at a glance who's out on a transition visit today.
def _travel_key_for_program(prog):
    p = (prog or "").strip().lower()
    if not p: return None
    if p.startswith("jp") or "junior" in p: return "travel_jp"
    if p.startswith("py") or "primary" in p: return "travel_py"
    if p.startswith("sy") or "senior" in p: return "travel_sy"
    return None

def transition_students_by_program(student_absent_rows):
    groups = {"travel_jp": [], "travel_py": [], "travel_sy": []}
    for r in (student_absent_rows or []):
        if not isinstance(r, dict):
            continue
        name = (r.get("Student") or "").strip()
        reason = (r.get("Reason") or "")
        if not name or "transition" not in reason.lower():
            continue
        key = _travel_key_for_program(r.get("Program", ""))
        if key:
            groups[key].append(name)
    return groups

def transition_bar_html(names, compact=False):
    """A highlighted strip of on-transition student names for a JP/PY/SY travel card."""
    if not names: return ""
    size = ".92rem" if compact else ".8rem"
    pad  = ".3rem .55rem" if compact else ".35rem .6rem"
    return (f'<div style="margin-top:.35rem;background:#fff3e0;border:1px solid #e8a125;border-radius:6px;'
            f'padding:{pad};font-size:{size};color:#7a5200;font-weight:600;line-height:1.3;">'
            f'\U0001f504 On Transition: {", ".join(names)}</div>')

# ── TODAY AT A GLANCE ────────────────────────────────────────
# One-line summary chips shown right under the hero header, so staff can
# tell at a single glance whether anything today needs attention — without
# clicking into any section. Each chip links to the section anchor that has
# the detail. Replaces having to open every section just to check.
def render_glance_strip(bulletin_data, notices_count, program_change_count, trade_n=0):
    staff_n    = len([r for r in bulletin_data.get("staff_absent", [])   if (r.get("Staff Member") or "").strip() or (r.get("TRT") or "").strip()])
    student_n  = len([r for r in bulletin_data.get("student_absent", []) if (r.get("Student") or "").strip()])
    excursion_n = len([r for r in bulletin_data.get("excursions", [])       if any(v for v in r.values())])
    visitor_n   = len([r for r in bulletin_data.get("visitors_on_site", []) if any(v for v in r.values())]) + trade_n
    travel_chg_n = len([r for r in bulletin_data.get("travel_changes", [])  if any(v for v in r.values())])

    def chip(anchor, icon, n, label, alert=False):
        cls = "alert" if (alert and n) else ("zero" if not n else "")
        return (f'<a class="glance-chip {cls}" href="#{anchor}">{icon}'
                f'<span class="num">{n}</span><span class="lbl">{label}</span></a>')

    chips = []
    if notices_count:
        chips.append(chip("sec-notices", "\U0001f4e2", notices_count, "Notices"))
    chips += [
        chip("sec-staff", "\U0001f645", staff_n, "Staff Absent"),
        chip("sec-staff", "\U0001f392", student_n, "Students Absent"),
        chip("sec-staff", "\U0001f68c", excursion_n, "Excursions"),
        chip("sec-staff", "\U0001f465", visitor_n, "Visitors"),
        chip("sec-travel", "\U0001f504", travel_chg_n, "Travel Changes", alert=True),
        chip("sec-program", "\U0001f4ca", program_change_count, "Program Changes"),
    ]
    st.markdown(f'<div class="glance-strip">{"".join(chips)}</div>', unsafe_allow_html=True)

def section_divider(anchor_id, num, icon, title):
    """Big, clearly-labelled section header with a jump-target anchor — used
    in place of the old nested tab bar so the whole bulletin is one flowing,
    scannable page instead of tabs-within-a-tab."""
    st.markdown(
        f'<div id="{anchor_id}" class="section-anchor"></div>'
        f'<div class="section-divider"><div class="num-badge">{num}</div>'
        f'<h2>{icon} {title}</h2><div class="rule"></div></div>',
        unsafe_allow_html=True
    )

import contextlib

@contextlib.contextmanager
def card(key, color, icon, title):
    """A bordered card with a colored header strip — used for every small
    info card (Staff Absent, Excursions, etc).

    This replaces the old pattern of opening a `<div class="section-card">`
    in one st.markdown() call and closing it in a later one, with real
    widgets (data_editor, buttons) in between. That pattern LOOKS like it
    nests everything inside one box, but it doesn't: each st.markdown()
    call renders its own isolated HTML fragment, so the opening div closes
    itself immediately and the "card" ends up an empty sliver a few pixels
    tall, with the header/table/table each rendering as separate
    unbounded pieces that only look grouped because their backgrounds
    happen to match. That was invisible at a glance but is exactly why the
    page felt like it wasted space — every card carried extra, uncounted
    gaps between its "header" and its actual content.

    st.container(border=True, key=...) is a real Streamlit component: it
    genuinely wraps whatever is rendered inside the `with` block, so the
    border, radius and shadow apply to the whole card - header, table,
    empty state, or data_editor alike - not just the header strip.
    """
    # `color` is either one of the shared palette classes (green/navy/amber/
    # red/…) or a literal "#rrggbb" for the one-off travel-card accents.
    header_attr = f'class="card-header" style="background:{color};"' if color.startswith("#") else f'class="card-header {color}"'
    with st.container(border=True, key=f"card_{key}"):
        st.markdown(f'<div {header_attr}>{icon} {title}</div>', unsafe_allow_html=True)
        yield

def default_bulletin():
    return {
        "fun_fact": "",
        "staff_absent": [{"Staff Member":"","TRT":""} for _ in range(4)],
        "student_absent": [{"Student":"","Program":"","Reason":""} for _ in range(4)],
        "excursions": [{"Program":"","Staff Member":"","Time Departing":"","Time Returning":"","Location":""} for _ in range(4)],
        "staff_meetings": [{"Type":"","Staff Member":"","Location":"","Time Departing":"","Time Returning":"","Student":""} for _ in range(4)],
        "entry_meetings": [{"Time":"","Program":"","Student":""} for _ in range(4)],
        "additional_messages": [{"Staff Member":"","Information":""} for _ in range(4)],
        "visitors_on_site": [{"Visitor Name":"","Reason":"","Program":"","Staff Responsible":"","Arriving":"","Departing":"","Location":""} for _ in range(4)],
        "travel_jp": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_py": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_sy": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_changes": [{"Student":"","Program":"","Change Type":"","Reason":"","Time":"","How Departed":""} for _ in range(3)],
        "vehicle_bookings": [],
        "staff_responsibilities": {"kitchen_duties":"","meeting_pd_focus":"","chair":"","minutes":""},
        "nit_booking": "",
        "program_changes": []
    }

def _clean_row_list(value):
    """Normalize a bulletin list-field to a plain list of dicts.

    Guards every downstream `for r in rows: r.get(...)` against crashing on
    malformed stored data — a field saved as a JSON-encoded string instead
    of a true array (iterating a string yields characters, which have no
    .get()), a null/None value, or a stray non-dict entry mixed into an
    otherwise-fine list. Any of those previously crashed the page outright
    (e.g. AttributeError on r.get(...)) instead of just showing an empty
    or partial table.
    """
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else []
        except Exception:
            return []
    if not isinstance(value, list):
        return []
    cleaned = []
    for r in value:
        if not isinstance(r, dict):
            continue
        # Every field in these row lists is meant to be plain text. Coerce
        # each cell to a real string here — not just filter row shape —
        # because a cell can individually be None/NaN (e.g. a leftover
        # pandas NaN from a partially-filled data_editor row that was
        # saved before being cleaned) or some other non-string value. NaN
        # in particular is truthy in Python, so a downstream
        # `(r.get("Field") or "").strip()` does NOT fall back to "" for
        # it — it stays NaN and crashes on .strip(). Cleaning cell values
        # here means every consumer of these fields can safely trust it's
        # always a string, without repeating that guard everywhere.
        safe_row = {}
        for k, v in r.items():
            if v is None or (isinstance(v, float) and v != v):  # v != v ⇔ NaN
                safe_row[k] = ""
            elif isinstance(v, str):
                safe_row[k] = v
            else:
                safe_row[k] = str(v)
        cleaned.append(safe_row)
    return cleaned

_ROW_LIST_FIELDS = (
    "staff_absent", "student_absent", "excursions", "staff_meetings",
    "entry_meetings", "additional_messages", "visitors_on_site",
    "travel_jp", "travel_py", "travel_sy", "travel_changes",
)

def load_bulletin(d):
    data = db.get_bulletin(d)
    defaults = default_bulletin()
    if not data:
        data = defaults.copy()
    else:
        for k, v in defaults.items():
            if k not in data: data[k] = v
    for lk in _ROW_LIST_FIELDS:
        data[lk] = _clean_row_list(data.get(lk))
    vb = data.get("vehicle_bookings", [])
    if isinstance(vb, dict):
        converted = []
        for t, v in vb.items():
            if v.get("van",""): converted.append({"vehicle":"Van","booker":v["van"],"whole_day":True,"start_time":"","end_time":""})
            if v.get("kia",""): converted.append({"vehicle":"Kia","booker":v["kia"],"whole_day":True,"start_time":"","end_time":""})
        data["vehicle_bookings"] = converted
    for tk in ("travel_jp","travel_py","travel_sy"):
        data[tk] = _migrate_travel_rows(data.get(tk, []))
    # Migrate old combined staff_absent → separate staff_absent + student_absent.
    # Guarded on "Staff Member" being ABSENT, not just "Staff Absence" being present —
    # a row already migrated to the current schema must never be rebuilt from the old
    # field again, even if a stray "Staff Absence" key is still sitting in the stored
    # data alongside it (e.g. from a save that merges fields rather than replacing the
    # row outright). Re-running this on an already-current row is what makes freshly
    # saved Staff Member / TRT values disappear on the next load.
    old_sa = data.get("staff_absent", [])
    if old_sa and isinstance(old_sa[0], dict) and "Staff Absence" in old_sa[0] and "Staff Member" not in old_sa[0]:
        data["staff_absent"]   = [{"Staff Member": r.get("Staff Absence",""), "TRT": r.get("TRT","")} for r in old_sa if (r.get("Staff Absence") or "").strip() or (r.get("TRT") or "").strip()]
        data["student_absent"] = [{"Student": r.get("Student Absence",""), "Program": r.get("Program",""), "Reason": r.get("Reason","")} for r in old_sa if (r.get("Student Absence") or "").strip()]
        if not data["staff_absent"]:   data["staff_absent"]   = [{"Staff Member":"","TRT":""} for _ in range(4)]
        if not data["student_absent"]: data["student_absent"] = [{"Student":"","Program":"","Reason":""} for _ in range(4)]
    # Migrate old additional_messages → Staff Member / Information
    old_am = data.get("additional_messages", [])
    if old_am and isinstance(old_am[0], dict) and any(k in old_am[0] for k in ("Visitor","Reason","Arriving/Departing","Staff Name","Details")):
        migrated_am = []
        for r in old_am:
            staff = r.get("Staff Member","") or r.get("Staff Name","")
            info_parts = [v for k,v in r.items() if k not in ("Staff Member","Staff Name") and (v or "").strip()]
            migrated_am.append({"Staff Member": staff, "Information": " — ".join(info_parts)})
        data["additional_messages"] = migrated_am if migrated_am else [{"Staff Member":"","Information":""} for _ in range(4)]
    sr = data.get("staff_responsibilities", {})
    resp_keys = ["kitchen_duties", "meeting_pd_focus", "chair", "minutes"]
    is_empty = not any((sr.get(k) or "").strip() for k in resp_keys)
    monday = d - timedelta(days=d.weekday())
    if is_empty and d != monday:
        monday_data = db.get_bulletin(monday)
        if monday_data:
            monday_sr = monday_data.get("staff_responsibilities", {})
            if any((monday_sr.get(k) or "").strip() for k in resp_keys):
                data["staff_responsibilities"] = monday_sr
    if not (data.get("fun_fact") or "").strip():
        data["fun_fact"] = daily_fun_fact(d)
    return data

# ── NOTICE HELPERS ────────────────────────────────────────────
NOTICE_CATS = {
    "General":      {"color":"#4a8f33","bg":"#e8f5e1","emoji":"\U0001f4e2"},
    "Reminder":     {"color":"#c97b1a","bg":"#fff3e0","emoji":"\u23f0"},
    "Urgent":       {"color":"#b91c1c","bg":"#fee2e2","emoji":"\U0001f6a8"},
    "Student Info": {"color":"#1d4ed8","bg":"#dbeafe","emoji":"\U0001f468\u200d\U0001f393"},
    "Facilities":   {"color":"#6d28d9","bg":"#ede9fe","emoji":"\U0001f3eb"},
    "Wellbeing":    {"color":"#0e7490","bg":"#cffafe","emoji":"\U0001f49a"},
}

# ── PROGRAM CHANGES ───────────────────────────────────────────
PC_TIME_SLOTS = [
    "9:00","9:15","9:30","9:45",
    "10:00","10:15","10:30","10:45",
    "11:00","11:15","11:30","11:45",
    "12:00","12:15","12:30","12:45",
    "1:00","1:15","1:30","1:45",
    "2:00","2:15","2:30","2:45",
]
PC_TIME_SLOTS_30 = [s for s in PC_TIME_SLOTS if s.endswith(":00") or s.endswith(":30")]

ROLE_OPTIONS = ["", "JP", "PY", "SY", "NIT", "Lunch Cover", "Lunch Break",
                "Release", "Planning", "Meeting", "Other"]

ROLE_COLORS = {
    "JP":"#dbeafe","PY":"#ede9fe","SY":"#fef3c7","NIT":"#f1f5f9",
    "Lunch Cover":"#fef9c3","Lunch Break":"#cffafe","Release":"#dcfce7",
    "Planning":"#fce7f3","Meeting":"#fef3c7","Other":"#f3f4f6",
}
ROLE_COLORS_DARK = {
    "JP":"#1d4ed8","PY":"#6d28d9","SY":"#92400e","NIT":"#374151",
    "Lunch Cover":"#856404","Lunch Break":"#004085","Release":"#166534",
    "Planning":"#9d174d","Meeting":"#78350f","Other":"#4b5563",
}

def _slot_color_bg(val): return ROLE_COLORS.get(val, "#f9fafb")
def _slot_color_fg(val): return ROLE_COLORS_DARK.get(val, "#374151")

def _t2m(ts):
    try:
        h, m = str(ts).strip().split(":")
        h, m = int(h), int(m)
        if h < 9: h += 12
        return h * 60 + m
    except Exception:
        return -1

def blocks_to_slots(blocks, slot_list=None):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    result = {s: {"value":"","person":""} for s in slot_list}
    for slot in slot_list:
        sm = _t2m(slot)
        best = None; best_bs = -1
        for block in (blocks or []):
            bs = _t2m(block.get("start","")); be = _t2m(block.get("end",""))
            if bs >= 0 and be > bs and bs <= sm < be:
                result[slot] = {"value": block.get("role",""), "person": block.get("person","")}
                break
            if bs < 0 or be <= bs: continue
            if bs <= sm <= be and bs > best_bs: best = block; best_bs = bs
        if best: result[slot] = {"value": best.get("role",""), "person": best.get("person","")}
    return result

def _pc_row_html(label, normal_prog, ts, slot_list=None, dark=False):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    text = "#1a2e44" if not dark else "#c8d8c8"
    fs = "0.56rem" if dark else "0.62rem"
    lbl_c = "#1a2e44" if not dark else "#6BBF4E"
    bdr = "#e0e8dc" if not dark else "#2a3d2a"
    td_cells = ""
    for slot in slot_list:
        raw = ts.get(slot, {})
        val = raw.get("value","") if isinstance(raw,dict) else str(raw)
        person = raw.get("person","") if isinstance(raw,dict) else ""
        bg = _slot_color_bg(val); fg = _slot_color_fg(val) if val else text
        disp = val if val else ("\u00b7" if not dark else "")
        inner = f'<span style="font-weight:700;font-size:{fs};">{disp}</span>'
        if person:
            arrow = "\u2192" if val == "Lunch Cover" else ("\u21a9" if val == "Lunch Break" else "")
            inner += f'<br><span style="font-size:0.85em;opacity:0.75;">{arrow} {person}</span>'
        td_cells += f'<td style="background:{bg};color:{fg};text-align:center;padding:2px 1px;min-width:30px;vertical-align:top;border-right:1px solid {bdr};">{inner}</td>'
    lbl_html = (f'<td style="white-space:nowrap;padding:3px 8px 3px 4px;color:{lbl_c};font-weight:700;font-size:{fs};vertical-align:middle;border-right:2px solid {"#6BBF4E" if not dark else "#4a8f33"};">'
                f'{label}' + (f'<br><span style="font-weight:400;opacity:0.65;font-size:0.9em;">{normal_prog}</span>' if normal_prog else "") + f'</td>')
    return f'<tr>{lbl_html}{td_cells}</tr>'

def _timetable_grid_html(staff_rows, slot_list=None, dark=False):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    if not staff_rows: return ""
    th_bg = "#f4f8f2" if not dark else "#111e11"
    hdr = "#4a6640" if not dark else "#6BBF4E"
    bdr = "#e0e8dc" if not dark else "#2a3d2a"
    bdr2 = "#6BBF4E" if not dark else "#4a8f33"
    th_cells = (f'<th style="white-space:nowrap;padding:3px 8px 3px 4px;background:{th_bg};color:{hdr};font-size:0.5rem;border-right:2px solid {bdr2};">Staff / Role</th>'
                + "".join([f'<th style="background:{th_bg};color:{hdr};font-size:0.48rem;padding:1px 2px;text-align:center;white-space:nowrap;border-right:1px solid {bdr};">{s}</th>' for s in slot_list]))
    rows_html = ""
    for row in staff_rows:
        name = row.get("name",""); normal = row.get("normal_prog",""); blocks = row.get("blocks",[])
        ts = row.get("time_slots")
        if ts is None: ts = blocks_to_slots(blocks, slot_list)
        if any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
            rows_html += _pc_row_html(name, normal, ts, slot_list, dark)
    if not rows_html: return ""
    return (f'<div style="overflow-x:auto;margin-top:6px;"><table style="border-collapse:collapse;width:auto;">'
            f'<thead><tr>{th_cells}</tr></thead><tbody>{rows_html}</tbody></table></div>')

# ── SUPABASE / FACTS ──────────────────────────────────────────
_AUS_FACTS = [
    "Australia is the only continent that is also a single country \u2014 and somehow still can\u2019t decide where to put its capital.",
    "Kangaroos can\u2019t walk backwards, which is why they\u2019re on the Australian coat of arms \u2014 always moving forward, mate.",
    "Australia has more kangaroos than people. The roos are winning.",
    "The Box Jellyfish has 24 eyes. It still can\u2019t see why Australians swim anywhere near it.",
    "A group of kangaroos is called a mob. Very on-brand for Australia.",
    "Wombats produce cube-shaped poo \u2014 the only animal in the world that does. Science still hasn\u2019t fully explained why.",
    "Australia has 10 of the world\u2019s 15 most venomous snakes. They\u2019re very proud of this.",
    "The Great Barrier Reef is the largest living structure on Earth \u2014 visible from space, yet invisible to politicians.",
    "Australian Rules Football was invented to keep cricketers fit during winter. Cricket: unintentionally very useful.",
    "The platypus is venomous, lays eggs, and has a bill like a duck. It looks like Australia designed it after a big night.",
    "Australians consume more than 1.9 billion Tim Tams per year \u2014 roughly 80 per person. This tracks.",
    "The Sydney Funnel-web Spider is considered the world\u2019s most dangerous spider. Sydney has strong opinions about everything.",
    "Australia once fought a war against emus. The emus won. This is true. Look it up.",
    "The Dingo Fence is 5,614 km long \u2014 built to keep dingoes out of southern Australia. The dingoes are biding their time.",
    "Eucalyptus leaves are mildly toxic to most animals. Koalas eat almost nothing else and sleep 22 hours a day. Icon behaviour.",
    "Australia has the longest straight stretch of railway in the world \u2014 478 km of perfectly straight track through the Nullarbor.",
    "Canberra was purpose-built as the capital because Sydney and Melbourne couldn\u2019t agree on which city deserved it. Classic.",
    "Australia has pink lakes. Lake Hillier on Middle Island is bubblegum pink year-round, and scientists still argue about why.",
    "The Thorny Devil lizard can drink through its feet by standing in water. Useful at a BBQ.",
    "Australia\u2019s first police force was made up of the most well-behaved convicts. Starting as you mean to go on.",
    "Australians invented WiFi. Also the black box flight recorder. And the bionic ear. But mostly WiFi.",
    "Drop bears are not real. Probably.",
    "The laughing kookaburra\u2019s call sounds exactly like a human laughing manically. Nobody finds this unsettling.",
    "Vegemite was invented in 1922 as a way to use leftover brewer\u2019s yeast. You\u2019re welcome, or sorry, depending on your position.",
    "Australians use the word \u2018reckon\u2019 as a sophisticated intellectual agreement mechanism. Fully reckon this is true.",
    "A baby kangaroo (joey) is about the size of a jellybean when born. It then spends six months in a pouch.",
    "The Australian dollar is made from polymer plastic, making it waterproof. Essential for a country surrounded by water.",
    "The Melbourne Cup is a public holiday in Victoria. Only Australians would make a horse race a reason to stop work.",
    "Quokkas are considered the happiest animal on Earth. They live on Rottnest Island. No predators, good weather \u2014 honestly same.",
    "Australian magpies remember human faces and will swoop people they dislike. They hold grudges. Do not underestimate them.",
    "South Australia was the first place in the world to give women the right to stand for parliament, back in 1894.",
    "The echidna and platypus are the only two mammals in the world that lay eggs. Both live in Australia, naturally.",
    "Australians say \u2018arvo\u2019 for afternoon, \u2018servo\u2019 for service station, and \u2018bottle-o\u2019 for bottle shop.",
    "There are more than 10,000 beaches in Australia. Visiting a new one every day would take 27 years.",
    "A mob of emus will methodically destroy a fence to get to crops. They have a system. They are organised.",
    "The Royal Flying Doctor Service covers 7.69 million square kilometres \u2014 the world\u2019s largest GP practice.",
    "Uluru extends 2.5 km underground \u2014 what you see is only a fraction of the full rock.",
    "Australians invented the Hills Hoist rotary clothesline. A genuine contribution to civilisation.",
    "The Australian Alps receive more snowfall than Switzerland in a good year. Nobody ever believes this.",
]

def daily_fun_fact(d):
    import hashlib
    seed = int(hashlib.md5(str(d).encode()).hexdigest(), 16)
    return _AUS_FACTS[seed % len(_AUS_FACTS)]

def _get_sb(): return db.get_supabase()

def load_todays_nit_bookings(for_date):
    """Load NIT bookings for today from the database"""
    try:
        sb = _get_sb()
        response = sb.table("nit_bookings").select("*").eq("status", "booked").eq("booking_date", str(for_date)).execute()
        if response.data:
            slot_order = {"Tuesday 9:00-10:15am": 1, "Monday 1:45-3:00pm": 2, "Thursday 1:45-3:00pm": 3, "Monday 1:45pm": 4, "Tuesday 1:45pm": 5, "Thursday 2:15pm": 6}
            return sorted(response.data, key=lambda x: slot_order.get(x.get('time_slot', ''), 99))
        return []
    except Exception:
        return []

# Meeting room hour-block slots, 8:00am through the last bookable start of 4:00pm.
# Kept in the same order as 52_meeting_room_bookings.py so sorting lines up.
MEETING_ROOM_SLOT_ORDER = {
    "8:00 - 9:00am": 1, "9:00 - 10:00am": 2, "10:00 - 11:00am": 3,
    "11:00am - 12:00pm": 4, "12:00 - 1:00pm": 5, "1:00 - 2:00pm": 6,
    "2:00 - 3:00pm": 7, "3:00 - 4:00pm": 8, "4:00 - 5:00pm": 9,
}

def load_todays_meeting_room_bookings(for_date):
    """Load Meeting Room bookings for a given date from the database.

    Called with whichever date the bulletin is currently showing (today or
    any future date via the date navigator), so a booking made for a future
    day automatically appears when that day's bulletin is opened.
    """
    try:
        sb = _get_sb()
        response = sb.table("meeting_room_bookings").select("*").eq("status", "booked").eq("booking_date", str(for_date)).execute()
        if response.data:
            return sorted(response.data, key=lambda x: MEETING_ROOM_SLOT_ORDER.get(x.get('time_slot', ''), 99))
        return []
    except Exception:
        return []

@st.cache_resource
def _trade_bookings_client():
    """Dedicated client for trade_bookings — deliberately NOT routed through
    database.py's db.get_supabase(), because this portal uses more than one
    Supabase project across different tools. This uses the exact same
    st.secrets["SUPABASE_URL"]/["SUPABASE_KEY"] that 12_Calendar.py and
    56_Trade_Bookings.py both read directly, so all three are guaranteed to
    point at the same project/table."""
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def load_todays_trade_bookings(for_date):
    """Load tradesperson/contractor bookings for a given date — public-safe only.
    Full detail (company, contact, phone, internal notes) lives in
    56_Trade_Bookings.py and is never requested here."""
    try:
        sb = _trade_bookings_client()
        response = (
            sb.table("trade_bookings")
            .select("id,booking_date,start_time,end_time,display_category,work_summary,status")
            .eq("booking_date", str(for_date))
            .neq("status", "Cancelled")
            .execute()
        )
        rows = response.data or []
        st.session_state["_trade_bookings_last_error"] = None
        return sorted(rows, key=lambda x: str(x.get("start_time") or ""))
    except Exception as _tb_err:
        st.session_state["_trade_bookings_last_error"] = str(_tb_err)
        return []

def trade_bookings_as_visitor_rows(for_date):
    """Trade/contractor bookings reframed as Visitors-on-Site rows — same
    sanitized fields as everywhere else (no company/contact/phone)."""
    out = []
    for b in load_todays_trade_bookings(for_date):
        category = b.get("display_category") or "Onsite Works"
        summary = b.get("work_summary") or ""
        label = f"{category} - {summary}" if summary else category
        start_t = (b.get("start_time") or "")[:5]
        end_t = (b.get("end_time") or "")[:5]
        out.append({
            "Visitor Name": f"🔧 {label}",
            "Reason": "Trade/Contractor",
            "Program": "",
            "Staff Responsible": b.get("booked_by") or "",
            "Arriving": start_t,
            "Departing": end_t,
            "Location": b.get("location_onsite") or "",
        })
    return out

def load_notices(for_date=None):
    try:
        q = _get_sb().table("daily_notices").select("*").order("created_at", desc=False)
        if for_date: q = q.eq("notice_date", str(for_date))
        return q.execute().data or []
    except Exception as e:
        st.warning(f"\u26a0\ufe0f Could not load notices: {e}"); return []

def save_notice(row):
    try: _get_sb().table("daily_notices").insert(row).execute()
    except Exception as e: st.error(f"Could not save notice: {e}")

def load_scheduled_meetings(for_date=None):
    _DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    try:
        d = for_date or date.today()
        day_name = _DAY_NAMES[d.weekday()]
        res = _get_sb().table("tm_schedules").select("*").eq("show_in_bulletin", True).execute()
        meetings = []
        for r in (res.data or []):
            if (r.get("day_of_week") or "").strip().lower() == day_name.lower():
                prog = r.get("program","")
                prog_label = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years","STAFF":"All Staff","ADMIN":"Admin"}.get(prog, prog)
                meetings.append({"Type": r.get("schedule_name","Team Meeting"),"Staff Member": prog_label,"Location": r.get("location",""),"Time Departing": r.get("meeting_time",""),"Time Returning": "","Student": ""})
        return meetings
    except Exception: return []

def delete_notice(nid):
    try: _get_sb().table("daily_notices").delete().eq("id", nid).execute()
    except Exception as e: st.error(f"Could not delete notice: {e}")

def load_bulletin_changes(d):
    try:
        res = _get_sb().table("daily_changes").select("*").eq("bulletin_date", str(d)).order("created_at").execute()
        rows = res.data or []; result = []
        for r in rows:
            sr = r.get("staff_rows", [])
            if isinstance(sr, str):
                try: sr = json.loads(sr)
                except: sr = []
            result.append({**r, "staff_rows": sr})
        return result
    except Exception: return []

def save_bulletin_change(d, entry):
    try:
        data = {"bulletin_date": str(d),"reason": entry.get("reason",""),"staff_absent": entry.get("staff_absent",""),"has_trt": entry.get("has_trt", False),"trt_name": entry.get("trt_name",""),"staff_rows": json.dumps(entry.get("staff_rows",[])),}
        if entry.get("id"): res = _get_sb().table("daily_changes").update(data).eq("id", entry["id"]).execute()
        else: res = _get_sb().table("daily_changes").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e: st.error(f"Could not save change: {e}"); return None

def delete_bulletin_change(cid):
    try: _get_sb().table("daily_changes").delete().eq("id", cid).execute(); return True
    except Exception as e: st.error(f"Delete failed: {e}"); return False

def load_pc_manager_changes(d):
    """Load entries saved by the Program Changes Manager tool.

    Reads directly from the program_changes Supabase table (plain table
    calls only, no RPC functions - the reliable pattern used elsewhere in
    this app). This works regardless of which tab, browser, or device the
    Program Changes Manager was used on, since it's a real shared database
    rather than browser session state.

    Falls back to session state (only useful within the same tab) if the
    database is unreachable, so the tool degrades gracefully rather than
    breaking outright.
    """
    import os
    from supabase import create_client as _create_client
    try:
        _url = os.environ.get("SUPABASE_URL", "")
        _key = os.environ.get("SUPABASE_KEY", "")
        if _url and _key:
            _sb = _create_client(_url, _key)
            res = _sb.table("program_changes").select("*").eq("change_date", str(d)).order("created_at").execute()
            rows = res.data or []
            for row in rows:
                if isinstance(row.get("time_blocks"), str):
                    try: row["time_blocks"] = json.loads(row["time_blocks"])
                    except: row["time_blocks"] = []
            return rows
    except Exception:
        pass

    # Fallback: session state (same tab only)
    all_changes = st.session_state.get("program_changes", {})
    return all_changes.get(str(d), [])


def _fmt_pc_time(ts):
    try: return datetime.strptime(str(ts), "%H:%M:%S").strftime("%I:%M %p").lstrip("0")
    except: return str(ts)

def _build_plain_text_bc(changes, for_date):
    lines = [f"CLC PROGRAM CHANGES \u2014 {for_date.strftime('%A %-d %B %Y').upper()}", "="*52]
    for idx, ch in enumerate(changes, 1):
        reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt", False); trt_name = ch.get("trt_name","")
        lines.append(f"\n[{idx}] {reason.upper()}")
        if absent: lines.append(f"    Absent staff: {absent}")
        if has_trt: lines.append(f"    TRT on site:  {trt_name or '(name not recorded)'}")
        else: lines.append(f"    No TRT \u2014 internal staff adjustment")
        for row in ch.get("staff_rows",[]):
            name = row.get("name",""); normal = row.get("normal_prog",""); blocks = row.get("blocks",[])
            if not blocks: continue
            norm_str = f" [normally: {normal}]" if normal else ""
            lines.append(f"\n    {name}{norm_str}:")
            for block in sorted(blocks, key=lambda b: b.get("start","")):
                role = block.get("role",""); start = block.get("start",""); end = block.get("end",""); person = block.get("person","")
                if not role: continue
                detail = ""
                if role == "Lunch Cover" and person: detail = f" (releasing {person})"
                elif role == "Lunch Break" and person: detail = f" (covered by {person})"
                elif person: detail = f" \u2014 {person}"
                lines.append(f"      {start} \u2013 {end}: {role}{detail}")
    lines += ["", "="*52, "Cowandilla Learning Centre \u00b7 LBU Daily Bulletin"]
    return "\n".join(lines)

def _build_html_sheet_bc(changes, for_date):
    slot_list = PC_TIME_SLOTS_30
    def slot_td(val, person):
        bg = _slot_color_bg(val); fg = _slot_color_fg(val) if val else "#9ca3af"; disp = val if val else ""; arrow = ""
        if val == "Lunch Cover" and person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">\u2192{person}</small>'
        elif val == "Lunch Break" and person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">\u21a9{person}</small>'
        elif person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">{person}</small>'
        return (f'<td style="background:{bg};color:{fg};text-align:center;padding:2px 1px;font-size:0.5rem;font-weight:600;border:1px solid #e5e7eb;min-width:38px;">{disp}{arrow}</td>')
    def tt_block(staff_rows):
        if not staff_rows: return ""
        header = "".join([f'<th style="background:#1a2e44;color:rgba(255,255,255,0.85);font-size:0.42rem;padding:2px 1px;text-align:center;border:1px solid #374151;white-space:nowrap;">{s}</th>' for s in slot_list])
        rows_html = ""
        for row in staff_rows:
            name = row.get("name","(Staff)"); normal = row.get("normal_prog",""); blocks = row.get("blocks",[]); ts = blocks_to_slots(blocks, slot_list)
            if not any(v.get("value","") for v in ts.values()): continue
            norm_str = f'<span style="font-weight:400;color:#6b7280;font-size:0.75em;"> ({normal})</span>' if normal else ""
            cells = "".join([slot_td(ts[s].get("value",""), ts[s].get("person","")) for s in slot_list])
            rows_html += f'<tr><td style="white-space:nowrap;padding:3px 8px;color:#1a2e44;font-weight:700;font-size:0.6rem;border:1px solid #e5e7eb;border-right:2px solid #6BBF4E;">{name}{norm_str}</td>{cells}</tr>'
        if not rows_html: return ""
        return (f'<table style="border-collapse:collapse;width:100%;table-layout:fixed;margin-top:8px;"><thead><tr><th style="background:#1a2e44;color:rgba(255,255,255,0.85);font-size:0.42rem;padding:2px 8px;border:1px solid #374151;text-align:left;">Staff / Role</th>{header}</tr></thead><tbody>{rows_html}</tbody></table>')
    changes_html = ""
    for idx, ch in enumerate(changes, 1):
        reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt", False); trt_name = ch.get("trt_name",""); staff_rows = ch.get("staff_rows",[])
        color = "#dc2626" if reason == "Staff Absence" else "#0e7490"
        meta = []
        if absent: meta.append(f"<strong>Absent:</strong> {absent}")
        if has_trt: meta.append(f"<strong>TRT on site:</strong> {trt_name or 'Name TBC'}")
        else: meta.append("<strong>No TRT \u2014 internal adjustment</strong>")
        changes_html += (f'<div style="background:white;border:1.5px solid #e5e7eb;border-left:5px solid {color};border-radius:8px;padding:12px 14px;margin-bottom:14px;page-break-inside:avoid;"><div style="font-size:0.85rem;font-weight:800;color:{color};margin-bottom:4px;">Change {idx} \u2014 {reason}</div><div style="font-size:0.78rem;color:#374151;margin-bottom:6px;">{" &nbsp;\u00b7&nbsp; ".join(meta)}</div>{tt_block(staff_rows)}</div>')
    legend = "".join([f'<span style="background:{_slot_color_bg(v)};color:{_slot_color_fg(v)};padding:2px 8px;border-radius:10px;font-size:0.62rem;font-weight:600;">{v}</span>' for v in ["JP","PY","SY","NIT","Lunch Cover","Lunch Break","Release","Planning"]])
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>CLC Program Changes</title><style>@page{{size:A4 landscape;margin:10mm 12mm}}body{{font-family:'Segoe UI',Arial,sans-serif;background:#f9fafb;margin:0;padding:14px;color:#1a2e44}}@media print{{body{{background:white;padding:0}}.no-print{{display:none!important}}}}.page{{background:white;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.08);padding:18px 22px}}</style></head><body><div class="page"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:10px;"><div><div style="font-size:1rem;font-weight:800;color:#1a2e44;">\U0001f4ca CLC Program Changes</div><div style="font-size:0.75rem;color:#6b7280;">{for_date.strftime('%A %-d %B %Y')} &nbsp;\u00b7&nbsp; Cowandilla Learning Centre LBU</div></div><button class="no-print" onclick="window.print()" style="background:#1a2e44;color:white;border:none;padding:7px 14px;border-radius:6px;font-size:0.78rem;cursor:pointer;">\U0001f5a8\ufe0f Print / Save PDF</button></div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:12px;">{legend}</div>{changes_html}<div style="font-size:0.6rem;color:#9ca3af;margin-top:16px;text-align:center;border-top:1px solid #f3f4f6;padding-top:8px;">Cowandilla Learning Centre \u00b7 LBU Daily Bulletin \u00b7 Printed {date.today().strftime('%-d %B %Y')}</div></div></body></html>"""


# ══════════════════════════════════════════════════════════════
# DISPLAY MODE
# ══════════════════════════════════════════════════════════════
params = st.query_params
if params.get("display") == "true":
    import time
    if "display_date" not in st.session_state: st.session_state.display_date = date.today()
    if st.session_state.display_date < date.today(): st.session_state.display_date = date.today()
    today = st.session_state.display_date
    d_data = load_bulletin(today)
    if "display_last_refresh" not in st.session_state: st.session_state.display_last_refresh = time.time()
    if time.time() - st.session_state.display_last_refresh > 60:
        st.session_state.display_last_refresh = time.time(); st.session_state.display_date = date.today(); st.rerun()

    st.markdown("""<style>
    html,body{margin:0!important;padding:0!important}
    /* Only the .dt tables were actually getting the DM Sans font - every
       other piece of text on this screen (card headers, the responsibility
       values, vehicle/travel badges, the fun-fact bar) had no font-family
       set anywhere and so fell back to the browser's plain default sans,
       which read as noticeably plainer/less polished than the rest of the
       portal. Setting it once here on the whole app view means everything
       inherits it unless something more specific overrides it. */
    [data-testid="stAppViewContainer"]{background:#eef4ec!important;padding:0!important;font-family:'DM Sans',Arial,sans-serif!important}
    [data-testid="stMainBlockContainer"],.main .block-container{padding:0!important;margin:0!important;max-width:100%!important}
    [data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
    #MainMenu,footer,.stDeployButton{display:none}
    [data-baseweb="tab-list"]{display:none!important}
    [data-testid="stVerticalBlock"]{gap:.4rem!important}
    [data-testid="element-container"],.element-container{margin-bottom:0!important}
    iframe{display:block}
    /* Day-nav button row, sized up for a TV viewed from across the room and
       bled flush against the header bar above it (same trick used on the
       main bulletin page) so the two read as one continuous control strip
       instead of two stacked bars. */
    .st-key-display_daynav{background:white;padding:.5rem 1.25rem .65rem;margin-top:-4px}
    .st-key-display_daynav .stButton button{font-size:1.15rem!important;font-weight:700!important;padding:.7rem 1rem!important;min-height:3.1rem!important;border-radius:10px!important}
    </style>""", unsafe_allow_html=True)
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    sr = d_data.get("staff_responsibilities", {}); fun = d_data.get("fun_fact","")
    st.markdown("""<style>
    /* ── Same visual language as the redesigned Daily Bulletin page:
       green/navy/amber/red as the four meaningful colors, the JP/PY/SY
       travel cards keeping their own one-off accent hues, real card
       borders + radius + shadow, uppercase colored header strips. Sizes
       are pushed up well beyond the bulletin's own scale on top of that,
       since this is read from across a room on a wall-mounted TV rather
       than close-up on a laptop. ─────────────────────────────────────── */
    .dp{background:#ffffff;border:1px solid #e9eee7;border-radius:12px;overflow:hidden;
        box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:1rem;break-inside:avoid;
        -webkit-column-break-inside:avoid;page-break-inside:avoid}
    .dp-header{padding:.6rem 1rem;font-size:1.2rem;font-weight:800;letter-spacing:.06em;
        text-transform:uppercase;color:white;display:flex;align-items:center;gap:.5rem;
        text-shadow:0 1px 2px rgba(0,0,0,0.12)}
    .dp-header.green{background:#6BBF4E}
    .dp-header.navy{background:#1a2e44}
    .dp-header.amber{background:#e8a125;color:#1a2e44;text-shadow:none}
    .dp-header.red{background:#c0392b}
    .dp-header.jp{background:#3d5d80}
    .dp-header.py{background:#5b4a75}
    .dp-header.sy{background:#7a5c3f}
    .dp-body{padding:.75rem 1rem;background:white}
    /* A smaller footprint for a card that's useful but doesn't need the
       same visual weight as attendance/travel - one dense line of
       label:value pairs instead of four stacked blocks. */
    .dp-body.dp-body-compact{padding:.55rem .9rem;display:flex;flex-wrap:wrap;gap:.35rem 1.1rem;align-items:baseline}
    .dp-body-compact .resp-item{font-size:1rem;color:#2a3a2a;white-space:nowrap}
    .dp-body-compact .resp-item strong{color:#4a8f33}
    .dp-grid{column-width:420px;column-gap:1.1rem;margin:.9rem 1.25rem 0}
    .dp-full{margin:0 1.25rem 1rem}
    /* table-layout:fixed made every column share the card's width evenly,
       which fixed the earlier clipping but made anything with 4+ narrow
       columns (Staff Meetings, the travel cards) wrap one letter per
       line - unreadable, worse than the clipping it replaced. Natural
       (auto) column sizing reads properly, so a wide table just gets a
       smaller "compact" type size instead (applied by column count,
       below) so it fits the card without either clipping or squeezing
       column headers into vertical letter-stacks. */
    .dt{width:100%;border-collapse:collapse;font-size:1.2rem;color:#1a2e44;font-family:'DM Sans',Arial,sans-serif}
    .dt.dt-compact{font-size:.98rem}
    .dt th{color:#4a8f33;font-weight:700;font-size:.92rem;text-transform:uppercase;letter-spacing:.03em;
        padding:.4rem .55rem;border-bottom:2px solid #d8ead2;text-align:left;background:#f4f8f2;
        overflow-wrap:break-word;word-break:break-word;white-space:normal}
    .dt.dt-compact th{font-size:.76rem;padding:.3rem .4rem}
    .dt.dt-compact td{padding:.35rem .4rem}
    .dt td{padding:.5rem .55rem;border-bottom:1px solid #f0f4ee;vertical-align:top;line-height:1.35;
        overflow-wrap:break-word;word-break:break-word}
    .dt tr:last-child td{border-bottom:none}
    .dt-em{color:#9ab09a;font-style:italic;font-size:1.1rem}
    .vb-tag{background:#e8f5e1;color:#2d6b1a;padding:.2rem .6rem;border-radius:5px;font-size:1.1rem;font-weight:600}
    .kitchen-val{background:#e8a125;border-radius:6px;padding:.25rem .65rem;color:#1a2e44;font-weight:800;
        font-size:1.15rem;display:inline-block}
    .resp-label{font-size:.92rem;color:#4a8f33;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
    .resp-val{font-size:1.15rem;color:#2a3a2a;margin-top:.2rem}
    .tc-badge{background:#fde2e2;color:#c0392b;padding:.2rem .6rem;border-radius:5px;font-size:1.1rem;font-weight:700}
    .fact-bar{display:flex;align-items:center;gap:.7rem;background:#1a2e44;color:white;padding:.7rem 1.25rem;
        margin:0 1.25rem 1rem;border-radius:10px;font-size:1.2rem;line-height:1.35}
    .fact-label{background:#6BBF4E;color:#1a2e44;font-weight:800;font-size:.85rem;text-transform:uppercase;
        letter-spacing:.05em;padding:.3rem .7rem;border-radius:20px;white-space:nowrap}
    </style>""", unsafe_allow_html=True)
    import streamlit.components.v1 as _components
    _date_str = today.strftime("%A %-d %B %Y").upper()
    # components.html renders in its own standalone iframe document, which
    # never sees the Google Fonts <link> injected into the outer page via
    # st.markdown above - so this whole header (title, date, clock) was
    # silently falling back to the browser's default font the entire time,
    # the most visually obvious instance of the font problem since it sits
    # at the very top of the screen. It needs its own font link.
    _components.html(f"""<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=DM+Mono:wght@500;700&display=swap" rel="stylesheet">
    <div style="background:#1a2e44;padding:.7rem 1.25rem;display:flex;align-items:center;justify-content:space-between;font-family:'DM Sans',Arial,sans-serif;">
      <div>
        <div style="font-size:1.55rem;color:white;font-weight:700;letter-spacing:.01em;">CLC Daily Bulletin</div>
        <div style="font-size:1.05rem;color:#8fd468;font-weight:600;">{_date_str}</div>
      </div>
      <div style="display:flex;align-items:center;gap:1.25rem;">
        <div style="font-size:2.1rem;color:#e8a125;font-weight:700;font-family:'DM Mono',monospace;letter-spacing:.02em;" id="live-clock">--:-- --</div>
        <a href="/Daily_Bulletin?quickadd=true" style="background:#6BBF4E;color:#1a2e44;font-size:.85rem;font-weight:700;padding:.4rem .75rem;border-radius:5px;text-decoration:none;font-family:'DM Sans',sans-serif;">+ Add</a>
        <a href="/Daily_Bulletin?from_display=true" style="background:rgba(255,255,255,0.12);color:white;font-size:.85rem;font-weight:600;padding:.4rem .75rem;border-radius:5px;text-decoration:none;font-family:'DM Sans',sans-serif;">Staff</a>
      </div>
    </div>
    <script>
    function updateClock(){{var n=new Date();var h=n.getHours();var m=n.getMinutes();var ap=h>=12?'PM':'AM';h=h%12||12;document.getElementById('live-clock').textContent=h+':'+(m<10?'0':'')+m+' '+ap;}}
    updateClock();setInterval(updateClock,30000);
    </script>""", height=78, scrolling=False)

    prev_day = today - timedelta(days=1); next_day = today + timedelta(days=1)
    with st.container(key="display_daynav"):
        dn1, dn2, dn3, dn4 = st.columns([1,4,1,1])
        with dn1:
            if st.button(f"\u2190 {prev_day.strftime('%a %-d %b')}", key="dn_prev", use_container_width=True): st.session_state.display_date = prev_day; st.rerun()
        with dn2:
            st.markdown(f'<div style="text-align:center;color:#2d7d4f;font-size:1.05rem;font-weight:700;font-family:DM Mono,monospace;letter-spacing:.06em;padding:.7rem 0;">VIEWING: {today.strftime("%A %-d %B %Y").upper()}</div>', unsafe_allow_html=True)
        with dn3:
            if st.button(f"{next_day.strftime('%a %-d %b')} \u2192", key="dn_next", use_container_width=True): st.session_state.display_date = next_day; st.rerun()
        with dn4:
            if st.button("Today", key="dn_today", use_container_width=True): st.session_state.display_date = date.today(); st.rerun()

    def tbl_rows(rows, keys):
        filtered = [r for r in rows if any(r.get(k,"") for k in keys)]
        if not filtered: return '<tr><td colspan="20" class="dt-em">None today</td></tr>'
        return "".join(["<tr>"+"".join([f"<td>{r.get(k,'')}</td>" for k in keys])+"</tr>" for r in filtered])

    d_notices = load_notices(for_date=today)
    if d_notices:
        n_parts = []
        for n in d_notices:
            cat = n.get("category","General"); nc = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            n_parts.append(f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:.78rem;font-weight:700;text-transform:uppercase;padding:.1rem .4rem;border-radius:4px;">{cat}</span> <strong style="color:#1a2e44;font-size:1.05rem;">{n.get("title","")}</strong> <span style="color:#4a6a4a;font-size:1rem;">{n.get("body","")}</span> <span style="color:#999;font-size:.85rem;">({n.get("submitted_by","")})</span>')
        st.markdown(f'<div class="dp dp-full"><div class="dp-header green">\U0001f4cb Notices</div><div class="dp-body"><div style="line-height:1.7;">{"<br>".join(n_parts)}</div></div></div>', unsafe_allow_html=True)

    # ── One continuous masonry grid for every compact info card ──────
    # Previously five st.columns() side by side, then another five below -
    # with cards of very different natural heights (a one-line "None
    # today" next to a five-row table) that leaves ragged, uneven gaps
    # of bare background under the shorter columns before the next row
    # starts. CSS multi-column layout (column-width, with break-inside:
    # avoid on each card) packs every card into whichever column has
    # room next, the way a real noticeboard would, instead of reserving
    # a fixed-height row per group.
    _staff_rows   = [r for r in d_data.get("staff_absent",  []) if (r.get("Staff Member") or "").strip() or (r.get("TRT") or "").strip()]
    _student_rows = [r for r in d_data.get("student_absent", []) if (r.get("Student") or "").strip()]
    _sched = load_scheduled_meetings(today); _all_mtgs = list(d_data.get("staff_meetings") or []) + _sched
    kitchen = sr.get("kitchen_duties","") or "\u2014"
    _vis_rows = [r for r in d_data.get("visitors_on_site", []) if any(r.get(k,"") for k in ["Visitor Name","Reason","Staff Responsible"])] + trade_bookings_as_visitor_rows(today)
    _transition_d = transition_students_by_program(d_data.get("student_absent", []))
    vb = d_data.get("vehicle_bookings",[])
    if isinstance(vb, dict): vb = []
    if vb:
        def _dm_vb_time_d(b): return "All day" if b.get("whole_day",True) else f"{b.get('start_time','?')}\u2013{b.get('end_time','?')}"
        vb_html = "".join([f'<tr><td style="font-size:.95rem;color:#666;">{"\U0001f690 Van" if b.get("vehicle")=="Van" else "\U0001f699 Kia"}</td><td><span class="vb-tag">{b.get("booker","")}</span></td><td style="font-size:.95rem;color:#4a8f33;">{_dm_vb_time_d(b)}</td></tr>' for b in vb if b.get("booker","")])
    else:
        vb_html = '<tr><td colspan="3" class="dt-em">No bookings</td></tr>'
    nit = d_data.get("nit_booking","") or '<span class="dt-em">None</span>'
    _mrb_today = load_todays_meeting_room_bookings(today)
    if _mrb_today:
        _mrb_rows = "".join([f'<tr><td style="font-family:\'DM Mono\',monospace;font-size:.95rem;color:#4a8f33;font-weight:700;white-space:nowrap;">{b.get("time_slot","")}</td><td>{b.get("staff_name","")}</td><td style="font-size:.95rem;color:#666;">{b.get("purpose","") or ""}</td></tr>' for b in _mrb_today])
        _mrb_html = f'<table class="dt"><tr><th>Time</th><th>Booked By</th><th>Purpose</th></tr>{_mrb_rows}</table>'
    else:
        _mrb_html = '<span class="dt-em">No meeting room bookings today</span>'

    _cards = []
    _cards.append(f'<div class="dp"><div class="dp-header green">\U0001f645 Staff Absent</div><div class="dp-body"><table class="dt"><tr><th>Staff</th><th>TRT</th></tr>{tbl_rows(_staff_rows, ["Staff Member","TRT"])}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f392 Student Absent</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Program</th><th>Reason</th></tr>{tbl_rows(_student_rows, ["Student","Program","Reason"])}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f68c Excursions</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Program</th><th>Staff</th><th>Depart</th><th>Return</th><th>Location</th></tr>{tbl_rows(d_data.get("excursions",[]), ["Program","Staff Member","Time Departing","Time Returning","Location"])}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f91d Staff Meetings</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>{tbl_rows(_all_mtgs, ["Type","Staff Member","Location","Time Departing","Time Returning","Student"])}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f4e5 Entry Meetings</div><div class="dp-body"><table class="dt"><tr><th>Time</th><th>Program</th><th>Student</th></tr>{tbl_rows(d_data.get("entry_meetings",[]), ["Time","Program","Student"])}</table></div></div>')
    if _vis_rows:
        _vis_html = "".join([f'<tr><td><strong style="color:#1a2e44;">{r.get("Visitor Name","")}</strong></td><td style="font-size:.95rem;">{r.get("Reason","")}</td><td style="font-size:.95rem;">{r.get("Program","")}</td><td style="font-size:.95rem;">{r.get("Staff Responsible","")}</td><td style="font-size:.95rem;">{r.get("Arriving","")}</td><td style="font-size:.95rem;">{r.get("Departing","")}</td><td style="font-size:.95rem;">{r.get("Location","")}</td></tr>' for r in _vis_rows])
        _cards.append(f'<div class="dp"><div class="dp-header green">\U0001f465 Visitors</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Visitor</th><th>Reason</th><th>Prog</th><th>Staff</th><th>Arriving</th><th>Departing</th><th>Location</th></tr>{_vis_html}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header jp">\U0001f7e6 JP \u2013 Travel</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_jp",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table>{transition_bar_html(_transition_d.get("travel_jp",[]), compact=True)}</div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header py">\U0001f7e3 PY \u2013 Travel</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_py",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table>{transition_bar_html(_transition_d.get("travel_py",[]), compact=True)}</div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header sy">\U0001f7eb SY \u2013 Travel</div><div class="dp-body"><table class="dt dt-compact"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_sy",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table>{transition_bar_html(_transition_d.get("travel_sy",[]), compact=True)}</div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f697 Vehicles</div><div class="dp-body"><table class="dt"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{vb_html}</table></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header green">\U0001f4c5 NIT</div><div class="dp-body"><p style="font-size:1.05rem;color:#2a3a2a;margin:0;line-height:1.35;">{nit}</p></div></div>')
    _cards.append(f'<div class="dp"><div class="dp-header navy">\U0001f5d3\ufe0f Meeting Room</div><div class="dp-body">{_mrb_html}</div></div>')
    # Staff Responsibilities moved here (was up front, the same size as
    # every attendance/travel card) and condensed to one dense line of
    # label:value pairs instead of four stacked blocks - it's useful but
    # doesn't need the same visual weight, so it now takes a noticeably
    # smaller spot near the end of the board rather than competing with
    # the higher-priority cards for the most prominent positions.
    _cards.append(
        f'<div class="dp"><div class="dp-header amber">\u2b50 Staff Responsibilities</div>'
        f'<div class="dp-body dp-body-compact">'
        f'<span class="resp-item">\U0001f373 <strong>Kitchen:</strong> {kitchen}</span>'
        f'<span class="resp-item">\U0001f4cc <strong>PD:</strong> {sr.get("meeting_pd_focus","") or "\u2014"}</span>'
        f'<span class="resp-item">\U0001fa91 <strong>Chair:</strong> {sr.get("chair","") or "\u2014"}</span>'
        f'<span class="resp-item">\U0001f4dd <strong>Minutes:</strong> {sr.get("minutes","") or "\u2014"}</span>'
        f'</div></div>'
    )

    st.markdown(f'<div class="dp-grid">{"".join(_cards)}</div>', unsafe_allow_html=True)
    if st.session_state.get("_trade_bookings_last_error"):
        st.warning(f"⚠️ Couldn't load trade bookings for {today}: {st.session_state['_trade_bookings_last_error']}")

    # ── Full-width, below the grid: things that deserve a second look
    # rather than being squeezed into a masonry column ───────────────
    tc_today = d_data.get("travel_changes", [])
    tc_filtered = [r for r in tc_today if any(r.get(k,"") for k in ["Student","Change Type","Reason","Time","How Departed"])]
    if tc_filtered:
        tc_rows_html = "".join([
            f'<tr><td><strong style="color:#1a2e44;">{r.get("Student","")}</strong></td>'
            f'<td style="font-size:.95rem;">{r.get("Program","")}</td>'
            f'<td><span class="tc-badge">{r.get("Change Type","")}</span></td>'
            f'<td style="font-size:.95rem;color:#666;">{r.get("Reason","")}</td>'
            f'<td style="font-family:monospace;font-size:.95rem;color:#c0392b;font-weight:700;">{r.get("Time","")}</td>'
            f'<td style="font-size:.95rem;">{r.get("How Departed","")}</td></tr>'
            for r in tc_filtered
        ])
        st.markdown(f'<div class="dp dp-full" style="border-left:4px solid #c0392b;"><div class="dp-header red">\U0001f504 Travel Changes</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Program</th><th>Change</th><th>Reason</th><th>Time</th><th>How Departed</th></tr>{tc_rows_html}</table></div></div>', unsafe_allow_html=True)

    bc_today = load_bulletin_changes(today)
    if bc_today:
        pc_parts = []
        for ch in bc_today:
            reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt",False); trt_name = ch.get("trt_name",""); staff_rows = ch.get("staff_rows",[])
            color = "#c0392b" if reason == "Staff Absence" else "#0e7490"
            meta = []
            if absent: meta.append(f"Absent: <strong>{absent}</strong>")
            if has_trt: meta.append(f"TRT: {trt_name or 'On site'}")
            tt_html = _timetable_grid_html(staff_rows, PC_TIME_SLOTS_30, dark=True)
            pc_parts.append(f'<div style="margin-bottom:10px;border-left:3px solid {color};padding-left:8px;"><div style="font-size:.85rem;color:#a8c8a8;margin-bottom:3px;font-weight:700;">{reason.upper()}{(" \u00b7 " + " \u00b7 ".join(meta)) if meta else ""}</div>{tt_html or "<span style=\'color:#3a5a3a;font-size:.85rem;\'>No timetable entered</span>"}</div>')
        st.markdown(f'<div class="dp dp-full"><div class="dp-header green">\U0001f4ca Program Changes</div><div class="dp-body">{"".join(pc_parts)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="dp dp-full"><div class="dp-header green">\U0001f4ca Program Changes</div><div class="dp-body"><span class="dt-em">No program changes today</span></div></div>', unsafe_allow_html=True)

    # ── Program Changes Manager entries (from standalone tool) ──
    _pcm_today = load_pc_manager_changes(today)
    if _pcm_today:
        _pcm_parts = []
        for _pcm in _pcm_today:
            _pcm_staff = _pcm.get("staff_name","N/A"); _pcm_reason = _pcm.get("reason","")
            _pcm_covered = _pcm.get("covered_by",""); _pcm_blocks = _pcm.get("time_blocks",[]) or []
            _block_rows = "".join([
                f'<tr><td style="color:#C8760A;font-weight:600;white-space:nowrap;font-size:.85rem;">'
                f'{_fmt_pc_time(b.get("start_time",""))} \u2192 {_fmt_pc_time(b.get("end_time",""))}</td>'
                f'<td style="font-size:.85rem;">{b.get("modified_program","")}'
                f'{"<br><span style=\'color:#6BBF4E;font-size:0.9em;\'>Release: "+b["released_by"]+"</span>" if b.get("released_by") else ""}'
                f'</td></tr>'
                for b in _pcm_blocks
            ])
            _cov_html = f'<div style="font-size:.85rem;color:#6BBF4E;font-weight:600;margin:.2rem 0;">Covered by: {_pcm_covered}</div>' if _pcm_covered else ""
            _pcm_parts.append(
                f'<div style="margin-bottom:8px;border-left:3px solid #C8760A;padding-left:7px;">'
                f'<div style="font-size:.9rem;font-weight:700;color:#6BBF4E;">{_pcm_staff}</div>'
                f'<div style="font-size:.85rem;color:#a8c8a8;margin-bottom:3px;">{_pcm_reason}</div>'
                f'{_cov_html}'
                f'{"<table style=\'border-collapse:collapse;width:100%;\'>" + _block_rows + "</table>" if _block_rows else ""}'
                f'</div>'
            )
        st.markdown(
            f'<div class="dp dp-full"><div class="dp-header amber">\U0001f4cb Staff Timetable Changes</div>'
            f'<div class="dp-body">{"".join(_pcm_parts)}</div></div>',
            unsafe_allow_html=True
        )

    import streamlit.components.v1 as components
    components.html("""<script>(function(){function u(){var o={timeZone:'Australia/Adelaide',hour:'numeric',minute:'2-digit',hour12:true};var t=new Date().toLocaleTimeString('en-AU',o).toUpperCase();var e=window.parent.document.getElementById('live-clock');if(e)e.textContent=t}u();setInterval(u,1000)})();</script>""", height=0)
    st.markdown(f'<div class="fact-bar"><span class="fact-label">\U0001f4a1 Fun Fact</span><span>{fun or "No fun fact for today"}</span></div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════
# QUICK ADD MODE
# ══════════════════════════════════════════════════════════════
if params.get("quickadd") == "true":
    st.markdown("""<style>[data-testid="stAppViewContainer"]{background:#f0f7eb!important}.main .block-container{padding:2rem 2rem 3rem!important;max-width:620px!important;margin:0 auto!important}[data-testid="stHeader"]{display:none}#MainMenu,footer,.stDeployButton{display:none}</style>""", unsafe_allow_html=True)
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center;color:white;"><div style="font-size:2rem;margin-bottom:.3rem;">\U0001f4dd</div><div style="font-size:1.3rem;font-weight:700;margin-bottom:.25rem;">Staff Quick Notice</div><div style="font-size:.85rem;opacity:.85;">Cowandilla Learning Centre \u00b7 Daily Bulletin</div></div>""", unsafe_allow_html=True)
    with st.form("qa_standalone_form", clear_on_submit=True):
        qa_name = st.text_input("Your name *", placeholder="e.g. Sarah")
        qa_cat = st.selectbox("Category *", list(NOTICE_CATS.keys()), format_func=lambda x: f"{NOTICE_CATS[x]['emoji']} {x}")
        qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
        qa_body = st.text_area("Details (optional)", height=110)
        qa_date = st.date_input("For which day?", value=date.today())
        if st.form_submit_button("\U0001f4e2 Post Notice to Bulletin", type="primary", use_container_width=True):
            if not qa_name.strip(): st.warning("Please enter your name.")
            elif not qa_title.strip(): st.warning("Please enter a title.")
            else:
                save_notice({"submitted_by": qa_name.strip(), "category": qa_cat, "title": qa_title.strip(), "body": qa_body.strip(), "notice_date": str(qa_date)})
                st.success(f"\u2705 Notice posted for {qa_date.strftime('%-d %B')}!"); st.balloons()
    st.markdown('<div style="text-align:center;"><a href="/Daily_Bulletin" style="font-size:.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">\u2190 Back to full bulletin</a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="/Daily_Bulletin?display=true" style="font-size:.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">Staff room display \u2192</a></div>', unsafe_allow_html=True)
    st.stop()


# ── TOP NAV ───────────────────────────────────────────────────
edit = st.session_state.edit_mode and st.session_state.authenticated
auth_badge = ('<span class="nav-badge edit">\u270f\ufe0f Edit Mode</span>' if edit else '<span class="nav-badge">\u2705 Staff</span>') if st.session_state.authenticated else ''
st.markdown(f'<div class="top-nav"><div class="top-nav-left"><div class="top-nav-logo">CLC</div><div><div class="top-nav-title">Daily Bulletin</div><div class="top-nav-sub">Cowandilla Learning Centre</div></div></div><div class="top-nav-right">{auth_badge}</div></div>', unsafe_allow_html=True)

current_date = st.session_state.selected_date
bulletin_data = load_bulletin(current_date)
# Hoisted so both the "at a glance" strip and the Program Changes section
# below use the same single fetch instead of loading twice.
_pcm_changes_today = load_pc_manager_changes(current_date)
_admin_notices_today = load_notices(for_date=current_date)

page_tab, quickadd_tab, archive_tab, login_tab = st.tabs(["\U0001f4cb Bulletin", "\U0001f4dd Quick Add", "\U0001f5c2\ufe0f Archive", "\U0001f510 Staff"])

with page_tab:
    if st.query_params.get("from_display") == "true" and not st.session_state.authenticated:
        st.markdown("""<div style="background:#1a2e44;border-left:4px solid #6BBF4E;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;"><span style="color:white;font-size:.85rem;">\U0001f510 Enter your staff password to edit today's bulletin, then save to return to the display screen.</span></div>""", unsafe_allow_html=True)
        pw_col, btn_col, back_col = st.columns([2,1,1])
        with pw_col:
            quick_pw = st.text_input("Staff Password", type="password", key="quick_pw", label_visibility="collapsed", placeholder="Enter staff password...")
        with btn_col:
            if st.button("\U0001f513 Login", type="primary", use_container_width=True):
                if quick_pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.session_state.edit_mode = True; st.rerun()
                else: st.error("Incorrect password")
        with back_col:
            st.markdown('<a href="/Daily_Bulletin?display=true" style="display:block;text-align:center;background:#eef1f4;color:#1a2e44;font-weight:600;font-size:.85rem;padding:.5rem;border-radius:8px;text-decoration:none;">\u21a9\ufe0f Back to Display</a>', unsafe_allow_html=True)
        st.markdown("---")

    week = week_dates(current_date)
    import html as _html, re as _re
    fact = bulletin_data.get("fun_fact","")
    fact_clean = _html.escape(_re.sub(r'<[^>]+>', '', fact)).strip()
    fun_fact_html = (f'<div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);border-radius:12px;padding:.65rem 1rem;max-width:480px;"><div style="font-size:.65rem;color:rgba(255,255,255,0.6);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.2rem;">\U0001f4a1 Fun Fact</div><div style="font-size:.85rem;color:white;font-weight:500;line-height:1.4;">{fact_clean}</div></div>') if fact_clean else ""
    edit_badge_html = '<div class="hero-edit-badge">\u270f\ufe0f EDITING</div>' if edit else ""
    st.markdown(f"""<div class="bulletin-hero">{edit_badge_html}<div class="bulletin-hero-inner"><div><div class="bulletin-date-label">{term_label(current_date)}</div><div class="bulletin-date-main">{current_date.strftime("%A %-d %B")}</div><div class="bulletin-date-sub">{current_date.strftime("%Y")}</div></div>{fun_fact_html}</div></div>""", unsafe_allow_html=True)

    # \u2500\u2500 Unified header control bar \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # Was three separately-boxed banners (week nav / jump-to-date /
    # edit-save-logout buttons) stacked on top of each other. Now one
    # container: week navigation on top, then a single button row that
    # folds "jump to date" in as a compact widget instead of its own box.
    with st.container(key="header_bar"):
        nav_l, nav_m, nav_r = st.columns([1,4,1])
        with nav_l:
            if st.button("\u2190 Prev Week", key="prev_week", use_container_width=True): st.session_state.selected_date = week[0] - timedelta(days=7); st.rerun()
        with nav_m:
            wls = f"Week of {week[0].strftime('%-d %b')} \u2013 {week[-1].strftime('%-d %b %Y')}"
            if date.today() in week: wls += " \u00b7 This Week"
            st.markdown(f'<div class="week-label" style="color:{"#4a8f33" if date.today() in week else "#5a6e5a"};">{wls}</div>', unsafe_allow_html=True)
        with nav_r:
            if st.button("Next Week \u2192", key="next_week", use_container_width=True): st.session_state.selected_date = week[0] + timedelta(days=7); st.rerun()
        day_cols = st.columns(5)
        for i, d in enumerate(week):
            with day_cols[i]:
                lbl = d.strftime("%a %-d %b") + (" \u25c9" if d == date.today() else "")
                if st.button(lbl, key=f"day_{d}", use_container_width=True, type="primary" if d==current_date else "secondary"): st.session_state.selected_date = d; st.rerun()

        if st.session_state.pop("_save_ok", False):
            st.success("\u2705 Bulletin saved successfully!")

        st.markdown('<hr style="border:none;border-top:1.5px solid #eef3ec;margin:.75rem 0 .6rem;">', unsafe_allow_html=True)
        if st.session_state.authenticated:
            ctrl_cols = st.columns([1,1,1,1.6,1])
            with ctrl_cols[0]:
                if st.button("\u270f\ufe0f Edit" if not edit else "\U0001f441\ufe0f View", type="primary" if not edit else "secondary", use_container_width=True): st.session_state.edit_mode = not st.session_state.edit_mode; st.rerun()
            with ctrl_cols[1]:
                if edit and st.button("\U0001f4be Save", type="primary", use_container_width=True): st.session_state["_pending_save"] = True
            with ctrl_cols[2]:
                if st.button("\U0001f6aa Logout", type="secondary", use_container_width=True): st.session_state.authenticated = False; st.session_state.edit_mode = False; st.rerun()
            with ctrl_cols[3]:
                # Key is tied to current_date so the widget re-seeds itself to
                # value=current_date whenever the date changes via ANY control
                # (prev/next week, a day pill, or a previous jump) — otherwise
                # a stale picker value from an earlier pick would silently
                # override navigation done through those other controls on the
                # very next rerun.
                jump_date = st.date_input("Jump to date", value=current_date, key=f"jump_date_picker_{current_date}", label_visibility="collapsed")
                if jump_date != current_date: st.session_state.selected_date = jump_date; st.rerun()
            with ctrl_cols[4]:
                st.markdown('<a href="/Daily_Bulletin?display=true" target="_blank" style="display:block;text-align:center;background:#1a2e44;color:white;font-weight:600;font-size:.8rem;padding:.45rem .75rem;border-radius:8px;text-decoration:none;white-space:nowrap;">\U0001f4fa Staff Room</a>', unsafe_allow_html=True)
        else:
            ctrl_cols = st.columns([1,1.6,1])
            with ctrl_cols[0]:
                if st.button("\U0001f510 Staff Login", type="secondary", use_container_width=True): st.session_state.show_inline_login = not st.session_state.get("show_inline_login", False); st.rerun()
            with ctrl_cols[1]:
                # Key is tied to current_date so the widget re-seeds itself to
                # value=current_date whenever the date changes via ANY control
                # (prev/next week, a day pill, or a previous jump) — otherwise
                # a stale picker value from an earlier pick would silently
                # override navigation done through those other controls on the
                # very next rerun.
                jump_date = st.date_input("Jump to date", value=current_date, key=f"jump_date_picker_{current_date}", label_visibility="collapsed")
                if jump_date != current_date: st.session_state.selected_date = jump_date; st.rerun()
            with ctrl_cols[2]:
                st.markdown('<a href="/Daily_Bulletin?display=true" target="_blank" style="display:block;text-align:center;background:#1a2e44;color:white;font-weight:600;font-size:.8rem;padding:.45rem .75rem;border-radius:8px;text-decoration:none;white-space:nowrap;">\U0001f4fa Staff Room</a>', unsafe_allow_html=True)

        if not st.session_state.authenticated and st.session_state.get("show_inline_login", False):
            st.markdown('<div style="background:#f0f7eb;border:1.5px solid #6BBF4E;border-radius:10px;padding:1rem 1.25rem;margin-top:.75rem;">', unsafe_allow_html=True)
            lc1, lc2, lc3 = st.columns([3,1,1])
            with lc1: quick_pw = st.text_input("Staff password", type="password", key="inline_pw", label_visibility="collapsed", placeholder="Enter staff password\u2026")
            with lc2:
                if st.button("\U0001f513 Login", type="primary", use_container_width=True, key="inline_login_btn"):
                    if quick_pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.session_state.edit_mode = True; st.session_state.show_inline_login = False; st.rerun()
                    else: st.error("Incorrect password")
            with lc3:
                if st.button("Cancel", type="secondary", use_container_width=True, key="inline_cancel"): st.session_state.show_inline_login = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    if edit:
        # Editing cue that's visible everywhere on the page, not just the
        # top bar - a soft amber wash on the whole working area plus an
        # amber left-edge on every card, so it's never ambiguous whether
        # you're looking at the live bulletin or a draft. Injected as its
        # own conditional <style> block (rather than a `.content-area.editing`
        # descendant selector) because .content-area is a div opened by one
        # st.markdown() call and never closed by a matching one - it renders
        # as an empty fragment with no real descendants, so nothing inside
        # it can ever be reached that way. Targeting real, page-wide
        # elements directly here works regardless of that.
        st.markdown(
            '<style>'
            '[data-testid="stMainBlockContainer"]{background:#fdf8ee}'
            'div.stVerticalBlock[class*="st-key-card_"]{border-left:4px solid #e8a125}'
            '</style>',
            unsafe_allow_html=True
        )

    # \u2500\u2500 Quick-jump nav bar \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # Replaces the old nested tab bar (s1-s4): the whole bulletin now
    # flows as one page, and this sticky strip lets staff jump straight
    # to a section instead of clicking through tabs-within-a-tab.
    _quicknav_class = "quicknav editing" if edit else "quicknav"
    _quicknav_tag = '<span class="quicknav-tag">\u270f\ufe0f Editing</span>' if edit else ""
    _quicknav_links = ['<a href="#sec-notices">\U0001f4e2 Notices</a>'] if (_admin_notices_today or edit) else []
    _quicknav_links += [
        '<a href="#sec-staff">\U0001f465 Staff &amp; Meetings</a>',
        '<a href="#sec-travel">\U0001f68c Travel &amp; Vehicles</a>',
        '<a href="#sec-responsibilities">\U0001f4cc Responsibilities &amp; NIT</a>',
        '<a href="#sec-program">\U0001f4ca Program Changes</a>',
    ]
    st.markdown(
        f'<div class="{_quicknav_class}">{"".join(_quicknav_links)}{_quicknav_tag}</div>',
        unsafe_allow_html=True
    )

    # \u2500\u2500 Today at a glance \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # One-line summary chips so staff can tell at a glance whether
    # anything today needs attention, without opening every section.
    render_glance_strip(bulletin_data, len(_admin_notices_today), len(_pcm_changes_today), trade_n=len(trade_bookings_as_visitor_rows(current_date)))

    _admin_notices = _admin_notices_today
    if _admin_notices or edit:
        st.markdown('<div id="sec-notices" class="section-anchor"></div>', unsafe_allow_html=True)
        with card("notices", "green", "\U0001f4dd", "Staff Notices"):
            if _admin_notices:
                for _n in _admin_notices:
                    _cat = _n.get("category","General"); _nc = NOTICE_CATS.get(_cat, NOTICE_CATS["General"]); _nid = _n.get("id","")
                    _nc1, _nc2 = st.columns([9,1])
                    with _nc1:
                        st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {_nc["color"]};padding:.75rem 1rem;margin-bottom:.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);"><div style="margin-bottom:.2rem;"><span style="background:{_nc["bg"]};color:{_nc["color"]};font-size:.65rem;font-weight:700;text-transform:uppercase;padding:.15rem .5rem;border-radius:20px;">{_nc["emoji"]} {_cat}</span><span style="font-size:.7rem;color:#9ab09a;margin-left:.5rem;">from {_n.get("submitted_by","")}</span></div><div style="font-size:.9rem;font-weight:700;color:#1a2e44;margin:.3rem 0 .2rem;">{_n.get("title","")}</div><div style="font-size:.82rem;color:#3a4a3a;line-height:1.5;">{_n.get("body","")}</div></div>', unsafe_allow_html=True)
                    with _nc2:
                        if edit:
                            st.write("")
                            if st.button("\U0001f5d1\ufe0f", key=f"top_del_n_{_nid}", help="Delete notice"): delete_notice(_nid); st.rerun()
            else:
                st.markdown('<div style="text-align:center;padding:1rem;color:#9ab09a;font-size:.85rem;">No notices today \u2014 staff can add via the \U0001f4dd Quick Add tab</div>', unsafe_allow_html=True)

    section_divider("sec-staff", 1, "\U0001f465", "Staff & Meetings")
    if True:
        import pandas as pd
        if edit:
            auto_fact = daily_fun_fact(current_date); current_fact = (bulletin_data.get("fun_fact") or "").strip()
            fc1, fc2 = st.columns([5,1])
            with fc1: new_fact = st.text_input("\U0001f4a1 Fun Fact of the Day", value=current_fact if current_fact else auto_fact, key="fun_fact_input")
            with fc2:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                if st.button("\U0001f3b2 New", key="new_fact", use_container_width=True): bulletin_data["fun_fact"] = auto_fact; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            bulletin_data["fun_fact"] = new_fact

        # Three columns instead of two \u2014 real bounded cards (see `card()`)
        # make it safe to pack the page wider instead of one long pair of
        # stacked columns, so a normal desktop screen shows more at once.
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            with card("staff_absent", "green", "\U0001f645", "Staff Absent"):
                if edit:
                    sa_df = pd.DataFrame(bulletin_data["staff_absent"])
                    sa_edited = st.data_editor(sa_df, key="sa_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                    bulletin_data["staff_absent"] = sa_edited.to_dict("records")
                else:
                    _s_rows = [r for r in bulletin_data["staff_absent"] if (r.get("Staff Member") or "").strip() or (r.get("TRT") or "").strip()]
                    if _s_rows: st.markdown('<table class="data-table"><tr><th>Staff Member</th><th>TRT</th></tr>'+"".join([f"<tr><td><strong>{r.get('Staff Member','')}</strong></td><td>{r.get('TRT','')}</td></tr>" for r in _s_rows])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No staff absent today</div>', unsafe_allow_html=True)

            with card("excursions", "blue", "\U0001f68c", "Excursions"):
                if edit:
                    df = pd.DataFrame(bulletin_data["excursions"]); edited = st.data_editor(df, key="ex_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["excursions"] = edited.to_dict("records")
                else:
                    rows = bulletin_data["excursions"]; has_data = any(any(v for v in r.values()) for r in rows)
                    if has_data: st.markdown('<table class="data-table"><tr><th>Program</th><th>Staff</th><th>Departing</th><th>Returning</th><th>Location</th></tr>'+"".join([f"<tr><td>{r.get('Program','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Location','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f5fa\ufe0f</div>No excursions today</div>', unsafe_allow_html=True)

        with col_b:
            with card("student_absent", "blue", "\U0001f392", "Student Absent"):
                if edit:
                    st_df = pd.DataFrame(bulletin_data["student_absent"])
                    st_edited = st.data_editor(st_df, key="st_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                    bulletin_data["student_absent"] = st_edited.to_dict("records")
                else:
                    _st_rows = [r for r in bulletin_data["student_absent"] if (r.get("Student") or "").strip()]
                    if _st_rows: st.markdown('<table class="data-table"><tr><th>Student</th><th>Program</th><th>Reason</th></tr>'+"".join([f"<tr><td><strong>{r.get('Student','')}</strong></td><td>{r.get('Program','')}</td><td>{r.get('Reason','')}</td></tr>" for r in _st_rows])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No students absent today</div>', unsafe_allow_html=True)

            with card("entry_meetings", "brown", "\U0001f4e5", "Entry Meetings \u2013 Annette"):
                if edit:
                    df = pd.DataFrame(bulletin_data["entry_meetings"]); edited = st.data_editor(df, key="em_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["entry_meetings"] = edited.to_dict("records")
                else:
                    rows = bulletin_data["entry_meetings"]; has_data = any(any(v for v in r.values()) for r in rows)
                    if has_data: st.markdown('<table class="data-table"><tr><th>Time</th><th>Program</th><th>Student</th></tr>'+"".join([f"<tr><td>{r.get('Time','')}</td><td>{r.get('Program','')}</td><td>{r.get('Student','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ed</div>No entry meetings today</div>', unsafe_allow_html=True)

            with card("staff_meetings", "navy", "\U0001f91d", "Staff Meetings"):
                if edit:
                    df = pd.DataFrame(bulletin_data["staff_meetings"]); edited = st.data_editor(df, key="sm_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["staff_meetings"] = edited.to_dict("records")
                else:
                    all_mtgs = list(bulletin_data["staff_meetings"] or []) + load_scheduled_meetings(current_date); has_data = any(any(v for v in r.values()) for r in all_mtgs)
                    if has_data: st.markdown('<table class="data-table"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>'+"".join([f"<tr><td>{r.get('Type','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Location','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Student','')}</td></tr>" for r in all_mtgs if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4c5</div>No staff meetings today</div>', unsafe_allow_html=True)

        with col_c:
            with card("additional_messages", "slate", "\U0001f4ac", "Additional Staff Messages"):
                if edit:
                    df = pd.DataFrame(bulletin_data["additional_messages"]); edited = st.data_editor(df, key="msg_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["additional_messages"] = edited.to_dict("records")
                else:
                    rows = bulletin_data["additional_messages"]; has_data = any(any(v for v in r.values()) for r in rows)
                    if has_data: st.markdown('<table class="data-table"><tr><th>Staff Member</th><th>Information</th></tr>'+"".join([f"<tr><td><strong>{r.get('Staff Member','')}</strong></td><td>{r.get('Information','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ad</div>No additional messages</div>', unsafe_allow_html=True)

            with card("visitors_on_site", "green", "\U0001f465", "Visitors on Site"):
                _trade_vis_rows = trade_bookings_as_visitor_rows(current_date)
                if edit:
                    _vis_raw = bulletin_data.get("visitors_on_site") or []
                    if not _vis_raw:
                        _vis_raw = [{"Visitor Name":"","Reason":"","Program":"","Staff Responsible":"","Arriving":"","Departing":"","Location":""} for _ in range(4)]
                    _vis_cols = ["Visitor Name","Reason","Program","Staff Responsible","Arriving","Departing","Location"]
                    _vis_raw = [{c: (r.get(c, "") or "") for c in _vis_cols} for r in _vis_raw]
                    vis_df = pd.DataFrame(_vis_raw, columns=_vis_cols)
                    vis_edited = st.data_editor(vis_df, key="vis_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                        column_config={
                            "Reason": st.column_config.SelectboxColumn("Reason", options=VISITOR_REASON_OPTIONS, required=False),
                            "Program": st.column_config.SelectboxColumn("Program", options=["JP","PY","SY"], required=False,
                                help="Which program they're visiting — Student Observations with a program appear on the CLC Calendar"),
                        })
                    bulletin_data["visitors_on_site"] = vis_edited.to_dict("records")
                    if _trade_vis_rows:
                        st.caption("🔧 Auto-added from Trade Bookings — edit or cancel these there, not here:")
                        st.markdown('<table class="data-table"><tr><th>Visitor</th><th>Reason</th><th>Program</th><th>Staff Responsible</th><th>Arriving</th><th>Departing</th><th>Location</th></tr>'+"".join([f"<tr><td><strong>{r.get('Visitor Name','')}</strong></td><td>{r.get('Reason','')}</td><td>{r.get('Program','')}</td><td>{r.get('Staff Responsible','')}</td><td>{r.get('Arriving','')}</td><td>{r.get('Departing','')}</td><td>{r.get('Location','')}</td></tr>" for r in _trade_vis_rows])+"</table>", unsafe_allow_html=True)
                        st.markdown('<div style="margin-top:0.4rem;font-size:0.75rem;color:#6b7280;">📌 <a href="/Trade_Bookings" target="_self" style="color:#1a2e44;text-decoration:none;font-weight:600;">Manage Trade Bookings →</a></div>', unsafe_allow_html=True)
                    elif st.session_state.get("_trade_bookings_last_error"):
                        st.warning(f"⚠️ Couldn't load trade bookings: {st.session_state['_trade_bookings_last_error']}")
                else:
                    vis_rows = bulletin_data.get("visitors_on_site", []) + _trade_vis_rows
                    has_vis = any(any(v for v in r.values()) for r in vis_rows)
                    if has_vis: st.markdown('<table class="data-table"><tr><th>Visitor</th><th>Reason</th><th>Program</th><th>Staff Responsible</th><th>Arriving</th><th>Departing</th><th>Location</th></tr>'+"".join([f"<tr><td><strong>{r.get('Visitor Name','')}</strong></td><td>{r.get('Reason','')}</td><td>{r.get('Program','')}</td><td>{r.get('Staff Responsible','')}</td><td>{r.get('Arriving','')}</td><td>{r.get('Departing','')}</td><td>{r.get('Location','')}</td></tr>" for r in vis_rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f6b6</div>No visitors today</div>', unsafe_allow_html=True)
                    if not _trade_vis_rows and st.session_state.get("_trade_bookings_last_error"):
                        st.warning(f"⚠️ Couldn't load trade bookings: {st.session_state['_trade_bookings_last_error']}")

    section_divider("sec-travel", 2, "\U0001f68c", "Travel & Vehicles")
    if True:
        import pandas as pd
        st.markdown('<div style="font-size:.8rem;font-weight:600;color:#4a6640;margin-bottom:.5rem;">\U0001f4c5 Planned Travel \u2014 expected arrivals &amp; departures</div>', unsafe_allow_html=True)
        jp_col, py_col, sy_col = st.columns(3)
        _transition_bp = transition_students_by_program(bulletin_data.get("student_absent", []))

        def render_travel_card(col, key, label, color):
            with col:
                with card(key, color, "", label):
                    rows = bulletin_data[key]
                    if edit:
                        df = pd.DataFrame(rows)
                        edited = st.data_editor(df, key=f"{key}_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                            column_config={"Transport": st.column_config.SelectboxColumn("Transport", options=TRANSPORT_OPTIONS, required=False)})
                        bulletin_data[key] = edited.to_dict("records")
                    else:
                        has_data = any(any(v for v in r.values()) for r in rows)
                        if has_data:
                            st.markdown('<table class="data-table"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>'+"".join([f"<tr><td>{r.get('Student','')}</td><td>{r.get('Arrival Time','')}</td><td>{r.get('Departure Time','')}</td><td>{r.get('Transport','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                        else: st.markdown('<div class="empty-state"><div class="icon">\U0001f690</div>No travel today</div>', unsafe_allow_html=True)
                    _trans_names = _transition_bp.get(key, [])
                    if _trans_names:
                        st.markdown(transition_bar_html(_trans_names), unsafe_allow_html=True)

        render_travel_card(jp_col, "travel_jp", "\U0001f7e6 Junior Primary \u2013 Travel", "#3d5d80")
        render_travel_card(py_col, "travel_py", "\U0001f7e3 Primary Years \u2013 Travel", "#5b4a75")
        render_travel_card(sy_col, "travel_sy", "\U0001f7eb Senior Years \u2013 Travel", "#7a5c3f")

        st.markdown('<div style="font-size:.8rem;font-weight:600;color:#c0392b;margin:1rem 0 .5rem;">\U0001f504 Travel Plan Changes \u2014 update if a student\u2019s plan changes during the day</div>', unsafe_allow_html=True)
        with card("travel_changes", "red", "\U0001f504", "Travel Plan Changes"):
            tc_rows = bulletin_data.get("travel_changes") or []
            if edit:
                if not tc_rows:
                    tc_rows = [{"Student":"","Program":"","Change Type":"","Reason":"","Time":"","How Departed":""} for _ in range(3)]
                tc_df = pd.DataFrame(tc_rows)
                tc_edited = st.data_editor(tc_df, key="tc_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                    column_config={
                        "Program": st.column_config.SelectboxColumn("Program", options=["JP","PY","SY"], required=False),
                        "Change Type": st.column_config.SelectboxColumn("Change Type", options=CHANGE_TYPE_OPTIONS, required=False),
                        "How Departed": st.column_config.SelectboxColumn("How Departed", options=TRANSPORT_OPTIONS, required=False),
                    })
                bulletin_data["travel_changes"] = tc_edited.to_dict("records")
                st.markdown('<div style="background:#fff8f7;border:1px solid #f5c6c0;border-radius:8px;padding:.5rem .75rem;margin-top:.5rem;font-size:.75rem;color:#7a2a2a;">\U0001f4a1 <strong>Tip:</strong> Fill in whenever a student\u2019s travel plan changes \u2014 e.g. early departure, parent collecting instead of taxi. Appears highlighted on the staff room display so staff notice it immediately.</div>', unsafe_allow_html=True)
            else:
                has_tc = any(any(v for v in r.values()) for r in tc_rows)
                if has_tc:
                    st.markdown('<table class="data-table"><tr><th>Student</th><th>Program</th><th>Change</th><th>Reason</th><th>Time</th><th>How Departed</th></tr>'+"".join([f"<tr><td><strong>{r.get('Student','')}</strong></td><td>{r.get('Program','')}</td><td><span class='change-badge'>{r.get('Change Type','')}</span></td><td>{r.get('Reason','')}</td><td><strong style='color:#c0392b;'>{r.get('Time','')}</strong></td><td>{r.get('How Departed','')}</td></tr>" for r in tc_rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No travel changes today</div>', unsafe_allow_html=True)

        with card("vehicle_bookings", "navy", "\U0001f697", "Vehicle Bookings \u2014 Van & Kia"):
            vb_list = bulletin_data.get("vehicle_bookings",[])
            if isinstance(vb_list, dict): vb_list = []
            if edit:
                if vb_list:
                    st.markdown("**Current bookings:**")
                    for _bi, _bk in enumerate(vb_list):
                        _bc1, _bc2, _bc3, _bc4 = st.columns([1,2,2,1])
                        with _bc1: st.markdown(f"**{'\U0001f690 Van' if _bk.get('vehicle','')=='Van' else '\U0001f699 Kia'}**")
                        with _bc2: st.markdown(f"**{_bk.get('booker','\u2014')}**")
                        with _bc3: st.markdown("\U0001f550 Whole day" if _bk.get("whole_day",True) else f"\U0001f550 {_bk.get('start_time','?')} \u2013 {_bk.get('end_time','?')}")
                        with _bc4:
                            if st.button("\U0001f5d1\ufe0f", key=f"vb_del_{_bi}"): vb_list.pop(_bi); bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                    st.markdown("---")
                st.markdown("**Add a booking:**")
                _av1, _av2, _av3 = st.columns([1,2,2])
                with _av1: _new_vehicle = st.selectbox("Vehicle", ["Van","Kia"], key="vb_new_vehicle")
                with _av2: _new_booker = st.text_input("Booked by", key="vb_new_booker", placeholder="e.g. Sarah")
                with _av3: _new_whole = st.checkbox("Whole day", value=True, key="vb_new_whole")
                if not _new_whole:
                    _at1, _at2 = st.columns(2)
                    with _at1: _new_start = st.text_input("Start time", key="vb_new_start", placeholder="e.g. 9:30")
                    with _at2: _new_end = st.text_input("End time", key="vb_new_end", placeholder="e.g. 12:00")
                else: _new_start = _new_end = ""
                if st.button("\u2795 Add Booking", type="primary", key="vb_add_btn"):
                    if _new_booker.strip(): vb_list.append({"vehicle":_new_vehicle,"booker":_new_booker.strip(),"whole_day":_new_whole,"start_time":_new_start.strip(),"end_time":_new_end.strip()}); bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                    else: st.warning("Please enter a name.")
            else:
                if vb_list and any(b.get("booker","") for b in vb_list):
                    def _vbt(b): return "Whole day" if b.get("whole_day",True) else f"{b.get('start_time','?')} \u2013 {b.get('end_time','?')}"
                    st.markdown('<table class="data-table"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>'+"".join([f'<tr><td>{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td><td><span class="vehicle-booking">{b.get("booker","")}</span></td><td class="vehicle-time">{_vbt(b)}</td></tr>' for b in vb_list if b.get("booker","")])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f697</div>No vehicle bookings today</div>', unsafe_allow_html=True)

    section_divider("sec-responsibilities", 3, "\U0001f4cc", "Responsibilities & NIT")
    if True:
        resp_col, nit_col, room_col = st.columns(3)
        with resp_col:
            with card("staff_responsibilities", "amber", "\u2b50", "Staff Responsibilities"):
                sr = bulletin_data["staff_responsibilities"]
                if edit:
                    bulletin_data["staff_responsibilities"] = {"kitchen_duties": st.text_input("\U0001f373 Kitchen Duties", sr.get("kitchen_duties",""), key="sr_k"),"meeting_pd_focus": st.text_input("\U0001f4cc Staff Meeting PD Focus", sr.get("meeting_pd_focus",""), key="sr_pd"),"chair": st.text_input("\U0001fa91 Meeting Chair", sr.get("chair",""), key="sr_c"),"minutes": st.text_input("\U0001f4dd Meeting Minutes", sr.get("minutes",""), key="sr_m"),}
                else:
                    kitchen = sr.get("kitchen_duties","")
                    st.markdown(f'<table class="data-table"><tr class="kitchen-row"><td><span class="kitchen-badge">\U0001f373 Kitchen</span></td><td><strong>{kitchen or "\u2014"}</strong></td></tr><tr><td>\U0001f4cc PD Focus</td><td>{sr.get("meeting_pd_focus","") or "\u2014"}</td></tr><tr><td>\U0001fa91 Chair</td><td>{sr.get("chair","") or "\u2014"}</td></tr><tr><td>\U0001f4dd Minutes</td><td>{sr.get("minutes","") or "\u2014"}</td></tr></table>', unsafe_allow_html=True)
        with nit_col:
            with card("nit_bookings", "green", "📅", "Additional NIT Bookings"):
                nit_bookings = load_todays_nit_bookings(current_date)
                if nit_bookings:
                    for booking in nit_bookings:
                        time_slot = booking.get('time_slot', '')
                        staff_name = booking.get('staff_name', '')
                        st.markdown(f'<div style="background:#E8F5E9;padding:0.75rem;margin:0.5rem 0;border-radius:8px;border-left:4px solid #1A7A6E;"><div style="font-weight:700;color:#1A7A6E;font-size:0.9rem;">🕐 {time_slot}</div><div style="font-size:0.85rem;color:#2d6b1a;margin-top:0.2rem;">{staff_name}</div></div>', unsafe_allow_html=True)
                    st.markdown('<div style="margin-top:0.75rem;font-size:0.75rem;color:#6b7280;">📌 <a href="/NIT_Bookings" target="_self" style="color:#1A7A6E;text-decoration:none;font-weight:600;">Manage NIT Bookings \u2192</a></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📅</div>No NIT bookings today</div>', unsafe_allow_html=True)
                    st.markdown('<div style="margin-top:0.5rem;font-size:0.75rem;color:#6b7280;">📌 <a href="/NIT_Bookings" target="_self" style="color:#1A7A6E;text-decoration:none;font-weight:600;">Book NIT Time \u2192</a></div>', unsafe_allow_html=True)

        with room_col:
            with card("meeting_room_bookings", "navy", "🗓️", "Meeting Room Bookings"):
                room_bookings = load_todays_meeting_room_bookings(current_date)
                if room_bookings:
                    for booking in room_bookings:
                        time_slot = booking.get('time_slot', '')
                        booked_by = booking.get('staff_name', '')
                        purpose = booking.get('purpose', '')
                        purpose_html = f'<div style="font-size:0.75rem;color:#6b7280;margin-top:0.1rem;">{purpose}</div>' if purpose else ""
                        st.markdown(f'<div style="background:#eef2f7;padding:0.75rem;margin:0.5rem 0;border-radius:8px;border-left:4px solid #1a2e44;"><div style="font-weight:700;color:#1a2e44;font-size:0.9rem;">🕐 {time_slot}</div><div style="font-size:0.85rem;color:#374151;margin-top:0.2rem;">{booked_by}</div>{purpose_html}</div>', unsafe_allow_html=True)
                    st.markdown('<div style="margin-top:0.75rem;font-size:0.75rem;color:#6b7280;">📌 <a href="/meeting_room_bookings" target="_self" style="color:#1a2e44;text-decoration:none;font-weight:600;">Manage Meeting Room \u2192</a></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">🗓️</div>No meeting room bookings today</div>', unsafe_allow_html=True)
                    st.markdown('<div style="margin-top:0.5rem;font-size:0.75rem;color:#6b7280;">📌 <a href="/meeting_room_bookings" target="_self" style="color:#1a2e44;text-decoration:none;font-weight:600;">Book Meeting Room \u2192</a></div>', unsafe_allow_html=True)

    section_divider("sec-program", 4, "\U0001f4ca", "Program Changes")
    if True:
        st.markdown(
            '<div style="background:#fff8f0;border:1.5px solid #e8c090;border-radius:10px;'
            'padding:.75rem 1rem;margin-bottom:.75rem;">'
            '<div style="font-size:.9rem;font-weight:700;color:#1a2e44;margin-bottom:.15rem;">'
            '\U0001f4cb Staff Timetable Changes '
            '<span style="font-size:.72rem;font-weight:400;color:#7a907a;">'
            '(from Program Changes Manager)</span></div>'
            '<div style="font-size:.78rem;color:#7a907a;">Managed via the '
            '<strong>Program Changes Manager</strong> tool — changes appear here automatically, '
            'from any device.</div>'
            '</div>',
            unsafe_allow_html=True
        )
        _pcm_changes = _pcm_changes_today
        if not _pcm_changes:
            st.markdown(
                '<div style="text-align:center;padding:1.25rem;color:#9ab09a;font-size:.85rem;'
                'background:#f8fdf6;border-radius:10px;">'
                '\U0001f4ed No staff timetable changes entered via Program Changes Manager for this day.</div>',
                unsafe_allow_html=True
            )
            with st.expander("\U0001f4e5 Import changes (only needed if the database is unreachable)"):
                st.caption(
                    "This is a fallback for when the database can't be reached. Normally changes "
                    "appear here automatically with no action needed."
                )
                _pcm_upload = st.file_uploader("Upload Program Changes JSON", type=["json"], key="bulletin_pcm_import")
                if _pcm_upload is not None:
                    try:
                        _pcm_data = json.loads(_pcm_upload.read().decode())
                        if "program_changes" in _pcm_data:
                            st.session_state["program_changes"] = _pcm_data["program_changes"]
                            if "staff_list" in _pcm_data:
                                st.session_state["staff_list"] = _pcm_data["staff_list"]
                        else:
                            st.session_state["program_changes"] = _pcm_data
                        st.success("\u2705 Imported!")
                        st.rerun()
                    except Exception:
                        st.error("Could not read that file - make sure it's a JSON export from Program Changes Manager.")
        else:
            st.markdown(
                f'<div style="font-size:.82rem;font-weight:600;color:#C8760A;margin-bottom:.5rem;">'
                f'\U0001f4cb {len(_pcm_changes)} timetable change{"s" if len(_pcm_changes)!=1 else ""} '
                f'for {current_date.strftime("%-d %B")}:</div>',
                unsafe_allow_html=True
            )
            for _pcm in _pcm_changes:
                _pcm_staff   = _pcm.get("staff_name","N/A")
                _pcm_reason  = _pcm.get("reason","")
                _pcm_covered = _pcm.get("covered_by","")
                _pcm_notes   = _pcm.get("notes","")
                _pcm_blocks  = _pcm.get("time_blocks",[]) or []
                _pcm_updated = " *(edited)*" if _pcm.get("updated_at") else ""
                st.markdown(
                    f'<div style="background:white;border:1.5px solid #e8d0b0;border-left:5px solid #C8760A;'
                    f'border-radius:10px;padding:.85rem 1rem;margin-bottom:.6rem;">'
                    f'<div style="font-size:.95rem;font-weight:700;color:#1a2e44;">{_pcm_staff}{_pcm_updated}</div>'
                    f'<div style="font-size:.82rem;color:#7a907a;margin:.2rem 0 .4rem;">{_pcm_reason}</div>'
                    + (f'<div style="font-size:.78rem;color:#1A7A6E;font-weight:600;margin-bottom:.35rem;">Covered by: {_pcm_covered}</div>' if _pcm_covered else "")
                    + (f'<div style="font-size:.75rem;color:#888;font-style:italic;margin-bottom:.35rem;">{_pcm_notes}</div>' if _pcm_notes else "")
                    + "</div>",
                    unsafe_allow_html=True
                )
                for _b in _pcm_blocks:
                    _bstart = _fmt_pc_time(_b.get("start_time",""))
                    _bend   = _fmt_pc_time(_b.get("end_time",""))
                    _bprog  = _b.get("modified_program","N/A")
                    _brb    = _b.get("released_by","")
                    _rb_txt = f" *(Release: {_brb})*" if _brb else ""
                    st.markdown(f"&nbsp;&nbsp;&nbsp;- **{_bstart} → {_bend}**: {_bprog}{_rb_txt}")
            st.caption("\U0001f4a1 To edit or remove an entry, use the Program Changes Manager tool directly.")

    if edit:
        st.markdown('<div style="background:white;border-top:2px solid #e8f0e3;padding:1rem 2rem;position:sticky;bottom:0;z-index:100;display:flex;gap:1rem;align-items:center;">', unsafe_allow_html=True)
        bsv1, bsv2, bsv3 = st.columns([2,2,6])
        with bsv1:
            if st.button("\U0001f4be Save Bulletin", type="primary", use_container_width=True, key="bottom_save"): st.session_state["_pending_save"] = True
        with bsv2:
            if st.button("\U0001f6aa Discard & Exit", type="secondary", use_container_width=True, key="bottom_discard"): st.session_state.edit_mode = False; st.rerun()
        with bsv3: st.markdown('<span style="font-size:.78rem;color:#9ab09a;">\U0001f4a1 Changes are saved to the database and appear on the staff room display immediately.</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("_pending_save"):
        st.session_state["_pending_save"] = False
        import math as _math
        def _sane(o):
            if isinstance(o, dict): return {k2: _sane(v2) for k2, v2 in o.items()}
            if isinstance(o, list): return [_sane(i) for i in o]
            if isinstance(o, float) and _math.isnan(o): return ""
            return o
        save_data = _sane({k: v for k, v in bulletin_data.items() if k != "id"})
        try:
            db.save_bulletin(current_date, save_data)
            st.session_state.edit_mode = False
            st.session_state["_save_ok"] = True
            if st.query_params.get("from_display") == "true":
                st.markdown('<meta http-equiv="refresh" content="2;url=/Daily_Bulletin?display=true">', unsafe_allow_html=True); st.info("\u21a9\ufe0f Returning to staff room display in 2 seconds...")
            st.rerun()
        except Exception as _save_err:
            st.error(f"\u26a0\ufe0f Bulletin could not be saved \u2014 {_save_err}")


with quickadd_tab:
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;color:white;"><div style="font-size:1.3rem;font-weight:700;margin-bottom:.3rem;">\U0001f4dd Add a Staff Notice</div><div style="font-size:.85rem;opacity:.85;">No password needed. Your notice will appear on today's bulletin and the staff room display straight away.</div></div>""", unsafe_allow_html=True)
    qa_col, preview_col = st.columns(2)
    with qa_col:
        with st.form("quick_add_form", clear_on_submit=True):
            qa_name = st.text_input("Your name *", placeholder="e.g. Sarah"); qa_cat = st.selectbox("Category *", list(NOTICE_CATS.keys()))
            qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3"); qa_body = st.text_area("Details", height=120); qa_date = st.date_input("For which day?", value=date.today())
            if st.form_submit_button("\U0001f4e2 Post Notice", type="primary", use_container_width=True):
                if not qa_name.strip(): st.warning("Please enter your name.")
                elif not qa_title.strip(): st.warning("Please enter a title.")
                else: save_notice({"submitted_by":qa_name.strip(),"category":qa_cat,"title":qa_title.strip(),"body":qa_body.strip(),"notice_date":str(qa_date)}); st.success(f"\u2705 Notice posted for {qa_date.strftime('%-d %B')}!"); st.balloons()
    with preview_col:
        st.markdown("**Category guide:**")
        for cat, cfg in NOTICE_CATS.items(): st.markdown(f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;"><span style="background:{cfg["bg"]};color:{cfg["color"]};font-size:.72rem;font-weight:700;padding:.2rem .6rem;border-radius:20px;min-width:90px;text-align:center;">{cfg["emoji"]} {cat}</span></div>', unsafe_allow_html=True)
    st.markdown("---"); st.markdown(f"**Notices posted for {date.today().strftime('%A %-d %B')}:**")
    listed = load_notices(for_date=date.today())
    if not listed: st.markdown('<div style="text-align:center;padding:2rem;color:#9ab09a;font-size:.85rem;">No notices yet today \u2014 be the first!</div>', unsafe_allow_html=True)
    else:
        for n in listed:
            cat = n.get("category","General"); nc = NOTICE_CATS.get(cat, NOTICE_CATS["General"]); nid = n.get("id","")
            nl1, nl2 = st.columns([9,1])
            with nl1: st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {nc["color"]};padding:.75rem 1rem;margin-bottom:.5rem;"><span style="background:{nc["bg"]};color:{nc["color"]};font-size:.65rem;font-weight:700;text-transform:uppercase;padding:.15rem .5rem;border-radius:20px;">{nc["emoji"]} {cat}</span><span style="font-size:.7rem;color:#9ab09a;margin-left:.5rem;">from {n.get("submitted_by","")}</span><div style="font-size:.9rem;font-weight:700;color:#1a2e44;margin:.3rem 0 .2rem;">{n.get("title","")}</div><div style="font-size:.82rem;color:#3a4a3a;line-height:1.5;">{n.get("body","") or ""}</div></div>', unsafe_allow_html=True)
            with nl2:
                st.write("")
                if st.session_state.authenticated:
                    if st.button("\U0001f5d1\ufe0f", key=f"qa_del_{nid}"): delete_notice(nid); st.rerun()


with archive_tab:
    st.markdown("### \U0001f5c2\ufe0f Bulletin Archive")
    a1, a2 = st.tabs(["Browse by Week / Term","Search"])
    with a1:
        c1, c2 = st.columns(2)
        with c1: browse_date = st.date_input("Select a date", value=date.today(), key="archive_date")
        with c2: browse_mode = st.selectbox("Browse by", ["Week","Term"])
        y = browse_date.year; terms_map = {1:(date(y,1,28),date(y,4,11)),2:(date(y,4,28),date(y,7,4)),3:(date(y,7,21),date(y,9,26)),4:(date(y,10,13),date(y,12,12))}
        if browse_mode == "Week":
            wk = week_dates(browse_date); results = db.get_bulletins_range(wk[0], wk[-1]); st.markdown(f"**Week of {wk[0].strftime('%-d %b %Y')}**")
        else:
            t_start = t_end = None
            for t,(s,e) in terms_map.items():
                if s <= browse_date <= e: t_start, t_end = s, e; st.markdown(f"**Term {t}, {y}**"); break
            results = db.get_bulletins_range(t_start, t_end) if t_start else []
            if not t_start: st.info("Date is outside term dates.")
        if results:
            for row in results:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                st.markdown(f'<div class="arch-card"><div class="arch-card-date">{d.strftime("%A %-d %B %Y")}</div><div class="arch-card-fact">\U0001f4a1 {row.get("fun_fact","") or "No fun fact recorded"}</div></div>', unsafe_allow_html=True)
                if st.button(f"Open \u2192", key=f"arch_{row['date']}"): st.session_state.selected_date = d; st.rerun()
        else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ed</div>No bulletins found for this period</div>', unsafe_allow_html=True)
    with a2:
        keyword = st.text_input("\U0001f50d Search all bulletins", placeholder="Enter staff name, student, excursion, note...")
        if keyword and len(keyword) >= 2:
            results = db.search_bulletins(keyword)
            if results:
                st.markdown(f"**{len(results)} result(s) found for '{keyword}'**")
                for row in results:
                    d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    st.markdown(f'<div class="arch-card"><div class="arch-card-date">{d.strftime("%A %-d %B %Y")}</div></div>', unsafe_allow_html=True)
                    if st.button(f"Open \u2192", key=f"search_{row['date']}"): st.session_state.selected_date = d; st.rerun()
            else: st.markdown(f'<div class="empty-state"><div class="icon">\U0001f50d</div>No results for "{keyword}"</div>', unsafe_allow_html=True)


with login_tab:
    if st.session_state.authenticated:
        st.success("\u2705 You are logged in as Staff")
        st.markdown("You can now edit bulletins \u2014 head to the **\U0001f4cb Bulletin** tab and click **\u270f\ufe0f Edit**.")
        if st.button("\U0001f6aa Logout", type="secondary"): st.session_state.authenticated = False; st.session_state.edit_mode = False; st.rerun()
    else:
        st.markdown('<div class="auth-gate"><h2>\U0001f510 Staff Login</h2><p>Login to create and edit daily bulletins.</p>', unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", placeholder="Enter staff password")
        if st.button("Login", type="primary", use_container_width=True):
            if pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.success("\u2705 Logged in! Go to the Bulletin tab to start editing."); st.rerun()
            else: st.error("Incorrect password.")
        st.markdown('</div>', unsafe_allow_html=True)
