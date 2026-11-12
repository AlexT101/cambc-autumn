"""One stretch of a game around our Prism, round by round: python3 show.py EXTROOT/TAG/DIR ROUND [BEFORE [AFTER]]

Each round: the Prism at the round's start (tile, health, bag, cooldowns, channel), every champion within 10 of it
(E enemy, A ally; type, distance, health share, cooldowns), then the round's events that involve the Prism or a
champion near it, in order. With stdout traces in the replay (a debug build), the Prism's D line (its decision).
"""
import gzip, json, os, re, sys, zipfile

ROOT = '/home/ubuntu/cambc-autumn'
ABB = {'Vesper Vale': 'Vesp', 'Heart of Ruin': 'HoR', 'Marcella': 'Marc', 'Vendetta': 'Vend', 'Prism': 'Prsm', 'Willow': 'Will', 'Cassi': 'Cass', 'Issac': 'Issc',
       'Stellar': 'Stel', 'Tavi': 'Tavi', 'Ren': 'Ren', 'Ryth': 'Ryth', 'Varg': 'Varg'}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    d = sys.argv[1]; r = int(sys.argv[2]); before = int(sys.argv[3]) if len(sys.argv) > 3 else 10; after = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    meta = json.load(open(os.path.join(d, 'meta.json')))
    R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    names = [t['name'] for t in meta['teams']]
    us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    p = next(c for c in ch if typ[c] == 'Prism' and team[c] == us)
    P = ch[p]
    mp = json.load(open(os.path.join(d, meta['mapFile']))); sp = mp['spawn'][us]
    dl = {}
    try:
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
        for line in out.splitlines():
            m = re.match(r'\s*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)', line)
            if m: dl.setdefault(int(m.group(1)), {})[int(m.group(2))] = m.group(3)
    except Exception:
        pass
    print(f"{meta['source']}  map {meta['map']['name']} {meta['map']['width']}x{meta['map']['height']}  us team {'AB'[us]} spawn {sp}  result winner {'AB'[meta['result']['winner']]} {meta['result']['gems']}")
    nm = lambda c: ('A' if team[c] == us else 'E') + ABB.get(typ[c], typ[c]) + str(c)
    for q in range(max(1, r - before), min(rounds[-1], r + after) + 1):
        i = idx.get(q); j = idx.get(q - 1, i)
        if i is None: continue
        if not P['alive'][j]:
            print(f'r{q}: Prism dead'); continue
        me = (P['x'][j], P['y'][j])
        s = f"r{q} P@{me} hp {P['hp'][j]:.0f}/{P['maxHp'][j]:.0f} ({P['hp'][j] / max(1, P['maxHp'][j]):.2f}) bag {P['gems'][j]} foc {P['foc'][j]:.0f} cd {P['cd0'][j]},{P['cd1'][j]} chan {P['chan'][j]} turn {P['turn'][i]} sees {P['sees'][i]}"
        if q in dl: s += '  D:' + ' '.join(f'{k}={v}' for k, v in sorted(dl[q].items()))
        print(s)
        near = []
        for c in ch:
            if c == p or not ch[c]['alive'][j] or ch[c]['x'][j] is None: continue
            dd = cheb(me, (ch[c]['x'][j], ch[c]['y'][j]))
            if dd <= 10: near.append((dd, f"{nm(c)}@{dd}({ch[c]['x'][j]},{ch[c]['y'][j]}) {ch[c]['hp'][j] / max(1, ch[c]['maxHp'][j]):.2f} cd{ch[c]['cd0'][j]},{ch[c]['cd1'][j]}{' g' + str(ch[c]['gems'][j]) if ch[c]['gems'][j] else ''}"))
        print('     ' + '  '.join(x for _, x in sorted(near)))
        nearids = {c for c in ch if ch[c]['alive'][j] and ch[c]['x'][j] is not None and cheb(me, (ch[c]['x'][j], ch[c]['y'][j])) <= 10}
        for x in ev:
            if x['r'] != q: continue
            a = x.get('a'); k = x['k']
            inv = a == p or x.get('v') == p or (isinstance(x.get('dmg'), list) and any(v == p for v, _ in x['dmg'])) or p in (x.get('stun') or []) or x.get('tgt') == p
            if not inv and not (a in nearids and k in ('attack', 'cast', 'move', 'death')) and not (k == 'death' and x.get('v') in nearids): continue
            if k == 'move': print(f"       {nm(a)} move {x['f']}->{x['to']}")
            elif k in ('attack', 'cast'):
                tg = ', '.join(f'{nm(v)} {amt:.0f}' for v, amt in (x.get('dmg') or []))
                cm = f" camp {sum(a2 for _, a2 in x['cdmg']):.0f}" if x.get('cdmg') else ''
                st = ' STUN ' + ','.join(nm(v) for v in x['stun']) if x.get('stun') else ''
                mv = f" to {x['moved']}" if x.get('moved') else ''
                print(f"       {nm(a)} {k}{'' if k == 'attack' else str(x.get('slot')) + ':' + str(x.get('ab'))} -> {tg}{cm}{st}{mv}")
            elif k == 'camp_attack':
                print(f"       camp{x['camp']} hits {nm(x['tgt']) if x.get('tgt') in ch else x.get('tgt')} {x.get('dmg')}")
            elif k == 'death': print(f"       DEATH {nm(x['v'])} bag {x.get('gems')} by {nm(x['by']) if x.get('by') in ch else 'camp'}")
            elif a == p: print(f"       {nm(a)} {k} {x.get('cause', '')}")


if __name__ == '__main__':
    main()
