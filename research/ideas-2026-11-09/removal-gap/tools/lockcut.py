import beh, json, sys, pickle, collections
def cuts(d, T):
    """Victim = team 1-T (opponent of T). For each lock cancel of a victim tribute: ran, left, gems, then outcome."""
    meta, rd, ev = beh.load(d)
    team = {c['id']: c['team'] for c in meta['champions']}
    out = []; starts = {}
    for i, e in enumerate(ev):
        if e['k'] == 'tribute_start': starts[e['a']] = e
        if e['k'] == 'tribute_cancel' and e.get('cause') == 'lock' and team[e['a']] != T:
            s = starts.get(e['a']); a = e['a']
            if not s: continue
            rec = {'r': e['r'], 'gems': s['gems'], 'dur': s['dur'], 'left': e.get('left', 0), 'rebank': None, 'died': None, 'rebank_g': 0, 'win': int(meta['result']['winner'] == T)}
            for f in ev[i + 1:]:
                if f['k'] == 'tribute_end' and f['a'] == a:
                    rec['rebank'] = f['r'] - e['r']; rec['rebank_g'] = f.get('gems', 0); break
                if f['k'] == 'death' and f['v'] == a:
                    rec['died'] = f['r'] - e['r']; rec['died_g'] = f.get('gems', 0); rec['killer_team_T'] = int(team.get(f.get('by'), -1) == T); break
            out.append(rec)
    return out
