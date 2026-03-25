"""
database.py — Supabase backend for LBU Staff Notice Board v2
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, date, timedelta
import uuid
import hashlib
import time
import json

# ── Retry wrapper ─────────────────────────────────────────────────────────────
def _execute(query, retries: int = 3, base_delay: float = 0.4):
    """
    Call query.execute() with automatic retry on transient network errors.

    Catches httpx.ReadError (errno 11 EAGAIN), httpx.ConnectError,
    httpx.RemoteProtocolError and httpx.TimeoutException — all of which are
    momentary socket/buffer blips between Render and Supabase that resolve
    on a re-attempt.  Uses exponential back-off:
      attempt 1 → wait 0.4 s, attempt 2 → wait 0.8 s, attempt 3 → wait 1.6 s.

    If every retry fails the exception is re-raised so the caller's
    try/except can show a graceful message instead of crashing the page.
    Non-transient exceptions (e.g. bad SQL, auth failures) are raised
    immediately without retrying.
    """
    try:
        import httpx as _httpx
        _transient = (
            _httpx.ReadError,
            _httpx.ConnectError,
            _httpx.RemoteProtocolError,
            _httpx.TimeoutException,
        )
    except ImportError:
        # httpx not installed — fall through, no retry on network errors
        _transient = ()

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return query.execute()
        except _transient as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(base_delay * (2 ** (attempt - 1)))
        except Exception:
            raise   # non-transient — propagate immediately
    raise last_exc


STORAGE_BUCKET = "notice-attachments"

# ── Connection ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ── Week helpers ──────────────────────────────────────────────────────────────
def get_current_monday() -> date:
    """Return the Monday of the current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())

# ── SA School Calendar 2026 ──────────────────────────────────────────────────
# Each tuple: (term_number, first_monday_of_term, number_of_weeks)
SA_TERMS_2026 = [
    (1, date(2026, 1, 26), 11),   # Term 1: 26 Jan – 10 Apr
    (2, date(2026, 4, 27), 10),   # Term 2: 27 Apr – 3 Jul
    (3, date(2026, 7, 20), 10),   # Term 3: 20 Jul – 25 Sep
    (4, date(2026, 10, 12), 9),   # Term 4: 12 Oct – 11 Dec
]

def get_term_and_week(monday: date):
    """Return (term_num, week_num, total_weeks) or None if in holidays."""
    for term_num, term_start, total_weeks in SA_TERMS_2026:
        if monday < term_start:
            break
        week_num = (monday - term_start).days // 7 + 1
        if 1 <= week_num <= total_weeks:
            return term_num, week_num, total_weeks
    return None, None, None

def week_label(monday: date) -> str:
    term_num, week_num, total_weeks = get_term_and_week(monday)
    date_str = monday.strftime("%-d %b %Y")
    if term_num is None:
        return f"School Holidays  ·  {date_str}"
    return f"Term {term_num}  ·  Week {week_num} of {total_weeks}  ·  {date_str}"

