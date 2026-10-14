"""Halaman menu Constraints — form editable min/max Capacity, CV, TS, Ash, Na2O per brand
+ assay per Site. Disimpan ke config/constraint_settings.json (agents/settings.py) lalu
dipakai constraint.build/optimizer. Tema clay-warm + toggle terang/gelap (selaras dashboard).
"""


def _n(v):
    return '' if v is None else (f'{v:g}' if isinstance(v, float) else v)


def render(settings, manifest, saved=False, db_ok=None):
    brands, sites = manifest['brands'], manifest['sites']
    spec = manifest['brand_spec']
    cv, ts, ash, na2o = settings['cv'], settings['ts'], settings['ash'], settings['na2o']
    assay = settings['site_assay']; cap = settings['capacity']

    def num(name, val, step='any', w='72'):
        return f'<input name="{name}" type="number" step="{step}" value="{_n(val)}" style="width:{w}px">'

    # baris brand: CV min/max + reject ref + TS/Ash/Na2O min/max
    brand_rows = ''
    for b in brands:
        c = cv.get(b, {}); rej = spec[b]['cv_min_reject']
        brand_rows += (
            f'<tr><td style="text-align:left">{b}</td>'
            f'<td class=mut>{rej}</td>'
            f'<td>{num(f"cv_min_{b}", c.get("min"))}</td>'
            f'<td>{num(f"cv_max_{b}", c.get("max"))}</td>'
            f'<td>{num(f"ts_min_{b}", (ts.get(b) or {}).get("min"))}</td>'
            f'<td>{num(f"ts_max_{b}", (ts.get(b) or {}).get("max"))}</td>'
            f'<td>{num(f"ash_min_{b}", (ash.get(b) or {}).get("min"))}</td>'
            f'<td>{num(f"ash_max_{b}", (ash.get(b) or {}).get("max"))}</td>'
            f'<td>{num(f"na2o_min_{b}", (na2o.get(b) or {}).get("min"))}</td>'
            f'<td>{num(f"na2o_max_{b}", (na2o.get(b) or {}).get("max"))}</td></tr>')

    site_rows = ''
    for s in sites:
        a = assay.get(s, {})
        site_rows += (f'<tr><td style="text-align:left">{s}</td>'
                      f'<td>{num(f"assay_ts_{s}", a.get("ts"))}</td>'
                      f'<td>{num(f"assay_ash_{s}", a.get("ash"))}</td>'
                      f'<td>{num(f"assay_na2o_{s}", a.get("na2o"))}</td></tr>')

    jetty_rows = ''
    for s in sites:
        pj = (cap.get('per_jetty') or {}).get(s, {})
        jetty_rows += (f'<tr><td style="text-align:left">{s}</td>'
                       f'<td>{num(f"jetty_min_{s}", pj.get("min"))}</td>'
                       f'<td>{num(f"jetty_max_{s}", pj.get("max"), w="90")}</td></tr>')

    dbmsg = ('' if db_ok is None else
             (' · <b>tercatat di Postgres</b> (tabel coalblend_constraints)' if db_ok else
              ' · <span style="color:var(--r)">DB belum tersambung — tersimpan lokal saja (set DATABASE_URL)</span>'))
    ok = (f'<div class="okbox" id="okmsg">✓ Constraint tersimpan &amp; langsung dipakai optimizer{dbmsg}. '
          'Jalankan ulang blending untuk melihat hasilnya.</div>' if saved else '')
    chk = 'checked' if settings.get('enabled') else ''

    return f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>beraucoal Cortex — Constraints</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800;900&family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#1a1a19;--p:#20201f;--p2:#262523;--l:#37342f;--ink:#f0efec;--m:#c3c2b7;--g:#c6613f;--b:#6b9bd1;--r:#ff6159;--ok:#7d9b76}}
