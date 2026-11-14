# TSP Routing & Optimization — OSRM & Phân Tích Thực Nghiệm Thuật Toán

Dự án nghiên cứu, hiện thực hóa và phân tích giải pháp tối ưu cho **Bài toán Người giao hàng chọn lọc theo ràng buộc thời gian (Time-Constrained Selective TSP / Orienteering Problem)** trên mạng lưới giao thông đường bộ thực tế tại **Thành phố Hồ Chí Minh**.

Hệ thống tích hợp giữa **Open Source Routing Machine (OSRM)**, dữ liệu bản đồ số **OpenStreetMap (OSM)**, các công cụ xử lý không gian địa lý, và 3 thuật toán tối ưu kinh điển: **Vét cạn (Backtracking)**, **Tham lam (Greedy)**, và **Quy hoạch động (Dynamic Programming - Held-Karp)**.

---

## 📑 Mục lục
1. [Tổng quan Dự án & Cơ chế Tối ưu mới](#-1-tổng-quan-dự-án--cơ-chế-tối-ưu-mới)
2. [Giai đoạn 1: Chuẩn bị Dữ liệu (Data Preparation)](#-2-giai-đoạn-1-chuẩn-bị-dữ-liệu-data-preparation)
   - 2.1. Dữ liệu bản đồ OpenStreetMap & Cắt lọc vùng TP.HCM bằng `osmium-tool`
   - 2.2. Xây dựng Profile phương tiện xe máy (`motorcycle.lua`)
   - 2.3. Tiền xử lý đồ thị định tuyến OSRM (MLD Pipeline)
   - 2.4. Dữ liệu danh sách điểm giao hàng (`places.csv`) & Ràng buộc thời gian cứng
3. [Giai đoạn 2: Công cụ & Công nghệ Sử dụng (Tools & Tech Stack)](#-3-giai-đoạn-2-công-cụ--công-nghệ-sử-dụng-tools--tech-stack)
4. [Giai đoạn 3: Quy trình Hoạt động của Dự án (System Workflow)](#-4-giai-đoạn-3-quy-trình-hoạt-động-của-dự-án-system-workflow)
   - 4.1. Sơ đồ kiến trúc tổng thể
   - 4.2. Luồng 1: Quy trình Toàn trình Online / Local OSRM (`main.py`)
   - 4.3. Luồng 2: Phân tích Thuật toán & Kiểm thử Thực nghiệm Offline (`run_algorithms.py`)
5. [So sánh & Đánh giá 3 Thuật toán Tối ưu](#-5-so-sánh--đánh-giá-3-thuật-toán-tối-ưu)
6. [Hướng dẫn Cài đặt & Vận hành Chi tiết](#-6-hướng-dẫn-cài-đặt--vận-hành-chi-tiết)
7. [Cấu trúc Thư mục Dự án](#-7-cấu-trúc-thư-mục-dự-án)

---

## 🎯 1. Tổng quan Dự án & Cơ chế Tối ưu mới

Trong thực tế vận hành logistics (Last-mile delivery), shipper luôn có một **quỹ thời gian ca làm việc cố định** (ví dụ tối đa $X = 7$ phút hoặc $X = 120$ phút). Nếu danh sách giao hàng có $N - 1$ điểm mà việc đi hết tất cả các điểm chắc chắn sẽ bị trễ giờ làm, giải pháp thực tế nhất là: **Giao được nhiều điểm nhất có thể ($k \le N - 1$) và kịp quay về kho trước khi hết thời gian $X$.**

### 🌟 Cơ chế tối ưu 2 mục tiêu bậc thang (Lexicographical Objectives):
1. **Mục tiêu ưu tiên 1 (Tối đa hóa số đơn phục vụ)**: Tìm tập con gồm $k$ điểm giao hàng sao cho $k$ là **lớn nhất có thể** ($k \le N - 1$).
2. **Mục tiêu ưu tiên 2 (Tối thiểu hóa chi phí)**: Trong tất cả các lộ trình cùng đạt số điểm $k$ tối đa đó, chọn lộ trình có **tổng quãng đường ngắn nhất** (km) và **tổng thời gian nhanh nhất** (phút).
3. **Ràng buộc cứng (Hard Constraint)**:
   $$\text{Thời gian từ DEPOT} \to \text{Ghé qua } k \text{ điểm} \to \text{Quay về DEPOT} \le X \text{ (phút)}$$
4. **Xử lý điểm tồn đọng**: Các điểm không kịp ghé thăm sẽ tự động được nhận diện là **bị bỏ lại (hoãn sang ca sau)**, hiển thị danh sách rõ ràng trên Terminal và gắn huy hiệu màu xám `✕` trên Bản đồ tương tác.
5. **Tính tương thích ngược**: Nếu thời gian $X$ đủ lớn để đi hết toàn bộ $N$ điểm (hoặc không đặt $X$), hệ thống sẽ tự động tìm chu trình khép kín qua đủ 100% các điểm như TSP truyền thống.

---

## 🗺️ 2. Giai đoạn 1: Chuẩn bị Dữ liệu (Data Preparation)

Quy trình chuẩn bị dữ liệu là nền tảng cốt lõi giúp hệ thống định tuyến chính xác với tốc độ cao mà không làm quá tải phần cứng:

```
[Geofabrik OSM Vietnam] (~332 MB .pbf)
            │
            ▼ (Dockerfile.osmium - Bounding Box TP.HCM)
   [hcm_2026.osm.pbf] (~29.7 MB)
            │
            ├─► [motorcycle.lua] (Luật giao thông xe máy VN)
            │
            ▼ (osrm-extract)
   [hcm_2026.osrm]
            │
            ▼ (osrm-partition & osrm-customize)
[Mạng lưới OSRM MLD sẵn sàng phục vụ API]
```

### 2.1. Dữ liệu bản đồ OpenStreetMap & Cắt lọc vùng TP.HCM bằng `osmium-tool`
- **Nguồn dữ liệu gốc**: Tải file trích xuất bản đồ Việt Nam định dạng Protocolbuffer Binary Format (`.osm.pbf`) từ Geofabrik (`vietnam-261105.osm.pbf`, dung lượng ~332 MB).
- **Vấn đề**: File toàn quốc quá lớn, chứa hàng triệu nút (nodes) và đường đi (ways) trên cả nước. Nếu nạp toàn bộ vào OSRM sẽ tốn nhiều gigabyte RAM và thời gian tiền xử lý rất lâu.
- **Giải pháp**: Trích xuất riêng vùng địa lý TP.HCM bằng `osmium-tool` với khung tọa độ (Bounding Box):
  - Kinh độ (Longitude): `106.35` đến `107.03`
  - Vĩ độ (Latitude): `10.37` đến `11.16`
- **Thực hiện qua Dockerfile.osmium**:
  ```dockerfile
  FROM ubuntu:24.04
  RUN apt-get update && apt-get install -y osmium-tool && rm -rf /var/lib/apt/lists/*
  ```
  Lệnh trích xuất:
  ```bash
  osmium extract --bbox 106.35,10.37,107.03,11.16 vietnam-261105.osm.pbf -o hcm_2026.osm.pbf
  ```
  *Kết quả*: Dung lượng giảm xuống còn **~29.7 MB**, tăng tốc độ truy vấn lên gấp 10 lần và tiết kiệm RAM tối đa.

### 2.2. Xây dựng Profile phương tiện xe máy (`motorcycle.lua`)
Server OSRM công cộng quốc tế (`https://router.project-osrm.org`) chỉ hỗ trợ ô tô (`driving`), xe đạp (`bike`) và đi bộ (`foot`), hoàn toàn **không hỗ trợ xe máy** tại Việt Nam.

Tệp `motorcycle.lua` được tùy biến riêng cho điều kiện giao thông TP.HCM:
- **Quyền lưu thông**: Bổ sung `access = { motorcycle = true }`. Cho phép đi vào các tuyến đường cấm ô tô nhưng xe máy được phép lưu thông (hẻm nhỏ, đường gom, tuyến phố nội đô).
- **Quy tắc 1 chiều**: Tuân thủ chiều lưu thông của xe máy trên đường 1 chiều (`oneway = yes`).
- **Tốc độ thiết kế thực tế**:
  - Đường đô thị (primary/secondary): 30 – 40 km/h.
  - Đường ngõ hẻm (residential/living_street): 20 – 25 km/h.
  - Quốc lộ/Đại lộ (trunk): 50 – 60 km/h.
- **Phạt chuyển hướng (Turn Penalties)**: Thiết lập thời gian phạt khi rẽ trái, rẽ phải hoặc quay đầu (U-turn) để phản ánh đúng độ trễ tại các nút giao thông.

### 2.3. Tiền xử lý đồ thị định tuyến OSRM (MLD Pipeline)
Sử dụng thuật toán **Multi-Level Dijkstra (MLD)** để chuẩn bị dữ liệu đường đi qua 3 bước:
1. **Extract**:
   ```bash
   docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /data/motorcycle.lua /data/hcm_2026.osm.pbf
   ```
2. **Partition** (Phân chia đồ thị mạng lưới thành các ô tế bào đa cấp):
   ```bash
   docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/hcm_2026.osrm
   ```
3. **Customize** (Tính toán trọng số chi phí khoảng cách và thời gian cho từng đoạn đường):
   ```bash
   docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/hcm_2026.osrm
   ```

### 2.4. Dữ liệu danh sách điểm giao hàng (`places.csv`) & Ràng buộc thời gian cứng
Dữ liệu đầu vào do người dùng chỉ định gồm các điểm cần giao hàng:
```csv
id,name,address,max_minutes
DEPOT,Bưu điện Trung tâm TP.HCM,"02 Công xã Paris, Quận 1, TP.HCM",7
P1,Nhà thờ Đức Bà,"01 Công xã Paris, Quận 1, TP.HCM",
P2,Chợ Bến Thành,"Đường Lê Lợi, Phường Bến Thành, Quận 1, TP.HCM",
P3,Nhà hát Thành phố,"07 Công trường Lam Sơn, Quận 1, TP.HCM",
P4,Công viên Tao Đàn,"Đường Trương Định, Phường Bến Thành, Quận 1, TP.HCM",
```
- **Dòng `DEPOT`**: Vị trí xuất phát và cũng là điểm kết thúc của chuyến hành trình.
- **Cột `max_minutes`**: Thời gian trần tối đa cho phép của ca giao hàng (tính bằng phút). Thuật toán sẽ dùng mốc này làm ràng buộc cứng để tìm phương án giao được nhiều điểm $k$ nhất mà không vượt quá số phút này.
- **Cơ chế Geocoding tự động**: Người dùng chỉ cần nhập địa chỉ tiếng Việt rõ ràng. Khi chạy, hệ thống sẽ:
  1. Kiểm tra cache trong `coords_cache.json` hoặc danh bạ tọa độ chuẩn `DEFAULT_COORDS`.
  2. Nếu chưa có, tự động gọi **ArcGIS World Geocoding API** để lấy tọa độ chính xác $(lat, lon)$ và tự lưu vào file cache để tái sử dụng vĩnh viễn không cần gọi lại mạng.

---

## 🛠️ 3. Giai đoạn 2: Công cụ & Công nghệ Sử dụng (Tools & Tech Stack)

| Công cụ / Thư viện | Vai trò trong hệ thống |
| :--- | :--- |
| **Docker & Docker Compose** | Đóng gói môi trường định tuyến OSRM (`ghcr.io/project-osrm/osrm-backend`) và Python app độc lập, bảo đảm chạy đồng nhất trên Windows/Linux/macOS mà không phụ thuộc cài đặt máy chủ. |
| **Osmium Tool** | Bộ công cụ C++ xử lý dữ liệu bản đồ OSM mã nguồn mở, dùng cắt Bounding Box trích xuất TP.HCM từ dữ liệu toàn quốc. |
| **OSRM Engine (MLD)** | Máy chủ định tuyến tính toán đường đi với hiệu năng cực cao, cung cấp **Table API** (ma trận chi phí) và **Route API** (hình học polyline thực tế). |
| **Python 3.11+** | Ngôn ngữ trung tâm phát triển logic thuật toán, xử lý dữ liệu, kiểm thử và vẽ bản đồ. |
| **Requests** | Giao tiếp HTTP RESTful với OSRM Server và Geocoding API. |
| **Folium & Branca** | Tạo bản đồ tương tác HTML (Leaflet.js), hỗ trợ nền vệ tinh Google Maps, gắn icon, mũi tên di chuyển, biển báo rẽ, số thứ tự điểm dừng và huy hiệu điểm bỏ qua `✕`. |
| **ArcGIS World Geocoding** | Dịch vụ phân giải địa chỉ thành tọa độ địa lý toàn cầu miễn phí, không yêu cầu API Key. |
| **Python Standard Libs (`time.perf_counter`, `csv`, `math`, `pathlib`)** | Đo đạc thời gian thực nghiệm độ chính xác micro-giây ($ms$), xử lý ma trận và đọc ghi file. |

---

## 🔄 4. Giai đoạn 3: Quy trình Hoạt động của Dự án (System Workflow)

Hệ thống được thiết kế theo kiến trúc module hóa phân tầng, hỗ trợ **2 luồng hoạt động riêng biệt**:

```
                              [places.csv]
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
   [Luồng 1: main.py]                         [Luồng 2: run_algorithms.py]
 (Online / Local OSRM Server)                  (Offline / Kiểm thử thực nghiệm)
             │                                           │
  - Geocoding tọa độ (lat/lon)               - Đọc distance_matrix.csv
  - Gọi OSRM Table API                         & duration_matrix.csv
  - Lưu distance & duration CSV                         │
             │                                          ▼
             ▼                               - In ma trận Input chuẩn
  - Giải Selective TSP (<= max_time):         - Benchmark 3 thuật toán:
    * Backtracking (nhánh cận cắt tỉa)         * Backtracking (Selective)
    * Greedy (lookahead đường lui)             * Greedy (an toàn quay về)
    * DP Held-Karp (quét bitmask)              * DP Held-Karp (quét k max)
  - Đánh giá điểm phục vụ & điểm bỏ qua      - Đo thời gian perf_counter (ms)
  - Gọi OSRM Route API (GeoJSON)                        │
             │                                          ▼
             ▼                               - Bảng phân tích độ phức tạp (N)
  - Xuất [output/route_map.html]              - Bộ Unit Test kiểm định
    (Bản đồ Google Maps có thứ tự ghé thăm
     và huy hiệu đánh dấu điểm bỏ qua ✕)
```

---

### 4.1. Luồng 1: Quy trình Toàn trình Online / Local OSRM (`main.py`)
Áp dụng khi người dùng thay đổi danh sách địa điểm trong `places.csv` hoặc cần cập nhật lại đường đi từ OSRM:

1. **Bước 1 - Khởi tạo & Tải dữ liệu**:
   - `main.py` đọc file `places.csv`.
   - Hàm `load_places` trong `api_calls.py` kiểm tra từng địa chỉ. Nếu thiếu `latitude` / `longitude`, hệ thống thực hiện Geocoding và lưu vào `coords_cache.json`.
2. **Bước 2 - Lấy Ma trận Khoảng cách & Thời gian**:
   - Gọi `fetch_matrices`: Gửi tọa độ toàn bộ $N$ điểm đến endpoint `/table/v1/driving/...` (hoặc `/motorcycle/...`) của OSRM.
   - Nhận về 2 ma trận $N \times N$: Khoảng cách ($m$) và Thời gian ($s$).
   - `save_matrices` quy đổi thành km và phút (làm tròn 2 chữ số thập phân), ghi thành 2 file `output/distance_matrix.csv` và `output/duration_matrix.csv`.
3. **Bước 3 - Giải quyết bài toán Selective TSP với 3 chiến lược**:
   - Chuyển đổi `max_minutes` từ DEPOT sang giây (`max_time_s = max_minutes * 60`).
   - `solve_backtracking(distances, n, dur=durations, max_time=max_time_s)`: Duyệt nhánh cận tìm tập con $k$ lớn nhất có thời gian $\le \text{max\_time}$.
   - `solve_greedy(distances, n, dur=durations, max_time=max_time_s)`: Tham lam với điều kiện an toàn luôn đủ thời gian quay về Depot.
   - `solve_dynamic_programming(distances, n, dur=durations, max_time=max_time_s)`: Quét không gian trạng thái $(mask, u)$ tìm phương án $k$ lớn nhất và chi phí thấp nhất.
4. **Bước 4 - Đánh giá Điểm Phục Vụ & Điểm Bỏ Qua (Evaluation)**:
   - Hàm `evaluate_route` tính toán danh sách các điểm được giao thành công ($k$ điểm), danh sách các điểm bị loại bỏ (không đủ thời gian), và thời gian ca làm việc còn dư.
5. **Bước 5 - Lấy Hình học Đường đi Thực tế (Route Geometry)**:
   - Với mỗi lộ trình tìm được, hàm `get_route_geometry` gọi endpoint `/route/v1/...` của OSRM để lấy tọa độ chi tiết từng ngã rẽ và đoạn đường cong (Polyline GeoJSON).
6. **Bước 6 - Xuất Bản đồ Số Tương tác (`output/route_map.html`)**:
   - Hàm `create_map` trong `output.py` tạo giao diện bản đồ Folium trên nền **Google Maps** (hỗ trợ cả lớp Google Vệ tinh).
   - Đánh dấu các địa điểm với Tooltip cố định tên địa danh.
   - Vẽ đường đi với màu sắc nhận diện riêng:
     - **Vét cạn (Backtracking)**: Màu xanh lá cây (`#28a745`), độ dày nét 6.
     - **Tham lam (Greedy)**: Màu đỏ rực (`#dc3545`), độ dày nét 5.
     - **Quy hoạch động (DP)**: Màu cam đậm (`#ff8800`), độ dày nét 5.
   - **Tích hợp các chi tiết chỉ dẫn**:
     - Mũi tên chỉ hướng di chuyển `➤` chạy dọc thân đường.
     - Biển báo các vị trí rẽ: Rẽ trái `↰`, Rẽ phải `↱`, Vòng xuyến `🔄`, Quay đầu `↩`.
     - **Huy hiệu số thứ tự lộ trình (`1`, `2`, `3`...)**: Đặt ngay cạnh mỗi điểm dừng theo đúng thứ tự ghé thăm của thuật toán.
     - **Huy hiệu màu xám `✕`**: Đặt trên các điểm bị bỏ qua do giới hạn thời gian để shipper nắm rõ các đơn hoãn lại.
     - `LayerControl`: Checkbox cho phép bật/tắt từng chiến lược để so sánh trực quan lộ trình.

---

### 4.2. Luồng 2: Phân tích Thuật toán & Kiểm thử Thực nghiệm Offline (`run_algorithms.py`)
Được thiết kế phục vụ mục đích học thuật, nghiên cứu và báo cáo. **Hoàn toàn không cần kết nối internet hay máy chủ OSRM**:

1. **Bước 1 - Đọc ma trận có sẵn**:
   - Đọc trực tiếp ma trận 2 chiều từ file `output/distance_matrix.csv` và `output/duration_matrix.csv`.
2. **Bước 2 - In định dạng ma trận Input chuẩn**:
   - In kích thước $N$ và toàn bộ bảng ma trận khoảng cách đối xứng.
3. **Bước 3 - Thực thi và Đo lường Thực nghiệm**:
   - Sử dụng `time.perf_counter()` đo lường thời gian chạy trung bình qua nhiều lượt lặp.
   - In kết quả chi tiết từng thuật toán:
     - Chi phí tối thiểu (km).
     - Chuỗi chỉ số lộ trình: `0 1 2 3 0`.
     - Lộ trình tên địa danh trực quan.
     - **Số lượng điểm phục vụ**: ví dụ `3/4 điểm (Ràng buộc ca: ≤ 7.0 phút)`.
     - **Danh sách điểm bỏ qua**: ví dụ `⚠️ Điểm bỏ qua (không đủ giờ): Công viên Tao Đàn`.
     - Thời gian thực thi chính xác đến phần nghìn mili-giây ($ms$).
4. **Bước 4 - Bảng Phân tích Độ Phức Tạp Thực Nghiệm**:
   - Tự động lấy kích thước $N$ hiện tại từ ma trận CSV và đo đạc thời gian của 3 thuật toán, đối chiếu trực tiếp với độ phức tạp lý thuyết:
     ```text
     ================================================================================
                  BẢNG PHÂN TÍCH ĐỘ PHỨC TẠP THỰC NGHIỆM
     ================================================================================
       N   |   Backtracking (ms)    |    Greedy (ms)     |   DP Held-Karp (ms)   
           |  Lý thuyết: O((N-1)!)  |  Lý thuyết: O(N²)  |  Lý thuyết: O(N²·2ⁿ)  
     --------------------------------------------------------------------------------
       5   |        0.029 ms        |     0.0371 ms      |        0.078 ms       
     --------------------------------------------------------------------------------
     ================================================================================
     ```
5. **Bước 5 - Bộ Unit Test Kiểm định (chạy với cờ `--test`)**:
   - Kiểm tra **Tính hợp lệ của chu trình**: Bắt đầu và kết thúc tại 0, không lặp lại đỉnh.
   - Kiểm tra **Tính tối ưu**: Đảm bảo số điểm $k$ phục vụ và chi phí của Dynamic Programming luôn trùng khớp tuyệt đối với kết quả Backtracking.
   - Kiểm tra **Ràng buộc thời gian**: Kiểm tra tổng thời gian của cả 3 thuật toán đều $\le \text{max\_time}$.

---

## 🧠 5. So sánh & Đánh giá 3 Thuật toán Tối ưu

| Tiêu chí | 1. Vét cạn (Backtracking) | 2. Tham lam (Greedy) | 3. Quy hoạch động (Held-Karp) |
| :--- | :--- | :--- | :--- |
| **Nguyên lý** | Duyệt nhánh cận đệ quy. Nếu thời gian hiện tại cộng đường về depot $> X \implies$ Cắt tỉa (Pruning) ngay. Duy trì kỷ lục $(k_{\max}, \text{cost}_{\min})$. | Tại mỗi bước, chọn điểm gần nhất trong số các điểm an toàn (đến được và vẫn kịp quay về depot $\le X$). Dừng ngay khi hết điểm an toàn. | Tính bảng $dp[mask][u]$ lưu thời gian ngắn nhất qua tập đỉnh $mask$. Quét mọi trạng thái $(mask, u)$ thỏa mãn $\le X$, chọn trạng thái có số bit 1 lớn nhất. |
| **Tính tối ưu** | **Tối ưu toàn cục 100%** (Tìm được số điểm $k$ nhiều nhất và quãng đường ngắn nhất). | **Xấp xỉ (Heuristic)**, có thể dừng sớm hoặc phục vụ ít hơn 1-2 điểm so với tối ưu. | **Tối ưu toàn cục 100%** (Cam kết số điểm $k$ tối đa và chi phí tối thiểu). |
| **Độ phức tạp Thời gian** | $O((N-1)!)$ (thực tế chạy rất nhanh do tỉa nhánh sớm bởi $X$) | $O(N^2)$ (chạy trong chớp mắt $< 0.05$ ms) | $O(N^2 \cdot 2^N)$ |
| **Độ phức tạp Không gian** | $O(N)$ (ngăn xếp đệ quy) | $O(N)$ (mảng trạng thái `visited`) | $O(N \cdot 2^N)$ (bảng lưu trạng thái bitmask) |
| **Ưu điểm** | Đơn giản, tốn cực ít bộ nhớ RAM, bảo đảm luôn tìm ra lời giải tốt nhất. | Chạy siêu nhanh, phù hợp cho bài toán thời gian thực với hàng trăm điểm giao. | Nhanh hơn vét cạn theo cấp số nhân, bảo đảm 100% lời giải tối ưu. |
| **Nhược điểm** | Khi $N \ge 12$ và $X$ quá lớn, số nhánh duyệt có thể tăng nhanh. | Dễ dừng lại sớm nếu điểm đầu tiên chọn dẫn vào vùng cô lập. | Giới hạn bởi bộ nhớ RAM khi $N > 20$. |
| **Phạm vi áp dụng** | $N \le 10$ điểm | $N$ lớn từ hàng chục đến hàng nghìn điểm | $N \le 16 - 18$ điểm |

---

## 🚀 6. Hướng dẫn Cài đặt & Vận hành Chi tiết

### Bước 1: Chuẩn bị Môi trường Python
Mở Terminal tại thư mục gốc của dự án:
```powershell
# Di chuyển vào thư mục code chính
cd tsp_osrm_demo

# Kích hoạt môi trường ảo (nếu đã có):
.\.venv\Scripts\Activate.ps1

# Hoặc cài đặt các thư viện cần thiết:
pip install -r requirements.txt
```

---

### Bước 2: Khởi động Máy chủ OSRM Định tuyến (Docker)
Để hệ thống tính toán đường đi xe máy chuẩn xác qua OSRM:

#### Cách 1: Sử dụng Docker Compose (Đơn giản nhất)
Tại thư mục gốc chứa file `compose.yaml`:
```powershell
docker compose up -d osrm
```
Server OSRM sẽ khởi chạy và lắng nghe tại cổng `http://localhost:5001`.

#### Cách 2: Khởi chạy thủ công bằng Docker CLI
```powershell
docker run -d --name osrm_hcm -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/hcm_2026.osrm
```

Kiểm tra server đã sẵn sàng hoạt động:
```powershell
curl http://localhost:5000/route/v1/driving/106.69805,10.77255;106.70317,10.77663
```

---

### Bước 3: Chạy Toàn trình Dự án & Tạo Bản đồ (`main.py`)
```powershell
# Chạy với máy chủ OSRM local (port 5000):
$env:OSRM_BASE_URL="http://localhost:5000"
python main.py

# Hoặc nếu dùng server mặc định:
python main.py
```
- **Kết quả xuất ra**:
  - In thông tin geocoding các điểm.
  - Ma trận `output/distance_matrix.csv` và `output/duration_matrix.csv`.
  - Kết quả số điểm phục vụ thành công $k$, các điểm bị bỏ lại, tổng km, tổng phút của từng thuật toán.
  - File bản đồ `output/route_map.html`.
- **Xem bản đồ**: Nhấp đúp mở `output/route_map.html` trên trình duyệt web. Bạn sẽ thấy các điểm phục vụ được đánh số thứ tự dừng $1 \to 2 \to 3...$ và các điểm không kịp giao được gắn huy hiệu màu xám `✕`.

---

### Bước 4: Chạy Phân tích Thuật toán Offline (`run_algorithms.py`)

> **Mục đích**: File này dùng để **chạy thuần thuật toán**, kiểm thử tính đúng đắn và đo thời gian thực nghiệm — **hoàn toàn offline**, không cần Docker, không cần OSRM, không cần kết nối mạng.

> **Điều kiện**: Cần có file `output/distance_matrix.csv` (được tạo sẵn khi chạy `main.py` ở Bước 3). Nếu chưa có, chương trình sẽ tự dùng bộ dữ liệu mẫu 4 điểm để minh họa.

#### 4.1. Các lệnh chạy

```powershell
# Di chuyển vào thư mục code:
cd tsp_osrm_demo

# ── Lệnh 1: Chạy đầy đủ (3 thuật toán + Benchmark) ──
python run_algorithms.py
```

**Kết quả mẫu trên Terminal:**
```text
[INFO] Đọc ma trận từ distance_matrix.csv (N=5)

Ma trận khoảng cách (5×5):
  [   0.00    0.52    1.36    0.94    1.45 ]
  [   0.47    0.00    1.23    0.91    1.36 ]
  [   1.38    1.44    0.00    0.77    0.95 ]
  [   0.82    0.89    1.18    0.00    1.82 ]
  [   1.73    1.65    1.78    2.04    0.00 ]

==== VÉT CẠN (BACKTRACKING) (O((N-1)!)) ====
  Chi phí: 3.34
  Lộ trình: 0 1 2 3 0
  (Bưu điện Trung tâm → Nhà thờ Đức Bà → Chợ Bến Thành → Nhà hát Thành phố → Bưu điện Trung tâm)
  Thời gian thực nghiệm: 0.020 ms
  🎯 Phục vụ 3/4 điểm (≤ 7.0p) | Bỏ qua: Công viên Tao Đàn

==== THAM LAM (GREEDY) (O(N²)) ====
  Chi phí: 2.25
  Lộ trình: 0 1 3 0
  (Bưu điện Trung tâm → Nhà thờ Đức Bà → Nhà hát Thành phố → Bưu điện Trung tâm)
  Thời gian thực nghiệm: 0.006 ms
  🎯 Phục vụ 2/4 điểm (≤ 7.0p) | Bỏ qua: Chợ Bến Thành, Công viên Tao Đàn

==== QUY HOẠCH ĐỘNG (DP HELD-KARP) (O(N²·2ᴺ)) ====
  Chi phí: 3.34
  Lộ trình: 0 1 2 3 0
  Thời gian thực nghiệm: 0.063 ms
  🎯 Phục vụ 3/4 điểm (≤ 7.0p) | Bỏ qua: Công viên Tao Đàn

======================================================================
        BENCHMARK ĐỘ PHỨC TẠP THỰC NGHIỆM
======================================================================
Thuật toán                     | Lý thuyết       |     Thực nghiệm
----------------------------------------------------------------------
  Vét cạn (Backtracking)       | O((N-1)!)       |        0.038 ms
  Tham lam (Greedy)            | O(N²)           |        0.005 ms
  Quy hoạch động (DP Held-Karp) | O(N²·2ᴺ)       |        0.064 ms
======================================================================
```

```powershell
# ── Lệnh 2: Chỉ chạy Unit Test kiểm tra tính đúng đắn ──
python run_algorithms.py --test
```

**Kết quả mẫu:**
```text
============================================================
           BỘ UNIT TEST KIỂM THỬ THUẬT TOÁN
============================================================
Ma trận N = 5, Ràng buộc: 7.0 phút

  [TEST 1] Backtracking   : 3/4 điểm | Chi phí = 3.3400 (Optimal) | PASSED ✅
  [TEST 2] Greedy         : 2/4 điểm | Chi phí = 2.2500 (gấp 0.67× optimal) | PASSED ✅
  [TEST 3] DP             : 3/4 điểm | Chi phí = 3.3400 (Optimal) | PASSED ✅
  [TEST 4] Ràng buộc thời gian ≤ 7.0p: PASSED ✅
------------------------------------------------------------
KẾT QUẢ: TẤT CẢ PASSED 🎉
============================================================
```

```powershell
# ── Lệnh 3: Chỉ chạy 1 thuật toán cụ thể ──
python run_algorithms.py --alg greedy          # Chỉ Greedy
python run_algorithms.py --alg dp              # Chỉ DP
python run_algorithms.py --alg backtracking    # Chỉ Backtracking
python run_algorithms.py --alg greedy dp       # Greedy + DP (bỏ Backtracking)
```

#### 4.2. Tổng hợp các tùy chọn (flags)

| Lệnh | Ý nghĩa |
| :--- | :--- |
| `python run_algorithms.py` | Chạy đầy đủ: in ma trận → 3 thuật toán → benchmark |
| `python run_algorithms.py --test` | Chỉ chạy **Unit Test** kiểm tra tính đúng đắn |
| `python run_algorithms.py --alg <tên>` | Chỉ chạy thuật toán được chọn (`backtracking`, `greedy`, `dp`) |

#### 4.3. Giải thích nội dung kết quả

| Mục hiển thị | Ý nghĩa |
| :--- | :--- |
| **Chi phí** | Tổng quãng đường lộ trình (km) |
| **Lộ trình** | Chuỗi chỉ số các điểm theo thứ tự ghé thăm (0 = Depot) |
| **Thời gian thực nghiệm** | Thời gian CPU chạy thuật toán (mili-giây), đo bằng `perf_counter` |
| **Phục vụ k/N điểm** | Số điểm giao thành công / tổng số điểm cần giao |
| **Bỏ qua: ...** | Tên các điểm không kịp giao do hết thời gian ca |
| **BENCHMARK** | Bảng so sánh thời gian thực tế vs độ phức tạp lý thuyết |
| **Unit Test PASSED/FAILED** | Kiểm tra chu trình hợp lệ, tính tối ưu, ràng buộc thời gian |

---

### Bước 5: Khởi chạy Ứng dụng Web Tương tác (Streamlit Web App - `app.py`)

Hệ thống cung cấp giao diện Web trực quan theo đúng tài liệu đặc tả SRS:
- **Nguồn địa điểm**: Chọn Preset Demo (5, 8, 12 điểm) hoặc Nhập địa chỉ thủ công kèm Geocoding tự động.
- **Giới hạn thời gian ca**: Nhập số phút bằng **ô nhập số (không dùng slider)**; để trống = không giới hạn thời gian.
- **Bản đồ Folium tương tác**: Hiển thị số thứ tự ghé thăm **vàng hổ phách (#ffc107)**, biển báo rẽ, và điểm bỏ qua **(✕)**.
- **Dashboard số liệu**: Thẻ Key Metrics, Terminal Console ghi log trực tiếp, Bảng phân tích độ phức tạp và Biểu đồ Runtime Benchmark Plotly.

#### Hướng dẫn chạy Web:
```powershell
# Di chuyển vào thư mục code chính:
cd tsp_osrm_demo

# Khởi chạy ứng dụng Streamlit:
streamlit run app.py
```
Trình duyệt sẽ tự động mở trang web tại địa chỉ: `http://localhost:8501`.

---

## 📂 7. Cấu trúc Thư mục Dự án

```text
tsp_osrm_demo/
│
├── compose.yaml                    # Docker Compose cấu hình OSRM và Python App
├── Dockerfile.osmium               # Dockerfile build môi trường osmium-tool cắt bản đồ
├── motorcycle.lua                  # Tệp cấu hình luật lưu thông xe máy Việt Nam
├── vietnam-261105.osm.pbf          # Dữ liệu OSM thô toàn quốc Việt Nam (~332 MB)
├── hcm_2026.osm.pbf                # Dữ liệu bản đồ sau khi trích xuất TP.HCM (~29.7 MB)
├── hcm_2026.osrm*                  # Bộ tệp chỉ mục đồ thị mạng lưới MLD sau khi tiền xử lý
│
└── tsp_osrm_demo/                  # Thư mục mã nguồn chính của ứng dụng
    ├── app.py                      # Giao diện Web tương tác Streamlit (theo đặc tả SRS v1.1)
    ├── places.csv                  # Danh sách điểm giao hàng đầu vào & giới hạn thời gian cứng
    ├── coords_cache.json           # Bộ đệm lưu trữ tọa độ đã geocode (tránh gọi lại API)
    ├── main.py                     # Điều phối toàn trình CLI (Online OSRM + GIS Folium Map)
    ├── thuat_toan.py               # Hiện thực 3 thuật toán Selective TSP: Backtracking, Greedy, DP Held-Karp
    ├── api_calls.py                # Wrapper gọi OSRM Table API, Route API & Geocoding ArcGIS
    ├── output.py                   # Xuất ma trận CSV, vẽ bản đồ Folium với thứ tự lộ trình & điểm bỏ qua
    ├── run_algorithms.py           # Module chạy phân tích thực nghiệm & benchmark offline
    ├── Dockerfile                  # Dockerfile đóng gói ứng dụng Python & Web App
    ├── requirements.txt            # Danh mục thư viện Python (streamlit, folium, plotly, requests, pandas)
    ├── README.md                   # Tài liệu phân tích và hướng dẫn kỹ thuật chi tiết
    └── output/
        ├── distance_matrix.csv     # Ma trận khoảng cách thực tế giữa các điểm (km)
        ├── duration_matrix.csv     # Ma trận thời gian di chuyển thực tế (phút)
        └── route_map.html          # Bản đồ số tương tác Folium trên nền Google Maps
```

---
*Tài liệu được xây dựng phục vụ nghiên cứu và thực nghiệm bài toán Tối ưu hóa Lộ trình Vận chuyển Chọn lọc (Selective TSP / Orienteering) trên dữ liệu không gian địa lý đô thị thực tế.*
