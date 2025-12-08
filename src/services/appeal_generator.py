"""
Appeal Generator Service

This service generates complete property tax appeal packages including:
- Formal appeal letters in multiple styles
- Executive summaries
- Evidence summaries with bullet points
- Comparable properties analysis tables
- Filing instructions and deadlines

The generator uses the AssessmentAnalyzer for property analysis and can
optionally use Claude API for enhanced letter generation.

Usage:
    from src.config import get_engine
    from src.services import AppealGenerator
    from src.services.appeal_models import GeneratorConfig

    engine = get_engine()
    config = GeneratorConfig(template_style="formal", mill_rate=65.0)
    generator = AppealGenerator(engine, config)

    # Generate appeal for a single property
    package = generator.generate_appeal("16-26005-000")
    print(package.appeal_letter_text)

    # Batch generate appeals
    results = generator.generate_batch(["16-26005-000", "16-26006-000"])
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError

from .assessment_analyzer import AssessmentAnalyzer, AssessmentAnalysis
from .comparable_service import ComparableService, PropertyNotFoundError, DatabaseError
from .appeal_models import (
    GeneratorConfig,
    AppealPackage,
    BatchAppealResult,
    ComparablePropertySummary,
    AppealStatus,
    TemplateStyle,
    GeneratorType,
)

# Configure logging
logger = logging.getLogger(__name__)


class AppealGenerationError(Exception):
    """Raised when appeal generation fails."""
    pass


class PropertyNotQualifiedError(Exception):
    """Raised when a property doesn't qualify for appeal."""
    pass


