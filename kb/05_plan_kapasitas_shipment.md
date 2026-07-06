---
id: KB-05
judul: Plan Kapasitas Shipment
kategori: static_knowledge
tipe: definisi_data_source
kategori_ontologi: DEMAND
angka_simulasi: true
keywords: [plan kapasitas shipment, jetty, crusher, BLC, outloading, maksimum kapal]
---

# Plan Kapasitas Shipment

**Definisi:** Rencana MAKSIMUM yang bisa dikapalkan dari masing-masing jetty.

**Pertimbangan penyusunannya:**
1. Available Product → plan kapasitas shipment < available product.
2. Kapasitas Processing & Outloading (crusher, BLC).
3. Minimum closing stock yang diharapkan.

**Penggunaan dalam model:** Konstrain Model 4 menggunakan TOTAL plan kapasitas shipment (grand total, bukan per site): `Total Blending keseluruhan <= Total Plan Kapasitas Shipment`. Angka per-jetty dipertahankan sebagai referensi/warning check di dashboard, bukan hard constraint per site.

**Contoh SIMULASI (per jetty, MT):** Lati 650.000 · Binsua 1.100.000 · Sambarata 450.000 · Gurimbang 660.000 · BMO 3 140.000 · **Total 3.000.000**
