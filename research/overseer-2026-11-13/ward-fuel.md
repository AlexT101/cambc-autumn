# nyx-vl's ward policy: where its fuel goes, and an exact cut (2026-11-13)

`bots/variants/nyx-vl` is charybdis 525 plus a value-driven ward policy (`place_ward`, `ward_value`,
`ward_site_boards`, ...) and no altar locks. At 2x fuel it beat charybdis by about 52%. At the real budget it
read 50.8% (50.3-51.2) of 40,960 games, with CAND out-of-fuel turns at 325,655 against REF's 254,127 (+28%).
The working copies are:
- `bots/variants/nyx-vl-fuel`: the exact cut.
- `bots/variants/nyx-vl-fuel2`: the exact cut plus one change that alters behaviour.

## 1. Where the fuel went (nyx-vl, real budget)

The sample was 205 overseer-nyx maps (every 100th), both sides, against charybdis: 410 games
(`replays/fuel/wardfuel/`). Timings come from an instrumented copy that prints a `WPROF` line per call past the
cooldown (`wardprof_patch.py`, read by `wardprof.py`).

Per play turn, nyx-vl's mean turn cost 50,731 fuel against charybdis's 47,136 (+3.6k):

| | nyx-vl | charybdis |
|---|---|---|
| mean play turn | 50,731 | 47,136 |
| OOF turns (debug `out-of-fuel` shortcuts) | 2,853 | 2,133 (nyx +34%, like the A/B's +28%) |
| `turn-order` shortcuts | 33,649 | 9,703 |
| `farm-partial-evaluation` shortcuts | 65,474 | 44,202 |
| `ward-fuel` shortcuts | 103,208 | 0 |

`place_ward` itself spent 7.63G over the 410 games: 18.6M a game, about 4.1k a play turn. That is the whole of
the gap, so the ward policy is what squeezes the later gates (turn order, farm) and drives the extra OOF turns.

| part | share | notes |
|---|---|---|
| candidate loop (`ward_value` x up to 25) | 72-73% | 20 candidates a loop, 690-750 fuel each |
| own sight + near/far boards + old ward's value | 11-15% | ~1.2k a call |
| memo check (allied wards read + count) | 6-9% | ~400 a call; 2/3 of start calls stop here |
| site boards (`ward_site_boards`) | 2-4% | rebuilt ~200 times a game (the site flips) |
| cluster growth | 2% | |

- **Calls.** There were 686k turn-start calls (mean 4.4k each) and 625k turn-end calls (mean 7.4k).
- **The dear case.** It is "no candidate beats the margin" (exit 3): 242k loops at 12-18k each, typically a
  champion walking with its ward ready.
- **Casts.** 86% of candidate casts repeat a tile the same champion cast before.
- **Per candidate** (micro timings that include one `fuel()` call): the r6 cast cost 240-490 depending on the
  map, and board scoring about 285.

## 2. What changed (nyx-vl-fuel), and why it is exact

The only file changed is `bot.cc`.

1. **`SightCache`, `cached_sight`.** `ward_sight_from(p, r)` depends only on the static map:
   - `walls_and_bushes` never changes after startup.
   - A bush tile's cluster is complete before any tile points at it.
   - The cast overwrites the board and leaves nothing beyond r of p.

   So the words of the cast over p's chunk window (at most 3x3 chunks for r 6 and 8) are a pure function of p.
   They are stored per tile on first use in zero static arrays: 2 x 730 KB, and a measured 0 fuel for the BSS.
   `ward_value` scores from the stored words with the same chunk loop, so the integer sums are identical. Maps
   over 10,000 tiles and off-map tiles take the old path.
2. **`champion_sight_into`.** It does the same for the champion sight (r8) of `here` and of the site's stand
   tiles. On a hit it calls `clear_board` and writes the window words, which gives the same board as the cast.
3. **Copy loops with vectorisation off.** Clang auto-vectorised the 9-word copy loops, and the alias checks and
   prologue made a copy cost about 450, more than the cast it saved. `#pragma clang loop vectorize(disable)`
   brings a copy to about 16 wasm ops a word.
4. **One fuel check for the whole candidate loop.** It checks for room for all n+1 candidates before the loop.
   Each candidate costs under `ward_candidate_cost` (1500), so whenever the hoisted check passes, every
   per-candidate check would have passed too. When it fails, the old per-candidate check runs.

A check copy (`wf-check`) compared every cached board and value against a fresh cast: there were no mismatches
in 52 games.

**Tried and dropped:**
- **v2: per-site cached values plus a bound on what `here` adds.** Exact, but it skipped only about 20% of
  candidates, because the here-part is large while walking. Each evaluated candidate went from 720 to 1,130.
  Net: dearer.
- **SIMD scoring of chunk pairs.** It saved about 15 a candidate: the scoring loop is already about 22 ops a
  chunk, and the rest is overhead.

## 3. Bench identity (100M, fast runner, `--set wide --jobs 86`, against astraeus)

- **`--test-draft`:** 52/52 identical replays, every version.
- **Own drafts:** 48/52. The 4 that differ (00fragment-b, 00swirl-b, 01boss-battle-a, gen-chambers-102206117-a)
  are the known turn-end queue trap. `TurnEndQueue::run`'s floor simulates the real budget even at 100M, so
  fuel saved in the turn buys more next-turn prep and warm-up, and the first divergence is a `WARM` line.
- **Own drafts with the queue on a fixed 30k in both copies** (`wf-base-qfix` against `wf-v3-qfix`, DIAG copies
  only): 52/52 identical.

Fuel on those games (test drafts):
- all turns: mean -1.5%, p99 -2.4%;
- total fuel -1.45%;
- round 1 +2.0%: every tile misses the cache there, and the cast plus copy runs once per tile.

At 100M the queue soaks up savings, so the 100M total understates the per-turn saving.

## 4. Result

### Real-budget ward cost (the same 410 games, instrumented copies)

| | nyx-vl | nyx-vl-fuel |
|---|---|---|
| `place_ward` total | 7.63G | 6.27G (-18%) |
| turn-start calls / turn-end calls | 3.04G / 4.59G | 2.47G / 3.80G |
| fuel per candidate (start / end) | 747 / 687 | 616 / 487 |
| candidate loop | 5.54G | 4.13G |
| old + boards / memo / site | 1.00G / 0.53G / 0.24G | 0.98G / 0.53G / 0.30G |
| mean play turn (uninstrumented nyx-vl / instrumented fuel copy) | 50,731 | 49,643 |
| OOF (debug shortcut; nyx-vl's instrumented copy: 2,897) | 2,853 | 2,603 |
| `ward-fuel` / `turn-order` shortcuts | 103k / 34k | 77k / 26k |

charybdis on the same games: mean play turn 47,136, OOF 2,133.

nyx-vl-fuel2 on the same games (instrumented):
- `place_ward` 5.79G in all: the turn-start calls fall from 2.47G to 0.41G, mostly the memo check, and the
  turn-end calls rise from 3.80G to 5.38G, because the searches move there.
- mean play turn 50,111; OOF 2,068; `ward-fuel` shortcuts 45k.

The total barely falls, but the fuel now lands where the turn-end gates (`room`) can skip it. What drives OOF
turns is where the ward fuel is spent in the turn, not how much of it there is.

### A/B against charybdis

The A/B ran at 100k on `maps/suites/overseer-nyx`, with 40,960 games, own drafts and release builds:

| CAND | win % | 95% CI | OOF CAND | OOF REF | CAND/REF |
|---|---|---|---|---|---|
| nyx-vl (earlier) | 50.8 | 50.3-51.2 | 325,655 | 254,127 | +28% |
| **nyx-vl-fuel** (exact) | **51.2** | 50.8-51.7 | 312,392 | 252,706 | +24% |
| **nyx-vl-fuel2** (start call: drafted tile only) | **51.9** | 51.4-52.4 | 256,209 | 251,555 | +2% |

- **The exact cut** removes 18% of the ward fuel and 4% of CAND's OOF turns. The win rate moves by +0.4, inside
  the noise.
- **Where the extra OOF turns come from.** They are the ward policy's, and almost all of them come from its
  turn-start call. That call does the full search before the strike search and the move.
- **nyx-vl-fuel2.** It leaves the turn start only the draft's tile (as charybdis's planned ward did) and the
  full search to the turn end. That brings OOF turns back to charybdis's level (+2%) and reads 51.9%, the 2x-fuel
  gain of about 52%.
- **fuel2 changes behaviour.** A ward that would have gone down at the turn start now goes down at the turn end
  (or on the drafted tile at the start), so it needs its own gate before shipping.

## 5. Left on the table

- **The exact search still costs ~3.3k a turn** (6.27G / 1.88M play turns).
  - 66% of it is ~20 candidates x ~490-620 each: scoring ~200 a hit, plus misses (cast, copy and score,
    ~1k). 25% of casts are first visits, which cannot be shared across bodies.
  - The dear case is "nothing beats the margin" while walking: the best candidate sits at a median 0.68 of the
    threshold (p90 0.89).
  - Exact bounds tried were too loose to prune: per-site values plus `extra` skipped about 20%. Untried: a bound
    from the previous call's exact values plus the boards' added tiles, `value_t <= value_prev + 2|N\N_prev| +
    |F\F_prev|`. It is exact, but the payoff is unclear.
- **The champion-sight (r8) cache does not pay.** The hit path (`clear_board` plus writing 9 words) costs about
  what the cast does. Site boards got ~25% dearer and `here`'s sight about level. Dropping `champion_sight_into`
  (back to `ward_sight_from`) is exact and would save ~0.1G over the 410 games. It was left in so as not to
  restart the A/B.
- **The memo check is ~400 a call** (ward read, `count_within`); ~0.5G in all.
- **Round 1 costs +2% at 100M** (all cache misses). It is a 200k turn, so a little warm-up moves to round 2.
- **Own-draft bench identity** can only be shown with the queue on a fixed floor (the trap in section 3).

Scripts: `wardprof_patch.py` and `wardprof.py` (ward profile), `micro_patch.py` and `micro_read.py` (per-candidate
timings), `bench_id.sh` and `bench_real.sh`. The data is in `replays/fuel/wardfuel/`.
