begin;

create extension if not exists pgcrypto;

create table jobs (
    id uuid primary key default gen_random_uuid(),
    external_id text,
    company text not null,
    normalized_company text not null,
    title text not null,
    normalized_title text not null,
    description_snapshot text not null default '',
    source text not null,
    source_url text,
    detected_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create unique index jobs_source_external_id_uidx
    on jobs (source, external_id) where external_id is not null;
create unique index jobs_source_url_uidx
    on jobs (source, source_url) where external_id is null and source_url is not null;
create unique index jobs_fallback_identity_uidx
    on jobs (source, normalized_company, normalized_title)
    where external_id is null and source_url is null;

create table recommendation_runs (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    matcher_version text not null,
    profile_version text not null,
    cv_version text,
    source_context text,
    total_jobs_found integer check (total_jobs_found is null or total_jobs_found >= 0),
    total_jobs_scored integer check (total_jobs_scored is null or total_jobs_scored >= 0)
);

create table recommendation_items (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references recommendation_runs(id) on delete cascade,
    job_id uuid not null references jobs(id),
    rank integer not null check (rank > 0),
    fit_score numeric(5,2) not null check (fit_score between 0 and 100),
    role_family text not null,
    role_fit numeric(6,5) not null,
    skill_fit numeric(6,5) not null,
    matched_evidence_strength numeric(6,5) not null,
    interest_alignment numeric(6,5) not null,
    hard_gap_penalty numeric(6,5) not null,
    reasons jsonb not null default '[]'::jsonb,
    strong_matches jsonb not null default '[]'::jsonb,
    partial_matches jsonb not null default '[]'::jsonb,
    hard_gaps jsonb not null default '[]'::jsonb,
    job_description_snapshot text not null default '',
    recommended_at timestamptz not null default now(),
    unique (run_id, rank),
    unique (run_id, job_id)
);

create table applications (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references jobs(id),
    recommendation_item_id uuid references recommendation_items(id),
    applied_at timestamptz not null default now(),
    application_source text,
    cv_version text,
    status text not null default 'applied',
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (status in ('applied','rejected','screening','technical_test','interview','final_interview','offer','withdrawn','ghosted'))
);

create table application_events (
    id uuid primary key default gen_random_uuid(),
    application_id uuid not null references applications(id) on delete cascade,
    event text not null,
    occurred_at timestamptz not null default now(),
    notes text,
    metadata jsonb,
    created_at timestamptz not null default now(),
    check (event in ('applied','rejected','screening','technical_test','interview','final_interview','offer','withdrawn','ghosted'))
);

create index recommendation_items_run_idx on recommendation_items(run_id);
create index application_events_application_time_idx on application_events(application_id, occurred_at, created_at);

create or replace function set_updated_at() returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger applications_set_updated_at
before update on applications
for each row execute function set_updated_at();

-- Historical career data is private. Server-side service-role access bypasses
-- RLS; no anonymous policies are created in this initial migration.
alter table jobs enable row level security;
alter table recommendation_runs enable row level security;
alter table recommendation_items enable row level security;
alter table applications enable row level security;
alter table application_events enable row level security;

commit;