:root[data-theme="light"]{{--bg:#f0efec;--p:#fff;--p2:#f5f4f1;--l:#dcdad2;--ink:#20201f;--m:#6f6b62;--g:#c6613f;--b:#3f6ea5;--r:#d6453c;--ok:#5f7a54}}
html{{background:var(--bg)}}*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--ink);font:14px 'IBM Plex Sans',sans-serif;padding:22px 26px 80px;max-width:1120px;margin:0 auto}}
.hd{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px}}
h1{{font:800 20px Archivo}}h2{{font:800 14px Archivo;border-bottom:1px solid var(--l);padding-bottom:6px;margin:22px 0 10px}}
.sub{{font:11px 'IBM Plex Mono';color:var(--m)}}
a{{color:var(--b);text-decoration:none}}
.card{{background:var(--p);border:1px solid var(--l);border-radius:12px;padding:14px;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{padding:5px 7px;border-bottom:1px solid var(--l);text-align:center;font-family:'IBM Plex Mono',monospace;white-space:nowrap}}
th{{font-size:9px;color:var(--m);text-transform:uppercase;letter-spacing:.04em}}
th:first-child,td:first-child{{text-align:left;font-family:'IBM Plex Sans'}}
input[type=number]{{background:var(--p2);border:1px solid var(--l);color:var(--ink);border-radius:6px;padding:4px 6px;font:12px 'IBM Plex Mono';text-align:right}}
input:focus{{outline:none;border-color:var(--g)}}
.tw{{overflow-x:auto}}.mut{{color:var(--m)}}
.btn{{background:var(--g);color:#fff;border:none;font:700 13px 'IBM Plex Sans';padding:9px 18px;border-radius:9px;cursor:pointer}}
.tbtn{{width:38px;height:38px;border-radius:10px;background:var(--p2);border:1px solid var(--l);color:var(--ink);font-size:17px;cursor:pointer}}
.row{{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}}
.fld{{display:flex;flex-direction:column;gap:4px}}.fld label{{font:9px 'IBM Plex Mono';color:var(--m);text-transform:uppercase;letter-spacing:.05em}}
.ok{{color:var(--ok);font:600 12px 'IBM Plex Mono';margin:8px 0}}
.okbox{{background:rgba(125,155,118,.15);border:1px solid var(--ok);border-left:4px solid var(--ok);color:var(--ok);font:700 13px 'IBM Plex Sans';padding:11px 14px;border-radius:0 10px 10px 0;margin:8px 0 14px;animation:okflash 1.6s ease}}
@keyframes okflash{{0%{{background:rgba(125,155,118,.5)}}100%{{background:rgba(125,155,118,.15)}}}}
.btn:disabled{{opacity:.7;cursor:progress}}
.note{{background:var(--p2);border-left:3px solid var(--g);border-radius:0 9px 9px 0;padding:10px 13px;font-size:12px;margin-bottom:10px}}
.reco{{background:rgba(107,155,209,.10);border:1px solid var(--l);border-left:3px solid var(--b);border-radius:0 10px 10px 0;padding:11px 14px;font-size:12.5px;margin-bottom:12px;line-height:1.5}}
.reco b.t{{color:var(--b);font-family:'IBM Plex Mono';font-size:11px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:840px){{.grid2{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="hd"><h1>🎛️ Constraint Settings</h1>
<span class="sub">beraucoal · Cortex</span>
<button class="tbtn" id="tb" onclick="tg()" title="Terang/gelap" style="margin-left:auto">🌙</button>
<a href="/dashboard" style="font-weight:600">← Dashboard</a></div>
<div class="sub" style="margin-bottom:12px">Atur batas <b>min/max</b> Capacity · CV · TS · Ash · Na2O per brand + assay per Site. Disimpan &amp; langsung dipakai optimizer.</div>
{ok}
<form method="post" action="/constraints" id="cform">
<div class="card"><div class="row">
<label style="display:flex;gap:7px;align-items:center;font-size:13px"><input type="checkbox" name="enabled" {chk}> Aktifkan constraint settings</label>
<div class="fld"><label>Quality margin CV (kcal)</label>{num('qmargin', settings.get('quality_margin_cv'))}</div>
<div class="fld"><label>Quality reward (bobot)</label>{num('qreward', settings.get('quality_reward'))}</div>
<button class="btn" type="submit" style="margin-left:auto">💾 Simpan Constraints</button>
</div></div>

<div class="grid2">
<div class="card"><h2 style="margin-top:0">⚓ Capacity Total (MT)</h2>
<div class="row">
<div class="fld"><label>Min</label>{num('cap_total_min', cap.get('total_min'), w='110')}</div>
<div class="fld"><label>Max (kosong = plan)</label>{num('cap_total_max', cap.get('total_max'), w='110')}</div></div>
<h2>Kapasitas per Jetty (MT)</h2>
<div class="tw"><table><tr><th>Jetty</th><th>Min</th><th>Max</th></tr>{jetty_rows}</table></div></div>

<div class="card"><h2 style="margin-top:0">🏭 Assay per Site</h2>
<div class="sub" style="margin-bottom:8px">Nilai kualitas batubara tiap Site (dasar hitung TS/Ash/Na2O blend).</div>
<div class="tw"><table><tr><th>Site</th><th>TS (%)</th><th>Ash (%)</th><th>Na2O (%)</th></tr>{site_rows}</table></div></div>
</div>

<div class="card"><h2 style="margin-top:0">🎯 Batas Kualitas per Brand</h2>
<div class="sub" style="margin-bottom:8px">CV dalam kcal/kg (min ≥ reject). TS/Ash/Na2O dalam % (max = batas atas; min opsional). Kosongkan = tak dibatasi.</div>
<div class="tw"><table>
<tr><th>Brand</th><th>CV reject</th><th>CV min</th><th>CV max</th><th>TS min</th><th>TS max</th><th>Ash min</th><th>Ash max</th><th>Na2O min</th><th>Na2O max</th></tr>
{brand_rows}</table></div></div>
<button class="btn" type="submit">💾 Simpan Constraints</button>
</form>
<script>
function tg(){{const t=document.documentElement.getAttribute('data-theme')==='light'?'dark':'light';
 document.documentElement.setAttribute('data-theme',t);try{{localStorage.setItem('cortex-theme',t)}}catch(e){{}}
 document.getElementById('tb').textContent=t==='light'?'☀️':'🌙';}}
(function(){{let t='dark';try{{t=localStorage.getItem('cortex-theme')||'dark'}}catch(e){{}}
 document.documentElement.setAttribute('data-theme',t);document.getElementById('tb').textContent=t==='light'?'☀️':'🌙';}})();
// feedback simpan: tombol jadi "Menyimpan…" + disabled saat submit (hindari kesan menggantung)
(function(){{var f=document.getElementById('cform'); if(!f) return;
 f.addEventListener('submit',function(){{
   f.querySelectorAll('button[type=submit]').forEach(function(b){{b.disabled=true; b.textContent='⏳ Menyimpan…';}});
 }});}})();
// bila baru tersimpan, pastikan banner terlihat (scroll ke atas)
(function(){{var m=document.getElementById('okmsg'); if(m){{window.scrollTo({{top:0,behavior:'smooth'}});}}}})();
</script></body></html>"""
