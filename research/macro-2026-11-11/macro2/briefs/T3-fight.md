# T3: team engagement verdicts (`bots/variants/macro2-fight`)

Read briefs/common.md (same folder) first and follow it. Candidate dir: `bots/variants/macro2-fight`, created with
`./copybot variants/ocean-ref-b7c87cf variants/macro2-fight` (unless the lead names another base).

## Why (measured on 512 ocean-vs-ocean games)
- 28.5 engagements a game; only 24% produce a kill. With a headcount advantage the bigger side fails to kill 85% of
  the time (+1 body: 13.4% kills vs 9.9% for the smaller side). What decides engagements is the pooled HP share of
  the champions present: share 0.6-0.8 -> 19% kill / 5.7% loss; 0.8-1.0 -> 38% / 4%; 0.4-0.6 -> 11% / 11%.
- Kills decide games: first kill wins 68%; net kills +1 at r150 -> 75%, +2 at r300 -> 89%.
- Deaths: healthy (median 85% HP), mostly empty-bag champions, 59% while walking, 67% mid-map, victim saw the
  killer in 80% of cases, burst in ~2 rounds; 21% alone; 26% (42% of 2+ round engagements) while retreating.
- Replay transcripts show superior local groups dissolving: in a "present 1v3" fight our Vendetta dashed in alone and
  died while its ally Varg kept hitting a camp then retreated; in a "1v4" the four retreated from one Vesper. Each
  champion decides alone (want_home / stand_lost_at, prey/chase_trade, strike search, each with its own sim and its
  own set of allies within `fight_ally_radius`), so allies present in the same skirmish reach different verdicts.
- Priors (research/EXPERIMENTS.md): pulling distant allies to fights lost (hunts 48.6%, "join your mate's fight" -2,
  rallies); "43% of allies in not-lost fight sims deal nothing within 5 rounds (farm 39%, bank 16%)". So: do NOT
  summon allies from afar. This track is about allies ALREADY present (within a few steps) acting on one shared
  verdict.

## Design goals (you decide specifics after reading combat/fight.cc want_home/prey, combat/plan.cc search,
## model/safety.cc fight sims, model/turn_order.cc kill bids, model/comms.cc layout, combat/support.cc)
1. A shared skirmish verdict. When visible enemies are within striking reach of us or of allies near us, compute
   one verdict for the local skirmish: the joint fight of every ally present (within a few steps, including ones that
   act later this round) against every enemy present (visible and credible unseen), with the existing fight sim.
   Verdict ENGAGE with a focus target (the enemy the joint sim kills first / the best kill value), or DISENGAGE.
2. Publish it so allies acting later read it this round (and next): use free comms bits (model/comms.cc lays out
   fields; ~13-16 bits are typically free: e.g. verdict + target enemy index + round tag) and/or the priority payload
   (readable only by allies in sight). Allies that see the verdict and are present follow it: ENGAGE -> they strike /
   chase the focus target and do not take a solo retreat unless their own death is imminent (lethal next enemy
   turn); DISENGAGE -> they all leave rather than some staying. Allies busy with high-value work (a capture paying in
   1-2 rounds, a winning tribute) keep it unless the verdict needs them.
3. The verdict should use pooled force (effective HP x damage, stuns, the initiative of who acts first this round)
   rather than headcount; derive thresholds from the sim's outcome, not new magic numbers.
4. Keep cost bounded (one verdict per skirmish per round, recomputed by whoever acts first; others reuse it).
5. debug_block traces: verdicts, focus target, followers, outcome.

## Not in scope
Farm/economy, banking, shopping, the draft, emblems. Don't retune existing constants.

## Done when
Builds; three local games against variants/ocean-ref-b7c87cf run to completion with no bot errors; auditor's
findings addressed. Report what you built and where, and what to measure (kills/deaths per game, kill rate in
numbers-advantaged engagements).
