# TETHYS: macro refactor of charybdis (2026-11-13)

## Status (final, 19:25 UTC: programme ended early by the overseer)
- Lines A-H all level or losing against chy-ref. Closest: `mx-midx17` (mid_exposure 1.70): pooled held-out 50.2 of
  20,400 at 2x (hold 50.4, conf1 49.9); at 100k on `fin` 49.3 (48.3-50.2) of 10,200, OOF 71,933 / 72,893 (level).
- `bots/charybdis` left equal to chy-ref (529); midx17's one line is in patches/mx-midx17.diff.
- Nothing running: subagents stopped, mx-tethys-* sessions killed, studied batches deleted.

## Setup
- A/B: `tools/ab.py variants/CAND variants/chy-ref --no-test-draft --fuel 200000 --suites SUITE --name mx-tethys-TAG`, fast runner native.
- Suites: `maps/suites/mx/dev` (5,100 maps = 10,200 games), `maps/suites/mx/hold` (5,100), `maps/suites/mx/study`
  (seeds 61401000-61401007, 2,720 maps, ladder-v4; analysis and smokes only, never decisions).
- `maps/suites/mx/train` (61401100-61401114, 5,100): implementers iterate here. `maps/suites/mx/conf1` (61402000-61402014,
  5,100): my fresh confirmation suite. `maps/suites/mx/fin` (61403000-61403014, 5,100): reserved for the final 100k read.

## Log
- 14:21 Read BRIEF, rules, AGENTS, the 11-11 and 11-13 programme summaries, CASTOR's notes (the one large gain:
  Prism gem premium priced consistently, Willow medic, Prism shop/farm-recall timing; now in charybdis 527+).
  Priors: farm time binds; restricting where allies farm lost; non-Prism games (~22%) stayed level under CASTOR.
- 14:25 Debug mirror `mx-tethys-mirror` (chy-mirror = chy-ref copy, study suite, 5,440 games, 2.9 min wall): 50.0%.
  Solo `mx-tethys-solo0` (vs idle, study, debug): 1000 tributed at r628 on average; collected @150/300/600
  215/510/925, tributed 38/169/735.
- 14:35 Mirror metrics (scripts/cohesion.py, carry.py, gold.py, kills.py; 400-800 games, winner W vs loser L):
  - Charybdis already packs about as Fish did in Nov: nearest ally 4.8 tiles r<=300 (Fish 4.0-4.9), largest
    cluster 75% (Fish 77-83%), early Elk crews 3.2, Golem 3.9. Plain packing is not the missing piece.
  - Deaths decide: L 10.5 a game vs W 3.3; gems lost dying 269 vs 43. Cassi+Issac pair deaths 2.63 (L) / 1.05 (W)
    a game, half of all deaths, each two bodies. Prism deaths 1.61 / 0.09. L dies outnumbered (more enemies
    within 8 than allies + 1) 4.3 a game vs W 0.7.
  - Killers: the enemy Prism kills ~4.5 of L's bodies a game (its Prism 1.33, Cassi 1.25, Issac 0.5, Ryth, Willow,
    Vesper ~0.45 each); Vesper is the second killer. Camps kill ~0.2.
  - Economy: W's Prism captures 595 gems a game and scores 620 in ~1 completed tribute (8 starts); other bodies
    carry 30-50 gem bags, 3-5 tributes each. Gold: Prism 2,800 (W) / 1,870 (L), Vesper 3,000 / 2,400; Cassi and
    Issac ~200-300 a game, Willow ~50: the fragile bodies stay near base stats all game.
  - Early economy is close: tributed @150 24/25, @300 112/95, capture gems r<=300 402/352 (+14%); the gap opens
    r300-600 (523 vs 271 tributed @600), with the deaths.
