# demeter: why the top teams out-farm us, and what to test (2026-10-29)

Ladder games from big-arm's platform capture (2026-10-27..29), decoded with `tools/replay`. "Us" is the ladder team
"newer team". The sets:

| Set | Distinct games |
| --- | --- |
| us vs Intercontinental Fish | 112 |
| us vs prism best girl (pbg) | 69 |
| us vs Mite | 31 |
| Fish vs pbg / Ad Astra / Mite | 93 |

The ladder replays many byte-identical rematches (540 files, ~304 distinct games), so count distinct games.

A replay-behaviour workflow of 5 analysts plus 3 skeptics re-checked every behavioural claim; the figures below are the
verified ones. Everything is in `replays/bigarm/` (gitignored):
- `repl/`: replays.
- `meta.json`: names, maps, picks.
- `narrative/`: `narrate.py` output.
- `workflow-reports.json`: full reports and verdicts.
- `crew-call-workflow.json`: crew-call designs, critiques, sizing and the kite check; scripts in `scripts/crew/`.
- `scripts/<analyst>/`: their scripts.

Data bug found: in `replays/.analysis/maps/*.json`, 112 of 1340 groups list gems that do not match their camps (e.g. a
lone gold cluster listed at 43 gems). The `side` label also disagrees with walking distance on 127 of 817 groups, and
self-mirrored jackpots are labelled 0, not -1. Splits by group gems or `side` from those files are unreliable; use
walking distance and paid shares.

## The gap

- **Draft ruled out.** demeter forced to Fish's drafts (`bots/variants/demeter-fishdraft`), each against `bots/idle`,
  326 maps, both sides: it collects fewer gems (−4 @150, −11 @300, −29 @600), earns less gold, and reaches 1000 3.1%
  slower. The gap is behaviour.
- **It is the opponent, not raw speed.** On the 45 ladder maps in both sets, capture gems:

  | | demeter vs idle | us on the ladder | top opponents |
  | --- | --- | --- | --- |
  | by r150 | 132 | 78 | 110 |
  | by r300 | 300 | 178 | 223 |

  `solo.py` cannot show most of what follows.
- **Small groups are level.** On groups under 30 gems and own-side wolves/clusters we convert damage as well as Mite
  or Fish, and lead by r300. The gap is big striker groups (Elk/Golem) and big middle gem fields. Elk/Golem capture
  gems r1-300: 70 vs 121 (Fish), 57 vs 114 (pbg), 68 vs 86 (Mite). Golems: 2.8 vs 16.8 and 0.5 vs 23.7.
- **Crews.** Each body sees a cluster (allies linked within 4) of this size, r1-150: Fish 3.5 vs our 2.2, and our team
  first splits at a median r8 vs r26. Top teams bring 4+ champions to 67-78% of their Elk/Golem captures; we do 24-33%.
  We start Elk/Golem groups alone 5.5 times a game and finish 47% of them. In 2.1 a game an ally within 12 tiles never
  joins. Fish's pairs are not fixed: crews re-form on targets. Nearest teammate: 7.2 vs 5.0 tiles.
- **Contested groups.** Groups where we did over half the damage but the enemy captured cost us 74 gems a game
  against 22 the other way (28.5 vs 3.9 by r300). By cause:
  - left standing in a fight: 18
  - cleared, never held: 10
  - left for another camp: 9
  - held, then contested off: 7.5
  - held, then left before payout: 7.5

  With an enemy within 4 at our clear we lose 29% of those groups (Fish 12%). With 3+ of ours there we still lose 25%
  (Fish 1%): our champions walk off at ~0.8 hp with even numbers instead of keeping enemies off the tiles.
- **Bags.** Tribute counts are equal; ours are smaller (29 vs 39-44 gems) because the captures are. Against Mite our
  trip rounds per banked gem are 1.81 vs 1.16 by r300, with 3.5 sub-15-gem trips a game to its 1.6. `chain_bag_limit`
  binds on 0% of our bags.
- **Idle.** Our Prism (22.6 rounds a game) and Cassi (5.6) spell-kite from range and wait out cooldowns; opponents'
  almost never do (0.9). About half of Prism's kiting is 00stampede (below). Wolf kites are not a leak: we keep
  95-98% of kited groups, no enemy ever damaged one mid-kite, and standing in at range 3 would have been quicker in
  about 11% of Prism episodes by ~2.4 rounds each. Respawn camping is not a gap: Fish waits less than we do.
