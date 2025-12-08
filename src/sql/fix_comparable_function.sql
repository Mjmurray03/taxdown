-- Fix for the comparable matching function
-- The issue is that ROUND(double precision, integer) doesn't exist in some PostgreSQL versions
-- We need to cast to NUMERIC first

DROP FUNCTION IF EXISTS find_comparable_properties(VARCHAR);

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
            'SUBDIVISION'::VARCHAR AS match_type,
            0.0::NUMERIC AS distance_miles,  -- Within subdivision, cast to NUMERIC
            p.type_,
            p.total_val_cents,
            p.assess_val_cents,
            p.land_val_cents,
            p.imp_val_cents,
            p.acre_area::NUMERIC AS acre_area,  -- Cast to NUMERIC
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
            'PROXIMITY'::VARCHAR AS match_type,
            (ST_Distance(
                ST_Transform(p.geometry, 4326)::geography,
                ST_Transform(t.geometry, 4326)::geography
            ) * 0.000621371)::NUMERIC AS distance_miles,  -- Cast to NUMERIC
            p.type_,
            p.total_val_cents,
            p.assess_val_cents,
            p.land_val_cents,
            p.imp_val_cents,
            p.acre_area::NUMERIC AS acre_area,  -- Cast to NUMERIC
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
        ROUND(sc.distance_miles, 3) AS distance_miles,

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
        ROUND(sc.acre_area, 2) AS acre_area,
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

COMMENT ON FUNCTION find_comparable_properties IS
'Finds top 20 comparable properties for assessment fairness analysis.
Prioritizes same-subdivision matches, falls back to 0.5-mile proximity.
Filters by same property type, ±20% value, ±25% acreage.
Returns weighted similarity score (0-100) based on type, value, acreage, and location.';
