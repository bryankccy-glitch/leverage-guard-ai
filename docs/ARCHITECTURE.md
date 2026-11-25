# 系統架構

```
apps/web（Next.js 16 App Router、React 19、Tailwind 4）
  ├─ 公開頁：/、/about、/how-it-works、/legal-resources、/privacy、/terms、/login、/register
  ├─ 應用：/dashboard、/simulator/*、/scenarios/*、/digital-twin/*、/legal/*、/contracts/*、/regulatory-monitor/*、/agents/*、/reports/*、/history、/notifications、/settings
  └─ 管理：/admin/*
        │ REST /api/v1（Bearer JWT）；Agent 進度用 SSE（fetch stream）
apps/api（FastAPI、Pydantic、SQLAlchemy Core + psycopg）
  ├─ financial_engine/   Layer 03：Decimal 計算（margin、day_trading、fees、interest、collateral、liquidation、portfolio）
  ├─ legal_rules/        Layer 04：Regulation-as-Code（宣告式規則、版本、引用驗證、衝突偵測）
  ├─ timeline_engine/    交易日曆（證交所休市日）、時間軸節點
  ├─ scenario_engine/    多步驟情境推演、12 個預設情境
  ├─ agents/             Layer 05：11 個 Agent、Orchestrator、Copilot、LLM Provider、Review guards
  ├─ legal_rag/          Layer 06：pg_trgm 關鍵字＋pgvector 語意＋RRF 混合排序
  ├─ contracts/          契約檔案驗證、擷取、條款切分、AI 白話（引用驗證）
  ├─ regulatory_monitor/ 版本差異、影響分析、待審查更新
  ├─ api/                public / user / admin 路由
  ├─ core/ security/     設定、DB（RLS 情境）、錯誤格式、限流、稽核、JWT、RBAC
  └─ services/           計算服務、報告（PDF/JSON/CSV）、seed、示範資料
PostgreSQL 17 + pgvector + pg_trgm（本機 docker；正式 Supabase）  Layer 07：RLS、append-only、稽核
Ollama（千問 qwen3:8b、qwen3-embedding:0.6b）／Gemini（選配）
```

## 核心原則

- **金融數字只由程式計算**：LLM 只能讀取已驗證結果；Verification Agent 比對計算結果雜湊，Review Agent 檢查 AI 文字中的未驗證數字。
- **法律規則由規則引擎執行**：規則條件只能用固定運算子，絕不執行 AI 產生的程式碼。
- **RLS 真的生效**：每個使用者請求在交易中 `set local role authenticated` 並帶入 JWT claims；系統工作明確使用 `service_session()`。
- **歷史不可覆寫**：`simulation_results`、`audit_logs` 有 append-only trigger；規則定義寫入後不可修改（只能建新版本）。

## 與需求的差異（決策紀錄）

| 需求 | 實作 | 理由 |
|---|---|---|
| Google Gemini／ADK | 預設 Ollama 千問；Gemini Provider 已寫好（設定 `LLM_PROVIDER=gemini`、`GOOGLE_API_KEY`、`GEMINI_MODEL`）；Orchestrator 自行實作 | 沒有 Gemini 金鑰，使用者指定千問；ADK 需額外相依，核心流程不能因此無法運作 |
| Redis＋Celery | FastAPI BackgroundTasks＋DB 紀錄（`jobs` 表已建立，供之後換成佇列） | 黑客松單機展示；Agent 進度與結果都寫入 DB，可稽核 |
| Supabase Auth（本機） | `AUTH_MODE=local` 示範帳號＋本機 auth stub；`AUTH_MODE=supabase` 驗證 Supabase JWT | 本機沒有 Supabase CLI；RLS 政策兩種模式共用 |
| next-intl 路由式 i18n | next-intl client provider（語言存在瀏覽器） | 避免 Cache Components 下的動態請求；URL 不帶語系 |
| PDF 字型 | 嵌入 Droid Sans Fallback（PyMuPDF 內建，Apache 2.0） | reportlab CID 字型未嵌入時擷取與跨平台顯示會亂碼（已實測） |
