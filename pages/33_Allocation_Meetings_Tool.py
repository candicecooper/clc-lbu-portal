-- Allocation Meetings Database Schema
-- CLC-LBU Allocation Meeting Tracking System

-- Main allocation records table
CREATE TABLE IF NOT EXISTS allocation_students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_week TEXT NOT NULL,
    meeting_date DATE NOT NULL,
    term TEXT NOT NULL,
    year INTEGER NOT NULL,
    
    -- Student Information
    student_name TEXT NOT NULL,
    school TEXT,
    date_of_birth DATE,
    year_level TEXT,
    exc_tsp_itsp TEXT,
    edid TEXT,
    
    -- Categorical Funding (stored as JSON array for flexibility)
    cat_funding JSONB DEFAULT '[]'::jsonb,
    
    -- Partnership (stored as JSON array)
    partnership JSONB DEFAULT '[]'::jsonb,
    
    -- Program
    program TEXT,
    
    -- Placement Information
    start_after DATE,
    finishing_date DATE,
    
    -- Case Worker/BSC/School
    case_worker TEXT,
    bsc TEXT,
    school_contact TEXT,
    
    -- Meeting Details
    queries TEXT,
    outcome TEXT,
    details TEXT,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT,
    
    CONSTRAINT allocation_students_program_check 
        CHECK (program IN ('Junior Primary', 'Primary', 'Secondary'))
);

-- Extension requests table
CREATE TABLE IF NOT EXISTS allocation_extensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_week TEXT NOT NULL,
    meeting_date DATE NOT NULL,
    term TEXT NOT NULL,
    year INTEGER NOT NULL,
    
    -- Student Information
    student_name TEXT NOT NULL,
    program TEXT,
    
    -- Extension Details
    extension_outcome TEXT,
    conditional BOOLEAN,
    information_to_school TEXT,
    actioned_by TEXT,
    extended_until DATE,
    
    -- Support Team
    school_referrer TEXT,
    caseworker TEXT,
    behaviour_support_educator TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT,
    
    CONSTRAINT allocation_extensions_program_check 
        CHECK (program IN ('Junior Primary', 'Primary', 'Secondary')),
    CONSTRAINT allocation_extensions_outcome_check
        CHECK (extension_outcome IN ('Approved', 'Not Approved', NULL))
);

-- Students not placed table
CREATE TABLE IF NOT EXISTS allocation_not_placed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_week TEXT NOT NULL,
    meeting_date DATE NOT NULL,
    term TEXT NOT NULL,
    year INTEGER NOT NULL,
    
    -- Student Information
    student_name TEXT NOT NULL,
    program TEXT,
    school TEXT,
    
    -- Placement Information
    information_to_school TEXT,
    reason_full_capacity BOOLEAN DEFAULT FALSE,
    reason_slc_option BOOLEAN DEFAULT FALSE,
    reason_documentation_needed BOOLEAN DEFAULT FALSE,
    reason_other TEXT,
    
    -- Follow-up
    request_next_meeting BOOLEAN,
    
    -- Support Team
    school_referrer TEXT,
    caseworker TEXT,
    behaviour_support_educator TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT,
    
    CONSTRAINT allocation_not_placed_program_check 
        CHECK (program IN ('Junior Primary', 'Primary', 'Secondary'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_allocation_students_meeting 
    ON allocation_students(meeting_week, meeting_date);
CREATE INDEX IF NOT EXISTS idx_allocation_students_student 
    ON allocation_students(student_name);
CREATE INDEX IF NOT EXISTS idx_allocation_students_term_year 
    ON allocation_students(term, year);

CREATE INDEX IF NOT EXISTS idx_allocation_extensions_meeting 
    ON allocation_extensions(meeting_week, meeting_date);
CREATE INDEX IF NOT EXISTS idx_allocation_extensions_student 
    ON allocation_extensions(student_name);

CREATE INDEX IF NOT EXISTS idx_allocation_not_placed_meeting 
    ON allocation_not_placed(meeting_week, meeting_date);
CREATE INDEX IF NOT EXISTS idx_allocation_not_placed_student 
    ON allocation_not_placed(student_name);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_allocation_students_updated_at 
    BEFORE UPDATE ON allocation_students
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_allocation_extensions_updated_at 
    BEFORE UPDATE ON allocation_extensions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_allocation_not_placed_updated_at 
    BEFORE UPDATE ON allocation_not_placed
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies (disable for anon key access, following CLC portal pattern)
ALTER TABLE allocation_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE allocation_extensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE allocation_not_placed ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all access for allocation_students" ON allocation_students
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Enable all access for allocation_extensions" ON allocation_extensions
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Enable all access for allocation_not_placed" ON allocation_not_placed
    FOR ALL USING (true) WITH CHECK (true);
