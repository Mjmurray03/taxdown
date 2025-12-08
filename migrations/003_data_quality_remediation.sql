-- Taxdown - Data Quality Remediation
-- Migration: 003_data_quality_remediation.sql
-- Created: 2025-12-08
-- Description: Cleans up 2,697 properties without parcel_id from parcels_enriched.parquet
--
-- FINDINGS FROM ANALYSIS:
-- =======================
-- Total properties: 173,743
-- Properties without parcel_id: 2,697 (1.55%)
-- Properties with parcel_id: 171,046 (98.45%)
--
-- All 2,697 missing parcel_id records came from: parcels_enriched.parquet
--
-- Breakdown of records without parcel_id:
-- - 2,478 records: Empty placeholder records (no address, no owner, value=0)
--   These are duplicates of the same empty record with different geometries
-- - 175 records: Legitimate properties with addresses but duplicated 2-4 times each
--   (79 unique combinations × ~2 duplicates each = 158 records)
--   (3 unique combinations × 3 duplicates = 9 records)
--   (2 unique combinations × 4 duplicates = 8 records)
-- - Some high-value properties included (e.g., Walmart $72M property appears twice)
--
-- REMEDIATION STRATEGY:
-- =====================
-- 1. DELETE all 2,478 empty placeholder records (no address, no owner, zero value)
--    - These provide no useful data and appear to be geocoding artifacts
-- 2. DEDUPLICATE the remaining 219 records to keep only one per unique combination
--    - Keep the record with the smallest uuid (deterministic selection)
-- 3. RETAIN records where synthetic_parcel_id exists as the unique identifier
--
-- IMPACT:
-- - Records deleted: ~2,600 (empty + duplicates)
-- - Records retained: ~84 unique properties with synthetic_parcel_id
-- - Final property count: ~171,130 (vs 173,743 before)
-- - Data quality improvement: All remaining records have valid identifiers

BEGIN;

-- ============================================================================
-- STEP 1: Create audit table to track what was removed
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_quality_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remediation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    issue_type VARCHAR(100) NOT NULL,
    records_affected INTEGER NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    details JSONB
);

-- ============================================================================
-- STEP 2: Record baseline metrics
-- ============================================================================
INSERT INTO data_quality_audit (issue_type, records_affected, action_taken, details)
SELECT
    'baseline_metrics',
    COUNT(*),
    'recorded',
    jsonb_build_object(
        'total_properties', COUNT(*),
        'with_parcel_id', COUNT(NULLIF(parcel_id, '')),
        'without_parcel_id', COUNT(*) - COUNT(NULLIF(parcel_id, '')),
        'with_synthetic_id', COUNT(NULLIF(synthetic_parcel_id, ''))
    )
FROM properties;

-- ============================================================================
-- STEP 3: Delete empty placeholder records
-- Records with: no parcel_id, no address, no owner, zero value
-- ============================================================================

-- First, log what we're deleting
INSERT INTO data_quality_audit (issue_type, records_affected, action_taken, details)
SELECT
    'empty_placeholder_records',
    COUNT(*),
    'deleted',
    jsonb_build_object(
        'criteria', 'no parcel_id AND (no address OR no owner) AND zero value',
        'source_file', 'parcels_enriched.parquet'
    )
FROM properties
WHERE (parcel_id IS NULL OR parcel_id = '')
  AND (ph_add IS NULL OR ph_add = '')
  AND (ow_name IS NULL OR ow_name = '')
  AND (total_val_cents IS NULL OR total_val_cents = 0);

-- Delete the empty records
DELETE FROM properties
WHERE (parcel_id IS NULL OR parcel_id = '')
  AND (ph_add IS NULL OR ph_add = '')
  AND (ow_name IS NULL OR ow_name = '')
  AND (total_val_cents IS NULL OR total_val_cents = 0);

-- ============================================================================
-- STEP 4: Deduplicate remaining records without parcel_id
-- Keep only one record per unique (ph_add, ow_name, total_val_cents) combination
-- ============================================================================

