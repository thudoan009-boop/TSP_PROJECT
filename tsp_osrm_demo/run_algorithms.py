"""
run_algorithms.py  –  Chạy & kiểm thử 3 thuật toán TSP offline (không cần OSRM).

Chức năng:
  1. Đọc ma trận khoảng cách/thời gian từ CSV (hoặc dùng dữ liệu mẫu).
  2. Chạy 3 thuật toán: Backtracking, Greedy, DP → in kết quả.
  3. Unit Test: kiểm tra chu trình hợp lệ, tính tối ưu, ràng buộc thời gian.
  4. Đo thời gian thực nghiệm (benchmark) của từng thuật toán.

Cách dùng:
  python run_algorithms.py            # Chạy thuật toán + benchmark
  python run_algorithms.py --test     # Chỉ chạy Unit Test
  python run_algorithms.py --alg dp   # Chỉ chạy DP
"""

from __future__ import annotations
import csv, math, time, sys
from pathlib import Path
from typing import List, Dict

# Đảm bảo import được module cùng thư mục
_dir = str(Path(__file__).resolve().parent)
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from thuat_toan import (
    solve_backtracking, solve_greedy, solve_dynamic_programming,
    compute_route_cost, evaluate_route,
)

# ── Dữ liệu mẫu (fallback khi chưa có CSV) ──────────────────
SAMPLE_MATRIX = [
    [0.0, 20.0, 42.0, 35.0],
    [20.0, 0.0, 30.0, 34.0],
    [42.0, 30.0, 0.0, 12.0],
    [35.0, 34.0, 12.0, 0.0],
]
SAMPLE_PLACES = [
    {"id": "DEPOT", "name": "Kho (DEPOT)", "address": "", "max_minutes": 120},
    {"id": "P1", "name": "Điểm 1", "address": "", "max_minutes": None},
    {"id": "P2", "name": "Điểm 2", "address": "", "max_minutes": None},
    {"id": "P3", "name": "Điểm 3", "address": "", "max_minutes": None},
]

# ── Bảng thuật toán ───────────────────────────────────────────
ALGORITHMS = {
    "backtracking": {
        "name": "Vét cạn (Backtracking)",
        "func": solve_backtracking,
        "exact": True,
        "time_O": "O((N-1)!)",
    },
    "greedy": {
        "name": "Tham lam (Greedy)",
        "func": solve_greedy,
        "exact": False,
        "time_O": "O(N²)",
    },
    "dp": {
        "name": "Quy hoạch động (DP Held-Karp)",
        "func": solve_dynamic_programming,
        "exact": True,
        "time_O": "O(N²·2ᴺ)",
    },
}


# ── Đọc file ─────────────────────────────────────────────────
def read_matrix(path: Path) -> List[List[float]]:
    """Đọc CSV ma trận, trả về List[List[float]]."""
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return [
        [float(v) if v.strip() else math.inf for v in row[1:]]
        for row in rows[1:]
    ]


def read_places(path: Path) -> List[Dict]:
    """Đọc danh sách địa điểm từ places.csv."""
    places = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            mx = row.get("max_minutes", "").strip()
            places.append({
                "id":   row.get("id", "").strip(),
                "name": row.get("name", "").strip(),
                "address": row.get("address", "").strip(),
                "lat":  float(row.get("latitude") or row.get("lat") or 0),
                "lon":  float(row.get("longitude") or row.get("lon") or 0),
                "max_minutes": float(mx) if mx else None,
            })
    return places


def get_max_time(places: List[Dict]) -> float | None:
    """Lấy ràng buộc thời gian từ depot (places[0])."""
    mx = places[0].get("max_minutes") if places else None
    return float(mx) if mx is not None else None


# ── Chạy 1 thuật toán & đo thời gian ────────────────────────
def run_one(key: str, dist, n, places, dur=None):
    """Chạy thuật toán, đo thời gian, in kết quả."""
    info = ALGORITHMS[key]
    max_time = get_max_time(places)

    # Đo thời gian (chạy 5 lần lấy trung bình)
    func = info["func"]
    order = func(dist, n, dur=dur, max_time=max_time)

    start = time.perf_counter()
    for _ in range(5):
        func(dist, n, dur=dur, max_time=max_time)
    ms = (time.perf_counter() - start) / 5 * 1000

    cost = compute_route_cost(order, dist)
    route_str = " → ".join(places[i]["name"] if i < len(places) else f"#{i}" for i in order)

    print(f"==== {info['name'].upper()} ({info['time_O']}) ====")
    print(f"  Chi phí: {cost:.2f}")
    print(f"  Lộ trình: {' '.join(map(str, order))}")
    print(f"  ({route_str})")
    print(f"  Thời gian thực nghiệm: {ms:.3f} ms")

    # Thông tin ràng buộc thời gian
    if dur is not None and max_time is not None:
        dist_m = [[v * 1000 for v in row] for row in dist]
        dur_s  = [[v * 60   for v in row] for row in dur]
        ev = evaluate_route(order, places, dist_m, dur_s, max_time_min=max_time)
        k, total = ev["visited_count"], ev["total_places"]
        if ev["skipped_indices"]:
            skipped = ", ".join(places[i]["name"] for i in ev["skipped_indices"])
            print(f"  🎯 Phục vụ {k}/{total} điểm (≤ {max_time}p) | Bỏ qua: {skipped}")
        elif ev["is_overtime"]:
            print(f"  ⚠️ Lố thời gian: {ev['total_dur_min']}p > {max_time}p (+{ev['overtime_min']}p)")
        else:
            print(f"  ✅ Đạt chuẩn: {ev['total_dur_min']}p ≤ {max_time}p (dư {ev['remaining_time_min']}p)")
    print()


