"""
app.py - Website Tối ưu hóa Lộ trình Giao hàng (TSP - OSRM)
Hiện thực hóa đầy đủ theo Software Requirements Specification (SRS) v1.1:
- FR-01: Nguồn địa điểm (Nhập thủ công hoặc Preset Demo 5, 8, 12 điểm).
- FR-02: Nhập giới hạn thời gian bằng Ô SỐ (TUYỆT ĐỐI KHÔNG DÙNG SLIDER), để trống = không giới hạn.
- FR-03: Tối ưu hóa bằng 3 thuật toán: Backtracking, Greedy, Held-Karp DP.
- FR-04: Bản đồ tương tác Folium (LayerControl, số thứ tự vàng hổ phách #ffc107, dấu bỏ qua ✕).
- FR-05: Bảng Key Metrics chi tiết từng thuật toán.
- FR-06: Terminal Output Console nền tối hiển thị log thực thi thực tế + Tải file log.
- FR-07: Bảng phân tích độ phức tạp thời gian & không gian.
- FR-08: Runtime Benchmark đo bằng time.perf_counter() kèm biểu đồ Plotly.
"""

from __future__ import annotations
import sys
import os
import time
import math
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import streamlit as st
import folium
import plotly.graph_objects as go
import pandas as pd

# Thiết lập đường dẫn thư mục gốc
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tái sử dụng các module hiện có
from thuat_toan import (
    solve_backtracking,
    solve_greedy,
    solve_dynamic_programming,
    evaluate_route,
)
from api_calls import (
    geocode_address,
    fetch_matrices,
    get_route_geometry,
    DEFAULT_COORDS,
)
from output import create_map

