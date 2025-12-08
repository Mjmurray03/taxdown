-- Simplified comparable matching test query
-- Testing with property: 02-07504-000

WITH target_property AS (
    SELECT
        parcel_id,
        type_,
        total_val_cents,
        assess_val_cents,
        acre_area,
        subdivname,
        geometry
    FROM properties
    WHERE parcel_id = '02-07504-000'
        AND type_ IS NOT NULL
        AND total_val_cents > 0
        AND acre_area > 0
),
comparables AS (
    SELECT
        p.parcel_id,
        'SUBDIVISION' AS match_type,
        0.0 AS distance_miles,
        p.type_,
        p.total_val_cents,
        p.assess_val_cents,
        p.acre_area,
        p.subdivname,
        p.ph_add,
        -- Similarity score (simplified)
        (
            100 - (ABS(p.total_val_cents - t.total_val_cents)::NUMERIC / t.total_val_cents * 100)
        ) AS similarity_score
    FROM properties p, target_property t
    WHERE p.subdivname = t.subdivname
        AND p.subdivname IS NOT NULL
        AND p.parcel_id != t.parcel_id
        AND p.type_ = t.type_
        AND p.total_val_cents BETWEEN t.total_val_cents * 0.80 AND t.total_val_cents * 1.20
        AND p.acre_area BETWEEN t.acre_area * 0.75 AND t.acre_area * 1.25
        AND p.total_val_cents > 0
        AND p.acre_area > 0
    ORDER BY similarity_score DESC
    LIMIT 20
)
SELECT
    parcel_id,
    match_type,
    distance_miles,
    similarity_score::NUMERIC(6,2) as similarity_score,
    total_val_cents,
    assess_val_cents,
    acre_area::NUMERIC(6,2) as acre_area,
    type_,
    subdivname,
    ph_add as property_address
FROM comparables;
