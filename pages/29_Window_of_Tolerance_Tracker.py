import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from supabase import create_client
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(page_title="Window of Tolerance Tracker", layout="wide")

# Supabase connection
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )

supabase = init_supabase()

# CSS for the three zones with proper colors
st.markdown("""
<style>
    .zone-card {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid;
    }
    .mobilisation {
        background-color: #ffe6e6;
        border-color: #cc0000;
    }
    .window {
        background-color: #e6f5e6;
        border-color: #008000;
    }
    .immobilisation {
        background-color: #e6e6ff;
        border-color: #0000cc;
    }
    .zone-title {
        font-weight: bold;
        font-size: 1.3em;
        margin-bottom: 10px;
    }
    .zone-subtitle {
        font-weight: bold;
        font-size: 1.1em;
        margin: 8px 0;
    }
    .zone-desc {
        font-size: 0.95em;
        font-style: italic;
        color: #666;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_students():
    """Get all students from database"""
    try:
        response = supabase.table("students").select("*").order("first_name").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return []

def get_observations(student_id=None, days=30):
    """Get WoT observations"""
    try:
        query = supabase.table("wot_observations").select("*")
        
        if student_id:
            query = query.eq("student_id", student_id)
        
        # Filter by date range
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        query = query.gte("observation_date", start_date)
        
        response = query.order("observation_date", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading observations: {e}")
        return []

def save_observation(data):
    """Save new observation"""
    try:
        response = supabase.table("wot_observations").insert(data).execute()
        return response.data
    except Exception as e:
        st.error(f"Error saving observation: {e}")
        return None

def delete_observation(obs_id):
    """Delete an observation"""
    try:
        response = supabase.table("wot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting observation: {e}")
        return False

# Main app
st.title("🎯 Window of Tolerance Tracker")
st.markdown("Track and analyze student arousal states and regulation patterns")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 New Observation", "📊 Student Dashboard", "📈 Analytics", "ℹ️ Reference"])

# TAB 1: New Observation
with tab1:
    st.header("Record Observation")
    
    # Get students
    students = get_students()
    if not students:
        st.warning("No students found. Please add students first.")
    else:
        student_options = {f"{s['first_name']} {s['last_name']}": s['id'] for s in students}
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_student_name = st.selectbox(
                "Student",
                options=list(student_options.keys()),
                key="obs_student"
            )
            selected_student_id = student_options[selected_student_name]
        
        with col2:
            obs_date = st.date_input("Date", value=date.today(), key="obs_date")
            obs_time = st.time_input("Time", key="obs_time")
        
        st.markdown("---")
        
        # Arousal state selection with visual cards
        st.subheader("Arousal State Observed")
        
        arousal_col1, arousal_col2, arousal_col3 = st.columns(3)
        
        with arousal_col1:
            if st.button("🔴 MOBILISATION", key="btn_mob", use_container_width=True):
                st.session_state.arousal_state = "mobilisation"
            st.markdown("""
            <div class="zone-card mobilisation">
                <div class="zone-title" style="color: #cc0000;">MOBILISATION</div>
                <div class="zone-subtitle">Hyper-arousal</div>
                <div class="zone-desc">
                    • Fight/Flight/Freeze<br>
                    • Too much arousal<br>
                    • Reduced capacity to learn
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with arousal_col2:
            if st.button("🟢 WINDOW OF TOLERANCE", key="btn_window", use_container_width=True):
                st.session_state.arousal_state = "window"
            st.markdown("""
            <div class="zone-card window">
                <div class="zone-title" style="color: #008000;">WINDOW OF TOLERANCE</div>
                <div class="zone-subtitle">Optimal arousal</div>
                <div class="zone-desc">
                    • Student feels safe<br>
                    • Ready to learn<br>
                    • Can interact with others
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with arousal_col3:
            if st.button("🔵 IMMOBILISATION", key="btn_immob", use_container_width=True):
                st.session_state.arousal_state = "immobilisation"
            st.markdown("""
            <div class="zone-card immobilisation">
                <div class="zone-title" style="color: #0000cc;">IMMOBILISATION</div>
                <div class="zone-subtitle">Hypo-arousal</div>
                <div class="zone-desc">
                    • Submission/Collapse/Shutdown<br>
                    • Too little arousal<br>
                    • Reduced capacity to learn
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if 'arousal_state' not in st.session_state:
            st.session_state.arousal_state = None
        
        if st.session_state.arousal_state:
            st.success(f"Selected: **{st.session_state.arousal_state.upper()}**")
        
        st.markdown("---")
        
        # Context and details
        col1, col2 = st.columns(2)
        
        with col1:
            context = st.text_area(
                "Context (What was happening?)",
                placeholder="e.g., Literacy lesson, transition to recess, peer conflict...",
                height=100,
                key="context"
            )
            
            triggers = st.text_area(
                "Observed Triggers",
                placeholder="e.g., Peer provocation, noise level, task demand...",
                height=100,
                key="triggers"
            )
        
        with col2:
            duration = st.number_input(
                "Duration (minutes)",
                min_value=1,
                max_value=300,
                value=5,
                key="duration"
            )
            
            interventions = st.text_area(
                "Interventions Used",
                placeholder="e.g., Movement break, sensory tool, 1:1 check-in...",
                height=100,
                key="interventions"
            )
        
        effectiveness = st.radio(
            "Intervention Effectiveness",
            options=["Not applicable", "Helped regulate", "Neutral/No change", "Escalated"],
            horizontal=True,
            key="effectiveness"
        )
        
        notes = st.text_area(
            "Additional Notes",
            placeholder="Any other relevant observations...",
            height=80,
            key="notes"
        )
        
        staff_name = st.text_input("Observer Name", value="", key="staff_name")
        
        st.markdown("---")
        
        # Save button
        if st.button("💾 Save Observation", type="primary", use_container_width=True):
            if not st.session_state.arousal_state:
                st.error("Please select an arousal state")
            elif not staff_name:
                st.error("Please enter observer name")
            else:
                obs_data = {
                    "student_id": selected_student_id,
                    "observation_date": obs_date.isoformat(),
                    "observation_time": obs_time.isoformat(),
                    "arousal_state": st.session_state.arousal_state,
                    "context": context,
                    "triggers": triggers,
                    "duration_minutes": duration,
                    "interventions_used": interventions,
                    "effectiveness": effectiveness,
                    "notes": notes,
                    "staff_name": staff_name,
                    "created_at": datetime.now().isoformat()
                }
                
                result = save_observation(obs_data)
                if result:
                    st.success("✅ Observation saved successfully!")
                    st.session_state.arousal_state = None
                    st.rerun()

# TAB 2: Student Dashboard
with tab2:
    st.header("Student Dashboard")
    
    students = get_students()
    if students:
        student_options = {f"{s['first_name']} {s['last_name']}": s['id'] for s in students}
        
        col1, col2 = st.columns([2, 1])
        with col1:
            dash_student_name = st.selectbox(
                "Select Student",
                options=list(student_options.keys()),
                key="dash_student"
            )
            dash_student_id = student_options[dash_student_name]
        
        with col2:
            days_range = st.selectbox(
                "Time Period",
                options=[7, 14, 30, 60, 90],
                format_func=lambda x: f"Last {x} days",
                index=2,
                key="days_range"
            )
        
        # Get observations
        observations = get_observations(dash_student_id, days_range)
        
        if observations:
            df = pd.DataFrame(observations)
            df['observation_date'] = pd.to_datetime(df['observation_date'])
            
            # Summary metrics
            st.markdown("### Overview")
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            total_obs = len(df)
            in_window = len(df[df['arousal_state'] == 'window'])
            mobilisation = len(df[df['arousal_state'] == 'mobilisation'])
            immobilisation = len(df[df['arousal_state'] == 'immobilisation'])
            
            with metric_col1:
                st.metric("Total Observations", total_obs)
            with metric_col2:
                pct = (in_window/total_obs*100) if total_obs > 0 else 0
                st.metric("In Window", f"{in_window} ({pct:.0f}%)")
            with metric_col3:
                pct = (mobilisation/total_obs*100) if total_obs > 0 else 0
                st.metric("Mobilisation", f"{mobilisation} ({pct:.0f}%)")
            with metric_col4:
                pct = (immobilisation/total_obs*100) if total_obs > 0 else 0
                st.metric("Immobilisation", f"{immobilisation} ({pct:.0f}%)")
            
            st.markdown("---")
            
            # Visualization
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### State Distribution")
                state_counts = df['arousal_state'].value_counts()
                
                fig = go.Figure(data=[go.Pie(
                    labels=[s.title() for s in state_counts.index],
                    values=state_counts.values,
                    marker=dict(colors=['#cc0000', '#008000', '#0000cc']),
                    hole=0.4
                )])
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Trend Over Time")
                daily_counts = df.groupby(['observation_date', 'arousal_state']).size().reset_index(name='count')
                
                fig = px.line(
                    daily_counts,
                    x='observation_date',
                    y='count',
                    color='arousal_state',
                    color_discrete_map={
                        'mobilisation': '#cc0000',
                        'window': '#008000',
                        'immobilisation': '#0000cc'
                    },
                    markers=True
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20),
                    xaxis_title="",
                    yaxis_title="Observations",
                    legend_title="State"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Recent observations table
            st.markdown("### Recent Observations")
            
            display_df = df.copy()
            display_df = display_df.sort_values('observation_date', ascending=False)
            display_df['Date'] = display_df['observation_date'].dt.strftime('%Y-%m-%d')
            display_df['State'] = display_df['arousal_state'].str.title()
            
            # Show table with delete option
            for idx, row in display_df.head(10).iterrows():
                with st.expander(f"{row['Date']} - {row['State']} ({row['duration_minutes']}min) - {row['staff_name']}"):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**Context:** {row['context']}")
                        if row['triggers']:
                            st.markdown(f"**Triggers:** {row['triggers']}")
                        if row['interventions_used']:
                            st.markdown(f"**Interventions:** {row['interventions_used']}")
                        if row['effectiveness']:
                            st.markdown(f"**Effectiveness:** {row['effectiveness']}")
                        if row['notes']:
                            st.markdown(f"**Notes:** {row['notes']}")
                    
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                            if delete_observation(row['id']):
                                st.success("Deleted")
                                st.rerun()
        else:
            st.info(f"No observations recorded for {dash_student_name} in the last {days_range} days")

# TAB 3: Analytics
with tab3:
    st.header("Analytics & Patterns")
    
    analysis_days = st.selectbox(
        "Analysis Period",
        options=[7, 14, 30, 60, 90],
        format_func=lambda x: f"Last {x} days",
        index=2,
        key="analysis_days"
    )
    
    # Get all observations
    all_obs = get_observations(days=analysis_days)
    
    if all_obs:
        df = pd.DataFrame(all_obs)
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        
        # Overall program stats
        st.markdown("### Program-Wide Patterns")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Observations", len(df))
        
        with col2:
            unique_students = df['student_id'].nunique()
            st.metric("Students Observed", unique_students)
        
        with col3:
            avg_duration = df['duration_minutes'].mean()
            st.metric("Avg Duration", f"{avg_duration:.1f} min")
        
        st.markdown("---")
        
        # Trigger analysis
        st.markdown("### Common Triggers")
        all_triggers = []
        for triggers in df['triggers'].dropna():
            if triggers:
                all_triggers.extend([t.strip() for t in triggers.split(',')])
        
        if all_triggers:
            trigger_df = pd.DataFrame({'trigger': all_triggers})
            trigger_counts = trigger_df['trigger'].value_counts().head(10)
            
            fig = px.bar(
                x=trigger_counts.values,
                y=trigger_counts.index,
                orientation='h',
                labels={'x': 'Count', 'y': 'Trigger'}
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Intervention effectiveness
        st.markdown("### Intervention Effectiveness")
        effectiveness_counts = df['effectiveness'].value_counts()
        
        fig = go.Figure(data=[go.Bar(
            x=effectiveness_counts.index,
            y=effectiveness_counts.values,
            marker_color=['#008000', '#ffa500', '#cc0000', '#999999']
        )])
        fig.update_layout(
            height=300,
            xaxis_title="Effectiveness",
            yaxis_title="Count",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No observations recorded in the selected period")

# TAB 4: Reference
with tab4:
    st.header("Window of Tolerance Reference")
    
    st.markdown("""
    ### Understanding Arousal States
    
    The Window of Tolerance is a neurobiological framework describing the optimal arousal zone for learning and social engagement.
    
    #### 🔴 MOBILISATION (Hyper-arousal)
    **Sympathetic nervous system activation**
    
    - **Behaviours:** Agitation, aggression, hypervigilance, difficulty sitting still, rapid speech, impulsivity
    - **Physical signs:** Increased heart rate, sweating, muscle tension, dilated pupils
    - **Impact on learning:** Difficulty focusing, processing information, or engaging in calm activities
    - **Common triggers:** Sensory overload, perceived threats, transitions, task demands, peer conflict
    
    **Regulation strategies:**
    - Calming sensory input (weighted items, quiet space)
    - Movement breaks
    - Deep breathing exercises
    - Reduce environmental stimulation
    - Predictable routine
    
    ---
    
    #### 🟢 WINDOW OF TOLERANCE (Optimal arousal)
    **Ventral vagal activation - social engagement system**
    
    - **Behaviours:** Calm, focused, receptive to learning, able to engage socially
    - **Physical signs:** Relaxed body language, appropriate eye contact, regulated breathing
    - **Impact on learning:** Optimal state for new learning, problem-solving, and relationship building
    - **Maintaining the window:** Predictable environment, attuned relationships, appropriate challenges
    
    **Widening the window:**
    - Build relational safety
    - Teach self-regulation skills
    - Gradual exposure to manageable stressors
    - Consistent co-regulation
    
    ---
    
    #### 🔵 IMMOBILISATION (Hypo-arousal)
    **Dorsal vagal activation**
    
    - **Behaviours:** Withdrawal, dissociation, flat affect, minimal response, appearing "shut down"
    - **Physical signs:** Slowed movement, low energy, limited facial expression, minimal speech
    - **Impact on learning:** Inability to engage, process information, or respond to prompts
    - **Common triggers:** Prolonged stress, overwhelm, feeling unsafe, previous trauma activation
    
    **Regulation strategies:**
    - Gentle activation (movement, music, games)
    - Sensory input (cold water, crunchy snacks)
    - Connection attempts (low-pressure activities)
    - Safe, predictable environment
    - Avoid forcing engagement
    
    ---
    
    ### Polyvagal Theory Foundation
    
    The Window of Tolerance framework is grounded in Polyvagal Theory (Porges, 2011), which describes three neural pathways:
    
    1. **Ventral Vagal** (social engagement) → Window of Tolerance
    2. **Sympathetic** (fight/flight) → Mobilisation
    3. **Dorsal Vagal** (freeze/collapse) → Immobilisation
    
    ### Key Practice Principles
    
    - **Regulation before education:** Students must feel safe before they can learn
    - **Co-regulation precedes self-regulation:** Adult's regulated state helps student regulate
    - **Window widens with safety:** Relational safety expands tolerance for stress
    - **Track patterns, not incidents:** Look for triggers, contexts, and effective interventions
    - **Individualized approach:** Each student's window and triggers are unique
    
    ### Documentation Tips
    
    - Record observations as close to the event as possible
    - Note context and environmental factors
    - Identify specific triggers when observable
    - Document what interventions were tried and their effectiveness
    - Look for patterns over time rather than isolated incidents
    - Share observations with the team to build collective understanding
    
    ### References
    
    - Porges, S. W. (2011). *The Polyvagal Theory: Neurophysiological foundations of emotions, attachment, communication, and self-regulation.*
    - Siegel, D. J. (1999). *The Developing Mind: How relationships and the brain interact to shape who we are.*
    - Ogden, P., Minton, K., & Pain, C. (2006). *Trauma and the Body: A sensorimotor approach to psychotherapy.*
    """)

st.markdown("---")
st.caption("Window of Tolerance Tracker | Cowandilla Learning Centre LBU")
