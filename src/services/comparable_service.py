"""
Comparable Property Matching Service for Taxdown Assessment Analyzer.

This service implements the SALES COMPARISON APPROACH used by Benton County
to find truly comparable properties for assessment fairness analysis.

KEY PRINCIPLES (from County methodology):
1. SAME SUBDIVISION/NEIGHBORHOOD is the most important factor
2. Similar property characteristics (type, size, improvements)
3. Properties should have similar physical attributes
4. Location/neighborhood context matters significantly

Matching Criteria (in priority order):
1. Same subdivision (REQUIRED if subject has subdivision)
2. Same property type (RI, RV, CI, etc.)
3. Similar lot size (acre_area within ±50%)
4. Similar improvement value (imp_val_cents within ±50%)
5. Similar total value range (within 2x)
6. Geographic proximity as final fallback

A property may be OVER-ASSESSED if its total market value is significantly
HIGHER than comparable properties with similar characteristics in the same area.

Usage:
    from services import ComparableService
    from config import get_engine

    engine = get_engine()
    service = ComparableService(engine)

    # Find truly comparable properties
    comparables = service.find_comparables("16-26005-000")

    # Each comparable has total_val_cents that can be compared
    # to the subject property to determine fairness
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError


# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class ServiceError(Exception):
    """Base exception for service layer errors."""
    pass


class PropertyNotFoundError(ServiceError):
    """Raised when a property cannot be found in the database."""

    def __init__(self, property_id: str):
        self.property_id = property_id
        super().__init__(f"Property not found: {property_id}")


class DatabaseError(ServiceError):
    """Raised when a database operation fails."""
    pass


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ComparableProperty:
    """
    Represents a comparable property with similarity metrics.

    Attributes:
        id: Unique parcel identifier
        parcel_id: Original parcel ID (same as id, for clarity)
        address: Physical address of the property
        total_val_cents: Total market value in cents
        assess_val_cents: Assessed value for tax purposes in cents
        land_val_cents: Land value in cents
        imp_val_cents: Improvement/building value in cents
        assessment_ratio: Assessed value as % of total value (0-100)
        acreage: Property size in acres
        property_type: Property type code (RI, RV, AV, etc.)
        subdivision: Subdivision name (optional)
        owner_name: Property owner name
        distance_miles: Distance from target property (0 for subdivision matches)
        match_type: SUBDIVISION or PROXIMITY
        similarity_score: Overall similarity score (0-100, higher is better)
        value_difference_pct: % difference in total value from target
        acreage_difference_pct: % difference in acreage from target
        type_match_score: Type matching component (0-100)
        value_match_score: Value matching component (0-100)
        acreage_match_score: Acreage matching component (0-100)
        location_score: Location matching component (0-100)
    """
    id: str
    parcel_id: str
    address: str
    total_val_cents: int
    assess_val_cents: int
    land_val_cents: int
    imp_val_cents: int
    assessment_ratio: float
    acreage: float
    property_type: str
    subdivision: Optional[str]
    owner_name: Optional[str]
    distance_miles: float
    match_type: str
    similarity_score: float
    value_difference_pct: float
    acreage_difference_pct: float
    type_match_score: float
    value_match_score: float
    acreage_match_score: float
    location_score: float

    @property
    def total_val_dollars(self) -> float:
        """Total market value in dollars."""
        return self.total_val_cents / 100.0

    @property
    def assess_val_dollars(self) -> float:
        """Assessed value in dollars."""
        return self.assess_val_cents / 100.0

    @property
    def is_subdivision_match(self) -> bool:
        """True if this is a subdivision match."""
        return self.match_type == "SUBDIVISION"

    @property
    def is_proximity_match(self) -> bool:
        """True if this is a proximity match."""
        return self.match_type == "PROXIMITY"


@dataclass
class PropertyCriteria:
    """
    Criteria for finding comparable properties.

    Used when searching without a specific property ID, allowing
    manual specification of the target property characteristics.

    Attributes:
        total_val_cents: Target total market value in cents
        acreage: Target property size in acres
        property_type: Target property type code (RI, RV, AV, etc.)
        subdivision: Target subdivision name (optional)
        latitude: Property latitude (WGS84/EPSG:4326)
        longitude: Property longitude (WGS84/EPSG:4326)
    """
    total_val_cents: int
    acreage: float
    property_type: str
    subdivision: Optional[str]
    latitude: float
    longitude: float

    def validate(self) -> None:
        """
        Validate criteria values.

        Raises:
            ValueError: If any criteria is invalid
        """
        if self.total_val_cents <= 0:
            raise ValueError("total_val_cents must be positive")
        if self.acreage <= 0:
            raise ValueError("acreage must be positive")
        if not self.property_type or len(self.property_type.strip()) == 0:
            raise ValueError("property_type cannot be empty")
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")


# ============================================================================
# SERVICE CONFIGURATION
# ============================================================================

@dataclass
class ComparableConfig:
    """Configuration for comparable property matching."""
    min_comparables: int = 5
    max_comparables: int = 20
    radius_miles: float = 0.5
    value_tolerance: float = 0.20  # ±20%
    acreage_tolerance: float = 0.25  # ±25%


# ============================================================================
# COMPARABLE SERVICE
# ============================================================================

class ComparableService:
    """
    Service for finding comparable properties for assessment analysis.

    This service provides a clean Python API over the PostgreSQL/PostGIS
    comparable matching function. It handles property lookups, similarity
    scoring, and error handling.

    Example:
        engine = get_engine()
        service = ComparableService(engine)

        # Find comparables for a specific property
        comparables = service.find_comparables("16-26005-000", limit=20)

        for comp in comparables:
            print(f"{comp.address}: {comp.similarity_score:.1f}% similar")
            print(f"  Assessment ratio: {comp.assessment_ratio:.2f}%")
            print(f"  Distance: {comp.distance_miles:.2f} miles")
    """

    def __init__(
        self,
        db_connection: Engine | Connection,
        config: Optional[ComparableConfig] = None
    ):
        """
        Initialize the comparable service.

        Args:
            db_connection: SQLAlchemy Engine or Connection
            config: Optional configuration (uses defaults if not provided)
        """
        self.db = db_connection
        self.config = config or ComparableConfig()
        logger.info("ComparableService initialized")

    def find_comparables(
        self,
        property_id: str,
        limit: int = 20
    ) -> List[ComparableProperty]:
        """
        Find truly comparable properties using the SALES COMPARISON APPROACH.

        This method implements county assessment methodology:
        1. Same subdivision is CRITICAL (properties in same neighborhood)
        2. Same property type (residential, commercial, etc.)
        3. Similar lot size (within ±50%)
        4. Similar improvement value (indicates similar building quality/size)
        5. Geographic proximity as fallback for properties without subdivision

        The goal is to find properties that the county would consider
        "comparable" for assessment purposes - same neighborhood, similar
        characteristics.

        Args:
            property_id: The parcel ID to find comparables for
            limit: Maximum number of comparables to return (1-50)

        Returns:
            List of ComparableProperty objects, sorted by similarity score
            (highest first). Returns empty list if no comparables found.

        Raises:
            PropertyNotFoundError: If the property doesn't exist or is invalid
            DatabaseError: If database operation fails
            ValueError: If limit is out of range
        """
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        logger.info(f"Finding comparables for property: {property_id} (limit={limit})")

        try:
            # Sales Comparison Approach Query
            # Priority: Same subdivision > Same type > Similar size > Similar improvements
            query = text("""
                WITH subject AS (
                    SELECT
                        id,
                        parcel_id,
                        type_,
                        subdivname,
                        acre_area,
                        total_val_cents,
                        assess_val_cents,
                        land_val_cents,
                        imp_val_cents,
                        geometry
                    FROM properties
                    WHERE parcel_id = :parcel_id
                      AND is_active = true
                    LIMIT 1
                ),

                -- Find comparables prioritizing subdivision match
                comparables AS (
                    SELECT
                        p.parcel_id AS comparable_parcelid,
                        p.ph_add AS property_address,
                        p.total_val_cents AS total_value,
                        p.assess_val_cents AS assess_value,
                        p.land_val_cents AS land_value,
                        p.imp_val_cents AS imp_value,
                        p.acre_area,
                        p.type_ AS property_type,
                        p.ow_name AS owner_name,
                        p.subdivname AS subdivision,

                        -- Match type: SUBDIVISION or PROXIMITY
                        CASE
                            WHEN p.subdivname = s.subdivname AND p.subdivname IS NOT NULL
                            THEN 'SUBDIVISION'
                            ELSE 'PROXIMITY'
                        END AS match_type,

                        -- Calculate distance (0 for subdivision matches)
                        CASE
                            WHEN p.subdivname = s.subdivname AND p.subdivname IS NOT NULL THEN 0.0
                            WHEN p.geometry IS NOT NULL AND s.geometry IS NOT NULL THEN
                                ST_Distance(
                                    ST_Transform(p.geometry, 4326)::geography,
                                    ST_Transform(s.geometry, 4326)::geography
                                ) * 0.000621371  -- meters to miles
                            ELSE 999.0
                        END AS distance_miles,

                        -- Assessment ratio (always ~20% but include for reference)
                        CASE
                            WHEN p.total_val_cents > 0
                            THEN ROUND((p.assess_val_cents::numeric / p.total_val_cents::numeric) * 100, 2)
                            ELSE 0
                        END AS assessment_ratio,

                        -- Value difference percentage
                        CASE
                            WHEN s.total_val_cents > 0
                            THEN ROUND(ABS(p.total_val_cents - s.total_val_cents)::numeric / s.total_val_cents * 100, 2)
                            ELSE 0
                        END AS value_difference_pct,

                        -- Acreage difference percentage
                        CASE
                            WHEN s.acre_area > 0.01
                            THEN ROUND(ABS(p.acre_area::numeric - s.acre_area::numeric) / s.acre_area::numeric * 100, 2)
                            ELSE 0
                        END AS acreage_difference_pct,

                        -- Improvement value difference percentage
                        CASE
                            WHEN s.imp_val_cents > 0
                            THEN ROUND(ABS(p.imp_val_cents - s.imp_val_cents)::numeric / s.imp_val_cents * 100, 2)
                            ELSE 0
                        END AS imp_difference_pct,

                        -- SCORING COMPONENTS
                        -- Type match: 100 if same type
                        CASE WHEN p.type_ = s.type_ THEN 100.0 ELSE 0.0 END AS type_match_score,

                        -- Value similarity score (closer = higher score)
                        GREATEST(0, 100 - (
                            CASE
                                WHEN s.total_val_cents > 0
                                THEN ABS(p.total_val_cents - s.total_val_cents)::numeric / s.total_val_cents * 100
                                ELSE 100
                            END
                        )) AS value_match_score,

                        -- Acreage similarity score
                        GREATEST(0, 100 - (
                            CASE
                                WHEN s.acre_area > 0.01
                                THEN ABS(p.acre_area::numeric - s.acre_area::numeric) / s.acre_area::numeric * 100
                                ELSE 100
                            END
                        )) AS acreage_match_score,

                        -- Location score (subdivision match = 100, proximity decreases with distance)
                        CASE
                            WHEN p.subdivname = s.subdivname AND p.subdivname IS NOT NULL THEN 100.0
                            WHEN p.geometry IS NOT NULL AND s.geometry IS NOT NULL THEN
                                GREATEST(0, 100 - (
                                    ST_Distance(
                                        ST_Transform(p.geometry, 4326)::geography,
                                        ST_Transform(s.geometry, 4326)::geography
                                    ) * 0.000621371 * 50  -- Penalize distance
                                ))
                            ELSE 0.0
                        END AS location_score,

                        -- Improvement similarity score (key for sales comparison)
                        GREATEST(0, 100 - (
                            CASE
                                WHEN s.imp_val_cents > 0
                                THEN ABS(p.imp_val_cents - s.imp_val_cents)::numeric / s.imp_val_cents * 100
                                ELSE
                                    CASE WHEN p.imp_val_cents > 0 THEN 100 ELSE 0 END
                            END
                        )) AS improvement_match_score

                    FROM properties p, subject s
                    WHERE p.parcel_id != s.parcel_id
                      AND p.is_active = true
                      AND p.total_val_cents > 0
                      -- MUST be same property type
                      AND p.type_ = s.type_
                      -- Either same subdivision OR within reasonable value range
                      AND (
                          -- Same subdivision: relax other constraints
                          (p.subdivname = s.subdivname AND p.subdivname IS NOT NULL)
                          OR
                          -- Different subdivision: must be similar size and value
                          (
                              p.acre_area BETWEEN s.acre_area * 0.5 AND s.acre_area * 2.0
                              AND p.total_val_cents BETWEEN s.total_val_cents * 0.3 AND s.total_val_cents * 3.0
                          )
                      )
                )

                SELECT
                    c.comparable_parcelid,
                    c.match_type,
                    ROUND(c.distance_miles::numeric, 3)::float AS distance_miles,
                    -- Overall similarity score (weighted)
                    ROUND((
                        c.type_match_score::numeric * 0.05 +        -- 5% type (already filtered)
                        c.location_score::numeric * 0.35 +          -- 35% location (subdivision is key)
                        c.value_match_score::numeric * 0.20 +       -- 20% value similarity
                        c.acreage_match_score::numeric * 0.15 +     -- 15% lot size
                        c.improvement_match_score::numeric * 0.25   -- 25% improvement value
                    ), 2)::float AS similarity_score,
                    c.total_value,
                    c.assess_value,
                    c.land_value,
                    c.imp_value,
                    ROUND(c.acre_area::numeric, 3)::float AS acre_area,
                    c.property_type,
                    c.owner_name,
                    c.property_address,
                    c.subdivision,
                    c.assessment_ratio::float AS assessment_ratio,
                    c.value_difference_pct::float AS value_difference_pct,
                    c.acreage_difference_pct::float AS acreage_difference_pct,
                    ROUND(c.type_match_score::numeric, 2)::float AS type_match_score,
                    ROUND(c.value_match_score::numeric, 2)::float AS value_match_score,
                    ROUND(c.acreage_match_score::numeric, 2)::float AS acreage_match_score,
                    ROUND(c.location_score::numeric, 2)::float AS location_score
                FROM comparables c
                ORDER BY
                    -- Prioritize subdivision matches
                    CASE WHEN c.match_type = 'SUBDIVISION' THEN 0 ELSE 1 END,
                    -- Then by overall similarity
                    (c.type_match_score * 0.05 + c.location_score * 0.35 +
                     c.value_match_score * 0.20 + c.acreage_match_score * 0.15 +
                     c.improvement_match_score * 0.25) DESC
                LIMIT :limit
            """)

            with self._get_connection() as conn:
                result = conn.execute(
                    query,
                    {"parcel_id": property_id, "limit": limit}
                )
                rows = result.fetchall()

            # If no results, check if property exists
            if not rows:
                if not self._property_exists(property_id):
                    raise PropertyNotFoundError(property_id)

                logger.warning(
                    f"No comparables found for property {property_id}. "
                    "Property may have unusual characteristics or be isolated."
                )
                return []

            # Convert to ComparableProperty objects
            comparables = [self._row_to_comparable(row) for row in rows]

            logger.info(
                f"Found {len(comparables)} comparables for {property_id}. "
                f"Avg similarity: {sum(c.similarity_score for c in comparables) / len(comparables):.1f}%"
            )

            return comparables

        except PropertyNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error finding comparables: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error finding comparables: {e}")
            raise ServiceError(f"Service error: {str(e)}") from e

    def find_comparables_by_criteria(
        self,
        criteria: PropertyCriteria,
        limit: int = 20
    ) -> List[ComparableProperty]:
        """
        Find comparable properties based on manual criteria.

        This method is useful when you don't have a property ID but want
        to find comparables based on specific characteristics (e.g., for
        hypothetical property analysis or external data integration).

        Args:
            criteria: PropertyCriteria specifying target characteristics
            limit: Maximum number of comparables to return (1-50)

        Returns:
            List of ComparableProperty objects, sorted by similarity score

        Raises:
            ValueError: If criteria is invalid
            DatabaseError: If database operation fails
        """
        criteria.validate()

        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        logger.info(
            f"Finding comparables by criteria: type={criteria.property_type}, "
            f"value=${criteria.total_val_cents/100:,.0f}, "
            f"acres={criteria.acreage:.2f}"
        )

        try:
            # Build inline query based on the SQL function logic
            # NOTE: All numeric calculations must be cast to NUMERIC for ROUND() to work
            # Use CAST() syntax instead of :: to avoid SQLAlchemy parameter parsing issues
            query = text("""
                WITH target_property AS (
                    SELECT
                        :property_type AS type_,
                        CAST(:total_val_cents AS BIGINT) AS total_val_cents,
                        CAST(:acreage AS NUMERIC) AS acre_area,
                        :subdivision AS subdivname,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS point_geom
                ),

                all_candidates AS (
                    -- Subdivision matches
                    SELECT
                        p.parcel_id,
                        CAST('SUBDIVISION' AS VARCHAR) AS match_type,
                        CAST(0.0 AS NUMERIC) AS distance_miles,
                        p.type_,
                        p.total_val_cents,
                        p.assess_val_cents,
                        p.land_val_cents,
                        p.imp_val_cents,
                        CAST(p.acre_area AS NUMERIC) AS acre_area,
                        p.ow_name,
                        p.ph_add,
                        p.subdivname,
                        p.geometry
                    FROM properties p, target_property t
                    WHERE p.subdivname = t.subdivname
                        AND p.subdivname IS NOT NULL
                        AND p.type_ = t.type_
                        AND p.total_val_cents BETWEEN t.total_val_cents * 0.80 AND t.total_val_cents * 1.20
                        AND p.acre_area BETWEEN t.acre_area * 0.75 AND t.acre_area * 1.25
                        AND p.total_val_cents > 0
                        AND p.acre_area > 0

                    UNION ALL

                    -- Proximity matches (fallback)
                    SELECT
                        p.parcel_id,
                        CAST('PROXIMITY' AS VARCHAR) AS match_type,
                        CAST(ST_Distance(
                            CAST(ST_Transform(p.geometry, 4326) AS geography),
                            CAST(t.point_geom AS geography)
                        ) * 0.000621371 AS NUMERIC) AS distance_miles,
                        p.type_,
                        p.total_val_cents,
                        p.assess_val_cents,
                        p.land_val_cents,
                        p.imp_val_cents,
                        CAST(p.acre_area AS NUMERIC) AS acre_area,
                        p.ow_name,
                        p.ph_add,
                        p.subdivname,
                        p.geometry
                    FROM properties p, target_property t
                    WHERE ST_DWithin(
                            CAST(ST_Transform(p.geometry, 4326) AS geography),
                            CAST(t.point_geom AS geography),
                            804.67  -- 0.5 miles in meters
                        )
                        AND p.type_ = t.type_
                        AND p.total_val_cents BETWEEN t.total_val_cents * 0.80 AND t.total_val_cents * 1.20
                        AND p.acre_area BETWEEN t.acre_area * 0.75 AND t.acre_area * 1.25
                        AND p.total_val_cents > 0
                        AND p.acre_area > 0
                ),

                scored_comparables AS (
                    SELECT
                        ac.parcel_id,
                        ac.match_type,
                        ac.distance_miles,
                        ac.total_val_cents,
                        ac.assess_val_cents,
                        ac.land_val_cents,
                        ac.imp_val_cents,
                        ac.acre_area,
                        ac.type_,
                        ac.ow_name,
                        ac.ph_add,
                        ac.subdivname,

                        -- Assessment ratio
                        CASE
                            WHEN ac.total_val_cents > 0 THEN
                                ROUND(CAST(ac.assess_val_cents AS NUMERIC) / CAST(ac.total_val_cents AS NUMERIC) * 100, 2)
                            ELSE CAST(0 AS NUMERIC)
                        END AS assessment_ratio,

                        -- Difference percentages
                        ROUND(
                            CAST(ABS(ac.total_val_cents - CAST(:total_val_cents AS BIGINT)) AS NUMERIC) /
                            NULLIF(CAST(:total_val_cents AS NUMERIC), 0) * 100,
                            2
                        ) AS value_difference_pct,

                        ROUND(
                            ABS(ac.acre_area - CAST(:acreage AS NUMERIC)) /
                            NULLIF(CAST(:acreage AS NUMERIC), 0) * 100,
                            2
                        ) AS acreage_difference_pct,

                        -- Score components (all cast to NUMERIC for ROUND)
                        CAST(100.0 AS NUMERIC) AS type_match_score,

                        GREATEST(CAST(0 AS NUMERIC), CAST(100 AS NUMERIC) - (
                            CAST(ABS(ac.total_val_cents - CAST(:total_val_cents AS BIGINT)) AS NUMERIC) /
                            NULLIF(CAST(:total_val_cents AS NUMERIC), 0) * 100 * 5
                        )) AS value_match_score,

                        GREATEST(CAST(0 AS NUMERIC), CAST(100 AS NUMERIC) - (
                            ABS(ac.acre_area - CAST(:acreage AS NUMERIC)) /
                            NULLIF(CAST(:acreage AS NUMERIC), 0) * 100 * 4
                        )) AS acreage_match_score,

                        CASE
                            WHEN ac.match_type = 'SUBDIVISION' THEN CAST(100.0 AS NUMERIC)
                            WHEN ac.match_type = 'PROXIMITY' THEN
                                GREATEST(CAST(0 AS NUMERIC), CAST(100 AS NUMERIC) - (ac.distance_miles * 200))
                            ELSE CAST(0 AS NUMERIC)
                        END AS location_score
                    FROM all_candidates ac
                )

                SELECT
                    sc.parcel_id AS comparable_parcelid,
                    sc.match_type,
                    ROUND(sc.distance_miles, 3) AS distance_miles,

                    -- Weighted similarity score
                    ROUND(
                        (sc.type_match_score * 0.10) +
                        (sc.value_match_score * 0.35) +
                        (sc.acreage_match_score * 0.30) +
                        (sc.location_score * 0.25),
                        2
                    ) AS similarity_score,

                    sc.total_val_cents AS total_value,
                    sc.assess_val_cents AS assess_value,
                    sc.land_val_cents AS land_value,
                    sc.imp_val_cents AS imp_value,
                    ROUND(sc.acre_area, 2) AS acre_area,
                    sc.type_ AS property_type,
                    sc.ow_name AS owner_name,
                    sc.ph_add AS property_address,
                    sc.subdivname AS subdivision,
                    sc.assessment_ratio,
                    sc.value_difference_pct,
                    sc.acreage_difference_pct,
                    ROUND(sc.type_match_score, 2) AS type_match_score,
                    ROUND(sc.value_match_score, 2) AS value_match_score,
                    ROUND(sc.acreage_match_score, 2) AS acreage_match_score,
                    ROUND(sc.location_score, 2) AS location_score

                FROM scored_comparables sc
                ORDER BY similarity_score DESC, sc.distance_miles ASC
                LIMIT :limit
            """)

            with self._get_connection() as conn:
                result = conn.execute(
                    query,
                    {
                        "property_type": criteria.property_type,
                        "total_val_cents": criteria.total_val_cents,
                        "acreage": criteria.acreage,
                        "subdivision": criteria.subdivision,
                        "latitude": criteria.latitude,
                        "longitude": criteria.longitude,
                        "limit": limit
                    }
                )
                rows = result.fetchall()

            if not rows:
                logger.warning(
                    f"No comparables found for criteria: {criteria.property_type}, "
                    f"${criteria.total_val_cents/100:,.0f}, {criteria.acreage:.2f} acres"
                )
                return []

            comparables = [self._row_to_comparable(row) for row in rows]

            logger.info(
                f"Found {len(comparables)} comparables by criteria. "
                f"Avg similarity: {sum(c.similarity_score for c in comparables) / len(comparables):.1f}%"
            )

            return comparables

        except SQLAlchemyError as e:
            logger.error(f"Database error finding comparables by criteria: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error finding comparables by criteria: {e}")
            raise ServiceError(f"Service error: {str(e)}") from e

    def get_property_summary(self, property_id: str) -> Dict[str, Any]:
        """
        Get a summary of a property including its comparables.

        Args:
            property_id: The parcel ID to analyze

        Returns:
            Dictionary containing property info and comparable statistics

        Raises:
            PropertyNotFoundError: If property doesn't exist
            DatabaseError: If database operation fails
        """
        logger.info(f"Getting property summary for {property_id}")

        try:
            # Get property details
            property_query = text("""
                SELECT
                    parcel_id,
                    type_ AS property_type,
                    total_val_cents,
                    assess_val_cents,
                    acre_area,
                    ph_add AS address,
                    subdivname AS subdivision,
                    ow_name AS owner_name,
                    CASE
                        WHEN total_val_cents > 0 THEN
                            ROUND((assess_val_cents::NUMERIC / total_val_cents::NUMERIC) * 100, 2)
                        ELSE 0
                    END AS assessment_ratio
                FROM properties
                WHERE parcel_id = :parcel_id
            """)

            with self._get_connection() as conn:
                result = conn.execute(property_query, {"parcel_id": property_id})
                property_row = result.fetchone()

            if not property_row:
                raise PropertyNotFoundError(property_id)

            # Get comparables
            comparables = self.find_comparables(property_id)

            # Calculate statistics
            if comparables:
                avg_assessment_ratio = sum(c.assessment_ratio for c in comparables) / len(comparables)
                avg_similarity = sum(c.similarity_score for c in comparables) / len(comparables)
                subdivision_count = sum(1 for c in comparables if c.is_subdivision_match)
                proximity_count = sum(1 for c in comparables if c.is_proximity_match)

                target_ratio = float(property_row.assessment_ratio) if property_row.assessment_ratio else 0.0
                ratio_diff = target_ratio - avg_assessment_ratio

                # Determine fairness assessment
                if ratio_diff > 5:
                    fairness = "OVER-ASSESSED"
                elif ratio_diff < -5:
                    fairness = "UNDER-ASSESSED"
                else:
                    fairness = "FAIR"
            else:
                avg_assessment_ratio = None
                avg_similarity = None
                subdivision_count = 0
                proximity_count = 0
                ratio_diff = None
                fairness = "INSUFFICIENT_DATA"

            return {
                "property": {
                    "parcel_id": property_row.parcel_id,
                    "property_type": property_row.property_type,
                    "total_value": property_row.total_val_cents,
                    "assess_value": property_row.assess_val_cents,
                    "acreage": float(property_row.acre_area) if property_row.acre_area else None,
                    "address": property_row.address,
                    "subdivision": property_row.subdivision,
                    "owner_name": property_row.owner_name,
                    "assessment_ratio": float(property_row.assessment_ratio),
                },
                "comparables": {
                    "count": len(comparables),
                    "subdivision_matches": subdivision_count,
                    "proximity_matches": proximity_count,
                    "avg_similarity_score": round(avg_similarity, 2) if avg_similarity else None,
                    "avg_assessment_ratio": round(avg_assessment_ratio, 2) if avg_assessment_ratio else None,
                },
                "assessment": {
                    "fairness": fairness,
                    "ratio_difference": round(ratio_diff, 2) if ratio_diff is not None else None,
                    "explanation": self._get_fairness_explanation(fairness, ratio_diff),
                }
            }

        except PropertyNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting property summary: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting property summary: {e}")
            raise ServiceError(f"Service error: {str(e)}") from e

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

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

    def _property_exists(self, property_id: str) -> bool:
        """Check if a property exists in the database."""
        query = text("""
            SELECT 1
            FROM properties
            WHERE parcel_id = :parcel_id
            LIMIT 1
        """)

        with self._get_connection() as conn:
            result = conn.execute(query, {"parcel_id": property_id})
            return result.fetchone() is not None

    def _row_to_comparable(self, row) -> ComparableProperty:
        """Convert a database row to a ComparableProperty object."""
        return ComparableProperty(
            id=row.comparable_parcelid,
            parcel_id=row.comparable_parcelid,
            address=row.property_address or "",
            total_val_cents=int(row.total_value),
            assess_val_cents=int(row.assess_value),
            land_val_cents=int(row.land_value) if row.land_value else 0,
            imp_val_cents=int(row.imp_value) if row.imp_value else 0,
            assessment_ratio=float(row.assessment_ratio),
            acreage=float(row.acre_area),
            property_type=row.property_type,
            subdivision=row.subdivision,
            owner_name=row.owner_name,
            distance_miles=float(row.distance_miles),
            match_type=row.match_type,
            similarity_score=float(row.similarity_score),
            value_difference_pct=float(row.value_difference_pct),
            acreage_difference_pct=float(row.acreage_difference_pct),
            type_match_score=float(row.type_match_score),
            value_match_score=float(row.value_match_score),
            acreage_match_score=float(row.acreage_match_score),
            location_score=float(row.location_score),
        )

    def _get_fairness_explanation(
        self,
        fairness: str,
        ratio_diff: Optional[float]
    ) -> str:
        """Generate a human-readable explanation of the fairness assessment."""
        if fairness == "OVER-ASSESSED":
            return (
                f"Property is assessed {ratio_diff:.1f}% higher than similar properties, "
                "which may indicate over-assessment."
            )
        elif fairness == "UNDER-ASSESSED":
            return (
                f"Property is assessed {abs(ratio_diff):.1f}% lower than similar properties, "
                "which may indicate under-assessment."
            )
        elif fairness == "FAIR":
            return (
                "Property assessment is within 5% of similar properties, "
                "indicating fair and equitable assessment."
            )
        else:
            return "Insufficient comparable data to assess fairness."
