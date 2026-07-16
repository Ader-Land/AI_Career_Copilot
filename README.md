# AI Career Copilot

AI Career Copilot; PDF/DOCX CV'leri yapılandıran, ATS uyumluluğunu ölçen,
iyileştirme önerileri, ön yazı, mülakat hazırlığı ve kariyer yol haritası üreten
Streamlit tabanlı profesyonel kariyer asistanıdır.

Uygulama, CV'de bulunmayan deneyim veya başarıları aday adına üretmemek üzere
tasarlanmıştır. Eksik tekil alanlar `Belirtilmemiş`, eksik koleksiyonlar boş liste
olarak işlenir. AI çıktıları kullanılmadan önce Pydantic şemalarıyla doğrulanır.

## Özellikler

- PyMuPDF, pdfplumber yedeği ve python-docx ile güvenli PDF/DOCX ayrıştırma
- Ad, eğitim, deneyim, yetenek, sertifika, dil ve projeler için JSON çıktı
- Açıklanabilir, ağırlıklı 0-100 ATS skoru ve iş ilanı anahtar kelime karşılaştırması
- Önceliklendirilmiş CV geliştirme önerileri ve kanıta dayalı profesyonel özet
- Resmi, samimi veya kurumsal tonda role özel ön yazı
- Teknik, İK, davranışsal ve proje bazlı mülakat soruları ile cevap ipuçları
- Teknoloji, sertifika, portföy, seviye geçişi ve kariyer yol haritası
- Yedi bölümlü, Türkçe karakter destekli profesyonel PDF rapor
- SQLite/SQLAlchemy üzerinde analiz, mektup, soru ve rapor geçmişi
- Dönen uygulama logları, ayrı hata logu ve API anahtarlarını gizli tutan yapı
- Google Gemini 3.5 Flash ve Groq Llama 3.3 arasında arayüzden seçim

## Multi-Agent Mimari

```text
CV Dosyası
   │
   ├─ DocumentParser ── ham metin
   │
   └─ Resume Parser Agent ── doğrulanmış JSON
          ├─ ATS Scoring Agent
          │     └─ Resume Improvement Agent
          ├─ Cover Letter Agent
          ├─ Interview Coach Agent
          └─ Career Advisor Agent
                    └─ PDF Report Generator
```

Her ajan tek bir sorumluluğa ve tipli çıktı sözleşmesine sahiptir. `AIService`,
Gemini ve Groq istemcilerini tek arayüz arkasında toplar. Provider hataları yeniden
denenir; şema dışı sonuçlar veritabanına yazılmaz.

## Kullanılan Teknolojiler

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.11+ |
| Frontend | Streamlit |
| AI | Google Gemini 3.5 Flash, Groq Llama 3.3 70B |
| Veri | SQLite, SQLAlchemy 2 |
| Dosya | PyMuPDF, pdfplumber, python-docx |
| Rapor | ReportLab |
| Veri sözleşmesi | Pydantic 2 |
| Yardımcılar | Pandas, python-dotenv, Pillow, logging |

## Kurulum

