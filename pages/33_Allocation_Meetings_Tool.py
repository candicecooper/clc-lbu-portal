# ============================================================================
# DEBUG EXPORT FUNCTION - Shows what's happening with your data
# Use this to diagnose why rows are empty
# ============================================================================

def export_to_data_entry_DEBUG(selected_allocations):
    """Generate Excel with DEBUG info - shows what data is being exported"""
    
    import json
    
    # Show what data we received from Supabase
    st.write("🔍 **DEBUG INFO**")
    st.write(f"Number of records received: {len(selected_allocations)}")
    
    if len(selected_allocations) > 0:
        st.write("First record Supabase field names:")
        st.code(json.dumps(list(selected_allocations[0].keys()), indent=2))
        
        st.write("First record sample values:")
        sample = {k: str(v)[:50] for k, v in selected_allocations[0].items()}
        st.write(sample)
    
    # Create DataFrame from allocations
    df = pd.DataFrame(selected_allocations)
    
    st.write(f"DataFrame shape: {df.shape}")
    st.write(f"DataFrame columns: {list(df.columns)}")
    
    # ============================================================================
    # COMPREHENSIVE FIELD MAPPING - All Supabase → Excel names
    # ============================================================================
    field_mapping = {
        # Direct name mappings
        'id': 'Referral_ID',
        'student_name': 'Student_Name',
        'date_of_birth': 'DOB',
        'school': 'Referring_School',
        'program': 'Allocated_Program',
        'outcome': 'Allocation_Status',
        'start_after': 'Placement_Start',
        'finishing_date': 'Placement_End',
        'partnership_area': 'Partnership_Area',
        'year_level': 'Year_Level',
        'gender': 'Gender',
        'priority_level': 'Priority_Level',
        'previous_clc_placement': 'Previous_CLC_Placement',
        'previous_other_lc': 'Previous_Other_LC',
        'other_lc_name': 'Other_LC_Name',
        'total_previous_placements': 'Total_Previous_Placements',
        'placement_history_notes': 'Placement_History_Notes',
        'medical_condition_details': 'Medical_Condition_Details',
        'medication_details': 'Medication_Details',
        'bespoke_placement': 'Bespoke_Placement',
        'waitlist_status': 'Waitlist_Status',
        'waitlist_date': 'Waitlist_Date',
        'allocated_from_waitlist': 'Allocated_From_Waitlist',
        'exclusion_finish_date': 'Exclusion_End_Date',
        'proposed_extension_finish_date': 'Proposed_Extension_Finish_Date',
        'extension_weeks': 'Extension_Weeks',
        'information': 'Communication_to_school',
        'actioned_by': 'Action_owner',
        'case_worker': 'Case_Worker',
        'meeting_week': 'Meeting_Week',
        'meeting_date': 'Meeting_Date',
        'referral_date': 'Referral_Date',
        'bse_involved': 'BSE_Involved',
        'bse_name': 'BSE_Name',
        'term': 'Term',
        'year': 'Year',
    }
    
    # Show which Supabase columns we can map
    mapped_columns = [col for col in df.columns if col in field_mapping]
    unmapped_columns = [col for col in df.columns if col not in field_mapping]
    
    st.write(f"✅ Can map {len(mapped_columns)} columns: {mapped_columns}")
    if unmapped_columns:
        st.write(f"⚠️ Cannot map {len(unmapped_columns)} columns: {unmapped_columns}")
    
    # Rename columns
    df_renamed = df.rename(columns=field_mapping)
    
    st.write(f"After rename, DataFrame has columns: {list(df_renamed.columns)}")
    
    # Create export dataframe with all 76 columns
    df_export = pd.DataFrame(index=df_renamed.index)
    
    for col in EXPORT_COLUMNS:
        if col in df_renamed.columns:
            df_export[col] = df_renamed[col]
            st.write(f"✅ Column {col}: {len(df_renamed[col].dropna())} non-empty values")
        else:
            df_export[col] = None
    
    st.write("---")
    st.write(f"Final export DataFrame: {df_export.shape[0]} rows × {df_export.shape[1]} columns")
    
    # Show first row of export
    if df_export.shape[0] > 0:
        st.write("**First exported row (non-null values only):**")
        first_row = df_export.iloc[0]
        non_null = first_row[first_row.notna()]
        st.write(non_null)
    
    # Create Excel
    output = BytesIO()
    df_export.to_excel(output, sheet_name='Data_Model', index=False, engine='openpyxl')
    
    # Style
    output.seek(0)
    wb = openpyxl.load_workbook(output)
    ws = wb.active
    
    header_fill = PatternFill(start_color="1A7A6E", end_color="1A7A6E", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    output_final = BytesIO()
    wb.save(output_final)
    output_final.seek(0)
    
    return output_final


# ============================================================================
# IN TAB 4, REPLACE THIS:
# ============================================================================
#
# if st.button("📥 Download Data Entry Excel", type="primary"):
#     try:
#         all_allocations = allocated + not_allocated
#         
#         if all_allocations:
#             excel_bytes = export_to_data_entry(all_allocations)
#
# WITH THIS:
# ============================================================================
#
# if st.button("📥 Download Data Entry Excel (with Debug)", type="primary"):
#     try:
#         all_allocations = allocated + not_allocated
#         
#         if all_allocations:
#             excel_bytes = export_to_data_entry_DEBUG(all_allocations)
#
# ============================================================================
