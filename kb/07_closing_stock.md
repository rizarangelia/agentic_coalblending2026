---
id: KB-07
judul: Closing Stock
kategori: static_knowledge
tipe: definisi_turunan
kategori_ontologi: SISA
angka_simulasi: true
keywords: [closing stock, stok akhir, demurrage, kontinuitas pengapalan, opening stock bulan depan]
---

# Closing Stock

**Definisi:** Sisa batubara yang tidak dijual di bulan tersebut, yang peruntukannya sebagai Opening Stock persiapan jualan bulan depan.

**Kenapa harus ada closing stock?** Agar pengapalan CONTINUE karena stok masih tersedia, sehingga risiko DEMURRAGE bisa diminimalisir.

**Formula (per site):** `Closing Stock = Available Product - Total Blending aktual site tersebut`.
Karena Total Blending dibatasi Plan Kapasitas Shipment (Model 4), maka secara agregat `Closing Stock total >= Available Product total - Plan Kapasitas Shipment total`.

**Konstrain:** Model 8 (closing >= min per site) dan Model 9 (closing <= max per site).

**Contoh SIMULASI:** Available 3.500.000 − Blending 3.000.000 = closing 500.000 (Lati 175rb, Binsua 150rb, Sambarata 100rb, Gurimbang 50rb, BMO 3 25rb). Band min–max per site: Lati 100–250rb, Binsua 60–150rb, Sambarata 100–250rb, Gurimbang 20–50rb, BMO 3 10–25rb.
