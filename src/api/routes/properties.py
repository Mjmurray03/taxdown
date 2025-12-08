"""
Property API routes.

Endpoints for searching and retrieving property information.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy import text

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_assessment_analyzer
)
from src.api.schemas.property import (
    PropertyDetail,
    PropertySummary,
    PropertySearchRequest,
    PropertySearchResponse,
    AddressSuggestion
)
from src.api.schemas.common import APIResponse, cents_to_dollars
from src.services import AssessmentAnalyzer

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("/{property_id}", response_model=APIResponse[PropertyDetail])
async def get_property(
    property_id: str,
    include_analysis: bool = Query(True, description="Include latest analysis results"),
    api_key: str = Depends(verify_api_key)
):
    """
    Get detailed property information by ID.

    - **property_id**: Property UUID or parcel ID
    - **include_analysis**: Whether to include fairness analysis
    """
    engine = get_engine()

    with engine.connect() as conn:
        # Try UUID first, then parcel_id
        # Using only columns that exist in the properties table
        query = text("""
            SELECT p.id, p.parcel_id, p.ph_add, p.city,
                   p.ow_name, p.ow_add as owner_address,
                   p.total_val_cents, p.assess_val_cents,
                   p.land_val_cents, p.imp_val_cents,
                   p.type_ as parcel_type, p.subdivname as subdivision,
                   p.acre_area as tax_area_acres,
                   aa.fairness_score,
                   aa.recommended_action,
                   aa.estimated_savings_cents,
                   aa.analysis_date as last_analyzed
            FROM properties p
            LEFT JOIN LATERAL (
                SELECT * FROM assessment_analyses
                WHERE property_id = p.id
                ORDER BY analysis_date DESC
                LIMIT 1
            ) aa ON true
            WHERE p.id::text = :id OR p.parcel_id = :id
        """)

        result = conn.execute(query, {"id": property_id})
        row = result.mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Property not found")

        # Convert to response
        property_data = PropertyDetail(
            id=str(row["id"]),
            parcel_id=row["parcel_id"],
            address=_build_address(row),
            city=row.get("city"),
            county="Benton",  # Default county
            owner_name=row.get("ow_name"),
            owner_address=row.get("owner_address"),
            total_value=cents_to_dollars(row.get("total_val_cents")),
            assessed_value=cents_to_dollars(row.get("assess_val_cents")),
            land_value=cents_to_dollars(row.get("land_val_cents")),
            improvement_value=cents_to_dollars(row.get("imp_val_cents")),
            property_type=row.get("parcel_type"),
            subdivision=row.get("subdivision"),
            tax_area_acres=float(row.get("tax_area_acres")) if row.get("tax_area_acres") else None,
            fairness_score=row.get("fairness_score") if include_analysis else None,
            recommended_action=row.get("recommended_action") if include_analysis else None,
            estimated_savings=cents_to_dollars(row.get("estimated_savings_cents")) if include_analysis else None,
            last_analyzed=row.get("last_analyzed") if include_analysis else None
        )

        # Calculate estimated annual tax
        if property_data.assessed_value:
            property_data.estimated_annual_tax = (property_data.assessed_value * 65.0) / 1000

        return APIResponse(data=property_data)


@router.post("/search", response_model=PropertySearchResponse)
async def search_properties(
    request: PropertySearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Search properties with filters.

    Supports:
    - Text search (address, owner name)
    - Parcel ID lookup
    - Value range filters
    - City/subdivision filters
    - Fairness score filters
    """
    engine = get_engine()

    # Build dynamic query
    conditions = ["1=1"]
    params = {}

    if request.parcel_id:
        conditions.append("p.parcel_id = :parcel_id")
        params["parcel_id"] = request.parcel_id

    if request.query:
        conditions.append("""
            (p.ph_add ILIKE :query
             OR p.ow_name ILIKE :query
             OR p.parcel_id ILIKE :query)
        """)
        params["query"] = f"%{request.query}%"

    if request.city:
        conditions.append("p.city ILIKE :city")
        params["city"] = f"%{request.city}%"

    if request.subdivision:
        conditions.append("p.subdivname ILIKE :subdivision")
        params["subdivision"] = f"%{request.subdivision}%"

    if request.property_type:
        conditions.append("p.type_ = :property_type")
        params["property_type"] = request.property_type

    if request.min_value:
        conditions.append("p.total_val_cents >= :min_value")
        params["min_value"] = int(request.min_value * 100)

    if request.max_value:
        conditions.append("p.total_val_cents <= :max_value")
        params["max_value"] = int(request.max_value * 100)

    if request.min_fairness_score:
        conditions.append("aa.fairness_score >= :min_score")
        params["min_score"] = request.min_fairness_score

    if request.only_appeal_candidates:
        conditions.append("aa.recommended_action = 'APPEAL'")

    where_clause = " AND ".join(conditions)

    # Sorting
    sort_column = {
        "address": "p.ph_add",
        "value": "p.total_val_cents",
        "assessed_value": "p.assess_val_cents",
        "fairness_score": "aa.fairness_score"
    }.get(request.sort_by, "p.ph_add")

    sort_dir = "DESC" if request.sort_order == "desc" else "ASC"

    with engine.connect() as conn:
        # Count total
        count_query = text(f"""
            SELECT COUNT(*) FROM properties p
            LEFT JOIN LATERAL (
                SELECT * FROM assessment_analyses
                WHERE property_id = p.id
                ORDER BY analysis_date DESC LIMIT 1
            ) aa ON true
            WHERE {where_clause}
        """)
        total_count = conn.execute(count_query, params).scalar()

        # Fetch page
        offset = (request.page - 1) * request.page_size
        params["limit"] = request.page_size
        params["offset"] = offset

        data_query = text(f"""
            SELECT p.id, p.parcel_id, p.ph_add, p.city,
                   p.ow_name, p.total_val_cents, p.assess_val_cents,
                   p.type_, p.subdivname,
                   aa.fairness_score, aa.recommended_action
            FROM properties p
            LEFT JOIN LATERAL (
                SELECT * FROM assessment_analyses
                WHERE property_id = p.id
                ORDER BY analysis_date DESC LIMIT 1
            ) aa ON true
            WHERE {where_clause}
            ORDER BY {sort_column} {sort_dir} NULLS LAST
            LIMIT :limit OFFSET :offset
        """)

        results = conn.execute(data_query, params)

        properties = []
        for row in results.mappings():
            properties.append(PropertySummary(
                id=str(row["id"]),
                parcel_id=row["parcel_id"],
                address=row["ph_add"],
                city=row["city"],
                owner_name=row["ow_name"],
                total_value=cents_to_dollars(row["total_val_cents"]),
                assessed_value=cents_to_dollars(row["assess_val_cents"]),
                property_type=row["type_"],
                subdivision=row["subdivname"]
            ))

    total_pages = (total_count + request.page_size - 1) // request.page_size

    return PropertySearchResponse(
        properties=properties,
        total_count=total_count,
        page=request.page,
        page_size=request.page_size,
        total_pages=total_pages,
        has_more=request.page < total_pages
    )


