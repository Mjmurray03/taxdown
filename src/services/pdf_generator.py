"""
PDF Generator Service

This service generates professional PDF documents from appeal packages.
Supports multiple output formats and customization options.

Usage:
    from src.services.pdf_generator import PDFGenerator
    from src.services.appeal_models import AppealPackage

    pdf_gen = PDFGenerator()
    pdf_bytes = pdf_gen.generate_pdf_bytes(appeal_package)

    # Or save directly to file
    pdf_gen.generate_pdf_file(appeal_package, "appeal_output.pdf")
"""

import io
import logging
from datetime import datetime
from typing import Optional, List

from .appeal_models import AppealPackage, ComparablePropertySummary

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Raised when PDF generation fails."""
    pass


class PDFGenerator:
    """
    Generates professional PDF documents from appeal packages.

    This generator creates formatted PDF documents including:
    - Cover page with property information
    - Appeal letter
    - Executive summary
    - Evidence summary
    - Comparable properties table
    - Filing instructions

    The generator uses ReportLab if available, falling back to
    a plain text format if ReportLab is not installed.
    """

    def __init__(
        self,
        include_cover_page: bool = True,
        include_comparables: bool = True,
        include_filing_info: bool = True,
        company_name: str = "Property Tax Appeal Services",
        company_logo_path: Optional[str] = None
    ):
        """
        Initialize the PDF Generator.

        Args:
            include_cover_page: Whether to include a cover page
            include_comparables: Whether to include comparable properties table
            include_filing_info: Whether to include filing instructions
            company_name: Name to display on documents
            company_logo_path: Path to logo image (optional)
        """
        self.include_cover_page = include_cover_page
        self.include_comparables = include_comparables
        self.include_filing_info = include_filing_info
        self.company_name = company_name
        self.company_logo_path = company_logo_path

        # Check if ReportLab is available
        self._reportlab_available = self._check_reportlab()

    def _check_reportlab(self) -> bool:
        """Check if ReportLab is available."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate
            return True
        except ImportError:
            logger.warning(
                "ReportLab not installed. PDF generation will fall back to plain text. "
                "Install with: pip install reportlab"
            )
            return False

    def generate_pdf_bytes(self, package: AppealPackage) -> bytes:
        """
        Generate PDF and return as bytes.

        Args:
            package: AppealPackage containing appeal data

        Returns:
            PDF document as bytes
        """
        if self._reportlab_available:
            return self._generate_reportlab_pdf(package)
        else:
            return self._generate_text_fallback(package)

    def generate_pdf_file(self, package: AppealPackage, output_path: str) -> str:
        """
        Generate PDF and save to file.

        Args:
            package: AppealPackage containing appeal data
            output_path: Path to save the PDF file

        Returns:
            Path to the generated file
        """
        pdf_bytes = self.generate_pdf_bytes(package)

        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

        logger.info(f"PDF saved to {output_path}")
        return output_path

    def _generate_reportlab_pdf(self, package: AppealPackage) -> bytes:
        """Generate PDF using ReportLab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
            HRFlowable
        )
        from reportlab.lib import colors

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        # Define styles
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=HexColor('#1a365d'),
            alignment=1  # Center
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=HexColor('#2c5282'),
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=8,
            textColor=HexColor('#4a5568'),
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=8,
        )

        small_style = ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=HexColor('#718096'),
        )

        # Build document content
        story = []

        # Cover Page
        if self.include_cover_page:
            story.extend(self._build_cover_page(package, title_style, body_style, small_style))
            story.append(PageBreak())

        # Appeal Letter
        story.append(Paragraph("PROPERTY TAX ASSESSMENT APPEAL", title_style))
        story.append(HRFlowable(width="100%", thickness=2, color=HexColor('#2c5282')))
        story.append(Spacer(1, 0.2 * inch))

        # Property info box
        property_info = [
            ['Parcel ID:', package.parcel_id],
            ['Property Address:', package.address or 'N/A'],
            ['Owner:', package.owner_name or 'N/A'],
            ['Current Assessed Value:', f"${package.current_assessed_value_cents / 100:,.2f}"],
            ['Requested Assessed Value:', f"${package.requested_assessed_value_cents / 100:,.2f}"],
        ]

        info_table = Table(property_info, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f7fafc')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))

        # Appeal letter content
        story.append(Paragraph("Appeal Letter", heading_style))
        for para in package.appeal_letter_text.split('\n\n'):
            if para.strip():
                # Handle line breaks within paragraphs
                formatted_para = para.replace('\n', '<br/>')
                story.append(Paragraph(formatted_para, body_style))
                story.append(Spacer(1, 0.1 * inch))

        story.append(PageBreak())

        # Executive Summary
        if package.executive_summary:
            story.append(Paragraph("Executive Summary", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')))
            story.append(Spacer(1, 0.1 * inch))

            for line in package.executive_summary.split('\n'):
                if line.strip():
                    if line.startswith('=') or line.startswith('-'):
                        continue
                    story.append(Paragraph(line, body_style))

            story.append(Spacer(1, 0.2 * inch))

        # Evidence Summary
        if package.evidence_summary:
            story.append(Paragraph("Evidence Summary", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')))
            story.append(Spacer(1, 0.1 * inch))

            for line in package.evidence_summary.split('\n'):
                if line.strip() and not line.startswith('='):
                    if line.strip().startswith('•'):
                        story.append(Paragraph(line, body_style))
                    else:
                        story.append(Paragraph(line, body_style))

            story.append(Spacer(1, 0.2 * inch))

        # Comparable Properties Table
        if self.include_comparables and package.comparables:
            story.append(PageBreak())
            story.append(Paragraph("Comparable Properties Analysis", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')))
            story.append(Spacer(1, 0.1 * inch))

            story.extend(self._build_comparables_table(package.comparables))

        # Filing Information
        if self.include_filing_info:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("Filing Information", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')))
            story.append(Spacer(1, 0.1 * inch))

            filing_info = [
                f"<b>Jurisdiction:</b> {package.jurisdiction}",
                f"<b>Filing Deadline:</b> {package.filing_deadline.strftime('%B %d, %Y') if package.filing_deadline else 'N/A'}",
                f"<b>Required Forms:</b> {', '.join(package.required_forms)}",
                f"<b>Legal Reference:</b> {package.statute_reference}",
            ]

            for info in filing_info:
                story.append(Paragraph(info, body_style))

        # Footer
        story.append(Spacer(1, 0.5 * inch))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')))
        story.append(Paragraph(
            f"Generated on {package.generated_at.strftime('%B %d, %Y at %I:%M %p')} | "
            f"Appeal ID: {package.appeal_id}",
            small_style
        ))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        return buffer.read()

    def _build_cover_page(self, package: AppealPackage, title_style, body_style, small_style) -> list:
        """Build cover page elements."""
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.colors import HexColor

        elements = []

        elements.append(Spacer(1, 1.5 * inch))
        elements.append(Paragraph("PROPERTY TAX APPEAL", title_style))
        elements.append(Paragraph("DOCUMENTATION PACKAGE", title_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Property details box
        details = [
            ['PROPERTY INFORMATION', ''],
            ['Parcel ID:', package.parcel_id],
            ['Address:', package.address or 'N/A'],
            ['Owner:', package.owner_name or 'N/A'],
            ['', ''],
            ['ASSESSMENT DETAILS', ''],
            ['Current Assessed Value:', f"${package.current_assessed_value_cents / 100:,.2f}"],
            ['Requested Assessed Value:', f"${package.requested_assessed_value_cents / 100:,.2f}"],
            ['Potential Annual Savings:', f"${package.estimated_annual_savings_cents / 100:,.2f}"],
            ['', ''],
            ['ANALYSIS SUMMARY', ''],
            ['Fairness Score:', f"{package.fairness_score}/100"],
            ['Confidence Level:', f"{package.confidence_level}%"],
            ['Comparables Analyzed:', str(package.comparable_count)],
        ]

        detail_table = Table(details, colWidths=[2.5 * inch, 3.5 * inch])
        detail_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 5), (0, 5), 'Helvetica-Bold'),
            ('FONTNAME', (0, 10), (0, 10), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (0, 5), (1, 5)),
            ('SPAN', (0, 10), (1, 10)),
            ('BACKGROUND', (0, 0), (1, 0), HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (1, 0), HexColor('#ffffff')),
            ('BACKGROUND', (0, 5), (1, 5), HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 5), (1, 5), HexColor('#ffffff')),
            ('BACKGROUND', (0, 10), (1, 10), HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 10), (1, 10), HexColor('#ffffff')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#2c5282')),
            ('LINEABOVE', (0, 5), (-1, 5), 1, HexColor('#2c5282')),
            ('LINEABOVE', (0, 10), (-1, 10), 1, HexColor('#2c5282')),
        ]))

        elements.append(detail_table)
        elements.append(Spacer(1, 1 * inch))

        # Filing info
        if package.filing_deadline:
            elements.append(Paragraph(
                f"<b>Filing Deadline:</b> {package.filing_deadline.strftime('%B %d, %Y')}",
                body_style
            ))

        elements.append(Paragraph(
            f"<b>Jurisdiction:</b> {package.jurisdiction}",
            body_style
        ))

        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(
            f"Generated: {package.generated_at.strftime('%B %d, %Y')}",
            small_style
        ))

        return elements

    def _build_comparables_table(self, comparables: List[ComparablePropertySummary]) -> list:
        """Build comparable properties table."""
        from reportlab.lib.units import inch
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.colors import HexColor
        from reportlab.lib.styles import getSampleStyleSheet

        styles = getSampleStyleSheet()
        small_style = styles['Normal']
        small_style.fontSize = 8

        elements = []

        # Build table data
        headers = ['Parcel ID', 'Address', 'Total Value', 'Assessed', 'Ratio']
        data = [headers]

        for comp in comparables[:10]:  # Limit to 10 for space
            address = comp.address[:25] + '...' if len(comp.address) > 28 else comp.address
            data.append([
                comp.parcel_id,
                address,
                f"${comp.total_value_cents / 100:,.0f}",
                f"${comp.assessed_value_cents / 100:,.0f}",
                f"{comp.assessment_ratio:.1%}"
            ])

        # Add average row
        if comparables:
            avg_total = sum(c.total_value_cents for c in comparables) / len(comparables)
            avg_assessed = sum(c.assessed_value_cents for c in comparables) / len(comparables)
            avg_ratio = sum(c.assessment_ratio for c in comparables) / len(comparables)
            data.append([
                'AVERAGE',
                '',
                f"${avg_total / 100:,.0f}",
                f"${avg_assessed / 100:,.0f}",
                f"{avg_ratio:.1%}"
            ])

        table = Table(data, colWidths=[1.3 * inch, 2.2 * inch, 1.1 * inch, 1.1 * inch, 0.8 * inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#edf2f7')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e0')),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.1 * inch))

        return elements

    def _generate_text_fallback(self, package: AppealPackage) -> bytes:
        """Generate plain text fallback when ReportLab is not available."""
        lines = [
            "=" * 70,
            "PROPERTY TAX ASSESSMENT APPEAL",
            "=" * 70,
            "",
            f"Generated: {package.generated_at.strftime('%B %d, %Y %I:%M %p')}",
            f"Appeal ID: {package.appeal_id}",
            "",
            "-" * 70,
            "PROPERTY INFORMATION",
            "-" * 70,
            f"Parcel ID: {package.parcel_id}",
            f"Address: {package.address}",
            f"Owner: {package.owner_name or 'N/A'}",
            "",
            f"Current Assessed Value: ${package.current_assessed_value_cents / 100:,.2f}",
            f"Requested Assessed Value: ${package.requested_assessed_value_cents / 100:,.2f}",
            f"Potential Annual Savings: ${package.estimated_annual_savings_cents / 100:,.2f}",
            "",
            "-" * 70,
            "ANALYSIS SUMMARY",
            "-" * 70,
            f"Fairness Score: {package.fairness_score}/100",
            f"Confidence Level: {package.confidence_level}%",
            f"Comparables Analyzed: {package.comparable_count}",
            "",
            "=" * 70,
            "APPEAL LETTER",
            "=" * 70,
            "",
            package.appeal_letter_text,
            "",
        ]

        if package.executive_summary:
            lines.extend([
                "=" * 70,
                "EXECUTIVE SUMMARY",
                "=" * 70,
                "",
                package.executive_summary,
                "",
            ])

        if package.evidence_summary:
            lines.extend([
                "=" * 70,
                "EVIDENCE SUMMARY",
                "=" * 70,
                "",
                package.evidence_summary,
                "",
            ])

        if package.comparables_table:
            lines.extend([
                "=" * 70,
                "COMPARABLE PROPERTIES",
                "=" * 70,
                "",
                package.comparables_table,
                "",
            ])

        lines.extend([
            "=" * 70,
            "FILING INFORMATION",
            "=" * 70,
            f"Jurisdiction: {package.jurisdiction}",
            f"Filing Deadline: {package.filing_deadline.strftime('%B %d, %Y') if package.filing_deadline else 'N/A'}",
            f"Required Forms: {', '.join(package.required_forms)}",
            f"Legal Reference: {package.statute_reference}",
            "",
            "=" * 70,
        ])

        return '\n'.join(lines).encode('utf-8')


# ============================================================================
# TEST SECTION
# ============================================================================

if __name__ == "__main__":
    """Test PDF generation with a sample appeal package."""
    from datetime import date

    print("Testing PDF Generator...")

    # Create sample package
    package = AppealPackage(
        property_id="test-uuid-123",
        parcel_id="16-26005-000",
        address="123 Main Street, Bentonville, AR 72712",
        owner_name="John Smith",
        current_assessed_value_cents=15000000,
        current_total_value_cents=75000000,
        current_assessment_ratio=0.20,
        requested_assessed_value_cents=13500000,
        target_assessment_ratio=0.18,
        estimated_annual_savings_cents=97500,
        estimated_five_year_savings_cents=487500,
        reduction_amount_cents=1500000,
        appeal_letter_text="""December 8, 2025

