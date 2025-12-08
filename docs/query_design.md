# Assessment Analysis Query Design Documentation

**Version:** 1.0
**Date:** 2025-12-07
**Database:** PostgreSQL 14+ with PostGIS 3+
**Dataset Size:** 173,743 parcels (Benton County, Arkansas)

---

## Table of Contents

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Comparable Property Matching](#comparable-property-matching)
4. [Assessment Analytics](#assessment-analytics)
5. [Performance Optimization](#performance-optimization)
6. [Usage Examples](#usage-examples)
7. [Query Execution Plans](#query-execution-plans)

---

## Overview

This document describes the SQL query design for the Taxdown MVP assessment analysis system. The system consists of two main components:

1. **Comparable Property Matching** - Finds similar properties for fairness scoring
2. **Assessment Analytics** - Calculates neighborhood/subdivision statistics and percentile rankings

### Design Goals

- **Accuracy**: Prioritize subdivision matches (highest granularity), fall back to proximity
- **Performance**: Optimize for 173K records with sub-300ms query times
- **Transparency**: Provide detailed scoring breakdowns and statistical confidence
- **Scalability**: Use spatial indexes and efficient algorithms

### Data Source

Data comes from Arkansas GIS Office FeatureServer API via Benton County shapefiles:
- 173,743 total parcels
- EPSG:3433 coordinate system (Arkansas State Plane North)
- 16 core attributes including valuations, owner info, and spatial data

---

## Database Schema

### Parcels Table

Based on the extracted shapefile data:

```sql
CREATE TABLE parcels (
    -- Primary identification
    parcelid VARCHAR(50),           -- Parcel ID (e.g., '16-26005-000')

    -- Property characteristics
    type_ VARCHAR(10),              -- Property type (RV, RI, AV, EG, etc.)
    acre_area NUMERIC(10, 2),       -- Acreage
    gis_est_ac NUMERIC(10, 2),      -- GIS-estimated acreage

    -- Valuation data (CRITICAL)
    total_val BIGINT,               -- Total market value
    assess_val BIGINT,              -- Assessed value (for tax purposes)
    land_val BIGINT,                -- Land value only
    imp_val BIGINT,                 -- Improvement/building value

    -- Owner information
    ow_name VARCHAR(200),           -- Owner name
    ow_add VARCHAR(200),            -- Owner mailing address
    ph_add VARCHAR(200),            -- Physical address

    -- Location/geography
    s_t_r VARCHAR(20),              -- Section-Township-Range (neighborhood identifier)
    subdivname VARCHAR(200),        -- Subdivision name
    schl_code VARCHAR(10),          -- School district code

    -- Spatial
    geometry GEOMETRY(MultiPolygon, 3433),  -- Parcel boundary
    shape_leng NUMERIC,             -- Perimeter length
    shape_area NUMERIC,             -- Area in square feet

    -- Indexes for performance
    CONSTRAINT pk_parcels PRIMARY KEY (parcelid)
);
```

### Required Indexes

```sql
-- Spatial index (CRITICAL for performance)
CREATE INDEX idx_parcels_geometry ON parcels USING GIST(geometry);

-- Subdivision matching
CREATE INDEX idx_parcels_subdivname ON parcels(subdivname)
    WHERE subdivname IS NOT NULL;

-- Property type filtering
CREATE INDEX idx_parcels_type ON parcels(type_)
    WHERE type_ IS NOT NULL;

-- Value-based filtering
CREATE INDEX idx_parcels_total_val ON parcels(total_val)
    WHERE total_val > 0;

-- Acreage filtering
CREATE INDEX idx_parcels_acre_area ON parcels(acre_area)
    WHERE acre_area > 0;

-- Composite index for common filter combinations
CREATE INDEX idx_parcels_type_val_acre ON parcels(type_, total_val, acre_area)
    WHERE type_ IS NOT NULL AND total_val > 0 AND acre_area > 0;

-- Analytics indexes (ratio calculations)
CREATE INDEX idx_parcels_str_ratio
    ON parcels(s_t_r, ((assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC)))
    WHERE total_val > 0 AND assess_val > 0;

CREATE INDEX idx_parcels_subdiv_ratio
    ON parcels(subdivname, ((assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC)))
    WHERE subdivname IS NOT NULL AND total_val > 0 AND assess_val > 0;
```

### Property Type Codes

Based on observed data:

- **RV**: Residential Vacant Land
- **RI**: Residential Improved (with building)
- **AV**: Agricultural Vacant
- **AI**: Agricultural Improved
- **EG**: Exempt Government
- **CV**: Commercial Vacant
- **CI**: Commercial Improved

---

## Comparable Property Matching

### Algorithm Overview

The comparable property matching algorithm (`find_comparable_properties`) uses a **two-tier strategy**:

1. **Tier 1: Subdivision Matches** (Priority)
   - Search within the same subdivision
   - If ≥5 matches found, return these (most accurate comparables)

2. **Tier 2: Proximity Matches** (Fallback)
   - Search within 0.5 miles radius
   - Only used if <5 subdivision matches
   - Still filters by type, value, and acreage

### Matching Criteria

| Criterion | Filter Rule | Rationale |
|-----------|-------------|-----------|
| **Property Type** | Exact match | Different types have fundamentally different values |
| **Total Value** | ±20% | Allows variation while staying comparable |
| **Acreage** | ±25% | Lot size significantly impacts assessment |
| **Location** | Same subdivision OR <0.5 miles | Location is primary value driver |

### Similarity Scoring

Properties are scored 0-100 based on weighted criteria:

```
Similarity Score = (Type × 10%) + (Value × 35%) + (Acreage × 30%) + (Location × 25%)
```

#### Component Scores

**1. Type Match Score (10% weight)**
- 100 if exact match (enforced by filter)
- 0 if different type (excluded by filter)

**2. Value Match Score (35% weight)**
- 100 if exact value match
- Linear decay: 100 - (|value_diff%| × 5)
- Example: 10% difference = 100 - (10 × 5) = 50 points
- 0 at 20% difference (filter boundary)

**3. Acreage Match Score (30% weight)**
- 100 if exact acreage match
- Linear decay: 100 - (|acreage_diff%| × 4)
- Example: 15% difference = 100 - (15 × 4) = 40 points
- 0 at 25% difference (filter boundary)

**4. Location Score (25% weight)**
- 100 if same subdivision
- Linear decay for proximity: 100 - (distance_miles × 200)
- Example: 0.25 miles = 100 - (0.25 × 200) = 50 points
- 0 at 0.5 miles (filter boundary)

### Output Fields

The function returns 20 columns per comparable:

**Identification**
- `comparable_parcelid`: Parcel ID of comparable property
- `match_type`: 'SUBDIVISION' or 'PROXIMITY'

**Scoring**
- `similarity_score`: Overall score (0-100)
- `type_match_score`, `value_match_score`, `acreage_match_score`, `location_score`: Component breakdowns

**Property Details**
- `total_value`, `assess_value`, `land_value`, `imp_value`
- `acre_area`, `property_type`
- `owner_name`, `property_address`, `subdivision`

**Comparative Metrics**
- `distance_miles`: Distance from target (0 for subdivision matches)
- `assessment_ratio`: Assessed value / Total value × 100
- `value_difference_pct`: % difference from target value
- `acreage_difference_pct`: % difference from target acreage

### Query Logic Flow

```sql
-- Pseudocode representation
WITH target_property AS (
    -- Get characteristics of target property
    SELECT type_, total_val, acre_area, subdivname, geometry
    FROM parcels WHERE parcelid = @target
),

subdivision_matches AS (
    -- Find matches in same subdivision
    SELECT * FROM parcels
    WHERE subdivname = target.subdivname
      AND type_ = target.type_
      AND total_val BETWEEN target.total_val * 0.8 AND 1.2
      AND acre_area BETWEEN target.acre_area * 0.75 AND 1.25
),

proximity_matches AS (
    -- Find matches within 0.5 miles (if needed)
    SELECT * FROM parcels
    WHERE ST_DWithin(geometry, target.geometry, 804.67)  -- 0.5 miles in meters
      AND type_ = target.type_
      AND total_val BETWEEN target.total_val * 0.8 AND 1.2
      AND acre_area BETWEEN target.acre_area * 0.75 AND 1.25
      AND (subdivision_count >= 5 OR subdivname != target.subdivname)
),

scored_comparables AS (
    -- Calculate similarity scores
    SELECT *,
        (type_score * 0.10 + value_score * 0.35 +
         acreage_score * 0.30 + location_score * 0.25) AS similarity_score
    FROM (subdivision_matches UNION ALL proximity_matches)
)

-- Return top 20, prioritizing subdivision matches
SELECT * FROM scored_comparables
ORDER BY
    CASE WHEN match_type = 'SUBDIVISION' AND count >= 5 THEN 0 ELSE 1 END,
    similarity_score DESC,
    distance_miles ASC
LIMIT 20;
```

### Spatial Operations

**PostGIS Functions Used:**

1. **ST_DWithin(geog1, geog2, distance_meters)**
   - Efficient spatial filter using GIST index
   - Returns TRUE if geometries are within specified distance
   - Used for: Initial proximity filtering

2. **ST_Distance(geog1, geog2)**
   - Calculates exact distance between geometries
   - Returns distance in meters (when using geography type)
   - Used for: Display and sorting

3. **ST_Transform(geom, srid)**
   - Converts between coordinate systems
   - Used for: Converting EPSG:3433 → EPSG:4326 for accurate distance calculations
   - EPSG:4326 = WGS84 (latitude/longitude)
   - Geography type ensures accurate great-circle distances

**Coordinate System Strategy:**

```sql
-- Store in original projection for efficiency
geometry GEOMETRY(MultiPolygon, 3433)

-- Transform to geography for distance calculations
ST_Transform(geometry, 4326)::geography
```

This approach:
- Maintains spatial index efficiency (EPSG:3433)
- Provides accurate distance calculations (geography type)
- Minimizes transformation overhead (only for results, not filters)

---

## Assessment Analytics

### 1. Neighborhood Median Assessment Ratio

**Function:** `get_neighborhood_median_ratio(parcelid)`

**Purpose:** Calculate median assessment ratio for all properties in the same S_T_R (Section-Township-Range), which represents a neighborhood.

**Algorithm:**

```
1. Get target property's S_T_R and assessment ratio
2. Find all properties in same S_T_R with valid assessments
3. Calculate:
   - Median ratio (PERCENTILE_CONT 0.50)
   - Mean ratio (AVG)
   - Min/Max ratios
   - Standard deviation
   - 25th and 75th percentiles (for IQR)
4. Compare target property ratio to neighborhood statistics
```

**Key Metrics:**

- **Assessment Ratio** = (Assessed Value / Total Value) × 100
  - Arkansas typically uses 20% for residential property
  - Uniformity is key - all similar properties should have similar ratios

- **Interquartile Range (IQR)** = P75 - P25
  - Measures spread of middle 50% of data
  - Low IQR indicates consistent assessments
  - High IQR suggests assessment inequality

**Output:**
- Neighborhood statistics (count, median, mean, stddev, quartiles)
- Target property ratio
- Difference from median
- IQR for consistency assessment

### 2. Subdivision Median Assessment Ratio

**Function:** `get_subdivision_median_ratio(parcelid)`

**Purpose:** More granular analysis within specific subdivisions (typically 10-200 properties).

**Differences from Neighborhood Analysis:**

- Smaller geographic scope (subdivision vs. S_T_R)
- More homogeneous properties (planned developments)
- Includes median property values (total, land, improvement)
- Better for appeal arguments (more similar properties)

**When to Use:**

- Subdivision analysis: New developments, planned communities
- Neighborhood analysis: Rural areas, older neighborhoods, broader comparisons

### 3. Property Percentile Ranking

**Function:** `get_property_percentile_ranking(parcelid)`

**Purpose:** Rank a property's assessment ratio across multiple dimensions.

**Ranking Dimensions:**

1. **Neighborhood Ranking** (by S_T_R)
   - Percentile: Where does this property rank? (0-100)
   - Rank: Actual position (1 = lowest ratio)
   - Example: 85th percentile = assessed higher than 85% of neighbors

2. **Subdivision Ranking** (if applicable)
   - Same metrics as neighborhood
   - More precise due to similar properties

3. **Property Type Ranking** (county-wide)
   - Compare to all properties of same type (RV, RI, etc.)
   - Useful for understanding broader assessment patterns

**Fairness Categories:**

Based on deviation from neighborhood median:

| Category | Ratio Difference | Interpretation |
|----------|------------------|----------------|
| `SIGNIFICANTLY_OVER_ASSESSED` | >+10% | Strong appeal candidate |
| `MODERATELY_OVER_ASSESSED` | +5% to +10% | Moderate appeal candidate |
| `FAIR` | -5% to +5% | Assessment appears reasonable |
| `UNDER_ASSESSED` | <-5% | Paying less than neighbors |

**Savings Potential Indicators:**

| Indicator | Ratio Difference | Action |
|-----------|------------------|--------|
| `HIGH_POTENTIAL` | >+10% | Prioritize for appeal |
| `MODERATE_POTENTIAL` | +5% to +10% | Consider appeal |
| `LOW_POTENTIAL` | +2% to +5% | Marginal case |
| `MINIMAL_POTENTIAL` | <+2% | No action recommended |

### 4. Assessment Fairness Summary View

**View:** `v_assessment_fairness_summary`

**Purpose:** Pre-calculated fairness analysis for all properties in the database.

**Use Cases:**
- Bulk property dashboard
- Identifying high-priority appeals
- County-wide assessment equity analysis
- Portfolio management

**Calculations:**

```sql
-- Assessment ratio
(assess_val / total_val) * 100

-- Neighborhood comparison
property_ratio - neighborhood_median_ratio

-- Potential assessment reduction (if over-assessed)
IF property_ratio > (median_ratio + 5%) THEN
    assess_val - (total_val * median_ratio / 100)
ELSE
    0
```

**Appeal Priority Logic:**

```sql
CASE
    WHEN ratio_diff > 10% THEN 'HIGH_PRIORITY'      -- >10% over median
    WHEN ratio_diff > 5%  THEN 'MEDIUM_PRIORITY'    -- 5-10% over median
    WHEN ratio_diff > 2%  THEN 'LOW_PRIORITY'       -- 2-5% over median
    ELSE 'NO_ACTION'                                 -- Within 2% of median
END
```

### 5. Top Over-Assessed Properties View

**View:** `v_top_over_assessed_properties`

**Purpose:** Pre-filtered list of best appeal candidates.

**Filters:**
- Appeal priority = HIGH or MEDIUM
- Total value > $50,000 (focus on meaningful savings)

**Additional Calculations:**
- Estimated annual tax savings (assuming 2% effective tax rate)
- Ranked by priority, then potential reduction

**Example Output:**

| Parcel ID | Ratio | Median | Diff | Priority | Potential Reduction | Est. Annual Savings |
|-----------|-------|--------|------|----------|---------------------|---------------------|
| 16-26005-000 | 25.0% | 18.0% | +7.0% | MEDIUM | $5,600 | $112 |
| 02-13045-000 | 28.5% | 18.0% | +10.5% | HIGH | $62,000 | $1,240 |

---

## Performance Optimization

### Index Strategy

**1. Spatial Index (GIST)**
```sql
CREATE INDEX idx_parcels_geometry ON parcels USING GIST(geometry);
```
- **Critical** for ST_DWithin performance
- GIST = Generalized Search Tree (for geometric data)
- Enables fast bounding box searches
- Expected performance: O(log n) vs O(n) sequential scan

**2. Partial Indexes**
```sql
CREATE INDEX idx_parcels_subdivname ON parcels(subdivname)
    WHERE subdivname IS NOT NULL;
```
- Only indexes rows with non-null values
- Smaller index size = faster lookups
- Reduces index maintenance overhead

**3. Expression Indexes**
```sql
CREATE INDEX idx_parcels_str_ratio
    ON parcels(s_t_r, ((assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC)))
    WHERE total_val > 0 AND assess_val > 0;
```
- Pre-calculates assessment ratio
- Avoids runtime computation for sorting/filtering
- Especially valuable for percentile calculations

**4. Composite Indexes**
```sql
CREATE INDEX idx_parcels_type_val_acre ON parcels(type_, total_val, acre_area)
    WHERE type_ IS NOT NULL AND total_val > 0 AND acre_area > 0;
```
- Covers multiple filter conditions in one index
- PostgreSQL can use for queries filtering on any/all of these columns
- Reduces index lookup overhead

### Query Optimization Techniques

**1. CTE (Common Table Expressions)**
- Used for readability and maintainability
- PostgreSQL 12+ optimizes CTEs aggressively
- Materialization only when beneficial

**2. Spatial Query Optimization**
```sql
-- Efficient (uses index)
WHERE ST_DWithin(geom1::geography, geom2::geography, 804.67)

-- Inefficient (sequential scan)
WHERE ST_Distance(geom1::geography, geom2::geography) < 804.67
```
- ST_DWithin leverages spatial index
- ST_Distance calculates exact distance for every row

**3. Filter Pushdown**
- Apply most selective filters first
- Move filters inside CTEs when possible
- Let PostgreSQL query planner optimize

**4. Limit Early**
- Use LIMIT in subqueries when possible
- Reduces sorting/aggregation overhead
- Especially important for TOP N queries

### Performance Targets

Based on 173,743 records:

| Query | Target Time | Expected Rows Scanned |
|-------|-------------|----------------------|
| `find_comparable_properties` | <300ms | ~500-5,000 |
| `get_neighborhood_median_ratio` | <150ms | ~200-2,000 |
| `get_subdivision_median_ratio` | <100ms | ~50-500 |
| `get_property_percentile_ranking` | <300ms | ~1,000-10,000 |
| `v_assessment_fairness_summary` (full) | 2-5s | 173,743 (cache as materialized view) |

### Materialized Views

For frequently accessed summary data:

```sql
CREATE MATERIALIZED VIEW mv_assessment_fairness_summary AS
SELECT * FROM v_assessment_fairness_summary;

-- Create indexes on materialized view
CREATE INDEX idx_mv_fairness_appeal_priority
    ON mv_assessment_fairness_summary(appeal_priority);

CREATE INDEX idx_mv_fairness_subdivision
    ON mv_assessment_fairness_summary(subdivision);

-- Refresh periodically (e.g., nightly)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_assessment_fairness_summary;
```

Benefits:
- One-time computation cost
- Fast subsequent queries
- Can be refreshed on schedule (daily/weekly)
- Use CONCURRENTLY to avoid locking

---

## Usage Examples

### Example 1: Find Comparables and Calculate Fairness Score

```sql
-- Step 1: Find comparable properties
WITH comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
),

-- Step 2: Get target property details
target AS (
    SELECT
        parcelid,
        total_val,
        assess_val,
        CASE WHEN total_val > 0
            THEN ROUND((assess_val::NUMERIC / total_val::NUMERIC) * 100, 2)
            ELSE 0
        END AS assessment_ratio
    FROM parcels
    WHERE parcelid = '16-26005-000'
),

-- Step 3: Calculate statistics
comp_stats AS (
    SELECT
        AVG(assessment_ratio) AS avg_comp_ratio,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assessment_ratio) AS median_comp_ratio,
        STDDEV(assessment_ratio) AS stddev_comp_ratio,
        COUNT(*) AS comp_count,
        AVG(similarity_score) AS avg_similarity
    FROM comparables
)

-- Step 4: Compare and score
SELECT
    t.parcelid,
    t.total_val AS target_value,
    t.assessment_ratio AS target_ratio,
    cs.median_comp_ratio,
    cs.avg_comp_ratio,
    cs.stddev_comp_ratio,
    cs.comp_count,
    cs.avg_similarity,

    -- Fairness score (0-100, where 100 = perfectly fair)
    GREATEST(0, 100 - ABS(t.assessment_ratio - cs.median_comp_ratio) * 5) AS fairness_score,

    -- Assessment
    CASE
        WHEN t.assessment_ratio > cs.median_comp_ratio + 10 THEN 'SIGNIFICANTLY_OVER_ASSESSED'
        WHEN t.assessment_ratio > cs.median_comp_ratio + 5 THEN 'MODERATELY_OVER_ASSESSED'
        WHEN t.assessment_ratio < cs.median_comp_ratio - 5 THEN 'UNDER_ASSESSED'
        ELSE 'FAIR'
    END AS fairness_category,

    -- Potential savings
    CASE
        WHEN t.assessment_ratio > cs.median_comp_ratio + 5 THEN
            ROUND(t.assess_val - (t.total_val * cs.median_comp_ratio / 100), 0)
        ELSE 0
    END AS potential_assessment_reduction

FROM target t
CROSS JOIN comp_stats cs;
```

### Example 2: Generate Appeal Letter Data

```sql
-- Gather all data needed for an appeal letter
WITH target AS (
    SELECT
        p.parcelid,
        p.ow_name,
        p.ph_add,
        p.total_val,
        p.assess_val,
        p.land_val,
        p.imp_val,
        p.acre_area,
        p.type_,
        p.subdivname,
        CASE WHEN p.total_val > 0
            THEN ROUND((p.assess_val::NUMERIC / p.total_val::NUMERIC) * 100, 2)
            ELSE 0
        END AS assessment_ratio
    FROM parcels p
    WHERE p.parcelid = '16-26005-000'
),

comparables AS (
    SELECT * FROM find_comparable_properties('16-26005-000')
    WHERE similarity_score >= 70  -- Only high-quality comparables
    LIMIT 10  -- Top 10 for letter
),

neighborhood AS (
    SELECT * FROM get_neighborhood_median_ratio('16-26005-000')
),

subdivision AS (
    SELECT * FROM get_subdivision_median_ratio('16-26005-000')
),

ranking AS (
    SELECT * FROM get_property_percentile_ranking('16-26005-000')
)

SELECT
    -- Property details
    t.parcelid,
    t.ow_name AS owner_name,
    t.ph_add AS property_address,
    t.subdivname,

    -- Current assessment
    t.total_val AS current_market_value,
    t.assess_val AS current_assessed_value,
    t.assessment_ratio AS current_ratio,

    -- Comparable properties (JSON array for letter)
    json_agg(json_build_object(
        'parcel_id', c.comparable_parcelid,
        'address', c.property_address,
        'total_value', c.total_value,
        'assessed_value', c.assess_value,
        'assessment_ratio', c.assessment_ratio,
        'similarity_score', c.similarity_score,
        'distance_miles', c.distance_miles
    ) ORDER BY c.similarity_score DESC) AS comparable_properties,

    -- Statistical support
    n.median_assessment_ratio AS neighborhood_median_ratio,
    s.median_assessment_ratio AS subdivision_median_ratio,
    r.neighborhood_percentile,
    r.fairness_category,

    -- Requested assessment
    ROUND(t.total_val * n.median_assessment_ratio / 100, 0) AS recommended_assessed_value,
    ROUND(t.assess_val - (t.total_val * n.median_assessment_ratio / 100), 0) AS requested_reduction,

    -- Supporting statistics
    n.property_count AS neighborhood_property_count,
    s.property_count AS subdivision_property_count

FROM target t
CROSS JOIN comparables c
CROSS JOIN neighborhood n
LEFT JOIN subdivision s ON TRUE
CROSS JOIN ranking r
GROUP BY t.parcelid, t.ow_name, t.ph_add, t.subdivname, t.total_val, t.assess_val,
         t.assessment_ratio, n.median_assessment_ratio, s.median_assessment_ratio,
         r.neighborhood_percentile, r.fairness_category, n.property_count, s.property_count;
```

### Example 3: Bulk Analysis for Portfolio

```sql
-- Analyze multiple properties (e.g., landlord's portfolio)
WITH portfolio AS (
    SELECT parcelid FROM unnest(ARRAY[
        '16-26005-000',
        '02-13045-000',
        '18-11331-002'
    ]) AS parcelid
),

rankings AS (
    SELECT
        p.parcelid,
        r.*
    FROM portfolio p
    CROSS JOIN LATERAL get_property_percentile_ranking(p.parcelid) r
)

SELECT
    parcelid,
    owner_name,
    property_address,
    total_value,
    assessment_ratio,
    neighborhood_percentile,
    subdivision_percentile,
    fairness_category,
    potential_savings_indicator,

    -- Portfolio totals
    SUM(total_value) OVER () AS portfolio_total_value,
    SUM(assess_value) OVER () AS portfolio_assessed_value,

    -- Weighted average ratio
    SUM(assess_value) OVER () / NULLIF(SUM(total_value) OVER (), 0) * 100 AS portfolio_avg_ratio,

    -- Potential savings
    CASE
        WHEN is_over_assessed THEN
            assess_value - (total_value * neighborhood_median_ratio / 100)
        ELSE 0
    END AS potential_reduction_per_property

FROM rankings
ORDER BY potential_reduction_per_property DESC;
```

### Example 4: County-Wide Assessment Equity Analysis

```sql
-- Analyze assessment equity across entire county
WITH assessment_stats AS (
    SELECT
        type_ AS property_type,
        COUNT(*) AS property_count,

        -- Value statistics
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_val) AS median_value,
        AVG(total_val) AS avg_value,

        -- Ratio statistics
        AVG(CASE WHEN total_val > 0
            THEN (assess_val::NUMERIC / total_val::NUMERIC) * 100
            ELSE NULL
        END) AS avg_ratio,

        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
            CASE WHEN total_val > 0
                THEN (assess_val::NUMERIC / total_val::NUMERIC) * 100
                ELSE NULL
            END
        ) AS median_ratio,

        STDDEV(CASE WHEN total_val > 0
            THEN (assess_val::NUMERIC / total_val::NUMERIC) * 100
            ELSE NULL
        END) AS stddev_ratio,

        -- Coefficient of dispersion (measure of uniformity)
        (AVG(ABS(
            (assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100) -
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
                assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100
            )
        )) / NULLIF(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY
            assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC * 100
        ), 0)) * 100 AS coefficient_of_dispersion

    FROM parcels
    WHERE total_val > 0 AND assess_val > 0
    GROUP BY type_
)

SELECT
    property_type,
    property_count,
    ROUND(median_value, 0) AS median_value,
    ROUND(avg_value, 0) AS avg_value,
    ROUND(avg_ratio, 2) AS avg_assessment_ratio,
    ROUND(median_ratio, 2) AS median_assessment_ratio,
    ROUND(stddev_ratio, 2) AS stddev_assessment_ratio,
    ROUND(coefficient_of_dispersion, 2) AS cod,

    -- IAAO standards: COD should be <15% for residential, <20% for other
    CASE
        WHEN property_type IN ('RI', 'RV') AND coefficient_of_dispersion < 15 THEN 'EXCELLENT'
        WHEN property_type IN ('RI', 'RV') AND coefficient_of_dispersion < 20 THEN 'ACCEPTABLE'
        WHEN property_type NOT IN ('RI', 'RV') AND coefficient_of_dispersion < 20 THEN 'GOOD'
        ELSE 'NEEDS_IMPROVEMENT'
    END AS equity_rating

FROM assessment_stats
ORDER BY property_count DESC;
```

---

## Query Execution Plans

### Analyzing Query Performance

Use `EXPLAIN ANALYZE` to understand query execution:

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM find_comparable_properties('16-26005-000');
```

### Expected Plan for Comparable Matching

```
Function Scan on find_comparable_properties  (cost=0.00..10.00 rows=1000 width=...)
  ->  Limit  (cost=500.00..550.00 rows=20 width=...)
        ->  Sort  (cost=500.00..520.00 rows=1000 width=...)
              Sort Key: (calculated similarity_score) DESC, distance_miles
              ->  Append  (cost=50.00..450.00 rows=1000 width=...)
                    ->  CTE Scan on subdivision_matches  (cost=50.00..100.00 rows=50 width=...)
                          ->  Index Scan using idx_parcels_subdivname on parcels
                                Index Cond: (subdivname = $1)
                                Filter: (type_ = $2 AND total_val BETWEEN ... AND ...)
                    ->  CTE Scan on proximity_matches  (cost=200.00..350.00 rows=200 width=...)
                          ->  Index Scan using idx_parcels_geometry on parcels
                                Index Cond: (ST_DWithin(...))
                                Filter: (type_ = $2 AND total_val BETWEEN ... AND ...)
```

**Key Points:**
1. **Index Scans**: Both subdivision and spatial indexes are used (good!)
2. **Append**: Combines subdivision and proximity matches efficiently
3. **Sort**: Final sorting on similarity score (expected, only 20 rows due to LIMIT)
4. **Cost Estimates**: Should be <1000 for good performance

### Expected Plan for Percentile Ranking

```
Function Scan on get_property_percentile_ranking  (cost=0.00..10.00 rows=1 width=...)
  ->  Nested Loop  (cost=300.00..450.00 rows=1 width=...)
        ->  Aggregate  (cost=100.00..120.00 rows=1 width=...)
              ->  Index Scan using idx_parcels_str_ratio on parcels
                    Index Cond: (s_t_r = $1)
                    Filter: (total_val > 0 AND assess_val > 0)
        ->  Aggregate  (cost=80.00..100.00 rows=1 width=...)
              ->  Index Scan using idx_parcels_subdiv_ratio on parcels
                    Index Cond: (subdivname = $2)
        ->  Aggregate  (cost=100.00..120.00 rows=1 width=...)
              ->  Index Scan using idx_parcels_type_ratio on parcels
                    Index Cond: (type_ = $3)
```

**Key Points:**
1. **Expression Indexes**: Pre-calculated ratios speed up percentile calculations
2. **Aggregates**: PERCENTILE_CONT requires full scan of matching rows (expected)
3. **Parallel Execution**: PostgreSQL may parallelize percentile calculations

### Performance Red Flags

Watch for these in EXPLAIN output:

1. **Seq Scan on parcels** (without justification)
   - Fix: Add missing index
   - Exception: OK for small result sets or full table aggregates

2. **Index Scan ... Filter: (many rows removed)**
   - Fix: Index may not be selective enough
   - Solution: Add composite index or partial index

3. **Sort ... (external merge)**
   - Fix: Increase work_mem
   - Or: Reduce result set before sorting

4. **Nested Loop ... (many iterations)**
   - Fix: May need better join method
   - Solution: Analyze statistics, consider Hash Join

### PostgreSQL Configuration

For optimal performance with 173K records:

```sql
-- Increase work memory for sorting/aggregation
SET work_mem = '64MB';  -- Per operation

-- Increase shared buffers for caching
-- In postgresql.conf:
shared_buffers = 2GB  -- 25% of total RAM

-- Enable parallel query execution
max_parallel_workers_per_gather = 4

-- Update statistics regularly
ANALYZE parcels;

-- Vacuum to reclaim space and update statistics
VACUUM ANALYZE parcels;
```

---

## Troubleshooting

### Common Issues

**1. Slow Comparable Matching Query**

Symptoms:
- Query takes >1 second
- EXPLAIN shows Seq Scan on parcels

Solutions:
```sql
-- Verify spatial index exists
SELECT indexname FROM pg_indexes
WHERE tablename = 'parcels' AND indexname LIKE '%geometry%';

-- If missing, create it
CREATE INDEX idx_parcels_geometry ON parcels USING GIST(geometry);

-- Update statistics
ANALYZE parcels;
```

**2. No Comparable Properties Found**

Possible causes:
- Target property has NULL values (type_, total_val, acre_area)
- Target property is unusual (outlier)
- Filters too restrictive

Debug query:
```sql
-- Check target property
SELECT parcelid, type_, total_val, acre_area, subdivname
FROM parcels
WHERE parcelid = '16-26005-000';

-- Relax filters to see available properties
SELECT COUNT(*)
FROM parcels
WHERE type_ = 'RV'
  AND total_val > 0
  AND acre_area > 0;
```

**3. Percentile Calculations Timeout**

Symptoms:
- Query takes >5 seconds
- High CPU usage

Solutions:
```sql
-- Create expression indexes
CREATE INDEX idx_parcels_str_ratio
    ON parcels(s_t_r, ((assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC)))
    WHERE total_val > 0 AND assess_val > 0;

-- Increase work_mem
SET work_mem = '128MB';

-- Use materialized view for batch processing
CREATE MATERIALIZED VIEW mv_property_rankings AS
SELECT p.parcelid, r.*
FROM parcels p
CROSS JOIN LATERAL get_property_percentile_ranking(p.parcelid) r
WHERE p.total_val > 50000;  -- Focus on meaningful properties
```

---

## Best Practices

### 1. Data Quality

- **Validate inputs**: Check for NULL values, zero values, invalid geometries
- **Handle edge cases**: Properties with unusual characteristics may need manual review
- **Update regularly**: Keep parcel data current (monthly or quarterly)

### 2. Query Optimization

- **Use EXPLAIN**: Always analyze query plans before deploying
- **Index strategically**: Balance query performance vs. write overhead
- **Cache results**: Use materialized views for frequently accessed aggregations
- **Limit result sets**: Use LIMIT and focused WHERE clauses

### 3. Fairness Analysis

- **Use multiple metrics**: Combine neighborhood, subdivision, and type-based comparisons
- **Consider sample size**: Require minimum of 5 comparables for statistical validity
- **Interpret conservatively**: ±5% ratio difference is reasonable margin of error
- **Document methodology**: Save comparable lists and calculations for appeals

### 4. Production Deployment

```sql
-- Create all indexes before first use
\i create_indexes.sql

-- Analyze statistics
ANALYZE parcels;

-- Test with sample parcels
SELECT * FROM find_comparable_properties('16-26005-000');
SELECT * FROM get_property_percentile_ranking('16-26005-000');

-- Create materialized views for dashboards
CREATE MATERIALIZED VIEW mv_assessment_fairness_summary AS
SELECT * FROM v_assessment_fairness_summary;

-- Schedule regular refreshes (via cron or pg_cron)
-- Daily at 2 AM:
SELECT cron.schedule('refresh-fairness-summary', '0 2 * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_assessment_fairness_summary$$);
```

---

## Appendix

### Glossary

**Assessment Ratio**: Assessed value divided by total market value, expressed as percentage. Arkansas typically uses 20% for residential.

**Coefficient of Dispersion (COD)**: Measure of assessment uniformity. Lower is better. IAAO standards: <15% for residential.

**GIST Index**: Generalized Search Tree index type for spatial and other non-standard data types.

**Interquartile Range (IQR)**: Difference between 75th and 25th percentiles. Measures spread of middle 50% of data.

**Percentile**: Position in a distribution. 75th percentile means 75% of values are lower.

**PostGIS**: PostgreSQL extension for geographic objects and spatial queries.

**S_T_R**: Section-Township-Range, a land survey system used in the US. Acts as neighborhood identifier.

**Subdivision**: Planned development with platted lots. More homogeneous than neighborhoods.

### References

- **International Association of Assessing Officers (IAAO)**: [www.iaao.org](https://www.iaao.org)
- **PostGIS Documentation**: [postgis.net/documentation](https://postgis.net/documentation/)
- **PostgreSQL Performance Tuning**: [www.postgresql.org/docs/current/performance-tips.html](https://www.postgresql.org/docs/current/performance-tips.html)
- **Arkansas Assessment Standards**: Arkansas Assessment Coordination Department

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial release with comparable matching and analytics |

---

**Document maintained by**: Taxdown MVP Development Team
**Last updated**: 2025-12-07
**Contact**: For questions or improvements, please submit an issue or pull request.
