#!/usr/bin/env python3
"""
Benton County Property Tax Assessment Batch Analysis Script

This CLI tool analyzes properties in Benton County to identify potential tax appeal
candidates based on fairness scoring, comparable property analysis, and estimated
tax savings.

Usage Examples:
    # Analyze first 1000 properties (default)
    python src/scripts/analyze_county.py

    # Analyze with custom limits
    python src/scripts/analyze_county.py --limit 1000 --min-score 70 --min-savings 500

    # Filter by subdivision
    python src/scripts/analyze_county.py --subdivision "Bella Vista" --limit 500

    # Analyze all properties (WARNING: may take hours)
    python src/scripts/analyze_county.py --full --output full_results.csv --save-db

    # Save results to CSV
    python src/scripts/analyze_county.py --output appeal_candidates.csv --verbose
"""

import argparse
import csv
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from decimal import Decimal

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("WARNING: tqdm not installed. Progress bars will be disabled.")
    print("Install with: pip install tqdm")

from src.config import get_engine
from src.services.assessment_analyzer import AssessmentAnalyzer, AssessmentAnalysis


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging with appropriate level."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_property_ids(
    engine: Engine,
    limit: Optional[int] = None,
    subdivision: Optional[str] = None,
    property_type: Optional[str] = None,
    full: bool = False
) -> List[str]:
    """
    Fetch property IDs to analyze based on filters.

    Args:
        engine: Database engine
        limit: Maximum number of properties (None for no limit if full=True)
        subdivision: Filter by subdivision name
        property_type: Filter by property type (RES, COM, etc.)
        full: If True, analyze all properties (overrides limit)

    Returns:
        List of parcel IDs to analyze
    """
    # Build WHERE clause
    where_conditions = [
        "assess_val_cents > 0",
        "total_val_cents > 0",
        "parcel_id IS NOT NULL",
        "is_active = true"
    ]

    params = {}

    if subdivision:
        where_conditions.append("UPPER(subdivname) LIKE UPPER(:subdivision)")
        params['subdivision'] = f"%{subdivision}%"

    if property_type:
        where_conditions.append("UPPER(type_) = UPPER(:property_type)")
        params['property_type'] = property_type

    where_clause = " AND ".join(where_conditions)

    # Build query
    if full:
        # Analyze all matching properties
        query = text(f"""
            SELECT parcel_id
            FROM properties
            WHERE {where_clause}
            ORDER BY total_val_cents DESC
        """)
    else:
        # Apply limit
        query_limit = limit or 1000
        query = text(f"""
            SELECT parcel_id
            FROM properties
            WHERE {where_clause}
            ORDER BY total_val_cents DESC
            LIMIT :query_limit
        """)
        params['query_limit'] = query_limit

    with engine.connect() as conn:
        result = conn.execute(query, params)
        property_ids = [row.parcel_id for row in result.fetchall()]

    return property_ids


# ============================================================================
# ANALYSIS EXECUTION
# ============================================================================

class AnalysisStats:
    """Track statistics during batch analysis."""

    def __init__(self):
        self.total_analyzed = 0
        self.total_errors = 0
        self.appeal_candidates = 0
        self.strong_cases = 0
        self.moderate_cases = 0
        self.weak_cases = 0
        self.total_annual_savings_cents = 0
        self.total_five_year_savings_cents = 0
        self.start_time = time.time()
        self.results: List[AssessmentAnalysis] = []

    def add_result(self, analysis: AssessmentAnalysis):
        """Add a successful analysis result."""
        self.total_analyzed += 1
        self.results.append(analysis)

        if analysis.recommended_action == "APPEAL":
            self.appeal_candidates += 1
            self.total_annual_savings_cents += analysis.estimated_annual_savings_cents
            self.total_five_year_savings_cents += analysis.estimated_five_year_savings_cents

            if analysis.appeal_strength == "STRONG":
                self.strong_cases += 1
            elif analysis.appeal_strength == "MODERATE":
                self.moderate_cases += 1
        elif analysis.recommended_action == "MONITOR":
            self.weak_cases += 1

    def add_error(self):
        """Increment error count."""
        self.total_errors += 1

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time

    @property
    def elapsed_time_str(self) -> str:
        """Get formatted elapsed time string."""
        seconds = int(self.elapsed_time)
        minutes = seconds // 60
        secs = seconds % 60
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    @property
    def average_savings_per_case(self) -> int:
        """Get average annual savings per appeal case in cents."""
        if self.appeal_candidates > 0:
            return self.total_annual_savings_cents // self.appeal_candidates
        return 0


