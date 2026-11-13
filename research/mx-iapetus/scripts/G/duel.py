# Line G: our Prism's deaths against the safety model's read (PZ trace, bot.cc) at its last turns.
# Usage: duel.py BATCH_DIR EXTRACT_DIR CAND_NAME [--dump N]
import json, gzip, sys, os, zipfile, collections
B, A, cand = sys.argv[1], sys.argv[2].rstrip('/') + '/', sys.argv[3]
dump = int(sys.argv[sys.argv.index('--dump') + 1]) if '--dump' in sys.argv else 0
idx = json.load(open(A + 'index.json'))['games']

def parse(l):
    p = l.split()
    d = dict(r=int(p[1]), h=int(p[2]), hp=float(p[3]), mhp=float(p[4]), gems=int(p[5]), x=int(p[6]), y=int(p[7]), dec=p[8],
             took=float(p[9]), bound=float(p[10]), doubled=float(p[11]), stuns=int(p[12]), camp=float(p[13]), tki=int(p[14]), en={})
    for q in p[15:]:
        f = q.split(':')
        h = int(f[0][1:])
        x, y = map(int, f[2].split(','))
        r0, r1 = map(int, f[6].split(','))
        d['en'][h] = dict(vis=int(f[1][0]), trk=int(f[1][1]), cred=int(f[1][2]), x=x, y=y, pr=int(f[3]), foc=float(f[4]), gems=int(f[5]),
                          r0=r0, r1=r1, blow=float(f[7]), st=int(f[8]))
    return d

games = 0
deaths = collections.Counter(); dgems = collections.Counter()
cls = collections.defaultdict(lambda: [0, 0])
samples = collections.defaultdict(list)
stale = []  # (believed focus, actual focus) of the killer at our last line, unseen or seen
calib = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])  # visible enemy Prism near: n, exceeded, sum pred, sum actual
work = 0; turns = 0; decs = collections.Counter(); trib = collections.Counter()
for r in idx:
    src = os.path.basename(r['source']); f = os.path.join(B, src)
    if not os.path.exists(f) or cand not in r['teams']: continue
    ct = r['teams'].index(cand); side = 'ab'[ct]
    try: out = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except KeyError: continue
    pz = collections.defaultdict(dict)
    for l in out:
        if l.startswith('PZ '):
            try: d = parse(l)
            except Exception: continue
            pz[d['h']][d['r']] = d
    d = r['dir']; games += 1
    R = json.load(gzip.open(A + d + '/rounds.json.gz')); ri = {x: i for i, x in enumerate(R['round'])}
    ch = {int(c['id']): c for c in R['champions']}
    m = json.load(open(A + d + '/meta.json')); name = {c['id']: c['name'] for c in m['champions']}
    ev = [json.loads(l) for l in gzip.open(A + d + '/events.jsonl.gz', 'rt')]
    # damage to each of our Prisms by (round, attacker)
    hit = collections.defaultdict(float)
    for e in ev:
        if e['k'] in ('attack', 'cast', 'other_dmg') and 'dmg' in e:
            for v, a in e['dmg']:
                if v in pz and a > 0 and 'a' in e: hit[(v, e['r'], e['a'])] += a
    for e in ev:
        if e.get('a') in pz:
            if e['k'] == 'tribute_start': trib['starts'] += 1; trib['start_gems'] += e.get('gems', 0)
            elif e['k'] == 'tribute_end': trib['ends'] += 1; trib['end_gems'] += e.get('gems', 0)
            elif e['k'] == 'tribute_cancel': trib['cancel_' + e.get('cause', '?')] += 1
    for h, lines in pz.items():
        turns += len(lines)
        for L in lines.values(): decs[L['dec']] += 1
        rs = sorted(lines)
        # calibration: a visible enemy whose blow at our end tile we read, against what it dealt by our next line
        for i, rr in enumerate(rs[:-1]):
            L = lines[rr]; nx = rs[i + 1]
            if nx != rr + 1: continue
            for eh, E in L['en'].items():
                if E['vis'] and name.get(eh) == 'Prism' and max(abs(E['x'] - L['x']), abs(E['y'] - L['y'])) <= 8:
                    act = hit[(h, rr, eh)] + hit[(h, nx, eh)]  # over-counts its turn before ours in rr; fine as a bound check
                    c = calib['seen enemy Prism <=8']; c[0] += 1; c[1] += act > E['blow'] + 1; c[2] += E['blow']; c[3] += act
    for e in ev:
        if e['k'] != 'death' or e.get('linked') is not None or e['v'] not in pz: continue
        v = e['v']; rd = e['r']; gems = e.get('gems', 0)
        deaths['all'] += 1; dgems['all'] += gems
        if gems >= 100: deaths['100+'] += 1; dgems['100+'] += gems
        lines = pz[v]
        prior = [x for x in lines if x <= rd]
        if not prior: continue
        L = lines[max(prior)]
        k = e.get('by')
        if k is None or k not in ch:
            key = ('camp', '')
        else:
            E = L['en'].get(k)
            kt = name.get(k, '?')
            i = ri.get(L['r'])
            afoc = ch[k]['foc'][i] if i is not None else -1
            agems = ch[k]['gems'][i] if i is not None else -1
            ax, ay = (ch[k]['x'][i], ch[k]['y'][i]) if i is not None else (-1, -1)
            dd = max(abs(ax - L['x']), abs(ay - L['y'])) if ax is not None and ay is not None else -1
            if E is None: state = 'dead/none'
            elif E['vis']: state = 'seen-lethal' if L['bound'] >= L['hp'] else 'seen-under'
            elif not E['trk']: state = 'untracked'
            elif E['cred']: state = 'unseen-cred'
            else: state = 'unseen-notcred'
            key = (kt, state)
            if E is not None: stale.append((kt, state, E['foc'], afoc, E['gems'], agems, E['pr'], L['r'], dd, gems))
            # earlier sightings within 10 rounds: was it seen at all?
            seen10 = any(lines[x]['en'].get(k, {}).get('vis') for x in prior if x >= rd - 10)
            samples[key].append((src, rd, gems, L['hp'], L['bound'], L['tki'], L['dec'], E and E['foc'], afoc, E and E['gems'], agems, dd, seen10,
                                 E and E['blow'], E and E['pr']))
        if gems >= 100: cls[key][0] += 1; cls[key][1] += gems

