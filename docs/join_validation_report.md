# PARCELID Join Validation Report

**Generated:** 2025-12-07 22:52:25

**Objective:** Validate PARCELID as the common identifier across Benton County data sources

---

## Executive Summary

### Key Findings

- **Parcels Dataset:** 173,743 total records
  - Valid PARCELIDs: 173,145 (99.66%)
  - NULL PARCELIDs: 598 (0.34%)
  - Unique valid PARCELIDs: 171,169
  - Duplicate PARCELIDs: 1,976

- **Lots Dataset:** 150,764 total records
  - **NOTE:** Lots dataset does NOT contain PARCELID column
  - Spatial join coverage: 4,443 records (2.95%)
  - Parcels with Lots: 1,761 (1.02%)
  - Orphan Lots (no parent Parcel): 146,337 (97.06%)

- **Addresses Dataset:** 164,759 total records
  - **NOTE:** Addresses dataset does NOT contain PARCELID column
  - Spatial join coverage: 163,627 records (99.31%)
  - Parcels with Addresses: 120,168 (69.40%)
  - Orphan Addresses (no parent Parcel): 1,192 (0.72%)

### Critical Discovery

> **IMPORTANT:** The Lots and Addresses shapefiles do **NOT** contain a PARCELID column. These datasets must be joined to Parcels using **spatial joins** (point-in-polygon or within operations), not attribute-based joins.

This has significant implications for ETL pipeline design:
- Spatial joins are more computationally expensive than attribute joins
- Spatial join results may be non-deterministic at parcel boundaries
- Cannot use standard SQL joins; requires spatial database (PostGIS) or in-memory processing
- Join performance scales with geometry complexity, not just row count

---

## 1. Dataset Overview

### 1.1 Parcels Dataset

- **File:** `data/raw/Parcels (1)/Parcels.shp`
- **Total Records:** 173,743
- **PARCELID Column:** `PARCELID` (EXISTS)
- **Records with NULL PARCELID:** 598 (0.34%)
- **Records with non-NULL PARCELID:** 173,145 (99.66%)
- **Unique non-NULL PARCELIDs:** 171,169
- **Duplicate PARCELIDs:** 1,976
- **CRS:** EPSG:3433

**WARNING:** 1,976 duplicate PARCELID values detected! PARCELID is NOT a unique identifier.

### 1.2 Lots Dataset

- **File:** `data/raw/Lots/Lots.shp`
- **Total Records:** 150,764
- **PARCELID Column:** NOT PRESENT
- **Available Columns:** TYPE, Lot, SubName, Block, Shape_Leng, Shape_Area
- **CRS:** EPSG:3433

### 1.3 Addresses Dataset

- **File:** `data/raw/Addresses/Addresses.shp`
- **Total Records:** 164,759
- **PARCELID Column:** NOT PRESENT
- **Available Columns:** ADDR_NUM, PRE_DIR, ROAD_NAME, TYPE, SUF_DIR, FULL_ADDR, UNIT_APT, CITY, ZIP_CODE, CLASSIFICA, City_Zip
- **CRS:** EPSG:3433

---

## 2. Spatial Join Coverage Analysis

Since PARCELID is not present in Lots and Addresses datasets, spatial joins are required to establish relationships. The analysis uses **'within'** predicate to find Lots/Addresses that fall within Parcel boundaries.

### 2.1 Parcels to Lots Spatial Join

**Base:** 173,145 Parcels with non-NULL PARCELID

**Method:** Spatial join using 'within' predicate (Lots within Parcels)

**Results:**
- Total Lots: 150,764
- Lots matched to Parcels: 4,443 (2.95%)
- Lots without Parcel: 146,337 (97.06%)
- Unique PARCELIDs with Lots: 700

**Parcels Perspective:**
- Parcels with at least one Lot: 1,761 (1.02%)
- Parcels without Lots: 171,384 (98.98%)

**Coverage Assessment:** POOR

### 2.2 Parcels to Addresses Spatial Join

**Base:** 173,145 Parcels with non-NULL PARCELID

**Method:** Spatial join using 'within' predicate (Addresses within Parcels)

