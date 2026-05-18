-- ════════════════════════════════════════════════════════════════════════════
-- Scatter Plot Tracker — ABA Edition
-- COMPLETE DATABASE SETUP (builds everything from scratch)
-- Run this in Supabase SQL Editor
-- ════════════════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════════
-- PART 1: CREATE CORE TABLES
-- ══════════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_students (student roster)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_students (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_name TEXT NOT NULL UNIQUE,
    program_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE scatter_students IS 'Student roster for scatter plot tracking';
COMMENT ON COLUMN scatter_students.program_type IS 'JP, PY, or SY program';

-- Create index
CREATE INDEX IF NOT EXISTS idx_scatter_students_name ON scatter_students(student_name);


-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_behaviour_bank (behaviour definitions with ABA fields)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_behaviour_bank (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- ABA Fields
    operational_definition TEXT DEFAULT '',
    examples TEXT DEFAULT '',
    non_examples TEXT DEFAULT '',
    measurement_type TEXT DEFAULT 'frequency',
    hypothesized_function TEXT DEFAULT 'unknown',
    
    -- Metadata
    is_custom BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(category, description)
);

COMMENT ON TABLE scatter_behaviour_bank IS 'Global behaviour bank with operational definitions';
COMMENT ON COLUMN scatter_behaviour_bank.operational_definition IS 'Observable, measurable description of the behaviour';
COMMENT ON COLUMN scatter_behaviour_bank.examples IS 'Comma-separated examples of what counts as this behaviour';
COMMENT ON COLUMN scatter_behaviour_bank.non_examples IS 'Comma-separated examples of what does NOT count';
COMMENT ON COLUMN scatter_behaviour_bank.measurement_type IS 'Type of measurement: frequency, duration, latency, rate';
COMMENT ON COLUMN scatter_behaviour_bank.hypothesized_function IS 'Function: attention, escape, tangible, sensory, unknown';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_behaviour_bank_category ON scatter_behaviour_bank(category);
CREATE INDEX IF NOT EXISTS idx_behaviour_bank_function ON scatter_behaviour_bank(hypothesized_function);


-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_tracking_periods (tracking periods for each student)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_tracking_periods (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_name TEXT NOT NULL,
    label TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    target_behaviours JSONB DEFAULT '[]'::jsonb,
    schedule JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_period_student FOREIGN KEY (student_name) 
        REFERENCES scatter_students(student_name) ON DELETE CASCADE
);

COMMENT ON TABLE scatter_tracking_periods IS 'Tracking periods defining which behaviours to track for each student';
COMMENT ON COLUMN scatter_tracking_periods.target_behaviours IS 'JSON array of behaviour labels for this period';
COMMENT ON COLUMN scatter_tracking_periods.schedule IS 'JSON array of time slots and activities';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_periods_student ON scatter_tracking_periods(student_name);
CREATE INDEX IF NOT EXISTS idx_periods_dates ON scatter_tracking_periods(start_date, end_date);


-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_observations (main data collection with ABA fields)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_observations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_name TEXT NOT NULL,
    obs_date DATE NOT NULL,
    day_of_week TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    activity TEXT,
    
    -- Behaviour data
    value TEXT NOT NULL,  -- "0", "1", "2", "3", "4", "5+", "X"
    behaviour_index INTEGER DEFAULT 0,
    behaviour_label TEXT,
    target_behaviours JSONB DEFAULT '[]'::jsonb,
    
    -- Context
    setting TEXT,
    grouping TEXT,
    
    -- ABA Fields
    antecedent TEXT DEFAULT '',
    consequence TEXT DEFAULT '',
    observed_function TEXT DEFAULT 'unknown',
    interventions_in_place JSONB DEFAULT '[]'::jsonb,
    setting_events TEXT DEFAULT '',
    secondary_observer TEXT DEFAULT '',
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_obs_student FOREIGN KEY (student_name) 
        REFERENCES scatter_students(student_name) ON DELETE CASCADE,
    
    -- Prevent duplicate observations for same time slot
    UNIQUE(student_name, obs_date, time_slot, behaviour_index)
);

