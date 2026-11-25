# 資料庫結構

Migration：`supabase/migrations/20261126000001_schema.sql`（32 張表）、`20261126000002_rls.sql`（RLS）。本機另需 `supabase/local/00_auth_stub.sql`（模擬 Supabase 的 `auth` schema；正式 Supabase 不可執行）。

## 主要資料表

| 群組 | 表 | 重點 |
|---|---|---|
| 使用者 | profiles | role：investor / legal_reviewer / system_admin |
| 數位分身 | virtual_accounts、virtual_positions、collateral_assets | `is_simulation` 強制為 true；金額 numeric |
| 法規 | legal_documents、legal_document_versions、legal_articles、legal_chunks | 版本、content_hash、retrieved_at；`legal_chunks.embedding vector(1024)` HNSW 索引；條文 pg_trgm 索引 |
| 規則 | legal_rules、legal_rule_versions、rule_test_cases、regulatory_updates | 規則定義寫入後不可修改（trigger），(rule_id, version) 唯一 |
| 模擬 | simulation_scenarios、scenario_steps、simulation_results、calculation_snapshots、legal_events | `simulation_results` append-only（trigger） |
| 契約 | contracts、contract_clauses、contract_analyses、contract_access_grants | 檔案 SHA-256；授權有期限 |
| 引用 | legal_citations | validated / failed / insufficient_legal_evidence |
| Agent | agent_runs、agent_tasks、agent_events、copilot_messages | input_hash 快取；事件序號唯一 |
| 其他 | reports、notifications、notification_subscriptions、reviews、audit_logs、jobs | audit_logs append-only；通知 dedupe |

## RLS 摘要

| 資料 | 規則 |
|---|---|
| 私人資料（帳戶、模擬、報告、Copilot、通知） | 只有本人（`user_id = auth.uid()`） |
| 契約 | 本人，或有未過期 `contract_access_grants` 的被授權者；**管理員沒有預設權限** |
| 法規、規則、法規更新 | anon 與 authenticated 可讀；寫入只有 service_role |
| 規則審查 | legal_reviewer、system_admin 可更新狀態 |
| 稽核紀錄 | 本人或 system_admin 可讀；只能新增 |
| jobs | 只有 service_role |

所有表都 `force row level security`；後端以 `set local role authenticated` 讓政策對每個使用者請求生效。整合測試 `tests/test_api_integration.py` 驗證跨使用者讀取、刪除與管理員讀取契約都被擋下。
