"""Win rate, Prism deaths and out-of-fuel turns of arms on the same games: python3 quick.py REF ARM...

Each name is a pair of files ~/tmp-offload/prismlife/out/NAME-{Flp4,Mt3q}.jsonl written by arm.sh (outcome.mjs on a
batch): one line a game. Our side is team A in files ending -12 and B in -21. Games are paired by (opponent, file).
"""
import json, math, os, sys
O = os.path.expanduser('~/tmp-offload/prismlife/out')
PRISM = 6  # engine champion type (enums.json champions)
OPPS = ('Flp4', 'Mt3q')


def load(name):
    rows = {}
    for opp in OPPS:
        for line in open(f'{O}/{name}-{opp}.jsonl'):
            g = json.loads(line)
            f = g['file']; us = 0 if f.rsplit('.', 1)[0].endswith('-12') else 1
            ours = [c for c in g['champions'] if c['team'] == us]
            pr = [c for c in ours if c['type'] == PRISM]
            rows[(opp, f)] = dict(win=g['winner'] == us, prism=bool(pr), pdeaths=sum(c['deaths'] for c in pr), deaths=sum(c['deaths'] for c in ours),
                                  kills=sum(c['kills'] for c in ours), rounds=g['rounds'], gems=g['tributed'][us], egems=g['tributed'][1 - us], opp=opp)
    return rows


def main():
    names = sys.argv[1:]
    A = {n: load(n) for n in names}
    ref = A[names[0]]
    for n in names:
        R = A[n]; G = list(R.values()); P = [g for g in G if g['prism']]
        w = sum(g['win'] for g in G) / len(G)
        oof = ''
        try: oof = ' | '.join(l.strip().split(',')[0].replace('Out-of-fuel turns: ', '') for l in open(f'{O}/{n}.oof'))
        except OSError: pass
        print(f'{n:14s} {len(G):5d} games  win {100 * w:6.2f}%  Prism games win {100 * sum(g["win"] for g in P) / max(1, len(P)):6.2f}%  Prism deaths a Prism game {sum(g["pdeaths"] for g in P) / max(1, len(P)):.3f}  '
              f'games with one {100 * sum(1 for g in P if g["pdeaths"]) / max(1, len(P)):5.1f}%  team deaths a game {sum(g["deaths"] for g in G) / len(G):.2f}  kills {sum(g["kills"] for g in G) / len(G):.2f}  rounds {sum(g["rounds"] for g in G) / len(G):.0f}  OOF {oof}')
        print(' ' * 15 + '; '.join(f'{o}: win {100 * sum(g["win"] for g in G if g["opp"] == o) / max(1, sum(1 for g in G if g["opp"] == o)):.2f}%, Prism deaths {sum(g["pdeaths"] for g in P if g["opp"] == o) / max(1, sum(1 for g in P if g["opp"] == o)):.3f}' for o in OPPS))
        if n != names[0]:
            keys = [k for k in R if k in ref]
            gain = sum(1 for k in keys if R[k]['win'] and not ref[k]['win']); loss = sum(1 for k in keys if not R[k]['win'] and ref[k]['win'])
            dd = sum(R[k]['pdeaths'] - ref[k]['pdeaths'] for k in keys if R[k]['prism'])
            z = (gain - loss) / math.sqrt(max(1, gain + loss))
            print(' ' * 15 + f'paired on {len(keys)}: wins +{gain} -{loss} (net {100 * (gain - loss) / max(1, len(keys)):+.2f} points, z {z:+.2f}); Prism deaths {dd:+d}; changed results {100 * (gain + loss) / max(1, len(keys)):.1f}%')


if __name__ == '__main__':
    main()
