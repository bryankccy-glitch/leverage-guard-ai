"""回應語系（zh-TW／en）。

計算、規則與時間軸引擎一律產生繁體中文；請求帶 `Accept-Language: en` 時，由 middleware 在
送出 JSON 前把已知字串換成英文。這樣引擎程式與數字完全不動，中文版結果不受影響。

不翻譯：官方條文原文（quote、content）、使用者契約原文（original_text）——英文版只翻譯標題與說明，
不把非官方譯文當成法條。檢索關鍵字、正規表示式與 prompt 也不在這裡處理。
"""
from __future__ import annotations

import json
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any

_locale: ContextVar[str] = ContextVar("locale", default="zh-TW")

SKIP_KEYS = frozenset({"quote", "content", "original_text", "highlights", "text", "removed", "added",
                       "document_hash", "content_hash", "storage_path", "official_url", "url"})


def parse_accept_language(header: str | None) -> str:
    """只支援 en 與 zh-TW；其他或缺少時用 zh-TW。"""
    if not header:
        return "zh-TW"
    first = header.split(",")[0].strip().lower()
    return "en" if first.startswith("en") else "zh-TW"


def set_locale(locale: str):
    return _locale.set(locale)


def reset_locale(token) -> None:
    _locale.reset(token)


def get_locale() -> str:
    return _locale.get()


def is_en() -> bool:
    return _locale.get() == "en"


