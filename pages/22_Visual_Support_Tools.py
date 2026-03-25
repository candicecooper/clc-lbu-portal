# ════════════════════════════════════════════════════════════════════════════
# Social_Story_Builder.py  ·  CLC-LBU Portal
# Build, save, personalise and display visual support tools for students
# ════════════════════════════════════════════════════════════════════════════

import streamlit as st
import json
from datetime import datetime
from supabase import create_client

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Visual Support Tools · CLC",
    page_icon="🖼️",
    layout="wide",
)

# ── Brand colours ─────────────────────────────────────────────────────────────
TEAL  = "#1A6B8A"
AMBER = "#D4860A"
NAVY  = "#1a2e44"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}

/* Header */
.ssb-header {{
    background: linear-gradient(135deg, {TEAL} 0%, #1a4d6b 100%);
    color: white; padding: 1.1rem 1.6rem;
    border-radius: 12px; margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 1rem;
}}
.ssb-header .icon {{ font-size: 2rem; }}
.ssb-header h1 {{ margin: 0; font-size: 1.45rem; font-weight: 700; }}
.ssb-header p  {{ margin: .15rem 0 0; opacity: .85; font-size: .82rem; }}

/* Story cards in library */
.story-card {{
    background: white; border-radius: 10px;
    border: 1px solid #e2e8f0;
    padding: .85rem 1rem; margin-bottom: .6rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    transition: box-shadow .2s;
}}
.story-card:hover {{ box-shadow: 0 3px 10px rgba(0,0,0,.12); }}
.story-card .sc-title {{ font-weight: 700; color:{NAVY}; font-size: .95rem; }}
.story-card .sc-meta  {{ font-size: .75rem; color: #6b7a8d; margin-top: .2rem; }}
.story-card .sc-tags  {{ margin-top: .35rem; }}
.tag {{
    display: inline-block; background: #EBF4F9; color: {TEAL};
    border-radius: 20px; padding: .1rem .55rem;
    font-size: .72rem; font-weight: 600; margin-right: .3rem;
}}
.tag-template {{ background: #FEF3E2; color: {AMBER}; }}

/* Page editor */
.page-box {{
    background: white; border: 2px solid #e2e8f0;
    border-radius: 10px; padding: .75rem 1rem; margin-bottom: .5rem;
}}
.page-num {{
    font-size: .72rem; font-weight: 700; color: {TEAL};
    text-transform: uppercase; letter-spacing: .05em;
}}

/* Student book display */
.book-page {{
    background: white;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,.12);
    min-height: 320px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 2.5rem 3rem;
    text-align: center;
    margin: 1rem auto; max-width: 680px;
}}
.book-page .bp-text {{
    font-size: 1.45rem; font-weight: 600; color: {NAVY};
    line-height: 1.6; margin-bottom: 1.5rem;
}}
.book-nav {{
    display: flex; gap: 1rem; justify-content: center;
    margin-top: 1rem;
}}
.progress-dots {{
    display: flex; gap: .4rem; justify-content: center; margin-top: .75rem;
}}
.dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: #cbd5e0; display: inline-block;
}}
.dot-active {{ background: {TEAL}; }}

/* AI panel */
.ai-box {{
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 1px solid #bae6fd; border-radius: 10px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
}}
.ai-box h4 {{ margin: 0 0 .5rem; color: #0369a1; font-size: .9rem; }}

/* Info chips */
.chip {{
    display: inline-block; padding: .25rem .7rem;
    border-radius: 20px; font-size: .75rem; font-weight: 600;
    margin-right: .3rem;
}}
.chip-teal {{ background: #E0F4F8; color: {TEAL}; }}
.chip-amber {{ background: #FEF3E2; color: {AMBER}; }}
</style>
""", unsafe_allow_html=True)

# ── Supabase ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

sb = get_supabase()

# ── Groq AI helper ────────────────────────────────────────────────────────────
def generate_story_with_groq(prompt: str) -> list[dict]:
    """Call Groq to generate story pages. Returns list of {page_number, text}."""
    try:
        from groq import Groq
        client = Groq(api_key=st.secrets["groq"]["api_key"])
        system = (
            "You are a specialist in creating social stories for students with diverse needs. "
            "Social stories are short, clear, positive, first-person narratives that help students "
            "understand social situations and expected behaviours. "
            "Follow the Carol Gray Social Stories™ framework: descriptive, perspective, directive, and "
            "affirmative sentences. Use simple, concrete language. "
            "Respond ONLY with a JSON array — no markdown, no preamble. "
            "Format: [{\"page_number\": 1, \"text\": \"...\"}, ...] "
            "Create 5-8 pages. Each page should be 1-3 short sentences. "
            "Start with the context, build understanding, then end positively."
        )
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.6,
            max_tokens=1200,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        pages = json.loads(raw)
        return pages
    except Exception as e:
        st.error(f"AI generation error: {e}")
        return []

# ── Supabase DB helpers ───────────────────────────────────────────────────────
def load_stories(template_only=False) -> list[dict]:
    try:
        q = sb.table("social_stories").select("*").order("created_at", desc=True)
        if template_only:
            q = q.eq("is_template", True)
        return q.execute().data or []
    except Exception as e:
        st.error(f"Could not load stories: {e}")
        return []

def load_pages(story_id: str) -> list[dict]:
    try:
        return (
            sb.table("social_story_pages")
            .select("*")
            .eq("story_id", story_id)
            .order("page_number")
            .execute()
            .data or []
        )
    except Exception as e:
        st.error(f"Could not load pages: {e}")
        return []

def save_story(title: str, student_name: str, tags: list[str],
               is_template: bool, created_by: str) -> str | None:
    """Insert story header, return new id."""
    try:
        res = sb.table("social_stories").insert({
            "title": title,
            "student_name": student_name or "",
            "tags": tags,
            "is_template": is_template,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        st.error(f"Save error: {e}")
        return None

def save_pages(story_id: str, pages: list[dict]):
    """Bulk-insert pages."""
    try:
        rows = [
            {
                "story_id": story_id,
                "page_number": p["page_number"],
                "text": p["text"],
            }
            for p in pages
        ]
        sb.table("social_story_pages").insert(rows).execute()
    except Exception as e:
        st.error(f"Page save error: {e}")

def update_story_pages(story_id: str, pages: list[dict]):
    """Delete existing pages and re-insert."""
    try:
        sb.table("social_story_pages").delete().eq("story_id", story_id).execute()
        save_pages(story_id, pages)
        sb.table("social_stories").update({
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", story_id).execute()
    except Exception as e:
        st.error(f"Update error: {e}")

def delete_story(story_id: str):
    try:
        sb.table("social_story_pages").delete().eq("story_id", story_id).execute()
        sb.table("social_stories").delete().eq("id", story_id).execute()
    except Exception as e:
        st.error(f"Delete error: {e}")

def toggle_template(story_id: str, value: bool):
    try:
        sb.table("social_stories").update({"is_template": value}).eq("id", story_id).execute()
    except Exception as e:
        st.error(f"Toggle error: {e}")

# ── Session state defaults ────────────────────────────────────────────────────
for k, v in {
    "ssb_mode": "library",          # library | create | edit | display
    "ssb_pages": [],                 # [{page_number, text}]
    "ssb_story_id": None,
    "ssb_story_meta": {},
    "ssb_book_page": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ssb-header">
  <div class="icon">📖</div>
  <div>
    <h1>Visual Support Tools</h1>
    <p>Create, save, personalise and display visual support materials for students</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Top navigation ────────────────────────────────────────────────────────────
col_nav1, col_nav2, col_nav3 = st.columns(3)
with col_nav1:
    if st.button("📚  Story Library", use_container_width=True,
                 type="primary" if st.session_state.ssb_mode == "library" else "secondary"):
        st.session_state.ssb_mode = "library"
        st.rerun()
with col_nav2:
    if st.button("✏️  Create New Story", use_container_width=True,
                 type="primary" if st.session_state.ssb_mode == "create" else "secondary"):
        st.session_state.ssb_mode = "create"
        st.session_state.ssb_pages = []
        st.session_state.ssb_story_id = None
        st.session_state.ssb_story_meta = {}
        st.rerun()
with col_nav3:
    if st.button("📺  Student Display Mode", use_container_width=True,
                 type="primary" if st.session_state.ssb_mode == "display" else "secondary"):
        if not st.session_state.ssb_pages:
            st.warning("Load or create a story first, then switch to display mode.")
        else:
            st.session_state.ssb_mode = "display"
            st.session_state.ssb_book_page = 0
            st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# MODE: LIBRARY
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.ssb_mode == "library":
    col_l, col_r = st.columns([3, 1])
    with col_l:
        search = st.text_input("🔍 Search stories", placeholder="Title, student name or tag…")
    with col_r:
        show_templates = st.checkbox("Templates only", value=False)

    stories = load_stories(template_only=show_templates)

    # Filter by search
    if search:
        q = search.lower()
        stories = [
            s for s in stories
            if q in s.get("title", "").lower()
            or q in s.get("student_name", "").lower()
            or any(q in t.lower() for t in (s.get("tags") or []))
        ]

    if not stories:
        st.info("No stories found. Create one using **Create New Story** above.")
    else:
        st.markdown(f"**{len(stories)} stor{'y' if len(stories)==1 else 'ies'} found**")
        for story in stories:
            with st.container():
                c1, c2 = st.columns([5, 1])
                with c1:
                    tags_html = ""
                    for t in (story.get("tags") or []):
                        tags_html += f'<span class="tag">{t}</span>'
                    if story.get("is_template"):
                        tags_html += '<span class="tag tag-template">⭐ Template</span>'
                    student = story.get("student_name") or "General"
                    created = story.get("created_at", "")[:10]
                    author = story.get("created_by", "")
                    st.markdown(f"""
                    <div class="story-card">
                      <div class="sc-title">{story['title']}</div>
                      <div class="sc-meta">👤 {student} &nbsp;·&nbsp; 📅 {created} &nbsp;·&nbsp; ✍️ {author}</div>
                      <div class="sc-tags" style="margin-top:.35rem">{tags_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
                    if st.button("Load & Edit", key=f"load_{story['id']}", use_container_width=True):
                        pages = load_pages(story["id"])
                        st.session_state.ssb_pages = [{"page_number": p["page_number"], "text": p["text"]} for p in pages]
                        st.session_state.ssb_story_id = story["id"]
                        st.session_state.ssb_story_meta = story
                        st.session_state.ssb_mode = "edit"
                        st.rerun()
                    if st.button("▶ Display", key=f"disp_{story['id']}", use_container_width=True):
                        pages = load_pages(story["id"])
                        st.session_state.ssb_pages = [{"page_number": p["page_number"], "text": p["text"]} for p in pages]
                        st.session_state.ssb_story_id = story["id"]
                        st.session_state.ssb_story_meta = story
                        st.session_state.ssb_mode = "display"
                        st.session_state.ssb_book_page = 0
                        st.rerun()
                    tmpl_label = "★ Unmark Template" if story.get("is_template") else "☆ Mark Template"
                    if st.button(tmpl_label, key=f"tmpl_{story['id']}", use_container_width=True):
                        toggle_template(story["id"], not story.get("is_template"))
                        st.rerun()
                    if st.button("🗑 Delete", key=f"del_{story['id']}", use_container_width=True):
                        delete_story(story["id"])
                        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# MODE: CREATE
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.ssb_mode == "create":
    st.subheader("✏️ Create New Visual Support Material")

    # Story metadata
    with st.expander("📋 Material Details", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            story_title    = st.text_input("Title *", placeholder="e.g. Going to the Canteen")
            student_name   = st.text_input("Student name (optional)", placeholder="Leave blank for a general story")
        with c2:
            created_by     = st.text_input("Your name *", placeholder="e.g. J. Smith")
            tags_input     = st.text_input("Tags (comma separated)", placeholder="e.g. lunchtime, transitions, anxiety")
            is_template    = st.checkbox("Save as a template (reusable for other students)")

    # AI generator
    st.markdown("""<div class="ai-box">
    <h4>🤖 AI Content Generator</h4>
    <p style="font-size:.83rem;color:#0369a1;margin:0">
    Describe the situation and what you want the material to teach — the AI will draft the pages for you to review and edit.
    </p></div>""", unsafe_allow_html=True)

    ai_prompt = st.text_area(
        "Describe the situation",
        placeholder=(
            "e.g. Write a visual support story for a 10-year-old named Alex who gets anxious during "
            "unstructured lunch times. He finds the noise overwhelming and sometimes runs away. "
            "The story should help him understand what happens at lunch and give him strategies."
        ),
        height=120,
    )
    if st.button("🤖 Generate with AI", use_container_width=False):
        if not ai_prompt.strip():
            st.warning("Please describe the situation first.")
        else:
            with st.spinner("Generating story pages…"):
                pages = generate_story_with_groq(ai_prompt.strip())
            if pages:
                st.session_state.ssb_pages = pages
                st.success(f"Generated {len(pages)} pages! Review and edit below.")
            else:
                st.error("Generation failed — please try again or write pages manually.")

    # Manual / editable pages
    st.markdown("#### 📄 Pages")
    st.caption("Edit the AI-generated text, or add pages manually below.")

    new_pages = []
    for i, page in enumerate(st.session_state.ssb_pages):
        with st.container():
            st.markdown(f'<div class="page-num">Page {page["page_number"]}</div>', unsafe_allow_html=True)
            col_t, col_x = st.columns([10, 1])
            with col_t:
                txt = st.text_area(
                    f"Page {page['page_number']} text",
                    value=page["text"],
                    key=f"page_text_{i}",
                    label_visibility="collapsed",
                    height=80,
                )
            with col_x:
                st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_page_{i}"):
                    continue  # Skip this page (delete it)
            new_pages.append({"page_number": len(new_pages) + 1, "text": txt})

    st.session_state.ssb_pages = new_pages

    c_add, c_save = st.columns([1, 2])
    with c_add:
        if st.button("+ Add Page", use_container_width=True):
            next_num = len(st.session_state.ssb_pages) + 1
            st.session_state.ssb_pages.append({"page_number": next_num, "text": ""})
            st.rerun()
    with c_save:
        if st.button("💾 Save Story", type="primary", use_container_width=True):
            if not story_title.strip():
                st.error("Please enter a story title.")
            elif not created_by.strip():
                st.error("Please enter your name.")
            elif not st.session_state.ssb_pages:
                st.error("Please add at least one page.")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                story_id = save_story(
                    title=story_title.strip(),
                    student_name=student_name.strip(),
                    tags=tags,
                    is_template=is_template,
                    created_by=created_by.strip(),
                )
                if story_id:
                    save_pages(story_id, st.session_state.ssb_pages)
                    st.success("✅ Story saved to library!")
                    st.session_state.ssb_story_id = story_id
                    st.session_state.ssb_mode = "library"
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# MODE: EDIT  (loaded from library)
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.ssb_mode == "edit":
    meta = st.session_state.ssb_story_meta

    st.subheader(f"✏️ Editing: {meta.get('title', 'Story')}")
    student_chip = f'<span class="chip chip-teal">👤 {meta.get("student_name") or "General"}</span>'
    tmpl_chip    = '<span class="chip chip-amber">⭐ Template</span>' if meta.get("is_template") else ""
    st.markdown(f"{student_chip} {tmpl_chip}", unsafe_allow_html=True)
    st.markdown("")

    # AI personalise panel
    with st.expander("🤖 Personalise with AI"):
        st.markdown("""<div class="ai-box">
        <h4>🤖 AI Personalisation</h4>
        <p style="font-size:.83rem;color:#0369a1;margin:0">
        Describe changes you'd like — the AI will rewrite the pages based on your guidance while keeping the story structure.
        </p></div>""", unsafe_allow_html=True)
        personalise_prompt = st.text_area(
            "What would you like to change?",
            placeholder=(
                "e.g. Adapt this story for Maya, a 9-year-old girl who uses AAC. "
                "Simplify the language further and add a page about using her device to ask for help."
            ),
            height=100,
        )
        if st.button("🤖 Personalise with AI"):
            if personalise_prompt.strip():
                existing = "\n\n".join(
                    f"Page {p['page_number']}: {p['text']}"
                    for p in st.session_state.ssb_pages
                )
                full_prompt = (
                    f"Here is an existing visual support material:\n\n{existing}\n\n"
                    f"Please adapt it based on the following request:\n{personalise_prompt}"
                )
                with st.spinner("Personalising…"):
                    pages = generate_story_with_groq(full_prompt)
                if pages:
                    st.session_state.ssb_pages = pages
                    st.success("Story personalised! Review and save below.")
                    st.rerun()

    # Edit pages
    st.markdown("#### 📄 Pages")
    new_pages = []
    for i, page in enumerate(st.session_state.ssb_pages):
        st.markdown(f'<div class="page-num">Page {page["page_number"]}</div>', unsafe_allow_html=True)
        col_t, col_x = st.columns([10, 1])
        with col_t:
            txt = st.text_area(
                f"Page {page['page_number']}",
                value=page["text"],
                key=f"edit_page_{i}",
                label_visibility="collapsed",
                height=80,
            )
        with col_x:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"edit_del_{i}"):
                continue
        new_pages.append({"page_number": len(new_pages) + 1, "text": txt})

    st.session_state.ssb_pages = new_pages

    c_add, c_save, c_disp = st.columns(3)
    with c_add:
        if st.button("+ Add Page", use_container_width=True):
            next_num = len(st.session_state.ssb_pages) + 1
            st.session_state.ssb_pages.append({"page_number": next_num, "text": ""})
            st.rerun()
    with c_save:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            update_story_pages(st.session_state.ssb_story_id, st.session_state.ssb_pages)
            st.success("✅ Changes saved!")
    with c_disp:
        if st.button("▶ Display Mode", use_container_width=True):
            st.session_state.ssb_mode = "display"
            st.session_state.ssb_book_page = 0
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# MODE: STUDENT DISPLAY (book style)
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.ssb_mode == "display":
    pages = st.session_state.ssb_pages
    if not pages:
        st.warning("No story loaded. Go to the library and press ▶ Display next to a story.")
    else:
        meta  = st.session_state.ssb_story_meta
        total = len(pages)
        idx   = st.session_state.ssb_book_page

        # Title card
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:.5rem;">
            <div style="font-size:1.1rem;font-weight:700;color:{NAVY}">{meta.get('title','Visual Support Material')}</div>
            <div style="font-size:.8rem;color:#6b7a8d">
                {"For " + meta.get('student_name') if meta.get('student_name') else ''}
                &nbsp;·&nbsp; Page {idx+1} of {total}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress dots
        dots_html = '<div class="progress-dots">'
        for d in range(total):
            dots_html += f'<span class="dot {"dot-active" if d==idx else ""}"></span>'
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)

        # Page card
        page_text = pages[idx]["text"]
        st.markdown(f"""
        <div class="book-page">
            <div class="bp-text">{page_text}</div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation buttons
        left_col, mid_col, right_col = st.columns([1, 2, 1])
        with left_col:
            if idx > 0:
                if st.button("◀  Previous", use_container_width=True):
                    st.session_state.ssb_book_page -= 1
                    st.rerun()
        with mid_col:
            if st.button("✏️  Back to Edit", use_container_width=True):
                st.session_state.ssb_mode = "edit" if st.session_state.ssb_story_id else "create"
                st.rerun()
        with right_col:
            if idx < total - 1:
                if st.button("Next  ▶", use_container_width=True):
                    st.session_state.ssb_book_page += 1
                    st.rerun()
            else:
                st.markdown(f"""
                <div style="text-align:center;padding:.5rem;
                    background:#F0FAF4;border-radius:8px;
                    color:#2d7d4f;font-weight:700;font-size:.9rem">
                    🌟 The End!
                </div>""", unsafe_allow_html=True)