Benton County Board of Equalization
215 E Central Ave, Suite 217
Bentonville, AR 72712

RE: Property Tax Assessment Appeal
Parcel ID: 16-26005-000
Property Address: 123 Main Street, Bentonville, AR 72712

Dear Members of the Board of Equalization:

I am writing to formally appeal the current assessed value of my property at the address listed above. The current assessed value of $150,000.00 does not reflect fair market value when compared to similar properties in the area.

Based on an analysis of 10 comparable properties in Benton County, the typical assessment ratio is 18.0% of market value. My property is currently assessed at 20.0%, which is 2.0 percentage points higher than comparable properties.

I respectfully request that the assessed value be reduced to $135,000.00.

Thank you for your consideration.

Respectfully,

John Smith""",
        executive_summary="EXECUTIVE SUMMARY\n\nProperty shows signs of over-assessment based on comparable analysis.",
        evidence_summary="EVIDENCE SUMMARY\n\n• Property assessed 2% higher than comparables\n• 10 comparable properties analyzed",
        fairness_score=72,
        confidence_level=85,
        comparable_count=10,
        filing_deadline=date(2025, 5, 31),
    )

    generator = PDFGenerator()
    pdf_bytes = generator.generate_pdf_bytes(package)

    print(f"Generated PDF: {len(pdf_bytes)} bytes")

    # Save test file
    with open("test_appeal.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("Saved to test_appeal.pdf")
