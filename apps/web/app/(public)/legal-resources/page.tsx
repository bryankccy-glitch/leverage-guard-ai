import type { Metadata } from "next";
import { StaticPage } from "@/features/landing/StaticPage";
import { Bi } from "@/lib/i18n";

export const metadata: Metadata = { title: "法律資料來源" };

export default function Page() {
  return (
    <StaticPage title="法律資料來源" lead="本平台匯入的官方資料、取得方式與尚未匯入的部分。" titleEn="Legal data sources" leadEn="Official data imported into this platform, how it was obtained, and what has not been imported yet. Legal texts are in Traditional Chinese.">
      <Bi
        zh={<>
      <h2>已匯入（含版本與取得時間）</h2>
      <ul>
        <li>全國法規資料庫開放資料（<a href="https://law.moj.gov.tw/" target="_blank" rel="noopener noreferrer">law.moj.gov.tw</a>）：證券交易法、證券交易稅條例、金融消費者保護法、證券商辦理有價證券買賣融資融券管理辦法、證券金融事業管理規則、有價證券得為融資融券標準。</li>
        <li>臺灣證券交易所法規分享知識庫（<a href="https://twse-regulation.twse.com.tw/" target="_blank" rel="noopener noreferrer">twse-regulation.twse.com.tw</a>）：證券商辦理有價證券買賣融資融券業務操作辦法（115.10.16）、有價證券當日沖銷交易作業辦法（105.02.01）。</li>
        <li>臺灣證券交易所市場開休市日期（目前只公布最新年度）。</li>
      </ul>
      <h2>尚未匯入（相關結果會標示「法律依據待查證」）</h2>
      <ul>
        <li>證交所營業細則中的普通交割期限與違約交割處理條文。</li>
        <li>證券櫃檯買賣中心相關規章。</li>
        <li>各證券商的融資融券契約與受託契約（使用者可自行上傳分析）。</li>
      </ul>
      <h2>官方求助管道</h2>
      <ul>
        <li>財團法人金融消費評議中心：<a href="https://www.foi.org.tw/" target="_blank" rel="noopener noreferrer">www.foi.org.tw</a>（依金融消費者保護法第 13 條，先向金融服務業申訴，30 日內未處理或不接受結果，可於 60 日內申請評議）。</li>
        <li>金融監督管理委員會證券期貨局：<a href="https://www.sfb.gov.tw/" target="_blank" rel="noopener noreferrer">www.sfb.gov.tw</a></li>
      </ul>
        </>}
        en={<>
      <h2>Imported (with version and retrieval time)</h2>
      <ul>
        <li>Laws &amp; Regulations Database open data (<a href="https://law.moj.gov.tw/" target="_blank" rel="noopener noreferrer">law.moj.gov.tw</a>): Securities and Exchange Act, Securities Transaction Tax Act, Financial Consumer Protection Act, Regulations Governing Margin Purchase and Short Sale by Securities Firms, Regulations Governing Securities Finance Enterprises, Criteria Governing Securities Eligible for Margin Purchase and Short Sale.</li>
        <li>TWSE Regulations Knowledge Base (<a href="https://twse-regulation.twse.com.tw/" target="_blank" rel="noopener noreferrer">twse-regulation.twse.com.tw</a>): Operating Rules for Securities Firms Handling Margin Purchase and Short Sale (2026-10-16 version), Operating Rules for Day Trading of Securities (2016-02-01 version).</li>
        <li>TWSE market open and holiday dates (only the latest year is published).</li>
      </ul>
      <h2>Not imported yet (related results are marked &quot;legal basis to be verified&quot;)</h2>
      <ul>
        <li>Regular settlement deadlines and settlement default handling in the TWSE Operating Rules.</li>
        <li>Rules of the Taipei Exchange (TPEx).</li>
        <li>Individual brokers&apos; margin contracts and brokerage agreements (users can upload their own for analysis).</li>
      </ul>
      <h2>Official help channels</h2>
      <ul>
        <li>Financial Ombudsman Institution: <a href="https://www.foi.org.tw/" target="_blank" rel="noopener noreferrer">www.foi.org.tw</a> (under Art. 13 of the Financial Consumer Protection Act, first complain to the financial service provider; if it does not handle it within 30 days or you reject the outcome, you can apply for mediation within 60 days).</li>
        <li>Securities and Futures Bureau, Financial Supervisory Commission: <a href="https://www.sfb.gov.tw/" target="_blank" rel="noopener noreferrer">www.sfb.gov.tw</a></li>
      </ul>
        </>}
      />
    </StaticPage>
  );
}