print('games', games, 'Prism turns', turns)
W = set('FPGXBT')  # farm, hold, siege, contest, bank walk, tribute channel
print(f"Prism living turns/game {turns/games:.0f}; working (F P G X B T) {100*sum(v for k, v in decs.items() if k in W)/max(1,turns):.1f}%; "
      + ' '.join(f"{k}:{100*v/max(1,turns):.1f}" for k, v in decs.most_common(12)))
print('Prism tributes/game:', {k: round(v / games, 2) for k, v in sorted(trib.items())})
print(f"Prism deaths {deaths['all']/games:.3f}/game, bag lost {dgems['all']/games:.1f}/game; 100+ bag deaths {deaths['100+']/games:.3f} ({dgems['100+']/games:.1f} gems)")
print('100+ bag deaths by (killer type, model state at our last turn):')
for k, v in sorted(cls.items(), key=lambda kv: -kv[1][1]):
    s = samples[k]
    seen10 = sum(1 for x in s if x[12]) if s else 0
    print(f'  {k[0]:14} {k[1]:15} n={v[0]:4} gems/game {v[1]/games:5.1f}  seen-in-last-10 {seen10}/{len(s)}')
print('calibration:', {k: (v[0], f'exceeded {100*v[1]/max(1,v[0]):.1f}%', f'pred {v[2]/max(1,v[0]):.0f}', f'actual {v[3]/max(1,v[0]):.0f}') for k, v in calib.items()})
# killer Focus belief vs actual (enemy Prism killers of 100+ bags)
pk = [x for x in stale if x[0] == 'Prism' and x[9] >= 100]
if pk:
    import statistics as st
    for state in sorted(set(x[1] for x in pk)):
        q = [x for x in pk if x[1] == state]
        ratio = [x[2] / x[3] for x in q if x[3] > 0]
        age = [x[7] - x[6] for x in q]
        print(f'  Prism killer {state:15} n={len(q)} belief/actual Focus median {st.median(ratio):.2f} (p25 {sorted(ratio)[len(ratio)//4]:.2f}); '
              f'sighting age median {st.median(age)}; actual Focus median {st.median([x[3] for x in q]):.0f}; dist median {st.median([x[8] for x in q])}')
if dump:
    for k in sorted(samples, key=lambda k: -cls[k][1])[:6]:
        print(k)
        for x in samples[k][:dump]: print('   ', x)
