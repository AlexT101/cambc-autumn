"""Emblem lab round 5, the edit lab: many policy-level A/Bs in one run. A lab team plays the base
bot's own draft and emblem table plus a few non-conflicting edits from a registry (edits.py), all game; the outcome
is the win and the assignment is the plan, so vehicles are release builds that log nothing. efit.py estimates every
edit and writes alloc.json, the edits still in play and their shares, which each batch's plan reads.

    py tools/emblab/elab.py init   --lab NAME      # config.json first: source, pool, registry, opponents
    py tools/emblab/elab.py drafts --lab NAME      # the base's own draft on every pool map and side (draft-only games)
    py tools/emblab/elab.py run    --lab NAME --games 80000 [--batches N | --hours H]
    py tools/emblab/elab.py status --lab NAME
    py tools/emblab/elab.py check  --lab NAME --games 64 [--edits NAME ...]   # the vehicle plays as plain bots do

Everything lives in replays/emblab/NAME/: config.json, maps.jsonl, drafts.json, alloc.json, games.jsonl (a row a
game: the sides' edits and the winner), lab.log, batches/bNNN/. A `stop` file ends the run after the batch in play."""
import argparse, collections, json, os, random, re, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "draftlab"))
sys.path.insert(0, str(ROOT / "tools"))
import edits as ed  # noqa: E402
import evehicle as ev  # noqa: E402
import vehicle  # noqa: E402
import lab as dlab  # noqa: E402
import cambc_env  # noqa: E402

LABS = ROOT / "replays" / "emblab"
DEFAULTS = {
    "seed": 5, "source": "bots/variants/oc-fuel-501", "registry": None, "vehicles": 4, "timeout": 900,
    # opponents: who plays the other side. "self": a second lab team with its own edits; any other kind: one of
    # opponent_bots[KIND] (bot directories), which drafts and shops for itself.
    "opponents": {"self": 0.5, "fish": 0.25, "mite": 0.25}, "opponent_bots": {},
    # none_share of lab teams play the base alone; solo_share of the rest one edit; the others up to max_edits
    # non-conflicting ones. A typed edit (need) goes only to teams drafting that pick.
    "none_share": 0.15, "solo_share": 0.2, "max_edits": 3,
    "pool": None, "holdout": [], "check_drafts": 300,
}
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def log(lab, msg):
    dlab.log(lab, msg)


def config(lab):
    return {**DEFAULTS, **json.loads((lab / "config.json").read_text())}


def release_build(paths):
    """cambc build --release, then one warm game each, all at once."""
    cli, _, env = dlab.runner()
    t = time.time()
    warm_map = next((ROOT / "maps").glob("*.map26a"))

    def one(path):
        r = subprocess.run([cli, "build", str(path), "--release"], cwd=ROOT, env=env, capture_output=True, text=True, errors="replace")
        if r.returncode:
            shutil.rmtree(Path(path) / ".cambc", ignore_errors=True)
            raise RuntimeError(f"build failed {path}:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
        cambc_env.warm(cli, path, warm_map, ["--release"])
        (Path(path) / ".cambc" / "emblab-release").write_text(vehicle.src_hash(path))
    paths = list(dict.fromkeys(paths))
    with ThreadPoolExecutor(max(1, len(paths))) as ex:
        list(ex.map(one, paths))
    return time.time() - t


def built(path):
    mark = Path(path) / ".cambc" / "emblab-release"
    return mark.is_file() and mark.read_text() == vehicle.src_hash(path)


def play(bdir, lines, threads, timeout, extra=(), on_done=None):
    """One fast-runner run-batch of release builds over `lines` {stem: manifest line}; returns {stem: result}, also
    appended to results.jsonl."""
    done = {r["stem"]: r for r in dlab.jsonl(bdir / "results.jsonl")}
    lines = {s: l for s, l in lines.items() if s not in done}
    if not lines:
        return done
    cli, fast, env = dlab.runner()
    assert fast, "the edit lab plays on the fast runner"
    manifest = bdir / "manifest.txt"
    manifest.write_text("".join(lines.values()))
    cmd = [cli, "run-batch", str(manifest.resolve()), "--jobs", str(threads), "--release", "--color", "never", "--timeout", str(timeout),
           "--log-limit", "0", "--slot-dir", str(dlab.cpu_slots.DIR), "--slots", str(dlab.cpu_slots.SIZE), *extra]
    status = None
    with open(bdir / "results.jsonl", "a") as out, open(bdir / "run.log", "a") as rl, \
            subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1) as proc:
        for raw in proc.stdout:
            line = ANSI.sub("", raw.rstrip("\r\n"))
            if f := dlab.STATUS.match(line):
                status = f
                continue
            f = dlab.REPLAY.match(line)
            if not f or status is None:
                if not line.startswith(("STARTING", "Building", "Compiling")):
                    rl.write(raw)
                continue
            stem = re.split(r"[\\/]", f.group(1))[-1].removesuffix(".repl26a")
            kind, team, failure, rounds = status.groups()
            status = None
            if kind == "STARTING":
                continue
            r = {"stem": stem, "error": failure} if failure is not None else {"stem": stem, "winner": 0 if team == "A" else 1, "rounds": int(rounds or 0)}
            done[stem] = r
            out.write(json.dumps(r) + "\n")
            if on_done:
                on_done(stem, failure)
    return done


