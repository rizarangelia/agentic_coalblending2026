---
id: KB-10
judul: Sembilan Konstrain Optimisasi (Model 1-9)
kategori: static_knowledge
tipe: business_rules
angka_simulasi: false
keywords: [model 1-9, konstrain, constraint, LP, linear programming, business rules]
---

# Model 1–9: Konstrain Optimisasi Blending

**Variabel keputusan:** x[site, brand] = tonase batubara dari site yang dialokasikan ke brand (>= 0).

| Model | Aturan | Formulasi |
|---|---|---|
| 1 | Total shipment per brand >= Shipment Schedule Deal (min) | sum_site(x) >= Deal_brand |
| 2 | Total shipment per brand <= max (4 x Deal) | sum_site(x) <= 4 x Deal_brand |
| 3 | Total blending per site <= Available Product site | sum_brand(x) <= Available_site |
| 4 | Total blending KESELURUHAN <= Total Plan Kapasitas Shipment | grand_total(x) <= TotalKapasitas (TOTAL-ONLY, bukan per site) |
| 5 | Blending mengikuti matriks Allowance | x[site,brand] = 0 jika tidak diizinkan |
| 6 | Weighted average CV per brand >= Min (reject) | sum(x*CV_site) >= MinCV x total_brand |
| 7 | Weighted average CV per brand <= Max (typical) | sum(x*CV_site) <= MaxCV x total_brand |
| 8 | Closing stock per site >= min | Available - sum_brand(x) >= min_site |
| 9 | Closing stock per site <= max | Available - sum_brand(x) <= max_site |

**Catatan penting hasil validasi:**
- Model 4 adalah TOTAL-ONLY. Kapasitas per-jetty TIDAK menjadi hard constraint; ia dipakai sebagai warning check di dashboard.
- Model 6 memakai Min apa adanya (batas reject). TIDAK ada toleransi -50.
- Multiplier Model 2 (4x Deal) adalah parameter kebijakan, dapat dikonfigurasi.
