"""Agent 4 — Dashboard Synthesizer.
Output solver -> HTML review dashboard (dark theme, gaya Control Tower).
Top-fold sesuai kesepakatan: fulfillment deal, CV deviation vs reject, revenue, closing vs band.
"""
SEV = {'CRITICAL': ('#ef5350', 'CRITICAL'), 'WARNING': ('#f6b53c', 'WARNING'), 'INFO': ('#4aa3df', 'INFO')}
CSS = """
:root{--bg:#0b1012;--panel:#131c1f;--line:#23312f;--ink:#e8efee;--mut:#8aa09c;
--g:#34c759;--a:#f6b53c;--r:#ef5350;--b:#4aa3df}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font:14px 'IBM Plex Sans',sans-serif;margin:0;padding:26px}
h1{font-size:20px;margin:0 0 2px}h2{font-size:15px;border-bottom:1px solid var(--line);padding-bottom:6px;margin:28px 0 12px}
.sub{color:var(--mut);font:11px 'IBM Plex Mono',monospace;margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--g);border-radius:10px;padding:12px 14px}
.kpi.r{border-left-color:var(--r)}.kpi.a{border-left-color:var(--a)}.kpi.b{border-left-color:var(--b)}
.kpi .l{font:10px 'IBM Plex Mono',monospace;color:var(--mut);text-transform:uppercase;letter-spacing:.07em}
.kpi .v{font:700 24px 'IBM Plex Mono',monospace;margin-top:4px}.kpi .d{font:11px 'IBM Plex Mono',monospace;color:var(--mut);margin-top:3px}
table{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:'IBM Plex Mono',monospace}
th{font-size:10px;color:var(--mut);text-transform:uppercase}th:first-child,td:first-child{text-align:left;font-family:inherit}
.al{display:flex;gap:10px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 12px;margin-bottom:7px}
.al .tag{font:700 9px 'IBM Plex Mono',monospace;padding:2px 7px;border-radius:4px;color:#0b1012;flex:none;margin-top:2px}
.bar{height:9px;background:#0e1517;border-radius:5px;overflow:hidden;min-width:80px}.bar i{display:block;height:100%}
.pos{color:var(--g)}.neg{color:var(--r)}.amb{color:var(--a)}.mut{color:var(--mut)}
.badge{font:700 10px 'IBM Plex Mono',monospace;padding:3px 9px;border-radius:20px}
"""

def _fmt(v): return f'{v:,.0f}'


def _n_unhealthy(C, sol, tol=1.0):
    """Jumlah site yang closing stock-nya di LUAR rentang sehat 20–80% band [cs_min,cs_max].
    Dipakai kolom perbandingan Opsi C (Normalisasi Stok): 0 = semua site sehat."""
    n = 0
    for s in C['sites']:
        lo, hi = C['cs_min'][s], C['cs_max'][s]
        rng = hi - lo
        c = sol['closing'][s]
        if c < lo + 0.20 * rng - tol or c > lo + 0.80 * rng + tol:
            n += 1
    return n