def read_drafts(files, procs=16):
    """{replay path: [A's picks, B's]} (tools/replay/drafts.mjs, which steps through the draft only)."""
    files = [Path(f) for f in files]
    if not files:
        return {}
    tmp = files[0].parent / "drafts-list"
    parts = [files[i::procs] for i in range(procs) if files[i::procs]]
    jobs = []
    for i, part in enumerate(parts):
        (tmp.parent / f"{tmp.name}-{i}.txt").write_text("\n".join(map(str, part)) + "\n")
        jobs.append(subprocess.Popen(["node", str(ROOT / "tools" / "replay" / "drafts.mjs"), str(tmp.parent / f"{tmp.name}-{i}.txt")], cwd=ROOT,
                                     stdout=subprocess.PIPE, text=True))
    out = {}
    name = lambda c: c.lower().replace(" & ", "_and_").replace(" ", "_")  # noqa: E731
    for i, j in enumerate(jobs):
        for line in j.communicate()[0].splitlines():
            f, a, b = line.split("\t")
            out[Path(f)] = [[name(c) for c in t.split(",") if c] for t in (a, b)]
        (tmp.parent / f"{tmp.name}-{i}.txt").unlink()
    for t in out.values():
        assert all(c in vehicle.CHAMPS for team in t for c in team), t
    return out


