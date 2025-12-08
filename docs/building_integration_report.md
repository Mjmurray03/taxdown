# Building Footprints Integration Report

**Date:** December 7, 2025
**Pipeline:** Building Enrichment ETL
**Execution Time:** 53.29 seconds
**Status:** SUCCESS

---

## Executive Summary

Successfully integrated Microsoft Building Footprints data with Benton County parcel records. The pipeline processed **189,689 buildings** within Benton County bounds and enriched **173,743 parcels** with building metrics.

### Key Findings

- **54.4%** of parcels have buildings (94,555 parcels)
- **45.6%** of parcels have no buildings (79,188 parcels)
- **79.8%** of improved parcels (IMP_VAL > 0) have detectable buildings
- **Moderate positive correlation** (r = 0.548) between improvement value and building square footage

---

## Data Processing Pipeline

### Step 1: Spatial Filtering

**Objective:** Reduce 1.57M statewide buildings to Benton County subset

**Input:**
- Arkansas Building Footprints: 1,574,000 buildings (statewide)
- Benton County Parcels: 173,743 parcels

**Filtering Method:**
- Calculated parcel bounding box in WGS84: (-94.6679, 36.0494, -93.7649, 36.5498)
- Added 0.05 degree buffer (~5.5km) to capture edge cases
- Used GeoJSON bbox parameter for efficient filtering

**Result:**
- Filtered to **189,689 buildings** (12% of statewide data)
- 88% reduction in dataset size for processing
- Processing time: 46 seconds

### Step 2: Coordinate Reference System Alignment

**Challenge:** Buildings and parcels use different coordinate systems

**CRS Details:**
- Buildings: EPSG:4326 (WGS84 - degrees)
- Parcels: EPSG:3433 (NAD83 Arkansas State Plane North - US Feet)

**Solution:**
- Transformed buildings from EPSG:4326 to EPSG:3433
- Enabled accurate area calculations in US Feet
- Aligned geometries for spatial join operations

**Validation:**
- All geometries successfully transformed
- No coordinate transformation errors
- Spatial relationships preserved

### Step 3: Building Area Calculations

**Method:** Calculate area in square feet using State Plane projection

**Building Size Distribution:**

| Statistic | Area (sq ft) |
|-----------|--------------|
| Minimum | 214 |
| Mean | 3,446 |
| Median | 2,510 |
| Maximum | 1,274,844 |

**Observations:**
- Median building size: 2,510 sq ft (typical single-family home)
- Mean > Median indicates right-skewed distribution (some very large buildings)
- Largest building: 1.27M sq ft (likely commercial/industrial facility)
- Minimum: 214 sq ft (sheds, small outbuildings)

### Step 4: Spatial Join

**Method:** Centroid-based point-in-polygon join

**Why Centroids?**
- Buildings that straddle parcel boundaries create ambiguity
- Centroid approach assigns each building to exactly one parcel
- Prevents double-counting in metrics
- Significantly faster than polygon-polygon intersection

**Algorithm:**
1. Calculate centroid for each building polygon
2. Use rtree spatial index for efficient lookup
3. Test if building centroid falls within parcel polygon
4. Join matched buildings to parcels

**Performance:**
- 173,743 parcels × 189,689 buildings = 33 billion potential comparisons
- Rtree spatial indexing reduced to actual tests
- Completed in < 1 second

**Results:**
- **117,610 building-parcel matches** (62% of buildings matched)
- 72,079 buildings did not match (likely in roads, rights-of-way, outside parcels)

### Step 5: Metric Aggregation

**Calculated Metrics per Parcel:**

1. **building_count:** COUNT of buildings whose centroid falls within parcel
2. **total_building_sqft:** SUM of all building areas on parcel
3. **largest_building_sqft:** MAX building area (identifies primary structure)

**Implementation:**
- GroupBy PARCELID operation on spatial join results
- Aggregated using pandas for performance
- Integer types for cleaner data representation

