"""
Output utilities for the TSP demo.
- save_matrices: lưu distance và duration vào CSV (km, phút).
- save_report: báo cáo tổng kết các chiến lược thành CSV.
- create_map: tạo bản đồ Folium với LayerControl (checkbox) để so sánh.
"""

from __future__ import annotations
import csv
from pathlib import Path
import folium
from folium.plugins import PolyLineTextPath
from folium.features import DivIcon
from typing import List, Dict

import math

def save_matrices(
    places: List[Dict],
    distances: List[List[float]],
    durations: List[List[float]],
    output_dir: Path,
) -> None:
    """Lưu distance_matrix.csv (km) và duration_matrix.csv (phút).
    Các giá trị được làm tròn 2 chữ số thập phân.
    """
    # Distance (m -> km)
    dist_path = output_dir / "distance_matrix.csv"
    with dist_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id"] + [p["id"] for p in places])
        for p, row in zip(places, distances):
            writer.writerow([p["id"]] + [round(v / 1000.0, 2) if not math.isinf(v) else "" for v in row])
    # Duration (s -> phút)
    dur_path = output_dir / "duration_matrix.csv"
    with dur_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id"] + [p["id"] for p in places])
        for p, row in zip(places, durations):
            writer.writerow([p["id"]] + [round(v / 60.0, 2) if not math.isinf(v) else "" for v in row])
    print(f"Đã lưu ma trận: {dist_path.name}, {dur_path.name}")

