"""Validated data contracts shared by AI agents and the UI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NOT_SPECIFIED = "Belirtilmemiş"


class StrictSchema(BaseModel):
    """Base schema that rejects unexpected model output fields."""

    model_config = ConfigDict(extra="forbid")


class EducationItem(StrictSchema):
    """Education entry extracted from a CV."""

    institution: str = NOT_SPECIFIED
    degree: str = NOT_SPECIFIED
    field: str = NOT_SPECIFIED
    date: str = NOT_SPECIFIED


class ExperienceItem(StrictSchema):
    """Professional experience entry extracted from a CV."""

    company: str = NOT_SPECIFIED
    position: str = NOT_SPECIFIED
    date: str = NOT_SPECIFIED
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class ProjectItem(StrictSchema):
    """Project entry extracted from a CV."""

    name: str = NOT_SPECIFIED
    description: str = NOT_SPECIFIED
    technologies: list[str] = Field(default_factory=list)
    link: str = NOT_SPECIFIED


class ParsedResume(StrictSchema):
    """Structured representation of a CV without invented facts."""

    full_name: str = NOT_SPECIFIED
    professional_summary: str = NOT_SPECIFIED
    contact: dict[str, str] = Field(default_factory=dict)
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)


class ATSBreakdown(StrictSchema):
    """Weighted ATS scoring dimensions."""

    keywords: float = Field(ge=0, le=20)
    headings: float = Field(ge=0, le=15)
    readability: float = Field(ge=0, le=15)
    experience: float = Field(ge=0, le=20)
    technical_skills: float = Field(ge=0, le=15)
    education: float = Field(ge=0, le=10)
    certificates: float = Field(ge=0, le=5)


class ATSResult(StrictSchema):
    """ATS score, evidence and recommendations."""

    score: float = Field(ge=0, le=100)
    breakdown: ATSBreakdown
    criteria_explanations: dict[str, str] = Field(default_factory=dict)
    detected_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ImprovementResult(StrictSchema):
    """Evidence-based CV improvement guidance."""

    strengths: list[str] = Field(default_factory=list)
    missing_areas: list[str] = Field(default_factory=list)
    prioritized_recommendations: list[str] = Field(default_factory=list)
    improved_summary: str = NOT_SPECIFIED
    length_feedback: str = NOT_SPECIFIED


class CoverLetterResult(StrictSchema):
    """Generated cover letter response."""

    tone: Literal["Resmi", "Samimi", "Kurumsal"]
    position: str
    company: str = NOT_SPECIFIED
    content: str


class InterviewQuestionItem(StrictSchema):
    """Interview question with non-fictional answer guidance."""

    category: Literal["Teknik", "İnsan Kaynakları", "Davranışsal", "Proje"]
    question: str
    answer_tips: list[str] = Field(default_factory=list)


class InterviewResult(StrictSchema):
    """Categorized interview preparation set."""

    questions: list[InterviewQuestionItem] = Field(default_factory=list)
    general_tips: list[str] = Field(default_factory=list)


class CareerReportResult(StrictSchema):
    """Career recommendations grounded in the CV."""

    current_profile: str = NOT_SPECIFIED
    target_role: str = NOT_SPECIFIED
    technologies_to_learn: list[str] = Field(default_factory=list)
    certificate_recommendations: list[str] = Field(default_factory=list)
    portfolio_recommendations: list[str] = Field(default_factory=list)
    level_transition_advice: list[str] = Field(default_factory=list)
    salary_guidance: str = NOT_SPECIFIED
    roadmap: list[str] = Field(default_factory=list)


class CompleteAnalysis(StrictSchema):
    """Combined output used by history and PDF reports."""

    parsed_resume: ParsedResume
    ats: ATSResult
    improvement: ImprovementResult
    interview: InterviewResult
    career: CareerReportResult
