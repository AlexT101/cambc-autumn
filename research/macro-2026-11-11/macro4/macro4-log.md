# macro4 running log (lead)

Start: 2026-11-11 01:40 UTC. Goal: >=60% vs variants/ocean-ref-b7c87cf over 10k+ games, --fuel 200000.
Brief: research/macro-2026-11-11/macro4-brief.md. Worktree /home/ubuntu/wt/macro4, branch macro4-20261111.
Maps: /home/ubuntu/wt/macro4-maps/s-4000NN (ladder-v2, seeds 400001-400040 generated first).

## Plan
1. Architecture survey (Explore agent) + mirror-game study (replays/narratives) -> structural limits.
2. Design a coherent macro refactor; implement via subagent; A/B 10k games.
3. Iterate.

## Log
- 01:45 mirror study batch (ocean vs ref, debug, s-400039/40, 1024 games, 2 min wall). Mirror stats (macro_stats):
  winners die 2.5/game vs 6.4, kills 6.3 vs 2.3; time: walking 53%, camp hits 18%, hold 4.6%, recall 6%;
  walking out from spawn after recall/respawn ~21% of alive time; ~half the map's gem capacity sits alive and
  unworked (labour-limited economy). Gem/round realised ~1.2 winner, 0.93 loser.
- Architecture survey (Explore): greedy per-body farm choice in turn order, ally claims as a damage-share discount;
  crews by claim inference (fail after 4 rounds, ban 26); no team objective after r100 (open_plan only); unseen
  camps believed alive (no enemy macro model), enemy tracking dies after 3 rounds, sightings never shared; comms =
  claims + one bag slot + one respawn record + healer-only position; fights per-body, only visible allies within 4-7;
  claim stale while banking.
- Priors (EXPERIMENTS): squads/packs/duos/leashes/deathballs all lost (18-46%) — packing costs farm; quill's crew
  economics (pricing heal trips forced by camp damage, crews for strong groups) was the one big macro win (+10).
  Fish: joins (ally_closer +0.73), joint clears 53% vs 42%, carry holds, cohesion 61% vs 45%, small tributes,
  home gate hp<=0.63 or gold>=30. "With an ally near, top teams' contact death rate falls 16->5%; ours stays ~18%".
- Joint clears are sequential (scr/stagger.py on the 512 study games): second dealer arrives 9.6 rounds after the
  first on Elk groups (n=2), 15.4 on Golem; only 7.4 of 15 hit-rounds have 2+ hitting. Joint Elk clears take
  22 rounds and 800 camp damage vs solo 17.5 / 584; Golem 3-dealer 36 rounds / 2124 vs solo 24 / 1410.
  "Crews" are mostly one champion chipping alone, then help arriving.
- Suites: dev = /home/ubuntu/wt/macro4-maps/dev-{a,b,c,d} (seeds 400001-400020, 5120 maps, 10240 games);
  confirm = cf-{a,b,c,d} (400021-400038); study = s-400039/40. A 1024-game A/B took 2 min wall.
- 02:10 replay study (256 mirror games): fights are lopsided (2-0 271x, 3-0 50x vs 101 1-1); first death loses 63%;
  at first deaths an ally is within 4 in 62% but 66% of victims get no ally hitting back (allies within 8: 32% hit,
  32% retreat, 17% keep farming). Victims: retreating 38%, at camp 33%, walking 14%, carrying 10%; 81% in the middle
  band; median hp 86%. Prism 100+ bags = 67% of gems lost to deaths (114 events, victim team lost 83%).
  Home trips: work gap median 30 rounds, 37% of alive time (heal 32%, shop-at-full 24%, bag 22%, recall-as-travel 11%).
  Target churn: 17.6% of alive time walking to targets later dropped (62% untouched by anyone).
- Priors re-read (macro-3): distress/assist + retreat-to-help was level (deaths -8%), roster radius 8 lost at 1x fuel
  ("counted allies don't come"), home_power 0 level (side weighting doesn't matter), claim arbitration level.
- Hypothesis H1: team fights fail for lack of a consistent, committed roster; cohesion has had no value because
  allies don't fight together (ocean's contact death rate ~18% with or without an ally near; top teams 16%->5%).
  Build A = engagement pact (briefs/A-pact.md, variants/macro4-pact). Then cohesion/carrier escort on top if A works.
