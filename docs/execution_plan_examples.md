# Query Execution Plan Examples

**PostgreSQL 14+ with PostGIS 3+**
**Dataset:** 173,743 parcels (Benton County, Arkansas)

This document shows expected EXPLAIN ANALYZE output for the core queries, helping you identify performance issues.

---

## How to Analyze Query Plans

### Basic Analysis

```sql
EXPLAIN SELECT * FROM find_comparable_properties('16-26005-000');
```

Shows estimated costs and query plan without executing.

### Full Analysis with Timing

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM find_comparable_properties('16-26005-000');
```

Shows actual execution time, rows processed, and buffer usage.

### Key Metrics to Watch

- **Execution Time:** Total time in milliseconds
- **Index Usage:** Look for "Index Scan" (good) vs "Seq Scan" (bad for large tables)
- **Rows Estimated vs Actual:** Large discrepancies indicate stale statistics
- **Buffers:** Shared hit = from cache (fast), read = from disk (slower)
- **Sort/Hash Memory:** Should fit in work_mem

---

## 1. Comparable Property Matching

### Optimal Plan (With Indexes)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM find_comparable_properties('16-26005-000');
```

**Expected Output:**

```
Function Scan on find_comparable_properties
  (cost=0.00..10.00 rows=1000 width=...)
  (actual time=45.234..152.678 rows=20 loops=1)
  Planning Time: 2.156 ms
  Execution Time: 153.234 ms

  ->  Limit  (cost=485.23..495.45 rows=20 width=...)
       (actual time=148.567..152.123 rows=20 loops=1)
       ->  Sort  (cost=485.23..488.67 rows=1375 width=...)
            Sort Key: similarity_score DESC, distance_miles
            Sort Method: top-N heapsort  Memory: 32kB
            (actual time=148.543..152.089 rows=20 loops=1)
            ->  Append  (cost=100.23..465.89 rows=1375 width=...)
                 (actual time=12.456..145.234 rows=847 loops=1)

                 ->  CTE Scan on subdivision_matches
                      (cost=100.23..150.45 rows=50 width=...)
                      (actual time=12.432..18.765 rows=48 loops=1)
                      ->  Index Scan using idx_parcels_subdivname on parcels p
                           Index Cond: (subdivname = 'REIGHTON SUB-BVV')
                           Filter: (type_ = 'RV' AND total_val BETWEEN ...)
                           Rows Removed by Filter: 8
                           (actual time=0.089..2.345 rows=48 loops=1)
                           Buffers: shared hit=45

                 ->  CTE Scan on proximity_matches
                      (cost=200.67..315.44 rows=1325 width=...)
                      (actual time=42.123..125.678 rows=799 loops=1)
                      ->  Index Scan using idx_parcels_geometry on parcels p
                           Index Cond: ST_DWithin(geometry::geography, ...)
                           Filter: (type_ = 'RV' AND total_val BETWEEN ...)
                           Rows Removed by Filter: 1234
                           (actual time=0.234..98.456 rows=799 loops=1)
                           Buffers: shared hit=2456 read=123

Planning Time: 2.156 ms
Execution Time: 153.234 ms
```

**Analysis:**

✅ **Good Indicators:**
- Uses `idx_parcels_subdivname` for subdivision matches
- Uses `idx_parcels_geometry` for spatial query
- Sort method is "top-N heapsort" (efficient for LIMIT)
- Execution time ~150ms (within 300ms target)
- Most buffers are "shared hit" (cached in memory)

⚠️ **Watch For:**
- "Rows Removed by Filter" should be reasonable (<80% removed)
- Sort should fit in memory (no "external merge" disk sort)

---

### Suboptimal Plan (Without Spatial Index)

