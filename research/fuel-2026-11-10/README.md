# ocean's fuel, 2026-11-10 (CHANGES 495)

Goal: lower mean fuel a turn, p90, out-of-fuel turns and shortcuts, the worst case first, with replays at 100M
byte-identical unless the new version is plainly better. Base: `bots/ocean` at 0309644b5 (CHANGES 494), frozen as
`variants/ocf-base`; result `variants/oc-fuel-495` (= `bots/ocean`), [patch](oc-fuel-495.patch).

## Result

All against ocf-base in mirror games, own drafts, fast runner.

| measure | base | oc-fuel-495 | change |
|---|---|---|---|
| out-of-fuel turns, real budget, 4,096 games (`fuelcap/p1`, debug builds) | 49,337 | 42,634 | **-13.6%** (95% -16.3 to -11.1, games resampled) |
| mean fuel a turn, same games | 51,669 | 48,278 | -6.5% |
| p50 / p90 / p99 | 49,834 / 85,850 / 95,319 | 46,314 / 84,966 / 95,155 | -7.1% / -1.0% / -0.2% |
| `SHORTCUT` lines (out-of-fuel included) | 1,527,368 | 1,512,062 | -1.0% (without them -0.6%, 95% -2.4 to +0.9) |
| 100M identity, own drafts (96 games, `tools/maps-id.txt`) | | 94 / 96 | mean -5.7%, p99 -0.6%, turns over 100k -2.8% |
| 100M identity, test drafts (96 games) | | 96 / 96 | mean -5.7% |

**Results against ocf-base** (release builds, `merged/fuel-1995`, 20,480 games each, the same games):

| gate | win% (CI) of n | out-of-fuel turns, arm / base |
|---|---|---|
| ab.py oc-fuel-495 | 49.6 (48.9-50.3) of 20,480 | 223,128 / 255,886 (-12.8%) |
| ab.py oc-fuel-495, held out (`merged/fuel-1996`) | 50.1 (49.7-50.6) of 40,960 | 429,719 / 493,257 (-12.9%) |
| ab.py oc-fuel-495 without the tail's fuel checks (change 3) | 49.4 (48.7-50.1) of 20,480 | 241,666 / 255,011 (-5.2%) |
| ab.py oc-fuel-495 with the own ring at radius 8 (change 4 undone) | 49.7 (49.0-50.4) of 20,480 | 222,092 / 255,878 (-13.2%) |

So the tail's checks are worth about 7.6 points of the out-of-fuel fall and cost no games; the smaller ring costs about
0.5% more out-of-fuel turns for 2.3% of all fuel (one constant, `TurnEndQueue::own_radius`).

- The two games that differ at 100M (gen-contested-centre-144000010000 a, gen-ladder-144000000050 b) are identical
  (4/4) once neither bot prepares next turn's walk in the turn-end queue: the known coupling (fuelcap README), reached
  because the queue now gets further on the same fuel.
- By first-turn cost (a proxy for map size and camps) the mean falls 4.5% on the smallest third of games and 6.9% on
  the largest tenth; p90 and p99 fall a little in every class.
- p90 is pinned by the turn-end queue: it fills caches until 84k of the turn is spent, and 12.7% of turns end there
  (most in rounds 2-60, the map-wide warm-up). Only less warm-up would move it.

## Where out-of-fuel turns come from

- **The profile is flat, also on the turns that run out.** `tools/fuel/fuelprof` now writes three profiles: all turns,
  turns that finished on 88k+, and out-of-fuel episodes (setup.sh). By source function (`tools/byfn.py`) the costliest
  in episodes is 2.0% (`update_champion`); nothing in decide stands out.
- **58% of turns that run out pass no fuel check** (census `tail.py`); the heavy parts are `want_home`'s stand (17k a
  turn that ran out: its sim 12.7k a call, and the first strike and Reach builds), the strike search (33k where it
  runs), retreat (47k where it runs) and Willow's support (23k).
- **29% run out in the turn's tail**, after decide's branch has acted (probe: fuel left at each step from act()'s
  `see_revealed` to the posts, 96 games at the real budget). 13% of all first out-of-fuel turns enter the tail with
  under 2k, 18% with under 5k. With every step idle the tail costs 1.35k at p10 and 1.56k at the median, so a turn
  entering it with less cannot finish; from under 1k none did.
