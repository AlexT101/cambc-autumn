# Fuel campaign 12, agent A: threats, combat and the recall decision (ocean)

Copy: `bots/variants/oc-fuel12-a` (oc-base13 plus the three changes below). Bench tags `a2` (change 1), `a3` (1-2), `a7` (1-3, final).

The kept changes are exact but small: -0.08% to -0.19% total fuel at 100M on every set, and 1.6-3.0% fewer turns over
100k. The OOF turns in my area are spread thin over code that earlier campaigns have already tuned: no single function
in my area takes more than ~5% of a heavy turn. Two changes that looked larger turned out dearer or no better and were
dropped (see "Tried and dropped").

## Kept changes

### 1. Pack zone: possible_box reads the chunk storage (a2)

- **File and function:** `combat/guard.cc`, `possible_box()`. It is called from `pack_members_of()` for each credible
  unseen enemy, while we are hurt, carry a big bag, or stand on our own ground.
- **Idea:** where the board is stored as one word per 8x8 chunk (`board_chunks_across(map) > 0`), the bounding box of
  `possible & ~near_enemy_spawn` is read from the chunks that `e.possible_box` covers. Each chunk's columns are OR-folded
  and its rows found with countr_zero/countl_zero. Before, `positions_into` listed up to 338 tiles into a `Tiles<338>`.
