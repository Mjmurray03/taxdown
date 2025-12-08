# Column Mapping Reference

## Overview

This document provides a mapping between the original shapefile column names and the standardized database column names used in the Taxdown MVP schema.

**Created:** 2025-12-07
**Last Updated:** 2025-12-07
**Schema Version:** 001_initial_schema.sql

---

## Naming Conventions

### Table Name
| Source File | Database Table |
|-------------|----------------|
| Parcels.shp | `properties` |

### Column Naming Rules

1. **Monetary values**: All monetary columns use the `_cents` suffix to store values in cents (integer) to avoid floating-point precision issues.
2. **Identifiers**: Column names are converted to snake_case (e.g., `PARCELID` -> `parcel_id`).
3. **Reserved words**: Columns that conflict with SQL reserved words have an underscore suffix (e.g., `TYPE` -> `type_`).

---

## Properties Table Column Mapping

### Identification Columns

| Shapefile Column | Database Column | Data Type | Notes |
|------------------|-----------------|-----------|-------|
| PARCELID | `parcel_id` | VARCHAR(50) | 598 records have NULL values; synthetic IDs generated for these |
| - | `synthetic_parcel_id` | VARCHAR(50) | Auto-generated for NULL PARCELID records using format `SYNTH-{hash}` |
| - | `is_synthetic_id` | BOOLEAN | Flag indicating if parcel_id is generated |

### Monetary Value Columns

| Shapefile Column | Database Column | Data Type | Conversion Notes |
|------------------|-----------------|-----------|------------------|
| TOTAL_VAL | `total_val_cents` | BIGINT | Multiply source value by 100 (dollars to cents) |
| ASSESS_VAL | `assess_val_cents` | BIGINT | Multiply source value by 100 (dollars to cents) |
| LAND_VAL | `land_val_cents` | BIGINT | Multiply source value by 100 (dollars to cents) |
| IMP_VAL | `imp_val_cents` | BIGINT | Multiply source value by 100 (dollars to cents) |

**Example Conversion:**
```python
# During ETL import
total_val_cents = int(source_record['TOTAL_VAL'] * 100)
assess_val_cents = int(source_record['ASSESS_VAL'] * 100)
land_val_cents = int(source_record['LAND_VAL'] * 100)
imp_val_cents = int(source_record['IMP_VAL'] * 100)
```

**Example Usage in Queries:**
```sql
-- Convert back to dollars for display
SELECT
    parcel_id,
    total_val_cents / 100.0 AS total_val_dollars,
    assess_val_cents / 100.0 AS assess_val_dollars
FROM properties;
```

### Property Information Columns

| Shapefile Column | Database Column | Data Type | Notes |
|------------------|-----------------|-----------|-------|
| ACRE_AREA | `acre_area` | DOUBLE PRECISION | Acreage from shapefile |
| GIS_EST_AC | `gis_est_ac` | DOUBLE PRECISION | GIS-estimated acreage |
| OW_NAME | `ow_name` | VARCHAR(255) | Owner name |
| OW_ADD | `ow_add` | VARCHAR(500) | Owner mailing address |
| PH_ADD | `ph_add` | VARCHAR(500) | Physical property address |
| TYPE_ | `type_` | VARCHAR(50) | Property type (underscore suffix to avoid SQL reserved word) |
| S_T_R | `s_t_r` | VARCHAR(50) | Section-Township-Range legal description |
| SCHL_CODE | `schl_code` | VARCHAR(50) | School district code |
| SUBDIVNAME | `subdivname` | VARCHAR(255) | Subdivision name |

### Geometry and Shape Columns

| Shapefile Column | Database Column | Data Type | Notes |
|------------------|-----------------|-----------|-------|
| Shape_Leng | `shape_leng` | DOUBLE PRECISION | Perimeter length |
| Shape_Area | `shape_area` | DOUBLE PRECISION | Area in source CRS units |
| geometry | `geometry` | GEOMETRY(MultiPolygon, 4326) | Transformed from EPSG:3433 to EPSG:4326 |

