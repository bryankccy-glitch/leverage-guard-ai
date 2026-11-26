"""個人風險報告：投資人版與專業版。內容全部來自已驗證的計算結果、規則與檢索條文。

PDF 嵌入 Droid Sans Fallback（Apache 2.0）繁中字型，並以 reportlab 繪製維持率圖表。
"""
from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .. import i18n

WATERMARK = "未經專業審查｜NOT PROFESSIONALLY REVIEWED"


def _metric_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"key": k, "label": m["label"], "value": m["value"], "unit": m["unit"], "formula": m["formula"],
             "simplified": m["simplified"], "note": m.get("note")} for k, m in metrics.items()]


def build(report_type: str, output: dict[str, Any]) -> dict[str, Any]:
    sim = output["simulation"]
    trading_type = sim["trading_type"]
    metrics = sim.get("opening") if trading_type == "margin" else sim.get("metrics")
    last = sim["states"][-1]["metrics"] if trading_type == "margin" else metrics
    events = [e for e in output["legal_events"] if e["status"] != "not_triggered"]
    citations = {}
    for n in sim["timeline"]:
        for b in n["legal_basis"]:
            citations[f"{b['source_key']}#{b['article_number']}"] = b
    sections: list[dict[str, Any]] = []

    def add(key: str, title: str, body: Any) -> None:
        sections.append({"key": key, "title": title, "body": body})

    if report_type == "investor":
        add("summary", "1. 模擬情境摘要", output["summary"] + "\n" + output["financial_explanation"]["summary"])
        if trading_type == "margin":
            add("amounts", "2–5. 交易金額、自備資金、融資借款與模擬損益", _metric_rows(
                {k: metrics[k] for k in ("purchase_value", "own_funds", "financing")} |
                {k: last[k] for k in ("market_value", "gross_pnl", "net_pnl")}))
            add("ratio", "6. 擔保維持率", _metric_rows({k: last[k] for k in ("maintenance_ratio", "threshold_price",
                                                                              "margin_call_amount")}))
        else:
            add("amounts", "2–5. 交易金額與損益", _metric_rows({k: metrics[k] for k in (
                "buy_amount", "sell_amount", "matched_quantity", "unmatched_long", "unmatched_short", "net_pnl")}))
            add("ratio", "6. 交割資金缺口", _metric_rows({k: metrics[k] for k in ("settlement_payable", "funding_gap")}))
        add("events", "7. 可能發生的法律事件", [{"date": e["date"], "title": e["title"], "status": e["status"],
                                              "explanation": e["explanation"]} for e in events])
        add("rights", "8. 投資人權利", [r["description"] for r in output["investor_rights"]])
        add("obligations", "9. 投資人義務", [r["description"] for r in output["investor_obligations"]])
        add("contract", "10. 契約注意事項", [c["original_text"][:300] for c in output["contract_findings"]]
            or ["本次分析未連結契約；實際比率、期限與處分方式以你和券商簽訂的契約為準。"])
        add("pending", "11. 尚待確認的資訊", output["uncertainties"] or ["無"])
        add("sources", "12. 官方資料來源", [f"{c['official_title']} {c['article_number']}（{c['version']}）{c['official_url']}"
                                         for c in citations.values()])
        add("assumptions", "13. 計算假設", output["financial_explanation"]["assumptions"])
        add("limitations", "14. 分析限制", output["limitations"])
    else:
        add("executive", "1. Executive Summary", output["summary"])
        add("inputs", "2. Input Parameters", sim.get("input") or {})
        add("calculation", "3. Financial Calculation", _metric_rows(metrics))
        add("methodology", "4. Calculation Methodology", [f"{m['label']}＝{m['formula']}" for m in metrics.values()])
        add("scenario", "5. Scenario Analysis", [{"date": s.get("date"), "price": s.get("price"),
                                                   "maintenance_ratio_pct": s.get("maintenance_ratio_pct")}
                                                  for s in sim.get("states", [])])
        add("rules", "6. Legal Rule Matching", [{"rule_id": r["rule_id"], "version": r["version"],
                                                 "review_status": r["review_status"], "parameters": r["parameters"]}
                                                for r in sim["rules"]])
        add("citations", "7. Legal Citations", [{"id": k, "title": c["official_title"], "article": c["article_number"],
                                                 "quote": c["quote"], "url": c["official_url"], "version": c["version"],
                                                 "validated": c["validated"]} for k, c in citations.items()])
        add("contract", "8. Contract References", output["contract_findings"])
        add("timeline", "9. Responsibility Timeline", [{"date": e["date"], "title": e["title"], "status": e["status"],
                                                        "trigger": e["trigger_condition"]} for e in output["legal_events"]])
        add("missing", "10. Missing Facts", output["uncertainties"])
        add("version", "11. Regulatory Version", {"rule_version": output["rule_version"],
                                                  "legal_source_version": output["legal_source_version"]})
        add("verification", "12. Verification Results", {"verification": output["verification"],
                                                         "review": output["review"]})
        add("review_status", "13. Review Status", "未經具金融法律專業人員審查（pending_professional_review）")
        add("disclaimer", "14. Disclaimer", output["limitations"])
    return {"report_type": report_type, "trading_type": trading_type, "sections": sections,
            "watermark": WATERMARK, "curve": None,
            "generated_at": datetime.now(UTC).isoformat(), "is_simulation": True}


