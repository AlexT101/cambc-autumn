"""A league over a tunified bot's constants, after AlphaStar's: a main agent, exploiters that hunt it, frozen past
agents, and fixed outside opponents, all on the fast runner with patched candidates (tune.py, patch.py).

    PY=<python with optuna>  # optuna and numpy (not the repo's venv)
    $PY tools/tune/league.py init --run L --from-tune d1 [--opps variants/a,baselines/v67]   # main starts at d1's x
    $PY tools/tune/league.py run --run L --hours 4                                          # resumable
    $PY tools/tune/league.py status --run L

A round is one fast-runner batch:
- **main** takes an SPSA step (tune.py's: `pairs` sign vectors, paired + / - candidates on common games) against a
  prioritized mix (PFSP): each game's opponent is drawn from the outside panel and the league's frozen agents with
  weight (1 - p)^2 + 0.1, p the main's recent win share against it, so it trains most against what beats it.
- **the exploiter** asks `exploiter_trials` values from an optuna study (TPE by default; `sampler` "cmaes" or "random")
  and plays each against the current main only (both sides on `exploiter_maps` maps); scores are the exploiter's.
  When its best trial's recent win share against the main passes `freeze_at` on a confirmation of `confirm_maps` maps,
  that trial joins the league as a frozen agent and a fresh study starts.
- every `snapshot_every` rounds the main itself joins the league frozen.
State: replays/tune/L/ (config.json editable, state.json, league.json, history.jsonl, optuna study per exploiter in
exploiters.db). Games, scores and the stop file work as in tune.py.
"""
import argparse, json, random, shutil, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tune  # noqa: E402
import patch  # noqa: E402
from tune import ROOT, RUNS, log, values_of, score, summarize, runner_env, maps_in, FASTRUNNER, cpu_slots  # noqa: E402


class Jobs:
    """One run-batch of arbitrary (candidate, opponent, map, side) games; agents are value dicts (patched builds),
    other opponents are run/opps/<name> directories."""

    def __init__(self, run, cfg, agents, jobs, tag, base):
        self.run, self.cfg, self.jobs, self.tag = run, cfg, jobs, tag
        self.work = run / "work" / tag
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True)
        used = sorted({j[0] for j in jobs} | {j[1] for j in jobs if j[1] in agents})
        dirs, self.hashes = {}, set()
        with ThreadPoolExecutor(8) as pool:
            for name, (path, h) in zip(used, pool.map(lambda n: base.write(agents[n], self.work / "bots" / n), used)):
                dirs[name] = path
                if h != base.hash:
                    self.hashes.add(h)
        lines = []
        for i, (cand, opp, m, side) in enumerate(jobs):
            o = dirs[opp] if opp in dirs else run / "opps" / opp
            a, b = (dirs[cand], o) if side == 0 else (o, dirs[cand])
            lines.append(f"{a} {b} {m} {self.work / f'{i}.repl26a'} --statistics {self.work / f'{i}.camstat'}\n")
        random.Random(tag).shuffle(lines)
        (self.work / "manifest.txt").write_text("".join(lines))

    def play(self):
        t0 = time.time()
        with (self.work / "run.log").open("w") as out:
            tune.subprocess.run([str(FASTRUNNER), "run-batch", str(self.work / "manifest.txt"), "--release", "--log-limit", "0",
                                 "--jobs", str(min(len(self.jobs), cpu_slots.SIZE)), "--slot-dir", str(cpu_slots.DIR),
                                 "--slots", str(cpu_slots.SIZE)], cwd=ROOT, env=runner_env(self.run), stdout=out,
                                stderr=tune.subprocess.STDOUT)
        self.wall = time.time() - t0
        with ThreadPoolExecutor(32) as pool:
            stats = list(pool.map(lambda i: summarize(self.work / f"{i}.camstat"), range(len(self.jobs))))
        out = []  # (job index, score, win) from the candidate's side; None for a failed game
        for i, st in enumerate(stats):
            out.append(None if st is None else score(self.cfg["weights"], st, self.jobs[i][3]))
        shutil.rmtree(self.work, ignore_errors=True)
        for h in self.hashes:
            patch.forget(h)
        return out


def load(run):
    return (json.loads((run / "config.json").read_text()), json.loads((run / "state.json").read_text()),
            json.loads((run / "league.json").read_text()))


def save(run, st, league):
    (run / "state.json").write_text(json.dumps(st, indent=1))
    (run / "league.json").write_text(json.dumps(league, indent=1))


