# cal_cal 手搖杯熱量機器人

LINE Bot：輸入「品牌 品名 [尺寸] [冰量] [甜度] [+/-配料]」，回覆該飲料的熱量與糖量。
資料來源為 Google Sheets（試算表 `Nutrition_Facts`），與網頁版 [boba-cal.com](https://boba-cal.com/) 共用。

使用範例：

```
50嵐 珍奶 微糖 +珍珠*2
清心 高山 熱 大
星巴克 那堤 中杯 -鮮奶油
```

隱藏指令 `更新資料`：重新從 Google Sheets 載入資料（改完試算表後不用重啟服務）。

## 架構

```
app.py                 # Flask 進入點：LINE webhook、/healthz、回覆組字
data_loader.py         # 從 Google Sheets 載入 6 張工作表，建索引；失敗時退回本地快取
input_parser.py        # 解析品牌/品名/尺寸/冰量/甜度/加減配料（支援 +配料*N）
calorie_calculator.py  # 甜度採「剩餘糖量比例」依品牌計算；配料需該品牌欄打 V
config.py              # 預設值與冰量關鍵字
tests/test_offline.py  # 離線邏輯測試（不需金鑰）：python tests/test_offline.py
scripts/manual_test.py # 用真實 Sheet 測試（需金鑰）：python scripts/manual_test.py "50嵐 珍奶"
docs/DEPLOY_OCI.md     # Oracle Cloud + Cloudflare 部署教學
```

Google Sheets 工作表：`Drinks`、`Toppings`、`Brand_sweet_setting`（甜度×品牌矩陣，
儲存格為剩餘糖量比例）、`Brands_Alias`、`Size_Alias`、`Drinks_Alias`。

計算公式（1g 糖 = 4 kcal，p 為該品牌該甜度的剩餘糖量比例）：

```
最終糖量 = 糖量 × p
最終熱量 = 熱量 − 糖量 × (1 − p) × 4 ± 配料熱量 × 份數
```

熱飲（冰量 H）查無資料時自動退回冰飲（I）數值估算。

## 本機開發

```bash
pip install -r requirements.txt
cp .env.example .env        # 填入 LINE 憑證與 Google 金鑰
python tests/test_offline.py            # 離線邏輯測試
python scripts/manual_test.py           # 用真實 Sheet 互動測試
python app.py                            # 啟動本機伺服器（port 8080）
```

## 部署（Oracle Cloud + Docker Compose + Caddy）

完整步驟見 [docs/DEPLOY_OCI.md](docs/DEPLOY_OCI.md)。摘要：

```bash
git clone https://github.com/JSCtw/cal_cal.git && cd cal_cal
cp .env.example .env                     # 填 LINE 憑證
nano service_account.json                # 貼上 GCP Service Account JSON 金鑰
docker compose up -d --build
curl http://127.0.0.1:8080/healthz       # 應回 {"status":"ok",...}
```

Webhook URL：`https://line.boba-cal.com/callback`（Caddy 自動申請與續期 TLS 憑證）。

## 環境變數

| 變數 | 說明 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 存取權杖 |
| `LINE_CHANNEL_SECRET` | LINE Bot 頻道密鑰 |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | GCP Service Account JSON 金鑰檔路徑（建議） |
| `GOOGLE_SHEETS_API_KEY` | 或：金鑰 JSON 單行字串（兩者擇一） |
| `GOOGLE_SHEET_NAME` | 試算表名稱，預設 `Nutrition_Facts` |
| `PORT` | 監聽埠，預設 8080 |

`docs/PRD.md` 與 `docs/Context.md` 為歷史文件，部分內容（FastAPI、Zeabur、舊甜度表結構）已過時，現況以本 README 與程式碼為準。
