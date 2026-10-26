"""Death rates with the prototype's pockets (per team), within-map stratified, plus coverage of brute pockets."""
import gzip, json, glob, os, sys, collections, pickle
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto import find_cuts, rebuild

ANA = sys.argv[1]
DASH_TYPES = {'Vesper Vale', 'Vendetta', 'Ren', 'Heart of Ruin', 'Issac'}


def one_map(path):
    mp = json.load(open(path))
    out = {}
    for team in (0, 1):
        for dash in (False, True):
            reps, cuts, ctx = find_cuts(mp, team=team, dash=dash)
            pocket, block = rebuild(*ctx, cuts)
            out[(team, dash)] = (pocket, len(cuts))
    return os.path.basename(path)[:-5], out


if __name__ == '__main__':
    cache = os.path.join(ANA, 'proto.pkl')
    if os.path.exists(cache):
        PP = pickle.load(open(cache, 'rb'))
    else:
        with Pool(6) as p:
            PP = dict(p.map(one_map, glob.glob(os.path.join(ANA, 'maps', '*.json'))))
        pickle.dump(PP, open(cache, 'wb'))
    PK = pickle.load(open(os.path.join(ANA, 'pockets.pkl'), 'rb'))
    exp = act = 0.0
    tot_in = tot_out = d_in = d_out = 0
    cov_n = cov_d = 0
    for meta_path in sorted(glob.glob(os.path.join(ANA, '*', 'meta.json'))):
        d = os.path.dirname(meta_path)
        meta = json.load(open(meta_path))
        h = meta['map']['hash']
        pp = PP[h]
        brute = set().union(*[s for s, _ in PK[h]]) if PK[h] else set()
        p0 = pp[(0, False)][0]
        cov_n += len(brute & (p0 | pp[(1, False)][0]))
        cov_d += len(brute)
        if not any(pp[k][0] for k in pp):
            continue
        rounds = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        names = {c['id']: c['name'] for c in meta['champions']}
        champs = rounds['champions']
        team_of = {c['id']: c['team'] for c in champs}
        def pocket_of(cid):
            return pp[(team_of[cid], names[cid] in DASH_TYPES)][0]
        ri = ro = 0
        for c in champs:
            P = pocket_of(c['id'])
            for x, y, a in zip(c['x'], c['y'], c['alive']):
                if a and x is not None:
                    if (x, y) in P:
                        ri += 1
                    else:
                        ro += 1
        di = do = 0
        for line in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
            e = json.loads(line)
            if e['k'] != 'death' or e.get('linked') is not None or 'camp' in e:
                continue
            if tuple(e['at']) in pocket_of(e['v']):
                di += 1
            else:
                do += 1
        tot_in += ri; tot_out += ro; d_in += di; d_out += do
        if ro:
            exp += ri * do / ro
            act += di
    print('brute pocket tiles covered by proto (either team): %.1f%%' % (100 * cov_n / max(1, cov_d)))
    print('champion-rounds in pocket %d, out %d; deaths in %d, out %d' % (tot_in, tot_out, d_in, d_out))
    print('rate in %.3f/1k out %.3f/1k; stratified actual %d vs expected %.1f (x%.2f)' % (
        1000 * d_in / max(1, tot_in), 1000 * d_out / max(1, tot_out), act, exp, act / max(1e-9, exp)))
