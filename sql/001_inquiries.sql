create table public.inquiries (
  id bigint generated always as identity primary key,
  name text not null,
  email text not null,
  content text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint inquiries_name_length check (char_length(btrim(name)) between 1 and 100),
  constraint inquiries_email_format check (email ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
  constraint inquiries_content_length check (char_length(btrim(content)) between 1 and 5000)
);

create index inquiries_created_at_idx on public.inquiries (created_at desc);

alter table public.inquiries enable row level security;

revoke all on table public.inquiries from anon, authenticated, service_role;
grant select, insert, update, delete on table public.inquiries to service_role;

revoke all on sequence public.inquiries_id_seq from anon, authenticated;
grant usage, select on sequence public.inquiries_id_seq to service_role;
