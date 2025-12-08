-- ============================================================================
-- ASSESSMENT ANALYTICS QUERIES
-- ============================================================================
-- PostgreSQL
-- Purpose: Neighborhood/subdivision analytics and percentile ranking
-- Optimized for: 173K records
--
-- CONTENTS:
--   1. Neighborhood median assessment ratio
--   2. Subdivision median assessment ratio
--   3. Property percentile ranking vs neighbors
--   4. Statistical summaries for assessment fairness
-- ============================================================================

-- ============================================================================
-- 1. NEIGHBORHOOD MEDIAN ASSESSMENT RATIO
-- ============================================================================
-- Purpose: Calculate median assessment ratio for properties in same neighborhood
-- Used for: Identifying neighborhood-wide assessment patterns

CREATE OR REPLACE FUNCTION get_neighborhood_median_ratio(
    p_target_parcelid VARCHAR
)
RETURNS TABLE (
    neighborhood_code VARCHAR,
    property_count BIGINT,
    median_assessment_ratio NUMERIC,
    avg_assessment_ratio NUMERIC,
    min_assessment_ratio NUMERIC,
    max_assessment_ratio NUMERIC,
    stddev_assessment_ratio NUMERIC,
    target_property_ratio NUMERIC,
    target_vs_median_diff NUMERIC,
    percentile_25 NUMERIC,
    percentile_75 NUMERIC,
    interquartile_range NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_s_t_r VARCHAR;
    v_target_ratio NUMERIC;
BEGIN
    -- Get target property's S_T_R (Section-Township-Range) which represents neighborhood
    SELECT
        p.s_t_r,
        CASE WHEN p.total_val_cents > 0
            THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 4)
            ELSE NULL
        END
    INTO v_target_s_t_r, v_target_ratio
    FROM properties p
    WHERE p.parcel_id = p_target_parcelid;

    -- If target not found, return empty
    IF NOT FOUND OR v_target_s_t_r IS NULL THEN
        RETURN;
    END IF;

    -- Calculate neighborhood statistics
    RETURN QUERY
    WITH neighborhood_properties AS (
        SELECT
            p.parcel_id,
            p.total_val_cents,
            p.assess_val_cents,
            CASE WHEN p.total_val_cents > 0
                THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 4)
                ELSE NULL
            END AS assessment_ratio
        FROM properties p
        WHERE p.s_t_r = v_target_s_t_r
            AND p.total_val_cents > 0
            AND p.assess_val_cents > 0
    ),
    statistics AS (
        SELECT
            v_target_s_t_r AS neighborhood_code,
            COUNT(*) AS property_count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio) AS median_ratio,
            AVG(assessment_ratio) AS avg_ratio,
            MIN(assessment_ratio) AS min_ratio,
            MAX(assessment_ratio) AS max_ratio,
            STDDEV(assessment_ratio) AS stddev_ratio,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY assessment_ratio) AS pct_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY assessment_ratio) AS pct_75
        FROM neighborhood_properties
    )
    SELECT
        s.neighborhood_code,
        s.property_count,
        ROUND(s.median_ratio, 2) AS median_assessment_ratio,
        ROUND(s.avg_ratio, 2) AS avg_assessment_ratio,
        ROUND(s.min_ratio, 2) AS min_assessment_ratio,
        ROUND(s.max_ratio, 2) AS max_assessment_ratio,
        ROUND(s.stddev_ratio, 2) AS stddev_assessment_ratio,
        ROUND(v_target_ratio, 2) AS target_property_ratio,
        ROUND(v_target_ratio - s.median_ratio, 2) AS target_vs_median_diff,
        ROUND(s.pct_25, 2) AS percentile_25,
        ROUND(s.pct_75, 2) AS percentile_75,
        ROUND(s.pct_75 - s.pct_25, 2) AS interquartile_range
    FROM statistics s;
END;
$$;

COMMENT ON FUNCTION get_neighborhood_median_ratio IS
'Calculates median assessment ratio and statistics for a neighborhood (S_T_R).
Returns comprehensive statistics including median, mean, stddev, and quartiles.
Compares target property ratio to neighborhood median.';

