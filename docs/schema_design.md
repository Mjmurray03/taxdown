# Taxdown MVP Database Schema Design

## Overview

This document describes the PostgreSQL + PostGIS database schema for the Taxdown MVP, a property tax intelligence platform focused on Northwest Arkansas (starting with Benton County).

**Database:** PostgreSQL 15+ with PostGIS extension
**Primary Data Source:** Benton County GIS Shapefiles (173,743 parcels)
**Storage Standard:** All monetary values in cents (BIGINT) to avoid float precision issues

---

## Entity Relationship Diagram (ERD)

```
+------------------+       +--------------------+       +-------------------+
|      users       |       |   user_properties  |       |    properties     |
+------------------+       +--------------------+       +-------------------+
| id (PK, UUID)    |<------| id (PK, UUID)      |------>| id (PK, UUID)     |
| email            |       | user_id (FK)       |       | parcel_id         |
| password_hash    |       | property_id (FK)   |       | synthetic_parcel_ |
| user_type        |       | ownership_type     |       | is_synthetic_id   |
| first_name       |       | ownership_pct      |       | ow_name           |
| last_name        |       | purchase_date      |       | ow_add            |
| phone            |       | purchase_price_cts |       | ph_add            |
| subscription_tier|       | is_primary_res     |       | type_             |
| created_at       |       | notes              |       | assess_val_cents  |
| updated_at       |       | tags (JSONB)       |       | imp_val_cents     |
+------------------+       | created_at         |       | land_val_cents    |
                          | updated_at         |       | total_val_cents   |
                          +--------------------+       | s_t_r             |
                                                       | schl_code         |
                                                       | subdivname        |
                                                       | city              |
                                                       | geometry (PostGIS)|
                                                       | subdivision_id(FK)|
                                                       | created_at        |
                                                       | updated_at        |
                                                       +-------------------+
                                                              |
                                                              |
                    +--------------------+                     |
                    |    subdivisions    |<--------------------+
                    +--------------------+
                    | id (PK, UUID)      |
                    | name               |
                    | cama_name          |
                    | shape_leng         |
                    | shape_area         |
                    | geometry (PostGIS) |
                    | created_at         |
                    | updated_at         |
                    +--------------------+

+-------------------+       +------------------------+
| property_history  |       | assessment_analyses    |
+-------------------+       +------------------------+
| id (PK, UUID)     |       | id (PK, UUID)          |
| property_id (FK)  |------>| property_id (FK)       |
| field_name        |       | analysis_date          |
| old_value         |       | fairness_score         |
| new_value         |       | assessment_ratio       |
| change_date       |       | neighborhood_avg_ratio |
| change_source     |       | comparable_properties  |
| created_at        |       | recommended_action     |
+-------------------+       | estimated_savings_cents|
                           | confidence_level       |
                           | ml_model_version       |
                           | created_at             |
                           | updated_at             |
                           +------------------------+
```

---

## Table Specifications

### 1. properties

**Purpose:** Core property/parcel data storage from Parcels.shp

**Source Data:**
- File: `Parcels.shp`
- Record Count: 173,743
- CRS: EPSG:3433 (stored as EPSG:4326)

**Column Mapping from Shapefile:**

| Shapefile Column | Database Column     | Data Type         | Notes                           |
|------------------|---------------------|-------------------|---------------------------------|
| PARCELID         | parcel_id           | VARCHAR(50)       | 598 NULL values                 |
| ACRE_AREA        | acre_area           | DOUBLE PRECISION  |                                 |
| OW_NAME          | ow_name             | VARCHAR(255)      | Owner name                      |
| OW_ADD           | ow_add              | VARCHAR(500)      | Owner address                   |
| PH_ADD           | ph_add              | VARCHAR(500)      | Physical address                |
| TYPE_            | type_               | VARCHAR(50)       | Property type                   |
| ASSESS_VAL       | assess_val_cents    | BIGINT            | Multiplied by 100               |
| IMP_VAL          | imp_val_cents       | BIGINT            | Multiplied by 100               |
| LAND_VAL         | land_val_cents      | BIGINT            | Multiplied by 100               |
| TOTAL_VAL        | total_val_cents     | BIGINT            | Multiplied by 100               |
| S_T_R            | s_t_r               | VARCHAR(50)       | Section-Township-Range          |
| SCHL_CODE        | schl_code           | VARCHAR(50)       | School district code            |
| GIS_EST_AC       | gis_est_ac          | DOUBLE PRECISION  | GIS estimated acreage           |
| SUBDIVNAME       | subdivname          | VARCHAR(255)      | Subdivision name                |
| Shape_Leng       | shape_leng          | DOUBLE PRECISION  | Perimeter length                |
| Shape_Area       | shape_area          | DOUBLE PRECISION  | Area in square units            |
| geometry         | geometry            | GEOMETRY          | PostGIS MultiPolygon            |

