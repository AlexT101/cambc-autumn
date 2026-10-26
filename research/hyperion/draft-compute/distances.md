# Draft plan v4 and group distances (DRAFT-COMPUTE #1)

2026-10-26, branch `worktree-agent-a0333236d6aa4c6e9`. Part A is CHANGES 155 (merged as 490ea1e9). Part B is two
commits on 801ed7da: 0665471 (drafted walk orders) and cabb3f7 (the same loop order by Chebyshev distance, no draft
data), which supersedes it.

## Part A: the v4 layout

One bit stream over all 1024 bytes, least significant bit first. The header is 76 bits (v3's was 160):

| Field | Bits | Notes |
|---|---|---|
| `check` | 16 | hash of `current_version`, width, height, group count, first ally spawn tile; never 0. 0 (unwritten memory) is no plan; another version or map mismatches but for a 1 in 65535 chance |
| `field_layers` | 14 | the draft's deepest field, clamped |
| `steps`, `mirrored`, `spawn_offsets` | 1 each | `spawn_offsets` replaces v3's spawn tile count: champions know the count |
| `rice[3]` | 3 each | ally, enemy, altar steps; k up to 7 |
| `attack_groups` | 8 | |
| `distances_at` | 13 | lazily read section's start bit; 0 absent |
| `schedule_at` | 13 | for #5; 0 absent |

- The steps follow the header. The attack tiles start where the steps end, so v3's `attack_start` is gone.
- A future section decoded at build goes after the steps with no offset; a lazily read one gets an offset field.
- `PlanReader` keeps a 57-bit window and refills it only when it runs out: a Rice value ~80 fuel rather than ~100.
- Bytes used (header, steps, attack tiles) on the 26 bench maps: min 21, median ~66, max 228.
- Fuel-only: wide bench 52/52 byte-identical against f3f47ea. Round 1 −0.2% (−1.3k a champion; decode −0.6k on
  00ambush, −2.8k on 00lanes).

## Where a group-to-group distance could replace a field or a bound in `farm`

Measured with exit counters in the evaluation loop, 400 rounds at the real budget, against f3f47ea:

| Map (groups) | Warm calls: fuel a call | Pruned by the value bound (count × fuel) | Fully evaluated | Cut short |
|---|---|---|---|---|
| gen-close-spawns-120104804 (102) | 28-32k | 57-70 × 280-360 | 6-9 × ~800 | 50-57% |
| gen-dense-camps-120205502 (106) | 29-34k | 69-86 × 265-370 | 6-7 × ~750 | 39-42% |
| gen-star-120103100 (106) | 25-28k | 50-75 × 285-390 | 3-5 × ~800 | ~59% |
| gen-hourglass-102205812 (68) | 23-28k | ~50 × 290-350 | 3-7 × ~780 | 11-13% |

- **Most of the fuel is touching groups.** A group that fails the value bound has already cost ~280.
- **A tighter distance bound adds almost nothing.** Once the centre fields are warm, the loop has exact steps from
  `here` (27 fuel a read), and the prefilter experiment found exact steps prune ~1 group more than Chebyshev.
- **Skipping groups in bulk needs a bound per block of groups.** A suffix maximum of worth over a distance-sorted
  list is far too loose (a 36-gem group against a best of ~0.4 a round is pruned only beyond ~80 steps). Per-cell
  aggregates were the spatial-bucket experiment.
- **The cold phase.** Before the centre fields are warm, which takes 55-110 rounds on 100+ group maps (to round
  ~280 on gen-star), a from-here field costs ~7k a call. D can't bound steps from `here` without an exact anchor
  distance.
- **The order of evaluation is what helps.** Groups nearest last turn's choice come first. So a loop cut short (on
  11-94% of calls on these maps; 4,030 times over the 52 real-budget bench games, 1,751 of them on 00ambush) has
  weighed the likeliest groups. An early good `best_value` sends more groups out at the cheap prune: fully evaluated
  groups a warm call fell from 5.6-6.7 to 3.5 (close-spawns) and from 3.1-3.4 to 2.1-2.4 (star).

## Part B as built: drafted walk orders (0665471)

- **Draft:**
  - one uncapped walking field (`blocked_for_us`) per canonical group: half of them when mirrored.
  - These are kept out of `max_field_layers` and `costliest_field`, so champions' estimates don't change.
- **Section:**
  - A 3-bit Rice parameter, then an 8-bit `count` a row, then a 13-bit offset every second row after the first.
  - Then one row per canonical group: its `count` nearest groups by walk (ties by Chebyshev, then index).
  - Each entry is a Lehmer rank among the groups not yet listed, in Chebyshev order from the group's centre (a set
    both sides can list).
  - A mirror group's row is its canonical group's, mirrored.
  - `count` is the most that fits, capped at 16.
- **Bytes:**
  - Walk section 5-128 bytes on the bench maps (median ~29); whole plan 26-335 bytes (median ~99).
  - On 106-group maps, 150-178 bytes; plans 356-423 bytes.
  - Uncapped, the full order (n−1 a row) fit on every bench map: 68 groups took 2,393 bits.
