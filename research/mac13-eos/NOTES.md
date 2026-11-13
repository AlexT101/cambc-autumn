# EOS: macro refactor of charybdis (2026-11-13, 02:00-10:00 UTC)

Worktree `/home/ubuntu/wt/mac13-eos`, branch `mac13-eos-20261113`. Reference `bots/variants/chy-ref` (= charybdis
at 0f6fa9879). Every A/B: candidate vs `variants/chy-ref`, `--no-test-draft --fuel 200000`, fast runner, own drafts.
Suites: `maps/suites/mac13/dev` (5,120 maps, 10,240 games), `maps/suites/mac13/hold` (2,560 maps), my own seeds
143200-143999 for more. Analysis suite `maps/suites/mac13/ana` (seeds 143900-143903, 1,024 maps; mirror/debug study only).

## Resume-cold summary (final, 09:00)
- **Best: `bots/variants/stack2` = `bots/charybdis` on this branch (commit 39840da0d).** It is a lead-conditioned risk
  stance plus ATLAS fixes. Each body tracks lead = score + carried: ally bags from comms, plus remembered enemy bags
  grown at our per-body rate. States EVEN/AHEAD/BEHIND/DEEP use hysteresis (+-75 in, +-45 out; DEEP below -150, out
  above -120). BEHIND plays risky: recall and camp_risk x0.7, retreat ratios x1.4, home_power x0.5, mid premium x2.
  DEEP doubles the deviation. AHEAD plays as EVEN. atlas-rest adds ATLAS fixes 3/5 and press.
- stack2 vs chy-ref (2x fuel, own drafts):

  | Suite | Win % | Games | CI |
  |---|---|---|---|
  | dev | 51.9 | 10,240 | 51.0-52.9 |
  | hold | 50.7 | 5,120 | |
  | conf | 50.8 | 10,240 | |
  | conf2 | 51.4 | 10,240 | 50.5-52.4 |
  | conf3 | 51.4 | 10,240 | 50.4-52.4 |
  | conf4 | 51.1 | 10,240 | 50.1-52.1 |
  | conf5 | 51.2 | 10,240 | 50.3-52.2 |
  | **pooled** | **51.25** | **66,560** | **50.9-51.6** |

  The 60% target was not reached.
- Mechanism controls:
  - ctl-ar (AHEAD plays the risky multipliers too): 51.4% over five suites, equal to stack2.
  - ctl-all (risky in every state, EVEN included): 50.5% of 40,960, against stack2's 51.45 on the same suites,
    about 2.7 sigma.
  - ctl-ard (DEEP mirrored to a lead of +150 or more): 51.2-51.3, no gain.

  So the multipliers pay once the game is decided (|lead| >= 75), in either direction, and cost at parity. Safety
  when ahead (stance-safe, 49.1) is what loses.
- Ablation: the risk and positional knobs work only together (full 51.0 on dev; health/risk knobs alone 50.4,
  positional knobs alone 50.1).
- Level or losing on today's charybdis:
  - capture denial: 47.8-48.5
  - pack joins: 50.1-51.3
  - Prism-war doctrine: 48.6-49.5
  - Prism escort: 50.1-50.5
  - quiet camp casts: 49.4-49.7
  - safer when AHEAD: 49.1
  - HOPELESS tier: no gain
  - stacking escort: no gain
  - opening and phase-knob grids: 47.6-50.5
- Currency (handicap probes): ~2 points per 1% of alive time; opening rounds are worth ~3x late ones; the Prism ~2x
  a body.

## Priors (from research/macro-*, 2026-11-11 programme: 8 orchestrators, all level)
- Games end at 1000 gems ~820-845 rounds; Prism war decides (first Prism death loses ~90%); bigger Focus wins duel.
- Prism collects 513-782 gems a game, others 107-141 each; the hoard is worth ~21 points (no-hoard 28.7%).
- Walking ~50% of alive time, ~20% walking back out from spawn/recall; dead 4% (winner) / 12% (loser).
- Every restriction of farm choice lost in proportion to how much it bound (pack -11, convoy -5); soft prices level.
- DELPHI's pack: cohesion wins fights (Prism kills 5.8 vs 3.1, Prism deaths 0.9 vs 1.7, Prism gems 660 vs 535) but
  idle/walk-back allies cost captures (62.6 vs 74.3) -> 38.7%. "Buy cohesion without idle allies."
- First team to score+carried >= 1000 wins 87-90%; conversion median 58 rounds (mean 147), 4.2-4.5 attempts.
- Mid captures differ most between winner and loser; own-side equal; early economy near supply-bound.

## Log
- 02:00 start. Read brief, rules, priors. 02:02 generated ana suite. 02:20 mirror (debug) on ana: 2,048 games in
  3.2 min wall, 50.0% (deterministic mirror). Extracting to `replays/ana-mirror`.
