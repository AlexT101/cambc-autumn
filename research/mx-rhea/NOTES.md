# RHEA: macro refactor of charybdis (2026-11-13)

## Status
- 17:40 UTC: FINAL (ended early by the user to save usage). Every candidate read level or losing against chy-ref;
  `bots/charybdis` = chy-ref (529). C7 `hunt` and C8 `urgency` were stopped mid-implementation (no results; their
  variant dirs may hold partial work). No normal-fuel read was run (no candidate to read).

Reference `bots/variants/chy-ref` (charybdis 529). Every A/B: candidate vs chy-ref, `--fuel 200000`, own drafts,
fast runner native. Suites: `maps/suites/mx/dev` (5,100 maps), `maps/suites/mx/hold` (5,100), my own:
`maps/suites/mx-rhea/study3` (61411000-02, 1,020 maps, analysis only), `study` (61411003-05, smokes/analysis),
`conf` (61411100-14, 5,100 maps, held-out confirmation).

## Log
- 14:20 Read brief, rules, prior programmes (macro-orchestrators-2026-11-11, mac13-*, overseer candidates).
  Priors: CASTOR's +5 came from pricing the Prism's gems consistently across every ally decision and from the
  Prism's shop/recall timing; non-Prism games stayed level. Soft coordination terms, packs, rallies, escorts all lost
  or read level (farm time is the binding resource). track_horizon (forget unseen enemies after 3 rounds) was tuned
  down repeatedly: remembering more with a uniform-weight `possible` made bots over-cautious.
