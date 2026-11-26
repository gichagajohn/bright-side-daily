-- Additive migration; does NOT alter existing tables, buckets or content.
-- Apply once in the identified project's SQL editor before enabling publishing.
begin;
create table if not exists public.bsd_jobs (
  job_key text primary key,
  status text not null default 'claimed',
  content_hash text unique,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.bsd_assets (
  clip_id text primary key,
  job_key text not null references public.bsd_jobs(job_key),
  used_at timestamptz not null default now(),
  provenance jsonb not null
);
create table if not exists public.bsd_metrics (
  observation_key text primary key,
  payload jsonb not null,
  collected_at timestamptz not null default now()
);
alter table public.bsd_jobs enable row level security;
alter table public.bsd_assets enable row level security;
alter table public.bsd_metrics enable row level security;
revoke all on public.bsd_jobs, public.bsd_assets, public.bsd_metrics from anon, authenticated;
grant select, insert, update on public.bsd_jobs, public.bsd_assets, public.bsd_metrics to service_role;
commit;
-- Rollback: leave these tables intact to preserve the anti-duplicate ledger.
