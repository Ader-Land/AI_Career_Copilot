"""Streamlit interface for the AI Career Copilot SaaS application."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from pydantic import ValidationError
from sqlalchemy import func, select

import crud
from agents import (
    ATSScoringAgent,
    CareerAdvisorAgent,
    CareerCopilotCoordinator,
    CoverLetterAgent,
    InterviewCoachAgent,
    ResumeImprovementAgent,
    ResumeParserAgent,
    model_dump,
)
from ai_service import AIService
from config import settings
from database import init_db, session_scope
from models import (
    AnalysisHistory,
    CareerReport,
    CoverLetter,
    UploadedCV,
)
from parser import DocumentParseError, DocumentParser
from report import CareerReportGenerator
from schemas import ATSResult, CompleteAnalysis, ParsedResume
from utils import logger


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

PAGES = [
    "📊 Dashboard",
    "📄 CV Yükle",
    "🎯 ATS Analizi",
    "✨ CV İyileştirme",
    "✉️ Ön Yazı Oluştur",
    "🎤 Mülakat Hazırlığı",
    "🧭 Kariyer Danışmanı",
    "🕘 Geçmiş Analizler",
    "⚙️ Ayarlar",
]


def inject_styles() -> None:
    """Apply a compact professional visual theme."""
    st.markdown(
        """
        <style>
        .stApp { background: #f8fafc; }
        [data-testid="stSidebar"] { background: #0f172a; }
        [data-testid="stSidebar"] * { color: #e2e8f0; }
        .hero { padding: 1.4rem 1.6rem; border-radius: 18px;
                background: linear-gradient(120deg,#172554,#2563eb); color: white;
                margin-bottom: 1.2rem; box-shadow: 0 12px 28px #1e3a8a22; }
        .hero h1 { margin: 0; font-size: 2rem; }
        .hero p { margin: .4rem 0 0; color: #dbeafe; }
        div[data-testid="stMetric"] { background: white; border: 1px solid #e2e8f0;
                padding: .8rem; border-radius: 14px; }
        .result-card { background: white; padding: 1rem 1.2rem; border-radius: 14px;
                border: 1px solid #e2e8f0; margin: .55rem 0; }
        .muted { color: #64748b; font-size: .9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    """Render a consistent page heading."""
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def ensure_user() -> int:
    """Create or load the local Streamlit user."""
    if "user_id" in st.session_state:
        return int(st.session_state.user_id)
    with session_scope() as session:
        user = crud.users.get_or_create(session, "Kullanıcı", "kullanici@example.com")
        st.session_state.user_id = user.id
        st.session_state.user_name = user.name
        st.session_state.user_email = user.email
        return user.id


def create_ai_service() -> AIService:
    """Create an AI service for the provider selected in session state."""
    provider = st.session_state.get("ai_provider", settings.default_ai_provider)
    return AIService(provider)


def cv_selector(label: str = "CV seçin") -> UploadedCV | None:
    """Render a CV selector and return the selected detached entity."""
    with session_scope() as session:
        cvs = list(crud.uploaded_cvs.list_by_user(session, ensure_user()))
    if not cvs:
        st.info("Önce **CV Yükle** sayfasından bir PDF veya DOCX yükleyin.")
        return None
    labels = {
        cv.id: f"{cv.original_filename} · {cv.created_at:%d.%m.%Y %H:%M}" for cv in cvs
    }
    default_id = st.session_state.get("current_cv_id", cvs[0].id)
    ids = [cv.id for cv in cvs]
    index = ids.index(default_id) if default_id in ids else 0
    selected_id = st.selectbox(
        label,
        ids,
        index=index,
        format_func=lambda item_id: labels[item_id],
    )
    st.session_state.current_cv_id = selected_id
    return next(cv for cv in cvs if cv.id == selected_id)


def ensure_parsed_resume(cv: UploadedCV) -> ParsedResume:
    """Load structured CV data or create it with the parser agent."""
    if cv.parsed_data:
        try:
            return ParsedResume.model_validate(cv.parsed_data)
        except ValidationError:
            logger.warning("stored_resume_schema_invalid cv_id=%s", cv.id)
    resume = ResumeParserAgent(create_ai_service()).parse(cv.extracted_text)
    with session_scope() as session:
        crud.uploaded_cvs.update(session, cv.id, parsed_data=model_dump(resume))
    return resume


def show_items(title: str, items: list[str], empty: str = "Belirtilmemiş") -> None:
    """Render a titled collection as clean Markdown bullets."""
    st.subheader(title)
    if not items:
        st.caption(empty)
        return
    for item in items:
        st.markdown(f"- {item}")


def handle_ai_error(exc: Exception) -> None:
    """Log and display a safe AI error message."""
    logger.error("ui_ai_error type=%s error=%s", type(exc).__name__, exc, exc_info=True)
    st.error(f"AI işlemi tamamlanamadı: {exc}")
    if "API_KEY" in str(exc):
        st.info("API anahtarını `.env` veya Streamlit Secrets üzerinden tanımlayın.")


def render_dashboard() -> None:
    """Render usage metrics and complete-analysis workflow."""
    hero("AI Career Copilot", "CV'nizden kariyer yol haritanıza tek çalışma alanı.")
    user_id = ensure_user()
    with session_scope() as session:
        counts = {
            "CV": session.scalar(
                select(func.count())
                .select_from(UploadedCV)
                .where(UploadedCV.user_id == user_id)
            ),
            "Analiz": session.scalar(
                select(func.count())
                .select_from(AnalysisHistory)
                .where(AnalysisHistory.user_id == user_id)
            ),
            "Ön Yazı": session.scalar(
                select(func.count())
                .select_from(CoverLetter)
                .where(CoverLetter.user_id == user_id)
            ),
            "Kariyer Raporu": session.scalar(
                select(func.count())
                .select_from(CareerReport)
                .where(CareerReport.user_id == user_id)
            ),
        }
    columns = st.columns(4)
    for column, (label, value) in zip(columns, counts.items()):
        column.metric(label, value or 0)

    st.subheader("360° Kariyer Analizi")
    st.caption(
        "Parser, ATS, iyileştirme, mülakat ve kariyer ajanlarını sırasıyla çalıştırır."
    )
    cv = cv_selector("Analiz edilecek CV")
    if cv is None:
        return
    left, right = st.columns(2)
    target_role = left.text_input("Hedef rol (isteğe bağlı)")
    job_description = right.text_area("İş ilanı (isteğe bağlı)", height=100)
    if st.button("Tam Analizi Başlat", type="primary", use_container_width=True):
        try:
            with st.status("Uzman ajanlar çalışıyor...", expanded=True) as status:
                service = create_ai_service()
                coordinator = CareerCopilotCoordinator(service)
                result = coordinator.analyze(
                    cv.extracted_text, job_description, target_role or "Belirtilmemiş"
                )
                st.write("✓ CV ayrıştırıldı ve ATS puanı hesaplandı")
                st.write("✓ İyileştirme, mülakat ve kariyer raporları hazırlandı")
                with session_scope() as session:
                    crud.uploaded_cvs.update(
                        session, cv.id, parsed_data=model_dump(result.parsed_resume)
                    )
                    crud.analyses.create(
                        session,
                        user_id=user_id,
                        cv_id=cv.id,
                        provider=service.provider_name,
                        model_name=service.model_name,
                        ats_score=result.ats.score,
                        analysis_data=model_dump(result),
                    )
                    crud.career_reports.create(
                        session,
                        user_id=user_id,
                        cv_id=cv.id,
                        target_role=result.career.target_role,
                        report_data=model_dump(result.career),
                    )
                    for question in result.interview.questions:
                        crud.interview_questions.create(
                            session,
                            user_id=user_id,
                            cv_id=cv.id,
                            **model_dump(question),
                        )
                st.session_state.complete_analysis = model_dump(result)
                status.update(label="Analiz tamamlandı", state="complete")
            st.success(f"ATS puanı: {result.ats.score:.1f}/100")
        except Exception as exc:
            handle_ai_error(exc)

    if complete_data := st.session_state.get("complete_analysis"):
        result = CompleteAnalysis.model_validate(complete_data)
        col1, col2 = st.columns([1, 2])
        col1.metric("Son ATS Puanı", f"{result.ats.score:.1f}/100")
        col2.progress(result.ats.score / 100)
        if st.button("PDF Raporunu Hazırla"):
            try:
                output_path = settings.reports_dir / f"career_report_cv_{cv.id}.pdf"
                pdf_bytes = CareerReportGenerator().generate(result, output_path)
                st.session_state.pdf_report = pdf_bytes
            except Exception as exc:
                st.error(f"PDF oluşturulamadı: {exc}")
        if pdf_bytes := st.session_state.get("pdf_report"):
            st.download_button(
                "PDF Raporunu İndir",
                data=pdf_bytes,
                file_name=f"AI_Career_Copilot_{cv.id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


def render_upload() -> None:
    """Render secure CV upload and initial extraction."""
    hero("CV Yükle", "PDF veya DOCX özgeçmişinizi güvenli biçimde analiz edin.")
    st.caption(f"Desteklenen türler: PDF, DOCX · En fazla {settings.max_upload_mb} MB")
    uploaded = st.file_uploader("CV dosyanızı seçin", type=["pdf", "docx"])
    if uploaded is None:
        return
    st.write(f"**Dosya:** {uploaded.name} · **Boyut:** {uploaded.size / 1024:.1f} KB")
    if st.button("Yükle ve Ayrıştır", type="primary", use_container_width=True):
        try:
            parsed_document = DocumentParser().parse_and_save(
                uploaded.name, uploaded.getvalue()
            )
            user_id = ensure_user()
            with session_scope() as session:
                duplicate = crud.uploaded_cvs.get_by_hash(
                    session, user_id, parsed_document.file_hash
                )
            if duplicate:
                st.session_state.current_cv_id = duplicate.id
                st.warning("Bu CV daha önce yüklenmiş; mevcut kayıt seçildi.")
                return
            parsed_data: dict[str, Any] = {}
            ai_warning = ""
            try:
                resume = ResumeParserAgent(create_ai_service()).parse(
                    parsed_document.text
                )
                parsed_data = model_dump(resume)
            except Exception as exc:
                ai_warning = str(exc)
                logger.error("upload_ai_parse_failed error=%s", exc, exc_info=True)
            with session_scope() as session:
                cv = crud.uploaded_cvs.create(
                    session,
                    user_id=user_id,
                    original_filename=parsed_document.original_filename,
                    stored_filename=parsed_document.stored_filename,
                    file_type=parsed_document.extension,
                    file_hash=parsed_document.file_hash,
                    extracted_text=parsed_document.text,
                    parsed_data=parsed_data,
                )
                st.session_state.current_cv_id = cv.id
            st.success("CV güvenli biçimde kaydedildi ve metin çıkarıldı.")
            if ai_warning:
                st.warning(
                    f"Yapılandırılmış AI ayrıştırması daha sonra yapılacak: {ai_warning}"
                )
            else:
                st.json(parsed_data)
        except DocumentParseError as exc:
            st.error(str(exc))
        except Exception as exc:
            logger.error("upload_failed error=%s", exc, exc_info=True)
            st.error(f"CV yüklenemedi: {exc}")


def render_ats() -> None:
    """Render the ATS scoring agent page."""
    hero("ATS Analizi", "Şeffaf, 100 puanlık kriterlerle uyumluluğu ölçün.")
    cv = cv_selector()
    if cv is None:
        return
    job_description = st.text_area(
        "Hedef iş ilanı (önerilir)",
        height=180,
        placeholder="İlan metnini buraya yapıştırın...",
    )
    if st.button("ATS Puanını Hesapla", type="primary", use_container_width=True):
        try:
            with st.spinner("ATS ajanı CV'yi değerlendiriyor..."):
                resume = ensure_parsed_resume(cv)
                service = create_ai_service()
                result = ATSScoringAgent(service).score(resume, job_description)
                with session_scope() as session:
                    crud.analyses.create(
                        session,
                        user_id=ensure_user(),
                        cv_id=cv.id,
                        provider=service.provider_name,
                        model_name=service.model_name,
                        ats_score=result.score,
                        analysis_data={"ats": model_dump(result)},
                    )
                st.session_state.ats_result = model_dump(result)
        except Exception as exc:
            handle_ai_error(exc)
    if data := st.session_state.get("ats_result"):
        result = ATSResult.model_validate(data)
        st.metric("ATS Puanı", f"{result.score:.1f}/100")
        st.progress(result.score / 100)
        breakdown = pd.DataFrame(
            [
                ("Anahtar Kelimeler", result.breakdown.keywords, 20),
                ("Başlık Yapısı", result.breakdown.headings, 15),
                ("Okunabilirlik", result.breakdown.readability, 15),
                ("Deneyim", result.breakdown.experience, 20),
                ("Teknik Beceriler", result.breakdown.technical_skills, 15),
                ("Eğitim", result.breakdown.education, 10),
                ("Sertifikalar", result.breakdown.certificates, 5),
            ],
            columns=["Kriter", "Puan", "Maksimum"],
        )
        st.dataframe(breakdown, hide_index=True, use_container_width=True)
        show_items("Güçlü Yönler", result.strengths)
        show_items("Öneriler", result.recommendations)
        if result.missing_keywords:
            show_items(
                "İlanda Olup CV'de Görülmeyen Anahtar Kelimeler",
                result.missing_keywords,
            )


def render_improvement() -> None:
    """Render evidence-based resume improvement guidance."""
    hero("CV İyileştirme", "Güçlü yanları koruyun, en etkili eksikleri önce giderin.")
    cv = cv_selector()
    if cv is None:
        return
    if st.button(
        "İyileştirme Önerileri Oluştur", type="primary", use_container_width=True
    ):
        try:
            with st.spinner("CV iyileştirme ajanı çalışıyor..."):
                resume = ensure_parsed_resume(cv)
                service = create_ai_service()
                ats = ATSScoringAgent(service).score(resume)
                result = ResumeImprovementAgent(service).improve(resume, ats)
                with session_scope() as session:
                    crud.analyses.create(
                        session,
                        user_id=ensure_user(),
                        cv_id=cv.id,
                        provider=service.provider_name,
                        model_name=service.model_name,
                        ats_score=ats.score,
                        analysis_data={
                            "ats": model_dump(ats),
                            "improvement": model_dump(result),
                        },
                    )
                st.session_state.improvement_result = model_dump(result)
        except Exception as exc:
            handle_ai_error(exc)
    if data := st.session_state.get("improvement_result"):
        show_items("Güçlü Yönler", data["strengths"])
        show_items("Geliştirilmesi Gereken Alanlar", data["missing_areas"])
        show_items("Öncelikli Öneriler", data["prioritized_recommendations"])
        st.subheader("İyileştirilmiş Profesyonel Özet")
        st.info(data["improved_summary"])
        st.caption(data["length_feedback"])


def render_cover_letter() -> None:
    """Render cover-letter generation and persistence."""
    hero(
        "Ön Yazı Oluştur", "CV'nize sadık, role özel ve profesyonel bir başvuru metni."
    )
    cv = cv_selector()
    if cv is None:
        return
    col1, col2 = st.columns(2)
    position = col1.text_input("Hedef pozisyon *")
    company = col2.text_input("Şirket")
    tone = st.segmented_control(
        "Ton", ["Resmi", "Samimi", "Kurumsal"], default="Kurumsal"
    )
    job_description = st.text_area("İş ilanı (isteğe bağlı)", height=130)
    if st.button("Ön Yazıyı Oluştur", type="primary", use_container_width=True):
        if not position.strip():
            st.warning("Hedef pozisyon zorunludur.")
            return
        try:
            with st.spinner("Ön yazı ajanı çalışıyor..."):
                resume = ensure_parsed_resume(cv)
                result = CoverLetterAgent(create_ai_service()).create(
                    resume,
                    position,
                    company or "Belirtilmemiş",
                    tone or "Kurumsal",
                    job_description,
                )
                with session_scope() as session:
                    crud.cover_letters.create(
                        session,
                        user_id=ensure_user(),
                        cv_id=cv.id,
                        position=result.position,
                        company=result.company,
                        tone=result.tone,
                        content=result.content,
                    )
                st.session_state.cover_letter = result.content
        except Exception as exc:
            handle_ai_error(exc)
    if content := st.session_state.get("cover_letter"):
        st.text_area("Oluşturulan Ön Yazı", content, height=420)
        st.download_button(
            "Metin Olarak İndir",
            content.encode("utf-8"),
            file_name="on_yazi.txt",
            mime="text/plain",
        )


def render_interview() -> None:
    """Render resume-specific interview preparation."""
    hero(
        "Mülakat Hazırlığı", "Teknik, İK, davranışsal ve proje sorularıyla prova yapın."
    )
    cv = cv_selector()
    if cv is None:
        return
    target_role = st.text_input("Hedef rol")
    if st.button("Mülakat Seti Oluştur", type="primary", use_container_width=True):
        try:
            with st.spinner("Mülakat koçu soruları hazırlıyor..."):
                resume = ensure_parsed_resume(cv)
                result = InterviewCoachAgent(create_ai_service()).prepare(
                    resume, target_role or "Belirtilmemiş"
                )
                with session_scope() as session:
                    for item in result.questions:
                        crud.interview_questions.create(
                            session,
                            user_id=ensure_user(),
                            cv_id=cv.id,
                            **model_dump(item),
                        )
                st.session_state.interview_result = model_dump(result)
        except Exception as exc:
            handle_ai_error(exc)
    if data := st.session_state.get("interview_result"):
        tabs = st.tabs(["Teknik", "İnsan Kaynakları", "Davranışsal", "Proje"])
        for tab, category in zip(
            tabs, ["Teknik", "İnsan Kaynakları", "Davranışsal", "Proje"]
        ):
            with tab:
                questions = [q for q in data["questions"] if q["category"] == category]
                for index, item in enumerate(questions, 1):
                    with st.expander(f"{index}. {item['question']}"):
                        show_items("Cevap İpuçları", item["answer_tips"])
        show_items("Genel Tavsiyeler", data["general_tips"])


def render_career() -> None:
    """Render career guidance and roadmap persistence."""
    hero("Kariyer Danışmanı", "Mevcut profilinizden hedef rolünüze gerçekçi bir rota.")
    cv = cv_selector()
    if cv is None:
        return
    target_role = st.text_input("Hedef rol (isteğe bağlı)")
    if st.button(
        "Kariyer Yol Haritası Oluştur", type="primary", use_container_width=True
    ):
        try:
            with st.spinner("Kariyer danışmanı planı hazırlıyor..."):
                resume = ensure_parsed_resume(cv)
                result = CareerAdvisorAgent(create_ai_service()).advise(
                    resume, target_role or "Belirtilmemiş"
                )
                with session_scope() as session:
                    crud.career_reports.create(
                        session,
                        user_id=ensure_user(),
                        cv_id=cv.id,
                        target_role=result.target_role,
                        report_data=model_dump(result),
                    )
                st.session_state.career_result = model_dump(result)
        except Exception as exc:
            handle_ai_error(exc)
    if data := st.session_state.get("career_result"):
        st.info(data["current_profile"])
        col1, col2 = st.columns(2)
        with col1:
            show_items("Öğrenilecek Teknolojiler", data["technologies_to_learn"])
            show_items("Sertifika Önerileri", data["certificate_recommendations"])
            show_items("Portföy Tavsiyeleri", data["portfolio_recommendations"])
        with col2:
            show_items("Seviye Geçişi", data["level_transition_advice"])
            show_items("Kariyer Yol Haritası", data["roadmap"])
            st.subheader("Maaş Beklentisi Yaklaşımı")
            st.write(data["salary_guidance"])


def render_history() -> None:
    """Render persisted analysis, letter and report history."""
    hero("Geçmiş Analizler", "Önceki çalışmalarınızı tek yerde inceleyin ve yönetin.")
    user_id = ensure_user()
    with session_scope() as session:
        analyses = list(crud.analyses.list_by_user(session, user_id))
        letters = list(crud.cover_letters.list_by_user(session, user_id))
        reports = list(crud.career_reports.list_by_user(session, user_id))
    tab1, tab2, tab3 = st.tabs(["ATS / Analiz", "Ön Yazılar", "Kariyer Raporları"])
    with tab1:
        if analyses:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ID": item.id,
                            "CV ID": item.cv_id,
                            "ATS": item.ats_score,
                            "Sağlayıcı": item.provider,
                            "Model": item.model_name,
                            "Tarih": item.created_at,
                        }
                        for item in analyses
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Henüz analiz kaydı yok.")
    with tab2:
        for letter in letters:
            with st.expander(
                f"{letter.position} · {letter.company} · {letter.created_at:%d.%m.%Y}"
            ):
                st.write(letter.content)
    with tab3:
        for report in reports:
            with st.expander(f"{report.target_role} · {report.created_at:%d.%m.%Y}"):
                st.json(report.report_data)

    st.divider()
    st.subheader("Kayıt Sil")
    deletable_repositories = {
        "analysis_history": crud.analyses,
        "cover_letters": crud.cover_letters,
        "interview_questions": crud.interview_questions,
        "career_reports": crud.career_reports,
    }
    record_type = st.selectbox("Kayıt türü", list(deletable_repositories))
    record_id = st.number_input("Kayıt ID", min_value=1, step=1)
    confirm = st.checkbox("Silme işlemini onaylıyorum")
    if st.button("Kaydı Sil", disabled=not confirm):
        repository = deletable_repositories[record_type]
        with session_scope() as session:
            entity = repository.get(session, int(record_id))
            owned_by_user = entity is not None and entity.user_id == user_id
            deleted = (
                repository.delete(session, int(record_id)) if owned_by_user else False
            )
        st.success("Kayıt silindi.") if deleted else st.warning("Kayıt bulunamadı.")


def render_settings() -> None:
    """Render profile and provider settings."""
    hero("Ayarlar", "Profilinizi ve tercih edilen AI sağlayıcısını yönetin.")
    user_id = ensure_user()
    with st.form("profile_form"):
        name = st.text_input("Ad Soyad", st.session_state.get("user_name", "Kullanıcı"))
        email = st.text_input(
            "E-posta", st.session_state.get("user_email", "kullanici@example.com")
        )
        submitted = st.form_submit_button("Profili Kaydet", type="primary")
    if submitted:
        if "@" not in email:
            st.error("Geçerli bir e-posta girin.")
        else:
            with session_scope() as session:
                crud.users.update(
                    session, user_id, name=name.strip(), email=email.strip().lower()
                )
            st.session_state.user_name = name.strip()
            st.session_state.user_email = email.strip().lower()
            st.success("Profil güncellendi.")

    st.subheader("AI Sağlayıcısı")
    provider = st.radio(
        "Tercih",
        ["gemini", "groq"],
        index=0
        if st.session_state.get("ai_provider", settings.default_ai_provider) == "gemini"
        else 1,
        horizontal=True,
        format_func=lambda value: (
            "Google Gemini 2.5 Flash" if value == "gemini" else "Groq · Llama 3.3 70B"
        ),
    )
    st.session_state.ai_provider = provider
    key_status = {
        "Gemini": "Hazır" if settings.gemini_api_key else "Eksik",
        "Groq": "Hazır" if settings.groq_api_key else "Eksik",
    }
    st.table(pd.DataFrame([key_status]))
    st.caption("Anahtarlar arayüzde gösterilmez ve uygulama loglarına yazılmaz.")


def main() -> None:
    """Run the Streamlit application router."""
    inject_styles()
    ensure_user()
    with st.sidebar:
        st.markdown("## 🧭 AI Career Copilot")
        st.caption(f"v{settings.app_version}")
        page = st.radio("Navigasyon", PAGES, label_visibility="collapsed")
        st.divider()
        provider = st.selectbox(
            "AI Sağlayıcısı",
            ["gemini", "groq"],
            index=0
            if st.session_state.get("ai_provider", settings.default_ai_provider)
            == "gemini"
            else 1,
            format_func=lambda value: (
                "Gemini 2.5 Flash" if value == "gemini" else "Groq · Llama 3"
            ),
        )
        st.session_state.ai_provider = provider
        if not settings.has_provider_key(provider):
            st.warning(f"{provider.upper()} API anahtarı eksik")

    routes = {
        PAGES[0]: render_dashboard,
        PAGES[1]: render_upload,
        PAGES[2]: render_ats,
        PAGES[3]: render_improvement,
        PAGES[4]: render_cover_letter,
        PAGES[5]: render_interview,
        PAGES[6]: render_career,
        PAGES[7]: render_history,
        PAGES[8]: render_settings,
    }
    routes[page]()


if __name__ == "__main__":
    main()
