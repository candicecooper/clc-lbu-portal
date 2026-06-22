import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import folium
from streamlit_folium import st_folium
from collections import Counter
import os
import pickle
from datetime import datetime

# Define persistent data file location
DATA_FILE = "clc_lbu_data.pkl"

def save_data_to_file(data):
    """Save data to persistent file"""
    try:
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(data, f)
        return True
    except:
        return False

def load_data_from_file():
    """Load data from persistent file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
    except:
        pass
    return None

def clear_data_file():
    """Delete the persistent data file"""
    try:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        return True
    except:
        return False

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; border-right: 2px solid #00e5ff !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }

/* Sidebar text sizing and overflow fixes */
[data-testid="stSidebar"] h3 {
    font-size: 16px !important;
    line-height: 1.2 !important;
    margin: 15px 0 10px 0 !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
}

[data-testid="stSidebar"] h4 {
    font-size: 14px !important;
    line-height: 1.2 !important;
    margin: 10px 0 8px 0 !important;
}

[data-testid="stSidebar"] p {
    font-size: 13px !important;
    line-height: 1.3 !important;
    word-wrap: break-word !important;
}

[data-testid="stSidebar"] .stMarkdown {
    font-size: 13px !important;
}

[data-testid="stSidebar"] .stButton > button {
    font-size: 13px !important;
    padding: 12px 8px !important;
    min-height: auto !important;
    height: auto !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] {
    font-size: 12px !important;
}
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2.5rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { 
    background: linear-gradient(135deg, #1a2942 0%, #0d1929 100%) !important; 
    color: #00e5ff !important; 
    border: 2px solid #00e5ff !important; 
    font-weight: 600 !important; 
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
    padding: 20px 10px !important;
    min-height: 80px !important;
    font-size: 16px !important;
    border-radius: 8px !important;
}
.stButton > button:hover { 
    background: linear-gradient(135deg, #00e5ff 0%, #00b8d4 100%) !important; 
    color: #0a0e27 !important; 
    box-shadow: 0 0 40px rgba(0, 229, 255, 0.7) !important; 
}

button[kind="secondary"] {
    background: linear-gradient(135deg, #1a2942 0%, #0d1929 100%) !important;
    color: #00e5ff !important;
    border: 2px solid #00e5ff !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
}

/* Catch-all for any button element */
button, [role="button"], input[type="button"] {
    background: linear-gradient(135deg, #1a2942 0%, #0d1929 100%) !important;
    color: #00e5ff !important;
    border: 2px solid #00e5ff !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
}
p { color: #ffffff !important; }

/* Remove glow from file uploader and other icons */
[data-testid="fileUploadDropzone"] {
    border: 1px solid #00e5ff !important;
    box-shadow: none !important;
}

[data-testid="stFileUploadDropzone"] {
    box-shadow: none !important;
}

/* Remove focus glow from all inputs and interactive elements */
input:focus, button:focus, select:focus {
    outline: none !important;
    box-shadow: none !important;
}

/* Remove glow from file upload icon area */
.stFileUploadDropzone:focus-within {
    box-shadow: none !important;
}

/* Reduce glow on hover for file upload */
[data-testid="stFileUploadDropzone"]:hover {
    box-shadow: none !important;
}

/* Remove blue outline from Plotly chart buttons (zoom, pan, autoscale, etc) */
.plotly-container button {
    outline: none !important;
    box-shadow: none !important;
    border: none !important;
}

.plotly-container button:hover {
    outline: none !important;
    box-shadow: none !important;
}

.plotly-container button:focus {
    outline: none !important;
    box-shadow: none !important;
}


/* Hide/clean up Streamlit menu and toolbar */
[data-testid="stToolbar"] {
    visibility: hidden !important;
    height: 0 !important;
}

/* Hide "Made with Streamlit" footer */
footer {
    visibility: hidden !important;
    height: 0 !important;
}

footer::before {
    visibility: hidden !important;
}

/* Clean up menu button styling - reduce text size */
button[kind="header"] {
    font-size: 11px !important;
}

[role="menu"] {
    font-size: 11px !important;
}

[role="menuitem"] {
    font-size: 11px !important;
    padding: 6px 10px !important;
    line-height: 1.2 !important;
}

/* Reduce header area padding */
[data-testid="stHeader"] {
    padding: 6px 12px !important;
}

/* Remove Glow from Plotly modebar buttons */
.modebar-btn {
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    border: none !important;
    background-color: transparent !important;
}

.modebar-btn:hover {
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

.modebar-btn:focus {
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

.modebar-btn.active {
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

/* Remove background from entire modebar */
.modebar {
    background: transparent !important;
}

/* Remove any SVG styling */
.modebar-btn svg {
    opacity: 0.6 !important;
}

.modebar-btn svg:hover {
    opacity: 0.9 !important;
}

/* Fix chart axis labels for readability */
.plotly .xtick text,
.plotly .ytick text {
    font-size: 12px !important;
    font-family: 'Poppins', sans-serif !important;
}

/* Ensure axis titles are readable */
.plotly .axis-title {
    font-size: 13px !important;
    color: #ffffff !important;
}

.dashboard-title {
    background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 229, 255, 0.05) 100%);
    border: 2px solid rgba(0, 229, 255, 0.4);
    border-radius: 12px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.15);
}

.metric-card {
    background: linear-gradient(135deg, #1A2942 0%, #243556 100%);
    border: 1.5px solid #2D3F5F;
    border-radius: 12px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.3s ease;
}
.metric-card:hover {
    border-color: #00e5ff;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}
</style>

<div class="dashboard-title">
    <h1 style="margin: 0; text-align: center; color: #00e5ff; font-size: 2.8em; letter-spacing: 2px; font-weight: 800;">
        CLC-LBU ALLOCATION DASHBOARD
    </h1>
    <p style="text-align: center; color: #ffffff; margin: 10px 0 0 0; font-size: 1.15em; font-weight: 500;">
        Student Allocation & Equity Analysis
    </p>
</div>
""", unsafe_allow_html=True)