```
Function Scan on find_comparable_properties
  (cost=0.00..10.00 rows=1000 width=...)
  (actual time=234.567..5432.123 rows=20 loops=1)

  ->  Seq Scan on parcels p  ❌ SEQUENTIAL SCAN - BAD!
       Filter: (ST_DWithin(...) AND type_ = 'RV' AND ...)
       Rows Removed by Filter: 173723
       (actual time=1.234..5234.567 rows=799 loops=1)
       Buffers: shared hit=12345 read=45678  ❌ TOO MANY READS

Execution Time: 5432.123 ms  ❌ TOO SLOW (>5 seconds)
```

**Fix:**
```sql
CREATE INDEX idx_parcels_geometry ON parcels USING GIST(geometry);
ANALYZE parcels;
```

---

## 2. Neighborhood Median Ratio

### Optimal Plan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_neighborhood_median_ratio('16-26005-000');
```

**Expected Output:**

```
Function Scan on get_neighborhood_median_ratio
  (cost=0.00..0.26 rows=1 width=...)
  (actual time=78.234..78.237 rows=1 loops=1)
  Planning Time: 1.234 ms
  Execution Time: 78.567 ms

  ->  Aggregate  (cost=245.67..245.69 rows=1 width=...)
       (actual time=75.123..75.126 rows=1 loops=1)
       ->  Index Scan using idx_parcels_str_ratio on parcels
            Index Cond: (s_t_r = '32-21-30')
            Filter: (total_val > 0 AND assess_val > 0)
            (actual time=0.056..12.345 rows=1847 loops=1)
            Buffers: shared hit=234

       ->  Sort  (for PERCENTILE_CONT)
            Sort Key: assessment_ratio
            Sort Method: quicksort  Memory: 145kB
            (actual time=62.345..64.123 rows=1847 loops=1)

Planning Time: 1.234 ms
Execution Time: 78.567 ms
```

**Analysis:**

✅ **Good Indicators:**
- Uses `idx_parcels_str_ratio` (expression index)
- Sort fits in memory (145kB << work_mem)
- Execution time ~80ms (within 150ms target)
- Only ~1800 rows processed (neighborhood size)

---

### Suboptimal Plan (Without Expression Index)

```
->  Aggregate
     ->  Seq Scan on parcels  ❌ SEQUENTIAL SCAN
          Filter: (s_t_r = '32-21-30' AND total_val > 0 ...)
          Rows Removed by Filter: 171896
          (actual time=0.234..2345.678 rows=1847 loops=1)

     ->  Sort
          Sort Key: ((assess_val / total_val) * 100)  ❌ COMPUTED EVERY TIME
          Sort Method: external merge  Disk: 8192kB  ❌ SPILLED TO DISK
          (actual time=3456.789..3678.901 rows=1847 loops=1)

Execution Time: 3987.234 ms  ❌ WAY TOO SLOW
```

**Fix:**
```sql
CREATE INDEX idx_parcels_str_ratio
    ON parcels(s_t_r, ((assess_val::NUMERIC / NULLIF(total_val, 0)::NUMERIC)))
    WHERE total_val > 0 AND assess_val > 0;
ANALYZE parcels;
```

---

## 3. Percentile Ranking

### Optimal Plan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_property_percentile_ranking('16-26005-000');
```

**Expected Output:**

```
Function Scan on get_property_percentile_ranking
  (cost=0.00..0.26 rows=1 width=...)
  (actual time=234.567..234.570 rows=1 loops=1)
  Planning Time: 2.345 ms
  Execution Time: 235.123 ms

  ->  Nested Loop  (cost=567.89..890.23 rows=1 width=...)
       (actual time=230.123..234.234 rows=1 loops=1)

       ->  Aggregate (neighborhood_stats)
            ->  Index Scan using idx_parcels_str_ratio
                 Index Cond: (s_t_r = '32-21-30')
                 (actual time=0.089..15.234 rows=1847 loops=1)

       ->  Aggregate (subdivision_stats)
            ->  Index Scan using idx_parcels_subdiv_ratio
                 Index Cond: (subdivname = 'REIGHTON SUB-BVV')
                 (actual time=0.045..8.123 rows=48 loops=1)

       ->  Aggregate (property_type_stats)
            ->  Index Scan using idx_parcels_type_ratio
                 Index Cond: (type_ = 'RV')
                 (actual time=0.123..98.456 rows=45234 loops=1)
                 Buffers: shared hit=3456

Planning Time: 2.345 ms
Execution Time: 235.123 ms
```

