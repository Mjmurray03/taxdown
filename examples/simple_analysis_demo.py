"""
Simple demonstration of the Assessment Analyzer.

This script shows the basic workflow for analyzing a property for appeal potential.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_engine
from src.services import AssessmentAnalyzer


def main():
    """
    Simple example: Analyze a property and print results.
    """
    print("=" * 80)
    print("TAXDOWN ASSESSMENT ANALYZER - SIMPLE DEMO")
    print("=" * 80)
    print()

    # Step 1: Initialize database connection
    print("Connecting to database...")
    engine = get_engine()

    # Step 2: Create analyzer instance
    print("Initializing analyzer...")
    analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)
    print()

    # Step 3: Analyze a specific property
    # Replace this with your property ID
    property_id = "16-26005-000"  # Example property

    print(f"Analyzing property: {property_id}")
    print("-" * 80)

    analysis = analyzer.analyze_property(property_id)

    if analysis:
        # Print results
        print()
        print(analysis)
        print()

        # Make recommendation
        if analysis.recommended_action == "APPEAL":
            print("\nRECOMMENDATION: File an appeal!")
            print(f"Strength: {analysis.appeal_strength}")
            print(f"Your property is valued at ${analysis.total_val_cents / 100:,.2f},")
            print(f"while similar properties have a median value of ${analysis.median_comparable_value_cents / 100:,.2f}.")
            print(f"\nA successful appeal could save you ${analysis.estimated_annual_savings_dollars:,.2f} per year.")
            print(f"That's ${analysis.estimated_five_year_savings_dollars:,.2f} over 5 years!")

        elif analysis.recommended_action == "MONITOR":
            print("\nRECOMMENDATION: Monitor this property.")
            print("Your assessment may be slightly high. Keep an eye on future assessments.")

        else:
            print("\nRECOMMENDATION: No action needed.")
            print("Your property appears to be fairly assessed relative to similar properties.")

    else:
        print("Could not analyze this property. Insufficient data or no comparable properties found.")


if __name__ == "__main__":
    main()
