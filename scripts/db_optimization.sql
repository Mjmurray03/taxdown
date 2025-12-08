-- PostgreSQL Performance Optimization for TaxDown
-- Production Database Configuration for Railway
-- Run these queries to optimize query performance

-- ============================================
-- VERIFY EXISTING INDEXES
-- ============================================

-- View all indexes on properties table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'properties'
ORDER BY indexname;

-- ============================================
-- ADDITIONAL PERFORMANCE INDEXES
-- ============================================

-- Index for sorting by creation date (recent properties first)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_created_at
ON properties(created_at DESC);

-- Index for sorting by update date (recently modified)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_updated_at
ON properties(updated_at DESC);

-- Composite index for common query patterns (city filtering with value sorting)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_city_value
ON properties(city, total_val_cents DESC);

-- Partial index for appeal candidates (high-value optimization)
-- Only indexes properties worth > $100k for faster appeal candidate queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_appeal_candidates
ON properties(id, total_val_cents, assess_val_cents)
WHERE total_val_cents > 10000000; -- Properties > $100k (stored in cents)

-- ============================================
-- ANALYZE TABLES FOR QUERY PLANNER
-- ============================================

-- Update statistics for optimal query planning
ANALYZE properties;
ANALYZE assessment_analyses;
ANALYZE appeals;
ANALYZE portfolios;
ANALYZE portfolio_properties;

-- ============================================
-- USEFUL DIAGNOSTIC QUERIES
-- ============================================

-- Check table sizes
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Check index usage statistics
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Find unused indexes (candidates for removal)
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
ORDER BY relname, indexrelname;

-- Check for missing indexes (sequential scans on large tables)
SELECT
    relname AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    CASE WHEN seq_scan > 0
         THEN round((seq_tup_read::numeric / seq_scan), 2)
         ELSE 0
    END AS avg_seq_tuples
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC;
