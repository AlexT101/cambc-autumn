#!/usr/bin/env python3
"""Lab filler: runs lab rounds (emblem, draft, tune) on idle local compute, as the lowest-priority work.

    nohup setsid python3 research/ideas-2026-11-12/labs/filler.py > ~/tmp-offload/labs/filler.out 2>&1 &

State lives in ~/tmp-offload/labs (L):
- BASE: the bot directory the next round builds on (e.g. bots/variants/chy-life), read when a round is created, so
  the coordinator can switch it without a restart. A round keeps the base it started with.
- LIST: lab kinds in priority order, one a line (emb, draft, tune; '#' comments). The next round is the first kind
  with no round yet on the current BASE. When every kind has one, the filler waits for BASE to change.
- conf.json (optional, re-read every poll): weight (slot weight of a round, default 0.001), idle_slots (main-pool slots
  others may hold and still count as idle, 6), idle_polls (consecutive idle polls before a start, 3), poll (60 s).
- PAUSE: start no new round (a running one goes on). STOP: the filler exits (a running one goes on).
- rounds/ID/: round.json (id, kind, base, its source hash, seed block), events, out.log, pid, exit (the wrapper
  writes the exit code), candidate.json (the round's result), posted (its ready line was written).
- filler.log: one line per decision. Ready lines go to ~/tmp-offload/handoff/parked/labs.ready.

Yielding: a round starts only after idle_polls polls with no gate, A/B, lab or mapgen of anyone else running and at
most idle_slots main-pool slots held by others. Once started it runs to the end, but every game it plays takes a slot
at slot weight `weight` (fair share: a group below its weighted share, or with no one else waiting below theirs, may
take a free slot), so when a gate starts waiting the lab keeps only ~weight/(1+weight) of the pool and the gate gets
every slot as the lab's games end (seconds). All its processes run at nice 19."""
import hashlib, json, os, re, signal, subprocess, time
from pathlib import Path

L = Path.home() / "tmp-offload" / "labs"
R = Path("/home/ubuntu/cambc-autumn")
HERE = Path(__file__).resolve().parent
READY = Path.home() / "tmp-offload" / "handoff" / "parked" / "labs.ready"
MAIN = R / ".git" / "cambc-slots"
# Lab numbering continues each lab's history (emblem rounds 1-5, draft labs to draft18, localq tune1-8).
FIRST = {"emb": 6, "draft": 19, "tune": 9}
SEED0, SEED_STEP = 7700000, 10000  # maps/SUITES.md: the filler's block, 10,000 seeds a round
# Command lines that mean someone else's gate, A/B or lab is running (or preparing: mapgen, compile-ahead).
BUSY = re.compile(r"(fgate(_batch)?\.py|tools/ab\.py|run_batched\.py|tools/solo\.py|lqgate\.py|mapgen\.mjs|"
                  r"draftlab/lab\.py|emblab/elab\.py|emblab/lab\.py|tune/tune\.py|fuel/bench\.py|gate_compile_ahead)")


def log(msg):
    with open(L / "filler.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} {msg}\n")


def conf():
    try:
        c = json.loads((L / "conf.json").read_text())
    except (OSError, ValueError):
        c = {}
    return {"weight": 0.001, "idle_slots": 6, "idle_polls": 3, "poll": 60, **c}


def ours(pid):
    """Whether a process belongs to a filler round (its environment says so)."""
    try:
        env = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return False
    return b"LABS_FILLER=1" in env


def foreign_busy():
    """Processes of other work matching BUSY: [(pid, short command)]."""
    out, me = [], os.getpid()
    for p in Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) == me:
            continue
        try:
            args = (p / "cmdline").read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        # Only an interpreter running the script: a waiter's `bash -c '... pgrep -f fgate.py'` is not a gate.
        if not re.search(r"(python[\d.]*|node|py)$", Path(args[0]).name):
            continue
        cmd = " ".join(args[:4])
        if BUSY.search(cmd) and not ours(p.name):
            out.append((int(p.name), cmd[:120]))
    return out


