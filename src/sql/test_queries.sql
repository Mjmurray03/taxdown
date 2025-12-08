-- ============================================================================
-- TEST QUERIES FOR ASSESSMENT ANALYSIS SYSTEM
-- ============================================================================
-- PostgreSQL + PostGIS
-- Purpose: Validate functions and analyze query performance
--
-- USAGE:
--   1. Ensure schema_setup.sql has been run
--   2. Ensure comparable_matching.sql has been loaded
--   3. Ensure assessment_analytics.sql has been loaded
--   4. Update sample parcel IDs below with actual data from your database
--   5. Run tests: \i test_queries.sql
-- ============================================================================

\timing on
\x auto

-- Set display settings
SET client_min_messages = NOTICE;

-- ============================================================================
-- 1. DATA VALIDATION TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '1. DATA VALIDATION TESTS'
\echo '============================================'
\echo ''

-- Test 1.1: Check record count
\echo 'Test 1.1: Total record count'
SELECT COUNT(*) AS total_parcels FROM properties;

-- Test 1.2: Check data completeness
\echo ''
\echo 'Test 1.2: Data completeness check'
SELECT
    COUNT(*) AS total_records,
    COUNT(parcel_id) AS has_parcel_id,
    COUNT(type_) AS has_type,
    COUNT(total_val_cents) AS has_total_val_cents,
    COUNT(assess_val_cents) AS has_assess_val_cents,
    COUNT(geometry) AS has_geometry,
    COUNT(*) FILTER (WHERE total_val_cents > 0) AS valid_total_val_cents,
    COUNT(*) FILTER (WHERE assess_val_cents > 0) AS valid_assess_val_cents,
    COUNT(*) FILTER (WHERE subdivname IS NOT NULL) AS has_subdivision,
    COUNT(*) FILTER (WHERE s_t_r IS NOT NULL) AS has_str,
    ROUND(100.0 * COUNT(*) FILTER (WHERE total_val_cents > 0 AND assess_val_cents > 0) / COUNT(*), 2) AS pct_usable
FROM properties;

-- Test 1.3: Property type distribution
\echo ''
\echo 'Test 1.3: Property type distribution'
SELECT
    type_ AS property_type,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage,
    ROUND(AVG(total_val_cents), 0) AS avg_total_value,
    ROUND(AVG(acre_area), 2) AS avg_acreage
FROM properties
WHERE type_ IS NOT NULL
GROUP BY type_
ORDER BY count DESC;

-- Test 1.4: Value distribution
\echo ''
\echo 'Test 1.4: Value distribution (quartiles)'
SELECT
    ROUND(PERCENTILE_CONT(0.00) WITHIN GROUP (ORDER BY total_val_cents), 0) AS min_value,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY total_val_cents), 0) AS q1_value,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_val_cents), 0) AS median_value,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY total_val_cents), 0) AS q3_value,
    ROUND(PERCENTILE_CONT(1.00) WITHIN GROUP (ORDER BY total_val_cents), 0) AS max_value,
    ROUND(AVG(total_val_cents), 0) AS mean_value
FROM properties
WHERE total_val_cents > 0;

-- Test 1.5: Spatial data validation
\echo ''
\echo 'Test 1.5: Spatial data validation'
SELECT
    COUNT(*) AS total_parcels,
    COUNT(*) FILTER (WHERE geometry IS NOT NULL) AS has_geometry,
    COUNT(*) FILTER (WHERE ST_IsValid(geometry)) AS valid_geometries,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geometry)) AS invalid_geometries,
    COUNT(*) FILTER (WHERE ST_GeometryType(geometry) = 'ST_MultiPolygon') AS multipolygons,
    ST_SRID(geometry) AS coordinate_system
FROM properties
WHERE geometry IS NOT NULL
LIMIT 1;

-- ============================================================================
-- 2. INDEX VERIFICATION
-- ============================================================================

\echo ''
\echo '============================================'
\echo '2. INDEX VERIFICATION'
\echo '============================================'
\echo ''

-- Test 2.1: List all indexes
\echo 'Test 2.1: Indexes on properties table'
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'properties'
ORDER BY indexname;

-- Test 2.2: Index usage statistics (if available)
\echo ''
\echo 'Test 2.2: Index usage statistics'
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'properties'
ORDER BY idx_scan DESC;