-- ============================================================================
-- 2. SUBDIVISION MEDIAN ASSESSMENT RATIO
-- ============================================================================
-- Purpose: Calculate median assessment ratio for properties in same subdivision
-- Used for: More granular assessment fairness analysis than neighborhood

CREATE OR REPLACE FUNCTION get_subdivision_median_ratio(
    p_target_parcelid VARCHAR
)
RETURNS TABLE (
    subdivision_name VARCHAR,
    property_count BIGINT,
    median_assessment_ratio NUMERIC,
    avg_assessment_ratio NUMERIC,
    min_assessment_ratio NUMERIC,
    max_assessment_ratio NUMERIC,
    stddev_assessment_ratio NUMERIC,
    target_property_ratio NUMERIC,
    target_vs_median_diff NUMERIC,
    percentile_25 NUMERIC,
    percentile_75 NUMERIC,
    interquartile_range NUMERIC,
    median_total_value NUMERIC,
    median_land_value NUMERIC,
    median_imp_value NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_subdivision VARCHAR;
    v_target_ratio NUMERIC;
BEGIN
    -- Get target property's subdivision
    SELECT
        p.subdivname,
        CASE WHEN p.total_val_cents > 0
            THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 4)
            ELSE NULL
        END
    INTO v_target_subdivision, v_target_ratio
    FROM properties p
    WHERE p.parcel_id = p_target_parcelid;

    -- If target not found or no subdivision, return empty
    IF NOT FOUND OR v_target_subdivision IS NULL THEN
        RETURN;
    END IF;

    -- Calculate subdivision statistics
    RETURN QUERY
    WITH subdivision_properties AS (
        SELECT
            p.parcel_id,
            p.total_val_cents,
            p.assess_val_cents,
            p.land_val_cents,
            p.imp_val_cents,
            CASE WHEN p.total_val_cents > 0
                THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 4)
                ELSE NULL
            END AS assessment_ratio
        FROM properties p
        WHERE p.subdivname = v_target_subdivision
            AND p.total_val_cents > 0
            AND p.assess_val_cents > 0
    ),
    statistics AS (
        SELECT
            v_target_subdivision AS subdivision_name,
            COUNT(*) AS property_count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio) AS median_ratio,
            AVG(assessment_ratio) AS avg_ratio,
            MIN(assessment_ratio) AS min_ratio,
            MAX(assessment_ratio) AS max_ratio,
            STDDEV(assessment_ratio) AS stddev_ratio,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY assessment_ratio) AS pct_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY assessment_ratio) AS pct_75,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_val_cents) AS median_total,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY land_val_cents) AS median_land,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY imp_val_cents) AS median_imp
        FROM subdivision_properties
    )
    SELECT
        s.subdivision_name,
        s.property_count,
        ROUND(s.median_ratio, 2) AS median_assessment_ratio,
        ROUND(s.avg_ratio, 2) AS avg_assessment_ratio,
        ROUND(s.min_ratio, 2) AS min_assessment_ratio,
        ROUND(s.max_ratio, 2) AS max_assessment_ratio,
        ROUND(s.stddev_ratio, 2) AS stddev_assessment_ratio,
        ROUND(v_target_ratio, 2) AS target_property_ratio,
        ROUND(v_target_ratio - s.median_ratio, 2) AS target_vs_median_diff,
        ROUND(s.pct_25, 2) AS percentile_25,
        ROUND(s.pct_75, 2) AS percentile_75,
        ROUND(s.pct_75 - s.pct_25, 2) AS interquartile_range,
        ROUND(s.median_total, 0) AS median_total_value,
        ROUND(s.median_land, 0) AS median_land_value,
        ROUND(s.median_imp, 0) AS median_imp_value
    FROM statistics s;
END;
$$;

COMMENT ON FUNCTION get_subdivision_median_ratio IS
'Calculates median assessment ratio and statistics for a subdivision.
Returns comprehensive statistics including median values, ratios, and quartiles.
Compares target property ratio to subdivision median.';

