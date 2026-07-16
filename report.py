"""Professional PDF report generation with ReportLab."""

from __future__ import annotations

import io
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from schemas import CompleteAnalysis
from utils import logger


NAVY = colors.HexColor("#172554")
BLUE = colors.HexColor("#2563EB")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
SLATE = colors.HexColor("#475569")
GREEN = colors.HexColor("#059669")


def _register_font() -> tuple[str, str]:
    """Register Unicode fonts available on common Windows/Linux hosts."""
    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            try:
                pdfmetrics.registerFont(TTFont("CareerRegular", str(regular)))
                pdfmetrics.registerFont(TTFont("CareerBold", str(bold)))
                return "CareerRegular", "CareerBold"
            except Exception:
                continue
    logger.warning("unicode_pdf_font_not_found using_helvetica=true")
    return "Helvetica", "Helvetica-Bold"


class NumberedCanvasMixin:
    """Page decoration helper used through document callbacks."""

    @staticmethod
    def decorate(canvas: Any, document: Any, regular_font: str) -> None:
        """Draw a header line, footer and page number."""
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1)
        canvas.line(20 * mm, height - 17 * mm, width - 20 * mm, height - 17 * mm)
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(SLATE)
        canvas.drawString(20 * mm, 12 * mm, "AI Career Copilot • Gizli Kariyer Raporu")
        canvas.drawRightString(width - 20 * mm, 12 * mm, f"Sayfa {document.page}")
        canvas.restoreState()