def render(sol, C, alerts, meta=''):
    a_html = ''.join(
        f'<div class="al"><span class="tag" style="background:{SEV[s][0]}">{SEV[s][1]}</span>'
        f'<div><b style="color:{SEV[s][0]};font-size:11px">{cat}</b><div>{msg}</div></div></div>'
        for s, cat, msg in alerts) or '<div class="mut">Tidak ada alert.</div>'

    if sol is None:
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<h1>CoalBlend AI — MVP 1 <span class="badge" style="background:rgba(239,83,80,.2);color:#ffb3b1">INFEASIBLE</span></h1>
<div class="sub">{meta}</div><h2>Diagnosis & Alert</h2>{a_html}
<p class="mut">Optimisasi tidak menemukan solusi. Tinjau relaksasi minimum di atas bersama tim Marketing/Mineplan, perbaiki parameter, lalu jalankan ulang.</p>
</body></html>"""

    deal_ok = all(sol['brand_total'][b] >= C['deal'][b] - 1 for b in C['brands'])
    n_reject = sum(1 for b in C['brands'] if abs(sol['brand_cv'][b] - C['cv_min'][b]) < 1)

    def brand_rows():
        r = ''
        for b in C['brands']:
            cv, mn, mx = sol['brand_cv'][b], C['cv_min'][b], C['cv_max'][b]
            pos = max(0, min(1, (cv - mn) / max(mx - mn, 1)))
            col = 'var(--r)' if pos < .05 else ('var(--a)' if pos < .3 else 'var(--g)')
            r += (f'<tr><td>{b}</td><td>{_fmt(C["deal"][b])}</td><td>{_fmt(sol["optimize"][b])}</td>'
                  f'<td><b>{_fmt(sol["brand_total"][b])}</b></td><td>{cv:,.0f}</td>'
                  f'<td><div class="bar"><i style="width:{pos*100:.0f}%;background:{col}"></i></div></td>'
                  f'<td class="{"neg" if pos<.05 else "mut"}">{cv-mx:+,.0f} vs typical</td>'
                  f'<td>{_fmt(sol["brand_revenue"][b])}</td></tr>')
        return r

    def matrix_rows():
        hdr = '<th>Site</th>' + ''.join(f'<th>{b}</th>' for b in C['brands']) + '<th>Total</th><th>Closing</th><th>Band</th>'
        r = ''
        for s in C['sites']:
            cells = ''.join(f'<td>{_fmt(sol["x"][s][b]) if sol["x"][s][b] > .5 else "<span class=mut>—</span>"}</td>' for b in C['brands'])
            cl, mn, mx = sol['closing'][s], C['cs_min'][s], C['cs_max'][s]
            edge = ' (MIN)' if abs(cl - mn) < 1 else (' (MAX)' if abs(cl - mx) < 1 else '')
            r += (f'<tr><td>{s}</td>{cells}<td><b>{_fmt(sol["site_ship"][s])}</b></td>'
                  f'<td class="{"amb" if edge else ""}">{_fmt(cl)}{edge}</td><td class="mut">{_fmt(mn)}–{_fmt(mx)}</td></tr>')
        return hdr, r

    hdr, mrows = matrix_rows()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<h1>CoalBlend AI — MVP 1 · Review Blending <span class="badge" style="background:rgba(52,199,89,.18);color:#7fe39b">OPTIMAL</span></h1>
<div class="sub">{meta} · Model 1–9 (C4 total-only · C6 tanpa toleransi) · Solver CBC</div>

<div class="kpis">
 <div class="kpi"><div class="l">Total Revenue (Objective)</div><div class="v">{sol['revenue']:,.0f}</div><div class="d">basis harga dummy MVP 1</div></div>
 <div class="kpi b"><div class="l">Total Shipment</div><div class="v">{_fmt(sol['total_ship'])}</div><div class="d">/ kapasitas {_fmt(C['total_capacity'])}</div></div>
 <div class="kpi {'a' if not deal_ok else ''}"><div class="l">Fulfillment Deal</div><div class="v">{'100%' if deal_ok else 'GAP'}</div><div class="d">Model 1 {'terpenuhi semua brand' if deal_ok else 'ADA BRAND KURANG'}</div></div>
 <div class="kpi {'r' if n_reject else 'a'}"><div class="l">Brand di Batas Reject</div><div class="v">{n_reject}</div><div class="d">CV blend tepat di rejection limit</div></div>
</div>

<h2>Alert & Review Flag ({len(alerts)})</h2>{a_html}

<h2>Rekomendasi per Brand — Deal · Optimize · Kualitas</h2>
<table><tr><th>Brand</th><th>Deal (min)</th><th>Optimize</th><th>Total</th><th>CV Blend</th><th>Posisi Band</th><th>Δ Typical</th><th>Revenue</th></tr>{brand_rows()}</table>

<h2>Matriks Blending Site × Brand (MT)</h2>
<div style="overflow-x:auto"><table><tr>{hdr}</tr>{mrows}</table></div>
<p class="mut" style="font:11px 'IBM Plex Mono',monospace">Solusi LP dapat memiliki alternate optima; validasi pada objective & binding constraints (lihat KB-13).
Reviewer: setujui / tolak dengan catatan sebelum publikasi ke Marketing.</p>
</body></html>"""


