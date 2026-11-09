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