**Null Value Profile:**

| Column     | Null Count | Percentage |
|------------|------------|------------|
| PARCELID   | 598        | 0.34%      |
| OW_NAME    | 2,498      | 1.44%      |
| OW_ADD     | 2,559      | 1.47%      |
| PH_ADD     | 5,997      | 3.45%      |
| TYPE_      | 2,498      | 1.44%      |
| S_T_R      | 2,498      | 1.44%      |
| SCHL_CODE  | 2,498      | 1.44%      |
| SUBDIVNAME | 2,498      | 1.44%      |

**Indexes:**
- `idx_properties_parcel_id` - B-tree on parcel_id
- `idx_properties_ow_name` - B-tree on ow_name
- `idx_properties_ow_name_trgm` - GIN trigram for fuzzy search
- `idx_properties_subdivname` - B-tree on subdivname
- `idx_properties_assess_val` - B-tree on assess_val_cents
- `idx_properties_city` - B-tree on city
- `idx_properties_geometry` - GIST spatial index

---

### 2. NULL PARCELID Handling Strategy

**Problem:** 598 records (0.34%) in Parcels.shp have NULL PARCELID values.

**Solution: Synthetic Parcel ID Generation**

1. **Preserve Source Data:** The `parcel_id` column allows NULL to maintain data integrity with the source shapefile.

2. **Generate Synthetic IDs:** For records with NULL PARCELID:
   - Generate a synthetic ID using: `SYNTH-` + first 12 characters of MD5 hash of geometry centroid WKT
   - Store in `synthetic_parcel_id` column
   - Set `is_synthetic_id = true`

3. **Effective Parcel ID:** Use `COALESCE(parcel_id, synthetic_parcel_id)` for:
   - Unique constraint enforcement
   - Display and API responses
   - Foreign key relationships in related systems

4. **Implementation:**
   ```sql
   -- Function to generate synthetic parcel ID
   CREATE FUNCTION generate_synthetic_parcel_id(geom GEOMETRY)
   RETURNS VARCHAR(50) AS $$
       SELECT 'SYNTH-' || UPPER(SUBSTRING(MD5(ST_AsText(ST_Centroid(geom))), 1, 12));
   $$ LANGUAGE SQL IMMUTABLE;

   -- Example usage in ETL:
   INSERT INTO properties (parcel_id, synthetic_parcel_id, is_synthetic_id, ...)
   SELECT
       PARCELID,
       CASE WHEN PARCELID IS NULL
            THEN generate_synthetic_parcel_id(geometry)
            ELSE NULL END,
       PARCELID IS NULL,
       ...
   FROM staging_parcels;
   ```

5. **Data Quality Tracking:** Records with synthetic IDs are flagged with reduced `data_quality_score` (e.g., 80 instead of 100).

---

### 3. subdivisions

**Purpose:** Subdivision boundary polygons from Subdivisions.shp

**Source Data:**
- File: `Subdivisions.shp`
- Record Count: 4,041
- CRS: EPSG:3433 (stored as EPSG:4326)

**Column Mapping:**

| Shapefile Column | Database Column | Data Type         |
|------------------|-----------------|-------------------|
| NAME             | name            | VARCHAR(255)      |
| CAMA_Name        | cama_name       | VARCHAR(255)      |
| Shape_Leng       | shape_leng      | DOUBLE PRECISION  |
| Shape_Area       | shape_area      | DOUBLE PRECISION  |
| geometry         | geometry        | GEOMETRY          |

