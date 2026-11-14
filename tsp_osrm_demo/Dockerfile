
FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn vào container
COPY . .

# Chạy chương trình chính
CMD ["python", "main.py"]
