"""
73_Talk_Book.py  —  CLC Talk Book (interactive PODD-style communication book)

Tabs
  1. Talk Book      – the interactive book. Pick a student (or the shared practice
                      book); words the student taps and messages they speak are
                      logged against their INITIALS ONLY.
  2. Trial notes    – staff record how a session went (setting, support level,
                      engagement, what the student communicated).
  3. Trial review   – most-used words, sections used, spoken messages and trial
                      notes per student, with CSV downloads.

How it works
  • The book itself is a static component in data/talk_book/index.html
    (symbols from the site's licensed Boardmaker book are embedded in it).
  • The component sends word taps and book edits back to this page, which
    writes them to Supabase (students project) with the server key — no
    database key is ever exposed to the browser.
  • Each student can have their own customised book (talk_book_profiles).
    Students without one use the shared book ("_shared").

Supabase tables (students project): run talk_book_schema.sql once.
"""

from __future__ import annotations

import os
import sys
import time as _time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Talk Book", page_icon="💬", layout="wide")

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _p in (str(_HERE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from theme import apply_clc_theme, page_header
    apply_clc_theme()
except Exception:  # noqa: BLE001
    def page_header(title, subtitle="", icon=""):
        st.title(f"{icon} {title}")
        if subtitle:
            st.caption(subtitle)

from archive_utils import _get_client, fetch_register  # noqa: E402

ADL = ZoneInfo("Australia/Adelaide")
SHARED_KEY = "_shared"
T_PROFILES = "talk_book_profiles"
T_USAGE = "talk_book_usage"
T_TRIALS = "talk_book_trials"

try:
    import talk_book_component as _tbc
except ModuleNotFoundError:
    st.error("**talk_book_component.py is missing from the GitHub repo.** Upload it to the main (top) "
             "folder of clc-lbu-portal, next to staff_auth.py, then wait for Render to redeploy.")
    st.stop()

if not _tbc.AVAILABLE:
    st.error("**data/talk_book/index.html is missing from the GitHub repo.** Create the folder "
             "`data/talk_book` and upload `index.html` into it, then wait for Render to redeploy.")
    st.stop()

_talk_book = _tbc.talk_book

SECTIONS = ["Page 1 / Starters", "Tell", "Like / Don't like", "Something's wrong", "Body", "Categories",
            "Questions", "People", "Actions", "Activities", "Places", "Special events", "Health",
            "Clothes", "Things", "House & garden", "Food & drink", "Transport", "Characters",
            "Animals", "Days & times", "Feelings", "Descriptions", "Toilet", "Alphabet (spelling)"]
SETTINGS = ["Classroom learning", "Morning circle", "Play / break", "Eating time", "Café / barista",
            "1:1 session", "Community outing", "Regulation / break space", "Other"]
SUPPORT = ["Independent", "Indirect cue (pause, expectant look)", "Gesture / point",
           "Verbal prompt", "Modelled on the book (aided language)", "Physical support"]
ENGAGE = {1: "1 · Refused / no interest", 2: "2 · Brief interest", 3: "3 · Used with lots of support",
          4: "4 · Used with some support", 5: "5 · Used readily"}


# ──────────────────────────────────────────────────────────────────────────
# Supabase (students project — same as the Register / Document Archive)
# ──────────────────────────────────────────────────────────────────────────
def _q(fn, retries: int = 3):
    """Run a query with retry (Render free tier drops idle connections)."""
    last = None
    for attempt in range(retries):
        try:
            return fn(_get_client())
        except Exception as exc:  # noqa: BLE001
            last = exc
            _time.sleep(0.4 * (attempt + 1))
    raise last


@st.cache_data(ttl=120, show_spinner=False)
def load_students() -> list[dict]:
    rows = fetch_register("active") or []
    return [r for r in rows if r.get("initials")]


@st.cache_data(ttl=30, show_spinner=False)
def load_profile(key: str) -> dict | None:
    try:
        rows = _q(lambda c: c.table(T_PROFILES).select("*").eq("profile_key", key).limit(1).execute().data)
        return rows[0] if rows else None
    except Exception:  # noqa: BLE001
        return None


def save_profile(key: str, data: dict, staff: str):
    _q(lambda c: c.table(T_PROFILES).upsert({
        "profile_key": key, "data": data, "updated_by": staff or None,
        "updated_at": datetime.now(ADL).isoformat(),
    }, on_conflict="profile_key").execute())
    load_profile.clear()


def delete_profile(key: str):
    _q(lambda c: c.table(T_PROFILES).delete().eq("profile_key", key).execute())
    load_profile.clear()


@st.cache_data(ttl=30, show_spinner=False)
def load_usage(ini: str | None, since: str, until: str) -> pd.DataFrame:
    def fn(c):
        q = c.table(T_USAGE).select("*").gte("tapped_at", since).lt("tapped_at", until)
        if ini:
            q = q.eq("student_initials", ini)
        return q.order("tapped_at").limit(20000).execute().data or []
    try:
        df = pd.DataFrame(_q(fn))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load the word log: {exc}")
        return pd.DataFrame()
    if not df.empty:
        df["tapped_at"] = pd.to_datetime(df["tapped_at"], utc=True).dt.tz_convert(ADL)
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_trials(ini: str | None) -> pd.DataFrame:
    def fn(c):
        q = c.table(T_TRIALS).select("*")
        if ini:
            q = q.eq("student_initials", ini)
        return q.order("trial_date", desc=True).limit(500).execute().data or []
    try:
        return pd.DataFrame(_q(fn))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load trial notes: {exc}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────
# Messages coming back from the book (word log + book edits)
# ──────────────────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("tb_acks", {})        # {component instance: {"seq": n, "save": n}}
ss.setdefault("tb_staff", "")
ss.setdefault("tb_sid", None)
ss.setdefault("tb_sid_for", None)


def process_outbox(comp_key: str = "tb_comp") -> str | None:
    """Save anything the book has sent since the last rerun. Returns a notice for the book."""
    v = ss.get(comp_key)
    if not isinstance(v, dict) or not v.get("inst"):
        return None
    ack = ss.tb_acks.setdefault(v["inst"], {"seq": 0, "save": 0})
    notice = None

    events = [e for e in (v.get("events") or []) if int(e.get("seq", 0)) > ack["seq"]]
    if events:
        rows = [{
            "student_initials": str(e.get("s"))[:10],
            "staff_name": ss.tb_staff or None,
            "session_id": ss.tb_sid,
            "kind": e.get("kind") or "word",
            "word": str(e.get("w") or "")[:500],
            "page": str(e.get("p") or "")[:10],
            "section": str(e.get("c") or "")[:60],
            "tapped_at": e.get("t") or datetime.now(ADL).isoformat(),
        } for e in events if e.get("s")]
        try:
            if rows:
                _q(lambda c: c.table(T_USAGE).insert(rows).execute())
            ack["seq"] = max(int(e["seq"]) for e in events)
            load_usage.clear()
        except Exception as exc:  # noqa: BLE001
            notice = "Word log not saved yet. It will try again."
            st.toast(f"Talk Book word log could not be saved: {exc}", icon="⚠️")

    sv = v.get("save")
    if isinstance(sv, dict) and int(sv.get("seq", 0)) > ack["save"] and sv.get("key"):
        try:
            save_profile(sv["key"], sv.get("data") or {}, ss.tb_staff)
            ack["save"] = int(sv["seq"])
        except Exception as exc:  # noqa: BLE001
            notice = "Changes not saved to the portal yet. They will try again."
            st.toast(f"Talk Book changes could not be saved: {exc}", icon="⚠️")
    return notice


notice = process_outbox("tb_comp")
helper_notice = process_outbox("tb_helper_comp")

# ──────────────────────────────────────────────────────────────────────────
# Page
# ──────────────────────────────────────────────────────────────────────────
page_header("Talk Book", "Interactive communication book — trial with students", "💬")

students = load_students()
labels = {r["initials"]: f'{r["initials"]}' + (f' ({r["program"]})' if r.get("program") else "") for r in students}
PRACTICE = "— Practice / shared book (no logging) —"

tab_book, tab_helper, tab_notes, tab_review = st.tabs(["💬 Talk Book", "🧰 Helper Books", "📝 Trial notes", "📊 Trial review"])

with tab_book:
    c1, c2, c3 = st.columns([2, 2, 1.4])
    with c1:
        choice = st.selectbox("Student", [PRACTICE] + list(labels), key="tb_student",
                              format_func=lambda k: labels.get(k, k))
    with c2:
        ss.tb_staff = st.text_input("Your name (for the trial record)", value=ss.tb_staff, key="tb_staff_in")
    with c3:
        st.write("")
        logging_on = st.toggle("Log words", value=True, key="tb_log",
                               help="Records each word the student taps and each message spoken, "
                                    "against their initials only.")

    student = None if choice == PRACTICE else choice
    if ss.tb_sid_for != student:            # new session each time the student changes
        ss.tb_sid = f"{date.today():%Y%m%d}-{uuid.uuid4().hex[:8]}"
        ss.tb_sid_for = student

    shared = load_profile(SHARED_KEY)
    if student:
        own = load_profile(student)
        prof = own or shared
        profile_key, profile_label = student, f"{student}'s book"
        if own:
            st.caption(f"Using **{student}'s own book**. Edits save to their book only.")
        else:
            st.caption(f"Using the **shared book**. Edits you make here create **{student}'s own book** "
                       f"(the shared book stays the same).")
    else:
        prof = shared
        profile_key, profile_label = SHARED_KEY, "the shared book"
        st.caption("Practice mode: nothing is logged. Edits here change the **shared book**, "
                   "which every student starts from.")

    if student and logging_on and not ss.tb_staff.strip():
        st.info("Add your name above so the trial record shows who was working with the student.")

    _talk_book(
        student=student,
        logging=bool(student and logging_on),
        profile=(prof or {}).get("data") or {},
        profile_key=profile_key,
        profile_label=profile_label,
        profile_rev=str((prof or {}).get("updated_at") or ""),
        acks=ss.tb_acks,
        notice=notice,
        key="tb_comp",
        default=None,
    )

    with st.expander("How to use the Talk Book with a student"):
        st.markdown("""
- **Model first.** Point to the words yourself as you talk (aided language). Students learn the book by watching adults use it.
- Tap a **category** (page 7, or the red **C**) to open a section. Coloured page numbers on a square take you to that page.
- Tap **Say it** (or the message bar) to speak the whole message. **Oops** removes the last word.
- **Edit book** lets you change any square: word, picture (upload a photo or symbol), and which page it opens. Changes save to the portal.
- Choose an **Australian voice** in ⚙️ Settings inside the book (iPad: Settings › Accessibility › Spoken Content › Voices if none is listed).
- After the session, add a **Trial note** so we can see what's working.
""")
    if student and load_profile(student):
        with st.expander(f"Reset {student}'s book"):
            st.write(f"This removes {student}'s own edits so they go back to the shared book. The word log is kept.")
            if st.button(f"Reset {student}'s book to the shared book", key="tb_reset"):
                try:
                    delete_profile(student)
                    st.success("Reset. Reloading…")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not reset: {exc}")

# ── Helper Books ─────────────────────────────────────────────────────────
with tab_helper:
    try:
        import helper_book as hb
    except ModuleNotFoundError:
        hb = None
        st.error("**helper_book.py is missing from the GitHub repo.** Upload it to the main (top) folder "
                 "of clc-lbu-portal, next to talk_book_component.py.")
    if hb is not None and not hb.symbols():
        st.warning("**data/talk_book/symbols.json is missing.** Upload it into the data/talk_book folder "
                   "so the Helper Books can show symbols.")
    if hb is not None:
        st.markdown("A small, personal book of big squares for one student: how they feel, what they need, "
                    "how to ask for help and what they can do when they're upset. Use it on screen or print "
                    "it as a pocket booklet.")
        h1, h2 = st.columns([2, 3])
        with h1:
            h_student = st.selectbox("Student", list(labels) or ["(no students on the register)"],
                                     format_func=lambda k: labels.get(k, k), key="hb_student")
        hkey = f"helper:{h_student}"
        if ss.get("hb_loaded_for") != h_student:
            row = load_profile(hkey) if h_student in labels else None
            ss.hb_data = (row or {}).get("data") or hb.default_helper()
            ss.hb_saved = bool(row)
            ss.hb_loaded_for = h_student
            ss.hb_ver = ss.get("hb_ver", 0) + 1
        data = ss.hb_data
        v = ss.hb_ver
        with h2:
            st.write("")
            st.caption(f"Showing **{h_student}'s helper book**." if ss.hb_saved else
                       f"{h_student} doesn't have a helper book yet. This is the starter book; "
                       f"change anything, then **Save**.")

        sub_setup, sub_use, sub_print = st.tabs(["✏️ Set up", "💬 Use with student", "🖨️ Print"])

        with sub_setup:
            data["title"] = st.text_input("Book title", value=data.get("title", "My Helper Book"), key=f"hb_title_{v}")
            sym_opts = [""] + hb.symbol_options()
            colours = list(hb.PAGE_COLOURS)
            for pi, pg in enumerate(data["pages"]):
                with st.expander(f'{"✅" if pg.get("on", True) else "⬜"}  {pg.get("title") or "Untitled page"}',
                                 expanded=False):
                    a, b, c, d = st.columns([3, 1.4, 1, 1])
                    pg["title"] = a.text_input("Page title", value=pg.get("title", ""), key=f"hb_pt_{v}_{pi}")
                    pg["colour"] = b.selectbox("Colour", colours,
                                               index=colours.index(pg.get("colour")) if pg.get("colour") in colours else 0,
                                               key=f"hb_pc_{v}_{pi}")
                    with c:
                        st.write("")
                        pg["on"] = st.checkbox("Include", value=pg.get("on", True), key=f"hb_on_{v}_{pi}")
                    with d:
                        st.write("")
                        if st.button("🗑️ Remove page", key=f"hb_rm_{v}_{pi}"):
                            data["pages"].pop(pi)
                            ss.hb_ver += 1
                            st.rerun()
                    for si, sq in enumerate(pg["squares"]):
                        x1, x2, x3, x4, x5 = st.columns([0.6, 2, 2.4, 2.4, 0.5])
                        img = hb.square_image(sq)
                        if img:
                            x1.markdown(f'<img src="{img}" style="height:46px;max-width:100%;object-fit:contain;'
                                        f'background:#fff;border-radius:6px">', unsafe_allow_html=True)
                        else:
                            x1.markdown(f'<div style="font-size:32px">{sq.get("icon") or "▫️"}</div>',
                                        unsafe_allow_html=True)
                        sq["label"] = x2.text_input("Words on the square", value=sq.get("label", ""),
                                                    key=f"hb_l_{v}_{pi}_{si}", label_visibility="collapsed" if si else "visible")
                        sq["say"] = x3.text_input("Spoken as (optional)", value=sq.get("say", ""),
                                                  key=f"hb_s_{v}_{pi}_{si}", label_visibility="collapsed" if si else "visible",
                                                  placeholder="same as the words")
                        cur_sym = sq.get("sym") or ""
                        sq["sym"] = x4.selectbox("Symbol (type to search)", sym_opts,
                                                 index=sym_opts.index(cur_sym) if cur_sym in sym_opts else 0,
                                                 format_func=hb.symbol_label, key=f"hb_y_{v}_{pi}_{si}",
                                                 label_visibility="collapsed" if si else "visible") or None
                        with x5:
                            if not si:
                                st.write("")
                                st.write("")
                            if st.button("✕", key=f"hb_x_{v}_{pi}_{si}", help="Remove this square"):
                                pg["squares"].pop(si)
                                ss.hb_ver += 1
                                st.rerun()
                    a, b = st.columns([1, 2])
                    with a:
                        if len(pg["squares"]) < hb.MAX_SQUARES and st.button("➕ Add a square", key=f"hb_add_{v}_{pi}"):
                            pg["squares"].append({"label": "", "sym": None, "icon": "", "say": "", "photo": None})
                            ss.hb_ver += 1
                            st.rerun()
                        if len(pg["squares"]) >= hb.MAX_SQUARES:
                            st.caption(f"{hb.MAX_SQUARES} squares is the most a page can hold.")
                    with b:
                        named = [f"{i + 1}. {s.get('label') or '(blank)'}" for i, s in enumerate(pg["squares"])]
                        if named:
                            which = st.selectbox("Use a photo instead of the symbol for", named, key=f"hb_pw_{v}_{pi}")
                            up = st.file_uploader("Photo (e.g. a staff member or the break space)",
                                                  type=["jpg", "jpeg", "png", "webp"], key=f"hb_pu_{v}_{pi}")
                            idx = named.index(which)
                            pcol1, pcol2 = st.columns(2)
                            if up and pcol1.button("Use this photo", key=f"hb_pp_{v}_{pi}"):
                                pg["squares"][idx]["photo"] = hb.photo_to_data_url(up.getvalue())
                                ss.hb_ver += 1
                                st.rerun()
                            if pg["squares"][idx].get("photo") and pcol2.button("Remove photo", key=f"hb_pr_{v}_{pi}"):
                                pg["squares"][idx]["photo"] = None
                                ss.hb_ver += 1
                                st.rerun()
            a, b, c = st.columns([2, 1.2, 1.2])
            with a:
                new_title = st.text_input("Add a page", placeholder="e.g. At lunch time", key=f"hb_np_{v}")
            with b:
                st.write("")
                if st.button("➕ Add page", key=f"hb_npb_{v}") and new_title.strip():
                    data["pages"].append({"title": new_title.strip(), "colour": "Blue", "on": True, "squares": []})
                    ss.hb_ver += 1
                    st.rerun()
            st.divider()
            a, b, c = st.columns([1.3, 1.6, 3])
            with a:
                if st.button("💾 Save helper book", type="primary", key="hb_save",
                             disabled=h_student not in labels):
                    try:
                        save_profile(hkey, data, ss.tb_staff)
                        ss.hb_saved = True
                        st.success(f"Saved {h_student}'s helper book.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not save: {exc}")
            with b:
                if st.button("↩️ Start again from the starter book", key="hb_reset"):
                    ss.hb_data = hb.default_helper()
                    ss.hb_ver += 1
                    st.rerun()
            c.caption("Changes aren't kept until you press **Save**. Photos are stored with the "
                      "student's book (initials only).")

        with sub_use:
            st.caption("Big squares, one topic at a time. Tap a square to say it; tap the message bar or "
                       "**Say it** to say the whole message. Taps are logged against the student's initials "
                       "when **Log words** is on (Talk Book tab).")
            _talk_book(
                student=h_student if h_student in labels else None,
                logging=bool(h_student in labels and ss.get("tb_log", True)),
                profile={}, profile_key=None, profile_label=f"{h_student}'s helper book",
                helper=hb.for_component(data), helper_rev=f"{h_student}-{ss.hb_ver}",
                acks=ss.tb_acks, notice=helper_notice, key="tb_helper_comp", default=None,
            )

        with sub_print:
            a, b = st.columns(2)
            with a:
                layout = st.radio("Layout", ["pocket", "a4"], key="hb_layout",
                                  format_func=lambda k: {"pocket": "Pocket booklet: 4 small pages per A4 sheet "
                                                                   "(cut, stack and staple or ring)",
                                                         "a4": "Full size: one page per A4 sheet "
                                                               "(desk, wall or break space)"}[k])
                cover_name = st.text_input("Name on the cover (printed only, not saved)", key="hb_cover")
            with b:
                titles = [p["title"] for p in data["pages"] if p.get("on", True)]
                chosen = st.multiselect("Pages to print", titles, default=titles, key=f"hb_pick_{v}")
            if st.button("Make the PDF", type="primary", key="hb_make_pdf_btn"):
                try:
                    ss.hb_pdf_bytes = hb.build_pdf(data, layout=layout, name=cover_name.strip(), page_titles=chosen)
                except Exception as exc:  # noqa: BLE001
                    ss.hb_pdf_bytes = None
                    st.error(f"Could not make the PDF: {exc}")
            if ss.get("hb_pdf_bytes"):
                st.download_button("⬇️ Download the helper book (PDF)", ss.hb_pdf_bytes,
                                   file_name=f"helper_book_{h_student}_{layout}.pdf", mime="application/pdf")
                st.caption("Print at 100% (actual size). For the pocket booklet, cut along the dashed lines, "
                           "stack the pages in order (cover on top), then staple or use a ring. "
                           "Laminating makes it last.")

# ── Trial notes ──────────────────────────────────────────────────────────
with tab_notes:
    st.markdown("Record how a Talk Book session went. Use **initials only** in the notes.")
    with st.form("tb_trial_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        with a:
            t_student = st.selectbox("Student", list(labels) or ["(no students on the register)"],
                                     format_func=lambda k: labels.get(k, k), key="tn_student")
        with b:
            t_staff = st.text_input("Staff", value=ss.tb_staff, key="tn_staff")
        with c:
            t_date = st.date_input("Date", value=datetime.now(ADL).date(), format="DD/MM/YYYY", key="tn_date")
        a, b = st.columns(2)
        with a:
            t_setting = st.selectbox("Setting / activity", SETTINGS, key="tn_setting")
            t_support = st.radio("Most support needed", SUPPORT, key="tn_support")
        with b:
            t_pages = st.multiselect("Sections used", SECTIONS, key="tn_pages")
            t_engage = st.select_slider("Engagement with the book", options=list(ENGAGE),
                                        format_func=lambda k: ENGAGE[k], value=3, key="tn_engage")
            t_minutes = st.number_input("About how many minutes?", min_value=0, max_value=300, value=15, step=5,
                                        key="tn_minutes")
        t_comm = st.text_area("What did the student communicate? (messages, words, requests)", key="tn_comm")
        t_notes = st.text_area("What helped / what would you change? (words to add, pages to set up)", key="tn_notes")
        if st.form_submit_button("Save trial note", type="primary"):
            if t_student not in labels:
                st.error("Choose a student first.")
            elif not t_staff.strip():
                st.error("Add the staff name.")
            else:
                try:
                    _q(lambda cl: cl.table(T_TRIALS).insert({
                        "student_initials": t_student, "staff_name": t_staff.strip(),
                        "trial_date": t_date.isoformat(), "setting": t_setting, "sections_used": t_pages,
                        "support_level": t_support, "engagement": int(t_engage), "minutes": int(t_minutes),
                        "communicated": t_comm.strip() or None, "notes": t_notes.strip() or None,
                    }).execute())
                    load_trials.clear()
                    st.success(f"Trial note saved for {t_student}.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not save the trial note: {exc}")

# ── Trial review ─────────────────────────────────────────────────────────
with tab_review:
    a, b = st.columns([2, 2])
    with a:
        r_student = st.selectbox("Student", ["All students"] + list(labels),
                                 format_func=lambda k: labels.get(k, k), key="rv_student")
    with b:
        today = datetime.now(ADL).date()
        r_range = st.date_input("Dates", value=(today - timedelta(days=27), today), format="DD/MM/YYYY",
                                key="rv_range")
    if isinstance(r_range, (list, tuple)) and len(r_range) == 2:
        d0, d1 = r_range
    else:
        d0 = d1 = r_range if isinstance(r_range, date) else today
    since = datetime.combine(d0, datetime.min.time(), ADL).isoformat()
    until = datetime.combine(d1 + timedelta(days=1), datetime.min.time(), ADL).isoformat()
    ini = None if r_student == "All students" else r_student

    df = load_usage(ini, since, until)
    trials = load_trials(ini)
    if not trials.empty and "trial_date" in trials:
        trials["trial_date"] = pd.to_datetime(trials["trial_date"]).dt.date
        trials = trials[(trials["trial_date"] >= d0) & (trials["trial_date"] <= d1)]

    if df.empty and trials.empty:
        st.info("No Talk Book activity for these dates yet. Choose a student on the **Talk Book** tab "
                "with **Log words** on, and their taps will show here.")
    else:
        words = df[df["kind"] == "word"] if not df.empty else df
        says = df[df["kind"] == "say"] if not df.empty else df
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Sessions", int(df["session_id"].nunique()) if not df.empty else 0)
        m2.metric("Words tapped", len(words))
        m3.metric("Different words", int(words["word"].str.lower().nunique()) if not words.empty else 0)
        m4.metric("Messages spoken", len(says))
        m5.metric("Trial notes", len(trials))

        if ini is None and not df.empty:
            st.markdown("#### By student")
            g = df.groupby("student_initials")
            summary = pd.DataFrame({
                "Sessions": g["session_id"].nunique(),
                "Words tapped": g.apply(lambda x: (x["kind"] == "word").sum()),
                "Different words": g.apply(lambda x: x.loc[x["kind"] == "word", "word"].str.lower().nunique()),
                "Messages spoken": g.apply(lambda x: (x["kind"] == "say").sum()),
                "Last used": g["tapped_at"].max().dt.strftime("%d/%m/%Y"),
            }).sort_values("Words tapped", ascending=False)
            st.dataframe(summary, use_container_width=True)

        if not words.empty:
            import plotly.express as px
            l, r = st.columns(2)
            with l:
                top = words["word"].str.lower().value_counts().head(15).sort_values()
                fig = px.bar(x=top.values, y=top.index, orientation="h",
                             labels={"x": "Times tapped", "y": ""}, title="Most-used words")
                fig.update_traces(marker_color="#1A7A7A")
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with r:
                sec = words["section"].fillna("Other").value_counts().head(12).sort_values()
                fig = px.bar(x=sec.values, y=sec.index, orientation="h",
                             labels={"x": "Words tapped", "y": ""}, title="Sections used")
                fig.update_traces(marker_color="#C8760A")
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)
            per_day = words.groupby(words["tapped_at"].dt.date).size()
            fig = px.bar(x=per_day.index, y=per_day.values, labels={"x": "", "y": "Words tapped"},
                         title="Words tapped per day")
            fig.update_traces(marker_color="#1A7A7A")
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        if not says.empty:
            st.markdown("#### Messages spoken")
            show = says.sort_values("tapped_at", ascending=False)[["tapped_at", "student_initials", "word", "staff_name"]]
            show = show.rename(columns={"tapped_at": "When", "student_initials": "Student",
                                        "word": "Message", "staff_name": "With"})
            show["When"] = show["When"].dt.strftime("%a %d/%m %I:%M %p")
            st.dataframe(show.head(200), use_container_width=True, hide_index=True)

        if not trials.empty:
            st.markdown("#### Trial notes")
            tv = trials.copy()
            tv["engagement"] = tv["engagement"].map(lambda v: ENGAGE.get(int(v), v) if pd.notna(v) else "")
            tv["sections_used"] = tv["sections_used"].map(lambda v: ", ".join(v) if isinstance(v, list) else (v or ""))
            cols = ["trial_date", "student_initials", "staff_name", "setting", "support_level", "engagement",
                    "minutes", "sections_used", "communicated", "notes"]
            tv = tv[[c for c in cols if c in tv.columns]].rename(columns={
                "trial_date": "Date", "student_initials": "Student", "staff_name": "Staff", "setting": "Setting",
                "support_level": "Support", "engagement": "Engagement", "minutes": "Mins",
                "sections_used": "Sections", "communicated": "Communicated", "notes": "Notes"})
            st.dataframe(tv, use_container_width=True, hide_index=True)

        d1c, d2c = st.columns(2)
        tag = (ini or "all") + f"_{d0:%Y%m%d}-{d1:%Y%m%d}"
        if not df.empty:
            out = df.drop(columns=[c for c in ("id",) if c in df.columns]).copy()
            out["tapped_at"] = out["tapped_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
            d1c.download_button("⬇️ Word log (CSV)", out.to_csv(index=False).encode(),
                                file_name=f"talk_book_words_{tag}.csv", mime="text/csv")
        if not trials.empty:
            d2c.download_button("⬇️ Trial notes (CSV)", trials.to_csv(index=False).encode(),
                                file_name=f"talk_book_trials_{tag}.csv", mime="text/csv")
