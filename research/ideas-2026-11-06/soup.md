# Constant soup tune (ocean, 2026-11-06/07)

Results and settings: EXPERIMENTS.md, "Soup tune (ocean, 2026-11-06/07)". Flat over 6.5M games; stopped by the
coordinator, since base10 is ~5 points behind live.

State, all resumable, under `/home/ubuntu/tmp-offload/soup/`:
- `tune/soup1`: the first 110-param attempt, aborted at iteration 4 (start 46%);
- `tune/soup2`: the 92-param run, 2,111 iterations; `games.jsonl` has every game for a map-feature fit;
- `tune/lite1`: soup-lite, 983 iterations;
- `pipeline.sh`: the chained prune / refit / held-out / panel / freeze / het steps, done through stage s1;
- `prune/T.json`: soup2's final values;
- helpers: `mk_soup.py` (builds a soup tree with chosen members, `VALUES=` / `NOTUNE=` to freeze), `setcfg.py`,
  `soupkit.py` and `members.py` (member -> params, off values);
- `logs/`: every checkpoint and bisect A/B.

Bots: `variants/oc-soup2-tt`, the 92-param tunified start; `variants/oc-soup-lite`, 58 params, identical to
oc-base10 at 100M; `variants/oc-soup-T`, soup2's final, tunified; `variants/oc-soup2-ck*` and `oc-lite1-ck*`, the
checkpoints.

Design note. With the `c_min` 0.15 floor, every gate within 0.15 of 0.5 is on in a random half of the candidates: a
random-balance design. Bad gates then add variance to every continuous gradient, which is why the M tier was compiled
out, not left to the tuner.