- **Draft fuel:** round 0 rose from 0.2-1.2M to up to 2.3M on bench maps, and to 6.1M on 106-group maps (53 fields on
  99×99).
- **Decode, once per anchor, cached:**

  | Groups | At 32 a row, offset every 4 rows | At 16 a row, offset every 2 rows |
  |---|---|---|
  | 12 | ~6k | 4.0-4.8k |
  | 42-50 | ~16k | 9-10k |
  | 68 | 18-19k | 12-13k |
  | 106 | ~25k | 18-19k |

  - Chebyshev ordering is ~7k of the 50-group row; every Rice rank is ~130 with its select.
  - The chosen group's row is decoded at turn end when fuel is spare (`prepare_next_turn`).
  - With no choice yet (round 1), the loop keeps index order, so the decode never lands in round 1's decision.

## A/B results

All on own drafts (`--no-test-draft`), ~1100 games unless noted.

| Candidate | Reference | Overall | Ladder / gen / gen-s1 | Out-of-fuel turns (CAND vs REF) |
|---|---|---|---|---|
| walk orders, 32 a row, round 1 too | f3f47ea | 50.4% of 1164 | 50.0 / 50.4 / 50.6 | 6167 vs 5805 (+6%: decode spikes) |
| walk orders, 16 a row, prefetch | f3f47ea | 50.9% of 1164 | 52.1 / 51.0 / 50.6 | 5970 vs 5839 |
| Chebyshev order, round 1 too | f3f47ea | 49.5% of 1164 | 49.3 / 49.2 / 49.8 | 5766 vs 5897 |
| walk orders, final (0665471) | 801ed7da | 51.4% of 1164 (48.5-54.2) | 50.7 / 51.2 / 51.8 | 4574 vs 4616 |
| Chebyshev order, final (cabb3f7) | 801ed7da | 51.6% of 1164 (48.8-54.5) | 50.7 / 51.8 / 51.8 | 4718 vs 4681 |

Many-group maps are where the loop is cut short. The fresh suites are `mapgen gen dense-camps|tiny-groups` with seeds
7001-7050 (90 maps of 40+ groups, median 70) and 8001-8050 (88 maps, median 66). By group count, in the main suites:

| Candidate | Reference | Under 20 | 20-39 | 40-59 | 60+ (38 games) | Fresh many-group suite |
|---|---|---|---|---|---|---|
| walk, 16 a row | f3f47ea | 50.4% | 50.9% | 48.8% | 60.5% | 55.6% of 180 |
| walk, final | 801ed7da | 48.4% | 53.5% | 61.2% | 57.9% | 57.8% of 180 (50.5-64.8); out-of-fuel turns 1613 vs 1466 |
| Chebyshev, final | 801ed7da | 49.1% | 52.6% | 62.5% | 60.5% | 49.4% of 180 |
| Chebyshev | f3f47ea | | | | | 56.7% of 180 |

- **Walk orders against Chebyshev order, head to head** (0665471 against cabb3f7's build) on both fresh many-group
  suites: 49.2% of 356 (44.0-54.3). Walking distance orders the groups no better than Chebyshev distance does.
- **Out-of-fuel turns with farm sub-phases marked,** on the many-group suite: none of either bot's stopped inside
  `farm` (its loop gate holds), and the totals were level (1826 vs 1838).

## Fuel at 100M (wide bench, test drafts) against 801ed7da

- Walk orders (0665471): play turns mean −0.1%, p99 −1.3%; round 1 +1.8% (+9.1k a champion, the turn-end decode).
- Chebyshev order (cabb3f7): play turns mean −0.3%, p99 −1.8%; round 1 +0.8% (+4.0k a champion).
  - cabb3f7's replays are byte-identical (52/52) to the build A/B'd as cheb-final, so that A/B stands for it.

## What didn't work, and why the draft section was dropped

- **Ranks by list scans.** The first rank computation was O(n²) a row, and the decode check was too. On a 106-group
  map the draft ran out of fuel before picking (every pick random). Fixed with a 256-bit "not yet listed" set (popcount
  ranks and selects) and a fuel check before the section; it would have been a disaster on the ladder.
- **Decoding inside the farm turn.** A 32-a-row decode in the turn cost 6-25k and ran a few turns out of fuel
  mid-decode (+6% out-of-fuel turns). Fixed with 16 a row, an offset every 2 rows, the turn-end prefetch, and no order
  before the first choice.
- **Walking distance itself.** It added nothing measurable over Chebyshev distance for the farm order, and it cost
  1-6M draft fuel, up to 128 plan bytes and a 4-19k decode per anchor. cabb3f7 keeps the order and drops the section;
  `distances_at` stays 0.
- **Not tried, with reasons above:** pruning by D-based lower bounds (an anchor needs an exact distance, and exact
  steps add ~1 prune); D in allies' arrival estimates (`work_arrival` uses Chebyshev on purpose, as the earliest
  effect); chaining or lookahead values (two-job lookahead lost −24 on older bots).
- **What else could use real group-to-group distances:** #5's schedule needs travel times between groups. Those are
  the draft's own business: the schedule sends group sequences, so champions never need the matrix. A matrix in the
  plan is worth it only for a champion-side consumer that beats Chebyshev, and none was found.
