"""Patch table for fuelhook.c's call counter: every wasmtime array_call_trampoline over cambc's GuestCtx (one per
host import), with how many of its first bytes to displace (whole instructions, >= 14 bytes, no RIP-relative
operand or relative branch among them).

    objdump -d --no-show-raw-insn cambc > cambc.dis   (with raw bytes: drop --no-show-raw-insn)
    python3 make_tramp_table.py SYMS DISASM > tramp.tsv
"""
import re
import sys

syms, dis = sys.argv[1], sys.argv[2]
targets = {}
for line in open(syms, encoding="utf-8", errors="replace"):
    if " <wasmtime::runtime::func::HostFunc>::array_call_trampoline::<wasm_runtime::GuestCtx" in line:
        targets[int(line.split()[0], 16)] = None
insn = re.compile(r"^\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*\t?(.*)$")
want = sorted(targets)
wi = 0
cur = None
acc = 0
bad = False
out = {}
for line in open(dis, encoding="utf-8", errors="replace"):
    m = insn.match(line)
    if not m:
        continue
    addr = int(m.group(1), 16)
    if addr in targets:
        cur, acc, bad = addr, 0, False
    if cur is None:
        continue
    n = len(m.group(2).split())
    text = m.group(3)
    if "rip" in text or re.match(r"\s*(j[a-z]+|call|loop)\b", text):
        bad = True
    acc += n
    if acc >= 14:
        if not bad:
            out[cur] = acc
        cur = None
for a in want:
    if a in out:
        print("%x %d" % (a, out[a]))
print("covered %d of %d" % (len(out), len(want)), file=sys.stderr)
