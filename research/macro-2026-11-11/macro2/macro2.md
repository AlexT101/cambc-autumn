# macro2: macro refactor of ocean (2026-11-11)

Lead: orchestrator subagent, ~8 hours, worktree `/home/ubuntu/wt/macro2`, branch `macro2-20261111`.
Brief: [macro2-brief.md](macro2-brief.md). Running log: [macro2-log.md](macro2-log.md). Implementation briefs:
[briefs/](briefs/).

## Outcome

**The goal (60%+) was not reached.** The best candidate is `bots/variants/macro2-lstep`, now in `bots/ocean`
(CHANGES 507-508, commits 5fd022d34 and c3e459e6e). It beats `variants/ocean-ref-b7c87cf` by three quarters of a
point: **50.76% of 51,200 games (95% CI 50.33-51.20)** at `--fuel 200000`, own drafts.

| Suites | Games | Win % (95% CI) |
|---|---|---|
| s-200001..030 | 15,360 | 50.8 (50.0-51.6) |
| held-out s-200031..060 + fresh s-200061..100 (made at the end) | 35,840 | 50.8 (50.2-51.3) |
| fresh s-200111..130 | 10,240 | 50.5 (49.6-51.5) |
| fresh s-200131..150 | 10,240 | 51.3 (50.3-52.3) |
| **all five ladder-v2 sets** | **71,680** | **50.81 (50.44-51.17)** |
| stress `--mix varied` v-200101..110 (not pooled) | 5,116 | 50.6 (49.2-52.0) |

lstep is four rule-derived fixes, each level on its own. The first three form macro2-combo (50.53% of the same
51,200; held-out 50.5%):
1. **Willow's heal order:** by farm time saved, urgent heals first (macro2-medic1, 50.2% of 24,496).
2. **Two casts on a double turn:** an enemy with two turns before ours may cast one slot on each (macro2-duelm,
   50.0% of 25,600).
3. **Hold cast:** a capture holder with no basic target casts at another group in reach (macro2-spells, 50.0% of
   10,240).
4. **No lethal camp flight:** `flee_camps` never walks onto an enemy-lethal step when a safe one exists.
   Found in a replay where a 228-gem Prism fled a 20-damage wolf into a one-cast kill. +118 wins paired with combo.

Out-of-fuel turns: 3939 vs 3511 over the five sets, in about as many games. The last set had a few long streaks;
it's worth a fuel census before a ladder submission. The 100k ladder budget is untested: every A/B ran at 2x fuel, as the
brief required.

Every A/B played CAND vs `variants/ocean-ref-b7c87cf`, `--no-test-draft --fuel 200000`, on generated ladder-v2
suites. The noise is about ±1 point at 10k games. Early screens used SPRT, 0.50 vs 0.52, each run with its own seed.
Later ones ran the full 10,240 games of s-200001..020, because A/Bs on this box take a few minutes.

## Design process

1. **Theory first** ([macro2-log.md §0](macro2-log.md)). The economy is labour-bound: gems per champion-round of
   work. Supply per group is fixed, so contested groups count double in the difference. Kills transfer bags.
   Enemy deaths open 60-round windows.
2. **Measure the mirror** (ref vs ref, 512-1024 games, debug D-line traces, extract.mjs). Then build one candidate per
   mechanism, each grounded in a rule, with no new tuned constants. Implementers wrote the code; each audited its own
   diff with a read-only auditor.
3. **Iterate on what failed**, with analysts: a replay watcher, a retreat anatomy, lock warfare, a farm-waste census
   and a fresh-eyes researcher.

## Every A/B result