def to_pdf(report: dict[str, Any], meta: dict[str, Any], curve: list[dict[str, Any]] | None = None) -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from ..core.cjk_font import register_reportlab
    f = register_reportlab()  # 嵌入 Droid Sans Fallback，任何電腦都能正確顯示繁體中文
    navy, teal = colors.HexColor("#10243E"), colors.HexColor("#087F8C")
    st_h1 = ParagraphStyle("h1", fontName=f, fontSize=17, leading=24, textColor=navy)
    st_h2 = ParagraphStyle("h2", fontName=f, fontSize=12.5, leading=19, textColor=teal, spaceBefore=10, spaceAfter=4)
    st_b = ParagraphStyle("b", fontName=f, fontSize=9.5, leading=15)
    st_s = ParagraphStyle("s", fontName=f, fontSize=8, leading=12, textColor=colors.HexColor("#475569"))

    def p(t: Any, s=st_b):  # noqa: ANN001
        return Paragraph(escape(str(t)).replace("\n", "<br/>"), s)

    buf = io.BytesIO()

    def on_page(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        canvas.setFont(f, 8)
        canvas.setFillColor(colors.HexColor("#DC2626"))
        canvas.drawString(40, A4[1] - 28, WATERMARK)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(A4[0] - 40, 24, (f"LeverageGuard AI | {meta['report_number']} | page {doc.page}" if i18n.is_en() else f"LeverageGuard AI｜{meta['report_number']}｜第 {doc.page} 頁"))
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=46, bottomMargin=40,
                            title=f"LeverageGuard AI {meta['report_number']}")
    title = i18n.tr("個人金融法律風險報告（投資人版）" if report["report_type"] == "investor" else "金融法律風險報告（專業版）")
    story = [p("LeverageGuard AI", st_s), p(title, st_h1), Spacer(1, 4)]
    info = [["報告編號", meta["report_number"]], ["產生時間", meta["generated_at"]],
            ["計算版本", meta["calculation_version"]], ["規則版本", meta["rule_version"]],
            ["法源版本", meta["legal_source_version"][:90]], ["模型", meta.get("model_version") or "未使用生成式 AI"],
            ["審查狀態", "未經專業審查"], ["資料性質", "模擬情境（非真實帳戶、非投資建議）"]]
    info = i18n.translate(info)
    t = Table([[p(a, st_s), p(b, st_s)] for a, b in info], colWidths=[70, 440])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DCE3EB")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F6"))]))
    story += [t, Spacer(1, 8)]

    if curve:
        d = Drawing(510, 170)
        lp = LinePlot()
        lp.x, lp.y, lp.width, lp.height = 40, 25, 450, 125
        pts = [(float(c["price"]), float(c["maintenance_ratio"])) for c in curve if c.get("maintenance_ratio")]
        lp.data = [pts, [(pts[0][0], 130.0), (pts[-1][0], 130.0)]]
        lp.lines[0].strokeColor, lp.lines[0].strokeWidth = teal, 1.6
        lp.lines[1].strokeColor, lp.lines[1].strokeDashArray = colors.HexColor("#DC2626"), [3, 3]
        lp.xValueAxis.labels.fontName = lp.yValueAxis.labels.fontName = "Helvetica"
        d.add(lp)
        d.add(String(40, 158, i18n.tr("模擬股價 vs. 擔保維持率（%）；紅色虛線為 130% 追繳門檻"), fontName=f, fontSize=8))
        story += [d, Spacer(1, 6)]

    for sec in report["sections"]:
        story.append(p(sec["title"], st_h2))
        body = sec["body"]
        if isinstance(body, str):
            story.append(p(body))
        elif isinstance(body, list) and body and isinstance(body[0], dict):
            keys = list(body[0].keys())[:5]
            data = [[p(k, st_s) for k in keys]] + [[p(r.get(k, ""), st_s) for k in keys] for r in body[:40]]
            tb = Table(data, repeatRows=1)
            tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DCE3EB")),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(tb)
        elif isinstance(body, list):
            for item in body[:40]:
                story.append(p(f"・{item}"))
        else:
            story.append(p(json.dumps(body, ensure_ascii=False, default=str)[:3000], st_s))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def to_csv(report: dict[str, Any]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["section", "label", "value", "unit", "formula"])
    for sec in report["sections"]:
        if isinstance(sec["body"], list):
            for r in sec["body"]:
                if isinstance(r, dict) and "label" in r:
                    w.writerow([sec["title"], r["label"], r.get("value"), r.get("unit"), r.get("formula")])
    return out.getvalue()


def dec_default(o: Any) -> Any:
    return str(o) if isinstance(o, Decimal) else str(o)
