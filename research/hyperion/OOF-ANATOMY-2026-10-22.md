# hyperion: anatomy of the out-of-fuel turns (2026-10-22)

Measured on main d59ccf7 (CHANGES 1-67). This note covers what fills the 100k on the turns that run out of fuel, so
the next round can bound it without new fuel gates.

## Method

- **Games:** `bench.py run <bot> --test-draft` against hecate, both sides, on the four maps that hold most of the
  out-of-fuel (OOF) turns: gen-s1/gen-chambers-102206117, gen/gen-chambers-102106111, gen-s1/gen-hourglass-102205812
  and 00contest. That is 8 games, run at `--fuel 0` (real budget) and at 100M.
- **Instrumented copy:** `bots/variants/oofa` (local, not committed).
  - It adds 33 RAII probes on the decide steps and the shared work (sims, Reach builds, lethal, threats,
    find_members, route), plus 5 phases inside `plan_strikes` (read / grow / price / act).
  - A per-turn stack records inclusive and exclusive fuel.
  - The first probe event after a resume finds the round changed. The frames open at that moment are the ones open
    when the fuel ran out, and each is charged its start fuel (it ran to 0).
  - A replay is the `continue` in main.cpp after an OOF (CHANGES 59). The copy prints one `PF` line for every OOF
    turn, every replay, and every turn over 100k at 100M.
  - SRCH, SLOT, D and SHORTCUT output were switched off to stay under the 1 MiB stdout cap.
- **Fidelity:**
  - At 100M the copy plays 8/8 replays identical to main, at +0.58% fuel (~250 a turn: debug_block's guard is
    not quite free).
  - At the real budget that shift reroutes the games. The copy had 691 OOF turns where main had 1038 on the same
    8 games. CHANGES 67 records swings of hundreds on these maps, so read the shares, not the counts.

## OOF turns at the real budget (691)

| map | OOF | of which replays |
|---|---|---|
| gen-chambers-102206117 | 318 | 150 |
| gen-hourglass-102205812 | 206 | 100 |
| gen-chambers-102106111 | 96 | 31 |
| 00contest | 71 | 22 |

| champion | OOF | share |
|---|---|---|
| Heart of Ruin | 416 | 60.2% |
| Ren | 120 | 17.4% |
| Ryth | 51 | 7.4% |
| Varg | 46 | 6.7% |
| Stellar | 41 | 5.9% |
| others | 17 | 2.5% |

Every OOF turn ran out inside `decide`. The world update, comms and the turn end never ran out.

### Where it ran out

The table shows the decide step open at the cut. The last column is the step that cost the most that turn.

| step open at cut | all (691) | first-time (388) | replays (303) | costliest step on the turn |
|---|---|---|---|---|
| strike search (`plan_strikes`) | 58.6% | 49.2% | 70.6% | 62.7% |
| `farm` | 18.4% | 20.1% | 16.2% | 12.4% |
| `carry_bag` (bank, walk) | 5.8% | 8.2% | 2.6% | — |
| `siege` (`siege_candidate`) | 5.2% | 7.5% | 2.3% | — |
| act's tail / `strike_after` / turn order | 5.9% | 9.8% | 1.0% | — |
| retreat, chase, shop, other | 6.1% | 5.2% | 7.3% | — |
| `step_guard` / `want_home` | 0.4% | 0% | 1.0% | 14.9% / 6.5% |

- **Inside the search:** it ran out in `grow` 66% of the time, `price` 29% and `act` 3%. Heart of Ruin holds 303
  of the 405 search cuts.
- **The last step is only where the bill came due.** On turns cut in the search, it began with 41k left (p10 27k,
  p50 41k, p90 57k). Before it, the turn had spent:
  - world update: 12.8k;
  - `want_home`: 20.1k;
  - `step_guard`: 18.1k (p90 39k);
  - prepare_walk, ward and shop: ~1.5k.
- **Farm cuts:** turns cut in `farm` began it with 29k left (p50 32k). Before it they had spent the world update
  (15.6k), `want_home` (16.1k), `step_guard` (6.9k), `prey` (4.1k) and siege (2.3k).

### What each step costs before the cut

The fuel is inclusive and averaged over all OOF turns. The values are each frame's spend up to the cut.