- **Not leaks:** parallel solo clears on nearby groups (as common as theirs), walks abandoned to an ally (rarer for
  us), `home_ground` on middle groups (weight 1.0), recall policy (both recall onto payouts at ~55%).

## In gold

Camp gold, like gems, is paid only at capture to the allies on the tiles; damage alone pays nothing. Measured from
capture shares and the champions' lifetime `earned` (304 distinct games, `scripts/gold/gold.py`, `goldsum.py`),
paired by game. Bracketed ranges are 95% CIs:

| Gold | vs Fish (112) | vs pbg (68) | vs Mite (31) |
| --- | --- | --- | --- |
| Earned by r150, us / them | 521 / 631 | 430 / 648 | 484 / 584 |
| Earned by r300 | 1167 / 1418 (−18%) | 964 / 1381 (−30%) | 1050 / 1266 (−17%) |
| Earned by r600 | 2657 / 3246 | 2232 / 3071 | 2439 / 2995 |
| r300 gap from captures | −258 [−340, −164] | −338 | −159 |
| r300 gap from kills, Marcella | +7 (level) | −79 | −57 |
| Capture gold r1-300 gap, groups with an Elk | −219 [−288, −147] | −198 | −36 |
| ... with a Golem | −36 | −47 | −21 |
| ... wolves only | −28 (n.s.) | −91 | −46 |
| ... gold clusters only | +16 (n.s.) | −4 | −78 |
| Gold lost r1-300: we did most damage, they captured | 59 vs their 8 | 54 vs 23 | 30 vs 6 |
| Capture gold per 1k camp damage r1-300 | 40 vs 51 | 39 vs 50 | 42 vs 49 |

- We deal nearly as much camp damage (−8% vs Fish) but turn less of it into gold. We put 40% of our damage into
  wolf groups and 16% into gem fields, which pay almost no gold. Fish puts 33% and 11% there, and more into Elk
  (42% vs 34%) and Golem groups (5.4% vs 1.7%).
- Against Fish and pbg the gold gap is Elk groups. Against Mite it is spread out, gold clusters included.
- The "big middle gem fields" in the gem gap above pay ~0 gold.
- farm.cc prices a group as gems + `per_gold` × gold (farm.cc:747), where `per_gold` is gold's gem value through the
  shards it buys (shop.cc:445). Only Cassi and Tavi's gold maps weight gold up (`gold_farmer_weight` 4).

## Ally positions in comms

The user's proposal: each champion posts its turn-end position every turn, as fuchsia does. Designed and simulated
on our 211 distinct ladder games, with real priorities and positions (`scripts/comms/possim.py`, `boxsim.py`).

- **Why it matters.** 64-69% of our champion pairs are more than 8 tiles apart, so out of sight (Fish ~50%). Every crew
  and holder rule needs a visible ally: `ally_engaged`, the `engaged` box, `struggling`, `unclaimed_partner_output`
  (radius 12 but sight 8), `pick_up`, `allies_on`, `capture_taken`, the partner term.
- **fuchsia's scheme as-is breaks under our changing turn order.** It sends positions mod 13 relative to the last
  write, plus a one-shot home code after recalls and respawns. In 3.15% of reads a reader misses one write; when that
  write was the home code, the reader decodes 13 tiles off and stays wrong. Result: 98.2% of out-of-sight reads exact,
  with 422 wrong episodes lasting 50+ reads.
- **The fix is writer-side and costs no bits.** The writer keeps what readers decoded from its last two writes. It
  sends a near code only if that code decodes from both; otherwise it sends the home code of the nearest spawn-box
  tile. Result: 99.94% exact, wrong episodes averaging 1.2 reads, none reaching 50.
- **Bits.** Per body, 1 + 169 + box (spawn ±3): ~8.1 bits, so 24/32/40/48 bits for 3/4/5/6 bodies.
  - The claim (7.3-8.3) and today's capture record (up to 11.9; fuchsia's payout mod 4 is 7.7) still fit.
  - The bag fits on 3-4 bodies and 34 of 58 five-body ladder rows.
  - The enemy sighting fits only on small 3-body maps; the second sighting goes.
  - Prior evidence values sightings at ~0: astraeus without them read 53.6% on ladder maps, and river lost 3.5 points
    applying them.
