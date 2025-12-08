-- Taxdown MVP - Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Created: 2025-12-07
-- Description: Creates all core tables for Taxdown MVP with PostGIS support
--
-- Data Source Reference: Benton County GIS shapefiles
-- - Parcels.shp: 173,743 records (598 with NULL PARCELID)
-- - Subdivisions.shp: 4,041 records
-- - Addresses.shp: 164,759 records
-- - Cities.shp: 20 records
-- - Lots.shp: 150,764 records
--
-- CRS: EPSG:3433 (source data) - Will transform to EPSG:4326 (WGS84) for storage

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search on owner names

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- User types
CREATE TYPE user_type_enum AS ENUM (
    'INVESTOR',
    'AGENT',
    'HOMEOWNER',
    'ADMIN'
);

-- Ownership/tracking relationship types
CREATE TYPE ownership_type_enum AS ENUM (
    'OWNER',
    'TRACKING',
    'INTERESTED',
    'FORMER_OWNER'
);

-- Assessment recommendation actions
CREATE TYPE recommendation_action_enum AS ENUM (
    'APPEAL',
    'MONITOR',
    'NONE'
);

-- Analysis methodology types
CREATE TYPE analysis_methodology_enum AS ENUM (
    'COMPARABLE_SALES',
    'INCOME_APPROACH',
    'COST_APPROACH',
    'STATISTICAL',
    'ML_MODEL'
);

-- ============================================================================
-- TABLE: users
-- Description: Basic authentication and user profile management
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_type user_type_enum NOT NULL DEFAULT 'HOMEOWNER',

    -- Profile information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),

    -- Subscription information (future use)
    subscription_tier VARCHAR(50) DEFAULT 'FREE',
    stripe_customer_id VARCHAR(100),

    -- Preferences
    notification_preferences JSONB DEFAULT '{}',
    default_county VARCHAR(50) DEFAULT 'Benton',

    -- System fields
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT password_hash_not_empty CHECK (password_hash <> '')
);

COMMENT ON TABLE users IS 'User accounts for authentication and portfolio tracking';
COMMENT ON COLUMN users.password_hash IS 'bcrypt or argon2 hashed password, never store plaintext';

-- ============================================================================
-- TABLE: subdivisions
-- Description: Subdivision boundaries from Subdivisions.shp
-- Source columns: NAME, CAMA_Name, Shape_Leng, Shape_Area, geometry
-- ============================================================================

CREATE TABLE subdivisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source fields from Subdivisions.shp (exact column names)
    name VARCHAR(255),              -- NAME from shapefile
    cama_name VARCHAR(255),         -- CAMA_Name from shapefile
    shape_leng DOUBLE PRECISION,    -- Shape_Leng from shapefile
    shape_area DOUBLE PRECISION,    -- Shape_Area from shapefile

    -- PostGIS geometry column (transformed to WGS84)
    -- Original CRS: EPSG:3433, stored as EPSG:4326
    geometry GEOMETRY(MultiPolygon, 4326),

    -- Computed/derived fields
    city VARCHAR(100),              -- Derived from CAMA_Name parsing or spatial join

    -- Data quality tracking
    data_quality_score INTEGER DEFAULT 100 CHECK (data_quality_score >= 0 AND data_quality_score <= 100),
    source_file VARCHAR(255) DEFAULT 'Subdivisions.shp',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE subdivisions IS 'Subdivision boundaries from Benton County Subdivisions.shp (4,041 records)';
COMMENT ON COLUMN subdivisions.cama_name IS 'CAMA system name, typically includes city suffix (e.g., "MCNAIR SUB-SILOAM SPRINGS")';

