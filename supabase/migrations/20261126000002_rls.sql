-- Row Level Security：私人資料只給本人；法規與規則公開可讀；規則審查只給 legal_reviewer。
-- 管理員沒有讀私人契約的特權，除非有未過期的 contract_access_grants。

create or replace function app.my_role() returns text language sql stable security definer set search_path = public as $$
  select coalesce((select role from profiles where id = auth.uid()), 'guest') $$;
create or replace function app.owns_account(a uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from virtual_accounts where id = a and user_id = auth.uid()) $$;
create or replace function app.owns_scenario(s uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from simulation_scenarios where id = s and user_id = auth.uid()) $$;
create or replace function app.owns_result(r uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from simulation_results x join simulation_scenarios s on s.id = x.scenario_id
                 where x.id = r and s.user_id = auth.uid()) $$;
create or replace function app.can_read_contract(c uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from contracts where id = c and user_id = auth.uid())
      or exists (select 1 from contract_access_grants g where g.contract_id = c and g.grantee_id = auth.uid()
                 and g.expires_at > now()) $$;
create or replace function app.owns_run(r uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from agent_runs where id = r and user_id = auth.uid()) $$;

grant usage on schema app to anon, authenticated, service_role;
grant execute on all functions in schema app to anon, authenticated, service_role;

do $$ declare t text; begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('create policy service_all on public.%I for all to service_role using (true) with check (true)', t);
  end loop;
end $$;

grant usage on schema public to anon, authenticated, service_role;
grant select, insert, update, delete on all tables in schema public to authenticated, service_role;
grant usage, select on all sequences in schema public to authenticated, service_role;
grant select on legal_documents, legal_document_versions, legal_articles, legal_chunks, legal_rules,
  legal_rule_versions, rule_test_cases, regulatory_updates to anon;
revoke all on jobs from authenticated, anon;

create policy profiles_self on profiles for select to authenticated using (id = auth.uid());
create policy profiles_self_update on profiles for update to authenticated using (id = auth.uid())
  with check (id = auth.uid() and role = (select p.role from profiles p where p.id = auth.uid()));

create policy accounts_own on virtual_accounts for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy positions_own on virtual_positions for all to authenticated
  using (app.owns_account(account_id)) with check (app.owns_account(account_id));
create policy collateral_own on collateral_assets for all to authenticated
  using (app.owns_account(account_id)) with check (app.owns_account(account_id));

create policy scenarios_own on simulation_scenarios for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy steps_own on scenario_steps for all to authenticated
  using (app.owns_scenario(scenario_id)) with check (app.owns_scenario(scenario_id));
create policy results_read on simulation_results for select to authenticated using (app.owns_scenario(scenario_id));
create policy results_insert on simulation_results for insert to authenticated with check (app.owns_scenario(scenario_id));
create policy results_delete on simulation_results for delete to authenticated using (app.owns_scenario(scenario_id));
create policy snapshots_own on calculation_snapshots for all to authenticated
  using (app.owns_result(simulation_result_id)) with check (app.owns_result(simulation_result_id));
create policy events_own on legal_events for all to authenticated
  using (app.owns_result(simulation_result_id)) with check (app.owns_result(simulation_result_id));

create policy contracts_read on contracts for select to authenticated using (user_id = auth.uid() or app.can_read_contract(id));
create policy contracts_write on contracts for insert to authenticated with check (user_id = auth.uid());
create policy contracts_update on contracts for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy contracts_delete on contracts for delete to authenticated using (user_id = auth.uid());
create policy clauses_read on contract_clauses for select to authenticated using (app.can_read_contract(contract_id));
create policy clauses_write on contract_clauses for insert to authenticated
  with check (exists (select 1 from contracts c where c.id = contract_id and c.user_id = auth.uid()));
create policy canalyses_read on contract_analyses for select to authenticated using (app.can_read_contract(contract_id));
create policy canalyses_write on contract_analyses for insert to authenticated
  with check (exists (select 1 from contracts c where c.id = contract_id and c.user_id = auth.uid()));
create policy grants_read on contract_access_grants for select to authenticated
  using (grantee_id = auth.uid() or granted_by = auth.uid());
create policy grants_owner on contract_access_grants for insert to authenticated
  with check (granted_by = auth.uid() and exists (select 1 from contracts c where c.id = contract_id and c.user_id = auth.uid()));

create policy citations_own on legal_citations for select to authenticated
  using ((simulation_result_id is not null and app.owns_result(simulation_result_id))
      or (contract_analysis_id is not null and exists (select 1 from contract_analyses a where a.id = contract_analysis_id
          and app.can_read_contract(a.contract_id))));

create policy runs_own on agent_runs for all to authenticated
  using (user_id = auth.uid() or app.my_role() = 'system_admin') with check (user_id = auth.uid());
create policy tasks_own on agent_tasks for select to authenticated
  using (app.owns_run(agent_run_id) or app.my_role() = 'system_admin');
create policy agent_events_own on agent_events for select to authenticated
  using (app.owns_run(agent_run_id) or app.my_role() = 'system_admin');
create policy copilot_own on copilot_messages for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy reports_own on reports for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy notif_own on notifications for select to authenticated using (user_id = auth.uid());
create policy notif_mark on notifications for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy subs_own on notification_subscriptions for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 公開法規與規則
create policy docs_public on legal_documents for select to anon, authenticated using (true);
create policy docver_public on legal_document_versions for select to anon, authenticated using (true);
create policy articles_public on legal_articles for select to anon, authenticated using (true);
create policy chunks_public on legal_chunks for select to anon, authenticated using (true);
create policy rules_public on legal_rules for select to anon, authenticated using (true);
create policy rulever_public on legal_rule_versions for select to anon, authenticated using (true);
create policy ruletests_public on rule_test_cases for select to anon, authenticated using (true);
create policy updates_public on regulatory_updates for select to anon, authenticated using (true);

-- 規則審查：legal_reviewer 改狀態；system_admin 可建立新版本（定義不可改，見 trigger）
create policy rulever_review on legal_rule_versions for update to authenticated
  using (app.my_role() in ('legal_reviewer','system_admin')) with check (app.my_role() in ('legal_reviewer','system_admin'));
create policy rulever_insert on legal_rule_versions for insert to authenticated
  with check (app.my_role() in ('legal_reviewer','system_admin') and review_status in ('draft','pending_review'));
create policy rules_insert on legal_rules for insert to authenticated with check (app.my_role() = 'system_admin');
create policy updates_review on regulatory_updates for update to authenticated
  using (app.my_role() in ('legal_reviewer','system_admin')) with check (app.my_role() in ('legal_reviewer','system_admin'));
create policy reviews_read on reviews for select to authenticated
  using (reviewer_id = auth.uid() or app.my_role() in ('legal_reviewer','system_admin'));
create policy reviews_insert on reviews for insert to authenticated
  with check (reviewer_id = auth.uid() and app.my_role() in ('legal_reviewer','system_admin'));

create policy audit_read on audit_logs for select to authenticated
  using (actor_id = auth.uid() or app.my_role() = 'system_admin');
create policy audit_insert on audit_logs for insert to authenticated with check (actor_id = auth.uid());
