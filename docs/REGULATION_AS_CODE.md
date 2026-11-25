# Regulation-as-Code

規則檔：`data/rules/rules.json`；引擎：`apps/api/app/legal_rules/engine.py`。

## 規則結構

```json
{
  "rule_id": "MARGIN-CALL-THRESHOLD",
  "version": "1.0.0",
  "rule_type": "maintenance_threshold",
  "trading_type": "margin",
  "effective_from": null, "effective_to": null,
  "sources": [{"source_key": "twse:FL007121", "article_number": "第54條",
               "quote": "委託人信用帳戶之整戶擔保維持率低於百分之一百三十者，證券商應即通知委託人"}],
  "parameters": {"threshold": "1.30"},
  "condition": {"op": "lt", "field": "maintenance_ratio", "parameter": "threshold"},
  "event": "maintenance_threshold_breach",
  "required_facts": ["maintenance_ratio"],
  "exceptions": [],
  "plain_language": "…",
  "investor_rights": [], "investor_obligations": [], "broker_rights": [], "broker_obligations": [],
  "required_evidence": [],
  "is_demo": false
}
```

條件運算子只有 `lt / lte / gt / gte / eq / neq / exists / in` 與 `all / any / not` 組合；比較對象可以是參數、固定值或另一個事實（`field_ref`）。**不執行任何程式碼字串**。

## 引用驗證

載入時把每個 `quote` 去除空白後，比對 `documents.json` 中同一份文件、同一條號的內容。比對失敗的規則不能被選用，也不能被核准（API 回 409）。測試 `test_every_sourced_rule_quotes_official_text` 會檢查全部規則。

目前 27 個規則版本，有官方來源的 25 個全部通過；2 個沒有來源（T+2 交割、資金不足）標為 `is_demo` 並在時間軸顯示「法律依據待查證」。

## 版本選擇

1. 交易類型相符（或 `general`）。
2. 評估日期落在 `effective_from ~ effective_to`。
3. 狀態優先序：`active > approved > pending_review`；`draft` 只有明確要求才用；`superseded / suspended` 不用。
4. 同一規則有多個同優先序且參數不同的版本 → **標記衝突、不自行選擇**，需要人工確認（API 回 409）。
5. 有來源的示範規則（虛構 140%）預設不啟用，只在「規則版本比較」時以 `force_versions` 指定。

## 審查流程

所有規則從 `pending_review` 開始：可以在模擬中使用，但每個結果都標示「尚未經人工法律審查」。法律審查員在 `/admin/review-queue` 核准（approved）或啟用（active）；虛構示範規則不能啟用。核准紀錄寫入 `reviews` 與 `audit_logs`；啟用後通知使用過該規則的使用者，**舊計算結果保留不變**。

## 規則清單

| 規則 | 依據 |
|---|---|
| MARGIN-RATIO-FORMULA | 操作辦法第 53 條、管理辦法第 17 條 |
| MARGIN-CALL-THRESHOLD（130%） | 第 54 條 |
| MARGIN-CALL-DEADLINE（通知送達起 2 營業日） | 第 54 條 |
| MARGIN-CALL-AMOUNT | 第 54 條 |
| MARGIN-CALL-CANCEL（166% 或補足差額） | 第 55 條 |
| MARGIN-DISPOSAL-CONDITION | 第 55 條、管理辦法第 18 條 |
| MARGIN-DISPOSAL-DEFERRED | 第 55 條 |
| MARGIN-DISPOSAL-SURPLUS／SHORTFALL | 第 55 條 |
| MARGIN-LIQUIDITY-FAILURE（連續六營業日） | 第 55 條 |
| MARGIN-DEFAULT-REPORT | 第 81 條 |
| MARGIN-PENALTY | 第 82 條 |
| MARGIN-NO-WITHDRAW-GAINS | 管理辦法第 20 條 |
| MARGIN-CONTRACT-REQUIRED | 管理辦法第 10 條 |
| TAX-GENERAL（3‰）／TAX-DAYTRADE（1.5‰，至 2027-12-31） | 證交稅條例第 2、2-2 條 |
| DT-DEFINITION／ELIGIBILITY／REPORTING／UNMATCHED-LONG／SELL-FIRST-BUYIN／SELL-FIRST-COSTS／LOSS-SUSPENSION | 當日沖銷交易作業辦法第 1、2、6、7、9、13、14 條 |
| GENERAL-DISPUTE | 金融消費者保護法第 13 條 |
| DT-SETTLEMENT-CYCLE、DT-FUNDING-GAP | 尚未匯入原文（示範、待查證） |
