---
id: KB-12
judul: Kalender Operasional Bulanan
kategori: static_knowledge
tipe: proses_bisnis
angka_simulasi: false
keywords: [kalender, tanggal 1, tanggal 3-5, survey, mineplan, siklus bulanan, cadence]
---

# Kalender Operasional Bulanan (Cadence Data)

| Tanggal | Aktivitas | Pemilik | Output |
|---|---|---|---|
| Tgl 1 | Semua CPP melaporkan volume stockpile; diukur Dept. Survey. Shipping melaporkan volume di tongkang & vessel belum complete | CPP, Dept. Survey, Shipping | Opening Stock (QTY & QLT) |
| Tgl 3–5 | Mineplan mengirimkan plan volume & kualitas coal getting bulanan per site | Mineplan | Coal Getting Plan (QTY & QLT) |
| Awal bulan | Shipment Schedule (deal & belum deal) tersedia | Marketing/Shipping | Demand per brand |
| Setelah data lengkap | Generate blending -> Review -> Publikasi rekomendasi | AI System + Human Review | Blending plan & rekomendasi brand |

**Implikasi sistem:** Ingestion Agent baru boleh menjalankan optimisasi setelah keempat sumber data bulan berjalan tersedia dan lolos validasi skema.