# ---------------------------------------------------------------- 完全相同的字串
EXACT: dict[str, str] = {
    # --- 共用 / 欄位名稱
    "模擬資產": "Simulated asset", "買入價格": "Buy price", "股數": "Shares", "融資比例": "Financing ratio",
    "模擬目前價格": "Simulated current price", "維持率門檻": "Maintenance threshold", "融資年利率": "Annual margin interest rate",
    "其他擔保品市值": "Other collateral value", "手續費率": "Fee rate", "手續費折扣": "Fee discount",
    "最低手續費": "Minimum fee", "交易稅率": "Transaction tax rate", "融資金額計算單位": "Margin loan rounding unit",
    "持有天數不能是負數": "Holding days cannot be negative", "年基準天數只支援 360 或 365": "Day-count basis must be 360 or 365",
    "僅計算單一融資部位，不含融券、其他信用部位與整戶合併": "Only a single margin position is calculated; short sales, other credit positions and account-level aggregation are excluded",
    "以使用者輸入的模擬價格代替官方規定的計算日收盤價": "The simulated price you entered stands in for the official closing price on the calculation date",
    "原始交易金額": "Purchase value", "融資借款": "Margin loan", "P0 × Q × F（依融資金額計算單位捨去）": "P0 × Q × F (rounded down to the loan unit)",
    "自備本金": "Own funds", "原始交易金額 − 融資借款": "Purchase value − margin loan", "實際投入現金": "Cash invested",
    "自備本金 ＋ 買進手續費": "Own funds + buy fee", "模擬股票市值": "Simulated market value", "未計費用損益": "P&L before costs",
    "模擬市值 − 原始交易金額": "Simulated market value − purchase value", "買進手續費": "Buy fee",
    "max(最低手續費, 原始交易金額 × 費率 × 折扣)": "max(minimum fee, purchase value × fee rate × discount)",
    "估計賣出手續費": "Estimated sell fee", "max(最低手續費, 模擬市值 × 費率 × 折扣)": "max(minimum fee, market value × fee rate × discount)",
    "估計證券交易稅": "Estimated securities transaction tax", "模擬市值 × 稅率": "Market value × tax rate",
    "估計融資利息": "Estimated margin interest", "融資借款 × 年利率 × 持有天數 ÷ 年基準": "Margin loan × annual rate × holding days ÷ day-count basis",
    "估計交易成本合計": "Estimated total trading costs", "買進手續費 ＋ 賣出手續費 ＋ 交易稅 ＋ 利息": "Buy fee + sell fee + transaction tax + interest",
    "模擬淨損益": "Simulated net P&L", "未計費用損益 − 交易成本合計": "P&L before costs − total trading costs",
    "本金損益率": "Return on own funds", "模擬淨損益 ÷ 自備本金 × 100%": "Net P&L ÷ own funds × 100%",
    "擔保維持率（單一部位）": "Maintenance ratio (single position)", "(模擬市值 ＋ 抵繳市值) ÷ 融資借款 × 100%": "(market value + substitute collateral) ÷ margin loan × 100%",
    "估計追繳門檻股價": "Estimated call-threshold price", "(融資借款 × 門檻 − 抵繳市值) ÷ Q": "(margin loan × threshold − substitute collateral) ÷ Q",
    "取消追繳紀錄所需股價": "Price needed to cancel the margin call", "(融資借款 × 取消門檻 − 抵繳市值) ÷ Q": "(margin loan × cancel threshold − substitute collateral) ÷ Q",
    "估計補繳差額": "Estimated top-up amount",
    "融資借款 −（價格 × 股數 × 融資比率）−（抵繳市值 × 融資比率）": "Margin loan − (price × shares × financing ratio) − (substitute collateral × financing ratio)",
    "帳戶淨值（市值＋抵繳−借款）": "Account equity (market value + collateral − loan)", "模擬市值 ＋ 抵繳市值 − 融資借款": "Market value + substitute collateral − margin loan",
    "未輸入融資利率，淨損益未扣除利息": "No margin interest rate entered; net P&L excludes interest",
    "模擬市值已低於融資借款：即使全部賣出也不足清償，可能產生剩餘債務": "Simulated market value is below the margin loan: even selling everything would not repay it, so residual debt may arise",
    "計算單位": "Rounding unit", "費率": "Fee rate", "折扣": "Discount", "最低": "Minimum", "假設以模擬價格全部賣出": "Assumes selling everything at the simulated price",
    "稅率": "Tax rate", "年利率": "Annual rate", "天數": "Days", "年基準": "Day-count basis", "計息天數算法依券商契約": "Interest day-count follows your brokerage contract",
    "抵繳市值": "Substitute collateral value", "官方以整戶計算；此處僅單一部位": "Officially calculated per account; this is a single position only",
    "門檻": "Threshold", "不是確定的斷頭價：處分還受通知送達、補繳期限、契約與成交狀況影響": "Not a definite liquidation price: disposal also depends on notice delivery, the top-up deadline, your contract and fills",
    "取消門檻": "Cancel threshold", "僅在維持率低於門檻時計算；實際以券商通知為準": "Only calculated when the ratio is below the threshold; your broker's notice is authoritative",
    # --- 當沖
    "買進價格": "Buy price", "賣出價格": "Sell price", "可用交割資金": "Available settlement funds", "當沖稅率": "Day-trade tax rate",
    "一般稅率": "General tax rate", "借券費率": "Borrowing fee rate", "手續費依股數比例分攤到已沖銷與未沖銷部分": "Fees are allocated between offset and non-offset shares by quantity",
    "假設券商已依規定在成交當日申報沖銷（作業辦法第 14 條：未申報者視為不予沖銷）": "Assumes the broker reported the offset on the trade date as required (Operating Rules Art. 14: unreported trades are treated as not offset)",
    "交易方向只能是先買後賣或先賣後買": "Direction must be buy-first or sell-first", "買進股數": "Shares bought", "賣出股數": "Shares sold",
    "買進或賣出股數至少一項大於 0": "Shares bought or sold must be greater than 0", "先買後賣必須有買進股數": "Buy-first requires shares bought",
    "先賣後買必須有賣出股數": "Sell-first requires shares sold", "買進總金額": "Total buy amount", "買進價格 × 買進股數": "Buy price × shares bought",
    "賣出總金額": "Total sell amount", "賣出價格 × 賣出股數": "Sell price × shares sold", "已沖銷股數": "Offset shares",
    "min(買進股數, 賣出股數)": "min(shares bought, shares sold)", "未沖銷股數（買進未賣出）": "Non-offset shares (bought, not sold)",
    "買進股數 − 已沖銷股數": "Shares bought − offset shares", "未沖銷股數（賣出未買回）": "Non-offset shares (sold, not bought back)",
    "賣出股數 − 已沖銷股數": "Shares sold − offset shares", "已沖銷毛損益": "Gross P&L on offset shares",
    "(賣出價格 − 買進價格) × 已沖銷股數": "(sell price − buy price) × offset shares", "手續費合計": "Total fees", "買進手續費 ＋ 賣出手續費": "Buy fee + sell fee",
    "當沖交易稅（已沖銷部分）": "Day-trade tax (offset portion)", "已沖銷賣出金額 × 當沖稅率": "Offset sell amount × day-trade tax rate",
    "一般交易稅（未沖銷賣出）": "General transaction tax (non-offset sale)", "未沖銷賣出金額 × 一般稅率": "Non-offset sell amount × general tax rate",
    "已沖銷淨損益": "Net P&L on offset shares", "毛損益 − 分攤手續費 − 當沖交易稅": "Gross P&L − allocated fees − day-trade tax",
    "估計交割應付款": "Estimated settlement payable", "未沖銷買進價金與手續費 − 已沖銷淨損益 − 未買回賣出價款淨額": "Non-offset purchase amount and fees − net P&L on offset shares − net proceeds of unbought sales",
    "估計資金缺口": "Estimated funding gap", "max(0, 交割應付款 − 可用交割資金)": "max(0, settlement payable − available settlement funds)",
    "估計強制買回成本": "Estimated forced buy-in cost", "假設買回價 × 未買回股數 ＋ 手續費 ＋ 借券費": "Assumed buy-back price × unbought shares + fees + borrowing fee",
    "估計交割資金不足。這是預估，不代表已發生違約；是否違約依交割期限與券商確認": "Estimated shortfall in settlement funds. This is an estimate, not a default; whether a default occurs depends on the settlement deadline and your broker's confirmation",
    "價格": "Price", "買進": "Buy", "賣出": "Sell", "未完成同數量沖銷的賣出，不適用當沖減半稅率": "Sales not offset by an equal quantity do not get the reduced day-trade tax rate",
    "負數代表應收": "A negative value means a receivable", "可用資金": "Available funds", "預估值，不等於違約": "An estimate, not a default",
    "假設買回價": "Assumed buy-back price", "假設借券費率": "Assumed borrowing fee rate",
    "借券費率上限為收盤價 7%（作業辦法第 7 條），實際依當日標借結果": "The borrowing fee is capped at 7% of the closing price (Operating Rules Art. 7); the actual fee depends on that day's borrowing auction",
    "先賣後買未買回：未提供強制買回價格與借券費率假設，無法估算強制買回成本": "Sold first and not bought back: without an assumed buy-in price and borrowing fee rate, the forced buy-in cost cannot be estimated",
    # --- 處分 / 整戶
    "處分股數": "Shares to dispose", "處分價格": "Disposal price", "未清償借款": "Outstanding loan", "成交股數必須介於 0 與處分股數之間": "Filled shares must be between 0 and shares to dispose",
    "處分成交金額": "Disposal proceeds", "處分價格 × 成交股數": "Disposal price × filled shares", "處分手續費與交易稅": "Disposal fees and tax",
    "賣出手續費 ＋ 證券交易稅": "Sell fee + securities transaction tax", "處分淨所得": "Net disposal proceeds", "處分成交金額 − 處分成本": "Disposal proceeds − disposal costs",
    "應清償債務合計": "Total debt to repay", "融資借款 ＋ 利息 ＋ 違約金": "Margin loan + interest + penalty", "可能的剩餘債務": "Possible residual debt",
    "max(0, 應清償債務 − 處分淨所得 − 可抵充款項)": "max(0, debt − net disposal proceeds − offsettable funds)", "應發還溢額": "Surplus to be returned",
    "max(0, 處分淨所得 ＋ 可抵充款項 − 應清償債務)": "max(0, net disposal proceeds + offsettable funds − debt)", "未成交股數": "Unfilled shares",
    "處分股數 − 成交股數": "Shares to dispose − filled shares", "成交股數": "Filled shares", "利息": "Interest", "違約金": "Penalty",
    "可抵充款項": "Offsettable funds", "實際金額以券商結算為準": "Actual amounts follow your broker's settlement",
    "抵繳品市值": "Substitute collateral value", "至少需要一個融資部位": "At least one margin position is required", "模擬價格": "Simulated price",
    "融資金額": "Margin loan", "整戶融資部位市值": "Account margin positions market value", "Σ 股數 × 模擬價格": "Σ shares × simulated price",
    "整戶融資金額": "Account margin loan total", "Σ 融資金額": "Σ margin loans", "整戶擔保維持率": "Account-level maintenance ratio",
    "(Σ市值 ＋ 抵繳品市值) ÷ Σ融資金額 × 100%": "(Σ market value + substitute collateral) ÷ Σ margin loans × 100%", "不含融券部位": "Excludes short positions",
    "數字必須是有限值": "Number must be finite", "布林值不能當數字": "A boolean is not a number", "金額不接受 float，請傳字串或 Decimal": "Amounts must be strings or Decimal, not float",
    # --- 情境推演
    "使用者建立模擬融資部位": "You open a simulated margin position", "假設追繳通知於維持率跌破當日送達": "Assumes the margin call notice is delivered the day the ratio falls below the threshold",
    "假設追繳通知於跌破後次一營業日送達": "Assumes the margin call notice is delivered the business day after the breach", "券商通知送達日未知": "Broker notice delivery date unknown",
    "對通知、處分或結算有疑義時": "If you dispute a notice, disposal or settlement", "情境步驟之間的每日價格未知，以下一個步驟的價格代表期限當日價格": "Daily prices between scenario steps are unknown; the next step's price stands for the price on the deadline",
    "情境至少需要一個步驟": "A scenario needs at least one step", "應清償債務": "Debt to repay", "擔保維持率%": "Maintenance ratio %",
    "是否申報違約取決於券商實際通知與清償情形": "Whether a default is reported depends on the broker's actual notices and your repayment",
    "期限屆滿仍未補足，且維持率仍低於門檻（以本步驟模擬價格判斷）": "Deadline passed without a top-up and the ratio is still below the threshold (judged at this step's simulated price)",
    "期限當日維持率回升至門檻以上": "Ratio back above the threshold on the deadline", "未計入除權息、停止買賣等特殊價格認定": "Special pricing (ex-rights/dividends, trading halts, etc.) is not considered",
    "模擬券商發出補繳通知（不是真實券商通知）": "Simulated broker issues a top-up notice (not a real broker notice)", "模擬市值": "Simulated market value",
    "步驟的交易日數不能是負數": "Step trading days cannot be negative", "沒有生效的維持率門檻規則，無法推演（需要人工確認規則）": "No active maintenance threshold rule, so the scenario cannot run (rule needs manual confirmation)",
    "沒有通知送達日，無法計算補繳期限": "Without a notice delivery date, the top-up deadline cannot be calculated", "維持率回升至取消門檻以上，或補繳達通知差額": "Ratio back above the cancel threshold, or top-ups reach the notified amount",
    "自次一營業日起處分": "Disposal from the next business day", "若補足通知與限期清償後仍未清償": "If still unpaid after the shortfall notice and repayment deadline",
    "處分以模擬價格成交，實際成交價可能不同": "Disposal is filled at the simulated price; actual fills may differ", "處分所得不足清償債務": "Disposal proceeds do not cover the debt",
    "處分所得清償後仍有剩餘": "Disposal proceeds exceed the debt", "補繳後融資金額": "Margin loan after top-up", "補繳現金視為償還部分融資": "Top-up cash is treated as partial loan repayment",
    "補繳金額": "Top-up amount", "通知送達日未知：不計算補繳期限": "Notice delivery date unknown: top-up deadline not calculated",
    "（下午五時前）": " (by 5 p.m.)", "交割日依 T+2 估算（尚未匯入證交所營業細則原文，屬待查證資訊）": "Settlement date estimated as T+2 (TWSE Operating Rules text not yet imported; unverified)",
    "估計交割應付款大於可用交割資金": "Estimated settlement payable exceeds available settlement funds", "假設券商已於成交當日下午六時前申報沖銷": "Assumes the broker reported the offset by 6 p.m. on the trade date",
    "先買後賣": "Buy first", "先賣後買": "Sell first", "對處理結果有疑義時": "If you dispute the outcome", "強制買回還券之次一營業日下午五時前": "By 5 p.m. on the business day after the forced buy-in returns the shares",
    "成交日期不在當沖減半稅率的適用期間，以一般稅率計算": "The trade date is outside the reduced day-trade tax period, so the general rate applies",
    "成交日期不是交易日，請確認日期": "The trade date is not a trading day; please check the date", "未提供強制買回價格與借券費率假設，無法估算成本": "Without an assumed buy-in price and borrowing fee rate, the cost cannot be estimated",
    "未沖銷股數": "Non-offset shares", "未買回股數": "Shares not bought back", "若券商未申報，視為不予沖銷，全部須全額交割": "If the broker does not report it, the trade is treated as not offset and settled in full",
    "這是預估資金缺口，不是違約。交割日前補足即可；是否構成違約交割，以券商確認為準": "This is an estimated funding gap, not a default. Topping up before settlement is enough; whether it becomes a settlement default is for your broker to confirm",
    "還券日以強制買回當日全數成交估算；未全數買回時期限會延後": "The return date assumes the forced buy-in fills in full that day; if not, the deadline moves later",
    # --- 預設情境
    "交割資金不足": "Insufficient settlement funds", "交易規則版本變更（虛構示範規則 140%）": "Rule version change (fictional demo rule: 140%)",
    "先賣後買但未完成買回": "Sold first but not bought back", "收到補繳通知後未補繳": "No top-up after the notice", "流動性不足：處分連續六日無法全數成交": "Illiquidity: disposal not fully filled for six days",
    "當沖買進後未完成賣出": "Day trade bought but not sold", "示範股票（虛構）": "Demo stock (fictional)", "第一階段": "Stage 1", "第二階段": "Stage 2", "第三階段": "Stage 3", "第四階段": "Stage 4","股價下跌 10%": "Price falls 10%", "股價下跌 20%": "Price falls 20%",
    "股價下跌 5%": "Price falls 5%", "處分後仍有剩餘債務": "Residual debt after disposal", "證券商契約條款不同（通知於次一營業日送達）": "Different contract terms (notice delivered the next business day)",
    "連續數日下跌（自訂跌幅，非真實漲跌幅限制）": "Several days of declines (custom drops, not real price limits)",
    # --- 時間軸事件
    "交割日": "Settlement date", "估計交割資金不足": "Estimated settlement funds shortfall", "使用者補繳": "You top up", "借券與強制買回": "Share borrowing and forced buy-in",
    "剩餘債務：通知補足": "Residual debt: notice to pay", "券商申報沖銷": "Broker reports the offset", "市場價格變動": "Market price change", "建立當沖交易": "Open a day trade",
    "建立融資部位": "Open a margin position", "強制買回費用清償期限": "Forced buy-in cost payment deadline", "擔保品處分（模擬）": "Collateral disposal (simulated)",
    "暫不處分（追繳未取消）": "Disposal deferred (margin call not cancelled)", "未沖銷部分轉一般交割": "Non-offset portion moves to regular settlement",
    "符合擔保品處分條件": "Collateral disposal conditions met", "維持率低於追繳門檻": "Ratio below the call threshold", "處分連續未能全數成交": "Disposal repeatedly not fully filled",
    "補繳期限": "Top-up deadline", "補繳通知（模擬）": "Top-up notice (simulated)", "追繳紀錄取消": "Margin call cancelled", "金融消費爭議處理": "Financial consumer dispute handling",
    "限期清償逾期：申報違約": "Repayment overdue: default reported", "溢額發還": "Surplus returned",
    "此事件的法律依據尚未匯入官方原文（Insufficient Legal Evidence）": "The legal basis for this event has not been imported from official text (Insufficient Legal Evidence)",
    "n 必須 ≥ 0": "n must be ≥ 0", "此期間部分日期不在證交所已公告的休市日資料內，僅排除週末，實際期限可能不同": "Some dates in this period are outside TWSE's published holiday data, so only weekends are excluded; the actual deadline may differ",
    # --- 規則引擎
    "不在生效期間": "Not in effect", "同時有多個生效版本且參數不同，需要人工確認": "Several active versions with different parameters; needs manual confirmation",
    "引用文字與官方條文不符": "Quoted text does not match the official article", "引用驗證失敗": "Citation verification failed", "（找不到文件）": "(document not found)",
    "找不到條號": "Article number not found", "示範規則（未啟用示範模式）": "Demo rule (demo mode not enabled)", "草稿規則": "Draft rule", "資料庫中沒有這份文件": "This document is not in the database",
    # --- API
    "Simulation 模擬資料": "Simulation data", "下載連結無效或已過期": "The download link is invalid or has expired", "分析尚未完成，無法產生報告": "Analysis is not finished, so a report cannot be generated",
    "只接受 PDF、PNG、JPEG 或 UTF-8 純文字檔": "Only PDF, PNG, JPEG or UTF-8 plain text files are accepted", "只有失敗或取消的執行可以重試": "Only failed or cancelled runs can be retried",
    "同一情境（套用比較規則版本）": "Same scenario (with the comparison rule version)", "尚未計算": "Not calculated yet", "找不到執行紀錄": "Run not found", "找不到報告": "Report not found",
    "找不到契約": "Contract not found", "找不到模擬情境": "Scenario not found", "找不到虛擬帳戶": "Virtual account not found", "找不到部位": "Position not found",
    "本比較只列出文件中的原始條款，不推薦任何證券商。": "This comparison only lists the original clauses in the documents and does not recommend any broker.",
    "檔案是空的": "The file is empty", "檔案超過大小上限": "The file exceeds the size limit", "沒有要更新的欄位": "No fields to update",
    "請先確認隱私提醒（遮罩身分證字號、帳號、地址、電話、簽名）": "Please confirm the privacy reminder first (mask ID numbers, account numbers, addresses, phone numbers, signatures)",
    "這筆執行沒有對應的模擬情境，請重新送出分析": "This run has no matching scenario; please submit the analysis again", "0（本機模型）": "0 (local model)",
    "契約分析完成": "Contract analysis complete", "報告已產生": "Report generated", "你儲存的模擬所使用的規則已更新": "A rule used by your saved simulations has been updated",
    "尚未執行 scripts/run_evaluation.py": "scripts/run_evaluation.py has not been run", "已核准的更新仍需建立新規則版本並經啟用後才會影響計算": "An approved update only affects calculations after a new rule version is created and activated",
    "引用驗證未通過的規則不能核准": "Rules that failed citation verification cannot be approved", "找不到法規更新": "Regulatory update not found", "找不到被授權的帳號": "Authorised account not found",
    "找不到規則版本": "Rule version not found", "未啟用 LEGAL_SOURCE_SYNC_ENABLED，只比對本機已下載的官方資料": "LEGAL_SOURCE_SYNC_ENABLED is off; only locally downloaded official data is compared",
    "此更新尚未對應到可比較的規則草案": "This update has no comparable draft rule yet", "示範情境：100 元買進 1,000 股、融資六成，股價 82 → 75 元": "Demo scenario: buy 1,000 shares at 100 with 60% financing, price 82 → 75",
    "示範更新只會標記審查結果，不會套用到正式規則": "Demo updates only record the review outcome and are never applied to real rules",
    "示範規則為虛構，僅展示版本差異與重新計算；不會套用到正式計算。": "The demo rule is fictional and only shows version differences and recalculation; it is never applied to real calculations.",
    "虛構示範規則不能啟用到正式計算": "Fictional demo rules cannot be activated for real calculations", "規則版本尚未匯入資料庫": "Rule versions have not been imported into the database",
    "只能使用示範帳號登入（本機模式）": "Only demo accounts can log in (local mode)", "找不到條文": "Article not found", "找不到法規": "Regulation not found", "找不到規則": "Rule not found",
    "本機登入未啟用": "Local login is not enabled", "請先登入": "Please log in first", "系統發生錯誤，請稍後再試": "Something went wrong. Please try again later.",
    "輸入資料不正確": "Invalid input", "請求太頻繁，請稍後再試": "Too many requests. Please try again later.",
    "以模擬價格代替收盤價": "Simulated price used instead of the closing price", "只計算融資部位與抵繳品，不含融券": "Only margin positions and substitute collateral are included; short sales are not",
    "目前沒有可用的維持率門檻規則（可能有衝突待人工確認）": "No maintenance threshold rule is available (there may be a conflict awaiting manual review)",
    "必須是數字": "Must be a number", "必須是有限數字": "Must be a finite number", "使用者": "User", "尚未設定 SUPABASE_JWT_SECRET": "SUPABASE_JWT_SECRET is not set",
    "帳號不存在": "Account does not exist", "沒有權限執行此操作": "You do not have permission to do this", "登入已過期，請重新登入": "Your session has expired. Please log in again.",
    "登入憑證無效": "Invalid credentials", "示範投資人": "Demo investor", "示範投資人二": "Demo investor 2", "示範法律審查員": "Demo legal reviewer", "示範系統管理員": "Demo system admin",
    "受影響的規則需由法律審查員確認後建立新版本，不會自動套用": "Affected rules need a legal reviewer to confirm and create a new version; nothing is applied automatically",
    # --- 示範資料（資料庫內容）
    "示範融資帳戶（模擬）": "Demo margin account (simulated)", "示範股票 A（虛構）": "Demo stock A (fictional)", "示範股票 B（虛構）": "Demo stock B (fictional)",
    "示範情境 A：融資追繳與剩餘債務": "Demo scenario A: margin call and residual debt", "示範情境 B：當沖未完成沖銷": "Demo scenario B: incomplete day-trade offset",
    "【示範】假設整戶擔保維持率追繳門檻由 130% 調整為 140%": "[Demo] Hypothetical change of the account-level call threshold from 130% to 140%",
    "臺灣證券交易所（虛構示範）": "Taiwan Stock Exchange (fictional demo)", "虛構示範融資融券契約.pdf": "Fictional demo margin contract.pdf", "示範證券（虛構）": "Demo Securities (fictional)",
    "我的模擬融資帳戶": "My simulated margin account",
    "這是虛構的法規變動，用來展示版本差異、重新計算與人工審查流程。現行規定仍為 130%。": "This is a fictional regulatory change used to demonstrate version differences, recalculation and the human review process. The current rule is still 130%.",
    "同一部位的追繳門檻股價上升，較早進入追繳": "The call-threshold price for the same position rises, so the margin call comes earlier",
    "更早觸發補繳通知與後續處分流程": "Top-up notices and the disposal process are triggered earlier",
    # --- Agent / 工作流程
    "AI 說明未通過審查，已改用規則模板": "The AI explanation failed review; a rule template was used instead",
    "以下說明由規則模板產生（未使用生成式 AI），內容來自已驗證的計算結果與規則。": "The explanation below was generated from a rule template (no generative AI), using verified calculation results and rules.",
    "依交易情境檢索相關法規條文與官方來源": "Retrieve relevant legal articles and official sources for the trading scenario", "假設": "Assumptions",
    "僅支援單一融資部位或單筆當沖；整戶與融券部位未完整納入。": "Only a single margin position or a single day trade is supported; account-level and short positions are not fully included.",
    "全國法規資料庫": "Laws & Regulations Database (MOJ)", "最後擔保維持率%": "Final maintenance ratio %", "最後模擬價格": "Final simulated price",
    "取出使用者契約中的相關原始條款": "Extract the relevant original clauses from the user's contract", "呼叫 Regulation-as-Code 規則引擎，找出法律事件與缺少的事實": "Call the Regulation-as-Code rule engine to find legal events and missing facts",
    "審查通過": "Review passed", "工作流程完成": "Workflow complete", "已組成結構化結果": "Structured result assembled", "影響": "Impact",
    "把自然語言假設轉成結構化情境參數並呼叫情境引擎": "Turn natural-language assumptions into structured scenario parameters and call the scenario engine",
    "把金融與法律結果轉成白話繁體中文，保留條件與不確定性": "Turn financial and legal results into plain language, keeping conditions and uncertainty",
    "整合計算、法規、契約與時間軸，產生結構化結果": "Combine calculations, regulations, contract and timeline into a structured result",
    "數字由程式依輸入假設計算，實際金額以券商對帳單與通知為準。": "Numbers are calculated by the program from your assumptions; actual amounts follow your broker's statements and notices.",
    "日期": "Date", "未知": "Unknown", "本結果是模擬與教育用途，不是投資建議，也不是律師的正式法律意見。": "This result is for simulation and education only. It is not investment advice or formal legal advice from a lawyer.",
    "條件": "Condition", "檢查買賣建議、未驗證數字、個資與事實推論混淆": "Check for trading advice, unverified numbers, personal data, and confusion of facts with inference",
    "比較官方法規新舊版本，建立待審查的規則更新": "Compare old and new official regulations and create rule updates for review", "沒有": "None",
    "法律與命令原文": "Original text of laws and regulations", "狀態": "Status", "申報違約": "Default reported", "事件": "Events",
    "臺灣證券交易所 法規分享知識庫": "TWSE Regulations Knowledge Base", "融資融券、當沖相關規章原文": "Original margin and day-trading rules",
    "規則已自動比對官方原文，但尚未全部經過具金融法律專業的人員審查。": "Rules have been checked against the official text automatically, but not all have been reviewed by a financial-law professional.",
    "規則說明": "Rule explanation", "規劃工作流程、管理依賴、預算與重試、整合輸出": "Plan the workflow, manage dependencies, budget and retries, and combine outputs",
    "證券主管機關": "Securities regulator", "財團法人金融消費評議中心": "Financial Ombudsman Institution",
    "金融消費爭議：先向券商申訴，未獲處理可申請評議": "Financial consumer disputes: complain to the broker first; if unresolved, apply for mediation",
    "金融監督管理委員會證券期貨局": "Securities and Futures Bureau, Financial Supervisory Commission", "關鍵數字": "Key numbers",
    "驗證引用、規則版本與計算結果一致性": "Verify citations, rule versions and calculation consistency", "驗證輸入並呼叫金融計算引擎，不以 LLM 計算數字": "Validate inputs and call the financial engine; numbers are never calculated by the LLM",
    "我不能提供個股買賣、進出場時機、槓桿比例或股價預測的建議，也不能協助規避交割或清償義務。我可以幫你：用目前的模擬參數試算不同價格下的維持率與損益、說明追繳與擔保品處分的規定、或整理你契約中的通知與處分條款。":
        "I can't advise on buying or selling specific stocks, timing, leverage levels or price predictions, and I can't help avoid settlement or repayment obligations. I can: recalculate the ratio and P&L at different prices with your current inputs, explain the rules on margin calls and collateral disposal, or summarise the notice and disposal clauses in your contract.",
    "生成式 AI 目前無法使用，以下是系統依你的問題檢索到的官方條文與規則說明：": "Generative AI is unavailable right now. Here are the official articles and rule explanations retrieved for your question:",
    "尚未設定 GOOGLE_API_KEY 與 GEMINI_MODEL": "GOOGLE_API_KEY and GEMINI_MODEL are not set", "已設定不使用生成式 AI": "Generative AI is turned off in settings",
    "語意檢索未啟用：尚未設定 EMBEDDING_MODEL 或尚未建立向量，結果只來自關鍵字檢索": "Semantic search is off: EMBEDDING_MODEL is not set or no vectors have been built, so results come from keyword search only",
    # --- 評估頁（scripts/run_evaluation.py 的結果）
    "LLM 白話說明清晰度與正確性（需人工審查）": "Clarity and accuracy of LLM plain-language explanations (needs human review)",
    "契約條款擷取正確率（需人工標註的真實契約集）": "Contract clause extraction accuracy (needs a human-labelled set of real contracts)",
    "Prompt Injection 抵抗（需 LLM 對抗測試）": "Prompt injection resistance (needs adversarial LLM testing)",
    "使用者理解度（需使用者研究）": "User comprehension (needs user research)",
    # --- 審查閘門訊息
    "把擔保維持率誤稱為槓桿比例": "Calls the maintenance ratio a leverage ratio",
    "補繳差額依第 54 條公式計算，不是補到 130%": "The top-up amount follows the Art. 54 formula; it is not 'back to 130%'",
    "追繳門檻股價不是確定的斷頭價": "The call-threshold price is not a definite liquidation price",
    "處分與違約須視通知、期限與契約而定": "Disposal and default depend on notices, deadlines and the contract",
    # --- Copilot 拒答附帶的風險資訊
    "整戶擔保維持率低於 130% 時，券商會通知補繳；通知送達後 2 個營業日內未補足、且期限當日仍低於門檻，券商自次一營業日起處分擔保品（證交所融資融券業務操作辦法第 54、55 條）。":
        "When the account-level maintenance ratio falls below 130%, the broker notifies you to top up; if you have not topped up within 2 business days of the notice and the ratio is still below the threshold on the deadline, the broker disposes of collateral from the next business day (TWSE margin operating rules Arts. 54–55).",
    "處分所得不足清償借款時，券商會通知你補足差額：本金虧完不代表債務結束（同辦法第 55、81 條）。":
        "If disposal proceeds do not repay the loan, the broker asks you to pay the difference: losing your principal does not end the debt (same rules, Arts. 55 and 81).",
    # --- 報告
    "1. 模擬情境摘要": "1. Scenario summary", "10. 契約注意事項": "10. Contract notes", "11. 尚待確認的資訊": "11. Information still to confirm",
    "12. 官方資料來源": "12. Official data sources", "13. 計算假設": "13. Calculation assumptions", "14. 分析限制": "14. Limitations",
    "2–5. 交易金額、自備資金、融資借款與模擬損益": "2–5. Trade value, own funds, margin loan and simulated P&L", "2–5. 交易金額與損益": "2–5. Trade value and P&L",
    "6. 交割資金缺口": "6. Settlement funding gap", "6. 擔保維持率": "6. Maintenance ratio", "7. 可能發生的法律事件": "7. Possible legal events",
    "8. 投資人權利": "8. Investor rights", "9. 投資人義務": "9. Investor obligations", "個人金融法律風險報告（投資人版）": "Personal financial-legal risk report (investor edition)",
    "報告編號": "Report number", "審查狀態": "Review status", "未使用生成式 AI": "No generative AI used",
    "未經具金融法律專業人員審查（pending_professional_review）": "Not reviewed by a financial-law professional (pending_professional_review)",
    "未經專業審查": "Not professionally reviewed", "未經專業審查｜NOT PROFESSIONALLY REVIEWED": "NOT PROFESSIONALLY REVIEWED",
    "本次分析未連結契約；實際比率、期限與處分方式以你和券商簽訂的契約為準。": "No contract was linked to this analysis; actual ratios, deadlines and disposal methods follow your contract with the broker.",
    "模型": "Model", "模擬情境（非真實帳戶、非投資建議）": "Simulated scenario (not a real account, not investment advice)",
    "模擬股價 vs. 擔保維持率（%）；紅色虛線為 130% 追繳門檻": "Simulated price vs. maintenance ratio (%); the red dashed line is the 130% call threshold",
    "法源版本": "Legal source version", "無": "None", "產生時間": "Generated at", "規則版本": "Rule version", "計算版本": "Calculation version",
    "資料性質": "Nature of data", "金融法律風險報告（專業版）": "Financial-legal risk report (professional edition)",
    # --- 契約服務
    "PDF 沒有文字層（可能是掃描檔），目前未啟用 OCR，無法擷取條款": "The PDF has no text layer (it may be a scan) and OCR is not enabled, so clauses cannot be extracted",
    "圖片需要 OCR／視覺模型才能擷取文字，目前未啟用；請改上傳有文字層的 PDF 或貼上文字": "Images need OCR or a vision model, which is not enabled; please upload a PDF with a text layer or paste the text",
    "文件中未找到相關條款": "No relevant clause found in the document", "文件超過 60 頁，只分析前 60 頁": "The document exceeds 60 pages; only the first 60 are analysed",
    # --- 規則：權利、義務、證據、例外
    "收到通知後在期限內補繳，可避免擔保品被處分": "Topping up within the deadline after the notice avoids collateral disposal",
    "在期限內補繳差額，或以規定的有價證券抵繳": "Top up the shortfall within the deadline, or provide eligible securities as substitute collateral",
    "逐日計算維持率，低於門檻時應即通知委託人": "Calculate the ratio daily and notify the client immediately when it falls below the threshold",
    "券商的追繳通知（含送達時間）": "The broker's margin call notice (with delivery time)", "當日對帳單或維持率紀錄": "That day's statement or ratio record",
    "期限內補足可避免處分": "Topping up within the deadline avoids disposal", "於期限內補繳差額": "Top up the shortfall within the deadline",
    "通知送達日期與方式的紀錄": "Record of the notice delivery date and method", "補足差額或維持率回升後，追繳紀錄取消": "The margin call is cancelled once you top up or the ratio recovers",
    "補繳款項入帳紀錄": "Record of the top-up payment", "處分後如有溢額，應發還給你": "Any surplus after disposal must be returned to you",
    "承擔處分後仍不足清償的債務": "Bear any debt still unpaid after disposal", "處分擔保品以清償債務": "Dispose of collateral to repay the debt",
    "依規定方式處分擔保品": "Dispose of collateral in the prescribed way", "處分成交明細": "Disposal trade details", "處分通知": "Disposal notice",
    "雙方另有約定者，依約定（第 55 條、管理辦法第 18 條但書）": "Where the parties agree otherwise, the agreement applies (Art. 55; proviso to Art. 18 of the Regulations)",
    "持續注意維持率，再度不足時須當日補繳": "Keep watching the ratio; if it falls short again you must top up that day",
    "維持率再度不足時，自次一營業日起處分": "If the ratio falls short again, dispose from the next business day", "每日維持率紀錄": "Daily ratio records",
    "取回處分後的溢額": "Receive the surplus after disposal", "發還溢額": "Return the surplus", "處分結算明細": "Disposal settlement details",
    "取得處分結算明細": "Obtain disposal settlement details", "於次一營業日補足剩餘差額": "Pay the remaining shortfall by the next business day",
    "以帳戶內其他款項抵充": "Offset with other funds in the account", "通知委託人補足": "Notify the client to pay the shortfall", "補足通知": "Shortfall notice",
    "補足差額": "Pay the shortfall", "每日委託處分紀錄": "Daily disposal order records",
    "對處分與結算有疑義時，可依金融消費爭議程序申訴": "If you dispute the disposal or settlement, you can complain through the financial consumer dispute process",
    "於限期內清償債務": "Repay the debt by the deadline", "註銷信用帳戶": "Close the credit account",
    "逾期未清償時向證交所或櫃買中心申報違約": "Report a default to TWSE or TPEx if repayment is overdue", "限期清償通知": "Repayment deadline notice", "結算明細": "Settlement details",
    "雙方另有約定者，依約定（第 81 條但書）": "Where the parties agree otherwise, the agreement applies (proviso to Art. 81)",
    "取得並了解契約中載明的比率、補繳期限與處分方式": "Obtain and understand the ratios, top-up deadline and disposal method stated in the contract",
    "遵守契約約定": "Comply with the contract", "於契約載明比率、補繳期限與處分方式": "State the ratios, top-up deadline and disposal method in the contract",
    "融資融券契約": "Margin purchase and short sale contract", "證券商自行買賣適用期間自 2018-04-28 起": "For securities firms' proprietary trading, applies from 2018-04-28",
    "相同數量部分只需交割差價": "Matching quantities settle only the price difference", "負擔差價損失與手續費、稅": "Bear price-difference losses, fees and tax",
    "成交回報與對帳單": "Trade confirmations and statements", "已開立信用交易帳戶者、專業機構投資人等不在此限": "Does not apply to holders of credit trading accounts, professional institutional investors, etc.",
    "成交當日下午六時前申報當沖數額": "Report day-trade quantities by 6 p.m. on the trade date", "成交回報、對帳單上的沖銷註記": "Offset marks on trade confirmations and statements",
    "取得未沖銷部分的股票": "Receive the shares for the non-offset portion", "交割未沖銷部分的全額價金與手續費": "Settle the full price and fees for the non-offset portion",
    "對帳單（未沖銷股數、應付金額）": "Statement (non-offset shares, amount payable)", "負擔借券費、強制買回價差與相關費用": "Bear borrowing fees, the forced buy-in price difference and related costs",
    "以應付當日沖銷券差專戶強制買回": "Force a buy-in through the day-trade shortfall account", "確認券源、辦理借券與強制買回": "Source shares, arrange borrowing and the forced buy-in",
    "借券與強制買回明細": "Borrowing and forced buy-in details", "取得借券與買回費用明細": "Obtain details of borrowing and buy-in costs",
    "期限內清償強制買回價差與費用": "Pay the forced buy-in difference and costs by the deadline", "逾期未清償視為違約": "Late payment is treated as a default",
    "費用明細": "Cost details", "於交割日前備妥款項": "Have funds ready before the settlement date", "對帳單上的交割日": "Settlement date on the statement",
    "交割日前補足款項": "Top up before the settlement date", "銀行交割帳戶餘額": "Settlement bank account balance", "向券商申訴": "Complain to the broker",
    "向爭議處理機構申請評議": "Apply to the dispute resolution body for mediation", "收受申訴後 30 日內處理並回覆": "Handle and reply within 30 days of receiving a complaint",
    "通知、對帳單、處分明細、往來紀錄": "Notices, statements, disposal details, correspondence",
    "是否屬於金融消費者與金融消費爭議，依金融消費者保護法定義判斷": "Whether you are a financial consumer with a financial consumer dispute follows the Financial Consumer Protection Act definitions",
    # --- 法規名稱與主管機關
    "證券交易法": "Securities and Exchange Act", "證券交易稅條例": "Securities Transaction Tax Act", "金融消費者保護法": "Financial Consumer Protection Act",
    "證券金融事業管理規則": "Regulations Governing Securities Finance Enterprises",
    "有價證券得為融資融券標準": "Criteria Governing Securities Eligible for Margin Purchase and Short Sale",
    "證券商辦理有價證券買賣融資融券管理辦法": "Regulations Governing Margin Purchase and Short Sale by Securities Firms",
    "證券商辦理有價證券買賣融資融券業務操作辦法": "TWSE Operating Rules for Securities Firms Handling Margin Purchase and Short Sale",
    "有價證券當日沖銷交易作業辦法": "TWSE Operating Rules for Day Trading of Securities",
    "財政部": "Ministry of Finance", "金融監督管理委員會": "Financial Supervisory Commission", "臺灣證券交易所": "Taiwan Stock Exchange",
    "臺灣證券交易所法規分享知識庫": "TWSE Regulations Knowledge Base",
}

