"""
Analysis API Routes

Endpoints for property assessment fairness analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
import time

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_assessment_analyzer
)
from src.api.schemas.analysis import (
    AssessmentAnalysisResult,
    AnalyzePropertyRequest,
    BulkAnalyzeRequest,
    BulkAnalyzeResponse,
    ComparablePropertySchema,
    RecommendedAction
)
from src.api.schemas.common import APIResponse, cents_to_dollars
from src.services import AssessmentAnalyzer
from src.api.config import get_settings

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
    # Resolve property ID
    property_id = request.property_id
    if not property_id and request.parcel_id:
        property_id = _lookup_property_id(get_engine(), request.parcel_id)

    if not property_id:
        raise HTTPException(
            status_code=400,
            detail="Either property_id or parcel_id must be provided"
        )

    try:
        # Run analysis - use parcel_id if that's what we have
        analysis_id = request.parcel_id if request.parcel_id else property_id
        analysis = analyzer.analyze_property(property_id=analysis_id)

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Property not found or analysis failed"
            )

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
            analysis_date=analysis.analysis_date,
            mill_rate_used=request.mill_rate
        )

        return APIResponse(data=result)

    except Exception as e:
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

    for property_id in request.property_ids:
        try:
            analysis = analyzer.analyze_property(property_id=property_id)

            if analysis:
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


# Helper
def _lookup_property_id(engine, parcel_id: str) -> Optional[str]:
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM properties WHERE parcel_id = :parcel_id"),
            {"parcel_id": parcel_id}
        )
        row = result.first()
        return str(row[0]) if row else None
