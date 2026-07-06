"""Orchestrator — Agentic Flow eksplisit (state graph ala LangGraph, tanpa dependensi).
Melengkapi baseline pseudocode dengan yang selama ini baru klaim: DATA LINEAGE & TRACEABILITY.

Graph:
  INGEST -> CONSTRAINT -> OPTIMIZE -> REVIEW(pause, human-in-the-loop) -> DECIDE -> [PUBLISH | CALIBRATE]
  Setiap node bisa keluar ke ALERT (terminal). Semua transisi + lineage ditulis ke output/trace.jsonl.
"""
import json, hashlib, datetime, uuid, pathlib

ROOT = pathlib.Path(__file__).parent.parent
TRACE = ROOT / 'output/trace.jsonl'

def _now(): return datetime.datetime.now().isoformat(timespec='seconds')

def _log(run_id, node, status, detail=None):
    with open(TRACE, 'a') as f:
        f.write(json.dumps({'run_id': run_id, 'ts': _now(), 'node': node,
                            'status': status, 'detail': detail or {}}, ensure_ascii=False) + '\n')

def lineage_of(files: dict, manifest: dict):
    """Sidik jari asal-usul data: hash tiap file input + versi manifest."""
    return {
        'files': {k: {'nama': fn, 'sha256': hashlib.sha256(b).hexdigest()[:16], 'bytes': len(b)}
                  for k, (b, fn) in files.items()},
        'manifest_versi': manifest.get('_meta', {}).get('versi', '?'),
        'baseline_validasi': manifest.get('_meta', {}).get('baseline_validasi_revenue'),
    }

def run(files, manifest, user, ingestion, constraint, optimizer):
    """Eksekusi graph sampai node REVIEW (pause untuk manusia). Return state lengkap."""
    state = {'run_id': uuid.uuid4().hex[:10], 'user': user, 'mulai': _now(),
             'lineage': lineage_of(files, manifest), 'alerts': [], 'node_terakhir': None}
    rid = state['run_id']
    _log(rid, 'START', 'ok', {'user': user, 'lineage': state['lineage']})

    # NODE 1 — INGEST
    data, a1 = ingestion.ingest(files, manifest)
    state['alerts'] += a1
    if data is None:
        state['node_terakhir'] = 'ALERT'
        _log(rid, 'INGEST', 'REJECTED', {'alerts': [m for _, _, m in a1]})
        return state
    state['data'] = data
    state['data'] = data
    _log(rid, 'INGEST', 'VALID', {'n_alerts': len(a1)})

    # NODE 2 — CONSTRAINT
    C, a2 = constraint.build(manifest, data)
    state['alerts'] += a2
    state['C'] = C
    if any(s == 'CRITICAL' for s, _, _ in a2):
        state['node_terakhir'] = 'ALERT'
        _log(rid, 'CONSTRAINT', 'PRESOLVE_FAIL', {'alerts': [m for _, _, m in a2]})
        return state
    _log(rid, 'CONSTRAINT', 'ok', {'total_deal': sum(C['deal'].values()),
                                   'total_kapasitas': C['total_capacity']})

    # NODE 3 — OPTIMIZE (multi-skenario)
    scenarios = optimizer.solve_scenarios(C)
    state['scenarios'] = scenarios
    ringkas = {sc['id']: (round(sc['revenue'], 2) if sc['revenue'] else 'INFEASIBLE') for sc in scenarios}
    if all(sc['sol'] is None for sc in scenarios):
        state['node_terakhir'] = 'ALERT'
        _log(rid, 'OPTIMIZE', 'ALL_INFEASIBLE', {'skenario': ringkas})
        return state
    _log(rid, 'OPTIMIZE', 'ok', {'skenario': ringkas})

    # NODE 4 — REVIEW (pause: menunggu keputusan manusia via /decide)
    state['node_terakhir'] = 'REVIEW'
    _log(rid, 'REVIEW', 'MENUNGGU_VALIDATOR', {'opsi': list(ringkas)})
    return state

def decide(run_id, user, opsi, aksi, catatan, revenue):
    """NODE 5 — DECIDE -> PUBLISH (approve) | CALIBRATE (reject). Dicatat di trace yang sama."""
    _log(run_id, 'DECIDE', aksi.upper(), {'validator': user, 'opsi': opsi,
                                          'catatan': catatan, 'revenue': revenue})
    _log(run_id, 'PUBLISH' if aksi == 'approve' else 'CALIBRATE', 'ok',
         {'opsi': opsi} if aksi == 'approve' else {'sinyal': catatan or '(tanpa catatan)'})

def trace_of(run_id):
    if not TRACE.exists(): return []
    return [json.loads(l) for l in TRACE.read_text().splitlines() if json.loads(l)['run_id'] == run_id]