# ---------------------------------------------------------------- 含變數的樣板（{} 為變數，依序對應 {0} {1}…）
PATTERNS: list[tuple[str, str]] = [
    ("資產：{}（模擬，非真實帳戶）", "Asset: {0} (simulated, not a real account)"),
    ("手續費率 {}、折扣 {}、最低 {} 元，無條件捨去到元（可調整）", "Fee rate {0}, discount {1}, minimum {2}, rounded down to the dollar (adjustable)"),
    ("融資利息以 {} 天為年基準、持有 {} 天估算", "Margin interest estimated on a {0}-day year for {1} holding days"),
    ("資產：{}（模擬）", "Asset: {0} (simulated)"),
    ("有 {} 股買進未在當日賣出，這部分需以全額價金辦理交割", "{0} shares bought were not sold the same day; that portion must be settled at the full price"),
    ("{}為必填", "{0} is required"), ("{}不能是負數", "{0} cannot be negative"), ("{}必須是整數", "{0} must be an integer"),
    ("{}必須大於 0", "{0} must be greater than 0"), ("{}必須介於 0 與 1 之間（不含）", "{0} must be between 0 and 1 (exclusive)"),
    ("{}必須介於 0 與 {} 之間", "{0} must be between 0 and {1}"),
    ("不支援的數字型別：{}", "Unsupported number type: {0}"), ("不是合法數字：{}", "Not a valid number: {0}"),
    ("以模擬價格 {} 處分擔保品", "Collateral disposed at the simulated price of {0}"), ("使用者補繳 {} 元", "You top up {0}"),
    ("模擬價格 {}（{}）", "Simulated price {0} ({1})"), ("模擬價格 {}", "Simulated price {0}"),("模擬連續 {} 個營業日無法全數成交", "Simulated: not fully filled for {0} consecutive business days"),
    ("維持率 {}% 低於門檻 {}%", "Ratio {0}% below the {1}% threshold"), ("自通知送達日起 {} 個營業日", "{0} business days from notice delivery"),
    ("成交日後第 {} 個營業日", "Business day {0} after the trade date"),
    ("{}：買 {} 股、賣 {} 股", "{0}: bought {1} shares, sold {2} shares"),
    ("{} 股買進未在當日賣出", "{0} shares bought were not sold the same day"), ("{} 股賣出未買回", "{0} shares sold were not bought back"),
    ("例外：{}", "Exception: {0}"), ("規則 {} 目前沒有生效版本，無法提供法律依據", "Rule {0} has no active version, so no legal basis can be given"),
    ("不支援的運算子：{}", "Unsupported operator: {0}"), ("狀態為 {}", "Status is {0}"),
    ("擷取 {} 條條款", "{0} clauses extracted"),
    ("規則 {} 版本 {} 已啟用。舊的計算結果保留不變，可重新計算比較差異。", "Rule {0} version {1} is now active. Earlier results are kept; recalculate to compare."),
    ("偵測到 {} 條條文變動，待人工審查", "{0} article change(s) detected, awaiting manual review"),
    ("{} 版本 {} → {}", "{0} version {1} → {2}"),
    ("{} 失敗：{}", "{0} failed: {1}"), ("{} 完成", "{0} done"), ("{} 開始：{}", "{0} started: {1}"),
    ("{}:{} 產生說明（{} ms）", "{0}:{1} generated the explanation ({2} ms)"),
    ("取出 {} 條相關契約條款", "{0} relevant contract clauses extracted"), ("工作流程失敗：{}", "Workflow failed: {0}"),
    ("檢索到 {} 條相關條文", "{0} relevant articles retrieved"), ("生成式 AI 不可用，改用規則模板：{}", "Generative AI unavailable; using a rule template: {0}"),
    ("最後一個步驟的模擬價格是 {}，擔保維持率約 {}%。融資借款 {} 元。", "The last step's simulated price is {0} and the maintenance ratio is about {1}%. Margin loan: {2}."),
    ("已沖銷 {} 股，淨損益 {} 元；估計交割應付款 {} 元。", "{0} shares offset, net P&L {1}; estimated settlement payable {2}."),
    ("引用 {} 筆，失敗 {} 筆；數字未被修改：{}", "{0} citations, {1} failed; numbers unchanged: {2}"),
    ("規則版本 {}；事件 {} 個", "Rule version {0}; {1} event(s)"), ("計算完成（{}）", "Calculation complete ({0})"),
    ("以目前模擬價格 {} 元為基準上漲 {}%", "Up {1}% from the current simulated price of {0}"),
    ("以目前模擬價格 {} 元為基準下跌 {}%", "Down {1}% from the current simulated price of {0}"),
    ("直接把模擬價格設為 {} 元", "Set the simulated price to {0}"),
    ("{} 個欄位錯誤", "{0} field error(s)"), ("模型輸出連續 {} 次未通過 Schema 驗證", "Model output failed schema validation {0} times in a row"),
    ("無法連線到 Gemini：{}", "Cannot connect to Gemini: {0}"), ("無法連線到本機 Ollama：{}", "Cannot connect to local Ollama: {0}"),
    ("Gemini 回應 {}", "Gemini responded {0}"), ("Ollama 回應 {}", "Ollama responded {0}"),
    ("AI 有 {} 筆引用在文件中找不到，已捨棄", "{0} AI citation(s) were not found in the document and were dropped"),
    ("生成式 AI 不可用，只提供確定性條款切分與分類：{}", "Generative AI unavailable; only deterministic clause splitting and classification are provided: {0}"),
    ("Value error, {}", "Value error, {0}"),
    ("以目前的融資比例 {}，自備 {}%、借款 {}%：股價每下跌 1%，自備本金約減少 {}%（未計費用）。",
     "At the current financing ratio of {0} (own funds {1}%, loan {2}%), each 1% price drop cuts your own funds by about {3}% (before costs)."),
    ("模擬價格 {} 時擔保維持率約 {}%，估計追繳門檻股價約 {}（簡化估算，不是確定的斷頭價）。",
     "At the simulated price of {0}, the maintenance ratio is about {1}% and the estimated call-threshold price is about {2} (a simplified estimate, not a definite liquidation price)."),
    ("第{}條", "Art. {0}"), ("第 {} 條", "Art. {0}"), ("第{}條之{}", "Art. {0}-{1}"),
]


