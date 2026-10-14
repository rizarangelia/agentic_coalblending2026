"""Agent 2 — Constraint Manager.
Membaca constraint_manifest.json (source of truth deterministik, BUKAN vector retrieval)
+ data runtime valid -> constraint set siap-solve (Model 1-9 final tervalidasi):
  Model 4 TOTAL-ONLY (per-jetty = warning check), Model 6 tanpa toleransi -50.
"""

def build(manifest: dict, data: dict, overrides: dict = None, settings: dict = None):
    """overrides (Manual Override validator): {'cs_min':{site:v},'cs_max':{site:v},'deal':{brand:v}} —
    tacit knowledge manusia masuk sebagai parameter, dicatat di audit trail.
    settings (opsional, dari menu Constraints): min/max Capacity/CV/TS/Ash/Na2O + assay per Site.
    TANPA settings, perilaku identik dengan baseline (jalur test tidak berubah)."""
    alerts = []
    sites, brands = manifest['sites'], manifest['brands']
    avail = {s: data['opening_stock'][s]['volume_mt'] + data['coal_getting'][s]['volume_mt'] for s in sites}
    # CV komposit available product (weighted opening + CG per site)
    cv = {}
    for s in sites:
        o, g = data['opening_stock'][s], data['coal_getting'][s]
        cv[s] = (o['volume_mt'] * o['cv_gar'] + g['volume_mt'] * g['cv_gar']) / max(avail[s], 1e-9)
    deal = {b: data['demand_deal'][b]['volume_deal_mt'] for b in brands}
    if overrides and overrides.get('deal'):
        deal.update({b: float(v) for b, v in overrides['deal'].items() if b in deal})
    jetty = {s: data['plan_kapasitas'][s]['kapasitas_mt'] for s in sites}
    total_cap = sum(jetty.values())
    mult = manifest['constraints']['model_2']['multiplier']
    spec = manifest['brand_spec']
    csb = {s: dict(manifest['closing_stock_band_simulasi'][s]) for s in sites}
    if overrides:
        for s, v in (overrides.get('cs_min') or {}).items(): csb[s]['min'] = float(v)
        for s, v in (overrides.get('cs_max') or {}).items(): csb[s]['max'] = float(v)
        for b, v in (overrides.get('deal') or {}).items(): deal_ovr = True

    # sanity pre-solve (deteksi dini infeasibility aritmetis)
    if sum(deal.values()) > total_cap:
        alerts.append(('CRITICAL', 'CONSTRAINT',
                       f'Total deal {sum(deal.values()):,.0f} > total kapasitas {total_cap:,.0f} — pasti infeasible (Model 1 vs 4).'))
    for s in sites:
        if avail[s] - csb[s]['min'] < 0:
            alerts.append(('CRITICAL', 'CONSTRAINT',
                           f'{s}: available {avail[s]:,.0f} < min closing {csb[s]["min"]:,.0f} (Model 8 mustahil).'))
    # Price Ladder Guardrail (pra-MVP2): harga wajib monotonic naik terhadap band CV
    order = sorted(brands, key=lambda b: spec[b]['cv_max_typical'])
    for lo, hi in zip(order, order[1:]):
        if spec[hi]['base_price_simulasi'] < spec[lo]['base_price_simulasi']:
            alerts.append(('WARNING', 'PRICE',
                           f'Guardrail harga: {hi} (CV {spec[hi]["cv_max_typical"]}) lebih murah dari {lo} '
                           f'(CV {spec[lo]["cv_max_typical"]}) — cek input harga (anomali monotonic).'))
    C = {
        'sites': sites, 'brands': brands, 'available': avail, 'cv_site': cv,
        'deal': deal, 'deal_multiplier': mult,
        'allowance': manifest['allowance_matrix'],
        'cv_min': {b: spec[b]['cv_min_reject'] for b in brands},
        'cv_reject': {b: spec[b]['cv_min_reject'] for b in brands},  # batas reject asli (tak pernah ditimpa)
        'cv_max': {b: spec[b]['cv_max_typical'] for b in brands},
        'price': {b: spec[b]['base_price_simulasi'] for b in brands},  # MVP1: dummy; runtime: input tim komersial
        'cs_min': {s: csb[s]['min'] for s in sites},
        'cs_max': {s: csb[s]['max'] for s in sites},
        'total_capacity': total_cap, 'jetty_capacity': jetty,  # jetty = warning check saja
    }
    # --- Capacity total min/max = batas TOTAL SHIPMENT (hard limit bisnis) ---
    # Berlaku WALAU 'enabled' OFF: bila planner mengisi min/max, nilai itu WAJIB ditegakkan.
    if settings:
        cap = settings.get('capacity') or {}
        tmin, tmax = cap.get('total_min'), cap.get('total_max')
        if tmin not in (None, '', 0):
            C['cap_total_min'] = float(tmin)
        if tmax not in (None, ''):
            C['cap_total_max'] = float(tmax)
    # pre-solve sanity capacity — beri ALASAN jelas sebelum solver (orchestrator berhenti di ALERT)
    if C.get('cap_total_min', 0) > total_cap:
        alerts.append(('CRITICAL', 'CONSTRAINT',
                       f'Min total shipment {C["cap_total_min"]:,.0f} > total plan kapasitas {total_cap:,.0f} (mustahil).'))
    if C.get('cap_total_max') is not None:
        cmax = C['cap_total_max']; total_deal = sum(deal.values())
        # Max field = acuan utama. Satu-satunya yang mustahil: max di bawah total deal (deal wajib dipenuhi).
        # Batas stok cs_max TIDAK memaksa minimum shipment di sini (M9 dilewati saat max di-set).
        if cmax < total_deal:
            alerts.append(('CRITICAL', 'CONSTRAINT',
                           f'Max total shipment {cmax:,.0f} < total deal {total_deal:,.0f} — deal wajib dipenuhi, tak bisa di bawah max.'))

    # --- settings kualitas (opsional, di-gate 'enabled'): CV + TS/Ash/Na2O + quality reward ---
    if settings and settings.get('enabled'):
        cvs = settings.get('cv') or {}
        margin = float(settings.get('quality_margin_cv') or 0)   # buffer global: CV min >= reject + margin
        for b in brands:
            rej = spec[b]['cv_min_reject']
            mx = float((cvs.get(b) or {}).get('max', C['cv_max'][b]))
            floor = rej + margin                                 # buffer berlaku untuk SEMUA brand
            tbl = (cvs.get(b) or {}).get('min')                  # kolom per-brand boleh memperketat lebih tinggi
            if tbl is not None:
                floor = max(floor, float(tbl))
            # jaga feasibility: cv_min di antara reject dan (cv_max - 5)
            C['cv_min'][b] = max(rej, min(floor, mx - 5))
            C['cv_max'][b] = mx
        assay = settings.get('site_assay') or {}
        for dim in ('ts', 'ash', 'na2o'):
            if all(dim in (assay.get(s) or {}) for s in sites):
                C[f'{dim}_site'] = {s: float(assay[s][dim]) for s in sites}
                bd = settings.get(dim) or {}
                C[f'{dim}_max'] = {b: float((bd.get(b) or {}).get('max')) for b in brands if (bd.get(b) or {}).get('max') is not None}
                C[f'{dim}_min'] = {b: float((bd.get(b) or {}).get('min')) for b in brands if (bd.get(b) or {}).get('min')}
        C['quality_reward'] = float(settings.get('quality_reward') or 0)
    return C, alerts
