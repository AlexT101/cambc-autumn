"""Map fuzzing: find maps on which our bot farms pathologically against bots/idle, then hill-climb them with
mapgen mutations into more extreme (and, with --shrink, simpler) maps. Output: replays/fuzz/<name>/.

    py tools/fuzz/fuzz.py run NAME [--screen 400] [--climb 8 --gens 4 --children 10] [--shrink 2] [--ref astraeus]
    py tools/fuzz/fuzz.py report NAME [--top 20]
    py tools/fuzz/fuzz.py rescore NAME                 # recompute scores after editing score.py, no games
    py tools/fuzz/fuzz.py vs NAME BOT [--top 10]       # head-to-head on the worst maps, both sides

Screen: maps sampled from every preset `mapgen list` prints at run time (equal shares) and `mapgen mutate random`
(--mutate-share), plus every map in --include DIRs; presets that fail to generate are skipped. Each map is played by
the bot against idle through run_batched.py (both sides unless --one-side), extracted with extract.mjs and scored
(score.py; README.md). Climb: the --climb worst maps (at most two per source) each get --children single-op
mutations a generation, played on both sides; the worst child replaces its parent if it scores --min-gain more."""

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import math
import random
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "fuzz"))
from ab import rel, slug, TEST_DRAFT  # noqa: E402
import cpu_slots  # noqa: E402
import score  # noqa: E402

MAPGEN = ROOT / "tools" / "mapgen" / "mapgen.mjs"
IDLE = ROOT / "bots" / "idle"
OUT = ROOT / "replays" / "fuzz"
GEN_JOBS = 48
# Map file hashes already played: a mutation that changes nothing (or repeats a sibling) is dropped.
SEEN = set()


def say(*parts):
    print(*parts, flush=True)


def path_of(f):
    f = Path(f)
    return f if f.is_absolute() else ROOT / f


# ---- maps -------------------------------------------------------------------------------------

def presets():
    done = subprocess.run(["node", str(MAPGEN), "list"], cwd=ROOT, capture_output=True, text=True)
    return [line.split()[0] for line in done.stdout.splitlines() if line.strip()]


