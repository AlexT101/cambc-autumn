"""Arms of this study from v118's live Fish r8 positions (Study A's livefork_arms.py, run from this worktree).

    python3 research/ideas-2026-11-12/r8-scale/lfork.py OUT_DIR --cands g1,phs [--forks 300,450,600,750] [--seeds 1,2]
    python3 research/ideas-2026-11-12/r8-scale/lfork.py OUT_DIR --read

Each arm (bots/variants/r8s-CAND here) and the reference (bots/variants/r8s-base = charybdis 524) is built privately in
~/tmp-offload/r8-scale/lfws (a copy of the harness workspace's SDK) and takes our side, cold, at each fork of the live
game against variants/fr8-g25 (the primary checkout's, read only). Reads only from the primary checkout: the harness
workspace replays/v118/ws (puppets, maps, the live release build), replays/forkcomp/runner and the loss classes."""
import argparse, importlib.util, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
PRIMARY = Path("/home/ubuntu/cambc-autumn")
WS = Path.home() / "tmp-offload/r8-scale/lfws"
spec = importlib.util.spec_from_file_location("lfa", PRIMARY / "research/ideas-2026-11-12/v118-fish/livefork_arms.py")
lfa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lfa)
lf = lfa.lf


def build(name, variant):
    bot = WS / "bots" / f"c-{name}"
    src = HERE / "bots/variants" / variant / "src"
    stamp = bot / "SOURCE"
    import hashlib
    h = hashlib.sha256(b"".join(f.read_bytes() for f in sorted(src.rglob("*")) if f.is_file())).hexdigest()
    if stamp.exists() and stamp.read_text() == h:
        return str(bot)
    if bot.exists():
        shutil.rmtree(bot)
    shutil.copytree(src, bot / "src")
    r = subprocess.run(["cambc", "build", f"bots/c-{name}", "--release"], cwd=WS, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    stamp.write_text(h)
    return str(bot)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--cands", default="")
    ap.add_argument("--forks", default="300,450,600,750")
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--shards", type=int, default=16)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.read:
        return lfa.read(a.out)
    cands = [c for c in a.cands.split(",") if c]
    seeds = [int(x) for x in a.seeds.split(",")]
    ref = build("ref", "r8s-base")
    built = {c: build(c, f"r8s-{c}") for c in cands}

    def lines(exp, versions, forks, limit):
        out = []
        val = {x["key"]: x for x in json.load(open(PRIMARY / "replays/v118/runs/batch/validation.json"))}
        man = {f"{g['group'][:8]}-{g['position']}": g for g in json.load(open(PRIMARY / "replays/v118/manifest.json"))["games"]}
        ws = "replays/v118/ws"
        seen = set()
        for key, g in sorted(val.items()):
            if not g["release"]["exact"]:
                continue
            cell = (g["map"], g["our_side"])
            if cell in seen:
                continue
            seen.add(cell)
            ours = 0 if g["our_side"] == "a" else 1
            opp = 1 - ours
            fk = [r for r in forks if r <= g["rounds"] - 30]
            if not fk:
                continue
            bots = [None, None]
            bots[ours], bots[opp] = f"{ws}/bots/v118-release", f"{ws}/bots/p-{key}"
            pup = [False, False]
            pup[opp] = True
            arms = [{"label": "puppet"}]
            for s in seeds:
                arms.append({"label": f"ref+body{s}", f"t{ours}": {"bot": ref}, f"t{opp}": lfa.body(s)})
                for c in cands:
                    arms.append({"label": f"{c}+body{s}", f"t{ours}": {"bot": built[c]}, f"t{opp}": lfa.body(s)})
            out.append({"id": f"v118:{key}", "map": f"{ws}/maps/{g['map'].replace('_', '-')}.map26a", "bots": bots, "puppet": pup, "forks": fk, "arms": arms,
                        "ours": ours, "picks": man[key]["our_draft"], "live": {"result": g.get("score"), "rounds": g["rounds"], "our_side": g["our_side"]}})
        return out[:limit] if limit else out

    lf.lines = lines
    sys.argv = [sys.argv[0], a.out, "--exp", "live", "--versions", "v118", "--forks", a.forks, "--shards", str(a.shards)] + (["--limit", str(a.limit)] if a.limit else [])
    lf.main()


if __name__ == "__main__":
    main()