| step | first-time OOF: mean | p90 when run | replay OOF: mean | 100M turns > 100k: mean | 100M: p90 |
|---|---|---|---|---|---|
| world update | 14.6k | 19.1k | 13.3k | 15.8k | 19.6k |
| `want_home` (all callers) | 18.8k | 31.0k | 20.3k | 18.0k | 28.3k |
| `want_home`: `stand` (its fight) | 8.6k | 18.0k | 8.5k | 8.6k | 17.3k |
| `want_home`: `lethal` (1.4 calls) | 5.6k | 9.7k | 5.7k | 4.9k | 9.0k |
| `want_home`: `camp_trapped` | 3.0k | | | 2.5k | |
| `step_guard` (1.07 calls; own code 10.9k) | 18.3k | 38.7k | 12.1k | 24.8k | 50.3k |
| strike search (cut-inclusive) | 31.9k | 50.9k | 34.9k | 19.3k | 41.3k |
| search: read / grow / price | 9.1 / 17.1 / 5.2k | | 7.7 / 23.3 / 3.6k | 6.5 / 6.5 / 5.6k | grow 17.9k, max 142k |
| `prey` + `chase` | 1.8k | 17.0k | 0.4k | 16.2k | 33.0k |
| `farm` (when run) | 24.7k | 58.0k | 28.1k | 28.4k | 50.3k |
| fight sims, summed | 9.5k (3.1 sims) | 20.4k | 6.5k (2.4) | 21.1k (6.4 sims, 3.3k each) | 38.4k |
| Reach builds, summed | 3.7k (2.5) | 6.7k | 3.2k | 4.6k (3.2, 1.5k each) | 7.6k |
| `find_members` | 3.7k | 9.2k | 3.5k | 4.0k | 8.8k |

- **At the real budget the gates truncate the guard and prey.**
  - The step-guard gate (`act_reserve`) and prey-cut-short hold `step_guard` to 18k and `prey` to 1.8k on OOF
    turns. At 100M the same steps cost 25k and 16k on turns over 100k.
  - What they save goes into the strike search, which has no gate and runs out.
  - This is why every gate removal raised OOF turns: the saved fuel was the search's.
- **The fixed part of every OOF turn:** world, upkeep and `want_home` cost 32.6k at p50 (p90 48k). With
  `step_guard` it is 50.7k at p50 (p90 66k). At 100M on turns over 100k, the same four steps cost 58k at p50 (p90
  86k).

### Chains and replays

| chain length (consecutive OOF rounds, same body) | chains | OOF turns |
|---|---|---|
| 1 | 264 | 264 (38%) |
| 2 | 71 | 142 (21%) |
| 3-5 | 50 | 180 (26%) |
| 6-10 | 14 | 91 (13%) |
| 11-14 | 1 | 14 (2%) |

- **Replay share:** 303 of the 691 OOF turns (43.8%) are replays that ran out again. Each first-time OOF turn costs
  1.78 OOF turns on average.
- **How replays end:** of 712 replays, 409 finished (they used 72k mean, p90 89k) and 303 ran out again.
- **Where re-cut replays run out:** 233 of 291 paired re-cuts (80%) ran out in the same decide step as the turn they
  replaced, mostly the strike search.
- **A replay starts with 91.5k on average.** The abandoned turn's resumed tail costs 5.0k (p50 4.7k, max 27k): the
  thrown StaleTurn (~3.9k) and main.cpp's plain "turn ran out" printf (~1.3k).
  - Whether a replay runs out again does not depend on how much it starts with. Of replays starting at 90-95k, 42%
    ran out again; at 95k or more, 42%. Refunding the tail would not help.
- **The replay redoes the same work** on the next round's world:

| step (pairs: cut turn, then its replay) | cut turn mean | replay mean | both ran |
|---|---|---|---|
| world update | 14.0k | 13.7k | 690/690 |
| `want_home` | 19.5k | 19.1k | 688/690 |
| `find_members` | 3.6k | 3.6k | 686/690 |
| `step_guard` | 15.6k | 8.0k | 578 |
| strike search | 33.2k (cut) | 21.1k | 514 |
| fight sims | 8.2k (2.8) | 6.3k (2.3) | 555 |

So the replay is the same turn one round later: the same ~50k of fixed work, then the same search into the same
wall. Cut the first-time OOF turns and the replays fall with them (×1.78).

## Turns over 100k at 100M (1740 of 58.1k play turns)

- **By champion:** Heart of Ruin 35%, Ren 18%, Ryth 15%, Varg 15%, Issac 6%, others 12%.
- **Size:** used mean 124k, p50 117k, p90 155k, max 250k.
- **Overrun:**
  - 20% of these turns are within 5k of the budget;
  - 34% within 10k;
  - 56% within 20k;
  - 71% within 30k;
  - 88% within 50k.
- **Costliest step:** `step_guard` 34.7%, `farm` 18.3%, strike search 17.1%, `chase`/`prey` 10.1%, `carry_bag`
  8.7%, `continue_recall`/`want_home` 9.9%.
- **The strike search by champion** (on turns over 100k, mean / p90):
  - Heart of Ruin: 27.6k / 58.6k, and `grow` 12.1k / 33.0k. Its search exceeds 30k on 29% of these turns and
    `grow` exceeds 30k on 10%.
  - Ren: 22.7k / 38.6k.
  - Others: 15-21k / 31-37k.
- **step_guard by champion:** Ren 41.4k mean (p90 69k); the others 19-28k.

Turns over 100k brought under 100k by each what-if (inclusive costs, same turns):

