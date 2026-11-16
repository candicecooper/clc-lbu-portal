"""
end_of_placement.py — End-of-placement document pack
=====================================================

When a student is archived in the Student Register, this gathers their
final documents from every tool and files them in the student's
Document Archive folder, so staff don't have to open each tool and save
each report by hand.

    Item                    What happens
    ──────────────────────  ─────────────────────────────────────────────
    SMARTAR Goal Report     Always regenerated from the goal + tracking data
                            (same PDF as the SMARTAR Goal Builder's
                            "Generate PDF Report"). Replaces the older one.
    Behaviour Summary       Always regenerated from incident data (same Word
                            report as the Behaviour Support Tool's
                            "Behaviour Summary (Word)"). Replaces the older one.
    Sensory Overview        If one exists and the archive doesn't already
                            have a copy at least as new, the latest overview
                            is filed (the Sensory Overview's own Word report).
    Window of Tolerance     If one has been built and the archive doesn't
                            already have a copy at least as new, a Word copy
                            of the saved zones is filed.
    Safety & Risk Plan      CHECKED only. The builder keeps no saved data
                            (Word/Excel files only), so it can't be rebuilt —
                            staff are told if one isn't on file.

How the tools' own code is reused
    Each report is built by the tool's OWN functions, read from its page
    file without running that page (same approach as the Student Snapshot's
    _borrow). So the archived report is identical to the one staff would
    get by opening the tool, and it never drifts when a tool is updated.

Never raises. Every item reports one of:
    filed    — a new document was saved to the archive
    already  — an up-to-date copy was already on file (nothing added)
    none     — the tool has nothing for this student
    failed   — something went wrong (detail says what)
"""

from __future__ import annotations

import ast
import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import streamlit as st

from archive_utils import (
    _get_client as _archive_client,
    archive_document,
    fetch_archive,
    initials_from_name,
)

PAGES_DIR = Path(__file__).parent / "pages"

BEHAVIOUR_PAGE = "5_Behaviour_Support.py"
SMARTAR_PAGE = "25_SMARTAR_Goal_Builder.py"
SENSORY_PAGE = "7_Sensory_Overview.py"
WOT_PAGE = "53_Window_of_tolerance-creator.py"

# Modules a page imports that must NOT be re-imported here (they draw UI or
# check logins at import time).
_SKIP_IMPORTS = {"streamlit", "theme", "staff_auth", "auth", "confidential_auth"}

WOT_ZONES = [
    ("hyper", "Mobilisation — Hyperarousal"),
    ("copingup", "Coping — moving toward Hyperarousal"),
    ("wot", "Window of Tolerance"),
    ("copingdown", "Coping — moving toward Hypoarousal"),
    ("hypo", "Immobilisation — Hypoarousal"),
]
WOT_COLS = [("context", "When / where"), ("behaviour", "What it looks like"),
            ("interventions", "What helps")]


# ──────────────────────────────────────────────────────────────────────────
# Borrowing a tool's own functions without running its page
# ──────────────────────────────────────────────────────────────────────────
class _AttrDict(dict):
    """dict that also allows attribute access — stands in for st.session_state."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v


class _StShim:
    """Stand-in for `st` inside borrowed functions. Secrets and caching go to
    the real Streamlit; on-screen messages are collected (not shown); a
    private session_state is used so the Register's own state is untouched."""

    def __init__(self, session_state: dict | None = None):
        self.session_state = _AttrDict(session_state or {})
        self.messages: list[str] = []
        self.secrets = st.secrets
        self.cache_resource = st.cache_resource
        self.cache_data = st.cache_data

    def _note(self, *a, **_k):
        if a:
            self.messages.append(str(a[0]))

    error = warning = info = success = toast = caption = write = markdown = _note

    def stop(self):
        raise RuntimeError("tool stopped: " + (self.messages[-1] if self.messages else "unknown"))

    def __getattr__(self, name):
        # Any other UI call (columns, spinner, …) — a harmless no-op.
        def _noop(*_a, **_k):
            return None
        return _noop


