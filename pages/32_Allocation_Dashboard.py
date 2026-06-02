import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import os

st.set_page_config(
    page_title="Allocation Dashboard",
    page_icon="📊",
    layout="wide"
)

@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

# ============================================================================
# DARK WITH NEON GLOW STYLING - CONSISTENT THROUGHOUT
# ============================================================================
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #f5f5f5;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# MAIN TITLE - DARK WITH NEON GLOW
# ============================================================================
st.markdown("""
    <div style='
        background-color: #1a1a2e;
        padding: 30px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 30px;
        border: 2px solid #00ffff;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), inset 0 0 20px rgba(0, 255, 255, 0.1);
    '>
        <h1 style='color: white; margin: 0; font-size: 2.5rem;'>📊 Allocation Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# SUMMARY METRICS
# ============================================================================
st.markdown("""
    <div style='
        background-color: #1a1a2e;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 2px solid #00ffff;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
    '>
        <h2 style='margin: 0;'>📈 Summary Metrics</h2>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Students", "145")
with col2:
    st.metric("Allocated", "112")
with col3:
    st.metric("Pending", "28")
with col4:
    st.metric("On Waitlist", "15")

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3 = st.tabs(["📋 Recent Allocations", "⏳ Pending", "📊 Overview"])

with tab1:
    st.markdown("""
        <div style='
            background-color: #1a1a2e;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0 20px 0;
            border: 2px solid #00ffff;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
        '>
            <h3 style='margin: 0;'>Recent Allocations</h3>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        records = supabase.table("allocation_students")\
            .select("student_name, program, school, outcome, meeting_week")\
            .not_.is_("outcome", "null")\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        if records.data:
            df = pd.DataFrame(records.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No allocations yet")
    except:
        st.info("No allocations yet")

with tab2:
    st.markdown("""
        <div style='
            background-color: #1a1a2e;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0 20px 0;
            border: 2px solid #00ffff;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
        '>
            <h3 style='margin: 0;'>Pending Allocations</h3>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        pending = supabase.table("allocation_students")\
            .select("student_name, school, meeting_week")\
            .is_("outcome", "null")\
            .execute()
        
        if pending.data:
            df_pending = pd.DataFrame(pending.data)
            st.dataframe(df_pending, use_container_width=True, hide_index=True)
        else:
            st.info("No pending allocations")
    except:
        st.info("No pending allocations")

with tab3:
    st.markdown("""
        <div style='
            background-color: #1a1a2e;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0 20px 0;
            border: 2px solid #00ffff;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
        '>
            <h3 style='margin: 0;'>Overview</h3>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        total = supabase.table("allocation_students")\
            .select("id", count="exact")\
            .execute()
        
        allocated = supabase.table("allocation_students")\
            .select("id", count="exact")\
            .eq("outcome", "Allocated")\
            .execute()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", total.count if total.count else 0)
        with col2:
            st.metric("Allocated", allocated.count if allocated.count else 0)
    except:
        st.info("Unable to load overview")

st.caption("CLC-LBU Allocation Dashboard")
