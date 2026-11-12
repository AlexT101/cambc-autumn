"""Vesper-avoidance mechanism, local games against a body: per arm, our deaths a game (all, to their Vesper, to her
after round 400), her deaths, our kills, gems lost / collected / banked, and the paired win against BASE.
Usage: vmech.py EXT_ROOT BASE ARM..."""
import sys, json, gzip, glob, os, re, collections
from multiprocessing import Pool
def one(args):
    mp, bot = args
    g = os.path.dirname(mp); m = json.load(open(mp))
    src = m['source']; k = re.search(r'-k(\d)-ladder', src).group(1); stem = os.path.basename(src).split('-', 1)[1]
    t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
    team = {c['id']: c['team'] for c in m['champions']}
    her = [c['id'] for c in m['champions'] if c['team'] != t and c['name'] == 'Vesper Vale']
    s = collections.Counter({'her_games': len(her) > 0})
    for c in m['champions']:
        if c['team'] == t: s['collected'] += c['stats']['collectedGems']; s['banked'] += c['stats']['submittedGems']
    for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
        e = json.loads(line)
        if e['k'] != 'death' or e['v'] not in team: continue
        if team[e['v']] == t:
            s['deaths'] += 1; s['gems_lost'] += e.get('gems', 0)
            if e.get('by') in her: s['by_her'] += 1; s['by_her_late'] += e['r'] > 400
        else:
            s['kills'] += 1; s['her_deaths'] += e['v'] in her
    return (k, stem), m['result']['winner'] == t, s
def load(root, bot):
    with Pool(8) as P:
        return {key: (w, s) for key, w, s in P.map(one, [(mp, bot) for mp in glob.glob(f'{root}/{bot}/*/meta.json')], chunksize=8)}
if __name__ == '__main__':
    root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
    B = load(root, base)
    for arm in [base] + arms:
        A = B if arm == base else load(root, arm)
        for lab, sel in (('all', lambda k: True), ('she plays', lambda k: B[k][1]['her_games'])):
            ks = [k for k in A if k in B and sel(k)]; n = len(ks)
            S = collections.Counter()
            for k in ks: S.update(A[k][1])
            wa = sum(A[k][0] for k in ks); wb = sum(B[k][0] for k in ks); fl = sum(A[k][0] != B[k][0] for k in ks)
            print(f'{arm} [{lab}]: {n} games; win {wa/n:.1%} ({(wa-wb)/n*100:+.1f}, flips {fl}); deaths {S["deaths"]/n:.2f}, to her '
                  f'{S["by_her"]/n:.2f} (after r400 {S["by_her_late"]/n:.2f}); her deaths {S["her_deaths"]/n:.2f}; kills {S["kills"]/n:.2f}; '
                  f'gems lost {S["gems_lost"]/n:.0f}, collected {S["collected"]/n:.0f}, banked {S["banked"]/n:.0f}')
