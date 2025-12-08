-- ============================================================================
-- DATABASE SCHEMA SETUP FOR TAXDOWN MVP
-- ============================================================================
-- PostgreSQL 14+ with PostGIS 3+
-- Purpose: Create table structure and indexes for assessment analysis
--
-- USAGE:
--   1. Create database: CREATE DATABASE taxdown;
--   2. Enable PostGIS: CREATE EXTENSION postgis;
--   3. Run this script: \i schema_setup.sql
-- ============================================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- DROP EXISTING OBJECTS (for clean reinstall)
-- ============================================================================

-- Drop views first (depend on functions)
DROP VIEW IF EXISTS v_top_over_assessed_properties CASCADE;
DROP VIEW IF EXISTS v_assessment_fairness_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_assessment_fairness_summary CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS find_comparable_properties(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_neighborhood_median_ratio(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_subdivision_median_ratio(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_property_percentile_ranking(VARCHAR) CASCADE;

-- Drop table
DROP TABLE IF EXISTS properties CASCADE;

-- ============================================================================
-- CREATE PROPERTIES TABLE
-- ============================================================================

CREATE TABLE properties (
    -- Primary identification
    parcel_id VARCHAR(50) PRIMARY KEY,

    -- Property characteristics
    type_ VARCHAR(10),              -- Property type (RV, RI, AV, EG, etc.)
    acre_area NUMERIC(10, 2),       -- Acreage
    gis_est_ac NUMERIC(10, 2),      -- GIS-estimated acreage

    -- Valuation data (CRITICAL for analysis)
    total_val_cents BIGINT,         -- Total market value in cents
    assess_val_cents BIGINT,        -- Assessed value (for tax purposes) in cents
    land_val_cents BIGINT,          -- Land value only in cents
    imp_val_cents BIGINT,           -- Improvement/building value in cents

    -- Owner information
    ow_name VARCHAR(200),           -- Owner name
    ow_add VARCHAR(200),            -- Owner mailing address
    ph_add VARCHAR(200),            -- Physical address

    -- Location/geography
    s_t_r VARCHAR(20),              -- Section-Township-Range (neighborhood identifier)
    subdivname VARCHAR(200),        -- Subdivision name
    schl_code VARCHAR(10),          -- School district code

    -- Spatial
    geometry GEOMETRY(MultiPolygon, 3433),  -- Parcel boundary (Arkansas State Plane North)
    shape_leng NUMERIC,             -- Perimeter length
    shape_area NUMERIC              -- Area in square feet
);

-- Add table comment
COMMENT ON TABLE properties IS
'Property parcel data from Arkansas GIS Office FeatureServer.
Contains 173,743 parcels for Benton County, Arkansas.
Used for property tax assessment analysis and comparable property matching.';

-- Add column comments
COMMENT ON COLUMN properties.parcel_id IS 'Unique parcel identifier (e.g., 16-26005-000)';
COMMENT ON COLUMN properties.type_ IS 'Property type code: RV=Residential Vacant, RI=Residential Improved, AV=Agricultural Vacant, etc.';
COMMENT ON COLUMN properties.total_val_cents IS 'Total market value in cents';
COMMENT ON COLUMN properties.assess_val_cents IS 'Assessed value for tax purposes (typically 20% of market value) in cents';
COMMENT ON COLUMN properties.s_t_r IS 'Section-Township-Range identifier, used as neighborhood proxy';
COMMENT ON COLUMN properties.subdivname IS 'Subdivision name for planned developments';
COMMENT ON COLUMN properties.geometry IS 'Parcel boundary polygon in EPSG:3433 (Arkansas State Plane North)';

-- ============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Spatial index (CRITICAL for ST_DWithin performance)
CREATE INDEX idx_properties_geometry ON properties USING GIST(geometry);

-- Subdivision matching (for comparable property search)
CREATE INDEX idx_properties_subdivname ON properties(subdivname)
    WHERE subdivname IS NOT NULL;

-- Property type filtering
CREATE INDEX idx_properties_type ON properties(type_)
    WHERE type_ IS NOT NULL;

-- Value-based filtering
CREATE INDEX idx_properties_total_val_cents ON properties(total_val_cents)
    WHERE total_val_cents > 0;

-- Acreage filtering
CREATE INDEX idx_properties_acre_area ON properties(acre_area)
    WHERE acre_area > 0;

-- Composite index for common filter combinations
CREATE INDEX idx_properties_type_val_acre ON properties(type_, total_val_cents, acre_area)
    WHERE type_ IS NOT NULL AND total_val_cents > 0 AND acre_area > 0;

-- Neighborhood (S_T_R) grouping for analytics
CREATE INDEX idx_properties_str ON properties(s_t_r)
    WHERE s_t_r IS NOT NULL;

-- ============================================================================
-- CREATE EXPRESSION INDEXES FOR ANALYTICS
-- ============================================================================
-- These pre-calculate assessment ratios to speed up percentile calculations

-- Assessment ratio by neighborhood
CREATE INDEX idx_properties_str_ratio
    ON properties(s_t_r, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
    WHERE total_val_cents > 0 AND assess_val_cents > 0;

-- Assessment ratio by subdivision
CREATE INDEX idx_properties_subdiv_ratio
    ON properties(subdivname, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
    WHERE subdivname IS NOT NULL AND total_val_cents > 0 AND assess_val_cents > 0;

-- Assessment ratio by property type
CREATE INDEX idx_properties_type_ratio
    ON properties(type_, ((assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)::NUMERIC)))
    WHERE type_ IS NOT NULL AND total_val_cents > 0 AND assess_val_cents > 0;

-- Composite index for fairness analysis
CREATE INDEX idx_properties_fairness_analysis
    ON properties(s_t_r, subdivname, type_, total_val_cents, assess_val_cents)
    WHERE total_val_cents > 0 AND assess_val_cents > 0;

-- ============================================================================
-- UPDATE STATISTICS
-- ============================================================================

-- Ensure PostgreSQL has accurate statistics for query planning
ANALYZE properties;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify table structure
/*
\d properties
*/

-- Verify indexes
/*
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'properties'
ORDER BY indexname;
*/

-- Check spatial reference system
/*
SELECT
    Find_SRID('public', 'properties', 'geometry') AS srid,
    ST_SRID(geometry) AS geom_srid
FROM properties
LIMIT 1;
*/

-- ============================================================================
-- SAMPLE DATA IMPORT FROM SHAPEFILE
-- ============================================================================
/*
Example using ogr2ogr (GDAL/OGR command-line tool):

ogr2ogr -f "PostgreSQL" \
    PG:"host=localhost dbname=taxdown user=postgres password=yourpassword" \
    "C:\taxdown\data\raw\Parcels (1)\Parcels.shp" \
    -nln properties \
    -nlt PROMOTE_TO_MULTI \
    -lco GEOMETRY_NAME=geometry \
    -lco FID=parcel_id \
    -t_srs EPSG:3433 \
    -overwrite

Or using PostGIS shp2pgsql:

shp2pgsql -I -s 3433 "C:\taxdown\data\raw\Parcels (1)\Parcels.shp" properties | \
    psql -h localhost -d taxdown -U postgres

After import, rename columns to match schema:
ALTER TABLE properties RENAME COLUMN "PARCELID" TO parcel_id;
ALTER TABLE properties RENAME COLUMN "ACRE_AREA" TO acre_area;
ALTER TABLE properties RENAME COLUMN "OW_NAME" TO ow_name;
ALTER TABLE properties RENAME COLUMN "OW_ADD" TO ow_add;
ALTER TABLE properties RENAME COLUMN "PH_ADD" TO ph_add;
ALTER TABLE properties RENAME COLUMN "TYPE_" TO type_;
ALTER TABLE properties RENAME COLUMN "ASSESS_VAL" TO assess_val_cents;
ALTER TABLE properties RENAME COLUMN "IMP_VAL" TO imp_val_cents;
ALTER TABLE properties RENAME COLUMN "LAND_VAL" TO land_val_cents;
ALTER TABLE properties RENAME COLUMN "TOTAL_VAL" TO total_val_cents;
ALTER TABLE properties RENAME COLUMN "S_T_R" TO s_t_r;
ALTER TABLE properties RENAME COLUMN "SCHL_CODE" TO schl_code;
ALTER TABLE properties RENAME COLUMN "GIS_EST_AC" TO gis_est_ac;
ALTER TABLE properties RENAME COLUMN "SUBDIVNAME" TO subdivname;
ALTER TABLE properties RENAME COLUMN "Shape_Leng" TO shape_leng;
ALTER TABLE properties RENAME COLUMN "Shape_Area" TO shape_area;
*/

-- ============================================================================
-- SAMPLE DATA VALIDATION
-- ============================================================================
/*
-- Check record count
SELECT COUNT(*) FROM properties;

-- Check data completeness
SELECT
    COUNT(*) AS total_records,
    COUNT(parcel_id) AS has_parcel_id,
    COUNT(type_) AS has_type,
    COUNT(total_val_cents) AS has_total_val_cents,
    COUNT(assess_val_cents) AS has_assess_val_cents,
    COUNT(geometry) AS has_geometry,
    COUNT(*) FILTER (WHERE total_val_cents > 0) AS valid_total_val_cents,
    COUNT(*) FILTER (WHERE assess_val_cents > 0) AS valid_assess_val_cents,
    COUNT(*) FILTER (WHERE subdivname IS NOT NULL) AS has_subdivision,
    COUNT(*) FILTER (WHERE s_t_r IS NOT NULL) AS has_str
FROM properties;

-- Check value ranges
SELECT
    MIN(total_val_cents) AS min_value,
    MAX(total_val_cents) AS max_value,
    AVG(total_val_cents) AS avg_value,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_val_cents) AS median_value
FROM properties
WHERE total_val_cents > 0;

-- Check property type distribution
SELECT
    type_,
    COUNT(*) AS count,
    ROUND(AVG(total_val_cents), 0) AS avg_value,
    ROUND(AVG(acre_area), 2) AS avg_acreage
FROM properties
WHERE type_ IS NOT NULL
GROUP BY type_
ORDER BY count DESC;

-- Check spatial data validity
SELECT
    COUNT(*) AS total_parcels,
    COUNT(*) FILTER (WHERE ST_IsValid(geometry)) AS valid_geometries,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geometry)) AS invalid_geometries,
    COUNT(*) FILTER (WHERE ST_GeometryType(geometry) = 'ST_MultiPolygon') AS multipolygons
FROM properties
WHERE geometry IS NOT NULL;
*/

-- ============================================================================
-- POSTGRESQL CONFIGURATION RECOMMENDATIONS
-- ============================================================================
/*
Add to postgresql.conf for optimal performance:

# Memory settings (adjust based on available RAM)
shared_buffers = 2GB                    # 25% of total RAM
effective_cache_size = 6GB              # 75% of total RAM
work_mem = 64MB                         # Per operation
maintenance_work_mem = 512MB            # For VACUUM, CREATE INDEX

# Query planning
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage

# Parallel query execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 8

# Write-ahead log
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Planner settings
default_statistics_target = 100

# PostGIS specific
postgis.gdal_enabled_drivers = 'ENABLE_ALL'
postgis.enable_outdb_rasters = true

After changing postgresql.conf:
1. Restart PostgreSQL
2. Run: VACUUM ANALYZE properties;
*/

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Schema setup complete!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Import parcel data from shapefile';
    RAISE NOTICE '2. Run: ANALYZE properties;';
    RAISE NOTICE '3. Load functions from comparable_matching.sql';
    RAISE NOTICE '4. Load functions from assessment_analytics.sql';
    RAISE NOTICE '5. Test with sample parcel IDs';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes created: %', (
        SELECT COUNT(*)
        FROM pg_indexes
        WHERE tablename = 'properties'
    );
    RAISE NOTICE '';
END $$;
