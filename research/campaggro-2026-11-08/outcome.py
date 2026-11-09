"""Per fire of camp_aggro (CAGG lines, debug builds): the woken group's camp attacks on each team over the next
HORIZON rounds, camp kills, and enemy deaths. Usage: python3 outcome.py ANA_DIR [HORIZON]"""
import json, gzip, os, sys, zipfile, re, collections
ana = sys.argv[1]; H = int(sys.argv[2]) if len(sys.argv) > 2 else 8
tot = collections.Counter(); rows = []
for g in json.load(open(ana + '/index.json'))['games']:
    d = ana + '/' + g['dir']; meta = json.load(open(d + '/meta.json'))
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    Z = zipfile.ZipFile(g['source']); fires = []
    for t, nm in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        for l in Z.read(nm).decode(errors='ignore').splitlines():
            m = re.match(r'CAGG (\d+) (\d+) g(\d+) v(\d+)(.*)', l)
            if m:
                kv = m[5].split(); x = dict(zip(kv[::2], kv[1::2]))
                fires.append((t, int(m[1]), int(m[2]), int(m[4]), x))
    if not fires: continue
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    for T, r, h, v, x in fires:
        w = [e for e in ev if e['k'] == 'group_wake' and e['r'] == r and e.get('by') == h]
        if not w: rows.append((os.path.basename(g['source']), r, name.get(h), 'no wake event')); tot['nowake'] += 1; continue
        gid = w[0]['g']
        en = ow = 0; kills = []
        for e in ev:
            if not (r <= e['r'] <= r + H): continue
            if e['k'] == 'camp_attack' and e['g'] == gid:
                if team[e['tgt']] == T: ow += e['dmg']
                else: en += e['dmg']
            if e['k'] == 'death' and 'linked' not in e:
                who = 'enemy' if team[e['v']] != T else 'ally'
                by = 'camp' if 'camp' in e else ('us' if e.get('by') in team and team[e['by']] == T else 'them')
                kills.append(f"{who}:{name[e['v']]}/{by}@{e['r']}")
        side = 'nohome' if not x else ('home' if int(x['home']) <= int(x['away']) else 'away')
        ed = sum(k.startswith('enemy') for k in kills); ad = sum(k.startswith('ally') for k in kills)
        for key in ('all', side, 'theirs' + x.get('theirs', '?')):
            tot[key, 'fires'] += 1; tot[key, 'en_dmg'] += en; tot[key, 'our_dmg'] += ow; tot[key, 'enemy_deaths'] += ed; tot[key, 'ally_deaths'] += ad
        rows.append((os.path.basename(g['source']), r, name.get(h), f'v{v} {side} theirs {x.get("theirs")} enemy_dmg {en:.0f} our_dmg {ow:.0f}', ' '.join(kills)))
for r in rows: print(*r)
keys = sorted({k[0] for k in tot if isinstance(k, tuple)})
for k in keys: print(k, {f: round(tot[k, f]) for f in ('fires', 'en_dmg', 'our_dmg', 'enemy_deaths', 'ally_deaths')})
if tot['nowake']: print('nowake', tot['nowake'])
