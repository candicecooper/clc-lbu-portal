"""
CLC-LBU Leadership Checklist
pages/68_leadership_checklist.py   ->  URL: /leadership_checklist

Tabs
  1. Today          – daily leadership jobs (+ Wednesday jobs, + TRT plan when flagged)
  2. New Students   – entry meeting workflow per student (initials only)
  3. Overview       – last two weeks at a glance, open entry workflows
  4. Admin          – edit task list and leadership names

Backend: Supabase (see leadership_checklist_schema.sql)
Access:  confidential password via shared confidential_auth.py
"""

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Leadership Checklist", page_icon="✅", layout="wide")

TZ = ZoneInfo("Australia/Adelaide")
PORTAL_BASE = os.environ.get("PORTAL_BASE_URL", "https://clc-lbu-portal.onrender.com").rstrip("/")
PROGRAMS = ["JP", "PY", "SY"]
CATEGORY_LABELS = {
    "daily": "Every day",
    "wednesday": "Wednesdays",
    "trt": "TRT / change to the day",
    "entry": "New student entry",
}


# ---------------------------------------------------------------------
# Helpers: secrets, time, auth, Supabase
# ---------------------------------------------------------------------
def _secret(*names):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
        try:
            if n in st.secrets:
                return st.secrets[n]
        except Exception:
            pass
    return None


def now_iso():
    return datetime.now(TZ).isoformat()


def today_adl():
    return datetime.now(TZ).date()


def fmt_stamp(ts):
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(TZ).strftime("%a %d %b, %I:%M %p")
    except Exception:
        return str(ts)


def link_md(link):
    if not link:
        return ""
    url = PORTAL_BASE + link if link.startswith("/") else link
    return f"[Open ↗]({url})"


