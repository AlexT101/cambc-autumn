# Out-of-fuel anatomy: where the fuel goes, what the plan cuts, what it misses

Inputs: oof/anatomy b88794d batches (100 games, 3226 OOF turns, 84,884 turns over 60k), the reference side's SRCH lines in
the same replays (oof-int, debug_search on: 88k searches), the 100M bench (oof-int-ref-100m.json), and a scratch copy of
oof-int with extra `debug_block` timers in the search (8 games, 4 gen maps, both sides; free in local builds).
The raw data (analysis scripts, the probe bot, decoded replay metas) was session-local and is not kept.

## 1. Where the fuel goes

### Out-of-fuel turns that die in the search (1970 of 3226; 54% end in plan_strikes grow/price/act/read)

| | all | Heart of Ruin | Ren | Vendetta | Vesper Vale |
|---|---|---|---|---|---|
| before the search | 54.9k | 49.7k | 67.1k | 68.5k | 66.4k |
| want_home (decide or continue_recall) | 23.3k | 21.6k | 26.4k | 20.2k | 26.0k |
| step_guard | 16.5k | 12.7k | 26.8k | 36.1k | 28.3k |
| world | 9.6k | 9.6k | 9.4k | 8.0k | 9.1k |
| the search (read+grow+price+act) | 45.1k | 50.3k | 32.9k | 31.5k | 33.6k |
| of it grow | 26.9k | 32.9k | 13.9k | 13.5k | 11.0k |

So two different problems:
- **Dashers (Ren, Vendetta, Vesper, Issac):** step_guard's radius is 2 when a dash is ready, so its exposure loop looks at
  24 tiles (Reach::at ~1k a foe per new tile, then fight_key_with, then a sim per new key). 27-36k before the search starts.
- **Heart of Ruin:** the search itself. HoR is in 96 of the 100 games (test drafts), runs ~250 searches a game, and has
  20 OOF turns a game (Ren 8.5, Vendetta 11.5, Stellar 1.7). The searches that ran out mid-grow (195 on the reference
  side) had 2-4 foes, **35 nodes median (p90 54, max 117) and 71 offers (p90 134)**, against p99 18 nodes for its
  searches that finished.

Every turn also pays `world` (~10k) and want_home (~8-24k, mostly through continue_recall, because start_recall begins a
recall at every turn end so the next turn opens in continue_recall).

### Inside grow (probe, per-section self fuel; children excluded)

| | settle (offers) | dash branch | of it land groups | land_at | attack branch | reset+walk | spells |
|---|---|---|---|---|---|---|---|
| HoR, grow > 10k (125 searches, 19.5k mean, 13.8 nodes, 25.7 offers) | 47% | 31% | 15% | 6% | 11% (hit_unit 5%) | 4% | 1% |
| Ren, grow > 10k | 57% | 10% | 0 | 0 | 17% | 5% | 4% |
| Stellar, grow > 10k | 34% | 1% | 0 | 0 | 14% | 2% | 42% (ground centres) |
| all champions, all searches | 42-50% | 1-19% | | | 12-30% | 6-12% | 3-28% |

- The cost is a high constant, not a blow-up of duplicates: **~700-950 fuel a node on average, ~1.4k a node and ~360 an
  offer on big searches.** Settle alone is ~370 a node / ~390 an offer (Front::admit, Choice writes, leaf copy, wake_at).
- Transpositions are negligible: hashing every node's full state (seg, flags, req masks, lset, stunned, touched, healths)
  found duplicate states worth 0% of HoR's grow fuel and 0.3-4.8% for the others. **A transposition table is not worth it.**
- HoR's extra cost is its landing dash: each dash-capable node (start, and every walked node) rebuilds the landing
  classes (`hits != groups_hits` is almost always true, since `reach` differs per walk tile), then pushes one child per
  class, and each landing child's walk (dashed_walked) offers up to ~25 end tiles.
- wake/find_wakers are ~1% (camps rarely touched in these fights).

### Read and price (probe)

- read ~5k typical, 9.5k mean on OOF turns: read_geometry 34% (~1.7k of board ops: or/copy/and, camps_into,
  occupancy_into, two positions_into), the foe loop 31% (per foe: live()/is_visible/buffs/kept_recall host reads,
  stun_worth, turns_before_ours), read_spells 10% (31% on reads > 12k: damage_amount(e.live()) per slot per foe,
  find_centres, add_unseen).
