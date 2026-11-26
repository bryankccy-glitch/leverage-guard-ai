# AI_HANDOFF — LeverageGuard AI

> 夜間開發交接檔。每完成一段就更新。使用者 2026-11-26 凌晨交代：不要問問題、持續做、早上再報告；版面參考深色儀表板截圖（左側欄＋KPI 卡＋兩欄主內容），深淺模式與中英文都要。

## 已確認的事實（有證據）

- 官方法規來源已下載並解析：`data/legal/documents.json`（8 份：證券交易法、證券交易稅條例、金融消費者保護法、融資融券管理辦法、證券金融事業管理規則、有價證券得為融資融券標準、證交所融資融券業務操作辦法 115.10.16、當日沖銷交易作業辦法 105.02.01）。腳本：`scripts/extract_legal_sources.py`。
- 證交所休市日只公布最新年度（目前是 2027）；2026 年剩餘日期只排除週末，結果會標示 `weekends_only`。
- 維持率門檻 130%、取消 166%、補繳期限 2 營業日、處分、溢額、剩餘債務、違約申報、違約金：都有證交所操作辦法第 53–55、81、82 條原文。
- 當沖稅率 1.5‰ 至 2027-12-31（證交稅條例 2-2），之後回到 3‰（第 2 條）。
- T+2 交割與「資金不足→違約交割」：**尚未匯入營業細則原文**，規則標為 is_demo、sources 空、時間軸標示 Insufficient Legal Evidence。
- Codex 額度用完，下午 2:20 恢復（實測錯誤訊息）。今晚全部由 Claude 實作。
- 沒有 Gemini 金鑰；使用者指定改用千問（本機 Ollama `qwen3:8b`）。

## 決策

| 決策 | 理由 |
|---|---|
| LLM 預設 Ollama qwen3:8b，Gemini 保留為可切換 Provider | 使用者沒有 Gemini 金鑰，指定千問 |
| 規則全部 `pending_review`，模擬可用但標示「尚未經人工審查」；後台核准後變 active | 需求要求人工審查；不能假裝已審查 |
| 規則引用載入時逐字比對官方條文，比對失敗不能執行 | 防止虛構法條 |
| 先不 git commit | multi-agent 規則：commit 需使用者同意 |

## 完成進度（2026-11-26 05:00）

全部 P0 已實作並驗證；P1 基本版完成；P2 頁面標示尚未開放。詳細驗收對照：`docs/IMPLEMENTATION_PLAN.md`。

| 檢查 | 結果 |
|---|---|
| 後端 pytest | 46 passed |
| 後端 Ruff | All checks passed |
| 評估集 `scripts/run_evaluation.py` | 金融 27/27、法律事件 15/15、引用 30/30、版本 4/4、建議偵測 12/12、輸出審查 6/6 |
| 前端 tsc／ESLint | 0 錯誤 |
| 前端 `next build` | 成功（52 路由） |
| Playwright E2E 核心 9 項 | 9 passed |
| 頁面巡檢（3 身分 × 深淺色 × 中英） | 52 頁皆 200；唯一錯誤是 RLS 正確擋下他人契約（預期 404） |

## 執行中的服務（本機）

- DB：docker compose（port 54330），重建：`./scripts/db_reset_local.sh && cd apps/api && .venv/bin/python -m app.services.seed`
- API：`cd apps/api && .venv/bin/uvicorn app.main:app --port 8810`（8000 被別的程式佔用）
- Web：`cd apps/web && npx next dev -p 3000`
- 截圖：`cd apps/web && node tests/shoot.mjs /dashboard out.png investor light 1440 1200`；全站巡檢：`node tests/sweep.mjs investor light zh`

## 需要使用者決定（早上）

1. 是否 `git commit`（目前完全沒有 commit）。
2. 是否部署（需要 Supabase 專案、Vercel、後端主機）。
3. 是否下載 qwen2.5vl（圖片契約 OCR）。
4. 規則審查：目前全部 pending_review，需要具法律背景的人核准。
5. Codex 下午 2:20 恢復後要不要派它做：Supabase Auth 前端、更多 E2E、營業細則匯入。

