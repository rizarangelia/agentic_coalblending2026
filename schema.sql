-- CoalBlend AI — skema persistensi untuk Postgres `defaultdb`
-- Dijalankan OTOMATIS oleh app.py (agents/db.py -> db.init()) saat startup.
-- Bisa juga dijalankan manual: psql "$DATABASE_URL" -f schema.sql
--
-- Metabase membaca DB yang sama, jadi dashboard update otomatis setiap ada
-- upload / run blending / keputusan di web. (Setelah pertama kali, jalankan
-- "Sync database schema" di Metabase agar tabel baru muncul.)

-- ============================================================================
-- 1) Tabel HISTORY baru (append-only) — audit lengkap, aman untuk tabel lama
-- ============================================================================

-- metadata tiap file yang diupload (sha256 + ukuran = data lineage)
CREATE TABLE IF NOT EXISTS coalblend_uploads (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    uploaded_at timestamptz NOT NULL DEFAULT now(),
    username text,
    sumber text,
    file_key text NOT NULL,
    filename text,
    sha256 text,
    bytes integer
);

-- isi baris data input (per entity: site/brand/jetty)
CREATE TABLE IF NOT EXISTS coalblend_input_data (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    uploaded_at timestamptz NOT NULL DEFAULT now(),
    username text,
    file_key text NOT NULL,
    entity text NOT NULL,
    volume_mt numeric,
    cv_gar numeric
);

-- satu baris per RONDE blending (run AI)
CREATE TABLE IF NOT EXISTS coalblend_runs (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    round_no integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    username text,
    sumber text,
    node_terakhir text,
    n_alerts integer
);

-- ringkasan 3 opsi (A/B/C) + revenue tiap ronde
CREATE TABLE IF NOT EXISTS coalblend_run_scenarios (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    round_no integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    scenario_id text,
    nama text,
    revenue numeric,
    total_ship numeric,
    feasible boolean
);

-- keputusan validator (Human-in-the-Loop): approve / reject
CREATE TABLE IF NOT EXISTS coalblend_decisions (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    round_no integer,
    decided_at timestamptz NOT NULL DEFAULT now(),
    validator text,
    scenario_id text,
    aksi text,
    catatan text,
    revenue numeric
);

-- matriks alokasi site x brand dari opsi yang DISETUJUI (history hasil)
CREATE TABLE IF NOT EXISTS coalblend_blending_history (
    id serial PRIMARY KEY,
    run_id text NOT NULL,
    round_no integer,
    scenario_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    validator text,
    site text,
    brand text,
    shipment_mt numeric,
    cv_site numeric
);

-- ============================================================================
-- 2) Tabel Metabase LAMA yang di-refresh tiap run/approve (agar dashboard
--    existing ikut update). Schema mengikuti metabase/output/load_coalblend.sql.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.business_process (
    id serial PRIMARY KEY,
    category text NOT NULL,
    group_type text,
    item_name text NOT NULL,
    volume_mt numeric,
    kualitas_gar numeric
);

CREATE TABLE IF NOT EXISTS public.blending_allocation (
    id serial PRIMARY KEY,
    source text NOT NULL,
    product text NOT NULL,
    shipment_mt numeric NOT NULL,
    blending_allowance_mt numeric,
    kualitas numeric
);
