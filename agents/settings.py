"""Constraint Settings — parameter min/max yang bisa diedit planner lewat menu Constraints.

Menyimpan kapasitas, CV, TS (Total Sulphur), Ash, Na2O per brand + assay per Site ke
config/constraint_settings.json (DATA_DIR agar writable di serverless). Default = quality-safe:
CV min dinaikkan margin di atas batas reject supaya blending TIDAK mepet garis reject,
dan brand CV tinggi didorong kualitasnya (quality reward di optimizer).

Penting: modul optimizer/constraint TETAP identik bila dipanggil tanpa settings (jalur test
baseline 24.225.858,52 tidak berubah). Settings hanya aktif lewat app.py.
"""
import os, json, pathlib

ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = pathlib.Path(os.environ.get('DATA_DIR', str(ROOT)))
PATH = DATA_DIR / 'config/constraint_settings.json'

# assay default per Site (simulasi realistis Berau — bisa diedit di menu Constraints)
SITE_ASSAY = {
    'Lati':      {'ts': 0.60, 'ash': 4.5, 'na2o': 0.40},
    'Binungan':  {'ts': 0.50, 'ash': 5.0, 'na2o': 0.50},
    'Sambarata': {'ts': 0.40, 'ash': 3.8, 'na2o': 0.35},
    'Gurimbang': {'ts': 0.90, 'ash': 7.5, 'na2o': 0.90},
    'BMO3':      {'ts': 1.10, 'ash': 9.0, 'na2o': 1.20},
}
# batas atas kualitas per brand (default longgar agar feasible; perketat lewat menu)
BRAND_QUALITY = {
    'Eboni':    {'ts': 1.2, 'ash': 6.0,  'na2o': 1.5},
    'Mahoni B': {'ts': 1.2, 'ash': 6.0,  'na2o': 1.5},
    'Agathis':  {'ts': 1.2, 'ash': 7.0,  'na2o': 1.5},
    'Sungkai':  {'ts': 1.2, 'ash': 8.0,  'na2o': 1.5},
    'Sungkai B':{'ts': 1.2, 'ash': 9.0,  'na2o': 1.5},
    'CV 4600':  {'ts': 1.3, 'ash': 10.0, 'na2o': 1.6},
    'CV 4200':  {'ts': 1.3, 'ash': 11.0, 'na2o': 1.6},
    'CV 3800':  {'ts': 1.4, 'ash': 12.0, 'na2o': 1.8},
}

QUALITY_MARGIN_CV = 75    # kcal — CV blend minimal = reject + margin (jauh dari garis reject)
QUALITY_REWARD = 0.0008   # bobot kecil: dorong CV brand premium naik tanpa mengalahkan revenue


def defaults(manifest):
    spec = manifest['brand_spec']
    brands, sites = manifest['brands'], manifest['sites']
    total_cap_hint = None
    cv = {}
    for b in brands:
        rej, typ = spec[b]['cv_min_reject'], spec[b]['cv_max_typical']
        cvmin = min(rej + QUALITY_MARGIN_CV, typ - 10)   # jaga tetap < max
        cv[b] = {'min': round(cvmin), 'max': typ, 'reject': rej}
    def qd(dim):
        return {b: {'min': 0.0, 'max': BRAND_QUALITY[b][dim] if b in BRAND_QUALITY else 99} for b in brands}
    return {
        'enabled': True,
        'quality_margin_cv': QUALITY_MARGIN_CV,
        'quality_reward': QUALITY_REWARD,
        'capacity': {'total_min': 0, 'total_max': None,
                     'per_jetty': {s: {'min': 0, 'max': None} for s in sites}},
        'cv': cv,
        'ts':   qd('ts'),
        'ash':  qd('ash'),
        'na2o': qd('na2o'),
        'site_assay': {s: dict(SITE_ASSAY.get(s, {'ts': 0.6, 'ash': 5.0, 'na2o': 0.5})) for s in sites},
    }


def load(manifest):
    d = defaults(manifest)
    # 1) prioritas: constraint terbaru dari Postgres (persist lintas restart/deploy)
    try:
        from agents import db
        dbc = db.load_constraints()
        if dbc:
            _merge(d, dbc)
            return d
    except Exception:
        pass
    # 2) fallback: file JSON lokal
    try:
        if PATH.exists():
            _merge(d, json.loads(PATH.read_text(encoding='utf-8')))
    except Exception:
        pass
    return d


def save(settings):
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps(settings, indent=1, ensure_ascii=False), encoding='utf-8')
        return True
    except Exception:
        return False


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
