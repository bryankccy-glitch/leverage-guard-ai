/**
 * 前端即時預覽（Decimal.js）：拖動 Slider 時立刻更新數字。
 * 公式與後端 financial_engine/margin.py 相同；正式結果一律以後端計算為準（Source of Truth），
 * 介面會顯示兩者是否一致。
 */
import Decimal from "decimal.js";

export type MarginPreviewInput = {
  buyPrice: string;
  quantity: string;
  financingRatio: string;
  currentPrice: string;
  threshold: string; // 1.30
  otherCollateral?: string;
};

export type MarginPreview = {
  purchaseValue: string;
  financing: string;
  ownFunds: string;
  marketValue: string;
  grossPnl: string;
  ratioPct: string | null;
  thresholdPrice: string | null;
  callAmount: string;
  belowThreshold: boolean;
  equity: string;
};

const D = (v: string | undefined, fallback = "0") => {
  try {
    const d = new Decimal(v && v.trim() !== "" ? v : fallback);
    return d.isFinite() ? d : new Decimal(fallback);
  } catch {
    return new Decimal(fallback);
  }
};

export function marginPreview(i: MarginPreviewInput): MarginPreview | null {
  const p0 = D(i.buyPrice);
  const q = D(i.quantity);
  const f = D(i.financingRatio);
  const pt = D(i.currentPrice);
  const t = D(i.threshold, "1.3");
  const col = D(i.otherCollateral);
  if (p0.lte(0) || q.lte(0) || pt.lte(0) || f.lte(0) || f.gte(1)) return null;
  const purchase = p0.mul(q).toDecimalPlaces(0, Decimal.ROUND_HALF_UP);
  const financing = purchase.mul(f).toDecimalPlaces(0, Decimal.ROUND_DOWN);
  const mv = pt.mul(q).toDecimalPlaces(0, Decimal.ROUND_HALF_UP);
  const ratio = financing.gt(0) ? mv.plus(col).div(financing) : null;
  const below = ratio !== null && ratio.lt(t);
  const call = below ? Decimal.max(0, financing.minus(pt.mul(q).mul(f)).minus(col.mul(f))).toDecimalPlaces(0, Decimal.ROUND_HALF_UP) : new Decimal(0);
  return {
    purchaseValue: purchase.toString(),
    financing: financing.toString(),
    ownFunds: purchase.minus(financing).toString(),
    marketValue: mv.toString(),
    grossPnl: mv.minus(purchase).toString(),
    ratioPct: ratio ? ratio.mul(100).toDecimalPlaces(2, Decimal.ROUND_HALF_UP).toFixed(2) : null,
    thresholdPrice: financing.gt(0) ? Decimal.max(0, financing.mul(t).minus(col).div(q)).toDecimalPlaces(2, Decimal.ROUND_HALF_UP).toFixed(2) : null,
    callAmount: call.toString(),
    belowThreshold: below,
    equity: mv.plus(col).minus(financing).toString(),
  };
}
