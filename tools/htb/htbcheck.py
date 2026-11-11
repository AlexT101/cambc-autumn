#!/usr/bin/env python3
"""Check .htb bots for errors without building them.

For each bot: first every .htb file is checked on its own for unbalanced brackets
and unterminated strings (these would otherwise confuse the generated code and
bury the real mistake under follow-on errors); then tools/htb/hgen.py regenerates src/
and the cambc compiler checks src/unity.cpp with -fsyntax-only (no code is
generated, nothing is written). Errors and warnings point at your .htb files and
lines.

The compiler flags come from the bot's compile_commands.json (written by its first
`cambc build`), so the check uses exactly what cambc builds with; before that, the
SDK's standard flags are used.

  python3 tools/htb/htbcheck.py                 every bot with .htb files
  python3 tools/htb/htbcheck.py archives/htb-starter   just these bots
Exit status: 0 when every bot is clean, 1 when any has errors.
"""

import bisect
import glob
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hgen  # noqa: E402  (tools/htb/hgen.py)

ROOT = hgen.ROOT


def wasi_clang():
    homes = [os.path.expanduser("~/Library/Caches/cambc"), os.path.expanduser("~/.cache/cambc"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "cambc")]
    found = sorted(p for h in homes for name in ("clang++", "clang++.exe")
                   for p in glob.glob(os.path.join(h, "wasi-sdk-*", "bin", name)))
    return found[-1] if found else None


def check_command(bot_dir):
    """The compiler command for src/unity.cpp, as a syntax-only check, and the folder to run it in."""
    unity = bot_dir / "src" / "unity.cpp"
    db = bot_dir / "compile_commands.json"
    if db.exists():
        for entry in json.loads(db.read_text()):
            if Path(entry["file"]).resolve() != unity.resolve():
                continue
            args = entry.get("arguments") or shlex.split(entry["command"])
            out, skip = [], False
            for a in args:
                if skip:
                    skip = False
                    continue
                if a == "-o":
                    skip = True
                    continue
                if a == "-c" or a.startswith("-O"):
                    continue
                out.append(a)
            return out + ["-fsyntax-only"], entry.get("directory", str(bot_dir))
    clang = wasi_clang()
    if not clang:
        return None, None
    sysroot = Path(clang).parent.parent / "share" / "wasi-sysroot"
    return [clang, "--target=wasm32-wasip1", f"--sysroot={sysroot}", "-DCAMBC_DEBUG", f"-I{ROOT / 'sdk' / 'cpp'}",
            "-isystem", str(sysroot / "include" / "wasm32-wasip1" / "eh" / "c++" / "v1"), "-std=c++20", "-msimd128",
            "-mbulk-memory", "-fwasm-exceptions", "-fsyntax-only", str(unity)], str(bot_dir)


PAIRS = {")": "(", "]": "[", "}": "{"}


def structure_errors(path):
    """Unbalanced ( [ { and unterminated strings in one .htb file, as 'file:line:col: error: ...' lines."""
    src = path.read_text(encoding="utf-8")
    starts = [0] + [i + 1 for i, c in enumerate(src) if c == "\n"]

    def where(off):   # file:line:column of a character offset
        line = bisect.bisect_right(starts, off)
        return f"{os.path.relpath(path, ROOT)}:{line}:{off - starts[line - 1] + 1}"

    toks, _ = hgen.tokenize(src)
    errors, stack = [], []
    for t in toks:
        if t.kind == "str":
            body = t.text.lstrip("uUL8R")
            if len(body) < 2 or body[-1] != body[0]:
                errors.append(f"{where(t.start)}: error: unterminated {'string' if body[:1] == '\"' else 'character'} literal")
        elif t.text in ("(", "[", "{"):
            stack.append(t)
        elif t.text in PAIRS:
            if not stack:
                errors.append(f"{where(t.start)}: error: '{t.text}' has no matching '{PAIRS[t.text]}'")
            elif stack[-1].text != PAIRS[t.text]:
                o = stack.pop()
                errors.append(f"{where(t.start)}: error: '{t.text}' closes the '{o.text}' opened at {where(o.start)}")
            else:
                stack.pop()
    errors += [f"{where(o.start)}: error: '{o.text}' is never closed" for o in stack]
    return errors


def check(bot_dir):
    rel = lambda p: os.path.relpath(p, ROOT)
    found = [e for f in hgen.bot_files(bot_dir, (hgen.SOURCE,)) for e in structure_errors(f)]
    if found:
        print("\n".join(found))
        print(f"{bot_dir.name}: {len(found)} bracket/string error(s); fix these first ({rel(bot_dir)})")
        return False
    if hgen.run(bot_dir) == "refused":
        return False
    cmd, cwd = check_command(bot_dir)
    if cmd is None:
        print(f"{bot_dir.name}: no cambc compiler found; run `cambc build {bot_dir.name}` once")
        return False
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    text = (r.stdout + r.stderr).replace(str(ROOT) + os.sep, "")
    if r.returncode == 0 and "warning:" not in text:
        print(f"{bot_dir.name}: no errors ({len(hgen.Bot(bot_dir).files)} .htb files)")
    else:
        print(text.rstrip())
        print(f"{bot_dir.name}: {'errors' if r.returncode else 'warnings only'} -- see above ({rel(bot_dir)})")
    return r.returncode == 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):   # a Windows console's code page can't show every file name
        stream.reconfigure(errors="replace")
    names = sys.argv[1:] if argv is None else argv
    if any(n in ("-h", "--help") for n in names):
        print(__doc__)
        return 0
    bots = hgen.find_bots(names)
    if not bots:
        print("htbcheck: no bot has .htb files in its own folder yet")
        return 0
    return 0 if all([check(b) for b in bots]) else 1


if __name__ == "__main__":
    sys.exit(main())