# ── Weekly Editions ───────────────────────────────────────────────────────────
def get_or_create_current_edition() -> dict:
    """
    Returns the draft edition staff should be submitting into.
    - Mon/Tue: this week (admin reviewing/publishing current week)
    - Wed onwards: next week (current week published, staff submit for next)
    """
    client = get_client()
    today  = date.today()
    if today.weekday() >= 2:
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
    else:
        monday = today - timedelta(days=today.weekday())
    correct_label = week_label(monday)
    try:
        result = _execute(
            client.table("weekly_editions")
                .select("*")
                .eq("week_start", monday.isoformat())
                .single()
        )
        row = result.data
        if row and row.get("week_label") != correct_label:
            _execute(
                client.table("weekly_editions")
                    .update({"week_label": correct_label})
                    .eq("id", row["id"])
            )
            row["week_label"] = correct_label
        return row
    except:
        pass
    try:
        result = _execute(
            client.table("weekly_editions").insert({
                "week_start": monday.isoformat(),
                "week_label": week_label(monday),
                "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        )
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Error creating edition: {e}")
        return None

def get_edition(edition_id) -> dict:
    try:
        client = get_client()
        result = _execute(
            client.table("weekly_editions")
                .select("*").eq("id", edition_id).single()
        )
        return result.data
    except:
        return None

def get_current_published_edition() -> dict:
    """Get the published edition for the current week only, with fresh label."""
    try:
        client = get_client()
        current_monday = get_current_monday()
        result = _execute(
            client.table("weekly_editions")
                .select("*")
                .eq("status", "published")
                .eq("week_start", current_monday.isoformat())
                .limit(1)
        )
        row = result.data[0] if result.data else None
        if row:
            fresh = week_label(current_monday)
            if row.get("week_label") != fresh:
                _execute(
                    client.table("weekly_editions")
                        .update({"week_label": fresh})
                        .eq("id", row["id"])
                )
                row["week_label"] = fresh
        return row
    except:
        return None

def get_all_editions() -> list:
    """All editions ordered newest first."""
    try:
        client = get_client()
        result = _execute(
            client.table("weekly_editions")
                .select("*")
                .order("week_start", desc=True)
        )
        return result.data or []
    except Exception as e:
        st.error(f"Error loading editions: {e}")
        return []

def publish_edition(edition_id, published_by: str) -> bool:
    try:
        client = get_client()
        _execute(
            client.table("weekly_editions").update({
                "status": "published",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "published_by": published_by
            }).eq("id", edition_id)
        )
        return True
    except Exception as e:
        st.error(f"Error publishing edition: {e}")
        return False

def unpublish_edition(edition_id) -> bool:
    """Revert a published edition back to draft so admin can amend it."""
    try:
        client = get_client()
        _execute(
            client.table("weekly_editions").update({
                "status": "draft",
                "published_at": None,
                "published_by": None
            }).eq("id", edition_id)
        )
        return True
    except Exception as e:
        st.error(f"Error reopening edition: {e}")
        return False

def sync_to_staff_minutes(edition_id) -> tuple:
    """Build formatted minutes from a published digital staff meeting and merge
    with any face-to-face minutes for the same week into one record in tm_minutes.
    Returns (success: bool, message: str)."""
    import re as _re
    try:
        client = get_client()

        ed = _execute(
            client.table("weekly_editions").select("*").eq("id", edition_id).single()
        ).data
        if not ed:
            return False, "Edition not found."

        week_start     = ed.get("week_start", "")
        week_label_str = ed.get("week_label", "")
        published_by   = ed.get("published_by", "Admin")

        from datetime import date as _date
        monday   = _date.fromisoformat(week_start)
        week_end = (monday + timedelta(days=6)).isoformat()

        agenda_rows = _execute(
            client.table("agenda_items").select("*")
                .eq("edition_id", edition_id).order("created_at")
        ).data or []

        notices = _execute(
            client.table("notices").select("*")
                .eq("edition_id", edition_id).order("created_at")
        ).data or []

        notice_ids = [n["id"] for n in notices]
        all_notice_actions = []
        if notice_ids:
            all_notice_actions = _execute(
                client.table("notice_actions").select("*").in_("notice_id", notice_ids)
            ).data or []
        actions_by_notice = {}
        for a in all_notice_actions:
            actions_by_notice.setdefault(a["notice_id"], []).append(a["action_text"])

        attendance_rows = _execute(
            client.table("tm_attendance").select("*")
                .eq("program", "STAFF")
                .gte("meeting_date", week_start)
                .lte("meeting_date", week_end)
        ).data or []

        present   = sorted([r["staff_name"] for r in attendance_rows if r.get("status") == "present"])
        apologies = sorted([r["staff_name"] for r in attendance_rows if r.get("status") in ("absent", "apology")])

        SECTION_LABELS = {
            "pac":        "PAC",
            "whs":        "WHS",
            "profdev":    "Professional Development",
            "curriculum": "Curriculum",
            "welfare":    "Student Welfare",
            "timetable":  "Timetable",
        }

        by_sec = {}
        for it in agenda_rows:
            if it.get("content", "").startswith("TIMETABLE_PATH::"):
                continue
            by_sec.setdefault(it.get("section", ""), []).append(it)

        seen_titles = set()
        unique_notices = []
        for n in notices:
            t = n.get("title", "").strip()
            if t not in seen_titles:
                seen_titles.add(t)
                unique_notices.append(n)

        pub_date = monday.strftime("%-d %B %Y")
        lines = [
            "## 💻 Digital Staff Meeting",
            "",
            f"**Date:** {pub_date}  ",
            f"**Published by:** {published_by}  ",
            f"**Platform:** CLC Digital Staff Meeting",
            "",
        ]

        if present or apologies:
            lines.append("**Attendance**")
            if present:
                lines.append(f"- Present: {', '.join(present)}")
            if apologies:
                lines.append(f"- Apologies: {', '.join(apologies)}")
            lines.append("")

        if by_sec:
            lines.append("**Standing Agenda Items**")
            lines.append("")
            for sec, items in by_sec.items():
                sec_label = SECTION_LABELS.get(sec, sec.upper())
                lines.append(f"**{sec_label}:**")
                for it in items:
                    lines.append(f"- {it.get('content', '')}")
                lines.append("")

        if unique_notices:
            lines.append("**Notices & Updates**")
            lines.append("")
            all_digital_actions = []
            for n in unique_notices:
                cat   = n.get("category", "general").title()
                clean = _re.sub('<[^<]+?>', '', n.get("content", "")).strip()
                lines.append(f"**{n['title']}** *({cat})*")
                lines.append(f"*{n.get('author','')} · {n.get('audience','All Staff')}*")
                if clean:
                    lines.append(clean)
                n_acts = actions_by_notice.get(n["id"], [])
                if n_acts:
                    for a in n_acts:
                        lines.append(f"- Action: {a}")
                        all_digital_actions.append(f"{a} (re: {n['title']})")
                lines.append("")

        digital_section = "\n".join(lines)

        action_summary = " · ".join(
            f"{a} (re: {n['title']})"
            for n in unique_notices
            for a in actions_by_notice.get(n["id"], [])
        )

        all_staff_mins = _execute(
            client.table("tm_minutes").select("*")
                .eq("program", "STAFF")
                .gte("meeting_date", week_start)
                .lte("meeting_date", week_end)
        ).data or []

        digital_tag  = "<!-- digital-staff-meeting -->"
        digital_recs = [m for m in all_staff_mins if digital_tag in m.get("content", "")]
        f2f_recs     = [m for m in all_staff_mins if digital_tag not in m.get("content", "")]

        f2f_section        = ""
        f2f_action_summary = ""
        if f2f_recs:
            f2f_parts    = []
            f2f_act_parts = []
            for m in f2f_recs:
                f2f_parts.append(m.get("content", "").strip())
                if m.get("action_summary"):
                    f2f_act_parts.append(m["action_summary"])
            f2f_section = (
                "\n\n---\n\n"
                "## 🏫 Face-to-Face Staff Meeting\n\n"
                + "\n\n".join(f2f_parts)
            )
            f2f_action_summary = " · ".join(f2f_act_parts)

        final_content = digital_tag + "\n" + digital_section + f2f_section
        final_actions = " · ".join(filter(None, [action_summary, f2f_action_summary]))
        merged_title  = f"Staff Meeting — {week_label_str}"

        row = {
            "program":        "STAFF",
            "schedule_id":    None,
            "title":          merged_title,
            "meeting_date":   week_start,
            "content":        final_content,
            "action_summary": final_actions,
        }

        if digital_recs:
            _execute(client.table("tm_minutes").update(row).eq("id", digital_recs[0]["id"]))
            for dup in digital_recs[1:]:
                _execute(client.table("tm_minutes").delete().eq("id", dup["id"]))
            msg = "Staff minutes updated in Team Meetings app."
        else:
            _execute(client.table("tm_minutes").insert(row))
            msg = "Staff minutes created in Team Meetings app."

        for m in f2f_recs:
            _execute(client.table("tm_minutes").delete().eq("id", m["id"]))

        return True, msg

    except Exception as e:
        return False, f"Sync error: {e}"


def seed_term_weeks() -> int:
    """Pre-create draft editions for all SA 2026 school term weeks that don't yet exist."""
    client = get_client()
    existing = {row["week_start"] for row in (_execute(
        client.table("weekly_editions").select("week_start")
    ).data or [])}
    inserted = 0
    for term_num, term_start, total_weeks in SA_TERMS_2026:
        for w in range(total_weeks):
            monday = term_start + timedelta(weeks=w)
            iso = monday.isoformat()
            if iso not in existing:
                try:
                    _execute(client.table("weekly_editions").insert({
                        "week_start": iso,
                        "week_label": week_label(monday),
                        "status": "draft",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }))
                    inserted += 1
                except:
                    pass
    return inserted

# ── Notices ───────────────────────────────────────────────────────────────────
def get_notices_for_edition(edition_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("notices")
                .select("*")
                .eq("edition_id", edition_id)
                .order("created_at", desc=False)
        )
        return result.data or []
    except Exception as e:
        st.error(f"Error loading notices: {e}")
        return []

def get_notice(notice_id) -> dict:
    try:
        client = get_client()
        result = _execute(
            client.table("notices").select("*").eq("id", notice_id).single()
        )
        return result.data
    except:
        return None

def create_notice(edition_id, title, content, category, author, audience,
                  has_actions, actions,
                  has_poll, poll_question, poll_options,
                  has_comments, comment_prompt,
                  uploaded_files=None) -> object:
    try:
        client = get_client()
        result = _execute(client.table("notices").insert({
            "edition_id": edition_id,
            "title": title,
            "content": content,
            "category": category,
            "author": author,
            "audience": audience,
            "has_actions": has_actions,
            "has_poll": has_poll,
            "poll_question": poll_question if has_poll else None,
            "has_comments": has_comments,
            "comment_prompt": comment_prompt if has_comments else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))

        if not result.data:
            return None
        notice_id = result.data[0]["id"]

        if has_actions and actions:
            _execute(client.table("notice_actions").insert([
                {"notice_id": notice_id, "action_text": a, "sort_order": i}
                for i, a in enumerate(actions)
            ]))

        if has_poll and poll_options:
            _execute(client.table("poll_options").insert([
                {"notice_id": notice_id, "option_text": o, "sort_order": i}
                for i, o in enumerate(poll_options)
            ]))

        if uploaded_files:
            for uf in uploaded_files:
                upload_attachment(notice_id, uf)

        return notice_id
    except Exception as e:
        st.error(f"Error creating notice: {e}")
        return None

# ── Attachments ───────────────────────────────────────────────────────────────
def upload_attachment(notice_id, uploaded_file) -> bool:
    """Save file data directly into the notice_attachments table (no storage bucket needed)."""
    import base64
    try:
        client = get_client()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        if not file_bytes:
            st.error(f"❌ File {uploaded_file.name} appears empty.")
            return False
        file_b64 = base64.b64encode(file_bytes).decode("utf-8")
        content_type = uploaded_file.type or "application/octet-stream"
        result = _execute(client.table("notice_attachments").insert({
            "notice_id": notice_id,
            "file_name": uploaded_file.name,
            "file_size": len(file_bytes),
            "file_type": content_type,
            "storage_path": f"inline:{file_b64}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        if not result.data:
            st.error(f"❌ DB insert returned no data for {uploaded_file.name}.")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Attachment failed for {uploaded_file.name}: {type(e).__name__}: {e}")
        return False

def get_attachments(notice_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("notice_attachments")
                .select("id, notice_id, file_name, file_size, file_type, storage_path, created_at")
                .eq("notice_id", notice_id)
                .order("created_at")
        )
        return result.data or []
    except:
        return []

def get_attachment_url(storage_path: str) -> str:
    return ""

def get_attachment_bytes(storage_path: str):
    """Return file bytes — handles both inline (base64 in DB) and legacy storage paths."""
    import base64
    try:
        if storage_path.startswith("inline:"):
            return base64.b64decode(storage_path[7:])
        client = get_client()
        return client.storage.from_(STORAGE_BUCKET).download(storage_path)
    except Exception:
        return None

# ── Actions ───────────────────────────────────────────────────────────────────
def get_actions(notice_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("notice_actions")
                .select("*").eq("notice_id", notice_id)
                .order("sort_order")
        )
        return result.data or []
    except:
        return []

# ── Poll ──────────────────────────────────────────────────────────────────────
def get_poll_options(notice_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("poll_options")
                .select("*").eq("notice_id", notice_id)
                .order("sort_order")
        )
        return result.data or []
    except:
        return []

def get_poll_votes(notice_id) -> dict:
    try:
        client = get_client()
        result = _execute(
            client.table("poll_votes")
                .select("option_id").eq("notice_id", notice_id)
        )
        counts = {}
        for row in (result.data or []):
            oid = row["option_id"]
            counts[oid] = counts.get(oid, 0) + 1
        return counts
    except:
        return {}

def has_voted(notice_id, staff_name) -> bool:
    try:
        client = get_client()
        result = _execute(
            client.table("poll_votes")
                .select("id").eq("notice_id", notice_id)
                .eq("staff_name", staff_name)
        )
        return len(result.data or []) > 0
    except:
        return False

def record_poll_vote(notice_id, option_id, staff_name):
    try:
        client = get_client()
        _execute(client.table("poll_votes").insert({
            "notice_id": notice_id,
            "option_id": option_id,
            "staff_name": staff_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
    except Exception as e:
        st.error(f"Error recording vote: {e}")

# ── Read / Acknowledge ────────────────────────────────────────────────────────
def record_read(notice_id, staff_name):
    try:
        client = get_client()
        _execute(client.table("notice_responses").upsert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "read_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="notice_id,staff_name"))
    except:
        pass

def record_acknowledgement(notice_id, staff_name):
    try:
        client = get_client()
        _execute(client.table("notice_responses").upsert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "acknowledged_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="notice_id,staff_name"))
    except Exception as e:
        st.error(f"Error recording acknowledgement: {e}")

def has_acknowledged(notice_id, staff_name) -> bool:
    try:
        client = get_client()
        result = _execute(
            client.table("notice_responses")
                .select("acknowledged_at").eq("notice_id", notice_id)
                .eq("staff_name", staff_name)
        )
        return any(r.get("acknowledged_at") for r in (result.data or []))
    except:
        return False

def get_responses(notice_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("notice_responses")
                .select("*").eq("notice_id", notice_id)
                .order("staff_name")
        )
        return result.data or []
    except:
        return []

# ── Comments ──────────────────────────────────────────────────────────────────
def record_comment(notice_id, staff_name, comment_text):
    try:
        client = get_client()
        _execute(client.table("notice_comments").insert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "comment_text": comment_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
    except Exception as e:
        st.error(f"Error saving comment: {e}")

def get_comments(notice_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("notice_comments")
                .select("*").eq("notice_id", notice_id)
                .order("created_at")
        )
        return result.data or []
    except:
        return []

# ── Staff List & Authentication ───────────────────────────────────────────────
def hash_pin(pin: str) -> str:
    """SHA-256 hash of the PIN string."""
    return hashlib.sha256(pin.strip().encode()).hexdigest()

def get_staff_list() -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("staff_list")
                .select("id, name, email, role, active, created_at")
                .eq("active", True)
                .order("name")
        )
        return result.data or []
    except:
        return []

def get_staff_names() -> list:
    """Return just names for the login dropdown."""
    staff = get_staff_list()
    return [s["name"] for s in staff]

def verify_pin(name: str, pin: str) -> object:
    """Returns the staff record if name + PIN are correct, else None."""
    try:
        client = get_client()
        result = _execute(
            client.table("staff_list")
                .select("*")
                .eq("name", name)
                .eq("active", True)
        )
        rows = result.data or []
        if not rows:
            return None
        staff = rows[0]
        stored_hash = staff.get("pin_hash")
        if not stored_hash:
            return None
        if stored_hash == hash_pin(pin):
            return staff
        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None

def add_staff_member(name: str, email: str, pin: str, role: str = "staff") -> bool:
    try:
        client = get_client()
        _execute(client.table("staff_list").insert({
            "name": name,
            "email": email,
            "role": role,
            "pin_hash": hash_pin(pin) if pin.strip() else None,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        return True
    except Exception as e:
        st.error(f"Error adding staff: {e}")
        return False

def set_staff_pin(staff_id: int, new_pin: str) -> bool:
    try:
        client = get_client()
        _execute(
            client.table("staff_list")
                .update({"pin_hash": hash_pin(new_pin)})
                .eq("id", staff_id)
        )
        return True
    except Exception as e:
        st.error(f"Error setting PIN: {e}")
        return False

def remove_staff_member(staff_id: int) -> bool:
    try:
        client = get_client()
        _execute(
            client.table("staff_list")
                .update({"active": False})
                .eq("id", staff_id)
        )
        return True
    except:
        return False

def is_admin(name: str) -> bool:
    try:
        client = get_client()
        result = _execute(
            client.table("staff_list")
                .select("role").eq("name", name).eq("active", True)
        )
        rows = result.data or []
        return rows[0].get("role") == "admin" if rows else False
    except:
        return False

# ── Edition acknowledgement summary ──────────────────────────────────────────
def get_edition_ack_summary(edition_id) -> dict:
    """Returns {notice_id: {ackd_count, total_responses}} for all notices in edition."""
    notices = get_notices_for_edition(edition_id)
    summary = {}
    for n in notices:
        responses = get_responses(n["id"])
        ackd = [r for r in responses if r.get("acknowledged_at")]
        summary[n["id"]] = {"ackd": len(ackd), "total": len(responses)}
    return summary

# ── Agenda Items ──────────────────────────────────────────────────────────────
def get_agenda_items(edition_id) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_items")
                .select("*")
                .eq("edition_id", edition_id)
                .order("created_at")
        )
        return result.data or []
    except Exception:
        return []

def delete_agenda_item(item_id) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_items").delete().eq("id", item_id))
        return True
    except Exception as e:
        st.error(f"Error deleting agenda item: {e}")
        return False

def save_agenda_item(edition_id, section: str, author: str, content: str) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_items").insert({
            "edition_id": edition_id,
            "section": section,
            "author": author,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        return True
    except Exception as e:
        st.error(f"Error saving agenda item: {e}")
        return False

# ── Agenda Acknowledgements ───────────────────────────────────────────────────
def get_agenda_acks(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_acks")
                .select("*").eq("edition_id", edition_id).eq("section", section)
        )
        return result.data or []
    except:
        return []

def has_agenda_acked(edition_id, section: str, staff_name: str) -> bool:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_acks")
                .select("id").eq("edition_id", edition_id)
                .eq("section", section).eq("staff_name", staff_name)
        )
        return len(result.data or []) > 0
    except:
        return False

def record_agenda_ack(edition_id, section: str, staff_name: str) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_acks").upsert({
            "edition_id": edition_id,
            "section": section,
            "staff_name": staff_name,
            "acked_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="edition_id,section,staff_name"))
        return True
    except Exception as e:
        st.error(f"Error recording acknowledgement: {e}")
        return False

# ── Agenda Comments ───────────────────────────────────────────────────────────
def get_agenda_comments(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_comments")
                .select("*").eq("edition_id", edition_id).eq("section", section)
                .order("created_at")
        )
        return result.data or []
    except:
        return []

def save_agenda_comment(edition_id, section: str, author: str, content: str) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_comments").insert({
            "edition_id": edition_id,
            "section": section,
            "author": author,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        return True
    except Exception as e:
        st.error(f"Error saving comment: {e}")
        return False

# ── Agenda Polls ──────────────────────────────────────────────────────────────
def get_agenda_poll_options(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_poll_options")
                .select("*").eq("edition_id", edition_id).eq("section", section)
                .order("sort_order")
        )
        return result.data or []
    except:
        return []

def get_agenda_poll_votes(edition_id, section: str) -> dict:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_poll_votes")
                .select("option_id").eq("edition_id", edition_id).eq("section", section)
        )
        counts = {}
        for r in (result.data or []):
            oid = r["option_id"]
            counts[oid] = counts.get(oid, 0) + 1
        return counts
    except:
        return {}

def has_agenda_voted(edition_id, section: str, staff_name: str) -> bool:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_poll_votes")
                .select("id").eq("edition_id", edition_id)
                .eq("section", section).eq("staff_name", staff_name)
        )
        return len(result.data or []) > 0
    except:
        return False

def save_agenda_poll_option(edition_id, section: str, question: str, options: list) -> bool:
    try:
        client = get_client()
        rows = [{"edition_id": edition_id, "section": section, "question": question,
                 "option_text": o, "sort_order": i} for i, o in enumerate(options)]
        _execute(client.table("agenda_poll_options").insert(rows))
        return True
    except Exception as e:
        st.error(f"Error creating poll: {e}")
        return False

def record_agenda_vote(edition_id, section: str, option_id, staff_name: str) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_poll_votes").insert({
            "edition_id": edition_id,
            "section": section,
            "option_id": option_id,
            "staff_name": staff_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        return True
    except Exception as e:
        st.error(f"Error recording vote: {e}")
        return False

# ── Global Timetable ──────────────────────────────────────────────────────────
def get_global_timetable() -> dict:
    try:
        client = get_client()
        result = _execute(
            client.table("global_settings")
                .select("*").eq("key", "current_timetable")
                .limit(1)
        )
        return result.data[0] if result.data else None
    except:
        return None

def save_global_timetable(filename: str, file_b64: str, uploaded_by: str) -> bool:
    try:
        client = get_client()
        _execute(client.table("global_settings").upsert({
            "key": "current_timetable",
            "value": file_b64,
            "meta": filename,
            "updated_by": uploaded_by,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="key"))
        return True
    except Exception as e:
        st.error(f"Failed to save timetable: {e}")
        return False

def get_global_timetable_bytes() -> bytes:
    import base64
    record = get_global_timetable()
    if record and record.get("value"):
        try:
            return base64.b64decode(record["value"])
        except:
            return None
    return None

# ── Agenda Attachments ────────────────────────────────────────────────────────
def save_agenda_attachment(edition_id, section: str, filename: str, file_bytes: bytes,
                           mime_type: str, uploaded_by: str) -> bool:
    import base64 as b64lib
    try:
        client = get_client()
        _execute(client.table("agenda_attachments").insert({
            "edition_id": edition_id,
            "section": section,
            "filename": filename,
            "file_data": b64lib.b64encode(file_bytes).decode("utf-8"),
            "file_size": len(file_bytes),
            "mime_type": mime_type,
            "uploaded_by": uploaded_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        return True
    except Exception as e:
        st.error(f"Error saving attachment: {e}")
        return False

def get_agenda_attachments(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_attachments")
                .select("id,edition_id,section,filename,file_size,mime_type,uploaded_by,created_at")
                .eq("edition_id", edition_id).eq("section", section)
                .order("created_at")
        )
        return result.data or []
    except:
        return []

def get_agenda_attachment_bytes(attachment_id) -> tuple:
    import base64 as b64lib
    try:
        client = get_client()
        result = _execute(
            client.table("agenda_attachments")
                .select("filename,mime_type,file_data").eq("id", attachment_id).single()
        )
        row = result.data
        if row:
            return row["filename"], row["mime_type"], b64lib.b64decode(row["file_data"])
        return None, None, None
    except:
        return None, None, None

def delete_agenda_attachment(attachment_id) -> bool:
    try:
        client = get_client()
        _execute(client.table("agenda_attachments").delete().eq("id", attachment_id))
        return True
    except:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# DAILY BULLETIN
# ══════════════════════════════════════════════════════════════════════════════

# Alias so bulletin functions can use get_supabase() without a second connection
get_supabase = get_client

def get_bulletin(bulletin_date: date):
    try:
        sb = get_supabase()
        result = _execute(
            sb.table("bulletins").select("*").eq("date", str(bulletin_date))
        )
        return result.data[0] if result.data else None
    except Exception as e:
        st.warning(f"⚠️ Could not load bulletin (network issue, retrying may help): {e}")
        return None

def save_bulletin(bulletin_date: date, data: dict):
    try:
        sb = get_supabase()
        existing = get_bulletin(bulletin_date)
        data["date"] = str(bulletin_date)
        data["updated_at"] = datetime.utcnow().isoformat()
        if existing:
            _execute(sb.table("bulletins").update(data).eq("date", str(bulletin_date)))
        else:
            data["created_at"] = datetime.utcnow().isoformat()
            _execute(sb.table("bulletins").insert(data))
    except Exception as e:
        st.error(f"❌ Could not save bulletin: {e}")

def get_bulletins_range(start: date, end: date):
    try:
        sb = get_supabase()
        result = _execute(
            sb.table("bulletins")
                .select("date, fun_fact")
                .gte("date", str(start))
                .lte("date", str(end))
                .order("date", desc=True)
        )
        return result.data
    except Exception as e:
        st.warning(f"⚠️ Could not load bulletin range: {e}")
        return []

def search_bulletins(keyword: str):
    try:
        sb = get_supabase()
        result = _execute(
            sb.table("bulletins")
                .select("date, fun_fact, nit_booking")
                .order("date", desc=True)
        )
        kw = keyword.lower()
        matches = []
        for row in result.data:
            if kw in json.dumps(row).lower():
                matches.append(row)
        return matches
    except Exception as e:
        st.warning(f"⚠️ Search unavailable: {e}")
        return []

def get_all_bulletin_dates():
    try:
        sb = get_supabase()
        result = _execute(
            sb.table("bulletins").select("date").order("date", desc=True)
        )
        return [row["date"] for row in result.data]
    except Exception as e:
        st.warning(f"⚠️ Could not load bulletin dates: {e}")
        return []
