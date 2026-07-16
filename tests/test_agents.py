"""Agent guardrail and score consistency tests."""

from __future__ import annotations

import unittest
from typing import Any

from agents import ATSScoringAgent
from schemas import ATSBreakdown, ATSResult, ParsedResume


class FakeAIService:
    """Deterministic service double that avoids network requests."""

    def generate_structured(self, **_: Any) -> ATSResult:
        """Return an intentionally inconsistent total for correction."""
        return ATSResult(
            score=1,
            breakdown=ATSBreakdown(
                keywords=10,
                headings=10,
                readability=10,
                experience=10,
                technical_skills=10,
                education=5,
                certificates=2,
            ),
            criteria_explanations={},
        )


class AgentTests(unittest.TestCase):
    """Verify deterministic post-processing around AI responses."""

    def test_ats_total_is_sum_of_breakdown(self) -> None:
        """Never trust an arithmetically inconsistent model total."""
        agent = ATSScoringAgent(FakeAIService())  # type: ignore[arg-type]
        result = agent.score(ParsedResume())
        self.assertEqual(result.score, 57)


if __name__ == "__main__":
    unittest.main()
