# THEIA: macro refactor of charybdis (2026-11-13)

## Status (final, 19:50 UTC)
- **bots/charybdis = denyfix-531** (charybdis 531 c451e3387 + denyfix-a's pieces 530 lacks; patches/denyfix-531-vs-chy-531.diff).
  Smoke only (256 ladder games vs chy-531: 48.8%, 0 failed, no DRAFT-UNFINISHED / PLAN-CHECK); the user runs its
  normal-fuel A/B against 531. Its OOF in the smoke was twice REF's (43 turns in 21 games vs 20 in 17): check it there.
- The 529-based best, **denyfix-a**, is bots/charybdis at 503219a55: pooled held-out 52.5 of 30,600 vs 529, 52.2 at 100k.
- Against 531: denyfix-a 48.9 on hold (2x); 531 itself reads 53.6 vs 529 on hold. 530's `stop_due` already holds the
  late-stop gain; what is left to add is the alarm and T9's fixes.
- Stopped at the user's request: the 2x / 100k reads of denyfix-531, T12 `alarm` (alarm-a: dev 52.7 vs 529, one read).
- Closed lines: orbit/funnel, front, chase, premium, relay, conceal, escort, chip: all level or worse.

Every A/B: `research/mx-theia/ab.sh TAG CAND SUITE [args]` = `tools/ab.py variants/CAND variants/chy-ref --no-test-draft
--fuel 200000 --suites SUITE --name mx-theia-TAG`, fast runner native. Suites: `maps/suites/mx/dev` (screen),
`maps/suites/mx/hold` (held out), `maps/suites/mx-theia/x1` (fresh, seeds 61431100-61431114, held out),
`maps/suites/mx-theia/study` (seeds 61431000-61431002, 1,020 maps: debug traces and analysis only, never decisions).

## Log

- 14:20 Read brief, rules, AGENTS, prior programmes (macro-orchestrators-2026-11-11, mac13-castor in full, overseer
  candidates). Priors: Prism duel decides; farm time binds; CASTOR's +5 came from pricing consistency (Prism gem
  premium everywhere) and Prism recall/shop timing. Restrictive coordination (pack, squad, escort) lost.
- 14:25 Debug mirror chy-mirror vs chy-ref on study (2,040 games, 1,019 distinct), extracted to
  `replays/mx-theia-an/mirror`. Scripts in `research/mx-theia/scripts/`.
- 14:40 **Territory profile of the mirror** (winner W vs loser L, per game; `terr.py`, `supply.py`, `occ.py`,
  `deaths.py`):
  - Captured gems by group side: own 817 / 747, **mid 309 / 151, enemy side 164 / 86, Monolith 451 / 201**. Early
    (r<=300): own 339 / 314, mid 101 / 58, enemy 55 / 34. The winner's edge is almost all contested ground.
  - Supply use through r600 (gems captured / respawn-limited potential): own side 51% / 47%, mid 27% / 14%, enemy
    side 7% / 4%, Monolith 3% / 2%. Supply is abundant everywhere; the mid is mostly unworked by both teams.
  - Occupancy (alive champion-rounds by spawn-distance side): own 64-68%, mid 30-35%, **enemy side 1%**. With every
    enemy alive own 67 / mid 32 / enemy 1.1%; with half or more of the enemy dead own 34 / mid 62 / **enemy 3.3%**.
    Champions barely set foot on the enemy side even while it is empty: the static side weight
    (home_ground: share^1.89 by spawn walks) does not know who is alive or where they are.
  - Deaths by champions: L 10.6 / W 3.5 a game; L dies on its own side 41% of the time (the winner pushes in).
  - Gold earned by r300: Prism 850, Vesper 758, Cassi 61, Issac 70, Willow 16 (hold_shy hands captures away by
    design). Unspent gold time-averaged: Prism 123, Vesper 47, rest <35.
