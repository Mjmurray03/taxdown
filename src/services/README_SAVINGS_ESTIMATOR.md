# Savings Estimator Service

## Overview

The `SavingsEstimator` service calculates potential tax savings if a property tax appeal is successful in Arkansas. It handles Arkansas-specific tax calculation rules and provides both simple and fairness-based calculation methods.

## Arkansas Tax Calculation Context

- **Assessed Value** = 20% of market value (statutory ratio)
- **Tax** = assessed_value × (mill_rate / 1000)
- **Mill Rate** = dollars per $1,000 of assessed value
- **Typical Mill Rates** in Benton County: 50-80 mills (default: 65.0)

## Installation

The service is part of the `src.services` package:

```python
from src.services import SavingsEstimator, SavingsEstimate
```

## Quick Start

### Basic Usage

```python
from src.services import SavingsEstimator

# Initialize with default mill rate
estimator = SavingsEstimator(default_mill_rate=65.0)

# Calculate savings from reducing assessed value
savings = estimator.estimate_savings(
    current_assessed_cents=5000000,  # $50,000
    target_assessed_cents=4500000,   # $45,000
    mill_rate=65.0
)

print(f"Annual Savings: ${savings.annual_savings_dollars:,.2f}")
print(f"5-Year Savings: ${savings.five_year_savings_dollars:,.2f}")
print(f"Worth Appealing: {savings.is_worthwhile}")
```

### Fairness-Based Calculation

```python
# Calculate savings based on target fairness ratio
savings = estimator.estimate_from_fairness(
    current_assessed_cents=6250000,   # $62,500 (25%)
    current_total_cents=25000000,     # $250,000 market value
    target_ratio=0.20                  # Should be 20% (statutory)
)
```

## API Reference

### SavingsEstimator Class

#### Constructor

```python
SavingsEstimator(default_mill_rate: float = 65.0)
```

**Parameters:**
- `default_mill_rate`: Default mill rate to use when none is specified (default: 65.0)

**Raises:**
- `ValueError`: If default_mill_rate is not positive

#### Methods

##### estimate_savings()

Calculate potential savings from reducing assessed value.

```python
estimate_savings(
    current_assessed_cents: int,
    target_assessed_cents: int,
    mill_rate: Optional[float] = None
) -> SavingsEstimate
```

**Parameters:**
- `current_assessed_cents`: Current assessed value in cents
- `target_assessed_cents`: Proposed/target assessed value in cents
- `mill_rate`: Mill rate for the property's district (uses default if None)

**Returns:**
- `SavingsEstimate`: Object containing all calculated savings projections

**Raises:**
- `ValueError`: If inputs are negative or mill_rate is non-positive

##### estimate_from_fairness()

Calculate savings based on a target fairness ratio from comparable sales.

```python
estimate_from_fairness(
    current_assessed_cents: int,
    current_total_cents: int,
    target_ratio: float,
    mill_rate: Optional[float] = None
) -> SavingsEstimate
```

**Parameters:**
- `current_assessed_cents`: Current assessed value in cents
- `current_total_cents`: Current total/market value in cents
- `target_ratio`: Target ratio (assessed/total) that would be "fair" (e.g., 0.20 for 20%)
- `mill_rate`: Mill rate for the property's district (uses default if None)

**Returns:**
- `SavingsEstimate`: Object containing all calculated savings projections

**Raises:**
- `ValueError`: If inputs are invalid

##### get_mill_rate_for_property()

Get the mill rate for a specific property based on its tax district.

```python
get_mill_rate_for_property(property_id: str) -> float
```

**Note:** This is currently a stub that returns the default mill rate. Future enhancement will implement district-based mill rate lookup.

### SavingsEstimate Dataclass

Contains all calculated savings projections.

#### Fields (all in cents)

- `current_assessed_cents`: Current assessed value
- `target_assessed_cents`: Target assessed value
- `reduction_cents`: Reduction amount (current - target)
- `reduction_percent`: Reduction as percentage
- `current_annual_tax_cents`: Current annual tax
- `target_annual_tax_cents`: Target annual tax
- `annual_savings_cents`: Annual tax savings
- `five_year_savings_cents`: 5-year projected savings
- `mill_rate_used`: Mill rate used in calculation

#### Properties (convenient dollar conversions)

