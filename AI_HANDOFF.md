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
