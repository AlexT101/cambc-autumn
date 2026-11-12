"""Camp kills without captures, from extract.mjs output of ab.py batches (bot 0 = CAND, `-12` replays: CAND is team A)
or one ladder replay (--team T).

An episode is one clear of a group: from the first damage after the group (re)appeared to the clear. Our attack
turns in it are (champion, round) pairs whose attack or cast damaged its camps. Outcome after the clear:
  prompt  our hold starts within --window rounds of the clear and is paid to us
  late    paid to us, but our first hold started later
  lost    the enemy captured it
  never   nobody captured it before the game ended
Episodes are split by who landed the clear (ours / theirs). Reported per game: episodes, attack turns, gems by class.

usage: ck.py EXTDIR... [--window W] [--team T] [--hist] [--by-type] [--json OUT]
"""
import argparse, collections, gzip, json, os, sys

def side_of(src, team):
    if team is not None: return team
    b = os.path.basename(src)
    return 0 if b.endswith('-12.repl26a') else 1

def kind(G):
    t = set(G['types'])
    if t <= {'Gem cluster'}: return 'gemcl'
    if t <= {'Gold cluster'}: return 'goldcl'
    if t <= {'Gem cluster', 'Gold cluster'}: return 'cl'
    if 'Monolith' in t: return 'mono'
    if 'Golem' in t: return 'golem'
    if 'Elk' in t: return 'elk'
    return 'wolf'

