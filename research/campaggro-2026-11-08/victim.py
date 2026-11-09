"""Per fire (CAGG lines): victim's health fraction and channel at the wake, whether it died within 8 rounds, and
the woken group's damage to each team. Usage: python3 victim.py ANA_DIR..."""
import json, gzip, re, sys, zipfile, collections
rows = []
for ana in sys.argv[1:]:
    for g in json.load(open(ana + '/index.json'))['games']:
        d = ana + '/' + g['dir']; meta = json.load(open(d + '/meta.json')); team = {c['id']: c['team'] for c in meta['champions']}
        try: Z = zipfile.ZipFile(g['source'])
        except OSError: continue
        fires = []
        for t, nm in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
            for l in Z.read(nm).decode(errors='ignore').splitlines():
                m = re.match(r'CAGG (\d+) (\d+) g\d+ v\d+ vic (\d+)', l)
                if m: fires.append((t, int(m[1]), int(m[2]), int(m[3])))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
        R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: i for i, r in enumerate(R['round'])}; chs = {c['id']: c for c in R['champions']}
        for T, r, h, v in fires:
            w = [e for e in ev if e['k'] == 'group_wake' and e['r'] == r and e.get('by') == h]
            if not w or v not in chs: continue
            gid = w[0]['g']; i = ri[r - 1]; c = chs[v]
            en = sum(e['dmg'] for e in ev if r <= e['r'] <= r + 8 and e['k'] == 'camp_attack' and e['g'] == gid and team[e['tgt']] != T)
            ow = sum(e['dmg'] for e in ev if r <= e['r'] <= r + 8 and e['k'] == 'camp_attack' and e['g'] == gid and team[e['tgt']] == T)
            died = any(e['k'] == 'death' and e['v'] == v and r <= e['r'] <= r + 8 for e in ev)
            ad = sum(1 for e in ev if e['k'] == 'death' and 'linked' not in e and team[e['v']] == T and r <= e['r'] <= r + 8)
            rows.append(dict(hp=c['hp'][i] / c['maxHp'][i], hpabs=c['hp'][i], chan=c['chan'][i], gems=c['gems'][i], died=died, en=en, ow=ow, ad=ad))
def show(name, f):
    s = [x for x in rows if f(x)]
    if not s: return
    print(f"{name:>14}: n={len(s):3d} victim died {sum(x['died'] for x in s)/len(s):.2f}  enemy dmg {sum(x['en'] for x in s)/len(s):5.0f}  ours {sum(x['ow'] for x in s)/len(s):5.0f}  ally deaths {sum(x['ad'] for x in s)/len(s):.2f}")
show('all', lambda x: True)
for lo, hi in ((0, .35), (.35, .6), (.6, .85), (.85, 1.01)): show(f'hp {lo}-{hi}', lambda x, lo=lo, hi=hi: lo <= x['hp'] < hi)
for a in (0, 300, 600): show(f'hpabs<={a+300}', lambda x, a=a: x['hpabs'] <= a + 300)
for ch in (0, 1, 2): show(f'chan {ch}', lambda x, ch=ch: x['chan'] == ch)
show('gems>=10', lambda x: x['gems'] >= 10)