def _compile(zh: str) -> re.Pattern[str]:
    parts = zh.split("{}")
    body = "(.+?)".join(re.escape(p) for p in parts)
    return re.compile(f"^{body}$", re.S)


# 固定文字越長的樣板越具體，先比對；否則「模擬價格 {}」這類短樣板會吃掉整句
_COMPILED = [(_compile(zh), en) for zh, en in sorted(PATTERNS, key=lambda p: -len(p[0].replace("{}", "")))]
_CJK = re.compile(r"[一-鿿]")


def tr(s: str) -> str:
    """翻譯單一字串；找不到對照時原樣傳回。"""
    if not s or not _CJK.search(s):
        return s
    hit = EXACT.get(s) or EXACT.get(s.strip())
    if hit:
        return hit
    for rx, en in _COMPILED:
        m = rx.match(s)
        if m:
            return en.format(*(tr(g) for g in m.groups()))
    if "\n" in s:
        return "\n".join(tr(line) for line in s.split("\n"))
    return s


def translate(obj: Any, _key: str | None = None) -> Any:
    """遞迴翻譯 JSON 結構的字串值與 dict 鍵；SKIP_KEYS 的值保持原文。"""
    if _key in SKIP_KEYS:
        return obj
    if isinstance(obj, str):
        return tr(obj)
    if isinstance(obj, list):
        return [translate(v, _key) for v in obj]
    if isinstance(obj, dict):
        return {(tr(k) if isinstance(k, str) else k): translate(v, k) for k, v in obj.items()}
    return obj


