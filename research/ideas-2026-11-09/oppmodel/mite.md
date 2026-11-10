# Mite reverse-engineering (mite-re, 2026-11-09/10)

Data: ~/tmp-offload/oppre/replays/mite/ (manifest.tsv = capture.db rows; file = match id). Decoded with
tools/replay/extract.mjs into ~/tmp-offload/miteRE/ana; per-game features feats.jsonl; tools in ~/tmp-offload/miteRE/tools/.
Sources: capture.db replays (our games, copied from big-arm) + `cambc matches download` for Mite vs other teams
(capture.db never downloads those). Download is rate limited (~0.2-0.4/s shared with fish-re), newest-first, Fish first.

## Versions
- Willow enters Mite's picks at 11-08 23:00 UTC; draft shifts again 05:00, 08:00, 11:00.
- From 11-09 12:00 UTC Mite's picks are 99%+ a fixed function of (map, side), independent of the opponent: treat
  12:00+ as the current version.
- 12:00+ Mite places altar locks: ~0.5-1.1 before r600 and 1.3-3 a game vs Fish/others (05:00-12:00: ~0.1).
  Mostly on multi-site maps, from r~400, not to cancel a tribute (11 of 129 during an enemy tribute).
- Priority encoding (11-08 README) still holds: quiet 1000+floor(20 hp/maxHp) (HoR/Marcella 1025+floor(24..)) matches
  98.8% of quiet turns; dead 1050; channel 18965; contact 100-d; alert 0; +2000 retreat. The +6460 kill flag is gone;
  new offsets 3095-3099 (hit a champion 35% of those turns, likely the new kill flag), 5095-5099 (= +2000+3000),
  195-199, 50, 4050.
  - +2000 turns: 80% carry 10+ gems, 29% under 40% hp; they still hit a champion 32% and step toward 34%.
    11.8% die within 5 rounds (contact 3.4%, quiet 0.5%). 52% of Mite's champion deaths follow a +2000 turn.

## Against us (2,409 games 11-09 05:00+, live-test versions): Mite wins 37-39%
- Mite loses short games (<600 rounds: 20%) and wins long ones (1200+: 53-61%).
- Altars: one-site 33%, 2 altars 42.5%, 3 33%, 4 37%.
- Losses are death-driven: in Mite losses Mite dies 12.7 a game vs our 5.0, and loses 160 gems to kills vs our 58.
- Mite's Prism is its carrier (+1.5 Focus/gem): dies 1.9 a game losing 154 gems a game.
- Mite tributes small and often (18.5 completions a game, mean 36 gems, 3.8 turns); feint cancels 2.0 a game with
  mean bag 125. We never waste stuns or locks on its feints.

## Locks: the strongest regularity found
- **Mite hits a lock only while carrying gems.** Mite champion-turns within attack range+1 of an altar with our lock:
  empty bag 0.3-0.6% hit the lock; with gems and no one of ours within 8, 43-56%; with one of ours within 4, 9-10%.
  Same in the 12:00+ window and against other teams.
- Mite never submits at a locked altar (0 tribute_blocked).
- One-site maps, us games: our lock is up 53% of rounds after r100. Mite's tribute rate while it is up: 0.008
  gems/round, against 1.46 while down. Mite carriers' bags grow (team carry 129 locked vs 210 unlocked; they bank
  when it breaks).
- First Mite hit on our one-site lock: median 36 rounds after placement (p25 15, p75 73); 4 hits, 1.35 hitters.
- After Mite breaks it, our next lock comes a median 35 rounds later (p25 16, p75 69).
- Mite wins 53% of one-site games where our lock is up <20% of rounds, 21% at 60-80%, 1% at 80%+ (confounded with control).
- Our locks: every champion buys one on spawn; place_lock locks any our-side/middle altar in reach and any visible enemy tribute.

## Body fidelity (Mt3p vs ocean-16d6f78; fresh one-site 120 maps, multi-site 200 maps)
- Lock dynamics match: body hits our lock only with gems (0.0% empty / 59% free / 4-12% contested), first hit median
  33 vs real 36, relock gap 35 vs 35, lock up 58% vs 53%, ~0 tributes while locked. fgate judges lock changes fairly.
- Gaps (tools/fidcmp.py): real games bloodier (one-site: Mite deaths 12.4 vs 9.6, ours 10.4 vs 5.7; gems lost 313/207
  vs 172/102); real Mite carries more in the field on one-site (mean bag 41-46 from r300 vs 21-28) yet tributes smaller
  bags (start median 21-30 vs 35-40) — no at-altar floor, contact within 4 stops it (43% vs 87% free); multi-site
  banking matches the body. Real feints more (manual cancels 3.65 vs 1.48 one-site). Real 12:00+ places locks
  (0.5-0.7 a game vs us), body none. Capture shares go to Vesper/HoR/Marcella in real Mite, Cassi/Tavi in the body.
