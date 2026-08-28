"""Monitoring Realtime — Barge Corridor.

Model operasi nyata: TONGKANG (barge) berlayar dari tiap situs (Lati, Binungan, Sambarata,
Gurimbang, BMO3) menuju ANCHORAGE, lalu dibongkar ke KAPAL BUYER. Satu kapal buyer diisi
7–15 tongkang dari beberapa situs sekaligus — inilah proses BLENDING (mis. 2 Lati + 3
Gurimbang + 1 BMO3 + 3 Binungan → 1 kapal brand CV 4600).

Komposisi tongkang per kapal DITARIK DARI HASIL BLENDING NYATA (matriks site×brand solver),
jadi warna tongkang per situs memperlihatkan racikan blend yang benar. Posisi tongkang
bergerak deterministik terhadap waktu → polling berkala tampak realtime tanpa kredit API.
AIS asli (Data Docked) opsional server-side, tidak di-poll.
"""
import math, time, hashlib

# --- layout korridor (x,y di viewBox SVG 1000x560) ---------------------------
SITES_XY = {
    'Lati':      (140, 92),
    'Binungan':    (170, 205),
    'Sambarata': (120, 318),
    'Gurimbang': (185, 420),
    'BMO3':      (140, 505),
}
GEO = {  # perkiraan wilayah Berau, Kalimantan Timur (untuk tabel)
    'Lati':      (2.281, 117.472),
    'Binungan':    (2.155, 117.510),
    'Sambarata': (2.205, 117.418),
    'Gurimbang': (2.052, 117.560),
    'BMO3':      (1.965, 117.605),
}
CONFLUENCE = (600, 300)          # muara / pertemuan alur sungai
ANCHOR_SLOTS = [(855, 140), (890, 300), (855, 460)]   # slot kapal buyer di anchorage
ANCHOR_GEO = (2.150, 118.240)
PERIOD = 240.0                   # detik satu siklus voyage penuh (loop)
BARGE_CAP = 8000                 # kapasitas tongkang tipikal (MT), untuk hitung jumlah

# nama kapal & buyer per brand (contoh sesuai info lapangan)
SHIP_BY_BRAND = {
    'CV 4600':   ('MV Andhika Paramesti', 'PLTU Suralaya'),
    'Sungkai':   ('MV Meratus Zamrud',    'PLTU Indramayu'),
    'CV 4200':   ('MV Nusantara Jaya',    'PLTU Lontar'),
    'Mahoni B':  ('MV Sinar Borneo',      'PLTU Cirebon'),
    'Sungkai B': ('MV Karya Bahari',      'PLTU Labuan'),
    'Agathis':   ('MV Ocean Harmony',     'PLTU Tanjung Jati'),
    'Eboni':     ('MV Bulk Prosperity',   'PLTU Paiton'),
    'CV 3800':   ('MV Samudra Biru',      'PLTU Pelabuhan Ratu'),
}


