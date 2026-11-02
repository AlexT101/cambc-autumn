# Verdict-ok engaged stand sims: features of the ones where our side died first vs theirs, ladder and self-play (r<=260).
import sys, os, json
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF
import race as RC
K = 5


def feats(x):
    selff = next(f for f in x['us'] if f['h'] == x['c'])
    took = lambda f: sum(f['took'][:K])
    tot_them_dmg = sum(sum(f['a_any'][:K]) for f in x['them']) + sum(sum(e['dmg'][:K]) for e in x['extra'])
    w = min(x['them'], key=lambda f: f['hp'] + f['sh'])
    return dict(
        margin=x['margin'], self_hp=x['hp'] / x['mh'], n_us=len(x['us']), n_them=len(x['them']),
        extra_joined=len(x['extra']) > 0, near_n=len(x.get('near', [])), near_joined=sum(e['joined'] for e in x.get('near', [])),
        ci=any(f['typ'] in ('cassi', 'issac') for f in x['them']), weakest_cassi=w['typ'] == 'cassi',
        weakest_hit=took(w) > 0,
        self_share_of_their_dmg=took(selff) / max(1, tot_them_dmg), self_is_target=x['sim_target'] == x['c'],
        our_real=sum(sum(f['a_any'][:K]) for f in x['us']) / max(1, sum(f['pd'] * max(0, K - f['arr']) for f in x['us'])),
        their_real=sum(sum(f['a_any'][:K]) for f in x['them']) / max(1, sum(f['pd'] * max(0, K - f['arr']) for f in x['them'])),
        self_hits=sum(1 for k in range(K) if selff['a_hits'][k] > 0) / K,
        stuns=x['stuns_on_us'], chase=x['kind'] == 'chase', first_t=x['first'] == 't')


if __name__ == '__main__':
    for src in ('selfplay', 'ladder'):
        rs = [x for x in CF.load(src) if not x['lost']]
        grp = defaultdict(list)
        for x in rs:
            o = RC.first(x)
            if o in ('ours', 'theirs'): grp[o].append(feats(x))
        print('\n## %s verdict ok: ours first n=%d, theirs first n=%d' % (src, len(grp['ours']), len(grp['theirs'])))
        for k in grp['ours'][0]:
            a = sum(float(f[k]) for f in grp['ours']) / len(grp['ours']); b = sum(float(f[k]) for f in grp['theirs']) / len(grp['theirs'])
            print('  %-24s ours-first %7.3f   theirs-first %7.3f' % (k, a, b))
