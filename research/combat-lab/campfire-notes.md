# cl2-campfire: camp fire in chases, and fleers luring pursuers (2026-11-08)

Idea 2 of cl2-log's read-only analysis. Base `variants/oc-cl2-base`; copy of `variants/cl2-belief`.

## Census (before coding)
2,000 games of `batch-20261108-192213-ab-cl2-ret-v1-cl2-dev` (cl2-ret v1 vs base, both ~ the base; extract in the
cl2 scratchpad `ex-v1`), script `scratchpad/cf/census.py`. The camp model was checked against every strong camp
attack (2.62M): the attacker is in a group awake at the end of the previous round, and its target is the nearest
champion in reach at the end of the previous round, 100% of both.

Flee episode as `ana/flee.py` (below 50% health, a step homeward, an enemy within 5; one per 15 rounds a champion):
24.5 a game a side. Pursuer = the fleer's nearest enemy; a *pursued phase* = a camp phase whose positions have the
pair within 4 (418k phases). Per game a side:

| | Elk | Golem | Monolith | Wolf |
|---|---|---|---|---|
| camp hits on the pursuer | 1.90 (91 dmg) | 0.24 (22) | 0.14 (19) | 2.63 (44) |
| camp hits on the fleer | 1.46 (72) | 0.18 (17) | 0.09 (12) | 2.04 (36) |
| episodes with the fleer in reach of an awake one | 1.68 | 0.24 | 0.18 | |
| episodes with the pursuer in reach | 1.71 | 0.24 | 0.18 | |
| (b) opportunities: pursuer within reach+1, fleer within reach+2 | 1.92 | 0.27 | 0.20 | |
| phases the pursuer was the nearest / the fleer / tied / a third champion | 1.26 / 0.94 / 0.65 / 6.13 | 0.17 / 0.11 / 0.10 / 0.60 | 0.08 / 0.06 / 0.05 / 0.50 | |

- Episodes with a pursuer camp hit: 1.95 a game a side (8%); fleer caught 24.3% (clean 26.8%), pursuer dead within
  20 rounds 14.4% (clean 8.6%). Deaths to strong camps with an enemy within 4: 0.09 a game a side.
- Any opportunity for (b): 2.4 episodes a game a side (> 0.5): (b) kept.
- The asymmetry is real but small: pursuers take ~30% more strong-camp damage than fleers (132 vs 101 a game side).

Who the pursuer was (600 debug games, base mirror, `D` trace of its turn before the hit, `attr.py`): of 1,105 strong
hits in pursued phases, the pursuer's last turn was farm 39%, chase 29%, retreat 20%, bank 4%; **96% were on a
pursuer already in that monster's reach the phase before** (entered: 42). Pursuers rarely walk into a camp: they
stand in a camp's reach (farming it, or fighting beside it) when a fleer passes. Over all turns (not only flee
episodes), chase-branch turns end in strong-camp fire 5.8 times a game a side (353 damage; entered 0.32).

## Mechanism
(a) Pursuer, `cl2-cf-a`:
- `chase()`'s walk: the route's equally short first steps (`Route::first_steps`, already found by the one search)
  are tried cheapest first by `camp_damage(q, false)` (find_members' nearest-champion assignment, others where they
  stand; maybe-awake groups at `unknown_camp_weight`). A new `Pathing::set_step_price` hook; no extra search, one
  camp lookup per first step, only when some member is awake.
- `prey()`: `chase_fire` = the least `camp_damage(q, false)` over here and the steps no farther from the target
  (≤ 9 lookups). `chase_trade(..., camp)` plays it on us each camp phase (`us.camp`, as `stand_trade` does) and is
  not memoised then. A lost plain fight stays skipped (camp fire only adds losses); a fired fight is not recorded.
