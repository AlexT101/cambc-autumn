# SELENE: macro refactor of charybdis (2026-11-13, 02:00-10:00 UTC)

Reference `bots/variants/chy-ref` (= bots/charybdis at 0f6fa9879). Every A/B: candidate vs chy-ref, `--fuel 200000`,
own drafts (`--no-test-draft`), fast runner, release builds. Suites: `maps/suites/mac13/dev` (5,120 maps, 10,240
games), `maps/suites/mac13/hold` (2,560 maps). Study suite (never for decisions): `maps/suites/mac13s/study` (512
maps, seeds 147200-147201). Further fresh suites from seeds 147202+.

## Log

- 02:00 Read brief, rules, prior programme notes (macro-orchestrators-2026-11-11 and the eight NOTES), architecture
  map of charybdis's macro (explore agent). Opening angle: space / map control.
- 02:05 Mirror study `mac13-selene-mirror` (chy-mirror = copy of chy-ref, 1,024 games on study): 50.0%, 2.8 min wall.
  Extracted to `replays/.an-mirror` for analysis.
- 02:30 Mirror facts (1,024 games, `/tmp/selene/*.py` scripts, copied to `research/mac13-selene/scripts/`):
  - Captures by zone (group's walking share toward the enemy spawn: own < 0.4 <= mid <= 0.6 < enemy), winner vs
    loser gems a game: own 586 vs 562 (equal), **mid 452 vs 269**, enemy 18 vs 4 (nobody farms the enemy half).
    Upper-bound supply (every respawn recaptured): own 1,218, mid 2,200 (shared), enemy 1,218. Mid is 33% used.
  - Time (analysis/macro.py): walk 56-61% of alive time, work (camp+hold) 26-29%, walk_waste (steps beyond the
    straight line) 28-32%, regroup 14%. Recalls 43 a team-game (45% at full health; travel recalls, removing them lost
    before).
  - Per type (whole game): Prism captures 485 gems / 1,669 gold; Vesper 231 / 2,408; Cassi 82 / 228, Issac 93 / 258,
    Willow 14 / 47. Three of five bodies in most comps capture almost nothing (they clear for the Prism).
  - Deaths: 77% of kills were seen by the victim the round before; only 10% were unseen by the victim but seen by an
    ally (shared sightings cannot move much).
  - First Prism death (282 of 455 two-Prism games): victim's team wins 8%; 74% in the mid, 23% own half; killer the
    enemy Prism 70%; bag ratio victim/other < 0.67 in 36%, parity in 59%; **40% with no ally within 6** of our Prism.
- 02:18-02:25 Territory knob probes on dev (10,240 each; ~7 min wall per A/B):
  | variant | change | dev |
  |---|---|---|
  | sel-hp0 | home_power 1.89 -> 0 (no enemy-ground discount) | 48.1 (47.1-49.1) |
  | sel-hp1 | home_power -> 0.95 | 50.2 (49.2-51.2) |
  | sel-mid2 | mid_exposure 1.36 -> 2.0 | 48.9 (47.9-49.9) |
  The static side valuation sits at its optimum: farming the enemy half blindly costs 2 points, more mid bias 1.
  Space has to be gained by something that knows *when* a region is safe or winnable, not by static weights.
- Debug mirror (1,024 games) decision branches: farm 58%, none 8.7%, retreat 5.9%, Willow support 5.4%, bank 5.2%,
  hold 4.3%, altar guard 2.3%, tribute 2.2%, recall 2.0%, chase 1.5%.
- 02:45 More mirror facts: per team-game the Prism captures 16.6 groups / 436 gems: 294 from its own clears, 127 from
  ally clears; allies capture 40 groups / 510 gems themselves. Loss episodes (analyze.py losses on the debug mirror):
  deaths ~430 gems a side a game, camps lost (stolen / contested / invaded) ~350. Game breaks (macro.py) spread over
  the game (quartiles r168 / r374 / r591), cause farm 56%, fight 36%; whole-game winner advantage fight +439, farm +222.
- 02:45 Candidate 1 `sel-conv` (implementer launched): the conveyor. Prism's tile always posted; allies price the
  Prism's collection (gems x (1 + carried_bonus) weighted by the Prism's ETA) in their farm choice, so they clear near
  the Prism and hand it the groups; the Prism collects rather than clears. Division of labour (Prism is a weak clearer)
  plus implicit cohesion (40% of first Prism deaths have no ally within 6).
- 02:55 Death windows (mirror): rounds with >= 1 enemy body dead are 23% of the game; in them our mid capture rate
  rises (37 -> 58 gems / 100 rounds) but enemy-half captures stay ~2-6 / 100 rounds even with 3 enemy bodies dead.
- 03:00 Missed handoffs (mirror, Prism games): allies capture gem groups with our Prism within 12 tiles ~10,400 times
  in ~910 team-games; in half (90k gems, ~100 a team-game) the Prism was just walking. ~100-200 gems a game could
  reach the Prism's bag without anyone farming elsewhere. Sent to the sel-conv implementer.