def _borrow(filename: str, names: tuple, shim: _StShim) -> dict:
    """Load the named top-level functions/constants from a page file PLUS
    everything they depend on (transitively), with the page's own imports,
    and return the resulting namespace. The page itself is never run."""
    src = (PAGES_DIR / filename).read_text(encoding="utf-8")
    tree = ast.parse(src)

    defs: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defs[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = node

    want, seen = list(names), set()
    while want:
        w = want.pop()
        if w in seen or w not in defs:
            continue
        seen.add(w)
        for x in ast.walk(defs[w]):
            if isinstance(x, ast.Name) and x.id in defs and x.id not in seen:
                want.append(x.id)

    def _imports_ok(node) -> bool:
        mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                else [node.module or ""])
        return not any(m.split(".")[0] in _SKIP_IMPORTS for m in mods)

    ns: dict = {"st": shim, "__name__": f"borrowed_{Path(filename).stem}"}
    # 1. the page's imports (top level, and simple try/except import blocks)
    for node in tree.body:
        chunk = None
        if isinstance(node, (ast.Import, ast.ImportFrom)) and _imports_ok(node):
            chunk = node
        elif isinstance(node, ast.Try) and all(
                isinstance(b, (ast.Import, ast.ImportFrom, ast.Assign, ast.Expr))
                for b in node.body) and all(
                _imports_ok(b) for b in node.body if isinstance(b, (ast.Import, ast.ImportFrom))):
            chunk = node
        if chunk is not None:
            try:
                exec(compile(ast.Module([chunk], []), filename, "exec"), ns)  # noqa: S102
            except Exception:
                pass
    ns["st"] = shim  # an import block may have rebound it

    # 2. the needed definitions, in file order (so constants exist before use)
    ordered = [n for n in tree.body if any(defs.get(s) is n for s in seen)]
    exec(compile(ast.Module(ordered, []), filename, "exec"), ns)  # noqa: S102
    return ns


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def _name_matches(name, ini: str) -> bool:
    """Same rule as the Student Snapshot: initials-only rows, prefix names
    like 'JT (PY)', and legacy full-name rows."""
    n = str(name or "").strip()
    if not n:
        return False
    up = n.upper()
    if up == ini:
        return True
    if up.startswith(ini) and not up[len(ini):len(ini) + 1].isalpha():
        return True
    return initials_from_name(n) == ini


def _ts(v) -> datetime | None:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _on_file_since(ini: str, doc_type: str, since) -> dict | None:
    """The newest archived document of this type filed at/after `since`."""
    try:
        docs = fetch_archive(student_initials=ini, doc_type=doc_type,
                             include_confidential=True, limit=20) or []
    except Exception:
        docs = []
    since_t = _ts(since)
    for d in docs:
        t = _ts(d.get("created_at") or d.get("uploaded_at"))
        if since_t is None or (t and t >= since_t):
            return d
    return None


def _loads(v, default):
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def _result(item, status, detail=""):
    return {"item": item, "status": status, "detail": detail}


