import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";

export const metadata: Metadata = { title: "隱私政策" };

export default function Page() {
  return (
    <StaticPage title="隱私政策" lead="本政策說明原型系統實際如何處理資料。">
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
    </StaticPage>
  );
}