COMMENT ON TABLE scatter_observations IS 'Scatter plot observations with ABC and context data';
COMMENT ON COLUMN scatter_observations.value IS 'Frequency: 0, 1, 2, 3, 4, 5+, or X (could not observe)';
COMMENT ON COLUMN scatter_observations.antecedent IS 'What happened immediately before the behaviour';
COMMENT ON COLUMN scatter_observations.consequence IS 'What happened immediately after the behaviour';
COMMENT ON COLUMN scatter_observations.observed_function IS 'Observed function: attention, escape, tangible, sensory, unknown';
COMMENT ON COLUMN scatter_observations.interventions_in_place IS 'JSON array of interventions that were in place';
COMMENT ON COLUMN scatter_observations.setting_events IS 'Contextual factors that may influence behaviour';
COMMENT ON COLUMN scatter_observations.secondary_observer IS 'Name of second observer for inter-observer reliability';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_obs_student_date ON scatter_observations(student_name, obs_date);
CREATE INDEX IF NOT EXISTS idx_obs_date_range ON scatter_observations(obs_date);
CREATE INDEX IF NOT EXISTS idx_obs_function ON scatter_observations(observed_function);
CREATE INDEX IF NOT EXISTS idx_obs_secondary ON scatter_observations(secondary_observer) 
    WHERE secondary_observer IS NOT NULL AND secondary_observer != '';
CREATE INDEX IF NOT EXISTS idx_obs_behaviour ON scatter_observations(behaviour_label);


-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_abc_records (detailed ABC recording)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_abc_records (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_name TEXT NOT NULL,
    obs_date DATE NOT NULL,
    time TIME NOT NULL,
    behaviour_label TEXT NOT NULL,
    
    -- Antecedent
    antecedent_category TEXT,
    antecedent TEXT,
    antecedent_detail TEXT,
    
    -- Behaviour
    behaviour_description TEXT,
    duration_seconds INTEGER,
    intensity TEXT,
    
    -- Consequence
    consequence_category TEXT,
    consequence TEXT,
    consequence_detail TEXT,
    
    -- Analysis
    observed_function TEXT DEFAULT 'unknown',
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_abc_student FOREIGN KEY (student_name) 
        REFERENCES scatter_students(student_name) ON DELETE CASCADE
);

COMMENT ON TABLE scatter_abc_records IS 'Detailed ABC (Antecedent-Behavior-Consequence) records for functional analysis';
COMMENT ON COLUMN scatter_abc_records.antecedent_category IS 'Category: Demand/Task, Social, Environmental, Internal State';
COMMENT ON COLUMN scatter_abc_records.consequence_category IS 'Category: Attention Given, Escape Provided, Tangible Delivered, Planned Consequence';
COMMENT ON COLUMN scatter_abc_records.duration_seconds IS 'Duration of behaviour episode in seconds';
COMMENT ON COLUMN scatter_abc_records.intensity IS 'Intensity level: Low, Medium, High, Severe';
COMMENT ON COLUMN scatter_abc_records.observed_function IS 'Function: attention, escape, tangible, sensory, unknown';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_abc_student_date ON scatter_abc_records(student_name, obs_date);
CREATE INDEX IF NOT EXISTS idx_abc_function ON scatter_abc_records(observed_function);
CREATE INDEX IF NOT EXISTS idx_abc_created ON scatter_abc_records(created_at);


-- ──────────────────────────────────────────────────────────────────────────
-- TABLE: scatter_daily_support (support type by day - if you use this)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scatter_daily_support (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_name TEXT NOT NULL,
    obs_date DATE NOT NULL,
    support_type TEXT,
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_support_student FOREIGN KEY (student_name) 
        REFERENCES scatter_students(student_name) ON DELETE CASCADE,
    
    UNIQUE(student_name, obs_date)
);

