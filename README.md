# LeverageGuard AI

**AI 金融交易風險與法律責任情境模擬平台**｜AI-Powered Financial Risk & Legal Intelligence Platform
Know the Risk. Understand Your Rights.｜看見風險，理解責任，掌握權益。

在承擔融資或當沖風險之前，先看懂可能的財務損失、追繳與處分流程、剩餘債務、交割責任與投資人權益。

> 本平台不提供投資建議、不推薦股票、不預測股價，也不是律師的正式法律意見。所有帳戶與價格都是模擬資料。

**🔗 線上展示：<https://leverage-guard-ai.vercel.app>**｜API 文件：<https://leverage-guard-api.vercel.app/api/v1/docs>

## 為什麼做這個

很多投資人開了融資、當沖帳戶，卻不知道「維持率跌破 130% 之後會發生什麼」：哪天要補繳、補多少、沒補會被怎麼處分、處分完還欠多少。這些答案散落在證交所規章與法規條文裡，一般人很難看懂。

LeverageGuard AI 把**金融計算、法規條文與 AI 說明**串在一起：輸入持股與價格變化，就能看到損失數字、法律時間軸和白話解釋，而且每一個數字都能展開公式、每一句說明都附官方條文出處。

## 專案亮點

| 亮點 | 說明 |
|---|---|
| 計算不交給 AI | 所有金額由後端 Decimal 計算引擎產生，AI 只負責白話說明，避免 LLM 算錯錢 |
| Regulation-as-Code | 把法規寫成有版本、生效日期、可比對原文的規則，法規修正時舊情境仍能重算 |
| 有出處的 RAG | 法律檢索結合關鍵字＋語意搜尋，回答引用必須真實存在於官方條文 |
| 可稽核的多 Agent | 11 個 Agent 分工，每一步都留紀錄並即時顯示，看得到 AI 怎麼得出結論 |
| 安全與權限 | Supabase Auth、資料列層級權限（RLS）、拒絕投資建議的護欄 |
| 測試 | 後端 pytest（金融 golden test、RLS 權限測試）與 Playwright E2E |

**技術棧**：Next.js · React · TypeScript · Tailwind CSS · FastAPI · SQLAlchemy · PostgreSQL + pgvector · Supabase · Ollama（Qwen3）· Vercel

## 功能

- **融資風險模擬器**：滑桿即時預覽（Decimal.js），後端 Decimal 正式計算；擔保維持率、追繳門檻股價、第 54 條補繳差額、交易成本、本金損益率；每個數字可展開公式。
- **當沖風險模擬器**：完成／部分沖銷、買進未賣出、先賣後買未買回、資金缺口；稅率依成交日期由規則引擎決定。
- **極端情境實驗室**：12 個預設情境、情境編輯器、播放／暫停／逐步、情境比較、規則版本比較。
- **法律責任時間軸**：依證交所休市日與通知送達日推算期限；每個事件附官方條文、權利義務、應保存資料與不確定性。
- **Regulation-as-Code**：27 個規則版本，引用逐字比對官方條文；版本、生效期間、衝突偵測、人工審查。
- **法律知識中心**：8 份官方法規（全國法規資料庫、證交所），關鍵字＋語意（qwen3-embedding）混合檢索。
- **契約分析**：上傳 PDF／文字，條款切分、分類、頁碼、參數擷取；AI 白話說明的引用必須存在於文件。
- **AI Agents**：11 個 Agent（Orchestrator、計算、規則、檢索、契約、驗證、白話、審查、報告…），每一步寫入可稽核紀錄並以 SSE 即時顯示。
- **Legal Copilot**：理解目前模擬參數，「再跌 10%」由計算引擎重算；拒絕買賣建議。
- **個人風險報告**：投資人版／專業版，PDF（嵌入繁中字型）、JSON、CSV。
- **其他**：數位分身、法規變動監察、通知、管理後台、深淺色、繁中／英文。

