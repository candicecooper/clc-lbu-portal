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
    sb = get_supabase()
    existing = get_bulletin(bulletin_date)
    data["date"] = str(bulletin_date)
    data["updated_at"] = datetime.utcnow().isoformat()
    
    if existing:
        sb.table("daily_bulletins").update(data).eq("date", str(bulletin_date)).execute()
    else:
        data["created_at"] = datetime.utcnow().isoformat()
        sb.table("daily_bulletins").insert(data).execute()

def get_bulletins_range(start: date, end: date):
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("date, fun_fact").gte("date", str(start)).lte("date", str(end)).order("date", desc=True).execute()
    return result.data

def search_bulletins(keyword: str):
    sb = get_supabase()
    result = sb.table("daily_bulletins").select("*").order("bulletin_date", desc=True).execute()
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
