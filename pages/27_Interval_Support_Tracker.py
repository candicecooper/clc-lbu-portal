-- ============================================
-- Committee Meetings Management Schema
-- ============================================

-- Table: committee_meetings
-- Stores meeting information
CREATE TABLE IF NOT EXISTS committee_meetings (
    id BIGSERIAL PRIMARY KEY,
    committee_name TEXT NOT NULL,
    meeting_title TEXT NOT NULL,
    meeting_date DATE NOT NULL,
    meeting_time TIME,
    location TEXT,
    status TEXT DEFAULT 'draft', -- draft, published, archived
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Table: committee_agenda_items
-- Stores agenda items for each meeting
CREATE TABLE IF NOT EXISTS committee_agenda_items (
    id BIGSERIAL PRIMARY KEY,
    meeting_id BIGINT NOT NULL REFERENCES committee_meetings(id) ON DELETE CASCADE,
    item_number INTEGER NOT NULL,
    item_title TEXT NOT NULL,
    item_description TEXT,
    duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: committee_minutes
-- Stores meeting minutes (both transcript and formatted)
CREATE TABLE IF NOT EXISTS committee_minutes (
    id BIGSERIAL PRIMARY KEY,
    meeting_id BIGINT NOT NULL REFERENCES committee_meetings(id) ON DELETE CASCADE,
    transcript TEXT,
    formatted_minutes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_committee_meetings_committee ON committee_meetings(committee_name);
CREATE INDEX IF NOT EXISTS idx_committee_meetings_date ON committee_meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_committee_meetings_status ON committee_meetings(status);
CREATE INDEX IF NOT EXISTS idx_committee_agenda_meeting ON committee_agenda_items(meeting_id);
CREATE INDEX IF NOT EXISTS idx_committee_minutes_meeting ON committee_minutes(meeting_id);

-- Enable RLS (will be disabled for simplicity, matching the documents pattern)
ALTER TABLE committee_meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE committee_agenda_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE committee_minutes ENABLE ROW LEVEL SECURITY;

-- Disable RLS for these tables to avoid auth issues
ALTER TABLE committee_meetings DISABLE ROW LEVEL SECURITY;
ALTER TABLE committee_agenda_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE committee_minutes DISABLE ROW LEVEL SECURITY;

-- Note: RLS is disabled to match the pattern used for committees_documents
-- This is appropriate for an internal staff portal where all authenticated users
-- should have access to committee information