- 14:45 Turn budget (mirror, `logs/turn_budget_mirror.md`; solo, `logs/turn_budget_solo.md`) and solo walk audit
  (`logs/walk_audit_solo.md`):
  - Walking is ~50% of alive time for every body, mirror and solo alike; camp hits 18% (mirror) / 25% (solo).
  - Solo: recall + walk-out cycles are ~31% of champion-rounds (7.9 recalls a champion a game, 5.4 of them at 80%+
    health: transport and shopping, about as fast as walking). 69% of walks to a camp head to a group respawning or
    cleared at the start; ~100 idle rounds a game beside respawning groups. Supply used: own 62%, middle 42%, enemy
    16% even unopposed. Wolves take ~50% of hitting turns for ~27% of gems (1.4-1.5 hitting turns a gem; golems,
    solo elks, gem clusters 0.2-0.4).
  - Mirror: predictors: more middle captures wins 78%; tributed+carried lead at r200 of 50-149 wins 73%, 150+ 94%;
    fewer gems lost at death 88%. Deaths: L 8.0 to champions a game, W 2.4; at 3+ allies vs 3+ enemies within 8,
    L 2.0 a game vs W 0.6 (big team fights). Deaths are rare before r300 (L 1.24, W 0.60).
  - Pair spacing is not the lever: Cassi and Issac are 11+ apart 40% of alive time, and pair deaths split by distance
    roughly as time does.
- 14:55 **Line A launched** (implementer, `briefs/a-control.md`, variant `mx-ctl`): a team control map (influence
  map of both teams' force at each group, from beliefs) that replaces the static middle band in the farm weight:
  expand where we hold the ground, stay off ground the enemy holds, denial credit for middle/enemy groups we
  control. Training suite `maps/suites/mx/train` (seeds 61401100-61401114) for implementers' A/Bs.
- 15:00 Coordination checks (scripts/coherence.py, prism_death.py, mirror):
  - Fight incoherence is rare: rounds with 2+ of a team's bodies within 6 of an enemy where some retreat (R) while
    others fight (A/C): ~14 a game against ~190 with no mix. Retreating bodies die within 5 rounds at 8-10% (L)
    against 1.5-3% for fighting ones (selection). Earlier programmes' rally lost 1, gank level: kill coordination
    dropped.
  - **First Prism deaths (1,450 of 2,363 games with both Prisms): on middle ground 72%** (own half 24%, enemy 4%),
    outnumbered within 8 in 69%, 38% by r300, branch R (caught retreating) 68%, killer the enemy Prism 73%,
    Focus parity (0.8-1.25) 49% / weaker 40%; the victim's team loses 92%. The middle is both where the winning
    captures are and where Prisms die. Sent to the Line A implementer: control-map risk scales with each body's
    stake, the Prism's most.
- 15:00 Probes `mx-midx10/17/22` (mid_exposure 1.0 / 1.70 / 2.2, one constant each) built by a small implementer:
  the slope on the expansion axis, and a control the control map must beat.

### 15:00 Early first Prism deaths (mirror, r<=300, 552 of 1,465 games with both Prisms)
- Middle ground 70%; Focus parity (0.8-1.25) 56%; outnumbered within 8 in ~70%; victim's team lost 91%.
- Branch at death R 87%; main branch over the 10 rounds before R 57% / F 37%. Bag mostly 0-149 (78%).
- **Burst, not attrition:** HP above 70% ten rounds before in 74.5%; champion damage over the last 15 rounds is 1x max HP or more in 48%, 0.5-1x in 39%. Camps did nothing in 63%. The Prism retreats only once already hit, and dies in the retreat.
- So the lever is pre-emptive: the Prism should not stand where the enemy's local force can burst it, before it is hurt. Line A's control map (stake-weighted) is meant to cover this.

### 14:58 Probes launched on dev: mx-midx10 / 17 / 22 (mid_exposure 1.0 / 1.70 / 2.2; chy-ref 1.36). Smokes (256, noise ±6): 45.3 / 57.8 / 51.2.

### 15:01 Probe results: mid_exposure slope (dev, 10,200 games each, 2.2 min wall each)
| Variant | mid_exposure | Win % (95% CI) | OOF CAND / REF |
|---|---|---|---|
| mx-midx10 | 1.0 | 46.4 (45.4-47.4) | 831 / 865 |
| mx-midx17 | 1.70 | 50.6 (49.6-51.5) | 855 / 880 |
| mx-midx22 | 2.2 | 47.8 (46.8-48.7) | 1036 / 882 |
- Static expansion sits near its optimum (a flat top 1.36-1.7). Less middle loses 3.6, much more loses 2.2. A static
  weight can't buy more middle without paying in deaths: the control map must make the weight depend on the ground's
  state, or it is this curve again.
- A/Bs on this box run 10k games in ~2.2 min: screening is cheap, implementation is the bottleneck.

### 15:15 Closing out and Prism channels (mirror, scripts/winbag.py, prism_channel.py)
- First team to hold 1000 tributed+carried wins 86.8%, loses 12.2%. When it gets there, need ~530 (W) / 715 (L), and the
  Prism carries ~490 / 627 of it. Its bag alone covers the need in only 10-14%. In the losses, the Prism dies after
  reaching in 50%, and 516 gems are lost dying. Median 57 rounds from reaching to the win (mean 159).
- Prism channels with bag 30+: 8.2 a game, 11% complete. The winner's Prism averages 6.8 channels and 126 channel-rounds a
  game, 90 of them in channels that never finish. Cancels: stun 40%, own safety cancel 33%, lock 15.5%. A channel with no
  enemy within 8 throughout completes 89%; with 2+ enemies, 5%. Cancelled channels average bag 1,100-1,300 (winning bags
  of ~110-130 turns, judged safe on an 11-turn window: tribute_safe's params::tribute_window).
- Prism bag caps / bank earlier lost 9-22 in earlier programmes (EXPERIMENTS), so the kept bag stays.
- Combat values a carried gem flat (params::gem_value 17.5 against life_value 277) everywhere (plan.cc, abilities, fight,
  safety, guard), while farm prices a keeping Prism's gem at 1 + prism_premium (CASTOR's compounding). The bag changes
  hands at a kill (rules: the killer gets it), a 2x swing in a race. Probe launched: mx-gv05 / mx-gv2 (gem_value x0.5 / x2).

### 15:14 gem_value probe (dev, 10,200 each): x0.5 49.3 (48.3-50.2), x2 50.5 (49.5-51.5). Flat: the combat price of a
carried gem is not the lever as a scale. Batches deleted.

### 15:25 Replay study: what kills early Prisms (25 games read turn by turn, rates on all 552; scripts prism_mech*.py,
prism_warning.py, prism_stall.py, prism_hazard.py, prism_trace.py)
- Mechanisms (25): caught farming while an enemy group gathered and outnumbered it 9; team contest at one camp, Prism
  focus-fired 6; blind burst by an unseen enemy Prism 4; lost Prism duel then chased and re-stunned 2; camp death 4.
