# Dockerfile
FROM python:3.11-slim

# PYTHONUNBUFFERED: 讓 log 直接輸出到終端，方便 docker logs 查看
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# 先複製 requirements.txt 以利用 Docker layer 快取
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# 單一 worker + 多執行緒：
# 「更新資料」熱更新是改記憶體內的資料，多 worker 會導致只有其中一個被更新，
# 這個流量級別單 worker 多執行緒已足夠。
CMD exec gunicorn --bind "0.0.0.0:$PORT" --workers 1 --threads 8 --timeout 60 --access-logfile - app:app
