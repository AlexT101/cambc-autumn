# Fish: tactics against enemy champions beyond the fight rules (2026-11-05)

This report covers how Intercontinental Fish acts around enemy champions, beyond COMBAT.md's
engage, chase and spell rules. It covers dashes, enemy channels, gem carriers, contested
captures, its own spawn and respawns. Which camp group Fish targets is deliberately not studied.

Results:

- **Four rules hold on held-out data:**
  - spell targets weigh carried gems;
  - escape-dash landings;
  - Heart of Ruin's stun-dash landing;
  - Fish never leaves its spawn short of full health.
- **Two overrides are quantified:** Fish dashes in when a dash gives a kill, and it holds a running capture against danger.
- **Three hypotheses are refuted:**
  - Fish does not prioritise interrupting enemy channels, and engages recalling enemies less;
  - basic attacks ignore gems;
  - the engage and escape dash *decisions* follow no health/danger threshold.

No bot source changed.

## Data, split and definitions

- **Fit cohorts:** `model` 124, `confirm` 96, `third` 43 and `fourth` 46 games (309).
- **Held out:** `fifth` 94 and `sixth` 53 games (147, 31 match groups).
- Every rule, threshold and constant below was chosen on the fit cohorts. The held-out cohorts were then scored once.
- Earlier studies had decoded and used the held-out cohorts (COMBAT.md, FARM-CHOICE.md), but not for any label studied here.
- Two disclosures:
  - The spawn health rule (section 5) was first seen in a table pooled over all six cohorts.
  - The dash kill override (section 1) was first seen in a fit-plus-held table.
- Counts are correlated turns, not independent trials.

All features come from the actor's own perspectives in the existing caches:

- turn start, and each attack/cast's own before-state;
- dash casts are `Cast ability` with ability type 6, and have before-states;
- enemy channel type and timer are visible fields.

No raw replay re-decode was needed. Rows: `tools/fish/tactic_rows.py` →
`replays/fish-tactics/<cohort>-tactic-v3.jsonl.gz` (earlier v1/v2 lacked fields and were deleted).

Terms used below:

- **Danger(tile)** is COMBAT.md's: the sum of visible, unstunned enemies' one-turn damage reach at that tile, divided by own HP + shield. It is Chebyshev and ignores terrain and items.
- **Acceptable** is COMBAT.md's rule: a kill is available, or (hp/max > 0.49 and danger ≤ 0.28).
- **Dash landings** are computed from public terrain plus units visible before the dash (rules `abilities.dash`):
  - a path of at most 2 king steps, not through walls, the enemy spawn, visible enemies or visible live camps;
  - landing on a free tile that is not a hole or altar.
  - All **93,357** observed dash landings (six cohorts) are in this set.
- **Random-landing baseline** is the expected accuracy of a uniformly random legal landing.

## 1. Dashes

About 75% of dashes (77,809 of 93,357) happen with no enemy within 6 (travel). Classes with an enemy within 6 (all cohorts):

| | engage | escape | other |
| --- | ---: | ---: | ---: |
| Heart of Ruin | 2,927 | 1,537 | 634 |
| Vendetta | 1,245 | 1,444 | 1,745 |
| Issac | 975 | 1,452 | 1,555 |
| Vesper Vale | 803 | 647 | 398 |
| Ren | 34 | 114 | 38 |

- **engage:** a visible enemy is hit later that turn. For Heart of Ruin the landing hit counts.
- **escape:** no hit, and the landing is farther from every visible enemy than the pre-dash nearest distance.

Dashes come first in the turn. Melee dashes are dash, walk, attack; Heart of Ruin's are walk, dash, attack.

### Landing tiles

| Rule (meaningful subset: the key differs among legal landings) | Fit | **Held out** (fifth / sixth) | Random landing, held |
| --- | ---: | ---: | ---: |
| **Heart of Ruin engage dash: lands where the most visible enemies are within 1** | 1,970/2,030 (97.0%) | **882/896 (98.4%)**: 487/493, 395/403 | 15.9% |
| **Escape dash: lands on a minimum-danger tile** | 3,332/3,476 (95.9%) | **1,158/1,196 (96.8%)**: 818/841, 340/355 | 46.6%; 79.0% among landings farther than the nearest enemy |
| Escape dash: farthest from the nearest enemy | 3,391/3,859 (87.9%) | 1,186/1,335 (88.8%) | 24.2%; 48.8% among farther |
| Escape dash: nearer home than before | 2,812/3,859 (72.9%) | 944/1,335 (70.7%) | 37.6%; 52.5% among farther |
| Engage dash: minimum danger among landings that reach the target | 579/996 (58.1%) | 201/328 (61.3%) | 50.1% |