def _seed(*parts):
    h = hashlib.sha1('|'.join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _point_on_path(pts, p):
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    total = sum(lens) or 1.0
    d = max(0.0, min(1.0, p)) * total
    for (a, b), L in zip(segs, lens):
        if d <= L or L == 0:
            t = (d / L) if L else 0.0
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            return x, y, ang
        d -= L
    return pts[-1][0], pts[-1][1], 0.0


def _lerp_geo(site, p):
    (la, lo), (aa, ao) = GEO.get(site, (2.15, 117.5)), ANCHOR_GEO
    return round(la + (aa - la) * p, 3), round(lo + (ao - lo) * p, 3)


def _distribute(n, weights):
    """Bagi n tongkang ke situs proporsional bobot (tonase alokasi), jumlah tetap n."""
    tot = sum(weights.values()) or 1.0
    raw = {s: n * w / tot for s, w in weights.items()}
    base = {s: int(math.floor(v)) for s, v in raw.items()}
    rem = n - sum(base.values())
    # sisa dibagi ke situs dengan pecahan terbesar
    for s, _ in sorted(raw.items(), key=lambda kv: kv[1] - base[kv[0]], reverse=True)[:max(0, rem)]:
        base[s] += 1
    return {s: c for s, c in base.items() if c > 0}


def _status(p):
    if p < 0.10:
        return 'Loading', 0.0
    if p < 0.86:
        return 'En-route', round(5.2 + _seed('spd', round(p, 2)) * 3.0, 1)
    if p < 0.94:
        return 'At Anchorage', 0.0
    return 'Discharging', 0.0


def snapshot(sites_state, alloc, brand_total, now=None, max_ships=3):
    """sites_state: list {site,util,cv,...}. alloc: {site:{brand:mt}}. brand_total:{brand:mt}.
    Kembalikan kapal buyer aktif di anchorage + tongkang bergerak per kapal (racikan blend)."""
    now = now or time.time()
    # situs
    sites_out = []
    for s in (sites_state or []):
        name = s['site']; x, y = SITES_XY.get(name, (150, 300)); la, lo = GEO.get(name, (2.15, 117.5))
        sites_out.append({'site': name, 'x': x, 'y': y, 'lat': la, 'lon': lo,
                          'util': s.get('util'), 'cv': s.get('cv'), 'ship': s.get('ship')})

    # kapal buyer = brand dengan shipment > 0, diurut tonase; top-N aktif di anchorage
    ranked = sorted([(b, t) for b, t in (brand_total or {}).items() if t and t > 0],
                    key=lambda kv: -kv[1])
    active = ranked[:max_ships]
    queued = ranked[max_ships:]

    ships, barges = [], []
    for i, (brand, tot) in enumerate(active):
        sx, sy = ANCHOR_SLOTS[i % len(ANCHOR_SLOTS)]
        name, buyer = SHIP_BY_BRAND.get(brand, (f'MV {brand}', 'Buyer'))
        # jumlah tongkang untuk kapal ini (7–15), dibagi per situs sesuai alokasi blend
        need = max(7, min(15, round(tot / 28000)))
        weights = {s: (alloc.get(s, {}) or {}).get(brand, 0) for s in SITES_XY}
        weights = {s: w for s, w in weights.items() if w and w > 0}
        per_site = _distribute(need, weights) if weights else {}
        need = sum(per_site.values()) or need
        arrived = 0
        for site, cnt in per_site.items():
            for k in range(cnt):
                off = _seed(brand, site, k)
                spd = 0.85 + _seed('v', brand, site, k) * 0.45
                p = ((now / PERIOD) * spd + off) % 1.0
                # jalur tongkang: situs -> muara -> slot kapal (scatter kecil dekat kapal)
                jx = sx + (_seed('jx', brand, site, k) - 0.5) * 40
                jy = sy + (_seed('jy', brand, site, k) - 0.5) * 46
                x2, y2, ang = _point_on_path([SITES_XY[site], CONFLUENCE, (jx, jy)], p)
                status, kn = _status(p)
                if status in ('At Anchorage', 'Discharging'):
                    arrived += 1
                cargo = int((weights[site] / cnt)) if cnt else BARGE_CAP
                cargo = max(6000, min(15000, cargo))
                vla, vlo = _lerp_geo(site, p)
                barges.append({
                    'id': f'TB-{site[:3].upper()}-{brand.replace(" ", "")[:5]}-{k+1:02d}',
                    'site': site, 'ship': name, 'buyer': buyer, 'brand': brand,
                    'x': round(x2, 1), 'y': round(y2, 1), 'heading': round(ang, 1),
                    'lat': vla, 'lon': vlo, 'status': status, 'speed_kn': kn,
                    'cargo_mt': cargo, 'progress': round(p, 3),
                    'eta_min': int((1 - p) * (PERIOD / 60)),
                })
        ships.append({'brand': brand, 'name': name, 'buyer': buyer, 'x': sx, 'y': sy,
                      'need_barges': need, 'arrived_barges': arrived,
                      'fill': round(arrived / need, 3) if need else 0, 'total_mt': int(tot)})

    active_barges = len(barges)
    enroute_mt = sum(b['cargo_mt'] for b in barges if b['status'] == 'En-route')
    loading = sum(1 for b in barges if b['status'] == 'Loading')
    discharging = sum(1 for b in barges if b['status'] == 'Discharging')
    at_anchor = sum(1 for b in barges if b['status'] == 'At Anchorage')
    return {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now)),
        'source': 'simulasi barge corridor (deterministik realtime · racikan dari blend solver)',
        'confluence': {'x': CONFLUENCE[0], 'y': CONFLUENCE[1]},
        'sites': sites_out, 'ships': ships, 'barges': barges,
        'queued': [{'brand': b, 'name': SHIP_BY_BRAND.get(b, (f'MV {b}', '-'))[0],
                    'buyer': SHIP_BY_BRAND.get(b, ('-', 'Buyer'))[1], 'total_mt': int(t)}
                   for b, t in queued],
        'kpi': {'barges': active_barges, 'ships': len(ships), 'enroute_mt': enroute_mt,
                'loading': loading, 'anchor': at_anchor, 'discharging': discharging},
    }
