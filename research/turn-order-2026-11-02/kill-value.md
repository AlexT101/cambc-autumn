# Kill execution: a kill-now value and bids only on reachable kills (`bots/variants/ast-kill*`, 2026-11-02)

The starting point is [follow-through.md](follow-through.md) "Where a gain would be". It names two leftovers:
- **`hit_worth` is order-free.** Damage short of a kill counts as banked progress toward a kill, though most of it
  never converts.
- **Kill bids use Strike's crow-flies reach.** 8% of unkept bids had no legal plan.

**Setup.**
- BASE is `bots/variants/ast-follow-v2`: astraeus 294, plus v1 (keep our own kill bid) and v2 (no kill bid while a
  channel runs past our next turn).
- Every A/B is against REF `bots/variants/astraeus-294`, both bots on their own drafts (`--no-test-draft`), on the
  fastrunner (native).
- Main: 10,240 games on fresh-86000..86019. Confirm: fresh-86020..86039 (10,238 games; 2 maps fewer).
- "Paired" is the difference from BASE on the same games (`scripts/paired.py`).
- `ast-kill2` and `ast-kill12` now hold the fixed reach check (section 3); their first runs used the earlier one.
- A/B run names: `kill-base`, `kill1-main`, `kill2-main` (first reach check), `kill12-main`, `kill1bx-main`,
  `kill2x-main`, `kill12bx-main`; confirm `follow-v2-conf`, `kill2-conf`, `kill1b-conf`, `kill12b-conf`.
- Traced runs: `kill-meas0`, `kill-meas1`, `kill-meas1bx`, `kill-meas2x`.

## Result

| Variant | Main vs REF | Paired vs BASE, main | Confirm vs REF | Paired vs BASE, confirm | Games changed (main) | Out-of-fuel turns vs BASE (main / confirm) |
|---|---|---|---|---|---|---|
| BASE `ast-follow-v2` | 50.7% | | 50.5% | | | 105,940 / 101,208 |
| 1a `ast-kill1`: partial damage x its conversion rate | 49.7% (48.8-50.7) | **-0.92** (-1.91..+0.08) | | | 2,692 | +2.6% |
| 1b `ast-kill1b`: a kill also takes back banked progress | 50.5% (49.5-51.4) | -0.20 (-0.69..+0.30) | 50.3% | -0.21 (-0.69..+0.28) | 676 | -1.5% / +1.3% |
| 2 `ast-kill2`: bid only on kills a real move reaches | 50.5% (49.6-51.5) | -0.11 (-0.24..+0.02) | 50.5% | +0.05 (-0.08..+0.18) | 47 | -0.1% / -0.3% |
| 1a + 2 (first reach check) `ast-kill12` | 49.9% | -0.78 (-1.77..+0.21) | | | 2,694 | +2.7% |
| 1b + 2 `ast-kill12b` | 50.5% | -0.20 (-0.70..+0.31) | 50.3% | -0.17 (-0.66..+0.33) | 696 | -1.8% / +1.2% |

Kills and deaths a game, CAND, on the main run's first 2,048 games (fresh-86000..86003, `scripts/kill_kd.py`;
paired with BASE on the same games):

| | kills | deaths | paired kills vs BASE | paired deaths vs BASE |
|---|---|---|---|---|
| BASE | 5.87 | 6.40 | | |
| 1a | 5.58 | 6.32 | **-0.29** (-0.56..-0.02) | -0.08 (-0.34..+0.18) |
| 1b | 5.82 | 6.40 | -0.06 (-0.22..+0.11) | +0.00 (-0.16..+0.16) |
| 2 | 5.84 | 6.42 | -0.03 (-0.07..+0.01) | +0.02 (-0.03..+0.07) |
| 1a + 2 (first) | 5.60 | 6.29 | -0.27 (-0.54..+0.00) | -0.11 (-0.37..+0.15) |
| 1b + 2 | 5.85 | 6.40 | -0.02 (-0.19..+0.14) | -0.00 (-0.17..+0.16) |

Out-of-fuel turns run ~10 a game in every variant.

- **Neither change moves the game.** Every variant but 1a is level with BASE on both suite sets.
- **1a is worse than BASE.** It makes the bot less engaged (section 2). It is not under 48.5%, but -0.92 paired with
  0.29 fewer kills a game.
