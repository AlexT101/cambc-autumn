#!/usr/bin/env python3
"""Set up .htb editing: install the HTB extension into VS Code and check what it needs.

  python3 tools/htb/install.py        (Windows: py tools\\htb\\install.py)

1. Generates every .htb bot's src/ (tools/htb/hgen.py) and builds it once with `cambc build`, which writes the
   compile_commands.json clangd reads to find cambc.h.
2. Installs tools/htb/vscode/htb-<version>.vsix with VS Code's `code` command.
3. Checks for clangd, which gives the squiggles, completion and go to definition.
Then reload VS Code (Developer: Reload Window) and open an .htb file.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WINDOWS = sys.platform == "win32"
sys.path.insert(0, str(HERE))
import hgen  # noqa: E402


def first(paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def code_cli():
    local, programs = os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", "")
    return first([shutil.which("code"), shutil.which("code.cmd"),
                  "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
                  os.path.join(local, "Programs", "Microsoft VS Code", "bin", "code.cmd"),
                  os.path.join(programs, "Microsoft VS Code", "bin", "code.cmd")])


def clangd():
    return first(["/opt/homebrew/opt/llvm/bin/clangd", "/usr/local/opt/llvm/bin/clangd", shutil.which("clangd"),
                  os.path.join(os.environ.get("ProgramFiles", ""), "LLVM", "bin", "clangd.exe")])


def cambc_cli():
    venv = hgen.ROOT / ".venv"
    return first([shutil.which("cambc"), str(venv / "bin" / "cambc"), str(venv / "Scripts" / "cambc.exe")])


def setup_bots():
    bots = hgen.find_bots([])
    if not bots:
        print("-  no .htb bots under bots/ yet")
        return True
    cambc, ok = cambc_cli(), True
    for bot in bots:
        if hgen.run(bot) == "refused":
            ok = False
            continue
        if (bot / "compile_commands.json").exists():
            continue
        if not cambc:
            print(f"x  {bot.name}: cambc not found; run `cambc build {bot.name}` once so clangd can find cambc.h")
            ok = False
            continue
        r = subprocess.run([cambc, "build", bot.name], cwd=hgen.ROOT, capture_output=True, text=True)
        if r.returncode == 0 and (bot / "compile_commands.json").exists():
            print(f"ok {bot.name}: built once (clangd now knows its compile flags)")
        else:
            print(f"x  `cambc build {bot.name}` failed:\n{(r.stdout + r.stderr).strip()[-2000:]}")
            ok = False
    return ok


def version_key(p):
    return tuple(int(x) for x in re.findall(r"\d+", Path(p).stem))


def main():
    ok = setup_bots()
    packages = sorted(glob.glob(str(HERE / "vscode" / "htb-*.vsix")), key=version_key)
    code = code_cli()
    if not packages:
        print("x  no tools/htb/vscode/htb-*.vsix (build it: see tools/htb/vscode/README.md)")
        ok = False
    elif not code:
        print("x  VS Code's `code` command not found. Install VS Code, or in VS Code run")
        print("   'Extensions: Install from VSIX...' and pick " + os.path.relpath(packages[-1]))
        ok = False
    else:
        r = subprocess.run([code, "--install-extension", packages[-1], "--force"], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"ok VS Code extension installed: {Path(packages[-1]).name}")
        else:
            print(f"x  installing {Path(packages[-1]).name} failed:\n{r.stdout}{r.stderr}")
            ok = False

    c = clangd()
    if c:
        v = subprocess.run([c, "--version"], capture_output=True, text=True).stdout.splitlines()
        print(f"ok clangd: {c} ({v[0] if v else 'unknown version'})")
        if WINDOWS and not shutil.which("clangd"):
            print(f"   (not on PATH: the extension looks in Program Files\\LLVM; else set htb.clangdPath to {c})")
    else:
        print("x  clangd not found; squiggles and completion need it:")
        print("   macOS: brew install llvm    Windows: winget install LLVM.LLVM    Linux: sudo apt install clangd")
        ok = False

    print("\nNext: reload VS Code (Developer: Reload Window) and open an .htb file, e.g. bots/htb-starter/bot.htb."
          if ok else "\nFix the items marked x, then run this again.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
