"""Is the Fish in a recorded game r8? Two tests on rbook's extract.mjs entries (WORK/ent/KEY.json):
  sig     Fish r8 xors its priority's low 20 bits with a mask fixed per champion slot and round
          (research/ideas-2026-11-12/fishr8/mask_r8.json): the share of Fish's priority writes that decode to a
          payload under 2^17 with the mask of the round that wrote it (1.0 on our pinned r8 games, 0.13 by chance).
  opening Fish plays the same until it first meets the other team: the rounds for which Fish's actions equal
          those in a pinned r8 game of ours on the same cell (--ref: the book's WORK dirs, entries MAP-SIDE-v...).

    py r8check.py WORK [--ref ~/tmp-offload/rbook/ff ...]"""
import argparse, glob, json, os, re, sys
from pathlib import Path

MASK = {int(k): {int(r): v for r, v in d.items()} for k, d in
        json.load(open(Path(__file__).resolve().parents[2] / 'ideas-2026-11-12/fishr8/mask_r8.json')).items()}
PRIORITY = 4


def sig(ent, shift=0):
    fit = tot = 0
    for k, b in enumerate(ent['opp']['bodies']):
        for i, (_, acts) in enumerate(b['turns'][:1000]):
            for a in acts:
                if a[0] != PRIORITY:
                    continue
                m = MASK.get(k, {}).get(i + 1 + shift)
                if m is None:
                    continue
                tot += 1
                fit += ((a[3] & 0xFFFFF) ^ m) < (1 << 17)
    return fit / tot if tot else None, tot


def opening(ent, ref):
    """Rounds from the start in which every Fish body's actions equal the reference game's."""
    A, B = ent['opp']['bodies'], ref['opp']['bodies']
    if ent['opp']['picks'] != ref['opp']['picks']:
        return -1
    n = min(len(A[0]['turns']), len(B[0]['turns']))
    for r in range(n):
        if any(a['turns'][r] != b['turns'][r] for a, b in zip(A, B)):
            return r
    return n


def cell(key):
    m = re.match(r'^(.+)-([ab])-v\d+-', key)
    return (m.group(1), m.group(2)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--ref', nargs='*', default=[str(Path.home() / 'tmp-offload/rbook/ff'), str(Path.home() / 'tmp-offload/rbook/hostcheck')])
    ap.add_argument('--json')
    a = ap.parse_args()
    refs = {}
    for d in a.ref:
        for f in glob.glob(os.path.join(os.path.expanduser(d), 'ent', '*.json')):
            c = cell(os.path.basename(f)[:-5])
            if c:
                refs.setdefault(c, f)
    out = {}
    for f in sorted(glob.glob(os.path.join(os.path.expanduser(a.work), 'ent', '*.json'))):
        key = os.path.basename(f)[:-5]
        ent = json.load(open(f))
        s, n = sig(ent)
        c = cell(key)
        o = opening(ent, json.load(open(refs[c]))) if c in refs else None
        out[key] = dict(sig=s, writes=n, opening=o, rounds=ent['rounds'], outcome=ent['outcome'], gems=ent['gems'], problems=ent['problems'][:3])
        print(f"{key:55s} sig {s if s is None else round(s, 4)} of {n:5d}  opening same {o} of {ent['rounds']} rounds  {ent['outcome']} {ent['gems']} {ent['problems'][:2]}")
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
