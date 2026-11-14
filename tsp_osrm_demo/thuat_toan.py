from __future__ import annotations
import math
from typing import List, Dict


# ============================================================
# 1. THUẬT TOÁN QUAY LUI (BACKTRACKING)
# ============================================================

def solve_backtracking(
    dist: List[List[float]],
    n: int,
    dur: List[List[float]] = None,
    max_time: float = None,
) -> List[int]:
    """
    Tìm lộ trình bằng thuật toán quay lui có cắt tỉa.

    Nếu không giới hạn thời gian, thuật toán xét các lộ trình
    đi qua toàn bộ địa điểm.

    Nếu có giới hạn thời gian, ưu tiên đi qua nhiều địa điểm nhất.
    Khi số địa điểm bằng nhau, chọn lộ trình có tổng quãng đường
    nhỏ hơn.
    """

    if n <= 1:
        return [0, 0] if n == 1 else []

    limit = max_time if (max_time is not None and max_time > 0) else math.inf
    time_mat = dur if dur is not None else dist

    best_k = 0
    best_cost = math.inf
    best_route = [0, 0]

    visited = [False] * n

    def dfs(u: int, count: int, d_cost: float, t_cost: float, path: List[int]):
        nonlocal best_k, best_cost, best_route

        # Kiểm tra thời gian nếu quay về kho từ vị trí hiện tại
        total_t = t_cost + time_mat[u][0]

        if total_t <= limit:
            k = count - 1
            total_d = d_cost + dist[u][0]

            # Cập nhật lộ trình tốt nhất
            if k > best_k or (k == best_k and total_d < best_cost):
                best_k = k
                best_cost = total_d
                best_route = path + [0]

        # Thử đi đến những địa điểm chưa được ghé thăm
        for v in range(1, n):
            if not visited[v] and t_cost + time_mat[u][v] + time_mat[v][0] <= limit:
                visited[v] = True

                dfs(
                    v,
                    count + 1,
                    d_cost + dist[u][v],
                    t_cost + time_mat[u][v],
                    path + [v]
                )

                visited[v] = False

    # Bắt đầu tìm kiếm từ kho (đỉnh 0)
    visited[0] = True
    dfs(0, 1, 0.0, 0.0, [0])

    return best_route


solve_brute_force = solve_backtracking


# ============================================================
# 2. THUẬT TOÁN THAM LAM (GREEDY)
# ============================================================

def solve_greedy(
    dist: List[List[float]],
    n: int,
    dur: List[List[float]] = None,
    max_time: float = None,
) -> List[int]:
    """
    Tìm lộ trình bằng thuật toán tham lam (Nearest Neighbor).

    Tại mỗi bước, chọn địa điểm gần nhất trong số các địa điểm
    chưa ghé thăm, đồng thời đảm bảo còn đủ thời gian quay về kho.
    """

    if n <= 1:
        return [0, 0] if n == 1 else []

    limit = max_time if (max_time is not None and max_time > 0) else math.inf
    time_mat = dur if dur is not None else dist

    unvisited = set(range(1, n))
    route = [0]
    cur_time = 0.0

    while unvisited:
        u = route[-1]

        # Lọc các địa điểm có thể đến và vẫn kịp quay về kho
        candidates = [
            v for v in unvisited
            if cur_time + time_mat[u][v] + time_mat[v][0] <= limit
        ]

        if not candidates:
            break

        # Chọn địa điểm gần nhất
        nxt = min(candidates, key=lambda v: dist[u][v])

        route.append(nxt)
        unvisited.remove(nxt)

        cur_time += time_mat[u][nxt]

    # Kết thúc lộ trình tại kho
    route.append(0)

    return route


# ============================================================
# 3. THUẬT TOÁN QUY HOẠCH ĐỘNG (DYNAMIC PROGRAMMING)
# ============================================================

