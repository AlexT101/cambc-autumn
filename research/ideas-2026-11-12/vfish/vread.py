import json, statistics as st, collections
import sys
res = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'vfish.json'))
NAMES = sys.argv[2:4] if len(sys.argv) > 3 else ('fish', 'us')
def mean(xs): xs = [x for x in xs if x is not None]; return (sum(xs) / len(xs), len(xs)) if xs else (None, 0)
def flat(key, side): return [y for g in res if g[side].get('has_v') for y in g[side].get(key, [])]
for side in ('fish', 'us'):
    G = [g[side] for g in res if g[side].get('has_v')]
    print(f'== {NAMES[0] if side == "fish" else NAMES[1]}: {len(G)} games with Vesper of {len(res)}; win {mean([g["win"] for g in G])[0]:.3f}')
    for ph in 'el':
        tot = sum(g['caps_' + ph] for g in G)
        print(f'  caps {"<=r300" if ph == "e" else ">r300"}: {tot / len(G):.1f}/game  ' + '  '.join(f'{k} {sum(g[k + "_" + ph] for g in G) / tot:.2f}' for k in ('vsolo', 'vshared', 'osolo', 'oshared')),
              f' | V gold share {mean([g["vgold_share_" + ph] for g in G])[0]:.2f} gem share {mean([g["vgem_share_" + ph] for g in G])[0]:.2f}')
        a = flat('vdmg_share_on_vcaps_' + ph, side); b = flat('ndmg_on_vcaps_' + ph, side); c = flat('mates_near_vsolo_' + ph, side)
        if a: print(f'     on V-held captures: V dealt {sum(a) / len(a):.2f} of the clear damage; champions with >10% of it {sum(b) / len(b):.2f}; mates within 5 of the clearer at a V-solo clear {sum(c) / max(1, len(c)):.2f}')
    print(f'  V tribute share of team gems {mean([g["vtrib_share"] for g in G])[0]:.2f}; V tributed {mean([g["vtrib"] for g in G])[0]:.0f}')
    print(f'  V recalls {mean([g["vrecalls"] for g in G])[0]:.1f} (mates {mean([g["mrecalls"] for g in G])[0]:.1f} each), V shop rounds/game {mean([len(g["vshop_rounds"]) for g in G])[0]:.1f}, first shop r{st.median([g["vshop_rounds"][0] for g in G if g["vshop_rounds"]])}, V crystals {mean([g["vtele"] for g in G])[0]:.1f}')
    for rr in (100, 200, 300, 450, 600, 900):
        print(f'  r{rr}: V earned {mean([g.get(f"vearn_{rr}") for g in G])[0]:.0f} mate avg {mean([g.get(f"mearn_{rr}") for g in G])[0]:.0f} | V str {mean([g.get(f"vstr_{rr}") for g in G])[0]:.0f} hp {mean([g.get(f"vhp_{rr}") for g in G])[0]:.0f} unspent {mean([g.get(f"vgoldheld_{rr}") for g in G])[0]:.0f} | mate maxhp {mean([g.get(f"mhp_{rr}") for g in G])[0]:.0f}  n={mean([g.get(f"vearn_{rr}") for g in G])[1]}')
    print('  team gold earned: ' + '  '.join(f'r{rr} {mean([g.get(f"tearn_{rr}") for g in G])[0]:.0f}' for rr in (100, 300, 600)) + f' | capture gems to r300 {mean([g["capgems300"] for g in G])[0]:.0f}, all game {mean([g["capgems"] for g in G])[0]:.0f} | gems lost to deaths {mean([g["gems_lost"] for g in G])[0]:.0f} (V {mean([g["v_gems_lost"] for g in G])[0]:.0f})')
    wv = flat('wait_v', side); wo = flat('wait_o', side)
    print(f'  rounds from a group clear to its payout: V-held {sum(wv) / max(1, len(wv)):.1f}, others {sum(wo) / max(1, len(wo)):.1f}')
    print('  cohesion (share of mates within 5 of V): ' + '  '.join(f'r{a}+ {mean([g.get(f"coh_{a}") for g in G])[0]:.2f}' for a in (1, 100, 300, 600)))
    print(f'  V kills {mean([g["vkills"] for g in G])[0]:.2f} of team {mean([g["tkills"] for g in G])[0]:.2f}; V deaths {mean([g["vdeaths"] for g in G])[0]:.2f} of team {mean([g["tdeaths"] for g in G])[0]:.2f}; V champ dmg share {sum(g["vchampdmg"] for g in G) / sum(g["tchampdmg"] for g in G):.2f}; V monster dmg share {sum(g["vmondmg"] for g in G) / sum(g["tmondmg"] for g in G):.2f}')
    # build order: first-purchase round of each item family for V
    first = collections.defaultdict(list); cnt = collections.Counter()
    for g in G:
        seen = set()
        for r, it, c in g['vbuys']:
            fam = it.replace(' Shard', '').replace(' Emblem', '')
            if fam not in seen: seen.add(fam); first[fam].append(r)
    print('  V item families (first bought: games, median round):')
    for fam, rs in sorted(first.items(), key=lambda kv: st.median(kv[1]))[:16]: print(f'     {fam:32s} {len(rs):4d} r{st.median(rs):.0f}')
    mb = collections.Counter()
    for g in G:
        for k, c in g['mbuys'].items(): mb[k.split('|')[1].replace(' Shard', '').replace(' Emblem', '')] += c
    print('  mates buy (top):', ', '.join(f'{k} {c / len(G):.1f}' for k, c in mb.most_common(10)))