- Code reading: enemy respawn timers (`respawn_earliest/latest`) are written, never read by a decision. home_ground
  (farm's side discount, share^1.89 by walk distances from both spawns) is static: it ignores where enemies are,
  whether they are dead, and what they are doing.
- 14:25-14:58 Mirror study (`mx-rhea-mirror`: chy-mirror vs chy-ref, study3, debug, 2,040 games = 1,020 distinct;
  extracted to `replays/ana-mirror`; scripts in `research/mx-rhea/scripts/`):
  - Deaths to champions (enemy_angle.py): the victim saw its killer within 1 round in 74% (W) / 83% (L); the team
    saw it within 1 round in 86% / 93%; unseen 31+ rounds 12% / 9%. Forgetting enemies after 3 rounds is not where
    deaths come from. L's Prism dies 654 times in 1,020 games, W's 21.
  - Capture gems a team-round by enemies dead (r<=600, deadshift.py): W 1.48 with none dead, 1.53 with some, 1.53
    with half+; L 1.24 / 1.22 / 1.10. Teams move their captures to mid / enemy side while enemies are dead (W own
    share 81% -> 53%) but produce no more: dead time is not converted.
  - Capture gems r<=500 by side (gold.py): W own 574k / mid 95k / enemy 74k, L 528k / 52k / 44k: of the W-L gap
    of 118k, 72k is mid and enemy-side groups.
  - Gold is spent (Prism holds ~150-260 at r300-500). Cassi / Issac / Willow earn ~65 / 70 / 17 gold by r300.
  - Endgame (endwin.py): a provably safe channel (every enemy's respawn + walk, or Chebyshev distance, longer than
    walk + channel) exists in 49% of W's winning-bag games but almost only once the game is already ending; L had one
    and lost in 15 of 1,020 games. Respawn-timed final tributes are a small lever on their own.
  - Time (macro_stats): walking 49%, camp 19%, still 7%, recall 6%, hold 5%; recall cycle ~27% of alive time.
    Recalls (recalls.py): Cassi and Issac each ~6 transport recalls a game at >=60% HP (RFKEEP: recall_to_farm),
    Issac 6 heal recalls; Prism ~10 shop recalls; ~20-30 rounds from arrival to the next camp hit.
- 14:45 Killers (killers.py, 1,020 games, both teams): the enemy Prism kills 66% of Cassi deaths (2.2 a game, both
  teams), 79% of Prism deaths, 60% of Issac, 59% of Willow, 66% of Ryth, 63% of Vesper; mostly by cast (its 1.5x Focus
  stun one-shots base-stat Cassi / Willow from range 4). Ambush test (ambush.py): of deaths to a Prism the victim saw
  at its turn start, the sighting began at 7-8 tiles in ~45-55% and lasted 4+ rounds in ~60%: victims watch the
  Prism come and still die (not ambushes). Holds (holds.py): holders hit a camp on ~0.1 of their ~4.5 hold rounds;
  15.5k pure gold-cluster captures (20 gold each) in 1,020 games.
- 14:50 Launched C1 `presence` implementer (brief `briefs/c1-presence.md`) and a read-only Prism-duel / hunt analyst.
- 15:05 Deaths by phase (death_phase.py, retreat_start.py): 39% of champion deaths come while the enemy holds a
  winning bag, 2,907 of them (28% of all) on branch E (stop a game-ender). Early/mid deaths: last branch R in ~70%,
  the retreat began with the killer at 3-6 tiles mostly, from F in 2,994 of ~4,500; full hp at R start in 1,171.
  Cassi's (4,5,6,7) walk-in deaths to a Prism are 79% E (endgame stops).
- 15:05 Analyst (Prism duel, scripts pd_*.py): 4.2 hunt episodes a game (stronger Prism S, Focus >= 1.2x and hp
  >= 60%, sees V at 5-9). Clean hunts (S not tributing, V not on E): V dies 13%, S closes only 33%; when S closes V
  dies 17% (ratio 1.2-2), 31% (2-3), 53% (3+), S dies < 1%. V's death rate by net bodies near V: 8% at -2, 13% at 0,
  26% at +2; V reaching its spawn: 2%. First Prism deaths (535): victim's team loses 92.5%; classes: weaker Prism
  met the stronger while farming 35% (had seen it, retreated 2 rounds late), stronger but outnumbered 20%, E 21%
  of first deaths (weaker Prism with median 528 gems chasing an enemy winning bag that is mostly retreating, not
  channelling; team wins 7%), caught retreating 11%, chased into enemies 8%, holding 8%.
- 15:10 Damage fate (dmgfate.py): camp damage later captured by the enemy or by nobody is 4-9% for every body; the
  Prism captures 87% of its own damage, Cassi / Issac / Willow feed allies (Prism 28-39%). Labour is not wasted on
  uncaptured groups. Launched C2 `duel` implementer (briefs/c2-duel.md: one matchup model -> hunt, spacing,
  game-ender restraint; copies c2-duel and c2-duel-ns without spacing).
- 15:15 Focus race (focusratio.py, Prism games): the higher-Focus Prism's team wins 52% at ratio 1-1.2, ~60% at
  1.2-1.5, ~75% at 1.5-2, ~93% at 2+. Ratios diverge early: at r150, 21% of games are already at 1.5+; at r300, 31%.

## Candidates
- **C1 `presence`** (patches/c1-presence.diff): provable enemy reach (dead: respawn + walk from spawn; seen: last
  sighting + elapsed steps) scales farm's side hazard and contested bonus (home^f, 1 + (e-1) f) and allows a
  provably uninterruptible long winning channel. `mx-rhea-c1-dev`: **50.1% (49.1-51.0) of 10,200**, OOF 1,245 vs 825.
  Final build (after audit) on hold: **50.3% (49.4-51.3) of 10,200**, OOF 986 vs 735. PRES fires in 94% of games
  (median f 0.75), PSAFE never (tribute_safe already passes those channels). Dropped: provable-reach information
  moves the territorial weights a lot and changes nothing in the result. The model stays available as infrastructure.
- 15:08 Focus gap sources (focus_src.py): at r150, ratio 1.2-1.5 is capture-driven (leading Prism 140 capture gems
  in 4.9 captures vs 99 in 3.9); ratio 1.5+ adds early Prism deaths (trailer 0.4 deaths, 17 gems lost, kill gems 9
  to the leader). At r300 ratio 1.5+ the leader has 53 kill gems. The Prism captures only ~5 groups by r150.
- **C2 `duel`** (patches/c2-duel.diff, c2-duel-ns.diff): `duel_edge` (kill turns each way from Focus, health,
  shields, cooldowns), net bodies; hunt (a favoured Prism's chase priced by bag x (1 + premium) + kill gold), spacing
  (a disfavoured Prism retreats on sight within two-turn reach + 1 and its farm skips groups inside), game-ender
  restraint for non-channelling carriers. `mx-rhea-c2-dev`: **44.8% (43.9-45.8) of 10,200**; without spacing
  (`c2ns-dev`): **49.9% (49.0-50.9)**. Spacing costs ~5 (as ARGO's "Prism avoids Prisms" -6): positional freedom near
  the enemy Prism is worth more than the deaths it avoids. Hunts fire 1.4 a game and are mostly vetoed by the existing
  escape verdict (612) and chase fight (696). The restraint barely binds: stop_game_ender only runs against a
  channelling ender (holds_hard_stop); the E targets read as non-channelling because carriers start a tribute every
  turn end and cancel it (mite_tribute_habit). Both dropped as standalones.

- 15:30 Turn-by-turn study (read-only analyst, 5 close Prism games read, then all 1,020 mirror games scripted; scripts tt_*.py).
  Unproductive pursuits (3+ rounds, no hit, no share) ~860 champion-rounds per team-game, ~555 lost. Sized habits:
  1. farm/retreat flicker on a group's edge (farm picks g, want_home R, farm picks g again): 10.0 (W) vs 12.2 (L) per
     team-game, ~31 rounds each, 0.077 gems/round vs 0.296; deaths in them 0.57 vs 1.30. The only habit losers do clearly more.
  2. target churn with no new information ~19/team-game plus ~20 on respawning groups (max_wait=2 hard drop), ~210 lost rounds.
  3. recall for group X, retarget on landing: 4.5/team-game (a third of recall-to-farm trips), half would have been faster walking; ~44 rounds.
  4. racing the enemy for its own groups at respawn: 7.3 vs 9.0, ~110-130 lost rounds.
  5. ally overlap ~10/team-game, symmetric.
  Monoliths first hit at median r554 (383/625 never); first Monolith capturer wins 68%, first Golem 57%.
  -> C3 `threat` (habit 1): the retreat's verdict marks the group; farm re-asks the same stand test at the group's work tile.
- 15:36 Probes on `mid_exposure` (the contested-middle weight 1.36; the W-L capture gap is mostly mid and enemy-side
  groups): pb-mid10 (1.0), pb-mid17 (1.70), pb-mid22 (2.2), pb-mid17h (1.70 with home_power halved), each on dev
  (`mx-rhea-pbmid*`). A direction-finding probe, not a candidate in itself. pb-mid17 smoke 57.8% of 256 (noise).
- 15:40 C4 `recall` implementer launched (habit 3: recall target as a commitment / claim; find the cause split first).
- 15:40 Probe results (dev, 10,200 each): pb-mid10 **45.9 (44.9-46.8)**, pb-mid17 **49.7 (48.7-50.7)**, pb-mid22 **47.3 (46.3-48.2)**,
  pb-mid17h **49.5 (48.6-50.5)**. The tuned 1.36 sits at the optimum (dropping the mid bonus costs 4); home_power halved is
  level. The constant side of the middle is spent: the middle gap must come from behaviour, not weights. A/Bs run in ~3 min
  per 10k on this box, so many more reads are affordable.
- 15:55 **Binding check** (overseer: does a change move games at all?). `scripts/bind.py MIRROR CAND`: games are
  deterministic and chy-mirror is chy-ref, so each CAND-vs-chy-ref debug game on study3 pairs with the mirror's game on the
  same map and side; the first D line (round, champion, branch, target, claim) that differs on CAND's side is where the
  change first bound, and the pair's results show what it did. (Sanity: mirror against itself 100% identical; side swaps identical.)
  - C1 `presence` (`bind1-c1`): binds in **76%** of games, first divergence median r177 (p25 r40), almost all F->F (a
    different farm target); results flip 242 W->L vs 238 L->W: net zero. It changes targets a lot; the changes are no better.
  - C2 `duel-ns` (`bind1-c2ns`): binds in only **14%** of games (F->C hunts 76, F->F 73, R->B 26); flips 31 vs 35. Too rare
    to reach the goal whatever its sign.
  - Lesson: once a game diverges its result flips ~24% of the time each way (chaos), so a change needs both reach (binds in
    most games) and a real edge where it binds. C1 had reach without edge, C2 neither. Every candidate gets this check.
  - Launcher bug fixed: ab.sh passed multiple extra args wrongly (`$@` inside the tmux string); earlier runs had at most one.
- 15:55 Loss episodes on the mirror (`analyze.py --reports losses`): deaths cost 469 gems/game (731 in losses, 182 in wins);
  camps lost 354. The win/loss signature is the Prism killed carrying 200+ gems (walking with gems or fighting, killer seen
  6+ rounds, grouped): ~0.19 a game a side, almost only in losses. `cf recall` says a recall in the safe window would have
  saved 35-39% of those bags. Example 2d4e1d13 r535-570: our Prism with a 1024-gem (winning) bag walks B/E/R between spawn and
  the altar while the enemy Prism guards it; 3742 -> 1735 hp in one turn, killed at r570; the enemy wins.
- Winning bags (`scripts/winbag.py`: a champion's bag + its team's score >= 1000): 1,197 team-games in 1,020 games; the holder
  wins 88% if it keeps it alive, 25% if it dies with it (73). Both sides hold one at once in 375 team-games: a coin flip (51%);
  otherwise the holder wins 99%. Median first winning bag r597; held a median 29 rounds (p75 91) before tribute: the channel
  is ceil(bag/10) turns, the whole bag, and any stun cancels it, so a 600-gem Prism needs 60 uninterrupted turns at an altar.
- 16:00 Endgame races (`endrace.py`, `endrace2.py`): both sides hold a winning bag at once in 174 games (17%), a coin flip.
  Winning tributes channel a median 60 turns; each side starts ~5 a game; ends: stun 420/316 (winner/loser side), manual
  cancel 310/393, lock 156/104, completed 120/0; the loser never started one in 119. Completed ones mostly ran with most
  enemies alive and none near (nearest 12+ in 40, 7+ in 81): races are won by tributing where and when the enemy cannot
  reach, not by fighting. -> C5 `race` brief (race arithmetic per altar, manual-cancel audit, lock denial).
- 16:05 **C3 `threat`** (patch `patches/c3-threat.diff`): bind run `mx-rhea-bind-c3` (study3, debug, 2,040) **46.5% (44.4-48.7)**,
  OOF ~20% above the mirror. Binds in 83% of games (F->F); flips 344 W->L vs 273 L->W, the loss concentrated in games diverging
  before r100 (-7.6%). Removes only 7-17% of the flips: most marks clear when the stand test at the work tile holds, so both
  tests agree and the champion goes back. Passing up contested groups early costs more than the flicker. Dropped.
- 16:20 **C4 `recall`** (patch `patches/c4-recall.diff`): cause split of persistent landing retargets: ally claimed X before our
  RFCHOOSE 37%, X's wait from the landing tile > max_wait (hard drop) 14%, chosen group dropped at the choice by its wait 13%,
  ally claimed during the channel 9%, price 18%. Built: `served_first` (no recall for a group an ally's claim serves no later
  than our recall would) and the landed group keeps the wait the recall priced. bind-c4 (study3 debug 2,040): **51.3% (49.2-53.5)**,
  binds in 89% (F->F 1093, K->F 584), recalls -24%; flips 352 vs 379. OOF turns up 47% in the same number of games (debug).
  Launched `mx-rhea-c4-dev`.
- 16:07 C4 `recall` dev (`mx-rhea-c4-dev`): **50.1% (49.1-51.1) of 10,200**, OOF 862 vs 877. Level: the study3 51.3 was noise.
  Fewer recalls for served claims reshuffle targets without an edge. Dropped as a standalone.
- 16:05 C6 `carry` implementer launched (Prism / carrier killed with a big bag: price the swing, recall in the safe window).
- 16:15 Early game (`early.py`, `prismdeath.py`): **the first Prism death's team wins 8% of 540 games** (8% by r200 too); 393
  are by the enemy Prism and the weaker by Focus dies in 69%. A lead of 60+ gems in hand at r150 wins 79%, 0-30 is ~55%.
  The first death in general: 37%. -> C7 `hunt` brief (on c2-duel-ns: audit the vetoes that stopped favoured hunts).
- 16:50 **C5 `race`** (patches `c5-race.diff` kept part, `c5-race-full.diff` dropped design). Step 1: manual cancels of winning
  channels are justified in 98% (a stunner or lock carrier could reach before the end); 482 of 703 are one-turn channels from
  the turn-end tribute habit cancelled when want_home fires. Starts with a non-negative margin (no stop can arrive in time)
  complete 95% but are only 64 of ~1,600; no other altar would have had one. Refusing negative-margin channels / holding at
  spawn: **40.6%**, then **32.2%** after audit fixes (bind study3): holders win by channelling in windows the worst case calls
  unsafe, because the enemy does not beeline to every channel. Denial piece alone (ally stops the ender in time -> holder spared;
  lock before shards in races): **49.5%**, binds in 11%, races 176 vs 178 of 354. Dropped. Lesson: worst-case race arithmetic is
  far too pessimistic; the endgame is won on the enemy's actual behaviour.
- 16:50 C7 `hunt` implementer launched.
- 16:55 **C6 `carry`** (patch `c6-carry.diff`): step 1 on 404 deaths with 200+ gems (0.198/game/side, 378 in losses; 82% Prism
  victims, 82% Prism killers): last 10 turns R 174 (no winning bag either side in 155), E 138 (113 with only the enemy holding a
  winning bag), tributing 50; killer unseen until the first hit in 193. The recall window was open on the last turn before the
  first hit in 301/386 and want_home said stay in 297: retreat comes only once a recall can be cancelled. But the window closing
  happens ~14 times a game per side for 50+ carriers, 20x the deaths. Built: keep the turn-end recall on the closing turn when
  the forecast stand is lost and the swing (2x bag) pays the trip; bag priced as a swing in the carrier-falls test. Bind study3:
  **48.4% (46.2-50.6)**, binds 67% (F->K 531, B->K 225), flips 207 vs 174, 200+ deaths 0.198 -> 0.190. Dropped: the keeps
  rarely fall in the windows before deaths; the threat model can't tell which closing ends in a death.
- 17:00 C8 `urgency` brief and implementer: E deaths are 28% of all deaths; holds_hard_stop needs only that the ender is
  channelling, and turn-end one-turn tribute channels make every holder near an altar read as channelling a winning
  tribute that would in fact last ~60 turns.
- 17:40 C7 `hunt` stopped before its gate (no smoke/bind); partial diff `patches/c7-hunt-partial.diff`. Step-2 findings: C2's
  duel model played both sides at once and called hunts "favoured" where the weaker Prism gets the first stun on the walker
  entering range; in true turn order it agreed with 95% of the chase-trade "lost" vetoes (V alone). ~91% of "lost" vetoes are
  V's teammates nearby. Two escape-model errors (our stun stays ready until cast; our double move) overturn ~11% of hunt escape
  vetoes, ~7% on all chases: a possible general fix, untested. C8 `urgency` stopped mid-work (partial `patches/c8-urgency.diff`).
- 17:45 **C8 `urgency`** (patch `c8-urgency.diff`, built and audited): step 1 says the one-turn-channel hypothesis is mostly
  wrong (272 of 7,388 E starts); E charges long channels (median 61 turns left) and our champion dies within 10 rounds in 51%
  of E episodes whatever the clock; a stop gains only the turns already run, as the owner restarts whole. Built: wait a turn
  when our worst-case stop (or an ally's safe stop) still lands before the channel (`stop_can_wait`, `holds_stop_in_time`).
  Bind study3 debug: **52.5% (50.4-54.7) of 2,040**, binds 27% (E->F/R/B), flips 34 W->L vs **86 L->W**, gain in games
  diverging after r400. The only positive lead; **unconfirmed** (no 10k dev/hold read: programme ended). Next: A/B c8-urgency
  on dev, hold, conf.
