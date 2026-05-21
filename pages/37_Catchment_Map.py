import streamlit as st
import folium
from streamlit_folium import st_folium
from collections import Counter
import json
from datetime import datetime

# Page config
st.set_page_config(page_title="Adelaide Catchment Map", page_icon="🗺️", layout="wide")

# Import database connection
try:
    from database import get_supabase_client
    supabase = get_supabase_client()
except:
    st.error("⚠️ Could not connect to database")
    st.stop()

# Header
st.title("🗺️ Adelaide Catchment Map")
st.caption("Student Allocation Distribution Across Partnership Areas")

# Fetch allocation data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_allocation_data():
    """Load allocation data from Supabase"""
    try:
        # Get all completed allocations
        result = supabase.table("allocation_students")\
            .select("school, partnership_area, student_name, outcome")\
            .in_("outcome", ["Allocated", "Not Allocated"])\
            .execute()
        
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

# Load data
allocations = load_allocation_data()

# Count by partnership
partnership_counts = Counter()
for allocation in allocations:
    partnership = allocation.get('partnership_area', 'Unknown')
    if partnership:
        partnership_counts[partnership] += 1

total_students = len(allocations)

# Partnership geographical data (Adelaide, SA)
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
        "coords": [[-34.96, 138.60], [-34.96, 138.66], [-35.01, 138.66],
                   [-35.01, 138.60]]
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

# Create layout
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    st.metric("Total Students", total_students)
with col2:
    st.metric("Partnership Areas", len([k for k in partnership_counts.keys() if k != 'Unknown']))
with col3:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# Main layout: Map on left, legend on right
map_col, legend_col = st.columns([3, 1])

with map_col:
    st.subheader("🗺️ Interactive Map")
    
    # Create map centered on Adelaide
    m = folium.Map(
        location=[-34.92, 138.60],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # Calculate max count for opacity scaling
    max_count = max(partnership_counts.values()) if partnership_counts else 1
    
    # Add partnership regions
    for partnership_name, region_data in partnership_regions.items():
        count = partnership_counts.get(partnership_name, 0)
        
        if count > 0:  # Only show regions with students
            # Calculate opacity based on count
            opacity = 0.3 + (count / max_count) * 0.5
            percentage = (count / total_students * 100) if total_students > 0 else 0
            
            # Create polygon
            folium.Polygon(
                locations=region_data["coords"],
                color=region_data["color"],
                fill=True,
                fillColor=region_data["color"],
                fillOpacity=opacity,
                weight=3,
                popup=folium.Popup(
                    f"""
                    <div style='font-family: Arial; padding: 10px;'>
                        <h4 style='margin: 0 0 10px 0;'>{partnership_name}</h4>
                        <p style='margin: 5px 0; font-size: 24px; font-weight: bold; color: {region_data["color"]};'>
                            {count} students
                        </p>
                        <p style='margin: 5px 0;'>{percentage:.1f}% of total</p>
                    </div>
                    """,
                    max_width=200
                ),
                tooltip=f"{partnership_name}: {count} students"
            ).add_to(m)
    
    # Add CLC marker
    folium.Marker(
        location=[-34.9286, 138.5830],
        popup=folium.Popup(
            "<div style='font-family: Arial; padding: 10px;'>"
            "<h4 style='margin: 0;'>🏫 CLC-LBU</h4>"
            "<p style='margin: 5px 0;'>Cowandilla Learning Centre</p>"
            "</div>",
            max_width=200
        ),
        tooltip="CLC-LBU",
        icon=folium.Icon(color='green', icon='home', prefix='fa')
    ).add_to(m)
    
    # Display map
    st_folium(m, width=None, height=600)

with legend_col:
    st.subheader("📊 Distribution")
    
    # Sort by count
    sorted_partnerships = sorted(
        partnership_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for partnership, count in sorted_partnerships:
        if partnership == 'Unknown' or partnership == '':
            continue
            
        percentage = (count / total_students * 100) if total_students > 0 else 0
        color = partnership_regions.get(partnership, {}).get('color', '#95A5A6')
        
        # Partnership card
        st.markdown(
            f"""
            <div style='padding: 12px; margin-bottom: 10px; border-left: 4px solid {color}; 
                        background: #f8f9fa; border-radius: 6px;'>
                <div style='font-weight: 600; font-size: 0.9em; margin-bottom: 4px;'>
                    {partnership}
                </div>
                <div style='font-size: 1.8em; font-weight: bold; color: {color};'>
                    {count}
                </div>
                <div style='font-size: 0.85em; color: #666;'>
                    {percentage:.1f}% of total
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Unknown count
    unknown_count = partnership_counts.get('Unknown', 0) + partnership_counts.get('', 0)
    if unknown_count > 0:
        st.markdown("---")
        st.warning(f"⚠️ **{unknown_count} students** from unknown/unmapped partnerships")

# Additional info
st.markdown("---")

# Expandable details
with st.expander("ℹ️ About This Map"):
    st.markdown("""
    ### How the Map Works
    
    - **Color Intensity:** Darker colors indicate more students from that partnership area
    - **Interactive:** Click any colored region to see detailed student count
    - **Real-time:** Updates automatically as new allocations are added
    - **CLC Location:** Green marker shows Cowandilla Learning Centre
    
    ### Partnership Coverage
    
    The map shows all Adelaide metropolitan partnership areas that CLC-LBU serves. 
    Each region is color-coded and the opacity increases with the number of allocated students.
    
    ### Data Source
    
    Data is pulled directly from the allocation_students table and shows only completed 
    allocations (outcome = "Allocated" or "Not Allocated"). Draft allocations are not included.
    
    **Last Updated:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
    """)

with st.expander("📈 Detailed Statistics"):
    if total_students > 0:
        st.markdown("### Students by Partnership")
        
        # Create breakdown table
        data_rows = []
        for partnership, count in sorted_partnerships:
            if partnership and partnership != 'Unknown':
                percentage = (count / total_students * 100)
                data_rows.append({
                    "Partnership": partnership,
                    "Students": count,
                    "Percentage": f"{percentage:.1f}%"
                })
        
        if data_rows:
            st.dataframe(data_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No allocation data available yet")

# Footer
st.caption(f"🔄 Auto-refresh: Data cached for 5 minutes | Last refresh: {datetime.now().strftime('%H:%M:%S')}")
