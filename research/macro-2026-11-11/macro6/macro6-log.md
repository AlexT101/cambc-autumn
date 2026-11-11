# macro6 running log

Lead's log for the macro6 refactor of ocean (brief: macro6-brief.md). Newest entries at the bottom.

## Setup (2026-11-11 ~01:40)
- Worktree /home/ubuntu/wt/macro6, branch macro6-20261111, base b7c87cf. bots/ocean == variants/ocean-ref-b7c87cf (test_draft off).
- Maps: /home/ubuntu/wt/macro6-maps/s-600001 .. s-600040 (ladder-v2, 256 maps each). Plan: s-600001..600020 dev (10k games), 600021..600040 confirm.
- A/B command: prefix from the brief; `py tools/ab.py variants/macro6-X variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000 --suites ... --name macro6-X`.

## Plan
1. Baseline mirror (ref copy vs ref) with all replays kept: time-trajectory study of how games are decided.
2. Prior-research survey (subagent) + code survey of farm/bank/target selection.
3. Design a coherent macro refactor from the trajectory findings; implement via subagent; A/B at 10k.

## Baseline mirror (macro6-mirror == ref), s-600037..40, 2048 games, 2.2 min wall (~55k games/h on the shared box)
- 50.0% exactly (deterministic: each map 1-1). OOF 132 turns each.
- 97.4% end by 1000 gems; end round quantiles p10 485, p25 600, p50 755, p75 1007, p90 1312.
- Leader-predicts-winner (held = tributed+carried): r100 57%, r200 62%, r300 69%, r400 75%, r600 83%. Gold lead plateaus ~80%. Kill lead r300 70%, r600 79%.
- Winner vs loser per game: capture gems 1007 vs 786; kill gems 193 vs 51; champion-kill deaths 3.3 vs 8.1; gems lost 56 vs 191; dead time 4.6% vs 10.5%. First kill side wins 64% (median first kill r189).
- Time share (winner): move_bag 26.7, move 25.6, camp 18.4, recall 6.1, still 5.2, hold 5.2, dead 4.6, tribute 3.0, fight 3.0.
- Deaths mostly at 0.3-0.5 of the way to the enemy spawn (our side of the middle); numbers at death are mixed (team fights 4v4 and 1v1 duels most common).
- Unspent gold small (15-60 for losers), shop spending is fine. Carried gems 30-55 a champion.
- Rough gem-equivalent cost of a death: ~60 (60 rounds of a body ~20 gems of income, bag ~20 to the enemy, +100 enemy gold). Losers' 4.8 extra deaths ≈ the margin.

## Prior survey (subagent) key points
- Gains so far: more time at work + exact pricing (crew economics +10 in astraeus; min_bank 25 +4; recall-out-to-farm).
- Losses: anything pulling bodies off the farm (hunts, duos, packs, summons, escorts, guards, team sieges, follow-group early 39%).
- Untested: crews paying through what the farm rate leaves out (fewer deaths, fewer stolen clears); respawn-timed crews; one home visit heals+shops+banks; chase persistence; cohesion as execution.
- Fish packs 77-83% of bodies with no throughput cost (17.8 vs 18.1 camp damage per champion-round); top teams' death rate at contact with an ally near falls 16->5%, ours ~18%.
- We lose 74 gems/game on groups where we did most damage vs 22 the other way (old data).

## Code survey key points
- farm: greedy per body, rate(w,r)=w/(r(1+r/H)); worth = home_ground^1.89 x (gems + per_gold x gold) x exposure; shared pick for joining an ally's claim values part = S x rounds/health; crews for strong groups.
- No team plan beyond the opening plan (r<=100). Nothing changes aggression/banking/spread when leading; only comeback (behind) and altar_guard.
- Hooks for a strategic layer: farm weight product (farm.cc ~1793), prices() (shop.cc 530), bankable_bag/min_bank, recall_line/pack ratios, branch flags in decide. Obstacle: farm prunes assume weight <= exposure bounds.

