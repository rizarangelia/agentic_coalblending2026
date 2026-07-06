---
id: KB-04
judul: Shipment Schedule Deal
kategori: static_knowledge
tipe: definisi_data_source
kategori_ontologi: DEMAND
sumber_data: Sold shipment.xls
angka_simulasi: true
keywords: [shipment schedule, deal, buyer, vessel, ETA, brand, minimal dikapalkan, kontrak]
---

# Shipment Schedule Deal

**Definisi:** Data buyer, vessel, ETA, Brand, dan Volume yang SUDAH deal membeli batubara BC, beserta volume yang belum deal. Dalam konteks model blending, yang digunakan adalah Brand & Volume-nya.

**Makna dalam optimisasi:** Shipment Schedule Deal adalah MINIMAL yang harus dikapalkan per brand (Konstrain Model 1). Ini adalah demand kontraktual — wajib dipenuhi.

**Contoh SIMULASI (per brand, MT):**
Eboni 70.000 · Mahoni B 195.000 · Agathis 65.000 · Sungkai 230.000 · Sungkai B 290.000 · CV 4600 260.000 · CV 4200 325.000 · CV 3800 65.000 · **Total 1.500.000**