class AppealGenerator:
    """
    Generates complete property tax appeal packages.

    This service orchestrates the appeal generation workflow:
    1. Analyzes the property using AssessmentAnalyzer
    2. Validates the property qualifies for appeal
    3. Retrieves comparable properties for evidence
    4. Generates appeal letter in the specified style
    5. Creates executive and evidence summaries
    6. Optionally saves the appeal to database

    Example:
        engine = get_engine()
        generator = AppealGenerator(engine)

        # Generate with default config
        package = generator.generate_appeal("16-26005-000")

        # Generate with custom config
        config = GeneratorConfig(template_style="detailed", mill_rate=65.0)
        generator.config = config
        package = generator.generate_appeal("16-26005-000")
    """

    def __init__(
        self,
        db_connection: Engine | Connection,
        config: Optional[GeneratorConfig] = None
    ):
        """
        Initialize the AppealGenerator.

        Args:
            db_connection: SQLAlchemy Engine or Connection
            config: Generator configuration (optional, uses defaults if not provided)
        """
        self.engine = db_connection if isinstance(db_connection, Engine) else None
        self.db = db_connection
        self.config = config or GeneratorConfig()

        # Initialize sub-services
        self.analyzer = AssessmentAnalyzer(db_connection, default_mill_rate=self.config.mill_rate)
        self.comparable_service = ComparableService(db_connection)

        logger.info(
            f"AppealGenerator initialized with style={self.config.template_style}, "
            f"mill_rate={self.config.mill_rate}"
        )

    def generate_appeal(
        self,
        property_id: str,
        config: Optional[GeneratorConfig] = None
    ) -> Optional[AppealPackage]:
        """
        Generate a complete appeal package for a property.

        Args:
            property_id: Parcel ID or property UUID to generate appeal for
            config: Optional override configuration for this generation

        Returns:
            AppealPackage with complete appeal documentation, or None if property
            doesn't qualify

        Raises:
            PropertyNotFoundError: If property doesn't exist
            PropertyNotQualifiedError: If property doesn't qualify for appeal
            AppealGenerationError: If generation fails
        """
        cfg = config or self.config
        logger.info(f"Generating appeal for property {property_id} with style={cfg.template_style}")

        try:
            # Step 1: Analyze the property
            analysis = self.analyzer.analyze_property(property_id)

            if not analysis:
                logger.warning(f"Property {property_id} could not be analyzed (insufficient data)")
                return None

            # Step 2: Validate property qualifies (score >= 50)
            if analysis.fairness_score < 50:
                logger.info(
                    f"Property {property_id} does not qualify for appeal "
                    f"(fairness_score={analysis.fairness_score} < 50)"
                )
                return None

            # Step 3: Get property details
            property_data = self._get_property_details(property_id)

            # Step 4: Get comparable properties for evidence
            comparables = self._get_comparable_summaries(property_id, limit=10)

            # Step 5: Calculate target values
            target_ratio = analysis.median_comparable_ratio
            requested_assessed_cents = int(analysis.total_val_cents * target_ratio)
            reduction_cents = analysis.assess_val_cents - requested_assessed_cents

            # Step 6: Generate appeal content
            appeal_letter = self._generate_letter(analysis, property_data, cfg)
            executive_summary = self._generate_executive_summary(analysis, cfg)
            evidence_summary = self._generate_evidence_summary(analysis, comparables, cfg)
            comparables_table = self._generate_comparables_table(comparables) if cfg.include_comparables else None

            # Step 7: Build the package
            package = AppealPackage(
                property_id=analysis.property_id,
                parcel_id=analysis.parcel_id,
                address=analysis.address,
                owner_name=property_data.get('owner_name'),
                owner_address=property_data.get('owner_address'),

                # Current values
                current_assessed_value_cents=analysis.assess_val_cents,
                current_total_value_cents=analysis.total_val_cents,
                current_assessment_ratio=analysis.current_ratio,

                # Requested values
                requested_assessed_value_cents=requested_assessed_cents,
                requested_total_value_cents=analysis.total_val_cents,
                target_assessment_ratio=target_ratio,

                # Savings
                estimated_annual_savings_cents=analysis.estimated_annual_savings_cents,
                estimated_five_year_savings_cents=analysis.estimated_five_year_savings_cents,
                reduction_amount_cents=reduction_cents,

                # Generated content
                appeal_letter_text=appeal_letter,
                executive_summary=executive_summary,
                evidence_summary=evidence_summary,
                comparables_table=comparables_table,

                # Analysis backing
                fairness_score=analysis.fairness_score,
                confidence_level=analysis.confidence,
                interpretation=analysis.interpretation,
                comparable_count=len(comparables),
                comparables=comparables,

                # Filing info
                jurisdiction=cfg.jurisdiction,
                filing_deadline=cfg.get_filing_deadline(),
                required_forms=["Written Statement of Appeal", "Evidence Documentation"],
                statute_reference="Arkansas Code § 26-27-301",

                # Metadata
                generated_at=datetime.now(),
                generator_type=GeneratorType.CLAUDE_API.value if cfg.use_claude_api else GeneratorType.TEMPLATE.value,
                template_style=cfg.template_style,
                status=AppealStatus.GENERATED.value,
            )

            # Step 8: Optionally save to database
            if cfg.save_to_database:
                self._save_appeal(package)

            logger.info(
                f"Appeal generated successfully for {property_id}: "
                f"fairness={analysis.fairness_score}, savings=${analysis.estimated_annual_savings_cents / 100:,.2f}"
            )

            return package

        except PropertyNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error generating appeal for {property_id}: {e}")
            raise AppealGenerationError(f"Database error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error generating appeal for {property_id}: {e}")
            raise AppealGenerationError(f"Appeal generation failed: {str(e)}") from e

    def generate_batch(
        self,
        property_ids: List[str],
        config: Optional[GeneratorConfig] = None
    ) -> BatchAppealResult:
        """
        Generate appeals for multiple properties.

        Args:
            property_ids: List of parcel IDs or property UUIDs
            config: Optional override configuration

        Returns:
            BatchAppealResult with generated appeals and statistics
        """
        cfg = config or self.config
        logger.info(f"Starting batch appeal generation for {len(property_ids)} properties")

        result = BatchAppealResult(total_requested=len(property_ids))

        for property_id in property_ids:
            try:
                package = self.generate_appeal(property_id, cfg)

                if package:
                    result.appeals.append(package)
                    result.generated += 1
                    result.total_potential_savings_cents += package.estimated_annual_savings_cents
                else:
                    result.skipped += 1

            except PropertyNotFoundError as e:
                result.errors += 1
                result.error_details.append({
                    'property_id': property_id,
                    'error': 'Property not found',
                    'message': str(e)
                })
            except Exception as e:
                result.errors += 1
                result.error_details.append({
                    'property_id': property_id,
                    'error': type(e).__name__,
                    'message': str(e)
                })

        logger.info(
            f"Batch generation complete: {result.generated} generated, "
            f"{result.skipped} skipped, {result.errors} errors"
        )

        return result

    def _get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get extended property details from database."""
        query = text("""
            SELECT
                id,
                parcel_id,
                ph_add AS address,
                ow_name AS owner_name,
                ow_add AS owner_address,
                total_val_cents,
                assess_val_cents,
                sq_ft,
                yr_built,
                prop_class
            FROM properties
            WHERE parcel_id = :property_id OR id::text = :property_id
            LIMIT 1
        """)

        with self._get_connection() as conn:
            result = conn.execute(query, {"property_id": property_id})
            row = result.mappings().first()

        if not row:
            return {}

        return dict(row)

    def _get_comparable_summaries(
        self,
        property_id: str,
        limit: int = 10
    ) -> List[ComparablePropertySummary]:
        """Get comparable properties as summary objects."""
        try:
            comparables = self.comparable_service.find_comparables(property_id, limit=limit)

            summaries = []
            for comp in comparables:
                summaries.append(ComparablePropertySummary(
                    parcel_id=comp.parcel_id,
                    address=comp.address or "Address unavailable",
                    total_value_cents=comp.total_val_cents,
                    assessed_value_cents=comp.assess_val_cents,
                    assessment_ratio=comp.assessment_ratio / 100.0,  # Convert from % to decimal
                    square_footage=comp.sq_ft,
                    year_built=comp.yr_built,
                    distance_miles=comp.distance_miles,
                    similarity_score=comp.similarity_score,
                ))

            return summaries

        except Exception as e:
            logger.warning(f"Could not get comparables for {property_id}: {e}")
            return []

    def _generate_letter(
        self,
        analysis: AssessmentAnalysis,
        property_data: Dict[str, Any],
        config: GeneratorConfig
    ) -> str:
        """Generate the appeal letter based on style."""
        style = TemplateStyle(config.template_style)
        today = date.today()

        # Format values
        current_val = f"${analysis.assess_val_cents / 100:,.2f}"
        requested_cents = int(analysis.total_val_cents * analysis.median_comparable_ratio)
        requested_val = f"${requested_cents / 100:,.2f}"
        savings = f"${analysis.estimated_annual_savings_cents / 100:,.2f}"
        owner_name = property_data.get('owner_name', '[Property Owner]')

        if style == TemplateStyle.CONCISE:
            return self._generate_concise_letter(
                analysis, today, current_val, requested_val, savings, owner_name, config
            )
        elif style == TemplateStyle.DETAILED:
            return self._generate_detailed_letter(
                analysis, today, current_val, requested_val, savings, owner_name, config
            )
        else:  # FORMAL (default)
            return self._generate_formal_letter(
                analysis, today, current_val, requested_val, savings, owner_name, config
            )

    def _generate_formal_letter(
        self,
        analysis: AssessmentAnalysis,
        today: date,
        current_val: str,
        requested_val: str,
        savings: str,
        owner_name: str,
        config: GeneratorConfig
    ) -> str:
        """Generate formal style appeal letter."""
        return f"""{today.strftime('%B %d, %Y')}

