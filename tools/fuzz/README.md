# Map fuzzing: tools/fuzz

Finds maps on which our bot farms pathologically against `bots/idle` (which never acts), so they can be fixed by hand.
It is a bug finder, not a benchmark: a high score says "look at this map", not "the bot is worse".

```
py tools/fuzz/fuzz.py run NAME                                   # 400 maps, climb 8 of the worst, 4 generations
py tools/fuzz/fuzz.py run NAME --screen 600 --ref hyperion --climb 10 --gens 5 --children 12 --shrink 2
py tools/fuzz/fuzz.py run NAME --screen 0 --include maps/gen --climb 0   # score an existing set only
py tools/fuzz/fuzz.py report NAME [--top 30]                     # rewrite report.md/json
py tools/fuzz/fuzz.py rescore NAME                               # after editing score.py: recompute from analysis/, no games
py tools/fuzz/fuzz.py vs NAME hyperion [--top 10]                # head-to-head on the worst maps, both sides
cambc run bots/astraeus bots/idle --map replays/fuzz/NAME/worst/01-<map>.map26a
node tools/mapgen/mapgen.mjs show replays/fuzz/NAME/worst/01-<map>.map26a
```

Run it in tmux. 600 maps with a reference, a 5-generation climb of 10 maps and 2 shrink generations took 12 minutes
on the 96-core box (2026-10-30: screen 3.5 min, each generation 60-80 s, gated by its slowest 2000-round games) and
1.2 GB, mostly replays (delete `stages/*/batch-*/*.repl26a` once done; `analysis/` keeps what rescore needs).

## Pipeline

1. **Screen.** `--screen N` maps: `--mutate-share` (0.2) from `mapgen mutate random` (a ladder map under random edits), the rest
   in equal shares over every preset `mapgen list` prints at run time, so new presets join without a change here. A
   preset that fails a seed retries two more; failures are counted in the report and skipped. `--include DIR` adds
   existing maps.
2. **Play.** `run_batched.py BOT bots/idle` on both sides (`--one-side` halves the screen; climbs always play both),
   at most `--threads` (80) games at once from the shared CPU-slot pool, then `extract.mjs` into the run's
   `analysis/`. `--ref BOT` plays a reference solo on the same maps and sides (match `test_draft`: astraeus and
   hyperion are both off).
3. **Score** each game (`score.py`), then each map: the mean over its sides plus their asymmetry.
4. **Climb.** The `--climb` worst maps scoring `--bad` (2) or more, at most two per source, each get `--children`
   mutations a generation (one `mapgen mutate` op, a quarter of the time two). Children are played on both sides;
   the worst replaces its parent if it scores `--min-gain` (0.15) more. A lineage stops after `--patience` (2)
   generations without gain. Mutations that change nothing are dropped (by file hash).
5. **Shrink** (`--shrink G`): G generations of removing ops (`walls*0`, `holes*0.5`, `camps-1`, `altars-1`, ...);
   a child is kept if it holds 85% of the score and 70% of its leading component, so the map gets simpler while the
   pathology stays.
6. **Report.**

## Score

Higher is worse. Each component is capped, then weighted (`WEIGHTS` in score.py); report.md lists them per map.

| Component | Weight | What | Value |
|---|---|---|---|
| `econ` | 1 | Gem rate (tributed per round; 1000 / round reached, or end gems / 2000) under the typical rate for maps offering as much | log2(typical / ours), cap 3 |
| `no1000` | 1 | Never reaches 1000 where the typical rate would by round 1400 | 0/1 |
| `hoard` | 1 | Gems carried, never tributed, at the end of a game that never reached 1000 | / 250, cap 2 |
| `asym` | 1 | Gem rates of the two sides differ (the map is symmetric, so a gap is fragile play) | 2 x (abs log2 ratio - 0.2), cap 2 |
| `untaken` | 1.5 | Share of own-side gem groups' gems (shared halved) never captured, in long games only | share x (rounds - 500) / 1000, cap 1 |
| `stall` | 1 | Champion-rounds in runs of 160+ rounds inside a 3x3 box, alive, off spawn, not tributing, teleporting or attacking | / 600, cap 3 |
| `camp_deaths` | 1 | Deaths to camps and the gems they cost | 0.5 a death + gems / 200, cap 3 |
| `oof` | 1 | Out-of-fuel turns | / 10, cap 3 |
| `errors` | 3 | Bot-error turns, or a failed or timed-out match | 0/1 |
| `poke` | 0.25 | Attacks on the idle champions (on their spawn, so wasted turns) | / 100, cap 2 |
| `vs_ref` | 1 | With `--ref`: gem rate under the reference's on the same map and side | log2(ref / ours), cap 3 |

- **Offer rate**: over the side's gem groups (shared groups halved), gems / respawn rounds; the map's gems
  regrowing per round. The typical gem rate at an offer is fitted on the screen (medians of 8 quantile bins of
  offer, interpolated in log-log; state.json `base`), and never above the offer itself. The bot's rate saturates
  near 2 a round whatever the map offers, so a raw efficiency (rate / offer) would only rank map richness.
- A stall must outlast every camp respawn (a Monolith's 150 rounds) so waiting by a camp doesn't count. Recall
  channels don't excuse a round: the bot starts and cancels a recall nearly every turn, also while stuck.
- `poke` is weighted low: idle champions stand on their spawn, which no real opponent does.

## Output: replays/fuzz/NAME/

| Path | Contents |
|---|---|
| `report.md`, `report.json` | Worst maps (one per lineage) with components, source and a one-line description of the worse side; clusters by source and by leading component; each lineage's accepted edits; mean score change per op family over every child |
| `worst/NN-<map>.map26a` | The worst maps, ranked; `worst/Lxx-final-*.map26a` each climbed lineage's end map |
| `maps.jsonl` | Every map played: origin (preset and seed, or ladder map and ops, or lineage and op chain), `mapgen check` metrics, per-side metrics, components and score |
| `lineages.json`, `ops.json`, `state.json` | Climb chains, every child's op and score change, run arguments, stage times and the rate baseline |
| `stages/<stage>/` | Maps, `run_batched.py` batches and logs per stage (screen, seeds, climb-gN, shrink-gN, vs-BOT) |
| `analysis/` | extract.mjs output for every game |

Map names: `p-<preset>-<seed>` (`node tools/mapgen/mapgen.mjs gen <preset> --seed <seed>` regenerates it while the
preset is unchanged), `m-<ladder>-<seed>` (`mutate random --seed <seed>`), `Lxx-cG-K` / `Lxx-sG-K` (lineage xx, climb
or shrink generation G, child K; the chain of ops is in maps.jsonl). Mutations rebuild from files, so a child is
reproducible only from its parent's file.
