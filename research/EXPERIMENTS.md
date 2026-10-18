# Experiments

What has been tried on our bots, so it isn't repeated. Win rates are against the bot's own previous version, on all maps from both sides, unless noted. Noise is about ±2.5 points on 390 games. "Level" means within noise. Don't retry a lost or level idea as is; it needs a new mechanism or ladder evidence.

## General

- Judge changes on ladder + gen + central and a fresh-seed suite (700+ games). Gains on the committed suites shrink on fresh seeds: crews went +22/320 → +8/320, and a 54.6% hecate bundle was 47.8% on a fresh suite.
- Local games are deterministic: rerunning the same maps gives the same results.
- Self-play hides ladder behaviour. Our bots start a recall at every turn end and cancel it the next turn, so in local games enemies look like they are recalling in ~90% of rounds (5-8% on the ladder). Any value for cancelling an enemy recall is inflated locally, and an ally's `channel == recall` does not mean it is going home. A morgana copy without the pre-start won only 20.8% against morgana.
- Bug fixes, drafts and map-type strategies have paid off. Retuning tactics or pricing against our own bots rarely has: whole-model ports (morgana's farm pricing into nemesis 43.0%, a pack zone decided by the fight sim 46.9%) lost.
- Lifetime gold is the best predictor of who wins fights. In the nemesis mirror, +1 net kill at round 300 takes the win rate from 56% to 85%.
- contest is the only ladder map that reaches round 2000. 31% of its games tie on gems, and gold then decided every tied ladder game. nemesis took ~15% of the gold clusters there.

## aphelios and morgana (2026-10-15/16)

- One champion per camp (claims keeping allies off each other's groups): 38-45%, because deaths with no ally within 6 doubled. Waiting at respawning groups: 45%. Won: discounting enemy-ground groups by min(1, 2·d_enemy/(d_ally+d_enemy)) with ×1.2 stickiness.
- ~20 morgana tactical tweaks were level or worse: retreat variants, fighting back when doomed, ally assist, a strike-first fight sim alone, pushing when ahead, gold in camp value, Focus on Ren/Tavi, Durability as second emblem (−15), a farm-race draft rule, and steering around the pack zone (−15/240). Won: crews, draft order (Varg 3rd), a stun valuation bug, fuel gates, lock/tribute bugs.
- One-price farm valuation (96e33f5, ~52% vs morgana-v5, 100% on Monolith-only maps). Needed: the first claimer owns a group; a respawning group's attack tiles exclude its camp tiles; no face-clearing when camp DPS × exit hits exceeds health at the recall line; death price from the ladder hazard. Lost: discounting reward by enemies that could reach (−3 to −20), two-job lookahead (−24), a constant gold share (−4 to −8), pooled crew health (−3). Capping waits at a quarter of a respawn took small maps from ~25% to 50%.
- Picking up cleared groups in sight plus team-total banking: 52.8%; gold-only captures went 529 → 1849 per 264 games. Shared memory is now fully packed.

## nemesis (2026-10-17/18)

- Won (from rival): max_wait 5 (10 cost 4.5); home_retreat ratio 2 in our own half; finishing_camp summing all awake groups, plus camp_trapped; a sticky siege target with 2 Monolith holders; shop recall and chain_bag_limit 80; camp tie-break by turn order; retreat by the least exposed homeward step (2dba924, about +5 vs rival and morgana).
- Lost or level:
  - other drafts (37-50%) and Fish builds (−3)
  - pack bonus or spread penalty in farm value
  - Monolith sieges on normal maps (39.6%); stickiness 1.0 (−5); shopping at 300 gold (−7)
  - casting before walking (46.2%: the spell is cast a turn later anyway, and the delay costs camp hits)
  - camp damage in the fight sim (47.7%); a periodic ward rule (48.7%)
  - ranking jobs by worth − ρ·cycle (27-34%)
  - EOQ bag limit, capture-recall heal value, tank assignment, stun value max(80, next-turn damage), Smith targeting
  - nine calculation-based changes: Treasure as second emblem, Stellar ground-skip fix, tank priority, pursuit sim, attack-tile adjacency, symmetric fight arrivals, exact enemy-turn threat model, camp clear sim, gold-as-score on Monolith-only maps
  - a crowd rule (3+ enemies outnumbering us by 2) and farm-zone avoidance with an empty bag (−3.5 vs rival)
- Open issues as of 2026-10-18:
  - Movement jitter: farm() re-picks its target every turn with only ×1.2 stickiness, and the crew hit share grows as we approach, so the 'H' and 'L' skips can bounce a champion between two tiles.
  - Healthy solo champions away from home walk toward visible packs: retreat_ratio is 100 there, and fight() counts only enemies already in reach. About 25-30% of deaths are a lone champion killed by 2+ enemies.

## brawler (2026-10-17, local and untracked)

The whole team as one PVP pack: 2-8% vs nemesis. It earns ~150 gold a game against nemesis's 540-940, nemesis flees packs in its own half, and travel after deaths is long. A pure pack can't out-score five farmers.

## hecate (2026-10-18)

Shipped changes are in [hecate/CHANGES.md](hecate/CHANGES.md). Level or lost: true first striker in the fight sim, shopping ×2 emblems, third-party camp damage in the fight sim, rally assist, caster poke from our own ground, Cassi/Issac target priority, kite cap 40, altar control (6 variants), central-group kiting, Focus builds (−4), alternative drafts (no Cassi 39.5%), and Monolith + cluster sieges on normal maps (5-40%).
- Ladder-motivated, lost or level locally (vs hecate, 390 games): gold valued 3× in farm choice (`worth = gems + 3 · gold · clear_share`) 46.9%; the top teams' draft (Ren, Stellar, Cassi, Ryth, Varg) with Focus builds for Ren 42.3%. Both target gaps seen against Intercontinental Fish ([LADDER-FISH.md](LADDER-FISH.md)), which our own bots don't exploit, so judge them on the ladder, not locally.
- Also level or lost locally on 2026-10-18 (vs the hecate of the day, 390 games): Cassi gold weight 10 instead of 4 (49.2%); gold value front-loaded by the gems still to farm, ×(1 + k·left/1000) with k 2 or 5 (47.2%, 45.6%); a 100+ carrier going home from any visible threat (48.7%); the full escort with Monolith ward and carrier intercept (48.5%, out-of-fuel turns 18 → 56).
- Big-bag work on hecate v21 (2026-10-18, bots/variants/hx-bags): a 150+ bag treated like Cassi/Issac (a fight where the carrier falls counts as lost in want_home, pursuit, step_guard and prey) lost bags faster vs the carrier-hunting hx-ambush on the 10 Monolith-only maps (big bags lost 42 vs 34, tributed 67 vs 76, wins 12/20 vs 15/20): carriers that retreat alone get run down. No escort and no escort wait on shared_gems_map() maps (ladder: v21 lost stampede to Mite and procless, v20 won both): 49.5% vs hecate (ladder 17/34, gen 130/264, central 46/92); only shared-gem maps change, and hecate takes mut-stampede 4/4 (captures every block, 4380-120 gems), so locally the escort helps there.
- Big-bag escort (hecate v21/v22, 2026-10-18): a 150+ carrier waits for 2 allies, empty-handed allies within 18 guard it. Locally level (51.3%) and big bags lost on Monolith-only maps 7 vs 14, but on the ladder (same seeded maps vs the top 5) v20 28-47, v21 26-49, v22 24-51; stampede fell to 0-1080 when escorts left the shared block. Reverted. Next idea there: keep the carrier with allies and flee towards them, not to spawn.
