"""
Test script for ComparableService.

This script demonstrates the usage of the ComparableService and validates
that it works correctly with the database.

Usage:
    python -m src.services.test_comparable_service
"""

import sys
import logging
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_engine
from src.services.comparable_service import (
    ComparableService,
    PropertyCriteria,
    PropertyNotFoundError,
    ServiceError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_find_random_property_comparables():
    """Test finding comparables for a random property with assess_val_cents > 0."""
    logger.info("=" * 80)
    logger.info("TEST 1: Find comparables for a random property")
    logger.info("=" * 80)

    engine = get_engine()
    service = ComparableService(engine)

    # Find a random property with assess_val_cents > 0
    with engine.connect() as conn:
        from sqlalchemy import text

        result = conn.execute(text("""
            SELECT
                parcel_id,
                type_,
                total_val_cents,
                assess_val_cents,
                acre_area,
                ph_add,
                subdivname,
                ST_Y(ST_Transform(ST_Centroid(geometry), 4326)) AS latitude,
                ST_X(ST_Transform(ST_Centroid(geometry), 4326)) AS longitude
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND acre_area > 0
                AND type_ IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 1
        """))

        property_row = result.fetchone()

    if not property_row:
        logger.error("No suitable properties found in database!")
        return False

    property_id = property_row.parcel_id
    logger.info(f"\nSelected Property: {property_id}")
    logger.info(f"  Address: {property_row.ph_add}")
    logger.info(f"  Type: {property_row.type_}")
    logger.info(f"  Total Value: ${property_row.total_val_cents / 100:,.2f}")
    logger.info(f"  Assessed Value: ${property_row.assess_val_cents / 100:,.2f}")
    logger.info(f"  Acreage: {property_row.acre_area:.2f}")
    logger.info(f"  Subdivision: {property_row.subdivname or 'N/A'}")

    try:
        # Find comparables
        comparables = service.find_comparables(property_id, limit=20)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Found {len(comparables)} comparable properties")
        logger.info(f"{'=' * 80}")

        if comparables:
            # Calculate statistics
            avg_similarity = sum(c.similarity_score for c in comparables) / len(comparables)
            avg_ratio = sum(c.assessment_ratio for c in comparables) / len(comparables)
            subdivision_matches = sum(1 for c in comparables if c.is_subdivision_match)
            proximity_matches = sum(1 for c in comparables if c.is_proximity_match)

            logger.info(f"\nComparable Statistics:")
            logger.info(f"  Average Similarity: {avg_similarity:.1f}%")
            logger.info(f"  Average Assessment Ratio: {avg_ratio:.2f}%")
            logger.info(f"  Subdivision Matches: {subdivision_matches}")
            logger.info(f"  Proximity Matches: {proximity_matches}")

            # Display top 5 comparables
            logger.info(f"\nTop 5 Comparable Properties:")
            logger.info(f"{'=' * 80}")

            for i, comp in enumerate(comparables[:5], 1):
                logger.info(f"\n{i}. {comp.parcel_id} ({comp.match_type})")
                logger.info(f"   Address: {comp.address or 'N/A'}")
                logger.info(f"   Similarity Score: {comp.similarity_score:.1f}%")
                logger.info(f"   Total Value: ${comp.total_val_dollars:,.2f} "
                           f"({comp.value_difference_pct:+.1f}% diff)")
                logger.info(f"   Assessment Ratio: {comp.assessment_ratio:.2f}%")
                logger.info(f"   Acreage: {comp.acreage:.2f} "
                           f"({comp.acreage_difference_pct:+.1f}% diff)")
                logger.info(f"   Distance: {comp.distance_miles:.2f} miles")
                logger.info(f"   Score Breakdown:")
                logger.info(f"     - Type: {comp.type_match_score:.0f}%")
                logger.info(f"     - Value: {comp.value_match_score:.0f}%")
                logger.info(f"     - Acreage: {comp.acreage_match_score:.0f}%")
                logger.info(f"     - Location: {comp.location_score:.0f}%")

        return True

    except PropertyNotFoundError as e:
        logger.error(f"Property not found: {e}")
        return False
    except ServiceError as e:
        logger.error(f"Service error: {e}")
        return False


def test_get_property_summary():
    """Test getting a property summary with fairness assessment."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Get property summary with fairness assessment")
    logger.info("=" * 80)

    engine = get_engine()
    service = ComparableService(engine)

    # Find a property with assess_val_cents > 0
    with engine.connect() as conn:
        from sqlalchemy import text

        result = conn.execute(text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND acre_area > 0
                AND type_ IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 1
        """))

        property_row = result.fetchone()

    if not property_row:
        logger.error("No suitable properties found!")
        return False

    property_id = property_row.parcel_id

    try:
        summary = service.get_property_summary(property_id)

        logger.info(f"\nProperty Summary for {property_id}")
        logger.info(f"{'=' * 80}")

        # Property details
        prop = summary["property"]
        logger.info(f"\nProperty Details:")
        logger.info(f"  Address: {prop['address'] or 'N/A'}")
        logger.info(f"  Type: {prop['property_type']}")
        logger.info(f"  Total Value: ${prop['total_value'] / 100:,.2f}")
        logger.info(f"  Assessed Value: ${prop['assess_value'] / 100:,.2f}")
        logger.info(f"  Assessment Ratio: {prop['assessment_ratio']:.2f}%")
        logger.info(f"  Acreage: {prop['acreage']:.2f}" if prop['acreage'] else "  Acreage: N/A")
        logger.info(f"  Subdivision: {prop['subdivision'] or 'N/A'}")
        logger.info(f"  Owner: {prop['owner_name'] or 'N/A'}")

        # Comparable statistics
        comps = summary["comparables"]
        logger.info(f"\nComparable Statistics:")
        logger.info(f"  Total Comparables: {comps['count']}")
        logger.info(f"  Subdivision Matches: {comps['subdivision_matches']}")
        logger.info(f"  Proximity Matches: {comps['proximity_matches']}")

        if comps['avg_similarity_score'] is not None:
            logger.info(f"  Average Similarity: {comps['avg_similarity_score']:.1f}%")
            logger.info(f"  Average Assessment Ratio: {comps['avg_assessment_ratio']:.2f}%")

        # Fairness assessment
        assess = summary["assessment"]
        logger.info(f"\nFairness Assessment:")
        logger.info(f"  Status: {assess['fairness']}")
        if assess['ratio_difference'] is not None:
            logger.info(f"  Ratio Difference: {assess['ratio_difference']:+.2f}%")
        logger.info(f"  Explanation: {assess['explanation']}")

        return True

    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return False


