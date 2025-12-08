-- ============================================================================
-- COMPARABLE PROPERTY MATCHING QUERY FOR ASSESSMENT ANALYSIS
-- ============================================================================
-- PostgreSQL + PostGIS
-- Purpose: Find similar properties for fairness scoring and assessment analysis
-- Optimized for: 173K records with spatial indexing
--
-- USAGE:
--   Parameters:
--     - p_target_parcelid: The parcel ID to find comparables for
--   Returns: Top 20 comparable properties with similarity scores
-- ============================================================================

-- Prerequisites: Ensure PostGIS extension and spatial indexes exist
-- CREATE EXTENSION IF NOT EXISTS postgis;
-- CREATE INDEX idx_properties_geometry ON properties USING GIST(geometry);
-- CREATE INDEX idx_properties_subdivname ON properties(subdivname) WHERE subdivname IS NOT NULL;
-- CREATE INDEX idx_properties_type ON properties(type_) WHERE type_ IS NOT NULL;
-- CREATE INDEX idx_properties_total_val ON properties(total_val_cents) WHERE total_val_cents > 0;
-- CREATE INDEX idx_properties_acre_area ON properties(acre_area) WHERE acre_area > 0;

-- ============================================================================
-- MAIN COMPARABLE PROPERTY MATCHING QUERY
-- ============================================================================

