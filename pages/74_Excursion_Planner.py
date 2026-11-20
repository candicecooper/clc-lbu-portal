"""
74_Excursion_Planner.py  —  CLC Excursion Planner (ED169 + Risk Management Plan)

Staff enter an excursion ONCE; the tool builds both documents from it:
  * ED169 Application to Conduct a Camp or Excursion
  * CLC Risk Management Plan and Approval to Transport

Tabs
  1. ✏️ Plan an excursion – staff (staff password). Sub-steps: details, students & staff,
                            transport & costs, activities & risks, emergency & checks, review & submit
  2. 📋 Excursions        – every excursion and its status; edit drafts, reuse as a template, download
  3. 📚 Activity Library  – the risks/strategies each activity brings into a risk assessment
  4. 🔒 Leadership        – confidential password: approve / return, manage library + staff list, setup

Rules checked come from the DfE Camps and Excursions Procedure (March 2025) — see excursion_utils.py.
Needs: excursion_utils.py in the repo root + the SQL in Leadership → Setup run once in Supabase.
"""

import os
import sys

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Excursion Planner", page_icon="🚌", layout="wide")

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from theme import apply_clc_theme
    apply_clc_theme()
except Exception:
    pass

try:
    import excursion_utils as eu
except ModuleNotFoundError:
    st.error("**excursion_utils.py is missing from the GitHub repo.** Upload it to the main (top) folder of "
             "clc-lbu-portal, next to confidential_auth.py, then wait for Render to redeploy.")
    st.stop()

try:
    from staff_auth import require_staff_auth
    require_staff_auth("Excursion Planner", "🚌")
except ModuleNotFoundError:
    pass

ss = st.session_state
TEAL = "#1A7A7A"


# =====================================================================
# Data helpers
# =====================================================================
def db():
    return eu.get_supabase()


@st.cache_data(ttl=60, show_spinner=False)
def load_staff_dir() -> list[dict]:
    try:
        return db().table(eu.T_STAFF).select("*").order("name").execute().data or []
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def load_library() -> tuple[list[dict], bool]:
    """Returns (activities, starter_loaded). Database activities, plus any built-in starter activities
    not yet in the database (so the library is never empty and never loses the starter set)."""
    try:
        rows = db().table(eu.T_ACTIVITIES).select("*").eq("active", True).order("category").order("name").execute().data or []
    except Exception:
        rows = []
    in_db = {r["name"].strip().lower() for r in rows}
    try:
        all_names = {r["name"].strip().lower() for r in
                     db().table(eu.T_ACTIVITIES).select("name").execute().data or []}   # incl. removed ones
    except Exception:
        all_names = in_db
    missing = [dict(a, id=None, reviewed=True) for a in eu.DEFAULT_ACTIVITIES
               if a["name"].strip().lower() not in all_names]
    starter_loaded = len(missing) < len(eu.DEFAULT_ACTIVITIES)
    lib = rows + missing
    lib.sort(key=lambda a: ((a.get("category") or "Activity"), a["name"]))
    return lib, starter_loaded