COMMENT ON TABLE scatter_daily_support IS 'Support level provided each day';

CREATE INDEX IF NOT EXISTS idx_support_student_date ON scatter_daily_support(student_name, obs_date);


-- ══════════════════════════════════════════════════════════════════════════
-- PART 2: UPDATED_AT TRIGGERS
-- ══════════════════════════════════════════════════════════════════════════

-- Create or replace the trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to all tables with updated_at
DROP TRIGGER IF EXISTS set_updated_at ON scatter_students;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON scatter_students
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_updated_at ON scatter_behaviour_bank;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON scatter_behaviour_bank
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_updated_at ON scatter_tracking_periods;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON scatter_tracking_periods
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_updated_at ON scatter_observations;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON scatter_observations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_updated_at ON scatter_abc_records;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON scatter_abc_records
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ══════════════════════════════════════════════════════════════════════════
-- PART 3: ROW LEVEL SECURITY (RLS)
-- ══════════════════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE scatter_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE scatter_behaviour_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE scatter_tracking_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE scatter_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE scatter_abc_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE scatter_daily_support ENABLE ROW LEVEL SECURITY;

-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_students
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read students" ON scatter_students;
DROP POLICY IF EXISTS "Allow authenticated users to insert students" ON scatter_students;
DROP POLICY IF EXISTS "Allow authenticated users to update students" ON scatter_students;
DROP POLICY IF EXISTS "Allow authenticated users to delete students" ON scatter_students;

CREATE POLICY "Allow all authenticated users to read students"
ON scatter_students FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert students"
ON scatter_students FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update students"
ON scatter_students FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete students"
ON scatter_students FOR DELETE TO authenticated USING (true);


-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_behaviour_bank
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read behaviour bank" ON scatter_behaviour_bank;
DROP POLICY IF EXISTS "Allow authenticated users to insert behaviours" ON scatter_behaviour_bank;
DROP POLICY IF EXISTS "Allow authenticated users to update behaviours" ON scatter_behaviour_bank;
DROP POLICY IF EXISTS "Allow authenticated users to delete custom behaviours" ON scatter_behaviour_bank;

CREATE POLICY "Allow all authenticated users to read behaviour bank"
ON scatter_behaviour_bank FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert behaviours"
ON scatter_behaviour_bank FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update behaviours"
ON scatter_behaviour_bank FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete custom behaviours"
ON scatter_behaviour_bank FOR DELETE TO authenticated USING (is_custom = true);


-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_tracking_periods
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read periods" ON scatter_tracking_periods;
DROP POLICY IF EXISTS "Allow authenticated users to insert periods" ON scatter_tracking_periods;
DROP POLICY IF EXISTS "Allow authenticated users to update periods" ON scatter_tracking_periods;
DROP POLICY IF EXISTS "Allow authenticated users to delete periods" ON scatter_tracking_periods;

CREATE POLICY "Allow all authenticated users to read periods"
ON scatter_tracking_periods FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert periods"
ON scatter_tracking_periods FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update periods"
ON scatter_tracking_periods FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete periods"
ON scatter_tracking_periods FOR DELETE TO authenticated USING (true);


-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_observations
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read observations" ON scatter_observations;
DROP POLICY IF EXISTS "Allow authenticated users to insert observations" ON scatter_observations;
DROP POLICY IF EXISTS "Allow authenticated users to update observations" ON scatter_observations;
DROP POLICY IF EXISTS "Allow authenticated users to delete observations" ON scatter_observations;

CREATE POLICY "Allow all authenticated users to read observations"
ON scatter_observations FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert observations"
ON scatter_observations FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update observations"
ON scatter_observations FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete observations"
ON scatter_observations FOR DELETE TO authenticated USING (true);


