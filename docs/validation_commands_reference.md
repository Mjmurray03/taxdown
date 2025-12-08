# Database Validation Commands Reference

Quick reference for running database validation queries against the Taxdown Railway database.

## Connection Information

```bash
# Public connection URL
DATABASE_URL="postgres://postgres:f2af4DCdcBGCagDcA4gGDcFf2aCgCB5G@mainline.proxy.rlwy.net:53382/railway"

# Connect via psql
psql "postgres://postgres:f2af4DCdcBGCagDcA4gGDcFf2aCgCB5G@mainline.proxy.rlwy.net:53382/railway"
```

## Quick Validation Commands

### 1. Row Counts
```bash
psql "$DATABASE_URL" -c "
SELECT 'Properties' as table_name, COUNT(*) FROM properties
UNION ALL
SELECT 'Subdivisions', COUNT(*) FROM subdivisions;
"
```

### 2. Data Quality Check
```bash
psql "$DATABASE_URL" -c "
SELECT
    COUNT(*) as total_properties,
    COUNT(*) FILTER (WHERE parcel_id IS NOT NULL) as with_parcel_id,
    COUNT(*) FILTER (WHERE parcel_id IS NULL) as null_parcel_id,
    COUNT(*) FILTER (WHERE geometry IS NOT NULL) as with_geometry,
    COUNT(*) FILTER (WHERE assess_val_cents > 0) as with_assessment,
    COUNT(*) FILTER (WHERE total_val_cents > 0) as with_value
FROM properties;
"
```

### 3. Spatial Validation
```bash
psql "$DATABASE_URL" -c "
SELECT
    COUNT(*) FILTER (WHERE ST_IsValid(geometry)) as valid_geoms,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geometry)) as invalid_geoms,
    COUNT(*) as total_geoms
FROM properties
WHERE geometry IS NOT NULL;
"
```

### 4. Assessment Ratio Check
```bash
psql "$DATABASE_URL" -c "
SELECT
    ROUND(AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)), 4) as avg_ratio,
    ROUND(AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100, 2) as avg_ratio_pct,
    COUNT(*) as sample_size
FROM properties
WHERE total_val_cents > 0 AND assess_val_cents > 0;
"
```

### 5. Value Statistics
```bash
psql "$DATABASE_URL" -c "
SELECT
    MIN(total_val_cents) as min_value,
    MAX(total_val_cents) as max_value,
    AVG(total_val_cents)::BIGINT as avg_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_val_cents)::BIGINT as median_value,
    COUNT(*) as count_with_value
FROM properties
WHERE total_val_cents > 0;
"
```

## Comprehensive Validation Script

Run the full validation suite:

```bash
psql "$DATABASE_URL" -f "C:\taxdown\validation_queries_v2.sql"
```

## Comparable Matching Test

Test the comparable matching algorithm:

```bash
# Simple test query
psql "$DATABASE_URL" -f "C:\taxdown\test_comparable_simple.sql"
```

## Advanced Queries

### Find Invalid Geometries
```sql
SELECT parcel_id, ph_add, subdivname
FROM properties
WHERE geometry IS NOT NULL
  AND NOT ST_IsValid(geometry)
ORDER BY parcel_id;
```

### Spatial Relationship Test
```sql
SELECT COUNT(*)
FROM properties p
JOIN subdivisions s ON ST_Within(p.geometry, s.geometry)
WHERE p.geometry IS NOT NULL AND s.geometry IS NOT NULL;
```

### Property Type Distribution
```sql
SELECT
    type_,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM properties) * 100, 2) as pct
FROM properties
WHERE type_ IS NOT NULL
GROUP BY type_
ORDER BY count DESC;
```

### Subdivision Statistics
```sql
SELECT
    s.name,
    COUNT(p.parcel_id) as property_count,
    AVG(p.total_val_cents) as avg_value,
    AVG(p.acre_area) as avg_acreage
FROM subdivisions s
LEFT JOIN properties p ON ST_Within(p.geometry, s.geometry)
GROUP BY s.name
HAVING COUNT(p.parcel_id) > 10
ORDER BY property_count DESC
LIMIT 20;
```

### Assessment Fairness by Property Type
```sql
SELECT
    type_,
    COUNT(*) as count,
    ROUND(AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100, 2) as avg_ratio_pct,
    ROUND(STDDEV(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100, 2) as stddev_ratio_pct
FROM properties
WHERE total_val_cents > 0 AND assess_val_cents > 0
GROUP BY type_
HAVING COUNT(*) > 100
ORDER BY count DESC;
```

## Performance Monitoring

### Check Index Usage
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Table Statistics
```sql
SELECT
    schemaname,
    tablename,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public';
```

### Long Running Queries
```sql
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
  AND state != 'idle'
ORDER BY duration DESC;
```

## Automated Validation Schedule

### Daily Health Check
```bash
#!/bin/bash
# Save as: daily_health_check.sh

DATE=$(date +%Y-%m-%d)
OUTPUT="validation_${DATE}.txt"

echo "Taxdown Database Health Check - ${DATE}" > $OUTPUT
echo "========================================" >> $OUTPUT

psql "$DATABASE_URL" -c "
SELECT
    'Properties' as metric,
    COUNT(*) as value
FROM properties
UNION ALL
SELECT 'Valid Geometries', COUNT(*) FROM properties WHERE ST_IsValid(geometry)
UNION ALL
SELECT 'Avg Assessment Ratio', ROUND(AVG(assess_val_cents::NUMERIC / NULLIF(total_val_cents, 0)) * 100, 2)
FROM properties WHERE total_val_cents > 0;
" >> $OUTPUT

echo "Health check saved to: $OUTPUT"
```

## Troubleshooting

### Connection Issues
```bash
# Test connection
psql "$DATABASE_URL" -c "SELECT version();"

# Test PostGIS
psql "$DATABASE_URL" -c "SELECT PostGIS_Version();"
```

### Performance Issues
```sql
-- Analyze tables to update statistics
ANALYZE properties;
ANALYZE subdivisions;

-- Check for missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename = 'properties'
ORDER BY abs(correlation) DESC;
```

### Spatial Query Debugging
```sql
-- Explain a spatial query
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM properties
WHERE ST_DWithin(
    geometry,
    ST_SetSRID(ST_MakePoint(-94.2, 36.4), 4326),
    0.01
);
```

## Expected Results (as of 2025-12-08)

| Metric | Expected Value |
|--------|---------------|
| **Total Properties** | 173,743 |
| **Total Subdivisions** | 4,041 |
| **Properties with Buildings** | 94,555 |
| **Valid Geometries** | 173,677 (99.96%) |
| **Assessment Ratio** | 20.00% |
| **Properties with Assessments** | 161,278 (92.8%) |

## Files

- **Full Validation Script:** `C:\taxdown\validation_queries_v2.sql`
- **Comparable Test:** `C:\taxdown\test_comparable_simple.sql`
- **Full Report:** `C:\taxdown\docs\phase3_validation_report.md`
- **Quick Summary:** `C:\taxdown\docs\phase3_validation_summary.md`
- **Invalid Geometries:** `C:\taxdown\docs\invalid_geometries_list.md`

## Notes

- All queries tested on PostgreSQL 15 with PostGIS 3.x
- Connection uses Railway public network endpoint
- Query timeout: 2 minutes (default)
- For long-running queries, increase timeout: `--set statement_timeout=300000`
