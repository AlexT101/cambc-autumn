"""Every death of ours in nemesis-era games, with what led to it.

py research/hecate/losses/deaths.py [--losses] [--csv out.csv]
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games, strong  # noqa

REACH = {'Ryth': 1, 'Vendetta': 1, 'Marcella': 1, 'Ren': 1, 'Varg': 1, 'Issac': 1}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def camp_group(g):
    return {c['id']: c['group'] for c in g.map.raw['camps']}


def group_tiles(g):
    return {gr['id']: {tuple(t) for t in gr['tiles']} for gr in g.map.raw['groups']}


def genuine_recall(c, i):
    return c['chan'][i] == 1 and c['chanT'][i] is not None and c['chanT'][i] < 4


def analyse(g):
    cg = camp_group(g)
    tiles = group_tiles(g)
    ev = g.events
    us = set(g.team_ids[g.us])
    by_actor = collections.defaultdict(list)
    for e in ev:
        if 'a' in e:
            by_actor[e['a']].append(e)
    captures = [e for e in ev if e['k'] in ('capture_hold', 'capture_reset', 'capture')]
    dmg_to = collections.defaultdict(list)  # victim -> [(r, source, amount, src_pos)]
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        dmg_to[v].append((r, a, amt, ap))
    for s, r, v, amt in g.camp_damage:
        dmg_to[v].append((r, 'camp', amt, None))
    rows = []
    for d in g.deaths:
        v = d['v']
        if v not in us:
            continue
        r = d['r']
        c = g.ch(v)
        i_end = r - 1  # end of death round
        i_prev = max(0, r - 2)  # end of previous round
        vt = g.name_of[v]
        killer = d.get('by')
        ktype = g.name_of.get(killer, 'camp') if killer is not None else ('camp' if 'camp' in d else '?')
        if 'camp' in d and killer is None:
            ktype = 'camp:' + g.map.group_label(cg[d['camp']]) if hasattr(g.map, 'group_label') else 'camp'
        linked = d.get('linked')
        # damage window
        window = [x for x in dmg_to[v] if r - 10 <= x[0] <= r]
        champ_src = collections.Counter()
        camp_dmg = 0
        for rr, a, amt, ap in window:
            if a == 'camp':
                camp_dmg += amt
            else:
                champ_src[a] += amt
        first_dmg = min((x[0] for x in window if x[1] != 'camp'), default=None)
        # attackers' first sight by the victim before their first hit
        sees = c['sees']
        vis = []
        for a in champ_src:
            fa = min(x[0] for x in window if x[1] == a)
            seen_run = None
            for rr in range(fa, max(0, fa - 25), -1):
                if a in (sees[rr - 1] or []):
                    seen_run = rr
                else:
                    if seen_run is not None or rr < fa:
                        if seen_run is None and rr < fa - 0:
                            continue
                        break
            # earliest round in [fa-15, fa] the victim saw a
            first_seen = next((rr for rr in range(max(1, fa - 15), fa + 1) if a in (sees[rr - 1] or [])), None)
            ally_seen = next((rr for rr in range(max(1, fa - 15), fa + 1)
                              if any(x in us for x in (g.ch(a)['seenBy'][rr - 1] or []))), None)
            vp = g.pos(v, max(0, (first_seen or fa) - 2))
            ap = g.pos(a, max(0, (first_seen or fa) - 2))
            dist_seen = cheb(vp, ap) if vp and ap else None
            ap_hit = g.pos(a, max(0, fa - 2))
            in_bush = ap_hit in g.map.bushes if ap_hit else False
            vis.append(dict(a=a, at=g.name_of[a], fa=fa, dmg=round(champ_src[a]), first_seen=first_seen, lead=(fa - first_seen) if first_seen else None,
                            dist=dist_seen, bush=in_bush, ally_seen=ally_seen))
        # what the victim was doing in the 8 rounds before
        acts = collections.Counter()
        farm_groups = collections.Counter()
        champ_attacks = 0
        tribute = None
        for e in by_actor[v]:
            if not (r - 8 <= e['r'] <= r):
                continue
            k = e['k']
            if k in ('attack', 'cast'):
                if 'camp' in e or e.get('cdmg'):
                    camp = e.get('camp') or (e['cdmg'][0][0] if e.get('cdmg') else None)
                    if camp is not None:
                        farm_groups[cg[camp]] += 1
                if e.get('tgt') is not None or any(x[0] in g.team_of for x in e.get('dmg', [])):
                    champ_attacks += 1
            if k == 'tribute_start':
                tribute = e
            acts[k] += 1
        pos = g.pos(v, i_prev) or (tuple(d['at']) if d.get('at') else None)
        on_group = next((gid for gid, ts in tiles.items() if pos in ts), None)
        recall = genuine_recall(c, i_prev)
        chan = c['chan'][i_prev]
        bag = d.get('gems', 0)
        # movement relative to spawn / altar over last 5 rounds
        p5 = g.pos(v, max(0, r - 7))
        spawn_c = g.map.spawn_center(g.us)
        alt5 = g.map.altar_dist(p5) if p5 else None
        alt0 = g.map.altar_dist(pos) if pos else None
        sp5 = cheb(p5, spawn_c) if p5 else None
        sp0 = cheb(pos, spawn_c) if pos else None
        if chan == 2 or (tribute and r - tribute['r'] <= 6):
            doing = 'tributing'
        elif recall:
            doing = 'recalling'
        elif on_group is not None and any(x['k'] in ('capture_hold',) and x['g'] == on_group and x['team'] == g.us and r - 7 <= x['r'] <= r for x in captures):
            doing = 'capturing'
        elif farm_groups:
            doing = 'farming'
        elif champ_attacks:
            doing = 'fighting'
        elif bag > 0 and alt5 is not None and alt0 < alt5:
            doing = 'banking'
        elif sp5 is not None and sp0 < sp5:
            doing = 'homeward'
        else:
            doing = 'walking'
        farm_label = g.map.group_label(farm_groups.most_common(1)[0][0]) if farm_groups else ''
        half = g.map.half(g.own_pos(v, pos)) if pos else None
        partner_bag = 0
        if vt in ('Cassi', 'Issac') and not linked:
            other = [x for x in g.deaths if x['r'] == r and x.get('linked') == v]
            partner_bag = sum(x.get('gems', 0) for x in other)
        rows.append(dict(
            game=g.dir, gdir=g.gdir, map=g.map_name, opp=g.opp, strong=strong(g.opp), won=g.winner == g.us, r=r, v=v, vt=vt, linked=linked,
            killer=killer, ktype=ktype, bag=bag, partner_bag=partner_bag, hp0=round(d.get('hp', 0)), maxhp=round(c['maxHp'][i_prev] or 0),
            doing=doing, farm=farm_label, camp_dmg=round(camp_dmg), champ_dmg=round(sum(champ_src.values())), n_attackers=len(champ_src),
            attackers='+'.join(sorted(g.name_of[a] for a in champ_src)), first_dmg=first_dmg, vis=vis, pos=pos, half=half,
            hp_at_first=round(c['hp'][max(0, (first_dmg or r) - 2)] or 0), allies_near=sum(
                1 for a in us if a != v and g.pos(a, i_prev) and pos and cheb(g.pos(a, i_prev), pos) <= 5),
            enemies_near=sum(1 for a in g.team_ids[g.them] if g.pos(a, i_prev) and pos and cheb(g.pos(a, i_prev), pos) <= 5),
            gems_us=g.gems_at(g.us, r), gems_them=g.gems_at(g.them, r)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--losses', action='store_true')
    ap.add_argument('--csv')
    ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    rows = []
    games = our_games()
    for g in games:
        if a.losses and g.winner == g.us:
            continue
        rows += analyse(g)
    roots = [x for x in rows if not x['linked']]
    print(f'{len(games)} games, {len(roots)} deaths (+{len(rows) - len(roots)} linked)')
    for key in ('ktype', 'doing', 'vt', 'half'):
        cnt = collections.Counter(x[key] for x in roots)
        print(key, cnt.most_common(15))
    if a.print:
        for x in roots:
            vs = '; '.join(f"{y['at']}#{y['a']} d{y['dmg']} seen{y['lead']}@{y['dist']}{' bush' if y['bush'] else ''}{' ally' + str(y['fa'] - y['ally_seen']) if y['ally_seen'] else ''}" for y in x['vis'])
            print(f"{x['game']} {x['map'][:9]:9} {'W' if x['won'] else 'L'} r{x['r']:4} {x['vt']:7} by {x['ktype']:14} bag{x['bag']:3}+{x['partner_bag']:3} {x['doing']:9} {x['farm']:18} {x['half']} hp1st{x['hp_at_first']:5}/{x['maxhp']} camp{x['camp_dmg']:5} ch{x['champ_dmg']:5} al{x['allies_near']} en{x['enemies_near']} | {vs}")
    if a.csv:
        with open(a.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=[k for k in rows[0] if k != 'vis'] + ['vis'])
            w.writeheader()
            for x in rows:
                w.writerow({**x, 'vis': repr(x['vis'])})


if __name__ == '__main__':
    main()
