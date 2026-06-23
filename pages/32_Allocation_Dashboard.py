# ====================================================================
# COMPLETE DRILL-DOWN ANALYSIS - ATSI, SWD, AND ASD
# Insert this entire file after EALD Enrollment Trends section
# Before "Multiple Disabilities" section in 32_Allocation_Dashboard.py
# ====================================================================

# ====================================================================
# 🔴 ATSI ENROLLMENT TRENDS BY PROGRAM & TERM
# ====================================================================

st.markdown("---")
st.markdown("## 🔴 ATSI Enrollment Trends by Program & Term")

def analyze_atsi_trends(df):
    """Analyze ATSI enrollment trends by term and program"""
    if 'Flag_ATSI' not in df.columns or 'Term' not in df.columns or 'Allocated_Program' not in df.columns:
        return None
    atsi_data = df[df['Flag_ATSI'] == 'Yes'].copy()
    if atsi_data.empty:
        return None
    atsi_data['Term'] = pd.to_numeric(atsi_data['Term'], errors='coerce')
    atsi_data = atsi_data.dropna(subset=['Term'])
    programs = sorted([p for p in atsi_data['Allocated_Program'].unique() if pd.notna(p)])
    if not programs:
        return None
    trend_data = {}
    for program in programs:
        prog_data = atsi_data[atsi_data['Allocated_Program'] == program]
        term_counts = prog_data.groupby('Term').size().sort_index()
        trend_data[program] = term_counts
    return trend_data, programs, atsi_data