## Ops note (01:57)
- The session scratchpad is SHARED with other leads (macro2/macro5 overwrote my ab.sh). Use /home/ubuntu/wt/macro6-work/ only: ab6.sh NAME A B [args] runs variants/NAME vs ref on s-A..s-B, log in macro6-work/logs/. Subagents must write there too.
- Probes launched (2 suites s-600021..22, 1024 games each, directional only): homelo (home_power/2), homehi (x2), goldlo (gold price x0.6), goldhi (x1.6), bank45 (min_bank 45), nomid (mid_exposure 1.0).
- Probe results (1024 games each, ±3): homelo 49.8, homehi 48.2, goldlo 48.9, goldhi 49.3, bank45 49.9, nomid 48.1. All flat/slightly negative: the scalar landscape (territory weight, gold price, bank size, middle premium) is flat around the tuned point. Confirms: no knob path; need structural change.

## Replay-study aggregates (subagent, interim agg.out)
- Biggest 100-round swing per game: primary cause kills 45%, middle captures 34%, own captures 20%. Swing start median r507 (0.69 of game length).
- Champion-kill deaths: 64-72% in the middle zone; 'grouped' (ally within 5) deaths are the majority (loser 4.1/game grouped vs 1.4 isolated-vs-2+); outnumbered 41%; victims at 0.95 hp 10 rounds before (not camp-weakened); counter-kill within 15 rounds only 5-17% (fights are one-sided).
- Loser's alive count falls over the game (5.4 -> 4.3 by r1000 vs 4.96 winner): snowball via deaths.
- Middle capture gems winner 441 vs loser 263; own 552 vs 520; enemy-side ~0 for both. The middle is the battlefield.

## Replay study final + my Prism analysis (02:10)
- 80% of mirror games have Prism on both sides (draft fixed). Prism games end r693 median vs r1122 without.
- Prism +1.5 Focus/carried gem; ocean's Prism retains its bag (retaining_gems) until winning/closing. Prism max bag median 417, p90 864.
- Big-bag (100+) Prism deaths: 0.41/game; victim's team loses 87%. Killers: Prism 56% (bigger-bag Prism wins 65%), Vesper 28%.
- Prism-bag lead (30+) predicts the winner: r200 67%, r300 72%, r400 75%, r500 77% (stronger than overall held-gem lead). Mean Prism bag W/L at r300 140/96; others' bags ~45 a team; tributed ~200.
- Fights: side carrying 200+ more gems wins 83-86% of fights even outnumbered (Focus). Numbers matter at equal bags: 42/49/55%.
- Cascades: 43% of loser deaths come 4-60 rounds after another own death; counter-kills rare (5%).
- Conversion: huge Prism bags (800-2000) start/cancel tributes and can't convert; winners carry 250-280 from r500.

## Design A: "carry economy" (Prism as the team's gem sink)
Mechanic: a gem on the Prism scores the same once tributed but adds 1.5 Focus meanwhile; a Focus shard adds 8 Focus for 30 gold, so a gem on the Prism is worth 1 + (1.5/8)*30*per_gold gems (per_gold = the shop's gem price of gold, falling to 0 as the game closes). Allies' captures handed to the Prism also spare them bank trips.
Implementation: holder_value adds that bonus for gem_focus holders; Prism may take over allies' gem captures (farm's 'T' takeover path, takes_over/may_take_over); allies yield when it arrives.
- Conversion study: winner's latency from held>=1000 to the win median 31 rounds (p75 70, p90 153); in 186/1024 games the eventual loser held >=1000 at some point, in 73 it got there first and still lost (big-bag deaths after 1000: 0.63/team). Candidate design C: closing protocol (later).

## Design B: numbers posture (Lanchester) — implementing in parallel with A
- Farm worth of middle/enemy-side groups x m = min(2, (alive_us/alive_them)^2); own ground unchanged; opening plan unchanged. Targets the cascade deaths (43% of loser deaths come 4-60 rounds after another own death).
- Fight narrative (game 600038-143): B's Prism, bag 361, soloed a middle Elk down to 35% hp seeing no one; A's Prism's blind AoE (ground spells hit unseen units) killed it (+361). Later A's Prism (bag 638-699) repeatedly started 64-turn tributes at the enemy-side altar and was killed by a Vesper.
- Design D idea: stakes-aware risk. The recall line / camp risk ignore the bag: a 361-bag Prism uses the same health line (0.11 when no threat seen) as an empty body, although its death costs life + 2x bag. Price the line by stakes.

