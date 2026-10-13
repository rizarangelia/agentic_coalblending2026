"""Agent 3 — Blending Generator (The Core).
LP deterministik (PuLP). LLM tidak pernah menghasilkan angka — hanya menarasikan hasil.
Solver: HiGHS in-process bila tersedia (jalan di serverless/Vercel tanpa subprocess binary);
fallback CBC. Fitur kunci: infeasibility DIAGNOSER (elastic re-solve) -> relaksasi minimum.
"""
import pulp


def _solver():
    """Solver LP yang tersedia. PuLP >=4 melepas CBC bawaan & memakai HiGHS (in-process,
    jalan di Lambda/Vercel tanpa subprocess). PuLP <4 pakai CBC. None = default PuLP."""
    for name, kw in (('HiGHS', {'msg': False}), ('PULP_CBC_CMD', {'msg': 0})):
        cls = getattr(pulp, name, None)
        if cls is not None:
            try:
                s = cls(**kw)
                if s.available():
                    return s
            except Exception:
                continue
    return None

def _base_model(C, elastic=False):
    sites, brands = C['sites'], C['brands']
    m = pulp.LpProblem('coalblend', pulp.LpMaximize)
    x = {(s, b): pulp.LpVariable(f'x_{s}_{b}'.replace(' ', '_'), lowBound=0) for s in sites for b in brands}
    slack = {}

    def S(name, lb=0):
        slack[name] = pulp.LpVariable('sl_' + name.replace(' ', '_'), lowBound=lb)
        return slack[name]

    for s in sites:
        for b in brands:
            if not C['allowance'][s][b]:
                m += x[s, b] == 0, f'M5_{s}_{b}'
    # dimensi kualitas tambahan (aktif hanya bila settings menyediakannya)
    QDIM = (('ts', 'M10'), ('ash', 'M11'), ('na2o', 'M12'))
    for b in brands:
        tot = pulp.lpSum(x[s, b] for s in sites)
        eng = pulp.lpSum(x[s, b] * C['cv_site'][s] for s in sites)
        m += tot + (S(f'M1 deal {b}') if elastic else 0) >= C['deal'][b], f'M1_{b}'
        m += tot <= C['deal_multiplier'] * C['deal'][b] + (S(f'M2 max {b}') if elastic else 0), f'M2_{b}'
        m += eng + (S(f'M6 cvmin {b}') if elastic else 0) >= C['cv_min'][b] * tot, f'M6_{b}'
        m += eng <= C['cv_max'][b] * tot + (S(f'M7 cvmax {b}') if elastic else 0), f'M7_{b}'
        for dim, mid in QDIM:  # TS / Ash / Na2O — weighted per brand <= max (>= min opsional)
            site_a = C.get(f'{dim}_site'); smax = C.get(f'{dim}_max') or {}; smin = C.get(f'{dim}_min') or {}
            if site_a and b in smax:
                q = pulp.lpSum(x[s, b] * site_a[s] for s in sites)
                m += q <= smax[b] * tot + (S(f'{mid} {dim}max {b}') if elastic else 0), f'{mid}_{b}'
            if site_a and b in smin:
                q = pulp.lpSum(x[s, b] * site_a[s] for s in sites)
                m += q + (S(f'{mid}min {dim} {b}') if elastic else 0) >= smin[b] * tot, f'{mid}min_{b}'
    for s in sites:
        ship = pulp.lpSum(x[s, b] for b in brands)
        m += ship <= C['available'][s], f'M3_{s}'
        m += C['available'][s] - ship + (S(f'M8 csmin {s}') if elastic else 0) >= C['cs_min'][s], f'M8_{s}'
        m += C['available'][s] - ship <= C['cs_max'][s] + (S(f'M9 csmax {s}') if elastic else 0), f'M9_{s}'
    grand = pulp.lpSum(x[s, b] for s in sites for b in brands)
    cap_max = C.get('cap_total_max', C['total_capacity'])
    m += grand <= cap_max + (S('M4 total') if elastic else 0), 'M4'
    if C.get('cap_total_min'):  # capacity minimum (opsional dari menu)
        m += grand + (S('M4min total') if elastic else 0) >= C['cap_total_min'], 'M4min'

    revenue = pulp.lpSum(pulp.lpSum(x[s, b] * C['cv_site'][s] for s in sites) / C['cv_max'][b] * C['price'][b] for b in brands)
    qr = C.get('quality_reward')  # dorong CV brand naik (headroom di atas cv_min), bobot kecil
    if qr:
        revenue = revenue + qr * pulp.lpSum(
            pulp.lpSum(x[s, b] * C['cv_site'][s] for s in sites) - C['cv_min'][b] * pulp.lpSum(x[s, b] for s in sites)
            for b in brands)
    return m, x, slack, revenue