def solve_dynamic_programming(
    dist: List[List[float]],
    n: int,
    dur: List[List[float]] = None,
    max_time: float = None,
) -> List[int]:
    """
    Giải bài toán bằng quy hoạch động Held-Karp.

    Sử dụng bitmask để biểu diễn tập các địa điểm đã đi qua.
    dp[mask][u] lưu thời gian nhỏ nhất để đi qua tập mask
    và kết thúc tại đỉnh u.
    """

    if n <= 1:
        return [0, 0] if n == 1 else []

    limit = max_time if (max_time is not None and max_time > 0) else math.inf
    time_mat = dur if dur is not None else dist
    INF = math.inf

    # Khởi tạo bảng quy hoạch động và bảng truy vết
    dp = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]

    dp[1][0] = 0.0

    # Duyệt các tập hợp địa điểm
    for mask in range(1, 1 << n):
        if not (mask & 1):
            continue

        for u in range(n):
            if dp[mask][u] == INF:
                continue

            # Thử mở rộng lộ trình đến đỉnh chưa đi qua
            for v in range(1, n):
                if not (mask & (1 << v)):
                    nxt_t = dp[mask][u] + time_mat[u][v]
                    new_mask = mask | (1 << v)

                    if nxt_t < dp[new_mask][v]:
                        dp[new_mask][v] = nxt_t
                        parent[new_mask][v] = u

    # Chọn trạng thái đi qua nhiều địa điểm nhất
    best_k = -1
    best_cost = INF
    best_mask = 1
    best_u = 0

    for mask in range(1, 1 << n):
        k = bin(mask).count("1") - 1

        if k < best_k:
            continue

        for u in range(n):
            if dp[mask][u] != INF and dp[mask][u] + time_mat[u][0] <= limit:
                total_t = dp[mask][u] + time_mat[u][0]

                if k > best_k or (k == best_k and total_t < best_cost):
                    best_k = k
                    best_cost = total_t
                    best_mask = mask
                    best_u = u

    # Truy vết để khôi phục lộ trình
    route = []
    mask = best_mask
    curr = best_u

    while curr != -1:
        route.append(curr)
        mask, curr = mask ^ (1 << curr), parent[mask][curr]

    return list(reversed(route)) + [0]


# ============================================================
# 4. CÁC HÀM HỖ TRỢ
# ============================================================

def compute_route_cost(order: List[int], dist: List[List[float]]) -> float:
    """Tính tổng quãng đường của lộ trình."""

    return (
        sum(dist[order[i]][order[i + 1]] for i in range(len(order) - 1))
        if len(order) > 1 else 0.0
    )


def evaluate_route(
    order: List[int],
    places: List[Dict],
    distances: List[List[float]],
    durations: List[List[float]],
    max_time_min: float = None,
) -> Dict:
    """
    Đánh giá lộ trình sau khi chạy thuật toán.

    Thống kê tổng quãng đường, thời gian di chuyển,
    số địa điểm đã ghé thăm và các địa điểm bị bỏ qua.
    """

    legs = []
    total_dist = 0.0
    total_dur = 0.0

    # Tính khoảng cách và thời gian của từng chặng
    for i in range(len(order) - 1):
        u, v = order[i], order[i + 1]

        dm = distances[u][v]
        ds = durations[u][v]

        total_dist += dm
        total_dur += ds

        legs.append({
            "from_id": places[u]["id"],
            "to_id": places[v]["id"],
            "from_name": places[u]["name"],
            "to_name": places[v]["name"],
            "dist_km": round(dm / 1000.0, 2),
            "dur_min": round(ds / 60.0, 1),
        })

    # Đổi đơn vị để hiển thị kết quả
    total_dist_km = round(total_dist / 1000.0, 2)
    total_dur_min = round(total_dur / 60.0, 1)

    # Lấy giới hạn thời gian từ thông tin kho nếu chưa truyền vào
    if max_time_min is None and places and places[0].get("max_minutes") is not None:
        max_time_min = float(places[0]["max_minutes"])

    # Xác định các địa điểm đã ghé thăm và bị bỏ qua
    visited = [idx for idx in order[:-1] if idx != 0]
    skipped = [
        idx for idx in range(1, len(places))
        if idx not in visited
    ]

    # Kiểm tra thời gian thực hiện lộ trình
    is_overtime = bool(max_time_min and total_dur_min > max_time_min)

    overtime = (
        round(total_dur_min - max_time_min, 1)
        if is_overtime else 0.0
    )

    remaining = (
        round(max_time_min - total_dur_min, 1)
        if (max_time_min and not is_overtime) else 0.0
    )

    return {
        "order": order,
        "legs": legs,
        "total_dist_km": total_dist_km,
        "total_dur_min": total_dur_min,
        "max_time_min": max_time_min,
        "is_overtime": is_overtime,
        "overtime_min": overtime,
        "remaining_time_min": remaining,
        "visited_count": len(visited),
        "total_places": len(places) - 1,
        "skipped_indices": skipped,
    }


# ============================================================
# 5. CÁC HÀM THUẬT TOÁN KHÁC
# ============================================================

