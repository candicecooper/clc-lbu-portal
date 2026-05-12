# SMARTAR Goal Builder Modifications
# Add these changes to 25_SMARTAR_Goal_Builder.py to complete Team Meetings integration

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: ADD AT START OF FILE (after imports, before main render function)
# ═══════════════════════════════════════════════════════════════════════════════

def check_team_meeting_context():
    """
    Check if this page was opened from Team Meetings.
    Returns context dict if yes, None if standalone use.
    """
    if 'from_team_meeting' in st.session_state:
        context = st.session_state['from_team_meeting']
        
        # Optional: Check timestamp to avoid stale context (older than 5 minutes)
        try:
            timestamp = datetime.datetime.fromisoformat(context['timestamp'])
            age = (datetime.datetime.now() - timestamp).total_seconds()
            if age > 300:  # 5 minutes
                # Context is stale, clear it
                del st.session_state['from_team_meeting']
                return None
        except:
            pass
        
        return context
    return None

def return_to_team_meeting_with_goal(student_name, goal_text, meeting_id):
    """
    Pass created goal back to Team Meeting and navigate back.
    """
    st.session_state['smartar_return_data'] = {
        'student_name': student_name,
        'smartar_goal': goal_text,
        'meeting_id': meeting_id,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # Clear the context since we're returning
    if 'from_team_meeting' in st.session_state:
        del st.session_state['from_team_meeting']
    
    # Navigate back to Team Meetings
    st.switch_page("pages/3_Team_Meetings.py")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: MODIFY AT START OF MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main SMARTAR Goal Builder function."""
    
    # ═══ NEW: Check if opened from Team Meeting ═══
    meeting_context = check_team_meeting_context()
    
    # Show context banner if from Team Meeting
    if meeting_context:
        st.markdown(f"""
        <div style="background:#dbeafe;border-left:5px solid #0284c7;border-radius:8px;
                    padding:12px 16px;margin-bottom:16px;font-size:14px;">
          📍 <strong>Creating goal for {meeting_context['student_name']}</strong><br>
          <small style="color:#075985;">
            {PROGRAMS[meeting_context['program']]['label']} Team Meeting · 
            {meeting_context['term']} Week {meeting_context['week']} · 
            Meeting ID: {meeting_context['meeting_id']}
          </small>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══ EXISTING CODE: Page title, etc. ═══
    st.title("🎯 SMARTAR Goal Builder")
    # ... rest of existing page setup ...
    
    # ═══ MODIFIED: Student name input with context pre-population ═══
    if meeting_context:
        # Pre-populate from context, make it read-only or disabled
        st.markdown(f"**Student:** {meeting_context['student_name']}")
        student_name = meeting_context['student_name']
        
        # Optional: Show as disabled input so it's in the UI consistently
        st.text_input(
            "Student Name",
            value=meeting_context['student_name'],
            disabled=True,
            key="student_name_from_meeting",
            label_visibility="collapsed"
        )
    else:
        # Normal student name input for standalone use
        student_name = st.text_input(
            "Student Name",
            placeholder="Enter student name",
            key="student_name_standalone"
        )
    
    # ═══ EXISTING CODE: All goal building UI ═══
    # Your existing goal builder interface goes here:
    # - SMARTAR framework inputs
    # - GAS levels
    # - Evidence fields
    # - etc.
    
    # ... existing goal building code ...
    
    # After goal is built, you have 'goal_text' variable with final goal
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PART 3: REPLACE SAVE BUTTON WITH CONDITIONAL LOGIC
    # ═══════════════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    # Check if goal is complete and valid
    goal_complete = bool(student_name and goal_text and len(goal_text) > 20)
    
    if meeting_context:
        # ═══ TEAM MEETING WORKFLOW: Return button ═══
        st.markdown("### Add Goal to Meeting")
        st.caption("This will save the goal and return you to the Team Meeting with the goal automatically added.")
        
        col_return, col_cancel = st.columns([2, 1])
        
        with col_return:
            if st.button(
                "✓ Add Goal to Meeting & Return",
                type="primary",
                disabled=not goal_complete,
                use_container_width=True,
                key="return_to_meeting"
            ):
                if goal_complete:
                    # Save goal to database first (your existing save logic)
                    try:
                        goal_data = {
                            'student_name': student_name,
                            'smartar_goal': goal_text,
                            'meeting_id': meeting_context['meeting_id'],
                            'program': meeting_context['program'],
                            'term': meeting_context['term'],
                            'week': meeting_context['week'],
                            'created_at': datetime.datetime.now().isoformat(),
                            # ... any other fields your table needs ...
                        }
                        
                        # Save to your Behaviour Support Supabase
                        behaviour_supabase.table('smartar_goals').insert(goal_data).execute()
                        
                        st.success("✅ Goal saved to database!")
                        
                        # Return to meeting with goal
                        return_to_team_meeting_with_goal(
                            student_name,
                            goal_text,
                            meeting_context['meeting_id']
                        )
                        
                    except Exception as e:
                        st.error(f"⚠️ Failed to save goal: {e}")
                        st.info("Goal was not saved. Please try again or contact support.")
                else:
                    st.warning("⚠️ Please complete all required goal fields first.")
        
        with col_cancel:
            if st.button("❌ Cancel & Return", use_container_width=True, key="cancel_return"):
                # Return without saving
                if 'from_team_meeting' in st.session_state:
                    del st.session_state['from_team_meeting']
                st.switch_page("pages/3_Team_Meetings.py")
    
    else:
        # ═══ STANDALONE WORKFLOW: Regular save button ═══
        st.markdown("### Save Goal")
        
        if st.button(
            "💾 Save Goal",
            type="primary",
            disabled=not goal_complete,
            use_container_width=True,
            key="save_standalone"
        ):
            if goal_complete:
                try:
                    # Your existing save logic for standalone use
                    goal_data = {
                        'student_name': student_name,
                        'smartar_goal': goal_text,
                        'created_at': datetime.datetime.now().isoformat(),
                        # ... other fields ...
                    }
                    
                    behaviour_supabase.table('smartar_goals').insert(goal_data).execute()
                    
                    st.success("✅ Goal saved!")
                    
                    # Optional: Clear form for next goal
                    if st.button("Create Another Goal"):
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"⚠️ Failed to save goal: {e}")
            else:
                st.warning("⚠️ Please complete all required fields.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: TESTING THE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

"""
TESTING WORKFLOW:

1. From Team Meetings:
   - Click "🎯 Open Goal Builder" for a student
   - Should see: "📍 Creating goal for [Student Name]" banner
   - Student name should be pre-filled
   
2. Build Goal:
   - Fill out goal details
   - "✓ Add Goal to Meeting & Return" button should be visible
   - "❌ Cancel & Return" button should be visible
   
3. Save & Return:
   - Click "✓ Add Goal to Meeting & Return"
   - Should save to database
   - Should navigate back to Team Meetings
   - Should see: "✅ Goal created for [Student Name]!"
   - Goal text should appear in student notes

4. Standalone Use:
   - Navigate directly to SMARTAR Goal Builder (not from Team Meeting)
   - Should NOT see context banner
   - Should see normal student name input
   - Should see "💾 Save Goal" button (not Return button)

DEBUGGING:

If context banner doesn't appear:
- Check st.session_state['from_team_meeting'] exists
- Print it: st.write(st.session_state.get('from_team_meeting'))

If return doesn't work:
- Check st.session_state['smartar_return_data'] is set
- Verify path in st.switch_page() matches your file structure
- Check browser console for JavaScript errors

If goal doesn't appear in meeting:
- Check check_smartar_return() is called in Team Meetings
- Verify student name matching (case-sensitive!)
- Check goal text format
"""

# ═══════════════════════════════════════════════════════════════════════════════
# ALTERNATIVE: QUERY PARAMS METHOD (if st.switch_page unavailable)
# ═══════════════════════════════════════════════════════════════════════════════

"""
If your Streamlit version doesn't support st.switch_page(), use query params:

FROM TEAM MEETINGS:
```python
def open_smartar_goal_builder(student_name, meeting_id, program, term, week):
    url = f"SMARTAR_Goal_Builder?from_meeting=true&student={quote(student_name)}&meeting_id={meeting_id}&program={program}&term={term}&week={week}"
    st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
```

IN SMARTAR GOAL BUILDER:
```python
def check_team_meeting_context():
    from_meeting = st.query_params.get("from_meeting")
    if from_meeting == "true":
        return {
            'student_name': st.query_params.get("student"),
            'meeting_id': st.query_params.get("meeting_id"),
            'program': st.query_params.get("program"),
            'term': st.query_params.get("term"),
            'week': st.query_params.get("week")
        }
    return None

def return_to_team_meeting_with_goal(student_name, goal_text, meeting_id):
    # Store goal in Supabase with meeting_id
    # Then redirect back
    st.markdown('<meta http-equiv="refresh" content="0; url=Team_Meetings">', unsafe_allow_html=True)
```

This method is less clean but works without session state cross-page passing.
"""