### Enriched/Derived Columns

These columns are not in the source shapefile but are populated through spatial joins or other data enrichment:

| Database Column | Data Type | Source | Notes |
|-----------------|-----------|--------|-------|
| `city` | VARCHAR(100) | Spatial join with Cities.shp | City name |
| `zip_code` | VARCHAR(10) | Spatial join with Addresses.shp | ZIP code |
| `county` | VARCHAR(50) | Default: 'Benton' | County name |
| `state` | CHAR(2) | Default: 'AR' | State code |
| `subdivision_id` | UUID | FK to subdivisions table | Linked via spatial join |
| `building_sqft` | INTEGER | Future: Arkansas.geojson | Building square footage |
| `building_year_built` | INTEGER | Future: Arkansas.geojson | Year built |
| `building_stories` | INTEGER | Future: Arkansas.geojson | Number of stories |
| `building_class` | VARCHAR(50) | Future: Arkansas.geojson | Building classification |

---

## Subdivisions Table Column Mapping

| Shapefile Column | Database Column | Data Type | Notes |
|------------------|-----------------|-----------|-------|
| NAME | `name` | VARCHAR(255) | Subdivision name |
| CAMA_Name | `cama_name` | VARCHAR(255) | CAMA system name (includes city suffix) |
| Shape_Leng | `shape_leng` | DOUBLE PRECISION | Perimeter length |
| Shape_Area | `shape_area` | DOUBLE PRECISION | Area |
| geometry | `geometry` | GEOMETRY(MultiPolygon, 4326) | Transformed from EPSG:3433 to EPSG:4326 |

---

## Query Reference Examples

### Converting Cents to Dollars in Queries

```sql
-- Use the v_properties_full view which includes dollar conversions
SELECT
    effective_parcel_id,
    ow_name,
    assess_val_dollars,  -- Pre-computed in view
    total_val_dollars    -- Pre-computed in view
FROM v_properties_full
WHERE city = 'Bentonville';

-- Or calculate inline
SELECT
    parcel_id,
    ow_name,
    assess_val_cents / 100.0 AS assess_val,
    total_val_cents / 100.0 AS total_val
FROM properties
WHERE city = 'Bentonville';
```

### Assessment Ratio Calculation

```sql
-- Assessment ratio using _cents columns
SELECT
    parcel_id,
    CASE
        WHEN total_val_cents > 0
        THEN ROUND((assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100, 2)
        ELSE NULL
    END AS assessment_ratio_pct
FROM properties
WHERE total_val_cents > 0;
```

---

## ETL Import Guidelines

When importing data from shapefiles, follow these transformations:

```python
# Python ETL example
def transform_parcel_record(source_record):
    return {
        'parcel_id': source_record.get('PARCELID'),  # May be NULL
        'acre_area': source_record.get('ACRE_AREA'),
        'gis_est_ac': source_record.get('GIS_EST_AC'),
        'ow_name': source_record.get('OW_NAME'),
        'ow_add': source_record.get('OW_ADD'),
        'ph_add': source_record.get('PH_ADD'),
        'type_': source_record.get('TYPE_'),
        's_t_r': source_record.get('S_T_R'),
        'schl_code': source_record.get('SCHL_CODE'),
        'subdivname': source_record.get('SUBDIVNAME'),
        'shape_leng': source_record.get('Shape_Leng'),
        'shape_area': source_record.get('Shape_Area'),

        # Monetary conversions (dollars to cents)
        'total_val_cents': int(source_record.get('TOTAL_VAL', 0) * 100),
        'assess_val_cents': int(source_record.get('ASSESS_VAL', 0) * 100),
        'land_val_cents': int(source_record.get('LAND_VAL', 0) * 100),
        'imp_val_cents': int(source_record.get('IMP_VAL', 0) * 100),

        # Geometry transformation
        'geometry': transform_geometry(source_record['geometry'], from_crs=3433, to_crs=4326)
    }
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-07 | Database Team | Initial column mapping document |
