"""Entrypoint Vercel (Python serverless / @vercel/python).

Vercel mendeteksi variabel WSGI bernama `app`. Filesystem serverless read-only kecuali
/tmp — jadi DATA_DIR diarahkan ke /tmp agar penulisan output/ & calibration tidak crash.
Konfigurasi env (DATABASE_URL, SECRET_KEY, DATADOCKED_API_KEY) diisi di dashboard Vercel.
"""
import os, sys, pathlib

# pastikan root repo ada di path agar `import app` menemukan app.py + paket agents/
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# arahkan tulisan runtime ke /tmp (satu-satunya lokasi writable di Vercel)
os.environ.setdefault('DATA_DIR', '/tmp')

from app import app  # noqa: E402  (WSGI app yang dijalankan Vercel)
