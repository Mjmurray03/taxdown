-- ============================================================================
-- QUICK REFERENCE GUIDE - TAXDOWN ASSESSMENT ANALYSIS
-- ============================================================================
-- PostgreSQL + PostGIS
-- Common queries and usage patterns
-- Copy and paste these queries, replacing parcel IDs with your data
-- ============================================================================

-- ============================================================================
-- BASIC QUERIES
-- ============================================================================

-- Find a specific property
SELECT *
FROM properties
WHERE parcel_id = '16-26005-000';

-- Search by owner name
SELECT parcel_id, ow_name, ph_add, total_val_cents, assess_val_cents
FROM properties
WHERE ow_name ILIKE '%SMITH%'
ORDER BY total_val_cents DESC;

-- Find properties in a subdivision
SELECT parcel_id, ow_name, ph_add, total_val_cents
FROM properties
WHERE subdivname = 'REIGHTON SUB-BVV'
ORDER BY total_val_cents DESC;

-- ============================================================================
-- COMPARABLE PROPERTY QUERIES
-- ============================================================================

-- Basic: Find comparables for a property
SELECT *
FROM find_comparable_properties('16-26005-000');

-- Get just the top 5 best matches
SELECT
    comparable_parcelid,
    similarity_score,
    property_address,
    total_value,
    assessment_ratio,
    distance_miles
FROM find_comparable_properties('16-26005-000')
ORDER BY similarity_score DESC
LIMIT 5;

-- Get comparables with only high similarity (>80)
SELECT *
FROM find_comparable_properties('16-26005-000')
WHERE similarity_score > 80;

-- Compare target property to its comparables
WITH target AS (
    SELECT
        parcel_id,
        total_val_cents,
        assess_val_cents,
        ROUND((assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100, 2) AS ratio
    FROM properties
    WHERE parcel_id = '16-26005-000'
),
comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
)
SELECT
    t.parcel_id AS my_parcel,
    t.total_val_cents AS my_value,
    t.ratio AS my_ratio,
    COUNT(c.*) AS comparable_count,
    ROUND(AVG(c.assessment_ratio), 2) AS avg_comparable_ratio,
    ROUND(AVG(c.similarity_score), 2) AS avg_similarity,
    t.ratio - ROUND(AVG(c.assessment_ratio), 2) AS ratio_difference,
    CASE
        WHEN t.ratio > AVG(c.assessment_ratio) + 5 THEN 'OVER-ASSESSED'
        WHEN t.ratio < AVG(c.assessment_ratio) - 5 THEN 'UNDER-ASSESSED'
        ELSE 'FAIR'
    END AS assessment_status
FROM target t
CROSS JOIN comparables c
GROUP BY t.parcel_id, t.total_val_cents, t.ratio;

-- ============================================================================
-- NEIGHBORHOOD ANALYSIS QUERIES
-- ============================================================================

-- Get neighborhood statistics for a property
SELECT *
FROM get_neighborhood_median_ratio('16-26005-000');

-- Simple format: Am I over-assessed compared to neighbors?
SELECT
    parcel_id AS my_parcel,
    neighborhood_code,
    property_count AS neighbor_count,
    target_property_ratio AS my_ratio,
    median_assessment_ratio AS neighbor_median,
    target_vs_median_diff AS difference,
    CASE
        WHEN target_vs_median_diff > 10 THEN 'SIGNIFICANTLY OVER-ASSESSED'
        WHEN target_vs_median_diff > 5 THEN 'MODERATELY OVER-ASSESSED'
        WHEN target_vs_median_diff < -5 THEN 'UNDER-ASSESSED'
        ELSE 'FAIR'
    END AS status
FROM get_neighborhood_median_ratio('16-26005-000');

-- ============================================================================
-- SUBDIVISION ANALYSIS QUERIES
-- ============================================================================

-- Get subdivision statistics for a property
SELECT *
FROM get_subdivision_median_ratio('16-26005-000');

