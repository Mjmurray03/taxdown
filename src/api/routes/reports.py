"""
Report generation API routes.

Provides endpoints for generating PDF, CSV, Excel, and JSON reports
for portfolios and individual properties.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
from datetime import datetime
import tempfile
import os
import io
import json
import csv

from src.api.dependencies import (
    get_engine,
    verify_api_key,
    get_report_generator,
    get_assessment_analyzer,
)
from src.api.utils import resolve_to_parcel_id
from src.api.schemas.report import (
    GenerateReportRequest,
    ReportJobResponse,
    ReportMetadata,
    ReportFormat,
    ReportType,
)
from src.api.schemas.common import APIResponse, cents_to_dollars
from src.services import AssessmentAnalyzer

router = APIRouter(prefix="/reports", tags=["Reports"])

# Temporary storage for generated reports (in production, use S3 or similar)
TEMP_REPORTS_DIR = tempfile.mkdtemp(prefix="taxdown_reports_")


@router.post("/generate", response_model=ReportMetadata)
async def generate_report(
    request: GenerateReportRequest,
    generator=Depends(get_report_generator),
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a report and return metadata with download info.

    Supports:
    - Portfolio summary reports (PDF, CSV, Excel)
    - Property analysis reports
    - Appeal packages
    """
    if not request.portfolio_id and not request.property_id:
        raise HTTPException(
            status_code=400, detail="Either portfolio_id or property_id required"
        )

    try:
        # Build report options
        options = {
            "include_executive_summary": request.include_executive_summary,
            "include_property_details": request.include_property_details,
            "include_analysis_results": request.include_analysis_results,
            "include_recommendations": request.include_recommendations,
            "include_comparables": request.include_comparables,
            "include_geographic_breakdown": request.include_geographic_breakdown,
            "only_appeal_candidates": request.only_appeal_candidates,
            "min_fairness_score": request.min_fairness_score,
            "sort_by": request.sort_by,
            "sort_order": request.sort_order,
        }

        # Generate based on format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if request.format == ReportFormat.PDF:
            filename = f"report_{timestamp}.pdf"
            output_path = os.path.join(TEMP_REPORTS_DIR, filename)
            generator.generate_pdf_report(request.portfolio_id, output_path, options)

        elif request.format == ReportFormat.CSV:
            filename = f"report_{timestamp}.csv"
            output_path = os.path.join(TEMP_REPORTS_DIR, filename)
            generator.generate_csv_export(
                request.portfolio_id, output_path, request.include_analysis_results
            )

        elif request.format == ReportFormat.EXCEL:
            filename = f"report_{timestamp}.xlsx"
            output_path = os.path.join(TEMP_REPORTS_DIR, filename)
            generator.generate_excel_export(request.portfolio_id, output_path)

        elif request.format == ReportFormat.JSON:
            filename = f"report_{timestamp}.json"
            output_path = os.path.join(TEMP_REPORTS_DIR, filename)
            _generate_json_report(generator, request.portfolio_id, output_path, options)

        # Get file stats
        file_size = os.path.getsize(output_path)

        return ReportMetadata(
            filename=filename,
            format=request.format.value,
            size_bytes=file_size,
            generated_at=datetime.now().isoformat(),
            properties_included=0,  # Would need to track during generation
            total_value=None,
            total_savings=None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_report(filename: str, api_key: str = Depends(verify_api_key)):
    """Download a generated report by filename."""
    file_path = os.path.join(TEMP_REPORTS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found or expired")

    # Determine content type
    content_types = {
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
    }

    ext = os.path.splitext(filename)[1].lower()
    content_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(file_path, media_type=content_type, filename=filename)


@router.post("/portfolio/{portfolio_id}/pdf")
async def generate_portfolio_pdf(
    portfolio_id: str,
    only_appeal_candidates: bool = False,
    generator=Depends(get_report_generator),
    api_key: str = Depends(verify_api_key),
):
    """Generate and immediately download portfolio PDF report."""
    try:
        options = {"only_appeal_candidates": only_appeal_candidates}

        # Generate to temp file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_{portfolio_id[:8]}_{timestamp}.pdf"
        output_path = os.path.join(TEMP_REPORTS_DIR, filename)

        generator.generate_pdf_report(portfolio_id, output_path, options)

        return FileResponse(output_path, media_type="application/pdf", filename=filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/{portfolio_id}/csv")
async def generate_portfolio_csv(
    portfolio_id: str,
    include_analysis: bool = True,
    generator=Depends(get_report_generator),
    api_key: str = Depends(verify_api_key),
):
    """Generate and immediately download portfolio CSV export."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_{portfolio_id[:8]}_{timestamp}.csv"
        output_path = os.path.join(TEMP_REPORTS_DIR, filename)

        generator.generate_csv_export(portfolio_id, output_path, include_analysis)

        return FileResponse(output_path, media_type="text/csv", filename=filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/{portfolio_id}/excel")
async def generate_portfolio_excel(
    portfolio_id: str,
    generator=Depends(get_report_generator),
    api_key: str = Depends(verify_api_key),
):
    """Generate and immediately download portfolio Excel workbook."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_{portfolio_id[:8]}_{timestamp}.xlsx"
        output_path = os.path.join(TEMP_REPORTS_DIR, filename)

        generator.generate_excel_export(portfolio_id, output_path)

        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/{portfolio_id}/summary")
async def get_portfolio_summary_text(
    portfolio_id: str,
    generator=Depends(get_report_generator),
    api_key: str = Depends(verify_api_key),
):
    """Get portfolio summary as plain text."""
    try:
        summary = generator.generate_summary_text(portfolio_id)
        return {"status": "success", "data": {"summary": summary}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/property/{property_id}/analysis")
async def generate_property_analysis_report(
    property_id: str,
    format: ReportFormat = ReportFormat.PDF,
    include_comparables: bool = True,
    analyzer: AssessmentAnalyzer = Depends(get_assessment_analyzer),
    api_key: str = Depends(verify_api_key),
):
    """Generate analysis report for a single property."""
    try:
        # Resolve to parcel_id - analyzer expects parcel_id, not UUID
        parcel_id = resolve_to_parcel_id(get_engine(), property_id)
        if not parcel_id:
            raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")

        # Run analysis with parcel_id
        analysis = analyzer.analyze_property(parcel_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Property analysis failed")

        if format == ReportFormat.JSON:
            return {
                "status": "success",
                "data": {
                    "property_id": str(analysis.property_id),
                    "parcel_id": analysis.parcel_id,
                    "address": analysis.address,
                    "market_value": cents_to_dollars(analysis.total_value_cents),
                    "assessed_value": cents_to_dollars(analysis.assessed_value_cents),
                    "fairness_score": analysis.fairness_score,
                    "confidence_level": analysis.confidence_level,
                    "recommended_action": analysis.recommended_action,
                    "estimated_savings": cents_to_dollars(
                        analysis.estimated_annual_savings_cents
                    ),
                    "comparable_count": analysis.comparable_count,
                    "comparables": [
                        {
                            "parcel_id": c.parcel_id,
                            "address": c.address,
                            "value": cents_to_dollars(c.total_value_cents),
                            "assessment_ratio": c.assessment_ratio,
                        }
                        for c in (
                            analysis.comparables[:10] if include_comparables else []
                        )
                    ]
                    if analysis.comparables
                    else [],
                },
            }

        # For other formats, generate file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{analysis.parcel_id}_{timestamp}.{format.value}"
        output_path = os.path.join(TEMP_REPORTS_DIR, filename)

        # Generate based on format (simplified for single property)
        if format == ReportFormat.CSV:
            _generate_single_property_csv(analysis, output_path, include_comparables)
        else:
            # Default to JSON file for unsupported formats
            with open(output_path, "w") as f:
                json.dump({"analysis": _analysis_to_dict(analysis)}, f, default=str)

        content_types = {
            ReportFormat.CSV: "text/csv",
            ReportFormat.PDF: "application/pdf",
        }

        return FileResponse(
            output_path,
            media_type=content_types.get(format, "application/json"),
            filename=filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def _generate_json_report(generator, portfolio_id: str, output_path: str, options: dict):
    """Generate JSON report for portfolio."""
    # Get portfolio data from generator
    portfolio_data = generator.get_portfolio_data(portfolio_id)

    report_data = {
        "portfolio": {
            "id": portfolio_id,
            "name": portfolio_data.get("name", ""),
            "description": portfolio_data.get("description", ""),
        },
        "summary": {
            "total_properties": portfolio_data.get("total_properties", 0),
            "total_market_value": portfolio_data.get("total_market_value", 0),
            "total_assessed_value": portfolio_data.get("total_assessed_value", 0),
            "total_potential_savings": portfolio_data.get("total_potential_savings", 0),
            "appeal_candidates": portfolio_data.get("appeal_candidates", 0),
        },
        "properties": portfolio_data.get("properties", []),
        "generated_at": datetime.now().isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(report_data, f, indent=2)


def _generate_single_property_csv(analysis, output_path: str, include_comparables: bool):
    """Generate CSV for single property analysis."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Property details
        writer.writerow(["Property Analysis Report"])
        writer.writerow([])
        writer.writerow(["Parcel ID", analysis.parcel_id])
        writer.writerow(["Address", analysis.address])
        writer.writerow(
            ["Market Value", f"${cents_to_dollars(analysis.total_value_cents):,.2f}"]
        )
        writer.writerow(
            [
                "Assessed Value",
                f"${cents_to_dollars(analysis.assessed_value_cents):,.2f}",
            ]
        )
        writer.writerow(["Fairness Score", analysis.fairness_score])
        writer.writerow(["Confidence", f"{analysis.confidence_level}%"])
        writer.writerow(["Recommendation", analysis.recommended_action])
        writer.writerow(
            [
                "Estimated Savings",
                f"${cents_to_dollars(analysis.estimated_annual_savings_cents):,.2f}",
            ]
        )

        if include_comparables and analysis.comparables:
            writer.writerow([])
            writer.writerow(["Comparable Properties"])
            writer.writerow(["Parcel ID", "Address", "Value", "Assessment Ratio"])
            for c in analysis.comparables[:10]:
                writer.writerow(
                    [
                        c.parcel_id,
                        c.address,
                        f"${cents_to_dollars(c.total_value_cents):,.2f}",
                        f"{c.assessment_ratio:.2%}",
                    ]
                )


def _analysis_to_dict(analysis) -> dict:
    """Convert analysis object to dictionary."""
    return {
        "property_id": str(analysis.property_id),
        "parcel_id": analysis.parcel_id,
        "address": analysis.address,
        "total_value_cents": analysis.total_value_cents,
        "assessed_value_cents": analysis.assessed_value_cents,
        "fairness_score": analysis.fairness_score,
        "confidence_level": analysis.confidence_level,
        "recommended_action": analysis.recommended_action,
        "estimated_annual_savings_cents": analysis.estimated_annual_savings_cents,
        "comparable_count": analysis.comparable_count,
    }