EXACT.update({
    "交割日依證交所營業細則第57條按 T+2 推算，實際收款時間依券商通知": (
        "Settlement date calculated as T+2 under Article 57 of the TWSE Operating Rules; the payment cutoff "
        "follows the broker’s notice"
    ),
    "若交割期限屆至仍未履行交割義務，券商須申報違約並通知委託人": (
        "If settlement obligations remain unfulfilled at the deadline, the broker must report default and "
        "notify the client"
    ),
    "若交割日違約，券商承受的款券至遲於次一營業日在市場委託其他券商處理": (
        "If default occurs on settlement day, the broker must arrange market disposal through another broker "
        "by the next business day"
    ),
    "僅為未如期交割的條件式風險，預估缺口不代表已違約": (
        "Conditional risk if settlement is missed; an estimated gap does not mean default has occurred"
    ),
    "未如期交割：違約申報（條件式）": (
        "Settlement default report (conditional)"
    ),
    "違約承受款券處理期限（條件式）": (
        "Default securities/funds disposal deadline (conditional)"
    ),
    "第91條另有同帳戶同種類同數量證券抵繳、大量違約證券處理及不可歸責於券商的例外，須依實際事實確認": (
        "Article 91 also provides exceptions for offsetting identical securities in the same account, large "
        "default positions and circumstances not attributable to the broker; confirm the actual facts"
    ),
    "例外：第91條另有同帳戶同種類同數量證券抵繳、大量違約證券處理及不可歸責於券商的例外，須依實際事實確認": (
        "Exception: Article 91 includes same-account securities offsets, large default positions and "
        "circumstances not attributable to the broker; confirm the actual facts"
    ),
    "臺灣證券交易所股份有限公司營業細則": (
        "Taiwan Stock Exchange Corporation Operating Rules"
    ),
})


def register_rules(rules: list[dict[str, Any]], english: dict[str, dict[str, str]]) -> None:
    """把規則名稱與白話說明加入對照（由 rules_en.json 提供）。"""
    for r in rules:
        en = english.get(f"{r['rule_id']}@demo" if r.get("is_demo") and f"{r['rule_id']}@demo" in english else r["rule_id"])
        if not en:
            continue
        if r.get("rule_name"):
            EXACT.setdefault(r["rule_name"], en["name"])
        if r.get("plain_language"):
            EXACT.setdefault(r["plain_language"], en["plain"])


def _load_rule_names() -> None:
    root = Path(__file__).resolve().parents[3]
    try:
        rules = json.loads((root / "data" / "rules" / "rules.json").read_text(encoding="utf-8"))["rules"]
        english = json.loads((root / "data" / "i18n" / "rules_en.json").read_text(encoding="utf-8"))["rules"]
    except (OSError, KeyError, ValueError):
        return
    register_rules(rules, english)


_load_rule_names()
