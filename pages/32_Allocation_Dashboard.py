import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from collections import Counter
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="CLC Allocation Dashboard",
    page_icon="📊",
    layout="wide"
)

# Import database connection
try:
    from database import get_supabase_client
    supabase = get_supabase_client()
except:
    st.error("⚠️ Could not connect to database")
    st.stop()

# Title
st.title("📊 CLC Allocation Dashboard")
st.caption("Comprehensive view of student allocations across Adelaide partnerships")

# Add refresh button
col1, col2, col3 = st.columns([4, 1, 1])
with col2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col3:
    auto_refresh = st.checkbox("Auto-refresh 60s", value=False)

if auto_refresh:
    import time
    time.sleep(60)
    st.rerun()

st.markdown("---")

# ============================================================================
# LOAD DATA
# ============================================================================

@st.cache_data(ttl=60)
def load_allocation_data():
    """Load all allocation data"""
    try:
        result = supabase.table("allocation_students")\
            .select("*")\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

# Load data
all_data = load_allocation_data()
df = pd.DataFrame(all_data) if all_data else pd.DataFrame()

# Filter for completed allocations
completed_data = [r for r in all_data if r.get('outcome') in ['Allocated', 'Not Allocated']]
completed_df = pd.DataFrame(completed_data) if completed_data else pd.DataFrame()

# ============================================================================
# KEY METRICS
# ============================================================================

