"""
Example: Using FairnessScorer with Database Property Data

This example demonstrates how to integrate the fairness scorer
with actual property data from the PostGIS database.
"""

import sys
import os
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.fairness_scorer import FairnessScorer, FairnessResult


def calculate_assessment_ratio(assessed_value: float, total_value: float) -> Optional[float]:
    """
    Calculate the assessment ratio (assessed / total)

    Args:
        assessed_value: Assessed value of the property
        total_value: Total market value of the property

    Returns:
        Assessment ratio or None if invalid
    """
    if total_value <= 0:
        return None
    return assessed_value / total_value


def example_with_real_property_data():
    """
    Example using realistic property data structure
    """
    print("Example: Fairness Scoring with Property Database")
    print("=" * 80)

    scorer = FairnessScorer()

    # Simulate property data from database
    # In real usage, this would come from your PostGIS database query
    subject_property = {
        'property_id': 'R123456',
        'address': '123 Main Street',
        'assessed_value': 285000,
        'total_value': 300000,  # Market value
        'property_type': 'Residential',
        'sqft': 2000,
        'year_built': 2005
    }

    # Comparable properties (from spatial query or similarity search)
    comparable_properties = [
        {'property_id': 'R123457', 'assessed_value': 242000, 'total_value': 280000},
        {'property_id': 'R123458', 'assessed_value': 255000, 'total_value': 295000},
        {'property_id': 'R123459', 'assessed_value': 232000, 'total_value': 275000},
        {'property_id': 'R123460', 'assessed_value': 266000, 'total_value': 310000},
        {'property_id': 'R123461', 'assessed_value': 248000, 'total_value': 290000},
        {'property_id': 'R123462', 'assessed_value': 261000, 'total_value': 305000},
        {'property_id': 'R123463', 'assessed_value': 238000, 'total_value': 282000},
        {'property_id': 'R123464', 'assessed_value': 253000, 'total_value': 298000},
    ]

    # Calculate ratios
    subject_ratio = calculate_assessment_ratio(
        subject_property['assessed_value'],
        subject_property['total_value']
    )

    comparable_ratios = []
    for comp in comparable_properties:
        ratio = calculate_assessment_ratio(comp['assessed_value'], comp['total_value'])
        if ratio is not None:
            comparable_ratios.append(ratio)

    # Calculate fairness score
    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)

    if result is None:
        print("ERROR: Unable to calculate fairness score (insufficient comparables)")
        return

    # Display results
    print(f"\nSubject Property: {subject_property['address']}")
    print(f"Property ID: {subject_property['property_id']}")
    print(f"Assessed Value: ${subject_property['assessed_value']:,}")
    print(f"Total Value: ${subject_property['total_value']:,}")
    print(f"Assessment Ratio: {result.subject_ratio:.2%}")

    print(f"\nComparables Analyzed: {result.comparable_count}")
    print(f"Median Comparable Ratio: {result.median_ratio:.2%}")
    print(f"Standard Deviation: {result.std_deviation:.4f}")

    print(f"\n{'='*80}")
    print(f"FAIRNESS SCORE: {result.fairness_score}/100")
    print(f"{'='*80}")

    print(f"\nInterpretation: {result.interpretation}")
    print(f"Recommendation: {result.get_recommendation()}")
    print(f"Confidence Level: {result.confidence}/100")
    print(f"Percentile Rank: {result.percentile:.1f}th")

    print(f"\nStatistical Analysis:")
    print(f"  Z-Score: {result.z_score:.2f} standard deviations from median")

    # Calculate potential over-assessment amount
    if result.interpretation == "OVER_ASSESSED":
        expected_assessed = subject_property['total_value'] * result.median_ratio
        over_assessment = subject_property['assessed_value'] - expected_assessed
        print(f"\nPotential Over-Assessment:")
        print(f"  Expected Assessed Value: ${expected_assessed:,.0f}")
        print(f"  Actual Assessed Value: ${subject_property['assessed_value']:,}")
        print(f"  Difference: ${over_assessment:,.0f}")

        # Estimate tax impact (assuming 2% tax rate)
        tax_rate = 0.02
        excess_tax = over_assessment * tax_rate
        print(f"  Potential Annual Tax Savings: ${excess_tax:,.2f}")

    print(f"\n{'='*80}")
    print("Recommendation Detail:")
    print(f"{'='*80}")

    if result.fairness_score >= 81:
        print("STRONG APPEAL CASE")
        print("Your property is severely over-assessed compared to similar properties.")
        print("This represents a significant statistical deviation that warrants immediate appeal.")
    elif result.fairness_score >= 61:
        print("APPEAL RECOMMENDED")
        print("Your property is significantly over-assessed. An appeal is likely to succeed.")
    elif result.fairness_score >= 41:
        print("MONITOR SITUATION")
        print("Your property is slightly over-assessed. Consider monitoring for next year.")
    elif result.fairness_score >= 21:
        print("NO ACTION NEEDED")
        print("Your property is fairly assessed relative to comparable properties.")
    else:
        print("UNDER-ASSESSED")
        print("Your property is assessed below comparable properties (favorable).")


