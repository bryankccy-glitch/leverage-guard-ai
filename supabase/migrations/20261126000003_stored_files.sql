-- 雲端（serverless）沒有可長期保存的檔案系統：契約原檔存在資料庫，只有 service_role 可讀寫
create table if not exists stored_files (
  path text primary key,
  data bytea not null,
  created_at timestamptz not null default now()
);
alter table stored_files enable row level security;
alter table stored_files force row level security;
create policy service_all on stored_files for all to service_role using (true) with check (true);
revoke all on stored_files from anon, authenticated;
grant select, insert, delete on stored_files to service_role;