- Probes (briefs/P-probes.md): p-roster (radii 4->7, pack 6->9: the no-commitment control for A), p-prismbank
  (no Focus hoard), p-stick (stickiness 2.0).
- Idle capacity by type (study games): Golem 62-81% idle, Monolith ~88%, Elk 43-52%, Wolf 47%, gem clusters 23-29%.
  Considered "synchronised strong-group ops" (stage before waking): REFUTED by macro-4 P2 (assemble before waking
  38.4% strict / 48.1% with fallback: bold chips are banked progress). Not building it.
- macro-4 also: removing enemy sightings from comms was +1.7 (sightings feed Safety and make champions give way);
  camp records worth ~7 points; cohesion x1.15/x1.30 level; numbers help moderately (2v1 +0.067 net kills/fight).
  Idea queue: enemy-intent model (discount threats from committed/departing enemies; punish committed ones).
- 02:11 launched probe A/Bs (dev-a..d, --sprt 0.47,0.53, seeds 11/12/13): macro4-p-roster, -p-prismbank, -p-stick.
- 02:25 probes (SPRT 0.47/0.53 stops early, small samples): p-prismbank 30.4% of 263 (H0: Prism's Focus hoard is
  hugely valuable), p-stick 46.4% of 394 (H0), p-roster 54.2% of 306 (H1, tiny sample) -> full 10k run started.
  Lesson: use plain 10k runs, or SPRT only for kill-early of clear losers.
- Picks in the study: C&I 97%, Prism 79%, Vesper 71%, Willow 63%. Prism bag lead >60 at r200 -> 78% win (A side),
  < -60 -> 34%. With p-prismbank at 30%, Prism's Focus hoard is the game's main engine in most comps.
  Thesis B ("carry convoy"): organise the team around the carry: allies farm near Prism (escort), gems routed to
  Prism (pc1 already does some), pact protects it, focus the enemy carry. Needs A (allies that fight together).
- 02:32 p-roster full: 50.6% of 10240 [49.6-51.6], level (no -3 as at 1x fuel). 10k games take ~5 min wall now.
- 02:45 Prism collects 36% of team gems (mean); share >=0.5 -> wins 60-66%, <=0.3 -> 40-44%. Launched B
  (briefs/B-hub.md, variants/macro4-hub): allies value gems Prism can collect at x(1+rho), rho derived from Prism's
  Focus-per-gem spell output converted at the map's camp HP per gem; holds handed to Prism; Prism as collector;
  sole_capture_holder's enemy_seen gate narrowed to enemies that can reach the tiles before payout.
- (clock correction: earlier "02:xx" stamps were guesses; real time at this entry 02:35.)
- A pact (variants/macro4-pact): 50.7% of 10240 dev [49.7-51.7], level. OOF 704 vs 518. Debug 512-game study:
  ~7 joins/game, ~30 rejected; deaths 4.40 vs 4.73, kills 4.51 vs 4.21, economy ~equal. The join rule (lost without
  us, won with us) is rare. Asked for pact2: join whenever won with us, walk <= 3.
- Prism deaths (study, 309): killer is the enemy Prism in 169 (solo duels 91), Vesper 64. Median hp at first hit
  1.00, death within 3 rounds, nearest ally 3 tiles, no ally hits back in 66%. The game is a Prism Focus race and
  duel: the bigger-bag Prism bursts the other (stun 1.5F + ground 1F) and takes its bag. Supports B (hub); next
  candidate idea C: Prism duel doctrine (avoid the enemy Prism's cast range when it out-Focuses us, gang it when ours
  is bigger, focus it in team fights).
- pact2 (join whenever the fight with us is won, walk <= 3): 50.4% of 10240 [49.4-51.3], level. A line closed:
  committed joins don't move the mirror (consistent with macro-3). Kept as a possible component.

