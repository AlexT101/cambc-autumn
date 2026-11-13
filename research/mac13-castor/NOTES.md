# CASTOR: macro refactor of charybdis (2026-11-13)

Running log, timestamped (UTC). Reference `bots/variants/chy-ref` (= charybdis at 0f6fa9879). Every A/B:
`research/mac13-castor/ab.sh TAG CAND SUITE` = `tools/ab.py variants/CAND variants/chy-ref --no-test-draft --fuel 200000
--suites SUITE --name mac13-castor-TAG`, fast runner native. Suites: `maps/suites/mac13/dev` (5,120 maps, 10,240 games),
`maps/suites/mac13/hold` (2,560), `maps/suites/mac13/study` (seeds 141200-141203, 1,024 maps: debug traces and smokes
only, never decisions).

## Log

- 02:00 Read BRIEF, rules, prior programme notes (macro-orchestrators-2026-11-11 and the eight NOTES, fish-farm study).
  Priors: the mirror is decided by the Prism duel (first Prism death loses ~88%); every change that takes farm time
  away lost; re-weightings flat. Overseer's addendum: gains come from pricing mechanics the bot never sees.
- 02:05 Debug mirror chy-mirror vs chy-ref on study (2,048 games, 50.0%, 4.6 min wall) for traces; solo baseline
  (vs idle) on study running.
- 02:10 macro_stats on 354 mirror games: winner/loser move 51%/51% of alive time, camp 17.1%/15.5%, dead 4.6%/12.1%;
  kills 7.6/2.6, gems lost at death 31/232; captures 62/55 (1072/839 gems); recalls ~45 a team-game.
- 02:30 Turn budget (tools/replay/turn_budget.py, 1,023 distinct mirror games; full table in
  `logs/turn_budget_mirror.md`). Supply is not binding: gem-weighted group-rounds asleep (available, unworked) own
  57%, mid 70%, enemy 58%. Team hits camps 18% of champion-rounds (27% r1-150), walks ~50%. Predictors: more r1-300
  captures wins 68%, tributed+carried lead of 150+ at r200 wins 88%, more mid captures 77%, fewer gems lost at death
  88%. 72% of deaths happen while retreating (R). Solo vs idle: collected 195/463/892 at r150/300/600.
- 02:35 Per type (mirror): gold earned per game Prism 2046, Vesper 2742, Cassi 256, Issac 250, Willow 60, HoR 493.
  Cassi/Issac/Willow are frozen near base stats (Cassi max HP 663 at r300, 764 at r600; Willow 707): one enemy-Prism
  stun (1.5 x Focus ~450 at r300) kills Cassi. Prism Focus r200/300/600: W 332/512/969, L 292/405/645; Prism unspent
  gold mean 230 (W) / 109 (L), 124 at r300 and 344 at r600; Prism buys mostly Health (max HP 1602 at r300).
  Willow heals 13.5k a game (~32 heals of a ~110 cap).
- 02:50 Theme for the first two lines: **cooldown economy**. Abilities are the strongest, cooldown-limited outputs
  and run at ~30% of capacity. C1 `c1-casts`: free damage casts on camps on turns that don't walk (holds, waits),
  keeping the duel stun (brief `briefs/c1-casts.md`). C2 `c2-medic`: Willow positions for heal value across the team,
  allies within reach of her heal skip trips home (brief `briefs/c2-medic.md`). Both implementers running.
- 02:30 (clock check: my earlier entries' times ran ahead; this is the real time) First Prism deaths (531 games with
  both Prisms): victim's team wins 50/531; killer Prism 351, Vesper 58, camp 29; median r446, bag 140; Focus ratio
  victim/other <0.8 in 234, 0.8-1.25 in 245, >1.25 in 52; allies within 8 of the victim 0 in 165 (31%); allies minus
  enemies within 8 is negative in 70%; the victim ends the round before at <=30% HP in 70%, 4 tiles from the enemy
  Prism in 45%. First team to hold a winning bag (score + one bag >= 1000) wins 92% (921/1003; median r650).
- Deaths after a retreat run (`R` branch): 6,155 of 10,624. Retreats start at full HP in 29% of them, with the
  nearest enemy at 1-5 tiles in 82%: champions are caught, not worn down. Cassi 1,103, Issac 943, Prism 786, Willow 775.
- Death hazard per 1000 champion-rounds by max HP / (2.5 x enemy Prism Focus): Cassi 5.4 (<0.25), 1.8 (0.25-0.5),
  ~1.0 above; Prism 7.5 / 3.3 / 1.6 / 1.0 / 0.9 / 0.5 at 0.25-1.5+. Confounded with being behind; gold-for-HP on the
  fragile bodies looks weak (they never reach 1.0).
- One game read end to end (gen-ladder-14120200013, 827): the Prism farms a pocket 27-35 steps from spawn and makes
  four heal/shop trips home by r430 (~37 rounds each, ~35% of its time); idles 25 rounds waiting for respawns; after
  both Monoliths (r622) our Prism walks 65 steps alone to the single mid altar with a winning bag, while our Vesper
  and Vendetta wander into enemy ground alone and die 1v2/1v3 (r665, r688) to the converging enemy Prism; our Prism
  dies at the altar 1v2 (r704, 1,076 gems). Their Prism hunted toward the fights; ours had nobody near.