**Analysis:**

✅ **Good Indicators:**
- Three separate index scans (neighborhood, subdivision, type)
- Each uses appropriate expression index
- Execution time ~235ms (within 300ms target)
- Parallel execution of three aggregates

⚠️ **Watch For:**
- Type stats process most rows (~45K) - largest contributor to time
- Should still be <300ms total

---

## 4. Assessment Fairness Summary View

### Full Scan (Expected to be Slow)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM v_assessment_fairness_summary;
```

**Expected Output:**

```
Hash Join  (cost=12345.67..45678.90 rows=171145 width=...)
  (actual time=1234.567..3456.789 rows=171145 loops=1)
  Hash Cond: (pr.s_t_r = nm.s_t_r)
  Planning Time: 45.678 ms
  Execution Time: 3891.234 ms  ⚠️ SLOW BUT EXPECTED

  ->  CTE Scan on property_ratios pr
       (cost=0.00..3456.78 rows=171145 width=...)
       ->  Seq Scan on parcels p  ⚠️ SEQ SCAN IS OK HERE (full table needed)
            Filter: (total_val > 0 AND assess_val > 0)
            Rows Removed by Filter: 2598
            (actual time=0.123..567.890 rows=171145 loops=1)

  ->  Hash (neighborhood_medians)
       Buckets: 2048  Batches: 1  Memory: 256kB
       ->  HashAggregate
            Group Key: s_t_r
            (actual time=1234.567..1567.890 rows=1247 loops=1)
            ->  CTE Scan on property_ratios
                 (actual time=0.001..890.123 rows=171145 loops=1)

  ->  Hash Join (subdivision_medians)
       Similar pattern...

Planning Time: 45.678 ms
Execution Time: 3891.234 ms
Buffers: shared hit=12345 read=2345
```

**Analysis:**

✅ **This is EXPECTED:**
- Sequential scan is appropriate (processing entire table)
- 3-4 seconds for 171K records is reasonable
- Should cache results in materialized view

**Recommendation:**
```sql
-- Don't query this view directly for real-time use
-- Instead, create materialized view:
CREATE MATERIALIZED VIEW mv_assessment_fairness_summary AS
SELECT * FROM v_assessment_fairness_summary;

-- Refresh nightly
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_assessment_fairness_summary;

-- Then query the materialized view (fast!)
SELECT * FROM mv_assessment_fairness_summary
WHERE appeal_priority = 'HIGH_PRIORITY';
```

---

## Common Performance Issues

### Issue 1: Sequential Scan Instead of Index Scan

**Symptom:**
```
Seq Scan on parcels  (cost=0.00..45678.90 rows=173743 width=...)
```

**Causes:**
1. Index doesn't exist
2. Statistics are outdated
3. Query doesn't match index condition
4. PostgreSQL estimates seq scan is faster (small result set)

**Solutions:**
```sql
-- Create missing index
CREATE INDEX idx_name ON parcels(column_name);

-- Update statistics
ANALYZE parcels;

-- Check if index exists
SELECT * FROM pg_indexes WHERE tablename = 'parcels';

-- Force index usage (testing only)
SET enable_seqscan = OFF;
```

---

### Issue 2: Sort Spilling to Disk

**Symptom:**
```
Sort Method: external merge  Disk: 8192kB
```

**Cause:** work_mem too small for sort operation

**Solution:**
```sql
-- Increase work_mem for session
SET work_mem = '128MB';