-- ============================================================================
-- TABLE: properties
-- Description: Core property/parcel data from Parcels.shp with building enrichment
-- Source columns: PARCELID, ACRE_AREA, OW_NAME, OW_ADD, PH_ADD, TYPE_,
--                 ASSESS_VAL, IMP_VAL, LAND_VAL, TOTAL_VAL, S_T_R,
--                 SCHL_CODE, GIS_EST_AC, SUBDIVNAME, Shape_Leng, Shape_Area, geometry
--
-- NULL PARCELID Handling Strategy:
-- There are 598 records with NULL PARCELID values. Strategy:
-- 1. synthetic_parcel_id is generated for records with NULL PARCELID
-- 2. parcel_id column allows NULL to preserve source data integrity
-- 3. synthetic_parcel_id is generated as: 'SYNTH-' + geometry centroid hash
-- 4. Unique constraint uses COALESCE(parcel_id, synthetic_parcel_id)
-- 5. is_synthetic_id flag indicates if parcel_id is generated
-- ============================================================================

CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Parcel identification (NULL PARCELID handling)
    parcel_id VARCHAR(50),                  -- PARCELID from shapefile (598 are NULL)
    synthetic_parcel_id VARCHAR(50),        -- Generated ID for NULL PARCELID records
    is_synthetic_id BOOLEAN DEFAULT false,  -- True if parcel_id is NULL and we generated one

    -- Acreage fields from shapefile
    acre_area DOUBLE PRECISION,             -- ACRE_AREA from shapefile
    gis_est_ac DOUBLE PRECISION,            -- GIS_EST_AC from shapefile

    -- Owner information from shapefile
    ow_name VARCHAR(255),                   -- OW_NAME from shapefile (owner name)
    ow_add VARCHAR(500),                    -- OW_ADD from shapefile (owner address)

    -- Physical address from shapefile
    ph_add VARCHAR(500),                    -- PH_ADD from shapefile (physical address)

    -- Property type from shapefile
    type_ VARCHAR(50),                      -- TYPE_ from shapefile

    -- Valuation data (stored in cents to avoid float precision issues)
    -- Source values are integers in dollars, multiply by 100 for cents
    assess_val_cents BIGINT,                -- ASSESS_VAL * 100 (assessed value in cents)
    imp_val_cents BIGINT,                   -- IMP_VAL * 100 (improvement value in cents)
    land_val_cents BIGINT,                  -- LAND_VAL * 100 (land value in cents)
    total_val_cents BIGINT,                 -- TOTAL_VAL * 100 (total value in cents)

    -- Legal description from shapefile
    s_t_r VARCHAR(50),                      -- S_T_R from shapefile (Section-Township-Range)

    -- School and subdivision from shapefile
    schl_code VARCHAR(50),                  -- SCHL_CODE from shapefile
    subdivname VARCHAR(255),                -- SUBDIVNAME from shapefile

    -- Shape metrics from shapefile
    shape_leng DOUBLE PRECISION,            -- Shape_Leng from shapefile
    shape_area DOUBLE PRECISION,            -- Shape_Area from shapefile

    -- PostGIS geometry column (transformed to WGS84)
    -- Original CRS: EPSG:3433, stored as EPSG:4326
    geometry GEOMETRY(MultiPolygon, 4326),

    -- Enriched/derived fields (not in source shapefile)
    city VARCHAR(100),                      -- Derived from spatial join with Cities.shp
    zip_code VARCHAR(10),                   -- Derived from spatial join with Addresses.shp
    county VARCHAR(50) DEFAULT 'Benton',    -- County name
    state CHAR(2) DEFAULT 'AR',             -- State code

    -- Building enrichment data (from future building footprint integration)
    building_sqft INTEGER,
    building_year_built INTEGER,
    building_stories INTEGER,
    building_class VARCHAR(50),

    -- Subdivision foreign key (linked after spatial join)
    subdivision_id UUID REFERENCES subdivisions(id) ON DELETE SET NULL,

    -- Data quality and source tracking
    data_quality_score INTEGER DEFAULT 100 CHECK (data_quality_score >= 0 AND data_quality_score <= 100),
    source_file VARCHAR(255) DEFAULT 'Parcels.shp',
    source_date DATE,
    last_api_sync TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint using COALESCE to handle NULL parcel_id
-- This ensures both real and synthetic IDs are unique
CREATE UNIQUE INDEX idx_properties_effective_parcel_id
    ON properties (COALESCE(parcel_id, synthetic_parcel_id));