```bash
git clone https://github.com/Ader-Land/AI_Career_Copilot.git
cd AI_Career_Copilot
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## API Key Ayarları

En az bir sağlayıcı anahtarı gerekir. `.env.example` dosyasını `.env` olarak
kopyalayın ve gerçek anahtarınızı girin:

```env
GEMINI_API_KEY=...
GROQ_API_KEY=...
DEFAULT_AI_PROVIDER=gemini
```

- Gemini anahtarı: [Google AI Studio](https://aistudio.google.com/app/apikey)
- Groq anahtarı: [Groq Console](https://console.groq.com/keys)

`.env` Git tarafından izlenmez. Anahtarları koda, commit mesajına veya ekran
görüntüsüne eklemeyin.

## Çalıştırma

```bash
streamlit run app.py
```

Uygulama ilk açılışta SQLite veritabanını ve gerekli çalışma dizinlerini oluşturur.
Önce **Ayarlar** sayfasında profilinizi güncelleyin, sonra **CV Yükle** sayfasından
belgenizi ekleyin. Tekil ajan sayfalarını veya Dashboard'daki 360° analizi
kullanabilirsiniz.

Testler herhangi bir API çağrısı yapmaz:

```bash
python -m unittest discover -s tests -v
```

## Streamlit Community Cloud Deploy

1. Projeyi GitHub hesabınıza pushlayın. Repo özel ise Streamlit'e GitHub erişimi verin.
2. [share.streamlit.io](https://share.streamlit.io/) üzerinde **Create app** seçin.
3. Repository olarak `Ader-Land/AI_Career_Copilot`, branch olarak `main`, main file
   path olarak `app.py` girin.
4. **Advanced settings → Secrets** alanına aşağıdakilerden en az birini ekleyin:

   ```toml
   GEMINI_API_KEY = "gercek_anahtar"
   GROQ_API_KEY = "gercek_anahtar"
   DEFAULT_AI_PROVIDER = "gemini"
   GEMINI_MODEL = "gemini-3.5-flash"
   GROQ_MODEL = "llama-3.3-70b-versatile"
   ```

5. Python sürümü olarak desteklenen güncel 3.11 veya 3.12 sürümünü seçin ve deploy edin.
6. Deploy logunda `requirements.txt` kurulumunu ve uygulama health-check sonucunu kontrol edin.

Önemli: Streamlit Community Cloud'un yerel dosya sistemi kalıcı veri deposu garantisi
vermez. SQLite uygulamayı çalıştırır ancak yeniden başlatma/yeniden deploy sırasında
veri kaybı yaşanabilir. Uzun süreli SaaS üretim kullanımı için ileride yönetilen
PostgreSQL ve özel nesne depolama servisine geçilmelidir. Bu geçiş SQLAlchemy
repository katmanı sayesinde arayüz kodunu değiştirmeden yapılabilir.

## Proje Yapısı

```text
AI_Career_Copilot/
├── app.py                 # Streamlit sayfaları ve kullanıcı akışları
├── config.py              # Ortam, secret ve platform bağımsız yollar
├── database.py            # Engine, session ve tablo başlangıcı
├── models.py              # Altı SQLAlchemy veri modeli
├── schemas.py             # Pydantic AI/veri çıktı sözleşmeleri
├── crud.py                # Tüm modeller için CRUD repository'leri
├── ai_service.py          # Gemini/Groq adaptörleri, retry ve doğrulama
├── agents.py              # Altı uzman ajan ve koordinatör
├── parser.py              # PDF/DOCX doğrulama, çıkarma ve kayıt
├── report.py              # Yedi bölümlü PDF rapor üretimi
├── utils.py               # Logging, JSON, hash ve güvenlik yardımcıları
├── requirements.txt       # Üretim bağımlılıkları
├── .env.example           # Güvenli yapılandırma şablonu
├── .streamlit/config.toml # Cloud uyumlu arayüz/sunucu ayarları
├── tests/                 # CRUD, parser, ajan ve PDF smoke testleri
├── uploads/               # Git dışında tutulan CV dosyaları
├── reports/               # Üretilen PDF'ler
├── logs/                  # app.log ve errors.log
└── assets/                # Görsel/statik varlık alanı
```

## Güvenlik ve Gizlilik

- Uzantı, MIME imzası, boyut ve parola koruması kontrol edilir.
- Dosya adlarında dizin geçişi engellenir ve içerik SHA-256 ile tanımlanır.
- CV içeriği veya API anahtarı loglanmaz; loglarda işlem adı, süre ve içerik hash'i bulunur.
- Yükleme, rapor, log ve veritabanı dosyaları Git'e gönderilmez.
- CV metni güvenilmeyen veri olarak etiketlenir; içindeki prompt talimatları uygulanmaz.
- Gerçek çok kullanıcılı üretimde kimlik doğrulama, açık rıza, saklama süresi ve silme
  politikaları ayrıca uygulanmalıdır.

## Gelecek Geliştirmeler

- OAuth/SSO, rol tabanlı yetki ve kullanıcı başına veri izolasyonu
- PostgreSQL, Alembic migration ve S3 uyumlu şifreli nesne depolama
- OCR ile taranmış CV desteği
- İş ilanı toplama, başvuru takip panosu ve sürüm karşılaştırma
- Arka plan görev kuyruğu, streaming yanıtlar ve maliyet/token gözlemlenebilirliği
- Çok dilli CV ve ülkeye özel maaş veri sağlayıcısı entegrasyonları
- Otomatik değerlendirme seti, prompt sürümleme ve insan geri bildirim döngüsü

## Lisans

Bu proje eğitim ve ürün geliştirme amaçlı bir başlangıç uygulamasıdır. Dağıtımdan önce
kurumunuzun gizlilik, veri koruma ve AI kullanım politikalarını uygulayın.
