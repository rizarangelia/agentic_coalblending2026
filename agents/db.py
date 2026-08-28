"""Lapisan persistensi Postgres — menulis upload, ronde blending, keputusan, dan
alokasi hasil ke database `defaultdb` yang SAMA dengan sumber data Metabase.

Desain aman-gagal (fail-safe): bila DATABASE_URL belum di-set atau koneksi gagal,
SEMUA fungsi menjadi no-op sehingga web app tetap jalan (fallback file JSON di app.py
tidak terganggu). Metabase update otomatis karena membaca tabel yang sama.

Arsitektur (sesuai diagram): Web (predict/blending) --write--> PostgreSQL(defaultdb)
                                                     --read--> Metabase & Claude
"""
import os, json, pathlib, datetime

ROOT = pathlib.Path(__file__).parent.parent

# --- load .env (python-dotenv sudah jadi dependency) -------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except Exception:
    pass

_WARNED = False


def _log(msg):
    """Catat diagnostik non-fatal ke output/db.log tanpa memutus web flow."""
    try:
        (ROOT / 'output').mkdir(exist_ok=True)
        with open(ROOT / 'output/db.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}  {msg}\n")
    except Exception:
        pass


def _dsn():
    """Ambil connection string dari env. Untuk Postgres cloud (Aiven/DO/Supabase)
    paksa sslmode=require bila belum ada dan host bukan localhost."""
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        return None
    low = url.lower()
    if 'sslmode=' not in low and 'localhost' not in low and '127.0.0.1' not in low:
        url += ('&' if '?' in url else '?') + 'sslmode=require'
    return url


def enabled():
    return _dsn() is not None


def _connect():
    """Buka koneksi baru. Melempar exception bila gagal — pemanggil menangkapnya."""
    import psycopg2  # import lokal agar app tetap load walau lib belum terpasang
    return psycopg2.connect(_dsn(), connect_timeout=8)


# --- DDL: tabel history baru (append-only, aman untuk tabel Metabase lama) ----
SCHEMA = """
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
"""

# tabel Metabase lama yang di-refresh tiap run/approve (schema mengikuti
# metabase/output/load_coalblend.sql).
_EXISTING_DDL = """
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
"""


def init():
    """Buat tabel bila belum ada. Best-effort, dipanggil sekali saat startup."""
    if not enabled():
        _log("DATABASE_URL belum di-set — persistensi Postgres NONAKTIF (pakai file JSON).")
        return False
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute(_EXISTING_DDL)
            conn.commit()
        _log("Skema Postgres siap (tabel history + existing).")
        return True
    except Exception as e:
        _log(f"init() gagal: {e!r}")
        return False


def _safe(fn):
    """Jalankan operasi tulis; tangkap semua error agar web flow tak pernah putus."""
    global _WARNED
    if not enabled():
        return False
    try:
        with _connect() as conn:
            fn(conn)
            conn.commit()
        return True
    except Exception as e:
        _log(f"{getattr(fn, '__name__', 'op')} gagal: {e!r}")
        if not _WARNED:
            _WARNED = True
            _log("Peringatan pertama tercatat — cek DATABASE_URL / jaringan / SSL.")
        return False


# --- API tulis (dipanggil dari app.py) ---------------------------------------
def record_upload(run_id, username, sumber, lineage, data):
    """Simpan metadata tiap file (sha256/ukuran) + isi baris data input ke DB."""
    files = (lineage or {}).get('files', {})

    def op(conn):
        with conn.cursor() as cur:
            for key, meta in files.items():
                cur.execute(
                    "INSERT INTO coalblend_uploads (run_id, username, sumber, file_key, filename, sha256, bytes)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (run_id, username, sumber, key, meta.get('nama'), meta.get('sha256'), meta.get('bytes')))
            for key in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas'):
                for entity, rec in (data or {}).get(key, {}).items():
                    if not isinstance(rec, dict):
                        continue
                    vol = rec.get('volume_mt', rec.get('volume_deal_mt', rec.get('kapasitas_mt')))
                    cur.execute(
                        "INSERT INTO coalblend_input_data (run_id, username, file_key, entity, volume_mt, cv_gar)"
                        " VALUES (%s,%s,%s,%s,%s,%s)",
                        (run_id, username, key, entity, vol, rec.get('cv_gar')))
    return _safe(op)


def record_run(run_id, round_no, username, sumber, node_terakhir, scenarios, n_alerts):
    """Simpan satu ronde blending + ringkasan tiap opsi (A/B/C + revenue)."""
    def op(conn):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO coalblend_runs (run_id, round_no, username, sumber, node_terakhir, n_alerts)"
                " VALUES (%s,%s,%s,%s,%s,%s)",
                (run_id, round_no, username, sumber, node_terakhir, n_alerts))
            for sc in (scenarios or []):
                sol = sc.get('sol')
                cur.execute(
                    "INSERT INTO coalblend_run_scenarios"
                    " (run_id, round_no, scenario_id, nama, revenue, total_ship, feasible)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (run_id, round_no, sc.get('id'), sc.get('nama'), sc.get('revenue'),
                     (sol or {}).get('total_ship'), sol is not None))
    return _safe(op)


