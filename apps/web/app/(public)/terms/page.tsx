import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";
import { Bi } from "@/lib/i18n";

export const metadata: Metadata = { title: "使用條款" };

export default function Page() {
  return (
    <StaticPage title="使用條款" lead="使用本平台前請先閱讀。" titleEn="Terms of use" leadEn="Please read before using this platform.">
      <Bi
        zh={<>
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
        </>}
        en={<>
      <h2>Nature of the service</h2>
      <p>This platform provides simulations and educational information on financial trading risk and legal responsibility. It is not investment advice, does not recommend any security or broker, and is not formal legal advice from a lawyer or professional.</p>
      <h2>Limits of calculations and rules</h2>
      <ul>
        <li>Calculations depend on your inputs and stated assumptions and may be simplified estimates (for example, a single margin position only).</li>
        <li>Legal rules are automatically checked against the official text, but not all have been reviewed by a financial-law professional; unreviewed rules are clearly marked.</li>
        <li>Actual margin calls, disposals, settlement and default determinations follow your broker&apos;s notices, your contract, and the rules of the regulator and exchange.</li>
      </ul>
      <h2>Prohibited uses</h2>
      <ul>
        <li>Using this platform to look for ways to evade settlement, repayment or margin call obligations.</li>
        <li>Uploading other people&apos;s personal data or documents you are not authorised to share.</li>
      </ul>
        </>}
      />
    </StaticPage>
  );
}
