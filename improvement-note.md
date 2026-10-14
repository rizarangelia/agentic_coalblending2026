# Improvement Notes — CoalBlend AI

Catatan hal-hal yang **sengaja dibiarkan apa adanya sekarang**, sebagai bahan evaluasi & perbaikan ke depan. Bukan bug yang memblokir; ini optimasi/perapihan.

---

## 1. Cold-start `db.init()` + `seed_demo()` (prioritas: sedang) — ✅ SUDAH diterapkan (guarded ensure_ready)

**Dulu**
`app.py` memanggil `db.init()` penuh di import → tiap cold-start membuka 1–2 koneksi Aiven + `CREATE TABLE IF NOT EXISTS …` + `ALTER …` + `seed_demo()` (4× `SELECT COUNT`), padahal skema & data sudah ada. Mubazir.

**Sekarang**
`app.py` memanggil `db.ensure_ready()` (bukan `db.init()`):
- **struktur sudah ada** → hanya **1 query cek ringan** (`information_schema`), lalu langsung pakai DB (skip DDL + seed).
- **struktur belum ada** (deploy awal / DB baru) → `init()` penuh jalan **sekali**.
- guard `_READY` per-instance mencegah cek berulang; jalur simpan constraint tidak pernah memanggil init.

**Caveat yang perlu diingat**
- **Migrasi skema baru (ALTER/CREATE kolom-tabel baru) tidak lagi auto-jalan** di cold-start untuk DB yang strukturnya sudah ada. Setelah menambah kolom/tabel baru di kode, jalankan `init()` **manual sekali** (mis. lewat endpoint one-off `GET /api/dbinit` bila nanti dibuat, atau script) agar migrasi ter-apply.
- Untuk benar-benar 0 DB-call di cold-start, init bisa dijadikan langkah build/deploy — belum dilakukan (manfaat kecil vs kompleksitas).

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