def record_decision(run_id, round_no, validator, scenario_id, aksi, catatan, revenue):
    """Simpan keputusan validator (approve/reject) — Human-in-the-Loop."""
    def op(conn):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO coalblend_decisions"
                " (run_id, round_no, validator, scenario_id, aksi, catatan, revenue)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (run_id, round_no, validator, scenario_id, aksi, catatan, revenue))
    return _safe(op)


def record_blending_history(run_id, round_no, scenario_id, validator, sol, C):
    """Simpan matriks alokasi site x brand dari opsi yang DISETUJUI (history)."""
    if not sol:
        return False

    def op(conn):
        with conn.cursor() as cur:
            for s in C['sites']:
                for b in C['brands']:
                    ship = (sol.get('x', {}).get(s, {}) or {}).get(b, 0) or 0
                    if ship <= 0:
                        continue
                    cur.execute(
                        "INSERT INTO coalblend_blending_history"
                        " (run_id, round_no, scenario_id, validator, site, brand, shipment_mt, cv_site)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (run_id, round_no, scenario_id, validator, s, b, ship, C['cv_site'].get(s)))
    return _safe(op)


# --- refresh tabel Metabase lama (agar dashboard existing ikut update) --------
def refresh_business_process(data, C):
    """Replace isi public.business_process dari input run terbaru (snapshot bulanan).
    Metabase membaca tabel ini untuk dashboard 'business process' yang sudah ada."""
    if not data:
        return False

    def op(conn):
        rows = []
        for s in C['sites']:
            os_ = (data.get('opening_stock', {}).get(s) or {})
            rows.append(('Opening Stock', 'CPP', s, os_.get('volume_mt'), os_.get('cv_gar')))
        for s in C['sites']:
            cg = (data.get('coal_getting', {}).get(s) or {})
            rows.append(('Coal Getting Plan', 'Site', s, cg.get('volume_mt'), cg.get('cv_gar')))
        for s in C['sites']:
            rows.append(('Available Product', 'Site', s, C['available'].get(s), C['cv_site'].get(s)))
        for b in C['brands']:
            dd = (data.get('demand_deal', {}).get(b) or {})
            rows.append(('Shipment Schedule Deal', 'Brand', b, dd.get('volume_deal_mt'), None))
        for s in C['sites']:
            rows.append(('Plan Kapasitas shipment', 'Jetty', s,
                         (data.get('plan_kapasitas', {}).get(s) or {}).get('kapasitas_mt'), None))
        with conn.cursor() as cur:
            cur.execute("TRUNCATE public.business_process RESTART IDENTITY")
            cur.executemany(
                "INSERT INTO public.business_process (category, group_type, item_name, volume_mt, kualitas_gar)"
                " VALUES (%s,%s,%s,%s,%s)", rows)
    return _safe(op)


def refresh_blending_allocation(sol, C):
    """Replace isi public.blending_allocation dari opsi yang DISETUJUI.
    Metabase dashboard alokasi (site x brand) langsung mencerminkan hasil terbaru."""
    if not sol:
        return False

    def op(conn):
        rows = []
        for s in C['sites']:
            for b in C['brands']:
                ship = (sol.get('x', {}).get(s, {}) or {}).get(b, 0) or 0
                allow = (C.get('allowance', {}).get(s, {}) or {}).get(b)
                rows.append((s, b, ship, allow, (C['cv_site'].get(s) or 0) * ship))
        with conn.cursor() as cur:
            cur.execute("TRUNCATE public.blending_allocation RESTART IDENTITY")
            cur.executemany(
                "INSERT INTO public.blending_allocation (source, product, shipment_mt, blending_allowance_mt, kualitas)"
                " VALUES (%s,%s,%s,%s,%s)", rows)
    return _safe(op)
