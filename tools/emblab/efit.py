"""Emblem lab round 5: estimates and allocation for the edit lab (elab.py).

    py tools/emblab/efit.py fit  --lab NAME [--from B] [--to B] [--by opp|picks] [--gate] [--top N]
    py tools/emblab/efit.py step --lab NAME      # the screen's allocation step: reads stage.json, writes alloc.json

Model: a Bradley-Terry logistic over games. logit P(A wins) = side[opponent kind, picks]
  + s x (lab[kind, picks] + body[kind, index] + sum over the lab team's picks of type[kind, pick] + sum of its edits' beta)
with s = +1 / -1 for the lab team on A / B; in a mirror game both teams' terms enter with opposite signs. An edit's
beta is its effect on a team carrying it; points = 25 beta (the win-rate change at 50%). A typed edit (need) is only
ever on teams drafting its pick, so its beta is the effect on those teams; its value to the bot, `pts`, is that times
f, the share of teams drafting the pick. n_eff = (50 / se of pts)^2: the team-games an untyped edit would need for
that precision, the unit of the screen's targets.

The screen (stage.json: stages [[n_eff target, keep]], cumulative estimates): when every edit alive has the stage's
n_eff, the best `keep` by pts stay. Each step asks, per edit, for the appearances that bring it to the target,
counting those planned and not yet merged; spare room goes to the provisional leaders' next stage."""
import argparse, collections, json, math, os, pickle, sys
from pathlib import Path

# On a box full of games a BLAS thread per core spins for minutes on a solve that takes a second.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import edits as ed  # noqa: E402