-- ============================================================================
-- 3. PROPERTY PERCENTILE RANKING VS NEIGHBORS
-- ============================================================================
-- Purpose: Rank a property's assessment ratio within its neighborhood and subdivision
-- Used for: Determining if a property is in top/bottom X% for assessment fairness

CREATE OR REPLACE FUNCTION get_property_percentile_ranking(
    p_target_parcelid VARCHAR
)
RETURNS TABLE (
    parcelid VARCHAR,
    owner_name VARCHAR,
    property_address VARCHAR,
    total_value BIGINT,
    assess_value BIGINT,
    assessment_ratio NUMERIC,
    -- Neighborhood rankings
    neighborhood_code VARCHAR,
    neighborhood_property_count BIGINT,
    neighborhood_percentile NUMERIC,
    neighborhood_rank BIGINT,
    neighborhood_median_ratio NUMERIC,
    -- Subdivision rankings
    subdivision_name VARCHAR,
    subdivision_property_count BIGINT,
    subdivision_percentile NUMERIC,
    subdivision_rank BIGINT,
    subdivision_median_ratio NUMERIC,
    -- Property type rankings
    property_type VARCHAR,
    type_property_count BIGINT,
    type_percentile NUMERIC,
    type_rank BIGINT,
    type_median_ratio NUMERIC,
    -- Fairness indicators
    is_over_assessed BOOLEAN,
    is_under_assessed BOOLEAN,
    fairness_category VARCHAR,
    potential_savings_indicator VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_s_t_r VARCHAR;
    v_target_subdivision VARCHAR;
    v_target_type VARCHAR;
    v_target_ratio NUMERIC;
    v_target_total_val_cents BIGINT;
    v_target_assess_val_cents BIGINT;
    v_target_owner VARCHAR;
    v_target_address VARCHAR;
BEGIN
    -- Get target property details
    SELECT
        p.s_t_r,
        p.subdivname,
        p.type_,
        CASE WHEN p.total_val_cents > 0
            THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 4)
            ELSE NULL
        END,
        p.total_val_cents,
        p.assess_val_cents,
        p.ow_name,
        p.ph_add
    INTO
        v_target_s_t_r,
        v_target_subdivision,
        v_target_type,
        v_target_ratio,
        v_target_total_val_cents,
        v_target_assess_val_cents,
        v_target_owner,
        v_target_address
    FROM properties p
    WHERE p.parcel_id = p_target_parcelid;

    -- If target not found, return empty
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Calculate rankings across multiple dimensions
    RETURN QUERY
    WITH neighborhood_stats AS (
        -- Neighborhood (S_T_R) rankings
        SELECT
            COUNT(*) AS property_count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
                CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END
            ) AS median_ratio,
            COUNT(*) FILTER (
                WHERE CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END < v_target_ratio
            ) AS rank_position
        FROM properties
        WHERE s_t_r = v_target_s_t_r
            AND total_val_cents > 0
            AND assess_val_cents > 0
    ),
    subdivision_stats AS (
        -- Subdivision rankings
        SELECT
            COUNT(*) AS property_count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
                CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END
            ) AS median_ratio,
            COUNT(*) FILTER (
                WHERE CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END < v_target_ratio
            ) AS rank_position
        FROM properties
        WHERE subdivname = v_target_subdivision
            AND subdivname IS NOT NULL
            AND total_val_cents > 0
            AND assess_val_cents > 0
    ),
    property_type_stats AS (
        -- Property type rankings
        SELECT
            COUNT(*) AS property_count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
                CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END
            ) AS median_ratio,
            COUNT(*) FILTER (
                WHERE CASE WHEN total_val_cents > 0
                    THEN (assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100
                    ELSE NULL
                END < v_target_ratio
            ) AS rank_position
        FROM properties
        WHERE type_ = v_target_type
            AND type_ IS NOT NULL
            AND total_val_cents > 0
            AND assess_val_cents > 0
    )
    SELECT
        p_target_parcelid AS parcelid,
        v_target_owner AS owner_name,
        v_target_address AS property_address,
        v_target_total_val_cents AS total_value,
        v_target_assess_val_cents AS assess_value,
        ROUND(v_target_ratio, 2) AS assessment_ratio,

        -- Neighborhood rankings
        v_target_s_t_r AS neighborhood_code,
        ns.property_count AS neighborhood_property_count,
        ROUND((ns.rank_position::NUMERIC / NULLIF(ns.property_count, 0)::NUMERIC) * 100, 2) AS neighborhood_percentile,
        ns.rank_position + 1 AS neighborhood_rank,  -- +1 because we're counting properties below
        ROUND(ns.median_ratio, 2) AS neighborhood_median_ratio,

        -- Subdivision rankings
        v_target_subdivision AS subdivision_name,
        COALESCE(ss.property_count, 0) AS subdivision_property_count,
        ROUND((ss.rank_position::NUMERIC / NULLIF(ss.property_count, 0)::NUMERIC) * 100, 2) AS subdivision_percentile,
        ss.rank_position + 1 AS subdivision_rank,
        ROUND(ss.median_ratio, 2) AS subdivision_median_ratio,

        -- Property type rankings
        v_target_type AS property_type,
        pts.property_count AS type_property_count,
        ROUND((pts.rank_position::NUMERIC / NULLIF(pts.property_count, 0)::NUMERIC) * 100, 2) AS type_percentile,
        pts.rank_position + 1 AS type_rank,
        ROUND(pts.median_ratio, 2) AS type_median_ratio,

        -- Fairness indicators
        (v_target_ratio > COALESCE(ns.median_ratio, 0) + 5) AS is_over_assessed,
        (v_target_ratio < COALESCE(ns.median_ratio, 0) - 5) AS is_under_assessed,

        CASE
            WHEN v_target_ratio > COALESCE(ns.median_ratio, 0) + 10 THEN 'SIGNIFICANTLY_OVER_ASSESSED'
            WHEN v_target_ratio > COALESCE(ns.median_ratio, 0) + 5 THEN 'MODERATELY_OVER_ASSESSED'
            WHEN v_target_ratio < COALESCE(ns.median_ratio, 0) - 5 THEN 'UNDER_ASSESSED'
            ELSE 'FAIR'
        END AS fairness_category,

        CASE
            WHEN v_target_ratio > COALESCE(ns.median_ratio, 0) + 10 THEN 'HIGH_POTENTIAL'
            WHEN v_target_ratio > COALESCE(ns.median_ratio, 0) + 5 THEN 'MODERATE_POTENTIAL'
            WHEN v_target_ratio > COALESCE(ns.median_ratio, 0) + 2 THEN 'LOW_POTENTIAL'
            ELSE 'MINIMAL_POTENTIAL'
        END AS potential_savings_indicator

    FROM neighborhood_stats ns
    LEFT JOIN subdivision_stats ss ON TRUE
    LEFT JOIN property_type_stats pts ON TRUE;