- 02:25 overseer: measure the currency first with handicap probes. Spawning a probe-builder subagent.
- 02:15 mirror study (1,024 games, scripts in `scripts/`):
  - phase.py: P(win | ahead in score+carried) 0.55 @r100, 0.59 @150, 0.64 @200, 0.71 @300, 0.74 @400, 0.78 @500.
    The game is decided r150-500. Winner/loser carried 183/157 @200, 272/217 @300, 363/263 @400. Deaths W/L
    0.44/0.78 @200, 0.81/1.39 @300. First to score+carried 1000 wins 87% (median round 635).
  - supply.py (gem-weighted stock): mid Monoliths ~22% of all gem stock sit idle all game; mid beast groups idle
    8-15%, own-side beasts ~5%; respawning ~30%.
  - deaths.py: first death victim Cassi 40% (409/1024), median r216, victim's team loses 65%; first killer Prism 34%,
    camps 12%. Pair bodies are >half of deaths before r400. Deaths outnumbered (enemies>allies+1 within 8) 31-44%;
    no ally within 8 in ~22%.
  - hometrips.py: 42.5 home arrivals a team-game; 8.5 at 90%+ hp that buy nothing (travel); Prism arrives with 186 gold.
  - macro_stats: walking ~51% (empty->camp 21%, bag->camp 15%, from:spawn+recall 21%), camp 17-18%, hold 5%.
- 02:16 launched a read-only study of early Cassi/Issac deaths (mechanisms).
- 02:35 smoke hc-all10 (every champion skips 10% of its quiet turns, i.e. no enemy visible): **30.9% of 256 ladder
  games**. Champion time is extremely valuable: ~2 points per 1% of quiet time (to confirm on the probe suite
  `maps/suites/mac13/probe`, seeds 143200-143209, 2,560 maps).
- finish.py: at the first score+carried >= 1000, median score 344, Prism bag 584, others 55; that team wins 87%;
  with a 500-700 Prism bag only 77% (rounds to end median 74), bag <300 (score ~970) 93%.
- branches.py: 'still' turns (alive, off spawn, no move, no damage) 15% (W) / 13% (L) of alive time: holds 4.1%,
  farm-still 3% (mostly waiting beside respawning groups: ~73 champion-turns a team-game), altar guard 2.7%/0.8%.

## Currency: handicap probes (02:20-02:50, probe suite 2,560 maps = 5,120 games each, vs chy-ref, 2x fuel)
A skipped turn = the champion does nothing (as if stunned), only on quiet turns (no enemy visible), drawn by a
deterministic hash. Quiet turns are 81% of alive turns r1-200, 76% r201-500, 64% after (quiet.py). Patch:
`patches/hc-handicap.diff`.

| probe | skipped | win % (95% CI) | points | per round of every champion |
|---|---|---|---|---|
| hc-all10 | 10%, everyone, all game | 32.8 (31.5-34.1) | -17.2 | |
| hc-prism10 | 10%, Prism only | 43.7 (42.3-45.1) | -6.3 | |
| hc-ally10 | 10%, all but Prism | 38.3 (37.0-39.7) | -11.7 | |
| hc-open20 | 20%, r1-200 | 34.4 (33.1-35.7) | -15.6 | ~0.49 (32 rounds a body) |
| hc-mid20 | 20%, r201-500 | 35.2 (33.9-36.5) | -14.8 | ~0.32 (46 rounds a body) |
| hc-late20 | 20%, r501+ | 41.6 (40.3-43.0) | -8.4 | ~0.18 |

Reading: one champion-round in the opening is worth ~0.1 points (0.065 mid, 0.035 late). The Prism's time is worth
about twice an average body's (6.3 for one body vs 11.7 for ~4). A death at r150 (60 rounds dead + ~17 walking back)
costs ~77 champion-rounds, ~7 points by this rate before counting its bag and kill gold; consistent with the first
death's team losing 65%. So: (1) the opening's tempo is the most valuable time of the game; (2) early deaths and
early wasted walking are where the points are; (3) anything that buys late safety with early time is a bad trade.
- Probe builder: 8.2% of alive turns were actually skipped by hc-all10 (82% eligible) -> ~2.1 points per 1% of
  alive time.

## Pair-death study (02:30, read-only subagent, 529 games with a Cassi/Issac death before r400; scripts in
`replays/tmp/pairdeath/`, scratch)
- That death was the game's first in 329; its team lost 62%. Median r216. Killers: Prism 196, enemy pair 125, camps 69.
- Killer seen by the body within 3 rounds in 88%. The dead body was our closest to an enemy in 82%.
- Farm group of the dead body: middle 70%, enemy side 15%, own 15% (pair time: 45/7/47) -> risk ratio 1.5 middle,
  2.2 enemy side, 0.31 own side. Cassi-Issac distance does not separate deaths (together and alone die alike).
