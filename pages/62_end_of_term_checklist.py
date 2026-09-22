"""
62_End_of_Term_Checklist.py
----------------------------
End of Term actions checklist for CLC-LBU staff portal.

Replaces the paper "End of Term actions" sign-off sheet with an interactive
version:
  - Each staff member has their own checklist of standard end-of-term jobs,
    ticks items off, and digitally signs at the end.
  - A shared "Additional Jobs" list is visible to everyone; staff can assign
    themselves (or be assigned by admin) and tick jobs complete.
  - Admin can add/remove staff, add/delete standard + additional jobs, start
    a new term (optionally copying last term's job list as a template), and
    see an at-a-glance overview of who has finished / signed off.

Requires a Supabase project with the tables in eot_checklist_schema.sql.
Uses st.secrets["SUPABASE_URL"] / st.secrets["SUPABASE_KEY"] (same pattern as
the rest of the portal). If your portal has a shared staff_auth.py module for
the staff-level password gate, this file will use it automatically; otherwise
it falls back to a simple password stored in st.secrets["EOT_ADMIN_PASSWORD"].
"""

import streamlit as st
from datetime import datetime, timezone
from supabase import create_client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="End of Term Checklist", page_icon="✅", layout="wide")

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# Try to use the portal's shared staff-level auth module if it exists;
# otherwise fall back to a simple password check.
def admin_gate() -> bool:
    try:
        import staff_auth  # shared module used by other portal tools
        return staff_auth.check_password()
    except ImportError:
        pw = st.text_input("Admin password", type="password", key="eot_admin_pw")
        correct = st.secrets.get("EOT_ADMIN_PASSWORD", "")
        if not correct:
            st.warning("No EOT_ADMIN_PASSWORD set in secrets — admin tab is unlocked for now.")
            return True
        return pw == correct

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def get_terms():
    return sb.table("eot_terms").select("*").order("id", desc=True).execute().data

def get_active_term():
    terms = sb.table("eot_terms").select("*").eq("is_active", True).order("id", desc=True).limit(1).execute().data
    return terms[0] if terms else None

def create_term(label, instructions, meeting_details, copy_jobs_from_term_id=None):
    # deactivate any currently active term
    sb.table("eot_terms").update({"is_active": False}).eq("is_active", True).execute()
    new_term = sb.table("eot_terms").insert({
        "label": label,
        "instructions": instructions,
        "meeting_details": meeting_details,
        "is_active": True,
    }).execute().data[0]

    if copy_jobs_from_term_id:
        std_jobs = sb.table("eot_standard_jobs").select("*").eq("term_id", copy_jobs_from_term_id).order("order_index").execute().data
        for j in std_jobs:
            sb.table("eot_standard_jobs").insert({
                "term_id": new_term["id"],
                "action_text": j["action_text"],
                "order_index": j["order_index"],
            }).execute()
        add_jobs = sb.table("eot_additional_jobs").select("*").eq("term_id", copy_jobs_from_term_id).order("order_index").execute().data
        for j in add_jobs:
            sb.table("eot_additional_jobs").insert({
                "term_id": new_term["id"],
                "action_text": j["action_text"],
                "order_index": j["order_index"],
            }).execute()
    return new_term

def get_staff(active_only=True):
    q = sb.table("eot_staff").select("*").order("name")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data

def add_staff(name):
    sb.table("eot_staff").insert({"name": name.strip()}).execute()

def remove_staff(staff_id):
    sb.table("eot_staff").update({"active": False}).eq("id", staff_id).execute()

def get_standard_jobs(term_id):
    return sb.table("eot_standard_jobs").select("*").eq("term_id", term_id).order("order_index").execute().data

def add_standard_job(term_id, text, order_index):
    sb.table("eot_standard_jobs").insert({"term_id": term_id, "action_text": text, "order_index": order_index}).execute()

def delete_standard_job(job_id):
    sb.table("eot_standard_jobs").delete().eq("id", job_id).execute()