def solve(C):
    alerts = []
    m, x, _, revenue = _base_model(C)
    m += revenue
    m.solve(_solver())
    if pulp.LpStatus[m.status] != 'Optimal':
        # DIAGNOSER: minimasi total slack -> relaksasi minimum yang membuat feasible
        md, _, slack, _ = _base_model(C, elastic=True)
        md.sense = pulp.LpMinimize
        md += pulp.lpSum(slack.values())
        md.solve(_solver())
        diag = sorted(((n, v.value()) for n, v in slack.items() if v.value() and v.value() > 1e-6),
                      key=lambda t: -t[1])
        for n, v in diag:
            alerts.append(('CRITICAL', 'OPTIMIZER',
                           f'INFEASIBLE — konstrain "{n}" butuh relaksasi minimum ±{v:,.0f} agar solvable.'))
        if not diag:
            alerts.append(('CRITICAL', 'OPTIMIZER', 'INFEASIBLE — diagnosis slack tidak konklusif; cek data input.'))
        return None, alerts

    sol = {'status': 'Optimal', 'revenue': pulp.value(m.objective),
           'x': {s: {b: x[s, b].value() or 0 for b in C['brands']} for s in C['sites']}}
    # shadow prices (dual values) — nilai marginal konstrain, gratis dari LP
    def _pi(name):
        k = name.replace(' ', '_')
        c = m.constraints.get(k)
        pi = getattr(c, 'pi', None) if c is not None else None   # HiGHS kadang tak isi dual → None-safe
        return round(pi, 4) if pi is not None else None
    sol['shadow'] = {
        'total_capacity': _pi('M4'),
        'deal': {b: _pi(f'M1_{b}') for b in C['brands']},
        'available': {s: _pi(f'M3_{s}') for s in C['sites']},
        'cs_min': {s: _pi(f'M8_{s}') for s in C['sites']},
        'cs_max': {s: _pi(f'M9_{s}') for s in C['sites']},
    }
    sol['brand_total'] = {b: sum(sol['x'][s][b] for s in C['sites']) for b in C['brands']}
    sol['brand_cv'] = {b: (sum(sol['x'][s][b] * C['cv_site'][s] for s in C['sites']) / t if (t := sol['brand_total'][b]) else 0)
                       for b in C['brands']}
    sol['brand_revenue'] = {b: sum(sol['x'][s][b] * C['cv_site'][s] for s in C['sites']) / C['cv_max'][b] * C['price'][b]
                            for b in C['brands']}
    # kualitas tambahan per brand (weighted) — hanya bila assay tersedia dari settings
    for dim in ('ts', 'ash', 'na2o'):
        site_a = C.get(f'{dim}_site')
        if site_a:
            sol['brand_' + dim] = {b: (sum(sol['x'][s][b] * site_a[s] for s in C['sites']) / t
                                       if (t := sol['brand_total'][b]) else 0) for b in C['brands']}
    sol['optimize'] = {b: sol['brand_total'][b] - C['deal'][b] for b in C['brands']}
    sol['site_ship'] = {s: sum(sol['x'][s][b] for b in C['brands']) for s in C['sites']}
    sol['closing'] = {s: C['available'][s] - sol['site_ship'][s] for s in C['sites']}
    sol['total_ship'] = sum(sol['site_ship'].values())

    # post-solve alerts — bandingkan ke batas REJECT ASLI (bukan floor quality-safe)
    for b in C['brands']:
        rej = C.get('cv_reject', C['cv_min']).get(b, C['cv_min'][b])
        if sol['brand_total'][b] > 0 and sol['brand_cv'][b] <= rej + 1:
            alerts.append(('WARNING', 'COMMERCIAL',
                           f'{b}: CV blend {sol["brand_cv"][b]:,.0f} tepat DI BATAS REJECT — zero margin kualitas, risiko klaim buyer.'))
    for s in C['sites']:
        if sol['site_ship'][s] > C['jetty_capacity'][s] + 1:
            alerts.append(('WARNING', 'LOGISTIK',
                           f'{s}: blending {sol["site_ship"][s]:,.0f} melebihi kapasitas jetty {C["jetty_capacity"][s]:,.0f} '
                           f'(Model 4 total-only; verifikasi outloading site ini).'))
        if abs(sol['closing'][s] - C['cs_max'][s]) < 1:
            alerts.append(('INFO', 'STOCK', f'{s}: closing stock mentok di MAX band ({C["cs_max"][s]:,.0f}).'))
        if abs(sol['closing'][s] - C['cs_min'][s]) < 1:
            alerts.append(('INFO', 'STOCK', f'{s}: closing stock mentok di MIN band ({C["cs_min"][s]:,.0f}).'))
    return sol, alerts


