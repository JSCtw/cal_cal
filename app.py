import os
import pandas as pd
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數 (主要用於本地測試)
load_dotenv()

# --- 全域設定 ---
# Flask 應用程式初始化
app = Flask(__name__)

# Line Bot SDK 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '').strip()

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    app.logger.warning("LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 未設定，Line Bot 可能無法正常運作。")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- Excel 檔案設定 ---
EXCEL_FILE_PATH = 'data/Nutrition_Facts.xlsx'
EXCEL_SHEET_NAME = 'Drinks'

# 預期 Excel 中的欄位名稱
COL_BRAND = 'Brand_Standard_Name'
COL_DRINK_NAME = 'Standard_Drinks_Name' # 用於匹配使用者輸入
COL_SIZE = 'Size'
COL_ICE = '冰量'
COL_CALORIES = '熱量'
COL_SUGAR = '糖量'

# --- 應用程式啟動時載入 Excel 資料 ---
df_nutrition = pd.DataFrame()

try:
    if not os.path.exists('data'):
        app.logger.error(f"錯誤：找不到 'data' 資料夾。請確認 '{EXCEL_FILE_PATH}' 的路徑是否正確。")
    elif not os.path.exists(EXCEL_FILE_PATH):
        app.logger.error(f"錯誤：在 'data' 資料夾中找不到 Excel 檔案 '{os.path.basename(EXCEL_FILE_PATH)}'。")
    else:
        df_nutrition = pd.read_excel(EXCEL_FILE_PATH, sheet_name=EXCEL_SHEET_NAME)
        app.logger.info(f"成功從 '{EXCEL_FILE_PATH}' (工作表: '{EXCEL_SHEET_NAME}') 載入 {len(df_nutrition)} 筆飲料資料。")
        
        required_cols = [COL_DRINK_NAME, COL_CALORIES, COL_SUGAR]
        missing_cols = [col for col in required_cols if col not in df_nutrition.columns]
        if missing_cols:
            app.logger.error(f"Excel 檔案 (工作表: '{EXCEL_SHEET_NAME}') 中缺少必要的欄位：{', '.join(missing_cols)}。機器人可能無法正確查詢。")
            df_nutrition = pd.DataFrame()
except Exception as e:
    app.logger.error(f"讀取 Excel 檔案 '{EXCEL_FILE_PATH}' (工作表: '{EXCEL_SHEET_NAME}') 時發生錯誤: {e}")

# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        abort(500)
    return 'OK'

# --- 訊息事件處理 (已修改為除錯增強版) ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_message_original = event.message.text.strip()
        user_message_search = user_message_original.lower()

        reply_text = f"您好，我目前找不到關於「{user_message_original}」的營養資訊。\n請試試看輸入常見的飲料名稱。"

        if df_nutrition.empty:
            app.logger.warning("營養資料 (DataFrame) 為空，無法進行查詢。")
            reply_text = "抱歉，營養資料庫目前似乎無法使用，請稍後再試。"
        else:
            try:
                matched_item = None
                
                # --- 開始除錯日誌 ---
                app.logger.info("="*20)
                app.logger.info(f"開始搜尋，使用者輸入 (已轉小寫): '{user_message_search}'")
                app.logger.info(f"總共比對 {len(df_nutrition)} 筆資料。")
                # --- 除錯日誌結束 ---

                for index, row in df_nutrition.iterrows():
                    # *** 關鍵修改 1：從 Excel 取出資料時，也使用 .strip() 去除前後空格 ***
                    drink_name_from_excel = str(row[COL_DRINK_NAME]).strip().lower()
                    
                    # --- 除錯日誌：印出正在比對的內容 (只印前5筆，避免日誌過多) ---
                    if index < 5:
                        app.logger.info(f"正在比對 第 {index} 筆: '{drink_name_from_excel}'")
                    
                    # *** 關鍵修改 2：修正搜尋邏輯 ***
                    if drink_name_from_excel and (drink_name_from_excel in user_message_search):
                        # --- 成功日誌 ---
                        app.logger.info(f"比對成功！使用者輸入 '{user_message_search}' 中包含 Excel 項目 '{drink_name_from_excel}'")
                        matched_item = row
                        break

                if matched_item is not None:
                    brand_reply = matched_item.get(COL_BRAND, "N/A")
                    drink_name_reply = matched_item.get(COL_DRINK_NAME, "N/A")
                    size_reply = matched_item.get(COL_SIZE, "N/A")
                    ice_reply = matched_item.get(COL_ICE, "N/A")
                    calories_reply = matched_item.get(COL_CALORIES, "N/A")
                    sugar_reply = matched_item.get(COL_SUGAR, "N/A")
                    reply_text = (
                        f"找到「{drink_name_reply}」的資訊：\n"
                        f"品牌：{brand_reply}\n"
                        f"品名：{drink_name_reply}\n"
                        f"份量：{size_reply}\n"
                        f"冰量：{ice_reply}\n"
                        f"熱量：約 {calories_reply} 大卡\n"
                        f"糖量：約 {sugar_reply} 克"
                    )
                else:
                    # --- 失敗日誌 ---
                    app.logger.warning(f"搜尋結束，找不到符合 '{user_message_search}' 的項目。")
                    app.logger.warning("="*20)

            except Exception as e:
                app.logger.error(f"處理訊息時發生未預期錯誤: {e}")
                reply_text = "處理您的請求時發生內部錯誤，請稍後再試。"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# --- 啟動伺服器 ---
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)