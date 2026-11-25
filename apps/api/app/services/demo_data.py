"""示範資料：虛構帳戶、部位、情境與一份虛構的融資融券契約 PDF。全部明確標示為示範。"""
from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import text

from ..core.db import one, service_session
from ..security.auth import DEMO_ACCOUNTS

INVESTOR = DEMO_ACCOUNTS[0]["id"]

DEMO_CONTRACT_TEXT = [
    ("【虛構示範文件】示範證券股份有限公司 融資融券契約（示範版）",
     "本文件為 LeverageGuard AI 產品展示用之虛構契約，非任何真實證券商之契約，不具法律效力。"),
    ("第一條 契約目的", "委託人向示範證券股份有限公司（以下簡稱本公司）申請開立信用帳戶，辦理有價證券買賣融資融券，雙方同意遵守本契約及相關法令規章。"),
    ("第二條 融資利率與計息方式", "融資年利率為 6.45%，自融資買進交割日起按日計息，以三百六十五日為一年，未滿一元部分四捨五入。利率調整時，本公司應於調整前公告並通知委託人。"),
    ("第三條 融資期限", "融資期限為六個月，期限屆滿前得依規定申請展延。"),
    ("第四條 擔保維持率", "委託人信用帳戶之整戶擔保維持率低於 130% 時，本公司應即以電話、電子郵件或簡訊通知委託人補繳差額。"),
    ("第五條 補繳期限", "委託人應於通知送達之日起 2 個營業日內補繳融資自備款差額，或以本公司同意之有價證券抵繳。"),
    ("第六條 擔保品處分", "委託人未於期限內補足差額，且期限屆滿當日整戶擔保維持率仍低於 130% 者，本公司得自次一營業日起處分其擔保品。處分後如有溢額應予發還；如不足抵償債務，委託人應於接獲通知之次一營業日補足。"),
    ("第七條 違約金", "委託人違約時，本公司得自違約日起至清償日止，按應補差額乘以融資利率百分之十計收違約金。"),
    ("第八條 費用負擔", "委託人應負擔買賣手續費、證券交易稅、融資利息及處分擔保品所生之一切費用。"),
    ("第九條 個人資料", "委託人同意本公司於辦理本契約業務之必要範圍內蒐集、處理及利用其個人資料。"),
    ("第十條 爭議處理", "雙方因本契約發生爭議時，委託人得先向本公司申訴；未獲妥適處理者，得向財團法人金融消費評議中心申請評議。"),
]


def demo_contract_pdf() -> bytes:
    """用 PyMuPDF 產生虛構示範契約 PDF（嵌入 CJK 字型，文字可正確擷取）。"""
    import pymupdf

    doc = pymupdf.open()
    font = pymupdf.Font("cjk")
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="cjk", fontbuffer=font.buffer)
    y = 60
    for title, body in DEMO_CONTRACT_TEXT:
        for content, size in ((title, 12.5), (body, 10.5)):
            rect = pymupdf.Rect(56, y, 540, y + 200)
            rc = page.insert_textbox(rect, content, fontname="cjk", fontsize=size, lineheight=1.5)
            used = 200 - rc if rc >= 0 else 200
            y += used + 6
            if y > 760:
                page = doc.new_page(width=595, height=842)
                page.insert_font(fontname="cjk", fontbuffer=font.buffer)
                y = 60
        y += 6
    doc.set_metadata({"title": "虛構示範融資融券契約（LeverageGuard AI 展示用，非真實券商契約）"})
    doc.subset_fonts()
    data = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return data


def seed_demo_content() -> dict[str, int]:
    out = {"accounts": 0, "scenarios": 0, "contracts": 0}
    with service_session() as conn:
        if not one(conn, "select id from virtual_accounts where user_id = :u", u=INVESTOR):
            acc = one(conn, """insert into virtual_accounts (user_id, name, account_type, cash_balance)
                               values (:u, '示範融資帳戶（模擬）', 'margin', 50000) returning id""", u=INVESTOR)
            for label, q, p, sp, ratio in (("示範股票 A（虛構）", 1000, 100, 100, "0.6"),
                                           ("示範股票 B（虛構）", 2000, 45, 41, "0.6")):
                conn.execute(text("""insert into virtual_positions (account_id, asset_label, trading_type, quantity, entry_price,
                                     simulated_price, financing_principal, financing_ratio, interest_rate)
                                     values (:a, :l, 'margin', :q, :p, :sp, :fp, :r, 0.0645)"""),
                             {"a": acc["id"], "l": label, "q": q, "p": p, "sp": sp,
                              "fp": int(q * p * float(ratio)), "r": ratio})
            out["accounts"] = 1
        if not one(conn, "select id from simulation_scenarios where user_id = :u and is_demo", u=INVESTOR):
            start = date.today()
            while start.weekday() >= 5:
                start += timedelta(days=1)
            demo_a = {"asset_label": "示範股票（虛構）", "buy_price": "100", "quantity": "1000", "financing_ratio": "0.6",
                      "annual_interest_rate": "0.0645", "start_date": start.isoformat(),
                      "steps": [{"day": 0, "price": "100", "label": "第一階段"}, {"day": 1, "price": "80", "label": "第二階段"},
                                {"day": 2, "price": "70", "label": "第三階段"}, {"day": 5, "price": "50", "label": "第四階段"}]}
            demo_b = {"asset_label": "示範股票（虛構）", "direction": "buy_first", "buy_price": "100", "buy_quantity": "2000",
                      "sell_price": "102", "sell_quantity": "1000", "trade_date": start.isoformat(),
                      "available_cash": "50000"}
            for name, typ, inp, key in (("示範情境 A：融資追繳與剩餘債務", "margin", demo_a, "demo_a"),
                                        ("示範情境 B：當沖未完成沖銷", "day_trading", demo_b, "demo_b")):
                conn.execute(text("""insert into simulation_scenarios (user_id, scenario_name, scenario_type, preset_key,
                                     input_parameters, is_demo) values (:u, :n, :t, :k, cast(:i as jsonb), true)"""),
                             {"u": INVESTOR, "n": name, "t": typ, "k": key, "i": json.dumps(inp, ensure_ascii=False)})
                out["scenarios"] += 1
    return out
