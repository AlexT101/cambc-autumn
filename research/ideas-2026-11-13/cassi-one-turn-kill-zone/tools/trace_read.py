"""Cassi's last turns before her late deaths to Vesper, from czk-trace's debug stdout: python3 trace_read.py EXT [BODY]"""
import gzip, json, os, sys, zipfile, collections
ext = sys.argv[1]; BODY = sys.argv[2] if len(sys.argv) > 2 else 'Cassi'
cheb = lambda a, b: 99 if None in a or None in b else max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(ext + '/index.json'))['games']
ROOT = '/home/ubuntu/cambc-autumn/'
dec = collections.defaultdict(collections.Counter); stand = collections.defaultdict(collections.Counter); why = collections.defaultdict(collections.Counter)
n = 0; examples = []
for g in idx:
    us = 0 if g['source'].endswith('-12.repl26a') else 1
    d = ext + '/' + g['dir']
    m = json.load(open(d + '/meta.json'))
    ch = {c['id']: c for c in m['champions']}
    ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}
    fish = {c['name']: c['id'] for c in m['champions'] if c['team'] != us}
    if 'Cassi' not in ours or 'Vesper Vale' not in fish: continue
    vid = fish['Vesper Vale']; bid = ours[BODY]
    evs = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    kills = [e for e in evs if e['k'] == 'death' and e['v'] == bid and 'linked' not in e and e['r'] >= 300 and e.get('by') == vid]
    if not kills: continue
    src = g['source'] if os.path.isabs(g['source']) else ROOT + g['source']
    if not os.path.exists(src): src = os.path.join(ROOT, os.path.relpath(g['source']))
    out = zipfile.ZipFile(src).read('team-a.stdout' if us == 0 else 'team-b.stdout').decode(errors='replace').splitlines()
    D = {}; W = {}; S = {}
    for l in out:
        v = l.split()
        if not v: continue
        try:
            if v[0] == 'D' and int(v[2]) == bid: D[int(v[1])] = v[3]
            elif v[0] == 'CZW' and int(v[2]) == bid: W[int(v[1])] = v[3]
            elif v[0] == 'CZS' and int(v[2]) == bid: S[int(v[1])] = (int(v[3], 16), int(v[4], 16), int(v[5], 16), int(v[6]), int(v[7]), v[8], int(v[9]))
        except (ValueError, IndexError): pass
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); ri = {v: i for i, v in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    vpos = lambda r: (C[vid]['x'][ri[r]], C[vid]['y'][ri[r]])
    bpos = lambda r: (C[bid]['x'][ri[r]], C[bid]['y'][ri[r]])
    for e in kills:
        n += 1; r0 = e['r']
        # T0 = the last round of ours before the death (its own turn if it acted before dying that round)
        turns = [r for r in range(r0, r0 - 9, -1) if r in D]
        line = []
        for k, r in enumerate(turns[:6]):
            vesv = vid in (C[bid]['sees'][ri[r] - 1] or []) if ri.get(r, 0) > 0 else False
            sid = vid - (6 if vid >= 6 else 0)
            s = S.get(r)
            vin = None
            if s:
                # Vesper's bit in the stand: hit / walking / pending use enemy index (our team's view: index among enemies)
                pass
            dec[k][D[r]] += 1
            why[k][W.get(r, '-')] += 1
            stand[k][('none' if s is None else {-1: 'nofight', 0: 'kept', 1: 'lost', 2: 'falls'}[s[6]]) + ('' if s is None else f' pur{s[3]} own{s[4]}')] += 1
            dd = cheb(bpos(r - 1), vpos(r - 1)) if ri.get(r, 0) > 1 else -1
            line.append(f'r{r} d{dd} {D[r]}{W.get(r, "")} ' + ('-' if s is None else f'h{s[0]:x} w{s[1]:x} p{s[2]:x} pur{s[3]} own{s[4]} k{s[5]} res{s[6]}'))
        examples.append((g['dir'], r0, ' | '.join(line)))
print(f'{BODY} late deaths to Vesper with traces: {n}')
for k in range(6):
    print(f'T{k}: decision {dict(dec[k].most_common())}; want_home clause {dict(why[k].most_common())}')
    print(f'     stand {dict(stand[k].most_common(8))}')
for x in examples[:25]: print(x)
