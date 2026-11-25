# API 規格

前綴 `/api/v1`。完整 OpenAPI：`GET /api/v1/openapi.json`，互動文件：`/api/v1/docs`。

## 共通

- 驗證：`Authorization: Bearer <JWT>`；本機模式由 `POST /auth/dev/login` 取得。
- 錯誤：`{"error": {"code", "message", "request_id", "details"}}`；欄位錯誤在 `details[]`（field、code、message）。
- 每個回應帶 `X-Request-ID`；限流 `RATE_LIMIT_PER_MINUTE`（預設 600），超過回 429。
- 金額與比率一律以字串傳遞（例如 `"0.6"`），後端轉 Decimal。

## 端點

| 群組 | 方法與路徑 | 權限 |
|---|---|---|
| 系統 | GET /health、GET /ready | 公開 |
| 驗證 | GET /auth/config、POST /auth/dev/login、GET/PATCH /me | 公開／登入 |
| 計算 | POST /calculate/margin、/calculate/day-trading、/calculate/scenario、/calculate/portfolio；GET /calculate/presets | 公開（訪客可試算，不保存） |
| 模擬 | POST/GET /simulations；GET/DELETE /simulations/{id}；POST /simulations/{id}/calculate、/explain、/compare；GET /simulations/{id}/timeline | 登入 |
| 數位分身 | GET/POST /accounts；GET/PATCH /accounts/{id}；POST /accounts/{id}/positions；PATCH/DELETE /positions/{id} | 登入 |
| 法規 | GET /legal/search、/legal/documents、/legal/documents/{id}、/legal/articles/{id}、/legal/rights、/legal/obligations | 公開 |
| 規則 | GET /rules、/rules/{id}、/rules/{id}/versions；POST /rules/evaluate | 公開 |
| 契約 | POST /contracts/upload（multipart，需 `acknowledge_privacy=true`）、/contracts/demo；GET /contracts、/contracts/{id}、/contracts/{id}/file?sig=；POST /contracts/{id}/analyze、/contracts/compare、/contracts/{id}/grants；DELETE /contracts/{id} | 登入（檔案以簽名連結下載） |
| 法規監察 | GET /regulatory/updates、/regulatory/updates/{id}、/regulatory/updates/{id}/impact | 公開 |
| Agent | POST /agents/run；GET /agents、/agents/runs、/agents/runs/{id}、/agents/runs/{id}/events（SSE）；POST /agents/runs/{id}/retry、/cancel | 登入 |
| Copilot | POST /copilot/messages（保存對話）、POST /copilot/guest（不保存） | 登入／公開 |
| 報告 | POST/GET /reports；GET /reports/{id}；GET /reports/{id}/export?format=pdf\|json\|csv | 登入 |
| 通知 | GET /notifications；PATCH /notifications/{id}/read；POST /notifications/read-all；GET/PUT /notifications/subscriptions | 登入 |
| Dashboard | GET /dashboard、/history | 登入 |
| 管理 | POST /admin/rules/{id}/review；GET /admin/review-queue；POST /admin/regulatory/{id}/review、/admin/legal-sources/sync；GET /admin/evaluation、/admin/knowledge-base | legal_reviewer 以上 |
| 管理 | GET /admin/system-health、/admin/audit-logs、/admin/users、/admin/agent-config | system_admin |

## 範例：融資試算

```http
POST /api/v1/calculate/margin
{"buy_price":"100","quantity":"1000","financing_ratio":"0.6","current_price":"70","curve":false}
```

回應包含 `metrics`（每個指標的 value、unit、formula、inputs、rule_ids、simplified、note）、`rule_evaluation`（matched、missing_facts、triggered_events、unreviewed_rules）、`rules`（含官方引用與驗證結果）、`calculation_version`、`rule_version`、`legal_source_version`、`assumptions`、`warnings`。

## AI 結構化輸出

分析結果（`agent_runs.output`）欄位：`summary`、`calculation_reference`、`calculation_version`、`financial_explanation{summary, verified_metrics, assumptions}`、`legal_events[{event_type, status, trigger_condition, explanation, legal_citation_ids, missing_facts}]`、`investor_rights`、`investor_obligations`、`contract_findings`、`uncertainties`、`official_resources`、`limitations`、`verification`、`review`、`requires_professional_review: true`。`verified_metrics` 由系統填入，AI 無法修改。
