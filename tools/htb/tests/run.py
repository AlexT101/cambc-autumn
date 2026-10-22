#!/usr/bin/env python3
"""Tests for .htb:  python3 tools/htb/tests/run.py [CASE ...] [--fast] [--keep]

Each folder in tests/cases/ is a small bot: .htb files (in any subfolders) and headers, plus
  expect.txt   what main() prints: the case is built natively and run (plain C++, no cambc API)
  errors.txt   instead: `file:line` (from the bot folder) the compiler must report an error at, one per line
  notes.txt    text hgen's notes must contain, one per line (without it, any note fails the case)
  editor.txt   `file:line` clangd should flag in the editor, one per line (without it: no squiggles at all)
  wasm.txt     (empty) a real bot using the cambc API: only cambc's compiler and the editor check it
Every case goes through:
  1. hgen: no crash, the expected notes
  2. a native build, then the program's output (expect.txt), or the expected errors (errors.txt); errors must
     point at the bot's own files, never into the generated src/
  3. cambc's wasm compiler (syntax only), which must agree with the native build
  4. clangd on every .htb file, opened the way the HTB extension opens them
  5. robustness: every .htb file cut off at every token, with each token deleted, and with junk inserted
     before each token, must not crash (or hang) hgen
--fast skips 4 and 5.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import hgen  # noqa: E402
import htbcheck  # noqa: E402

CASES = HERE / "cases"
META = ("expect.txt", "errors.txt", "notes.txt", "editor.txt", "wasm.txt")


def first(*paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


CXX = first("/opt/homebrew/opt/llvm/bin/clang++", "/usr/local/opt/llvm/bin/clang++", shutil.which("clang++"))
CLANGD = first("/opt/homebrew/opt/llvm/bin/clangd", "/usr/local/opt/llvm/bin/clangd", shutil.which("clangd"))
WASI = htbcheck.wasi_clang()
LSP = HERE.parent / "vscode" / "node_modules" / "vscode-jsonrpc"   # clangd_diag.js talks LSP through it


def lines_of(path):
    """A case's expectation file, without blank lines and `#` comments (None if it has none)."""
    if not path.exists():
        return None
    return [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def wasm_command(unity):
    sysroot = Path(WASI).parent.parent / "share" / "wasi-sysroot"
    return [WASI, "--target=wasm32-wasip1", f"--sysroot={sysroot}", "-DCAMBC_DEBUG", f"-I{hgen.ROOT / 'sdk' / 'cpp'}",
            "-isystem", str(sysroot / "include" / "wasm32-wasip1" / "eh" / "c++" / "v1"), "-std=c++20",
            "-msimd128", "-mbulk-memory", "-fwasm-exceptions", "-mllvm", "-wasm-use-legacy-eh=false",
            "-fsyntax-only", str(unity)]


def located(errors, name, wants):
    """Which `file:line` in wants no error line names."""
    return [w for w in wants if not any(l.startswith(f"{name}/{w}:") for l in errors)]


def check_build(name, bot, meta, tmp, fails):
    unity = bot / "src" / "unity.cpp"
    if meta["wasm.txt"] is not None:
        if not WASI:
            fails.append("needs cambc's compiler (run `cambc build` on any bot once)")
            return
        w = subprocess.run(wasm_command(unity), cwd=bot.parent, capture_output=True, text=True)
        if w.returncode != 0:
            fails.append("wasm build failed:\n  " + "\n  ".join([l for l in w.stderr.splitlines() if "error" in l][:10]))
        return
    exe = tmp / "prog"
    b = subprocess.run([CXX, "-std=c++20", "-o", str(exe), str(unity)], cwd=bot.parent, capture_output=True, text=True)
    errors = [l for l in b.stderr.splitlines() if ": error:" in l]
    into_src = [l for l in errors if "/src/" in l.split(": error:")[0] or l.startswith("src/")]
    if into_src:
        fails.append("errors point into generated src/:\n  " + "\n  ".join(into_src[:5]))
    if meta["errors.txt"] is not None:
        if b.returncode == 0:
            fails.append("expected a compile error, but it built")
        missing = located(errors, name, meta["errors.txt"])
        if missing:
            fails.append(f"no error at {', '.join(missing)}; errors were:\n  " + "\n  ".join(errors[:8]))
        if WASI:    # the command-line checker must point at the same lines
            c = subprocess.run([sys.executable, str(HERE.parent / "htbcheck.py"), str(bot)], cwd=bot.parent,
                               capture_output=True, text=True)
            shown = [l for l in c.stdout.splitlines() if "error" in l]
            gone = located(shown, name, meta["errors.txt"])
            if c.returncode == 0 or gone:
                fails.append(f"htbcheck.py doesn't report {', '.join(gone) or 'the errors'}:\n  "
                             + "\n  ".join(c.stdout.splitlines()[:8]))
    elif b.returncode != 0:
        fails.append("native build failed:\n  " + "\n  ".join((errors or b.stderr.splitlines())[:10]))
    else:
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=20)
        got = [l.rstrip() for l in r.stdout.splitlines()]
        want = meta["expect.txt"] or []
        if r.returncode != 0:
            fails.append(f"program exited with {r.returncode}: {r.stderr.strip()[:300]}")
        if got != want:
            diff = [f"  line {i + 1}: want {w!r}, got {g!r}" for i, (w, g) in
                    enumerate(zip(want + [None] * len(got), got + [None] * len(want))) if w != g][:10]
            fails.append("output differs:\n" + "\n".join(diff))
    if WASI:
        w = subprocess.run(wasm_command(unity), cwd=bot.parent, capture_output=True, text=True)
        if (w.returncode == 0) != (b.returncode == 0):
            fails.append(f"wasm compiler disagrees with the native build (wasm exit {w.returncode}):\n  "
                         + "\n  ".join([l for l in w.stderr.splitlines() if "error" in l][:8]))


