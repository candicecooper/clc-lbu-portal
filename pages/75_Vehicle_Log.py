"""
75_Vehicle_Log.py — CLC-LBU Vehicle Log Book
-------------------------------------------------
Electronic version of the printable Vehicle Log Book for the two CLC site
vehicles (Kia site car S104BQL, Van S996BQL).

Tabs
  🚗 Log a Trip      – open access. Start odometer auto-fills from the vehicle's
                        last recorded reading; total km calculated automatically.
  📋 Trip History    – open access. Filter by vehicle / month, view only.
  🛠️ Admin & Reports – confidential password. Monthly summary, Excel + Word
                        (printable log book) downloads, "Email report now",
                        fix / delete entries.

Monthly email
  Sent automatically on the 1st of each month (covering the previous month) by
  the Google Apps Script `vehicle_log_monthly_email.gs` on the CLC Gmail account.
  The "Email report now" button calls the same script, so both emails look
  identical.

Supabase table: vehicle_log  (see vehicle_log_schema.sql)

Render env vars used
  SUPABASE_URL / SUPABASE_KEY        (same as other portal tools)
  VEHICLE_LOG_WEBHOOK_URL            (Apps Script web app URL)
  VEHICLE_LOG_WEBHOOK_TOKEN          (shared secret, matches Script Property)
"""

import io
import os
import calendar
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Vehicle Log Book", page_icon="🚗", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# Vehicles
# ──────────────────────────────────────────────────────────────────────────────
VEHICLES = {
    "Kia": {"label": "Kia (site car)", "rego": "S104BQL", "make_model": "Kia"},
    "Van": {"label": "Van", "rego": "S996BQL", "make_model": "Van"},
}
WORKSITE = "Cowandilla Learning Centre — LBU"
TABLE = "vehicle_log"
TRIP_TYPES = ["Business", "Private"]
BIG_TRIP_KM = 500  # warn (not block) above this


# ──────────────────────────────────────────────────────────────────────────────
# Supabase
# ──────────────────────────────────────────────────────────────────────────────
def _cfg(*names):
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


@st.cache_resource
def get_client():
    from supabase import create_client

    url = _cfg("SUPABASE_URL", "SUPABASE_URL_MEETINGS", "SUPABASE_URL_STUDENTS")
    key = _cfg(
        "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY",
        "SUPABASE_KEY_MEETINGS", "SUPABASE_KEY_STUDENTS",
    )
    if not url or not key:
        return None
    return create_client(url, key)


sb = get_client()
if sb is None:
    st.error("Supabase isn't configured (SUPABASE_URL / SUPABASE_KEY missing).")
    st.stop()


def load_trips(vehicle=None, start=None, end=None):
    """Trips with start <= trip_date < end."""
    try:
        q = sb.table(TABLE).select("*")
        if vehicle:
            q = q.eq("vehicle", vehicle)
        if start:
            q = q.gte("trip_date", start.isoformat())
        if end:
            q = q.lt("trip_date", end.isoformat())
        res = q.order("trip_date").order("start_odo").execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        msg = str(e)
        if "vehicle_log" in msg and ("does not exist" in msg or "schema cache" in msg):
            st.error("The `vehicle_log` table doesn't exist yet — run vehicle_log_schema.sql in Supabase.")
        else:
            st.error(f"Couldn't load trips: {e}")
        return pd.DataFrame()


def last_odometer(vehicle):
    try:
        res = (sb.table(TABLE).select("end_odo, trip_date, driver")
               .eq("vehicle", vehicle).order("end_odo", desc=True).limit(1).execute())
        return res.data[0] if res.data else None
    except Exception:
        return None


def known_drivers():
    try:
        res = sb.table(TABLE).select("driver").order("driver").execute()
        return sorted({(r["driver"] or "").strip() for r in res.data or [] if r.get("driver")})
    except Exception:
        return []


def month_bounds(y, m):
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return start, end


def month_options(n=18):
    today = date.today()
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def month_label(y, m):
    return f"{calendar.month_name[m]} {y}"


