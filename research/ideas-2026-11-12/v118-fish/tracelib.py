"""Loader for v118's traced re-runs (tracebot.py's lines), keyed by (round, champion id).

    import tracelib as T
    tr = T.load("fb2e2eae-4")            # runs/direct; T.load(key, "direct-st") for the pass with ST / CT lines
    tr.trusted                           # the last round the re-run shares with the live game
    tr.turn(599, 3)                      # {'D': ..., 'TT': ..., 'EB': [...], 'WH': [...], 'CR': ..., 'CX': ..., 'ST': [...], 'CT': [...]}

Only rounds <= tr.trusted are evidence about the live game: tr.turn() returns None past it unless untrusted=True."""
import gzip, json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
V = REPO / "replays/v118"

FIELDS = {
    "D": ["r", "h", "branch", "farm", "claim"],
    "TT": ["r", "h", "sx", "sy", "ex", "ey", "hp", "maxhp", "gems", "gold", "branch", "score_us", "score_them", "alive", "winning"],
    "EB": ["r", "h", "e", "visible", "tracked", "x", "y", "pos_round", "hp", "maxhp", "str", "foc", "gems", "shield"],
    "WH": ["r", "h", "x", "y", "code"],
    "CR": ["r", "h", "home", "bits"],
    "CX": ["r", "h", "home"],
    "ST": ["r", "h", "x", "y", "lost", "self_falls", "tku", "tkt", "allies", "enemies", "falls", "pursued", "unseen", "hit", "key", "walking"],
    "CT": ["r", "h", "target", "tx", "ty", "lost", "self_falls", "tku", "tkt", "i", "key", "delayed", "late"],
}
WH_REASON = {0: "no", 1: "low health", 2: "pack zone", 3: "camp trap", 4: "camp fled", 5: "willow exposed", 6: "lost stand / finish heal"}
MULTI = ("EB", "WH", "ST", "CT")


def _val(x):
    try:
        return int(x)
    except ValueError:
        return x


class Trace:
    def __init__(self, key, run="direct"):
        d = V / "runs" / run / key
        self.key = key
        self.info = json.loads((d / "direct.json").read_text())
        self.trusted = self.info.get("ladder_trusted_through") or 0
        self.exact = bool(self.info.get("exact"))
        self.turns = defaultdict(dict)
        with gzip.open(d / "trace.stdout.gz", "rt", errors="replace") as f:
            for line in f:
                p = line.split()
                if not p or p[0] not in FIELDS:
                    continue
                names = FIELDS[p[0]]
                if len(p) - 1 != len(names):
                    continue
                rec = {n: _val(v) for n, v in zip(names, p[1:])}
                slot = self.turns[(rec["r"], rec["h"])]
                if p[0] in MULTI:
                    slot.setdefault(p[0], []).append(rec)
                else:
                    slot[p[0]] = rec

    def turn(self, r, h, untrusted=False):
        if r > self.trusted and not untrusted:
            return None
        return self.turns.get((r, h))

    def beliefs(self, r, h):
        t = self.turn(r, h)
        return {e["e"]: e for e in (t or {}).get("EB", [])}


def load(key, run="direct"):
    return Trace(key, run)


def validation(run="direct"):
    out = {}
    for d in sorted((V / "runs" / run).glob("*/direct.json")):
        j = json.loads(d.read_text())
        out[j["key"]] = j
    return out