- Mechanisms: B chased home by a melee 27% (retreat toward spawn a median 24 tiles away, melee keeps contact, partner
  hits an enemy in only 28 of 145); D Prism attrition 22%; F supported fight lost 18%; A camp kill 13% (left camps at
  ~47% hp with the 0.109 safe recall line, died walking out); C Prism burst from >=80% hp 11% (team lost 84%);
  E lone body picked off 9%. The Prism causes 33%. 57% of deaths had a body within 5 of the enemy Prism in the 20
  rounds before (pair time within 5 of it: 2.9%). Of Prism first hits, 58/108 our body made the last step in (33 of
  those Prisms unseen: fog or bush); 49 the Prism stepped in.
- Code: approach by farm (F) 51%, `guard_work` fences; `retreat()` always heads for `to_ally_spawn()`; partner
  never joins.

## Opening / pair probes (02:39-03:10, probe suite, 5,120 games each vs chy-ref)
| probe | change | win % | read |
|---|---|---|---|
| op-noplan | farm ignores the draft's opening plan | 49.1 | the plan is worth ~+1 |
| op-noQ | no Prism ride-home capture recall r<=200 | 49.7 | level |
| op-noshop | no pure shop trips r<=200 | 50.4 | level |
| op-norf | no recall-as-travel to farm r<=200 | 48.9 | travel recalls worth ~+1 early |
| pair-home | Cassi/Issac weigh enemy ground 3x as hard (home_ground^3) | 51.2 | leans positive (+1.2 +-1.4) |
The opening's mechanisms are each near their local optimum; the pair's risk allocation is the one lean.
- 03:15 pair-home on dev: **49.9% of 10,240 (48.9-50.9)**: level; the probe-suite +1.2 was noise. A 10k A/B takes ~1 min wall now.
- 03:30 **pairsafe** (pair as a unit: enemy-Prism burst zone in work guard + farm, retreat toward a supporting ally,
  partner answers via sight/distress post, solo camp-exit price; diff `patches/pairsafe.diff`): smoke counters per
  game ~87 zone-turns, ~36 partner-answer turns, ~7 retargeted retreats. **dev 48.4% of 10,240 (47.5-49.4): loses.**
  Extracting its kept replays to see whether pair deaths fell and what it cost.
- 03:28 launched `deny` (enemy holds and clears as farm candidates worth up to 2x: deny + take; contest from a free
  tile; safety unchanged). Evidence: at an enemy hold's start one of ours is within 6 tiles in 6.3 captures a
  team-game (136 gems), within 9 in 12.2 (230 gems); we contest ~0.5 a game (scripts/denial.py).
- 03:40 pairsafe replays (376 kept games, scripts/abcmp.py): pair deaths 2.0 vs ref 1.8, all deaths 7.7 vs 6.8,
  kills 4.9 vs 5.6, capture gems -44, gold -252. **The design did not reduce pair deaths at all**; it only cost farm
  and fights (answers drag both bodies into fights, retreats drag chasers onto allies). Dropped; the premise that
  pair deaths are cheaply avoidable through positioning is not supported.
- Mirror: winners and losers have identical time use in r1-150 and r151-350 (timeuse_wl.py); the games part on
  deaths only. So the mirror is decided by fights, while each farm mechanism sits at its own optimum.
- 03:42 launched phase-knob probes (6 tuned constants x {opening r1-200, mid r201-500} x {up, down}, 24 variants +
  a no-op control): do the tuned optima differ by phase? A whole-phase parametrisation is the overseer's
  "plan a phase differently" in its cheapest form.
- denial2.py: of the 6.3 enemy holds a team-game with one of ours within 6 at the start, our body was farming in 2.8,
  retreating in 2.1, already contesting in 0.5; 89% of those groups have 2+ tiles (contestable). Realistic deny
  pool ~2.5 a game, ~20 gems + ~70 gold each.
- windows.py (r>=100, team-rounds): a team has more alive bodies 20% of the time, fewer 20%, parity 59%. Ahead, its
  bodies stand own/mid/enemy 44/53/3%; behind, 64/35/1% = exactly as at parity: the bot does not pull back when
  outnumbered, nor push into the enemy half when ahead (enemy-side presence ~1-3% always).
- stunprism.py: our Cassi starts 1.3 turns a game with the visible enemy Prism within 4 and its stun ready; it
  stuns the Prism in 29% of them (casts that slot at all 33%).
- 03:57 deny-s0 (pre-audit snapshot of deny) on dev: **47.8% of 10,240 (46.9-48.8)**, OOF 733 vs 622: loses. Asked the implementer to diagnose with its counters and tighten.
- 04:05 ph-base control: exactly 50.0% with identical out-of-fuel counts (no-op confirmed). 24 phase-knob probes on the
  probe suite at ~1,500 games each: all 47.6-51.9, i.e. flat; the tuned constants are near their optima in each phase
  too (final numbers below when complete).
