import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

if 'filters' not in st.session_state:
    st.session_state.filters = {
        'year': {'2025', '2026'},
        'program': {'JP', 'PY', 'SY'},
        'status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
        'atsi': {'Yes', 'No'},
        'eald': {'Yes', 'No'},
        'attendance': {'Full-time', 'Part-time', 'Irregular'},
        'swd': {'Yes', 'No'},
        'swd_type': {'Speech and Language', 'ASD', 'Intellectual', 'Learning Difficulty', 'Sensory Processing', 'ADHD', 'ODD', 'PDA'},
        'cat_support': {'1', '2', '3', '4', '5', '6', '7', '8', '9', '9+ RAAP'},
        'partnership': {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    }

if 'view' not in st.session_state:
    st.session_state.view = "Dashboard Overview"

def process_data(df):
    """Transform raw Excel data to dashboard format"""
    df_processed = df.copy()
    
    # Map allocation status
    df_processed['Status'] = 'Not Placed'
    df_processed.loc[df_processed['Allocation_Status'].notna() & (df_processed['Allocation_Status'] != ''), 'Status'] = 'Allocated'
    df_processed.loc[df_processed['Waitlist_Status'].notna() & (df_processed['Waitlist_Status'] != ''), 'Status'] = 'On Waitlist'
    
    # Map program
    df_processed['Program'] = df_processed['Allocated_Program'].fillna('Not Placed')
    
    # Map year
    df_processed['Year'] = '2026'
    
    # Map ATSI, EALD, SWD (1 = True, 0/NaN = False)
    df_processed['ATSI'] = df_processed['Flag_ATSI'].fillna(0).apply(lambda x: 'Yes' if x == 1 else 'No')
    df_processed['EALD'] = df_processed['Flag_EALD'].fillna(0).apply(lambda x: 'Yes' if x == 1 else 'No')
    df_processed['SWD'] = df_processed['Flag_SWD'].fillna(0).apply(lambda x: 'Yes' if x == 1 else 'No')
    
    # Map SWD Type
    def get_swd_type(row):
        swd_flags = {
            'Speech and Language': row.get('Flag_Speech_and_Lang', 0),
            'ASD': row.get('Flag_ASD', 0),
            'Intellectual': row.get('Flag_Intellectual', 0),
            'Learning Difficulty': row.get('Flag_Learning_Difficulty', 0),
            'Sensory Processing': row.get('Flag_Sensory_Processing', 0),
            'ADHD': row.get('Flag_ADHD', 0),
            'ODD': row.get('Flag_ODD', 0),
            'PDA': row.get('Flag_PDA', 0),
        }
        for swd_type, flag in swd_flags.items():
            if flag == 1:
                return swd_type
        return 'None'
    
    df_processed['SWD Type'] = df_processed.apply(get_swd_type, axis=1)
    
    # Map Category of Support
    def get_category(row):
        for i in range(1, 10):
            if row.get(f'Flag_Category_{i}', 0) == 1:
                return str(i)
        if row.get('Flag_9plusRAAP', 0) == 1:
            return '9+ RAAP'
        return 'Unknown'
    
    df_processed['Category of Support'] = df_processed.apply(get_category, axis=1)
    
    # Map Attendance
    def get_attendance(row):
        if row.get('Flag_Attendance_Fulltime', 0) == 1:
            return 'Full-time'
        elif row.get('Flag_Attendance_Parttime', 0) == 1:
            return 'Part-time'
        return 'Irregular'
    
    df_processed['Attendance'] = df_processed.apply(get_attendance, axis=1)
    
    # Map Partnership Area
    df_processed['Partnership'] = df_processed['Partnership_Area'].fillna('Unknown')
    
    return df_processed

# Load default file directly (NO CACHING)
all_data = None
default_file = '/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_WithNames_1.xlsx'

if os.path.exists(default_file):
    try:
        all_data = pd.read_excel(default_file)
        all_data = process_data(all_data)
    except Exception as e:
        st.error(f"Error loading default file: {e}")

# Apply filters
if all_data is not None and len(all_data) > 0:
    filter_conditions = pd.Series([True] * len(all_data), index=all_data.index)
    
    if 'Year' in all_data.columns:
        filter_conditions &= all_data['Year'].isin(st.session_state.filters['year'])
    if 'Program' in all_data.columns:
        filter_conditions &= all_data['Program'].isin(st.session_state.filters['program'])
    if 'Status' in all_data.columns:
        filter_conditions &= all_data['Status'].isin(st.session_state.filters['status'])
    if 'ATSI' in all_data.columns:
        filter_conditions &= all_data['ATSI'].isin(st.session_state.filters['atsi'])
    if 'EALD' in all_data.columns:
        filter_conditions &= all_data['EALD'].isin(st.session_state.filters['eald'])
    if 'Attendance' in all_data.columns:
        filter_conditions &= all_data['Attendance'].isin(st.session_state.filters['attendance'])
    if 'SWD' in all_data.columns:
        filter_conditions &= all_data['SWD'].isin(st.session_state.filters['swd'])
    if 'SWD Type' in all_data.columns:
        filter_conditions &= all_data['SWD Type'].isin(st.session_state.filters['swd_type'])
    if 'Category of Support' in all_data.columns:
        filter_conditions &= all_data['Category of Support'].isin(st.session_state.filters['cat_support'])
    if 'Partnership' in all_data.columns:
        filter_conditions &= all_data['Partnership'].isin(st.session_state.filters['partnership'])
    
    filtered = all_data[filter_conditions]
else:
    filtered = pd.DataFrame()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
.main { background-color: #0a0e27 !important; padding: 1rem !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2.2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; padding: 0.3rem 0.6rem !important; font-size: 0.75rem !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded = st.file_uploader("", type=['xlsx', 'xls', 'csv'])
    if uploaded is not None:
        try:
            new_data = pd.read_excel(uploaded) if uploaded.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded)
            all_data = process_data(new_data)
            filtered = all_data
            st.success(f"✓ Loaded {len(all_data)} records")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.markdown("---")
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Dashboard Overview", "All Students"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 QUICK FILTERS")
    
    st.markdown("**Year**")
    yc1, yc2 = st.columns(2)
    if yc1.button("All", key="y_all", use_container_width=True): st.session_state.filters['year'] = {'2025', '2026'}
    if yc2.button("Clear", key="y_clear", use_container_width=True): st.session_state.filters['year'] = set()
    y1, y2 = st.columns(2)
    if y1.button("2025", use_container_width=True, key="y1"): st.session_state.filters['year'] ^= {"2025"}
    if y2.button("2026", use_container_width=True, key="y2"): st.session_state.filters['year'] ^= {"2026"}
    
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All", key="p_all", use_container_width=True): st.session_state.filters['program'] = {'JP', 'PY', 'SY'}
    if pc2.button("Clear", key="p_clear", use_container_width=True): st.session_state.filters['program'] = set()
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", use_container_width=True, key="p1"): st.session_state.filters['program'] ^= {"JP"}
    if p2.button("PY", use_container_width=True, key="p2"): st.session_state.filters['program'] ^= {"PY"}
    if p3.button("SY", use_container_width=True, key="p3"): st.session_state.filters['program'] ^= {"SY"}
    
    st.markdown("**Status**")
    sc1, sc2 = st.columns(2)
    if sc1.button("All", key="s_all", use_container_width=True): st.session_state.filters['status'] = {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'}
    if sc2.button("Clear", key="s_clear", use_container_width=True): st.session_state.filters['status'] = set()
    s1, s2 = st.columns(2)
    if s1.button("Allocated", use_container_width=True, key="s1"): st.session_state.filters['status'] ^= {"Allocated"}
    if s2.button("Pending", use_container_width=True, key="s2"): st.session_state.filters['status'] ^= {"Pending"}
    s3, s4 = st.columns(2)
    if s3.button("Not Placed", use_container_width=True, key="s3"): st.session_state.filters['status'] ^= {"Not Placed"}
    if s4.button("Waitlist", use_container_width=True, key="s4"): st.session_state.filters['status'] ^= {"On Waitlist"}
    
    st.markdown("**ATSI**")
    ac1, ac2 = st.columns(2)
    if ac1.button("All", key="a_all", use_container_width=True): st.session_state.filters['atsi'] = {'Yes', 'No'}
    if ac2.button("Clear", key="a_clear", use_container_width=True): st.session_state.filters['atsi'] = set()
    a1, a2 = st.columns(2)
    if a1.button("Yes", use_container_width=True, key="a1"): st.session_state.filters['atsi'] ^= {"Yes"}
    if a2.button("No", use_container_width=True, key="a2"): st.session_state.filters['atsi'] ^= {"No"}
    
    st.markdown("**EALD**")
    ec1, ec2 = st.columns(2)
    if ec1.button("All", key="e_all", use_container_width=True): st.session_state.filters['eald'] = {'Yes', 'No'}
    if ec2.button("Clear", key="e_clear", use_container_width=True): st.session_state.filters['eald'] = set()
    e1, e2 = st.columns(2)
    if e1.button("Yes", use_container_width=True, key="e1"): st.session_state.filters['eald'] ^= {"Yes"}
    if e2.button("No", use_container_width=True, key="e2"): st.session_state.filters['eald'] ^= {"No"}
    
    st.markdown("**SWD**")
    swdc1, swdc2 = st.columns(2)
    if swdc1.button("All", key="swd_all", use_container_width=True): st.session_state.filters['swd'] = {'Yes', 'No'}
    if swdc2.button("Clear", key="swd_clear", use_container_width=True): st.session_state.filters['swd'] = set()
    swd1, swd2 = st.columns(2)
    if swd1.button("Yes", use_container_width=True, key="swd1"): st.session_state.filters['swd'] ^= {"Yes"}
    if swd2.button("No", use_container_width=True, key="swd2"): st.session_state.filters['swd'] ^= {"No"}
    
    st.markdown("**SWD Type**")
    swdtc1, swdtc2 = st.columns(2)
    if swdtc1.button("All", key="swdt_all", use_container_width=True): st.session_state.filters['swd_type'] = {'Speech and Language', 'ASD', 'Intellectual', 'Learning Difficulty', 'Sensory Processing', 'ADHD', 'ODD', 'PDA'}
    if swdtc2.button("Clear", key="swdt_clear", use_container_width=True): st.session_state.filters['swd_type'] = set()
    swdt1, swdt2 = st.columns(2)
    if swdt1.button("Speech & Lang", use_container_width=True, key="swdt1"): st.session_state.filters['swd_type'] ^= {"Speech and Language"}
    if swdt2.button("ASD", use_container_width=True, key="swdt2"): st.session_state.filters['swd_type'] ^= {"ASD"}
    swdt3, swdt4 = st.columns(2)
    if swdt3.button("Intellectual", use_container_width=True, key="swdt3"): st.session_state.filters['swd_type'] ^= {"Intellectual"}
    if swdt4.button("Learning Diff", use_container_width=True, key="swdt4"): st.session_state.filters['swd_type'] ^= {"Learning Difficulty"}
    swdt5, swdt6 = st.columns(2)
    if swdt5.button("Sensory Proc", use_container_width=True, key="swdt5"): st.session_state.filters['swd_type'] ^= {"Sensory Processing"}
    if swdt6.button("ADHD", use_container_width=True, key="swdt6"): st.session_state.filters['swd_type'] ^= {"ADHD"}
    swdt7, swdt8 = st.columns(2)
    if swdt7.button("ODD", use_container_width=True, key="swdt7"): st.session_state.filters['swd_type'] ^= {"ODD"}
    if swdt8.button("PDA", use_container_width=True, key="swdt8"): st.session_state.filters['swd_type'] ^= {"PDA"}
    
    st.markdown("**Attendance**")
    attc1, attc2 = st.columns(2)
    if attc1.button("All", key="att_all", use_container_width=True): st.session_state.filters['attendance'] = {'Full-time', 'Part-time', 'Irregular'}
    if attc2.button("Clear", key="att_clear", use_container_width=True): st.session_state.filters['attendance'] = set()
    att1, att2, att3 = st.columns(3)
    if att1.button("Full-time", use_container_width=True, key="att1"): st.session_state.filters['attendance'] ^= {"Full-time"}
    if att2.button("Part-time", use_container_width=True, key="att2"): st.session_state.filters['attendance'] ^= {"Part-time"}
    if att3.button("Irregular", use_container_width=True, key="att3"): st.session_state.filters['attendance'] ^= {"Irregular"}
    
    st.markdown("**Category of Support**")
    catc1, catc2 = st.columns(2)
    if catc1.button("All", key="cat_all", use_container_width=True): st.session_state.filters['cat_support'] = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '9+ RAAP'}
    if catc2.button("Clear", key="cat_clear", use_container_width=True): st.session_state.filters['cat_support'] = set()
    cat1, cat2, cat3 = st.columns(3)
    if cat1.button("1", use_container_width=True, key="cat1"): st.session_state.filters['cat_support'] ^= {"1"}
    if cat2.button("2", use_container_width=True, key="cat2"): st.session_state.filters['cat_support'] ^= {"2"}
    if cat3.button("3", use_container_width=True, key="cat3"): st.session_state.filters['cat_support'] ^= {"3"}
    cat4, cat5, cat6 = st.columns(3)
    if cat4.button("4", use_container_width=True, key="cat4"): st.session_state.filters['cat_support'] ^= {"4"}
    if cat5.button("5", use_container_width=True, key="cat5"): st.session_state.filters['cat_support'] ^= {"5"}
    if cat6.button("6", use_container_width=True, key="cat6"): st.session_state.filters['cat_support'] ^= {"6"}
    cat7, cat8, cat9 = st.columns(3)
    if cat7.button("7", use_container_width=True, key="cat7"): st.session_state.filters['cat_support'] ^= {"7"}
    if cat8.button("8", use_container_width=True, key="cat8"): st.session_state.filters['cat_support'] ^= {"8"}
    if cat9.button("9", use_container_width=True, key="cat9"): st.session_state.filters['cat_support'] ^= {"9"}
    cat10 = st.columns(1)
    if cat10[0].button("9+ RAAP", use_container_width=True, key="cat10"): st.session_state.filters['cat_support'] ^= {"9+ RAAP"}

