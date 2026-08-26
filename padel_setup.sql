create extension if not exists pgcrypto;

create table if not exists padel_users (
  id uuid primary key default gen_random_uuid(),
  username text unique not null,
  phone text not null,
  password_hash text not null,
  is_admin boolean not null default false,
  bio text,
  play_side text check (play_side in ('right', 'left', 'both')),
  avatar_url text,
  created_at timestamptz default now()
);

create table if not exists padel_tournaments (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  date date not null,
  level text not null,
  pairs_count int not null check (pairs_count in (4, 6, 8, 12, 16)),
  groups_count int not null,
  game_target int not null check (game_target in (4, 6, 8)),
  price_per_player numeric(10,2),
  about text,
  manager text,
  location text,
  status text not null default 'open', -- open -> full -> in_progress -> completed
  winner_pair_id uuid,
  created_by uuid references padel_users(id),
  created_at timestamptz default now()
);

-- player{1,2}_name / player{1,2}_phone are always populated (copied from the linked
-- account's username/phone at pair-creation time, or entered free-text for a guest
-- with no account) so pair display never needs to join padel_users.
create table if not exists padel_pairs (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references padel_tournaments(id),
  player1_id uuid references padel_users(id),
  player1_name text not null,
  player1_phone text not null,
  player2_id uuid references padel_users(id),
  player2_name text not null,
  player2_phone text not null,
  group_number int,
  added_by uuid references padel_users(id),
  created_at timestamptz default now()
);

create table if not exists padel_matches (
  id uuid primary key default gen_random_uuid(),
  tournament_id uuid not null references padel_tournaments(id),
  stage text not null, -- group | tiebreak | quarterfinal | semifinal | final
  group_number int,
  round_number int,
  match_index int not null default 0,
  game_target int check (game_target in (4, 6, 8)),
  pair_a_id uuid references padel_pairs(id),
  pair_b_id uuid references padel_pairs(id),
  score_a int,
  score_b int,
  winner_pair_id uuid references padel_pairs(id),
  created_at timestamptz default now()
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'winner_pair_fk') then
    alter table padel_tournaments
      add constraint winner_pair_fk foreign key (winner_pair_id) references padel_pairs(id);
  end if;
end $$;

create index if not exists idx_padel_pairs_tournament on padel_pairs(tournament_id);
create index if not exists idx_padel_matches_tournament on padel_matches(tournament_id);
