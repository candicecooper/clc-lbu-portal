# Daily Bulletin Integration for Program Changes
# Add this code to 1_Daily_Bulletin.py to display program changes from the new tool

# At the top with other imports:
from datetime import date

# In your Daily Bulletin display section, replace the program changes input section with this read-only display:

def display_program_changes(supabase, target_date):
    """Display program changes from the Program Changes Manager"""
    
    # Get today's changes from database
    response = supabase.table("program_changes").select("*").eq("change_date", target_date.isoformat()).order("created_at").execute()
    changes = response.data if response.data else []
    
    if not changes:
        st.info("ℹ️ No program changes scheduled for today. Add changes in the **Program Changes Manager** tool.")
        return
    
    st.markdown("### 📋 Today's Program Changes")
    
    for idx, change in enumerate(changes):
        # Create a card for each change
        with st.container():
            st.markdown(f"""
            <div style="background-color: #FFF9E6; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #C8760A; margin-bottom: 1rem;">
                <h4 style="color: #1A7A6E; margin-top: 0;">
                    {change.get('reason', 'Program Change')}
                </h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f"**Staff:** {change.get('staff_name', 'N/A')}")
            with col2:
                if change.get('trt_name'):
                    st.markdown(f"**TRT/Acting:** {change.get('trt_name')}")
            
            # Display time blocks
            blocks = change.get('time_blocks', [])
            if blocks:
                st.markdown("**Time Changes:**")
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    st.markdown(f"- **{start} → {end}**: {program}")
            
            if change.get('notes'):
                st.markdown(f"*{change.get('notes')}*")
            
            st.markdown("---")

# Helper function (add to your helpers section):
def format_time(t):
    """Format time object to string"""
    if isinstance(t, time):
        return t.strftime("%I:%M %p").lstrip('0')
    elif isinstance(t, str):
        try:
            from datetime import datetime
            return datetime.strptime(t, "%H:%M:%S").strftime("%I:%M %p").lstrip('0')
        except:
            return t
    return str(t)

# In your main Daily Bulletin display, replace the program changes section with:
# (Around where you currently have the program changes input)

st.markdown("---")
display_program_changes(supabase, date.today())

# For STAFF ROOM DISPLAY MODE (?display=true), also add:
# In the display mode section, add the program changes display:

if query_params.get("display") == "true":
    # ... existing staff room display code ...
    
    # Add program changes section
    st.markdown("---")
    st.markdown("## 📋 Program Changes")
    
    response = supabase.table("program_changes").select("*").eq("change_date", date.today().isoformat()).order("created_at").execute()
    changes = response.data if response.data else []
    
    if not changes:
        st.markdown("### No program changes today")
    else:
        for change in changes:
            st.markdown(f"""
            <div style="background-color: #1A7A6E; color: white; padding: 1.5rem; 
                        border-radius: 10px; margin-bottom: 1.5rem;">
                <h2 style="margin-top: 0; color: white;">{change.get('reason', 'Program Change')}</h2>
                <h3 style="color: #FFD700; margin: 0.5rem 0;">
                    {change.get('staff_name', 'N/A')}
                    {' → ' + change.get('trt_name') if change.get('trt_name') else ''}
                </h3>
            """, unsafe_allow_html=True)
            
            blocks = change.get('time_blocks', [])
            if blocks:
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    st.markdown(f"<p style='font-size: 1.2rem; color: white; margin: 0.5rem 0;'>• {start} → {end}: <strong>{program}</strong></p>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

# NOTES:
# 1. Remove the existing program changes INPUT section from Daily Bulletin
# 2. Keep only the DISPLAY code above
# 3. The Program Changes Manager tool handles all input
# 4. Daily Bulletin becomes read-only for program changes
# 5. Staff room display will show program changes in large, clear format