def cmd_init(a):
    run = RUNS / a.run
    if run.exists() and not a.force:
        raise SystemExit(f"{run} exists")
    src = RUNS / a.from_tune
    scfg = json.loads((src / "config.json").read_text())
    sst = json.loads((src / "state.json").read_text())
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    shutil.copytree(src / "base", run / "base", symlinks=True)
    opps = scfg["opps"]
    if a.opps:
        opps = []
        for o in a.opps.split(","):
            name = o.replace("/", "-")
            if (src / "opps" / name).exists():
                shutil.copytree(src / "opps" / name, run / "opps" / name, symlinks=True)
            else:
                tune.copy_bot(ROOT / "bots" / o, run / "opps" / name)
                tune.build_release(run / "opps" / name)
            opps.append(name)
    else:
        shutil.copytree(src / "opps", run / "opps", symlinks=True)
    cfg = {
        "params": scfg["params"], "pool": scfg["pool"], "opps": opps, "weights": scfg["weights"],
        "pairs": 4, "main_maps": 48, "a": scfg["a"], "A": scfg["A"], "alpha": scfg["alpha"], "c": scfg["c"],
        "gamma": scfg["gamma"], "seed": a.seed,
        "exploiter_trials": 8, "exploiter_maps": 24, "sampler": "tpe", "freeze_at": 0.56, "confirm_maps": 200,
        "snapshot_every": 60, "pfsp_window": 400,
    }
    (run / "config.json").write_text(json.dumps(cfg, indent=1))
    base = patch.Base(run / "base")
    d = base.defaults()
    league = {"frozen": {"default": d}, "results": {}}  # results[opp] = recent main outcomes (1 win, 0 not)
    st = {"k": sst["k"], "round": 0, "x": sst["x"], "exploiter": 0, "since_freeze": 0}
    save(run, st, league)
    print(f"{run}: main from {src.name} at iteration {sst['k']}, {len(opps)} outside opponents")


def study(run, cfg, n):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = {"tpe": lambda: optuna.samplers.TPESampler(multivariate=True, seed=n),
               "cmaes": lambda: optuna.samplers.CmaEsSampler(seed=n),
               "random": lambda: optuna.samplers.RandomSampler(seed=n)}[cfg.get("sampler", "tpe")]()
    return optuna.create_study(study_name=f"exploiter-{n}", storage=f"sqlite:///{run / 'exploiters.db'}",
                               direction="maximize", sampler=sampler, load_if_exists=True)


def suggest(trial, cfg, base_values):
    out = {}
    for n, (lo, hi, kind) in cfg["params"].items():
        out[n] = trial.suggest_int(n, int(lo), int(hi)) if kind == "int" else trial.suggest_float(n, lo, hi)
    return out