- price ~3-4.5k typical, 7.8k on OOF turns: Reach blow queries 15% (36% on prices > 12k: first Reach::at on a tile, and
  the turn's first Reach::build when nothing earlier asked), goal_field 9%, strikers/camps setup 5%; the rest is the
  pricing loop itself (gather, factor, top() after each add).

### How far over

At 100M (gate-free), 742 of 93k bench turns exceed 100k: excess median 17k, p75 37k, p90 65k. Cutting ~20k from a heavy
turn removes about half of them; ~40k removes about three quarters.

## 2. What the plan cuts

| Wave item | Mechanism | Expected effect on OOF turns |
|---|---|---|
| W2-A/B/C/D lazy `guarded(q)` replacing step_guard | exposure + fight only for tiles actually asked: the search's winning candidates (~2-8 priced tiles, Reach::at shared with price's blow through the same 64-slot memo, which holds the whole 7x7 window without collisions) and route first steps (cap 8), instead of 8/24 tiles up front; dominance + memo for the fights | step_guard 16.5k -> ~4k (-12k avg; dashers -20k to -30k). The plan's biggest win and the main fix for the dashers. |
| W2-D want_home pursue skip | skip `pursuit` when the stand sim is won and covers every pursuer | pursuit is 3.0% of OOF fuel (12k when it runs, 25% of turns): -1k to -3k |
| W1-A tile table in lethal/damage_bound/threats_at | one unseen rule, no bisection | lethal self 1.8k -> ~1k: -1k |
| W1-B memo across invalidate, reobserve | sims after safety.refresh (post-attack chase/prey/carry_bag) and on ward turns hit the memo | little on OOF turns (chase 0.5%, place_ward ends 26 turns); more on big turns (chase 6.1%, carry_bag 3.4%) |
| W1-D shield_cap, camp_at -> tile().camp_exp | removes duplicate formulas | <0.5k: camp setup + shield are ~5% of price |
| W3 one search per turn | retreat/chase become pricing modes | **not a saving on these turns**: decide's search keeps its full read+grow; flee pricing and chase repricing add price passes (~4-8k each) on turns that already searched. With today's grow, the 4a +135% OOF risk stands; the W3 gate is right. |
| W4 | one shield/heal call, tribute_safe memo, turn-order gate | small (set_turn_order 2.4% of big turns) |

Plan total: about -15k on an average OOF turn that dies in the search (dashers -25k), mostly from W2.

## 3. What the plan misses

1. **grow: 21% of OOF fuel, 33k on HoR's OOF turns.** No wave changes grow's cost; W3 builds more pricing on top of it.
2. **read: 9.5%.** Geometry board ops and per-foe host reads, repeated by cast_at_enemies/strike_after on the same turn.
3. **world: 10% of every OOF turn, 14.5% of big turns** (update_champions 3.7/6.0%, camps 3.7/4.4%). Not in any wave.
4. **The sims themselves:** new_fight is 13.4% self at any depth. W2 dominance only helps when several keys are asked;
   the sim core (W5-A) is a stretch. Measure first with W1-B's MEMO/act-branch counters.
