-- ============================================================================
-- CLC-LBU Committee Members Database Setup
-- Run this in your Supabase SQL Editor
-- Tables: committee_roles and committee_role_members (to avoid naming conflicts)
-- ============================================================================

-- Create committee_roles table
CREATE TABLE IF NOT EXISTS committee_roles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create committee_role_members table
CREATE TABLE IF NOT EXISTS committee_role_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    committee_id UUID REFERENCES committee_roles(id) ON DELETE CASCADE,
    staff_name TEXT NOT NULL,
    role TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(committee_id, staff_name, role)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_committee_role_members_committee 
    ON committee_role_members(committee_id);
CREATE INDEX IF NOT EXISTS idx_committee_roles_display_order 
    ON committee_roles(display_order);
CREATE INDEX IF NOT EXISTS idx_committee_role_members_display_order 
    ON committee_role_members(display_order);

-- Enable Row Level Security
ALTER TABLE committee_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE committee_role_members ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow read for authenticated users" ON committee_roles;
DROP POLICY IF EXISTS "Allow read for authenticated users" ON committee_role_members;
DROP POLICY IF EXISTS "Allow all for service role" ON committee_roles;
DROP POLICY IF EXISTS "Allow all for service role" ON committee_role_members;

-- Create RLS policies
CREATE POLICY "Allow read for authenticated users" ON committee_roles
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow read for authenticated users" ON committee_role_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for service role" ON committee_roles
    FOR ALL USING (true);

CREATE POLICY "Allow all for service role" ON committee_role_members
    FOR ALL USING (true);

-- ============================================================================
-- Insert default committee roles and members
-- ============================================================================

-- PAC Committee
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('PAC', 'Partnership & Cooperation Committee', 0)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Candice', 'Leader', 0
FROM committee_roles c WHERE c.name = 'PAC'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Naomi', 'SSO rep', 1
FROM committee_roles c WHERE c.name = 'PAC'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben', 'AEU Rep', 2
FROM committee_roles c WHERE c.name = 'PAC'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Brenton', 'Teacher Rep', 3
FROM committee_roles c WHERE c.name = 'PAC'
ON CONFLICT DO NOTHING;

-- WHS Committee
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('WHS', 'Work Health & Safety', 1)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Candice', 'OHS Rep', 0
FROM committee_roles c WHERE c.name = 'WHS'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Naomi', '', 1
FROM committee_roles c WHERE c.name = 'WHS'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben Selga', '', 2
FROM committee_roles c WHERE c.name = 'WHS'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Caitie', '', 3
FROM committee_roles c WHERE c.name = 'WHS'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Roisin', '', 4
FROM committee_roles c WHERE c.name = 'WHS'
ON CONFLICT DO NOTHING;

-- Social Club
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('Social Club', '', 2)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben Sutton', '', 0
FROM committee_roles c WHERE c.name = 'Social Club'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Vinnie', '', 1
FROM committee_roles c WHERE c.name = 'Social Club'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Jacqui', '', 2
FROM committee_roles c WHERE c.name = 'Social Club'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Annette', '', 3
FROM committee_roles c WHERE c.name = 'Social Club'
ON CONFLICT DO NOTHING;

-- Centre Spec Events
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('Centre Spec Events', 'Centre Special Events', 3)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Brenton', '', 0
FROM committee_roles c WHERE c.name = 'Centre Spec Events'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben Selga', '', 1
FROM committee_roles c WHERE c.name = 'Centre Spec Events'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Annette', '', 2
FROM committee_roles c WHERE c.name = 'Centre Spec Events'
ON CONFLICT DO NOTHING;

-- Leaving Gift
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('Leaving Gift', '', 4)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Caitie', '', 0
FROM committee_roles c WHERE c.name = 'Leaving Gift'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Jacqui', '', 1
FROM committee_roles c WHERE c.name = 'Leaving Gift'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Annette', '', 2
FROM committee_roles c WHERE c.name = 'Leaving Gift'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Candice', '', 3
FROM committee_roles c WHERE c.name = 'Leaving Gift'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Naomi', '', 4
FROM committee_roles c WHERE c.name = 'Leaving Gift'
ON CONFLICT DO NOTHING;

-- OHS
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('OHS', 'Occupational Health & Safety', 5)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Roisin', 'Proxy', 0
FROM committee_roles c WHERE c.name = 'OHS'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Caitie', 'Proxy', 1
FROM committee_roles c WHERE c.name = 'OHS'
ON CONFLICT DO NOTHING;

-- AEU
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('AEU', 'Australian Education Union', 6)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Roisin', 'Proxy', 0
FROM committee_roles c WHERE c.name = 'AEU'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben Sutton', 'Proxy', 1
FROM committee_roles c WHERE c.name = 'AEU'
ON CONFLICT DO NOTHING;

-- Fire Warden
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('Fire Warden', '', 7)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Brenton', '', 0
FROM committee_roles c WHERE c.name = 'Fire Warden'
ON CONFLICT DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Ben Selga', '', 1
FROM committee_roles c WHERE c.name = 'Fire Warden'
ON CONFLICT DO NOTHING;

-- First Aid Officer
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('First Aid Officer', '', 8)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Naomi', '', 0
FROM committee_roles c WHERE c.name = 'First Aid Officer'
ON CONFLICT DO NOTHING;

-- 3P Learning Coordinator
INSERT INTO committee_roles (name, description, display_order) 
VALUES ('3P Learning Coordinator', '', 9)
ON CONFLICT (name) DO NOTHING;

INSERT INTO committee_role_members (committee_id, staff_name, role, display_order)
SELECT c.id, 'Caitie', '', 0
FROM committee_roles c WHERE c.name = '3P Learning Coordinator'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Verify the data
-- ============================================================================

SELECT 'Committee roles created:' as status, COUNT(*) as count FROM committee_roles;
SELECT 'Committee role members created:' as status, COUNT(*) as count FROM committee_role_members;

-- View all committee roles with their members
SELECT 
    c.name as committee,
    c.description,
    cm.staff_name,
    cm.role,
    cm.display_order
FROM committee_roles c
LEFT JOIN committee_role_members cm ON c.id = cm.committee_id
ORDER BY c.display_order, cm.display_order;