CREATE OR REPLACE FUNCTION find_comparable_properties(
    p_target_parcelid VARCHAR
)
RETURNS TABLE (
    comparable_parcelid VARCHAR,
    match_type VARCHAR,
    distance_miles NUMERIC,
    similarity_score NUMERIC,
    total_value BIGINT,
    assess_value BIGINT,
    land_value BIGINT,
    imp_value BIGINT,
    acre_area NUMERIC,
    property_type VARCHAR,
    owner_name VARCHAR,
    property_address VARCHAR,
    subdivision VARCHAR,
    assessment_ratio NUMERIC,
    value_difference_pct NUMERIC,
    acreage_difference_pct NUMERIC,
    -- Detailed score breakdown
    type_match_score NUMERIC,
    value_match_score NUMERIC,
    acreage_match_score NUMERIC,
    location_score NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_type VARCHAR;
    v_target_total_val_cents BIGINT;
    v_target_acre_area NUMERIC;
    v_target_subdivision VARCHAR;
    v_target_geometry GEOMETRY;
    v_subdivision_count INTEGER;
BEGIN
    -- Get target property characteristics
    SELECT
        p.type_,
        p.total_val_cents,
        p.acre_area,
        p.subdivname,
        p.geometry
    INTO
        v_target_type,
        v_target_total_val_cents,
        v_target_acre_area,
        v_target_subdivision,
        v_target_geometry
    FROM properties p
    WHERE p.parcel_id = p_target_parcelid
        AND p.type_ IS NOT NULL
        AND p.total_val_cents > 0
        AND p.acre_area > 0;

    -- If target property not found or invalid, return empty result
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Check how many properties exist in the same subdivision
    SELECT COUNT(*)
    INTO v_subdivision_count
    FROM properties p
    WHERE p.subdivname = v_target_subdivision
        AND p.subdivname IS NOT NULL
        AND p.parcel_id != p_target_parcelid
        AND p.type_ = v_target_type
        AND p.total_val_cents BETWEEN v_target_total_val_cents * 0.80 AND v_target_total_val_cents * 1.20
        AND p.acre_area BETWEEN v_target_acre_area * 0.75 AND v_target_acre_area * 1.25
        AND p.total_val_cents > 0
        AND p.acre_area > 0;

    -- Return results from CTE-based query
    RETURN QUERY
    WITH target_property AS (
        -- Anchor query: get target property details
        SELECT
            v_target_type AS type_,
            v_target_total_val_cents AS total_val_cents,
            v_target_acre_area AS acre_area,
            v_target_subdivision AS subdivname,
            v_target_geometry AS geometry
    ),

    subdivision_matches AS (
        -- PRIORITY 1: Same subdivision matches
        SELECT
            p.parcel_id,
            'SUBDIVISION' AS match_type,
            0.0 AS distance_miles,  -- Within subdivision
            p.type_,
            p.total_val_cents,
            p.assess_val_cents,
            p.land_val_cents,
            p.imp_val_cents,
            p.acre_area,
            p.ow_name,
            p.ph_add,
            p.subdivname,
            p.geometry
        FROM properties p, target_property t
        WHERE p.subdivname = t.subdivname
            AND p.subdivname IS NOT NULL
            AND p.parcel_id != p_target_parcelid
            -- Filters: same type, similar value (±20%), similar acreage (±25%)
            AND p.type_ = t.type_
            AND p.total_val_cents BETWEEN t.total_val_cents * 0.80 AND t.total_val_cents * 1.20
            AND p.acre_area BETWEEN t.acre_area * 0.75 AND t.acre_area * 1.25
            AND p.total_val_cents > 0
            AND p.acre_area > 0
    ),

    proximity_matches AS (
        -- PRIORITY 2: Proximity matches (within 0.5 miles)
        -- Only used if subdivision matches < 5
        SELECT
            p.parcel_id,
            'PROXIMITY' AS match_type,
            ST_Distance(
                ST_Transform(p.geometry, 4326)::geography,
                ST_Transform(t.geometry, 4326)::geography
            ) * 0.000621371 AS distance_miles,  -- Convert meters to miles
            p.type_,
            p.total_val_cents,
            p.assess_val_cents,
            p.land_val_cents,
            p.imp_val_cents,
            p.acre_area,
            p.ow_name,
            p.ph_add,
            p.subdivname,
            p.geometry
        FROM properties p, target_property t
        WHERE p.parcel_id != p_target_parcelid
            -- Spatial filter: within 0.5 miles (804.67 meters)
            AND ST_DWithin(
                ST_Transform(p.geometry, 4326)::geography,
                ST_Transform(t.geometry, 4326)::geography,
                804.67  -- 0.5 miles in meters
            )
            -- Same property type
            AND p.type_ = t.type_
            -- Similar total value (±20%)
            AND p.total_val_cents BETWEEN t.total_val_cents * 0.80 AND t.total_val_cents * 1.20
            -- Similar acreage (±25%)
            AND p.acre_area BETWEEN t.acre_area * 0.75 AND t.acre_area * 1.25
            AND p.total_val_cents > 0
            AND p.acre_area > 0
            -- Exclude properties already in subdivision matches
            AND (v_subdivision_count >= 5 OR p.subdivname IS DISTINCT FROM v_target_subdivision)
    ),

    all_candidates AS (
        -- Combine both match types
        SELECT * FROM subdivision_matches
        UNION ALL
        SELECT * FROM proximity_matches
    ),

    scored_comparables AS (
        -- Calculate similarity scores using weighted criteria
        SELECT
            ac.parcel_id,
            ac.match_type,
            ac.distance_miles,
            ac.total_val_cents,
            ac.assess_val_cents,
            ac.land_val_cents,
            ac.imp_val_cents,
            ac.acre_area,
            ac.type_,
            ac.ow_name,
            ac.ph_add,
            ac.subdivname,

            -- Calculate assessment ratio (assessed value / total value)
            CASE
                WHEN ac.total_val_cents > 0 THEN
                    ROUND((ac.assess_val_cents::NUMERIC / ac.total_val_cents::NUMERIC) * 100, 2)
                ELSE 0
            END AS assessment_ratio,

            -- Value difference percentage
            ROUND(
                ABS(ac.total_val_cents - v_target_total_val_cents)::NUMERIC /
                NULLIF(v_target_total_val_cents, 0)::NUMERIC * 100,
                2
            ) AS value_difference_pct,

            -- Acreage difference percentage
            ROUND(
                ABS(ac.acre_area - v_target_acre_area)::NUMERIC /
                NULLIF(v_target_acre_area, 0)::NUMERIC * 100,
                2
            ) AS acreage_difference_pct,

            -- SCORING COMPONENTS (0-100 each)

            -- 1. Type match score (100 if exact match, handled by filter)
            100.0 AS type_match_score,

            -- 2. Value match score (inverse of % difference, max 100)
            GREATEST(0, 100 - (
                ABS(ac.total_val_cents - v_target_total_val_cents)::NUMERIC /
                NULLIF(v_target_total_val_cents, 0)::NUMERIC * 100 * 5  -- Scale: 20% diff = 0 points
            )) AS value_match_score,

            -- 3. Acreage match score (inverse of % difference, max 100)
            GREATEST(0, 100 - (
                ABS(ac.acre_area - v_target_acre_area)::NUMERIC /
                NULLIF(v_target_acre_area, 0)::NUMERIC * 100 * 4  -- Scale: 25% diff = 0 points
            )) AS acreage_match_score,

            -- 4. Location score (100 for subdivision, distance-based for proximity)
            CASE
                WHEN ac.match_type = 'SUBDIVISION' THEN 100.0
                WHEN ac.match_type = 'PROXIMITY' THEN
                    GREATEST(0, 100 - (ac.distance_miles * 200))  -- Linear decay: 0.5 miles = 0 points
                ELSE 0
            END AS location_score

        FROM all_candidates ac
    )

    -- Final output with weighted similarity score
    SELECT
        sc.parcel_id AS comparable_parcelid,
        sc.match_type,
        ROUND(sc.distance_miles::NUMERIC, 3) AS distance_miles,

        -- WEIGHTED SIMILARITY SCORE (0-100)
        -- Weights: Type 10%, Value 35%, Acreage 30%, Location 25%
        ROUND(
            (sc.type_match_score * 0.10) +
            (sc.value_match_score * 0.35) +
            (sc.acreage_match_score * 0.30) +
            (sc.location_score * 0.25),
            2
        ) AS similarity_score,

        sc.total_val_cents AS total_value,
        sc.assess_val_cents AS assess_value,
        sc.land_val_cents AS land_value,
        sc.imp_val_cents AS imp_value,
        ROUND(sc.acre_area::NUMERIC, 2) AS acre_area,
        sc.type_ AS property_type,
        sc.ow_name AS owner_name,
        sc.ph_add AS property_address,
        sc.subdivname AS subdivision,
        sc.assessment_ratio,
        sc.value_difference_pct,
        sc.acreage_difference_pct,

        -- Score breakdown for transparency
        ROUND(sc.type_match_score, 2) AS type_match_score,
        ROUND(sc.value_match_score, 2) AS value_match_score,
        ROUND(sc.acreage_match_score, 2) AS acreage_match_score,
        ROUND(sc.location_score, 2) AS location_score

    FROM scored_comparables sc
    ORDER BY
        -- Prioritize subdivision matches when we have enough
        CASE WHEN v_subdivision_count >= 5 AND sc.match_type = 'SUBDIVISION' THEN 0 ELSE 1 END,
        -- Then sort by similarity score
        similarity_score DESC,
        -- Tie-breaker: closer is better
        sc.distance_miles ASC
    LIMIT 20;

END;
$$;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Find comparables for a specific parcel
-- SELECT * FROM find_comparable_properties('16-26005-000');

-- Example 2: Get comparables with summary statistics
/*
WITH comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
)
SELECT
    COUNT(*) as comparable_count,
    AVG(similarity_score) as avg_similarity,
    MIN(similarity_score) as min_similarity,
    MAX(similarity_score) as max_similarity,
    AVG(total_value) as avg_total_value,
    AVG(assessment_ratio) as avg_assessment_ratio,
    COUNT(*) FILTER (WHERE match_type = 'SUBDIVISION') as subdivision_matches,
    COUNT(*) FILTER (WHERE match_type = 'PROXIMITY') as proximity_matches
FROM comparables;
*/

-- Example 3: Compare target property to comparables
/*
WITH target AS (
    SELECT
        parcel_id,
        total_val_cents,
        assess_val_cents,
        CASE WHEN total_val_cents > 0
            THEN ROUND((assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100, 2)
            ELSE 0
        END AS assessment_ratio
    FROM properties
    WHERE parcel_id = '16-26005-000'
),
comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
)
SELECT
    t.parcel_id as target_parcelid,
    t.total_val_cents as target_value,
    t.assessment_ratio as target_ratio,
    AVG(c.assessment_ratio) as avg_comparable_ratio,
    t.assessment_ratio - AVG(c.assessment_ratio) as ratio_difference,
    CASE
        WHEN t.assessment_ratio > AVG(c.assessment_ratio) + 5 THEN 'OVER-ASSESSED'
        WHEN t.assessment_ratio < AVG(c.assessment_ratio) - 5 THEN 'UNDER-ASSESSED'
        ELSE 'FAIR'
    END as fairness_assessment
FROM target t
CROSS JOIN comparables c
GROUP BY t.parcel_id, t.total_val_cents, t.assessment_ratio;
*/

-- ============================================================================
-- PERFORMANCE OPTIMIZATION NOTES
-- ============================================================================
--
-- 1. SPATIAL INDEXES: Essential for ST_DWithin performance
--    CREATE INDEX idx_properties_geometry ON properties USING GIST(geometry);
--
-- 2. COLUMN INDEXES: Speed up filtering
--    CREATE INDEX idx_properties_subdivname ON properties(subdivname) WHERE subdivname IS NOT NULL;
--    CREATE INDEX idx_properties_type ON properties(type_) WHERE type_ IS NOT NULL;
--    CREATE INDEX idx_properties_total_val ON properties(total_val_cents) WHERE total_val_cents > 0;
--    CREATE INDEX idx_properties_acre_area ON properties(acre_area) WHERE acre_area > 0;
--
-- 3. COMPOSITE INDEX: For common filter combinations
--    CREATE INDEX idx_properties_type_val_acre ON properties(type_, total_val_cents, acre_area)
--    WHERE type_ IS NOT NULL AND total_val_cents > 0 AND acre_area > 0;
--
-- 4. STATISTICS: Ensure PostgreSQL has current statistics
--    ANALYZE properties;
--
-- 5. ST_DWithin vs ST_Distance:
--    - ST_DWithin uses spatial index efficiently (preferred for filtering)
--    - ST_Distance is calculated only for results (used for sorting/display)
--
-- 6. Geography vs Geometry:
--    - Cast to geography for accurate distance in meters/miles
--    - Keep original geometry in EPSG:3433 for spatial index
--    - Transform on-the-fly for distance calculations
--
-- ============================================================================
-- QUERY EXECUTION PLAN ANALYSIS
-- ============================================================================
--
-- To analyze query performance:
--
-- EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
-- SELECT * FROM find_comparable_properties('16-26005-000');
--
-- Expected plan features:
-- 1. Index Scan on idx_properties_geometry (for ST_DWithin)
-- 2. Index Scan on idx_properties_subdivname (for subdivision matches)
-- 3. Filter conditions applied early (type_, total_val_cents, acre_area)
-- 4. CTE Materialization for subdivision_matches and proximity_matches
-- 5. Sort operation for final ordering (should be quick with LIMIT 20)
--
-- Performance targets (173K records):
-- - Subdivision matches: < 50ms
-- - Proximity matches: < 200ms (with spatial index)
-- - Total query time: < 300ms
--
-- ============================================================================

COMMENT ON FUNCTION find_comparable_properties IS
'Finds top 20 comparable properties for assessment fairness analysis.
Prioritizes same-subdivision matches, falls back to 0.5-mile proximity.
Filters by same property type, ±20% value, ±25% acreage.
Returns weighted similarity score (0-100) based on type, value, acreage, and location.';
