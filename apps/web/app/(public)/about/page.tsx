import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";

export const metadata: Metadata = { title: "關於" };

export default function Page() {
  return (
    <StaticPage title="關於 LeverageGuard AI" lead="AI 金融交易風險與法律責任情境模擬平台：在承擔交易風險之前，先理解可能的財務損失、契約責任與投資人權益。">
      <h2>我們要解決的問題</h2>
      <ul>
        <li>知道融資能放大購買力，卻不清楚虧損也會被放大。</li>
        <li>不清楚擔保維持率怎麼算、追繳門檻、補繳期限與擔保品處分的差別。</li>
        <li>誤以為本金虧完就不需要承擔其他債務。</li>
        <li>不了解當沖未完成沖銷時的交割責任。</li>
        <li>一般金融計算機只有數字，沒有法律後果；一般聊天機器人可能給出錯誤公式或不存在的條文。</li>
      </ul>
      <h2>我們不做的事</h2>
      <ul>
        <li>不推薦股票、不提供進出場訊號、不預測股價、不建議槓桿比例。</li>
        <li>不連接真實券商帳戶、不下單、不儲存券商帳密。</li>
        <li>不把 AI 生成內容當作正式法律意見。</li>
      </ul>
      <h2>目前狀態</h2>
      <p>這是黑客松與研究用的產品原型。目標使用者包括投資人、證券商法遵與客服部門、金融法律專業人士；本平台尚未被任何證券商、政府機關或法律機構採用。</p>
    </StaticPage>
  );
}