**Note:** CAMA_Name often includes city suffix (e.g., "MCNAIR SUB-SILOAM SPRINGS") which can be parsed to derive city information.

---

### 4. property_history

**Purpose:** Audit trail for tracking property value and field changes over time.

**Use Cases:**
- Track assessment value changes year-over-year
- Monitor ownership changes
- Detect data corrections or anomalies
- Support historical trend analysis

**Key Fields:**

| Column        | Type          | Description                                    |
|---------------|---------------|------------------------------------------------|
| property_id   | UUID (FK)     | Reference to properties table                  |
| field_name    | VARCHAR(100)  | Database column name that changed              |
| old_value     | TEXT          | Previous value (stringified)                   |
| new_value     | TEXT          | New value (stringified)                        |
| change_date   | DATE          | When the change was detected                   |
| change_source | VARCHAR(100)  | Source: GIS_SYNC, MANUAL, API_UPDATE, etc.     |

**Population Strategy:**
1. During ETL sync: Compare incoming values with existing records
2. For any changed fields, insert a history record before updating
3. Use triggers or application-level logic for change detection

---

### 5. assessment_analyses

**Purpose:** Store fairness analysis results, comparable property data, and recommendations.

**Key Fields:**

| Column                     | Type          | Description                                |
|----------------------------|---------------|--------------------------------------------|
| property_id                | UUID (FK)     | Property being analyzed                    |
| fairness_score             | INTEGER       | 0-100 score (see scale below)              |
| assessment_ratio           | DECIMAL(5,4)  | Property's assessed/total ratio            |
| neighborhood_avg_ratio     | DECIMAL(5,4)  | Neighborhood average ratio                 |
| comparable_properties      | JSONB         | Array of comparable property data          |
| recommended_action         | ENUM          | APPEAL, MONITOR, or NONE                   |
| estimated_savings_cents    | BIGINT        | Potential annual savings in cents          |
| confidence_level           | INTEGER       | 0-100 confidence in analysis               |

**Fairness Score Scale:**
- 0-20: Likely under-assessed (favorable for owner)
- 21-40: Fairly assessed
- 41-60: Possibly over-assessed
- 61-80: Likely over-assessed
- 81-100: Significantly over-assessed (strong appeal candidate)

**Comparable Properties JSONB Structure:**
```json
[
  {
    "property_id": "uuid",
    "parcel_id": "123-456-789",
    "address": "123 Main St",
    "similarity_score": 0.85,
    "assessed_value_cents": 15000000,
    "total_value_cents": 20000000,
    "assessment_ratio": 0.75,
    "distance_miles": 0.3,
    "acreage": 0.25,
    "type": "RESIDENTIAL"
  }
]
```

---

### 6. users

**Purpose:** User authentication and profile management.

**Key Fields:**

| Column              | Type       | Description                          |
|---------------------|------------|--------------------------------------|
| email               | VARCHAR    | Unique email, validated by regex     |
| password_hash       | VARCHAR    | bcrypt/argon2 hashed password        |
| user_type           | ENUM       | INVESTOR, AGENT, HOMEOWNER, ADMIN    |
| subscription_tier   | VARCHAR    | FREE, BASIC, PRO, ENTERPRISE         |

**Security Notes:**
- Passwords must be hashed using bcrypt or argon2
- Email validation regex in CHECK constraint
- Sensitive fields should be excluded from API responses

---

### 7. user_properties

**Purpose:** Many-to-many relationship for portfolio tracking.

**Ownership Types:**

| Type         | Description                                |
|--------------|--------------------------------------------|
| OWNER        | User is the actual property owner          |
| TRACKING     | User is monitoring the property            |
| INTERESTED   | User considering purchase (e.g., auction)  |
| FORMER_OWNER | Historical ownership record                |

**Features:**
- Support partial ownership percentages
- Track purchase date and price
- Enable custom tags and notes
- Configure per-property alert preferences

---

## Monetary Value Storage

**Standard:** All monetary values stored in cents as BIGINT.