## Result B: macro6-posture 48.3% of 10240 (CI 47.4-49.3), s-600001..20. OOF 491 vs 474. 10k games take ~1.5 min wall.
- Lanchester posture on farm worth loses 1.7. Ceding the middle while outnumbered (and/or over-pushing when ahead) costs more than the cascade deaths it saves. Consistent with prior "farm value halved near enemy reach 41.5%": middle presence is valuable; avoid the risk through better fights/stakes, not by leaving.

## Result A: macro6-carry 54.1% of 10240 (CI 53.1-55.1), s-600001..20. OOF 459 vs 460. +4.1: the Prism gem economy is a real lever.
- Implementation: holder_value gems x (1 + carried_bonus), bonus = price*(1.5/8)*30 for a Prism keeping its bag (keeps_bag: below the win, time to bank, health >= hurt line); allies' holder comparisons use holder_gold_price 0.3 (consensus), takeovers use prices().per_gold. Prism may take over ally gem holds ('T'); multiplies() true for a keeping Prism on gem groups. Takeovers rare (0-3/game), yields to Prism 0-24/game.
- carry held-out s-600023..36: CAND 53.9% of 7168 (3864-3304), 95% CI 52.8-55.1
- Conversion in carry games: CAND held>=1000 first but lost 95/2048 (REF 101). Pattern: a Prism with 430-750 gems at held>=1000 starts 30-70-turn tributes, cancels manually/stun/lock repeatedly, then dies; also start/cancel loops of mid bags (Issac 77 x4). Design C (closing protocol) potential ~+2.

## Result D: macro6-stakes 48.8% of 10240 (CI 47.8-49.7). Carriers (bag >= brake_bag) using the threatened line plus a one-turn enemy burst floor: -1.2. Caution costs time at work; like posture, risk reduction by leaving work loses. Lesson so far: gains come from making the work itself pay more (carry), not from avoiding risk.

