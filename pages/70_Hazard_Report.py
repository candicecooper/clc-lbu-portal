"""
70_Hazard_Report.py  —  CLC Potential Hazard Report (replaces the Microsoft Form)

Tabs
  1. Report a Hazard   – open to all staff (same 6 questions as the MS Form + optional photo)
  2. Current Hazards   – open to all staff, read-only list of unresolved hazards
  3. Manage            – Admin & Leadership (confidential password): update status,
                         resolve, register export, email recipients, staff list

On submit an email goes to every active Admin/Leadership recipient.
Unresolved hazards show in the Daily Bulletin via hazard_utils.render_bulletin_hazards().
"""

import io
import uuid
from datetime import date

import os
import sys

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Hazard Report", page_icon="⚠️", layout="wide")

# Find hazard_utils.py whether it sits in the repo root or in /pages
_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import hazard_utils  # noqa: F401
except ModuleNotFoundError:
    st.error("**hazard_utils.py is missing from the GitHub repo.** Upload it to the main (top) folder "
             "of clc-lbu-portal, next to confidential_auth.py, then wait for Render to redeploy.")
    st.stop()

from hazard_utils import (
    LOCATIONS, PHOTO_BUCKET, RISK_EMOJI, RISK_LABELS, RISK_SHORT, STATUSES,
    due_date_for, fetch_hazards, fetch_open_hazards, get_supabase, location_text,
    send_hazard_email, today_adl, _secret,
)


OTHER_NAME = "Other (type name)"


# ------------------------------------------------------------------
# Confidential gate (Admin & Leadership) — uses the portal's shared
# confidential_auth.py, with a fallback so the page never crashes.
# ------------------------------------------------------------------
def confidential_gate() -> bool:
    try:
        import confidential_auth as ca
        for fn_name in ("require_confidential_auth", "require_confidential", "confidential_gate",
                        "check_confidential_password", "check_password", "require_password",
                        "password_gate", "check_auth"):
            fn = getattr(ca, fn_name, None)
            if callable(fn):
                result = fn()
                # Some gates st.stop() themselves; others return True/False
                return result is not False
    except Exception:
        pass

    # Fallback: compare against the confidential password in secrets
    if st.session_state.get("hazard_admin_ok"):
        return True
    pw_secret = _secret("CONFIDENTIAL_PASSWORD", "confidential_password", "confidential.password",
                        "passwords.confidential", "ADMIN_PASSWORD")
    pw = st.text_input("Admin / Leadership password", type="password", key="hz_admin_pw")
    if pw and pw_secret and pw == pw_secret:
        st.session_state["hazard_admin_ok"] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    return False


# ------------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------------
def get_staff_names() -> list[str]:
    try:
        rows = get_supabase().table("hazard_staff").select("name").eq("active", True).order("name").execute().data
        return [r["name"] for r in rows or []]
    except Exception:
        return []


def get_recipients(active_only=True) -> list[dict]:
    q = get_supabase().table("hazard_recipients").select("*").order("role").order("name")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data or []


def portal_page_url() -> str | None:
    base = _secret("PORTAL_URL", "portal.url", default="https://clc-lbu-portal.onrender.com")
    return f"{base.rstrip('/')}/Hazard_Report" if base else None


def upload_photos(files) -> list[str]:
    paths = []
    if not files:
        return paths
    sb = get_supabase()
    for f in files:
        ext = (f.name.rsplit(".", 1)[-1] if "." in f.name else "jpg").lower()
        path = f"{today_adl():%Y/%m}/{uuid.uuid4().hex}.{ext}"
        try:
            sb.storage.from_(PHOTO_BUCKET).upload(path, f.getvalue(), {"content-type": f.type or "image/jpeg"})
            paths.append(path)
        except Exception as e:
            st.warning(f"Photo '{f.name}' could not be uploaded ({e}). The report will still be saved.")
    return paths


def photo_urls(paths) -> list[str]:
    urls = []
    for p in paths or []:
        try:
            res = get_supabase().storage.from_(PHOTO_BUCKET).create_signed_url(p, 3600)
            url = res.get("signedURL") or res.get("signedUrl") if isinstance(res, dict) else None
            if url:
                urls.append(url)
        except Exception:
            pass
    return urls


def risk_badge(risk: str) -> str:
    return f"{RISK_EMOJI.get(risk, '⚠️')} {risk}"


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("⚠️ CLC Potential Hazard Report")
st.caption("To be used by staff when a hazard has been identified across the site to action a WHS response. "
           "Please report hazards on the same day they are sighted.")

