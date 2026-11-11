from lib2 import *
import sys
def stats(ext):
    agg=collections.defaultdict(lambda:collections.Counter())
    for g in local_games(ext):
        meta,R,ev,mp=load(ext,g['dir']); us=g['us']
        A,team,typ=acct(meta,R,ev,us)
        opp='Mt3q' if 'Mt3q' in g['src'] else 'Flp4'
        a=agg[opp]; a['n']+=1; a['win']+=g['win']; a['rounds']+=g['rounds']
        for e in ev:
            if e['k']=='death' and team[e['v']]==us:
                if typ[e['v']]=='Prism': a['prism_died']+=e.get('gems',0)
                else: a['np_died']+=e.get('gems',0); a['np_died_small']+=e.get('gems',0) if e.get('gems',0)<25 else 0
                a['deaths']+=1
            if e['k']=='tribute_end' and team[e['a']]==us and typ[e['a']]!='Prism':
                a['np_trib']+=1; a['np_trib_gems']+=e['gems']; a['np_trib_small']+=e['gems']<25
        a['cap']+=A[0].get('cap_gems',0); a['them_cap']+=A[1].get('cap_gems',0)
        i=min(599,len(R['round'])-1); a['g600']+=R['gems'][us][i]
    for opp,a in sorted(agg.items()):
        n=a['n']
        print(f"  {opp}: win {100*a['win']/n:.1f}% | non-Prism tributes/game {a['np_trib']/n:.1f} (under 25 gems: {a['np_trib_small']/n:.1f}), mean size {a['np_trib_gems']/max(1,a['np_trib']):.1f} | gems lost on death/game: non-Prism {a['np_died']/n:.1f} (bags under 25: {a['np_died_small']/n:.1f}), Prism {a['prism_died']/n:.1f} | deaths {a['deaths']/n:.2f} | captured {a['cap']/n:.0f} vs {a['them_cap']/n:.0f} | tributed by r600 {a['g600']/n:.0f} | rounds {a['rounds']/n:.0f}")
for name,ext in (('base 506','/home/ubuntu/tmp-offload/badmaps/extl'),('bm-nb-d','/home/ubuntu/tmp-offload/badmaps/extd')):
    print(name); stats(ext)
