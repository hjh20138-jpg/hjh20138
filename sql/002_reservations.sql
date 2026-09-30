create table public.reservations (
  id bigint generated always as identity primary key,
  name text not null,
  phone text not null,
  note text,
  created_at timestamptz not null default now(),
  constraint reservations_name_length check (char_length(btrim(name)) between 1 and 100),
  constraint reservations_phone_format check (phone ~ '^010[0-9]{8}$' or phone ~ '^01[16789][0-9]{7,8}$'),
  constraint reservations_note_length check (note is null or char_length(btrim(note)) between 1 and 2000)
);

create index reservations_created_at_idx on public.reservations (created_at desc);

alter table public.reservations enable row level security;

revoke all on table public.reservations from anon, authenticated, service_role;
grant select, insert, update, delete on table public.reservations to service_role;

revoke all on sequence public.reservations_id_seq from anon, authenticated;
grant usage, select on sequence public.reservations_id_seq to service_role;
