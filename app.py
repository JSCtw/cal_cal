# app.py (最終除錯版本)
import os
import traceback  # <-- 匯入 traceback 模組，用於獲取詳細錯誤資訊
from flask import Flask, request, abort

# --- 應用程式和日誌記錄器初始化 ---
app = Flask(__name__)
app.logger.info("--- [除錯] app.py 開始執行 ---")


# --- 主體：將所有初始化過程包裹在一個大的 try...except 中 ---
# 這個結構可以捕捉到任何在啟動階段發生的錯誤
try:
    # 逐一匯入並初始化您的模組，並在每一步打印日誌
    app.logger.info("--- [除錯] 準備匯入自訂模組 ---")
    
    from data_loader import DataLoader
    app.logger.info("--- [除錯] 成功匯入 DataLoader ---")

    from input_parser import UserInputParser
    app.logger.info("--- [除錯] 成功匯入 InputParser ---")

    from calorie_calculator import CalorieCalculator
    app.logger.info("--- [除錯] 成功匯入 CalorieCalculator ---")

    # 開始初始化
    app.logger.info("--- [除錯] 準備初始化 DataLoader... ---")
    data_loader = DataLoader(file_path="data/Nutrition_Facts.xlsx")
    app.logger.info("--- [除錯] 成功初始化 DataLoader ---")

    app.logger.info("--- [除錯] 準備初始化 InputParser... ---")
    input_parser = UserInputParser(data_loader)
    app.logger.info("--- [除錯] 成功初始化 InputParser ---")

    app.logger.info("--- [除錯] 準備初始化 CalorieCalculator... ---")
    calorie_calculator = CalorieCalculator(data_loader)
    app.logger.info("--- [除錯] 成功初始化 CalorieCalculator ---")

    # 初始化 Line SDK
    from linebot.v3 import WebhookHandler
    from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
    from linebot.v3.webhooks import MessageEvent, TextMessageContent
    
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    app.logger.info("--- [除錯] 成功初始化 Line SDK ---")

    app.logger.info("--- [除錯] 所有模組初始化成功！應用程式準備就緒。---")

except Exception as e:
    # --- 這是最關鍵的部分 ---
    # 如果在 try 區塊中發生任何錯誤，我們將其完整的 Traceback 資訊格式化
    # 並作為一條非常明顯的 ERROR 日誌打印出來。
    error_details = traceback.format_exc()
    app.logger.error(f"\n\n!!!!!! 應用程式啟動時發生致命錯誤 !!!!!!\n\n{error_details}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    # 重新引發異常，讓容器知道啟動失敗了，但我們已經記錄下了關鍵資訊
    raise

# --- Webhook 路由 (如果啟動成功，它才會正常運作) ---
@app.route("/callback", methods=['POST'])
def callback():
    # ... (這裡的邏輯暫時不重要，因為錯誤發生在啟動階段) ...
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # ... (這裡的邏輯暫時不重要) ...
    pass

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)