class CareerReportGenerator:
    """Generate a seven-section, Unicode-compatible PDF report."""

    def __init__(self) -> None:
        self.regular_font, self.bold_font = _register_font()
        base_styles = getSampleStyleSheet()
        self.styles = {
            "title": ParagraphStyle(
                "CareerTitle",
                parent=base_styles["Title"],
                fontName=self.bold_font,
                fontSize=24,
                leading=29,
                textColor=NAVY,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            "subtitle": ParagraphStyle(
                "CareerSubtitle",
                parent=base_styles["Normal"],
                fontName=self.regular_font,
                fontSize=10,
                leading=15,
                textColor=SLATE,
                alignment=TA_CENTER,
                spaceAfter=18,
            ),
            "heading": ParagraphStyle(
                "CareerHeading",
                parent=base_styles["Heading2"],
                fontName=self.bold_font,
                fontSize=15,
                leading=19,
                textColor=NAVY,
                spaceBefore=12,
                spaceAfter=8,
            ),
            "body": ParagraphStyle(
                "CareerBody",
                parent=base_styles["BodyText"],
                fontName=self.regular_font,
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#1E293B"),
                spaceAfter=6,
            ),
            "bullet": ParagraphStyle(
                "CareerBullet",
                parent=base_styles["BodyText"],
                fontName=self.regular_font,
                fontSize=9.5,
                leading=14,
                leftIndent=12,
                firstLineIndent=-7,
                bulletIndent=4,
                spaceAfter=5,
            ),
        }

    def generate(
        self,
        analysis: CompleteAnalysis | dict[str, Any],
        output_path: Path | None = None,
    ) -> bytes:
        """Build and optionally persist a complete career report."""
        data = (
            analysis
            if isinstance(analysis, CompleteAnalysis)
            else CompleteAnalysis.model_validate(analysis)
        )
        buffer = io.BytesIO()
        target: io.BytesIO | str = buffer if output_path is None else str(output_path)
        document = SimpleDocTemplate(
            target,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=24 * mm,
            bottomMargin=20 * mm,
            title="AI Career Copilot Kariyer Raporu",
            author="AI Career Copilot",
        )
        story: list[Any] = []
        self._build_story(story, data)
        callback = lambda canvas, doc: NumberedCanvasMixin.decorate(  # noqa: E731
            canvas, doc, self.regular_font
        )
        document.build(story, onFirstPage=callback, onLaterPages=callback)

        if output_path is not None:
            pdf_bytes = output_path.read_bytes()
            logger.info(
                "pdf_report_saved path=%s bytes=%s", output_path, len(pdf_bytes)
            )
            return pdf_bytes
        pdf_bytes = buffer.getvalue()
        logger.info("pdf_report_generated bytes=%s", len(pdf_bytes))
        return pdf_bytes

    def _build_story(self, story: list[Any], data: CompleteAnalysis) -> None:
        """Compose all required report sections."""
        resume = data.parsed_resume
        story.extend(
            [
                Spacer(1, 12 * mm),
                Paragraph("AI Career Copilot", self.styles["title"]),
                Paragraph(
                    "Profesyonel CV ve Kariyer Analiz Raporu", self.styles["subtitle"]
                ),
                Paragraph(
                    f"<b>Aday:</b> {escape(resume.full_name)}",
                    self.styles["body"],
                ),
                Paragraph(
                    "Bu rapor yalnızca yüklenen CV'de bulunan bilgiler ve açıkça "
                    "belirtilen hedefler temel alınarak hazırlanmıştır.",
                    self.styles["subtitle"],
                ),
                PageBreak(),
            ]
        )

        self._heading(story, "1. Genel CV Özeti")
        self._paragraph(story, resume.professional_summary)
        self._paragraph(
            story,
            f"Deneyim kaydı: {len(resume.experience)} • Eğitim kaydı: "
            f"{len(resume.education)} • Proje: {len(resume.projects)}",
        )
        self._bullets(story, resume.skills or ["Belirtilmemiş"])

        self._heading(story, "2. ATS Puanı")
        self._score_card(story, data)
        for criterion, explanation in data.ats.criteria_explanations.items():
            self._paragraph(story, f"{criterion}: {explanation}")

        self._heading(story, "3. Güçlü Yönler")
        strengths = list(dict.fromkeys(data.improvement.strengths + data.ats.strengths))
        self._bullets(story, strengths or ["Belirtilmemiş"])

        self._heading(story, "4. Geliştirilmesi Gereken Alanlar")
        self._bullets(story, data.improvement.missing_areas or ["Belirtilmemiş"])
        self._paragraph(story, data.improvement.length_feedback)

        self._heading(story, "5. AI Önerileri")
        self._bullets(
            story,
            data.improvement.prioritized_recommendations
            or data.ats.recommendations
            or ["Belirtilmemiş"],
        )

        self._heading(story, "6. Kariyer Yol Haritası")
        self._paragraph(story, f"Hedef rol: {data.career.target_role}")
        self._bullets(story, data.career.roadmap or ["Belirtilmemiş"])
        self._paragraph(story, f"Maaş yaklaşımı: {data.career.salary_guidance}")

        self._heading(story, "7. Mülakat Tavsiyeleri")
        self._bullets(story, data.interview.general_tips or ["Belirtilmemiş"])
        for item in data.interview.questions[:8]:
            self._paragraph(story, f"{item.category}: {item.question}")
            self._bullets(story, item.answer_tips)

    def _heading(self, story: list[Any], text: str) -> None:
        """Append a section heading."""
        story.append(Paragraph(escape(text), self.styles["heading"]))

    def _paragraph(self, story: list[Any], text: str) -> None:
        """Append escaped body text."""
        story.append(
            Paragraph(escape(str(text)).replace("\n", "<br/>"), self.styles["body"])
        )

    def _bullets(self, story: list[Any], items: list[str]) -> None:
        """Append escaped bullet items."""
        for item in items:
            story.append(Paragraph(f"• {escape(str(item))}", self.styles["bullet"]))

    def _score_card(self, story: list[Any], data: CompleteAnalysis) -> None:
        """Append ATS score and weighted breakdown table."""
        breakdown = data.ats.breakdown
        rows = [
            ["Toplam ATS Puanı", f"{data.ats.score:.1f} / 100"],
            ["Anahtar Kelimeler", f"{breakdown.keywords:.1f} / 20"],
            ["Başlık Yapısı", f"{breakdown.headings:.1f} / 15"],
            ["Okunabilirlik", f"{breakdown.readability:.1f} / 15"],
            ["Deneyim", f"{breakdown.experience:.1f} / 20"],
            ["Teknik Beceriler", f"{breakdown.technical_skills:.1f} / 15"],
            ["Eğitim", f"{breakdown.education:.1f} / 10"],
            ["Sertifikalar", f"{breakdown.certificates:.1f} / 5"],
        ]
        table = Table(rows, colWidths=[105 * mm, 45 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.regular_font),
                    ("FONTNAME", (0, 0), (-1, 0), self.bold_font),
                    ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BLUE),
                    ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