{config.jurisdiction}
215 E Central Ave, Suite 217
Bentonville, AR 72712

RE: Property Tax Assessment Appeal
Parcel ID: {analysis.parcel_id}
Property Address: {analysis.address}

Dear Members of the Board of Equalization:

I am writing to formally appeal the current assessed value of my property at the address listed above. The current assessed value of {current_val} does not reflect fair market value when compared to similar properties in the area.

GROUNDS FOR APPEAL

Based on an analysis of {analysis.comparable_count} comparable properties in Benton County, the typical assessment ratio is {analysis.median_comparable_ratio:.1%} of market value. My property is currently assessed at {analysis.current_ratio:.1%}, which is {(analysis.current_ratio - analysis.median_comparable_ratio) * 100:.1f} percentage points higher than comparable properties.

Our statistical analysis indicates:
- Fairness Score: {analysis.fairness_score}/100 ({analysis.interpretation})
- Confidence Level: {analysis.confidence}%
- Comparable Properties Analyzed: {analysis.comparable_count}

REQUESTED ADJUSTMENT

I respectfully request that the assessed value be reduced from {current_val} to {requested_val}, which would bring the assessment in line with comparable properties and result in annual tax savings of approximately {savings}.

This appeal is filed pursuant to Arkansas Code § 26-27-301. I am prepared to provide additional documentation and comparable property data to support this appeal.

Thank you for your consideration.

Respectfully,

