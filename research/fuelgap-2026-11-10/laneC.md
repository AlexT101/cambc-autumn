# Lane C: around the farm loop (order, prefetch, post-loop shortcuts), 2026-11-10

**Verdict: no-go on all three directions. No candidates.** The two refund-scope runs price each direction's ceiling
inside noise. Each is a free version of what the direction could at best achieve, and each fired: cut loops fell 77% /
44%.

## Measurement 1: where a cut farm turn's fuel goes

`bots/variants/fgc-meas` is oc-ceil-ref plus fuel marks in `debug_block`s through the turn ([patch](laneC-meas.patch)).
It played 1,280 debug games at the real budget against oc-ceil-ref (fceil-2020, every 16th map,
`laneC-tools/maps640.txt`), with a second run on finer marks. Scripts are in `laneC-tools/`: `an1*.py` parse,
`an2.py` / `an3.py` tabulate, `pair.py` pairs ab logs by map.

- **Volume.** 6.9% of farm-loop turns after round 1 are cut, 12% in rounds 2-49. 25% of cut loops stop before their
  first pass: they reach the loop with a median 25k and walk on to the last choice. Enemies are visible on 61% of cut
  turns (12% of uncut ones).
- **Fuel at farm entry:** 57k mean on cut turns, 83k on uncut ones. The turn starts with ~100k.
- **Fuel left at turn end:** 12.8k mean on cut turns. The loop's reserve over-covers what follows it: at the cut 29k
  is left (median), and the rest of the turn spends 17k.

Spend by part, mean (p90), cut turns against uncut:

| part | cut | uncut | owner |
|---|---|---|---|
| world update | 9.6k (13.9k) | 6.1k | lane A |
| `chase_with_guard`, which then declines | **14.2k (37.0k)** | 0.8k | prey |
| channel checks: `continue_recall`'s want_home on the feint recall | **9.1k (20.0k)** | 3.4k | |
| `local_support` .. heal / shield | 1.9k (4.5k) | 0.5k | |
| kite / siege | 1.8k | 1.4k | |
| everything else before the farm | ~5k | ~4k | |
| farm before its loop | 9.2k (13.2k) | 6.9k | |
| of which contexts, gold prices, struck check | 2.5k | 2.0k | |
| of which recall_out, home trips | 1.6k | 0.8k | |
| loop | 16.3k (39.5k) | 13.0k | lane B |
| after the loop | 10.5k (19.2k) | 9.0k | |

- **Post-loop shortcuts are rare.** On cut turns: farm-no-route 1.5%, crow-flies-farm 0.7%, farm-kept-target 0.06%,
  farm-no-attack-tiles 0.04%. Over all play that is ~7 events a game.
- **Spare fuel the turn before.**
  - 43% of cut turns follow a turn that ended with 20k+ unspent.
  - 42% follow a cut turn, which left a median 13k.
  - 42% follow a turn with no farm loop (fight, chase, recall), which left a median 37k.

## Measurement 2: the ceilings (refund scopes, 20,480 games each)

Both arms are built like the step-0 arms: oc-fz2-dev, a 10M quantum, gates reading the 1x budget. Each played
oc-ceil-ref on `merged/fceil-2020` and is paired by map against `fz2-view`.

| arm | what is free | win % | paired diff (95%) | cut loops, 128 games at 10M |
|---|---|---|---|---|
| `fgc-fzpre` ([patch](laneC-fzpre.patch)) | everything `act()` spent before the farm got control, refunded at farm entry: the ceiling of moving it all after the farm | 51.9 | **+0.31 (-0.55 to +1.20)** | 4,144 (view 18,183) |
| `fgc-fzspare` ([patch](laneC-fzspare.patch)) | the whole farm, only on turns whose previous turn reached its queue with 30k+ of the 1x budget: the ceiling of a turn-end prefetch | 52.1 | **+0.43 (-0.45 to +1.27)** | 10,163 |
| `fz2-farm` (step 0) | the whole farm, every turn | 52.7 | +1.11 (+0.23 to +1.97) | |

- **Direction 1 (order): no-go.** Moving every pre-farm part after the farm at no cost removes 77% of cut loops, yet
  buys +0.3. That is the most any reordering could reach. Besides, most of that spend is a verdict the farm depends on:
  want_home, the chase's decision not to chase, heals.
- **Direction 2 (prefetch): no-go.** Even a perfect prefetch, the farm free on every turn after a spare turn, buys
  +0.4. Any real prefetch has stale inputs and pays its own cost, and the cross-turn memo hit rates are
  0.01-10%. The candidate I had in mind was a turn-end speculative farm evaluation from next turn's tile, setting
  `farm_group` so a cut loop starts from a fresh choice. Its ceiling is this arm's. It was not built.
- **Direction 3 (post-loop shortcuts): no-go on volume.** The searches after the loop are already funded on 98% of cut
  turns. A provably valid reused route would only shrink the loop's reserve, which gives the loop more fuel, and
  `fgc-fzpre` shows that more loop fuel buys about +0.3. The blind reserve cuts (x0.75, x0.5) were already level.

## Open questions

- **fzpre against fz2-farm, paired: -0.81 (-1.71 to +0.04).** Giving the farm ~43k up front on cut turns, which ends
  most cut loops, reads worse than refunding the farm's own spend. Possible reasons:
  - noise between two arms;
  - fz2-farm also frees `farm_reprice` in `continue_recall`;
  - the step guard placed lazily inside the farm's route searches is free under fz2-farm only.

  If the gap is real, the farm's +1.11 is not mainly about finishing the loop. Lane B may want to check this before
  building on loop completion.
- **`chase_with_guard`'s rejected verdicts cost 14k on cut turns.** Prey free reads +0.43 ±0.83 in step 0, so this is
  not a farm-order lever. Whether a cheaper verdict is worth anything is prey's question.
- The feint recall makes `continue_recall`'s want_home run at every turn start (9.1k on cut turns). It is needed
  either way, because want_home's answer gates the farm.

Copies: `bots/variants/fgc-meas` (marks, debug only), `fgc-fzpre`, `fgc-fzspare`; none is a candidate. Runs:
`replays/ab/fgc-fzpre/`, `replays/ab/fgc-fzspare/`.