def check_editor(name, bot, meta, fails):
    build = bot / ".cambc" / "build"
    build.mkdir(parents=True, exist_ok=True)
    unity = bot / "src" / "unity.cpp"
    (bot / "compile_commands.json").write_text(json.dumps([{
        "directory": str(build), "file": str(unity),
        # cambc's own flags when its compiler is there, as in a real bot
        "arguments": ([a for a in wasm_command(unity) if a != "-fsyntax-only"] if WASI
                      else [CXX, "-std=c++20", str(unity)]) + ["-c", "-o", "unity.o"]}]))
    files = [str(p) for p in hgen.bot_files(bot, (hgen.SOURCE,))]
    r = subprocess.run(["node", str(HERE / "clangd_diag.js"), CLANGD, str(bot), *files],
                       capture_output=True, text=True, timeout=180)
    try:
        diags = json.loads(r.stdout)
    except ValueError:
        fails.append(f"clangd check failed: {r.stderr[-500:]}")
        return
    want = set(meta["editor.txt"] or [])
    seen = set()
    for f, ds in diags.items():
        rel = os.path.relpath(f, bot)
        if ds is None:
            fails.append(f"editor: clangd never answered for {rel}")
            continue
        for d in ds:
            if d["severity"] != 1:
                continue
            key = f"{rel}:{d['line']}"
            seen.add(key)
            if key not in want:
                fails.append(f"editor squiggle {key}:{d['col']}: {d['message']} [{d['code']}]")
    for key in sorted(want - seen):
        fails.append(f"editor: expected an error at {key}, none shown")


JUNK = ["{", "}", "(", ")", "<", ">", "template <", "class", "struct X", "enum", "operator", "::", "~",
        "#if X\n", "\n#endif\n", "\n#define Q(", '"', "'", "/*", "R\"(", "using", "namespace", "typedef", "=",
        ";", ",", "static", "friend", "try", "catch (...)", "requires", "->", "[[", "]]", "extern \"C\""]


class Hang(Exception):
    pass


def _alarm(signum, frame):
    raise Hang()