# ──────────────────────────────────────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────────────────────────────────────
DISPLAY_COLS = {
    "trip_date": "Date", "vehicle": "Vehicle", "rego": "Rego", "driver": "Driver",
    "start_odo": "Start odo", "end_odo": "End odo", "total_km": "Total km",
    "from_location": "From", "to_location": "To", "purpose": "Purpose of trip",
    "trip_type": "Private / Business", "fuel_notes": "Fuel / notes",
}


def fuel_notes(row):
    bits = []
    fa = row.get("fuel_added")
    if fa is True or (fa is not None and not pd.isna(fa) and bool(fa)):
        f = "Fuel added"
        if pd.notna(row.get("fuel_litres")) and row.get("fuel_litres"):
            f += f" {float(row['fuel_litres']):g} L"
        if pd.notna(row.get("fuel_cost")) and row.get("fuel_cost"):
            f += f" (${float(row['fuel_cost']):.2f})"
        bits.append(f)
    n = row.get("notes")
    if n is not None and not (isinstance(n, float) and pd.isna(n)) and str(n).strip():
        bits.append(str(n).strip())
    return "; ".join(bits)


def to_display(df):
    if df.empty:
        return df
    d = df.copy()
    if "total_km" not in d or d["total_km"].isna().any():
        d["total_km"] = d["end_odo"] - d["start_odo"]
    d["fuel_notes"] = d.apply(fuel_notes, axis=1)
    d["trip_date"] = pd.to_datetime(d["trip_date"]).dt.strftime("%d/%m/%Y")
    cols = [c for c in DISPLAY_COLS if c in d.columns]
    return d[cols].rename(columns=DISPLAY_COLS)


def summary_table(df):
    rows = []
    for key, v in VEHICLES.items():
        sub = df[df["vehicle"] == key] if not df.empty else df
        km = (sub["end_odo"] - sub["start_odo"]) if not sub.empty else pd.Series(dtype=int)
        bus = km[sub["trip_type"] == "Business"].sum() if not sub.empty else 0
        prv = km[sub["trip_type"] == "Private"].sum() if not sub.empty else 0
        fuel = sub["fuel_cost"].fillna(0).sum() if not sub.empty and "fuel_cost" in sub else 0
        rows.append({
            "Vehicle": f"{v['label']} — {v['rego']}",
            "Trips": len(sub),
            "Total km": int(km.sum()) if len(km) else 0,
            "Business km": int(bus), "Private km": int(prv),
            "Odometer start": int(sub["start_odo"].min()) if not sub.empty else None,
            "Odometer end": int(sub["end_odo"].max()) if not sub.empty else None,
            "Fuel cost": f"${fuel:,.2f}",
        })
    return pd.DataFrame(rows)


def odo_gaps(df):
    """Find places where a trip's start odo doesn't match the previous trip's end odo."""
    issues = []
    for key in VEHICLES:
        sub = df[df["vehicle"] == key].sort_values(["start_odo", "trip_date"])
        prev = None
        for _, r in sub.iterrows():
            if prev is not None and int(r["start_odo"]) != int(prev["end_odo"]):
                diff = int(r["start_odo"]) - int(prev["end_odo"])
                kind = "unlogged" if diff > 0 else "overlap"
                d1 = pd.to_datetime(prev["trip_date"]).strftime("%d/%m/%Y")
                d2 = pd.to_datetime(r["trip_date"]).strftime("%d/%m/%Y")
                issues.append(
                    f"{key}: {abs(diff)} km {kind} between "
                    f"{prev['end_odo']} ({d1}, {prev['driver']}) and "
                    f"{r['start_odo']} ({d2}, {r['driver']})"
                )
            prev = r
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Exports
# ──────────────────────────────────────────────────────────────────────────────
def build_excel(df, title):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        summary_table(df).to_excel(xw, sheet_name="Summary", index=False, startrow=2)
        ws = xw.sheets["Summary"]
        ws["A1"] = title
        for key, v in VEHICLES.items():
            sub = df[df["vehicle"] == key] if not df.empty else df
            to_display(sub).to_excel(xw, sheet_name=key, index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 45)
    return buf.getvalue()


