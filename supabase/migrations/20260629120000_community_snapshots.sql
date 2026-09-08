-- Snapshots communautés (clustering TF-IDF/analytics + embedding) calculés
-- hors-ligne et poussés ici. Source de vérité consommée par le build Vercel
-- (prebuild Node) qui les écrit dans le bundle statique. Une ligne par
-- (mission, label_source). Le payload est déjà scrubbé au push.
create table if not exists public.community_snapshots (
  mission       text        not null,
  label_source  text        not null,  -- 'analytics' (lexical/TF-IDF) | 'embedding'
  snapshot      jsonb       not null,
  generated_at  timestamptz not null default now(),
  primary key (mission, label_source)
);

-- Même posture de sécurité que le reste du schéma (migration de durcissement) :
-- propriété idefix_owner, RLS activé, aucun accès anon/authenticated. Seul le
-- service-role (qui bypasse RLS) lit/écrit cette table.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'idefix_owner') then
    execute 'alter table public.community_snapshots owner to idefix_owner';
  end if;
end
$$;

alter table public.community_snapshots enable row level security;
revoke all privileges on public.community_snapshots from anon, authenticated;