-- Or permanently in postgresql.conf
work_mem = 128MB
```

---

### Issue 3: High Buffer Reads (Not Hits)

**Symptom:**
```
Buffers: shared hit=123 read=45678  ❌ Too many disk reads
```

**Causes:**
1. Data not in cache
2. shared_buffers too small
3. First query after restart

**Solutions:**
```sql
-- In postgresql.conf:
shared_buffers = 2GB  # 25% of total RAM

-- Warm up cache (run query twice)
SELECT * FROM find_comparable_properties('16-26005-000');
SELECT * FROM find_comparable_properties('16-26005-000');  -- Should show more hits

-- Check cache hit ratio
SELECT
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
-- Should be > 0.99 (99%)
```

---

### Issue 4: Inaccurate Row Estimates

**Symptom:**
```
(cost=100.00..200.00 rows=50 width=...)
(actual time=10.123..234.567 rows=5000 loops=1)  ❌ Estimated 50, got 5000
```

**Cause:** Outdated statistics

**Solution:**
```sql
ANALYZE parcels;

-- For persistent issues, increase statistics target
ALTER TABLE parcels ALTER COLUMN type_ SET STATISTICS 1000;
ANALYZE parcels;
```

---

## Benchmarking Commands

### Test All Core Functions

```sql
-- Warm up cache
SELECT * FROM find_comparable_properties('16-26005-000');

-- Benchmark comparable matching
\timing on
SELECT * FROM find_comparable_properties('16-26005-000');
SELECT * FROM find_comparable_properties('02-13045-000');
SELECT * FROM find_comparable_properties('18-11331-002');
\timing off

-- Should be consistently <300ms
```

### Test with EXPLAIN ANALYZE

```sql
-- Save to file for analysis
\o /tmp/explain_output.txt

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM find_comparable_properties('16-26005-000');

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM get_neighborhood_median_ratio('16-26005-000');

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM get_property_percentile_ranking('16-26005-000');

\o
```

---

## Performance Tuning Checklist

Before deploying to production:

- [ ] All indexes created (12+ indexes)
- [ ] Statistics updated (`ANALYZE parcels`)
- [ ] work_mem ≥ 64MB
- [ ] shared_buffers ≥ 2GB (25% of RAM)
- [ ] effective_cache_size ≥ 6GB (75% of RAM)
- [ ] All queries use index scans (no seq scans except for full table)
- [ ] Sorts fit in memory (no external merge)
- [ ] Cache hit ratio > 99%
- [ ] Query times meet targets:
  - [ ] Comparable matching: <300ms
  - [ ] Neighborhood median: <150ms
  - [ ] Subdivision median: <100ms
  - [ ] Percentile ranking: <300ms

---

## PostgreSQL Configuration for Optimal Performance

Add to `postgresql.conf`:

```ini
# Memory Settings
shared_buffers = 2GB                    # 25% of RAM
effective_cache_size = 6GB              # 75% of RAM
work_mem = 64MB                         # Per operation
maintenance_work_mem = 512MB            # For VACUUM, CREATE INDEX

# Query Planner
random_page_cost = 1.1                  # For SSD (default 4.0 for HDD)
effective_io_concurrency = 200          # For SSD (default 1 for HDD)
default_statistics_target = 100         # Higher = better estimates

# Parallel Execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 8

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Logging (for troubleshooting)
log_min_duration_statement = 1000       # Log queries > 1 second
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '
```

After changes:
```bash
sudo systemctl restart postgresql
```

---

## Monitoring Queries

### Find Slow Queries

```sql
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE query LIKE '%find_comparable_properties%'
ORDER BY mean_time DESC;
```

### Check Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'parcels'
ORDER BY idx_scan DESC;
```

### Check Table Statistics

```sql
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'parcels';
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-07
**PostgreSQL Version:** 14+
**PostGIS Version:** 3+
