"""Fight mechanism, local games against a body: per arm, kills and deaths a game (enemy deaths split by whether the
victim was at 40%+ health with a bag under 11 ten rounds before: Mite's standing state), gems taken and lost, and the
paired win against BASE. Usage: fightmech.py EXT_ROOT BASE ARM..."""
import sys, json, gzip, glob, os, re, collections
from multiprocessing import Pool
def one(args):
    mp, bot = args
    g = os.path.dirname(mp); m = json.load(open(mp))
    src = m['source']; k = re.search(r'-k(\d)-ladder', src).group(1); stem = os.path.basename(src).split('-', 1)[1]
    t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
    team = {c['id']: c['team'] for c in m['champions']}
    C = {c['id']: c for c in json.load(gzip.open(f'{g}/rounds.json.gz', 'rt'))['champions']}
    s = collections.Counter()
    for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
        e = json.loads(line)
        if e['k'] != 'death' or e['v'] not in team: continue
        if team[e['v']] == t:
            s['our_deaths'] += 1; s['gems_lost'] += e.get('gems', 0)
        else:
            s['kills'] += 1; s['gems_taken'] += e.get('gems', 0)
            i = max(0, e['r'] - 11); c = C[e['v']]
            if c['alive'][i] and c['hp'][i] >= 0.4 * c['maxHp'][i] and c['gems'][i] < 11: s['kills_standing'] += 1
    return (k, stem), m['result']['winner'] == t, s
def load(root, bot):
    with Pool(8) as P:
        return {key: (w, s) for key, w, s in P.map(one, [(mp, bot) for mp in glob.glob(f'{root}/{bot}/*/meta.json')], chunksize=8)}
if __name__ == '__main__':
    root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
    B = load(root, base)
    for arm in [base] + arms:
        A = B if arm == base else load(root, arm)
        ks = [k for k in A if k in B]; n = len(ks)
        S = collections.Counter()
        for k in ks: S.update(A[k][1])
        wa = sum(A[k][0] for k in ks); wb = sum(B[k][0] for k in ks); fl = sum(A[k][0] != B[k][0] for k in ks)
        print(f'{arm}: {n} games; win {wa/n:.1%} ({(wa-wb)/n*100:+.1f}, flips {fl}); kills {S["kills"]/n:.2f} (standing {S["kills_standing"]/n:.2f}), '
              f'deaths {S["our_deaths"]/n:.2f}; gems taken {S["gems_taken"]/n:.0f}, lost {S["gems_lost"]/n:.0f}')
