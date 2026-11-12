"""Mechanism check: who holds our captured gold. Usage: mech.py TEAM_SUBSTR EXTRACT_DIR...
Per game, our team = the team whose name holds TEAM_SUBSTR. Base gold is the group's reward before bonuses,
split among holders by their share of the paid gold."""
import sys, json, gzip, glob, os, collections
sub = sys.argv[1]
S = collections.defaultdict(lambda: collections.Counter())
earned = collections.defaultdict(list); n = collections.Counter(); wins = collections.Counter()
for d in sys.argv[2:]:
    for mp in glob.glob(f'{d}/**/meta.json', recursive=True):
        g = os.path.dirname(mp); m = json.load(open(mp))
        ts = [i for i, t in enumerate(m['teams']) if sub in t['name']]
        if len(ts) != 1: continue
        t = ts[0]
        name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
        ours = {name[c] for c in name if team[c] == t}
        key = 'V+P' if {'Vesper Vale', 'Prism'} <= ours else ('V' if 'Vesper Vale' in ours else 'noV')
        mapf = os.path.normpath(os.path.join(g, m['mapFile'])) if not os.path.isabs(m['mapFile']) else m['mapFile']
        if not os.path.exists(mapf): mapf = os.path.normpath(os.path.join(d, m['mapFile']))
        gm = {q['id']: q for q in json.load(open(mapf))['groups']}
        n[key] += 1; wins[key] += m['result']['winner'] == t
        rd = json.load(gzip.open(f'{g}/rounds.json.gz', 'rt'))
        nR = len(rd['round'])
        earned[key].append([sum(c['earned'][min(r, nR) - 1] for c in rd['champions'] if team[c['id']] == t) for r in (100, 200)])
        for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
            e = json.loads(line)
            if e['k'] != 'capture' or e['team'] != t: continue
            base = gm[e['g']]['gold']
            if base <= 0: continue
            tot = sum(s[2] for s in e['shares']) or 1
            for s in e['shares']:
                for lim in (100, 200, 9999):
                    if e['r'] <= lim: S[(key, lim)][name[s[0]]] += base * s[2] / tot
for key in ('V+P', 'V', 'noV'):
    if not n[key]: continue
    out = [f'{key}: {n[key]} games, win {wins[key]/n[key]:.1%}, earned r100/r200 ' + '/'.join(f'{sum(e[i] for e in earned[key])/n[key]:.0f}' for i in (0, 1))]
    for lim in (100, 200, 9999):
        c = S[(key, lim)]; tot = sum(c.values()) or 1
        out.append(f'  by r{lim if lim < 9999 else "end"}: base gold/game {tot/n[key]:.0f}, Vesper {c["Vesper Vale"]/tot:.0%}, Prism {c["Prism"]/tot:.0%}')
    print('\n'.join(out))
