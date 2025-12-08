"""
Examples of using the SavingsEstimator service.

This file demonstrates various use cases for calculating potential tax savings
from property tax appeals in Arkansas.
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.savings_estimator import SavingsEstimator


def example_1_basic_usage():
    """Example 1: Basic savings calculation."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Savings Calculation")
    print("=" * 70)

    # Initialize with default mill rate (65.0 mills typical for Benton County)
    estimator = SavingsEstimator(default_mill_rate=65.0)

    # Calculate savings from reducing assessed value
    savings = estimator.estimate_savings(
        current_assessed_cents=5000000,  # $50,000 current assessment
        target_assessed_cents=4500000,   # $45,000 target assessment
        mill_rate=65.0
    )

    print(savings)
    print()


def example_2_fairness_ratio():
    """Example 2: Calculate savings based on fairness ratio from comparables."""
    print("=" * 70)
    print("EXAMPLE 2: Fairness Ratio Calculation")
    print("=" * 70)
    print("Scenario: Property is assessed at 25% of market value")
    print("          but comparables show it should be at 20% (statutory ratio)")
    print()

    estimator = SavingsEstimator(default_mill_rate=68.5)

    # Property market value: $350,000
    # Currently assessed at: $87,500 (25% of market value)
    # Should be assessed at: 20% (statutory ratio)
    savings = estimator.estimate_from_fairness(
        current_assessed_cents=8750000,   # $87,500 (current 25%)
        current_total_cents=35000000,     # $350,000 (market value)
        target_ratio=0.20                  # Target 20% (statutory)
    )

    print(savings)
    print()


def example_3_determine_if_worthwhile():
    """Example 3: Determine if an appeal is worth pursuing."""
    print("=" * 70)
    print("EXAMPLE 3: Is the Appeal Worthwhile?")
    print("=" * 70)

    estimator = SavingsEstimator()

    # Case A: Large overassessment - definitely worth appealing
    print("Case A: Large Overassessment")
    print("-" * 70)
    savings_large = estimator.estimate_savings(
        current_assessed_cents=10000000,  # $100,000
        target_assessed_cents=8000000,    # $80,000 (20% reduction)
        mill_rate=70.0
    )
    print(f"Annual Savings: ${savings_large.annual_savings_dollars:,.2f}")
    print(f"5-Year Savings: ${savings_large.five_year_savings_dollars:,.2f}")
    print(f"Worth Appealing: {savings_large.is_worthwhile}")
    print()

    # Case B: Small overassessment - probably not worth the effort
    print("Case B: Small Overassessment")
    print("-" * 70)
    savings_small = estimator.estimate_savings(
        current_assessed_cents=5100000,   # $51,000
        target_assessed_cents=5000000,    # $50,000 (2% reduction)
        mill_rate=65.0
    )
    print(f"Annual Savings: ${savings_small.annual_savings_dollars:,.2f}")
    print(f"5-Year Savings: ${savings_small.five_year_savings_dollars:,.2f}")
    print(f"Worth Appealing: {savings_small.is_worthwhile}")
    print(f"Note: Annual savings < $100 may not justify appeal effort")
    print()


def example_4_compare_mill_rates():
    """Example 4: Compare savings across different mill rates."""
    print("=" * 70)
    print("EXAMPLE 4: Impact of Different Mill Rates")
    print("=" * 70)
    print("Same assessed value reduction, different mill rates")
    print()

    estimator = SavingsEstimator()

    # Same reduction amount
    current = 7500000   # $75,000
    target = 6000000    # $60,000
    reduction = (current - target) / 100  # $15,000

    print(f"Assessed Value Reduction: ${reduction:,.2f}")
    print("-" * 70)

    for mill_rate in [50.0, 60.0, 70.0, 80.0]:
        savings = estimator.estimate_savings(
            current_assessed_cents=current,
            target_assessed_cents=target,
            mill_rate=mill_rate
        )
        print(f"Mill Rate {mill_rate:5.1f}: "
              f"Annual = ${savings.annual_savings_dollars:>8.2f}, "
              f"5-Year = ${savings.five_year_savings_dollars:>9.2f}")

    print()


