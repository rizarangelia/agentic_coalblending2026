# Deploy CoalBlend AI — Online

Arsitektur = **3 komponen terpisah** yang semuanya menunjuk ke Postgres `defaultdb` yang sama.
Metabase **bukan** web host — ia hanya menampilkan dashboard-nya sendiri.

```
              ┌─────────────────────────────┐
  Web Flask ──┤  PostgreSQL  defaultdb (cloud) ├── Metabase Cloud (dashboard)
  (Railway)   └─────────────────────────────┘        └── Claude (baca data)
```

| Komponen | Online via | Sumber |
|---|---|---|
| Postgres `defaultdb` | Cloud managed (Aiven/DO/Supabase) — sudah publik | — |
| Web Flask CoalBlend | **Railway** (auto-deploy dari GitHub) | repo ini |
| Dashboard | **Metabase Cloud** (connect ke defaultdb) | tabel `coalblend_*` |

---

## 1. Push ke GitHub

```bash
git add .
git commit -m "Deploy config: Railway + Postgres persistence + monitoring realtime"
git push origin main
```

> `.env` **tidak** ikur ter-push (di-gitignore) — rahasia diisi via dashboard Railway, bukan di repo.

## 2. Deploy Web Flask ke Railway

1. Buka https://railway.app → **New Project → Deploy from GitHub repo** → pilih repo ini.
2. Railway auto-detect Python (via `requirements.txt` + `runtime.txt`) dan menjalankan `Procfile`:
   `gunicorn app:app --bind 0.0.0.0:$PORT`
3. Tab **Variables** → tambahkan environment variables:

   | Variable | Nilai | Wajib |
   |---|---|---|
   | `DATABASE_URL` | `postgresql://USER:PASS@HOST:5432/defaultdb?sslmode=require` | ✅ |
   | `SECRET_KEY` | string acak panjang (untuk session Flask) | ✅ |
   | `DATADOCKED_API_KEY` | key AIS (opsional, untuk vessel asli) | ⬜ |

4. Railway memberi domain publik, mis. `https://coalblend-production.up.railway.app`.
   `PORT` di-inject otomatis oleh Railway — tidak perlu di-set manual.
5. Buka domain → login (`planner` / `coalblend2026`). Setiap upload & run blending langsung
   tertulis ke `defaultdb`.

> **Catatan filesystem:** Railway ephemeral — file di `output/*.json` bisa ter-reset saat
> redeploy. Itu tidak masalah karena **sumber kebenaran sudah Postgres**; JSON hanya cache/fallback.

## 3. Onlinekan Dashboard via Metabase Cloud

1. Daftar di https://www.metabase.com/cloud → buat instance.
2. **Admin → Databases → Add database → PostgreSQL**, isi dengan koneksi `defaultdb` Anda:
   - Host / Port / Database name (`defaultdb`) / User / Password
   - Aktifkan **Use a secure connection (SSL)** → `require`
3. **Sync database schema** → tabel muncul:
   `coalblend_uploads`, `coalblend_input_data`, `coalblend_runs`, `coalblend_run_scenarios`,
   `coalblend_decisions`, `coalblend_blending_history`, `business_process`, `blending_allocation`.
4. Buat Questions/Dashboard di atas tabel itu (contoh di bawah). Karena web Flask menulis ke DB
   yang sama, dashboard **update otomatis** tiap ada aktivitas di web.
5. Bagikan: **Sharing → Public link** atau **Embed** untuk menampilkan tanpa login.

### Contoh Question Metabase (SQL)
```sql
-- Tren revenue per ronde (opsi terbaik)
SELECT round_no, max(revenue) AS best_revenue
FROM coalblend_run_scenarios GROUP BY round_no ORDER BY round_no;

-- Approve vs Reject
SELECT aksi, count(*) FROM coalblend_decisions GROUP BY aksi;

-- Alokasi blending terbaru yang disetujui
SELECT site, brand, shipment_mt FROM coalblend_blending_history
WHERE round_no = (SELECT max(round_no) FROM coalblend_blending_history)
ORDER BY shipment_mt DESC;
```

## 4. (Opsional) Scheduler — sesuai diagram

Kotak **GitHub Actions** di diagram = penjadwal, **bukan** host UI. Untuk cron harian yang
menulis ke Postgres (mis. `predict.py`), buat `.github/workflows/predict.yml` dengan
`schedule: cron` + `DATABASE_URL` sebagai GitHub Secret. (Belum termasuk di MVP ini.)

---

## Yang TIDAK bisa
- Menaruh web Flask "di dalam" Metabase — Metabase bukan web hosting.
- Menjalankan backend Flask di GitHub Pages — hanya file statis.

## Lokal vs Produksi
- **Lokal (Windows):** `python app.py` → http://localhost:8080 (gunicorn tidak dipakai/tidak jalan di Windows).
- **Produksi (Railway/Linux):** `gunicorn app:app` via `Procfile`.
