"""
Portfolio management API endpoints.

Provides endpoints for managing user portfolios, properties within portfolios,
bulk operations, analysis triggers, and dashboard data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional
from datetime import date, datetime
import csv
import io

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_portfolio_service,
    get_bulk_analysis_service,
    get_portfolio_analytics,
)
from src.api.schemas.portfolio import (
    UserCreate,
    UserResponse,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioSummaryResponse,
    PortfolioDetailResponse,
    AddPropertyRequest,
    UpdatePropertyRequest,
    PortfolioPropertyResponse,
    BulkImportRequest,
    BulkImportResponse,
    DashboardResponse,
    DashboardMetrics,
    TopProperty,
    OwnershipType,
)
from src.api.schemas.common import APIResponse, cents_to_dollars

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


# ==================== USER ENDPOINTS ====================


@router.post("/users", response_model=APIResponse[UserResponse])
async def create_user(
    request: UserCreate,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Create a new user account."""
    try:
        user = service.create_user(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            user_type=request.user_type.value,
        )
        return APIResponse(data=_user_to_response(user))
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=APIResponse[UserResponse])
async def get_user(
    user_id: str,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Get user by ID."""
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(data=_user_to_response(user))


@router.get("/users/by-email/{email}", response_model=APIResponse[UserResponse])
async def get_user_by_email(
    email: str,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Get user by email address."""
    user = service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(data=_user_to_response(user))


# ==================== PORTFOLIO CRUD ====================


@router.post("", response_model=APIResponse[PortfolioSummaryResponse])
async def create_portfolio(
    request: PortfolioCreate,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Create a new portfolio for a user."""
    try:
        portfolio = service.create_portfolio(
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            default_mill_rate=request.default_mill_rate,
            auto_analyze=request.auto_analyze,
        )
        return APIResponse(data=_portfolio_to_summary(portfolio))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=APIResponse[List[PortfolioSummaryResponse]])
async def list_portfolios(
    user_id: str,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """List all portfolios for a user."""
    portfolios = service.get_user_portfolios(user_id)
    return APIResponse(data=[_portfolio_to_summary(p) for p in portfolios])


@router.get("/{portfolio_id}", response_model=APIResponse[PortfolioDetailResponse])
async def get_portfolio(
    portfolio_id: str,
    include_properties: bool = Query(True),
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Get portfolio details with optional properties."""
    portfolio = service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    properties = []
    if include_properties:
        props = service.get_portfolio_properties(portfolio_id)
        properties = [_property_to_response(p) for p in props]

    return APIResponse(data=_portfolio_to_detail(portfolio, properties))


@router.patch("/{portfolio_id}", response_model=APIResponse[PortfolioSummaryResponse])
async def update_portfolio(
    portfolio_id: str,
    request: PortfolioUpdate,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Update portfolio settings."""
    try:
        updates = request.model_dump(exclude_unset=True)
        portfolio = service.update_portfolio(portfolio_id, **updates)
        return APIResponse(data=_portfolio_to_summary(portfolio))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Portfolio not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Delete a portfolio and all its property associations."""
    success = service.delete_portfolio(portfolio_id)
    if not success:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"status": "success", "message": "Portfolio deleted"}


# ==================== PROPERTY MANAGEMENT ====================


@router.post(
    "/{portfolio_id}/properties", response_model=APIResponse[PortfolioPropertyResponse]
)
async def add_property(
    portfolio_id: str,
    request: AddPropertyRequest,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Add a property to a portfolio."""
    try:
        if request.property_id:
            prop = service.add_property(
                portfolio_id=portfolio_id,
                property_id=request.property_id,
                ownership_type=request.ownership_type.value,
                ownership_percentage=request.ownership_percentage,
                purchase_date=request.purchase_date,
                purchase_price_cents=(
                    int(request.purchase_price * 100) if request.purchase_price else None
                ),
                notes=request.notes,
                tags=request.tags,
                is_primary_residence=request.is_primary_residence,
            )
        elif request.parcel_id:
            prop = service.add_property_by_parcel(
                portfolio_id=portfolio_id,
                parcel_id=request.parcel_id,
                ownership_type=request.ownership_type.value,
                ownership_percentage=request.ownership_percentage,
                purchase_date=request.purchase_date,
                purchase_price_cents=(
                    int(request.purchase_price * 100) if request.purchase_price else None
                ),
                notes=request.notes,
                tags=request.tags,
                is_primary_residence=request.is_primary_residence,
            )
        else:
            raise HTTPException(
                status_code=400, detail="Either property_id or parcel_id required"
            )

        return APIResponse(data=_property_to_response(prop))

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" in error_msg or "already" in error_msg:
            raise HTTPException(status_code=409, detail="Property already in portfolio")
        if "not found" in error_msg:
            raise HTTPException(
                status_code=404, detail="Portfolio or property not found"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{portfolio_id}/properties",
    response_model=APIResponse[List[PortfolioPropertyResponse]],
)
async def list_properties(
    portfolio_id: str,
    include_inactive: bool = False,
    ownership_type: Optional[OwnershipType] = None,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """List all properties in a portfolio."""
    properties = service.get_portfolio_properties(
        portfolio_id, include_inactive=include_inactive
    )

    # Filter by ownership type if specified
    if ownership_type:
        properties = [p for p in properties if p.ownership_type == ownership_type.value]

    return APIResponse(data=[_property_to_response(p) for p in properties])


@router.patch(
    "/{portfolio_id}/properties/{property_id}",
    response_model=APIResponse[PortfolioPropertyResponse],
)
async def update_property(
    portfolio_id: str,
    property_id: str,
    request: UpdatePropertyRequest,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Update property details in portfolio."""
    try:
        updates = {}
        if request.ownership_type is not None:
            updates["ownership_type"] = request.ownership_type.value
        if request.ownership_percentage is not None:
            updates["ownership_percentage"] = request.ownership_percentage
        if request.purchase_date is not None:
            updates["purchase_date"] = request.purchase_date
        if request.purchase_price is not None:
            updates["purchase_price_cents"] = int(request.purchase_price * 100)
        if request.notes is not None:
            updates["notes"] = request.notes
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.is_primary_residence is not None:
            updates["is_primary_residence"] = request.is_primary_residence

        # Find the portfolio_property record
        props = service.get_portfolio_properties(portfolio_id)
        pp = next((p for p in props if str(p.property_id) == property_id), None)
        if not pp:
            raise HTTPException(status_code=404, detail="Property not found in portfolio")

        updated = service.update_property(pp.id, **updates)
        return APIResponse(data=_property_to_response(updated))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{portfolio_id}/properties/{property_id}")
async def remove_property(
    portfolio_id: str,
    property_id: str,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Remove a property from a portfolio (soft delete)."""
    success = service.remove_property(portfolio_id, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found in portfolio")
    return {"status": "success", "message": "Property removed from portfolio"}


# ==================== BULK OPERATIONS ====================


@router.post("/{portfolio_id}/properties/bulk", response_model=BulkImportResponse)
async def bulk_add_properties(
    portfolio_id: str,
    request: BulkImportRequest,
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Add multiple properties to a portfolio."""
    added = []
    duplicates = 0
    not_found = 0
    errors = 0
    error_details = []

    for prop_req in request.properties:
        try:
            if prop_req.property_id:
                prop = service.add_property(
                    portfolio_id=portfolio_id,
                    property_id=prop_req.property_id,
                    ownership_type=prop_req.ownership_type.value,
                )
            elif prop_req.parcel_id:
                prop = service.add_property_by_parcel(
                    portfolio_id=portfolio_id,
                    parcel_id=prop_req.parcel_id,
                    ownership_type=prop_req.ownership_type.value,
                )
            else:
                errors += 1
                error_details.append("Missing property_id or parcel_id")
                continue

            added.append(_property_to_response(prop))

        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg or "already" in error_msg:
                duplicates += 1
            elif "not found" in error_msg:
                not_found += 1
                error_details.append(
                    f"Property not found: {prop_req.parcel_id or prop_req.property_id}"
                )
            else:
                errors += 1
                error_details.append(str(e))

    return BulkImportResponse(
        total_requested=len(request.properties),
        added=len(added),
        duplicates=duplicates,
        not_found=not_found,
        errors=errors,
        error_details=error_details[:10],  # Limit error details
        properties_added=added,
    )


@router.post("/{portfolio_id}/import/csv", response_model=BulkImportResponse)
async def import_csv(
    portfolio_id: str,
    file: UploadFile = File(...),
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Import properties from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    added = []
    duplicates = 0
    not_found = 0
    errors = 0
    error_details = []
    row_count = 0

    for row in reader:
        row_count += 1
        try:
            parcel_id = (
                row.get("parcel_id") or row.get("Parcel ID") or row.get("ParcelID")
            )
            if not parcel_id:
                errors += 1
                error_details.append("Row missing parcel_id")
                continue

            prop = service.add_property_by_parcel(
                portfolio_id=portfolio_id,
                parcel_id=parcel_id.strip(),
                ownership_type=row.get("ownership_type", "OWNER"),
                notes=row.get("notes", ""),
            )
            added.append(_property_to_response(prop))

        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg:
                duplicates += 1
            elif "not found" in error_msg:
                not_found += 1
            else:
                errors += 1
                error_details.append(str(e)[:100])

    return BulkImportResponse(
        total_requested=row_count,
        added=len(added),
        duplicates=duplicates,
        not_found=not_found,
        errors=errors,
        error_details=error_details[:10],
        properties_added=added,
    )


# ==================== ANALYSIS ====================


@router.post("/{portfolio_id}/analyze")
async def analyze_portfolio(
    portfolio_id: str,
    force: bool = Query(False, description="Force reanalysis of all properties"),
    service=Depends(get_bulk_analysis_service),
    api_key: str = Depends(verify_api_key),
):
    """Run assessment analysis on all properties in portfolio."""
    try:
        result = service.analyze_portfolio(portfolio_id, force_reanalyze=force)
        return {
            "status": "success",
            "data": {
                "total_properties": result.total_properties,
                "analyzed": result.analyzed_count,
                "skipped": result.skipped_count,
                "errors": result.error_count,
                "appeal_candidates": result.appeal_candidates,
                "total_potential_savings": cents_to_dollars(result.total_savings_cents),
                "duration_seconds": result.duration_seconds,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{portfolio_id}/candidates")
async def get_appeal_candidates(
    portfolio_id: str,
    min_score: int = Query(60, ge=0, le=100),
    min_savings: float = Query(250.0, ge=0),
    service=Depends(get_bulk_analysis_service),
    api_key: str = Depends(verify_api_key),
):
    """Get properties that are candidates for appeal."""
    candidates = service.find_portfolio_candidates(
        portfolio_id, min_score=min_score, min_savings=int(min_savings * 100)
    )
    return {
        "status": "success",
        "data": {
            "count": len(candidates),
            "total_potential_savings": sum(
                cents_to_dollars(c.estimated_savings_cents) or 0 for c in candidates
            ),
            "candidates": [
                {
                    "property_id": str(c.property_id),
                    "parcel_id": c.parcel_id,
                    "address": c.address,
                    "fairness_score": c.fairness_score,
                    "confidence": c.confidence_level,
                    "estimated_savings": cents_to_dollars(c.estimated_savings_cents),
                }
                for c in candidates
            ],
        },
    }


# ==================== DASHBOARD ====================


@router.get("/{portfolio_id}/dashboard", response_model=APIResponse[DashboardResponse])
async def get_dashboard(
    portfolio_id: str,
    analytics=Depends(get_portfolio_analytics),
    service=Depends(get_portfolio_service),
    api_key: str = Depends(verify_api_key),
):
    """Get dashboard data for a portfolio."""
    portfolio = service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    try:
        dashboard = analytics.get_dashboard_data(portfolio_id)

        # Calculate appeal deadline
        today = date.today()
        if today.month <= 5:
            deadline = date(today.year, 5, 31)
        else:
            deadline = date(today.year + 1, 5, 31)
        days_until = (deadline - today).days

        return APIResponse(
            data=DashboardResponse(
                portfolio_id=str(portfolio.id),
                portfolio_name=portfolio.name,
                metrics=DashboardMetrics(
                    total_properties=dashboard.summary.total_properties,
                    total_market_value=(
                        cents_to_dollars(dashboard.summary.total_market_value_cents) or 0
                    ),
                    total_assessed_value=(
                        cents_to_dollars(dashboard.summary.total_assessed_value_cents)
                        or 0
                    ),
                    estimated_annual_tax=(
                        cents_to_dollars(dashboard.summary.estimated_annual_tax_cents)
                        or 0
                    ),
                    total_potential_savings=(
                        cents_to_dollars(dashboard.summary.total_potential_savings_cents)
                        or 0
                    ),
                    appeal_candidates=dashboard.summary.appeal_candidates,
                    average_fairness_score=dashboard.summary.average_fairness_score,
                    by_ownership_type=dashboard.summary.by_ownership_type,
                    by_city=getattr(dashboard.summary, "by_city", {}),
                    by_recommendation=dashboard.summary.by_recommendation,
                ),
                top_savings_opportunities=[
                    TopProperty(
                        property_id=str(p.property_id),
                        parcel_id=p.parcel_id,
                        address=p.address,
                        value=cents_to_dollars(p.estimated_savings_cents) or 0,
                        metric_name="potential_savings",
                    )
                    for p in dashboard.top_savings[:5]
                ],
                top_over_assessed=[
                    TopProperty(
                        property_id=str(p.property_id),
                        parcel_id=p.parcel_id,
                        address=p.address,
                        value=p.fairness_score or 0,
                        metric_name="fairness_score",
                    )
                    for p in dashboard.top_over_assessed[:5]
                ],
                recent_analyses=[],
                appeal_deadline=deadline,
                days_until_deadline=days_until,
            )
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HELPER FUNCTIONS ====================


def _user_to_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        user_type=user.user_type,
        subscription_tier=user.subscription_tier,
        created_at=user.created_at,
        last_login=user.last_login,
    )


def _portfolio_to_summary(portfolio) -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        id=str(portfolio.id),
        user_id=str(portfolio.user_id),
        name=portfolio.name,
        description=portfolio.description,
        property_count=getattr(portfolio, "property_count", 0),
        total_value=cents_to_dollars(
            getattr(portfolio, "total_market_value_cents", None)
        ),
        total_assessed_value=cents_to_dollars(
            getattr(portfolio, "total_assessed_value_cents", None)
        ),
        estimated_annual_tax=cents_to_dollars(
            getattr(portfolio, "estimated_annual_tax_cents", None)
        ),
        total_potential_savings=cents_to_dollars(
            getattr(portfolio, "total_potential_savings_cents", None)
        ),
        appeal_candidates=getattr(portfolio, "appeal_candidates", 0),
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


def _portfolio_to_detail(portfolio, properties: List) -> PortfolioDetailResponse:
    summary = _portfolio_to_summary(portfolio)
    return PortfolioDetailResponse(
        **summary.model_dump(),
        default_mill_rate=portfolio.default_mill_rate,
        auto_analyze=portfolio.auto_analyze,
        properties=properties,
    )


def _property_to_response(prop) -> PortfolioPropertyResponse:
    return PortfolioPropertyResponse(
        id=str(prop.id),
        portfolio_id=str(prop.portfolio_id),
        property_id=str(prop.property_id),
        parcel_id=prop.parcel_id,
        address=getattr(prop, "address", None),
        city=getattr(prop, "city", None),
        owner_name=getattr(prop, "owner_name", None),
        ownership_type=prop.ownership_type,
        ownership_percentage=prop.ownership_percentage,
        purchase_date=prop.purchase_date,
        purchase_price=cents_to_dollars(prop.purchase_price_cents),
        market_value=cents_to_dollars(getattr(prop, "market_value_cents", None)),
        assessed_value=cents_to_dollars(getattr(prop, "assessed_value_cents", None)),
        estimated_annual_tax=cents_to_dollars(
            getattr(prop, "estimated_annual_tax_cents", None)
        ),
        fairness_score=getattr(prop, "fairness_score", None),
        recommended_action=getattr(prop, "recommended_action", None),
        estimated_savings=cents_to_dollars(
            getattr(prop, "estimated_savings_cents", None)
        ),
        last_analyzed=getattr(prop, "last_analyzed", None),
        notes=prop.notes,
        tags=prop.tags or [],
        is_primary_residence=prop.is_primary_residence,
        added_at=prop.added_at,
    )
