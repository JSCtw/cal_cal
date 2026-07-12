# app.py
"""LINE Bot 進入點（Flask + gunicorn）。

設計重點：
- 資料層初始化失敗時 app 仍可啟動（回覆維護訊息、/healthz 回報 degraded），
  之後每次收到訊息會自動重試初始化。
- 「更新資料」隱藏指令：重新從 Google Sheets 載入（需搭配單一 gunicorn worker，
  否則只會更新到其中一個 worker 的記憶體）。
"""
import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from calorie_calculator import CalorieCalculator
from data_loader import DataLoader
from input_parser import UserInputParser

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cal_cal")

app = Flask(__name__)

GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Nutrition_Facts").strip()
CACHE_PATH = os.getenv("SHEET_CACHE_PATH", "cache/sheet_cache.json").strip()

# LINE SDK 一律先建立：缺憑證時驗簽會失敗回 400，但 app 本身能啟動，
# 不會像舊版一樣因 handler=None 導致整個模組 import 失敗。
configuration = Configuration(
    access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip() or "not-set")
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET", "").strip() or "not-set")

_services = {}
_lock = threading.Lock()


def _google_key() -> str:
    """優先讀金鑰檔（GOOGLE_SERVICE_ACCOUNT_FILE），檔案不存在時退回 JSON 字串環境變數。"""
    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    if path:
        logger.warning("找不到金鑰檔 %s，改用 GOOGLE_SHEETS_API_KEY 環境變數", path)
    return os.getenv("GOOGLE_SHEETS_API_KEY", "").strip()


def init_services(force: bool = False) -> bool:
    """初始化資料層。失敗時回傳 False，app 仍可運作並於下次訊息再重試。"""
    with _lock:
        if _services.get("loader") and not force:
            return True
        try:
            key = _google_key()
            if not key:
                raise ValueError("未設定 GOOGLE_SERVICE_ACCOUNT_FILE 或 GOOGLE_SHEETS_API_KEY")
            loader = DataLoader(key, GOOGLE_SHEET_NAME, cache_path=CACHE_PATH)
            loader.load()
            _services["loader"] = loader
            _services["parser"] = UserInputParser(loader)
            _services["calculator"] = CalorieCalculator(loader)
            logger.info("資料層初始化完成（來源：%s）", loader.source)
            return True
        except Exception:  # noqa: BLE001 - 啟動失敗需容忍，於 /healthz 回報
            logger.exception("資料層初始化失敗")
            return False


init_services()


@app.route("/")
def index():
    return "cal_cal LINE Bot is running."


@app.route("/healthz")
def healthz():
    loader = _services.get("loader")
    if loader:
        return jsonify(status="ok", data_source=loader.source, drinks=len(loader.drinks_index))
    return jsonify(status="degraded", data_source=None), 503


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_text = build_reply(event.message.text)
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )


ICE_DISPLAY = {"H": "熱", "I": "冰"}


def build_reply(user_input: str) -> str:
    """把使用者輸入轉成回覆文字（純函式，方便離線測試）。"""
    user_input = user_input.strip()

    if user_input == "更新資料":
        loader = _services.get("loader")
        if not loader:
            return "✅ 資料已載入" if init_services() else "❌ 資料載入失敗，請檢查伺服器日誌"
        try:
            with _lock:
                loader.refresh()
            return "✅ 資料已成功更新，新的飲品資料可以查詢了"
        except Exception:  # noqa: BLE001
            logger.exception("手動更新資料失敗")
            return "❌ 資料更新失敗，暫時沿用原有資料"

    if not _services.get("loader") and not init_services():
        return "抱歉，機器人目前正在維護中，暫時無法提供服務"

    try:
        parsed = _services["parser"].parse(user_input)
        if parsed.get("error"):
            return f"❌ {parsed['error']}"

        result = _services["calculator"].calculate(parsed)
        if not result["ok"]:
            return f"❌ {result['error']}"

        header = (f"🧋 {parsed['brand']} {parsed['drink']}｜{parsed['size']}｜"
                  f"{ICE_DISPLAY.get(parsed['ice'], parsed['ice'])}｜{parsed['sweetness'] or '全糖'}")
        lines = [header]
        for name, count in parsed["toppings"]:
            lines.append(f"➕ {name}" + (f" ×{count}" if count > 1 else ""))
        for name, count in parsed["removed_toppings"]:
            lines.append(f"➖ {name}" + (f" ×{count}" if count > 1 else ""))
        lines.append(f"熱量約 {result['calories']} 大卡，糖量約 {result['sugar']} 克")
        if result["ice_fallback"]:
            lines.append("（此品項無熱飲資料，以冰飲數值估算）")
        return "\n".join(lines)
    except Exception:  # noqa: BLE001 - 任何未預期錯誤都不能讓 webhook 掛掉
        logger.exception("處理訊息「%s」時發生錯誤", user_input)
        return "抱歉，處理您的請求時發生了內部錯誤"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
