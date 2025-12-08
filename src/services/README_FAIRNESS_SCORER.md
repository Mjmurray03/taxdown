# Fairness Scorer Service

A statistical service for evaluating the fairness of property tax assessments by comparing a subject property's assessment ratio to comparable properties.

## Overview

The Fairness Scorer calculates a 0-100 score indicating how fairly a property is assessed relative to similar properties. The score is based on statistical analysis using z-scores and standard deviations.

## Fairness Score Scale

| Score Range | Category | Description | Recommended Action |
|-------------|----------|-------------|-------------------|
| 0-20 | Under-assessed | Paying less than fair share | No action (favorable) |
| 21-40 | Fairly assessed | Assessment is fair and equitable | No action needed |
| 41-60 | Slightly over-assessed | Moderately higher than comparables | Monitor for trends |
| 61-80 | Significantly over-assessed | Substantially higher than fair | Appeal recommended |
| 81-100 | Severely over-assessed | Extreme disparity vs comparables | Strong appeal case |

## Statistical Methodology

### Calculation Process

1. **Input Data**
   - Subject property's assessment ratio (assessed value / total value)
   - List of comparable properties' assessment ratios
   - Optional subdivision median (for future enhancements)

2. **Statistical Analysis**
   - Calculate median ratio from comparables
   - Calculate standard deviation of comparable ratios
   - Compute z-score: `(subject_ratio - median_ratio) / std_deviation`

3. **Score Conversion**
   - Z-score of 0 (at median) → Fairness score of 30 (fair)
   - Z-score of +2 (2 std devs above) → Fairness score of 80 (over-assessed)
   - Z-score of -2 (2 std devs below) → Fairness score of 0 (under-assessed)
   - Formula: `fairness_score = 30 + (z_score * 25)`
   - Capped at 0 and 100

4. **Confidence Calculation**
   - Based on sample size (more comparables = higher confidence)
   - Based on consistency (lower std deviation = higher confidence)
   - Formula: `(comp_count/20 * 50) + ((1 - coefficient_of_variation/0.5) * 50)`
   - Capped at 50 if fewer than 3 comparables

## Usage

### Basic Usage

```python
from src.services.fairness_scorer import FairnessScorer

scorer = FairnessScorer()

# Your property's ratio
subject_ratio = 0.95

# Comparable properties' ratios
comparable_ratios = [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]

# Calculate fairness
result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)

print(f"Fairness Score: {result.fairness_score}")
print(f"Interpretation: {result.interpretation}")
print(f"Recommendation: {result.get_recommendation()}")
```

### Batch Processing

```python
properties = [
    {
        'subject_ratio': 0.85,
        'comparable_ratios': [0.80, 0.82, 0.83, 0.84, 0.86]
    },
    {
        'subject_ratio': 1.05,
        'comparable_ratios': [0.80, 0.82, 0.83, 0.84, 0.86]
    }
]

results = scorer.calculate_batch(properties)

for result in results:
    print(f"Score: {result.fairness_score}, Status: {result.interpretation}")
```

### Result Object

The `FairnessResult` dataclass contains:

```python
@dataclass
class FairnessResult:
    fairness_score: int          # 0-100 fairness score
    subject_ratio: float         # Property's assessment ratio
    median_ratio: float          # Median of comparable ratios
    std_deviation: float         # Standard deviation of comparables
    z_score: float              # Statistical z-score
    percentile: float           # Percentile rank (0-100)
    interpretation: str         # "FAIR", "OVER_ASSESSED", "UNDER_ASSESSED"
    confidence: int             # Confidence level (0-100)
    comparable_count: int       # Number of comparables used
```

### Methods

#### `to_dict()`
Convert result to dictionary for JSON serialization:

```python
result_dict = result.to_dict()
# Returns: {'fairness_score': 66, 'subject_ratio': 0.95, ...}
```

#### `get_recommendation()`
Get action recommendation based on score:

```python
recommendation = result.get_recommendation()
# Returns: "APPEAL_RECOMMENDED", "NO_ACTION_NEEDED", etc.
```

## Confidence Scoring

