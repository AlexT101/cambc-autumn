# HECATE: macro refactor of charybdis (2026-11-13, 02:00-10:00 UTC)

Reference `bots/variants/chy-ref` (frozen charybdis). Every A/B: `tools/ab.py variants/CAND variants/chy-ref
--no-test-draft --fuel 200000`, fast runner, release builds unless noted. Suites: `maps/suites/mac13/dev` (5,120
fresh ladder-v2 maps, 10,240 games), `maps/suites/mac13/hold` (2,560 maps), `maps/suites/mac13/study` (512 symlinks,
every 10th dev map; study only, never for decisions). Patches of each candidate against chy-ref: `patches/`.

## Study

Mirror (`mac13-hecate-mir`, 512 distinct debug games on study; scripts in `scripts/`):
- Deaths (pair bodies counted each): 12.7 champion deaths a game. The victim saw its killer in the 10 rounds before in
  78% (mostly 10+ rounds before), only an ally saw it in 17%, nobody 5%: shared sightings could touch at most ~17% of
  deaths (11% of gems lost). Outnumbered within 8 (enemies > allies+1) in 33%.
- Victims: Cassi/Issac pair 1,701 pair deaths in 512 games (3.3 a game, the largest class), Prism 671, Willow 616.
  Killers: Prism 54%, Vesper 23%.
- Prism-on-Prism kills 1.0 a game, 205 with 100+ bags: killer/victim Focus median 1.38; the victim had cast on the
  killer in the 8 rounds before in most (101 stun, 73 AoE): these are exchanges the bigger Prism wins, not camp-cast
  blunders. Approach is visible: distance closes 10 -> 4 over ~10 rounds.
- Captures 116 a game (both teams), 1,886 gems, 9,494 gold; steals (capturer != clearer team) 2.8 a game. Prism holds
  828 capture gems a game (both teams), Vesper 323, Issac 180, Cassi 149.
- Winner/loser curves: r300 score 113/98, team bag 258/197, Prism bag 198/144, gold 1,753/1,537; r600 324/237,
  451/238, 390/186, 4,168/3,406. Median game 759 rounds.
- Recalls: 45 completed a team-game; 49% start at 90%+ health, 53% carry gems; recall start -> next camp work 25
  rounds mean (19 median): 23% of all body-rounds are recall cycles.
- Bushes: 4.8% of tiles, 30% of groups have one within 3. Champions stand in bushes ~5.5% of alive rounds (no
  preference), but killers are in a bush at the kill 14.8% of the time; one-sided bush kills 721 (killer in bush) vs
  386 (victim in bush).

## Candidates