**Rationale:**
1. Avoids floating-point precision issues
2. Maintains exact calculations for tax computations
3. Supports values up to ~$92 quadrillion (more than sufficient)

**Conversion Examples:**

| Source Value   | Database Value    | Column               |
|----------------|-------------------|----------------------|
| $150,000.00    | 15000000          | assess_val_cents     |
| $1,234.56      | 123456            | estimated_savings    |

**Application-Level Conversion:**
```python
# Python
dollars = assess_val_cents / 100

# SQL View
assess_val_cents / 100.0 AS assess_val_dollars
```

---

## PostGIS Geometry Handling

**Source CRS:** EPSG:3433 (NAD83 / Arkansas North)
**Storage CRS:** EPSG:4326 (WGS84)

**Transformation During ETL:**
```sql
ST_Transform(geometry, 4326)
```

**Spatial Indexes:**
- GIST index on all geometry columns
- Enables efficient spatial queries (contains, intersects, distance)

**Common Spatial Queries:**

```sql
-- Find properties within a subdivision
SELECT p.* FROM properties p
JOIN subdivisions s ON ST_Within(p.geometry, s.geometry)
WHERE s.name = 'BELLA VISTA';

-- Find properties within 0.5 miles of a point
SELECT * FROM properties
WHERE ST_DWithin(
    geometry::geography,
    ST_SetSRID(ST_MakePoint(-94.2, 36.5), 4326)::geography,
    804.67  -- 0.5 miles in meters
);

-- Calculate parcel centroid
SELECT ST_AsText(ST_Centroid(geometry)) FROM properties;
```

---

## Index Strategy

### Primary Indexes (Required)

| Table       | Column(s)            | Type    | Purpose                        |
|-------------|----------------------|---------|--------------------------------|
| properties  | parcel_id            | B-tree  | Lookup by parcel ID            |
| properties  | ow_name              | B-tree  | Owner name search              |
| properties  | subdivname           | B-tree  | Subdivision filtering          |
| properties  | assess_val_cents     | B-tree  | Value range queries            |
| properties  | city                 | B-tree  | City-based filtering           |
| properties  | geometry             | GIST    | Spatial queries                |

### Secondary Indexes (Performance)

| Table              | Column(s)          | Type    | Purpose                      |
|--------------------|--------------------|---------|-----------------------------|
| properties         | ow_name            | GIN     | Fuzzy text search (trigram) |
| property_history   | property_id        | B-tree  | History lookup              |
| property_history   | change_date        | B-tree  | Date range queries          |
| assessment_analyses| property_id        | B-tree  | Analysis lookup             |
| assessment_analyses| fairness_score     | B-tree  | Score filtering             |
| user_properties    | user_id            | B-tree  | Portfolio lookup            |

---

## Data Quality Management

**Quality Score (0-100):**
- 100: Complete, validated record
- 80-99: Minor issues (e.g., synthetic parcel ID)
- 60-79: Moderate issues (e.g., missing address)
- Below 60: Significant data quality concerns

**Quality Factors:**
1. NULL PARCELID: -20 points
2. Missing owner name: -10 points
3. Missing physical address: -5 points
4. Zero valuation: -15 points
5. Invalid geometry: -25 points

---

## Migration Execution

**Prerequisites:**
1. PostgreSQL 15+
2. PostGIS extension available
3. Database created: `CREATE DATABASE taxdown;`

**Execution:**
```bash
psql -h localhost -U postgres -d taxdown -f migrations/001_initial_schema.sql
```

**Verification:**
```sql
-- Check tables created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- Check PostGIS enabled
SELECT PostGIS_Version();

-- Verify migration recorded
SELECT * FROM schema_migrations;
```

---

## Future Considerations

1. **Partitioning:** Consider range partitioning on `created_at` for property_history if table grows large.

2. **Read Replicas:** For heavy analytical queries, consider read replicas.

3. **Full-Text Search:** May need dedicated search index (Elasticsearch) for complex property searches.

4. **Archival:** Implement data archival strategy for old assessment analyses.

5. **Audit Logging:** Consider adding comprehensive audit logging table for compliance.