def example_5_realistic_scenario():
    """Example 5: Realistic property tax appeal scenario."""
    print("=" * 70)
    print("EXAMPLE 5: Realistic Property Tax Appeal Scenario")
    print("=" * 70)

    estimator = SavingsEstimator(default_mill_rate=67.5)

    # Realistic scenario from Benton County
    print("Property Details:")
    print("  Location: Rogers, AR (Benton County)")
    print("  Market Value: $425,000")
    print("  Current Assessment: $93,500 (22% of market value)")
    print("  Comparables show: Should be assessed at 20%")
    print("  Mill Rate: 67.5")
    print()

    savings = estimator.estimate_from_fairness(
        current_assessed_cents=9350000,   # $93,500 (22%)
        current_total_cents=42500000,     # $425,000
        target_ratio=0.20                  # Should be 20%
    )

    print("Appeal Analysis:")
    print("-" * 70)
    print(f"Current Assessment:    ${savings.current_assessed_dollars:>12,.2f}")
    print(f"Target Assessment:     ${savings.target_assessed_dollars:>12,.2f}")
    print(f"Reduction:             ${savings.reduction_dollars:>12,.2f} "
          f"({savings.reduction_percent:.1f}%)")
    print()
    print(f"Current Annual Tax:    ${savings.current_annual_tax_cents / 100:>12,.2f}")
    print(f"Target Annual Tax:     ${savings.target_annual_tax_cents / 100:>12,.2f}")
    print(f"Annual Savings:        ${savings.annual_savings_dollars:>12,.2f}")
    print()
    print(f"5-Year Savings:        ${savings.five_year_savings_dollars:>12,.2f}")
    print()
    print(f"Recommendation: {'APPEAL' if savings.is_worthwhile else 'DO NOT APPEAL'}")
    print()


def example_6_json_output():
    """Example 6: Export savings estimate as JSON."""
    print("=" * 70)
    print("EXAMPLE 6: JSON Output for API Integration")
    print("=" * 70)

    import json

    estimator = SavingsEstimator(default_mill_rate=65.0)

    savings = estimator.estimate_savings(
        current_assessed_cents=8000000,   # $80,000
        target_assessed_cents=7000000,    # $70,000
    )

    # Convert to dictionary for JSON serialization
    savings_dict = savings.to_dict()

    print("JSON Output:")
    print("-" * 70)
    print(json.dumps(savings_dict, indent=2))
    print()


def example_7_batch_analysis():
    """Example 7: Batch analysis of multiple properties."""
    print("=" * 70)
    print("EXAMPLE 7: Batch Analysis of Multiple Properties")
    print("=" * 70)

    estimator = SavingsEstimator(default_mill_rate=65.0)

    # Multiple properties to analyze
    properties = [
        {"id": "PROP-001", "current": 5000000, "target": 4500000},
        {"id": "PROP-002", "current": 7500000, "target": 6800000},
        {"id": "PROP-003", "current": 10000000, "target": 8500000},
        {"id": "PROP-004", "current": 3000000, "target": 2950000},  # Small
    ]

    print(f"{'Property':<12} {'Current':<12} {'Target':<12} "
          f"{'Annual $':<12} {'5-Year $':<12} {'Appeal?'}")
    print("-" * 80)

    for prop in properties:
        savings = estimator.estimate_savings(
            current_assessed_cents=prop["current"],
            target_assessed_cents=prop["target"]
        )

        print(f"{prop['id']:<12} "
              f"${prop['current']/100:>10,.0f} "
              f"${prop['target']/100:>10,.0f} "
              f"${savings.annual_savings_dollars:>10,.2f} "
              f"${savings.five_year_savings_dollars:>10,.2f} "
              f"{'YES' if savings.is_worthwhile else 'NO':>6}")

    print()


if __name__ == "__main__":
    print("\n")
    print("#" * 70)
    print("# SAVINGS ESTIMATOR USAGE EXAMPLES")
    print("#" * 70)
    print("\n")

    example_1_basic_usage()
    example_2_fairness_ratio()
    example_3_determine_if_worthwhile()
    example_4_compare_mill_rates()
    example_5_realistic_scenario()
    example_6_json_output()
    example_7_batch_analysis()

    print("#" * 70)
    print("# END OF EXAMPLES")
    print("#" * 70)