try:
    get_supabase()
except Exception as e:
    st.error(f"Could not connect to the database: {e}")
    st.stop()

tab_report, tab_current, tab_manage = st.tabs(["📝 Report a Hazard", "📋 Current Hazards", "🔒 Manage (Admin & Leadership)"])


# ==================================================================
# TAB 1 — REPORT
# ==================================================================
with tab_report:
    if st.session_state.get("hz_submitted"):
        info = st.session_state.pop("hz_submitted")
        st.success(f"Thank you — hazard #{info['id']} has been reported. It will show in the Daily Bulletin "
                   "until it is resolved.")
        (st.info if info["email_ok"] else st.warning)(info["email_msg"])
        if info["risk"] == "Urgent":
            st.error("**URGENT:** please now report this directly to Leadership in person or by phone.")

    staff = get_staff_names()
    staff_options = ["— select —"] + staff + [OTHER_NAME]

    with st.form("hazard_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            d_sighted = st.date_input("1. Date potential hazard sighted *", value=today_adl(),
                                      max_value=today_adl(), format="DD/MM/YYYY")
        with c2:
            reporter = st.selectbox("2. Reporter's full name *", staff_options)
            reporter_other = st.text_input("If 'Other', type your full name")

        c3, c4 = st.columns(2)
        with c3:
            loc = st.selectbox("3. Location of hazard *", ["— select —"] + LOCATIONS)
        with c4:
            loc_other = st.text_input("If 'Other', describe the location")

        hazard = st.text_input("4. What is the potential hazard? *", max_chars=150,
                               placeholder="e.g. Loose paver near Shed 2 door")
        explanation = st.text_area("5. Further explanation of concern", height=100)

        risk_label = st.radio("6. Level of risk *", RISK_LABELS, index=None)
        risk_other = st.text_input("If 'Other', describe the level of risk")

        photos = st.file_uploader("Photo(s) of the hazard (optional)", type=["jpg", "jpeg", "png", "heic", "webp"],
                                  accept_multiple_files=True)

        submitted = st.form_submit_button("Submit hazard report", type="primary", use_container_width=True)

    if submitted:
        name = reporter_other.strip() if reporter == OTHER_NAME else (reporter if reporter != "— select —" else "")
        errors = []
        if not name:
            errors.append("Reporter's name")
        if loc == "— select —":
            errors.append("Location")
        if loc == "Other" and not loc_other.strip():
            errors.append("Description of the 'Other' location")
        if not hazard.strip():
            errors.append("What the hazard is")
        if not risk_label:
            errors.append("Level of risk")
        if errors:
            st.error("Please complete: " + ", ".join(errors))
        else:
            risk = RISK_SHORT[risk_label]
            row = {
                "date_sighted": d_sighted.isoformat(),
                "reporter_name": name,
                "location": loc,
                "location_other": loc_other.strip() or None,
                "hazard": hazard.strip(),
                "explanation": explanation.strip() or None,
                "risk_level": risk,
                "risk_other": risk_other.strip() or None,
                "due_date": due_date_for(risk, d_sighted).isoformat(),
                "status": "Open",
            }
            with st.spinner("Saving report and alerting Admin & Leadership…"):
                row["photo_paths"] = upload_photos(photos)
                try:
                    saved = get_supabase().table("hazard_reports").insert(row).execute().data[0]
                except Exception as e:
                    st.error(f"The report could not be saved: {e}. Please tell Admin or Leadership directly.")
                    st.stop()
                try:
                    emails = [r["email"] for r in get_recipients()]
                except Exception:
                    emails = []
                ok, msg = send_hazard_email(saved, emails, portal_page_url())
                if ok:
                    try:
                        get_supabase().table("hazard_reports").update({"email_sent": True}).eq("id", saved["id"]).execute()
                    except Exception:
                        pass
                else:
                    msg += " Your report IS saved — please let Admin or Leadership know directly."
            st.session_state["hz_submitted"] = {"id": saved["id"], "email_ok": ok, "email_msg": msg, "risk": risk}
            st.rerun()


