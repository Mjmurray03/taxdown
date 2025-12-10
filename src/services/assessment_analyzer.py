"""
Assessment Analyzer Orchestrator

This service orchestrates the full assessment analysis workflow by combining:
1. ComparableService - Find similar properties for comparison
2. FairnessScorer - Calculate statistical fairness scores
3. SavingsEstimator - Estimate potential tax savings

It provides a high-level API for analyzing properties and identifying appeal candidates.

Usage:
    from config import get_engine
    from services import AssessmentAnalyzer

    engine = get_engine()
    analyzer = AssessmentAnalyzer(engine)

    # Analyze a single property
    analysis = analyzer.analyze_property("16-26005-000")
    print(f"Fairness Score: {analysis.fairness_score}")
    print(f"Estimated Annual Savings: ${analysis.estimated_annual_savings_cents / 100:,.2f}")

    # Find top appeal candidates
    candidates = analyzer.find_appeal_candidates(min_score=60, limit=50)
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError

from .comparable_service import ComparableService, PropertyNotFoundError, DatabaseError
from .fairness_scorer import FairnessScorer, FairnessResult
from .savings_estimator import SavingsEstimator, SavingsEstimate


# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AssessmentAnalysis:
    """
    Complete assessment analysis result for a property using SALES COMPARISON APPROACH.

    This dataclass combines results from all services into a single comprehensive
    report suitable for display to users or storage in database.

    SCORING (from taxpayer perspective):
    - Higher fairness_score = fairer assessment (less likely over-assessed)
    - Lower fairness_score = more likely over-assessed (better appeal candidate)
    - 90-100: Fairly assessed (at or below comparable median)
    - 70-89: Slightly above comparables (probably fair)
    - 50-69: Moderately above comparables (worth reviewing)
    - 30-49: Significantly above comparables (appeal candidate)
    - 0-29: Greatly above comparables (strong appeal candidate)
    """
    # Property identification
    property_id: str
    parcel_id: Optional[str]
    address: str

    # Current values (all in cents)
    total_val_cents: int
    assess_val_cents: int
    current_ratio: float  # assess_val / total_val (always ~20% for Benton County)

    # Analysis results from FairnessScorer (SALES COMPARISON APPROACH)
    fairness_score: int  # 0-100 (higher = FAIRER, lower = appeal candidate)
    confidence: int  # 0-100 (confidence in the analysis)
    interpretation: str  # "FAIR", "POTENTIALLY_OVER_ASSESSED", "OVER_ASSESSED"

    # Comparables summary from ComparableService
    comparable_count: int
    median_comparable_value_cents: int  # Median total market value of comparables (in cents)

    # Savings estimate from SavingsEstimator
    estimated_annual_savings_cents: int
    estimated_five_year_savings_cents: int

    # Recommendation logic
    recommended_action: str  # "APPEAL", "MONITOR", "NONE"

    # Metadata
    analysis_date: datetime

    # Fields with default values must come last
    appeal_strength: Optional[str] = None  # "STRONG", "MODERATE", "WEAK" (None if no appeal)
    comparables: List[Any] = None  # List of ComparableProperty objects
    model_version: str = "1.0.0"

    # Backward compatibility property
    @property
    def median_comparable_ratio(self) -> float:
        """Backward compatibility - returns median_comparable_value_cents."""
        return float(self.median_comparable_value_cents)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization or database storage."""
        return {
            'property_id': self.property_id,
            'parcel_id': self.parcel_id,
            'address': self.address,
            'total_val_cents': self.total_val_cents,
            'assess_val_cents': self.assess_val_cents,
            'current_ratio': round(self.current_ratio, 4),
            'fairness_score': self.fairness_score,
            'confidence': self.confidence,
            'interpretation': self.interpretation,
            'comparable_count': self.comparable_count,
            'median_comparable_value_cents': self.median_comparable_value_cents,
            'estimated_annual_savings_cents': self.estimated_annual_savings_cents,
            'estimated_five_year_savings_cents': self.estimated_five_year_savings_cents,
            'recommended_action': self.recommended_action,
            'appeal_strength': self.appeal_strength,
            'analysis_date': self.analysis_date.isoformat(),
            'model_version': self.model_version
        }

    @property
    def total_val_dollars(self) -> float:
        """Total market value in dollars."""
        return self.total_val_cents / 100.0

    @property
    def assess_val_dollars(self) -> float:
        """Assessed value in dollars."""
        return self.assess_val_cents / 100.0

    @property
    def estimated_annual_savings_dollars(self) -> float:
        """Estimated annual savings in dollars."""
        return self.estimated_annual_savings_cents / 100.0

    @property
    def estimated_five_year_savings_dollars(self) -> float:
        """Estimated 5-year savings in dollars."""
        return self.estimated_five_year_savings_cents / 100.0

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Assessment Analysis for {self.address}\n"
            f"{'=' * 70}\n"
            f"Property ID: {self.property_id} (Parcel: {self.parcel_id})\n"
            f"Total Value: ${self.total_val_dollars:,.2f}\n"
            f"Assessed Value: ${self.assess_val_dollars:,.2f} ({self.current_ratio:.2%})\n"
            f"\n"
            f"Fairness Analysis:\n"
            f"  Score: {self.fairness_score}/100 ({self.interpretation})\n"
            f"  Confidence: {self.confidence}/100\n"
            f"  Comparables: {self.comparable_count} properties\n"
            f"  Median Comparable Value: ${self.median_comparable_value_cents / 100:,.2f}\n"
            f"\n"
            f"Potential Savings:\n"
            f"  Annual: ${self.estimated_annual_savings_dollars:,.2f}\n"
            f"  5-Year: ${self.estimated_five_year_savings_dollars:,.2f}\n"
            f"\n"
            f"Recommendation: {self.recommended_action}"
            + (f" ({self.appeal_strength} case)" if self.appeal_strength else "") +
            f"\n"
            f"Analysis Date: {self.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 70}"
        )


