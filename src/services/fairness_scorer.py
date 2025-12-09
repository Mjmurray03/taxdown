"""
Fairness Scorer Service - Sales Comparison Approach

This service calculates how fairly a property is assessed by comparing its
TOTAL MARKET VALUE to comparable properties in the same area, following
Benton County's actual assessment methodology.

KEY INSIGHT:
Since Benton County applies a uniform 20% assessment ratio to ALL properties
(assessed_value = total_value * 0.20), comparing assessment ratios is useless.
Instead, we compare TOTAL MARKET VALUES among truly comparable properties.

A property may be OVER-ASSESSED if:
- Its total market value is significantly HIGHER than comparable properties
- With similar characteristics (size, improvements, location)
- In the same neighborhood/subdivision

Score Interpretation (INVERTED from old system):
- 90-100: Fairly assessed (at or below comparable median)
- 70-89: Slightly above comparables (probably fair)
- 50-69: Moderately above comparables (worth reviewing)
- 30-49: Significantly above comparables (appeal candidate)
- 0-29: Greatly above comparables (strong appeal candidate)

The scoring is from the TAXPAYER'S perspective:
- Higher score = fairer assessment = less likely over-assessed
- Lower score = potential over-assessment = appeal candidate
"""

from dataclasses import dataclass
from typing import List, Optional
import statistics
import math