def build_word(df, period_text):
    """Printable log book matching the paper form — one section per vehicle."""
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    def shade(cell, hex_fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_fill)
        tcPr.append(shd)

    def cell_text(cell, text, bold=False, size=9):
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run("" if text is None else str(text))
        run.bold = bold
        run.font.size = Pt(size)

    def heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.add_run(text).bold = True

    doc = Document()
    st_ = doc.styles["Normal"]
    st_.font.name = "Arial"
    st_.font.size = Pt(10)

    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.5))

    first = True
    for key, v in VEHICLES.items():
        sub = df[df["vehicle"] == key].sort_values(["trip_date", "start_odo"]) if not df.empty else df
        if not first:
            doc.add_page_break()
        first = False

        h = doc.add_paragraph()
        r = h.add_run("Vehicle Log Book")
        r.bold, r.font.size = True, Pt(18)
        r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

        heading("Vehicle details")
        drivers = sub["driver"].value_counts() if not sub.empty else pd.Series(dtype=int)
        details = [
            ("Vehicle make / model", v["make_model"], "Registration number", v["rego"]),
            ("Fleet / asset number", "", "Primary driver / officer",
             drivers.index[0] if len(drivers) else ""),
            ("Worksite / location", WORKSITE, "Period covered", period_text),
        ]
        t = doc.add_table(rows=3, cols=4)
        t.style = "Table Grid"
        for i, (a, b, c, d) in enumerate(details):
            for j, (txt, bold) in enumerate([(a, True), (b, False), (c, True), (d, False)]):
                cell_text(t.cell(i, j), txt, bold=bold, size=10)
                if bold:
                    shade(t.cell(i, j), "E8EEF5")

        heading("Trip entries")
        heads = ["Date", "Driver", "Start odo", "End odo", "Total km", "From", "To",
                 "Purpose of trip", "Private / Business", "Fuel / notes"]
        widths = [2.0, 3.0, 2.0, 2.0, 1.7, 3.2, 3.2, 4.6, 2.2, 2.8]
        rows = max(len(sub), 10)
        t = doc.add_table(rows=1 + rows + 1, cols=len(heads))
        t.style = "Table Grid"
        t.autofit = False
        for j, w in enumerate(widths):
            t.columns[j].width = Cm(w)
        for j, hd in enumerate(heads):
            cell_text(t.cell(0, j), hd, bold=True)
            shade(t.cell(0, j), "1F3A5F")
            t.cell(0, j).paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        tot = 0
        for i, (_, row) in enumerate(sub.iterrows(), start=1):
            km = int(row["end_odo"]) - int(row["start_odo"])
            tot += km
            vals = [
                pd.to_datetime(row["trip_date"]).strftime("%d/%m/%Y"), row["driver"],
                int(row["start_odo"]), int(row["end_odo"]), km,
                row.get("from_location"), row.get("to_location"), row.get("purpose"),
                row.get("trip_type"), fuel_notes(row),
            ]
            for j, val in enumerate(vals):
                cell_text(t.cell(i, j), val)
        last = t.rows[-1]
        cell_text(last.cells[3], "Total", bold=True)
        cell_text(last.cells[4], tot, bold=True)
        for row in t.rows:
            for j, w in enumerate(widths):
                row.cells[j].width = Cm(w)

        heading("Declaration and approval")
        decl = [
            ("Driver declaration",
             "Each driver certified their entries as true and correct when lodging them in the CLC portal."),
            ("Supervisor / authorised officer", ""),
            ("Signature", ""),
            ("Date", ""),
        ]
        t = doc.add_table(rows=len(decl), cols=2)
        t.style = "Table Grid"
        for i, (a, b) in enumerate(decl):
            cell_text(t.cell(i, 0), a, bold=True, size=10)
            shade(t.cell(i, 0), "E8EEF5")
            cell_text(t.cell(i, 1), b, size=10)
            t.cell(i, 0).width, t.cell(i, 1).width = Cm(6), Cm(20)
            t.rows[i].height = Cm(0.8)

        foot = doc.add_paragraph(f"Generated from the CLC-LBU portal on {date.today():%d/%m/%Y}.")
        foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        foot.runs[0].font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def email_report_now(y, m, to_override=""):
    url = _cfg("VEHICLE_LOG_WEBHOOK_URL")
    token = _cfg("VEHICLE_LOG_WEBHOOK_TOKEN")
    if not url or not token:
        return False, "VEHICLE_LOG_WEBHOOK_URL / VEHICLE_LOG_WEBHOOK_TOKEN aren't set in Render."
    payload = {"token": token, "action": "send_report", "month": f"{y:04d}-{m:02d}"}
    if to_override.strip():
        payload["to"] = to_override.strip()
    try:
        r = requests.post(url, json=payload, timeout=60, allow_redirects=True)
        try:
            data = r.json()
        except Exception:
            return False, f"Unexpected reply from the email script (HTTP {r.status_code})."
        if data.get("ok"):
            return True, f"Report for {month_label(y, m)} emailed to {data.get('to', 'admin')}."
        return False, data.get("error", "The email script reported an error.")
    except Exception as e:
        return False, f"Couldn't reach the email script: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Admin gate
