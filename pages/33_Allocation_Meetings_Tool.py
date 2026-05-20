-- ========================================================================
-- QUICK FIX: Reload PostgREST Schema Cache
-- ========================================================================
-- Error: PGRST204 - "Could not find column in schema cache"
-- Solution: Force PostgREST to reload the schema
-- ========================================================================

-- Run this single command:
NOTIFY pgrst, 'reload schema';

-- That's it! The schema cache will refresh in 1-2 seconds.

-- ========================================================================
-- VERIFICATION (optional):
-- ========================================================================

-- Check that the columns exist in the actual table:
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'allocation_students'
AND column_name IN ('previously_referred', 'medical_condition_details')
ORDER BY column_name;

-- Expected output:
-- medical_condition_details | text
-- previously_referred       | text

-- ========================================================================
-- DONE!
-- ========================================================================
-- After running NOTIFY pgrst, wait 5 seconds then try saving a draft again.
-- The error should be gone!
-- ========================================================================