- 04:12 Phase-knob probes are final (probe suite, 5,120 games each; CI ±1.4). Names are ph-<knob>-<phase>-<dir>:
  knob 1 recall_health_fraction, 2 camp_risk, 3 home_power, 4 mid_exposure premium, 5 retreat ratios, 6 gold_price_scale;
  phase o is r1-200, m is r201-500; dir u is ×1.4 (knob 3 ×2, knob 4 premium ×2), d is ×0.7 (knob 3 ×0.5, knob 4 premium 0).
  1-m-d 50.5 | 1-m-u 49.6 | 1-o-d 50.1 | 1-o-u 50.2 | 2-m-d 50.1 | 2-m-u 50.1 | 2-o-d 50.0 | 2-o-u 50.0
  3-m-d 50.4 | 3-m-u 50.5 | 3-o-d 50.0 | 3-o-u 50.1 | 4-m-d **47.6** | 4-m-u 49.2 | 4-o-d 49.7 | 4-o-u 49.7
  5-m-d 50.1 | 5-m-u 49.7 | 5-o-d 49.5 | 5-o-u 50.0 | 6-m-d 50.0 | 6-m-u 49.5 | 6-o-d 49.7 | 6-o-u 49.4
  Verdict: no lever. The only clear effect is that dropping the mid-exposure premium in r201-500 costs 2.4 points, so the
  mid-exposure term matters. Partial reads at ~1,500 games (3-m-u 51.9, 6-o-u 47.6) all regressed to 50. The 2-* cells
  sit at 50.0 suspiciously evenly; I asked the builder whether camp_risk is routed.
  Conclusion: macro constants sit at their optima in every phase. A gain must come from new behaviour, not reweighting.
- 04:15 prismduel.py/prismduel3.py (mirror, 879 two-Prism games): 4.6 Prism encounters (within 6) a game. Before r600:
  2,435 encounters; the smaller-Focus Prism dies in 16%, the bigger in 5%. By Focus ratio (bigger/smaller), the smaller
  dies 8% below 1.15x, 11% at 1.15-1.4x, 16% at 1.4-2x, 19% at 2-3x and 35% at 3x+. The first Prism death (median r429)
  loses 90%. Its killer is the enemy Prism 66% of the time, with the bigger Focus 71% of those times (median 1.23x). It takes
  ~10 rounds from >=90% hp to death, and the victim saw the killer in the prior 15 rounds 69% of the time. Late deaths of a
  depleted Prism (median r766, branch E stop_ender) are the endgame, not a lever. BOREAS tried Prism-burst lethality:
  level. The opportunity is ~0.15 deaths a team-game, worth ~2-3 points at best.
- 04:20 Reading the prior programme summary (research/macro-orchestrators-2026-11-11.md): ATLAS's fixes 3 and 5 and its
  press are worth ~+1.3 at 2x fuel and were left out of 517 for 100k fuel cost. Our target is 2x, so they're a real
  component. Spawned the `atlas-rest` port.
- 04:25 joins.py (mirror, 23 engagements a game to r900; an engagement starts at a cross-team champion hit with none
  within 10 tiles in the prior 6 rounds). Of the other champions within 8 of the target, in the next 3 rounds: attacker side
  1.43 a fight, 15% hit a champion, 15% a camp, 70% neither; defender side 1.82, 10% / 18% / 72%. Willow joins 3-4%.
  Outcome by (attacker joins, defender joins): (0,0) target dies 11%; (1,0) 30% and defender-side deaths 0.49;
  (2,0) 62%, 1.0; (3,0) 76%. A defender join (0,1) raises attacker-side deaths from 0.15 to 0.40. Confounded (the bot
  joins when it pays), but the size matches the Fish study: "the whole pack turns on the target". Bystanders doing
  neither are mostly in farm (F 41-45%), retreat (R 16-18%) or Willow-follow (h 8%). Defender bystanders within 1-3
  doing nothing are common (13.9k), likely the target's pair partner and Willow.
- 04:27 Overseer check-in: the phase grid ruled out the cheap form; pursue one large behavioural design (the pack turns on
  the target) and weigh its farm-time cost. Spawned `join` (diagnose first why bystanders don't join: prey filter,
  chase_trade, escapes, guard or an earlier branch; then build). Its screens go on probe2 (seeds 143400-409). `atlas-rest`
  port running; deny wrapping up.
- 04:28 deny final report. The 2.2-point loss in deny-s0 came from waits beside live groups the enemy was clearing (1.5
  a game, none won, 66% ended in a retreat) and from hits in passing gated off on ~7 turns a game. Deaths were not the
  cause. Contests are rare in both bots (0.5-0.8 started a game, 0.14-0.29 won); the safety model calls most denial
  stands lost. chy-ref's forced contest_capture walks: 3.2 a game, reach the tile 0.06, retreat within 10 79%. The final
  `deny` removes the forced contest branch, makes denial a farm candidate with a strict stand check, and has no waits.
  0.06-0.08 picks a game, so it is close to inert: effectively "chy-ref without the forced contest". Debug 2,048 games:
  49.7%. Running dev.