- 14:55 **Funnel leak** (`orbit.py`, `funnel.py`, r1-600): non-Prism allies capture ~125 gems a team-game in groups
  within 12 tiles of their living Prism without the Prism sharing (half within 6). At hold start the Prism was
  farming ('F') for 63% of those gems, holding 8%, tributing 10%; an enemy within 8 of the capturer only 27%. Prism
  share of capture gems r1-600: 0.585. Cause: the feeders price the premium only on the Prism's claimed group, and
  the funnel (leave_for_prism) waits at most capture_time and never for a Prism busy on a live group (prism_eta
  cannot time a clear). A wait only delays the group's next respawn (timer starts at payout), which `worth_wait`
  prices at premium x cycle: 50-200 rounds early, against the 6 the lapse allows.
  -> T2 `orbit` (briefs/t2-orbit.md) and T3 `funnel` on top of it (briefs/t3-funnel.md): one design, the team's
  territory forms around its carry by pricing, not by rules.
- Monolith (`mono.py`): 31% of maps; captured in 43% of those; the first capturer wins 74%, but only ~50% when it
  was not ahead 30 rounds before: a consequence of leads, not a lever. Steals (damage-weighted, `steals.py`): 32-62
  gems a game, small.
- Suites: x2 (61431300-61431314) and f100 (61431200-61431214, for the final 100k read) generated, 5,100 maps each.

- 15:25 **orbit-b** (T3 on orbit-a: funnel waits priced by premium x cycle, prism_eta times a live clear, orbit
  anchored on the Prism's tile): 48.7 of 1,236, SPRT H0. Prism share r<=600 0.589 vs 0.578 (+1 point), total gems
  r<=600 down 14 a game. Holding allies back for the Prism costs about what it gains: the funnel/orbit line is not a
  lever. Closed.
- 15:20 **front smokes** (T1): front-a 23.8%, front-b 41.4%, front-a-nosight (deaths only: the front moves back
  only while the whole enemy team is dead) 48.4%, all 256 ladder games. A sighted enemy within reach drops the
  weight of every group near it towards 0 and the team abandons contested ground it would have held: fear of
  sighted enemies collapses play, the static side weight is a better prior than live sightings priced as a lone
  farmer's death. Deaths-only screened on dev (nosight-dev).
- 15:35 **Macro metrics W vs L** (`macroagg.py`, 600 mirror games; analysis/macro.py): contest_win 0.627 / 0.373,
  own_lost 0.076 / 0.189, fight_outnum 0.295 / 0.402, outnumbered 0.118 / 0.167, control 0.535 / 0.465; cohesion
  (isolated 0.182 / 0.190, lonely_death 0.254 / 0.283, fight_turnout 0.537 / 0.544) barely differs. The loser
  fights outnumbered more and loses contested captures; spread and grouping are not the difference.

- 15:40 nosight-dev: H0 at 406 games, 49.5 (44.7-54.4). Front line closed.
- 15:45 **Prism duel** (`pdeath.py`, `duel.py`, `duelctx.py`): 1,114 of 2,040 games have a Prism death; the first
  Prism to die loses 89% (996 / 118). Losers' Prisms die 1.6 a game carrying a mean 132 gems (21% carry 200+), 80% to
  the enemy Prism, by its spells. First Prism-on-Prism kills (378 distinct): the killer had more Focus 72% (half of them
  by 100+), more max health 62%; the victim was farming (F 56% of the 10 rounds before contact), saw the killer at
  contact (within 8) only 19% of the time, and closed the gap as much as the killer did. Prior programmes tried
  avoidance and caution (all lost: EXPERIMENTS 'Caution loses in proportion to the work it costs'): the duel is
  decided by the Focus lead, i.e. the Prism's gem rate.
- 15:50 **Where the Focus lead comes from** (`plead.py`, r250, both Prisms alive, 724 games): the Prism holds all its
  gems (no tributes yet), all from capture shares (kills ~0); team captures W 367 / L 336 predict the winner 65%,
  Prism Focus 60%. **Prism capture cycle** (`pcycle.py`, r<=600): 30 gems a capture; walk 14.7 rounds, clear 4.8,
  other 2.6, hold 6: walking is half the cycle. Allies clear 40% of the Prism's groups (`clears.py`). During its holds
  (`holdwork.py`, 65 rounds a Prism per 600) the Prism deals camp damage 5% of rounds; its ground slot is ready with a
  live group within 5 in 15%: free work exists but is small (~4 casts a game).
- 15:50 **Endings** (`endings.py`): median end ~r600; the winner tributes 1,093, the loser 372 (median 298); the
  winner's Prism scores 48% of its team's tributes; winners' big tributes are cancelled often (stuns 3.8, locks 1.6 a
  game).
