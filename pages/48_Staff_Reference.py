"""
46_Staff_Reference.py — CLC-LBU Staff Portal
=============================================
Staff Reference — policies & expectations, live from Supabase.

STAFF VIEW (default): pick a document, expand sections to read,
download the full branded Word document to print. View-only.

ADMIN (password gated): edit section content/titles, reorder,
add/remove sections, add documents, publish/unpublish, and a
one-click seeder that loads the CLC 2026.8 Daily Work
Expectations starter content.

-------------------------------------------------------------------
SUPABASE SETUP — run once in the SQL editor:

create table if not exists reference_documents (
    id bigint generated always as identity primary key,
    slug text unique not null,
    doc_code text default '',
    title text not null,
    subtitle text default '',
    intro text default '',
    sort_order int default 0,
    is_published boolean default true,
    updated_at timestamptz default now()
);

create table if not exists reference_sections (
    id bigint generated always as identity primary key,
    document_id bigint references reference_documents(id) on delete cascade,
    title text not null,
    content text default '',
    sort_order int default 0,
    updated_at timestamptz default now()
);

alter table reference_documents enable row level security;
alter table reference_sections enable row level security;
create policy "ref_docs_all" on reference_documents for all using (true) with check (true);
create policy "ref_secs_all" on reference_sections for all using (true) with check (true);
-------------------------------------------------------------------
Dependencies: streamlit, supabase, python-docx (all already used by
other portal tools).
"""

import io
import re
from datetime import datetime, timezone, timedelta

import streamlit as st
from supabase import create_client

# ------------------------------------------------------------------
# Page config + CLC styling
# ------------------------------------------------------------------
st.set_page_config(page_title="Staff Reference", page_icon="📖", layout="wide")

TEAL = "#00695C"
TEAL_DARK = "#004D40"
TEAL_LIGHT = "#E0F2F1"

