# Fairness Scorer Service - Sales Comparison Approach

A statistical service for evaluating the fairness of property tax assessments by comparing a subject property's **TOTAL MARKET VALUE** to comparable properties.

## Overview

The Fairness Scorer calculates a 0-100 score indicating how fairly a property is assessed relative to similar properties. The score is based on comparing market values using the sales comparison approach.

**KEY INSIGHT:** Since Benton County applies a uniform 20% assessment ratio to ALL properties, comparing assessment ratios is meaningless (they're all ~20%). Instead, we compare **total market values** among comparable properties.

## Fairness Score Scale (NEW - INVERTED)

**Higher score = FAIRER (less likely over-assessed)**

| Score Range | Category | Description | Recommended Action |
|-------------|----------|-------------|-------------------|
| 70-100 | Fairly assessed | At or below comparable median | No action needed |
| 50-69 | Slightly over-assessed | Somewhat above comparables | Monitor for trends |
| 30-49 | Moderately over-assessed | Significantly above comparables | Appeal candidate |
| 0-29 | Significantly over-assessed | Greatly above comparables | Strong appeal case |

## Statistical Methodology

### Calculation Process

1. **Input Data**
   - Subject property's total market value (in cents)
   - List of comparable properties' total market values (in cents)

2. **Statistical Analysis**
   - Calculate median value from comparables
   - Calculate standard deviation of comparable values
   - Compute z-score: `(subject_value - median_value) / std_deviation`

3. **Score Conversion**
   - Subject at/below median → High fairness score (70-100)
   - Subject above median → Lower fairness score
   - Significantly above median → Low score (0-29, appeal candidate)
   - Formula: Inverted from z-score so higher = fairer

4. **Confidence Calculation**
   - Based on sample size (more comparables = higher confidence)
   - Based on consistency (lower std deviation = higher confidence)
   - Capped at 50 if fewer than 3 comparables

## Usage

### Basic Usage

```python
from src.services.fairness_scorer import FairnessScorer

scorer = FairnessScorer(mill_rate=65.0)  # Benton County mill rate

# Your property's total market value in cents
subject_value = 35000000  # $350,000

# Comparable properties' total market values in cents
comparable_values = [28000000, 30000000, 32000000, 34000000, 36000000]

# Calculate fairness
result = scorer.calculate_fairness_score(subject_value, comparable_values)

print(f"Fairness Score: {result.fairness_score}/100 (higher = fairer)")
print(f"Interpretation: {result.interpretation}")
print(f"Recommendation: {result.get_recommendation()}")
if result.potential_annual_savings_cents > 0:
    print(f"Potential Savings: ${result.potential_annual_savings_cents / 100:,.2f}/year")
```

### Batch Processing

```python
properties = [
    {
        'subject_value': 30000000,  # $300k
        'comparable_values': [28000000, 29000000, 30000000, 31000000, 32000000]
    },
    {
        'subject_value': 45000000,  # $450k - above comparables
        'comparable_values': [28000000, 29000000, 30000000, 31000000, 32000000]
    }
]

for prop in properties:
    result = scorer.calculate_fairness_score(
        prop['subject_value'],
        prop['comparable_values']
    )
    print(f"Score: {result.fairness_score}, Status: {result.interpretation}")
```

### Result Object

The `FairnessResult` dataclass contains:

```python
@dataclass
class FairnessResult:
    fairness_score: int          # 0-100 (higher = FAIRER)
    subject_value: int           # Property's total market value in cents
    median_value: int            # Median of comparable values in cents
    mean_value: int              # Mean of comparable values in cents
    std_deviation: int           # Standard deviation in cents
    z_score: float               # Statistical z-score (positive = above median)
    percentile: float            # Percentile rank (0-100)
    interpretation: str          # "FAIR", "OVER_ASSESSED"
    confidence: int              # Confidence level (0-100)
    comparable_count: int        # Number of comparables used
    over_assessment_cents: int   # Amount over median (0 if at/below)
    potential_annual_savings_cents: int  # Estimated annual tax savings
```

### Methods

#### `to_dict()`
Convert result to dictionary for JSON serialization:

```python
result_dict = result.to_dict()
# Returns: {'fairness_score': 75, 'subject_value_cents': 30000000, ...}
```

#### `get_recommendation()`
Get action recommendation based on score:

```python
recommendation = result.get_recommendation()
# Returns: "NO_ACTION_NEEDED", "MONITOR", "APPEAL_RECOMMENDED", or "STRONG_APPEAL_RECOMMENDED"
```

## Integration with AssessmentAnalyzer

The FairnessScorer is used by the AssessmentAnalyzer which:
1. Finds comparable properties using ComparableService
2. Extracts their total market values
3. Passes values to FairnessScorer
4. Combines results with savings estimates

```python
from src.services import AssessmentAnalyzer

analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)
analysis = analyzer.analyze_property("16-26005-000")

if analysis:
    print(f"Fairness: {analysis.fairness_score}/100")
    print(f"Median Comparable Value: ${analysis.median_comparable_value_cents / 100:,.2f}")
    print(f"Recommendation: {analysis.recommended_action}")
```

## Edge Cases

- **No comparables**: Returns `None` - cannot assess without comparables
- **Zero subject value**: Returns `None` - invalid property data
- **All invalid comparables**: Returns `None` - need valid data
- **Low confidence**: Score still calculated but confidence < 50 indicates unreliable result

## Testing

```python
# Property at median = high fairness score (fair)
result = scorer.calculate_fairness_score(
    subject_value=30000000,
    comparable_values=[28000000, 29000000, 30000000, 31000000, 32000000]
)
assert result.fairness_score >= 70  # At median = fair

# Property above median = lower fairness score
result = scorer.calculate_fairness_score(
    subject_value=45000000,  # 50% above median
    comparable_values=[28000000, 29000000, 30000000, 31000000, 32000000]
)
assert result.fairness_score < 70  # Above median = over-assessed
assert result.over_assessment_cents > 0
assert result.potential_annual_savings_cents > 0
```