- **Fuel.** ~1-1.2k a turn. It also removes the turn-end `observe()` refresh that exists only for sightings.

The stages:

| Stage | What | Effort |
| --- | --- | --- |
| 0 | New mixed-radix word with positions decoded but unused. Prices the dropped sightings: `ab.py`, accept level. | large |
| 1 | `World` stores comms positions (`Source::comms`, a `located()` test). The rules written for full information switch from `visible` to it: `allies_on` and its callers, `capture_taken`, `pick_up`, `recall_landing`, occupancy and `hold_start`, Safety's occupied window, `Pathing::blocked`. | medium |
| 2a | Crew arrivals (`work_arrival`, `crew_work`) from exact anchors. | small |
| 2b | `ally_engaged` and `engaged` count located allies. | small |
| 2c | The partner and `struggling` terms over the full 12-tile radius. | small |
| 2d | Camp-hit competition (`find_members`) and siege staging. | small |

Stage 2's consumers are judged one A/B each. `work_arrival` must accept `Source::comms` in stage 1, or out-of-sight
allies lose their anchor. Full design: `workflow-reports.json`, key `comms`.

## What to test, in order

1. **P0: sum the partners** (small, exact). `farm.cc` prices a clear shared with partners from the strongest one alone
   (`max`, farm.cc:1086; `unclaimed_partner_output` 580-583), while `crew_work` sums the joiners. Sum them everywhere,
   prunes included. On round 1 cap the sum at the fewest nearest allies the group needs. Judge with `solo.py`, then
   `ab.py`.
2. **Crew-aware `finishing_camp`** (small; no comms). `finishing_camp` (camps.cc:510) prices the rest of a clear at
   the member's own output, so below the recall line a crew member goes home unless it could finish alone (`want_home`,
   fight.cc:180). Count visible allies claiming the group and in range. It changes today's shared and help clears,
   and crew calls depend on it. Watch deaths with an enemy within 8.
