"""casts.py BATCH_DIR [0|1|both]: camp-cast statistics per champion type for one side of a local batch.

Casts (damage/stun spells) per 100 alive rounds, camp damage share dealt from distance 4+, camp stuns per
game, and missed opportunities: turns with a damage/stun slot ready and a live camp within 4 (awake, or
being hit by us) but no damage/stun cast, split by the likely reason."""
import json, gzip, sys, collections
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AN = ROOT / "replays" / ".analysis"
SPELL_SLOTS = {"Cassi": (0, 1), "Stellar": (0, 1), "Ryth": (0,), "Tavi": (1,), "Ren": (0,), "Prism": (0, 1), "Marcella": (1,)}
STUN_AB = {"CC"}
DMG_AB = {"Damage", "AoE damage", "CC"}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    gdir, team = args
    d = AN / gdir
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mp = json.loads((d / meta["mapFile"]).resolve().read_text(encoding="utf-8"))
    camps = {c["id"]: c for c in mp["camps"]}
    gcamps = collections.defaultdict(list)
    for c in mp["camps"]:
        gcamps[c["group"]].append(c["id"])
    R = json.load(gzip.open(d / "rounds.json.gz"))
    ev = sorted((json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")), key=lambda e: e["s"])
    rounds = R["round"]
    nR = len(rounds)
    alive = set(camps)
    alive_at = {}
    acts = collections.defaultdict(list)
    ei = 0
    for r in rounds:
        while ei < len(ev) and (ev[ei]["r"] < r or (ev[ei]["r"] == r and ev[ei]["t"] == -1)):
            e = ev[ei]
            if e["k"] == "camp_death": alive.discard(e["camp"])
            elif e["k"] == "group_respawn": alive.update(gcamps[e["g"]])
            ei += 1
        alive_at[r] = frozenset(alive)
        while ei < len(ev) and ev[ei]["r"] == r:
            e = ev[ei]
            if e["k"] == "camp_death": alive.discard(e["camp"])
            elif e["k"] == "group_respawn": alive.update(gcamps[e["g"]])
            if "a" in e: acts[(r, e["a"])].append(e)
            ei += 1
    ia = R["groupCols"].index("awake")
    rows_by_round = collections.defaultdict(list)
    for row in R["groups"]:
        rows_by_round[row[0]].append(row)
    awake_end = {}
    cur = {}
    for r in rounds:
        for row in rows_by_round.get(r, []):
            cur[row[1]] = row[ia]
        awake_end[r] = dict(cur)
    champs = R["champions"]
    byid = {c["id"]: c for c in champs}
    names = {c["id"]: c["name"] for c in meta["champions"]}
    out = collections.defaultdict(collections.Counter)
    for c in champs:
        if c["team"] != team: continue
        nm = names[c["id"]]
        S = out[nm]
        slots = SPELL_SLOTS.get(nm, ())
        for i in range(1, nR):
            r = rounds[i]
            if not c["alive"][i] or not c["alive"][i - 1]:
                continue
            S["alive"] += 1
            evr = acts.get((r, c["id"]), [])
            casts = [e for e in evr if e["k"] == "cast" and e.get("ab") in DMG_AB]
            moved = any(e["k"] == "move" for e in evr)
            camp_hit = False
            for e in evr:
                if e["k"] in ("attack", "cast") and e.get("cdmg"):
                    for cid, amt in e["cdmg"]:
                        cp = camps.get(cid)
                        if not cp: continue
                        S["cdmg_" + ("spell" if e["k"] == "cast" else "basic")] += amt
                        if cheb(e["f"], (cp["x"], cp["y"])) >= 4: S["cdmg_far"] += amt
                        S["cdmg"] += amt
                        camp_hit = True
            for e in casts:
                S["casts"] += 1
                if e.get("cdmg") or "camp" in e:
                    S["casts_camp"] += 1
                    if e["ab"] in STUN_AB or nm == "Ryth": S["stuns_camp"] += 1
                elif e.get("dmg") or "tgt" in e:
                    S["casts_champ"] += 1
                else:
                    S["casts_none"] += 1
            if c["turn"][i] not in (1, 2) or c["chan"][i - 1] == 2:
                continue
            ready = [s for s in slots if c["cd%d" % s][i - 1] == 0]
            if not ready:
                continue
            p = (c["x"][i - 1], c["y"][i - 1])
            near = [cid for cid in alive_at[r] if cheb(p, (camps[cid]["x"], camps[cid]["y"])) <= 4]
            if not near:
                continue
            aw = awake_end.get(rounds[i - 1], {})
            if not camp_hit and not any(aw.get(camps[cid]["group"], 0) == 1 for cid in near):
                continue
            S["opp"] += 1
            dmin = min(cheb(p, (camps[cid]["x"], camps[cid]["y"])) for cid in near)
            S["opp_d4" if dmin >= 4 else "opp_d3"] += 1
            if any(e.get("cdmg") or "camp" in e for e in casts):
                S["opp_cast"] += 1
                continue
            if casts:
                S["opp_champ"] += 1
                continue
            sees = c["sees"][i] or []
            enemy_close = any(byid[e]["alive"][i - 1] and cheb(p, (byid[e]["x"][i - 1], byid[e]["y"][i - 1])) <= 6 for e in sees)
            reason = "enemy" if enemy_close else "walked" if moved else "no_hit" if not camp_hit else "other"
            S["miss_" + reason] += 1
            S["miss_" + reason + ("_d4" if dmin >= 4 else "_d3")] += 1
            q = (c["x"][i], c["y"][i])
            dafter = min((cheb(q, (camps[cid]["x"], camps[cid]["y"])) for cid in alive_at[r]), default=9)
            hit_types = "".join(sorted({camps[cid]["type"][:2] for e in evr if e.get("cdmg") for cid, _ in e["cdmg"] if cid in camps}))
            S["X%s d%d->%d hit%d slots%s %s" % (reason, dmin, min(dafter, 9), camp_hit, "".join(map(str, ready)), hit_types)] += 1
    return dict(out)


def main():
    batch = Path(sys.argv[1]).resolve()
    which = sys.argv[2] if len(sys.argv) > 2 else "0"
    idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
    jobs = []
    for g in idx["games"]:
        src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
        if src.resolve().parent != batch: continue
        a_is_bot0 = src.stem.endswith("-12")
        for b in ((0, 1) if which == "both" else (int(which),)):
            jobs.append((g["dir"], 0 if (b == 0) == a_is_bot0 else 1))
    with Pool(8) as p:
        res = p.map(one, jobs, chunksize=4)
    T = collections.defaultdict(collections.Counter)
    games = collections.Counter()
    for r in res:
        for nm, S in r.items():
            T[nm].update(S); games[nm] += 1
            T["ALL"].update(S)
        games["ALL"] += 1
    print(f"{len(jobs)} team-games")
    print("type      games cast/100 camp/100 champ/100 campStun/g far%  spell%  opp/100 cast%  miss%: enemy walked no_hit other | opp d4 share, miss walked d4/d3")
    for nm in sorted(T, key=lambda n: -T[n]["alive"]):
        S = T[nm]; a = max(1, S["alive"]); g = games[nm]; o = max(1, S["opp"])
        print(f"{nm:9s} {g:5d} {100*S['casts']/a:8.2f} {100*S['casts_camp']/a:8.2f} {100*S['casts_champ']/a:8.2f} {S['stuns_camp']/g:9.1f}"
              f" {100*S['cdmg_far']/max(1,S['cdmg']):5.1f} {100*S['cdmg_spell']/max(1,S['cdmg']):6.1f} {100*S['opp']/a:7.2f} {100*S['opp_cast']/o:5.1f}"
              f"        {100*S['miss_enemy']/o:5.1f} {100*S['miss_walked']/o:6.1f} {100*S['miss_no_hit']/o:6.1f} {100*S['miss_other']/o:5.1f}"
              f" | {100*S['opp_d4']/o:4.1f}  {S['miss_walked_d4']}/{S['miss_walked_d3']} other {S['miss_other_d4']}/{S['miss_other_d3']} nohit {S['miss_no_hit_d4']}/{S['miss_no_hit_d3']}")
    if "-v" in sys.argv: detail(T)


def detail(T):
    for nm in T:
        if nm == "ALL": continue
        xs = sorted(((v, k) for k, v in T[nm].items() if k.startswith("X")), reverse=True)[:12]
        if xs: print(nm, "  ".join(f"{k[1:]}:{v}" for v, k in xs))


if __name__ == "__main__":
    main()