# ---------- init, drafts ----------
def init(args):
    lab = LABS / args.lab
    cfg = config(lab)
    assert (ROOT / cfg["source"] / "src").is_dir() and cfg["pool"] and cfg["registry"]
    dlab.write_maps(lab, cfg)
    rows = [r for r in dlab.jsonl(lab / "maps.jsonl") if r["picks"] in (3, 4, 5)]
    keys = collections.Counter(r["key"] for r in rows)
    rows = [{k: r[k] for k in ("path", "name", "set", "key", "picks")} for r in rows if keys[r["key"]] == 1]
    (lab / "maps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    reg = ed.load(ROOT / cfg["registry"])
    print(f"{len(rows)} maps in {len(collections.Counter(r['set'] for r in rows))} sets ({sum(1 for k in keys.values() if k > 1)} repeated keys left out); "
          f"registry {reg['sha']}, {len(reg['edits'])} edits; source {cfg['source']}")


def drafts(args):
    """drafts.json {map key: [A's picks, B's]}: the source's own draft, from a draft-only game a map. The draft does
    not see the opponent or the edits, so it holds for every lab game; run()'s check_drafts confirms it."""
    lab = LABS / args.lab
    cfg = config(lab)
    src = ROOT / cfg["source"]
    if not built(src):
        release_build([src])
    maps = dlab.jsonl(lab / "maps.jsonl")
    bdir = lab / "drafts"
    bdir.mkdir(exist_ok=True)
    lines = {f"d{i:06d}": f"{src.as_posix()} {src.as_posix()} {(ROOT / m['path']).as_posix()} {bdir.resolve().as_posix()}/d{i:06d}.repl26a\n"
             for i, m in enumerate(maps)}
    threads = args.threads or dlab.cpu_slots.SIZE
    play(bdir, lines, threads, cfg["timeout"], ["--rounds", "0"])
    out, bad = {}, 0
    for f, teams in read_drafts(sorted(bdir.glob("*.repl26a"))).items():
        m = maps[int(f.name[1:7])]
        if all(len(t) == m["picks"] for t in teams):
            out[m["key"]] = teams
        else:
            bad += 1
    for f in bdir.glob("*.repl26a"):
        f.unlink()
    (lab / "drafts.json").write_text(json.dumps(out) + "\n")
    freq = collections.Counter(c for teams in out.values() for t in teams for c in t)
    n = 2 * len(out)
    print(f"{len(out)} of {len(maps)} maps drafted ({bad} short drafts); "
          f"share of teams holding a pick: " + ", ".join(f"{c} {v / n:.2f}" for c, v in freq.most_common()))


# ---------- plan ----------
class Drawer:
    """Draws each lab team's edits: an edit's chance follows what is left of its batch quota, among the edits the
    team can carry (its typed ones, none conflicting with one already drawn)."""

    def __init__(self, reg, alloc, cfg, teams):
        self.cfg = cfg
        self.edits = {e["id"]: e for e in reg["edits"] if str(e["id"]) in alloc["active"]}
        cells = {i: {tuple(c[:3]) for c in e["cells"]} | {("flag", f[0]) for f in e["flags"]} for i, e in self.edits.items()}
        self.clash = {i: {j for j in self.edits if j != i and cells[i] & cells[j]} for i in self.edits}
        w = {i: float(alloc["active"][str(i)]) for i in self.edits}
        # Appearances a team: (1 - none) x (solo + (1 - solo) x ~2.5, conflicts permitting).
        per_team = (1 - cfg["none_share"]) * (cfg["solo_share"] + (1 - cfg["solo_share"]) * min(cfg["max_edits"], 2.5))
        total = sum(w.values()) or 1
        # alloc "absolute": the weights are appearances wanted this batch (efit.py step); else shares of the batch.
        self.left = dict(w) if alloc.get("absolute") else {i: w[i] / total * per_team * teams for i in self.edits}
        self.by_need = collections.defaultdict(list)
        for i, e in self.edits.items():
            self.by_need[e["need"]].append(i)

    def draw(self, r, team):
        if r.random() < self.cfg["none_share"] or not self.edits:
            return []
        want = 1 if r.random() < self.cfg["solo_share"] else self.cfg["max_edits"]
        can = [i for need in [None, *team] for i in self.by_need.get(need, [])]
        out = []
        while len(out) < want:
            pool = [i for i in can if self.left[i] > 0 and i not in out and not (self.clash[i] & set(out))]
            if not pool:
                break
            i = r.choices(pool, weights=[self.left[i] for i in pool])[0]
            self.left[i] -= 1
            out.append(i)
        return sorted(out)


def plan(lab, cfg, b, games):
    r = random.Random(cfg["seed"] * 100003 + b)
    maps = dlab.jsonl(lab / "maps.jsonl")
    teams_of = json.loads((lab / "drafts.json").read_text())
    maps = [m for m in maps if m["key"] in teams_of]
    random.Random(cfg["seed"]).shuffle(maps)  # one fixed walk through the pool, a slice a batch
    V = cfg["vehicles"]
    n = games // V
    chosen = [maps[(b * n + i) % len(maps)] for i in range(n)]
    kinds, shares = list(cfg["opponents"]), list(cfg["opponents"].values())
    out = []
    for m in chosen:
        for v in range(V):
            g = {"map": m["path"], "key": m["key"], "picks": m["picks"], "vehicle": v}
            kind = r.choices(kinds, weights=shares)[0]
            g["opp"], g["us"] = kind, "AB" if kind == "self" else r.choice("AB")
            if kind != "self":
                g["body"] = r.randrange(len(cfg["opponent_bots"][kind]))
            for t, s in enumerate("AB"):
                if s in g["us"]:
                    g[s] = teams_of[m["key"]][t]
            out.append(g)
    alloc = json.loads((lab / "alloc.json").read_text())
    slots = [(i, s) for i, g in enumerate(out) for s in g["us"]]
    drawer = Drawer(ed.load(ROOT / cfg["registry"]), alloc, cfg, len(slots))
    r.shuffle(slots)  # quotas run down in an order unrelated to the maps
    for i, s in slots:
        out[i][f"e{s}"] = drawer.draw(r, out[i][s])
    return {"batch": b, "alloc": alloc.get("label"), "games": out}


# ---------- run ----------
def vehicle_name(lab, b, v):
    return f"ee-{lab.name}-v{v}" + ("-odd" if b % 2 else "")


def build(lab, cfg, b, p):
    reg = ed.load(ROOT / cfg["registry"])
    defs = ed.defs_header(reg, [n for n, _ in ev.FLAGS])
    per = collections.defaultdict(list)
    for g in p["games"]:
        per[g["vehicle"]] += [(g["key"], t, g[f"e{s}"]) for t, s in enumerate("AB") if s in g["us"]]
    paths = [ROOT / bot for bots in cfg["opponent_bots"].values() for bot in bots if not built(ROOT / bot)]
    for v in sorted(per):
        path, _ = ev.make_edit(ROOT / cfg["source"], vehicle_name(lab, b, v), per[v], defs)
        if not built(path):
            paths.append(path)
    if paths:
        log(lab, f"batch {b}: built {len(paths)} bots in {release_build(paths):.0f} s")


def lines_of(lab, cfg, b, bdir, p):
    lines = {}
    for i, g in enumerate(p["games"]):
        name = (vehicle.VARIANTS / vehicle_name(lab, b, g["vehicle"])).as_posix()
        va = vb = name
        if g["opp"] != "self":
            body = (ROOT / cfg["opponent_bots"][g["opp"]][g["body"]]).as_posix()
            va, vb = (name, body) if g["us"] == "A" else (body, name)
        lines[f"g{i:05d}"] = f"{va} {vb} {(ROOT / g['map']).as_posix()} {bdir.resolve().as_posix()}/g{i:05d}.repl26a\n"
    return lines


def prepare(lab, cfg, b, games):
    bdir = lab / "batches" / f"b{b:03d}"
    bdir.mkdir(parents=True)
    p = plan(lab, cfg, b, games)
    build(lab, cfg, b, p)
    (bdir / "plan.json").write_text(json.dumps(p))
    return bdir, p


def play_batch(lab, cfg, b, bdir, p, threads):
    keep = cfg["check_drafts"]

    def on_done(stem, failure):  # the replay is not needed: the result line is the outcome
        if int(stem[1:]) >= keep or failure is not None:
            (bdir / f"{stem}.repl26a").unlink(missing_ok=True)
    return play(bdir, lines_of(lab, cfg, b, bdir, p), threads, cfg["timeout"], on_done=on_done)


def finish(lab, cfg, b, bdir, p, results):
    rows, early, errors = [], 0, 0
    for i, g in enumerate(p["games"]):
        res = results.get(f"g{i:05d}")
        if res is None:
            continue
        row = {"id": f"b{b:03d}-g{i:05d}", "batch": b, **{k: v for k, v in g.items() if k != "vehicle"}}
        if res.get("error"):
            row["error"] = res["error"]
            errors += 1
        else:
            row.update(winner=res["winner"], rounds=res["rounds"])
            early += res["rounds"] <= cambc_env.EARLY_ROUNDS
        rows.append(row)
    # The first games' replays check that every lab team drafted what drafts.json says.
    bad = checked = 0
    for f, teams in read_drafts(sorted(bdir.glob("*.repl26a"))).items():
        g = p["games"][int(f.name[1:6])]
        for t, s in enumerate("AB"):
            if s in g["us"]:
                checked += 1
                bad += teams[t] != g[s]
        f.unlink()
    with open(lab / "games.jsonl", "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    (bdir / "merged").write_text(f"{len(rows)}\n")
    for f in ("manifest.txt",):
        (bdir / f).unlink(missing_ok=True)
    ok = [r for r in rows if "winner" in r]
    teams = sum(len(r["us"]) for r in ok)
    log(lab, f"batch {b}: merged {len(rows)} games ({errors} errors, {early} over by round {cambc_env.EARLY_ROUNDS}), {teams} lab teams, "
             f"{sum(len(r.get(f'e{s}', [])) for r in ok for s in r['us'])} edit appearances, alloc {p.get('alloc')}, "
             f"drafts off the plan {bad} of {checked}, opponents {dict(collections.Counter(r['opp'] for r in ok))}")
    if errors > 0.02 * len(rows) or bad > 0.02 * max(1, checked):
        raise SystemExit("too many errors or drafts off the plan: stopping")


def run(args):
    lab = LABS / args.lab
    cfg = config(lab)
    threads = args.threads or dlab.cpu_slots.SIZE
    cli, fast, env = dlab.runner()
    log(lab, f"runner {cli} ({'fastrunner' if fast else 'STOCK'}), release; {threads} threads of {dlab.cpu_slots.SIZE} slots at weight "
             f"{os.environ.get('CAMBC_SLOT_WEIGHT')}, group {os.environ.get('CAMBC_SLOT_GROUP')}")
    deadline = time.time() + args.hours * 3600 if args.hours else None
    if deadline:
        args.batches = 10 ** 6
    (lab / "batches").mkdir(exist_ok=True)
    for bdir in dlab.batch_dirs(lab):
        if not (bdir / "merged").is_file() and (bdir / "plan.json").is_file():
            b = int(bdir.name[1:])
            log(lab, f"resuming {bdir.name}")
            p = json.loads((bdir / "plan.json").read_text())
            build(lab, cfg, b, p)
            finish(lab, cfg, b, bdir, p, play_batch(lab, cfg, b, bdir, p, threads))
        elif not (bdir / "plan.json").is_file():
            shutil.rmtree(bdir)  # planned but never fully built
    first = len(dlab.batch_dirs(lab))

    def more(b):
        return b < first + args.batches and not (lab / "stop").exists() and (deadline is None or time.time() < deadline)

    def update():
        """efit.py's allocation step between batches (config "auto": its arguments), on the batches merged so far."""
        if cfg.get("auto") is not None:
            r = subprocess.run([sys.executable, str(HERE / "efit.py"), "step", "--lab", args.lab, *cfg["auto"]], cwd=ROOT, capture_output=True, text=True)
            log(lab, "efit step: " + (r.stdout.strip().splitlines() or [r.stderr.strip()[-300:]])[-1])
    ready = prepare(lab, cfg, first, args.games) if more(first) else None
    played = None
    with ThreadPoolExecutor(1) as player:
        b = first
        while ready is not None:
            bdir, p = ready
            t0 = time.time()
            log(lab, f"batch {b}: {len(p['games'])} games")
            playing = player.submit(play_batch, lab, cfg, b, bdir, p, threads)
            if played:
                finish(lab, cfg, *played)
                played = None
                cfg = config(lab)
                update()
            ready = prepare(lab, cfg, b + 1, args.games) if more(b + 1) else None
            results = playing.result()
            log(lab, f"batch {b}: played in {time.time() - t0:.0f} s")
            played = (b, bdir, p, results)
            b += 1
    if played:
        finish(lab, cfg, *played)
        update()


def check(args):
    """The vehicle against plain bots, mirror games on the pool's first maps: with no edits it must play as the
    source does, and with an edit on both sides as a copy of the source with that edit written into its table
    (edits.py table). Compares each game's outcome.mjs row (winner, rounds, gem checkpoints, champions)."""
    lab = LABS / args.lab
    cfg = config(lab)
    reg = ed.load(ROOT / cfg["registry"])
    defs = ed.defs_header(reg, [n for n, _ in ev.FLAGS])
    by = {e["name"]: e for e in reg["edits"]}
    maps = dlab.jsonl(lab / "maps.jsonl")[:args.games]
    cdir = lab / "check"
    shutil.rmtree(cdir, ignore_errors=True)
    cdir.mkdir()
    pairs, builds = [], []
    for i, names in enumerate([[]] + [n.split("+") for n in args.edits]):
        ids = [by[n]["id"] for n in names]
        veh, _ = ev.make_edit(ROOT / cfg["source"], f"ee-{lab.name}-chk{i}", [(m["key"], t, ids) for m in maps for t in (0, 1)], defs)
        ref = ROOT / cfg["source"]
        if names:
            ref = vehicle.VARIANTS / f"ee-{lab.name}-ref{i}"
            subprocess.run([sys.executable, str(HERE / "edits.py"), "table", "--registry", str(ROOT / cfg["registry"]), "--base", cfg["source"],
                            "--out", ref.relative_to(ROOT).as_posix(), *names], cwd=ROOT, check=True, capture_output=True)
        pairs.append(("+".join(names) or "no edits", veh, ref))
        builds += [b for b in (veh, ref) if not built(b)]
    if builds:
        release_build(builds)
    lines = {}
    for i, (_, veh, ref) in enumerate(pairs):
        for j, m in enumerate(maps):
            for k, bot in enumerate((veh, ref)):
                stem = f"c{i}-{k}-{j:04d}"
                lines[stem] = f"{bot.as_posix()} {bot.as_posix()} {(ROOT / m['path']).as_posix()} {cdir.resolve().as_posix()}/{stem}.repl26a\n"
    play(cdir, lines, args.threads or dlab.cpu_slots.SIZE, cfg["timeout"], ["--fuel", str(args.fuel)] if args.fuel else [])
    dlab.node(dlab.HERE / "outcome.mjs", cdir, "--out", cdir / "outcomes.jsonl", "--delete", "--threads", 16)
    rows = {o["file"].removesuffix(".repl26a"): {k: v for k, v in o.items() if k != "file"} for o in dlab.jsonl(cdir / "outcomes.jsonl")}
    for i, (name, _, _) in enumerate(pairs):
        same = [rows.get(f"c{i}-0-{j:04d}") == rows.get(f"c{i}-1-{j:04d}") for j in range(len(maps))]
        base = [rows.get(f"c{i}-0-{j:04d}") == rows.get(f"c0-1-{j:04d}") for j in range(len(maps))]
        print(f"{name}: vehicle = reference bot on {sum(same)} of {len(maps)} maps; vehicle = unedited source on {sum(base)}")


def status(args):
    lab = LABS / args.lab
    n = sum(1 for _ in open(lab / "games.jsonl")) if (lab / "games.jsonl").is_file() else 0
    print(f"{n} games merged")
    for line in (lab / "lab.log").read_text().splitlines()[-6:] if (lab / "lab.log").is_file() else []:
        print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "drafts", "run", "status", "check"])
    ap.add_argument("--fuel", type=int, help="check: fuel a turn for both sides (100000000: no turn runs out, so only the logic is compared)")
    ap.add_argument("--edits", nargs="*", default=[], help="check: edit names, a+b for several on one team")
    ap.add_argument("--lab", required=True)
    ap.add_argument("--games", type=int, default=80000)
    ap.add_argument("--batches", type=int, default=1)
    ap.add_argument("--hours", type=float)
    ap.add_argument("--threads", type=int)
    args = ap.parse_args()
    {"init": init, "drafts": drafts, "run": run, "status": status, "check": check}[args.command](args)


if __name__ == "__main__":
    main()
