"""Planning Documents - staff download page with an admin tab to add documents and publish new versions.
Files are stored in Supabase Storage (bucket: planning-documents); the list is in table planning_documents.

UNIT PLANS tab: staff upload their completed unit plans (shared with all staff). Every upload is saved
as its own Term/Week version and nothing is overwritten; the first upload of each unit is kept as the
ORIGINAL and stays downloadable. Program (JP/PY/SY/...) is required and shown on every plan.
Files: same bucket, under unit-plans/. List: table unit_plans (see unit_plans_schema.sql)."""
import re
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Planning Documents", page_icon="📄", layout="wide")

BUCKET = "planning-documents"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DEFAULT_SECTIONS = [("JP", "Junior Primary", "Reception to Year 2", "#44546A", 1),
                    ("PY", "Primary Years", "Years 3 to 6", "#6B4226", 2),
                    ("SY", "Senior Years", "Years 7 to 10", "#2F4858", 3),
                    ("ALL", "All programs", "Specialist and whole-unit documents", "#475569", 4)]


def _call_first(module_name, names):
    """Call the first matching gate function in a shared auth module. Returns True if one ran."""
    try:
        mod = __import__(module_name)
    except Exception:
        return False
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            fn()
            return True
    return False


@st.cache_resource
def get_client():
    from supabase import create_client
    s = st.secrets
    url = s.get("SUPABASE_URL") or s["supabase"]["url"]
    key = s.get("SUPABASE_KEY") or s.get("SUPABASE_SERVICE_KEY") or s["supabase"]["key"]
    return create_client(url, key)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_file(path):
    return get_client().storage.from_(BUCKET).download(path)


def load_rows():
    r = get_client().table("planning_documents").select("*").eq("hidden", False).order("uploaded_at", desc=True).execute()
    return r.data or []


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def ensure_bucket():
    """Create the storage bucket if it does not exist yet (needs a key allowed to create buckets)."""
    try:
        names = [b.name if hasattr(b, "name") else b.get("name") for b in get_client().storage.list_buckets()]
        if BUCKET not in names:
            get_client().storage.create_bucket(BUCKET, options={"public": False})
    except Exception:
        pass


def upload(program, title, desc, version, up):
    path = f"{program}/{datetime.now():%Y%m%d%H%M%S}_{safe_name(up.name)}"
    try:
        get_client().storage.from_(BUCKET).upload(path, up.getvalue(), {"content-type": MIME})
    except Exception as e:
        msg = str(getattr(e, "message", "") or e)
        if "not found" in msg.lower() or "bucket" in msg.lower():
            ensure_bucket()
            try:
                get_client().storage.from_(BUCKET).upload(path, up.getvalue(), {"content-type": MIME})
            except Exception as e2:
                st.error("Upload failed: " + str(getattr(e2, "message", "") or e2))
                st.info("Fix in Supabase: Storage > create a bucket named planning-documents, then run the storage "
                        "policy line from planning_documents_schema.sql.")
                st.stop()
        else:
            st.error("Upload failed: " + msg)
            st.info("If this mentions row-level security or a policy, run the storage policy line from "
                    "planning_documents_schema.sql. If it mentions the bucket, create a bucket named planning-documents.")
            st.stop()
    get_client().table("planning_documents").insert({
        "program": program, "title": title, "description": desc, "version": version,
        "file_name": up.name, "storage_path": path, "is_current": True}).execute()


def admin_gate():
    """Confidential-password gate. Tries the shared confidential_auth module first, then a direct password check."""
    if st.session_state.get("pd_admin_ok"):
        return True
    try:
        import confidential_auth as ca
        names = ["require_confidential_auth", "require_confidential", "check_confidential_auth", "confidential_gate",
                 "require_auth", "check_password", "require_password", "gate", "login", "confidential_login"]
        found = [n for n in names if callable(getattr(ca, n, None))]
        for n in found:
            res = getattr(ca, n)()
            if res is False:
                return False
            return True
        mod_funcs = [n for n in dir(ca) if not n.startswith("_") and callable(getattr(ca, n))]
    except Exception:
        mod_funcs = None
    # Fallback: ask for the confidential password directly
    secret = None
    for k in ("CONFIDENTIAL_PASSWORD", "confidential_password", "ADMIN_PASSWORD", "admin_password"):
        try:
            if k in st.secrets:
                secret = st.secrets[k]
                break
        except Exception:
            pass
    if secret is None:
        st.error("The admin password could not be checked from this page.")
        if mod_funcs is not None:
            st.caption("Functions found in confidential_auth: " + (", ".join(mod_funcs) or "none"))
        else:
            st.caption("confidential_auth could not be imported from this page.")
        return False
    pw = st.text_input("Confidential password", type="password", key="pd_pw")
    if pw and pw == str(secret):
        st.session_state["pd_admin_ok"] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    return False