st.markdown(
    f"""
    <style>
    .ref-header {{
        background: linear-gradient(120deg, {TEAL_DARK}, {TEAL});
        color: white; padding: 1.2rem 1.5rem; border-radius: 12px;
        margin-bottom: 1rem;
    }}
    .ref-header h1 {{ color: white; font-size: 1.6rem; margin: 0; }}
    .ref-header p {{ color: {TEAL_LIGHT}; margin: 0.3rem 0 0 0; font-size: 0.95rem; }}
    .ref-intro {{
        background: {TEAL_LIGHT}; border-left: 6px solid {TEAL};
        padding: 0.8rem 1rem; border-radius: 6px; margin-bottom: 1rem;
        color: #1a1a1a;
    }}
    div[data-testid="stExpander"] details summary p {{
        font-weight: 700; color: {TEAL_DARK}; font-size: 1.02rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Supabase connection (tolerant of the two secret layouts used
# across the portal)
# ------------------------------------------------------------------
def _get_supabase():
    url = key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass
    if not url:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("anon_key")
        except Exception:
            pass
    if not url or not key:
        st.error("Supabase credentials not found in secrets. Add SUPABASE_URL and SUPABASE_KEY.")
        st.stop()
    return create_client(url, key)


sb = _get_supabase()

# ------------------------------------------------------------------
# Admin gate.
# Uses the shared confidential password. If your confidential_auth
# module exposes a check function, swap the marked block for it —
# otherwise this reads the same secret directly.
# ------------------------------------------------------------------
def admin_unlocked() -> bool:
    if st.session_state.get("ref_admin_ok"):
        return True
    pw = None
    for k in ("CONFIDENTIAL_PASSWORD", "confidential_password", "ADMIN_PASSWORD"):
        try:
            pw = st.secrets.get(k)
        except Exception:
            pw = None
        if pw:
            break
    if not pw:
        st.warning("No admin password configured in secrets (CONFIDENTIAL_PASSWORD).")
        return False
    entered = st.text_input("Admin password", type="password", key="ref_admin_pw")
    if entered:
        if entered == pw:
            st.session_state["ref_admin_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ------------------------------------------------------------------
# Data access
# ------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_documents(include_unpublished: bool = False):
    q = sb.table("reference_documents").select("*").order("sort_order").order("id")
    res = q.execute()
    docs = res.data or []
    if not include_unpublished:
        docs = [d for d in docs if d.get("is_published")]
    return docs


@st.cache_data(ttl=60)
def fetch_sections(document_id: int):
    res = (
        sb.table("reference_sections")
        .select("*")
        .eq("document_id", document_id)
        .order("sort_order")
        .order("id")
        .execute()
    )
    return res.data or []


def clear_caches():
    fetch_documents.clear()
    fetch_sections.clear()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Markdown -> docx (minimal, matches the content conventions used
# in the seeded sections: '- ' bullets, '**bold**', '> ' callouts)
# ------------------------------------------------------------------
def build_docx(doc_row, sections) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    TEAL_RGB = RGBColor(0x00, 0x69, 0x5C)
    TEAL_DARK_RGB = RGBColor(0x00, 0x4D, 0x40)
    GREY = RGBColor(0x59, 0x59, 0x59)

    d = Document()
    for s in d.sections:
        s.top_margin = s.bottom_margin = Pt(36)
        s.left_margin = s.right_margin = Pt(45)

    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    def shade(par, hexcolor):
        pPr = par._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), hexcolor)
        pPr.append(shd)

    # Title block
    t1 = d.add_paragraph()
    r = t1.add_run("COWANDILLA LEARNING CENTRE  |  LEARNING & BEHAVIOUR UNIT")
    r.font.size = Pt(8); r.font.bold = True; r.font.color.rgb = RGBColor(0xE0, 0xF2, 0xF1)
    shade(t1, "00695C")
    t2 = d.add_paragraph()
    r = t2.add_run(f"{doc_row.get('doc_code','')}  {doc_row['title']}".strip())
    r.font.size = Pt(20); r.font.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    shade(t2, "00695C")
    if doc_row.get("subtitle"):
        t3 = d.add_paragraph()
        r = t3.add_run(doc_row["subtitle"])
        r.font.size = Pt(10); r.font.italic = True; r.font.color.rgb = RGBColor(0xE0, 0xF2, 0xF1)
        shade(t3, "00695C")
    d.add_paragraph()

    def add_runs(par, text):
        # split on **bold** markers
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if chunk == "":
                continue
            run = par.add_run(chunk)
            if i % 2 == 1:
                run.font.bold = True

    if doc_row.get("intro"):
        p = d.add_paragraph()
        add_runs(p, doc_row["intro"])
        shade(p, "E0F2F1")

    for sec in sections:
        h = d.add_paragraph()
        r = h.add_run(sec["title"])
        r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = TEAL_DARK_RGB
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        for raw in (sec.get("content") or "").splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            if line.startswith("- "):
                p = d.add_paragraph(style="List Bullet")
                add_runs(p, line[2:])
            elif line.startswith("> "):
                p = d.add_paragraph()
                add_runs(p, line[2:])
                shade(p, "E0F2F1")
            else:
                p = d.add_paragraph()
                add_runs(p, line)
            p.paragraph_format.space_after = Pt(3)

    acst = datetime.now(timezone(timedelta(hours=9, minutes=30)))
    f = d.add_paragraph()
    r = f.add_run(f"CLC-LBU  |  Downloaded from the Staff Portal {acst.strftime('%d/%m/%Y')} — the portal version is always current.")
    r.font.size = Pt(8); r.font.color.rgb = GREY

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------
# Seed content — CLC 2026.8 Daily Work Expectations (current as of
# 20 July 2026). Loaded via the admin "Seed" button when empty.
# ------------------------------------------------------------------
SEED_DOC = {
    "slug": "daily-work-expectations",
    "doc_code": "CLC 2026.8",
    "title": "Daily Work Expectations",
    "subtitle": "Norms for every working day at CLC",
    "intro": "**Staff Portal:** Daily processes run through the CLC-LBU Staff Portal — absence procedures, Staff Bulletin, CLC Calendar, NIT Bookings, Communication Log and hazard reporting. Bookmark it.",
    "sort_order": 1,
    "is_published": True,
}

SEED_SECTIONS = [
    ("Hours and start of day", """- Administration hours: **8:00am – 4:00pm**. Teaching staff are on site **8:30am – 3:30pm** and available via mobile until 4:00pm. Face-to-face teaching (9:00am – 3:00pm) excludes NIT and meal breaks.
- Program teachers exercise duty of care by supervising their students throughout face-to-face teaching time.
- Be prepared for the working day by 8:30am (SSOs by scheduled start time): **Staff Bulletin checked on the staff portal**, emails checked, phone calls made or returned."""),
    ("Absences and whereabouts", """- **Unplanned absence:** call or text the **Manager and Transition Coordinator by 6:30am**. Then follow the **Unplanned Absence procedure on the staff portal** — all steps, including recording the absence via EIK (edHR self-service).
- Maintain an **up-to-date TRT plan** (timetable, room access, program information) so your program can run in your absence.
- **Planned absence:** request leave in advance through your line manager — follow the **Planned Absence procedure on the staff portal** and complete the Planned Absence form (observe LSL and sick leave timeframes).
- **All staff sign in and out at Admin every day** — on arrival, on departure, and whenever leaving site during the day. This is an **expectation, not a negotiation**: it is how we account for everyone in an emergency.
- Seek Site Leader approval in advance to leave before 3:30pm.
- If absent for more than 2 days, set an automatic email reply directing stakeholders to CLC administration so enquiries can be managed during your leave."""),
    ("Equipment and breaks", """- Carry your keys/fobs at all times. Walkie-talkies charged and carried all day.
- Take a 30-minute meal break within the first 5 hours of the working day — timing depends on program needs and SSO cover, negotiated with your line manager if required.
- With **3 or fewer students** attending, lunch breaks in two-teacher programs can be **informally managed between the two teachers** — the same expectation as informal NIT arrangements. Any change to these arrangements is raised with leadership beforehand."""),
    ("End of day", """- Teachers remain on site until 3:30pm and are contactable on mobile until 4:00pm. Requests to leave earlier go to your line manager.
- All students require supervision while on the CLC site. Exercise duty of care **until students are picked up by carer or taxi (by 3:00pm)** — if you cannot, arrange other supervision through your line manager.
- Check emails before leaving from 3:30pm. Lock student laptops/iPads away securely. Program phone **locked away/stored in the agreed location** so it can be accessed if a staff member is away; phone messaging switched on after 3:30pm.
- Lock building entry/exit; turn off computers, screens and air conditioning."""),
    ("Site environment", """- Meeting/staff rooms locked after use and left clean and tidy; meeting rooms are booked by **entering the booking on the Daily Bulletin**; lights and air conditioning off.
- **All staff are allocated a week** to complete kitchen duties (roster displayed in kitchen).
- Every program has a welcome sign on the door; staff photos displayed near the front entrance for visitors.
- Security: individual alarm codes are issued; keys and personal items locked away at all times; front door locked at all times with the doorbell available for visitors.
- Report hazards and maintenance issues via the **Report a Hazard tile on the staff portal**."""),
    ("Communication and documentation", """**Two records, no exceptions:**
- **Every meeting** — including TAC, Transition and Review — whether held face-to-face, over the phone or via email → documented officially in the **student file**, accessible through the portal (where the case management checklist also sits). It is an expectation that **ALL meetings are uploaded**.
- **All other communication** with families, schools, SSS and agencies — calls, emails, texts, conversations → entered in the **Communication Log on the staff portal**.

This applies to every staff member and every contact, however brief. **If it isn't recorded, it didn't happen.**
> **Trial:** The Communication Log is being trialled as our system for day-to-day contact. Capture the contact at the time it happens — date, who, method, summary. Feedback on the trial goes to your line manager.
- Use the departmental signature block and corporate branding/writing style. LBU font is Calibri 11 for any documentation distributed to stakeholders.
- Letters to outside agencies/stakeholders are ratified and co-signed by the Site Leader on Learning Centre letterhead.
- Use the Transition Report template for Exit meetings: send electronically to the home-school Principal (cc your line manager), distribute hard copies at the Exit meeting, and save the report to the **student file**.
- Respond to stakeholder emails within **24–48 hours**.
- Program teachers can expect newly referred student information by 3:30pm Wednesdays."""),
    ("Attire and mobile phones", """- No thongs or backless/open-front shoes. Risk-assess jewellery, scarves and long hair worn down.
- **Site uniform:** to be worn when leaving the site — e.g. excursions and offsite meetings.
- Personal mobile phones are **not out at any time you are student-facing** — this includes, but is not limited to, face-to-face teaching (also yard duty, transitions and excursions). Phones stay out of sight; staff model the student ICT device policy.
- Program/site mobiles are used for parent and stakeholder contact where the landline is unavailable or inappropriate — charged and switched on for excursion days."""),
    ("Non-Instruction Time (NIT)", """- With **4 or more students** attending, the **formal NIT timetable** applies (see PAC-ratified NIT guidelines). View and book NIT via **NIT Bookings on the staff portal**.
- With **3 or fewer students** attending, **informal NIT arrangements** apply. This means the two teachers in a program **release each other** for their allocated NIT, and the NIT teacher may be deployed elsewhere — **at the discretion of leadership and according to site needs**.
- Any change to NIT or lunch break arrangements is raised with leadership **beforehand** — leadership makes the final decision.
- NIT is calculated per face-to-face teaching minutes and may alter with teacher–student contact time. Missed NIT is individually negotiated with line management within the PAC-approved timeframe.

**Booking times — additional NIT**
- Booking times are **additional NIT**. Meetings should be scheduled within your allocated NIT in the first instance — that is what NIT is for.
- Where a meeting time within your allocated NIT **cannot be agreed with the other attendees**, a Booking time supports attendance at the offsite or student meeting. In this case, **entering the meeting in NIT Bookings on the staff portal is required**.
- Booking times are **never used for personal appointments** — personal appointments are managed through the leave process.
- Booking times are not for make-up NIT, **unless agreed to by leadership beforehand** — this is the only exception."""),
    ("Staff meetings", """- Staff meetings start at **3:10pm Wednesdays**; attendance at all staff meetings is required, including signing in.
- The **Staff Bulletin is sent out COB Tuesday** with business and information that can be shared without needing face-to-face time — read it before Wednesday's meeting so meeting time stays focused.
- Participate — share data and teaching and learning strategies, and engage in the administration and training components.
- Arrange any site/student meetings outside of staff meeting time."""),
    ("Team meetings", """- Program teams meet **once a week**, following the alternating fortnightly structure: **Week A — student lens** (individual students, goals, data, interventions); **Week B — system lens** (curriculum and program improvement).
- All team meetings are **documented in minutes via the Team Meetings tool on the staff portal**, including agreements made and who is actioning them.
- Agreements made in team meetings **are actioned** — actions are reviewed at the following meeting before new business.
- If you do not attend a meeting, **follow up with the minutes and action any agreements** that involve you — absence doesn't pause your actions."""),
    ("Offsite meetings and travel", """- All site/student meeting times are communicated to site admin and entered in the **CLC Calendar on the staff portal**.
- Use the government vehicle in the first instance when travelling between programs or offsite (as negotiated with your line manager).
- Pre-approval is required when leaving the premises between 8:30am and 3:30pm; sign out at Admin on departure, sign in on return, and sign in when attending offsite meetings."""),
    ("Student attendance", """- Ring the student's caregiver **by 9:30am** when a student is absent and record the reason on **EMS**. All absences must be investigated and explained.
- Attach student attendance data to the Transition Report at exit. **Attendance concerns are discussed with leadership** — refer to the Student Attendance Improvement Plan (induction folder) for managing ongoing non-attendance."""),
    ("Mail and first aid", """- Send information to carers via registered post only — liaise with site administration.
- Program teachers maintain first aid equipment and facilities daily, consulting the site's nominated First Aid staff on procedures and systems.
- Student medication is kept in a locked medication box (program teachers and administration both hold keys). Complete the medication log when administering medication at the CORRECT time.
- If medication is administered at a time that differs from the medication plan, complete a medication error log and inform the Site Manager and parent."""),
    ("Student file boxes", """- Program teachers can expect student file boxes **within 24 hours of the entry meeting** — or, if the student is starting the next day, **by the end of the entry-meeting day**."""),
]