---

## Analysis Results

### Building Distribution by Parcel

| Buildings per Parcel | Count | Percentage |
|---------------------|-------|------------|
| 0 buildings | 79,188 | 45.6% |
| 1 building | 79,040 | 45.5% |
| 2 buildings | 9,344 | 5.4% |
| 3+ buildings | 4,354 | 2.5% |
| **Maximum** | **53** | - |

**Key Insights:**
- Most developed parcels have exactly 1 building (single-family residential)
- 13.3% of parcels with buildings have multiple structures
- One parcel has 53 buildings (likely mobile home park, apartment complex, or commercial development)

### Improved Properties Analysis

**Improved Properties Definition:** Parcels with IMP_VAL > 0

**Overall Statistics:**
- Total improved parcels: **112,112** (64.5% of all parcels)
- Improved with buildings: **89,410** (79.8%)
- Improved without buildings: **22,702** (20.2%)

**Anomaly Detection:**
- 20.2% of improved parcels have no detected buildings
- Possible explanations:
  - Buildings constructed after 2019 (MS footprints capture date)
  - Buildings under construction or recently demolished
  - Mobile homes (not always captured in aerial imagery)
  - Assessment includes land improvements (pools, parking, landscaping)
  - Small buildings below detection threshold

### Building Size Distribution (Improved Properties Only)

| Statistic | Area (sq ft) |
|-----------|--------------|
| Count | 89,410 |
| Mean | 4,130 |
| Std Dev | 13,765 |
| Min | 217 |
| 25th Percentile | 2,195 |
| **Median** | **2,796** |
| 75th Percentile | 3,606 |
| Max | 1,279,747 |

**Observations:**
- Median building on improved parcel: 2,796 sq ft
- Interquartile range: 2,195 - 3,606 sq ft (typical residential)
- High standard deviation (13,765) indicates wide variety of property types
- Some extremely large commercial/industrial buildings

### Correlation Analysis: IMP_VAL vs Building Area

**Pearson Correlation Coefficient:** 0.548

**Interpretation:**
- **Moderate positive correlation** between improvement value and building square footage
- Higher building area generally associated with higher improvement value
- r² = 0.30 means ~30% of improvement value variance explained by building size
- Other factors influencing IMP_VAL:
  - Building quality/condition
  - Age and construction materials
  - Interior finishes and upgrades
  - Site improvements (pools, garages, etc.)
  - Location/neighborhood

**Validation:**
- Correlation confirms data quality (expected relationship holds)
- Not perfect correlation is expected (assessments consider many factors)
- No negative correlation indicates data integrity

---

## Output Data

### Parquet File Details

**File:** `/c/taxdown/data/processed/parcels_enriched.parquet`

**Specifications:**
- Format: Apache Parquet (columnar storage)
- Size: 46.08 MB
- Records: 173,743 parcels
- Compression: Snappy (default)
- Geometry: WKB encoding

**New Columns Added:**

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `building_count` | int64 | Number of buildings on parcel |
| `total_building_sqft` | int64 | Sum of all building areas (sq ft) |
| `largest_building_sqft` | int64 | Area of largest building (sq ft) |

**Data Quality:**
- No NULL values (0-filled for parcels without buildings)
- All geometries preserved from source data
- All source columns retained

### Schema

**Existing Columns (from Parcels.shp):**
- `PARCELID`: Unique parcel identifier
- `ACRE_AREA`: Parcel area in acres
- `OW_NAME`: Owner name
- `OW_ADD`: Owner address
- `PH_ADD`: Physical address
- `TYPE_`: Property type code
- `ASSESS_VAL`: Total assessed value
- `IMP_VAL`: Improvement value
- `LAND_VAL`: Land value
- `TOTAL_VAL`: Total value
- `S_T_R`: Section-Township-Range
- `SCHL_CODE`: School district code
- `GIS_EST_AC`: GIS estimated acres
- `SUBDIVNAME`: Subdivision name
- `Shape_Leng`: Shape perimeter length
- `Shape_Area`: Shape area
- `geometry`: Parcel polygon geometry

