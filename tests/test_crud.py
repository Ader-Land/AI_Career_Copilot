"""Database CRUD contract tests."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crud
from database import Base


class CRUDTests(unittest.TestCase):
    """Verify create, read, update, list and delete behavior."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_all_entity_crud(self) -> None:
        """Exercise all six repositories in one related data graph."""
        user = crud.users.create(
            self.session, name="Test User", email="test@example.com"
        )
        cv = crud.uploaded_cvs.create(
            self.session,
            user_id=user.id,
            original_filename="cv.pdf",
            stored_filename="hash_cv.pdf",
            file_type="pdf",
            file_hash="a" * 64,
            extracted_text="Test CV content sufficient for storage.",
            parsed_data={},
        )
        analysis = crud.analyses.create(
            self.session,
            user_id=user.id,
            cv_id=cv.id,
            provider="gemini",
            model_name="gemini-3.5-flash",
            ats_score=75,
            analysis_data={},
        )
        letter = crud.cover_letters.create(
            self.session,
            user_id=user.id,
            cv_id=cv.id,
            position="Developer",
            company="Belirtilmemiş",
            tone="Kurumsal",
            content="Test cover letter",
        )
        question = crud.interview_questions.create(
            self.session,
            user_id=user.id,
            cv_id=cv.id,
            category="Teknik",
            question="Test question?",
            answer_tips=["Test tip"],
        )
        report = crud.career_reports.create(
            self.session,
            user_id=user.id,
            cv_id=cv.id,
            target_role="Developer",
            report_data={},
        )
        self.assertEqual(
            crud.users.get(self.session, user.id).email, "test@example.com"
        )
        self.assertEqual(len(crud.uploaded_cvs.list_by_user(self.session, user.id)), 1)
        self.assertEqual(
            crud.analyses.latest_for_cv(self.session, cv.id).id, analysis.id
        )
        self.assertEqual(len(crud.cover_letters.list_by_cv(self.session, cv.id)), 1)
        self.assertIsNotNone(question.id)
        self.assertIsNotNone(report.id)
        updated = crud.cover_letters.update(
            self.session, letter.id, content="Updated content"
        )
        self.assertEqual(updated.content, "Updated content")
        self.assertTrue(crud.cover_letters.delete(self.session, letter.id))
        self.assertIsNone(crud.cover_letters.get(self.session, letter.id))


if __name__ == "__main__":
    unittest.main()
