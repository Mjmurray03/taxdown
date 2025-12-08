"""
Portfolio Service for Taxdown.

Provides comprehensive portfolio management including:
- User management
- Portfolio CRUD operations
- Portfolio property management
- Portfolio analytics and dashboard data
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class User:
    """User account data."""
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: str = "INVESTOR"
    subscription_tier: str = "FREE"
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


@dataclass
class Portfolio:
    """Portfolio data."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    default_mill_rate: float = 65.0
    auto_analyze: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Computed fields
    property_count: int = 0
    total_market_value_cents: Optional[int] = None
    total_assessed_value_cents: Optional[int] = None
    estimated_annual_tax_cents: Optional[int] = None
    total_potential_savings_cents: Optional[int] = None
    appeal_candidates: int = 0


@dataclass
class PortfolioProperty:
    """Portfolio property data with analysis."""
    id: UUID
    portfolio_id: UUID
    property_id: UUID
    parcel_id: str
    address: Optional[str] = None
    city: Optional[str] = None
    owner_name: Optional[str] = None
    ownership_type: str = "TRACKING"
    ownership_percentage: float = 100.0
    purchase_date: Optional[date] = None
    purchase_price_cents: Optional[int] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_primary_residence: bool = False
    added_at: Optional[datetime] = None
    # Property values
    market_value_cents: Optional[int] = None
    assessed_value_cents: Optional[int] = None
    estimated_annual_tax_cents: Optional[int] = None
    # Analysis results
    fairness_score: Optional[int] = None
    recommended_action: Optional[str] = None
    estimated_savings_cents: Optional[int] = None
    last_analyzed: Optional[datetime] = None


@dataclass
class PortfolioSummary:
    """Summary statistics for a portfolio."""
    total_properties: int = 0
    total_market_value_cents: int = 0
    total_assessed_value_cents: int = 0
    estimated_annual_tax_cents: int = 0
    total_potential_savings_cents: int = 0
    appeal_candidates: int = 0
    average_fairness_score: Optional[float] = None
    by_ownership_type: Dict[str, int] = field(default_factory=dict)
    by_city: Dict[str, int] = field(default_factory=dict)
    by_recommendation: Dict[str, int] = field(default_factory=dict)


@dataclass
class DashboardData:
    """Portfolio dashboard data."""
    summary: PortfolioSummary
    top_savings: List[PortfolioProperty]
    top_over_assessed: List[PortfolioProperty]
    recent_analyses: List[Dict[str, Any]]


@dataclass
class AnalysisResult:
    """Bulk analysis result."""
    total_properties: int = 0
    analyzed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    appeal_candidates: int = 0
    total_savings_cents: int = 0
    duration_seconds: float = 0.0


@dataclass
class AppealCandidate:
    """Appeal candidate property."""
    property_id: UUID
    parcel_id: str
    address: Optional[str] = None
    fairness_score: int = 0
    confidence_level: int = 0
    estimated_savings_cents: int = 0


# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================


