---
id: KB-08
judul: Matriks Blending Allowance
kategori: static_knowledge
tipe: aturan_kompatibilitas
angka_simulasi: false
keywords: [blending allowance, kompatibilitas site brand, mask, aturan blending]
---

# Matriks Blending Allowance (Site x Brand)

**Definisi:** Matriks kompatibilitas yang menentukan site mana boleh berkontribusi ke brand mana. Nilai "boleh" berarti kontribusi site dibatasi Available Product site tersebut; nilai "tidak" berarti kontribusi = 0 (Konstrain Model 5).

| Site | Eboni | Mahoni B | Agathis | Sungkai | Sungkai B | CV 4600 | CV 4200 | CV 3800 |
|---|---|---|---|---|---|---|---|---|
| Lati | TIDAK | boleh | boleh | boleh | boleh | boleh | boleh | TIDAK |
| Binsua | boleh | boleh | boleh | boleh | boleh | boleh | boleh | TIDAK |
| Sambarata | boleh | boleh | boleh | TIDAK | TIDAK | TIDAK | TIDAK | TIDAK |
| Gurimbang | TIDAK | TIDAK | TIDAK | TIDAK | boleh | boleh | boleh | boleh |
| BMO 3 | TIDAK | TIDAK | TIDAK | TIDAK | TIDAK | boleh | boleh | boleh |

**Intuisi:** Sambarata (CV tertinggi ~5900) hanya untuk 3 brand premium; Gurimbang (~3880) & BMO 3 (~3350) hanya untuk brand low-CV; Binsua paling fleksibel (semua brand KECUALI CV 3800). **CV 3800 HANYA boleh dari Gurimbang & BMO 3** (aturan v1.1 — keputusan bisnis yang meng-override tampilan sheet simulasi).