def get_completions(term_id, staff_id):
    rows = sb.table("eot_staff_completions").select("*").eq("term_id", term_id).eq("staff_id", staff_id).execute().data
    return {r["job_id"]: r for r in rows}

def set_completion(term_id, staff_id, job_id, completed):
    existing = sb.table("eot_staff_completions").select("id").eq("term_id", term_id).eq("staff_id", staff_id).eq("job_id", job_id).execute().data
    payload = {"completed": completed, "completed_at": now_iso() if completed else None}
    if existing:
        sb.table("eot_staff_completions").update(payload).eq("id", existing[0]["id"]).execute()
    else:
        payload.update({"term_id": term_id, "staff_id": staff_id, "job_id": job_id})
        sb.table("eot_staff_completions").insert(payload).execute()

def get_signoff(term_id, staff_id):
    rows = sb.table("eot_staff_signoff").select("*").eq("term_id", term_id).eq("staff_id", staff_id).execute().data
    return rows[0] if rows else None

def sign_off(term_id, staff_id, signature_name):
    existing = get_signoff(term_id, staff_id)
    payload = {"signed": True, "signature_name": signature_name, "signed_at": now_iso()}
    if existing:
        sb.table("eot_staff_signoff").update(payload).eq("id", existing["id"]).execute()
    else:
        payload.update({"term_id": term_id, "staff_id": staff_id})
        sb.table("eot_staff_signoff").insert(payload).execute()

def unsign(term_id, staff_id):
    existing = get_signoff(term_id, staff_id)
    if existing:
        sb.table("eot_staff_signoff").update({"signed": False}).eq("id", existing["id"]).execute()

def get_additional_jobs(term_id):
    return sb.table("eot_additional_jobs").select("*").eq("term_id", term_id).order("order_index").execute().data

def add_additional_job(term_id, text, order_index):
    sb.table("eot_additional_jobs").insert({"term_id": term_id, "action_text": text, "order_index": order_index}).execute()

def delete_additional_job(job_id):
    sb.table("eot_additional_assignments").delete().eq("additional_job_id", job_id).execute()
    sb.table("eot_additional_jobs").delete().eq("id", job_id).execute()

def get_assignments(term_id):
    rows = sb.table("eot_additional_assignments").select("*, eot_staff(name)").eq("term_id", term_id).execute().data
    by_job = {}
    for r in rows:
        by_job.setdefault(r["additional_job_id"], []).append(r)
    return by_job

def assign_staff(term_id, job_id, staff_id):
    existing = sb.table("eot_additional_assignments").select("id").eq("additional_job_id", job_id).eq("staff_id", staff_id).execute().data
    if not existing:
        sb.table("eot_additional_assignments").insert({"term_id": term_id, "additional_job_id": job_id, "staff_id": staff_id}).execute()

def unassign_staff(job_id, staff_id):
    sb.table("eot_additional_assignments").delete().eq("additional_job_id", job_id).eq("staff_id", staff_id).execute()

def set_additional_complete(job_id, completed, by_name=""):
    payload = {"completed": completed, "completed_at": now_iso() if completed else None, "completed_by": by_name if completed else ""}
    sb.table("eot_additional_jobs").update(payload).eq("id", job_id).execute()

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("✅ End of Term Checklist")

term = get_active_term()

if term is None:
    st.warning("No active term has been set up yet. An admin needs to create one in the Admin tab below.")

tab_mine, tab_additional, tab_admin = st.tabs(["📋 My Checklist", "🧹 Additional Jobs", "🔐 Admin"])

# ---- My Checklist -----------------------------------------------------

