"""Who captures gold in the opening: Vesper (+33% gold) presence, its share of captured base gold, the gold multiplier, and what the capturer did in the clear."""
import gzip, json, os, collections, sys
import fl
P = os.path.expanduser('~/tmp-offload/mitere/open2.jsonl.gz')
GR = sys.argv[1:] or ['r7', 'v2']
def vg(g):
    if g['src'] == 'live': return 'r7'
    e = int(g['ver'][1:]); return 'v0' if e == 0 else ('v1' if e <= 7 else 'v2')
G = [g for g in (json.loads(l) for l in gzip.open(P, 'rt')) if vg(g) in GR]
for v in GR:
    gs = [g for g in G if vg(g) == v]
    print(f'==== {v}: {len(gs)} games')
    for who in ('M', 'O'):
        T = lambda g: g['mite'] if who == 'M' else 1 - g['mite']
        for lim in (100, 200):
            hv = [g for g in gs if any(c[1] == T(g) and c[2] == 'Vesper Vale' for c in g['champs'])]
            capb = collections.Counter(); capg = collections.Counter(); ncap = collections.Counter(); vatt = [0, 0]; vb = [0, 0]
            for g in hv:
                name = {c[0]: c[2] for c in g['champs']}
                for x in g['eps']:
                    if not (x['cap'] and x['cap'][1] == T(g) and x['cap'][0] <= lim and x['gold'] > 0): continue
                    sh = x['cap'][2]; tot = sum(s[2] for s in sh)
                    for s in sh:
                        frac = s[2] / tot if tot else 1 / len(sh)
                        capb[name[s[0]]] += x['gold'] * frac; capg[name[s[0]]] += s[2]; ncap[name[s[0]]] += 1 / len(sh)
                    isv = any(name[s[0]] == 'Vesper Vale' for s in sh)
                    vid = [str(c[0]) for c in g['champs'] if c[1] == T(g) and c[2] == 'Vesper Vale'][0]
                    vb[0] += 1; vb[1] += vid in x['att']
                    if vid in x['att']: vatt[0] += 1; vatt[1] += isv
            tb = sum(capb.values())
            print(f' {who} r{lim}: Vesper drafted {len(hv)/len(gs):.0%}; in those games base gold/game {tb/max(1,len(hv)):.0f}, Vesper share of captured base gold {capb["Vesper Vale"]/max(1,tb):.0%}; '
                  f'Vesper hit the group {vb[1]/max(1,vb[0]):.0%} of gold captures, and captured {vatt[1]/max(1,vatt[0]):.0%} of those she hit')
            if lim == 100:
                print('   base gold by capturer: ' + ', '.join(f'{k} {capb[k]/max(1,len(hv)):.0f} (x{capg[k]/max(1,capb[k]):.2f})' for k, _ in capb.most_common(6)))
