# ════════════════════════════════════════════════════════════════════════════
# 20_Interval_Support_Tracker.py  ·  CLC-LBU Portal
# Records regulation, demand, grouping, support and outcome per time interval
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
.sg { width:100%; border-collapse:collapse; font-size:.8rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.38rem .5rem;
    text-align:center; font-size:.7rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:55px; }
.sg td { padding:.28rem .4rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.73rem; white-space:nowrap; background:#f8fafc; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
       padding:.4rem .7rem; text-align:center; margin-bottom:.35rem; }
.kpi .val { font-size:1.35rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.67rem; color:#666; }
.kpi-g { border-color:#16a34a; } .kpi-g .val { color:#16a34a; }
.kpi-a { border-color:#d97706; } .kpi-a .val { color:#d97706; }
.kpi-r { border-color:#dc2626; } .kpi-r .val { color:#dc2626; }
.rec-bar {
    background:white; border:1.5px solid #1A6B8A; border-radius:8px;
    padding:.5rem 1rem; margin:.35rem 0 .6rem; font-size:.85rem;
}
</style>
""", unsafe_allow_html=True)

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

REGULATED_OPTS = {
    "yes":     {"label":"✅  Regulated",  "bg":"#dcfce7","fg":"#16a34a","short":"R"},
    "partial": {"label":"⚠️  Partial",    "bg":"#fef3c7","fg":"#d97706","short":"P"},
    "no":      {"label":"❌  Not regulated","bg":"#fee2e2","fg":"#dc2626","short":"N"},
}
DEMAND_OPTS = {
    "low":    {"label":"Low demand",    "bg":"#f0fdf4","fg":"#15803d","short":"Lo"},
    "medium": {"label":"Medium demand", "bg":"#fef9ec","fg":"#92400e","short":"Md"},
    "high":   {"label":"High demand",   "bg":"#fff1f2","fg":"#be123c","short":"Hi"},
}
GROUPING_OPTS = {
    "i":   "Independent",
    "1:1": "One-to-one",
    "sg":  "Small group",
    "lg":  "Large group",
    "U":   "Unstructured",
}
SUPPORT_OPTS = [
    "None","1:1 SSO","1:1 Teacher","Small group","Visual supports","Modified task","Sensory break",
]
OUTCOME_OPTS = {
    "on_task":  {"label":"On task",   "bg":"#dcfce7","fg":"#16a34a","short":"✓"},
    "off_task": {"label":"Off task",  "bg":"#fef3c7","fg":"#d97706","short":"~"},
    "escalated":{"label":"Escalated", "bg":"#fee2e2","fg":"#dc2626","short":"!"},
}

DEFAULT_SLOTS = [
    "9:00","9:15","9:20","10:00","10:05","10:20","10:30",
    "11:00","11:30","11:40","12:30","12:50","13:00","13:30","13:45","14:30",
]


def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


def load_known_students():
    """Pull distinct student names from scatter_plot_observations."""
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("scatter_plot_observations").select("student_name").execute()
        names = sorted({r["student_name"] for r in (res.data or []) if r.get("student_name","").strip()})
        return names
    except Exception:
        return []


def load_week_obs(student_name, week_start, week_end):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_support_observations")
               .select("*")
               .eq("student_name", student_name)
               .gte("obs_date", str(week_start))
               .lte("obs_date", str(week_end))
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error("Load error: " + str(e))
        return pd.DataFrame()


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


def upsert_obs(student_name, sel_date, sel_day, sel_time, field, value):
    """Update a single field on an interval observation, inserting if needed."""
    sb = get_sb()
    if not sb: return False
    try:
        ex = (sb.table("interval_support_observations")
              .select("id").eq("student_name", student_name)
              .eq("obs_date", sel_date.isoformat())
              .eq("time_slot", sel_time).limit(1).execute())
        if ex.data:
            sb.table("interval_support_observations").update(
                {field: value}
            ).eq("id", ex.data[0]["id"]).execute()
        else:
            sb.table("interval_support_observations").insert({
                "student_name": student_name,
                "obs_date":     sel_date.isoformat(),
                "day_of_week":  sel_day,
                "time_slot":    sel_time,
                field:          value,
                "created_by":   get_staff_name(),
            }).execute()
        return True
    except Exception as e:
        st.error("Save failed: " + str(e))
        return False


def clear_obs(student_name, sel_date, sel_time):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("interval_support_observations").delete()\
          .eq("student_name", student_name)\
          .eq("obs_date", sel_date.isoformat())\
          .eq("time_slot", sel_time).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("ist_name", ""),
    ("ist_week", date.today() - timedelta(days=date.today().weekday())),
    ("ist_sel_time", ""),
    ("ist_sel_day", DAYS[date.today().weekday()] if date.today().weekday() < 5 else "Monday"),
]:
    if k not in ss: ss[k] = v


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="clc-header">
  <h2>🔵 Interval Support Tracker</h2>
  <p>Record regulation, demand, grouping, support and outcome per time slot
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR
# ════════════════════════════════════════════════════════════════════════════
known = load_known_students()
sc1, sc2 = st.columns([3, 1])
with sc1:
    if known:
        name_opts = ["— type name below —"] + known
        sel_opt = st.selectbox("Select existing student", name_opts, key="ist_sel_opt")
        if sel_opt != "— type name below —" and sel_opt != ss.ist_name:
            ss.ist_name = sel_opt
            st.rerun()
with sc2:
    st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
    if st.button("➕ New name", key="ist_new_btn", use_container_width=True):
        ss.ist_name = ""
    st.markdown("</div>", unsafe_allow_html=True)

if not ss.ist_name:
    new_name = st.text_input("Student name", placeholder="Type student name and press Enter",
                             key="ist_name_input")
    if new_name.strip():
        ss.ist_name = new_name.strip()
        st.rerun()
    st.stop()

student_name = ss.ist_name
st.markdown(f"**{student_name}**  "
            f"<span style='font-size:.78rem;color:#64748b;'>— Interval Support Tracker</span>",
            unsafe_allow_html=True)
if st.button("← Change student", key="ist_change", use_container_width=False):
    ss.ist_name = ""; st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis"])

# ════════════════════════════════════════════════════════════════════════════
# RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    # Week navigation
    week_start = ss.ist_week
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())
    is_this    = week_start == this_week

    wc1,wc2,wc3,wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", key="ist_prev", use_container_width=True):
            ss.ist_week -= timedelta(weeks=1); st.rerun()
    with wc2:
        st.markdown(
            f'<div style="text-align:center;padding:.38rem 0;font-weight:700;'
            f'color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>', unsafe_allow_html=True
        )
    with wc3:
        if st.button("Next →", key="ist_next", use_container_width=True):
            ss.ist_week += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", key="ist_today", use_container_width=True):
            ss.ist_week = this_week; st.rerun()

    week_df = load_week_obs(student_name, week_start, week_end)
    day_dates = {DAYS[i]: (week_start+timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None

    # Build cell lookup {time_slot: {day: row_dict}}
    cell_data = {}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t = row.get("time_slot",""); d = row.get("day_of_week","")
            if not t or not d: continue
            if t not in cell_data: cell_data[t] = {}
            cell_data[t][d] = row.to_dict()

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;gap:.5rem;flex-wrap:wrap;font-size:.72rem;margin:.2rem 0 .5rem;">'
        '<b>Regulation:</b> '
        '<span style="background:#dcfce7;color:#16a34a;padding:.1rem .4rem;border-radius:8px;">R</span> regulated &nbsp;'
        '<span style="background:#fef3c7;color:#d97706;padding:.1rem .4rem;border-radius:8px;">P</span> partial &nbsp;'
        '<span style="background:#fee2e2;color:#dc2626;padding:.1rem .4rem;border-radius:8px;">N</span> not regulated &nbsp;&nbsp;'
        '<b>Outcome:</b> '
        '<span style="background:#dcfce7;color:#16a34a;padding:.1rem .4rem;border-radius:8px;">✓</span> on task &nbsp;'
        '<span style="background:#fef3c7;color:#d97706;padding:.1rem .4rem;border-radius:8px;">~</span> off task &nbsp;'
        '<span style="background:#fee2e2;color:#dc2626;padding:.1rem .4rem;border-radius:8px;">!</span> escalated'
        '</div>', unsafe_allow_html=True
    )

    # ── Grid — shows regulation (top) + outcome (bottom) per cell ─────────
    th = '<th class="lh">Time</th>'
    for d in DAYS:
        is_td = (d == today_day and is_this)
        bg    = "background:#1a4d8a;" if is_td else ""
        th   += f'<th style="{bg}">{d[:3]}<br><span style="font-weight:400;font-size:.62rem;">{day_dates[d]}</span></th>'

    rows_html = ""
    slot_list = sorted(cell_data.keys() | set(DEFAULT_SLOTS),
                       key=lambda t: int(t.split(":")[0])*60+int(t.split(":")[1]) if ":" in t else 999)

    for t in slot_list:
        rows_html += f'<tr><td class="tl">{t}</td>'
        for d in DAYS:
            cell = cell_data.get(t,{}).get(d)
            if cell:
                reg = cell.get("regulated","")
                out = cell.get("outcome","")
                rbg = REGULATED_OPTS.get(reg,{}).get("bg","white")
                rfg = REGULATED_OPTS.get(reg,{}).get("fg","#334155")
                rsh = REGULATED_OPTS.get(reg,{}).get("short","·")
                osh = OUTCOME_OPTS.get(out,{}).get("short","")
                rows_html += (
                    f'<td style="background:{rbg};color:{rfg};vertical-align:middle;'
                    f'text-align:center;padding:.2rem .3rem;font-weight:700;">'
                    f'{rsh}<br><span style="font-size:.62rem;opacity:.8;">{osh}</span></td>'
                )
            else:
                rows_html += '<td style="color:#e2e8f0;text-align:center;">·</td>'
        rows_html += "</tr>"

    st.markdown(
        f'<div class="grid-wrap"><table class="sg">'
        f'<thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True
    )

    # ── Time slot tap buttons ─────────────────────────────────────────────
    st.markdown("**➕ Record an observation:**")
    st.markdown('<div style="font-size:.7rem;font-weight:600;color:#64748b;margin:.2rem 0 .15rem;">TIME SLOT</div>',
                unsafe_allow_html=True)
    if not ss.ist_sel_time and slot_list:
        ss.ist_sel_time = slot_list[0]

    chunk_size = 8
    for ci_start in range(0, len(slot_list), chunk_size):
        chunk = slot_list[ci_start:ci_start+chunk_size]
        cols  = st.columns(len(chunk))
        for ci, t in enumerate(chunk):
            is_sel = (t == ss.ist_sel_time)
            if cols[ci].button(t, key=f"ist_t_{ci_start+ci}", use_container_width=True,
                               type="primary" if is_sel else "secondary"):
                ss.ist_sel_time = t; st.rerun()

    # ── Day buttons ───────────────────────────────────────────────────────
    st.markdown('<div style="font-size:.7rem;font-weight:600;color:#64748b;margin:.35rem 0 .15rem;">DAY</div>',
                unsafe_allow_html=True)
    dcols = st.columns(5)
    for di, d in enumerate(DAYS):
        is_sel  = (d == ss.ist_sel_day)
        d_date  = week_start + timedelta(days=di)
        d_label = d[:3] + " " + d_date.strftime("%-d/%m")
        if dcols[di].button(d_label, key=f"ist_d_{di}", use_container_width=True,
                            type="primary" if is_sel else "secondary"):
            ss.ist_sel_day = d; st.rerun()

    sel_time = ss.ist_sel_time or (slot_list[0] if slot_list else "")
    sel_day  = ss.ist_sel_day
    sel_date = week_start + timedelta(days=DAYS.index(sel_day))
    cur_cell = cell_data.get(sel_time,{}).get(sel_day,{})

    # Context bar
    st.markdown(
        f'<div class="rec-bar"><b style="color:{TEAL};">Recording:</b> {sel_time}'
        f' &nbsp;·&nbsp; <b>{sel_day}</b> {sel_date.strftime("%-d %b")}'
        + (f' &nbsp;·&nbsp; <span style="color:#16a34a;font-weight:600;">'
           f'{REGULATED_OPTS.get(cur_cell.get("regulated",""),{}).get("label","")}</span>'
           if cur_cell.get("regulated") else '')
        + '</div>', unsafe_allow_html=True
    )

    # ── Five recording fields ─────────────────────────────────────────────
    def _tap_row(field_label, options_dict, field_key, cur_val, btn_key_prefix,
                 show_labels=True):
        """Render a labelled row of tap buttons for a field."""
        st.markdown(
            f'<div style="font-size:.7rem;font-weight:600;color:#64748b;'
            f'margin:.3rem 0 .1rem;">{field_label}</div>',
            unsafe_allow_html=True
        )
        opts  = list(options_dict.items())
        cols  = st.columns(len(opts) + 1)
        saved = False
        for ci, (val, cfg) in enumerate(opts):
            lbl    = cfg["label"] if show_labels else val
            is_sel = (cur_val == val)
            if cols[ci].button(lbl, key=f"{btn_key_prefix}_{ci}",
                               use_container_width=True,
                               type="primary" if is_sel else "secondary"):
                new_val = "" if is_sel else val  # tap again = deselect
                upsert_obs(student_name, sel_date, sel_day, sel_time, field_key, new_val)
                saved = True
        with cols[-1]:
            if cur_val:
                if st.button("✕", key=f"{btn_key_prefix}_clr",
                             use_container_width=True, help="Clear"):
                    upsert_obs(student_name, sel_date, sel_day, sel_time, field_key, "")
                    saved = True
        if saved: st.rerun()

    # Regulation
    _tap_row("REGULATION", REGULATED_OPTS, "regulated",
             cur_cell.get("regulated",""), f"ist_reg_{sel_time}_{sel_day}")

    # Task demand
    _tap_row("TASK DEMAND", DEMAND_OPTS, "task_demand",
             cur_cell.get("task_demand",""), f"ist_dem_{sel_time}_{sel_day}", show_labels=True)

    # Grouping — convert to dict format
    grp_dict = {k: {"label": f"{k} — {v}", "bg":"", "fg":""} for k,v in GROUPING_OPTS.items()}
    _tap_row("GROUPING", grp_dict, "grouping",
             cur_cell.get("grouping",""), f"ist_grp_{sel_time}_{sel_day}")

    # Support used — list → dict
    sup_dict = {s: {"label": s, "bg":"", "fg":""} for s in SUPPORT_OPTS}
    _tap_row("SUPPORT USED", sup_dict, "support_used",
             cur_cell.get("support_used",""), f"ist_sup_{sel_time}_{sel_day}")

    # Outcome
    _tap_row("OUTCOME", OUTCOME_OPTS, "outcome",
             cur_cell.get("outcome",""), f"ist_out_{sel_time}_{sel_day}")

    # Notes
    cur_notes = cur_cell.get("notes","") or ""
    new_notes = st.text_input("Notes (optional)", value=cur_notes,
                              key=f"ist_notes_{sel_time}_{sel_day}",
                              placeholder="Any context for this interval")
    if new_notes != cur_notes:
        upsert_obs(student_name, sel_date, sel_day, sel_time, "notes", new_notes)

    # Clear whole cell
    if cur_cell:
        if st.button("🗑️ Clear this interval", key=f"ist_clr_{sel_time}_{sel_day}"):
            clear_obs(student_name, sel_date, sel_time)
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Interval Support Analysis")

    all_obs = load_all_obs(student_name)
    if all_obs.empty:
        st.info("No observations recorded yet."); st.stop()

    fc1, fc2 = st.columns(2)
    with fc1: date_from = st.date_input("From", value=all_obs["obs_date_dt"].min().date(), key="ist_af")
    with fc2: date_to   = st.date_input("To",   value=all_obs["obs_date_dt"].max().date(), key="ist_at")

    filt = all_obs[
        (all_obs["obs_date_dt"].dt.date >= date_from) &
        (all_obs["obs_date_dt"].dt.date <= date_to)
    ].copy()
    if filt.empty:
        st.info("No data in this range."); st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────
    n_tot  = len(filt)
    n_reg  = (filt["regulated"]=="yes").sum()
    n_part = (filt["regulated"]=="partial").sum()
    n_not  = (filt["regulated"]=="no").sum()
    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><div class='val'>{n_tot}</div><div class='lbl'>Intervals recorded</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-g'><div class='val'>{n_reg}</div><div class='lbl'>Regulated</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n_part}</div><div class='lbl'>Partial</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi kpi-r'><div class='val'>{n_not}</div><div class='lbl'>Not regulated</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    ac1, ac2 = st.columns(2)

    # ── Regulation by time slot ────────────────────────────────────────────
    with ac1:
        slot_reg = filt.dropna(subset=["regulated"]).copy()
        slot_reg["Regulation"] = slot_reg["regulated"].map(
            {k: v["label"] for k,v in REGULATED_OPTS.items()}
        )
        slot_reg["sort_k"] = slot_reg["time_slot"].apply(
            lambda t: int(t.split(":")[0])*60+int(t.split(":")[1]) if ":"in t else 999)
        sg = slot_reg.groupby(["time_slot","Regulation","sort_k"]).size().reset_index(name="n")
        sg = sg.sort_values("sort_k")
        fig1 = px.bar(sg, x="n", y="time_slot", color="Regulation", orientation="h",
            color_discrete_map={
                "✅  Regulated":"#16a34a","⚠️  Partial":"#d97706","❌  Not regulated":"#dc2626"
            },
            title="Regulation by time slot", barmode="stack",
            labels={"time_slot":"","n":"Intervals"})
        fig1.update_layout(height=max(280,len(sg["time_slot"].unique())*22),
            plot_bgcolor="#f8fafc",paper_bgcolor="white",
            margin=dict(l=10,r=10,t=45,b=10),xaxis=dict(tickformat="d"),
            yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig1, use_container_width=True)

    # ── Regulation by grouping ─────────────────────────────────────────────
    with ac2:
        grp_reg = filt.dropna(subset=["regulated","grouping"]).copy()
        grp_reg = grp_reg[grp_reg["grouping"].str.strip() != ""]
        if not grp_reg.empty:
            grp_reg["Regulation"] = grp_reg["regulated"].map(
                {k: v["label"] for k,v in REGULATED_OPTS.items()}
            )
            grp_reg["Grouping"] = grp_reg["grouping"].map(GROUPING_OPTS).fillna(grp_reg["grouping"])
            gg = grp_reg.groupby(["Grouping","Regulation"]).size().reset_index(name="n")
            fig2 = px.bar(gg, x="n", y="Grouping", color="Regulation", orientation="h",
                color_discrete_map={
                    "✅  Regulated":"#16a34a","⚠️  Partial":"#d97706","❌  Not regulated":"#dc2626"
                },
                title="Regulation by grouping", barmode="stack",
                labels={"Grouping":"","n":"Intervals"})
            fig2.update_layout(height=max(240,len(gg["Grouping"].unique())*32),
                plot_bgcolor="#f8fafc",paper_bgcolor="white",
                margin=dict(l=10,r=10,t=45,b=10),xaxis=dict(tickformat="d"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Record grouping data to see this chart.")

    # ── Support effectiveness ──────────────────────────────────────────────
    st.markdown("---")
    sup_filt = filt.dropna(subset=["support_used","regulated"]).copy()
    sup_filt = sup_filt[sup_filt["support_used"].str.strip() != ""]
    if not sup_filt.empty:
        sup_filt["Regulation"] = sup_filt["regulated"].map(
            {k: v["label"] for k,v in REGULATED_OPTS.items()}
        )
        sg2 = sup_filt.groupby(["support_used","Regulation"]).size().reset_index(name="n")
        fig3 = px.bar(sg2, x="n", y="support_used", color="Regulation", orientation="h",
            color_discrete_map={
                "✅  Regulated":"#16a34a","⚠️  Partial":"#d97706","❌  Not regulated":"#dc2626"
            },
            title="Support effectiveness — regulation outcome by support type",
            barmode="stack", labels={"support_used":"","n":"Intervals"})
        fig3.update_layout(height=max(260,len(sg2["support_used"].unique())*32),
            plot_bgcolor="#f8fafc",paper_bgcolor="white",
            margin=dict(l=10,r=10,t=50,b=10),xaxis=dict(tickformat="d"))
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("💡 This shows which support types are most associated with regulation. "
                   "Longer green bars = that support consistently works for this student.")
    else:
        st.info("Record support data to see effectiveness analysis.")

    # ── Demand vs regulation ───────────────────────────────────────────────
    dem_filt = filt.dropna(subset=["task_demand","regulated"]).copy()
    dem_filt = dem_filt[dem_filt["task_demand"].str.strip() != ""]
    if not dem_filt.empty:
        dem_filt["Regulation"] = dem_filt["regulated"].map(
            {k: v["label"] for k,v in REGULATED_OPTS.items()}
        )
        dem_filt["Demand"] = dem_filt["task_demand"].str.capitalize()
        dg = dem_filt.groupby(["Demand","Regulation"]).size().reset_index(name="n")
        fig4 = px.bar(dg, x="Demand", y="n", color="Regulation",
            color_discrete_map={
                "✅  Regulated":"#16a34a","⚠️  Partial":"#d97706","❌  Not regulated":"#dc2626"
            },
            title="Task demand vs regulation",
            barmode="stack", labels={"Demand":"Task demand","n":"Intervals"})
        fig4.update_layout(height=280,plot_bgcolor="#f8fafc",paper_bgcolor="white",
            margin=dict(l=10,r=10,t=50,b=10),yaxis=dict(tickformat="d"))
        st.plotly_chart(fig4, use_container_width=True)

    # ── CSV download ───────────────────────────────────────────────────────
    st.markdown("---")
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    csv = dl[["obs_date","day_of_week","time_slot","regulated","task_demand",
              "grouping","support_used","outcome","notes","created_by"]].to_csv(index=False)
    st.download_button("📥 Download CSV", csv,
        file_name=f"IntervalSupport_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True)
