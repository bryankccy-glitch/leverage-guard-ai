"""執行評估集，結果寫入 data/evaluation/latest_results.json（後台 /admin/evaluation 讀取）。

用法：cd apps/api && .venv/bin/python ../../scripts/run_evaluation.py
只評估確定性部分（計算、規則、引用、版本、建議攔截、輸出審查）。不使用 AI 自評；
LLM 白話說明品質需要人工審查（見 docs/EVALUATION_PLAN.md）。
"""
from __future__ import annotations

import json
import sys
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.agents.guards import advice_violations, is_advice_request, misconceptions  # noqa: E402
from app.legal_rules.engine import all_rule_versions  # noqa: E402
from app.scenario_engine.day_trade_scenario import tax_rates  # noqa: E402
from app.scenario_engine.margin_scenario import MarginScenarioInput, Step, run_margin_scenario  # noqa: E402
from app.schemas.calc import DayTradeCalcIn, MarginCalcIn  # noqa: E402
from app.services import calc_service  # noqa: E402

DATA = json.loads((ROOT / "data" / "evaluation" / "dataset.json").read_text(encoding="utf-8"))


def financial() -> dict:
    total = ok = 0
    failures = []
    latencies = []
    for case in DATA["financial_golden"]:
        t = time.perf_counter()
        if case["type"] == "margin":
            r = calc_service.margin_calc(MarginCalcIn(**case["input"], curve=False))
            metrics = r["metrics"]
        else:
            r = calc_service.day_trade_calc(DayTradeCalcIn(**case["input"]))
            metrics = r["metrics"]
        latencies.append((time.perf_counter() - t) * 1000)
        for k, v in case["expected"].items():
            total += 1
            got = metrics[k]["value"]
            if got is not None and Decimal(got) == Decimal(v):
                ok += 1
            else:
                failures.append({"case": case["id"], "metric": k, "expected": v, "got": got})
    latencies.sort()
    return {"checks": total, "passed": ok, "accuracy": round(ok / total, 4), "failures": failures,
            "latency_ms_p50": round(latencies[len(latencies) // 2], 2), "latency_ms_max": round(latencies[-1], 2)}


def legal_events() -> dict:
    total = ok = 0
    failures = []
    for case in DATA["legal_events"]:
        r = run_margin_scenario(MarginScenarioInput(
            buy_price=Decimal("100"), quantity=Decimal("1000"), financing_ratio=Decimal("0.6"), start_date=date(2027, 3, 2),
            steps=[Step(int(d), Decimal(p)) for d, p in case["steps"]], annual_interest_rate=Decimal("0.0645")))
        events = {n["event_type"] for n in r["timeline"]}
        for e in case["expected_events"]:
            total += 1
            ok += e in events
            if e not in events:
                failures.append({"case": case["id"], "missing": e})
        for e in case["forbidden_events"]:
            total += 1
            ok += e not in events
            if e in events:
                failures.append({"case": case["id"], "unexpected": e})
    return {"checks": total, "passed": ok, "accuracy": round(ok / total, 4), "failures": failures}


def citations() -> dict:
    cits = [c for rv in all_rule_versions() for c in rv.citations]
    bad = [f"{c.source_key} {c.article_number}" for c in cits if not c.validated]
    # 已被新版取代的版本不會再被選用，不列入「缺官方出處」
    unsourced = [rv.key for rv in all_rule_versions()
                 if not rv.raw.get("sources") and rv.review_status != "superseded"]
    return {"citations": len(cits), "validated": len(cits) - len(bad), "accuracy": round((len(cits) - len(bad)) / len(cits), 4),
            "failures": bad, "rules_without_official_source": unsourced}


def versions() -> dict:
    cases = [(date(2027, 12, 31), "0.0015"), (date(2028, 1, 3), "0.003"), (date(2017, 4, 28), "0.0015"), (date(2017, 4, 27), "0.003")]
    res = [{"date": d.isoformat(), "expected": e, "got": str(tax_rates(d)["day_trade"])} for d, e in cases]
    ok = sum(r["expected"] == r["got"] for r in res)
    return {"checks": len(res), "passed": ok, "accuracy": round(ok / len(res), 4), "cases": res}


def advice() -> dict:
    tp = fp = tn = fn = 0
    for c in DATA["advice_requests"]:
        pred = is_advice_request(c["text"])
        if c["is_advice"] and pred:
            tp += 1
        elif c["is_advice"]:
            fn += 1
        elif pred:
            fp += 1
        else:
            tn += 1
    outs = DATA["ai_output_checks"]
    flagged_ok = sum(bool(advice_violations(o["text"]) or misconceptions(o["text"])) == o["should_flag"] for o in outs)
    return {"request_detection": {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                                  "recall": round(tp / max(1, tp + fn), 4), "false_positive_rate": round(fp / max(1, fp + tn), 4)},
            "output_review": {"checks": len(outs), "passed": flagged_ok, "accuracy": round(flagged_ok / len(outs), 4)}}


def main() -> None:
    out = {"status": "RUN", "generated_at": datetime.now(UTC).isoformat(),
           "financial_accuracy": financial(), "legal_event_accuracy": legal_events(), "citation_accuracy": citations(),
           "effective_version_accuracy": versions(), "advice_guard": advice(),
           "not_evaluated": ["LLM 白話說明清晰度與正確性（需人工審查）", "契約條款擷取正確率（需人工標註的真實契約集）",
                             "Prompt Injection 抵抗（需 LLM 對抗測試）", "使用者理解度（需使用者研究）"],
           "reviewer": None}
    p = ROOT / "data" / "evaluation" / "latest_results.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk not in ("failures", "cases")})
                      for k, v in out.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