- 04:35 **deny (final) on dev: 48.5% of 10,240 (47.6-49.5)**, OOF 597 vs 591: loses 1.5. The change is almost inert as a
  denial, so the loss comes from removing chy-ref's forced contest_capture branch, or from the hits held back during the
  denial gate. The forced contest walks (3.2 a game, 79% end in a retreat) look wasteful but pay; they probably push enemy
  holders off. Dropped.
- 04:38 joins.py positional table: attacker-side bystanders within 4 of the target at the first hit, with no defenders
  within 4. With 0 the target dies 13%; with 1, 31%; with 2, 52%; with 3, 81%. Defenders within 4 cut it: for 0
  attackers and 3 defenders the target dies 8% and attacker-side deaths are 0.32. 82% of engagements start with 0
  attacker bystanders within 4: fights start as one-on-one. Sent join a time-cost calibration: ~37 bystanders a
  team-game, so joining everything for ~5 rounds is ~4-5% of time (~-9 points). Joining must be selective.
- 04:50 join-s1 (the implementer's first version): probe2 51.3% of 5,120 (50.0-52.7); **dev 50.2% of 10,240
  (49.2-51.1)**, OOF 707 vs 582. Level. Told the implementer.
- 04:55 **atlas-rest (ATLAS fixes 3 and 5, the merge fixes, the press and the fuel floors, ported onto 525) on dev: 50.5% of
  10,240 (49.5-51.4)**, OOF 831 vs 570. That is +0.5, inside noise; on 515 the same parts were worth ~+1.3. Kept as a
  possible stack component only.
- windows2.py: 2+ bodies ahead is 12% of team-rounds (~1.9 windows a team-game, ~47 rounds each). Even then, enemy-half
  captures are only 3.8 gems per 100 team-rounds (mid 63). A raid stance would have little to take: not a lever.
- 05:00 join diagnosis (256 debug ladder games; each non-joining bystander on its first turn after the first hit):

  | Reason | Attacker side | Defender side |
  |---|---|---|
  | enemy not in sight at all | 37% | 58% |
  | healthy enemy off our ground, out of range (G clause) | 22% | 18% |
  | chase_trade lost | 25% | 16% |
  | pack zone covers the target | 5% | 2% |
  | near the enemy spawn | 3% | 2% |
  | C&I would fall | 1% | 0.4% |
  | fight won and catchable (chased, no hit within 3 rounds) | 7% | 3% |

  Only 16-24% of the unseen are in bushes. Most stand 5-10+ tiles away a turn after the hit: **poke-and-leave fights**.
  The lost trades are mostly Willow and C&I, who read their side as dead in 1-2 enemy turns. join-s1 flipped ~35 of ~900
  lost trades. The fight model is calibrated at its boundary. Branch takeover after prey is <10%. So the mirror's
  "engagements" are mostly incidental pokes (the first hitter's branch is F or R in most lone-attacker cases), not
  committed fights. Joining can't change a fight that is over in a round.
- 05:05 Willow heals ~53 times a game (13.6k hp); its heal is used, so no lever there. Kills by killer: the Prism makes
  7.1k of ~13.5k kills in 1,024 games (224k gems). Non-Prism kills that the Prism assisted carry only ~18 gems a
  team-game, so routing last hits to the Prism is no lever.
- 05:05 Spawned `pwar` (Prism-war doctrine). It diagnoses first why the smaller-Focus Prism stays in the bigger one's
  reach and why the bigger fails to convert. Then: (a) the smaller keeps out of the enemy Prism's remembered reach while
  the model says it loses the duel; (b) the bigger presses with support. Screens on the probe suite; join uses probe2.
- 05:12 **join final: level everywhere.** Screens on probe2 (5,120 games each): s1 51.3, s2 (no ground clause) 50.6,
  s3 (s1 + audit fixes) 50.9; dev s1 50.2. The join rate barely moved (attacker side 17.3% vs 17.1%): the joiners flipped
  ~35 of ~900 lost trades, and the contact lift fired ~100 times in 256 games. Farm cost ~13 turns a game, which is
  negligible. Conclusion: in the mirror, fights are pokes that are over by the next turn, and the remaining join
  decisions sit at the fight model's calibrated boundary. Fish's edge comes from a travelling pack (a team shape), not
  from a join filter. Patches: join.diff, join-g.diff.
- 05:20 leadwin.py, P(win | score+carried lead) in the mirror. From r250, +75..150 wins 73-85%, +150 or more wins 81-98%,
  and an even lead (±25) wins 49-53% at every round. Spawned `stance`: a lead-conditioned risk posture, AHEAD plays
  safer and BEHIND riskier, on ph-base's knob routing (variants stance-safe, stance-risky, stance). The phase grid showed
  the fixed posture is right on average; this tests whether it is right conditional on the lead. Screens on probe2.
- 05:30 castmove.py: in quiet rounds (no enemy seen) the Prism hits a camp with its basic, stands still, has an
  ability ready and doesn't cast it about 11 times a Prism-game (CC ~6, AoE ~5). At Focus ~400 that is ~4-5k camp damage
  a game. The likely gates in camp_cast are engagement_near (remembered enemies), the cast_cost floor (an overkill on a
  nearly dead camp) and members out of reach. Queued: a "quiet camp casts" diagnosis.
- 05:40 pwar-s1 screen on probe: 48.6% of 5,120 (47.3-50.0); the implementer is diagnosing.
- 05:48 castmove2.py: of the Prism's quiet unused ready casts while hitting a camp (~22 a game, both Prisms), the group's hp exceeds the cast's damage in 53%, and an enemy was seen in the prior 8 rounds in 13%. The rest (not overkill, quiet) are ~10 a game, 98% in the farm branch F. Farm skips casts for a reason not yet known (an exclusive cast vs a planned walk? engagement_near on beliefs?). Worth ~2.5k camp damage a Prism-game, maybe +0.5-1.
- 06:00 **stance screens (probe2, 5,120 games each): stance 50.1, stance-safe 49.1, stance-risky 50.6**: level.
  Neither playing safer when ahead nor riskier when behind moves the result. Risk posture is not a lever, by phase or by lead.
- 06:03 stance report. Lead estimate: scores plus comms-posted ally bags plus remembered enemy bags grown at
  our per-body rate; bias 4-11 gems through r500. States EVEN/AHEAD/BEHIND 46/29/25% with hysteresis (±75 in, ±45 out),
  ~2.9 changes a champion-game; teammates disagree 22% of rounds. Patches stance*.diff.
- 06:12 Dev reads of the small positives: **join-s3 50.1% of 10,240 (49.1-51.1)**; **stance-risky 50.9% of
  10,240 (49.9-51.8)**, OOF 700 vs 629. Pooled with probe2, stance-risky is ~50.8% of 15,360, a lean of under +1. Also
  atlas-rest 50.5 (dev). None is large; at most they are stack components.
- 06:16 pwar-s2 screen (probe): 49.5% of 5,120. Level.
- 06:22 **pwar final: level** (probe s1 48.6, s2 49.5). Diagnosis over 512 debug games, encounters before r600
  at a Focus ratio of 1.25x or more:
  - The smaller Prism walks into reach while farming (F); the team model calls it no fight or not lost, because enemy
    turns aim at our weakest member. Then its retreat fails, casting instead of walking half the time.
  - The bigger Prism wins a 1v1 duel on ~25 champion-turns a game, but its team chase fight is lost on most of those,
    because other enemies are around.
  - Avoiding a Prism that beats us 1v1 (s1) pulled our Prism out of fights the team was winning: kills of the enemy
    Prism fell 0.74 -> 0.57.
  - **Support decides encounters**: our Prism dies 25% / 16% / 9% with 0 / 2 / 4+ allies within 8; the enemy's 7% / 11% / 19%.

  Next: an encounter-bounded **escort** (allies converge on our Prism only while the Prism pair is within encounter
  distance), built by the same implementer. Also: my castmove2 "unused casts" were mostly a counting artifact (one cast
  per turn across both slots); the qcast implementer found turns with no cast at all at 0.02 a Prism-game.
- 06:25 escortpool.py: Prism encounters (within 6, r<600) take ~44 rounds a two-Prism game. Our Prism already has 2.5 allies within 8 per encounter round, and 0.57 more at 9-14. Escorting those costs ~25 champion-rounds a team-game (~0.6% of time, ~-1.2 points) for ~+0.5 allies within 8.
- 06:52 The box is heavily loaded (load ~237): a 5k screen now takes ~30 min. stance-risky (best so far) started on hold as a fallback finalist.
- 07:01 **stance-risky on hold: 50.9% of 5,120 (49.5-52.3)**, OOF 288 vs 267. Pooled over probe2, dev and hold:
  50.8% of 20,480 (~50.1-51.5). That is a small real gain from playing riskier when 75+ gems behind: recall line x0.7,
  camp_risk x0.7, retreat ratios x1.4, home_power x0.5, mid premium x2. The leading candidate so far; next is stacking
  it with atlas-rest.
- 07:08 stance-risky started on conf (my seeds 143300-319, 10,240 games).
- 07:11 escort-s1 screen (probe): 50.1% of 5,120. Level.
- 07:12 stance-risky2 (a DEEP tier below -150 at twice the deviation) and stack1 (stance-risky + atlas-rest) are built, audited clean and smoked (48.8 / 52.7 of 256). Both started on dev.
- 07:24 qcast screens (probe2): s1 49.4, s2 49.7 of 5,120. Level.
- 07:27 qcast report. The quiet unused casts were a counting artifact: one cast a turn across both slots,
  and quiet standing turns with no cast are 0.02 a Prism-game. The real gate is engagement_near holds with an enemy
  visible 5-7 tiles away: the held slot hits an enemy within its cooldown only ~6% of the time. Releasing a cast unless an
  enemy is within that slot's reach gives ~3 more Prism camp casts a game, and reads level (probe2 49.4; 49.7 with stun
  slots still held). escort-s2 (probe): 50.5% of 5,120.
- 07:27 **escort final: level** (probe s1 50.1, s2 50.5). It moved few bodies: 6-7 escort steps a side a
  game, 0.2-0.4% of farm steps. Allies within 8 of our Prism in encounters went only 2.42 -> 2.49. Our Prism's deaths fell
  (0.95 -> 0.71 a two-Prism game), but the enemy Prism also died less (0.955 -> 0.85): fewer Prism kills on both sides, so
  the win rate stayed level. It needed comms room: the encounter record fits only when the ally-position record is
  dropped on healer-less teams. Patch escort.diff.
- 07:31 **stance-risky on conf: 50.2% of 10,240 (49.3-51.2)**, OOF 731 vs 715. Pooled over probe2, dev, hold
  and conf: **50.6% of 30,720 (~50.1-51.2)**. Resumed the stance implementer for rc1/rc2: comeback's cooked() (risky
  chase acceptance plus mirror_pull denial) also on while the stance is BEHIND (rc1) or DEEP (rc2).
