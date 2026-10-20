# koi

koi is a C++ sparring bot meant to play like the ladder's #1 team, Intercontinental Fish ([FISH-BOT.md](../FISH-BOT.md)).
It is hecate at 110e338 with Fish's camp micro, targeting, shopping and banking cycle, commit rule, peel stuns, turn
priorities and 30% recall line, plus the end-race banking Fish lacks; it keeps hecate's builds. It plays slightly above
that hecate. Experiments: [LOG.md](LOG.md) (attempts 2 and 3) and [LOG-attempt1.md](LOG-attempt1.md).

## Rebuilding it

The bot is not in the tree. [koi.patch](koi.patch) is its diff against `bots/hecate` at 110e338 (9 files, +407/-93):

```
git worktree add --detach ../koi-src 110e338
cd ../koi-src && git apply <repo>/research/koi/koi.patch
```

then copy `bots/hecate/` from there to `bots/koi/` (leaving out `.cambc/`). The variants named in the logs
(`bots/variants/koi*`) were never committed.

## Results (2026-10-20, the final koi: attempt 3's `hf`)

| opponent | koi | hecate-v1 |
|---|---|---|
| hecate-v1, 1986 games: ladder 18/34, gen 147/264, central 51/92, fresh seeds (`replays/koi-maps/`) gen-7101 153/264, central-7102 43/92, gen-7103 147/264, gen-7104 140/264, gen-7105 138/264, central-7106 43/92, gen-7107 144/264, central-7108 48/92 | 54.0% | - |
| hecate-v1, with gen-7109 118/264, central-7110 49/92, gen-7111 152/264, central-7112 51/92 (2698 games) | 53.4% | - |
| nemesis (390) | 63.3% | 61.5% |
| rival (390) | 73.6% | 69.0% |
| morgana (390) | 74.9% | 74.9% |
| aphelios (390) | 92.6% | 90.3% |

Fish's own build table cost about two points against hecate in every attempt (no Jungle: more camp damage, more heal
trips in these short, fight-poor games), so the final koi buys hecate's upkeep builds; attempt 2's koi (Fish's builds,
`koi2-eng`) scored 50.4% over the first 1986 games (nemesis 59.0, rival 66.7, morgana 74.9, aphelios 89.5).

## What koi does, and how it maps to Fish