def check_robust(bot, fails):
    """hgen runs on every save, so half-written files must never crash (or hang) it."""
    files = hgen.bot_files(bot, (hgen.SOURCE,))
    original_read, override = hgen.read, {}
    hgen.read = lambda p: override[Path(p)] if Path(p) in override else original_read(p)
    signal.signal(signal.SIGALRM, _alarm)
    try:
        for f in files:
            text = original_read(f)
            toks, comments = hgen.tokenize(text)
            cuts = sorted({t.end for t in toks} | {t.start + 1 for t in toks if t.end - t.start > 1}
                          | {(s + e) // 2 for s, e in comments})
            variants = [(f"cut at {pos}", text[:pos]) for pos in cuts]
            variants += [(f"without the {t.text!r} at {t.start}", text[:t.start] + text[t.end:]) for t in toks]
            variants += [(f"with {j!r} inserted at {t.start}", text[:t.start] + j + " " + text[t.start:])
                         for n, t in enumerate(toks) for j in [JUNK[n % len(JUNK)]]]
            broken = 0
            for what, variant in variants:
                override[Path(f)] = variant
                signal.alarm(5)
                try:
                    hgen.Bot(bot).generate()
                except Hang:
                    fails.append(f"robustness: hgen hangs on {f.name} {what}")
                    broken += 1
                except Exception:
                    tb = traceback.format_exc().strip().splitlines()
                    fails.append(f"robustness: hgen crashes on {f.name} {what}: {tb[-1]} ({tb[-3].strip()})")
                    broken += 1
                finally:
                    signal.alarm(0)
                if broken >= 3:
                    break
            override.pop(Path(f), None)
    finally:
        hgen.read = original_read


def check_case(name, fast, keep):
    src = CASES / name
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix="htbtest-"))
    try:
        bot = tmp / "bots" / name
        shutil.copytree(src, bot, ignore=shutil.ignore_patterns(*META))
        meta = {m: lines_of(src / m) for m in META}
        r = subprocess.run([sys.executable, str(HERE.parent / "hgen.py"), str(bot)], capture_output=True, text=True)
        out = r.stdout + r.stderr
        if r.returncode != 0 or "Traceback" in out:
            return name, [f"hgen failed:\n{out}"], tmp
        again = subprocess.run([sys.executable, str(HERE.parent / "hgen.py"), "--check", str(bot)],
                               capture_output=True, text=True)
        if again.returncode != 0:
            fails.append(f"hgen isn't stable: a second run would change src/:\n  {again.stdout.strip()}")
        leaked = [p for p in (bot / "src").rglob("*") if p.is_file() and str(tmp) in p.read_text(errors="replace")]
        if leaked:
            fails.append(f"generated files hold this machine's paths: {[str(p.relative_to(bot)) for p in leaked]}")
        notes = [l.strip()[6:] for l in out.splitlines() if l.strip().startswith("note: ")]
        for want in meta["notes.txt"] or []:
            if not any(want in n for n in notes):
                fails.append(f"missing note: {want}\n  notes were: {notes}")
        if meta["notes.txt"] is None and notes:
            fails.append("unexpected notes:\n  " + "\n  ".join(notes))
        check_build(name, bot, meta, tmp, fails)
        if not fast:
            if CLANGD and LSP.exists() and shutil.which("node"):
                check_editor(name, bot, meta, fails)
            check_robust(bot, fails)
        return name, fails, tmp
    except Exception:
        return name, fails + ["runner error:\n" + traceback.format_exc()], tmp
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--fast", action="store_true", help="skip the editor and robustness checks")
    ap.add_argument("--keep", action="store_true", help="keep each case's generated bot and print where")
    ap.add_argument("-j", type=int, default=4)
    args = ap.parse_args()
    names = args.cases or sorted(p.name for p in CASES.iterdir() if p.is_dir())
    if not CXX:
        sys.exit("no clang++ found")
    editor = (CLANGD if LSP.exists() and shutil.which("node") else "skipped: needs node and `npm install` in tools/htb/vscode"
              ) if CLANGD else "not found: editor checks skipped"
    print(f"clang++ {CXX}\nclangd  {editor}\nwasm    {WASI or 'not found: skipped'}\n")
    failed = 0
    with ProcessPoolExecutor(args.j) as pool:
        for name, fails, tmp in pool.map(check_case, names, [args.fast] * len(names), [args.keep] * len(names)):
            print(f"{'ok  ' if not fails else 'FAIL'} {name}" + (f"   ({tmp})" if args.keep else ""))
            for f in fails:
                print("     " + f.replace("\n", "\n     "))
            failed += bool(fails)
    print(f"\n{len(names) - failed}/{len(names)} cases pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
