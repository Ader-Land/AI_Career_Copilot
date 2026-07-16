"""PDF generation smoke test."""

from __future__ import annotations

import unittest

from report import CareerReportGenerator
from schemas import (
    ATSBreakdown,
    ATSResult,
    CareerReportResult,
    CompleteAnalysis,
    ImprovementResult,
    InterviewResult,
    ParsedResume,
)


class ReportTests(unittest.TestCase):
    """Ensure the seven-section report builds as a real PDF."""

    def test_generates_pdf_bytes(self) -> None:
        """Build a minimal valid report without external services."""
        analysis = CompleteAnalysis(
            parsed_resume=ParsedResume(full_name="Ayşe Yılmaz"),
            ats=ATSResult(
                score=50,
                breakdown=ATSBreakdown(
                    keywords=10,
                    headings=8,
                    readability=8,
                    experience=10,
                    technical_skills=7,
                    education=5,
                    certificates=2,
                ),
            ),
            improvement=ImprovementResult(),
            interview=InterviewResult(),
            career=CareerReportResult(),
        )
        content = CareerReportGenerator().generate(analysis)
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)


if __name__ == "__main__":
    unittest.main()
