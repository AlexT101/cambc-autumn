"""Timelines of uncontested Elk/Golem crew clears (2+ same-team strikers, >=10% of the damage each), from an extract
dir whose meta 'source' replay holds debug stdout. Per round from 15 before the wake to the clear: each team member's
distance to the group's nearest live striker camp, hp, damage dealt to the group, camp damage taken, and that
champion's CREW/MONO trace lines that round.
Usage: crewtrace.py EXTRACT_DIR [N_CLEARS] [MIN_LAG]"""
import json, gzip, glob, os, sys, collections, zipfile, re
ROOT = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 5; MINLAG = int(sys.argv[3]) if len(sys.argv) > 3 else 4
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
shown = 0
for d in sorted(os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')):
    meta = json.load(open(d + '/meta.json'))
    src = os.path.join(REPO, meta['source'])
    if os.environ.get('SRC') and os.environ['SRC'] not in src: continue
    if not os.path.exists(src): continue
    z = zipfile.ZipFile(src)
    out = {0: z.read('team-a.stdout').decode(errors='replace').splitlines(), 1: z.read('team-b.stdout').decode(errors='replace').splitlines()}
    if not out[0] and not out[1]: continue
    mp = json.load(open(os.path.join(d, meta['mapFile']))); camps = {c['id']: c for c in mp['camps']}
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    groups = {G['id']: G for G in mp['groups']}; cg = {c['id']: c['group'] for c in mp['camps']}
    big = {g for g, G in groups.items() if any(camps[c]['type'] in ('Elk', 'Golem') for c in G['camps'])}
    R = json.load(gzip.open(d + '/rounds.json.gz')); r_first = R['round'][0]
    ch = {int(c['id']): c for c in R['champions']}
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    open_ = {}; clears = []
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for cid, amt in e['cdmg']:
                g = cg.get(cid)
                if g in big:
                    o = open_.setdefault(g, {'r0': e['r'], 'dmg': collections.Counter(), 'first': {}})
                    o['dmg'][e['a']] += amt; o['first'].setdefault(e['a'], e['r'])
        elif k == 'group_clear' and e['g'] in open_:
            o = open_.pop(e['g']); tot = sum(o['dmg'].values()); t = team[max(o['dmg'], key=o['dmg'].get)]
            if any(team[a] != t for a in o['dmg']): continue
            sts = [a for a, v in o['dmg'].items() if v >= 0.1 * tot]
            if len(sts) < 2: continue
            fs = sorted(o['first'][a] for a in sts)
            if fs[1] - fs[0] < MINLAG: continue
            clears.append((e['g'], o['r0'], e['r'], t, sts))
    for g, r0, r1, t, sts in clears:
        if shown >= N: sys.exit()
        shown += 1
        G = groups[g]
        pos = [tuple(camps[c]['pos'] if 'pos' in camps[c] else (camps[c]['x'], camps[c]['y'])) for c in G['camps']]
        types = [camps[c]['type'] for c in G['camps']]
        print('=' * 100); print(meta['source'], 'team', t, 'g%d' % g, types, 'wake', r0, 'clear', r1, 'strikers', [(a, name[a]) for a in sts])
        mem = [a for a in ch if team[a] == t]
        lines = collections.defaultdict(list)
        for l in out[t]:
            m = re.match(r'\s*(CREW \w+|MONO \w+)\s+(\d+)\s+(\d+)\s(.*)', l)
            if m and r0 - 15 <= int(m.group(2)) <= r1: lines[(int(m.group(2)), int(m.group(3)))].append(m.group(1) + ' ' + m.group(4)[:110])
        dealt = collections.Counter(); taken = collections.Counter()
        for e in ev:
            if not (r0 - 15 <= e['r'] <= r1): continue
            if e['k'] in ('attack', 'cast') and e.get('cdmg'):
                for cid, amt in e['cdmg']:
                    if cg.get(cid) == g: dealt[(e['r'], e['a'])] += amt
            if e['k'] == 'camp_attack' and e.get('g') == g: taken[(e['r'], e['tgt'])] += e['dmg']
        for r in range(r0 - 15, r1 + 1):
            i = r - r_first
            cells = []
            for a in mem:
                c = ch[a]
                if i >= len(c['x']): continue
                x, y = c['x'][i], c['y'][i]
                if x is None: cells.append('%s dead' % name[a][:4]); continue
                dd = min(max(abs(x - p[0]), abs(y - p[1])) for p, ty in zip(pos, types) if ty in ('Elk', 'Golem', 'Wolf'))
                cells.append('%s d%-2d hp%-4d %s%s' % (name[a][:4], dd, c['hp'][i], ('h%-4d' % dealt[(r, a)]) if dealt[(r, a)] else '     ',
                                                    ('t%-4d' % taken[(r, a)]) if taken[(r, a)] else '     '))
            print('r%-4d ' % r + ' | '.join(cells))
            for a in mem:
                for l in lines.get((r, a), []): print('        %d %s: %s' % (a, name[a][:5], l))
