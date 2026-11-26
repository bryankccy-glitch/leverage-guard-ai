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

## 帳號資料隔離＋版面精簡（2026-11-26 晚，Claude；尚未 commit、尚未部署）

**資料隔離**（使用者要求：帳號登入後不出現模擬／示範資料，只看到自己的紀錄）
- 個人資料表原本就由 RLS 隔離（user_id = auth.uid()），新帳號不會被自動建立示範資料。
- 新增 `Settings.hide_demo_content`（auth_mode=supabase 時為真）：儀表板與 `/regulatory/updates` 排除 is_demo 的全站示範法規更新（詳情 404；管理員審查頁仍可見）；`POST /contracts/demo` 回 404；前端契約頁隱藏示範契約區塊。
- 測試 `tests/test_demo_isolation.py`（4 項）：新帳號儀表板全為 0、無示範內容；示範模式仍顯示示範更新。

**版面 A–E**（使用者選全部）
- A：規則版本只給審查員／管理員（頂部列）；儀表板移除更新時間與規則版本按鈕；融資頁技術徽章（Decimal.js、fin-engine、規則版本）移到展開的「計算假設」。
- B：左側選單 5 組 14 項 → 2 組 9 項（模擬、法律知識；管理員多一組）；報告、紀錄、通知、設定移到帳號選單；未讀數字改在鈴鐺；API 狀態只在斷線時顯示。
- C：儀表板風險事件同情境同狀態合併（×n）；「模擬資料」改為一行說明；沒有模擬帳戶時不顯示該列；移除英文殘留「total」。
- D：Field/NumberField 新增 `tip`（說明收成 ⓘ、sr-only 保留）；融資頁換算說明與紅漲綠跌改用 ⓘ。
- E：頁面間距加大（space-y-6、gap-5/6、main px-4）。
- E2E：core.spec 融資測試配合收合調整（先展開計算結果；後端正式計算改在計算假設內檢查）。該測試自 12a19f3 起即會失敗（計算結果預設收合），本次一併修正。
- 驗證：pytest 75 passed、Ruff PASS、tsc PASS、ESLint PASS、Playwright 10/10 passed、next build PASS（暫存複本）。

### 部署紀錄（2026-11-26 晚，使用者同意 commit 與部署）
- commit `2a5a6c9`。後端 → `leverage-guard-3q8xeauok`（上一版 `leverage-guard-2kumyeipg`）；前端 → `leverage-guard-5zqa3zh6q`（上一版 `leverage-guard-1t6my0t92`）。
- 部署後檢查 PASS：/regulatory/updates 無示範項目；示範登入 404；未登入後台 401；未登入建示範契約 401；訪客 Copilot 拒答；正式站融資頁、法規變動監察、契約頁無【示範】、無 Decimal.js、頂部列無規則版本，選單 9 項，無頁面錯誤。
- NOT RUN：帳號登入後的儀表板（密碼只有使用者知道）。

## 當沖法源補完與入口恢復（2026-11-26，Codex；未 commit、未部署）

- 使用既有 `.tmp/legal_raw` 執行擷取腳本，未重新下載任何檔案；新增 `twse:FL007304`「臺灣證券交易所股份有限公司營業細則」（115.11.18、270 條），目前共 9 份。原有 8 份的條文與內容雜湊逐一比較完全一致，僅取得時間等中繼資料更新；休市日檔也僅更新取得時間。
- `DT-SETTLEMENT-CYCLE`、`DT-FUNDING-GAP` 新增 1.0.0，引用第 57、91（第 1、3 項）、82 條，逐字驗證通過，`is_demo=false`、`pending_review`。0.1.0 示範版本保留並標為 `superseded`；原版翻譯也保留供歷史版本顯示。
- 現有選擇器同優先序且參數相同時取第一筆，不會自動選較新版本，因此明確停用舊示範版本。匯入程式同步停用資料庫中對應的待審查／草稿舊版，避免資料庫狀態覆蓋檔案；已核准／啟用狀態不會被匯入程式擅自改寫。
- 時間軸沿用既有引用組裝方式，無須修改 `builder.py`。資金缺口時新增「未如期交割：違約申報」與「違約承受款券處理期限」兩個條件式事件；次一營業日使用既有日曆工具計算。只標可能風險，不將預估缺口當成已違約；附第 91 條抵繳、大量違約證券及不可歸責事由的例外提醒。不計算或臆測違約金，未改動任何金額計算邏輯。
- 恢復側欄模擬群組及模擬首頁的當沖入口（融資之後），未恢復數位分身或 AI Agents 入口。同步更新規則英文、事件英文、法規名稱英文、README 與兩份法規文件。
- 評估集 `dataset.json` 無依賴舊示範狀態的題目，未修改；重跑結果已寫入 `latest_results.json`。Claude 接手審查後修正 `scripts/run_evaluation.py`：已 `superseded` 的版本不再列入「缺官方出處」，重跑後清單為空；預設選用的 1.0.0 均有法源。
- Claude 審查與重驗（2026-11-26 晚）：審閱 seed／時間軸／前端 diff；規則檔無 active／approved 狀態，人工審查未被繞過。親自重跑 pytest 79 passed、Ruff PASS、評估引用 34/34、tsc／ESLint／next build PASS；直接執行資金不足情境，時間軸 12/3 交割（第57條）、12/3 違約申報（第82、91條）、12/4 處理期限（第91條），無 Insufficient Legal Evidence。