**Results:**
- Total Addresses: 164,759
- Addresses matched to Parcels: 163,627 (99.31%)
- Addresses without Parcel: 1,192 (0.72%)
- Unique PARCELIDs with Addresses: 118,643

**Parcels Perspective:**
- Parcels with at least one Address: 120,168 (69.40%)
- Parcels without Addresses: 52,977 (30.60%)

**Coverage Assessment:** EXCELLENT

---

## 3. Orphan Records Analysis

### 3.1 Orphan Lots

Lots records that do not fall within any valid Parcel boundary.

- **Orphan Lots count:** 146,337
- **Percentage of Lots dataset:** 97.06%

**Possible Reasons:**
1. Geometry misalignment or precision issues
2. Lots outside Parcel boundaries (edge cases)
3. Lots in areas with NULL PARCELID
4. Data synchronization timing differences

**Sample Orphan Lots:**

| Lot | SubName | Block |
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
| 38E |  |  |
|  |  |  |
| 30R | LAKE VIEW SUB REVISED-RURBAN |  |
| 48 | LAKESIDE SUB-RURBAN |  |

### 3.2 Orphan Addresses

Address records that do not fall within any valid Parcel boundary.

- **Orphan Addresses count:** 1,192
- **Percentage of Addresses dataset:** 0.72%

**Possible Reasons:**
1. Addresses on right-of-way (roads, utilities)
2. Addresses in public spaces (parks, government buildings)
3. Point location accuracy issues
4. Multi-unit buildings with multiple addresses in single parcel

**Sample Orphan Addresses:**

| FULL_ADDR | CITY | ZIP_CODE |
|---|---|---|
| 450 E MAIN ST | GENTRY | 72734 |
| 19908 WOODHAVEN DR | HINDSVILLE | 72738 |
| 23429 TWIN FALLS RD | ADAIR COUNTY | 72761 |
| 23423 TWIN FALLS RD | ADAIR COUNTY | 72761 |
| 23417 TWIN FALLS RD | ADAIR COUNTY | 72761 |
| 23411 TWIN FALLS RD | ADAIR COUNTY | 72761 |
| 20752 KEITH PEARSON DR | WASHINGTON COUNTY | 72761 |
| 8084 HAMLEY RD | BENTON COUNTY | 72756 |
| 249 S MAIN ST | DECATUR | 72722 |
| 12131 N AR 43 HWY | DELAWARE COUNTY | 72747 |

---

## 4. NULL PARCELID Investigation

### 4.1 Overview

Found **598** Parcels records with NULL PARCELID (0.34% of total).

This is a relatively small percentage but worth investigating to understand their nature.

### 4.2 Attribute Analysis

Examining other attributes to understand what these NULL PARCELID records represent:

#### OW_NAME

| Value | Count | Percentage |
|-------|-------|------------|
| (NULL) | 598 | 100.00% |

#### TYPE_

| Value | Count | Percentage |
|-------|-------|------------|
| (NULL) | 598 | 100.00% |

#### SUBDIVNAME

| Value | Count | Percentage |
|-------|-------|------------|
| (NULL) | 598 | 100.00% |

#### ASSESS_VAL

- Non-null values: 598
- NULL values: 0
- Mean: 0.00
- Median: 0.00
- Min: 0.00
- Max: 0.00

#### IMP_VAL

- Non-null values: 598
- NULL values: 0
- Mean: 0.00
- Median: 0.00
- Min: 0.00
- Max: 0.00

#### LAND_VAL

- Non-null values: 598
- NULL values: 0
- Mean: 0.00
- Median: 0.00
- Min: 0.00
- Max: 0.00

#### TOTAL_VAL

- Non-null values: 598
- NULL values: 0
- Mean: 0.00
- Median: 0.00
- Min: 0.00
- Max: 0.00

#### GIS_EST_AC

- Non-null values: 598
- NULL values: 0
- Mean: 0.39
- Median: 0.14
- Min: 0.00
- Max: 40.57

### 4.3 Possible Explanations

Based on the attribute analysis, NULL PARCELID records may represent:

