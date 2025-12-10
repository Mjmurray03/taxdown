"""
Test script for Assessment Analyzer - demonstrates full workflow.

This script:
1. Analyzes specific properties by ID
2. Finds top appeal candidates from database
3. Demonstrates batch analysis
4. Shows different recommendation scenarios
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_engine
from src.services import AssessmentAnalyzer


def test_single_property_analysis():
    """Test analyzing a single property."""
    print("\n" + "=" * 80)
    print("TEST 1: Single Property Analysis")
    print("=" * 80)

    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    # Get a random property
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 1
        """))
        property_id = result.fetchone().parcel_id

    print(f"\nAnalyzing property: {property_id}")
    print("-" * 80)

    analysis = analyzer.analyze_property(property_id)

    if analysis:
        print(analysis)

        # Show JSON serialization
        print("\nJSON Representation:")
        print("-" * 80)
        import json
        print(json.dumps(analysis.to_dict(), indent=2))
    else:
        print("Could not analyze property (insufficient data)")


def test_batch_analysis():
    """Test analyzing multiple properties."""
    print("\n" + "=" * 80)
    print("TEST 2: Batch Analysis")
    print("=" * 80)

    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    # Get 10 random properties
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 10
        """))
        property_ids = [row.parcel_id for row in result.fetchall()]

    print(f"\nAnalyzing {len(property_ids)} properties in batch...")
    print("-" * 80)

    analyses = analyzer.analyze_batch(property_ids)

    print(f"\nResults Summary:")
    print("-" * 80)
    print(f"Total analyzed: {len(analyses)}")

    # Group by recommendation
    appeals = [a for a in analyses if a.recommended_action == "APPEAL"]
    monitors = [a for a in analyses if a.recommended_action == "MONITOR"]
    none_action = [a for a in analyses if a.recommended_action == "NONE"]

    print(f"APPEAL recommendations: {len(appeals)}")
    print(f"MONITOR recommendations: {len(monitors)}")
    print(f"NO ACTION needed: {len(none_action)}")

    if appeals:
        print(f"\nTop appeal candidate:")
        print(f"  Property: {appeals[0].parcel_id}")
        print(f"  Address: {appeals[0].address}")
        print(f"  Fairness Score: {appeals[0].fairness_score}")
        print(f"  Potential Savings: ${appeals[0].estimated_annual_savings_dollars:,.2f}/year")


def test_find_appeal_candidates():
    """Test finding top appeal candidates."""
    print("\n" + "=" * 80)
    print("TEST 3: Find Top Appeal Candidates")
    print("=" * 80)

    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    print("\nSearching for top appeal candidates (min_score=60)...")
    print("-" * 80)

    candidates = analyzer.find_appeal_candidates(min_score=60, limit=10)

    print(f"\nFound {len(candidates)} appeal candidates")
    print()

    if candidates:
        print("TOP 5 APPEAL CANDIDATES:")
        print("-" * 80)

        for i, candidate in enumerate(candidates[:5], 1):
            print(f"\n#{i}. {candidate.parcel_id} - {candidate.address}")
            print(f"    Total Value: ${candidate.total_val_dollars:,.2f}")
            print(f"    Fairness Score: {candidate.fairness_score}/100 ({candidate.appeal_strength} case)")
            print(f"    Confidence: {candidate.confidence}/100")
            print(f"    Annual Savings: ${candidate.estimated_annual_savings_dollars:,.2f}")
            print(f"    5-Year Savings: ${candidate.estimated_five_year_savings_dollars:,.2f}")
            print(f"    Comparables: {candidate.comparable_count} properties")
    else:
        print("No appeal candidates found with score <= 60 (lower score = more over-assessed)")


def test_recommendation_scenarios():
    """Test different recommendation scenarios by filtering properties."""
    print("\n" + "=" * 80)
    print("TEST 4: Recommendation Scenarios")
    print("=" * 80)

    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    # Sample various properties to find different scenarios
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 50
        """))
        property_ids = [row.parcel_id for row in result.fetchall()]

    print(f"\nAnalyzing {len(property_ids)} properties to find different scenarios...")
    print("-" * 80)

    analyses = analyzer.analyze_batch(property_ids, batch_size=25)

    # Group by interpretation
    over_assessed = [a for a in analyses if a.interpretation == "OVER_ASSESSED"]
    fair = [a for a in analyses if a.interpretation == "FAIR"]
    under_assessed = [a for a in analyses if a.interpretation == "UNDER_ASSESSED"]

    print(f"\nFairness Distribution:")
    print(f"  Over-assessed: {len(over_assessed)}")
    print(f"  Fair: {len(fair)}")
    print(f"  Under-assessed: {len(under_assessed)}")

    # Show examples
    if over_assessed:
        print(f"\nExample OVER-ASSESSED property:")
        prop = over_assessed[0]
        print(f"  {prop.parcel_id} - {prop.address}")
        print(f"  Your market value: ${prop.total_val_cents / 100:,.2f}")
        print(f"  Median comparable value: ${prop.median_comparable_value_cents / 100:,.2f}")
        print(f"  Fairness Score: {prop.fairness_score}")
        print(f"  Recommendation: {prop.recommended_action}")

    if fair:
        print(f"\nExample FAIR property:")
        prop = fair[0]
        print(f"  {prop.parcel_id} - {prop.address}")
        print(f"  Your market value: ${prop.total_val_cents / 100:,.2f}")
        print(f"  Median comparable value: ${prop.median_comparable_value_cents / 100:,.2f}")
        print(f"  Fairness Score: {prop.fairness_score}")
        print(f"  Recommendation: {prop.recommended_action}")

    if under_assessed:
        print(f"\nExample UNDER-ASSESSED property:")
        prop = under_assessed[0]
        print(f"  {prop.parcel_id} - {prop.address}")
        print(f"  Your market value: ${prop.total_val_cents / 100:,.2f}")
        print(f"  Median comparable value: ${prop.median_comparable_value_cents / 100:,.2f}")
        print(f"  Fairness Score: {prop.fairness_score}")
        print(f"  Recommendation: {prop.recommended_action}")


def main():
    """Run all tests."""
    print("=" * 80)
    print("ASSESSMENT ANALYZER COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    try:
        test_single_property_analysis()
        test_batch_analysis()
        test_find_appeal_candidates()
        test_recommendation_scenarios()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
