# MCP Servers — CoalBlend AI

MCP server yang membungkus agent-agent di `agents/` supaya bisa dipakai langsung dari
Claude Desktop (bukan lewat Flask app di `app.py`).

## 1. coalblend-data (`spreadsheet_server.py`)

Membungkus `agents/ingestion.py`. Tools yang diekspos:
- `list_data_files(directory)` — daftar file .csv/.xlsx/.xls di sebuah folder (default `fixtures`).
- `read_spreadsheet(path, max_rows)` — intip isi satu file sebelum di-ingest.
- `get_manifest()` — daftar site/brand valid + aturan blending dari `config/constraint_manifest.json`.
- `ingest_coal_data(opening_stock_path, coal_getting_path, demand_deal_path, plan_kapasitas_path)` —
  parse + validasi 4 file jadi JSON standar (status VALID/REJECTED + alerts). Kosongkan path
  (string kosong `""`) untuk pakai fixture simulasi pada slot itu.

## Instalasi

    cd mcp_servers
    pip install -r requirements.txt

## Daftarkan di Claude Desktop

Edit config Claude Desktop:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Tambahkan entry berikut (sesuaikan path Python & path project dengan lokasi di komputer Anda):

```json
{
  "mcpServers": {
    "coalblend-data": {
      "command": "C:\\Program Files\\Python312\\python.exe",
      "args": [
        "C:\\Users\\Riza\\Downloads\\coalblend_mvp_v3\\coalblend_mvp1\\mcp_servers\\spreadsheet_server.py"
      ]
    }
  }
}
```

Restart Claude Desktop. Cek ikon slider/tools di kolom chat — tool `list_data_files`,
`read_spreadsheet`, `get_manifest`, `ingest_coal_data` harus muncul di bawah server
`coalblend-data`.

## Tes manual tanpa Claude Desktop

    python -c "
    import sys; sys.path.insert(0, '.')
    from spreadsheet_server import list_data_files, ingest_coal_data
    print(list_data_files('../fixtures'))
    print(ingest_coal_data('', '', '', ''))
    "

## Selanjutnya

- `blend_server.py` — bungkus `agents/constraint.py` + `agents/optimizer.py` (terima output
  `ingest_coal_data`, jalankan solver CBC, kembalikan alokasi + revenue).
- `dashboard_server.py` — bungkus `agents/dashboard.py` (render `output/dashboard.html` dari
  hasil blending).
