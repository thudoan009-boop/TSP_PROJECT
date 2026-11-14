# Tối Ưu Hóa Lộ Trình Giao Hàng Bằng OSRM & Thuật Toán Tối Ưu (Selective TSP)

Dự án nghiên cứu, hiện thực hóa và phân tích giải pháp tối ưu cho **Bài toán Người giao hàng chọn lọc theo ràng buộc thời gian (Time-Constrained Selective TSP / Orienteering Problem)** trên mạng lưới giao thông đường bộ thực tế tại **Thành phố Hồ Chí Minh**.

Hệ thống tích hợp giữa **Open Source Routing Machine (OSRM)**, dữ liệu bản đồ số **OpenStreetMap (OSM)**, các công cụ không gian địa lý, và 3 thuật toán tối ưu kinh điển: **Vét cạn (Backtracking)**, **Tham lam (Greedy)**, và **Quy hoạch động (Dynamic Programming - Held-Karp)**. Dự án hỗ trợ cả giao diện **Dòng lệnh CLI (`main.py`)** tích hợp sẵn bảng Benchmark đo thời gian thực nghiệm ($ms$) lẫn **Ứng dụng Web tương tác hiện đại (`app.py` - Streamlit)**.

---

## 📑 Mục lục
1. [Phần 1: Ý Tưởng & Mô Hình Bài Toán (Problem Concept & Formulation)](#-phần-1-ý-tưởng--mô-hình-bài-toán-problem-concept--formulation)
   - 1.1. Bối cảnh thực tế (Last-Mile Delivery tại TP.HCM)
   - 1.2. Mô hình tối ưu 2 mục tiêu bậc thang (Lexicographical Objectives)
   - 1.3. Tính tương thích ngược với bài toán TSP truyền thống
2. [Phần 2: Chuẩn Bị Dữ Liệu & Công Nghệ (Data Preparation & Tech Stack)](#-phần-2-chuẩn-bị-dữ-liệu--công-nghệ-data-preparation--tech-stack)
   - 2.1. Bản đồ OpenStreetMap & Cắt lọc vùng TP.HCM bằng `osmium-tool`
   - 2.2. Xây dựng Profile phương tiện xe máy (`motorcycle.lua`)
   - 2.3. Tiền xử lý đồ thị định tuyến OSRM (MLD Pipeline)
   - 2.4. Dữ liệu điểm giao hàng (`places.csv`), Geocoding & Bộ đệm tọa độ
   - 2.5. Bảng công cụ & công nghệ sử dụng (Tech Stack)
3. [Phần 3: Quy Trình Vận Hành & Thực Hành (Workflow & Practical Execution)](#-phần-3-quy-trình-vận-hành--thực-hành-workflow--practical-execution)
   - 3.1. Sơ đồ kiến trúc tổng thể toàn hệ thống
   - 3.2. Luồng 1: Báo cáo toàn trình dòng lệnh CLI (`main.py`)
   - 3.3. Luồng 2: Ứng dụng Web tương tác Streamlit (`app.py` - Chuẩn SRS v1.1)
   - 3.4. So sánh & Đánh giá chuyên sâu 3 thuật toán tối ưu
4. [Phần 4: Hướng Dẫn Cài Đặt & Vận Hành Chi Tiết](#-phần-4-hướng-dẫn-cài-đặt--vận-hành-chi-tiết)
   - 4.1. Chuẩn bị môi trường Python
   - 4.2. Chạy ứng dụng Web tương tác (`app.py`)
   - 4.3. Chạy báo cáo dòng lệnh CLI (`main.py`)
   - 4.4. Tùy chọn máy chủ OSRM (Trực tuyến vs. Docker Local)
5. [Phần 5: Cấu Trúc Thư Mục Dự Án](#-phần-5-cấu-trúc-thư-mục-dự-án)

---

## 🎯 Phần 1: Ý Tưởng & Mô Hình Bài Toán (Problem Concept & Formulation)

### 1.1. Bối cảnh thực tế (Last-Mile Delivery tại TP.HCM)
Trong thực tế vận hành logistics đô thị bằng xe máy, mỗi shipper thường có một **quỹ thời gian ca làm việc cố định** (ví dụ tối đa $X = 7$ phút hoặc $X = 120$ phút). Nếu danh sách giao hàng có $N - 1$ địa điểm mà việc ghé thăm toàn bộ các điểm chắc chắn sẽ bị trễ giờ ca làm việc, giải pháp thực tế nhất là: **Giao được nhiều đơn nhất có thể ($k \le N - 1$) và bảo đảm quay về kho trước khi hết thời gian $X$.**

### 1.2. Mô hình tối ưu 2 mục tiêu bậc thang (Lexicographical Objectives)
Hệ thống giải quyết bài toán theo thứ tự ưu tiên kép:
1. **Mục tiêu ưu tiên 1 (Tối đa hóa số đơn phục vụ):**
   Tìm tập con gồm $k$ điểm giao hàng sao cho $k$ là **lớn nhất có thể** ($k \le N - 1$).
2. **Mục tiêu ưu tiên 2 (Tối thiểu hóa chi phí di chuyển):**
   Trong tất cả các lộ trình cùng đạt số điểm $k$ tối đa đó, chọn lộ trình có **tổng quãng đường ngắn nhất** (km) và **tổng thời gian nhanh nhất** (phút).
3. **Ràng buộc thời gian cứng (Hard Constraint):**
   $$\text{Thời gian từ DEPOT} \to \text{Ghé qua } k \text{ điểm} \to \text{Quay về DEPOT} \le X \text{ (phút)}$$
4. **Xử lý đơn tồn đọng:** Các điểm không kịp ghé thăm sẽ tự động được nhận diện là **bị hoãn lại (bỏ qua ca sau)**, hiển thị danh sách rõ ràng trên bảng điều khiển và gắn huy hiệu màu xám `✕` trên bản đồ số.

### 1.3. Tính tương thích ngược với bài toán TSP truyền thống
Nếu thời gian $X$ đủ lớn để đi hết toàn bộ $N$ điểm (hoặc người dùng **để trống ô thời gian** $\implies X = \infty$), hệ thống tự động tìm chu trình khép kín tối ưu đi qua đủ **100% các điểm** như bài toán TSP chuẩn tắc.

---

## 🗺️ Phần 2: Chuẩn Bị Dữ Liệu & Công Nghệ (Data Preparation & Tech Stack)

Quy trình chuẩn bị dữ liệu là nền tảng cốt lõi giúp hệ thống định tuyến chính xác với tốc độ cao mà không làm quá tải phần cứng:

```text
[Geofabrik OSM Vietnam] (~332 MB .pbf)
            │
            ▼ (Dockerfile.osmium - Bounding Box TP.HCM)
   [hcm_2026.osm.pbf] (~29.7 MB)
            │
            ├─► [motorcycle.lua] (Luật giao thông xe máy TP.HCM)
            │
            ▼ (osrm-extract)
   [hcm_2026.osrm]
            │
            ▼ (osrm-partition & osrm-customize)
[Mạng lưới OSRM MLD sẵn sàng phục vụ API]
```

### 2.1. Bản đồ OpenStreetMap & Cắt lọc vùng TP.HCM bằng `osmium-tool`
- **Nguồn dữ liệu gốc:** Tải file bản đồ Việt Nam Protocolbuffer Binary Format (`.osm.pbf`) từ Geofabrik (`vietnam-261105.osm.pbf`, dung lượng ~332 MB).
- **Vấn đề:** File toàn quốc quá lớn, chứa hàng triệu nút và đoạn đường cả nước. Nếu nạp toàn bộ vào OSRM sẽ tốn nhiều gigabyte RAM và tiền xử lý rất lâu.
- **Giải pháp:** Cắt lọc riêng vùng TP.HCM bằng `osmium-tool` với khung tọa độ (Bounding Box):
  - Kinh độ (Longitude): `106.35` đến `107.03`
  - Vĩ độ (Latitude): `10.37` đến `11.16`
- Lệnh trích xuất qua `Dockerfile.osmium`:
  ```bash
  osmium extract --bbox 106.35,10.37,107.03,11.16 vietnam-261105.osm.pbf -o hcm_2026.osm.pbf
  ```
  *Kết quả:* File giảm từ ~332 MB xuống còn **~29.7 MB**, tăng tốc truy vấn gấp 10 lần và tối ưu bộ nhớ.

### 2.2. Xây dựng Profile phương tiện xe máy (`motorcycle.lua`)
Máy chủ OSRM công cộng quốc tế chỉ hỗ trợ ô tô (`driving`), xe đạp (`bike`) và đi bộ (`foot`). File cấu hình `motorcycle.lua` được thiết kế riêng cho xe máy tại TP.HCM:
- **Quyền lưu thông:** Bổ sung `access = { motorcycle = true }`. Cho phép đi vào các tuyến đường cấm ô tô nhưng xe máy được phép đi (hẻm nhỏ, đường nhánh, phố đi bộ cho phép).
- **Quy tắc 1 chiều:** Tuân thủ hướng đường một chiều của xe máy (`oneway = yes`).
- **Tốc độ thực tế đô thị:**
  - Tuyến phố chính (primary/secondary): 30 – 40 km/h.
  - Ngõ hẻm nội đô (residential/living_street): 20 – 25 km/h.
  - Đại lộ/Quốc lộ (trunk): 50 – 60 km/h.
- **Phạt chuyển hướng (Turn Penalties):** Thêm chi phí thời gian khi rẽ trái, rẽ phải hoặc quay đầu (U-turn) để mô phỏng chính xác độ trễ tại nút giao.

### 2.3. Tiền xử lý đồ thị định tuyến OSRM (MLD Pipeline)
Sử dụng thuật toán **Multi-Level Dijkstra (MLD)** qua 3 bước:
1. **Extract:** Trích xuất đồ thị mạng lưới đường giao thông theo luật xe máy.
2. **Partition:** Phân chia đồ thị thành các ô tế bào đa cấp phục vụ tìm kiếm nhanh.
3. **Customize:** Tính toán ma trận trọng số chi phí khoảng cách và thời gian cho từng cung đường.

### 2.4. Dữ liệu điểm giao hàng (`places.csv`), Geocoding & Bộ đệm tọa độ
- File CSV đầu vào định nghĩa vị trí Kho (DEPOT) và các điểm giao hàng:
  ```csv
  id,name,address,max_minutes
  DEPOT,Bưu điện Trung tâm TP.HCM,"02 Công xã Paris, Quận 1, TP.HCM",7
  P1,Nhà thờ Đức Bà,"01 Công xã Paris, Quận 1, TP.HCM",
  P2,Chợ Bến Thành,"Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM",
  P3,Nhà hát Thành phố,"07 Công trường Lam Sơn, Quận 1, TP.HCM",
  P4,Công viên Tao Đàn,"Đường Trương Định, Phường Bến Thành, Quận 1, TP.HCM",
  ```
- **Cơ chế Geocoding tự động:** Người dùng chỉ cần nhập địa chỉ tiếng Việt thông thường. Hệ thống sẽ:
  1. Tra cứu nhanh danh bạ chuẩn `DEFAULT_COORDS` hoặc bộ nhớ đệm `coords_cache.json`.
  2. Nếu là địa chỉ mới, tự động gửi yêu cầu tới **ArcGIS World Geocoding API** để lấy tọa độ $(lat, lon)$ chính xác và lưu vào cache vĩnh viễn, không cần gửi yêu cầu mạng lại lần sau.

### 2.5. Bảng công cụ & công nghệ sử dụng (Tech Stack)

| Công cụ / Thư viện | Phiên bản | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| **Python** | 3.11+ | Ngôn ngữ trung tâm phát triển thuật toán, xử lý dữ liệu và đo đạc thực nghiệm. |
| **Streamlit** | >= 1.35.0 | Nền tảng xây dựng Web App giao diện hai cột, bảng điều khiển và dashboard. |
| **OSRM Engine** | v5.27+ (MLD) | Máy chủ tính toán ma trận chi phí (Table API) và hình học tuyến đường (Route API). |
| **Folium & Branca** | >= 0.16.0 | Dựng bản đồ số tương tác trên nền Google Maps, vẽ polyline, gắn biển báo rẽ và marker. |
| **Plotly** | >= 5.20.0 | Vẽ biểu đồ Runtime Benchmark so sánh thời gian thực thi thuật toán. |
| **Pandas** | >= 2.0.0 | Xử lý dữ liệu bảng, hiển thị danh sách địa điểm và ma trận chi phí. |
| **Requests** | >= 2.31.0 | Gọi API HTTP RESTful kết nối OSRM và ArcGIS Geocoding. |
| **`time.perf_counter`**| Chuẩn Python | Đo đạc thời gian thực thi thuật toán với độ chính xác micro-giây ($ms$). |
| **Docker & Compose** | Khuyến nghị | Tùy chọn đóng gói máy chủ OSRM cục bộ chạy mạng đường xe máy TP.HCM. |

---

## 🔄 Phần 3: Quy Trình Vận Hành & Thực Hành (Workflow & Practical Execution)

### 3.1. Sơ đồ kiến trúc tổng thể toàn hệ thống

```text
                           [Nguồn Dữ Liệu Địa Điểm]
                           (places.csv hoặc Web Input)
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        [Luồng 1: CLI main.py]                [Luồng 2: Web App app.py]
                    │                                     │
                    ├─► Geocoding (ArcGIS) & Cache       ├─► Geocoding / Preset Demo
                    ├─► OSRM Table API (Ma trận N x N)   ├─► Ô nhập thời gian số (No slider)
                    │                                     │
                    ▼                                     ▼
           [thuat_toan.py - Chạy 3 Thuật Toán Tối Ưu Cho Xe Máy]
           ┌──────────────────────┬──────────────────────┐
           ▼                      ▼                      ▼
     Backtracking               Greedy              Held-Karp DP
   (Nhánh cận cắt tỉa)     (Lookahead an toàn)   (Quét trạng thái Bitmask)
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
           [Đo thời gian thực nghiệm bằng time.perf_counter() (ms)]
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        [Báo Cáo CLI Terminal]       [Bảng Điều Khiển Web App]
        - Chi tiết từng chặng        - 3 Thẻ Key Metrics
        - Điểm phục vụ & bỏ qua      - Bản đồ Folium Google Maps
        - Bảng Benchmark Terminal    - Terminal Console ghi log
        - Xuất file route_map.html   - Biểu đồ Plotly Benchmark
```

---

### 3.2. Luồng 1: Báo cáo toàn trình dòng lệnh CLI (`main.py`)
Phục vụ chạy tự động, lập báo cáo kết quả và đo benchmark nhanh trên Terminal:
1. **Bước 1:** Đọc file `places.csv`, tự động geocode các địa chỉ chưa có tọa độ.
2. **Bước 2:** Gọi OSRM Table API lấy ma trận khoảng cách (m) và thời gian (s), tự động chuyển đổi sang km và phút lưu vào `output/distance_matrix.csv` và `output/duration_matrix.csv`.
3. **Bước 3:** Chạy 3 thuật toán:
   - Đo thời gian chạy thuần của thuật toán bằng `time.perf_counter()`.
   - Lấy hình học chi tiết từng khúc cua, ngã rẽ từ OSRM Route API.
4. **Bước 4:** In chi tiết chặng di chuyển, số điểm phục vụ ($k/n$), điểm bị bỏ lại và thời gian thực nghiệm ($ms$).
5. **Bước 5:** In **BẢNG BENCHMARK ĐỘ PHỨC TẠP THỰC NGHIỆM** ngay trên Terminal:
   ```text
   ============================================================================
                    BẢNG BENCHMARK ĐỘ PHỨC TẠP THỰC NGHIỆM
   ============================================================================
   Thuật toán                     | Độ phức tạp lý thuyết  | Thời gian thực nghiệm
   ----------------------------------------------------------------------------
     Vét cạn (Backtracking)       | O((N-1)!)              |         0.055 ms
     Tham lam (Greedy)            | O(N²)                  |         0.043 ms
     Quy hoạch động (DP)          | O(N²·2ᴺ)               |         0.273 ms
   ============================================================================
   ```
6. **Bước 6:** Tự động tạo và lưu bản đồ tương tác vào `output/route_map.html`.

---

### 3.3. Luồng 2: Ứng dụng Web tương tác Streamlit (`app.py` - Chuẩn SRS v1.1)
Giao diện trực quan hóa toàn bộ quá trình dành cho người dùng và trình diễn đồ án:

#### Cột trái — Điều khiển & Thiết lập:
- **Nguồn địa điểm (FR-01):**
  - **Preset Demo (FR-01B):** Cung cấp sẵn 3 bộ dữ liệu tọa độ chuẩn:
    - *Nhỏ (5 điểm):* Depot Bưu điện TP, Nhà thờ Đức Bà, Chợ Bến Thành, Nhà hát TP, CV Tao Đàn.
    - *Vừa (8 điểm):* Thêm Dinh Độc Lập, Hồ Con Rùa, Bảo tàng Chứng tích, Chợ Tân Định.
    - *Lớn (12 điểm):* Thêm Landmark 81, Bến Nhà Rồng, Thảo Cầm Viên (có cơ chế cảnh báo an toàn cho Backtracking khi $N \ge 11$).
  - **Nhập địa chỉ thủ công (FR-01A):** Nhập Depot và danh sách điểm cần ghé, thêm/xóa điểm động, tích hợp nút kiểm tra Geocoding.
- **Giới hạn thời gian ca làm việc (FR-02 — TUYỆT ĐỐI KHÔNG DÙNG SLIDER):**
  - Ô nhập số: **“Giới hạn thời gian (phút) — không bắt buộc”**.
  - Để trống $\implies$ Không giới hạn thời gian (tìm chu trình đủ 100% điểm).
  - Nhập số dương $\implies$ Áp dụng ràng buộc ca.
  - Nhập $\le 0$ hoặc chữ $\implies$ Báo lỗi đỏ rõ ràng.
- **Phương tiện:** Cố định và tối ưu hóa riêng cho **🛵 Xe máy (Motorcycle)**.

#### Cột phải — Bảng điều khiển kết quả:
- **Key Metrics (FR-05):** 3 thẻ chỉ số tương ứng 3 thuật toán gồm Quãng đường (km), Thời gian đi (phút), Số điểm phục vụ ($k/n$), Thời gian CPU ($ms$), và huy hiệu trạng thái (Đạt chuẩn / Bỏ qua đơn / Lố giờ).
- **Bản đồ Folium Google Maps (FR-04):**
  - Lớp bản đồ đường bộ & Google Vệ tinh.
  - **Huy hiệu số thứ tự dừng vàng hổ phách (`1`, `2`, `3`...)** nổi bật trên nền đường.
  - **Huy hiệu màu xám `✕`** đánh dấu các đơn hàng bị hoãn lại do hết giờ ca.
  - Polyline bám đường thực tế OSRM có mũi tên chỉ hướng `➤` và biển báo chuyển hướng (`↰`, `↱`, `🔄`, `↩`).
  - Bộ lọc xem *Tất cả các tuyến* hoặc *Từng tuyến riêng biệt* tránh chồng chéo marker.
- **Terminal Output Console (FR-06):** Khung nền đen bóng hiển thị log thực thi từng bước có phân loại màu sắc (`[INFO]`, `[OK]`, `[RESULT]`, `[WARN]`, `[DONE]`), kèm nút **📥 Tải Log (.txt)**.
- **Biểu đồ Runtime Benchmark Plotly (FR-08):** Biểu đồ cột trực quan so sánh thời gian chạy thực nghiệm ($ms$) đo bằng `perf_counter()`.
- **Bảng Độ phức tạp thuật toán (FR-07):** Bảng đối chiếu lý thuyết Big-O và khuyến nghị áp dụng.

---

### 3.4. So sánh & Đánh giá chuyên sâu 3 thuật toán tối ưu

| Tiêu chí | 1. Vét cạn (Backtracking) | 2. Tham lam (Greedy) | 3. Quy hoạch động (Held-Karp DP) |
| :--- | :--- | :--- | :--- |
| **Nguyên lý hoạt động** | Duyệt cây đệ quy có cắt tỉa nhánh cận. Nếu thời gian hiện tại cộng đường về kho $> X \implies$ Cắt tỉa ngay lập tức. Duy trì kỷ lục $(k_{\max}, \text{cost}_{\min})$. | Tại mỗi bước, chọn điểm gần nhất trong các điểm an toàn (đến được và còn đủ giờ quay về kho $\le X$). Dừng ngay khi không còn điểm an toàn. | Bảng $dp[mask][u]$ lưu thời gian nhỏ nhất đi qua tập đỉnh biểu diễn bằng bitmask kết thúc tại $u$. Quét mọi trạng thái hợp lệ $\le X$, chọn trạng thái có số bit 1 lớn nhất. |
| **Tính tối ưu** | **Tối ưu toàn cục 100%** (Số điểm $k$ tối đa, quãng đường ngắn nhất). | **Xấp xỉ (Heuristic)**, có thể dừng sớm hoặc phục vụ ít hơn 1 đơn so với tối ưu. | **Tối ưu toàn cục 100%** (Cam kết số điểm $k$ tối đa và chi phí tối thiểu). |
| **Độ phức tạp Thời gian** | $O((N-1)!)$ | $O(N^2)$ (thực thi cực nhanh $< 0.05$ ms) | $O(N^2 \cdot 2^N)$ |
| **Độ phức tạp Không gian** | $O(N)$ (ngăn xếp đệ quy) | $O(N)$ (mảng đánh dấu đỉnh) | $O(N \cdot 2^N)$ (bảng trạng thái bitmask) |
| **Ưu điểm** | Đơn giản, tốn rất ít RAM, luôn bảo đảm tìm ra kết quả tốt nhất. | Chạy tức thì, phù hợp bài toán thời gian thực với quy mô hàng trăm điểm. | Nhanh hơn vét cạn theo cấp số nhân, 100% bảo đảm kết quả tối ưu. |
| **Nhược điểm** | Khi $N \ge 12$ và thời gian $X$ quá lớn, số nhánh duyệt tăng vọt. | Dễ dừng lại sớm nếu điểm chọn ban đầu dẫn vào vùng cô lập. | Giới hạn bởi bộ nhớ RAM khi $N > 20$. |
| **Phạm vi áp dụng khuyến nghị**| $N \le 10$ điểm | $N$ lớn từ hàng chục đến hàng nghìn điểm | $N \le 16 - 18$ điểm |

---

## 🚀 Phần 4: Hướng Dẫn Cài Đặt & Vận Hành Chi Tiết

### 4.1. Chuẩn bị môi trường Python
Mở Terminal tại thư mục gốc dự án:
```powershell
# Kích hoạt môi trường ảo:
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện phụ thuộc (nếu chưa có):
pip install -r tsp_osrm_demo\requirements.txt
```

---

### 4.2. Chạy ứng dụng Web tương tác (`app.py`)
Cách thuận tiện và trực quan nhất để trải nghiệm và báo cáo:

```powershell
# Chạy trực tiếp qua python venv:
.\.venv\Scripts\python.exe -m streamlit run tsp_osrm_demo\app.py

# Hoặc nếu đã kích hoạt venv:
cd tsp_osrm_demo
streamlit run app.py
```
> Trình duyệt web sẽ tự động mở trang tại: **`http://localhost:8501`**.

---

### 4.3. Chạy báo cáo dòng lệnh CLI (`main.py`)
Khi muốn chạy tự động và xuất ngay file HTML bản đồ và bảng Benchmark ra terminal:

```powershell
cd tsp_osrm_demo
python main.py
```
- Kết quả Terminal: In đầy đủ lộ trình, số đơn giao thành công, điểm bị bỏ lại, thời gian thực nghiệm ($ms$) và Bảng Benchmark.
- Bản đồ: Mở file `output/route_map.html` trên trình duyệt để quan sát các tuyến đường Google Maps.

---

### 4.4. Tùy chọn máy chủ OSRM (Trực tuyến vs. Docker Local)

#### Lựa chọn 1: Máy chủ trực tuyến miễn phí (Mặc định)
* Hệ thống mặc định trỏ tới `https://router.project-osrm.org`.
* **Không cần bật Docker**, không cần cài đặt gì thêm, mở web lên là chạy ngay.
* Hệ thống tự động xử lý profile thông minh để luôn kết nối ổn định.

#### Lựa chọn 2: Máy chủ Docker Local (Nếu muốn chạy offline mạng đường xe máy TP.HCM)
Tại thư mục gốc chứa file `compose.yaml`:
```powershell
docker compose up -d osrm
```
Máy chủ OSRM local sẽ lắng nghe tại `http://localhost:5001`. Khi chạy, chỉ cần đặt biến môi trường:
```powershell
$env:OSRM_BASE_URL="http://localhost:5001"
python main.py
```

---

## 📂 Phần 5: Cấu Trúc Thư Mục Dự Án

```text
tsp_osrm_demo/
│
├── compose.yaml                    # Cấu hình Docker dịch vụ OSRM backend local
├── Dockerfile.osmium               # Dockerfile build môi trường cắt trích xuất bản đồ
├── motorcycle.lua                  # Tệp cấu hình luật lưu thông xe máy Việt Nam
├── vietnam-261105.osm.pbf          # Dữ liệu OSM thô toàn quốc Việt Nam (~332 MB)
├── hcm_2026.osm.pbf                # Bản đồ sau khi cắt trích xuất riêng TP.HCM (~29.7 MB)
├── hcm_2026.osrm*                  # Bộ tệp chỉ mục đồ thị mạng lưới MLD xe máy TP.HCM
│
└── tsp_osrm_demo/                  # Thư mục mã nguồn chính của ứng dụng
    ├── app.py                      # Ứng dụng Web tương tác Streamlit (theo đặc tả SRS v1.1)
    ├── main.py                     # Điều phối toàn trình CLI, đo thời gian thực nghiệm & Benchmark
    ├── thuat_toan.py               # 3 thuật toán Selective TSP: Backtracking, Greedy, DP Held-Karp
    ├── api_calls.py                # Wrapper OSRM Table API, Route API & Geocoding ArcGIS
    ├── output.py                   # Xuất ma trận CSV, tạo bản đồ Folium (thứ tự vàng, dấu ✕)
    ├── places.csv                  # Danh sách điểm giao hàng mẫu & giới hạn thời gian cứng
    ├── coords_cache.json           # Bộ đệm lưu trữ tọa độ đã geocode (tránh gọi lại API)
    ├── Dockerfile                  # Dockerfile đóng gói ứng dụng Python
    ├── requirements.txt            # Danh mục thư viện Python (streamlit, folium, plotly, pandas...)
    ├── README.md                   # Tài liệu phân tích và hướng dẫn kỹ thuật chi tiết
    └── output/
        ├── distance_matrix.csv     # Ma trận khoảng cách thực tế giữa các điểm (km)
        ├── duration_matrix.csv     # Ma trận thời gian di chuyển thực tế (phút)
        └── route_map.html          # Bản đồ số tương tác Folium trên nền Google Maps
```

---
*Dự án thuộc đề tài: Phân tích & Thiết kế Giải thuật — Tối ưu hóa lộ trình vận chuyển chọn lọc có ràng buộc thời gian ca làm việc (Time-Constrained Selective TSP) trên mạng lưới giao thông đường bộ Thành phố Hồ Chí Minh.*
