"""Loaders for the v118b trace runs (replays/v118b/runs/<NAME>/<key>/trace.stdout.gz + direct.json)."""
import gzip, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "replays/v118b/runs"

BRANCH = {"-": "none", "C": "chase", "A": "attack", "R": "retreat", "F": "farm", "B": "bank", "W": "wait_altar", "U": "guard_altar",
          "T": "tribute_kept", "t": "tribute_cancelled", "K": "recall_kept", "k": "recall_cancelled", "H": "mend", "S": "shop",
          "P": "hold", "Q": "capture_recall", "G": "siege", "X": "contest", "E": "stop_ender", "h": "willow_support", "r": "prism_recovery"}


def validation(name):
    p = RUNS / name / "direct_validation.json"
    return json.loads(p.read_text()) if p.exists() else {}


def trusted(name, key):
    p = RUNS / name / key / "direct.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("ladder_trusted_through")


def lines(name, key, tags=None):
    p = RUNS / name / key / "trace.stdout.gz"
    if not p.exists():
        return
    with gzip.open(p, "rt", errors="replace") as f:
        for line in f:
            w = line.split()
            if w and (tags is None or w[0] in tags):
                yield w


def branches(name, key):
    """{(round, champion id): branch letter} from the D lines."""
    out = {}
    for w in lines(name, key, {"D"}):
        try:
            out[(int(w[1]), int(w[2]))] = w[3]
        except (ValueError, IndexError):
            pass
    return out