- 15:52 **Pricing audit** (read-only agent): ranked mismatches: (1) premium cliff at 0.453 health while the bag is kept
  (Prism in that band only 2.7% of alive rounds: small); (2) **Monolith**: keep_bonus gives no premium but
  sole_capture_holder can pay the Prism; measured: the Prism receives only 21% of 88,700 Monolith gems; (3) **chase
  entry has no farm opportunity cost** and the strike search prices a step without walking or premium; (4) three gold
  prices (holder 0.3 vs per_gold vs efficiency counted twice); (5) pooled carrier hazard; (6) camp damage priced three
  ways; (7) constant life_value; (8) dominance read in one place. -> T4 (1, 2, 8) and T5 (3).

- 16:05 **Duel initiative** (`initiative.py`, 2,300 engagement-opening Prism-to-Prism unit casts): at Focus parity
  (0.8-1.25) the opener's target dies within 30 rounds 27%, the opener 13%; the stronger opener (>1.25) kills 61%.
  1,390 openers are by the weaker Prism (<0.8), 896 of them in branch E (stopping a winning tribute, median r993, 90%
  die): desperate endgames. Bushes play no part (killer in a bush at contact 8%, base rate 6%).

- 16:20 **Missed openings** (`missed.py`): a Prism that sees the enemy Prism within 4 with its stun ready and does not
  cast, at parity: 1.1 episodes a game; within 30 rounds the holder dies 15%, the enemy 24% (openers: 13% / 27%):
  holding is about as good as opening; initiative is not a lever. Prism camp deaths (`campdeath.py`): 66 in 2,040
  team-games, mostly in retreat: small. **By r150 the whole W/L capture difference is the Prism's** (`early.py`: Prism
  107 vs 95 gems, every other body equal): the early Prism's own farm rate is the economy.
- 16:21 chasea-dev: H0 at 3,565 games, 50.4 (48.8-52.1). Chase pricing is not a lever. The pool is fast now (~900
  games a minute when free).

- 16:30 **Ally damage** (`allydmg.py`, r<=150 per team-game): allies deal 13.4k camp damage, the Prism 4.1k; 44% of the
  allies' goes to groups the Prism collects, 53% to their own captures (face value). **Relay potential**
  (`relaypot.py`, r<=300, 15,029 consecutive Prism captures A->B): payout of A to hold of B median 19 rounds (mean 24);
  Prism's first hit on B to hold start 8.4; only 28% of B's damage was dealt before the Prism arrived (11% fully
  pre-cleared, 41% untouched). -> T6 `relay` (briefs/t6-relay.md): the holding Prism announces its next group and
  feeders price its premium there, so the clear happens during the Prism's hold and walk.
- 16:28 prema-dev: H0 at 1,333, 50.3 (47.7-53.0). premm-dev (Monolith only): H0 at 217 games, 49.3 (the SPRT stops
  very early when most pairs are untouched by the change and split 1-1: read such stops as 'not +2', nothing finer).

- 16:55 **Brainstorm agent** (read-only, scripts in /tmp/theia-ideas/): (1) **endgame tribute denial**: big tributes
  (200+) ~9 a game, the winner starts 7.4 and ~1.15 complete; chy-ref stops only winning tributes it sees, at once (stun
  cancels a mean 18 turns into ~93-turn channels, 64% in the first fifth), so each stop costs the channeller ~18 turns;
  unseen channels complete 86%, seen early 7%. scylla's denial package (late stops, alarm, watch ward, lock first, hoard
  stops) was worth +4 against charybdis 525 and was never ported to charybdis -> T7. (2) concealed tribute starts (pick
  altar/tile/time out of enemy sight; unit stuns need sight); (3) prem-m deserves a Monolith-maps-only read (events in
  ~9% of games); (4) relay extended to the trip home. Ruled out: Capture-emblem tap, clear-to-hold gap, camp damage
  soak, feeding through kills.

