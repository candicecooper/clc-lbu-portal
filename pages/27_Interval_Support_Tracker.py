# ════════════════════════════════════════════════════════════════════════════
# 27_Interval_Support_Tracker.py  ·  CLC-LBU Portal
# Window of Tolerance interval tracker — regulation state + support per slot
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from auth import require_auth, logout_button, get_staff_name
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

TEAL  = "#1A6B8A"
AMBER = "#D4860A"

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f8fa; }
.clc-header {
    background:linear-gradient(135deg,#1A6B8A 0%,#1A6B8ABB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}
.clc-header h2 { margin:0; font-size:1.25rem; }
.clc-header p  { margin:.2rem 0 0; opacity:.85; font-size:.78rem; }
.grid-wrap { overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:.6rem; }
.sg { width:100%; border-collapse:collapse; font-size:.78rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.35rem .45rem;
    text-align:center; font-size:.68rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:48px; }
.sg td { padding:.22rem .3rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; font-size:.72rem; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.7rem; white-space:nowrap; background:#f8fafc; padding:.22rem .5rem; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
       padding:.4rem .7rem; text-align:center; margin-bottom:.35rem; }
.kpi .val { font-size:1.3rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.65rem; color:#666; }
.kpi-g { border-color:#16a34a; } .kpi-g .val { color:#16a34a; }
.kpi-y { border-color:#ca8a04; } .kpi-y .val { color:#ca8a04; }
.kpi-r { border-color:#dc2626; } .kpi-r .val { color:#dc2626; }
.kpi-b { border-color:#2563eb; } .kpi-b .val { color:#2563eb; }
.rec-bar {
    background:#EBF4F9; border:1.5px solid #1A6B8A; border-radius:8px;
    padding:.45rem 1rem; margin:.3rem 0 .5rem; font-size:.85rem;
}
</style>
""", unsafe_allow_html=True)

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

# 15-minute intervals 9:00 to 14:30
def _gen_slots():
    slots = []
    t = 9 * 60
    while t <= 14 * 60 + 30:
        slots.append(f"{t//60}:{t%60:02d}")
        t += 15
    return slots
SLOT_TIMES = _gen_slots()

REG_STATES = {
    "in_window":    {"label": "In window",    "emoji": "🟢", "short": "W",   "bg": "#dcfce7", "fg": "#16a34a", "desc": "Regulated — learning ready"},
    "coping":       {"label": "Coping",        "emoji": "🟡", "short": "C",   "bg": "#fef9c3", "fg": "#ca8a04", "desc": "At edge — strategies working"},
    "hyperaroused": {"label": "Hyperaroused",  "emoji": "🔴", "short": "H+",  "bg": "#fee2e2", "fg": "#dc2626", "desc": "Above window — fight/flight"},
    "hypoaroused":  {"label": "Hypoaroused",   "emoji": "🔵", "short": "H-",  "bg": "#dbeafe", "fg": "#2563eb", "desc": "Below window — shutdown/freeze"},
}

SUPPORT_TYPES = [
    "None", "1:1 SSO", "1:1 Teacher", "Small group",
    "Visual supports", "Modified task", "Sensory break", "Peer support",
]

GROUPING_TYPES = {
    "1:1":         "1:1",
    "independent": "Independent",
    "small_group": "Small group",
    "large_group": "Large group (≤10)",
}

ACTIVITY_TYPES = [
    "Structured",
    "Unstructured",
    "Yard play",
    "Preferred task",
    "Non-preferred task",
]

OUTCOMES = {
    "on_task":   {"label": "On task",   "short": "T", "bg": "#dcfce7", "fg": "#16a34a"},
    "partial":   {"label": "Partial",   "short": "P", "bg": "#fef9c3", "fg": "#ca8a04"},
    "escalated": {"label": "Escalated", "short": "E", "bg": "#fee2e2", "fg": "#dc2626"},
}


def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


def load_known_students():
    """Returns students with interval data, excluding archived ones."""
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("interval_support_observations").select("student_name").execute()
        all_names = sorted({r["student_name"] for r in (res.data or [])
                            if r.get("student_name","").strip()})
        try:
            ar = sb.table("interval_archived_students") \
                   .select("student_name").eq("archived", True).execute()
            archived = {r["student_name"] for r in (ar.data or [])}
            all_names = [n for n in all_names if n not in archived]
        except Exception:
            pass
        return all_names
    except Exception:
        return []


def load_week_obs(student_name, week_start, week_end):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_support_observations")
               .select("*").eq("student_name", student_name)
               .gte("obs_date", str(week_start)).lte("obs_date", str(week_end)).execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error("Load error: " + str(e)); return pd.DataFrame()


def load_all_obs(student_name):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_support_observations")
               .select("*").eq("student_name", student_name)
               .order("obs_date").order("time_slot").execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception:
        return pd.DataFrame()


def upsert_field(student_name, sel_date, sel_day, sel_time, field, value):
    sb = get_sb()
    if not sb: return False
    try:
        ex = (sb.table("interval_support_observations")
              .select("id").eq("student_name", student_name)
              .eq("obs_date", sel_date.isoformat()).eq("time_slot", sel_time)
              .limit(1).execute())
        if ex.data:
            sb.table("interval_support_observations").update(
                {field: value}).eq("id", ex.data[0]["id"]).execute()
        else:
            sb.table("interval_support_observations").insert({
                "student_name": student_name,
                "obs_date":     sel_date.isoformat(),
                "day_of_week":  sel_day,
                "time_slot":    sel_time,
                "regulated":    "",
                field:          value,
                "created_by":   get_staff_name(),
            }).execute()
        return True
    except Exception as e:
        st.error("Save failed: " + str(e)); return False


def clear_interval(student_name, sel_date, sel_time):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("interval_support_observations").delete()\
          .eq("student_name", student_name).eq("obs_date", sel_date.isoformat())\
          .eq("time_slot", sel_time).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("ist_name", ""),
    ("ist_week", date.today() - timedelta(days=date.today().weekday())),
    ("ist_sel_time", SLOT_TIMES[0]),
    ("ist_sel_day",  DAYS[min(date.today().weekday(), 4)]),
]:
    if k not in ss: ss[k] = v


st.markdown("""
<div class="clc-header">
  <h2>🔵 Interval Support Tracker</h2>
  <p>Window of Tolerance — regulation state &amp; support per 15-minute interval
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)

# ── Student selector ──────────────────────────────────────────────────────────
known = load_known_students()

if not ss.ist_name:
    st.markdown("#### Select or add a student")

    if known:
        opts = ["— select existing —"] + known
        sel_opt = st.selectbox("Existing students", opts, index=0, key="ist_sel_opt")
        if sel_opt != "— select existing —":
            ss.ist_name = sel_opt
            st.rerun()
        st.markdown(
            "<div style='text-align:center;color:#94a3b8;font-size:.82rem;"
            "padding:.4rem 0;'>— or add a new student below —</div>",
            unsafe_allow_html=True)
    else:
        st.info("No students tracked yet. Add the first one below.")

    with st.form("ist_new_student_form", clear_on_submit=True):
        new_n = st.text_input(
            "New student name",
            placeholder="e.g. Alex Smith",
            key="ist_name_inp"
        )
        submitted = st.form_submit_button(
            "▶ Start tracking", type="primary", use_container_width=True
        )
    if submitted:
        if new_n.strip():
            ss.ist_name = new_n.strip()
            st.rerun()
        else:
            st.error("Please enter a student name.")

    st.stop()

student_name = ss.ist_name

# Active student bar
bar1, bar2, bar3 = st.columns([5, 1, 1])
with bar1:
    st.markdown(
        f'<div style="background:#EBF4F9;border:1.5px solid #1A6B8A;border-radius:8px;'
        f'padding:.45rem .9rem;font-weight:700;color:#1A6B8A;font-size:.95rem;">'
        f'👤 {student_name}</div>',
        unsafe_allow_html=True)
with bar2:
    if known and len(known) > 1:
        other = [n for n in known if n != student_name]
        switch = st.selectbox("Switch", ["—"] + other, index=0,
                              key="ist_switch", label_visibility="collapsed")
        if switch != "—":
            ss.ist_name = switch
            st.rerun()
with bar3:
    if st.button("+ New", key="ist_new", use_container_width=True):
        ss.ist_name = ""
        st.rerun()

# ── Archive management ───────────────────────────────────────────────────
with st.expander("🗄️ Archive / manage student data", expanded=False):
    arch_tabs = st.tabs(["Archive a student", "View archived students"])

    with arch_tabs[0]:
        st.caption(
            "Archiving moves a student out of the active list. "
            "Their data is preserved and can be restored at any time."
        )
        if not known:
            st.info("No students with data yet.")
        else:
            arch_name = st.selectbox("Select student to archive",
                                     known, key="ist_arch_sel")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🗄️ Archive this student", key="ist_arch_btn",
                             use_container_width=True, type="secondary"):
                    sb = get_sb()
                    if sb:
                        try:
                            sb.table("interval_archived_students").upsert(
                                {"student_name": arch_name, "archived": True},
                                on_conflict="student_name"
                            ).execute()
                            if ss.ist_name == arch_name:
                                ss.ist_name = ""
                            st.success(f"✅ {arch_name} archived.")
                            st.rerun()
                        except Exception as e:
                            st.error("Could not archive: " + str(e))
            with col_b:
                if st.button("🗑️ Delete ALL data for this student", key="ist_del_btn",
                             use_container_width=True, type="secondary"):
                    ss["ist_confirm_del"] = arch_name
                    st.rerun()

            if ss.get("ist_confirm_del") == arch_name:
                st.warning(f"⚠️ This permanently deletes all interval data for **{arch_name}**.")
                confirm = st.text_input("Type the student name to confirm",
                                        key="ist_del_confirm")
                if st.button("Confirm delete", key="ist_del_confirm_btn", type="secondary"):
                    if confirm.strip().lower() == arch_name.lower():
                        sb = get_sb()
                        if sb:
                            try:
                                sb.table("interval_support_observations").delete() \
                                  .eq("student_name", arch_name).execute()
                                try:
                                    sb.table("interval_archived_students").delete() \
                                      .eq("student_name", arch_name).execute()
                                except Exception:
                                    pass
                                ss.pop("ist_confirm_del", None)
                                if ss.ist_name == arch_name:
                                    ss.ist_name = ""
                                st.success(f"✅ All data for {arch_name} deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error("Delete failed: " + str(e))
                    else:
                        st.error("Name does not match.")

    with arch_tabs[1]:
        sb = get_sb()
        archived_names = []
        if sb:
            try:
                ar = sb.table("interval_archived_students") \
                       .select("student_name").eq("archived", True).execute()
                archived_names = [r["student_name"] for r in (ar.data or [])]
            except Exception:
                pass

        if not archived_names:
            st.info("No archived students.")
        else:
            st.markdown(f"**{len(archived_names)} archived student(s):**")
            for aname in archived_names:
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                with ac1:
                    st.markdown(f"**{aname}**")
                with ac2:
                    if st.button("Restore", key=f"restore_{aname}",
                                 use_container_width=True):
                        try:
                            sb.table("interval_archived_students").update(
                                {"archived": False}
                            ).eq("student_name", aname).execute()
                            st.success(f"✅ {aname} restored.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with ac3:
                    if st.button("View data", key=f"view_arch_{aname}",
                                 use_container_width=True):
                        ss.ist_name = aname
                        st.rerun()

st.markdown("---")
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis"])

# ════════════════════════════════════════════════════════════════════════════
# RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:
    week_start = ss.ist_week
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())
    is_this    = week_start == this_week

    # Week nav
    wc1,wc2,wc3,wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", key="ist_prev", use_container_width=True):
            ss.ist_week -= timedelta(weeks=1); st.rerun()
    with wc2:
        st.markdown(
            f'<div style="text-align:center;padding:.35rem 0;font-weight:700;'
            f'color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>', unsafe_allow_html=True)
    with wc3:
        if st.button("Next →", key="ist_next", use_container_width=True):
            ss.ist_week += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", key="ist_today", use_container_width=True):
            ss.ist_week = this_week; st.rerun()

    week_df   = load_week_obs(student_name, week_start, week_end)
    day_dates = {DAYS[i]: (week_start+timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day = DAYS[min(date.today().weekday(), 4)]

    # Build cell lookup
    cell_data = {}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t = row.get("time_slot",""); d = row.get("day_of_week","")
            if not t or not d: continue
            if t not in cell_data: cell_data[t] = {}
            cell_data[t][d] = row.to_dict()

    # Initialise selected cell
    from datetime import datetime as _dt
    _now_m = _dt.now().hour*60 + _dt.now().minute
    _nearest = min(SLOT_TIMES, key=lambda t: abs(int(t.split(":")[0])*60+int(t.split(":")[1])-_now_m))
    if ss.ist_sel_time not in SLOT_TIMES: ss.ist_sel_time = _nearest
    if ss.ist_sel_day  not in DAYS:       ss.ist_sel_day  = today_day

    sel_time = ss.ist_sel_time
    sel_day  = ss.ist_sel_day
    sel_date = week_start + timedelta(days=DAYS.index(sel_day))

    # ── Legend ────────────────────────────────────────────────────────────
    leg_parts = " &nbsp;".join(
        f'<span style="background:{v["bg"]};color:{v["fg"]};padding:.1rem .4rem;'
        f'border-radius:6px;font-weight:700;font-size:.68rem;">{v["short"]}</span>'
        f'<span style="font-size:.68rem;color:#475569;"> {v["emoji"]} {v["label"]}</span>'
        for v in REG_STATES.values()
    )
    st.markdown(f'<div style="margin:.15rem 0 .4rem;display:flex;flex-wrap:wrap;gap:.25rem;">'
                f'{leg_parts}</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # INTERACTIVE GRID — each cell is a Streamlit button
    # ════════════════════════════════════════════════════════════════════
    hdr_cols = st.columns([1.2] + [1]*5)
    with hdr_cols[0]:
        st.markdown(
            '<div style="font-size:.68rem;font-weight:700;color:white;'
            'background:#1A6B8A;border-radius:6px;padding:.3rem .4rem;'
            'text-align:center;">Time</div>', unsafe_allow_html=True)
    for di, d in enumerate(DAYS):
        d_date   = week_start + timedelta(days=di)
        is_td    = (d == today_day and is_this)
        is_sd    = (d == sel_day)
        bg       = "#0f3d5c" if is_td else ("#1d5a7a" if is_sd else "#1A6B8A")
        border   = "3px solid #fbbf24" if is_sd else "none"
        with hdr_cols[di+1]:
            st.markdown(
                f'<div style="font-size:.68rem;font-weight:700;color:white;'
                f'background:{bg};border-radius:6px;padding:.3rem .4rem;'
                f'text-align:center;border:{border};">'
                f'{d[:3]}<br><span style="font-weight:400;font-size:.6rem;">'
                f'{d_date.strftime("%-d/%m")}</span></div>',
                unsafe_allow_html=True)

    for t in SLOT_TIMES:
        row_cols = st.columns([1.2] + [1]*5)

        is_sel_time = (t == sel_time)
        with row_cols[0]:
            st.markdown(
                f'<div style="font-size:.72rem;font-weight:{"700" if is_sel_time else "500"};'
                f'color:{TEAL if is_sel_time else "#475569"};'
                f'background:{"#EBF4F9" if is_sel_time else "#f8fafc"};'
                f'border-radius:6px;padding:.28rem .4rem;text-align:center;'
                f'border:{"1.5px solid "+TEAL if is_sel_time else "1px solid #e2e8f0"};">'
                f'{t}</div>', unsafe_allow_html=True)

        for di, d in enumerate(DAYS):
            cell    = cell_data.get(t,{}).get(d,{})
            reg     = cell.get("regulated","") or ""
            grp     = cell.get("grouping_type","") or ""
            cfg     = REG_STATES.get(reg,{})
            is_this_cell = (t == sel_time and d == sel_day)

            if reg:
                bg_c   = cfg.get("bg","#f1f5f9")
                fg_c   = cfg.get("fg","#334155")
                sh     = cfg.get("short","·")
                grp_lbl = GROUPING_TYPES.get(grp,"")[:3] if grp else ""
                cell_txt = sh + ("\n" + grp_lbl if grp_lbl else "")
            else:
                bg_c   = "#f8fafc"
                fg_c   = "#cbd5e1"
                cell_txt = "·"

            with row_cols[di+1]:
                btn_clicked = st.button(
                    cell_txt,
                    key=f"gc_{t}_{d}",
                    use_container_width=True,
                    help=f"{t} {d} — {cfg.get('label','(empty)')} {GROUPING_TYPES.get(grp,'')}" if reg else f"{t} {d} — tap to record",
                )
                if btn_clicked:
                    ss.ist_sel_time = t
                    ss.ist_sel_day  = d
                    st.rerun()

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════
    # RECORDING CARD for selected cell
    # ════════════════════════════════════════════════════════════════════
    cur_cell = cell_data.get(sel_time,{}).get(sel_day,{})
    cur_reg  = cur_cell.get("regulated","") or ""
    cur_out  = cur_cell.get("outcome","") or ""
    cur_grp  = cur_cell.get("grouping_type","") or ""
    cur_acts = [a.strip() for a in (cur_cell.get("activity_types","") or "").split(",") if a.strip()]
    cfg_cur  = REG_STATES.get(cur_reg,{})

    banner_fg = cfg_cur.get("fg", TEAL) if cur_reg else TEAL
    banner_bg = cfg_cur.get("bg", "#EBF4F9") if cur_reg else "#EBF4F9"

    st.markdown(
        f'<div style="background:{banner_bg};border:2px solid {banner_fg};'
        f'border-radius:10px;padding:.5rem 1rem;margin-bottom:.5rem;">'
        f'<span style="font-size:.95rem;font-weight:700;color:{banner_fg};">'
        f'📍 {sel_time} · {sel_day} {sel_date.strftime("%-d %b")}'
        + (f'</span> &nbsp;<span style="font-weight:600;color:{banner_fg};">'
           f'{cfg_cur.get("emoji","")} {cfg_cur.get("label","")}</span>' if cur_reg else
           '</span> <span style="color:#94a3b8;font-size:.8rem;">— tap a field to record</span>')
        + '</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:.6rem .9rem;">',
        unsafe_allow_html=True)

    fa1, fa2 = st.columns(2)
    with fa1:
        st.markdown('<div style="font-size:.65rem;font-weight:700;color:#1A6B8A;margin-bottom:.1rem;">'
                    'REGULATION STATE</div>', unsafe_allow_html=True)
        for val, cfg in REG_STATES.items():
            is_sel = (cur_reg == val)
            col_a, col_b = st.columns([5,1]) if is_sel else [st.container(), None]
            if col_b is None:
                if st.button(cfg["emoji"]+" "+cfg["label"],
                             key=f"rf_{val}_{sel_time}_{sel_day}",
                             use_container_width=True,
                             type="secondary", help=cfg["desc"]):
                    upsert_field(student_name, sel_date, sel_day, sel_time,
                                 "regulated", val); st.rerun()
            else:
                with col_a:
                    if st.button(cfg["emoji"]+" "+cfg["label"],
                                 key=f"rf_{val}_{sel_time}_{sel_day}",
                                 use_container_width=True,
                                 type="primary", help=cfg["desc"]):
                        upsert_field(student_name, sel_date, sel_day, sel_time,
                                     "regulated", ""); st.rerun()
                with col_b:
                    pass

    with fa2:
        st.markdown('<div style="font-size:.65rem;font-weight:700;color:#1A6B8A;margin-bottom:.1rem;">'
                    'GROUPING</div>', unsafe_allow_html=True)
        for val, lbl in GROUPING_TYPES.items():
            is_sel = (cur_grp == val)
            if st.button(lbl, key=f"gf_{val}_{sel_time}_{sel_day}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                upsert_field(student_name, sel_date, sel_day, sel_time,
                             "grouping_type", "" if is_sel else val); st.rerun()

    st.markdown('<div style="border-top:1px solid #f1f5f9;margin:.4rem 0;"></div>',
                unsafe_allow_html=True)

    fb1, fb2 = st.columns(2)
    with fb1:
        st.markdown('<div style="font-size:.65rem;font-weight:700;color:#1A6B8A;margin-bottom:.1rem;">'
                    'ACTIVITY <span style="font-weight:400;">(tap multiple)</span></div>',
                    unsafe_allow_html=True)
        for act in ACTIVITY_TYPES:
            is_sel = (act in cur_acts)
            if st.button(act, key=f"af_{act}_{sel_time}_{sel_day}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                new_acts = list(cur_acts)
                if is_sel: new_acts.remove(act)
                else: new_acts.append(act)
                upsert_field(student_name, sel_date, sel_day, sel_time,
                             "activity_types", ",".join(new_acts)); st.rerun()

    with fb2:
        st.markdown('<div style="font-size:.65rem;font-weight:700;color:#1A6B8A;margin-bottom:.1rem;">'
                    'OUTCOME</div>', unsafe_allow_html=True)
        for val, cfg in OUTCOMES.items():
            is_sel = (cur_out == val)
            if st.button(cfg["label"], key=f"of_{val}_{sel_time}_{sel_day}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                upsert_field(student_name, sel_date, sel_day, sel_time,
                             "outcome", "" if is_sel else val); st.rerun()

        if cur_out or cur_reg or cur_grp or cur_acts:
            st.markdown("")
            if st.button("🗑️ Clear interval", key=f"clr_{sel_time}_{sel_day}",
                         use_container_width=True, type="secondary"):
                clear_interval(student_name, sel_date, sel_time); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════

def _slot_to_min(t):
    """Convert 'H:MM' string to minutes-since-midnight."""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 9999


def _groq_hypothesis(prompt_text):
    """Call Groq to generate a clinical hypothesis. Returns None if unavailable."""
    try:
        import requests as _req
        key = st.secrets.get("groq", {}).get("api_key") or st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return None
        resp = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 220,
                "temperature": 0.4,
                "messages": [
                    {"role": "system", "content":
                        "You are a specialist behaviour support practitioner at an alternative education setting "
                        "for students with complex needs. Write a concise, data-grounded clinical hypothesis "
                        "(3–5 sentences, plain English, no bullet points) interpreting the pattern described. "
                        "Acknowledge what the data suggests, note what this means for the student's support needs, "
                        "and identify one key question or recommendation for the team. Do not use the student's "
                        "full name — refer to 'the student'."},
                    {"role": "user", "content": prompt_text},
                ]
            },
            timeout=12,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _rpt_fig(fig, height=380, margin_b=100, margin_l=65, margin_r=30, margin_t=65, font_size=12):
    """
    Return a copy of fig sized and styled for the HTML report.
    Sets explicit width so the chart fills the 820px report column without clipping,
    increases font sizes and margins so axis labels aren't cropped, and turns off
    autosize so Plotly doesn't try to resize to the Streamlit container.
    """
    import copy
    f = copy.deepcopy(fig)
    f.update_layout(
        width=820,
        height=height,
        autosize=False,
        font=dict(size=font_size, family="Arial, sans-serif"),
        margin=dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.04,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
    )
    # Make sure x/y grid lines remain clean
    f.update_xaxes(gridcolor="#e2e8f0", tickfont=dict(size=11))
    f.update_yaxes(gridcolor="#e2e8f0", tickfont=dict(size=11))
    return f


def _hypothesis_box(text, key=None):
    """Render a teal hypothesis card. key stores text in ss for report."""
    if key:
        ss[key] = text
    st.markdown(
        f'<div style="background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:0 8px 8px 0;'
        f'padding:.6rem 1rem;margin:.3rem 0 .7rem;font-size:.82rem;color:#1e3a4a;line-height:1.5;">'
        f'<span style="font-size:.68rem;font-weight:700;color:#1A6B8A;letter-spacing:.05em;">'
        f'🔍 HYPOTHESIS</span><br>{text}</div>',
        unsafe_allow_html=True)


def _generate_questions(data_summary):
    """Call Groq to generate specific investigative questions from data patterns."""
    try:
        import requests as _req
        key = st.secrets.get("groq", {}).get("api_key") or st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return None
        resp = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 400,
                "temperature": 0.5,
                "messages": [
                    {"role": "system", "content":
                        "You are a specialist behaviour support practitioner reviewing interval observation data. "
                        "Based on the patterns in the data, generate exactly 5 specific, practical investigative "
                        "questions the team should ask to better understand the student's regulation. "
                        "Questions must be grounded in the actual data patterns described — reference specific "
                        "times, days, activities, or support arrangements from the data. "
                        "Number each question 1–5. Each question should be one sentence ending in a question mark. "
                        "Do not use bullet points. Do not use the student's full name — say 'the student'. "
                        "Focus on: what is happening at the times/days of best regulation (not just why it's bad), "
                        "what specific tasks or routines occur at those times, "
                        "what staff actions or environments correlate with regulation, "
                        "and what would help the team build on strengths rather than only manage difficulties."},
                    {"role": "user", "content": data_summary},
                ]
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None



    all_obs = load_all_obs(student_name)
    if all_obs.empty:
        st.info("No observations recorded yet."); st.stop()

    fc1, fc2 = st.columns(2)
    with fc1: date_from = st.date_input("From", value=all_obs["obs_date_dt"].min().date(), key="ist_af")
    with fc2: date_to   = st.date_input("To",   value=all_obs["obs_date_dt"].max().date(), key="ist_at")

    filt = all_obs[
        (all_obs["obs_date_dt"].dt.date >= date_from) &
        (all_obs["obs_date_dt"].dt.date <= date_to) &
        (all_obs["regulated"].notna()) &
        (all_obs["regulated"].str.strip() != "")
    ].copy()

    if filt.empty:
        st.info("No regulation data in this range."); st.stop()

    filt["State"]  = filt["regulated"].map({k: v["emoji"]+" "+v["label"] for k,v in REG_STATES.items()})
    colour_map     = {v["emoji"]+" "+v["label"]: v["fg"] for v in REG_STATES.values()}
    state_order    = [v["emoji"]+" "+v["label"] for v in REG_STATES.values()]

    # ── Time frame summary ────────────────────────────────────────────────────
    slot_mins = filt["time_slot"].dropna().apply(_slot_to_min)
    min_slot  = filt.loc[slot_mins.idxmin(), "time_slot"] if not slot_mins.empty else "—"
    max_slot  = filt.loc[slot_mins.idxmax(), "time_slot"] if not slot_mins.empty else "—"
    n_days    = filt["obs_date_dt"].dt.date.nunique()
    date_span = f"{date_from.strftime('%-d %b')} – {date_to.strftime('%-d %b %Y')}"

    st.markdown(
        f'<div style="background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;'
        f'padding:.55rem 1rem;margin-bottom:.6rem;font-size:.82rem;color:#0c4a6e;">'
        f'<strong>📅 Observation window:</strong> {date_span} &nbsp;·&nbsp; '
        f'<strong>{n_days} school day{"s" if n_days != 1 else ""}</strong> with data &nbsp;·&nbsp; '
        f'<strong>Time range recorded: {min_slot} – {max_slot}</strong>'
        f'</div>',
        unsafe_allow_html=True)

    # ── What does "interval" mean? ────────────────────────────────────────────
    st.info(
        "ℹ️ **What is an interval?** Each interval represents one 15-minute observation window "
        "during the school day. Staff record regulation state, grouping, activity type, and outcome "
        "for each interval in which they observe the student. Intervals outside the observation "
        f"window ({min_slot}–{max_slot}) were not collected and are not represented in these charts."
    )

    n_tot  = len(filt)
    n_win  = int((filt["regulated"]=="in_window").sum())
    n_cop  = int((filt["regulated"]=="coping").sum())
    n_hyp  = int((filt["regulated"]=="hyperaroused").sum())
    n_hypo = int((filt["regulated"]=="hypoaroused").sum())

    pct_inwin = round(100*n_win/n_tot) if n_tot else 0
    pct_cop_only = round(100*n_cop/n_tot) if n_tot else 0

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.markdown(f"<div class='kpi'><div class='val'>{n_tot}</div><div class='lbl'>Total intervals<br><span style='font-size:.58rem;'>15-min windows</span></div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-g'><div class='val'>{n_win}</div><div class='lbl'>🟢 In window<br><span style='font-size:.58rem;'>{pct_inwin}%</span></div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-y'><div class='val'>{n_cop}</div><div class='lbl'>🟡 Coping<br><span style='font-size:.58rem;'>{pct_cop_only}% — at edge</span></div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi kpi-r'><div class='val'>{n_hyp}</div><div class='lbl'>🔴 Hyperaroused</div></div>", unsafe_allow_html=True)
    k5.markdown(f"<div class='kpi kpi-b'><div class='val'>{n_hypo}</div><div class='lbl'>🔵 Hypoaroused</div></div>", unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:.8rem;color:#475569;text-align:center;margin:.3rem 0 .2rem;">'
        f'<strong>{pct_inwin}%</strong> of intervals fully within the window of tolerance '
        f'({n_win} of {n_tot}). &nbsp;'
        f'<strong>{pct_cop_only}%</strong> coping (at edge — student is managing but struggling).</div>'
        f'<div style="font-size:.75rem;color:#dc2626;text-align:center;margin:0 0 .6rem;">'
        f'⚠️ Only <em>In window</em> (green) indicates genuine regulation. '
        f'A predominantly yellow day is still a difficult day.</div>',
        unsafe_allow_html=True)

    st.markdown("---")

    # ── Chart 1: Regulation across the day ───────────────────────────────────
    st.markdown("##### 📊 Regulation state across the day")
    st.caption(
        f"Each bar represents one 15-minute time slot. Height = number of intervals recorded at that time. "
        f"Data was collected between **{min_slot}** and **{max_slot}**. "
        f"Colour shows regulation state across all recorded days."
    )
    slot_df = filt.groupby(["time_slot","State"]).size().reset_index(name="n")
    slot_df["sort_k"] = slot_df["time_slot"].apply(_slot_to_min)
    slot_df = slot_df.sort_values("sort_k")
    # Only show states that actually have data
    active_states_slot = [s for s in state_order if s in slot_df["State"].values]
    fig1 = px.bar(slot_df, x="time_slot", y="n", color="State",
        color_discrete_map=colour_map, barmode="stack",
        labels={"time_slot":"Time","n":"Intervals","State":""},
        category_orders={"State": active_states_slot})
    fig1.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(tickangle=-45, gridcolor="#e2e8f0", title=""),
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=55,b=70))
    st.plotly_chart(fig1, use_container_width=True)
    ss["rpt_fig1"] = _rpt_fig(fig1, height=400, margin_b=130, margin_l=70).to_html(full_html=False, include_plotlyjs=False)

    # Hypothesis: time-of-day
    best_slot = slot_df[slot_df["State"].str.contains("In window")].groupby("time_slot")["n"].sum()
    worst_slot_df = slot_df[slot_df["State"].str.contains("Hyperaroused|Hypoaroused")].groupby("time_slot")["n"].sum()
    best_t  = best_slot.idxmax()  if not best_slot.empty  else None
    worst_t = worst_slot_df.idxmax() if not worst_slot_df.empty else None
    hyp1_prompt = (
        f"Student has {n_tot} intervals recorded between {min_slot} and {max_slot} across {n_days} school days. "
        f"Regulation breakdown: {n_win} fully in-window (regulated), {n_cop} coping (at the edge — actively managing but not fully regulated), {n_hyp} hyperaroused, {n_hypo} hypoaroused. "
        f"Note: 'coping' means the student is at the edge of their window and actively managing — it is NOT a successful state. "
        + (f"Time slot with highest in-window count: {best_t}. " if best_t else "")
        + (f"Most dysregulation observed at: {worst_t}. " if worst_t else "")
        + "Interpret this time-of-day pattern and its implications for scheduling and support."
    )
    with st.spinner("Generating hypothesis…"):
        hyp1 = _groq_hypothesis(hyp1_prompt)
    if hyp1:
        _hypothesis_box(hyp1, key="rpt_hyp_time")
    else:
        best_str  = f"Best full regulation is seen at {best_t}. " if best_t else ""
        worst_str = f"Dysregulation is most prominent at {worst_t}. " if worst_t else ""
        _hypothesis_box(
            f"{n_win} of {n_tot} intervals ({round(100*n_win/n_tot) if n_tot else 0}%) were fully within the window of tolerance. "
            + best_str + worst_str +
            "This pattern suggests consideration of scheduling demands and staffing intensity "
            "relative to time of day when planning this student's program.",
            key="rpt_hyp_time"
        )

    st.markdown("---")

    # ── Chart 2: Daily trend (ONLY show lines with actual data) ──────────────
    st.markdown("##### 📈 Daily regulation trend")
    st.caption(
        "Percentage of that day's intervals in each regulation state. "
        "Only states that were actually observed on at least one day appear as lines. "
        "The dashed green line marks the 70% in-window benchmark."
    )
    daily = filt.groupby("obs_date_dt").apply(lambda g: pd.Series({
        "pct_win":  round(100*(g["regulated"]=="in_window").sum()/len(g)),
        "pct_cop":  round(100*(g["regulated"]=="coping").sum()/len(g)),
        "pct_hyp":  round(100*(g["regulated"]=="hyperaroused").sum()/len(g)),
        "pct_hypo": round(100*(g["regulated"]=="hypoaroused").sum()/len(g)),
    })).reset_index()
    daily["date_lbl"] = pd.to_datetime(daily["obs_date_dt"]).dt.strftime("%a %-d %b")
    fig2 = go.Figure()
    trace_map = [
        ("pct_win",  "🟢 In window",    "#16a34a"),
        ("pct_cop",  "🟡 Coping",       "#ca8a04"),
        ("pct_hyp",  "🔴 Hyperaroused", "#dc2626"),
        ("pct_hypo", "🔵 Hypoaroused",  "#2563eb"),
    ]
    for col, name, col_c in trace_map:
        # Only add trace if this state was ever observed (max > 0)
        if daily[col].max() > 0:
            fig2.add_trace(go.Scatter(x=daily["date_lbl"], y=daily[col],
                mode="lines+markers", name=name,
                line=dict(color=col_c, width=2.5), marker=dict(size=7, color=col_c),
                hovertemplate=f"{name}: %{{y}}%<extra></extra>"))
    fig2.add_hline(y=70, line_dash="dot", line_color="#16a34a", line_width=1.5,
                   annotation_text="70% in-window target",
                   annotation_font_color="#16a34a", annotation_position="bottom right")
    fig2.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(range=[0,105], tickformat="d", gridcolor="#e2e8f0",
                   title="% of intervals", ticksuffix="%"),
        xaxis=dict(gridcolor="#e2e8f0", title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=55,b=20), hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)
    ss["rpt_fig2"] = _rpt_fig(fig2, height=360, margin_b=60, margin_l=65).to_html(full_html=False, include_plotlyjs=False)

    st.markdown("---")

    # ── Chart 3: Day of week ──────────────────────────────────────────────────
    st.markdown("##### 📅 Regulation by day of week")
    st.caption(
        "Total intervals per day across the observation period, coloured by regulation state. "
        "Taller bars mean more intervals were recorded on that day. "
        "The colour split shows how regulation varied across days of the week."
    )
    dow = filt.groupby(["day_of_week","State"]).size().reset_index(name="n")
    dow["sort_k"] = dow["day_of_week"].apply(lambda d: DAYS.index(d) if d in DAYS else 9)
    dow = dow.sort_values("sort_k")
    active_states_dow = [s for s in state_order if s in dow["State"].values]
    # Best day = highest % fully IN WINDOW (not coping — coping means struggling)
    dow_win = filt.groupby("day_of_week").apply(
        lambda g: round(100*(g["regulated"] == "in_window").sum()/len(g))
    ).reset_index(name="pct_win")
    dow_cop = filt.groupby("day_of_week").apply(
        lambda g: round(100*(g["regulated"] == "coping").sum()/len(g))
    ).reset_index(name="pct_cop")
    dow_reg = dow_win.merge(dow_cop, on="day_of_week")
    dow_reg["sort_k"] = dow_reg["day_of_week"].apply(lambda d: DAYS.index(d) if d in DAYS else 9)
    dow_reg = dow_reg.sort_values("sort_k")
    best_day  = dow_reg.loc[dow_reg["pct_win"].idxmax(), "day_of_week"] if not dow_reg.empty else None
    worst_day = dow_reg.loc[dow_reg["pct_win"].idxmin(), "day_of_week"] if not dow_reg.empty else None
    best_pct  = dow_reg["pct_win"].max() if not dow_reg.empty else 0
    worst_pct = dow_reg["pct_win"].min() if not dow_reg.empty else 0

    fig4 = px.bar(dow, x="day_of_week", y="n", color="State",
        color_discrete_map=colour_map, barmode="stack",
        labels={"day_of_week":"","n":"Intervals","State":""},
        category_orders={"day_of_week": DAYS, "State": active_states_dow})
    fig4.update_layout(height=280, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0",
                   title="15-min intervals recorded"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig4, use_container_width=True)
    ss["rpt_fig4"] = _rpt_fig(fig4, height=320, margin_b=55, margin_l=65).to_html(full_html=False, include_plotlyjs=False)

    # Build a separate NORMALISED (100% stacked) bar for the report so bar height
    # always reflects the proportion, not raw count — matches the % table below.
    fig4_pct = px.bar(dow, x="day_of_week", y="n", color="State",
        color_discrete_map=colour_map, barmode="relative",
        labels={"day_of_week":"","n":"Intervals","State":""},
        category_orders={"day_of_week": DAYS, "State": active_states_dow})
    fig4_pct.update_layout(barnorm="percent")
    fig4_pct.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="% of intervals",
                   ticksuffix="%", range=[0,105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=50,b=10))
    ss["rpt_fig4_pct"] = _rpt_fig(fig4_pct, height=320, margin_b=55, margin_l=70).to_html(full_html=False, include_plotlyjs=False)

    # Per-day summary under chart
    dow_summary_parts = []
    for _, r in dow_reg.iterrows():
        dow_summary_parts.append(
            f"<strong>{r['day_of_week'][:3]}:</strong> {r['pct_win']}% in-window, {r['pct_cop']}% coping"
        )
    st.markdown(
        '<div style="font-size:.75rem;color:#475569;margin:.2rem 0 .5rem;">'
        + " &nbsp;·&nbsp; ".join(dow_summary_parts) + "</div>",
        unsafe_allow_html=True)
    st.caption(
        "⚠️ 'In window' (green) is the only indicator of genuine regulation. "
        "'Coping' (yellow) means the student is at the edge of their window and actively managing — "
        "a predominantly yellow day still represents a student who is struggling."
    )

    hyp_dow_prompt = (
        f"Student regulation by day of week — % of intervals FULLY IN WINDOW (regulated): "
        + ", ".join(f"{r['day_of_week']} {r['pct_win']}% in-window / {r['pct_cop']}% coping" for _, r in dow_reg.iterrows()) + ". "
        + f"IMPORTANT: 'coping' means the student is at the edge of their window and struggling — it is NOT a successful state. "
        + (f"Best day is {best_day} ({best_pct}% fully in-window). " if best_day else "")
        + (f"Most difficult day is {worst_day} ({worst_pct}% fully in-window). " if worst_day else "")
        + "Interpret this weekly pattern using Window of Tolerance framework. "
          "What might explain why the student is more regulated on certain days? "
          "Pose specific questions the team should investigate about the most difficult day."
    )
    with st.spinner("Generating hypothesis…"):
        hyp_dow = _groq_hypothesis(hyp_dow_prompt)
    if hyp_dow:
        _hypothesis_box(hyp_dow, key="rpt_hyp_dow")
    else:
        _hypothesis_box(
            (f"The student demonstrates the highest proportion of fully regulated intervals on {best_day} ({best_pct}% in-window). " if best_day else "")
            + (f"The most challenging day is {worst_day}, with only {worst_pct}% of intervals reaching full regulation. " if worst_day and worst_day != best_day else "")
            + "Note that days with a high proportion of 'coping' intervals still represent a student who is actively struggling — "
              "coping is the edge of the window, not a position of stability. "
              "The team should investigate what structural differences exist between the best and worst days: "
              "timetable, staffing, peer groupings, and the sequence and demands of activities.",
            key="rpt_hyp_dow"
        )

    st.markdown("---")

    # ── Chart 4: Support / grouping type volume ───────────────────────────────
    sup_filt = filt[
        filt.get("grouping_type", pd.Series(dtype=str)).notna() &
        (filt.get("grouping_type", pd.Series(dtype=str)).str.strip() != "")
    ].copy() if "grouping_type" in filt.columns else pd.DataFrame()

    if not sup_filt.empty:
        st.markdown("##### 👥 Level of support — how often was each grouping recorded?")
        st.caption(
            "Shows the total number of 15-minute intervals recorded under each support/grouping arrangement, "
            "coloured by the regulation state during that interval. "
            "This identifies which support type is most frequently used and how effective it is."
        )
        sup_filt["Grouping"] = sup_filt["grouping_type"].map(GROUPING_TYPES).fillna(sup_filt["grouping_type"])

        # Volume chart: total intervals per grouping, colour = regulation state
        grp_state = sup_filt.groupby(["Grouping","State"]).size().reset_index(name="n")
        active_states_grp = [s for s in state_order if s in grp_state["State"].values]
        fig_grp = px.bar(grp_state, x="n", y="Grouping", color="State",
            color_discrete_map=colour_map, barmode="stack", orientation="h",
            labels={"Grouping":"","n":"Intervals","State":""},
            category_orders={"State": active_states_grp})
        fig_grp.update_layout(height=max(220, len(grp_state["Grouping"].unique())*60+80),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
            margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig_grp, use_container_width=True)
        ss["rpt_fig_grp"] = _rpt_fig(fig_grp, height=max(280, len(grp_state["Grouping"].unique())*80+100), margin_b=60, margin_l=110, margin_r=20).to_html(full_html=False, include_plotlyjs=False)

        # Regulation breakdown table (replaces misleading % heatmap)
        st.markdown("**Regulation breakdown by support type** — counts and percentages")
        st.caption(
            "Shows how many 15-minute intervals were recorded in each regulation state per support arrangement. "
            "⚠️ Rows with fewer than 3 intervals should be interpreted with caution — "
            "a single interval showing 100% in-window or 100% dysregulated reflects only one moment, not a pattern."
        )
        # Build a readable table
        pivot_counts = sup_filt.groupby(["Grouping","State"]).size().unstack(fill_value=0)
        pivot_counts["Total"] = pivot_counts.sum(axis=1)
        ordered_state_cols = [s for s in state_order if s in pivot_counts.columns]
        table_rows = []
        for grp_name, row in pivot_counts.iterrows():
            total = int(row["Total"])
            reliability = "⚠️ low n" if total < 3 else ""
            row_dict = {"Grouping": grp_name, "n (total)": f"{total} {reliability}"}
            for sc in ordered_state_cols:
                cnt = int(row.get(sc, 0))
                pct = round(100*cnt/total) if total else 0
                row_dict[sc] = f"{cnt} ({pct}%)" if cnt > 0 else "—"
            table_rows.append(row_dict)
        tbl_df = pd.DataFrame(table_rows).set_index("Grouping")
        st.dataframe(tbl_df, use_container_width=True)

        # Build summary for hypothesis
        grp_counts = sup_filt["Grouping"].value_counts()
        top_grp    = grp_counts.index[0] if not grp_counts.empty else "unknown"
        top_grp_n  = int(grp_counts.iloc[0]) if not grp_counts.empty else 0
        top_grp_pct = round(100*top_grp_n/len(sup_filt)) if len(sup_filt) else 0
        # Plain-language support summary for report
        support_summary_parts = [f"{g}: {n} interval{'s' if n!=1 else ''} ({round(100*n/len(sup_filt))}%)"
                                  for g, n in grp_counts.items()]
        ss["rpt_support_summary"] = " · ".join(support_summary_parts)
        ss["rpt_top_grp"] = top_grp
        ss["rpt_top_grp_pct"] = top_grp_pct
        # Use in-window only for regulation rate
        grp_win_rates = {}
        for g in sup_filt["Grouping"].unique():
            sub = sup_filt[sup_filt["Grouping"]==g]
            if len(sub) >= 3:
                grp_win_rates[g] = round(100*(sub["regulated"]=="in_window").sum()/len(sub))
        hyp_grp_prompt = (
            f"Student support type distribution across {len(sup_filt)} intervals: "
            + ", ".join(f"{g} ({n} intervals, {round(100*n/len(sup_filt))}%)" for g, n in grp_counts.items()) + ". "
            + f"Most common support arrangement is '{top_grp}' ({top_grp_pct}% of intervals). "
            + ("In-window regulation rates (only rows with ≥3 intervals): "
               + "; ".join(f"{g}: {pct}% in-window" for g, pct in grp_win_rates.items()) + ". "
               if grp_win_rates else "")
            + "Interpret what this reveals about the student's dependence on intensive support, "
              "and what the data implies for resourcing, fading support, or building independence."
        )
        with st.spinner("Generating hypothesis…"):
            hyp_grp = _groq_hypothesis(hyp_grp_prompt)
        if hyp_grp:
            _hypothesis_box(hyp_grp, key="rpt_hyp_grp")
        else:
            _hypothesis_box(
                f"The data shows that {top_grp_pct}% of observed intervals occurred under '{top_grp}' support. "
                "This indicates the current level of support is the primary context in which this student's "
                "regulation is being observed and maintained. The team should consider whether this level of "
                "resourcing is sustainable, what structured plans exist for support-fading, and how the "
                "student's regulation changes in lower-support contexts.",
                key="rpt_hyp_grp"
            )
    else:
        st.info("Record grouping/support data during observations to see this chart.")

    st.markdown("---")

    # ── Chart 5: Activity type vs regulation ─────────────────────────────────
    if "activity_types" in filt.columns:
        act_rows = []
        for _, row in filt.iterrows():
            acts = [a.strip() for a in str(row.get("activity_types","")).split(",") if a.strip()]
            for act in acts:
                act_rows.append({
                    "Activity": act,
                    "State":    row["State"],
                    "Grouping": GROUPING_TYPES.get(row.get("grouping_type",""),"") if row.get("grouping_type") else "",
                })
        if act_rows:
            st.markdown("##### 🎯 Regulation by activity type")
            st.caption(
                "Each bar represents all 15-minute intervals recorded during that activity type. "
                "When an interval has multiple activity types selected, it is counted in each. "
                "Colour shows regulation state during that activity."
            )
            act_df = pd.DataFrame(act_rows)
            adf    = act_df.groupby(["Activity","State"]).size().reset_index(name="n")
            active_states_act = [s for s in state_order if s in adf["State"].values]
            fig6 = px.bar(adf, x="n", y="Activity", color="State",
                color_discrete_map=colour_map, barmode="stack", orientation="h",
                labels={"Activity":"","n":"Intervals","State":""},
                category_orders={"State": active_states_act})
            fig6.update_layout(height=max(220,len(adf["Activity"].unique())*60+80),
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(autorange="reversed"),
                xaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
                margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig6, use_container_width=True)
            ss["rpt_fig6"] = _rpt_fig(fig6, height=max(300, len(adf["Activity"].unique())*80+100), margin_b=60, margin_l=130, margin_r=20).to_html(full_html=False, include_plotlyjs=False)

            # Build hypothesis
            act_counts  = act_df["Activity"].value_counts()
            top_act     = act_counts.index[0] if not act_counts.empty else "unknown"
            act_reg_pct = {}
            for act in act_df["Activity"].unique():
                sub = act_df[act_df["Activity"]==act]
                reg_n = sub["State"].str.contains("In window|Coping").sum()
                act_reg_pct[act] = round(100*reg_n/len(sub)) if len(sub) else 0

            # Support info for top activity
            top_act_grp = act_df[act_df["Activity"]==top_act]["Grouping"].value_counts()
            top_grp_for_act = top_act_grp.index[0] if not top_act_grp.empty else "unrecorded grouping"

            hyp_act_prompt = (
                f"Student activity type data across all intervals: "
                + ", ".join(f"{a} ({n} intervals, {act_reg_pct.get(a,0)}% regulated)" for a, n in act_counts.items()) + ". "
                + f"Most common activity is '{top_act}' — primarily with '{top_grp_for_act}' support. "
                + "Interpret what this reveals about demand tolerance, preferred vs non-preferred tasks, "
                  "and what this implies for curriculum design and support planning. "
                  "Note whether regulation is contingent on activity preference, and question whether "
                  "the student is building capacity for non-preferred tasks."
            )
            with st.spinner("Generating hypothesis…"):
                hyp_act = _groq_hypothesis(hyp_act_prompt)
            if hyp_act:
                _hypothesis_box(hyp_act, key="rpt_hyp_act")
            else:
                best_act  = max(act_reg_pct, key=act_reg_pct.get) if act_reg_pct else None
                worst_act = min(act_reg_pct, key=act_reg_pct.get) if act_reg_pct else None
                _hypothesis_box(
                    f"The majority of observed intervals involved '{top_act}' tasks, predominantly under '{top_grp_for_act}' support. "
                    + (f"Highest in-window regulation was observed during '{best_act}' activities ({act_reg_pct[best_act]}% in-window). " if best_act else "")
                    + (f"Greatest dysregulation occurred during '{worst_act}' activities ({act_reg_pct[worst_act]}% in-window). " if worst_act and worst_act != best_act else "")
                    + "The team should consider whether regulation during preferred or structured tasks "
                      "is contingent on high levels of 1:1 support, and build a plan to gradually "
                      "introduce demand and fade support across this student's program.",
                    key="rpt_hyp_act"
                )
            st.markdown("---")

    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    csv = dl[["obs_date","day_of_week","time_slot","regulated","State",
              "grouping_type","activity_types","outcome","created_by"]].to_csv(index=False)

    st.markdown("---")

    # ── Build data summary for questions generator ────────────────────────────
    # Identify time slots where student is consistently in-window
    slot_win = filt[filt["regulated"]=="in_window"].groupby("time_slot").size()
    slot_tot = filt.groupby("time_slot").size()
    slot_pct_win = (slot_win / slot_tot * 100).fillna(0).round(0)
    strong_slots = slot_pct_win[slot_pct_win >= 70].sort_values(ascending=False)
    weak_slots   = slot_pct_win[slot_pct_win <= 20].sort_values()

    questions_data_summary = (
        f"Student: {student_name}. Observation period: {date_span}. "
        f"Time range: {min_slot}–{max_slot}. Days observed: {n_days}. "
        f"Total intervals: {n_tot}. In-window: {n_win} ({pct_inwin}%). Coping (dysregulated): {n_cop} ({pct_cop_only}%). "
        f"Hyperaroused: {n_hyp}. Hypoaroused: {n_hypo}. "
        + (f"Time slots with ≥70% in-window (consistently regulated): {', '.join(strong_slots.index.tolist())}. " if not strong_slots.empty else "")
        + (f"Time slots with ≤20% in-window (consistently dysregulated): {', '.join(weak_slots.index.tolist())}. " if not weak_slots.empty else "")
        + (f"Best day: {best_day} ({best_pct}% in-window). Worst day: {worst_day} ({worst_pct}% in-window). " if best_day else "")
        + (f"Support distribution: {ss.get('rpt_support_summary','')}. " if ss.get("rpt_support_summary") else "")
        + "Generate 5 specific investigative questions grounded in these patterns."
    )

    # ── Report generator ─────────────────────────────────────────────────────
    with st.expander("📄 Generate analysis report", expanded=False):
        st.caption(
            "Scroll through the Analysis tab first so every chart and hypothesis is generated, "
            "then complete the fields below and click Generate."
        )
        report_title  = st.text_input("Report title",  value=f"Interval Support Analysis — {student_name}", key="rpt_title")
        report_author = st.text_input("Prepared by",   value=get_staff_name() or "", key="rpt_author")
        additional_details = st.text_area(
            "Additional context / staff observations",
            placeholder=(
                "Add any context to be included in the report — e.g. what specific tasks were "
                "running at the times of best regulation, staffing notes, environmental factors, "
                "recent changes to the student's program or home situation, etc."
            ),
            height=120,
            key="rpt_additional"
        )

        if st.button("📄 Generate report", key="rpt_gen_btn", type="primary", use_container_width=True):

            # ── Generate investigative questions ────────────────────────────
            with st.spinner("Generating investigative questions…"):
                questions_text = _generate_questions(questions_data_summary)
            if not questions_text:
                # Rule-based fallback
                q_lines = []
                if not strong_slots.empty:
                    q_lines.append(f"1. What specific tasks or routines are running at {strong_slots.index[0]} each day, given that this is when the student is most consistently within their window?")
                if not weak_slots.empty:
                    q_lines.append(f"2. What is happening at {weak_slots.index[0]} that consistently results in dysregulation — is this a transition point, change of staff, or particular demand?")
                if best_day and worst_day and best_day != worst_day:
                    q_lines.append(f"3. What structural differences exist between {best_day} and {worst_day} in terms of timetable, staffing, and peer grouping that could explain the difference in regulation?")
                q_lines.append(f"4. Given that {ss.get('rpt_top_grp_pct',0)}% of observed intervals involve {ss.get('rpt_top_grp','1:1')} support, what is the plan for building the student's capacity to function in lower-support contexts?")
                q_lines.append("5. Which specific activities or times of regulation could be used as a foundation for gradually introducing demand and building the student's window of tolerance?")
                questions_text = "\n".join(q_lines[:5])

            ss["rpt_questions"] = questions_text

            # Show questions in UI before download
            st.markdown("**Questions generated for this student:**")
            st.info(questions_text)

            # ── Retrieve stored data ────────────────────────────────────────
            hyp_time  = ss.get("rpt_hyp_time", "")
            hyp_dow_  = ss.get("rpt_hyp_dow",  "")
            hyp_grp_  = ss.get("rpt_hyp_grp",  "")
            hyp_act_  = ss.get("rpt_hyp_act",  "")
            fig1_html     = ss.get("rpt_fig1",    "")
            fig2_html     = ss.get("rpt_fig2",    "")
            fig4_html     = ss.get("rpt_fig4",    "")
            fig4_pct_html = ss.get("rpt_fig4_pct","")
            fig_grp_html  = ss.get("rpt_fig_grp", "")
            fig6_html     = ss.get("rpt_fig6",    "")
            support_summary = ss.get("rpt_support_summary", "")
            top_grp      = ss.get("rpt_top_grp", "")
            top_grp_pct  = ss.get("rpt_top_grp_pct", 0)

            missing = [n for n, h in [("Regulation across the day", fig1_html), ("Day of week", fig4_html)] if not h]
            if missing:
                st.warning("⚠️ Some charts missing — scroll through the Analysis tab first: " + ", ".join(missing))

            # ── Inner HTML helpers ──────────────────────────────────────────
            def _hyp_block(text):
                if not text: return ""
                return (
                    '<div class="hyp"><div class="hyp-label">🔍 Hypothesis</div>'
                    f'<p>{text}</p></div>'
                )

            def _chart_block(title, info_text, chart_html, hyp_text=""):
                ch = chart_html or '<p class="no-data">Chart not yet generated — scroll through the Analysis tab and regenerate.</p>'
                return (
                    f'<h2>{title}</h2>'
                    f'<div class="info-box">{info_text}</div>'
                    f'<div class="chart-wrap">{ch}</div>'
                    + _hyp_block(hyp_text)
                )

            # ── Day of week table ───────────────────────────────────────────
            dow_html_table = ""
            if not dow_reg.empty:
                dow_html_table = (
                    '<table><thead><tr>'
                    '<th>Day</th><th>n (intervals)</th>'
                    '<th style="color:#16a34a;">🟢 In window</th>'
                    '<th style="color:#ca8a04;">🟡 Coping ⚠️</th>'
                    '<th style="color:#dc2626;">🔴 Hyperaroused</th>'
                    '<th style="color:#2563eb;">🔵 Hypoaroused</th>'
                    '</tr></thead><tbody>'
                )
                for _, r in dow_reg.iterrows():
                    d   = r["day_of_week"]
                    sub = filt[filt["day_of_week"] == d]
                    tot = len(sub)
                    p_h  = round(100*(sub["regulated"]=="hyperaroused").sum()/tot) if tot else 0
                    p_ho = round(100*(sub["regulated"]=="hypoaroused").sum()/tot)  if tot else 0
                    dow_html_table += (
                        f'<tr><td><strong>{d}</strong></td><td>{tot}</td>'
                        f'<td style="color:#16a34a;font-weight:700;">{r["pct_win"]}%</td>'
                        f'<td style="color:#ca8a04;">{r["pct_cop"]}%</td>'
                        f'<td style="color:#dc2626;">{p_h}%</td>'
                        f'<td style="color:#2563eb;">{p_ho}%</td></tr>'
                    )
                dow_html_table += '</tbody></table>'
                dow_html_table += '<p style="font-size:.75rem;color:#64748b;margin-top:.2rem;">⚠️ Coping = at the edge of the window — the student is struggling to manage, not regulated.</p>'

            # ── Support summary HTML ────────────────────────────────────────
            support_summary_html = ""
            if support_summary:
                support_summary_html = (
                    f'<div class="support-summary">'
                    f'<strong>Support profile across all {n_tot} observed intervals:</strong><br>'
                    f'{support_summary}<br>'
                    + (f'<br><strong>⚠️ {top_grp_pct}% of all observed intervals involved {top_grp} support.</strong> '
                       'This data represents what was observed — it does not mean the student '
                       'was unsupported during other intervals; it means those intervals were '
                       'not recorded under a different grouping arrangement.' if top_grp_pct >= 70 else '')
                    + '</div>'
                )

            # ── Support breakdown table ─────────────────────────────────────
            grp_html_table = ""
            if not sup_filt.empty and "Grouping" in sup_filt.columns:
                pivot_c = sup_filt.groupby(["Grouping","State"]).size().unstack(fill_value=0)
                pivot_c["Total"] = pivot_c.sum(axis=1)
                osc = [s for s in state_order if s in pivot_c.columns]
                grp_html_table = '<table><thead><tr><th>Grouping</th><th>Total (n)</th>'
                for sc in osc: grp_html_table += f'<th>{sc}</th>'
                grp_html_table += '</tr></thead><tbody>'
                for g, row in pivot_c.iterrows():
                    total = int(row["Total"])
                    warn  = " ⚠️" if total < 3 else ""
                    grp_html_table += f'<tr><td><strong>{g}</strong>{warn}</td><td>{total}</td>'
                    for sc in osc:
                        cnt = int(row.get(sc, 0))
                        pct = round(100*cnt/total) if total else 0
                        grp_html_table += f'<td>{"—" if cnt==0 else f"{cnt} ({pct}%)"}</td>'
                    grp_html_table += '</tr>'
                grp_html_table += '</tbody></table>'
                grp_html_table += '<p style="font-size:.75rem;color:#64748b;">⚠️ Rows with n &lt; 3 reflect a single moment, not a pattern.</p>'

            # ── Questions HTML ──────────────────────────────────────────────
            qs_html = ""
            if questions_text:
                lines = [l.strip() for l in questions_text.strip().split("\n") if l.strip()]
                qs_html = '<ol class="questions">' + "".join(f"<li>{l.lstrip('0123456789. ')}</li>" for l in lines) + "</ol>"

            # ── Additional details HTML ─────────────────────────────────────
            additional_html = ""
            if additional_details and additional_details.strip():
                safe_ad = additional_details.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
                additional_html = f'<div class="additional"><div class="add-label">📝 Additional staff observations</div><p>{safe_ad}</p></div>'

            # ── Assemble full report ────────────────────────────────────────
            html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{report_title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  body {{font-family:Arial,sans-serif;font-size:13px;color:#1e293b;margin:0;padding:0;background:white;}}
  .page {{max-width:900px;margin:0 auto;padding:30px 36px;}}
  h1 {{font-size:1.45rem;color:#1A6B8A;border-bottom:3px solid #1A6B8A;padding-bottom:.5rem;margin-bottom:.3rem;}}
  h2 {{font-size:1.05rem;color:#1A6B8A;margin:2rem 0 .4rem;border-bottom:1px solid #e2e8f0;padding-bottom:.25rem;}}
  .meta {{font-size:.78rem;color:#64748b;margin-bottom:1rem;}}
  .obs-box {{background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;padding:.65rem 1.1rem;font-size:.83rem;margin-bottom:.8rem;}}
  .warn {{background:#fef9c3;border-left:4px solid #ca8a04;border-radius:0 6px 6px 0;padding:.55rem 1rem;font-size:.82rem;margin-bottom:1rem;line-height:1.6;}}
  .kpi-row {{display:flex;gap:.8rem;margin-bottom:1rem;flex-wrap:wrap;}}
  .kpi {{background:white;border-left:4px solid #1A6B8A;border-radius:6px;padding:.5rem .9rem;min-width:110px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.08);}}
  .kpi .val {{font-size:1.6rem;font-weight:700;color:#1A6B8A;}}
  .kpi .lbl {{font-size:.65rem;color:#64748b;line-height:1.4;}}
  .kpi.g {{border-color:#16a34a;}} .kpi.g .val {{color:#16a34a;}}
  .kpi.y {{border-color:#ca8a04;}} .kpi.y .val {{color:#ca8a04;}}
  .kpi.r {{border-color:#dc2626;}} .kpi.r .val {{color:#dc2626;}}
  .kpi.b {{border-color:#2563eb;}} .kpi.b .val {{color:#2563eb;}}
  .info-box {{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:.5rem .9rem;font-size:.8rem;color:#475569;margin-bottom:.5rem;line-height:1.5;}}
  .chart-wrap {{margin:.2rem 0 .6rem;border:1px solid #e2e8f0;border-radius:8px;overflow:visible;padding:.3rem;width:820px;max-width:100%;}}
  .hyp {{background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:0 8px 8px 0;padding:.65rem 1.1rem;margin:.6rem 0 1.2rem;font-size:.83rem;line-height:1.6;}}
  .hyp-label {{font-size:.65rem;font-weight:700;color:#1A6B8A;letter-spacing:.06em;margin-bottom:.3rem;}}
  .support-summary {{background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;padding:.65rem 1.1rem;font-size:.83rem;margin:.4rem 0 .7rem;line-height:1.6;}}
  .questions {{background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;padding:.8rem 1.1rem .8rem 2rem;margin:1rem 0;font-size:.84rem;line-height:1.8;color:#14532d;}}
  .questions li {{margin-bottom:.3rem;}}
  .additional {{background:#fefce8;border-left:4px solid #ca8a04;border-radius:0 8px 8px 0;padding:.65rem 1.1rem;margin:1rem 0;font-size:.83rem;line-height:1.6;}}
  .add-label {{font-size:.65rem;font-weight:700;color:#92400e;letter-spacing:.06em;margin-bottom:.3rem;}}
  .no-data {{color:#94a3b8;font-size:.8rem;font-style:italic;margin:.5rem 0 1rem;}}
  table {{border-collapse:collapse;width:100%;margin:.5rem 0 .8rem;font-size:.8rem;}}
  thead th {{background:#1A6B8A;color:white;padding:.4rem .65rem;text-align:left;font-weight:600;}}
  td {{border:1px solid #e2e8f0;padding:.32rem .65rem;}}
  tr:nth-child(even) td {{background:#f8fafc;}}
  .footer {{font-size:.68rem;color:#94a3b8;border-top:1px solid #e2e8f0;margin-top:2.5rem;padding-top:.6rem;}}
  @media print {{
    body {{font-size:11px;}}
    .page {{padding:18px 22px;}}
    .chart-wrap {{page-break-inside:avoid;}}
    h2 {{page-break-after:avoid;}}
  }}
</style>
</head>
<body>
<div class="page">

  <h1>{report_title}</h1>
  <div class="meta">
    {'Prepared by: <strong>' + report_author + '</strong> &nbsp;·&nbsp; ' if report_author else ''}
    Generated: <strong>{date.today().strftime('%-d %B %Y')}</strong>
  </div>

  <div class="obs-box">
    <strong>📅 Observation window:</strong> {date_span} &nbsp;·&nbsp;
    <strong>{n_days} school day{"s" if n_days!=1 else ""}</strong> with data &nbsp;·&nbsp;
    <strong>Time range: {min_slot}–{max_slot}</strong>
  </div>

  <div class="warn">
    <strong>⚠️ How to read this report — regulation states:</strong><br>
    🟢 <strong>In window</strong> — genuinely regulated; calm, present, learning-ready.<br>
    🟡 <strong>Coping</strong> — <strong>at the edge of the window and dysregulated</strong>.
    The student is actively working to manage their arousal state. This is not a stable or successful position.
    A session that is predominantly yellow is still a difficult session.<br>
    🔴 <strong>Hyperaroused</strong> — above the window; fight/flight/fright response.<br>
    🔵 <strong>Hypoaroused</strong> — below the window; shutdown/freeze/dissociation.<br><br>
    Each <em>interval</em> = one 15-minute observation window. Data was collected between
    <strong>{min_slot} and {max_slot}</strong> only.
  </div>

  <h2>Overall regulation summary</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="val">{n_tot}</div><div class="lbl">Total intervals<br>(15-min windows)</div></div>
    <div class="kpi g"><div class="val">{n_win}</div><div class="lbl">🟢 In window<br>{pct_inwin}%</div></div>
    <div class="kpi y"><div class="val">{n_cop}</div><div class="lbl">🟡 Coping (dysregulated)<br>{pct_cop_only}%</div></div>
    <div class="kpi r"><div class="val">{n_hyp}</div><div class="lbl">🔴 Hyperaroused</div></div>
    <div class="kpi b"><div class="val">{n_hypo}</div><div class="lbl">🔵 Hypoaroused</div></div>
  </div>

  {_chart_block(
    "📊 Regulation state across the day",
    f"Each bar = one 15-minute time slot between {min_slot} and {max_slot}, across all {n_days} observed days. "
    "Bar height = number of intervals recorded at that time. Colour = regulation state. "
    "<strong>🟡 Yellow (Coping) = dysregulated</strong> — the student is at the edge of their window and struggling to manage. "
    "Tall green bars = the student was consistently within their window at that time.",
    fig1_html, hyp_time
  )}

  <h2>📈 Daily regulation trend</h2>
  <div class="info-box">
    Percentage of each day's intervals in each regulation state across the {n_days} observed school days.
    The dashed green line marks the 70% in-window benchmark.
    <strong>Days above the green line in window% are the strongest days for regulation.</strong>
    Note: with a small number of observation days, individual daily variation may be large.
  </div>
  <div class="chart-wrap">{fig2_html or '<p class="no-data">Daily trend chart not yet generated.</p>'}</div>

  <h2>📅 Regulation by day of week</h2>
  <div class="info-box">
    The bar chart below shows each day's intervals as a <strong>100% normalised bar</strong> —
    bar colour split reflects the <em>proportion</em> of intervals in each state, regardless of how many
    intervals were recorded on that day. This matches the percentage table.
    <strong>Best days are those with the most green (In window), not yellow.</strong>
    🟡 Coping = dysregulated.
  </div>
  <div class="chart-wrap">{fig4_pct_html or fig4_html or '<p class="no-data">Chart not yet generated.</p>'}</div>
  {dow_html_table}
  {_hyp_block(hyp_dow_)}

  <h2>👥 Level of support</h2>
  {support_summary_html}
  <div class="info-box">
    The bar chart shows the total number of intervals recorded under each support/grouping arrangement,
    coloured by regulation state during that interval.
    The table below shows exact counts and percentages per regulation state.
    <strong>⚠️ Rows with n &lt; 3 should not be used to draw conclusions.</strong>
  </div>
  <div class="chart-wrap">{fig_grp_html or '<p class="no-data">Support chart not yet generated.</p>'}</div>
  {grp_html_table}
  {_hyp_block(hyp_grp_)}

  {_chart_block(
    "🎯 Regulation by activity type",
    "Each bar = all intervals recorded during that activity type, coloured by regulation state. "
    "When an interval has multiple activities selected, it is counted in each. "
    "🟡 Coping = dysregulated.",
    fig6_html or "", hyp_act_
  ) if fig6_html else (
    '<h2>🎯 Regulation by activity type</h2>'
    '<div class="no-data">No activity data recorded, or chart not yet generated.</div>'
    + _hyp_block(hyp_act_)
  )}

  <h2>🔎 Questions for the team to investigate</h2>
  <div class="info-box">
    The following questions were generated from the patterns in this student's data.
    They are intended to guide discussion at the next team meeting or TAC.
  </div>
  {qs_html or '<p class="no-data">Questions not generated — regenerate the report after scrolling through all charts.</p>'}

  {additional_html}

  <div class="footer">
    Interval Support Tracker &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit &nbsp;·&nbsp;
    Generated {date.today().strftime('%-d %B %Y')}
    {(' &nbsp;·&nbsp; Prepared by: ' + report_author) if report_author else ''}
  </div>
</div>
</body>
</html>"""

            st.download_button(
                "⬇️ Download report (HTML — opens in any browser)",
                html_report,
                file_name=f"IST_Report_{student_name.replace(' ','_')}_{date.today()}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.success("✅ Report ready. Open in Chrome, Edge or Firefox to view interactive charts and print.")

    st.download_button("📥 Download raw data (CSV)", csv,
        file_name=f"IntervalSupport_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True)

