"""
Fairness Scorer Service

Calculates how fairly a property is assessed relative to comparable properties
using statistical analysis of assessment ratios.

The fairness score (0-100) indicates:
- 0-20: Under-assessed (paying less than fair share)
- 21-40: Fairly assessed
- 41-60: Slightly over-assessed (monitor)
- 61-80: Significantly over-assessed (appeal recommended)
- 81-100: Severely over-assessed (strong appeal case)
"""

from dataclasses import dataclass
from typing import List, Optional
import statistics
import math


@dataclass
class FairnessResult:
    """Result of fairness assessment calculation"""
    fairness_score: int  # 0-100
    subject_ratio: float
    median_ratio: float
    std_deviation: float
    z_score: float
    percentile: float  # where subject falls among comparables
    interpretation: str  # "FAIR", "OVER_ASSESSED", "UNDER_ASSESSED"
    confidence: int  # 0-100 based on comparable count and consistency
    comparable_count: int

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization"""
        return {
            'fairness_score': self.fairness_score,
            'subject_ratio': round(self.subject_ratio, 4),
            'median_ratio': round(self.median_ratio, 4),
            'std_deviation': round(self.std_deviation, 4),
            'z_score': round(self.z_score, 4),
            'percentile': round(self.percentile, 2),
            'interpretation': self.interpretation,
            'confidence': self.confidence,
            'comparable_count': self.comparable_count
        }

    def get_recommendation(self) -> str:
        """Get action recommendation based on fairness score"""
        if self.fairness_score >= 81:
            return "STRONG_APPEAL_RECOMMENDED"
        elif self.fairness_score >= 61:
            return "APPEAL_RECOMMENDED"
        elif self.fairness_score >= 41:
            return "MONITOR"
        elif self.fairness_score >= 21:
            return "NO_ACTION_NEEDED"
        else:
            return "UNDER_ASSESSED"


class FairnessScorer:
    """
    Calculates fairness scores for property tax assessments using
    statistical comparison to comparable properties.
    """

    # Small epsilon to avoid division by zero
    EPSILON = 0.0001

    # Z-score to fairness score mapping
    # z=0 (at median) -> fairness=30 (fair)
    # z=+2 (2 std devs above) -> fairness=80 (over-assessed)
    # z=-2 (2 std devs below) -> fairness=0 (under-assessed)
    Z_SCORE_SCALE = 25.0  # multiplier for z-score conversion
    Z_SCORE_OFFSET = 30.0  # offset to center fairness score

    def calculate_fairness_score(
        self,
        subject_ratio: float,
        comparable_ratios: List[float],
        subdivision_median: Optional[float] = None
    ) -> Optional[FairnessResult]:
        """
        Calculate fairness score for a property assessment.

        Args:
            subject_ratio: The property's assessed/total value ratio
            comparable_ratios: List of assessment ratios from comparable properties
            subdivision_median: Optional subdivision median ratio (future use)

        Returns:
            FairnessResult with score and statistical details, or None if insufficient data
        """
        # Validate inputs
        if not comparable_ratios or len(comparable_ratios) == 0:
            return None

        if subject_ratio <= 0:
            return None

        # Filter out invalid comparable ratios
        valid_ratios = [r for r in comparable_ratios if r > 0]

        if len(valid_ratios) == 0:
            return None

        # Calculate statistical measures
        median_ratio = statistics.median(valid_ratios)

        # Calculate standard deviation (use sample std dev)
        if len(valid_ratios) >= 2:
            std_deviation = statistics.stdev(valid_ratios)
        else:
            # Only one comparable, use a default std dev based on median
            std_deviation = median_ratio * 0.1

        # Avoid division by zero
        if std_deviation < self.EPSILON:
            std_deviation = self.EPSILON

        # Calculate z-score
        z_score = (subject_ratio - median_ratio) / std_deviation

        # Convert z-score to fairness score (0-100)
        # z=0 -> 30, z=+2 -> 80, z=-2 -> 0
        fairness_score = self.Z_SCORE_OFFSET + (z_score * self.Z_SCORE_SCALE)

        # Cap at 0 and 100
        fairness_score = max(0, min(100, fairness_score))
        fairness_score = int(round(fairness_score))

        # Calculate percentile (where subject falls among comparables)
        percentile = self._calculate_percentile(subject_ratio, valid_ratios)

        # Determine interpretation
        interpretation = self._interpret_score(fairness_score)

        # Calculate confidence
        confidence = self._calculate_confidence(len(valid_ratios), std_deviation, median_ratio)

        return FairnessResult(
            fairness_score=fairness_score,
            subject_ratio=subject_ratio,
            median_ratio=median_ratio,
            std_deviation=std_deviation,
            z_score=z_score,
            percentile=percentile,
            interpretation=interpretation,
            confidence=confidence,
            comparable_count=len(valid_ratios)
        )

    def _calculate_percentile(self, subject_ratio: float, comparable_ratios: List[float]) -> float:
        """
        Calculate the percentile rank of the subject property among comparables.

        Args:
            subject_ratio: The subject property's ratio
            comparable_ratios: List of comparable ratios

        Returns:
            Percentile (0-100)
        """
        count_below = sum(1 for r in comparable_ratios if r < subject_ratio)
        count_equal = sum(1 for r in comparable_ratios if r == subject_ratio)

        # Use midpoint method for ties
        percentile = ((count_below + (count_equal / 2)) / len(comparable_ratios)) * 100

        return percentile

    def _interpret_score(self, fairness_score: int) -> str:
        """
        Interpret the fairness score into a category.

        Args:
            fairness_score: Score from 0-100

        Returns:
            Interpretation string
        """
        if fairness_score >= 41:
            return "OVER_ASSESSED"
        elif fairness_score >= 21:
            return "FAIR"
        else:
            return "UNDER_ASSESSED"

    def _calculate_confidence(
        self,
        comparable_count: int,
        std_deviation: float,
        median_ratio: float
    ) -> int:
        """
        Calculate confidence in the fairness assessment.

        Confidence is based on:
        - Number of comparables (more is better)
        - Consistency of comparables (lower std dev is better)

        Args:
            comparable_count: Number of comparable properties
            std_deviation: Standard deviation of comparable ratios
            median_ratio: Median ratio for normalization

        Returns:
            Confidence score (0-100)
        """
        # Cap confidence at 50 if fewer than 3 comparables
        if comparable_count < 3:
            max_confidence = 50
        else:
            max_confidence = 100

        # Component 1: Based on sample size (50% weight)
        # Asymptotic approach to 50 points as count approaches 20
        count_score = (comparable_count / 20) * 50
        count_score = min(50, count_score)

        # Component 2: Based on consistency (50% weight)
        # Calculate coefficient of variation (CV)
        if median_ratio > 0:
            cv = std_deviation / median_ratio
        else:
            cv = 1.0

        # Lower CV means higher confidence
        # CV of 0 -> 50 points, CV of 0.5+ -> 0 points
        consistency_score = max(0, (1 - min(cv, 0.5) / 0.5) * 50)

        # Total confidence
        confidence = count_score + consistency_score
        confidence = min(max_confidence, int(round(confidence)))

        return confidence

    def calculate_batch(
        self,
        properties: List[dict]
    ) -> List[Optional[FairnessResult]]:
        """
        Calculate fairness scores for multiple properties.

        Args:
            properties: List of dicts with 'subject_ratio' and 'comparable_ratios' keys

        Returns:
            List of FairnessResult objects
        """
        results = []

        for prop in properties:
            result = self.calculate_fairness_score(
                subject_ratio=prop.get('subject_ratio'),
                comparable_ratios=prop.get('comparable_ratios', []),
                subdivision_median=prop.get('subdivision_median')
            )
            results.append(result)

        return results


# Unit Tests
if __name__ == "__main__":
    print("Running Fairness Scorer Unit Tests...\n")

    scorer = FairnessScorer()

    # Test 1: Fairly assessed property (ratio matches median)
    print("=" * 60)
    print("Test 1: Fairly Assessed Property")
    print("=" * 60)
    comparable_ratios = [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
    subject_ratio = 0.88  # Close to median

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Median Ratio: {result.median_ratio:.4f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Confidence: {result.confidence}")
    print(f"Percentile: {result.percentile:.1f}th")
    print(f"Recommendation: {result.get_recommendation()}")
    assert 21 <= result.fairness_score <= 40, f"Expected fair score, got {result.fairness_score}"
    print("PASSED\n")

    # Test 2: Over-assessed property (ratio 50% above median)
    print("=" * 60)
    print("Test 2: Over-Assessed Property (50% Above Median)")
    print("=" * 60)
    comparable_ratios = [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
    median = statistics.median(comparable_ratios)
    subject_ratio = median * 1.5  # 50% above median

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio:.4f}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Median Ratio: {result.median_ratio:.4f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Confidence: {result.confidence}")
    print(f"Percentile: {result.percentile:.1f}th")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score >= 61, f"Expected over-assessed score, got {result.fairness_score}"
    assert result.interpretation == "OVER_ASSESSED"
    print("PASSED\n")

    # Test 3: Under-assessed property (ratio 50% below median)
    print("=" * 60)
    print("Test 3: Under-Assessed Property (50% Below Median)")
    print("=" * 60)
    comparable_ratios = [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
    median = statistics.median(comparable_ratios)
    subject_ratio = median * 0.5  # 50% below median

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio:.4f}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Median Ratio: {result.median_ratio:.4f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Confidence: {result.confidence}")
    print(f"Percentile: {result.percentile:.1f}th")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.fairness_score <= 20, f"Expected under-assessed score, got {result.fairness_score}"
    assert result.interpretation == "UNDER_ASSESSED"
    print("PASSED\n")

    # Test 4: Edge case - only 3 comparables
    print("=" * 60)
    print("Test 4: Edge Case - Only 3 Comparables")
    print("=" * 60)
    comparable_ratios = [0.85, 0.90, 0.95]
    subject_ratio = 1.10  # Significantly above

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Median Ratio: {result.median_ratio:.4f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Confidence: {result.confidence}")
    print(f"Percentile: {result.percentile:.1f}th")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.confidence <= 55, f"Expected low confidence (<=55), got {result.confidence}"
    assert result.comparable_count == 3
    print("PASSED\n")

    # Test 5: Edge case - zero standard deviation
    print("=" * 60)
    print("Test 5: Edge Case - Zero Standard Deviation")
    print("=" * 60)
    comparable_ratios = [0.90, 0.90, 0.90, 0.90]  # All identical
    subject_ratio = 1.00  # Above identical values

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Median Ratio: {result.median_ratio:.4f}")
    print(f"Std Deviation: {result.std_deviation:.6f}")
    print(f"Fairness Score: {result.fairness_score}")
    print(f"Z-Score: {result.z_score:.4f}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Confidence: {result.confidence}")
    print(f"Percentile: {result.percentile:.1f}th")
    print(f"Recommendation: {result.get_recommendation()}")
    assert result.std_deviation >= scorer.EPSILON, "Should handle zero std dev"
    print("PASSED\n")

    # Test 6: Edge case - no comparables
    print("=" * 60)
    print("Test 6: Edge Case - No Comparables")
    print("=" * 60)
    comparable_ratios = []
    subject_ratio = 0.90

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    print(f"Subject Ratio: {subject_ratio}")
    print(f"Comparable Ratios: {comparable_ratios}")
    print(f"Result: {result}")
    assert result is None, "Should return None with no comparables"
    print("PASSED\n")

    # Test 7: Batch calculation
    print("=" * 60)
    print("Test 7: Batch Calculation")
    print("=" * 60)
    properties = [
        {
            'subject_ratio': 0.88,
            'comparable_ratios': [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
        },
        {
            'subject_ratio': 1.20,
            'comparable_ratios': [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
        },
        {
            'subject_ratio': 0.50,
            'comparable_ratios': [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
        }
    ]

    results = scorer.calculate_batch(properties)
    print(f"Processed {len(results)} properties")
    for i, result in enumerate(results, 1):
        print(f"\nProperty {i}:")
        print(f"  Fairness Score: {result.fairness_score}")
        print(f"  Interpretation: {result.interpretation}")
        print(f"  Recommendation: {result.get_recommendation()}")

    assert len(results) == 3
    assert results[0].interpretation == "FAIR"
    assert results[1].interpretation == "OVER_ASSESSED"
    assert results[2].interpretation == "UNDER_ASSESSED"
    print("\nPASSED\n")

    # Test 8: Dictionary serialization
    print("=" * 60)
    print("Test 8: Dictionary Serialization")
    print("=" * 60)
    comparable_ratios = [0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
    subject_ratio = 0.88

    result = scorer.calculate_fairness_score(subject_ratio, comparable_ratios)
    result_dict = result.to_dict()

    print(f"Serialized result:")
    for key, value in result_dict.items():
        print(f"  {key}: {value}")

    assert 'fairness_score' in result_dict
    assert 'median_ratio' in result_dict
    assert 'interpretation' in result_dict
    assert 'confidence' in result_dict
    print("PASSED\n")

    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