-- ============================================================================
-- 3. FUNCTION EXISTENCE TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '3. FUNCTION EXISTENCE TESTS'
\echo '============================================'
\echo ''

-- Test 3.1: Check if all functions exist
\echo 'Test 3.1: Check if all functions exist'
SELECT
    proname AS function_name,
    pronargs AS argument_count,
    prorettype::regtype AS return_type
FROM pg_proc
WHERE proname IN (
    'find_comparable_properties',
    'get_neighborhood_median_ratio',
    'get_subdivision_median_ratio',
    'get_property_percentile_ranking'
)
ORDER BY proname;

-- Test 3.2: Check if views exist
\echo ''
\echo 'Test 3.2: Check if views exist'
SELECT
    viewname,
    definition
FROM pg_views
WHERE viewname IN (
    'v_assessment_fairness_summary',
    'v_top_over_assessed_properties'
)
ORDER BY viewname;

-- ============================================================================
-- 4. SAMPLE PARCEL SELECTION
-- ============================================================================

\echo ''
\echo '============================================'
\echo '4. SAMPLE PARCEL SELECTION'
\echo '============================================'
\echo ''

-- Get sample parcel IDs for testing
\echo 'Test 4.1: Select sample parcels for testing'

-- Create temporary table with test parcels
DROP TABLE IF EXISTS test_parcels;

CREATE TEMP TABLE test_parcels AS
SELECT
    parcel_id,
    type_,
    total_val_cents,
    assess_val_cents,
    acre_area,
    subdivname,
    s_t_r
FROM properties
WHERE total_val_cents > 0
    AND assess_val_cents > 0
    AND acre_area > 0
    AND type_ IS NOT NULL
    AND geometry IS NOT NULL
ORDER BY RANDOM()
LIMIT 5;

\echo 'Sample test parcels:'
SELECT * FROM test_parcels;

-- ============================================================================
-- 5. COMPARABLE PROPERTY MATCHING TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '5. COMPARABLE PROPERTY MATCHING TESTS'
\echo '============================================'
\echo ''

-- Test 5.1: Find comparables for first test parcel
\echo 'Test 5.1: Find comparables for sample parcel'
DO $$
DECLARE
    v_test_parcel VARCHAR;
BEGIN
    SELECT parcel_id INTO v_test_parcel FROM test_parcels LIMIT 1;
    RAISE NOTICE 'Testing with parcel: %', v_test_parcel;

    PERFORM * FROM find_comparable_properties(v_test_parcel);

    IF FOUND THEN
        RAISE NOTICE 'SUCCESS: Comparable properties found';
    ELSE
        RAISE WARNING 'No comparable properties found for parcel: %', v_test_parcel;
    END IF;
END $$;

SELECT * FROM find_comparable_properties((SELECT parcel_id FROM test_parcels LIMIT 1));

-- Test 5.2: Verify similarity score calculation
\echo ''
\echo 'Test 5.2: Similarity score statistics'
WITH comparables AS (
    SELECT * FROM find_comparable_properties((SELECT parcel_id FROM test_parcels LIMIT 1))
)
SELECT
    COUNT(*) AS comparable_count,
    ROUND(AVG(similarity_score), 2) AS avg_similarity_score,
    ROUND(MIN(similarity_score), 2) AS min_similarity_score,
    ROUND(MAX(similarity_score), 2) AS max_similarity_score,
    COUNT(*) FILTER (WHERE match_type = 'SUBDIVISION') AS subdivision_matches,
    COUNT(*) FILTER (WHERE match_type = 'PROXIMITY') AS proximity_matches
FROM comparables;

-- Test 5.3: Query performance analysis
\echo ''
\echo 'Test 5.3: Comparable matching query performance'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM find_comparable_properties((SELECT parcel_id FROM test_parcels LIMIT 1));

-- ============================================================================
-- 6. NEIGHBORHOOD MEDIAN TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '6. NEIGHBORHOOD MEDIAN TESTS'
\echo '============================================'
\echo ''

-- Test 6.1: Get neighborhood median for sample parcel
\echo 'Test 6.1: Neighborhood median calculation'
SELECT * FROM get_neighborhood_median_ratio((SELECT parcel_id FROM test_parcels LIMIT 1));