with tab_mine:
    if term:
        st.subheader(term["label"])
        if term.get("instructions"):
            st.info(term["instructions"])
        if term.get("meeting_details"):
            st.markdown(f"**{term['meeting_details']}**")

        staff_list = get_staff()
        if not staff_list:
            st.warning("No staff have been added yet. Ask an admin to add staff in the Admin tab.")
        else:
            names = [s["name"] for s in staff_list]
            picked = st.selectbox("Who are you?", names, key="mine_who")
            staff = next(s for s in staff_list if s["name"] == picked)

            signoff = get_signoff(term["id"], staff["id"])
            is_signed = bool(signoff and signoff["signed"])

            jobs = get_standard_jobs(term["id"])
            completions = get_completions(term["id"], staff["id"])

            if not jobs:
                st.info("No standard checklist items have been set up for this term yet.")
            else:
                done_count = 0
                st.markdown("---")
                for job in jobs:
                    existing = completions.get(job["id"])
                    checked = bool(existing and existing["completed"])
                    if checked:
                        done_count += 1
                    new_val = st.checkbox(job["action_text"], value=checked, key=f"job_{job['id']}_{staff['id']}", disabled=is_signed)
                    if new_val != checked:
                        set_completion(term["id"], staff["id"], job["id"], new_val)
                        st.rerun()

                st.progress(done_count / len(jobs))
                st.caption(f"{done_count} of {len(jobs)} items complete")

            st.markdown("---")
            st.subheader("Sign off")
            if is_signed:
                st.success(f"Signed by **{signoff['signature_name']}** on {signoff['signed_at'][:16].replace('T', ' ')}")
                if st.button("Unlock to make changes"):
                    unsign(term["id"], staff["id"])
                    st.rerun()
            else:
                if jobs and done_count < len(jobs):
                    st.caption("You can still sign even if items are outstanding, but consider finishing the list first.")
                sig_name = st.text_input("Type your full name to sign", key="sig_name_input")
                if st.button("Sign & Submit", type="primary"):
                    if sig_name.strip().lower() == staff["name"].strip().lower():
                        sign_off(term["id"], staff["id"], sig_name.strip())
                        st.rerun()
                    else:
                        st.error(f"Please type your name exactly as selected above ({staff['name']}) to confirm.")
    else:
        st.info("Waiting on an admin to set up the current term.")

# ---- Additional Jobs (shared) -----------------------------------------

with tab_additional:
    if term:
        st.subheader("Additional Jobs — everyone can see this list")
        staff_list = get_staff()
        jobs = get_additional_jobs(term["id"])
        assignments = get_assignments(term["id"])

        if not staff_list:
            st.warning("No staff have been added yet.")
        elif not jobs:
            st.info("No additional jobs have been set up for this term yet.")
        else:
            who_am_i = st.selectbox("Acting as", [s["name"] for s in staff_list], key="additional_who")
            me = next(s for s in staff_list if s["name"] == who_am_i)

            st.markdown("---")
            for job in jobs:
                assigned = assignments.get(job["id"], [])
                assigned_names = [a["eot_staff"]["name"] for a in assigned if a.get("eot_staff")]
                i_am_assigned = me["name"] in assigned_names

                cols = st.columns([4, 3, 2])
                with cols[0]:
                    label = job["action_text"]
                    if job["completed"]:
                        st.markdown(f"~~{label}~~  ✅")
                    else:
                        st.markdown(label)
                with cols[1]:
                    st.caption("Assigned: " + (", ".join(assigned_names) if assigned_names else "Unassigned"))
                    if i_am_assigned:
                        if st.button("Remove myself", key=f"unassign_{job['id']}"):
                            unassign_staff(job["id"], me["id"])
                            st.rerun()
                    else:
                        if st.button("Assign to me", key=f"assign_{job['id']}"):
                            assign_staff(term["id"], job["id"], me["id"])
                            st.rerun()
                with cols[2]:
                    new_complete = st.checkbox("Done", value=job["completed"], key=f"addcomplete_{job['id']}")
                    if new_complete != job["completed"]:
                        set_additional_complete(job["id"], new_complete, by_name=me["name"])
                        st.rerun()
                st.markdown("---")
    else:
        st.info("Waiting on an admin to set up the current term.")

# ---- Admin --------------------------------------------------------------