## 02:39 hub (B) preview, pre-audit source
- macro4-hub-pre vs ref, dev-a..d: **53.5%**, 10240 games, CI 52.6-54.5 (dev-a 54.0, b 53.5, c 52.7, d 53.9). OOF 669 vs 493.
- First clear gain. Carry economics (allies value gems Prism can collect at x(1+rho); holds handed to Prism; narrower sole-holder enemy gate) moves the needle where fight-commitment didn't.

## 02:44 hub preview on fresh confirm suites
- macro4-hub vs ref, cf-a..d: **54.1%**, 9216 games, CI 53.1-55.2 (cf-a 52.9, b 54.4, c 55.0, d 54.3). Note: this run built a farm.cc the hub agent edited at 02:40 (mid-audit), so it's a slightly later source than the 02:37 dev run. Both positive.
- Mechanism (dev-a, 1000 extracted games): hub deaths 5.33 vs 5.95, kills 5.75 vs 5.13, gems lost to deaths 107 vs 121, gems300 lower (bag held in Prism), tribute gems equal.
- Split by comp (drafts are mirrored): games with Prism 53.6% (735), without 50.6% (265). 26% of games have no Prism: the hub can't help there.

## 02:55 where the hub loses (dev-a, 735 both-Prism games; scr/pbag.py, loss.py, pkill.py, precall.py)
- Our Prism's bag dwarfs theirs (r200 mean 87 vs 54; r500 268 vs 161), but wins only 53.6%.
- Our Prism died carrying 100+ in 162/735 games (22%): we won 10% of those (3% when theirs survived). Neither lost a 100+ bag: 54%.
- 180 such deaths: killer enemy Prism 73, Vesper 63, camps 11. In 130 the enemy Prism carried less than ours. 90 died channelling a recall. Nearest enemy at the decisive moment mostly 3-4 tiles (stun range 4); our Prism usually hurt; no ally within 4 in ~40%.
- Theirs dies the same way 200 times (136 to our Prism). Conclusion: protecting our carry is the lever. Brief C updated: carrier's safety/retreat/recall decisions price death at the bag (burst-vs-HP, no recall inside enemy reach), plus duel strike and carry focus.

## 02:57 hub1 (final audited hub, frozen as bots/variants/macro4-hub1)
- vs ref, dev-a..d + cf-a..d: **53.2%**, 19456 games, CI 52.5-53.9 (dev 53.0, cf 53.5). OOF 1035 vs 903.
- The audit fixes (hand-over loop, unheld-group walk cost, shared hand-over test, posted-wall fallback) are neutral vs the preview (53.5/54.1); hub1 is the base for C (macro4-duel) and hub2 (team-view Q value).

## 03:15 hub2 (team-view collection value; frozen copy bots/variants/macro4-hub2f)
- hub2 = hub1 + Prism's 'Q' collection valued at its team marginal (rho*G + holder gain + freed ally rounds x work rate, the takeover_worth shape) and the ally hand-over gated on the premium beating Prism's rounds at the team's per-champion gem rate. Fixes hub1's ~4x over-valuation of collections (the ally would have scored those gems anyway).
- vs ref, dev+cf: **54.8%**, 19456 games, CI 54.1-55.5 (hub1 53.2 on the same games).
- Fresh suites fr-a..d (seeds 400041-400060, ladder-v2): **55.5%**, 10240 games, CI 54.5-56.4.
- New best. C (duel) to be ported onto hub2 as macro4-duel2.

## 03:32 C duel2 (carrier death priced at its bag, on hub2): LOST
- macro4-duel2 vs ref, dev+cf: **49.1%**, 19456 games, CI 48.4-49.8 (hub2 54.8 on the same games: -5.7).
- cf-a extracted: both-Prism games 47.8% (hub2 ~56), no-Prism 49.7%. Economy fell (captures 64 vs 67, gold 6014 vs 6292, tribute gems 750 vs 804), recalls up; 100+ Prism deaths only modestly lower.
- Reading: `fall_counts` (bag worth >= one life, ~6-9 gems for Prism, ~16 for others) makes carriers count their fall almost always, so they retreat from won fights and stop working. The same lesson as "safety-first" priors: blanket caution costs more economy than the bags it saves.
- Ablations requested (each from hub2): dA heal-price bag risk, dB bag-weighted target value, dC carrier recall gate, dD trade-comparison fall rule + duel_strike.
- Patches of every candidate vs ocean are now saved in research/macro-2026-11-11/patches/.