1. **Right-of-Way (ROW):** Public roads, utilities, or easements
2. **Public Lands:** Parks, government property, or common areas
3. **Unplatted Land:** Parcels not yet assigned formal identifiers
4. **Pending Development:** New subdivisions awaiting final platting
5. **Water Features:** Rivers, lakes, or other water bodies
6. **Data Quality Issues:** Records pending cleanup or validation

**Recommendation:** Review a sample of NULL PARCELID records with domain experts to determine appropriate handling strategy. Consider:
- Assigning special PARCELID codes (e.g., 'ROW-001', 'PARK-001')
- Flagging for exclusion from certain analyses
- Spatial join with alternative identifier datasets

---

## 5. Data Quality Recommendations

### 5.1 PARCELID as Primary Key

**CRITICAL ISSUE:** Found 1,976 duplicate PARCELID values in Parcels dataset!

PARCELID is **NOT** a suitable primary key due to duplicates. Investigate:
- Are duplicates intentional (e.g., condos, multiple owners)?
- Should a composite key be used instead?
- Consider creating a surrogate key (auto-increment ID)

**Top Duplicate PARCELIDs:**

| PARCELID | Occurrence Count |
|----------|------------------|
| 18-99999-999 | 458 |
| 15-99999-999 | 264 |
| DG | 231 |
| 02-99999-999 | 171 |
| 01-99999-999 | 137 |

### 5.2 Join Strategy Recommendations

#### Attribute-Based Joins (Not Applicable)

Standard SQL joins on PARCELID **cannot** be used for Lots and Addresses datasets since they lack PARCELID columns.

#### Spatial Join Approach (Required)

```python
# Load datasets
parcels = gpd.read_file('Parcels.shp')
lots = gpd.read_file('Lots.shp')
addresses = gpd.read_file('Addresses.shp')

# Ensure same CRS
lots = lots.to_crs(parcels.crs)
addresses = addresses.to_crs(parcels.crs)

# Spatial joins
lots_enriched = gpd.sjoin(lots, parcels[['PARCELID', 'geometry']], 
                          how='left', predicate='within')

addresses_enriched = gpd.sjoin(addresses, parcels[['PARCELID', 'geometry']], 
                                how='left', predicate='within')
```

#### Performance Considerations

Spatial joins are computationally expensive. For large datasets:

1. **Use Spatial Indexing:** Ensure .shp files have .sbn/.sbx spatial index files
2. **Database Approach:** Load into PostGIS with spatial indexes
   ```sql
   CREATE INDEX parcels_geom_idx ON parcels USING GIST(geometry);
   CREATE INDEX lots_geom_idx ON lots USING GIST(geometry);
   ```
3. **Chunking:** Process data in batches to manage memory
4. **Caching:** Persist join results to avoid repeated spatial operations
5. **Simplification:** Consider simplifying geometries for faster joins

### 5.3 ETL Pipeline Design

#### Airflow DAG Structure

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'benton_county_spatial_etl',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False
)

# Task 1: Load and validate Parcels
load_parcels = PythonOperator(
    task_id='load_parcels',
    python_callable=load_and_validate_parcels,
    dag=dag
)

# Task 2: Spatial join Lots to Parcels
enrich_lots = PythonOperator(
    task_id='enrich_lots',
    python_callable=spatial_join_lots,
    dag=dag
)

# Task 3: Spatial join Addresses to Parcels
enrich_addresses = PythonOperator(
    task_id='enrich_addresses',
    python_callable=spatial_join_addresses,
    dag=dag
)

# Task 4: Data quality checks
quality_checks = PythonOperator(
    task_id='quality_checks',
    python_callable=run_quality_checks,
    dag=dag
)