if 'drill_down_view' not in st.session_state:
    st.session_state.drill_down_view = None
if 'terms_selected' not in st.session_state:
    st.session_state.terms_selected = set()  # Empty = show all terms
if 'years_selected' not in st.session_state:
    st.session_state.years_selected = set()  # Empty = show all years
if 'programs_selected' not in st.session_state:
    st.session_state.programs_selected = set()  # Empty = show all programs
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

with st.sidebar:
    st.markdown("### UPLOAD DATA")
    
    # Check if saved data exists on startup
    saved_data = load_data_from_file()
    
    if saved_data is not None and st.session_state.uploaded_data is None:
        st.session_state.uploaded_data = saved_data
        st.session_state.data_loaded = True
    
    if st.session_state.data_loaded and st.session_state.uploaded_data is not None:
        st.success("✅ Data loaded in memory")
        st.info("Data saved and will persist between sessions")
        
        if st.button("Clear Saved Data & Upload New", use_container_width=True, key="clear_data"):
            st.session_state.uploaded_data = None
            st.session_state.data_loaded = False
            clear_data_file()
            st.rerun()
    
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    
    if uploaded_file is not None and not st.session_state.data_loaded:
        # Load new file, store in session, and save to disk
        st.session_state.uploaded_data = pd.read_excel(uploaded_file)
        st.session_state.data_loaded = True
        
        # Save to persistent file
        if save_data_to_file(st.session_state.uploaded_data):
            st.success(f"✅ {uploaded_file.name} loaded & saved")
        else:
            st.success(f"✅ {uploaded_file.name} loaded")
    
    st.markdown("---")
    
    # Add Show All Data button
    if st.button("SHOW ALL DATA (Clear All Filters)", use_container_width=True, key="show_all"):
        st.session_state.terms_selected = set()
        st.session_state.years_selected = set()
        st.session_state.programs_selected = set()
        st.rerun()
    
    st.markdown("---")
    
    with st.expander("FILTERS (Click to expand/collapse)", expanded=True):
        st.markdown("**Term**")
        tc1, tc2, tc3 = st.columns(3)
        if tc1.button("All", key="t_all", use_container_width=True): 
            st.session_state.terms_selected = {1.0, 2.0, 3.0, 4.0}
        if tc2.button("None", key="t_none", use_container_width=True): 
            st.session_state.terms_selected = set()
        if tc3.button("T2 Now", key="t_current", use_container_width=True): 
            st.session_state.terms_selected = {2.0}
        
        t1, t2, t3, t4 = st.columns(4)
        if t1.button("T1" + (" ✓" if 1.0 in st.session_state.terms_selected else ""), key="t1", use_container_width=True): 
            st.session_state.terms_selected ^= {1.0}
        if t2.button("T2" + (" ✓" if 2.0 in st.session_state.terms_selected else ""), key="t2", use_container_width=True): 
            st.session_state.terms_selected ^= {2.0}
        if t3.button("T3" + (" ✓" if 3.0 in st.session_state.terms_selected else ""), key="t3", use_container_width=True): 
            st.session_state.terms_selected ^= {3.0}
        if t4.button("T4" + (" ✓" if 4.0 in st.session_state.terms_selected else ""), key="t4", use_container_width=True): 
            st.session_state.terms_selected ^= {4.0}
        
        st.markdown("**Year**")
        yc1, yc2 = st.columns(2)
        if yc1.button("All", key="y_all", use_container_width=True): 
            st.session_state.years_selected = {2025.0, 2026.0}
        if yc2.button("None", key="y_none", use_container_width=True): 
            st.session_state.years_selected = set()
        
        y1, y2 = st.columns(2)
        if y1.button("2025" + (" ✓" if 2025.0 in st.session_state.years_selected else ""), key="y1", use_container_width=True): 
            st.session_state.years_selected ^= {2025.0}
        if y2.button("2026" + (" ✓" if 2026.0 in st.session_state.years_selected else ""), key="y2", use_container_width=True): 
            st.session_state.years_selected ^= {2026.0}
        
        st.markdown("**Program**")
        pc1, pc2 = st.columns(2)
        if pc1.button("All", key="p_all", use_container_width=True): 
            st.session_state.programs_selected = {"JP", "PY", "SY"}
        if pc2.button("None", key="p_none", use_container_width=True): 
            st.session_state.programs_selected = set()
        
        p1, p2, p3 = st.columns(3)
        if p1.button("JP" + (" ✓" if "JP" in st.session_state.programs_selected else ""), key="p1", use_container_width=True): 
            st.session_state.programs_selected ^= {"JP"}
        if p2.button("PY" + (" ✓" if "PY" in st.session_state.programs_selected else ""), key="p2", use_container_width=True): 
            st.session_state.programs_selected ^= {"PY"}
        if p3.button("SY" + (" ✓" if "SY" in st.session_state.programs_selected else ""), key="p3", use_container_width=True): 
            st.session_state.programs_selected ^= {"SY"}