{owner_name}
{analysis.address}"""

    def _generate_detailed_letter(
        self,
        analysis: AssessmentAnalysis,
        today: date,
        current_val: str,
        requested_val: str,
        savings: str,
        owner_name: str,
        config: GeneratorConfig
    ) -> str:
        """Generate detailed style appeal letter."""
        five_year_savings = f"${analysis.estimated_five_year_savings_cents / 100:,.2f}"

        return f"""{today.strftime('%B %d, %Y')}

{config.jurisdiction}
215 E Central Ave, Suite 217
Bentonville, AR 72712

RE: Formal Appeal of Property Tax Assessment
Parcel ID: {analysis.parcel_id}
Property Address: {analysis.address}
Current Assessed Value: {current_val}
Requested Assessed Value: {requested_val}

Dear Members of the Board of Equalization:

INTRODUCTION

I am writing to formally appeal the current assessed value of my property located at {analysis.address}, Parcel ID {analysis.parcel_id}. After careful analysis of comparable properties in the area, I believe the current assessment of {current_val} significantly exceeds the fair market value basis for this property.

STATEMENT OF FACTS

The current assessment places my property at an assessment ratio of {analysis.current_ratio:.2%} of total market value (${analysis.total_val_cents / 100:,.2f}). However, a comprehensive analysis of {analysis.comparable_count} comparable properties in Benton County reveals that the typical assessment ratio for similar properties is {analysis.median_comparable_ratio:.2%}.

This discrepancy of {(analysis.current_ratio - analysis.median_comparable_ratio) * 100:.2f} percentage points represents a significant deviation from the norm and results in an unfair tax burden on this property.

STATISTICAL ANALYSIS

Our fairness analysis yielded the following results:

Assessment Comparison:
- Subject Property Ratio: {analysis.current_ratio:.2%}
- Median Comparable Ratio: {analysis.median_comparable_ratio:.2%}
- Deviation: {(analysis.current_ratio - analysis.median_comparable_ratio) * 100:.2f} percentage points

Analysis Metrics:
- Fairness Score: {analysis.fairness_score}/100 (higher indicates over-assessment)
- Confidence Level: {analysis.confidence}/100
- Assessment Interpretation: {analysis.interpretation}
- Comparable Properties Analyzed: {analysis.comparable_count}

The fairness score of {analysis.fairness_score} (where 50 represents fair assessment) indicates that this property is being assessed at a rate substantially higher than comparable properties in the same jurisdiction.

FINANCIAL IMPACT

The over-assessment of this property results in the following excess tax burden:
- Estimated Annual Overpayment: {savings}
- Projected 5-Year Overpayment: {five_year_savings}

REQUESTED RELIEF

Based on the evidence presented, I respectfully request that the Board reduce the assessed value from {current_val} to {requested_val}. This adjustment would:

1. Align my property's assessment ratio ({analysis.median_comparable_ratio:.2%}) with comparable properties
2. Ensure fair and equitable taxation as required by Arkansas law
3. Reduce my annual property tax burden by approximately {savings}

LEGAL BASIS

This appeal is filed pursuant to Arkansas Code § 26-27-301, which provides property owners the right to appeal assessments to the County Board of Equalization when there is evidence of unequal or unfair assessment.

The Arkansas Constitution (Article 16, Section 5) requires that all property be assessed uniformly and equally. The evidence presented herein demonstrates that my property is not being assessed uniformly compared to similar properties.

SUPPORTING DOCUMENTATION

I am prepared to provide the following supporting documentation upon request:
- Detailed comparable property analysis
- Assessment ratio calculations
- Market value supporting data
- Statistical methodology documentation

CONCLUSION

I respectfully request that the Board give careful consideration to this appeal and adjust the assessment to reflect a fair and equitable value consistent with comparable properties in Benton County.

I am available to appear before the Board to present this appeal in person and answer any questions you may have.

Respectfully submitted,

{owner_name}
{analysis.address}

Enclosures: Comparable Property Analysis, Evidence Summary"""

    def _generate_concise_letter(
        self,
        analysis: AssessmentAnalysis,
        today: date,
        current_val: str,
        requested_val: str,
        savings: str,
        owner_name: str,
        config: GeneratorConfig
    ) -> str:
        """Generate concise style appeal letter."""
        return f"""{today.strftime('%B %d, %Y')}

{config.jurisdiction}
215 E Central Ave, Suite 217
Bentonville, AR 72712

