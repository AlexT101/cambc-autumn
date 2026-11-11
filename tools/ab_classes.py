"""CAND's win % per map class in an A/B: joins each match with its map's entry in the maps/ index.json files.

    py tools/ab_classes.py <ab name or batch dir>... [--by preset,access] [--min 4] [--list CLASS=VALUE]

Classes (--by): suite, kind, preset, access, gated, camp_mode, spawn, picks, altar_zone, economy. Ladder maps have
kind "ladder". Each row: games, CAND win %, the share of games that reached round 2000 and, when the batch has been
through tools/replay/extract.mjs, CAND's and REF's mean tributed gems.
--list prints every match of one class (e.g. --list access=teleport): map, side, winner, rounds, gems.
"""
import argparse
import collections
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = ["suite", "kind", "preset", "access", "gated", "camp_mode", "spawn", "picks", "altar_zone", "economy"]


def load_index():
    maps = {}
    for path in glob.glob(os.path.join(ROOT, "maps", "**", "index.json"), recursive=True):
        for m in json.load(open(path, encoding="utf-8")).get("maps", []):
            maps[m["file"]] = m
    return maps


def load_gems():
    """Tributed gems [A, B] by replay path, from extract.mjs's index."""
    path = os.path.join(ROOT, "replays", ".analysis", "index.json")
    if not os.path.exists(path):
        return {}
    out = {}
    for g in json.load(open(path, encoding="utf-8")).get("games", []):
        if g.get("gems") is not None:
            out[os.path.normcase(os.path.abspath(os.path.join(ROOT, g["source"])))] = g["gems"]
    return out


def batches(spec):
    if os.path.isdir(spec) and os.path.exists(os.path.join(spec, "results.json")):
        return [spec]
    summary = os.path.join(ROOT, "replays", "ab", spec, "summary.json")
    if os.path.exists(summary):
        return [os.path.join(ROOT, s["batch"]) for s in json.load(open(summary, encoding="utf-8"))["suites"]]
    sys.exit(f"no batch or A/B named {spec}")


def classify(m, entry, suite):
    if entry is None:
        return {"suite": suite, "kind": "ladder", "preset": "ladder", "access": "walk", "gated": False,
                "camp_mode": "-", "spawn": "-", "picks": "-", "altar_zone": "-", "economy": "-"}
    spec, met = entry.get("spec", {}), entry.get("metrics", {})
    preset = entry.get("preset") or ("mut-" + str(entry.get("mutate")) if entry["kind"] == "mutation" else entry["kind"])
    economy = next((p for p in ("gem-drought", "gem-flood", "gold-flood") if p == preset), "-")
    return {"suite": suite, "kind": entry["kind"], "preset": preset, "access": met.get("access"),
            "gated": bool(entry.get("gated")), "camp_mode": spec.get("camp_mode"), "spawn": met.get("spawn"),
            "picks": met.get("picks"), "altar_zone": met.get("altar_zone"), "economy": economy}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--by", default="suite,kind,preset,access,gated,camp_mode,spawn,economy")
    ap.add_argument("--min", type=int, default=4, help="hide classes with fewer games")
    ap.add_argument("--list", help="CLASS=VALUE: print each match of that class")
    args = ap.parse_args()
    index, gems = load_index(), load_gems()
    rows = []
    for spec in args.specs:
        for b in batches(spec):
            res = json.load(open(os.path.join(b, "results.json"), encoding="utf-8"))
            suite = os.path.basename(b).rsplit("-", 1)[-1]
            for m in res["matches"]:
                if m.get("winner") is None:
                    continue
                name = os.path.basename(m["map"])
                local = os.path.join(os.path.dirname(m["map"]), "index.json")
                if name not in index and os.path.exists(local):
                    for e in json.load(open(local, encoding="utf-8")).get("maps", []):
                        index.setdefault(e["file"], e)
                cand_a = m["order"][0] == 0
                g = gems.get(os.path.normcase(os.path.abspath(m["replay"])))
                c, r = (g if cand_a else g[::-1]) if g else (None, None)
                rows.append({"map": name, "cand_a": cand_a, "win": m["winner"] == 0, "rounds": m["rounds"],
                             "cg": c, "rg": r, **classify(m, index.get(name), suite)})
    if args.list:
        k, v = args.list.split("=", 1)
        for x in sorted((x for x in rows if str(x[k]) == v), key=lambda x: x["map"]):
            print(f"{x['map']:45} {'A' if x['cand_a'] else 'B'} {'WIN ' if x['win'] else 'loss'} r{x['rounds']:4} "
                  f"gems {x['cg']}-{x['rg']}")
        return
    print(f"{len(rows)} games, CAND {100 * sum(x['win'] for x in rows) / max(1, len(rows)):.1f}%")
    for key in args.by.split(","):
        groups = collections.defaultdict(list)
        for x in rows:
            groups[str(x[key])].append(x)
        print(f"\n{key:>14} {'games':>5} {'win%':>6} {'r2000%':>6} {'gems C':>7} {'gems R':>7}")
        for v, xs in sorted(groups.items(), key=lambda kv: sum(x["win"] for x in kv[1]) / len(kv[1])):
            if len(xs) < args.min:
                continue
            gx = [x for x in xs if x["cg"] is not None]
            cg = f"{sum(x['cg'] for x in gx) / len(gx):7.0f}" if gx else "      -"
            rg = f"{sum(x['rg'] for x in gx) / len(gx):7.0f}" if gx else "      -"
            print(f"{v[:14]:>14} {len(xs):5} {100 * sum(x['win'] for x in xs) / len(xs):6.1f} "
                  f"{100 * sum(x['rounds'] >= 2000 for x in xs) / len(xs):6.1f} {cg} {rg}")


if __name__ == "__main__":
    main()
