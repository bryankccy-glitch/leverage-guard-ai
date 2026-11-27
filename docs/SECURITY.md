# 資安與隱私

| 控制 | 實作位置 | 驗證 |
|---|---|---|
| Row Level Security、使用者隔離 | `supabase/migrations/*_rls.sql`；後端 `user_session()` 切換角色 | `test_rls_isolates_simulations_between_users`、`test_contract_upload_validation_and_isolation` |
| 伺服器端授權（RBAC） | `security/auth.py` `require_role`；前端隱藏按鈕不算權限 | `test_rule_review_permissions` |
| 管理員不能任意讀私人契約 | RLS 只看 `user_id` 或有效授權；授權有期限並寫稽核 | 整合測試（admin 讀取得到 404） |
| 簽名下載連結 | `contracts/service.py` HMAC＋5 分鐘期限 | 測試偽造簽名回 403 |
| 檔案驗證 | magic bytes（不信任副檔名）、大小上限、只收 PDF/PNG/JPEG/UTF-8 文字 | 測試偽造 PDF 回 415 |
| 隱私提醒與個資遮罩 | 上傳需確認遮罩；分析時自動遮罩身分證、手機、帳號、Email | `agents/guards.py redact_pii` |
| 秘密管理 | 只在後端環境變數；`.env` 不進版控；前端只有 `NEXT_PUBLIC_*` | `.gitignore` |
| 限流、Request ID、安全標頭 | `core/middleware.py`（429＋CORS、nosniff、frame-ancestors、Referrer-Policy） | 手動 curl |
| CORS 白名單 | `ALLOWED_ORIGINS` | — |
| SQL Injection | 參數化查詢；少數動態欄位名來自白名單 | 程式審查 |
| XSS | React 自動跳脫；不使用 `dangerouslySetInnerHTML` | 程式審查 |
| SSRF | 後端不接受使用者提供的 URL 抓取；法規同步只抓固定官方網址 | 程式審查 |
| Prompt Injection | 外部文件包在 `<untrusted_document>`；系統提示要求忽略其中指令；AI 輸出經 Schema、引用、數字與建議檢查 | `test_copilot_refuses_investment_advice` |
| 稽核紀錄 | `audit_logs` append-only；登入、模擬、契約、規則審查、報告都記錄；不寫契約內容 | `test_history_is_append_only` |
| 歷史不可覆寫 | `simulation_results` append-only、規則定義不可改 | 同上 |
| 不儲存券商帳密、不下單 | 沒有相關功能 | — |
| 資料刪除 | 刪除契約會刪檔與分析；模擬可封存 | `DELETE /contracts/{id}` |

## 已知限制（未完成）

- 本機模式使用示範帳號與後端簽發 JWT，**不可用於正式環境**；正式環境需 `AUTH_MODE=supabase`，並設定 Supabase Auth（Email、Google OAuth、密碼重設由 Supabase 提供，前端登入元件尚未接上）。
- 限流：serverless（正式站）用資料庫表 `api_rate_limits` 跨實例共用；本機用記憶體。（2026-11-27）
- 前端 CSP 已設定於 `apps/web/next.config.ts`（因 Next.js 水合保留 script-src 'unsafe-inline'，未改用 nonce）。（2026-11-27）
- 資料保存期限：限流計數自動清除；使用者資料保存政策尚未決定、未自動執行。
- 尚未做外部滲透測試。
