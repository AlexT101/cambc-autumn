"""Paired lab score: a candidate's rollouts against its base's on the same frames, from our team's side.

    python3 research/reply-model/score.py FRAMES.jsonl CAND.jsonl BASE.jsonl TEAM [CAND2 BASE2 TEAM2 ...] [--marks 5,10,30]

Rollouts are `fastrunner scenario --hitlog --marks ...` lines (one per frame, plain mode). A team's value at a mark:
each live fighter's hp / max hp (a rollout that stopped before the mark counts its end), -1 a death, and GEM x (gems its fighters carry + gems the team tributed since the
frame). GEM is ocean's own gem_value / life_value (0.0633); 0.01 (experiments 1-2) is shown alongside. Reward =
ours - theirs; the paired difference is candidate - base, by frame, with a 95% interval.
"""
import json
import math
import sys

GEMS = [17.52141 / 276.60016, 0.01]


def max_hp(frames):
    m = {}
    with open(frames) as f:
        for line in f:
            v = json.loads(line)
            m[v["id"]] = {c["id"]: c.get("maxHp") or 1.0 for c in v["champions"]}
    return m


def values(row, mark, mh):
    """(value terms per team at the mark: hp fraction sum, deaths, gems + tributed) or None."""
    fighters = row["fighters"]
    teams = {f["id"]: f["team"] for f in fighters}
    if mark == "end":
        hp = {f["id"]: (f["hp"] if f["alive"] else None) for f in fighters}
        deaths = [sum(f["deaths"] for f in fighters if f["team"] == t) for t in (0, 1)]
        gems = row["gems"]
        trib = [row["trib"][t] - row["trib0"][t] for t in (0, 1)]
    else:
        at = row.get("at", {}).get(mark)
        if at is None:
            # The rollout stopped before the mark (apart, a team dead, the game over): its end stands.
            if row["rounds"] >= int(mark):
                return None
            return values(row, "end", mh)
        hp = {int(k): v for k, v in at["hp"].items()}
        deaths, gems = at["deaths"], at["gems"]
        trib = [at["trib"][t] - row["trib0"][t] for t in (0, 1)]
    out = []
    for t in (0, 1):
        h = sum((hp[i] / mh.get(i, 1.0)) for i in hp if teams.get(i) == t and hp[i] is not None)
        out.append((h, deaths[t], gems[t] + trib[t]))
    return out


def reward(v, team, gem):
    a, b = v[team], v[1 - team]
    return (a[0] - a[1] + gem * a[2]) - (b[0] - b[1] + gem * b[2])


def load(path):
    rows = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if "error" not in r and r.get("rollout", 0) == 0:
                rows[r["id"]] = r
    return rows


def ci(xs):
    n = len(xs)
    if n < 2:
        return float("nan"), float("nan")
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, 1.96 * sd / math.sqrt(n)


def main():
    a = sys.argv[1:]
    marks = ["5", "10", "30"]
    if "--marks" in a:
        i = a.index("--marks")
        marks = a[i + 1].split(",")
        del a[i:i + 2]
    mh = max_hp(a[0])
    trip = a[1:]
    allrows = {m: {g: [] for g in GEMS} for m in marks}
    alld = {m: [] for m in marks}
    for k in range(0, len(trip), 3):
        cand, base, team = load(trip[k]), load(trip[k + 1]), int(trip[k + 2])
        ids = sorted(set(cand) & set(base))
        print(f"{trip[k]} vs {trip[k + 1]} (team {team}): {len(ids)} frames")
        for m in marks:
            line = [f"  mark {m}:"]
            for g in GEMS:
                d = []
                for i in ids:
                    vc, vb = values(cand[i], m, mh[i]), values(base[i], m, mh[i])
                    if vc is None or vb is None:
                        continue
                    d.append(reward(vc, team, g) - reward(vb, team, g))
                mu, h = ci(d)
                allrows[m][g].extend(d)
                line.append(f"gem {g:.4f}: {mu:+.4f} +-{h:.4f} (n {len(d)})")
            dd, de = [], []
            for i in ids:
                vc, vb = values(cand[i], m, mh[i]), values(base[i], m, mh[i])
                if vc is None or vb is None:
                    continue
                dd.append(vc[team][1] - vb[team][1])
                de.append(vc[1 - team][1] - vb[1 - team][1])
                alld[m].append((dd[-1], de[-1]))
            mu, h = ci(dd)
            mu2, h2 = ci(de)
            line.append(f"our deaths {mu:+.4f} +-{h:.4f}, their deaths {mu2:+.4f} +-{h2:.4f}")
            print("  ".join(line))
    print("pooled:")
    for m in marks:
        line = [f"  mark {m}:"]
        for g in GEMS:
            mu, h = ci(allrows[m][g])
            line.append(f"gem {g:.4f}: {mu:+.4f} +-{h:.4f}")
        mu, h = ci([x[0] for x in alld[m]])
        mu2, h2 = ci([x[1] for x in alld[m]])
        line.append(f"our deaths {mu:+.4f} +-{h:.4f}, their deaths {mu2:+.4f} +-{h2:.4f}")
        print("  ".join(line))


if __name__ == "__main__":
    main()