@router.get("/autocomplete/address", response_model=List[AddressSuggestion])
async def autocomplete_address(
    q: str = Query(..., min_length=3, description="Address search query"),
    limit: int = Query(10, ge=1, le=50),
    api_key: str = Depends(verify_api_key)
):
    """
    Address autocomplete for search boxes.

    Returns top matches with relevance scores.
    """
    engine = get_engine()

    with engine.connect() as conn:
        # Note: similarity function requires pg_trgm extension
        # Fall back to simple ILIKE matching if similarity not available
        query = text("""
            SELECT id, parcel_id, ph_add, city,
                   COALESCE(similarity(ph_add, :query), 0.5) as match_score
            FROM properties
            WHERE ph_add ILIKE :pattern
            ORDER BY match_score DESC, ph_add
            LIMIT :limit
        """)

        results = conn.execute(query, {
            "query": q,
            "pattern": f"%{q}%",
            "limit": limit
        })

        suggestions = []
        for row in results.mappings():
            suggestions.append(AddressSuggestion(
                property_id=str(row["id"]),
                parcel_id=row["parcel_id"],
                address=row["ph_add"],
                city=row["city"],
                match_score=float(row["match_score"]) if row["match_score"] else 0.5
            ))

        return suggestions


@router.get("/by-parcel/{parcel_id}", response_model=APIResponse[PropertyDetail])
async def get_property_by_parcel(
    parcel_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get property by parcel ID (convenience endpoint).
    """
    return await get_property(parcel_id, include_analysis=True, api_key=api_key)


# Helper functions
def _build_address(row: dict) -> str:
    """Build full address string from components"""
    parts = []
    if row.get("ph_add"):
        parts.append(row["ph_add"])
    if row.get("city"):
        parts.append(row["city"])
    if row.get("state"):
        parts.append(row["state"])
    if row.get("zip_code"):
        parts.append(row["zip_code"])
    return ", ".join(parts) if parts else None
