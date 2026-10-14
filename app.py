"""CoalBlend AI MVP 1 — Web App (login + input data + run pipeline + dashboard + alerts).
Orkestrasi 4 agent: Ingestion -> Constraint -> Optimizer -> Synthesizer.
Login MVP: kredensial demo di config/users.json (sha256). Ganti dengan SSO korporat saat produksi.
"""
import os, json, hashlib, pathlib
import hashlib as _h
from flask import Flask, request, session, redirect, render_template_string
from agents import ingestion, constraint, optimizer, synthesizer, orchestrator
from agents import db  # persistensi Postgres (defaultdb) — Metabase baca DB yang sama
from agents import settings as cset  # constraint settings (menu Constraints): CV/TS/Ash/Na2O/kapasitas
from agents.dashboard import DASH_HTML

ROOT = pathlib.Path(__file__).parent
# DATA_DIR = lokasi tulis runtime. Default = repo (dev lokal). Di serverless read-only
# (Vercel) set DATA_DIR=/tmp agar output/ & calibration bisa ditulis. Best-effort mkdir.
DATA_DIR = pathlib.Path(os.environ.get('DATA_DIR', str(ROOT)))
for _d in ('output', 'config'):
    try: (DATA_DIR / _d).mkdir(parents=True, exist_ok=True)
    except Exception: pass
MANIFEST = json.loads((ROOT / 'config/constraint_manifest.json').read_text())
USERS = json.loads((ROOT / 'config/users.json').read_text())
SETTINGS = cset.load(MANIFEST)  # quality-safe default; diedit lewat /constraints