RE: Property Tax Assessment Appeal
Parcel ID: {analysis.parcel_id}
Property Address: {analysis.address}

To Whom It May Concern:

I am formally appealing the assessed value of {current_val} for the above property. Based on comparable sales analysis, the fair assessed value should be {requested_val}.

Analysis of {analysis.comparable_count} comparable properties shows a median assessment ratio of {analysis.median_comparable_ratio:.1%}, while my property is assessed at {analysis.current_ratio:.1%} of market value.

Key findings:
- Fairness Score: {analysis.fairness_score}/100
- Confidence: {analysis.confidence}%
- Interpretation: {analysis.interpretation}

I request a reduction to {requested_val}, which would result in annual tax savings of approximately {savings}.

This appeal is filed pursuant to Arkansas Code § 26-27-301.

Sincerely,

{owner_name}"""

    def _generate_executive_summary(
        self,
        analysis: AssessmentAnalysis,
        config: GeneratorConfig
    ) -> str:
        """Generate executive summary for the appeal."""
        requested_cents = int(analysis.total_val_cents * analysis.median_comparable_ratio)

        return f"""EXECUTIVE SUMMARY
{'=' * 60}

Property: {analysis.address}
Parcel ID: {analysis.parcel_id}

KEY FINDINGS
{'-' * 40}
Current Assessment:      ${analysis.assess_val_cents / 100:>15,.2f}
Recommended Assessment:  ${requested_cents / 100:>15,.2f}
Potential Annual Savings: ${analysis.estimated_annual_savings_cents / 100:>14,.2f}
5-Year Savings Potential: ${analysis.estimated_five_year_savings_cents / 100:>14,.2f}

ASSESSMENT COMPARISON
{'-' * 40}
Your Assessment Ratio:        {analysis.current_ratio:>10.2%}
Comparable Properties Ratio:  {analysis.median_comparable_ratio:>10.2%}
Difference:                   {(analysis.current_ratio - analysis.median_comparable_ratio) * 100:>10.2f} pts

ANALYSIS STRENGTH
{'-' * 40}
Fairness Score:    {analysis.fairness_score:>3}/100
Confidence Level:  {analysis.confidence:>3}/100
Comparables Used:  {analysis.comparable_count:>3} properties
Recommendation:    {analysis.recommended_action}
Appeal Strength:   {analysis.appeal_strength or 'N/A'}