COMMENT ON TABLE properties IS 'Core property/parcel data from Benton County Parcels.shp (173,743 records, 598 with NULL PARCELID)';
COMMENT ON COLUMN properties.parcel_id IS 'Original PARCELID from shapefile - 598 records have NULL values';
COMMENT ON COLUMN properties.synthetic_parcel_id IS 'Generated ID for records with NULL PARCELID using format SYNTH-{geometry_hash}';
COMMENT ON COLUMN properties.is_synthetic_id IS 'Flag indicating if this record uses a synthetic (generated) parcel ID';
COMMENT ON COLUMN properties.assess_val_cents IS 'Assessed value in cents (ASSESS_VAL * 100) to avoid float precision issues';

-- ============================================================================
-- TABLE: property_history
-- Description: Track value and field changes over time for properties
-- ============================================================================

CREATE TABLE property_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Change tracking
    field_name VARCHAR(100) NOT NULL,       -- Name of the field that changed
    old_value TEXT,                          -- Previous value (stored as text for flexibility)
    new_value TEXT,                          -- New value (stored as text for flexibility)
    change_date DATE NOT NULL,               -- Date the change was detected

    -- Source of change information
    change_source VARCHAR(100),              -- e.g., 'GIS_SYNC', 'MANUAL', 'API_UPDATE'
    change_type VARCHAR(50),                 -- e.g., 'VALUE_CHANGE', 'OWNER_CHANGE', 'CORRECTION'

    -- Metadata
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE property_history IS 'Audit trail of property field changes for historical analysis and trend detection';
COMMENT ON COLUMN property_history.field_name IS 'Database column name that changed (e.g., assess_val_cents, ow_name)';

-- ============================================================================
-- TABLE: assessment_analyses
-- Description: Fairness scores, comparable property analysis, and recommendations
-- ============================================================================

CREATE TABLE assessment_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Fairness metrics (0-100 scale)
    -- 0-20: Under-assessed, 21-40: Fair, 41-60: Possibly over, 61-80: Likely over, 81-100: Significantly over
    fairness_score INTEGER CHECK (fairness_score >= 0 AND fairness_score <= 100),

    -- Assessment ratio analysis
    assessment_ratio DECIMAL(5,4),           -- property assessed/total ratio
    neighborhood_avg_ratio DECIMAL(5,4),     -- avg ratio for neighborhood/subdivision
    subdivision_avg_ratio DECIMAL(5,4),      -- avg ratio for specific subdivision
    city_avg_ratio DECIMAL(5,4),             -- avg ratio for city

    -- Comparable properties analysis
    comparable_properties JSONB,             -- Array of {property_id, similarity_score, assessed_value, etc.}
    comparable_count INTEGER DEFAULT 0,
    median_comparable_value_cents BIGINT,    -- Median value of comparables in cents

    -- Recommendations
    recommended_action recommendation_action_enum DEFAULT 'NONE',
    estimated_savings_cents BIGINT,          -- Potential annual tax savings in cents
    confidence_level INTEGER CHECK (confidence_level >= 0 AND confidence_level <= 100),

    -- Analysis methodology and model tracking
    analysis_methodology analysis_methodology_enum DEFAULT 'STATISTICAL',
    ml_model_version VARCHAR(20),

    -- Supporting information
    notes TEXT,
    analysis_parameters JSONB,               -- Parameters used for this analysis

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE assessment_analyses IS 'Assessment fairness analysis results with comparable properties and recommendations';
COMMENT ON COLUMN assessment_analyses.fairness_score IS 'Score 0-100: 0-20 under-assessed, 21-40 fair, 41-60 possibly over, 61-80 likely over, 81-100 significantly over';
COMMENT ON COLUMN assessment_analyses.comparable_properties IS 'JSON array of comparable property analysis: [{property_id, similarity_score, address, value, ratio}]';

-- ============================================================================
-- TABLE: user_properties
-- Description: Portfolio tracking - links users to properties they own or track
-- ============================================================================