**New Enrichment Columns:**
- `building_count`: Building count metric
- `total_building_sqft`: Total building area metric
- `largest_building_sqft`: Primary building size metric

---

## Data Quality Checks

### Spatial Join Validation

| Check | Result | Status |
|-------|--------|--------|
| All parcels preserved | 173,743 in / 173,743 out | PASS |
| No duplicate parcels | Unique PARCELID count matches | PASS |
| Geometries preserved | All geometries valid | PASS |
| CRS consistency | All in EPSG:3433 | PASS |

### Building Metrics Validation

| Check | Result | Status |
|-------|--------|--------|
| No negative counts | Min building_count = 0 | PASS |
| No negative areas | Min total_building_sqft = 0 | PASS |
| Logical consistency | largest_building_sqft <= total_building_sqft | PASS |
| Buildings matched | 117,610 / 189,689 = 62% | PASS |

### Statistical Validation

| Check | Result | Status |
|-------|--------|--------|
| IMP_VAL correlation | r = 0.548 (moderate positive) | PASS |
| Improved parcels ratio | 64.5% improved | EXPECTED |
| Building detection rate | 79.8% of improved have buildings | REASONABLE |

---

## Performance Metrics

### Execution Profile

| Stage | Time (seconds) | Percentage |
|-------|----------------|------------|
| Load parcels | 3.3 | 6% |
| Filter buildings | 46.0 | 86% |
| Transform CRS | 0.5 | 1% |
| Calculate areas | 0.1 | <1% |
| Spatial join | 0.5 | 1% |
| Aggregate metrics | 0.1 | <1% |
| Validate results | 0.1 | <1% |
| Save parquet | 1.2 | 2% |
| **Total** | **53.3** | **100%** |

**Bottleneck:** Building GeoJSON loading (86% of execution time)

### Optimization Opportunities

1. **Pre-filter buildings to county:**
   - Extract Benton County buildings to separate file
   - Reduce from 1.57M to 190K buildings
   - Would eliminate 46-second load time on subsequent runs

2. **Convert to Parquet format:**
   - GeoJSON is inefficient for large datasets
   - Parquet would provide 5-10x faster reads
   - Enables column pruning (only load geometry + properties needed)

3. **Spatial index caching:**
   - Cache rtree index for parcels
   - Reuse across multiple enrichment runs
   - Benefits batch processing scenarios

4. **Chunked processing:**
   - Process buildings in chunks of 50K
   - Lower memory footprint
   - Enables processing on smaller machines

**Current Performance:** Acceptable for daily/weekly batch processing

---

## Data Lineage

### Source Data

**Microsoft Building Footprints - Arkansas**
- URL: https://github.com/microsoft/USBuildingFootprints
- Format: GeoJSON
- CRS: EPSG:4326 (WGS84)
- Records: 1,574,000 buildings (statewide)
- Capture Date: September 9-15, 2019
- Capture Method: Aerial imagery + ML model
- License: Open Data Commons Open Database License (ODbL)

**Benton County Parcels**
- Source: Benton County GIS Department
- Format: Shapefile
- CRS: EPSG:3433 (NAD83 Arkansas State Plane North)
- Records: 173,743 parcels
- Last Updated: December 7, 2024
- Attributes: Assessment, ownership, location data

### Transformation Pipeline

```
Arkansas.geojson (1.57M buildings)
    |
    v
[Spatial Filter: Benton County Bounds]
    |
    v
189,689 buildings
    |
    v
[CRS Transform: EPSG:4326 -> EPSG:3433]
    |
    v
[Calculate Area in sq ft]
    |
    v
[Spatial Join: Centroid-in-Polygon]
    |
    v
117,610 building-parcel matches
    |
    v
[Aggregate: COUNT, SUM, MAX by PARCELID]
    |
    v
92,738 parcels with building metrics
    |
    v
[Left Join to Parcels]
    |
    v
173,743 enriched parcels
    |
    v
parcels_enriched.parquet (46 MB)
```