def load_excursions() -> list[dict]:
    try:
        return db().table(eu.T_EXCURSIONS).select("*").order("excursion_date", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Couldn't load excursions ({e}). Has the setup SQL been run? (Leadership → Setup)")
        return []


def refresh():
    load_staff_dir.clear()
    load_library.clear()


def leader_emails() -> list[str]:
    return [s["email"] for s in load_staff_dir() if s.get("is_leader") and s.get("active", True) and s.get("email")]


def staff_email(name: str) -> str | None:
    rec = next((s for s in load_staff_dir() if s.get("name") == name), None)
    return (rec or {}).get("email")


def save_new_library_activities(d: dict, who: str):
    """Activities staff started from scratch and ticked 'save to library' → library (Leadership to check)."""
    for a in d.get("activities", []):
        if a.get("is_new") and a.get("save_to_library") and a.get("name", "").strip():
            try:
                res = db().table(eu.T_ACTIVITIES).insert({
                    "name": a["name"].strip(), "category": a.get("category") or "Activity",
                    "flags": a.get("flags") or {}, "risks": a.get("risks") or [],
                    "created_by": who, "reviewed": False, "active": True}).execute().data
                a["library_id"] = (res or [{}])[0].get("id")
                a["is_new"] = False
                a["save_to_library"] = False
            except Exception as e:
                st.warning(f"'{a['name']}' couldn't be added to the library ({e}). It is still in this excursion.")
    load_library.clear()


def save_excursion(status: str | None = None) -> dict | None:
    d = ss.ex
    save_new_library_activities(d, d.get("prepared_by") or d.get("teacher_in_charge") or "")
    rec = {
        "name": d.get("name"), "destination": d.get("destination"), "program": d.get("program"),
        "excursion_date": d.get("date_from") or None, "teacher_in_charge": d.get("teacher_in_charge"),
        "prepared_by": d.get("prepared_by"), "data": d, "updated_at": eu.now_iso(),
        "status": status or ss.ex_status or "Draft",
    }
    if status == "Submitted":
        rec["submitted_at"] = eu.now_iso()
        rec["leader_comment"] = None
    try:
        if ss.ex_id:
            row = db().table(eu.T_EXCURSIONS).update(rec).eq("id", ss.ex_id).execute().data
        else:
            row = db().table(eu.T_EXCURSIONS).insert(rec).execute().data
    except Exception as e:
        st.error(f"Couldn't save ({e}). Has the setup SQL been run? (Leadership → Setup)")
        return None
    row = (row or [None])[0]
    if row:
        ss.ex_id, ss.ex_status = row["id"], row["status"]
    return row


# =====================================================================
# Session state for the excursion being edited
# =====================================================================
def start_new(data: dict | None = None):
    ss.ex = data if data is not None else eu.blank_excursion()
    ss.ex_id = None
    ss.ex_status = "Draft"
    ss.fv = ss.get("fv", 0) + 1


def load_into_planner(row: dict, as_template: bool = False):
    import copy
    d = copy.deepcopy(row.get("data") or {})
    base = eu.blank_excursion()
    base.update(d)
    if as_template:
        base.update(date_from=None, date_to=None, checks={}, venue_reviewed=False)
        start_new(base)
    else:
        ss.ex, ss.ex_id, ss.ex_status = base, row["id"], row.get("status", "Draft")
        ss.fv = ss.get("fv", 0) + 1


if "ex" not in ss:
    start_new()
ss.setdefault("pending", None)
ss.setdefault("flash", None)


def K(name: str) -> str:
    """Widget key tied to the current form version (bumped whenever a different excursion is loaded)."""
    return f"{name}__{ss.fv}"


def queue(action, *args):
    ss.pending = (action, args)


def _int(v) -> int:
    try:
        return 0 if pd.isna(v) else int(v)
    except Exception:
        return 0


def _str(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def level_badge(lvl: str) -> str:
    return (f"<span style='background:{eu.LEVEL_COLOUR[lvl]};color:white;border-radius:10px;"
            f"padding:1px 9px;font-size:0.8rem;font-weight:600'>{lvl}</span>")


STATUS_BADGE = {"Draft": "📝 Draft", "Submitted": "⏳ Awaiting approval", "Returned": "↩️ Returned for changes",
                "Approved": "✅ Approved", "Cancelled": "✖️ Cancelled"}


def show_checks(checks):
    for lvl, msg in checks:
        if lvl == "block":
            st.error(msg, icon="⛔")
        elif lvl == "warn":
            st.warning(msg, icon="⚠️")
        else:
            st.success(msg, icon="✅")


def download_buttons(row: dict, key: str):
    c1, c2 = st.columns(2)
    try:
        c1.download_button("📄 ED169 (Word)", eu.build_ed169(row), file_name=eu.doc_filename(row, "ED169"),
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           key=f"dl169_{key}", use_container_width=True)
        c2.download_button("🛡️ Risk Assessment (Word)", eu.build_risk_assessment(row),
                           file_name=eu.doc_filename(row, "Risk_Assessment"),
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           key=f"dlra_{key}", use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't build the documents: {e}")


# =====================================================================
# Header
# =====================================================================
st.markdown(f"""
<div style="background:linear-gradient(135deg,{TEAL},#0f5f5f);color:white;border-radius:14px;
            padding:1.1rem 1.4rem;margin-bottom:0.8rem">
  <div style="font-size:1.5rem;font-weight:700">🚌 Excursion Planner</div>
  <div style="opacity:.85;font-size:.92rem">Enter the excursion once → ED169 and Risk Management Plan built for you,
  checked against the DfE Camps &amp; Excursions Procedure, then approved by a Leader.</div>
</div>""", unsafe_allow_html=True)

if ss.flash:
    kind, msg = ss.flash
    (st.success if kind == "ok" else st.warning if kind == "warn" else st.error)(msg)
    ss.flash = None

tab_plan, tab_list, tab_lib, tab_lead = st.tabs(
    ["✏️ Plan an excursion", "📋 Excursions", "📚 Activity Library", "🔒 Leadership"])

staff_dir = load_staff_dir()
library, lib_from_db = load_library()

# =====================================================================
# TAB 1 — PLAN
# =====================================================================
with tab_plan:
    d = ss.ex
    top = st.columns([3, 1, 1])
    title = d.get("name") or "New excursion"
    top[0].markdown(f"#### {title}  \n<span style='color:#666'>{STATUS_BADGE.get(ss.ex_status, ss.ex_status)}"
                    f"{' · saved' if ss.ex_id else ' · not saved yet'}</span>", unsafe_allow_html=True)
    locked = ss.ex_status in ("Submitted", "Approved")
    if locked:
        st.info("This excursion has been submitted/approved, so it's read-only here. To change it, ask a Leader "
                "to return it, or use **📋 Excursions → Use as template** to start a new one.")
    if top[1].button("➕ Start new", use_container_width=True):
        queue("new")
    if top[2].button("💾 Save draft", use_container_width=True, disabled=locked, type="primary"):
        queue("save")

    s1, s2, s3, s4, s5, s6 = st.tabs(["1 · Details", "2 · Students & staff", "3 · Transport & costs",
                                      "4 · Activities & risks", "5 · Emergency & checks", "6 · Review & submit"])

    # ---------------- 1. Details ----------------
    with s1:
        c = st.columns([2, 1])
        d["excursion_type"] = c[0].radio("Type", eu.EXCURSION_TYPES, horizontal=True, key=K("type"),
                                         index=eu.EXCURSION_TYPES.index(d.get("excursion_type", eu.EXCURSION_TYPES[0])),
                                         disabled=locked)
        d["program"] = c[1].selectbox("Program", eu.PROGRAMS, key=K("prog"),
                                      index=eu.PROGRAMS.index(d.get("program", "PY")) if d.get("program") in eu.PROGRAMS else 1,
                                      disabled=locked)
        if d["excursion_type"].startswith("Local walk"):
            st.caption("Local walks/regular outings: one risk assessment per walk, reviewed at least every 12 months; "
                       "annual parent consent; tell a Leader on the day before you go.")
        c = st.columns(2)
        d["name"] = c[0].text_input("Name of excursion *", d.get("name", ""), key=K("name"), disabled=locked,
                                    placeholder="e.g. Beach & BBQ lunch")
        d["destination"] = c[1].text_input("Destination *", d.get("destination", ""), key=K("dest"), disabled=locked,
                                           placeholder="e.g. Point Malcolm Reserve")
        d["address"] = st.text_input("Suburb / address", d.get("address", ""), key=K("addr"), disabled=locked)
        d["outline"] = st.text_area("Outline of the excursion – places visited and program of activities *",
                                    d.get("outline", ""), key=K("outline"), height=100, disabled=locked)
        d["curriculum"] = st.text_area("Curriculum links / outcomes *  (how it links to the curriculum for these "
                                       "year levels – e.g. Personal and Social Capability, English, HPE)",
                                       d.get("curriculum", ""), key=K("curr"), height=80, disabled=locked)
        c = st.columns(4)
        df = eu._parse_date(d.get("date_from")) or eu.today_adl()
        dfrom = c[0].date_input("Date *", df, key=K("dfrom"), format="DD/MM/YYYY", disabled=locked)
        multi = c[1].checkbox("Runs over more than one day", value=bool(d.get("date_to") and d.get("date_to") != d.get("date_from")),
                              key=K("multi"), disabled=locked)
        dto = dfrom
        if multi:
            dto = c[1].date_input("End date", eu._parse_date(d.get("date_to")) or dfrom, key=K("dto"),
                                  format="DD/MM/YYYY", disabled=locked)
        d["date_from"], d["date_to"] = dfrom.isoformat(), dto.isoformat()
        dep = c[2].time_input("Leave CLC", eu._parse_time(d.get("depart_time")) or eu.time(10, 0), key=K("dep"),
                              step=300, disabled=locked)
        ret = c[3].time_input("Return to CLC", eu._parse_time(d.get("return_time")) or eu.time(14, 30), key=K("ret"),
                              step=300, disabled=locked)
        d["depart_time"], d["return_time"] = dep.strftime("%H:%M"), ret.strftime("%H:%M")

    # ---------------- 2. Students & staff ----------------
    with s2:
        st.markdown("##### Students (numbers only – no names)")
        init_key = f"stud_init_{ss.fv}"
        if init_key not in ss:
            _t = pd.DataFrame(d.get("students") or [{"year": "3", "male": 0, "female": 0, "other": 0}],
                              columns=["year", "male", "female", "other"])
            _t["year"] = _t["year"].astype(str)
            for _c in ("male", "female", "other"):
                _t[_c] = pd.to_numeric(_t[_c], errors="coerce").fillna(0).astype(int)
            ss[init_key] = _t
        sdf = st.data_editor(
            ss[init_key], key=K("students"), num_rows="dynamic", use_container_width=True, disabled=locked,
            column_config={
                "year": st.column_config.SelectboxColumn("Year level", options=eu.YEAR_LEVELS, required=True),
                "male": st.column_config.NumberColumn("Male", min_value=0, step=1, default=0),
                "female": st.column_config.NumberColumn("Female", min_value=0, step=1, default=0),
                "other": st.column_config.NumberColumn("Not specified", min_value=0, step=1, default=0),
            })
        d["students"] = [{"year": _str(r.get("year")) or "3", "male": _int(r.get("male")),
                          "female": _int(r.get("female")), "other": _int(r.get("other"))}
                         for r in sdf.to_dict("records") if _str(r.get("year"))]
        need, why = eu.required_adults(d)
        st.caption(f"**{eu.student_total(d)} students** → at least **{need} adults** needed. {why}.")
        d["student_considerations"] = st.text_area(
            "Individual student considerations – INITIALS ONLY (e.g. 'LA – history of leaving; stays with BS')",
            d.get("student_considerations", ""), key=K("consid"), height=80, disabled=locked)

        st.markdown("##### Staff and other adults attending")
        names = [s["name"] for s in staff_dir if s.get("active", True)]
        if names and not locked:
            c = st.columns([4, 1])
            pick = c[0].multiselect("Quick add from the staff list", [n for n in names if n not in
                                    [x.get("name") for x in d.get("staff", [])]], key=K("pickstaff"))
            c[1].markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            if c[1].button("Add", use_container_width=True, disabled=not pick):
                queue("add_staff", pick)
        elif not names:
            st.caption("Tip: a Leader can add the staff list (with first aid expiry dates) in 🔒 Leadership → Staff list.")
        init_key = f"staff_init_{ss.fv}"
        if init_key not in ss:
            _t = pd.DataFrame(d.get("staff") or [], columns=["name", "gender", "status", "experience", "first_aid"])
            _t["first_aid"] = _t["first_aid"].fillna(False).astype(bool)
            for _c in ("name", "gender", "status", "experience"):
                _t[_c] = _t[_c].astype("string")
            ss[init_key] = _t
        tdf = st.data_editor(
            ss[init_key], key=K("staff"), num_rows="dynamic", use_container_width=True, disabled=locked,
            column_config={
                "name": st.column_config.TextColumn("Name", required=True),
                "gender": st.column_config.SelectboxColumn("M/F", options=["M", "F", "X"]),
                "status": st.column_config.SelectboxColumn("Status", options=eu.STAFF_STATUSES, default="Teacher"),
                "experience": st.column_config.TextColumn("Qualifications / experience in these activities", default="Y"),
                "first_aid": st.column_config.CheckboxColumn("Current first aid", default=False),
            })
        d["staff"] = [{"name": _str(r.get("name")).strip(), "gender": _str(r.get("gender")),
                       "status": _str(r.get("status")) or "Teacher", "experience": _str(r.get("experience")) or "Y",
                       "first_aid": bool(r.get("first_aid")) if not pd.isna(r.get("first_aid")) else False}
                      for r in tdf.to_dict("records") if _str(r.get("name")).strip()]
        staff_names = [s["name"] for s in d["staff"]]
        c = st.columns(3)
        tic_opts = [""] + staff_names
        d["teacher_in_charge"] = c[0].selectbox(
            "Teacher in charge *", tic_opts, key=K("tic"), disabled=locked,
            index=tic_opts.index(d.get("teacher_in_charge")) if d.get("teacher_in_charge") in tic_opts else 0)
        d["min_at_once"] = c[1].number_input("Minimum number of adults at any one time", 1, 20,
                                             int(d.get("min_at_once") or 2), key=K("minat"), disabled=locked)
        d["prepared_by"] = c[2].text_input("Prepared by", d.get("prepared_by") or d.get("teacher_in_charge", ""),
                                           key=K("prep"), disabled=locked)

    # ---------------- 3. Transport & costs ----------------
    with s3:
        mode = st.selectbox("Mode of travel", eu.TRANSPORT_MODES, key=K("mode"), disabled=locked,
                            index=eu.TRANSPORT_MODES.index(d.get("transport_mode")) if d.get("transport_mode") in eu.TRANSPORT_MODES else 0)
        d["transport_mode"] = mode
        if mode == "Site car / government vehicle":
            d["vehicle_desc"] = st.text_input("Which vehicle?", d.get("vehicle_desc", ""), key=K("veh"),
                                              placeholder="e.g. Site car Kia", disabled=locked)
            st.caption("Only authorised drivers. Seat belts for everyone; headcount getting in and out; check the "
                       "vehicle is empty before locking.")
        elif mode == "Chartered bus":
            c = st.columns(2)
            d["bus_company"] = c[0].text_input("Bus company *", d.get("bus_company", ""), key=K("busco"), disabled=locked)
            d["bus_phone"] = c[1].text_input("Phone", d.get("bus_phone", ""), key=K("busph"), disabled=locked)
            d["bus_accreditation"] = c[0].text_input("Company accreditation no. *", d.get("bus_accreditation", ""),
                                                     key=K("busacc"), disabled=locked)
            d["driver_accreditation"] = c[1].text_input("Driver accreditation (or collect on arrival)",
                                                        d.get("driver_accreditation", ""), key=K("drvacc"), disabled=locked)
            st.markdown("**Driver** (if known now – otherwise collect from the driver on arrival and file it)")
            c = st.columns(3)
            d["driver_name"] = c[0].text_input("Name of driver", d.get("driver_name", ""), key=K("drvname"), disabled=locked)
            d["driver_licence"] = c[1].text_input("Driver's licence no", d.get("driver_licence", ""), key=K("drvlic"),
                                                  disabled=locked)
            d["last_heavy_vehicle"] = c[2].text_input("When did the driver last drive a heavy vehicle?",
                                                      d.get("last_heavy_vehicle", ""), key=K("lasthv"), disabled=locked)
            yn = ["Not known yet", "Yes", "No"]
            to_v = {"Yes": True, "No": False, "Not known yet": None}
            from_v = {True: "Yes", False: "No", None: "Not known yet"}
            c = st.columns(2)
            d["hvnl_aware"] = to_v[c[0].radio("Driver aware of Heavy Vehicle National Law requirements?", yn,
                                               index=yn.index(from_v[d.get("hvnl_aware")]), horizontal=True,
                                               key=K("hvnl"), disabled=locked)]
            d["freeway_aware"] = to_v[c[1].radio("If using the South Eastern Freeway down track: driver aware of the "
                                                  "truck and bus laws?", yn, index=yn.index(from_v[d.get("freeway_aware")]),
                                                  horizontal=True, key=K("sef"), disabled=locked)]
        elif mode == "Private vehicle":
            init_key = f"pv_init_{ss.fv}"
            if init_key not in ss:
                ss[init_key] = pd.DataFrame(d.get("private_vehicles") or [],
                                            columns=["owner", "accreditation", "rego", "safety_label_expiry",
                                                     "insurance_category", "insurer"])
            pv = st.data_editor(ss[init_key], key=K("pv"), num_rows="dynamic", use_container_width=True,
                                disabled=locked, column_config={
                                    "owner": "Name of owner", "accreditation": "Accreditation no",
                                    "rego": "Registration no", "safety_label_expiry": "Safety label expiry",
                                    "insurance_category": st.column_config.SelectboxColumn(
                                        "Insurance category", options=["Comprehensive", "Third party property"]),
                                    "insurer": "Insuring company"})
            d["private_vehicles"] = [{k: _str(v) for k, v in r.items()} for r in pv.to_dict("records")
                                     if _str(r.get("owner")) or _str(r.get("rego"))]
            st.caption("Parent consent needed for every passenger. A staff member must not transport a single student 1:1.")
        elif mode.startswith("Public transport"):
            st.caption("A CLC staff member must travel in each vehicle/carriage with students.")

        st.markdown("##### Costs per student (GST exclusive)")
        d["predominantly_educational"] = st.checkbox("This excursion is predominantly educational "
                                                     "(GST is then added to food only)",
                                                     value=bool(d.get("predominantly_educational", True)),
                                                     key=K("edu"), disabled=locked)
        c = st.columns(4)
        costs = dict(d.get("costs") or {})
        for i, (k, lbl) in enumerate([("food", "Food"), ("transport", "Transport"),
                                      ("accommodation", "Accommodation"), ("entrance", "Entrance fee(s)")]):
            costs[k] = c[i].number_input(f"{lbl} $", 0.0, 1000.0, float(costs.get(k) or 0), step=0.5,
                                         key=K(f"cost_{k}"), disabled=locked)
        d["costs"] = costs
        st.caption(f"Charge to each student (incl. any GST): **${eu.cost_breakdown(d)['total']:.2f}**")

    # ---------------- 4. Activities & risks ----------------
    with s4:
        st.markdown("Pick everything the excursion involves – **the travel, the venue and what you'll do there**. "
                    "Each one brings in its usual risks, strategies and procedures. Adjust them for this group. "
                    "The *General – supervision and student wellbeing* risks are always included automatically.")
        have = {a.get("name") for a in d.get("activities", [])}
        lib_names = [a["name"] for a in library if a["name"] not in have
                     and not (a.get("flags") or {}).get("always")]
        if not locked:
            c = st.columns([4, 1])
            pick = c[0].multiselect("Add activities from the library", lib_names, key=K("pickact"),
                                    help="Not listed? Start a new activity below — it can be saved to the library for next time.")
            c[1].markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            if c[1].button("Add", key="add_act_btn", use_container_width=True, disabled=not pick):
                queue("add_acts", pick)
            c = st.columns([4, 1])
            new_name = c[0].text_input("…or start a new activity that isn't in the library", key=K("newact"),
                                       placeholder="e.g. Ten-pin bowling")
            c[1].markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            if c[1].button("➕ New", use_container_width=True, disabled=not new_name.strip()):
                queue("new_act", new_name.strip())

        with st.expander("ℹ️ How to rate a risk (Likelihood × Consequence)"):
            mdf = pd.DataFrame({cons: eu.MATRIX[cons] for cons in reversed(eu.CONSEQUENCE)}, index=eu.LIKELIHOOD).T
            st.dataframe(mdf, use_container_width=True)
            st.caption("Rate the risk **with your strategies in place**. HIGH needs a Leader to accept it; "
                       "EXTREME can't be submitted – add controls or change the plan. "
                       "Major consequence includes 'one or more children are lost from the main group'.")

        for ai, a in enumerate(d.get("activities", [])):
            lvls = [eu.risk_level(r.get("likelihood"), r.get("consequence")) for r in a.get("risks", [])]
            top_lvl = max(lvls, key=lambda x: eu.LEVEL_ORDER[x]) if lvls else "Low"
            tag = " 🆕" if a.get("is_new") else ""
            with st.expander(f"{a.get('name') or 'New activity'}{tag}  ·  {len(a.get('risks', []))} risk(s)  ·  highest: {top_lvl}",
                             expanded=bool(a.get("is_new"))):
                if a.get("is_new"):
                    c = st.columns([3, 2])
                    a["name"] = c[0].text_input("Activity name", a.get("name", ""), key=K(f"an{ai}"), disabled=locked)
                    a["category"] = c[1].selectbox("Type", ["Activity", "Venue", "Transport", "General"],
                                                   index=["Activity", "Venue", "Transport", "General"].index(a.get("category", "Activity"))
                                                   if a.get("category") in ["Activity", "Venue", "Transport", "General"] else 0,
                                                   key=K(f"ac{ai}"), disabled=locked)
                    fl = dict(a.get("flags") or {})
                    c = st.columns(4)
                    fl["aquatic"] = c[0].checkbox("Near / in water", fl.get("aquatic", False), key=K(f"fa{ai}"), disabled=locked)
                    fl["bushfire"] = c[1].checkbox("Bushfire-prone area", fl.get("bushfire", False), key=K(f"fb{ai}"), disabled=locked)
                    fl["national_park"] = c[2].checkbox("State / national park", fl.get("national_park", False), key=K(f"fn{ai}"), disabled=locked)
                    fl["food"] = c[3].checkbox("Food involved", fl.get("food", False), key=K(f"ff{ai}"), disabled=locked)
                    a["flags"] = fl
                    a["save_to_library"] = st.checkbox("Save this activity to the library for next time "
                                                       "(a Leader will check it)", a.get("save_to_library", True),
                                                       key=K(f"sl{ai}"), disabled=locked)
                for ri, r in enumerate(a.get("risks", [])):
                    st.markdown("---" if ri else "")
                    c = st.columns([4, 1.4, 1.4, 1])
                    r["hazard"] = c[0].text_input(f"Potential risk {ri + 1}", r.get("hazard", ""),
                                                  key=K(f"h{ai}_{ri}"), disabled=locked)
                    r["likelihood"] = c[1].selectbox("Likelihood", eu.LIKELIHOOD,
                                                     index=eu.LIKELIHOOD.index(r.get("likelihood", "Unlikely")),
                                                     key=K(f"l{ai}_{ri}"), disabled=locked,
                                                     help="\n".join(f"{k}: {v}" for k, v in eu.LIKELIHOOD_HELP.items()))
                    r["consequence"] = c[2].selectbox("Consequence", eu.CONSEQUENCE,
                                                      index=eu.CONSEQUENCE.index(r.get("consequence", "Minor")),
                                                      key=K(f"c{ai}_{ri}"), disabled=locked,
                                                      help="\n\n".join(f"{k}: {' '.join(v)}" for k, v in eu.CONSEQUENCE_HELP.items()))
                    lvl = eu.risk_level(r["likelihood"], r["consequence"])
                    c[3].markdown(f"<div style='margin-top:1.9rem'>{level_badge(lvl)}</div>", unsafe_allow_html=True)
                    c = st.columns(2)
                    r["controls"] = c[0].text_area("Proactive strategies to prevent / reduce (who is responsible)",
                                                   r.get("controls", ""), key=K(f"pc{ai}_{ri}"), height=150, disabled=locked)
                    r["procedure"] = c[1].text_area("Procedure to follow if it occurs (who is responsible)",
                                                    r.get("procedure", ""), key=K(f"pr{ai}_{ri}"), height=150, disabled=locked)
                    if not locked and st.button("🗑️ Remove this risk", key=K(f"rr{ai}_{ri}")):
                        queue("del_risk", ai, ri)
                if not locked:
                    c = st.columns(2)
                    if c[0].button("➕ Add a risk to this activity", key=K(f"ar{ai}"), use_container_width=True):
                        queue("add_risk", ai)
                    if c[1].button("🗑️ Remove this activity", key=K(f"ra{ai}"), use_container_width=True):
                        queue("del_act", ai)

        with st.expander("Always included: " + eu.GENERAL_ACTIVITY["name"]):
            for r in eu.GENERAL_ACTIVITY["risks"]:
                st.markdown(f"**{r['hazard']}** {level_badge(eu.risk_level(r['likelihood'], r['consequence']))}",
                            unsafe_allow_html=True)

    # ---------------- 5. Emergency & checks ----------------
    with s5:
        st.markdown("##### Site-based contact and emergency action")
        leaders = [s["name"] for s in staff_dir if s.get("is_leader") and s.get("active", True)]
        c = st.columns(2)
        d["site_contact"] = c[0].text_input("Site-based contact person during the excursion *",
                                            d.get("site_contact") or (leaders[0] if leaders else ""),
                                            key=K("sc"), disabled=locked)
        d["site_contact_phone"] = c[1].text_input("Their mobile *", d.get("site_contact_phone", ""),
                                                  key=K("scph"), disabled=locked)
        d["call_in"] = st.text_input("Call-in procedure (when you will check in with the site contact)",
                                     d.get("call_in", ""), key=K("callin"), disabled=locked)
        d["emergency_extra"] = st.text_area("Anything extra for the emergency plan (optional)",
                                            d.get("emergency_extra", ""), key=K("emx"), height=70, disabled=locked)
        with st.expander("Preview the emergency action text on the ED169"):
            for line in eu.emergency_text(d):
                st.markdown(f"- {line}")

        st.markdown("##### Location")
        c = st.columns(2)
        d["bushfire_area"] = c[0].checkbox("In or travelling through a bushfire-prone area",
                                           bool(d.get("bushfire_area")), key=K("bfa"), disabled=locked)
        d["national_park"] = c[1].checkbox("In a state / national park", bool(d.get("national_park")),
                                           key=K("npk"), disabled=locked)

        st.markdown("##### Preparation checks")
        checks = dict(d.get("checks") or {})
        for key, label in eu.PRE_CHECKS:
            checks[key] = st.checkbox(label, bool(checks.get(key)), key=K(f"chk_{key}"), disabled=locked)
        d["checks"] = checks
        d["venue_reviewed"] = st.checkbox("Venue and safety information reviewed (and attached if the venue provides it)",
                                          bool(d.get("venue_reviewed")), key=K("venue"), disabled=locked)

    # ---------------- 6. Review & submit ----------------
    with s6:
        checks = eu.check_excursion(d, staff_dir)
        blocks = sum(1 for lv, _ in checks if lv == "block")
        warns = sum(1 for lv, _ in checks if lv == "warn")
        c = st.columns(4)
        c[0].metric("Students", eu.student_total(d))
        c[1].metric("Adults", f"{len(d.get('staff', []))} / {eu.required_adults(d)[0]} needed")
        c[2].metric("Highest risk", eu.highest_level(d))
        c[3].metric("To fix / to check", f"{blocks} / {warns}")
        show_checks(checks)
        st.markdown("##### Preview documents")
        st.caption("Drafts are marked DRAFT. The final versions are available once a Leader approves.")
        preview = {"status": ss.ex_status, "data": d}
        download_buttons(preview, "plan")
        if not locked:
            st.markdown("---")
            ok = eu.can_submit(checks)
            if not ok:
                st.info("Fix the ⛔ items above, then submit. You can save a draft any time.")
            elif warns:
                st.info("You can submit with ⚠️ items, but the Leader will see them — tick or explain what you can first.")
            if st.button("📨 Submit to Leadership for approval", type="primary", disabled=not ok,
                         use_container_width=True):
                queue("submit")

    # ---------------- pending actions (run after every widget above has updated ss.ex) ----------------
    if ss.pending:
        action, args = ss.pending
        ss.pending = None
        d = ss.ex
        if action == "new":
            start_new()
        elif action == "add_staff":
            for n in args[0]:
                rec = next((s for s in staff_dir if s.get("name") == n), {})
                exp = eu._parse_date(rec.get("first_aid_expiry"))
                d["staff"].append({"name": n, "gender": rec.get("gender") or "",
                                   "status": rec.get("status") or "Teacher",
                                   "experience": "Y",
                                   "first_aid": bool(exp and exp >= (eu._parse_date(d.get("date_from")) or eu.today_adl()))})
        elif action == "add_acts":
            for n in args[0]:
                lib_row = next((a for a in library if a["name"] == n), None)
                if lib_row:
                    d["activities"].append(eu.activity_for_excursion(lib_row))
        elif action == "new_act":
            d["activities"].append(eu.blank_activity(args[0]))
        elif action == "add_risk":
            d["activities"][args[0]]["risks"].append(eu.new_risk())
        elif action == "del_risk":
            d["activities"][args[0]]["risks"].pop(args[1])
        elif action == "del_act":
            d["activities"].pop(args[0])
        elif action == "save":
            if save_excursion():
                ss.flash = ("ok", "Draft saved. Find it any time in 📋 Excursions.")
        elif action == "submit":
            row = save_excursion("Submitted")
            if row:
                ok, msg = eu.send_email(leader_emails(), f"🚌 Excursion for approval – {d.get('name')} "
                                        f"({eu.fmt_date(d.get('date_from'))})", eu.submission_email_html(row))
                ss.flash = ("ok" if ok else "warn",
                            "Submitted to Leadership. " + (msg if ok else f"{msg} — please let a Leader know it's waiting."))
        if action not in ("new",):
            ss.fv += 1     # rebuild widgets from ss.ex
        st.rerun()


# =====================================================================
# TAB 2 — EXCURSIONS
# =====================================================================
with tab_list:
    rows = load_excursions()
    c = st.columns(3)
    f_status = c[0].multiselect("Status", list(STATUS_BADGE), default=["Draft", "Submitted", "Returned", "Approved"])
    f_prog = c[1].multiselect("Program", eu.PROGRAMS)
    f_text = c[2].text_input("Search", placeholder="destination, teacher…")
    shown = [r for r in rows if r.get("status") in f_status
             and (not f_prog or r.get("program") in f_prog)
             and (not f_text or f_text.lower() in " ".join(str(r.get(k) or "") for k in
                                                         ("name", "destination", "teacher_in_charge", "prepared_by")).lower())]
    if not shown:
        st.info("No excursions match. Start one in ✏️ Plan an excursion.")
    for r in shown:
        dd = r.get("data") or {}
        head = (f"{STATUS_BADGE.get(r['status'], r['status'])}  ·  {eu.fmt_date(r.get('excursion_date'))}  ·  "
                f"{r.get('name') or '(no name)'} – {r.get('destination') or ''}  ·  {r.get('program') or ''}  ·  "
                f"{r.get('teacher_in_charge') or ''}")
        with st.expander(head):
            st.markdown(f"**Students:** {eu.student_total(dd)} · **Adults:** {len(dd.get('staff', []))} · "
                        f"**Transport:** {dd.get('transport_mode', '')} · **Highest risk:** {eu.highest_level(dd)}")
            if r.get("status") == "Returned" and r.get("leader_comment"):
                st.warning(f"**{r.get('leader_name')}:** {r['leader_comment']}")
            if r.get("status") == "Approved":
                st.success(f"Approved by {r.get('leader_name')} on {eu.fmt_date(r.get('decided_at'))}"
                           + (f" – {r['leader_comment']}" if r.get("leader_comment") else ""))
            download_buttons(r, r["id"])
            c = st.columns(3)
            if r["status"] in ("Draft", "Returned"):
                if c[0].button("✏️ Edit", key=f"edit_{r['id']}", use_container_width=True):
                    load_into_planner(r)
                    ss.flash = ("ok", f"Loaded '{r.get('name')}' — open the ✏️ Plan an excursion tab.")
                    st.rerun()
            if c[1].button("📑 Use as template for a new excursion", key=f"tpl_{r['id']}", use_container_width=True):
                load_into_planner(r, as_template=True)
                ss.flash = ("ok", f"Copied '{r.get('name')}' as a new draft (dates and checks cleared) — open the "
                                  "✏️ Plan an excursion tab and review every risk for this group.")
                st.rerun()
            if r["status"] in ("Draft", "Returned", "Submitted"):
                if c[2].button("✖️ Cancel excursion", key=f"cx_{r['id']}", use_container_width=True):
                    db().table(eu.T_EXCURSIONS).update({"status": "Cancelled", "updated_at": eu.now_iso()}).eq("id", r["id"]).execute()
                    st.rerun()


# =====================================================================
# TAB 3 — ACTIVITY LIBRARY (read only)
# =====================================================================
with tab_lib:
    st.caption("These are the starting risks each activity brings into a risk assessment. Staff can adjust them "
               "for each excursion, and add new activities from the planner. Leadership edits the library.")
    cats = sorted({a.get("category") or "Activity" for a in library})
    for cat in cats:
        st.markdown(f"#### {cat}")
        for a in [x for x in library if (x.get("category") or "Activity") == cat]:
            new = "" if a.get("reviewed", True) else "  🆕 *(added by staff – awaiting Leadership check)*"
            with st.expander(f"{a['name']}{new}"):
                for r in a.get("risks") or []:
                    lvl = eu.risk_level(r.get("likelihood"), r.get("consequence"))
                    st.markdown(f"**{r.get('hazard')}** {level_badge(lvl)} "
                                f"<span style='color:#777;font-size:.85rem'>({r.get('likelihood')} × {r.get('consequence')})</span>",
                                unsafe_allow_html=True)
                    c = st.columns(2)
                    c[0].markdown("*Strategies*\n" + (r.get("controls") or ""))
                    c[1].markdown("*If it occurs*\n" + (r.get("procedure") or ""))


# =====================================================================
# TAB 4 — LEADERSHIP (confidential password) — keep this LAST: the gate stops the page
# =====================================================================
with tab_lead:
    try:
        from confidential_auth import require_confidential_auth
        require_confidential_auth("Excursion approvals", "🚌")
    except ModuleNotFoundError:
        st.error("confidential_auth.py not found.")
        st.stop()

    l_appr, l_lib, l_staff, l_setup = st.tabs(["✅ Awaiting approval", "📚 Edit library", "👥 Staff list", "⚙️ Setup"])

    with l_appr:
        pending_rows = [r for r in load_excursions() if r.get("status") == "Submitted"]
        if not pending_rows:
            st.success("Nothing waiting for approval.")
        leader_names = [s["name"] for s in staff_dir if s.get("is_leader") and s.get("active", True)]
        for r in pending_rows:
            dd = r.get("data") or {}
            with st.expander(f"⏳ {eu.fmt_date(r.get('excursion_date'))} · {r.get('name')} – {r.get('destination')} · "
                             f"{r.get('program')} · {r.get('teacher_in_charge')}", expanded=True):
                c = st.columns(4)
                c[0].metric("Students", eu.student_total(dd))
                c[1].metric("Adults", f"{len(dd.get('staff', []))} / {eu.required_adults(dd)[0]} needed")
                c[2].metric("Highest risk", eu.highest_level(dd))
                c[3].metric("Leave → return", f"{eu.fmt_time(dd.get('depart_time'))}–{eu.fmt_time(dd.get('return_time'))}")
                st.markdown(f"**Outline:** {dd.get('outline', '')}")
                st.markdown(f"**Activities:** " + ", ".join(a.get("name", "") for a in dd.get("activities", [])))
                if dd.get("student_considerations"):
                    st.markdown(f"**Student considerations:** {dd['student_considerations']}")
                chk = [x for x in eu.check_excursion(dd, staff_dir) if x[0] != "ok"]
                if chk:
                    st.markdown("**Flags for the Leader**")
                    show_checks(chk)
                st.caption("Open the documents to read every risk before approving:")
                download_buttons(r, f"lead_{r['id']}")
                c = st.columns([2, 3])
                if leader_names:
                    who = c[0].selectbox("Leader", leader_names, key=f"who_{r['id']}")
                else:
                    who = c[0].text_input("Leader name", key=f"who_{r['id']}")
                comment = c[1].text_area("Comment (required if returning)", key=f"cm_{r['id']}", height=70)
                c = st.columns(2)
                if c[0].button("✅ Approve", key=f"ap_{r['id']}", type="primary", use_container_width=True,
                               disabled=not who):
                    upd = {"status": "Approved", "leader_name": who, "leader_comment": comment or None,
                           "decided_at": eu.now_iso(), "updated_at": eu.now_iso()}
                    db().table(eu.T_EXCURSIONS).update(upd).eq("id", r["id"]).execute()
                    r.update(upd)
                    to = [e for e in {staff_email(r.get("teacher_in_charge")), staff_email(r.get("prepared_by"))} if e]
                    ok, msg = eu.send_email(to, f"✅ Excursion approved – {r.get('name')}", eu.decision_email_html(r, True)) \
                        if to else (False, "No email on file for the teacher in charge.")
                    ss.flash = ("ok", f"Approved. {msg if ok else msg + ' Let the teacher know directly.'}")
                    st.rerun()
                if c[1].button("↩️ Return for changes", key=f"rt_{r['id']}", use_container_width=True,
                               disabled=not (who and comment.strip())):
                    upd = {"status": "Returned", "leader_name": who, "leader_comment": comment,
                           "decided_at": eu.now_iso(), "updated_at": eu.now_iso()}
                    db().table(eu.T_EXCURSIONS).update(upd).eq("id", r["id"]).execute()
                    r.update(upd)
                    to = [e for e in {staff_email(r.get("teacher_in_charge")), staff_email(r.get("prepared_by"))} if e]
                    ok, msg = eu.send_email(to, f"↩️ Excursion returned for changes – {r.get('name')}",
                                            eu.decision_email_html(r, False)) if to else (False, "No email on file.")
                    ss.flash = ("ok", f"Returned with your comment. {msg if ok else msg + ' Let the teacher know directly.'}")
                    st.rerun()

    with l_lib:
        missing = [a for a in library if not a.get("id")]
        if missing:
            st.info(f"{len(missing)} starter activities are built into the tool but not in the database yet. Load them "
                    "so you can edit them (staff can already use them).")
            if st.button("📥 Load the starter library into the database", type="primary"):
                try:
                    db().table(eu.T_ACTIVITIES).insert(
                        [{"name": a["name"], "category": a["category"], "flags": a["flags"], "risks": a["risks"],
                          "created_by": "Starter library", "reviewed": True} for a in missing]).execute()
                    refresh()
                    ss.flash = ("ok", f"Loaded {len(missing)} activities.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't load ({e}). Run the setup SQL first (⚙️ Setup).")
        editable = [a for a in library if a.get("id")]
        if not editable:
            st.caption("Nothing to edit yet.")
        else:
            unrev = [a for a in library if not a.get("reviewed", True)]
            if unrev:
                st.warning(f"{len(unrev)} activity(ies) added by staff need checking: " + ", ".join(a["name"] for a in unrev))
            names = [("🆕 " if not a.get("reviewed", True) else "") + a["name"] for a in editable]
            pick = st.selectbox("Activity to edit", range(len(editable)), format_func=lambda i: names[i])
            a = editable[pick]
            c = st.columns([3, 2])
            nm = c[0].text_input("Name", a["name"], key=f"lname_{a['id']}")
            cat = c[1].selectbox("Type", ["Activity", "Venue", "Transport", "General"],
                                 index=["Activity", "Venue", "Transport", "General"].index(a.get("category"))
                                 if a.get("category") in ["Activity", "Venue", "Transport", "General"] else 0,
                                 key=f"lcat_{a['id']}")
            fl = dict(a.get("flags") or {})
            c = st.columns(4)
            for i, (k, lbl) in enumerate([("aquatic", "Near / in water"), ("bushfire", "Bushfire-prone"),
                                          ("national_park", "State / national park"), ("food", "Food involved")]):
                fl[k] = c[i].checkbox(lbl, bool(fl.get(k)), key=f"lf{k}_{a['id']}")
            rdf = pd.DataFrame(a.get("risks") or [], columns=["hazard", "likelihood", "consequence", "controls", "procedure"])
            ed = st.data_editor(rdf, key=f"lrisks_{a['id']}", num_rows="dynamic", use_container_width=True,
                                column_config={
                                    "hazard": st.column_config.TextColumn("Potential risk", width="medium"),
                                    "likelihood": st.column_config.SelectboxColumn("Likelihood", options=eu.LIKELIHOOD, default="Unlikely"),
                                    "consequence": st.column_config.SelectboxColumn("Consequence", options=eu.CONSEQUENCE, default="Minor"),
                                    "controls": st.column_config.TextColumn("Strategies (start lines with '- ')", width="large"),
                                    "procedure": st.column_config.TextColumn("If it occurs", width="large")})
            st.caption("Tip: long text is easier to edit by double-clicking a cell. Changes only affect NEW excursions.")
            c = st.columns(3)
            if c[0].button("💾 Save & mark checked", type="primary", use_container_width=True):
                risks = [{k: _str(v) for k, v in rr.items()} for rr in ed.to_dict("records") if _str(rr.get("hazard"))]
                db().table(eu.T_ACTIVITIES).update({"name": nm, "category": cat, "flags": fl, "risks": risks,
                                                    "reviewed": True}).eq("id", a["id"]).execute()
                refresh()
                ss.flash = ("ok", f"Saved '{nm}'.")
                st.rerun()
            if c[2].button("🗑️ Remove from library", use_container_width=True):
                db().table(eu.T_ACTIVITIES).update({"active": False}).eq("id", a["id"]).execute()
                refresh()
                st.rerun()

    with l_staff:
        st.caption("Used for quick-adding staff, first aid expiry warnings, choosing the approving Leader, and emails. "
                   "**Leaders** receive submission emails and can approve.")
        sdf = pd.DataFrame(staff_dir, columns=["id", "name", "gender", "status", "email", "is_leader",
                                               "first_aid_expiry", "active"])
        sdf["first_aid_expiry"] = pd.to_datetime(sdf["first_aid_expiry"], errors="coerce").dt.date
        for _c in ("is_leader", "active"):
            sdf[_c] = sdf[_c].fillna(_c == "active").astype(bool)
        for _c in ("id", "name", "gender", "status", "email"):
            sdf[_c] = sdf[_c].astype("string")
        ed = st.data_editor(sdf, key="staff_dir_ed", num_rows="dynamic", use_container_width=True,
                            column_config={
                                "id": None,
                                "name": st.column_config.TextColumn("Name", required=True),
                                "gender": st.column_config.SelectboxColumn("M/F", options=["M", "F", "X"]),
                                "status": st.column_config.SelectboxColumn("Role", options=eu.STAFF_STATUSES),
                                "email": st.column_config.TextColumn("Email"),
                                "is_leader": st.column_config.CheckboxColumn("Leader", default=False),
                                "first_aid_expiry": st.column_config.DateColumn("First aid expires", format="DD/MM/YYYY"),
                                "active": st.column_config.CheckboxColumn("Active", default=True)})
        c = st.columns(2)
        if c[0].button("💾 Save staff list", type="primary", use_container_width=True):
            try:
                for rr in ed.to_dict("records"):
                    if not _str(rr.get("name")).strip():
                        continue
                    exp = rr.get("first_aid_expiry")
                    rec = {"name": _str(rr["name"]).strip(), "gender": _str(rr.get("gender")) or None,
                           "status": _str(rr.get("status")) or "Teacher", "email": _str(rr.get("email")).strip() or None,
                           "is_leader": bool(rr.get("is_leader")) if not pd.isna(rr.get("is_leader")) else False,
                           "first_aid_expiry": exp.isoformat() if exp is not None and not pd.isna(exp) else None,
                           "active": bool(rr.get("active")) if not pd.isna(rr.get("active")) else True}
                    if _str(rr.get("id")):
                        db().table(eu.T_STAFF).update(rec).eq("id", rr["id"]).execute()
                    else:
                        db().table(eu.T_STAFF).insert(rec).execute()
                refresh()
                ss.flash = ("ok", "Staff list saved. (Untick Active to remove someone.)")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save ({e}).")
        if c[1].button("📥 Copy names & emails from the Hazard Report lists", use_container_width=True):
            try:
                have = {s["name"].lower() for s in staff_dir}
                new = []
                for h in db().table("hazard_recipients").select("*").eq("active", True).execute().data or []:
                    if h.get("name") and h["name"].lower() not in have:
                        new.append({"name": h["name"], "email": h.get("email"),
                                    "is_leader": h.get("role") == "Leadership",
                                    "status": "Leader" if h.get("role") == "Leadership" else "SSO"})
                        have.add(h["name"].lower())
                for h in db().table("hazard_staff").select("name").eq("active", True).execute().data or []:
                    if h.get("name") and h["name"].lower() not in have:
                        new.append({"name": h["name"]})
                        have.add(h["name"].lower())
                if new:
                    db().table(eu.T_STAFF).insert(new).execute()
                refresh()
                ss.flash = ("ok", f"Copied {len(new)} new name(s). Now add gender, role and first aid expiry.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't copy ({e}).")

    with l_setup:
        st.markdown("Run this once in **Supabase → SQL editor** (the same project as the Hazard Report):")
        st.code(eu.SETUP_SQL, language="sql")
        st.markdown("Email uses the existing portal mailer (`EMAIL_WEBHOOK_URL` / `EMAIL_WEBHOOK_TOKEN`). "
                    "Submissions go to every **active Leader with an email** in the Staff list.")
        if st.button("Send a test email to the Leaders"):
            ok, msg = eu.send_email(leader_emails(), "TEST – Excursion Planner",
                                    "<p>Test from the CLC portal's Excursion Planner. Excursions submitted for "
                                    "approval will arrive like this.</p>")
            (st.success if ok else st.error)(msg)
