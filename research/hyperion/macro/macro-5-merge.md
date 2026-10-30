# Macro merge notes (macro-5, 2026-10-30)

Merging the four macro branches (macro-1..4, all from ef8f0b84) into one astraeus. A/Bs at normal fuel, own drafts
(`--no-test-draft`), run names `m5-*`. Dev suites: ladder, gen, fresh, maps/fresh-6100..6115 (~10k games).
Held-out: maps/fresh-6116..6123. Refs: `variants/astraeus-ef8f0b8` (current astraeus) and the base's frozen copy
`variants/astraeus-67cad24`.

## Plan (revised after a read-only audit)

### Base: macro-4 (c3, bot 83804615 = frozen astraeus-67cad24)
- Level with macro-1 at normal fuel (59.9 vs 59.5 vs ef8f0b8; 83.3 vs 83.1 vs hyperion; 66.4 vs 66.9 vs 54254fb).
- Its gains are many separately measured pieces (threat-aware recall line +~1-2, no sightings +2, camp exit by
  walking distance +0.9 and half the camp deaths, pack zone radius 5 / ratios +2, pursuit 2, hurt 0.35, brake 25
  +~1), fiddly to port; macro-1's portable gains are mostly two params (horizon, max_wait), a two-line shop rule,
  and the claim board, which the comms test ports anyway.
- Smaller (net -32 lines in the bot: it dropped sightings); macro-1 is +545 lines, much of it level (locks, stalls).
- (Audit: macro-1's recall 0.25 / camp_risk 0.25 move draft.cc type_facts, but that only feeds rank_body's farm
  leads (loop order, so fuel and tie-breaks), not the picks: a weak point. The out-of-fuel counts of the two
  branches came from different held-out sets and are not comparable.)

### Overlaps, settled before testing
- Retreat ratios: macro-1 and macro-4 landed on the same values (hurt 3.5, home 3.0). Nothing to choose.
- Recall line: keep macro-4's threat-aware 0.18 / 0.35, not macro-1's flat 0.25. macro-1's own last probe (0.30)
  was level with 0.25, and macro-4's line is the same idea made conditional (low only when no enemy can reach us),
  measured on this base; macro-2's 0.25 low line with an enemy-aware 0.10 lost, so a lower line without a threat
  check is not on the table.
- camp_risk: keep 0.35. macro-4 measured 0.25 on its own base at -1.5 (and 0.20 at -2.2); macro-1's gain from 0.25
  came paired with its flat 0.25 recall line, which we are not taking.
- Pack zone: keep macro-4's radius 5 with the ratios. macro-2's Y1 (no pack zone for healthy empty-handed champions
  on own ground, +1.8 on macro-2) changes the same retreat trigger; macro-4's version measured more (+2.6 with the
  ratios on 9356) on the stronger bot. Not stacked.
- Recall out to farm: macro-4's (5fd9c4cf) is in the base; macro-2's version is the same idea. Not ported.
- Corridor jams: macro-3's make_way fix (opens a single-file line of allies) fixes the cause; macro-1's jam stall
  breaker (give the target up after 8 jammed turns) works around it. Only the former is a candidate.
- Comms: alternatives per the user's instruction; see step C.

### Steps
Round 1, each a variant of the base A/B'd against the base (astraeus-67cad24) on the dev suites: A1, A12, B, D.
Meanwhile C1 is ported onto a copy of the base. Round 2: the base plus round 1's keepers = M; M with C1 = M-C1;
A/B M and M-C1 each vs ef8f0b8 and M-C1 vs M.
A. Time at work (macro-1 e926bbeb, the parts not already in the base): cycle horizon 25 (was 100) and max_wait 0
   (was 5). Evidence: macro-1 probes on its board base: horizon x0.25 +1.5 (53.3 vs 51.8), max_wait 2 +2.8,
   max_wait 0 +1.1 more on c1; the package is where macro-1's whole gain came from. Audit: max_wait also bounds the
   base's FarmRecall::sooner, where 0 would reject a recall that arrives before a respawn even when it beats the
   walk (the walk is allowed with no wait): waiting after a recall costs no more champion time than walking longer,
   so macro-1's reason does not apply there. So farm's max_wait goes to 0 and sooner() keeps the tested bound 5.
   macro-1's max_wait gain was measured with its held-respawn stall breaker (keyed on max_wait) in: expect less.
   Horizon 25 and recall-to-farm pull opposite ways on far groups: A12 (both) is the main variant; A1 alone too.
