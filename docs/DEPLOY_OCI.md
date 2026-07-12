# 部署教學：Oracle Cloud + Cloudflare + Docker Compose

本文件帶你把 cal_cal LINE Bot 部署到 Oracle Cloud（OCI）free tier 主機，
並透過 Cloudflare 的子網域 `line.boba-cal.com` 取得 HTTPS（LINE webhook 強制要求）。

架構：

```
LINE 平台 ──HTTPS──> line.boba-cal.com（DNS 指向 OCI 主機 IP）
                        │
                  [OCI 主機]
                  Caddy 容器（80/443，自動申請 Let's Encrypt 憑證）
                        │ reverse_proxy
                  bot 容器（gunicorn + Flask，port 8080）
                        │
                  Google Sheets（Nutrition_Facts）
```

---

## 事前準備清單

- [ ] OCI 主機的**公有 IP**（OCI 主控台 → Compute → Instances 可查）
- [ ] 能 SSH 登入主機（`ssh ubuntu@<公有IP>` 或 `opc@<公有IP>`，看你建機時的映像檔）
- [ ] Cloudflare 帳號可管理 `boba-cal.com` 這個網域
- [ ] LINE 憑證：`LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`
      （LINE Developers Console → 你的 Channel → Messaging API / Basic settings；
      若 Zeabur 面板還進得去，可直接抄之前設定的值）
- [ ] GCP Service Account 的 **JSON 金鑰**（之前設定在 Zeabur 的 `GOOGLE_SHEETS_API_KEY` 內容）

---

## 第 1 步：Cloudflare 新增子網域

