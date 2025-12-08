# SQL Query Design for Taxdown MVP

This directory contains the complete SQL implementation for the Taxdown MVP assessment analysis system.

## Files Overview

| File | Purpose | Lines | Usage |
|------|---------|-------|-------|
| `schema_setup.sql` | Database schema and indexes | ~400 | Run once to create table structure |
| `comparable_matching.sql` | Comparable property matching | ~500 | Load after schema setup |
| `assessment_analytics.sql` | Statistical analytics functions | ~700 | Load after schema setup |
| `test_queries.sql` | Validation and testing | ~600 | Run to verify installation |
| `README.md` | This file | - | Documentation |

## Quick Start

### 1. Database Setup

```bash
# Create database
createdb taxdown

# Connect to database
psql taxdown

# Enable PostGIS extension
CREATE EXTENSION postgis;
```

### 2. Load Schema and Functions

```sql
-- Load in this order:
\i schema_setup.sql
\i comparable_matching.sql
\i assessment_analytics.sql
```

### 3. Import Data

Using ogr2ogr (recommended):

```bash
ogr2ogr -f "PostgreSQL" \
    PG:"host=localhost dbname=taxdown user=postgres" \
    "C:\taxdown\data\raw\Parcels (1)\Parcels.shp" \
    -nln parcels \
    -nlt PROMOTE_TO_MULTI \
    -lco GEOMETRY_NAME=geometry \
    -t_srs EPSG:3433 \
    -overwrite
```

Or using shp2pgsql:

```bash
shp2pgsql -I -s 3433 "C:\taxdown\data\raw\Parcels (1)\Parcels.shp" parcels | \
    psql -h localhost -d taxdown
```

After import, you may need to rename columns to lowercase (see schema_setup.sql comments).

### 4. Run Tests

```sql
\i test_queries.sql
```

## Core Functions

### 1. Comparable Property Matching

**Function:** `find_comparable_properties(parcel_id VARCHAR)`

Finds the top 20 comparable properties for assessment analysis.

**Strategy:**
- Priority 1: Same subdivision (if ≥5 matches)
- Priority 2: Within 0.5 miles radius

**Filters:**
- Same property type
- ±20% total value
- ±25% acreage

**Returns:** 20 columns including similarity score, property details, and comparative metrics

**Example:**
```sql
SELECT * FROM find_comparable_properties('16-26005-000');
```

### 2. Neighborhood Median Assessment Ratio

**Function:** `get_neighborhood_median_ratio(parcel_id VARCHAR)`

Calculates median assessment ratio for all properties in the same neighborhood (S_T_R).

**Returns:**
- Median, mean, min, max, stddev
- Quartiles (25th, 75th percentiles)
- IQR (interquartile range)
- Comparison to target property

**Example:**
```sql
SELECT * FROM get_neighborhood_median_ratio('16-26005-000');
```

### 3. Subdivision Median Assessment Ratio

**Function:** `get_subdivision_median_ratio(parcel_id VARCHAR)`

Similar to neighborhood analysis but for specific subdivisions (more granular).

**Returns:**
- Same statistics as neighborhood
- Median property values (total, land, improvement)

**Example:**
```sql
SELECT * FROM get_subdivision_median_ratio('16-26005-000');
```

### 4. Property Percentile Ranking

**Function:** `get_property_percentile_ranking(parcel_id VARCHAR)`

Ranks property's assessment ratio across multiple dimensions.

**Dimensions:**
- Neighborhood (by S_T_R)
- Subdivision (if applicable)
- Property type (county-wide)

**Returns:**
- Percentile rankings (0-100)
- Actual rank positions
- Fairness indicators
- Savings potential assessment

**Example:**
```sql
SELECT * FROM get_property_percentile_ranking('16-26005-000');
```

## Views

### 1. Assessment Fairness Summary

**View:** `v_assessment_fairness_summary`

Pre-calculated fairness analysis for all properties.

**Use Cases:**
- Bulk property dashboard
- Identifying appeal candidates
- Portfolio analysis