- 02:45 **Economic leads convert even without kills** (games with no champion kill before round T, side with more
  tributed + carried gems at T): r300 lead 10-25% -> 62% wins (112 games), 25-50% -> 64% (55), >50% -> 87% (31);
  r150 25-50% -> 65% (111). So a systematic ~20-25% faster economy by r300, fights unchanged, is worth ~60%. Target
  for economy lines: solo collected @300 (463 now) +20%, with deaths unchanged. Back-of-envelope: camp damage
  ~17 HP a gem, a heal trip restores ~750 HP for ~2x the pocket's distance from spawn (25-40 rounds on big maps), so
  heal trips cost about as many rounds per gem as the hitting itself on big maps (~0.9 rounds a gem).
- 02:40 Recalls (87,715 completed, ~43 a team-game): only 14-35% start below half HP (Prism 16%, Issac 35%); 54-61%
  start at >=90% HP (transport, shopping, capture rides). The recall/spawn cycle is mostly travel, not healing, so
  C2's heal value is smaller than first estimated. Prism-sole captures: Prism stands on the tiles ~4.3 rounds each
  (~15 a team-game, ~65 rounds); an ally pre-held 36% of them. Winning-bag reversals (82 of 1003) are diverse (47
  Prism holders; 46 never tributed or died): an endgame escort is worth at most a couple of points, dropped.
  Stun cover in Prism duels: an allied ready stunner within 4 of the enemy Prism at a parity opener in only 35 of
  564 (opener covered: its Prism died 0/23 vs 12% uncovered). Cassi is within 4 of our Prism 32% of the time.
  -> C3 `c3-screen` brief written (stunners screen our Prism only while the enemy Prism can engage).
- 02:50 Utilisation r1-300 (camp damage dealt / alive rounds x raw output incl. spells at cooldown): Prism 34%,
  Vesper 30%, Cassi 29%, Issac 28%, Willow 17%, all types 16-52%. 70% of output is lost to walking (~50% of time),
  holds, recalls. Prism ready-slot turns r1-300: casts on 12%; a live group within 5 on 42% of them, cast on 25% of
  those; ~7% of ready turns are stationary next to a live group with no cast (C1's free-cast pool: ~13 casts a
  Prism by r300 against ~23 now, roughly +5-10% team camp damage early).
