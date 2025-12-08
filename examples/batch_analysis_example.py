#!/usr/bin/env python3
"""
Example: Using the analyze_county.py script programmatically

This demonstrates how to use the batch analyzer components directly
in your own scripts instead of via the CLI.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_engine
from src.scripts.analyze_county import (
    fetch_property_ids,
    analyze_properties,
    save_results_to_csv,
    print_summary_report,
    AnalysisStats,
    setup_logging
)
from src.services.assessment_analyzer import AssessmentAnalyzer


def main():
    """Run a custom batch analysis."""
    print("=" * 70)
    print("CUSTOM BATCH ANALYSIS EXAMPLE")
    print("=" * 70)
    print()

    # Setup
    logger = setup_logging(verbose=True)
    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    # Fetch properties from a specific subdivision
    print("Fetching properties from AVONDALE SUB 1...")
    property_ids = fetch_property_ids(
        engine,
        limit=20,  # Just 20 for this example
        subdivision="AVONDALE SUB 1"
    )

    print(f"Found {len(property_ids)} properties to analyze")
    print()

    # Analyze properties
    print("Starting analysis...")
    stats = analyze_properties(
        analyzer=analyzer,
        property_ids=property_ids,
        min_score=40,  # Lower threshold for example
        min_savings=100,  # $100 minimum
        verbose=True,
        save_db=False,  # Don't save to DB in this example
        logger=logger
    )

    # Save to CSV
    if stats.results:
        output_file = "example_analysis_results.csv"
        save_results_to_csv(stats.results, output_file)
        print()
        print(f"Saved {len(stats.results)} results to {output_file}")

    # Print summary
    print_summary_report(stats, output_file if stats.results else None)

    # Custom analysis of results
    if stats.results:
        print()
        print("=" * 70)
        print("CUSTOM ANALYSIS")
        print("=" * 70)

        # Group by appeal strength
        strong_cases = [r for r in stats.results if r.appeal_strength == "STRONG"]
        moderate_cases = [r for r in stats.results if r.appeal_strength == "MODERATE"]
        weak_cases = [r for r in stats.results if r.recommended_action == "MONITOR"]

        print(f"\nBreakdown by Appeal Strength:")
        print(f"  Strong: {len(strong_cases)}")
        print(f"  Moderate: {len(moderate_cases)}")
        print(f"  Weak/Monitor: {len(weak_cases)}")

        # Show confidence distribution
        if stats.results:
            avg_confidence = sum(r.confidence for r in stats.results) / len(stats.results)
            print(f"\nAverage Confidence: {avg_confidence:.1f}/100")

        # Show top 3 by savings
        top_3 = sorted(stats.results, key=lambda x: x.estimated_annual_savings_cents, reverse=True)[:3]
        if top_3:
            print(f"\nTop 3 by Potential Savings:")
            for i, result in enumerate(top_3, 1):
                print(f"\n{i}. {result.address}")
                print(f"   Fairness Score: {result.fairness_score}/100")
                print(f"   Annual Savings: ${result.estimated_annual_savings_dollars:,.2f}")
                print(f"   Confidence: {result.confidence}/100")
                print(f"   Comparables Used: {result.comparable_count}")

    print()
    print("=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
