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
    st.session_state.terms_selected = {2.0}
if 'years_selected' not in st.session_state:
    st.session_state.years_selected = set()
if 'programs_selected' not in st.session_state:
    st.session_state.programs_selected = set()
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
    st.markdown("### FILTERS")
    
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
        
        st.markdown("## Metrics & Drill Down")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
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
        
        st.markdown("---")
        
        # DRILL DOWN VIEWS
        if st.session_state.drill_down_view:
            st.markdown(f"## Detailed Analysis: {st.session_state.drill_down_view.upper()}")
            
            if st.button("Back to Overview", key="back_btn"):
                st.session_state.drill_down_view = None
                st.rerun()
            
            tabs = st.tabs(["Overview", "By Program", "By Partnership", "Disability Profile", "Trends"])
            
            if st.session_state.drill_down_view == "atsi":
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ff6b6b', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[4]:
                    if 'Term' in drill_data.columns:
                        term_trend = drill_data['Term'].value_counts().sort_index()
                        fig = go.Figure([go.Scatter(x=term_trend.index, y=term_trend.values, mode='lines+markers', marker_color='#ff6b6b', line=dict(width=3), marker_size=10)])
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, xaxis_title='Term', yaxis_title='Students')
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#00e5ff', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[2]:
                    part = drill_data['Partnership_Area'].value_counts()
                    if len(part) > 0:
                        fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ffd93d', text=part.values.astype(int), textposition='outside')])
                        fig.update_xaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tabs[3]:
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
                        fig.update_yaxes(dtick=1)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
        
        else:
            # MAIN OVERVIEW
            st.markdown("## Program Distribution")
            prog = filtered['Allocated_Program'].value_counts().sort_index()
            if len(prog) > 0:
                fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color=['#00e5ff', '#ffd93d', '#ff6b6b'][:len(prog)], text=prog.values.astype(int), textposition='outside')])
                fig.update_yaxes(dtick=1)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("## Students with Multiple Disabilities")
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
            fig.update_yaxes(dtick=1)
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
                        fig.update_xaxes(dtick=1)
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
