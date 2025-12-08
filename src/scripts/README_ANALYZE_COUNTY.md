# Benton County Property Tax Assessment Batch Analyzer

## Overview

The `analyze_county.py` script performs batch analysis of properties in Benton County to identify potential tax appeal candidates based on statistical fairness scoring and savings estimation.

## Features

- **Batch Processing**: Analyze hundreds or thousands of properties efficiently
- **Flexible Filtering**: Filter by subdivision, property type, value ranges
- **Progress Tracking**: Real-time progress bars (with tqdm) and statistics
- **CSV Export**: Export results to CSV for Excel/Sheets analysis
- **Database Persistence**: Optionally save results to assessment_analyses table
- **Beautiful Reports**: Formatted summary reports with top candidates
- **Error Resilient**: Continues analysis even if individual properties fail

## Installation

```bash
# Optional: Install tqdm for progress bars
pip install tqdm
```

## Usage

### Basic Examples

```bash
# Analyze first 1000 properties (default)
python src/scripts/analyze_county.py

# Analyze 500 properties with higher thresholds
python src/scripts/analyze_county.py --limit 500 --min-score 70 --min-savings 500

# Analyze specific subdivision
python src/scripts/analyze_county.py --subdivision "AVONDALE SUB 1" --limit 100

# Save results to CSV
python src/scripts/analyze_county.py --limit 2000 --output appeal_candidates.csv

# Verbose mode with detailed progress
python src/scripts/analyze_county.py --limit 1000 --verbose
```

### Advanced Examples

```bash
# Full county analysis (WARNING: may take 20-30 hours)
python src/scripts/analyze_county.py --full --output full_county_results.csv --save-db

# Focus on high-value properties with strong appeal potential
python src/scripts/analyze_county.py --limit 1000 --min-score 75 --min-savings 1000

# Analyze commercial properties
python src/scripts/analyze_county.py --property-type COM --limit 200

# Custom mill rate (default is 65.0)
python src/scripts/analyze_county.py --limit 500 --mill-rate 70.0
```

## Command Line Arguments

### Analysis Parameters

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--limit` | int | 1000 | Maximum properties to analyze |
| `--min-score` | int | 60 | Minimum fairness score (0-100) to include |
| `--min-savings` | int | 250 | Minimum annual savings in dollars |
| `--mill-rate` | float | 65.0 | Mill rate for tax calculations |

### Filters

| Argument | Type | Description |
|----------|------|-------------|
| `--subdivision` | string | Filter to specific subdivision (partial match) |
| `--property-type` | string | Filter by property type (RES, COM, etc.) |

### Output Options

| Argument | Type | Description |
|----------|------|-------------|
| `--output` | string | Output CSV file path |
| `--save-db` | flag | Save results to assessment_analyses table |
| `--verbose` | flag | Show detailed progress and debug info |
| `--full` | flag | Analyze ALL properties (overrides --limit) |

## Output Format

### Console Summary

```
======================================================================
BENTON COUNTY ASSESSMENT ANALYSIS COMPLETE
======================================================================
Properties Analyzed:     1,000
Analysis Time:          12m 34s
Errors/Skipped:         23

APPEAL CANDIDATES FOUND: 127 (12.7%)
├── Strong Cases:        23
├── Moderate Cases:      58
└── Weak (Monitor):      46

POTENTIAL SAVINGS IDENTIFIED:
├── Annual Total:       $89,450
├── 5-Year Total:      $447,250
└── Average per Case:     $704

TOP 5 APPEAL CANDIDATES:

1. 123 Main St
   Score: 94, Savings: $2,340/yr, Strength: STRONG
2. 456 Oak Ave
   Score: 89, Savings: $1,890/yr, Strength: STRONG
...