## 怎麼跑測試

```
cd apps/api && .venv/bin/python -m pytest -q
```

## 續工紀錄（2026-11-26 清晨）

- 報告 E2E 第一次失敗的真正原因：`POST /reports` 用使用者身分寫入通知，被 notifications 的 RLS 擋下（500）。已改為 service_session 寫入系統通知。
- 新增整合測試 `test_report_from_completed_run`（不依賴 LLM：產生報告、PDF/JSON/CSV 匯出、他人讀不到、通知寫入）。
- 第二次失敗是測試等待「工作流程完成」事件，但相同輸入命中快取時不會重播事件；改為等待結果區塊的「數字未被 AI 修改」徽章。
- 結果：後端 pytest 47 passed、Ruff 通過；Playwright 10/10 passed。
- 觀察：較早一次未命中快取的千問分析花了約 20 分鐘（19:09→19:29，多次逾時後改用模板）。本機 16GB 同時跑 qwen3:8b、嵌入模型、Docker 與 Next 時很慢；展示前建議先暖機模型，或把 `LLM_TIMEOUT_SECONDS` 調低到 90 讓模板更快接手。

## 英文化（2026-11-26，Claude；Codex 額度用完改由 Claude 實作）

分支 `codex/full-english`（worktree `.tmp/codex-en`），尚未 commit。

做法：
- 前端：寫死中文改成 `L("中文", "English")`（`lib/i18n.tsx` 的 `useL`／`useIsEn`，語系一律從 next-intl `useLocale()` 讀，避免 Suspense hydration 不一致）；靜態頁用 `<Bi zh en>`；`PageTitle` 支援 `subtitleEn` 並更新分頁標題；`api.ts` 一律帶 `Accept-Language`。
- 後端：`app/i18n.py` ＋ middleware，`Accept-Language: en` 時在回應送出前翻譯 JSON（完全相同字串＋含數字的樣板）；計算／規則／時間軸引擎完全沒改。`quote`、`content`、`original_text` 等原文欄位不翻。SSE 與報告匯出（JSON/CSV/PDF）另外處理。
- 規則英文名稱與白話說明：`data/i18n/rules_en.json`（非官方翻譯）。
- AI：英文模式用英文 system prompt／prompt，快取鍵含語系；`guards.py` 補英文的投資建議／誤解偵測（否則英文輸出會繞過審查閘門）。
- 官方法條、法條章節、修正對照、契約原文刻意保留中文並標 `lang="zh-Hant-TW"`，英文版加註「Original text (Traditional Chinese)」。

驗收：
- 後端 pytest 65 passed（原 47＋新 `tests/test_i18n.py` 18）、Ruff PASS。
- 前端 tsc PASS（`LayoutProps` 錯誤是 worktree 未產生型別，build 後消失）、ESLint 0 警告、`next build` PASS。
- 瀏覽器巡檢（worktree 服務 3001/8811）：英文 reviewer 51 頁、英文 investor 51 頁、中文 investor 51 頁，皆 0 錯誤、英文版無可見中文。

已知限制：
- 英文模式的 Copilot／法規搜尋仍以中文關鍵字檢索法條，用英文提問的檢索效果較差。
- 新增中文字串時要同步補 `app/i18n.py`；`test_i18n.py` 會抓出漏翻。
- 法規英文名稱：前三部依全國法規資料庫英文名稱（未連網再次核對），其餘為本平台翻譯。

## 部署紀錄（2026-11-26 下午，使用者同意部署）

