"""Count each function's fuel-charged operators in a built wasm (llvm-objdump -d), for the wrapper refunds.

    py tools/replay/harness/count_ops.py BOT.wasm [--prefix sdk_] [--split] > costs.json

Wasmtime charges 1 per operator except nop, drop, block, loop, end, else, unreachable and return.
A function with branches has no single count; the generated wrappers have none (checked here).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

OBJDUMP = next((p for p in (Path.home() / "AppData/Local/cambc/wasi-sdk-33/bin/llvm-objdump.exe",
                             Path.home() / ".cache/cambc/wasi-sdk-33/bin/llvm-objdump") if p.exists()), "llvm-objdump")
FREE = {"nop", "drop", "block", "loop", "end", "else", "unreachable", "return"}
BRANCH = {"br", "br_if", "br_table", "if", "try_table", "throw", "rethrow", "throw_ref"}


def count_ops(wasm, prefix="sdk_", names=None):
    out = subprocess.run([str(OBJDUMP), "-d", str(wasm)], capture_output=True, text=True, check=True).stdout
    costs, cur, ops, branchy = {}, None, 0, False
    head = re.compile(r"^[0-9a-f]+ <(.+)>:$")
    for line in out.splitlines():
        m = head.match(line.strip())
        if m:
            if cur is not None:
                costs[cur] = None if branchy else ops
            name = m.group(1)
            cur = name if (name.startswith(prefix) or (names and name in names)) else None
            ops, branchy = 0, False
            continue
        if cur is None:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        instr = parts[1].strip() if len(parts) >= 2 else ""
        if not instr or instr.endswith(":"):
            continue
        if instr in BRANCH:
            branchy = True
        if instr not in FREE:
            ops += 1
    if cur is not None:
        costs[cur] = None if branchy else ops
    return costs


def split_ops(wasm, prefix="sdk_"):
    """Recorder wrappers (harness_rec.h shape): unpaused operators before the real import (from entry
    through the first call, the pause, then after the third call, the resume, through the fourth, the
    import) and after it (from there through the fifth call, the pause, then after the seventh, the
    resume, to the end)."""
    out = subprocess.run([str(OBJDUMP), "-d", str(wasm)], capture_output=True, text=True, check=True).stdout
    costs, cur, ops = {}, None, []
    head = re.compile(r"^[0-9a-f]+ <(.+)>:$")

    def done():
        if cur is None:
            return
        calls = [k for k, x in enumerate(ops) if x.startswith("call")]
        if len(calls) != 7 or any(x in BRANCH for x in ops):
            costs[cur] = None
            return
        c = calls
        unpaused = lambda a, b: sum(1 for x in ops[a:b] if x not in FREE)
        costs[cur] = [unpaused(0, c[0] + 1) + unpaused(c[2] + 1, c[3] + 1), unpaused(c[3] + 1, c[4] + 1) + unpaused(c[6] + 1, len(ops))]
    for line in out.splitlines():
        m = head.match(line.strip())
        if m:
            done()
            name = m.group(1)
            cur, ops = (name if name.startswith(prefix) else None), []
            continue
        if cur is None:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        instr = parts[1].strip()
        if instr and not instr.endswith(":"):
            ops.append(instr)
    done()
    return costs


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "sdk_"
    print(json.dumps(split_ops(args[0], prefix) if "--split" in sys.argv else count_ops(args[0], prefix), indent=0))
