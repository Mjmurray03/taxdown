"""
Centralized property ID resolution utilities.

This module provides consistent handling of property identifiers across
all API endpoints. Properties can be identified by either:
- UUID (id column) - e.g., "d3cacc55-8759-495d-a30b-b8206435b7e6"
- Parcel ID - e.g., "15-18321-000"

The AssessmentAnalyzer and other services expect parcel_id, while the
API often receives UUID from the frontend. This module provides utilities
to resolve between the two.
"""

from typing import Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedProperty:
    """Result of property ID resolution."""
    uuid: str
    parcel_id: str
    address: Optional[str] = None
    exists: bool = True


class PropertyResolver:
    """
    Resolves property identifiers between UUID and parcel_id.

    Usage:
        resolver = PropertyResolver(engine)

        # From either ID type
        prop = resolver.resolve("d3cacc55-8759-495d-a30b-b8206435b7e6")
        prop = resolver.resolve("15-18321-000")

        if prop:
            print(f"UUID: {prop.uuid}, Parcel: {prop.parcel_id}")
    """

    def __init__(self, engine):
        self.engine = engine

    def resolve(self, identifier: str) -> Optional[ResolvedProperty]:
        """
        Resolve a property identifier (UUID or parcel_id) to both IDs.

        Args:
            identifier: Either a UUID or parcel_id

        Returns:
            ResolvedProperty with both uuid and parcel_id, or None if not found
        """
        if not identifier:
            return None

        # Try as UUID first (check if it looks like a UUID)
        if self._looks_like_uuid(identifier):
            result = self._lookup_by_uuid(identifier)
            if result:
                return result

        # Try as parcel_id
        result = self._lookup_by_parcel_id(identifier)
        if result:
            return result

        # If looks like UUID but not found, don't try as parcel_id
        if self._looks_like_uuid(identifier):
            return None

        return None

    def get_parcel_id(self, identifier: str) -> Optional[str]:
        """
        Get parcel_id from any identifier type.

        This is the most common operation - services usually need parcel_id.
        """
        resolved = self.resolve(identifier)
        return resolved.parcel_id if resolved else None

    def get_uuid(self, identifier: str) -> Optional[str]:
        """Get UUID from any identifier type."""
        resolved = self.resolve(identifier)
        return resolved.uuid if resolved else None

    def _looks_like_uuid(self, s: str) -> bool:
        """Check if string looks like a UUID."""
        # UUIDs are 36 chars with 4 hyphens: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        if len(s) == 36 and s.count('-') == 4:
            parts = s.split('-')
            if len(parts) == 5 and all(len(p) in [8, 4, 4, 4, 12] for p in parts):
                try:
                    # Verify it's valid hex
                    int(s.replace('-', ''), 16)
                    return True
                except ValueError:
                    pass
        return False

    def _lookup_by_uuid(self, uuid: str) -> Optional[ResolvedProperty]:
        """Look up property by UUID."""
        query = text("""
            SELECT id, parcel_id, ph_add as address
            FROM properties
            WHERE id::text = :uuid
            LIMIT 1
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"uuid": uuid})
            row = result.mappings().first()

            if row:
                return ResolvedProperty(
                    uuid=str(row["id"]),
                    parcel_id=row["parcel_id"],
                    address=row["address"]
                )
        return None

    def _lookup_by_parcel_id(self, parcel_id: str) -> Optional[ResolvedProperty]:
        """Look up property by parcel_id."""
        query = text("""
            SELECT id, parcel_id, ph_add as address
            FROM properties
            WHERE parcel_id = :parcel_id
            LIMIT 1
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"parcel_id": parcel_id})
            row = result.mappings().first()

            if row:
                return ResolvedProperty(
                    uuid=str(row["id"]),
                    parcel_id=row["parcel_id"],
                    address=row["address"]
                )
        return None


# Convenience functions for use without instantiating the class

def resolve_to_parcel_id(engine, identifier: str) -> Optional[str]:
    """
    Resolve any property identifier to parcel_id.

    This is the main function to use when you need parcel_id for services.

    Args:
        engine: SQLAlchemy engine
        identifier: UUID or parcel_id

    Returns:
        parcel_id string or None if not found
    """
    return PropertyResolver(engine).get_parcel_id(identifier)


def resolve_to_uuid(engine, identifier: str) -> Optional[str]:
    """
    Resolve any property identifier to UUID.

    Args:
        engine: SQLAlchemy engine
        identifier: UUID or parcel_id

    Returns:
        UUID string or None if not found
    """
    return PropertyResolver(engine).get_uuid(identifier)


def resolve_property(engine, identifier: str) -> Optional[ResolvedProperty]:
    """
    Fully resolve a property identifier to both UUID and parcel_id.

    Args:
        engine: SQLAlchemy engine
        identifier: UUID or parcel_id

    Returns:
        ResolvedProperty with both IDs, or None if not found
    """
    return PropertyResolver(engine).resolve(identifier)