Results saved to: appeal_candidates.csv
======================================================================
```

### CSV Output

The CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| property_id | UUID of the property |
| parcel_id | Parcel ID (e.g., 16-02302-000) |
| address | Property address |
| total_value | Market value in dollars |
| assessed_value | Assessed value in dollars |
| fairness_score | Fairness score (0-100) |
| confidence | Confidence in analysis (0-100) |
| annual_savings | Estimated annual tax savings |
| five_year_savings | Estimated 5-year savings |
| recommendation | APPEAL, MONITOR, or NONE |
| appeal_strength | STRONG, MODERATE, or WEAK |

## Performance

### Expected Processing Speed

- **Target Rate**: ~100 properties per minute
- **Actual Rate**: 40-60 properties per minute (depends on comparables)
- **Full County (173K properties)**: ~29-48 hours

### Memory Usage

- Minimal memory footprint
- Processes properties one at a time
- Database connections are managed efficiently

### Optimization Tips

1. **Use --limit**: Start small to test before running full analysis
2. **Filter by subdivision**: Analyze neighborhoods instead of entire county
3. **Run during off-hours**: Database queries are less impacted
4. **Use --save-db carefully**: Only save if you need database persistence

## Understanding Results

### Fairness Scores

- **0-40**: Property is fairly or under-assessed (no action needed)
- **41-60**: Slightly over-assessed (monitor for changes)
- **61-80**: Significantly over-assessed (appeal recommended)
- **81-100**: Severely over-assessed (strong appeal case)

### Appeal Strength

- **STRONG**: fairness >= 70, confidence >= 60, savings >= $500/year
- **MODERATE**: fairness >= 60, savings >= $250/year
- **WEAK**: fairness >= 50 (monitor recommended)

### Confidence Levels

- **0-50**: Low confidence (few comparables or high variance)
- **51-75**: Moderate confidence (decent comparables)
- **76-100**: High confidence (many similar comparables, low variance)

## Common Issues

### No Comparables Found

Some properties (especially high-value or unique properties) may not have good comparables:

```
WARNING: No comparables found for property 01-08641-005
```

**Solution**: This is normal. The script will skip these and continue.

### All Properties Filtered Out

If you see 0 appeal candidates, try:
- Lower `--min-score` (default is 60, try 50 or 40)
- Lower `--min-savings` (default is $250, try $100)
- Increase `--limit` to analyze more properties

### Slow Performance

If analysis is slower than expected:
- Check database connection (public vs private URL)
- Reduce `--limit` for testing
- Use `--subdivision` to focus on specific areas

## Examples with Real Data

### Find Top Appeal Cases in Bella Vista

```bash
python src/scripts/analyze_county.py \
  --subdivision "BELLA VISTA" \
  --limit 500 \
  --min-score 70 \
  --min-savings 500 \
  --output bella_vista_appeals.csv
```

### Analyze Entire Subdivision

```bash
python src/scripts/analyze_county.py \
  --subdivision "AVONDALE SUB 1" \
  --min-score 50 \
  --output avondale_analysis.csv
```

### Quick Test Run

```bash
# Test with just 50 properties to verify everything works
python src/scripts/analyze_county.py --limit 50 --verbose
```

### Production Full County Analysis

```bash
# Run overnight, save everything
python src/scripts/analyze_county.py \
  --full \
  --min-score 60 \
  --min-savings 250 \
  --output full_county_$(date +%Y%m%d).csv \
  --save-db \
  > analysis_log_$(date +%Y%m%d).txt 2>&1
```

## Integration with Other Tools

### Import to Excel/Google Sheets

The CSV output can be directly imported into Excel or Google Sheets for:
- Sorting by savings potential
- Filtering by neighborhood
- Creating pivot tables
- Generating charts

### Database Integration

When using `--save-db`, results are saved to `assessment_analyses` table:

```sql
SELECT
  p.parcel_id,
  p.ph_add,
  a.fairness_score,
  a.estimated_savings_cents / 100.0 as annual_savings,
  a.recommended_action
FROM assessment_analyses a
JOIN properties p ON p.id = a.property_id
WHERE a.fairness_score >= 70
ORDER BY a.estimated_savings_cents DESC
LIMIT 20;
```

### Automated Workflows

Schedule regular analyses:

```bash
# Weekly analysis (cron job)
0 2 * * 0 cd /path/to/taxdown && python src/scripts/analyze_county.py --limit 5000 --output weekly_$(date +\%Y\%m\%d).csv
```

## Technical Details

### Architecture

The script uses a modular architecture:

```
analyze_county.py
├── AssessmentAnalyzer (orchestrator)
│   ├── ComparableService (find similar properties)
│   ├── FairnessScorer (statistical analysis)
│   └── SavingsEstimator (tax calculations)
└── Database (PostgreSQL + PostGIS)
```

### Error Handling

- **Property not found**: Logs warning, continues
- **No comparables**: Logs warning, skips property
- **Database error**: Logs error, retries or skips
- **Keyboard interrupt**: Graceful shutdown

### Logging

- Default: INFO level (key progress updates)
- Verbose: DEBUG level (detailed analysis steps)
- Errors: Always logged with full stack trace

## Support

For issues or questions:
1. Check this README
2. Review service documentation in `src/services/`
3. Enable `--verbose` mode to see detailed logs
4. Check database connection with `src/config.py`

## Version History

- **v1.0.0** (2025-12-08): Initial release
  - Batch analysis with filtering
  - CSV export
  - Database persistence
  - Progress tracking
  - Beautiful console reports
