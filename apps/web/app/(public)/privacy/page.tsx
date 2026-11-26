import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";
import { Bi } from "@/lib/i18n";

export const metadata: Metadata = { title: "隱私政策" };

export default function Page() {
  return (
    <StaticPage title="隱私政策" lead="本政策說明原型系統實際如何處理資料。" titleEn="Privacy policy" leadEn="This policy explains how the prototype actually handles data.">
      <Bi
        zh={<>
      <h2>我們蒐集的資料</h2>
      <ul>
        <li>帳號資料：Email、顯示名稱、語言與外觀偏好。</li>
        <li>你建立的虛擬帳戶、模擬情境、報告與 Copilot 對話。</li>
        <li>你上傳的契約檔案（只在你按下分析時處理）。</li>
      </ul>
      <h2>我們不蒐集的資料</h2>
      <ul>
        <li>真實券商帳號密碼、真實交易帳戶資料。</li>
        <li>不需要的個人資料：上傳契約前，系統會提醒你遮罩身分證字號、帳號、地址、電話與簽名；分析時也會自動遮罩常見格式。</li>
      </ul>
      <h2>存取控制</h2>
      <ul>
        <li>私人資料以資料庫 Row Level Security 隔離，只有本人可讀。系統管理員沒有預設讀取權，除非你主動授權且授權有期限，並會留下稽核紀錄。</li>
        <li>契約檔案以有時效的簽名連結下載；私人契約內容不寫入一般系統紀錄。</li>
      </ul>
      <h2>AI 模型</h2>
      <p>預設使用在本機執行的千問（Qwen）模型，資料不會傳送到第三方 AI 服務；若管理者改用雲端模型，需另行告知。</p>
      <h2>刪除</h2>
      <p>你可以刪除上傳的契約（同時刪除檔案與分析結果）並封存模擬情境。</p>
        </>}
        en={<>
      <h2>Data we collect</h2>
      <ul>
        <li>Account data: email, display name, language and appearance preferences.</li>
        <li>The virtual accounts, simulation scenarios, reports and Copilot conversations you create.</li>
        <li>Contract files you upload (processed only when you press analyse).</li>
      </ul>
      <h2>Data we do not collect</h2>
      <ul>
        <li>Real brokerage usernames and passwords, or real trading account data.</li>
        <li>Unneeded personal data: before you upload a contract, the system reminds you to mask ID numbers, account numbers, addresses, phone numbers and signatures, and common formats are also masked automatically during analysis.</li>
      </ul>
      <h2>Access control</h2>
      <ul>
        <li>Private data is isolated with database Row Level Security so only you can read it. System admins have no default read access unless you grant time-limited access, which is audit-logged.</li>
        <li>Contract files are downloaded through time-limited signed links; private contract content is not written to general system logs.</li>
      </ul>
      <h2>AI model</h2>
      <p>By default a Qwen model running locally is used, so data is not sent to third-party AI services. If an administrator switches to a cloud model, users must be told separately.</p>
      <h2>Deletion</h2>
      <p>You can delete uploaded contracts (removing both the file and the analysis) and archive simulation scenarios.</p>
        </>}
      />
    </StaticPage>
  );
}