# ==============================================================================
# CẤU HÌNH TRANG STREAMLIT & GIAO DIỆN CHUYÊN NGHIỆP
# ==============================================================================
st.set_page_config(
    page_title="Tối ưu hóa Lộ trình Giao hàng (TSP - OSRM)",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS cho phong cách hiện đại, bảng điều khiển và terminal
st.markdown(
    """
    <style>
    /* Font & container styling */
    .main-title {
        font-size: 26px;
        font-weight: 800;
        color: #1a202c;
        margin-bottom: 2px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .sub-title {
        font-size: 14px;
        color: #718096;
        margin-bottom: 16px;
    }
    /* Metric Cards */
    .metric-card {
        background: #ffffff;
        border-radius: 8px;
        padding: 14px 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .metric-header {
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-val {
        font-size: 20px;
        font-weight: 800;
        color: #2b6cb0;
    }
    .badge-success {
        background-color: #c6f6d5;
        color: #22543d;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-warn {
        background-color: #feebc8;
        color: #744210;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-skip {
        background-color: #e2e8f0;
        color: #4a5568;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    /* Terminal Console Style */
    .terminal-container {
        background-color: #1a1a1a;
        color: #00ff66;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.5;
        padding: 14px;
        border-radius: 6px;
        max-height: 280px;
        overflow-y: auto;
        border: 1px solid #333333;
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.7);
    }
    .term-info { color: #38bdf8; }
    .term-ok   { color: #4ade80; font-weight: bold; }
    .term-warn { color: #facc15; }
    .term-err  { color: #f87171; font-weight: bold; }
    .term-res  { color: #e879f9; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# DỮ LIỆU PRESET DEMO (FR-01B) - TỌA ĐỘ THỰC TẾ CHUẨN XÁC TẠI TP.HCM
# ==============================================================================
PRESETS = {
    "preset_small": {
        "title": "Quy mô Nhỏ (5 điểm) — Trung tâm Quận 1",
        "description": "Thử nghiệm chuẩn: Depot Bưu điện TP và 4 điểm tham quan nội ô.",
        "default_time": "7.0",
        "places": [
            {"id": "DEPOT", "name": "Bưu điện Trung tâm TP.HCM", "address": "02 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77984, "lon": 106.70001},
            {"id": "P1", "name": "Nhà thờ Đức Bà", "address": "01 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77978, "lon": 106.69902},
            {"id": "P2", "name": "Chợ Bến Thành", "address": "Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77255, "lon": 106.69805},
            {"id": "P3", "name": "Nhà hát Thành phố", "address": "07 Công trường Lam Sơn, Quận 1, TP.HCM", "lat": 10.77663, "lon": 106.70317},
            {"id": "P4", "name": "Công viên Tao Đàn", "address": "Đường Trương Định, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77484, "lon": 106.69315},
        ],
    },
    "preset_medium": {
        "title": "Quy mô Vừa (8 điểm) — Mở rộng Quận 1 & Quận 3",
        "description": "Thêm Dinh Độc Lập, Hồ Con Rùa, Bảo tàng Chứng tích Chiến tranh, Chợ Tân Định.",
        "default_time": "25.0",
        "places": [
            {"id": "DEPOT", "name": "Bưu điện Trung tâm TP.HCM", "address": "02 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77984, "lon": 106.70001},
            {"id": "P1", "name": "Nhà thờ Đức Bà", "address": "01 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77978, "lon": 106.69902},
            {"id": "P2", "name": "Dinh Độc Lập", "address": "135 Nam Kỳ Khởi Nghĩa, Bến Thành, Quận 1, TP.HCM", "lat": 10.77700, "lon": 106.69530},
            {"id": "P3", "name": "Hồ Con Rùa", "address": "Vòng xoay Công trường Quốc Tế, Quận 3, TP.HCM", "lat": 10.78280, "lon": 106.69610},
            {"id": "P4", "name": "Bảo tàng Chứng tích Chiến tranh", "address": "28 Võ Văn Tần, Phường 6, Quận 3, TP.HCM", "lat": 10.77940, "lon": 106.69220},
            {"id": "P5", "name": "Chợ Tân Định", "address": "336 Hai Bà Trưng, Tân Định, Quận 1, TP.HCM", "lat": 10.79030, "lon": 106.69080},
            {"id": "P6", "name": "Chợ Bến Thành", "address": "Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77255, "lon": 106.69805},
            {"id": "P7", "name": "Thảo Cầm Viên Sài Gòn", "address": "02 Nguyễn Bỉnh Khiêm, Bến Nghé, Quận 1, TP.HCM", "lat": 10.78760, "lon": 106.70520},
        ],
    },
    "preset_large": {
        "title": "Quy mô Lớn (12 điểm) — Nội thành TP.HCM (Q1, Q3, Q4, Bình Thạnh)",
        "description": "Thêm Landmark 81, Bến Nhà Rồng, Chợ Lớn. Khuyến nghị chạy Greedy & DP.",
        "default_time": "50.0",
        "places": [
            {"id": "DEPOT", "name": "Bưu điện Trung tâm TP.HCM", "address": "02 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77984, "lon": 106.70001},
            {"id": "P1", "name": "Nhà thờ Đức Bà", "address": "01 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77978, "lon": 106.69902},
            {"id": "P2", "name": "Dinh Độc Lập", "address": "135 Nam Kỳ Khởi Nghĩa, Bến Thành, Quận 1, TP.HCM", "lat": 10.77700, "lon": 106.69530},
            {"id": "P3", "name": "Hồ Con Rùa", "address": "Vòng xoay Công trường Quốc Tế, Quận 3, TP.HCM", "lat": 10.78280, "lon": 106.69610},
            {"id": "P4", "name": "Bảo tàng Chứng tích Chiến tranh", "address": "28 Võ Văn Tần, Phường 6, Quận 3, TP.HCM", "lat": 10.77940, "lon": 106.69220},
            {"id": "P5", "name": "Chợ Tân Định", "address": "336 Hai Bà Trưng, Tân Định, Quận 1, TP.HCM", "lat": 10.79030, "lon": 106.69080},
            {"id": "P6", "name": "Chợ Bến Thành", "address": "Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77255, "lon": 106.69805},
            {"id": "P7", "name": "Nhà hát Thành phố", "address": "07 Công trường Lam Sơn, Quận 1, TP.HCM", "lat": 10.77663, "lon": 106.70317},
            {"id": "P8", "name": "Công viên Tao Đàn", "address": "Đường Trương Định, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77484, "lon": 106.69315},
            {"id": "P9", "name": "Thảo Cầm Viên Sài Gòn", "address": "02 Nguyễn Bỉnh Khiêm, Bến Nghé, Quận 1, TP.HCM", "lat": 10.78760, "lon": 106.70520},
            {"id": "P10", "name": "Bến Nhà Rồng", "address": "01 Nguyễn Tất Thành, Phường 12, Quận 4, TP.HCM", "lat": 10.76810, "lon": 106.70680},
            {"id": "P11", "name": "Landmark 81", "address": "720A Điện Biên Phủ, Phường 22, Bình Thạnh, TP.HCM", "lat": 10.79500, "lon": 106.72190},
        ],
    },
}

# ==============================================================================
# KHỞI TẠO STATE
# ==============================================================================
if "manual_depot" not in st.session_state:
    st.session_state.manual_depot = {
        "name": "Bưu điện Trung tâm TP.HCM (DEPOT)",
        "address": "02 Công xã Paris, Quận 1, TP.HCM",
        "lat": 10.77984,
        "lon": 106.70001,
    }

if "manual_stops" not in st.session_state:
    st.session_state.manual_stops = [
        {"name": "Nhà thờ Đức Bà", "address": "01 Công xã Paris, Quận 1, TP.HCM", "lat": 10.77978, "lon": 106.69902},
        {"name": "Chợ Bến Thành", "address": "Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM", "lat": 10.77255, "lon": 106.69805},
        {"name": "Nhà hát Thành phố", "address": "07 Công trường Lam Sơn, Quận 1, TP.HCM", "lat": 10.77663, "lon": 106.70317},
    ]

if "optimization_results" not in st.session_state:
    st.session_state.optimization_results = None

# ==============================================================================
# GIAO DIỆN CHÍNH: 2 CỘT (ĐIỀU KHIỂN & KẾT QUẢ)
# ==============================================================================
st.markdown("<div class='main-title'>🚚 Tối ưu hóa Lộ trình Giao hàng TP.HCM</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Hệ thống so sánh 3 thuật toán <b>Backtracking</b>, <b>Greedy</b>, <b>DP Held-Karp</b> trên mạng đường OSRM với ràng buộc thời gian ca làm việc.</div>", unsafe_allow_html=True)

col_ctrl, col_main = st.columns([1, 2], gap="large")

# ------------------------------------------------------------------------------
# CỘT TRÁI (COL_CTRL): THIẾT LẬP DỮ LIỆU & RÀNG BUỘC
# ------------------------------------------------------------------------------
with col_ctrl:
    st.subheader("⚙️ Thiết lập Bài toán")
    
    # FR-01: Chọn một trong hai chế độ
    input_mode = st.radio(
        "Nguồn dữ liệu địa điểm:",
        options=["Preset Demo", "Nhập địa chỉ thủ công"],
        horizontal=True,
    )
    
    places_to_run: List[Dict] = []
    default_time_str = ""
    
    if input_mode == "Preset Demo":
        st.markdown("**Chọn bộ dữ liệu mẫu có sẵn:**")
        preset_key = st.selectbox(
            "Danh mục Preset:",
            options=list(PRESETS.keys()),
            format_func=lambda k: PRESETS[k]["title"],
        )
        selected_preset = PRESETS[preset_key]
        st.caption(f"ℹ️ {selected_preset['description']}")
        default_time_str = selected_preset["default_time"]
        places_to_run = selected_preset["places"]
        
        # Xem trước danh sách điểm
        with st.expander(f"👁️ Xem trước {len(places_to_run)} điểm của preset"):
            preview_df = pd.DataFrame([
                {"Mã": p["id"], "Tên địa điểm": p["name"], "Địa chỉ": p["address"], "Tọa độ": f"{p['lat']:.5f}, {p['lon']:.5f}"}
                for p in places_to_run
            ])
            st.dataframe(preview_df, hide_index=True, use_container_width=True)
            
        # Cảnh báo an toàn cho N lớn
        skip_bt_for_large_n = False
        if len(places_to_run) >= 11:
            st.warning(f"⚠️ N = {len(places_to_run)}: Thuật toán Vét cạn (Backtracking O(N!)) có thể mất nhiều phút.")
            skip_bt_for_large_n = st.checkbox("Bỏ qua Backtracking (chỉ chạy Greedy & DP để phản hồi tức thì)", value=True)
    else:
        st.markdown("**1. Địa điểm xuất phát (DEPOT):**")
        st.session_state.manual_depot["name"] = st.text_input("Tên kho xuất phát:", value=st.session_state.manual_depot["name"])
        st.session_state.manual_depot["address"] = st.text_input("Địa chỉ kho xuất phát:", value=st.session_state.manual_depot["address"])
        
        st.markdown("**2. Danh sách các điểm cần giao hàng:**")
        for i, stop in enumerate(st.session_state.manual_stops):
            c_name, c_addr, c_del = st.columns([3, 4, 1])
            with c_name:
                stop["name"] = st.text_input(f"Điểm {i+1} - Tên:", value=stop["name"], key=f"name_{i}")
            with c_addr:
                stop["address"] = st.text_input(f"Địa chỉ:", value=stop["address"], key=f"addr_{i}")
            with c_del:
                st.write("")
                st.write("")
                if st.button("🗑️", key=f"del_{i}", help="Xóa điểm này"):
                    if len(st.session_state.manual_stops) > 1:
                        st.session_state.manual_stops.pop(i)
                        st.rerun()
                    else:
                        st.error("Cần giữ ít nhất 1 điểm đến.")
                        
        if st.button("➕ Thêm điểm giao hàng"):
            new_idx = len(st.session_state.manual_stops) + 1
            st.session_state.manual_stops.append({
                "name": f"Điểm giao mới #{new_idx}",
                "address": "Đường Lê Duẩn, Bến Nghé, Quận 1, TP.HCM",
                "lat": None,
                "lon": None,
            })
            st.rerun()
            
        # Nút Geocoding trước khi tối ưu (FR-01A)
        if st.button("🔍 Kiểm tra & Định vị tọa độ (Geocoding)"):
            with st.spinner("Đang định vị địa chỉ qua ArcGIS Geocoding..."):
                all_good = True
                try:
                    lat, lon = geocode_address(st.session_state.manual_depot["address"])
                    st.session_state.manual_depot["lat"], st.session_state.manual_depot["lon"] = lat, lon
                except Exception as exc:
                    st.error(f"❌ Lỗi định vị Kho: {exc}")
                    all_good = False
                
                for s in st.session_state.manual_stops:
                    try:
                        lat, lon = geocode_address(s["address"])
                        s["lat"], s["lon"] = lat, lon
                    except Exception as exc:
                        st.error(f"❌ Không thể định vị '{s['name']}': {exc}")
                        all_good = False
                        
                if all_good:
                    st.success("✅ Toàn bộ địa chỉ đã được định vị thành công!")

    # --------------------------------------------------------------------------
    # FR-02: NHẬP GIỚI HẠN THỜI GIAN (BẮT BUỘC KHÔNG DÙNG SLIDER)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### ⏱️ Giới hạn thời gian ca làm việc")
    
    initial_time_val = default_time_str if input_mode == "Preset Demo" else ""
    time_input_str = st.text_input(
        "Giới hạn thời gian (phút) — không bắt buộc",
        value=initial_time_val,
        placeholder="Ví dụ: 7 hoặc 120. Để trống = không giới hạn",
        help="Để trống nếu không giới hạn thời gian. Nhập số phút dương (cho phép số thập phân, ví dụ: 7.5).",
    )
    st.caption("ℹ️ *Để trống nếu không giới hạn thời gian.*")

    # Cấu hình OSRM
    with st.expander("🌐 Cấu hình máy chủ OSRM"):
        osrm_url = st.text_input("OSRM Base URL:", value=os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org"))
        st.markdown("**Phương tiện mặc định:** 🛵 **Xe máy (Motorcycle)**")
        st.caption("ℹ️ *Cố định theo đề tài: Tối ưu hóa lộ trình cho shipper xe máy tại mạng đường TP.HCM.*")

    # --------------------------------------------------------------------------
    # FR-03: NÚT TỐI ƯU HÓA LỘ TRÌNH
    # --------------------------------------------------------------------------
    st.markdown("---")
    btn_optimize = st.button("🚀 Tối ưu hóa lộ trình", type="primary", use_container_width=True)

# ------------------------------------------------------------------------------
# LOGIC XỬ LÝ KHI NHẤN NÚT TỐI ƯU HÓA (FR-03)
# ------------------------------------------------------------------------------
if btn_optimize:
    # 1. Kiểm tra validation thời gian (FR-02)
    max_time_min: Optional[float] = None
    time_clean = time_input_str.strip()
    valid_time = True
    
    if time_clean != "":
        try:
            val = float(time_clean)
            if val <= 0:
                st.error("❌ Lỗi: Giới hạn thời gian phải là số dương lớn hơn 0!")
                valid_time = False
            else:
                max_time_min = val
        except ValueError:
            st.error("❌ Lỗi: Giá trị giới hạn thời gian không hợp lệ! Vui lòng chỉ nhập số (ví dụ: 15 hoặc 7.5) hoặc để trống.")
            valid_time = False

    if valid_time:
        # Chuẩn bị danh sách places
        final_places: List[Dict] = []
        geocoding_success = True
        log_messages: List[str] = []
        
        def write_log(tag: str, msg: str):
            log_messages.append(f"[{tag}] {msg}")
            
        write_log("INFO", "Bắt đầu quy trình tối ưu hóa lộ trình...")
        
        if input_mode == "Preset Demo":
            final_places = [dict(p) for p in places_to_run]
            write_log("INFO", f"Nạp dữ liệu từ {PRESETS[preset_key]['title']} ({len(final_places)} điểm).")
        else:
            # Chế độ nhập tay -> Geocoding
            write_log("INFO", "Đang phân giải tọa độ địa lý (Geocoding)...")
            depot_p = dict(st.session_state.manual_depot)
            depot_p["id"] = "DEPOT"
            try:
                lat, lon = geocode_address(depot_p["address"])
                depot_p["lat"], depot_p["lon"] = lat, lon
                final_places.append(depot_p)
                write_log("OK", f"Định vị Kho DEPOT: {depot_p['name']} -> ({lat:.5f}, {lon:.5f})")
            except Exception as e:
                st.error(f"❌ Không thể định vị địa chỉ Kho: '{depot_p['address']}'. Lỗi: {e}")
                geocoding_success = False

            if geocoding_success:
                for idx, stop in enumerate(st.session_state.manual_stops, 1):
                    p_dict = dict(stop)
                    p_dict["id"] = f"P{idx}"
                    try:
                        lat, lon = geocode_address(p_dict["address"])
                        p_dict["lat"], p_dict["lon"] = lat, lon
                        final_places.append(p_dict)
                        write_log("OK", f"Định vị Điểm #{idx}: {p_dict['name']} -> ({lat:.5f}, {lon:.5f})")
                    except Exception as e:
                        st.error(f"❌ Không thể định vị điểm '{p_dict['name']}' ({p_dict['address']}): {e}")
                        geocoding_success = False
                        break

        if geocoding_success and len(final_places) >= 2:
            n = len(final_places)
            write_log("INFO", f"Đã chuẩn hóa danh sách {n} địa điểm (1 Kho DEPOT + {n-1} Điểm giao).")
            if max_time_min is not None:
                write_log("INFO", f"Ràng buộc thời gian ca làm việc: ≤ {max_time_min} phút.")
            else:
                write_log("INFO", "Không đặt ràng buộc thời gian (Tìm chu trình qua 100% các điểm).")

            # 2. Gọi OSRM Table API
            write_log("INFO", f"Đang gửi yêu cầu tới OSRM Table API ({osrm_url})...")
            matrix_ok = True
            distances = []
            durations = []
            # Profile phương tiện: Nếu dùng OSRM public demo thì map sang driving (vì server public không host motorcycle)
            # Nếu dùng OSRM local thì gọi thẳng motorcycle
            profile_to_use = "driving" if "router.project-osrm.org" in osrm_url else "motorcycle"

            try:
                with st.spinner("Đang lấy ma trận khoảng cách & thời gian từ OSRM (Xe máy)..."):
                    distances, durations = fetch_matrices(
                        final_places,
                        osrm_url.rstrip("/"),
                        profile=profile_to_use,
                        timeout=30,
                    )
                write_log("OK", f"Đã nhận thành công ma trận chi phí {n}x{n} từ OSRM cho xe máy.")
            except Exception as exc:
                st.error(f"❌ Lỗi kết nối OSRM Table API: {exc}")
                write_log("ERR", f"Lỗi OSRM Table API: {exc}")
                matrix_ok = False

            if matrix_ok:
                max_time_s = (max_time_min * 60.0) if max_time_min is not None else None
                
                # 3. Chạy 3 thuật toán
                algorithms_to_run = {}
                is_skip_bt = (input_mode == "Preset Demo" and len(final_places) >= 11 and skip_bt_for_large_n)
                
                if not is_skip_bt:
                    algorithms_to_run["Vét cạn (Backtracking)"] = solve_backtracking
                else:
                    write_log("WARN", "Bỏ qua Backtracking vì số điểm N >= 11 (tránh làm chậm ứng dụng).")

                algorithms_to_run["Tham lam (Greedy)"] = solve_greedy
                algorithms_to_run["Quy hoạch động (DP)"] = solve_dynamic_programming

                results: Dict[str, Dict] = {}
                geometries: Dict[str, Dict] = {}
                runtimes_ms: Dict[str, float] = {}

                for alg_name, alg_func in algorithms_to_run.items():
                    write_log("INFO", f"Đang thực thi thuật toán: {alg_name}...")
                    t_start = time.perf_counter()
                    try:
                        order = alg_func(distances, n, dur=durations, max_time=max_time_s)
                        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                        runtimes_ms[alg_name] = round(t_elapsed_ms, 3)

                        # Đánh giá kết quả
                        eval_data = evaluate_route(order, final_places, distances, durations, max_time_min=max_time_min)
                        eval_data["runtime_ms"] = runtimes_ms[alg_name]
                        results[alg_name] = eval_data

                        write_log(
                            "RESULT",
                            f"{alg_name}: Phục vụ {eval_data['visited_count']}/{eval_data['total_places']} điểm | "
                            f"{eval_data['total_dist_km']} km | {eval_data['total_dur_min']} phút | {runtimes_ms[alg_name]} ms"
                        )
                        
                        if eval_data["skipped_indices"]:
                            skipped_names = [final_places[i]["name"] for i in eval_data["skipped_indices"]]
                            write_log("WARN", f"  ↳ Điểm bỏ lại (không đủ thời gian): {', '.join(skipped_names)}")

                        # Lấy Route Geometry từ OSRM
                        geom = get_route_geometry(order, final_places, osrm_url.rstrip("/"), profile=profile_to_use)
                        geometries[alg_name] = geom
                    except Exception as exc:
                        st.error(f"❌ Thuật toán '{alg_name}' gặp lỗi: {exc}")
                        write_log("ERR", f"Lỗi thực thi {alg_name}: {exc}")

                write_log("DONE", "Hoàn tất tối ưu hóa và tổng hợp kết quả.")
                
                # Lưu vào session_state để render ở cột phải
                st.session_state.optimization_results = {
                    "places": final_places,
                    "results": results,
                    "geometries": geometries,
                    "runtimes_ms": runtimes_ms,
                    "max_time_min": max_time_min,
                    "logs": log_messages,
                }
                st.rerun()

# ------------------------------------------------------------------------------
# CỘT PHẢI (COL_MAIN): BẢN ĐỒ, KEY METRICS, TERMINAL CONSOLE, BENCHMARK
# ------------------------------------------------------------------------------
with col_main:
    opt_data = st.session_state.optimization_results
    
    if not opt_data:
        st.info("👈 Vui lòng chọn dữ liệu địa điểm ở cột bên trái và bấm **[ 🚀 Tối ưu hóa lộ trình ]** để xem kết quả.")
        # Hiển thị bản đồ tổng quan ban đầu
        m_preview = folium.Map(
            location=[10.77984, 106.70001],
            zoom_start=14,
            tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
            attr="Google Maps",
        )
        folium.Marker(
            [10.77984, 106.70001],
            tooltip="<b>Bưu điện Trung tâm TP.HCM (DEPOT)</b>",
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
        ).add_to(m_preview)
        st.components.v1.html(m_preview.get_root().render(), height=500)
    else:
        places = opt_data["places"]
        results = opt_data["results"]
        geometries = opt_data["geometries"]
        runtimes_ms = opt_data["runtimes_ms"]
        logs = opt_data["logs"]
        max_time_min = opt_data["max_time_min"]
        
        # ----------------------------------------------------------------------
        # 1. KEY METRICS (FR-05)
        # ----------------------------------------------------------------------
        st.markdown("### 📊 Chỉ số Hiệu năng Thuật toán (Key Metrics)")
        cols_metrics = st.columns(len(results))
        
        for col_m, (alg_name, r_data) in zip(cols_metrics, results.items()):
            with col_m:
                k = r_data["visited_count"]
                total_k = r_data["total_places"]
                is_ot = r_data.get("is_overtime", False)
                skipped = r_data.get("skipped_indices", [])
                
                if skipped:
                    badge_html = f"<span class='badge-warn'>🎯 Phục vụ {k}/{total_k} điểm</span>"
                elif is_ot:
                    badge_html = f"<span class='badge-warn'>⚠️ Lố {r_data['overtime_min']}p</span>"
                else:
                    badge_html = f"<span class='badge-success'>✅ 100% Hoàn thành</span>"
                    
                st.markdown(
                    f"""
                    <div class='metric-card'>
                        <div class='metric-header'>
                            <span>{alg_name}</span>
                            {badge_html}
                        </div>
                        <div class='metric-val'>{r_data['total_dist_km']} km</div>
                        <div style='color:#4a5568; font-size:13px; margin-top:4px;'>
                            ⏱️ <b>Thời gian di chuyển:</b> {r_data['total_dur_min']} phút<br>
                            ⚡ <b>Thời gian chạy:</b> {r_data['runtime_ms']:.3f} ms<br>
                            🎯 <b>Số điểm phục vụ:</b> {k}/{total_k} điểm
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if skipped:
                    skipped_str = ", ".join(places[i]["name"] for i in skipped)
                    st.caption(f"❌ *Bỏ lại: {skipped_str}*")

        # ----------------------------------------------------------------------
        # 2. BẢN ĐỒ TƯƠNG TÁC FOLIUM (FR-04)
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🗺️ Bản đồ Lộ trình Tương tác (Google Maps + OSRM)")
        
        c_filter, c_hint = st.columns([2, 3])
        with c_filter:
            view_option = st.selectbox(
                "Lựa chọn tuyến hiển thị:",
                options=["Tất cả các tuyến (bật/tắt LayerControl)"] + list(results.keys()),
                index=0,
                help="Chọn 1 tuyến duy nhất để quan sát rõ ràng số thứ tự dừng mà không bị chồng lấn.",
            )
        with c_hint:
            st.caption("💡 *Huy hiệu tròn vàng hổ phách (**1, 2, 3...**) chỉ số thứ tự dừng. Huy hiệu xám (**✕**) đánh dấu điểm bị bỏ qua.*")

        # Lọc kết quả nếu người dùng chỉ muốn xem 1 tuyến
        if view_option == "Tất cả các tuyến (bật/tắt LayerControl)":
            filtered_results = results
            filtered_geometries = geometries
        else:
            filtered_results = {view_option: results[view_option]}
            filtered_geometries = {view_option: geometries[view_option]}

        # Tạo bản đồ qua hàm create_map trong output.py
        m = create_map(places, filtered_results, filtered_geometries, output_path=None)
        st.components.v1.html(m.get_root().render(), height=550)

        # ----------------------------------------------------------------------
        # 3. TERMINAL OUTPUT CONSOLE (FR-06)
        # ----------------------------------------------------------------------
        st.markdown("---")
        c_term_head, c_term_dl = st.columns([3, 1])
        with c_term_head:
            st.markdown("### 💻 Terminal Output Console")
        with c_term_dl:
            log_text = "\n".join(logs)
            st.download_button(
                label="📥 Tải Log (.txt)",
                data=log_text,
                file_name="tsp_optimization_log.txt",
                mime="text/plain",
                use_container_width=True,
            )

        # Định dạng màu cho log
        styled_logs = []
        for line in logs:
            if line.startswith("[INFO]"):
                styled_logs.append(f"<span class='term-info'>[INFO]</span> {line[6:]}")
            elif line.startswith("[OK]"):
                styled_logs.append(f"<span class='term-ok'>[OK]</span> {line[4:]}")
            elif line.startswith("[RESULT]"):
                styled_logs.append(f"<span class='term-res'>[RESULT]</span> {line[8:]}")
            elif line.startswith("[WARN]"):
                styled_logs.append(f"<span class='term-warn'>[WARN]</span> {line[6:]}")
            elif line.startswith("[ERR]"):
                styled_logs.append(f"<span class='term-err'>[ERR]</span> {line[5:]}")
            elif line.startswith("[DONE]"):
                styled_logs.append(f"<span class='term-ok'>[DONE]</span> {line[6:]}")
            else:
                styled_logs.append(line)

        terminal_html = "<div class='terminal-container'>" + "<br>".join(styled_logs) + "</div>"
        st.markdown(terminal_html, unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # 4. PHÂN TÍCH ĐỘ PHỨC TẠP & RUNTIME BENCHMARK (FR-07, FR-08)
        # ----------------------------------------------------------------------
        st.markdown("---")
        tab_bench, tab_comp = st.tabs(["📈 Biểu đồ Runtime Benchmark", "📚 Bảng Phân tích Độ phức tạp"])

        with tab_bench:
            st.markdown("##### So sánh Thời gian Chạy Thuật toán Thuần túy (`time.perf_counter`)")
            names = list(runtimes_ms.keys())
            times = [runtimes_ms[k] for k in names]
            
            # Vẽ biểu đồ cột bằng Plotly
            colors = ["#28a745", "#dc3545", "#ff8800"]
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=names,
                        y=times,
                        text=[f"{t:.3f} ms" for t in times],
                        textposition="auto",
                        marker_color=colors[:len(names)],
                    )
                ]
            )
            fig.update_layout(
                yaxis_title="Thời gian thực thi (mili-giây - ms)",
                xaxis_title="Thuật toán",
                height=320,
                margin=dict(l=40, r=40, t=20, b=40),
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("ℹ️ *Đo riêng thời gian CPU chạy thuật toán trong `thuat_toan.py`, không tính thời gian mạng OSRM hay render đồ họa.*")

        with tab_comp:
            comp_data = [
                {
                    "Thuật toán": "Vét cạn (Backtracking)",
                    "Time Complexity": "O(N!)",
                    "Space Complexity": "O(N)",
                    "Tính tối ưu": "Tối ưu toàn cục (k max, cost min)",
                    "Khuyến nghị áp dụng": "Quy mô nhỏ (N ≤ 10). Cần lời giải chuẩn xác tuyệt đối.",
                },
                {
                    "Thuật toán": "Tham lam (Greedy / Nearest Neighbor)",
                    "Time Complexity": "O(N²)",
                    "Space Complexity": "O(N)",
                    "Tính tối ưu": "Xấp xỉ Heuristic (Cục bộ)",
                    "Khuyến nghị áp dụng": "Quy mô lớn (hàng trăm điểm). Cần phản hồi tức thì < 1 ms.",
                },
                {
                    "Thuật toán": "Quy hoạch động (Held-Karp DP)",
                    "Time Complexity": "O(N² · 2ᴺ)",
                    "Space Complexity": "O(N · 2ᴺ)",
                    "Tính tối ưu": "Tối ưu toàn cục (k max, cost min)",
                    "Khuyến nghị áp dụng": "Quy mô vừa (N ≤ 18 - 20). Nhanh hơn vét cạn theo cấp số nhân.",
                },
            ]
            st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)