## Result A2: macro6-carry2 55.2% of 10240 (CI 54.2-56.2), s-600001..20 (+1.1 over carry on the same maps). OOF 431 vs 446.
- carry2 = carry + the Prism's 'J' join of an ally's claimed gem group valued rate(worth*part + gems*carried_bonus, trip + rounds + hold + trips) with prune bounds widened, health-gated (no bonus if the join's expected camp damage takes it below hurt_health_fraction). In 16 debug games: Prism 'J' picks 220 -> 398, but Prism-solo captures fell (112 -> 65) and J-to-J flips rose; share of team capture gems paid to the Prism ~40% in both.
- Next: carry3 = the Prism's own solo/crew values also carry the Focus bonus (coherent pricing on every path).

## Conversion study (subagent; /home/ubuntu/wt/macro6-work/convstudy/)
- Blown (95/2048): Prism holds a 216/418/539 bag needing 28-57-turn channels at a mid altar with enemy stunners 4-6 tiles away; long Prism channels complete 2% (won games 16%). 37/95 the Prism dies there (median 534 gems).
- Completion by length: 4-5 turns 94%, 9-11 78%, 12-16 55%, 25-34 34%, 35-49 20%, 50-74 13%, 75+ 4%. Nearest live enemy stunner >8 tiles at start: 12-24 turns 72% vs 27% within 8; 25-49 55% vs 10%.
- Loop: mite_tribute_habit (bank.cc:1206) starts a channel at turn end with no tribute_ok; continue_tribute cancels next turn when want_home flips (bank.cc:1328-1338); carry_bag waits at the altar (wait_altar; unreachable other altar on one-altar maps -> waits forever) and the habit restarts it.
- Proposed: (a) start long channels only inside a stun-free window W (min over enemies of time until they can stun/lock: visible stunner max(cooldown, steps to reach); dead stunner respawn + walk; lock carriers' steps); don't park outside a window; (b) choose the altar by window; (c) cap the Prism's retained bag at what the respawn horizon can bank; (d) allies keep farming; (e) don't cancel inside the window on want_home alone.

## carry3 (2026-11-11 03:10)
carry2 + the Prism's solo (S/K), kited, risky and crew (C) values carry the Focus bonus (`gems*carried_bonus`), J unchanged (no double count); every before-facts bound adds `keep_most` to the gem price. Non-Prism arithmetic bit-identical.
- s-600001..20: carry3 56.0% of 10240 (55.1-57.0) vs carry2 55.2%.
- held-out s-600021..40: carry3 56.2% of 10240 (55.2-57.1); carry2 55.0% (54.1-56.0).
- pooled 20480: carry3 56.1%, carry2 55.1%. carry3 is the new best (+1.0, consistent on both halves).
- Debug sample: Prism solo captures 65 -> 105, Prism's share of team capture gems 0.39 -> 0.44.
- Open from its audit: no health gate on S/C (Focus counted when the clear may leave the Prism below hurt_health_fraction); C scales the bonus by part.
Patch: patches/macro6-carry3-vs-carry2.diff.

## close (closing protocol, on carry2) -- FAILED, not A/B'd (2026-11-11 03:50)
Stun-free window gate on >11-turn channels (enemy stun/lock reach from position/fog/respawn), altar choice by window, no park outside a window.
Local sample, 174 debug games vs ref (72 study-loss maps + 15 one-altar maps, both sides): carry2 96 wins (55%), close 43-46 (25%).
The gate fitted 0 of 289k checks (median window 49 turns short of the channel): fog grows unseen enemies a tile a round and
ladder maps are too small for a 20-50-turn channel to fit any reach-based window. Blocking the non-fitting starts (which do
complete ~11%) leaves the bag out on the map: Prism deaths with 100+ gems 41 -> 70. Lesson: a long channel never gets a
provable window; the only real window is a won fight (enemies respawning). Code: bots/variants/macro6-close (scratch).

## Endgame anatomy (carry3 games, s-600001..4, 2048 games; endg/ scripts)
- A side that holds a winning bag (score + one champion's bag >= 1000) wins ~91% (CAND 1145 of 1255 such games, REF 869 of 969).
  The game is the race to a winning bag; conversion failures are ~110 of 2048 games for CAND.
- Winning (>11-turn) channels complete ~11% per start for both sides: 1% with an opponent within 4 of the altar, 36-38% with all
  >= 15 away (then only ~2 of 5 opponents alive). Windows come from kills.
- In Prism games CAND's Prism tributes ~1.1 times in won games (one winning dump, 488 gems), lost games end with its bag at 152 mean
  (203 of 684 losses with 200+).

## carry4 (carry3 + Focus-aware kill value) -- FLAT (2026-11-11 04:05)
Combat kill values price a bag at pair_gems x (1 + taken bonus if our killer is a keeping Prism + denied bonus if the victim is an
enemy keeping Prism), one helper bag_worth at every gem_value x pair_gems value site. Local 16-game sample looked large
(enemy Prism kills 10 -> 33), but at scale nothing moved:
- s-600001..20: 56.0% of 10240 (55.1-57.0) = carry3's 56.0%. Kills 5.8/5.1, deaths 5.1/5.8, big Prism deaths unchanged.
Lesson: kill choice is not the bottleneck; bags already dominate kill values (life_value is ~16 gems), so a larger bag price
reorders little. Small local samples mislead again.
Prism duels (carry3 games): our Prism dies 985 times vs theirs 1384; Prism-on-Prism kills 869 ours vs 504 theirs; big-bag (100+)
deaths 366 ours vs 421 theirs (bags ~114k vs ~121k gems): ours carries more, so it loses about as much.

## Probes: carried-bonus scale (carry3 x K), s-600001..20, 10240 games each
- K 0.5: 54.2% (53.2-55.1); K 1 (carry3): 56.0%; K 2: 55.6% (54.7-56.6); K 4: 54.9% (54.0-55.9).
- The shard-price valuation is at the optimum; the carry line is calibrated, not under-priced.

## Trajectory / time-use studies (carry3 games, endg/ scripts)
- Time use (champion-rounds): walking ~48-50% all game; camp attacks 27% (r0-150) -> 10% (r700+); idle 7-11%; dead 2.5% -> 10-15%.
  Paths are direct (net/step ~1); holds have ~1.06 holders; gold is spent promptly (~10% unspent). No single waste.
- Supply is not saturated: groups wait median 19 (home) / 41 (mid) rounds early, 9-16 mid-game. Home groups go ~97% to the
  owner; the middle splits 52/48 for carry3. Champion time binds, not supply.
- Lead at r300 decomposes into capture diff (sd 119, carry3 +25) and 2x kill-gem swing (sd 117, +4): equal weight.
  At r300 a 150+ asset lead wins 90-95%. carry3 wins 56% of games level at r50-r100 (the Focus pays later).
- Monolith maps 29% of games; who captures more of it wins 86%, but only 186 of 600 such games differ.
- **Prism as the fight engine**: our non-Prism kill/death ratio is ~2 within 8 tiles of our Prism, 0.8-0.9 farther (ref 1.2-1.35 near).
  While our Prism is dead, our other champions die at 4.2-8.7 per 1000 alive-rounds vs 1.03 while it lives, even 30-62
  rounds after its death (confounded by game state, but large).
- **Prism deaths**: 39% of its time in the middle but 69% of its deaths (per-round rate x1.78 vs own x0.47), bags 152 vs 78;
  75% die in fights (from >=80% HP 10 rounds before in 58%); 28% with no ally within 6, 26% with one.
- Prism bag lost to deaths: 75 gems/game ours, 84 theirs; every other champion ~10.

## carry5 (carry3 + audit fixes: health gate on S/C, Prospector count, no bonus while banking) -- not better
- s-600001..20: 55.3% of 10240 (54.3-56.3) vs carry3 56.0% on the same maps. Dropped: the gate counts whole-job damage
  including trips home (cuts at full health), so it mostly removes good Prism clears. carry3 stays best.

## Prism-down study (corrected): our non-Prism deaths per 1000 alive-rounds
- own Prism up, none else dead 0.89; one other dead 3.13; own Prism DOWN, none else dead 3.92; enemy Prism down 0.60.
  Head count matters about as much as the Prism; posture by head count already lost, so a Prism-keyed posture is not pursued.
- Prism hazard marginal over enemies does not depend on allies within 6 (fights bring both): cohesion would not cut Prism deaths.
  Zone does: own ~3.5e-4/round, middle ~11.4e-4, enemy side ~2e-3. -> pzone (stake-priced zones for a keeping Prism).

## carry3 fresh confirmation
- s-600041..60 (fresh): carry3 55.2% of 10240 (54.2-56.1). Pooled carry3: 55.8% of 30720 games over s-600001..60.

## More studies (carry3 games)
- Cassi&Issac (96% of games): pair death hazard does not rise with separation (0.66-1.03% per 6 rounds at any distance),
  and together they earn half as much (0.12 vs 0.30 capture gems/round): splitting is right. Dead end.
- Prism time: farm 21% early (ref's Prism 25%), holding 13%, idle 11-12% with or without Willow; hold_capture already hits camps.
- Allies in the middle within 6 of our Prism: deaths 1.11/1000r (same as far, 1.15), kills 1.40 vs 0.83 (1.7x). Cohesion around
  the Prism would add ~+0.3 kills/game at most (selection-biased): about +1 point upside; not a big lever.

## pzone (carry3 + stake-priced zone risk for a keeping Prism) -- LOST
- Loss = job rounds x (measured extra hazard: middle 7.9e-4, enemy side 1.6e-3 per round) x bag x (2 + bonus), on every Prism path.
- s-600001..20: 54.5% of 10240 (53.5-55.4) vs carry3 56.0%: -1.5. Local sample: Prism capture gems -10%, middle share down.
- Fourth risk-reduction design to lose by 1.2-1.7 (posture, stakes, pzone; carry5's gate). The bot's risk pricing is
  near-optimal: pulling the Prism off the middle costs more in captures and the fights it wins there than the deaths it saves.

## Thrown leads and the variance principle (carry3 games)
- 153 of 1099 games with a peak asset lead >= 150 were lost (7.5% of all games), 136 with our Prism; the reversal is a sudden
  ~350-gem swing in 30 rounds (a Prism death). Winning-bag holders gain little after first holding (Prism: +5 capture gems,
  +82 kill gems) and win 94%: conversion is not the leak.
- Our Prism's deaths by lead at the time: behind 150+: 421 (bag 53, won after 3%); level: 218 (bag 141, 17%); ahead 50-150:
  93 (bag 189, 25%); ahead 150+: 111 (bag 341, 46%).
- P(win | asset lead) ~ sigma(0.018 x lead) at every phase.
- Principle: in a race, variance hurts the leader and helps the trailer. pzone taxed the Prism in all states (lost); posture
  pushed when ahead and ceded when behind (the reverse of the principle; lost). -> pzone2: price the Prism's stake by the
  win-probability drop a death causes, (sigma(kL) - sigma(k(L-S)))/(k/4), so level games are taxed ~1/4 of pzone, leads more.

## postup (04:35 UTC)
carry3 plus upside-only posture: off-ground exposure and bounds lifted by `max(1, min(2, (alive_us/alive_them)^2))` after round 100, with Cassi and Issac counted as one unit.
- **Result:** 55.6% of 10240 (CI 54.6-56.5) on s-600001..20. carry3 scored 56.0% there, so this is flat.
- **Reading:** pressing a numbers advantage over the field doesn't add value. The leader seeking more variance is neutral at best, which is consistent with the variance principle.
- **Verdict:** dropped.

## pzone2 (04:40 UTC)
pzone, with the stake priced as the drop in win probability: `(σ(kL) − σ(k(L−S)))·4/k`, where k = 0.018 is the measured slope.
- **Result:** 56.1% of 10240 (CI 55.1-57.0) on s-600001..20. pzone scored 54.5% and carry3 56.0%.
- **Reading:** the lead shaping removes pzone's 1.5-point loss but adds nothing over carry3. The estimate of L is +106 biased, because the enemy bags it uses are stale.
- **Conclusion:** Prism risk-pricing is closed. Neither the linear stake nor the win-probability stake beats no explicit risk term.

## Tribute channels (carry3 vs ref, 2048 games, mean per game)
| Measure | carry3 | ref |
|---|---|---|
| Channels started | 20.2 | 19.8 |
| Starting gems | 2252 | 1842 |
| Channels completed | 17.4 | 17.1 |
| Cancels | 2.67 | 2.54 |
| Starting gems of cancelled channels | 1390 | 1074 |
| ...cancelled manually | 552 | 422 |
| ...cancelled by stun | 548 | 464 |
| ...cancelled by lock | 285 | 184 |
| Locks placed | 4.1 | 4.2 |
| Gold spent in the shop | 4448 | 4452 |

- Bigger bags (the carry economy) lead to more gems in cancelled channels.
- A cancel keeps the bag, so the cost is the time to re-channel plus the exposure, not the gems.

## Rate horizon probes (05:00 UTC)
These probes scale `cycle_horizon`'s 100 in carry3. The draft's copy at draft.cc:278 was left at 100, since the draft is off limits.
| Probe | Win % of 10240, s-600001..20 | 95% CI |
|---|---|---|
| H×0.5 (h05) | 56.0 | 55.1-57.0 |
| carry3 | 56.0 | 55.1-57.0 |
| H×2 (h2) | 54.8 | 53.8-55.8 |

- **Result:** the curve is flat at or below 100. A longer horizon hurts, because it favours long trips.
- **Conclusion:** the horizon is not a lever.

## Kill economy (carry3, 2048 games, mean per game)
- **Our wins:** we kill 8.0 (bags 174 gems) and they kill 3.2 (bags 47).
- **Our losses:** the mirror image: they kill 7.6 (bags 177).
- **Reading:** kills follow the game's outcome. They are not a separate lever.

## carry3, fourth sample (s-600061..80, fresh)
- **s-600061..80:** 55.0% of 10240 (CI 54.0-55.9).
- **Pooled over s-600001..80:** 22764 wins of 40960, 55.6% (CI 55.1-56.1).

## follow (05:25 UTC) -- LOST
carry3 plus a follow-up value for empty-handed jobs: the semi-Markov bias of the job's end position.
- **Formula:** δ_g = max(0, max_{h≠g} W_h/(1+r_gh/H) − ρ̂·r_gh), where ρ̂ is the best rate from here. δ is 0 where neighbourhoods are equally rich.
- **Bounds:** every bound was loosened by rate(Δ, R_lo), with Δ = max δ.
- **Trace:** δ changed the pick on 7% of turns, and Δ averaged about 24 gems.
- **Result:** s-600001..20: 54.2% of 10240 (CI 53.2-55.1), against carry3's 56.0, so −1.8.
  - Out-of-fuel turns: 1171 in 759 games for follow, against 463 in 350 for carry3. The ref had 532.
  - The farm loop was cut short (`farm-partial-evaluation`) about 4× as often, and 15× on large maps.
- **Open question:** this doesn't yet separate the value from its fuel cost.
- **Next:** follow2 keeps carry3's loop and bounds unchanged and re-ranks only the near-best fully valued candidates by base + δ.
- **Patch:** patches/macro6-follow-vs-carry3.diff.

## follow2 (06:06 UTC) -- LOST
carry3's loop and bounds are unchanged. After the loop, it re-ranks the 4 best fully valued own, crew, join and kited candidates by value + rate(δ·part, rounds)·hold, and changes the pick on 2.5% of decisions. Fuel is level with carry3.
- **Result:** s-600001..20: 55.0% of 10240 (CI 54.0-55.9) against carry3's 56.0, so −1.0. Out-of-fuel turns: 496 in 388 games, ref 585.
- **Conclusion:** follow-up value doesn't help even at no fuel cost. The greedy rate with its horizon already captures what locality is worth.
  - The δ estimate ignores competition: the next group may be taken by the time we arrive.
  - It also ignores walls (the distances are Chebyshev).
  - So δ mostly adds noise to a tuned choice.
- **Line closed.** Patch: patches/macro6-follow2-vs-carry3.diff.

## Checked and ruled out without a build (06:30 UTC)
- **Kill windows for banking:** a keeping Prism with 150+ gems, at most one enemy alive, and the dead enemies' respawn covering the channel plus 5.
  - Measured with endg/windows.py on carry3's games: 61 windows in 1636 Prism games (0.04 a game, mean bag 310). The Prism already banked in 54 of them.
  - Nothing to gain.
- **Already priced or handled in carry3:**
  - **Holder valuation:** Vesper's gold and relative efficiency, Marcella's tribute gold, Prospector (capture.cc holder_value).
  - **Clear time:** uses the current Focus (camps.cc camp_output).
  - **Blind ground casts:** at tracked unseen enemies (plan.cc cast_at_enemies).
  - **Turn priority:** turn_order.cc.
  - **Lock and stun stops:** on game-ending tributes (fight.cc ally_stops; bank.cc place_lock).
  - **Comeback gambits:** when far behind (comeback.cc).
- **Prism cohesion, sized:** +0.57 kills per 1000 rounds near the Prism, at about 40 gem-equivalents a kill, is about 0.02 gems a round. Farm rates are 0.5-3, so it isn't worth building.

## carry3 on stress maps (--mix varied, v-610001..20)
- **Result:** 53.5% of 10240 (CI 52.5-54.4).
- **Out-of-fuel turns:** 1129 in 561 games, against the ref's 1047 in 545.
- **Reading:** the gain is smaller on stress maps but positive, so carry3 is robust.
- **Idle by location (endg/idle.py, 2048 games):**
  - carry3 idles for 237,949 champion-rounds in total, the ref for 223,885.
  - Near altars: 18.0% of carry3's idle rounds against 14.0% of the ref's. That is about +5.6 rounds a game, which is the Prism waiting to bank.
  - Too small to build on.

## The Monolith (carry3, 600 Monolith-map games, endg/mono2.py)
- **No captures:** in 371 games nobody captures the Monolith, and in 339 it is never woken. We win 59.3% of those games.
- **First capture:** ours in 123 games (we win 76.4%), theirs in 106 (we win 22.6%).
  - First captures come at round 499 / 649 / 874 (p25 / p50 / p75).
- **Gap:** carry3's `keep_bonus` excludes the Monolith (`!G.has_monolith`, with no reason recorded), and so does the takeover path.
  - So the Prism is biased away from the biggest gem prize on the map, compared with every other gem group.
- **Next:** macro6-mono, which extends the carry pricing to the Monolith's crew and hold paths.
- **Ruled out:** Prism bags above the respawn-window bank (10 × 61 ≈ 610) without a winning bag occur in 260 of 1636 Prism games, which we win 80%. A cap there has little to gain.

## carry3, fifth sample (s-600081..100, fresh)
- **s-600081..100:** 56.5% of 10240 (CI 55.6-57.5).
- **Pooled over s-600001..100, five independent suite blocks:** 28554 wins of 51200, 55.77% (CI 55.34-56.20).
