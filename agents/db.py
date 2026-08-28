"""Lapisan persistensi Postgres — menulis upload, ronde blending, keputusan, dan
alokasi hasil ke database `defaultdb` yang SAMA dengan sumber data Metabase.

Desain aman-gagal (fail-safe): bila DATABASE_URL belum di-set atau koneksi gagal,
SEMUA fungsi menjadi no-op sehingga web app tetap jalan (fallback file JSON di app.py
tidak terganggu). Metabase update otomatis karena membaca tabel yang sama.

Arsitektur (sesuai diagram): Web (predict/blending) --write--> PostgreSQL(defaultdb)
                                                     --read--> Metabase & Claude
"""
import os, json, pathlib, datetime, decimal, hashlib

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

# tabel TIME-SERIES / INSIGHT — butuh kolom waktu (monitoring harian + ETA kapal).
# Grafik "Insight (Database)" & jadwal ETA membaca tabel ini LANGSUNG.
SCHEMA_TS = """
CREATE TABLE IF NOT EXISTS coalblend_vessels (
    id serial PRIMARY KEY,
    vessel_name text NOT NULL,
    buyer text,
    brand text,
    capacity_mt numeric,
    eta timestamptz,
    laycan_start date,
    laycan_end date,
    status text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS coalblend_daily_stats (
    id serial PRIMARY KEY,
    stat_date date NOT NULL,
    site text NOT NULL,
    opening_mt numeric,
    coal_getting_mt numeric,
    shipment_mt numeric,
    closing_mt numeric,
    util numeric,
    cv_gar numeric
);
CREATE TABLE IF NOT EXISTS coalblend_barge_trips (
    id serial PRIMARY KEY,
    trip_date date NOT NULL,
    barge_id text NOT NULL,
    site text,
    vessel_name text,
    brand text,
    cargo_mt numeric,
    status text,
    eta timestamptz,
    departed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


def init():
    """Buat tabel bila belum ada. Best-effort, dipanggil sekali saat startup."""
    if not enabled():
        _log("DATABASE_URL belum di-set — persistensi Postgres NONAKTIF (pakai file JSON).")
        return False
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute(_EXISTING_DDL)
            cur.execute(SCHEMA_TS)
        conn.commit()
        _log("Skema Postgres siap (history + existing + time-series).")
        seed_demo()  # isi dummy bila tabel insight/history kosong
        return True
    except Exception as e:
        _log(f"init() gagal: {e!r}")
        return False
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def _safe(fn):
    """Jalankan operasi tulis; tangkap semua error agar web flow tak pernah putus."""
    global _WARNED
    if not enabled():
        return False
    conn = None
    try:
        conn = _connect()
        fn(conn)
        conn.commit()
        return True
    except Exception as e:
        _log(f"{getattr(fn, '__name__', 'op')} gagal: {e!r}")
        if conn:
            try: conn.rollback()
            except Exception: pass
        if not _WARNED:
            _WARNED = True
            _log("Peringatan pertama tercatat — cek DATABASE_URL / jaringan / SSL.")
        return False
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


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
def load_latest_state():
    """Baca data input run TERBARU langsung dari Postgres (untuk deploy stateless spt Vercel,
    di mana file output/ ephemeral). Kembalikan {'data': {...}} format ingestion, atau None."""
    if not enabled():
        return None
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("SELECT run_id, username, sumber FROM coalblend_runs ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                cur.execute("SELECT run_id, username, sumber FROM coalblend_uploads ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
            if not row:
                return None
            run_id, username, sumber = row
            cur.execute(
                "SELECT file_key, entity, volume_mt, cv_gar FROM coalblend_input_data WHERE run_id=%s",
                (run_id,))
            rows = cur.fetchall()
        if not rows:
            return None
        data = {'status': 'VALID', 'opening_stock': {}, 'coal_getting': {},
                'demand_deal': {}, 'plan_kapasitas': {}}
        for fk, entity, vol, cv in rows:
            v = float(vol) if vol is not None else 0.0
            if fk == 'demand_deal':
                data.setdefault(fk, {})[entity] = {'volume_deal_mt': v}
            elif fk == 'plan_kapasitas':
                data.setdefault(fk, {})[entity] = {'kapasitas_mt': v}
            elif fk in ('opening_stock', 'coal_getting'):
                data[fk][entity] = {'volume_mt': v, 'cv_gar': float(cv) if cv is not None else 0.0}
        return {'user': username or 'db', 'run_id': run_id,
                'sumber': f'Postgres · {sumber or "defaultdb"}', 'data': data, 'alerts': []}
    except Exception as e:
        _log(f"load_latest_state gagal: {e!r}")
        return None
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


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


# ============================================================================
# INSIGHT / TIME-SERIES — data untuk grafik dashboard, SEMUA dari Postgres.
# Generator dipakai bersama oleh seed_demo() (INSERT) & fallback insights()
# (bila DATABASE_URL belum di-set, agar grafik tetap render dengan label jelas).
# ============================================================================
_SEED_SITES = [   # (site, opening, coal_getting, shipment_bulan, cv, jetty)
    ('Lati',      200000,  600000,  625000, 5000,  650000),
    ('Binungan',  190000, 1000000, 1040000, 4950, 1100000),
    ('Sambarata', 250000,  350000,  500000, 5900,  450000),
    ('Gurimbang',  50000,  650000,  650000, 3880,  660000),
    ('BMO3',       10000,  200000,  185000, 3350,  140000),
]
_SEED_VESSELS = [   # (vessel, buyer, brand)
    ('MV Andhika Paramesti', 'PLTU Suralaya',      'CV 4600'),
    ('MV Meratus Zamrud',    'PLTU Indramayu',     'Sungkai'),
    ('MV Nusantara Jaya',    'PLTU Lontar',        'CV 4200'),
    ('MV Sinar Borneo',      'PLTU Cirebon',       'Mahoni B'),
    ('MV Karya Bahari',      'PLTU Labuan',        'Sungkai B'),
    ('MV Ocean Harmony',     'PLTU Tanjung Jati',  'Agathis'),
    ('MV Bulk Prosperity',   'PLTU Paiton',        'Eboni'),
    ('MV Samudra Biru',      'PLTU Pelabuhan Ratu','CV 3800'),
]
_BASELINE = 24225858.52
_STATUS_CYCLE = ['Scheduled', 'En-route', 'At Anchorage', 'Discharging']


def _rnd(*parts):
    h = hashlib.sha1('|'.join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _gen_daily(days=30):
    today = datetime.date.today()
    out = []
    for d in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=d)
        for (site, op, cg, shm, cv, jet) in _SEED_SITES:
            noise = 0.9 + _rnd('ds', site, d) * 0.2
            ship = round(shm / 30 * noise)
            cgd = round(cg / 30 * noise)
            out.append({'stat_date': day, 'site': site, 'opening_mt': op,
                        'coal_getting_mt': cgd, 'shipment_mt': ship,
                        'closing_mt': round(op + cg / 30 - ship),
                        'util': round(ship / (jet / 30), 3), 'cv_gar': cv})
    return out


def _gen_vessels():
    now = datetime.datetime.now()
    out = []
    for i, (name, buyer, brand) in enumerate(_SEED_VESSELS):
        cap = int(50000 + _rnd('cap', name) * 30000)
        eta = now + datetime.timedelta(hours=round(_rnd('eta', name) * 264 - 48))  # -2..+9 hari
        ls = eta.date(); le = ls + datetime.timedelta(days=2)
        out.append({'vessel_name': name, 'buyer': buyer, 'brand': brand, 'capacity_mt': cap,
                    'eta': eta, 'laycan_start': ls, 'laycan_end': le,
                    'status': _STATUS_CYCLE[i % len(_STATUS_CYCLE)]})
    return sorted(out, key=lambda v: v['eta'])


def _gen_runs(n=8):
    now = datetime.datetime.now()
    out = []
    for i in range(n):
        rid = f'seed{i:02d}'; ts = now - datetime.timedelta(days=(n - i))
        base = _BASELINE * (0.97 + _rnd('rev', i) * 0.06)
        scen = [('A', 'Max Revenue', 1.0), ('B', 'Quality-Safe', 0.995), ('C', 'Evakuasi', 0.988)]
        out.append({'run_id': rid, 'round_no': i + 1, 'ts': ts,
                    'scenarios': [{'scenario_id': s, 'nama': nm, 'revenue': round(base * m)} for s, nm, m in scen]})
    return out


def _gen_decisions(n=8):
    now = datetime.datetime.now()
    out = []
    for i in range(n):
        aksi = 'approve' if _rnd('dec', i) > 0.25 else 'reject'
        opsi = 'A' if _rnd('op', i) > 0.4 else ('B' if _rnd('op2', i) > 0.5 else 'C')
        out.append({'run_id': f'seed{i:02d}', 'round_no': i + 1,
                    'decided_at': now - datetime.timedelta(days=(n - i)),
                    'scenario_id': opsi, 'aksi': aksi,
                    'revenue': round(_BASELINE * (0.97 + _rnd('r2', i) * 0.05))})
    return out


def _empty(cur, table):
    cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
    return cur.fetchone() is None


def seed_demo():
    """Isi dummy HANYA bila tabel kosong (tidak menimpa data asli). Idempotent."""
    if not enabled():
        return False
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            if _empty(cur, 'coalblend_daily_stats'):
                for r in _gen_daily():
                    cur.execute(
                        "INSERT INTO coalblend_daily_stats (stat_date,site,opening_mt,coal_getting_mt,shipment_mt,closing_mt,util,cv_gar)"
                        " VALUES (%(stat_date)s,%(site)s,%(opening_mt)s,%(coal_getting_mt)s,%(shipment_mt)s,%(closing_mt)s,%(util)s,%(cv_gar)s)", r)
            if _empty(cur, 'coalblend_vessels'):
                for v in _gen_vessels():
                    cur.execute(
                        "INSERT INTO coalblend_vessels (vessel_name,buyer,brand,capacity_mt,eta,laycan_start,laycan_end,status)"
                        " VALUES (%(vessel_name)s,%(buyer)s,%(brand)s,%(capacity_mt)s,%(eta)s,%(laycan_start)s,%(laycan_end)s,%(status)s)", v)
            if _empty(cur, 'coalblend_runs'):
                for r in _gen_runs():
                    cur.execute("INSERT INTO coalblend_runs (run_id,round_no,created_at,username,sumber,node_terakhir,n_alerts)"
                                " VALUES (%s,%s,%s,%s,%s,%s,%s)", (r['run_id'], r['round_no'], r['ts'], 'planner', 'seed demo', 'REVIEW', 3))
                    for sc in r['scenarios']:
                        cur.execute("INSERT INTO coalblend_run_scenarios (run_id,round_no,created_at,scenario_id,nama,revenue,total_ship,feasible)"
                                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (r['run_id'], r['round_no'], r['ts'], sc['scenario_id'], sc['nama'], sc['revenue'], 1500000, True))
            if _empty(cur, 'coalblend_decisions'):
                for d in _gen_decisions():
                    cur.execute("INSERT INTO coalblend_decisions (run_id,round_no,decided_at,validator,scenario_id,aksi,catatan,revenue)"
                                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (d['run_id'], d['round_no'], d['decided_at'], 'planner', d['scenario_id'], d['aksi'], 'seed', d['revenue']))
        conn.commit()
        _log("seed_demo selesai (tabel kosong diisi dummy time-series/insight).")
        return True
    except Exception as e:
        _log(f"seed_demo gagal: {e!r}")
        if conn:
            try: conn.rollback()
            except Exception: pass
        return False
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def _iso(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v


def _fetch(sql, params=()):
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            rows = cur.fetchall()
        return [{c: _iso(v) for c, v in zip(cols, r)} for r in rows]
    except Exception as e:
        _log(f"_fetch gagal: {e!r}")
        return None
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def insights():
    """Kumpulan insight untuk grafik dashboard. Dari Postgres bila terhubung,
    selain itu dummy in-memory (label 'contoh') agar grafik tetap tampil."""
    if enabled():
        rev = _fetch("SELECT round_no, max(revenue) AS revenue, min(created_at) AS ts"
                     " FROM coalblend_run_scenarios GROUP BY round_no ORDER BY round_no")
        daily = _fetch("SELECT stat_date, site, sum(shipment_mt) AS shipment"
                       " FROM coalblend_daily_stats GROUP BY stat_date, site ORDER BY stat_date, site")
        dec = _fetch("SELECT aksi, count(*) AS n FROM coalblend_decisions GROUP BY aksi")
        ves = _fetch("SELECT vessel_name, buyer, brand, capacity_mt, eta, laycan_start, laycan_end, status"
                     " FROM coalblend_vessels ORDER BY eta")
        if rev is not None and daily is not None:
            return {'source': 'postgres', 'revenue_trend': rev, 'daily_shipment': daily,
                    'decisions': dec or [], 'vessels': ves or [],
                    'sites': [s[0] for s in _SEED_SITES]}
    # fallback in-memory
    daily = [{'stat_date': r['stat_date'].isoformat(), 'site': r['site'], 'shipment': r['shipment_mt']}
             for r in _gen_daily()]
    rev = [{'round_no': r['round_no'], 'revenue': max(s['revenue'] for s in r['scenarios']),
            'ts': r['ts'].isoformat()} for r in _gen_runs()]
    from collections import Counter
    dc = Counter(d['aksi'] for d in _gen_decisions())
    dec = [{'aksi': k, 'n': v} for k, v in dc.items()]
    ves = [{'vessel_name': v['vessel_name'], 'buyer': v['buyer'], 'brand': v['brand'],
            'capacity_mt': v['capacity_mt'], 'eta': v['eta'].isoformat(),
            'laycan_start': v['laycan_start'].isoformat(), 'laycan_end': v['laycan_end'].isoformat(),
            'status': v['status']} for v in _gen_vessels()]
    return {'source': 'contoh (DB tidak terhubung)', 'revenue_trend': rev, 'daily_shipment': daily,
            'decisions': dec, 'vessels': ves, 'sites': [s[0] for s in _SEED_SITES]}
