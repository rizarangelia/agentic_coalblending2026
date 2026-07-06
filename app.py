"""CoalBlend AI MVP 1 — Web App (login + input data + run pipeline + dashboard + alerts).
Orkestrasi 4 agent: Ingestion -> Constraint -> Optimizer -> Synthesizer.
Login MVP: kredensial demo di config/users.json (sha256). Ganti dengan SSO korporat saat produksi.
"""
import json, hashlib, pathlib
import hashlib as _h
from flask import Flask, request, session, redirect, render_template_string
from agents import ingestion, constraint, optimizer, synthesizer, orchestrator
from agents.dashboard import DASH_HTML

ROOT = pathlib.Path(__file__).parent
MANIFEST = json.loads((ROOT / 'config/constraint_manifest.json').read_text())
USERS = json.loads((ROOT / 'config/users.json').read_text())

app = Flask(__name__)
app.secret_key = 'coalblend-mvp1-demo'  # produksi: env var

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{background:#0b1012;color:#e8efee;font:14px 'IBM Plex Sans',sans-serif;display:flex;justify-content:center;padding-top:60px}
.card{background:#131c1f;border:1px solid #23312f;border-radius:14px;padding:28px;width:430px}
h1{font-size:18px;margin:0 0 4px}.sub{color:#8aa09c;font-size:11px;font-family:monospace;margin-bottom:18px}
input,button{width:100%;padding:9px 11px;margin:5px 0;border-radius:8px;border:1px solid #23312f;background:#0e1517;color:#e8efee;font-size:13px}
button{background:#1f9e45;border:none;font-weight:700;cursor:pointer;margin-top:12px}
label{font-size:11px;color:#8aa09c;font-family:monospace;text-transform:uppercase;letter-spacing:.05em}
.err{color:#ef5350;font-size:12px}.ok{color:#34c759;font-size:12px}
a{color:#4aa3df}</style></head><body><div class="card">{{ body|safe }}</div></body></html>"""

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
    body = f"""<h1>CoalBlend AI · MVP 1</h1><div class="sub">AI Coal Blending Optimizer — Login</div>
    <form method="post"><label>Username</label><input name="u" autofocus>
    <label>Password</label><input name="p" type="password">{err}<button>Masuk</button></form>
    <div class="sub" style="margin-top:14px">Demo: planner / coalblend2026</div>"""
    return render_template_string(PAGE, body=body)

@app.route('/input', methods=['GET', 'POST'])
def input_data():
    if not logged_in(): return redirect('/')
    if request.method == 'POST':
        files = {}
        for key in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas'):
            f = request.files.get(key)
            if f and f.filename:
                files[key] = (f.read(), f.filename)
        return run_pipeline(files)
    rows = ''.join(f'<label>{k.replace("_"," ").title()} (.csv / .xlsx)</label><input type="file" name="{k}">'
                   for k in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas'))
    body = f"""<h1>Input Data Bulanan</h1><div class="sub">User: {session['user']} · cadence KB-12 (tgl 1 &amp; tgl 3–5) · <a href="/logout">logout</a></div>
    <form method="post" enctype="multipart/form-data">{rows}<button>Jalankan Optimisasi</button></form>
    <div class="sub" style="margin-top:12px">Kosongkan semua untuk memakai <b>fixtures simulasi</b> (uji baseline 24.225.858,52).</div>"""
    return render_template_string(PAGE, body=body)

def _rounds():
    p = ROOT / 'output/rounds.json'
    return json.loads(p.read_text()) if p.exists() else []

def _rounds_save(r):
    (ROOT / 'output/rounds.json').write_text(json.dumps(r, indent=1, ensure_ascii=False))

def _history_html():
    rows = ''
    for r in _rounds():
        opsi = ' · '.join(f"{k}: {v['revenue']:,.0f}" if v.get('revenue') else f"{k}: INF" for k, v in r['opsi'].items())
        ch = r.get('chosen')
        pil = (f"<b style='color:#7fe39b'>Opsi {ch['opsi']} ✓</b> — {ch.get('catatan') or 'tanpa catatan'}"
               if ch and ch['aksi'] == 'approve' else
               (f"<b style='color:#ffb3b1'>Ditolak</b> — {ch.get('catatan','')}" if ch else
                "<span style='color:#f6cf86'>menunggu validasi</span>"))
        rows += (f"<tr><td>Ronde {r['no']}</td><td style='text-align:left'>{r['sumber']}</td>"
                 f"<td style='text-align:left;font-size:11px'>{opsi}</td>"
                 f"<td style='text-align:left'>{pil}</td><td>{r['ts'][:16].replace('T',' ')}</td></tr>")
    if not rows: return ''
    return ("<h2>Riwayat Ronde &amp; Keputusan</h2>"
            "<table><tr><th>Ronde</th><th style='text-align:left'>Sumber Demand</th>"
            "<th style='text-align:left'>Opsi &amp; Revenue</th><th style='text-align:left'>Keputusan Validator</th>"
            "<th>Waktu</th></tr>" + rows + "</table>"
            "<p class='mut' style='font:11px monospace'>Setiap demand baru = ronde blending baru — "
            "validator menilai feasibilitas jual, bukan hanya revenue tertinggi. Arsip lengkap: output/rounds.json</p>")

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
    p = ROOT / 'config/calibration.json'
    if not p.exists(): return {'approval': {}, 'reject': {}, 'total_keputusan': 0, 'skenario_favorit': '-', 'catatan': []}
    return json.loads(p.read_text())

def _save_calib(c):
    if c['approval']:
        c['skenario_favorit'] = max(c['approval'], key=c['approval'].get)
    (ROOT / 'config/calibration.json').write_text(json.dumps(c, indent=1, ensure_ascii=False))

def run_pipeline(files, sumber_demand=None):
    # fallback fixtures untuk demo/validasi
    use_fixtures = not files
    if not files:
        fx = ROOT / 'fixtures'
        files = {k: ((fx / f'{k}_simulasi.csv').read_bytes(), f'{k}_simulasi.csv')
                 for k in ('opening_stock', 'coal_getting', 'demand_deal', 'plan_kapasitas')}
    st = orchestrator.run(files, MANIFEST, session.get('user', 'tester'),
                          ingestion, constraint, optimizer)          # state graph + lineage + trace
    session['run_id'] = st['run_id']
    if st['node_terakhir'] == 'ALERT':
        return synthesizer.render(None, st.get('C'), st['alerts'],
                                  meta=f"run {st['run_id']} · pipeline berhenti (lihat output/trace.jsonl)")
    C, scenarios = st['C'], st['scenarios']
    app.config['LAST'] = {'C': C, 'scenarios': scenarios, 'run_id': st['run_id'],
                          'data': st.get('data'), 'alerts': st['alerts']}
    a1 = a2 = []  # alerts pre-solve sudah di st['alerts']
    # persist state utk /dashboard, /review (revisit) & /api
    (ROOT / 'output/last_state.json').write_text(json.dumps({
        'user': session.get('user', 'tester'), 'run_id': st['run_id'],
        'sumber': 'fixtures simulasi' if use_fixtures else f'{len(files)} file input',
        'data': st.get('data'), 'alerts': st['alerts'],
    }, ensure_ascii=False))
    # simpan run untuk endpoint keputusan (tanpa objek sol penuh: cukup ringkasan auditabel)
    (ROOT / 'output/last_run.json').write_text(json.dumps(
        {sc['id']: {'nama': sc['nama'], 'revenue': sc['revenue'],
                    'brand_total': sc['sol']['brand_total'] if sc['sol'] else None,
                    'closing': sc['sol']['closing'] if sc['sol'] else None}
         for sc in scenarios}, indent=1, ensure_ascii=False))
    # catat RONDE baru (histori opsi)
    import datetime as _dt
    rounds = _rounds()
    rounds.append({'no': len(rounds) + 1, 'ts': _dt.datetime.now().isoformat(timespec='seconds'),
                   'user': session.get('user', 'tester'), 'run_id': st['run_id'],
                   'sumber': sumber_demand or ('fixtures simulasi' if use_fixtures else f'{len(files)} file input'),
                   'opsi': {sc['id']: {'nama': sc['nama'], 'revenue': sc['revenue']} for sc in scenarios},
                   'chosen': None})
    _rounds_save(rounds)
    html = synthesizer.render_review(scenarios, C, st['alerts'], calib=_load_calib(),   # Agent 4 (review HITL)
                                     meta=f"RONDE {len(_rounds())} · run {st['run_id']} · validator: {session.get('user','tester')} · lineage: {len(st['lineage']['files'])} file (sha256 tercatat)")
    html = html.replace('</body>', f"<div style='max-width:1180px'>{_history_html()}</div></body>")
    (ROOT / 'output/dashboard.html').write_text(html)
    return html

@app.route('/decide', methods=['POST'])
def decide():
    if not logged_in(): return redirect('/')
    import datetime
    opsi, aksi = request.form.get('opsi'), request.form.get('aksi')
    catatan = request.form.get('catatan', '').strip()
    run = json.loads((ROOT / 'output/last_run.json').read_text()) if (ROOT / 'output/last_run.json').exists() else {}
    rec = {'waktu': datetime.datetime.now().isoformat(timespec='seconds'), 'validator': session['user'],
           'opsi': opsi, 'aksi': aksi, 'catatan': catatan, 'revenue': (run.get(opsi) or {}).get('revenue')}
    with open(ROOT / 'output/decisions.jsonl', 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    c = _load_calib()
    key = 'approval' if aksi == 'approve' else 'reject'
    c[key][opsi] = c[key].get(opsi, 0) + 1
    c['total_keputusan'] += 1
    if catatan: c['catatan'].append({'opsi': opsi, 'aksi': aksi, 'catatan': catatan})
    _save_calib(c)
    orchestrator.decide(session.get('run_id', '?'), session['user'], opsi, aksi, catatan, rec['revenue'])
    rounds = _rounds()
    if rounds and rounds[-1]['chosen'] is None:
        rounds[-1]['chosen'] = {'opsi': opsi, 'aksi': aksi, 'catatan': catatan,
                                'revenue': rec['revenue'], 'validator': session['user'], 'ts': rec['waktu']}
        _rounds_save(rounds)
    report_link = ''
    L = app.config.get('LAST')
    if aksi == 'approve' and L:
        sc = next((s for s in L['scenarios'] if s['id'] == opsi and s['sol']), None)
        if sc:
            rp = ROOT / f"output/report_final_{session.get('run_id','x')}_{opsi}.html"
            rp.write_text(synthesizer.render_report(sc, L['C'], session.get('run_id','?'), session['user'], catatan))
            report_link = f'<p class="ok">Report Final &amp; Rekomendasi Eksekusi diterbitkan: {rp.name}</p>'
    verdict = ('DISETUJUI — blending plan siap dipublikasikan ke Marketing.' if aksi == 'approve'
               else 'DITOLAK — catatan Anda tercatat sebagai sinyal kalibrasi.')
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
    C, a2 = constraint.build(MANIFEST, L['data'], overrides=ov)
    if any(s == 'CRITICAL' for s, _, _ in a2):
        return synthesizer.render(None, C, a2, meta=f"override oleh {session['user']} · pre-solve gagal")
    scenarios = optimizer.solve_scenarios(C)
    app.config['LAST'].update({'C': C, 'scenarios': scenarios})
    ov_alert = [('INFO', 'OVERRIDE', f"Re-run dengan override validator ({session['user']}): " +
                 ('; '.join(changed) if changed else 'tanpa perubahan angka') + f" · alasan: {alasan}")]
    return synthesizer.render_review(scenarios, C, ov_alert + a2, calib=_load_calib(),
                                     meta=f"run {session.get('run_id','?')} · MANUAL OVERRIDE aktif · re-run < 1 detik")

def _last_state():
    p = ROOT / 'output/last_state.json'
    if p.exists():
        return json.loads(p.read_text())
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
    C, a2 = constraint.build(MANIFEST, data)
    if any(s == 'CRITICAL' for s, _, _ in a2):
        return None, C, a2
    sol, a3 = optimizer.solve(C)
    return sol, C, a2 + a3

def _alert_objs(alerts):
    ackp = ROOT / 'output/alerts_ack.json'
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
    ackp = ROOT / 'output/alerts_ack.json'
    acked = set(json.loads(ackp.read_text())) if ackp.exists() else set()
    if aid: acked.add(aid)
    ackp.write_text(json.dumps(sorted(acked)))
    return {'ok': True, 'acked': len(acked)}

@app.route('/dashboard')
def dashboard():
    if not logged_in(): return redirect('/')
    return DASH_HTML

@app.route('/api/state')
def api_state():
    if not logged_in(): return {'error': 'unauthorized'}, 401
    st = _last_state()
    sol, C, alerts = _solve_from(st['data'])
    sol['deal'] = C['deal']
    sites = [{'site': s, 'opening': st['data']['opening_stock'][s]['volume_mt'],
              'cv_open': st['data']['opening_stock'][s]['cv_gar'],
              'cg': st['data']['coal_getting'][s]['volume_mt'],
              'cv_cg': st['data']['coal_getting'][s]['cv_gar'],
              'available': C['available'][s], 'cv': C['cv_site'][s],
              'jetty': C['jetty_capacity'][s], 'cs_min': C['cs_min'][s], 'cs_max': C['cs_max'][s]}
             for s in C['sites']]
    return {'meta': {'user': st['user'], 'sumber': st['sumber'],
                     'versi': MANIFEST['_meta'].get('versi', '?'), 'run_id': st['run_id']},
            'sites': sites, 'brands': C['brands'], 'allowance': C['allowance'],
            'cv_min': C['cv_min'], 'cv_max': C['cv_max'], 'price': C['price'],
            'deal_default': C['deal'], 'total_capacity': C['total_capacity'],
            'solution': sol, 'alerts': _alert_objs([tuple(a) for a in (st.get('alerts') or [])] + alerts)}

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
    p = ROOT / 'output/dashboard.html'
    if p.exists(): return p.read_text()
    return run_pipeline({})

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
