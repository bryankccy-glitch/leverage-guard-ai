import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";

export const metadata: Metadata = { title: "使用條款" };

export default function Page() {
  return (
    <StaticPage title="使用條款" lead="使用本平台前請先閱讀。">
      <h2>性質</h2>
      <p>本平台提供金融交易風險與法律責任的模擬與教育資訊，不構成投資建議、不推薦任何證券或證券商，也不是律師或專業人員的正式法律意見。</p>
      <h2>計算與規則的限制</h2>
      <ul>
        <li>計算以使用者輸入與明示假設為準，可能為簡化估算（例如僅單一融資部位）。</li>
        <li>法律規則已自動比對官方原文，但未必全部經過具金融法律專業的人員審查；未審查的規則會清楚標示。</li>
        <li>實際的追繳、處分、交割與違約認定，以證券商通知、契約與主管機關、交易所規定為準。</li>
      </ul>
      <h2>禁止的使用方式</h2>
      <ul>
        <li>利用本平台尋求規避交割、清償或追繳義務的方法。</li>
        <li>上傳他人個人資料或未經授權的文件。</li>
      </ul>
    </StaticPage>
  );
}
