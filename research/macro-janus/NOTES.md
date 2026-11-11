# macro-janus (JANUS, macro-o8): macro refactor of charybdis (2026-11-11)

Reference: `bots/variants/charybdis-ref` (= bots/charybdis at the start, 81fc6f968). Every A/B: `tools/ab.py CAND
variants/charybdis-ref --no-test-draft --fuel 200000`, fast runner native, release builds, own drafts.
Suites: `maps/macro-dev` (5,120 fresh ladder-v2 maps, 10,240 games), `maps/macro-holdout` (1,280 maps) and
`ladder,gen,fresh` for confirmation.

## Mirror study (256 ladder games, chy vs ref, identical bots)

- Time (winner / loser): move 25.6/27.4%, move with bag 22.5/21.1%, camp 17.5/15.1%, dead 5.7/13.6%, hold 7.3/6.5%,
  recall 5.8/5.1%. Deaths 3.4 vs 8.6 a game, kills 8.5 vs 3.4.
- Recall cycle: recall channel 5.8% + walks out of spawn (from:spawn 12.3%, from:recall 9.1%) = ~27% of alive time.
  Half of completed recalls start at >= 90% health (shop or fast travel).
- Supply is not the limit: gem groups sit alive and asleep 53% of rounds (mid 46%). The economy is labour-bound.
- Teams farm their own half: 7.6% of alive champion-rounds in the enemy half at equal numbers, 15% at +1/+2 alive.
- Prism deaths decide: the team whose Prism dies first loses 66 of 73 games with a Prism death (90%). First Prism
  death median round 335; the victim outnumbered within 8 in 53%, even 32%; killed by the enemy Prism in 66%.
  64% of all Prism deaths happen with the victim's Focus under half the enemy Prism's (8 rounds before).
- Prism hazard (P(death within 10 rounds) with an enemy within 12), by local numbers (allies+self minus enemies
  within 8): even Focus +2: 0.7%, +1: 1.3%, 0: 2.0%, -1: 4.3%, -2: 8.8%; dominated (< 0.5x Focus): 4.5% .. 32%.
- Kill share in fights with kills by numbers present (within 8 of the first hit): -2: 0.35, -1: 0.41, 0: 0.50,
  +1: 0.59, +2: 0.65.
- Endgame: the first team to a winning bag (tributed + one bag >= 1000) wins 116 of 123 (94%); median 29 rounds from
  it to the end, mean 119. Winner Prisms' big tributes are cancelled often (stun 275, manual 166, lock 104 vs 79
  banked over 128 games): long channels at contested altars.

## Experiments
- Prism Focus ratio over Prism-alive rounds (both alive): contested (0.5-2x) 62%, dominant 15% (82% of those in
  games the dominant side wins; median bag 415), dominated 15%, enemy Prism dead 8%.
- Isolated Prisms: 526 episodes (no teammate within 6, seen by an enemy, 2+ enemies within 10); it died within 15
  rounds in 10%.
- Prism spell uptime: 9.1 casts per 100 alive rounds against a cap of 25; when a slot is ready, no live camp is
  within 4 in 68% of turns; with one in range it casts in 31%.
- Analyst study (scripts in the scratchpad `study/`): 128 distinct games (side-swapped copies are byte-identical).
  Surviving Prism of a one-Prism-dies exchange: its team won 122/129. Team that lost more gems to deaths won 13%.
  43% of losers' deaths are to an enemy Prism carrying 300+ (70% of those victims carried nothing, 82% had seen it
  in the previous 5 rounds). Reinforcements: of ~0.95 allies 9-16 tiles from a fight's first hit, 0.13 join.
  Prism tribute success by bag: <50 95%, 50-149 80-91%, 150-399 23-30%, 400+ 6-12%; non-Prism 87-91%.

### E1 jn-bank (Prism economy relative to the enemy Prism)
Enemy Prism Focus estimate (last seen + growth at a mirror rate), premium saturating at the 2x dominance line,
bank when the enemy Prism is dead long enough or banking leaves us even, dominated Prism banks (flags
saturate_premium, bank_window, bank_dominated). Smoke 45.3% of 256.

