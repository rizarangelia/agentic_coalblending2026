# MCP Servers — CoalBlend AI

MCP server yang membungkus agent-agent di `agents/` supaya bisa dipakai langsung dari
Claude Desktop (bukan lewat Flask app di `app.py`).

## 1. coalblend-data (`spreadsheet_server.py`)

Membungkus `agents/ingestion.py`. Tools yang diekspos:
- `list_data_files(directory)` — daftar file .csv/.xlsx/.xls di sebuah folder (default `fixtures`).
- `read_spreadsheet(path, max_rows)` — intip isi satu file sebelum di-ingest.
- `get_manifest()` — daftar site/brand valid + aturan blending dari `config/constraint_manifest.json`.
- `ingest_coal_data(opening_stock_path, coal_getting_path, demand_deal_path, plan_kapasitas_path)` —
  parse + validasi 4 file terpisah jadi JSON standar (status VALID/REJECTED + alerts). Kosongkan
  path (string kosong `""`) untuk pakai fixture simulasi pada slot itu.
- `ingest_coal_data_from_workbook(workbook_path)` — sama seperti di atas, tapi dari **1 file Excel
  konsolidasi** dengan 4 sheet (`opening_stock`, `coal_getting`, `demand_deal`, `plan_kapasitas`).
  Cocok untuk `fixtures/coalblend_input_template.xlsx` (lihat bawah).

## 2. coalblend-blend (`blend_server.py`)

Membungkus `agents/constraint.py` + `agents/optimizer.py` (LP PuLP/CBC, sudah tervalidasi —
baseline revenue **24.225.858,52**, sama persis dengan `tests/test_pipeline.py`). Input tool ini
adalah field `"data"` dari hasil `ingest_coal_data*` di atas — jadi alurnya agentic: Claude Desktop
panggil `coalblend-data` dulu untuk ambil & validasi data dari spreadsheet, baru hasilnya
dilewatkan ke `coalblend-blend` untuk dioptimasi. Tools:
- `get_baseline_info()` — angka baseline tervalidasi, untuk sanity-check hasil.
- `solve_single(ingested_data, overrides=None)` — 1x solve Model 1-9 (skenario Max Revenue murni).
- `run_blending(ingested_data, overrides=None)` — 3 skenario HITL (sama seperti halaman `/review`
  di app.py): **A** Max Revenue, **B** Quality-Safe (buffer CV +25), **C** Evakuasi Stok Site Kritis.
  `overrides` opsional: `{"deal": {brand: v}, "cs_min": {site: v}, "cs_max": {site: v}}`.

Kalau solver infeasible, `agents/optimizer.py` otomatis mendiagnosis relaksasi minimum yang
dibutuhkan per constraint (lihat alerts CRITICAL "butuh relaksasi minimum ±...").

## Spreadsheet template (simulasi data source)

`fixtures/coalblend_input_template.xlsx` — 1 workbook, 4 sheet, angka identik dengan
`fixtures/*_simulasi.csv` (baseline tervalidasi, jangan ubah kalau mau tetap bisa dibandingkan ke
`tests/test_pipeline.py`). Pakai ini sebagai baseline end-to-end sebelum diganti data real:

    spreadsheet template (4 sheet) → ingest_coal_data_from_workbook → run_blending → revenue

Untuk data real bulanan nanti: ganti isi sheet (jangan ubah nama sheet/kolom header — validator
`agents/ingestion.py` mencocokkan persis), atau tetap pakai 4 file terpisah lewat
`ingest_coal_data` sesuai nama file asli di `config/constraint_manifest.json` → `input_runtime`
("opening stock status.xls", "R3MMP.xls", "Sold shipment.xls", dst).

## Instalasi

    cd mcp_servers
    pip install -r requirements.txt

## Daftarkan di Claude Desktop

Edit config Claude Desktop:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Tambahkan kedua server (sesuaikan path Python & path project dengan lokasi di komputer Anda):

```json
{
  "mcpServers": {
    "coalblend-data": {
      "command": "C:\\Program Files\\Python312\\python.exe",
      "args": [
        "C:\\Users\\Riza\\Downloads\\coalblend_mvp_v3\\coalblend_mvp1\\mcp_servers\\spreadsheet_server.py"
      ]
    },
    "coalblend-blend": {
      "command": "C:\\Program Files\\Python312\\python.exe",
      "args": [
        "C:\\Users\\Riza\\Downloads\\coalblend_mvp_v3\\coalblend_mvp1\\mcp_servers\\blend_server.py"
      ]
    }
  }
}
```

Restart Claude Desktop. Cek ikon slider/tools di kolom chat — tool dari kedua server harus muncul.
Lalu tinggal minta di chat, misal: *"ambil data dari fixtures/coalblend_input_template.xlsx,
validasi, lalu jalankan blending 3 skenario"* — Claude akan otomatis memanggil
`ingest_coal_data_from_workbook` lalu `run_blending` berurutan.

## Tes manual tanpa Claude Desktop

    python -c "
    import sys; sys.path.insert(0, '.')
    import spreadsheet_server as sp, blend_server as bl
    ing = sp.ingest_coal_data_from_workbook('../fixtures/coalblend_input_template.xlsx')
    res = bl.run_blending(ing['data'])
    for sc in res['scenarios']:
        print(sc['id'], sc['nama'], sc['revenue'])
    "

## Selanjutnya

- `dashboard_server.py` — bungkus `agents/dashboard.py` (render `output/dashboard.html` dari
  hasil `run_blending`).
- Basis referensi yang sudah direview untuk server blending: repo
  `rizarangelia/agentic_folder_coalblend2` (solver LP standalone + xlsx sumber data
  `ghost_deck_generate_blending_using_AI.xlsx`, struktur sheet "Business Process" jadi acuan
  template di atas) dan `aicortex_app` (dari `mkt-intopsbc.it.com.zip`, Flask/WSGI edition dengan
  laycan scheduler). Solver final yang dipakai di `blend_server.py` tetap
  `agents/constraint.py` + `agents/optimizer.py` milik repo ini karena sudah lebih lengkap
  (infeasibility diagnoser, shadow price, 3 skenario HITL) dan itu yang divalidasi
  `tests/test_pipeline.py`.