| Candidate | Idea (mechanism) | Games | Win % (95% CI) | Verdict |
|---|---|---|---|---|
| macro2-plan | farm chain lookahead (each job valued with its best follow-up) | 1306 | 45.6 (43.0-48.3) | lost |
| macro2-heavy | team-throughput Golem/Monolith programme | 869 | 48.6 (45.3-51.9) | lost |
| macro2-fight | joint skirmish verdicts (ENGAGE/DISENGAGE over comms) | 3338 | 50.0 (48.3-51.7) | level |
| macro2-fight2 | engage-only verdicts | 2138 | 49.6 (47.5-51.7) | level |
| macro2-pair | Cassi & Issac as one stake | 634 | 46.5 (42.7-50.4) | lost |
| macro2-shop | EOQ shop timing | 2034 | 49.4 (47.2-51.6) | level |
| macro2-stand | stand initiative to the side not walking in | 1252 | 49.9 (47.2-52.7) | level |
| macro2-stand2 | double-turn commitment bet | 1555 | 49.3 (46.8-51.7) | level |
| macro2-medic | Willow attends the top camp-damage ally, plus heal value | 1326 | 48.8 (46.1-51.5) | lost |
| macro2-medic1 | Willow heal-value ordering only | 24496 | ~50.2 (held out 49.3-50.9) | level; in combo |
| macro2-mono | heavy programme on Monolith maps only | 1482 (Monolith suite) | 48.0 (45.4-50.5) | lost |
| macro2-monowin | mono, started only in enemy death windows | 1482 (Monolith suite) | 48.1 (45.6-50.7) | lost |
| macro2-lock | lockout siege (nearest k break together), carriers wait | 10240 | 46.8 (45.9-47.8) | lost |
| macro2-lock2 | siege without the carriers wait | 10240 | 47.6 (46.7-48.6) | lost |
| macro2-lock3 | carriers that bank anyway hit the lock every turn | 10240 | 49.9 (48.9-50.9) | level |
| macro2-duel | two-cast double-turn burst + Prism stun reserve | 10240 | 39.1 (38.2-40.1) | lost |
| macro2-duelm | two-cast double-turn burst model only | 10240 + 15360 held out | 50.0 / 50.0 (held out 49.2-50.8) | level; in combo |
| macro2-duelr | Prism keeps its stun off camps near enemy Prisms | 10240 | 39.3 (38.3-40.2) | lost |
| macro2-spells | camp cast on hold turns with no basic target | 10240 | 50.0 (49.0-50.9) | level; in combo |
| macro2-race | farm value x 1/2 when the enemy can arrive before our clear + hold | 10240 | 44.8 (43.8-45.8) | lost |
| macro2-commit | farm target kept unless new information arrives | 10240 | 48.6 (47.7-49.6) | lost |
| **macro2-combo** | **medic1 + duelm + spells' hold cast** | **51200** | **50.53 (50.10-50.97)** | **ocean 507** |
| macro2-held | combo + the escape plan counts a ready spell on every turn until cast | 10240 | 49.9 (48.9-50.9) | level; OOF 896 vs 511 |
| macro2-exits | combo + a hold exit check + a kill-bid lethal filter | 15360 | 50.3 (49.5-51.1) | level; never fired in reruns |
| macro2-healstay | combo + allies count a visible Willow's coming heal in heal-trip pricing | 15360 | 50.5 (49.7-51.3) | level (= combo) |
| **macro2-lstep** | **combo + flee_camps never takes an enemy-lethal step when a safe one exists** | **51200** | **50.76 (50.33-51.20)** | **best; bots/ocean (508)** |

## What failed and why

- **Farm planning (plan, heavy, mono, monowin, race, commit).**
  - **Solo:** ref's farm is near a local optimum. Chain lookahead made solo farming 2.1% slower.
  - **Heavy jobs:** they fire (first Golem capture at r222 vs r331), but they pull champions off the elk, wolf and
    cluster supply that pays more per round.
  - **Race (-5):** a step race on top of `home_ground`'s static spawn-walk ratio over-prices contest, and gave up
    own-side groups that clear slowly.
  - **Commit (-1.4):** ref's per-turn re-planning plus stickiness 1.2 beats commitment. Many "abandoned" walks
    still step toward the group reached next. Re-planning around respawns and claims pays.
- **Fight coordination (fight, fight2, pair, stand, stand2).**
  - **Joint verdicts** cut deaths (4.27 vs 4.60) but bought no economy.
  - **The pair stake** cost farm time and saved no lives.
  - **The stands:** the mechanic behind "healthy flinches" is turn-order parity. Each enemy gets two turns before
    our next every other round, so ref's they-strike-first test is exact there. Holding ground against the double
    turn gains nothing, because the flapping costs both sides alike.
