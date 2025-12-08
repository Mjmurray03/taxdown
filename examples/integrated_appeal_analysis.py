"""
Integrated Appeal Analysis Example

This example demonstrates how to combine the ComparableService with the
SavingsEstimator to perform a complete property tax appeal analysis:

1. Find comparable properties
2. Calculate fairness metrics
3. Estimate potential savings
4. Provide actionable recommendations
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services import SavingsEstimator


def analyze_property_appeal(
    subject_property_id: str,
    current_assessed_cents: int,
    current_total_cents: int,
    fair_ratio: float,
    mill_rate: float = 65.0
):
    """
    Perform complete appeal analysis for a property.

    Args:
        subject_property_id: Property identifier
        current_assessed_cents: Current assessed value in cents
        current_total_cents: Current total/market value in cents
        fair_ratio: Fair assessed/total ratio from comparable analysis
        mill_rate: Mill rate for the property's district

    Returns:
        dict: Complete analysis results
    """
    estimator = SavingsEstimator(default_mill_rate=mill_rate)

    # Calculate current ratio
    current_ratio = current_assessed_cents / current_total_cents

    # Calculate savings if appealing to fair ratio
    savings = estimator.estimate_from_fairness(
        current_assessed_cents=current_assessed_cents,
        current_total_cents=current_total_cents,
        target_ratio=fair_ratio,
        mill_rate=mill_rate
    )

    # Determine recommendation
    if savings.is_worthwhile:
        if savings.reduction_percent >= 15:
            recommendation = "STRONG APPEAL"
            confidence = "HIGH"
        elif savings.reduction_percent >= 10:
            recommendation = "APPEAL"
            confidence = "MEDIUM"
        else:
            recommendation = "CONSIDER APPEAL"
            confidence = "LOW"
    else:
        recommendation = "DO NOT APPEAL"
        confidence = "N/A"

    return {
        "property_id": subject_property_id,
        "current_assessment": {
            "assessed_cents": current_assessed_cents,
            "total_cents": current_total_cents,
            "ratio": current_ratio,
            "assessed_dollars": current_assessed_cents / 100,
            "total_dollars": current_total_cents / 100,
        },
        "fair_assessment": {
            "ratio": fair_ratio,
            "target_assessed_cents": savings.target_assessed_cents,
            "target_assessed_dollars": savings.target_assessed_dollars,
        },
        "overassessment": {
            "amount_cents": savings.reduction_cents,
            "amount_dollars": savings.reduction_dollars,
            "percent": savings.reduction_percent,
        },
        "savings": {
            "annual_cents": savings.annual_savings_cents,
            "annual_dollars": savings.annual_savings_dollars,
            "five_year_cents": savings.five_year_savings_cents,
            "five_year_dollars": savings.five_year_savings_dollars,
            "mill_rate": mill_rate,
        },
        "recommendation": {
            "action": recommendation,
            "confidence": confidence,
            "is_worthwhile": savings.is_worthwhile,
        }
    }


def print_appeal_report(analysis: dict):
    """Print a formatted appeal analysis report."""
    print("=" * 80)
    print(f"PROPERTY TAX APPEAL ANALYSIS: {analysis['property_id']}")
    print("=" * 80)
    print()

    # Current Assessment
    print("CURRENT ASSESSMENT")
    print("-" * 80)
    curr = analysis['current_assessment']
    print(f"  Total Value:        ${curr['total_dollars']:>15,.2f}")
    print(f"  Assessed Value:     ${curr['assessed_dollars']:>15,.2f}")
    print(f"  Assessment Ratio:   {curr['ratio']:>16.2%}")
    print()

    # Fair Assessment
    print("FAIR ASSESSMENT (Based on Comparables)")
    print("-" * 80)
    fair = analysis['fair_assessment']
    print(f"  Fair Ratio:         {fair['ratio']:>16.2%}")
    print(f"  Fair Assessed:      ${fair['target_assessed_dollars']:>15,.2f}")
    print()

    # Overassessment
    print("OVERASSESSMENT ANALYSIS")
    print("-" * 80)
    over = analysis['overassessment']
    print(f"  Overassessed By:    ${over['amount_dollars']:>15,.2f}")
    print(f"  Reduction Percent:  {over['percent']:>16.1f}%")
    print()

    # Savings
    print("POTENTIAL TAX SAVINGS")
    print("-" * 80)
    savings = analysis['savings']
    print(f"  Annual Savings:     ${savings['annual_dollars']:>15,.2f}")
    print(f"  5-Year Savings:     ${savings['five_year_dollars']:>15,.2f}")
    print(f"  Mill Rate Used:     {savings['mill_rate']:>16.2f}")
    print()

    # Recommendation
    print("RECOMMENDATION")
    print("-" * 80)
    rec = analysis['recommendation']
    print(f"  Action:             {rec['action']:>16}")
    print(f"  Confidence:         {rec['confidence']:>16}")

    if rec['is_worthwhile']:
        print()
        print("  NEXT STEPS:")
        print("  1. Gather supporting documentation (comparable sales)")
        print("  2. Prepare formal appeal with evidence")
        print("  3. Submit to county assessor before deadline")
        print(f"  4. Potential savings: ${savings['annual_dollars']:,.2f}/year")
    else:
        print()
        print("  NOTE: Potential savings do not justify appeal effort.")
        print("        Consider waiting for next reassessment cycle.")

    print()
    print("=" * 80)
    print()


def main():
    """Run example appeal analyses."""
    print("\n")
    print("#" * 80)
    print("# INTEGRATED APPEAL ANALYSIS EXAMPLES")
    print("#" * 80)
    print("\n")

    # Example 1: Strong appeal case
    print("EXAMPLE 1: Strong Appeal Case")
    print("Property significantly overassessed compared to comparables")
    print()

    analysis1 = analyze_property_appeal(
        subject_property_id="123-45-678",
        current_assessed_cents=9000000,   # $90,000 (25.7% ratio)
        current_total_cents=35000000,     # $350,000 market value
        fair_ratio=0.20,                   # Comparables show 20% is fair
        mill_rate=68.5
    )
    print_appeal_report(analysis1)

    # Example 2: Moderate appeal case
    print("\n")
    print("EXAMPLE 2: Moderate Appeal Case")
    print("Property moderately overassessed")
    print()

    analysis2 = analyze_property_appeal(
        subject_property_id="987-65-432",
        current_assessed_cents=5400000,   # $54,000 (21.6% ratio)
        current_total_cents=25000000,     # $250,000 market value
        fair_ratio=0.20,                   # Comparables show 20% is fair
        mill_rate=65.0
    )
    print_appeal_report(analysis2)

    # Example 3: Not worthwhile
    print("\n")
    print("EXAMPLE 3: Not Worthwhile Case")
    print("Property only slightly overassessed")
    print()

    analysis3 = analyze_property_appeal(
        subject_property_id="555-12-999",
        current_assessed_cents=5100000,   # $51,000 (20.4% ratio)
        current_total_cents=25000000,     # $250,000 market value
        fair_ratio=0.20,                   # Comparables show 20% is fair
        mill_rate=65.0
    )
    print_appeal_report(analysis3)

    # Example 4: Fairly assessed
    print("\n")
    print("EXAMPLE 4: Fairly Assessed Case")
    print("Property already at fair ratio")
    print()

    analysis4 = analyze_property_appeal(
        subject_property_id="444-88-222",
        current_assessed_cents=5000000,   # $50,000 (20% ratio)
        current_total_cents=25000000,     # $250,000 market value
        fair_ratio=0.20,                   # Already at fair ratio
        mill_rate=65.0
    )
    print_appeal_report(analysis4)

    # Summary table
    print("\n")
    print("BATCH SUMMARY")
    print("=" * 80)

    analyses = [analysis1, analysis2, analysis3, analysis4]

    print(f"{'Property':<15} {'Current':<12} {'Fair':<12} "
          f"{'Savings/Yr':<15} {'Recommendation':<20}")
    print("-" * 80)

    for analysis in analyses:
        prop_id = analysis['property_id']
        current_ratio = analysis['current_assessment']['ratio']
        fair_ratio = analysis['fair_assessment']['ratio']
        annual_savings = analysis['savings']['annual_dollars']
        rec = analysis['recommendation']['action']

        print(f"{prop_id:<15} {current_ratio:>10.1%} {fair_ratio:>10.1%} "
              f"${annual_savings:>13,.2f} {rec:<20}")

    print()
    print("#" * 80)
    print("# END OF EXAMPLES")
    print("#" * 80)
    print()


if __name__ == "__main__":
    main()
