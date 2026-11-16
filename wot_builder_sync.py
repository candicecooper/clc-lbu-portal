"""
wot_builder_sync.py — send Behaviour Support data into the Window of Tolerance Builder
=====================================================================================

Used by: pages/5_Behaviour_Support.py (Analysis page, Window of Tolerance section)

The WoT Builder (window-of-tolerance-builder.html on the Cloudflare launcher) keeps
one report per student in `wot_builder_reports` (its own Supabase project), with
data = {zone_id: {"context": [...], "behaviour": [...], "interventions": [...]}}
where each line is {"text": "...", "custom": bool}.

This module adds the student's Behaviour Support data into that report:
  * every incident behaviour type, intervention and context, in the zone the
    Behaviour Support WoT draft puts it (hyper / copingup / copingdown / hypo)
  * every micro behaviour (coping signs) in the two Coping zones, with the
    settings it came up in and what helped the student settle

Rules that keep staff in charge of the document:
  * Synced lines are tagged {"src": "bst", "key": ..., "synced_text": ...}.
    Lines staff add in the Builder are never touched.
  * A synced line staff REMOVE in the Builder is remembered and not re-added.
  * A synced line staff REWORD in the Builder becomes theirs and is left alone.
  * A synced line nobody has touched is removed if the data no longer supports it
    (e.g. an incident was deleted), so the report stays truthful.
  * The Window of Tolerance zone itself is never written to.

-------------------------------------------------------------------
SUPABASE SETUP — run once in the SQL editor of the WoT BUILDER's project
(the operational project the Builder page connects to — lvzaebjrxrgguypqvdcq):

create table if not exists wot_bst_sync (
    student_register_id text primary key,
    student_initials    text default '',
    synced_keys         jsonb not null default '[]'::jsonb,
    dismissed_keys      jsonb not null default '[]'::jsonb,
    synced_at           timestamptz default now()
);
alter table wot_bst_sync enable row level security;
create policy "wot_bst_sync_all" on wot_bst_sync for all using (true) with check (true);
-------------------------------------------------------------------
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

ZONES = ("hyper", "copingup", "wot", "copingdown", "hypo")
SYNC_ZONES = ("hyper", "copingup", "copingdown", "hypo")
COLS = ("context", "behaviour", "interventions")
SYNC_BY = "Behaviour Support Tool"
BUILDER_URL = "https://clc-portal.pages.dev/window-of-tolerance-builder.html"

SYNC_SQL = """create table if not exists wot_bst_sync (
    student_register_id text primary key,
    student_initials    text default '',
    synced_keys         jsonb not null default '[]'::jsonb,
    dismissed_keys      jsonb not null default '[]'::jsonb,
    synced_at           timestamptz default now()
);
alter table wot_bst_sync enable row level security;
create policy "wot_bst_sync_all" on wot_bst_sync for all using (true) with check (true);"""

_COUNT_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")


def norm(text: str) -> str:
    t = _COUNT_SUFFIX.sub("", str(text or "")).strip()
    return re.sub(r"\s+", " ", t)


def line_key(zone: str, col: str, text: str) -> str:
    return f"{zone}|{col}|{norm(text).lower()}"


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────
def _builder_creds() -> tuple[str, str] | None:
    """Same public URL/anon key the Builder page uses. Env vars win; otherwise
    read them from the copy of the Builder kept in the repo (as Student
    Snapshot already does)."""
    u, k = os.environ.get("WOT_BUILDER_URL"), os.environ.get("WOT_BUILDER_KEY")
    if u and k:
        return u, k
    here = Path(__file__).resolve().parent
    for f in (here / "pages" / "53_Window_of_tolerance-creator.py",
              here / "window-of-tolerance-builder.html"):
        try:
            src = f.read_text(encoding="utf-8")
            mu = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', src)
            mk = re.search(r'SUPABASE_ANON_KEY\s*=\s*"([^"]+)"', src)
            if mu and mk:
                return mu.group(1), mk.group(1)
        except Exception:
            continue
    return None


def get_builder_client():
    creds = _builder_creds()
    if not creds:
        return None
    from supabase import create_client
    return create_client(*creds)


def find_register_student(client, initials: str) -> dict | None:
    """The Builder's own student list (student_directory), matched by register
    initials — the same code the Behaviour Support Tool stores as the name."""
    ini = (initials or "").strip().upper()
    if not ini:
        return None
    rows = client.table("student_directory").select("*").execute().data or []
    hits = [r for r in rows if str(r.get("initials") or "").strip().upper() == ini
            and str(r.get("status") or "").strip().lower() != "archived"]
    return hits[0] if hits else None


# ──────────────────────────────────────────────────────────────────────────
# What to send
# ──────────────────────────────────────────────────────────────────────────
def desired_lines(wot_all: dict) -> dict:
    """{zone: {col: [text,...]}} from a WoT dict shaped like the Behaviour
    Support draft (zone -> {context, behaviour, interventions, micro?})."""
    out = {z: {c: [] for c in COLS} for z in SYNC_ZONES}

    def add(z, c, t):
        t = norm(t)
        if t and t not in ("—", "-") and t.lower() not in {x.lower() for x in out[z][c]}:
            out[z][c].append(t)

    for z in SYNC_ZONES:
        zd = (wot_all or {}).get(z) or {}
        for c in COLS:
            for t in zd.get(c, []) or []:
                add(z, c, t)
        m = zd.get("micro") or {}
        for c in COLS:
            for t in m.get(c, []) or []:
                add(z, c, t)
    return out


# ──────────────────────────────────────────────────────────────────────────
# Merge (pure — no database)
# ──────────────────────────────────────────────────────────────────────────
def merge(report_data: dict | None, desired: dict, synced_keys: set, dismissed_keys: set) -> dict:
    """Returns {"data", "synced_keys", "dismissed_keys", "added", "removed", "kept_by_staff"}."""
    data = {z: {c: [dict(i) for i in ((report_data or {}).get(z, {}) or {}).get(c, []) or []
                    if isinstance(i, dict)] for c in COLS} for z in ZONES}
    dismissed = set(dismissed_keys)
    added = removed = kept = 0

    present = set()
    for z in SYNC_ZONES:
        for c in COLS:
            for it in data[z][c]:
                if it.get("src") == "bst" and it.get("key"):
                    present.add(it["key"])
    # synced before, not there now -> a teacher removed it in the Builder
    dismissed |= (set(synced_keys) - present)

    want_keys = set()
    for z in SYNC_ZONES:
        for c in COLS:
            want = {line_key(z, c, t): t for t in desired.get(z, {}).get(c, [])}
            want_keys |= set(want)
            lst = data[z][c]
            # drop untouched synced lines the data no longer supports
            keep = []
            for it in lst:
                if it.get("src") == "bst":
                    edited = norm(it.get("text")) != norm(it.get("synced_text", it.get("text")))
                    if edited:
                        it["src"] = "bst-edited"          # staff reworded it: theirs now
                        kept += 1
                    elif it.get("key") not in want:
                        removed += 1
                        continue
                keep.append(it)
            lst[:] = keep
            have_text = {norm(i.get("text")).lower() for i in lst}
            have_keys = {i.get("key") for i in lst if i.get("key")}
            for k, t in want.items():
                if k in have_keys or k in dismissed or norm(t).lower() in have_text:
                    continue
                lst.append({"text": t, "custom": False, "src": "bst", "key": k, "synced_text": t})
                added += 1

    now_synced = set()
    for z in SYNC_ZONES:
        for c in COLS:
            for it in data[z][c]:
                if it.get("src") == "bst" and it.get("key"):
                    now_synced.add(it["key"])
    # forget dismissals for lines the data no longer produces at all
    dismissed &= want_keys
    return {"data": data, "synced_keys": sorted(now_synced), "dismissed_keys": sorted(dismissed),
            "added": added, "removed": removed, "kept_by_staff": kept}


# ──────────────────────────────────────────────────────────────────────────
# Sync (database)
# ──────────────────────────────────────────────────────────────────────────
class SyncTableMissing(Exception):
    pass


def sync_student(initials: str, wot_all: dict, client=None) -> dict:
    """Push this student's lines into their Builder report. Returns a summary
    dict {ok, added, removed, kept_by_staff, created, register_name, report_id}
    or {ok: False, reason}. Raises SyncTableMissing if wot_bst_sync isn't set up."""
    client = client or get_builder_client()
    if client is None:
        return {"ok": False, "reason": "Couldn't find the Window of Tolerance Builder's connection details."}
    stu = find_register_student(client, initials)
    if not stu:
        return {"ok": False, "reason": f"No active student with initials {initials} in the Builder's "
                                       f"student list (Student Register)."}
    rid = str(stu.get("id"))
    try:
        srow = (client.table("wot_bst_sync").select("*").eq("student_register_id", rid)
                .limit(1).execute().data or [])
    except Exception as e:
        raise SyncTableMissing(str(e))
    srow = srow[0] if srow else {}

    reps = (client.table("wot_builder_reports").select("*").eq("student_register_id", rid)
            .order("updated_at", desc=True).limit(1).execute().data or [])
    rep = reps[0] if reps else None

    res = merge(rep.get("data") if rep else None, desired_lines(wot_all),
                set(srow.get("synced_keys") or []), set(srow.get("dismissed_keys") or []))
    now = datetime.now(timezone.utc).isoformat()
    changed = bool(res["added"] or res["removed"] or res["kept_by_staff"])
    created = False
    if rep is None:
        if res["added"]:
            ins = client.table("wot_builder_reports").insert({
                "student_register_id": rid, "student_initials": stu.get("initials"),
                "data": res["data"], "print_style": "grid", "status": "draft",
                "created_by": SYNC_BY, "updated_by": SYNC_BY, "updated_at": now,
            }).execute()
            rep = (ins.data or [{}])[0]
            created = True
    elif changed:
        client.table("wot_builder_reports").update({
            "data": res["data"], "updated_by": SYNC_BY, "updated_at": now,
        }).eq("id", rep["id"]).execute()

    client.table("wot_bst_sync").upsert({
        "student_register_id": rid, "student_initials": stu.get("initials"),
        "synced_keys": res["synced_keys"], "dismissed_keys": res["dismissed_keys"],
        "synced_at": now,
    }, on_conflict="student_register_id").execute()

    return {"ok": True, "added": res["added"], "removed": res["removed"],
            "kept_by_staff": res["kept_by_staff"], "created": created,
            "register_name": stu.get("full_name") or stu.get("initials"),
            "report_id": (rep or {}).get("id"), "total_synced": len(res["synced_keys"])}