-- Log duplicates before deletion
INSERT INTO data_quality_audit (issue_type, records_affected, action_taken, details)
SELECT
    'duplicate_synthetic_records',
    COUNT(*) - COUNT(DISTINCT (COALESCE(ph_add,'') || COALESCE(ow_name,'') || COALESCE(total_val_cents::text,''))),
    'deleted',
    jsonb_build_object(
        'unique_combinations', COUNT(DISTINCT (COALESCE(ph_add,'') || COALESCE(ow_name,'') || COALESCE(total_val_cents::text,''))),
        'total_records_before', COUNT(*),
        'duplicates_removed', COUNT(*) - COUNT(DISTINCT (COALESCE(ph_add,'') || COALESCE(ow_name,'') || COALESCE(total_val_cents::text,'')))
    )
FROM properties
WHERE (parcel_id IS NULL OR parcel_id = '');

-- Delete duplicates, keeping the one with smallest id (deterministic)
DELETE FROM properties p1
WHERE (p1.parcel_id IS NULL OR p1.parcel_id = '')
  AND EXISTS (
    SELECT 1 FROM properties p2
    WHERE (p2.parcel_id IS NULL OR p2.parcel_id = '')
      AND COALESCE(p1.ph_add,'') = COALESCE(p2.ph_add,'')
      AND COALESCE(p1.ow_name,'') = COALESCE(p2.ow_name,'')
      AND COALESCE(p1.total_val_cents,0) = COALESCE(p2.total_val_cents,0)
      AND p2.id < p1.id  -- Keep the record with smaller UUID
  );

-- ============================================================================
-- STEP 5: Flag remaining records without parcel_id with lower data quality score
-- ============================================================================
UPDATE properties
SET data_quality_score = LEAST(COALESCE(data_quality_score, 100), 50)
WHERE (parcel_id IS NULL OR parcel_id = '');

-- Log the update
INSERT INTO data_quality_audit (issue_type, records_affected, action_taken, details)
SELECT
    'synthetic_id_only_records',
    COUNT(*),
    'quality_score_reduced',
    jsonb_build_object(
        'new_quality_score', 50,
        'reason', 'Using synthetic_parcel_id instead of official parcel_id'
    )
FROM properties
WHERE (parcel_id IS NULL OR parcel_id = '');

-- ============================================================================
-- STEP 6: Record final metrics
-- ============================================================================
INSERT INTO data_quality_audit (issue_type, records_affected, action_taken, details)
SELECT
    'final_metrics',
    COUNT(*),
    'recorded',
    jsonb_build_object(
        'total_properties', COUNT(*),
        'with_parcel_id', COUNT(NULLIF(parcel_id, '')),
        'without_parcel_id', COUNT(*) - COUNT(NULLIF(parcel_id, '')),
        'with_synthetic_id', COUNT(NULLIF(synthetic_parcel_id, '')),
        'parcel_coverage_pct', ROUND(COUNT(NULLIF(parcel_id, ''))::numeric / COUNT(*)::numeric * 100, 2)
    )
FROM properties;

-- ============================================================================
-- STEP 7: Add constraint to prevent future empty records
-- ============================================================================
ALTER TABLE properties
ADD CONSTRAINT chk_valid_identifier
CHECK (
    (parcel_id IS NOT NULL AND parcel_id <> '')
    OR (synthetic_parcel_id IS NOT NULL AND synthetic_parcel_id <> '')
);

-- ============================================================================
-- STEP 8: Create index on synthetic_parcel_id for faster lookups
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_properties_synthetic_parcel_id
ON properties(synthetic_parcel_id)
WHERE synthetic_parcel_id IS NOT NULL AND synthetic_parcel_id <> '';

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run after migration)
-- ============================================================================
-- SELECT * FROM data_quality_audit ORDER BY remediation_date;
--
-- SELECT
--     COUNT(*) as total,
--     COUNT(NULLIF(parcel_id, '')) as with_parcel,
--     COUNT(*) - COUNT(NULLIF(parcel_id, '')) as without_parcel,
--     ROUND(COUNT(NULLIF(parcel_id, ''))::numeric / COUNT(*)::numeric * 100, 2) as coverage_pct
-- FROM properties;