load_parcels >> [enrich_lots, enrich_addresses] >> quality_checks
```

### 5.4 Data Quality Monitoring

Implement automated monitoring for:

**Key Metrics:**
1. NULL PARCELID percentage (alert if > 1%)
2. Lots spatial join coverage (alert if < 3%)
3. Addresses spatial join coverage (alert if < 99%)
4. Orphan record counts (alert if increasing trend)
5. Duplicate PARCELID count (alert if any)

**Sample Monitoring Query (PostGIS):**
```sql
-- Monitor NULL PARCELID rate
SELECT 
    COUNT(*) as total_parcels,
    COUNT(parcelid) as valid_parcelids,
    COUNT(*) - COUNT(parcelid) as null_parcelids,
    ROUND(100.0 * (COUNT(*) - COUNT(parcelid)) / COUNT(*), 2) as null_pct
FROM parcels;

-- Monitor spatial join coverage
SELECT 
    COUNT(l.*) as total_lots,
    COUNT(p.parcelid) as matched_lots,
    ROUND(100.0 * COUNT(p.parcelid) / COUNT(l.*), 2) as coverage_pct
FROM lots l
LEFT JOIN parcels p ON ST_Within(l.geometry, p.geometry);
```

### 5.5 Data Governance

1. **Establish Primary Source:** Confirm Parcels dataset is authoritative for PARCELID
2. **Document Join Logic:** Clearly document that Lots/Addresses require spatial joins
3. **NULL Handling Policy:** Define business rules for NULL PARCELID records
4. **Geometry Quality:** Implement topology validation (no gaps, overlaps)
5. **Data Lineage:** Document data refresh schedules and dependencies
6. **SLA Definition:** Define acceptable join coverage thresholds
7. **Change Management:** Track schema changes and geometry updates

---

## 6. Summary Statistics

| Metric | Value |
|--------|-------|
| Total Parcels | 173,743 |
| Valid PARCELIDs in Parcels | 173,145 |
| Unique PARCELIDs | 171,169 |
| NULL PARCELIDs in Parcels | 598 (0.34%) |
| Duplicate PARCELIDs | 1,976 |
| | |
| Total Lots | 150,764 |
| Lots Matched (Spatial Join) | 4,443 (2.95%) |
| Orphan Lots | 146,337 (97.06%) |
| Parcels with Lots | 1,761 (1.02%) |
| | |
| Total Addresses | 164,759 |
| Addresses Matched (Spatial Join) | 163,627 (99.31%) |
| Orphan Addresses | 1,192 (0.72%) |
| Parcels with Addresses | 120,168 (69.40%) |

---

## 7. Conclusion

### Key Takeaways

1. **PARCELID is ONLY in Parcels dataset** - Lots and Addresses require spatial joins
2. **598 NULL PARCELIDs** found in Parcels (0.34%) - manageable but needs investigation
3. **1,976 Duplicate PARCELIDs** - CRITICAL issue affecting data integrity
4. **Spatial join coverage** - Lots: 2.9%, Addresses: 99.3%
5. **Orphan records exist** - 146,337 Lots and 1,192 Addresses without Parcels

### Next Steps

1. **Investigate duplicate PARCELIDs** - Understand root cause and remediation
2. **Review NULL PARCELID records** - Classify and assign handling strategy
3. **Analyze orphan records** - Determine if data quality issue or expected
4. **Design ETL pipeline** - Implement spatial join logic with performance optimization
5. **Set up monitoring** - Track join coverage and data quality metrics
6. **Document data model** - Create clear documentation for downstream consumers

---

## Appendix: Column Details

### Parcels Columns
```
['PARCELID', 'ACRE_AREA', 'OW_NAME', 'OW_ADD', 'PH_ADD', 'TYPE_', 'ASSESS_VAL', 'IMP_VAL', 'LAND_VAL', 'TOTAL_VAL', 'S_T_R', 'SCHL_CODE', 'GIS_EST_AC', 'SUBDIVNAME', 'Shape_Leng', 'Shape_Area', 'geometry']
```

### Lots Columns
```
['TYPE', 'Lot', 'SubName', 'Block', 'Shape_Leng', 'Shape_Area', 'geometry']
```

### Addresses Columns
```
['ADDR_NUM', 'PRE_DIR', 'ROAD_NAME', 'TYPE', 'SUF_DIR', 'FULL_ADDR', 'UNIT_APT', 'CITY', 'ZIP_CODE', 'CLASSIFICA', 'City_Zip', 'geometry']
```

