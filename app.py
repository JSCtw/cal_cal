# app.py
import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# 匯入您自己的模組
from data_loader import DataLoader
from input_parser import UserInputParser
from calorie_calculator import CalorieCalculator

# --- 初始化 ---
load_dotenv()
app = Flask(__name__)

# Line Bot SDK 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 建立我們核心服務的實例
try:
    data_loader = DataLoader(file_path="data/Nutrition_Facts.xlsx")
    input_parser = UserInputParser(data_loader)
    calorie_calculator = CalorieCalculator(data_loader)
    app.logger.info("所有服務模組已成功初始化。")
except Exception as e:
    app.logger.error(f"服務模組初始化失敗: {e}", exc_info=True)
    # 在這種情況下，應用程式啟動失敗是合理的
    data_loader = None
    input_parser = None
    calorie_calculator = None


# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
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
        user_input = event.message.text
        
        # 檢查服務是否已成功初始化
        if not all([data_loader, input_parser, calorie_calculator]):
            reply_text = "抱歉，機器人目前正在維護中，暫時無法提供服務。"
        else:
            try:
                # 1. 呼叫 InputParser 進行解析
                parsed_data = input_parser.parse(user_input)
                
                if parsed_data.get("error"):
                    # 如果解析階段就出錯 (例如找不到品牌/飲品)
                    reply_text = f"查無飲品：{parsed_data['error']}"
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
                app.logger.error(f"處理訊息 '{user_input}' 時發生未預期的錯誤: {e}", exc_info=True)
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