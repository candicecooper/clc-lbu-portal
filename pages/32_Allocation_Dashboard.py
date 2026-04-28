import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Allocation Dashboard | CLC-LBU", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1A7A6E 0%, #4A9B8E 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        color: #D6F0EB;
        margin: 0.5rem 0 0 0;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1A7A6E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-card h2 {
        color: #1A7A6E;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .metric-card p {
        color: #666;
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .info-box {
        background-color: #D6F0EB;
        border-left: 4px solid #1A7A6E;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Allocation Dashboard</h1>
    <p>De-identified overview of student referrals, allocations, and placement data</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD / LINK TO EXCEL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📁 Data Source")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    <div class="info-box">
    <strong>📊 Excel File Location</strong><br>
    This dashboard reads from the shared allocation tracking Excel file. Upload the file below or enter allocation data directly in the Excel file stored on OneDrive.
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.link_button(
        "📝 Open Excel File (SharePoint)",
        "https://schoolssaedu-my.sharepoint.com/:x:/g/personal/candice_cooper330_schools_sa_edu_au/IQBhW-ZIsUHVRqPS9dTnsMCjAbVOnHlaDm42f3L0uv17gZo?email=Annette.Balestrin13%40schools.sa.edu.au&e=Fw3KpR",
        help="Opens the allocation tracking Excel file for data entry",
        use_container_width=True
    )

# File upload
uploaded_file = st.file_uploader(
    "Upload Allocation Excel File",
    type=['xlsx'],
    help="Upload the CLC_Allocation_Dashboard Excel file to view analytics"
)

if uploaded_file:
    try:
        # Read the Data_Model sheet
        df = pd.read_excel(uploaded_file, sheet_name='Data_Model')
        
        # Remove any empty rows
        df = df.dropna(how='all')
        
        if df.empty or len(df) == 0:
            st.warning("📭 No data found in Excel file. Add student records to the Data_Model sheet.")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} allocation records from Excel file")
        
        # ══════════════════════════════════════════════════════════════════
        # KEY METRICS
        # ══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### 📈 Key Metrics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total = len(df)
            st.markdown(f"""
            <div class="metric-card">
                <h2>{total}</h2>
                <p>Total Referrals</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            allocated = len(df[df['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h2>{allocated}</h2>
                <p>Allocated</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            waitlist = len(df[df['Allocation_Status'] == 'Waitlist']) if 'Allocation_Status' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h2>{waitlist}</h2>
                <p>Waitlist</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            rereferrals = 0
            if 'Previous_CLC_Placement' in df.columns and 'Previous_Other_LC' in df.columns:
                rereferrals = len(df[(df['Previous_CLC_Placement'] == 'Yes') | (df['Previous_Other_LC'] == 'Yes')])
            st.markdown(f"""
            <div class="metric-card">
                <h2>{rereferrals}</h2>
                <p>Re-referrals</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            partnerships = len(df[df['Partnership_Area'].notna()]) if 'Partnership_Area' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h2>{partnerships}</h2>
                <p>Partnerships</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ══════════════════════════════════════════════════════════════════
        # CHARTS
        # ══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### 📊 Visual Analytics")
        
        col1, col2 = st.columns(2)
        
        # Program Capacity Chart
        with col1:
            if 'Allocated_Program' in df.columns:
                program_counts = df['Allocated_Program'].value_counts()
                
                fig1 = go.Figure(data=[
                    go.Bar(
                        x=program_counts.index,
                        y=program_counts.values,
                        marker_color='#1A7A6E',
                        text=program_counts.values,
                        textposition='auto'
                    )
                ])
                
                fig1.update_layout(
                    title="Students by Program",
                    xaxis_title="Program",
                    yaxis_title="Count",
                    height=400,
                    showlegend=False
                )
                
                st.plotly_chart(fig1, use_container_width=True)
        
        # Partnership Distribution
        with col2:
            if 'Partnership_Area' in df.columns:
                partnership_counts = df['Partnership_Area'].value_counts()
                
                fig2 = go.Figure(data=[
                    go.Pie(
                        labels=partnership_counts.index,
                        values=partnership_counts.values,
                        marker=dict(colors=['#1A7A6E', '#4A9B8E', '#6BB5A8', '#8CCFC4', '#ADE0D9'])
                    )
                ])
                
                fig2.update_layout(
                    title="Partnership Distribution",
                    height=400
                )
                
                st.plotly_chart(fig2, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        # Priority Profile
        with col1:
            if 'Priority_Level' in df.columns:
                priority_counts = df['Priority_Level'].value_counts().sort_index()
                
                fig3 = go.Figure(data=[
                    go.Bar(
                        x=priority_counts.values,
                        y=['Priority ' + str(i) for i in priority_counts.index],
                        orientation='h',
                        marker_color='#C8760A',
                        text=priority_counts.values,
                        textposition='auto'
                    )
                ])
                
                fig3.update_layout(
                    title="Priority Profile",
                    xaxis_title="Count",
                    yaxis_title="Priority Level",
                    height=400,
                    showlegend=False
                )
                
                st.plotly_chart(fig3, use_container_width=True)
        
        # Placement History
        with col2:
            history_data = {
                'First-time': 0,
                'Previous CLC': 0,
                'Previous Other LC': 0,
                'Multiple Previous': 0
            }
            
            if 'Previous_CLC_Placement' in df.columns and 'Previous_Other_LC' in df.columns:
                history_data['First-time'] = len(df[(df['Previous_CLC_Placement'] == 'No') & (df['Previous_Other_LC'] == 'No')])
                history_data['Previous CLC'] = len(df[df['Previous_CLC_Placement'] == 'Yes'])
                history_data['Previous Other LC'] = len(df[df['Previous_Other_LC'] == 'Yes'])
                
                if 'Total_Previous_Placements' in df.columns:
                    history_data['Multiple Previous'] = len(df[df['Total_Previous_Placements'] > 1])
            
            fig4 = go.Figure(data=[
                go.Pie(
                    labels=list(history_data.keys()),
                    values=list(history_data.values()),
                    hole=0.4,
                    marker=dict(colors=['#1A7A6E', '#4A9B8E', '#C8760A', '#F5A623'])
                )
            ])
            
            fig4.update_layout(
                title="Placement History",
                height=400
            )
            
            st.plotly_chart(fig4, use_container_width=True)
        
        # ══════════════════════════════════════════════════════════════════
        # DE-IDENTIFIED SUMMARY TABLE
        # ══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### 📋 De-Identified Summary")
        
        st.info("ℹ️ Student names are hidden to protect privacy. This view is suitable for leadership presentations and broader sharing.")
        
        # Create de-identified view
        display_cols = [
            'Referring_School', 'Referral_Date', 'Allocation_Status', 
            'Allocated_Program', 'Partnership_Area', 'Previous_CLC_Placement',
            'Priority_Level', 'Current_Status'
        ]
        
        available_cols = [col for col in display_cols if col in df.columns]
        
        if available_cols:
            summary_df = df[available_cols].copy()
            
            # Add row numbers instead of names
            summary_df.insert(0, 'Record_ID', range(1, len(summary_df) + 1))
            
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.caption(f"Showing {len(summary_df)} records • Student names removed for privacy")
        
        # ══════════════════════════════════════════════════════════════════
        # INSIGHTS
        # ══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### 💡 Key Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Re-referral Patterns:**
            - Track students with previous placements
            - Identify support gaps requiring intervention
            - Inform service improvement strategies
            """)
        
        with col2:
            st.markdown("""
            **Partnership Engagement:**
            - Monitor school cluster participation
            - Identify opportunities for outreach
            - Strengthen collaborative relationships
            """)
        
    except Exception as e:
        st.error(f"⚠️ Error reading Excel file: {e}")
        st.info("Please ensure you're uploading the correct CLC Allocation Dashboard Excel file with a 'Data_Model' sheet.")

else:
    # Instructions when no file uploaded
    st.info("""
    📊 **How to Use This Dashboard:**
    
    1. **Enter Data**: Click the OneDrive link above to open the Excel file and add allocation records
    2. **View Dashboard**: Upload the Excel file using the uploader above
    3. **Share Insights**: This de-identified view is suitable for leadership meetings and broader sharing
    
    The dashboard automatically updates when you upload the latest version of the Excel file.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.85rem;">
    <p>📊 Allocation Dashboard | Cowandilla Learning Centre LBU</p>
    <p>🔒 De-identified data view | Student names removed for privacy protection</p>
</div>
""", unsafe_allow_html=True)
