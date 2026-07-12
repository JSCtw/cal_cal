#專案上下文：JSCtw/cal_cal 手搖杯熱量計算 LINE Bot

1. 專案概述 (Project Overview)
本專案是一個部署於 LINE 平台的聊天機器人，專門用於計算手搖飲的熱量與糖量。機器人透過解析使用者的自然語言輸入（如「品牌 品名 +配料 -配料」），標準化比對資料庫後，動態計算出對應的營養資訊並回覆使用者。

2. 系統架構與核心模組 (System Architecture)
專案採用 Python 開發（經歷從 FastAPI 到 Flask 的過渡，目前主要以 Flask 處理 LINE Webhook），包含以下核心模組：

app.py / main.py：程式進入點，負責處理 LINE Bot Webhook 請求與對接。

data_loader.py：資料載入層。啟動時從 Google Sheets 載入 6 張核心資料表（Drinks, Toppings, Size_Alias, Brands_Alias, Drinks_Alias, sweet_setting），並將別名映射（Alias Map）存入記憶體以加速查詢。

input_parser.py：自然語言解析器。將輸入字串拆解並標準化為 6 大要素：品牌 (Brand)、品名 (Drink)、尺寸 (Size, 預設 L)、冰量 (Ice, 預設 I)、甜度 (Sweetness)、以及增減配料清單。

calorie_calculator.py：計算引擎。處理基礎熱量查找、甜度乘數調整，以及配料熱量的加減。

response_builder.py：負責將計算結果組合為最終回覆給使用者的字串。

3. 核心運算邏輯 (Core Logic)
熱飲回退機制 (Fallback)：若使用者輸入熱飲（冰量 'H'）但資料庫無精確匹配，系統會自動改用同尺寸的冷飲（'I'）資料進行計算（因基礎營養素相近）。若皆無匹配則回傳「查無飲品」。

配料雙向增減 (Toppings Addition/Subtraction)：

解析 +配料：將配料熱量/糖量疊加至總數。

解析 -配料：從總數扣除特定配料（如星巴克客製化減少果露），並設有保護機制確保最終熱量與糖量不低於 0。

4. 開發歷程與架構演進 (Development History)
Phase 1 - 概念驗證與 Docker 化：使用本地 Excel/CSV 檔案作為資料庫，並包裝為 Docker Image 部署於 GCP Cloud Run。

Phase 2 - 資料庫雲端化 (2025/06/11)：為了便於非技術人員維護資料，捨棄本地 CSV，改用 gspread 套件透過 GCP Service Account 金鑰直接讀取 Google Sheets。金鑰存放於 GCP Secret Manager。

Phase 3 - 熱更新與客製化強化 (2025/10/08)：

熱更新指令：為了解決每次更新 Google Sheets 都要重啟伺服器的問題，在 app.py 實作了「更新資料」的隱藏指令，觸發 data_loader.refresh() 重新將資料載入記憶體。

負向配料：實作了前述的 -配料 扣除熱量邏輯。

Phase 4 - 平台遷移 (GCP -> Zeabur)：為降低維護成本與設定複雜度，專案從 GCP Cloud Run 遷移至 Zeabur 部署。

使用 Zeabur 提供的自動化 Git 部署。

動態讀取環境變數 PORT (os.environ.get('PORT')) 以適應 Zeabur 的無狀態容器架構。

更新 LINE Developer Console 的 Webhook URL 指向 Zeabur 生成的網域。

5. 當前環境變數需求 (Environment Variables)
新接手的開發者或 AI 需要確保環境中設定了以下變數才能正常運作：

LINE_CHANNEL_SECRET：LINE Bot 頻道密鑰。

LINE_CHANNEL_ACCESS_TOKEN：LINE Bot 存取權杖。

GOOGLE_SHEETS_API_KEY：Google Cloud 服務帳戶的 JSON 金鑰字串（用於授權存取 Google Sheets）。

PORT：（可選）由部署平台自動注入的通訊埠。