# Fidelity table: cmp.py NAME=ROWS.pkl[:OPP] ...   (ROWS from eng.py; OPP filters 'Inte' or 'Mite', default Inte)
import sys, pickle, json, gzip, collections, random
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from summ import mean
def alpha(games, maxr=300):
    s = collections.Counter()
    for d0, us in games:
        meta = json.load(open(d0 + '/meta.json')); team = {c['id']: c['team'] for c in meta['champions']}
        per = collections.defaultdict(lambda: collections.defaultdict(set))
        for l in gzip.open(d0 + '/events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e['r'] > maxr: break
            if e['k'] in ('attack', 'cast'):
                for t, dm in e.get('dmg', []): per[e['r']][t].add(e['a'])
        for r, d in per.items():
            for t, att in d.items():
                side = 'them' if team[t] == us else 'us'
                if len(att) >= 3: s[side + '3'] += 1
                if len(att) >= 4: s[side + '4'] += 1
    return s
def ci(v):
    v = [x for x in v if x is not None]
    if len(v) < 2: return float('nan')
    m = sum(v) / len(v); return 1.96 * (sum((x - m) ** 2 for x in v) / (len(v) - 1) / len(v)) ** 0.5
cols = []
for a in sys.argv[1:]:
    name, path = a.split('=', 1); opp = 'Inte'
    if ':' in path: path, opp = path.split(':')
    d = pickle.load(open(path, 'rb')); rows = [r for r in d['rows'] if r['opp'] == opp]
    gp = path.replace('rows-', 'games-') if 'rows-' in path else None
    G = None
    if gp:
        try: G = [g for g in pickle.load(open(gp, 'rb')) if g['opp'] == opp]
        except FileNotFoundError: G = None
    if G is None:
        src = '/home/ubuntu/tmp-offload/overruns/an/' + ('deaths.pkl' if 'live' in path else 'deaths_local.pkl')
        seen = set(); G = []
        for g in pickle.load(open(src, 'rb')):
            if g['opp'] == opp and g['match'] not in seen: seen.add(g['match']); G.append(g)
    cols.append((name, rows, G))
def w4(r): return sum(1 for b in r['B'] if b['d'][0] is not None and b['d'][0] <= 4)
out = collections.OrderedDict()
def put(k, vals): out.setdefault(k, []).append(vals)
for name, rows, G in cols:
    ng = len(G); a = alpha([(g['dir'], g['us']) for g in G])
    put('games', '%d' % ng); put('ocean win %', '%.1f' % (100 * mean([g['win'] for g in G])))
    put('ocean deaths / their deaths by r250', '%.2f / %.2f' % (mean([sum(1 for d in g['D'] if d['ours'] and d['r'] <= 250 and d['typ'] != 'Issac') for g in G]), mean([sum(1 for d in g['D'] if not d['ours'] and d['r'] <= 250 and d['typ'] != 'Issac') for g in G])))
    T1 = [r for r in rows if not r['by_us'] and r['nA'] > r['nD']]
    put('T1 they start with numbers: a game', '%.2f' % (len(T1) / ng)); put('  n', '%d' % len(T1))
    put('  net kills for them, each', '%+.2f ±%.2f' % (mean([r['kA'] - r['kD'] for r in T1]), ci([r['kA'] - r['kD'] for r in T1])))
    put('  first target died', '%.0f%% ±%.0f' % (100 * mean([r['died'] for r in T1]), 100 * ci([float(r['died']) for r in T1])))
    put('  their attackers (any target)', '%.2f' % mean([r['att_total'] for r in T1]))
    put('  dmg on first target', '%.0f' % mean([r['dmg_on_t0'] for r in T1]))
    put('  their bodies within 4 of it, r0-1', '%.2f' % mean([w4(r) for r in T1]))
    put('  share with 2+ within 4', '%.0f%%' % (100 * mean([w4(r) >= 2 for r in T1])))
    put('  their bodies hitting a camp r0..r0+2', '%.0f%%' % (100 * mean([any('C' in x for x in b['post'][:3]) for r in T1 for b in r['B']])))
    put('  on our half', '%.0f%%' % (100 * mean([r['home_D'] for r in T1])))
    T2 = [r for r in rows if r['by_us'] and r['nA'] < r['nD']]
    put('T2 we start outnumbered: a game', '%.2f' % (len(T2) / ng)); put('  n ', '%d' % len(T2))
    put('  net kills for us, each', '%+.2f ±%.2f' % (mean([r['kA'] - r['kD'] for r in T2]), ci([r['kA'] - r['kD'] for r in T2])))
    put('  our kills / theirs, each', '%.2f / %.2f' % (mean([r['kA'] for r in T2]), mean([r['kD'] for r in T2])))
    put('  first target died ', '%.0f%% ±%.0f' % (100 * mean([r['died'] for r in T2]), 100 * ci([float(r['died']) for r in T2])))
    put('  our damage / theirs', '%.0f / %.0f' % (mean([r['dmg_A'] for r in T2]), mean([r['dmg_D'] for r in T2])))
    put('  duration, rounds', '%.1f' % mean([r['r1'] - r['r0'] + 1 for r in T2]))
    put('  on their half', '%.0f%%' % (100 * mean([r['home_D'] for r in T2])))
    T3 = [r for r in rows if r['by_us'] and r['nA'] > r['nD']]
    put('T3 we start with numbers: a game', '%.2f' % (len(T3) / ng))
    put('  net kills for us, each ', '%+.2f ±%.2f' % (mean([r['kA'] - r['kD'] for r in T3]), ci([r['kA'] - r['kD'] for r in T3])))
    allr = [r for r in rows]
    put('all engagements a game', '%.2f' % (len(allr) / ng))
    put('net kills for us a game, all engagements', '%+.2f' % (sum((r['kA'] - r['kD']) * (1 if r['by_us'] else -1) for r in allr) / ng))
    put('rounds 4+ of them on one of ours, a game', '%.2f' % (a['them4'] / ng)); put('rounds 3+ of them on one of ours', '%.2f' % (a['them3'] / ng))
    put('rounds 4+ of ours on one of them', '%.2f' % (a['us4'] / ng))
print('%-44s' % '' + ''.join('%18s' % c[0] for c in cols))
for k, v in out.items(): print('%-44s' % k + ''.join('%18s' % x for x in v))