**Columns:**
- Property details and values
- Neighborhood/subdivision comparisons
- Appeal priority (HIGH/MEDIUM/LOW/NO_ACTION)
- Potential assessment reduction

**Example:**
```sql
SELECT * FROM v_assessment_fairness_summary
WHERE appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
ORDER BY potential_assessment_reduction DESC
LIMIT 100;
```

### 2. Top Over-Assessed Properties

**View:** `v_top_over_assessed_properties`

Pre-filtered list of best appeal candidates.

**Filters:**
- Appeal priority = HIGH or MEDIUM
- Total value > $50,000

**Includes:**
- Estimated annual tax savings

**Example:**
```sql
SELECT * FROM v_top_over_assessed_properties LIMIT 20;
```

## Performance

### Expected Query Times (173K records)

| Query | Target | Typical |
|-------|--------|---------|
| find_comparable_properties | <300ms | 100-200ms |
| get_neighborhood_median_ratio | <150ms | 50-100ms |
| get_subdivision_median_ratio | <100ms | 30-80ms |
| get_property_percentile_ranking | <300ms | 150-250ms |
| v_assessment_fairness_summary (full) | 2-5s | 3-4s |

### Performance Optimization

**1. Verify Indexes:**
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'parcels';
```

Should see 12+ indexes including:
- idx_parcels_geometry (GIST)
- idx_parcels_subdivname
- idx_parcels_type_val_acre
- idx_parcels_str_ratio

**2. Update Statistics:**
```sql
ANALYZE parcels;
```

**3. Check Configuration:**
```sql
SHOW work_mem;          -- Should be ≥64MB
SHOW shared_buffers;    -- Should be ≥2GB (25% of RAM)
SHOW effective_cache_size;  -- Should be ≥6GB (75% of RAM)
```

**4. Analyze Query Plans:**
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM find_comparable_properties('16-26005-000');
```

Look for:
- Index scans (not sequential scans)
- Low cost estimates (<1000)
- Fast execution times

## Common Use Cases

### Use Case 1: Generate Appeal Letter Data

```sql
WITH target AS (
    SELECT * FROM parcels WHERE parcelid = '16-26005-000'
),
comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
    WHERE similarity_score >= 70
),
ranking AS (
    SELECT * FROM get_property_percentile_ranking('16-26005-000')
),
neighborhood AS (
    SELECT * FROM get_neighborhood_median_ratio('16-26005-000')
)
SELECT
    t.parcelid,
    t.ow_name,
    t.total_val AS current_value,
    t.assess_val AS current_assessment,
    n.median_assessment_ratio AS neighborhood_median,
    r.fairness_category,
    json_agg(json_build_object(
        'parcel_id', c.comparable_parcelid,
        'address', c.property_address,
        'value', c.total_value,
        'ratio', c.assessment_ratio,
        'similarity', c.similarity_score
    )) AS comparable_properties
FROM target t
CROSS JOIN comparables c
CROSS JOIN ranking r
CROSS JOIN neighborhood n
GROUP BY t.parcelid, t.ow_name, t.total_val, t.assess_val,
         n.median_assessment_ratio, r.fairness_category;
```

### Use Case 2: Analyze Portfolio

```sql
WITH portfolio AS (
    SELECT unnest(ARRAY['16-26005-000', '02-13045-000']) AS parcelid
)
SELECT
    r.parcelid,
    r.total_value,
    r.assessment_ratio,
    r.neighborhood_percentile,
    r.fairness_category,
    r.potential_savings_indicator,
    CASE WHEN r.is_over_assessed
        THEN r.assess_value - (r.total_value * r.neighborhood_median_ratio / 100)
        ELSE 0
    END AS potential_reduction
FROM portfolio p
CROSS JOIN LATERAL get_property_percentile_ranking(p.parcelid) r
ORDER BY potential_reduction DESC;
```

### Use Case 3: Find All Over-Assessed in Subdivision