END;
$$;

COMMENT ON FUNCTION get_property_percentile_ranking IS
'Ranks property assessment ratio across neighborhood, subdivision, and property type.
Returns percentile rankings, median comparisons, and fairness indicators.
Identifies over/under-assessed properties and savings potential.';

-- ============================================================================
-- 4. BATCH ASSESSMENT FAIRNESS ANALYSIS
-- ============================================================================
-- Purpose: Analyze multiple properties for assessment fairness
-- Used for: Bulk property dashboard, identifying appeal candidates

CREATE OR REPLACE VIEW v_assessment_fairness_summary AS
WITH property_ratios AS (
    SELECT
        p.parcel_id,
        p.ow_name,
        p.ph_add,
        p.subdivname,
        p.s_t_r,
        p.type_,
        p.total_val_cents,
        p.assess_val_cents,
        p.land_val_cents,
        p.imp_val_cents,
        p.acre_area,
        CASE WHEN p.total_val_cents > 0
            THEN ROUND((p.assess_val_cents::NUMERIC / p.total_val_cents::NUMERIC) * 100, 2)
            ELSE NULL
        END AS assessment_ratio
    FROM properties p
    WHERE p.total_val_cents > 0
        AND p.assess_val_cents > 0
),
neighborhood_medians AS (
    SELECT
        s_t_r,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio) AS median_ratio,
        COUNT(*) AS property_count
    FROM property_ratios
    WHERE s_t_r IS NOT NULL
    GROUP BY s_t_r
),
subdivision_medians AS (
    SELECT
        subdivname,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio) AS median_ratio,
        COUNT(*) AS property_count
    FROM property_ratios
    WHERE subdivname IS NOT NULL
    GROUP BY subdivname
)
SELECT
    pr.parcel_id,
    pr.ow_name AS owner_name,
    pr.ph_add AS property_address,
    pr.subdivname AS subdivision,
    pr.s_t_r AS neighborhood,
    pr.type_ AS property_type,
    pr.total_val_cents AS total_value,
    pr.assess_val_cents AS assessed_value,
    pr.assessment_ratio,

    -- Neighborhood comparison
    ROUND(nm.median_ratio, 2) AS neighborhood_median_ratio,
    ROUND(pr.assessment_ratio - nm.median_ratio, 2) AS neighborhood_ratio_diff,

    -- Subdivision comparison (if applicable)
    ROUND(sm.median_ratio, 2) AS subdivision_median_ratio,
    ROUND(pr.assessment_ratio - sm.median_ratio, 2) AS subdivision_ratio_diff,

    -- Fairness flags
    CASE
        WHEN pr.assessment_ratio > nm.median_ratio + 10 THEN 'HIGH_PRIORITY'
        WHEN pr.assessment_ratio > nm.median_ratio + 5 THEN 'MEDIUM_PRIORITY'
        WHEN pr.assessment_ratio > nm.median_ratio + 2 THEN 'LOW_PRIORITY'
        ELSE 'NO_ACTION'
    END AS appeal_priority,

    -- Estimated potential savings (rough calculation)
    CASE
        WHEN pr.assessment_ratio > nm.median_ratio + 5 THEN
            ROUND(
                (pr.assess_val_cents - (pr.total_val_cents * nm.median_ratio / 100))::NUMERIC,
                0
            )
        ELSE 0
    END AS potential_assessment_reduction,

    nm.property_count AS neighborhood_comp_count,
    sm.property_count AS subdivision_comp_count

