-- Taxdown - Portfolios Schema Migration
-- Migration: 002_portfolios.sql
-- Created: 2025-12-08
-- Description: Creates portfolios table to allow users to organize properties into named collections

-- ============================================================================
-- TABLE: portfolios
-- Description: Named property collections for users
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Portfolio metadata
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Settings
    default_mill_rate DECIMAL(6,2) DEFAULT 65.0,
    auto_analyze BOOLEAN DEFAULT true,

    -- System fields
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT unique_portfolio_name_per_user UNIQUE (user_id, name)
);

COMMENT ON TABLE portfolios IS 'Named property collections for organizing user portfolios';

-- ============================================================================
-- TABLE: portfolio_properties
-- Description: Junction table linking portfolios to properties
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolio_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Relationship details
    ownership_type ownership_type_enum NOT NULL DEFAULT 'TRACKING',
    ownership_percentage DECIMAL(5,2) DEFAULT 100.0,

    -- Purchase/acquisition information
    purchase_date DATE,
    purchase_price_cents BIGINT,

    -- Property flags
    is_primary_residence BOOLEAN DEFAULT false,

    -- User notes and organization
    notes TEXT,
    tags JSONB DEFAULT '[]',

    -- Timestamps
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique property per portfolio
    CONSTRAINT unique_property_per_portfolio UNIQUE (portfolio_id, property_id)
);

COMMENT ON TABLE portfolio_properties IS 'Links properties to portfolios with ownership details';

-- ============================================================================
-- TABLE: tax_appeals (if not exists)
-- Description: Stores generated tax appeals
-- ============================================================================

CREATE TABLE IF NOT EXISTS tax_appeals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Appeal content
    appeal_letter_text TEXT,
    executive_summary TEXT,
    evidence_summary TEXT,

    -- Values
    original_assessed_value_cents BIGINT,
    requested_value_cents BIGINT,
    reduction_amount_cents BIGINT,

    -- Analysis reference
    fairness_score INTEGER,
    success_probability DECIMAL(3,2),
    comparable_count INTEGER DEFAULT 0,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'GENERATED',

    -- Generation metadata
    generator_type VARCHAR(50) DEFAULT 'TEMPLATE',
    template_style VARCHAR(50) DEFAULT 'formal',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tax_appeals IS 'Generated property tax appeal letters and packages';

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_name ON portfolios(name);
CREATE INDEX IF NOT EXISTS idx_portfolios_is_active ON portfolios(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_portfolio_properties_portfolio_id ON portfolio_properties(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_properties_property_id ON portfolio_properties(property_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_properties_ownership_type ON portfolio_properties(ownership_type);

CREATE INDEX IF NOT EXISTS idx_tax_appeals_property_id ON tax_appeals(property_id);
CREATE INDEX IF NOT EXISTS idx_tax_appeals_status ON tax_appeals(status);
CREATE INDEX IF NOT EXISTS idx_tax_appeals_created_at ON tax_appeals(created_at);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER trigger_portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_portfolio_properties_updated_at
    BEFORE UPDATE ON portfolio_properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_tax_appeals_updated_at
    BEFORE UPDATE ON tax_appeals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MIGRATION METADATA
-- ============================================================================

INSERT INTO schema_migrations (version, name, checksum)
VALUES (
    '002',
    'portfolios',
    'b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7'
) ON CONFLICT (version) DO NOTHING;
