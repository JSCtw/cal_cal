# app.py (超最小化檔案讀取測試版本)
import os
import pandas as pd # 直接在這裡匯入
from flask import Flask, request, abort

app = Flask(__name__)

# --- 在應用程式啟動時，直接嘗試讀取一個檔案 ---
try:
    app.logger.info("--- 測試：準備讀取 'data/brands_alias.csv' ---")
    csv_path = 'data/brands_alias.csv'
    df = pd.read_csv(csv_path, encoding='utf-8') # 明確指定 UTF-8 編碼
    app.logger.info(f"--- 測試成功：成功讀取 '{csv_path}'，共 {len(df)} 行資料。---")
except Exception as e:
    # 如果發生任何錯誤，將其詳細記錄下來
    app.logger.error(f"--- 測試失敗：讀取 '{csv_path}' 時發生嚴重錯誤！---", exc_info=True)
# --- 測試結束 ---

# 我們保留一個能運作的 Webhook 端點
@app.route("/callback", methods=['POST'])
def callback():
    app.logger.info("超最小化測試 Webhook 已成功接收請求！")
    return 'OK', 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)