@dataclass
class FairnessResult:
    """
    Result of fairness assessment using sales comparison method.

    Key fields:
    - fairness_score: 0-100 (higher = fairer from taxpayer perspective)
    - subject_value: The property's total market value in cents
    - median_value: Median total market value of comparables in cents
    - over_assessment_cents: Amount property may be over-assessed (0 if fairly assessed)
    - potential_annual_savings_cents: Estimated annual tax savings if appealed successfully
    """
    fairness_score: int  # 0-100 (higher = fairer)
    subject_value: int  # total_val_cents of subject property
    median_value: int  # median total_val_cents of comparables
    mean_value: int  # mean total_val_cents of comparables
    std_deviation: int  # standard deviation in cents
    z_score: float  # how many std devs above/below median
    percentile: float  # where subject falls among comparables (0-100)
    interpretation: str  # "FAIR", "OVER_ASSESSED", "UNDER_ASSESSED"
    confidence: int  # 0-100 based on comparable quality
    comparable_count: int
    over_assessment_cents: int  # amount over median (0 if at/below)
    potential_annual_savings_cents: int  # estimated savings from appeal

    # Keep these for backward compatibility with AssessmentAnalyzer
    @property
    def subject_ratio(self) -> float:
        """For backward compatibility - returns subject value as ratio placeholder."""
        return self.subject_value

    @property
    def median_ratio(self) -> float:
        """For backward compatibility - returns median value as ratio placeholder."""
        return self.median_value

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization"""
        return {
            'fairness_score': self.fairness_score,
            'subject_value_cents': self.subject_value,
            'median_value_cents': self.median_value,
            'mean_value_cents': self.mean_value,
            'std_deviation_cents': self.std_deviation,
            'z_score': round(self.z_score, 4),
            'percentile': round(self.percentile, 2),
            'interpretation': self.interpretation,
            'confidence': self.confidence,
            'comparable_count': self.comparable_count,
            'over_assessment_cents': self.over_assessment_cents,
            'potential_annual_savings_cents': self.potential_annual_savings_cents,
            'potential_annual_savings_dollars': round(self.potential_annual_savings_cents / 100, 2),
            'over_assessment_dollars': round(self.over_assessment_cents / 100, 2),
        }

    def get_recommendation(self) -> str:
        """Get action recommendation based on fairness score"""
        if self.fairness_score >= 80:
            return "NO_ACTION_NEEDED"
        elif self.fairness_score >= 60:
            return "MONITOR"
        elif self.fairness_score >= 40:
            return "APPEAL_RECOMMENDED"
        else:
            return "STRONG_APPEAL_RECOMMENDED"


class FairnessScorer:
    """
    Calculates fairness scores using the SALES COMPARISON APPROACH.

    This matches how Benton County actually assesses properties:
    - Compare total market values (not ratios, since all are 20%)
    - Focus on similar properties in same neighborhood
    - Higher value relative to comparables = potential over-assessment
    """

    # Small epsilon to avoid division by zero
    EPSILON = 1  # 1 cent minimum std dev

    # Default mill rate for Benton County (mills per dollar of assessed value)
    DEFAULT_MILL_RATE = 65.0  # 65 mills = $65 per $1000 assessed value

    # Assessment ratio used by county (uniform 20%)
    ASSESSMENT_RATIO = 0.20

    def __init__(self, mill_rate: float = DEFAULT_MILL_RATE):
        """
        Initialize the scorer.

        Args:
            mill_rate: Mill rate for tax calculations (default 65.0)
        """
        self.mill_rate = mill_rate

    def calculate_fairness_score(
        self,
        subject_value: int,
        comparable_values: List[int],
        subject_characteristics: Optional[dict] = None
    ) -> Optional[FairnessResult]:
        """
        Calculate fairness score based on value comparison to comparables.

        This is the SALES COMPARISON APPROACH:
        - Compare subject property's total market value to comparables
        - If subject is significantly above median, it may be over-assessed
        - Score reflects likelihood of successful appeal

        Args:
            subject_value: Subject property's total_val_cents
            comparable_values: List of comparable properties' total_val_cents
            subject_characteristics: Optional dict with additional property info

        Returns:
            FairnessResult with score and analysis, or None if insufficient data
        """
        # Validate inputs
        if not comparable_values or len(comparable_values) == 0:
            return None

        if subject_value <= 0:
            return None

        # Filter out invalid values
        valid_values = [v for v in comparable_values if v > 0]

        if len(valid_values) == 0:
            return None

        # Calculate statistical measures
        median_value = int(statistics.median(valid_values))
        mean_value = int(statistics.mean(valid_values))

        # Calculate standard deviation
        if len(valid_values) >= 2:
            std_deviation = int(statistics.stdev(valid_values))
        else:
            # Only one comparable, use a default std dev (10% of median)
            std_deviation = int(median_value * 0.10)

        # Avoid division by zero
        if std_deviation < self.EPSILON:
            std_deviation = max(self.EPSILON, int(median_value * 0.05))

        # Calculate z-score (how many std devs above/below median)
        z_score = (subject_value - median_value) / std_deviation

        # Calculate percentile (where subject falls among comparables)
        percentile = self._calculate_percentile(subject_value, valid_values)

        # Calculate fairness score (0-100, higher = fairer)
        # If at or below median: score = 100 (fair)
        # If above median: score decreases based on how far above
        if subject_value <= median_value:
            # At or below median = fair (score 90-100)
            # Give credit for being below median
            below_ratio = (median_value - subject_value) / max(median_value, 1)
            fairness_score = min(100, 90 + int(below_ratio * 50))
        else:
            # Above median - score decreases with z-score
            # z=0 -> 90, z=1 -> 65, z=2 -> 40, z=3 -> 15
            fairness_score = max(0, int(90 - (z_score * 25)))

        # Determine interpretation
        interpretation = self._interpret_score(fairness_score)

        # Calculate over-assessment amount and potential savings
        if subject_value > median_value:
            over_assessment_cents = subject_value - median_value
            # Potential tax savings if value reduced to median:
            # savings = (over_assessment * assessment_ratio * mill_rate / 1000)
            potential_savings_cents = int(
                over_assessment_cents * self.ASSESSMENT_RATIO * self.mill_rate / 1000
            )
        else:
            over_assessment_cents = 0
            potential_savings_cents = 0

        # Calculate confidence
        confidence = self._calculate_confidence(
            len(valid_values), std_deviation, median_value
        )

        return FairnessResult(
            fairness_score=fairness_score,
            subject_value=subject_value,
            median_value=median_value,
            mean_value=mean_value,
            std_deviation=std_deviation,
            z_score=z_score,
            percentile=percentile,
            interpretation=interpretation,
            confidence=confidence,
            comparable_count=len(valid_values),
            over_assessment_cents=over_assessment_cents,
            potential_annual_savings_cents=potential_savings_cents
        )

    def _calculate_percentile(self, subject_value: int, comparable_values: List[int]) -> float:
        """
        Calculate the percentile rank of the subject property among comparables.

        Higher percentile = property value is higher than more comparables
        - 50th percentile = at median
        - 90th percentile = higher than 90% of comparables (may be over-assessed)
        - 10th percentile = lower than 90% of comparables (likely fair)

        Args:
            subject_value: The subject property's value
            comparable_values: List of comparable values

        Returns:
            Percentile (0-100)
        """
        count_below = sum(1 for v in comparable_values if v < subject_value)
        count_equal = sum(1 for v in comparable_values if v == subject_value)

        # Use midpoint method for ties
        percentile = ((count_below + (count_equal / 2)) / len(comparable_values)) * 100

        return percentile

    def _interpret_score(self, fairness_score: int) -> str:
        """
        Interpret the fairness score into a category.

        From taxpayer perspective:
        - FAIR: Score >= 70 (at or near comparable median)
        - OVER_ASSESSED: Score < 70 (above comparable median, potential appeal)
        - UNDER_ASSESSED: N/A (we don't flag under-assessment as unfair to taxpayer)

        Args:
            fairness_score: Score from 0-100

        Returns:
            Interpretation string
        """
        if fairness_score >= 70:
            return "FAIR"
        elif fairness_score >= 40:
            return "POTENTIALLY_OVER_ASSESSED"
        else:
            return "OVER_ASSESSED"

    def _calculate_confidence(
        self,
        comparable_count: int,
        std_deviation: int,
        median_value: int
    ) -> int:
        """
        Calculate confidence in the fairness assessment.

        Confidence is based on:
        - Number of comparables (more is better, especially subdivision matches)
        - Consistency of comparables (lower coefficient of variation is better)
        - At least 5 comparables needed for high confidence

        Args:
            comparable_count: Number of comparable properties
            std_deviation: Standard deviation of comparable values
            median_value: Median value for normalization

        Returns:
            Confidence score (0-100)
        """
        # Cap confidence at 60 if fewer than 5 comparables
        if comparable_count < 3:
            max_confidence = 40
        elif comparable_count < 5:
            max_confidence = 60
        elif comparable_count < 10:
            max_confidence = 80
        else:
            max_confidence = 100

        # Component 1: Based on sample size (50% weight)
        # 20 comparables = full score
        count_score = min(50, (comparable_count / 20) * 50)

        # Component 2: Based on consistency (50% weight)
        # Calculate coefficient of variation (CV)
        if median_value > 0:
            cv = std_deviation / median_value
        else:
            cv = 1.0

        # Lower CV means higher confidence
        # CV of 0 -> 50 points, CV of 1.0+ -> 0 points
        consistency_score = max(0, (1 - min(cv, 1.0)) * 50)

        # Total confidence
        confidence = int(min(max_confidence, count_score + consistency_score))

        return confidence

    def calculate_batch(
        self,
        properties: List[dict]
    ) -> List[Optional[FairnessResult]]:
        """
        Calculate fairness scores for multiple properties.

        Args:
            properties: List of dicts with 'subject_value' and 'comparable_values' keys

        Returns:
            List of FairnessResult objects
        """
        results = []

        for prop in properties:
            result = self.calculate_fairness_score(
                subject_value=prop.get('subject_value', 0),
                comparable_values=prop.get('comparable_values', []),
                subject_characteristics=prop.get('characteristics')
            )
            results.append(result)

        return results


# Unit Tests
if __name__ == "__main__":
    print("Running Fairness Scorer Unit Tests (Sales Comparison Approach)...\n")

    scorer = FairnessScorer(mill_rate=65.0)

    # Test 1: Fairly assessed property (at median)
    print("=" * 60)
    print("Test 1: Fairly Assessed Property (At Median)")
    print("=" * 60)
    # Comparable properties with values around $200k-$250k
    comparable_values = [
        20000000, 21000000, 22500000, 23000000,
        24000000, 25000000, 26000000
    ]  # $200k-$260k in cents
    subject_value = 23000000  # $230k - at median

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    print(f"Subject Value: ${subject_value/100:,.2f}")
    print(f"Comparable Values: {[f'${v/100:,.0f}' for v in comparable_values]}")
    print(f"Median Value: ${result.median_value/100:,.2f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Over-Assessment: ${result.over_assessment_cents/100:,.2f}")
    print(f"Potential Savings: ${result.potential_annual_savings_cents/100:,.2f}/year")
    print(f"Confidence: {result.confidence}")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score >= 80, f"Expected fair score (>=80), got {result.fairness_score}"
    assert result.interpretation == "FAIR"
    print("PASSED\n")

    # Test 2: Over-assessed property (50% above median)
    print("=" * 60)
    print("Test 2: Over-Assessed Property (50% Above Median)")
    print("=" * 60)
    comparable_values = [
        20000000, 21000000, 22500000, 23000000,
        24000000, 25000000, 26000000
    ]
    median = statistics.median(comparable_values)
    subject_value = int(median * 1.5)  # 50% above median

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    print(f"Subject Value: ${subject_value/100:,.2f}")
    print(f"Median Value: ${result.median_value/100:,.2f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Over-Assessment: ${result.over_assessment_cents/100:,.2f}")
    print(f"Potential Savings: ${result.potential_annual_savings_cents/100:,.2f}/year")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score < 60, f"Expected over-assessed score (<60), got {result.fairness_score}"
    assert result.over_assessment_cents > 0
    print("PASSED\n")

    # Test 3: Under-assessed property (below median)
    print("=" * 60)
    print("Test 3: Under-Assessed Property (Below Median)")
    print("=" * 60)
    comparable_values = [
        20000000, 21000000, 22500000, 23000000,
        24000000, 25000000, 26000000
    ]
    median = statistics.median(comparable_values)
    subject_value = int(median * 0.7)  # 30% below median

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    print(f"Subject Value: ${subject_value/100:,.2f}")
    print(f"Median Value: ${result.median_value/100:,.2f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Over-Assessment: ${result.over_assessment_cents/100:,.2f}")
    print(f"Potential Savings: ${result.potential_annual_savings_cents/100:,.2f}/year")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score >= 90, f"Expected high score (>=90), got {result.fairness_score}"
    assert result.over_assessment_cents == 0
    assert result.potential_annual_savings_cents == 0
    print("PASSED\n")

    # Test 4: Strong appeal case (2+ std devs above)
    print("=" * 60)
    print("Test 4: Strong Appeal Case (Way Above Comparables)")
    print("=" * 60)
    comparable_values = [
        20000000, 21000000, 22000000, 22000000,
        23000000, 24000000, 25000000
    ]  # $200k-$250k range
    subject_value = 40000000  # $400k - way above comparables

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    print(f"Subject Value: ${subject_value/100:,.2f}")
    print(f"Median Value: ${result.median_value/100:,.2f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Over-Assessment: ${result.over_assessment_cents/100:,.2f}")
    print(f"Potential Savings: ${result.potential_annual_savings_cents/100:,.2f}/year")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score < 40, f"Expected low score (<40), got {result.fairness_score}"
    assert result.get_recommendation() == "STRONG_APPEAL_RECOMMENDED"
    print("PASSED\n")

    # Test 5: Edge case - no comparables
    print("=" * 60)
    print("Test 5: Edge Case - No Comparables")
    print("=" * 60)
    comparable_values = []
    subject_value = 25000000

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    print(f"Subject Value: ${subject_value/100:,.2f}")
    print(f"Comparable Values: {comparable_values}")
    print(f"Result: {result}")
    assert result is None, "Should return None with no comparables"
    print("PASSED\n")

    # Test 6: Dictionary serialization
    print("=" * 60)
    print("Test 6: Dictionary Serialization")
    print("=" * 60)
    comparable_values = [20000000, 22000000, 24000000, 26000000, 28000000]
    subject_value = 30000000

    result = scorer.calculate_fairness_score(subject_value, comparable_values)
    result_dict = result.to_dict()

    print(f"Serialized result:")
    for key, value in result_dict.items():
        print(f"  {key}: {value}")

    assert 'fairness_score' in result_dict
    assert 'median_value_cents' in result_dict
    assert 'potential_annual_savings_dollars' in result_dict
    print("PASSED\n")

    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