- 07:34 **stack1 (stance-risky + atlas-rest) on dev: 51.3% of 10,240 (50.3-52.3)**, OOF 922 vs 637.
  **stance-risky2 on dev: 51.0% of 10,240 (50.1-52.0)**, OOF 666 vs 651. Started stack1 on hold and conf, and
  stance-risky2 on hold.
- 07:36 rc1/rc2 built, audited clean and smoked (47.7 / 49.2 of 256). The stance is per body: teammates can disagree on it. rc2 started on dev.
- 07:42 stack2 (stance-risky2 + atlas-rest) built, audited and smoked (53.5% of 256). Started on dev.
- 07:45 **stack1 on hold: 50.7% of 5,120 (49.4-52.1)**, OOF 430 vs 330. **stance-risky2 on hold: 51.8% of 5,120
  (50.4-53.2)**, OOF 310 vs 285. stance-risky2 over dev and hold: 51.3% of 15,360. Started stance-risky2 on conf.
- 07:48 **stack1 on conf: 51.3% of 10,240 (50.3-52.2)**, OOF 984 vs 651. stack1 over dev, hold and conf: 51.2% of 25,600.
- 07:50 **rc2 on dev: 51.1% of 10,240 (50.1-52.0)**, OOF 732 vs 667: the same as stance-risky2 (51.0). Comeback mode in DEEP adds nothing measurable.
- 07:53 **stack2 (stance-risky2 + atlas-rest) on dev: 51.9% of 10,240 (51.0-52.9)**, OOF 917 vs 652: the best dev
  read. Started stack2 on hold and conf. stance-risky3 (a HOPELESS tier at -300 or below, using BEHIND's multipliers cubed;
  recall capped at the safe line) is built, audited and smoked (48.8 of 256). Started on dev.
