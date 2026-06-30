-- ============================================================================
-- Japanese vocab study — Supabase schema
-- Run ONCE in the Supabase SQL editor (Database → SQL editor → New query → Run).
--
-- Creates:
--   words            — canonical catalog of every practiceable word ("track all words")
--   user_word_stats  — per-user accuracy (seen / correct / wrong / score), DENORMALIZED
--                      with the word's reading/meaning/type so the UI needs no joins
--   record_attempt() — atomic upsert of one answer (no client read-modify-write)
--   import_stats()   — one-shot import of legacy browser localStorage progress
--
-- Security: Row-Level Security so each user can read/write ONLY their own stats.
-- The anon (public) key in supabase-config.js is safe to expose *because* RLS is on.
-- ============================================================================

-- 1) Canonical catalog (seeded from db/words_seed.sql; regenerate with work/export_words.py)
create table if not exists public.words (
  slug    text not null,
  word    text not null,
  reading text not null,
  meaning text,
  type    text not null check (type in ('reading', 'meaning')),
  primary key (slug, word)
);

-- 2) Per-user aggregate. accuracy ("frequency correct") = correct / nullif(seen, 0).
--    Denormalized reading/meaning/type so 你的难词 + the review render with no join.
create table if not exists public.user_word_stats (
  user_id   uuid not null references auth.users (id) on delete cascade,
  slug      text not null,
  word      text not null,
  reading   text not null default '',
  meaning   text,
  type      text not null default 'reading',
  seen      integer not null default 0,
  correct   integer not null default 0,
  wrong     integer not null default 0,
  score     integer not null default 0,
  last_seen timestamptz not null default now(),
  primary key (user_id, slug, word)
);
create index if not exists user_word_stats_hard_idx
  on public.user_word_stats (user_id, score desc);

-- 3) Row-Level Security --------------------------------------------------------
alter table public.words           enable row level security;
alter table public.user_word_stats enable row level security;

-- words: any signed-in user may read the catalog; writes happen via the SQL editor
-- (service role), so no client-write policy is defined.
drop policy if exists "words readable by authenticated" on public.words;
create policy "words readable by authenticated"
  on public.words for select to authenticated using (true);

-- user_word_stats: a user may read/write ONLY rows they own.
drop policy if exists "own stats" on public.user_word_stats;
create policy "own stats"
  on public.user_word_stats for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- 4) record one answer, atomically. SECURITY DEFINER so it always stamps the
--    caller's own user_id and increments server-side (no race).
create or replace function public.record_attempt(
  p_slug text, p_word text, p_reading text, p_meaning text, p_type text, p_correct boolean
) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  insert into public.user_word_stats as s
      (user_id, slug, word, reading, meaning, type, seen, correct, wrong, score, last_seen)
  values (
      auth.uid(), p_slug, p_word, coalesce(p_reading, ''), p_meaning,
      coalesce(nullif(p_type, ''), 'reading'), 1,
      case when p_correct then 1 else 0 end,
      case when p_correct then 0 else 1 end,
      case when p_correct then 0 else 2 end,
      now())
  on conflict (user_id, slug, word) do update set
      reading   = excluded.reading,
      meaning   = excluded.meaning,
      type      = excluded.type,
      seen      = s.seen + 1,
      correct   = s.correct + case when p_correct then 1 else 0 end,
      wrong     = s.wrong   + case when p_correct then 0 else 1 end,
      score     = greatest(0, s.score + case when p_correct then -1 else 2 end),
      last_seen = now();
end; $$;
grant execute on function public.record_attempt(text, text, text, text, text, boolean) to authenticated;

-- 5) one-shot import of legacy localStorage aggregates (the 导入本机旧记录 button).
--    Payload: jsonb array of {slug, word, reading, meaning, type, seen, correct, wrong, score}.
create or replace function public.import_stats(p jsonb)
returns integer
language plpgsql security definer set search_path = public as $$
declare rec jsonb; n integer := 0;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  for rec in select * from jsonb_array_elements(p) loop
    insert into public.user_word_stats as s
        (user_id, slug, word, reading, meaning, type, seen, correct, wrong, score, last_seen)
    values (
        auth.uid(), rec->>'slug', rec->>'word',
        coalesce(rec->>'reading', ''), rec->>'meaning',
        coalesce(nullif(rec->>'type', ''), 'reading'),
        coalesce((rec->>'seen')::int, 0), coalesce((rec->>'correct')::int, 0),
        coalesce((rec->>'wrong')::int, 0), coalesce((rec->>'score')::int, 0), now())
    on conflict (user_id, slug, word) do update set
        seen      = s.seen + excluded.seen,
        correct   = s.correct + excluded.correct,
        wrong     = s.wrong + excluded.wrong,
        score     = greatest(0, s.score + excluded.score),
        last_seen = now();
    n := n + 1;
  end loop;
  return n;
end; $$;
grant execute on function public.import_stats(jsonb) to authenticated;
