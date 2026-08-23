"""MCP server — CoalBlend Dashboard (synthesizer).

Membungkus agents/synthesizer.py (Agent 4 — render HTML statis dari hasil solver,
dark theme "Control Tower", tanpa perlu Flask/login/session). Alurnya menyambung
dari 2 server sebelumnya:

    coalblend-data (ingest_coal_data*) -> coalblend-blend (run_blending) sudah
    menghitung skenario A/B/C -> coalblend-dashboard merender jadi 1 file HTML
    yang bisa langsung dibuka di browser.

Untuk kesederhanaan, tool di sini membangun ulang constraint + solve sendiri dari
ingested_data (constraint.build itu murah, bukan LP; solve tetap 1x per tool call)
supaya server ini tidak bergantung pada bentuk internal output blend_server.

Jalankan manual untuk tes cepat:
    python mcp_servers/dashboard_server.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents import constraint, optimizer, synthesizer  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

mcp = MCPServer("coalblend-dashboard")


def _load_manifest() -> dict:
    return json.loads((ROOT / 'config' / 'constraint_manifest.json').read_text(encoding='utf-8'))


def _load_calib() -> dict:
    p = ROOT / 'config' / 'calibration.json'
    if not p.exists():
        return {'approval': {}, 'reject': {}, 'total_keputusan': 0, 'skenario_favorit': '-', 'catatan': []}
    return json.loads(p.read_text(encoding='utf-8'))


def _resolve_out(out_path: str) -> Path:
    p = Path(out_path)
    if not p.is_absolute():
        p = (ROOT / out_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _solve(ingested_data, overrides):
    manifest = _load_manifest()
    C, alerts_pre = constraint.build(manifest, ingested_data, overrides)
    return manifest, C, alerts_pre


@mcp.tool()
def render_review_html(ingested_data: dict, overrides: dict = None,
                        out_path: str = "output/dashboard.html", meta: str = "") -> dict:
    """Solve 3 skenario (A/B/C) lalu render halaman review HTML statis (siap dibuka di
    browser, tanpa perlu server Flask/login) — sama seperti halaman /review di app.py,
    minus form approve/reject (itu aksi HITL yang tetap lewat app.py kalau dipakai resmi).

    ingested_data: dict hasil field "data" dari ingest_coal_data / ingest_coal_data_from_workbook.
    overrides (opsional): {'deal': {brand: v}, 'cs_min': {site: v}, 'cs_max': {site: v}}
    out_path: path file HTML output, relatif ke root project atau absolut.
    """
    if not ingested_data or ingested_data.get('status') != 'VALID':
        return {"status": "REJECTED", "reason": "ingested_data belum VALID — jalankan ingest_coal_data dulu."}

    _, C, alerts_pre = _solve(ingested_data, overrides)
    if any(lvl == 'CRITICAL' for lvl, _, _ in alerts_pre):
        return {"status": "PRESOLVE_FAIL",
                "alerts": [{"level": l, "agent": a, "message": m} for l, a, m in alerts_pre]}

    scenarios = optimizer.solve_scenarios(C)
    html = synthesizer.render_review(scenarios, C, alerts_pre, calib=_load_calib(),
                                      meta=meta or "baseline end-to-end · via MCP coalblend-dashboard")
    p = _resolve_out(out_path)
    p.write_text(html, encoding='utf-8')
    return {
        "status": "ok",
        "path": str(p),
        "scenarios_summary": [{"id": sc['id'], "nama": sc['nama'],
                                "revenue": sc['revenue'], "delta": sc.get('delta')} for sc in scenarios],
    }


@mcp.tool()
def render_report_html(ingested_data: dict, scenario_id: str, validator: str, catatan: str = "",
                        overrides: dict = None, out_path: str = None) -> dict:
    """Terbitkan Report Final & Rekomendasi Eksekusi untuk 1 skenario yang sudah dipilih
    (setara aksi "Approve" di /decide), sebagai file HTML statis siap kirim ke Marketing.

    scenario_id: 'A' | 'B' | 'C' (harus hasil solve yang Optimal, bukan INFEASIBLE).
    validator: nama/username orang yang menyetujui (untuk audit trail di dokumen).
    """
    if not ingested_data or ingested_data.get('status') != 'VALID':
        return {"status": "REJECTED", "reason": "ingested_data belum VALID — jalankan ingest_coal_data dulu."}

    _, C, alerts_pre = _solve(ingested_data, overrides)
    if any(lvl == 'CRITICAL' for lvl, _, _ in alerts_pre):
        return {"status": "PRESOLVE_FAIL",
                "alerts": [{"level": l, "agent": a, "message": m} for l, a, m in alerts_pre]}

    scenarios = optimizer.solve_scenarios(C)
    sc = next((s for s in scenarios if s['id'] == scenario_id), None)
    if sc is None:
        return {"status": "ERROR", "reason": f"scenario_id '{scenario_id}' tidak ditemukan. Pilihan: {[s['id'] for s in scenarios]}"}
    if sc['sol'] is None:
        return {"status": "ERROR", "reason": f"Opsi {scenario_id} INFEASIBLE — tidak bisa diterbitkan sebagai report final."}

    html = synthesizer.render_report(sc, C, run_id="mcp-manual", validator=validator, catatan=catatan)
    out_path = out_path or f"output/report_final_{scenario_id}.html"
    p = _resolve_out(out_path)
    p.write_text(html, encoding='utf-8')
    return {"status": "ok", "path": str(p), "scenario_id": scenario_id, "revenue": sc['revenue']}


if __name__ == "__main__":
    mcp.run()