- 17:00 First team to start a winning-size tribute (score + bag >= 1,000) wins 93% (796 games); median 45 rounds from
  that start to the end (p75 169).
- 17:10 **relay-a** (T6): RELAY fires 0.8 a Prism hold, the Prism follows its announced group 68%, but feeders barely
  pre-clear it (share dealt before the Prism 0.23 vs 0.21; fully pre-cleared 6% vs 7%): the hold rest + walk (~29
  rounds) outruns feeders busy with their own work, and 15% of relayed groups go to the enemy. relay-dev: H0 at 5,273,
  50.3 (49.0-51.7). Closed.

- 17:45 **deny-a** (T7, scylla's denial ported: late stops, alarm, watch ward, lock first, hoard stops; our Prism
  exempt from hoards) and **deny-b** (hoards off). Smokes 51.6 / 52.7; the share of the enemy Prism's channel run
  before our cancels 0.61 stun / 0.73 lock (chy-ref's against us 0.23 / 0.23). denya-dev: **50.9 (50.0-51.9) of
  10,200** (SPRT never stopped); denyb-dev: H0 at 9,210, 50.5 (49.5-51.6). Hold read of deny-a running.

- 17:53 **deny-a held out**: hold 50.9 (49.9-51.8), x1 51.3 (50.3-52.2), x2 50.3 (49.4-51.3), 10,200 each: pooled
  held-out 50.8 of 30,600 (15,550 wins). **Why only +1** (`winrace.py`, 1,000 dev games): when chy-ref starts a
  winning-size tribute first (434 games) deny-a still wins 14.3% (the mirror's comeback rate is 7%); when deny-a is first
  (381) it wins 93.7% (mirror 93%); but deny-a is first less often (381 vs 434): stopping costs economy (bodies sent to
  hoards; deaths near hoard channels 3.69 vs 3.02 a game). Our stops now run 65-75% of the enemy channel (chy-ref's
  against us 20%). Ablations running: deny-nolock, deny-nowatch, deny-noalarm (flag flips in params.h).
- 17:54 conceal-a (T8: sight-aware altar/tile/time for long tributes; departs from chy-ref in 7 of 44 debug games):
  SPRT H0 at 356 (early-stop artefact: most pairs untouched); full dev read running.

- 17:58 **Ablations of deny-a** (dev, 10,200 each): no watch ward 51.7, no lock_first 50.6, no alarm 50.0;
  conceal-a full dev read 49.9 (48.9-50.8): level, closed. **deny-nowatch held out**: hold 51.8 (50.8-52.7), x1 50.7
  (49.7-51.6), x2 51.8 (50.8-52.8): **pooled 51.4 of 30,600** (15,730 wins; 95% CI ~50.8-52.0). The watch ward costs a
  NYX value-placed ward for the whole game; the alarm and the late stops carry the gain. bots/charybdis = deny-nowatch.
- 18:00 **Winning channels under deny-a** (`winchan.py`): chy-ref's completed 349 (our nearest body a median 7 tiles at
  its closest, within 4 in only 19%), stunned 1,048, locked 483, self-cancelled 1,473; ours completed 381, stunned
  2,170 and locked 786 by chy-ref's at-once stops. -> T9 (diagnose and fix our stops) and T10 (escort our tribute).

- 18:05 deny-nowatch at 100k fuel (f100, preview): 50.4 (49.4-51.3) of 10,200; OOF turns 76,905 in 7,557 games vs
  REF 79,457 in 7,548.
- 18:08 **Fewer pieces read better** (dev, 10,200 each, on deny-nowatch): no hoard stops 51.8, no lock_first 51.9,
  neither (**dnw-min**: deny_late + deny_alarm only) 52.2. dnw-min held out: hold 52.0 (51.0-52.9), x1 52.2
  (51.3-53.2), x2 52.1 (51.2-53.1): **pooled 52.1 of 30,600** (15,946 wins; CI ~51.6-52.7). Hoard stops (bodies sent
  after non-winning bags, which stay as enemy Focus) and the lock bought before shards each cost what they gain in the
  mirror; the gain is timing every stop for the channel's last turns and the alarm that brings stoppers in time.
  bots/charybdis = dnw-min.

- 18:14 **dnw-min at 100k fuel** (f100, 10,200): **51.4 (50.4-52.4)**; OOF turns CAND 74,808 in 7,484 games, REF
  78,088 in 7,448. Attribution: alarm without late stops (dnw-alarm) 49.8 on dev: the late timing is the gain.

- 18:44 **escort-a** (T10, on dnw-min: allies screen the altar of our winning tribute, value enemies that could stop
  it, break locks on it): debug batch shows stops per channel unchanged (completed 6.9% of started vs 6.4%; chy-ref
  stops from range 4 or with a lock, a screen at stand radius 2 blocks little), farming abandoned while a winning bag
  is pending. escort-dev 51.3 (50.3-52.2) vs dnw-min's 52.2: worse. Closed.

- 18:50 **dnw-min's win race** (`winrace.py`, 1,000 of 2,040 study games, 51.7 there): first to a winning start 420
  dnw-min vs 418 chy-ref (deny-a's 381 vs 434: the hoard stops and the lock bought first were what cost the economy);
  when chy-ref is first dnw-min still wins 11.7% (mirror 7%); when dnw-min is first it wins 92.6%. Our late stops run
  0.58 (stun) / 0.65 (lock) of chy-ref's channels; chy-ref's at-once stops run 0.20 / 0.18 of ours.
- 18:50 T11 `chip` implementer launched (free hits from beyond a camp's reach during holds; briefs/t11-chip.md).

- 19:05 **T9 denyfix** (on dnw-min's flags). Diagnosis of 261 long enemy winning channels that completed (2,040 debug
  study games): never seen and no alarm 86 (the alarm field does not fit the shared bytes in 830 of 2,040 games,
  mostly with a healer drafted), stopper died 37, waited for the margin then lost sight and forgot 51, seen but never
  targeted 21, stun spent on a guard 16, late from first sight 14, walk estimate (Chebyshev) too short 14, pre-empted
  15, nobody alive 6. chy-ref's other stop paths (strike-search stuns, turn-end locks) still cut 827 stuns / 130 locks
  at 0.40 / 0.32 of the channel; chy-ref self-cancels 2,454 times, 91% with one of our bodies within 8. Fixes: F1 keep
  the stun for the channeller, F2 walk by pathing (fuel-gated), F3 remember a seen channel where the alarm does not fit,
  F5 the late-stop gate on the other paths (stun_worth priced by the wasted-channel difference; place_lock skips an
  altar whose tributer is waited on); F4 (inferred alarm) built but off. denyfix-v prices that stun as a veto.
  Reads (10,200 each): denyfix-a dev 52.4, hold 52.4 (51.4-53.4), x1 52.6 (51.7-53.6), x2 52.4 (51.4-53.4): **pooled
  52.5 of 30,600** (16,058 wins; dnw-min 15,946 on the same maps: +112, +0.37 points, every suite up). denyfix-v
  identical within 3 wins. bots/charybdis = denyfix-a.

- 19:17 **denyfix-a at 100k fuel** (f100, 10,200): **52.2 (51.2-53.2)**; OOF turns CAND 77,704 in 7,541 games, REF
  78,827 in 7,494 (dnw-min 51.4 on the same maps). T12 `alarm` launched (alarm field in every game; briefs/t12-alarm.md).

- 19:25 **Plan change**: main is at 531 (530's `stop_due` in combat/fight.cc: a winning enemy tribute is stopped only
  when the rounds to its last stop are within our steps plus one cooldown; unseen deferred enders remembered; a stun on
  a not-yet-due winning channel worth 0; plus contest judgement in economy/contest.cc). Main's dnw-min vs 530 at 100k
  read 49.0 of 40,120 (530 already covers the late stop). T13 builds `variants/denyfix-531` = 531 + the pieces 530
  lacks (alarm, F1, F2, F3, F5 where not redundant). Frozen REF `variants/chy-531`. Fresh suites: x3 (seeds
  61431400-61431414, 2x) and f2 (61431500-61431514, 100k).
- 19:25 **T11 chip stopped** (patches/chip-a.diff): 0.17 chips a game, ~9 camp damage a game; own tile is in a
  striker's reach most of the time and the slot gate passes only on the first hold turn. Three open bugs (woke() gate
  outlives an ally's fight; last-round re-wake unrecorded; one woken group). Not measured; closed as too small.
- 19:30 **Context: denyfix-a (529-based) vs chy-531** on hold at 2x (10,200): **48.9 (47.9-49.8)**; OOF CAND 1,260 in 614
  games, REF 1,167 in 669. 531 is ahead of our 529-based best, as expected from 530's own stop_due plus contest.
  chy-531 vs chy-ref (529) on hold at 2x: **53.6 (52.6-54.6)**, against denyfix-a's 52.4 there.
- 19:45 **T12 alarm-a** (on denyfix-a; patches/alarm-a-vs-denyfix-a.diff): the alarm now fits in 4,076 of 4,080 study
  team-games (was 2,420). Wins bit dropped while deny_hoards is off (readers ignored hoard alarms); own bits at 8x16 when
  they fit, else the alarm shares Willow's ally-record field (values above ally_codes are alarms; ally posts pause while
  one stands), else fewer longer steps keeping the 112-round reach (0.6% of games). Cause of the misses: Cassi & Issac
  (2 bodies, ~98% of drafts) and Willow's ally record left 0-3 bits. alarm-dev (10,200): **52.7 (51.7-53.6)** vs
  denyfix-a's 52.4 on dev: +0.3, inside noise, one suite. Not ported to denyfix-531 (stopped).
- 19:45 **T13 denyfix-531** (patches/denyfix-531-vs-chy-531.diff): 531 + deny_alarm (field carries altar, end step and
  the channeller's enemy index; winning tributes only; read as a synthetic sighting fed through ender_to_stop, so
  stop_due rules it), F1 (stun slots held for the channeller; no stunning dash for travel then), F2 (stop_within:
  pathing threshold per stop kind, fuel-gated, memoised per enemy, Chebyshev fallback), F3 (deferred ender forgotten
  when its tile is in sight without it or our lock is placed since), F5 (turn-end place_lock skips an altar whose
  winning tributes are not yet due; stun_worth negative on a not-due channel, by the channel the stop would waste).
  530's stop_due kept as the one timing rule. Possible flaw in 530 (not changed): stop_due returns due when no stop
  can land in time, so bodies run in at a channel they cannot stop; the alarm readers filter this out, visible enders
  keep 530's behaviour. Smoke 48.8% of 256 vs chy-531, 0 failed; OOF 43 in 21 vs 20 in 17. **Reads skipped at the
  user's request**; bots/charybdis = denyfix-531.

## Candidates

| Candidate | Change | A/B | Win % (95% CI) | Games | Notes |
|---|---|---|---|---|---|
| orbit-a | T2: feeders price the Prism's premium x q on groups within carry_reach (12) of its claim/tile, falling to 0 at 24 | orbita-dev (SPRT low, seed 101) | 49.9 (48.6-51.2) | 5,498 | H0 at 5.5k. Prism share r<=600 0.581 vs 0.576; un-shared ally captures within 12 of the Prism 138 vs 134 gems: allies moved a little nearer, the funnel still does not convert. Expected: the conversion is T3's. |
| front-a | T1: farm side weight from live enemy presence (dead enemies' respawn + spawn steps; fresh sightings bring them closer) | smoke | 23.8 (19.0-29.4) | 256 | sightings collapse play (see 15:20) |
| front-b | front-a variant (implementer's second form) | smoke | 41.4 | 256 | same failure, milder |
| front-a-nosight | front-a with sightings off: front moves back only while the whole enemy team is dead | nosight-dev (SPRT low, seed 103) | 49.5 (44.7-54.4) | 406 | H0 |
| chase-a | T5: chase entry needs kill worth per turn > the body's gem farm rate (smoothed best_value gem share); strike step_value = farm rate | chasea-dev (SPRT low, seed 104) | 50.4 (48.8-52.1) | 3,565 | H0. CHASEX ~5 a game |
| prem-a | T4: Prism premium on Monoliths (prism_paid_gems) + hand-over paths take cleared Monoliths; continuous health knee instead of the cliff; prism_dominant removed | prema-dev (SPRT low, seed 105) | 50.3 (47.7-53.0) | 1,333 | H0 |
| prem-m | T4 Monolith part only | premm-dev (SPRT low, seed 106) | 49.3 (42.7-55.9) | 217 | H0 (early stop) |
| relay-a | T6: holding Prism plans and posts its next group (new comms record); feeders price its premium there; funnel waits for the relayed Prism | relay-dev (SPRT low, seed 107) | 50.3 (49.0-51.7) | 5,273 | H0 |
| deny-a | T7: scylla's tribute denial (deny_late, deny_alarm, deny_watch, lock_first, deny_hoards) ported onto 529 | denya-dev; hold; x1; x2 | 50.9 / 50.9 / 51.3 / 50.3 | 10,200 each | best so far; pooled held-out 50.8 of 30,600 |
| deny-nowatch | deny-a with deny_watch off | dev; hold; x1; x2; f100 (100k) | 51.7 / 51.8 / 50.7 / 51.8 / 50.4 | 10,200 each | pooled held-out 51.4 of 30,600 |
| denyfix-531 | T13: 531 + deny_alarm, F1, F2, F3, F5 (530's stop_due kept) | smoke vs chy-531 | 48.8 | 256 | reads left to the user; = bots/charybdis |
| alarm-a | T12 on denyfix-a: alarm fits in 99.9% of games (wins bit dropped, shares the ally-record field) | dev | 52.7 (51.7-53.6) | 10,200 | +0.3 on denyfix-a's dev, noise |
| **denyfix-a** | dnw-min + T9: stun kept for the channeller, pathing walk estimate, remembered channels, late-stop gate on stun_worth / place_lock | dev; hold; x1; x2; f100 (100k) | 52.4 / 52.4 / 52.6 / 52.4 / 52.2 | 10,200 each | **best**: pooled held-out 52.5 of 30,600 |
| denyfix-v | denyfix-a with the gate as a veto | dev; hold; x1; x2 | 52.4 / 52.4 / 52.6 / 52.4 | 10,200 each | same as denyfix-a |
| dnw-min | deny-a with deny_watch, deny_hoards and lock_first off (late stops + alarm) | dev; hold; x1; x2; f100 (100k) | 52.2 / 52.0 / 52.2 / 52.1 / 51.4 | 10,200 each | pooled held-out 52.1 of 30,600 |
| escort-a | T10 on dnw-min: allies screen our winning tribute's altar, escort_worth in stun/kill values, break locks | escort-dev | 51.3 (50.3-52.2) | 10,200 | below dnw-min (52.2 on dev) |
| dnw-alarm | dnw-min with deny_late off | dev | 49.8 | 10,200 | late timing is the gain |
| dnw-nohoard | deny-nowatch with deny_hoards off | dev | 51.8 | 10,200 | |
| dnw-nolock | deny-nowatch with lock_first off | dev | 51.9 | 10,200 | |
| deny-nolock | deny-a with lock_first off | dev | 50.6 | 10,200 | |
| deny-noalarm | deny-a with deny_alarm off | dev | 50.0 | 10,200 | |
| conceal-a | T8: sight-aware altar/tile/time for long tributes | concealf-dev | 49.9 (48.9-50.8) | 10,200 | level |
| deny-b | deny-a without deny_hoards | denyb-dev (SPRT low, seed 109) | 50.5 (49.5-51.6) | 9,210 | H0 |
| orbit-b | T3 on orbit-a: funnel wait W = min(respawn, premium x cycle) near the Prism; prism_eta times live clears | orbitb-dev (SPRT low, seed 102) | 48.7 | 1,236 | H0. Prism share +1 pt, total gems r<=600 -14 |