| what-if | fixed | share |
|---|---|---|
| fight sims at half cost | 527 | 30.3% |
| `step_guard` at most 15k | 442 | 25.4% |
| `prey` at most 10k | 371 | 21.3% |
| `find_members` free | 245 | 14.1% |
| `want_home` at most 15k | 231 | 13.3% |
| `farm` at most 20k | 166 | 9.5% |
| Reach builds at half cost | 157 | 9.0% |
| strike search at most 20k / 30k | 142 / 59 | 8.2% / 3.4% |
| step_guard 15k + prey 10k + search 30k | 953 | 54.8% |
| ... + want_home 15k | 1223 | 70.3% |

## Proposals, ranked

The shares are of the 691 OOF turns. A fix to first-time OOF turns also removes their replays (×1.78), so the
shares already include replays.

1. **Bound the strike search's growth by a node budget, not fuel (Heart of Ruin first).**
   - Addresses up to **58.6%** of OOF turns: the search is open at 405 cuts (303 Heart of Ruin, 66% in `grow`).
   - The search began with ≥30k on 335 of those 405 turns, and with ≥20k on 394. A search held to ~25k (plus ~5k
     for the goal walk and turn end) would have finished on most of them.
   - At 100M a 30k bound changes 29% of Heart of Ruin's heavy-turn searches. Over all turns it changes far fewer (the
     profile's Heart of Ruin p99 search is 79k), so measure the bind rate over all turns before choosing the bound.
   - **Design:**
     - Count nodes and landings in `Search::grow` and expand best bound first, so that the budget drops the weakest
       branches.
     - Or merge equal landing states (tile, dead mask, cooldowns) before expanding. That part may be
       byte-identical.
     - The deterministic fallback is the best plan found so far (the search already caps exact queries at
       `max_exact_queries`).
2. **One danger pass per tile per turn across want_home, step_guard and the search's end tiles.**
   - Addresses the ~50k of fixed work on **all OOF turns**. It is the reason the search starts with only 41k (p50).
   - `want_home` costs 19-20k on every OOF turn: `stand` 8.5k, `lethal` 5.6k over 1.4 calls, `camp_trapped` 3k and
     its own code 2.7k.
   - `step_guard` costs 15.6k, of which 10.9k is its own code: Reach::at looks, bounds and fight keys.
   - **Byte-identical first steps:**
     - memoise `lethal(p)` for the turn (step_guard and the search's end tiles ask it again);
     - keep step_guard's settled keys and Reach exposures across its two calls a turn;
     - widen the 64-entry Reach memo.
   - The fold (FUEL-PROFILE item 5) comes after.
   - At 100M, `want_home` ≤ 15k alone fixes 13% of over-100k turns and `step_guard` ≤ 15k alone 25%.
3. **Cheaper fight simulation.**
   - At 100M: 6.4 sims a turn over 100k at 3.3k each, 21k (17%). Halving their cost fixes 30% of over-100k
     turns, the most of any single item.
   - At the real budget the sims are gated down to 2.8 a turn (9.5k): this is what removing the step-guard and
     prey-cut-short gates releases. So this item has to land before those gates can go.
   - Same levers as FUEL-PROFILE item 2: a cheaper act(), and exits checked every few half-turns.
   - Addresses the step-guard/prey share: 14.9% of OOF turns have `step_guard` as their costliest step.
4. **Farm cold cost (FUEL-GATES phase 4).**
   - Addresses **18.4%** of OOF turns, cut in `farm`. They began it with 29k left; `farm` costs 25-28k when run on
     these turns (p90 58k).
   - The farm-partial-evaluation gate still fires a lot here. Bound the evaluation loop (per-group reads hoisted or
     cached across turns, FUEL-PROFILE item 3) so a farm turn after a fight fits in ~15k.
5. **`siege_candidate`, `carry_bag`'s bank walk, and find_members.**
   - Siege and carry_bag cuts are 11% of OOF turns. `siege_candidate` costs 2.5k at p90 on OOF turns and is
     memoisable (FUEL-PROFILE item 7).
   - `find_members` costs 3.6k a turn (p90 9.3k) on these camp-dense maps, both in want_home's `camp_trapped` and in
     upkeep. Giving it a memo for more than the last tile fixes 14% of over-100k turns at 100M.
6. **Replays: no separate lever.**
   - 44% of OOF turns are replays, but they run out for the same reason and in the same step (80%) as the turn they
     replace. Starting fuel does not change the outcome.
   - Making a replay cheaper means a cheaper turn, which is items 1-3. Throwing less (a flag instead of StaleTurn)
     and moving main.cpp's printf into debug_block would save ~5k a replay, but the 90-95k vs ≥95k comparison says
     that buys nothing.
   - Carrying out the abandoned plan instead (before CHANGES 59) traded OOF turns for stale actions, and should not
     come back.

Order of work: proposal 1 alone covers the largest share and is local to plan.cpp. Proposal 2 makes room for
everything after it. Proposal 3 is the prerequisite for removing the step-guard and prey-cut-short gates. Re-run this
bench (8 games, ~3 min) after each, counting OOF turns on a full A/B with `oof.py`.