-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_abc_records
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read ABC records" ON scatter_abc_records;
DROP POLICY IF EXISTS "Allow authenticated users to insert ABC records" ON scatter_abc_records;
DROP POLICY IF EXISTS "Allow users to update their own ABC records" ON scatter_abc_records;
DROP POLICY IF EXISTS "Allow users to delete their own ABC records" ON scatter_abc_records;

CREATE POLICY "Allow all authenticated users to read ABC records"
ON scatter_abc_records FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert ABC records"
ON scatter_abc_records FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow users to update their own ABC records"
ON scatter_abc_records FOR UPDATE TO authenticated 
USING (created_by = auth.jwt() ->> 'email')
WITH CHECK (created_by = auth.jwt() ->> 'email');

CREATE POLICY "Allow users to delete their own ABC records"
ON scatter_abc_records FOR DELETE TO authenticated 
USING (created_by = auth.jwt() ->> 'email');


-- ──────────────────────────────────────────────────────────────────────────
-- RLS Policies: scatter_daily_support
-- ──────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow all authenticated users to read support" ON scatter_daily_support;
DROP POLICY IF EXISTS "Allow authenticated users to insert support" ON scatter_daily_support;
DROP POLICY IF EXISTS "Allow authenticated users to update support" ON scatter_daily_support;
DROP POLICY IF EXISTS "Allow authenticated users to delete support" ON scatter_daily_support;

CREATE POLICY "Allow all authenticated users to read support"
ON scatter_daily_support FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert support"
ON scatter_daily_support FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update support"
ON scatter_daily_support FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete support"
ON scatter_daily_support FOR DELETE TO authenticated USING (true);


-- ══════════════════════════════════════════════════════════════════════════
-- PART 4: SEED DATA (optional - populate behaviour bank with common behaviours)
-- ══════════════════════════════════════════════════════════════════════════