# ---------- Human-in-the-Loop: multi-skenario ----------
import copy

def solve_scenarios(C):
    """3 opsi kanonik — SATU tuas per opsi agar trade-off teratribusi bersih.
    A Max Revenue (murni) · B Quality-Safe (cv_min +25 saja) · C Normalisasi Stok (closing tiap site 20–80% band).
    Angka 100% dari solver."""
    out = []

    def run(cid, nama, desc, Cx):
        sol, al = solve(Cx)
        out.append({'id': cid, 'nama': nama, 'desc': desc, 'sol': sol, 'alerts': al,
                    'revenue': sol['revenue'] if sol else None})

    run('A', 'Max Revenue (Baseline)',
        'Model 1-9 murni. Revenue tertinggi; konsekuensi: beberapa brand tepat di batas reject.', C)

    C2 = copy.deepcopy(C)
    C2['cv_min'] = {b: v + 25 for b, v in C['cv_min'].items()}
    run('B', 'Quality-Safe (buffer +25 GAR)',
        'Satu tuas: CV blend minimal +25 di atas reject. Margin klaim buyer; revenue sedikit turun.', C2)

    C3 = copy.deepcopy(C)
    for s in C3['sites']:
        lo, hi = C3['cs_min'][s], C3['cs_max'][s]
        rng = hi - lo
        C3['cs_min'][s] = lo + 0.20 * rng   # lantai sehat: closing tak kurang dari 20% band
        C3['cs_max'][s] = lo + 0.80 * rng   # plafon sehat: closing tak lebih dari 80% band
    run('C', 'Normalisasi Stok Antar-Site',
        'Satu tuas: closing tiap site dijaga di 20–80% band (stok sehat) — '
        'tidak ada site kebanyakan (mentok MAX) atau kedikitan (mentok MIN).', C3)

    base = out[0]['revenue']
    for sc in out:
        sc['delta'] = (sc['revenue'] - base) if (sc['revenue'] is not None and base) else None
        if sc['sol']:
            sc['n_reject'] = sum(1 for b in C['brands']
                                 if sc['sol']['brand_total'][b] > 0 and abs(sc['sol']['brand_cv'][b] - C['cv_min'][b]) < 1)
    return out