app = Flask(__name__)
# produksi (Railway): set SECRET_KEY di env; fallback demo untuk dev lokal
app.secret_key = os.environ.get('SECRET_KEY', 'coalblend-mvp1-demo')
db.ensure_ready()  # cek ringan skema sekali; init() penuh HANYA bila struktur belum ada (hemat cold-start)

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{background:#1a1a19;color:#f0efec;font:14px 'IBM Plex Sans',sans-serif;display:flex;justify-content:center;padding-top:60px}
.card{background:#20201f;border:1px solid #37342f;border-radius:14px;padding:28px;width:430px}
h1{font-size:18px;margin:0 0 4px}.sub{color:#c3c2b7;font-size:11px;font-family:monospace;margin-bottom:18px}
input,button{width:100%;padding:9px 11px;margin:5px 0;border-radius:8px;border:1px solid #37342f;background:#262523;color:#f0efec;font-size:13px}
button{background:#c6613f;border:none;font-weight:700;cursor:pointer;margin-top:12px;color:#fff}
label{font-size:11px;color:#c3c2b7;font-family:monospace;text-transform:uppercase;letter-spacing:.05em}
.err{color:#ff6159;font-size:12px}.ok{color:#7d9b76;font-size:12px}
a{color:#6b9bd1}</style></head><body><div class="card">{{ body|safe }}</div></body></html>"""

def logged_in(): return session.get('user') is not None

@app.route('/', methods=['GET', 'POST'])
def login():
    if logged_in(): return redirect('/dashboard')
    err = ''
    if request.method == 'POST':
        u, p = request.form.get('u', ''), request.form.get('p', '')
        if USERS.get(u) == hashlib.sha256(p.encode()).hexdigest():
            session['user'] = u
            return redirect('/dashboard')
        err = '<div class="err">Username / password salah.</div>'
    body = f"""<h1>beraucoal · Cortex</h1><div class="sub">Coal Blending Optimization &amp; Real Time Execution — Login</div>
    <form method="post"><label>Username</label><input name="u" autofocus>
    <label>Password</label><input name="p" type="password">{err}<button>Masuk</button></form>
    <div class="sub" style="margin-top:14px">Demo: planner / coalblend2026</div>"""
    return render_template_string(PAGE, body=body)

@app.route('/input', methods=['GET', 'POST'])
def input_data():
    if not logged_in(): return redirect('/')
    if request.method == 'POST':
        files = {}
        for key in ('opening_stock', 'coal_getting', 'demand_deal'):
            f = request.files.get(key)
            if f and f.filename:
                files[key] = (f.read(), f.filename)
        return run_pipeline(files)
    rows = ''.join(
        f'<label>{k.replace("_"," ").title()} (.csv / .xlsx) '
        f'<a href="/template/{k}" download style="text-transform:none;color:#6b9bd1;font-weight:600">⬇ unduh template</a>'
        f'</label><input type="file" name="{k}">'
        for k in ('opening_stock', 'coal_getting', 'demand_deal'))
    sites = ', '.join(MANIFEST['sites'])
    body = f"""<h1>Input Data Bulanan</h1><div class="sub">User: {session['user']} · cadence KB-12 (tgl 1 &amp; tgl 3–5) · <a href="/logout">logout</a></div>
    <div class="sub" style="background:#262523;border:1px solid #37342f;border-radius:9px;padding:10px 12px;margin-bottom:14px;text-transform:none;line-height:1.5">
    📄 Belum punya format? <b>Unduh template</b> di tiap kolom — sudah sesuai nama Site: <b>{sites}</b>.
    Isi angkanya, lalu upload. <a href="/template/all" download style="color:#6b9bd1;font-weight:600">⬇ unduh semua (ZIP)</a></div>
    <form method="post" enctype="multipart/form-data">{rows}<button>Jalankan Optimisasi</button></form>
    <div class="sub" style="margin-top:12px">Kosongkan semua untuk memakai <b>fixtures simulasi</b> (uji baseline 24.225.858,52).</div>"""
    return render_template_string(PAGE, body=body)

@app.route('/template/<key>')
def template(key):
    if not logged_in(): return redirect('/')
    from flask import Response
    keys = ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas')
    if key == 'all':
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for k in ('opening_stock', 'coal_getting', 'demand_deal'):
                p = ROOT / f'fixtures/{k}_simulasi.csv'
                if p.exists(): z.writestr(f'{k}_template.csv', p.read_text(encoding='utf-8'))
        return Response(buf.getvalue(), mimetype='application/zip',
                        headers={'Content-Disposition': 'attachment; filename=coalblend_templates.zip'})
    if key not in keys:
        return 'template tidak dikenal', 404
    p = ROOT / f'fixtures/{key}_simulasi.csv'
    if not p.exists(): return 'template tidak ditemukan', 404
    return Response(p.read_text(encoding='utf-8'), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={key}_template.csv'})

def _rounds():
    p = DATA_DIR / 'output/rounds.json'
    return json.loads(p.read_text()) if p.exists() else []

def _rounds_save(r):
    (DATA_DIR / 'output/rounds.json').write_text(json.dumps(r, indent=1, ensure_ascii=False))

# ===== CYCLE: tiap perubahan Constraint = cycle baru; iterasi (ronde) reset per cycle =====
def _cycle_state():
    p = DATA_DIR / 'output/cycle.json'
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    return {'cycle': 1, 'hash': None}

def _cycle_state_save(d):
    (DATA_DIR / 'output/cycle.json').write_text(json.dumps(d, ensure_ascii=False))

def _cycle_now():
    return _cycle_state().get('cycle', 1)

def _cycle_hash(settings):
    """Hash bagian constraint yang relevan — pembeda apakah constraint benar-benar berubah."""
    key = json.dumps({k: (settings or {}).get(k) for k in
                      ('enabled', 'quality_margin_cv', 'quality_reward', 'cv', 'ts', 'ash', 'na2o',
                       'capacity', 'site_assay')}, sort_keys=True, ensure_ascii=False)
    return _h.sha1(key.encode()).hexdigest()[:16]

def _cycle_bump_if_changed(settings):
    """Simpan Constraint dengan nilai berubah → cycle += 1 (iterasi reset ke 1).
    Simpan pertama (belum ada hash) = tetapkan cycle saat ini tanpa menaikkan."""
    h = _cycle_hash(settings); st = _cycle_state()
    if st.get('hash') is None:
        st['hash'] = h
    elif h != st['hash']:
        st['cycle'] = st.get('cycle', 1) + 1; st['hash'] = h
    _cycle_state_save(st)
    return st['cycle']

def _cycle_iter(rounds, cyc):
    """Iterasi ke-berapa dalam cycle ini (reset per cycle)."""
    return sum(1 for r in rounds if r.get('cycle') == cyc) + 1

def _chosen():
    """Opsi (A/B/C) yang DISETUJUI validator untuk run terakhir — agar menu Revenue/Blending
    selaras dengan opsi terpilih, bukan solve baseline."""
    p = DATA_DIR / 'output/chosen.json'
    return json.loads(p.read_text()) if p.exists() else None

def _chosen_save(d):
    (DATA_DIR / 'output/chosen.json').write_text(json.dumps(d, ensure_ascii=False))

def _inject_print(html, opsi):
    """Sisipkan toolbar cetak (Simpan sebagai PDF via window.print) + judul + CSS print
    ke halaman report agar bisa diunduh sebagai PDF dari browser (tanpa lib PDF berat)."""
    head = (f"<title>Report Final Opsi {opsi} - beraucoal Cortex</title>"
            "<style>@media print{.rbar{display:none!important}body{padding:0}}"
            ".rbar{position:sticky;top:0;display:flex;gap:10px;align-items:center;background:#131c1f;"
            "border-bottom:1px solid #23312f;padding:10px 16px;margin:-16px -16px 18px;z-index:9;flex-wrap:wrap}"
            ".rbar button,.rbar a{background:#c6613f;color:#fff;border:none;font:700 12px 'IBM Plex Sans',sans-serif;"
            "padding:9px 15px;border-radius:8px;cursor:pointer;text-decoration:none}"
            ".rbar a.sec{background:transparent;border:1px solid #37342f;color:#cfe3df}"
            ".rbar .tip{color:#8aa09c;font:11px 'IBM Plex Mono',monospace}</style>")
    bar = ('<div class="rbar"><button onclick="window.print()">⬇ Simpan sebagai PDF</button>'
           '<a class="sec" href="/dashboard?go=rv">← Revenue</a>'
           '<a class="sec" href="/review">Review &amp; Validasi</a>'
           '<span class="tip">Tip: pada dialog cetak pilih "Save as PDF / Simpan sebagai PDF"</span></div>')
    html = html.replace('</head>', head + '</head>', 1)
    html = html.replace('<body>', '<body>' + bar, 1)
    return html

def _history_html():
    rows = ''
    for r in _rounds():
        opsi = ' · '.join(f"{k}: {v['revenue']:,.0f}" if v.get('revenue') else f"{k}: INF" for k, v in r['opsi'].items())
        ch = r.get('chosen')
        pil = (f"<b style='color:#7fe39b'>Opsi {ch['opsi']} ✓</b> — {ch.get('catatan') or 'tanpa catatan'}"
               if ch and ch['aksi'] == 'approve' else
               (f"<b style='color:#ffb3b1'>Ditolak</b> — {ch.get('catatan','')}" if ch else
                "<span style='color:#f6cf86'>menunggu validasi</span>"))
        cyc = r.get('cycle', 1); it = r.get('iter', r.get('no'))
        rows += (f"<tr><td style='text-align:center'><b>{cyc}</b></td><td>Iterasi {it}</td>"
                 f"<td style='text-align:left'>{r['sumber']}</td>"
                 f"<td style='text-align:left;font-size:11px'>{opsi}</td>"
                 f"<td style='text-align:left'>{pil}</td><td>{r['ts'][:16].replace('T',' ')}</td></tr>")
    if not rows: return ''
    return ("<h2>Riwayat Cycle &amp; Iterasi</h2>"
            "<table><tr><th>Cycle</th><th>Iterasi</th><th style='text-align:left'>Sumber Demand</th>"
            "<th style='text-align:left'>Opsi &amp; Revenue</th><th style='text-align:left'>Keputusan Validator</th>"
            "<th>Waktu</th></tr>" + rows + "</table>"
            "<p class='mut' style='font:11px monospace'>Ubah Constraint = <b>Cycle baru</b> (iterasi reset ke 1). "
            "Tiap simulasi/koreksi dalam cycle = iterasi berikutnya. Semua terekam untuk pembelajaran AI. Arsip: output/rounds.json</p>")

def _synth_files_from_last(demand_file):
    """Ronde demand-baru: 3 sumber lain dibawa dari data valid terakhir, demand diganti file baru."""
    st = _last_state(); d = st['data']
    def csv_sites(key):
        rows = 'site,volume_mt,cv_gar\n' + ''.join(
            f"{s},{d[key][s]['volume_mt']},{d[key][s]['cv_gar']}\n" for s in MANIFEST['sites'])
        return rows.encode()
    kap = ('jetty,kapasitas_mt\n' + ''.join(
        f"{s},{d['plan_kapasitas'][s]['kapasitas_mt']}\n" for s in MANIFEST['sites'])).encode()
    return {'opening_stock': (csv_sites('opening_stock'), 'carryover.csv'),
            'coal_getting': (csv_sites('coal_getting'), 'carryover.csv'),
            'plan_kapasitas': (kap, 'carryover.csv'),
            'demand_deal': demand_file}

def _load_calib():
    p = DATA_DIR / 'config/calibration.json'
    if not p.exists(): return {'approval': {}, 'reject': {}, 'total_keputusan': 0, 'skenario_favorit': '-', 'catatan': []}
    return json.loads(p.read_text())

def _save_calib(c):
    if c['approval']:
        c['skenario_favorit'] = max(c['approval'], key=c['approval'].get)
    (DATA_DIR / 'config/calibration.json').write_text(json.dumps(c, indent=1, ensure_ascii=False))

def run_pipeline(files, sumber_demand=None):
    # fallback fixtures untuk demo/validasi
    use_fixtures = not files
    n_upload = len(files)  # jumlah file yang benar-benar diupload user (sebelum inject kapasitas)
    if not files:
        fx = ROOT / 'fixtures'
        files = {k: ((fx / f'{k}_simulasi.csv').read_bytes(), f'{k}_simulasi.csv')
                 for k in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas')}
    # plan_kapasitas tidak lagi di-upload di halaman Input — kapasitas jetty bersumber dari
    # config/Constraint Settings. Selalu sediakan dari baseline config agar constraint.build tak gagal.
    if 'plan_kapasitas' not in files:
        files['plan_kapasitas'] = ((ROOT / 'fixtures/plan_kapasitas_simulasi.csv').read_bytes(),
                                   'plan_kapasitas_config.csv')
    st = orchestrator.run(files, MANIFEST, session.get('user', 'tester'),
                          ingestion, constraint, optimizer, settings=SETTINGS)   # state graph + lineage + trace
    session['run_id'] = st['run_id']
    _sumber = sumber_demand or ('fixtures simulasi' if use_fixtures else f'{n_upload} file input')
    # PERSIST: tiap upload masuk DB (defaultdb) — Metabase baca tabel yang sama
    db.record_upload(st['run_id'], session.get('user', 'tester'), _sumber,
                     st.get('lineage'), st.get('data'))
    if st['node_terakhir'] == 'ALERT':
        return synthesizer.render(None, st.get('C'), st['alerts'],
                                  meta=f"run {st['run_id']} · pipeline berhenti (lihat output/trace.jsonl)")
    C, scenarios = st['C'], st['scenarios']
    app.config['LAST'] = {'C': C, 'scenarios': scenarios, 'run_id': st['run_id'],
                          'data': st.get('data'), 'alerts': st['alerts']}
    a1 = a2 = []  # alerts pre-solve sudah di st['alerts']
    # persist state utk /dashboard, /review (revisit) & /api
    (DATA_DIR / 'output/last_state.json').write_text(json.dumps({
        'user': session.get('user', 'tester'), 'run_id': st['run_id'],
        'sumber': 'fixtures simulasi' if use_fixtures else f'{n_upload} file input',
        'data': st.get('data'), 'alerts': st['alerts'],
    }, ensure_ascii=False))
    # simpan run untuk endpoint keputusan (tanpa objek sol penuh: cukup ringkasan auditabel)
    (DATA_DIR / 'output/last_run.json').write_text(json.dumps(
        {sc['id']: {'nama': sc['nama'], 'revenue': sc['revenue'],
                    'brand_total': sc['sol']['brand_total'] if sc['sol'] else None,
                    'closing': sc['sol']['closing'] if sc['sol'] else None}
         for sc in scenarios}, indent=1, ensure_ascii=False))
    # catat RONDE baru (histori opsi) + CYCLE/ITERASI (iterasi reset per cycle)
    import datetime as _dt
    rounds = _rounds()
    _cyc = _cycle_now(); _it = _cycle_iter(rounds, _cyc)
    rounds.append({'no': len(rounds) + 1, 'cycle': _cyc, 'iter': _it,
                   'ts': _dt.datetime.now().isoformat(timespec='seconds'),
                   'user': session.get('user', 'tester'), 'run_id': st['run_id'],
                   'sumber': sumber_demand or ('fixtures simulasi' if use_fixtures else f'{n_upload} file input'),
                   'opsi': {sc['id']: {'nama': sc['nama'], 'revenue': sc['revenue']} for sc in scenarios},
                   'chosen': None})
    _rounds_save(rounds)
    # PERSIST: tiap run AI blending -> history ronde + opsi ke DB; refresh tabel Metabase input
    db.record_run(st['run_id'], len(rounds), session.get('user', 'tester'), _sumber,
                  st['node_terakhir'], scenarios, len(st['alerts']), cycle=_cyc)
    db.refresh_business_process(st.get('data'), C)
    html = synthesizer.render_review(scenarios, C, st['alerts'], calib=_load_calib(),   # Agent 4 (review HITL)
                                     meta=f"CYCLE {_cyc} · ITERASI {_it} · run {st['run_id']} · validator: {session.get('user','tester')} · lineage: {len(st['lineage']['files'])} file (sha256 tercatat)")
    html = html.replace('</body>', f"<div style='max-width:1180px'>{_history_html()}</div></body>")
    (DATA_DIR / 'output/dashboard.html').write_text(html)
    return html

@app.route('/decide', methods=['POST'])
def decide():
    if not logged_in(): return redirect('/')
    import datetime
    opsi, aksi = request.form.get('opsi'), request.form.get('aksi')
    catatan = request.form.get('catatan', '').strip()
    run = json.loads((DATA_DIR / 'output/last_run.json').read_text()) if (DATA_DIR / 'output/last_run.json').exists() else {}
    rec = {'waktu': datetime.datetime.now().isoformat(timespec='seconds'), 'validator': session['user'],
           'opsi': opsi, 'aksi': aksi, 'catatan': catatan, 'revenue': (run.get(opsi) or {}).get('revenue')}
    with open(DATA_DIR / 'output/decisions.jsonl', 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    c = _load_calib()
    key = 'approval' if aksi == 'approve' else 'reject'
    c[key][opsi] = c[key].get(opsi, 0) + 1
    c['total_keputusan'] += 1
    if catatan: c['catatan'].append({'opsi': opsi, 'aksi': aksi, 'catatan': catatan})
    _save_calib(c)
    orchestrator.decide(session.get('run_id', '?'), session['user'], opsi, aksi, catatan, rec['revenue'])
    # PERSIST: keputusan validator (HITL) -> DB
    db.record_decision(session.get('run_id', '?'), len(_rounds()), session['user'],
                       opsi, aksi, catatan, rec['revenue'])
    rounds = _rounds()
    if rounds and rounds[-1]['chosen'] is None:
        rounds[-1]['chosen'] = {'opsi': opsi, 'aksi': aksi, 'catatan': catatan,
                                'revenue': rec['revenue'], 'validator': session['user'], 'ts': rec['waktu']}
        _rounds_save(rounds)
    # APPROVE -> kunci opsi terpilih supaya menu Revenue/Blending selaras dgn opsi ini
    if aksi == 'approve':
        _chosen_save({'run_id': session.get('run_id', '?'), 'opsi': opsi,
                      'nama': (run.get(opsi) or {}).get('nama', ''), 'catatan': catatan,
                      'validator': session['user'], 'ts': rec['waktu']})
    report_link = ''
    L = app.config.get('LAST')
    if aksi == 'approve':
        report_link = (f'<a href="/report?opsi={opsi}" style="display:inline-block;background:#20201f;'
                       f'border:1px solid #37342f;color:#f0efec;padding:11px 18px;border-radius:9px;'
                       f'text-decoration:none;font-weight:700;margin:6px 0">📄 Buka Report Final &amp; Rekomendasi '
                       f'Eksekusi — bisa disimpan PDF</a>')
        if L:
            sc = next((s for s in L['scenarios'] if s['id'] == opsi and s['sol']), None)
            if sc:
                rp = DATA_DIR / f"output/report_final_{session.get('run_id','x')}_{opsi}.html"
                rp.write_text(synthesizer.render_report(sc, L['C'], session.get('run_id','?'), session['user'], catatan))
                # PERSIST: alokasi opsi disetujui -> history DB + refresh tabel alokasi Metabase
                db.record_blending_history(session.get('run_id', '?'), len(_rounds()), opsi,
                                           session['user'], sc['sol'], L['C'])
                db.refresh_blending_allocation(sc['sol'], L['C'])
    verdict = ('DISETUJUI — blending plan siap dipublikasikan ke Marketing.' if aksi == 'approve'
               else 'DITOLAK — catatan Anda tercatat sebagai sinyal kalibrasi.')
    rev_link = ''
    if aksi == 'approve':
        rev_link = (f'<a href="/dashboard?go=rv" style="display:inline-block;background:#c6613f;color:#fff;'
                    f'padding:11px 18px;border-radius:9px;text-decoration:none;font-weight:700;margin:10px 0">'
                    f'→ Lihat Revenue (CV blending Opsi {opsi})</a>'
                    f'<div class="sub" style="margin:2px 0 8px">Tidak ada koreksi demand lagi? Lanjut ke Revenue — '
                    f'angka &amp; CV blending/kontrak selaras dengan Opsi {opsi} yang Anda pilih.</div>')
    demand_form = ''
    if aksi == 'approve':
        nro = len(_rounds())
        demand_form = (
            f'<div style="border:1px solid rgba(52,199,89,.4);background:rgba(52,199,89,.07);'
            f'border-radius:12px;padding:14px;margin:14px 0;text-align:left">'
            f'<b>Blending plan Ronde {nro} terkunci: Opsi {opsi}</b>'
            f'<div class="sub" style="margin:6px 0">Ada demand baru masuk? Feasibilitas jual berubah — '
            f'blending harus dihitung ulang (3 opsi baru).</div>'
            f'<form method="post" action="/input_demand" enctype="multipart/form-data">'
            f'<label>Upload Demand Baru — demand_deal (.csv/.xlsx: brand, volume_deal_mt total terbaru)</label>'
            f'<input type="file" name="demand_deal" required>'
            f'<button>Jalankan Ronde {nro+1} → 3 Opsi Baru</button></form></div>')
    body = f"""<h1>Keputusan Tercatat</h1><div class="sub">Human-in-the-Loop · audit trail: output/decisions.jsonl</div>
    <p><b>Opsi {opsi}</b> · {verdict}</p>
    <p class="{'ok' if aksi=='approve' else 'err'}">Validator: {session['user']} · Catatan: {catatan or '—'}</p>
    <p class="sub">Kalibrasi: {c['total_keputusan']} keputusan terekam · favorit saat ini: skenario {c.get('skenario_favorit','-')}</p>
    {report_link}
    {rev_link}
    {demand_form}
    <a href="/input">← Input lengkap (4 file)</a> · <a href="/review">Riwayat ronde</a>"""
    return render_template_string(PAGE, body=body)

@app.route('/override', methods=['POST'])
def override():
    if not logged_in(): return redirect('/')
    L = app.config.get('LAST')
    if not L or not L.get('data'):
        return redirect('/input')
    ov, changed = {'cs_min': {}, 'cs_max': {}, 'deal': {}}, []
    C0 = L['C']
    for k, v in request.form.items():
        if '__' not in k: continue
        kind, name = k.split('__', 1)
        try: val = float(v)
        except ValueError: continue
        cur = {'cs_min': C0['cs_min'], 'cs_max': C0['cs_max'], 'deal': C0['deal']}[kind].get(name)
        if cur is not None and abs(val - cur) > 0.5:
            ov[kind][name] = val; changed.append(f'{kind}.{name}: {cur:,.0f} -> {val:,.0f}')
    alasan = request.form.get('alasan', '').strip()
    orchestrator._log(session.get('run_id', '?'), 'OVERRIDE', 'RERUN',
                      {'validator': session['user'], 'alasan': alasan, 'perubahan': changed})
    C, a2 = constraint.build(MANIFEST, L['data'], overrides=ov, settings=SETTINGS)
    if any(s == 'CRITICAL' for s, _, _ in a2):
        return synthesizer.render(None, C, a2, meta=f"override oleh {session['user']} · pre-solve gagal")
    scenarios = optimizer.solve_scenarios(C)
    app.config['LAST'].update({'C': C, 'scenarios': scenarios})
    ov_alert = [('INFO', 'OVERRIDE', f"Re-run dengan override validator ({session['user']}): " +
                 ('; '.join(changed) if changed else 'tanpa perubahan angka') + f" · alasan: {alasan}")]
    return synthesizer.render_review(scenarios, C, ov_alert + a2, calib=_load_calib(),
                                     meta=f"run {session.get('run_id','?')} · MANUAL OVERRIDE aktif · re-run < 1 detik")

def _db_state_complete(st):
    """Valid hanya bila semua entitas manifest lengkap (agar constraint.build tak gagal)."""
    d = (st or {}).get('data') or {}
    need = {'opening_stock': MANIFEST['sites'], 'coal_getting': MANIFEST['sites'],
            'demand_deal': MANIFEST['brands'], 'plan_kapasitas': MANIFEST['sites']}
    return all(set(names) <= set((d.get(k) or {})) for k, names in need.items())

def _last_state():
    p = DATA_DIR / 'output/last_state.json'
    if p.exists():
        return json.loads(p.read_text())
    # baca data run terbaru LANGSUNG dari Postgres (deploy stateless / Vercel)
    dbst = db.load_latest_state()
    if dbst and _db_state_complete(dbst):
        return dbst
    # fallback fixtures
    fx = ROOT / 'fixtures'
    files = {k: ((fx / f'{k}_simulasi.csv').read_bytes(), f'{k}.csv')
             for k in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas')}
    data, a1 = ingestion.ingest(files, MANIFEST)
    return {'user': session.get('user', 'tester'), 'run_id': '-', 'sumber': 'fixtures simulasi',
            'data': data, 'alerts': a1}

def _solve_from(data, deal_override=None):
    if deal_override:
        data = json.loads(json.dumps(data))
        for b, v in deal_override.items():
            if b in data['demand_deal']:
                data['demand_deal'][b]['volume_deal_mt'] = float(v)
    C, a2 = constraint.build(MANIFEST, data, settings=SETTINGS)
    if any(s == 'CRITICAL' for s, _, _ in a2):
        return None, C, a2
    sol, a3 = optimizer.solve(C)
    return sol, C, a2 + a3

def _alert_objs(alerts):
    ackp = DATA_DIR / 'output/alerts_ack.json'
    acked = set(json.loads(ackp.read_text())) if ackp.exists() else set()
    out = []
    for sev, cat, msg in alerts:
        aid = _h.sha1(f'{sev}|{cat}|{msg}'.encode()).hexdigest()[:10]
        out.append({'id': aid, 'sev': sev, 'cat': cat, 'msg': msg, 'acked': aid in acked})
    return out

@app.route('/input_demand', methods=['POST'])
def input_demand():
    if not logged_in(): return redirect('/')
    f = request.files.get('demand_deal')
    if not f or not f.filename:
        return render_template_string(PAGE, body='<h1>Demand belum diunggah</h1><a href="/review">← kembali</a>')
    files = _synth_files_from_last((f.read(), f.filename))
    n = len(_rounds()) + 1
    return run_pipeline(files, sumber_demand=f'demand baru: {f.filename} (ronde {n}; sumber lain carry-over)')

@app.route('/api/alerts/ack', methods=['POST'])
def api_ack():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    aid = (request.get_json(silent=True) or {}).get('id')
    ackp = DATA_DIR / 'output/alerts_ack.json'
    acked = set(json.loads(ackp.read_text())) if ackp.exists() else set()
    if aid: acked.add(aid)
    ackp.write_text(json.dumps(sorted(acked)))
    return {'ok': True, 'acked': len(acked)}

@app.route('/constraints', methods=['GET', 'POST'])
def constraints():
    global SETTINGS
    if not logged_in(): return redirect('/')
    from agents import constraints_page
    if request.method == 'POST':
        # pakai salinan setting di memori sebagai basis (hindari round-trip DB baca saat simpan);
        # form membawa semua field, jadi tiap nilai di-override dari form di bawah.
        s = json.loads(json.dumps(SETTINGS)); f = request.form
        def fnum(key, default=None):
            v = (f.get(key) or '').strip()
            if v == '': return default
            try: return float(v)
            except ValueError: return default
        s['enabled'] = f.get('enabled') == 'on'
        s['quality_margin_cv'] = fnum('qmargin', s.get('quality_margin_cv'))
        s['quality_reward'] = fnum('qreward', s.get('quality_reward'))
        s['capacity']['total_min'] = fnum('cap_total_min', 0) or 0
        s['capacity']['total_max'] = fnum('cap_total_max', None)
        for site in MANIFEST['sites']:
            pj = s['capacity'].setdefault('per_jetty', {}).setdefault(site, {})
            pj['min'] = fnum(f'jetty_min_{site}', 0) or 0
            pj['max'] = fnum(f'jetty_max_{site}', None)
            a = s['site_assay'].setdefault(site, {})
            for dim in ('ts', 'ash', 'na2o'):
                a[dim] = fnum(f'assay_{dim}_{site}', a.get(dim))
        _margin = s.get('quality_margin_cv') or 0   # buffer global: CV min minimal = reject + margin
        for b in MANIFEST['brands']:
            spec_b = MANIFEST['brand_spec'][b]
            s['cv'].setdefault(b, {})['max'] = fnum(f'cv_max_{b}', s['cv'][b].get('max'))
            _mn = fnum(f'cv_min_{b}', s['cv'][b].get('min')) or spec_b['cv_min_reject']
            _mx = s['cv'][b]['max'] or spec_b['cv_max_typical']
            # margin berlaku global; kolom per-brand hanya menaikkan (memperketat) di atas buffer
            s['cv'][b]['min'] = min(round(max(float(_mn), spec_b['cv_min_reject'] + float(_margin))), _mx - 5)
            for dim in ('ts', 'ash', 'na2o'):
                d = s[dim].setdefault(b, {})
                d['min'] = fnum(f'{dim}_min_{b}', 0) or 0
                d['max'] = fnum(f'{dim}_max_{b}', None)
        cset.save(s)                                   # simpan file JSON (fallback lokal)
        db_ok = db.save_constraints(s, session['user'])  # UPDATE tabel Postgres (Aiven)
        _cycle_bump_if_changed(s)                       # constraint berubah → CYCLE baru (iterasi reset)
        SETTINGS = s                                    # pakai hasil simpan di memori — hindari 1 round-trip DB reload (lebih cepat)
        return constraints_page.render(SETTINGS, MANIFEST, saved=True, db_ok=db_ok)
    return constraints_page.render(SETTINGS, MANIFEST)

@app.route('/api/reco')
def api_reco():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    return db.reco(MANIFEST)

@app.route('/api/dbstatus')
def api_dbstatus():
    """Cek apakah app terhubung & mengikuti Postgres. Buka di browser (perlu login):
    https://<app>/api/dbstatus — connected:true + daftar tabel coalblend_* = Vercel ikut DB."""
    if not logged_in(): return {'error': 'unauthorized — login dulu'}, 401
    st = db.status()
    dsn = db._dsn() or ''
    import re
    st['host'] = re.sub(r'^.*@', '', dsn).split('?')[0] if '@' in dsn else '-'  # host saja, tanpa kredensial
    return st

@app.route('/api/selftest')
def api_selftest():
    """Diagnostik solver/runtime untuk debug deploy (login diperlukan). Tanpa rahasia —
    lapor versi PuLP, solver tersedia, status highspy, dan traceback asli dari solve."""
    if not logged_in(): return {'error': 'unauthorized — login dulu'}, 401
    import sys, traceback as _tb
    out = {'python': sys.version.split()[0]}
    try:
        import pulp
        out['pulp_version'] = pulp.__version__
        try: out['solvers_available'] = pulp.listSolvers(onlyAvailable=True)
        except Exception as e: out['solvers_available_error'] = repr(e)
    except Exception as e:
        out['pulp_import_error'] = repr(e)
    try:
        import highspy  # noqa
        out['highspy'] = 'ok'
    except Exception as e:
        out['highspy_error'] = repr(e)
    try:
        from agents import optimizer
        s = optimizer._solver()
        out['solver_picked'] = type(s).__name__ if s else None
    except Exception:
        out['solver_picked_error'] = _tb.format_exc().splitlines()[-1]
    def _probe(tag, data, settings):
        try:
            C, a = constraint.build(MANIFEST, data, settings=settings)
            crit = [m for s, c, m in a if s == 'CRITICAL']
            sol, a2 = optimizer.solve(C)
            crit += [m for s, c, m in (a2 or []) if s == 'CRITICAL']
            return {'feasible': sol is not None, 'revenue': (sol or {}).get('revenue'),
                    'critical': crit[:4]}
        except Exception:
            return {'error': _tb.format_exc().splitlines()[-1]}
    try:
        st = _last_state()
        d = st['data']
        out['sumber'] = st.get('sumber')
        # sanity data (sumber infeasibility aritmetis)
        try:
            sites = MANIFEST['sites']; brands = MANIFEST['brands']
            avail = {s: d['opening_stock'][s]['volume_mt'] + d['coal_getting'][s]['volume_mt'] for s in sites}
            total_deal = sum(d['demand_deal'][b]['volume_deal_mt'] for b in brands)
            total_cap = sum(d['plan_kapasitas'][s]['kapasitas_mt'] for s in sites)
            csmin = MANIFEST['closing_stock_band_simulasi']
            bad = [f"{s}: avail {avail[s]:,.0f} < cs_min {csmin[s]['min']:,.0f}" for s in sites if avail[s] < csmin[s]['min']]
            out['sanity'] = {'total_deal': round(total_deal), 'total_capacity': round(total_cap),
                             'deal_gt_cap': total_deal > total_cap,
                             'sites_avail_lt_csmin': bad,
                             'keys_ok': {'sites': sorted(d.get('opening_stock', {})) == sorted(sites),
                                         'brands': sorted(d.get('demand_deal', {})) == sorted(brands)}}
        except Exception:
            out['sanity_error'] = _tb.format_exc().splitlines()[-1]
        out['solve_with_settings'] = _probe('settings', d, SETTINGS)
        out['solve_baseline'] = _probe('baseline', d, None)
    except Exception:
        out['state_error'] = _tb.format_exc()
    # kontrol: fixtures (data bersih) harus selalu feasible
    try:
        fx = ROOT / 'fixtures'
        files = {k: ((fx / f'{k}_simulasi.csv').read_bytes(), f'{k}.csv')
                 for k in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas')}
        fdata, _ = ingestion.ingest(files, MANIFEST)
        out['solve_fixtures'] = _probe('fixtures', fdata, None)
    except Exception:
        out['fixtures_error'] = _tb.format_exc().splitlines()[-1]
    return out

@app.route('/dashboard')
def dashboard():
    if not logged_in(): return redirect('/')
    return DASH_HTML

@app.route('/report')
def report():
    """Report Final & Rekomendasi Eksekusi (opsi disetujui) — dibuat ulang on-demand
    (aman di serverless) + toolbar 'Simpan sebagai PDF'."""
    if not logged_in(): return redirect('/')
    ch = _chosen()
    opsi = request.args.get('opsi') or (ch or {}).get('opsi')
    if not opsi:
        return render_template_string(PAGE, body='<h1>Belum ada opsi disetujui</h1>'
                                      '<a href="/review">← Review &amp; Validasi</a>')
    st = _last_state()
    _, C, _ = _solve_from(st['data'])
    sc = next((s for s in optimizer.solve_scenarios(C) if s['id'] == opsi and s.get('sol')), None)
    if not sc:
        return render_template_string(PAGE, body=f'<h1>Opsi {opsi} tidak tersedia untuk run ini</h1>'
                                      '<a href="/review">← Review &amp; Validasi</a>')
    validator = (ch or {}).get('validator', session.get('user', '-'))
    catatan = (ch or {}).get('catatan', '') if (ch and ch.get('opsi') == opsi) else ''
    html = synthesizer.render_report(sc, C, st.get('run_id', '?'), validator, catatan)
    return _inject_print(html, opsi)

@app.route('/api/state')
def api_state():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    st = _last_state()
    sol, C, alerts = _solve_from(st['data'])
    # Infeasible (mis. total shipment melebihi Max, atau Quality margin terlalu ketat) TIDAK
    # ditutupi: solution=null + alerts berisi alasan, agar batas constraint benar-benar dihormati.
    # SELARAS OPSI TERPILIH: bila validator sudah approve opsi (A/B/C) utk run ini,
    # tampilkan solusi opsi tsb (CV blending/kontrak selaras), bukan solve baseline.
    opsi_meta = None
    ch = _chosen()
    if sol is not None and ch and ch.get('run_id') == st.get('run_id') and ch.get('opsi'):
        scen = optimizer.solve_scenarios(C)
        csc = next((s for s in scen if s['id'] == ch['opsi'] and s.get('sol')), None)
        if csc:
            sol = csc['sol']
            opsi_meta = {'opsi': ch['opsi'], 'nama': csc.get('nama') or ch.get('nama'),
                         'validator': ch.get('validator')}
    if sol is not None:
        sol['deal'] = C['deal']
    sites = [{'site': s, 'opening': st['data']['opening_stock'][s]['volume_mt'],
              'cv_open': st['data']['opening_stock'][s]['cv_gar'],
              'cg': st['data']['coal_getting'][s]['volume_mt'],
              'cv_cg': st['data']['coal_getting'][s]['cv_gar'],
              'available': C['available'][s], 'cv': C['cv_site'][s],
              'jetty': C['jetty_capacity'][s], 'cs_min': C['cs_min'][s], 'cs_max': C['cs_max'][s]}
             for s in C['sites']]
    return {'meta': {'user': st['user'], 'sumber': st['sumber'],
                     'versi': MANIFEST['_meta'].get('versi', '?'), 'run_id': st['run_id'], 'opsi': opsi_meta},
            'sites': sites, 'brands': C['brands'], 'allowance': C['allowance'],
            'cv_min': C['cv_min'], 'cv_max': C['cv_max'], 'price': C['price'],
            'cv_reject': {b: MANIFEST['brand_spec'][b]['cv_min_reject'] for b in C['brands']},
            'deal_default': C['deal'], 'total_capacity': C['total_capacity'],
            'solution': sol, 'alerts': _alert_objs([tuple(a) for a in (st.get('alerts') or [])] + alerts)}

@app.route('/api/monitoring')
def api_monitoring():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    from agents import monitoring
    st = _last_state()
    sol, C, _ = _solve_from(st['data'])
    # Live Operations tidak boleh 0: bila solve dengan Constraint Settings infeasible,
    # fallback ke solve BASELINE dari data valid terakhir agar monitoring tetap berangka.
    if sol is None:
        baseC, _b = constraint.build(MANIFEST, st['data'])
        bsol, _b2 = optimizer.solve(baseC)
        if bsol is not None:
            sol, C = bsol, baseC
    sites_state = []
    for s in C['sites']:
        ship = (sol or {}).get('site_ship', {}).get(s, 0) if sol else 0
        jetty = C['jetty_capacity'][s]
        sites_state.append({
            'site': s, 'available': C['available'][s], 'jetty': jetty,
            'ship': ship, 'util': (ship / jetty) if jetty else None,
            'closing': (sol or {}).get('closing', {}).get(s) if sol else None,
            'cv': C['cv_site'][s],
        })
    alloc = {s: {b: (sol or {}).get('x', {}).get(s, {}).get(b, 0) for b in C['brands']} for s in C['sites']} if sol else {}
    brand_total = (sol or {}).get('brand_total', {}) if sol else {}
    snap = monitoring.snapshot(sites_state, alloc, brand_total)
    snap['meta'] = {'user': st['user'], 'run_id': st['run_id'], 'sumber': st['sumber']}
    return snap

@app.route('/api/insights')
def api_insights():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    return db.insights()

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    st = _last_state()
    ov = (request.get_json(silent=True) or {}).get('deal', {})
    sol, C, alerts = _solve_from(st['data'], deal_override=ov)
    if sol is None:
        return {'status': 'Infeasible', 'alerts': _alert_objs(alerts)}
    sol['deal'] = C['deal']
    return {'status': 'Optimal', 'solution': sol, 'alerts': _alert_objs(alerts)}

@app.route('/review')
def review_page():
    if not logged_in(): return redirect('/')
    p = DATA_DIR / 'output/dashboard.html'
    if p.exists(): return p.read_text()
    return run_pipeline({})

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

if __name__ == '__main__':
    # dev lokal: `python app.py`. Produksi Railway pakai gunicorn (lihat Procfile).
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