def foreign_slots():
    """Main-pool slots held by groups other than the filler's."""
    import fcntl
    n = 0
    for f in MAIN.glob("slot-*"):
        try:
            with open(f, "rb") as h:
                try:
                    fcntl.flock(h.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                except OSError:
                    if not h.read().decode(errors="replace").strip().startswith("labs-"):
                        n += 1
        except OSError:
            pass
    return n


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def rounds():
    return sorted((p for p in (L / "rounds").iterdir() if (p / "round.json").is_file()), key=lambda p: p.stat().st_mtime) \
        if (L / "rounds").is_dir() else []


def info(d):
    return json.loads((d / "round.json").read_text())


def running():
    """The round in play, if any (pid alive, no exit). A round whose process vanished without an exit is marked."""
    for d in rounds():
        if (d / "exit").exists() or not (d / "pid").exists():
            continue
        if alive(int((d / "pid").read_text())):
            return d
        (d / "exit").write_text("CRASH\n")
        log(f"{d.name}: process gone without an exit code (CRASH)")
    return None


def src_hash(bot):
    root = R / bot / "src"
    rows = [(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob("*")) if p.is_file()]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def ready(line):
    READY.parent.mkdir(parents=True, exist_ok=True)
    with open(READY, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} {line}\n")
    log(f"READY {line}")


def post(d):
    """A finished round's ready line, once."""
    if (d / "posted").exists():
        return
    i, code = info(d), (d / "exit").read_text().strip()
    try:
        c = json.loads((d / "candidate.json").read_text())
    except (OSError, ValueError):
        c = {}
    if code == "0" and c.get("variant"):
        ready(f"labs {d.name} CANDIDATE base={i['base']} cand=bots/{c['variant']} patch={c.get('patch', '')} :: {c.get('summary', '')}")
    elif code == "0":
        ready(f"labs {d.name} NO-CANDIDATE base={i['base']} :: {c.get('summary', 'no candidate')}")
    else:
        fail = (d / "fail").read_text().strip() if (d / "fail").exists() else ""
        ready(f"labs {d.name} FAILED exit={code} base={i['base']} :: {fail or 'see ' + str(d / 'out.log')}")
    (d / "posted").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n", time.gmtime()))


def next_kind(base):
    done = {info(d)["kind"] for d in rounds() if info(d)["base"] == base}
    for line in (L / "LIST").read_text().splitlines():
        k = line.split("#")[0].strip()
        if k and k not in done:
            return k
    return None


def create(kind, base, c):
    rs = rounds()
    n = max([int(re.sub(r"\D", "", info(d)["id"]) or 0) + 1 for d in rs if info(d)["kind"] == kind] + [FIRST[kind]])
    rid = f"{kind}{n}"
    seed = SEED0 + SEED_STEP * len(rs)
    d = L / "rounds" / rid
    d.mkdir(parents=True)
    i = {"id": rid, "kind": kind, "base": base, "base_src_sha256": src_hash(base), "seed": seed, "weight": c["weight"],
         "created": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
         "decision": "user 2026-11-12: labs as filler on idle local compute, lowest priority; candidate only, gated by the coordinator"}
    (d / "round.json").write_text(json.dumps(i, indent=1) + "\n")
    return d


def start(d, c):
    i = info(d)
    env = dict(os.environ, LABS_FILLER="1", CAMBC_SLOT_GROUP=f"labs-{i['id']}", CAMBC_SLOT_WEIGHT=str(i.get("weight", c["weight"])),
               CAMBC_BIN=str(R / "tools/fastengine/runner/fastrunner"), FASTRUNNER_MODE="native",
               PATH=f"/home/ubuntu/venv/bin:{Path.home()}/.cargo/bin:{os.environ.get('PATH', '')}", VIRTUAL_ENV="/home/ubuntu/venv")
    env.pop("CAMBC_SLOT_DIR", None)
    env.pop("CAMBC_SLOTS", None)
    script = HERE / f"round_{i['kind']}.sh"
    (d / "exit").unlink(missing_ok=True)
    wrap = f'nice -n 19 bash {script} {d}; echo $? > {d}/exit'
    p = subprocess.Popen(["bash", "-c", wrap], cwd=R, env=env, stdout=open(d / "out.log", "a"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    (d / "pid").write_text(f"{p.pid}\n")
    log(f"START {i['id']} on {i['base']} (seed {i['seed']}, weight {env['CAMBC_SLOT_WEIGHT']}), pid {p.pid}")
    return p


def main():
    L.mkdir(parents=True, exist_ok=True)
    (L / "filler.pid").write_text(f"{os.getpid()}\n")
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)  # reap round wrappers
    log(f"FILLER up, pid {os.getpid()}")
    idle, said = 0, None
    while True:
        c = conf()
        if (L / "STOP").exists():
            log("STOP file: filler exits (a running round goes on)")
            return
        for d in rounds():
            if (d / "exit").exists():
                post(d)
        cur = running()
        if cur is not None:
            idle = 0
            note = f"running {cur.name}"
        elif (L / "PAUSE").exists():
            idle, note = 0, "paused"
        else:
            base = (L / "BASE").read_text().strip()
            busy, slots = foreign_busy(), foreign_slots()
            if busy or slots > c["idle_slots"]:
                idle = 0
                note = f"busy: {len(busy)} processes ({busy[0][1][:60] if busy else ''}), {slots} slots"
            else:
                idle += 1
                note = f"idle {idle}/{c['idle_polls']}"
            kind = next_kind(base) if (R / base / "src").is_dir() else None
            if not (R / base / "src").is_dir():
                note = f"BASE {base} has no src/"
            elif kind is None:
                note = f"every lab in LIST has a round on {base}; waiting for BASE to change"
            elif idle >= c["idle_polls"]:
                start(create(kind, base, c), c)
                idle, note = 0, "started"
        # Log state changes only (busy notes differ by counts: log their kind).
        key = note.split(":")[0]
        if key != said:
            log(note)
            said = key
        time.sleep(c["poll"])


if __name__ == "__main__":
    main()