-- Test 6.2: Verify statistical calculations
\echo ''
\echo 'Test 6.2: Neighborhood statistics validation'
WITH median_result AS (
    SELECT * FROM get_neighborhood_median_ratio((SELECT parcel_id FROM test_parcels LIMIT 1))
)
SELECT
    neighborhood_code,
    property_count,
    median_assessment_ratio,
    avg_assessment_ratio,
    target_property_ratio,
    target_vs_median_diff,
    CASE
        WHEN ABS(target_vs_median_diff) <= 5 THEN 'FAIR'
        WHEN target_vs_median_diff > 5 THEN 'OVER_ASSESSED'
        ELSE 'UNDER_ASSESSED'
    END AS assessment_status
FROM median_result;

-- Test 6.3: Query performance
\echo ''
\echo 'Test 6.3: Neighborhood median query performance'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_neighborhood_median_ratio((SELECT parcel_id FROM test_parcels LIMIT 1));

-- ============================================================================
-- 7. SUBDIVISION MEDIAN TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '7. SUBDIVISION MEDIAN TESTS'
\echo '============================================'
\echo ''

-- Test 7.1: Get subdivision median (if parcel has subdivision)
\echo 'Test 7.1: Subdivision median calculation'
SELECT * FROM get_subdivision_median_ratio((
    SELECT parcel_id FROM test_parcels WHERE subdivname IS NOT NULL LIMIT 1
));

-- Test 7.2: Compare neighborhood vs subdivision statistics
\echo ''
\echo 'Test 7.2: Neighborhood vs Subdivision comparison'
WITH test_parcel AS (
    SELECT parcel_id FROM test_parcels WHERE subdivname IS NOT NULL LIMIT 1
),
neighborhood AS (
    SELECT * FROM get_neighborhood_median_ratio((SELECT parcel_id FROM test_parcel))
),
subdivision AS (
    SELECT * FROM get_subdivision_median_ratio((SELECT parcel_id FROM test_parcel))
)
SELECT
    'Neighborhood' AS scope,
    n.property_count,
    n.median_assessment_ratio,
    n.target_vs_median_diff
FROM neighborhood n
UNION ALL
SELECT
    'Subdivision' AS scope,
    s.property_count,
    s.median_assessment_ratio,
    s.target_vs_median_diff
FROM subdivision s;

-- ============================================================================
-- 8. PERCENTILE RANKING TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '8. PERCENTILE RANKING TESTS'
\echo '============================================'
\echo ''

-- Test 8.1: Get percentile ranking for sample parcel
\echo 'Test 8.1: Percentile ranking calculation'
SELECT
    parcel_id,
    total_value,
    assessment_ratio,
    neighborhood_percentile,
    subdivision_percentile,
    type_percentile,
    fairness_category,
    potential_savings_indicator,
    is_over_assessed,
    is_under_assessed
FROM get_property_percentile_ranking((SELECT parcel_id FROM test_parcels LIMIT 1));

-- Test 8.2: Verify percentile logic
\echo ''
\echo 'Test 8.2: Percentile ranking validation'
WITH ranking AS (
    SELECT * FROM get_property_percentile_ranking((SELECT parcel_id FROM test_parcels LIMIT 1))
)
SELECT
    parcel_id,
    neighborhood_rank || ' of ' || neighborhood_property_count AS neighborhood_position,
    ROUND(neighborhood_percentile, 1) || '%' AS neighborhood_pct,
    subdivision_rank || ' of ' || subdivision_property_count AS subdivision_position,
    ROUND(subdivision_percentile, 1) || '%' AS subdivision_pct,
    fairness_category
FROM ranking;

-- Test 8.3: Query performance
\echo ''
\echo 'Test 8.3: Percentile ranking query performance'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_property_percentile_ranking((SELECT parcel_id FROM test_parcels LIMIT 1));

-- ============================================================================
-- 9. ASSESSMENT FAIRNESS VIEW TESTS
-- ============================================================================

\echo ''
\echo '============================================'
\echo '9. ASSESSMENT FAIRNESS VIEW TESTS'
\echo '============================================'
\echo ''

-- Test 9.1: Sample data from fairness summary view
\echo 'Test 9.1: Sample assessment fairness summary'
SELECT
    parcel_id,
    property_type,
    total_value,
    assessment_ratio,
    neighborhood_median_ratio,
    neighborhood_ratio_diff,
    appeal_priority,
    potential_assessment_reduction
FROM v_assessment_fairness_summary
WHERE total_value > 50000
ORDER BY potential_assessment_reduction DESC
LIMIT 10;

