"""
Analysis API Routes

Endpoints for property assessment fairness analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
import time
import logging

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_assessment_analyzer
)
from src.api.utils import resolve_to_parcel_id
from src.api.schemas.analysis import (
    AssessmentAnalysisResult,
    AnalyzePropertyRequest,
    BulkAnalyzeRequest,
    BulkAnalyzeResponse,
    ComparablePropertySchema,
    RecommendedAction
)
from src.api.schemas.common import APIResponse, cents_to_dollars
from src.api.cache import get_cache_manager, CacheTTL, cache_key
from src.services import AssessmentAnalyzer
from src.api.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/assess", response_model=APIResponse[AssessmentAnalysisResult])
async def analyze_property(
    request: AnalyzePropertyRequest,
    analyzer: AssessmentAnalyzer = Depends(get_assessment_analyzer),
    api_key: str = Depends(verify_api_key)
):
    """
    Run assessment fairness analysis on a single property.

    Returns:
    - Fairness score (0-100, higher = more over-assessed)
    - Confidence level
    - Recommended action (APPEAL, MONITOR, NONE)
    - Estimated savings if appeal successful
    - Comparable properties used in analysis
    """
    cache = get_cache_manager()
    engine = get_engine()

    # Resolve to parcel_id - the analyzer service works with parcel_id, not UUID
    # Use centralized resolver that handles both UUID and parcel_id inputs
    identifier = request.parcel_id or request.property_id
    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Either property_id or parcel_id must be provided"
        )

    parcel_id = resolve_to_parcel_id(engine, identifier)
    if not parcel_id:
        raise HTTPException(
            status_code=404,
            detail=f"Property not found: {identifier}"
        )

    # Check cache if not forcing reanalysis
    analysis_cache_key = f"taxdown:analysis:{cache_key(parcel_id, request.mill_rate)}"

    if not request.force_reanalyze:
        cached_result = cache.get(analysis_cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for analysis: {parcel_id}")
            return APIResponse(data=AssessmentAnalysisResult(**cached_result))

    try:
        # Run analysis - the analyzer expects parcel_id
        analysis = analyzer.analyze_property(property_id=parcel_id)

        if not analysis:
            # Analysis returned None - usually means no comparable properties found
            raise HTTPException(
                status_code=422,
                detail=f"Analysis could not be completed for property {parcel_id}. This usually means no comparable properties were found in the same area. Try a different property."
            )

        # Save analysis to database so it shows up in property details
        try:
            analyzer.save_analysis(analysis)
            logger.info(f"Saved analysis for property {parcel_id}")
        except Exception as save_error:
            logger.warning(f"Failed to save analysis to database: {save_error}")
            # Continue - we still have the analysis results to return

        # Build comparables list if requested and available
        comparables_list = None
        if request.include_comparables and analysis.comparables:
            comparables_list = [
                ComparablePropertySchema(
                    property_id=comp.id,
                    parcel_id=comp.parcel_id,
                    address=comp.address,
                    total_value=cents_to_dollars(comp.total_val_cents),
                    assessed_value=cents_to_dollars(comp.assess_val_cents),
                    assessment_ratio=comp.assessment_ratio,
                    distance_miles=comp.distance_miles,
                    similarity_score=comp.similarity_score
                )
                for comp in analysis.comparables[:10]  # Limit to top 10 most similar
            ]

        # Build response - map from AssessmentAnalysis dataclass to schema
        result = AssessmentAnalysisResult(
            property_id=str(analysis.property_id),
            parcel_id=analysis.parcel_id,
            address=analysis.address,
            current_market_value=cents_to_dollars(analysis.total_val_cents),
            current_assessed_value=cents_to_dollars(analysis.assess_val_cents),
            current_assessment_ratio=analysis.current_ratio,
            fairness_score=analysis.fairness_score,
            confidence_level=analysis.confidence,
            recommended_action=RecommendedAction(analysis.recommended_action),
            fair_assessed_value=cents_to_dollars(
                int(analysis.total_val_cents * analysis.median_comparable_ratio)
            ) if analysis.median_comparable_ratio else None,
            estimated_annual_savings=cents_to_dollars(analysis.estimated_annual_savings_cents),
            comparable_count=analysis.comparable_count,
            median_comparable_ratio=analysis.median_comparable_ratio,
            percentile_rank=None,  # Not provided by current analyzer
            comparables=comparables_list,
            analysis_date=analysis.analysis_date,
            mill_rate_used=request.mill_rate
        )

        # Cache the analysis result
        cache.set(analysis_cache_key, result.model_dump(), CacheTTL.ANALYSIS_RESULTS)

        # Invalidate related property cache since analysis data changed
        cache.invalidate_property(str(analysis.property_id))

        return APIResponse(data=result)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {parcel_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/assess/{property_id}", response_model=APIResponse[AssessmentAnalysisResult])
async def analyze_property_by_id(
    property_id: str,
    force: bool = False,
    include_comparables: bool = True,
    analyzer: AssessmentAnalyzer = Depends(get_assessment_analyzer),
    api_key: str = Depends(verify_api_key)
):
    """
    Convenience endpoint to analyze property by ID in path.
    """
    request = AnalyzePropertyRequest(
        property_id=property_id,
        force_reanalyze=force,
        include_comparables=include_comparables
    )
    return await analyze_property(request, analyzer, api_key)


@router.post("/bulk", response_model=BulkAnalyzeResponse)
async def bulk_analyze(
    request: BulkAnalyzeRequest,
    analyzer: AssessmentAnalyzer = Depends(get_assessment_analyzer),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyze multiple properties in bulk.

    - Maximum 100 properties per request
    - Returns aggregate statistics and per-property results
    - Suitable for portfolio analysis
    """
    settings = get_settings()

    if not settings.enable_bulk_operations:
        raise HTTPException(
            status_code=403,
            detail="Bulk operations are disabled"
        )

    if len(request.property_ids) > settings.max_bulk_properties:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_bulk_properties} properties per request"
        )

    start_time = time.time()
    results = []
    analyzed = 0
    skipped = 0
    errors = 0
    appeal_candidates = 0
    total_savings_cents = 0

    engine = get_engine()

    for property_id in request.property_ids:
        try:
            # Resolve to parcel_id first
            parcel_id = resolve_to_parcel_id(engine, property_id)
            if not parcel_id:
                skipped += 1
                continue

            analysis = analyzer.analyze_property(property_id=parcel_id)

            if analysis:
                # Save analysis to database
                try:
                    analyzer.save_analysis(analysis)
                except Exception as save_err:
                    logger.warning(f"Failed to save bulk analysis for {parcel_id}: {save_err}")

                result = AssessmentAnalysisResult(
                    property_id=str(analysis.property_id),
                    parcel_id=analysis.parcel_id,
                    address=analysis.address,
                    current_market_value=cents_to_dollars(analysis.total_val_cents),
                    current_assessed_value=cents_to_dollars(analysis.assess_val_cents),
                    current_assessment_ratio=analysis.current_ratio,
                    fairness_score=analysis.fairness_score,
                    confidence_level=analysis.confidence,
                    recommended_action=RecommendedAction(analysis.recommended_action),
                    fair_assessed_value=cents_to_dollars(
                        int(analysis.total_val_cents * analysis.median_comparable_ratio)
                    ) if analysis.median_comparable_ratio else None,
                    estimated_annual_savings=cents_to_dollars(analysis.estimated_annual_savings_cents),
                    comparable_count=analysis.comparable_count,
                    median_comparable_ratio=analysis.median_comparable_ratio,
                    percentile_rank=None,
                    analysis_date=analysis.analysis_date,
                    mill_rate_used=request.mill_rate,
                    comparables=None  # Don't include in bulk for performance
                )
                results.append(result)
                analyzed += 1

                if analysis.recommended_action == "APPEAL":
                    appeal_candidates += 1
                    if analysis.estimated_annual_savings_cents:
                        total_savings_cents += analysis.estimated_annual_savings_cents
            else:
                skipped += 1

        except Exception as e:
            logger.error(f"Bulk analysis error for {property_id}: {e}")
            errors += 1

    duration = time.time() - start_time

    return BulkAnalyzeResponse(
        total_requested=len(request.property_ids),
        analyzed=analyzed,
        skipped=skipped,
        errors=errors,
        appeal_candidates_found=appeal_candidates,
        total_potential_savings=cents_to_dollars(total_savings_cents) or 0,
        results=results,
        duration_seconds=round(duration, 2)
    )