# ==================================================================
# TAB 2 — CURRENT HAZARDS (read-only)
# ==================================================================
with tab_current:
    try:
        open_rows = fetch_open_hazards()
    except Exception as e:
        open_rows = []
        st.error(f"Could not load hazards: {e}")

    if not open_rows:
        st.success("✅ No open hazards on site.")
    else:
        st.write(f"**{len(open_rows)} hazard(s) not yet resolved.** Please take care around these areas.")
        today = today_adl()
        for r in open_rows:
            overdue = r.get("due_date") and date.fromisoformat(r["due_date"]) < today
            flag = " 🚩 **OVERDUE**" if overdue else ""
            st.markdown(f"{risk_badge(r['risk_level'])} — **{location_text(r)}**: {r['hazard']}  \n"
                        f"<span style='color:#888;font-size:0.9em'>Status: {r['status']} · "
                        f"sighted {date.fromisoformat(r['date_sighted']):%d/%m/%Y}</span>{flag}",
                        unsafe_allow_html=True)


# ==================================================================
# TAB 3 — MANAGE (Admin & Leadership)
# ==================================================================
with tab_manage:
    if not confidential_gate():
        st.info("Admin and Leadership only.")
    else:
        m_open, m_register, m_settings = st.tabs(["🛠️ Open hazards", "📚 Hazard register", "⚙️ Settings"])

        # ---------- Open hazards ----------
        with m_open:
            try:
                rows = fetch_open_hazards()
            except Exception as e:
                rows = []
                st.error(f"Could not load hazards: {e}")
            if not rows:
                st.success("✅ Nothing to action.")
            today = today_adl()
            for r in rows:
                due = date.fromisoformat(r["due_date"]) if r.get("due_date") else None
                overdue = due and due < today
                title = (f"{'🚩 ' if overdue else ''}#{r['id']} · {risk_badge(r['risk_level'])} · "
                         f"{location_text(r)} — {r['hazard'][:60]} · {r['status']}")
                with st.expander(title, expanded=bool(overdue) or r["risk_level"] in ("Urgent", "Extremely High")):
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        st.markdown(f"**Hazard:** {r['hazard']}")
                        if r.get("explanation"):
                            st.markdown(f"**Further explanation:** {r['explanation']}")
                        risk_txt = r["risk_level"] + (f" – {r['risk_other']}" if r.get("risk_other") else "")
                        st.markdown(f"**Risk:** {risk_txt}  \n"
                                    f"**Respond by:** {due:%d/%m/%Y}" + (" 🚩 overdue" if overdue else "") + "  \n"
                                    f"**Reported by:** {r['reporter_name']} · sighted "
                                    f"{date.fromisoformat(r['date_sighted']):%d/%m/%Y}  \n"
                                    f"**Email alert:** {'sent ✅' if r.get('email_sent') else 'not sent ⚠️'}")
                        urls = photo_urls(r.get("photo_paths"))
                        if urls:
                            st.image(urls, width=220)
                    with c2:
                        with st.form(f"upd_{r['id']}"):
                            status = st.selectbox("Status", STATUSES, index=STATUSES.index(r["status"]))
                            action = st.text_area("Action taken", value=r.get("action_taken") or "", height=90)
                            ventia = st.text_input("Ventia work order no. (optional)", value=r.get("ventia_wo") or "")
                            by = st.text_input("Updated / resolved by", value=r.get("resolved_by") or "")
                            if st.form_submit_button("Save", type="primary"):
                                if status == "Resolved" and (not action.strip() or not by.strip()):
                                    st.error("To resolve, enter the action taken and who resolved it.")
                                else:
                                    upd = {
                                        "status": status,
                                        "action_taken": action.strip() or None,
                                        "ventia_wo": ventia.strip() or None,
                                        "resolved_by": by.strip() or None,
                                        "resolved_date": today.isoformat() if status == "Resolved" else None,
                                        "updated_at": pd.Timestamp.utcnow().isoformat(),
                                    }
                                    get_supabase().table("hazard_reports").update(upd).eq("id", r["id"]).execute()
                                    st.success("Saved." + (" Removed from the Daily Bulletin." if status == "Resolved" else ""))
                                    st.rerun()
                    if not r.get("email_sent"):
                        if st.button("Resend email alert", key=f"resend_{r['id']}"):
                            ok, msg = send_hazard_email(r, [x["email"] for x in get_recipients()], portal_page_url())
                            if ok:
                                get_supabase().table("hazard_reports").update({"email_sent": True}).eq("id", r["id"]).execute()
                            (st.success if ok else st.error)(msg)

        # ---------- Register ----------
        with m_register:
            try:
                all_rows = fetch_hazards()
            except Exception as e:
                all_rows = []
                st.error(f"Could not load register: {e}")
            if not all_rows:
                st.info("No hazards recorded yet.")
            else:
                df = pd.DataFrame(all_rows)
                df["Location"] = [location_text(r) for r in all_rows]
                view = df.rename(columns={
                    "id": "ID", "date_sighted": "Date sighted", "reporter_name": "Reported by",
                    "hazard": "Hazard", "explanation": "Further explanation", "risk_level": "Risk",
                    "due_date": "Respond by", "status": "Status", "action_taken": "Action taken",
                    "ventia_wo": "Ventia WO", "resolved_by": "Resolved by", "resolved_date": "Resolved date",
                }).reindex(columns=["ID", "Date sighted", "Location", "Hazard", "Further explanation", "Risk",
                                    "Respond by", "Status", "Action taken", "Ventia WO", "Resolved by",
                                    "Resolved date", "Reported by"])

                f1, f2 = st.columns(2)
                s_filter = f1.multiselect("Status", STATUSES, default=STATUSES)
                l_filter = f2.multiselect("Location", sorted(view["Location"].dropna().unique()))
                shown = view[view["Status"].isin(s_filter)]
                if l_filter:
                    shown = shown[shown["Location"].isin(l_filter)]
                st.dataframe(shown, use_container_width=True, hide_index=True)

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                    shown.to_excel(xw, index=False, sheet_name="Hazard Register")
                    ws = xw.sheets["Hazard Register"]
                    for col in ws.columns:
                        width = min(max(len(str(c.value or "")) for c in col) + 2, 50)
                        ws.column_dimensions[col[0].column_letter].width = width
                st.download_button("⬇️ Download WHS hazard register (Excel)", buf.getvalue(),
                                   file_name=f"CLC_Hazard_Register_{today_adl():%Y-%m-%d}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # ---------- Settings ----------
        with m_settings:
            st.subheader("📧 Email recipients")
            st.caption("Every active recipient is emailed for every new hazard report, at every risk level.")
            try:
                recips = get_recipients(active_only=False)
            except Exception as e:
                recips = []
                st.error(f"Could not load recipients: {e}")
            for rc in recips:
                c1, c2, c3, c4 = st.columns([3, 4, 2, 2])
                c1.write(rc["name"])
                c2.write(rc["email"])
                c3.write(rc["role"])
                new_active = c4.checkbox("Active", value=rc["active"], key=f"rc_act_{rc['id']}")
                if new_active != rc["active"]:
                    get_supabase().table("hazard_recipients").update({"active": new_active}).eq("id", rc["id"]).execute()
                    st.rerun()
            with st.form("add_recipient", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 4, 2])
                rn = c1.text_input("Name")
                re_ = c2.text_input("Email")
                rr = c3.selectbox("Role", ["Leadership", "Admin"])
                if st.form_submit_button("Add recipient"):
                    if rn.strip() and "@" in re_:
                        get_supabase().table("hazard_recipients").insert(
                            {"name": rn.strip(), "email": re_.strip(), "role": rr}).execute()
                        st.rerun()
                    else:
                        st.error("Enter a name and a valid email.")
            if recips and st.button("Send a test email to all active recipients"):
                test = {"risk_level": "Low", "location": "Other", "location_other": "TEST – please ignore",
                        "hazard": "Test of the hazard email alert", "date_sighted": today_adl().isoformat(),
                        "due_date": today_adl().isoformat(), "reporter_name": "Portal test", "photo_paths": []}
                ok, msg = send_hazard_email(test, [r["email"] for r in recips if r["active"]], portal_page_url())
                (st.success if ok else st.error)(msg)

            st.divider()
            st.subheader("👥 Reporter name list")
            st.caption("Names in the 'Reporter's full name' dropdown. Staff can still choose 'Other' and type a name.")
            try:
                srows = get_supabase().table("hazard_staff").select("*").order("name").execute().data or []
            except Exception as e:
                srows = []
                st.error(f"Could not load staff list: {e}")
            for s in srows:
                c1, c2 = st.columns([6, 2])
                c1.write(s["name"])
                act = c2.checkbox("Active", value=s["active"], key=f"st_act_{s['id']}")
                if act != s["active"]:
                    get_supabase().table("hazard_staff").update({"active": act}).eq("id", s["id"]).execute()
                    st.rerun()
            with st.form("add_staff", clear_on_submit=True):
                names = st.text_area("Add names (one per line)")
                if st.form_submit_button("Add to list"):
                    new = [n.strip() for n in names.splitlines() if n.strip()]
                    existing = {s["name"].lower() for s in srows}
                    new = [n for n in new if n.lower() not in existing]
                    if new:
                        get_supabase().table("hazard_staff").insert([{"name": n} for n in new]).execute()
                        st.rerun()
