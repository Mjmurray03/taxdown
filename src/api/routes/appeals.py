"""
Appeal Generation API Routes

This module provides REST API endpoints for generating property tax appeals:
- Generate single appeal with customizable options
- Batch generate appeals for multiple properties
- Download appeals as PDF
- List and retrieve saved appeals

All endpoints require API key authentication when enabled.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, date
import io
import logging

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_appeal_generator,
    get_assessment_analyzer,
    get_pdf_generator,
)
from src.api.utils import resolve_to_parcel_id, resolve_property
from src.api.schemas.appeal import (
    GenerateAppealRequest,
    AppealPackageResponse,
    AppealListItem,
    AppealDownloadRequest,
    BatchAppealRequest,
    BatchAppealResponse,
    AppealStatus,
    TemplateStyle,
)
from src.api.schemas.common import APIResponse, cents_to_dollars
from src.services import (
    AppealGenerator,
    AssessmentAnalyzer,
    GeneratorConfig,
    PDFGenerator,
    AppealPackage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appeals", tags=["Appeals"])


def _package_to_response(package: AppealPackage) -> AppealPackageResponse:
    """Convert AppealPackage to API response model."""
    return AppealPackageResponse(
        appeal_id=package.appeal_id,
        property_id=package.property_id,
        parcel_id=package.parcel_id,
        address=package.address,
        owner_name=package.owner_name,
        current_assessed_value=cents_to_dollars(package.current_assessed_value_cents),
        requested_assessed_value=cents_to_dollars(package.requested_assessed_value_cents),
        estimated_annual_savings=cents_to_dollars(package.estimated_annual_savings_cents),
        appeal_letter=package.appeal_letter_text,
        executive_summary=package.executive_summary,
        evidence_summary=package.evidence_summary,
        fairness_score=package.fairness_score,
        confidence_level=package.confidence_level,
        comparable_count=package.comparable_count,
        jurisdiction=package.jurisdiction,
        filing_deadline=package.filing_deadline,
        required_forms=package.required_forms,
        statute_reference=package.statute_reference,
        generated_at=package.generated_at,
        generator_type=package.generator_type,
        template_style=package.template_style,
        word_count=package.word_count,
        status=AppealStatus(package.status) if package.status else AppealStatus.GENERATED
    )


@router.post("/generate", response_model=APIResponse[AppealPackageResponse])
async def generate_appeal(
    request: GenerateAppealRequest,
    generator: AppealGenerator = Depends(get_appeal_generator),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate a property tax appeal letter.

    The appeal includes:
    - Formal appeal letter in selected style (formal, detailed, or concise)
    - Executive summary with key findings
    - Evidence summary with bullet points
    - Comparable properties analysis
    - Filing instructions and deadlines

    Returns the complete appeal package ready for submission.

    **Request Body:**
    - `property_id`: Property UUID (optional if parcel_id provided)
    - `parcel_id`: Parcel ID (optional if property_id provided)
    - `style`: Letter style - "formal", "detailed", or "concise"
    - `include_comparables`: Whether to include comparables table
    - `save_to_database`: Whether to save the appeal
    - `mill_rate`: Mill rate for tax calculations (default: 65.0)

    **Returns:**
    Complete appeal package with letter, summaries, and filing information.
    """
    engine = get_engine()

    # Resolve property identifier using centralized resolver
    identifier = request.parcel_id or request.property_id
    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Either property_id or parcel_id must be provided"
        )

    resolved = resolve_property(engine, identifier)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"Property not found: {identifier}"
        )

    parcel_id = resolved.parcel_id

    try:
        # Configure generator
        config = GeneratorConfig(
            template_style=request.style.value,
            mill_rate=request.mill_rate,
            save_to_database=request.save_to_database,
            include_comparables=request.include_comparables,
        )
        generator.config = config

        # Generate appeal
        package = generator.generate_appeal(parcel_id)

        if not package:
            raise HTTPException(
                status_code=422,
                detail="Property does not qualify for appeal (score < 50 or insufficient comparables)"
            )

        response = _package_to_response(package)
        return APIResponse(data=response)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Appeal generation failed for {parcel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Appeal generation failed: {str(e)}")


@router.post("/generate/{property_id}", response_model=APIResponse[AppealPackageResponse])
async def generate_appeal_by_id(
    property_id: str,
    style: TemplateStyle = Query(TemplateStyle.FORMAL, description="Letter style"),
    save: bool = Query(False, description="Save appeal to database"),
    generator: AppealGenerator = Depends(get_appeal_generator),
    api_key: str = Depends(verify_api_key)
):
    """
    Convenience endpoint to generate appeal by property ID in path.

    **Path Parameters:**
    - `property_id`: Property UUID or Parcel ID

    **Query Parameters:**
    - `style`: Letter style - "formal", "detailed", or "concise"
    - `save`: Whether to save the appeal to database
    """
    request = GenerateAppealRequest(
        property_id=property_id,
        parcel_id=property_id,  # Also try as parcel_id
        style=style,
        save_to_database=save
    )
    return await generate_appeal(request, generator, api_key)


@router.post("/generate/{property_id}/pdf")
async def generate_appeal_pdf(
    property_id: str,
    style: TemplateStyle = Query(TemplateStyle.FORMAL, description="Letter style"),
    generator: AppealGenerator = Depends(get_appeal_generator),
    pdf_gen: PDFGenerator = Depends(get_pdf_generator),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate appeal and return as downloadable PDF.

    **Path Parameters:**
    - `property_id`: Property UUID or Parcel ID

    **Query Parameters:**
    - `style`: Letter style - "formal", "detailed", or "concise"

    **Returns:**
    PDF file as download attachment.
    """
    try:
        # Configure generator
        config = GeneratorConfig(
            template_style=style.value,
            include_comparables=True,
        )
        generator.config = config

        # Generate appeal (try as parcel_id first, then as UUID)
        package = generator.generate_appeal(property_id)

        if not package:
            raise HTTPException(
                status_code=422,
                detail="Property does not qualify for appeal"
            )

        # Generate PDF
        pdf_bytes = pdf_gen.generate_pdf_bytes(package)

        filename = f"appeal_{package.parcel_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed for {property_id}: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/batch", response_model=BatchAppealResponse)
async def batch_generate_appeals(
    request: BatchAppealRequest,
    generator: AppealGenerator = Depends(get_appeal_generator),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate appeals for multiple properties.

    **Limits:**
    - Maximum 20 properties per request
    - Properties that don't qualify (score < 50) are skipped

    **Request Body:**
    - `property_ids`: List of property UUIDs or Parcel IDs (max 20)
    - `style`: Letter style for all appeals
    - `save_to_database`: Whether to save appeals

    **Returns:**
    Batch results with generated appeals and aggregate statistics.
    """
    if len(request.property_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 properties per batch request"
        )

    # Configure generator
    config = GeneratorConfig(
        template_style=request.style.value,
        save_to_database=request.save_to_database,
    )
    generator.config = config

    # Generate batch
    result = generator.generate_batch(request.property_ids, config)

    # Convert to response format
    appeals = [_package_to_response(pkg) for pkg in result.appeals]

    return BatchAppealResponse(
        total_requested=result.total_requested,
        generated=result.generated,
        skipped=result.skipped,
        errors=result.errors,
        total_potential_savings=cents_to_dollars(result.total_potential_savings_cents) or 0,
        appeals=appeals
    )


@router.get("/list", response_model=APIResponse[List[AppealListItem]])
async def list_appeals(
    status: Optional[AppealStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    api_key: str = Depends(verify_api_key)
):
    """
    List saved appeals with optional status filter.

    **Query Parameters:**
    - `status`: Filter by appeal status (optional)
    - `limit`: Maximum number of results (1-100, default: 20)
    - `offset`: Number of results to skip (default: 0)

    **Returns:**
    List of appeal summaries.
    """
    engine = get_engine()

    from sqlalchemy import text

    try:
        # Check if tax_appeals table exists
        with engine.connect() as conn:
            check_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'tax_appeals'
                )
            """)
            exists = conn.execute(check_query).scalar()

            if not exists:
                return APIResponse(data=[])

            # Build query
            conditions = ["1=1"]
            params = {"limit": limit, "offset": offset}

            if status:
                conditions.append("ta.status = :status")
                params["status"] = status.value

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT ta.id, ta.property_id, p.parcel_id, p.ph_add as street_address,
                       ta.status, ta.reduction_amount_cents, ta.created_at
                FROM tax_appeals ta
                JOIN properties p ON ta.property_id = p.id
                WHERE {where_clause}
                ORDER BY ta.created_at DESC
                LIMIT :limit OFFSET :offset
            """)

            results = conn.execute(query, params)

            appeals = []
            for row in results.mappings():
                appeals.append(AppealListItem(
                    appeal_id=str(row["id"]),
                    property_id=str(row["property_id"]),
                    parcel_id=row["parcel_id"],
                    address=row["street_address"],
                    status=AppealStatus(row["status"]) if row["status"] else AppealStatus.GENERATED,
                    estimated_savings=cents_to_dollars(row.get("reduction_amount_cents")),
                    generated_at=row["created_at"]
                ))

            return APIResponse(data=appeals)

    except Exception as e:
        logger.error(f"Failed to list appeals: {e}")
        # Return empty list on error
        return APIResponse(data=[])


@router.get("/{appeal_id}", response_model=APIResponse[AppealPackageResponse])
async def get_appeal(
    appeal_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get a saved appeal by ID.

    **Path Parameters:**
    - `appeal_id`: Appeal UUID

    **Returns:**
    Complete appeal package.
    """
    engine = get_engine()

    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # Check if tax_appeals table exists
            check_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'tax_appeals'
                )
            """)
            exists = conn.execute(check_query).scalar()

            if not exists:
                raise HTTPException(status_code=404, detail="Appeal not found")

            query = text("""
                SELECT
                    ta.id,
                    ta.property_id,
                    ta.status,
                    ta.original_assessed_value_cents,
                    ta.requested_value_cents,
                    ta.reduction_amount_cents,
                    ta.appeal_letter_text,
                    ta.success_probability,
                    ta.created_at,
                    p.parcel_id,
                    p.ph_add as street_address,
                    p.ow_name as owner_name
                FROM tax_appeals ta
                JOIN properties p ON ta.property_id = p.id
                WHERE ta.id::text = :appeal_id
            """)

            result = conn.execute(query, {"appeal_id": appeal_id})
            row = result.mappings().first()

            if not row:
                raise HTTPException(status_code=404, detail="Appeal not found")

            # Calculate filing deadline
            today = date.today()
            deadline = date(today.year if today.month <= 5 else today.year + 1, 5, 31)

            return APIResponse(data=AppealPackageResponse(
                appeal_id=str(row["id"]),
                property_id=str(row["property_id"]),
                parcel_id=row["parcel_id"],
                address=row["street_address"],
                owner_name=row["owner_name"],
                current_assessed_value=cents_to_dollars(row.get("original_assessed_value_cents")),
                requested_assessed_value=cents_to_dollars(row.get("requested_value_cents")),
                estimated_annual_savings=cents_to_dollars(row.get("reduction_amount_cents")),
                appeal_letter=row.get("appeal_letter_text", ""),
                executive_summary=None,
                evidence_summary=None,
                fairness_score=int(row.get("success_probability", 0.5) * 100) if row.get("success_probability") else 50,
                confidence_level=80,
                comparable_count=0,
                jurisdiction="Benton County Board of Equalization",
                filing_deadline=deadline,
                required_forms=["Written Statement of Appeal"],
                statute_reference="Arkansas Code § 26-27-301",
                generated_at=row["created_at"],
                generator_type="TEMPLATE",
                template_style="formal",
                word_count=len(row.get("appeal_letter_text", "").split()) if row.get("appeal_letter_text") else 0,
                status=AppealStatus(row["status"]) if row["status"] else AppealStatus.GENERATED
            ))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get appeal {appeal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve appeal: {str(e)}")


@router.delete("/{appeal_id}", response_model=APIResponse)
async def delete_appeal(
    appeal_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a saved appeal.

    **Path Parameters:**
    - `appeal_id`: Appeal UUID

    **Returns:**
    Success confirmation.
    """
    engine = get_engine()

    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # Check if exists
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM tax_appeals WHERE id::text = :appeal_id
                )
            """)
            exists = conn.execute(check_query, {"appeal_id": appeal_id}).scalar()

            if not exists:
                raise HTTPException(status_code=404, detail="Appeal not found")

            # Delete
            delete_query = text("DELETE FROM tax_appeals WHERE id::text = :appeal_id")
            conn.execute(delete_query, {"appeal_id": appeal_id})
            conn.commit()

            return APIResponse(data={"deleted": True, "appeal_id": appeal_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete appeal {appeal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete appeal: {str(e)}")


@router.patch("/{appeal_id}/status", response_model=APIResponse[AppealListItem])
async def update_appeal_status(
    appeal_id: str,
    status: AppealStatus = Query(..., description="New status"),
    api_key: str = Depends(verify_api_key)
):
    """
    Update the status of a saved appeal.

    **Path Parameters:**
    - `appeal_id`: Appeal UUID

    **Query Parameters:**
    - `status`: New appeal status

    **Returns:**
    Updated appeal summary.
    """
    engine = get_engine()

    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # Update status
            update_query = text("""
                UPDATE tax_appeals
                SET status = :status, updated_at = CURRENT_TIMESTAMP
                WHERE id::text = :appeal_id
                RETURNING id, property_id, status, reduction_amount_cents, created_at
            """)

            result = conn.execute(update_query, {
                "appeal_id": appeal_id,
                "status": status.value
            })
            row = result.mappings().first()

            if not row:
                raise HTTPException(status_code=404, detail="Appeal not found")

            conn.commit()

            # Get parcel_id
            parcel_query = text("""
                SELECT parcel_id, ph_add FROM properties WHERE id = :property_id
            """)
            prop_result = conn.execute(parcel_query, {"property_id": row["property_id"]})
            prop_row = prop_result.mappings().first()

            return APIResponse(data=AppealListItem(
                appeal_id=str(row["id"]),
                property_id=str(row["property_id"]),
                parcel_id=prop_row["parcel_id"] if prop_row else "",
                address=prop_row["ph_add"] if prop_row else None,
                status=AppealStatus(row["status"]),
                estimated_savings=cents_to_dollars(row.get("reduction_amount_cents")),
                generated_at=row["created_at"]
            ))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update appeal status {appeal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update appeal: {str(e)}")