# ---------- Human-in-the-Loop: halaman review multi-opsi ----------
def render_review(scenarios, C, pre_alerts, calib=None, meta=''):
    """Perbandingan opsi + form keputusan validator (approve/reject + catatan) per opsi."""
    pref = ''
    if calib and calib.get('total_keputusan'):
        pref = (f"<div class='al'><span class='tag' style='background:#4aa3df'>KALIBRASI</span>"
                f"<div>Histori validator: skenario <b>{calib['skenario_favorit']}</b> paling sering disetujui "
                f"({calib['approval'].get(calib['skenario_favorit'],0)}/{calib['total_keputusan']} keputusan). "
                f"AI menempatkannya sebagai kandidat utama.</div></div>")

    comp = ('<table><tr><th>Opsi</th><th>Skenario</th><th>Revenue</th><th>&Delta; vs Baseline</th>'
            '<th>Total Ship</th><th>Brand di Reject</th><th>Stok di luar 20–80%</th><th>Status</th></tr>')
    cards = ''
    for sc in scenarios:
        if sc['sol'] is None:
            comp += (f"<tr><td><b>{sc['id']}</b></td><td>{sc['nama']}</td><td class='mut'>—</td><td class='mut'>—</td>"
                     f"<td class='mut'>—</td><td class='mut'>—</td><td class='mut'>—</td><td class='neg'>INFEASIBLE</td></tr>")
            diag = ''.join(f"<div class='al'><span class='tag' style='background:#ef5350'>DIAG</span><div>{m}</div></div>"
                           for _,_,m in sc['alerts'])
            cards += f"<h2>Opsi {sc['id']} — {sc['nama']} (INFEASIBLE)</h2><p class='mut'>{sc['desc']}</p>{diag}"
            continue
        s = sc['sol']
        comp += (f"<tr><td><b>{sc['id']}</b></td><td>{sc['nama']}</td><td><b>{s['revenue']:,.0f}</b></td>"
                 f"<td class='{'pos' if sc['delta']>=0 else 'neg'}'>{sc['delta']:+,.0f}</td>"
                 f"<td>{_fmt(s['total_ship'])}</td><td class='{'neg' if sc['n_reject'] else 'pos'}'>{sc['n_reject']}</td>"
                 f"<td class='{'pos' if _n_unhealthy(C, s) == 0 else 'neg'}'>{_n_unhealthy(C, s)}</td>"
                 f"<td class='pos'>Optimal</td></tr>")
        brand = ''.join(f"<tr><td>{b}</td><td>{_fmt(C['deal'][b])}</td><td>{_fmt(s['optimize'][b])}</td>"
                        f"<td><b>{_fmt(s['brand_total'][b])}</b></td><td>{s['brand_cv'][b]:,.0f}</td>"
                        f"<td>{s['brand_cv'][b]-C['cv_min'][b]:+,.0f}</td><td>{_fmt(s['brand_revenue'][b])}</td></tr>"
                        for b in C['brands'])
        cards += f"""<h2>Opsi {sc['id']} — {sc['nama']} · Revenue {s['revenue']:,.0f}</h2>
<p class='mut'>{sc['desc']}</p>
<table><tr><th>Brand</th><th>Deal</th><th>Optimize</th><th>Total</th><th>CV Blend</th><th>Jarak ke Reject</th><th>Revenue</th></tr>{brand}</table>
<form method='post' action='/decide' style='margin:10px 0 26px;display:flex;gap:8px;align-items:center;flex-wrap:wrap'>
<input type='hidden' name='opsi' value='{sc['id']}'>
<input name='catatan' placeholder='Catatan validator (alasan/kalibrasi)...' style='flex:1;min-width:240px;padding:8px;border-radius:8px;border:1px solid #23312f;background:#0e1517;color:#e8efee'>
<button name='aksi' value='approve' style='background:#1f9e45;border:none;color:#fff;font-weight:700;padding:9px 16px;border-radius:8px;cursor:pointer'>Setujui Opsi {sc['id']}</button>
<button name='aksi' value='reject' style='background:#31201f;border:1px solid #ef5350;color:#ffb3b1;font-weight:700;padding:9px 16px;border-radius:8px;cursor:pointer'>Tolak</button>
</form>"""
    comp += '</table>'

    pa = ''.join(f"<div class='al'><span class='tag' style='background:{SEV[sv][0]}'>{sv}</span><div><b style='font-size:11px'>{c}</b><div>{m}</div></div></div>"
                 for sv, c, m in pre_alerts)
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap' rel='stylesheet'>
<style>{CSS}</style></head><body>
<h1>CoalBlend AI — Review Blending <span class='badge' style='background:rgba(246,181,60,.18);color:#f6cf86'>MENUNGGU VALIDASI MANUSIA</span></h1>
<div class='sub'>{meta} · AI mengusulkan {len(scenarios)} opsi — keputusan final di tangan validator; setiap keputusan menjadi data kalibrasi.</div>
{pref}
<div style='margin:4px 0 14px'><a href='/dashboard' style='color:#4aa3df;font:600 12px IBM Plex Sans,sans-serif;text-decoration:none'>📊 Buka Dashboard Analitik (coal balance · available · matriks · revenue · simulasi slider) →</a></div><h2>Perbandingan Opsi Blending</h2>{comp}
<h2 style='border:none;margin-top:6px'></h2>{pa}
{cards}
{override_panel(C)}
<p class='mut' style="font:11px 'IBM Plex Mono',monospace">Approve menerbitkan Report Final &amp; Rekomendasi Eksekusi;
Reject + catatan = sinyal kalibrasi; Manual Override = tacit knowledge validator masuk sebagai parameter (AI re-run dalam detik, tercatat di audit trail).</p>
</body></html>"""


def override_panel(C):
    inp = "style='width:110px;padding:6px;border-radius:7px;border:1px solid #23312f;background:#0e1517;color:#e8efee;font-family:monospace'"
    site_rows = ''.join(
        f"<tr><td>{s}</td><td><input name='cs_min__{s}' value='{C['cs_min'][s]:.0f}' {inp}></td>"
        f"<td><input name='cs_max__{s}' value='{C['cs_max'][s]:.0f}' {inp}></td></tr>" for s in C['sites'])
    deal_rows = ''.join(
        f"<tr><td>{b}</td><td><input name='deal__{b}' value='{C['deal'][b]:.0f}' {inp}></td></tr>" for b in C['brands'])
    return f"""<h2>Manual Override — Titik Veto Validator</h2>
