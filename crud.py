"""Complete CRUD repositories for all database entities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from database import Base
from models import (
    AnalysisHistory,
    CareerReport,
    CoverLetter,
    InterviewQuestion,
    UploadedCV,
    User,
)


ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Reusable CRUD operations with explicit transaction flushing."""

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    def create(self, session: Session, **data: Any) -> ModelT:
        """Create and flush an entity."""
        entity = self.model(**data)
        session.add(entity)
        session.flush()
        session.refresh(entity)
        return entity

    def get(self, session: Session, entity_id: int) -> ModelT | None:
        """Get an entity by primary key."""
        return session.get(self.model, entity_id)

    def list(
        self,
        session: Session,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """List entities newest first with pagination."""
        statement = self._base_query().offset(offset).limit(limit)
        return session.scalars(statement).all()

    def update(
        self,
        session: Session,
        entity_id: int,
        **data: Any,
    ) -> ModelT | None:
        """Update allowed mapped attributes of an entity."""
        entity = self.get(session, entity_id)
        if entity is None:
            return None
        for field, value in data.items():
            if field in {"id", "created_at"} or not hasattr(entity, field):
                continue
            setattr(entity, field, value)
        session.flush()
        session.refresh(entity)
        return entity

    def delete(self, session: Session, entity_id: int) -> bool:
        """Delete an entity and report whether it existed."""
        entity = self.get(session, entity_id)
        if entity is None:
            return False
        session.delete(entity)
        session.flush()
        return True

    def _base_query(self) -> Select[tuple[ModelT]]:
        """Build a consistently ordered select query."""
        statement = select(self.model)
        if hasattr(self.model, "created_at"):
            statement = statement.order_by(self.model.created_at.desc())
        return statement


class UserRepository(Repository[User]):
    """User-specific persistence queries."""

    def get_by_email(self, session: Session, email: str) -> User | None:
        """Find a user by normalized e-mail address."""
        normalized = email.strip().lower()
        return session.scalar(select(User).where(User.email == normalized))

    def get_or_create(self, session: Session, name: str, email: str) -> User:
        """Return an existing user or create a new one."""
        normalized = email.strip().lower()
        user = self.get_by_email(session, normalized)
        if user is not None:
            if name.strip() and user.name != name.strip():
                user.name = name.strip()
                session.flush()
            return user
        return self.create(
            session,
            name=name.strip() or "Kullanıcı",
            email=normalized,
        )


class UploadedCVRepository(Repository[UploadedCV]):
    """CV-specific persistence queries."""

    def list_by_user(
        self, session: Session, user_id: int, limit: int = 100
    ) -> Sequence[UploadedCV]:
        """List a user's CVs newest first."""
        statement = (
            select(UploadedCV)
            .where(UploadedCV.user_id == user_id)
            .order_by(UploadedCV.created_at.desc())
            .limit(limit)
        )
        return session.scalars(statement).all()

    def get_by_hash(
        self, session: Session, user_id: int, file_hash: str
    ) -> UploadedCV | None:
        """Find a duplicate CV for one user by SHA-256 hash."""
        statement = select(UploadedCV).where(
            UploadedCV.user_id == user_id,
            UploadedCV.file_hash == file_hash,
        )
        return session.scalar(statement)


class AnalysisRepository(Repository[AnalysisHistory]):
    """Analysis-history persistence queries."""

    def list_by_user(
        self, session: Session, user_id: int, limit: int = 100
    ) -> Sequence[AnalysisHistory]:
        """List a user's analyses newest first."""
        statement = (
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user_id)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
        )
        return session.scalars(statement).all()

    def latest_for_cv(self, session: Session, cv_id: int) -> AnalysisHistory | None:
        """Return the most recent analysis for a CV."""
        statement = (
            select(AnalysisHistory)
            .where(AnalysisHistory.cv_id == cv_id)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(1)
        )
        return session.scalar(statement)


class CVChildRepository(Repository[ModelT]):
    """Shared filters for entities belonging to both a user and CV."""

    def list_by_user(
        self, session: Session, user_id: int, limit: int = 100
    ) -> Sequence[ModelT]:
        """List records belonging to a user."""
        statement = (
            self._base_query()
            .where(self.model.user_id == user_id)  # type: ignore[attr-defined]
            .limit(limit)
        )
        return session.scalars(statement).all()

    def list_by_cv(
        self, session: Session, cv_id: int, limit: int = 100
    ) -> Sequence[ModelT]:
        """List records belonging to a CV."""
        statement = (
            self._base_query()
            .where(self.model.cv_id == cv_id)  # type: ignore[attr-defined]
            .limit(limit)
        )
        return session.scalars(statement).all()


users = UserRepository(User)
uploaded_cvs = UploadedCVRepository(UploadedCV)
analyses = AnalysisRepository(AnalysisHistory)
cover_letters = CVChildRepository(CoverLetter)
interview_questions = CVChildRepository(InterviewQuestion)
career_reports = CVChildRepository(CareerReport)


REPOSITORIES: dict[str, Repository[Any]] = {
    "users": users,
    "uploaded_cv": uploaded_cvs,
    "analysis_history": analyses,
    "cover_letters": cover_letters,
    "interview_questions": interview_questions,
    "career_reports": career_reports,
}