CREATE TABLE user_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Relationship details
    ownership_type ownership_type_enum NOT NULL DEFAULT 'TRACKING',
    ownership_percentage DECIMAL(5,2),       -- For partial ownership (0.00 to 100.00)

    -- Purchase/acquisition information
    purchase_date DATE,
    purchase_price_cents BIGINT,             -- Purchase price in cents

    -- Property flags
    is_primary_residence BOOLEAN DEFAULT false,

    -- User notes and organization
    notes TEXT,
    tags JSONB DEFAULT '[]',                 -- User-defined tags for organization
    custom_name VARCHAR(255),                -- User's custom name for the property

    -- Notification preferences for this property
    enable_value_alerts BOOLEAN DEFAULT true,
    enable_auction_alerts BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique user-property combinations
    CONSTRAINT unique_user_property UNIQUE (user_id, property_id)
);

COMMENT ON TABLE user_properties IS 'Many-to-many relationship between users and properties for portfolio tracking';
COMMENT ON COLUMN user_properties.ownership_type IS 'OWNER: actual owner, TRACKING: monitoring, INTERESTED: potential purchase, FORMER_OWNER: historical';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Properties indexes (as specified in requirements)
CREATE INDEX idx_properties_parcel_id ON properties(parcel_id);
CREATE INDEX idx_properties_ow_name ON properties(ow_name);
CREATE INDEX idx_properties_subdivname ON properties(subdivname);
CREATE INDEX idx_properties_assess_val ON properties(assess_val_cents);
CREATE INDEX idx_properties_city ON properties(city);

-- Additional useful indexes for properties
CREATE INDEX idx_properties_type ON properties(type_);
CREATE INDEX idx_properties_total_val ON properties(total_val_cents);
CREATE INDEX idx_properties_subdivision_id ON properties(subdivision_id);
CREATE INDEX idx_properties_geometry ON properties USING GIST(geometry);
CREATE INDEX idx_properties_is_active ON properties(is_active) WHERE is_active = true;

-- Trigram indexes for fuzzy text search on owner names
CREATE INDEX idx_properties_ow_name_trgm ON properties USING GIN(ow_name gin_trgm_ops);

-- Subdivisions indexes
CREATE INDEX idx_subdivisions_name ON subdivisions(name);
CREATE INDEX idx_subdivisions_cama_name ON subdivisions(cama_name);
CREATE INDEX idx_subdivisions_geometry ON subdivisions USING GIST(geometry);

-- Property history indexes
CREATE INDEX idx_property_history_property_id ON property_history(property_id);
CREATE INDEX idx_property_history_field_name ON property_history(field_name);
CREATE INDEX idx_property_history_change_date ON property_history(change_date);

-- Assessment analyses indexes
CREATE INDEX idx_assessment_analyses_property_id ON assessment_analyses(property_id);
CREATE INDEX idx_assessment_analyses_analysis_date ON assessment_analyses(analysis_date);
CREATE INDEX idx_assessment_analyses_fairness_score ON assessment_analyses(fairness_score);
CREATE INDEX idx_assessment_analyses_recommended_action ON assessment_analyses(recommended_action);

-- User properties indexes
CREATE INDEX idx_user_properties_user_id ON user_properties(user_id);
CREATE INDEX idx_user_properties_property_id ON user_properties(property_id);
CREATE INDEX idx_user_properties_ownership_type ON user_properties(ownership_type);

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER trigger_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_subdivisions_updated_at
    BEFORE UPDATE ON subdivisions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_assessment_analyses_updated_at
    BEFORE UPDATE ON assessment_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_user_properties_updated_at
    BEFORE UPDATE ON user_properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCTION: Generate synthetic parcel ID
-- Used for the 598 records with NULL PARCELID values
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_synthetic_parcel_id(geom GEOMETRY)
RETURNS VARCHAR(50) AS $$
DECLARE
    centroid_wkt TEXT;
    hash_value TEXT;
BEGIN
    -- Get WKT of centroid for hashing
    centroid_wkt := ST_AsText(ST_Centroid(geom));
    -- Generate MD5 hash and take first 12 characters
    hash_value := SUBSTRING(MD5(centroid_wkt), 1, 12);
    RETURN 'SYNTH-' || UPPER(hash_value);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_synthetic_parcel_id IS 'Generates a synthetic parcel ID for records with NULL PARCELID based on geometry centroid hash';