## 03:50 next levers (read-only planner, fresh eyes)
1. Willow as a field spawn: allies price Willow's heals (3F, cd 8, range 4) into recall/budget/crew decisions; Willow covers the ally with the largest heal gain. Willow restores ~12k of ~100k possible a game; heal trips are 32% of home trips. -> brief E, macro4-willow (from hub2f), implementing.
2. Crew prices following arrival times (plan_crew prices allies at full output from round 0; joiners already price delay).
3. Shop trips priced against the next forced home visit, not the whole remaining game.

## 03:48 duel ablations (each = hub2 + one piece of C), dev-a..d 10240 games each, preview builds (pre-audit)
| variant | piece | win % | CI |
|---|---|---|---|
| hub2 (ref point) | - | 54.8 | 53.8-55.8 |
| dA | bag-at-risk term in the heal-trip price | **50.1** | 49.1-51.1 |
| dB | bag_worth (victim bag at Prism premium) in kill/target values | 54.7 | 53.7-55.6 |
| dC | carrier recall gate (no recall kept inside enemy reach) | 54.7 | 53.7-55.6 |
- The heal-trip term alone costs ~5 points: pricing more home trips for hurt carriers (to protect the bag) loses more work than the bags it saves. dB and dC are level. dD (trade-comparison fall rule + duel_strike) pending.
- Lesson: heal-trip pricing is a steep lever. The direction that loses is "more trips"; the open question is whether fewer/cheaper heals (Willow, brief E) win.
- 03:52 dD (trade-comparison fall rule + duel_strike + lethal_without): **54.8%**, 10240 dev games, CI 53.8-55.7 — level. The C line is closed: every piece is level or (heal credit) a loss. Patches in patches/abl-*.
- Next probe: direction of heal-trip pricing (p-heal50 / p-heal150 scale the heal credit; direction-finding only).

## 03:58 heal-credit direction probes (hub2 + heal_rounds_now x k), dev 10240 each
- x0.5: 53.9 (52.9-54.8); x1.5: 54.0 (53.0-55.0); hub2 54.8. Heal-trip pricing sits at its local optimum; dA's loss came from a large extra credit. Heal line closed.
- Started F (crew prices follow arrival times, from hub2f) with the C agent; E (Willow) in progress.

## 04:22 E willow (allies price Willow heals; Willow covers the max-gain ally; budgets count Willow supply), from hub2f
- vs ref, dev+cf+fr: **54.9%**, 29696 games, CI 54.3-55.4 (hub2 on the same suites ~55.0). Level.
- fr-a split: games with Willow 56.2% (674) vs hub2's 55.2% (643); without 55.2 vs 54.3: noise-level. A pre-audit preview gave 55.0 on dev.
- Level: allies trading trips for field heals neither gained nor lost. Not kept (no measured gain; adds complexity). Patch in patches/willow-on-hub2.diff.
- Started a read-only loss study on hub2 (what separates losses without a Prism bag loss from wins).

