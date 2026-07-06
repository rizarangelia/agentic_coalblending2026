---
id: KB-01
judul: Opening Stock
kategori: static_knowledge
tipe: definisi_data_source
kategori_ontologi: SOURCE
sumber_data: opening stock status.xls
angka_simulasi: true
keywords: [opening stock, stok awal, CPP, stockpile, survey, tongkang, vessel]
---

# Opening Stock

**Definisi:** Volume batubara aktual di stockpile masing-masing CPP pada awal bulan, ditambah batubara di atas tongkang & di atas vessel yang belum complete.

**Proses bisnis:**
- Per tanggal 1 tiap bulan, SEMUA CPP melaporkan volume masing-masing stockpile-nya.
- Volume diukur oleh Dept. Survey untuk mengetahui aktual volume batubara di CPP.
- Per tanggal 1, Shipping juga melaporkan volume batubara di atas tongkang & di atas vessel yang belum complete.

**Atribut per site/CPP:** Volume (MT) dan Kualitas CV (kcal/kg GAR).

**Contoh SIMULASI (bukan angka riil — angka riil diinjeksi runtime dari file input):**
| CPP | Volume (MT) | CV (GAR) |
|---|---|---|
| CPP Lati | 200.000 | 5.000 |
| CPP Binsua | 190.000 | 4.950 |
| CPP Sambarata | 250.000 | 5.900 |
| CPP Gurimbang | 50.000 | 3.880 |
| CPP BMO 3 | 10.000 | 3.350 |
| **Total** | **700.000** | |