-- Test 9.2: Appeal priority distribution
\echo ''
\echo 'Test 9.2: Appeal priority distribution'
SELECT
    appeal_priority,
    COUNT(*) AS property_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage,
    ROUND(AVG(total_value), 0) AS avg_value,
    ROUND(SUM(potential_assessment_reduction), 0) AS total_potential_reduction
FROM v_assessment_fairness_summary
GROUP BY appeal_priority
ORDER BY
    CASE appeal_priority
        WHEN 'HIGH_PRIORITY' THEN 1
        WHEN 'MEDIUM_PRIORITY' THEN 2
        WHEN 'LOW_PRIORITY' THEN 3
        ELSE 4
    END;

-- ============================================================================
-- 10. INTEGRATED TEST: FULL ANALYSIS WORKFLOW
-- ============================================================================

\echo ''
\echo '============================================'
\echo '10. INTEGRATED TEST: FULL ANALYSIS'
\echo '============================================'
\echo ''

-- Test 10.1: Complete analysis for one property
\echo 'Test 10.1: Complete property analysis workflow'
WITH test_parcel AS (
    SELECT parcel_id FROM test_parcels LIMIT 1
),
target_info AS (
    SELECT
        p.parcel_id,
        p.ow_name,
        p.ph_add,
        p.total_val_cents,
        p.assess_val_cents,
        CASE WHEN p.total_val_cents > 0
            THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 2)
            ELSE NULL
        END AS assessment_ratio
    FROM properties p
    WHERE p.parcel_id = (SELECT parcel_id FROM test_parcel)
),
comparables AS (
    SELECT * FROM find_comparable_properties((SELECT parcel_id FROM test_parcel))
),
comp_stats AS (
    SELECT
        COUNT(*) AS comp_count,
        ROUND(AVG(similarity_score), 2) AS avg_similarity,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio), 2) AS median_comp_ratio,
        COUNT(*) FILTER (WHERE match_type = 'SUBDIVISION') AS subdiv_matches,
        COUNT(*) FILTER (WHERE match_type = 'PROXIMITY') AS proximity_matches
    FROM comparables
),
ranking AS (
    SELECT * FROM get_property_percentile_ranking((SELECT parcel_id FROM test_parcel))
),
neighborhood AS (
    SELECT * FROM get_neighborhood_median_ratio((SELECT parcel_id FROM test_parcel))
)
SELECT
    '=== PROPERTY INFORMATION ===' AS section,
    t.parcel_id,
    t.ow_name,
    t.total_val_cents,
    t.assess_val_cents,
    t.assessment_ratio
FROM target_info t
UNION ALL
SELECT
    '=== COMPARABLE PROPERTIES ===' AS section,
    NULL, NULL, NULL, NULL,
    cs.comp_count::NUMERIC
FROM comp_stats cs
UNION ALL
SELECT
    '=== RANKINGS ===' AS section,
    NULL, NULL, NULL, NULL,
    r.neighborhood_percentile
FROM ranking r
UNION ALL
SELECT
    '=== FAIRNESS ASSESSMENT ===' AS section,
    NULL, NULL, NULL, NULL,
    NULL
FROM ranking r;

-- ============================================================================
-- 11. PERFORMANCE SUMMARY
-- ============================================================================

\echo ''
\echo '============================================'
\echo '11. PERFORMANCE SUMMARY'
\echo '============================================'
\echo ''

\echo 'Performance benchmarks (times shown above):'
\echo '  - Comparable matching: Target <300ms'
\echo '  - Neighborhood median: Target <150ms'
\echo '  - Subdivision median: Target <100ms'
\echo '  - Percentile ranking: Target <300ms'
\echo ''
\echo 'If any queries exceed targets:'
\echo '  1. Verify all indexes exist: SELECT * FROM pg_indexes WHERE tablename = ''properties'';'
\echo '  2. Update statistics: ANALYZE properties;'
\echo '  3. Check work_mem: SHOW work_mem; (should be >= 64MB)'
\echo '  4. Review EXPLAIN ANALYZE output for sequential scans'
\echo ''

-- ============================================================================
-- 12. CLEANUP
-- ============================================================================

DROP TABLE IF EXISTS test_parcels;

\echo ''
\echo '============================================'
\echo 'ALL TESTS COMPLETED'
\echo '============================================'
\echo ''
\echo 'Review output above for any errors or warnings.'
\echo 'Check that performance times meet targets.'
\echo ''

\timing off