FROM property_ratios pr
LEFT JOIN neighborhood_medians nm ON pr.s_t_r = nm.s_t_r
LEFT JOIN subdivision_medians sm ON pr.subdivname = sm.subdivname
WHERE pr.assessment_ratio IS NOT NULL;

COMMENT ON VIEW v_assessment_fairness_summary IS
'Comprehensive view of all properties with fairness analysis.
Compares each property to neighborhood and subdivision medians.
Includes appeal priority and potential savings estimates.
Use for bulk analysis and identifying assessment anomalies.';

-- Create index to speed up queries on this view
CREATE INDEX IF NOT EXISTS idx_properties_fairness_analysis
ON properties(s_t_r, subdivname, type_, total_val_cents, assess_val_cents)
WHERE total_val_cents > 0 AND assess_val_cents > 0;

-- ============================================================================
-- 5. TOP OVER-ASSESSED PROPERTIES QUERY
-- ============================================================================
-- Purpose: Identify properties with highest over-assessment potential
-- Used for: Prioritizing appeal candidates

CREATE OR REPLACE VIEW v_top_over_assessed_properties AS
SELECT
    parcel_id,
    owner_name,
    property_address,
    subdivision,
    neighborhood,
    property_type,
    total_value,
    assessed_value,
    assessment_ratio,
    neighborhood_median_ratio,
    neighborhood_ratio_diff,
    subdivision_median_ratio,
    subdivision_ratio_diff,
    appeal_priority,
    potential_assessment_reduction,
    -- Calculate estimated annual tax savings (assuming ~2% tax rate)
    ROUND(potential_assessment_reduction * 0.02, 0) AS estimated_annual_savings,
    neighborhood_comp_count,
    subdivision_comp_count
FROM v_assessment_fairness_summary
WHERE appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
    AND total_value > 5000000  -- Focus on properties with meaningful value (in cents: $50,000 = 5,000,000 cents)
