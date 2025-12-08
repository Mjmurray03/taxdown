"""
Example usage of the FairnessScorer service

This demonstrates how to use the fairness scorer to evaluate
property tax assessment fairness.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.fairness_scorer import FairnessScorer


def main():
    print("Fairness Scorer Examples")
    print("=" * 80)

    scorer = FairnessScorer()

    # Example 1: Single property evaluation
    print("\nExample 1: Evaluating a Single Property")
    print("-" * 80)

    # Property has assessed/total ratio of 0.95
    subject_ratio = 0.95

    # Comparable properties have these ratios
    comparable_ratios = [
        0.78, 0.81, 0.83, 0.85, 0.87, 0.88, 0.90, 0.91, 0.93, 0.94
    ]

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)

    print(f"\nYour Property Assessment Ratio: {result.subject_ratio:.2%}")
    print(f"Median Comparable Ratio: {result.median_ratio:.2%}")
    print(f"\nFairness Score: {result.fairness_score}/100")
    print(f"Interpretation: {result.interpretation}")
    print(f"Recommendation: {result.get_recommendation()}")
    print(f"\nStatistical Details:")
    print(f"  - Z-Score: {result.z_score:.2f}")
    print(f"  - Percentile: {result.percentile:.1f}th")
    print(f"  - Standard Deviation: {result.std_deviation:.4f}")
    print(f"  - Confidence: {result.confidence}/100")
    print(f"  - Comparables Used: {result.comparable_count}")

    # Example 2: Comparing multiple properties
    print("\n\nExample 2: Batch Analysis of Multiple Properties")
    print("-" * 80)

    properties = [
        {
            'name': '123 Oak Street',
            'subject_ratio': 0.85,
            'comparable_ratios': [0.80, 0.82, 0.83, 0.84, 0.86, 0.87, 0.88]
        },
        {
            'name': '456 Maple Avenue',
            'subject_ratio': 1.05,
            'comparable_ratios': [0.80, 0.82, 0.83, 0.84, 0.86, 0.87, 0.88]
        },
        {
            'name': '789 Pine Road',
            'subject_ratio': 0.72,
            'comparable_ratios': [0.80, 0.82, 0.83, 0.84, 0.86, 0.87, 0.88]
        }
    ]

    for prop in properties:
        result = scorer.calculate_fairness_score(
            prop['subject_ratio'],
            prop['comparable_ratios']
        )

        print(f"\n{prop['name']}:")
        print(f"  Ratio: {result.subject_ratio:.2%} (vs median {result.median_ratio:.2%})")
        print(f"  Fairness Score: {result.fairness_score}/100")
        print(f"  Status: {result.interpretation}")
        print(f"  Action: {result.get_recommendation()}")

    # Example 3: Understanding score ranges
    print("\n\nExample 3: Understanding Fairness Score Ranges")
    print("-" * 80)

    score_ranges = [
        (0, 20, "Under-assessed", "Paying less than fair share"),
        (21, 40, "Fairly assessed", "No action needed"),
        (41, 60, "Slightly over-assessed", "Monitor situation"),
        (61, 80, "Significantly over-assessed", "Appeal recommended"),
        (81, 100, "Severely over-assessed", "Strong appeal case")
    ]

    print("\nScore Range Interpretations:")
    for min_score, max_score, category, description in score_ranges:
        print(f"  {min_score:3d}-{max_score:3d}: {category:25s} - {description}")

    # Example 4: Export to dictionary for API/database
    print("\n\nExample 4: Export Result as Dictionary")
    print("-" * 80)

    result = scorer.calculate_fairness_score(0.95, [0.80, 0.82, 0.85, 0.88, 0.90])
    result_dict = result.to_dict()

    print("\nJSON-serializable result:")
    import json
    print(json.dumps(result_dict, indent=2))


if __name__ == "__main__":
    main()