### E2 jn-hunt (team converges on an isolated enemy Prism)
Isolated (no other enemy within 6, possible boards counted), >= 2 fit hunters within 8-10, two-turn damage >= its
effective health after its burst, burst kills at most one; prey() takes it, enemy Prism kill worth 2x life_value,
want_home's lost-stand exit skipped only with no other enemy able to hit us. Debug 256: fired in 27 games, 34 hunts,
hunted Prism died within 15 rounds in 18 (53%). Smoke 50.4% of 256.
Results (dev, vs ref, 2x fuel):
- jn-bank (all three parts): SPRT(0.50/0.53) H0 at 423 games, 47.8%. Lost.
- jn-bank-p2 (premium saturation only; bank_window, bank_dominated off): SPRT(0.50/0.52) H0 at 1,282 games, 50.6%.
- jn-hunt: 50.05% of 10,240 (full run). Level: fires in ~10% of games and the hunted Prism dies in about half of
  hunts, but nothing moves the win rate.
- Note: A/Bs run at ~1,500 games/min on this box when it is free: a full dev run takes ~7-10 min.
- Landscape probes (one constant each, stopped at ~2,000 games, ±2.2): life_value x2 49.9, x0.5 50.4; mid_exposure
  1.0 44.4 (mid groups matter a lot), 1.8 50.9. The fight-life price is flat; the mid weight is at or below its
  optimum's plateau.
- jn-art (Prism free casts at own-side/claimed camps on walking turns): Prism casts 8.0 -> 8.8 per 100 alive rounds
  after the audit's gates; SPRT(0.48/0.52) H0 at 795 games, 47.9% (pre-audit snapshot). Dropped.
- jn-turtle (respect a dominant enemy Prism: farm/chase/walk-out zone around its last sighting when its two casts
  kill us, unless 3 of us are near): SPRT(0.48/0.52) H1 at 234 games, 51.3%. Full run follows.
- SPRT caution: with --sprt-min-games 200, jn-turtle-a (pre-audit) accepted H1 (0.52 vs 0.48) at 234 games, then
  read 49.6% at 1,115 games of a full run; jn-turtle-bd (+ dominated banking) accepted H1 at 205 games. The paired
  variance estimate is unreliable on a few hundred games: later screens use --sprt-min-games 1000-1500.
- The box is shared by ~8 programmes from ~20:30: throughput fell to ~100-150 games/min for all of ours together.
- Prism-vs-Prism openers (first Prism->Prism hit of an engagement, outcome within 15 rounds), by the opener's
  Focus ratio: the weaker Prism (< 0.8x) opening with its stun died 67 times and killed 3 (33 neither); opening
  with the ground spell it died 23, killed 6. The stronger Prism (> 1.25x) opening with the ground spell killed
  46, died 4. A weaker Prism that engages the stronger one is nearly always the one that dies.
- jn-turtle (final, after the audit): SPRT H0 at ~2,000 games, 50.2%. Level: the zone fires on 1.3% of champion
  turns (94 of 256 games), mostly in games already lost.
- Ablations (one subsystem off, SPRT 0.48/0.52, min 1,000 games; ~2,000 games each): no chase (prey() off) 44.3%;
  no Willow/Prism support pairing 47.1%; no comeback cook 50.0%; no opening plan 50.9% (running).
  Chasing is worth ~6 points and the support pair ~3 in this matchup.
- More ablations (stopped early, the box is busy): no opening plan 50.4% (~4,000 games, level); no siege 48.3%,
  no shopping-only trips 51.5%, no dash hand-overs 49.6% (~500 games each, noise); no contest ~48.8%.
- SPRT note: with P0/P1 = 0.48/0.52 the test only asks whether CAND is above 50% (the midpoint); "H1" at ~1,000
  games means little. Screens that stopped: jn-duel-a (pre-audit) 50.4% of ~850, no shopping-only trips 50.9% of
  ~1,700, carried-gem premium x1.5 50.1% of ~1,900, x2 51.8% of ~760 (probes of one constant).
- Full-run corrections (the earlier counts were partial): jn-turtle-b (final turtle) 50.0% of 10,233; no opening
  plan 50.6% of 10,207; no chase 44.3% of 10,229; no support pairing 48.0% of 10,221.
- Fuller runs: carried-gem premium x2 50.0% of 10,240; no shopping-only trips 50.1% of 8,886; jn-bank-p2 49.6% of
  8,952 (stopped). All level.
- jn-mono (a cleared Monolith goes through the Prism funnel: keep bonus, 'G'/'L' takeovers, leave-for-Prism, Prism
  pick-up; off on monolith_only maps): 50.0% of ~7,000 (pre-audit snapshot). Level: the Monolith is rarely cleared.
- jn-duel (our weaker Prism never trades with a stronger one: no basic attack or turn end inside its reach when its
  two-turn burst kills us and ours does not kill it; a stun only as an escape), post-audit snapshot: 49.5% of
  10,240. Level: the weaker opener is usually already caught.
