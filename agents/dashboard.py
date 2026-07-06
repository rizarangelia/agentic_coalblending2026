"""Dashboard analitik (gaya deployment Railway) — SPA satu halaman di belakang login.
Data dari /api/state; slider deal men-trigger /api/optimize (re-solve live oleh CBC).
Chart: Chart.js via CDN. Semua angka dari solver — JS hanya merender.
"""
DASH_HTML = r"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CoalBlend AI — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800;900&family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b1012;--p:#131c1f;--p2:#172225;--l:#23312f;--ink:#e8efee;--m:#8aa09c;--g:#34c759;--a:#f6b53c;--r:#ef5350;--b:#4aa3df;--gold:#e9c84a}
*{box-sizing:border-box;margin:0}body{background:var(--bg);color:var(--ink);font:14px 'IBM Plex Sans',sans-serif;display:flex;min-height:100vh}
aside{width:212px;background:var(--p);border-right:1px solid var(--l);padding:18px 12px;position:sticky;top:0;height:100vh;flex:none}
.logo{font:900 17px Archivo;padding:0 8px 16px}.logo em{color:var(--g);font-style:normal}.logo small{display:block;font:600 9px 'IBM Plex Mono';color:var(--g);letter-spacing:.16em}
.nav{display:flex;flex-direction:column;gap:4px}.nav a{color:var(--m);text-decoration:none;padding:9px 11px;border-radius:9px;font-size:13px;border:1px solid transparent}
.nav a.on{background:var(--p2);color:var(--ink);border-color:var(--l)}.nav a:hover{color:var(--ink)}
.foot{position:absolute;bottom:14px;left:12px;right:12px;font:10px 'IBM Plex Mono';color:#5f7470}
main{flex:1;padding:22px 26px 70px;max-width:1160px}
.hd{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.hd h1{font:800 20px Archivo}
.badge{font:700 9.5px 'IBM Plex Mono';padding:4px 10px;border-radius:16px;background:rgba(52,199,89,.14);color:#7fe39b;border:1px solid rgba(52,199,89,.35)}
.sub{font:11px 'IBM Plex Mono';color:var(--m);margin:4px 0 16px}
h2{font:800 15px Archivo;border-bottom:1px solid var(--l);padding-bottom:7px;margin:26px 0 6px}
.cap{font:11.5px;color:var(--m);margin-bottom:12px}
.card{background:var(--p);border:1px solid var(--l);border-radius:12px;padding:14px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 9px;border-bottom:1px solid var(--l);text-align:right;font-family:'IBM Plex Mono',monospace;white-space:nowrap}
th{font-size:9.5px;color:var(--m);text-transform:uppercase;letter-spacing:.05em}
th:first-child,td:first-child{text-align:left;font-family:'IBM Plex Sans'}
tr:last-child td{border-bottom:none}.tw{overflow-x:auto}
.pos{color:var(--g)}.neg{color:var(--r)}.amb{color:var(--a)}.mut{color:var(--m)}
.pillOK{color:#7fe39b}.pillMIN,.pillMAX{color:var(--a)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:960px){.grid2{grid-template-columns:1fr}}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:6px}@media(max-width:960px){.kpis{grid-template-columns:1fr 1fr}}
.kpi{background:var(--p);border:1px solid var(--l);border-left:3px solid var(--g);border-radius:11px;padding:12px 14px}
.kpi.b{border-left-color:var(--b)}.kpi.a{border-left-color:var(--a)}.kpi.r{border-left-color:var(--r)}
.kpi .l{font:600 9px 'IBM Plex Mono';color:var(--m);text-transform:uppercase;letter-spacing:.07em}
.kpi .v{font:700 22px 'IBM Plex Mono';margin-top:4px}.kpi .d{font:10.5px 'IBM Plex Mono';color:var(--m);margin-top:3px}
.sliders{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}@media(max-width:960px){.sliders{grid-template-columns:1fr 1fr}}
.sl{background:var(--p2);border:1px solid var(--l);border-radius:10px;padding:10px 12px}
.sl b{font-size:12px}.sl .val{font:700 13px 'IBM Plex Mono';color:var(--g)}
input[type=range]{width:100%;accent-color:var(--g)}
.mx td.dis{color:#3a4a47;background:rgba(255,255,255,.015)}
.spin{color:var(--a);font:600 11px 'IBM Plex Mono';display:none}
canvas{max-height:280px}
.alerts .al{display:flex;gap:9px;border:1px solid var(--l);border-radius:9px;padding:8px 11px;margin-bottom:6px;font-size:12px;background:var(--p2)}
.tag{font:700 8.5px 'IBM Plex Mono';padding:2px 6px;border-radius:4px;color:#0b1012;height:fit-content;margin-top:2px}
section{display:none}section.on{display:block}
.bellw{position:relative;margin-left:auto}
.bell{width:38px;height:38px;border-radius:10px;background:var(--p2);border:1px solid var(--l);display:flex;align-items:center;justify-content:center;font-size:17px;cursor:pointer}
.bell .n{position:absolute;top:-6px;right:-6px;background:var(--r);color:#fff;font:700 9px 'IBM Plex Mono';padding:2px 6px;border-radius:10px;display:none}
.drawer{display:none;position:absolute;right:0;top:46px;width:min(520px,92vw);max-height:66vh;overflow:auto;background:var(--p);border:1px solid var(--l);border-radius:14px;z-index:50;box-shadow:0 18px 50px rgba(0,0,0,.5)}
.drawer.open{display:block}
.dh{display:flex;gap:8px;align-items:center;padding:11px 13px;border-bottom:1px solid var(--l);background:var(--p2);position:sticky;top:0}
.fbtn{font:600 10px 'IBM Plex Mono';padding:4px 10px;border-radius:14px;border:1px solid var(--l);background:transparent;color:var(--m);cursor:pointer}
.fbtn.on{border-color:var(--g);color:#7fe39b;background:rgba(52,199,89,.1)}
.aitem{display:flex;gap:10px;padding:11px 13px;border-bottom:1px solid var(--l);align-items:flex-start}
.dot{width:9px;height:9px;border-radius:50%;flex:none;margin-top:5px}
.d-CRITICAL{background:var(--r);box-shadow:0 0 8px rgba(239,83,80,.6)}.d-WARNING{background:var(--a);box-shadow:0 0 8px rgba(246,181,60,.5)}.d-INFO{background:var(--b)}
.aitem .m{flex:1;font-size:12px}.aitem .m b{font-size:12px}
.state{font:700 8.5px 'IBM Plex Mono';padding:2px 7px;border-radius:4px}
.s-new{background:rgba(239,83,80,.15);color:#ffb3b1}.s-ack{background:rgba(74,163,223,.15);color:#8ecbf2}
.abtn{font:700 9.5px 'IBM Plex Mono';padding:4px 10px;border-radius:6px;cursor:pointer;border:none;background:rgba(74,163,223,.15);color:#8ecbf2}
#toast{position:fixed;bottom:18px;right:18px;z-index:99;display:flex;flex-direction:column;gap:8px}
.tst{background:var(--p);border:1px solid var(--l);border-left:3px solid var(--r);border-radius:11px;padding:11px 14px;max-width:380px;font-size:12.5px;box-shadow:0 12px 34px rgba(0,0,0,.5);animation:tin .25s}
.tst.W{border-left-color:var(--a)}@keyframes tin{from{transform:translateY(12px);opacity:0}}
.prev{font:700 9px 'IBM Plex Mono';padding:3px 9px;border-radius:12px;background:rgba(246,181,60,.14);color:#f6cf86;border:1px solid rgba(246,181,60,.4);letter-spacing:.06em}
.note{background:var(--p2);border-left:3px solid var(--g);border-radius:0 9px 9px 0;padding:10px 13px;font-size:12.5px;margin-top:10px}
.note.r{border-color:var(--r)}.note.a2{border-color:var(--a)}.note.b2{border-color:var(--b)}
.ax{font:9.5px 'IBM Plex Mono';fill:var(--m)}.bt{font:10px 'IBM Plex Mono';fill:var(--ink)}svg.sv{display:block;width:100%;height:auto}
a.btn{background:var(--g);color:#06210f;font:700 12px 'IBM Plex Sans';padding:8px 14px;border-radius:9px;text-decoration:none}
</style></head><body>
<aside><div class="logo">berau<em>coal</em><small>COALBLEND AI</small></div>
<div class="nav">
<a href="#" class="on" data-s="ov">📊 Dashboard</a>
<a href="#" data-s="ap">📦 Available Product</a>
<a href="#" data-s="bp">⚖️ Blending Plan</a>
<a href="#" data-s="rv">💰 Revenue</a>
<a href="#" data-s="pi">💡 Price Intel <span style="font-size:8px;color:var(--a)">MVP2</span></a>
<a href="#" data-s="si">🚢 Stock Intel <span style="font-size:8px;color:var(--a)">MVP3</span></a>
<a href="/input">⬆️ Input Data</a>
<a href="/review">✅ Review &amp; Validasi</a>
<a href="/logout">↩︎ Logout</a></div>
<div class="foot">Model 1–9 v1.1 · Solver CBC<br>angka 100% dari solver</div></aside>
<main>
<div class="hd"><h1 id="title">Dashboard Overview</h1><span class="badge" id="mode">Live Simulation</span><span class="spin" id="spin">⟳ re-optimizing…</span>
<div class="bellw"><div class="bell" id="bell" onclick="tgD()">🔔<span class="n" id="bn"></span></div>
<div class="drawer" id="drawer"><div class="dh"><b style="font-size:13px">Notifikasi</b>
<span class="sub" id="dcount"></span><div style="margin-left:auto;display:flex;gap:5px">
<button class="fbtn on" onclick="flt(this,'all')">Semua</button>
<button class="fbtn" onclick="flt(this,'CRITICAL')">Critical</button>
<button class="fbtn" onclick="flt(this,'WARNING')">Warning</button>
<button class="fbtn" onclick="flt(this,'INFO')">Info</button></div></div>
<div id="dlist"></div></div></div></div><div id="toast"></div>
<div class="sub" id="meta">memuat…</div>

<section id="ov" class="on">
<div class="kpis">
<div class="kpi"><div class="l">Total Revenue (Opsi A)</div><div class="v" id="k_rev">—</div><div class="d">objective solver</div></div>
<div class="kpi b"><div class="l">Total Shipment</div><div class="v" id="k_ship">—</div><div class="d" id="k_cap">—</div></div>
<div class="kpi a"><div class="l">Brand di Batas Reject</div><div class="v" id="k_rej">—</div><div class="d">risiko klaim buyer</div></div>
<div class="kpi"><div class="l">Closing Stock Total</div><div class="v" id="k_cs">—</div><div class="d">buffer anti-demurrage</div></div></div>
<h2>🏭 Coal Balance per Site — Quantity &amp; Quality</h2>
<div class="cap">Opening Stock + Coal Getting − Coal Shipment = Closing Stock · kualitas dalam CV GAR (kcal/kg)</div>
<div class="card tw"><table id="t_bal"></table></div>
<div class="grid2">
<div class="card"><h2 style="border:none;margin:0 0 8px">📊 Coal Balance Flow per Site (MT)</h2><canvas id="c_bal"></canvas></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">🔥 Kualitas (CV GAR) per Site</h2><canvas id="c_cv"></canvas></div></div>
</section>

<section id="ap">
<h2>📦 Available Product = Opening Stock + Coal Getting Plan</h2>
<div class="cap">Maksimal batubara yang bisa dikapalkan bulan ini per site, beserta kualitasnya.</div>
<div class="card tw"><table id="t_av"></table></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">📊 Komposisi Available Product per Site</h2><canvas id="c_av"></canvas></div>
</section>

<section id="bp">
<h2>🎚️ Shipment Schedule Deal per Brand (MT)</h2>
<div class="cap">Geser untuk mensimulasikan perubahan volume deal — optimizer menghitung ulang blending &amp; kolom Optimize secara live (solver CBC di server).</div>
<div class="card"><div class="sliders" id="sliders"></div></div>
<h2>🏷️ Tonnage per Brand</h2>
<div class="card tw"><table id="t_brand"></table></div>
<h2>⚖️ Matriks Blending — Tonnage Site → Brand (MT)</h2>
<div class="cap">Sel redup = kombinasi tidak diizinkan pada Blending Allowance (Model 5).</div>
<div class="card tw"><table id="t_mx" class="mx"></table></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">📊 Komposisi Site Pemblending per Brand</h2><canvas id="c_mx"></canvas></div>
<div class="card" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
<div style="flex:1;font-size:12.5px" class="mut">Simulasi slider tidak mengubah data resmi. Untuk keputusan final, gunakan alur validasi multi-opsi.</div>
<a class="btn" href="/review">Lanjut ke Review &amp; Validasi →</a></div>
</section>

<section id="pi">
<h2>💡 Shadow Price Panel — Nilai Marginal Konstrain <span class="prev">LIVE · dari dual LP run ini</span></h2>
<div class="cap">Setiap solve LP menghasilkan dual values: berapa revenue berubah jika satu konstrain dilonggarkan 1 MT. Bahasa capex &amp; negosiasi, dihitung ulang tiap simulasi slider.</div>
<div class="kpis" id="sh_kpis"></div>
<div class="grid2" style="margin-top:14px">
<div class="card"><h2 style="border:none;margin:0 0 8px">Nilai Marginal per Konstrain (per MT)</h2><div class="cap">positif = melonggarkan menambah revenue · negatif = kewajiban ini memakan revenue</div><div class="tw"><table id="t_sh"></table></div></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">Ladder Nilai per 1.000 kcal</h2><div class="cap">base price ÷ CV kontrak — kompas kenapa optimizer mendorong kalori ke brand premium</div><canvas id="c_lad"></canvas></div></div>
<div class="note b2"><b>Guardrail harga (pra-MVP 2):</b> sistem memeriksa kurva harga wajib monotonic terhadap band CV setiap run — anomali muncul sebagai WARNING di lonceng 🔔, bukan halaman terpisah.</div>
</section>

<section id="si">
<h2>🚢 Stock &amp; Marine Intelligence <span class="prev">PREVIEW MVP 3 · ANGKA SIMULASI</span></h2>
<div class="cap">Gambaran end-in-mind fase 3 — membutuhkan data vessel/laycan &amp; histori aktual-vs-plan. Semua angka di bawah simulasi.</div>
<div class="grid2">
<div class="card"><h2 style="border:none;margin:0 0 8px">Probabilistic Stock Fan (P10–P50–P90)</h2>
<svg class="sv" viewBox='0 0 560 230'><line x1='44' y1='14' x2='500' y2='14' stroke='#1c2a28'/><line x1='44' y1='61' x2='500' y2='61' stroke='#1c2a28'/><line x1='44' y1='108' x2='500' y2='108' stroke='#1c2a28'/><line x1='44' y1='155' x2='500' y2='155' stroke='#1c2a28'/><line x1='44' y1='202' x2='500' y2='202' stroke='#1c2a28'/>
<text class='ax' x='38' y='17' text-anchor='end'>650</text><text class='ax' x='38' y='111' text-anchor='end'>425</text><text class='ax' x='38' y='205' text-anchor='end'>200</text>
<path d='M44 52 L120 58 L196 60 L272 64 L348 67 L424 65 L500 60 L500 164 L424 166 L348 160 L272 148 L196 133 L120 121 L44 102 Z' fill='rgba(74,163,223,.16)'/>
<path d='M44 77 L120 89 L196 95 L272 106 L348 114 L424 116 L500 112' fill='none' stroke='#4aa3df' stroke-width='2.4'/>
<line x1='44' y1='164' x2='500' y2='164' stroke='#ef5350' stroke-dasharray='5 4'/><circle cx='424' cy='166' r='6' fill='none' stroke='#ef5350' stroke-width='2'/>
<text class='bt' x='504' y='167' style='fill:#ef5350;font-size:9px'>band min</text><text class='bt' x='504' y='115' style='fill:#4aa3df;font-size:9px'>P50</text>
<text class='ax' x='44' y='220' text-anchor='middle'>Jun</text><text class='ax' x='196' y='220' text-anchor='middle'>Agu</text><text class='ax' x='348' y='220' text-anchor='middle'>Okt</text><text class='ax' x='500' y='220' text-anchor='middle'>Des</text></svg>
<div class="note r">P10 menembus band min di <b>November</b> — deteksi risiko stok kritis 4 bulan lebih awal; proyeksi deterministik tidak akan menunjukkannya.</div></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">Laycan–Stock Matcher</h2>
<svg class="sv" viewBox='0 0 560 220'>
<rect x='60' y='18' width='90' height='20' rx='5' fill='#46c06a' fill-opacity='.28' stroke='#46c06a'/><text class='bt' x='65' y='32' style='font-size:9px'>MV ORIENT STAR · Mahoni B 65rb</text><text class='ax' x='156' y='32' style='fill:#46c06a;font-weight:700;font-size:9px'>OK</text>
<rect x='140' y='58' width='95' height='20' rx='5' fill='#e9c84a' fill-opacity='.28' stroke='#e9c84a'/><text class='bt' x='145' y='72' style='font-size:9px'>MV PACIFIC · CV 4600 55rb</text><text class='ax' x='241' y='72' style='fill:#e9c84a;font-weight:700;font-size:9px'>KETAT −2 hr</text>
<rect x='225' y='98' width='105' height='20' rx='5' fill='#ef5350' fill-opacity='.28' stroke='#ef5350'/><text class='bt' x='230' y='112' style='font-size:9px'>MV HARMONY · Sungkai B 70rb</text><text class='ax' x='336' y='112' style='fill:#ef5350;font-weight:700;font-size:9px'>GAP STOK</text>
<rect x='300' y='138' width='95' height='20' rx='5' fill='#46c06a' fill-opacity='.28' stroke='#46c06a'/><text class='bt' x='305' y='152' style='font-size:9px'>MV NUSANTARA · Eboni 40rb</text><text class='ax' x='401' y='152' style='fill:#46c06a;font-weight:700;font-size:9px'>OK</text>
<rect x='380' y='178' width='100' height='20' rx='5' fill='#46c06a' fill-opacity='.28' stroke='#46c06a'/><text class='bt' x='385' y='192' style='font-size:9px'>MV BORNEO · CV 4200 80rb</text><text class='ax' x='486' y='192' style='fill:#46c06a;font-weight:700;font-size:9px'>OK</text></svg>
<div class="note a2"><b>MV HARMONY</b> GAP STOK: sistem mengusulkan aksi terurut — geser laycan +4 hari · pindah loading ke Binsua · re-blend parsial dari Lati; demurrage dihitung per opsi.</div></div></div>
<div class="card" style="margin-top:14px"><h2 style="border:none;margin:0 0 8px">Survey Reconciliation Radar</h2>
<div class="tw"><table><tr><th>CPP</th><th>Book</th><th>Survey</th><th>Varians</th><th>Trend 3 bln</th><th>Status</th></tr>
<tr><td>Lati</td><td>200.000</td><td>198.400</td><td class="mut">−0,8%</td><td class="mut">−0,5 · −0,7 · −0,8</td><td class="pos">Wajar</td></tr>
<tr><td>Sambarata</td><td>250.000</td><td>241.200</td><td class="neg">−3,5%</td><td class="neg">−1,1 · −2,4 · −3,5</td><td class="neg">INVESTIGASI</td></tr>
<tr><td>Gurimbang</td><td>50.000</td><td>49.700</td><td class="mut">−0,6%</td><td class="mut">stabil</td><td class="pos">Wajar</td></tr></table></div>
<div class="note r">Varians Sambarata memburuk beruntun — dan Sambarata satu-satunya bahan bakar brand premium: error 3,5% = risiko CV Eboni/Mahoni meleset. Varians beruntun otomatis menjadi alert CRITICAL di lonceng sebelum blending dihitung.</div></div>
</section>

<section id="rv">
<h2>💰 Revenue = Tonnage Product × Harga</h2>
<div class="cap">Harga aktual mengikuti kualitas blending: harga = base price × (CV blending ÷ CV kontrak).</div>
<div class="card tw"><table id="t_rev"></table></div>
<div class="card"><h2 style="border:none;margin:0 0 8px">📊 Revenue per Brand</h2><canvas id="c_rev"></canvas></div>
</section>
</main>
<script>
const F=v=>Math.round(v).toLocaleString('id-ID'), F1=v=>v.toLocaleString('id-ID',{maximumFractionDigits:0});
const PAL=['#34c759','#4aa3df','#e9c84a','#f6b53c','#ef5350','#8aa09c','#7fe39b','#8ecbf2'];
const GRID={color:'#1c2a28'}, TICK={color:'#8aa09c',font:{family:'IBM Plex Mono',size:10}};
Chart.defaults.color='#8aa09c'; Chart.defaults.font.family='IBM Plex Sans';
let ST=null, charts={}, deb=null;

document.querySelectorAll('.nav a[data-s]').forEach(a=>a.onclick=e=>{e.preventDefault();
 document.querySelectorAll('.nav a[data-s]').forEach(x=>x.classList.remove('on'));a.classList.add('on');
 document.querySelectorAll('main section').forEach(s=>s.classList.remove('on'));
 document.getElementById(a.dataset.s).classList.add('on');
 document.getElementById('title').textContent=a.textContent.replace(/^..\s*/,'');});

function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
async function load(){ST=await (await fetch('/api/state')).json();renderAll();buildSliders();}
function sol(){return ST.solution}

function renderAll(){
 const s=sol(),S=ST.sites,B=ST.brands;
 document.getElementById('meta').textContent=`sumber data: ${ST.meta.sumber} · manifest v${ST.meta.versi} · user: ${ST.meta.user}`;
 document.getElementById('k_rev').textContent=F(s.revenue);
 document.getElementById('k_ship').textContent=F(s.total_ship);
 document.getElementById('k_cap').textContent='/ kapasitas '+F(ST.total_capacity);
 document.getElementById('k_rej').textContent=B.filter(b=>s.brand_total[b]>0&&Math.abs(s.brand_cv[b]-ST.cv_min[b])<1).length;
 document.getElementById('k_cs').textContent=F(S.reduce((t,x)=>t+s.closing[x.site],0));
 // balance table
 let h='<tr><th>Site</th><th>Opening Stock</th><th>CV</th><th>Coal Getting</th><th>CV</th><th>Coal Shipment</th><th>CV*</th><th>Closing Stock</th><th>CV</th><th>Status Closing</th></tr>';
 S.forEach(x=>{const ship=s.site_ship[x.site],cl=s.closing[x.site];
  const st=Math.abs(cl-x.cs_min)<1?['pillMIN','DI MIN']:(Math.abs(cl-x.cs_max)<1?['pillMAX','DI MAX']:['pillOK','Sehat']);
  h+=`<tr><td>${x.site}</td><td>${F(x.opening)}</td><td class=mut>${F1(x.cv_open)}</td><td>${F(x.cg)}</td><td class=mut>${F1(x.cv_cg)}</td><td>${F(ship)}</td><td class=mut>${F1(x.cv)}</td><td><b>${F(cl)}</b></td><td class=mut>${F1(x.cv)}</td><td class="${st[0]}">${st[1]}</td></tr>`});
 document.getElementById('t_bal').innerHTML=h+'<tr><td class=mut style="font-size:10px" colspan=10>*CV shipment & closing memakai CV komposit available per site (single-quality per site pada MVP 1)</td></tr>';
 mk('c_bal',{type:'bar',data:{labels:S.map(x=>x.site),datasets:[
  {label:'Opening',data:S.map(x=>x.opening),backgroundColor:'#4aa3df'},
  {label:'Coal Getting',data:S.map(x=>x.cg),backgroundColor:'#34c759'},
  {label:'Shipment',data:S.map(x=>-s.site_ship[x.site]),backgroundColor:'#ef5350'},
  {label:'Closing',data:S.map(x=>s.closing[x.site]),backgroundColor:'#e9c84a'}]},
  options:{scales:{x:{grid:GRID,ticks:TICK},y:{grid:GRID,ticks:TICK}},plugins:{legend:{labels:{color:'#8aa09c'}}}}});
 mk('c_cv',{type:'bar',data:{labels:S.map(x=>x.site),datasets:[{label:'CV GAR',data:S.map(x=>x.cv),backgroundColor:S.map((_,i)=>PAL[i])}]},
  options:{indexAxis:'y',scales:{x:{grid:GRID,ticks:TICK,min:3000},y:{grid:GRID,ticks:TICK}},plugins:{legend:{display:false}}}});
 renderBell();
 renderPI();
 // available
 h='<tr><th>Site</th><th>Opening Stock (MT)</th><th>Coal Getting Plan (MT)</th><th>Available Product (MT)</th><th>Kualitas GAR</th><th>Plan Kapasitas Jetty (MT)</th><th>Utilisasi Shipment</th></tr>';
 S.forEach(x=>{const u=s.site_ship[x.site]/x.jetty*100;
  h+=`<tr><td>${x.site}</td><td>${F(x.opening)}</td><td>${F(x.cg)}</td><td><b>${F(x.available)}</b></td><td class=mut>${F1(x.cv)}</td><td>${F(x.jetty)}</td><td class="${u>100?'amb':'pos'}">${u.toFixed(0)}%${u>100?' ⚠':''}</td></tr>`});
 document.getElementById('t_av').innerHTML=h;
 mk('c_av',{type:'bar',data:{labels:S.map(x=>x.site),datasets:[
  {label:'Opening Stock',data:S.map(x=>x.opening),backgroundColor:'#4aa3df',stack:'a'},
  {label:'Coal Getting',data:S.map(x=>x.cg),backgroundColor:'#34c759',stack:'a'}]},
  options:{scales:{x:{stacked:true,grid:GRID,ticks:TICK},y:{stacked:true,grid:GRID,ticks:TICK}},plugins:{legend:{labels:{color:'#8aa09c'}}}}});
 renderBlend(); renderRev();
}
function renderBlend(){
 const s=sol(),S=ST.sites,B=ST.brands;
 let h='<tr><th>Brand</th><th>Deal (MT)</th><th>Optimize (MT)</th><th>Total Shipment (MT)</th><th>CV Blending</th><th>Band CV (min–max)</th><th>Kualitas</th></tr>';
 B.forEach(b=>{const cv=s.brand_cv[b],mn=ST.cv_min[b],mx=ST.cv_max[b];
  const q=Math.abs(cv-mn)<1?['neg','DI BATAS REJECT']:(cv>=mx-1?['pos','di typical']:['amb',`−${F1(mx-cv)} vs typical`]);
  h+=`<tr><td>${b}</td><td>${F(s.deal[b])}</td><td class=pos>${F(s.optimize[b])}</td><td><b>${F(s.brand_total[b])}</b></td><td>${F1(cv)}</td><td class=mut>${F1(mn)}–${F1(mx)}</td><td class="${q[0]}">${q[1]}</td></tr>`});
 document.getElementById('t_brand').innerHTML=h;
 h='<tr><th>Site \\ Brand</th>'+B.map(b=>`<th>${b}</th>`).join('')+'<th>Total Site</th></tr>';
 S.forEach(x=>{h+=`<tr><td>${x.site}</td>`+B.map(b=>ST.allowance[x.site][b]?`<td>${s.x[x.site][b]>0.5?F(s.x[x.site][b]):'<span class=mut>—</span>'}</td>`:'<td class=dis>✕</td>').join('')+`<td><b>${F(s.site_ship[x.site])}</b></td></tr>`});
 h+='<tr><td><b>Total Brand</b></td>'+B.map(b=>`<td><b>${F(s.brand_total[b])}</b></td>`).join('')+`<td><b>${F(s.total_ship)}</b></td></tr>`;
 document.getElementById('t_mx').innerHTML=h;
 mk('c_mx',{type:'bar',data:{labels:B,datasets:S.map((x,i)=>({label:x.site,data:B.map(b=>s.x[x.site][b]),backgroundColor:PAL[i],stack:'s'}))},
  options:{scales:{x:{stacked:true,grid:GRID,ticks:TICK},y:{stacked:true,grid:GRID,ticks:TICK}},plugins:{legend:{labels:{color:'#8aa09c'}}}}});
}
function renderRev(){
 const s=sol(),B=ST.brands;
 let h='<tr><th>Brand</th><th>Tonnage (MT)</th><th>Base Price ($/MT)</th><th>CV Blending / Kontrak</th><th>Harga Aktual ($/MT)</th><th>Revenue ($)</th></tr>',tot=0;
 B.forEach(b=>{const t=s.brand_total[b],cv=s.brand_cv[b],bp=ST.price[b],k=ST.cv_max[b],pa=bp*cv/k,rev=s.brand_revenue[b];tot+=rev;
  h+=`<tr><td>${b}</td><td>${F(t)}</td><td>${bp}</td><td class=mut>${F1(cv)} / ${F1(k)}</td><td>${pa.toFixed(2)}</td><td><b>${F(rev)}</b></td></tr>`});
 h+=`<tr><td><b>Total</b></td><td colspan=4></td><td><b>${F(tot)}</b></td></tr>`;
 document.getElementById('t_rev').innerHTML=h;
 mk('c_rev',{type:'bar',data:{labels:B,datasets:[{label:'Revenue',data:B.map(b=>s.brand_revenue[b]),backgroundColor:B.map((_,i)=>PAL[i])}]},
  options:{scales:{x:{grid:GRID,ticks:TICK},y:{grid:GRID,ticks:TICK}},plugins:{legend:{display:false}}}});
}
function buildSliders(){
 const el=document.getElementById('sliders');el.innerHTML='';
 ST.brands.forEach(b=>{const d0=ST.deal_default[b];
  el.insertAdjacentHTML('beforeend',`<div class=sl><b>${b}</b> <span class=val id=v_${b.replace(/\s/g,'_')}>${F(d0)}</span>
  <input type=range min=0 max=${d0*2} step=5000 value=${d0} data-b="${b}"></div>`)});
 el.querySelectorAll('input').forEach(i=>i.oninput=()=>{
  document.getElementById('v_'+i.dataset.b.replace(/\s/g,'_')).textContent=F(+i.value);
  clearTimeout(deb);deb=setTimeout(reopt,450);});
}
async function reopt(){
 const overrides={};document.querySelectorAll('#sliders input').forEach(i=>overrides[i.dataset.b]=+i.value);
 document.getElementById('spin').style.display='inline';
 const r=await (await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({deal:overrides})})).json();
 document.getElementById('spin').style.display='none';
 if(r.status!=='Optimal'){document.getElementById('mode').textContent='INFEASIBLE — lihat alert';document.getElementById('mode').style.background='rgba(239,83,80,.15)';document.getElementById('mode').style.color='#ffb3b1';
  ST.alerts=r.alerts;renderBell();return;}
 document.getElementById('mode').textContent='Live Simulation';document.getElementById('mode').style.background='';document.getElementById('mode').style.color='';
 ST.solution=r.solution;ST.alerts=r.alerts;renderAll();
}
// ===== BELL / DRAWER / TOAST — alert muncul hanya saat trigger =====
let seen=new Set(), dfilter='all';
function tgD(){document.getElementById('drawer').classList.toggle('open')}
function flt(btn,s){dfilter=s;document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');renderBell(true)}
function renderBell(keepOpen){
 const A=ST.alerts||[], un=A.filter(a=>!a.acked&&a.sev!=='INFO');
 const bn=document.getElementById('bn');
 bn.style.display=un.length?'block':'none'; bn.textContent=un.length;
 document.getElementById('dcount').textContent=`${A.length} alert · ${un.length} perlu perhatian`;
 document.getElementById('dlist').innerHTML=A.filter(a=>dfilter==='all'||a.sev===dfilter).map(a=>`
  <div class="aitem"><span class="dot d-${a.sev}"></span>
  <div class="m"><b>[${a.cat}]</b> ${a.msg}
  <div style="margin-top:4px"><span class="state ${a.acked?'s-ack':'s-new'}">${a.acked?'DIAKUI':'BARU'}</span></div></div>
  ${a.acked||a.sev==='INFO'?'':`<button class="abtn" onclick="ack('${a.id}')">Akui</button>`}</div>`).join('')
  ||'<div class="aitem"><span class="mut">Tidak ada alert.</span></div>';
 // TOAST: hanya alert BARU (belum pernah tampil di sesi ini) & belum diakui & bukan INFO
 un.filter(a=>!seen.has(a.id)).slice(0,3).forEach(a=>{seen.add(a.id);
  const d=document.createElement('div');d.className='tst '+(a.sev==='WARNING'?'W':'');
  d.innerHTML=`<b>[${a.cat}]</b> ${a.msg}`;document.getElementById('toast').appendChild(d);
  setTimeout(()=>d.remove(),6500);});
 A.forEach(a=>seen.add(a.id));
}
async function ack(id){await fetch('/api/alerts/ack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
 (ST.alerts.find(a=>a.id===id)||{}).acked=true;renderBell(true);}
document.addEventListener('click',e=>{const d=document.getElementById('drawer');
 if(d.classList.contains('open')&&!e.target.closest('.bellw'))d.classList.remove('open')});

// ===== PRICE INTEL (MVP2 preview — data NYATA dari dual LP) =====
function renderPI(){
 const s=sol(), sh=s.shadow; if(!sh)return;
 const S=ST.sites.map(x=>x.site), B=ST.brands;
 const worstDeal=B.reduce((w,b)=>(sh.deal[b]??0)<(sh.deal[w]??0)?b:w,B[0]);
 const bestAvail=S.reduce((w,x)=>(sh.available[x]??0)>(sh.available[w]??0)?x:w,S[0]);
 const bestCsMax=S.reduce((w,x)=>(sh.cs_max[x]??0)>(sh.cs_max[w]??0)?x:w,S[0]);
 document.getElementById('sh_kpis').innerHTML=`
 <div class="kpi"><div class="l">Kapasitas Total (M4)</div><div class="v">${(sh.total_capacity??0).toFixed(2)}<small>/MT</small></div><div class="d">nilai tiap +1 MT kapasitas shipment</div></div>
 <div class="kpi r"><div class="l">Deal Paling Menyeret</div><div class="v">${(sh.deal[worstDeal]??0).toFixed(2)}<small>/MT</small></div><div class="d">${worstDeal} — biaya per MT kewajiban deal</div></div>
 <div class="kpi b"><div class="l">Coal Paling Bernilai</div><div class="v">${(sh.available[bestAvail]??0).toFixed(2)}<small>/MT</small></div><div class="d">available ${bestAvail} +1 MT</div></div>
 <div class="kpi a"><div class="l">Plafon Closing Terberharga</div><div class="v">${(sh.cs_max[bestCsMax]??0).toFixed(2)}<small>/MT</small></div><div class="d">melonggarkan cs_max ${bestCsMax}</div></div>`;
 let h='<tr><th>Konstrain</th><th>Objek</th><th>Shadow Price (/MT)</th><th style="text-align:left">Interpretasi</th></tr>';
 h+=`<tr><td>M4 kapasitas total</td><td>—</td><td class="pos">${(sh.total_capacity??0).toFixed(2)}</td><td style="text-align:left" class="mut">tiap +1 MT kapasitas → revenue naik segini</td></tr>`;
 B.forEach(b=>{const v=sh.deal[b];if(v==null)return;
  h+=`<tr><td>M1 deal</td><td>${b}</td><td class="${v<-0.001?'neg':'mut'}">${v.toFixed(2)}</td><td style="text-align:left" class="mut">${v<-0.001?'kewajiban deal ini memakan revenue':'tidak binding'}</td></tr>`});
 S.forEach(x=>{const v=sh.available[x];if(v>0.001)h+=`<tr><td>M3 available</td><td>${x}</td><td class="pos">${v.toFixed(2)}</td><td style="text-align:left" class="mut">coal ${x} tambahan bernilai — bahan bakar brand mahal</td></tr>`});
 S.forEach(x=>{const v=sh.cs_max[x];if(v>0.001)h+=`<tr><td>M9 max closing</td><td>${x}</td><td class="pos">${v.toFixed(2)}</td><td style="text-align:left" class="mut">plafon stok ${x} membatasi revenue</td></tr>`;
  const w=sh.cs_min[x];if(w<-0.001)h+=`<tr><td>M8 min closing</td><td>${x}</td><td class="neg">${w.toFixed(2)}</td><td style="text-align:left" class="mut">safety stock ${x} berbiaya segini per MT</td></tr>`});
 document.getElementById('t_sh').innerHTML=h;
 mk('c_lad',{type:'bar',data:{labels:B,datasets:[{label:'$/1000 kcal',data:B.map(b=>ST.price[b]/ST.cv_max[b]*1000),backgroundColor:B.map((_,i)=>PAL[i])}]},
  options:{indexAxis:'y',scales:{x:{grid:GRID,ticks:TICK},y:{grid:GRID,ticks:TICK}},plugins:{legend:{display:false}}}});
}
load();
</script></body></html>"""
