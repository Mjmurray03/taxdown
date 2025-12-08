"""
Test script for saving analysis results to database.

This demonstrates the complete workflow including database persistence.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_engine
from src.services import AssessmentAnalyzer
from sqlalchemy import text


def main():
    print("=" * 80)
    print("ASSESSMENT ANALYZER - DATABASE PERSISTENCE TEST")
    print("=" * 80)
    print()

    # Initialize
    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)

    # Get a random property
    print("Finding a property to analyze...")
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

    print(f"Property: {property_id}")
    print()

    # Analyze
    print("Analyzing property...")
    analysis = analyzer.analyze_property(property_id)

    if not analysis:
        print("Could not analyze property (insufficient data)")
        return

    print(analysis)
    print()

    # Save to database
    print("Saving analysis to database...")
    try:
        analyzer.save_analysis(analysis)
        print("SUCCESS: Analysis saved to database")
        print()

        # Verify by querying back
        print("Verifying saved data...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    aa.fairness_score,
                    aa.recommended_action,
                    aa.confidence_level,
                    aa.comparable_count,
                    aa.estimated_savings_cents,
                    aa.analysis_date,
                    aa.created_at
                FROM assessment_analyses aa
                WHERE aa.property_id = CAST(:property_id AS uuid)
                ORDER BY aa.created_at DESC
                LIMIT 1
            """), {"property_id": analysis.property_id})

            row = result.fetchone()

        if row:
            print("Retrieved from database:")
            print(f"  Fairness Score: {row.fairness_score}")
            print(f"  Recommended Action: {row.recommended_action}")
            print(f"  Confidence: {row.confidence_level}")
            print(f"  Comparable Count: {row.comparable_count}")
            print(f"  Estimated Savings: ${row.estimated_savings_cents / 100:,.2f}/year")
            print(f"  Analysis Date: {row.analysis_date}")
            print(f"  Created At: {row.created_at}")
            print()
            print("VERIFICATION SUCCESSFUL!")
        else:
            print("ERROR: Could not retrieve saved analysis")

    except Exception as e:
        print(f"ERROR saving to database: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