- 內容：main `12a19f3`（英文化＋評審回饋 6 項：申訴頁、拒答示範與客觀風險資訊、版面收合、移除非融資入口、法規最新修正日期、訪客 Copilot）。
- Vercel 帳號 1（bryankccy-2499）。CLI 登入存在獨立設定 `~/.vercel-leverageguard`（指令要寫成 `vercel --global-config ~/.vercel-leverageguard <子指令>`），不影響 ImportGuard 用的帳號 3 登入。
- 後端 leverage-guard-api → `leverage-guard-asi5pr8xp`（上一版 `leverage-guard-qe9lv9udt`）；部署包由 `deploy/build_api.sh` 產生，執行後要把 `.tmp/deploy-api/.vercel` 放回。
- 前端 leverage-guard-ai → `leverage-guard-8402eatkp`（上一版 `leverage-guard-9ik2yxh9f`）。
- 部署後檢查：health 200、未登入 /simulations 401、英文標籤與規則名稱為英文且數字與中文版相同、訪客拒答附 4 條風險資訊；瀏覽器（訪客）中英文融資頁與申訴頁：無可見中文殘留、選單無當沖／分身／Agent、拒答示範正常、無頁面錯誤。
- 回復：在 Vercel 後台把兩個專案的上一版 Promote 回 Production。
- 本機注意：localhost 8810 後端是合併前啟動的舊程序（沒有 --reload），需手動重啟才會載入新版。

## 帳號密碼登入（2026-11-26 下午，Claude；尚未 commit、尚未部署）

目的：正式站原本是 AUTH_MODE=local（任何人可一鍵登入示範管理員）。改成跟 ImportGuard 一樣用「帳號＋密碼」：帳號 `bryan` 對應 Supabase Auth 的 `bryan@leverageguard.local`。

- 後端：`security/auth.py` 支援新版 Supabase ES256（JWKS 公鑰驗證，`_jwks_client` 快取）；HS256 只在有 `SUPABASE_JWT_SECRET` 時接受。`/auth/config` 在 supabase 模式回傳 `supabase_anon_key`、`login_domain`。`pyjwt[crypto]`（requirements.txt 與 deploy/requirements.prod.txt）。
- 前端：`lib/supabase.ts`（設定只抓一次、client 單例、憑證自動續期並同步到 useAuth、登出一起清 Supabase）；`api.ts` 呼叫前取最新憑證；登入頁 supabase 模式為帳號密碼表單；註冊頁顯示「不開放自行註冊」。
- 建帳號：`python3 scripts/create_user.py`，service_role key 與密碼都由使用者執行時自己輸入（AI 不經手密碼）。第一次登入自動建 profile，角色 investor。
- 驗證：後端 pytest 71 passed（新增 tests/test_supabase_auth.py 5 項）、Ruff PASS；前端 tsc、ESLint PASS、next build PASS；本機 supabase 模式：登入頁只剩帳號密碼、示範登入 404、未登入 /admin/users 401、假憑證 401、訪客 Copilot 拒答＋風險資訊正常。
- NOT RUN：實際用 Supabase 帳號登入（需要使用者先建帳號）。
- 上線要設的環境變數（API 專案）：AUTH_MODE=supabase、SUPABASE_URL、SUPABASE_ANON_KEY；然後重新部署 API 與前端。切換後示範帳號（含示範管理員）全部失效，管理員帳號需另外把 profiles.role 改成 system_admin。

### 部署紀錄（2026-11-26，使用者同意 commit 與部署）
- commit `3182cea`。API 環境變數新增 SUPABASE_URL、SUPABASE_ANON_KEY（publishable key），AUTH_MODE 由 local 改為 supabase（用 `vercel env update`；`env rm` 會被 CLI 要求人工核准）。
- 後端 leverage-guard-api → `leverage-guard-2kumyeipg`（上一版 `leverage-guard-asi5pr8xp`）；前端 leverage-guard-ai → `leverage-guard-1t6my0t92`（上一版 `leverage-guard-8402eatkp`）。
- 部署後檢查 PASS：/auth/config mode=supabase、示範帳號清單空；示範登入 404；未登入 /admin/users 401；假憑證 401；訪客 Copilot 拒答＋風險資訊；正式站登入頁只有帳號密碼、無頁面錯誤。
- NOT RUN：真的帳號登入（密碼只有使用者知道）。
- 待辦：Supabase Auth「Allow new users to sign up」仍開啟（建議關閉）；管理員帳號建立後要把 profiles.role 改為 system_admin（使用者先登入一次讓 profile 建立）。
- 回復：Vercel 兩個專案 Promote 上一版；或把 AUTH_MODE 改回 local 後重新部署 API。
