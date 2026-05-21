# ============================================================================
# FIXED VERSION - Add this after the documents view (line 930)
# ============================================================================

# ========== COMMITTEE MEMBERS VIEW ==========
elif st.session_state.committee_view == 'members':
    
    st.markdown("### 👥 Committee Members & Roles")
    st.markdown("View all staff committee assignments and roles.")
    
    # Back button
    if st.button("↩ Return to Committees Home", use_container_width=True):
        navigate_to('home')
    
    st.divider()
    
    # Try to load data with error handling
    try:
        # Test if tables exist
        test_response = supabase.table('committee_roles').select('*').limit(1).execute()
        
        # Get all committees
        committees_response = supabase.table('committee_roles')\
            .select('*')\
            .order('display_order', desc=False)\
            .execute()
        
        committees = committees_response.data if committees_response.data else []
        
        # Get members for each committee
        for committee in committees:
            members_response = supabase.table('committee_role_members')\
                .select('*')\
                .eq('committee_id', committee['id'])\
                .order('display_order', desc=False)\
                .execute()
            
            committee['members'] = members_response.data if members_response.data else []
        
        # Display results
        if len(committees) == 0:
            st.info("👋 No committee roles found in database.")
            st.warning("Tables exist but are empty. Click below to initialize with default data:")
            
            if st.button("🚀 Load Default Committees", use_container_width=True, type="primary"):
                with st.spinner("Loading default committees..."):
                    try:
                        # PAC Committee
                        pac = supabase.table('committee_roles').insert({
                            'name': 'PAC',
                            'description': 'Partnership & Cooperation Committee',
                            'display_order': 0
                        }).execute()
                        
                        if pac.data:
                            pac_id = pac.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': pac_id, 'staff_name': 'Candice', 'role': 'Leader', 'display_order': 0},
                                {'committee_id': pac_id, 'staff_name': 'Naomi', 'role': 'SSO rep', 'display_order': 1},
                                {'committee_id': pac_id, 'staff_name': 'Ben', 'role': 'AEU Rep', 'display_order': 2},
                                {'committee_id': pac_id, 'staff_name': 'Brenton', 'role': 'Teacher Rep', 'display_order': 3}
                            ]).execute()
                        
                        # WHS
                        whs = supabase.table('committee_roles').insert({
                            'name': 'WHS',
                            'description': 'Work Health & Safety',
                            'display_order': 1
                        }).execute()
                        
                        if whs.data:
                            whs_id = whs.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': whs_id, 'staff_name': 'Candice', 'role': 'OHS Rep', 'display_order': 0},
                                {'committee_id': whs_id, 'staff_name': 'Naomi', 'role': '', 'display_order': 1},
                                {'committee_id': whs_id, 'staff_name': 'Ben Selga', 'role': '', 'display_order': 2},
                                {'committee_id': whs_id, 'staff_name': 'Caitie', 'role': '', 'display_order': 3},
                                {'committee_id': whs_id, 'staff_name': 'Roisin', 'role': '', 'display_order': 4}
                            ]).execute()
                        
                        # Social Club
                        social = supabase.table('committee_roles').insert({
                            'name': 'Social Club',
                            'description': '',
                            'display_order': 2
                        }).execute()
                        
                        if social.data:
                            social_id = social.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': social_id, 'staff_name': 'Ben Sutton', 'role': '', 'display_order': 0},
                                {'committee_id': social_id, 'staff_name': 'Vinnie', 'role': '', 'display_order': 1},
                                {'committee_id': social_id, 'staff_name': 'Jacqui', 'role': '', 'display_order': 2},
                                {'committee_id': social_id, 'staff_name': 'Annette', 'role': '', 'display_order': 3}
                            ]).execute()
                        
                        # Centre Spec Events
                        events = supabase.table('committee_roles').insert({
                            'name': 'Centre Spec Events',
                            'description': 'Centre Special Events',
                            'display_order': 3
                        }).execute()
                        
                        if events.data:
                            events_id = events.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': events_id, 'staff_name': 'Brenton', 'role': '', 'display_order': 0},
                                {'committee_id': events_id, 'staff_name': 'Ben Selga', 'role': '', 'display_order': 1},
                                {'committee_id': events_id, 'staff_name': 'Annette', 'role': '', 'display_order': 2}
                            ]).execute()
                        
                        # Leaving Gift
                        leaving = supabase.table('committee_roles').insert({
                            'name': 'Leaving Gift',
                            'description': '',
                            'display_order': 4
                        }).execute()
                        
                        if leaving.data:
                            leaving_id = leaving.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': leaving_id, 'staff_name': 'Caitie', 'role': '', 'display_order': 0},
                                {'committee_id': leaving_id, 'staff_name': 'Jacqui', 'role': '', 'display_order': 1},
                                {'committee_id': leaving_id, 'staff_name': 'Annette', 'role': '', 'display_order': 2},
                                {'committee_id': leaving_id, 'staff_name': 'Candice', 'role': '', 'display_order': 3},
                                {'committee_id': leaving_id, 'staff_name': 'Naomi', 'role': '', 'display_order': 4}
                            ]).execute()
                        
                        # OHS
                        ohs = supabase.table('committee_roles').insert({
                            'name': 'OHS',
                            'description': 'Occupational Health & Safety',
                            'display_order': 5
                        }).execute()
                        
                        if ohs.data:
                            ohs_id = ohs.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': ohs_id, 'staff_name': 'Roisin', 'role': 'Proxy', 'display_order': 0},
                                {'committee_id': ohs_id, 'staff_name': 'Caitie', 'role': 'Proxy', 'display_order': 1}
                            ]).execute()
                        
                        # AEU
                        aeu = supabase.table('committee_roles').insert({
                            'name': 'AEU',
                            'description': 'Australian Education Union',
                            'display_order': 6
                        }).execute()
                        
                        if aeu.data:
                            aeu_id = aeu.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': aeu_id, 'staff_name': 'Roisin', 'role': 'Proxy', 'display_order': 0},
                                {'committee_id': aeu_id, 'staff_name': 'Ben Sutton', 'role': 'Proxy', 'display_order': 1}
                            ]).execute()
                        
                        # Fire Warden
                        fire = supabase.table('committee_roles').insert({
                            'name': 'Fire Warden',
                            'description': '',
                            'display_order': 7
                        }).execute()
                        
                        if fire.data:
                            fire_id = fire.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': fire_id, 'staff_name': 'Brenton', 'role': '', 'display_order': 0},
                                {'committee_id': fire_id, 'staff_name': 'Ben Selga', 'role': '', 'display_order': 1}
                            ]).execute()
                        
                        # First Aid Officer
                        first_aid = supabase.table('committee_roles').insert({
                            'name': 'First Aid Officer',
                            'description': '',
                            'display_order': 8
                        }).execute()
                        
                        if first_aid.data:
                            first_aid_id = first_aid.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': first_aid_id, 'staff_name': 'Naomi', 'role': '', 'display_order': 0}
                            ]).execute()
                        
                        # Mathletics Coordinator (was 3P Learning Coordinator)
                        mathletics = supabase.table('committee_roles').insert({
                            'name': 'Mathletics Coordinator',
                            'description': '3P Learning',
                            'display_order': 9
                        }).execute()
                        
                        if mathletics.data:
                            mathletics_id = mathletics.data[0]['id']
                            supabase.table('committee_role_members').insert([
                                {'committee_id': mathletics_id, 'staff_name': 'Caitie', 'role': '', 'display_order': 0}
                            ]).execute()
                        
                        st.success("✅ All committees loaded successfully!")
                        st.balloons()
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error loading committees: {str(e)}")
        
        else:
            # Display committees
            st.success(f"✅ Loaded {len(committees)} committees")
            
            # Edit mode toggle
            edit_mode = st.toggle("✏️ Edit Mode", value=False)
            
            if edit_mode:
                st.info("✏️ **Edit Mode Active** - Click on a committee name to edit it.")
            
            st.divider()
            
            # Display each committee
            for committee in committees:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"### 🤝 {committee['name']}")
                        if committee.get('description'):
                            st.caption(committee['description'])
                    
                    with col2:
                        if edit_mode:
                            if st.button("✏️", key=f"edit_{committee['id']}", help="Edit committee"):
                                st.info("Editing features coming soon!")
                    
                    # Display members
                    if committee['members']:
                        member_display = []
                        for member in committee['members']:
                            if member['role']:
                                member_display.append(f"**{member['staff_name']}** ({member['role']})")
                            else:
                                member_display.append(f"**{member['staff_name']}**")
                        
                        st.markdown("**Members:** " + " • ".join(member_display))
                    else:
                        st.caption("_No members assigned_")
                    
                    st.divider()
    
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")
        
        st.warning("**Tables might not exist yet.** Run this SQL in Supabase SQL Editor:")
        
        with st.expander("📋 Click to see SQL setup"):
            st.code("""
CREATE TABLE IF NOT EXISTS committee_roles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS committee_role_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    committee_id UUID REFERENCES committee_roles(id) ON DELETE CASCADE,
    staff_name TEXT NOT NULL,
    role TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_committee_role_members_committee ON committee_role_members(committee_id);
ALTER TABLE committee_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE committee_role_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for service role" ON committee_roles FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON committee_role_members FOR ALL USING (true);
            """, language="sql")
