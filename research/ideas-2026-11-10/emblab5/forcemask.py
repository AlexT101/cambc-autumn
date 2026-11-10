"""Audit 5 of round 4 (tools/emblab/PLAN-round5.md): is self-healing real beyond deletions? On the dense labs' games
alone (no fit, no propensities): a logistic of the win on each lab team's force masks, the cells whose emblem was
drawn at random in place of the table's. Terms a team: forced cells; forced Collectors cells (the table's arm there
is Collectors); rows with one Collectors cell, forced; rows with several, all forced. If the base heals a single
deviation, a forced Collectors cell costs little while "all of a row's forced" costs much more than their sum. Every
term is centred on its expectation given the team, so team composition (round 4 randomised drafts) cancels.
    py forcemask.py LAB..."""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/emblab"))
import edits as ed
table = ed.read_table((ROOT / "bots/variants/oc-campsh-498/src/economy/emblem_table.h").read_text())  # round 4's base table
COLL = ed.FAM["collectors"]
NAMES = ["forced cells", "forced Collectors cells", "single Collectors cell forced (rows)", "all of several Collectors cells forced (rows)"]

def feats(team, force, mode):
    """Each term less its expectation given the team: a cell is forced with a known chance (0.35 at ordinal 0, 0.5
    after; 0.2 on a uniform-mode team), so what is left is the random draw alone, whatever the team's types."""
    p = len(team) - 3
    pk = [0.2] * 12 if mode else [0.35] + [0.5] * 11
    x = np.zeros(4)
    for i, pick in enumerate(team):
        for row, name in ([(i, "cassi"), (5, "issac")] if pick == "cassi_and_issac" else [(i, pick)]):
            cells = [k for k, a in enumerate(table[p][ed.TYPES.index(name)]) if a != 255 and a // 3 == COLL]
            m = force[row]
            x[0] += bin(m).count("1") - sum(pk)
            hit = [k for k in cells if m >> k & 1]
            x[1] += len(hit) - sum(pk[k] for k in cells)
            if len(cells) == 1: x[2] += len(hit) - pk[cells[0]]
            if len(cells) > 1: x[3] += (len(hit) == len(cells)) - math.prod(pk[k] for k in cells)
    return x

X, y = [], []
kinds = {}
for lab in sys.argv[1:]:
    for line in open(ROOT / "replays/emblab" / lab / "games.jsonl"):
        g = json.loads(line)
        if "winner" not in g or len(g.get("A", [])) not in (3, 4, 5): continue
        k = kinds.setdefault(g["opp"], len(kinds))
        row = np.zeros(4 + 8)
        row[4 + k] = 1                                    # side A's edge against this kind
        for s, sign in (("A", 1.0), ("B", -1.0)):
            if s in g["us"]:
                row[:4] += sign * feats(g[s], g[f"force{s}"], g[f"mode{s}"])
                if g["opp"] != "self": row[8 + k] = sign  # the lab against a body
        X.append(row); y.append(g["winner"] == 0)
X, y = np.array(X), np.array(y, float)
b = np.zeros(X.shape[1])
for _ in range(20):
    p = 1 / (1 + np.exp(-X @ b))
    H = (X * (p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(len(b))
    step = np.linalg.solve(H, X.T @ (y - p)); b += step
    if abs(step).max() < 1e-9: break
cov = np.linalg.inv(H)
print(f"{len(y)} games of {sys.argv[1:]}; mean forced cells a team {np.abs(X[:, 0]).mean():.1f}")
for i, n in enumerate(NAMES):
    print(f"  {n:46s} {25 * b[i]:+.3f} ± {25 * math.sqrt(cov[i, i]):.3f} points each")