3. **P1: crew calls** (medium; 2 bits in today's word). Smaller than first thought. Sized on 297 ladder games
   (`crew-call-workflow.json`, key `sizing`): a call fires 0.5-1.0 times a game in r1-300. In 55-82% of calls the
   joiners came anyway. Worth ~0-4 gems a game early and 4-8 over a game, so `ab.py` may read level. It pays only
   with short arrival caps (net −2 at 15 turns, −5 at 30). Design (key `synth`, after three designs and critiques):
   - **Post:** the caller writes (g, J joiners wanted) in the claim record, ((g+1)·4 + J)·team + index, and payload
     bits 11-12 (62 of 64 bits on the worst map). Allies on g with J = 0 are volunteers. Nobody predicts anyone
     else's choice, so there is no crew to rebuild.
   - **Kinds:** 2+ Elk or any Golem; a lone Elk only with a joiner ≤6 turns out; never strikerless fields (81% are
     solo-affordable, and their losses are contests).
   - **`crew_fit`:** a camp hits the nearest champion, so the front (shortest range) takes the hits, against real
     margins (hp − 0.35·max, no `camp_risk`). Arrivals are staggered by ETA = steps − radius − range, +1 for a
     ranged champion without a reset. The k ≤ 3 nearest free allies by (ETA, index); first ETA ≤ 10, the rest ≤ 15.
     Pricing hits by output share (as farm.cc:1107 does) or with `camp_risk`'s 2.86× margin certified crews that
     fail in one trip.
   - **Joiners:** free (no bag ≥11, hp ≥50%, not holding, banking or working an awake group), within the cap, and
     their exact self-check fits. Over-supply is settled once by index before the start; committed joiners are never
     displaced.
   - **Start:** hold fire on a sleeping called group until the crew in range fits, or 5 rounds after the caller
     arrives. A melee caller never starts later than today; top teams wake at once (median 0 rounds).
   - **Off:** no call with 2+ enemies within 8 of the group (those starts complete 18%). Clear the claim on recall,
     bank and mend.
   - **Ranged members:** walk once to a back tile at range 3, ≥2 from every striker, then basic plus cast every turn
     while a melee holds the hits.

   Stages: fuel-only caches (`min_camp_damage` slots 4 → 8), then item 2, then the call, then the caller valuing
   crews (P0's sum and the prunes), then comms positions for allies out of sight.
4. **Closeness** (unsized design). The bigger lever behind calls: at the first hit on a big group top teams have
   3.38 bodies within 12 steps (all 5 in 32%) against our 2.71 (12%), and they complete more at every count.
   Re-weighting our completion to their spread is worth ~9 gems a game (observational). Their joiners come from the
   same distances as ours (walk median 8, p90 20), and they do not wait before waking.
5. **Comms stages 0-1**, then 2b/2c beside P1.
6. **Keep the hold to payout** (small; a narrower lever than first thought). One ally on any camp tile captures, but
   any enemy on any tile blocks or resets it, and extra holders only split the shares. We already hold alone (1.03
   holders a capture, 3% with 2+; top teams 1.07-1.08), so the fix is not more bodies on the tiles. Gold the enemy
   captured after we did most of the damage, r1-300, 204 games (`scripts/leaks/leak_gold.py`; theirs in brackets):
   - not cleared, they finished it: 23.7 (6.6); a crew and `finishing_camp` question, not a hold
   - held, the holder left before payout: 9.0 (1.8)
   - held, contested off: 5.9 (0.9)
   - cleared, nobody held: 5.1 (0.4)
   - they took the last hit: 6.1 (0.0)

   So: the holder stays the 6 rounds unless forced out, nobody walks off a clear with no holder, and while an enemy
   is within reach of the tiles the crew stays to fight them off, not to stand on them. ~15 gold a game by r300.
   Check bot.cc's order: the strike search runs before `hold_capture`, and `holding_capture_now` turns false once an
   enemy is on the tiles. A ranged hit in passing that clears a cluster (`attack_in_range`, `passing`) leaves it for
   anyone. Who holds matters little: with Vesper (+33% gold) drafted our captures pay 1.17x base gold, Fish's 1.15x.
7. **P3: an opening crew plan from the draft's leads** (medium). Every round-1 input is common knowledge, so a team
   greedy over bodies (join an earlier body's lead when it is beyond the leader's spare or the joint rate wins) needs
   no comms. The opening gap is concentrated (three 00vault games make half the r1-150 gap vs Fish; the median per
   game is 6), so expect it on jackpot maps.
8. **A bag floor** (small). No dedicated altar trip under ~20 gems unless the altar is within ~5 steps, the tribute
   wins, or a credible threat is in reach. Prior: "Banking small bags only for nearby enemies" was held as
   ladder-motivated. Watch gems lost on death.
9. **Kiting: leave farm.cc's rule** (farm.cc:1099); narrow siege.cc's. A ranged walk spends the attack, but standing
   at range 3 costs only the walk-in turn: from there a champion basic-attacks and casts every turn (no ability
   spends the walk or the attack). The real trade is camp hits paid as heal trips, and farm.cc:1099 prices it per
   group. Kiting wins at our median Focus (Prism ~195); standing in wins at low Focus near spawn. The gain from
   changing it is under 2 rounds a champion-game. Elk and Golem never kite in farm (reach 4 = ability range). The
   loss is siege.cc's `kite()` on shared-gems maps (bot.cc:362; 00stampede, 01elk_arena): our Prism softens the
   160-gem Elk.mid alone for 474-704 rounds at Focus 80, and enemies take the last hits in all 4 games. Bound a lone
   kite's clear time (≈ respawn or 100 rounds), but keep later lives kited with crews (676 of our 836 gems in the
   one win). Judge on a suite of shared-gems mapgen maps: two ladder maps are noise in `ab.py`.
10. Lower: Jungle first (every Mite champion takes it; we open Prospector/Hunter). `home_power` 2 → 1 (enemy-side
   groups only; history argues against).

Judging: `solo.py` shows P0/P1/P3/bag floor; holds, contests and crews' contest value need `ab.py` and the ladder.
Measure the local A/B replays with the same metrics as here (`scripts/mine/farmcmp.py`, `farmsum.py`): crew size at
clears, Elk/Golem capture gems, nearest-teammate distance, damage ending in enemy captures, gems per tribute. demeter
is untracked in git, so freeze it with `./copybot demeter variants/demeter-<tag>`, and pass `--no-test-draft` to
`ab.py`.
