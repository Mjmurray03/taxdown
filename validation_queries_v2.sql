-- ============================================================================
-- TAXDOWN PHASE 3 - DATABASE VALIDATION QUERIES
-- ============================================================================
-- Database: Railway PostGIS
-- Date: 2025-12-08
-- ============================================================================

-- Set output format
\pset border 2
\pset format wrapped

-- VALIDATION 1: ROW COUNTS
\echo ''
\echo '========================================='
\echo 'VALIDATION 1: ROW COUNTS'
\echo '========================================='
\echo ''

SELECT 'Properties Count' as metric, COUNT(*) as value, 173743 as expected FROM properties
UNION ALL
SELECT 'Subdivisions Count', COUNT(*), 4041 FROM subdivisions
UNION ALL
SELECT 'Properties with building_sqft > 0', COUNT(*), 94555 FROM properties WHERE building_sqft > 0;

-- VALIDATION 2: DATA QUALITY
\echo ''
\echo '========================================='
\echo 'VALIDATION 2: DATA QUALITY'
\echo '========================================='
\echo ''

SELECT 'NULL parcel_id records' as metric, COUNT(*)::text as value FROM properties WHERE parcel_id IS NULL
UNION ALL
SELECT 'Properties with assess_val_cents > 0', COUNT(*)::text FROM properties WHERE assess_val_cents > 0
UNION ALL
SELECT 'Properties with geometry NOT NULL', COUNT(*)::text FROM properties WHERE geometry IS NOT NULL;

\echo ''
\echo 'Value Statistics (total_val_cents):'
SELECT
    MIN(total_val_cents) as min_value,
    MAX(total_val_cents) as max_value,
    AVG(total_val_cents)::BIGINT as avg_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_val_cents)::BIGINT as median_value
FROM properties
WHERE total_val_cents > 0;

-- VALIDATION 3: SPATIAL VALIDATION
\echo ''
\echo '========================================='
\echo 'VALIDATION 3: SPATIAL VALIDATION'
\echo '========================================='
\echo ''

\echo 'Geometry validity check:'
SELECT
    CASE WHEN ST_IsValid(geometry) THEN 'VALID' ELSE 'INVALID' END as validity,
    COUNT(*) as count
FROM properties
WHERE geometry IS NOT NULL
GROUP BY ST_IsValid(geometry)
ORDER BY validity;

\echo ''
\echo 'Geometry SRID check:'
SELECT
    ST_SRID(geometry) as srid,
    COUNT(*) as count
FROM properties
WHERE geometry IS NOT NULL
GROUP BY ST_SRID(geometry)
ORDER BY srid;

\echo ''
\echo 'Spatial query test:'
SELECT COUNT(*) as nearby_properties_count
FROM properties
WHERE geometry IS NOT NULL
  AND ST_DWithin(
    geometry,
    ST_SetSRID(ST_MakePoint(-94.2, 36.4), 4326),
    0.01
  );

-- VALIDATION 4: RELATIONSHIP TEST
\echo ''
\echo '========================================='
\echo 'VALIDATION 4: RELATIONSHIP TEST'
\echo '========================================='
\echo ''

SELECT COUNT(*) as properties_within_subdivisions
FROM properties p
JOIN subdivisions s ON ST_Within(p.geometry, s.geometry)
WHERE p.geometry IS NOT NULL AND s.geometry IS NOT NULL;

-- VALIDATION 5: ASSESSMENT RATIO
\echo ''
\echo '========================================='
\echo 'VALIDATION 5: ASSESSMENT RATIO'
\echo '========================================='
\echo ''

SELECT
    (AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)))::NUMERIC(6,4) as avg_assessment_ratio,
    (AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100)::NUMERIC(6,2) as avg_ratio_pct,
    COUNT(*) as sample_size
FROM properties
WHERE total_val_cents > 0 AND assess_val_cents > 0;

-- VALIDATION 6: SAMPLE PROPERTY
\echo ''
\echo '========================================='
\echo 'VALIDATION 6: SAMPLE PROPERTY'
\echo '========================================='
\echo ''

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
