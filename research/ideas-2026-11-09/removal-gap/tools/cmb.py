"""Combat-level metrics for team T and its opponent."""
import beh, json, gzip, collections
def cm(d, T):
    meta, rd, ev = beh.load(d)
    team = {c['id']: c['team'] for c in meta['champions']}
    f = collections.Counter()
    R = rd['round'][-1]; f['rounds'] = R; f['win'] = int(meta['result']['winner'] == T)
    for c in meta['champions']:
        s = 'us' if c['team'] == T else 'op'
        st = c['stats']
        f['cdmg_' + s] += st['championDamageDone']; f['mdmg_' + s] += st['monsterDamageDone']
        f['kills_' + s] += st['kills']; f['gold_' + s] += st['earnedGold']
    for c in rd['champions']:
        s = 'us' if c['team'] == T else 'op'
        f['oof_' + s] += sum(1 for t in c['turn'] if t == 6)
    for e in ev:
        if e['k'] == 'cast':
            s = 'us' if team[e['a']] == T else 'op'
            f['cast_' + s] += 1
            if e.get('dmg'): f['ccast_' + s] += 1
        elif e['k'] == 'shop':
            s = 'us' if team[e['a']] == T else 'op'
            for it, n in (e.get('items') or {}).items():
                if n > 0:
                    fam = it.split(' ')[0]
                    f['buy_' + fam + '_' + s] += n
    return f