- Not ambushes: our killers were seen by the victim in the last 3 rounds 90% (Mite's 84%).

## Mite's own locks (12:00+, 1,284 placements in 1,718 games)
- First lock round mostly 400-800 (p10 432, median 700); mid altars 61%, Mite-side 28%, ours 11%; 0 on one-site maps.
- Not a reach rule: in reach of an unlocked altar with a lock in hand, it places 0.05-0.1% a turn; 0.7% when one of
  ours is tributing there, 0.4% when one of ours with 150+ gems is beside it. Looks like deliberate trips to mid altars.

## Exploiter arms (all on ocean-16d6f78 + opp::mite stub forced on)
- mx-rl1 relock errand (one-site, nearest ally with a lock walks to relock the site from r30): REJECTED in smoke,
  57.1% of 240 vs base 76.7% against dvn1-Mt3p on one-site maps. Lock up 58→64%, gap 35→22, but captures −106 a
  game, deaths +1.7: the base already exploits the lock rule; a dedicated runner costs more than it gains.
- mx-lk2 lock-everything (from r30 lock any altar passed, Mite's side too): smoke 73.2% vs base 71.8% of 400 on
  multi-site (noise); Mite-side locks 0.41→0.86 a game. fgate 4 blocks (512 fresh units): fresh −0.59 ±1.08,
  Mite −0.49 ±1.59, Fish −0.68 ±1.28, ladder +0.24: REJECTED (no gain).
- Draft counter: our live drafts barely vary within a map (≤8-41 games with a pick change), so live data can't fit one.

## Mite body patches (diverse's Mt3p2fight / Mt3p3), fidelity (tools/fidcmp.py, fid-p3.txt)
- A bag that never brakes doesn't move deaths (one-site Mite/ours 10.2/6.0 vs real 12.4/10.4): the gap is engagement.
- Mt3p3's no-trips-on-one-site overshoots: at-altar 0.6-1.3% of rounds (real 3.5-4.5%), bag 114 by r600 (real 46),
  bag at tribute start median 143 (real 26).
- Multi-site: we capture 361 gems by r300 vs the body but 272 vs real Mite; real Mite contests our early farm.

## Kill edge: cohesion + item build (tools/mcoh.py, killctx.py, nuke.py, burst.py, stats.py, shopm.py, chase.py)
- Cohesion (mates within 5, Cassi/Issac partner not counted, r<=400): real Mite 1.50 vs ours 1.19 (Fish 1.54 vs 1.14);
  body 1.19 (one-site) / 1.09 (multi). At contact 1.63 vs ours 1.51. Our contact samples outnumbered (foes-mates>=1)
  39% vs Mite's 34%; deaths outnumbered the round before (r<=400) ours 74% vs Mite 65% (body games: ours 67-76%).
- Not numbers alone: at equal numbers our hazard vs real Mite is 2-3x the body's (healthy, f-m 0: .009 vs .003-.005;
  f-m +1: .010 vs .003-.007); Mite's own hazard is the same real vs body (.014 vs .011).
- Real Mite kills from >=50% hp within the death round 1.44/game vs body 0.66 / 0.30; ability kills of ours 2.80 vs
  1.35 / 0.77. Per cast at the same target health (median 0.85-0.89): Marcella Damage kills 14.6% vs 8.5%, Prism CC
  15.6% vs 9-11%.
- Cause: Mite's item build. At r600 real vs body (multi): Marcella focus 318 vs 220, maxHp 2670 vs 2059; HoR focus 195
  vs 117, maxHp 1970 vs 1631; Vesper str 286 vs 235, maxHp 2895 vs 2551; Tavi str 71 vs 121. Buys a game: Bruiser
  Emblem of Health Marcella 4.0 / Vesper 4.5 / Prism 1.7 vs 1.4 / 1.8 / 0.8; Vesper Greed Shard of Strength 3.6 vs 0.
- Retreat flag (+2000) chase value (observational): low-hp retreaters die within 5 rounds 43% when chased vs 24% held
  (quiet low-hp: 39% vs 31%); healthy retreaters (carrying) 5.4% vs 2.8%. The flag adds little beyond hp and bag.

## Mt3q arms (diverse) and map-matched ladder check (2026-11-10)
- multi1 (400 each): ocean beats Mt3q 74.0, Mt3qe (emblem order) 77.5, Mt3qc (cohesion) 80.5, Mt3r 83.2.
- Mt3qe moves Marcella maxHp and Tavi str toward real, but not Marcella/HoR focus; HoR and Vesper maxHp go the wrong way.
  Mt3qc's cohesion goes 1.12 → 1.38 (real 1.50). No arm moves our deaths (3.1-3.3 vs real 7.9) or ability kills.
- Map-matched ladder (Mt3q 256 games vs 1,069 real on the same 88 maps): Mite deaths match (9.8 vs 9.4), ours don't
  (6.0 vs 9.1). Mite capture gold +22% real; ours −8%. Mite's gold per share +12% early, +9% overall; ours +1-3%.
  Mite's gold per capture early is +15%: camp choice or Prospector. Late captures: Mite 34.1 real vs 28.7 body, ours
  31.5 vs 35.5.

## Marcella nuke exploit: mechanism check, not gated (2026-11-10)
- Real (451 games with Mite's Marcella): her ability kills 3.1 of ours a game, 2.69 of them on victims whose hp at
  round start was <= 2x her focus, 2.88 from within 4. Our champions spend 50.5 rounds a game within 5 of her at
  hp <= nuke, and die to her ability within 2 rounds 9.4% of those rounds (0.4% above nuke hp).
- Body (Mt3q, ladder 69 games / multi 101): 0.71-0.84 such kills a game; exposure at hp <= nuke only 15 rounds a game
  (her focus is lower), so a gate on Mt3q sees about a quarter of the live effect: under ~1 point, inside fgate noise.
- ocean's Safety already prices enemy casts by type, focus and reach (safety.cc compute_strike), so a Mite-only
  avoidance is a margin knob on an existing model. Not gated. Lead for main (all opponents): why Safety accepts
  9% two-round death risk from nuke-killable positions; check its cooldown belief for enemy casts.
- Data: 4,700 Mite replays in oppre/replays/mite (newest ~500 not decoded); mite.done written, downloader stopped.
