"""Create the v38 re-run workspace from scratch: replays/v38-top20/ws (cambc 3.0.5) with its two harness
patches, the exact v38 release bot and the recorder, plus ladder-list.json for decode_all.mjs.

    py tools/replay/harness/setup_ws.py [--ws replays/v38-top20/ws] [--refund 10] [--no-build]

Idempotent; each step is skipped when its result is already there:
  1. `cambc init --yes WS`; the manifest's maps copied from the repo's maps/ (byte-identical to the pool).
  2. cmake/CMakeLists.txt: a bot directory holding a RELEASE_CODE file is compiled without CAMBC_DEBUG
     even in a debug run (the recorder is release code that uses the debug-only fuel_pause imports).
  3. sdk/cpp/cambc.h: DebugGuard's refund as the CAMBC_DEBUG_REFUND macro and the cambc_debug_depth
     counter that the tracer's wrappers read (trace_batch.py checks for it).
  4. bots/v38-release: `git archive 5b02a02 bots/hyperion` (v38), built with --release.
  5. bots/v38-rec: v38-release's sources + RELEASE_CODE + harness_rec.h + zz_harness.cpp from
     gen_wrappers.py --mode rec. Built with zero costs, measured with count_ops.py --split (bots/v38-rec/costs.json),
     regenerated with those costs, rebuilt, and the counts checked unchanged.
  6. replays/v38-top20/ladder-list.json ([{key, replay}] from manifest.json) for decode_all.mjs.
"""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
V38 = REPO / "replays/v38-top20"
V38_COMMIT = "5b02a02"
CAMBC = shutil.which("cambc") or "cambc"

CMAKE_OLD = "if(CAMBC_DEBUG)\n  target_compile_definitions(bot PRIVATE CAMBC_DEBUG)"
CMAKE_NEW = """# Harness (replays/v38-top20): a bot with a RELEASE_CODE file is compiled exactly as for --release
# even in a debug run, so the debug run's fuel pause imports can be used by its own wrappers.
if(CAMBC_DEBUG AND NOT EXISTS "${BOT_DIR}/RELEASE_CODE")
  target_compile_definitions(bot PRIVATE CAMBC_DEBUG)"""

SDK_STOCK = """/// Fuel pause/resume guard behind the `debug_block` macro.
struct DebugGuard
{
	DebugGuard() { sdk_fuel_pause(); }
	// Refund the guard's own call overhead before restoring the saved fuel.
	~DebugGuard() { sdk_fuel_adjust(2); sdk_fuel_resume(); }"""
SDK_NEW = """/// Fuel pause/resume guard behind the `debug_block` macro.
#ifndef CAMBC_DEBUG_REFUND
#define CAMBC_DEBUG_REFUND {refund}
#endif
// Harness (replays/v38-top20): nesting depth of open debug blocks, so that import wrappers can
// tell the bot's own host calls from those made inside a debug block.
extern "C" inline std::int32_t cambc_debug_depth = 0;
struct DebugGuard
{
	DebugGuard() { ++cambc_debug_depth; sdk_fuel_pause(); }
	// Refund the guard's own call overhead before restoring the saved fuel.
	~DebugGuard() { sdk_fuel_adjust(CAMBC_DEBUG_REFUND); sdk_fuel_resume(); --cambc_debug_depth; }"""


def log(msg):
    print(msg, flush=True)


def run(cmd, cwd):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{' '.join(map(str, cmd))} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def patch(path, old, new, marker):
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    if old not in text:
        sys.exit(f"{path}: not the stock cambc 3.0.5 text; patch it by hand (see {Path(__file__).name})")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def manifest():
    return [(f"{g['group'][:8]}-{g['position']}", g) for g in json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))["games"]]


