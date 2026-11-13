# PHOEBE: macro refactor of charybdis (2026-11-13)

## Status (final, 17:24 UTC: programme stopped by the user)
- Best candidate: `variants/p-nolock` = `bots/charybdis` on this branch (chy-ref without buying altar locks). Dev 51.2
  (50.2-52.2), hold 50.5 (49.6-51.5), x1 50.2 (49.3-51.2), 10,200 each at 2x; held-out pooled (hold + x1) 50.35 of
  20,400. A small component, not a macro lever. No normal-fuel read was run (stopped before 21:30).
- Every structural candidate read level on train (10,200 each, 2x): A `phb-hub` 50.1 / 49.9 / 50.1; B `phb-lethal`
  50.3 / 49.7 / 50.8 (49.8-51.8); C `phb-stakes` 50.1 / 50.4 (49.4-51.4). B and C were stopped before audit and smoke;
  their last sources and diffs (`patches/phb-lethal.diff`, `patches/phb-stakes.diff`) are unaudited.
- Nothing running: implementers told to stop, every mx-phoebe tmux session and extraction killed.

## Setup
- Every A/B: `research/mx-phoebe/ab.sh TAG CAND SUITE [args]` = `tools/ab.py variants/CAND variants/chy-ref
  --no-test-draft --fuel 200000 --suites SUITE --name mx-phoebe-TAG`, fast runner native.
- Suites (fresh `--mix ladder-v4`, `research/mx-phoebe/gen.sh NAME A B`):
  - `maps/suites/mx/dev` (5,100 maps), `maps/suites/mx/hold` (5,100): given.
  - `maps/suites/mx-phoebe/study` (61421000-61421003, 1,360 maps): debug traces and studies only, never decisions.
  - `maps/suites/mx-phoebe/train` (61421100-61421114, 5,100 maps): implementers' own iteration loops.
  - Reserved fresh: x1 61421200-14, x2 61421300-14, normal-fuel final 61421400-14.

## Log
- 14:25 Debug mirror chy-mirror vs chy-ref on study: 50.0% of 2,720 (2.4 min wall). Extracted to `replays/.mxp-mirror`.
  Scripts in `research/mx-phoebe/scripts/` (flow, legs, crews, gold, deaths, firstdeath, prismdist; turn_budget copy).
- 14:35 Mirror facts (W/L per team-game):
  - Supply is not binding: gem-weighted group-rounds asleep (available, unworked) own 59%, mid 68%, enemy 59%.
  - Captured 1101/892, tributed 1094/381; kill gems 288/45. Captures 54/48 (own 43, mid 5.8/3.8, enemy 5.7/3.5).
  - Time r1-300 (mirror W): camp 26%, walking ~45%, hold 5%, recall 5%, dead 3%, fight 3%. Solo vs idle r1-300:
    camp 31%, walking ~45%: walking is the bot's own cost, not the enemy's. Solo collected@300 527 (mirror W 448, L 346).
  - Walk legs (r<=400) average 15.5 rounds (incl. holds) for 9.9 tiles direct; swapping allies' targets would save
    only ~7 steps a game: assignment crossing is not the problem.
  - 70% of camp-hit turns r1-300 are crews of 2+ (wolves 65%, elk 87%). Probes crew_cap 2 / 3: SPRT-low stops at
    49.1% (1,498) / 49.4% (1,222) on train: crews are not simply over-used.
  - Gold is skewed: by r300 Prism earns 859, Vesper 735, Cassi 59, Issac 69, Willow 16 (Willow never upgrades;
    Cassi 651 HP at r300). Unspent team gold r600 480/261.
  - First champion death decides: victim team wins 34%. First victims: C&I 526/1221 (43%, median r191, victim team
    wins 37.3%, killer the enemy Prism 51%), Prism 141 (7.1%), Ryth 118, Vesper 114. Around them ~2 allies and ~3
    enemies within 8. C&I deaths 2.9 (L) / 1.2 (W) a game, mostly one stun-burst (HP < 1.5 x killer Focus).
  - Non-Prism captures within 12 tiles of the Prism at payout: ~27 gems r1-150, ~31 r151-300 (Prism holds 107/131).