# ──────────────────────────────────────────────────────────────────────────────
def admin_unlocked():
    try:
        from confidential_auth import require_confidential_auth
    except Exception:
        st.warning("confidential_auth.py not found — admin tab locked.")
        return False
    try:
        res = require_confidential_auth()
    except TypeError:
        res = require_confidential_auth("vehicle_log")
    return res is not False


# ──────────────────────────────────────────────────────────────────────────────
# Page
# ──────────────────────────────────────────────────────────────────────────────
st.title("🚗 Vehicle Log Book")
st.caption("Kia site car (S104BQL) and Van (S996BQL). Log every trip when you return the keys.")

notice = st.session_state.pop("_vl_notice", None)
if notice:
    st.success(notice)

tab_log, tab_hist, tab_admin = st.tabs(["🚗 Log a Trip", "📋 Trip History", "🛠️ Admin & Reports"])

# ── Log a trip ────────────────────────────────────────────────────────────────
with tab_log:
    vkey = st.radio(
        "Vehicle", list(VEHICLES), horizontal=True,
        format_func=lambda k: f"{VEHICLES[k]['label']} — {VEHICLES[k]['rego']}",
        key="vl_vehicle",
    )
    last = last_odometer(vkey)
    if last:
        st.info(
            f"Last recorded odometer for the {vkey}: **{last['end_odo']:,} km** "
            f"({pd.to_datetime(last['trip_date']):%d/%m/%Y}, {last['driver']}). "
            "Check this matches the dashboard before you set off."
        )
        default_start = int(last["end_odo"])
    else:
        st.info(f"No trips logged for the {vkey} yet — enter the odometer reading from the dashboard.")
        default_start = 0

    drivers = known_drivers()
    driver_choice = st.selectbox(
        "Driver", ["— select —"] + drivers + ["➕ My name isn't listed"], key="vl_driver_pick"
    )
    new_driver = ""
    if driver_choice == "➕ My name isn't listed":
        new_driver = st.text_input("Your name (first and last)", key="vl_driver_new")

    with st.form("vl_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        trip_date = c1.date_input("Date", value=date.today(), format="DD/MM/YYYY",
                                  max_value=date.today())
        start_odo = c2.number_input("Start odometer (km)", min_value=0, step=1,
                                    value=default_start, key=f"vl_start_{vkey}_{default_start}")
        end_odo = c3.number_input("End odometer (km)", min_value=0, step=1,
                                  value=default_start, key=f"vl_end_{vkey}_{default_start}")

        c4, c5 = st.columns(2)
        from_loc = c4.text_input("From", value="CLC Cowandilla")
        to_loc = c5.text_input("To", placeholder="e.g. Glenelg beach / home school / Bunnings Mile End")
        purpose = st.text_input("Purpose of trip",
                                placeholder="e.g. PY excursion, student transport, collecting supplies")

        c6, c7 = st.columns([1, 2])
        trip_type = c6.radio("Private / Business", TRIP_TYPES, horizontal=True)
        fuel_added = c7.checkbox("I added fuel on this trip")
        c8, c9 = st.columns(2)
        fuel_litres = c8.number_input("Litres (if fuel added)", min_value=0.0, step=0.1, format="%.1f")
        fuel_cost = c9.number_input("Cost $ (if fuel added)", min_value=0.0, step=0.01, format="%.2f")
        notes = st.text_area("Notes (damage, warning lights, cleaning needed, etc.)", height=70)

        declared = st.checkbox("I certify that the entries above are true and correct.")
        submitted = st.form_submit_button("💾 Save trip", type="primary", use_container_width=True)

    if submitted:
        driver = (new_driver if driver_choice == "➕ My name isn't listed" else driver_choice).strip()
        errs = []
        if not driver or driver == "— select —":
            errs.append("Choose or enter the driver's name.")
        if end_odo <= start_odo:
            errs.append("End odometer must be higher than start odometer.")
        if not to_loc.strip():
            errs.append("Enter where you went (To).")
        if not purpose.strip():
            errs.append("Enter the purpose of the trip.")
        if fuel_added and fuel_litres == 0 and fuel_cost == 0:
            errs.append("You ticked 'added fuel' — enter the litres or cost.")
        if not declared:
            errs.append("Tick the declaration to confirm the entry is correct.")
        if errs:
            for e in errs:
                st.error(e)
        else:
            km = int(end_odo - start_odo)
            row = {
                "trip_date": trip_date.isoformat(), "vehicle": vkey, "rego": VEHICLES[vkey]["rego"],
                "driver": driver, "start_odo": int(start_odo), "end_odo": int(end_odo),
                "from_location": from_loc.strip(), "to_location": to_loc.strip(),
                "purpose": purpose.strip(), "trip_type": trip_type,
                "fuel_added": bool(fuel_added),
                "fuel_litres": float(fuel_litres) if fuel_added and fuel_litres else None,
                "fuel_cost": float(fuel_cost) if fuel_added and fuel_cost else None,
                "notes": notes.strip() or None, "declared": True,
            }
            try:
                res = sb.table(TABLE).insert(row).execute()
                if res.data:
                    msg = f"✅ Trip saved — {vkey}, {km:,} km, {driver}."
                    if km > BIG_TRIP_KM:
                        msg += f" (That's over {BIG_TRIP_KM} km — tell Admin if it's a typo.)"
                    if last and int(start_odo) != int(last["end_odo"]):
                        msg += (f" Note: start odometer differs from the last recorded reading "
                                f"({last['end_odo']:,}) — Admin will see this in the monthly report.")
                    st.session_state["_vl_notice"] = msg
                    st.session_state.pop("vl_driver_pick", None)
                    st.session_state.pop("vl_driver_new", None)
                    st.rerun()
                else:
                    st.error("The trip didn't save — please try again or tell Admin.")
            except Exception as e:
                st.error(f"The trip didn't save: {e}")