def cmd_run(a):
    import optuna  # noqa: F401  (fail early)
    run = RUNS / a.run
    deadline = time.time() + a.hours * 3600 if a.hours else None
    base = patch.Base(run / "base")
    maps_cache = {}
    while not ((deadline and time.time() > deadline) or (run / "STOP").exists()):
        cfg, st, league = load(run)
        key = tuple(cfg["pool"])
        if key not in maps_cache:
            maps_cache[key] = maps_in(cfg["pool"])
        maps = maps_cache[key]
        k, rnd = st["k"], st["round"]
        rng = random.Random(cfg["seed"] * 1000003 + rnd)
        x = st["x"]
        for n in cfg["params"]:
            x.setdefault(n, 0.5)
        main = values_of(cfg, x)
        agents = {"main": main}
        agents.update({f"f-{n}": v for n, v in league["frozen"].items()})
        # Main: SPSA against PFSP-drawn opponents.
        names = list(cfg["params"])
        ck = cfg["c"] / (k + 1) ** cfg["gamma"]
        cn = {n: max(ck, 1.0 / max(1, hi - lo)) if kind == "int" else ck for n, (lo, hi, kind) in cfg["params"].items()}
        deltas = [{n: rng.choice((-1, 1)) for n in names} for _ in range(cfg["pairs"])]
        for p, d in enumerate(deltas):
            agents[f"p{p}"] = values_of(cfg, {n: x[n] + cn[n] * d[n] for n in names})
            agents[f"m{p}"] = values_of(cfg, {n: x[n] - cn[n] * d[n] for n in names})
        pool = list(cfg["opps"]) + [f"f-{n}" for n in league["frozen"]]
        def winshare(o):
            r = league["results"].get(o, [])
            return sum(r) / len(r) if len(r) >= 20 else 0.5
        weights = [(1 - winshare(o)) ** 2 + 0.1 for o in pool]
        main_games = [(m, rng.choices(pool, weights)[0], rng.randrange(2)) for m in rng.sample(maps, cfg["main_maps"] * 4)]
        jobs, owner = [], []
        for p in range(cfg["pairs"]):
            for gi, (m, o, side) in enumerate(main_games):
                for c in (f"p{p}", f"m{p}"):
                    jobs.append((c, o, m, side)); owner.append(("main", c, gi, o))
        # Exploiter: optuna trials against the current main, both sides of each map.
        stdy = study(run, cfg, st["exploiter"])
        trials = [stdy.ask() for _ in range(cfg["exploiter_trials"])]
        for t in trials:
            agents[f"x{t.number}"] = suggest(t, cfg, main)
        xmaps = rng.sample(maps, cfg["exploiter_maps"])
        for t in trials:
            for m in xmaps:
                for side in (0, 1):
                    jobs.append((f"x{t.number}", "main", m, side)); owner.append(("exp", t.number, None, None))
        res = Jobs(run, cfg, agents, jobs, f"r{rnd}", base).play()
        # Main's SPSA step, paired by game within each pair.
        per = defaultdict(dict)
        for (kind, c, gi, o), r in zip(owner, res):
            if kind == "main" and r is not None:
                per[c][gi] = r
                league["results"].setdefault(o, []).append(1 if r[1] > 0 else 0)
                league["results"][o] = league["results"][o][-cfg["pfsp_window"]:]
        grad = {n: 0.0 for n in names}
        for p, d in enumerate(deltas):
            both = [g for g in per[f"p{p}"] if g in per[f"m{p}"]]
            diff = sum(per[f"p{p}"][g][0] - per[f"m{p}"][g][0] for g in both) / len(both) if both else 0.0
            for n in names:
                grad[n] += diff / (2 * cn[n] * d[n]) / len(deltas)
        ak = cfg["a"] / (k + 1 + cfg["A"]) ** cfg["alpha"]
        x = {n: min(1.0, max(0.0, x[n] + ak * grad[n])) for n in names}
        # Exploiter: tell each trial its mean score against the main.
        xs = defaultdict(list)
        for (kind, num, _, _), r in zip(owner, res):
            if kind == "exp" and r is not None:
                xs[num].append(r)
        for t in trials:
            r = xs.get(t.number, [])
            stdy.tell(t, sum(s for s, _ in r) / len(r) if r else -1.0)
        best = max(trials, key=lambda t: sum(s for s, _ in xs.get(t.number, [])) / max(1, len(xs.get(t.number, []))))
        bw = xs.get(best.number, [])
        best_win = sum(w > 0 for _, w in bw) / max(1, len(bw))
        froze = None
        if best_win >= cfg["freeze_at"]:
            # Confirm on fresh maps before freezing (a lucky 48 games is common among 8 trials).
            cm = rng.sample(maps, cfg["confirm_maps"])
            cj = [("cand", "main", m, side) for m in cm for side in (0, 1)]
            cres = Jobs(run, cfg, {"cand": agents[f"x{best.number}"], "main": main}, cj, f"r{rnd}c", base).play()
            cw = [r[1] > 0 for r in cres if r is not None]
            share = sum(cw) / max(1, len(cw))
            if share >= cfg["freeze_at"] - 0.02:
                froze = f"e{st['exploiter']}-{best.number}"
                league["frozen"][froze] = agents[f"x{best.number}"]
                st["exploiter"] += 1
            log(run, f"round {rnd + 1}: exploiter trial {best.number} confirm {100 * share:.1f}% of {len(cw)}"
                     f"{' -> frozen as ' + froze if froze else ''}")
        if (rnd + 1) % cfg["snapshot_every"] == 0:
            league["frozen"][f"main-{rnd + 1}"] = values_of(cfg, x)
        st.update(k=k + 1, round=rnd + 1, x=x)
        save(run, st, league)
        mm = [r for (kind, *_), r in zip(owner, res) if kind == "main" and r is not None]
        rec = {"round": rnd + 1, "k": k + 1, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "games": len(res),
               "main_score": sum(s for s, _ in mm) / max(1, len(mm)), "main_win": sum(w > 0 for _, w in mm) / max(1, len(mm)),
               "exploiter_best": best_win, "frozen": froze, "x": x,
               "vs": {o: round(sum(r) / len(r), 3) for o, r in league["results"].items() if r}}
        with (run / "history.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        log(run, f"round {rnd + 1}: {len(res)} games, main score {rec['main_score']:+.4f} win {100 * rec['main_win']:.1f}%, "
                 f"best exploiter {100 * best_win:.1f}% vs main, league {len(league['frozen'])}")


def cmd_status(a):
    run = RUNS / a.run
    cfg, st, league = load(run)
    print(f"{run}: round {st['round']}, main iteration {st['k']}, exploiter #{st['exploiter']}, frozen: {list(league['frozen'])}")
    for o, r in sorted(league["results"].items()):
        print(f"  main vs {o:28s} {100 * sum(r) / len(r):5.1f}% of last {len(r)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--run", required=True)
    i.add_argument("--from-tune", required=True, help="a tune.py run: its base, opponents, ranges and current x")
    i.add_argument("--opps", help="outside opponents (default: the tune run's)")
    i.add_argument("--seed", type=int, default=1)
    i.add_argument("--force", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--hours", type=float)
    s = sub.add_parser("status")
    s.add_argument("--run", required=True)
    a = ap.parse_args()
    {"init": cmd_init, "run": cmd_run, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
