"""Loader for BattleCats match rows pulled from big-arm's capture.db (pull_remote.sh -> raw/all.tsv.gz)."""
import gzip, json, os, collections
BC = '285f4eb5-e97f-4ea4-93c5-19e1590a1e5a'
US = 'stellar best girl'
CH = ["Ryth", "Vesper", "Vendetta", "C&I", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "HoR"]
COLS = "match_id,created_at,kind,map,group_id,position,team_a,team_b,name_a,name_b,result_a,picks_a,picks_b,engine,rank_a,rank_b,rating_a,rating_b,replay".split(',')
RAW = os.path.expanduser('~/tmp-offload/battlecats/raw/all.tsv.gz')
def rows():
    out = {}
    for line in gzip.open(RAW, 'rt'):
        f = line.rstrip('\n').split('\t')
        if len(f) != len(COLS): continue
        r = dict(zip(COLS, f))
        s = 'a' if r['team_a'] == BC else 'b'
        o = 'b' if s == 'a' else 'a'
        try:
            r['bc_picks'] = json.loads(r['picks_' + s]); r['op_picks'] = json.loads(r['picks_' + o])
        except Exception: continue
        if not r['bc_picks'] or not r['op_picks']: continue
        r['bc_side'] = s; r['opp'] = r['name_' + o]; r['opp_id'] = r['team_' + o]
        ra = r['result_a']
        r['bc_win'] = (ra == 'win') == (s == 'a') if ra in ('win', 'loss') else None
        r['hour'] = r['created_at'][:13]
        out[r['match_id']] = r
    return sorted(out.values(), key=lambda r: r['created_at'])
def names(p): return [CH[i] for i in p]