def example_batch_neighborhood_analysis():
    """
    Example: Analyze multiple properties in a neighborhood
    """
    print("\n\nExample: Neighborhood Batch Analysis")
    print("=" * 80)

    scorer = FairnessScorer()

    # Simulate neighborhood data
    neighborhood_properties = [
        {
            'address': '100 Oak Lane',
            'assessed': 250000,
            'total': 280000,
            'comparable_ratios': [0.84, 0.86, 0.87, 0.88, 0.89, 0.90]
        },
        {
            'address': '102 Oak Lane',
            'assessed': 265000,
            'total': 285000,
            'comparable_ratios': [0.84, 0.86, 0.87, 0.88, 0.89, 0.90]
        },
        {
            'address': '104 Oak Lane',
            'assessed': 290000,
            'total': 290000,
            'comparable_ratios': [0.84, 0.86, 0.87, 0.88, 0.89, 0.90]
        },
        {
            'address': '106 Oak Lane',
            'assessed': 230000,
            'total': 275000,
            'comparable_ratios': [0.84, 0.86, 0.87, 0.88, 0.89, 0.90]
        },
    ]

    print(f"\nAnalyzing {len(neighborhood_properties)} properties on Oak Lane...")
    print(f"\n{'Address':<20} {'Ratio':>8} {'Score':>6} {'Status':<20} {'Action':<25}")
    print("-" * 90)

    appeal_candidates = []

    for prop in neighborhood_properties:
        ratio = prop['assessed'] / prop['total']
        result = scorer.calculate_fairness_score(ratio, prop['comparable_ratios'])

        if result:
            print(f"{prop['address']:<20} {ratio:>7.2%} {result.fairness_score:>6} "
                  f"{result.interpretation:<20} {result.get_recommendation():<25}")

            if result.fairness_score >= 61:
                appeal_candidates.append({
                    'address': prop['address'],
                    'score': result.fairness_score,
                    'over_assessment': prop['assessed'] - (prop['total'] * result.median_ratio)
                })

    if appeal_candidates:
        print(f"\n\nPriority Appeal Candidates:")
        print(f"{'Address':<20} {'Score':>6} {'Est. Over-Assessment':>22}")
        print("-" * 50)
        for candidate in sorted(appeal_candidates, key=lambda x: x['score'], reverse=True):
            print(f"{candidate['address']:<20} {candidate['score']:>6} "
                  f"${candidate['over_assessment']:>20,.0f}")


def example_sql_integration():
    """
    Example SQL query for fetching comparable properties
    """
    print("\n\nExample: SQL Query for Comparable Properties")
    print("=" * 80)

    sql_query = """
    -- Find comparable properties for fairness analysis
    WITH subject_property AS (
        SELECT
            property_id,
            assessed_value,
            total_value,
            assessed_value::float / NULLIF(total_value, 0) as assessment_ratio,
            geometry,
            property_class,
            year_built,
            square_feet
        FROM properties
        WHERE property_id = 'R123456'
    ),
    comparable_properties AS (
        SELECT
            p.property_id,
            p.assessed_value,
            p.total_value,
            p.assessed_value::float / NULLIF(p.total_value, 0) as assessment_ratio,
            ST_Distance(p.geometry, s.geometry) as distance_meters
        FROM properties p
        CROSS JOIN subject_property s
        WHERE p.property_id != s.property_id
          AND p.property_class = s.property_class
          AND p.year_built BETWEEN s.year_built - 10 AND s.year_built + 10
          AND p.square_feet BETWEEN s.square_feet * 0.7 AND s.square_feet * 1.3
          AND ST_DWithin(p.geometry, s.geometry, 1600)  -- Within 1 mile
          AND p.total_value > 0
        ORDER BY distance_meters
        LIMIT 20
    )
    SELECT
        (SELECT assessment_ratio FROM subject_property) as subject_ratio,
        array_agg(assessment_ratio ORDER BY distance_meters) as comparable_ratios,
        count(*) as comparable_count
    FROM comparable_properties;
    """

    print("\nSQL Query:")
    print(sql_query)

    print("\n\nPython Integration:")
    print("""
# Execute query
result = db.execute(sql_query).fetchone()

# Calculate fairness
scorer = FairnessScorer()
fairness = scorer.calculate_fairness_score(
    subject_ratio=result.subject_ratio,
    comparable_ratios=result.comparable_ratios
)

if fairness:
    print(f"Fairness Score: {fairness.fairness_score}")
    print(f"Recommendation: {fairness.get_recommendation()}")
    """)


if __name__ == "__main__":
    example_with_real_property_data()
    example_batch_neighborhood_analysis()
    example_sql_integration()