-- Compare neighborhood vs subdivision
WITH n AS (
    SELECT * FROM get_neighborhood_median_ratio('16-26005-000')
),
s AS (
    SELECT * FROM get_subdivision_median_ratio('16-26005-000')
)
SELECT
    'My Property' AS level,
    n.target_property_ratio AS ratio,
    NULL::BIGINT AS property_count
FROM n
UNION ALL
SELECT
    'Neighborhood Average' AS level,
    n.median_assessment_ratio AS ratio,
    n.property_count
FROM n
UNION ALL
SELECT
    'Subdivision Average' AS level,
    s.median_assessment_ratio AS ratio,
    s.property_count
FROM s;

-- ============================================================================
-- PERCENTILE RANKING QUERIES
-- ============================================================================

-- Get complete percentile ranking for a property
SELECT *
FROM get_property_percentile_ranking('16-26005-000');

-- Simple format: Where do I rank?
SELECT
    parcel_id AS my_parcel,
    total_value,
    assessment_ratio AS my_ratio,
    neighborhood_percentile,
    CASE
        WHEN neighborhood_percentile >= 90 THEN 'Top 10% (Highest assessed)'
        WHEN neighborhood_percentile >= 75 THEN 'Top 25%'
        WHEN neighborhood_percentile >= 50 THEN 'Above average'
        WHEN neighborhood_percentile >= 25 THEN 'Below average'
        ELSE 'Bottom 25% (Lowest assessed)'
    END AS ranking_description,
    fairness_category,
    potential_savings_indicator
FROM get_property_percentile_ranking('16-26005-000');

-- ============================================================================
-- APPEAL CANDIDATE QUERIES
-- ============================================================================

-- Find all over-assessed properties (high priority)
SELECT
    parcel_id,
    owner_name,
    property_address,
    total_value,
    assessment_ratio,
    neighborhood_median_ratio,
    neighborhood_ratio_diff AS over_assessed_by,
    potential_assessment_reduction AS potential_savings
FROM v_assessment_fairness_summary
WHERE appeal_priority = 'HIGH_PRIORITY'
ORDER BY potential_assessment_reduction DESC
LIMIT 100;

-- Find over-assessed properties in specific subdivision
SELECT
    parcel_id,
    owner_name,
    property_address,
    total_value,
    assessment_ratio,
    neighborhood_median_ratio,
    potential_assessment_reduction
FROM v_assessment_fairness_summary
WHERE subdivision = 'REIGHTON SUB-BVV'
    AND appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
ORDER BY potential_assessment_reduction DESC;

-- Find over-assessed properties by property type
SELECT
    property_type,
    COUNT(*) AS over_assessed_count,
    ROUND(AVG(total_value), 0) AS avg_value,
    ROUND(AVG(potential_assessment_reduction), 0) AS avg_potential_savings
FROM v_assessment_fairness_summary
WHERE appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
GROUP BY property_type
ORDER BY over_assessed_count DESC;

-- ============================================================================
-- PORTFOLIO ANALYSIS QUERIES
-- ============================================================================

-- Analyze multiple properties (portfolio)
WITH my_properties AS (
    SELECT unnest(ARRAY[
        '16-26005-000',
        '02-13045-000',
        '18-11331-002'
    ]) AS parcel_id
)
SELECT
    r.parcel_id,
    r.owner_name,
    r.property_address,
    r.total_value,
    r.assessment_ratio,
    r.neighborhood_median_ratio,
    r.neighborhood_percentile,
    r.fairness_category,
    CASE WHEN r.is_over_assessed
        THEN r.assess_value - (r.total_value * r.neighborhood_median_ratio / 100)
        ELSE 0
    END AS potential_reduction
FROM my_properties p
CROSS JOIN LATERAL get_property_percentile_ranking(p.parcel_id) r
ORDER BY potential_reduction DESC;