if st.session_state.data_loaded and st.session_state.uploaded_data is not None:
    try:
        all_data = st.session_state.uploaded_data.copy()
        
        for col in all_data.columns:
            if all_data[col].dtype == 'object':
                all_data[col] = all_data[col].astype(str).str.strip()
        
        # Show ALL students regardless of status
        filtered = all_data.copy()
        
        if st.session_state.terms_selected:
            filtered = filtered[filtered['Term'].isin(st.session_state.terms_selected)]
        
        if st.session_state.years_selected:
            filtered = filtered[filtered['Referral_Year'].isin(st.session_state.years_selected)]
        
        if st.session_state.programs_selected:
            filtered = filtered[filtered['Allocated_Program'].isin(st.session_state.programs_selected)]
        
        total = int(len(filtered))
        allocated = int(len(filtered[filtered['Allocation_Status'] == 'Allocated']))
        atsi = int(len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        eald = int(len(filtered[filtered['Flag_EALD'] == 'Yes']))
        swd = int(len(filtered[filtered['Flag_SWD'] == 'Yes']))
        
        # Calculate repeating students
        student_col = None
        for col in ['Student_Name', 'student_name', 'Student', 'Name', 'Full_Name']:
            if col in filtered.columns:
                student_col = col
                break
        
        repeating_students = 0
        if student_col:
            student_counts = filtered[student_col].value_counts()
            repeating_students = int(len(student_counts[student_counts > 1]))
        
        st.markdown("## Metrics & Drill Down")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            if st.button(f"Total\n{total}", key="metric_total", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "total"
        
        with col2:
            if st.button(f"Allocated\n{allocated}", key="metric_allocated", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "allocated"
        
        with col3:
            if st.button(f"ATSI\n{atsi}", key="metric_atsi", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "atsi"
        
        with col4:
            if st.button(f"SWD\n{swd}", key="metric_swd", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "swd"
        
        with col5:
            if st.button(f"EALD\n{eald}", key="metric_eald", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "eald"
        
        with col6:
            if st.button(f"Repeating\n{repeating_students}", key="metric_repeating", use_container_width=True, help="Click to drill down"):
                st.session_state.drill_down_view = "repeating"
        
        st.markdown("---")
        
        # DRILL DOWN VIEWS
        if st.session_state.drill_down_view:
            st.markdown(f"## Detailed Analysis: {st.session_state.drill_down_view.upper()}")
            
            if st.button("Back to Overview", key="back_btn"):
                st.session_state.drill_down_view = None
                st.rerun()
            
            tabs = st.tabs(["Overview", "By Program", "By Partnership", "By School", "Disability Profile", "Trends"])
            
            if st.session_state.drill_down_view == "total":
                drill_data = filtered
                
                with tabs[0]:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Students", int(len(drill_data)))
                    c2.metric("Allocated", int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated'])))
                    allocated_pct = int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated']) / len(drill_data) * 100) if len(drill_data) > 0 else 0
                    c3.metric("Allocation %", f"{allocated_pct}%")
                    c4.metric("Waiting List", int(len(drill_data[drill_data['Allocation_Status'] == 'On Waiting List'])))
                
                with tabs[1]:
                    prog = drill_data['Allocated_Program'].value_counts().sort_index()
                    if len(prog) > 0:
                        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color=['#00e5ff', '#ffd93d', '#ff6b6b'][:len(prog)], text=prog.values.astype(int), textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_xaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#00e5ff', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_yaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
                    if 'Referring_School' in drill_data.columns:
                        schools = drill_data['Referring_School'].value_counts().head(15)
                        if len(schools) > 0:
                            fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#00e5ff', text=schools.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_yaxes(showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[4]:
                    if 'Term' in drill_data.columns and 'Referral_Year' in drill_data.columns:
                        valid_data = drill_data.dropna(subset=['Term', 'Referral_Year'])
                        valid_data['Term_Year'] = valid_data['Term'].astype(int).astype(str) + '-' + valid_data['Referral_Year'].astype(int).astype(str)
                        trend_data = valid_data['Term_Year'].value_counts().sort_index()
                        if len(trend_data) > 0:
                            fig = go.Figure([go.Scatter(x=trend_data.index, y=trend_data.values, mode='lines+markers', marker=dict(size=10, color='#00e5ff'), line=dict(width=3, color='#00e5ff'))])
                            fig.update_yaxes(dtick=1, showgrid=False)
                            fig.update_xaxes(showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, xaxis_title='Term-Year', yaxis_title='Students')
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[5]:
                    st.markdown("**Total Student Overview**")
                    st.write(f"Total students: {int(len(drill_data))}")
                    st.write(f"Allocated: {int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated']))} ({allocated_pct}%)")
                    st.write(f"On Waiting List: {int(len(drill_data[drill_data['Allocation_Status'] == 'On Waiting List']))}")
            
            elif st.session_state.drill_down_view == "allocated":
                drill_data = filtered[filtered['Allocation_Status'] == 'Allocated']
                
                with tabs[0]:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Allocated", int(len(drill_data)))
                    swd_allocated = int(len(drill_data[drill_data['Flag_SWD'] == 'Yes']))
                    c2.metric("SWD", swd_allocated)
                    atsi_allocated = int(len(drill_data[drill_data['Flag_ATSI'] == 'Yes']))
                    c3.metric("ATSI", atsi_allocated)
                    eald_allocated = int(len(drill_data[drill_data['Flag_EALD'] == 'Yes']))
                    c4.metric("EALD", eald_allocated)
                
                with tabs[1]:
                    prog = drill_data['Allocated_Program'].value_counts().sort_index()
                    if len(prog) > 0:
                        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color=['#00e5ff', '#ffd93d', '#ff6b6b'][:len(prog)], text=prog.values.astype(int), textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_xaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#10b981', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_yaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
                    if 'Referring_School' in drill_data.columns:
                        schools = drill_data['Referring_School'].value_counts().head(15)
                        if len(schools) > 0:
                            fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#10b981', text=schools.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_yaxes(showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[4]:
                    if 'Term' in drill_data.columns and 'Referral_Year' in drill_data.columns:
                        valid_data = drill_data.dropna(subset=['Term', 'Referral_Year'])
                        valid_data['Term_Year'] = valid_data['Term'].astype(int).astype(str) + '-' + valid_data['Referral_Year'].astype(int).astype(str)
                        trend_data = valid_data['Term_Year'].value_counts().sort_index()
                        if len(trend_data) > 0:
                            fig = go.Figure([go.Scatter(x=trend_data.index, y=trend_data.values, mode='lines+markers', marker=dict(size=10, color='#10b981'), line=dict(width=3, color='#10b981'))])
                            fig.update_yaxes(dtick=1, showgrid=False)
                            fig.update_xaxes(showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, xaxis_title='Term-Year', yaxis_title='Students')
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[5]:
                    st.markdown("**Allocated Students Overview**")
                    st.write(f"Total allocated: {int(len(drill_data))}")
                    st.write(f"SWD: {swd_allocated}")
                    st.write(f"ATSI: {atsi_allocated}")
                    st.write(f"EALD: {eald_allocated}")
            
            elif st.session_state.drill_down_view == "atsi":
                drill_data = filtered[filtered['Flag_ATSI'] == 'Yes']
                
                with tabs[0]:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total ATSI", int(len(drill_data)))
                    c2.metric("Allocated", int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated'])))
                    allocated_pct = int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated']) / len(drill_data) * 100) if len(drill_data) > 0 else 0
                    c3.metric("Allocation %", f"{allocated_pct}%")
                    c4.metric("Waiting List", int(len(drill_data[drill_data['Allocation_Status'] == 'On Waiting List'])))
                
                with tabs[1]:
                    prog = drill_data['Allocated_Program'].value_counts().sort_index()
                    if len(prog) > 0:
                        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#ff6b6b', text=prog.values.astype(int), textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ff6b6b', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
                    if 'Referring_School' in drill_data.columns:
                        schools = drill_data['Referring_School'].value_counts().head(15)
                        if len(schools) > 0:
                            fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#ff6b6b', text=schools.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[4]:
                    disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
                    disability_labels = ['ASD', 'ADHD', 'Speech', 'Intellectual', 'Learning', 'Sensory', 'ODD', 'PDA']
                    dis_counts = []
                    for col in disability_cols:
                        if col in drill_data.columns:
                            dis_counts.append(int(len(drill_data[drill_data[col] == 'Yes'])))
                        else:
                            dis_counts.append(0)
                    if sum(dis_counts) > 0:
                        fig = go.Figure([go.Bar(x=disability_labels, y=dis_counts, marker_color='#ff6b6b', text=dis_counts, textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[5]:
                    if 'Term' in drill_data.columns and 'Referral_Year' in drill_data.columns:
                        valid_data = drill_data.dropna(subset=['Term', 'Referral_Year'])
                        valid_data['Term_Year'] = valid_data['Term'].astype(int).astype(str) + '-' + valid_data['Referral_Year'].astype(int).astype(str)
                        term_trend = valid_data['Term_Year'].value_counts().sort_index()
                        if len(term_trend) > 0:
                            fig = go.Figure([go.Scatter(x=term_trend.index, y=term_trend.values, mode='lines+markers', marker_color='#ff6b6b', line=dict(width=3), marker_size=10)])
                            fig.update_yaxes(dtick=1, showgrid=False)
                            fig.update_xaxes(showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, xaxis_title='Term-Year', yaxis_title='Students')
                            st.plotly_chart(fig, use_container_width=True)
            
            elif st.session_state.drill_down_view == "swd":
                drill_data = filtered[filtered['Flag_SWD'] == 'Yes']
                
                with tabs[0]:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total SWD", int(len(drill_data)))
                    c2.metric("Allocated", int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated'])))
                    allocated_pct = int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated']) / len(drill_data) * 100) if len(drill_data) > 0 else 0
                    c3.metric("Allocation %", f"{allocated_pct}%")
                    c4.metric("Waiting List", int(len(drill_data[drill_data['Allocation_Status'] == 'On Waiting List'])))
                
                with tabs[1]:
                    prog = drill_data['Allocated_Program'].value_counts().sort_index()
                    if len(prog) > 0:
                        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff', text=prog.values.astype(int), textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#00e5ff', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
                    if 'Referring_School' in drill_data.columns:
                        schools = drill_data['Referring_School'].value_counts().head(15)
                        if len(schools) > 0:
                            fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#00e5ff', text=schools.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[5]:
                    disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
                    disability_labels = ['ASD', 'ADHD', 'Speech', 'Intellectual', 'Learning', 'Sensory', 'ODD', 'PDA']
                    dis_counts = []
                    for col in disability_cols:
                        if col in drill_data.columns:
                            dis_counts.append(int(len(drill_data[drill_data[col] == 'Yes'])))
                        else:
                            dis_counts.append(0)
                    if sum(dis_counts) > 0:
                        fig = go.Figure([go.Bar(x=disability_labels, y=dis_counts, marker_color='#00e5ff', text=dis_counts, textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
            
            elif st.session_state.drill_down_view == "eald":
                drill_data = filtered[filtered['Flag_EALD'] == 'Yes']
                
                with tabs[0]:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total EALD", int(len(drill_data)))
                    c2.metric("Allocated", int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated'])))
                    allocated_pct = int(len(drill_data[drill_data['Allocation_Status'] == 'Allocated']) / len(drill_data) * 100) if len(drill_data) > 0 else 0
                    c3.metric("Allocation %", f"{allocated_pct}%")
                    c4.metric("Waiting List", int(len(drill_data[drill_data['Allocation_Status'] == 'On Waiting List'])))
                
                with tabs[1]:
                    prog = drill_data['Allocated_Program'].value_counts().sort_index()
                    if len(prog) > 0:
                        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#ffd93d', text=prog.values.astype(int), textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ffd93d', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
                    if 'Referring_School' in drill_data.columns:
                        schools = drill_data['Referring_School'].value_counts().head(15)
                        if len(schools) > 0:
                            fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#ffd93d', text=schools.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                
                with tabs[5]:
                    disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
                    disability_labels = ['ASD', 'ADHD', 'Speech', 'Intellectual', 'Learning', 'Sensory', 'ODD', 'PDA']
                    dis_counts = []
                    for col in disability_cols:
                        if col in drill_data.columns:
                            dis_counts.append(int(len(drill_data[drill_data[col] == 'Yes'])))
                        else:
                            dis_counts.append(0)
                    if sum(dis_counts) > 0:
                        fig = go.Figure([go.Bar(x=disability_labels, y=dis_counts, marker_color='#ffd93d', text=dis_counts, textposition='outside')])
                        fig.update_yaxes(dtick=1, showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
            
            elif st.session_state.drill_down_view == "repeating":
                if student_col:
                    st.markdown("### Students Appearing Multiple Times")
                    
                    student_counts = filtered[student_col].value_counts()
                    repeating = student_counts[student_counts > 1].sort_values(ascending=False)
                    
                    with tabs[0]:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Unique Students", int(len(student_counts)))
                        c2.metric("Repeating Students", int(len(repeating)))
                        c3.metric("Total Repeat Enrollments", int(repeating.sum()))
                        
                        st.markdown("**Students with Multiple Enrollments - Enrollment History**")
                        st.markdown("*Student names withheld for privacy - showing enrollment patterns instead*")
                        
                        # Build table of repeating student enrollments
                        repeating_details = []
                        for student_name in repeating.index[:20]:  # Top 20 repeating
                            student_recs = filtered[filtered[student_col] == student_name]
                            for _, rec in student_recs.iterrows():
                                school = rec.get('Referring_School', 'Unknown')
                                program = rec.get('Allocated_Program', '-')
                                term = rec.get('Term', '-')
                                year = rec.get('Referral_Year', '-')
                                age = rec.get('Age', '-') if 'Age' in rec.index else 'N/A'
                                
                                # Handle NaN values safely
                                term_str = '-'
                                if pd.notna(term) and term != '-':
                                    try:
                                        term_str = f"T{int(term)}"
                                    except:
                                        term_str = '-'
                                
                                year_str = '-'
                                if pd.notna(year) and year != '-':
                                    try:
                                        year_str = int(year)
                                    except:
                                        year_str = '-'
                                
                                repeating_details.append({
                                    'School': school,
                                    'Program': program,
                                    'Term': term_str,
                                    'Year': year_str,
                                    'Age': age,
                                    'Enrollments for This Student': int(repeating[student_name])
                                })
                        
                        if repeating_details:
                            repeating_df = pd.DataFrame(repeating_details)
                            st.dataframe(repeating_df, use_container_width=True, hide_index=True)
                    
                    with tabs[1]:
                        st.markdown("**Repeating Students by Program**")
                        repeating_filtered = filtered[filtered[student_col].isin(repeating.index)]
                        prog = repeating_filtered['Allocated_Program'].value_counts().sort_index()
                        if len(prog) > 0:
                            fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff', text=prog.values.astype(int), textposition='outside')])
                            fig.update_yaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with tabs[2]:
                        st.markdown("**Repeating Students by Partnership**")
                        part = repeating_filtered['Partnership_Area'].value_counts()
                        if len(part) > 0:
                            fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#00e5ff', text=part.values.astype(int), textposition='outside')])
                            fig.update_xaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with tabs[3]:
                        st.markdown("**Repeating Students by School**")
                        if 'Referring_School' in repeating_filtered.columns:
                            schools = repeating_filtered['Referring_School'].value_counts().head(15)
                            if len(schools) > 0:
                                fig = go.Figure([go.Bar(y=schools.index, x=schools.values, orientation='h', marker_color='#00e5ff', text=schools.values.astype(int), textposition='outside')])
                                fig.update_xaxes(dtick=1, showgrid=False)
                                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                                st.plotly_chart(fig, use_container_width=True)
                    
                    with tabs[5]:
                        st.markdown("**Repeating Students: Terms Enrolled**")
                        if 'Term' in repeating_filtered.columns:
                            terms = repeating_filtered['Term'].value_counts().sort_index()
                            fig = go.Figure([go.Bar(x=['T' + str(int(t)) for t in terms.index], y=terms.values, marker_color='#00e5ff', text=terms.values.astype(int), textposition='outside')])
                            fig.update_yaxes(dtick=1, showgrid=False)
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with tabs[5]:
                        st.markdown("**Why Students Are Repeating**")
                        st.markdown("Students appear multiple times due to:")
                        st.markdown("- **Different Terms**: Enrolled in T1, then T2, then T3, etc.")
                        st.markdown("- **Different Programs**: Started in JP, moved to PY")
                        st.markdown("- **Different Years**: Re-enrolled in different school year")
                        st.markdown("- **Status Changes**: Status changed from pending to allocated")
                else:
                    st.warning("Student name column not found in data")
        
        else:
            # MAIN OVERVIEW
            st.markdown("## Program Distribution")
            prog = filtered['Allocated_Program'].value_counts().sort_index()
            if len(prog) > 0:
                fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color=['#00e5ff', '#ffd93d', '#ff6b6b'][:len(prog)], text=prog.values.astype(int), textposition='outside')])
                fig.update_yaxes(dtick=1, showgrid=False)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=350, showlegend=False, margin=dict(l=0, r=120, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("## School Equity Analysis - Over/Under Representation")
            st.markdown("*Shows which schools refer students with SWD, ATSI, EALD at higher rates than overall*")
            
            # Calculate overall rates
            overall_swd_rate = (int(len(filtered[filtered['Flag_SWD'] == 'Yes'])) / total * 100) if total > 0 else 0
            overall_atsi_rate = (int(len(filtered[filtered['Flag_ATSI'] == 'Yes'])) / total * 100) if total > 0 else 0
            overall_eald_rate = (int(len(filtered[filtered['Flag_EALD'] == 'Yes'])) / total * 100) if total > 0 else 0
            
            # Analyze by school
            if 'Referring_School' in filtered.columns:
                schools = filtered['Referring_School'].unique()
                school_data = []
                
                for school in schools:
                    school_students = filtered[filtered['Referring_School'] == school]
                    school_total = len(school_students)
                    
                    if school_total > 0:
                        swd_count = len(school_students[school_students['Flag_SWD'] == 'Yes'])
                        atsi_count = len(school_students[school_students['Flag_ATSI'] == 'Yes'])
                        eald_count = len(school_students[school_students['Flag_EALD'] == 'Yes'])
                        
                        swd_rate = int(swd_count / school_total * 100)
                        atsi_rate = int(atsi_count / school_total * 100)
                        eald_rate = int(eald_count / school_total * 100)
                        
                        school_data.append({
                            'School': school,
                            'Total': school_total,
                            'SWD %': swd_rate,
                            'SWD vs Overall': f"{swd_rate - int(overall_swd_rate):+d}%",
                            'ATSI %': atsi_rate,
                            'ATSI vs Overall': f"{atsi_rate - int(overall_atsi_rate):+d}%",
                            'EALD %': eald_rate,
                            'EALD vs Overall': f"{eald_rate - int(overall_eald_rate):+d}%"
                        })
                
                if school_data:
                    school_df = pd.DataFrame(school_data).sort_values('Total', ascending=False).head(15)
                    
                    # Create variance columns for visualization
                    school_df['SWD_Variance'] = school_df['SWD %'] - int(overall_swd_rate)
                    school_df['ATSI_Variance'] = school_df['ATSI %'] - int(overall_atsi_rate)
                    school_df['EALD_Variance'] = school_df['EALD %'] - int(overall_eald_rate)
                    
                    st.markdown(f"**Overall Rates**: SWD {int(overall_swd_rate)}% | ATSI {int(overall_atsi_rate)}% | EALD {int(overall_eald_rate)}%")
                    
                    # Create three side-by-side diverging bar charts
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        st.markdown("### SWD Over-Representation")
                        swd_data = school_df.sort_values('SWD_Variance', ascending=True)
                        colors_swd = ['#ff6b6b' if x > 0 else '#00e5ff' for x in swd_data['SWD_Variance']]
                        fig = go.Figure([go.Bar(
                            y=swd_data['School'],
                            x=swd_data['SWD_Variance'],
                            orientation='h',
                            marker_color=colors_swd,
                            text=swd_data['SWD_Variance'].astype(int),
                            textposition='outside'
                        )])
                        fig.add_vline(x=0, line_dash="dash", line_color="#ffffff", opacity=0.3)
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, xaxis_title="Variance from Overall %")
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with c2:
                        st.markdown("### ATSI Over-Representation")
                        atsi_data = school_df.sort_values('ATSI_Variance', ascending=True)
                        colors_atsi = ['#ff6b6b' if x > 0 else '#00e5ff' for x in atsi_data['ATSI_Variance']]
                        fig = go.Figure([go.Bar(
                            y=atsi_data['School'],
                            x=atsi_data['ATSI_Variance'],
                            orientation='h',
                            marker_color=colors_atsi,
                            text=atsi_data['ATSI_Variance'].astype(int),
                            textposition='outside'
                        )])
                        fig.add_vline(x=0, line_dash="dash", line_color="#ffffff", opacity=0.3)
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, xaxis_title="Variance from Overall %")
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with c3:
                        st.markdown("### EALD Over-Representation")
                        eald_data = school_df.sort_values('EALD_Variance', ascending=True)
                        colors_eald = ['#ff6b6b' if x > 0 else '#00e5ff' for x in eald_data['EALD_Variance']]
                        fig = go.Figure([go.Bar(
                            y=eald_data['School'],
                            x=eald_data['EALD_Variance'],
                            orientation='h',
                            marker_color=colors_eald,
                            text=eald_data['EALD_Variance'].astype(int),
                            textposition='outside'
                        )])
                        fig.add_vline(x=0, line_dash="dash", line_color="#ffffff", opacity=0.3)
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=False)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False, xaxis_title="Variance from Overall %")
                        st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("## EALD Trend Analysis - Increase Over Time")
            st.markdown("*Shows if EALD students are increasing and particularly in SY program*")
            
            if 'Term' in filtered.columns:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("### EALD Students by Term (All Programs)")
                    eald_by_term = filtered[filtered['Flag_EALD'] == 'Yes'].groupby('Term').size().sort_index()
                    total_by_term = filtered.groupby('Term').size().sort_index()
                    
                    if len(eald_by_term) > 0:
                        eald_rates = []
                        term_labels = []
                        # Filter out NaN values from Term column
                        valid_terms = sorted([t for t in filtered['Term'].unique() if pd.notna(t)])
                        for term in valid_terms:
                            try:
                                term_data = filtered[filtered['Term'] == term]
                                # Get years for this term
                                years_for_term = sorted([int(y) for y in term_data['Referral_Year'].unique() if pd.notna(y)])
                                
                                for year in years_for_term:
                                    eald_count = len(filtered[(filtered['Term'] == term) & (filtered['Referral_Year'] == year) & (filtered['Flag_EALD'] == 'Yes')])
                                    term_count = len(filtered[(filtered['Term'] == term) & (filtered['Referral_Year'] == year)])
                                    rate = int(eald_count / term_count * 100) if term_count > 0 else 0
                                    eald_rates.append(rate)
                                    term_label = f"T{int(term)}-{int(year)}"
                                    term_labels.append(term_label)
                            except:
                                continue
                        
                        if term_labels and eald_rates:
                            fig = go.Figure([go.Scatter(x=term_labels, y=eald_rates, mode='lines+markers', marker=dict(size=12, color='#ffd93d'), line=dict(width=3, color='#ffd93d'))])
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="EALD Percentage Trend", height=350, yaxis_title="% EALD", margin=dict(l=60, r=60, t=60, b=80))
                            fig.update_yaxes(dtick=5, showgrid=False)
                            fig.update_xaxes(showgrid=False)
                            st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    st.markdown("### EALD Students in SY Program by Term")
                    sy_data = filtered[filtered['Allocated_Program'] == 'SY']
                    
                    if len(sy_data) > 0:
                        eald_sy_rates = []
                        term_labels_sy = []
                        # Filter out NaN values from Term column
                        valid_terms_sy = sorted([t for t in sy_data['Term'].unique() if pd.notna(t)])
                        for term in valid_terms_sy:
                            try:
                                term_data = sy_data[sy_data['Term'] == term]
                                # Get years for this term
                                years_for_term = sorted([int(y) for y in term_data['Referral_Year'].unique() if pd.notna(y)])
                                
                                for year in years_for_term:
                                    eald_count = len(sy_data[(sy_data['Term'] == term) & (sy_data['Referral_Year'] == year) & (sy_data['Flag_EALD'] == 'Yes')])
                                    term_count = len(sy_data[(sy_data['Term'] == term) & (sy_data['Referral_Year'] == year)])
                                    rate = int(eald_count / term_count * 100) if term_count > 0 else 0
                                    eald_sy_rates.append(rate)
                                    term_label = f"T{int(term)}-{int(year)}"
                                    term_labels_sy.append(term_label)
                            except:
                                continue
                        
                        if term_labels_sy and eald_sy_rates:
                            fig = go.Figure([go.Scatter(x=term_labels_sy, y=eald_sy_rates, mode='lines+markers', marker=dict(size=12, color='#ff6b6b'), line=dict(width=3, color='#ff6b6b'))])
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="SY Program: EALD Percentage Trend", height=350, yaxis_title="% EALD", margin=dict(l=60, r=60, t=60, b=80))
                            fig.update_yaxes(dtick=5, showgrid=False)
                            fig.update_xaxes(showgrid=False)
                            st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### EALD Allocation Status by Program")
                for prog in ['JP', 'PY', 'SY']:
                    prog_data = filtered[filtered['Allocated_Program'] == prog]
                    if len(prog_data) > 0:
                        eald_allocated = len(prog_data[(prog_data['Flag_EALD'] == 'Yes') & (prog_data['Allocation_Status'] == 'Allocated')])
                        eald_waiting = len(prog_data[(prog_data['Flag_EALD'] == 'Yes') & (prog_data['Allocation_Status'] == 'On Waiting List')])
                        eald_total = len(prog_data[prog_data['Flag_EALD'] == 'Yes'])
                        
                        if eald_total > 0:
                            alloc_rate = int(eald_allocated / eald_total * 100)
                            st.write(f"**{prog} Program**: {eald_total} EALD students → {eald_allocated} Allocated ({alloc_rate}%) | {eald_waiting} Waiting List")
            st.markdown("*Important: Students with 2+ identified disabilities are represented in multiple disability categories below - these are the SAME students, not duplicates*")
            
            disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
            
            # Count disabilities per student
            filtered_copy = filtered.copy()
            filtered_copy['disability_count'] = 0
            for col in disability_cols:
                if col in filtered_copy.columns:
                    filtered_copy['disability_count'] += (filtered_copy[col] == 'Yes').astype(int)
            
            # Distribution of students by number of disabilities
            disability_dist = filtered_copy['disability_count'].value_counts().sort_index()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("No Identified Disabilities", int(disability_dist.get(0, 0)))
            c2.metric("1 Disability", int(disability_dist.get(1, 0)))
            c3.metric("2 Disabilities", int(disability_dist.get(2, 0)))
            c4.metric("3+ Disabilities", int(sum(disability_dist.get(i, 0) for i in range(3, 10))))
            
            # Chart showing distribution
            dist_labels = ['None', '1 Disability', '2 Disabilities', '3+ Disabilities']
            dist_values = [
                int(disability_dist.get(0, 0)),
                int(disability_dist.get(1, 0)),
                int(disability_dist.get(2, 0)),
                int(sum(disability_dist.get(i, 0) for i in range(3, 10)))
            ]
            
            fig = go.Figure([go.Bar(
                x=dist_labels,
                y=dist_values,
                marker_color=['#10b981', '#ffd93d', '#ff6b6b', '#ff3333'],
                text=dist_values,
                textposition='outside'
            )])
            fig.update_yaxes(dtick=1, showgrid=False)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                height=350,
                showlegend=False,
                title="Distribution of Students by Number of Identified Disabilities"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show top disability combinations
            if sum(disability_dist.get(i, 0) for i in range(2, 10)) > 0:
                st.markdown("### Common Disability Combinations (Same Student, Multiple Categories)")
                
                multi_disability_students = filtered_copy[filtered_copy['disability_count'] >= 2]
                
                if len(multi_disability_students) > 0:
                    # Find common combinations
                    combinations = []
                    for _, student in multi_disability_students.iterrows():
                        student_disabilities = [col.replace('Flag_', '').replace('_', ' ') for col in disability_cols if col in student.index and student[col] == 'Yes']
                        if len(student_disabilities) >= 2:
                            combinations.append(', '.join(sorted(student_disabilities)))
                    
                    from collections import Counter
                    combo_counts = Counter(combinations)
                    top_combos = combo_counts.most_common(10)
                    
                    if top_combos:
                        combo_names = [combo[0][:50] for combo in top_combos]  # Truncate long names
                        combo_values = [combo[1] for combo in top_combos]
                        
                        fig = go.Figure([go.Bar(
                            y=combo_names,
                            x=combo_values,
                            orientation='h',
                            marker_color='#ff6b6b',
                            text=combo_values,
                            textposition='outside'
                        )])
                        fig.update_xaxes(dtick=1, showgrid=False)
                        fig.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=400,
                            showlegend=False,
                            title="Top Disability Combinations"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("## Adelaide Partnership Map")
            
            partnership_coords = {
                "Le Fevre Peninsula": {"color": "#E74C3C", "coords": [[-34.78, 138.48], [-34.78, 138.52], [-34.84, 138.52], [-34.85, 138.50], [-34.84, 138.48]]},
                "Western Adelaide Shores": {"color": "#1ABC9C", "coords": [[-34.85, 138.48], [-34.85, 138.52], [-34.88, 138.52], [-34.88, 138.48]]},
                "Inner West": {"color": "#3498DB", "coords": [[-34.90, 138.54], [-34.90, 138.58], [-34.94, 138.58], [-34.94, 138.54]]},
                "West Torrens": {"color": "#F39C12", "coords": [[-34.93, 138.55], [-34.93, 138.59], [-34.96, 138.59], [-34.96, 138.55]]},
                "Adelaide Prospect": {"color": "#34495E", "coords": [[-34.84, 138.58], [-34.84, 138.62], [-34.88, 138.62], [-34.88, 138.58]]},
                "Holdfast": {"color": "#E67E22", "coords": [[-35.00, 138.50], [-35.00, 138.55], [-35.05, 138.55], [-35.05, 138.50]]},
                "Marion Inland": {"color": "#16A085", "coords": [[-35.00, 138.54], [-35.00, 138.59], [-35.05, 138.59], [-35.05, 138.54]]},
            }
            
            partnership_counts = Counter()
            for _, record in filtered.iterrows():
                partnership = record.get('Partnership_Area', '')
                if partnership and partnership != '':
                    partnership_counts[partnership] += 1
            
            m = folium.Map(location=[-34.92, 138.60], zoom_start=10, tiles='OpenStreetMap')
            max_count = max(partnership_counts.values()) if partnership_counts else 1
            
            for partnership_name, region_data in partnership_coords.items():
                count = partnership_counts.get(partnership_name, 0)
                if count > 0:
                    opacity = 0.3 + (count / max_count) * 0.5
                    folium.Polygon(
                        locations=region_data["coords"],
                        color=region_data["color"],
                        fill=True,
                        fillColor=region_data["color"],
                        fillOpacity=opacity,
                        weight=3,
                        popup=folium.Popup(f"<b>{partnership_name}</b><br>{count} students", max_width=200),
                        tooltip=f"{partnership_name}: {count} students"
                    ).add_to(m)
            
            folium.Marker(
                location=[-34.9286, 138.5830],
                popup="CLC-LBU",
                icon=folium.Icon(color='green', icon='home', prefix='fa')
            ).add_to(m)
            
            st_folium(m, width=None, height=500)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

else:
    st.warning("Upload your Excel file in the sidebar to begin")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.9em;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