- **Shop timing (shop).** Fewer trips buy farm time but stats arrive later; the two cancel.
- **Willow (medic).** Attending the top camp-damage ally halved her own camp damage and didn't raise healing.
  Ordering heals by trip value (medic1) is level.
- **Lock warfare (lock, lock2, lock3).**
  - **The pattern:** one-altar maps are 23% of games. Both sides lock the altar and spend most of the game locked
    out (mean 370/532 rounds for winner/loser). A ref lock takes a median 77 rounds from first hit to break.
  - **The siege worked mechanically:** 100 fewer lockout rounds a game, and locks fell within a round.
  - **It lost anyway.** With the carriers waiting, nobody was at the altar when it opened (73 gems per break vs 109,
    and 30% of breaks scored nothing). With farmers recruited, the farm time lost cost more than the faster breaks
    gained.
  - **Carrier-only persistence is level.** A lockout is symmetric, and the bags keep growing safely while locked.
- **Prism duels (duel, duelm, duelr).**
  - **The pattern:** big-bag Prism kills decide many mirror games. Prism-on-Prism kills of 100+ bags were 45 in 256
    games, and the victim lost 41.
  - **The diagnosis:** safety's one-window model was right. Death came from a capture hold in a dead-end pocket
    (no exit check after the payout), from enemies untracked after 3 rounds, and from one real gap (two casts on a
    double turn), which is now fixed in duelm (level).
  - **The reserve was the whole loss.** Keeping the stun off camps cut Prism camp stuns from 14-32 a game to 1-4 and
    lost 11 points. The Prism's Focus-scaled camp spells are the team's farm engine.
- **Camp spells (spells).** Ref already casts nearly every ready slot it usefully can. The uncast ready slots are
  ranged walks from 4 to 3 tiles for an extra basic, which pay more.

## Lessons

1. **Ocean vs itself is a near-mirror equilibrium.** Every structural change was level or worse, and the harms
   scale with the farm time they cost. Bag duels and lockouts look decisive, but they are rare and symmetric. Farm
   output accrues every turn.
   - The only gain came from four small, rule-derived fixes, each level alone. Combined, they give +0.76 over 51k
     games.
   - Each is a model or priority correction that fires rarely and costs nothing on the common turn. That kind of
     change is safe to stack.
2. **Caution loses in proportion to its cost.** The stun reserve cost 11 points, the race discount 5, the siege 2-3,
   and the pair stake 3.5. A rule that protects against a rare loss must cost near zero on the common turn.
3. **A pattern in losers' replays is not a lever.** Patterns A-C from the replay watcher (Prism duels, lockouts,
   piecemeal fights) and the farm-waste classes are real. But the loser's failures happen to the winner too, and
   fixing them reallocates time that ref already spends well.
4. **The mechanics that matter:**
   - Turn-order parity creates double turns.
   - Two casts on a double turn is a real model gap, now fixed, but level.
   - The Prism's Focus-scaled camp spells drive the economy.
   - Lock breaks convert only when bags are nearby.
5. **Process:**
   - A/Bs at 2x fuel finish 10k games in minutes. Use full 10k suites instead of SPRT once compute isn't the limit;
     the implementers are the bottleneck.
   - Checking identity on the games where a mechanism never fires (same outcome as ref vs ref) pinpoints where a
     loss comes from.
   - Splitting compound candidates into one change each (duel into duelm and duelr) is cheap and decisive.
6. **What's left:**
   - **Escape and hold with a two-window horizon:** the hold pocket, and escape counting held spells only on the
     first two ready turns.
   - **Enemy tracking past 3 rounds,** for cast reserves that cost nothing on the common turn.
   - **Draft or emblem changes:** out of scope here.
   The mirror suggests gains must come from value both bots leave, decided from the map. None found here survived.

## Files

- **Candidates:** `bots/variants/macro2-*`. They are gitignored, so the patches against ref are in
  [patches/](patches/).
- **Briefs:** T1-T15 in [briefs/](briefs/).
- **Running log:** [macro2-log.md](macro2-log.md). EXPERIMENTS.md has the macro2 table.
- **Analysis scripts** (scratchpad, not in git): lockout.py, lockbreak.py, sides.py, byaltar.py, ident.py, casts.py.