# ============================================================================
# ASSESSMENT ANALYZER SERVICE
# ============================================================================

class AssessmentAnalyzer:
    """
    Orchestrator service for complete property assessment analysis.

    This service combines all Phase 4 services to provide:
    - Comparable property matching
    - Statistical fairness scoring
    - Tax savings estimation
    - Appeal recommendations

    Example:
        engine = get_engine()
        analyzer = AssessmentAnalyzer(engine)

        # Analyze a single property
        analysis = analyzer.analyze_property("16-26005-000")
        if analysis.recommended_action == "APPEAL":
            print(f"Strong appeal case! Potential savings: ${analysis.estimated_annual_savings_dollars:,.2f}/year")
    """

    def __init__(
        self,
        db_connection: Engine | Connection,
        default_mill_rate: float = 65.0
    ):
        """
        Initialize the assessment analyzer.

        Args:
            db_connection: SQLAlchemy Engine or Connection
            default_mill_rate: Default mill rate for tax calculations (default: 65.0)
        """
        self.db = db_connection
        self.default_mill_rate = default_mill_rate

        # Initialize sub-services
        self.comparable_service = ComparableService(db_connection)
        self.fairness_scorer = FairnessScorer()
        self.savings_estimator = SavingsEstimator(default_mill_rate=default_mill_rate)

        logger.info(f"AssessmentAnalyzer initialized with mill_rate={default_mill_rate}")

    def analyze_property(self, property_id: str) -> Optional[AssessmentAnalysis]:
        """
        Perform complete assessment analysis using the SALES COMPARISON APPROACH.

        This method implements Benton County's actual assessment methodology:
        1. Find truly comparable properties (same subdivision, similar characteristics)
        2. Compare subject property's TOTAL MARKET VALUE to comparables
        3. If subject is significantly above comparable median, it may be over-assessed
        4. Calculate potential savings from a successful appeal

        Key insight: Since Benton County applies a uniform 20% assessment ratio,
        comparing ratios is useless. Instead, we compare total market values
        among comparable properties to identify potential over-assessments.

        Args:
            property_id: Parcel ID to analyze

        Returns:
            AssessmentAnalysis with complete results, or None if property cannot be analyzed

        Raises:
            PropertyNotFoundError: If property doesn't exist
            DatabaseError: If database operation fails
        """
        logger.info(f"Starting sales comparison analysis for property: {property_id}")

        try:
            # Step 1: Get property details
            property_data = self._get_property_data(property_id)
            if not property_data:
                raise PropertyNotFoundError(property_id)

            # Validate property has required data
            if property_data['assess_val_cents'] <= 0 or property_data['total_val_cents'] <= 0:
                logger.warning(
                    f"Property {property_id} has invalid valuation data "
                    f"(assess={property_data['assess_val_cents']}, total={property_data['total_val_cents']}). "
                    "Cannot analyze."
                )
                return None

            # Calculate current assessment ratio (for display - always ~20%)
            current_ratio = property_data['assess_val_cents'] / property_data['total_val_cents']

            # Step 2: Find truly comparable properties using sales comparison approach
            # The comparable finder now prioritizes same subdivision and similar characteristics
            logger.debug(f"Finding comparable properties for {property_id}")
            comparables = self.comparable_service.find_comparables(property_id, limit=20)

            if not comparables or len(comparables) == 0:
                logger.warning(f"No comparables found for property {property_id}. Cannot perform fairness analysis.")
                return None

            # Step 3: Calculate fairness score using TOTAL VALUE comparison
            # Compare subject's total_val_cents to comparable total_val_cents
            # Higher value than comparables = potentially over-assessed
            logger.debug(f"Calculating fairness score for {property_id}")

            subject_total_value = property_data['total_val_cents']
            comparable_values = [comp.total_val_cents for comp in comparables]

            # Use the updated fairness scorer with value comparison
            fairness_result = self.fairness_scorer.calculate_fairness_score(
                subject_value=subject_total_value,
                comparable_values=comparable_values
            )

            if not fairness_result:
                logger.warning(f"Could not calculate fairness score for {property_id}")
                return None

            # Step 4: Get savings from fairness result (already calculated)
            # The new FairnessScorer calculates over_assessment and potential_savings
            estimated_annual_savings = fairness_result.potential_annual_savings_cents
            estimated_five_year_savings = estimated_annual_savings * 5

            # Step 5: Determine recommendation based on new score interpretation
            # Note: New scoring is INVERTED - higher score = fairer
            recommended_action, appeal_strength = self._determine_recommendation_v2(
                fairness_score=fairness_result.fairness_score,
                confidence=fairness_result.confidence,
                over_assessment_cents=fairness_result.over_assessment_cents,
                savings_cents=estimated_annual_savings
            )

            # Step 6: Build analysis result
            # Store median_comparable_value_cents (market value of comparable properties)
            analysis = AssessmentAnalysis(
                property_id=property_data['id'],
                parcel_id=property_data['parcel_id'],
                address=property_data['address'] or "Address not available",
                total_val_cents=property_data['total_val_cents'],
                assess_val_cents=property_data['assess_val_cents'],
                current_ratio=current_ratio,
                fairness_score=fairness_result.fairness_score,
                confidence=fairness_result.confidence,
                interpretation=fairness_result.interpretation,
                comparable_count=len(comparables),
                median_comparable_value_cents=fairness_result.median_value,  # Median total value of comparables
                comparables=comparables,
                estimated_annual_savings_cents=estimated_annual_savings,
                estimated_five_year_savings_cents=estimated_five_year_savings,
                recommended_action=recommended_action,
                appeal_strength=appeal_strength,
                analysis_date=datetime.now(),
                model_version="2.0.0"  # Updated version for sales comparison approach
            )

            logger.info(
                f"Analysis complete for {property_id}: "
                f"fairness={fairness_result.fairness_score}/100, "
                f"interpretation={fairness_result.interpretation}, "
                f"action={recommended_action}, "
                f"over_assessment=${fairness_result.over_assessment_cents / 100:,.2f}, "
                f"potential_savings=${estimated_annual_savings / 100:,.2f}/year"
            )

            return analysis

        except PropertyNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error analyzing property {property_id}: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error analyzing property {property_id}: {e}")
            raise

    def analyze_batch(
        self,
        property_ids: List[str],
        batch_size: int = 100
    ) -> List[AssessmentAnalysis]:
        """
        Analyze multiple properties in batches.

        Processes properties in batches to manage memory efficiently and logs
        progress for long-running operations.

        Args:
            property_ids: List of property IDs to analyze
            batch_size: Number of properties to process at once (default: 100)

        Returns:
            List of AssessmentAnalysis results, sorted by fairness_score descending.
            Properties that cannot be analyzed are omitted from results.
        """
        logger.info(f"Starting batch analysis of {len(property_ids)} properties (batch_size={batch_size})")

        results = []
        total_analyzed = 0
        total_errors = 0

        # Process in batches
        for i in range(0, len(property_ids), batch_size):
            batch = property_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(property_ids) + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} properties)")

            for prop_id in batch:
                try:
                    analysis = self.analyze_property(prop_id)
                    if analysis:
                        results.append(analysis)
                        total_analyzed += 1
                    else:
                        total_errors += 1
                        logger.debug(f"Property {prop_id} could not be analyzed (insufficient data)")
                except PropertyNotFoundError:
                    total_errors += 1
                    logger.warning(f"Property {prop_id} not found")
                except Exception as e:
                    total_errors += 1
                    logger.error(f"Error analyzing property {prop_id}: {e}")

            # Log progress every 1000 properties
            if (i + batch_size) % 1000 == 0 or (i + batch_size) >= len(property_ids):
                logger.info(
                    f"Progress: {min(i + batch_size, len(property_ids))}/{len(property_ids)} "
                    f"({total_analyzed} analyzed, {total_errors} errors)"
                )

        # Sort by fairness score descending (most over-assessed first)
        results.sort(key=lambda x: x.fairness_score, reverse=True)

        logger.info(
            f"Batch analysis complete: {total_analyzed} properties analyzed, "
            f"{total_errors} errors/skipped"
        )

        return results

    def find_appeal_candidates(
        self,
        min_score: int = 60,
        limit: int = 100
    ) -> List[AssessmentAnalysis]:
        """
        Find top appeal candidates from the database.

        This method:
        1. Queries properties with valid assessment data
        2. Analyzes each property
        3. Filters by minimum fairness score
        4. Returns top candidates sorted by estimated savings

        Args:
            min_score: Minimum fairness score to include (default: 60)
            limit: Maximum number of candidates to return (default: 100)

        Returns:
            List of AssessmentAnalysis for top appeal candidates,
            sorted by estimated_annual_savings_cents descending
        """
        logger.info(f"Finding appeal candidates (min_score={min_score}, limit={limit})")

        try:
            # Query properties with valid assessment data
            # Focus on properties that are actually assessed (assess_val_cents > 0)
            query = text("""
                SELECT parcel_id
                FROM properties
                WHERE assess_val_cents > 0
                    AND total_val_cents > 0
                    AND parcel_id IS NOT NULL
                    AND is_active = true
                ORDER BY total_val_cents DESC
                LIMIT :query_limit
            """)

            # Query more properties than limit to account for filtering
            query_limit = min(limit * 10, 10000)  # Cap at 10k to avoid excessive queries

            with self._get_connection() as conn:
                result = conn.execute(query, {"query_limit": query_limit})
                property_ids = [row.parcel_id for row in result.fetchall()]

            logger.info(f"Found {len(property_ids)} properties to analyze")

            # Analyze all properties
            analyses = self.analyze_batch(property_ids)

            # Filter by minimum score
            candidates = [
                analysis for analysis in analyses
                if analysis.fairness_score >= min_score
            ]

            logger.info(f"Found {len(candidates)} candidates with score >= {min_score}")

            # Sort by estimated savings (highest first)
            candidates.sort(
                key=lambda x: x.estimated_annual_savings_cents,
                reverse=True
            )

            # Return top N
            top_candidates = candidates[:limit]

            logger.info(
                f"Returning top {len(top_candidates)} appeal candidates. "
                f"Top savings: ${top_candidates[0].estimated_annual_savings_dollars:,.2f}/year "
                if top_candidates else "No candidates found"
            )

            return top_candidates

        except SQLAlchemyError as e:
            logger.error(f"Database error finding appeal candidates: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error finding appeal candidates: {e}")
            raise

    def save_analysis(self, analysis: AssessmentAnalysis) -> None:
        """
        Save analysis results to the assessment_analyses table.

        This method persists the analysis for future reference and API access.
        Maps the AssessmentAnalysis data to the database schema.

        Args:
            analysis: AssessmentAnalysis to save

        Raises:
            DatabaseError: If save operation fails
        """
        logger.info(f"Saving analysis for property {analysis.property_id}")

        try:
            # Map our analysis to the database schema
            # Note: Simply insert without conflict handling for now
            query = text("""
                INSERT INTO assessment_analyses (
                    property_id,
                    analysis_date,
                    fairness_score,
                    assessment_ratio,
                    comparable_count,
                    recommended_action,
                    estimated_savings_cents,
                    confidence_level,
                    analysis_methodology,
                    ml_model_version,
                    analysis_parameters,
                    created_at
                )
                VALUES (
                    CAST(:property_id AS uuid),
                    :analysis_date,
                    :fairness_score,
                    :assessment_ratio,
                    :comparable_count,
                    CAST(:recommended_action AS recommendation_action_enum),
                    :estimated_savings_cents,
                    :confidence_level,
                    CAST('STATISTICAL' AS analysis_methodology_enum),
                    :ml_model_version,
                    CAST(:analysis_parameters AS jsonb),
                    CURRENT_TIMESTAMP
                )
            """)

            # Prepare analysis parameters JSON
            import json
            analysis_parameters = json.dumps({
                'parcel_id': analysis.parcel_id,
                'address': analysis.address,
                'total_val_cents': analysis.total_val_cents,
                'assess_val_cents': analysis.assess_val_cents,
                'current_ratio': analysis.current_ratio,
                'median_comparable_value_cents': analysis.median_comparable_value_cents,
                'interpretation': analysis.interpretation,
                'appeal_strength': analysis.appeal_strength,
                'estimated_five_year_savings_cents': analysis.estimated_five_year_savings_cents
            })

            with self._get_connection() as conn:
                conn.execute(query, {
                    'property_id': analysis.property_id,
                    'analysis_date': analysis.analysis_date.date(),
                    'fairness_score': analysis.fairness_score,
                    'assessment_ratio': float(analysis.current_ratio),
                    'comparable_count': analysis.comparable_count,
                    'recommended_action': analysis.recommended_action,
                    'estimated_savings_cents': analysis.estimated_annual_savings_cents,
                    'confidence_level': analysis.confidence,
                    'ml_model_version': analysis.model_version,
                    'analysis_parameters': analysis_parameters
                })
                conn.commit()

            logger.info(f"Successfully saved analysis for property {analysis.property_id}")

        except SQLAlchemyError as e:
            logger.error(f"Database error saving analysis: {e}")
            raise DatabaseError(f"Failed to save analysis: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error saving analysis: {e}")
            raise

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    def _get_property_data(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve property data from database.

        Args:
            property_id: Parcel ID to retrieve

        Returns:
            Dictionary with property data, or None if not found
        """
        query = text("""
            SELECT
                id,
                parcel_id,
                ph_add AS address,
                total_val_cents,
                assess_val_cents,
                acre_area,
                ow_name AS owner_name
            FROM properties
            WHERE parcel_id = :parcel_id
                AND is_active = true
            LIMIT 1
        """)

        with self._get_connection() as conn:
            result = conn.execute(query, {"parcel_id": property_id})
            row = result.fetchone()

        if not row:
            return None

        return {
            'id': str(row.id),
            'parcel_id': row.parcel_id,
            'address': row.address,
            'total_val_cents': int(row.total_val_cents) if row.total_val_cents else 0,
            'assess_val_cents': int(row.assess_val_cents) if row.assess_val_cents else 0,
            'acreage': float(row.acre_area) if row.acre_area else 0,
            'owner_name': row.owner_name
        }

    def _determine_recommendation(
        self,
        fairness_score: int,
        confidence: int,
        savings_cents: int
    ) -> tuple[str, Optional[str]]:
        """
        DEPRECATED: Use _determine_recommendation_v2 instead.

        This function uses the OLD scoring logic where higher score = more over-assessed.
        The new scoring logic (v2) is inverted: higher score = FAIRER.

        This function is kept for backward compatibility but should not be used.

        Returns:
            Tuple of (recommended_action, appeal_strength)
        """
        # Strong appeal case
        if fairness_score >= 70 and confidence >= 60 and savings_cents >= 50000:  # $500+
            return ("APPEAL", "STRONG")

        # Moderate appeal case
        elif fairness_score >= 60 and savings_cents >= 25000:  # $250+
            return ("APPEAL", "MODERATE")

        # Monitor case (potentially over-assessed but not enough to appeal yet)
        elif fairness_score >= 50:
            return ("MONITOR", "WEAK")

        # No action needed
        else:
            return ("NONE", None)

    def _determine_recommendation_v2(
        self,
        fairness_score: int,
        confidence: int,
        over_assessment_cents: int,
        savings_cents: int
    ) -> tuple[str, Optional[str]]:
        """
        Determine appeal recommendation based on sales comparison analysis.

        NEW SCORING INTERPRETATION (inverted from v1):
        - Higher score = fairer assessment (less likely to be over-assessed)
        - Lower score = more likely over-assessed (better appeal candidate)

        Recommendation Logic:
        - STRONG APPEAL: fairness <= 40, over_assessment >= $10k, savings >= $100/year
        - MODERATE APPEAL: fairness <= 60, over_assessment >= $5k, savings >= $50/year
        - MONITOR: fairness <= 75, any over-assessment
        - NO ACTION: fairness > 75 (property is at or below comparable median)

        Args:
            fairness_score: Fairness score (0-100, higher = fairer)
            confidence: Confidence score (0-100)
            over_assessment_cents: Amount property may be over-assessed
            savings_cents: Estimated annual savings in cents

        Returns:
            Tuple of (recommended_action, appeal_strength)
        """
        # Strong appeal case - significantly over-assessed
        if fairness_score <= 40 and over_assessment_cents >= 1000000 and savings_cents >= 10000:  # $10k over, $100+ savings
            return ("APPEAL", "STRONG")

        # Moderate appeal case
        elif fairness_score <= 60 and over_assessment_cents >= 500000 and savings_cents >= 5000:  # $5k over, $50+ savings
            return ("APPEAL", "MODERATE")

        # Monitor case - slightly above comparables
        elif fairness_score <= 75 and over_assessment_cents > 0:
            return ("MONITOR", "WEAK")

        # No action needed - property is at or below comparable median
        else:
            return ("NONE", None)

    def _get_connection(self):
        """Get a database connection context manager."""
        if isinstance(self.db, Engine):
            return self.db.connect()
        else:
            # Already a connection, return a no-op context manager
            from contextlib import contextmanager

            @contextmanager
            def no_op():
                yield self.db

            return no_op()


# ============================================================================
# TEST SECTION
# ============================================================================

if __name__ == "__main__":
    """
    Test the Assessment Analyzer by analyzing 3 random properties.

    This test demonstrates the full workflow:
    1. Initialize analyzer with database connection
    2. Get random properties from database
    3. Analyze each property
    4. Print comprehensive results
    """
    import sys
    import os

    # Add parent directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from config import get_engine

    print("=" * 80)
    print("ASSESSMENT ANALYZER TEST")
    print("=" * 80)
    print()

    try:
        # Initialize database connection
        print("Initializing database connection...")
        engine = get_engine()

        # Initialize analyzer
        print("Initializing Assessment Analyzer...")
        analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)
        print()

        # Get 3 random properties with valid assessment data
        print("Fetching 3 random properties from database...")
        query = text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
                AND is_active = true
            ORDER BY RANDOM()
            LIMIT 3
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            property_ids = [row.parcel_id for row in result.fetchall()]

        if not property_ids:
            print("ERROR: No valid properties found in database!")
            sys.exit(1)

        print(f"Found properties: {', '.join(property_ids)}")
        print()

        # Analyze each property
        for i, prop_id in enumerate(property_ids, 1):
            print("\n" + "=" * 80)
            print(f"ANALYSIS #{i}: Property {prop_id}")
            print("=" * 80)

            try:
                analysis = analyzer.analyze_property(prop_id)

                if analysis:
                    print(analysis)
                    print()

                    # Additional insights
                    print("DETAILED INSIGHTS:")
                    print("-" * 80)
                    print(f"Market Value Comparison:")
                    print(f"  Your market value: ${analysis.total_val_cents / 100:,.2f}")
                    print(f"  Median comparable value: ${analysis.median_comparable_value_cents / 100:,.2f}")
                    value_diff = analysis.total_val_cents - analysis.median_comparable_value_cents
                    print(f"  Difference: ${value_diff / 100:,.2f}")
                    print()

                    if analysis.recommended_action == "APPEAL":
                        print(f"APPEAL RECOMMENDATION ({analysis.appeal_strength} case):")
                        print(f"  This property appears to be over-assessed compared to similar properties.")
                        print(f"  A successful appeal could save ${analysis.estimated_annual_savings_dollars:,.2f} per year.")
                        print(f"  Over 5 years, that's ${analysis.estimated_five_year_savings_dollars:,.2f} in savings!")
                    elif analysis.recommended_action == "MONITOR":
                        print(f"MONITOR RECOMMENDATION:")
                        print(f"  This property may be slightly over-assessed.")
                        print(f"  Monitor for changes and consider appealing if values increase further.")
                    else:
                        print(f"NO ACTION NEEDED:")
                        print(f"  This property appears to be fairly assessed relative to similar properties.")

                    print()

                else:
                    print(f"Could not analyze property {prop_id} (insufficient data)")

            except PropertyNotFoundError:
                print(f"ERROR: Property {prop_id} not found in database")
            except Exception as e:
                print(f"ERROR: Failed to analyze property {prop_id}: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