- 07:57 **stance-risky2 on conf: 50.7% of 10,240 (49.7-51.6)**. stance-risky2 over dev, hold and conf: 51.1% of 25,600.
- 08:02 **stack2 on hold: 50.7% of 5,120 (49.4-52.1)**, OOF 424 vs 311. Asked the escort implementer for stack3 = stack2 + escort-s2.
- 08:08 **stack2 on conf: 50.8% of 10,240 (49.9-51.8)**, OOF 948 vs 676. **stance-risky3 on dev: 51.0% of 10,240
  (50.0-52.0)**: the HOPELESS tier adds nothing over risky2's 51.0.

  Finalists over dev + hold + conf (25,600 games each):

  | Variant | Win % |
  |---|---|
  | stack2 | 51.2 |
  | stack1 | 51.2 |
  | stance-risky2 | 51.1 |
  | stance-risky (+probe2) | 50.6 of 30,720 |

  The DEEP tier and atlas-rest each add a few tenths, all inside noise of each other.
- 08:10 stack3 (stack2 + escort-s2) smoke: 53.1% of 256, clean. Started on dev.
- 08:20 **stack3 on dev: 51.5% of 10,240 (50.5-52.4)**, OOF 948 vs 699; **on hold: 50.4% of 5,120 (49.1-51.8)**. Conf running.
- 08:21 **stack3 on conf: 51.3% of 10,240 (50.3-52.2)**. stack3 over the three suites: 51.2% of 25,600, identical to stack2. The escort adds comms complexity for nothing measurable, so the ship candidate is **stack2**. Generating conf2 (seeds 143500-519) for one more independent read of stack2.
- 08:26 Copied stack2's src into bots/charybdis (it builds), and started stack2 on conf2 (seeds 143500-519, 5,120 maps).
- 08:33 **stack2 on conf2: 51.4% of 10,240 (50.5-52.4)**, OOF 939 vs 598. stack2 over dev, hold, conf and conf2: **51.3% of 35,840 (~50.8-51.8)**. Asked the stance implementer for knob ablations of stance-risky2: abl-pos (home_power and mid premium only) and abl-hp (recall, camp_risk and retreat only).
- 08:44 abl-hp (smoke 47.7 of 256, clean) and abl-pos (a params-only diff from stance-risky2, checked) started on dev.
- 08:50 **Ablation of stance-risky2 (dev, 10,240 each):**

  | Variant | Win % |
  |---|---|
  | full | 51.0 |
  | abl-hp (recall, camp_risk, retreat only) | 50.4 |
  | abl-pos (home_power, mid premium only) | 50.1 |

  Neither half carries the gain alone. The package works as a whole: when behind, stay out longer at lower health
  *and* farm forward. Generating conf3 (seeds 143600-619) for a final tightening read of stack2.