- **1b is 1a's fix**: the same measured rates, applied only to kills. It is level: -0.2 paired on both sets (about
  -0.2 ± 0.35 over 20k).
- **2 does what it should and changes ~0.5% of games.** No-legal-plan bound turns fall 2.7% -> 1.2%. Its first
  version read bushes and wards wrong; the fix is level with it (-0.01 paired, 61 games differ).
- **No variant is a ship candidate on win rate.** 2 can ride along as a correctness fix: its fuel is level.

## 1. Measurement: does damage short of a kill convert? (`scripts/kill_convert.py`)

**Data.** Every champion turn that damaged an enemy champion and left it alive, off its spawn. It is 623k hits in the
2,048 REF self-play games of `replays/comms-meas-ex` (ast-comms-meas, astraeus 294 plus traces, against 294).

**Outcome.** Was the victim killed by the hitter's team before its health came back to full (spawn heal, recall,
Willow)? Followed for up to 60 rounds; "still hurt at 60" counts as not converted (8.6%).

| Health share left after the hit | 0-.1 | .1-.2 | .2-.3 | .3-.4 | .4-.5 | .5-.6 | .6-.7 | .7-.8 | .8-.9 | .9-1 |
|---|---|---|---|---|---|---|---|---|---|---|
| converted (killed before healing) | **69%** | 56% | 43% | 32% | 28% | 24% | 21% | 20% | 18% | 15% |
| converted within 3 rounds | 58% | 36% | 21% | 11% | 6% | 4% | 2% | 2% | 1% | 1% |
| healed to full first | 28% | 42% | 55% | 65% | 68% | 69% | 70% | 68% | 66% | 67% |

- **Over all partial hits, 27% convert.**
- **A stun from the same turn barely changes conversion**: 28.0% stunned against 26.6% not.
- **Who acted first doesn't either**: victim acted earlier in the round 26.9%, yet to act 26.3%.
- So the term is not limited to "enemies that act before our next hit". It applies to every partial hit off spawn.
- By victim: Marcella 20% and Vendetta 25% are hardest to finish; Cassi 44% and Prism 37% easiest.

The table is `converts(share)` in `combat/abilities.cc`, interpolated between tenth midpoints. No constant is tuned.

## 2. Change 1

### 1a (`ast-kill1`): partial progress counts by its conversion rate

`hit_worth` = chip (0.4 per point) + progress, where progress is the fall in `kill_distance`'s square-root term.

- **The rule.** At each leaf of the strike search, every foe left alive and hurt loses
  `(1 - converts(h_end / full)) x progress(h_start -> h_end)` (`Search::unconverted_now`).
- **Why at the leaf.** A kill later in the same turn takes back what its first hits lost: within a turn, order still
  doesn't matter.
- **Where else.** The unseen-target ground cast prices the same (`unconverted`).
- **Fuel.** One loop over the foes per node: at most 24 nodes a search.

**Traced** (`ast-kill-meas1` against `ast-kill-meas0`, the traced BASE; 2,048 games each on fresh-86056..86059):

| | BASE | 1a | 1b |
|---|---|---|---|
| searches offering a kill (unguarded end tile), a game | 5.32 | **4.92** | 5.18 |
| ... chosen plan killed an offered foe | 97.4% | **98.7%** | 98.5% |
| ... hit only foes it couldn't kill | 2.0% | 0.7% | 1.1% |
| bid-bound target killable -> killed | 99.9% | 99.9% | 99.9% |
| kill bids on acted targets, a game | 3.63 | 3.48 | 3.58 |

- **It does what it should, but there was little to fix.** BASE already takes an offered kill 97.4% of the time:
  v1's bid penalty forces the bid target's kill (99.9%).
- **The 73% "hit another" of follow-through.md is gone in BASE.** It was measured on 294, before v1. What is left
  is ~0.1 searches a game.
- **The cost is engagement.** Partial damage on a healthy target falls from ~0.83 to ~0.48 of a point. The search
  then weighs it against tile danger and `cast_cost`, so the bot strikes less:
  - searches offering a kill -7.5%;
  - kills -0.29 a game (-0.56..-0.02), deaths level;
  - out-of-fuel turns +2.6%.

### 1b (`ast-kill1b`): the same model, applied to kills only (the one fix)

