"""Create a version's re-run workspace from scratch: <dir>/ws with its two harness patches and the exact
release bot, plus ladder-list.json for decode_all.mjs.

    py tools/replay/harness/setup_ws.py [--version vN] [--ws <dir>/ws] [--refund 10] [--no-build]

The version (versions.py) gives the source and <dir> (replays/<version>); its release bot is ws/bots/<version>-release.

Idempotent; each step is skipped when its result is already there:
  1. `cambc init --yes WS`; the manifest's maps copied from the repo's maps/ (byte-identical to the pool).
  2. cmake/CMakeLists.txt: a bot directory holding a RELEASE_CODE file is compiled without CAMBC_DEBUG
     even in a debug run (live_trace_bot.py's trace bot is release code that uses the debug-only fuel_pause imports).
  3. sdk/cpp/cambc.h: DebugGuard's refund as the CAMBC_DEBUG_REFUND macro, and a cambc_debug_depth counter (once
     read by the retired recorder's wrappers; kept so existing workspaces build the same wasm).
  4. bots/<version>-release: the version's source, built with --release.
  5. <dir>/ladder-list.json ([{key, replay}] from the manifest) for decode_all.mjs, rewritten as the
     manifest grows.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import versions

REPO = Path(__file__).resolve().parents[3]
CFG = None
CAMBC = shutil.which("cambc") or "cambc"

CMAKE_OLD = "if(CAMBC_DEBUG)\n  target_compile_definitions(bot PRIVATE CAMBC_DEBUG)"
CMAKE_NEW = """# Harness: a bot with a RELEASE_CODE file is compiled exactly as for --release
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
// Harness: nesting depth of open debug blocks, so that import wrappers can
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
        sys.exit(f"{path}: not the stock cambc text (3.0.5 and 4.0.0 share it); patch it by hand (see {Path(__file__).name})")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def manifest():
    return [(f"{g['group'][:8]}-{g['position']}", g) for g in json.loads(CFG.manifest.read_text(encoding="utf-8"))["games"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--ws", help="default <dir>/ws")
    ap.add_argument("--refund", type=int, default=10, help="CAMBC_DEBUG_REFUND (stock SDK: 2; the existing ws used 10)")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()
    global CFG
    CFG = versions.get(args.version)
    ws = Path(args.ws or CFG.ws).resolve()

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

    rel = ws / "bots" / CFG.release.name
    if not (rel / "src").exists():
        shutil.copytree(CFG.src, rel / "src")
        log(f"bots/{rel.name}: copied {CFG.src}")
    if not args.no_build:
        run([CAMBC, "build", rel.relative_to(ws), "--release"], ws)
        log(f"built {rel.name} (--release)")

    rel_wasm = rel / ".cambc/build-release/bot-injected.wasm"
    ll = CFG.dir / "ladder-list.json"
    text = json.dumps([{"key": k, "replay": g["replay"]} for k, g in manifest()])
    if not ll.exists() or ll.read_text(encoding="utf-8") != text:
        ll.write_text(text, encoding="utf-8")
        log(f"wrote {ll.relative_to(REPO)}")
    if rel_wasm.exists():
        log(f"{rel_wasm.relative_to(ws)}: sha1 {hashlib.sha1(rel_wasm.read_bytes()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
