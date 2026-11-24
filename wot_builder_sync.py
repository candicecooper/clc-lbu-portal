"""
wot_builder_sync.py — send Behaviour Support data into the Window of Tolerance Builder
=====================================================================================

Used by: pages/5_Behaviour_Support.py (Analysis page, Window of Tolerance section)

The WoT Builder (window-of-tolerance-builder.html on the Cloudflare launcher) keeps
one report per student in `wot_builder_reports` (its own Supabase project), with
data = {zone_id: {"context": [...], "behaviour": [...], "interventions": [...]}}
where each line is {"text": "...", "custom": bool, "orig": neutral wording?}.

This module adds the student's Behaviour Support data into that report:
  * every incident behaviour type, intervention and context, in the zone the
    Behaviour Support WoT draft puts it (hyper / copingup / copingdown / hypo)
  * every micro behaviour (coping signs) in the two Coping zones, with the
    settings it came up in and what helped the student settle

Rules that keep staff in charge of the document:
  * New synced lines arrive tagged {"src": "bst", "key": ..., "synced_text": ...} and
    are shown highlighted in the Builder for staff to check.
  * Staff check each one: KEEP (src -> "bst-kept"), EDIT (src -> "bst-edited") or
    DELETE (the Builder records the key in wot_bst_sync.dismissed_keys on Save).
    Once checked, a line is the staff's: this module never changes, removes or
    re-adds it, so nobody has to re-check it on every sync.
  * Lines staff add in the Builder are never touched.
  * Only un-checked lines ("bst") are managed here: removed if the data no longer
    supports them (e.g. an incident was deleted), pronouns kept up to date.
  * A deletion only counts when the Builder recorded it. A synced line that is simply
    missing (e.g. a Builder tab saved an older copy over a sync) is added back for
    checking rather than silently lost.
  * The Window of Tolerance zone itself is never written to.
  * Every synced line is written with the student's own pronouns (the Builder's
    per-student setting, wot_builder_reports.pronouns) instead of "they / their /
    the student". The neutral wording is kept as "orig" and the line key is always
    built from it, so changing a student's pronouns is never mistaken for a staff
    edit, and the Builder (same rules, in JavaScript) and this module always agree.

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
# Student pronouns — same rules as the Builder page (window-of-tolerance-builder.html),
# so a line reads identically whichever side converts it. Generic wording
# ("they / their / the student / the child") becomes the student's own pronouns;
# text inside quotation marks is never changed. Rule-based, no AI.
# ──────────────────────────────────────────────────────────────────────────
PRONOUN_SETS = {
    "he":   {"subj": "he",   "obj": "him",  "poss": "his",   "possPron": "his",    "refl": "himself"},
    "she":  {"subj": "she",  "obj": "her",  "poss": "her",   "possPron": "hers",   "refl": "herself"},
    "they": {"subj": "they", "obj": "them", "poss": "their", "possPron": "theirs", "refl": "themselves"},
}
_PN_NOUNS = {"student", "child", "learner", "kid"}
_PN_ADVERBS = set("also often still just really usually always never sometimes only already even actually "
                  "quickly slowly suddenly rarely generally typically frequently mostly then now all both "
                  "first finally clearly".split())
_PN_KEEP_VERBS = set("can could will would should may might must shall can't couldn't won't wouldn't "
                     "shouldn't mustn't cannot had did felt got went said made came knew saw took found left "
                     "lost ran sat stood thought told gave kept began heard hadn't didn't hit put set let cut "
                     "needn't".split())
_PN_TO_SINGULAR = {"are": "is", "were": "was", "have": "has", "do": "does", "don't": "doesn't",
                   "aren't": "isn't", "weren't": "wasn't", "haven't": "hasn't", "go": "goes"}
_PN_SUBJ_LEAD = set("if when while because until unless before after so and that as where once whether "
                    "or but".split())
_PN_TOKEN = re.compile(r"([A-Za-z]+(?:['’][A-Za-z]+)?)|([^A-Za-z]+)")
_PN_QUOTES = re.compile(r"(“[^”]*”|\"[^\"]*\")")
_PN_BREAK = re.compile(r"[.,;:!?()—–]")


def normalise_pronouns(v) -> str | None:
    t = re.sub(r"\s+", "", str(v or "").lower())
    if t in ("he", "him", "his") or t.startswith("he/"):
        return "he"
    if t in ("she", "her") or t.startswith("she/"):
        return "she"
    if t in ("they", "them") or t.startswith("they/"):
        return "they"
    return None


def _pn_lower(w: str) -> str:
    return w.lower().replace("’", "'")


def _pn_case(src: str, out: str) -> str:
    if not src or not out:
        return out
    if len(src) > 1 and src == src.upper():
        return out.upper()
    if src[0] != src[0].lower():
        return out[0].upper() + out[1:]
    return out


def _pn_next(toks, i):
    j = i + 1
    if j < len(toks) and not toks[j]["w"]:
        if re.fullmatch(r"[ \t]+", toks[j]["t"]):
            j += 1
        else:
            return -1
    return j if j < len(toks) and toks[j]["w"] else -1


def _pn_prev(toks, i):
    j = i - 1
    if j >= 0 and not toks[j]["w"]:
        if re.fullmatch(r"[ \t]+", toks[j]["t"]):
            j -= 1
        else:
            return -1
    return j if j >= 0 and toks[j]["w"] else -1


def _pn_verb(toks, i):
    j, guard = _pn_next(toks, i), 0
    while j != -1 and _pn_lower(toks[j]["t"]) in _PN_ADVERBS and guard < 3:
        j = _pn_next(toks, j)
        guard += 1
    return j


def _pn_is_past(lv: str) -> bool:
    return lv.endswith("ed") and not lv.endswith("eed")


def _pn_singular(v: str) -> str:
    lv = _pn_lower(v)
    if lv in _PN_KEEP_VERBS or _pn_is_past(lv):
        return v
    if lv in _PN_TO_SINGULAR:
        return _pn_case(v, _PN_TO_SINGULAR[lv])
    if "'" in lv:
        return v
    if re.search(r"(s|x|z|ch|sh|o)$", lv):
        return v + "es"
    if re.search(r"[^aeiou]y$", lv):
        return v[:-1] + "ies"
    return v + "s"


def _pn_plural(v: str) -> str:
    lv = _pn_lower(v)
    to_plural = {"is": "are", "was": "were", "has": "have", "does": "do", "doesn't": "don't",
                 "isn't": "aren't", "wasn't": "weren't", "hasn't": "haven't", "goes": "go"}
    if lv in _PN_KEEP_VERBS or _pn_is_past(lv):
        return v
    if lv in to_plural:
        return _pn_case(v, to_plural[lv])
    if "'" in lv:
        return v
    if len(lv) > 4 and lv.endswith("ies"):
        return v[:-3] + "y"
    if re.search(r"(ss|x|z|ch|sh|o)es$", lv):
        return v[:-2]
    if re.search(r"[^su]s$", lv) and not re.search(r"(ss|us|is)$", lv):
        return v[:-1]
    return v


def _pn_convert_segment(seg: str, key: str) -> str:
    P = PRONOUN_SETS[key]
    toks = [{"w": bool(m.group(1)), "t": m.group(0)} for m in _PN_TOKEN.finditer(seg)]
    # 1) "the student's / this child / the student" -> pronoun
    i = 0
    while i < len(toks):
        tk = toks[i]
        if tk["w"] and _pn_lower(tk["t"]) in ("the", "this"):
            j = _pn_next(toks, i)
            nm = re.fullmatch(r"([a-z]+)('s)?", _pn_lower(toks[j]["t"])) if j != -1 else None
            if nm and nm.group(1) in _PN_NOUNS:
                is_subj = False
                if nm.group(2):
                    out = P["poss"]
                else:
                    p = _pn_prev(toks, i)
                    is_subj = (p == -1 and i == 0) or (p != -1 and _pn_lower(toks[p]["t"]) in _PN_SUBJ_LEAD)
                    out = P["subj"] if is_subj else P["obj"]
                toks[i] = {"w": True, "t": _pn_case(tk["t"], out), "done": True}
                del toks[i + 1:j + 1]
                if is_subj and key == "they":
                    v = _pn_verb(toks, i)
                    if v != -1:
                        toks[v] = {"w": True, "t": _pn_plural(toks[v]["t"]), "done": True}
        i += 1
    if key == "they":
        return "".join(t["t"] for t in toks)
    # 2) they / them / their / theirs / themselves -> he/she forms
    subj_active = False
    for i, tk in enumerate(toks):
        if not tk["w"]:
            if _PN_BREAK.search(tk["t"]):
                subj_active = False
            continue
        if tk.get("done"):
            continue
        lw = _pn_lower(tk["t"])
        if subj_active and lw in ("and", "or", "but"):
            cj = _pn_next(toks, i)
            if cj != -1 and not toks[cj].get("done") and _pn_lower(toks[cj]["t"]) in _PN_TO_SINGULAR:
                toks[cj] = {"w": True, "t": _pn_case(toks[cj]["t"], _PN_TO_SINGULAR[_pn_lower(toks[cj]["t"])]),
                            "done": True}
            continue
        rep = None
        if lw == "they":
            subj_active = True
            rep = P["subj"]
            vi = _pn_verb(toks, i)
            if vi != -1 and not toks[vi].get("done"):
                toks[vi] = {"w": True, "t": _pn_singular(toks[vi]["t"]), "done": True}
        elif lw in ("they're", "they've"):
            rep, subj_active = P["subj"] + "'s", True
        elif lw == "they'd":
            rep, subj_active = P["subj"] + "'d", True
        elif lw == "they'll":
            rep, subj_active = P["subj"] + "'ll", True
        elif lw == "them":
            rep = P["obj"]
        elif lw == "their":
            rep = P["poss"]
        elif lw == "theirs":
            rep = P["possPron"]
        elif lw in ("themselves", "themself"):
            rep = P["refl"]
        if rep:
            toks[i] = {"w": True, "t": _pn_case(tk["t"], rep), "done": True}
    return "".join(t["t"] for t in toks)


def convert_pronouns(text: str, pronouns) -> str:
    """Generic wording -> this student's pronouns ('he' / 'she' / 'they'). Unknown -> unchanged."""
    key = normalise_pronouns(pronouns)
    if not key or not text:
        return text
    parts = _PN_QUOTES.split(str(text))
    for i in range(0, len(parts), 2):
        parts[i] = _pn_convert_segment(parts[i], key)
    return "".join(parts)


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
def merge(report_data: dict | None, desired: dict, synced_keys: set, dismissed_keys: set,
          pronouns: str | None = None) -> dict:
    """Returns {"data", "synced_keys", "dismissed_keys", "added", "removed", "kept_by_staff",
    "converted"}. `pronouns` ('he' / 'she' / 'they', or None if not set yet) decides how
    synced lines are worded; keys always come from the neutral wording."""
    data = {z: {c: [dict(i) for i in ((report_data or {}).get(z, {}) or {}).get(c, []) or []
                    if isinstance(i, dict)] for c in COLS} for z in ZONES}
    dismissed = set(dismissed_keys)
    added = removed = kept = converted = 0

    # Deletions are recorded explicitly by the Builder (dismissed_keys) — a line that is
    # merely missing is NOT treated as deleted, so a stale save can't silently drop lines.

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
                    elif pronouns:
                        # untouched synced line: make sure it reads with this student's pronouns
                        base = it.get("orig") or it.get("synced_text") or it.get("text") or ""
                        shown = convert_pronouns(base, pronouns)
                        if shown != it.get("text"):
                            it["text"] = it["synced_text"] = shown
                            converted += 1
                        it["orig"] = base
                keep.append(it)
            lst[:] = keep
            have_text = {norm(i.get("text")).lower() for i in lst}
            have_text |= {norm(i.get("orig")).lower() for i in lst if i.get("orig")}
            have_keys = {i.get("key") for i in lst if i.get("key")}
            for k, t in want.items():
                shown = convert_pronouns(t, pronouns) if pronouns else t
                if (k in have_keys or k in dismissed or norm(t).lower() in have_text
                        or norm(shown).lower() in have_text):
                    continue
                lst.append({"text": shown, "custom": False, "src": "bst", "key": k,
                            "synced_text": shown, "orig": t})
                added += 1

    now_synced = set()
    for z in SYNC_ZONES:
        for c in COLS:
            for it in data[z][c]:
                if it.get("src") == "bst" and it.get("key"):
                    now_synced.add(it["key"])
    from_bst = sum(1 for z in SYNC_ZONES for c in COLS for it in data[z][c]
                   if str(it.get("src") or "").startswith("bst"))
    # forget dismissals for lines the data no longer produces at all
    dismissed &= want_keys
    return {"data": data, "synced_keys": sorted(now_synced), "dismissed_keys": sorted(dismissed),
            "added": added, "removed": removed, "kept_by_staff": kept, "converted": converted,
            "to_check": len(now_synced), "from_bst": from_bst}


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

    # The student's pronouns: set per report in the Builder (falls back to the register,
    # if it ever stores them). None = not chosen yet -> lines go in neutral and the
    # Builder converts them as soon as staff pick pronouns there.
    pronouns = normalise_pronouns((rep or {}).get("pronouns")) or normalise_pronouns(stu.get("pronouns"))
    res = merge(rep.get("data") if rep else None, desired_lines(wot_all),
                set(srow.get("synced_keys") or []), set(srow.get("dismissed_keys") or []),
                pronouns=pronouns)
    now = datetime.now(timezone.utc).isoformat()
    changed = bool(res["added"] or res["removed"] or res["kept_by_staff"] or res["converted"])
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
            "kept_by_staff": res["kept_by_staff"], "converted": res["converted"],
            "pronouns": pronouns, "created": created,
            "register_name": stu.get("full_name") or stu.get("initials"),
            "report_id": (rep or {}).get("id"), "total_synced": res["from_bst"],
            "to_check": res["to_check"]}