st.header("📈 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_records = len(all_data)
    st.metric("Total Records", total_records)

with col2:
    completed_count = len(completed_data)
    st.metric("Completed", completed_count)

with col3:
    draft_count = total_records - completed_count
    st.metric("Drafts", draft_count)

with col4:
    allocated = len([r for r in completed_data if r.get('outcome') == 'Allocated'])
    st.metric("Allocated", allocated)

with col5:
    returning = len([r for r in completed_data if r.get('previous_clc_placement') == 'Yes'])
    st.metric("Returning", returning)

# Last updated
st.caption(f"📅 Last updated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Current year: {datetime.now().year} | Total records: {total_records}")

st.markdown("---")

# ============================================================================
# ADELAIDE CATCHMENT MAP
# ============================================================================

st.header("🗺️ Adelaide Catchment Map")
st.caption("Geographic distribution of student allocations across partnership areas")

# Count by partnership
partnership_counts = Counter()
for record in completed_data:
    partnership = record.get('partnership_area', 'Unknown')
    if partnership:
        partnership_counts[partnership] += 1

total_students = len(completed_data)

# Partnership regions
partnership_regions = {
    "Le Fevre Peninsula": {
        "color": "#E74C3C",
        "coords": [[-34.78, 138.48], [-34.78, 138.52], [-34.84, 138.52], 
                   [-34.85, 138.50], [-34.84, 138.48]]
    },
    "Western Adelaide Shores": {
        "color": "#1ABC9C",
        "coords": [[-34.85, 138.48], [-34.85, 138.52], [-34.88, 138.52], 
                   [-34.88, 138.48]]
    },
    "Inner West": {
        "color": "#3498DB",
        "coords": [[-34.90, 138.54], [-34.90, 138.58], [-34.94, 138.58], 
                   [-34.94, 138.54]]
    },
    "West Torrens": {
        "color": "#F39C12",
        "coords": [[-34.93, 138.55], [-34.93, 138.59], [-34.96, 138.59], 
                   [-34.96, 138.55]]
    },
    "Adelaide Prospect": {
        "color": "#34495E",
        "coords": [[-34.84, 138.58], [-34.84, 138.62], [-34.88, 138.62], 
                   [-34.88, 138.58]]
    },
    "Holdfast": {
        "color": "#E67E22",
        "coords": [[-35.00, 138.50], [-35.00, 138.55], [-35.05, 138.55], 
                   [-35.05, 138.50]]
    },
    "Greenhill South": {
        "color": "#2ECC71",
        "coords": [[-34.96, 138.60], [-34.96, 138.66], [-35.01, 138.66], 
                   [-35.01, 138.60]]
    },
    "Mitcham Hills": {
        "color": "#9B59B6",
        "coords": [[-34.96, 138.62], [-34.96, 138.68], [-35.01, 138.68],
                   [-35.01, 138.62]]
    },
    "Orion": {
        "color": "#8E44AD",
        "coords": [[-34.68, 138.61], [-34.68, 138.67], [-34.73, 138.67], 
                   [-34.73, 138.61]]
    },
    "Marion Inland": {
        "color": "#16A085",
        "coords": [[-35.00, 138.54], [-35.00, 138.59], [-35.05, 138.59],
                   [-35.05, 138.54]]
    },
    "Marion Coastal": {
        "color": "#27AE60",
        "coords": [[-35.03, 138.50], [-35.03, 138.54], [-35.08, 138.54],
                   [-35.08, 138.50]]
    },
    "Onkaparinga": {
        "color": "#D35400",
        "coords": [[-35.10, 138.50], [-35.10, 138.58], [-35.18, 138.58],
                   [-35.18, 138.50]]
    }
}

# Map and stats layout
map_col, stats_col = st.columns([3, 1])

with map_col:
    # Create map
    m = folium.Map(
        location=[-34.92, 138.60],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Calculate max for opacity
    max_count = max(partnership_counts.values()) if partnership_counts else 1
    
    # Add regions
    for partnership_name, region_data in partnership_regions.items():
        count = partnership_counts.get(partnership_name, 0)
        
        if count > 0:
            opacity = 0.3 + (count / max_count) * 0.5
            percentage = (count / total_students * 100) if total_students > 0 else 0
            
            folium.Polygon(
                locations=region_data["coords"],
                color=region_data["color"],
                fill=True,
                fillColor=region_data["color"],
                fillOpacity=opacity,
                weight=3,
                popup=folium.Popup(
                    f"""
                    <div style='font-family: Arial; padding: 10px; min-width: 150px;'>
                        <h4 style='margin: 0 0 10px 0; color: {region_data["color"]};'>{partnership_name}</h4>
                        <p style='margin: 5px 0; font-size: 28px; font-weight: bold;'>{count}</p>
                        <p style='margin: 5px 0; color: #666;'>{percentage:.1f}% of total</p>
                        <p style='margin: 5px 0; font-size: 0.85em; color: #999;'>Click region for details</p>
                    </div>
                    """,
                    max_width=250
                ),
                tooltip=f"{partnership_name}: {count} students"
            ).add_to(m)
    
    # Add CLC marker
    folium.Marker(
        location=[-34.9286, 138.5830],
        popup=folium.Popup(
            "<div style='font-family: Arial; padding: 10px;'>"
            "<h4 style='margin: 0 0 5px 0;'>🏫 CLC-LBU</h4>"
            "<p style='margin: 0; font-size: 0.9em;'>Cowandilla Learning Centre</p>"
            "<p style='margin: 5px 0 0 0; font-size: 0.85em; color: #666;'>Learning & Behaviour Unit</p>"
            "</div>",
            max_width=200
        ),
        tooltip="Cowandilla Learning Centre",
        icon=folium.Icon(color='green', icon='home', prefix='fa')
    ).add_to(m)
    
    # Display map
    st_folium(m, width=None, height=550)

with stats_col:
    st.subheader("Distribution")
    
    # Sort by count
    sorted_partnerships = sorted(
        partnership_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for partnership, count in sorted_partnerships:
        if partnership and partnership != 'Unknown':
            percentage = (count / total_students * 100) if total_students > 0 else 0
            color = partnership_regions.get(partnership, {}).get('color', '#95A5A6')
            
            st.markdown(
                f"""
                <div style='padding: 10px; margin-bottom: 10px; border-left: 4px solid {color}; 
                            background: #f8f9fa; border-radius: 6px;'>
                    <div style='font-weight: 600; font-size: 0.9em; margin-bottom: 4px;'>
                        {partnership}
                    </div>
                    <div style='font-size: 1.8em; font-weight: bold; color: {color}; margin-bottom: 2px;'>
                        {count}
                    </div>
                    <div style='font-size: 0.85em; color: #666;'>
                        {percentage:.1f}% of total
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Unknown warning
    unknown_count = partnership_counts.get('Unknown', 0) + partnership_counts.get('', 0)
    if unknown_count > 0:
        st.markdown("---")
        st.warning(f"⚠️ **{unknown_count}** from unmapped schools")

st.markdown("---")

# ============================================================================
# DATA ANALYSIS
# ============================================================================

st.header("📊 Data Analysis")

tab1, tab2, tab3 = st.tabs(["Previous Placements", "Program Distribution", "Recent Allocations"])

with tab1:
    st.subheader("🔄 Previous Placement Analysis")
    
    if not completed_df.empty:
        # Previous CLC
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Previous CLC Placement:**")
            prev_clc_counts = completed_df['previous_clc_placement'].value_counts()
            for value, count in prev_clc_counts.items():
                st.write(f"- {value}: {count} students")
        
        with col2:
            st.write("**Previous Other LC:**")
            prev_other_counts = completed_df['previous_other_lc'].value_counts()
            for value, count in prev_other_counts.items():
                st.write(f"- {value}: {count} students")
        
        returning_count = len(completed_df[completed_df['previous_clc_placement'] == 'Yes'])
        st.info(f"📌 Total returning students (prev_clc=='Yes'): **{returning_count}**")
    else:
        st.info("No completed allocations yet")

with tab2:
    st.subheader("📚 Program Distribution")
    
    if not completed_df.empty and 'program' in completed_df.columns:
        program_counts = completed_df['program'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Bar chart
            st.bar_chart(program_counts)
        
        with col2:
            st.write("**Breakdown:**")
            for program, count in program_counts.items():
                if program:
                    percentage = (count / len(completed_df) * 100)
                    st.write(f"- {program}: {count} ({percentage:.1f}%)")
    else:
        st.info("No program data available")

with tab3:
    st.subheader("📅 Recent Allocations")
    
    if not completed_df.empty:
        # Show recent 10
        recent = completed_df.head(10)[['student_name', 'school', 'program', 'partnership_area', 'outcome']]
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No completed allocations yet")

st.markdown("---")

# ============================================================================
# DEBUG SECTION (Collapsible)
# ============================================================================

with st.expander("🔍 Debug: Dashboard Data", expanded=False):
    st.subheader("Raw Data from Database")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Raw previous_clc_placement:**")
        if not df.empty and 'previous_clc_placement' in df.columns:
            prev_counts = df['previous_clc_placement'].value_counts()
            st.dataframe(prev_counts, use_container_width=True)
            
            sample_values = df['previous_clc_placement'].head(5).tolist()
            st.write(f"Sample values: {sample_values}")
    
    with col2:
        st.write("**Outcome distribution:**")
        if not df.empty and 'outcome' in df.columns:
            outcome_counts = df['outcome'].value_counts()
            st.dataframe(outcome_counts, use_container_width=True)
    
    st.write("**Full data preview:**")
    if not df.empty:
        st.dataframe(df.head(10), use_container_width=True)
    else:
        st.info("No data in database")

# Footer
st.markdown("---")
st.caption(f"🔄 Data refreshes every 60 seconds | Last loaded: {datetime.now().strftime('%H:%M:%S')}")
