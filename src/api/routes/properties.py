"""
Property API routes.

Endpoints for searching and retrieving property information.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy import text
import logging

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
from src.api.cache import get_cache_manager, CacheTTL, cache_key
from src.services import AssessmentAnalyzer

logger = logging.getLogger(__name__)
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
    # Check cache first
    cache = get_cache_manager()
    cache_k = f"taxdown:property_detail:{cache_key(property_id, include_analysis)}"
    cached_data = cache.get(cache_k)
    if cached_data is not None:
        logger.debug(f"Cache hit for property {property_id}")
        return APIResponse(data=PropertyDetail(**cached_data))

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

        # Cache the result
        cache.set(cache_k, property_data.model_dump(), CacheTTL.PROPERTY_DETAIL)

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
    # Check cache for search results
    cache = get_cache_manager()
    search_cache_key = f"taxdown:search:{cache_key(request.model_dump())}"
    cached_result = cache.get(search_cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for search query")
        return PropertySearchResponse(**cached_result)

    engine = get_engine()

    # Build dynamic query
    # Always require parcel_id to be non-null (data quality filter)
    conditions = ["p.parcel_id IS NOT NULL"]
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

    if request.max_fairness_score:
        conditions.append("aa.fairness_score <= :max_score")
        params["max_score"] = request.max_fairness_score

    # Handle assessment category filter
    # NEW SCORING: Higher score = FAIRER (inverted from original)
    # - fairly_assessed: 70-100 (at or below comparable median)
    # - slightly_over: 50-69 (slightly above comparables)
    # - moderately_over: 30-49 (moderately above, appeal candidate)
    # - significantly_over: 0-29 (greatly above, strong appeal candidate)
    if request.assessment_category:
        if request.assessment_category == "fairly_assessed":
            conditions.append("aa.fairness_score >= 70")
        elif request.assessment_category == "slightly_over":
            conditions.append("aa.fairness_score >= 50 AND aa.fairness_score < 70")
        elif request.assessment_category == "moderately_over":
            conditions.append("aa.fairness_score >= 30 AND aa.fairness_score < 50")
        elif request.assessment_category == "significantly_over":
            conditions.append("aa.fairness_score < 30")
        elif request.assessment_category == "unanalyzed":
            conditions.append("aa.fairness_score IS NULL")

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

    # Determine if we need the analysis join (only for fairness-related filters/sorting)
    needs_analysis_join = (
        request.min_fairness_score is not None or
        request.max_fairness_score is not None or
        request.assessment_category is not None or
        request.only_appeal_candidates or
        request.sort_by == "fairness_score"
    )

    with engine.connect() as conn:
        try:
            # Set query timeout to 10 seconds
            conn.execute(text("SET statement_timeout = '10s'"))

            if needs_analysis_join:
                # Full query with analysis join
                count_query = text(f"""
                    SELECT COUNT(*) FROM properties p
                    LEFT JOIN LATERAL (
                        SELECT * FROM assessment_analyses
                        WHERE property_id = p.id
                        ORDER BY analysis_date DESC LIMIT 1
                    ) aa ON true
                    WHERE {where_clause}
                """)
            else:
                # Optimized count without analysis join (much faster)
                count_query = text(f"""
                    SELECT COUNT(*) FROM properties p
                    WHERE {where_clause}
                """)

            total_count = conn.execute(count_query, params).scalar()

            # Fetch page
            offset = (request.page - 1) * request.page_size
            params["limit"] = request.page_size
            params["offset"] = offset

            if needs_analysis_join:
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
            else:
                # Optimized query without analysis join
                data_query = text(f"""
                    SELECT p.id, p.parcel_id, p.ph_add, p.city,
                           p.ow_name, p.total_val_cents, p.assess_val_cents,
                           p.type_, p.subdivname,
                           NULL as fairness_score, NULL as recommended_action
                    FROM properties p
                    WHERE {where_clause}
                    ORDER BY {sort_column} {sort_dir} NULLS LAST
                    LIMIT :limit OFFSET :offset
                """)

            results = conn.execute(data_query, params)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Database query failed. Try a different sort option or add filters to narrow results."
            )

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

    response = PropertySearchResponse(
        properties=properties,
        total_count=total_count,
        page=request.page,
        page_size=request.page_size,
        total_pages=total_pages,
        has_more=request.page < total_pages
    )

    # Cache search results
    cache.set(search_cache_key, response.model_dump(), CacheTTL.SEARCH_RESULTS)

    return response


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
    # Check cache for autocomplete results
    cache = get_cache_manager()
    autocomplete_cache_key = f"taxdown:autocomplete:{cache_key(q.lower(), limit)}"
    cached_suggestions = cache.get(autocomplete_cache_key)
    if cached_suggestions is not None:
        logger.debug(f"Cache hit for autocomplete: {q}")
        return [AddressSuggestion(**s) for s in cached_suggestions]

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

        # Cache autocomplete results
        cache.set(
            autocomplete_cache_key,
            [s.model_dump() for s in suggestions],
            CacheTTL.AUTOCOMPLETE
        )

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


@router.get("/stats/assessment-distribution")
async def get_assessment_distribution(
    api_key: str = Depends(verify_api_key)
):
    """
    Get distribution of properties by assessment fairness category.

    Categories based on fairness score (SALES COMPARISON APPROACH):
    Higher score = FAIRER (less likely over-assessed)
    - fairly_assessed: 70-100 (at or below comparable median)
    - slightly_over: 50-69 (slightly above comparables)
    - moderately_over: 30-49 (moderately above, appeal candidate)
    - significantly_over: 0-29 (greatly above, strong appeal candidate)

    Returns counts for each category plus total analyzed properties.
    """
    cache = get_cache_manager()
    cache_key_str = "taxdown:stats:assessment_distribution"

    cached_data = cache.get(cache_key_str)
    if cached_data is not None:
        logger.debug("Cache hit for assessment distribution")
        return cached_data

    engine = get_engine()

    with engine.connect() as conn:
        # Get counts by fairness category from analyzed properties
        # NEW SCORING: Higher score = FAIRER
        query = text("""
            WITH latest_analyses AS (
                SELECT DISTINCT ON (property_id)
                    property_id,
                    fairness_score,
                    recommended_action,
                    estimated_savings_cents
                FROM assessment_analyses
                ORDER BY property_id, analysis_date DESC
            )
            SELECT
                COUNT(*) FILTER (WHERE fairness_score >= 70) as fairly_assessed,
                COUNT(*) FILTER (WHERE fairness_score >= 50 AND fairness_score < 70) as slightly_over,
                COUNT(*) FILTER (WHERE fairness_score >= 30 AND fairness_score < 50) as moderately_over,
                COUNT(*) FILTER (WHERE fairness_score < 30) as significantly_over,
                COUNT(*) as total_analyzed,
                COUNT(*) FILTER (WHERE recommended_action = 'APPEAL') as appeal_candidates,
                COALESCE(SUM(estimated_savings_cents) FILTER (WHERE recommended_action = 'APPEAL'), 0) as total_potential_savings_cents
            FROM latest_analyses
        """)

        result = conn.execute(query)
        row = result.mappings().first()

        # Also get total properties count (including unanalyzed)
        total_query = text("SELECT COUNT(*) FROM properties WHERE parcel_id IS NOT NULL")
        total_properties = conn.execute(total_query).scalar()

        response = {
            "fairly_assessed": row["fairly_assessed"] or 0,
            "slightly_over": row["slightly_over"] or 0,
            "moderately_over": row["moderately_over"] or 0,
            "significantly_over": row["significantly_over"] or 0,
            "total_analyzed": row["total_analyzed"] or 0,
            "total_properties": total_properties or 0,
            "unanalyzed": (total_properties or 0) - (row["total_analyzed"] or 0),
            "appeal_candidates": row["appeal_candidates"] or 0,
            "total_potential_savings": cents_to_dollars(row["total_potential_savings_cents"]) or 0
        }

        # Cache for 5 minutes
        cache.set(cache_key_str, response, 300)

        return response


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