- **Escapes.** Fish minimises the danger sum first; going home is secondary.
- **Per group.** Heart of Ruin beats random in 30/30 held-out groups, and escapes in 30/31.
- **Exact tile is not recovered.** The best lexicographic orders searched on fit get only 35-47% held out. Examples: Heart of Ruin `-adj, -y, -x`; escapes `-nearest-distance, home, y`.
- Engage landings always leave the target within reach (1,772/1,773). The class definition forces that, so it is not evidence.
- Counterexamples:
  - Heart of Ruin: `7c1f57ac42b47857` r67 actor 7; `9ee661b46521ffa8` r559 actor 7 (one enemy hit where 2 were possible).
  - Escape: `48c80d034e7941c0` r582 actor 4; `2c62f05a98d0a2ae` r43 actor 1.

### When to dash in: only the kill override is a rule

An **engage opportunity** is a turn where:

- the dash is ready, Fish is off spawn and not channelling a tribute or teleport;
- the nearest enemy is out of walk-and-hit reach but inside dash reach: melee at 3-4, Vesper at 4-5, Heart of Ruin at 2-3.

The label is whether Fish dashes and hits that turn.

| | Fit | Held out (fifth / sixth) |
| --- | ---: | ---: |
| **A landing tile gives a kill → dashes in** (kill: basic Strength within reach, plus Heart of Ruin's 1.5×Focus within 1) | 210/220 (95.5%) | **111/126 (88.1%)**: 55/63, 56/63; never-dash 11.9% |
| No kill, hp > 0.49, danger ≤ 0.28 at a reaching landing → dashes in | 2,149/11,745 (18.3%) | 905/3,466 (26.1%) |
| COMBAT's 0.49/0.28 rule as the whole decision | 46.2% | 48.9% (majority, never dash: 78.4%) |
| Best grid fit (h, z) | 85.6% (majority 85.3%) | 78.5% (78.4%) |

- With a dash kill on offer, Fish takes it; this is COMBAT's kill override extended by the dash.
- Otherwise Fish dashes in on only 18-26% of healthy, low-danger opportunities, so the positioning thresholds do not transfer.
- Kill-override per group: beats never-dash in 23 of 27 held-out groups, with 3 ties.
- Counterexamples: `0598b0f10f535534` r790-791 actor 7 (Heart of Ruin); `4d87bb1b586ab995` r215 actor 7.

**Escape decision: refuted as a threshold.** Opportunity: dash ready, enemy within 3, off spawn.

- No (hp, danger) grid rule beats never-escape: held out 4,809/5,200 (92.5%), the same as the baseline.
- Escape rate rises from about 3% at full health to 20-30% below 20% health, but never becomes the majority.

**Travel dashes are not "whenever ready".** On no-enemy moving turns with the dash ready, Fish dashes on 27-35%. The rate is flat in the distance to where it next stops (first 60 `model` games, a scratch check, not saved). Not pursued further, as that concerns destinations.

## 2. Enemy channels: no interruption priority

Script: `tactic_channel.py`. It uses COMBAT's contact caches, so idle enemies give the comparison.

- **Hit rate.** Every visible enemy that Fish's one-turn damage can reach, Fish off spawn. Label: that enemy is hit this turn.

  | Enemy at Fish's turn start | Fit | **Held out** |
  | --- | ---: | ---: |
  | not channelling | 21,117/39,374 (53.6%) | **9,800/17,508 (56.0%)** |
  | recall, timer 4 (started this round) | 21,344/68,529 (31.1%) | 6,734/16,769 (40.2%) |
  | recall, timer ≤ 3 (kept at least a turn) | 1,252/3,864 (32.4%) | 432/1,172 (36.9%) |
  | tribute | 273/632 (43.2%) | 166/342 (48.5%) |
  | teleport | 10/24 | 19/38 |

  The recalling-enemy deficit holds at each distance and own-health band (in the JSON).

- **Positioning.** COMBAT's contexts, split by whether the nearest enemy is recalling.

  | Held out, engage rate where COMBAT's rule says engage | nearest not recalling | nearest recalling |
  | --- | ---: | ---: |
  | m1, adjacent melee stays adjacent | 2,521/2,901 (86.9%) | 834/1,239 (67.3%) |
  | r, ranged holds its distance | 1,847/2,180 (84.7%) | 1,069/1,585 (67.4%) |
  | m2, melee one step out | 1,539/2,054 (74.9%) | 1,437/1,932 (74.4%) |

  Fit shows the same pattern (81.8% / 66.2%, 78.9% / 62.4%, 68.5% / 68.0%). Fish does not hunt recalls; it lets adjacent or in-range recallers go more often.

- **Target choice.** Basic attacks with mixed channelling and non-channelling candidates:
  - "channellers first" gets 186/801 held out (23.2%);
  - min HP + shield gets 743/801 (92.8%).
- **Stuns.** With a stun ready and an eligible enemy within 4, tributers are stunned at the same rate as anyone else: 16/86 (18.6%) against 1,617/8,581 (18.8%) held out. Stunning is the only way to cancel a tribute short of a kill.
  - Cassi's "tributers first" variant equals the max-Strength rule (74/86 and 27/31 held out).
  - Only 7 fit cases have an eligible tributer at all.

## 3. Gem carriers: spells weigh gems, basic attacks do not

Script: `tactic_target.py`. Rows: each attack or unit spell, from its own before-state, with every visible enemy in range. Meaningful choice: 2 or more candidates.

**Unit damage spells** (ability type 2: Cassi slot 0, Marcella slot 1; the other casters are too rare):

```text
target = argmax over visible enemies in range 4 of (gems + 8) / (HP + shield), lower id on ties
```

`8` is the fit-grid optimum: 1,317 at a = 8, 1,308 at 12, 1,299 at 5, and 1,123 for min EHP.

| | Fit | **Held out** (fifth / sixth) | min (HP + shield) baseline, held |
| --- | ---: | ---: | ---: |
| All multi-target spells | 1,317/1,428 (92.2%) | **423/462 (91.6%)**: 277/305, 146/157 | 362 (78.3%) |
| Gem counts differ among candidates | 689/765 | 217/240 (90.4%) | 65.0% |
| A carrier other than the min-EHP enemy carries more | 390/466 | 111/134 (82.8%) | 37.3% |
| Kill-first (damage = 2×Focus ≥ EHP), then the ratio | 1,348/1,428 (94.4%) | 425/462 (92.0%) | |
| Max gems, then min EHP | 83.3% | 392/462 (84.9%) | |

- By caster, held out: Cassi 108/116 (93.1%), Marcella 315/346 (91.0%).
- Per held-out group: better than min-EHP in 22 of 31, tied in 8, worse in 1.
- Counterexamples:
  - `48895b3d7b550c6a` r418 actor 6: Marcella picks Vesper (920) over Issac (900), neither carrying.
  - `ea2d323847aa1899` r479 actor 0: Issac (399) over Cassi (340). Killing either Cassi & Issac body kills both, so these may count the pair.

**Basic attacks ignore gems and channels.** min (HP + shield, id) stays best:

- held out 1,969/2,085 (94.4%);
- `(gems + 8)/EHP` 80.0%;
- carriers first 76.5%;
- channellers first 67.7%.

Fish's spell targeting is the gem-aware part. This is likely why CONTINUATION.md found min-EHP weak for Cassi and Marcella damage casts.

**Kill-stealing** was not separable: who lands the last hit cannot be told from intent with these labels.

## 4. Captures with enemies near

Script: `tactic_capture.py`. Rows: Fish within 3 of an empty group, a visible enemy within 8, completed turn, not channelling a tribute or teleport. Capture state is the actor's own read: `captureTeam` = our side, or 2 = contested; timer = rounds to payout.

| Context, label | Fit | **Held out** | Baseline, held |
| --- | ---: | ---: | ---: |
| **Hold** (on the group, no enemy on it): stays, when its own tile is *unacceptable* | 647/848 (76.3%) | **197/264 (74.6%)**: 127/173, 70/91 | leave 27.3% |
| Hold, all: rule "stay unless timer is 5 or none and unacceptable at h 0.45 / z 0.40" | 10,120/11,358 (89.1%) | 3,742/4,195 (89.2%) | always stay 89.1% |
| Hold, all: COMBAT acceptable only | 85.3% | 3,617/4,195 (86.2%) | 89.1% |
| **Contested** (Fish and an enemy on the group): stays iff acceptable (h 0.45, any danger) | 848/1,105 | 310/390 (79.5%) | always stay 76.7% |
| **Enemy-held group 1 tile away**, no ally on it: never steps on | 545/677 (80.5%) | 195/245 (79.6%) | (same rule) |

- **Holds.** A running capture overrides COMBAT's retreat line.
  - In COMBAT's own contexts, Fish engages on only 20-50% of the turns the rule calls unacceptable (fit; `tactic-channel.json`).
  - On a hold with the timer at 1-4, Fish stays in 714 of 891 unacceptable turns over all cohorts (80%).
  - With the timer at 5 or none, it stays in 112 of 221 (51%).
  - The rule only explains staying: holds are left 11% of the time for reasons outside these features (holder hand-offs, CONTINUATION.md).
- **Contests.** Fish fights the holder: it hits an enemy standing on the group in 615 of the 780 turns where that enemy is in its reach (79%, all cohorts).
- **Enemy-held groups beside Fish.** Fish hits the holder (488/922) far more often than it steps onto a free tile (182/841).
- Counterexamples: `7112b50eb5ac8cc2` r100 actor 0 (Marcella leaves an acceptable hold); `fe5675fd7c40fa51` r98 actor 2 (Heart of Ruin steps onto an enemy-held group).

## 5. Own spawn and respawns

Script: `tactic_spawn.py`. Rows: alive turn start on Fish's spawn, completed, not channelling, an off-spawn neighbour free. Label `left`: the turn ends off the spawn. ehd = distance from the nearest visible enemy to Fish's spawn.

| Rule | Fit | **Held out** (fifth / sixth) |
| --- | ---: | ---: |
| **Short of full health on spawn → stays** (with or without enemies) | 12,868/12,940 (99.4%) | **10,640/10,672 (99.7%)**: 6,938/6,966, 3,702/3,706 |
| With an enemy within 10: leave iff none within 7 of the spawn and at full health | 4,182/6,335 (66.0%) | 839/1,374 (61.1%); never-leave 53.4% |

- **Health.** On its spawn Fish heals to full at turn end, so it waits that turn out. Examples: after a recall arrival, or when hit from outside.
  - Exceptions: `753fe1f7c083280c` r1042-1048 actor 4 (Heart of Ruin at 67%); `1674051a0f1bdce8` r199 actor 3 (Issac at 2%).
- **Enemies near the spawn** keep Fish in, without a clean threshold.
  - Leave rate over all these spawn rows, all cohorts, by ehd 1 to 8: 24%, 23%, 26%, 34%, 39%, 48%, 46%, 65%.
  - With no visible enemy: 25,981/57,670 (45%).
- **Fighting from the spawn.** With an enemy in reach, Fish hits in 657/1,363 turns, and in 543 of those it stays on the spawn.
- **Respawns.** In the first 3 turns after a respawn with an enemy within 10 (344 turns), Fish leaves on 190 and hits on 23. In 273 of these an enemy is within 7 of the spawn, and Fish still leaves on 132. There is no special post-respawn caution beyond the general spawn behaviour.
- **Spawn camping by Fish** is rare: 100 of 17,392 held-out basics hit an enemy on its own spawn.

## Not done

- Bush ambush and ward vision in fights were not studied.
- Which group Fish targets was excluded by request.
- Kill-stealing (section 3) could not be separated.

## Compared with astraeus

- **Spell targets.**
  - astraeus scores every hit, basic or spell, by `hit_worth_of` (`combat/abilities.cc`): kill distance with the bag valued at `gem_value × gems`.
  - Fish splits the two: basics go to min EHP, unit damage spells to `(gems + 8)/EHP`.
- **Channels.**
  - astraeus adds `recall_value` to non-lethal hits on a kept recall, and prices stun cancels of tributes (`stun_worth`, `kill_stops`).
  - Fish shows neither: it hits recallers less, and stuns tributers at the base rate.
- **Escape dash.**
  - astraeus `dash_away(..., pathing.to_ally_spawn(), ...)` (`combat/fight.cc`) dashes homeward.
  - Fish lands on the lowest-danger tile (96.8%); homeward is only 70.7%, against 52.5% for a random farther tile.
- **Heart of Ruin's stun-dash.** Fish maximises the enemies within 1 of the landing (98.4%). astraeus's area cast scores members by damage and stun worth, which usually means the same.
- **Dash to kill.** Both do it: astraeus `dash_to_attack` and the sure-kill dash in `fight.cc`; Fish 88% held out.
- **Holding a capture.** astraeus `hold_outlasts` (`combat/guard.cc`) steps onto a hold only when it outlasts the strikes. Fish simply keeps a running hold (timer ≤ 4) against danger.
- **Spawn health.** astraeus `mend` (`bot.cc`) also stays on spawn while missing health, unless camp fire reaches it. Same rule.

## Reproduce

```sh
export PYTHONPATH=tools/fish R=research/fish-2026-11-05
for c in model confirm third fourth fifth sixth; do python3 tools/fish/tactic_rows.py $c --jobs 6; done
python3 tools/fish/tactic_dash.py $R/tactic-dash.json            # exact-tile search and decision grids (~10 min)
python3 tools/fish/tactic_dash_simple.py $R/tactic-dash-simple.json
python3 tools/fish/tactic_target.py $R/tactic-target.json
python3 tools/fish/tactic_channel.py $R/tactic-channel.json        # needs replays/fish-combat caches
python3 tools/fish/tactic_capture.py $R/tactic-capture.json
python3 tools/fish/tactic_spawn.py $R/tactic-spawn.json
python3 tools/fish/tactic_groups.py $R/tactic-groups.json          # per held-out group
```

- Each script refuses to overwrite its output.
- The JSONs hold counts by cohort and split (fit / held), games and groups, and up to 12 counterexamples per held-out cohort (game SHA16, round, actor).
- `tactic_common.py` holds the split, the loader and the scorer.

## Audit: forced vs free decisions (2026-11-06)

[rule-audit-micro.json](rule-audit-micro.json) holds these numbers, written by
`tools/fish/micro_audit.py`.

- **Method.** Rules are checked against cambc-rules.yaml for rows where the predicted outcome
  was the only legal one, and for conditioning on same-turn outcomes.
- **Scope.** All seven cohorts are pooled; seventh alone is in brackets.

| Rule | Legal alternatives | Forced rows | Free rows (baseline) | Verdict |
| --- | --- | --- | --- | --- |
| Short of full health on spawn → stays | leave; walking is forbidden only when stunned or on the respawn turn | 14 of 30,336 | 30,214/30,322 99.6% [9,920/9,938] | **real choice**, motivated by the rule that spawn heals at turn end |
| Heart of Ruin engage-dash landing: most enemies within 1 | any legal landing (the meaningful subset) | none | = old (98.4% held out, 15.9% random) | real choice |
| Escape dash: min-danger landing | any legal landing | none | = old (96.8%, 46.6% random) | real choice |
| Dash in when a landing gives a kill | no dash; the dash is not exclusive and spends nothing | none: rows are turn-start opportunities, and the label counts any order | = old (88.1%; never 11.9%) | real choice |
| Spell targets weigh gems; basic attacks ignore them | the other candidates (2+) | none | = old | real choice |
| Channels, captures, holds | walk or hit; both legal | none (turn-start rows) | = old | real choice |

- **Spawn counts.** The audit's spawn uses `breadth.spawn` and every cohort, so its row count
  differs from section 5's table (23,612 fit and held).
  - The rule is no less a choice for having a cause in the rules. Leaving is legal, and Fish
    leaves 45% of the time on spawn rows with no enemy visible.
  - Only the 14 stunned or respawn-turn rows are forced, all of them stays.
- **Nothing in this file is a pure rule.** The landing tables already restrict themselves to
  rows where the key differs among the legal landings. "Engage landings leave the target within
  reach" was already flagged as forced by the class definition.