- On all 552: lingered (enemy in sight 8+ of the last 20 rounds on F/P) while outnumbered 36%, in an even contest 15%;
  enemy arrived with < 8 rounds' warning 24% (seen) / 15% (unseen first hit); camp deaths 10%.
- Of 350 outnumbered at first hit: on F when outnumbering began 81%; outnumbered a median 6 rounds first; nearest
  ally a median 2 tiles away; 1.9 allies vs 3.2 enemies within 8; **allies within 16 could have matched in 91%**, 55% of
  their branches F. Allies dealt < 1/3 of the enemy's damage in 83%.
- After the first hit: dead within 2 rounds 19%; chased 8+ rounds 51% (54% of those stunned 2+); net progress home
  0.125 tiles a round; 49% flip R/other 3+ times.
- Hazard (Prism-rounds r<=300, death within 15): no enemy within 8 0.1%; 2+ not outnumbered 1.9%; outnumbered 5.8%.
- **Line B launched** (`briefs/b-muster.md`, variant `mx-must`): on-demand muster. The Prism reads the local fight
  (safety's fight sim) with allies that can arrive before the enemy strikes; won only with arrivals -> muster call
  through comms, allies in time drop farming and join; lost even so -> the Prism leaves before the first hit,
  committed. Unlike the earlier static escorts (lost/level), it costs farm time only while a threat exists.

### 15:40 Line A result: control map as a farm reweighting is level at best (implementer report; patch patches/mx-ctl.diff)
| ver | what | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| d1 | absolute W(c), wide horizon, stake exponent | 28.7 (27.9-29.6) | 2145/716 |
| s0 | sanity: new path, exact old static weights | 49.9 (48.9-50.9) | 2354/795 |
| d2/d3 | no stake (home_ground kept / dropped) | 46.5 / 46.0 | ~2100/730 |
| d4 | sharp horizon, us at own tile | 40.4 | 1899/743 |
| d5 | static x keep(c)/keep(c_usual), unsmoothed (bug: c_usual = 0 -> cap) | 39.8 | 3184/879 |
| d6 | d5 + stake exponent | 31.3 | 3877/964 |
| d7 | d5 fixed, smoothed one body a side | 50.1 (49.1-51.1) | 2466/736 |
| d8 | d7 + auditor fixes (stale ally posts) | 50.3 (49.3-51.2) | 2681/758 |
- Stake-scaled risk on the farm weight starves the Prism (its premium keeps the stake huge every turn): -17.
- An absolute control->weight map can't reproduce the tuned middle premium (~1.7 flat optimum vs ~1.3 from one gem denied
  = one gained): the middle premium is worth more than denial explains. Sharp shares (one sighted enemy = the ground) -6.
