"""
API utilities for the TSP demo.
- load_places: đọc CSV, geocode nếu thiếu lat/lon.
- fetch_matrices: gọi OSRM Table API để lấy distance / duration.
- get_route_geometry: gọi OSRM Route API để lấy polyline GeoJSON.
"""

from __future__ import annotations
import csv
import math
import os
from pathlib import Path
from typing import List, Tuple, Dict
import requests

import json

# Tọa độ thực tế chuẩn xác của các địa điểm trung tâm TP.HCM
DEFAULT_COORDS = {
    "02 Công xã Paris, Quận 1, TP.HCM": (10.77984, 106.70001),  # Bưu điện Trung tâm TP.HCM
    "01 Công xã Paris, Quận 1, TP.HCM": (10.77978, 106.69902),  # Nhà thờ Đức Bà (cách bưu điện 100m)
    "Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM": (10.77255, 106.69805),  # Chợ Bến Thành
    "07 Công trường Lam Sơn, Quận 1, TP.HCM": (10.77663, 106.70317),  # Nhà hát Thành phố
    "Đường Trương Định, Phường Bến Thành, Quận 1, TP.HCM": (10.77484, 106.69315),  # Công viên Tao Đàn
}

# ---------------------------------------------------------------------------
# Helper: geocode address using ArcGIS (miễn phí, không cần API key).
# ---------------------------------------------------------------------------
def geocode_address(address: str, timeout: int = 30) -> Tuple[float, float]:
    """Trả về (lat, lon) cho một địa chỉ.
    Ưu tiên tra cache/danh bạ mặc định, sau đó mới gọi ArcGIS."""
    cache_path = Path(__file__).resolve().parent / "coords_cache.json"
    cache = {}
    if cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
            
    if address in cache:
        return float(cache[address][0]), float(cache[address][1])
    if address in DEFAULT_COORDS:
        return DEFAULT_COORDS[address]

    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    clean_addr = address.strip()

    # Chiến lược định vị thông minh:
    # 1. Thử tìm đúng địa chỉ người dùng nhập (hỗ trợ toàn bộ các tỉnh thành trên cả nước: Tây Ninh, Hà Nội, Đà Nẵng...)
    # 2. Nếu không tìm thấy và địa chỉ chưa có tên tỉnh/thành, thử dự phòng ghép thêm ", TP.HCM"
    search_queries = [clean_addr]
    if not any(k in clean_addr.lower() for k in ["tỉnh", "tp", "thành phố", "hcm", "hà nội"]):
        search_queries.append(f"{clean_addr}, TP.HCM")

    for query in search_queries:
        try:
            resp = requests.get(
                url,
                params={"SingleLine": query, "f": "json", "maxLocations": 1},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                loc = candidates[0]["location"]
                lat, lon = float(loc["y"]), float(loc["x"])
                cache[clean_addr] = [lat, lon]
                try:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return lat, lon
        except Exception:
            continue

    if clean_addr in DEFAULT_COORDS:
        return DEFAULT_COORDS[clean_addr]
    raise RuntimeError(f"Không thể định vị địa chỉ '{address}'. Gợi ý: Ghi kèm tên Phường/Xã hoặc Tỉnh/Thành phố.")

# ---------------------------------------------------------------------------
# Load places from CSV, tự động geocode những dòng chưa có lat/lon.
# ---------------------------------------------------------------------------
def load_places(path: Path, timeout: int = 30) -> List[Dict]:
    """Đọc CSV và trả về list các dict (id, name, address, lat, lon).
    CSV tối thiểu có các cột: id, name, address.
    Nếu có cột latitude/longitude thì dùng trực tiếp, nếu không sẽ geocode.
    """
    places: List[Dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = row["address"].strip()
            if row.get("latitude") and row.get("longitude"):
                lat = float(row["latitude"]) if row["latitude"] else None
                lon = float(row["longitude"]) if row["longitude"] else None
            else:
                print(f"Đang geocode: {row['name']} – {address} …")
                lat, lon = geocode_address(address, timeout=timeout)
            
            max_minutes = None
            if row.get("max_minutes") and str(row["max_minutes"]).strip():
                try:
                    max_minutes = float(str(row["max_minutes"]).strip())
                except ValueError:
                    max_minutes = None

            places.append({
                "id": row["id"].strip(),
                "name": row["name"].strip(),
                "address": address,
                "lat": lat,
                "lon": lon,
                "max_minutes": max_minutes,
            })
    if len(places) < 2:
        raise ValueError("Cần ít nhất 2 địa điểm (điểm xuất phát + ít nhất 1 điểm đến).")
    return places

# ---------------------------------------------------------------------------
# Build OSRM coordinates string: "lon,lat;lon,lat;…"
# ---------------------------------------------------------------------------
def _osrm_coords(places: List[Dict]) -> str:
    return ";".join(f"{p['lon']:.6f},{p['lat']:.6f}" for p in places)

# ---------------------------------------------------------------------------
# Fetch distance and duration matrices từ OSRM Table API.
# ---------------------------------------------------------------------------
def fetch_matrices(
    places: List[Dict],
    base_url: str,
    profile: str = "driving",
    timeout: int = 30,
) -> Tuple[List[List[float]], List[List[float]]]:
    """Trả về ma trận distance (m) và duration (s) cho toàn bộ cặp.
    Mặc định profile là 'driving'. Có thể đổi thành 'bike', 'motorcycle' (nếu server hỗ trợ).
    """
    coords = _osrm_coords(places)
    url = f"{base_url}/table/v1/{profile}/{coords}"
    print(f"Gọi OSRM Table API (profile: {profile}) …")
    resp = requests.get(url, params={"annotations": "distance,duration"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM Table API error: {data}")
    return data["distances"], data["durations"]

# ---------------------------------------------------------------------------
# Get full route geometry (polyline) từ OSRM Route API cho một thứ tự điểm.
# ---------------------------------------------------------------------------
def get_route_geometry(
    order: List[int],
    places: List[Dict],
    base_url: str,
    profile: str = "driving",
    timeout: int = 30,
) -> Dict:
    """Trả về dict route (OSRM GeoJSON) cho thứ tự `order`.
    ``order`` là danh sách chỉ số (bắt đầu 0).
    """
    coords = ";".join(f"{places[i]['lon']:.6f},{places[i]['lat']:.6f}" for i in order)
    url = f"{base_url}/route/v1/{profile}/{coords}"
    resp = requests.get(
        url,
        params={
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",  # Bật steps để lấy thông tin rẽ, vòng xuyến, tên đường
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM Route API error: {data}")
    return data["routes"][0]

"""End of api_calls.py"""

