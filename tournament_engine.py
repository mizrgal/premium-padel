"""Pure tournament bracket logic - no Flask, no DB. Testable in isolation."""

import functools
import random

GROUP_ROUND_ORDER = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
GROUP_ROUNDS = [1, 1, 2, 2, 3, 3]

# groups of 3 have no parallel rounds - each pair sits out one round (round robin bye)
TRIO_ROUND_ORDER = [(0, 1), (0, 2), (1, 2)]
TRIO_ROUNDS = [1, 2, 3]


def _circle_method_schedule(n):
    """Round-robin schedule for n (even) pair-indices via the circle method: n-1 rounds,
    n/2 matches per round, with no pair playing twice in the same round."""
    fixed, rotating = 0, list(range(1, n))
    order, rounds = [], []
    for round_no in range(1, n):
        ring = [fixed] + rotating
        for i in range(n // 2):
            order.append((ring[i], ring[n - 1 - i]))
            rounds.append(round_no)
        rotating = [rotating[-1]] + rotating[:-1]
    return order, rounds


SIX_ROUND_ORDER, SIX_ROUNDS = _circle_method_schedule(6)
EIGHT_ROUND_ORDER, EIGHT_ROUNDS = _circle_method_schedule(8)

# pairs_count -> default groups_count. 12 pairs is 4 groups of 3, 8 defaults to 2 groups of 4
# (a single group of 8 is requested explicitly via run_draw's groups_count argument), everything
# else divides evenly into groups of 4.
GROUPS_COUNT_BY_PAIRS = {4: 1, 6: 1, 8: 2, 12: 4, 16: 4}


def groups_count_for_pairs(pairs_count):
    if pairs_count not in GROUPS_COUNT_BY_PAIRS:
        raise ValueError(f"unsupported pairs_count {pairs_count}")
    return GROUPS_COUNT_BY_PAIRS[pairs_count]


def round_robin_matches(pair_ids):
    """3, 4, 6, or 8 pair ids -> (round_number, pair_a_id, pair_b_id) tuples for a full round
    robin (every pair plays every other pair in the group exactly once)."""
    n = len(pair_ids)
    if n == 4:
        order, rounds = GROUP_ROUND_ORDER, GROUP_ROUNDS
    elif n == 3:
        order, rounds = TRIO_ROUND_ORDER, TRIO_ROUNDS
    elif n == 6:
        order, rounds = SIX_ROUND_ORDER, SIX_ROUNDS
    elif n == 8:
        order, rounds = EIGHT_ROUND_ORDER, EIGHT_ROUNDS
    else:
        raise ValueError("groups must have exactly 3, 4, 6, or 8 pairs")
    return [
        (round_no, pair_ids[a], pair_ids[b])
        for (a, b), round_no in zip(order, rounds)
    ]


def run_draw(pair_ids, groups_count=None):
    """Shuffle pairs, assign group numbers, generate all group-stage matches.

    groups_count defaults to the standard layout for len(pair_ids) (see
    GROUPS_COUNT_BY_PAIRS), but can be passed explicitly to pick a non-default layout
    (e.g. a single round-robin group of 8 pairs instead of the default 2 groups of 4).

    Returns (group_assignments, matches) where:
      group_assignments = {pair_id: group_number}
      matches = [{"stage": "group", "group_number": n, "round_number": r,
                  "pair_a_id": ..., "pair_b_id": ...}, ...]
    """
    if groups_count is None:
        groups_count = groups_count_for_pairs(len(pair_ids))
    group_size = len(pair_ids) // groups_count
    shuffled = list(pair_ids)
    random.shuffle(shuffled)

    group_assignments = {}
    matches = []
    idx = 0
    for g in range(groups_count):
        group_number = g + 1
        group_pairs = shuffled[g * group_size:(g + 1) * group_size]
        for pid in group_pairs:
            group_assignments[pid] = group_number
        for round_no, a, b in round_robin_matches(group_pairs):
            matches.append({
                "stage": "group",
                "group_number": group_number,
                "round_number": round_no,
                "match_index": idx,
                "pair_a_id": a,
                "pair_b_id": b,
            })
            idx += 1
    return group_assignments, matches


def head_to_head_winner(pair_a_id, pair_b_id, group_matches):
    """The winner_pair_id of the completed group_matches game between these two pairs, or
    None if they haven't played (or it hasn't been scored) yet."""
    for m in group_matches:
        if {m["pair_a_id"], m["pair_b_id"]} == {pair_a_id, pair_b_id} and m.get("winner_pair_id"):
            return m["winner_pair_id"]
    return None


def compute_group_standings(pair_ids, group_matches, tiebreak_winners=None):
    """pair_ids: pairs in one group. group_matches: completed matches for that group
    (each with pair_a_id, pair_b_id, score_a, score_b, winner_pair_id).
    tiebreak_winners: optional {frozenset({pair_a, pair_b}): winner_pair_id} for any manual
    tie-break matches played between two pairs still tied after head-to-head (e.g. a 3-way
    circular tie with no single decisive game).

    Returns list of pair_ids ranked best-first: wins desc, then game_diff desc (the two
    standard padel round-robin tie-break criteria). An exact tie on both is broken by the
    result of the head-to-head game the two tied pairs already played each other in the
    group stage, then by tiebreak_winners if that's also inconclusive (e.g. part of a
    circular 3-way tie). Ties with neither keep stable input order - games_won is NOT used
    as a silent further tiebreaker, since that would hide a real tie from the admin instead
    of surfacing it for a tie-break match.
    """
    tiebreak_winners = tiebreak_winners or {}
    stats = {pid: {"wins": 0, "games_won": 0, "games_lost": 0} for pid in pair_ids}
    for m in group_matches:
        if m.get("winner_pair_id") is None:
            continue
        a, b = m["pair_a_id"], m["pair_b_id"]
        sa, sb = m["score_a"], m["score_b"]
        if a in stats:
            stats[a]["games_won"] += sa
            stats[a]["games_lost"] += sb
            if m["winner_pair_id"] == a:
                stats[a]["wins"] += 1
        if b in stats:
            stats[b]["games_won"] += sb
            stats[b]["games_lost"] += sa
            if m["winner_pair_id"] == b:
                stats[b]["wins"] += 1

    def stat_key(pid):
        s = stats[pid]
        diff = s["games_won"] - s["games_lost"]
        return (-s["wins"], -diff)

    def compare(a, b):
        ka, kb = stat_key(a), stat_key(b)
        if ka != kb:
            return -1 if ka < kb else 1
        winner = head_to_head_winner(a, b, group_matches) or tiebreak_winners.get(frozenset((a, b)))
        if winner == a:
            return -1
        if winner == b:
            return 1
        return 0

    ranked = sorted(pair_ids, key=functools.cmp_to_key(compare))
    return ranked, stats


def find_stat_ties(pair_ids, stats):
    """Groups of 2+ pair_ids exactly tied on (wins, game_diff) - candidates for a manual
    tie-break match. Matches the ranking criteria in compute_group_standings exactly."""
    buckets = {}
    for pid in pair_ids:
        s = stats[pid]
        diff = s["games_won"] - s["games_lost"]
        key = (s["wins"], diff)
        buckets.setdefault(key, []).append(pid)
    return [pids for pids in buckets.values() if len(pids) >= 2]


def group_qualifiers(groups_count, standings_by_group):
    """standings_by_group: {group_number: ranked_pair_ids (best first)}.
    Returns ordered list [(group_number, rank, pair_id), ...] for rank 1 and 2 of every group,
    ordered by group number then rank.
    """
    qualifiers = []
    for g in range(1, groups_count + 1):
        ranked = standings_by_group[g]
        qualifiers.append((g, 1, ranked[0]))
        qualifiers.append((g, 2, ranked[1]))
    return qualifiers


def _qualifier_pair_id(qualifiers, group_number, rank):
    for g, r, pid in qualifiers:
        if g == group_number and r == rank:
            return pid
    raise ValueError(f"no qualifier for group {group_number} rank {rank}")


def generate_next_stage(tournament_pairs_count, groups_count, current_stage, standings_by_group=None,
                         stage_winner_ids_in_order=None):
    """Compute the matches for the stage that follows `current_stage`.

    - current_stage == "group": needs standings_by_group ({group_number: ranked_pair_ids}).
      Returns (next_stage_name, matches) where matches is a list of
      {"pair_a_id", "pair_b_id"} dicts (no scores yet).
    - current_stage in ("quarterfinal", "semifinal"): needs stage_winner_ids_in_order
      (winners in the same order the matches were created). Pairs consecutive winners.
    - current_stage == "final": returns (None, []) - tournament is complete.
    """
    if current_stage == "group":
        qualifiers = group_qualifiers(groups_count, standings_by_group)
        if groups_count == 1:
            return "final", _with_match_index([
                {"pair_a_id": _qualifier_pair_id(qualifiers, 1, 1), "pair_b_id": _qualifier_pair_id(qualifiers, 1, 2)},
            ])
        if groups_count == 2:
            return "semifinal", _with_match_index([
                {"pair_a_id": _qualifier_pair_id(qualifiers, 1, 1), "pair_b_id": _qualifier_pair_id(qualifiers, 2, 2)},
                {"pair_a_id": _qualifier_pair_id(qualifiers, 2, 1), "pair_b_id": _qualifier_pair_id(qualifiers, 1, 2)},
            ])
        if groups_count == 4:
            # A x D / B x C crossover, with each group's two qualifiers sent to opposite
            # bracket halves (rank 1 of a group and rank 2 of that same group can then only
            # meet again in the final, never as early as the semifinal).
            return "quarterfinal", _with_match_index([
                {"pair_a_id": _qualifier_pair_id(qualifiers, 1, 1), "pair_b_id": _qualifier_pair_id(qualifiers, 4, 2)},
                {"pair_a_id": _qualifier_pair_id(qualifiers, 2, 1), "pair_b_id": _qualifier_pair_id(qualifiers, 3, 2)},
                {"pair_a_id": _qualifier_pair_id(qualifiers, 1, 2), "pair_b_id": _qualifier_pair_id(qualifiers, 3, 1)},
                {"pair_a_id": _qualifier_pair_id(qualifiers, 2, 2), "pair_b_id": _qualifier_pair_id(qualifiers, 4, 1)},
            ])
        raise ValueError(f"unsupported groups_count {groups_count}")

    if current_stage == "quarterfinal":
        w = stage_winner_ids_in_order
        return "semifinal", _with_match_index([
            {"pair_a_id": w[0], "pair_b_id": w[1]},
            {"pair_a_id": w[2], "pair_b_id": w[3]},
        ])

    if current_stage == "semifinal":
        w = stage_winner_ids_in_order
        return "final", _with_match_index([
            {"pair_a_id": w[0], "pair_b_id": w[1]},
        ])

    if current_stage == "final":
        return None, []

    raise ValueError(f"unknown stage {current_stage}")


def _with_match_index(matches):
    for i, m in enumerate(matches):
        m["match_index"] = i
    return matches


def score_winner(pair_a_id, pair_b_id, score_a, score_b):
    if score_a == score_b:
        raise ValueError("no ties allowed - scores must differ")
    return pair_a_id if score_a > score_b else pair_b_id


def resolve_matchup(pair_a_id, pair_b_id, matchup_matches):
    """A knockout-stage matchup can be decided by 1 or 2 games (round_number 1/2), with an
    optional decisive 3rd game (round_number 3) if the first two split 1-1. Returns the
    winning pair_id, or None if not yet resolved (still waiting on a game, or on a decider
    after a 1-1 split).
    """
    wins = {pair_a_id: 0, pair_b_id: 0}
    decider = None
    for m in matchup_matches:
        if m.get("round_number") == 3:
            decider = m
            continue
        if m.get("winner_pair_id") is None:
            return None
        wins[m["winner_pair_id"]] += 1
    if wins[pair_a_id] != wins[pair_b_id]:
        return pair_a_id if wins[pair_a_id] > wins[pair_b_id] else pair_b_id
    if decider is not None and decider.get("winner_pair_id"):
        return decider["winner_pair_id"]
    return None
