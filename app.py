# app.py
import os
import traceback
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# --- 初始化 ---
app = Flask(__name__)
data_loader, input_parser, calorie_calculator = None, None, None

try:
    load_dotenv()
    from data_loader import DataLoader
    from input_parser import UserInputParser
    from calorie_calculator import CalorieCalculator
    
    data_loader = DataLoader(data_folder="data")
    input_parser = UserInputParser(data_loader)
    calorie_calculator = CalorieCalculator(data_loader)
    
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    
    app.logger.info("所有服務模組已成功初始化。")
except Exception:
    app.logger.error(f"應用程式啟動時發生致命錯誤: \n{traceback.format_exc()}")

# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        if handler: handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 訊息事件處理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_input = event.message.text
        
        if not all([data_loader, input_parser, calorie_calculator]):
            reply_text = "抱歉，機器人目前正在維護中，暫時無法提供服務。"
        else:
            try:
                parsed_data = input_parser.parse(user_input)
                if parsed_data.get("error"):
                    reply_text = f"查無飲品：{parsed_data['error']}"
                else:
                    result = calorie_calculator.calculate(parsed_data)
                    if result:
                        reply_text = f"「{user_input}」\n熱量為 {result['calories']} 大卡，糖量為 {result['sugar']} 克"
                    else:
                        reply_text = "查無此飲品，請確認品牌、品名、尺寸等資訊是否正確。"
            except Exception as e:
                app.logger.error(f"處理訊息 '{user_input}' 時發生錯誤: {e}", exc_info=True)
                reply_text = "抱歉，處理您的請求時發生了內部錯誤。"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )

# --- 啟動伺服器 ---
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)