def seed_daily_work_expectations():
    existing = sb.table("reference_documents").select("id").eq("slug", SEED_DOC["slug"]).execute().data
    if existing:
        return False, "Daily Work Expectations already exists — nothing seeded."
    doc = sb.table("reference_documents").insert(SEED_DOC).execute().data[0]
    rows = [
        {"document_id": doc["id"], "title": t, "content": c, "sort_order": i + 1}
        for i, (t, c) in enumerate(SEED_SECTIONS)
    ]
    sb.table("reference_sections").insert(rows).execute()
    clear_caches()
    return True, f"Seeded '{SEED_DOC['title']}' with {len(rows)} sections."


# ------------------------------------------------------------------
# STAFF VIEW
# ------------------------------------------------------------------
def staff_view():
    docs = fetch_documents()
    if not docs:
        st.info("No documents published yet. An administrator can seed or add documents in the Admin tab.")
        return

    if len(docs) == 1:
        doc = docs[0]
    else:
        labels = {f"{d.get('doc_code','')} {d['title']}".strip(): d for d in docs}
        pick = st.selectbox("Document", list(labels.keys()))
        doc = labels[pick]

    st.markdown(
        f"""<div class="ref-header">
        <h1>{doc.get('doc_code','')}&nbsp; {doc['title']}</h1>
        <p>{doc.get('subtitle','')}</p></div>""",
        unsafe_allow_html=True,
    )

    sections = fetch_sections(doc["id"])

    col1, col2 = st.columns([3, 1])
    with col2:
        if sections:
            st.download_button(
                "⬇️ Download full document (Word)",
                data=build_docx(doc, sections),
                file_name=f"{(doc.get('doc_code','') + '_' + doc['title']).strip('_').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    with col1:
        if doc.get("intro"):
            st.markdown(f"<div class='ref-intro'>{re.sub(r'\\*\\*(.+?)\\*\\*', r'<b>\\1</b>', doc['intro'])}</div>", unsafe_allow_html=True)

    if not sections:
        st.info("This document has no sections yet.")
        return

    expand_all = st.toggle("Expand all sections", value=False)
    for sec in sections:
        with st.expander(sec["title"], expanded=expand_all):
            st.markdown(sec.get("content") or "_(empty)_")

    upd = doc.get("updated_at", "")
    if upd:
        st.caption(f"Portal version is the current version. Last updated: {upd[:10]}")


# ------------------------------------------------------------------
# ADMIN VIEW
# ------------------------------------------------------------------
def admin_view():
    if not admin_unlocked():
        return

    st.success("Admin unlocked — changes save straight to the portal for all staff.")

    docs = fetch_documents(include_unpublished=True)

    with st.expander("➕ Add a new document / seed starter content"):
        c1, c2 = st.columns(2)
        with c1:
            new_code = st.text_input("Doc code (e.g. CLC 2026.8)", key="nd_code")
            new_title = st.text_input("Title", key="nd_title")
            new_sub = st.text_input("Subtitle", key="nd_sub")
            if st.button("Create document"):
                if new_title.strip():
                    slug = re.sub(r"[^a-z0-9]+", "-", new_title.lower()).strip("-")
                    sb.table("reference_documents").insert(
                        {"slug": slug, "doc_code": new_code, "title": new_title.strip(),
                         "subtitle": new_sub, "sort_order": len(docs) + 1, "is_published": False}
                    ).execute()
                    clear_caches(); st.rerun()
                else:
                    st.error("Title required.")
        with c2:
            st.markdown("**Starter content**")
            if st.button("Seed: Daily Work Expectations (CLC 2026.8)"):
                ok, msg = seed_daily_work_expectations()
                (st.success if ok else st.info)(msg)
                if ok:
                    st.rerun()

    if not docs:
        return

    labels = {f"{d.get('doc_code','')} {d['title']}".strip() + ("" if d.get("is_published") else "  (unpublished)"): d for d in docs}
    pick = st.selectbox("Edit document", list(labels.keys()), key="adm_doc")
    doc = labels[pick]

    with st.expander("Document settings", expanded=False):
        d_code = st.text_input("Doc code", value=doc.get("doc_code", ""), key=f"dc_{doc['id']}")
        d_title = st.text_input("Title", value=doc["title"], key=f"dt_{doc['id']}")
        d_sub = st.text_input("Subtitle", value=doc.get("subtitle", ""), key=f"ds_{doc['id']}")
        d_intro = st.text_area("Intro / highlighted note (optional, **bold** supported)", value=doc.get("intro", ""), key=f"di_{doc['id']}")
        d_pub = st.checkbox("Published (visible to staff)", value=bool(doc.get("is_published")), key=f"dp_{doc['id']}")
        cA, cB = st.columns(2)
        with cA:
            if st.button("Save document settings", key=f"dsave_{doc['id']}"):
                sb.table("reference_documents").update(
                    {"doc_code": d_code, "title": d_title, "subtitle": d_sub,
                     "intro": d_intro, "is_published": d_pub, "updated_at": _now()}
                ).eq("id", doc["id"]).execute()
                clear_caches(); st.success("Saved."); st.rerun()
        with cB:
            if st.button("🗑️ Delete this document (and all its sections)", key=f"ddel_{doc['id']}"):
                sb.table("reference_documents").delete().eq("id", doc["id"]).execute()
                clear_caches(); st.rerun()

    st.markdown("### Sections")
    sections = fetch_sections(doc["id"])

    for idx, sec in enumerate(sections):
        with st.expander(f"{idx+1}. {sec['title']}"):
            s_title = st.text_input("Section title", value=sec["title"], key=f"st_{sec['id']}")
            s_content = st.text_area(
                "Content — '- ' for bullets, **bold**, '> ' for a highlighted note",
                value=sec.get("content", ""), height=260, key=f"sc_{sec['id']}",
            )
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("💾 Save", key=f"ss_{sec['id']}"):
                    sb.table("reference_sections").update(
                        {"title": s_title, "content": s_content, "updated_at": _now()}
                    ).eq("id", sec["id"]).execute()
                    sb.table("reference_documents").update({"updated_at": _now()}).eq("id", doc["id"]).execute()
                    clear_caches(); st.success("Saved."); st.rerun()
            with c2:
                if idx > 0 and st.button("⬆️ Move up", key=f"su_{sec['id']}"):
                    above = sections[idx - 1]
                    sb.table("reference_sections").update({"sort_order": above["sort_order"]}).eq("id", sec["id"]).execute()
                    sb.table("reference_sections").update({"sort_order": sec["sort_order"]}).eq("id", above["id"]).execute()
                    clear_caches(); st.rerun()
            with c3:
                if idx < len(sections) - 1 and st.button("⬇️ Move down", key=f"sd_{sec['id']}"):
                    below = sections[idx + 1]
                    sb.table("reference_sections").update({"sort_order": below["sort_order"]}).eq("id", sec["id"]).execute()
                    sb.table("reference_sections").update({"sort_order": sec["sort_order"]}).eq("id", below["id"]).execute()
                    clear_caches(); st.rerun()
            with c4:
                if st.button("🗑️ Delete", key=f"sx_{sec['id']}"):
                    sb.table("reference_sections").delete().eq("id", sec["id"]).execute()
                    clear_caches(); st.rerun()

    st.markdown("#### Add section")
    a_title = st.text_input("New section title", key="ns_title")
    a_content = st.text_area("New section content", key="ns_content", height=160)
    if st.button("Add section"):
        if a_title.strip():
            sb.table("reference_sections").insert(
                {"document_id": doc["id"], "title": a_title.strip(), "content": a_content,
                 "sort_order": (sections[-1]["sort_order"] + 1) if sections else 1}
            ).execute()
            clear_caches(); st.rerun()
        else:
            st.error("Section title required.")


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------
st.title("📖 Staff Reference")
st.caption("Policies and expectations — live, current, and downloadable. The portal version is always the current version.")

tab_staff, tab_admin = st.tabs(["📚 View documents", "🔐 Admin"])
with tab_staff:
    staff_view()
with tab_admin:
    admin_view()