ORDER BY
    CASE appeal_priority
        WHEN 'HIGH_PRIORITY' THEN 1
        WHEN 'MEDIUM_PRIORITY' THEN 2
        ELSE 3
    END,
    potential_assessment_reduction DESC;

COMMENT ON VIEW v_top_over_assessed_properties IS
'Identifies properties most likely to benefit from assessment appeals.
Filters for high/medium priority cases with substantial potential savings.
Ordered by priority and potential reduction amount.';

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Get neighborhood median for a specific property
-- SELECT * FROM get_neighborhood_median_ratio('16-26005-000');

-- Example 2: Get subdivision median for a specific property
-- SELECT * FROM get_subdivision_median_ratio('16-26005-000');

-- Example 3: Get complete percentile ranking analysis
-- SELECT * FROM get_property_percentile_ranking('16-26005-000');

-- Example 4: Find all over-assessed properties in a subdivision
/*
SELECT *
FROM v_assessment_fairness_summary
WHERE subdivision = 'REIGHTON SUB-BVV'
    AND appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
ORDER BY potential_assessment_reduction DESC;
*/

-- Example 5: Summary statistics for entire county
/*
SELECT
    appeal_priority,
    COUNT(*) AS property_count,
    SUM(potential_assessment_reduction) AS total_potential_reduction,
    AVG(neighborhood_ratio_diff) AS avg_ratio_difference,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_value) AS median_property_value
FROM v_assessment_fairness_summary
GROUP BY appeal_priority
ORDER BY appeal_priority;
*/

-- Example 6: Top 100 over-assessed properties
-- SELECT * FROM v_top_over_assessed_properties LIMIT 100;

-- Example 7: Compare property across all dimensions
/*
WITH target_info AS (
    SELECT * FROM get_property_percentile_ranking('16-26005-000')
),
neighborhood_info AS (
    SELECT * FROM get_neighborhood_median_ratio('16-26005-000')
),
subdivision_info AS (
    SELECT * FROM get_subdivision_median_ratio('16-26005-000')
)
SELECT
    ti.parcelid,
    ti.total_value,
    ti.assessment_ratio,
    ti.neighborhood_percentile,
    ti.subdivision_percentile,
    ti.type_percentile,
    ti.fairness_category,
    ti.potential_savings_indicator,
    ni.median_assessment_ratio AS neighborhood_median,
    si.median_assessment_ratio AS subdivision_median,
    ni.interquartile_range AS neighborhood_iqr,
    si.interquartile_range AS subdivision_iqr
FROM target_info ti
CROSS JOIN neighborhood_info ni
CROSS JOIN subdivision_info si;
*/

-- ============================================================================
-- PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Essential indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_properties_str_ratio
ON properties(s_t_r, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
WHERE total_val_cents > 0 AND assess_val_cents > 0;

CREATE INDEX IF NOT EXISTS idx_properties_subdiv_ratio
ON properties(subdivname, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
WHERE subdivname IS NOT NULL AND total_val_cents > 0 AND assess_val_cents > 0;

CREATE INDEX IF NOT EXISTS idx_properties_type_ratio
ON properties(type_, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
WHERE type_ IS NOT NULL AND total_val_cents > 0 AND assess_val_cents > 0;

-- Update statistics after creating indexes
ANALYZE properties;

-- ============================================================================
-- QUERY EXECUTION PLAN NOTES
-- ============================================================================
--
-- For percentile calculations with 173K records:
-- 1. PERCENTILE_CONT uses in-memory sort (expect ~100-300ms)
-- 2. WHERE filters reduce working set before percentile calculation
-- 3. Indexes on s_t_r, subdivname, type_ enable efficient filtering
-- 4. Expression indexes on ratio calculations avoid recomputation
--
-- Expected performance:
-- - get_neighborhood_median_ratio: 50-150ms
-- - get_subdivision_median_ratio: 30-100ms
-- - get_property_percentile_ranking: 100-300ms
-- - v_assessment_fairness_summary (full scan): 2-5 seconds (cache in materialized view)
--
-- ============================================================================