- d7/d8 cut deaths ~0.5 a game (5.5 vs 6.0; died first 41.9% vs 51.0%) but captured no more: level.
- Lesson: the map's information is local and fast; the farm weight is the wrong lever. Local numbers belong in a trigger
  (muster / leave), which is Line B. Dropped as a candidate; variants mx-ctl* kept for reference.
- 15:42 Overseer note: no more one-knob sweeps (the midx and gv probes were the axis diagnostics; none more). A/B capacity
  goes to structural lines. On "what d2-d5's champions stopped doing" (from the implementer's replays): d1-d3's stake term
  cut Prism farming everywhere (weight near 0 below near-full control); d5 moved captures from own (43.3 vs 49.5 a game) and
  middle (5.1 vs 6.6) to the enemy half (10.5 vs 7.5), lost 88 gems captured a game, died on enemy ground in 35.5% of
  deaths (ref 12.7%) and idled more (idle-off 8.2% vs 5.5%): the map read thinly watched enemy ground as ours.

### 15:55 All champion-killed deaths by type (mirror, scripts/all_deaths.py; 13.8 a game, both sides)
- Cassi / Issac 3.52 a game each (1.76 pair events a team), outnumbered 5 rounds before only 16-18%, killed by the enemy
  Prism 60% and Vesper 18%: picks and duels against a high-Focus Prism, not local majorities.
- Prism 1.67, outnumbered at -5 50% (of those, allies within 16 could match 25% at -5; the study's 91% is at the moment
  the outnumbering began, earlier). Ryth / Marcella / HoR 42-50% outnumbered.
- The enemy Prism lands ~55% of all kills. Muster (Line B) targets the Prism's majority deaths; pair deaths need another
  answer (the pair's exposure to an enemy Prism that can one-shot it).
- Already tried by CASTOR and level: visit credit / EOQ shop timing for non-Prism bodies, endgame Prism installment
  banking. Not repeating.

### 16:35 Line B result: muster level, committed leave loses (patch patches/mx-must-v6.diff)
| ver | what | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| v1 | full brief: fight read gated on outnumbered in sight, call via shared bytes + payload, committed leave | 42.3 (41.4-43.3) | 782/798 |
| v2 | no committed leave (bug: still retreated, uncommitted), late arrivals counted | 47.5 (46.5-48.5) | 893/774 |
| v3 | no leave; call when near allies don't win and some can come | 50.0 (49.1-51.0) | 812/803 |
| v4 | v3 + Prism walks to meet the nearest called ally | 50.0 (49.0-50.9) | 806/820 |
| v5 | v4 without the outnumbered gate (fight sim decides) | 50.3 (49.3-51.3) | 918/803 |
| v6 | v5 + auditor fixes, one sim per read | 49.5 (48.6-50.5) | 839/795 |
- Leaving early loses 2.5-7.7: the retreat gets caught and costs farm. Muster fires (v6: ~29 calls, 20 joins, 123 ally
  turns beside the Prism a game) and cuts Prism deaths 5-10% (1.02 vs 1.09), early ones barely; win level. 71 of 93
  early deaths in v6 had a lost read with nobody able to come in time. Comms: 3-6 free bits with six bodies.
- Two lines now cut deaths a little at no win (d7: -0.5 deaths a game; muster: -7% Prism deaths). Death count alone is
  not the score: kills and the gems that change hands are the other half of the exchange.

### 16:40 Prism Focus race (mirror, scripts/prism_race.py; both Prisms alive at R)
| R | Focus ratio high/low | games | first Prism death lower / higher / none | higher-Focus team wins |
|---|---|---|---|---|
| 150 | 1.0-1.1 | 706 | 30 / 26 / 45 | 50% |
| 150 | 1.3-1.6 | 435 | 37 / 20 / 44 | 66% |
| 150 | 1.6+ | 274 | 47 / 16 / 37 | 74% |
| 250 | 1.0-1.1 | 565 | 26 / 22 / 52 | 50% |
| 250 | 1.3-1.6 | 394 | 32 / 20 / 48 | 62% |
| 250 | 1.6+ | 288 | 48 / 11 / 42 | 80% |
- The Prism duel is decided by relative Focus, and the bot ignores it in macro: farm prices no enemy-Prism threat (only
  static side weights and the carrier's pack zone on walks). "Avoid enemy Prisms" unconditionally lost 6 before; making
  it conditional on the duel (avoid when it loses, seek when it wins) is new.

### 17:00 Capture gems by ground (mirror, scripts/captures_ground.py), W vs L a game
| phase | own W / L | mid W / L | enemy W / L |
|---|---|---|---|
| r1-150 | 110.6 / 107.2 | 61.3 / 50.5 | 2.3 / 1.8 |
| r151-300 | 134.8 / 128.1 | 96.3 / 66.6 | 4.7 / 3.0 |
| r301-600 | 206.4 / 199.9 | 189.7 / 119.3 | 12.0 / 6.2 |
| r601+ | 111.8 / 115.0 | 148.8 / 76.4 | 10.5 / 5.0 |
- The middle decides; own halves are equal. The middle holds 259 gems in 8.3 groups (each half ~113); both teams take
  ~22% of its r1-300 potential (respawns counted).
- DELPHI's earlier programme (research/macro-delphi/NOTES.md): every restriction of farm choices lost in proportion to
  how much it bound (pack -11, convoy -5), soft prices that rarely change picks were level (hub, pairprice), Prism-only
  yield (E10) level and rarely fired. So the lines now are re-pricings from the rules that change many picks.
- **Line C launched** (`briefs/c-duel.md`, `mx-duel`): the duel read (enemy Prism's combo vs each body; Prism vs Prism)
  enters farm pricing: contact chance x death cost where the duel is lost, x kill worth for our Prism where it wins;
  hunt by the duel read. Covers our Cassi/Issac too (60% of their deaths are to the enemy Prism).
- **Line D launched** (`briefs/d-deny.md`, `mx-deny`): the enemy Prism's premium (CASTOR's expm1(k rho H) from the
  enemy's side) on denial: a group the enemy Prism would otherwise take gains P_enemy x gems x premium_enemy, on top of
  the static weights (which already hold plain denial). Explains the middle premium beyond denial and makes it dynamic
  (large early, near the enemy Prism's takers, zero when it is dead or absent).

### 17:05 Line C result (interim hand-back, 3 of 6 versions; patch patches/mx-duel.diff): level
| ver | what | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| v1 | avoid + seek/hunt | 49.4 (48.5-50.4) | 2173/872 |
| v1a | avoidance only | 49.1 (48.1-50.0) | 1394/904 |
| v1b | hunt + seek only | 49.9 (48.9-50.8) | 1128/871 |
- A lone body nearly always loses the duel read against an enemy Prism, so avoidance became a broad distance-graded
  avoid (the prior that lost); our Prism read a won duel alone on 8-37 turns a game, so seek rarely fired. OOF up (prunes
  switched off when seeking). Dropped.

### 17:10 Supply by camp type (mirror): Monoliths are 3% taken
| type | supply r101-600 a game | captured | share |
|---|---|---|---|
| Wolf | 924 | 389 | 42% |
| Elk | 974 | 467 | 48% |
| Gem cluster | 625 | 318 | 51% |
| Gold cluster | 63 | 35 | 56% |
| Golem | 232 | 89 | 39% |
| Monolith | 458 | 14 | 3% |
- 31% of maps have Monoliths (2 on average, 70% middle). Where one was captured, the team with more Monolith captures won
  80%. The op dithers: 27,264 MONO START / 24,638 END over 1,550 game-sides, most ENDs after 1-5 rounds. prism_premium is
  off for Monolith groups.
- **Line E launched** (`briefs/e-mono.md`, `mx-mono`): a committed team Monolith operation (declared once through comms,
  team-valued with the Prism premium, commitment on remaining value since camps never regenerate, chosen tank, stuns on
  the Monolith), iterated on a Monolith-map subset of train, read on full train.

### 17:15 Line D result: enemy-premium denial level (patch patches/mx-deny.diff)
| ver | chance the enemy Prism takes g | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| v1 | race share d_us/(d_us+d_it) (~0.5 in the middle) | 50.2 (49.2-51.2) | 872/816 |
| v2 | its share of the enemy's pace over the supply (sums to its take) | 50.5 (49.6-51.5) | 860/860 |
| v3 | the take on the groups it reaches first | 50.6 (49.6-51.6) | 946/860 |
- Priced consistently the term is small: the enemy Prism takes 5-10% of supply a cycle, so P x premium ~0.04-0.06 a gem;
  0.3-0.6% of picks change. v1's raw race share moves +10 middle gems a phase and loses as many from the own half: the
  static push's flat top again. The premium itself is ~1.7 mean (2.8 at r1, ~1.2 by r550). Dropped.

### 18:20 Line E result: a committed Monolith op loses (patch patches/mx-mono.diff; subset maps/suites/mx/train-mono)
| ver | change | Monolith-map subset win % (3,106 games) | OOF cand/ref |
|---|---|---|---|
| noop | never farm Monoliths (ablation) | 48.3 (46.6-50.1) | |
| prem | only the Prism premium / capture changes for Monolith groups | 49.5 (47.8-51.3) | |
| v1 | whole team via the siege code | 5.1 | 262/181 |
| v2 | op through farm, one decision in comms | 16.1 | 396/188 |
| v3 | declare only when no heal trips are needed; call-off until seen clear | 43.6 | 288/249 |
| v4 | nearby enemy ends it only if our fight read loses | 42.4 | 307/241 |
| v5 | smallest crew by arrival | 39.3 | 345/238 |
| v4a | v4 + audit fixes | 45.4 (43.6-47.1); full train 48.6 (47.7-49.6), non-Monolith maps 50.1 | 286/268 |
- Diagnosis (ref mirror): ~7.4 op ENDs a game a side, 58-62% while the Monolith still sleeps at full health; 3.35 wake
  episodes a game, 32% reach a kill; abandoned wakes had 1.46 bodies in range (kills 3.1). Either side spends ~1,000
  body-rounds near a Monolith a clear for a 500 reward: about half the normal farm's ~1 a body-round. So the low capture
  share is right: Monoliths as executable are poor value; chy-ref's opportunistic use is worth ~1.7 on those maps.

### 18:25 Held-out reads of the near-level variants launched (dev/hold): midx17 hold, mx-deny dev, mx-must-v5 dev,
mx-ctl (d8) dev. Line F launched (`briefs/f-stand.md`, `mx-stand`): `stand_lost_at` sends the Prism (always), Cassi /
Issac and big-bag carriers home from stands the team WINS whenever they would fall there (`falls && self_falls`),
without asking whether the retreat can escape; retreats don't open distance (0.125 tiles a round). New rule: leave a
won stand only if the retreat escapes the pursuers before their damage kills us; otherwise fight.

### 18:32 Held-out reads (10,200 each)
| variant | suite | win % (CI) | OOF cand/ref |
|---|---|---|---|
| mx-midx17 | hold | 50.4 (49.4-51.4) | 816/824 |
| mx-deny (v2+fixes) | dev | 50.0 (49.0-50.9) | 978/924 |
| mx-must-v5 | dev | 49.9 (49.0-50.9) | 974/820 |
| mx-ctl (d8) | dev | 50.1 (49.1-51.1) | 2693/777 |
- All level held out. Batches deleted.
- **Line G launched** (`briefs/g-pursue.md`, `mx-pursue`): `preyable()` lets a healthy enemy off our ground walk away;
  admit it when it cannot escape our side's reach before our damage kills it (the escape test from the pursuer's side).

### 18:55 Line F result: won-stand escape rule level (patch patches/mx-stand.diff)
| ver | change | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| v1 | Prism only; 2+ hits = the whole walk home in reach | 49.6 (48.6-50.5) | 808/820 |
| v2 | v1's test for all falls cases | 49.9 (48.9-50.8) | 933/790 |
| v3 | all cases, hits as the plan's lower bound | 50.1 (49.1-51.0) | 878/758 |
| v4 | v3 + targeting while kept | 50.1 (49.1-51.1) | 905/743 |
| v5 | v4, Prism only | 49.9 (49.0-50.9) | 823/780 |
- Fires 0.7-2.6 turns a game; deaths and kills move within noise. The won-stand exit is rare enough not to matter.
- Line G (pursuit escape test) interim train reads: v1 50.4 (OOF 2253/742), v2 49.9, v3 50.1: level so far.
- midx17 on the fresh conf1 suite launched (the best measured candidate).
- 18:56 midx17 on conf1 (fresh): 49.9 (48.9-50.9), OOF 872/949. Pooled held-out dev+hold+conf1: ~50.3 of 30,600: level.
- Line H launched (`briefs/h-wake.md`, `mx-wake`): replace the Monolith wake rule's gather share / 12-round timeout with
  a derived test (crew in range can kill it before its hits exhaust them); abandoned wakes (68%) hand the enemy
  softened Monoliths.

### 19:01 Line G result: pursuit escape test level (patch patches/mx-pursue.diff)
| ver | change | train win % (CI) | OOF cand/ref |
|---|---|---|---|
| v1 | escape test (per-pursuer hit layers in the chase race), all bodies | 50.4 (49.5-51.4) | 2253/742 |
| v2 | layers on demand + cheap bound first | 49.9 (48.9-50.9) | 1269/790 |
| v3 | bound before the fight sim + chase-posting allies join | 50.1 (49.2-51.1) | 1398/788 |
| v4 | v3 + auditor fixes | 50.0 (49.0-50.9) | 963/824 |
- Admits ~1 extra chase a game; chasers rarely die; kills within noise. Too rare to matter.

### 19:10 Channel time is not farm time (code read, economy/bank.cc)
- The 15:15 finding (winner's Prism: 90 channel-rounds a game in channels that never finish) is not a waste: a channel
  starts only on a turn the Prism stands at an altar anyway ("standing in a channel costs nothing"; damage does not
  interrupt it, and continue_tribute cancels it only to flee or fight). No line on channel pricing.

### 19:20 Line H result: derived Monolith wake rule level (implementer's logs; its report pending)
| ver | train-mono (3,106 games) | train (10,200) |
|---|---|---|
| v1 | 48.8 (47.1-50.6); debug 49.0 | 49.6 (48.7-50.6) |
| v2 | 49.2 (47.4-51.0) | 49.8 (48.8-50.7) |
| v3 | 49.4 (47.6-51.1); debug 49.2 | 49.8 (48.9-50.8) |
- Dropped. Monoliths stay a side matter: E and H both level or below on the Monolith maps themselves.
- `bots/charybdis` now holds the best measured candidate, mx-midx17 (one line: mid_exposure 1.70;
  patches/mx-midx17.diff), level within noise. Final 100k read started on `fin` (`mx-tethys-fin100k`).

### 19:20 Final 100k read (fin, 10,200 games, default fuel): mx-midx17 49.3% (48.3-50.2); OOF turns CAND 71,933 in
7,356 games, REF 72,893 in 7,429. Level. At 1 point per side-weight it is not worth placing in charybdis.

### 19:25 Line H detail (implementer's report; patch patches/mx-wake.diff, variant mx-wake = v3)
- v1 wakes 1.28 a game vs ref 1.64, clears 0.49 vs 0.56, captures 0.48 vs 0.56: kills a wake 34% -> 38%, less
  Monolith farm overall. The derived "can finish" test rarely passes (~11 phases of hold against ~83 needed).
  Open bug: with the timeout gone, 2+ claimers can wait at the staging ring indefinitely.
- v3 adds heal-trip rotation, one stun a cooldown, drops allies under the line; its keep fired 1,193 times on the subset.
- Started and stopped at the end: scripts/kill_bags.py (who takes the victim's bag at a kill, and whether our Prism stood
  near a non-Prism ally's kill). Unread. Untested lever it was for: route the last hit on a carrying enemy to our
  Prism (the killer takes the bag; on the Prism every gem is +1.5 Focus), along the axis of the two large past wins
  (507 carry, 527 premium). Grep shows no kill-to-Prism routing in combat/.
