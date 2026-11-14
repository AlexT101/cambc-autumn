"""Staged draft search on draft_search.py (research/notes/DRAFT.md, Phase 3). From the repo root:

  DS_SRC=bots/variants/astraeus-<sha7> DS_DB=replays/ds/<name>.jsonl py tools/variants/ds_run.py CMD --picks P ...
  run --picks 3,4 --n 160                 screen every CANDS entry of each count on the first 160 jobs of its pool
  run --picks 5 --from 160 --cands a,b    the rest of the pool for survivors
  run --picks 5 --fresh maps/suites/fresh/fresh-1303   the fresh suite instead of the base pool
  report ...                              the same tables without playing
  combo --picks 5 --draft "prism vendetta marcella willow hor"   an ad hoc draft
  vehicle --picks 5 --cands a             a bot with only that change, for ab.py --suites ds.suite_dir(5, ...)

The incumbent (the source's params.h) plays the same jobs, so comparisons are paired. Several pick counts in one
--picks share vehicles (one candidate of each count per build). --cands names are looked up per pick count."""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_search as ds  # noqa: E402

# Single swaps from the Phase 3 incumbents (reasons in DRAFT.md).
CANDS = {
    3: {  # Marc Vend HoR
        "vesp-marc": "vesper vendetta hor",
        "tavi-hor": "marcella vendetta tavi",
        "cass-hor": "marcella vendetta cassi",
        "cass-marc": "cassi vendetta hor",
        "stel-hor": "marcella vendetta stellar",
        "ryth-hor": "marcella vendetta ryth",
        "vesp-vend": "marcella vesper hor",
    },
    4: {  # Pris Vesp Marc HoR
        "vend-vesp": "prism vendetta marcella hor",
        "vend-pris": "vendetta vesper marcella hor",
        "cass-pris": "cassi vesper marcella hor",
        "cass-vesp": "prism cassi marcella hor",
        "tavi-vesp": "prism tavi marcella hor",
        "will-vesp": "prism willow marcella hor",
        "ryth-vesp": "prism ryth marcella hor",
    },
    5: {  # Pris Vesp Marc Will HoR
        "vend-vesp": "prism vendetta marcella willow hor",
        "vend-pris": "vendetta vesper marcella willow hor",
        "vend-will": "prism vesper marcella vendetta hor",
        "tavi-pris": "tavi vesper marcella willow hor",
        "cass-vesp": "prism cassi marcella willow hor",
        "ryth-will": "prism vesper marcella ryth hor",
        "varg-vesp": "prism varg marcella willow hor",
    },
}


def jobs(picks, n=None, start=0, fresh=None):
    j = ds.jobs_for(picks, {3: [], 4: [], 5: []}, [fresh]) if fresh else ds.jobs_for(picks)
    return j[start:start + n if n else None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "report", "combo", "vehicle"])
    ap.add_argument("--picks", required=True, help="e.g. 5 or 3,4")
    ap.add_argument("--cands", default="", help="CANDS names; default all (run/report)")
    ap.add_argument("--draft", help="an ad hoc draft (combo)")
    ap.add_argument("--n", type=int)
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--fresh")
    ap.add_argument("--threads", type=int, default=11)
    a = ap.parse_args()
    picks_list = [int(p) for p in a.picks.split(",")]
    names = [c for c in a.cands.split(",") if c]
    unknown = [c for c in names if not any(c in CANDS[p] for p in picks_list)]
    if unknown:
        sys.exit(f"unknown candidates for picks {a.picks}: {unknown}")
    spec = {}
    for picks in picks_list:
        sel = [c for c in names if c in CANDS[picks]] if names else \
            (list(CANDS[picks]) if a.cmd in ("run", "report") else [])
        cands = [(c, ds.D(CANDS[picks][c])) for c in sel] + ([("adhoc", ds.D(a.draft))] if a.draft else [])
        spec[picks] = (cands, jobs(picks, a.n, a.start, a.fresh))
    if a.cmd == "vehicle":
        for picks, (cands, _) in spec.items():
            for name, d in cands:
                path, new = ds.make_bot({**ds.INCUMBENT, picks: d})
                if new:
                    ds.build_all([path])
                print(picks, name, path.relative_to(ds.ROOT / "bots").as_posix())
        return
    if a.cmd in ("run", "combo"):
        ds.run([r for p, (cands, j) in spec.items() if cands
                for r in [(p, ds.INCUMBENT[p], (), j)] + [(p, d, (), j) for _, d in cands]], threads=a.threads)
    for picks, (cands, j) in spec.items():
        if not cands:
            continue
        title = f"{'fresh ' if a.fresh else ''}jobs {a.start}-{a.start + len(j)}"
        ds.compare(picks, [(d, ()) for _, d in cands], j, title=title)
        ds.compare(picks, [(d, ()) for _, d in cands], [x for x in j if ds.slot_of(*x) in ds.TOP5],
                   title=title + " top-5 opponents")


if __name__ == "__main__":
    main()
