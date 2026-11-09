# fish-re notes (Intercontinental Fish), started 2026-11-09 22:10 UTC

Data: ~/tmp-offload/oppre/replays/fish/ (5,144 capture.db replays since 11-07, list.tsv; dl/ = Fish vs non-Mite teams being
downloaded slowly). Decoded: ~/tmp-offload/fishre/ana2 (latest Fish, since 11-08 16:00: 490 vs others + 500 vs us), ana (11-07).
Archive extract (all Fish games 11-07..09, per-game summaries): ~/tmp-offload/fishre/arch/ + arch.pkl. Tools ~/tmp-offload/fishre/tools/.
"stellar best girl" = our live scrim team. Fish's draft table last changed 2026-11-08 ~16:00 (15 map-sides): latest version from then.

## What decides Fish's games (archive, since 11-08 16:00)
- Fish win rate: us 37%, Mite 47%, test4 68%, BattleCats 72%, Trzy 84%, Sponge 84%.
- In every matchup a Fish loss looks the same: Fish deaths ~6 -> 12-15, Fish kills ~11 -> 4, gold gap from round ~200.
- Early kills decide it: vs us Fish wins 10% when down 2+ early kills, 66% when up 2+ (Mite 18/86%, test4 20/89%).
- Deaths (replays vs us): we die 18/game in games Fish wins, 5 in games we win; >half of those from >80% health within 5 rounds.

## Big bags and big tributes (replays vs us, latest Fish)
- Fish's 10+ turn tributes: 2.4/game, mean bag 282, median 19 turns; 54% complete (lock 17%, stun 16%, Fish's own cancel 16%).
  ~207 gems/game come from them. Fish wins 17% of games with none completed, 72% with 3+.
- Only 21% of them are ever hit by us; 1 of 1,128 ended in the channeller's death. When hit, Fish cancels itself within 0-1
  rounds in ~27% (the rest mostly our stun first): it is not a free kill.
- After a cancelled Fish big channel the bag is never banked in 45-60% (game over or carrier killed); otherwise banked a
  median 47-71 rounds later. Uncancelled ones complete 61%.
- At their start one of ours holds a lock 86% of the time; a holder within (turns left + 2) of the altar 70%; within 8 only 29%.
- FIDELITY GAP: the Fish body (spar-dvn1-Flp) makes 0.66 such tributes a game against the new base locally (real Fish 2.4).
- Our big bags (>=100) sit on Prism: 0.67 episodes/game, ~365 rounds each; 26% end with Fish killing the Prism (~45 gems/game
  handed over; killers Marcella 28%, Vesper 26%). In games Fish wins, 55% of our big bags die. Examples: our Prism stuns
  Marcella (immune), stays in range, Marcella's 2x-Focus spell one-shots it (885, 1540 damage).

## Fish's builds (latest version, shop events): unchanged from FISH_MODEL 3.2
- Vesper 125 shards/game (~14 Bruiser emblems), Marcella 83 (Focus 63%), Vendetta 59, HoR 32, Cassi 13, Issac 9, Willow 5.

## Exploiter (bots/fishx = variants/ocean-16d6f78 + stub posterior, model/opp_class.{h,cc}, model/fishx.h)
- fx1-deny: CHANGES 485's removed timed lock + 100-gem deny (channel_to_deny, lock_plan), only while fishx::on. fgate started 23:05.
- fx1-deny on Flp bodies (fgate, stopped at 3,840 fresh units): -0.28 ±0.59; fresh Fish +0.09, Mite -0.65.
- fx2-denyc = fx1 + comms deny record (a seen enemy channel >= deny_gems posts altar + last round; a teammate
  holding a lock that can reach in time adopts the timed lock). Flp (stopped at 1,792): -0.49 ±0.99, Fish -1.31, Mite +0.33.
