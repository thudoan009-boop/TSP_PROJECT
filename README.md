# Tối Ưu Hóa Lộ Trình Giao Hàng Bằng OSRM & Thuật Toán Tối Ưu (Selective TSP)

Dự án nghiên cứu, hiện thực hóa và đánh giá giải pháp cho **Bài toán Người giao hàng chọn lọc theo ràng buộc thời gian (Time-Constrained Selective TSP / Orienteering Problem)** trên mạng lưới giao thông đường bộ thực tế tại **Việt Nam** (với dữ liệu thực nghiệm trọng điểm tại **TP. Hồ Chí Minh**).

Hệ thống kết hợp dịch vụ định tuyến **OSRM Public API (nền OpenStreetMap)**, dịch vụ định vị địa lý **ArcGIS Geocoding** và 3 thuật toán tối ưu kinh điển: **Vét cạn (Backtracking)**, **Tham lam (Greedy)**, và **Quy hoạch động (Dynamic Programming - Held-Karp)**. Dự án cung cấp cả giao diện **Web App trực quan (Streamlit)** và **Dòng lệnh CLI (`main.py`)** đo đạc hiệu năng thực nghiệm chi tiết ($ms$).

---

## 📑 Mục lục
1. [Giới thiệu dự án & Mô hình bài toán](#1-giới-thiệu-dự-án--mô-hình-bài-toán)
2. [Kiến trúc hệ thống & Dữ liệu định tuyến](#2-kiến-trúc-hệ-thống--dữ-liệu-định-tuyến)
3. [Ba thuật toán tối ưu & Đánh giá hiệu năng](#3-ba-thuật-toán-tối-ưu--đánh-giá-hiệu-năng)
4. [Hướng dẫn cài đặt & Cách sử dụng](#4-hướng-dẫn-cài-đặt--cách-sử-dụng)
   - 4.1. Cài đặt môi trường
   - 4.2. Chạy ứng dụng Web trực quan (`app.py`)
   - 4.3. Chạy báo cáo dòng lệnh CLI (`main.py`)
   - 4.4. Cách sử dụng trên giao diện Web
5. [Nghiên cứu mở rộng & Hướng phát triển](#5-nghiên-cứu-mở-rộng--hướng-phát-triển)
6. [Cấu trúc thư mục dự án](#6-cấu-trúc-thư-mục-dự-án)

---

## 1. Giới thiệu dự án & Mô hình bài toán

### 1.1. Bối cảnh thực tế (Last-Mile Delivery)
Trong thực tế giao hàng đô thị, shipper thường nhận một danh sách gồm $N - 1$ điểm giao cùng một **giới hạn thời gian ca làm việc nghiêm ngặt $X$** (ví dụ $X = 7$ phút hoặc $X = 120$ phút). Do điều kiện đường sá và cự ly, việc ghé thăm toàn bộ $N - 1$ điểm thường không khả thi trong quỹ thời gian $X$. 

Vì vậy, bài toán thực tế đặt ra là: **Giao được nhiều đơn nhất có thể ($k \le N - 1$) và bảo đảm quay về kho xuất phát trước khi hết giờ làm việc.**

### 1.2. Mô hình tối ưu 2 mục tiêu bậc thang (Lexicographical Objectives)
Hệ thống giải quyết bài toán theo thứ tự ưu tiên kép:
1. **Mục tiêu ưu tiên 1 (Tối đa hóa số đơn phục vụ):** Tìm tập con gồm $k$ điểm giao sao cho $k$ là lớn nhất ($k \le N - 1$).
2. **Mục tiêu ưu tiên 2 (Tối thiểu hóa chi phí di chuyển):** Trong các lộ trình cùng đạt số điểm $k$ tối đa, chọn lộ trình có **tổng quãng đường ngắn nhất** (km) hoặc **tổng thời gian nhanh nhất** (phút).
3. **Ràng buộc thời gian cứng:**
   $$\text{Thời gian: Kho (DEPOT)} \to \text{Ghé } k \text{ điểm} \to \text{Quay về Kho} \le X \text{ (phút)}$$
4. **Xử lý đơn tồn đọng:** Các điểm không kịp ghé thăm được nhận diện là **bị bỏ qua**, hiển thị danh sách rõ ràng và gắn biểu tượng màu xám `✕` trên bản đồ số.
5. **Tương thích bài toán TSP truyền thống:** Khi không đặt giới hạn thời gian (để trống $X \implies X = \infty$), hệ thống tự động tìm chu trình khép kín tối ưu đi qua đủ **100% các điểm**.

---

## 2. Kiến trúc hệ thống & Dữ liệu định tuyến

Hệ thống được thiết kế theo luồng xử lý tinh gọn, không đòi hỏi cài đặt máy chủ cục bộ phức tạp:

```text
[Danh sách địa chỉ] ──► [ArcGIS Geocoding] ──► [OSRM Public API] ──► [3 Thuật toán TSP] ──► [Bản đồ Folium & Streamlit]
(CSV hoặc Nhập tay)     (Chuyển sang Lat/Lon)   (Ma trận km & phút)   (Backtracking/Greedy/DP)  (Trực quan hóa lộ trình)
```

- **ArcGIS World Geocoding:** Tự động chuyển đổi tên/địa chỉ tiếng Việt thành tọa độ địa lý $(\text{lat}, \text{lon})$. Tích hợp bộ đệm `coords_cache.json` để không phải gọi API lặp lại.
- **OSRM Public Server (`router.project-osrm.org`):** Sử dụng Table API để trích xuất ma trận khoảng cách (m) và thời gian (s) thực tế giữa toàn bộ các cặp điểm, và Route API để lấy hình học đường đi (GeoJSON).
- **Lưu ý về dữ liệu:** Dữ liệu bản đồ được xây dựng từ nền tảng OpenStreetMap (OSM) cộng đồng tại Việt Nam. Do điều kiện giao thông biến động theo thời gian thực (ùn tắc, phân luồng tạm thời...), các thông số đóng vai trò là **dữ liệu mô phỏng tham chiếu thực tế**, phản ánh đúng cấu trúc mạng đường bất đối xứng để phục vụ kiểm thử và so sánh thuật toán.

---

## 3. Ba thuật toán tối ưu & Đánh giá hiệu năng

Cả 3 thuật toán đều nhận cùng ma trận khoảng cách, ma trận thời gian và giới hạn ca $X$ từ tệp `thuat_toan.py`:

| Tiêu chí | 1. Vét cạn (Backtracking) | 2. Tham lam (Greedy Lookahead) | 3. Quy hoạch động (Held-Karp DP) |
| :--- | :--- | :--- | :--- |
| **Nguyên lý** | Duyệt cây DFS có cắt tỉa nhánh cận. Nếu $t_{\text{hiện tại}} + T_{u \to 0} > X \implies$ Cắt tỉa ngay. | Tại mỗi bước, chỉ xét các điểm an toàn (đến được và kịp về kho $\le X$), chọn điểm gần nhất. | Bảng $dp[\text{mask}][u]$ lưu thời gian nhỏ nhất qua tập đỉnh bitmask, kết thúc tại $u$. Quét chọn trạng thái hợp lệ có $k$ lớn nhất. |
| **Tính tối ưu** | **Tối ưu toàn cục 100%** | **Xấp xỉ Heuristic** (có thể ít hơn 1 đơn so với tối ưu) | **Tối ưu toàn cục 100%** |
| **Độ phức tạp Thời gian** | $O(N!)$ | $O(N^2)$ (cực nhanh $< 0.05$ ms) | $O(N^2 \cdot 2^N)$ |
| **Độ phức tạp Không gian**| $O(N)$ | $O(N)$ | $O(N \cdot 2^N)$ |
| **Khuyến nghị áp dụng** | Quy mô nhỏ ($N \le 10$) | Quy mô lớn ($N \ge 18$ đến hàng nghìn điểm) | Quy mô vừa ($N \le 16 - 18$) |

---

## 4. Hướng dẫn cài đặt & Cách sử dụng

Dự án chạy trực tiếp với Python thuần, **hoàn toàn không cần cài đặt Docker hay build bản đồ**.

### 4.1. Cài đặt môi trường
Mở Terminal / PowerShell tại thư mục dự án:
```powershell
# 1. Kích hoạt môi trường ảo (nếu có):
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện cần thiết:
pip install -r tsp_osrm_demo/requirements.txt
```

---

### 4.2. Chạy ứng dụng Web trực quan (`app.py`)
Giao diện Web tương tác hoàn chỉnh xây dựng trên Streamlit:
```powershell
streamlit run tsp_osrm_demo/app.py
```
> Trình duyệt sẽ tự động mở tại địa chỉ: **`http://localhost:8501`**.

---

### 4.3. Chạy báo cáo dòng lệnh CLI (`main.py`)
Hỗ trợ chạy cả 3 thuật toán để so sánh hoặc **chạy riêng lẻ từng thuật toán theo yêu cầu của giảng viên**:

```powershell
# Chạy cả 3 thuật toán để so sánh benchmark (mặc định):
python tsp_osrm_demo/main.py

# Chỉ chạy riêng thuật toán Tham lam (Greedy):
python tsp_osrm_demo/main.py --algo greedy

# Chỉ chạy riêng thuật toán Vét cạn (Backtracking):
python tsp_osrm_demo/main.py --algo bt

# Chỉ chạy riêng thuật toán Quy hoạch động (Held-Karp DP):
python tsp_osrm_demo/main.py --algo dp
```
- **Terminal:** In chi tiết chặng đi, số điểm phục vụ, thời gian chạy thực nghiệm ($ms$) và Bảng Benchmark đối chứng lý thuyết vs thực nghiệm.
- **Bản đồ:** Tự động lưu bản đồ vào `tsp_osrm_demo/output/route_map.html` (nhấp đúp chuột để mở trên trình duyệt).

---

### 4.4. Cách sử dụng trên giao diện Web (`app.py`)
Giao diện được thiết kế trực quan gồm 2 cột:

1. **Cột trái (Thiết lập bài toán):**
   - **Nguồn dữ liệu:** Chọn **Preset Demo** (có sẵn 3 bộ dữ liệu chuẩn: *Nhỏ 5 điểm*, *Vừa 8 điểm*, *Lớn 12 điểm* tại Quận 1 TP.HCM) hoặc chọn **Nhập địa chỉ thủ công** để tự gõ địa chỉ tùy ý.
   - **Giới hạn thời gian ca làm việc (phút):** Nhập số phút mong muốn (ví dụ: `7` hoặc `30`). Nếu muốn tìm lộ trình qua toàn bộ 100% các điểm, chỉ cần **để trống ô này**.
   - **Chọn thuật toán chạy:** Hộp chọn cho phép bật/tắt linh hoạt (chọn chạy riêng lẻ 1 thuật toán bất kỳ hoặc chạy cả 3 thuật toán để so sánh).
   - Bấm nút **🚀 Tối ưu hóa lộ trình**.
2. **Cột phải (Bảng điều khiển kết quả):**
   - **3 Thẻ Key Metrics:** Xem tổng quãng đường (km), thời gian di chuyển (phút), số điểm hoàn thành ($k/n$) và thời gian thực thi của từng thuật toán.
   - **Bản đồ số tương tác:** Hiển thị lộ trình bám sát đường phố thực tế; số thứ tự ghé thăm được đánh số vàng hổ phách (`1`, `2`, `3`...), các điểm không kịp giao được đánh dấu màu xám `✕`.
   - **Terminal Console & Tải Log:** Theo dõi log thực thi từng bước và tải tệp `.txt` về máy.
   - **Biểu đồ Runtime Benchmark Plotly:** So sánh trực quan thời gian chạy của 3 thuật toán bằng biểu đồ cột.

---

## 5. Nghiên cứu mở rộng & Hướng phát triển

### 5.1. Thử nghiệm mở rộng với OSRM Docker Local
Nhóm đã tiến hành nghiên cứu mở rộng việc tự xây dựng máy chủ OSRM cục bộ trên Docker:
- Cắt lọc dữ liệu bản đồ `hcm_2026.osm.pbf` từ Geofabrik bằng `osmium-tool`.
- Thử nghiệm cấu hình phương tiện xe máy `motorcycle.lua` (tốc độ tham chiếu 20–40 km/h, đường hẻm dân cư).
- *Kết luận thử nghiệm:* Do luật giao thông xe máy đô thị tại Việt Nam rất phức tạp (ùn tắc giờ cao điểm, đường cấm theo giờ, hành vi luồn lách...) nên cấu hình Lua cần thêm thời gian hiệu chỉnh sâu. Do đó, hệ thống chọn sử dụng **OSRM Public API** cho phiên bản chính thức để đảm bảo tính khách quan và ổn định.

### 5.2. Hướng phát triển tiếp theo
1. **Hoàn thiện cấu hình xe máy:** Tiếp tục tinh chỉnh `motorcycle.lua` và triển khai máy chủ OSRM chuyên dụng riêng cho xe máy.
2. **Cải tiến nghiệm cho Greedy bằng 2-Opt / 3-Opt:** Áp dụng tìm kiếm cục bộ để khử các cạnh tự cắt chéo, giúp lộ trình ngắn hơn mà vẫn duy trì tốc độ mili-giây.
3. **Ứng dụng Meta-heuristic cho quy mô lớn ($N > 20$):** Nghiên cứu Giải thuật Di truyền (Genetic Algorithm) và Tối ưu hóa bầy kiến (Ant Colony Optimization) để giải bài toán hàng trăm điểm giao hàng.
4. **Mở rộng bài toán thực tế:** Bổ sung ràng buộc khung giờ nhận hàng (Time Windows) và bài toán điều phối cho đội xe nhiều người (Vehicle Routing Problem - VRP).

---

## 6. Cấu trúc thư mục dự án

```text
tsp_osrm_demo/
├── tsp_osrm_demo/                  # Thư mục mã nguồn chính của ứng dụng
│   ├── app.py                      # Giao diện Web tương tác Streamlit
│   ├── main.py                     # Điều phối chạy dòng lệnh CLI & in Benchmark
│   ├── thuat_toan.py               # Cài đặt 3 thuật toán: Backtracking, Greedy, DP Held-Karp
│   ├── api_calls.py                # Gọi OSRM Table/Route API và ArcGIS Geocoding
│   ├── output.py                   # Tạo bản đồ Folium và xuất ma trận chi phí
│   ├── places.csv                  # Dữ liệu danh sách địa điểm kiểm thử mặc định
│   ├── coords_cache.json           # Bộ đệm lưu trữ tọa độ đã tra cứu
│   ├── requirements.txt            # Danh sách thư viện Python cần cài đặt
│   └── output/                     # Thư mục chứa kết quả xuất ra (bản đồ, ma trận csv)
│       └── route_map.html          # Bản đồ số tương tác Folium
│
├── compose.yaml                    # (Thử nghiệm mở rộng) Cấu hình chạy OSRM local bằng Docker
├── motorcycle.lua                  # (Thử nghiệm mở rộng) Profile định tuyến xe máy
├── Dockerfile.osmium               # (Thử nghiệm mở rộng) Dockerfile cắt bản đồ OSM
└── README.md                       # Tài liệu hướng dẫn chi tiết
```
