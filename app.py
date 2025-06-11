# app.py (整合 Google Sheets 的完整版本)
import os
import traceback
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# --- 初始化區塊 ---
app = Flask(__name__)
# 將所有服務模組初始化為 None，以應對可能的啟動失敗
data_loader, input_parser, calorie_calculator = None, None, None
handler = None
configuration = None

try:
    load_dotenv()
    # 匯入您自訂的模組
    from data_loader import DataLoader
    from input_parser import UserInputParser
    from calorie_calculator import CalorieCalculator
    
    # 從環境變數讀取 Google Sheets API 金鑰的 JSON 內容
    GOOGLE_API_KEY_JSON = os.getenv('GOOGLE_SHEETS_API_KEY', '').strip()
    # *** 請在這裡填寫您在 Google Drive 中建立的試算表確切檔案名稱 ***
    YOUR_GOOGLE_SHEET_NAME = "Nutrition_Facts" 

    if not GOOGLE_API_KEY_JSON:
         raise ValueError("GOOGLE_SHEETS_API_KEY 環境變數未設定。")
    
    # 初始化 DataLoader，傳入金鑰和試算表名稱
    data_loader = DataLoader(secret_key_json_str=GOOGLE_API_KEY_JSON, sheet_name=YOUR_GOOGLE_SHEET_NAME)
    
    # 初始化其他依賴 DataLoader 的模組
    input_parser = UserInputParser(data_loader)
    calorie_calculator = CalorieCalculator(data_loader)
    
    # 初始化 Line Bot SDK
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    
    app.logger.info("所有服務模組已成功初始化，使用 Google Sheets 作為資料來源。")

except Exception as e:
    # 如果在啟動的任何環節發生錯誤，記錄下來
    app.logger.error(f"應用程式啟動時發生致命錯誤: \n{traceback.format_exc()}")


# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    # 如果 handler 在啟動時初始化失敗，則回傳 500 錯誤
    if not handler:
        app.logger.error("Webhook 請求失敗，因為 handler 未被成功初始化。")
        abort(500)
        
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 訊息事件處理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_input = event.message.text.strip()
        
        # 再次檢查服務是否已成功初始化
        if not all([data_loader, input_parser, calorie_calculator]):
            reply_text = "抱歉，機器人目前正在維護中，暫時無法提供服務。"
        else:
            try:
                # 1. 呼叫 InputParser 進行解析
                parsed_data = input_parser.parse(user_input)
                
                if parsed_data.get("error"):
                    # 如果解析階段就出錯 (例如找不到品牌/飲品)
                    reply_text = f"查無資料：{parsed_data['error']}，請遵循「品牌 品名 [選項]」格式。"
                else:
                    # 2. 呼叫 CalorieCalculator 進行計算
                    result = calorie_calculator.calculate(parsed_data)
                    
                    if result:
                        # 3. 組合成功的回覆
                        calories = result["calories"]
                        sugar = result["sugar"]
                        reply_text = f"「{user_input}」\n熱量為 {calories} 大卡，糖量為 {sugar} 克"
                    else:
                        # 如果計算階段回傳 None (例如，找不到完全符合的飲品)
                        reply_text = "查無此飲品，請確認品牌、品名、尺寸等資訊是否正確。"

            except Exception as e:
                app.logger.error(f"處理訊息 '{user_input}' 時發生錯誤: {e}", exc_info=True)
                reply_text = "抱歉，處理您的請求時發生了內部錯誤。"

        # 4. 回覆訊息給使用者
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )

# --- 啟動伺服器 ---
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    # 在生產環境中，debug 應設為 False。Gunicorn 會處理好這一切。
    app.run(host='0.0.0.0', port=port, debug=False)