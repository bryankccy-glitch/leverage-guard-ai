/** 原創 Logo：盾牌（保護）＋上升後回落的金融曲線＋天平橫桿（法律平衡）。純幾何線條，可用於 App Icon／Favicon。 */
export function LogoMark({ size = 32, mono = false, className }: { size?: number; mono?: boolean; className?: string }) {
  const stroke = mono ? "currentColor" : "var(--brand)";
  const fill = mono ? "none" : "var(--brand-soft)";
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="LeverageGuard AI" className={className}>
      <path d="M16 2.5 4.5 6.8v8.4c0 7.3 4.9 12.4 11.5 14.3 6.6-1.9 11.5-7 11.5-14.3V6.8L16 2.5Z" fill={fill} stroke={stroke} strokeWidth="2" strokeLinejoin="round" />
      <path d="M9 18.5 13 14l3.2 3 6.8-7" fill="none" stroke={stroke} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 22.5h12M16 20.5v4" stroke={mono ? "currentColor" : "var(--text)"} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function LogoHorizontal({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark size={30} />
      <span className="text-[17px] font-bold tracking-tight text-ink">
        LeverageGuard<span className="text-brand"> AI</span>
      </span>
    </span>
  );
}