# ──────────────────────────────────────────────────────────────────────────
# Each document
# ──────────────────────────────────────────────────────────────────────────
def _smartar_report(ini: str, created_by: str) -> dict:
    item = "SMARTAR Goal Report"
    try:
        import matplotlib
        matplotlib.use("Agg")
        shim = _StShim()
        ns = _borrow(SMARTAR_PAGE, ("make_student_pdf", "make_goal_chart_mpl", "goal_date_range",
                                    "get_tracking_range", "get_all_goals_for_student",
                                    "SESSIONS_FOR_PERIOD", "ALL_SESSIONS", "_q"), shim)
        # Goals are stored under the SMARTAR student name — the register's
        # initials, or a legacy name that reduces to them.
        names = {ini}
        try:
            rows = ns["_q"](lambda c: c.table("smartar_students").select("student_name")
                            .execute().data or [])
            names |= {r["student_name"] for r in rows if _name_matches(r.get("student_name"), ini)}
        except Exception:
            pass
        goals = []
        for nm in sorted(names):
            goals += ns["get_all_goals_for_student"](nm) or []
        if not goals:
            return _result(item, "none", "No SMARTAR goals set for this student.")

        charts = []
        for goal in goals:
            sessions = ns["SESSIONS_FOR_PERIOD"].get(goal.get("tracking_period", "All Day"),
                                                     ns["ALL_SESSIONS"])
            from_d, to_d = ns["goal_date_range"](goal)
            tracking = ns["get_tracking_range"](goal["id"], from_d, to_d, sessions=sessions)
            if not tracking:
                continue
            a_from = min(r["session_date"] for r in tracking)[:10]
            a_to = max(r["session_date"] for r in tracking)[:10]
            png = ns["make_goal_chart_mpl"](tracking, goal.get("smartar_goal", "No goal text"),
                                            a_from, a_to, student_name=ini)
            if png:
                charts.append((goal, png, a_from, a_to))
        if not charts:
            return _result(item, "none",
                           f"{len(goals)} goal(s) set, but no tracking recorded — nothing to report.")

        pdf = ns["make_student_pdf"](ini, charts)
        rec = archive_document(
            source_tool="SMARTAR Goal Builder",
            doc_type="SMARTAR Goals",
            title=f"SMARTAR Progress Report — {ini} — end of placement",
            file_bytes=pdf,
            filename=f"{ini}_SMARTAR_Progress_Report_{datetime.now():%Y%m%d}_final.pdf",
            student_initials=ini,
            created_by=created_by,
            notes="Auto-filed when the student was archived in the Student Register.",
            supersede=True,
        )
        if rec:
            return _result(item, "filed", f"{len(charts)} goal chart(s).")
        return _result(item, "failed", "Built the report but the archive didn't confirm the save.")
    except Exception as exc:  # noqa: BLE001
        return _result(item, "failed", f"Couldn't build the report: {exc}")


def _behaviour_report(ini: str, created_by: str) -> tuple[dict, list[str]]:
    """Returns (result, behaviour-tool student ids) — ids are reused to find
    the Sensory Overview."""
    item = "Behaviour Summary"
    ids: list[str] = []
    try:
        shim = _StShim()
        ns = _borrow(BEHAVIOUR_PAGE, ("load_students_from_db", "load_incidents_from_db",
                                      "load_critical_incidents_from_db", "load_staff_from_db",
                                      "build_student_full_df", "compute_analysis_stats",
                                      "generate_behaviour_analysis_plan_docx"), shim)
        students = ns["load_students_from_db"]() or []
        matched = [s for s in students
                   if str(s.get("first_name") or "").strip().upper() == ini
                   or _name_matches(s.get("name"), ini)]
        ids = [str(s["id"]) for s in matched]
        if not matched:
            return _result(item, "none", "Not found in the Behaviour Support Tool."), ids

        # The tool's report reads these from its session — fill them the same way it does.
        shim.session_state.update({
            "students": students,
            "staff": ns["load_staff_from_db"]() or [],
            "incidents": ns["load_incidents_from_db"]() or [],
            "critical_incidents": ns["load_critical_incidents_from_db"]() or [],
        })
        best, best_df = None, None
        for s in matched:
            df, _ = ns["build_student_full_df"](s["id"])
            if not df.empty and (best_df is None or len(df) > len(best_df)):
                best, best_df = s, df
        if best is None:
            return _result(item, "none", "No incidents recorded — nothing to report."), ids

        top_beh, top_ant, top_loc, top_ses, score, level = ns["compute_analysis_stats"](best_df)
        docx = ns["generate_behaviour_analysis_plan_docx"](
            best, best_df, top_ant, top_beh, top_loc, top_ses, score, level,
            supports_trialled="", supports_success="", before_after=None)
        if not docx:
            return _result(item, "failed", "The Behaviour Support Tool couldn't build the report."), ids
        rec = archive_document(
            source_tool="Behaviour Support Tool",
            doc_type="Behaviour Report",
            title=f"Behaviour Summary — {ini} — end of placement",
            file_bytes=docx.getvalue() if hasattr(docx, "getvalue") else docx,
            filename=f"BehaviourSummary_{ini}_{datetime.now():%Y%m%d}_final.docx",
            student_initials=ini,
            created_by=created_by,
            notes="Auto-filed when the student was archived in the Student Register.",
            supersede=True,
        )
        note = f"{len(best_df)} incident(s)."
        if len([s for s in matched]) > 1:
            note += f" ({len(matched)} matching records in the tool — used the one with most data.)"
        if rec:
            return _result(item, "filed", note), ids
        return _result(item, "failed", "Built the report but the archive didn't confirm the save."), ids
    except Exception as exc:  # noqa: BLE001
        return _result(item, "failed", f"Couldn't build the report: {exc}"), ids