Confidence indicates how reliable the fairness score is:

- **High Confidence (70-100)**: 10+ comparables with consistent ratios
- **Medium Confidence (50-69)**: 5-9 comparables or moderate variation
- **Low Confidence (0-49)**: Fewer than 5 comparables or high variation

Confidence is automatically capped at 50 for fewer than 3 comparables.

## Edge Cases

### Handled Automatically

1. **No comparables**: Returns `None`
2. **Invalid ratios**: Filters out zero or negative values
3. **Zero standard deviation**: Uses epsilon (0.0001) to avoid division by zero
4. **Single comparable**: Uses default 10% standard deviation
5. **Fewer than 3 comparables**: Caps confidence at 50

### Example with Edge Cases

```python
# No comparables
result = scorer.calculate_fairness_score(0.90, [])
# Returns: None

# Only 2 comparables (low confidence)
result = scorer.calculate_fairness_score(0.90, [0.85, 0.88])
# Returns: FairnessResult with confidence <= 50

# Zero standard deviation (all comparables identical)
result = scorer.calculate_fairness_score(1.00, [0.90, 0.90, 0.90])
# Uses epsilon to avoid division by zero
```

## Integration Examples

### With Database Query Results

```python
# Fetch comparable properties from database
comparables = db.query(
    "SELECT assessed_value::float / total_value as ratio "
    "FROM properties WHERE ... ORDER BY similarity DESC LIMIT 10"
).all()

comparable_ratios = [comp.ratio for comp in comparables]

# Calculate fairness
result = scorer.calculate_fairness_score(
    subject_ratio=property.assessed_value / property.total_value,
    comparable_ratios=comparable_ratios
)
```

### With API Response

```python
from flask import jsonify

@app.route('/api/fairness/<property_id>')
def get_fairness(property_id):
    property = get_property(property_id)
    comparables = find_comparables(property)

    result = scorer.calculate_fairness_score(
        subject_ratio=property.assessment_ratio,
        comparable_ratios=[c.assessment_ratio for c in comparables]
    )

    if result is None:
        return jsonify({'error': 'Insufficient comparables'}), 400

    return jsonify(result.to_dict())
```

## Testing

Run the comprehensive unit tests:

```bash
python src/services/fairness_scorer.py
```

Tests include:
- Fairly assessed properties (score 21-40)
- Over-assessed properties (score 61+)
- Under-assessed properties (score 0-20)
- Edge cases (few comparables, zero std dev, no comparables)
- Batch processing
- Dictionary serialization

## Statistical Notes

### Why Z-Score?

The z-score measures how many standard deviations a value is from the mean. This provides:
- **Standardization**: Comparable across different property types and price ranges
- **Statistical rigor**: Well-understood measure with clear interpretation
- **Outlier detection**: Identifies properties significantly different from peers

### Why Median vs Mean?

Median is used instead of mean because:
- **Robust to outliers**: Extreme values don't skew the center
- **Better for skewed distributions**: Property ratios often have asymmetric distributions
- **Industry standard**: Assessment ratio studies typically use median

### Interpretation Thresholds

The score thresholds (21-40 = fair, 61-80 = appeal recommended) are based on:
- **Statistical significance**: 1-2 standard deviations from median
- **Practical impact**: Material difference in tax burden
- **Legal standards**: Common thresholds in assessment appeals

## Performance

- **Time Complexity**: O(n log n) where n is number of comparables (due to median calculation)
- **Space Complexity**: O(n) for storing comparable ratios
- **Typical Runtime**: <1ms for 10-100 comparables

## Future Enhancements

Potential improvements:
1. **Subdivision weighting**: Use subdivision median as additional reference
2. **Temporal analysis**: Track fairness score changes over time
3. **Segmentation**: Different thresholds by property type or jurisdiction
4. **Visualization**: Generate charts showing property position vs comparables
5. **Multi-year analysis**: Compare fairness across multiple tax years

## References

- International Association of Assessing Officers (IAAO) Standard on Ratio Studies
- Statistical methods for assessment equity analysis
- Property tax assessment fairness literature

## License

Part of the TaxDown property tax assessment system.