- **Why it is exact:** a credible enemy has at most 2 x 13² = 338 possible tiles (`unseen_weight`'s cutoff), so the old
  listing never truncated and its box is the box of the whole set. `possible_box` holds `possible`.
  - Board shifts can leave stray bits past the map's width and height. No listing holds those bits, so each chunk is
    masked to the map's columns and rows. The first version, without the mask, gave 951 mismatches.
  - A debug cross-check against a full `Tiles<1000>` listing gave 0 mismatches over ~2.4k checks on the heavy set.
  - Maps without chunk storage keep the old path.

### 2. turns_before_ours is computed once per threat (a3)

- **Files and functions:** `model/safety.cc` (`threat_strike`, `moved_strike`, `enemy_blow_repeats`,
  `Safety::strike_foe`), `model/safety.h` (`Safety::blow_repeats`) and `model/turn_order.cc` (`danger`'s blow sum,
  `offer_escape`).
- **Idea:** `Safety::strike_foe` used to call `turns_before_ours` up to three times per enemy. `threat_strike` called it
  twice and `enemy_blow_repeats` once, and each call costs ~94 plus `enemy_turn_before_ours_next`. Internal overloads now
  take an `int& turns` (-1 until needed), and `strike_foe` threads one value through both. The public signatures are
  unchanged and wrap the overloads.
  - turn_order's two `enemy_blow_repeats(world, e)` calls read `safety.blow_repeats(e)` instead, which is
    `struck(e).repeats`, already computed by the `strike_of` or `threats_at` just before.
- **Why it is exact:** `turns_before_ours` is a pure function of the belief, the round and the turn windows. Its memos
  (windows, second sets) are idempotent, and nothing between the calls changes those inputs.
  - Safety's `Foe.repeats` is fixed for Safety's life. Every belief change during a turn rebuilds Safety:
    - `see_again`, after `World::observe`;
    - `see_stuns` and `see_kills`, after `World::read_stuns`.
  - `note_sighting` runs in comms receive, before Safety exists.

### 3. Reach builds reuse the threat's turns_before_ours (a7)

- **Files and functions:** `model/safety.h` (`Safety::Foe::turns`) and `model/safety.cc` (`Safety::strike_foe`,
  `Safety::build_reach`).
- **Idea:** `strike_foe` keeps its `turns` in `Foe`. `build_reach` takes `struck(e)` and passes `x.turns` (computed
  there only if still -1) instead of calling `turns_before_ours` again.
- **Why it is exact:** same as change 2. Every `reach_of` caller has already called `struck(e)`, so pulling it into
  `build_reach` only moves memo work.

## Identity at 100M (a7 against base-<set>-100M.json)

`bench.py compare`: identical replays on all six sets (16/16, 52/52, 128/128, 32/32, 50/50, 64/64). a2 and a3 are also
identical on all six.

| Set | Total fuel | Mean | p90 | p99 | Max | Turns over 100k | Round 1 mean |
|---|---|---|---|---|---|---|---|
| def | -0.09% | 53206 → 53159 | 86591 → 86581 | 99626 → 99422 | 219512 → 217829 | 776 → 768 | +0.0% |
| wide | -0.13% | 51856 → 51790 | 86471 → 86458 | 107211 → 106832 | 286819 → 285894 | 3986 → 3909 | +0.0% |
| pool | -0.19% | 55825 → 55717 | 87140 → 87121 | 111592 → 111028 | 374122 → 374122 | 12363 → 11991 (-3.0%) | -0.0% |
| big | -0.08% | 63950 → 63901 | 87683 → 87671 | 105831 → 105633 | 321720 → 321894 | 2804 → 2760 (-1.6%) | +0.0% |
| heavy | -0.16% | 52854 → 52771 | 87286 → 87270 | 119834 → 119514 | 341265 → 341265 | 7068 → 6942 (-1.8%) | +0.0% |
| td | -0.16% | 55378 → 55287 | 86984 → 86964 | 104380 → 103924 | 242519 → 240243 | 3760 → 3670 (-2.4%) | +0.0% |

How the stages added up:
- a2 (change 1 alone): -0.01% to -0.03%.
- a3: -0.04% to -0.10%, and 0.9-1.3% fewer turns over 100k.
- a7: the table above.

Builds of identical code move by about ±0.03-0.05% with code layout, so a single step that small is not resolved.

Coverage:
- Change 1 runs on every hurt or own-ground turn with a credible unseen enemy. The debug run counted ~2.4k checks on
  heavy.
- Changes 2 and 3 run on every turn that builds a threat (every turn with an enemy in sight or credible). Neither has a
  branch tied to a champion, emblem or map class.

## Real budget (benches diverge: direction only)

| Set | OOF play turns (base → a7) | step-guard-entry | turn-order | farm-partial-evaluation |
|---|---|---|---|---|
| pool | 855 → 1030 (turns 603k → 617k) | 10645 → 12479 | 2244 → 2572 | 19368 → 20156 |
| big | 317 → 341 | 1088 → 1206 | 643 → 690 | 8483 → 8531 |
| heavy | 790 → 663 | 3939 → 3981 | 1490 → 1361 | 10657 → 10388 |
| td | 393 → 314 | 4510 → 4417 | 1111 → 1004 | 7316 → 6931 |

- Summed: 2355 → 2348 OOF turns.
- These sets diverge after the first fuel-dependent choice. At this size they can't resolve the ~2% fall in the 100M
  over-100k counts: pool rose and heavy and td fell with the same code.

## A/B

`ab.py variants/oc-fuel12-a variants/oc-base13 --no-test-draft --suites maps/suites/merged/fc12-a`. The suite was made
by `mksuite.sh fc12-a 910000 910019` (5120 maps, 10,240 games), and results are in `replays/ab/fc12-a-final/`.

- **Win rate:** CAND 50.0% of 10,240 (5123-5117), 95% CI 49.1-51.0: level, as an exact change should be.
- **Failures:** 0 failed matches and 0 broken draft handoffs. Capped drafts: 74 games on each side.
- **OOF play turns:** CAND 75,444 in 7,360 games, REF 79,374 in 7,446 games: -5.0%.
- **Shortcuts by kind** (REF → CAND, from the replays' SHORTCUT lines):

  | Shortcut | REF | CAND | Change |
  |---|---|---|---|
  | farm-partial-evaluation | 1,370,886 | 1,356,576 | -1.0% |
  | step-guard-entry | 819,712 | 806,893 | -1.6% |
  | prey-cut-short | 207,559 | 201,696 | -2.8% |
  | turn-order | 182,412 | 175,532 | -3.8% |
  | step-guard-look | 95,266 | 94,186 | -1.1% |
  | out-of-fuel | 79,374 | 75,444 | -5.0% |
  | comms-stale-vision | 64,738 | 61,238 | -5.4% |
  | farm-no-route | 29,780 | 29,472 | -1.0% |
  | static-descend | 25,604 | 24,440 | -4.5% |
  | ward-no-bushes-clusters | 23,111 | 23,137 | +0.1% |
  | crow-flies-farm | 14,002 | 14,075 | +0.5% |
  | step-guard-sim | 8,291 | 7,925 | -4.4% |
  | siege-route-fuel | 4,397 | 4,246 | -3.4% |

- **Reading:** the drop in OOF is larger than the 100M over-100k proxy (-1.6% to -3.0%), but within the same order.
  The fuel-checked shortcuts fall by 1-5%, consistent with ~0.2% less fuel on the turns in this area.

## Measurements (oc-base13, real budget, census)

Pool and heavy census games (`instrument.py --trace`, plus my own scopes; `cen2.sh`) give the per-turn means below on
OOF turns.
- **Unchecked OOF turns:** 68% of OOF turns pass no fuel check at all. They are fight turns, so any cost cut in this area
  reaches OOF directly.
- **OOF turns with the strike search (~80% of all OOF):**

  | Item | Per OOF turn |
  |---|---|
  | `strike_search` | 34-38k incl. |
  | `sp.loop` (pricing) | 12k incl., 6.3-7.0k self |
  | `sp.grow` | 9.2k incl., 4.2-4.7k self |
  | `sp.read` | 10k incl. |
  | `sr.foes` within `sp.read` | 3.9k, of which `viewers` ~1.7k and `partner_bound` ~1.7k where linked |
  | `ss.geometry` | 2.1k |
  | `sp.prep` | 4.5k |
  | `sp.offer` | 3.2k |
  | `sp.settle` | 3.8k |

  A search over 1 foe with 0-3 nodes still costs ~13.7k: the fixed overhead is large.
- **want_home:**
  - `wh.stand_lost`: 22-33k incl.
  - `s.new_fight`: 13-17k incl. and 7.5-12.7k self, about one sim a turn.
  - `s.stand`: 13-16k incl.
  - `wh.outmatched`: 2-4k.
  - continue_recall's `want_home` runs on almost every turn, because of the turn-end recall feint.
- **Retreat turns** (26% of OOF turns): `retreat` 37k incl.
  - `retreat_step` 27k:
    - `rs.add` (tally of 8 steps) 9.5k;
    - `HomeWalk` 7.3k;
    - `avoid_within`/`avoid` 6.5k.
  - `dash_away` 15k where present.
- **Fight-hash test:** 41,707 sims on heavy at 100M. Only 11% repeat an earlier turn's exact fight and 0.6% repeat
  within a turn, so caching fights across turns cannot pay.
- **Reach builds** (heavy, 100M, 60k builds):
  - 68% have a camp in their set radius (`sets_reusable_` false).
  - 29% have no camp but a new origin or allies.
  - 4% reuse their tile sets.
  - The same enemy is rebuilt within one turn and observation only 0.3% of the time. Rebuilds after `see_again`
    therefore aren't the cost; first builds each turn are.

## Tried and dropped

- **fuel11-1's turn_window port (a1: input-kept windows, closed-form `ranks_before`, insertion sort, vectorize-disable
  pragmas):**
  - Mean +0.2 to +0.4% on all sets: dearer.
  - Pool: gen-classic-51903901008 side a differed.
- **Windows kept across observations with unchanged reads (a5):** `current()` kept the windows and second sets when an
  observation left every input unchanged:
  - each enemy's alive, visible, acted, tracked, priority_round == round, pos, next_priority, strength and handle;
  - `enemy_priorities_change`;
  - the windows' origin tile.

  The result was +0.25% on every set, because the fingerprint is written at every build and the round's first build
  can't be kept. Mid-turn observations that change nothing are rare. Pool's gen-classic-51903901008 side a differed
  again, as with a1. Every windows change so far has moved that game: it looks fuel-sensitive (a decision that reads
  measured fuel), but I did not trace it.
- **Per-origin camp member lists for Reach builds (a4, a6):** each origin's window camp tiles are listed once with
  group, member, ring and bush (sorted by ring in a6), in place of the per-bit `camp_tile` and `live_member` loop. It was
  identical, but no better than the layout noise (heavy -0.11% at a4 and -0.08% at a6, against -0.10% at a3).
  - Fuel markers had put the camp loop at ~725 a build. The markers inflate small phases, and the real loop was much
    cheaper. Dropped as complexity without a measurable gain.
- **Act unrolled for 2 or 3 fighters:** not retried; campaign 7 measured it dearer (+3-4%).
- **Fight caching across turns:** not built (fight-hash test above).

## Merge notes

- **Files touched:** `combat/guard.cc`, `model/safety.cc`, `model/safety.h`, `model/turn_order.cc`, all in my area.
  Nothing in agent B's area changed.
- **Interface additions:**
  - `Safety::blow_repeats(e)`, public and inline;
  - `Safety::Foe::turns`.
- **New internal overloads:** `threat_strike(world, c, int&)` and `enemy_blow_repeats(world, e, int&)` sit in an
  anonymous namespace in safety.cc, with the public signatures unchanged.
- **Interactions:**
  - None with b1 (`economy/capture.cc`). ocean now carries b1 (2ae9204b8, CHANGES 452), and my four files are
    unchanged there since oc-base13, so they copy over as they are.
  - Anything that edits beliefs mid-turn without rebuilding Safety would break the `Foe.repeats`/`Foe.turns` reuse.
    Today nothing does: `see_again`, `see_stuns` and `see_kills` all rebuild.
- **Divergences:** none at 100M on the six sets.
- **Debug copies made and deleted:** oc-fuel12-adev, -acen, -acent, -afh, -aprof, -adbg. Census games are under
  `/home/ubuntu/tmp-offload/fc12a/cen/`.
