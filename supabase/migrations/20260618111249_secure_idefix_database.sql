-- Supabase hosting overlay for Idéfix.
--
-- Alembic remains the source of truth for the business schema. This migration
-- only secures the restored public schema and establishes a dedicated owner.
-- The LOGIN password is provisioned out-of-band and must never be committed.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'idefix_owner') then
    create role idefix_owner
      nologin
      nosuperuser
      nocreatedb
      nocreaterole
      noreplication
      nobypassrls;
  end if;
end
$$;

grant connect on database postgres to idefix_owner;
grant usage, create on schema public to idefix_owner;
-- PostgreSQL requires the current owner to be a member of the target role
-- before relation ownership can be transferred. Supabase's managed `postgres`
-- role is the current owner of the restored objects.
grant idefix_owner to postgres;

-- Own every Idéfix relation restored into public so the offline pipeline and
-- future Alembic migrations can perform DDL without using Supabase's postgres
-- administrator credentials.
do $$
declare
  relation record;
begin
  for relation in
    select c.relname
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind in ('r', 'p')
  loop
    -- Ownership of SERIAL/IDENTITY sequences follows their owning table.
    execute format('alter table public.%I owner to idefix_owner', relation.relname);
    execute format('alter table public.%I enable row level security', relation.relname);
  end loop;
end
$$;

-- Idéfix has no browser-to-database path. The static webapp consumes scrubbed
-- JSON exports, so the Data API roles receive no access to operational tables.
revoke all privileges on all tables in schema public from anon, authenticated;
revoke all privileges on all sequences in schema public from anon, authenticated;
revoke all privileges on all functions in schema public from anon, authenticated;

alter default privileges for role idefix_owner in schema public
  revoke all on tables from anon, authenticated;
alter default privileges for role idefix_owner in schema public
  revoke all on sequences from anon, authenticated;
alter default privileges for role idefix_owner in schema public
  revoke all on functions from anon, authenticated;

alter role idefix_owner set search_path = public;
