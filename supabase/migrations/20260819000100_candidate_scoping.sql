begin;

create table candidate_profiles (
    candidate_id text primary key,
    profile_version text not null,
    profile_snapshot jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table recommendation_runs add column candidate_id text;
create index recommendation_runs_candidate_created_idx on recommendation_runs(candidate_id, created_at desc);

alter table candidate_profiles enable row level security;

commit;