1. 登入 [dash.cloudflare.com](https://dash.cloudflare.com/)，點選網域 **boba-cal.com**。
2. 左側選單點 **DNS** → **Records**。
3. 點 **Add record**，填入：
   - **Type**：`A`
   - **Name**：`line`（Cloudflare 會自動補成 line.boba-cal.com）
   - **IPv4 address**：你的 OCI 主機公有 IP
   - **Proxy status**：點一下橘色雲朵改成**灰色**（顯示 "DNS only"）⚠️ 重要
   - **TTL**：Auto
4. 點 **Save**。

> ⚠️ **為什麼一定要灰雲（DNS only）？**
> 主機上的 Caddy 要直接對外服務，才能通過 Let's Encrypt 的驗證自動拿到憑證。
> 橘雲（Proxied）會讓流量先過 Cloudflare，憑證申請會失敗，還會造成雙層代理問題。

驗證 DNS 已生效（在你自己的電腦執行，通常幾分鐘內生效）：

```bash
nslookup line.boba-cal.com
# 回應的 IP 應該是你的 OCI 主機公有 IP
```

---

## 第 2 步：OCI 開放 80 / 443 連接埠

OCI 有**兩層**防火牆，兩層都要開，只開一層是最常見的卡關原因。

### 2a. VCN Security List（雲端層）

1. OCI 主控台 → 左上漢堡選單 → **Networking** → **Virtual Cloud Networks**。
2. 點你的 VCN → 左側 **Security Lists** → 點預設的 Security List（通常叫 `Default Security List for ...`）。
3. 點 **Add Ingress Rules**，新增兩條規則：

   | 欄位 | 規則 1（HTTP） | 規則 2（HTTPS） |
   |---|---|---|
   | Source Type | CIDR | CIDR |
   | Source CIDR | `0.0.0.0/0` | `0.0.0.0/0` |
   | IP Protocol | TCP | TCP |
   | Destination Port Range | `80` | `443` |

4. 點 **Add Ingress Rules** 儲存。

### 2b. 主機內部防火牆（作業系統層）

SSH 進主機後，依你的作業系統執行：

**Ubuntu**（預設帳號 `ubuntu`）：

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
# 讓規則重開機後仍生效
sudo apt-get update && sudo apt-get install -y netfilter-persistent iptables-persistent
sudo netfilter-persistent save
```

**Oracle Linux**（預設帳號 `opc`）：

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 第 3 步：安裝 Docker

SSH 進主機執行（Ubuntu / Oracle Linux 皆適用）：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 讓群組設定生效：登出再重新 SSH 進來，或執行
newgrp docker
# 驗證
docker --version && docker compose version
# 確保重開機後 Docker 自動啟動
sudo systemctl enable docker
```

---

## 第 4 步：部署專案

```bash
git clone https://github.com/JSCtw/cal_cal.git
cd cal_cal
```

### 4a. 建立 `.env`（LINE 憑證）

```bash
cp .env.example .env
nano .env
```

填入兩行（等號後直接貼值，不要加引號）：

```
LINE_CHANNEL_ACCESS_TOKEN=你的token
LINE_CHANNEL_SECRET=你的secret
```

### 4b. 建立 `service_account.json`（Google 金鑰）

```bash
nano service_account.json
```

把整份 GCP Service Account JSON 金鑰貼進去（就是以前塞在 Zeabur
`GOOGLE_SHEETS_API_KEY` 的那串，`{"type": "service_account", ...}` 開頭），存檔。

> 這個檔案已列入 `.gitignore` 與 `.dockerignore`，不會被 commit 或打包進映像檔，
> 容器是用唯讀掛載的方式讀取它。

### 4c. 啟動

```bash
docker compose up -d --build
```

第一次會建置映像檔，約 1–3 分鐘。完成後檢查：

```bash
docker compose ps                        # 兩個服務都應該是 running
curl http://127.0.0.1:8080/healthz      # 應回 {"data_source":"sheets","drinks":NNN,"status":"ok"}
docker compose logs bot | tail -20      # 應看到「資料層初始化完成（來源：sheets）」
```

如果 `healthz` 回 `degraded`，看 `docker compose logs bot` 的錯誤訊息，
最常見是金鑰 JSON 貼錯（少了開頭/結尾大括號）或該 Service Account 沒有試算表的讀取權限。

### 4d. 確認 HTTPS 憑證

```bash
docker compose logs caddy | grep -i cert
# 在你自己的電腦瀏覽器開 https://line.boba-cal.com/healthz，應顯示 JSON 且憑證有效
```

憑證申請失敗的三大原因：DNS 還沒生效、Cloudflare 是橘雲、80/443 沒開通（回到第 1、2 步檢查）。

---

## 第 5 步：切換 LINE Webhook

1. 到 [LINE Developers Console](https://developers.line.biz/console/) → 你的 Channel → **Messaging API** 分頁。
2. **Webhook URL** 改為：`https://line.boba-cal.com/callback`
3. 點 **Verify**，應顯示 Success。
4. 確認 **Use webhook** 開關是開啟的。
5. 用手機傳訊息實測，例如 `50嵐 珍奶 微糖 +珍珠`。

到這裡就完成了。Zeabur 那邊不用動，webhook 已指向新主機。

---

## 日常維運

| 操作 | 指令 / 方式 |
|---|---|
| 看即時日誌 | `docker compose logs -f bot` |
| 改了 Google Sheets 資料 | 在 LINE 對機器人傳 `更新資料`（不用重啟） |
| 更新程式碼 | `git pull && docker compose up -d --build` |
| 重啟服務 | `docker compose restart` |
| 停止服務 | `docker compose down` |
| 檢查健康狀態 | `curl https://line.boba-cal.com/healthz` |

- 主機重開機後 Docker 與兩個容器會自動啟動（`restart: unless-stopped`）。
- Caddy 憑證會自動續期，不需人工處理。
- Google Sheets 暫時故障時，bot 啟動會自動改用上次成功載入的本地快取（`healthz` 的
  `data_source` 會顯示 `cache`），恢復後傳 `更新資料` 即可切回。

## 疑難排解

| 症狀 | 檢查 |
|---|---|
| Verify 失敗 / 機器人不回 | `curl https://line.boba-cal.com/healthz` 通不通 → 不通查 DNS/防火牆；通則看 `docker compose logs bot` |
| 回「機器人目前正在維護中」 | 資料層初始化失敗，看 bot 日誌，多半是金鑰或試算表權限問題 |
| 回覆亂算 / 查無資料 | 先傳 `更新資料`；再用 `python scripts/manual_test.py "輸入內容"` 在本機重現 |
| 憑證錯誤 | `docker compose logs caddy`，確認灰雲與 80/443 |
