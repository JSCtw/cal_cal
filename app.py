# app.py (最小化測試版本)
import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError

app = Flask(__name__)

# 我們仍然讀取 Channel Secret，以測試秘密注入是否正常
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()

# 只有在 SECRET 存在時才初始化 handler
handler = None
if LINE_CHANNEL_SECRET:
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    app.logger.info("測試模式：成功初始化 WebhookHandler。")
else:
    app.logger.warning("測試模式：LINE_CHANNEL_SECRET 未設定，將無法驗證簽名。")

@app.route("/callback", methods=['POST'])
def callback():
    # 這個版本只做最簡單的事：收到請求，打印日誌，回傳 OK
    app.logger.info("最小化測試 Webhook 已成功接收請求！")

    # 由於 handler 可能未初始化，我們只在它存在時才做驗證
    if handler:
        try:
            signature = request.headers.get('X-Line-Signature')
            body = request.get_data(as_text=True)
            handler.handle(body, signature)
        except InvalidSignatureError:
            app.logger.error("最小化測試時發生簽名驗證錯誤。")
            abort(400) # 簽名錯誤，回傳 400

    return 'OK', 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    # 在生產環境中，debug 應設為 False。Gunicorn 會處理好這一切。
    app.run(host='0.0.0.0', port=port, debug=False)