if 'Flag_ATSI' in filtered.columns:
    trend_results = analyze_atsi_trends(filtered)
    if trend_results and filtered[filtered['Flag_ATSI'] == 'Yes'].shape[0] > 0:
        trend_data, programs, atsi_students = trend_results
        
        # LINE CHART
        fig_atsi = go.Figure()
        colors = ['#00e5ff', '#00ff00', '#ff6b6b', '#ffd93d']
        for idx, program in enumerate(programs):
            if program in trend_data:
                term_counts = trend_data[program]
                fig_atsi.add_trace(go.Scatter(
                    x=term_counts.index.astype(int),
                    y=term_counts.values,
                    mode='lines+markers',
                    name=f'{program} Program',
                    line=dict(color=colors[idx % len(colors)], width=3),
                    marker=dict(size=10),
                    hovertemplate='<b>%{fullData.name}</b><br>Term: %{x}<br>Students: %{y}<extra></extra>'
                ))
        
        fig_atsi.update_layout(
            title='ATSI Student Enrollment Trends',
            xaxis_title='Term',
            yaxis_title='Number of ATSI Students',
            hovermode='x unified',
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
            yaxis=dict(showgrid=False),
            legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01, bgcolor='rgba(0,0,0,0.5)', bordercolor='#00e5ff', borderwidth=1)
        )
        st.plotly_chart(fig_atsi, use_container_width=True)
        
        # METRICS
        st.markdown("### 📊 Current Enrollments by Program")
        cols = st.columns(min(3, len(programs)))
        for idx, program in enumerate(programs):
            if program in trend_data:
                term_counts = trend_data[program]
                current_term = term_counts.index.max()
                current_count = term_counts.iloc[-1]
                if len(term_counts) > 1:
                    previous_count = term_counts.iloc[-2]
                    change = current_count - previous_count
                    change_pct = (change / previous_count * 100) if previous_count > 0 else 0
                else:
                    change = 0
                    change_pct = 0
                total_atsi = len(atsi_students[atsi_students['Allocated_Program'] == program])
                with cols[idx % 3]:
                    st.metric(f"{program} Program", f"{current_count}", delta=f"{change:+d} ({change_pct:+.0f}%)", delta_color="off")
                    st.caption(f"Term {int(current_term)} | Total: {total_atsi}")
        
        # DATA TABLE
        st.markdown("### 📋 Detailed Breakdown")
        detail_data = []
        for program in programs:
            if program in trend_data:
                term_counts = trend_data[program]
                for term, count in term_counts.items():
                    detail_data.append({'Program': program, 'Term': int(term), 'ATSI Students': count})
        if detail_data:
            detail_df = pd.DataFrame(detail_data).sort_values(['Program', 'Term'])
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
            
            st.markdown("### 📌 Key Insights")
            col1, col2, col3, col4 = st.columns(4)
            total_atsi = len(atsi_students)
            allocated_atsi = len(atsi_students[atsi_students['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in atsi_students.columns else 0
            waiting_atsi = len(atsi_students[atsi_students['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in atsi_students.columns else 0
            allocation_rate = (allocated_atsi / total_atsi * 100) if total_atsi > 0 else 0
            
            with col1:
                st.info(f"**Total ATSI**\n{total_atsi}")
            with col2:
                st.success(f"**Allocated**\n{allocated_atsi}")
            with col3:
                st.warning(f"**Waiting**\n{waiting_atsi}")
            with col4:
                st.metric("Allocation %", f"{allocation_rate:.0f}%")

# ====================================================================
# 🟠 SWD ENROLLMENT TRENDS BY PROGRAM & TERM
# ====================================================================

st.markdown("---")
st.markdown("## 🟠 SWD Enrollment Trends by Program & Term")

def analyze_swd_trends(df):
    """Analyze SWD enrollment trends by term and program"""
    if 'Flag_SWD' not in df.columns or 'Term' not in df.columns or 'Allocated_Program' not in df.columns:
        return None
    swd_data = df[df['Flag_SWD'] == 'Yes'].copy()
    if swd_data.empty:
        return None
    swd_data['Term'] = pd.to_numeric(swd_data['Term'], errors='coerce')
    swd_data = swd_data.dropna(subset=['Term'])
    programs = sorted([p for p in swd_data['Allocated_Program'].unique() if pd.notna(p)])
    if not programs:
        return None
    trend_data = {}
    for program in programs:
        prog_data = swd_data[swd_data['Allocated_Program'] == program]
        term_counts = prog_data.groupby('Term').size().sort_index()
        trend_data[program] = term_counts
    return trend_data, programs, swd_data

if 'Flag_SWD' in filtered.columns:
    trend_results = analyze_swd_trends(filtered)
    if trend_results and filtered[filtered['Flag_SWD'] == 'Yes'].shape[0] > 0:
        trend_data, programs, swd_students = trend_results
        
        # LINE CHART
        fig_swd = go.Figure()
        colors = ['#00e5ff', '#00ff00', '#ff6b6b', '#ffd93d']
        for idx, program in enumerate(programs):
            if program in trend_data:
                term_counts = trend_data[program]
                fig_swd.add_trace(go.Scatter(
                    x=term_counts.index.astype(int),
                    y=term_counts.values,
                    mode='lines+markers',
                    name=f'{program} Program',
                    line=dict(color=colors[idx % len(colors)], width=3),
                    marker=dict(size=10),
                    hovertemplate='<b>%{fullData.name}</b><br>Term: %{x}<br>Students: %{y}<extra></extra>'
                ))
        
        fig_swd.update_layout(
            title='SWD Student Enrollment Trends',
            xaxis_title='Term',
            yaxis_title='Number of SWD Students',
            hovermode='x unified',
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
            yaxis=dict(showgrid=False),
            legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01, bgcolor='rgba(0,0,0,0.5)', bordercolor='#00e5ff', borderwidth=1)
        )
        st.plotly_chart(fig_swd, use_container_width=True)
        
        # METRICS
        st.markdown("### 📊 Current Enrollments by Program")
        cols = st.columns(min(3, len(programs)))
        for idx, program in enumerate(programs):
            if program in trend_data:
                term_counts = trend_data[program]
                current_term = term_counts.index.max()
                current_count = term_counts.iloc[-1]
                if len(term_counts) > 1:
                    previous_count = term_counts.iloc[-2]
                    change = current_count - previous_count
                    change_pct = (change / previous_count * 100) if previous_count > 0 else 0
                else:
                    change = 0
                    change_pct = 0
                total_swd = len(swd_students[swd_students['Allocated_Program'] == program])
                with cols[idx % 3]:
                    st.metric(f"{program} Program", f"{current_count}", delta=f"{change:+d} ({change_pct:+.0f}%)", delta_color="off")
                    st.caption(f"Term {int(current_term)} | Total: {total_swd}")
        
        # DATA TABLE
        st.markdown("### 📋 Detailed Breakdown")
        detail_data = []
        for program in programs:
            if program in trend_data:
                term_counts = trend_data[program]
                for term, count in term_counts.items():
                    detail_data.append({'Program': program, 'Term': int(term), 'SWD Students': count})
        if detail_data:
            detail_df = pd.DataFrame(detail_data).sort_values(['Program', 'Term'])
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
            
            st.markdown("### 📌 Key Insights")
            col1, col2, col3, col4 = st.columns(4)
            total_swd = len(swd_students)
            allocated_swd = len(swd_students[swd_students['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in swd_students.columns else 0
            waiting_swd = len(swd_students[swd_students['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in swd_students.columns else 0
            allocation_rate = (allocated_swd / total_swd * 100) if total_swd > 0 else 0
            
            with col1:
                st.info(f"**Total SWD**\n{total_swd}")
            with col2:
                st.success(f"**Allocated**\n{allocated_swd}")
            with col3:
                st.warning(f"**Waiting**\n{waiting_swd}")
            with col4:
                st.metric("Allocation %", f"{allocation_rate:.0f}%")

# ====================================================================
# 🧠 ASD OVERREPRESENTATION - DEEP ANALYSIS
# ====================================================================

st.markdown("---")
st.markdown("## 🧠 ASD Overrepresentation Analysis")

if 'Flag_ASD' in filtered.columns:
    total_students = len(filtered)
    asd_count = len(filtered[filtered['Flag_ASD'] == 'Yes'])
    asd_percentage = (asd_count / total_students * 100) if total_students > 0 else 0
    
    st.markdown(f"### Overall ASD Representation: **{asd_percentage:.1f}%** ({asd_count}/{total_students} students)")
    
    # LARGE HEADLINE IF ASD > 90%
    if asd_percentage >= 90:
        st.error(f"⚠️ **CRITICAL OVERREPRESENTATION**: {asd_percentage:.1f}% of all CLC referrals are identified with ASD")
    elif asd_percentage >= 80:
        st.warning(f"⚠️ **SIGNIFICANT OVERREPRESENTATION**: {asd_percentage:.1f}% of all CLC referrals are identified with ASD")
    else:
        st.info(f"📊 ASD Representation: {asd_percentage:.1f}%")
    
    # ASD vs ALL OTHER DIAGNOSES
    st.markdown("### ASD vs All Other Students")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart: ASD vs Non-ASD
        asd_vs_other = pd.Series({'ASD': asd_count, 'Non-ASD': total_students - asd_count})
        fig_pie = go.Figure(data=[go.Pie(
            labels=asd_vs_other.index,
            values=asd_vs_other.values,
            marker=dict(colors=['#ff6b6b', '#00e5ff'])
        )])
        fig_pie.update_layout(
            title='ASD vs Non-ASD Distribution',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # ASD breakdown by program
        st.markdown("### ASD Distribution by Program")
        prog_data = []
        for prog in ['JP', 'PY', 'SY']:
            prog_students = filtered[filtered['Allocated_Program'] == prog] if 'Allocated_Program' in filtered.columns else pd.DataFrame()
            if len(prog_students) > 0:
                prog_asd = len(prog_students[prog_students['Flag_ASD'] == 'Yes'])
                prog_total = len(prog_students)
                prog_pct = (prog_asd / prog_total * 100) if prog_total > 0 else 0
                prog_data.append({'Program': prog, 'ASD': prog_asd, 'Total': prog_total, 'ASD %': prog_pct})
        
        if prog_data:
            prog_df = pd.DataFrame(prog_data)
            fig_prog = go.Figure(data=[
                go.Bar(x=prog_df['Program'], y=prog_df['ASD'], name='ASD', marker_color='#ff6b6b'),
                go.Bar(x=prog_df['Program'], y=prog_df['Total'] - prog_df['ASD'], name='Non-ASD', marker_color='#00e5ff')
            ])
            fig_prog.update_layout(
                title='ASD by Program',
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                height=400,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_prog, use_container_width=True)
    
    # ASD TRENDS BY TERM
    st.markdown("### ASD Enrollment Trends by Term")
    
    asd_filtered = filtered[filtered['Flag_ASD'] == 'Yes'].copy()
    if 'Term' in asd_filtered.columns:
        asd_filtered['Term'] = pd.to_numeric(asd_filtered['Term'], errors='coerce')
        asd_filtered = asd_filtered.dropna(subset=['Term'])
        
        term_asd = asd_filtered.groupby('Term').size()
        term_total = filtered.groupby('Term').size() if 'Term' in filtered.columns else pd.Series()
        
        if len(term_asd) > 0 and len(term_total) > 0:
            term_pct = (term_asd / term_total * 100).reindex(term_asd.index, fill_value=0)
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=term_asd.index.astype(int),
                y=term_pct.values,
                mode='lines+markers',
                name='ASD %',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=10),
                fill='tozeroy',
                hovertemplate='Term: %{x}<br>ASD %: %{y:.1f}%<extra></extra>'
            ))
            fig_trend.update_layout(
                title='ASD Percentage Over Terms',
                xaxis_title='Term',
                yaxis_title='Percentage of Referrals (%)',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                height=400,
                xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    
    # ASD WITH OTHER DISABILITIES (COMORBIDITIES)
    st.markdown("### ASD Comorbidity Analysis")
    st.markdown("*Students with ASD who ALSO have other identified disabilities*")
    
    disability_cols = ['Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
    
    asd_with_other = {}
    for col in disability_cols:
        if col in asd_filtered.columns:
            count = len(asd_filtered[asd_filtered[col] == 'Yes'])
            pct = (count / asd_count * 100) if asd_count > 0 else 0
            disability_name = col.replace('Flag_', '').replace('_', ' ')
            asd_with_other[disability_name] = {'Count': count, 'Percentage': pct}
    
    if asd_with_other:
        comorbid_df = pd.DataFrame(asd_with_other).T.sort_values('Percentage', ascending=True)
        
        fig_comorbid = go.Figure(data=[go.Bar(
            y=comorbid_df.index,
            x=comorbid_df['Percentage'],
            orientation='h',
            marker_color='#ffd93d',
            text=[f"{int(comorbid_df.loc[idx, 'Count'])}" for idx in comorbid_df.index],
            textposition='outside'
        )])
        fig_comorbid.update_layout(
            title='Additional Disabilities in ASD Students',
            xaxis_title='Percentage of ASD Students (%)',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            height=400,
            margin=dict(l=200, r=80, t=40, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_comorbid, use_container_width=True)
        
        st.dataframe(comorbid_df, use_container_width=True)
    
    # ASD KEY STATISTICS
    st.markdown("### 📌 ASD Key Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    asd_allocated = len(asd_filtered[asd_filtered['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in asd_filtered.columns else 0
    asd_waiting = len(asd_filtered[asd_filtered['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in asd_filtered.columns else 0
    asd_allocation_rate = (asd_allocated / asd_count * 100) if asd_count > 0 else 0
    
    with col1:
        st.metric("Total ASD", asd_count)
    with col2:
        st.metric("Allocated", asd_allocated)
    with col3:
        st.metric("Waiting", asd_waiting)
    with col4:
        st.metric("Allocation %", f"{asd_allocation_rate:.0f}%")
    
    # ASD INSIGHTS
    st.markdown("### 🔍 Critical Findings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"📊 **Overall ASD Rate**: {asd_percentage:.1f}% of all referrals\n\n**Finding**: This represents significant overrepresentation compared to typical ASD prevalence rates (1-2% in general population)")
    
    with col2:
        non_asd_with_multi = len(filtered[(filtered['Flag_ASD'] != 'Yes')])
        if non_asd_with_multi > 0:
            st.warning(f"⚠️ **Only {non_asd_with_multi} non-ASD students** ({100-asd_percentage:.1f}% of referrals)\n\n**Question**: Are other conditions being underidentified or are they less likely to be referred to CLC?")

# ====================================================================
# END OF ATSI, SWD, ASD ANALYSIS
# Everything below this point should be your existing code
# (Multiple Disabilities section, etc.)
# ====================================================================
