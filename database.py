"""
database.py — Supabase backend for LBU Staff Notice Board v2
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, date, timedelta
import uuid
import hashlib

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
    # Wed=2, Thu=3, Fri=4, Sat=5, Sun=6 → use next Monday
    if today.weekday() >= 2:
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
    else:
        monday = today - timedelta(days=today.weekday())
    correct_label = week_label(monday)
    try:
        result = client.table("weekly_editions") \
            .select("*") \
            .eq("week_start", monday.isoformat()) \
            .single() \
            .execute()
        row = result.data
        if row and row.get("week_label") != correct_label:
            client.table("weekly_editions").update({"week_label": correct_label}).eq("id", row["id"]).execute()
            row["week_label"] = correct_label
        return row
    except:
        pass
    # Create it
    try:
        result = client.table("weekly_editions").insert({
            "week_start": monday.isoformat(),
            "week_label": week_label(monday),
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Error creating edition: {e}")
        return None

def get_edition(edition_id) -> dict:
    try:
        client = get_client()
        result = client.table("weekly_editions") \
            .select("*").eq("id", edition_id).single().execute()
        return result.data
    except:
        return None

def get_current_published_edition() -> dict:
    """Get the published edition for the current week only, with fresh label."""
    try:
        client = get_client()
        current_monday = get_current_monday()
        result = client.table("weekly_editions") \
            .select("*") \
            .eq("status", "published") \
            .eq("week_start", current_monday.isoformat()) \
            .limit(1) \
            .execute()
        row = result.data[0] if result.data else None
        if row:
            fresh = week_label(current_monday)
            if row.get("week_label") != fresh:
                client.table("weekly_editions").update({"week_label": fresh}).eq("id", row["id"]).execute()
                row["week_label"] = fresh
        return row
    except:
        return None

def get_all_editions() -> list:
    """All editions ordered newest first."""
    try:
        client = get_client()
        result = client.table("weekly_editions") \
            .select("*") \
            .order("week_start", desc=True) \
            .execute()
        return result.data or []
    except Exception as e:
        st.error(f"Error loading editions: {e}")
        return []

def publish_edition(edition_id, published_by: str) -> bool:
    try:
        client = get_client()
        client.table("weekly_editions").update({
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "published_by": published_by
        }).eq("id", edition_id).execute()
        return True
    except Exception as e:
        st.error(f"Error publishing edition: {e}")
        return False

def unpublish_edition(edition_id) -> bool:
    """Revert a published edition back to draft so admin can amend it."""
    try:
        client = get_client()
        client.table("weekly_editions").update({
            "status": "draft",
            "published_at": None,
            "published_by": None
        }).eq("id", edition_id).execute()
        return True
    except Exception as e:
        st.error(f"Error reopening edition: {e}")
        return False

def sync_to_staff_minutes(edition_id) -> tuple:
    """Build formatted minutes from a published digital staff meeting and merge
    with any face-to-face minutes for the same week into one record in tm_minutes.
    Digital content appears first, followed by face-to-face minutes.
    Returns (success: bool, message: str)."""
    import re as _re
    try:
        client = get_client()

        # ── Fetch edition ─────────────────────────────────────────────────────
        ed = client.table("weekly_editions").select("*").eq("id", edition_id).single().execute().data
        if not ed:
            return False, "Edition not found."

        week_start     = ed.get("week_start", "")          # e.g. "2026-03-09"
        week_label_str = ed.get("week_label", "")
        published_by   = ed.get("published_by", "Admin")

        # Use date.fromisoformat (safe on Python 3.7+, unlike datetime.fromisoformat for dates)
        from datetime import date as _date
        monday   = _date.fromisoformat(week_start)
        week_end = (monday + timedelta(days=6)).isoformat()  # e.g. "2026-03-15"

        # ── Fetch digital meeting data ────────────────────────────────────────
        agenda_rows = client.table("agenda_items").select("*") \
            .eq("edition_id", edition_id).order("created_at").execute().data or []

        notices = client.table("notices").select("*") \
            .eq("edition_id", edition_id).order("created_at").execute().data or []

        notice_ids = [n["id"] for n in notices]
        all_notice_actions = []
        if notice_ids:
            all_notice_actions = client.table("notice_actions").select("*") \
                .in_("notice_id", notice_ids).execute().data or []
        actions_by_notice = {}
        for a in all_notice_actions:
            actions_by_notice.setdefault(a["notice_id"], []).append(a["action_text"])

        # ── Fetch attendance for STAFF program this week ──────────────────────
        attendance_rows = client.table("tm_attendance").select("*") \
            .eq("program", "STAFF") \
            .gte("meeting_date", week_start) \
            .lte("meeting_date", week_end) \
            .execute().data or []

        present   = sorted([r["staff_name"] for r in attendance_rows if r.get("status") == "present"])
        apologies = sorted([r["staff_name"] for r in attendance_rows if r.get("status") in ("absent", "apology")])

        # ── Section labels ────────────────────────────────────────────────────
        SECTION_LABELS = {
            "pac":        "PAC",
            "whs":        "WHS",
            "profdev":    "Professional Development",
            "curriculum": "Curriculum",
            "welfare":    "Student Welfare",
            "timetable":  "Timetable",
        }

        # ── Group agenda items by section ─────────────────────────────────────
        by_sec = {}
        for it in agenda_rows:
            if it.get("content", "").startswith("TIMETABLE_PATH::"):
                continue
            by_sec.setdefault(it.get("section", ""), []).append(it)

        # ── Deduplicate notices by title (catches double-submit) ──────────────
        seen_titles = set()
        unique_notices = []
        for n in notices:
            t = n.get("title", "").strip()
            if t not in seen_titles:
                seen_titles.add(t)
                unique_notices.append(n)

        # ── Build the digital section ─────────────────────────────────────────
        pub_date = monday.strftime("%-d %B %Y")
        lines = [
            "## 💻 Digital Staff Meeting",
            "",
            f"**Date:** {pub_date}  ",
            f"**Published by:** {published_by}  ",
            f"**Platform:** CLC Digital Staff Meeting",
            "",
        ]

        # Attendance (if recorded)
        if present or apologies:
            lines.append("**Attendance**")
            if present:
                lines.append(f"- Present: {', '.join(present)}")
            if apologies:
                lines.append(f"- Apologies: {', '.join(apologies)}")
            lines.append("")

        # Standing agenda items
        if by_sec:
            lines.append("**Standing Agenda Items**")
            lines.append("")
            for sec, items in by_sec.items():
                sec_label = SECTION_LABELS.get(sec, sec.upper())
                lines.append(f"**{sec_label}:**")
                for it in items:
                    lines.append(f"- {it.get('content', '')}")
                lines.append("")

        # Notices & updates
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

        # Action summary for digital section
        action_summary = " · ".join(
            f"{a} (re: {n['title']})"
            for n in unique_notices
            for a in actions_by_notice.get(n["id"], [])
        )

        # ── Find existing STAFF minutes for this week ─────────────────────────
        all_staff_mins = client.table("tm_minutes").select("*") \
            .eq("program", "STAFF") \
            .gte("meeting_date", week_start) \
            .lte("meeting_date", week_end) \
            .execute().data or []

        digital_tag    = "<!-- digital-staff-meeting -->"
        digital_recs   = [m for m in all_staff_mins if digital_tag in m.get("content", "")]
        f2f_recs       = [m for m in all_staff_mins if digital_tag not in m.get("content", "")]

        # ── Build face-to-face section ────────────────────────────────────────
        f2f_section        = ""
        f2f_action_summary = ""
        if f2f_recs:
            f2f_parts = []
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

        # ── Assemble final merged content ─────────────────────────────────────
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

        # ── Upsert merged record, delete redundant standalone records ─────────
        if digital_recs:
            client.table("tm_minutes").update(row).eq("id", digital_recs[0]["id"]).execute()
            for dup in digital_recs[1:]:
                client.table("tm_minutes").delete().eq("id", dup["id"]).execute()
            msg = "Staff minutes updated in Team Meetings app."
        else:
            client.table("tm_minutes").insert(row).execute()
            msg = "Staff minutes created in Team Meetings app."

        # Remove standalone face-to-face records (content preserved in merged)
        for m in f2f_recs:
            client.table("tm_minutes").delete().eq("id", m["id"]).execute()

        return True, msg

    except Exception as e:
        return False, f"Sync error: {e}"


def seed_term_weeks() -> int:
    """Pre-create draft editions for all SA 2026 school term weeks that don't yet exist.
    Returns count of new rows inserted."""
    client = get_client()
    existing = {row["week_start"] for row in (client.table("weekly_editions").select("week_start").execute().data or [])}
    inserted = 0
    for term_num, term_start, total_weeks in SA_TERMS_2026:
        for w in range(total_weeks):
            monday = term_start + timedelta(weeks=w)
            iso = monday.isoformat()
            if iso not in existing:
                try:
                    client.table("weekly_editions").insert({
                        "week_start": iso,
                        "week_label": week_label(monday),
                        "status": "draft",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    inserted += 1
                except:
                    pass  # already exists (race condition)
    return inserted

# ── Notices ───────────────────────────────────────────────────────────────────
def get_notices_for_edition(edition_id) -> list:
    try:
        client = get_client()
        result = client.table("notices") \
            .select("*") \
            .eq("edition_id", edition_id) \
            .order("created_at", desc=False) \
            .execute()
        return result.data or []
    except Exception as e:
        st.error(f"Error loading notices: {e}")
        return []

def get_notice(notice_id) -> dict:
    try:
        client = get_client()
        result = client.table("notices") \
            .select("*").eq("id", notice_id).single().execute()
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
        result = client.table("notices").insert({
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
        }).execute()

        if not result.data:
            return None
        notice_id = result.data[0]["id"]

        if has_actions and actions:
            client.table("notice_actions").insert([
                {"notice_id": notice_id, "action_text": a, "sort_order": i}
                for i, a in enumerate(actions)
            ]).execute()

        if has_poll and poll_options:
            client.table("poll_options").insert([
                {"notice_id": notice_id, "option_text": o, "sort_order": i}
                for i, o in enumerate(poll_options)
            ]).execute()

        # Handle file uploads
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
        result = client.table("notice_attachments").insert({
            "notice_id": notice_id,
            "file_name": uploaded_file.name,
            "file_size": len(file_bytes),
            "file_type": content_type,
            "storage_path": f"inline:{file_b64}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        if not result.data:
            st.error(f"❌ DB insert returned no data for {uploaded_file.name}. Result: {result}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Attachment failed for {uploaded_file.name}: {type(e).__name__}: {e}")
        return False

def get_attachments(notice_id) -> list:
    try:
        client = get_client()
        result = client.table("notice_attachments") \
            .select("id, notice_id, file_name, file_size, file_type, storage_path, created_at") \
            .eq("notice_id", notice_id) \
            .order("created_at").execute()
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
        # Legacy: try storage bucket
        client = get_client()
        return client.storage.from_(STORAGE_BUCKET).download(storage_path)
    except Exception as e:
        return None

# ── Actions ───────────────────────────────────────────────────────────────────
def get_actions(notice_id) -> list:
    try:
        client = get_client()
        result = client.table("notice_actions") \
            .select("*").eq("notice_id", notice_id) \
            .order("sort_order").execute()
        return result.data or []
    except:
        return []

# ── Poll ──────────────────────────────────────────────────────────────────────
def get_poll_options(notice_id) -> list:
    try:
        client = get_client()
        result = client.table("poll_options") \
            .select("*").eq("notice_id", notice_id) \
            .order("sort_order").execute()
        return result.data or []
    except:
        return []

def get_poll_votes(notice_id) -> dict:
    try:
        client = get_client()
        result = client.table("poll_votes") \
            .select("option_id").eq("notice_id", notice_id).execute()
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
        result = client.table("poll_votes") \
            .select("id").eq("notice_id", notice_id) \
            .eq("staff_name", staff_name).execute()
        return len(result.data or []) > 0
    except:
        return False

def record_poll_vote(notice_id, option_id, staff_name):
    try:
        client = get_client()
        client.table("poll_votes").insert({
            "notice_id": notice_id,
            "option_id": option_id,
            "staff_name": staff_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Error recording vote: {e}")

# ── Read / Acknowledge ────────────────────────────────────────────────────────
def record_read(notice_id, staff_name):
    try:
        client = get_client()
        client.table("notice_responses").upsert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "read_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="notice_id,staff_name").execute()
    except:
        pass

def record_acknowledgement(notice_id, staff_name):
    try:
        client = get_client()
        client.table("notice_responses").upsert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "acknowledged_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="notice_id,staff_name").execute()
    except Exception as e:
        st.error(f"Error recording acknowledgement: {e}")

def has_acknowledged(notice_id, staff_name) -> bool:
    try:
        client = get_client()
        result = client.table("notice_responses") \
            .select("acknowledged_at").eq("notice_id", notice_id) \
            .eq("staff_name", staff_name).execute()
        return any(r.get("acknowledged_at") for r in (result.data or []))
    except:
        return False

def get_responses(notice_id) -> list:
    try:
        client = get_client()
        result = client.table("notice_responses") \
            .select("*").eq("notice_id", notice_id) \
            .order("staff_name").execute()
        return result.data or []
    except:
        return []

# ── Comments ──────────────────────────────────────────────────────────────────
def record_comment(notice_id, staff_name, comment_text):
    try:
        client = get_client()
        client.table("notice_comments").insert({
            "notice_id": notice_id,
            "staff_name": staff_name,
            "comment_text": comment_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Error saving comment: {e}")

def get_comments(notice_id) -> list:
    try:
        client = get_client()
        result = client.table("notice_comments") \
            .select("*").eq("notice_id", notice_id) \
            .order("created_at").execute()
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
        result = client.table("staff_list") \
            .select("id, name, email, role, active, created_at") \
            .eq("active", True) \
            .order("name").execute()
        return result.data or []
    except:
        return []

def get_staff_names() -> list:
    """Return just names for the login dropdown."""
    staff = get_staff_list()
    return [s["name"] for s in staff]

def verify_pin(name: str, pin: str) -> object:
    """
    Returns the staff record if name + PIN are correct, else None.
    Also returns record if no PIN has been set yet (first login).
    """
    try:
        client = get_client()
        result = client.table("staff_list") \
            .select("*") \
            .eq("name", name) \
            .eq("active", True) \
            .execute()
        rows = result.data or []
        if not rows:
            return None
        staff = rows[0]
        stored_hash = staff.get("pin_hash")
        # No PIN set yet — block login, admin must set one first
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
        client.table("staff_list").insert({
            "name": name,
            "email": email,
            "role": role,
            "pin_hash": hash_pin(pin) if pin.strip() else None,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error adding staff: {e}")
        return False

def set_staff_pin(staff_id: int, new_pin: str) -> bool:
    try:
        client = get_client()
        client.table("staff_list").update({
            "pin_hash": hash_pin(new_pin)
        }).eq("id", staff_id).execute()
        return True
    except Exception as e:
        st.error(f"Error setting PIN: {e}")
        return False

def remove_staff_member(staff_id: int) -> bool:
    try:
        client = get_client()
        client.table("staff_list").update({"active": False}) \
            .eq("id", staff_id).execute()
        return True
    except:
        return False

def is_admin(name: str) -> bool:
    try:
        client = get_client()
        result = client.table("staff_list") \
            .select("role").eq("name", name).eq("active", True).execute()
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
        result = client.table("agenda_items")             .select("*")             .eq("edition_id", edition_id)             .order("created_at")             .execute()
        return result.data or []
    except Exception as e:
        return []

def delete_agenda_item(item_id) -> bool:
    try:
        client = get_client()
        client.table("agenda_items").delete().eq("id", item_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting agenda item: {e}")
        return False

def save_agenda_item(edition_id, section: str, author: str, content: str) -> bool:
    try:
        client = get_client()
        client.table("agenda_items").insert({
            "edition_id": edition_id,
            "section": section,
            "author": author,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving agenda item: {e}")
        return False

# ── Agenda Acknowledgements ───────────────────────────────────────────────────
def get_agenda_acks(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = client.table("agenda_acks") \
            .select("*").eq("edition_id", edition_id).eq("section", section).execute()
        return result.data or []
    except:
        return []

def has_agenda_acked(edition_id, section: str, staff_name: str) -> bool:
    try:
        client = get_client()
        result = client.table("agenda_acks") \
            .select("id").eq("edition_id", edition_id) \
            .eq("section", section).eq("staff_name", staff_name).execute()
        return len(result.data or []) > 0
    except:
        return False

def record_agenda_ack(edition_id, section: str, staff_name: str) -> bool:
    try:
        client = get_client()
        client.table("agenda_acks").upsert({
            "edition_id": edition_id,
            "section": section,
            "staff_name": staff_name,
            "acked_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="edition_id,section,staff_name").execute()
        return True
    except Exception as e:
        st.error(f"Error recording acknowledgement: {e}")
        return False

# ── Agenda Comments ───────────────────────────────────────────────────────────
def get_agenda_comments(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = client.table("agenda_comments") \
            .select("*").eq("edition_id", edition_id).eq("section", section) \
            .order("created_at").execute()
        return result.data or []
    except:
        return []

def save_agenda_comment(edition_id, section: str, author: str, content: str) -> bool:
    try:
        client = get_client()
        client.table("agenda_comments").insert({
            "edition_id": edition_id,
            "section": section,
            "author": author,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving comment: {e}")
        return False

# ── Agenda Polls ──────────────────────────────────────────────────────────────
def get_agenda_poll_options(edition_id, section: str) -> list:
    try:
        client = get_client()
        result = client.table("agenda_poll_options") \
            .select("*").eq("edition_id", edition_id).eq("section", section) \
            .order("sort_order").execute()
        return result.data or []
    except:
        return []

def get_agenda_poll_votes(edition_id, section: str) -> dict:
    try:
        client = get_client()
        result = client.table("agenda_poll_votes") \
            .select("option_id").eq("edition_id", edition_id).eq("section", section).execute()
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
        result = client.table("agenda_poll_votes") \
            .select("id").eq("edition_id", edition_id) \
            .eq("section", section).eq("staff_name", staff_name).execute()
        return len(result.data or []) > 0
    except:
        return False

def save_agenda_poll_option(edition_id, section: str, question: str, options: list) -> bool:
    try:
        client = get_client()
        rows = [{"edition_id": edition_id, "section": section, "question": question,
                 "option_text": o, "sort_order": i} for i, o in enumerate(options)]
        client.table("agenda_poll_options").insert(rows).execute()
        return True
    except Exception as e:
        st.error(f"Error creating poll: {e}")
        return False

def record_agenda_vote(edition_id, section: str, option_id, staff_name: str) -> bool:
    try:
        client = get_client()
        client.table("agenda_poll_votes").insert({
            "edition_id": edition_id,
            "section": section,
            "option_id": option_id,
            "staff_name": staff_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error recording vote: {e}")
        return False

# ── Global Timetable (persistent, not tied to any edition) ────────────────────
def get_global_timetable() -> dict:
    """Get the current global timetable record."""
    try:
        client = get_client()
        result = client.table("global_settings") \
            .select("*").eq("key", "current_timetable") \
            .limit(1).execute()
        return result.data[0] if result.data else None
    except:
        return None

def save_global_timetable(filename: str, file_b64: str, uploaded_by: str) -> bool:
    """Save the current timetable as a global setting (upsert)."""
    import base64
    try:
        client = get_client()
        client.table("global_settings").upsert({
            "key": "current_timetable",
            "value": file_b64,
            "meta": filename,
            "updated_by": uploaded_by,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="key").execute()
        return True
    except Exception as e:
        st.error(f"Failed to save timetable: {e}")
        return False

def get_global_timetable_bytes() -> bytes:
    """Get the current timetable as raw bytes."""
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
    """Save a file attachment for a standing agenda section (base64 in DB)."""
    import base64 as b64lib
    try:
        client = get_client()
        client.table("agenda_attachments").insert({
            "edition_id": edition_id,
            "section": section,
            "filename": filename,
            "file_data": b64lib.b64encode(file_bytes).decode("utf-8"),
            "file_size": len(file_bytes),
            "mime_type": mime_type,
            "uploaded_by": uploaded_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving attachment: {e}")
        return False

def get_agenda_attachments(edition_id, section: str) -> list:
    """Get all attachments for a section (returns metadata only, not file_data)."""
    try:
        client = get_client()
        result = client.table("agenda_attachments") \
            .select("id,edition_id,section,filename,file_size,mime_type,uploaded_by,created_at") \
            .eq("edition_id", edition_id).eq("section", section) \
            .order("created_at").execute()
        return result.data or []
    except:
        return []

def get_agenda_attachment_bytes(attachment_id) -> tuple:
    """Returns (filename, mime_type, bytes) for download."""
    import base64 as b64lib
    try:
        client = get_client()
        result = client.table("agenda_attachments") \
            .select("filename,mime_type,file_data").eq("id", attachment_id).single().execute()
        row = result.data
        if row:
            return row["filename"], row["mime_type"], b64lib.b64decode(row["file_data"])
        return None, None, None
    except:
        return None, None, None

def delete_agenda_attachment(attachment_id) -> bool:
    try:
        client = get_client()
        client.table("agenda_attachments").delete().eq("id", attachment_id).execute()
        return True
    except:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# DAILY BULLETIN
# ══════════════════════════════════════════════════════════════════════════════

# Alias so bulletin functions can use get_supabase() without a second connection
get_supabase = get_client

def get_bulletin(bulletin_date: date):
    sb = get_supabase()
    result = sb.table("bulletins").select("*").eq("date", str(bulletin_date)).execute()
    return result.data[0] if result.data else None

def save_bulletin(bulletin_date: date, data: dict):
    sb = get_supabase()
    existing = get_bulletin(bulletin_date)
    data["date"] = str(bulletin_date)
    data["updated_at"] = datetime.utcnow().isoformat()
    if existing:
        sb.table("bulletins").update(data).eq("date", str(bulletin_date)).execute()
    else:
        data["created_at"] = datetime.utcnow().isoformat()
        sb.table("bulletins").insert(data).execute()

def get_bulletins_range(start: date, end: date):
    sb = get_supabase()
    result = sb.table("bulletins").select("date, fun_fact").gte("date", str(start)).lte("date", str(end)).order("date", desc=True).execute()
    return result.data

def search_bulletins(keyword: str):
    sb = get_supabase()
    # Search across text fields using ilike on fun_fact and nit_booking; broader search via full list
    result = sb.table("bulletins").select("date, fun_fact, nit_booking").order("date", desc=True).execute()
    kw = keyword.lower()
    matches = []
    for row in result.data:
        row_str = json.dumps(row).lower()
        if kw in row_str:
            matches.append(row)
    return matches

def get_all_bulletin_dates():
    sb = get_supabase()
    result = sb.table("bulletins").select("date").order("date", desc=True).execute()
    return [row["date"] for row in result.data]