<p class='mut'>Intuisi yang belum ditangkap AI (misal: "simpan stok lebih untuk buyer bulan depan") diinput di sini.
AI kalkulasi ulang 3 opsi dalam hitungan detik; alasan override wajib diisi untuk audit &amp; kalibrasi.</p>
<form method='post' action='/override'>
<details><summary style='cursor:pointer;color:#8aa09c;font-family:monospace;font-size:12px'>Ubah band closing stock per site (MT)</summary>
<table style='max-width:520px;margin-top:8px'><tr><th>Site</th><th>Closing Min</th><th>Closing Max</th></tr>{site_rows}</table></details>
<details style='margin-top:8px'><summary style='cursor:pointer;color:#8aa09c;font-family:monospace;font-size:12px'>Ubah Shipment Schedule Deal per brand (MT)</summary>
<table style='max-width:420px;margin-top:8px'><tr><th>Brand</th><th>Deal (min)</th></tr>{deal_rows}</table></details>
<div style='display:flex;gap:8px;margin-top:12px;flex-wrap:wrap'>
<input name='alasan' required placeholder='Alasan override (wajib — masuk audit trail &amp; kalibrasi)...' style='flex:1;min-width:260px;padding:9px;border-radius:8px;border:1px solid #f6b53c;background:#0e1517;color:#e8efee'>
<button style='background:#8a6d1f;border:none;color:#fff;font-weight:700;padding:10px 16px;border-radius:8px;cursor:pointer'>Override &amp; Re-run AI</button>
</div></form>"""


def render_report(sc, C, run_id, validator, catatan):
    """Report Final + Rekomendasi Eksekusi (diterbitkan setelah Approve)."""
    s = sc['sol']
    hdr = '<th>Site</th>' + ''.join(f'<th>{b}</th>' for b in C['brands']) + '<th>Total</th>'
    rows = ''.join('<tr><td>' + st + '</td>' + ''.join(
        f'<td>{_fmt(s["x"][st][b]) if s["x"][st][b] > .5 else "—"}</td>' for b in C['brands']) +
        f'<td><b>{_fmt(s["site_ship"][st])}</b></td></tr>' for st in C['sites'])
    # Shipment Priority: kargo deal lebih dulu; brand rawan (CV dekat reject / optimize besar) diprioritaskan monitoringnya
    prio = sorted(C['brands'], key=lambda b: (-(C['deal'][b] > 0), s['brand_cv'][b] - C['cv_min'][b]))
    prio_rows = ''.join(
        f"<tr><td>{i+1}</td><td>{b}</td><td>{_fmt(C['deal'][b])}</td><td>{_fmt(s['optimize'][b])}</td>"
        f"<td>{s['brand_cv'][b]:,.0f}</td><td class='{'neg' if s['brand_cv'][b]-C['cv_min'][b] < 1 else 'mut'}'>"
        f"{s['brand_cv'][b]-C['cv_min'][b]:+,.0f} vs reject</td></tr>" for i, b in enumerate(prio))
    al = ''.join(f"<div class='al'><span class='tag' style='background:{SEV[sv][0]}'>{sv}</span><div><b style='font-size:11px'>{cat}</b><div>{m}</div></div></div>"
                 for sv, cat, m in sc['alerts']) or "<div class='mut'>Tidak ada alert — seluruh target tercapai.</div>"
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap' rel='stylesheet'>
<style>{CSS}</style></head><body>
<h1>REPORT FINAL — Rekomendasi Eksekusi Blending <span class='badge' style='background:rgba(52,199,89,.18);color:#7fe39b'>APPROVED</span></h1>
<div class='sub'>run {run_id} · Opsi {sc['id']} ({sc['nama']}) · Revenue {s['revenue']:,.0f} · disetujui: {validator} · catatan: {catatan or '—'}</div>
<h2>1 · Blending Recipe (tonase site × brand, MT)</h2>
<div style='overflow-x:auto'><table><tr>{hdr}</tr>{rows}</table></div>
<h2>2 · Shipment Priority (kargo deal dahulu; CV rawan = monitoring ketat)</h2>
<table><tr><th>#</th><th>Brand</th><th>Deal</th><th>Optimize</th><th>CV Blend</th><th>Margin Kualitas</th></tr>{prio_rows}</table>
<h2>3 · Alert Status</h2>{al}
<p class='mut' style="font:11px 'IBM Plex Mono',monospace">Dokumen ini adalah output Execution Layer — hasil AI yang telah melewati Validation Gateway (human-in-the-loop). Lineage penuh di output/trace.jsonl.</p>
</body></html>"""
