-- ============================================================================
-- TAXDOWN PHASE 3 - DATABASE VALIDATION QUERIES
-- ============================================================================
-- Database: Railway PostGIS
-- Date: 2025-12-08
-- ============================================================================

\echo '========================================='
\echo 'VALIDATION 1: ROW COUNTS'
\echo '========================================='

\echo 'Properties total count (expected: 173,743):'
SELECT COUNT(*) as properties_count FROM properties;

\echo ''
\echo 'Subdivisions total count (expected: 4,041):'
SELECT COUNT(*) as subdivisions_count FROM subdivisions;

\echo ''
\echo 'Properties with building_sqft > 0 (expected: ~94,555):'
SELECT COUNT(*) as properties_with_building FROM properties WHERE building_sqft > 0;

\echo ''
\echo '========================================='
\echo 'VALIDATION 2: DATA QUALITY'
\echo '========================================='

\echo 'Count of NULL parcel_id records (expected: ~2,697):'
SELECT COUNT(*) as null_parcel_id_count FROM properties WHERE parcel_id IS NULL;

\echo ''
\echo 'Count of properties with assess_val_cents > 0:'
SELECT COUNT(*) as properties_with_assessment FROM properties WHERE assess_val_cents > 0;

\echo ''
\echo 'Count of properties with geometry IS NOT NULL:'
SELECT COUNT(*) as properties_with_geometry FROM properties WHERE geometry IS NOT NULL;

\echo ''
\echo 'Min/Max/Avg of total_val_cents:'
SELECT
    MIN(total_val_cents) as min_total_val_cents,
    MAX(total_val_cents) as max_total_val_cents,
    AVG(total_val_cents)::BIGINT as avg_total_val_cents,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_val_cents)::BIGINT as median_total_val_cents
FROM properties
WHERE total_val_cents > 0;

\echo ''
\echo '========================================='
\echo 'VALIDATION 3: SPATIAL VALIDATION'
\echo '========================================='

\echo 'Geometry validity check:'
SELECT
    ST_IsValid(geometry) as is_valid,
    COUNT(*) as count
FROM properties
WHERE geometry IS NOT NULL
GROUP BY ST_IsValid(geometry)
ORDER BY is_valid;

\echo ''
\echo 'Geometry SRID check (should all be 4326):'
SELECT
    ST_SRID(geometry) as srid,
    COUNT(*) as count
FROM properties
WHERE geometry IS NOT NULL
GROUP BY ST_SRID(geometry)
ORDER BY srid;

\echo ''
\echo 'Spatial query test (properties near Fayetteville center):'
SELECT COUNT(*) as nearby_properties
FROM properties
WHERE geometry IS NOT NULL
  AND ST_DWithin(
    geometry,
    ST_SetSRID(ST_MakePoint(-94.2, 36.4), 4326),
    0.01
  );

\echo ''
\echo '========================================='
\echo 'VALIDATION 4: RELATIONSHIP TEST'
\echo '========================================='

\echo 'Properties within subdivision polygons:'
SELECT COUNT(*) as properties_within_subdivisions
FROM properties p
JOIN subdivisions s ON ST_Within(p.geometry, s.geometry)
WHERE p.geometry IS NOT NULL AND s.geometry IS NOT NULL;

\echo ''
\echo '========================================='
\echo 'VALIDATION 5: ASSESSMENT RATIO'
\echo '========================================='

\echo 'Average assessment ratio (expected: ~0.20 or 20%):'
SELECT
    ROUND(AVG(assess_val_cents::FLOAT / NULLIF(total_val_cents, 0)), 4) as avg_assessment_ratio,
    ROUND(AVG(assess_val_cents::FLOAT / NULLIF(total_val_cents, 0)) * 100, 2) as avg_assessment_ratio_pct,
    COUNT(*) as sample_size
FROM properties
WHERE total_val_cents > 0 AND assess_val_cents > 0;

\echo ''
\echo '========================================='
\echo 'VALIDATION 6: SAMPLE PROPERTY FOR COMPARABLE MATCHING'
\echo '========================================='

\echo 'Selecting a random property with valid data:'
SELECT
    parcel_id,
    total_val_cents,
    assess_val_cents,
    acre_area,
    type_,
    subdivname,
    ph_add as property_address
FROM properties
WHERE assess_val_cents > 0
  AND total_val_cents > 0
  AND acre_area > 0
  AND type_ IS NOT NULL
  AND geometry IS NOT NULL
ORDER BY RANDOM()
LIMIT 1;

\echo ''
\echo '========================================='
\echo 'VALIDATION COMPLETE'
\echo '========================================='
