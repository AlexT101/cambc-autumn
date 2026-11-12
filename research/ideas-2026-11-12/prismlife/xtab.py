"""Cross-tabs of onset.py's episodes: python3 xtab.py EXTROOT/TAG (episodes cached beside the extraction as onset.pkl)."""
import sys, os, collections, pickle, statistics
import onset


def episodes(root):
    c = os.path.join(root.rstrip('/') + '.onset.pkl')
    if os.path.exists(c): return pickle.load(open(c, 'rb'))
    G = [g for g in onset.load(root) if g['prism']]
    pickle.dump(G, open(c, 'wb'))
    return G


def main():
    G = episodes(sys.argv[1])
    E = [e for g in G for e in g['eps']]
    D = [e for e in E if e['died']]
    print(f'{len(G)} Prism games, {len(E)} episodes, {len(D)} deaths')

    def tab(name, key, S=E):
        g = collections.defaultdict(list)
        for e in S: g[key(e)].append(e)
        print('\n' + name)
        for k in sorted(g, key=str):
            s = g[k]; d = sum(e['died'] for e in s)
            print(f'  {str(k):40s} {len(s):6d} ({100 * len(s) / len(S):5.1f}%) die {100 * d / len(s):5.1f}% = {d:4d} ({100 * d / len(D):4.1f}% of deaths)')
    hb = lambda e: 'hurt<0.5' if e['hp'] < 0.5 else 'mid<0.9' if e['hp'] < 0.9 else 'full'
    ab = lambda e: 'alone' if e['na6'] == 0 else '1 ally' if e['na6'] == 1 else '2+ allies'
    la = lambda e: e['last'][-1] if e['last'] else '?'
    grp = lambda a: 'retreating' if a in ('walk-', 'walk=') else 'closing' if a == 'walk+' else 'fighting' if a in ('cast@champ', 'hit@champ') else 'tribute' if a == 'tribute' else 'other'
    tab('health x allies', lambda e: (hb(e), ab(e)))
    tab('allies within 3', lambda e: min(e['na3'], 3))
    tab('last act x health', lambda e: (grp(la(e)), hb(e)))
    tab('last act x allies', lambda e: (grp(la(e)), ab(e)))
    tab('home distance x allies (full health)', lambda e: ('far>=20' if e['home'] >= 20 else 'near', ab(e)), [e for e in E if e['hp'] >= 0.9])
    tab('struck a champion in its last 3 turns x allies', lambda e: (any(x in ('cast@champ', 'hit@champ') for x in e['last']), ab(e)))
    tab('enemies who saw the Prism at onset', lambda e: min(e['seen_by'], 4))
    tab('bag x allies', lambda e: ('bag>=100' if e['gems'] >= 100 else 'bag<100', ab(e)))
    tab('enemies within 8 x allies', lambda e: (min(e['ne8'], 3), ab(e)))
    print('\ndeath episodes: damage taken / max health, median', round(statistics.median(e['dmg'] / e['maxhp'] for e in D), 2))


if __name__ == '__main__':
    main()