- A resumed stale turn wastes 4.7k of the next round on average (p50 2.9k, p90 9.2k) before a stale check ends it; 37%
  of the turns played after it run out again. Earlier checks were not added: the long tails are spread over goal,
  retreat and route code, and a check costs every turn.
- Inside the turn order (5% of first out-of-fuel turns) the runs out are in `offer_heal` (up to 23k), `plain_priority`
  (p50 1.7k, to 16k) and the escape offers, entered with 3-16k: a least-cost gate saves almost none of them.

## Changes

1. **Turn-end queue: ring scan** (exact). `around()` restarted its scan of a ring's four sides after every tile and
   rescanned every finished ring of a new centre: 3.5% of all fuel in bookkeeping. Now one pass a side, and a centre
   starts from the rings its neighbours prove done. A checking build compared old and new fill order on every call
   (48 games at the real budget, 32k+ calls): same tiles, same order. Mean -2.6% at 100M.
2. **Our own record and gems read once between actions** (exact; campaign 16's unmerged `oc16-sc1`, re-done on 494):
   `self_acted()` before every engine call that changes them, and at every stale check once the round has moved on. A
   ward and a priority change neither, so they keep the cache. With it: closed-form `ranks_before`, an insertion sort
   for the unseen enemies' turns, `Tributing::gems` left unwritten. An oracle build compared every cached read with a
   fresh one: 0 mismatches at 100M over 192 games (own and test drafts). -475 fuel a turn, -640 on turns of 95k+.
3. **The turn's tail checks its fuel** (fuel-aware; identical at 100M). Under 5k left after decide's branch, each
   optional step (reveal, second strike search, heal and shield, end ward, lock, tribute habit) runs only if the fuel
   covers its least cost when it does anything plus the turn's end (1.0k at p99): a skipped step was idle or would have
   run the turn out. Under 0.8k the recall and the stun read (whose only reader, the turn order, already keeps its last
   rank this short) give way to the posts. `turn-end-short` is logged when a skipped step could have acted.
   Alone: out-of-fuel turns -6.7% (95% -10.9 to -2.1) of 1,280 games.
4. **Own ring radius 8 -> 4** (16 -> 8 while dead; queue only, identical at 100M). Warming a tile costs ~1.9k (sight
   mask 0.3-1.2k by terrain, two viewer windows ~0.75k, static window ~0.37k) and decide misses a table on 5% of heavy
   turns. Against radius 8 at 100M: radius 4 / 3 / 2 / none save 2.3 / 2.8 / 3.4 / 6.6% of all fuel and cost turns of
   95k+ 34 / 44 / 60 / 157 fuel. A turn's walk and dash end within 3.
5. **`escape_landings` works out a landing's danger only if its plan rank can still place it** (exact). -104 fuel on
   turns of 95k+.

## Tried and dropped

- A memo of `rank_turns`' inputs: +165 fuel a turn (+429 on heavy turns). The side marked stale each round by an unseen
  champion re-ranks rarely enough that the compare costs more than it saves.
- Removing the own ring: -6.6% mean, but 4 of 96 games differ at 100M and heavy turns cost 157 more.
- Not built: gates on a step's typical cost (the tail's second strike search costs 10k at the median once it acts, the
  tribute habit's `want_home` up to 20k: 3% of first out-of-fuel turns each). They would trade actions for turns.

## Open

- Tail steps that act with 2-8k left still run the turn out (second strike search, habit, casts).
- The turn order's 10k gate against `offer_heal` and `plain_priority` tails.
- A tile's warm-up is ~1.5k of our own instructions around 0.35k of shadow casts; the static window's incremental path
  measures ~370.

## Tools

`tools/` here (paths still point at `~/tmp-offload/fuelC/`, where the bench JSONs are): `b.sh` (bench.py runs: `id`, `td`, `real`, `p1`), `cmp.py` (paired real-budget comparison, bootstrap
over games), `heavy.py` (saving on identical 100M games by the base turn's fuel, and turns over 100k), `byfn.py` and
`top.py` (fuelprof profiles by function and line), `prof.sh` (the three-class profile), `oofphase.py`, `cenall.py`
(census: every label on turns that ran out). Real-budget out-of-fuel counts differ by ±5% between equivalent bots on
1,280 games (games diverge), ±2.5% on 4,096; `heavy.py`'s turns over 100k at 100M is the paired, noise-free proxy.
