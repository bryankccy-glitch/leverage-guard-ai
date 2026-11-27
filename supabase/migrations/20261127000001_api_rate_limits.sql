-- 跨伺服器實例共用的 API 限流計數（Vercel serverless 會同時開多個實例，記憶體計數無法共用）。
-- 只由後端以資料庫擁有者身分存取；不開放給 anon／authenticated。
create table if not exists public.api_rate_limits (
  bucket text not null,              -- 來源 IP＋授權標頭雜湊（不存原始 token）
  window_start timestamptz not null, -- 以分鐘為單位的計數視窗
  hits integer not null default 0,
  primary key (bucket, window_start)
);

create index if not exists api_rate_limits_window_idx on public.api_rate_limits (window_start);

alter table public.api_rate_limits enable row level security;
revoke all on public.api_rate_limits from anon, authenticated;

comment on table public.api_rate_limits is '後端限流計數；保留約 10 分鐘，由後端定期清除。';