def analyze_properties(
    analyzer: AssessmentAnalyzer,
    property_ids: List[str],
    min_score: int,
    min_savings: int,
    verbose: bool,
    save_db: bool,
    logger: logging.Logger
) -> AnalysisStats:
    """
    Analyze properties and collect results.

    Args:
        analyzer: AssessmentAnalyzer instance
        property_ids: List of parcel IDs to analyze
        min_score: Minimum fairness score to include
        min_savings: Minimum annual savings in dollars
        verbose: Show verbose progress
        save_db: Save results to database
        logger: Logger instance

    Returns:
        AnalysisStats with results and statistics
    """
    stats = AnalysisStats()
    min_savings_cents = min_savings * 100  # Convert to cents

    # Create progress bar if tqdm available
    if TQDM_AVAILABLE and not verbose:
        iterator = tqdm(property_ids, desc="Analyzing properties", unit="prop")
    else:
        iterator = property_ids

    for i, prop_id in enumerate(iterator, 1):
        try:
            # Analyze property
            analysis = analyzer.analyze_property(prop_id)

            if analysis:
                # Filter by minimum score and savings
                if (analysis.fairness_score >= min_score and
                    analysis.estimated_annual_savings_cents >= min_savings_cents):
                    stats.add_result(analysis)

                    # Save to database if requested
                    if save_db:
                        try:
                            analyzer.save_analysis(analysis)
                        except Exception as e:
                            logger.error(f"Failed to save analysis for {prop_id}: {e}")
                else:
                    # Still count as analyzed, just filtered out
                    stats.total_analyzed += 1
            else:
                stats.add_error()
                if verbose:
                    logger.debug(f"Could not analyze {prop_id} (insufficient data)")

        except Exception as e:
            stats.add_error()
            logger.error(f"Error analyzing {prop_id}: {e}")

        # Progress reporting every 100 properties
        if verbose and i % 100 == 0:
            logger.info(
                f"Progress: {i}/{len(property_ids)} | "
                f"Analyzed: {stats.total_analyzed} | "
                f"Appeal Candidates: {stats.appeal_candidates} | "
                f"Errors: {stats.total_errors}"
            )

    return stats


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def save_results_to_csv(results: List[AssessmentAnalysis], output_path: str):
    """
    Save analysis results to CSV file.

    Args:
        results: List of AssessmentAnalysis results
        output_path: Path to output CSV file
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'property_id',
            'parcel_id',
            'address',
            'total_value',
            'assessed_value',
            'fairness_score',
            'confidence',
            'annual_savings',
            'five_year_savings',
            'recommendation',
            'appeal_strength'
        ])

        # Write data rows
        for analysis in results:
            writer.writerow([
                analysis.property_id,
                analysis.parcel_id,
                analysis.address,
                f"{analysis.total_val_dollars:.2f}",
                f"{analysis.assess_val_dollars:.2f}",
                analysis.fairness_score,
                analysis.confidence,
                f"{analysis.estimated_annual_savings_dollars:.2f}",
                f"{analysis.estimated_five_year_savings_dollars:.2f}",
                analysis.recommended_action,
                analysis.appeal_strength or ''
            ])


def print_summary_report(stats: AnalysisStats, output_path: Optional[str] = None):
    """
    Print beautiful summary report to console.

    Args:
        stats: AnalysisStats with results
        output_path: Path to output CSV file (if saved)
    """
    # Sort results by annual savings (highest first)
    top_candidates = sorted(
        stats.results,
        key=lambda x: x.estimated_annual_savings_cents,
        reverse=True
    )[:5]

    print()
    print("=" * 70)
    print("BENTON COUNTY ASSESSMENT ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Properties Analyzed:     {stats.total_analyzed:,}")
    print(f"Analysis Time:          {stats.elapsed_time_str}")

    if stats.total_errors > 0:
        print(f"Errors/Skipped:         {stats.total_errors:,}")

    print()
    print(f"APPEAL CANDIDATES FOUND: {stats.appeal_candidates:,} "
          f"({stats.appeal_candidates / max(stats.total_analyzed, 1) * 100:.1f}%)")

    if stats.appeal_candidates > 0:
        print(f"├── Strong Cases:        {stats.strong_cases:,}")
        print(f"├── Moderate Cases:      {stats.moderate_cases:,}")
        print(f"└── Weak (Monitor):      {stats.weak_cases:,}")

        print()
        print("POTENTIAL SAVINGS IDENTIFIED:")
        print(f"├── Annual Total:       ${stats.total_annual_savings_cents / 100:,.2f}")
        print(f"├── 5-Year Total:      ${stats.total_five_year_savings_cents / 100:,.2f}")
        print(f"└── Average per Case:     ${stats.average_savings_per_case / 100:,.2f}")

        if top_candidates:
            print()
            print("TOP 5 APPEAL CANDIDATES:")
            print()
            for i, analysis in enumerate(top_candidates, 1):
                print(f"{i}. {analysis.address}")
                print(f"   Score: {analysis.fairness_score}, "
                      f"Savings: ${analysis.estimated_annual_savings_dollars:,.2f}/yr, "
                      f"Strength: {analysis.appeal_strength or 'N/A'}")
    else:
        print()
        print("No appeal candidates found matching the specified criteria.")

    if output_path:
        print()
        print(f"Results saved to: {output_path}")

    print("=" * 70)


# ============================================================================
# MAIN CLI
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Benton County properties to identify tax appeal candidates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze first 1000 properties with default settings
  python src/scripts/analyze_county.py

  # Find strong appeal cases with high savings potential
  python src/scripts/analyze_county.py --limit 500 --min-score 70 --min-savings 500

  # Analyze specific subdivision
  python src/scripts/analyze_county.py --subdivision "Bella Vista" --limit 1000

  # Full county analysis (WARNING: may take hours for 173K properties)
  python src/scripts/analyze_county.py --full --output full_county.csv --save-db

  # Verbose mode with progress details
  python src/scripts/analyze_county.py --limit 2000 --verbose
        """
    )

    # Analysis parameters
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Maximum properties to analyze (default: 1000)'
    )

    parser.add_argument(
        '--min-score',
        type=int,
        default=60,
        help='Minimum fairness score to include (default: 60)'
    )

    parser.add_argument(
        '--min-savings',
        type=int,
        default=250,
        help='Minimum annual savings in dollars (default: 250)'
    )

    # Filters
    parser.add_argument(
        '--subdivision',
        type=str,
        help='Filter to specific subdivision'
    )

    parser.add_argument(
        '--property-type',
        type=str,
        help='Filter by property type (e.g., RES, COM)'
    )

    # Output options
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path'
    )

    parser.add_argument(
        '--full',
        action='store_true',
        help='Analyze ALL properties (WARNING: may take hours)'
    )

    parser.add_argument(
        '--save-db',
        action='store_true',
        help='Save results to assessment_analyses table'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose progress details'
    )

    # Database configuration
    parser.add_argument(
        '--mill-rate',
        type=float,
        default=65.0,
        help='Mill rate for tax calculations (default: 65.0)'
    )

    return parser.parse_args()


