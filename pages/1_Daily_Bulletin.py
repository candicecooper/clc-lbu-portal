import streamlit as st
from datetime import date, timedelta, datetime
import database as db
import json
import time as _time

st.set_page_config(
    page_title="CLC Daily Bulletin",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import logout_button, get_staff_name
logout_button("sidebar")

# ══════════════════════════════════════════════════════════════
# 🔍 DIAGNOSTIC MODE - DELETE THIS SECTION AFTER FIXING
# ══════════════════════════════════════════════════════════════
st.write("---")
st.write("## 🔍 Connection Diagnostic")
try:
    sb = db.get_supabase()
    st.success("✅ Database connection created!")
    st.code(f"URL: {sb.supabase_url}")
    st.code(f"Key: {sb.supabase_key[:30]}...")
    
    # Try to access bulletins table
    try:
        result = sb.table("bulletins").select("*").limit(1).execute()
        st.success(f"✅ Can access 'bulletins' table! Found {len(result.data)} records")
        if result.data:
            st.write("Sample record:")
            st.json(result.data[0])
    except Exception as table_error:
        st.error(f"❌ Cannot access 'bulletins' table")
        st.code(str(table_error))
        
        # Try other tables
        st.write("### Testing other tables:")
        for table_name in ["bulletin_notices", "bulletin_changes", "staff_list", "students"]:
            try:
                test = sb.table(table_name).select("*").limit(1).execute()
                st.write(f"✅ {table_name}: {len(test.data)} records")
            except Exception as e:
                st.write(f"❌ {table_name}: {str(e)}")
                
except Exception as e:
    st.error(f"❌ Database connection failed!")
    st.code(str(e))

st.write("---")
st.write("**📸 Screenshot this entire diagnostic section and send it to Claude**")
st.write("---")
st.stop()  # STOP HERE - don't load the rest until we fix the connection
