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
  5. robustness: every .htb file cut off at every token, with each token deleted, with junk inserted
     before each token, and 150 seeded random multi-token edits, must not crash (or hang) hgen
--fast skips 4 and 5. Two more checks run with every full run (or by name):
  lifecycle    editing, deleting and renaming files; files hgen didn't write in src/; --check; --watch;
               your own .clangd settings kept
  stress       a 20,000-line file, 300 small files, namespaces and classes nested 100 deep
"""

import argparse
import json
import os
import random
import time
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
            rng = random.Random(f.name)
            for n in range(150):
                ts, ops = list(toks), []
                for _ in range(rng.randint(1, 4)):
                    if not ts:
                        break
                    i, op = rng.randrange(len(ts)), rng.choice(["del", "dup", "swap", "junk"])
                    ops.append(f"{op}@{ts[i].start}")
                    if op == "del":
                        del ts[i]
                    elif op == "dup":
                        ts.insert(i, ts[i])
                    elif op == "swap" and i + 1 < len(ts):
                        ts[i], ts[i + 1] = ts[i + 1], ts[i]
                    else:
                        ts.insert(i, hgen.Tok("p", rng.choice(JUNK), 0, 0))
                variants.append((f"after random edits {' '.join(ops)}",
                                 "\n".join(t.text if t.end == 0 else text[t.start:t.end] for t in ts)))
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


def hgen_run(*args, cwd=None):
    return subprocess.run([sys.executable, str(HERE.parent / "hgen.py"), *map(str, args)], capture_output=True,
                          text=True, cwd=cwd)


def build_and_run(bot, tmp):
    exe = tmp / "prog"
    b = subprocess.run([CXX, "-std=c++20", "-o", str(exe), str(bot / "src" / "unity.cpp")], capture_output=True, text=True)
    if b.returncode != 0:
        return "build failed: " + b.stderr[:400]
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=20).stdout.strip()


def check_lifecycle(tmp, fails):
    bot = tmp / "bots" / "life bot"
    (bot / "sub").mkdir(parents=True)
    write = lambda rel, text: (bot / rel).write_text(text)
    write(".clangd", "CompileFlags:\n  CompilationDatabase: .\n  Add: [-DMY_OWN_FLAG]\n")
    write("a.htb", "int a_val() { return 1; }\n")
    write("sub/b.htb", "struct B { int v = 2; };\n")
    write("main.htb", "#include <cstdio>\nint main() { std::printf(\"%d %d\\n\", a_val(), B{}.v); }\n")
    r = hgen_run(bot)
    if r.returncode or build_and_run(bot, tmp) != "1 2":
        fails.append(f"lifecycle: first run: {r.stdout} {build_and_run(bot, tmp)}")
        return
    if hgen_run("--check", bot).returncode != 0:
        fails.append("lifecycle: --check says a fresh src/ is out of date")
    clangd = (bot / ".clangd").read_text()
    if "-DMY_OWN_FLAG" not in clangd or "sub/b\\.htb" not in clangd:
        fails.append(f"lifecycle: .clangd lost your settings or the file blocks:\n{clangd[:300]}")
    write("a.htb", "int a_val() { return 1 + extra(); }\nint extra() { return 10; }\n")
    if hgen_run("--check", bot).returncode != 1:
        fails.append("lifecycle: --check didn't notice an edited file")
    hgen_run(bot)
    if build_and_run(bot, tmp) != "11 2":
        fails.append(f"lifecycle: after an edit: {build_and_run(bot, tmp)}")
    (bot / "sub" / "b.htb").unlink()
    write("main.htb", "#include <cstdio>\nint main() { std::printf(\"%d\\n\", a_val()); }\n")
    r = hgen_run(bot)
    left = [p for p in [bot / "src/headers/sub/b.h", bot / "src/sub/b.inl", bot / "src/sub", bot / ".cambc/hgen/sub/b.h"]
            if p.exists()]
    if left or "sub/b\\.htb" in (bot / ".clangd").read_text() or build_and_run(bot, tmp) != "11":
        fails.append(f"lifecycle: deleting sub/b.htb left {[str(p.relative_to(bot)) for p in left]}: {r.stdout}")
    (bot / "a.htb").rename(bot / "renamed.htb")
    hgen_run(bot)
    if (bot / "src/a.inl").exists() or not (bot / "src/renamed.inl").exists() or build_and_run(bot, tmp) != "11":
        fails.append("lifecycle: renaming a.htb didn't move its output")
    write("src/mine.cpp", "// mine\n")
    before = (bot / "src/renamed.inl").read_text()
    write("renamed.htb", "int a_val() { return 5; }\n")
    r = hgen_run(bot)
    if r.returncode != 1 or "left alone" not in r.stdout or (bot / "src/renamed.inl").read_text() != before:
        fails.append(f"lifecycle: a file hgen didn't write in src/ should stop it: exit {r.returncode}, {r.stdout}")
    (bot / "src/mine.cpp").unlink()
    w = subprocess.Popen([sys.executable, str(HERE.parent / "hgen.py"), "--watch", str(bot)], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(1.0)
        write("renamed.htb", "int a_val() { return 7; }\n")
        for _ in range(50):
            time.sleep(0.2)
            if "return 7" in (bot / "src/renamed.inl").read_text():
                break
        else:
            fails.append("lifecycle: --watch didn't pick up a saved file within 10 s")
    finally:
        w.terminate()
        w.wait(timeout=10)


def check_stress(tmp, fails):
    def timed(bot, limit, what):
        t = time.time()
        r = hgen_run(bot)
        took = time.time() - t
        if r.returncode or "Traceback" in r.stdout + r.stderr:
            fails.append(f"stress: {what}: hgen failed: {(r.stdout + r.stderr)[-400:]}")
        elif took > limit:
            fails.append(f"stress: {what}: hgen took {took:.1f} s (limit {limit} s)")
        return took
    big = tmp / "bots" / "big"
    big.mkdir(parents=True)
    lines = []
    for n in range(2000):
        lines += [f"struct S{n} {{", f"    int v = {n};", f"    int get() const {{ return v + K{n}; }}", "};",
                  f"constexpr int K{n} = {n};", f"int f{n}(S{n} s) {{ return s.get(); }}", "", "", "", ""]
    (big / "huge.htb").write_text("\n".join(lines) + "\n")
    (big / "main.htb").write_text("int main() { return f1999(S1999{}) == 3998 ? 0 : 1; }\n")
    timed(big, 15, "a 20,000-line file")
    if build_and_run(big, tmp) != "":
        fails.append(f"stress: the 20,000-line bot: {build_and_run(big, tmp)[:300]}")
    many = tmp / "bots" / "many"
    for n in range(300):
        (many / f"d{n % 7}" / f"e{n % 3}").mkdir(parents=True, exist_ok=True)
        (many / f"d{n % 7}" / f"e{n % 3}" / f"f{n}.htb").write_text(
            f"struct T{n} {{ T{n + 1}* next = nullptr; int k = {n}; }};\nint g{n}() {{ return T{n}{{}}.k; }}\n"
            if n < 299 else "struct T299 { int k = 299; };\nint g299() { return 299; }\n")
    (many / "main.htb").write_text("int main() { return g0() + g299() == 299 ? 0 : 1; }\n")
    timed(many, 15, "300 files")
    deep = tmp / "bots" / "deep"
    deep.mkdir(parents=True)
    ns = "".join(f"namespace n{i} {{ " for i in range(100)) + "int leaf() { return 3; } " + "} " * 100
    cls = "".join(f"struct C{i} {{ int m{i}() const {{ return {i}; }} " for i in range(100)) + "};" * 100
    (deep / "deep.htb").write_text(ns + "\n" + cls + "\n")
    (deep / "main.htb").write_text("int main() { return " + "::".join(f"n{i}" for i in range(100)) + "::leaf() == 3 ? 0 : 1; }\n")
    timed(deep, 15, "namespaces and classes nested 100 deep")
    if build_and_run(deep, tmp) != "":
        fails.append(f"stress: the deeply nested bot: {build_and_run(deep, tmp)[:300]}")


def check_case(name, fast, keep):
    if name in ("lifecycle", "stress"):
        tmp, fails = Path(tempfile.mkdtemp(prefix="htbtest-")), []
        try:
            (check_lifecycle if name == "lifecycle" else check_stress)(tmp, fails)
        except Exception:
            fails.append("runner error:\n" + traceback.format_exc())
        finally:
            if not keep:
                shutil.rmtree(tmp, ignore_errors=True)
        return name, fails, tmp
    src = CASES / name
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix="htbtest-"))
    try:
        bot = tmp / "bots" / name
        shutil.copytree(src, bot, symlinks=True, ignore=shutil.ignore_patterns(*META))
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
    names = args.cases or sorted(p.name for p in CASES.iterdir() if p.is_dir()) + ([] if args.fast else ["lifecycle", "stress"])
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