def main():
    """Main entry point for the CLI script."""
    args = parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)

    # Print header
    print()
    print("=" * 70)
    print("BENTON COUNTY PROPERTY TAX ASSESSMENT ANALYZER")
    print("=" * 70)
    print()

    # Validate arguments
    if args.full and not args.output:
        print("WARNING: Full analysis without --output flag.")
        print("Results will only be displayed on screen (not saved to file).")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    if args.full:
        print("WARNING: Full county analysis may take many hours (est. ~29 hrs for 173K properties)")
        print("Target rate: ~100 properties per minute")
        response = input("Continue with full analysis? (y/n): ")
        if response.lower() != 'y':
            print("Aborted. Use --limit to analyze a subset.")
            return

    try:
        # Initialize database connection
        logger.info("Connecting to database...")
        engine = get_engine()

        # Initialize analyzer
        logger.info(f"Initializing analyzer (mill_rate={args.mill_rate})...")
        analyzer = AssessmentAnalyzer(engine, default_mill_rate=args.mill_rate)

        # Fetch property IDs
        logger.info("Fetching property IDs from database...")
        property_ids = fetch_property_ids(
            engine,
            limit=args.limit,
            subdivision=args.subdivision,
            property_type=args.property_type,
            full=args.full
        )

        if not property_ids:
            print("ERROR: No properties found matching the specified criteria.")
            return

        print(f"Found {len(property_ids):,} properties to analyze")

        if args.subdivision:
            print(f"Subdivision filter: {args.subdivision}")
        if args.property_type:
            print(f"Property type filter: {args.property_type}")

        print(f"Minimum fairness score: {args.min_score}")
        print(f"Minimum annual savings: ${args.min_savings}")
        print()

        # Estimate time
        est_minutes = len(property_ids) / 100  # ~100 properties per minute
        if est_minutes > 60:
            print(f"Estimated time: ~{est_minutes / 60:.1f} hours")
        else:
            print(f"Estimated time: ~{est_minutes:.0f} minutes")
        print()

        # Run analysis
        logger.info("Starting analysis...")
        stats = analyze_properties(
            analyzer,
            property_ids,
            min_score=args.min_score,
            min_savings=args.min_savings,
            verbose=args.verbose,
            save_db=args.save_db,
            logger=logger
        )

        # Save to CSV if requested
        if args.output and stats.results:
            logger.info(f"Saving results to {args.output}...")
            save_results_to_csv(stats.results, args.output)

        # Print summary report
        print_summary_report(stats, args.output if args.output else None)

        logger.info("Analysis complete!")

    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
