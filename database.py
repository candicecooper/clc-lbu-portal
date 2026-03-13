import streamlit as st
from supabase import create_client, Client
import json
from datetime import date, datetime

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

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