- `annual_savings_dollars`: Annual savings in dollars
- `five_year_savings_dollars`: 5-year savings in dollars
- `reduction_dollars`: Reduction in dollars
- `current_assessed_dollars`: Current assessed in dollars
- `target_assessed_dollars`: Target assessed in dollars
- `is_worthwhile`: Boolean - True if annual savings >= $100

#### Methods

- `to_dict()`: Convert to dictionary with dollar values
- `__str__()`: Human-readable string representation

## Usage Examples

### Example 1: Standard Calculation

```python
estimator = SavingsEstimator(default_mill_rate=65.0)

savings = estimator.estimate_savings(
    current_assessed_cents=5000000,  # $50,000
    target_assessed_cents=4500000,   # $45,000
)

# Outputs:
# Annual Savings: $325.00
# 5-Year Savings: $1,625.00
```

### Example 2: Fairness Ratio

```python
# Property assessed at 25% but should be 20%
savings = estimator.estimate_from_fairness(
    current_assessed_cents=8750000,   # $87,500 (25%)
    current_total_cents=35000000,     # $350,000 market
    target_ratio=0.20                  # Statutory 20%
)

# Automatically calculates target as $350,000 × 0.20 = $70,000
```

### Example 3: Check if Appeal is Worthwhile

```python
savings = estimator.estimate_savings(
    current_assessed_cents=5100000,   # $51,000
    target_assessed_cents=5000000,    # $50,000
)

if savings.is_worthwhile:
    print(f"Appeal recommended: ${savings.annual_savings_dollars:.2f}/year")
else:
    print("Savings too small to justify appeal")
```

### Example 4: JSON Output for API

```python
import json

savings = estimator.estimate_savings(
    current_assessed_cents=8000000,
    target_assessed_cents=7000000
)

# Convert to JSON
json_output = json.dumps(savings.to_dict(), indent=2)
```

### Example 5: Batch Analysis

```python
properties = [
    {"id": "PROP-001", "current": 5000000, "target": 4500000},
    {"id": "PROP-002", "current": 7500000, "target": 6800000},
    {"id": "PROP-003", "current": 10000000, "target": 8500000},
]

for prop in properties:
    savings = estimator.estimate_savings(
        current_assessed_cents=prop["current"],
        target_assessed_cents=prop["target"]
    )

    print(f"{prop['id']}: ${savings.annual_savings_dollars:.2f}/year "
          f"({'APPEAL' if savings.is_worthwhile else 'SKIP'})")
```

## Calculation Formulas

### Tax Calculation

```
annual_tax = assessed_value × (mill_rate / 1000)
```

Example:
- Assessed value: $50,000
- Mill rate: 65.0
- Tax = $50,000 × (65 / 1000) = $50,000 × 0.065 = $3,250

### Savings Calculation

```
reduction = current_assessed - target_assessed
current_tax = current_assessed × (mill_rate / 1000)
target_tax = target_assessed × (mill_rate / 1000)
annual_savings = current_tax - target_tax
five_year_savings = annual_savings × 5
```

### Fairness Ratio Calculation

```
target_assessed = current_total × target_ratio
```

Then use standard savings calculation.

## Safety Checks

The service includes several safety checks:

1. **No Savings Case**: If target >= current, returns zero savings
2. **Worthwhile Threshold**: Flags appeals with annual savings < $100 as not worthwhile
3. **Validation**:
   - Mill rate must be positive
   - Assessed values must be non-negative
   - Target ratio must be between 0 and 1
   - Total value cannot be zero

## Future Enhancements

The `get_mill_rate_for_property()` method is currently a stub. Future implementation will:

1. Query property location from database
2. Determine applicable tax district(s)
3. Sum mill rates from all districts
4. Cache results for performance

## Testing

Comprehensive test coverage (34 tests, 100% pass rate):

```bash
pytest tests/test_savings_estimator.py -v
```

Test categories:
- Initialization and configuration
- Standard savings calculations
- Fairness ratio calculations
- Edge cases (zero values, no savings)
- Error handling and validation
- Different mill rates
- Precision with cent-based calculations
- Real-world scenarios

## Full Example

See `examples/savings_estimator_usage.py` for complete usage examples.

## Notes

- All monetary values are stored in cents for precision
- Mill rates are per $1,000 of assessed value
- Arkansas statutory assessment ratio is 20% of market value
- Default mill rate (65.0) is typical for Benton County
- 5-year projection assumes no reassessment during that period

## Author

Part of the Taxdown Assessment Analyzer project.
