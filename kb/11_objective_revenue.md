---
id: KB-11
judul: Fungsi Objective - Maksimasi Revenue
kategori: static_knowledge
tipe: objective_function
angka_simulasi: true
keywords: [objective, revenue, base price, base kualitas kontrak, prorate CV, maksimasi]
---

# Objective: Maksimasi Total Revenue

**Formula per brand:** `Revenue_brand = (Total Energi brand / Base Kualitas Kontrak) x Base Price`
di mana Total Energi brand = SUMPRODUCT(tonase per site x CV site). Ekuivalen dengan: `Base Price x Volume x (CV aktual / CV kontrak)` — harga di-prorate proporsional terhadap CV aktual.

**Objective total:** maksimalkan sum Revenue seluruh brand.

**Contoh SIMULASI base price (dummy, MVP 1):** Eboni 15 · Mahoni B 12 · Agathis 10 · Sungkai 8 · Sungkai B 6 · CV 4600 4 · CV 4200 3 · CV 3800 2. Base kualitas kontrak = Max/Typical CV brand.

**Baseline validasi (data simulasi, Model 1-9 final, allowance v1.1):** Total Revenue optimal = **24.225.858,52** dengan total shipment 3.000.000 MT. Setiap perubahan implementasi solver harus mereproduksi angka ini pada data simulasi.

**Nilai per kcal tertinggi:** Eboni (15/5800), lalu Mahoni B (12/5300) — inilah alasan optimizer mendorong coal high-CV ke brand premium hingga batas Max, dan menekan brand lain ke batas reject.

**Catatan MVP:** Harga di MVP 1 adalah dummy; optimisasi harga dinamis (higher price - higher CV) adalah scope MVP 2.
