"""Back-to-back kills: the killer's last turn before the kill fell in the previous round and hit the victim, and the
victim had no turn between the two (an enemy hitting twice across a round boundary before the victim acts).

For our deaths that were back-to-back, whether the base order model (the killer keeps last round's rank in its team)
would have given the killer a turn before ours next round, and whether turn windows would (the killer's priority
changed, so it was unsettled; windows give the `room` enemy slots before ours to the nearest unsettled enemies).

python3 b2b.py ANALYSIS_DIR GAMES.jsonl  (one JSON per line: {"dir": extracted dir, "us": 0|1, "tag": label})
"""
import collections, gzip, json, sys

def game(d, us):
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt'))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    champs = R['champions']; rounds = R['round']
    ri_of = {r: i for i, r in enumerate(rounds)}
    team = {c['id']: c['team'] for c in champs}
    C = {c['id']: c for c in champs}
    def ranks(j):
        by = {0: [], 1: []}
        for c in champs: by[c['team']].append((-c['prio'][max(j, 0)], c['id']))
        out = {}
        for t in by:
            for k, (_, cid) in enumerate(sorted(by[t])): out[cid] = k
        return out
    def slots(r, rank):
        first = 0 if r % 2 == 1 else 1
        n = {0: sum(1 for c in champs if c['team'] == 0), 1: sum(1 for c in champs if c['team'] == 1)}
        out = {}
        for cid, k in rank.items():
            t = team[cid]; others = n[1 - t]
            out[cid] = 2 * k + (0 if t == first else 1) if k < others else others + k
        return out
    order = {}
    for i, r in enumerate(rounds):
        order[r] = slots(r, ranks(i - 1))
    seq = lambda r, cid: r * 100 + order[r][cid]
    # who damaged whom in which turn
    hit = collections.defaultdict(set)  # (round, attacker) -> victims
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('a') in team:
            for x in e.get('dmg') or []:
                if x[0] in team and team[x[0]] != team[e['a']]: hit[(e['r'], e['a'])].add(x[0])
    out = []
    for e in ev:
        if e['k'] != 'death' or e.get('linked') is not None or e.get('by') not in team: continue
        v, k, r = e['v'], e['by'], e['r']
        if team[v] == team[k] or r - 1 not in order or r not in order: continue
        ri = ri_of[r]
        # killer's previous turn: the round before (its turn this round is the kill)
        prev_hit = v in hit.get((r - 1, k), ())
        s_p, s_d = seq(r - 1, k), seq(r, k)
        v_between = s_p < seq(r - 1, v) or seq(r, v) < s_d
        b2b = prev_hit and not v_between
        row = {'victim_team': team[v], 'ours': team[v] == us, 'b2b': b2b, 'loose': not v_between, 'round': r}
        if b2b and team[v] == us:
            # base: killer at its round r-1 rank in round r; windows: unsettled if its rank changed
            base_rank = ranks(ri - 2)  # ranks in force in r-1
            base_slot = slots(r, {**ranks(ri - 1), k: base_rank[k]})[k]
            base_pred = base_slot < order[r][v]
            changed = base_rank[k] != ranks(ri - 1)[k]
            # windows: room = enemy slots before ours in r; killer chosen among the nearest alive enemies
            room = sum(1 for c in champs if team[c['id']] != us and order[r][c['id']] < order[r][v])
            j = ri - 1
            vx, vy = C[v]['x'][j], C[v]['y'][j]
            def d(c): return max(abs(C[c]['x'][j] - vx), abs(C[c]['y'][j] - vy))
            foes = sorted((d(c['id']), -c['str'][j], c['id']) for c in champs if team[c['id']] != us and c['alive'][j])
            near = [x[2] for x in foes].index(k) if k in [x[2] for x in foes] else 99
            win_pred = base_pred if not changed else near < room
            seen = k in (C[v]['sees'][j] or [])
            row.update(base_pred=base_pred, changed=changed, win_pred=win_pred, seen=seen, room=room, near=near)
        out.append(row)
    return out

def main():
    rows = collections.defaultdict(list)
    for line in open(sys.argv[2]):
        g = json.loads(line)
        for x in game(g['dir'], g['us']):
            x['tag'] = g.get('tag', '')
            rows[g.get('tag', '')].append(x)
    for tag, xs in sorted(rows.items()):
        ours = [x for x in xs if x['ours']]; theirs = [x for x in xs if not x['ours']]
        b = [x for x in ours if x['b2b']]
        print(f"{tag}: kills by us {len(theirs)}, b2b {sum(x['b2b'] for x in theirs)} ({100*sum(x['b2b'] for x in theirs)/max(1,len(theirs)):.1f}%), loose {100*sum(x['loose'] for x in theirs)/max(1,len(theirs)):.1f}% | "
              f"our deaths {len(ours)}, b2b {len(b)} ({100*len(b)/max(1,len(ours)):.1f}%), loose {100*sum(x['loose'] for x in ours)/max(1,len(ours)):.1f}%")
        if b:
            n = len(b)
            print(f"   our b2b deaths: base model predicted the 2nd turn {sum(x['base_pred'] for x in b)} ({100*sum(x['base_pred'] for x in b)/n:.0f}%); "
                  f"killer changed priority {sum(x['changed'] for x in b)}; of those windows would pick it {sum(x['win_pred'] for x in b if x['changed'])}; "
                  f"windows predicted overall {sum(x['win_pred'] for x in b)} ({100*sum(x['win_pred'] for x in b)/n:.0f}%); "
                  f"predicted by windows but not base {sum(x['win_pred'] and not x['base_pred'] for x in b)}; killer in sight {sum(x['seen'] for x in b)}")
main()
