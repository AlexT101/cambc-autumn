"""Counterfactual examples from `--alt K --alt-fighter all --hitlog` rollouts: at a fighter's first strike-search
decision, rollout 0 plays ocean's choice and rollout k the k-th next-best, so the same state ends on different tiles.

    python3 research/reply-model/build_alt.py OUT.npz ROLLOUTS.jsonl [...] [--procs N]

Rows as build.py's (danger D, pressure P), each from the deciding fighter's turn in the decision round only, with
the group (frame, fighter, round) and the alternative k in front: [group, k, round, us, enemy, features..., label].
"""
import base64
import json
import multiprocessing as mp
import struct
import sys
import zlib

import numpy as np

DN, PN, HEAD = 48, 36, 10


def labels(r, k, c, e, hits, fighters):
    """build.py's danger and pressure labels for the turn record k of fighter c against e (None: censored)."""
    n = len(hits)
    k2 = next((j for j in range(k + 1, n) if hits[j][1] == c), None)
    if k2 is None and r["stop"] != "team_dead":
        return None, None
    stop = n if k2 is None else k2
    dmg, acted, dead = 0.0, False, False
    for j in range(k + 1, stop):
        hj = hits[j]
        if hj[1] == e:
            acted = True
            dmg += sum(max(0.0, l) for t, l, died in hj[4] if t == c)
        elif not acted:
            dead |= any(t == c and died for t, l, died in hj[4])
    d = dmg if (not dead and (acted or k2 is not None)) else None
    p = None
    if k2 is not None and not any(t == e and died for j in range(k + 1, k2) for t, l, died in hits[j][4]):
        p = sum(max(0.0, l) for t, l, died in hits[k2][4] if t == e)
    return d, p


def parse(line):
    r = json.loads(line)
    if "error" in r or "alt" not in r:
        return [], []
    a = r["alt"]
    fighters = {f["id"]: f["team"] for f in r["fighters"]}
    hits = r["hits"]
    if a["k"] == 0:
        decisions = [(int(f), v["round"]) for f, v in a["first"].items() if v]
        alt = 0
    else:
        decisions = [(a["fighter"], a["round"])]
        alt = a["k"]
    D, P = [], []
    for c, rnd in decisions:
        g = zlib.crc32(f'{r["id"]}/{c}/{rnd}'.encode()) % (1 << 24)
        k = next((j for j, h in enumerate(hits) if h[0] == rnd and h[1] == c), None)
        if k is None or hits[k][5] is None:
            continue
        b = base64.b64decode(hits[k][5])
        x = struct.unpack(f"<{len(b) // 4}f", b)
        off = HEAD
        for _ in range(int(x[7])):
            e = int(x[off + 1])
            dx, px = x[off + 2: off + 2 + DN], x[off + 2 + DN: off + 2 + DN + PN]
            off += 2 + DN + PN
            if e not in fighters or fighters[e] == fighters.get(c):
                continue
            d, p = labels(r, k, c, e, hits, fighters)
            if d is not None:
                D.append((g, alt, rnd, c, e) + tuple(dx) + (d,))
            if p is not None:
                P.append((g, alt, rnd, c, e) + tuple(px) + (p,))
    return D, P


def main():
    args = sys.argv[1:]
    procs = 16
    if "--procs" in args:
        i = args.index("--procs")
        procs = int(args[i + 1])
        del args[i:i + 2]
    out, files = args[0], args[1:]
    D, P = [], []
    with mp.Pool(procs) as pool:
        for f in files:
            for d, p in pool.imap_unordered(parse, open(f, "rb"), chunksize=64):
                D.extend(d), P.extend(p)
    np.savez_compressed(out, D=np.asarray(D, np.float32), P=np.asarray(P, np.float32))
    print(f"{out}: danger {len(D)}, pressure {len(P)}")


if __name__ == "__main__":
    main()