| Candidate | Idea | A/B name | Suite | Games | Win % (95% CI) | Verdict |
|---|---|---|---|---|---|---|
| h-noplan | play ignores the draft's opening plan | mac13-hecate-noplan | dev | 10,240 | 48.8 (47.8-49.8) | probe: the plan is worth ~+1.2 |
| h-plan3 | opening plan weight 1.5 -> 3 | mac13-hecate-plan3 | dev | 10,240 | 48.8 (47.8-49.7) | probe: following it harder loses as much |
| h-vision (first) | enemy-sighting record above the camp record | mac13-hecate-vision-pre | dev | 10,240 | 44.9 (44.0-45.9) | lost: crowded the camp record out |
| h-ref-nocamp | chy-ref without its camp record (ablation) | mac13-hecate-hv-refnocamp | dev | 10,240 | 45.1 (44.1-46.1) | the camp record is worth ~5 points |
| h-vision (late) | sighting record only in bits left after claims/bag/camp/ally (fits 22% of games) | mac13-hecate-hv-late | dev | 10,240 | 49.8 (48.8-50.8) | level: sightings are not a lever (also EXPERIMENTS: CHANGES 236, river, cm-sight) |
| h-mono | Monolith crew ops (ICARUS port) with non-Prism holders who bank | mac13-hecate-mono | dev | 10,240 | 49.9 (48.9-50.8); Monolith maps 49.5 of 3,036 | level: captures barely rise (145 vs 138 in 1,024 debug games), holders bank fine |
| h-terr | home_ground's exponent x presence of the enemy's live force (dead enemies not back in time) | mac13-hecate-terr-s1, -terr-s1b (audited) | scr1 | 10,240 / 10,240 | 50.2 (49.3-51.2) / 50.2 (49.3-51.2) | level |
| h-prey | busy enemies (clearing an awake group, channelling) are prey on their own ground | mac13-hecate-prey-s1, -prey-s1b (audited) | scr1 | 10,240 / 10,240 | 49.9 (48.9-50.9) / 50.0 (49.0-51.0) | level |
| h-campnet | camp record generalised: respawning / cleared-unheld / enemy-holding | mac13-hecate-campnet-s1, h-campnet-dev | scr1 / dev | 10,240 / 10,240 | 50.3 (49.3-51.2) / 49.0 (48.1-50.0) | level: the existing record carries the value; reports flow (48 cleared, 12 enemy-hold posts a game) but picks barely change (Prism 'L' 0.17 a game) |
| h-deny | contest enemy holds (gold groups too) before small-bag banking, gated by the stand verdict | mac13-hecate-deny-s1 | scr1 | 10,240 | 49.6 (48.6-50.6) | level: the gate refuses most chances (guarded holds) |
| h-stale | unseen enemy-side groups priced on an enemy farm cycle + a visible enemy's race priced (wait_priced off) | mac13-hecate-stale-s2 | scr2 | 10,240 | 49.9 (48.9-50.9) | level: picks change ~14 turns a game; abandonment 27.2% vs 27.9% |
| h-refuge | retreat to allies the pursuer can't see (refuge goals) + allies receive pursuers | mac13-hecate-refuge-s2 | scr2 | 10,240 | 50.2 (49.3-51.2) | level; OOF 686 vs 538 |
| h-mw0 / h-mw1 / h-mw4 | max_wait 2 -> 0 / 1 / 4 (probes) | mac13-hecate-mwN-s2 | scr2 | 10,240 each | 49.6 / 50.0 / 49.8 | flat: the -11 of wait_priced comes from long camps, not the cliff's place |
| h-pack | all seven parts merged (atlas, campnet, terr, prey, deny, refuge, stale), switch-identical to chy-ref when off | mac13-hecate-pack-s2 | scr2 | 10,240 | 49.4 (48.4-50.4) | loses ~1.7 to h-atlas alone on the same maps (51.1); OOF 1082 vs 490 |
| h-ab | h-atlas + BOREAS b-duel (Prism burst lethality in guard/retreat) | mac13-hecate-ab-s3 | scr3 | 10,240 | 50.3 (49.3-51.2) | = h-atlas on the same maps (50.4): adds nothing |
| h-race | leave when the escape plan from next turn's tile is no longer clean (pursuit race); Prism-only switch | agent study reads | study (debug) | 1,024 each | 44.3 / Prism only 44.0 / dry 51.2 | lost: 2 captures and 50 capture gems a game below chy-ref, no deaths saved |
| h-atlasf | h-atlas with behaviour-identical fuel cuts (chase_trade memo, press filter order) | bench identity 16/16 + 52/52; mac13-hecate-atlasf-hold, -atlasf-dev | hold / dev | 5,120 / 10,240 | 50.6 (49.2-52.0) / 50.6 (49.7-51.6) | 0.3% fewer fuel on 100k+ turns; h-atlas's extra OOF is shared fight code run on more fight turns, not its own checks |
| h-keep / h-keepp | a retreat turn keeps the claim (and the Prism's carry claim) unless sieging, healing or banking; all champions / Prism only (on h-atlasf) | mac13-hecate-keep-s4, -keepp-s4 | scr4 | 10,240 each | 47.9 (47.0-48.9) / 50.1 (49.1-51.1) | lost / = h-atlas (50.3 on scr4): dropping the claim on retreat is right |
| h-dt | on h-atlas: worst-case stunner choice, two enemy turns summed, worst slot assignment before ours in lethal() | mac13-hecate-dt-s4, -dt-hold | scr4 / hold | 10,240 / 5,120 | 50.3 (49.3-51.2) / 50.8 (49.5-52.2) | = h-atlas (50.3 / 50.4 on the same maps); OOF 1,134 vs 603 |
| h-atlas | ATLAS remainder (press on disarmed enemies, lethal fixes 3/5) + 4 audit fixes | mac13-hecate-atlas, -atlas-hx, -atlas-s2 | dev / hold+x1 / scr2 / scr3 / scr4 | 10,240 / 15,360 / 10,240 / 10,240 / 10,240 | 50.7 (49.8-51.7) / 50.5 (49.7-51.2) / 51.1 (50.1-52.0) / 50.4 (49.4-51.3) / 50.3 (49.4-51.3) | small gain (+0.6 over 25.6k); base layer |

## Log

### 02:15 UTC
- Read brief, rules, prior macro programme (8 orchestrators, all level; ATLAS +1.8 from bag-loss model fixes).
- Architecture map (Explore agent): farm value = rate(worth, trip+clear+capture+trips_home) with home_ground side
  discount; **no enemy-danger term in farm choice**; unseen enemies vanish from safety after track_horizon 3 rounds or
  when `possible` is large (credible_weight 0.5); **no enemy sightings in comms** (8 bytes = claims, bag, camp respawn,
  ally pos). Coordination = claims + crews + leave-for-Prism funnel.
- Overseer: in a mirror, removing a shared inefficiency pays both ways; look for capabilities/valuations the ref lacks
  (asymmetric). Read fixed 10k blocks, not tight SPRT.
- Mirror study: `mac13-hecate-mir` (chy-mir = copy of chy-ref, debug, study 512 maps, 1,024 games, 2.9 min wall).

### 02:25 UTC
- Wave 1 launched: `h-atlas` (port ATLAS's remaining press + retreat fixes, +0.5-1 at 2x fuel in its programme) and
  two planning probes `h-noplan` (play ignores the draft's opening plan) / `h-plan3` (plan weight 1.5 -> 3): is team
  planning a lever in the mirror? If yes, the big candidate is a rolling in-game team farm planner (the open-plan
  solver extended to live state); the opening plan alone went +14 live when it shipped (CHANGES 479/487).

### 02:35 UTC
- A 10,240-game release A/B takes ~0.6 min wall now: A/Bs are free, implementation is the bottleneck.
- Planning probes: the opening plan is worth +1.2 in the mirror, and weight 1.5 is its optimum from both sides
  (draftfarm 2026-11-08 found the same: the more a plan is followed, the more it loses). A rolling in-game planner is
  not a promising big bet: dropped.
- Launched `h-vision` (team vision: an enemy-sighting record in the 8 bytes, merged by `World::note_sighting`).

### 02:50 UTC
- h-atlas: +0.6 over 25.6k (dev 50.7, hold 50.4, x1 50.5). As ATLAS found: a model fix, small. Kept as a possible
  base layer. Fresh suite `maps/suites/mac13/x1` (seeds 144200-144219, 5,120 maps) generated.
- Launched `h-mono` (Monolith crew ops with non-Prism holders who bank; brief in `briefs/h-mono.md`).

### 03:05 UTC
- `h-vision` first build (sighting record in comms, merged via note_sighting): **44.9% of 10,240** dev. Replays (1,000
  games): more kills (5.84 vs 4.96), fewer deaths (5.28 vs 6.14), fewer gems lost (121 vs 133), yet captures -3%,
  tributed 723 vs 778, bigger tribute attempts (4,160 vs 3,395 gems started) and more carried at the end: the fights
  improve but conversion and farm drop. The implementer's ablations: sightings posted but not applied
  (`hv-noapply`) 46.7%, applied but not to safety (`hv-nosafe`) 46.4%: most of the loss is not the sightings'
  use but the layout change itself (camp/ally records displaced, or a bug). Under investigation.

### 03:20 UTC: farm waste and the value of shared camp knowledge
- Trips (debug D lines of the mirror, `scripts/trips.py`): 60% of turns are farm-branch; 28% of farm turns are in
  streaks towards a group the champion does not work within 40 rounds (11% in streaks of 11+ turns); ~22 target
  switches per body a game, 13% of them A-B-A within 30 rounds. Of the abandoned turns, 15% end with the enemy
  capturing the group, 6% with an ally capturing it; ~40% were walks to a group respawning throughout.
- EXPERIMENTS ("Distress beacon"): replacing the comms camp record cost ~6 points: shared camp knowledge is one of
  the strongest levers in the bot. That explains most of h-vision's loss (the sight record crowded the camp record
  out on most maps). New candidate `h-campnet` (brief `briefs/h-campnet.md`): generalise the camp record to the
  camp-state corrections the team needs (respawning as today, cleared-unheld, enemy-holding), which also gives the
  Prism funnel the distant clears it never saw (boreas b-col's diagnosis).

### 03:25 UTC
- h-vision final report: sightings accurate (99.98% in cell); the loss was the layout. With the sight record placed
  last it fits only 22% of games and reads level (49.8); posting-but-not-applying already cost 3.3 (the layout), and
  applying cost ~1.8 more when it always fit. Information about enemies is not a lever here; information about
  camps is (~5 points for one record).
- Launched `h-campnet`. h-mono dev running (box load ~240 from other programmes).

### 03:35 UTC
- h-mono level (49.9; Monolith maps 49.5 of 3,036 games). The holder rule works (non-Prism shares mostly banked)
  but the team takes Monoliths hardly more than the reference: the op's start rules bind, not the holder. Dropped.
- Overseer: screen on fresh suites of my own seeds; keep dev and hold for finalists (dev is now partly selected:
  ~8 reads). Build coherent packages around exploiting the enemy's behaviour, then ablate parts.
- Screening suite `maps/suites/mac13/scr1` (seeds 144300-144319, 5,120 maps) generating.
- Package taking shape, "punish the blind farmer": the reference farms blind to danger beyond sight, holds captures
  standing still, leaves cleared gem groups lying for its Prism, and discounts our side statically. Parts:
  (a) h-campnet (team camp picture: respawning / cleared-unheld / enemy-holding), (b) h-prey (busy enemies on their
  own ground are prey), (c) h-terr (territory discount follows the enemy's live force), then (d) contest/steal
  enemy-held captures reported by teammates. Probes (b), (c) launched.

### 03:40 UTC: denial pool (mirror, `scripts/deny.py`)
- Per game (both teams), captures with an opposing champion within 2 / 4 / 6 tiles of the group's tiles in the 6
  rounds before payout: 2.9 / 9.6 / 18.9, worth 95 / 243 / 391 gems and 351 / 967 / 1,672 gold (of 1,886 gems and
  9,494 gold captured). ~13-20% of the economy is captured within reach of an enemy, yet contests are ~0.5 a game.
  The holder is the Prism in a third of the within-4 cases. Brief `briefs/h-deny.md` (contest enemy holds of gold
  groups too, before small-bag banking, gated by the stand trade).
- `scripts/deny2.py` (mirror debug D lines): for enemy captures with one of ours within 4 tiles in the last 6
  rounds (9.6 a game), our nearest champion was farming 51%, retreating 23%, contesting 13%, chasing 5%, banking 4%;
  it carried gems 37% of the time (20+ in 18%); it was Issac 19%, Cassi 17%, Vesper 17%, Prism 12%. So the farm
  turns (contest_capture's conditions failed: gold-only group, steps > hold left, or vision+2) are the target.

### 03:55 UTC
- h-campnet 50.3 on scr1: more camp states are level. The pattern of every programme holds: removing a load-bearing
  capability loses big (camp record -5, crews ~-20, chase -6, Prism trips -17), adding refinements reads level.

### 04:10 UTC
- h-campnet final (agent's dev read 49.0, my scr1 50.3): the information flows (per game 78 respawn, 48 cleared,
  12 enemy-hold posts; farm skips 34 reported enemy holds) but decisions barely change and nothing is gained.
- Willow uses her heal on 54% of its cooldowns (mean heal 249).
- Launched `h-deny` and a study of farm-trip abandonment (`briefs/study-switch.md`). Re-screening the audited
  h-terr / h-prey on scr1 (`terr-s1b`, `prey-s1b`).

### 04:20 UTC: tribute war and Prism duels (mirror, `scripts/tribwar.py`, `winatt.py`, `flip.py`, `pduel3.py`)
- h-terr / h-prey audited re-screens: 50.2 / 50.0 on scr1. Both level.
- Big tributes (150+ gems): 7.1 starts a game, 1.2 complete; cancels stun 2.6, manual 2.2, lock 1.1 (3,000 gems of
  stun-cancelled channels a game). Median cancelled bag ~976 gems, channel ~67 turns; 90% are the eventual winner's.
  Completion by nearest enemy at the start: within 9 tiles 7%, 9-16 40%, 17+ 74%.
- The winner made a winning attempt (score + bag >= 1000) in 425 of 512 games; median 20 rounds to the end, mean 123.
  The eventual loser had made one in 35 games (16 lost the carrier to the enemy, 17 the race/round limit).
- Prior programmes worked this ground thoroughly (delphi endguard/stunsafe, calypso pr-nowin/tw/hold, EXPERIMENTS
  "Long channel fixes C1-C4", interrupt/deny): all level. Not reopened.
- Prism-on-Prism kills of 50+ bags where the killer had >1.1x the victim's Focus (154 of 226): in the 30 rounds before,
  the victim farmed on in 30% of its turns at 5-6 tiles and 44% at 7-8; 974 of 1,260 farm turns at 5-11 tiles had the
  killer unseen. ATLAS (lethal fixes, in chy-ref) covered the visible-cast model; the unseen stalker is the gap.

### 04:37 UTC: why farm trips are abandoned (study-switch, trace copy `h-trace`, 1,024 debug games; `scripts/switch.py`, `logs/switch-study.txt`)
- 114,563 abandoning switches (of 257,840; the rest follow work on the old group), 804,830 abandoned turns. Causes
  (switch % / turn %): belief wrong 19.3 / 9.7; ally took or claims it 18.9 / 7.6; enemy took it or is near 13.0 / 34.1
  (mostly retreats on meeting an enemy, group kept); value flicker < 20% only 2.7 / 2.2; own situation 8.6 / 20.5;
  other 37.5 / 22.0 (incl. the max_wait cliff: a respawning group appears when its wait comes within 2, 8.2% of turns).
- Predictor at a trip's start: a group believed alive on the enemy side and unseen for 100+ rounds is abandoned 79.5%
  (13% for own-side groups seen < 100 rounds ago); 16.6% of all abandoned turns; 62% were respawning or cleared on
  arrival; `World::update_camp` keeps unseen groups alive forever and nothing infers enemy captures. An enemy in sight
  nearer the group: 61% abandoned (24.5% with none in sight).
- Launched `h-stale` (brief `briefs/h-stale.md`): unseen enemy-side groups priced on an enemy farm cycle (expected
  respawn wait respawn^2 / 2T, T = enemy's walk + clear + capture + respawn), the max_wait cliff priced as wait in the
  rate, and a visible enemy's race to a group priced; each part behind a switch for ablation.
- h-deny final: the stand gate refuses most contests (72% stand lost, mostly 2-3+ enemies guarding); it starts fewer
  contests than chy-ref (1.8 vs 4.2 a game; 0.23 holds reset). Screening on scr1 (`deny-s1`).
- Launched `h-refuge` (brief `briefs/h-refuge.md`): retreat to allies the pursuer cannot see, and allies receive
  the pursuer (the reference prices its chase with the allies it sees).
- 04:38 h-deny on scr1: 49.6 (48.6-50.6). Level, as the counts predicted.
- 04:50 Fresh screening suite `maps/suites/mac13/scr2` (seeds 144320-144339, 5,120 maps, ladder-v2). scr1 has had 6 reads.
- 04:58 h-stale agent's study reads (1,024 debug games each, noisy): all three parts 39.3; without wait_priced 51.7;
  without unseen_cycle 39.4; without enemy_race 40.6. Pricing a respawn wait smoothly instead of the max_wait = 2 cliff
  costs ~11 points: the cliff is load-bearing (it keeps champions off groups they would stand idle at; the rate's
  time term undervalues idle rounds against walking, or allies pile onto the same respawn). Told the agent to ship
  wait_priced off.

### 05:17 UTC
- h-stale final (wait_priced off): unseen_cycle changes the pick ~12 turns a game, enemy_race ~2; abandoned share of
  farm-streak turns 27.2% vs chy-ref 27.9%. scr2: 49.9 (48.9-50.9). Level. The 79.5%-abandoned stale trips are rarely
  the pick that the price flips: most are still the best guess (the next-best group is also far or also uncertain).
- h-refuge final (refuge goals 22.6 a game, median walk 3 vs 25 home; receptions ~0.9 + 2.7 aims a game): screening
  on scr2 (`refuge-s2`).
- Launched max_wait probes h-mw0 / h-mw1 / h-mw4 (the cliff is load-bearing; what is its gradient?).
- 05:19 h-refuge on scr2: 50.2 (49.3-51.2), OOF 686 vs 538. Level.
- Launched `h-pack` (brief `briefs/h-pack.md`): all seven parts (atlas, campnet, terr, prey, deny, refuge, stale)
  merged behind per-part switches, around the one theme (punish a reference that farms blind and prices fights by
  sight), to test the overseer's interaction point before ablating.
- 05:26 max_wait probes 0 / 1 / 4 on scr2: 49.6 / 50.0 / 49.8. Flat around 2.
- 05:36 h-pack smoke (agent, pre-audit) 49.2% of 256. h-atlas re-read on scr2 (`atlas-s2`) for the base layer.
- Side note (not used: protocol-specific, an overfit by the rules): a visible champion's priority is readable by the
  enemy, and chy-ref's low priority bits carry its claim, support intents and chase bit (comms::priority_payload), so a
  visible reference champion broadcasts its farm target.
- 05:38 h-atlas on scr2: 51.1 (50.1-52.0). Pooled dev + hold + x1 + scr2: ~50.7 of 35,840.
- Launched `study-bagloss` (brief `briefs/study-bagloss.md`): trace copy of h-atlas, classify its remaining bag losses
  by model gap (ATLAS's method, the only one with gains in this mirror), recommend the largest fixable one.

### 05:55 UTC
- h-pack (seven parts, one theme) on scr2: 49.4 (48.4-50.4), against h-atlas alone 51.1 on the same maps. The level
  parts do not combine into a gain; together they cost ~1.7 (and double out-of-fuel turns, 1,082 vs 490). The
  interaction the overseer hoped for is not there for these parts. Not ablated: the merge is below its best part.
- Fresh suite `maps/suites/mac13/scr3` (seeds 144340-144359, 5,120 maps) for final confirmations.
- Launched `h-ab` = h-atlas + BOREAS's b-duel (Prism burst lethality in guard and retreat; +0.7 over 16,640 games in
  BOREAS against an older charybdis, never merged to main), porting only what ATLAS's fix 3 does not already model.
- 06:32 h-ab built (b-duel's burst lethality for our Prism ported onto h-atlas; lethal() adds the burst as its own
  bound, never summed with ATLAS's stun follow-up; burst-lethal tiles in work_guard/cover; burst-ranked retreat steps;
  fires: 0.09 guard turns, 0.7 ranked retreat steps a game; new lethal reads mostly from unseen Prisms). Screening
  h-ab and h-atlas together on scr3 (`ab-s3`, `atlas-s3`).
- 06:47 scr3: h-ab 50.3 (49.3-51.2), h-atlas 50.4 (49.4-51.3); OOF 854 / 827 vs ~520. b-duel adds nothing on top of
  ATLAS's fixes. h-atlas pooled over dev, hold, x1, scr2, scr3: ~50.6 of 46,080 (CI roughly +-0.45).
- Launched `h-atlasf`: a behaviour-identical fuel pass on h-atlas (its OOF turns are ~1.6x chy-ref's at 2x fuel).

### 06:55 UTC: where h-atlas still loses bags (study-bagloss, trace copy `h-atrace`, 1,024 debug games vs chy-ref)
- 6.1 deaths and 144 gems lost a game (Prism 0.59 deaths, 95 gems; first Prism death 0.29, 78 gems).
- Retreats whose last turn was lethal: 2.6 deaths, 57 gems a game (games with them won 31%). Retreats begun safe die
  5.7% with the nearest enemy within 4 at the start against 1.2% with a gap of 5+ (stand lost by gap 1..7: 12, 5.6,
  4.3, 2.7, 1.7, 1.0, 0.7%); dying ones are 5+ turn walks, half killed by another enemy. At equal speed the gap at the
  start is the gap of the whole walk; the trigger and retreat_step look one turn ahead.
- stop_game_ender held on a lethal tile: 0.73 deaths, 21 gems a game (Prism stoppers; those games won 4%).
- Unseen or untracked killers 36 gems (bush stuns, teammate-only sightings, 60+ rounds unseen: no information);
  model said safe with the killer visible 15 gems (two turns before ours, several attackers, one 3400.1 vs 3400 hp
  verdict).
- Launched `h-race` (brief `briefs/h-race.md`): on h-atlas, leave when the escape plan from next turn's tile is no
  longer clean (the pursuit race), Prism-only switch for ablation. Hard stop 08:45.
- 07:00 Fresh suite `maps/suites/mac13/scr4` (seeds 144360-144379, 5,120 maps) for the final confirmation.
- 07:31 h-atlas on scr4: 50.3 (49.4-51.3). Pooled over six suites: ~50.6 of 56,320 games.
- 07:37 h-race study reads (agent, 1,024 debug games): all champions 44.3-44.6, Prism only 44.0, trigger computed but
  not acted on ("dry") 51.2. Leaving on the pursuit race is caution, and caution loses here as in every programme
  (farm and position time). Told the agent to wrap up without tuning.
- Launched `h-dt` (brief `briefs/h-dt.md`): on h-atlas, the "said safe, killer visible" gaps (two enemy turns before
  ours, summed blows of several attackers, the edge comparison), the model-fix kind that has paid here.
- 07:45 h-race final: v2 17 triggers a game (Prism 5), retreats it starts almost never die, but deaths +0.4 and
  captures -2 a game against chy-ref; the dry copy (computes, never acts) 51.2: the acting is the cost. Its
  implementer's lead: a retreat turn drops `memory.claim` and the Prism's carry claim (act(): drop_carry_claim on
  Branch::retreat), withdrawing what allies plan around on every one-turn retreat.
- h-atlasf (fuel pass): identity holds on both bench sets; only ~0.3% saved on heavy turns. h-atlas's 1.6x OOF comes
  from more fight turns running the shared sims/escape plans (its own functions ~2% of an OOF episode).
- Launched `h-keep` / `h-keepp` (on h-atlasf): a retreat turn keeps the claim (all champions / Prism only), testing
  the claim-flicker lead; claims flicker on F-R-F trips and allies re-plan around them.
- 08:21 h-keep 47.9 / h-keepp 50.1 on scr4 (h-atlas 50.3 on the same maps). The claim drop on retreat is load-bearing
  for the non-Prism champions (a retreating champion's claim should free the group for allies); the claim-flicker
  hypothesis for h-race's loss is refuted.
- 08:25 h-atlasf on hold: 50.6 (49.2-52.0) (h-atlas 50.4 there). h-dt built (three lethal() gaps: the stunner
  choice skipped a two-turn killer behind a zero-damage Cassi stun; two enemy turns counted as the better one, never
  the sum; guessed slot assignment before ours; ~1 verdict change a game). Screening on scr4 and hold.
- 08:32 h-dt: scr4 50.3, hold 50.8 against h-atlas's 50.3 / 50.4 on the same maps. No measurable gain, nearly double
  the out-of-fuel turns. Not kept. Final candidate: h-atlasf (h-atlas's behaviour, a little less fuel); its own dev
  read running (`atlasf-dev`).
- 08:38 h-atlasf on dev: 50.6 (49.7-51.6) of 10,240 (h-atlas 50.7 there). Launched `atlasf-var`: h-atlasf on a
  `--mix varied` stress suite `maps/suites/mac13/var` (seeds 144380-144399, 5,120 maps), for robustness off the
  ladder mix.
- 08:42 h-atlasf on var (`--mix varied` stress maps): 50.2 (49.3-51.2) of 10,240, OOF turns 1,632 vs 1,349. Level
  off the ladder mix: no break on stress maps, no gain either. Two further fresh suites for a tighter final
  read: scr5 (seeds 144400-144419) running, scr6 (144420-144439) generating.
- 08:48 h-atlasf on scr5 50.3 (49.3-51.2), scr6 50.1 (49.1-51.0), 10,240 each (OOF 724/601, 777/623). h-atlasf pooled
  over hold, dev, var, scr5, scr6: 23,193 of 46,080 = 50.3 (49.9-50.8); on the two suites no earlier read touched,
  50.2. With h-atlas's 56k (same decisions: bench-identical), ~50.5 over ~102k games: a real but small gain.
- Launched `h-ender` (on h-atlasf): our Prism leaves a lethal stop_game_ender hold to an ally whose hard stop lands
  no later (the trace study's 0.73 deaths / 21 gems a game of Prism stoppers on lethal tiles). Hard stop 09:30.
- 08:53 h-atlasf on scr7 (seeds 144440-144459, 5,120 maps; h-ender's screening suite): 50.6 (49.7-51.6), OOF
  1,000 / 712. h-atlasf over six suites: 28,375 of 56,320 = 50.4 (49.97-50.8).
- 09:01 h-atlasf on scr8 (seeds 144460-144479; h-ender's confirmation suite): 50.2 (49.2-51.2), OOF 854 / 570.
  h-atlasf over seven suites (hold, dev, var, scr5-8): 33,516 of 66,560 = 50.35 (49.97-50.73).
- 09:02 Finish (called early by the harness's handback enforcement, before the planned 10:00). The h-ender agent was
  cut off mid-smoke: its patches are saved (`patches/h-ender*.diff`), it is unscreened and not kept. All mac13-hecate
  sessions and runs stopped; replay batches and extracts deleted.

## Conclusion
Final candidate: `bots/variants/h-atlasf`, copied into `bots/charybdis`. It makes the same decisions as h-atlas
(chy-ref + ATLAS's press on disarmed enemies, lethal fixes 3 and 5, 4 audit fixes; bench-identical) with fuel cuts.
h-atlasf: 50.35 (49.97-50.73) of 66,560 games over hold, dev, var, scr5-8; h-atlas: ~50.6 over 56k games. A real but
small gain, far from the 60% goal. The mirror is at a macro equilibrium: load-bearing subsystems lose big when
removed, caution and refinements read level or lose, and only model fixes where bags are lost have gained (~+0.5).
