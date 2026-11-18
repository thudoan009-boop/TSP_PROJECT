"""
TSP Routing Demo – Orchestrator
Chiến lược: Vét cạn (Backtracking), Tham lam (Greedy), Quy hoạch động (DP Held-Karp)
Tích hợp:
- Đo lường và in Thời gian thực nghiệm (ms) của từng thuật toán.
- Bảng Benchmark so sánh độ phức tạp lý thuyết vs thực nghiệm.
- Xuất bản đồ tương tác Folium với Google Maps.
"""

from __future__ import annotations
import sys
import os
import time
from pathlib import Path
import folium

# --- Cấu hình chung -------------------------------------------------------
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
INPUT_FILE = ROOT / "places.csv"
OUTPUT_DIR = ROOT / "output"

# OSRM endpoint & profile (có thể ghi đè qua biến môi trường)
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL","http://localhost:5001").rstrip("/")
OSRM_PROFILE = os.getenv("OSRM_PROFILE", "driving")  # 'driving', 'bike', hoặc 'motorcycle'
REQUEST_TIMEOUT = 30

# --- Import các module tách biệt ------------------------------------------
from thuat_toan import (
    solve_backtracking,
    solve_greedy,
    solve_dynamic_programming,
    evaluate_route,
)
from api_calls import load_places, fetch_matrices, get_route_geometry
from output import save_matrices, create_map


def main() -> None:
    # Tạo thư mục output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1️⃣ Đọc địa điểm (tự động geocode nếu chưa có lat/lon)
    places = load_places(INPUT_FILE, timeout=REQUEST_TIMEOUT)
    print(f"Đã tải {len(places)} địa điểm:")
    for i, p in enumerate(places):
        print(f"  [{p['id']}] {p['name']} ({p['address']}) -> ({p['lat']:.5f}, {p['lon']:.5f})")

    # 2️⃣ Lấy ma trận distance / duration từ OSRM
    distances, durations = fetch_matrices(places, OSRM_BASE_URL, profile=OSRM_PROFILE, timeout=REQUEST_TIMEOUT)
    # Lưu ma trận để tái sử dụng
    save_matrices(places, distances, durations, OUTPUT_DIR)

    # 3️⃣ Chạy 3 chiến lược: Backtracking, Greedy, DP Held-Karp
    max_time_min = places[0].get("max_minutes")
    max_time_s = (float(max_time_min) * 60.0) if max_time_min is not None else None
    n = len(places)

    algorithms = {
        "Vét cạn (Backtracking)": {
            "func": solve_backtracking,
            "theory": "O((N-1)!)",
        },
        "Tham lam (Greedy)": {
            "func": solve_greedy,
            "theory": "O(N²)",
        },
        "Quy hoạch động (DP)": {
            "func": solve_dynamic_programming,
            "theory": "O(N²·2ᴺ)",
        },
    }

    results: dict[str, dict] = {}
    geometries: dict[str, dict] = {}
    runtimes_ms: dict[str, float] = {}

    for name, info in algorithms.items():
        func = info["func"]
        
        # Đo thời gian thực nghiệm bằng time.perf_counter()
        t_start = time.perf_counter()
        order = func(distances, n, dur=durations, max_time=max_time_s)
        runtime_ms = (time.perf_counter() - t_start) * 1000.0
        runtimes_ms[name] = runtime_ms

        # Đánh giá chi tiết mỗi lộ trình
        eval_data = evaluate_route(order, places, distances, durations, max_time_min=max_time_min)
        eval_data["runtime_ms"] = runtime_ms
        results[name] = eval_data

        # Lấy hình học thực tế từ OSRM để vẽ lên bản đồ
        geometries[name] = get_route_geometry(order, places, OSRM_BASE_URL, profile=OSRM_PROFILE, timeout=REQUEST_TIMEOUT)

        # In thông tin chi tiết trên console
        k = eval_data["visited_count"]
        total_k = eval_data["total_places"]
        print(f"\n{'='*20} {name} {'='*20}")
        if max_time_min:
            print(f"🎯 Điểm giao hoàn thành: {k}/{total_k} điểm (Ràng buộc ca: ≤ {max_time_min} phút)")
            if eval_data["skipped_indices"]:
                skipped_names = [places[i]["name"] for i in eval_data["skipped_indices"]]
                print(f"⚠️ Điểm bỏ lại (không đủ giờ): {', '.join(skipped_names)}")
            else:
                print(f"✅ Giao được đầy đủ tất cả {total_k} điểm!")
        print("Lộ trình:", " -> ".join(places[i]["name"] for i in order))
        for idx, leg in enumerate(eval_data["legs"], 1):
            print(f"  {idx}. {leg['from_name']} -> {leg['to_name']}: {leg['dist_km']} km, {leg['dur_min']} phút")
        print(f"==> TỔNG QUÃNG ĐƯỜNG:         {eval_data['total_dist_km']} km")
        print(f"==> TỔNG THỜI GIAN DI CHUYỂN: {eval_data['total_dur_min']} phút")
        print(f"==> THỜI GIAN THỰC NGHIỆM:    {runtime_ms:.3f} ms")
        if max_time_min:
            if eval_data.get("is_overtime"):
                print(f"  ⚠️ CẢNH BÁO: Lộ trình vượt thời gian cho phép!")
                print(f"     (Tổng {eval_data['total_dur_min']} phút > Giới hạn {eval_data['max_time_min']} phút => Lố {eval_data['overtime_min']} phút)")
            else:
                print(f"  ✅ ĐẠT YÊU CẦU: Thời gian {eval_data['total_dur_min']} phút ≤ Giới hạn {eval_data['max_time_min']} phút (Còn dư {eval_data['remaining_time_min']} phút).")

    # 4️⃣ In bảng Benchmark phân tích độ phức tạp thực nghiệm
    print("\n" + "=" * 76)
    print("                 BẢNG BENCHMARK ĐỘ PHỨC TẠP THỰC NGHIỆM")
    print("=" * 76)
    print(f"{'Thuật toán':<30} | {'Độ phức tạp lý thuyết':<22} | {'Thời gian thực nghiệm':>16}")
    print("-" * 76)
    for name, info in algorithms.items():
        ms_val = runtimes_ms.get(name, 0.0)
        print(f"  {name:<28} | {info['theory']:<22} | {ms_val:>13.3f} ms")
    print("=" * 76)

    # 5️⃣ Xuất bản đồ HTML
    create_map(places, results, geometries, OUTPUT_DIR / "route_map.html")
    print(f"\nHoàn tất! Mở file {OUTPUT_DIR / 'route_map.html'} để xem bản đồ so sánh.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        sys.exit(1)