# ── Unit Test ────────────────────────────────────────────────
def run_unit_tests(dist, places, dur=None) -> bool:
    """Kiểm thử tính đúng đắn cho 3 thuật toán."""
    n = len(dist)
    max_time = get_max_time(places)
    all_ok = True

    print("=" * 60)
    print("           BỘ UNIT TEST KIỂM THỬ THUẬT TOÁN")
    print("=" * 60)
    print(f"Ma trận N = {n}, Ràng buộc: {max_time} phút\n")

    # Kết quả tham chiếu (Backtracking = exact)
    ref = solve_backtracking(dist, n, dur=dur, max_time=max_time)
    ref_cost = compute_route_cost(ref, dist)
    ref_k = len(set(ref[1:-1]))

    tests = [
        ("Backtracking", solve_backtracking, True),
        ("Greedy",       solve_greedy,       False),
        ("DP",           solve_dynamic_programming, True),
    ]

    for i, (name, func, is_exact) in enumerate(tests, 1):
        order = func(dist, n, dur=dur, max_time=max_time)
        cost = compute_route_cost(order, dist)
        mid = order[1:-1]

        # Kiểm tra chu trình hợp lệ
        valid = (
            order[0] == 0 and order[-1] == 0
            and len(mid) == len(set(mid))
            and all(1 <= v < n for v in mid)
        )

        k = len(set(mid))
        ok = valid and (abs(cost - ref_cost) < 1e-6 if is_exact else cost < math.inf)
        status = "PASSED ✅" if ok else "FAILED ❌"
        extra = f"(Optimal)" if is_exact and ok else f"(gấp {cost/ref_cost:.2f}× optimal)" if ref_cost > 0 else ""

        print(f"  [TEST {i}] {name:15s}: {k}/{n-1} điểm | Chi phí = {cost:.4f} {extra} | {status}")
        if not ok:
            all_ok = False

    # Test ràng buộc thời gian
    if dur is not None and max_time is not None:
        time_mat = dur
        all_within = True
        for name, func, _ in tests:
            order = func(dist, n, dur=dur, max_time=max_time)
            t = sum(time_mat[order[i]][order[i+1]] for i in range(len(order)-1))
            if t > max_time + 1e-4:
                all_within = False
        status = "PASSED ✅" if all_within else "FAILED ❌"
        print(f"  [TEST 4] Ràng buộc thời gian ≤ {max_time}p: {status}")
        if not all_within:
            all_ok = False

    print("-" * 60)
    result = "TẤT CẢ PASSED 🎉" if all_ok else "CÓ TEST THẤT BẠI ⚠️"
    print(f"KẾT QUẢ: {result}")
    print("=" * 60 + "\n")
    return all_ok


# ── Benchmark ────────────────────────────────────────────────
def run_benchmark(dist, dur=None, max_time=None):
    """Đo thời gian thực nghiệm trên ma trận hiện tại."""
    n = len(dist)
    print("=" * 70)
    print("        BENCHMARK ĐỘ PHỨC TẠP THỰC NGHIỆM")
    print("=" * 70)
    print(f"{'Thuật toán':<30} | {'Lý thuyết':<15} | {'Thực nghiệm':>15}")
    print("-" * 70)

    for key, info in ALGORITHMS.items():
        func = info["func"]
        # Bỏ qua nếu N quá lớn
        if key == "backtracking" and n > 12:
            ms_str = "Bỏ qua (N>12)"
        elif key == "dp" and n > 18:
            ms_str = "Bỏ qua (N>18)"
        else:
            repeat = max(1, min(50, 100 // n))
            start = time.perf_counter()
            for _ in range(repeat):
                func(dist, n, dur=dur, max_time=max_time)
            ms = (time.perf_counter() - start) / repeat * 1000
            ms_str = f"{ms:.3f} ms"

        print(f"  {info['name']:<28} | {info['time_O']:<15} | {ms_str:>15}")

    print("=" * 70 + "\n")


# ── Main ─────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Chạy & kiểm thử 3 thuật toán TSP.")
    parser.add_argument("--test", action="store_true", help="Chỉ chạy Unit Test.")
    parser.add_argument("--alg", nargs="+", choices=list(ALGORITHMS), help="Chọn thuật toán.")
    args = parser.parse_args()

    # Đọc dữ liệu
    root = Path(__file__).resolve().parent
    dist_csv = root / "output" / "distance_matrix.csv"
    dur_csv  = root / "output" / "duration_matrix.csv"

    if dist_csv.exists():
        dist   = read_matrix(dist_csv)
        dur    = read_matrix(dur_csv) if dur_csv.exists() else None
        places = read_places(root / "places.csv")
        print(f"[INFO] Đọc ma trận từ {dist_csv.name} (N={len(dist)})\n")
    else:
        dist, dur, places = SAMPLE_MATRIX, None, SAMPLE_PLACES
        print("[INFO] Chưa có CSV – dùng dữ liệu mẫu (N=4)\n")

    n = len(dist)
    max_time = get_max_time(places)

    if args.test:
        run_unit_tests(dist, places, dur)
        return

    # In ma trận
    print(f"Ma trận khoảng cách ({n}×{n}):")
    for row in dist:
        print("  [" + " ".join(f"{v:7.2f}" for v in row) + " ]")
    print()

    # Chạy thuật toán
    for key in (args.alg or list(ALGORITHMS)):
        run_one(key, dist, n, places, dur)

    # Benchmark
    run_benchmark(dist, dur, max_time)


if __name__ == "__main__":
    main()
