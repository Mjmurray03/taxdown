"""
Savings Estimator for Tax Appeal Analysis

This module calculates potential tax savings if a property tax appeal is successful
in Arkansas. It handles the state's specific tax calculation rules:
- Assessed value = 20% of market value (statutory ratio)
- Tax = assessed_value × mill_rate
- 1 mill = $1 per $1,000 of assessed value
- Mill rates typically range from 50-80 mills in Benton County
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SavingsEstimate:
    """
    Represents the potential savings from a successful property tax appeal.

    All monetary values are stored in cents for precision in calculations.
    """
    current_assessed_cents: int
    target_assessed_cents: int
    reduction_cents: int  # current - target
    reduction_percent: float

    current_annual_tax_cents: int
    target_annual_tax_cents: int
    annual_savings_cents: int

    five_year_savings_cents: int  # Assuming no reassessment

    mill_rate_used: float

    @property
    def annual_savings_dollars(self) -> float:
        """Convert annual savings from cents to dollars."""
        return self.annual_savings_cents / 100

    @property
    def five_year_savings_dollars(self) -> float:
        """Convert 5-year savings from cents to dollars."""
        return self.five_year_savings_cents / 100

    @property
    def reduction_dollars(self) -> float:
        """Convert assessed value reduction from cents to dollars."""
        return self.reduction_cents / 100

    @property
    def current_assessed_dollars(self) -> float:
        """Convert current assessed value from cents to dollars."""
        return self.current_assessed_cents / 100

    @property
    def target_assessed_dollars(self) -> float:
        """Convert target assessed value from cents to dollars."""
        return self.target_assessed_cents / 100

    @property
    def is_worthwhile(self) -> bool:
        """
        Determine if the appeal is worth pursuing.

        Returns False if annual savings is less than $100, as the effort
        of appealing may not be worth the minimal savings.
        """
        return self.annual_savings_cents >= 10000  # $100 in cents

    def to_dict(self) -> dict:
        """Convert the estimate to a dictionary with human-readable values."""
        return {
            "current_assessed": self.current_assessed_dollars,
            "target_assessed": self.target_assessed_dollars,
            "reduction": self.reduction_dollars,
            "reduction_percent": round(self.reduction_percent, 2),
            "current_annual_tax": self.current_annual_tax_cents / 100,
            "target_annual_tax": self.target_annual_tax_cents / 100,
            "annual_savings": self.annual_savings_dollars,
            "five_year_savings": self.five_year_savings_dollars,
            "mill_rate": self.mill_rate_used,
            "is_worthwhile": self.is_worthwhile
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Savings Estimate:\n"
            f"  Current Assessed: ${self.current_assessed_dollars:,.2f}\n"
            f"  Target Assessed: ${self.target_assessed_dollars:,.2f}\n"
            f"  Reduction: ${self.reduction_dollars:,.2f} ({self.reduction_percent:.1f}%)\n"
            f"  Annual Tax Savings: ${self.annual_savings_dollars:,.2f}\n"
            f"  5-Year Savings: ${self.five_year_savings_dollars:,.2f}\n"
            f"  Mill Rate: {self.mill_rate_used:.2f}\n"
            f"  Worth Appealing: {self.is_worthwhile}"
        )


class SavingsEstimator:
    """
    Calculates potential tax savings from property tax appeals.

    Uses Arkansas-specific tax calculation rules with configurable mill rates.
    """

    # Minimum annual savings (in cents) to consider appeal worthwhile
    MINIMUM_WORTHWHILE_SAVINGS_CENTS = 10000  # $100

    def __init__(self, default_mill_rate: float = 65.0):
        """
        Initialize the savings estimator.

        Args:
            default_mill_rate: Default mill rate to use when none is specified.
                             Typical range in Benton County: 50-80 mills.

        Raises:
            ValueError: If default_mill_rate is not positive.
        """
        if default_mill_rate <= 0:
            raise ValueError("Mill rate must be positive")
        self.default_mill_rate = default_mill_rate

    def estimate_savings(
        self,
        current_assessed_cents: int,
        target_assessed_cents: int,
        mill_rate: Optional[float] = None
    ) -> SavingsEstimate:
        """
        Calculate potential savings from reducing assessed value.

        Args:
            current_assessed_cents: Current assessed value in cents
            target_assessed_cents: Proposed/target assessed value in cents
            mill_rate: Mill rate for the property's district (uses default if None)

        Returns:
            SavingsEstimate with calculated savings projections

        Raises:
            ValueError: If inputs are negative or mill_rate is non-positive

        Example:
            >>> estimator = SavingsEstimator(default_mill_rate=65.0)
            >>> savings = estimator.estimate_savings(
            ...     current_assessed_cents=5000000,  # $50,000
            ...     target_assessed_cents=4500000,   # $45,000
            ...     mill_rate=65.0
            ... )
            >>> print(f"Annual savings: ${savings.annual_savings_dollars:,.2f}")
            Annual savings: $325.00
        """
        # Validation
        if current_assessed_cents < 0 or target_assessed_cents < 0:
            raise ValueError("Assessed values must be non-negative")

        effective_mill_rate = mill_rate if mill_rate is not None else self.default_mill_rate
        if effective_mill_rate <= 0:
            raise ValueError("Mill rate must be positive")

        # Calculate reduction
        reduction_cents = current_assessed_cents - target_assessed_cents

        # If target is higher than current, there are no savings
        if reduction_cents <= 0:
            return self._create_zero_savings_estimate(
                current_assessed_cents,
                target_assessed_cents,
                effective_mill_rate
            )

        # Calculate reduction percentage
        if current_assessed_cents > 0:
            reduction_percent = (reduction_cents / current_assessed_cents) * 100
        else:
            reduction_percent = 0.0

        # Calculate annual taxes
        # Formula: tax = assessed_value × (mill_rate / 1000)
        # Mill rate is dollars per $1,000 of assessed value
        current_annual_tax_cents = self._calculate_tax(
            current_assessed_cents,
            effective_mill_rate
        )
        target_annual_tax_cents = self._calculate_tax(
            target_assessed_cents,
            effective_mill_rate
        )

        annual_savings_cents = current_annual_tax_cents - target_annual_tax_cents

        # Project 5-year savings (assuming no reassessment)
        five_year_savings_cents = annual_savings_cents * 5

        return SavingsEstimate(
            current_assessed_cents=current_assessed_cents,
            target_assessed_cents=target_assessed_cents,
            reduction_cents=reduction_cents,
            reduction_percent=reduction_percent,
            current_annual_tax_cents=current_annual_tax_cents,
            target_annual_tax_cents=target_annual_tax_cents,
            annual_savings_cents=annual_savings_cents,
            five_year_savings_cents=five_year_savings_cents,
            mill_rate_used=effective_mill_rate
        )

    def estimate_from_fairness(
        self,
        current_assessed_cents: int,
        current_total_cents: int,
        target_ratio: float,
        mill_rate: Optional[float] = None
    ) -> SavingsEstimate:
        """
        Calculate savings based on a target fairness ratio from comparable sales.

        This method is useful when you've determined that a property should be
        assessed at a certain percentage of its total value (based on comparable
        properties in the area).

        Args:
            current_assessed_cents: Current assessed value in cents
            current_total_cents: Current total/market value in cents
            target_ratio: Target ratio (assessed/total) that would be "fair"
                         (e.g., 0.20 for 20%, which is the statutory ratio in AR)
            mill_rate: Mill rate for the property's district (uses default if None)

        Returns:
            SavingsEstimate with calculated savings projections

        Raises:
            ValueError: If inputs are invalid

        Example:
            >>> estimator = SavingsEstimator()
            >>> # Property currently assessed at 25% but should be 20%
            >>> savings = estimator.estimate_from_fairness(
            ...     current_assessed_cents=6250000,  # $62,500 (25%)
            ...     current_total_cents=25000000,     # $250,000
            ...     target_ratio=0.20                  # Should be 20%
            ... )
            >>> print(f"Target assessed: ${savings.target_assessed_dollars:,.2f}")
            Target assessed: $50,000.00
        """
        if current_assessed_cents < 0 or current_total_cents < 0:
            raise ValueError("Values must be non-negative")

        if target_ratio < 0 or target_ratio > 1:
            raise ValueError("Target ratio must be between 0 and 1")

        if current_total_cents == 0:
            raise ValueError("Current total value cannot be zero")

        # Calculate target assessed value based on the fair ratio
        target_assessed_cents = int(current_total_cents * target_ratio)

        # Use the standard estimate_savings method
        return self.estimate_savings(
            current_assessed_cents=current_assessed_cents,
            target_assessed_cents=target_assessed_cents,
            mill_rate=mill_rate
        )

    def get_mill_rate_for_property(self, property_id: str) -> float:
        """
        Get the mill rate for a specific property based on its tax district.

        This is a stub for future enhancement. Currently returns the default
        mill rate. In the future, this could look up the actual mill rate
        from a database based on the property's location and tax district.

        Args:
            property_id: Unique identifier for the property

        Returns:
            Mill rate for the property's district

        TODO: Implement district-based mill rate lookup
            - Query property location from database
            - Determine tax district(s)
            - Sum mill rates from all applicable districts
            - Cache results for performance
        """
        # TODO: Implement actual lookup logic
        # For now, return default mill rate
        return self.default_mill_rate

    def _calculate_tax(self, assessed_cents: int, mill_rate: float) -> int:
        """
        Calculate annual property tax in cents.

        Formula: tax = assessed_value × (mill_rate / 1000)

        Args:
            assessed_cents: Assessed value in cents
            mill_rate: Mill rate (dollars per $1,000 of assessed value)

        Returns:
            Annual tax in cents
        """
        # Convert cents to dollars for calculation
        assessed_dollars = assessed_cents / 100

        # Mill rate is per $1,000 of assessed value
        tax_dollars = assessed_dollars * (mill_rate / 1000)

        # Convert back to cents and round
        return int(round(tax_dollars * 100))

    def _create_zero_savings_estimate(
        self,
        current_assessed_cents: int,
        target_assessed_cents: int,
        mill_rate: float
    ) -> SavingsEstimate:
        """
        Create a SavingsEstimate with zero savings.

        Used when target assessed value is >= current assessed value.
        """
        current_annual_tax_cents = self._calculate_tax(
            current_assessed_cents,
            mill_rate
        )

        return SavingsEstimate(
            current_assessed_cents=current_assessed_cents,
            target_assessed_cents=target_assessed_cents,
            reduction_cents=0,
            reduction_percent=0.0,
            current_annual_tax_cents=current_annual_tax_cents,
            target_annual_tax_cents=current_annual_tax_cents,
            annual_savings_cents=0,
            five_year_savings_cents=0,
            mill_rate_used=mill_rate
        )


# Test cases
if __name__ == "__main__":
    print("=" * 70)
    print("SAVINGS ESTIMATOR TEST CASES")
    print("=" * 70)

    estimator = SavingsEstimator(default_mill_rate=65.0)

    # Test 1: Standard savings calculation
    print("\nTest 1: Standard Savings Calculation")
    print("-" * 70)
    savings1 = estimator.estimate_savings(
        current_assessed_cents=5000000,  # $50,000
        target_assessed_cents=4500000,   # $45,000
        mill_rate=65.0
    )
    print(savings1)
    print(f"\nDict format: {savings1.to_dict()}")

    # Test 2: Using fairness ratio
    print("\n\nTest 2: Fairness Ratio Calculation")
    print("-" * 70)
    print("Property assessed at 25% but should be 20% (statutory ratio)")
    savings2 = estimator.estimate_from_fairness(
        current_assessed_cents=6250000,   # $62,500 (25% of $250k)
        current_total_cents=25000000,     # $250,000 market value
        target_ratio=0.20                  # Should be 20%
    )
    print(savings2)

    # Test 3: Large reduction (worthwhile appeal)
    print("\n\nTest 3: Large Reduction (Worthwhile Appeal)")
    print("-" * 70)
    savings3 = estimator.estimate_savings(
        current_assessed_cents=10000000,  # $100,000
        target_assessed_cents=8000000,    # $80,000
        mill_rate=70.0
    )
    print(savings3)

    # Test 4: Small reduction (not worthwhile)
    print("\n\nTest 4: Small Reduction (Not Worthwhile)")
    print("-" * 70)
    savings4 = estimator.estimate_savings(
        current_assessed_cents=5000000,   # $50,000
        target_assessed_cents=4980000,    # $49,800 (only $200 reduction)
        mill_rate=65.0
    )
    print(savings4)

    # Test 5: No savings (target >= current)
    print("\n\nTest 5: No Savings (Target >= Current)")
    print("-" * 70)
    savings5 = estimator.estimate_savings(
        current_assessed_cents=5000000,   # $50,000
        target_assessed_cents=5500000,    # $55,000
        mill_rate=65.0
    )
    print(savings5)

    # Test 6: Edge case - zero current value
    print("\n\nTest 6: Edge Case - Zero Current Value")
    print("-" * 70)
    savings6 = estimator.estimate_savings(
        current_assessed_cents=0,
        target_assessed_cents=0,
        mill_rate=65.0
    )
    print(savings6)

    # Test 7: Different mill rates comparison
    print("\n\nTest 7: Mill Rate Comparison")
    print("-" * 70)
    reduction_cents = 5000000 - 4500000  # $5,000 reduction
    print(f"Assessed value reduction: ${reduction_cents / 100:,.2f}")
    print()

    for rate in [50.0, 65.0, 80.0]:
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            mill_rate=rate
        )
        print(f"Mill Rate {rate:.0f}: "
              f"Annual savings = ${savings.annual_savings_dollars:,.2f}, "
              f"5-year = ${savings.five_year_savings_dollars:,.2f}")

    # Test 8: Error handling
    print("\n\nTest 8: Error Handling")
    print("-" * 70)

    try:
        estimator_bad = SavingsEstimator(default_mill_rate=-10.0)
    except ValueError as e:
        print(f"Caught expected error (negative mill rate): {e}")

    try:
        estimator.estimate_savings(
            current_assessed_cents=-1000,
            target_assessed_cents=5000000
        )
    except ValueError as e:
        print(f"Caught expected error (negative assessed value): {e}")

    try:
        estimator.estimate_from_fairness(
            current_assessed_cents=5000000,
            current_total_cents=25000000,
            target_ratio=1.5  # Invalid ratio > 1
        )
    except ValueError as e:
        print(f"Caught expected error (invalid ratio): {e}")

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