- 08:54 **stack2 on conf3: 51.4% of 10,240 (50.4-52.4)**. stack2 over dev, hold, conf, conf2 and conf3: **51.3% of 46,080 (~50.8-51.8)**. Asked for a control, ctl-ar (stack2 with AHEAD also playing the risky multipliers), to test the variance mechanism.
- 08:58 ctl-ar on dev (launched 08:58). Rewrote the resume-cold summary to the final state.
- 09:04 **ctl-ar on dev: 52.0% of 10,240 (51.0-53.0)**, OOF 945 vs 670, the same as stack2 (51.9). Risky play when AHEAD does not lose, so the gain is not variance-seeking: the multipliers are better play in decided games either way, and the lead conditioning may not be needed. Running ctl-ar on conf2 and asking for ctl-all (risky in every state).
- 09:08 **ctl-ar on conf2: 51.6% of 10,240 (50.6-52.5)**, OOF 909 vs 589 (stack2 there: 51.4). ctl-all (risky in EVEN too) built by the stance agent: one-line routing change. Running ctl-all on dev and ctl-ar on conf3.
- 09:12 **ctl-ar on conf3: 50.8% of 10,240 (49.8-51.7)**. Over dev, conf2 and conf3, ctl-ar averages 51.5% against stack2's 51.6% on the same 30,720 games: equal. Whether AHEAD plays as EVEN or as BEHIND makes no difference. Plain safety is what costs (stance-safe, 49.1).
- 09:13 **ctl-all on dev: 50.5% of 10,240 (49.5-51.5)**, OOF 941 vs 637, against 51.9 (stack2) and 52.0 (ctl-ar). Risky play at parity costs about 1.5 points. So what the multipliers need is a decided lead, in either direction, not a deficit: a mechanism of |lead|. Confirming ctl-all on conf2.
- 09:17 **ctl-all on conf2: 50.7% of 10,240 (49.8-51.7)**, OOF 1019 vs 640. ctl-all pooled 50.6% of 20,480, against 51.7 for stack2/ctl-ar on the same suites. Confirmed: the risky multipliers pay only once a game is decided either way (|lead| >= 75), and cost at parity. Asked for ctl-ard (DEEP mirrored to a lead of +150 or more) as a last control.
- 09:20 **ctl-ar on hold: 49.8% of 5,120 (48.4-51.2)**. ctl-ar over dev, conf2, conf3 and hold: 51.2% of 35,840, against stack2's 51.4% on the same games. Level; stack2 stays the final.
- 09:24 **ctl-ard (DEEP mirrored to a lead of +150 or more): dev 51.2% (50.2-52.1), conf2 51.3% (50.3-52.2)**, against ctl-ar's 52.0/51.6 and stack2's 51.9/51.4. Deepening the risk when far ahead adds nothing. Generating conf4 (seeds 143700-719) for a last stack2 read.
- 09:28 **conf4 (seeds 143700-719, 5,120 maps): stack2 51.1% of 10,240 (50.1-52.1), OOF 924 vs 625; ctl-ar 51.8% (50.8-52.8).** stack2 over dev, hold, conf, conf2, conf3 and conf4: **51.3% of 56,320 (~50.8-51.7)**. On the five suites both played, ctl-ar and stack2 each average 51.4% of 46,080. Running ctl-all on conf3 and conf4 to firm up the cost of risky play at parity.
- 09:30 **ctl-all on conf3: 50.4% (49.5-51.4); on conf4: 50.3% (49.3-51.3).** ctl-all is 50.5% of 40,960 against stack2's 51.45% on the same four suites, a gap of about 2.7 sigma. Summary updated.
- 09:30 Deleted the mirror-ana batch and the ana-mirror/ana-pairsafe extracts.
- 09:37 **stack2 on conf5 (seeds 143800-819): 51.2% of 10,240 (50.3-52.2)**, OOF 892 vs 613. Pooled over 7 suites: **51.25% of 66,560 (50.9-51.6)**.