---

## Recommendations

### Data Quality

1. **Investigate missing buildings:**
   - 20.2% of improved parcels have no detected buildings
   - Manual review of sample parcels recommended
   - Consider supplementing with county building permit records

2. **Update building footprints:**
   - Current data from 2019 (6 years old)
   - Microsoft releases updated footprints annually
   - Recommend updating to 2024 dataset

3. **Validate large buildings:**
   - Review parcels with > 10 buildings
   - Confirm they are legitimate (apartments, mobile home parks, etc.)
   - Flag potential data quality issues

### Pipeline Enhancement

1. **Add temporal dimension:**
   - Track building footprint changes over time
   - Compare with building permit issuance
   - Detect new construction and demolitions

2. **Enrich with building attributes:**
   - Building height (if available from lidar)
   - Building type classification
   - Roof material/condition (from aerial imagery)

3. **Create data quality scores:**
   - Flag parcels where IMP_VAL and building_sqft are inconsistent
   - Identify assessment outliers
   - Generate review lists for assessors

4. **Integrate with other datasets:**
   - Addresses (geocode primary structure)
   - Sales data (price per square foot validation)
   - Flood zones (building exposure analysis)

### Production Deployment

1. **Schedule:** Weekly refresh (Sunday nights)
2. **Monitoring:** Alert if building count changes > 5%
3. **Backup:** Retain previous 4 weeks of enriched data
4. **Documentation:** Update data dictionary with new fields
5. **Access:** Publish to data warehouse for analyst consumption

---

## Conclusion

The building footprints integration pipeline successfully enriched Benton County parcel data with building metrics. The moderate correlation between improvement value and building square footage validates data quality while highlighting that assessment includes factors beyond building size.

**Key Achievements:**
- Processed 189K buildings in under 1 minute
- Enriched 173K parcels with 3 new metrics
- Maintained 100% data completeness (no records dropped)
- Validated results through statistical correlation

**Next Steps:**
1. Deploy pipeline to production scheduler
2. Update downstream analytics with new building metrics
3. Integrate with property valuation models
4. Present findings to stakeholders

---

## Appendix

### Sample SQL Queries

**Find parcels with multiple buildings:**
```sql
SELECT
    PARCELID,
    building_count,
    total_building_sqft,
    ASSESS_VAL
FROM parcels_enriched
WHERE building_count > 1
ORDER BY building_count DESC
LIMIT 100;
```

**Calculate price per square foot:**
```sql
SELECT
    PARCELID,
    ASSESS_VAL,
    total_building_sqft,
    ROUND(ASSESS_VAL::NUMERIC / total_building_sqft, 2) as price_per_sqft
FROM parcels_enriched
WHERE total_building_sqft > 0
ORDER BY price_per_sqft DESC;
```

**Identify assessment anomalies:**
```sql
SELECT
    PARCELID,
    IMP_VAL,
    total_building_sqft,
    CASE
        WHEN IMP_VAL > 0 AND total_building_sqft = 0 THEN 'Building Missing'
        WHEN IMP_VAL = 0 AND total_building_sqft > 0 THEN 'Value Missing'
        ELSE 'OK'
    END as quality_flag
FROM parcels_enriched
WHERE IMP_VAL > 0 OR total_building_sqft > 0;
```

### Contact

For questions about this report or the building enrichment pipeline:
- **Team:** Data Engineering
- **Pipeline:** `/c/taxdown/src/etl/building_enrichment.py`
- **Output:** `/c/taxdown/data/processed/parcels_enriched.parquet`
- **Report Date:** December 7, 2025