- 03:10 C1 interim solo (implementer's runs): collected @150/300/600 -3.5/-4.9/-1.1 (first build), then +0.7/-0.5/+0.8
  (second): free casts add no measurable farm against idle so far. Group geometry: 83% of camp groups have 2+ members
  and nearly all members of a group fit under one 3x3 (cardinally connected), so a ground spell hits the whole group;
  the farm's clear model (`camp_output` = raw_output once per round, `min_camp_damage` single-target) counts it once.
  For a Prism at Focus 400 on a 3-member group that is ~160 vs ~260 damage a round. Varg's cleave and Heart of
  Ruin's landing are the same. Candidate C4: AoE-aware clear model.
- 03:14 **C2 `c2-medic` (Willow medic)**: dev 50.8% (49.8-51.7) of 10,240 (`mac13-castor-c2-dev`, SPRT H1 crossed at
  2,156 games but ran to completion); hold 50.9% (49.6-52.3) of 5,120 (`mac13-castor-c2-hold`). Small gain, ~+0.8.
  Box is quiet now: a 10k A/B takes ~3 min. New suites generating: `train` (141300-141319, for implementers' own A/B
  loops) and `x1` (141230-141249, a further confirmation suite).
- 03:20 **C1 `c1-casts` (free casts on turns that don't walk): dev 50.0% (49.0-51.0) of 10,240 — dropped.** The
  implementer's traces: ~1 free cast per Prism per game (holds 514, standing farm turns 318 in ~1,000 games). Of ~32
  Prism turns a game with a ready slot, a live group within 5 and no walk, the duel gate keeps the slot in 22
  (visible enemy 14.3, seen within the cooldown 4.2, tracked unseen 3.7). A walking-turn variant (11.6 casts a game)
  cut solo collected @150/@300 by 3.5/4.9: casting costs the step. Spare cooldown is not free capacity: the Prism's
  slots are held for the duel when enemies are near, and elsewhere it is walking.
- 03:20 C3 `c3-screen` launched with licence to iterate on `train` (10k-game A/Bs, ~3 min). C4 `c4-aoe` brief
  written (area-aware clear model: ground spells, Varg cleave, HoR landing hit every member of a group).
- 03:30 Lead: ATLAS's fixes 3 and 5 and its "press a disarmed enemy" were left out of charybdis 517 only for their
  100k-fuel cost (ATLAS final 52.2% held out at 2x fuel vs charybdis 81fc6f968; 517 shipped fixes 1, 2, 4 at 50.5%).
  `research/macro-atlas/patches/remaining-after-517.diff` still applies to chy-ref (-p4, offsets/fuzz only).
  At our 2x-fuel standard it should be worth ~+1. Queued as C5 (port, audit, smoke) to stack with the macro lines.
- 03:35 **C2 final** (Willow's hold beside her target restored while the heal cools): dev 50.1% (49.1-51.0) of 10,240
  (`c2b-dev`), hold 50.4% (49.0-51.7) of 5,120 (`c2b-hold`). The 03:07 snapshot (hold gated off; recovered from
  `replays/frozen/ecdcdbcc6939` into `variants/c2a-medic`, `patches/c2a-medic.diff`, 9 lines from c2) read 50.8 /
  50.9. Pooled, the medic is ~+0.5: within noise. Implementer's traces (632 Willow team-games): heals 55.8 -> 60.2 a
  game, team recalls 40.4 -> 38.8, deaths 8.84 -> 8.06; but on 55% of Willow's heal-ready turns no ally anywhere is
  damaged: there is little spare heal to use. Keep c2a as a component for integration.
- 03:35 C5 `c5-atlas` launched (port of ATLAS fixes 3, 5 and the press). Overseer: integrate pieces into one consistent
  valuation, measure the combination, then ablate. Plan: integration candidate after C3/C4/C5 read.
- 03:47 Steal pool: 34 cleared groups a game (both teams) sit unheld 3+ rounds before someone holds them; in 7.7 an
  opponent was within 6 during the wait, and it stole 1.6 of those (~141 gems a game in the 7.7). Upside of a steal
  economy is a few % of captures: not a priority.
- 04:15 **C5 `c5-atlas` (ATLAS fixes 3, 5 and the press, ported to chy-ref; auditor fix: the press checks 520/525's
  wider "our fall" set, Prism and big-bag carriers, not just the linked pair): train 49.6% (48.7-50.6) of 10,240,
  OOF 956 vs 573** (`c5-train`); smokes 50.8 / 49.2. ATLAS's 52.2 was against an older charybdis; on top of 518-525
  the leftover fixes read flat and cost fuel. Dropped (diff in `patches/c5-atlas.diff`).
- 04:15 C4 `c4-aoe` (area-aware clear model) launched. Box load ~250: A/Bs now 10-15 min.
- 04:22 C3 `c3-screen` train1 49.8% (48.8-50.8) of 10,240 (OOF 740 vs 606): the stun screen reads level; asked
  the implementer to wrap up and report.
- 04:22 Solo (chy-ref vs idle, study, debug; `logs/turn_budget_solo.md`): 1000 tributed at r667 on average, about
  the mirror's median winning-bag round (r650): the enemy barely slows our farm, so a faster farm is the lever.
  Turns/gem by group: gem clusters 0.25, lone-hitter golem 0.25 / elk 0.41, wolves 1.4-1.6 (2.0 r1-300). Supply:
  own groups asleep 56%, enemy-side 87% even with an idle enemy.
  Prism (solo, r1-600; `/tmp/castor-tools/prism_walk.py`, `prism_recall.py`): walk 48%, hit 18.7%, recall 17%,
  still 10%, tribute 5%. 5.6 completed recalls by r600, 90% shop on arrival (117 gold, ~4 shards), 67% at >=90% HP;
  33% go home and walk back (~30 rounds to the next hit). `wants_shop` is a now-or-never test (gain x 0.75 > trip),
  where banking uses an order quantity. Walk segments to a hit: 14.5 rounds; 22% (42% of walk rounds) go 5+ tiles
  past the nearest live group.
- 04:26 Mirror vision (1023 games): of 13,178 champion deaths by a champion, the killer was seen by an ally but not
  the victim in the round before in 20% (8 rounds: 17%). Shared sightings have lost four times before (CHANGES 236,
  cm-sight, wp-sh: knowing more made teammates give way): not retried.
  Branches (D lines): mirror r1-300 farm 70%, Willow support 6.4%, retreat 4.7%, hold 4.6%; solo farm 77%.
- 04:28 C6 brief `briefs/c6-prism-time.md` (Prism time: shop timing as an order quantity, then the next mispricing
  in the Prism's budget, iterated on solo + train).
- 04:30 **A Prism gem is worth ~2 gems through r300** (logistic fit of the winner on gem holdings, 1,023 mirror
  games, per 100 gems of team difference; `/tmp/castor-tools/preg.py`): tributed / other-carried / Prism-carried
  r150 0.39/0.81/1.18, r200 0.45/0.55/1.15, r300 0.65/0.67/1.21, r400 0.73/0.43/0.87, r500 0.66/0.48/0.65 (+-0.1).
  At equal team totals a Prism gem share 10 points higher wins 58-61% (r200-400). The bot prices the premium once,
  as a Focus-shard equivalent in the Prism's own farm (`carried_bonus`); holders, leave-for-Prism, takeovers and
  crews compare gems as gems. -> C7 brief `briefs/c7-prism-gem.md` (one premium function, used everywhere).
- 04:41 **C3 `c3-screen` final report: level.** Train v3 49.8% (48.8-50.8), v6 50.5% (49.6-51.5) of 10,240 (v6 OOF
  1,188 vs 553; the final fuel fixes bring the smoke to parity, 52.0% of 256). Debug study: openers with a ready
  stunner in reach 9.9% -> 11.3%; Prism deaths 0.74 -> 0.65 a game; stuns on the enemy Prism 2.63 -> 2.76. Why
  level: a safe station for a fragile Cassi exists only on the boundary of the enemy Prism's reach, so coverage
  barely moves; half the openers have no ready stunner in sight at all; stuns go out when our Prism is not in the
  fight. Dropped as a standalone; `stun_worth`'s saved-turn term untested alone.
- 04:41 C7 `c7-pgem` launched (Prism gem premium, one function used by every holder/leave/takeover/crew decision).
- 04:44 Prism duel entries (mirror; first move into Chebyshev 5 of the enemy Prism, 3,836): the weaker
  Prism (Focus < 0.8x) walking in dies 49% within 15 rounds (seen first: 54%); but 722 of those 1,149 seen cases are
  branch E (stopping the enemy's winning tribute, 79% die, median r781): desperate endgames, already lost. Farm
  F 229 cases die 7%, retreat R 39 die 44%. Duel discipline is not the gap; economy -> Focus lead is.
  C4 v1 (implementer's): train 49.6% with OOF 4,987 vs 993 (fuel blow-up), solo round-to-1000 -0.5%.
  C8 brief `briefs/c8-route.md` (farm choice by worth - rho x rounds + onward value of where the job ends, replacing
  the (1 + rounds / H) stand-in). Queue: C8, then C6.
- 05:10 C4 v2 (implementer's): train 50.0% (49.1-51.0), OOF 858 vs 605: the area-aware clear model reads level.
  **C7 first train run: 52.8% (51.9-53.8) of 10,240** (`c7-train1`, OOF 710 vs 613). Froze that build as
  `variants/c7a-pgem` (`patches/c7a-pgem.diff`, from `replays/frozen/a764d6484cf5`); dev and hold A/Bs running
  (`c7a-dev`, `c7a-hold`) while the implementer ablates. Walk efficiency (solo, BFS): Prism steps 1.24x shortest,
  Cassi 1.22x, Willow 1.97x (follows); Prism excess ~5% of its time: re-targeting is not the walking problem.
- 05:12 **C7a (Prism gem premium, first build): dev 53.1% (52.1-54.0) of 10,240; hold 52.7% (51.3-54.0) of 5,120.**
  OOF 663 vs 560 / 334 vs 320. The premium is derived: a gem adds dOut = raw_output(F + 1.5) - raw_output(F) camp
  output a round, the team farms rho gems per output-round (its collected gems over rounds against summed
  camp_output, prior-weighted), the gems join the bag and compound, so over the H rounds the bag stays kept (to the
  win at the team's pace, or the last round that leaves the tribute) a gem becomes exp(dOut rho H) gems: premium =
  expm1(dOut rho H), capped by the room to the win. Used by the Prism's farm (replaces `carried_bonus`), by
  `holder_value` (a Prism holder's gems x (1 + premium)), leave-for-Prism (leave when premium x (respawn + capture)
  beats the payout delay), handoffs (no taking over a Prism hold unless ours pays more) and the feeders' farm (a
  group a Prism ally claims carries its premium). conf and x1 A/Bs started.
- 05:15 C7 ablation (implementer's): without the crew-share part, train 51.0% (50.0-51.9): the feeders' side is
  ~+1.8 of the 2.8. C7 solo: round to 1000 -0.1%, collected @300 +2.0 (CI -1.4..+5.5): **the premium does not
  farm faster; it moves gems into the Prism** (Focus for the duel). C4 train3 (implementer's): 46.7%: C4 is dropped.
  C9 brief (premium in fights/risk/turn order) written, to follow C7.
- 05:17 **C7a confirmed: conf 52.7% (51.8-53.7), x1 53.5% (52.5-54.4) of 10,240 each.** Pooled over dev+hold+conf+
  x1 (35,840 games): ~53.0%. c7a is the base for everything that follows. Asked C4 to stop and report.
- 05:19 **C4 `c4-aoe` final report: dropped.** Train v1 49.6 (fuel blow-up), v2 50.0 (49.1-51.0), "optimistic" (no
  decay as members die) 46.7 (45.8-47.7). Solo v2: round to 1000 -0.3%, tributed @300 +6.8, gold @600 +37. The
  multiplier is 10-30% for a base Prism, similar across multi-member groups, so few choices flip; more area credit
  sends area champions into longer exposure and loses. A late audit found a kite-term bug on mixed groups (unfixed).
- 05:19 C8 `c8-route` launched on top of c7a (onward value of where a job ends).
- 05:25 What C7 moved (1,000 kept replays of `c7-train1`, 805 games with both Prisms; `scripts/bybot.py`): Prism
  share of team gems (tributed + carried) at r200/300/400 0.576/0.571/0.559 vs chy-ref 0.512/0.502/0.490; Prism
  bag r300 197 vs 166 (+19%), Focus 436 vs 386 (+13%); team total r300 321 vs 303 (+6%); our Prism dies first
  28.2% vs 40.0%. The gain runs through the duel: a stronger Prism dies first less and takes the other's bag.
- 05:30 C7 traced premium (PREM lines, debug study): median 3.1 at r<100, 1.8 r100s, 1.1 r200s, 0.67 r300s,
  0.44 r400s, ~0.25-0.35 r500-1000: close to the logistic's ~1 extra gem a Prism gem through r300 (larger early).
  Implementer's later variants: train3 51.7, train4-v3 51.8 (below c7a's 52.8).
- 05:42 **C7 final report.** Final v4 (`variants/c7-pgem`, frozen copy `variants/c7f-pgem-frozen`,
  `patches/c7f-pgem.diff`): train 53.0% (52.0-53.9). Readings: v1 (=c7a) 52.8, v1 without the crew feed 51.0, v2
  (all audit fixes) 51.7, v3 51.8, v4 (v2 minus "a threatened Prism gets no premium") 53.0. The old carried_bonus was
  not small (1.5 at r150, 0.8 at r300; new premium 1.7 / 0.86): **the gain comes from consistency**, the allies'
  side (holders, leave-for-Prism, crews) now values the Prism's gems as the Prism does. Prism share of team gems
  +6-7 points at equal totals; solo farm speed unchanged. Premium assumes damage-proportional gem value. OOF +10-15%.
  Sent the C7 implementer the C9 brief (on c7-pgem v4). Dev A/B of v4 running (`c7f-dev`).
- 05:45 Mechanical merge (patch, no conflicts): `variants/c7m-medic` = c7-pgem v4 + c2a medic
  (`patches/c7m-medic.diff`). Train A/B running (`c7m-train`), compare with v4's 53.0 there.
- 05:47 C7 final v4 dev 53.0% (52.0-54.0) of 10,240 (c7a 53.1): equivalent; v4 (audited) is the base.
- 05:51 c7m (mechanical c7 v4 + c2a medic): train 53.8% (52.8-54.7), OOF 736 vs 712 (v4: 53.0).
  [Corrected: I first swapped this with C8's train1, which is the 28.1% / OOF 29,669 run (C8 v1 fuel blow-up).]
- 05:52 Hunt opportunities (mirror): the stronger Prism (Focus >= 1.25x, HP >= 70%) sees the weaker at
  6-8 tiles 4.2 times a game (weak bag ~100); within 15 rounds the weak one dies 15.6%, the strong 0.4%; the strong
  closes within 5 in 3 rounds only 20%. A Prism can't catch one that flees (same speed, cast needs a turn start in
  range), so a hunt macro's ceiling is modest; left to C9's kill pricing.
- 05:55 c7m dev A/B started.
- 06:02 c7m dev 53.2% (52.3-54.2) (v4 53.0): the medic adds ~+0.5 at best on top of c7; kept as an optional stack.
- 06:09 c7 vs chy-ref outcomes (1,000 train1 replays): our Prism dies first 227 games (we win 13.7%),
  theirs first 322 (87.9%), neither 256 (54.3%), **no Prism drafted 195 (50.3%)**: the whole gain is in Prism games;
  the ~20% of games without a Prism (mostly 5-pick Cassi&Issac/HoR/Ren-or-Varg/Vendetta/Vesper) are untouched.
- 06:19 C9 (premium in kills/risk/turn order, implementer's): train 52.8 / 52.9 / 52.8 / 53.0 across
  variants: level with v4 (53.0). C8 (route onward value): v1 28.1 (fuel), train3 38.5 (OOF 16k), train3b 50.1
  (49.1-51.1, OOF 1,263 vs 645): below its base c7a (52.8). Asked C9 to wrap up and take C6 next (on v4).
- 06:20 C10 brief (`briefs/c10-open-premium.md`): the opening plan (r1-100, solved in the draft) values gems without the premium and names the best-gold-bonus attendee as holder, exactly when the premium is ~3; give it the premium and a value holder. Sent to the C8 implementer after it wraps up C8.
- 06:20 Early Prism share (c7 train1 replays): r60/100/150 0.639/0.609/0.594 vs chy-ref 0.544/0.515/0.507; totals equal. The in-play holder logic already moves the plan's payouts, so C10's room is the plan's routes.
- 06:29 **C8 `c8-route` final report: dropped.** Train v1 28.1 (OOF 29,669), v3 38.5 (OOF 16,442), v3base
  (net-value form, no lookahead) 50.1, v4 (rate form kept, penalty-only two-job lookahead, prunes exact) 51.7
  (50.8-52.7), all below the c7 base (~53). Solo v1/v3 +11%/+7% slower to 1000 even with no enemy. Why: the farm
  re-picks every turn, so a one-step lookahead adds little signal; the worth is in priced/weighted units, so a
  measured gems-a-round rho doesn't fit it; any term that lowers values against the prune bounds weakens the
  prunes and blows the fuel. The (1 + r/H) stand-in stays.
- 06:31 Sole-Prism captures (c7 train1 replays): 16.1 a game (chy-ref 15.0), 26 gems each; the Prism
  stands ~4.1 rounds before payout (mode 4), an ally on the tiles in the last 6 rounds 43%. A relay (ally holds,
  Prism arrives for payout) saves ~3 rounds a capture only when the Prism comes from elsewhere; leaving costs the
  premium on 26 gems against ~4 Prism rounds: holding is right. Not pursued.
  Our Prism's first deaths (c7 227 / chy-ref 322 of 1,000): Focus ratio <0.8 38% / 54%, parity 48% / 40%; killer
  the enemy Prism 66% / 64%; no ally within 8 in 31% / 32%; outnumbered within 8 in 71% / 72%. Non-Prism games
  (mirror, 147): lifetime gold earned dominates the logistic (kills and captures), gems weigh less.
- 06:48 **C9 `c9-pfight` final report: level, dropped.** Train v1 52.8, killer-premium-only 52.9,
  enemy-premium-only 52.8, stakes/bids only 53.0, final v2 52.7 (v4 base 53.0). Our Prism takes more kills and bags
  (+0.2 kills, +15 gems a game) but Prism deaths don't fall: bag weights reprice fights, they don't change when
  fights happen (the Prism already "falls" in every stand test), and a threatened Prism is usually hurt, so its
  premium is 0 there. C6 (shop timing) train1 (implementer's): 53.5% (52.5-54.5) vs v4's 53.0.
- 06:48 c7m hold/conf A/Bs started (does the medic add on top of c7?).
- 06:50 c7s = c7 v4 + C3 stun screen (final, mechanical patch + screen.cc): train A/B started.
- 07:02 c7m hold 53.3% (51.9-54.7) of 5,120 (c7a hold 52.7): medic stays a small plus on c7.
- 07:02 Prism hazard (c7 train1 replays, both teams, rounds before the first Prism death with an enemy within 8;
  `scripts/phazard.py`): first death within 5 rounds per 1,000 rounds, by allies within 8 x enemies within 8:
  0 allies 13.3 / 27.7 / 50.9 (1/2/3+ enemies), 1 ally 6.6 / 11.6 / 41.3, 2 allies 4.5 / 4.8 / 18.2, 3 allies
  2.0 / 3.9 / 8.9. Deaths concentrate in 3-enemy rounds (1,653 of 2,645), 29% with 0-1 allies near. At threat
  onsets (`scripts/ponset.py`) the nearest ally is within 4 in 73%; onsets with it 9+ tiles away die within 15
  rounds 3.5% vs 1.1%: escorting in advance would save ~6% of first deaths (<1 point). The losses are team fights
  the Prism is caught in, not lone wandering. Not pursued as macro.
- 07:10 c7m conf 53.6% (52.6-54.6) of 10,240 (c7a conf 52.7). **c7m = v4 + medic is the best so far:
  train 53.8, dev 53.2, hold 53.3, conf 53.6.** C6 train2 (implementer's) 52.5 (51.6-53.5); train1 was 53.5.
  By map family (c7m hold, `scripts/byfamily.py`): no class stands out (gen-ladder 52.3, classic 53.3, huge 45 +-11).
- 07:17 c7s (v4 + C3 screen) train 53.5% (52.5-54.5), OOF 1,041 vs 640: about +0.5 over v4, like the medic.
- 07:17 **Endgame finding** (c7 train1 replays; scripts end*.py, tstart.py). R1000 = first round score + living
  bags >= 1000. The winner's Prism holds a median 580 at R1000. The win comes a median 73 rounds later (mean 150)
  with a Prism, 18 without. Its final tribute first starts ~11 rounds before R1000 and completes first time in about
  half the games. The top quarter takes 5+ starts, 41+ cancelled channel turns and 151+ rounds to win; the top tenth
  20 starts, 245 turns and 436 rounds. Near-end cancels average 3.1 stuns, 1.3 locks and 1.4 own a game. The first
  team to R1000 wins 87-88% with a Prism and 94% without; when both reach it, the first wins only 51% (224/1000
  games). Prism tribute starts with 100+ gems complete 4% with an enemy within 8 (mostly opportunistic starts we
  cancel ourselves), 23% at 9-15, 50% at 16-25, 38% at 26+, over a mean channel of 70 turns. Mechanism: one long
  channel that a stun or a lock restarts from zero, whose expected time grows as e^(lambda b). Brief C12
  (`briefs/c12-endgame.md`): installment banking priced against the premium, then the final start.
- 07:44 **C6 final report (c6-v4):** train v1 53.5, v2 (no EOQ) 52.5, v3 (v1 + farm_recall visit credit) 54.2,
  v4 (v3 + audit fixes) 54.1 (53.2-55.2). OOF 839 vs 701. The premise was mostly wrong: 82% of the Prism's recalls
  are farm recalls (`recall_to_farm`), not `wants_shop` trips. The gain came from `farm_recall` crediting the next
  emblem's gain as now-or-never; it now credits gain x min(1, visit_rounds / T), where visit_rounds is the measured
  rounds between home visits (prior 107 from chy-ref's 5.6 recalls by r600). It also adds EOQ shop timing with
  transport and heal credit. Solo farm speed is level. Walk dithering (the farm choice changes ~2.4 times a walk)
  was noted but not fixed.
- 07:44 C10 train2 52.6 (train1 52.3): level or below. Asked it to wrap up.
- 07:44 **c11-int** = c7-pgem + medic + screen + c6-v4 shop. The patches apply cleanly (only offsets;
  one screen hunk with fuzz); bot.cc's screen and medic edits are disjoint (non-Prism/non-Willow screen vs
  Willow medic). Smoke 55.1% of 256, 0 failed games, no DRAFT-UNFINISHED / PLAN-CHECK / DRAFT-CAPPED, OOF 34 vs 29.
  Train1 started. Patches: `patches/c11-int.diff` (vs c7-pgem), `c11-int-full.diff` (vs chy-ref).
- 07:55 **c11-int train 54.8% (53.8-55.7), dev 55.3% (54.3-56.2)**, both 10,240 games. OOF 1,065 / 990 vs
  667 / 590. The pieces add: v4 53.0 -> c11 ~55. Hold and conf started.
- 08:02 c11 hold 53.8% (52.4-55.1) of 5,120 (c7m 53.3, c7a 52.7). x1 started.
- 08:06 **C10 final report: dropped.** Train v1 52.3, v2 52.6, v3 52.6, all below v4's 53.0. The plan only sets the first
  group steps, and c7's in-play holder logic already moves the gems to the Prism (the Prism's early share lead over
  chy-ref is unchanged at +0.10/+0.09/+0.08 at r100/150/200). First-turn headroom fell to 1.27M on the heaviest map.
- 08:06 C12 (endgame, implementer's) train1 54.5 (53.6-55.5), level with c11's 54.8; it is iterating.
  C13 brief (`briefs/c13-dither.md`): why the farm choice changes mid-walk (C6 found 2.4 changes a walk). Launched on c11-int.
- 08:08 c11 conf 54.3% (53.4-55.3) of 10,240 (c7m 53.6, c7a 52.7).
- 08:12 **c11 x1 56.0% (55.1-57.0)** of 10,240 (c7a 53.5). c11 summary: train 54.8, dev 55.3, hold 53.8, conf 54.3, x1 56.0.
- 08:12 Ablations on dev (c11 read 55.3): c11-noscr (= c7m + c6 shop) and c11-noshop (= c7s + medic; differs from c11 only in shop.cc) started.
- 08:22 **Ablations on dev** (c11 55.3, OOF 990 vs 590):
  - Without the screen (c11-noscr): 55.1 (54.1-56.0), OOF 686 vs 601. The screen adds ~0 and is the OOF source.
  - Without the shop timing (c11-noshop): 52.8 (51.9-53.8). The C6 shop/farm-recall piece is worth ~+2.5 on dev.
  c11-noscr's conf A/B started (c11 conf 54.3). C12 train2 (implementer's) 54.4 (53.4-55.4).
- 08:28 c11-noscr conf 54.4% (53.5-55.4), OOF 785 vs 628 (c11 54.3, OOF 992). **The screen is dropped:** level on
  two suites and the main OOF source. The candidate is now c11-noscr (v4 + medic + shop); its hold and x1 started.
  Patches: `patches/c11-noscr.diff` (vs c7-pgem), `c11-noscr-full.diff` (vs chy-ref). C13 train1 (implementer's) 53.0.
- 08:35 c11-noscr hold 54.7% (53.3-56.0) of 5,120, OOF 379 vs 313 (c11 53.8). C12 train3 42.9 (a broken variant, implementer's), C13 train2 53.0.
- 08:36 **c11-noscr x1 55.7% (54.8-56.7)**, OOF 704 vs 590. c11-noscr summary: dev 55.1, hold 54.7, conf 54.4,
  x1 55.7 (c11 55.3 / 53.8 / 54.3 / 56.0). Its train A/B started for reference.
- 08:36 Asked C13 to wrap up (53.0 twice). C6g, sent to the C6 implementer: extend farm_recall's visit credit
  (a skipped purchase is made at the next visit, gain x min(1, visit_rounds / T)) from the Prism to every body,
  then try EOQ wants_shop for the non-Prism branch. The same mispricing applies to every body.
- 08:39 **C12 final report: level, dropped.**
  - Readings: train v1 54.5, v2 54.4 (c11 54.8). v3/v3b, which add the bag's death risk to the keep side, read 42.9.
    That model makes the Prism bank far too early: the Focus premium outweighs it.
  - The rule (`banks_installment`): bank when the end cost R x C(s) exceeds the bank-now cost r(1+p)(2 near + C(s))
    + B p, with C(s) = (e^(lambda s) - 1) / lambda. lambda has a Gamma prior of 0.0117 a turn and stays near it in
    game (median 0.0107).
  - It fires in 78/256 games, at a median r559 with 555 gems: an earlier final bank, not mid-game installments.
  - Endgame effect: Prism bag at R1000 610 -> 538; R1000-to-win lag median 80 -> 62.5, p90 543 -> 445; stuns near
    the end 4.96 -> 3.48. But first-to-1000 Prism win % 88.1 -> 87.4, and Prism-side wins 397 -> 390.
  - A faster end that doesn't win: the Focus given up offsets it. Piece 2 (completable final starts) was not
    pursued, since `tribute_safe` can't cover 50+ turn channels.
- 08:39 **C13 final report: dropped.** v1 (`retreat()` keeps the claim) and v2 (keeps it except a heal retreat)
  both read 53.0 on train. Cause analysis over 2,048 debug mirror games:
  - The "2.4 changes a walk" was an artefact: 0.26 farm_group switches a walk segment.
  - Switch causes: old group done 37%, ally claim changed 25%, camp state 16%, nothing visible 11%, camp health 9%.
  - 24.6% of posted claim changes revert within 3 rounds, mostly farm -> retreat -> farm (`retreat()` posts -1).
  - Keeping the claim lost: the -1 is information allies use (crew output, rivals, pick_up, Willow follow).
- 08:41 c11-noscr train 55.2% (54.2-56.2), OOF 755 vs 715.
- 08:46 C6g train1 (implementer's; visit credit for every body) 55.4 (54.5-56.4), level with c11-noscr's 55.2. Generating a fresh x2 suite (seeds 141500-141519, ladder-v2) for a final independent read.
- 08:50 **C6g final report: level, dropped.**
  - step 2 (visit credit for every body, body-neutral prior of 90 rounds a visit from chy-ref's solo recalls plus
    respawns): train 55.4 (54.5-56.4).
  - step 3 (+ EOQ wants_shop for non-Prism bodies): 55.2. Reference c11-noscr: 55.2.
  - So the C6 gain is all in the Prism-only piece.
  - Visits by body vary 56 (Vesper) to 179 (Willow) rounds.
- 08:50 c11-noscr on a fresh x2 suite (141500-141519) is running. Medic ablation (c6-v4 = c11-noscr without the medic) on dev started.
- 08:51 **c11-noscr x2 (fresh) 55.8% (54.8-56.7)**, OOF 733 vs 633. c14-end = c11-noscr + C12 v2 (mechanical port) on dev and x2, to see whether endgame banking adds on the final base.
- 08:54 Medic ablation: c6-v4 (c11-noscr without the medic) dev 54.3% (53.3-55.3) vs 55.1: the medic is worth ~+0.8, kept.
- 08:56 c14-end (c11-noscr + C12 endgame banking): dev 54.8 (53.9-55.8), x2 55.7 (54.7-56.6), against c11-noscr's 55.1 / 55.8: level, dropped. **Final: c11-noscr.** Generating a varied-mix robustness suite (seeds 141600-141609).
- 08:59 c11-noscr on a fresh --mix varied stress suite (141600-141609): 53.1% (51.7-54.5) of 5,120, OOF 758 vs 703. bots/charybdis = c11-noscr, committed (b36621954).

## Final (written 09:0x UTC)
**Best: `bots/variants/c11-noscr`, copied to `bots/charybdis` (commit b36621954).** Diff vs chy-ref:
`patches/final-charybdis.diff` (= `c11-noscr-full.diff`).

Its three pieces:
- **C7 Prism gem premium** (economy/capture.cc, farm.cc, bot_parts.h).
  - `prism_premium(a, gems)` = expm1(k rho H): Focus per gem -> camp output -> the team's gems per output-round,
    compounded over the rounds the bag stays kept. Zero past the win or when the bag won't be kept.
  - It is used in every decision of who gets a group's gems: the Prism's farm (`keep_most`/`keep_bonus`, replacing
    `carried_bonus`), `holder_value` (x (1 + premium)), `multiplies`, leave-for-Prism (`worth_wait`), handoffs,
    and the allies' crew/claim feeder pricing.
  - The gain is consistency: the allies now value the Prism's gems as the Prism does.
- **C2a Willow medic** (bot.cc, support.cc, farm.cc, shop.cc). Out of a fight, with her mate not needing her,
  Willow heals the ally whose next heal saves the most farm rounds, net of her walk.
- **C6 Prism shop / farm-recall timing** (economy/shop.cc).
  - A purchase skipped at a farm recall is made at the next visit home, so the stop's emblem credit is
    gain x min(1, visit_rounds / T), with visit_rounds measured in game (prior 107).
  - EOQ shop trips: G >= sqrt(2 cost D / h), with transport and heal credit.

Readings against chy-ref, 2x fuel:

| Suite | Win % (95% CI) | Games |
|---|---|---|
| train | 55.2 (54.2-56.2) | 10,240 |
| dev | 55.1 (54.1-56.0) | 10,240 |
| hold | 54.7 (53.3-56.0) | 5,120 |
| conf | 54.4 (53.5-55.4) | 10,240 |
| x1 | 55.7 (54.8-56.7) | 10,240 |
| x2 (fresh) | 55.8 (54.8-56.7) | 10,240 |
| varied | 53.1 (51.7-54.5) | 5,120 |

Ablations on dev:
- without the shop timing: 52.8;
- without the medic: 54.3;
- with the stun screen added (c11-int): 55.3 dev and 54.3 conf, level, with ~+300 OOF turns, so the screen is out.
- 09:12 Final outcome split (c11-noscr hold rerun, 1,000 replays, `scripts/split.py`):

  | Case | Games | Our win % |
  |---|---|---|
  | Our Prism dies first | 231 | 15.2 |
  | Theirs dies first | 308 | 89.9 |
  | No Prism death | 237 | 52.7 |
  | We drafted no Prism | 224 | 50.4 |

  c7 alone read 227 / 322 / 256 / 195 games at 13.7 / 87.9 / 54.3 / 50.3.
  The gain is in Prism games: fewer first deaths and better conversion in each case. The ~22% of games without our
  Prism are still level, which is the clearest place for the next programme.
- 09:18 c11-noscr on a fresh x3 suite (141700-141719): 55.0% (54.1-56.0) of 10,240. Pooled over held-out dev/hold/conf/x1/x2/x3: 55.2% of 56,320 (+-0.4).
- 09:23 c6g held out: dev 55.3 (54.3-56.2), x3 54.8 (53.9-55.8), against c11-noscr's 55.1 / 55.0: level. The final stays c11-noscr.