- Not done: `new_fight` (memoised by roster, not tile; its callers' stands already add camps in `stand_trade`).

(b) Fleer (`cl2-campfire` = (a) + (b)): `Safety::lure_fire(p, e)`, for the nearest visible enemy within 5 yet to act:
it stays if it strikes p from its tile, else takes one of its closing steps, each alike; each live awake striker
hits it if it is strictly nearer than us and every other champion (ties counted for nobody), less twice the fire
its walk would move onto us. In `retreat_step`: off `avoid`, before the plain `step_towards(home, &avoid)`, a
homeward step off avoid with the most lure (> 0) is taken; in the ranked options, lure breaks ties after steps
home (before bush and gap).

## Second- and third-order effects
- **Our own farming.** Most chaser camp hits are on our farmers at their own awake camp. (a) steps a chaser out of
  that fire when an equal step exists, which leaves the camp to sleep sooner (2 empty phases) only if no ally stays;
  the trade term makes a farmer less willing to chase from inside its camp's reach: it keeps farming instead, which
  may be right (the enemy entering our camp's fire is lured by it).
- **Ties at the camp phase.** `camp_damage` (via find_members) uses turn order for others a step nearer; `lure_fire`
  counts a tie for nobody (conservative both ways).
- **Camp kills destroy gems.** A lure that kills the pursuer by camp loses its bag for both teams, where our kill would
  have taken it; the lure is a tie-break among steps equal for our escape, so it never trades our kill for it.
- **Chases given up that would have killed.** chase_trade plays the camp fire every simulated phase, an overestimate
  when the chase leaves the reach next turn. Debug, 600 games: 1.8 won chases a game turn lost by it. The main risk.
- **Fuel.** (a): ≤ 9 cached-member lookups per candidate target plus ≤ 8 per walk; a fired trade skips the roster
  memo (one more fight sim, ~10k, ~17 a game). (b): per option a loop over stirring groups' members.

## Round 1 results (cl2-dev, 20,480 games, `--no-test-draft`, fastrunner native, release)
| Arm | Win % (95% CI) | OOF CAND / REF |
|---|---|---|
| `cl2-cf-a`: (a) | 50.1 (49.4-50.8) | 206,533 / 205,110 (+0.7%) |
| `cl2-cf-ab`: (a)+(b) | 49.9 (49.2-50.6) | 218,923 / 206,020 (+6.3%) |

Debug firing (600 games, sub300 of cl2-dev): (a)'s walk takes another first step 2.5 times a game (41 fire saved
each); its trade turns a won chase lost 1.8 times a game; (b) lures 2.7 times a game (~40 expected fire on the
pursuer each). Kept replays (1,000 each, `paired.py`), a game, CAND / REF:
- (a): strong-camp damage with an enemy within 4: 1,226 / 1,302; on our pursuers 138 / 145; deaths 11.39 / 10.93.
- (a)+(b): the same 1,192 / 1,295; on pursuers 126 / 143. REF's pursuers took no more fire than in (a)'s games
  (143 vs 145): the lure, a tie-break among steps equal for the escape, lands too rarely to see.

Why level: the chase-into-camp pool is small. Chase-branch hits come with the nearest enemy 4-8 away (5.1 of 5.8 a
game side), on chasers already inside an awake camp's reach, mostly their own farm camp, which they would take
farming anyway; (a) trims ~6% of fight-time camp damage, a few tens of health a game. (b)'s +6% OOF is its member
loop per retreat option (every stirring group on the map, every option): dropped.

## Round 2 (`cl2-cf-r2` = (a) + enemy-side camp fire in fight sims; (b) dropped)
Strong-camp damage taken with an enemy within 4 runs ~1,100-1,300 a game per team, and the fight sims price none of
it on the enemy side (`Side::camp` is ours only). `Safety::enemy_fire(i)` (cached per turn, reset by invalidate):
the awake strikers whose reach visible enemy i stands in with every other champion (allies, us, other seen
enemies) at least two steps farther, summed (maybe-awake at `unknown_camp_weight`), for `reach - d + 1` camp
phases (it walking straight out), at most 3. `fire_on` sets it on `them` in new_fight, chase_trade and
stand_trade; `simulate` applies it after each of our turns (`hurt_by_fire`, through Durability), skips
`play_quiet` while any is set, and `decided`/`overwhelmed` add the most any one of theirs takes (`fire_bound`).
A/B running at handback: `replays/ab/cl2-cf-r2/summary.md` (log `scratchpad/cf/ab-r2.log`); debug firing count
`replays/ab/cf-dbg3` (CFFIRE lines).
