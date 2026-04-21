# LINE Group Scheduler Bot

定時將預設訊息推送到 LINE 群組，支援多訊息依序/隨機輪替。

## 功能
- Web UI 管理排程（cron）、訊息、群組
- 自動從 webhook 蒐集 Bot 加入的群組 ID
- 發送紀錄（成功/失敗）
- Docker 化部署，SQLite 持久化

## 技術棧
FastAPI · APScheduler · SQLModel · Jinja2 · line-bot-sdk v3

## 快速開始

### 1. 建立 LINE Channel
到 [LINE Developers Console](https://developers.line.biz/) 建立 Messaging API Channel，取得：
- Channel access token (long-lived)
- Channel secret

### 2. 啟動
```bash
docker compose up -d --build
```

### 3. 於 Web UI 填入 API Key
訪問 <http://localhost:8000/settings>，貼上 Channel access token 與 Channel secret 後儲存即可（不需手動編輯 `.env`）。設定會存在 SQLite，重啟容器後仍保留。之後訪問 <http://localhost:8000/schedules> 開始建立排程。

### 4. 設定 webhook
- 公開一個 HTTPS URL（ngrok 或反向代理）指向 `http://<host>:8000/webhook`
- 到 LINE Console 填入該 URL，並啟用 Use webhook
- 把 Bot 加入群組，並在群組發一則訊息 → 群組會出現在 `/groups`

### 5. 建立排程
到 `/schedules` 建立，cron 範例：
| 需求 | Cron |
|---|---|
| 每週二 12:00 | `0 12 * * 2` |
| 每週三 18:00 | `0 18 * * 3` |
| 每天 09:30 | `30 9 * * *` |

接著到該排程的「訊息」頁面新增多則訊息，系統會依 sequential / random 模式輪替。

## 本機開發（不用 Docker）
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# 首次啟動後到 http://localhost:8000/settings 填入 token/secret
```

## 注意
- LINE Push Message 有每月額度限制，請留意。
- Webhook 必須 HTTPS。
- 容器時區預設 `Asia/Taipei`，如需更改請調整 `.env` 與 `docker-compose.yml` 中的 `TZ`。
- Web UI 目前無登入驗證，請以反向代理（Caddy / Nginx basic auth）保護。
