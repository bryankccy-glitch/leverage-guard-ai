-- LeverageGuard AI 資料庫結構
-- 金額欄位用 numeric（不用 float）；主要資料表用 UUID；歷史規則與計算紀錄不可覆寫。
create extension if not exists pgcrypto;
create extension if not exists pg_trgm;
create extension if not exists vector;
create schema if not exists app;

create or replace function app.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

create or replace function app.immutable_row() returns trigger language plpgsql as $$
begin raise exception '% is append-only', tg_table_name; end $$;

-- ───────── 使用者 ─────────
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text not null check (length(display_name) between 1 and 80),
  role text not null default 'investor' check (role in ('investor','legal_reviewer','system_admin')),
  preferred_language text not null default 'zh-TW' check (preferred_language in ('zh-TW','en')),
  theme text not null default 'light' check (theme in ('light','dark','system')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ───────── 金融法律數位分身（全部是模擬資料） ─────────
create table virtual_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  name text not null check (length(name) between 1 and 80),
  account_type text not null check (account_type in ('cash','margin','day_trading','portfolio')),
  cash_balance numeric(18,2) not null default 0 check (cash_balance >= 0),
  currency text not null default 'TWD' check (currency = 'TWD'),
  broker_contract_id uuid,
  is_simulation boolean not null default true check (is_simulation),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index virtual_accounts_user_idx on virtual_accounts(user_id);

create table virtual_positions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references virtual_accounts(id) on delete cascade,
  asset_label text not null check (length(asset_label) between 1 and 60),
  trading_type text not null check (trading_type in ('cash','margin','day_trading')),
  quantity numeric(18,0) not null check (quantity > 0),
  entry_price numeric(18,4) not null check (entry_price > 0),
  simulated_price numeric(18,4) not null check (simulated_price > 0),
  financing_principal numeric(18,2) not null default 0 check (financing_principal >= 0),
  financing_ratio numeric(6,4) check (financing_ratio > 0 and financing_ratio < 1),
  interest_rate numeric(8,6) check (interest_rate >= 0 and interest_rate <= 0.5),
  trading_date date not null default current_date,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index virtual_positions_account_idx on virtual_positions(account_id);

create table collateral_assets (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references virtual_accounts(id) on delete cascade,
  asset_type text not null,
  quantity numeric(18,4) not null check (quantity > 0),
  valuation numeric(18,2) not null check (valuation >= 0),
  applicable_haircut numeric(5,4) check (applicable_haircut > 0 and applicable_haircut <= 1),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ───────── 法規知識庫（公開資料） ─────────
create table legal_documents (
  id uuid primary key default gen_random_uuid(),
  source_key text not null unique,
  official_title text not null,
  authority text not null,
  source_type text not null check (source_type in ('statute','regulation','exchange_rule','contract','interpretation')),
  publisher text,
  jurisdiction text not null default 'TW',
  market text,
  trading_types text[] not null default '{}',
  official_url text not null,
  publication_date date,
  effective_date date,
  legal_status text not null default 'current' check (legal_status in ('current','draft','promulgated_not_effective','repealed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table legal_document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references legal_documents(id) on delete cascade,
  version text not null,
  effective_from date,
  effective_to date,
  content_hash text not null,
  source_content jsonb not null,
  retrieved_at timestamptz not null,
  is_current boolean not null default true,
  created_at timestamptz not null default now(),
  unique (document_id, version)
);

create table legal_articles (
  id uuid primary key default gen_random_uuid(),
  document_version_id uuid not null references legal_document_versions(id) on delete cascade,
  article_number text not null,
  sort_order integer not null,
  chapter text,
  article_content text not null,
  parent_article_id uuid references legal_articles(id),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique (document_version_id, article_number)
);
create index legal_articles_trgm on legal_articles using gin (article_content gin_trgm_ops);

create table legal_chunks (
  id uuid primary key default gen_random_uuid(),
  article_id uuid not null references legal_articles(id) on delete cascade,
  chunk_index integer not null default 0,
  chunk_text text not null,
  embedding vector(1024),
  embedding_model text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique (article_id, chunk_index)
);
create index legal_chunks_trgm on legal_chunks using gin (chunk_text gin_trgm_ops);
create index legal_chunks_hnsw on legal_chunks using hnsw (embedding vector_cosine_ops);

-- ───────── 規則（Regulation-as-Code） ─────────
create table legal_rules (
  id uuid primary key default gen_random_uuid(),
  rule_key text not null unique,
  rule_name text not null,
  rule_type text not null,
  jurisdiction text not null default 'TW',
  market text,
  trading_type text not null,
  source_article_id uuid references legal_articles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table legal_rule_versions (
  id uuid primary key default gen_random_uuid(),
  rule_id uuid not null references legal_rules(id) on delete cascade,
  version text not null,
  rule_definition jsonb not null,
  effective_from date,
  effective_to date,
  review_status text not null default 'pending_review'
    check (review_status in ('draft','pending_review','approved','active','superseded','suspended')),
  citation_validated boolean not null default false,
  reviewed_by uuid references profiles(id),
  approved_at timestamptz,
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (rule_id, version)
);

-- 規則定義寫入後不可修改（只能改審查狀態）：新規則要建新版本
create or replace function app.protect_rule_definition() returns trigger language plpgsql as $$
begin
  if new.rule_definition is distinct from old.rule_definition or new.version is distinct from old.version
     or new.effective_from is distinct from old.effective_from or new.effective_to is distinct from old.effective_to then
    raise exception 'rule definition is immutable; create a new version';
  end if;
  return new;
end $$;
create trigger legal_rule_versions_immutable before update on legal_rule_versions
  for each row execute function app.protect_rule_definition();

create table rule_test_cases (
  id uuid primary key default gen_random_uuid(),
  rule_version_id uuid not null references legal_rule_versions(id) on delete cascade,
  input_parameters jsonb not null,
  expected_result jsonb not null,
  actual_result jsonb,
  test_status text not null default 'not_run' check (test_status in ('not_run','passed','failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table regulatory_updates (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references legal_documents(id) on delete set null,
  previous_version_id uuid references legal_document_versions(id),
  new_version_id uuid references legal_document_versions(id),
  title text not null,
  authority text not null,
  official_url text,
  change_summary text,
  changed_articles jsonb not null default '[]',
  diff jsonb not null default '[]',
  affected_trading_types text[] not null default '{}',
  impact_analysis jsonb not null default '{}',
  draft_rule_version_id uuid references legal_rule_versions(id),
  publication_date date,
  effective_date date,
  is_demo boolean not null default false,
  review_status text not null default 'pending_review'
    check (review_status in ('pending_review','approved','rejected','published')),
  detected_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ───────── 模擬 ─────────
create table simulation_scenarios (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  account_id uuid references virtual_accounts(id) on delete set null,
  scenario_name text not null check (length(scenario_name) between 1 and 120),
  scenario_type text not null check (scenario_type in ('margin','day_trading','extreme','portfolio')),
  preset_key text,
  input_parameters jsonb not null,
  rule_version_label text,
  status text not null default 'draft' check (status in ('draft','calculated','failed','archived')),
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index simulation_scenarios_user_idx on simulation_scenarios(user_id, created_at desc);

create table scenario_steps (
  id uuid primary key default gen_random_uuid(),
  scenario_id uuid not null references simulation_scenarios(id) on delete cascade,
  step_number integer not null,
  event_type text not null,
  event_parameters jsonb not null default '{}',
  simulated_at date,
  unique (scenario_id, step_number)
);

create table simulation_results (
  id uuid primary key default gen_random_uuid(),
  scenario_id uuid not null references simulation_scenarios(id) on delete cascade,
  calculation_version text not null,
  rule_version_label text not null,
  rule_versions jsonb not null,
  input_hash text not null,
  financial_result jsonb not null,
  legal_result jsonb not null,
  assumptions jsonb not null default '[]',
  warnings jsonb not null default '[]',
  created_at timestamptz not null default now()
);
create index simulation_results_scenario_idx on simulation_results(scenario_id, created_at desc);
-- 歷史計算結果不可覆寫
create trigger simulation_results_append_only before update on simulation_results
  for each row execute function app.immutable_row();

create table calculation_snapshots (
  id uuid primary key default gen_random_uuid(),
  simulation_result_id uuid not null references simulation_results(id) on delete cascade,
  step_number integer not null,
  input_hash text not null,
  financial_state jsonb not null,
  legal_state jsonb not null,
  calculation_trace jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table legal_events (
  id uuid primary key default gen_random_uuid(),
  simulation_result_id uuid not null references simulation_results(id) on delete cascade,
  rule_key text,
  event_type text not null,
  trigger_condition text,
  event_status text not null check (event_status in ('not_triggered','potential','triggered_in_simulation','requires_confirmation','resolved')),
  event_date date,
  legal_basis jsonb not null default '[]',
  missing_facts jsonb not null default '[]',
  created_at timestamptz not null default now()
);

-- ───────── 契約 ─────────
create table contracts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  document_name text not null,
  document_type text,
  broker_name text,
  storage_path text not null,
  mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0),
  document_hash text not null check (document_hash ~ '^[0-9a-f]{64}$'),
  page_count integer,
  is_demo boolean not null default false,
  status text not null default 'uploaded' check (status in ('uploaded','analyzing','analyzed','failed')),
  uploaded_at timestamptz not null default now(),
  deletion_requested_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index contracts_user_idx on contracts(user_id, uploaded_at desc);

create table contract_clauses (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references contracts(id) on delete cascade,
  clause_number text,
  page_number integer,
  char_start integer,
  char_end integer,
  original_text text not null,
  category text not null,
  extracted_parameters jsonb not null default '{}',
  verification_status text not null default 'extracted'
    check (verification_status in ('extracted','verified_in_document','not_found','needs_review')),
  created_at timestamptz not null default now()
);

create table contract_analyses (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references contracts(id) on delete cascade,
  analysis_result jsonb not null,
  provider text not null,
  model_version text,
  review_status text not null default 'pending_professional_review',
  created_at timestamptz not null default now()
);

-- 管理員要讀私人契約必須有明確授權與紀錄
create table contract_access_grants (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references contracts(id) on delete cascade,
  granted_by uuid not null references profiles(id),
  grantee_id uuid not null references profiles(id),
  purpose text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table legal_citations (
  id uuid primary key default gen_random_uuid(),
  simulation_result_id uuid references simulation_results(id) on delete cascade,
  contract_analysis_id uuid references contract_analyses(id) on delete cascade,
  legal_article_id uuid references legal_articles(id),
  quoted_text text not null,
  applicability text,
  validation_status text not null check (validation_status in ('validated','failed','insufficient_legal_evidence')),
  created_at timestamptz not null default now()
);

-- ───────── Agent ─────────
create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  scenario_id uuid references simulation_scenarios(id) on delete set null,
  contract_id uuid references contracts(id) on delete set null,
  workflow_name text not null,
  input_hash text,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled')),
  started_at timestamptz,
  completed_at timestamptz,
  total_tokens integer not null default 0,
  estimated_cost numeric(12,6) not null default 0,
  provider text,
  model text,
  output jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index agent_runs_user_idx on agent_runs(user_id, created_at desc);
create index agent_runs_cache_idx on agent_runs(input_hash) where status = 'completed';

create table agent_tasks (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid not null references agent_runs(id) on delete cascade,
  agent_name text not null,
  task_type text not null,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','skipped','cancelled')),
  depends_on text[] not null default '{}',
  input_reference text,
  output_reference text,
  output_summary text,
  tool_calls jsonb not null default '[]',
  retrieved_sources jsonb not null default '[]',
  validation_result jsonb,
  tokens integer not null default 0,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  duration_ms integer,
  created_at timestamptz not null default now()
);

create table agent_events (
  id bigserial primary key,
  agent_run_id uuid not null references agent_runs(id) on delete cascade,
  seq integer not null,
  agent_name text not null,
  status text not null,
  message text not null,
  created_at timestamptz not null default now(),
  unique (agent_run_id, seq)
);

create table copilot_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  scenario_id uuid references simulation_scenarios(id) on delete set null,
  role text not null check (role in ('user','assistant')),
  content text not null,
  payload jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- ───────── 報告、通知、審查、稽核 ─────────
create table reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  scenario_id uuid references simulation_scenarios(id) on delete set null,
  simulation_result_id uuid references simulation_results(id) on delete set null,
  report_number text not null unique default ('LG-' || upper(substr(replace(gen_random_uuid()::text,'-',''),1,10))),
  report_type text not null check (report_type in ('investor','professional')),
  report_content jsonb not null,
  calculation_version text not null,
  rule_version text not null,
  legal_source_version text not null,
  model_version text,
  review_status text not null default 'pending_professional_review'
    check (review_status in ('pending_professional_review','reviewed')),
  created_at timestamptz not null default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  notification_type text not null check (notification_type in ('regulatory_update','saved_scenario_rule_changed',
    'contract_analysis_completed','report_generated','agent_task_completed','rule_review_required')),
  category text not null default 'system' check (category in ('simulation','real_regulation','pending_regulation','system')),
  title text not null,
  message text not null,
  resource_type text,
  resource_id uuid,
  dedupe_key text,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, dedupe_key)
);
create index notifications_user_idx on notifications(user_id, created_at desc);

create table notification_subscriptions (
  user_id uuid not null references profiles(id) on delete cascade,
  topic text not null check (topic in ('margin_rules','day_trading_rules','legal_document','saved_scenario_rules')),
  target text not null default '*',
  digest boolean not null default false,
  created_at timestamptz not null default now(),
  primary key (user_id, topic, target)
);

create table reviews (
  id uuid primary key default gen_random_uuid(),
  reviewer_id uuid not null references profiles(id),
  resource_type text not null check (resource_type in ('rule_version','regulatory_update','report','citation')),
  resource_id uuid not null,
  decision text not null check (decision in ('approve','reject','request_changes','activate','suspend')),
  notes text not null default '',
  reviewed_at timestamptz not null default now()
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references profiles(id) on delete set null,
  actor_type text not null default 'user' check (actor_type in ('user','agent','system','guest')),
  action text not null,
  resource_type text not null,
  resource_id uuid,
  metadata jsonb not null default '{}',
  request_id text,
  created_at timestamptz not null default now()
);
create index audit_logs_actor_idx on audit_logs(actor_id, created_at desc);
create trigger audit_logs_append_only before update or delete on audit_logs
  for each row execute function app.immutable_row();

create table jobs (
  id uuid primary key default gen_random_uuid(),
  kind text not null,
  payload jsonb not null default '{}',
  idempotency_key text unique,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','dead')),
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  run_after timestamptz not null default now(),
  locked_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index jobs_ready_idx on jobs(status, run_after) where status = 'queued';

do $$ declare t text; begin
  for t in select table_name from information_schema.columns
           where table_schema = 'public' and column_name = 'updated_at' loop
    execute format('create trigger %I_touch before update on public.%I for each row execute function app.touch_updated_at()', t, t);
  end loop;
end $$;
