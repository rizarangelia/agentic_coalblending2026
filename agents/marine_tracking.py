"""Marine Tracking — client tipis untuk Data Docked vessel/AIS API (datadocked.com).
Server-side only: API tidak mendukung CORS, dan API key TIDAK BOLEH pernah dikirim ke
browser/client-side (termasuk artifact statis). Semua pemanggilan harus lewat modul ini
di backend (app.py atau MCP server), lalu backend meneruskan hasil yang sudah disaring
ke frontend.

Kredensial dibaca dari environment variable DATADOCKED_API_KEY (lihat .env.example).
"""
import os
import requests

BASE_URL = "https://datadocked.com/api/vessels_operations"


def _api_key() -> str:
    key = os.environ.get("DATADOCKED_API_KEY")
    if not key:
        raise RuntimeError(
            "DATADOCKED_API_KEY belum di-set. Salin .env.example ke .env dan isi key-nya."
        )
    return key


def _headers() -> dict:
    return {"accept": "application/json", "x-api-key": _api_key()}


def get_my_credits() -> dict:
    """Sisa credit akun (endpoint gratis)."""
    r = requests.get(f"{BASE_URL}/my-credits", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def get_vessel_location(imo_or_mmsi: str) -> dict:
    """Posisi live 1 kapal (IMO atau MMSI). 1 credit, limit 100 req/min."""
    r = requests.get(
        f"{BASE_URL}/get-vessel-location",
        params={"imo_or_mmsi": imo_or_mmsi},
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_vessels_location_bulk(imo_or_mmsi_list: list[str]) -> dict:
    """Posisi live untuk hingga 50 kapal sekaligus. 1 credit/kapal, limit 15 req/min."""
    if len(imo_or_mmsi_list) > 50:
        raise ValueError("Maksimal 50 kapal per request (batas API).")
    r = requests.get(
        f"{BASE_URL}/get-vessels-location-bulk-search",
        params={"imo_or_mmsi_list": ",".join(imo_or_mmsi_list)},
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def get_vessel_info(imo_or_mmsi: str) -> dict:
    """Data lengkap kapal (nama, tipe, ukuran, dll). 5 credits, limit 15 req/min."""
    r = requests.get(
        f"{BASE_URL}/get-vessel-info",
        params={"imo_or_mmsi": imo_or_mmsi},
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_vessels_by_area(latitude: float, longitude: float, circle_radius: int = 50) -> dict:
    """Kapal dalam radius lingkaran dari titik pusat. 10 credits, limit 50 req/min.
    circle_radius dalam km, maksimal 50. latitude/longitude dibulatkan ke 1 desimal oleh API."""
    if circle_radius > 50:
        raise ValueError("circle_radius maksimal 50 km (batas API).")
    r = requests.get(
        f"{BASE_URL}/get-vessels-by-area",
        params={"latitude": latitude, "longitude": longitude, "circle_radius": circle_radius},
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def get_vessel_historical(imo_or_mmsi: str, days: int = 7) -> dict:
    """Historical track kapal N hari terakhir. 5 credits, limit 15 req/min."""
    r = requests.get(
        f"{BASE_URL}/get-vessel-historical-data",
        params={"imo_or_mmsi": imo_or_mmsi, "days": days},
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # smoke test manual: python agents/marine_tracking.py
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    import json
    print(json.dumps(get_vessel_location("9811000"), indent=2))
