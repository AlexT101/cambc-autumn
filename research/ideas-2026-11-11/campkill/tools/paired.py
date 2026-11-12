"""Paired CAND - REF win rate on a mechanism suite (same maps, seeds, sides, bodies), from ab.py batches named
ck-TAG-BOT-OPP-fFUEL. usage: paired.py TAG CAND REF [FUEL]"""
import glob, json, math, os, sys
tag, cand, ref = sys.argv[1:4]; fuel = sys.argv[4] if len(sys.argv) > 4 else '200000'
def load(bot):
    out = {}
    for opp in ('Mt3q', 'Flp4'):
        for f in glob.glob(f'replays/batch-*-ab-ck-{tag}-{bot}-{opp}-f{fuel}-maps/results.json'):
            for m in json.load(open(f))['matches']:
                if m.get('winner') is None: continue
                out[(opp, os.path.basename(m['map']), tuple(m['order']))] = (m['winner'] == 0, m.get('oof_turns', [0, 0])[0])
    return out
a, b = load(cand), load(ref)
keys = sorted(set(a) & set(b))
for opp in ('all', 'Flp4', 'Mt3q'):
    ks = [k for k in keys if opp == 'all' or k[0] == opp]
    d = [a[k][0] - b[k][0] for k in ks]; n = len(d)
    if not n: continue
    m = sum(d) / n; sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, n - 1))
    wa = sum(a[k][0] for k in ks) / n
    print(f"{opp:5} n {n}  CAND win {100*wa:.1f}%  REF {100*(wa-m):.1f}%  diff {100*m:+.2f} +/- {196*sd/math.sqrt(n):.2f}  "
          f"changed {sum(x != 0 for x in d)}  OOF/game CAND {sum(a[k][1] for k in ks)/n:.3f} REF {sum(b[k][1] for k in ks)/n:.3f}")
