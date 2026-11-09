"""HoR champion-hitting dashes: hp fraction at the dash, HoR death within W rounds, kills of hit enemies within W."""
import beh, json, gzip, collections
W=4
def dashes(d, T):
    meta, rd, ev = beh.load(d)
    team = {c['id']: c['team'] for c in meta['champions']}
    hor = {c['id'] for c in meta['champions'] if c['name'] == 'Heart of Ruin'}
    if not hor: return []
    ch = {c['id']: c for c in rd['champions']}
    rounds = rd['round']
    deaths = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append((e['r'], e.get('by')))
    out = []
    for e in ev:
        if e['k'] == 'cast' and e['a'] in hor and e.get('ab') == 'Dash' and e.get('dmg'):
            a = e['a']; r = e['r']; i = max(0, min(len(rounds) - 1, r - 2))
            c = ch[a]; frac = c['hp'][i] / max(1, c['maxHp'][i])
            died = any(r <= dr <= r + W for dr, _ in deaths[a])
            hit = [h[0] for h in e['dmg'] if team.get(h[0]) != team[a]]
            kills = sum(1 for v in hit if any(r <= dr <= r + W for dr, _ in deaths[v]))
            out.append(('us' if team[a] == T else 'op', frac, int(died), kills, len(hit)))
    return out
