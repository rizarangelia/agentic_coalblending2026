# Improvement Notes — CoalBlend AI

Catatan hal-hal yang **sengaja dibiarkan apa adanya sekarang**, sebagai bahan evaluasi & perbaikan ke depan. Bukan bug yang memblokir; ini optimasi/perapihan.

---

## 1. Cold-start menjalankan `db.init()` + `seed_demo()` (prioritas: sedang) — BELUM diterapkan

**Kondisi sekarang**
`app.py` memanggil `db.init()` di level import (saat modul dimuat). Di serverless (Vercel), ini berarti **setiap cold-start** (instance baru) menjalankan:
- `_connect()` ke Aiven (SSL handshake) untuk DDL,
- `CREATE TABLE IF NOT EXISTS …` (no-op bila tabel sudah ada), `ALTER TABLE … ADD COLUMN IF NOT EXISTS …`,
- `seed_demo()` → `_connect()` kedua + **4× `SELECT COUNT`** lalu skip insert karena tabel sudah berisi.

**Masalah**
Mubazir ketika skema & data **sudah ada**: menambah 1–2 koneksi Aiven + beberapa query **sebelum** request pertama diproses → request pertama tiap instance dingin terasa lebih lambat. Ini **bukan** terkait login; murni siklus hidup instance.

**Usulan (manual init)**
- Hapus pemanggilan `db.init()` otomatis di import (`app.py`).
- Tambah endpoint terlindungi sekali-jalan, mis. `GET /api/dbinit` (perlu login) yang menjalankan `db.init()` + `seed_demo()` on-demand.
- Admin menjalankannya **sekali** setelah DB dibuat; cold-start berikutnya tidak lagi menyentuh DB untuk init/seed.

**Catatan keamanan**
- Aman diterapkan karena DB produksi saat ini sudah lengkap (skema + data).
- Bila suatu saat DB dibuat ulang dari nol: cukup buka `/api/dbinit` sekali. Error tulis saat skema belum ada sudah ditangani `_safe` (tidak membuat app crash); pembacaan state jatuh ke fixtures.

---

## 2. Tidak ada connection pooling (prioritas: sedang)

Tiap `db._connect()` membuka koneksi psycopg2 **baru** ke Aiven (TLS handshake, `connect_timeout=8`). Tanpa pool, setiap operasi DB membayar handshake ~100–500 ms, diperparah cold-start serverless.

**Usulan:** pakai **endpoint connection-pool Aiven (PgBouncer)** pada `DATABASE_URL` (perubahan konfigurasi, bukan kode), atau pooler sisi aplikasi bila pindah ke host stateful (Railway).

---

## 3. `coalblend_constraint_params` tanpa UNIQUE key (prioritas: rendah)

Saat ini idempotensi dicapai dengan **DELETE (per user) + bulk INSERT** dalam satu transaksi (aman & konsisten, sudah diterapkan). Alternatif yang lebih "relasional": tambah `UNIQUE (username, category, entity, param)` lalu pakai **UPSERT** (`INSERT … ON CONFLICT DO UPDATE`).

**Konsekuensi:** butuh migrasi — dedup baris historis yang sudah ada dulu sebelum menambah unique constraint. Outcome kecepatan ~sama dengan DELETE+INSERT, jadi ini soal kerapihan model data saja.

---

## 4. `coalblend_constraints` (jsonb) append-only (prioritas: rendah)

Tabel ini sengaja append (audit trail: riwayat tiap perubahan constraint, 1 baris/simpan). Ringan, tapi tumbuh seiring waktu.

**Usulan:** batasi retensi (mis. simpan N terbaru per user, atau arsipkan berkala) bila audit log membesar.

---

## 5. Live Operations fallback belum cycle-aware (prioritas: rendah)

Saat solve dengan Constraint Settings infeasible, `/api/monitoring` fallback ke **solve baseline dari data terakhir**. Idealnya (sesuai konsep Cycle) fallback menarik **hasil cycle feasible terakhir** dari histori DB, bukan baseline data saat ini.

**Usulan:** persist snapshot solusi feasible terakhir per cycle, lalu tampilkan itu saat cycle berjalan belum feasible.

---

## 6. Price Intel (shadow price) kosong saat solver HiGHS (prioritas: rendah)

Setelah pindah solver CBC → HiGHS (PuLP 2.9), dual values (`.pi`) tidak selalu terisi, sehingga panel Price Intel bisa menampilkan "—".

**Usulan:** ekstrak dual values langsung dari `highspy` (API HiGHS), atau pakai solver yang mengembalikan dual untuk run khusus Price Intel.

---

_Dibuat sebagai bahan evaluasi — tidak ada perubahan perilaku dari file ini._
