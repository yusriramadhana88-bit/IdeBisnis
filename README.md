# IdeBisnis — Halal Personal Finance & Hajj Savings App

Aplikasi pengelolaan keuangan personal untuk muslim yang membantu perjalanan
menuju Haji/Umrah melalui penghematan cerdas dan perencanaan terstruktur.

> "Bantu kamu berangkat umrah/haji dari penghematan sehari-hari"

## Fitur (roadmap 6 fase)

| Fase | Fitur | Status |
|------|-------|--------|
| 1 | Expense tracker via foto struk (OCR otomatis) | 🚧 In Progress |
| 2 | Spending audit — pilih item yang mau dihemat | 📋 Planned |
| 3 | Kalkulator Zakat multi-aset | 📋 Planned |
| 4 | Hajj/Umrah Goal Planner + breakdown biaya detail | 📋 Planned |
| 5 | Savings allocation engine | 📋 Planned |
| 6 | A/B comparison provider investasi syariah | 📋 Planned |

## Arsitektur

- **Delivery awal**: Telegram bot (zero friction, tidak perlu install apapun)
- **OCR**: Claude Vision API (claude-haiku-4-5, cost-efficient)
- **Storage**: SQLite lokal (migrate ke cloud di fase lanjut)
- **Backend**: Python 3.10+
- **Hosting**: Lokal dulu (Windows Task Scheduler / VPS di fase lanjut)

## Prinsip bisnis

- Jual **tools & proses**, bukan sinyal / prediksi profit
- User selalu pegang kendali dana mereka sendiri (no custody)
- Semua fitur = alat bantu keputusan, dilengkapi disclaimer
- Revenue dari ujrah (subscription / one-time purchase)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Isi TELEGRAM_BOT_TOKEN dan ANTHROPIC_API_KEY di .env
python fase1/bot.py
```

## Struktur folder

```
IdeBisnis/
├── fase1/          # Expense tracker via foto struk
├── fase2/          # Spending audit dashboard
├── fase3/          # Kalkulator Zakat
├── fase4/          # Hajj/Umrah Goal Planner
├── fase5/          # Savings allocation engine
├── fase6/          # A/B investment comparison
├── shared/         # Utilities, database, models
└── docs/           # Dokumentasi & riset biaya Haji/Umrah
```