- **The model.** Under it, a target left alive at h keeps the progress already dealt to it only with chance
  `converts(h)`. Killing it now makes that sure.
- **The rule.** A kill's worth is `kill_distance(h)` plus `(1 - converts(h / full)) x banked(h)`, where `banked(h)`
  is the progress from full health to h. Each foe gets it once, in `lose()`.
- **Partial damage keeps its old worth**, so non-kill plans are unchanged. Cassi & Issac keep the old value, since
  their partner bound sets their worth.
- **A low target is worth much more.** At 20% health the kill gains about +280 (of ~1,000).
- **Traced:** offered kills taken 98.5%. Kill-offering searches are 5.18 a game (-2.6%, against 1a's -7.5%).
- **A/B:** level (-0.20 and -0.21 paired); 6.6% of games change.

## 3. Change 2 (`ast-kill2`): bid only on kills a real move reaches

**The rule.** `real_distance` in `model/turn_order.cc` re-reads our next turn's Strike for the one or two offers
that would win the bid.

1. **Where a basic attack can be made from:** the tiles that reach and see the target (`attack_viewers`). Our own
   tile counts when we see the target now. Every tile in range counts when our ward sees it, as the strike search's
   `viewers()` rules.
2. **Which of those we can stand on, from our turn-end tile:**
   - a free neighbour (a walk);
   - a tile 2 or 3 king steps away by a dash path, if the dash is ready next round. The path crosses holes, altars
     and allies, but not walls, camps, visible enemies or the enemy spawn. One `reachable_tiles` call each.
3. **The cost:** the fewest moves (walk 1, dash 2, both 3) beyond what open ground needs. That is added to the
   distance, and Strike's blow is read there; past `max_reach` when none reaches.
4. **Damage spells skip the check.** A ready damage spell keeps the Chebyshev distance: its cast needs no move.

**Fuel.** Host board calls, and only for winning kill offers (~6 a game); no fuel gate. Out-of-fuel turns -0.1% and
-0.3%.

**First version.** It read viewers with `attack_viewers` alone, which leaves out bush viewers beyond a step and
ignores wards.
- Traced on BASE, it called 254 bids unreachable, and only 41% of those searched had no plan.
- In the cases inspected, a Vesper inside a bush cluster struck a target 3 away in the same cluster.
- The fix (the search's own two rules above): of 90 bids it flags on BASE's games, 80 had no plan (89%). It catches
  about half of all no-plan bound turns.

**Traced** (`ast-kill-meas2`, the fixed version, against `ast-kill-meas0`; same 2,048 games):

| bound turns, our search ran with the target still above the health to leave | BASE | change 2 |
|---|---|---|
| bound turns | 6,233 | 6,147 |
| **no legal keeping plan** (no plan on any end tile, guarded or not) | **169 (2.7%)** | **74 (1.2%)** |
| no keeping plan on an unguarded end tile | 176 (2.8%) | 81 (1.3%) |
| kill bids on acted targets, a game | 3.63 | 3.58 |

The remaining 1.2% were not broken down. Likely causes, none checked:
- blows short of 90% of the modelled one;
- tiles that change before our turn (allies moving);
- Strike combinations a tile set doesn't capture.

## Scripts

- `scripts/kill_convert.py EXTRACT_DIR [--team NAME]`: the conversion table (section 1).
- `scripts/kill_trace.py RUN...`: KV / FK / KB / KO lines of the traced `ast-kill-meas*` builds (sections 2-3).
- `scripts/kill_kd.py EXTRACT_DIR...`: kills and deaths a game, CAND and REF, paired between runs.
- Traced builds have `debug_search` off for the stdout cap. KO computes `real_distance` inside `debug_block` in
  builds that don't use it.

## Verdict and next

- **Don't retry 1a (discounting partial damage).** Lowering chip's worth against danger makes the bot passive.
- **1b is the defensible form of the kill-now term, and it is level.** The kill-vs-chip choice it targets is already
  ~98% right in BASE.
- **2 is a correct, cheap, level fix.** Merge it with v1/v2 if they ship, or drop it; it won't show in win rate.
- **Kill conversion is not a value problem.** Kills offered are taken. The gap to Fish and PBG is reach and
  engagement, as follow-through.md section 2 found: 37% of non-hitting turns near a low enemy are out of reach.
