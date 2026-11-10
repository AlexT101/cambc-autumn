# Ocean fuel, sixth pass (2026-11-10, CHANGES 505)

Goal: fewer out-of-fuel (OOF) turns and shortcuts on bots/ocean (504), exact play at 100M.

## Shipped

`prey()` (combat/fight.cc) plays a chase's fight before asking its escape verdict, and asks the verdict
only of a fight it would take. The verdict's chase plan costs about twice the fight, and most fights
are declined. A declined fight waits in `unasked` with its target and result. It joins `lost` only once
its target is found not to escape, which keeps the old order of `lost` and of the returns.

- 100M (maps-id, 96 games): 95/96 replays byte-identical to 504. The one difference is the known
  fuel-dependent next-turn preparation coupling and vanishes in noprep diagnostic copies.
- Screen (1,024 paired real-budget games): shortcuts -9.39% (CI -12.03..-6.49); OOF -3.02%
  (CI -10.69..+4.62).
- Fresh dev suite (4,096 paired real-budget games, maps-dev): shortcuts **1,270,245 → 1,140,969 (-10.18%,
  CI -11.68..-8.78)**, OOF 26,022 → 25,545 (-1.83%, CI -5.30..+1.71), mean fuel -0.20%. No early losses.
- The forced-composition coverage run was not done: the reorder doesn't depend on the kit.

The 10% OOF target was **not** reached.

## Measurements worth keeping

- **Budget calibration** (base bot, screen suite, paired against the real budget):
  - 102k a turn: OOF -14.2% (CI -21.4..-7.5), shortcuts -8.3%.
  - 105k a turn: OOF -24.8% (CI -30.4..-18.7), shortcuts -18.9%.

  A saving early in a heavy turn acts like extra budget. About 1.5-2k saved on every heavy turn would
  give -10% OOF, about 2% of a heavy turn, spread over a flat profile.
- **The census's `dpost`/`post` is the stale tail, not the miss.** On a normal OOF it is the work done
  after the resume until StaleTurn unwinds to `run()`. Decide never finishes, so the miss is
  unobserved. Normal-OOF tails: median 3.0k, mean 5.3k, p90 9.4k, p99 50k (cen11, maps-id).
  - A copy that finished every resumed decision (`finish_late` forced on) overstates the miss: gates
    see the fresh budget and expand (median 15k).
  - Late turns that run out need a median 30k more after their resume, for the same reason.
- **Late turns** (after an OOF): they start with a median 97.6k of fuel, and 23% of them run out,
  against 3.9% of normal turns. They are ~24% of OOFs. Their cost is the heavy situation persisting,
  not a poorer start.
- **Doomed at entry is rare.** OOF turns entering a stage with less fuel than that stage's
  5th-percentile cost (completed turns): goal 43/321, g.farm 31/281, farm.post 9/123, ss.price 2/119,
  retreat 1/58 (cen12). Gates that fire only on certain exhaustion would catch about 4% of OOFs.
- **The fuelprof classes and attribution are misleading.**
  - An exhausted turn spends exactly 100k, so it lands in "heavy" (88k-100k).
  - "oof" (>100k) is almost only round-1 turns (200k budget).
  - "heavy" also holds turns that the turn-end queue filled with warm-ups (census `warm_up`: 10k self
    on 58% of heavy turns).
  - Function attribution, by DWARF or by body index, puts fuel in functions that can't run on those
    turns (`comms::receive` 4%, `play_draft`, static initialisers). Use the debug census (labels) for
    OOF work.

## Leads not pursued

- **Stale tails.** A check (`throw_if_stale`) in the long ungated routines would end tails sooner and
  give the late turn more fuel. Tails over 10k follow 9.5% of normal OOFs. The routines: reach builds
  in retreat's avoid, `drafted_attack_tiles`, `current_emblem`, escape plans, `min_camp_damage`.
  - Estimated gain: ~3-5% of OOFs.
  - Each check costs ~18 fuel a call on every turn.
  - Each new throw point must leave no cross-turn cache half-built.
  - A monotonic-fuel test in `fuel()` (fuel only falls within a turn) is free, but catches only
    tails that pass a fuel gate. The long ones don't.
- **Strike search.** It has no fuel gate and has ~20% of OOFs. An anytime cap is a gameplay change.
  The third pass's "below 25k" version lost -0.36 ± 0.54.
- Exact work examined this pass and found already tight:
  - `find_members` (SIMD lanes);
  - `update_camp` (bound by host calls per member);
  - Reach geometry (set reuse);
  - `Safety::tally`/`each_threat` (memoised blows);
  - turn windows (built once a round);
  - `Search::read`.

## Tools

`tools/`: `b.sh` (id, screen, dev, final and cov benches), `compare.py` (paired runner counts),
`census.h` (debug labels), `profile.py` and `symbolise.py` (see the caveat above), map lists.
