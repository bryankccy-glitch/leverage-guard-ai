import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";

export const metadata: Metadata = { title: "運作原理" };

export default function Page() {
  return (
    <StaticPage title="運作原理" lead="金融計算由程式完成，法律規則由經驗證的規則引擎執行，AI 只負責理解、檢索、解釋與整理。">
      <h2>1. 輸入</h2>
      <p>輸入交易參數（買入價、股數、融資比例、模擬價格、費率），或上傳證券商契約。</p>
      <h2>2. 計算（Financial Engine）</h2>
      <p>後端以 Python Decimal 計算交易金額、融資借款、擔保維持率、補繳差額、交易成本、剩餘債務。前端以 Decimal.js 即時預覽，正式結果以後端為準。每個數字都附公式、輸入與假設。</p>
      <h2>3. 套用法律規則（Regulation-as-Code）</h2>
      <p>官方條文轉成宣告式規則：適用條件、參數、生效期間、觸發事件與例外。每條規則的引用文字會逐字比對官方條文，比對失敗就不能執行；規則經法律審查員核准後才會變成啟用狀態，歷史計算保留當時的規則版本。</p>
      <h2>4. 法律責任時間軸</h2>
      <p>依交易日曆（證交所休市日）與通知送達日推算補繳期限、處分起始日與後續事件。缺少通知日期時不捏造期限，而是標示「需要確認」。</p>
      <h2>5. AI 白話說明（千問 Qwen）</h2>
      <p>AI Agent 讀取已驗證的計算結果與規則，產生白話說明；Review Agent 會檢查是否出現買賣建議、未經驗證的數字或常見概念錯誤，不通過就改用規則模板。每一步都記錄在 Agent 執行紀錄中。</p>
    </StaticPage>
  );
}
