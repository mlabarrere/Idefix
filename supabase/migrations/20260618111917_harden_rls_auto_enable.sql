-- Supabase may install this SECURITY DEFINER helper in the exposed public
-- schema while applying RLS changes. Idéfix does not expose database RPCs.
-- Remove every implicit execution path, including the PostgreSQL PUBLIC role.
revoke execute on function public.rls_auto_enable() from public;
revoke execute on function public.rls_auto_enable() from anon, authenticated;