- jn-bank decomposition (each part alone, SPRT min 2,000): bank_window alone (the Prism banks while every enemy
  Prism is dead long enough, or when banking leaves it at least even) 46.4% of 2,068, H0; bank_dominated alone
  49.8% of 2,047, H0. Banking the hoard even in a safe window loses ~3.5 points: its Focus is worth more than the
  score it locks in.

## Conclusion

No candidate beat the reference: `bots/charybdis` is left equal to `variants/charybdis-ref`. Every measured
change sat within about a point of 50% over 10,240 dev games, except those that removed or cashed in something the
bot already does well (chasing, support pairing, the Prism's hoard), which lost.

What the mirror says decides games (and so where a 60% bot must differ):
- The first Prism death decides 90% of games; the surviving Prism of a one-Prism exchange wins 122/129. Prism duels
  are one-cast affairs (Focus >> Prism health), and the weaker Prism that engages dies (67 to 3 when it opens with
  its stun).
- Kills transfer bags; the team that loses more gems at death wins 13%.
- Fights are decided by local numbers (kill share 0.35 at -2 to 0.65 at +2) and initiative (70%), and
  reinforcements almost never arrive (0.13 of 0.95 nearby allies join).
- Champions walk ~60% of alive rounds; ~27% of alive time is the recall/spawn cycle; supply is idle about half the
  time. Mid groups are the contested supply (mid weight 1.0 instead of 1.36: -6 points).

Why the changes were level: each one fires in a minority of games or turns (hunt ~10% of games, turtle 1.3% of
turns, free casts +0.8 casts per 100 Prism rounds), mostly in games already decided by the first Prism duel; the
always-on changes (premium scale, banking, shopping, opening plan) either cost the hoard or move nothing in the
mirror's flat landscape.

## Open leads
- The first Prism duel itself (median r335, Focus ratio near 1): bag size wins 70% of them, and more allies within
  8 16 vs 8. A design that makes our Prism's bag larger at that moment, or arranges the duel where our numbers are
  higher, attacks the 90% statistic directly. Neither cohesion nor hunting as built did.
- The recall/spawn cycle (27% of alive time; half of recalls at >= 90% health) is the largest block of
  non-farming time; its pieces are individually priced, but no one has re-planned the cycle as a whole.
- Chasing is worth ~6 points and the Willow-Prism support pair ~3: extending what makes them work (kills on the
  run; keeping the Prism healthy and accompanied) to teams without Willow is untested.

## Late probes and held-out checks
- fight_ally_radius 4 -> 6 (fight sims count allies within 6): 50.5% of 10,240 dev; held out (macro-holdout 2,560 +
  ladder/gen/fresh 1,280) 49.4% of 3,840.
- No opening plan: held out 49.8% of 3,840 (dev 50.6% of 10,207).
Both level, as every other candidate.
- Retreat-line probes (dev, 10,240 each): hurt_retreat_ratio 2.2 49.9%, 5.0 50.0%; hurt_health_fraction 0.3 50.7%,
  0.6 49.9%. Flat.
- jn-duel final build (stun on the stronger Prism banned as well; its first escape version had raised weaker-stun
  openings 96 -> 129-136 in smokes, our Prism still dying two times in three): 49.5% of 10,240.
- Territory/reach probes (dev, 10,240 each): own_ground_share 0.60 49.7%, 0.76 49.2%; pick_up_radius 10 50.5%;
  help_radius 9 49.4%. Flat: the reference sits on a broad plateau in every constant probed.

## Addendum (22:15-22:50): an escort partner for Prism teams without Willow
- jn-escort: with a Prism and no healer drafted, the highest-base-health melee ally (else the highest base health;
  not Issac) is the Prism's partner; when an enemy is seen and the Prism is visible beyond 2 tiles (Willow's follow
  distance), it steps to within 2 of it after its strikes, guard and chase have had their turn; no heals, no Willow
  caution. Built minimal (no support requests, the Prism's side unchanged). Smoke 52.3% of 256; dev 49.6% of 10,240.
  It acts only in the ~24% of Prism teams without Willow, so its effect there is about four times the overall delta
  (roughly -1.5, inside noise). Not shipped; bots/charybdis stays equal to the reference.
- jn-escort2 (escort also converges when an enemy it sees is within 8 of the Prism, Prism within 10, using the
  Prism's told tile): 49.61% of 10,240, the same 5,080 wins as jn-escort; the new trigger changed no game
  outcome (unverified whether it fired). Not shipped. Lead left open: the Prism posts no support request without a
  healer (support mailbox only runs for a Prism+Willow pair), so a full escort needs that path in comms.