def game(ext, g, us, window, opp):
    d = ext + '/' + g['dir']
    meta = json.load(open(d + '/meta.json'))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    mp = json.load(open(os.path.join(ext, 'maps', os.path.basename(meta['mapFile']))))
    team = {c['id']: c['team'] for c in meta['champions']}
    camp_g = {c['id']: c['group'] for c in mp['camps']}
    camp_tiles = {tuple(t) for G in mp['groups'] for t in G['tiles']}
    groups = {G['id']: G for G in mp['groups']}
    end = meta['result']['rounds']
    ep = {}          # g -> open episode: {'turns': {team: set((a, r))}, 'start': r}
    done = []        # closed episodes
    pending = []     # cleared, awaiting capture: dicts
    def open_ep(gid, r):
        return ep.setdefault(gid, {'g': gid, 'turns': (set(), set()), 'start': r})
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for cid, dmg in e['cdmg']:
                gid = camp_g.get(cid)
                if gid is None or dmg <= 0: continue
                x = open_ep(gid, e['r']); x['turns'][team[e['a']]].add((e['a'], e['r']))
                if team[e['a']] == us and tuple(e['f']) in camp_tiles: x.setdefault('held', set()).add((e['a'], e['r']))
        elif k == 'group_clear':
            x = ep.pop(e['g'], None) or {'g': e['g'], 'turns': (set(), set()), 'start': e['r']}
            x['clear'] = e['r']; x['by'] = team.get(e.get('by'), -1); x['hold'] = None; x['paid'] = None
            pending.append(x)
        elif k == 'capture_hold':
            for x in pending:
                if x['g'] == e['g'] and e['team'] == us and x['hold'] is None: x['hold'] = e['r']
        elif k == 'capture':
            for x in [x for x in pending if x['g'] == e['g']]:
                x['paid'] = (e['r'], e['team']); pending.remove(x); done.append(x)
    done += pending
    out = []
    for x in done:
        G = groups[x['g']]
        if x.get('paid') is None: cls = 'never'
        elif x['paid'][1] != us: cls = 'lost'
        elif x['hold'] is not None and x['hold'] - x['clear'] <= window: cls = 'prompt'
        else: cls = 'late'
        out.append({'g': x['g'], 'kind': kind(G), 'gems': G['gems'], 'gold': G['gold'], 'size': len(G['camps']),
                    'clear': x['clear'], 'by': 'us' if x['by'] == us else 'them', 'cls': cls,
                    'gap': None if x['hold'] is None else x['hold'] - x['clear'],
                    'paid': None if x.get('paid') is None else x['paid'][0] - x['clear'],
                    'ours': len(x['turns'][us]), 'held': len(x.get('held', ())), 'theirs': len(x['turns'][1 - us]), 'end': end})
    return out, end

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('ext', nargs='+'); ap.add_argument('--window', type=int, default=8)
    ap.add_argument('--team', type=int); ap.add_argument('--hist', action='store_true'); ap.add_argument('--by-type', action='store_true')
    ap.add_argument('--json'); ap.add_argument('--kinds', default='')
    a = ap.parse_args()
    allx = []; n = 0; rounds = 0
    for ext in a.ext:
        for g in json.load(open(ext + '/index.json'))['games']:
            opp = 'Mt3q' if 'Mt3q' in g['source'] else 'Flp4' if 'Flp4' in g['source'] else 'x'
            xs, end = game(ext, g, side_of(g['source'], a.team), a.window, opp)
            for x in xs: x['opp'] = opp; x['src'] = g['source']
            allx += xs; n += 1; rounds += end
    if a.kinds: allx = [x for x in allx if x['kind'] in a.kinds.split(',')]
    print(f'{n} games, {rounds/n:.0f} rounds a game, window {a.window}')
    if a.hist:
        h = collections.Counter(min(x['gap'], 60) if x['gap'] is not None else 'none' for x in allx if x['by'] == 'us')
        print('our clears: our first hold - clear round:', sorted(h.items(), key=lambda t: (isinstance(t[0], str), t[0])))
    keys = ['kind'] if a.by_type else []
    tab = collections.defaultdict(collections.Counter)
    for x in allx:
        key = (x['by'],) + tuple(x[k] for k in keys)
        t = tab[key]; t['eps'] += 1; t['eps_' + x['cls']] += 1
        t['turns'] += x['ours']; t['turns_' + x['cls']] += x['ours']; t['held_' + x['cls']] += x['held']; t['gems_' + x['cls']] += x['gems']; t['gold_' + x['cls']] += x['gold']
    for key in sorted(tab):
        t = tab[key]
        s = ' '.join(f"{c}:{t['eps_'+c]/n:.2f}ep/{t['turns_'+c]/n:.1f}t/{t['gems_'+c]/n:.1f}gm" for c in ('prompt', 'late', 'lost', 'never'))
        free = sum(t['held_' + c] for c in ('late', 'lost', 'never')); paid = sum(t['turns_' + c] for c in ('late', 'lost', 'never'))
        print(f"clear by {'/'.join(map(str,key)):<14} eps {t['eps']/n:6.2f}  our attack turns {t['turns']/n:6.1f}  | {s} | non-prompt turns {paid/n:.2f} of which from a capture tile {free/n:.2f}")
    if a.json: json.dump(allx, open(a.json, 'w'))

if __name__ == '__main__': main()

def killers(ext, us_of=None, window=8):
    """Who lands our clears, and how (basic / cast), by outcome class: champion name x hit kind x class counts."""
    tab = collections.Counter()
    for g in json.load(open(ext + '/index.json'))['games']:
        us = side_of(g['source'], us_of)
        d = ext + '/' + g['dir']
        meta = json.load(open(d + '/meta.json'))
        name = {c['id']: c['name'] for c in meta['champions']}
        team = {c['id']: c['team'] for c in meta['champions']}
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
        xs, _ = game(ext, g, us, window, None)
        cls = {(x['g'], x['clear']): x['cls'] for x in xs}
        last = None
        for e in ev:
            if e['k'] in ('attack', 'cast'): last = e
            if e['k'] == 'group_clear' and team.get(e.get('by')) == us:
                how = (last['k'] + ('-' + last.get('ab', '') if last['k'] == 'cast' else '')) if last and last.get('a') == e['by'] else '?'
                tab[(name[e['by']], how, cls.get((e['g'], e['r']), '?'))] += 1
    return tab
