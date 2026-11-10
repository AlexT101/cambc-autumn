# camphp: part-damaged camps (2026-11-09)

Scripts behind EXPERIMENTS.md "Camp health weight". Inputs are `extract.mjs` analysis dirs.

- `abandon.py DIR...`: one JSON line per group life (respawn to clear) with damage; a life with a gap of >= 10 rounds
  in its damage while members live is an abandonment, with the health left, who hit it, the hitters' state and the
  outcome (who hits next, clears, captures). Team names from `~/tmp-offload/camphp/names.tsv` (ladder) or the batch.
- `h2h.py`, `why.py`: head-to-head and per-cause summaries of the ladder lines (us, Fish, Mite).
- `joinF.py BATCH ABANDON.jsonl`: joins abandonments with a debug build's `D` (decision) and `FSW` lines (farm left a
  damaged group: the loop stage it was dropped at, its value and the best's), from the instrumented copy's stdout.
- `fsw.py BATCH`: FSW lines by health left. `cmp.py`: behaviour metrics of A/B arms' batches.
- `fsw-trace.patch`: the instrumentation (ocean-16d6f78's farm.cc; debug builds only). `damaged-weight.patch`: the w50 arm (w15: `damaged_boost = 0.15f`).