B. Home trips for two emblems' gold (macro-1 95500f74, 2 lines in wants_shop): a healthy (75%+) champion recalls to
   shop only with gold for two emblems. Evidence: +0.6 on macro-1's probe suite, level on dev; logical (a home trip
   heals too, so a healthy one should buy more per trip). Overlap: the base's FarmRecall credits the next emblem
   when recalling out to farm, which still applies.
D. make_way past a line of allies (macro-3 6be0d4ab pathing.cc/.h parts only, ~25 lines; not its Prism cap): fixes a 1270-round corridor
   jam; measured level (50.2 of 9356). Kept only as a bug fix if it reads level or better.
C. Comms layout (user's instruction: two alternatives, never combined).
   - C4 = the base's layout (macro-4 aa9eb229): no enemy sightings, a claim field per ally, the capture record in
     its own slot. On macro-4: no sightings +2.0 (55.3 vs 53.3); per-ally claims level with the rotating claim.
   - C1 = macro-1's claim board (1e7af34a) ported in place of the base's comms: per-body slot (claim, ETA bucket,
     need bit) every turn, camp record, bag and sightings as room allows; ownership (senior claimant unless 2+ ETA
     buckets earlier), crews valued by share on any owned group, the need bit answering unseen allies. On
     macro-1: +1.8 (51.8 of 9356). Ported whole from 1e7af34a only (not macro-1's tip: the stall breakers sit in
     the same farm hunks), restoring main.cc's comms::expect (sightings), with three adaptations to the base: the
     posted ETA uses the by-spawn arrival when farm chose a recall out; `claimed = ally_owns(...)` after `reach` is
     known; `struggles` measures against recall_line() as spare_health does. Caveat: C1 brings sightings back
     (-2 on macro-4), and that cannot be separated without mixing layouts.
   - Built on the merged bot after A/B/D; A/B'd each vs ef8f0b8 and C1 vs C4 directly. Keep the better; C4 if level
     (smaller, fewer bits).
E. Confirm the final on held-out (fresh-6116..6123) vs ef8f0b8 and vs the base.

### Dropped without a test (level or lost on their branches, or more code than they measured)
- macro-1: altar-lock wear-down (level, +160 lines), stall breakers (level; the freezes were mostly mirrored),
  camp_risk 0.25 and recall 0.25 (overlaps above), tank formation (level).
- macro-2: recall out to farm (base has macro-4's), hold own side Y1 (overlap above), recall 0.25 Y3 (recall line
  above), low line 25% / D1 / D3 (lost
  or level), buddy cohesion (level), hunt op (lost twice), burst op (lost), comms v2 op record (level, and a third
  layout).
- macro-3: distress beacon + assist (level, +44% out-of-fuel turns, and it would need rebuilding on the chosen
  comms), Prism as carrier (level), claim arbitration (level). Its rules fix is brought across (a87a5ff6).
- macro-4's own level extras: ward following, safe line 0.14, cv3 camp-info slots.

## Log
- Base: macro-5 reset to macro-4's tip 1f90e8fb (bot = 83804615 = astraeus-67cad24); macro-3's rules/probe fix
  cherry-picked.
- Round-1 variants (bots/variants/, gitignored): m5-a1 (horizon 25), m5-a12 (horizon 25 + farm max_wait 0, recall
  out keeps 5 as params::recall_max_wait), m5-b (two-emblem home trips), m5-d (make_way past allies), m5-c1 (the
  base with macro-1's board: comms.cc/.h byte-identical to 1e7af34a, main.cc's comms::expect restored, farm and
  bot.cc hunks of 1e7af34a with the three adaptations; +520/-111 lines). A read-only audit found the port faithful.
  Board layouts seen: 5 bodies `team 5 groups 14 eta 8 camp 1 bag 1 sight 0`; 3 bodies keep one sighting.

### Round 1 (vs the base astraeus-67cad24, dev suites, 9356 games each, normal fuel)
| variant | win % | 95% CI | OOF turns cand / ref |
|---|---|---|---|
| m5-a1 horizon 25 | 50.5 | 49.5-51.5 | 24756 / 24548 |
| m5-a12 horizon 25 + max_wait 0 | **52.4** | 51.4-53.4 | 24246 / 23575 |
| m5-b two-emblem home trips | 50.1 | 49.1-51.2 | 24633 / 24617 |
| m5-d make_way past allies | 49.9 | 48.9-50.9 | 24080 / 23999 |
| m5-c1 macro-1's board on the base | 49.0 | 47.9-50.0 | 27092 / 23549 |
Reading: the wait is the gain (horizon alone level). B and D level: left out (level; simpler without). The board on
the base reads -1 with 15% more out-of-fuel turns; tested again on the merged bot (round 2) as the brief asks.
Round 2: m5-a2 (max_wait 0 alone) vs base, to see whether the horizon is needed; M = m5-a12, M-C1 = m5-mc1 (board
+ a12); M-C1 vs M, and both vs ef8f0b8.

### Round 2 (dev suites, 9356 games each, normal fuel)
| run | win % | 95% CI | OOF turns cand / ref |
|---|---|---|---|
| m5-a2 max_wait 0 alone vs base | **52.3** | 51.3-53.3 | 24775 / 24324 |
| M = m5-a12 vs ef8f0b8 | 61.3 | 60.3-62.3 | 24300 / 24424 |
| M-C1 = m5-mc1 vs ef8f0b8 | 60.3 | 59.3-61.2 | 27339 / 23690 |
| M-C1 vs M (board vs macro-4 layout, head to head) | 49.3 | 48.3-50.3 | 28495 / 24426 |
Reading: max_wait carries all of A (52.3 alone vs 52.4 with horizon 25): the horizon change is left out. Comms:
macro-4's layout kept. The board lost on the base (49.0) and on the merged bot (49.3 head to head, 60.3 vs 61.3
against ef8f0b8), with 15-17% more out-of-fuel turns; it is also ~400 more lines. (It brings sightings back,
which macro-4 measured at -2; the two cannot be told apart without mixing layouts.)
Candidate = base + max_wait 0 / recall_max_wait 5: committed 532f164b (CHANGES 241). Held-out runs next.

### Held-out and final
- 532f164b held-out (fresh-6116..6123, 4096): 58.3% (56.8-59.9) vs ef8f0b8; 50.0% (48.4-51.5) vs the base.
  Dev was broad (16 of 19 suites over 50) and macro-1 measured the same knob at +1.1..2.8, so kept.
- Frozen as /home/ubuntu/cambc-autumn/bots/variants/astraeus-532f164. Final comparisons (10,240 each):
  vs ef8f0b8 (fresh-7021..7040) 59.6% (58.7-60.6); vs hyperion (fresh-7001..7020) 83.8% (83.0-84.5);
  vs 54254fb (fresh-7001..7020) 67.4% (66.5-68.3). Level to +1 against macro-4's and macro-1's own readings.

## Summary
The merge is macro-4's bot plus macro-1's max_wait 0. Everything else from the other branches read level on this
base (horizon, home trips, make_way) or lost (the claim board), so it was left out.