| Fish (FISH-BOT.md) | koi | where |
|---|---|---|
| Fixed build per champion: Focus on the casters, Health on the front line, spend everything | not copied: hecate's upkeep build (Jungle, Power or Durability by the clearing time saved), which still puts Focus on the casters; Fish's table cost about two points | `bot.cpp` `upkeep_emblem`, `build_step` |
| Basic attacks on the lowest hp + shield; stuns on the biggest threat; nukes on a killable target, else the most hurt | a basic attack takes a kill, else the lowest health; a stun adds the target's threat (max of Strength and its next-turn strike; Strength for a damage-free stun); a damage spell that cannot kill prefers the most hurt; a stun on an enemy below the hurt line is worth half a life more | `plan.cpp` `best_hit`, `abilities.cpp` `threat_of`, `enemy_cast`, `stun_worth` |
| Kills come from nuke range (4) at turn start, right after the target acted | a chasing caster with its nuke ready next turn closes only to the nuke's range, into a bush within 2 steps when one is there; right after an enemy acts, a caster with its nuke ready steps into nuke range when we act first next round | `bot.cpp` `chase`, `step_in` |
| Casts what is ready (58% with a nuke ready and an enemy in range) | a retreating caster casts any ready spell unless its tile is lethal | `bot.cpp` `retreat` |
| Contests a capture by killing its holder | an enemy on a cleared group counts the group's gems as a bag: chased on its own ground and worth more to kill | `bot.cpp` `prey` |
| New version: priority steers camp aggro onto healthy empty-handed bodies | out of fights, priority -1 - floor(10 x hurt) empty-handed, -6 - floor(5 x hurt) carrying (camps hit the first tied actor) | `turn_order.cpp` `set_turn_order` |
| Recall cliff at 30% hp | low-health line 30% | `params.h` |
| Basic attacks on the lowest-hp camp: clusters first, a body on a freed tile as the last monster falls | the same (Varg's splash still counts members next to the target), and a melee body that has attacked steps onto a freed camp tile still in reach of a live member, one per group | `bot.cpp` `attack_camp`, `step_onto_freed` |
| Stuns keep landing on the monster that deals damage; Cassi stuns camps 4.3 per 100 rounds | a damage-free stun (Cassi's) goes on any monster hitting an ally, at any value | `abilities.cpp` `camp_cast` |
| Openers from range 4-5 while the tank walks in | a spell from out of the monsters' reach when an ally is already in it | `bot.cpp` `farm` |
| Allies stun a chaser for a third of low-hp survivors | a stun on an enemy that threatens an ally below half health is worth that ally's life | `abilities.cpp` `stun_worth` |
| Commits at about 30% hp when its side outweighs the enemy's | no retreat while hp after the visible enemies' next-turn burst is 300+ and our local health is 1.5x theirs | `bot.cpp` `want_home`, `engage_at` |
| Engages where its side outweighs the enemy's; chases carriers and low-hp enemies, no leash | where hp after the visible burst is 300+ and our local health is 1.5x theirs, go for the weakest visible enemy within 6 (off its spawn); otherwise any carrier is chased when the fight simulation says we win | `bot.cpp` `prey` |
| The killer acts before its victim | in a fight, priority rises with the share of the weakest nearby enemy our next turn takes | `turn_order.cpp` `offer_engaged` |
| Recall to shop when a payout lifts gold to 150, bag and all; a carrier within 5 steps of an altar banks first | the same; the bag that rode home goes to an altar; empty-handed with 150 gold, go shop | `bot.cpp` `capture_recall`, `wants_shop`, `carry_bag`, `Memory::deliver` |
| Lazy banking: about 5 gems a step to the altar | chaining continues to 5 gems a step (cap 150), within hecate's threat and 60%-hp checks | `bot.cpp` `may_chain` |
| Waits next to a returning group | waits for it from a bush in reach when one is there | `bot.cpp` `farm` |
| Weak: big slow final tributes, no reaction to the enemy's race | bags bank at once when the enemy could win within the trip + 40 rounds or from 700 gems on either side; no shopping within 100 rounds of the enemy's win | `bot.cpp` `closing`, `late_race`, `enemy_race_left`, `may_shop` |
| Next group: soonest hittable, long cycles worth less | farm value `worth / (cycle (1 + cycle / H))`, H = 140 x max(1, side / 50); the bank-then-farm value it is compared with is not discounted, so carriers also bank earlier | `bot.cpp` `rate` |
| Weak in the end race | a winning or late-race bag within 12 steps of an altar goes in whatever threatens it when the enemy is on 850+ or near its win | `bot.cpp` `rush_bag` |

Also: a wider search when live camps block a static route (a body otherwise stood 90 rounds in a dead-end pocket;
koi gates it on fuel, which AGENTS.md rules out for hecate).

Against hecate specifically, how Fish kills is measured by `py tools/koi/killcard.py --scrims` (LOG.md, attempt 3):
Fish converts engagements into kills with less damage per kill (2.2k against 3.3k), mostly through its killers' stats.

Kept from hecate because Fish's version lost to it (LOG.md has the numbers): the fight simulations behind retreats
(the fitted engage rule as the decision rule lost 15 points), crews (pick-pair crews lost 4-10), solo range openers,
preferring respawning groups, Monolith chipping on mixed maps, the new version's Home emblem (1.6 points below the old
table), a Monster emblem first on big-group maps (level).

## Scorecard: koi, Fish and hecate (attempt 2's koi)

`py tools/koi/scorecard.py <batch dirs> --team koi` after `node tools/replay/extract.mjs <batch dirs>`; `--fish` for
Fish's own (cached). koi and hecate-v1 are the same 390 standard games (`replays/koi2-ab/eng-vs-baselines_hecate-v1-*`);
Fish is its 459 ladder games against the other top-15 teams.

| metric | koi | Fish | hecate-v1 |
|---|---|---|---|
| Basic attack on the cluster (cluster + monster in range) | 97% | 95% | 4% |
| Body on a freed tile at a clear (2+ clusters and a monster) | 52% | 70% | 37% |
| First wakes from distance 4+ | 13% | 37% | 7% |
| Camp attacks cancelled by stuns, per 100 alive rounds | 1.49 | 1.45 | 0.88 |
| Cassi stuns on camps per 100 Cassi rounds | 3.41 | 4.25 | 0.91 |
| Crew on wolf / elk groups | 2.01 / 2.47 | 2.29 / 3.48 | 1.97 / 2.45 |
| Far bodies arriving 1-4 rounds before a respawn | 39% | 86% | 37% |
| Single-share captures | 99% | 98% | 99% |
| Kept recalls at or right after a payout to 150+ gold | 17% + 4% | 83% | 17% + 5% |
| Recalls at 27.5-30% vs 30-32.5% hp | 775 vs 211 | 1000 vs 229 | 474 vs 702 |
| Median bag age at tribute | 14 | 40 | 17 |
| Carried gems per body-round | 8.3 | 16.9 | 10.4 |
| Spawn exits under 30 gold / shopping while dead | 99% / 100% | 100% / 100% | 99% / 100% |
| Builds (first three emblems; most champion-games complete fewer) | Fish's table: Ren 51%, Ryth 42%, Issac 42%, Stellar 37%, Varg 34%, Cassi 30% | Fish's table: Ren 87%, Ryth 76%, Issac 67%, Stellar 53%, Varg 43%, Cassi 28% | Jungle/Power/Durability by price, never Fish's table |
| Basic attack on lowest hp+shield | 82% | 92% | 79% |
| Available kill taken (spells counted) | 92% | 97% | 92% |
| Killer acts before its victim | 61% | 74% | 63% |
| Low-hp (<25%) survival in combat | 59% | 62% | 49% |
| Follow a fleeing enemy / chases that kill | 62% / 16% | 59% / 31% | 55% / 14% |
| Deaths / kills per game | 3.4 / 2.9 | 5.0 / 6.9 | 4.0 / 2.3 |

Where koi is still unlike Fish:
- **Shopping recall and lazy banking.** The end-race rules stop shopping and chaining from 700 gems on either side and
  within 100 rounds of the enemy's win, a third of each game; a carrier within 5 steps of an altar banks first, which
  on generated maps (altars near camps) is common; and koi keeps hecate's rule that a recall is kept only when no damage
  can land before it completes (dropping the unseen-enemy part changed little).
- **Crews and respawn timing.** Each of Fish's versions cost win rate against hecate (LOG.md), so koi keeps hecate's.
- **Fights.** koi-vs-hecate games have few fights (about 3 kills a game against Fish's 6.9 on the ladder), and the
  builds' burst rarely pays off before the game ends; chases kill half as often as Fish's.