def _sensory_overview(ini: str, register_id: str, beh_ids: list[str], created_by: str) -> dict:
    item = "Sensory Overview"
    try:
        rows = (_archive_client().table("sensory_overviews").select("*")
                .order("created_at", desc=True).execute().data or [])
        keys = {str(register_id)} | set(beh_ids)
        mine = [r for r in rows
                if (r.get("student_id") and str(r["student_id"]) in keys)
                or _name_matches(r.get("student_name"), ini)]
        if not mine:
            return _result(item, "none", "No Sensory Overview has been completed.")
        mine.sort(key=lambda r: (str(r.get("overview_date") or ""), str(r.get("created_at") or "")),
                  reverse=True)
        rec = mine[0]
        since = rec.get("updated_at") or rec.get("created_at")
        if _on_file_since(ini, "Sensory Overview", since):
            return _result(item, "already", f"Latest overview ({rec.get('overview_date') or '—'}) is on file.")

        fn = _borrow(SENSORY_PAGE, ("generate_word_report",), _StShim())["generate_word_report"]
        data = fn(rec)
        data = data.getvalue() if hasattr(data, "getvalue") else data
        ov = rec.get("overview_date") or f"{date.today():%Y-%m-%d}"
        saved = archive_document(
            source_tool="Sensory Overview",
            doc_type="Sensory Overview",
            title=f"Sensory Overview — {ini} — {ov}",
            file_bytes=data,
            filename=f"sensory_{ini}_{ov}.docx",
            student_initials=ini,
            created_by=created_by,
            notes="Auto-filed when the student was archived in the Student Register.",
            supersede=True,
        )
        if saved:
            return _result(item, "filed", f"Overview dated {ov}.")
        return _result(item, "failed", "Built the report but the archive didn't confirm the save.")
    except Exception as exc:  # noqa: BLE001
        return _result(item, "failed", f"Couldn't check or file it: {exc}")


def _wot_creds():
    """The WoT Builder connects with its own public URL/key — read from its page."""
    import re
    try:
        src = (PAGES_DIR / WOT_PAGE).read_text(encoding="utf-8")
        u = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', src)
        k = re.search(r'SUPABASE_ANON_KEY\s*=\s*"([^"]+)"', src)
        return (u.group(1), k.group(1)) if u and k else None
    except Exception:
        return None


