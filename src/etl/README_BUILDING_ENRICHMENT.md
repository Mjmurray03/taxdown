# Building Footprints Enrichment Pipeline

## Overview

This ETL pipeline integrates Microsoft Building Footprints data with Benton County parcel records, enriching each parcel with building metrics calculated from spatial analysis.

## Quick Start

```bash
# Run the enrichment pipeline
python src/etl/building_enrichment.py

# Query the enriched data
python scripts/query_enriched_parcels.py
```

## Output

**File:** `data/processed/parcels_enriched.parquet`

**New Columns:**
- `building_count` - Number of buildings on parcel
- `total_building_sqft` - Sum of all building areas (square feet)
- `largest_building_sqft` - Area of largest building (square feet)

## Performance

- **Execution Time:** ~53 seconds
- **Input:** 173,743 parcels + 189,689 buildings
- **Output:** 46 MB parquet file
- **Matches:** 117,610 building-parcel relationships

## Key Statistics

- **54.4%** of parcels have buildings (94,555 parcels)
- **79.8%** of improved parcels have detected buildings
- **Average buildings per developed parcel:** 1.40
- **Correlation (IMP_VAL vs building_sqft):** 0.548

## Pipeline Architecture

```
Step 1: Load Parcels (EPSG:3433)
   └─> 173,743 parcels from Parcels.shp

Step 2: Spatial Filter Buildings
   └─> 189,689 buildings (from 1.57M statewide)
   └─> Filtered to Benton County bbox + buffer

Step 3: CRS Alignment
   └─> Transform buildings EPSG:4326 -> EPSG:3433
   └─> Enables accurate area calculations

Step 4: Calculate Areas
   └─> Area in square feet using State Plane projection

Step 5: Spatial Join
   └─> Centroid-based point-in-polygon
   └─> Uses rtree spatial indexing
   └─> 117,610 matches

Step 6: Aggregate Metrics
   └─> COUNT, SUM, MAX by PARCELID
   └─> 92,738 parcels with buildings

Step 7: Enrich & Export
   └─> Left join to preserve all parcels
   └─> Fill NaN with 0 for parcels without buildings
   └─> Export to parquet format
```

## Data Sources

### Microsoft Building Footprints
- **Source:** https://github.com/microsoft/USBuildingFootprints
- **Coverage:** 1.57M buildings (Arkansas statewide)
- **Format:** GeoJSON
- **CRS:** EPSG:4326 (WGS84)
- **Capture Date:** September 9-15, 2019
- **License:** ODbL

### Benton County Parcels
- **Source:** Benton County GIS
- **Records:** 173,743 parcels
- **Format:** Shapefile
- **CRS:** EPSG:3433 (NAD83 Arkansas State Plane North)

## Usage Examples

### Load Enriched Data

```python
import geopandas as gpd

parcels = gpd.read_parquet('data/processed/parcels_enriched.parquet')
print(parcels[['PARCELID', 'building_count', 'total_building_sqft']].head())
```

### Find Multi-Building Parcels

```python
multi = parcels[parcels['building_count'] >= 3]
print(f"Parcels with 3+ buildings: {len(multi):,}")
```

### Calculate Price per Square Foot

```python
improved = parcels[(parcels['IMP_VAL'] > 0) & (parcels['total_building_sqft'] > 0)]
improved['price_per_sqft'] = improved['IMP_VAL'] / improved['total_building_sqft']
print(f"Median price per sqft: ${improved['price_per_sqft'].median():.2f}")
```

### Identify Assessment Anomalies

```python
# Improved parcels without buildings
anomalies = parcels[(parcels['IMP_VAL'] > 0) & (parcels['building_count'] == 0)]
print(f"Improved parcels without buildings: {len(anomalies):,}")
```

## Configuration

Edit constants in `building_enrichment.py`:

```python
EPSG_WGS84 = 4326  # Buildings CRS
EPSG_AR_STATE_PLANE_NORTH = 3433  # Parcels CRS
SQ_METERS_TO_SQ_FEET = 10.764  # Conversion factor
BUFFER_DEGREES = 0.05  # Spatial filter buffer
```

## Optimization Notes

### Current Performance Bottleneck
86% of execution time is loading the 1.57M building GeoJSON file.

### Recommended Optimizations

1. **Pre-filter to county:**
   ```bash
   # One-time extraction of Benton County buildings
   ogr2ogr -f "GeoJSON" \
     -spat -94.67 36.05 -93.76 36.55 \
     benton_buildings.geojson \
     Arkansas.geojson
   ```

2. **Convert to Parquet:**
   ```python
   buildings = gpd.read_file('Arkansas.geojson')
   buildings.to_parquet('Arkansas.parquet')
   # 5-10x faster reads
   ```

3. **Cache spatial index:**
   ```python
   # Save rtree index to disk
   # Reuse across multiple runs
   ```

## Data Quality Considerations

### Buildings Without Parcels (38%)
- In roads, rights-of-way
- In water bodies
- Outside parcel boundaries
- Data quality issues

### Improved Parcels Without Buildings (20%)
- Post-2019 construction
- Mobile homes
- Below detection threshold (<200 sqft)
- Land improvements only

### Validation Metrics
- IMP_VAL vs building_sqft correlation: 0.548 (moderate positive)
- Median price per sqft: $94.11 (reasonable for Benton County)
- Building size distribution: median 2,510 sqft (typical residential)

## Maintenance

### Update Building Footprints
Microsoft releases updated building footprints annually. To update:

```bash
# Download latest Arkansas dataset
wget https://usbuildingdata.blob.core.windows.net/usbuildings-v2-0/Arkansas.geojson.zip

# Extract
unzip Arkansas.geojson.zip -d data/raw/Arkansas.geojson/

# Re-run pipeline
python src/etl/building_enrichment.py
```

### Schedule
Recommended refresh frequency: **Weekly** (Sunday nights)

### Monitoring
Alert if:
- Building count changes > 5% week-over-week
- Execution time > 2 minutes
- Correlation drops below 0.4

## Documentation

- **Technical Report:** `docs/building_integration_report.md`
- **Sample Queries:** `scripts/query_enriched_parcels.py`
- **Pipeline Code:** `src/etl/building_enrichment.py`

## Support

For issues or questions:
1. Check logs for error messages
2. Verify data file paths exist
3. Ensure geopandas and dependencies installed
4. Review data quality section of report

## License

Pipeline code: Internal use only
Building footprints: ODbL (Open Database License)
Parcel data: Benton County GIS license applies
