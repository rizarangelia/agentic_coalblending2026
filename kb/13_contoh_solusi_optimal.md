---
id: KB-13
judul: Contoh Solusi Optimal Lengkap (Simulasi Tervalidasi)
kategori: static_knowledge
tipe: contoh_output_referensi
angka_simulasi: true
keywords: [contoh solusi, blending matrix, hasil optimal, kesimpulan, optimize, supply typical rejection, referensi output dashboard]
---

# Contoh Solusi Optimal (Data Simulasi — Baseline Validasi)

Solusi optimal Model 1-9 pada data simulasi. Total Revenue = **24.225.858,52** · Total shipment = 3.000.000 MT.
CATATAN: seluruh angka adalah SIMULASI untuk referensi struktur output & validasi solver, BUKAN untuk dikutip sebagai data riil.

## 1. Matriks Blending Optimal — x[site, brand] (MT)
| Site | Eboni | Mahoni B | Agathis | Sungkai | Sungkai B | CV 4600 | CV 4200 | CV 3800 | Total Site |
|---|---|---|---|---|---|---|---|---|---|
| Lati | 0 | 288.864 | 0 | 0 | 186.429 | 143.259 | 6.449 | 0 | 625.000 |
| Binungan | 29.474 | 241.663 | 260.000 | 508.864 | 0 | 0 | 0 | 0 | 1.040.000 |
| Sambarata | 250.526 | 249.474 | 0 | 0 | 0 | 0 | 0 | 0 | 500.000 |
| Gurimbang | 0 | 0 | 0 | 0 | 103.571 | 69.100 | 354.688 | 122.642 | 650.000 |
| BMO 3 | 0 | 0 | 0 | 0 | 0 | 47.642 | 0 | 137.358 | 185.000 |
| **Total Brand** | **280.000** | **780.000** | **260.000** | **508.864** | **290.000** | **260.000** | **361.136** | **260.000** | **3.000.000** |

## 2. Total Blending per Site vs Plan Kapasitas (referensi warning check)
Lati 625.000 / 650.000 · Binungan 1.040.000 / 1.100.000 · Sambarata 500.000 / 450.000 (MELEBIHI - contoh kasus warning per-jetty) · Gurimbang 650.000 / 660.000 · BMO 3 185.000 / 140.000 (MELEBIHI) · Total 3.000.000 / 3.000.000 (Model 4 binding).

## 3. Kualitas Tercapai per Brand (weighted average CV)
| Brand | CV Tercapai | Min (Reject) | Max (Typical) | Posisi |
|---|---|---|---|---|
| Eboni | 5.800 | 5.600 | 5.800 | di MAX (kualitas dimaksimalkan) |
| Mahoni B | 5.272 | 5.100 | 5.300 | dekat max (-28 dari typical) |
| Agathis | 4.950 | 4.900 | 5.100 | -150 dari typical |
| Sungkai | 4.950 | 4.800 | 5.000 | -50 dari typical |
| Sungkai B | 4.600 | 4.600 | 4.800 | DI BATAS REJECT (-200) |
| CV 4600 | 4.400 | 4.400 | 4.600 | DI BATAS REJECT (-200) |
| CV 4200 | 3.900 | 3.900 | 4.200 | DI BATAS REJECT (-300) |
| CV 3800 | 3.600 | 3.600 | 3.800 | DI BATAS REJECT (-200) |

Pola: kualitas dimaksimalkan pada Eboni & Mahoni B (nilai per-kcal tertinggi); brand lain disupply mendekati atau di batas reject.

## 4. Kesimpulan 1 — Rekomendasi Sales (baris Optimize = Total - Deal)
Di luar yang sudah deal (1,5 juta), sales harus menjual 1,5 juta dengan brand optimize:
Eboni 210.000 · Mahoni B 585.000 · Agathis 195.000 · Sungkai 278.864 · Sungkai B 0 · CV 4600 0 · CV 4200 36.136 · CV 3800 195.000 · **Total 1.500.000**

## 5. Kesimpulan 2 — Closing Stock per Site
Dari opening 700rb + coal getting 2,8jt, shipment 3jt -> closing 500rb:
Lati 175.000 · Binungan 150.000 · Sambarata 100.000 (di min) · Gurimbang 50.000 (di max) · BMO 3 25.000 (di max).

## 6. Revenue per Brand
Eboni 4.200.000 · Mahoni B 9.311.192 · Agathis 2.523.529 · Sungkai 4.030.200 · Sungkai B 1.667.500 · CV 4600 994.783 · CV 4200 1.006.023 · CV 3800 492.632 · **Total 24.225.858,52**

## Catatan aturan v1.1
Allowance CV 3800 diperketat: HANYA Gurimbang & BMO 3 (Binungan dicabut). Solusi optimal & revenue di halaman ini TIDAK berubah karena kontribusi Binungan→CV 3800 di optimum memang 0 (konstrain non-binding). Skenario turunan (quality-safe, evakuasi) BERUBAH — lihat expected_solution & kalkulasi skenario terbaru.

## Catatan solver
Solusi LP ini memiliki kemungkinan ALTERNATE OPTIMA (distribusi surplus antar brand tertentu dapat bergeser dengan revenue identik). Validasi implementasi cukup pada: nilai objective, total per brand pada binding constraints, dan status band CV — bukan kesamaan persis setiap sel matriks.