@router.get("/history/{property_id}", response_model=APIResponse[List[AssessmentAnalysisResult]])
async def get_analysis_history(
    property_id: str,
    limit: int = 10,
    api_key: str = Depends(verify_api_key)
):
    """
    Get historical analysis results for a property.
    """
    engine = get_engine()

    from sqlalchemy import text

    with engine.connect() as conn:
        query = text("""
            SELECT aa.*, p.parcel_id, p.ph_add as street_address
            FROM assessment_analyses aa
            JOIN properties p ON aa.property_id = p.id
            WHERE aa.property_id::text = :property_id OR p.parcel_id = :property_id
            ORDER BY aa.analysis_date DESC
            LIMIT :limit
        """)

        results = conn.execute(query, {"property_id": property_id, "limit": limit})

        history = []
        for row in results.mappings():
            history.append(AssessmentAnalysisResult(
                property_id=str(row["property_id"]),
                parcel_id=row["parcel_id"],
                address=row["street_address"],
                fairness_score=row["fairness_score"],
                confidence_level=row.get("confidence_level", 0),
                recommended_action=RecommendedAction(row["recommended_action"]),
                estimated_annual_savings=cents_to_dollars(row.get("estimated_savings_cents")),
                comparable_count=row.get("comparable_count", 0),
                analysis_date=row["analysis_date"],
                mill_rate_used=65.0
            ))

        return APIResponse(data=history)


# Note: Property ID resolution now uses centralized utility:
# from src.api.utils import resolve_to_parcel_id, resolve_to_uuid