st.markdown("## Allocation Dashboard")

if len(filtered) > 0:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total", len(filtered))
    c2.metric("Allocated", len(filtered[filtered['Status']=='Allocated']))
    c3.metric("Pending", len(filtered[filtered['Status']=='Pending']))
    c4.metric("ATSI", len(filtered[filtered['ATSI']=='Yes']))
    c5.metric("SWD", len(filtered[filtered['SWD']=='Yes']))
    c6.metric("EALD", len(filtered[filtered['EALD']=='Yes']))

    st.markdown("---")

    if st.session_state.view == "Dashboard Overview":
        c1, c2, c3 = st.columns(3)
        with c1:
            prog = filtered['Program'].value_counts()
            fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Program", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            stat = filtered['Status'].value_counts()
            fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Status", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        with c3:
            sup = filtered['Category of Support'].value_counts().sort_index()
            fig = go.Figure([go.Pie(labels=sup.index, values=sup.values)])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            sup_prog = pd.crosstab(filtered['Program'], filtered['Category of Support']).fillna(0)
            colors = ['#10b981', '#00e5ff', '#ffd93d', '#ff6b6b', '#ff00ff', '#00ffff', '#ffff00', '#ff8800', '#ff0088', '#00ff88']
            fig = go.Figure([go.Bar(x=sup_prog.index, y=sup_prog.get(col, 0), name=str(col), marker_color=colors[i%10]) for i, col in enumerate(sorted(sup_prog.columns))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by Program", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            sup_swd = pd.crosstab(filtered['SWD Type'], filtered['Category of Support']).fillna(0)
            fig = go.Figure([go.Bar(x=sup_swd.index, y=sup_swd.get(col, 0), name=str(col), marker_color=colors[i%10]) for i, col in enumerate(sorted(sup_swd.columns))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by SWD Type", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)

    elif st.session_state.view == "All Students":
        cols_to_show = [c for c in ['Student_Name', 'Program', 'Status', 'ATSI', 'SWD', 'SWD Type', 'Category of Support', 'Partnership'] if c in filtered.columns]
        st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True, height=400)
else:
    st.error("❌ No data loaded. File may not exist or be unreadable.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.85rem;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