- 14:45 Fresh suites generated: x1 (61421200-214), x2 (61421300-314), nf (61421400-414), 5,100 maps each.
- 14:45 A1 `phb-hub` implementer launched (brief `briefs/a-hub.md`): allies price a group's gems by their expected
  holder (the Prism's premium where it can collect the capture), holds begun for a Prism takeover rather than left
  empty. Study subagent launched (read-only): anatomy of the first death in 40 mirror games.
- 14:46 First deaths by location: mid 656 (victim team wins 34.5%), own side 449 (31.6%), enemy side 116 (36.2%).
- 14:46 Probes on train (SPRT-low): efficiency_power 1.47 -> 0 and -1 (gold allocation by gold efficiency).
- 15:00 Gold probes (train, SPRT-low): efficiency_power 0 -> 47.6% of 1,810; -1 -> 46.5% of 800. Concentrating gold
  on the efficient bodies (Prism, Vesper) is right: starved bodies are not a lever. Gold redistribution dropped.
- 15:00 Hazard near the enemy Prism (our body within 5 of it, first per 20 rounds, r<=600; dies within 10 rounds):
  C&I 13.6% with our Prism within 6 of it (3,696), 20.5% without (5,199), 43.7% with our Prism dead (531);
  Vesper 8.6 / 16.3 / 40.3; Willow 8.4 / 16.1 / 20.2. Cover roughly halves the hazard, but contacts within 5
  account for only ~1/3 of C&I deaths.
- 14:52 Legs between camp hits (r<=400, per team-game): 61 walking legs averaging 11 rounds (670 rounds) and 21
  legs with a recall inside averaging 30 rounds (620 rounds): bank trips cost about as much body time as walking
  between groups. C&I 6.0 bank legs (29.5 r), Prism 3.8 (30.3), Vesper 3.8 (24.1), Willow 1.0 (43.4).
- 14:55 Kill rate by the victim's commitment (killctx.py, r<=800): bodies under camp fire or holding are killed *less*
  per exposure round than free ones (camp 4.9, hold 2.8, tribute 1.9, free 7.7 per 1000); encounters that start on a
  camp end in our death 4.6% vs 6.0% free. "Catching committed enemies" is not a lever. Dropped.
- 14:56 The gem race (race.py): the loser's Prism holds 216 gems at the end (quartiles 18 / 100 / 476); the loser had
  tributed + carried >= 1000 at the end in 19.8% of games, first to 1000 held in 13.8%. Priors (KRONOS k6, ICARUS E3,
  CASTOR C12, ARGO chunking) all show banking the hoard earlier loses 1-14 points: the race is lost in the altar stun
  war, not the decision. Not pursued.
- 14:58 Prism duels (pduel.py, gclass.py): first Prism death decides: by the enemy Prism 39% of games (survivor wins
  93.6%, median r422), by another body 12% (85.4%), by camps 3%; no Prism death 35% (median end r601); <2 Prisms 11%.
  10 rounds before the first Prism-on-Prism kill the killer had more Focus 70%, more HP 72%, more allies within 8 in
  47% vs fewer 26%; Focus 871 vs 663, max HP 2,656 vs 2,121, bag 434 vs 305, lifetime gold 1,562 vs 1,261. Its
  income before the duel (pinc.py) is captures: 426 vs 355 gems, 1,381 vs 1,159 gold; kills only 1.9 vs 1.1 (21 vs 8
  gems). Duels are won by the richer Prism, and Prism wealth comes from its own captures.
- 14:59 Paired Prism income r1-300 (pincome.py): richer Prism 309 gems vs 227, 10.4 vs 8.5 captures, camp-hit rounds
  57 vs 55, hold rounds 60 vs 48, dead rounds 1.7 vs 12.8; ally captures near it equal. The richer Prism did not get
  more help: it died less and held more. The Prism spends only ~38% of r1-300 hitting camps or holding.
- 14:59 Altars are not at spawns: nearest altar to own spawn median 19 tiles (quartiles 12-30), about half way to the
  enemy spawn. Bank trips are walks to contested altars; recalls are transport and shopping.
- 15:00 First-death study (subagent, 40 games by hand + all 1,360): "lethal-exposed" (within 5 of a ready enemy Prism
  ground spell with HP <= Focus, or 4 of a ready stun with HP <= 1.5 Focus) -> next-round death 39% (C&I), 46% (other),
  55% (Prism); inside reach but not lethal 0.4-0.8%; 6-7 tiles 0-0.3%. 83% of C&I first deaths by a Prism blow were
  lethal-exposed the round before, 98% of those without our Prism within 5 of theirs. The enemy Prism walked in
  (mostly on chase; the victim retreating one step does not escape) or the victim walked in (farm, E, retreat).
  Cover by our Prism (within 4 of the enemy Prism, stun ready) exists in 3-4% of lethal states; it halves death.
  mo7-shy (ICARUS) tried guarded steps for this and was level; B's brief is diagnose-then-fix at the root.
- 15:03 B `phb-lethal` implementer launched (brief `briefs/b-lethal.md`).
- 15:20 A `phb-hub` train reads (implementer's): hub1 50.1% (49.1-51.1) of 10,200, OOF 1,458/950; hub2 49.9%
  (49.0-50.9), OOF 950/953. Level, as BOREAS b-hub and DELPHI E2 were. B `phb-lethal` leth1 50.3% (49.3-51.3), OOF
  1,618/899. Both still iterating.
- 15:30 Time use r1-400 (ptime.py; % of rounds): Prism camp 17, hold 12, recall 4, walk/other 59, dead 3; Cassi camp 25,
  walk 58, dead 7; Vesper camp 33, hold 10, walk 47; Willow camp 18, walk 72. At leg starts (nearest.py) ~10 gem groups
  are alive and asleep; the chosen one is 12.9 tiles away against 10.7 for the nearest own/mid one (often a big group):
  walking is set by the map's supply geometry, not by bad picks.
- 15:35 No-Prism-death games (35%): captures nearly level (W 1,058 / L 982, r1-300 496 / 459) but L tributed 448 vs
  1,042 (its Prism still holds ~500). Early deaths are rare (C&I 0.38, Prism 0.12 a team-game by r300).
- 15:40 Richer vs poorer Prism by r400 (pside.py): 418 vs 306 gems: own side +64, mid +28, enemy side +20; their teams
  +44 own, +36 mid, +24 enemy. Prism duels: the first damaging Prism spell between the Prisms came from the eventual
  killer 58%; when the victim stunned first, the killer was richer 86% (a richer Prism survives the first stun); when the
  killer stunned first it was richer only 47%. Wealth decides, the first stun equalises.
- 15:55 **A `phb-hub` final: level, dropped.** Collector ETA from the Prism's posted task; allies price the premium
  only when the Prism can collect before the payout of a hold they would begin; holds begun for a takeover rather than
  left empty. Train: hub1 50.1 (49.1-51.1), hub2 (begin-only) 49.9 (49.0-50.9), hub3 final 50.1 (49.1-51.1) of 10,200
  each, OOF 1,212 vs 866. Kept promises 39% of hub picks (58% of the captures we made); Prism share of captured gems
  59.2 vs 58.7% (r1-150). Why promises break: in two thirds the Prism's 'G' loop never considers the hold (it is
  collecting another capture, walking elsewhere, on a shop trip or hitting camps; 11+ tiles away at payout in half).
  Lesson: the Prism's next pick cannot be predicted from its posted task; making the hub real needs the Prism to
  commit to an itinerary, a different design. Patches `phb-hub.diff`, `phb-begin.diff`.
- 15:35 Probe `p-nolock` (chy-ref without buying altar locks; overseer's TODO lead, +1.0 in an older mirror) on dev.
- 15:51 C `phb-stakes` implementer launched (brief `briefs/c-stakes.md`): fight-side life and bag stakes by what the team loses (output x rounds out, C&I as two bodies, Prism bags at 1 + premium, the taker's gain), calibrated to today's mean.
- 15:51 p-nolock dev: **51.2% (50.2-52.2) of 10,200**, OOF 809/897. Confirming on hold.
- 15:56 p-nolock hold: 50.5% (49.6-51.5) of 10,200, OOF 829/886 (dev+hold 50.85 of 20,400). Mechanism (1,000 dev games): our deaths 4.97 vs 5.70 a game, kills 5.5 vs 4.8, shop purchase events 50.6 vs 57.2, Prism deaths 0.78 vs 0.90: lock purchases and placing trips cost bodies. On x1 for a held-out read.
- 15:59 p-nolock x1: 50.2% (49.3-51.2) of 10,200, OOF 888/895. Held-out pooled (hold + x1) 50.35 of 20,400; all
  three suites 50.6 of 30,600. A small, plausible component (fewer purchase/placing trips, fewer deaths), not a lever.
- 16:05 Prism standoffs (cdwin.py): Prisms spend ~70 rounds a game 5-8 tiles apart; when only one has its stun ready,
  the pair closes to 4 within 2 rounds 8% of the time, as often as when both are ready (5.5%). A Prism cannot cast after
  walking, so stepping in costs the turn and the other steps back: the asymmetric window is not simply exploitable.
- 16:05 Live scrims (committed games.jsonl, v126): charybdis wins 96-97% against Mite and Fish, 72% against BattleCats,
  which out-earns us in gold (11,022 vs 7,597) and kills (7.1 vs 5.2). No local copy of it to study.
- 16:40-17:10 B `phb-lethal` (implementer's, still running): train leth1 50.3 (49.3-51.3) OOF 1,618/899, leth2 49.7
  (48.7-50.6) OOF 1,651/865; ~25 study-suite probes of its variants all 46.9-50.7 (several at 1x fuel). C
  `phb-stakes`: train stk1 50.1 (49.2-51.1) of 10,200, OOF 1,184/864; debug studies 49.4, 48.9, 49.6, 49.7.
- 16:50 Supply by type (idle.py, r<=400, % of group-rounds alive and asleep): own golems 67, elk 47, wolves 56, gem
  clusters 33, gold clusters 49. Labour and walking, not supply, bound the economy.
- 17:18 Coordinator: box overloaded (C's extraction outside the pool); both implementers told to throttle (one run at a
  time, extract --threads <= 8) and wrap up.
- 17:20 B leth3 (final train read) 50.8% (49.8-51.8) of 10,200, OOF 1,084/966; C stk2 50.4% (49.4-51.4), OOF
  1,090/885. Both level.
- 17:24 Stopped by the user: implementers told to stop, tmux sessions and extractions killed, notes and patches committed.
- C final (implementer, stopped before fixes): per-body life = (respawn + walk back) x camp output x team gems per
  output (C&I both bodies) + kill gold; gem price = holder (1 + premium) and taker (1 + an opposing Prism's premium);
  each side's multipliers averaged to 1. First version died more (8.40 vs 7.85 deaths a game) and its Prism died in
  more games (41.9 vs 39.0%). Unfixed audit findings: C&I bag double-counted in the gem weights
  (abilities.cc:209); gem-weight calibration pins the main carrier at 17.5 and cuts other bags to ~40% early (the
  likely cause of the extra deaths); a loaded Prism's Focus counted in both its life rate and its bag.
- B final (implementer): smoke 51.6% of 256, clean. Diagnosis of lethal-exposed turns: largest share is E (stopping a
  game-ending Prism, ~5.9k turns, 1.8k deaths, an allowed exception); then leaving too late (1,946 of 2,081 lethal
  retreat turns had no safe step left); then blind walk-ins (85-90% with the enemy Prism unseen by the body, though an
  ally saw it in ~65%: comms bytes are full, sightings not shared); last the two-turn stun lock under-priced (282
  turns). Change: lethal() prices the stun lock; Safety::trapped() flags tiles a seen enemy Prism can still kill us on by
  our turn after next; want_home leaves trapped tiles, retreat_step frees them first, keep_out and Willow's guards keep
  off them. Mechanism (all-enemy version): lethal-exposed rounds 12.7 -> 11.9 a game, deaths level, captures level.
  Open lead: sharing enemy Prism sightings (comms are full). Patch `phb-lethal.diff` is the final audited version.
