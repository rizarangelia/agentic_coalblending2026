---
id: KB-09
judul: Kamus Spesifikasi Kualitas Brand (CV Band & Rejection)
kategori: static_knowledge
tipe: aturan_kualitas
angka_simulasi: false
keywords: [kualitas, CV band, min max CV, typical, rejection limit, reject, spesifikasi brand]
---

# Kamus Spesifikasi Kualitas Brand

**Semantik band CV per brand (kcal/kg GAR):**
- **Max = Typical = Base Kualitas Kontrak** — target kualitas kontraktual brand.
- **Min = REJECTION LIMIT (batas reject)** — batas bawah final. TIDAK ada toleransi tambahan di bawah Min (tidak ada pengurangan -50 atau sejenisnya).

| Brand | Min (Reject) | Max (Typical) | Selisih thd Typical |
|---|---|---|---|
| Eboni | 5.600 | 5.800 | -200 |
| Mahoni B | 5.100 | 5.300 | -200 |
| Agathis | 4.900 | 5.100 | -200 |
| Sungkai | 4.800 | 5.000 | -200 |
| Sungkai B | 4.600 | 4.800 | -200 |
| CV 4600 | 4.400 | 4.600 | -200 |
| CV 4200 | 3.900 | 4.200 | -300 |
| CV 3800 | 3.600 | 3.800 | -200 |

**Konstrain:** Weighted average CV hasil blending per brand harus berada dalam [Min, Max] (Model 6 & 7). Perhitungan: `CV_brand = SUMPRODUCT(tonase per site x CV site) / total tonase brand`.

**Perilaku optimum yang diharapkan:** kualitas dimaksimalkan pada brand bernilai per-kcal tertinggi (Eboni, Mahoni B); brand lain disupply mendekati atau di batas reject.
