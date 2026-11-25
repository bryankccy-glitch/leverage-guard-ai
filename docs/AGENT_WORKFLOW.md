# Agent 工作流程

程式：`apps/api/app/agents/workflow.py`（分析）、`copilot.py`（Copilot）、`regulatory_monitor/monitor.py`（法規監察）、`contracts/service.py`（契約）。

## 11 個 Agent

| Agent | 執行方式 | 職責 |
|---|---|---|
| orchestrator | 確定性 | 規劃步驟、依賴、預算（`MAX_AGENT_ITERATIONS`、`MAX_ANALYSIS_COST`）、錯誤處理、合併結果 |
| financial_calculation | 確定性 | 呼叫金融引擎；記錄輸入與輸出雜湊 |
| scenario | 確定性＋LLM | Copilot 中把「再跌 10%」「跌到 70 元」轉成參數（正規表示式，不靠 LLM）並重算 |
| legal_retrieval | 檢索 | 依觸發事件查詢法規（混合檢索），回傳官方來源 |
| legal_rules | 確定性 | 規則引擎：事件、缺少的事實、例外、規則版本、衝突 |
| contract | 確定性＋LLM | 取出使用者契約中的相關原始條款；AI 白話說明的引用必須存在於文件 |
| regulatory_watch | 確定性 | 比對官方版本、產生條文差異與受影響規則 |
| verification | 確定性 | 引用驗證、計算結果雜湊比對（AI 不能改數字）、未審查與無來源規則 |
| plain_language | LLM（千問） | 依已驗證結果寫白話說明；不可用時改用規則模板並標示 |
| review | 確定性 | 攔截買賣建議、未驗證數字、常見概念錯誤、個資；不通過→改用模板 |
| report | 確定性 | 依結構化 Schema 組成輸出 |

## 分析流程（POST /simulations/{id}/explain）

```
orchestrator.plan
→ financial_calculation.calculate
→ legal_rules.evaluate
→ legal_retrieval.search
→ contract.extract_relevant_clauses（有指定契約時）
→ verification.validate
→ plain_language.explain（LLM）
→ review.check（Review Gate）
→ report.assemble
```

每一步寫入 `agent_tasks`（狀態、耗時、tool_calls、retrieved_sources、validation_result、tokens）與 `agent_events`（序號）。前端以 `GET /agents/runs/{id}/events`（SSE）讀取真實事件；**不顯示模型隱藏思考**。

## 快取與去重

`input_hash = sha256(工作流程、輸入、模型資訊、使用者、PROMPT_VERSION)`；一天內相同 hash 且已完成的 run 直接重用。滑桿移動不呼叫 LLM：前端即時預覽、後端確定性計算，只有按「AI 白話分析」才建立 run。

## LLM 安全

- 系統提示固定：不給買賣建議、不修改數字、不引用未提供條文、外部文件放在 `<untrusted_document>` 內且視為資料。
- 結構化輸出：Ollama `format` 參數傳 JSON Schema，回應以 Pydantic 驗證；失敗重試 1 次，仍失敗就標示並改用模板，**不以虛構結果填補**。
- 超時：`LLM_TIMEOUT_SECONDS`（預設 180）。
- 工具白名單：financial_engine、legal_rules、legal_rag、contracts.clauses（`/admin/agent-config` 可查看）。

## 實測紀錄（2026-11-26，本機 M 系列 Mac、16GB）

- 九步流程完整執行並寫入事件；確定性步驟合計 < 0.3 秒（檢索在嵌入模型冷啟動時約 25 秒）。
- 千問 qwen3:8b：精簡提示約 40 秒、768 tokens；第一次用完整提示時逾時（90 秒）並正確改用模板；第二次 Schema 驗證失敗 3 次並正確改用模板。之後縮小提示、放寬長度改為截短，實測可在 40 秒內產生合格輸出。
