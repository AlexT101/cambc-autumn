"""Live r7 opening gold split by who drafted Vesper (+33% gold), paired on the same games; and Vesper's share of captured base gold within each cell."""
import gzip, json, os, collections
import fl
G = [g for g in (json.loads(l) for l in gzip.open(os.path.expanduser('~/tmp-offload/mitere/open2.jsonl.gz'), 'rt')) if g['src'] == 'live']
def hasv(g, t): return any(c[1] == t and c[2] == 'Vesper Vale' for c in g['champs'])
def vshare(gs, side, lim=100):
    v = b = 0
    for g in gs:
        t = g['mite'] if side == 'M' else 1 - g['mite']; name = {c[0]: c[2] for c in g['champs']}
        for x in g['eps']:
            if x['cap'] and x['cap'][1] == t and x['cap'][0] <= lim and x['gold'] > 0:
                b += x['gold']; v += sum(x['gold'] / len(x['cap'][2]) for s in x['cap'][2] if name[s[0]] == 'Vesper Vale')
    return v / max(1, b), b / max(1, len(gs))
print('Mite V, ours V: games, Mite r100 / ours r100, r200 / r200, Vesper share of base gold r100 (M/O), base gold r100 (M/O)')
for mv in (True, False):
    for ov in (True, False):
        gs = [g for g in G if hasv(g, g['mite']) == mv and hasv(g, 1 - g['mite']) == ov]
        if not gs: continue
        e = lambda r, s: fl.mean(g['earned'][str(r)][g['mite'] if s == 'M' else 1 - g['mite']] for g in gs)
        sm, bm = vshare(gs, 'M'); so, bo = vshare(gs, 'O')
        print(f'{mv!s:5} {ov!s:5} n {len(gs):3d}: r100 {e(100,"M"):.0f} / {e(100,"O"):.0f}, r200 {e(200,"M"):.0f} / {e(200,"O"):.0f}; Vesper share {sm:.0%} / {so:.0%}; base {bm:.0f} / {bo:.0f}')
# both-Vesper games: r200 routing, captures by type before r100, and who holds gold groups Vesper did not take
gs = [g for g in G if hasv(g, g['mite']) and hasv(g, 1 - g['mite'])]
for s in 'MO':
    sh, b = vshare(gs, s, 200)
    ty = collections.Counter(); hold = collections.Counter(); n = 0
    for g in gs:
        t = g['mite'] if s == 'M' else 1 - g['mite']; name = {c[0]: c[2] for c in g['champs']}
        for x in g['eps']:
            if x['cap'] and x['cap'][1] == t and x['cap'][0] <= 100:
                ty[fl.gtype(x['types'])] += 1; n += 1
                if x['gold'] > 0 and not any(name[q[0]] == 'Vesper Vale' for q in x['cap'][2]):
                    hold[name[x['cap'][2][0][0]]] += x['gold']
    print(f'{s} both-V r200: Vesper share {sh:.0%} of base {b:.0f}/game; captures by r100 {n/len(gs):.1f}: ' + ', '.join(f'{k} {c/len(gs):.1f}' for k, c in ty.most_common(5)) +
          '; non-Vesper gold holders (base/game): ' + ', '.join(f'{k} {c/len(gs):.0f}' for k, c in hold.most_common(4)))
