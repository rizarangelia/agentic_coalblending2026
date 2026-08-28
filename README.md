# CoalBlend AI — MVP 1 (Multi-Agent System)
Optimasi coal blending PT Berau Coal: 4 agent (Ingestion → Constraint → Optimizer → Synthesizer),
login + input data + alert engine + dashboard review.

## Instalasi & Menjalankan
    # 1. (sekali) buat virtual environment & instal dependensi
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

    # 2. (opsional tapi disarankan) hubungkan ke Postgres `defaultdb` (sumber Metabase)
    cp .env.example .env             # lalu isi DATABASE_URL dengan koneksi Postgres Anda
                                     # tabel dibuat otomatis saat app start (agents/db.py)

    # 3. jalankan aplikasi
    python app.py                    # buka http://localhost:8080

Login demo: planner / coalblend2026 · reviewer / review2026.

## Persistensi Database & Metabase (arsitektur)
Setiap **upload** dan setiap **run AI blending** di web otomatis ditulis ke Postgres `defaultdb`
— DB yang sama yang dibaca Metabase, sehingga dashboard update otomatis (jalankan
"Sync database schema" di Metabase satu kali agar tabel baru muncul).
- Koneksi via `DATABASE_URL` di `.env` (Postgres cloud → `sslmode=require` ditambah otomatis).
  Kosongkan untuk menonaktifkan DB → app tetap jalan pakai file JSON di `output/` (fail-safe).
- Skema dibuat otomatis oleh `db.init()` saat startup; manual: `psql "$DATABASE_URL" -f schema.sql`.
- Tabel history baru (append-only, audit): `coalblend_uploads`, `coalblend_input_data`,
  `coalblend_runs`, `coalblend_run_scenarios`, `coalblend_decisions`, `coalblend_blending_history`.
- Tabel Metabase lama di-refresh tiap run/approve: `business_process` (input), `blending_allocation`
  (alokasi opsi disetujui) — dashboard existing langsung mencerminkan hasil terbaru.
- Diagnostik koneksi non-fatal dicatat di `output/db.log`.
Halaman:
- /dashboard  → dashboard analitik (Coal Balance · Available Product · Blending Plan dgn slider
  deal live re-optimize · Matriks · Revenue) — gaya deployment Railway, kini di belakang login
- /input      → unggah 4 file (kosongkan = fixtures)
- /review     → validasi multi-opsi (HITL) — keputusan resmi hanya lewat sini
- /api/state, /api/optimize → JSON untuk dashboard (butuh sesi login)

Alur: Login → Dashboard/Input Data (unggah 4 file CSV/XLSX, atau kosongkan semua untuk fixtures simulasi)
→ halaman Review multi-opsi → Setujui/Tolak (+catatan) → kalibrasi & audit trail tercatat.

Output per run: output/dashboard.html · output/last_run.json · output/trace.jsonl (lineage) ·
output/decisions.jsonl (keputusan validator) · config/calibration.json (preferensi).

Uji kesehatan kapan pun: `python tests/test_pipeline.py` (wajib 4/4 PASS,
baseline 24.225.858,52).

## Validasi
    python tests/test_pipeline.py
4 test: baseline revenue 24.225.858,52 · reject data negatif · pre-solve deteksi infeasible · solver diagnoser.

## Struktur
- agents/        implementasi deterministik 4 agent
- prompts/       system prompt persona per agent (untuk augmentasi LLM; angka selalu dari solver)
- kb/            RAG knowledge base 14 chunk (narasi bisnis; angka=simulasi)
- config/        constraint_manifest.json (source of truth aturan) + users.json
- fixtures/      data simulasi + expected solution (acceptance test)
- output/        dashboard.html hasil run terakhir

## Prinsip arsitektur (hasil validasi)
1. Konstrain numerik = structured config, BUKAN vector retrieval. RAG hanya untuk konteks/penjelasan.
2. Model 4 TOTAL-ONLY; per-jetty = warning check. Model 6 tanpa toleransi −50.
3. LLM tidak pernah menghasilkan angka; solver CBC yang berhitung.
4. Infeasible → diagnosis relaksasi minimum (advisor, bukan kalkulator).
