"""An arm against its reference on the same games, split by the enemy's draft: python3 split.py REF ARM [REF2 ARM2 ...]
Pairs of names (quick.py's files) are pooled. Divers: Vendetta, Heart of Ruin, Vesper Vale, Cassi & Issac, Ren, Marcella
(a dash, or a ranged spell that reaches 4). Per split: games, the reference's win rate and Prism deaths, the arm's
change in each."""
import json, math, os, sys, collections
O = os.path.expanduser('~/tmp-offload/prismlife/out')
NAMES = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin']
DIVERS = {'Vendetta', 'Heart of Ruin', 'Vesper Vale', 'Ren'}


def load(name):
    rows = {}
    for opp in ('Flp4', 'Mt3q'):
        for line in open(f'{O}/{name}-{opp}.jsonl'):
            g = json.loads(line); f = g['file']; us = 0 if f.rsplit('.', 1)[0].endswith('-12') else 1
            ours = [c for c in g['champions'] if c['team'] == us]; pr = [c for c in ours if c['type'] == 6]
            ed = [NAMES[x] for x in g['draft'][1 - us]]
            rows[(name.split('.')[-1] if '.' in name else '', opp, f)] = dict(win=g['winner'] == us, prism=bool(pr), pd=sum(c['deaths'] for c in pr), opp=opp, divers=sum(1 for x in ed if x in DIVERS),
                                                                             eprism='Prism' in ed, picks=len(ed), ed=tuple(sorted(ed)))
    return rows


def main():
    a = sys.argv[1:]
    ref = {}; arm = {}
    for i in range(0, len(a), 2):
        ref.update(load(a[i])); arm.update(load(a[i + 1]))
    keys = [k for k in ref if k in arm and ref[k]['prism']]
    print(f'{len(keys)} paired Prism games')

    def tab(name, key):
        g = collections.defaultdict(list)
        for k in keys: g[key(ref[k])].append(k)
        print(name)
        for v in sorted(g, key=str):
            s = g[v]; n = len(s)
            w0 = sum(ref[k]['win'] for k in s) / n; w1 = sum(arm[k]['win'] for k in s) / n
            d0 = sum(ref[k]['pd'] for k in s) / n; d1 = sum(arm[k]['pd'] for k in s) / n
            gain = sum(1 for k in s if arm[k]['win'] and not ref[k]['win']); loss = sum(1 for k in s if ref[k]['win'] and not arm[k]['win'])
            print(f'  {str(v):22s} {n:5d} games  ref win {100 * w0:5.1f}%  Prism deaths {d0:.3f}   arm win {100 * (w1 - w0):+5.2f} (z {(gain - loss) / math.sqrt(max(1, gain + loss)):+.1f})  deaths {d1 - d0:+.3f}')
    tab('By opponent', lambda r: r['opp'])
    tab('By enemy divers (Vendetta, Heart of Ruin, Vesper Vale, Ren)', lambda r: min(r['divers'], 3))
    tab('By enemy Prism', lambda r: r['eprism'])
    tab('By picks', lambda r: r['picks'])
    tab("By the reference's Prism deaths in the game", lambda r: min(r['pd'], 2))


if __name__ == '__main__':
    main()