def mapgen(args, out):
    """One mapgen gen/mutate call holding a CPU slot; (ok, stdout+stderr)."""
    try:
        with cpu_slots.slot():
            done = subprocess.run(["node", str(MAPGEN), *args, "--out", str(out)], cwd=ROOT, capture_output=True,
                                  text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "mapgen timed out"
    return done.returncode == 0 and out.is_file(), (done.stdout + done.stderr).strip()


def generate(task):
    """Generate one screen map; a preset failing at a seed retries two more seeds."""
    kind, what, seed, dest = task
    for attempt in range(3):
        s = seed + 50000 * attempt
        if kind == "preset":
            out = dest / f"p-{what}-{s}.map26a"
            ok, log = mapgen(["gen", what, "--seed", str(s)], out)
            if ok:
                return {"name": out.stem, "file": out, "origin": {"kind": "preset", "preset": what, "seed": s}}
        else:
            tmp = dest / f"m-{s}.map26a"
            ok, log = mapgen(["mutate", "random", "--seed", str(s)], tmp)
            if ok:
                ladder = re.search(r"^mut-(\S+)-\d+", log, re.M)
                ops = re.search(r"^\s*ops: (.*)$", log, re.M)
                ladder = ladder.group(1) if ladder else "?"
                out = dest / f"m-{ladder}-{s}.map26a"
                tmp.rename(out)
                return {"name": out.stem, "file": out, "origin": {"kind": "mutate", "preset": f"mutate:{ladder}",
                                                                   "seed": s, "ops": ops.group(1).split() if ops else []}}
    return {"failed": what, "error": log.splitlines()[-1] if log else "no output"}


def check(files):
    """mapgen check --json metrics per file stem, in parallel chunks."""
    files = [str(f) for f in files]
    chunks = [files[i:i + 25] for i in range(0, len(files), 25)]

    def run(chunk):
        with cpu_slots.slot():
            done = subprocess.run(["node", str(MAPGEN), "check", *chunk, "--json"], cwd=ROOT, capture_output=True, text=True)
        out = {}
        for line in done.stdout.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            out[Path(row["file"]).stem] = row.get("metrics") or {}
        return out

    found = {}
    with ThreadPoolExecutor(min(GEN_JOBS, len(chunks) or 1)) as pool:
        for part in pool.map(run, chunks):
            found.update(part)
    return found


# ---- play and score ---------------------------------------------------------------------------

def play(bot, maps_dir, batch, args, share=1, one_side=False, side_seed=0):
    """run_batched.py bot vs idle on every map in maps_dir; its results.json (or None). Concurrent plays (`share`)
    split --threads."""
    command = [sys.executable, str(ROOT / "tools" / "run_batched.py"), str(bot), str(IDLE), "--maps-dir", str(maps_dir),
               "--output", str(batch), "--threads", str(max(1, args.threads // share)), "--timeout", str(args.timeout)]
    if args.fuel:
        command += ["--fuel", str(args.fuel)]
    if one_side:
        command += ["--one-side", "--side-seed", str(side_seed)]
    log = batch.parent / f"{batch.name}.log"
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    try:
        return json.loads((batch / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        say(f"  no results from {rel(batch)}; see {rel(log)}")
        return None


def extract(batches, analysis, threads):
    held = cpu_slots.acquire(min(threads, 64), least=8)
    try:
        subprocess.run(["node", str(ROOT / "tools" / "replay" / "extract.mjs"), *map(str, batches), "--out", str(analysis),
                        "--threads", str(len(held))], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        cpu_slots.release(held)
    try:
        return {row["source"]: row for row in json.loads((analysis / "index.json").read_text(encoding="utf-8"))["games"]}
    except (OSError, ValueError):
        return {}


def score_one(task):
    analysis, row, team = task
    try:
        return score.game(analysis, row, team)
    except (OSError, ValueError, KeyError) as error:
        return {"crash": f"scoring failed: {error!r}"}


def score_games(tasks, threads):
    """score.game over [(analysis, row, team)] in processes holding CPU slots."""
    if not tasks:
        return []
    held = cpu_slots.acquire(min(threads, 48, len(tasks)), least=1)
    try:
        with ProcessPoolExecutor(len(held)) as pool:
            return list(pool.map(score_one, tasks, chunksize=8))
    finally:
        cpu_slots.release(held)


def evaluate(report, index, analysis, threads):
    """{map stem: {side: metrics}} from one batch; failed matches get crash metrics."""
    out, todo = {}, []
    for m in (report or {}).get("matches", []):
        stem, team = Path(m["map"]).stem, m["order"].index(0)
        side = "AB"[team]
        row = index.get(rel(Path(m["replay"]))) if m.get("replay") else None
        if "error" in m or not row or not row["ok"]:
            out.setdefault(stem, {})[side] = {"crash": m.get("error", "replay not extracted")}
        else:
            todo.append((stem, side, (analysis, row, team)))
    for (stem, side, _), metrics in zip(todo, score_games([t for _, _, t in todo], threads)):
        out.setdefault(stem, {})[side] = metrics
    return out


def rescore(rec, base):
    """Fill each side's components and total, and the map's: the mean over sides plus their asymmetry."""
    totals, comps = [], {}
    for side, s in rec["sides"].items():
        if "crash" in s["metrics"]:
            s["comps"] = score.crash_components()
        else:
            ref = s.get("ref")
            m = s["metrics"]
            m["expected_rate"] = round(min(score.expected_rate(m["offer_rate"], base), m["offer_rate"]), 3)
            s["comps"] = score.components(m, base, ref if ref and "crash" not in ref else None)
        s["score"] = score.total(s["comps"])
        totals.append(s["score"])
        for k, v in s["comps"].items():
            comps[k] = comps.get(k, 0) + v / len(rec["sides"])
    comps["asym"] = score.asymmetry([s["metrics"] for s in rec["sides"].values()])
    rec["score"] = round((sum(totals) / len(totals) if totals else 0.0) + score.WEIGHTS["asym"] * comps["asym"], 3)
    rec["comps"] = {k: round(v, 3) for k, v in comps.items()}
    return rec


def run_stage(label, maps, bot, args, run_dir, state, one_side=False):
    """Copy maps into a stage directory, play them (and the reference), and return per-map records."""
    stage = run_dir / "stages" / label
    maps_dir = stage / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)
    for rec in maps:
        target = maps_dir / f"{rec['name']}.map26a"
        if not target.exists():
            shutil.copy2(path_of(rec["file"]), target)
    t0 = perf_counter()
    jobs = [("bot", bot)] + ([("ref", args.ref_path)] if args.ref_path else [])
    with ThreadPoolExecutor(len(jobs)) as pool:
        reports = dict(zip([j[0] for j in jobs], pool.map(
            lambda j: play(j[1], maps_dir, stage / f"batch-{j[0]}", args, len(jobs), one_side, args.seed), jobs)))
    analysis = run_dir / "analysis"
    index = extract([stage / f"batch-{role}" for role, _ in jobs], analysis, args.threads)
    results = {role: evaluate(reports[role], index, analysis, args.threads) for role, _ in jobs}
    seconds = perf_counter() - t0
    state.setdefault("stages", []).append({"label": label, "maps": len(maps), "seconds": round(seconds, 1),
                                          "games": sum(len(v) for v in results["bot"].values())})
    say(f"  {label}: {len(maps)} maps in {seconds:.0f} s")
    for rec in maps:
        sides = results["bot"].get(rec["name"], {})
        if not sides:
            sides = {"A": {"crash": "not played"}}
        rec["sides"] = {side: {"metrics": m, **({"ref": results["ref"].get(rec["name"], {}).get(side)} if "ref" in results else {})}
                        for side, m in sorted(sides.items())}
        rec["file"] = rel(maps_dir / f"{rec['name']}.map26a")
    return maps


# ---- mutation search --------------------------------------------------------------------------

def climb_op(r):
    f = lambda lo, hi: f"{r.uniform(lo, hi):.2f}"
    kinds = ["walls", "holes", "bushes"]
    a, b = r.sample(kinds, 2)
    return r.choice([
        f"walls*{f(0.3, 0.8)}", f"walls+{r.randint(3, 10)}", f"holes*{f(0.2, 0.7)}", f"holes+{r.randint(2, 8)}",
        f"bushes*{f(0.2, 0.7)}", f"bushes+{r.randint(3, 10)}", f"{a}~{b}*{f(0.3, 0.8)}", f"doors+{r.randint(1, 4)}",
        f"gaps+{r.randint(1, 3)}", f"vaults+{r.randint(1, 2)}", f"camps*{r.choice([f(0.6, 0.9), f(1.15, 1.6)])}",
        f"camps+{r.randint(1, 4)}", f"camps-{r.randint(1, 3)}", f"altars+{r.randint(1, 2)}", "altars-1",
        f"econ={r.choice(['rich', 'poor', 'gold', 'gems'])}", f"picks={r.randint(3, 5)}", "altars=mid"])


def shrink_op(r):
    return r.choice(["walls*0.5", "walls*0", "holes*0.5", "holes*0", "bushes*0.5", "bushes*0", "walls-3", "holes-3",
                     "camps-1", "camps-2", "altars-1"])


def family(op):
    """An op without its amounts: walls*<1, walls+N, econ=gold..."""
    m = re.match(r"^(.*?)([*+=-])([\d.]+)$", op)
    if m and m.group(2) == "*":
        return f"{m.group(1)}*{'<1' if float(m.group(3)) < 1 else '>1'}"
    if m and m.group(2) in "+-":
        return f"{m.group(1)}{m.group(2)}N"
    return op


def mutate_children(lineages, gen, phase, args, run_dir):
    rng = random.Random(f"{args.seed}:{phase}:{gen}")
    dest = run_dir / "maps" / f"{phase}-g{gen}"
    dest.mkdir(parents=True, exist_ok=True)
    tasks = []
    for lin in lineages:
        for k in range(args.children):
            ops = [shrink_op(rng)] if phase == "shrink" else [climb_op(rng) for _ in range(1 if rng.random() < 0.75 else 2)]
            name = f"L{lin['id']:02}-{phase[0]}{gen}-{k:02}"
            tasks.append((lin, ops, rng.randrange(1 << 30), dest / f"{name}.map26a"))

    def make(task):
        lin, ops, seed, out = task
        args_ = ["mutate", str(path_of(lin["current"]["file"])), "--seed", str(seed)]
        for op in ops:
            args_ += ["--op", op]
        ok, log = mapgen(args_, out)
        if not ok:
            return None
        cur = lin["current"]
        return {"name": out.stem, "file": out, "origin": {**cur["origin"], "kind": phase, "lineage": lin["id"],
                                                           "parent": cur["name"], "chain": [*cur["origin"].get("chain", []), *ops],
                                                           "step": ops}}

    with ThreadPoolExecutor(GEN_JOBS) as pool:
        made = [k for k in pool.map(make, tasks) if k]
    kids = []
    for k in made:
        h = digest(k["file"])
        if h not in SEEN:
            SEEN.add(h)
            kids.append(k)
    return kids, len(tasks) - len(made), len(made) - len(kids)


def digest(f):
    return hashlib.sha256(path_of(f).read_bytes()).hexdigest()


def features(rec):
    m = rec.get("check") or {}
    return round(100 * (m.get("walls", 0) + m.get("holes", 0) + m.get("bushes", 0)), 1), m.get("camps_side"), m.get("altars")


def search(lineages, phase, gens, args, run_dir, state, bot, base, records, op_log):
    for gen in range(1, gens + 1):
        active = [lin for lin in lineages if lin["active"]]
        if not active:
            break
        kids, failed, dupes = mutate_children(active, gen, phase, args, run_dir)
        say(f"{phase} generation {gen}: {len(kids)} children of {len(active)} maps ({failed} mutations failed, {dupes} duplicates)")
        if not kids:
            break
        meta = check([k["file"] for k in kids])
        for k in kids:
            k["check"] = meta.get(Path(k["file"]).stem, {})
        run_stage(f"{phase}-g{gen}", kids, bot, args, run_dir, state)
        for k in kids:
            rescore(k, base)
            records.append(k)
        for lin in active:
            cur = lin["current"]
            mine = [k for k in kids if k["origin"]["lineage"] == lin["id"]]
            for k in mine:
                k["delta"] = round(k["score"] - cur["score"], 3)
                for op in k["origin"]["step"]:
                    op_log.append({"phase": phase, "family": family(op), "delta": k["delta"], "lineage": lin["id"]})
            if phase == "climb":
                best = max(mine, key=lambda k: k["score"], default=None)
                ok = best is not None and best["score"] >= cur["score"] + args.min_gain
            else:
                # Keep the pathology (most of the score and its leading component) while removing features.
                lead = max(cur["comps"], key=lambda c: score.WEIGHTS[c] * cur["comps"][c])
                keep = [k for k in mine if k["score"] >= max(1.0, 0.85 * cur["score"])
                        and k["comps"].get(lead, 0) >= 0.7 * cur["comps"][lead]]
                best = max(keep, key=lambda k: k["score"], default=None)
                ok = best is not None
            if ok:
                lin["steps"].append({"phase": phase, "gen": gen, "ops": best["origin"]["step"], "map": best["name"],
                                     "score": best["score"], "delta": best["delta"],
                                     "moved": {c: round(best["comps"].get(c, 0) - cur["comps"].get(c, 0), 2)
                                               for c in set(best["comps"]) | set(cur["comps"])
                                               if abs(best["comps"].get(c, 0) - cur["comps"].get(c, 0)) >= 0.1}})
                lin["current"] = best
                lin["stale"] = 0
            else:
                lin["stale"] += 1
                if lin["stale"] >= args.patience:
                    lin["active"] = False
        save(run_dir, state, records, lineages, op_log)


# ---- output -----------------------------------------------------------------------------------

def save(run_dir, state, records, lineages, op_log):
    def plain(rec):
        return {k: (rel(v) if isinstance(v, Path) else v) for k, v in rec.items()}
    (run_dir / "state.json").write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    with (run_dir / "maps.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(plain(rec)) + "\n")
    (run_dir / "lineages.json").write_text(json.dumps([{**lin, "seed": lin["seed"]["name"], "current": lin["current"]["name"]}
                                                       for lin in lineages], indent=1) + "\n", encoding="utf-8")
    (run_dir / "ops.json").write_text(json.dumps(op_log) + "\n", encoding="utf-8")


def lead(rec):
    """The component contributing most to a map's score."""
    if not rec.get("comps"):
        return "-"
    k = max(rec["comps"], key=lambda c: score.WEIGHTS[c] * rec["comps"][c])
    return k if rec["comps"][k] > 0 else "-"


def describe(rec):
    """One line on what went wrong, from the worse side's metrics."""
    side, s = max(rec["sides"].items(), key=lambda kv: kv[1].get("score", 0))
    m = s["metrics"]
    if "crash" in m:
        return f"side {side}: match failed: {m['crash']}"
    parts = []
    r = f"reached 1000 at r{m['r1000']}" if m["r1000"] else f"{m['end_gems']} gems by r{m['rounds']}"
    parts.append(f"{r}: {m['gem_rate']:.2f} gems/round, typical here {m.get('expected_rate', 0):.2f} (offer {m['offer_gems']:.0f} gems/side,"
                 f" {m['offer_rate']:.2f}/round)")
    other = [o["metrics"] for k, o in rec["sides"].items() if k != side and "crash" not in o["metrics"]]
    if other and rec["comps"].get("asym"):
        parts.append(f"other side {other[0]['gem_rate']:.2f} gems/round")
    if m.get("carried_end") and m["r1000"] is None:
        parts.append(f"ends carrying {m['carried_end']} untributed gems ({m.get('tributes', 0)} tributes all game)")
    if m["groups_untaken"]:
        parts.append(f"{m['groups_untaken']}/{m['groups_own']} own gem groups never captured ({', '.join(m['untaken_types'])})")
    if m["stall_rounds"]:
        r0, tile = m["stall_at"][0], m["stall_at"][1]
        parts.append(f"{m['stall_champion']} stuck {m['stall_longest']} rounds near {tuple(tile)} from r{r0}"
                     f" ({m['stall_rounds']} stalled champion-rounds; {m.get('recall_starts', 0)} recalls started, {m.get('recalls', 0)} completed)")
    if m["camp_deaths"]:
        parts.append(f"{m['camp_deaths']} deaths to camps ({m['gems_lost_to_camps']} gems lost), first: "
                     + ", ".join(f"r{r} {t}" for r, t, _ in m["camp_death_list"][:3]))
    if m["oof_turns"]:
        parts.append(f"{m['oof_turns']} out-of-fuel turns")
    if m["error_turns"]:
        parts.append(f"{m['error_turns']} bot-error turns")
    if m["poke_actions"]:
        parts.append(f"{m['poke_actions']} attacks on idle champions")
    ref = s.get("ref")
    if ref and "crash" not in ref:
        parts.append(f"ref: " + (f"1000 at r{ref['r1000']}" if ref["r1000"] else f"{ref['end_gems']} gems"))
    return f"side {side}: " + "; ".join(parts)


def origin_text(rec):
    o = rec["origin"]
    text = o.get("preset", o["kind"])
    if o.get("ops"):
        text += " " + " ".join(o["ops"])
    if o.get("chain"):
        text += " + " + " ".join(o["chain"])
    return text


def report(run_dir, top=20):
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (run_dir / "maps.jsonl").read_text(encoding="utf-8").splitlines()]
    lineages = json.loads((run_dir / "lineages.json").read_text(encoding="utf-8"))
    op_log = json.loads((run_dir / "ops.json").read_text(encoding="utf-8"))
    by_name = {r["name"]: r for r in records}
    screen = [r for r in records if r["origin"]["kind"] in ("preset", "mutate", "dir")]
    bad = state["args"]["bad"]

    # Worst maps: the worst per lineage (its final map) and the rest of the screen, deduplicated by lineage.
    seen, worst = set(), []
    for rec in sorted(records, key=lambda r: -r["score"]):
        key = rec["origin"].get("lineage", rec["name"])
        if rec["origin"]["kind"] in ("climb", "shrink"):
            key = rec["origin"]["lineage"]
        seed_lin = next((lin["id"] for lin in lineages if lin["seed"] == rec["name"]), None)
        key = seed_lin if seed_lin is not None else key
        if key in seen:
            continue
        seen.add(key)
        worst.append(rec)
        if len(worst) >= top:
            break
    out = run_dir / "worst"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    for i, rec in enumerate(worst, 1):
        rec["copy"] = rel(out / f"{i:02}-{rec['name']}.map26a")
        shutil.copy2(path_of(rec["file"]), path_of(rec["copy"]))
    for lin in lineages:
        cur = by_name.get(lin["current"])
        if cur and lin["steps"]:
            dest = out / f"L{lin['id']:02}-final-{cur['name']}.map26a"
            shutil.copy2(path_of(cur["file"]), dest)
            lin["copy"] = rel(dest)

    # Clusters: by source preset and by leading failure.
    clusters = {}
    for rec in screen:
        c = clusters.setdefault(rec["origin"].get("preset", "?").split(":")[0], {"maps": 0, "bad": 0, "scores": [], "lead": {}})
        c["maps"] += 1
        c["scores"].append(rec["score"])
        if rec["score"] >= bad:
            c["bad"] += 1
            c["lead"][lead(rec)] = c["lead"].get(lead(rec), 0) + 1
    by_lead = {}
    for rec in screen:
        if rec["score"] >= bad:
            by_lead.setdefault(lead(rec), []).append(rec)
    ops = {}
    for o in op_log:
        ops.setdefault((o["phase"], o["family"]), []).append(o["delta"])

    md = [f"# Map fuzz {state['name']}", "",
          f"Bot `{state['args']['bot']}` against bots/idle" + (f", reference `{state['args']['ref']}` solo on the same maps" if state["args"].get("ref") else "")
          + f". Started {state['started']}; wall {state.get('wall_seconds', 0) / 60:.1f} min. Screen: {len(screen)} maps "
          f"({'one side' if state['args']['one_side'] else 'both sides'}), {state.get('gen_failed', 0)} generation failures"
          + (f" ({', '.join(f'{k} {v}' for k, v in sorted(state.get('gen_failed_by', {}).items()))})" if state.get("gen_failed_by") else "")
          + f"; climb/shrink maps: {len(records) - len(screen)}.",
          "", f"Score: weighted sum of capped components (higher is worse), averaged over the sides played; "
          "typical gem rate by offer rate (offer: rate, gems a round) " + ", ".join(f"{math.exp(x):.2g}: {math.exp(y):.2f}" for x, y in state["base"])
          + f"; a map scoring {bad}+ counts as bad. Weights: "
          + ", ".join(f"{k} {v}" for k, v in score.WEIGHTS.items()) + ".", "",
          "Stages: " + ", ".join(f"{s['label']} {s['maps']} maps {s['seconds']:.0f} s" for s in state.get("stages", [])), "",
          f"## Worst {len(worst)} maps", "",
          "| # | Map | Score | Components | Source | Copy |", "|---|---|---|---|---|---|"]
    for i, rec in enumerate(worst, 1):
        comps = " ".join(f"{k} {v:.2f}" for k, v in sorted(rec["comps"].items(), key=lambda kv: -kv[1]) if v)
        md.append(f"| {i} | {rec['name']} | {rec['score']:.2f} | {comps} | {origin_text(rec)} | `{rec['copy']}` |")
    md += [""] + [f"{i}. **{rec['name']}**: {describe(rec)}" for i, rec in enumerate(worst, 1)]
    md += ["", "## By source (screen)", "", "| Source | Maps | Mean score | Bad | Leading failure among bad |", "|---|---|---|---|---|"]
    for k, c in sorted(clusters.items(), key=lambda kv: -sum(kv[1]["scores"]) / kv[1]["maps"]):
        leads = ", ".join(f"{a} {n}" for a, n in sorted(c["lead"].items(), key=lambda kv: -kv[1]))
        md.append(f"| {k} | {c['maps']} | {sum(c['scores']) / c['maps']:.2f} | {c['bad']} | {leads} |")
    md += ["", "## By failure (screen maps scoring " + f"{bad}+)", "", "| Leading component | Maps | Sources |", "|---|---|---|"]
    for k, recs in sorted(by_lead.items(), key=lambda kv: -len(kv[1])):
        srcs = {}
        for r in recs:
            p = r["origin"].get("preset", "?").split(":")[0]
            srcs[p] = srcs.get(p, 0) + 1
        md.append(f"| {k} | {len(recs)} | " + ", ".join(f"{p} {n}" for p, n in sorted(srcs.items(), key=lambda kv: -kv[1])[:8]) + " |")
    if lineages:
        md += ["", "## Hill-climb", ""]
        for lin in lineages:
            seed_rec, cur = by_name.get(lin["seed"]), by_name.get(lin["current"])
            if not seed_rec or not cur:
                continue
            md.append(f"- **L{lin['id']:02}** {seed_rec['name']} {seed_rec['score']:.2f} -> {cur['name']} {cur['score']:.2f}"
                      + (f" (`{lin.get('copy')}`)" if lin.get("copy") else "") + f"; features {features(seed_rec)} -> {features(cur)}"
                      " (wall+hole+bush %, camps/side, altars)")
            for st in lin["steps"]:
                moved = ", ".join(f"{k} {v:+.2f}" for k, v in sorted(st["moved"].items(), key=lambda kv: -abs(kv[1])))
                md.append(f"  - {st['phase']} g{st['gen']}: `{' '.join(st['ops'])}` {st['delta']:+.2f} -> {st['score']:.2f} ({moved})")
            md.append(f"  - now: {describe(cur)}")
        md += ["", "## Edits (every child against its parent)", "", "| Phase | Op | Children | Worse by 0.5+ | Better by 0.5+ | Mean change |",
               "|---|---|---|---|---|---|"]
        # Parents are the extremes, so most children regress; the share made worse is the signal, not the mean.
        for (phase, fam), ds in sorted(ops.items(), key=lambda kv: (kv[0][0], -sum(d >= 0.5 for d in kv[1]) / len(kv[1]))):
            md.append(f"| {phase} | `{fam}` | {len(ds)} | {sum(d >= 0.5 for d in ds)} | {sum(d <= -0.5 for d in ds)} | {statistics.mean(ds):+.2f} |")
    md += ["", "Rerun one: `cambc run bots/" + state["args"]["bot"] + " bots/idle --map <copy>`; view: "
           "`node tools/mapgen/mapgen.mjs show <copy>`.", f"All maps: `{rel(run_dir)}/maps.jsonl`."]
    (run_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    summary = {"name": state["name"], "state": state, "worst": worst, "lineages": lineages,
               "clusters": {k: {**c, "mean": round(sum(c["scores"]) / c["maps"], 3)} for k, c in clusters.items()},
               "ops": [{"phase": p, "family": f, "n": len(ds), "mean": round(statistics.mean(ds), 3)} for (p, f), ds in ops.items()]}
    (run_dir / "report.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return md


# ---- commands ---------------------------------------------------------------------------------

def bot_dir(spec):
    for p in (ROOT / "bots" / spec, Path(spec)):
        if (p / "src").is_dir():
            return p.resolve()
    raise ValueError(f"bot not found: {spec}")


def test_draft(bot):
    found = TEST_DRAFT.findall((bot / "src" / "params.h").read_text(encoding="utf-8")) if (bot / "src" / "params.h").is_file() else []
    return found[0][1] == "true" if found else None


def cmd_run(args):
    started = perf_counter()
    name = slug(args.name)
    run_dir = OUT / name
    if run_dir.exists() and any(run_dir.iterdir()):
        raise SystemExit(f"{rel(run_dir)} exists; pick another name or delete it")
    run_dir.mkdir(parents=True, exist_ok=True)
    bot = bot_dir(args.bot)
    args.ref_path = bot_dir(args.ref) if args.ref else None
    if args.ref_path and test_draft(bot) != test_draft(args.ref_path):
        say(f"warning: test_draft differs between {args.bot} and {args.ref}; their drafts are not comparable")
    state = {"name": name, "started": datetime.now().strftime("%Y%m%d-%H%M%S"),
             "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k != "func"}}
    rng = random.Random(args.seed)

    # Screen maps.
    names = presets()
    if not names:
        raise SystemExit("mapgen list printed no presets")
    n_mut = round(args.screen * args.mutate_share) if "mutate" in args.sources else 0
    n_pre = args.screen - n_mut if "presets" in args.sources else 0
    order = []
    while len(order) < n_pre:
        order += rng.sample(names, len(names))
    tasks = [("preset", p, args.seed * 100000 + i, run_dir / "maps" / "screen") for i, p in enumerate(order[:n_pre])]
    tasks += [("mutate", "random", args.seed * 100000 + n_pre + i, run_dir / "maps" / "screen") for i in range(n_mut)]
    (run_dir / "maps" / "screen").mkdir(parents=True)
    say(f"Fuzz {name}: {len(names)} presets, generating {n_pre} preset and {n_mut} mutation maps")
    t0 = perf_counter()
    with ThreadPoolExecutor(GEN_JOBS) as pool:
        made = list(pool.map(generate, tasks))
    records = [m for m in made if "failed" not in m]
    failures = [m for m in made if "failed" in m]
    state["gen_failed"] = len(failures)
    state["gen_failed_by"] = {}
    for f in failures:
        state["gen_failed_by"][f["failed"]] = state["gen_failed_by"].get(f["failed"], 0) + 1
    for d in args.include:
        for f in sorted(Path(d).glob("*.map26a")):
            records.append({"name": f"d-{slug(Path(d).name)}-{f.stem}", "file": f.resolve(), "origin": {"kind": "dir", "preset": f"dir:{Path(d).name}"}})
    meta = check([r["file"] for r in records])
    for r in records:
        r["check"] = meta.get(Path(r["file"]).stem, {})
    state["stages"] = [{"label": "generate", "maps": len(records), "seconds": round(perf_counter() - t0, 1), "games": 0}]
    say(f"  generated {len(records)} maps in {perf_counter() - t0:.0f} s; {len(failures)} failed "
        + (str(state["gen_failed_by"]) if failures else ""))

    SEEN.update(digest(r["file"]) for r in records)
    run_stage("screen", records, bot, args, run_dir, state, one_side=args.one_side)
    state["base"] = score.fit_base([s["metrics"] for r in records for s in r["sides"].values() if "crash" not in s["metrics"]])
    for r in records:
        rescore(r, state["base"])
    lineages, op_log = [], []
    save(run_dir, state, records, lineages, op_log)

    # Hill-climb from the worst, at most two per source so one broken preset doesn't take every lineage.
    if args.climb:
        per, seeds = {}, []
        for r in sorted(records, key=lambda r: -r["score"]):
            src = r["origin"].get("preset", "?")
            if r["score"] < args.bad or per.get(src, 0) >= 2:
                continue
            per[src] = per.get(src, 0) + 1
            seeds.append(r)
            if len(seeds) >= args.climb:
                break
        if args.one_side and seeds:
            say(f"replaying {len(seeds)} climb seeds on both sides")
            again = [{"name": s["name"] + "-2s", "file": path_of(s["file"]), "origin": s["origin"], "check": s["check"]} for s in seeds]
            run_stage("seeds", again, bot, args, run_dir, state)
            for s, a in zip(seeds, again):
                rescore(a, state["base"])
                s.update(sides=a["sides"], score=a["score"], comps=a["comps"])
        lineages = [{"id": i, "seed": s, "current": s, "steps": [], "active": True, "stale": 0} for i, s in enumerate(seeds)]
        say(f"climbing from {len(seeds)} maps: " + ", ".join(f"{s['name']} {s['score']:.2f}" for s in seeds))
        search(lineages, "climb", args.gens, args, run_dir, state, bot, state["base"], records, op_log)
        if args.shrink:
            for lin in lineages:
                lin["active"], lin["stale"] = True, 0
            search(lineages, "shrink", args.shrink, args, run_dir, state, bot, state["base"], records, op_log)
    state["wall_seconds"] = round(perf_counter() - started, 1)
    save(run_dir, state, records, lineages, op_log)
    md = report(run_dir, args.top)
    say("\n".join(md[:md.index("## By source (screen)")]))
    say(f"\nReport: {rel(run_dir)}/report.md")
    return 0


def cmd_report(args):
    md = report(OUT / slug(args.name), args.top)
    print("\n".join(md))
    return 0


def cmd_rescore(args):
    """Recompute every game's metrics and every score from the run's analysis/ with the current score.py."""
    run_dir = OUT / slug(args.name)
    analysis = run_dir / "analysis"
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (run_dir / "maps.jsonl").read_text(encoding="utf-8").splitlines()]
    index = json.loads((analysis / "index.json").read_text(encoding="utf-8"))["games"]
    games = {}
    for row in index:
        m = re.match(r".*/stages/([^/]+)/batch-(bot|ref)/\d+-(.+)-(12|21)\.repl26a$", row["source"])
        if m and row["ok"]:
            games[(m.group(1), m.group(2), m.group(3), "AB"[m.group(4) == "21"])] = row
    todo = []
    for rec in records:
        label = Path(rec["file"]).parent.parent.name
        for side, s in rec["sides"].items():
            for role, key in (("bot", "metrics"), ("ref", "ref")):
                # One-side screens replay climb seeds on both sides in the seeds stage, as <name>-2s.
                row = games.get(("seeds", role, rec["name"] + "-2s", side)) or games.get((label, role, rec["name"], side))
                if row and key in s and s[key] is not None and "crash" not in s[key]:
                    todo.append((s, key, (analysis, row, "AB".index(side))))
    for (s, key, _), metrics in zip(todo, score_games([t for _, _, t in todo], args.threads)):
        s[key] = metrics
    screen = [r for r in records if r["origin"]["kind"] in ("preset", "mutate", "dir")]
    state["base"] = score.fit_base([s["metrics"] for r in screen for s in r["sides"].values() if "crash" not in s["metrics"]])
    by_name = {}
    for rec in records:
        rescore(rec, state["base"])
        by_name[rec["name"]] = rec
    lineages = json.loads((run_dir / "lineages.json").read_text(encoding="utf-8"))
    for lin in lineages:
        prev = by_name[lin["seed"]]["score"]
        for st in lin["steps"]:
            st["score"] = by_name[st["map"]]["score"]
            st["delta"], prev = round(st["score"] - prev, 3), st["score"]
    op_log = []
    for k in records:
        if k["origin"]["kind"] in ("climb", "shrink"):
            k["delta"] = round(k["score"] - by_name[k["origin"]["parent"]]["score"], 3)
            op_log += [{"phase": k["origin"]["kind"], "family": family(op), "delta": k["delta"], "lineage": k["origin"]["lineage"]}
                       for op in k["origin"]["step"]]
    (run_dir / "state.json").write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    with (run_dir / "maps.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    (run_dir / "lineages.json").write_text(json.dumps(lineages, indent=1) + "\n", encoding="utf-8")
    (run_dir / "ops.json").write_text(json.dumps(op_log) + "\n", encoding="utf-8")
    md = report(run_dir, args.top)
    print("\n".join(md[:md.index("## By source (screen)")]))
    return 0


def cmd_vs(args):
    """Head-to-head: the bot against BOT on the run's worst maps, both sides."""
    run_dir = OUT / slug(args.name)
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    bot, other = bot_dir(state["args"]["bot"]), bot_dir(args.other)
    if test_draft(bot) != test_draft(other):
        say(f"warning: test_draft differs between {bot.name} and {other.name}; AGENTS.md: match the drafts")
    maps = sorted((run_dir / "worst").glob("*.map26a"))[:args.top]
    stage = run_dir / "stages" / f"vs-{slug(args.other)}"
    shutil.rmtree(stage, ignore_errors=True)
    (stage / "maps").mkdir(parents=True)
    for m in maps:
        shutil.copy2(m, stage / "maps" / m.name)
    batch = stage / "batch"
    command = [sys.executable, str(ROOT / "tools" / "run_batched.py"), str(bot), str(other), "--maps-dir", str(stage / "maps"),
               "--output", str(batch), "--threads", str(args.threads)]
    subprocess.run(command, cwd=ROOT, stdout=(stage / "batch.log").open("w"), stderr=subprocess.STDOUT)
    res = json.loads((batch / "results.json").read_text(encoding="utf-8"))
    lines = [f"# {bot.name} vs {other.name} on {rel(run_dir)}'s worst maps", "", f"{bot.name} wins {res['wins'][0]}, "
             f"{other.name} wins {res['wins'][1]}, errors {res['errors']}", "", "| Map | Side | Winner | Rounds |", "|---|---|---|---|"]
    for m in res["matches"]:
        side = "AB"[m["order"].index(0)]
        win = "error" if "error" in m else (bot.name if m["winner"] == 0 else other.name)
        lines.append(f"| {Path(m['map']).stem} | {side} | {win} | {m.get('rounds', '-')} |")
    (stage / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("run", help="Screen, climb, report")
    p.add_argument("name")
    p.add_argument("--bot", default="astraeus", help="Bot directory under bots/ (default: astraeus)")
    p.add_argument("--ref", help="Also play this bot solo on every map; adds the vs_ref component")
    p.add_argument("--screen", type=int, default=400, help="Maps to generate for the screen (default: 400)")
    p.add_argument("--sources", default="presets,mutate", help="presets, mutate, or both (default)")
    p.add_argument("--mutate-share", type=float, default=0.2, help="Share of the screen from mutate random (default 0.2)")
    p.add_argument("--include", action="append", default=[], metavar="DIR", help="Also screen every map in DIR")
    p.add_argument("--one-side", action="store_true", help="Screen each map from one side (climbs use both)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--climb", type=int, default=8, metavar="K", help="Lineages to hill-climb (0: screen only)")
    p.add_argument("--gens", type=int, default=4, help="Climb generations (default 4)")
    p.add_argument("--children", type=int, default=10, help="Mutations per lineage per generation (default 10)")
    p.add_argument("--shrink", type=int, default=0, metavar="G", help="Then G generations removing features while the pathology holds")
    p.add_argument("--patience", type=int, default=2, help="Generations without gain before a lineage stops")
    p.add_argument("--min-gain", type=float, default=0.15, help="Score gain a child needs to replace its parent")
    p.add_argument("--bad", type=float, default=2.0, help="Score from which a map counts as bad (default 2)")
    p.add_argument("--top", type=int, default=20, help="Worst maps reported and copied")
    p.add_argument("--threads", type=int, default=min(80, cpu_slots.SIZE), help="Concurrent games (default 80)")
    p.add_argument("--timeout", type=int, default=900, help="Seconds per match before it counts as an error")
    p.add_argument("--fuel", type=int, help="Fuel per turn (run_batched.py --fuel)")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("report", help="Rewrite report.md/json of a run")
    p.add_argument("name")
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("rescore", help="Recompute metrics and scores of a run with the current score.py, then report")
    p.add_argument("name")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--threads", type=int, default=min(80, cpu_slots.SIZE))
    p.set_defaults(func=cmd_rescore)
    p = sub.add_parser("vs", help="Head-to-head against another bot on a run's worst maps, both sides")
    p.add_argument("name")
    p.add_argument("other")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--threads", type=int, default=min(80, cpu_slots.SIZE))
    p.set_defaults(func=cmd_vs)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