FILING INFORMATION
{'-' * 40}
Jurisdiction: {config.jurisdiction}
Deadline:     {config.get_filing_deadline().strftime('%B %d, %Y')}
Statute:      Arkansas Code § 26-27-301"""

    def _generate_evidence_summary(
        self,
        analysis: AssessmentAnalysis,
        comparables: List[ComparablePropertySummary],
        config: GeneratorConfig
    ) -> str:
        """Generate evidence summary with bullet points."""
        over_assessment_cents = analysis.assess_val_cents - int(
            analysis.total_val_cents * analysis.median_comparable_ratio
        )

        bullets = [
            f"Property assessed at {analysis.current_ratio:.2%} of market value vs. {analysis.median_comparable_ratio:.2%} median for comparable properties",
            f"Analysis based on {len(comparables)} comparable properties in Benton County",
            f"Fairness score of {analysis.fairness_score}/100 indicates {analysis.interpretation.lower().replace('_', '-')}",
            f"Statistical confidence level: {analysis.confidence}%",
            f"Estimated over-assessment: ${over_assessment_cents / 100:,.2f}",
            f"Projected annual tax savings if corrected: ${analysis.estimated_annual_savings_cents / 100:,.2f}",
            f"Projected 5-year tax savings: ${analysis.estimated_five_year_savings_cents / 100:,.2f}",
        ]

        if comparables:
            avg_ratio = sum(c.assessment_ratio for c in comparables) / len(comparables)
            bullets.append(f"Average comparable assessment ratio: {avg_ratio:.2%}")

        summary = "EVIDENCE SUMMARY\n" + "=" * 60 + "\n\n"
        summary += "\n".join(f"  • {b}" for b in bullets)

        return summary

    def _generate_comparables_table(
        self,
        comparables: List[ComparablePropertySummary]
    ) -> str:
        """Generate a formatted table of comparable properties."""
        if not comparables:
            return "No comparable properties available."

        header = (
            f"{'Parcel ID':<15} {'Address':<30} {'Total Value':>12} "
            f"{'Assessed':>12} {'Ratio':>8}"
        )
        separator = "-" * len(header)

        rows = [
            "COMPARABLE PROPERTIES ANALYSIS",
            "=" * 60,
            "",
            header,
            separator,
        ]

        for comp in comparables:
            address = (comp.address[:27] + "...") if len(comp.address) > 30 else comp.address
            rows.append(
                f"{comp.parcel_id:<15} {address:<30} "
                f"${comp.total_value_cents / 100:>10,.0f} "
                f"${comp.assessed_value_cents / 100:>10,.0f} "
                f"{comp.assessment_ratio:>7.1%}"
            )

        rows.append(separator)

        # Calculate averages
        avg_total = sum(c.total_value_cents for c in comparables) / len(comparables)
        avg_assessed = sum(c.assessed_value_cents for c in comparables) / len(comparables)
        avg_ratio = sum(c.assessment_ratio for c in comparables) / len(comparables)

        rows.append(
            f"{'AVERAGE':<15} {'':<30} "
            f"${avg_total / 100:>10,.0f} "
            f"${avg_assessed / 100:>10,.0f} "
            f"{avg_ratio:>7.1%}"
        )

        return "\n".join(rows)

    def _save_appeal(self, package: AppealPackage) -> None:
        """Save appeal to database."""
        logger.info(f"Saving appeal {package.appeal_id} to database")

        query = text("""
            INSERT INTO tax_appeals (
                id,
                property_id,
                status,
                original_assessed_value_cents,
                requested_value_cents,
                reduction_amount_cents,
                appeal_letter_text,
                success_probability,
                created_at,
                updated_at
            ) VALUES (
                :id,
                CAST(:property_id AS uuid),
                :status,
                :original_value,
                :requested_value,
                :reduction_amount,
                :appeal_letter,
                :success_probability,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """)

        try:
            with self._get_connection() as conn:
                conn.execute(query, {
                    'id': package.appeal_id,
                    'property_id': package.property_id,
                    'status': package.status,
                    'original_value': package.current_assessed_value_cents,
                    'requested_value': package.requested_assessed_value_cents,
                    'reduction_amount': package.reduction_amount_cents,
                    'appeal_letter': package.appeal_letter_text,
                    'success_probability': package.fairness_score / 100.0,
                })
                conn.commit()

            logger.info(f"Appeal {package.appeal_id} saved successfully")

        except SQLAlchemyError as e:
            logger.error(f"Failed to save appeal: {e}")
            # Don't raise - saving is optional

    def _get_connection(self):
        """Get a database connection context manager."""
        if isinstance(self.db, Engine):
            return self.db.connect()
        else:
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
    Test the Appeal Generator by generating an appeal for a random property.
    """
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from config import get_engine

    print("=" * 80)
    print("APPEAL GENERATOR TEST")
    print("=" * 80)
    print()

    try:
        engine = get_engine()

        # Get a random property that qualifies for appeal
        query = text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
                AND is_active = true
            ORDER BY RANDOM()
            LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            if not row:
                print("No valid properties found!")
                sys.exit(1)
            property_id = row.parcel_id

        print(f"Testing with property: {property_id}")
        print()

        # Test all three styles
        for style in ["formal", "detailed", "concise"]:
            print(f"\n{'=' * 80}")
            print(f"STYLE: {style.upper()}")
            print("=" * 80)

            config = GeneratorConfig(template_style=style, mill_rate=65.0)
            generator = AppealGenerator(engine, config)

            package = generator.generate_appeal(property_id)

            if package:
                print(f"\nProperty: {package.address}")
                print(f"Parcel ID: {package.parcel_id}")
                print(f"Current Value: ${package.current_assessed_value_cents / 100:,.2f}")
                print(f"Requested Value: ${package.requested_assessed_value_cents / 100:,.2f}")
                print(f"Estimated Savings: ${package.estimated_annual_savings_cents / 100:,.2f}/year")
                print(f"Fairness Score: {package.fairness_score}/100")
                print(f"Word Count: {package.word_count}")
                print()
                print("APPEAL LETTER:")
                print("-" * 60)
                print(package.appeal_letter_text[:2000])
                if len(package.appeal_letter_text) > 2000:
                    print("\n... [truncated]")
            else:
                print(f"Property {property_id} does not qualify for appeal")

        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
