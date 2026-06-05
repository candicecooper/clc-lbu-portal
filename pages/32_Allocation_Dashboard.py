import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CLC Allocation Dashboard", layout="wide")

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; color: #ffffff !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
h1, h2, h3 { color: #ffffff !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
</style>
""", unsafe_allow_html=True)

# Load data
df = pd.read_excel('/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_WithNames_1.xlsx')

# Transform data
df['ATSI'] = df['Flag_ATSI'].fillna('No').astype(str)
df['SWD'] = df['Flag_SWD'].fillna('No').astype(str)
df['EALD'] = df['Flag_EALD'].fillna('No').astype(str)
df['Allocated'] = (df['Allocation_Status'].notna()) & (df['Allocation_Status'] != '')
df['Term'] = df['Term'].fillna(4).astype(int)

# Sidebar
with st.sidebar:
    st.title("Filters")
    view = st.radio("View", ["Current", "ATSI", "SWD", "EALD", "Compare", "Trends"])
    
    terms = sorted(df['Term'].unique())
    selected_term = st.selectbox("Term", [None] + terms, format_func=lambda x: "All" if x is None else f"Term {x}")

# Filter data
if selected_term is None:
    data = df
    term_text = "All Terms"
else:
    data = df[df['Term'] == selected_term]
    term_text = f"Term {selected_term}"

# Main title
st.markdown(f"# CLC Allocation Dashboard")
st.markdown(f"**{term_text}** | {len(data)} referrals")
st.markdown("---")

# VIEW 1: CURRENT
if view == "Current":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", len(data))
    c2.metric("Allocated", f"{data['Allocated'].sum()}\n({data['Allocated'].sum()/len(data)*100:.0f}%)")
    c3.metric("ATSI %", f"{(data['ATSI']=='Yes').sum()}\n({(data['ATSI']=='Yes').sum()/len(data)*100:.1f}%)")
    c4.metric("SWD %", f"{(data['SWD']=='Yes').sum()}\n({(data['SWD']=='Yes').sum()/len(data)*100:.1f}%)")
    c5.metric("EALD %", f"{(data['EALD']=='Yes').sum()}\n({(data['EALD']=='Yes').sum()/len(data)*100:.1f}%)")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        allocated_counts = data['Allocation_Status'].value_counts()
        fig = go.Figure(data=[go.Bar(x=allocated_counts.index, y=allocated_counts.values, marker_color=['#00ff00', '#ffd93d'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Status", height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        atsi_yes = (data['ATSI']=='Yes').sum()
        atsi_no = (data['ATSI']=='No').sum()
        atsi_alloc_yes = data[data['ATSI']=='Yes']['Allocated'].sum()
        atsi_alloc_no = data[data['ATSI']=='No']['Allocated'].sum()
        
        fig = go.Figure(data=[
            go.Bar(x=['ATSI', 'Non-ATSI'], y=[atsi_alloc_yes, atsi_alloc_no], name='Allocated', marker_color='#00ff00'),
            go.Bar(x=['ATSI', 'Non-ATSI'], y=[atsi_yes - atsi_alloc_yes, atsi_no - atsi_alloc_no], name='Not Allocated', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI Allocations", barmode='stack', height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        swd_yes = (data['SWD']=='Yes').sum()
        swd_no = (data['SWD']=='No').sum()
        swd_alloc_yes = data[data['SWD']=='Yes']['Allocated'].sum()
        swd_alloc_no = data[data['SWD']=='No']['Allocated'].sum()
        
        fig = go.Figure(data=[
            go.Bar(x=['SWD', 'Non-SWD'], y=[swd_alloc_yes, swd_alloc_no], name='Allocated', marker_color='#00ff00'),
            go.Bar(x=['SWD', 'Non-SWD'], y=[swd_yes - swd_alloc_yes, swd_no - swd_alloc_no], name='Not Allocated', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="SWD Allocations", barmode='stack', height=300)
        st.plotly_chart(fig, use_container_width=True)

# VIEW 2: ATSI
elif view == "ATSI":
    atsi_yes = (data['ATSI']=='Yes').sum()
    atsi_no = (data['ATSI']=='No').sum()
    atsi_alloc_yes = data[data['ATSI']=='Yes']['Allocated'].sum()
    atsi_alloc_no = data[data['ATSI']=='No']['Allocated'].sum()
    atsi_rate = atsi_alloc_yes / atsi_yes * 100 if atsi_yes > 0 else 0
    non_atsi_rate = atsi_alloc_no / atsi_no * 100 if atsi_no > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ATSI Total", atsi_yes)
    c2.metric("ATSI Allocated", f"{atsi_alloc_yes} ({atsi_rate:.0f}%)")
    c3.metric("Non-ATSI Total", atsi_no)
    c4.metric("Non-ATSI Allocated", f"{atsi_alloc_no} ({non_atsi_rate:.0f}%)")
    
    st.markdown("---")
    st.write(f"**ATSI Allocation Rate: {atsi_rate:.1f}%**")
    st.write(f"**Non-ATSI Allocation Rate: {non_atsi_rate:.1f}%**")
    st.write(f"**Difference: {abs(atsi_rate - non_atsi_rate):.1f} percentage points**")

# VIEW 3: SWD
elif view == "SWD":
    swd_yes = (data['SWD']=='Yes').sum()
    swd_no = (data['SWD']=='No').sum()
    swd_alloc_yes = data[data['SWD']=='Yes']['Allocated'].sum()
    swd_alloc_no = data[data['SWD']=='No']['Allocated'].sum()
    swd_rate = swd_alloc_yes / swd_yes * 100 if swd_yes > 0 else 0
    non_swd_rate = swd_alloc_no / swd_no * 100 if swd_no > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SWD Total", swd_yes)
    c2.metric("SWD Allocated", f"{swd_alloc_yes} ({swd_rate:.0f}%)")
    c3.metric("Non-SWD Total", swd_no)
    c4.metric("Non-SWD Allocated", f"{swd_alloc_no} ({non_swd_rate:.0f}%)")
    
    st.markdown("---")
    st.write(f"**SWD Allocation Rate: {swd_rate:.1f}%**")
    st.write(f"**Non-SWD Allocation Rate: {non_swd_rate:.1f}%**")
    st.write(f"**Difference: {abs(swd_rate - non_swd_rate):.1f} percentage points**")

# VIEW 4: EALD
elif view == "EALD":
    eald_yes = (data['EALD']=='Yes').sum()
    eald_no = (data['EALD']=='No').sum()
    eald_alloc_yes = data[data['EALD']=='Yes']['Allocated'].sum()
    eald_alloc_no = data[data['EALD']=='No']['Allocated'].sum()
    eald_rate = eald_alloc_yes / eald_yes * 100 if eald_yes > 0 else 0
    non_eald_rate = eald_alloc_no / eald_no * 100 if eald_no > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EALD Total", eald_yes)
    c2.metric("EALD Allocated", f"{eald_alloc_yes} ({eald_rate:.0f}%)")
    c3.metric("Non-EALD Total", eald_no)
    c4.metric("Non-EALD Allocated", f"{eald_alloc_no} ({non_eald_rate:.0f}%)")
    
    st.markdown("---")
    st.write(f"**EALD Representation: {eald_yes/len(data)*100:.1f}%**")
    st.write(f"**Status: {'Rising need' if eald_yes > 8 else 'Emerging need'}**")

# VIEW 5: COMPARE
elif view == "Compare":
    col1, col2 = st.columns(2)
    
    with col1:
        groups = ['ATSI', 'SWD', 'EALD']
        pcts = [
            (data['ATSI']=='Yes').sum()/len(data)*100,
            (data['SWD']=='Yes').sum()/len(data)*100,
            (data['EALD']=='Yes').sum()/len(data)*100
        ]
        fig = go.Figure(data=[go.Bar(x=groups, y=pcts, marker_color=['#ff6b6b', '#ff6b6b', '#ffd93d'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Representation %", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        atsi_rate = data[data['ATSI']=='Yes']['Allocated'].sum() / (data['ATSI']=='Yes').sum() * 100 if (data['ATSI']=='Yes').sum() > 0 else 0
        swd_rate = data[data['SWD']=='Yes']['Allocated'].sum() / (data['SWD']=='Yes').sum() * 100 if (data['SWD']=='Yes').sum() > 0 else 0
        eald_rate = data[data['EALD']=='Yes']['Allocated'].sum() / (data['EALD']=='Yes').sum() * 100 if (data['EALD']=='Yes').sum() > 0 else 0
        
        rates = [atsi_rate, swd_rate, eald_rate]
        fig = go.Figure(data=[go.Bar(x=groups, y=rates, marker_color=['#ff6b6b', '#ff6b6b', '#ffd93d'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Rates %", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# VIEW 6: TRENDS
elif view == "Trends":
    by_term = df.groupby('Term').agg({
        'ATSI': lambda x: (x == 'Yes').sum(),
        'SWD': lambda x: (x == 'Yes').sum(),
        'EALD': lambda x: (x == 'Yes').sum(),
    }).reset_index()
    by_term['Total'] = df.groupby('Term').size().values
    by_term['ATSI_pct'] = by_term['ATSI'] / by_term['Total'] * 100
    by_term['SWD_pct'] = by_term['SWD'] / by_term['Total'] * 100
    by_term['EALD_pct'] = by_term['EALD'] / by_term['Total'] * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['ATSI_pct'], mode='lines+markers', name='ATSI', line=dict(color='#ff6b6b', width=3)))
    fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['SWD_pct'], mode='lines+markers', name='SWD', line=dict(color='#ff6b6b', width=3)))
    fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['EALD_pct'], mode='lines+markers', name='EALD', line=dict(color='#ffd93d', width=3)))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Trends by Term", height=400)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