def load_sections():
    """Sections come from Supabase; falls back to the four defaults if the table is empty or missing."""
    try:
        r = get_client().table("planning_doc_sections").select("*").order("sort_order").execute()
        if r.data:
            return {x["code"]: (x["name"], x.get("subtitle") or "", x.get("colour") or "#475569") for x in r.data}, r.data
    except Exception:
        pass
    d = {c: (n, sub, col) for c, n, sub, col, _ in DEFAULT_SECTIONS}
    return d, []


# ------------------------------------------------------------------
# Unit plans (staff uploads)
# ------------------------------------------------------------------
UNIT_TYPES = {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              ".doc": "application/msword",
              ".pdf": "application/pdf",
              ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
              ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
WEEKS = list(range(1, 12))


def unit_mime(name):
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    return UNIT_TYPES.get(ext, "application/octet-stream")


def store_file(path, data, mime):
    """Upload to the planning-documents bucket. Shows the Supabase error and stops if it fails."""
    try:
        get_client().storage.from_(BUCKET).upload(path, data, {"content-type": mime})
        return
    except Exception as e:
        msg = str(getattr(e, "message", "") or e)
    if "not found" in msg.lower() or "bucket" in msg.lower():
        ensure_bucket()
        try:
            get_client().storage.from_(BUCKET).upload(path, data, {"content-type": mime})
            return
        except Exception as e2:
            msg = str(getattr(e2, "message", "") or e2)
    st.error("Upload failed: " + msg)
    st.info("If this mentions row-level security or a policy, run the storage policy line from "
            "planning_documents_schema.sql. If it mentions the bucket, create a bucket named planning-documents.")
    st.stop()


def load_unit_rows():
    r = (get_client().table("unit_plans").select("*").eq("hidden", False)
         .order("uploaded_at", desc=True).execute())
    return r.data or []


def tw(r):
    return f"Term {r['term']} Week {r['week']} {r['year']}"


def unit_download_name(r):
    """Original keeps its own file name; later versions are named by term and week."""
    if r.get("is_original"):
        return r["file_name"]
    ext = ("." + r["file_name"].rsplit(".", 1)[-1]) if "." in r["file_name"] else ""
    return f"{r['program']}_{safe_name(r['unit_title'])}_T{r['term']}W{r['week']}_{r['year']}{ext}"


def program_badge(code):
    name, _, colour = SECTIONS.get(code, (code, "", "#475569"))
    return (f"<span style='background:{colour};color:white;padding:2px 9px;border-radius:10px;"
            f"font-size:0.8em;font-weight:600'>{code} · {name}</span>")


def save_unit_version(unit_id, program, teacher, unit_title, year, term, week, notes, up, is_original):
    path = f"unit-plans/{program}/{unit_id}/{datetime.now():%Y%m%d%H%M%S}_{safe_name(up.name)}"
    store_file(path, up.getvalue(), unit_mime(up.name))
    get_client().table("unit_plans").insert({
        "unit_id": unit_id, "program": program, "teacher": teacher, "unit_title": unit_title,
        "year": int(year), "term": int(term), "week": int(week), "notes": notes,
        "is_original": bool(is_original), "file_name": up.name, "storage_path": path}).execute()


# ---- staff-level gate (same shared module as the other staff tools)
_call_first("staff_auth", ["require_staff_auth", "require_staff", "check_staff_auth", "staff_gate"])

st.title("Planning Documents")
tab_dl, tab_units, tab_admin = st.tabs(["Download templates", "Unit Plans (shared)", "Admin: add, replace and organise"])

SECTIONS, SECTION_ROWS = load_sections()
try:
    rows = load_rows()
    db_ok = True
except Exception as e:
    rows, db_ok = [], False
    st.error("The document list could not be loaded. Check that planning_documents_schema.sql has been run and the "
             "Supabase secrets are set. Detail: " + str(e)[:200])

def sec_label(code):
    return SECTIONS.get(code, (code,))[0]

def doc_label(r):
    return f"{sec_label(r['program'])} - {r['title']} (v{r['version']})"

with tab_dl:
    st.write("Download a blank Word copy to complete for each unit or student. Save it under a new name so the "
             "original template stays clean. Older versions are listed under each document.")
    q = st.text_input("Search documents", "").lower().strip()
    shown = 0
    for code, (name, sub, colour) in SECTIONS.items():
        cur = [r for r in rows if r["program"] == code and r["is_current"]
               and q in (r["title"] + " " + (r["description"] or "")).lower()]
        if not cur:
            continue
        shown += len(cur)
        st.markdown(f"<h3 style='color:{colour};margin-bottom:0'>{name}</h3><div style='color:#666'>{sub}</div>",
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, r in enumerate(cur):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{r['title']}**")
                    st.caption(f"Version {r['version']} · updated {r['uploaded_at'][:10]}")
                    if r.get("description"):
                        st.write(r["description"])
                    try:
                        st.download_button("Download Word file", fetch_file(r["storage_path"]),
                                           file_name=r["file_name"], mime=MIME, key=f"d_{r['id']}")
                    except Exception:
                        st.warning("This file could not be loaded.")
                    older = [o for o in rows if o["program"] == code and o["title"] == r["title"] and not o["is_current"]]
                    if older:
                        with st.expander(f"Previous versions ({len(older)})"):
                            for o in older:
                                try:
                                    st.download_button(f"Version {o['version']} ({o['uploaded_at'][:10]})",
                                                       fetch_file(o["storage_path"]), file_name=o["file_name"],
                                                       mime=MIME, key=f"d_{o['id']}")
                                except Exception:
                                    st.caption(f"Version {o['version']} unavailable")
    if db_ok and not shown:
        st.info("No documents to show. Use the Admin tab to upload documents.")

with tab_units:
    import uuid
    try:
        units = load_unit_rows()
        units_ok = True
    except Exception as e:
        units, units_ok = [], False
        st.error("Unit plans could not be loaded. Run unit_plans_schema.sql in the Supabase SQL editor. "
                 "Detail: " + str(e)[:200])

    st.write("Upload your completed unit plans here so everyone can see them. Each upload is saved as a "
             "**Term and Week version** and nothing is overwritten. The **original** (first upload) of every "
             "unit is always kept and can be downloaded.")
    codes_u = list(SECTIONS)
    by_unit = {}
    for r in units:
        by_unit.setdefault(r["unit_id"], []).append(r)
    unit_meta = {}
    for uid, vs in by_unit.items():
        orig = next((v for v in vs if v.get("is_original")), None) or min(vs, key=lambda v: v["uploaded_at"])
        unit_meta[uid] = orig
    teachers = sorted({r["teacher"] for r in units if r.get("teacher")})

    if units_ok:
        with st.expander("⬆️ Upload a unit plan", expanded=not units):
            mode = st.radio("What are you uploading?",
                            ["A new unit plan", "A new Term/Week version of an existing unit"],
                            horizontal=True, key="up_mode")
            this_year = datetime.now().year

            if mode == "A new unit plan":
                with st.form("unit_new", clear_on_submit=True):
                    st.markdown("**Program** (required)")
                    prog_u = st.radio("Program", codes_u, index=None, horizontal=True,
                                      format_func=lambda c: f"{c} · {sec_label(c)}", label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    t_pick = c1.selectbox("Teacher", teachers + ["Someone else (type below)"], index=None,
                                          placeholder="Choose your name")
                    t_new = c2.text_input("Or type your name", placeholder="Only if you're not in the list")
                    title_u = st.text_input("Unit title", placeholder="e.g. Fractions in the Kitchen")
                    c3, c4, c5 = st.columns(3)
                    year_u = c3.number_input("Year", 2020, 2100, this_year)
                    term_u = c4.selectbox("Term", [1, 2, 3, 4], index=None, placeholder="Term")
                    week_u = c5.selectbox("Week", WEEKS, index=None, placeholder="Week")
                    notes_u = st.text_input("Notes (optional)", placeholder="e.g. Week 1 draft, focus on BIiN entry points")
                    file_u = st.file_uploader("Unit plan file", type=[e.strip(".") for e in UNIT_TYPES])
                    if st.form_submit_button("Save unit plan", type="primary"):
                        teacher = (t_new.strip() or (t_pick if t_pick and not t_pick.startswith("Someone") else ""))
                        missing = [n for n, v in [("program", prog_u), ("teacher", teacher), ("unit title", title_u.strip()),
                                                  ("term", term_u), ("week", week_u), ("file", file_u)] if not v]
                        if missing:
                            st.error("Please add: " + ", ".join(missing) + ".")
                        else:
                            save_unit_version(str(uuid.uuid4()), prog_u, teacher, title_u.strip(), year_u, term_u,
                                              week_u, notes_u.strip(), file_u, True)
                            st.cache_data.clear()
                            st.session_state["unit_flash"] = (f"Saved '{title_u.strip()}' ({prog_u}) as the original — "
                                                              f"Term {term_u} Week {week_u} {year_u}.")
                            st.rerun()
            else:
                if not unit_meta:
                    st.info("No unit plans yet — upload a new unit plan first.")
                else:
                    f_prog = st.radio("Program", codes_u, index=None, horizontal=True,
                                      format_func=lambda c: f"{c} · {sec_label(c)}", key="ver_prog")
                    options = [uid for uid, o in unit_meta.items() if f_prog and o["program"] == f_prog]
                    if f_prog and not options:
                        st.info(f"No {sec_label(f_prog)} unit plans yet.")
                    if options:
                        with st.form("unit_ver", clear_on_submit=True):
                            uid = st.selectbox("Unit", options, format_func=lambda u: (
                                f"{unit_meta[u]['unit_title']} — {unit_meta[u]['teacher']} "
                                f"(original {tw(unit_meta[u])})"))
                            c1, c2 = st.columns(2)
                            t_pick = c1.selectbox("Uploaded by", teachers + ["Someone else (type below)"], index=None,
                                                  placeholder="Choose your name")
                            t_new = c2.text_input("Or type your name", placeholder="Only if you're not in the list")
                            c3, c4, c5 = st.columns(3)
                            year_v = c3.number_input("Year", 2020, 2100, this_year)
                            term_v = c4.selectbox("Term", [1, 2, 3, 4], index=None, placeholder="Term")
                            week_v = c5.selectbox("Week", WEEKS, index=None, placeholder="Week")
                            notes_v = st.text_input("What changed? (optional)")
                            file_v = st.file_uploader("Updated unit plan file", type=[e.strip(".") for e in UNIT_TYPES])
                            if st.form_submit_button("Save new version", type="primary"):
                                teacher = (t_new.strip() or (t_pick if t_pick and not t_pick.startswith("Someone") else ""))
                                missing = [n for n, v in [("your name", teacher), ("term", term_v), ("week", week_v),
                                                          ("file", file_v)] if not v]
                                if missing:
                                    st.error("Please add: " + ", ".join(missing) + ".")
                                else:
                                    o = unit_meta[uid]
                                    save_unit_version(uid, o["program"], teacher, o["unit_title"], year_v, term_v,
                                                      week_v, notes_v.strip(), file_v, False)
                                    st.cache_data.clear()
                                    st.session_state["unit_flash"] = (f"Saved Term {term_v} Week {week_v} {year_v} version of "
                                                                      f"'{o['unit_title']}' ({o['program']}). The original is kept.")
                                    st.rerun()
        if st.session_state.get("unit_flash"):
            st.success(st.session_state.pop("unit_flash"))

        # ---- browse
        if unit_meta:
            st.markdown("#### Browse unit plans")
            f1, f2, f3, f4 = st.columns([2, 1, 1, 2])
            fp = f1.multiselect("Program", codes_u, format_func=lambda c: f"{c} · {sec_label(c)}",
                                placeholder="All programs")
            years = sorted({r["year"] for r in units}, reverse=True)
            fy = f2.selectbox("Year", ["All"] + years)
            ft = f3.selectbox("Term", ["All", 1, 2, 3, 4])
            fteach = f4.selectbox("Teacher", ["All"] + teachers)
            fq = st.text_input("Search unit titles", "").lower().strip()

            def unit_matches(uid):
                vs = by_unit[uid]; o = unit_meta[uid]
                if fp and o["program"] not in fp: return False
                if fq and fq not in o["unit_title"].lower(): return False
                if fteach != "All" and not any(v["teacher"] == fteach for v in vs): return False
                if fy != "All" and not any(v["year"] == fy for v in vs): return False
                if ft != "All" and not any(v["term"] == ft and (fy == "All" or v["year"] == fy) for v in vs): return False
                return True

            shown_u = 0
            for code in codes_u:
                uids = [u for u in unit_meta if unit_meta[u]["program"] == code and unit_matches(u)]
                if not uids:
                    continue
                name, sub, colour = SECTIONS[code]
                st.markdown(f"<h3 style='color:{colour};margin-bottom:0'>{code} · {name}</h3>"
                            f"<div style='color:#666'>{sub} · {len(uids)} unit plan{'s' if len(uids) != 1 else ''}</div>",
                            unsafe_allow_html=True)
                cols = st.columns(2)
                uids.sort(key=lambda u: max(v["uploaded_at"] for v in by_unit[u]), reverse=True)
                for i, uid in enumerate(uids):
                    shown_u += 1
                    o = unit_meta[uid]
                    vs = sorted(by_unit[uid], key=lambda v: (v["year"], v["term"], v["week"], v["uploaded_at"]),
                                reverse=True)
                    latest = vs[0]
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.markdown(f"{program_badge(code)}&nbsp; **{o['unit_title']}**", unsafe_allow_html=True)
                            st.caption(f"{o['teacher']} · {len(vs)} version{'s' if len(vs) != 1 else ''} · "
                                       f"latest: {tw(latest)}")
                            b1, b2 = st.columns(2)
                            try:
                                b1.download_button(f"⬇️ Original ({tw(o)})", fetch_file(o["storage_path"]),
                                                   file_name=unit_download_name(o), mime=unit_mime(o["file_name"]),
                                                   key=f"uo_{o['id']}", use_container_width=True)
                            except Exception:
                                b1.warning("Original unavailable")
                            others = [v for v in vs if v["id"] != o["id"]]
                            if others:
                                pick_v = b2.selectbox("Version", others, format_func=lambda v: (
                                    f"{tw(v)} · {v['teacher']} · {v['uploaded_at'][:10]}"),
                                    key=f"uv_{uid}", label_visibility="collapsed")
                                try:
                                    b2.download_button(f"⬇️ {tw(pick_v)}", fetch_file(pick_v["storage_path"]),
                                                       file_name=unit_download_name(pick_v),
                                                       mime=unit_mime(pick_v["file_name"]),
                                                       key=f"ud_{pick_v['id']}", use_container_width=True)
                                except Exception:
                                    b2.warning("This version is unavailable")
                            else:
                                b2.caption("No later versions yet.")
                            with st.expander("Version history"):
                                for v in vs:
                                    tag = " · **original**" if v["id"] == o["id"] else ""
                                    note = f" — {v['notes']}" if v.get("notes") else ""
                                    st.markdown(f"- {tw(v)} · {v['teacher']} · uploaded {v['uploaded_at'][:10]}{tag}{note}")
            if not shown_u:
                st.info("No unit plans match those filters.")

with tab_admin:
    if not admin_gate():
        st.stop()
    if not db_ok:
        st.stop()
    cur_all = [r for r in rows if r["is_current"]]
    codes = list(SECTIONS)

    st.subheader("1. Replace a document with a new version")
    st.caption("The old version stays available under Previous versions.")
    if cur_all:
        with st.form("new_ver", clear_on_submit=True):
            pick = st.selectbox("Document", cur_all, format_func=doc_label)
            nver = st.text_input("New version number", placeholder="e.g. 1.1")
            nup = st.file_uploader("Updated Word file", type=["docx"])
            if st.form_submit_button("Publish new version"):
                if not (nver.strip() and nup):
                    st.error("A version number and a Word file are required.")
                else:
                    upload(pick["program"], pick["title"], pick.get("description") or "", nver.strip(), nup)
                    get_client().table("planning_documents").update({"is_current": False}).eq("id", pick["id"]).execute()
                    st.cache_data.clear()
                    st.success("New version published.")
                    st.rerun()
    else:
        st.info("No documents yet. Add one below.")

    st.subheader("2. Add a new document")
    with st.form("add_doc", clear_on_submit=True):
        prog = st.selectbox("Section", codes, format_func=sec_label)
        title = st.text_input("Title")
        desc = st.text_area("Short description")
        ver = st.text_input("Version", "1.0")
        up = st.file_uploader("Word file", type=["docx"])
        if st.form_submit_button("Add document"):
            if not (title.strip() and up):
                st.error("A title and a Word file are required.")
            else:
                upload(prog, title.strip(), desc.strip(), ver.strip() or "1.0", up)
                st.cache_data.clear()
                st.success(f"Added {title.strip()}.")
                st.rerun()

    st.subheader("3. Create or edit sections")
    if not SECTION_ROWS:
        st.warning("Sections can only be saved once the planning_doc_sections table has been created "
                   "(see planning_documents_schema.sql).")
    with st.form("new_sec", clear_on_submit=True):
        c1, c2 = st.columns(2)
        sname = c1.text_input("New section name", placeholder="e.g. Specialist Program")
        ssub = c2.text_input("Subtitle (optional)")
        c3, c4 = st.columns(2)
        scol = c3.color_picker("Colour", "#475569")
        sord = c4.number_input("Display order", 1, 999, len(SECTIONS) + 1)
        if st.form_submit_button("Create section"):
            if not sname.strip():
                st.error("A section name is required.")
            else:
                code = re.sub(r"[^A-Za-z0-9]+", "_", sname.strip()).strip("_")[:30] or "SEC"
                get_client().table("planning_doc_sections").upsert(
                    {"code": code, "name": sname.strip(), "subtitle": ssub.strip(), "colour": scol, "sort_order": int(sord)}).execute()
                st.success(f"Section '{sname.strip()}' created. Add documents to it above.")
                st.rerun()
    if SECTION_ROWS:
        with st.form("edit_sec"):
            esec = st.selectbox("Edit existing section", [x["code"] for x in SECTION_ROWS], format_func=sec_label)
            cur_s = next(x for x in SECTION_ROWS if x["code"] == esec)
            en = st.text_input("Name", cur_s["name"])
            es = st.text_input("Subtitle", cur_s.get("subtitle") or "")
            ec = st.color_picker("Colour", cur_s.get("colour") or "#475569")
            eo = st.number_input("Display order", 1, 999, int(cur_s.get("sort_order") or 100))
            b1, b2 = st.columns(2)
            save = b1.form_submit_button("Save section changes")
            dele = b2.form_submit_button("Delete section (only if empty)")
            if save:
                get_client().table("planning_doc_sections").update(
                    {"name": en.strip(), "subtitle": es.strip(), "colour": ec, "sort_order": int(eo)}).eq("code", esec).execute()
                st.success("Section updated.")
                st.rerun()
            if dele:
                if any(r["program"] == esec for r in rows):
                    st.error("Move or remove the documents in this section first.")
                else:
                    get_client().table("planning_doc_sections").delete().eq("code", esec).execute()
                    st.success("Section deleted.")
                    st.rerun()

    st.subheader("4. Edit, move or remove a document")
    if cur_all:
        ed = st.selectbox("Document", cur_all, format_func=doc_label, key="ed_doc")
        with st.form(f"edit_doc_{ed['id']}"):
            nt = st.text_input("Title", ed["title"])
            nd = st.text_area("Description", ed.get("description") or "")
            ns = st.selectbox("Section", codes, index=codes.index(ed["program"]) if ed["program"] in codes else 0,
                              format_func=sec_label)
            c1, c2 = st.columns(2)
            sv = c1.form_submit_button("Save changes")
            rmv = c2.form_submit_button("Remove from list")
            if sv:
                get_client().table("planning_documents").update(
                    {"title": nt.strip(), "description": nd.strip(), "program": ns}
                ).eq("program", ed["program"]).eq("title", ed["title"]).execute()
                st.success("Saved.")
                st.rerun()
            if rmv:
                get_client().table("planning_documents").update({"hidden": True}).eq("program", ed["program"]).eq("title", ed["title"]).execute()
                st.success("Removed from the list. The files stay in storage.")
                st.rerun()

    st.subheader("5. Unit plans: remove an upload")
    st.caption("Takes a wrongly uploaded unit plan version off the Unit Plans tab. The file stays in storage. "
               "Removing an original also removes it from the unit's download, so only do this for mistakes.")
    try:
        up_rows = load_unit_rows()
    except Exception:
        up_rows = []
    if up_rows:
        with st.form("rm_unit"):
            rv = st.selectbox("Upload", up_rows, format_func=lambda v: (
                f"{v['program']} · {v['unit_title']} · {tw(v)} · {v['teacher']}"
                f"{' (original)' if v.get('is_original') else ''} · {v['uploaded_at'][:10]}"))
            if st.form_submit_button("Remove this upload"):
                get_client().table("unit_plans").update({"hidden": True}).eq("id", rv["id"]).execute()
                st.success("Removed. The file stays in storage.")
                st.rerun()
    else:
        st.caption("No unit plans uploaded yet.")