```sql
SELECT
    parcelid,
    owner_name,
    property_address,
    total_value,
    assessment_ratio,
    neighborhood_median_ratio,
    neighborhood_ratio_diff,
    potential_assessment_reduction
FROM v_assessment_fairness_summary
WHERE subdivision = 'REIGHTON SUB-BVV'
    AND appeal_priority IN ('HIGH_PRIORITY', 'MEDIUM_PRIORITY')
ORDER BY potential_assessment_reduction DESC;
```

### Use Case 4: County-Wide Equity Analysis

```sql
SELECT
    type_ AS property_type,
    COUNT(*) AS count,
    ROUND(AVG(CASE WHEN total_val > 0
        THEN (assess_val::NUMERIC / total_val::NUMERIC) * 100
        ELSE NULL
    END), 2) AS avg_ratio,
    ROUND(STDDEV(CASE WHEN total_val > 0
        THEN (assess_val::NUMERIC / total_val::NUMERIC) * 100
        ELSE NULL
    END), 2) AS stddev_ratio,
    -- Coefficient of Dispersion (lower is better)
    ROUND((AVG(ABS(
        (assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100) -
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
            assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100
        )
    )) / NULLIF(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
        assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100
    ), 0)) * 100, 2) AS coefficient_of_dispersion
FROM parcels
WHERE total_val > 0 AND assess_val > 0 AND type_ IS NOT NULL
GROUP BY type_
ORDER BY count DESC;
```

## Troubleshooting

### Issue: No Comparable Properties Found

**Cause:** Target property may have NULL values or be unusual

**Solution:**
```sql
-- Check target property
SELECT parcelid, type_, total_val, acre_area, subdivname
FROM parcels
WHERE parcelid = 'YOUR_PARCEL_ID';

-- Relax filters manually to see what's available
SELECT COUNT(*)
FROM parcels
WHERE type_ = 'RV'
  AND total_val BETWEEN 5000 AND 15000
  AND acre_area BETWEEN 0.2 AND 0.6;
```

### Issue: Slow Query Performance

**Cause:** Missing indexes or outdated statistics

**Solution:**
```sql
-- Verify indexes exist
\d parcels

-- Update statistics
ANALYZE parcels;

-- Check query plan
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM find_comparable_properties('YOUR_PARCEL_ID');

-- If you see "Seq Scan", create missing indexes
-- See schema_setup.sql for index definitions
```

### Issue: Percentile Calculation Timeout

**Cause:** Insufficient work_mem or large result set

**Solution:**
```sql
-- Increase work_mem for session
SET work_mem = '128MB';

-- Or use materialized view for batch processing
CREATE MATERIALIZED VIEW mv_property_rankings AS
SELECT p.parcelid, r.*
FROM parcels p
CROSS JOIN LATERAL get_property_percentile_ranking(p.parcelid) r
WHERE p.total_val > 50000;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_property_rankings;
```

## Database Maintenance

### Daily Tasks

```sql
-- Update statistics (run nightly)
ANALYZE parcels;
```

### Weekly Tasks

```sql
-- Vacuum to reclaim space
VACUUM ANALYZE parcels;

-- Refresh materialized views (if created)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_assessment_fairness_summary;
```

### Monthly Tasks

```sql
-- Full vacuum with index rebuild
VACUUM FULL ANALYZE parcels;

-- Reindex
REINDEX TABLE parcels;
```

## Documentation

For detailed documentation, see:
- **docs/query_design.md** - Complete query design documentation
- **schema_setup.sql** - Comments on schema and indexes
- **comparable_matching.sql** - Function documentation
- **assessment_analytics.sql** - Analytics documentation

## Support

For issues or questions:
1. Check EXPLAIN ANALYZE output
2. Verify indexes exist and are being used
3. Review query_design.md for algorithm details
4. Check PostgreSQL logs for errors

## Version

**Version:** 1.0
**Date:** 2025-12-07
**Database:** PostgreSQL 14+ with PostGIS 3+
**Dataset:** 173,743 parcels (Benton County, Arkansas)