# ── History ───────────────────────────────────────────────────────────────────
with tab_hist:
    opts = month_options()
    c1, c2 = st.columns(2)
    ym = c1.selectbox("Month", opts, format_func=lambda t: month_label(*t), key="vl_hist_month")
    vf = c2.selectbox("Vehicle", ["Both"] + list(VEHICLES), key="vl_hist_vehicle")
    s, e = month_bounds(*ym)
    df = load_trips(None if vf == "Both" else vf, s, e)
    if df.empty:
        st.info(f"No trips logged for {month_label(*ym)}.")
    else:
        st.dataframe(summary_table(df), hide_index=True, use_container_width=True)
        st.dataframe(to_display(df), hide_index=True, use_container_width=True)
        st.caption("Spotted a mistake? Tell Admin — they can correct entries in the Admin tab.")

# ── Admin ─────────────────────────────────────────────────────────────────────
with tab_admin:
    if admin_unlocked():
        opts = month_options()
        ym = st.selectbox("Report month", opts, format_func=lambda t: month_label(*t),
                          index=1 if date.today().day <= 7 else 0, key="vl_admin_month")
        s, e = month_bounds(*ym)
        df = load_trips(None, s, e)
        period = f"{s:%d/%m/%Y} – {date.fromordinal(e.toordinal() - 1):%d/%m/%Y}"

        st.subheader(f"Summary — {month_label(*ym)}")
        st.dataframe(summary_table(df), hide_index=True, use_container_width=True)

        if not df.empty:
            gaps = odo_gaps(df)
            if gaps:
                with st.expander(f"⚠️ {len(gaps)} odometer mismatch(es) to check", expanded=True):
                    for g in gaps:
                        st.write("•", g)
            st.dataframe(to_display(df), hide_index=True, use_container_width=True)

        c1, c2 = st.columns(2)
        fname = f"Vehicle_Log_{ym[0]}-{ym[1]:02d}"
        c1.download_button("⬇️ Excel (summary + trips per vehicle)",
                           build_excel(df, f"CLC Vehicle Log — {month_label(*ym)}"),
                           file_name=f"{fname}.xlsx", use_container_width=True,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        c2.download_button("⬇️ Word log book (printable, for signing)",
                           build_word(df, period), file_name=f"{fname}.docx", use_container_width=True,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        st.divider()
        st.markdown("**📧 Email this month's report**")
        st.caption("The report emails itself to Admin on the 1st of every month for the month before. "
                   "Use this to resend it or send a different month.")
        to_override = st.text_input("Send to (leave blank for the usual Admin address)", key="vl_to")
        if st.button("📧 Email report now", key="vl_email"):
            with st.spinner("Sending…"):
                ok, msg = email_report_now(*ym, to_override)
            (st.success if ok else st.error)(msg)

        st.divider()
        with st.expander("✏️ Fix or delete an entry"):
            if df.empty:
                st.info("No entries this month.")
            else:
                labels = {
                    int(r["id"]): f"{pd.to_datetime(r['trip_date']):%d/%m} · {r['vehicle']} · "
                                  f"{r['driver']} · {r['start_odo']}→{r['end_odo']} · {r['to_location']}"
                    for _, r in df.iterrows()
                }
                pick = st.selectbox("Entry", list(labels), format_func=labels.get, key="vl_fix_pick")
                r = df[df["id"] == pick].iloc[0]
                with st.form(f"vl_fix_{pick}"):
                    a, b, c = st.columns(3)
                    f_date = a.date_input("Date", value=pd.to_datetime(r["trip_date"]).date(),
                                          format="DD/MM/YYYY")
                    f_start = b.number_input("Start odo", min_value=0, step=1, value=int(r["start_odo"]))
                    f_end = c.number_input("End odo", min_value=0, step=1, value=int(r["end_odo"]))
                    a, b = st.columns(2)
                    f_driver = a.text_input("Driver", value=r["driver"] or "")
                    f_vehicle = b.selectbox("Vehicle", list(VEHICLES), index=list(VEHICLES).index(r["vehicle"]))
                    a, b = st.columns(2)
                    f_from = a.text_input("From", value=r.get("from_location") or "")
                    f_to = b.text_input("To", value=r.get("to_location") or "")
                    f_purpose = st.text_input("Purpose", value=r.get("purpose") or "")
                    f_type = st.radio("Private / Business", TRIP_TYPES, horizontal=True,
                                      index=TRIP_TYPES.index(r.get("trip_type") or "Business"))
                    f_notes = st.text_area("Notes", value=r.get("notes") or "")
                    save = st.form_submit_button("💾 Save changes", type="primary")
                if save:
                    if f_end <= f_start:
                        st.error("End odometer must be higher than start odometer.")
                    else:
                        try:
                            sb.table(TABLE).update({
                                "trip_date": f_date.isoformat(), "start_odo": int(f_start),
                                "end_odo": int(f_end), "driver": f_driver.strip(),
                                "vehicle": f_vehicle, "rego": VEHICLES[f_vehicle]["rego"],
                                "from_location": f_from.strip(), "to_location": f_to.strip(),
                                "purpose": f_purpose.strip(), "trip_type": f_type,
                                "notes": f_notes.strip() or None,
                            }).eq("id", pick).execute()
                            st.session_state["_vl_notice"] = "✅ Entry updated."
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Update failed: {ex}")
                confirm = st.checkbox("Yes, delete this entry permanently", key=f"vl_del_ok_{pick}")
                if st.button("🗑️ Delete entry", disabled=not confirm, key=f"vl_del_{pick}"):
                    try:
                        sb.table(TABLE).delete().eq("id", pick).execute()
                        st.session_state["_vl_notice"] = "🗑️ Entry deleted."
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Delete failed: {ex}")
