import streamlit as st
from supabase import create_client, Client
import os
from datetime import date, datetime
import json

@st.cache_resource
def get_supabase() -> Client:
    """
    Get Supabase client - reads from environment variables or st.secrets
    """
    # Try environment variables first (Render style)
    if "SUPABASE_URL" in os.environ and "SUPABASE_KEY" in os.environ:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
    # Fall back to st.secrets
    elif "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    # Try nested format
    elif "supabase" in st.secrets:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    else:
        raise ValueError("No Supabase credentials found in environment or secrets")
    
    return create_client(url, key)

# ══════════════════════════════════════════════════════════════════════════════
# BULLETIN FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_bulletin(bulletin_date: date):
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("*").eq("date", str(bulletin_date)).execute()
    return result.data[0] if result.data else None

def save_bulletin(bulletin_date: date, data: dict):
    """
    Save (create or update) the bulletin for a given date.

    Previously this fired .update()/.insert() and never looked at the
    result. That hides two failure modes that both look identical to a
    user — "I edited something, saved it, and it's gone":

      1. .update() only touches rows that match .eq("date", ...). If that
         match fails for any reason (a stale/misjudged `existing` check, a
         date-format quirk against the stored column), Supabase returns a
         normal 200 response with an EMPTY data list — not an error — so
         the call "succeeds" while writing nothing, and the next load just
         hands back the unchanged old row.
      2. If the insert/update branch is ever picked wrongly, a duplicate
         insert against a unique "date" constraint fails outright.

    This version checks that the write actually returned a saved row, and
    falls back from update→insert if an update unexpectedly matches zero
    rows (rather than silently accepting that as success). Any failure
    that still can't be resolved raises a clear, specific error, so the
    caller's existing try/except surfaces a real message to staff instead
    of the page quietly discarding their edit.
    """
    sb = get_supabase()
    data = dict(data)
    data["date"] = str(bulletin_date)
    data["updated_at"] = datetime.utcnow().isoformat()

    existing = get_bulletin(bulletin_date)

    if existing:
        result = sb.table("daily_bulletins").update(data).eq("date", str(bulletin_date)).execute()
        if not result.data:
            # Update matched zero rows despite existing being truthy — fall
            # back to insert rather than silently doing nothing. If a row
            # genuinely already exists this will raise a clear
            # unique-constraint error instead of losing the edit quietly.
            data["created_at"] = existing.get("created_at") or datetime.utcnow().isoformat()
            result = sb.table("daily_bulletins").insert(data).execute()
    else:
        data["created_at"] = datetime.utcnow().isoformat()
        result = sb.table("daily_bulletins").insert(data).execute()

    if not result.data:
        raise RuntimeError(
            "Save did not return a saved row for "
            f"{bulletin_date}. This usually means the Supabase key in use "
            "doesn't have write permission on daily_bulletins (check Row "
            "Level Security policies there), or the write didn't match "
            "the row you expected."
        )
    return result.data[0]

def get_bulletins_range(start: date, end: date):
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("date, fun_fact").gte("date", str(start)).lte("date", str(end)).order("date", desc=True).execute()
    return result.data

def search_bulletins(keyword: str):
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("*").order("date", desc=True).execute()
    kw = keyword.lower()
    matches = []
    for row in result.data:
        row_str = json.dumps(row).lower()
        if kw in row_str:
            matches.append(row)
    return matches

def get_all_bulletin_dates():
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("date").order("date", desc=True).execute()
    return [row["date"] for row in result.data]

# ══════════════════════════════════════════════════════════════════════════════
# BULLETIN NOTICES FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_notices_for_date(notice_date: date):
    sb = get_supabase()
    result = sb.table("daily_notices").select("*").eq("notice_date", str(notice_date)).order("created_at").execute()
    return result.data

def save_notice(notice_data: dict):
    sb = get_supabase()
    notice_data["created_at"] = datetime.utcnow().isoformat()
    sb.table("daily_notices").insert(notice_data).execute()

def delete_notice(notice_id: int):
    sb = get_supabase()
    sb.table("daily_notices").delete().eq("id", notice_id).execute()
