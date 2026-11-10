# Cohesion exploiter (fish-coh), started 2026-11-09 23:20 UTC

Builds on fish-re's finding (fish.md "Deaths"): Fish isn't better in fights at equal numbers, but it packs (1.54 mates within
5 vs our 1.14), so we meet it outnumbered. Tools: ~/tmp-offload/fishcoh/tools (iso.py, contact.py, econ.py, dctx.py; they
read fish-re's decoded live games, or `LOCAL=<extract dir>` for local batches). Big files: ~/tmp-offload/fishcoh/.

## Live data (544 latest-Fish games vs us, r20-400)
- Nearest teammate (Cassi/Issac partner excluded) within 2: Fish 52%, us 39%. Beyond 8: Fish 16%, us 25%.
- Early deaths are about level: 1,530 Fish vs 1,579 ours. When we die, our nearest ally is about as near as Fish's
  (within 5 at death-2: us 59%, Fish 62%), but foes - mates within 6 is >= 2 in 38% of ours vs 27% of Fish's.
- Our contact samples re-weighted to Fish's foes-mates distribution, at our own hazard (fish-re's hazard-us.txt):
  0.0423 vs 0.0487 deaths a sample, about 13% fewer deaths in contact; most of it from foes-mates >= 2.
- Fish's camp logit (FISH_MODEL 7.2) barely rewards allies (ally_closer +0.46, ally_recent -0.57): its packing comes
  from staying on its own half (logshare +2.4), shared camp memory and joining fights under way.

## Change (bots/fishx)
- farm.cc: a group's value x cohesion(g), the group's centre's distance d to the nearest live ally's anchor (its
  claimed group's centre, else its tile seen within 2 rounds or told within 6): 1 at d <= coh_near (6), linear down to
  coh_floor (0.75) at coh_far (14) and beyond. A discount only, so every prune bound in farm stays an upper bound.
  Off in the first round (the open plan). params::coh_mode 1 = while fishx::on, 2 = always.
- params::fishx_deny (false): the parked deny arms (fx1/fx2) are off in bots/fishx from here on.
- Arms: variants/fc1-coh75 (coh_mode 1), variants/fc2-coh75 (coh_mode 2).

## Mechanism, 256 ladder games each (ours = O)
| | vs Flp3 base | vs Flp3 fc2 | vs Flp4 base | vs Flp4 fc1 | vs Flp4 fc2 |
|---|---|---|---|---|---|
| our mates within 5 (r<=600) | 1.20 | 1.30 | 1.20 | 1.31 | 1.30 |
| body's mates within 5 | 1.19 | 1.22 | 1.50 | 1.52 | 1.52 |
| our deaths / game | 5.8 | 6.7 | 6.6 | 5.9 | 5.8 |
| body deaths / game | 10.7 | 10.6 | 11.6 | 11.6 | 11.3 |
| our earned gold @400 / @800 | 2369 / 4839 | 2254 / 4653 | 2295 / 4847 | 2299 / 4853 | 2311 / 4787 |
| our win % | 74.2 | 74.2 | 75.8 | 78.5 | 80.9 |
- Against a body that spreads out (Flp3), cohering costs ~5% of gold and adds deaths, mostly Cassi/Issac, and healthy
  ones in fights where we have the numbers (0.55 -> 0.88 a game). Against a body that packs like live Fish (Flp4),
  it saves 0.7 deaths a game at no gold cost.
- So it is an exploiter: it pays against an opponent that packs (Fish; Mite also packs, 1.50 vs our 1.19 per mite-re).

## Fresh-map check and gate (2026-11-10)
- Fresh slice f0 vs Flp4 (256 each, all replays): fc1 82.4% vs base 77.7%; our mates within 5 1.17 -> 1.27, our deaths
  5.4 -> 5.1, Flp4's 10.1 -> 9.4, gold level (4,663 vs 4,662 at r800). The mechanism moves, a little.
- fgate vs ocean-16d6f78 at block 34 (4,352 fresh units each): fc1 fresh -0.22 ±0.70 (Fish +0.03, Mite -0.48, ladder
  +0.56); fc2 -0.76 ±0.82 (Fish -0.69, Mite -0.84, ladder +0.38). Both stopped: level for Fish, below zero always on.
- Verdict: farm-pick cohesion is not a lever. Untried: travelling as a pair (escort) or declining contact against a
  seen pack bigger than ours; the hazard data (equal at equal numbers) bounds either at ~13% of contact deaths.