with tab_admin:
    st.subheader("Admin")
    if admin_gate():

        st.markdown("### Term management")
        terms = get_terms()
        if term:
            st.write(f"**Active term:** {term['label']}")
        with st.expander("Start a new term"):
            new_label = st.text_input("Term label", placeholder="e.g. 2026 Term 4")
            new_instructions = st.text_area("Instructions", value="Please hand this checklist to Annette at check in Friday arvo at 2:15 in the planning room")
            new_meeting = st.text_input("End of term meeting details", placeholder="e.g. End of Term Staff Meeting Wednesday 3:00 start - all Staff Kent Town Hotel")
            copy_from = st.selectbox(
                "Copy job list from",
                ["Start blank"] + [t["label"] for t in terms],
            )
            if st.button("Create new term", type="primary"):
                if new_label.strip():
                    copy_id = None
                    if copy_from != "Start blank":
                        copy_id = next(t["id"] for t in terms if t["label"] == copy_from)
                    create_term(new_label.strip(), new_instructions.strip(), new_meeting.strip(), copy_id)
                    st.success(f"Created and activated '{new_label}'.")
                    st.rerun()
                else:
                    st.error("Give the new term a label first.")

        with st.expander("Past terms (archive)"):
            for t in terms:
                flag = " (active)" if t["is_active"] else ""
                st.write(f"- {t['label']}{flag}")

        st.markdown("---")
        st.markdown("### Staff")
        staff_list = get_staff()
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Add staff member", key="add_staff_name")
            if st.button("Add staff"):
                if new_name.strip():
                    add_staff(new_name)
                    st.rerun()
        with col2:
            if staff_list:
                remove_name = st.selectbox("Remove staff member", [s["name"] for s in staff_list], key="remove_staff_select")
                if st.button("Remove selected staff", type="secondary"):
                    sid = next(s["id"] for s in staff_list if s["name"] == remove_name)
                    remove_staff(sid)
                    st.rerun()

        if term:
            st.markdown("---")
            st.markdown("### Standard checklist items (individual, per staff member)")
            jobs = get_standard_jobs(term["id"])
            for j in jobs:
                c1, c2 = st.columns([5, 1])
                c1.write(j["action_text"])
                if c2.button("Delete", key=f"del_std_{j['id']}"):
                    delete_standard_job(j["id"])
                    st.rerun()
            new_job = st.text_input("Add a standard checklist item", key="new_std_job")
            if st.button("Add item"):
                if new_job.strip():
                    add_standard_job(term["id"], new_job.strip(), len(jobs))
                    st.rerun()

            st.markdown("---")
            st.markdown("### Additional jobs (shared list)")
            add_jobs = get_additional_jobs(term["id"])
            for j in add_jobs:
                c1, c2 = st.columns([5, 1])
                c1.write(j["action_text"])
                if c2.button("Delete", key=f"del_add_{j['id']}"):
                    delete_additional_job(j["id"])
                    st.rerun()
            new_add_job = st.text_input("Add an additional job", key="new_add_job")
            if st.button("Add additional job"):
                if new_add_job.strip():
                    add_additional_job(term["id"], new_add_job.strip(), len(add_jobs))
                    st.rerun()

            st.markdown("---")
            st.markdown("### Overview — who's done what")
            staff_list = get_staff()
            std_jobs = get_standard_jobs(term["id"])
            rows = []
            for s in staff_list:
                comps = get_completions(term["id"], s["id"])
                done = sum(1 for v in comps.values() if v["completed"])
                signoff = get_signoff(term["id"], s["id"])
                rows.append({
                    "Staff": s["name"],
                    "Standard items done": f"{done}/{len(std_jobs)}" if std_jobs else "0/0",
                    "Signed off": "✅ " + signoff["signature_name"] if signoff and signoff["signed"] else "—",
                })
            if rows:
                st.table(rows)
            else:
                st.info("No staff to show yet.")
    else:
        st.caption("Enter the admin password above to manage staff, jobs and terms.")
