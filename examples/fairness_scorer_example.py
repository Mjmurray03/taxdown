"""
Example usage of the FairnessScorer service

This demonstrates how to use the fairness scorer to evaluate
property tax assessment fairness using the SALES COMPARISON APPROACH.

NEW SCORING (inverted from original):
- Higher score = FAIRER (less likely over-assessed)
- Lower score = more over-assessed (appeal candidate)

Score interpretation:
- 70-100: Fairly assessed (at or below comparable median)
- 50-69: Slightly over-assessed
- 30-49: Moderately over-assessed (appeal candidate)
- 0-29: Significantly over-assessed (strong appeal candidate)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.fairness_scorer import FairnessScorer


def main():
    print("Fairness Scorer Examples - Sales Comparison Approach")
    print("=" * 80)

    scorer = FairnessScorer(mill_rate=65.0)  # Benton County mill rate

    # Example 1: Single property evaluation
    print("\nExample 1: Evaluating a Single Property")
    print("-" * 80)

    # Property has total market value of $350,000
    subject_value = 35000000  # cents

    # Comparable properties have these market values
    comparable_values = [
        28000000, 29000000, 30000000, 31000000, 32000000,  # $280k-$320k
        33000000, 34000000, 35000000, 36000000, 37000000   # $330k-$370k
    ]

    result = scorer.calculate_fairness_score(subject_value, comparable_values)

    print(f"\nYour Property Market Value: ${result.subject_value / 100:,.2f}")
    print(f"Median Comparable Value: ${result.median_value / 100:,.2f}")
    print(f"\nFairness Score: {result.fairness_score}/100 (higher = fairer)")
    print(f"Interpretation: {result.interpretation}")
    print(f"Recommendation: {result.get_recommendation()}")
    print(f"\nStatistical Details:")
    print(f"  - Z-Score: {result.z_score:.2f}")
    print(f"  - Percentile: {result.percentile:.1f}th")
    print(f"  - Standard Deviation: ${result.std_deviation / 100:,.2f}")
    print(f"  - Confidence: {result.confidence}/100")
    print(f"  - Comparables Used: {result.comparable_count}")
    if result.over_assessment_cents > 0:
        print(f"  - Potential Over-assessment: ${result.over_assessment_cents / 100:,.2f}")
        print(f"  - Potential Annual Savings: ${result.potential_annual_savings_cents / 100:,.2f}")

    # Example 2: Comparing multiple properties
    print("\n\nExample 2: Batch Analysis of Multiple Properties")
    print("-" * 80)

    properties = [
        {
            'name': '123 Oak Street',
            'subject_value': 30000000,  # $300k - at median
            'comparable_values': [28000000, 29000000, 30000000, 31000000, 32000000]
        },
        {
            'name': '456 Maple Avenue',
            'subject_value': 45000000,  # $450k - significantly above median
            'comparable_values': [28000000, 29000000, 30000000, 31000000, 32000000]
        },
        {
            'name': '789 Pine Road',
            'subject_value': 25000000,  # $250k - below median (great for taxpayer!)
            'comparable_values': [28000000, 29000000, 30000000, 31000000, 32000000]
        }
    ]

    for prop in properties:
        result = scorer.calculate_fairness_score(
            prop['subject_value'],
            prop['comparable_values']
        )

        print(f"\n{prop['name']}:")
        print(f"  Market Value: ${result.subject_value / 100:,.2f} (median: ${result.median_value / 100:,.2f})")
        print(f"  Fairness Score: {result.fairness_score}/100")
        print(f"  Status: {result.interpretation}")
        print(f"  Action: {result.get_recommendation()}")
        if result.potential_annual_savings_cents > 0:
            print(f"  Potential Savings: ${result.potential_annual_savings_cents / 100:,.2f}/year")

    # Example 3: Understanding score ranges (NEW INVERTED SCORING)
    print("\n\nExample 3: Understanding Fairness Score Ranges")
    print("-" * 80)
    print("\nNEW SCORING: Higher score = FAIRER (less over-assessed)")

    score_ranges = [
        (70, 100, "Fairly assessed", "At or below comparable median - no action needed"),
        (50, 69, "Slightly over-assessed", "Somewhat above comparables - monitor"),
        (30, 49, "Moderately over-assessed", "Appeal candidate - worth reviewing"),
        (0, 29, "Significantly over-assessed", "Strong appeal candidate")
    ]

    print("\nScore Range Interpretations:")
    for min_score, max_score, category, description in score_ranges:
        print(f"  {min_score:3d}-{max_score:3d}: {category:25s} - {description}")

    # Example 4: Export to dictionary for API/database
    print("\n\nExample 4: Export Result as Dictionary")
    print("-" * 80)

    result_dict = result.to_dict()
    print("\nResult dictionary keys:")
    for key, value in result_dict.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