def save_report(path: Path, results: Dict[str, Dict], places: List[Dict]) -> None:
    """Ghi báo cáo CSV với các cột:
    Chiến lược, Lộ trình, Tổng quãng đường (km), Tổng thời gian (phút), Giới hạn (phút), Trạng thái, Chi tiết chặng.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Chiến lược",
            "Lộ trình",
            "Tổng quãng đường (km)",
            "Tổng thời gian (phút)",
            "Giới hạn thời gian (phút)",
            "Trạng thái thời gian",
            "Chi tiết từng chặng",
        ])
        for name, data in results.items():
            route_str = " -> ".join(places[i]["id"] for i in data["order"])
            legs_str = " | ".join(
                f"{leg['from_id']}->{leg['to_id']} ({leg['dist_km']}km, {leg['dur_min']}p)"
                for leg in data["legs"]
            )
            max_limit = data.get("max_time_min") or "Không ràng buộc"
            if data.get("is_overtime"):
                status_str = f"⚠️ Vượt thời gian (Lố {data['overtime_min']} phút)"
            elif data.get("max_time_min"):
                status_str = "✅ Đạt chuẩn thời gian"
            else:
                status_str = "Không ràng buộc"
            writer.writerow([
                name,
                route_str,
                data["total_dist_km"],
                data["total_dur_min"],
                max_limit,
                status_str,
                legs_str,
            ])
    print(f"Đã lưu báo cáo: {path}")

def extract_maneuvers(geom_data: Dict, line_coords: List[List[float]]) -> List[Dict]:
    """Trích xuất các điểm rẽ, vòng xuyến từ OSRM steps hoặc tính toán từ góc ngoặt tọa độ."""
    maneuvers: List[Dict] = []
    
    # 1. Thử lấy từ OSRM steps nếu có
    legs = geom_data.get("legs", [])
    if legs:
        for leg in legs:
            for step in leg.get("steps", []):
                m = step.get("maneuver", {})
                m_type = m.get("type", "")
                modifier = m.get("modifier", "")
                loc = m.get("location", [])  # [lon, lat]
                name_st = step.get("name", "")
                if not loc or len(loc) < 2:
                    continue
                lat, lon = loc[1], loc[0]
                
                symbol, desc = "", ""
                if "roundabout" in m_type or "rotary" in m_type:
                    symbol, desc = "🔄", f"Vào vòng xuyến ({name_st})" if name_st else "Vào vòng xuyến"
                elif modifier in ("left", "sharp left"):
                    symbol, desc = "↰", f"Rẽ trái vào {name_st}" if name_st else "Rẽ trái"
                elif modifier in ("right", "sharp right"):
                    symbol, desc = "↱", f"Rẽ phải vào {name_st}" if name_st else "Rẽ phải"
                elif modifier == "slight left":
                    symbol, desc = "↖", f"Chếch sang trái vào {name_st}" if name_st else "Chếch sang trái"
                elif modifier == "slight right":
                    symbol, desc = "↗", f"Chếch sang phải vào {name_st}" if name_st else "Chếch sang phải"
                elif modifier == "uturn":
                    symbol, desc = "↩", "Quay đầu (U-turn)"
                elif m_type == "fork":
                    symbol, desc = "⑂", f"Đi theo nhánh vào {name_st}" if name_st else "Đi theo nhánh"
                
                if symbol:
                    dist_m = round(step.get("distance", 0))
                    maneuvers.append({
                        "lat": lat,
                        "lon": lon,
                        "symbol": symbol,
                        "desc": desc,
                        "dist_m": dist_m,
                    })

    # 2. Nếu không có OSRM steps (offline), tự động phát hiện góc ngoặt từ line_coords
    if not maneuvers and len(line_coords) >= 3:
        for i in range(1, len(line_coords) - 1):
            p1 = line_coords[i - 1]
            p2 = line_coords[i]
            p3 = line_coords[i + 1]
            
            # Tính góc chuyển hướng giữa hai đoạn thẳng liên tiếp
            b1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            b2 = math.atan2(p3[1] - p2[1], p3[0] - p2[0])
            diff = math.degrees(b2 - b1)
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            
            if 40 <= diff <= 140:
                maneuvers.append({
                    "lat": p2[0], "lon": p2[1],
                    "symbol": "↱",
                    "desc": f"Rẽ phải (ngoặt {abs(round(diff))}°)",
                    "dist_m": 0,
                })
            elif -140 <= diff <= -40:
                maneuvers.append({
                    "lat": p2[0], "lon": p2[1],
                    "symbol": "↰",
                    "desc": f"Rẽ trái (ngoặt {abs(round(diff))}°)",
                    "dist_m": 0,
                })
            elif abs(diff) > 140:
                maneuvers.append({
                    "lat": p2[0], "lon": p2[1],
                    "symbol": "↩",
                    "desc": "Quay đầu",
                    "dist_m": 0,
                })
    return maneuvers


def create_map(
    places: List[Dict],
    results: Dict[str, Dict],
    geometries: Dict[str, Dict],
    output_path: Path | None = None,
) -> folium.Map:
    """Tạo bản đồ Folium có LayerControl để bật/tắt các chiến lược.
    Mỗi chiến lược sẽ hiện:
    - Polyline màu riêng kèm mũi tên chỉ hướng ➤ theo từng chặng
    - Các ký tự chỉ dẫn chuyển hướng: rẽ trái ↰, rẽ phải ↱, vòng xuyến 🔄,...
    - Popup và tooltip thông tin chi tiết
    """
    map_center = [places[0]["lat"], places[0]["lon"]]
    # Sử dụng Google Maps làm nền: cực nhanh, tiếng Việt rõ ràng, không lo lỗi mạng hay API key
    m = folium.Map(
        location=map_center,
        zoom_start=15,
        control_scale=True,
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps",
    )
    # Thêm lớp bản đồ vệ tinh Google
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Google Vệ Tinh",
    ).add_to(m)

    # Đánh dấu các điểm kèm tên hiển thị thường trực (permanent tooltip)
    for idx, p in enumerate(places):
        is_depot = idx == 0
        tag = "[DEPOT] " if is_depot else f"[{p['id']}] "
        folium.Marker(
            location=[p["lat"], p["lon"]],
            tooltip=folium.Tooltip(
                f"<b>{tag}{p['name']}</b>",
                permanent=True,
                direction="top",
                offset=(0, -28),
                style="font-size: 12px; font-weight: bold; background: white; border: 1.5px solid #2c3e50; padding: 2px 6px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.25);"
            ),
            popup=f"<b>{p['name']}</b><br>{p['address']}",
            icon=folium.Icon(
                color="red" if is_depot else "blue",
                icon="home" if is_depot else "location-dot",
                prefix="fa"
            ),
        ).add_to(m)

    # Màu cho mỗi chiến lược
    style_map = {
        "Vét cạn (Backtracking)": {"color": "#28a745", "weight": 6},
        "Vét cạn (Brute Force)": {"color": "#28a745", "weight": 6},
        "Tham lam (Greedy)": {"color": "#dc3545", "weight": 5},
        "Quy hoạch động (DP)": {"color": "#ff8800", "weight": 5},
    }

    # Chỉ hiển thị chiến lược đầu tiên (Vét cạn) mặc định, các chiến lược khác để người dùng tự tick chọn so sánh
    for idx_strat, (name, data) in enumerate(results.items()):
        style = style_map.get(name, {"color": "gray", "weight": 4})
        is_default_show = (idx_strat == 0)
        fg = folium.FeatureGroup(name=name, show=is_default_show)
        
        # GeoJSON từ OSRM: [lon, lat] → Folium yêu cầu [lat, lon]
        line_coords = [[lat, lon] for lon, lat in geometries[name]["geometry"]["coordinates"]]
        
        # Chi tiết các chặng di chuyển
        legs_html = "<br>".join(
            f"{leg['from_name']} → {leg['to_name']}: <b>{leg['dist_km']} km</b>, <b>{leg['dur_min']} p</b>"
            for leg in data["legs"]
        )

        # Tạo popup với chi tiết chặng, số điểm phục vụ và thông tin thời gian
        k = data.get("visited_count", len(data["order"]) - 2)
        total_k = data.get("total_places", len(places) - 1)
        skipped_indices = data.get("skipped_indices", [])

        time_badge = ""
        tooltip_status = ""
        if data.get("max_time_min"):
            if skipped_indices:
                skipped_names = ", ".join(places[i]["name"] for i in skipped_indices)
                time_badge = f"""
                <div style='background-color:#e8f4fd; color:#0d6efd; border:1px solid #b6d4fe; padding:6px 8px; border-radius:4px; margin:6px 0; font-size:12px; line-height:1.4;'>
                    🎯 <b>PHỤC VỤ {k}/{total_k} ĐIỂM (≤ {data['max_time_min']} phút)</b><br>
                    Thời gian: <b>{data['total_dur_min']} phút</b> (Dư {data.get('remaining_time_min', 0)} phút)<br>
                    <span style='color:#dc3545;'>❌ Bỏ lại ca sau: {skipped_names}</span>
                </div>
                """
                tooltip_status = f" [{k}/{total_k} điểm - Dư {data.get('remaining_time_min', 0)}p]"
            elif data.get("is_overtime"):
                time_badge = f"""
                <div style='background-color:#fff3cd; color:#856404; border:1px solid #ffeeba; padding:5px 8px; border-radius:4px; margin:6px 0; font-size:12px; line-height:1.4;'>
                    ⚠️ <b>CẢNH BÁO THỜI GIAN:</b><br>
                    Tổng {data['total_dur_min']} phút vượt giới hạn {data['max_time_min']} phút (Lố <b>{data['overtime_min']} phút</b>)!
                </div>
                """
                tooltip_status = f" [⚠️ LỐ {data['overtime_min']}p]"
            else:
                time_badge = f"""
                <div style='background-color:#d4edda; color:#155724; border:1px solid #c3e6cb; padding:5px 8px; border-radius:4px; margin:6px 0; font-size:12px;'>
                    ✅ <b>Hoàn thành 100% ({k}/{total_k} điểm)</b> trong {data['total_dur_min']} phút (≤ {data['max_time_min']} phút)
                </div>
                """
                tooltip_status = " [✅ 100% Đạt chuẩn]"

        popup_html = (
            f"<div style='font-family:Arial; min-width:270px;'>"
            f"<h4 style='color:{style['color']};margin:0;'>{name}</h4>"
            f"<b>Quãng đường:</b> {data['total_dist_km']} km<br>"
            f"<b>Thời gian:</b> {data['total_dur_min']} phút<br>"
            f"{time_badge}"
            f"<hr style='margin:6px 0;'>"
            f"<b>Chi tiết chặng:</b><br>{legs_html}"
            f"</div>"
        )
        
        # 1. Vẽ đường line chính
        polyline = folium.PolyLine(
            line_coords,
            color=style["color"],
            weight=style["weight"],
            opacity=0.85,
            tooltip=f"{name}: {data['total_dist_km']} km, {data['total_dur_min']} p{tooltip_status}",
            popup=folium.Popup(popup_html, max_width=350),
        )
        polyline.add_to(fg)
        
        # 2. Thêm mũi tên chỉ hướng di chuyển tương phản màu trắng nổi bật trên nền line
        PolyLineTextPath(
            polyline,
            "      ➤      ",
            repeat=True,
            offset=5,
            attributes={
                "fill": "#ffffff",          # Màu trắng nổi bật trên đường màu
                "stroke": "#111111",        # Viền đen mỏng để sắc nét trên mọi nền
                "stroke-width": "0.6px",
                "font-weight": "900",
                "font-size": "15px",
            }
        ).add_to(fg)
        
        # 3. Thêm các ký tự rẽ, vòng xuyến (maneuver badges) thiết kế như biển báo
        maneuvers = extract_maneuvers(geometries.get(name, {}), line_coords)
        for mv in maneuvers:
            div_icon = folium.DivIcon(
                icon_size=(26, 26),
                icon_anchor=(13, 13),
                html=f"""
                <div style="
                    background-color: {style['color']};
                    color: #ffffff;
                    border: 2px solid #ffffff;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    font-weight: bold;
                    line-height: 22px;
                    text-align: center;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.45);
                ">{mv['symbol']}</div>
                """
            )
            dist_info = f" ({mv['dist_m']} m)" if mv.get("dist_m") else ""
            folium.Marker(
                location=[mv["lat"], mv["lon"]],
                icon=div_icon,
                tooltip=f"{mv['symbol']} {mv['desc']}{dist_info}",
                popup=f"<b>{mv['symbol']} {mv['desc']}</b><br>Chiến lược: {name}",
            ).add_to(fg)

        # 4. Đánh số thứ tự lộ trình lên từng điểm dừng được ghé thăm (1, 2, 3...)
        # Sử dụng màu vàng tươi (#ffc107) tương phản hoàn toàn với màu line (xanh, đỏ, cam) để dễ quan sát
        order = data["order"]  # vd: [0, 2, 1, 0]
        visited = order[:-1]   # bỏ điểm cuối (trùng depot), chỉ lấy các điểm đi qua
        for step_num, place_idx in enumerate(visited):
            p = places[place_idx]
            label = str(step_num + 1)   # bắt đầu từ 1
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=folium.DivIcon(
                    icon_size=(28, 28),
                    icon_anchor=(-12, 32),
                    html=f"""
                    <div style="
                        background-color: #ffc107;
                        color: #111111;
                        border: 2.5px solid #ffffff;
                        border-radius: 50%;
                        width: 26px;
                        height: 26px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 13px;
                        font-weight: 900;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.6);
                        font-family: Arial, sans-serif;
                        z-index: 9999;
                        position: relative;
                        cursor: pointer;
                    ">{label}</div>
                    """
                ),
                tooltip=f"{name} – Điểm dừng #{label}: {p['name']}",
            ).add_to(fg)

        # 5. Đánh dấu các điểm bị bỏ qua do giới hạn thời gian (Huy hiệu màu xám ✕)
        for skip_idx in skipped_indices:
            p = places[skip_idx]
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=folium.DivIcon(
                    icon_size=(26, 26),
                    icon_anchor=(-12, 32),
                    html=f"""
                    <div style="
                        background-color: #6c757d;
                        color: #ffffff;
                        border: 2px solid #ffffff;
                        border-radius: 50%;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 12px;
                        font-weight: 900;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.45);
                        font-family: Arial, sans-serif;
                        z-index: 9998;
                        position: relative;
                        cursor: pointer;
                    ">✕</div>
                    """
                ),
                tooltip=f"{name} – Bỏ qua (không đủ thời gian): {p['name']}",
            ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    if output_path is not None:
        m.save(str(output_path))
        print(f"Đã lưu bản đồ: {output_path}")
    return m

"""End of output.py"""