5. **farm and siege are victims, not causes:** 1.4% and 1.3% of OOF fuel; they end OOF turns because they run last.
   No fuel work there helps OOF turns. (farm's evaluation loop is 5.4% of big turns: a big-turn item only.)

## 4. Bounded, non-gating fixes (none overlaps W1's owners)

All but P5 are fuel-only: `bench.py compare` at 100M must show 16/16 identical replays, and SRCH-EXH/SRCH-DOM stay 0.

**P1. Deferred offers (grow's settle).** Owner: plan.cpp `Search::settle`, `Search::offer`, `Front`, the Tables fronts
(`best`, `kept`, `has`, `kept_has`), plus two new accessors `float Search::top(int c, bool keep)` and
`const Front& Search::front(int c, bool keep)`. Settle appends one record per leaf {ends Grid, v, removed, touched,
leaf, keep/heal flags, seg data for `mid`} instead of admitting into up to 49 fronts. `top(c)` = max over records
covering c of (v - wake_at cost), which is exactly today's `Front::top()` (admit never drops the maximum). `front(c)`
replays the records covering c in order through `admit`, so it is identical to today's front, and is built only for
tiles plan_strikes prices (2-8), the capped fallback (0.7% of searches) and the act-phase alternatives.
Expected: settle 45-50% of grow -> ~15%: **-30% of grow, about -8k on an average search-ending OOF turn, -10k on HoR's.**
Interface: plan_strikes' bound loop and `gather` must call top()/front() instead of reading `tables.kept`/`S.best`.
That is 4-6 lines inside W1-D's area, so pin the accessors in w1-iface (stubs return today's tables). P1 is also the
natural `Prepared` for W3: flee/chase modes re-score the same records instead of growing again.

**P2. Landing classes once per alive set.** Owner: plan.cpp `Search::grow`'s dash branch and the `groups_hits` /
`land_groups` members. Class every land_hits cell once by (land_foes & alive, land_touch); recompute only when `alive`
changes (a kill). Per node, `alike_i = class_i & hits`, ordered by the lowest set bit of `alike_i` so the push order and
`land_at`'s tile stay identical. Expected: land groups 15% -> ~2% of HoR's big grows: **-3k to -5k on HoR OOF turns**,
about 0 for others.

**P3. Walked-dash reach memo.** Same owner as P2: `reach` for a walked node (union of landings over
`free_n & s.req_w`) memoised for the last req_w (single entry, like `wake_at`). Expected ~3% of HoR's grow (~1k).

**P4. Static geometry window.** Owner: plan.cpp `Search::read_geometry`. Cache walls/holes/altars as a 7x7 Grid per
centre tile (terrain only, like `viewer_rows`); keep one `positions_into` of `blocked & box` and of the live
camps/enemy occupancy. Expected ~0.8-1k of read's ~1.7k geometry per search (-1k). W2-C deletes the guard OR in the
same function: land P4 inside W1's window and let W2-C rebase its one-line removal.

**P5. One per-turn enemy read table.** Owner: plan.cpp `Search::read`'s foe loop and `read_spells`, plus abilities.cpp's
enemy_cast reads (W4-B owns abilities.cpp only from wave 4). Read once per turn per visible enemy: stunned, kept recall,
`damage_amount(slot, e)` for both slots, stun_worth(e, damaging). Shared by the search, cast_at_enemies and strike_after.
Expected -0.5k to -1.5k on multi-foe turns. Byte-identical as long as nothing between the reads changes them (a cast
we make does: invalidate the table entries for the target after our own cast/attack).

**P6. Camp state from two boards.** Owner: world.cpp `update_camps` / `update_camp` (no wave owns it). Today each visible
member costs a `test(visible, m.pos)`, `camp_health` and `camp_awake` host call every turn. Use the `seen` positions
update_camps already lists for visibility per member, and `vision::awake_camp_tiles_into` /
`asleep_camp_tiles_into` (two board calls) for awake/asleep instead of one `camp_awake` per striker. Expected camps
3.7k -> ~2k: **-1.5k to -2k on every turn**, OOF and big alike. First add a debug_block check that the boards agree
with `sdk_camp_state` for every visible member (CAMP-AWAKE-MISMATCH); if they ever differ, confirm with a probe in
rules-verification before relying on it.

**P7. Name world's sub-phases first.** Owner: world.cpp `update_champion` / `track` / `fix` / `prune` (debug only). The
3.7-6.0% in update_champions has no inner Phase. Add markers, rerun oof_costs.py, then pick the fix
(e.g. lineage sharing already exists in track; the cost may be in prune or fix).

**P8 (low value). Slimmer Node.** Owner: plan.cpp `Node`. `pos` and `moved` serve only the debug enumerator; children
copy ~64 bytes at 1 fuel a byte, several times a node. A separate exhaustive node type saves ~2-3% of grow.

Not recommended: a transposition table in grow (duplicates are 0-5% of grow fuel); any node or offer cap that would
bind (it changes play, and P1-P3 reach the same place without one).

## 5. Expected combined effect

On an average OOF turn that dies in the search: plan W1-W2 about -15k, P1 -8k, P4 -1k, P5 -1k, P6 -2k: **about -27k**
(HoR: W2 -10k, P1 -10k, P2+P3 -5k, P6 -2k, P4/P5 -2k: about -29k; dashers mostly from W2). Against the 100M excess
distribution (median 17k, p75 37k), that would clear roughly 55-70% of today's OOF turns. These are estimates from the
probe's section shares; P1, P2, P4 and P6 are fuel-only, so each can be checked byte-identical on the bench and measured
with `oof_costs.py` before any A/B.

Order: P6 and P7 any time (world.cpp, no wave owner); P1-P4 in W1's window (plan.cpp search internals, not W1-D's
pricing), with P1's accessors pinned in w1-iface; P5 before W4-B. All before W3, whose gate needs the search to be
cheaper first.
