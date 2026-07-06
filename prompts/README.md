# Workflow Agentic MVP 1
Trigger: user login → unggah 4 file di /input → pipeline:
Ingestion (validasi, REJECTED bila critical) → Constraint Manager (manifest + sanity pre-solve)
→ Blending Generator (CBC; decision gate: Optimal → Dashboard | Infeasible → Diagnoser → Alert)
→ Dashboard Synthesizer (HTML review + alerts).
LLM augmentation (opsional, fase berikut): narasi alert & ringkasan eksekutif via prompt persona di folder ini —
angka selalu dari solver, tidak pernah dari LLM.
