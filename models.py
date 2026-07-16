"""Relational data models for AI Career Copilot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Shared creation and modification timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class User(TimestampMixin, Base):
    """Application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)

    uploaded_cvs: Mapped[list[UploadedCV]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    analyses: Mapped[list[AnalysisHistory]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list[CoverLetter]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    interview_questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    career_reports: Mapped[list[CareerReport]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UploadedCV(TimestampMixin, Base):
    """Uploaded CV and its extracted content."""

    __tablename__ = "uploaded_cv"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    file_type: Mapped[str] = mapped_column(String(10))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str] = mapped_column(Text)
    parsed_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="uploaded_cvs")
    analyses: Mapped[list[AnalysisHistory]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list[CoverLetter]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )
    interview_questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )
    career_reports: Mapped[list[CareerReport]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )


class AnalysisHistory(TimestampMixin, Base):
    """A complete resume analysis snapshot."""

    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_cv.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(30))
    model_name: Mapped[str] = mapped_column(String(100))
    ats_score: Mapped[float] = mapped_column(Float)
    analysis_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="analyses")
    cv: Mapped[UploadedCV] = relationship(back_populates="analyses")


class CoverLetter(TimestampMixin, Base):
    """Generated cover letter."""

    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_cv.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200), default="Belirtilmemiş")
    tone: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="cover_letters")
    cv: Mapped[UploadedCV] = relationship(back_populates="cover_letters")


class InterviewQuestion(TimestampMixin, Base):
    """Generated interview question and answer guidance."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_cv.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    answer_tips: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped[User] = relationship(back_populates="interview_questions")
    cv: Mapped[UploadedCV] = relationship(back_populates="interview_questions")


class CareerReport(TimestampMixin, Base):
    """Generated career advice and roadmap."""

    __tablename__ = "career_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_cv.id", ondelete="CASCADE"), index=True
    )
    target_role: Mapped[str] = mapped_column(String(200), default="Belirtilmemiş")
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="career_reports")
    cv: Mapped[UploadedCV] = relationship(back_populates="career_reports")
