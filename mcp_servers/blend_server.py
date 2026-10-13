"""MCP server — CoalBlend Blend (optimizer).

Membungkus agents/constraint.py + agents/optimizer.py (LP deterministik PuLP/CBC,
sudah tervalidasi baseline revenue 24.225.858,52) sebagai tools MCP. Input tool ini
adalah output dari tool ingest_coal_data / ingest_coal_data_from_workbook di
coalblend-data server — jadi alurnya agentic: Claude Desktop panggil coalblend-data
dulu untuk ambil data dari spreadsheet, lalu lewatkan hasilnya ke sini untuk di-blend.

Jalankan manual untuk tes cepat:
    python mcp_servers/blend_server.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents import constraint, optimizer  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

mcp = MCPServer("coalblend-blend")


def _load_manifest() -> dict:
    return json.loads((ROOT / 'config' / 'constraint_manifest.json').read_text(encoding='utf-8'))


def _alerts_out(alerts):
    return [{"level": lvl, "agent": agent, "message": msg} for lvl, agent, msg in alerts]


@mcp.tool()
def get_baseline_info() -> dict:
    """Info validasi baseline model ini — dipakai untuk sanity-check hasil optimize
    terhadap angka yang sudah diverifikasi (tests/test_pipeline.py)."""
    m = _load_manifest()
    return {
        "baseline_validasi_revenue": m['_meta']['baseline_validasi_revenue'],
        "versi_manifest": m['_meta']['versi'],
        "sites": m['sites'],
        "brands": m['brands'],
    }


@mcp.tool()
def solve_single(ingested_data: dict, overrides: dict = None) -> dict:
    """Solve Model 1-9 sekali (skenario Max Revenue murni, tanpa opsi HITL).

    ingested_data: dict hasil field "data" dari ingest_coal_data /
        ingest_coal_data_from_workbook (harus status VALID).
    overrides (opsional): {'deal': {brand: v}, 'cs_min': {site: v}, 'cs_max': {site: v}}
        — kalibrasi manual (tacit knowledge validator), sesuai agents/constraint.py.
    """
    if not ingested_data or ingested_data.get('status') != 'VALID':
        return {"status": "REJECTED", "reason": "ingested_data belum VALID — jalankan ingest_coal_data dulu."}

    manifest = _load_manifest()
    C, alerts_pre = constraint.build(manifest, ingested_data, overrides)
    if any(lvl == 'CRITICAL' for lvl, _, _ in alerts_pre):
        return {"status": "PRESOLVE_FAIL", "alerts": _alerts_out(alerts_pre), "solution": None}

    sol, alerts_solve = optimizer.solve(C)
    return {
        "status": "OPTIMAL" if sol else "INFEASIBLE",
        "alerts": _alerts_out(alerts_pre + alerts_solve),
        "solution": sol,
    }


@mcp.tool()
def run_blending(ingested_data: dict, overrides: dict = None) -> dict:
    """Solve 3 skenario kanonik untuk review HITL (Human-in-the-Loop), identik dengan
    alur /review di app.py:
      A Max Revenue (Baseline) · B Quality-Safe (buffer CV +25) · C Normalisasi Stok Antar-Site (closing 20–80% band).

    ingested_data: dict hasil field "data" dari ingest_coal_data /
        ingest_coal_data_from_workbook (harus status VALID).
    overrides (opsional): {'deal': {brand: v}, 'cs_min': {site: v}, 'cs_max': {site: v}}
    """
    if not ingested_data or ingested_data.get('status') != 'VALID':
        return {"status": "REJECTED", "reason": "ingested_data belum VALID — jalankan ingest_coal_data dulu."}

    manifest = _load_manifest()
    C, alerts_pre = constraint.build(manifest, ingested_data, overrides)
    if any(lvl == 'CRITICAL' for lvl, _, _ in alerts_pre):
        return {"status": "PRESOLVE_FAIL", "alerts": _alerts_out(alerts_pre), "scenarios": None}

    scenarios = optimizer.solve_scenarios(C)
    out = []
    for sc in scenarios:
        out.append({
            "id": sc['id'], "nama": sc['nama'], "desc": sc['desc'],
            "revenue": sc['revenue'], "delta_vs_baseline": sc.get('delta'),
            "n_reject_band": sc.get('n_reject'),
            "alerts": _alerts_out(sc['alerts']),
            "solution": sc['sol'],
        })
    return {"status": "ok", "alerts": _alerts_out(alerts_pre), "scenarios": out}


if __name__ == "__main__":
    mcp.run()
