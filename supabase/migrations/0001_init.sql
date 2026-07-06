-- 0001_init: freee-invoice 初期スキーマ
-- 納品書を正とし、締め・紐付け・発行管理のみをSupabaseで持つ
-- 適用日: 2026-07-03 / project: uixpvfddixvbtavjfwhb

-- 取引先マスタ
create table public.partners (
  id                          uuid primary key default gen_random_uuid(),
  freee_partner_id            text unique,
  name                        text not null,
  default_invoice_template_id text,
  closing_day                 int,          -- NULL=月末締め
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now()
);

-- 締め処理の実行単位（月次）
create table public.billing_runs (
  id          uuid primary key default gen_random_uuid(),
  period_ym   text not null unique check (period_ym ~ '^[0-9]{4}-[0-9]{2}$'),
  status      text not null default 'running' check (status in ('running','drafted','failed')),
  started_at  timestamptz not null default now(),
  finished_at timestamptz
);

-- 請求書 ↔ 納品書の対応（二重請求防止の要）
create table public.invoice_links (
  id                     uuid primary key default gen_random_uuid(),
  billing_run_id         uuid references public.billing_runs(id) on delete set null,
  partner_id             uuid references public.partners(id)     on delete set null,
  freee_invoice_id       text,
  freee_delivery_slip_id text not null unique,   -- 同一納品書の二重取り込み禁止
  period_ym              text,
  created_at             timestamptz not null default now()
);

-- 発行ジョブ
create table public.issue_jobs (
  id              uuid primary key default gen_random_uuid(),
  billing_run_id  uuid references public.billing_runs(id) on delete cascade,
  partner_id      uuid references public.partners(id)     on delete set null,
  status          text not null default 'pending' check (status in ('pending','drafted','failed')),
  idempotency_key text not null unique,           -- = period_ym + partner_id
  freee_response  jsonb,
  error           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- freee OAuth トークン
create table public.freee_tokens (
  id            uuid primary key default gen_random_uuid(),
  access_token  text not null,
  refresh_token text not null,
  expires_at    timestamptz not null,
  company_id    text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- 検索用インデックス
create index idx_invoice_links_partner_period on public.invoice_links (partner_id, period_ym);
create index idx_issue_jobs_run               on public.issue_jobs (billing_run_id);

-- RLSは有効化（ポリシーなし＝サービスロール以外は不可。バックエンド専用のため安全側）
alter table public.partners      enable row level security;
alter table public.billing_runs  enable row level security;
alter table public.invoice_links enable row level security;
alter table public.issue_jobs    enable row level security;
alter table public.freee_tokens  enable row level security;