- 03:05 Replay study (read-only agent, 16 games breaking r111-319, counts over 241 games breaking r60-400; scratch in
  /tmp/selene-study): in the +-30-round break windows losers lose 11,381 gems in bags, winners 704; loser Prisms 70%
  of it, 29 of 45 killed by the winner's Prism; 629 of 825 Prism deaths are Prism-on-Prism (whoever casts first
  wins; in 18 of 29 the victim saw the killer at its turn start and still ended 2-6 tiles away). Patterns: (1) the
  bag-carrying Prism farms/holds a contested mid group inside the enemy Prism's reach (45 of 241 windows); (2) hurt
  bodies stay in retreat beside enemies 10-25 rounds (94 of 182 loser deaths after 3+ R turns); (3) loser outnumbered
  or alone where it dies (107 of 182 outnumbered within 8); (4) loser softens a group and the winner takes it (65 vs
  26 groups); (5) Cassi & Issac split and one dies alone (59 vs 21 loser/winner pair deaths, 25 with partner 8+
  away; winners' pairs stay within 1-2 tiles). Winners' big-bag Prisms hunt loners; their pack chases together.
- 03:05 Candidate 2 `sel-twin` (implementer launched): Cassi & Issac farm and fight as one unit - one shared target
  priced as a crew of both, shared danger in leave/retreat, no waiting.
- 03:15 Walk legs (continuous moves of 4+ steps, 200 mirror games) take 1.85x the terrain shortest path between
  their ends (terrain itself adds only 9% over Chebyshev). Legs with an enemy seen: 2.15x (tactical dancing); quiet
  legs 1.53x. On the debug traces, quiet 12+ legs with farm only waste ~10%; Willow's support legs ('h') waste ~55%.
  Quiet farm routing is not where the time goes; it goes near enemies.
- 02:55 (real time; earlier stamps ran ahead) Prism bags decide: 635 Prism-on-Prism kills, killer's Focus > 2x the
  victim's in 71%, parity (0.8-1.25) in 15%. Win rate by our/their Prism bag ratio at r200: <0.5 16%, 0.5-0.8 36%,
  parity 50%, 1.25-2 64%, >2 84% (r300: 7 / 33 / 50 / 67 / 93). A 25% bag edge is worth ~+6 points if it costs
  nothing elsewhere. Steals (capturer did < half the damage): ~97 gems a game in all, 4.25 a game.
- 03:22 **sel-conv** (conveyor; patch patches/sel-conv.diff) dev: **49.1% (48.1-50.1)** of 10,240; OOF 1,022 vs 709.
  Implementer's debug smoke: handoffs 4.76 vs 4.41 a Prism team-game (123 vs 111 gems), Prism capture gems 467 vs 428,
  Prism-to-nearest-ally 5.6 vs 6.0. The ally-side premium barely moves handoffs; the Prism-side 'Q' gate `worked`
  (ally hit last round or visible in attack range) binds: of ~105 Prism turns a game with an ally's claim in reach,
  35 are worked. Level: allies relocating toward the Prism cost about what the extra handoffs gave.
- Mirror split by group type (per team-game): allies hold wolves 13.2 (148 gems), gem clusters 9.5 (160), elk 4.2
  (124); the Prism clears and holds elk 3.3 (116), wolves 4.1 (77), gem clusters 2.2 (54).
  sel-conv on its first 1,000 kept dev games (abcmp.py): Prism bag r300 168 vs 158, Prism capture gems 369 vs 353,
  handoff gems 112 vs 102, Prism deaths 0.74 vs 0.82, pair deaths 2.0 vs 2.1: right direction, small.
- 03:20 Candidate 3 `sel-conv2` (implementer launched, from sel-conv): the Prism side - allies post a "working" bit
  with their claim; the Prism's 'Q' accepts imminent clears (working, or claimer's walk <= the Prism's), joins as
  crew, holds alone.
- 03:30 Death hazard per 1,000 champion-rounds (mirror, 400 games) by zone and allies within 6 (0/1/2/3+): home
  0.06-0.19; own 0.38 / 0.70 / 0.90 / 0.77; mid 2.54 / 2.82 / 2.19 / 1.63; enemy half ~6.4 / 6.5 / 2.4 / 3.7.
  Support cuts mid hazard ~40% at 3+ allies; worth ~0.1 gems a round for an empty-handed body (earn rate 0.29), ~0.3
  for a 300-gem Prism: cohesion pays only for big bags.
- Victim Prism's branch on its last two turns before a Prism-on-Prism kill (debug mirror, 1,258 kills): stop
  game-ender 'E' in ~48% (late, mostly lost games anyway), retreat 'R' ~36%; at parity (188) retreat 114, farm 12.
  Decisive parity deaths are failed retreats (double turns: the enemy Prism acts last in one round and first in the
  next).
- 03:26 Candidate 2 **sel-twin** returned (patch patches/sel-twin.diff). Debug smoke (our 246 pair games): C&I distance
  12.9 -> 7.8, within 2 tiles 20% -> 34%, pair deaths 2.33 -> 2.09 a game, but pair captured gems 193 -> 159 and team
  tributed 774 -> 670: cohesion costs the farm, as every earlier pack design did. Dev A/B launched for the record.
- 03:30 Candidate 4 `sel-intel` (implementer launched, from chy-ref): enemy Prism sightings shared in comms and merged
  into teammates' beliefs as tracked sightings; our Prism's farm prices the duel (expected loss of working inside a
  parity-or-bigger enemy Prism's reach, fresh info only); no step rules.
- 03:35 Enemy in sight (26% of alive champion-rounds): camp hits fall from 22.6% to 9.8% of turns, moving 69% vs 60%.
  Branches with an enemy seen: farm 46% (only 8.5% hitting a camp), retreat 20% (vs 0.9% quiet), bank 6, chase 5,
  altar guard 4.4. Sight of an enemy halves work: the "pessimism tax" is ~3-4% of all champion time.
- Retreat turns with an enemy in sight (debug mirror, 400 games, 171k): 46% at full health, 85% of those take no
  damage in the next 5 rounds (2% die). Below 30% health 18% die within 5 rounds.
- 03:40 Overseer: screen on a separate suite, keep dev/hold for finalists; look for systems of changes that cover
  each other's costs. `maps/suites/mac13s/screen` (seeds 147202-147221, 5,120 maps) is now the screening suite;
  `maps/suites/mac13s/x2` (147222-147241) is generating for a final fresh confirmation. dev has been read by 5 A/Bs
  so far (3 probes, conv, twin).
- 03:42 **sel-twin** dev: **46.4% (45.5-47.4)** of 10,240. Lost 3.6 points: the pair's cohesion costs more farm than
  the deaths it saves. Where C&I deaths happen (mirror): mid 1,211 (partner within 6 in 577), own half 692 (partner
  near in 485), enemy half 85: most pair deaths happen with the partner near anyway. Dropped.
- Housekeeping: delete only `*.repl26a` of finished batches from now on (keep results.json for ab_classes.py);
  sel-conv's and sel-twin's dev batches were deleted whole.
- 03:45 Candidate 3 **sel-conv2** returned (patch patches/sel-conv2.diff): work bit per non-Prism ally (fits only on
  18/26 four-body, 8/42 five-body, 38/140 six-body Prism teams), 'Q' accepts worked / working / imminent clears.
  Debug smoke (256): handoffs 4.84 vs 4.42, Prism capture gems 469 vs 431, bag r300 201 vs 170, r500 333 vs 261,
  Prism deaths 0.84 vs 1.00. Q gates per Prism team-game: 325 keep-gems farm turns, 57 with an enemy in sight (Q
  never runs), 115 candidates: 48 worked, 5 work bit, 14 imminent, 49 cannot start (unseen claimer, no bit).
  Screening conv2 and conv on `screen` (10,240 each).
- 03:58 Analysis agent launched: trace copy `sel-trace` (debug-only lines) to tabulate retreat triggers x health x
  outcome, to find over-cautious retreats (labour slack) and under-cautious ones.
- 04:10 Screen reads (10,240 each): **sel-conv2 50.4% (49.4-51.3)**, **sel-conv 50.5% (49.5-51.4)**. The conveyor is
  level (conv pooled with dev: ~49.8% of 20,480).

## 04:13 conv2 at scale (1000 sampled screen games, abcmp)
- Prism bag r300 236 vs 225, r500 369 vs 356; handoff gems 153 vs 145; Prism deaths 0.57 vs 0.60.
- But earned 5184 vs 5307 and tributed 755 vs 781: the bag gain is real but small, and total income falls by more than it adds.
- Reading: the conveyor moves gems into the Prism at the cost of ally income (relocation). The bag-to-win link in the mirror is largely confounded (the stronger side has a bigger bag). Bag growth alone is not a lever; it needs to be paid for by more total income or by fewer bag losses.

## 04:20 sel-intel returned (patch patches/sel-intel.diff)
- Enemy Prism record in comms (cell, round stamp, log Focus), teammates merge it as a tracked sighting, the Prism's
  and big carriers' farm subtract a measured duel hazard x (bag + 61 x farm rate).
- Study (1,024 each, noisy): final 47.8% (44.7-50.8); earlier versions 44.5-44.7. Prism deaths 0.64 vs 0.78, all
  deaths 4.82 vs 5.32, but tributed 723 vs 769. Ablations: told sightings only 47.4, duel pricing only 47.0, layout
  only (record laid out, never posted; camp record lost on some maps) 47.1 -> the camp-record bits are worth points.
- Not screened: it loses on every read. Same finding as twin and conv: caution / cohesion saves deaths but costs
  more farm than they are worth. Every design that adds caution has lost; the direction left is *less* caution
  where it is free (retreat study pending).

## 04:30 Retreat-trigger study returned (sel-trace, 1,024 study games, 249,915 retreat turns in sight)
| trigger | /game | full hp | hit<=5 | died<=10 |
|---|---|---|---|---|
| stand_lost_at, no hit now ("pursued") | 56.3 | 46% | **7%** | 3.3% |
| stand_lost_at, hit now, nearest >=5 | 57.4 | 50% | 13% | 4.2% |
| stand_lost_at, hit now, nearest <=4 | 53.0 | 22% | 48% | 8.4% |
| low (recall line) | 31.1 | 0% | 26% | 19.8% |
| pack (outmatched) | 25.4 | 28% | 40% | **18.3%** |
| Willow exposure | 18.6 | 48% | 8% | 4.4% |
Baseline non-retreat turns in sight: hit<=5 13.3%, died<=10 2.6%.
- Over-cautious: the pursued stand (walkers within pursuit_steps=2 of their reach join the stand) fires with the
  nearest enemy 6-8 tiles away in 78%; at full health hit<=5 6%, below the 11.6% of full-health champions that keep
  working. Mostly bag carriers (16+ gems, 41/g), Prism, C&I.
- Under-cautious: pack fires late (first retreat turn of a run with the nearest at 4.0 tiles, 14.6% die); with the
  enemy Prism's Focus ahead of ours pack deaths are 27.7%.
- Plan (system): `sel-pursue` frees labour (a walker joins the pursued stand only if its walk to reach is within
  what it gains on us before our next step: 1, +dash, +double turn) and `sel-pack` reads the pack zone one walk
  ahead so the deadly retreats start a turn sooner. Each alone, then combined.
- 04:35 Implementers launched: `sel-pursue` (+ probe `sel-ps1`: pursuit_steps 2 -> 1) and `sel-pack`.
- 04:45 Prism dominance episodes (mirror, 455 two-Prism games; strong bag >= 40 and >= 2x weak + 10, both alive,
  3+ rounds; scripts/dominance.py): 2.9 a game, mean 73 rounds; strong side wins 80%; strong Prism dies in 1.7%.
  By the closest the two Prisms come: within 6, 705 episodes, the weak one is killed 65%, strong team wins 90%
  (but these start at strong bags ~850: mostly the endgame carry, where the weak Prism comes to stop the ender);
  never within 10, 470 episodes (~1 a game), strong bag ~350 vs ~40, last ~30 rounds, end by the weak one growing
  (qgrow) or the strong one banking; strong team wins only 61-68%, weak never killed. A dominant Prism does not
  hunt. Candidate `sel-hunt` queued: a dominant Prism (duel won in openings, prism_dominant) goes for the weak
  enemy Prism's tracked position when its kill is worth more than its farm, using teammates' sightings (sel-intel's
  record, read only by the hunter, so no team-wide pessimism).
- 04:57 **sel-pack** returned (patches/sel-pack.diff, combat/guard.cc only): pack members count within
  pack_radius + walk_ahead(e) (turns before ours incl. double turns, ready dash, teleport landing; unseen: 1 step
  since `possible` already includes this round). Applied everywhere the zone is read (retreat, work guard, farm /
  chase boxes) to keep the invariant that advances stay out of the retreat zone. Debug smoke: pack-retreat turns
  50 -> 100 a game, runs 22 -> 47. Smoke 50.8% (256). Screening on `screen`.
- 05:00 Implementer launched: `sel-hunt` (dominant Prism hunts the weak enemy Prism, priced in its farm choice).
- 04:59 **sel-pack** screen: **49.1% (48.2-50.1)** of 10,240; OOF 780 vs 589. Retreating from packs a walk sooner
  (twice the pack-retreat turns) costs ~1 point: the deaths it saves do not pay for the farm. Same lesson again.
- 05:08 **sel-ps1** (pursuit_steps 2 -> 1 only) screen: **50.6% (49.7-51.6)** of 10,240; OOF 767 vs 597. Level to
  slightly up: the first lever in this programme that points up is the one that removes caution.
- 05:15 **sel-pursue** returned (patches/sel-pursue.diff; fight.cc stand_lost_at + Safety::pursuit_gain): for
  healthy champions in a pursued stand, a walker is dropped if its walk to reach exceeds what that walk can shrink
  by our next turn (t0 + dash + R1 - R0, from turn slots and strike reach); in practice only walk-2 walkers with
  gain 1 (plain walkers, melee dashers); Vesper, Ren, unseen dashers, Vendetta kept. Smoke 50.8% (256). Screening.
- 05:15 Probe batch launched: `sel-ps0` (pursuit_steps 0), `sel-wil` (no Willow exposure retreat), `sel-ps1w`.
- 05:16 **sel-pursue** screen: **51.0% (50.0-51.9)** of 10,240; OOF 632 vs 697. Best so far; direction confirmed.
- 05:25 Prior programme (EXPERIMENTS "Macro programme ... charybdis 2026-11-11"): hunting/yielding to enemy Prisms,
  kill routing, turn-order kill bid, chain lookahead (45.6), team plans, etc. were all level or lost against ocean.
  "Caution loses in proportion to the work it costs" was already their finding; nobody tried *removing* caution.
- Kills (mirror, 512 games): 13.9 deaths a game; the Prism lands 56% of kills and moves 226 gems a game (Vesper 43,
  camps 11); victims C&I 3.6 a game (linked), Prism 1.6, Willow 1.3. Last-hit routing has no room: non-Prism kills
  of 20+ bags with our Prism within 4 are 0.19 a game.
- Farm turns with an enemy in sight (debug mirror, 400 games, ~976 a game; scripts/farmseen.py): hitting 18.6% (quiet
  29.8%), within 3 of the target but not hitting 19.4% (quiet 11.5%), 4-8 away 26%, >8 33%. ~80 turns a game in sight
  near the target and not working: the work guard's price of being seen (candidate for the next labour piece).
- 05:28 Probe batch returned (patches/sel-ps0.diff, sel-wil.diff, sel-ps1w.diff): ps0 = pursuit_steps 0 at every
  reader except bank's may_chain (kept 2 as chain_reach_steps); wil = Willow's exposure retreat and its guard mirror
  removed (Willow uses the generic guards); ps1w = ps1 + wil. Smokes 52.7 / 48.8 / 53.1 (256). Screening all three.
- 05:30 Analysis agent launched: trace (sel-ftrace) of farm turns in sight near the target but not hitting, by reason.
- 05:34 Probe screens (10,240 each): **sel-ps0 48.8 (47.8-49.7)** (no pursuit at all loses: walkers 1 step out are
  real), **sel-wil 49.7 (48.7-50.7)** (Willow's exposure retreat is about right), **sel-ps1w 50.8 (49.8-51.8)**
  (= ps1). The pursuit horizon has an interior optimum near 1 step; sel-pursue's per-walker gain (51.0) is the
  principled form. Pursue goes to dev as the first finalist; next: systems built on it.
- 05:37 **sel-pursue** dev: **50.4% (49.4-51.4)** of 10,240; OOF 584 vs 1,085. Pooled with screen ~50.7% of 20,480:
  a real but small gain (~+0.7). Mirror games: median 757 rounds (IQR 597-1008), 38 of 1,024 reach the limit.
- 05:41 Session resumed after a stop (overseer). sel-hunt implementer and sel-ftrace analysis still running.
- Gold (mirror, scripts/gold.py): all bodies spend ~90-95% of earned gold; only the Prism holds much (time-weighted
  unspent 103 losers / 249 winners, mostly late with big bags). Gold spending is not the gap.
- Group-class utilisation (scripts/util.py; supply = rounds/(respawn+10) x gems): gem clusters 70%, elk 51%, wolves
  46%, golems 35%, **Monoliths 10%** (744 supply a game where present, winners 53 vs losers 22). Monoliths were the
  subject of whole earlier programmes (M1, sieges, crews: level), so not reopened.
- **Death windows** (scripts/window.py, winbranch.py; mirror): our capture rate is flat in the number of enemy bodies
  dead (k=0 110, 1 107, 2 110, 3 106 gems / 100 team-rounds), though the enemy half keeps ~100-122 gems of live camps
  standing. With 3 enemy bodies dead only 3.5% of our turns are spent in the enemy half (1.1% at k=0), farm turns fall
  67% -> 42% and tribute rises 1.3% -> 10.8%, bank 5 -> 8.7%. We bank in the window but never take the undefended
  half: the farm's enemy-ground discount (home_ground, static) prices the enemy team's threat even when it is dead.
  Candidate `sel-window`: the discount scales with the share of enemy bodies that can be at the group during our
  stay (alive, or respawned and walked there by its end).
- 05:58 Window reach (scripts/winreach.py, 300 mirror games): in 30.5% of our alive body-rounds during death windows a
  live enemy-half group stands within 10 tiles that we could finish before any dead enemy is back (respawn + crow
  walk from its spawn > now + distance + 15), 28.3% within 11-20. **sel-window** implementer launched (base sel-pursue):
  home weight = 1 - f (1 - static), f = share of enemy bodies alive or back at the group before our stay ends.
- 06:10 **sel-hunt** returned (patches/sel-hunt.diff; economy/hunt.cc + farm_hunt): a Prism with 2x the enemy Prism's
  Focus that wins the turn-counted duel walks to it when the kill (0.65 x bag + life + gold) beats its farm rate.
  Inert: 0.45 hunt turns a game (debug study, 1,024), 9 kills; escapes() rejects 91% of sighted targets (a Prism is
  no faster than its prey) and unseen weak Prisms cannot be located without shared sightings (whose team-wide use
  lost in sel-intel). Smokes 50.0% (256), 49.8% (debug 1,024). Not A/B'd; dropped.
- 06:12 **sel-ftrace** returned (scripts/ftrace.py; 1,024 debug study games, 588 farm turns in sight a game): 17.5% hit
  a camp; within 3 of the target and not hitting 122 a game: respawn waits 40 (hit<=5 18.6%), capture walk/hold 33
  (25%), approach 19, ranged arrived 12 (harmless), fight-spent 11. All guard blocks together 1.8 a game: the step
  guards are not a lever. Far (>8) turns: 43% walks, 35% respawn waits, 36% with a target change within 3 turns.
- Bags lost at death (scripts/deathbags.py, mirror): winners 3.7 deaths / 46 gems a game, losers 10.2 / 269, of which
  the loser Prism 1.5 deaths / 189 gems. Camp kills lose only 3-7 gems a game.
- 06:28 Endgame (mirror; scripts/lead.py, bigtrib3.py): tributed lead alone predicts little (r300 +50..100 62%),
  tributed + bags strongly (r300 +50..100 81%, < -200 5%): Prisms hoard and bank 500+ in one channel late. Tributes
  of 200+ gems: ~8.7 attempts a game; 60% succeed with no enemy within 8, 4-15% with enemies near. Failed attempts
  spend ~85 channel turns a game (both sides). But winners with 800-999 bags try 3.3 times a game at 6% success and
  still win: the endgame dance delays decided games, it does not flip them. Not pursued.
  Idle time (scripts/idle.py): 1-2% of alive turns (recall feints count as channels); idling is not the gap.
- 06:22 (real time; stamps above from ~05:40 ran ~10 min ahead) **sel-pursue** hold: **49.1% (47.7-50.5)** of 5,120;
  OOF 337 vs 315. Pooled screen + dev + hold: ~50.4% of 25,600 (+0.4 +- 0.6): level. The labour-from-caution line has
  no proven gain either; every local perturbation of this bot reads flat.
- 06:25 Other economy checks (mirror): gold-only clusters 58% used (util2.py); farm target switches 50 per
  champion-game of 547 farm turns, A-B-A flips 9 (churn.py); completed recalls 6-15 per 1,000 champion-rounds
  (health.py; ~28 a team-game, ~20 rounds each, 45% travel recalls), camp damage taken 1-10k per 1,000 rounds by
  type, Willow heals 15.6k per 1,000 rounds. Prism hoarding (keeps_gems until the bag wins) is the regime; every
  earlier Prism-banking variant lost 3-17 points (EXPERIMENTS), so not reopened.
- 06:22 sel-window smoke 49.6% (256), no failures; frozen as `sel-window-s1` and screening on `screen` while the
  implementer finishes its audit.
- 06:28 **sel-window** returned (patches/sel-window.diff; economy/farm.cc only; base sel-pursue): weight
  1 - f (1 - home) with f the share of enemy bodies present during our stay (dead bodies back by respawn_earliest +
  enemy_steps(g) - attack range, dash-aware), applied to the priced clear (stay_fit), the Monolith line, not to the
  from-altar cycle; caches keyed by the dead mask; all-alive path bit-identical. Smoke 49.6% (256). Acts modestly:
  enemy-half captures with 1+ enemy dead 21.8 vs 19.4 gems / 100 team-rounds, own half 54.5 vs 57.0.
  **Screen (sel-window-s1 = sel-window): 51.3% (50.4-52.3)** of 10,240; OOF 656 vs 723 (pursue alone 51.0 there).
  Dev launched.
- 06:33 **sel-window2** implementer launched (from sel-window): the denial term. In a window an enemy-half group is
  contested (the enemy takes it when back, while our own-half groups wait for us), so its weight rises from its static
  discount toward params::mid_exposure (the tuned contested-group value) as the present share falls.
- Prism bags W vs L (early.py): r50 27/25, r100 58/52, r150 98/82, r200 142/113, r300 242/169: the opening is level,
  Prisms diverge in the midgame (compounding Focus and kills).
- 06:42 **sel-window** dev: **50.8% (49.8-51.7)** of 10,240; OOF 653 vs 1,111. Pooled screen + dev 51.05% of 20,480 vs
  pursue's 50.7 on the same suites: +0.35 from the window, ~+1 over chy-ref in all. Small but in line.
- Killers (killshare.py, mirror): kills + assists a champion-game Prism 5.4, Ryth 5.6, Vesper 3.7, Cassi 2.8: threat
  is spread over bodies, so equal body shares in the window are a fair model.
- 06:50 Labour accounting (debug mirror, 400 games; holds.py, wasted4.py). Holds: 8.1% of alive time, 1.02-1.04
  holders and ~6 rounds a capture (the rules' minimum): lean. Farm steps by the target's fate (same target joined
  across interruptions within 40 rounds, capture within 30): our own capture 33.7%, an ally's that we helped clear
  20.3%, an ally's without our help 7.3%, the enemy's without our help 13.0%, the enemy's after we softened it 3.0%,
  nobody's (abandoned) 22.7%. Of the walks to enemy-taken groups, 32% of the turns come after the enemy's clear/hold
  began, 83% of those from beyond 8 tiles (unseen): mostly races lost before anyone could know.
- 06:58 Abandoned farm walks (abandon3.py): 67% end in a switch to another farm target, 12% in a retreat. Of
  the switch-ended ones the target was truly alive in 61%, respawning in 38%; 69% of switches happen beyond 8
  tiles. The respawning ones had been captured, before we set out, by the enemy (~2.7% of all farm steps), an ally
  (~2.4%; captures teammates were not told of) or ourselves. Each leak is a few percent; none dominates. The earlier
  programme measured the same (14 returns a game to groups believed alive; idea "post teammates' clears", unbuilt).
- 06:50 (real) Tanking (tank.py, 400 mirror games): ranged bodies take 12.9k camp damage a game, 22% of it with a
  melee ally also within that camp's range (melee 19.8k, 28%): ~3 heal trips a game, ~2% of team time. Small.
- 06:55 (real) Races (wasted6.py): on farm turns with an enemy in sight, the nearest visible enemy is nearer our
  target than we are in 76% of turns toward groups the enemy then took (57.5k vs 17.9k), 17% toward our own captures
  (17.4k vs 86.1k). Conversion: we capture ~22% of targets a visible enemy is nearer, ~67% when we are nearer. The farm
  skips only groups the enemy already holds. **sel-race** implementer launched (from sel-window): value x
  race_lost_share = 0.22/0.67 = 0.33 when an alive visible enemy is strictly nearer and we are not yet working it.
- 06:49 sel-window2 smoke 50.0% (256), no failures; frozen as sel-window2-s1, screening.
- 06:59 **sel-window2** returned (patches/sel-window2.diff; farm.cc): weight = threat_weight + (1 - f) x denial, denial
  = mid_exposure / exposure - 1 off our half; bounds lifted where weights exceed 1 (side_bound, denial_bounds).
  Smoke 50.0% (256). Barely acts: enemy-half captures with 1+ dead 21.9 vs sel-window's 21.8 (chy-ref ~19.5); the
  window's stay timing already excludes most far enemy-half groups (dead bodies return within ~60 rounds + walk).
  sel-window2-s1 (identical) screening.
- 07:05 Ally races (allyrace.py, true positions): an ally is nearer our target in 83% of turns of walks to an ally's
  capture we did not help (96k vs 19k), 35% of walks to our own captures, 48% of helped ones. Duplicate walks are
  mostly toward groups a nearer ally takes alone (claims / crew-join anticipation); not built.
- 07:13 **sel-window2** screen: **51.4% (50.5-52.4)** of 10,240; OOF 685 vs 743. = sel-window (51.3): the denial term
  changes ~nothing. Not taken further; sel-window stays the line.
- 07:14 **sel-race** returned (patches/sel-race.diff; params race_lost_share 0.33, farm.cc racers mask and
  race_lost(); scales gems/gold after stay_scale, so every valuation path and the Prism 'L' carry see it; exempt when
  already working the group, Monoliths). Smoke 49.6% (256), OOF 10 vs 14. Screening as sel-race-s1.
- 07:20 Unseen races (tracked.py): turns with no enemy in sight but one seen within 10 rounds that would be nearer
  (its distance then + half the rounds since): walks to enemy-taken groups 15.5k (of 128k unseen), own captures
  5.5k, ally-helped 2.2k, abandoned 13.0k: same ~21% conversion as the visible case, a quarter of its volume.
- 07:22 Race conversion by margin m (tiles the nearest visible enemy is nearer our target; margin.py): m<=0 58% ours
  (15% enemy's), m 1-2 28% (42%), 3-5 16% (54%), 6+ 11% (54%). Relative to m<=0: 0.48 / 0.28 / 0.19, fit by
  1 / (1 + m/2). The flat 0.33 is the pooled value.
- 07:21 **sel-race2** implementer launched (from sel-race): graded race price 1/(1 + m/2) in place of the flat 0.33.
- 07:25 **sel-race** screen killed at 4,374 games: **44.3%** vs 51.3% for its base sel-window on the same games
  (-7 points). sel-race2 (graded 1/(1+m/2)) stopped before playing (patches/sel-race2.diff kept, never measured).
  Lesson: the measured 22% conversion counts only our captures; walking at a group a visible enemy is nearer is
  not waste: our presence contests (a contested capture resets), denies and draws fights. Yielding contested groups
  is caution by another name and loses heavily, as the tuned mid_exposure premium (1.36 > 1) already said.
  Next probe, the other sign: **sel-contest** prices such groups as contested (x mid_exposure).
- 07:27 sel-window on hold launched.
- 07:36 sel-race sides (300 of its screen games, sidecmp.py): captures own 724 vs 737, mid 93 vs 104, enemy half 108
  vs 133; deaths 9 vs 7 a game, bag gems lost 179 vs 135; tributed 703 vs 807. Yielding gives up captures everywhere
  and costs deaths: the enemy farms and grows freely and wins the fights that follow.
- 07:37 **sel-window** hold: **49.5% (48.1-50.9)** of 5,120 (pursue alone 49.1 there). Pooled screen + dev + hold:
  ~50.75% of 25,600 (+0.75 +- 0.6). Best so far, but barely above level.
- 07:42 sel-contest smoke 51.6% (256); frozen as sel-contest-s1, screening. sel-window on x2 launched (final fresh
  confirmation for the fallback finalist).
- 07:43 sel-window sides (400 of its dev games, 52.5% in the sample): captures own 777 vs 765, mid 101 vs 104,
  enemy half 113 vs 107; deaths 7 vs 7, bag lost 176 vs 168; tributed 806 vs 769. The gain is capture volume.
- 07:46 **sel-contest** returned (patches/sel-contest.diff): a group an alive visible enemy is strictly nearer (and we
  do not work yet) is priced at mid_exposure (x mid_exposure / exposure(g)); per-group prunes lifted for contested
  groups, multi-group prunes widened while an enemy is in sight. Smoke 51.6% (256), OOF 20 vs 11.
- 07:53 **sel-reach** implementer launched (from sel-window): the window's absence test extended to alive enemies
  with a known position: absent if the rules' earliest arrival (walk, dash, crystal, recall + walk from spawn) from
  its current or last-fixed position is after our stay ends. Boldness only where safety is provable.
- 07:54 **sel-window** x2: **50.2% (49.2-51.2)** of 10,240. sel-window over all four suites (screen 51.3, dev 50.8,
  hold 49.5, x2 50.2): **~50.6% of 35,840 (+0.6 +- 0.5)**.
- 07:54 **sel-contest** screen: **50.8% (49.8-51.8)** of 10,240 vs its base sel-window's 51.3 on the same suite: level
  to slightly down. With sel-race (-7) this brackets the farm's pricing of groups a visible enemy goes for: yielding
  loses heavily, an extra contest premium gains nothing; the current (static mid_exposure) sits at the optimum.

## Summary so far (08:05)
| candidate | idea | screen | dev | hold | x2 |
|---|---|---|---|---|---|
| sel-conv | conveyor: allies hand groups to the Prism | 50.5 | 49.1 | | |
| sel-conv2 | + Prism-side acceptance of imminent clears | 50.4 | | | |
| sel-twin | C&I farm and fight as one unit | | 46.4 | | |
| sel-intel | shared enemy-Prism sightings, duel-priced farm | (1k study 47.8) | | | |
| sel-pack | retreat from packs one walk sooner | 49.1 | | | |
| sel-ps1 / ps0 / wil / ps1w | pursuit horizon 1 / 0, no Willow exposure retreat | 50.6 / 48.8 / 49.7 / 50.8 | | | |
| sel-pursue | walkers join a pursued stand only if they can close by our next turn | 51.0 | 50.4 | 49.1 | |
| sel-hunt | dominant Prism hunts the weak one | inert (0.45 hunt turns a game) | | | |
| **sel-window** | pursue + enemy-ground discount scaled by the enemy share present during our stay | **51.3** | **50.8** | **49.5** | **50.2** |
| sel-window2 | + denial premium in windows | 51.4 | | | |
| sel-race | yield groups a visible enemy is nearer (x0.33) | 44.3 (4.4k, killed) | | | |
| sel-contest | price such groups as contested (x mid_exposure) | 50.8 | | | |
- 08:07 sel-reach smoke 48.4% (256), OOF 30 vs 14; frozen as sel-reach-s1 (pre-audit-report), screening.
- 08:19 **sel-reach** screen: **51.3% (50.4-52.3)** of 10,240; paired with sel-window on the same 10,240: +0.0. OOF 768
  vs 727. Provable-reach absence of seen enemies adds nothing on top of death windows: territory is saturated.
- Willow (willow.py, debug mirror): 47% support ('h'), 27.6% farm, 6.6% retreat. Willow-as-farmer arms lost before
  (EXPERIMENTS: farmer 44.8, carry 44-48): not reopened.
- 08:23 sel-reach returned (patches/sel-reach.diff): the screened s1 predates two conservative audit fixes (spawn routes
  bounded by Chebyshev, respawn round capped); with s1 level with sel-window, not re-screened.
- 08:28 Prism last-hit check (lasthit.py, 1,027 mirror games, both teams): kill gems 306 a game; the Prism lands
  225; allies land 47 with the Prism assisting, 25 without. Routing last hits to the Prism could move ~23 gems a
  team-game: too small to build. Fresh suite `maps/suites/mac13s/x3` (seeds 147242-147261, ladder-v2, 5,120 maps);
  sel-window on x3 launched as a further fresh confirmation.
- 08:35 bots/charybdis on the branch = sel-window (0bf822709). Stress suite `maps/suites/mac13s/var` (seeds
  147262-147271, --mix varied) generating for a robustness read of sel-window.
- 08:36 **sel-owner** implementer launched (from sel-window): mutual non-crew claims (we and an ally both claim g, each
  pricing it as its own solo capture, the "unless we claimed it first" rule) get one owner, the claimer nearest g
  (ties: lower index); the other becomes crew through the existing claimed branch. Targets the 7.3% duplicate walks.
- (real 08:35; the two stamps above ran ~5 min ahead) **sel-window** x3: **50.4% (49.4-51.3)** of 10,240; OOF 561 vs
  559. Over five fresh suites (screen 51.3, dev 50.8, hold 49.5, x2 50.2, x3 50.4): **~50.5% of 46,080 (+0.5 +- 0.46)**.
  sel-window on the varied stress suite (2,560 maps) launched.
- **sel-window** on the varied stress suite: **50.2% (48.8-51.5)** of 5,120; OOF 653 vs 715. No robustness loss off
  the ladder-like distribution.
- 08:50 Programme closed early (hand-back enforced). **sel-owner** (mutual-claim owner rule) was mid-smoke: built and
  audited by its implementer but never measured; patches/sel-owner.diff saved as is. Open lead, not a result.
  Final: bots/charybdis = sel-window.
- sel-owner hand-back: farm.cc `yielded` (owner = claimer nearer by steps, slack and turn order resolving doubt towards
  keeping; exempt Monoliths, our proposals, the Prism carry, a group we work); readers taken(), claimed_bits, the 'J'
  pick (crew re-derived each turn), heal_before_waking. Pre-audit debug smoke 51.2% (256): mutual claims 10.5% of
  farm turns, yields on 12.9% of those. Post-audit build and release smoke killed unfinished: unverified. Open audit
  item F4: crew status is not posted (a priority-payload crew bit would fix it).