| 驗收 | 實際結果 |
|---|---|
| 後端 `.venv/bin/python -m pytest -q` | PASS：79 passed，無跳過；包含新引用、非示範、版本保留、無缺乏法律證據提示、週末／休市日期限、資金足夠不產生違約事件、英文缺口事件及資料庫匯入／時間軸整合測試 |
| 後端 `.venv/bin/ruff check .` | PASS：全部通過 |
| `.venv/bin/python ../../scripts/run_evaluation.py` | PASS：金融 27/27、法律事件 15/15、引用 34/34（原 30/30）、版本 4/4、建議偵測 12/12、輸出審查 6/6；準確率未下降 |
| 前端 `npx tsc --noEmit` | PASS |
| 前端 `npx eslint .` | PASS |
| 前端 `npx next build` | PASS；含 `/simulator/day-trading` 路由 |
| 本機 `.venv/bin/python -m app.services.seed` | PASS：連線固定為 127.0.0.1:54330；新增 1 份文件、270 條、433 區塊、2 個規則版本；冪等重跑測試通過 |
| 本機實際 HTTP API（8811） | PASS：中英文 `POST /api/v1/calculate/day-trading` 均 200 且選 1.0.0；`POST /api/v1/simulations` 為 201，`GET /api/v1/simulations/{id}/timeline` 為 200，附已驗證的第 57、82、91 條引用且無缺乏法律證據提示；12/02 成交、12/04 交割、12/07 條件式處理期限 |
| 頁面字串檢查 | PASS：當沖前端程式無待匯入提示；中英文 API 當沖輸出無過期法源提示，英文非原文欄位無中文殘留 |
| 瀏覽器互動驗收 | NOT RUN：已嘗試啟動 Playwright Chromium，但瀏覽器以 SIGABRT 中止、清理程序回 EPERM，尚未執行頁面點擊檢查 |
| 人工法律審查 | NOT RUN：需具法律專業的人員審查，兩條新版維持 pending_review |
| 正式資料庫、commit、push、部署 | NOT RUN：依本次指示禁止，未操作；未修改 `.env*` 或 `docs/DEPLOYMENT_ACCOUNTS.md` |

- 驗證程序以環境變數明確指定本機資料庫與本機驗證模式，不讀取或寫入正式資料庫。已清除本次新增的驗證暫存情境，並停止本次啟動的 8811 API、3002 前端；既有 8810 程序未動。
- 未解決限制：日曆資料未涵蓋的年度仍只排除週末，期限保留既有不確定性提示；規則尚待人工審查。建置有既有 `metadataBase` 提醒，pytest 有套件棄用提醒，均未造成驗收失敗。

### 部署紀錄（2026-11-26 晚，使用者同意 commit、正式資料庫新增與部署）
- commit `57988ee`（當沖法源補完）、`b54d7d1`（CI 修正）已推上 GitHub。CI：`b54d7d1` api／web 皆 success（先前 web 失敗是 tsc 在 Next.js 產生 `LayoutProps` 型別前執行，已在 CI 加 `npx next typegen`；api 失敗是英文測試只檢查第一筆模擬、示範情境 A 的「第一～四階段」未翻譯，已補翻譯並改為逐筆檢查）。
- 正式資料庫（Supabase `cxkcomcsnrcgkmdecsml`）：只執行 `seed_legal()`、`seed_rules()`，**沒有**執行 `main()`（避免在正式站建立示範帳號）。結果：新增 1 份文件（營業細則）、270 條、433 區塊、2 個規則版本；其餘資料未變。
- Vercel（帳號 bryankccy-2499，`npx vercel --global-config ~/.vercel-leverageguard`；本機 PATH 沒有 `vercel`）：API 由 `deploy/build_api.sh` 打包後部署（打包會刪掉 `.tmp/deploy-api/.vercel`，部署前要先備份再放回）；前端在 `apps/web` 部署。
- 部署後檢查 PASS：health 200；法規 9 份含營業細則；當沖試算使用 DT-SETTLEMENT-CYCLE／DT-FUNDING-GAP 1.0.0，引用第57、82、91條，無「待匯入」字樣；英文版無中文殘留（條文原文欄位除外）；未登入 /simulations 401；前端首頁與 /simulator/day-trading 200。
- NOT RUN：瀏覽器實際點擊選單中的當沖入口（瀏覽器擴充未連線）；規則人工法律審查（兩條新版仍為 pending_review）。
- 回復：Vercel 兩個專案 Promote 上一版；資料庫新增的文件與規則版本不影響舊版程式。