-- Insert common behaviours into bank (only if table is empty)
INSERT INTO scatter_behaviour_bank (category, description, operational_definition, examples, non_examples, hypothesized_function)
SELECT * FROM (VALUES
    -- Physical - peer directed
    ('Physical — peer directed', 'Hitting', 
     'Making contact with peer using hand (open or closed) with force', 
     'Slapping peer on arm, punching peer, hitting with fist', 
     'Accidental contact, light tap to get attention, high-five',
     'attention'),
    
    ('Physical — peer directed', 'Pushing', 
     'Using hands, arms, or body to forcefully move a peer', 
     'Pushing peer away from materials, shoving in line, pushing peer off chair', 
     'Gently guiding peer, moving past peer in crowded space',
     'escape'),
    
    ('Physical — peer directed', 'Kicking', 
     'Making contact with peer using foot or leg with force', 
     'Kicking peer under table, kicking at peer during transition', 
     'Accidental contact, stretching legs',
     'attention'),
    
    -- Physical - adult directed
    ('Physical — adult directed', 'Hitting adult', 
     'Making contact with adult using hand (open or closed) with force', 
     'Hitting teacher, striking SSO', 
     'High-five, reaching for adult assistance',
     'escape'),
    
    -- Self-injurious
    ('Self-injurious', 'Self-hitting', 
     'Making forceful contact with own body using hand, fist, or object', 
     'Hitting own head with hand, hitting head on table', 
     'Scratching itch, wiping face',
     'sensory'),
    
    -- Property / environment
    ('Property / environment', 'Throwing objects', 
     'Propelling objects through the air with force', 
     'Throwing books, tossing chair, hurling materials across room', 
     'Passing items, placing items down quickly, dropping accidentally',
     'escape'),
    
    ('Property / environment', 'Property destruction', 
     'Damaging or breaking materials or furniture', 
     'Tearing books, breaking pencils, ripping papers, scratching walls', 
     'Accidental damage, age-appropriate rough handling',
     'escape'),
    
    -- Elopement / movement
    ('Elopement / movement', 'Leaving assigned area', 
     'Moving beyond designated boundaries without permission', 
     'Leaving classroom without teacher, exiting playground area, wandering away from group', 
     'Transitioning with class, returning materials to shelf',
     'escape'),
    
    -- Verbal
    ('Verbal', 'Yelling', 
     'Speaking at volume significantly louder than conversational tone', 
     'Shouting across room, screaming during instruction, loud vocalizations', 
     'Excited voice during play, calling out to get attention from distance',
     'attention'),
    
    ('Verbal', 'Swearing', 
     'Using profanity or socially inappropriate language', 
     'F-word, curse words, explicit language directed at others', 
     'Repeating overheard language without understanding, song lyrics',
     'attention'),
    
    ('Verbal', 'Verbal threats', 
     'Statements expressing intent to harm self, others, or property', 
     'I will hit you, I am going to break that, I will hurt myself', 
     'Expressing frustration without specific threat, I dont like this',
     'escape'),
    
    -- Refusal / non-compliance
    ('Refusal / non-compliance', 'Task refusal', 
     'Verbal or physical refusal to begin or continue assigned task', 
     'Saying no to instruction, pushing materials away, stating I wont do this', 
     'Asking for help, requesting break, asking for clarification',
     'escape'),
    
    ('Refusal / non-compliance', 'Non-response to direction', 
     'Absence of response to direct instruction after 10 seconds', 
     'Teacher says pack up, student continues current activity with no acknowledgment', 
     'Student didnt hear, student is processing direction',
     'escape'),
    
    -- Dysregulation / other
    ('Dysregulation / other', 'Prolonged crying', 
     'Crying lasting 2+ minutes with visible tears or sobbing sounds', 
     'Sustained crying during task, crying after correction', 
     'Brief tears, watery eyes, crying after injury',
     'escape')
) AS v(category, description, operational_definition, examples, non_examples, hypothesized_function)
WHERE NOT EXISTS (SELECT 1 FROM scatter_behaviour_bank WHERE description = v.description);


-- ══════════════════════════════════════════════════════════════════════════
-- PART 5: VALIDATION
-- ══════════════════════════════════════════════════════════════════════════

-- Check tables were created
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name LIKE 'scatter_%'
ORDER BY table_name;

-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename LIKE 'scatter_%'
ORDER BY tablename;

-- Check behaviour bank has seed data
SELECT category, COUNT(*) as behaviour_count
FROM scatter_behaviour_bank
GROUP BY category
ORDER BY category;

-- Check policies exist
SELECT tablename, COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
AND tablename LIKE 'scatter_%'
GROUP BY tablename
ORDER BY tablename;


-- ══════════════════════════════════════════════════════════════════════════
-- SETUP COMPLETE!
-- ══════════════════════════════════════════════════════════════════════════

-- Summary of what was created:
-- ✅ 6 tables: students, behaviour_bank, tracking_periods, observations, abc_records, daily_support
-- ✅ All ABA fields included: operational definitions, ABC, functions, IOA
-- ✅ RLS policies on all tables
-- ✅ Indexes for performance
-- ✅ Updated_at triggers
-- ✅ Seed data with 14 common behaviours (with operational definitions)
-- ✅ Foreign key relationships

-- Next steps:
-- 1. Add your students via Portal Admin or:
--    INSERT INTO scatter_students (student_name, program_type) VALUES ('Student Name', 'PY');
-- 
-- 2. Create tracking periods via Portal Admin or:
--    INSERT INTO scatter_tracking_periods (student_name, label, start_date, target_behaviours, schedule)
--    VALUES ('Student Name', 'Term 2', '2026-05-01', '["Hitting", "Task refusal"]', '[...]');
--
-- 3. Deploy the new Streamlit file (18_Scatter_Plot_Tracker_ABA.py)
--
-- 4. Start collecting data with ABA standards!
