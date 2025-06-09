# Dockerfile

# 1. 使用官方 Python 映像作為基礎
# 選擇一個適合您 Python 版本的映像，slim 版本比較小；input_parser.py的程式碼使用了 Python 3.10 才有的新語法，所以使用3.11版本
FROM python:3.11-slim

# 2. 設定環境變數
#   - PYTHONUNBUFFERED: 確保 Python 的輸出 (print, log) 直接送到終端，方便在 Cloud Run 中查看日誌
#   - PORT: Cloud Run 會設定這個環境變數，告訴您的應用程式應該監聽哪個埠號 (預設 8080)
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 3. 設定工作目錄
# 之後的 COPY, RUN 指令都會在這個目錄下執行
WORKDIR /app

# 4. 複製依賴性檔案並安裝套件
# 只複製 requirements.txt 可以利用 Docker 的層快取機制，
# 只有當 requirements.txt 變更時，才會重新執行 pip install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 複製應用程式的其餘所有檔案到工作目錄
# 這會包括 app.py, data/ 資料夾及其內容 (Nutrition_Facts.xlsx)
COPY . .

# 6. 開放應用程式將監聽的埠號 (與 ENV PORT 相同)
# 這主要是文件作用，實際埠號由 Gunicorn 綁定
EXPOSE 8080

# 7. 設定容器啟動時執行的指令
# 使用 Gunicorn 作為生產級 WSGI 伺服器來運行您的 Flask 應用 (app:app 指的是 app.py 中的 app 物件)
# --bind 0.0.0.0:$PORT 表示 Gunicorn 會監聽所有網路介面，並使用 PORT 環境變數指定的埠號
# --workers 建議根據您的 CPU 資源設定，對於小型 Cloud Run 實例，2-4 個通常足夠
# --timeout 增加超時時間，以防某些請求處理較久
CMD exec gunicorn --bind "0.0.0.0:$PORT" --workers 2 --timeout 120 app:app