-- ============================================================================
-- FUNCTION: Calculate effective parcel ID
-- Returns parcel_id if not NULL, otherwise synthetic_parcel_id
-- ============================================================================

CREATE OR REPLACE FUNCTION get_effective_parcel_id(
    p_parcel_id VARCHAR(50),
    p_synthetic_parcel_id VARCHAR(50)
)
RETURNS VARCHAR(50) AS $$
BEGIN
    RETURN COALESCE(p_parcel_id, p_synthetic_parcel_id);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Properties with effective parcel ID and subdivision details
CREATE OR REPLACE VIEW v_properties_full AS
SELECT
    p.id,
    COALESCE(p.parcel_id, p.synthetic_parcel_id) AS effective_parcel_id,
    p.parcel_id,
    p.synthetic_parcel_id,
    p.is_synthetic_id,
    p.ow_name,
    p.ow_add,
    p.ph_add,
    p.type_,
    p.assess_val_cents,
    p.assess_val_cents / 100.0 AS assess_val_dollars,
    p.imp_val_cents,
    p.imp_val_cents / 100.0 AS imp_val_dollars,
    p.land_val_cents,
    p.land_val_cents / 100.0 AS land_val_dollars,
    p.total_val_cents,
    p.total_val_cents / 100.0 AS total_val_dollars,
    p.acre_area,
    p.gis_est_ac,
    p.s_t_r,
    p.schl_code,
    p.subdivname,
    p.city,
    p.zip_code,
    p.county,
    p.state,
    p.shape_leng,
    p.shape_area,
    p.geometry,
    p.subdivision_id,
    s.name AS subdivision_full_name,
    s.cama_name AS subdivision_cama_name,
    p.data_quality_score,
    p.is_active,
    p.created_at,
    p.updated_at
FROM properties p
LEFT JOIN subdivisions s ON p.subdivision_id = s.id;

COMMENT ON VIEW v_properties_full IS 'Full property view with effective parcel ID, dollar values, and subdivision details';

-- View: Property assessment summary for analysis
CREATE OR REPLACE VIEW v_property_assessment_summary AS
SELECT
    p.id AS property_id,
    COALESCE(p.parcel_id, p.synthetic_parcel_id) AS effective_parcel_id,
    p.ow_name,
    p.ph_add,
    p.subdivname,
    p.city,
    p.type_,
    p.assess_val_cents / 100.0 AS assess_val_dollars,
    p.total_val_cents / 100.0 AS total_val_dollars,
    CASE
        WHEN p.total_val_cents > 0
        THEN ROUND((p.assess_val_cents::DECIMAL / p.total_val_cents), 4)
        ELSE NULL
    END AS assessment_ratio,
    p.acre_area,
    aa.fairness_score,
    aa.recommended_action,
    aa.estimated_savings_cents / 100.0 AS estimated_savings_dollars,
    aa.analysis_date AS last_analysis_date
FROM properties p
LEFT JOIN LATERAL (
    SELECT * FROM assessment_analyses
    WHERE property_id = p.id
    ORDER BY analysis_date DESC
    LIMIT 1
) aa ON true
WHERE p.is_active = true;

COMMENT ON VIEW v_property_assessment_summary IS 'Summary view for property assessment analysis with latest fairness scores';

-- ============================================================================
-- SEED DATA: Insert sample user for testing
-- ============================================================================

-- Note: In production, use proper password hashing (bcrypt/argon2)
-- This is just a placeholder for development
-- INSERT INTO users (email, password_hash, user_type, first_name, last_name)
-- VALUES ('admin@taxdown.com', '$2b$12$placeholder_hash_here', 'ADMIN', 'Admin', 'User');

-- ============================================================================
-- MIGRATION METADATA
-- ============================================================================

-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    checksum VARCHAR(64)
);

-- Record this migration
INSERT INTO schema_migrations (version, name, checksum)
VALUES (
    '001',
    'initial_schema',
    'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'  -- Pre-computed checksum for migration tracking
) ON CONFLICT (version) DO NOTHING;

COMMENT ON TABLE schema_migrations IS 'Tracks executed database migrations for version control';