## 04:33 F crew (proposer's crew price follows arrival times; finish T from the schedule; damage by phase), from hub2f
- dev 10240: 54.8 (53.9-55.8); cf+fr 19456: **55.1** (54.4-55.8). hub2 on the same: 54.8 / ~55.2. Level; OOF 1360 vs 970 (more than hub2's ratio).
- Second-dealer lag on Elk did fall in smoke games (5.5 -> 4.0 rounds), but the win rate didn't move: clear-pricing accuracy is not the bottleneck.
- Pattern so far: after the hub, four coherent additions (duel, willow, crew, heal pricing) are all level. Waiting on a loss study for the next mechanism.

## 04:50 hub2 loss study (read-only agent; scripts l*.py in macro4-maps/scr)
- No-Prism losses: pure mirror, decided by side (all 90 map pairs split 1-1).
- Clean both-Prism losses (no 100+ Prism bag lost): ~70% of the gap is captures (mid/enemy-side groups carry 63% of it), ~30% gems moved by kills. We are dead 6.7% of the time vs 3.1%; 41% of our early deaths are to the enemy Prism.
- The hub is a bet on the Prism Focus race. Win% by our-minus-their Prism bag at r200: 60+ ahead 72% (287), 20-60 ahead 59% (185), level 46% (226), 20-60 behind 42% (72), 60+ behind 20% (49). When the lead doesn't form, allies are ~50 gems / ~180 gold poorer than ref's (they handed captures to Prism).
- The enemy's decisive move is one big tribute (~377 gems, ~29-turn channel, ~r635), escorted; cancels only delay it (banking team still wins 88-90%).
- Next: macro4-race (rho = 0 while our Prism is believed behind theirs) and macro4-race2 (rho fades when far ahead: burst lead exceeds the enemy Prism's HP); and a micro study of how our Prism loses duels to smaller enemy Prisms.

## 05:00 Prism duel micro study (79 deaths of our 100+ Prism to a smaller-bag enemy Prism; scr/pduel_*.py)
- First cast wins: stun + next ground = 2.5x Focus >= our HP in 55/79 (17 one-shots). A stun removes our reply.
- Classes: stepped into its ready reach 23; kept a (winning, 26-92 turn) tribute channel while it walked up 15; stood in reach without a shot 14; it moved after us and acted first next round 8; walked at a tributing enemy Prism to stun it (walk forbids the exclusive stun) 6; other 13.
- Enemy Prism unseen by ours on the decisive turn in 29/77. Our stun was usually ready.
- Code: Safety::lethal compares one turn's blows (a stun's lost turn isn't priced); step_guard returns early when no enemy is seen (tracked unseen threats ignored); stop_game_ender clears the guard and walks into stun range.
- -> brief G (stun window, all stunners; unseen-threat guard; game-ender approach; tribute cancel): macro4-g1 / g2 / gall from hub2f.

## 04:51 race-aware hub previews (dev 10240 each, pre-audit builds)
- race (rho = 0 while our Prism is believed behind the enemy Prism's bag): 53.9 (52.9-54.9).
- race2 (rho fades to 0 as our burst lead exceeds the enemy Prism's HP): 54.6 (53.6-55.5).
- hub2 54.8. Neither helps: the r200 bag-lead/win correlation is an outcome, not a lever via rho. Giving up the hub when behind loses.
- 05:10 race / race2 after the tracker fixes (the previews had false unseen-tribute resets): race 54.8 (53.8-55.8), race2 54.9 (53.9-55.8), dev 10240 each. Level. Race line closed.

## 05:20 hub half-ablations (from hub2f; dev 10240 each)
| variant | what's on | dev win % | CI |
|---|---|---|---|
| hub2 | allies' premium + Prism Q collection + hand-over | 54.8 | 53.8-55.8 |
| hubA | allies' premium + hand-over, no Q | **50.9** | 49.9-51.8 |
| hubQ | Prism Q collection + hand-over, allies unweighted (hub_m = 1) | **55.8** | 54.8-56.7 |
- hubQ on cf+fr (19456): **55.5** (54.8-56.2); hub2 ~55.2 there. hubQ over all 29696 games ~55.6.
- The hub's whole gain is Prism harvesting allies' clears; allies re-choosing groups for Prism's sake is worth nothing (hubA ~ ocean). "Don't distort the workers; let the carrier harvest."
- hubQ (frozen as macro4-hubQf) is the new base: simpler and at least as good.

## 05:22 rho direction on hubQ (dev 10240 each)
- rho x0.5: 55.0 (54.0-56.0); rho x2 (cap x2): 54.4 (53.5-55.4); hubQ 55.8. The derived premium sits at its optimum.
- Next toggles: q-gate (restore enemy_seen gate for Prism holds), q-nohand (no ally step-off; Prism only joins).

## 05:33 hubQ toggles (dev 10240 each)
- q-gate (ocean's enemy_seen gate restored in sole_capture_holder): **55.8** (54.9-56.8) = hubQ. The relaxed gate is irrelevant; ship ocean's gate (simpler).
- q-nohand (allies never step off for Prism; Q only joins and splits): **51.1** (50.2-52.1). The hand-over IS the engine.
- Mechanism, final: specialisation. Allies clear; Prism walks over and takes the hold; the ally steps off and goes back to work; the whole reward lands in Prism's bag where each gem also adds Focus. Worth ~+5.

## 05:44 G stun window (threat model prices a stun's lost reply turn; unseen-threat guard; game-ender approach; tribute cancel), previews (dev 10240)
- gallq (on hubQf): 55.9 (54.9-56.8) vs hubQ 55.8. g1 (window only, on hub2f): 55.1 vs hub2 54.8. g2 (unseen guard only): 54.7. OOF up (gallq 729 vs hubQ ~540).
- Level. A more accurate threat model didn't move results: the duel deaths it targets are a symptom; fights' outcomes are dominated elsewhere. Not kept.
- Next: is the hand-over's value the gems in Prism (rho) or the ally's freed hold time? q-r0 probe (rho = 0 in Q) and macro4-take (takeover generalised to any champion by the team-view marginal; works without Prism).

## 06:05 H hand (from q-gate: early release of single-tile holds when Prism's fresh hold is due before the ally's payout; Prism commits to Q picks instead of dropping/re-picking while a clear outlasts its walk; freed rounds = ours - max(clear, walk); join-under-way only if affordable)
- dev 10240: **56.6** (55.6-57.5) vs q-gate/hubQ 55.8. cf+fr 19456: **56.0** (55.3-56.7) vs hubQ 55.5. ~56.2 over 29696.
- Smoke measurements (18 Prism games): Q arrivals 39% -> 47%, Q paid Prism 38 -> 63, Prism share of capture gems 0.46 -> 0.49.
- New base, frozen as macro4-handf.

## 06:10 q-r0 probe (q-gate with rho = 0 inside Q; Q and hand-over still active), dev 10240
- **53.4** (52.5-54.4) vs q-gate 55.8 and ocean 50. Freed ally time is worth ~3 points, the Prism-bag premium ~2.5. The freed-time part should generalise to every comp -> macro4-take (pending).

## 06:35 take (takeover generalised to any non-Prism champion by the team-view marginal: holder gain + rounds x (holder rate - taker rate); shared predicate; from q-gate), dev 10240
- **54.2** (53.3-55.2) vs q-gate 55.8: -1.6. Freed time alone doesn't pay for non-Prism holders: a hold's rounds are cheap for whoever holds (it's mostly waiting near its next work anyway), and the takeover walk is the cost. The engine's value needs the Prism premium (q-r0: 53.4 = freed time only *for Prism*, whose own work rate is lowest). Closed.
- 06:40 winning-tribute check (hub2, scr/wintrib.py): in 340 of 360 losses our Prism never started a winning-bag tribute; escorting/guarding the final channel is not a lever.
- 06:58 Q-walk stall check (traced hand2, 22 maps): Prism closes distance on 93% of its Q-movement turns by its own field; the replay-measured 23% "stalls" are mostly fighting the camp it was sent to (67 rounds), other branches taking the turn (46), mode-switch artifacts; the guard never rejected an advancing tile. No defect; nothing to fix.

## 07:03 hand2 (hand + Prism starts a Q pick only where it arrives before the ally's payout; last-turn path kept for its current pick/claim)
- dev 10240: 56.7 (55.8-57.7); cf+fr 19456: **56.0** (55.3-56.7). = hand (56.6 / 56.0). Level; halves abandoned Q walks (76 -> 35) at the cost of some payouts.
- Next: macro4-aoe (camp clear model credits area damage: Prism/Stellar/Ryth ground, HoR landing, Varg splash) from hand2; fuel pass handff on handf.
- 07:15 fuel pass (handff from handf, farm.cc only): bench byte-identical 68/68 at 100M; saves ~0.1% fuel (58/turn). Hub code is 0.74% of the bot's fuel (0.93% on 88k+ turns); the OOF excess vs ref (572 vs 468 per 10k games) is spread over shop/safety/bank/escape — different game states, not hub cost. Not worth porting.

## 07:25 handf on the held-out suites ho-a..d (seeds 400061-400080, never used before)
- **57.0%**, 10240 games, CI 56.1-58.0 (ho-a 57.9, b 56.6, c 56.9, d 56.7). OOF 543 vs 481.
- handf over every suite it played: dev 56.6 (10240), cf+fr 56.0 (19456), ho 57.0 (10240) -> ~56.4 over 39936.
- 07:19 handf on `--mix varied` stress suites (seeds 400081-400090): **54.1%**, 5120 games, CI 52.7-55.4 (var-a 53.0, var-b 55.2). Robust (positive) off the ladder-like mix.
- 07:40 pre-ship review of handf (read-only agent): hubQ ablation scaffolding left in farm.cc (hub_most/p.hub/hub_m constants = 1, dead `if (false && ...)` block, trace-only fields) and two stale comments. Cleaned copy macro4-handfc: bench byte-identical to handf at 100M (16/16 Prism set, 52/52 wide). 36 edge-map release games (18 maps incl. altar-poor, monolith-only, tiny, shared-gems, fuel-stress): no crashes/resigns; handf 20/36 vs ocean-ref's own 18/36 control. hub_rho_most = 2 still binds on gem-dense maps.

## 07:52 aoe (camp clear model credits area damage per group: Prism/Ryth ground, HoR landing, Varg splash; from hand2)
- Measured: the old model under-predicts Prism's camp damage x1.57 (clusters 1.62), Varg 1.73; after the change 1.15-1.23.
- dev 10240: **53.5** (52.5-54.5) vs hand2 56.7: -3.2. OOF 722 vs ~565. A more accurate clear model loses: costlier, and it re-steers Prism toward clearing (Prism share dips), away from the harvesting that wins. Closed.
- Shipping handfc (= handf with the hubQ ablation scaffolding removed; bench-identical at 100M). Final runs on its exact source follow.

## 07:55 shipped
- bots/ocean = macro4-handfc. Final runs of its exact source: cf+fr+ho **56.3%**, 29696 games, CI 55.8-56.9; dev 56.6 (10240). CHANGES 507, EXPERIMENTS entry, macro4.md written.

## 08:13 last refinements on handfc (dev 10240 each) and ladder check
- hq-rate (Q's freed rounds priced at the ally's own rate, not Prism's): 56.7 (55.8-57.7). Level.
- hq-relief (an ally's farm prices its hold as ending at Prism's arrival when Prism will collect): 56.5 (55.6-57.5). Level.
- handfc on ab.py's default suites (the 128 ladder maps + maps/gen, both sides): ladder **57.4%** (256, 51.3-63.3), gen 54.7% (512, 50.4-58.9), total 55.6% (768). Consistent with the ladder-v2 suites.
- 08:20 aoe2 (area model for non-Prism champions only, lazy masks; from handfc): 56.1 (55.1-57.0) dev vs handfc 56.6. Level/slightly worse. Closed.
- 08:22 handfc on h2, a second never-used held-out set (seeds 400091-400110, 4 x 1280 maps): 56.1 (55.1-57.0), 10,240 games; suites 54.5/56.5/56.3/56.9. All fresh suites (cf+fr+ho+h2): 56.3 (55.8-56.8) over 39,936 games. Final number.
- 08:26 launched plast (Prism last-hits enemy gem carriers: a kill takes the victim's carried gems, so rho*G applies; frequency measured first) from handfc.
- 08:30 plast closed at measurement (80 dev-a debug games): our kills take 126 carried gems/game, Prism already lands 69% of them; an ally killed a carrier Prism could also have killed that round 15 times (2.3 gems/game), all on victims yet to act (not certain for Prism), 0 certain. Nothing to redirect. Launched kbag instead: Prism's own kill valuation prices the victim's bag at (1 + rho), consistent with the hub.
- 08:40 kbag (Prism's combat prices a victim's bag at gem_value x G x (1 + rho), 5 sites through one helper; from handfc): dev 10240 **56.3** (55.4-57.3) vs handfc 56.6. Level. Closed. Patch: patches/kbag-on-handfc.diff.
- 08:45 wrap-up: bots/ocean = macro4-handfc stands. Remaining measured leads are exhausted (loss study, duel study, plast measurement); every refinement since hand2 has been level.