- Both restarted on Flp2 (the diverse agent's fidelity body: FISH_MODEL 8.3 banking + Fish emblems).
- Flp2 vs real: tributes close (Fd10+ 1.64/g vs 2.36). Biggest gap is kill pressure: our deaths 6.5/g vs 9.6 real,
  burst deaths with a Fish body 1-4 tiles away 4 rounds before 0.57/g vs 1.8; Marcella kills 1.5/g vs 2.7, Vendetta 1.0 vs 1.6.
- Fish's manual tribute cancel: 0.35%/round unhit, 10%/round in a round it is hit (24-37% under half health).
  A hit Fish big channel completes 9% vs 61% unhit, mostly through our stun (51%).
- Deny arms parked (coordinator, 2026-11-10). Mechanism check, fx2 vs Flp2, 256 ladder games: Fish's big tributes
  are cancelled more often (lock 0.15->0.25/g, stun 0.16->0.29), but Fish restarts them, so they complete
  1.02/g both ways with 182 vs 184 gems.

## Deaths (latest Fish vs us, 544 games)
- Death hazard within 5 rounds, by foes-mates within 5 and health, is the same for Fish and for us
  (e.g. foes-mates +2: .105 us vs .108 Fish; at health<.5 and +2: .48 vs .37 for Fish). Fish's
  reactions when outnumbered match ours too (moves away 38-45%).
- The gap is how many bodies each side has at contact. Fish's cohesion (same-team bodies within 5, not
  counting the Cassi/Issac partner) is 1.54 vs our 1.14 (others' 1.31). We are outnumbered at contact
  more often: 43k vs 37k samples at foes-mates >= 1; Fish is at <= -2 25.7k vs 16.9k.
  Early (r<=400) 33% of our deaths come outnumbered vs 18.5% of Fish's.
- Mechanism (FISH_MODEL 11): Fish joins and never partitions (a later co-decider follows the earlier
  one's group 89-91%). Flp2's cohesion is 1.20, like ocean's 1.21: the body spreads out. This is the
  likely cause of its kill-pressure gap (sent to diverse).
- Hidden Fish bodies near a seen one do not raise our hazard, so an "unseen pack" prior in Safety is not supported.
- Fish leads on earned gold early: +50 at r100, +73 at r200, level by r400, -91 at r600 (vs others
  it leads +207 at r200 and +693 at r600).
- Kills before r400: Fish dies to camps 0.42/g (15% of its deaths) vs our 0.19/g. Fish's Marcella makes
  0.66 kills/g early, HoR 0.48, Vendetta 0.38.

## Handoff for fish-coh (2026-11-10)
- bots/fishx = variants/ocean-16d6f78 plus the following:
  - The opponent classifier (model/opp_class.{h,cc}, opp_token.h, opp_tables.h from variants/ocean-opp, v2: +71 fuel a turn). Its hooks: `#include "opp_class.h"` and `opp::observe(*this);` at the end of World::update in model/world.cc; `if (side == 1) opp::note(b.index, priority);` in World::read_priorities; and `#include "model/opp_class.cc"` in unity.cpp.
  - The switch, model/fishx.h: `fishx::on(world)` is true when the posterior's Fish share is at least `fish_on` (0.8). `params::opp_fish_stub` >= 0 overrides the posterior (1 forces the arm on, 0 forces it off); fishx's default is -1 (use the classifier). Local Fish bodies read as "other" (they write ocean's priorities), so freeze gate variants with opp_fish_stub = 1.
  - The parked deny arms, each behind fishx::on:
    - lock_plan_turn, channel_to_deny and lock_plan in combat/fight.cc, with the entry points in bot.cc;
    - a comms "deny" record (model/comms.cc, laid out after the other fields) with post_denial and adopt_told_deny.
    To start clean, delete them, or copy variants/ocean-16d6f78 and take only the classifier, the hooks and fishx.h.
- Frozen copies: bots/variants/fx1-deny, fx2-denyc (both with stub 1; variants/ is gitignored).
- Scripts in ~/tmp-offload/fishre/tools/:
  - fl.py is the loader: `games(filt, limit, rounds)` over the decoded real replays. With env LOCAL=<extract.mjs --out dir> it reads an ab batch (-12: Fish body is team B).
  - pairs.py measures cohesion and pair proximity.
  - hazard.py gives the death hazard by foes-mates and health; cohesion.py gives mates within 5 and the reaction when outnumbered.
  - killctx.py gives kill contexts (RMAX=); hidden.py, econ.py, denymech.py, tributes.py, bagkills.py, deaths.py us, ourdeaths.py.
- Data:
  - Real replays decoded in ~/tmp-offload/fishre/ana2 (latest Fish since 11-08 16:00: ~500 vs us + 490 vs others) and ana (11-07). The raw replays are ~/tmp-offload/oppre/replays/fish/ (list.tsv) and the dl/ downloads (Fish vs non-Mite; slow worker, PID in ~/tmp-offload/fishre/dl.pid, done file oppre/replays/fish-dl.done).
  - Local decodes: ~/tmp-offload/fishre/anaL (base vs Flp), ~/tmp-offload/diverse/flp2/ana (base vs Flp2), ~/tmp-offload/fishre/anaX2 (fx2 vs Flp2).
  - All Fish matches since 11-05: ~/tmp-offload/fishre/fish_matches.tsv. Archive extracts: ~/tmp-offload/fishre/arch/.
- Keep replays in an ab run with `--keep-replays 0`, then decode with `node tools/replay/extract.mjs <batch> --out DIR`; fgate prunes its replays.
