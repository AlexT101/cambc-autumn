"""tools/tune/tune.py with fresh maps every iteration: iteration k plays maps [k n, (k + 1) n) of the config's
`fresh_pool` (directories, their maps sorted then shuffled by `fresh_seed`), so no map is played in two iterations.
Two runs with the same fresh_pool and fresh_seed play the same maps at the same k (sides and sign vectors come from
their own `seed`). The run stops when the pool runs out.

    py research/tune-combo3-2026-11-06/tune_fresh.py init ...   # as tune.py init, then add fresh_pool/fresh_seed to config.json
    py research/tune-combo3-2026-11-06/tune_fresh.py run --run R --iters N
"""
import random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "tune"))
import tune  # noqa: E402

_POOLS = {}


def fresh_maps(cfg):
    key = (tuple(cfg["fresh_pool"]), cfg.get("fresh_seed", 0))
    if key not in _POOLS:
        maps = tune.maps_in(cfg["fresh_pool"])
        random.Random(key[1]).shuffle(maps)
        _POOLS[key] = maps
    return _POOLS[key]


_plan = tune.plan


def plan(cfg, k, x):
    # The sign vectors are drawn before the games, so drawing no games leaves them as tune.py's.
    deltas, cn, cands, _ = _plan(dict(cfg, maps_per_iter=0), k, x)
    if "fresh_pool" not in cfg:
        raise SystemExit("config.json has no fresh_pool")
    n = cfg["maps_per_iter"]
    maps = fresh_maps(cfg)
    if (k + 1) * n > len(maps):
        raise SystemExit(f"fresh pool exhausted at iteration {k} ({len(maps)} maps)")
    rng = random.Random(cfg["seed"] * 7919 + k)
    games = [(m, opp, rng.randrange(2)) for m in maps[k * n:(k + 1) * n] for opp in cfg["opps"]]
    return deltas, cn, cands, games


tune.plan = plan

if __name__ == "__main__":
    tune.main()