## 快速啟動（本機）

需求：Docker（或 OrbStack）、Python 3.12+、Node 20+、Ollama（可選，用於千問）。

```bash
# 1. 環境變數
cp .env.example .env                      # 請把 JWT_SECRET 改成隨機長字串

# 2. 資料庫（本機 Postgres + pgvector，port 54330）
./scripts/db_reset_local.sh

# 3. 後端
cd apps/api
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m app.services.seed      # 匯入法規、規則、示範帳號與示範資料
.venv/bin/uvicorn app.main:app --port 8810  # API 文件：http://127.0.0.1:8810/api/v1/docs

# 4. AI（可選）
ollama pull qwen3:8b && ollama pull qwen3-embedding:0.6b
.venv/bin/python -c "from app.legal_rag.search import embed_all_chunks; print(embed_all_chunks())"

# 5. 前端
cd ../web
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8810" > .env.local
npm install && npx next dev -p 3000         # http://localhost:3000
```

示範帳號（本機模式，登入頁直接點選）：投資人、投資人二、法律審查員、系統管理員。

沒有 Ollama 時，系統會自動改用規則模板說明並清楚標示「未使用生成式 AI」，其他功能不受影響。

## 測試與評估

```bash
cd apps/api && .venv/bin/python -m pytest -q                 # 46 個：金融 golden／性質測試、規則、情境、RLS 與權限整合測試
.venv/bin/python ../../scripts/run_evaluation.py              # 評估集（結果寫入 data/evaluation/latest_results.json）
cd ../web && npx tsc --noEmit && npx eslint . && npx playwright test   # 型別、Lint、E2E
```

## 更新官方法規資料

```bash
python3 scripts/extract_legal_sources.py .tmp/legal_raw_new   # 下載並解析
cd apps/api && .venv/bin/python -m app.services.seed           # 新版本寫入資料庫（舊版本保留）
```

或設定 `LEGAL_SOURCE_SYNC_ENABLED=true`，由管理員在 `/admin/legal-sources` 比對版本，系統只建立待審查的更新。

## 部署

目前正式環境：前端與 API 都部署在 Vercel，資料庫使用 Supabase（見上方線上展示連結）。雲端版沒有本機 Ollama，AI 說明會改用規則模板並清楚標示。

| 元件 | 平台 | 設定 |
|---|---|---|
| 前端 | Vercel | `NEXT_PUBLIC_API_URL`、（使用 Supabase Auth 時）`NEXT_PUBLIC_SUPABASE_URL`、`NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| 後端 | Cloud Run／Railway／Render | `DATABASE_URL`、`AUTH_MODE=supabase`、`SUPABASE_JWT_SECRET`、`ALLOWED_ORIGINS`、`LLM_PROVIDER`（雲端環境沒有本機 Ollama 時用 `gemini` 或自架 Ollama） |
| 資料庫 | Supabase | 依序執行 `supabase/migrations/*.sql`（**不要**執行 `supabase/local/`） |

正式部署前請先完成：Supabase Auth 前端登入元件、前端 CSP、Redis 版限流、法律專業審查規則。詳見 `docs/SECURITY.md`。

## 文件

`docs/`：PRODUCT_REQUIREMENTS、ARCHITECTURE、DESIGN_SYSTEM、FINANCIAL_FORMULAS、LEGAL_SOURCE_REGISTRY、REGULATION_AS_CODE、DATABASE_SCHEMA、AGENT_WORKFLOW、API_SPECIFICATION、SECURITY、EVALUATION_PLAN、IMPLEMENTATION_PLAN。

## 資料來源與授權

法規條文來自全國法規資料庫開放資料與臺灣證券交易所法規分享知識庫（公開網頁），保留官方網址、版本與取得時間；正式商用前請確認各網站使用條款。PDF 字型 Droid Sans Fallback 為 Apache License 2.0。
