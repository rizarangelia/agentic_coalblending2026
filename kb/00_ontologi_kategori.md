---
id: KB-00
judul: Ontologi Kategori Batubara dalam Proses Blending
kategori: static_knowledge
tipe: definisi_ontologi
angka_simulasi: false
keywords: [ontologi, source, demand, sisa, kategori, opening stock, coal getting, shipment deal, closing stock]
---

# Ontologi Kategori

Seluruh entitas volume batubara dalam proses blending bulanan diklasifikasikan ke dalam TIGA kategori:

1. **SOURCE (Sumber batubara yang akan dikapalkan)**
   - Opening Stock
   - Coal Getting Plan
   - Gabungan keduanya membentuk Available Product.

2. **DEMAND (Permintaan)**
   - Shipment Schedule Deal = demand yang SUDAH deal (kontraktual, wajib dipenuhi).
   - Free product / sisa product = demand yang BELUM deal (ruang optimisasi untuk direkomendasikan AI).

3. **SISA (Batubara yang tidak dikapalkan bulan ini)**
   - Closing Stock = sisa yang menjadi Opening Stock bulan berikutnya.

Aturan alur: SOURCE dikonversi melalui blending menjadi brand untuk memenuhi DEMAND; yang tidak terkonversi menjadi SISA (closing stock).