def test_find_by_criteria():
    """Test finding comparables using manual criteria."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Find comparables by manual criteria")
    logger.info("=" * 80)

    engine = get_engine()
    service = ComparableService(engine)

    # Create criteria for a typical residential property
    criteria = PropertyCriteria(
        total_val_cents=50000000,  # $500,000
        acreage=2.5,
        property_type="RI",  # Residential Improved
        subdivision="PLEASANT GROVE",
        latitude=36.3729,
        longitude=-94.2088
    )

    logger.info(f"\nSearch Criteria:")
    logger.info(f"  Property Type: {criteria.property_type}")
    logger.info(f"  Total Value: ${criteria.total_val_cents / 100:,.2f}")
    logger.info(f"  Acreage: {criteria.acreage:.2f}")
    logger.info(f"  Subdivision: {criteria.subdivision or 'N/A'}")
    logger.info(f"  Location: {criteria.latitude:.4f}, {criteria.longitude:.4f}")

    try:
        comparables = service.find_comparables_by_criteria(criteria, limit=10)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Found {len(comparables)} comparable properties")
        logger.info(f"{'=' * 80}")

        if comparables:
            # Display results
            for i, comp in enumerate(comparables[:5], 1):
                logger.info(f"\n{i}. {comp.parcel_id} ({comp.match_type})")
                logger.info(f"   Similarity: {comp.similarity_score:.1f}%")
                logger.info(f"   Value: ${comp.total_val_dollars:,.2f}")
                logger.info(f"   Acreage: {comp.acreage:.2f}")
                logger.info(f"   Distance: {comp.distance_miles:.2f} miles")
        else:
            logger.warning("No comparables found for the specified criteria")

        return True

    except Exception as e:
        logger.error(f"Error finding comparables by criteria: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting ComparableService Tests")
    logger.info("=" * 80)

    tests = [
        ("Find Random Property Comparables", test_find_random_property_comparables),
        ("Get Property Summary", test_get_property_summary),
        ("Find By Criteria", test_find_by_criteria),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with exception: {e}", exc_info=True)
            results.append((test_name, False))

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        logger.info(f"{test_name}: {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
