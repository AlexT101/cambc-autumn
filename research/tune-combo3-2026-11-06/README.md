Tools for research/tune-combo3-2026-11-06.md:
- `params.txt`: the 42 tuned constants (tunify.py's argument list).
- `tune_fresh.py`: tools/tune/tune.py with fresh maps every iteration (config `fresh_pool`, `fresh_seed`).
- `gradsig.py RUN`: per-constant gradient t and move; `progress.py RUN... --block N`: in-run win rate by block.
- `stop_at.sh N RUN...`: STOP each run at iteration N; `abq.sh FILE`: a queue of A/Bs (`q-untuned.txt`, `q-tuned.txt`).
- `tc3-final.json`, `tc3ctl-final.json`: the played values at iteration 500.
