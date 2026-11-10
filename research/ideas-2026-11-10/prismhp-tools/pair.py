"""pair.py BASE.jsonl CAND.jsonl: paired Prism metrics (pdeaths output, local) on the same games."""
import sys, json
def load(f): return {g['mid']: g for g in map(json.loads, open(f))}
B, C = load(sys.argv[1]), load(sys.argv[2]); K = sorted(set(B) & set(C))
def m(g):
    d = [x for x in g['deaths'] if not x['camp']]
    return dict(win=g['win'], d600=any(x['r'] <= 600 for x in d), deaths=len(d), gems_lost=sum(x['gems'] for x in d), d_big=sum(x['gems'] >= 50 for x in d),
                trib=g.get('trib', 0), otrib=g.get('otrib', 0), submitted=g['submitted'], maxhp=g['maxhp_end'], spent=g['spent'])
print('paired Prism games', len(K))
for k in ['win', 'd600', 'deaths', 'd_big', 'gems_lost', 'submitted', 'trib', 'otrib', 'maxhp', 'spent']:
    b = sum(m(B[x])[k] for x in K) / len(K); c = sum(m(C[x])[k] for x in K) / len(K)
    print(f'{k:10} base {b:8.3f} cand {c:8.3f}  diff {c - b:+.3f}')
print('flipped games', sum(m(B[x])['win'] != m(C[x])['win'] for x in K))