def count_ops(wasm):
    return json.loads(run([sys.executable, HERE / "count_ops.py", wasm, "--split"], REPO))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ws", default=str(V38 / "ws"))
    ap.add_argument("--refund", type=int, default=10, help="CAMBC_DEBUG_REFUND (stock SDK: 2; the existing ws used 10)")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()
    ws = Path(args.ws).resolve()

    if not (ws / "cambc.toml").exists():
        log(f"cambc init {ws}")
        ws.parent.mkdir(parents=True, exist_ok=True)
        run([CAMBC, "init", "--yes", ws], ws.parent)
    (ws / "maps").mkdir(exist_ok=True)
    copied = 0
    for _, g in manifest():
        name = g["map"].replace("_", "-") + ".map26a"
        if not (ws / "maps" / name).exists():
            shutil.copyfile(REPO / "maps" / name, ws / "maps" / name)
            copied += 1
    log(f"maps: {copied} copied")
    if patch(ws / "cmake/CMakeLists.txt", CMAKE_OLD, CMAKE_NEW, "RELEASE_CODE"):
        log("patched cmake/CMakeLists.txt: RELEASE_CODE")
    if patch(ws / "sdk/cpp/cambc.h", SDK_STOCK, SDK_NEW.replace("{refund}", str(args.refund)), "cambc_debug_depth"):
        log(f"patched sdk/cpp/cambc.h: CAMBC_DEBUG_REFUND {args.refund}, cambc_debug_depth")

    rel, rec = ws / "bots/v38-release", ws / "bots/v38-rec"
    if not (rel / "src").exists():
        data = subprocess.run(["git", "archive", "--format=tar", V38_COMMIT, "bots/hyperion/src"], cwd=REPO, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    out = rel / "src" / Path(m.name).relative_to("bots/hyperion/src")
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(tf.extractfile(m).read())
        log(f"bots/v38-release: git archive {V38_COMMIT}")
    if not args.no_build:
        run([CAMBC, "build", rel.relative_to(ws), "--release"], ws)
        log("built v38-release (--release)")

    rel_wasm = rel / ".cambc/build-release/bot-injected.wasm"
    rec_wasm = rec / ".cambc/build/bot-injected.wasm"
    if not (rec / "src/zz_harness.cpp").exists():
        if args.no_build:
            sys.exit("bots/v38-rec needs v38-release built (drop --no-build)")
        (rec / "src").mkdir(parents=True, exist_ok=True)
        for f in (rel / "src").iterdir():
            shutil.copyfile(f, rec / "src" / f.name)
        shutil.copyfile(HERE / "wrappers/harness_rec.h", rec / "src/harness_rec.h")
        (rec / "RELEASE_CODE").write_bytes(b"")
        gen = [sys.executable, HERE / "gen_wrappers.py", "--mode", "rec", "--wasm", rel_wasm, "--sdk", ws / "sdk/cpp",
               "--out", rec / "src/zz_harness.cpp"]
        run(gen, REPO)
        run([CAMBC, "build", rec.relative_to(ws)], ws)
        costs = count_ops(rec_wasm)
        costs_path = rec / "costs.json"
        costs_path.write_text(json.dumps(costs, indent=0))
        run(gen + ["--costs", costs_path], REPO)
        run([CAMBC, "build", rec.relative_to(ws)], ws)
        again = count_ops(rec_wasm)
        if again != costs:
            sys.exit(f"recorder wrapper op counts changed after the cost pass: {[k for k in costs if again.get(k) != costs[k]][:10]}")
        log(f"bots/v38-rec: recorder built, {len(costs)} wrapper costs in {costs_path}")
    elif not args.no_build:
        run([CAMBC, "build", rec.relative_to(ws)], ws)
        log("built v38-rec")

    ll = V38 / "ladder-list.json"
    if not ll.exists():
        ll.write_text(json.dumps([{"key": k, "replay": g["replay"]} for k, g in manifest()]))
        log(f"wrote {ll.relative_to(REPO)}")
    for p in (rel_wasm, rec_wasm):
        if p.exists():
            log(f"{p.relative_to(ws)}: sha1 {hashlib.sha1(p.read_bytes()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
