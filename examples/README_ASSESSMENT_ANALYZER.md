# Assessment Analyzer - User Guide

## Overview

The Assessment Analyzer is the core orchestration service that combines all Phase 4 analysis capabilities to provide comprehensive property tax assessment analysis. It identifies over-assessed properties and estimates potential tax savings from successful appeals.

## Features

1. **Comprehensive Property Analysis**
   - Finds comparable properties using spatial and statistical matching
   - Calculates fairness scores based on assessment ratios
   - Estimates tax savings potential
   - Provides actionable recommendations

2. **Batch Processing**
   - Analyze multiple properties efficiently
   - Progress logging for large datasets
   - Memory-efficient batch processing

3. **Appeal Candidate Discovery**
   - Query database for potentially over-assessed properties
   - Rank by savings potential
   - Filter by minimum fairness score

## Architecture

The Assessment Analyzer orchestrates three core services:

```
AssessmentAnalyzer
├── ComparableService    → Find similar properties
├── FairnessScorer       → Calculate statistical fairness
└── SavingsEstimator     → Estimate tax savings
```

## Data Model

### AssessmentAnalysis

Complete analysis result for a property:

```python
@dataclass
class AssessmentAnalysis:
    # Property identification
    property_id: str
    parcel_id: Optional[str]
    address: str

    # Current values (all in cents)
    total_val_cents: int
    assess_val_cents: int
    current_ratio: float

    # Analysis results
    fairness_score: int          # 0-100 (higher = more over-assessed)
    confidence: int              # 0-100 (confidence in analysis)
    interpretation: str          # "FAIR", "OVER_ASSESSED", "UNDER_ASSESSED"

    # Comparables summary
    comparable_count: int
    median_comparable_ratio: float

    # Savings estimate
    estimated_annual_savings_cents: int
    estimated_five_year_savings_cents: int

    # Recommendation
    recommended_action: str      # "APPEAL", "MONITOR", "NONE"
    appeal_strength: str         # "STRONG", "MODERATE", "WEAK"

    # Metadata
    analysis_date: datetime
    model_version: str
```

## Recommendation Logic

The system uses a multi-factor algorithm to determine recommendations:

### STRONG APPEAL
- Fairness Score >= 70
- Confidence >= 60
- Annual Savings >= $500

### MODERATE APPEAL
- Fairness Score >= 60
- Annual Savings >= $250

### MONITOR (Weak case)
- Fairness Score >= 50
- May become appeal-worthy in future

### NO ACTION
- Fairness Score < 50
- Property is fairly assessed

## Usage Examples

### Basic Analysis

```python
from config import get_engine
from services import AssessmentAnalyzer

# Initialize
engine = get_engine()
analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

# Analyze a property
analysis = analyzer.analyze_property("16-26005-000")

if analysis:
    print(f"Fairness Score: {analysis.fairness_score}")
    print(f"Recommendation: {analysis.recommended_action}")
    print(f"Potential Savings: ${analysis.estimated_annual_savings_dollars:,.2f}/year")
```

### Batch Analysis

```python
# Analyze multiple properties
property_ids = ["16-26005-000", "16-05881-000", "21-01960-000"]
results = analyzer.analyze_batch(property_ids)

# Find over-assessed properties
over_assessed = [r for r in results if r.fairness_score >= 60]
print(f"Found {len(over_assessed)} potentially over-assessed properties")
```

### Find Top Appeal Candidates

```python
# Find properties worth appealing
candidates = analyzer.find_appeal_candidates(min_score=60, limit=50)

# Show top candidate
if candidates:
    top = candidates[0]
    print(f"Top candidate: {top.address}")
    print(f"Potential savings: ${top.estimated_annual_savings_dollars:,.2f}/year")
```

### Save Results to Database

```python
# Analyze and save
analysis = analyzer.analyze_property("16-26005-000")
if analysis:
    analyzer.save_analysis(analysis)
```

## Performance Considerations

### Memory Management
- Batch processing uses configurable batch size (default: 100)
- Results are processed incrementally
- Suitable for analyzing entire county datasets

### Query Optimization
- Uses indexed queries for property lookups
- Spatial queries optimized with PostGIS
- Results cached where appropriate

### Logging
- Progress logged every 1000 properties in batch mode
- Detailed debug logging available
- Error tracking for failed analyses

## Error Handling

The analyzer handles several error scenarios:

1. **Property Not Found**
   - Raises `PropertyNotFoundError`
   - Property ID doesn't exist in database

2. **Insufficient Data**
   - Returns `None` from `analyze_property()`
   - No comparable properties found
   - Invalid valuation data (zeros, nulls)

3. **Database Errors**
   - Raises `DatabaseError`
   - Connection issues
   - Query failures

## Output Formats

### String Representation
Human-readable formatted output:

```python
print(analysis)  # Formatted report
```

### Dictionary/JSON
For API responses or storage:

```python
data = analysis.to_dict()
import json
print(json.dumps(data, indent=2))
```

### Database Persistence
Store for future reference:

```python
analyzer.save_analysis(analysis)
```

## Configuration

### Mill Rate
Configure the mill rate for your jurisdiction:

```python
# Benton County, AR typical rate
analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

# Different jurisdictions may vary (50-80 typical range)
analyzer = AssessmentAnalyzer(engine, default_mill_rate=72.0)
```

### Batch Size
Adjust batch size for memory constraints:

```python
# Smaller batches for limited memory
results = analyzer.analyze_batch(property_ids, batch_size=50)

# Larger batches for more RAM
results = analyzer.analyze_batch(property_ids, batch_size=200)
```

## Testing

Run the comprehensive test suite:

```bash
cd /c/taxdown
python examples/test_assessment_analyzer.py
```

Run the simple demo:

```bash
python examples/simple_analysis_demo.py
```

## API Integration

The Assessment Analyzer is designed for easy integration into REST APIs:

```python
from flask import Flask, jsonify
from services import AssessmentAnalyzer

app = Flask(__name__)
analyzer = AssessmentAnalyzer(engine)

@app.route('/api/properties/<property_id>/analysis')
def analyze_property_api(property_id):
    analysis = analyzer.analyze_property(property_id)
    if analysis:
        return jsonify(analysis.to_dict())
    else:
        return jsonify({"error": "Could not analyze property"}), 404
```

## Future Enhancements

Potential improvements for future versions:

1. **Historical Tracking**
   - Track fairness scores over time
   - Identify trending over-assessment
   - Alert on significant changes

2. **Machine Learning**
   - Predict appeal success probability
   - Optimize comparable property matching
   - Personalized recommendation thresholds

3. **District-Specific Mill Rates**
   - Lookup actual mill rates by tax district
   - Handle multiple overlapping districts
   - Cache mill rates for performance

4. **Subdivision Analysis**
   - Aggregate statistics by subdivision
   - Identify systematically over-assessed areas
   - Bulk appeal opportunities

5. **Export Capabilities**
   - PDF appeal reports
   - CSV batch exports
   - Integration with appeal filing systems

## Support

For issues or questions:
- Check logs for detailed error messages
- Review test cases in `examples/` directory
- Ensure database connection is properly configured
- Verify property has valid assessment data

## License

Copyright 2025 Taxdown. All rights reserved.
