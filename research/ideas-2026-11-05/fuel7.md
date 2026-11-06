# Fuel round 7: exact savings in the farm loop, prey and the step guard (ocean, 2026-11-06)

Goal: the same decisions for less fuel, so the fuel checks cut less (fuelbud: the cut prize is a fuel-efficiency
prize; 25% more budget recovers it). Base `variants/oc-retest-clean` (= `bots/ocean`); dev copy
`variants/oc-fuel7-dev`. Exactness: `tools/fuel/bench.py` at 100M, replays byte-identical to oc-retest-clean's on the
default (16), wide (52) and pool (128) sets. Tools in `fuel7-tools/` (`bench.sh`, `probe.py`/`lqan.py` per-group
lines, `probe2.py`/`lsan.py` segment profile, `probe3.py`/`lcan.py` crew call counters, `mksuites.sh`); bench JSONs
and profiles in `replays/fuel/ocfuel7/`. Suites: dev 537000-537039 (`maps/suites/merged/fuel7-dev`), confirm
537100-537139 (`fuel7-conf`).

## Profile (oc-retest-clean, pool set, 100M; `variants/oc-fuel7-probe`)

Segment profile of the group loop (probe2: a fuel mark between the loop body's stages, summed in the bot). Kind 0 is
the ordinary loop (190k loops, 15.9 groups, 16.5k a loop), kind 3 the banking loop (62k, 19.4 groups, 26.0k).

| where a group leaves | kind 0 groups / cost each / share | kind 3 |
|---|---|---|
| pre-facts bounds (PreLanes) | 1.87M / 237 / 14% | 550k / 243 / 8% |
| stage-1 checks, rated_below | 175k / 825 / 4.6% | (none) |
| the `least` prune (before live_steps) | 57k / 1,188 / 2.1% | 110k / 1,023 / 7% |
| **just after live_steps: the pre_value and claim_most bounds** | **255k / 1,405 / 11.3%** | 58k / 1,388 / 5% |
| idle wait, prunes(trip) | 128k / 1,634 / 6.6% | 106k / 1,526 / 10% |
| claimed: beaten_claimed, cleared | 100k / 2,446 / 7.7% | 56k / 2,353 / 8% |
| claimed: after crew_work (`c`, `d`) | 43k / 3,489 / 4.8% | 26k / 3,323 / 5% |
| claimed: share set (`J`) and after its plan | 70k / ~7,300 / 15% | 23k / ~6,200 / 9% |
| valued (best or not) | 250k / 2,936 / 23% | 253k / 2,604 / 40% |

Crew calls (probe3, all kinds): plan_crew 129k calls at 2.7k (price 0.8k of it), the crewable bound's ally pass 222k at
950, crew_work 178k at 1.25k (work_arrival 609 a call, 65% misses), crew_allies 211k at 700.

**The cheapest sound bound for the biggest prunable block** is the one already there: pre_value and claim_most are
loop constants once the group's PreLanes block is read, so their test gives the same answer at the loop's top as
after live_steps. fuel4 moved them after live_steps because live_steps keeps the approach's camp labels
(`same_labels`), which later turns read. But that state exists only for a group with an approach slot (one we
searched a way to); for the rest, live_steps returns at once, and what lies between (facts, steps, the least prune,
hops) only fills memos (facts' context, centre steps, fields) whose values do not depend on when they are read.

## Plan (each step exact on all three sets before the next)

1. **E1, early bounds.** At the loop's top, for a group with no approach slot at its live range, the pre_value and
   claim_most tests (exactly as after live_steps). Expected: ~1.2k of ~1.4k off 255k groups, ~9% of the ordinary
   loop's fuel. Risk: facts read later change rated_below's worth (weighted when current); both are valid bounds, so
   only which bound prunes changes, not the choice.
2. **B1, the crewable bound without its ally pass.** crew_rate at k in [1, crew_most] (a superset of [lo, hi], the
   rate unimodal in k) bounds the pass's `most`: when it fails every test the pass's would too, and the pass (crew
   table, claimers, available allies) is skipped. crew_work reads the table or the allies the same way, so the
   table's read state is free.
3. Then the claimed branch (the table read before beaten_claimed, crew_work), plan_crew's fixed costs, and the pre-facts
   path's per-group overhead, as the profile after 1-2 shows.
4. Prey (candidate costs before the sims) and the step guard (placings), exact cheaper versions where found.
5. Measure: fuel on the same games at 100M, and at the real budget the cut counts (farm-partial-evaluation,
   prey-cut-short, step-guard-*) and OOF turns; A/B against oc-retest-clean, SPRT 0.50/0.51 on the dev suite, then
   20,480 games on the confirm suite; also with the astraeus-port loop reserve (oc-astport's `loop_reserve`) on
   top, its scale at 0.8 / 1.0.

## Results: no exact saving worth an A/B; nothing frozen

**The concrete target is mostly not prunable.** fuelbud's "3.3k groups after prunes(trip), 29% of the loop" splits
(probe.py, rounds 150-299, ordinary loop) into the claimed branch's share set (`J`: the group becomes the crew share,
6.5k each, 15% of loop fuel: crew_work 1.7k, plan_crew 2.0k, the crew table 0.5k), which is the loop's answer, not
waste; the claimed branch's existing bounds (`b` beaten_claimed 6.9%, `c`/`d` after crew_work 5.4%, `e` 1.4%); and
small rest. Valued groups that lose (V) lose because their real clear (camp damage, trips home, crews) is much slower
than any cheap bound allows: a rated bound at the fastest clear (R1 below) catches almost none of them.

**Call costs** (probe3/4/5, pool 100M, all loop kinds): pre_bounds 4.1M calls at 127 (11% of loop fuel: the SIMD
block, ~420 a block of 4), plan_crew 129k at 2.7k (price 833 x 1.35, min_camp_damage 451, share_damage 270), the
crewable bound's pass 222k at 950, crew_work 178k at 1.25k (work_arrival 609, 65% misses: claimers move), crew_allies
211k at 700, live_steps ~220 a call (6%), room() 20. Prey: 389k calls at 1.7k, chase_trade 31% of it (5.2k a sim),
preyable 15% (833), the rest (~900 a call) the candidates' set-up. Step guard: 266k calls at 1.0k, new_fight 45% (5.4k
a sim), exposure 13% (1.3k). Over the whole game the farm loop is ~9% of mean turn fuel at 100M.

**Candidates** (bench.py at 100M against oc-retest-clean; mean fuel a turn, all play turns):

| | change | default | wide | pool |
|---|---|---|---|---|
| E1 | pre_value and claim_most at the loop's top for groups with no approach slot (`Pathing::approach_held`) | 16/16, +0.1% | **51/52**, +0.1% | **126/128**, -0.3% |
| R1 | the first turn's rated bound (`rated_beaten`) after prunes(trip) on later turns | 16/16, +0.1% | 52/52, +0.1% | 128/128, +0.0% |
| B1 | the crewable bound at k in [1, crew_most] before its ally pass (`fuel7-tools/b1-crew-bound.diff`) | 16/16, +0.1% | 52/52, +0.0% | 128/128, -0.0% |
| noop | an untaken branch after prunes(trip) (codegen check) | 16/16, +0.02% | 52/52, +0.02% | 128/128, +0.02% |

- **E1** moved 148k of the 255k post-live_steps prunes to the loop's top (segment profile: those exits 254k -> 106k)
  but its own test on every group that passes the pre-facts bounds (+72 a group there) took back nearly all of it:
  loop fuel 16,667 -> 16,616 a loop. And it is **not exact**: 3 games of 196 diverge, so some state on the way to
  live_steps other than the approach labels is read later (not found: the steps' source memo, which takes the first of
  the centre field, the draft's steps or a field from here, is the likeliest). Dropped.
- **R1, B1**: exact on 196/196, but their tests cost about what they skip. B1's loose bound rarely fails where the
  pass's fails (the pass's is tight because it knows the claimers); R1's bound at the fastest clear is far above the
  valued groups' real values.
- Not built: a cheaper pre_bounds block (bit-identical float ops needed, as any change in which groups are pruned
  before facts reaches live_steps; ~2-3% of loop fuel at best), cross-turn reuse of plan_crew / crew_work for the
  share group (its inputs, the claimers' positions, change every turn), prey and step guard cuts (their fuel is the
  sims, which fuel5 found flat; their non-sim parts are ~900 and ~430 a call).

**Why.** Fuel rounds 4-6 and the astraeus campaigns took the repeats and the cheap bounds: the loop is SIMD pre-bounds,
memos per context and version, and tight scalar code whose segments each cost 50-250 fuel a group. What is left
spends on answers (the share's plan, valued groups) or on bounds that already prune. As in fuel5, an exact change of
hundredths of a percent of total fuel cannot show at SPRT 0.50/0.51 (fuel4's -2.5% total fuel read +0.8), so no A/B
was run and `variants/oc-fuel7` is not frozen. `variants/oc-fuel7-dev` holds B1 (exact, level). The fuel left on cut
turns is a reserve question (the loop keeps back ~2.6x what the turn spends after it), which the astraeus-port
agent's state-sized `loop_reserve` (oc-astport) addresses as a decision change; it was A/B'd here on this round's
unused confirm suite (below).

## oc-astport (the loop reserve) on this round's confirm suite

With no fuel7 change, "fuel7 + loop_reserve" is `variants/oc-astport` itself, so it ran alone against oc-retest-clean
on `fuel7-conf` (537100-537139, unused by any A/B; own drafts, fast runner), 20,480 games: **49.8%** (10197-10283,
95% CI 49.1-50.5). OOF turns 152.0k against 155.7k (-2.4%); shortcuts: farm-partial-evaluation 2.54M against 3.57M
(-29%), farm-no-route 78k against 124k, turn-order 298k against 351k, prey-cut-short and step-guard-entry level
(334k / 332k, 1.251M / 1.243M). The reserve cuts the farm loop's partial evaluations as intended but reads level on a
fourth unused set (astport's three pooled read ~50.3%). The 0.8 / 1.0 scale re-check was not run: it was to tune
the reserve against fuel7's savings, which do not exist. Log: `replays/fuel/ocfuel7/ab/f7-astport-conf.log`.

Profiles: `replays/fuel/ocfuel7/probe1*.txt` (per-group exits), `probe2-pool*.txt` (segments); bench JSONs in
`replays/fuel/ocfuel7/bench/`.