-- Portfolio summary statistics
WITH my_properties AS (
    SELECT unnest(ARRAY[
        '16-26005-000',
        '02-13045-000'
    ]) AS parcel_id
)
SELECT
    COUNT(*) AS total_properties,
    SUM(p.total_val_cents) AS total_portfolio_value,
    SUM(p.assess_val_cents) AS total_assessed_value,
    ROUND(100.0 * SUM(p.assess_val_cents) / SUM(p.total_val_cents), 2) AS portfolio_avg_ratio,
    COUNT(*) FILTER (WHERE f.appeal_priority = 'HIGH_PRIORITY') AS high_priority_appeals,
    COUNT(*) FILTER (WHERE f.appeal_priority = 'MEDIUM_PRIORITY') AS medium_priority_appeals,
    ROUND(SUM(f.potential_assessment_reduction), 0) AS total_potential_savings
FROM my_properties mp
JOIN properties p ON p.parcel_id = mp.parcel_id
LEFT JOIN v_assessment_fairness_summary f ON f.parcel_id = mp.parcel_id;

-- ============================================================================
-- APPEAL LETTER DATA QUERIES
-- ============================================================================

-- Get all data needed for an appeal letter
WITH target AS (
    SELECT
        parcel_id,
        ow_name,
        ph_add,
        total_val_cents,
        assess_val_cents,
        type_,
        acre_area,
        subdivname
    FROM properties
    WHERE parcel_id = '16-26005-000'
),
comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
    WHERE similarity_score >= 70
    LIMIT 10
),
ranking AS (
    SELECT * FROM get_property_percentile_ranking('16-26005-000')
),
neighborhood AS (
    SELECT * FROM get_neighborhood_median_ratio('16-26005-000')
)
SELECT
    -- Property information
    t.parcel_id,
    t.ow_name AS owner,
    t.ph_add AS address,

    -- Current assessment
    t.total_val_cents AS current_market_value,
    t.assess_val_cents AS current_assessed_value,
    ROUND((t.assess_val_cents::NUMERIC / t.total_val_cents) * 100, 2) AS current_ratio,

    -- Neighborhood comparison
    n.median_assessment_ratio AS neighborhood_median,
    n.property_count AS neighborhood_count,
    ROUND((t.assess_val_cents::NUMERIC / t.total_val_cents) * 100 - n.median_assessment_ratio, 2) AS over_assessed_by,

    -- Ranking
    r.neighborhood_percentile,
    r.fairness_category,

    -- Recommended assessment
    ROUND(t.total_val_cents * n.median_assessment_ratio / 100, 0) AS recommended_assessment,
    ROUND(t.assess_val_cents - (t.total_val_cents * n.median_assessment_ratio / 100), 0) AS requested_reduction,

    -- Comparables (as JSON array)
    (SELECT json_agg(json_build_object(
        'parcel_id', comparable_parcelid,
        'address', property_address,
        'total_value', total_value,
        'assessed_value', assess_value,
        'assessment_ratio', assessment_ratio,
        'similarity_score', similarity_score,
        'distance_miles', distance_miles
    ) ORDER BY similarity_score DESC)
    FROM comparables) AS comparable_properties

FROM target t
CROSS JOIN neighborhood n
CROSS JOIN ranking r;

-- ============================================================================
-- GEOGRAPHIC/SPATIAL QUERIES
-- ============================================================================

-- Find properties near a specific location (0.5 mile radius)
WITH target AS (
    SELECT geometry FROM properties WHERE parcel_id = '16-26005-000'
)
SELECT
    p.parcel_id,
    p.ow_name,
    p.ph_add,
    p.total_val_cents,
    ROUND(
        ST_Distance(
            ST_Transform(p.geometry, 4326)::geography,
            ST_Transform(t.geometry, 4326)::geography
        ) * 0.000621371,  -- Convert meters to miles
        3
    ) AS distance_miles
FROM properties p, target t
WHERE ST_DWithin(
    ST_Transform(p.geometry, 4326)::geography,
    ST_Transform(t.geometry, 4326)::geography,
    804.67  -- 0.5 miles in meters
)
AND p.parcel_id != '16-26005-000'
ORDER BY distance_miles
LIMIT 20;

-- ============================================================================
-- STATISTICAL ANALYSIS QUERIES
-- ============================================================================