def _wot_docx(ini: str, rep: dict) -> bytes | None:
    from docx import Document
    from docx.shared import Pt

    data = _loads(rep.get("data"), {})
    zones = []
    for zid, label in WOT_ZONES:
        z = data.get(zid) or {}
        cols = {}
        for col, _lbl in WOT_COLS:
            vals = []
            for i in z.get(col) or []:
                t = str(i.get("text") if isinstance(i, dict) else i).strip()
                if t:
                    vals.append(t)
            cols[col] = vals
        if any(cols.values()):
            zones.append((label, cols))
    if not zones:
        return None

    doc = Document()
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(f"Window of Tolerance — {ini}", level=1)
    upd = str(rep.get("updated_at") or "")[:10]
    doc.add_paragraph("CLC Learning and Behaviour Unit · end-of-placement copy"
                      + (f" · last updated {upd}" if upd else ""))
    for label, cols in zones:
        doc.add_heading(label, level=2)
        tbl = doc.add_table(rows=1, cols=len(WOT_COLS))
        tbl.style = "Table Grid"
        for i, (_c, lbl) in enumerate(WOT_COLS):
            tbl.rows[0].cells[i].text = lbl
            for r in tbl.rows[0].cells[i].paragraphs[0].runs:
                r.bold = True
        row = tbl.add_row().cells
        for i, (c, _lbl) in enumerate(WOT_COLS):
            row[i].text = "\n".join(f"• {v}" for v in cols[c]) or "—"
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _window_of_tolerance(ini: str, register_id: str, created_by: str) -> dict:
    item = "Window of Tolerance"
    try:
        def fetch(c):
            rows = (c.table("wot_builder_reports").select("*")
                    .eq("student_initials", ini).execute().data or [])
            if register_id:
                rows += (c.table("wot_builder_reports").select("*")
                         .eq("student_register_id", register_id).execute().data or [])
            return rows

        rows, err = [], None
        try:
            rows = fetch(_archive_client())
        except Exception as exc:  # noqa: BLE001
            err = exc
        if not rows:
            creds = _wot_creds()
            if creds:
                from supabase import create_client
                try:
                    rows = fetch(create_client(*creds))
                    err = None
                except Exception as exc:  # noqa: BLE001
                    err = err or exc
        if not rows:
            if err:
                return _result(item, "failed", f"Couldn't reach the Window of Tolerance Builder: {err}")
            return _result(item, "none", "No Window of Tolerance has been built.")

        rep = max({r.get("id"): r for r in rows}.values(), key=lambda r: str(r.get("updated_at") or ""))
        if _on_file_since(ini, "Window of Tolerance", rep.get("updated_at")):
            return _result(item, "already", "Latest version is on file.")
        data = _wot_docx(ini, rep)
        if not data:
            return _result(item, "none", "A Window of Tolerance was started but has no content.")
        saved = archive_document(
            source_tool="Window of Tolerance Builder",
            doc_type="Window of Tolerance",
            title=f"Window of Tolerance — {ini} — end of placement",
            file_bytes=data,
            filename=f"window_of_tolerance_{ini}_{datetime.now():%Y%m%d}_final.docx",
            student_initials=ini,
            confidential=True,
            created_by=created_by,
            notes="Auto-filed when the student was archived in the Student Register.",
            supersede=False,  # keep the Builder's own formatted copy alongside
        )
        if saved:
            return _result(item, "filed", "Word copy of the saved zones.")
        return _result(item, "failed", "Built the document but the archive didn't confirm the save.")
    except Exception as exc:  # noqa: BLE001
        return _result(item, "failed", f"Couldn't check or file it: {exc}")


def _safety_plan(ini: str) -> dict:
    item = "Safety & Risk Plan"
    d = _on_file_since(ini, "Safety & Risk Plan", None)
    if d:
        when = str(d.get("created_at") or "")[:10]
        return _result(item, "already", f"On file{f' (saved {when})' if when else ''}.")
    return _result(item, "none",
                   "Not in the archive. The builder doesn't keep saved data, so it can't be "
                   "filed automatically — if a plan exists, open the Safety & Risk Plan "
                   "Builder and use *Save to archive*.")


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────
def file_end_of_placement_pack(initials: str, register_id: str | None = None,
                               created_by: str = "auto (end of placement)") -> list[dict]:
    """Gather and file every end-of-placement document for one student.
    Returns a list of {item, status, detail}. Never raises."""
    ini = (initials or "").strip().upper()
    if not ini:
        return []
    out = [_smartar_report(ini, created_by)]
    beh, beh_ids = _behaviour_report(ini, created_by)
    out.append(beh)
    out.append(_sensory_overview(ini, register_id or "", beh_ids, created_by))
    out.append(_window_of_tolerance(ini, register_id or "", created_by))
    out.append(_safety_plan(ini))
    return out
