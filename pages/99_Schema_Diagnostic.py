import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Schema Diagnostic", page_icon="🔍")

st.title("🔍 Database Schema Diagnostic")

# Connect to Supabase
url = st.secrets.get("BEHAVIOUR_SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
key = st.secrets.get("BEHAVIOUR_SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")

if not url or not key:
    st.error("Supabase credentials not configured")
    st.stop()

sb = create_client(url, key)

st.subheader("smartar_tracking Table Schema")

try:
    # Try to get one row to see the columns
    result = sb.table("smartar_tracking").select("*").limit(1).execute()
    
    if result.data and len(result.data) > 0:
        st.success("✅ Table exists and has data!")
        st.write("**Sample row:**")
        st.json(result.data[0])
        
        st.write("**Columns found:**")
        columns = list(result.data[0].keys())
        for col in columns:
            st.write(f"- `{col}` (type: {type(result.data[0][col]).__name__})")
    else:
        st.warning("Table exists but is empty. Showing structure...")
        # Try to insert and delete a test row to see columns
        st.info("Cannot determine columns from empty table. Try adding one tracking record first.")
        
except Exception as e:
    st.error(f"Error querying table: {e}")
    st.info("The table might not exist or might have different permissions.")

st.markdown("---")
st.subheader("smartar_goals Table Schema")

try:
    result = sb.table("smartar_goals").select("*").limit(1).execute()
    
    if result.data and len(result.data) > 0:
        st.success("✅ Table exists and has data!")
        st.write("**Sample row:**")
        st.json(result.data[0])
        
        st.write("**Columns found:**")
        columns = list(result.data[0].keys())
        for col in columns:
            st.write(f"- `{col}` (type: {type(result.data[0][col]).__name__})")
    else:
        st.warning("Table exists but is empty.")
        
except Exception as e:
    st.error(f"Error querying table: {e}")

st.markdown("---")
st.caption("Copy the column names and share them so I can fix the tracking features!")
