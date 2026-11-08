"""Danger and pressure examples from `fastrunner scenario --hitlog` rollouts of a labify_reply.py bot.

    python3 research/reply-model/build.py OUT.npz ROLLOUTS.jsonl [...] [--procs N]

Each fighter turn of the logging bot gives, per visible enemy e within 8 of its end tile p:
  danger: e's features at p (reply::danger_features) and the damage e dealt us in its next turn;
  pressure: our features against e from p and the damage we dealt e in our next turn.
A label is kept only when the turn that decides it was played (not cut off by the rollout's end), and the
victim was still alive at its start. Enemies that are not fighters (idle on their spawn) are left out.
"""
import base64
import json
import multiprocessing as mp
import struct
import sys
import zlib

import numpy as np

DN, PN, HEAD = 48, 36, 10


def rows_of(path):
    with open(path, "rb") as f:
        for line in f:
            yield line


def parse(args):
    line, cfg = args
    r = json.loads(line)
    if "error" in r:
        return None
    fighters = {f["id"]: f["team"] for f in r["fighters"]}
    hits = r["hits"]
    gid = zlib.crc32(r["id"].encode()) % (1 << 24)
    D, P = [], []
    # next record index by actor after k
    n = len(hits)
    for k, h in enumerate(hits):
        rnd, c, p0, p1, loss, feat = h
        if feat is None:
            continue
        b = base64.b64decode(feat)
        x = struct.unpack(f"<{len(b) // 4}f", b)
        nd = int(x[7])
        off = HEAD
        for _ in range(nd):
            e = int(x[off + 1])
            dx = x[off + 2: off + 2 + DN]
            px = x[off + 2 + DN: off + 2 + DN + PN]
            off += 2 + DN + PN
            if e not in fighters or fighters[e] == fighters.get(c):
                continue
            # c's next turn: the window in which every enemy acts once (twice for one with two turns before ours)
            k2 = next((j for j in range(k + 1, n) if hits[j][1] == c), None)
            if k2 is None and r["stop"] != "team_dead":
                continue
            stop = n if k2 is None else k2
            dmg, acted, dead = 0.0, False, False
            for j in range(k + 1, stop):
                hj = hits[j]
                if hj[1] == e:
                    acted = True
                    for t, l, died in hj[4]:
                        if t == c:
                            dmg += max(0.0, l)
                elif not acted:
                    dead |= any(t == c and died for t, l, died in hj[4])
            if not dead and (acted or k2 is not None):
                D.append((gid, rnd, c, e) + tuple(dx) + (dmg,))
            if k2 is None:
                continue
            gone = any(t == e and died for j in range(k + 1, k2) for t, l, died in hits[j][4])
            if not gone:
                pd = sum(max(0.0, l) for t, l, died in hits[k2][4] if t == e)
                P.append((gid, rnd, c, e) + tuple(px) + (pd,))
    return cfg, D, P


def main():
    args = sys.argv[1:]
    procs = 16
    if "--procs" in args:
        i = args.index("--procs")
        procs = int(args[i + 1])
        del args[i:i + 2]
    out, files = args[0], args[1:]
    tasks = []
    for f in files:
        cfg = {"oo": 0, "oa": 1, "ao": 2}[f.rsplit("-", 1)[1].split(".")[0]]
        tasks.append((f, cfg))
    D, P, Dc, Pc = [], [], [], []
    with mp.Pool(procs) as pool:
        for f, cfg in tasks:
            for res in pool.imap_unordered(parse, ((l, cfg) for l in rows_of(f)), chunksize=64):
                if res is None:
                    continue
                c, d, p = res
                D.extend(d), P.extend(p)
                Dc.extend([c] * len(d)), Pc.extend([c] * len(p))
    D = np.asarray(D, dtype=np.float32)
    P = np.asarray(P, dtype=np.float32)
    np.savez_compressed(out, D=D, P=P, Dc=np.asarray(Dc, np.int8), Pc=np.asarray(Pc, np.int8))
    print(f"{out}: danger {len(D)}, pressure {len(P)}")


if __name__ == "__main__":
    main()