class PortfolioService:
    """Service for managing portfolios and their properties."""

    def __init__(self, engine: Engine):
        self.engine = engine

    # ==================== USER MANAGEMENT ====================

    def create_user(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        user_type: str = "INVESTOR",
    ) -> User:
        """Create a new user."""
        with self.engine.connect() as conn:
            # Check for existing user
            check = text("SELECT id FROM users WHERE email = :email")
            if conn.execute(check, {"email": email}).first():
                raise ValueError(f"User with email {email} already exists")

            query = text("""
                INSERT INTO users (email, password_hash, first_name, last_name, phone, user_type)
                VALUES (:email, :password_hash, :first_name, :last_name, :phone, :user_type)
                RETURNING id, email, first_name, last_name, phone, user_type,
                          subscription_tier, created_at, last_login
            """)

            result = conn.execute(query, {
                "email": email,
                "password_hash": "api_created_placeholder",
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "user_type": user_type,
            })
            row = result.mappings().first()
            conn.commit()

            return User(
                id=row["id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                phone=row["phone"],
                user_type=row["user_type"],
                subscription_tier=row["subscription_tier"],
                created_at=row["created_at"],
                last_login=row["last_login"],
            )

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT id, email, first_name, last_name, phone, user_type,
                       subscription_tier, created_at, last_login
                FROM users
                WHERE id::text = :user_id AND is_active = true
            """)
            row = conn.execute(query, {"user_id": user_id}).mappings().first()

            if not row:
                return None

            return User(
                id=row["id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                phone=row["phone"],
                user_type=row["user_type"],
                subscription_tier=row["subscription_tier"],
                created_at=row["created_at"],
                last_login=row["last_login"],
            )

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT id, email, first_name, last_name, phone, user_type,
                       subscription_tier, created_at, last_login
                FROM users
                WHERE email = :email AND is_active = true
            """)
            row = conn.execute(query, {"email": email}).mappings().first()

            if not row:
                return None

            return User(
                id=row["id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                phone=row["phone"],
                user_type=row["user_type"],
                subscription_tier=row["subscription_tier"],
                created_at=row["created_at"],
                last_login=row["last_login"],
            )

    # ==================== PORTFOLIO CRUD ====================

    def create_portfolio(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        default_mill_rate: float = 65.0,
        auto_analyze: bool = True,
    ) -> Portfolio:
        """Create a new portfolio."""
        with self.engine.connect() as conn:
            # Verify user exists
            user_check = text("SELECT id FROM users WHERE id::text = :user_id AND is_active = true")
            if not conn.execute(user_check, {"user_id": user_id}).first():
                raise ValueError("User not found")

            # Check for duplicate name
            name_check = text("""
                SELECT id FROM portfolios
                WHERE user_id::text = :user_id AND name = :name AND is_active = true
            """)
            if conn.execute(name_check, {"user_id": user_id, "name": name}).first():
                raise ValueError("Portfolio with this name already exists")

            query = text("""
                INSERT INTO portfolios (user_id, name, description, default_mill_rate, auto_analyze)
                VALUES (:user_id::uuid, :name, :description, :mill_rate, :auto_analyze)
                RETURNING id, user_id, name, description, default_mill_rate, auto_analyze,
                          created_at, updated_at
            """)

            result = conn.execute(query, {
                "user_id": user_id,
                "name": name,
                "description": description,
                "mill_rate": default_mill_rate,
                "auto_analyze": auto_analyze,
            })
            row = result.mappings().first()
            conn.commit()

            return Portfolio(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                default_mill_rate=float(row["default_mill_rate"]),
                auto_analyze=row["auto_analyze"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID with summary statistics."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT
                    p.id, p.user_id, p.name, p.description,
                    p.default_mill_rate, p.auto_analyze,
                    p.created_at, p.updated_at,
                    COUNT(pp.id) as property_count,
                    COALESCE(SUM(prop.total_val_cents), 0) as total_market_cents,
                    COALESCE(SUM(prop.assess_val_cents), 0) as total_assessed_cents,
                    COALESCE(SUM(aa.estimated_savings_cents), 0) as total_savings_cents,
                    COUNT(CASE WHEN aa.recommended_action = 'APPEAL' THEN 1 END) as appeal_candidates
                FROM portfolios p
                LEFT JOIN portfolio_properties pp ON p.id = pp.portfolio_id
                LEFT JOIN properties prop ON pp.property_id = prop.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = prop.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE p.id::text = :portfolio_id AND p.is_active = true
                GROUP BY p.id
            """)

            row = conn.execute(query, {"portfolio_id": portfolio_id}).mappings().first()

            if not row:
                return None

            total_assessed = row["total_assessed_cents"] or 0
            mill_rate = float(row["default_mill_rate"])
            annual_tax = int((total_assessed * mill_rate) / 1000) if total_assessed else 0

            return Portfolio(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                default_mill_rate=mill_rate,
                auto_analyze=row["auto_analyze"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                property_count=row["property_count"],
                total_market_value_cents=row["total_market_cents"],
                total_assessed_value_cents=total_assessed,
                estimated_annual_tax_cents=annual_tax,
                total_potential_savings_cents=row["total_savings_cents"],
                appeal_candidates=row["appeal_candidates"] or 0,
            )

    def get_user_portfolios(self, user_id: str) -> List[Portfolio]:
        """Get all portfolios for a user."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT
                    p.id, p.user_id, p.name, p.description,
                    p.default_mill_rate, p.auto_analyze,
                    p.created_at, p.updated_at,
                    COUNT(pp.id) as property_count,
                    COALESCE(SUM(prop.total_val_cents), 0) as total_market_cents,
                    COALESCE(SUM(prop.assess_val_cents), 0) as total_assessed_cents,
                    COALESCE(SUM(aa.estimated_savings_cents), 0) as total_savings_cents,
                    COUNT(CASE WHEN aa.recommended_action = 'APPEAL' THEN 1 END) as appeal_candidates
                FROM portfolios p
                LEFT JOIN portfolio_properties pp ON p.id = pp.portfolio_id
                LEFT JOIN properties prop ON pp.property_id = prop.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = prop.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE p.user_id::text = :user_id AND p.is_active = true
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """)

            results = conn.execute(query, {"user_id": user_id})
            portfolios = []

            for row in results.mappings():
                total_assessed = row["total_assessed_cents"] or 0
                mill_rate = float(row["default_mill_rate"])
                annual_tax = int((total_assessed * mill_rate) / 1000) if total_assessed else 0

                portfolios.append(Portfolio(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    description=row["description"],
                    default_mill_rate=mill_rate,
                    auto_analyze=row["auto_analyze"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    property_count=row["property_count"],
                    total_market_value_cents=row["total_market_cents"],
                    total_assessed_value_cents=total_assessed,
                    estimated_annual_tax_cents=annual_tax,
                    total_potential_savings_cents=row["total_savings_cents"],
                    appeal_candidates=row["appeal_candidates"] or 0,
                ))

            return portfolios

    def update_portfolio(self, portfolio_id: str, **kwargs) -> Portfolio:
        """Update portfolio settings."""
        with self.engine.connect() as conn:
            updates = []
            params = {"portfolio_id": portfolio_id}

            if "name" in kwargs:
                updates.append("name = :name")
                params["name"] = kwargs["name"]
            if "description" in kwargs:
                updates.append("description = :description")
                params["description"] = kwargs["description"]
            if "default_mill_rate" in kwargs:
                updates.append("default_mill_rate = :mill_rate")
                params["mill_rate"] = kwargs["default_mill_rate"]
            if "auto_analyze" in kwargs:
                updates.append("auto_analyze = :auto_analyze")
                params["auto_analyze"] = kwargs["auto_analyze"]

            if not updates:
                raise ValueError("No fields to update")

            query = text(f"""
                UPDATE portfolios
                SET {", ".join(updates)}
                WHERE id::text = :portfolio_id AND is_active = true
                RETURNING id
            """)

            result = conn.execute(query, params)
            if not result.first():
                raise ValueError("Portfolio not found")

            conn.commit()

        return self.get_portfolio(portfolio_id)

    def delete_portfolio(self, portfolio_id: str) -> bool:
        """Soft delete a portfolio."""
        with self.engine.connect() as conn:
            query = text("""
                UPDATE portfolios
                SET is_active = false
                WHERE id::text = :portfolio_id AND is_active = true
                RETURNING id
            """)
            result = conn.execute(query, {"portfolio_id": portfolio_id})
            deleted = result.first() is not None
            conn.commit()
            return deleted

    # ==================== PROPERTY MANAGEMENT ====================

    def add_property(
        self,
        portfolio_id: str,
        property_id: str,
        ownership_type: str = "TRACKING",
        ownership_percentage: float = 100.0,
        purchase_date: Optional[date] = None,
        purchase_price_cents: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_primary_residence: bool = False,
    ) -> PortfolioProperty:
        """Add a property to a portfolio by property ID."""
        with self.engine.connect() as conn:
            # Verify portfolio exists
            port_check = text("SELECT id FROM portfolios WHERE id::text = :portfolio_id AND is_active = true")
            if not conn.execute(port_check, {"portfolio_id": portfolio_id}).first():
                raise ValueError("Portfolio not found")

            # Verify property exists
            prop_check = text("SELECT id, parcel_id FROM properties WHERE id::text = :property_id")
            prop_row = conn.execute(prop_check, {"property_id": property_id}).first()
            if not prop_row:
                raise ValueError("Property not found")

            # Check for duplicate
            dup_check = text("""
                SELECT id FROM portfolio_properties
                WHERE portfolio_id::text = :portfolio_id AND property_id::text = :property_id
            """)
            if conn.execute(dup_check, {"portfolio_id": portfolio_id, "property_id": property_id}).first():
                raise ValueError("Property already in portfolio")

            # Add property
            import json
            tags_json = json.dumps(tags or [])

            query = text("""
                INSERT INTO portfolio_properties (
                    portfolio_id, property_id, ownership_type, ownership_percentage,
                    purchase_date, purchase_price_cents, notes, tags, is_primary_residence
                )
                VALUES (
                    :portfolio_id::uuid, :property_id::uuid, :ownership_type::ownership_type_enum,
                    :ownership_pct, :purchase_date, :purchase_price_cents, :notes, :tags::jsonb, :is_primary
                )
                RETURNING id, portfolio_id, property_id, ownership_type, ownership_percentage,
                          purchase_date, purchase_price_cents, notes, tags, is_primary_residence, added_at
            """)

            result = conn.execute(query, {
                "portfolio_id": portfolio_id,
                "property_id": property_id,
                "ownership_type": ownership_type,
                "ownership_pct": ownership_percentage,
                "purchase_date": purchase_date,
                "purchase_price_cents": purchase_price_cents,
                "notes": notes,
                "tags": tags_json,
                "is_primary": is_primary_residence,
            })
            row = result.mappings().first()
            conn.commit()

            # Fetch full property details
            return self._get_portfolio_property(conn, str(row["id"]))

    def add_property_by_parcel(
        self,
        portfolio_id: str,
        parcel_id: str,
        **kwargs,
    ) -> PortfolioProperty:
        """Add a property to a portfolio by parcel ID."""
        with self.engine.connect() as conn:
            # Look up property ID
            query = text("SELECT id FROM properties WHERE parcel_id = :parcel_id")
            result = conn.execute(query, {"parcel_id": parcel_id}).first()
            if not result:
                raise ValueError(f"Property with parcel_id {parcel_id} not found")

            property_id = str(result[0])

        return self.add_property(portfolio_id, property_id, **kwargs)

    def get_portfolio_properties(
        self,
        portfolio_id: str,
        include_inactive: bool = False,
    ) -> List[PortfolioProperty]:
        """Get all properties in a portfolio."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT
                    pp.id, pp.portfolio_id, pp.property_id,
                    p.parcel_id, p.ph_add as address, p.city, p.ow_name,
                    pp.ownership_type, pp.ownership_percentage,
                    pp.purchase_date, pp.purchase_price_cents,
                    p.total_val_cents, p.assess_val_cents,
                    aa.fairness_score, aa.recommended_action, aa.estimated_savings_cents,
                    aa.analysis_date as last_analyzed,
                    pp.notes, pp.tags, pp.is_primary_residence, pp.added_at
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id
                ORDER BY pp.added_at DESC
            """)

            results = conn.execute(query, {"portfolio_id": portfolio_id})
            properties = []

            for row in results.mappings():
                assessed = row["assess_val_cents"] or 0
                annual_tax = int((assessed * 65.0) / 1000) if assessed else None

                properties.append(PortfolioProperty(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    property_id=row["property_id"],
                    parcel_id=row["parcel_id"],
                    address=row["address"],
                    city=row["city"],
                    owner_name=row["ow_name"],
                    ownership_type=row["ownership_type"],
                    ownership_percentage=float(row["ownership_percentage"]) if row["ownership_percentage"] else 100.0,
                    purchase_date=row["purchase_date"],
                    purchase_price_cents=row["purchase_price_cents"],
                    notes=row["notes"],
                    tags=row["tags"] if row["tags"] else [],
                    is_primary_residence=row["is_primary_residence"],
                    added_at=row["added_at"],
                    market_value_cents=row["total_val_cents"],
                    assessed_value_cents=assessed,
                    estimated_annual_tax_cents=annual_tax,
                    fairness_score=row["fairness_score"],
                    recommended_action=row["recommended_action"],
                    estimated_savings_cents=row["estimated_savings_cents"],
                    last_analyzed=row["last_analyzed"],
                ))

            return properties

    def update_property(self, portfolio_property_id: str, **kwargs) -> PortfolioProperty:
        """Update a portfolio property."""
        with self.engine.connect() as conn:
            updates = []
            params = {"pp_id": portfolio_property_id}

            if "ownership_type" in kwargs:
                updates.append("ownership_type = :ownership_type::ownership_type_enum")
                params["ownership_type"] = kwargs["ownership_type"]
            if "ownership_percentage" in kwargs:
                updates.append("ownership_percentage = :ownership_pct")
                params["ownership_pct"] = kwargs["ownership_percentage"]
            if "purchase_date" in kwargs:
                updates.append("purchase_date = :purchase_date")
                params["purchase_date"] = kwargs["purchase_date"]
            if "purchase_price_cents" in kwargs:
                updates.append("purchase_price_cents = :purchase_price_cents")
                params["purchase_price_cents"] = kwargs["purchase_price_cents"]
            if "notes" in kwargs:
                updates.append("notes = :notes")
                params["notes"] = kwargs["notes"]
            if "tags" in kwargs:
                import json
                updates.append("tags = :tags::jsonb")
                params["tags"] = json.dumps(kwargs["tags"])
            if "is_primary_residence" in kwargs:
                updates.append("is_primary_residence = :is_primary")
                params["is_primary"] = kwargs["is_primary_residence"]

            if not updates:
                raise ValueError("No fields to update")

            query = text(f"""
                UPDATE portfolio_properties
                SET {", ".join(updates)}
                WHERE id::text = :pp_id
                RETURNING id
            """)

            result = conn.execute(query, params)
            if not result.first():
                raise ValueError("Portfolio property not found")

            conn.commit()

            return self._get_portfolio_property(conn, portfolio_property_id)

    def remove_property(self, portfolio_id: str, property_id: str) -> bool:
        """Remove a property from a portfolio."""
        with self.engine.connect() as conn:
            query = text("""
                DELETE FROM portfolio_properties
                WHERE portfolio_id::text = :portfolio_id AND property_id::text = :property_id
                RETURNING id
            """)
            result = conn.execute(query, {
                "portfolio_id": portfolio_id,
                "property_id": property_id,
            })
            removed = result.first() is not None
            conn.commit()
            return removed

    def _get_portfolio_property(self, conn, portfolio_property_id: str) -> PortfolioProperty:
        """Get a single portfolio property by ID."""
        query = text("""
            SELECT
                pp.id, pp.portfolio_id, pp.property_id,
                p.parcel_id, p.ph_add as address, p.city, p.ow_name,
                pp.ownership_type, pp.ownership_percentage,
                pp.purchase_date, pp.purchase_price_cents,
                p.total_val_cents, p.assess_val_cents,
                aa.fairness_score, aa.recommended_action, aa.estimated_savings_cents,
                aa.analysis_date as last_analyzed,
                pp.notes, pp.tags, pp.is_primary_residence, pp.added_at
            FROM portfolio_properties pp
            JOIN properties p ON pp.property_id = p.id
            LEFT JOIN LATERAL (
                SELECT * FROM assessment_analyses
                WHERE property_id = p.id
                ORDER BY analysis_date DESC LIMIT 1
            ) aa ON true
            WHERE pp.id::text = :pp_id
        """)

        row = conn.execute(query, {"pp_id": portfolio_property_id}).mappings().first()

        if not row:
            raise ValueError("Portfolio property not found")

        assessed = row["assess_val_cents"] or 0
        annual_tax = int((assessed * 65.0) / 1000) if assessed else None

        return PortfolioProperty(
            id=row["id"],
            portfolio_id=row["portfolio_id"],
            property_id=row["property_id"],
            parcel_id=row["parcel_id"],
            address=row["address"],
            city=row["city"],
            owner_name=row["ow_name"],
            ownership_type=row["ownership_type"],
            ownership_percentage=float(row["ownership_percentage"]) if row["ownership_percentage"] else 100.0,
            purchase_date=row["purchase_date"],
            purchase_price_cents=row["purchase_price_cents"],
            notes=row["notes"],
            tags=row["tags"] if row["tags"] else [],
            is_primary_residence=row["is_primary_residence"],
            added_at=row["added_at"],
            market_value_cents=row["total_val_cents"],
            assessed_value_cents=assessed,
            estimated_annual_tax_cents=annual_tax,
            fairness_score=row["fairness_score"],
            recommended_action=row["recommended_action"],
            estimated_savings_cents=row["estimated_savings_cents"],
            last_analyzed=row["last_analyzed"],
        )


# ============================================================================
# BULK ANALYSIS SERVICE
# ============================================================================


class BulkAnalysisService:
    """Service for bulk portfolio analysis operations."""

    def __init__(self, engine: Engine):
        self.engine = engine
        from src.services import AssessmentAnalyzer
        self.analyzer = AssessmentAnalyzer(engine)

    def analyze_portfolio(
        self,
        portfolio_id: str,
        force_reanalyze: bool = False,
    ) -> AnalysisResult:
        """Analyze all properties in a portfolio."""
        import time
        start_time = time.time()

        result = AnalysisResult()

        with self.engine.connect() as conn:
            # Get portfolio properties
            query = text("""
                SELECT pp.property_id, p.parcel_id
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                WHERE pp.portfolio_id::text = :portfolio_id
            """)
            properties = list(conn.execute(query, {"portfolio_id": portfolio_id}).mappings())
            result.total_properties = len(properties)

            for prop in properties:
                try:
                    analysis = self.analyzer.analyze_property(prop["parcel_id"])
                    if analysis:
                        result.analyzed_count += 1
                        if analysis.recommended_action == "APPEAL":
                            result.appeal_candidates += 1
                            if analysis.estimated_annual_savings_cents:
                                result.total_savings_cents += analysis.estimated_annual_savings_cents
                    else:
                        result.skipped_count += 1
                except Exception as e:
                    logger.error(f"Error analyzing property {prop['parcel_id']}: {e}")
                    result.error_count += 1

        result.duration_seconds = round(time.time() - start_time, 2)
        return result

    def find_portfolio_candidates(
        self,
        portfolio_id: str,
        min_score: int = 60,
        min_savings: int = 25000,  # cents
    ) -> List[AppealCandidate]:
        """Find appeal candidates in a portfolio."""
        with self.engine.connect() as conn:
            query = text("""
                SELECT
                    pp.property_id, p.parcel_id, p.ph_add as address,
                    aa.fairness_score, aa.confidence_level, aa.estimated_savings_cents
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id
                  AND aa.fairness_score >= :min_score
                  AND aa.estimated_savings_cents >= :min_savings
                ORDER BY aa.estimated_savings_cents DESC
            """)

            results = conn.execute(query, {
                "portfolio_id": portfolio_id,
                "min_score": min_score,
                "min_savings": min_savings,
            })

            candidates = []
            for row in results.mappings():
                candidates.append(AppealCandidate(
                    property_id=row["property_id"],
                    parcel_id=row["parcel_id"],
                    address=row["address"],
                    fairness_score=row["fairness_score"],
                    confidence_level=row["confidence_level"] or 0,
                    estimated_savings_cents=row["estimated_savings_cents"] or 0,
                ))

            return candidates


# ============================================================================
# PORTFOLIO ANALYTICS
# ============================================================================


class PortfolioAnalytics:
    """Service for portfolio analytics and dashboard data."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def get_dashboard_data(self, portfolio_id: str) -> DashboardData:
        """Get comprehensive dashboard data for a portfolio."""
        with self.engine.connect() as conn:
            # Get summary metrics
            summary_query = text("""
                SELECT
                    COUNT(pp.id) as total_properties,
                    COALESCE(SUM(p.total_val_cents), 0) as total_market_cents,
                    COALESCE(SUM(p.assess_val_cents), 0) as total_assessed_cents,
                    COALESCE(SUM(aa.estimated_savings_cents), 0) as total_savings_cents,
                    COUNT(CASE WHEN aa.recommended_action = 'APPEAL' THEN 1 END) as appeal_candidates,
                    AVG(aa.fairness_score) as avg_fairness
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id
            """)
            summary_row = conn.execute(summary_query, {"portfolio_id": portfolio_id}).mappings().first()

            total_assessed = summary_row["total_assessed_cents"] or 0
            annual_tax = int((total_assessed * 65.0) / 1000) if total_assessed else 0

            # Get breakdowns
            ownership_query = text("""
                SELECT ownership_type, COUNT(*) as count
                FROM portfolio_properties
                WHERE portfolio_id::text = :portfolio_id
                GROUP BY ownership_type
            """)
            by_ownership = {row["ownership_type"]: row["count"]
                           for row in conn.execute(ownership_query, {"portfolio_id": portfolio_id}).mappings()}

            city_query = text("""
                SELECT p.city, COUNT(*) as count
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                WHERE pp.portfolio_id::text = :portfolio_id
                GROUP BY p.city
            """)
            by_city = {(row["city"] or "Unknown"): row["count"]
                      for row in conn.execute(city_query, {"portfolio_id": portfolio_id}).mappings()}

            rec_query = text("""
                SELECT aa.recommended_action, COUNT(*) as count
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id AND aa.recommended_action IS NOT NULL
                GROUP BY aa.recommended_action
            """)
            by_recommendation = {row["recommended_action"]: row["count"]
                                for row in conn.execute(rec_query, {"portfolio_id": portfolio_id}).mappings()}

            summary = PortfolioSummary(
                total_properties=summary_row["total_properties"],
                total_market_value_cents=summary_row["total_market_cents"] or 0,
                total_assessed_value_cents=total_assessed,
                estimated_annual_tax_cents=annual_tax,
                total_potential_savings_cents=summary_row["total_savings_cents"] or 0,
                appeal_candidates=summary_row["appeal_candidates"] or 0,
                average_fairness_score=float(summary_row["avg_fairness"]) if summary_row["avg_fairness"] else None,
                by_ownership_type=by_ownership,
                by_city=by_city,
                by_recommendation=by_recommendation,
            )

            # Get top savings opportunities
            top_savings_query = text("""
                SELECT
                    pp.id, pp.portfolio_id, pp.property_id,
                    p.parcel_id, p.ph_add as address, p.city,
                    aa.estimated_savings_cents, aa.fairness_score
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id
                  AND aa.estimated_savings_cents > 0
                ORDER BY aa.estimated_savings_cents DESC
                LIMIT 5
            """)
            top_savings = []
            for row in conn.execute(top_savings_query, {"portfolio_id": portfolio_id}).mappings():
                top_savings.append(PortfolioProperty(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    property_id=row["property_id"],
                    parcel_id=row["parcel_id"],
                    address=row["address"],
                    city=row["city"],
                    estimated_savings_cents=row["estimated_savings_cents"],
                    fairness_score=row["fairness_score"],
                ))

            # Get top over-assessed
            top_over_query = text("""
                SELECT
                    pp.id, pp.portfolio_id, pp.property_id,
                    p.parcel_id, p.ph_add as address, p.city,
                    aa.fairness_score, aa.estimated_savings_cents
                FROM portfolio_properties pp
                JOIN properties p ON pp.property_id = p.id
                LEFT JOIN LATERAL (
                    SELECT * FROM assessment_analyses
                    WHERE property_id = p.id
                    ORDER BY analysis_date DESC LIMIT 1
                ) aa ON true
                WHERE pp.portfolio_id::text = :portfolio_id
                  AND aa.fairness_score IS NOT NULL
                ORDER BY aa.fairness_score DESC
                LIMIT 5
            """)
            top_over = []
            for row in conn.execute(top_over_query, {"portfolio_id": portfolio_id}).mappings():
                top_over.append(PortfolioProperty(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    property_id=row["property_id"],
                    parcel_id=row["parcel_id"],
                    address=row["address"],
                    city=row["city"],
                    fairness_score=row["fairness_score"],
                    estimated_savings_cents=row["estimated_savings_cents"],
                ))

            return DashboardData(
                summary=summary,
                top_savings=top_savings,
                top_over_assessed=top_over,
                recent_analyses=[],
            )