def confidential_gate():
    """Use the portal's shared confidential password.
    If your confidential_auth.py exposes a different function name, replace
    this whole function body with the same call 64_nit_tracker.py uses."""
    try:
        import confidential_auth as ca
        for name in ("require_confidential_access", "require_confidential", "confidential_gate",
                     "check_confidential_password", "check_password", "require_password"):
            fn = getattr(ca, name, None)
            if callable(fn):
                try:
                    ok = fn()
                except TypeError:
                    continue
                if ok is False:
                    st.stop()
                return
    except ImportError:
        pass

    # Fallback: local check against CONFIDENTIAL_PASSWORD
    pw = _secret("CONFIDENTIAL_PASSWORD")
    if st.session_state.get("confidential_ok"):
        return
    st.title("🔒 Leadership Checklist")
    entered = st.text_input("Confidential password", type="password", key="lc_pw")
    if entered:
        if pw and entered == pw:
            st.session_state["confidential_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


@st.cache_resource
def get_sb():
    from supabase import create_client
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("Supabase is not configured (SUPABASE_URL / SUPABASE_KEY).")
        st.stop()
    return create_client(url, key)


confidential_gate()
sb = get_sb()


# ---------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------
def load_tasks(active_only=True):
    q = sb.table("leadership_tasks").select("*").order("sort_order").order("id")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data or []


def load_people():
    rows = sb.table("leadership_people").select("*").order("name").execute().data or []
    return rows


def load_flag(d_iso):
    rows = sb.table("leadership_day_flags").select("*").eq("log_date", d_iso).execute().data
    return rows[0] if rows else {"log_date": d_iso, "trt_change": False, "day_notes": ""}


def load_daily_log(d_iso):
    rows = sb.table("leadership_daily_log").select("*").eq("log_date", d_iso).execute().data or []
    return {r["task_id"]: r for r in rows}


def tasks_for_day(tasks, d, trt_flag):
    cats = {"daily"}
    if d.weekday() == 2:
        cats.add("wednesday")
    if trt_flag:
        cats.add("trt")
    return [t for t in tasks if t["category"] in cats]


def who():
    return st.session_state.get("lc_who") or "Unknown"


# ---------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------
def cb_daily_toggle(task_id, d_iso, key):
    val = bool(st.session_state[key])
    sb.table("leadership_daily_log").upsert(
        {"log_date": d_iso, "task_id": task_id, "done": val,
         "done_by": who() if val else None, "done_at": now_iso() if val else None},
        on_conflict="log_date,task_id",
    ).execute()


def cb_daily_note(task_id, d_iso, key):
    sb.table("leadership_daily_log").upsert(
        {"log_date": d_iso, "task_id": task_id, "notes": st.session_state[key] or None},
        on_conflict="log_date,task_id",
    ).execute()


def cb_flag(d_iso, key):
    sb.table("leadership_day_flags").upsert(
        {"log_date": d_iso, "trt_change": bool(st.session_state[key]), "updated_at": now_iso()},
        on_conflict="log_date",
    ).execute()


def cb_day_notes(d_iso, key):
    sb.table("leadership_day_flags").upsert(
        {"log_date": d_iso, "day_notes": st.session_state[key] or None, "updated_at": now_iso()},
        on_conflict="log_date",
    ).execute()


def cb_entry_toggle(student_id, task_id, key):
    val = bool(st.session_state[key])
    sb.table("leadership_entry_progress").upsert(
        {"student_id": student_id, "task_id": task_id, "done": val,
         "done_by": who() if val else None, "done_at": now_iso() if val else None},
        on_conflict="student_id,task_id",
    ).execute()


def cb_entry_note(student_id, task_id, key):
    sb.table("leadership_entry_progress").upsert(
        {"student_id": student_id, "task_id": task_id, "notes": st.session_state[key] or None},
        on_conflict="student_id,task_id",
    ).execute()


# ---------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------
st.title("✅ Leadership Checklist")
people = [p["name"] for p in load_people() if p.get("active")]
hcol1, hcol2 = st.columns([2, 3])
with hcol1:
    if people:
        st.selectbox("Signing off as", people, key="lc_who")
    else:
        st.warning("Add leadership names in the Admin tab first.")
with hcol2:
    st.caption("Ticks are saved instantly with your name and the time. "
               "Use student initials only on this page.")

all_tasks = load_tasks()
tab_today, tab_entry, tab_overview, tab_admin = st.tabs(
    ["📅 Today", "🧒 New Students", "📊 Overview", "⚙️ Admin"]
)


# ---------------------------------------------------------------------
# Tab 1: Today
# ---------------------------------------------------------------------
with tab_today:
    c1, c2 = st.columns([1, 2])
    with c1:
        d = st.date_input("Date", value=today_adl(), format="DD/MM/YYYY", key="lc_date")
    d_iso = d.isoformat()
    flag = load_flag(d_iso)
    with c2:
        st.toggle("TRT in, or a change to the day for staff",
                  value=bool(flag.get("trt_change")), key=f"flag_{d_iso}",
                  on_change=cb_flag, args=(d_iso, f"flag_{d_iso}"),
                  help="Turn on to add the TRT plan (Program Changes – Manager) to today's list.")

    if d.weekday() >= 5:
        st.info("That date is a weekend.")

    day_tasks = tasks_for_day(all_tasks, d, bool(flag.get("trt_change")))
    log = load_daily_log(d_iso)
    done_n = sum(1 for t in day_tasks if log.get(t["id"], {}).get("done"))
    total = len(day_tasks)

    st.progress(done_n / total if total else 0.0,
                text=f"{d.strftime('%A %d %B')}: {done_n} of {total} done")
    if total and done_n == total:
        st.success("All leadership jobs done for this day.")

    for cat in ("daily", "trt", "wednesday"):
        group = [t for t in day_tasks if t["category"] == cat]
        if not group:
            continue
        st.markdown(f"#### {CATEGORY_LABELS[cat]}")
        for t in group:
            row = log.get(t["id"], {})
            ck = f"d_{d_iso}_{t['id']}"
            nk = f"dn_{d_iso}_{t['id']}"
            a, b, c = st.columns([5, 1, 4])
            with a:
                st.checkbox(f"**{t['title']}**", value=bool(row.get("done")), key=ck,
                            on_change=cb_daily_toggle, args=(t["id"], d_iso, ck))
                meta = []
                if t.get("detail"):
                    meta.append(t["detail"])
                if row.get("done") and row.get("done_by"):
                    meta.append(f"✔ {row['done_by']} · {fmt_stamp(row.get('done_at'))}")
                if meta:
                    st.caption("  \n".join(meta))
            with b:
                if t.get("link"):
                    st.markdown(link_md(t["link"]))
            with c:
                st.text_input("Note", value=row.get("notes") or "", key=nk,
                              label_visibility="collapsed", placeholder="Note (optional)",
                              on_change=cb_daily_note, args=(t["id"], d_iso, nk))

    st.divider()
    dnk = f"daynotes_{d_iso}"
    st.text_area("Notes for the day (handover for other leaders)",
                 value=flag.get("day_notes") or "", key=dnk, height=90,
                 on_change=cb_day_notes, args=(d_iso, dnk))

    # Quick reminder of entry workflows still open
    open_students = sb.table("leadership_entry_students").select("id,initials,program") \
        .eq("status", "open").execute().data or []
    if open_students:
        names = ", ".join(f"{s['initials']} ({s.get('program') or '–'})" for s in open_students)
        st.info(f"New student checklists still open: {names} → see the New Students tab.")


# ---------------------------------------------------------------------
# Tab 2: New Students (entry meeting workflow)
# ---------------------------------------------------------------------
entry_tasks = [t for t in all_tasks if t["category"] == "entry"]
before_tasks = [t for t in entry_tasks if t.get("stage") == "before"]
after_tasks = [t for t in entry_tasks if t.get("stage") != "before"]


def render_student(s):
    prog_rows = sb.table("leadership_entry_progress").select("*") \
        .eq("student_id", s["id"]).execute().data or []
    prog = {r["task_id"]: r for r in prog_rows}
    n_done = sum(1 for t in entry_tasks if prog.get(t["id"], {}).get("done"))
    n_total = len(entry_tasks)

    title = f"{s['initials']} · {s.get('program') or '–'}"
    if s.get("entry_meeting_date"):
        title += f" · Entry meeting {date.fromisoformat(s['entry_meeting_date']).strftime('%d/%m/%Y')}"
    title += f"  —  {n_done}/{n_total}"
    closed = s["status"] == "complete"

    with st.expander(title, expanded=not closed and n_done < n_total):
        st.progress(n_done / n_total if n_total else 0.0)
        for label, group in (("Before the entry meeting", before_tasks),
                             ("After the entry meeting", after_tasks)):
            if not group:
                continue
            st.markdown(f"**{label}**")
            for t in group:
                row = prog.get(t["id"], {})
                ck = f"e_{s['id']}_{t['id']}"
                nk = f"en_{s['id']}_{t['id']}"
                a, b, c = st.columns([5, 1, 4])
                with a:
                    st.checkbox(t["title"], value=bool(row.get("done")), key=ck, disabled=closed,
                                on_change=cb_entry_toggle, args=(s["id"], t["id"], ck))
                    meta = []
                    if t.get("detail"):
                        meta.append(t["detail"])
                    if row.get("done") and row.get("done_by"):
                        meta.append(f"✔ {row['done_by']} · {fmt_stamp(row.get('done_at'))}")
                    if meta:
                        st.caption("  \n".join(meta))
                with b:
                    if t.get("link"):
                        st.markdown(link_md(t["link"]))
                with c:
                    st.text_input("Note", value=row.get("notes") or "", key=nk, disabled=closed,
                                  label_visibility="collapsed", placeholder="Note (optional)",
                                  on_change=cb_entry_note, args=(s["id"], t["id"], nk))

        st.write("")
        if not closed:
            if n_done < n_total:
                st.caption(f"{n_total - n_done} step(s) left before this checklist can be closed.")
            if st.button("Close checklist", key=f"close_{s['id']}", disabled=n_done < n_total):
                sb.table("leadership_entry_students").update(
                    {"status": "complete", "completed_at": now_iso()}).eq("id", s["id"]).execute()
                st.rerun()
        else:
            st.caption(f"Closed {fmt_stamp(s.get('completed_at'))}")
            if st.button("Reopen", key=f"reopen_{s['id']}"):
                sb.table("leadership_entry_students").update(
                    {"status": "open", "completed_at": None}).eq("id", s["id"]).execute()
                st.rerun()


with tab_entry:
    with st.form("new_student", clear_on_submit=True):
        st.markdown("#### Start a new student checklist")
        f1, f2, f3, f4 = st.columns(4)
        initials = f1.text_input("Student initials", max_chars=6)
        program = f2.selectbox("Program", PROGRAMS)
        em_date = f3.date_input("Entry meeting date", value=None, format="DD/MM/YYYY")
        start = f4.date_input("Placement start", value=None, format="DD/MM/YYYY")
        if st.form_submit_button("Add student"):
            ini = (initials or "").strip().upper().replace(" ", "")
            if not ini:
                st.error("Enter the student's initials.")
            else:
                sb.table("leadership_entry_students").insert({
                    "initials": ini, "program": program,
                    "entry_meeting_date": em_date.isoformat() if em_date else None,
                    "start_date": start.isoformat() if start else None,
                    "created_by": who(),
                }).execute()
                st.success(f"Checklist started for {ini}.")
                st.rerun()

    students = sb.table("leadership_entry_students").select("*") \
        .order("created_at", desc=True).execute().data or []
    open_s = [s for s in students if s["status"] == "open"]
    done_s = [s for s in students if s["status"] == "complete"]

    st.markdown(f"#### In progress ({len(open_s)})")
    if not open_s:
        st.caption("No open entry checklists.")
    for s in open_s:
        render_student(s)

    if done_s:
        with st.expander(f"Completed ({len(done_s)})"):
            for s in done_s:
                render_student(s)


# ---------------------------------------------------------------------
# Tab 3: Overview
# ---------------------------------------------------------------------
with tab_overview:
    end = today_adl()
    days = [end - timedelta(days=i) for i in range(0, 21)]
    days = [x for x in days if x.weekday() < 5][:10]
    start_iso, end_iso = min(days).isoformat(), end.isoformat()

    logs = sb.table("leadership_daily_log").select("*") \
        .gte("log_date", start_iso).lte("log_date", end_iso).execute().data or []
    flags = sb.table("leadership_day_flags").select("*") \
        .gte("log_date", start_iso).lte("log_date", end_iso).execute().data or []
    flag_map = {f["log_date"]: f for f in flags}
    done_map = {(l["log_date"], l["task_id"]) for l in logs if l.get("done")}

    rows = []
    for dd in days:
        di = dd.isoformat()
        applicable = tasks_for_day(all_tasks, dd, bool(flag_map.get(di, {}).get("trt_change")))
        missing = [t["title"] for t in applicable if (di, t["id"]) not in done_map]
        rows.append({
            "Date": dd.strftime("%a %d %b"),
            "Done": f"{len(applicable) - len(missing)}/{len(applicable)}",
            "TRT/change": "Yes" if flag_map.get(di, {}).get("trt_change") else "",
            "Not ticked": "; ".join(missing) if missing else "✔ all done",
        })
    st.markdown("#### Last two school weeks")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("#### Open new student checklists")
    open_now = sb.table("leadership_entry_students").select("*").eq("status", "open") \
        .order("created_at").execute().data or []
    if not open_now:
        st.caption("None.")
    else:
        prog_all = sb.table("leadership_entry_progress").select("student_id,task_id,done") \
            .in_("student_id", [s["id"] for s in open_now]).execute().data or []
        done_by_student = {}
        for p in prog_all:
            if p.get("done"):
                done_by_student.setdefault(p["student_id"], set()).add(p["task_id"])
        orows = []
        for s in open_now:
            dset = done_by_student.get(s["id"], set())
            left = [t["title"] for t in entry_tasks if t["id"] not in dset]
            orows.append({
                "Student": s["initials"], "Program": s.get("program") or "",
                "Entry meeting": s.get("entry_meeting_date") or "",
                "Done": f"{len(entry_tasks) - len(left)}/{len(entry_tasks)}",
                "Next step": left[0] if left else "Ready to close",
            })
        st.dataframe(pd.DataFrame(orows), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------
# Tab 4: Admin
# ---------------------------------------------------------------------
def _clean(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


with tab_admin:
    st.markdown("#### Task list")
    st.caption("Edit titles, details and links in place. Untick **Active** to retire a task "
               "but keep its history. Deleting a row also deletes its sign-off history. "
               "Links starting with “/” open portal pages.")
    tasks_all = load_tasks(active_only=False)
    cols = ["id", "title", "detail", "category", "stage", "link", "sort_order", "active"]
    df = pd.DataFrame(tasks_all, columns=cols) if tasks_all else pd.DataFrame(columns=cols)
    edited = st.data_editor(
        df, num_rows="dynamic", hide_index=True, use_container_width=True, key="task_editor",
        column_config={
            "id": None,
            "title": st.column_config.TextColumn("Task", required=True, width="large"),
            "detail": st.column_config.TextColumn("Detail", width="large"),
            "category": st.column_config.SelectboxColumn(
                "When", options=list(CATEGORY_LABELS), required=True, default="daily"),
            "stage": st.column_config.SelectboxColumn(
                "Entry stage", options=["before", "after"],
                help="Only for New student entry tasks"),
            "link": st.column_config.TextColumn("Link"),
            "sort_order": st.column_config.NumberColumn("Order", step=10, default=500),
            "active": st.column_config.CheckboxColumn("Active", default=True),
        },
    )
    if st.button("Save task list", type="primary"):
        orig_ids = {int(t["id"]) for t in tasks_all}
        kept_ids = set()
        errors = 0
        for _, r in edited.iterrows():
            title = _clean(r.get("title"))
            if not title:
                continue
            cat = _clean(r.get("category")) or "daily"
            stage = _clean(r.get("stage")) if cat == "entry" else None
            if cat == "entry" and not stage:
                stage = "after"
            payload = {
                "title": title, "detail": _clean(r.get("detail")), "category": cat,
                "stage": stage, "link": _clean(r.get("link")),
                "sort_order": int(_clean(r.get("sort_order")) or 500),
                "active": bool(r.get("active")) if _clean(r.get("active")) is not None else True,
            }
            rid = _clean(r.get("id"))
            try:
                if rid is None:
                    sb.table("leadership_tasks").insert(payload).execute()
                else:
                    kept_ids.add(int(rid))
                    sb.table("leadership_tasks").update(payload).eq("id", int(rid)).execute()
            except Exception as e:
                errors += 1
                st.error(f"Couldn't save “{title}”: {e}")
        for rid in orig_ids - kept_ids:
            sb.table("leadership_tasks").delete().eq("id", rid).execute()
        if not errors:
            st.success("Task list saved.")
            st.rerun()

    st.divider()
    st.markdown("#### Leadership names")
    plist = load_people()
    for p in plist:
        a, b = st.columns([4, 1])
        a.write(p["name"] + ("" if p.get("active") else "  *(inactive)*"))
        if b.button("Deactivate" if p.get("active") else "Reactivate", key=f"pp_{p['id']}"):
            sb.table("leadership_people").update({"active": not p.get("active")}).eq("id", p["id"]).execute()
            st.rerun()
    with st.form("add_person", clear_on_submit=True):
        nn = st.text_input("Add a name")
        if st.form_submit_button("Add") and nn.strip():
            try:
                sb.table("leadership_people").insert({"name": nn.strip()}).execute()
                st.rerun()
            except Exception:
                st.error("That name is already on the list.")