-- County-wide assessment ratio distribution
SELECT
    CASE
        WHEN ratio < 15 THEN '0-15%'
        WHEN ratio < 18 THEN '15-18%'
        WHEN ratio < 20 THEN '18-20%'
        WHEN ratio < 22 THEN '20-22%'
        WHEN ratio < 25 THEN '22-25%'
        ELSE '25%+'
    END AS ratio_range,
    COUNT(*) AS property_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM (
    SELECT
        ROUND((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100, 2) AS ratio
    FROM properties
    WHERE total_val_cents > 0 AND assess_val_cents > 0
) AS ratios
GROUP BY ratio_range
ORDER BY ratio_range;

-- Property type assessment statistics
SELECT
    type_ AS property_type,
    COUNT(*) AS count,
    ROUND(AVG(total_val_cents), 0) AS avg_total_value,
    ROUND(AVG(assess_val_cents), 0) AS avg_assessed_value,
    ROUND(AVG((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100), 2) AS avg_ratio,
    ROUND(STDDEV((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100), 2) AS stddev_ratio
FROM properties
WHERE total_val_cents > 0 AND assess_val_cents > 0 AND type_ IS NOT NULL
GROUP BY type_
ORDER BY count DESC;

-- Subdivision assessment uniformity
SELECT
    subdivname,
    COUNT(*) AS property_count,
    ROUND(AVG(total_val_cents), 0) AS avg_value,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (
        ORDER BY (assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100
    ), 2) AS median_ratio,
    ROUND(STDDEV((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100), 2) AS stddev_ratio,
    -- Coefficient of Dispersion (lower = more uniform)
    ROUND((AVG(ABS(
        (assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0) * 100) -
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0) * 100)
    )) / NULLIF(PERCENTILE_CONT(0.50) WITHIN GROUP (
        ORDER BY assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0) * 100
    ), 0)) * 100, 2) AS coefficient_of_dispersion
FROM properties
WHERE total_val_cents > 0
    AND assess_val_cents > 0
    AND subdivname IS NOT NULL
GROUP BY subdivname
HAVING COUNT(*) >= 10  -- Only subdivisions with 10+ properties
ORDER BY coefficient_of_dispersion
LIMIT 20;

-- ============================================================================
-- BATCH EXPORT QUERIES
-- ============================================================================

-- Export all high-priority appeals to CSV
-- Run with: \copy (...) TO 'high_priority_appeals.csv' CSV HEADER
SELECT
    parcel_id AS "Parcel ID",
    owner_name AS "Owner",
    property_address AS "Address",
    subdivision AS "Subdivision",
    total_value AS "Total Value",
    assessed_value AS "Assessed Value",
    assessment_ratio AS "Current Ratio %",
    neighborhood_median_ratio AS "Neighborhood Median %",
    neighborhood_ratio_diff AS "Over-Assessed By %",
    potential_assessment_reduction AS "Potential Reduction $",
    ROUND(potential_assessment_reduction * 0.02, 0) AS "Est. Annual Savings $"
FROM v_assessment_fairness_summary
WHERE appeal_priority = 'HIGH_PRIORITY'
ORDER BY potential_assessment_reduction DESC;

-- ============================================================================
-- NOTES
-- ============================================================================

-- Replace '16-26005-000' with your actual parcel ID
-- Replace subdivision names with actual subdivisions in your data
-- Adjust similarity score thresholds (70, 80) based on data quality
-- For portfolio queries, replace the parcel ID array with your properties
-- All ratio percentages are 0-100 (not 0-1)
-- Arkansas typically uses 20% assessment ratio for residential property

-- ============================================================================
-- PERFORMANCE TIPS
-- ============================================================================

-- If queries are slow:
-- 1. Update statistics: ANALYZE parcels;
-- 2. Check indexes: \d parcels
-- 3. Increase work_mem: SET work_mem = '128MB';
-- 4. Check query plan: EXPLAIN ANALYZE <your query>;

-- For large result sets:
-- Use LIMIT to restrict results
-- Filter by total_val_cents > 5000000 to focus on meaningful properties (values in cents)
-- Use materialized views for frequently accessed summaries