LABS = ROOT / "replays" / "emblab"
PICKS = ["ryth", "vesper_vale", "vendetta", "cassi_and_issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "heart_of_ruin"]
EARLY = 5
FLOOR = 40


def load(lab):
    """Game tuples (batch, kind, picks, lab on A, lab on B, body, A wins, A's picks, B's picks, A's edits, B's edits),
    parsed once (efit-cache.pkl keeps what games.jsonl already held)."""
    path, cache = lab / "games.jsonl", lab / "efit-cache.pkl"
    at, kinds, rows = 0, [], []
    if cache.is_file():
        at, kinds, rows = pickle.loads(cache.read_bytes())
        if at > path.stat().st_size:
            at, kinds, rows = 0, [], []
    with open(path, "rb") as f:
        f.seek(at)
        for line in f:
            if not line.endswith(b"\n"):
                break
            at += len(line)
            g = json.loads(line)
            if "winner" not in g or g["rounds"] <= EARLY:
                continue
            if g["opp"] not in kinds:
                kinds.append(g["opp"])
            team = lambda s: tuple(PICKS.index(c) for c in g[s]) if s in g["us"] else ()  # noqa: E731
            rows.append((g["batch"], kinds.index(g["opp"]), g["picks"], "A" in g["us"], "B" in g["us"], g.get("body", 0), g["winner"] == 0,
                         team("A"), team("B"), tuple(g.get("eA", ())), tuple(g.get("eB", ()))))
    cache.write_bytes(pickle.dumps((at, kinds, rows)))
    return kinds, rows


class Fit:
    def __init__(self, kinds, rows, edits, by=None, split=()):
        """by: 'opp' or 'picks' gives every edit a beta per opponent kind or pick count; split: edit ids that get one
        beta alone on a team and another with co-edits (the additivity check)."""
        self.kinds, self.edits = kinds, {e["id"]: e for e in edits}
        cols, ri, ci, vals, y = {}, [], [], [], []
        col = lambda *k: cols.setdefault(k, len(cols))  # noqa: E731
        self.n = collections.Counter()
        self.teams = self.holding = None
        teams, holding = 0, collections.Counter()
        for r, (batch, kind, picks, on_a, on_b, body, a_wins, ta, tb, ea, eb) in enumerate(rows):
            y.append(a_wins)
            ri.append(r), ci.append(col("side", kind, picks)), vals.append(1.0)
            mirror = on_a and on_b
            for s, on, team, es in ((1.0, on_a, ta, ea), (-1.0, on_b, tb, eb)):
                if not on:
                    continue
                teams += 1
                if not mirror:
                    ri.append(r), ci.append(col("lab", kind, picks)), vals.append(s)
                    if body:
                        ri.append(r), ci.append(col("body", kind, body)), vals.append(s)
                for c in team:
                    holding[c] += 1
                    ri.append(r), ci.append(col("type", kind, c)), vals.append(s)
                for e in es:
                    group = kinds[kind] if by == "opp" else picks if by == "picks" else None
                    key = ("edit", e, "alone" if len(es) == 1 else "with") if e in split else ("edit", e, group)
                    self.n[key[1:]] += 1
                    ri.append(r), ci.append(col(*key)), vals.append(s)
        self.cols, self.teams, self.holding = cols, teams, holding
        self.games = len(rows)
        if not rows:  # a phase's first step: nothing played yet
            self.beta, self.cov = np.zeros(0), np.zeros((0, 0))
            return
        X = sp.csr_matrix((vals, (ri, ci)), shape=(len(rows), len(cols)))  # duplicates (a mirror's equal terms) sum, cancelling
        y = np.array(y, float)
        b = np.zeros(len(cols))
        lam = 1e-4
        for _ in range(12):
            p = 1 / (1 + np.exp(-(X @ b)))
            H = (X.T @ X.multiply((p * (1 - p))[:, None])).toarray() + lam * np.eye(len(cols))
            step = np.linalg.solve(H, X.T @ (y - p) - lam * b)
            b += step
            if np.abs(step).max() < 1e-7:
                break
        self.beta, self.cov = b, np.linalg.inv(H)
        self.games = len(rows)

    def share(self, e):
        """f: the share of lab teams that can carry edit e."""
        need = self.edits[e]["need"]
        return 1.0 if need is None else self.holding[PICKS.index(need)] / max(1, self.teams)

    def rows(self):
        """Per edit column: id, group, n, f, points on carrying teams and their se, pts (x f) and its se."""
        out = []
        for key, c in self.cols.items():
            if key[0] != "edit":
                continue
            e, group = key[1], key[2]
            f = self.share(e)
            act, se = 25 * self.beta[c], 25 * math.sqrt(self.cov[c, c])
            out.append({"id": e, "name": self.edits[e]["name"], "tier": self.edits[e]["tier"], "group": group, "n": self.n[(e, group)], "f": f,
                        "act": act, "act_se": se, "pts": act * f, "se": se * f, "z": act / se if se else 0.0,
                        "n_eff": (50 / (se * f)) ** 2 if se else 0.0, "expect": self.edits[e]["expect"]})
        return out


def batches(rows, lo, hi):
    return [r for r in rows if (lo is None or r[0] >= lo) and (hi is None or r[0] <= hi)]


def show(rs, top=None):
    rs = sorted(rs, key=lambda r: -r["pts"])
    for r in rs if top is None else rs[:top]:
        print(f"{r['id']:4} {r['tier']:10} {r['name']:34} {str(r['group'] or ''):6} n {r['n']:7} f {r['f']:.2f}  pts {r['pts']:+6.2f} ± {r['se']:.2f}  z {r['z']:+5.1f}"
              + (f"  A/B {r['expect']:+.1f}" if r["expect"] is not None else ""))


def gate(kinds, rows, edits, expect):
    """The calibration gate's numbers (PLAN-round5.md section 5)."""
    fit = Fit(kinds, rows, edits)
    rs = {r["name"]: r for r in fit.rows()}
    print(f"{fit.games} games, {fit.teams} lab teams")
    anchors = [(n, rs[n], x) for n, x in expect.items() if n in rs]
    print("anchors (lab against the A/B on the same base):")
    for n, r, x in anchors:
        print(f"  {n:28} lab {r['pts']:+6.2f} ± {r['se']:.2f}   A/B {x:+6.2f}   gap {r['pts'] - x:+5.2f}")
    if anchors:
        print(f"  rms gap {math.sqrt(np.mean([(r['pts'] - x) ** 2 for _, r, x in anchors])):.2f} over {len(anchors)}; "
              f"lab on A/B slope {np.polyfit([x for _, _, x in anchors], [r['pts'] for _, r, _ in anchors], 1)[0]:.2f}")
    pl = [r for r in rs.values() if r["tier"] == "placebo"]
    if pl:
        w = np.array([1 / r["act_se"] ** 2 for r in pl])
        mean = float(np.sum(w * [r["act"] for r in pl]) / w.sum())
        print(f"placebos: mean {mean:+.3f} ± {1 / math.sqrt(w.sum()):.3f} on carrying teams, z {[round(r['z'], 1) for r in pl]}")
    co = Fit(kinds, rows, edits, split=[e["id"] for e in edits if e["tier"] == "anchor"])
    print("an anchor alone on a team against with co-edits:")
    for e in edits:
        a, w = co.cols.get(("edit", e["id"], "alone")), co.cols.get(("edit", e["id"], "with"))
        if a is None or w is None:
            continue
        d = 25 * (co.beta[w] - co.beta[a])
        se = 25 * math.sqrt(co.cov[a, a] + co.cov[w, w] - 2 * co.cov[a, w])
        print(f"  {e['name']:28} alone {25 * co.beta[a]:+6.2f} (n {co.n[(e['id'], 'alone')]})  with {25 * co.beta[w]:+6.2f} (n {co.n[(e['id'], 'with')]})  "
              f"diff {d:+5.2f} ± {se:.2f} (z {d / se:+.1f})")


def planned(lab):
    """Appearances per edit in batches planned and not yet merged."""
    out = collections.Counter()
    for bdir in sorted((lab / "batches").glob("b[0-9][0-9][0-9]")):
        if (bdir / "plan.json").is_file() and not (bdir / "merged").is_file():
            for g in json.loads((bdir / "plan.json").read_text())["games"]:
                for s in g["us"]:
                    out.update(g.get(f"e{s}", ()))
    return out


def step(lab, cfg, reg):
    """One allocation step of the screen."""
    st = json.loads((lab / "stage.json").read_text())
    kinds, rows = load(lab)
    # The share of teams drafting each pick, from every game: a phase's first step has none of its own.
    held, teams = collections.Counter(), 0
    for r in rows[:400000]:
        for on, team in ((r[3], r[7]), (r[4], r[8])):
            if on:
                teams += 1
                held.update(team)
    by_id = {e["id"]: e for e in reg["edits"]}
    prior_f = lambda e: 1.0 if by_id[e]["need"] is None else held[PICKS.index(by_id[e]["need"])] / max(1, teams)  # noqa: E731
    rows = batches(rows, st.get("from"), None)
    fit = Fit(kinds, rows, reg["edits"])
    rs = {r["id"]: r for r in fit.rows()}
    alive = st["alive"]
    zero = {"pts": 0.0, "se": 99.0, "n_eff": 0.0, "n": 0}
    get = lambda e: rs.get(e, zero)  # noqa: E731
    msg = []
    while st["stage"] < len(st["stages"]):
        target, keep = st["stages"][st["stage"]]
        if min(get(e)["n_eff"] for e in alive) < 0.97 * target or min(get(e)["n"] for e in alive) < FLOOR:
            break
        ranked = sorted(alive, key=lambda e: -get(e)["pts"])
        cut = get(ranked[keep - 1])["pts"] if len(ranked) >= keep else None
        st["history"].append({"stage": st["stage"], "target": target, "games": fit.games, "kept": ranked[:keep], "dropped": ranked[keep:],
                              "cut": cut, "est": {e: [round(get(e)["pts"], 3), round(get(e)["se"], 3)] for e in alive}})
        msg.append(f"stage {st['stage']} done at {fit.games} games: {len(alive)} -> {min(keep, len(alive))}, cut at {cut if cut is None else round(cut, 2)}")
        alive = st["alive"] = ranked[:keep]
        st["stage"] += 1
    inflight = planned(lab)
    f = {e: fit.share(e) if fit.teams else prior_f(e) for e in alive}
    # n_eff an appearance: the fit's own where it has data (co-assignment costs a little), else 1 / f^2.
    rate = {e: get(e)["n_eff"] / get(e)["n"] if get(e)["n"] > 300 else 1 / max(f[e], 0.02) ** 2 for e in alive}
    pred = {e: get(e)["n_eff"] + inflight[e] * rate[e] for e in alive}
    quota = {}
    if st["stage"] < len(st["stages"]):
        target, keep = st["stages"][st["stage"]]
        # At least FLOOR appearances each: a rare pick's typed edit reaches its n_eff on a handful of games.
        quota = {e: max(max(target - pred[e], 0) / rate[e], FLOOR - get(e)["n"] - inflight[e], 0) for e in alive}
        cap = st.get("capacity", 200000)
        spare = cap - sum(quota.values())
        if spare > 0 and st["stage"] + 1 < len(st["stages"]):
            nxt = st["stages"][st["stage"] + 1][0]
            lead = sorted(alive, key=lambda e: -get(e)["pts"])[:keep]
            more = {e: max(nxt - max(pred[e], target), 0) / rate[e] for e in lead}
            scale = min(1.0, spare / max(1.0, sum(more.values())))
            for e in lead:
                quota[e] += more[e] * scale
    # stage.json "extra" {edit id: appearances a batch}: more data for an edit whatever its stage (a placebo under watch).
    for e, q in st.get("extra", {}).items():
        quota[int(e)] = quota.get(int(e), 0) + q
    # Never more than a batch holds: scaled down together, so the edits that place easily (flags, single cells) run
    # out early in the batch and its later teams go to the ones that conflict with most (the inserts) or need a pick.
    total = sum(quota.values())
    if total > st.get("capacity", 200000):
        quota = {e: q * st["capacity"] / total for e, q in quota.items()}
    quota = {str(e): math.ceil(q) for e, q in quota.items() if q > 0}
    done = st["stage"] >= len(st["stages"])
    (lab / "alloc.json").write_text(json.dumps({"label": f"screen-s{st['stage']}", "absolute": True, "active": quota}) + "\n")
    (lab / "stage.json").write_text(json.dumps(st) + "\n")
    if done or not quota:
        (lab / "stop").write_text("screen finished\n")
    lo = min((get(e)["n_eff"] for e in alive), default=0)
    print("; ".join(msg + [f"stage {st['stage']}{' (finished)' if done else ''}: {len(alive)} alive, least n_eff {lo:.0f}, "
                           f"{fit.games} games, next batch asks {sum(quota.values()):.0f} appearances over {len(quota)} edits"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["fit", "step"])
    ap.add_argument("--lab", required=True)
    ap.add_argument("--from", dest="lo", type=int)
    ap.add_argument("--to", dest="hi", type=int)
    ap.add_argument("--by", choices=["opp", "picks"])
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--top", type=int)
    ap.add_argument("--json")
    a = ap.parse_args()
    lab = LABS / a.lab
    cfg = json.loads((lab / "config.json").read_text())
    reg = ed.load(ROOT / cfg["registry"])
    if a.command == "step":
        step(lab, cfg, reg)
        return
    kinds, rows = load(lab)
    rows = batches(rows, a.lo, a.hi)
    if a.gate:
        expect = {e["name"]: e["expect"] for e in reg["edits"] if e["expect"] is not None}
        if (lab / "expect.json").is_file():  # A/Bs re-measured on this lab's base
            expect.update(json.loads((lab / "expect.json").read_text()))
        gate(kinds, rows, reg["edits"], expect)
        return
    fit = Fit(kinds, rows, reg["edits"], by=a.by)
    rs = fit.rows()
    print(f"{fit.games} games, {fit.teams} lab teams; kinds {kinds}")
    show(rs, a.top)
    if a.json:
        Path(a.json).write_text(json.dumps(rs) + "\n")


if __name__ == "__main__":
    main()
